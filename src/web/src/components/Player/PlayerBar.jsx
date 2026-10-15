import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import './Player.css';
import * as collectionsAPI from '../../lib/collections';
import {
  clearDiscoveryShelf,
  exportDiscoveryShelfPolicyReport,
  getDiscoveryShelf,
  getDiscoveryShelfActionLabel,
  getDiscoveryShelfPolicyPreview,
  getDiscoveryShelfSummary,
  removeDiscoveryShelfItem,
  upsertDiscoveryShelfItem,
} from '../../lib/discoveryShelf';
import * as externalVisualizer from '../../lib/externalVisualizer';
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import { setExperiencePreference } from '../../lib/experiencePreferences';
import * as listenBrainz from '../../lib/listenBrainz';
import * as nowPlaying from '../../lib/nowPlaying';
import {
  clearListeningHistory,
  exportListeningHistoryCsv,
  exportListeningHistoryJson,
  getListeningRecommendationQueries,
  getListeningRecommendationSeeds,
  getListeningStats,
  importListeningHistory,
  recordLocalPlay,
} from '../../lib/listeningHistory';
import {
  getPlayerRating,
  getPlayerRatingSummary,
  setPlayerRating,
} from '../../lib/playerRatings';
import {
  buildPlayerRadioPlan,
  buildPlayerRadioSearchPath,
  getPlayerRadioQueries,
  getPlayerRadioCopyText,
} from '../../lib/playerRadio';
import {
  buildSimilarQueueCandidates,
  getSimilarQueueSearchQueries,
} from '../../lib/playerAutoQueue';
import { getPlayerShortcutAction } from '../../lib/playerShortcuts';
import { getLocalStorageItem, setLocalStorageItem } from '../../lib/storage';
import usePrefersReducedMotion from '../../lib/usePrefersReducedMotion';
import * as searches from '../../lib/searches';
import * as streaming from '../../lib/streaming';
import * as wishlistAPI from '../../lib/wishlist';
import Equalizer from './Equalizer';
import LyricsPane from './LyricsPane';
import SpectrumAnalyzer, { getFrequencyBars } from './SpectrumAnalyzer';
import RadioDirectory from './RadioDirectory';
import usePlayerDialog from './usePlayerDialog';
import { buildRadioStreamUrl, createRadioStreamUrl } from '../../lib/listeningParty';
import { fadeOutputGain, getExistingAudioGraph, getOrCreateAudioGraph, releaseAudioGraph, resumeAudioGraph, setKaraokeEnabled, setOutputGain, suspendAudioGraph } from './audioGraph';
import { usePlayer } from './PlayerContext';
import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  Checkbox,
  Header,
  Icon,
  Input,
  Label,
  Message,
  Modal,
  Popup,
  Segment,
  Table,
  TextArea,
} from 'semantic-ui-react';

const localMuteStorageKey = 'slskdn.player.localMuted';
const collapsedStorageKey = 'slskdn.player.collapsed';
const visualizerStorageKey = 'slskdn.player.visualizerEnabled';
const visualizerEngineStorageKey = 'slskdn.player.visualizerEngine';
const eqPanelStorageKey = 'slskdn.player.eqPanelOpen';
const lyricsStorageKey = 'slskdn.player.lyricsOpen';
const karaokeStorageKey = 'slskdn.player.karaokeEnabled';
const crossfadeStorageKey = 'slskdn.player.crossfadeEnabled';
const visualTileStorageKey = 'slskdn.player.visualTileMode';
const legacyAnalyzerModeStorageKey = 'slskdn.player.analyzerMode';
const analyzerModeStorageKey = 'slskdn.player.analyzerMode.v2';
const volumeStorageKey = 'slskdn.player.volume';
const playbackRateStorageKey = 'slskdn.player.rate';
const playerBrowserPageSize = 80;
const Visualizer = React.lazy(() => import('./Visualizer'));

