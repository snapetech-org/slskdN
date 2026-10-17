import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import * as listeningParty from '../../lib/listeningParty';
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import { usePlayer } from './PlayerContext';
import React, { useCallback, useEffect, useId, useRef, useState } from 'react';
import { Button, Checkbox, Icon, Label, List, Popup, Segment } from 'semantic-ui-react';

const DIRECTORY_POLL_INTERVAL_MS = 60_000;
const sameDirectory = (previous, next) =>
  previous.length === next.length &&
  previous.every(
    (party, index) =>
      party.partyId === next[index]?.partyId &&
      party.podId === next[index]?.podId &&
      party.channelId === next[index]?.channelId &&
      party.hostPeerId === next[index]?.hostPeerId &&
      party.title === next[index]?.title &&
      party.artist === next[index]?.artist &&
      party.album === next[index]?.album &&
      party.contentId === next[index]?.contentId &&
      party.action === next[index]?.action &&
      party.positionSeconds === next[index]?.positionSeconds &&
      party.startedAtUnixMs === next[index]?.startedAtUnixMs &&
      party.allowMeshStreaming === next[index]?.allowMeshStreaming &&
      party.streamPath === next[index]?.streamPath &&
      party.transportUsername === next[index]?.transportUsername &&
      party.streamTicket === next[index]?.streamTicket,
  );