const formatTime = (seconds) => {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00';
  const whole = Math.floor(seconds);
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`;
};

const PlayerProgress = ({ current, duration, onSeek, position }) => {
  useInterfaceLanguage();
  const draftRef = useRef(null);
  const [draft, setDraft] = useState(null);
  const displayedPosition = draft ?? position;
  useEffect(() => {
    draftRef.current = null;
    setDraft(null);
  }, [current]);
  const commitSeek = () => {
    if (draftRef.current === null) return;
    const seconds = draftRef.current;
    draftRef.current = null;
    setDraft(null);
    onSeek(seconds);
  };

  return (
    <div className="player-progress">
      <span aria-hidden="true">{formatTime(displayedPosition)}</span>
      <input
        aria-label={interfaceText("Seek playback")}
        aria-valuetext={`${formatTime(displayedPosition)} of ${formatTime(duration)}`}
        disabled={!current || duration <= 0}
        max={duration || 1}
        min="0"
        onBlur={commitSeek}
        onChange={(event) => {
          const seconds = Number(event.target.value);
          draftRef.current = seconds;
          setDraft(seconds);
        }}
        onKeyUp={commitSeek}
        onPointerCancel={() => {
          draftRef.current = null;
          setDraft(null);
        }}
        onPointerUp={commitSeek}
        step="1"
        type="range"
        value={Math.min(displayedPosition, duration || 1)}
       {...interfaceTextProps("Seek playback")}/>
      <span aria-hidden="true">-{formatTime(Math.max(0, duration - displayedPosition))}</span>
    </div>
  );
};

const asArray = (value) => (Array.isArray(value) ? value : []);

const readStoredBoolean = (key) => {
  return getLocalStorageItem(key) === 'true';
};

const readStoredVisualizerEngineTileMode = () => {
  const engine = getLocalStorageItem(visualizerEngineStorageKey);
  if (engine === 'native') return 'native-webgl2';
  return ['butterchurn', 'native-webgl2', 'native-webgpu'].includes(engine)
    ? engine
    : 'butterchurn';
};

const readStoredTileMode = () => {
  const mode = getLocalStorageItem(visualTileStorageKey);
  if (['art', 'spectrum', 'scope', 'butterchurn', 'native-webgl2', 'native-webgpu'].includes(mode)) {
    return mode;
  }
  if (mode === 'milkdrop') {
    return readStoredVisualizerEngineTileMode();
  }
  return 'art';
};

const readStoredAnalyzerMode = () => {
  const mode = getLocalStorageItem(analyzerModeStorageKey);
  if (['off', 'spectrum', 'scope'].includes(mode)) return mode;
  return getLocalStorageItem(legacyAnalyzerModeStorageKey) === 'scope' ? 'scope' : 'off';
};

const setPlayerHeightVariable = (element) => {
  if (!element || typeof document === 'undefined') return;

  const height = Math.ceil(element.getBoundingClientRect().height);
  if (height > 0) {
    document.documentElement.style.setProperty(
      '--slskdn-player-reserved-height',
      `${height}px`,
    );
  }
};

const getExternalVisualizerStatusText = (status, loading) => {
  if (loading) return interfaceText('Checking external visualizer launcher...');
  if (!status) return interfaceText('Status unavailable.');
  if (!status.enabled) return interfaceText('Disabled in slskd.yml.');
  if (!status.configured) return interfaceText('No launcher path configured.');
  if (!status.available) return interfaceText('Configured launcher path was not found.');
  return interfaceText('Ready to launch on the slskdN host.');
};

const getExternalVisualizerError = (error) =>
  getApiErrorMessage(error, { t: interfaceText }, 'External visualizer did not launch.');

const PlayerToolButton = ({
  active = false,
  children = null,
  content,
  disabled = false,
  icon,
  label,
  ...buttonProps
}) => (
  <Popup
    content={content}
    trigger={
      <Button
        {...buttonProps}
        className={[
          'player-tool-button',
          buttonProps.className,
          active ? 'player-tool-button-active' : '',
        ].filter(Boolean).join(' ')}
        disabled={disabled}
        icon={!label}
        size="small"
        type="button"
      >
        <Icon name={icon} />
        {label ? <span>{label}</span> : null}
        {children}
      </Button>
    }
  />
);

const formatPlayerProvider = (provider = '') => {
  const normalized = String(provider).trim();
  if (!normalized) return '';
  if (normalized.toLowerCase() === 'soulseek') return 'Soulseek';
  if (normalized.toLowerCase() === 'mesh') return 'Mesh';
  if (normalized.toLowerCase() === 'pod') return 'Pod';
  return normalized;
};

const getPlayerBadges = (current) => {
  if (!current) return [];

  const providers = (Array.isArray(current.sourceProviders)
    ? current.sourceProviders
    : [])
    .map(formatPlayerProvider)
    .filter(Boolean);
  const badges = providers.slice(0, 2).map((provider) => ({
    color: provider === 'Mesh' || provider === 'Pod' ? 'violet' : 'grey',
    icon: provider === 'Mesh' ? 'share alternate' : 'music',
    key: `source-${provider}`,
    text: provider,
    title: `Playback source: ${provider}`,
  }));

  const confidence = Number(current.confidence || 0);
  if (confidence > 0) {
    badges.push({
      color: confidence >= 0.75 ? 'green' : 'yellow',
      icon: 'crosshairs',
      key: 'confidence',
      text: `${Math.round(confidence * 100)}% match`,
      title: interfaceText("Local match confidence for this now-playing item."),
    });
  }

  if (current.verified) {
    badges.push({
      color: 'teal',
      icon: 'check circle',
      key: 'verified',
      text: interfaceText("Verified"),
      title: interfaceText("This item has local verification evidence."),
    });
  }

  return badges;
};

const PlayerRatingControls = ({ current, onChange, rating }) => {
  useInterfaceLanguage();
  if (!current) return null;

  const summary = getPlayerRatingSummary(current);

  return (
    <div
      aria-label={interfaceText("Now playing rating")}
      className={[
        'player-rating-controls',
        `player-rating-controls-${summary.tone}`,
      ].join(' ')}
      data-testid="player-rating-controls"
      role="group"
     {...interfaceTextProps("Now playing rating")}>
      {[1, 2, 3, 4, 5].map((value) => (
        <Popup
          content={
            value === rating
              ? interfaceText('Clear this local rating.')
              : interfaceText(
                'Rate this track {rating} out of 5 for local discovery context.',
                { rating: value },
              )
          }
          key={value}
          trigger={
            <button
              aria-label={
                value === rating
                  ? interfaceText('Clear {rating} star rating', { rating: value })
                  : interfaceText('Rate {rating} stars', { rating: value })
              }
              className={[
                'player-rating-button',
                value <= rating ? 'player-rating-button-active' : '',
              ].filter(Boolean).join(' ')}
              aria-pressed={value === rating}
              data-testid={`player-rating-${value}`}
              onClick={() => onChange(value === rating ? 0 : value)}
              title={
                value === rating
                  ? interfaceText('Clear this local rating.')
                  : interfaceText('Rate this track {rating} out of 5.', { rating: value })
              }
              type="button"
            >
              <Icon name={value <= rating ? 'star' : 'star outline'} />
            </button>
          }
        />
      ))}
      <span className="player-rating-summary">{interfaceText(summary.label)}</span>
    </div>
  );
};

const PlayerRadioModal = ({ current, onClose, onOpenSearch, open }) => {
  useInterfaceLanguage();
  const dialog = usePlayerDialog(open);
  const plan = buildPlayerRadioPlan(current);
  const copyText = getPlayerRadioCopyText(plan);
  const [runningSearches, setRunningSearches] = useState(false);
  const [savingWishlist, setSavingWishlist] = useState(false);
  const [status, setStatus] = useState('');

  const copyPlan = () => {
    if (navigator.clipboard && copyText) {
      navigator.clipboard.writeText(copyText).catch(() => {});
    }
  };

  const startRadioSearches = async () => {
    const queries = getPlayerRadioQueries(plan, { limit: 3 });
    if (queries.length === 0) {
      setStatus(interfaceText('No smart-radio queries are ready.'));
      return;
    }

    try {
      setRunningSearches(true);
      const count = await searches.createBatch({ queries });
      setStatus(interfaceText(
        count === 1 ? 'Started 1 smart-radio search.' : 'Started {count} smart-radio searches.',
        { count },
      ));
    } catch {
      setStatus(interfaceText('Unable to start smart-radio searches.'));
    } finally {
      setRunningSearches(false);
    }
  };

  const addRadioWishlist = async () => {
    const queries = getPlayerRadioQueries(plan, { limit: 4 });
    if (queries.length === 0) {
      setStatus(interfaceText('No smart-radio queries are ready for Wishlist.'));
      return;
    }

    try {
      setSavingWishlist(true);
      await queries.reduce(
        (chain, searchText) =>
          chain.then(() =>
            wishlistAPI.create({
              autoDownload: false,
              enabled: true,
              filter: '',
              maxResults: 50,
              searchText,
            }),
          ),
        Promise.resolve(),
      );
      setStatus(interfaceText(
        queries.length === 1 ? 'Added 1 smart-radio seed to Wishlist.' : 'Added {count} smart-radio seeds to Wishlist.',
        { count: queries.length },
      ));
    } catch {
      setStatus(interfaceText('Unable to add smart-radio seeds to Wishlist.'));
    } finally {
      setSavingWishlist(false);
    }
  };

  return (
    <Modal
      {...dialog.dialogProps}
      className="player-browser-modal player-radio-modal"
      onClose={onClose}
      open={open}
      size="small"
    >
      <Modal.Header {...dialog.titleProps}><LocalizedText source={"Smart Radio Seed"} /></Modal.Header>
      <Modal.Content>
        <p className="player-modal-copy">
          <LocalizedText source={"Build review-first radio searches from the current track. Nothing is searched or queued until you choose a query."} /></p>
        <div className="player-radio-seed" data-testid="player-radio-seed">
          <Icon name="random" />
          <div>
            <strong>{plan.seedLabel}</strong>
            <div>
              {plan.basis.length > 0 ? plan.basis.join(' | ') : <LocalizedText source={"Pick a track first."} />}
            </div>
          </div>
        </div>
        <div className="player-radio-query-list">
          {plan.queries.map((item) => (
            <div className="player-radio-query" key={item.id}>
              <div>
                <Label color="violet" size="mini">
                  {item.reason}
                </Label>
                <code>{item.query}</code>
              </div>
              <Popup
                content={interfaceText("Open this as a normal Search page query. This is the point where network search work can begin.")}
                trigger={
                  <Button
                    data-testid={`player-radio-search-${item.id}`}
                    onClick={() => onOpenSearch(item.query)}
                    size="mini"
                    type="button"
                  >
                    <Icon name="search" />
                    <LocalizedText source={"Search"} /></Button>
                }
               {...interfaceTextProps("Open this as a normal Search page query. This is the point where network search work can begin.")}/>
            </div>
          ))}
        </div>
        {status ? (
          <Message compact size="mini">
            {status}
          </Message>
        ) : null}
      </Modal.Content>
      <Modal.Actions>
        <Popup
          content={interfaceText("Start up to three live searches from this smart-radio plan. This does not browse peers, queue downloads, or mutate files.")}
          trigger={
            <Button
              data-testid="player-radio-start-searches"
              disabled={!plan.ready}
              loading={runningSearches}
              onClick={startRadioSearches}
              type="button"
            >
              <Icon name="search" />
              <LocalizedText source={"Start Searches"} /></Button>
          }
         {...interfaceTextProps("Start up to three live searches from this smart-radio plan. This does not browse peers, queue downloads, or mutate files.")}/>
        <Popup
          content={interfaceText("Add smart-radio seeds to Wishlist as enabled manual requests with auto-download off.")}
          trigger={
            <Button
              data-testid="player-radio-add-wishlist"
              disabled={!plan.ready}
              loading={savingWishlist}
              onClick={addRadioWishlist}
              type="button"
            >
              <Icon name="heart" />
              <LocalizedText source={"Add Wishlist"} /></Button>
          }
         {...interfaceTextProps("Add smart-radio seeds to Wishlist as enabled manual requests with auto-download off.")}/>
        <Popup
          content={interfaceText("Copy the generated radio search plan as plain text.")}
          trigger={
            <Button
              data-testid="player-radio-copy"
              disabled={!copyText}
              onClick={copyPlan}
              type="button"
            >
              <Icon name="copy outline" />
              <LocalizedText source={"Copy Plan"} /></Button>
          }
         {...interfaceTextProps("Copy the generated radio search plan as plain text.")}/>
        <Popup
          content={interfaceText("Close smart radio without starting a search.")}
          trigger={
            <Button
              data-testid="player-radio-close"
              onClick={onClose}
              primary
              type="button"
            >
              <Icon name="check" />
              <LocalizedText source={"Done"} /></Button>
          }
         {...interfaceTextProps("Close smart radio without starting a search.")}/>
      </Modal.Actions>
    </Modal>
  );
};

const getTrackLabel = (item) =>
  item?.title || item?.fileName || item?.contentId || 'Untitled track';

const isSavablePlaylistTrack = (item) =>
  typeof item?.contentId === 'string' &&
  !item.contentId.startsWith('local:') &&
  !item.streamUrl && !item.radioPartyId;

const PlayerQueueModal = ({
  current,
  history,
  onClearQueue,
  onAutoQueueSimilar,
  onClose,
  onLoadPlaylist,
  onMove,
  onNext,
  onPrevious,
  onRemove,
  open,
  queue,
}) => {
  useInterfaceLanguage();
  const dialog = usePlayerDialog(open);
  const upcoming = queue.slice(1);
  const [handoffStatus, setHandoffStatus] = useState('');
  const [searchingSimilar, setSearchingSimilar] = useState(false);
  const [savingSimilarWishlist, setSavingSimilarWishlist] = useState(false);
  const [playlists, setPlaylists] = useState([]);
  const [playlistName, setPlaylistName] = useState('');
  const [selectedPlaylist, setSelectedPlaylist] = useState('');
  const [playlistBusy, setPlaylistBusy] = useState('');
  const activeRef = useRef(true);
  const similarCandidates = buildSimilarQueueCandidates({
    current,
    history,
    queue,
  });

  useEffect(() => {
    activeRef.current = true;
    return () => {
      activeRef.current = false;
    };
  }, []);

  const closeModal = () => {
    activeRef.current = false;
    onClose();
  };

  useEffect(() => {
    if (!open) return undefined;
    let cancelled = false;
    collectionsAPI.getCollections().then((response) => {
      if (!cancelled) {
        const fetched = asArray(response.data).filter((entry) => entry.type === 'Playlist');
        setPlaylists((existing) => [...fetched, ...existing.filter((entry) => !fetched.some((item) => item.id === entry.id))]);
      }
    }).catch(() => {
      if (!cancelled) setHandoffStatus(interfaceText('Could not retrieve saved playlists. Close and reopen the queue to retry.'));
    });
    return () => { cancelled = true; };
  }, [open]);

  const savePlaylist = async () => {
    const name = playlistName.trim();
    const items = queue.filter(isSavablePlaylistTrack);
    if (!name || items.length === 0) return;
    setPlaylistBusy('saving');
    let createdPlaylistId = null;
    try {
      const response = await collectionsAPI.createCollection({ title: name, type: 'Playlist' });
      createdPlaylistId = response.data.id;
      for (const item of items) {
        await collectionsAPI.addCollectionItem(createdPlaylistId, {
          album: item.album,
          artist: item.artist,
          contentId: item.contentId,
          fileName: item.fileName,
          mediaKind: 'Audio',
          title: item.title,
        });
      }
      setPlaylists((existing) => [...existing, response.data]);
      setPlaylistName('');
      setHandoffStatus(interfaceText(
        items.length === 1 ? 'Saved {count} track to {name}.' : 'Saved {count} tracks to {name}.',
        { count: items.length, name },
      ));
    } catch {
      if (createdPlaylistId) {
        try {
          await collectionsAPI.deleteCollection(createdPlaylistId);
        } catch {
          setHandoffStatus(interfaceText('The playlist is incomplete and could not be removed. Review it in Collections.'));
          return;
        }
      }
      setHandoffStatus(interfaceText('Could not save the playlist.'));
    } finally {
      setPlaylistBusy('');
    }
  };

  const loadPlaylist = async () => {
    if (!selectedPlaylist) return;
    setPlaylistBusy('loading');
    try {
      const response = await collectionsAPI.getCollectionItems(selectedPlaylist);
      if (!activeRef.current) return;
      const items = asArray(response.data).filter((item) => item.contentId);
      if (items.length === 0) {
        setHandoffStatus(interfaceText('This playlist has no playable tracks.'));
      } else {
        onLoadPlaylist(items);
        setHandoffStatus(interfaceText('Loaded playlist tracks: {count}.', { count: items.length }));
      }
    } catch {
      if (activeRef.current) setHandoffStatus(interfaceText('Could not load the playlist.'));
    } finally {
      if (activeRef.current) setPlaylistBusy('');
    }
  };

  const startSimilarSearches = async () => {
    const queries = getSimilarQueueSearchQueries(similarCandidates, { limit: 3 });
    if (queries.length === 0) {
      setHandoffStatus(interfaceText('No similar queue candidates are ready to search.'));
      return;
    }

    try {
      setSearchingSimilar(true);
      const count = await searches.createBatch({ queries });
      setHandoffStatus(interfaceText(
        count === 1 ? 'Started 1 similar-track search.' : 'Started {count} similar-track searches.',
        { count },
      ));
    } catch {
      setHandoffStatus(interfaceText('Unable to start similar-track searches.'));
    } finally {
      setSearchingSimilar(false);
    }
  };

  const addSimilarWishlist = async () => {
    const queries = getSimilarQueueSearchQueries(similarCandidates, { limit: 5 });
    if (queries.length === 0) {
      setHandoffStatus(interfaceText('No similar queue candidates are ready for Wishlist.'));
      return;
    }

    try {
      setSavingSimilarWishlist(true);
      await queries.reduce(
        (chain, searchText) =>
          chain.then(() =>
            wishlistAPI.create({
              autoDownload: false,
              enabled: true,
              filter: '',
              maxResults: 50,
              searchText,
            }),
          ),
        Promise.resolve(),
      );
      setHandoffStatus(interfaceText(
        queries.length === 1 ? 'Added 1 similar-track seed to Wishlist.' : 'Added {count} similar-track seeds to Wishlist.',
        { count: queries.length },
      ));
    } catch {
      setHandoffStatus(interfaceText('Unable to add similar-track seeds to Wishlist.'));
    } finally {
      setSavingSimilarWishlist(false);
    }
  };

  return (
    <Modal
      {...dialog.dialogProps}
      className="player-browser-modal player-queue-modal"
      onClose={closeModal}
      open={open}
      size="small"
    >
      <Modal.Header {...dialog.titleProps}><LocalizedText source={"Playback Queue"} /></Modal.Header>
      <Modal.Content>
        <div className="player-queue-manager">
          <section className="player-playlist-actions">
            <div className="player-panel-title"><LocalizedText source={"Playlists"} /></div>
            <Input
              aria-label={interfaceText("New playlist name")}
              disabled={Boolean(playlistBusy)}
              onChange={(event) => setPlaylistName(event.target.value)}
              placeholder={interfaceText("Name this queue")}
              size="small"
              value={playlistName}
             {...interfaceTextProps("New playlist name")}/>
            <Popup content={interfaceText("Save the current server library tracks as a new Collection playlist.")} trigger={
              <Button aria-busy={playlistBusy === 'saving'} disabled={!playlistName.trim() || Boolean(playlistBusy) || !queue.some(isSavablePlaylistTrack)} loading={playlistBusy === 'saving'} onClick={savePlaylist} size="small" type="button"><LocalizedText source={"Save queue"} /></Button>
            }  {...interfaceTextProps("Save the current server library tracks as a new Collection playlist.")}/>
            <select aria-label={interfaceText("Saved playlist")} disabled={Boolean(playlistBusy)} onChange={(event) => setSelectedPlaylist(event.target.value)} value={selectedPlaylist} {...interfaceTextProps("Saved playlist")}>
              <option value=""><LocalizedText source={"Choose playlist"} /></option>
              {playlists.map((playlist) => <option key={playlist.id} value={playlist.id}>{playlist.title}</option>)}
            </select>
            <Popup content={interfaceText("Replace the immediate queue with tracks from this saved playlist.")} trigger={
              <Button aria-busy={playlistBusy === 'loading'} disabled={!selectedPlaylist || Boolean(playlistBusy)} loading={playlistBusy === 'loading'} onClick={loadPlaylist} size="small" type="button"><LocalizedText source={"Load"} /></Button>
            }  {...interfaceTextProps("Replace the immediate queue with tracks from this saved playlist.")}/>
          </section>
          <section>
            <div className="player-panel-title"><LocalizedText source={"Now Playing"} /></div>
            <div className="player-queue-manager-row player-queue-manager-current">
              <Icon name="play circle outline" />
              <div>
                <strong>{getTrackLabel(current)}</strong>
                <span>{current?.artist || <LocalizedText source={"No active playback"} />}</span>
              </div>
            </div>
          </section>
          <section>
            <div className="player-queue-manager-heading">
              <div className="player-panel-title"><LocalizedText source={"Upcoming"} /></div>
              <div className="player-queue-manager-actions">
                <Popup
                  content={interfaceText("Add similar recent session tracks to the upcoming queue. This only uses tracks already known to this browser session.")}
                  trigger={
                    <Button
                      data-testid="player-auto-queue-similar"
                      disabled={similarCandidates.length === 0}
                      onClick={() =>
                        onAutoQueueSimilar(
                          similarCandidates.map((candidate) => candidate.item),
                        )
                      }
                      size="mini"
                      type="button"
                    >
                      <Icon name="magic" />
                      <LocalizedText source={"Auto-fill Similar"} /></Button>
                  }
                 {...interfaceTextProps("Add similar recent session tracks to the upcoming queue. This only uses tracks already known to this browser session.")}/>
                <Popup
                  content={interfaceText("Start up to three searches from similar recent session tracks. This starts search jobs only.")}
                  trigger={
                    <Button
                      data-testid="player-search-similar-candidates"
                      disabled={similarCandidates.length === 0}
                      loading={searchingSimilar}
                      onClick={startSimilarSearches}
                      size="mini"
                      type="button"
                    >
                      <Icon name="search" />
                      <LocalizedText source={"Search Similar"} /></Button>
                  }
                 {...interfaceTextProps("Start up to three searches from similar recent session tracks. This starts search jobs only.")}/>
                <Popup
                  content={interfaceText("Add similar recent session tracks to Wishlist as manual requests with auto-download off.")}
                  trigger={
                    <Button
                      data-testid="player-wishlist-similar-candidates"
                      disabled={similarCandidates.length === 0}
                      loading={savingSimilarWishlist}
                      onClick={addSimilarWishlist}
                      size="mini"
                      type="button"
                    >
                      <Icon name="heart" />
                      <LocalizedText source={"Wishlist Similar"} /></Button>
                  }
                 {...interfaceTextProps("Add similar recent session tracks to Wishlist as manual requests with auto-download off.")}/>
                <Popup
                  content={interfaceText("Remove every upcoming item while keeping the current track playing.")}
                  trigger={
                    <Button
                      data-testid="player-clear-upcoming"
                      disabled={upcoming.length === 0}
                      onClick={onClearQueue}
                      size="mini"
                      type="button"
                    >
                      <Icon name="trash alternate outline" />
                      <LocalizedText source={"Clear Upcoming"} /></Button>
                  }
                 {...interfaceTextProps("Remove every upcoming item while keeping the current track playing.")}/>
              </div>
            </div>
            {upcoming.length > 0 ? (
              <div className="player-queue-manager-list">
                {upcoming.map((item, index) => (
                  <div
                    className="player-queue-manager-row"
                    data-testid={`player-queue-row-${item.contentId}`}
                    key={`${item.contentId}-${index}`}
                  >
                    <span className="player-queue-manager-index">{index + 1}</span>
                    <div>
                      <strong>{getTrackLabel(item)}</strong>
                      <span>{item.artist || item.album || item.contentId}</span>
                    </div>
                    <Popup content={interfaceText("Move this track earlier in the queue.")} trigger={
                      <Button aria-label={`Move ${getTrackLabel(item)} up`} disabled={index === 0} icon onClick={() => onMove(index + 1, index)} size="mini" type="button"><Icon name="arrow up" /></Button>
                    }  {...interfaceTextProps("Move this track earlier in the queue.")}/>
                    <Popup content={interfaceText("Move this track later in the queue.")} trigger={
                      <Button aria-label={`Move ${getTrackLabel(item)} down`} disabled={index === upcoming.length - 1} icon onClick={() => onMove(index + 1, index + 2)} size="mini" type="button"><Icon name="arrow down" /></Button>
                    }  {...interfaceTextProps("Move this track later in the queue.")}/>
                    <Popup
                      content={interfaceText("Remove this upcoming item from the local playback queue.")}
                      trigger={
                        <Button
                          aria-label={`Remove ${getTrackLabel(item)} from queue`}
                          data-testid={`player-remove-queue-${item.contentId}`}
                          icon
                          onClick={() => onRemove(index + 1)}
                          size="mini"
                          type="button"
                        >
                          <Icon name="close" />
                        </Button>
                      }
                     {...interfaceTextProps("Remove this upcoming item from the local playback queue.")}/>
                  </div>
                ))}
              </div>
            ) : (
              <div className="player-queue-manager-empty">
                <LocalizedText source={"No upcoming tracks."} /></div>
            )}
          </section>
          {handoffStatus ? (
            <Message aria-live="polite" compact role="status" size="mini">
              {handoffStatus}
            </Message>
          ) : null}
          <section>
            <div className="player-panel-title"><LocalizedText source={"Recent"} /></div>
            {history.length > 0 ? (
              <div className="player-queue-manager-list">
                {history.slice(0, 5).map((item, index) => (
                  <div
                    className="player-queue-manager-row"
                    key={`${item.contentId}-${index}`}
                  >
                    <Icon name="history" />
                    <div>
                      <strong>{getTrackLabel(item)}</strong>
                      <span>{item.artist || item.album || item.contentId}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="player-queue-manager-empty">
                <LocalizedText source={"No recent tracks in this session."} /></div>
            )}
          </section>
        </div>
      </Modal.Content>
      <Modal.Actions>
        <Popup
          content={interfaceText("Jump back to the previous session track, or restart the current track if there is no history.")}
          trigger={
            <Button
              data-testid="player-queue-previous"
              disabled={!current}
              onClick={onPrevious}
              type="button"
            >
              <Icon name="step backward" />
              <LocalizedText source={"Previous"} /></Button>
          }
         {...interfaceTextProps("Jump back to the previous session track, or restart the current track if there is no history.")}/>
        <Popup
          content={interfaceText("Advance to the next queued track.")}
          trigger={
            <Button
              data-testid="player-queue-next"
              disabled={queue.length < 2}
              onClick={onNext}
              type="button"
            >
              <Icon name="step forward" />
              <LocalizedText source={"Next"} /></Button>
          }
         {...interfaceTextProps("Advance to the next queued track.")}/>
        <Popup
          content={interfaceText("Close the queue manager.")}
          trigger={
            <Button
              data-testid="player-queue-close"
              onClick={closeModal}
              primary
              type="button"
            >
              <Icon name="check" />
              <LocalizedText source={"Done"} /></Button>
          }
         {...interfaceTextProps("Close the queue manager.")}/>
      </Modal.Actions>
    </Modal>
  );
};

const PlayerDiscoveryShelfModal = ({ onClose, open }) => {
  useInterfaceLanguage();
  const dialog = usePlayerDialog(open);
  const [expiryDays, setExpiryDays] = useState(14);
  const [items, setItems] = useState(() => getDiscoveryShelf());
  const [message, setMessage] = useState('');
  const [requireConsensus, setRequireConsensus] = useState(true);
  const summary = getDiscoveryShelfSummary();
  const policyPreview = getDiscoveryShelfPolicyPreview({
    expiryDays,
    items,
    requireConsensus,
  });

  const refreshShelf = () => {
    setItems(getDiscoveryShelf());
  };

  const previewAction = (item) => {
    setMessage(
      interfaceText("{action} prepared for {title}. No files were moved or deleted.", { action: interfaceText(getDiscoveryShelfActionLabel(item.action)), title: item.title }),
    );
  };

  const removeItem = (key) => {
    removeDiscoveryShelfItem(key);
    refreshShelf();
  };

  const clearShelf = () => {
    clearDiscoveryShelf();
    refreshShelf();
    setMessage(interfaceText("Discovery shelf cleared from this browser."));
  };

  const copyPolicyReport = () => {
    const report = exportDiscoveryShelfPolicyReport({
      expiryDays,
      items,
      requireConsensus,
    });

    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(report).catch(() => {});
    }

    setMessage(interfaceText("Policy report prepared for {length} shelf items.", { "length": (items.length) }));
  };

  return (
    <Modal
      {...dialog.dialogProps}
      className="player-browser-modal player-discovery-shelf-modal"
      onClose={onClose}
      open={open}
      size="small"
    >
      <Modal.Header {...dialog.titleProps}><LocalizedText source={"Discovery Shelf"} /></Modal.Header>
      <Modal.Content>
        <div className="player-shelf-summary" data-testid="player-shelf-summary">
          <div>
            <strong>{summary.total}</strong>
            <span><LocalizedText source={"local review items"} /></span>
          </div>
          <div>
            <strong>{summary['promote-preview']}</strong>
            <span><LocalizedText source={"promote previews"} /></span>
          </div>
          <div>
            <strong>{summary['archive-preview']}</strong>
            <span><LocalizedText source={"archive previews"} /></span>
          </div>
          <div>
            <strong>{summary['expiry-watch']}</strong>
            <span><LocalizedText source={"expiry watch"} /></span>
          </div>
        </div>
        {message ? (
          <Message compact size="mini">
            {message}
          </Message>
        ) : null}
        <section className="player-shelf-policy">
          <div className="player-panel-title"><LocalizedText source={"Policy Preview"} /></div>
          <div className="player-shelf-policy-controls">
            <label htmlFor="player-shelf-expiry-days"><LocalizedText source={"Expire unrated after"} /></label>
            <Input
              aria-label={interfaceText("Discovery shelf expiry days")}
              data-testid="player-shelf-expiry-days"
              id="player-shelf-expiry-days"
              min="1"
              onChange={(event) => setExpiryDays(event.target.value)}
              size="mini"
              type="number"
              value={expiryDays}
             {...interfaceTextProps("Discovery shelf expiry days")}/>
            <Popup
              content={interfaceText("Require shared-library consensus before any destructive archive or expiry action can be applied later.")}
              trigger={
                <Checkbox
                  checked={requireConsensus}
                  data-testid="player-shelf-require-consensus"
                  label={interfaceText("Consensus for destructive actions")}
                  onChange={(_, data) => setRequireConsensus(Boolean(data.checked))}
                  toggle
                 {...interfaceTextProps("Consensus for destructive actions")}/>
              }
             {...interfaceTextProps("Require shared-library consensus before any destructive archive or expiry action can be applied later.")}/>
          </div>
          <div className="player-shelf-policy-preview" data-testid="player-shelf-policy-preview">
            <span>{policyPreview.promote} <LocalizedText source={"promote"} /></span>
            <span>{policyPreview.archive} <LocalizedText source={"archive"} /></span>
            <span>{policyPreview.expire} <LocalizedText source={"expire"} /></span>
            <span>{policyPreview.review} <LocalizedText source={"review"} /></span>
            <span>{policyPreview.blockedByConsensus} <LocalizedText source={"consensus gated"} /></span>
          </div>
          <Popup
            content={interfaceText("Copy a text report of the current shelf policy preview for review. This does not apply any action.")}
            trigger={
              <Button
                data-testid="player-shelf-copy-policy-report"
                disabled={items.length === 0}
                onClick={copyPolicyReport}
                size="mini"
                type="button"
              >
                <Icon name="copy" />
                <LocalizedText source={"Copy Report"} /></Button>
            }
           {...interfaceTextProps("Copy a text report of the current shelf policy preview for review. This does not apply any action.")}/>
        </section>
        <div className="player-shelf-list">
          {items.length > 0 ? items.map((item) => (
            <div
              className="player-shelf-row"
              data-testid={`player-shelf-row-${item.key}`}
              key={item.key}
            >
              <div className="player-shelf-rating">{item.rating || '-'}</div>
              <div className="player-shelf-track">
                <strong>{item.title}</strong>
                <span>
                  {[item.artist, item.album].filter(Boolean).join(' - ') || <LocalizedText source={"Local discovery item"} />}
                </span>
              </div>
              <Label size="mini">
                {interfaceText(getDiscoveryShelfActionLabel(item.action))}
              </Label>
              <Popup
                content={interfaceText("Preview the shelf action. This does not move, delete, share, download, or publish anything.")}
                trigger={
                  <Button
                    aria-label={`Preview ${item.title || item.artist || 'discovery shelf item'}`}
                    data-testid={`player-shelf-preview-${item.key}`}
                    icon
                    onClick={() => previewAction(item)}
                    size="mini"
                    type="button"
                  >
                    <Icon name="eye" />
                  </Button>
                }
               {...interfaceTextProps("Preview the shelf action. This does not move, delete, share, download, or publish anything.")}/>
              <Popup
                content={interfaceText("Remove this local review item from the browser-only shelf.")}
                trigger={
                  <Button
                    aria-label={`Remove ${item.title || item.artist || 'discovery shelf item'} from the discovery shelf`}
                    data-testid={`player-shelf-remove-${item.key}`}
                    icon
                    onClick={() => removeItem(item.key)}
                    size="mini"
                    type="button"
                  >
                    <Icon name="trash alternate outline" />
                  </Button>
                }
               {...interfaceTextProps("Remove this local review item from the browser-only shelf.")}/>
            </div>
          )) : (
            <div className="player-queue-manager-empty">
              <LocalizedText source={"Rate tracks in the player to build a local discovery review shelf."} /></div>
          )}
        </div>
      </Modal.Content>
      <Modal.Actions>
        <Popup
          content={interfaceText("Clear browser-local discovery shelf review items. This does not affect files or ratings.")}
          trigger={
            <Button
              data-testid="player-clear-discovery-shelf"
              disabled={items.length === 0}
              onClick={clearShelf}
              type="button"
            >
              <Icon name="trash" />
              <LocalizedText source={"Clear Shelf"} /></Button>
          }
         {...interfaceTextProps("Clear browser-local discovery shelf review items. This does not affect files or ratings.")}/>
        <Popup
          content={interfaceText("Close the local discovery shelf.")}
          trigger={
            <Button
              data-testid="player-close-discovery-shelf"
              onClick={onClose}
              primary
              type="button"
            >
              <Icon name="check" />
              <LocalizedText source={"Done"} /></Button>
          }
         {...interfaceTextProps("Close the local discovery shelf.")}/>
      </Modal.Actions>
    </Modal>
  );
};

const PlayerStatsModal = ({ onClose, onOpenSearch, open }) => {
  useInterfaceLanguage();
  const dialog = usePlayerDialog(open);
  const fileInputRef = useRef(null);
  const importFileRequestRef = useRef(0);
  const [rangeDays, setRangeDays] = useState(30);
  const [importText, setImportText] = useState('');
  const [importStatus, setImportStatus] = useState(null);
  const [runningSeedSearches, setRunningSeedSearches] = useState(false);
  const [scrobblingRecent, setScrobblingRecent] = useState(false);
  const [savingSeedWishlist, setSavingSeedWishlist] = useState(false);
  const [stats, setStats] = useState(() =>
    getListeningStats({ rangeDays: 30 }),
  );
  const recommendationSeeds = getListeningRecommendationSeeds(stats);
  const refreshStats = useCallback((nextRangeDays = rangeDays) => {
    setStats(getListeningStats({ rangeDays: nextRangeDays }));
  }, [rangeDays]);

  const clearStats = () => {
    clearListeningHistory();
    setImportStatus(null);
    refreshStats();
  };

  const updateRange = (nextRangeDays) => {
    setRangeDays(nextRangeDays);
    refreshStats(nextRangeDays);
  };

  const importHistory = () => {
    importFileRequestRef.current += 1;
    const result = importListeningHistory(importText);
    setImportStatus(
      interfaceText('{imported} imported, {skipped} skipped as duplicates or incomplete rows.', {
        imported: result.imported,
        skipped: result.skipped,
      }),
    );
    setImportText('');
    refreshStats();
  };

  const copyHistory = (format) => {
    const content = format === 'csv'
      ? exportListeningHistoryCsv()
      : exportListeningHistoryJson();

    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(content).catch(() => {});
    }

    setImportStatus(interfaceText('Prepared {format} export for {count} plays.', {
      format: format.toUpperCase(),
      count: stats.history.length,
    }));
  };

  const startSeedSearches = async () => {
    const queries = getListeningRecommendationQueries(stats, { limit: 3 });
    if (queries.length === 0) {
      setImportStatus(interfaceText('No listening seeds are ready to search.'));
      return;
    }

    try {
      setRunningSeedSearches(true);
      const count = await searches.createBatch({ queries });
      setImportStatus(interfaceText(
        count === 1 ? 'Started 1 bounded listening seed search.' : 'Started {count} bounded listening seed searches.',
        { count },
      ));
    } catch {
      setImportStatus(interfaceText('Unable to start listening seed searches.'));
    } finally {
      setRunningSeedSearches(false);
    }
  };

  const addSeedsToWishlist = async () => {
    const queries = getListeningRecommendationQueries(stats, { limit: 5 });
    if (queries.length === 0) {
      setImportStatus(interfaceText('No listening seeds are ready for Wishlist.'));
      return;
    }

    try {
      setSavingSeedWishlist(true);
      await queries.reduce(
        (chain, searchText) =>
          chain.then(() =>
            wishlistAPI.create({
              autoDownload: false,
              enabled: true,
              filter: '',
              maxResults: 50,
              searchText,
            }),
          ),
        Promise.resolve(),
      );
      setImportStatus(interfaceText(
        queries.length === 1 ? 'Added 1 listening seed to Wishlist.' : 'Added {count} listening seeds to Wishlist.',
        { count: queries.length },
      ));
    } catch {
      setImportStatus(interfaceText('Unable to add listening seeds to Wishlist.'));
    } finally {
      setSavingSeedWishlist(false);
    }
  };

  const scrobbleRecentHistory = async () => {
    try {
      setScrobblingRecent(true);
      const result = await listenBrainz.submitListeningHistory(stats.history, {
        limit: 10,
      });
      setImportStatus(
        result.submitted > 0
          ? interfaceText(
            result.submitted === 1
              ? 'Submitted 1 recent listen to ListenBrainz.'
              : 'Submitted {count} recent listens to ListenBrainz.',
            { count: result.submitted },
          )
          : interfaceText('No ListenBrainz token or eligible recent listens are available.'),
      );
    } catch {
      setImportStatus(interfaceText('Unable to submit recent listens to ListenBrainz.'));
    } finally {
      setScrobblingRecent(false);
    }
  };

  const readImportFile = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const requestId = ++importFileRequestRef.current;
    file.text().then((content) => {
      if (requestId !== importFileRequestRef.current) return;
      setImportText(content);
      setImportStatus(interfaceText('Loaded {fileName} for review.', { fileName: file.name }));
    }).catch(() => {
      if (requestId === importFileRequestRef.current) {
        setImportStatus(interfaceText('Could not read {fileName}.', { fileName: file.name }));
      }
    });
    event.target.value = '';
  };

  const renderList = (items, emptyText) => (
    items.length > 0 ? (
      <div className="player-stats-list">
        {items.map((item, index) => (
          <div className="player-stats-row" key={`${item.label || item.title}-${index}`}>
            <span>{index + 1}</span>
            <strong>{item.label || item.title}</strong>
            <em>{item.plays ? <LocalizedText source={"{plays} plays"} values={{ "plays": (item.plays) }} /> : item.artist || item.album || ''}</em>
          </div>
        ))}
      </div>
    ) : (
      <div className="player-queue-manager-empty">{emptyText}</div>
    )
  );

  return (
    <Modal
      {...dialog.dialogProps}
      className="player-browser-modal player-stats-modal"
      onClose={onClose}
      open={open}
      size="small"
    >
      <Modal.Header {...dialog.titleProps}><LocalizedText source={"Listening Stats"} /></Modal.Header>
      <Modal.Content>
        <div className="player-stats-summary" data-testid="player-stats-summary">
          <Icon name="bar chart" />
          <div>
            <strong>{stats.totalPlays}</strong>
            <span>
              <LocalizedText source={"local plays recorded in this browser"} />{rangeDays ? <LocalizedText source={"over {rangeDays} days"} values={{ "rangeDays": (rangeDays) }} /> : <LocalizedText source={"overall"} />}
            </span>
          </div>
        </div>
        <div className="player-stats-ranges" role="group" aria-label={interfaceText("Listening stats range")} {...interfaceTextProps("Listening stats range")}>
          {[
            { label: interfaceText("7D"), value: 7 },
            { label: interfaceText("30D"), value: 30 },
            { label: interfaceText("90D"), value: 90 },
            { label: interfaceText("All"), value: null },
          ].map((range) => (
            <Popup
              content={range.value
                ? interfaceText('Show listening statistics from the last {days} days.', { days: range.value })
                : interfaceText('Show listening statistics from all recorded plays.')}
              key={range.label}
              trigger={
                <Button
                  active={rangeDays === range.value}
                  aria-label={range.value
                    ? interfaceText('Show last {days} days of listening statistics', { days: range.value })
                    : interfaceText('Show all listening statistics')}
                  data-testid={`player-stats-range-${range.label}`}
                  onClick={() => updateRange(range.value)}
                  size="mini"
                  type="button"
                >
                  {range.label}
                </Button>
              }
            />
          ))}
        </div>
        <div className="player-stats-grid">
          <section>
            <div className="player-panel-title"><LocalizedText source={"Top Artists"} /></div>
            {renderList(stats.topArtists, interfaceText('No artist plays recorded yet.'))}
          </section>
          <section>
            <div className="player-panel-title"><LocalizedText source={"Top Tracks"} /></div>
            {renderList(stats.topTracks, interfaceText('No track plays recorded yet.'))}
          </section>
          <section>
            <div className="player-panel-title"><LocalizedText source={"Top Genres"} /></div>
            {renderList(stats.topGenres, interfaceText('No genre metadata recorded yet.'))}
          </section>
          <section>
            <div className="player-panel-title"><LocalizedText source={"Recent"} /></div>
            {renderList(stats.recent, interfaceText('No recent plays recorded yet.'))}
          </section>
          <section>
            <div className="player-panel-title"><LocalizedText source={"Forgotten Favorites"} /></div>
            {renderList(
              stats.forgottenFavorites,
              interfaceText('No older repeat plays outside this range yet.'),
            )}
          </section>
        </div>
        <section className="player-stats-recommendations">
          <div className="player-panel-title"><LocalizedText source={"Recommendation Seeds"} /></div>
          {recommendationSeeds.length > 0 ? (
            <>
              <div className="player-stats-seed-list">
                {recommendationSeeds.map((seed) => (
                  <div className="player-stats-seed-row" key={`${seed.type}-${seed.query}`}>
                    <div>
                      <strong>{seed.label}</strong>
                      <span>{seed.type} - {seed.basis}</span>
                    </div>
                    <Popup
                      content={interfaceText("Open this local listening seed as a normal Search page query. Network search starts only after you choose to search.")}
                      trigger={
                        <Button
                          aria-label={interfaceText("Search {label}", { "label": (seed.label) })}
                          data-testid={`player-stats-search-seed-${seed.query}`}
                          icon
                          onClick={() => onOpenSearch(seed.query)}
                          size="mini"
                          type="button"
                         {...interfaceTextProps("Search {label}")}>
                          <Icon name="search" />
                        </Button>
                      }
                     {...interfaceTextProps("Open this local listening seed as a normal Search page query. Network search starts only after you choose to search.")}/>
                  </div>
                ))}
              </div>
              <Popup
                content={interfaceText("Start up to three live searches from the strongest listening seeds. This only starts searches; it does not browse peers, queue downloads, or mutate files.")}
                trigger={
                  <Button
                    data-testid="player-stats-start-seed-searches"
                    loading={runningSeedSearches}
                    onClick={startSeedSearches}
                    size="mini"
                    type="button"
                  >
                    <Icon name="search" />
                    <LocalizedText source={"Start Searches"} /></Button>
                }
               {...interfaceTextProps("Start up to three live searches from the strongest listening seeds. This only starts searches; it does not browse peers, queue downloads, or mutate files.")}/>
              <Popup
                content={interfaceText("Add up to five listening seeds to Wishlist as enabled manual-acquisition requests. Auto-download stays off.")}
                trigger={
                  <Button
                    data-testid="player-stats-add-seeds-to-wishlist"
                    loading={savingSeedWishlist}
                    onClick={addSeedsToWishlist}
                    size="mini"
                    type="button"
                  >
                    <Icon name="heart" />
                    <LocalizedText source={"Add Wishlist"} /></Button>
                }
               {...interfaceTextProps("Add up to five listening seeds to Wishlist as enabled manual-acquisition requests. Auto-download stays off.")}/>
            </>
          ) : (
            <div className="player-queue-manager-empty">
              <LocalizedText source={"Play more tracks locally to build recommendation seeds."} /></div>
          )}
        </section>
        <section className="player-stats-import">
          <div className="player-panel-title"><LocalizedText source={"Media Server Import"} /></div>
          <TextArea
            aria-label={interfaceText("Paste exported media server play history")}
            data-testid="player-listening-history-import-text"
            onChange={(event) => {
              importFileRequestRef.current += 1;
              setImportText(event.target.value);
            }}
            placeholder={interfaceText("Paste Plex, Jellyfin, Navidrome, or generic CSV/JSON play history here for local import.")}
            rows={4}
            value={importText}
           {...interfaceTextProps("Paste exported media server play history")}/>
          {importStatus ? (
            <Message compact size="mini">
              {importStatus}
            </Message>
          ) : null}
          <div className="player-stats-import-actions">
            <input
              accept=".csv,.json,.txt"
              aria-label={interfaceText("Choose media server history file")}
              data-testid="player-listening-history-file"
              onChange={readImportFile}
              ref={fileInputRef}
              type="file"
             {...interfaceTextProps("Choose media server history file")}/>
            <Popup
              content={interfaceText("Choose a local CSV or JSON export from Plex, Jellyfin, Navidrome, or another media server. The file is read in this browser only.")}
              trigger={
                <Button
                  data-testid="player-listening-history-choose-file"
                  onClick={() => fileInputRef.current?.click()}
                  size="mini"
                  type="button"
                >
                  <Icon name="folder open" />
                  <LocalizedText source={"Choose File"} /></Button>
              }
             {...interfaceTextProps("Choose a local CSV or JSON export from Plex, Jellyfin, Navidrome, or another media server. The file is read in this browser only.")}/>
            <Popup
              content={interfaceText("Import the pasted or chosen play history into browser-local listening stats with duplicate suppression.")}
              trigger={
                <Button
                  data-testid="player-listening-history-import"
                  disabled={!importText.trim()}
                  onClick={importHistory}
                  primary
                  size="mini"
                  type="button"
                >
                  <Icon name="upload" />
                  <LocalizedText source={"Import"} /></Button>
              }
             {...interfaceTextProps("Import the pasted or chosen play history into browser-local listening stats with duplicate suppression.")}/>
            <Popup
              content={interfaceText("Copy the browser-local listening history as JSON for backup or review.")}
              trigger={
                <Button
                  data-testid="player-listening-history-export-json"
                  disabled={stats.history.length === 0}
                  onClick={() => copyHistory('json')}
                  size="mini"
                  type="button"
                >
                  <Icon name="copy" />
                  JSON
                </Button>
              }
             {...interfaceTextProps("Copy the browser-local listening history as JSON for backup or review.")}/>
            <Popup
              content={interfaceText("Copy the browser-local listening history as CSV for media-server or spreadsheet review.")}
              trigger={
                <Button
                  data-testid="player-listening-history-export-csv"
                  disabled={stats.history.length === 0}
                  onClick={() => copyHistory('csv')}
                  size="mini"
                  type="button"
                >
                  <Icon name="table" />
                  CSV
                </Button>
              }
             {...interfaceTextProps("Copy the browser-local listening history as CSV for media-server or spreadsheet review.")}/>
            <Popup
              content={interfaceText("Submit up to ten recent browser-local plays to ListenBrainz using the saved token. This does not search, browse peers, download, or mutate files.")}
              trigger={
                <Button
                  data-testid="player-listening-history-scrobble-recent"
                  disabled={stats.history.length === 0}
                  loading={scrobblingRecent}
                  onClick={scrobbleRecentHistory}
                  size="mini"
                  type="button"
                >
                  <Icon name="send" />
                  <LocalizedText source={"Scrobble Recent"} /></Button>
              }
             {...interfaceTextProps("Submit up to ten recent browser-local plays to ListenBrainz using the saved token. This does not search, browse peers, download, or mutate files.")}/>
          </div>
        </section>
      </Modal.Content>
      <Modal.Actions>
        <Popup
          content={interfaceText("Clear only the browser-local listening history used for this stats view.")}
          trigger={
            <Button
              data-testid="player-clear-listening-history"
              disabled={stats.totalPlays === 0}
              onClick={clearStats}
              type="button"
            >
              <Icon name="trash alternate outline" />
              <LocalizedText source={"Clear Local History"} /></Button>
          }
         {...interfaceTextProps("Clear only the browser-local listening history used for this stats view.")}/>
        <Popup
          content={interfaceText("Close listening stats.")}
          trigger={
            <Button
              data-testid="player-close-listening-stats"
              onClick={onClose}
              primary
              type="button"
            >
              <Icon name="check" />
              <LocalizedText source={"Done"} /></Button>
          }
         {...interfaceTextProps("Close listening stats.")}/>
      </Modal.Actions>
    </Modal>
  );
};

const PlayerLauncher = ({ compact = false, onPlayItem, onPlayNext }) => {
  useInterfaceLanguage();
  const navigate = useNavigate();
  const [collections, setCollections] = useState([]);
  const [collectionsLoading, setCollectionsLoading] = useState(false);
  const [collectionsOpen, setCollectionsOpen] = useState(false);
  const [selectedCollection, setSelectedCollection] = useState(null);
  const [collectionItems, setCollectionItems] = useState([]);
  const [collectionItemsLoading, setCollectionItemsLoading] = useState(false);
  const collectionRequestRef = useRef(0);
  const [items, setItems] = useState([]);
  const [browserDirectories, setBrowserDirectories] = useState([]);
  const [browserBreadcrumbs, setBrowserBreadcrumbs] = useState([]);
  const [browserHasMore, setBrowserHasMore] = useState(false);
  const [browserOffset, setBrowserOffset] = useState(0);
  const [browserPath, setBrowserPath] = useState('');
  const [browserStats, setBrowserStats] = useState({
    duplicatesRemoved: 0,
    totalDirectories: 0,
    totalFiles: 0,
  });
  const [filesOpen, setFilesOpen] = useState(false);
  const collectionsDialog = usePlayerDialog(collectionsOpen);
  const filesDialog = usePlayerDialog(filesOpen);
  const [query, setQuery] = useState('');
  const [itemsLoading, setItemsLoading] = useState(false);

  useEffect(() => {
    if (!collectionsOpen) return undefined;
    let canceled = false;
    collectionsAPI
      .getCollections()
      .then((response) => {
        if (!canceled) setCollections(asArray(response.data));
      })
      .catch(() => {
        if (!canceled) setCollections([]);
      })
      .finally(() => {
        if (!canceled) setCollectionsLoading(false);
      });

    return () => {
      canceled = true;
    };
  }, [collectionsOpen]);

  useEffect(() => {
    if (!filesOpen) {
      setItemsLoading(false);
      return undefined;
    }

    if (query && query.length < 2) {
      setItemsLoading(false);
      setItems([]);
      setBrowserDirectories([]);
      setBrowserBreadcrumbs([]);
      setBrowserHasMore(false);
      setBrowserStats({ duplicatesRemoved: 0, totalDirectories: 0, totalFiles: 0 });
      return undefined;
    }

    let canceled = false;
    const timeoutId = window.setTimeout(() => {
      setItemsLoading(true);
      collectionsAPI
        .browseLibraryItems({
          kinds: 'Audio',
          limit: playerBrowserPageSize,
          offset: browserOffset,
          path: browserPath,
          query,
        })
        .then((response) => {
          if (!canceled) {
            setItems(asArray(response.data?.files));
            setBrowserDirectories(asArray(response.data?.directories));
            setBrowserBreadcrumbs(asArray(response.data?.breadcrumbs));
            setBrowserHasMore(Boolean(response.data?.hasMore));
            setBrowserStats({
              duplicatesRemoved: response.data?.duplicatesRemoved || 0,
              totalDirectories: response.data?.totalDirectories || 0,
              totalFiles: response.data?.totalFiles || 0,
            });
          }
        })
        .catch(() => {
          if (!canceled) {
            setItems([]);
            setBrowserDirectories([]);
            setBrowserBreadcrumbs([]);
            setBrowserHasMore(false);
            setBrowserStats({ duplicatesRemoved: 0, totalDirectories: 0, totalFiles: 0 });
          }
        })
        .finally(() => {
          if (!canceled) setItemsLoading(false);
        });
    }, query ? 200 : 0);

    return () => {
      canceled = true;
      window.clearTimeout(timeoutId);
    };
  }, [browserOffset, browserPath, filesOpen, query]);

  const selectCollection = (collection) => {
    const requestId = ++collectionRequestRef.current;
    setSelectedCollection(collection);
    setCollectionItems([]);
    setCollectionItemsLoading(true);
    collectionsAPI
      .getCollectionItems(collection.id)
      .then((response) => {
        if (requestId === collectionRequestRef.current) {
          setCollectionItems(asArray(response.data));
        }
      })
      .catch(() => {
        if (requestId === collectionRequestRef.current) setCollectionItems([]);
      })
      .finally(() => {
        if (requestId === collectionRequestRef.current) setCollectionItemsLoading(false);
      });
  };

  const closeCollections = () => {
    collectionRequestRef.current += 1;
    setCollectionsOpen(false);
    setSelectedCollection(null);
    setCollectionItems([]);
    setCollectionItemsLoading(false);
  };

  const playAndClose = (item) => {
    onPlayItem(item);
    setFilesOpen(false);
    closeCollections();
  };

  const openFileBrowser = () => {
    setBrowserOffset(0);
    setBrowserPath('');
    setFilesOpen(true);
    setQuery('');
  };

  const openBrowserPath = (path) => {
    setBrowserOffset(0);
    setBrowserPath(path || '');
    setQuery('');
  };

  const updateBrowserQuery = (value) => {
    setBrowserOffset(0);
    setQuery(value || '');
  };

  const shownFileCount = Math.min(
    browserOffset + items.length,
    browserStats.totalFiles,
  );

  return (
    <div className="player-launcher">
      <Popup
        content={interfaceText("Browse your collections and play an item from a playlist or share list.")}
        trigger={
          <Button
            aria-label={interfaceText("Open collections browser")}
            className="player-library-button"
            compact
            data-testid="player-open-collections-browser"
            icon
            labelPosition={compact ? undefined : 'left'}
            onClick={() => {
              setCollectionsLoading(true);
              setCollectionsOpen(true);
            }}
            size="small"
            title={interfaceText("Open collections browser")}
           {...interfaceTextProps("Open collections browser")}>
            <Icon name="list" />
            {compact ? null : <LocalizedText source={"Collections"} />}
          </Button>
        }
       {...interfaceTextProps("Browse your collections and play an item from a playlist or share list.")}/>
      <Popup
        content={interfaceText("Browse shared and downloaded local audio that slskdN can stream in this browser.")}
        trigger={
          <Button
            aria-label={interfaceText("Open local audio file browser")}
            className="player-library-button"
            compact
            data-testid="player-open-file-browser"
            icon
            labelPosition={compact ? undefined : 'left'}
            onClick={openFileBrowser}
            size="small"
            title={interfaceText("Open local audio file browser")}
           {...interfaceTextProps("Open local audio file browser")}>
            <Icon name="folder open" />
            {compact ? null : <LocalizedText source={"Files"} />}
          </Button>
        }
       {...interfaceTextProps("Browse shared and downloaded local audio that slskdN can stream in this browser.")}/>

      <Modal
        {...collectionsDialog.dialogProps}
        className="player-browser-modal"
        data-testid="player-collection-browser-modal"
        onClose={closeCollections}
        open={collectionsOpen}
        size="large"
      >
        <Modal.Header {...collectionsDialog.titleProps}><LocalizedText source={"Choose from Collections"} /></Modal.Header>
        <Modal.Content>
          <div className="player-browser-grid">
            <Segment className="player-browser-panel">
              <Header as="h4"><LocalizedText source={"Collections"} /></Header>
              {collectionsLoading ? (
                <Message info><LocalizedText source={"Loading collections..."} /></Message>
              ) : collections.length === 0 ? (
                <Message info><LocalizedText source={"No collections found."} /></Message>
              ) : (
                <Table compact selectable>
                  <Table.Body>
                    {collections.map((collection) => (
                      <Table.Row
                        active={selectedCollection?.id === collection.id}
                        data-testid={`player-collection-row-${collection.id}`}
                        key={collection.id}
                        onClick={() => selectCollection(collection)}
                      >
                        <Table.Cell>
                          <Popup
                            content={interfaceText("Show tracks in {title} so you can choose one to play or queue.", { "title": (collection.title) })}
                            trigger={
                              <button
                                aria-label={interfaceText("Show tracks in {title}", { "title": (collection.title) })}
                                aria-pressed={selectedCollection?.id === collection.id}
                                className="player-collection-select"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  selectCollection(collection);
                                }}
                                type="button"
                               {...interfaceTextProps("Show tracks in {title}")}>
                                <strong>{collection.title}</strong>
                                <span className="player-picker-meta">
                                  {collection.type || <LocalizedText source={"Playlist"} />}
                                </span>
                              </button>
                            }
                           {...interfaceTextProps("Show tracks in {title} so you can choose one to play or queue.")}/>
                        </Table.Cell>
                      </Table.Row>
                    ))}
                  </Table.Body>
                </Table>
              )}
            </Segment>
            <Segment className="player-browser-panel">
              <Header as="h4">
                {selectedCollection?.title || <LocalizedText source={"Collection Items"} />}
              </Header>
              {!selectedCollection ? (
                <Message info><LocalizedText source={"Select a collection to see its tracks."} /></Message>
              ) : collectionItemsLoading ? (
                <Message info><LocalizedText source={"Loading collection items..."} /></Message>
              ) : collectionItems.length === 0 ? (
                <Message info><LocalizedText source={"No playable items in this collection."} /></Message>
              ) : (
                <Table compact>
                  <Table.Header>
                    <Table.Row>
                      <Table.HeaderCell><LocalizedText source={"Track"} /></Table.HeaderCell>
                      <Table.HeaderCell collapsing><LocalizedText source={"Action"} /></Table.HeaderCell>
                    </Table.Row>
                  </Table.Header>
                  <Table.Body>
                    {collectionItems.map((item) => (
                      <Table.Row key={item.id || item.contentId}>
                        <Table.Cell>
                          <strong>
                            {item.fileName || item.title || item.contentId}
                          </strong>
                          <div className="player-picker-meta">
                            {item.mediaKind || <LocalizedText source={"Audio"} />}
                          </div>
                        </Table.Cell>
                        <Table.Cell collapsing>
                          <Popup
                            content={interfaceText("Play this collection item in the browser player.")}
                            trigger={
                              <Button
                                aria-label={`Play ${item.title || item.fileName || item.contentId || 'track'} from this collection`}
                                data-testid={`player-play-collection-item-${item.contentId}`}
                                icon
                                onClick={() => playAndClose(item)}
                                size="small"
                              >
                                <Icon name="play" />
                              </Button>
                            }
                           {...interfaceTextProps("Play this collection item in the browser player.")}/>
                          <Popup content={interfaceText("Place this collection item next in the playback queue.")} trigger={
                            <Button aria-label={`Play ${item.title || item.fileName || 'track'} next`} disabled={!onPlayNext} icon onClick={() => onPlayNext(item)} size="small"><Icon name="level down alternate" /></Button>
                          }  {...interfaceTextProps("Place this collection item next in the playback queue.")}/>
                        </Table.Cell>
                      </Table.Row>
                    ))}
                  </Table.Body>
                </Table>
              )}
            </Segment>
          </div>
        </Modal.Content>
        <Modal.Actions>
          <Popup
            content={interfaceText("Open the full Collections page to create, edit, or share collections.")}
            trigger={
              <Button
                data-testid="player-manage-collections"
                onClick={() => {
                  closeCollections();
                  navigate('/collections');
                }}
              >
                <Icon name="external alternate" />
                <LocalizedText source={"Manage Collections"} /></Button>
            }
           {...interfaceTextProps("Open the full Collections page to create, edit, or share collections.")}/>
          <Popup
            content={interfaceText("Close the collection picker without changing playback.")}
            trigger={
              <Button onClick={closeCollections}><LocalizedText source={"Close"} /></Button>
            }
           {...interfaceTextProps("Close the collection picker without changing playback.")}/>
        </Modal.Actions>
      </Modal>

      <Modal
        {...filesDialog.dialogProps}
        className="player-browser-modal"
        data-testid="player-file-browser-modal"
        onClose={() => setFilesOpen(false)}
        open={filesOpen}
        size="fullscreen"
      >
        <Modal.Header {...filesDialog.titleProps}><LocalizedText source={"Browse Local Audio Library"} /></Modal.Header>
        <Modal.Content>
          <div className="player-file-explorer">
            <div className="player-file-explorer-toolbar">
              <Input
                data-testid="player-file-browser-search"
                fluid
                icon="search"
                onChange={(_, { value }) => updateBrowserQuery(value)}
                placeholder={interfaceText("Search all audio by file, artist folder, album folder, or path")}
                value={query}
               {...interfaceTextProps("Search all audio by file, artist folder, album folder, or path")}/>
              <div className="player-file-explorer-counts">
                {itemsLoading
                  ? interfaceText('Loading...')
                  : <LocalizedText source={"{shownFileCount} of {totalFiles} tracks"} values={{ "shownFileCount": (shownFileCount), "totalFiles": (browserStats.totalFiles) }} />}
                {browserStats.duplicatesRemoved > 0
                  ? <LocalizedText source={", {duplicatesRemoved} duplicates collapsed"} values={{ "duplicatesRemoved": (browserStats.duplicatesRemoved) }} />
                  : ''}
              </div>
            </div>

            <div className="player-file-explorer-breadcrumbs">
              {(browserBreadcrumbs.length > 0
                ? browserBreadcrumbs
                : [{ name: 'Library', path: '' }]).map((breadcrumb, index) => (
                  <React.Fragment key={breadcrumb.path || 'library'}>
                    {index > 0 ? <Icon name="angle right" /> : null}
                    <Popup
                      content={interfaceText("Open {name} to browse files from that folder.", { "name": (breadcrumb.name) })}
                      trigger={
                        <button
                          className="player-file-breadcrumb"
                          data-testid={`player-file-breadcrumb-${index}`}
                          onClick={() => openBrowserPath(breadcrumb.path)}
                          type="button"
                        >
                          {breadcrumb.name}
                        </button>
                      }
                     {...interfaceTextProps("Open {name} to browse files from that folder.")}/>
                  </React.Fragment>
              ))}
            </div>

            <div className="player-file-explorer-body">
              <aside className="player-file-explorer-folders">
                <div className="player-file-explorer-section-title">
                  <LocalizedText source={"Folders"} /></div>
                {query ? (
                  <Message info compact>
                    <LocalizedText source={"Clear search to browse folders."} /></Message>
                ) : browserDirectories.length === 0 ? (
                  <Message info compact>
                    <LocalizedText source={"No child folders here."} /></Message>
                ) : (
                  browserDirectories.map((directory) => (
                    <Popup
                      content={interfaceText("Open {name} to browse its tracks and subfolders.", { "name": (directory.name) })}
                      key={directory.path}
                      trigger={
                        <button
                          className="player-file-folder-row"
                          data-testid={`player-file-folder-${directory.path}`}
                          onClick={() => openBrowserPath(directory.path)}
                          type="button"
                        >
                          <Icon name="folder" />
                          <span>
                            <strong>{directory.name}</strong>
                            <small>
                              {directory.fileCount} <LocalizedText source={"tracks"} />{directory.childDirectoryCount
                                ? <LocalizedText source={", {childDirectoryCount} folders"} values={{ "childDirectoryCount": (directory.childDirectoryCount) }} />
                                : ''}
                            </small>
                          </span>
                        </button>
                      }
                     {...interfaceTextProps("Open {name} to browse its tracks and subfolders.")}/>
                  ))
                )}
              </aside>

              <section className="player-file-explorer-files">
                <div className="player-file-explorer-section-title">
                  {query ? <LocalizedText source={"Search Results"} /> : browserPath || <LocalizedText source={"Library Root"} />}
                </div>
                {itemsLoading ? (
                  <Message info><LocalizedText source={"Loading audio files..."} /></Message>
                ) : items.length === 0 ? (
                  <Message info>
                    {query && query.length < 2
                      ? <LocalizedText source={"Type at least two characters to search."} />
                      : <LocalizedText source={"No local audio files found here."} />}
                  </Message>
                ) : (
                  <Table compact selectable>
                    <Table.Header>
                      <Table.Row>
                        <Table.HeaderCell><LocalizedText source={"Track"} /></Table.HeaderCell>
                        <Table.HeaderCell><LocalizedText source={"Location"} /></Table.HeaderCell>
                        <Table.HeaderCell collapsing><LocalizedText source={"Copies"} /></Table.HeaderCell>
                        <Table.HeaderCell collapsing><LocalizedText source={"Action"} /></Table.HeaderCell>
                      </Table.Row>
                    </Table.Header>
                    <Table.Body>
                      {items.map((item) => (
                        <Table.Row
                          data-testid={`player-file-row-${item.contentId}`}
                          key={`${item.contentId}-${item.path}`}
                          onDoubleClick={() => playAndClose(item)}
                        >
                          <Table.Cell>
                            <strong>{item.fileName || item.contentId}</strong>
                            <div className="player-picker-meta">
                              {item.mediaKind || <LocalizedText source={"Audio"} />}
                              {item.bytes ? ` - ${Math.round(item.bytes / 1024 / 1024)} MB` : ''}
                            </div>
                          </Table.Cell>
                          <Table.Cell>
                            <span className="player-file-path">{item.path}</span>
                          </Table.Cell>
                          <Table.Cell collapsing>
                            {item.duplicateCount > 1 ? item.duplicateCount : ''}
                          </Table.Cell>
                          <Table.Cell collapsing>
                            <Popup
                              content={interfaceText("Play this local file in the browser player.")}
                              trigger={
                                <Button
                                  aria-label={`Play ${item.fileName || item.contentId}`}
                                  data-testid={`player-play-file-${item.contentId}`}
                                  icon
                                  onClick={() => playAndClose(item)}
                                  size="small"
                                  title={`Play ${item.fileName || item.contentId}`}
                                >
                                  <Icon name="play" />
                                </Button>
                              }
                             {...interfaceTextProps("Play this local file in the browser player.")}/>
                            <Popup content={interfaceText("Place this file next in the playback queue.")} trigger={
                              <Button aria-label={`Play ${item.fileName || 'file'} next`} disabled={!onPlayNext} icon onClick={() => onPlayNext(item)} size="small"><Icon name="level down alternate" /></Button>
                            }  {...interfaceTextProps("Place this file next in the playback queue.")}/>
                          </Table.Cell>
                        </Table.Row>
                      ))}
                    </Table.Body>
                  </Table>
                )}
                <div className="player-file-explorer-pager">
                  <Popup
                    content={interfaceText("Move to the previous page of files in this folder or search.")}
                    trigger={
                      <Button
                        disabled={browserOffset === 0 || itemsLoading}
                        onClick={() =>
                          setBrowserOffset(Math.max(0, browserOffset - playerBrowserPageSize))
                        }
                        size="small"
                      >
                        <Icon name="angle left" />
                        <LocalizedText source={"Previous"} /></Button>
                    }
                   {...interfaceTextProps("Move to the previous page of files in this folder or search.")}/>
                  <Popup
                    content={interfaceText("Move to the next page of files in this folder or search.")}
                    trigger={
                      <Button
                        disabled={!browserHasMore || itemsLoading}
                        onClick={() =>
                          setBrowserOffset(browserOffset + playerBrowserPageSize)
                        }
                        size="small"
                      >
                        <LocalizedText source={"Next"} /><Icon name="angle right" />
                      </Button>
                    }
                   {...interfaceTextProps("Move to the next page of files in this folder or search.")}/>
                </div>
              </section>
            </div>
          </div>
        </Modal.Content>
        <Modal.Actions>
          <Popup
            content={interfaceText("Close the local file browser without changing playback.")}
            trigger={<Button onClick={() => setFilesOpen(false)}><LocalizedText source={"Close"} /></Button>}
           {...interfaceTextProps("Close the local file browser without changing playback.")}/>
        </Modal.Actions>
      </Modal>
    </div>
  );
};

const PlayerVisualTile = ({
  audioElement,
  controlsOpen,
  current,
  mode,
  onModeChange,
  onTileModeChange,
  tileMode,
}) => {
  useInterfaceLanguage();
  const tileModes = ['art', 'butterchurn', 'native-webgl2', 'native-webgpu', 'spectrum', 'scope'];
  const visualizerTileModes = ['butterchurn', 'native-webgl2', 'native-webgpu'];
  const tileModeLabels = {
    art: 'album art',
    butterchurn: 'Butterchurn',
    'native-webgl2': 'MilkDrop3 WebGL2',
    'native-webgpu': 'MilkDrop3 WebGPU',
    scope: 'signal scope',
    spectrum: 'spectrum bars',
  };
  const localizedTileModeLabel = (mode) => {
    if (mode === 'art') return interfaceText('album art');
    if (mode === 'scope') return interfaceText('signal scope');
    if (mode === 'spectrum') return interfaceText('spectrum bars');
    return tileModeLabels[mode];
  };
  const tileModeIcons = {
    butterchurn: 'magic',
    'native-webgl2': 'microchip',
    'native-webgpu': 'bolt',
    scope: 'signal',
    spectrum: 'chart bar',
  };
  const tileRef = useRef(null);
  const [visualizerRevision, setVisualizerRevision] = useState(0);
  const [allowReducedMotionAnalyzer, setAllowReducedMotionAnalyzer] = useState(false);
  const prefersReducedMotion = usePrefersReducedMotion();
  const title = current?.title || current?.fileName || 'slskdN';
  const artist = current?.artist || '';
  const initials = (artist || title)
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase() || 'N';
  const artworkUrl = current?.artworkUrl;
  const normalizedTileMode = tileModes.includes(tileMode) ? tileMode : 'art';
  const effectiveTileMode = mode === 'off' && visualizerTileModes.includes(normalizedTileMode)
    ? 'art'
    : normalizedTileMode;
  const showingVisualizer = visualizerTileModes.includes(effectiveTileMode);
  const showingAnalyzer = ['spectrum', 'scope'].includes(effectiveTileMode);
  const analyzerMotionSuppressed = showingAnalyzer
    && prefersReducedMotion
    && !allowReducedMotionAnalyzer;
  const nextTileMode = tileModes[
    (tileModes.indexOf(effectiveTileMode) + 1) % tileModes.length
  ];
  const visualizerDisplayMode = mode === 'off' ? 'inline' : mode;
  const preferredVisualizerMode = visualizerTileModes.includes(normalizedTileMode)
    ? normalizedTileMode
    : readStoredVisualizerEngineTileMode();
  useEffect(() => {
    if (!showingAnalyzer) setAllowReducedMotionAnalyzer(false);
  }, [showingAnalyzer]);
  const setTileMode = (nextMode) => {
    onTileModeChange(nextMode);
    if (visualizerTileModes.includes(nextMode) && mode === 'off') {
      onModeChange('inline');
    }
    if (visualizerTileModes.includes(nextMode)) {
      setVisualizerRevision((revision) => revision + 1);
    }
  };
  const switchTileMode = (event, nextMode) => {
    event.stopPropagation();
    setTileMode(nextMode);
  };
  const showVisualizerWindow = (event) => {
    event.stopPropagation();
    if (!showingVisualizer) {
      onTileModeChange(preferredVisualizerMode);
    }
    onModeChange('fullwindow');
  };
  const showVisualizerFullscreen = async (event) => {
    event.stopPropagation();
    if (!showingVisualizer) {
      onTileModeChange(preferredVisualizerMode);
    }
    if (tileRef.current?.requestFullscreen) {
      try {
        await tileRef.current.requestFullscreen();
      } catch {
        // Keep the visualizer in fullscreen layout even if the browser denies the request.
      }
    }
    onModeChange('fullscreen');
  };
  const handleTileActivate = () => setTileMode(nextTileMode);

  return (
    <div className="player-visual-tile" data-controls-open={controlsOpen}>
      <div className="player-visual-stage-shell">
        <Popup
          content={interfaceText('Show {mode} in this square.', {
            mode: localizedTileModeLabel(nextTileMode),
          })}
          trigger={
            <div
              aria-label={analyzerMotionSuppressed
                ? interfaceText(
                  'Show {mode} in player visual tile. Analyzer animation is paused because reduced motion is enabled',
                  { mode: localizedTileModeLabel(nextTileMode) },
                )
                : interfaceText('Show {mode} in player visual tile', {
                  mode: localizedTileModeLabel(nextTileMode),
                })}
              role="button"
              className="player-visual-stage"
              data-testid="player-visual-tile"
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  handleTileActivate();
                }
              }}
              onClick={handleTileActivate}
              ref={tileRef}
              tabIndex={0}
            >
              {showingVisualizer ? (
                <React.Suspense fallback={
                  <span className="player-visualizer-loading" role="status"><LocalizedText source={"Loading visualizer"} /></span>
                }>
                  <Visualizer
                    audioElement={audioElement}
                    compactControls
                    engineOverride={normalizedTileMode}
                    key={`${normalizedTileMode}-${visualizerRevision}`}
                    mode={visualizerDisplayMode}
                    onEngineChange={onTileModeChange}
                    onModeChange={onModeChange}
                  />
                </React.Suspense>
              ) : showingAnalyzer ? (
                <>
                  <SpectrumAnalyzer
                    allowReducedMotionAnimation={allowReducedMotionAnalyzer}
                    audioElement={audioElement}
                    className="player-visualizer-fallback"
                    mode={normalizedTileMode}
                  />
                  {analyzerMotionSuppressed ? (
                    <span aria-hidden="true" className="player-visual-tile-motion-status">
                      <LocalizedText source={"Paused"} /></span>
                  ) : null}
                </>
              ) : (
                <span className="player-album-art" data-testid="player-album-art">
                  {artworkUrl ? (
                    <img alt="" src={artworkUrl} />
                  ) : (
                    <>
                      <span className="player-album-art-glow" />
                      <span className="player-album-art-mark">{initials}</span>
                    </>
                  )}
                </span>
              )}
              {!analyzerMotionSuppressed ? (
                <span className="player-visual-affordance">
                  <Icon name={showingVisualizer ? 'magic' : (showingAnalyzer ? 'chart bar' : 'image outline')} />
                </span>
              ) : null}
            </div>
          }
        />
        {analyzerMotionSuppressed ? (
          <Popup
            content={interfaceText("Animate the analyzer until it is hidden, even though reduced motion is enabled.")}
            trigger={
              <Button
                aria-label={interfaceText("Animate analyzer anyway")}
                className="player-visual-tile-motion-override"
                data-testid="player-visual-tile-motion-override"
                icon
                onClick={() => setAllowReducedMotionAnalyzer(true)}
                size="mini"
                type="button"
               {...interfaceTextProps("Animate analyzer anyway")}>
                <Icon name="play" />
              </Button>
            }
           {...interfaceTextProps("Animate the analyzer until it is hidden, even though reduced motion is enabled.")}/>
        ) : null}
      </div>
      <div className="player-visual-tile-controls" onClick={(event) => event.stopPropagation()}>
        {['spectrum', 'scope', 'butterchurn', 'native-webgl2', 'native-webgpu'].map((option) => (
          <Popup
            content={interfaceText('Show {mode}.', { mode: localizedTileModeLabel(option) })}
            key={option}
            trigger={
              <Button
                aria-label={interfaceText('Show {mode}', { mode: localizedTileModeLabel(option) })}
                active={effectiveTileMode === option}
                toggle
                data-testid={`player-visual-tile-mode-${option}`}
                icon
                onClick={(event) => switchTileMode(event, option)}
                size="mini"
              >
                <Icon name={tileModeIcons[option]} />
              </Button>
            }
          />
        ))}
        <Popup
          content={interfaceText("Maximize the visualizer to the browser window.")}
          trigger={
            <Button
              aria-label={interfaceText("Maximize visualizer to browser window")}
              data-testid="player-visual-tile-fullwindow"
              icon
              onClick={showVisualizerWindow}
              size="mini"
             {...interfaceTextProps("Maximize visualizer to browser window")}>
              <Icon name="expand arrows alternate" />
            </Button>
          }
         {...interfaceTextProps("Maximize the visualizer to the browser window.")}/>
        <Popup
          content={interfaceText("Maximize the visualizer to fullscreen.")}
          trigger={
            <Button
              aria-label={interfaceText("Maximize visualizer to fullscreen")}
              data-testid="player-visual-tile-fullscreen"
              icon
              onClick={showVisualizerFullscreen}
              size="mini"
             {...interfaceTextProps("Maximize visualizer to fullscreen")}>
              <Icon name="expand" />
            </Button>
          }
         {...interfaceTextProps("Maximize the visualizer to fullscreen.")}/>
      </div>
    </div>
  );
};

const PlayerAnalyzerTile = ({ audioElement, mode, onModeChange }) => {
  useInterfaceLanguage();
  const [allowReducedMotionAnimation, setAllowReducedMotionAnimation] = useState(false);
  const prefersReducedMotion = usePrefersReducedMotion();
  const motionSuppressed = mode !== 'off'
    && prefersReducedMotion
    && !allowReducedMotionAnimation;
  const nextMode = { off: 'spectrum', spectrum: 'scope', scope: 'off' }[mode];
  const label = {
    off: 'Analyzer off',
    spectrum: 'Spectrum bars',
    scope: 'Signal scope',
  }[mode];
  const nextLabel = {
    off: 'turn off the analyzer',
    spectrum: 'show spectrum bars',
    scope: 'show signal scope',
  }[nextMode];

  useEffect(() => {
    if (mode === 'off') setAllowReducedMotionAnimation(false);
  }, [mode]);

  return (
    <div className="player-analyzer-tile-shell">
      <Popup
        content={interfaceText("Click to {nextLabel}.", { "nextLabel": (nextLabel) })}
        trigger={
          <div
            aria-label={`Click to ${nextLabel}${motionSuppressed
              ? '. Animation is paused because reduced motion is enabled'
              : ''}`}
            className="player-analyzer-tile"
            data-testid="player-analyzer-tile"
            onClick={() => onModeChange(nextMode)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                onModeChange(nextMode);
              }
            }}
            role="button"
            tabIndex={0}
          >
            <div className="player-analyzer-label">{label}</div>
            {mode !== 'off' ? (
              <SpectrumAnalyzer
                allowReducedMotionAnimation={allowReducedMotionAnimation}
                audioElement={audioElement}
                className="player-spectrum-switchable"
                mode={mode}
              />
            ) : null}
            {motionSuppressed ? (
              <span aria-hidden="true" className="player-analyzer-motion-status">
                <LocalizedText source={"Reduced motion"} /></span>
            ) : null}
            {!motionSuppressed ? (
              <span className="player-analyzer-affordance">
                <Icon name={{ off: 'power off', spectrum: 'signal', scope: 'chart bar' }[mode]} />
              </span>
            ) : null}
          </div>
        }
       {...interfaceTextProps("Click to {nextLabel}.")}/>
      {motionSuppressed ? (
        <Popup
          content={interfaceText("Animate the analyzer until it is turned off, even though reduced motion is enabled.")}
          trigger={
            <Button
              aria-label={interfaceText("Animate analyzer anyway")}
              className="player-analyzer-motion-override"
              data-testid="player-analyzer-motion-override"
              icon
              onClick={() => setAllowReducedMotionAnimation(true)}
              size="mini"
              type="button"
             {...interfaceTextProps("Animate analyzer anyway")}>
              <Icon name="play" />
            </Button>
          }
         {...interfaceTextProps("Animate the analyzer until it is turned off, even though reduced motion is enabled.")}/>
      ) : null}
    </div>
  );
};

const PlayerBar = () => {
  useInterfaceLanguage();
  const navigate = useNavigate();
  const audioRef = useRef(null);
  const fadeAudioRef = useRef(null);
  const renderedPrimaryAudioRef = useRef(null);
  const renderedSecondaryAudioRef = useRef(null);
  const lastSourceRef = useRef('');
  const activeItemRef = useRef(null);
  const playerBarRef = useRef(null);
  const scrobbledRef = useRef('');
  const playedSecondsRef = useRef(0);
  const playingNowSentRef = useRef(false);
  const pipRef = useRef({ data: null, raf: null, timer: null, win: null });
  const pipRequestRef = useRef(0);
  const fadeTimeoutRef = useRef(null);
  const fadeOutgoingRef = useRef(null);
  const fadeRequestRef = useRef(0);
  const playRequestRef = useRef(0);
  const crossfadeStartedRef = useRef(null);
  const localFileSequenceRef = useRef(0);
  const {
    broadcastStatus,
    reportPlaybackEvent,
    retryBroadcast,
    stopBroadcast,
    clearQueue,
    clear,
    current,
    followingParty,
    followingPartyStatus,
    history,
    moveQueueItem,
    next,
    queue,
    repeatMode,
    previous,
    playNext,
    queueItems,
    removeFromQueue,
    setRepeatMode,
    setShuffle,
    setAudioElement,
    setPauseHandler,
    setPlaybackPosition,
    shuffle,
    playItem,
    playerVisible,
  } = usePlayer();
  const [localMuted, setLocalMuted] = useState(() =>
    readStoredBoolean(localMuteStorageKey),
  );
  const [collapsed, setCollapsed] = useState(() => {
    // Auto-hide by default: an unset preference collapses the player so it
    // doesn't dominate the layout before the user has ever played anything.
    const stored = getLocalStorageItem(collapsedStorageKey);
    return stored === null ? true : stored === 'true';
  });
  const [playing, setPlaying] = useState(false);
  const playingRef = useRef(false);
  const [playbackStatus, setPlaybackStatus] = useState('idle');
  const [playbackError, setPlaybackError] = useState('');
  const [playbackAnnouncement, setPlaybackAnnouncement] = useState('');
  const previousAnnouncementItemRef = useRef(current);
  const [position, setPosition] = useState(0);
  const renderedPositionRef = useRef(0);
  const [duration, setDuration] = useState(0);
  const [transcodeMode, setTranscodeMode] = useState(false);
  const [transcodeAvailable, setTranscodeAvailable] = useState(false);
  const [transcodeOffset, setTranscodeOffset] = useState(0);
  const [sourceRetryRevision, setSourceRetryRevision] = useState(0);
  const [volume, setVolume] = useState(() => {
    const stored = Number(getLocalStorageItem(volumeStorageKey, '1'));
    return Number.isFinite(stored) ? Math.max(0, Math.min(1, stored)) : 1;
  });
  const [playbackRate, setPlaybackRate] = useState(() => {
    const stored = Number(getLocalStorageItem(playbackRateStorageKey, '1'));
    return [0.75, 1, 1.25, 1.5, 2].includes(stored) ? stored : 1;
  });
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const previousAdvancedOpenRef = useRef(false);
  const [outputDevices, setOutputDevices] = useState([]);
  const [outputDeviceId, setOutputDeviceId] = useState('default');
  const outputDeviceIdRef = useRef('default');
  const [outputSwitching, setOutputSwitching] = useState(false);
  const [outputChoosing, setOutputChoosing] = useState(false);
  const outputSwitchingRef = useRef(false);
  const outputSwitchPromiseRef = useRef(Promise.resolve());
  const fileInputRef = useRef(null);
  const localObjectUrlsRef = useRef(new Set());
  const selectedItemRef = useRef(current);
  const autoplayRef = useRef(false);
  const remountPositionRef = useRef(null);
  const transcodeRequestRef = useRef(0);
  const transcodeAbortRef = useRef(null);
  const failedTranscodeRef = useRef(null);
  const pendingTranscodeRef = useRef(false);

  const cancelTranscodeSetup = useCallback(() => {
    transcodeRequestRef.current += 1;
    transcodeAbortRef.current?.abort();
    transcodeAbortRef.current = null;
    pendingTranscodeRef.current = false;
  }, []);

  useEffect(() => () => cancelTranscodeSetup(), [cancelTranscodeSetup]);

  const closePictureInPicture = useCallback(() => {
    pipRequestRef.current += 1;
    const { raf, timer, win } = pipRef.current;
    pipRef.current = { data: null, raf: null, timer: null, win: null };
    if (!win) return;
    if (raf !== null) win.cancelAnimationFrame(raf);
    if (timer !== null) win.clearTimeout(timer);
    if (!win.closed) win.close();
  }, []);

  useEffect(() => () => {
    if (fadeTimeoutRef.current) window.clearTimeout(fadeTimeoutRef.current);
    closePictureInPicture();
    localObjectUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    localObjectUrlsRef.current.clear();
  }, [closePictureInPicture]);

  useEffect(() => {
    if (!playerVisible) closePictureInPicture();
  }, [closePictureInPicture, playerVisible]);

  useEffect(() => {
    const referenced = new Set([...queue, ...history, current].map((item) => item?.streamUrl));
    localObjectUrlsRef.current.forEach((url) => {
      if (referenced.has(url)) return;
      URL.revokeObjectURL(url);
      localObjectUrlsRef.current.delete(url);
    });
  }, [current, history, queue]);
  const [visualizerMode, setVisualizerMode] = useState(() =>
    readStoredBoolean(visualizerStorageKey) ? 'inline' : 'off',
  );
  const [visualTileMode, setVisualTileMode] = useState(readStoredTileMode);
  const [analyzerMode, setAnalyzerMode] = useState(readStoredAnalyzerMode);
  const [eqPanelOpen, setEqPanelOpen] = useState(() =>
    readStoredBoolean(eqPanelStorageKey),
  );
  const [lyricsOpen, setLyricsOpen] = useState(() =>
    readStoredBoolean(lyricsStorageKey),
  );
  const [karaokeEnabled, setKaraokeEnabledState] = useState(() =>
    readStoredBoolean(karaokeStorageKey),
  );
  const [crossfadeEnabled, setCrossfadeEnabled] = useState(() =>
    readStoredBoolean(crossfadeStorageKey),
  );
  const crossfadeEnabledRef = useRef(crossfadeEnabled);
  const [listenBrainzToken, setListenBrainzTokenState] = useState(() =>
    listenBrainz.getListenBrainzToken(),
  );
  const [integrationsOpen, setIntegrationsOpen] = useState(false);
  const integrationsDialog = usePlayerDialog(integrationsOpen);
  const [queueOpen, setQueueOpen] = useState(false);
  const [radioOpen, setRadioOpen] = useState(false);
  const [radioDirectoryOpen, setRadioDirectoryOpen] = useState(false);
  const [shelfOpen, setShelfOpen] = useState(false);
  const [statsOpen, setStatsOpen] = useState(false);
  const [externalVisualizerStatus, setExternalVisualizerStatus] = useState(null);
  const [externalVisualizerLoading, setExternalVisualizerLoading] = useState(false);
  const [externalVisualizerLaunching, setExternalVisualizerLaunching] = useState(false);
  const [externalVisualizerMessage, setExternalVisualizerMessage] = useState('');
  const [playerAudioElement, setPlayerAudioElement] = useState(null);
  const [playerRating, setPlayerRatingState] = useState(0);
  const [source, setSource] = useState(null);

  useEffect(() => {
    crossfadeEnabledRef.current = crossfadeEnabled;
  }, [crossfadeEnabled]);

  useEffect(() => {
    const previousItem = previousAnnouncementItemRef.current;
    if (!current) {
      if (previousItem) {
        const timer = window.setTimeout(() => {
          if (previousAnnouncementItemRef.current === previousItem) {
            previousAnnouncementItemRef.current = null;
            setPlaybackAnnouncement('Playback stopped.');
          }
        }, 200);
        return () => window.clearTimeout(timer);
      }
      return undefined;
    }

    previousAnnouncementItemRef.current = current;
    const title = current.title || current.fileName || current.contentId || 'Current track';
    if (previousItem !== current) {
      const timer = window.setTimeout(() => setPlaybackAnnouncement(interfaceText('Loading: {title}.', { title })), 400);
      return () => window.clearTimeout(timer);
    }
    const messages = {
      buffering: interfaceText('Buffering: {title}.', { title }),
      ended: interfaceText('Finished: {title}.', { title }),
      error: interfaceText('Playback error: {title}. {message}', {
        title,
        message: playbackError || interfaceText('Playback could not continue.'),
      }),
      paused: interfaceText('Paused: {title}.', { title }),
      playing: interfaceText('Now playing: {title}.', { title }),
    };
    const message = messages[playbackStatus];
    if (!message) return undefined;
    if (playbackStatus !== 'error' && activeItemRef.current !== current) return undefined;

    // Let transport-label updates settle before the polite status announcement.
    const delay = {
      buffering: 1200,
      paused: 200,
      playing: 200,
    }[playbackStatus] || 0;
    if (delay > 0) {
      const timer = window.setTimeout(() => setPlaybackAnnouncement(message), delay);
      return () => window.clearTimeout(timer);
    }

    setPlaybackAnnouncement(message);
    return undefined;
  }, [current, playbackError, playbackStatus]);

  const playbackAnnouncementRegion = (
    <div
      aria-atomic="true"
      aria-live="polite"
      className="player-playback-announcement"
      data-testid="player-playback-announcement"
      role="status"
    >
      {playbackAnnouncement}
    </div>
  );

  const refreshExternalVisualizerStatus = useCallback(() => {
    setExternalVisualizerLoading(true);
    setExternalVisualizerMessage('');

    return externalVisualizer.getExternalVisualizerStatus()
      .then((status) => {
        setExternalVisualizerStatus(status);
        return status;
      })
      .catch(() => {
        setExternalVisualizerStatus(null);
        setExternalVisualizerMessage(interfaceText('External visualizer status is unavailable.'));
      })
      .finally(() => {
        setExternalVisualizerLoading(false);
      });
  }, []);

  const launchExternalVisualizer = useCallback(() => {
    setExternalVisualizerLaunching(true);
    setExternalVisualizerMessage('');

    externalVisualizer.launchExternalVisualizer()
      .then((result) => {
        const name = result?.name || externalVisualizerStatus?.name || 'External visualizer';
        setExternalVisualizerMessage(
          result?.started ? interfaceText('{name} launched.', { name }) : result?.error || interfaceText('External visualizer did not launch.'),
        );
      })
      .catch((error) => {
        setExternalVisualizerMessage(getExternalVisualizerError(error));
      })
      .finally(() => {
        setExternalVisualizerLaunching(false);
      });
  }, [externalVisualizerStatus]);

  const bindAudioElement = useCallback((element) => {
    if (!element && audioRef.current && activeItemRef.current === selectedItemRef.current) {
      remountPositionRef.current = audioRef.current.currentTime;
    }
    if (!element && renderedPrimaryAudioRef.current) {
      releaseAudioGraph(renderedPrimaryAudioRef.current);
    }
    renderedPrimaryAudioRef.current = element;
    if (element && audioRef.current !== element) {
      lastSourceRef.current = '';
      if (activeItemRef.current === selectedItemRef.current) autoplayRef.current = playingRef.current;
    }
    audioRef.current = element;
    setPlayerAudioElement(element);
    setAudioElement(element);
  }, [setAudioElement]);

  const bindFadeAudioElement = useCallback((element) => {
    if (!element && renderedSecondaryAudioRef.current) {
      releaseAudioGraph(renderedSecondaryAudioRef.current);
    }
    renderedSecondaryAudioRef.current = element;
    fadeAudioRef.current = element;
  }, []);

  useLayoutEffect(() => {
    const element = playerBarRef.current;
    if (!element) return undefined;

    setPlayerHeightVariable(element);
    if (typeof window.ResizeObserver !== 'function') {
      return undefined;
    }

    const resizeObserver = new window.ResizeObserver(() =>
      setPlayerHeightVariable(element));
    resizeObserver.observe(element);

    return () => resizeObserver.disconnect();
  }, [collapsed, current, eqPanelOpen, lyricsOpen, playerVisible]);

  useLayoutEffect(() => {
    if (previousAdvancedOpenRef.current && !advancedOpen && playerBarRef.current) {
      playerBarRef.current.scrollTop = 0;
      const target = playerBarRef.current.querySelector('[data-testid="player-toggle-playback"]:not(:disabled)') ||
        playerBarRef.current.querySelector('[data-testid="player-visual-tile"]');
      target?.focus({ preventScroll: true });
    }
    previousAdvancedOpenRef.current = advancedOpen;
  }, [advancedOpen]);

  const playAudio = useCallback(async () => {
    const element = audioRef.current;
    if (!element) return;
    const request = ++playRequestRef.current;
    try {
      await outputSwitchPromiseRef.current;
      if (request !== playRequestRef.current || audioRef.current !== element) return;
      const selectedSinkId = outputDeviceIdRef.current === 'default'
        ? ''
        : outputDeviceIdRef.current;
      const graph = selectedSinkId || crossfadeEnabled
        ? getOrCreateAudioGraph(element)
        : getExistingAudioGraph(element);
      if (selectedSinkId) {
        await graph.ctx.setSinkId(selectedSinkId);
        const latestSinkId = outputDeviceIdRef.current === 'default'
          ? ''
          : outputDeviceIdRef.current;
        if (latestSinkId !== selectedSinkId) await graph.ctx.setSinkId(latestSinkId);
      }
      await resumeAudioGraph(element, false);
      if (request !== playRequestRef.current || audioRef.current !== element) return;
      await element.play();
    } catch (error) {
      if (request === playRequestRef.current && audioRef.current === element) throw error;
    }
  }, [crossfadeEnabled]);

  const stopOutgoingFade = useCallback(() => {
    fadeRequestRef.current += 1;
    if (fadeTimeoutRef.current) {
      window.clearTimeout(fadeTimeoutRef.current);
      fadeTimeoutRef.current = null;
    }
    const outgoing = fadeOutgoingRef.current;
    fadeOutgoingRef.current = null;
    if (!outgoing) return;
    outgoing.pause();
    const graph = getExistingAudioGraph(outgoing);
    if (graph && graph.ctx.state !== 'closed') {
        suspendAudioGraph(outgoing).catch(() => setPlaybackError(interfaceText('Audio processing could not pause.')));
    }
    outgoing.removeAttribute('src');
    outgoing.load();
    if (audioRef.current) {
      setOutputGain(outgoing, 1);
      setOutputGain(audioRef.current, 1);
    }
  }, []);

  useEffect(() => () => stopOutgoingFade(), [stopOutgoingFade]);

  useEffect(() => {
    if (playing || playbackStatus === 'loading') return undefined;
    let cancelled = false;
    const elements = [audioRef.current, fadeAudioRef.current].filter((element) => {
      const graph = getExistingAudioGraph(element);
      return graph && graph.ctx.state !== 'closed';
    });
    Promise.allSettled(elements.map((element) => suspendAudioGraph(element))).then((results) => {
      if (!cancelled && results.some((result) => result.status === 'rejected')) {
        setPlaybackError(interfaceText('Audio processing could not pause.'));
      }
    });
    return () => { cancelled = true; };
  }, [current, playbackStatus, playerAudioElement, playing]);

  const pausePlayback = useCallback(() => {
    playRequestRef.current += 1;
    autoplayRef.current = false;
    stopOutgoingFade();
    audioRef.current?.pause();
    playingRef.current = false;
    setPlaying(false);
    setPlaybackStatus((status) => status === 'ended' || status === 'error' ? status : 'paused');
    nowPlaying.clearNowPlaying().catch(() => {});
  }, [stopOutgoingFade]);

  useEffect(() => {
    setPauseHandler(pausePlayback);
    return () => setPauseHandler(null);
  }, [pausePlayback, setPauseHandler]);

  const startTranscode = useCallback(async (seconds = 0, autoPlay = true, coalesce = false) => {
    if (!current?.contentId || current.contentId.startsWith('local:')) return;
    transcodeAbortRef.current?.abort();
    const controller = new AbortController();
    transcodeAbortRef.current = controller;
    const requestId = ++transcodeRequestRef.current;
    failedTranscodeRef.current = null;
    pendingTranscodeRef.current = true;
    remountPositionRef.current = null;
    stopOutgoingFade();
    autoplayRef.current = autoPlay;
    playRequestRef.current += 1;
    activeItemRef.current = null;
    setSource(null);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.removeAttribute('src');
      audioRef.current.load();
    }
    playingRef.current = false;
    setPlaying(false);
    nowPlaying.clearNowPlaying().catch(() => {});
    setPlaybackError('');
    setPlaybackStatus(autoPlay ? 'loading' : 'paused');
    setPlaybackPosition(seconds);
    renderedPositionRef.current = seconds;
    setPosition(seconds);
    reportPlaybackEvent?.('pause', seconds);
    try {
      if (coalesce) {
        await new Promise((resolve) => {
          let timer;
          const finish = () => {
            window.clearTimeout(timer);
            controller.signal.removeEventListener('abort', finish);
            resolve();
          };
          timer = window.setTimeout(finish, 150);
          controller.signal.addEventListener('abort', finish, { once: true });
        });
      }
      if (requestId !== transcodeRequestRef.current) return;
      const ticket = await streaming.createStreamTicket(current.contentId, controller.signal);
      if (requestId !== transcodeRequestRef.current) return;
      const response = await streaming.getPlaybackInfo(current.contentId, controller.signal);
      if (requestId !== transcodeRequestRef.current) return;
      if (transcodeAbortRef.current === controller) transcodeAbortRef.current = null;
      pendingTranscodeRef.current = false;
      setDuration(Number(response.data?.durationSeconds) || 0);
      setTranscodeMode(true);
      setTranscodeOffset(seconds);
      const transcodedSource = streaming.buildTranscodedStreamUrl(current.contentId, ticket, seconds);
      setSource({ item: current, url: transcodedSource });
    } catch {
      if (requestId !== transcodeRequestRef.current) return;
      if (transcodeAbortRef.current === controller) transcodeAbortRef.current = null;
      pendingTranscodeRef.current = false;
      setPlaybackStatus('error');
      failedTranscodeRef.current = seconds;
      setPlaybackError(interfaceText('Decoding could not start. Press Play to retry. The server may be busy or FFmpeg may be unavailable.'));
    }
  }, [current, reportPlaybackEvent, setPlaybackPosition, stopOutgoingFade]);

  const tryPlay = useCallback((renewRadio = false) => {
    if (!current) return;
    if (failedTranscodeRef.current !== null) {
      startTranscode(failedTranscodeRef.current);
      return;
    }
    setPlaybackError('');
    setPlaybackStatus('loading');
    if (activeItemRef.current !== current) {
      if (current.radioPartyId) setSourceRetryRevision((revision) => revision + 1);
      autoplayRef.current = true;
      return;
    }
    const element = audioRef.current;
    if (element?.error || (current.radioPartyId && renewRadio === true)) {
      if (transcodeMode) {
        startTranscode(renderedPositionRef.current);
        return;
      }
      remountPositionRef.current = element.currentTime;
      if (!current.streamUrl || current.radioPartyId) {
        playRequestRef.current += 1;
        activeItemRef.current = null;
        autoplayRef.current = true;
        element.pause();
        if (current.radioPartyId) {
          element.removeAttribute('src');
          element.load();
        }
        playingRef.current = false;
        setPlaying(false);
        setSource(null);
        setSourceRetryRevision((revision) => revision + 1);
        return;
      }
      element.load();
    }
    playAudio().catch(() => {
      if (selectedItemRef.current !== current || audioRef.current !== element) return;
      pausePlayback();
      setPlaybackStatus('error');
      setPlaybackError(interfaceText('Playback could not start. Check the file or try again.'));
      reportPlaybackEvent?.('pause', transcodeOffset + element.currentTime);
    });
  }, [current, pausePlayback, playAudio, reportPlaybackEvent, startTranscode, transcodeMode, transcodeOffset]);

  const seekTo = useCallback((seconds) => {
    if (!current || !audioRef.current || !Number.isFinite(seconds)) return;
    const target = Math.max(0, Math.min(duration > 0 ? duration : Number.MAX_SAFE_INTEGER, seconds));
    stopOutgoingFade();
    crossfadeStartedRef.current = null;
    if (transcodeMode || pendingTranscodeRef.current || failedTranscodeRef.current !== null) {
      const autoPlay = activeItemRef.current === current
        ? playingRef.current
        : autoplayRef.current;
      startTranscode(target, autoPlay, true);
      return;
    }
    if (activeItemRef.current === current) audioRef.current.currentTime = target;
    else remountPositionRef.current = target;
    setPlaybackPosition(target);
    renderedPositionRef.current = target;
    setPosition(target);
  }, [current, duration, setPlaybackPosition, startTranscode, stopOutgoingFade, transcodeMode]);

  const seekBy = useCallback((seconds) => {
    if (!audioRef.current) return;
    const basePosition = activeItemRef.current === current
      ? transcodeOffset + audioRef.current.currentTime
      : renderedPositionRef.current;
    seekTo(basePosition + seconds);
  }, [current, seekTo, transcodeOffset]);

  const previousTrack = useCallback(() => {
    if (history.length === 0) {
      seekTo(0);
      return;
    }
    previous();
  }, [history.length, previous, seekTo]);

  useEffect(() => {
    if (!playerAudioElement) return;
    const safeVolume = Number.isFinite(volume) ? Math.max(0, Math.min(1, volume)) : 1;
    [audioRef.current, fadeAudioRef.current].filter(Boolean).forEach((element) => {
      element.volume = safeVolume;
    });
    setLocalStorageItem(volumeStorageKey, String(safeVolume));
  }, [playerAudioElement, volume]);

  useEffect(() => {
    if (!playerAudioElement) return;
    const safeRate = [0.75, 1, 1.25, 1.5, 2].includes(playbackRate) ? playbackRate : 1;
    [audioRef.current, fadeAudioRef.current].filter(Boolean).forEach((element) => {
      element.playbackRate = safeRate;
    });
    setLocalStorageItem(playbackRateStorageKey, String(safeRate));
  }, [playbackRate, playerAudioElement]);

  useEffect(() => {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!advancedOpen || !navigator.mediaDevices?.enumerateDevices || !AudioCtx?.prototype?.setSinkId) return undefined;
    let cancelled = false;
    const refreshOutputs = () => {
      navigator.mediaDevices.enumerateDevices().then((devices) => {
        if (!cancelled) setOutputDevices(devices.filter((device) =>
          device.kind === 'audiooutput' && device.deviceId !== 'default'));
      }).catch(() => {
        if (!cancelled) setOutputDevices([]);
      });
    };
    refreshOutputs();
    navigator.mediaDevices.addEventListener?.('devicechange', refreshOutputs);
    return () => {
      cancelled = true;
      navigator.mediaDevices.removeEventListener?.('devicechange', refreshOutputs);
    };
  }, [advancedOpen]);

  useEffect(() => {
    if (!playerAudioElement) return;
    [audioRef.current, fadeAudioRef.current].filter(Boolean).forEach((element) => {
      element.muted = localMuted;
    });
    setLocalStorageItem(localMuteStorageKey, localMuted ? 'true' : 'false');
  }, [localMuted, playerAudioElement]);

  useEffect(() => {
    setLocalStorageItem(collapsedStorageKey, collapsed ? 'true' : 'false');
  }, [collapsed]);

  useEffect(() => {
    if (!crossfadeEnabled) stopOutgoingFade();
  }, [crossfadeEnabled, stopOutgoingFade]);

  useEffect(() => {
    if (!crossfadeEnabled || !audioRef.current || audioRef.current.paused) return;
    resumeAudioGraph(audioRef.current).catch(() => {
      setPlaybackError(interfaceText('Could not prepare crossfade audio.'));
    });
  }, [crossfadeEnabled]);

  useEffect(() => {
    document.documentElement.classList.toggle('player-collapsed', collapsed);
    return () => {
      document.documentElement.classList.remove('player-collapsed');
    };
  }, [collapsed]);

  useEffect(() => {
    setLocalStorageItem(
      visualizerStorageKey,
      visualizerMode !== 'off' ? 'true' : 'false',
    );
  }, [visualizerMode]);

  useEffect(() => {
    setLocalStorageItem(visualTileStorageKey, visualTileMode);
  }, [visualTileMode]);

  useEffect(() => {
    setLocalStorageItem(analyzerModeStorageKey, analyzerMode);
  }, [analyzerMode]);

  useEffect(() => {
    if (integrationsOpen) {
      refreshExternalVisualizerStatus();
    }
  }, [integrationsOpen, refreshExternalVisualizerStatus]);

  useEffect(() => {
    setLocalStorageItem(eqPanelStorageKey, eqPanelOpen ? 'true' : 'false');
  }, [eqPanelOpen]);

  useEffect(() => {
    setLocalStorageItem(lyricsStorageKey, lyricsOpen ? 'true' : 'false');
  }, [lyricsOpen]);

  useEffect(() => {
    setLocalStorageItem(
      karaokeStorageKey,
      karaokeEnabled ? 'true' : 'false',
    );
    if (playerAudioElement) {
      [playerAudioElement, fadeOutgoingRef.current].filter(Boolean).forEach((element) => {
        setKaraokeEnabled(element, karaokeEnabled);
        if (!element.paused) {
          resumeAudioGraph(element, false).catch(() => {
            setPlaybackError(interfaceText('Could not enable vocal reduction for this track.'));
          });
        }
      });
    }
  }, [karaokeEnabled, playerAudioElement]);

  useEffect(() => {
    setLocalStorageItem(
      crossfadeStorageKey,
      crossfadeEnabled ? 'true' : 'false',
    );
  }, [crossfadeEnabled]);

  const toggleVisualizer = () => {
    setVisualizerMode((mode) => {
      if (mode === 'off') {
        setVisualTileMode(readStoredVisualizerEngineTileMode());
        return 'inline';
      }
      return 'off';
    });
  };

  useEffect(() => {
    setPlayerRatingState(getPlayerRating(current));
  }, [current]);

  const updatePlayerRating = (rating) => {
    const nextRating = setPlayerRating(current, rating);
    setPlayerRatingState(nextRating);
    upsertDiscoveryShelfItem(current, nextRating);
  };

  const openRadioSearch = (query) => {
    setRadioOpen(false);
    navigate(buildPlayerRadioSearchPath(query));
  };

  const togglePlayback = useCallback(() => {
    if (!audioRef.current || !current) return;
    if (playing || playbackStatus === 'loading') {
      pausePlayback();
    } else {
      tryPlay();
    }
  }, [current, pausePlayback, playbackStatus, playing, tryPlay]);

  useEffect(() => {
    let cancelled = false;

    if (!current) {
      selectedItemRef.current = null;
      failedTranscodeRef.current = null;
      activeItemRef.current = null;
      cancelTranscodeSetup();
      playRequestRef.current += 1;
      stopOutgoingFade();
      closePictureInPicture();
      autoplayRef.current = false;
      playingRef.current = false;
      setPlaying(false);
      setSource(null);
      setPlaybackStatus('idle');
      localObjectUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
      localObjectUrlsRef.current.clear();
      return undefined;
    }

    if (selectedItemRef.current !== current) {
      const previousItem = selectedItemRef.current;
      selectedItemRef.current = current;
      failedTranscodeRef.current = null;
      cancelTranscodeSetup();
      playRequestRef.current += 1;
      stopOutgoingFade();
      if (audioRef.current && (!crossfadeEnabledRef.current || current.startPaused || current.radioPartyId || previousItem?.radioPartyId)) {
        audioRef.current.pause();
        if (current.radioPartyId || previousItem?.radioPartyId) {
          audioRef.current.removeAttribute('src');
          audioRef.current.load();
          activeItemRef.current = null;
        }
        playingRef.current = false;
        setPlaying(false);
      }
      autoplayRef.current = !current.startPaused;
      remountPositionRef.current = null;
      setPlaybackStatus(current.startPaused ? 'paused' : 'loading');
      setTranscodeMode(false);
      setTranscodeAvailable(false);
      setTranscodeOffset(0);
      setDuration(0);
      const startingPosition = current.positionSeconds || 0;
      setPlaybackPosition(startingPosition);
      renderedPositionRef.current = startingPosition;
      setPosition(startingPosition);
    }
    setSource(null);

    if (current.radioPartyId) {
      createRadioStreamUrl(current.radioPartyId, current.contentId).then((url) => {
        if (!cancelled) setSource({ item: current, url });
      }).catch((error) => {
        if (!cancelled) {
          setPlaybackStatus('error');
          const status = error?.response?.status;
          setPlaybackError(interfaceText(error?.response?.data?.code === 'radio_fairness_limited'
            ? 'Remote radio is limited by network fairness. Check sharing activity before retrying.'
            : status === 429
              ? 'Radio streaming is at capacity. Retry later.'
              : status === 404
                ? 'This radio snapshot expired or is unavailable. Refresh listed radio.'
                : 'The request failed. Try again.'));
        }
      });
      return () => { cancelled = true; };
    }

    if (current.streamUrl) {
      setSource({ item: current, url: current.streamUrl });
      return undefined;
    }

    if (!current.contentId) {
      setSource(null);
      return undefined;
    }

    streaming
      .createStreamTicket(current.contentId)
      .then((ticket) => {
        if (!cancelled) {
          const nextSource = ticket
            ? streaming.buildTicketedStreamUrl(current.contentId, ticket)
            : streaming.buildDirectStreamUrl(current.contentId);
          setSource({ item: current, url: nextSource });
        }
      })
      .catch(() => {
        if (!cancelled) {
          const directSource = streaming.buildDirectStreamUrl(current.contentId);
          setSource({ item: current, url: directSource });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [cancelTranscodeSetup, closePictureInPicture, current, setPlaybackPosition, sourceRetryRevision, stopOutgoingFade]);

  useEffect(() => {
    const handleKeyDown = (event) => {
      const action = getPlayerShortcutAction(event);
      if (!action || !current) return;

      event.preventDefault();

      if (action === 'togglePlayback') {
        togglePlayback();
      } else if (action === 'seekBackward') {
        seekBy(-15);
      } else if (action === 'seekForward') {
        seekBy(30);
      } else if (action === 'previous') {
        previousTrack();
      } else if (action === 'next') {
        next();
      } else if (action === 'toggleMute') {
        setLocalMuted((muted) => !muted);
      } else if (action === 'toggleEqualizer') {
        setEqPanelOpen((open) => !open);
      } else if (action === 'toggleLyrics') {
        setLyricsOpen((open) => !open);
      } else if (action === 'toggleVisualizer') {
        toggleVisualizer();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    current,
    next,
    previousTrack,
    seekBy,
    togglePlayback,
    toggleVisualizer,
  ]);

  useEffect(() => {
    if (!audioRef.current || !source || source.item !== current) return;
    const previousSource = lastSourceRef.current;
    if (previousSource === source.url && activeItemRef.current === current) return;
    playRequestRef.current += 1;
    stopOutgoingFade();
    const active = audioRef.current;
    const standby = fadeAudioRef.current;
    if (crossfadeEnabled && (window.AudioContext || window.webkitAudioContext) &&
        !transcodeMode && autoplayRef.current &&
        previousSource && !active.paused && standby) {
      fadeOutgoingRef.current = active;
      const fadeRequest = ++fadeRequestRef.current;
      standby.src = source.url;
      standby.muted = localMuted;
      standby.volume = volume;
      standby.playbackRate = playbackRate;
      standby.load();
      setOutputGain(standby, 0);
      audioRef.current = standby;
      fadeAudioRef.current = active;
      activeItemRef.current = current;
      crossfadeStartedRef.current = null;
      setAudioElement(standby);
      setPlayerAudioElement(standby);
      autoplayRef.current = false;
      playAudio().then(() => {
        if (fadeRequest !== fadeRequestRef.current || audioRef.current !== standby) return;
        const remainingMediaSeconds = Number.isFinite(active.duration)
          ? Math.max(0, active.duration - active.currentTime)
          : 5;
        const fadeDurationSeconds = Math.max(0.1, Math.min(5, remainingMediaSeconds) / playbackRate);
        fadeOutputGain(active, 1, 0, fadeDurationSeconds);
        fadeOutputGain(standby, 0, 1, fadeDurationSeconds);
        fadeTimeoutRef.current = window.setTimeout(() => {
          if (fadeRequest !== fadeRequestRef.current) return;
          stopOutgoingFade();
        }, fadeDurationSeconds * 1000 + 200);
      }).catch(() => {
        if (fadeRequest !== fadeRequestRef.current) return;
        stopOutgoingFade();
        standby.pause();
        playingRef.current = false;
        setPlaying(false);
        setPlaybackStatus('error');
        setPlaybackError(interfaceText('The next track could not start.'));
        reportPlaybackEvent?.('pause', transcodeOffset + standby.currentTime);
        nowPlaying.clearNowPlaying().catch(() => {});
      });
    } else {
      if (standby) standby.pause();
      active.src = source.url;
      activeItemRef.current = current;
      crossfadeStartedRef.current = null;
      setOutputGain(active, 1);
      active.load();
      if (autoplayRef.current) {
        autoplayRef.current = false;
        tryPlay();
      } else {
        setPlaybackStatus('paused');
      }
    }
    lastSourceRef.current = source.url;
  }, [crossfadeEnabled, current, localMuted, playbackRate, playAudio, playerAudioElement, reportPlaybackEvent, setAudioElement, source, stopOutgoingFade, transcodeMode, transcodeOffset, tryPlay, volume]);

  useEffect(() => {
    scrobbledRef.current = '';
    playedSecondsRef.current = 0;
    playingNowSentRef.current = false;
  }, [current]);

  useEffect(() => {
    const audioElement = playerAudioElement;
    if (!audioElement || !current) return undefined;

    let lastPosition = audioElement.currentTime;
    const resetPosition = () => { lastPosition = audioElement.currentTime; };
    const handleTimeUpdate = () => {
      if (activeItemRef.current !== current) return;
      const mediaPosition = audioElement.currentTime;
      if (!audioElement.paused && !audioElement.seeking) {
        playedSecondsRef.current += Math.max(0, mediaPosition - lastPosition);
      }
      lastPosition = mediaPosition;
      const trackDuration = transcodeMode ? duration : audioElement.duration;
      const scrobbleDuration = Number.isFinite(trackDuration)
        ? trackDuration
        : 0;
      const threshold = scrobbleDuration > 0
        ? Math.min(scrobbleDuration / 2, 240)
        : 240;
      const scrobbleKey = `${current.contentId}:${current.title}`;

      if (playedSecondsRef.current >= threshold && scrobbledRef.current !== scrobbleKey) {
        scrobbledRef.current = scrobbleKey;
        recordLocalPlay(current);
        listenBrainz.submitListen('single', current).catch(() => {});
      }
    };

    audioElement.addEventListener('play', resetPosition);
    audioElement.addEventListener('seeking', resetPosition);
    audioElement.addEventListener('seeked', resetPosition);
    audioElement.addEventListener('timeupdate', handleTimeUpdate);
    return () => {
      audioElement.removeEventListener('play', resetPosition);
      audioElement.removeEventListener('seeking', resetPosition);
      audioElement.removeEventListener('seeked', resetPosition);
      audioElement.removeEventListener('timeupdate', handleTimeUpdate);
    };
  }, [current, duration, playerAudioElement, transcodeMode]);

  const openPictureInPicture = async () => {
    if (!audioRef.current || !window.documentPictureInPicture) return;

    closePictureInPicture();
    setPlaybackError((error) => error.startsWith('Picture-in-Picture could not open.') ? '' : error);
    const request = pipRequestRef.current;
    try {
      const graph = await resumeAudioGraph(audioRef.current);
      if (!graph || request !== pipRequestRef.current) return;

      const pipWindow = await window.documentPictureInPicture.requestWindow({
        height: 220,
        width: 360,
      });
      if (request !== pipRequestRef.current) {
        pipWindow.close();
        return;
      }
      pipWindow.document.body.style.margin = '0';
      pipWindow.document.body.style.background = '#050608';
      const canvas = pipWindow.document.createElement('canvas');
      canvas.style.height = '100%';
      canvas.style.width = '100%';
      pipWindow.document.body.appendChild(canvas);
      pipRef.current.win = pipWindow;
      pipWindow.addEventListener('pagehide', () => {
        if (pipRef.current.win === pipWindow) closePictureInPicture();
      }, { once: true });

      const draw = () => {
        if (pipRef.current.win !== pipWindow) return;
        if (pipWindow.closed) {
          closePictureInPicture();
          return;
        }
        pipRef.current.raf = null;
        pipRef.current.timer = null;
        const width = Math.max(1, pipWindow.innerWidth);
        const height = Math.max(1, pipWindow.innerHeight);
        if (canvas.width !== width) canvas.width = width;
        if (canvas.height !== height) canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#050608';
        ctx.fillRect(0, 0, width, height);
        const activeGraph = audioRef.current && playingRef.current
          ? getOrCreateAudioGraph(audioRef.current)
          : null;
        if (activeGraph) {
          if (pipRef.current.data?.length !== activeGraph.analyser.frequencyBinCount) {
            pipRef.current.data = new Uint8Array(activeGraph.analyser.frequencyBinCount);
          }
          const data = pipRef.current.data;
          activeGraph.analyser.getByteFrequencyData(data);
          const barCount = Math.min(72, Math.max(16, Math.floor(width / 7)));
          const bars = getFrequencyBars(data, barCount);
          const barWidth = width / bars.length;
          bars.forEach((value, index) => {
            const barHeight = (value / 255) * height;
            ctx.fillStyle = `hsl(${264 + (index / bars.length) * 24}, 72%, 68%)`;
            ctx.fillRect(
              index * barWidth,
              height - barHeight,
              Math.max(1, barWidth - 1),
              barHeight,
            );
          });
        }
        pipRef.current.timer = pipWindow.setTimeout(() => {
          if (pipRef.current.win === pipWindow) {
            pipRef.current.raf = pipWindow.requestAnimationFrame(draw);
          }
        }, playingRef.current ? 33 : 250);
      };

      draw();
    } catch {
      if (request !== pipRequestRef.current) return;
      closePictureInPicture();
      setPlaybackError(interfaceText('Picture-in-Picture could not open. Try again from the player tools.'));
    }
  };

  useEffect(() => {
    if (!('mediaSession' in navigator) || !window.MediaMetadata) {
      return undefined;
    }
    if (!current) {
      navigator.mediaSession.metadata = null;
      return undefined;
    }

    navigator.mediaSession.metadata = new window.MediaMetadata({
      album: current.album || '',
      artist: current.artist || '',
      artwork: current.artworkUrl ? [{ src: current.artworkUrl }] : [],
      title: current.title || current.fileName || current.contentId,
    });

    const handlers = {
      nexttrack: next,
      pause: pausePlayback,
      play: tryPlay,
      previoustrack: previousTrack,
      seekbackward: (details) => seekBy(-(details?.seekOffset || 15)),
      seekforward: (details) => seekBy(details?.seekOffset || 30),
      seekto: (details) => seekTo(details?.seekTime),
      stop: clear,
    };

    Object.entries(handlers).forEach(([action, handler]) => {
      try {
        navigator.mediaSession.setActionHandler(action, handler);
      } catch {
        // Some browsers expose a partial Media Session implementation.
      }
    });

    return () => {
      Object.keys(handlers).forEach((action) => {
        try {
          navigator.mediaSession.setActionHandler(action, null);
        } catch {
          // Some browsers expose a partial Media Session implementation.
        }
      });
    };
  }, [clear, current, next, pausePlayback, previousTrack, seekBy, seekTo, tryPlay]);

  useEffect(() => {
    if (!('mediaSession' in navigator)) return;
    navigator.mediaSession.playbackState = current ? (playing ? 'playing' : 'paused') : 'none';
    if (current && duration > 0 && navigator.mediaSession.setPositionState) {
      navigator.mediaSession.setPositionState({
        duration,
        playbackRate,
        position: Math.min(position, duration),
      });
    } else if (navigator.mediaSession.setPositionState) {
      navigator.mediaSession.setPositionState();
    }
  }, [current, duration, playbackRate, playing, position]);

  const switchOutputDevice = async (deviceId) => {
    if (outputSwitchingRef.current) return;
    outputSwitchingRef.current = true;
    setOutputSwitching(true);
    const sinkId = deviceId === 'default' ? '' : deviceId;
    const previousSinkId = outputDeviceIdRef.current === 'default'
      ? ''
      : outputDeviceIdRef.current;
    const switching = (async () => {
      const elements = [audioRef.current, fadeOutgoingRef.current].filter(Boolean);
      const contexts = elements
        .map((element) => (sinkId
          ? getOrCreateAudioGraph(element)
          : getExistingAudioGraph(element))?.ctx)
        .filter(Boolean);
      if (contexts.some((context) => !context.setSinkId)) {
        throw new Error('Web Audio output selection is unavailable.');
      }
      const results = await Promise.allSettled(
        contexts.map((context) => context.setSinkId(sinkId)),
      );
      if (results.some((result) => result.status === 'rejected')) {
        await Promise.allSettled(
          contexts.map((context) => context.setSinkId(previousSinkId)),
        );
        await Promise.allSettled(
          elements.filter((element) => !element.paused)
            .map((element) => resumeAudioGraph(element, false)),
        );
        throw new Error('Audio output switch failed.');
      }
      outputDeviceIdRef.current = deviceId;
      setOutputDeviceId(deviceId);
      const resumeResults = await Promise.allSettled(
        elements.filter((element) => !element.paused)
          .map((element) => resumeAudioGraph(element, false)),
      );
      if (resumeResults.some((result) => result.status === 'rejected')) {
        setPlaybackError(interfaceText('Audio output changed, but playback could not resume.'));
      }
    })();
    outputSwitchPromiseRef.current = switching.catch(() => {});
    try {
      await switching;
    } catch {
      setPlaybackError(interfaceText('Could not switch audio output device.'));
    } finally {
      outputSwitchingRef.current = false;
      setOutputSwitching(false);
    }
  };

  const chooseOutputDevice = async () => {
    if (outputChoosing || outputSwitchingRef.current) return;
    setOutputChoosing(true);
    try {
      const selection = navigator.mediaDevices.selectAudioOutput();
      const device = await selection;
      setOutputDevices((devices) => [
        ...devices.filter((listed) => listed.deviceId !== device.deviceId),
        device,
      ]);
      await switchOutputDevice(device.deviceId);
    } catch (error) {
      if (error?.name !== 'AbortError') {
        setPlaybackError(interfaceText('Could not choose an audio output device.'));
      }
    } finally {
      setOutputChoosing(false);
    }
  };

  if (!playerVisible) {
    return (
      <div
        className="player-bar player-bar-hidden player-bar-modern"
        ref={playerBarRef}
      >
        {playbackAnnouncementRegion}
        <div className="player-hidden-label">
          <Icon name="music" />
          <LocalizedText source={"Player hidden"} /></div>
        <PlayerToolButton
         {...interfaceTextProps("Show the browser player again at this location.")}
          content={interfaceText("Show the browser player again at this location.")}
          aria-label={interfaceText("Show player")}
          data-testid="player-show"
          icon="eye"
          onClick={() => setExperiencePreference('playerVisible', true)}
        />
      </div>
    );
  }

  const handleEnded = () => {
    if (!current) return;
    if (activeItemRef.current !== current || crossfadeStartedRef.current === current) {
      playingRef.current = false;
      setPlaying(false);
      setPlaybackStatus('loading');
      nowPlaying.clearNowPlaying().catch(() => {});
      return;
    }
    if (repeatMode === 'one' || (repeatMode === 'all' && queue.length === 1 && history.length === 0)) {
      playingNowSentRef.current = false;
      scrobbledRef.current = '';
      playedSecondsRef.current = 0;
      if (transcodeMode) startTranscode(0);
      else {
        audioRef.current.currentTime = 0;
        setPlaybackPosition(0);
        tryPlay();
      }
    } else if (queue.length > 1 || (repeatMode === 'all' && history.length > 0)) {
      next();
    } else {
      playingRef.current = false;
      setPlaying(false);
      setPlaybackStatus('ended');
      nowPlaying.clearNowPlaying().catch(() => {});
    }
  };

  const handleLocalFiles = (event) => {
    const files = Array.from(event.target.files || []);
    if (files.length === 0) return;
    const [file, ...remaining] = files;
    const streamUrl = URL.createObjectURL(file);
    localObjectUrlsRef.current.add(streamUrl);
    const makeItem = (selectedFile, url) => ({
      artist: 'Local file',
      contentId: `local:${Date.now()}:${++localFileSequenceRef.current}`,
      fileName: selectedFile.name,
      streamUrl: url,
      title: selectedFile.name.replace(/\.[^.]+$/u, ''),
    });
    playItem(makeItem(file, streamUrl), { replaceQueue: true });
    queueItems(remaining.map((selectedFile) => {
      const url = URL.createObjectURL(selectedFile);
      localObjectUrlsRef.current.add(url);
      return makeItem(selectedFile, url);
    }));
    event.target.value = '';
  };

  const loadPlaylist = (items) => {
    const [first, ...remaining] = items;
    playItem(first, { replaceQueue: true });
    queueItems(remaining, { allowDuplicates: true });
  };

  const audioHandlers = {
    onEnded: (event) => {
      if (event.currentTarget === audioRef.current) handleEnded();
    },
    onError: (event) => {
      if (event.currentTarget !== audioRef.current || !current) return;
      if (activeItemRef.current !== current) {
        playingRef.current = false;
        setPlaying(false);
        nowPlaying.clearNowPlaying().catch(() => {});
        return;
      }
      const failedElement = event.currentTarget;
      const failedSource = failedElement.currentSrc || failedElement.src;
      playRequestRef.current += 1;
      stopOutgoingFade();
      failedElement.pause();
      playingRef.current = false;
      setPlaying(false);
      setPlaybackStatus('error');
      setPlaybackError(transcodeMode
        ? 'The server could not decode this audio. Press Play to retry.'
        : current.radioPartyId
          ? 'The listed radio stream stopped or changed. Retry playback or refresh listed radio.'
          : 'This audio could not be decoded or streamed.');
      reportPlaybackEvent?.('pause', transcodeOffset + failedElement.currentTime);
      if (!transcodeMode && !current.streamUrl && !current.contentId.startsWith('local:')) {
        streaming.getPlaybackInfo(current.contentId).then((response) => {
          if (selectedItemRef.current !== current || audioRef.current !== failedElement ||
              (failedElement.currentSrc || failedElement.src) !== failedSource) return;
          setTranscodeAvailable(true);
          setDuration(Number(response.data?.durationSeconds) || 0);
        }).catch(() => {});
      }
      nowPlaying.clearNowPlaying().catch(() => {});
    },
    onLoadedMetadata: (event) => {
      if (event.currentTarget !== audioRef.current || activeItemRef.current !== current) return;
      if (!transcodeMode) setDuration(Number.isFinite(event.currentTarget.duration) ? event.currentTarget.duration : 0);
      if (remountPositionRef.current !== null) {
        event.currentTarget.currentTime = remountPositionRef.current;
        setPlaybackPosition(transcodeOffset + remountPositionRef.current);
        remountPositionRef.current = null;
      } else if (!transcodeMode && current?.positionSeconds > 0) {
        event.currentTarget.currentTime = current.positionSeconds;
        setPlaybackPosition(current.positionSeconds);
      }
      if (event.currentTarget.paused) reportPlaybackEvent?.('pause', transcodeOffset + event.currentTarget.currentTime);
    },
    onPause: (event) => {
      if (event.currentTarget !== audioRef.current) return;
      if (activeItemRef.current !== current) {
        playingRef.current = false;
        setPlaying(false);
        nowPlaying.clearNowPlaying().catch(() => {});
        return;
      }
      stopOutgoingFade();
      playingRef.current = false;
      setPlaying(false);
      setPlaybackStatus((status) => status === 'ended' || status === 'error' ? status : 'paused');
      reportPlaybackEvent?.('pause', transcodeOffset + event.currentTarget.currentTime);
      nowPlaying.clearNowPlaying().catch(() => {});
    },
    onSeeked: (event) => {
      if (event.currentTarget !== audioRef.current || activeItemRef.current !== current) return;
      reportPlaybackEvent?.(event.currentTarget.paused ? 'pause' : 'seek', transcodeOffset + event.currentTarget.currentTime);
    },
    onPlay: (event) => {
      if (event.currentTarget !== audioRef.current || activeItemRef.current !== current) return;
      playingRef.current = true;
      setPlaying(true);
      setPlaybackStatus('playing');
      reportPlaybackEvent?.('play', transcodeOffset + event.currentTarget.currentTime);
      if (current?.artist && current?.title) {
        nowPlaying.setNowPlaying({ album: current.album, artist: current.artist, title: current.title }).catch(() => {});
        if (!playingNowSentRef.current && listenBrainzToken) {
          playingNowSentRef.current = true;
          listenBrainz.submitListen('playing_now', current).catch(() => {});
        }
      }
    },
    onPlaying: (event) => {
      if (event.currentTarget !== audioRef.current || activeItemRef.current !== current) return;
      playingRef.current = true;
      setPlaying(true);
      setPlaybackStatus('playing');
    },
    onTimeUpdate: (event) => {
      if (event.currentTarget !== audioRef.current || activeItemRef.current !== current) return;
      const nextPosition = transcodeOffset + event.currentTarget.currentTime;
      setPlaybackPosition(nextPosition);
      if (Math.floor(nextPosition) !== Math.floor(renderedPositionRef.current)) {
        renderedPositionRef.current = nextPosition;
        setPosition(nextPosition);
      }
      if (crossfadeEnabled && !transcodeMode && repeatMode !== 'one' &&
          (queue.length > 1 || (repeatMode === 'all' && history.length > 0)) &&
          Number.isFinite(event.currentTarget.duration) && event.currentTarget.duration > 6 &&
          event.currentTarget.currentTime >= event.currentTarget.duration - 5 &&
          crossfadeStartedRef.current !== current) {
        crossfadeStartedRef.current = current;
        next();
      }
    },
    onWaiting: (event) => {
      if (event.currentTarget === audioRef.current && activeItemRef.current === current && playingRef.current) {
        setPlaybackStatus('buffering');
      }
    },
  };
  const audio = (
    <>
      <audio {...audioHandlers} playsInline preload="metadata" ref={bindAudioElement} />
      <audio {...audioHandlers} playsInline preload="metadata" ref={bindFadeAudioElement} />
    </>
  );
  const playerBadges = getPlayerBadges(current);
  const canPause = playing || playbackStatus === 'loading';
  const radioRetry = current?.radioPartyId && (playbackStatus === 'buffering' || playbackStatus === 'error') ? (
    <PlayerToolButton
      aria-label={interfaceText("Retry radio playback")}
      content={interfaceText("Reconnect to this radio snapshot if playback stalls. The host must still permit streaming.")}
      icon="redo"
      label={collapsed ? undefined : interfaceText('Retry radio')}
      onClick={() => tryPlay(true)}
     {...interfaceTextProps("Retry radio playback")}/>
  ) : null;

  if (collapsed) {
    return (
      <div
        className="player-bar player-bar-collapsed player-bar-modern"
        ref={playerBarRef}
      >
        {playbackAnnouncementRegion}
        {audio}
        <div className="player-track player-track-lcd">
          <Icon name="music" />
          <div>
            <div className="player-title">
              {current?.title || <LocalizedText source="Player" />}
            </div>
            <div className="player-subtitle" role={broadcastStatus?.error ? 'alert' : undefined}
              aria-label={broadcastStatus?.error || undefined} title={broadcastStatus?.error || undefined}>
              {broadcastStatus?.error ? <LocalizedText source="Broadcast updates failed" /> : broadcastStatus?.active ? <LocalizedText source="Broadcasting" /> : current?.artist || <LocalizedText source="Ready" />}
            </div>
          </div>
        </div>
        <PlayerProgress current={current} duration={duration} onSeek={seekTo} position={position} />
        <div className="player-controls player-control-cluster">
          {radioRetry}
          <PlayerToolButton
            content={interfaceText("Play the previous track or restart this one.")}
            aria-label={interfaceText("Previous local track")}
            disabled={!current}
            icon="step backward"
            onClick={previousTrack}
           {...interfaceTextProps("Play the previous track or restart this one.")}/>
          <PlayerToolButton
            content={canPause
              ? interfaceText('Pause playback or cancel pending autoplay.')
              : interfaceText('Play the selected track; retry if playback failed.')}
            aria-label={canPause ? interfaceText('Pause local playback') : interfaceText('Resume local playback')}
            data-testid="player-collapsed-toggle-playback"
            disabled={!current}
            icon={canPause ? 'pause' : 'play'}
            onClick={togglePlayback}
          />
          <PlayerToolButton
            content={interfaceText("Play the next queued track.")}
            aria-label={interfaceText("Next local track")}
            disabled={queue.length < 2}
            icon="step forward"
            onClick={next}
           {...interfaceTextProps("Play the next queued track.")}/>
          <PlayerToolButton
            content={interfaceText("Open the playback queue.")}
            className="player-compact-secondary"
            aria-label={interfaceText("Open playback queue")}
            disabled={!current}
            icon="list ol"
            onClick={() => setQueueOpen(true)}
           {...interfaceTextProps("Open the playback queue.")}/>
          <PlayerToolButton
            content={broadcastStatus
              ? interfaceText('Expand the player to view this room broadcast and use Retry or Stop.')
              : interfaceText('Expand the player drawer.')}
            aria-label={interfaceText("Expand player")}
            data-testid="player-expand"
            icon="angle up"
            onClick={() => setCollapsed(false)}
           {...interfaceTextProps("Expand player")}/>
          <PlayerToolButton
           {...interfaceTextProps("Stop playback and hide the player. Use Show player to restore it.")}
            content={interfaceText("Stop playback and hide the player. Use Show player to restore it.")}
            className="player-compact-secondary"
            aria-label={interfaceText("Hide player")}
            data-testid="player-hide"
            icon="eye slash"
            onClick={() => setExperiencePreference('playerVisible', false)}
          />
          <PlayerToolButton
            content={
              localMuted
              ? interfaceText('Unmute playback on this device without changing the stream.')
              : interfaceText('Mute playback on this device without changing the stream.')
            }
            className="player-compact-secondary"
            aria-label={localMuted ? interfaceText('Unmute local playback') : interfaceText('Mute local playback')}
            data-testid="player-collapsed-toggle-mute"
            disabled={!current}
            icon={localMuted ? 'volume off' : 'volume up'}
            onClick={() => setLocalMuted((muted) => !muted)}
          />
          <input
            aria-label={interfaceText("Playback volume")}
            aria-valuetext={`${Math.round(volume * 100)}%`}
            className="player-volume player-compact-secondary"
            max="1"
            min="0"
            onChange={(event) => setVolume(Number(event.target.value))}
            step="0.01"
            type="range"
            value={volume}
           {...interfaceTextProps("Playback volume")}/>
        </div>
        {queueOpen ? <PlayerQueueModal
          current={current}
          history={history}
          onAutoQueueSimilar={queueItems}
          onClearQueue={clearQueue}
          onClose={() => setQueueOpen(false)}
          onLoadPlaylist={loadPlaylist}
          onMove={moveQueueItem}
          onNext={next}
          onPrevious={previousTrack}
          onRemove={removeFromQueue}
          open={queueOpen}
          queue={queue}
        /> : null}
      </div>
    );
  }

  return (
    <div
      className="player-bar player-bar-modern"
      ref={playerBarRef}
    >
      {playbackAnnouncementRegion}
      {audio}
      <div className="player-main-deck">
        <div className="player-display">
          <PlayerVisualTile
            audioElement={playing ? playerAudioElement : null}
            controlsOpen={advancedOpen}
            current={current}
            mode={visualizerMode}
            onModeChange={setVisualizerMode}
            onTileModeChange={setVisualTileMode}
            tileMode={visualTileMode}
          />
          <div className="player-now-playing">
            <div className="player-track">
              <div>
                <div className="player-eyebrow">
                  {current ? <LocalizedText source={({
                    buffering: 'Buffering',
                    ended: 'Finished',
                    error: 'Playback error',
                    loading: 'Loading',
                    paused: 'Paused',
                    playing: 'Now playing',
                  }[playbackStatus] || 'Ready')} /> : <LocalizedText source={"Ready"} />}
                </div>
                <div className="player-title">
                  {current?.title || <LocalizedText source={"Nothing playing"} />}
                </div>
                <div className="player-subtitle">
                  {current?.artist || <LocalizedText source={"Pick a collection or local audio file"} />}
                  {current?.album ? <LocalizedText source={"| {album}"} values={{ "album": (current.album) }} /> : ''}
                  {followingParty ? followingParty.hostPeerId
                    ? <> | <LocalizedText source={"Following {peerId}"} values={{ peerId: followingParty.hostPeerId }} /></>
                    : <> | <LocalizedText source={"Waiting for room broadcast"} /></> : ''}
                  {broadcastStatus?.active ? <LocalizedText source={"| Broadcasting to room"} /> : ''}
                  {followingPartyStatus?.pending ? <LocalizedText source={"(connecting to room)"} />
                    : followingPartyStatus?.error ? <> <LocalizedText source={"(room updates unavailable)"} /></> : ''}
                </div>
                {broadcastStatus ? (
                  <div className="player-broadcast-controls">
                    {broadcastStatus.error ? <span role="alert"><LocalizedText source={broadcastStatus.error} /></span> : null}
                    {broadcastStatus.active ? <>
                      {broadcastStatus.error ? <Popup content={interfaceText("Retry publishing this room's current playback state after an update failure.")} trigger={<Button aria-label={interfaceText("Retry room broadcast")} onClick={() => retryBroadcast().catch(() => {})} size="mini" {...interfaceTextProps("Retry room broadcast")}><LocalizedText source={"Retry broadcast"} /></Button>}  {...interfaceTextProps("Retry publishing this room's current playback state after an update failure.")}/> : null}
                      <Popup content={interfaceText("Stop this room broadcast while keeping your own playback available.")} trigger={<Button aria-label={interfaceText("Stop active room broadcast")} onClick={() => stopBroadcast().catch(() => {})} size="mini" {...interfaceTextProps("Stop active room broadcast")}><LocalizedText source={"Stop broadcast"} /></Button>}  {...interfaceTextProps("Stop this room broadcast while keeping your own playback available.")}/>
                    </> : null}
                  </div>
                ) : null}
                {current ? (
                  <div className="player-now-playing-meta">
                    <div className="player-now-playing-badges">
                      {playerBadges.map((badge) => (
                        <Label
                          className="player-now-playing-badge"
                          color={badge.color}
                          data-testid={`player-badge-${badge.key}`}
                          key={badge.key}
                          size="mini"
                          title={badge.title}
                        >
                          <Icon name={badge.icon} />
                          {badge.text}
                        </Label>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
            <div className="player-display-analyzers" data-active={advancedOpen || analyzerMode !== 'off'}>
              <PlayerAnalyzerTile
                audioElement={playing ? playerAudioElement : null}
                mode={analyzerMode}
                onModeChange={setAnalyzerMode}
              />
            </div>
            <PlayerProgress current={current} duration={duration} onSeek={seekTo} position={position} />
            <PlayerRatingControls current={current} onChange={updatePlayerRating} rating={playerRating} />
            {playbackError ? <Message negative size="mini">{playbackError}</Message> : null}
            {transcodeAvailable && !transcodeMode ? (
              <Popup content={interfaceText("Decode this server library file to MP3 for this playback only. This uses server CPU until playback stops.")} trigger={
                <Button onClick={() => startTranscode(0)} size="mini" type="button"><LocalizedText source={"Decode for playback"} /></Button>
              }  {...interfaceTextProps("Decode this server library file to MP3 for this playback only. This uses server CPU until playback stops.")}/>
            ) : null}
          </div>
        </div>

        <div className="player-control-pad">
          <input
            accept="audio/*"
            aria-label={interfaceText("Choose audio files")}
            multiple
            onChange={handleLocalFiles}
            ref={fileInputRef}
            style={{ display: 'none' }}
            type="file"
           {...interfaceTextProps("Choose audio files")}/>
          <div className="player-control-row player-control-row-transport">
            <PlayerToolButton
              content={interfaceText("Go to the previous queue item, or restart the current stream.")}
              aria-label={interfaceText("Previous local track")}
              data-testid="player-previous"
              disabled={!current}
              icon="step backward"
              onClick={previousTrack}
             {...interfaceTextProps("Go to the previous queue item, or restart the current stream.")}/>
            <PlayerToolButton
              content={interfaceText("Rewind local playback by 15 seconds.")}
              aria-label={interfaceText("Rewind local playback")}
              data-testid="player-rewind"
              disabled={!current}
              icon="backward"
              onClick={() => seekBy(-15)}
             {...interfaceTextProps("Rewind local playback by 15 seconds.")}/>
            <PlayerToolButton
              content={canPause
                ? interfaceText('Pause the current stream or cancel pending autoplay.')
                : interfaceText('Resume the current stream; retry if playback failed.')}
              aria-label={canPause ? interfaceText('Pause local playback') : interfaceText('Resume local playback')}
              className="player-play-button"
              data-testid="player-toggle-playback"
              disabled={!current}
              icon={canPause ? 'pause' : 'play'}
              onClick={togglePlayback}
            />
            <PlayerToolButton
              content={interfaceText("Fast-forward local playback by 30 seconds.")}
              aria-label={interfaceText("Fast-forward local playback")}
              data-testid="player-fast-forward"
              disabled={!current}
              icon="forward"
              onClick={() => seekBy(30)}
             {...interfaceTextProps("Fast-forward local playback by 30 seconds.")}/>
            <PlayerToolButton
              content={interfaceText("Play the next queue item.")}
              aria-label={interfaceText("Next local track")}
              data-testid="player-next"
              disabled={!current || queue.length < 2}
              icon="step forward"
              onClick={next}
             {...interfaceTextProps("Play the next queue item.")}/>
            <PlayerToolButton
              content={interfaceText("Stop playback and clear your now-playing profile status.")}
              aria-label={interfaceText("Stop local playback")}
              data-testid="player-stop"
              disabled={!current}
              icon="stop"
              onClick={clear}
             {...interfaceTextProps("Stop playback and clear your now-playing profile status.")}/>
            <PlayerToolButton
              active={shuffle}
              aria-label={shuffle ? interfaceText('Disable shuffle') : interfaceText('Enable shuffle')}
              content={shuffle
                ? interfaceText('Play upcoming tracks in queue order.')
                : interfaceText('Choose upcoming tracks at random.')}
              icon="shuffle"
              onClick={() => setShuffle((enabled) => !enabled)}
            />
            <PlayerToolButton
              active={repeatMode !== 'off'}
              aria-label={interfaceText("Repeat {repeatMode}", { "repeatMode": (repeatMode) })}
              content={interfaceText("Repeat: {repeatMode}. Click to cycle off, all tracks, and one track.", { "repeatMode": (repeatMode) })}
              icon="repeat"
              onClick={() => setRepeatMode((mode) => mode === 'off' ? 'all' : mode === 'all' ? 'one' : 'off')}
             {...interfaceTextProps("Repeat {repeatMode}")}/>
            <select
              aria-label={interfaceText("Playback speed")}
              onChange={(event) => setPlaybackRate(Number(event.target.value))}
              value={playbackRate}
             {...interfaceTextProps("Playback speed")}>
              {[0.75, 1, 1.25, 1.5, 2].map((rate) => <option key={rate} value={rate}>{rate}×</option>)}
            </select>
          </div>
          <div className="player-control-row">
            {radioRetry}
            <PlayerLauncher
              compact
              onPlayItem={(item) => playItem(item, { replaceQueue: true })}
              onPlayNext={playNext}
            />
            <PlayerToolButton
              aria-label={interfaceText("Open audio files from this device")}
              content={interfaceText("Play files from this device in this browser session. They are not uploaded to the server.")}
              icon="folder open"
              onClick={() => fileInputRef.current?.click()}
             {...interfaceTextProps("Open audio files from this device")}/>
            <PlayerToolButton
              active={queueOpen}
              content={interfaceText("Open the playback queue manager with current, upcoming, and recent session tracks.")}
              aria-label={interfaceText("Open playback queue")}
              data-testid="player-open-queue"
              disabled={!current}
              icon="list ol"
              onClick={() => setQueueOpen(true)}
             {...interfaceTextProps("Open the playback queue manager with current, upcoming, and recent session tracks.")}/>
            <PlayerToolButton
              active={localMuted}
              content={
                localMuted
                  ? interfaceText('Unmute playback on this device without changing the stream.')
                  : interfaceText('Mute playback on this device without changing the stream.')
              }
              aria-label={localMuted ? interfaceText('Unmute local playback') : interfaceText('Mute local playback')}
              data-testid="player-toggle-mute"
              disabled={!current}
              icon={localMuted ? 'volume off' : 'volume up'}
              onClick={() => setLocalMuted((muted) => !muted)}
            />
            <input
              aria-label={interfaceText("Playback volume")}
              aria-valuetext={`${Math.round(volume * 100)}%`}
              className="player-volume"
              max="1"
              min="0"
              onChange={(event) => setVolume(Number(event.target.value))}
              step="0.01"
              type="range"
              value={volume}
             {...interfaceTextProps("Playback volume")}/>
            <PlayerToolButton
             {...interfaceTextProps("Collapse the player into a small drawer bar above the footer.")}
              content={interfaceText("Collapse the player into a small drawer bar above the footer.")}
              aria-label={interfaceText("Collapse player")}
              data-testid="player-collapse"
              icon="angle down"
              onClick={() => setCollapsed(true)}
            />
            <PlayerToolButton
              active={advancedOpen}
              aria-label={advancedOpen ? interfaceText('Hide player tools') : interfaceText('Show player tools')}
              content={advancedOpen
                ? interfaceText('Hide audio, discovery, and visual tools.')
                : interfaceText('Show audio, discovery, and visual tools.')}
              icon="ellipsis horizontal"
              onClick={() => setAdvancedOpen((open) => !open)}
            />
            <PlayerToolButton
             {...interfaceTextProps("Stop playback and hide the player. Use Show player to restore it.")}
              content={interfaceText("Stop playback and hide the player. Use Show player to restore it.")}
              aria-label={interfaceText("Hide player")}
              data-testid="player-hide"
              icon="eye slash"
              onClick={() => setExperiencePreference('playerVisible', false)}
            />
            {advancedOpen ? <>
            <PlayerToolButton
              active={visualizerMode !== 'off'}
              content={
                visualizerMode === 'off'
                  ? interfaceText('Show the MilkDrop visualizer.')
                  : interfaceText('Hide the MilkDrop visualizer.')
              }
              aria-label={
                visualizerMode === 'off'
                  ? interfaceText('Show MilkDrop visualizer')
                  : interfaceText('Hide MilkDrop visualizer')
              }
              data-testid="player-toggle-visualizer"
              icon="eye"
              onClick={toggleVisualizer}
            />
            <PlayerToolButton
              active={eqPanelOpen}
              content={
                eqPanelOpen
                  ? interfaceText('Hide the equalizer panel.')
                  : interfaceText('Show the equalizer sliders and presets.')
              }
              aria-label={eqPanelOpen ? interfaceText('Hide equalizer') : interfaceText('Show equalizer')}
              data-testid="player-toggle-eq"
              icon="sliders horizontal"
              onClick={() => setEqPanelOpen((open) => !open)}
            />
            <PlayerToolButton
              active={lyricsOpen}
              content={
                lyricsOpen
                  ? interfaceText('Hide synced lyrics for the current track.')
                  : interfaceText('Fetch synced lyrics for the current artist and title from LRCLIB.')
              }
              aria-label={lyricsOpen ? interfaceText('Hide lyrics') : interfaceText('Show lyrics')}
              data-testid="player-toggle-lyrics"
              disabled={!current}
              icon="align left"
              onClick={() => setLyricsOpen((open) => !open)}
            />
            <PlayerToolButton
              aria-label={interfaceText("Open listed radio")}
              content={interfaceText("Browse listed radio snapshots and choose a host-enabled stream to play.")}
              data-testid="player-open-listed-radio"
              icon="rss"
              onClick={() => setRadioDirectoryOpen(true)}
             {...interfaceTextProps("Open listed radio")}/>
            <PlayerToolButton
              content={interfaceText("Build smart-radio search seeds from the current track without starting network work yet.")}
              aria-label={interfaceText("Open smart radio seeds")}
              data-testid="player-open-radio"
              disabled={!current}
              icon="random"
              onClick={() => setRadioOpen(true)}
             {...interfaceTextProps("Build smart-radio search seeds from the current track without starting network work yet.")}/>
            <PlayerToolButton
              content={interfaceText("Show local listening stats recorded in this browser.")}
              aria-label={interfaceText("Open listening stats")}
              data-testid="player-open-listening-stats"
              icon="bar chart"
              onClick={() => setStatsOpen(true)}
             {...interfaceTextProps("Show local listening stats recorded in this browser.")}/>
            <PlayerToolButton
              active={shelfOpen}
              content={interfaceText("Open the browser-local discovery shelf built from player ratings.")}
              aria-label={interfaceText("Open discovery shelf")}
              data-testid="player-open-discovery-shelf"
              icon="bookmark"
              onClick={() => setShelfOpen(true)}
             {...interfaceTextProps("Open the browser-local discovery shelf built from player ratings.")}/>
            </> : null}
          </div>
          {advancedOpen ? <div className="player-control-row">
            {outputDevices.length > 0 || outputDeviceId !== 'default' ? (
              <select
                aria-label={interfaceText("Audio output device")}
                disabled={outputChoosing || outputSwitching}
                onChange={(event) => switchOutputDevice(event.target.value)}
                value={outputDeviceId}
               {...interfaceTextProps("Audio output device")}>
                <option value="default"><LocalizedText source={"System default"} /></option>
                {outputDeviceId !== 'default' &&
                  !outputDevices.some((device) => device.deviceId === outputDeviceId) ? (
                    <option value={outputDeviceId}><LocalizedText source={"Previously selected output"} /></option>
                  ) : null}
                {outputDevices.map((device, index) => (
                  <option key={device.deviceId || index} value={device.deviceId}>
                    {device.label || interfaceText('Audio output {number}', { number: index + 1 })}
                  </option>
                ))}
              </select>
            ) : null}
            {(window.AudioContext || window.webkitAudioContext)?.prototype?.setSinkId &&
              navigator.mediaDevices?.selectAudioOutput ? (
                <PlayerToolButton
                  content={interfaceText("Choose a speaker or headset and allow the browser to play through it.")}
                  aria-label={interfaceText("Choose audio output")}
                  disabled={outputChoosing || outputSwitching}
                  icon="headphones"
                  onClick={chooseOutputDevice}
                 {...interfaceTextProps("Choose a speaker or headset and allow the browser to play through it.")}/>
              ) : null}
            <PlayerToolButton
              active={karaokeEnabled}
              content={
                karaokeEnabled
                  ? interfaceText('Turn off center-channel vocal reduction.')
                  : interfaceText('Try center-channel vocal reduction for karaoke-style playback.')
              }
              aria-label={karaokeEnabled ? interfaceText('Disable karaoke mode') : interfaceText('Enable karaoke mode')}
              data-testid="player-toggle-karaoke"
              disabled={!current}
              icon="microphone slash"
              onClick={() => setKaraokeEnabledState((enabled) => !enabled)}
            />
            <PlayerToolButton
              active={crossfadeEnabled}
              content={
                crossfadeEnabled
                  ? interfaceText('Disable the five-second fade between queue items.')
                  : interfaceText('Enable a five-second fade between queue items.')
              }
              aria-label={crossfadeEnabled ? interfaceText('Disable crossfade') : interfaceText('Enable crossfade')}
              data-testid="player-toggle-crossfade"
              icon="exchange"
              onClick={() => setCrossfadeEnabled((enabled) => !enabled)}
            />
            <PlayerToolButton
              content={interfaceText("Open a tiny always-on-top spectrum window when this browser supports Document Picture-in-Picture.")}
              aria-label={interfaceText("Open visualizer picture in picture")}
              data-testid="player-document-pip"
              disabled={!current || !window.documentPictureInPicture}
              icon="window restore"
              onClick={openPictureInPicture}
             {...interfaceTextProps("Open a tiny always-on-top spectrum window when this browser supports Document Picture-in-Picture.")}/>
            <PlayerToolButton
              active={listenBrainzToken.length > 0}
              content={interfaceText("Configure ListenBrainz scrobbling for this browser.")}
              aria-label={interfaceText("Configure ListenBrainz scrobbling")}
              data-testid="player-open-integrations"
              icon="cloud upload"
              onClick={() => setIntegrationsOpen(true)}
             {...interfaceTextProps("Configure ListenBrainz scrobbling for this browser.")}/>
          </div> : null}
        </div>
      </div>

      <div className="player-expanded-panels">
        <div className="player-panel player-panel-eq" hidden={!eqPanelOpen}>
          <Equalizer
            audioElement={current ? playerAudioElement : null}
            fadeAudioElement={current ? fadeOutgoingRef.current : null}
            onAudioError={setPlaybackError}
          />
        </div>
        <LyricsPane
          audioElement={playerAudioElement}
          current={current}
          visible={lyricsOpen}
        />
      </div>

      <Modal
        {...integrationsDialog.dialogProps}
        className="player-browser-modal player-integrations-modal"
        onClose={() => setIntegrationsOpen(false)}
        open={integrationsOpen}
        size="tiny"
      >
        <Modal.Header {...integrationsDialog.titleProps}><LocalizedText source={"Player Integrations"} /></Modal.Header>
        <Modal.Content>
          <p className="player-modal-copy">
            <LocalizedText source={"ListenBrainz submissions are opt-in and the token is kept for this browser session."} /></p>
          <Input
            aria-label={interfaceText("ListenBrainz user token")}
            action={
              <Popup
                content={interfaceText("Remove the saved ListenBrainz token from this browser session. You can enter a new token at any time.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Clear ListenBrainz token")}
                    data-testid="player-clear-listenbrainz-token"
                    icon
                    onClick={() => {
                      setListenBrainzTokenState('');
                      listenBrainz.setListenBrainzToken('');
                    }}
                    type="button"
                   {...interfaceTextProps("Clear ListenBrainz token")}>
                    <Icon name="trash alternate outline" />
                  </Button>
                }
               {...interfaceTextProps("Remove the saved ListenBrainz token from this browser session. You can enter a new token at any time.")}/>
            }
            data-testid="player-listenbrainz-token"
            fluid
            icon="cloud upload"
            onChange={(event) => {
              setListenBrainzTokenState(event.target.value);
              listenBrainz.setListenBrainzToken(event.target.value);
            }}
            placeholder={interfaceText("ListenBrainz token")}
            size="mini"
            type="password"
            value={listenBrainzToken}
           {...interfaceTextProps("ListenBrainz user token")}/>
          <div
            className="player-token-save-state"
            data-testid="player-listenbrainz-save-state"
          >
            <Icon name="check circle outline" />
            <LocalizedText source={"Token changes are saved automatically for this session."} /></div>
          <div
            className="player-external-visualizer"
            data-testid="player-external-visualizer"
          >
            <div className="player-panel-title"><LocalizedText source={"External Visualizer"} /></div>
            <div className="player-external-visualizer-summary">
              <Icon
                name={externalVisualizerStatus?.enabled ? 'desktop' : 'ban'}
              />
              <div>
                <div className="player-external-visualizer-name">
                  {externalVisualizerStatus?.name || 'MilkDrop3'}
                </div>
                <div className="player-external-visualizer-status">
                  {getExternalVisualizerStatusText(
                    externalVisualizerStatus,
                    externalVisualizerLoading,
                  )}
                </div>
                {externalVisualizerStatus?.path ? (
                  <div
                    className="player-external-visualizer-path"
                    title={externalVisualizerStatus.path}
                  >
                    {externalVisualizerStatus.path}
                  </div>
                ) : null}
              </div>
            </div>
            {externalVisualizerMessage ? (
              <Message
                className="player-external-visualizer-message"
                compact
                data-testid="player-external-visualizer-message"
                info={externalVisualizerStatus?.available}
                size="tiny"
                warning={!externalVisualizerStatus?.available}
              >
                {externalVisualizerMessage}
              </Message>
            ) : null}
            <div className="player-external-visualizer-actions">
              <Popup
                content={interfaceText("Start the configured external visualizer on the slskdN host. Use this for MilkDrop3 or another local visualizer that captures system audio.")}
                trigger={
                  <Button
                    data-testid="player-launch-external-visualizer"
                    disabled={
                      externalVisualizerLaunching ||
                      !externalVisualizerStatus?.enabled ||
                      !externalVisualizerStatus?.available
                    }
                    loading={externalVisualizerLaunching}
                    onClick={launchExternalVisualizer}
                    size="mini"
                    type="button"
                  >
                    <Icon name="external alternate" />
                    <LocalizedText source={"Launch"} /></Button>
                }
               {...interfaceTextProps("Start the configured external visualizer on the slskdN host. Use this for MilkDrop3 or another local visualizer that captures system audio.")}/>
              <Popup
                content={interfaceText("Refresh the configured external visualizer path and readiness from the server.")}
                trigger={
                  <Button
                    data-testid="player-refresh-external-visualizer"
                    disabled={externalVisualizerLoading}
                    loading={externalVisualizerLoading}
                    onClick={refreshExternalVisualizerStatus}
                    size="mini"
                    type="button"
                  >
                    <Icon name="refresh" />
                    <LocalizedText source={"Refresh"} /></Button>
                }
               {...interfaceTextProps("Refresh the configured external visualizer path and readiness from the server.")}/>
            </div>
          </div>
        </Modal.Content>
        <Modal.Actions>
          <Popup
            content={interfaceText("Close settings. ListenBrainz token changes have already been saved.")}
            trigger={
              <Button
                data-testid="player-close-integrations"
                onClick={() => setIntegrationsOpen(false)}
                primary
              >
                <Icon name="check" />
                <LocalizedText source={"Done"} /></Button>
            }
           {...interfaceTextProps("Close settings. ListenBrainz token changes have already been saved.")}/>
        </Modal.Actions>
      </Modal>
      {radioDirectoryOpen ? <RadioDirectory
        onClose={() => setRadioDirectoryOpen(false)}
        onPlay={(party) => {
          const elapsed = party.action === 'play' && Number.isFinite(party.startedAtUnixMs) && party.startedAtUnixMs > 0
            ? Math.max(0, (Date.now() - party.startedAtUnixMs) / 1000) : 0;
          playItem({
            album: party.album,
            artist: party.artist || party.hostPeerId,
            contentId: party.contentId,
            streamUrl: buildRadioStreamUrl(party),
            radioPartyId: party.transportUsername && party.streamTicket ? party.partyId : null,
            title: party.title || party.contentId,
          }, {
            positionSeconds: (Number.isFinite(party.positionSeconds) ? Math.max(0, party.positionSeconds) : 0) + elapsed,
            replaceQueue: true,
            startPaused: party.action === 'pause',
          });
        }}
      /> : null}
      {radioOpen ? <PlayerRadioModal
        current={current}
        onClose={() => setRadioOpen(false)}
        onOpenSearch={openRadioSearch}
        open={radioOpen}
      /> : null}
      {queueOpen ? <PlayerQueueModal
        current={current}
        history={history}
        onAutoQueueSimilar={queueItems}
        onClearQueue={clearQueue}
        onClose={() => setQueueOpen(false)}
        onLoadPlaylist={loadPlaylist}
        onMove={moveQueueItem}
        onNext={next}
        onPrevious={previousTrack}
        onRemove={removeFromQueue}
        open={queueOpen}
        queue={queue}
      /> : null}
      {shelfOpen ? <PlayerDiscoveryShelfModal
        onClose={() => setShelfOpen(false)}
        open={shelfOpen}
      /> : null}
      {statsOpen ? <PlayerStatsModal
        onClose={() => setStatsOpen(false)}
        onOpenSearch={(query) => {
          setStatsOpen(false);
          openRadioSearch(query);
        }}
        open={statsOpen}
      /> : null}
      {current && queue.length > 1 ? (
        <div className="player-queue">
          {queue.slice(1, 4).map((item, index) => (
            <Popup
              content={interfaceText(
                'Remove {track} from upcoming playback without stopping the current track.',
                { track: item.title || item.fileName || item.contentId },
              )}
              key={`${item.contentId}-${index}`}
              trigger={
                <button
                  aria-label={interfaceText('Remove {track} from queue', {
                    track: item.title || item.fileName || item.contentId,
                  })}
                  className="player-queue-item"
                  onClick={() => removeFromQueue(index + 1)}
                  type="button"
                >
                  {item.title || item.fileName || item.contentId}
                </button>
              }
            />
          ))}
        </div>
      ) : null}
    </div>
  );
};

export default PlayerBar;