const PodListenAlongPanel = ({ channelId, compact = false, podId, user }) => {
  useInterfaceLanguage();
  const player = usePlayer();
  const settingsId = useId();
  const canBroadcastCurrent = Boolean(
    player.current?.contentId && !player.current.contentId.startsWith('local:') && !player.current.radioPartyId,
  );
  const [room, setRoom] = useState({ connected: false, error: '', pending: true, state: null });
  const { connected, error: connectionError, pending: connectionPending, state: roomState } = room;
  const [directory, setDirectory] = useState([]);
  const following = Boolean(player.followingParty &&
    player.followingParty.podId === podId && player.followingParty.channelId === channelId);
  const [globalRadio, setGlobalRadio] = useState(false);
  const [meshStreaming, setMeshStreaming] = useState(false);
  const [partyState, setPartyState] = useState(null);
  const [publishError, setPublishError] = useState('');
  const directoryFetchInFlightRef = useRef(false);
  const confirmedSettingsRef = useRef(null);
  const mountedRef = useRef(false);
  const publishRequestRef = useRef(0);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!podId || !channelId) return undefined;
    publishRequestRef.current += 1;
    setPublishError('');
    setGlobalRadio(false);
    setMeshStreaming(false);
    return player.observePartyRoom(podId, channelId, setRoom);
  }, [channelId, player.observePartyRoom, podId]);

  useEffect(() => { setPartyState(roomState); }, [roomState]);
  const ownBroadcast = player.broadcastStatus?.podId === podId && player.broadcastStatus?.channelId === channelId;
  useEffect(() => {
    if (ownBroadcast) {
      setGlobalRadio(Boolean(player.broadcastStatus.globalRadio));
      setMeshStreaming(Boolean(player.broadcastStatus.meshStreaming));
    }
  }, [ownBroadcast, player.broadcastStatus?.globalRadio, player.broadcastStatus?.meshStreaming]);

  const refreshDirectory = useCallback(async () => {
    if (compact || document.hidden || directoryFetchInFlightRef.current) return;

    directoryFetchInFlightRef.current = true;
    try {
      const next = await listeningParty.getPartyDirectory();
      if (!mountedRef.current || document.hidden) return;
      setDirectory((previous) =>
        sameDirectory(previous, next) ? previous : next,
      );
    } catch {
      // Retain the last successful directory during transient failures.
    } finally {
      directoryFetchInFlightRef.current = false;
    }
  }, [compact]);

  useEffect(() => {
    if (!ownBroadcast || !player.broadcastStatus.active || !player.broadcastStatus.confirmedSettings) {
      confirmedSettingsRef.current = null;
      return;
    }
    const settings = `${podId}/${channelId}:${player.broadcastStatus.globalRadio}:${player.broadcastStatus.meshStreaming}`;
    if (confirmedSettingsRef.current !== null && confirmedSettingsRef.current !== settings) refreshDirectory();
    confirmedSettingsRef.current = settings;
  }, [channelId, ownBroadcast, player.broadcastStatus?.active, player.broadcastStatus?.confirmedSettings,
    player.broadcastStatus?.globalRadio, player.broadcastStatus?.meshStreaming, podId, refreshDirectory]);

  useEffect(() => {
    if (compact) return undefined;

    let interval = null;
    const stopPolling = () => {
      if (interval) {
        window.clearInterval(interval);
        interval = null;
      }
    };
    const startPolling = () => {
      if (document.hidden || interval) return;
      refreshDirectory();
      interval = window.setInterval(
        refreshDirectory,
        DIRECTORY_POLL_INTERVAL_MS,
      );
    };
    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopPolling();
      } else {
        startPolling();
      }
    };

    startPolling();
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      stopPolling();
    };
  }, [compact, refreshDirectory]);

  const publish = (action, settings = { globalRadio, meshStreaming }, updatingSettings = false) => {
    if (action !== 'stop' && !canBroadcastCurrent) return;

    const requestId = ++publishRequestRef.current;
    setPublishError('');
    const request = player.publishBroadcast({ channelId, ...settings, podId, user,
      partyId: partyState?.podId === podId && partyState?.channelId === channelId ? partyState.partyId : '',
    }, action);
    request.then((state) => {
      if (!mountedRef.current || requestId !== publishRequestRef.current) return;
      if (state) setPartyState(action === 'stop' ? null : state);
      if (!compact && !updatingSettings) refreshDirectory();
    }).catch((error) => {
      if (error?.name === 'AbortError' || error?.code === 'ERR_CANCELED') return;
      if (mountedRef.current && requestId === publishRequestRef.current) {
        setPublishError(interfaceText(error?.message === 'Stop the active broadcast before starting another room.'
          ? 'Stop the active broadcast before starting another room.'
          : error?.response?.status === 429
          ? 'Room updates are at capacity. Retry later.'
          : error?.response?.status === 409 && error?.response?.data?.code === 'party_id_in_use'
            ? 'This Party ID is already in use. Start the broadcast again to claim a new ID.'
          : error?.response?.status === 403
            ? 'Room access was revoked. Rejoin before broadcasting.'
          : error?.response?.status === 404
            ? 'This room is unavailable. Choose an existing room.'
          : error?.response?.data?.code === 'room_storage_unavailable'
              ? 'The room update could not be saved. Try again.'
              : error?.response?.data?.code === 'party_directory_unavailable'
                ? 'Party ID ownership could not be checked. Try again.'
              : action === 'stop'
          ? 'Could not stop the room broadcast. Try again.'
          : updatingSettings
            ? 'Could not confirm broadcast settings. Retry to apply the requested settings.'
            : getApiErrorMessage(error, { t: interfaceText }, 'Could not start the room broadcast. Try again.')));
      }
    });
  };

  const hosting = ownBroadcast && player.broadcastStatus.active;
  const settingsBusy = hosting && (player.broadcastStatus.settingsPending || player.broadcastStatus.stopping);
  const listed = hosting ? player.broadcastStatus.globalRadio : globalRadio;
  const streaming = hosting ? player.broadcastStatus.meshStreaming : meshStreaming;
  const changeSettings = (field, value) => {
    const settings = hosting
      ? { globalRadio: player.broadcastStatus.requestedGlobalRadio, meshStreaming: player.broadcastStatus.requestedMeshStreaming }
      : { globalRadio, meshStreaming };
    settings[field] = value;
    if (!settings.globalRadio) settings.meshStreaming = false;
    if (hosting) publish('play', settings, true);
    else {
      setGlobalRadio(settings.globalRadio);
      setMeshStreaming(settings.meshStreaming);
    }
  };
  const visiblePublishError = publishError || (ownBroadcast ? player.broadcastStatus.error : '');
  const broadcastFeedback = <>
    {hosting && player.broadcastStatus.stopping
      ? <div className="pod-listen-along-state" role="status"><LocalizedText source={"Stopping room broadcast…"} /></div> : null}
    {hosting && player.broadcastStatus.settingsPending
      ? <div className="pod-listen-along-state" role="status"><LocalizedText source={"Applying broadcast settings…"} /></div> : null}
    {visiblePublishError ? <div className="pod-listen-along-error" role="alert"><LocalizedText source={visiblePublishError} /></div> : null}
    {hosting && player.broadcastStatus.error ? <Popup
      content={interfaceText("Retry the failed room update using the current playback state. Failed Stop requests are retried as Stop.")}
      trigger={<Button aria-label={interfaceText("Retry room broadcast update")} className="pod-listen-along-retry" disabled={player.broadcastStatus.pending || player.broadcastStatus.stopping}
        icon="refresh" onClick={() => { setPublishError(''); player.retryBroadcast().catch(() => {}); }} size="mini"  {...interfaceTextProps("Retry room broadcast update")}/>}
     {...interfaceTextProps("Retry the failed room update using the current playback state. Failed Stop requests are retried as Stop.")}/> : null}
  </>;

  const joinListedParty = (party) => {
    const streamUrl = listeningParty.buildRadioStreamUrl(party);
    const elapsed = party.action === 'play' && Number.isFinite(party.startedAtUnixMs) &&
      party.startedAtUnixMs > 0
      ? Math.max(0, (Date.now() - party.startedAtUnixMs) / 1000)
      : 0;
    const positionSeconds = Number.isFinite(party.positionSeconds)
      ? Math.max(0, party.positionSeconds)
      : 0;
    player.followParty(null);
    player.playItem(
      {
        album: party.album,
        artist: party.artist || party.hostPeerId,
        contentId: party.contentId,
        streamUrl,
        radioPartyId: party.transportUsername && party.streamTicket ? party.partyId : null,
        title: party.title || party.contentId,
      },
      {
        replaceQueue: true,
        positionSeconds: positionSeconds + elapsed,
        streamUrl,
        startPaused: party.action === 'pause',
      },
    );
  };

  const retryConnection = !connected || connectionError ? (
    <Popup
      content={interfaceText("Reconnect to this room and refresh the host's current state after a connection or refresh failure.")}
      trigger={
        <Button
          aria-label={interfaceText("Retry listen-along connection")}
          disabled={connectionPending || !podId || !channelId}
          icon="refresh"
          loading={connectionPending}
          onClick={() => player.retryPartyRoom(podId, channelId)}
          size="mini"
         {...interfaceTextProps("Retry listen-along connection")}/>
      }
     {...interfaceTextProps("Reconnect to this room and refresh the host's current state after a connection or refresh failure.")}/>
  ) : null;

  if (compact) {
    return (
      <Segment className="pod-listen-along pod-listen-along-compact">
        <div className="pod-listen-along-compact-status">
          <Popup
            content={
              partyState
                ? interfaceText('{hostPeerId} {action}: {title}', {
                  action: partyState.action,
                  hostPeerId: partyState.hostPeerId,
                  title: partyState.title || partyState.contentId,
                })
                : interfaceText('No active room broadcast')
            }
            trigger={
              <span
                className={`pod-listen-along-orb ${connected ? 'pod-listen-along-orb-live' : ''}`}
                role="status"
               {...interfaceTextProps(connected ? 'Listen Along live' : connectionPending ? 'Listen Along connecting' : 'Listen Along offline')}
              />
            }
          />
          <span className="pod-listen-along-compact-copy">
            {partyState ? partyState.title || partyState.contentId : <LocalizedText source={"Room broadcast"} />}
          </span>
        </div>
        <div className="pod-listen-along-compact-actions">
          {retryConnection}
          <Popup
            content={player.playerVisible === false
              ? interfaceText('Show the browser player before following this room.')
              : interfaceText("Follow this room's broadcast using your own stream access.")}
            {...interfaceTextProps(player.playerVisible === false
              ? 'Show the browser player before following this room.'
              : "Follow this room's broadcast using your own stream access.")}
            trigger={
              <Button
                active={following}
                aria-label={interfaceText("Follow room broadcast")}
                disabled={player.playerVisible === false}
                icon
                onClick={() => player.followParty(following ? null : { podId, channelId })}
                size="mini"
                title={interfaceText("Follow room broadcast")}
                toggle
               {...interfaceTextProps("Follow room broadcast")}>
                <Icon name={following ? 'volume up' : 'volume off'} />
              </Button>
            }
          />
          <Popup
            content={interfaceText("Broadcast the current server-backed track to this room. Browser-only files cannot be streamed to other listeners.")}
            trigger={
              <Button
                aria-label={interfaceText("Broadcast current track to room")}
                disabled={!canBroadcastCurrent || Boolean(settingsBusy)}
                icon
                onClick={() => publish('play')}
                size="mini"
                title={interfaceText("Broadcast current track to room")}
               {...interfaceTextProps("Broadcast current track to room")}>
                <Icon name="bullhorn" />
              </Button>
            }
           {...interfaceTextProps("Broadcast the current server-backed track to this room. Browser-only files cannot be streamed to other listeners.")}/>
          <Popup
            content={interfaceText("Choose whether listeners can discover this broadcast. Changes apply immediately while you host; otherwise click Broadcast to apply.")}
            trigger={
              <Button
                active={listed}
                aria-label={interfaceText("List room broadcast in mesh directory")}
                aria-busy={Boolean(settingsBusy)}
                disabled={Boolean(settingsBusy)}
                icon
                onClick={() => changeSettings('globalRadio', !listed)}
                size="mini"
                title={interfaceText("List room broadcast in mesh directory")}
                toggle
               {...interfaceTextProps("List room broadcast in mesh directory")}>
                <Icon name="globe" />
              </Button>
            }
           {...interfaceTextProps("Choose whether listeners can discover this broadcast. Changes apply immediately while you host; otherwise click Broadcast to apply.")}/>
          <Popup
            content={interfaceText("Allow directory listeners to stream from this node. Changes apply immediately while you host; unlisting also turns streaming off.")}
            trigger={
              <Button
                active={streaming}
                aria-label={interfaceText("Allow mesh streaming for broadcast")}
                aria-busy={Boolean(settingsBusy)}
                disabled={!listed || Boolean(settingsBusy)}
                icon
                onClick={() => changeSettings('meshStreaming', !streaming)}
                size="mini"
                title={interfaceText("Allow mesh streaming for broadcast")}
                toggle
               {...interfaceTextProps("Allow mesh streaming for broadcast")}>
                <Icon name="wifi" />
              </Button>
            }
           {...interfaceTextProps("Allow directory listeners to stream from this node. Changes apply immediately while you host; unlisting also turns streaming off.")}/>
          <Popup
            content={interfaceText("Stop broadcasting listen-along metadata for this room.")}
            trigger={
              <Button
                aria-label={interfaceText("Stop room broadcast")}
                disabled={Boolean(hosting && player.broadcastStatus.stopping)}
                loading={Boolean(hosting && player.broadcastStatus.stopping)}
                icon
                onClick={() => publish('stop')}
                size="mini"
                title={interfaceText("Stop room broadcast")}
               {...interfaceTextProps("Stop room broadcast")}>
                <Icon name="stop" />
              </Button>
            }
           {...interfaceTextProps("Stop broadcasting listen-along metadata for this room.")}/>
        </div>
        {connectionError ? <div className="pod-listen-along-error" role="alert"><LocalizedText source={connectionError} /></div> : null}
        {broadcastFeedback}
      </Segment>
    );
  }

  return (
    <Segment className="pod-listen-along">
      <div className="pod-listen-along-main">
        <div>
          <strong><LocalizedText source={"Listen Along"} /></strong>
          <div className="pod-listen-along-state">
            {partyState
              ? interfaceText('{hostPeerId} {action}: {title}', {
                action: partyState.action,
                hostPeerId: partyState.hostPeerId,
                title: partyState.title || partyState.contentId,
              })
              : <LocalizedText source={"No active party"} />}
          </div>
        </div>
        <Label color={connected ? 'green' : 'grey'}>
          {connected
            ? <LocalizedText source={"Live"} />
            : connectionPending
              ? <LocalizedText source={"Connecting"} />
              : <LocalizedText source={"Offline"} />}
        </Label>
        {retryConnection}
      </div>
      <div className="pod-listen-along-toggles">
        <Popup
          content={interfaceText("Choose whether listeners can discover this broadcast. Changes apply immediately while you host; otherwise click Broadcast to apply.")}
          trigger={
            <Checkbox
              aria-busy={Boolean(settingsBusy)}
              checked={listed}
              disabled={Boolean(settingsBusy)}
              id={`${settingsId}-listed`}
              label={interfaceText("List globally")}
              onChange={(event, data) => changeSettings('globalRadio', data.checked)}
              toggle
             {...interfaceTextProps("List globally")}/>
          }
         {...interfaceTextProps("Choose whether listeners can discover this broadcast. Changes apply immediately while you host; otherwise click Broadcast to apply.")}/>
        <Popup
          content={interfaceText("Allow directory listeners to stream from this node. Changes apply immediately while you host; unlisting also turns streaming off.")}
          trigger={
            <Checkbox
              aria-busy={Boolean(settingsBusy)}
              checked={streaming}
              id={`${settingsId}-streaming`}
              disabled={!listed || Boolean(settingsBusy)}
              label={interfaceText("Mesh streaming")}
              onChange={(event, data) => changeSettings('meshStreaming', data.checked)}
              toggle
             {...interfaceTextProps("Mesh streaming")}/>
          }
         {...interfaceTextProps("Allow directory listeners to stream from this node. Changes apply immediately while you host; unlisting also turns streaming off.")}/>
      </div>
      <Button.Group size="small">
        <Popup
          content={player.playerVisible === false
            ? interfaceText('Show the browser player before following this pod.')
            : interfaceText("Follow this pod's host playback using your own stream access.")}
          {...interfaceTextProps(player.playerVisible === false
            ? 'Show the browser player before following this pod.'
            : "Follow this pod's host playback using your own stream access.")}
          trigger={
            <Button
              active={following}
              aria-label={interfaceText("Follow pod broadcast")}
              toggle
              disabled={player.playerVisible === false}
              icon
              onClick={() => player.followParty(following ? null : { podId, channelId })}
             {...interfaceTextProps("Follow pod broadcast")}>
              <Icon name={following ? 'volume up' : 'volume off'} />
            </Button>
          }
        />
        <Popup
          content={interfaceText("Publish the current server-backed track as the pod listen-along host. Browser-only files cannot be streamed to other listeners.")}
          trigger={
            <Button
              aria-label={interfaceText("Broadcast current track to pod")}
              disabled={!canBroadcastCurrent || Boolean(settingsBusy)}
              icon
              onClick={() => publish('play')}
             {...interfaceTextProps("Broadcast current track to pod")}>
              <Icon name="bullhorn" />
            </Button>
          }
         {...interfaceTextProps("Publish the current server-backed track as the pod listen-along host. Browser-only files cannot be streamed to other listeners.")}/>
        <Popup
          content={interfaceText("Stop hosting listen-along metadata for this pod.")}
          trigger={
            <Button
              aria-label={interfaceText("Stop pod broadcast")}
              disabled={Boolean(hosting && player.broadcastStatus.stopping)}
              loading={Boolean(hosting && player.broadcastStatus.stopping)}
              icon
              onClick={() => publish('stop')}
             {...interfaceTextProps("Stop pod broadcast")}>
              <Icon name="stop" />
            </Button>
          }
         {...interfaceTextProps("Stop hosting listen-along metadata for this pod.")}/>
      </Button.Group>
      {connectionError ? <div className="pod-listen-along-error" role="alert"><LocalizedText source={connectionError} /></div> : null}
      {broadcastFeedback}
      {directory.length > 0 && (
        <div className="pod-listen-along-directory">
          <strong><LocalizedText source={"Listed radio"} /></strong>
          <List divided relaxed>
            {directory.slice(0, 6).map((party) => (
              <List.Item key={party.partyId}>
                <List.Content floated="right">
                  <Popup
                    content={interfaceText("Play this listed radio snapshot through the host's stream endpoint. Rejoin for later track changes.")}
                    trigger={
                      <Button
                        aria-label={`Play ${party.title || party.contentId} from listed radio`}
                        disabled={!party.allowMeshStreaming || !party.transportUsername || !party.streamTicket}
                        icon
                        onClick={() => joinListedParty(party)}
                        size="mini"
                      >
                        <Icon name="play" />
                      </Button>
                    }
                   {...interfaceTextProps("Play this listed radio snapshot through the host's stream endpoint. Rejoin for later track changes.")}/>
                </List.Content>
                <List.Content>
                  <List.Header>{party.title || party.contentId}</List.Header>
                  <List.Description>
                    {party.hostPeerId}
                    {party.allowMeshStreaming ? <LocalizedText source={"| streamable"} /> : <LocalizedText source={"| metadata only"} />}
                  </List.Description>
                </List.Content>
              </List.Item>
            ))}
          </List>
        </div>
      )}
    </Segment>
  );
};

export default PodListenAlongPanel;
