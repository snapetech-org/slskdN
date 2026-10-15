import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';


import './PlaylistIntake.css';
import * as collectionsAPI from '../../lib/collections';
import {
  addPlaylistIntake,
  approvePlaylistTagOrganizationPlan,
  buildPlaylistCollectionItems,
  buildPlaylistCompletionSummary,
  buildPlaylistIntakeSummary,
  buildSlskdPlaylistPreview,
  clearPlaylistTagOrganizationApproval,
  coverArtPolicies,
  formatPlaylistTagOrganizationReport,
  getPlaylistIntakes,
  markPlaylistCollectionCreated,
  multiArtistTagPolicies,
  organizationPathTemplates,
  previewPlaylistTagOrganizationPlan,
  replayGainPolicies,
  updatePlaylistIntakeTrackState,
} from '../../lib/playlistIntake';
import React, { useMemo, useState } from 'react';
import {
  Button,
  Form,
  Header,
  Icon,
  Label,
  Popup,
  Segment,
  TextArea,
} from 'semantic-ui-react';

const trackStateColor = (state) => (state === 'Matched' ? 'green' : 'orange');

const PlaylistIntake = () => {
  useInterfaceLanguage();
  const [items, setItems] = useState(() => getPlaylistIntakes());
  const [name, setName] = useState('');
  const [source, setSource] = useState('');
  const [content, setContent] = useState('');
  const [playlistPreviews, setPlaylistPreviews] = useState({});
  const [organizationInputs, setOrganizationInputs] = useState({});
  const [status, setStatus] = useState('');
  const [busyPlaylistId, setBusyPlaylistId] = useState('');

  const summary = useMemo(() => buildPlaylistIntakeSummary(items), [items]);

  const importPlaylist = () => {
    const sourceName = source.trim() || name.trim() || 'Pasted playlist';
    const nextItems = addPlaylistIntake({
      content,
      name: name.trim() || sourceName,
      source: sourceName,
    });

    setItems(nextItems);
    setName('');
    setSource('');
    setContent('');
  };

  const previewSlskdPlaylist = (playlist) => {
    setPlaylistPreviews((current) => ({
      ...current,
      [playlist.id]: buildSlskdPlaylistPreview(playlist),
    }));
  };

  const getOrganizationInput = (playlist) => ({
    albumTitle:
      organizationInputs[playlist.id]?.albumTitle ||
      playlist.organizationOptions?.albumTitle ||
      playlist.name,
    coverArtPolicy:
      organizationInputs[playlist.id]?.coverArtPolicy ||
      playlist.organizationOptions?.coverArtPolicy ||
      'sidecar',
    multiArtistPolicy:
      organizationInputs[playlist.id]?.multiArtistPolicy ||
      playlist.organizationOptions?.multiArtistPolicy ||
      'preserve',
    pathTemplate:
      organizationInputs[playlist.id]?.pathTemplate ||
      playlist.organizationOptions?.pathTemplate ||
      organizationPathTemplates[0].value,
    replayGainPolicy:
      organizationInputs[playlist.id]?.replayGainPolicy ||
      playlist.organizationOptions?.replayGainPolicy ||
      'skip',
  });

  const setOrganizationInput = (playlist, key, value) => {
    setOrganizationInputs((current) => ({
      ...current,
      [playlist.id]: {
        ...getOrganizationInput(playlist),
        ...current[playlist.id],
        [key]: value,
      },
    }));
  };

  const previewTagOrganization = (playlist) => {
    const nextItems = previewPlaylistTagOrganizationPlan(
      playlist.id,
      getOrganizationInput(playlist),
    );
    setItems(nextItems);
    setStatus(interfaceText("Prepared tag and organization dry run for {playlistName}", { playlistName: playlist.name }));
  };

  const copyTagOrganizationReport = (playlist) => {
    const report = formatPlaylistTagOrganizationReport(playlist);
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(report).catch(() => {});
    }
    setStatus(interfaceText("Prepared tag and organization report for {playlistName}", { playlistName: playlist.name }));
  };

  const approveTagOrganizationSnapshot = (playlist) => {
    setItems(approvePlaylistTagOrganizationPlan(playlist.id));
    setStatus(interfaceText("Approved tag and organization snapshot for {playlistName}", { playlistName: playlist.name }));
  };

  const clearTagOrganizationSnapshot = (playlist) => {
    setItems(clearPlaylistTagOrganizationApproval(playlist.id));
    setStatus(interfaceText("Cleared tag and organization snapshot for {playlistName}", { playlistName: playlist.name }));
  };

  const setTrackState = (playlist, track, state) => {
    setItems(updatePlaylistIntakeTrackState(playlist.id, track.id, state));
  };

  const createSlskdPlaylist = async (playlist) => {
    const itemsToCreate = buildPlaylistCollectionItems(playlist);
    if (itemsToCreate.length === 0) {
      setStatus(interfaceText("No matched rows are ready for {playlistName}", { playlistName: playlist.name }));
      return;
    }

    setBusyPlaylistId(playlist.id);
    try {
      const created = await collectionsAPI.createCollection({
        description: `Created from Playlist Intake source ${playlist.source}. Rows are planned playlist entries until resolved to local library content.`,
        title: playlist.name,
        type: 'Playlist',
      });
      const collectionId = created.data?.id;
      if (!collectionId) {
        throw new Error('Collections API did not return a collection id');
      }

      for (const item of itemsToCreate) {
        // Sequential writes preserve playlist order and avoid API bursts.
        // eslint-disable-next-line no-await-in-loop
        await collectionsAPI.addCollectionItem(collectionId, item);
      }
      setItems(markPlaylistCollectionCreated(playlist.id, collectionId));
      setStatus(
        interfaceText("Created playlist collection for {playlistName} with {count} planned rows", { playlistName: playlist.name, count: itemsToCreate.length }),
      );
    } catch (error) {
      setStatus(interfaceText("Playlist creation failed for {playlistName}: {message}", { playlistName: playlist.name, message: getApiErrorMessage(error, { t: interfaceText }) }));
    } finally {
      setBusyPlaylistId('');
    }
  };

  return (
    <Segment
      className="playlist-intake"
      raised
    >
      <div className="playlist-intake-header">
        <Header as="h2">
          <Icon name="list alternate outline" />
          <Header.Content>
            <LocalizedText source={"Playlist Intake"} /><Header.Subheader>
              <LocalizedText source={"Import playlist text for review before any provider or network activity."} /></Header.Subheader>
          </Header.Content>
        </Header>
      </div>

      <Form className="playlist-intake-form">
        <Form.Group widths="equal">
          <Form.Input
            aria-label={interfaceText("Playlist name")}
            label={<LocalizedText source="Name" />}
            onChange={(event) => setName(event.target.value)}
            placeholder={interfaceText("Road trip, label sampler, friend recs")}
            value={name}
           {...interfaceTextProps("Playlist name")}/>
          <Form.Input
            aria-label={interfaceText("Playlist source")}
            label={<LocalizedText source="Source" />}
            onChange={(event) => setSource(event.target.value)}
            placeholder={interfaceText("Local file name or provider URL")}
            value={source}
           {...interfaceTextProps("Playlist source")}/>
        </Form.Group>
        <Form.Field>
          <label><LocalizedText source={"Playlist rows"} /></label>
          <TextArea
            aria-label={interfaceText("Playlist rows")}
            onChange={(event) => setContent(event.target.value)}
            placeholder={interfaceText("Artist - Title, one row per track, or simple CSV artist,title")}
            rows={6}
            value={content}
           {...interfaceTextProps("Playlist rows")}/>
        </Form.Field>
        <Popup
          content={interfaceText("Import these playlist rows for matching and playlist creation. This does not search Soulseek, browse peers, download, or track provider playlists.")}
          position="top center"
          trigger={
            <Button
              aria-label={interfaceText("Import playlist for review")}
              disabled={!content.trim()}
              onClick={importPlaylist}
              primary
              type="button"
             {...interfaceTextProps("Import playlist for review")}>
              <Icon name="plus" />
              <LocalizedText source={"Import Playlist"} /></Button>
          }
         {...interfaceTextProps("Import these playlist rows for matching and playlist creation. This does not search Soulseek, browse peers, download, or track provider playlists.")}/>
      </Form>

      <div className="playlist-intake-summary">
        <Label basic>
          <LocalizedText source={"Playlists"} /><Label.Detail>{summary.total}</Label.Detail>
        </Label>
        <Label basic>
          <LocalizedText source={"Tracks"} /><Label.Detail>{summary.tracks}</Label.Detail>
        </Label>
        {/* Orange only once there's actually something unmatched to fix —
            not on a fresh, expected zero. */}
        <Label color={summary.unmatched > 0 ? 'orange' : 'grey'}>
          <LocalizedText source={"Unmatched"} /><Label.Detail>{summary.unmatched}</Label.Detail>
        </Label>
      </div>
      {status && <div className="playlist-intake-status">{status}</div>}

      <div className="playlist-intake-grid">
        {items.map((playlist) => (
          <Segment
            className="playlist-intake-card"
            key={playlist.id}
          >
            {(() => {
              const completion = buildPlaylistCompletionSummary(playlist);
              const organizationInput = getOrganizationInput(playlist);

              return (
                <>
                  <div className="playlist-intake-card-head">
                    <div>
                      <div className="playlist-intake-title">{playlist.name}</div>
                      <div className="playlist-intake-meta">
                        <Icon name="map signs" />
                        {playlist.source}
                        <span> - </span>
                        <Icon name="plug" />
                        {playlist.provider}
                      </div>
                      <div className="playlist-intake-summary">
                        <Label basic>
                          <Icon name="check" />
                          <LocalizedText source={"Matched"} />{" "}{completion.Matched}
                        </Label>
                        <Label basic>
                          <Icon name="question circle outline" />
                          <LocalizedText source={"Unmatched"} />{" "}{completion.Unmatched}
                        </Label>
                        <Label basic>
                          <Icon name="ban" />
                          <LocalizedText source={"Rejected"} />{" "}{completion.Rejected}
                        </Label>
                        <Label
                          basic
                          color={completion.Unmatched > 0 ? 'orange' : 'green'}
                        >
                          {completion.Unmatched > 0
                            ? <LocalizedText source={"Partial completion allowed"} />
                            : <LocalizedText source={"Ready for review"} />}
                        </Label>
                      </div>
                    </div>
                    <Label color="grey">
                      <LocalizedText source={playlist.state} />
                    </Label>
                  </div>
                  <div className="playlist-intake-actions">
                    <Popup
                      content={interfaceText("Preview the matched rows that will be used for a slskdN playlist Collection.")}
                      position="top center"
                      trigger={
                        <Button
                          aria-label={interfaceText("Preview slskdN playlist for {name}", { "name": (playlist.name) })}
                          icon
                          onClick={() => previewSlskdPlaylist(playlist)}
                          size="small"
                          type="button"
                         {...interfaceTextProps("Preview slskdN playlist for {name}")}>
                          <Icon name="file alternate outline" />
                          <LocalizedText source={"Preview Playlist"} /></Button>
                      }
                     {...interfaceTextProps("Preview the matched rows that will be used for a slskdN playlist Collection.")}/>
                    <Popup
                      content={interfaceText("Create a slskdN Playlist collection from matched rows. This writes local collection metadata only and does not search, browse, or download.")}
                      position="top center"
                      trigger={
                        <Button
                          aria-label={interfaceText("Create slskdN playlist for {name}", { "name": (playlist.name) })}
                          icon
                          loading={busyPlaylistId === playlist.id}
                          onClick={() => createSlskdPlaylist(playlist)}
                          size="small"
                          type="button"
                         {...interfaceTextProps("Create slskdN playlist for {name}")}>
                          <Icon name="save" />
                          <LocalizedText source={"Create Playlist"} /></Button>
                      }
                     {...interfaceTextProps("Create a slskdN Playlist collection from matched rows. This writes local collection metadata only and does not search, browse, or download.")}/>
                  </div>
                  {playlistPreviews[playlist.id] && (
                    <div className="playlist-intake-preview">
                      <div className="playlist-intake-meta">
                        <LocalizedText source={playlistPreviews[playlist.id].networkImpact} />
                      </div>
                      <pre>{playlistPreviews[playlist.id].text}</pre>
                    </div>
                  )}
                  <Segment className="playlist-intake-organization">
                    <Header as="h4">
                      <Icon name="tags" />
                      <LocalizedText source={"Tag and Organization Preview"} /><Header.Subheader>
                        <LocalizedText source={"Dry-run tag, cover-art, ReplayGain, and path decisions before any file write."} /></Header.Subheader>
                    </Header>
                    <Form>
                      <Form.Group widths="equal">
                        <Form.Input
                          aria-label={interfaceText("Organization album title for {name}", { "name": (playlist.name) })}
                          label={<LocalizedText source="Album title" />}
                          onChange={(event) =>
                            setOrganizationInput(
                              playlist,
                              'albumTitle',
                              event.target.value,
                            )
                          }
                          value={organizationInput.albumTitle}
                         {...interfaceTextProps("Organization album title for {name}")}/>
                        <Form.Select
                          aria-label={interfaceText("Organization path template for {name}", { "name": (playlist.name) })}
                          label={<LocalizedText source="Path template" />}
                          onChange={(_event, data) =>
                            setOrganizationInput(playlist, 'pathTemplate', data.value)
                          }
                          options={organizationPathTemplates.map((option) => ({ ...option, text: interfaceText(option.text) }))}
                          value={organizationInput.pathTemplate}
                         {...interfaceTextProps("Organization path template for {name}")}/>
                      </Form.Group>
                      <Form.Group widths="equal">
                        <Form.Select
                          aria-label={interfaceText("Multi-artist tag policy for {name}", { "name": (playlist.name) })}
                          label={<LocalizedText source="Multi-artist" />}
                          onChange={(_event, data) =>
                            setOrganizationInput(
                              playlist,
                              'multiArtistPolicy',
                              data.value,
                            )
                          }
                          options={multiArtistTagPolicies.map((option) => ({ ...option, text: interfaceText(option.text) }))}
                          value={organizationInput.multiArtistPolicy}
                         {...interfaceTextProps("Multi-artist")}/>
                        <Form.Select
                          aria-label={interfaceText("Cover art policy for {name}", { "name": (playlist.name) })}
                          label={<LocalizedText source="Cover art" />}
                          onChange={(_event, data) =>
                            setOrganizationInput(playlist, 'coverArtPolicy', data.value)
                          }
                          options={coverArtPolicies.map((option) => ({ ...option, text: interfaceText(option.text) }))}
                          value={organizationInput.coverArtPolicy}
                         {...interfaceTextProps("Cover art policy for {name}")}/>
                        <Form.Select
                          aria-label={interfaceText("ReplayGain policy for {name}", { "name": (playlist.name) })}
                          label={<LocalizedText source="ReplayGain" />}
                          onChange={(_event, data) =>
                            setOrganizationInput(playlist, 'replayGainPolicy', data.value)
                          }
                          options={replayGainPolicies.map((option) => ({ ...option, text: interfaceText(option.text) }))}
                          value={organizationInput.replayGainPolicy}
                         {...interfaceTextProps("ReplayGain policy for {name}")}/>
                      </Form.Group>
                      <Popup
                        content={interfaceText("Preview tag fields, cover-art policy, ReplayGain policy, and organized destination paths. This does not write tags, move files, run ReplayGain, or contact providers.")}
                        position="top center"
                        trigger={
                          <Button
                            aria-label={interfaceText("Preview tag organization for {name}", { "name": (playlist.name) })}
                            disabled={completion.Matched === 0}
                            icon
                            onClick={() => previewTagOrganization(playlist)}
                            size="small"
                            type="button"
                           {...interfaceTextProps("Preview tag organization for {name}")}>
                            <Icon name="magic" />
                            <LocalizedText source={"Preview Organization"} /></Button>
                        }
                       {...interfaceTextProps("Preview tag fields, cover-art policy, ReplayGain policy, and organized destination paths. This does not write tags, move files, run ReplayGain, or contact providers.")}/>
                      <Popup
                        content={interfaceText("Copy a text report of the current tag and organization dry run. This does not write tags, move files, run ReplayGain, or contact providers.")}
                        position="top center"
                        trigger={
                          <Button
                            aria-label={interfaceText("Copy tag organization report for {name}", { "name": (playlist.name) })}
                            disabled={!playlist.organizationPlan}
                            icon
                            onClick={() => copyTagOrganizationReport(playlist)}
                            size="small"
                            type="button"
                           {...interfaceTextProps("Copy tag organization report for {name}")}>
                            <Icon name="copy outline" />
                            <LocalizedText source={"Copy Report"} /></Button>
                        }
                       {...interfaceTextProps("Copy a text report of the current tag and organization dry run. This does not write tags, move files, run ReplayGain, or contact providers.")}/>
                      <Popup
                        content={interfaceText("Approve this dry-run snapshot for later import review. This records source/proposed metadata only and does not write tags or move files.")}
                        position="top center"
                        trigger={
                          <Button
                            aria-label={interfaceText("Approve tag organization snapshot for {name}", { "name": (playlist.name) })}
                            disabled={!playlist.organizationPlan}
                            icon
                            onClick={() => approveTagOrganizationSnapshot(playlist)}
                            size="small"
                            type="button"
                           {...interfaceTextProps("Approve tag organization snapshot for {name}")}>
                            <Icon name="check circle outline" />
                            <LocalizedText source={"Approve Snapshot"} /></Button>
                        }
                       {...interfaceTextProps("Approve this dry-run snapshot for later import review. This records source/proposed metadata only and does not write tags or move files.")}/>
                      <Popup
                        content={interfaceText("Clear the approved snapshot while keeping the dry-run preview available for more edits.")}
                        position="top center"
                        trigger={
                          <Button
                            aria-label={interfaceText("Clear tag organization snapshot for {name}", { "name": (playlist.name) })}
                            disabled={!playlist.organizationApproval}
                            icon
                            onClick={() => clearTagOrganizationSnapshot(playlist)}
                            size="small"
                            type="button"
                           {...interfaceTextProps("Clear tag organization snapshot for {name}")}>
                            <Icon name="undo" />
                            <LocalizedText source={"Clear Snapshot"} /></Button>
                        }
                       {...interfaceTextProps("Clear the approved snapshot while keeping the dry-run preview available for more edits.")}/>
                    </Form>
                    {playlist.organizationPlan && (
                      <div className="playlist-intake-organization-plan">
                        <div className="playlist-intake-summary">
                          <Label color="green">
                            <LocalizedText source={"Matched"} /><Label.Detail>
                              {playlist.organizationPlan.summary.matched}
                            </Label.Detail>
                          </Label>
                          <Label color="orange">
                            <LocalizedText source={"Skipped"} /><Label.Detail>
                              {playlist.organizationPlan.summary.skipped}
                            </Label.Detail>
                          </Label>
                          <Label color="blue">
                            <LocalizedText source={"Changed fields"} /><Label.Detail>
                              {playlist.organizationPlan.summary.changedFieldCount}
                            </Label.Detail>
                          </Label>
                        </div>
                        <div className="playlist-intake-impact">
                          <LocalizedText source={playlist.organizationPlan.networkImpact} />
                        </div>
                        <div className="playlist-intake-impact">
                          {playlist.organizationPlan.coverArtAction}
                        </div>
                        <div className="playlist-intake-impact">
                          {playlist.organizationPlan.replayGainAction}
                        </div>
                        <div className="playlist-intake-organization-destinations">
                          {playlist.organizationPlan.trackPreviews.map((preview) => (
                            <div
                              className="playlist-intake-organization-row"
                              key={preview.trackId}
                            >
                              <div>
                                <strong>{preview.destinationPath}</strong>
                                <div className="playlist-intake-meta">
                                  {preview.changedFields.join(', ')}
                                </div>
                              </div>
                              <Label basic>
                                <LocalizedText source={"Line"} />{" "}{preview.lineNumber}
                              </Label>
                            </div>
                          ))}
                        </div>
                        {playlist.organizationPlan.skippedTracks.length > 0 && (
                          <div className="playlist-intake-impact">
                            <LocalizedText source={"Skipped:"} />{' '}
                            {playlist.organizationPlan.skippedTracks
                              .map((track) => track.title)
                              .join(', ')}
                          </div>
                        )}
                        {playlist.organizationApproval && (
                          <div className="playlist-intake-organization-approval">
                            <Label color="green">
                              <Icon name="check circle outline" />
                              <LocalizedText source={"Snapshot approved"} /></Label>
                            <span>
                              {playlist.organizationApproval.summary.matched} <LocalizedText source={"tracks,"} />{' '}
                              {
                                playlist.organizationApproval.summary
                                  .changedFieldCount
                              }{' '}
                              <LocalizedText source={"changed fields"} /></span>
                            <div className="playlist-intake-impact">
                              {playlist.organizationApproval.impact}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </Segment>
                  <div className="playlist-intake-tracks">
                    {playlist.tracks.map((track) => (
                      <div
                        className="playlist-intake-track"
                        key={track.id}
                      >
                        <div>
                          <strong>
                            {[track.artist, track.title].filter(Boolean).join(' - ') ||
                              track.title}
                          </strong>
                          <div className="playlist-intake-meta">
                            <Icon name="list ol" />
                            <LocalizedText source={"Line"} />{" "}{track.lineNumber}
                            <span> - </span>
                            <Icon name="quote right" />
                            {track.sourceLine}
                          </div>
                        </div>
                        <div className="playlist-intake-track-actions">
                          <Label color={trackStateColor(track.state)}>
                            <LocalizedText source={track.state} />
                          </Label>
                          <Popup
                            content={interfaceText("Mark this row as matched for partial playlist completion review. This does not search or download it.")}
                            position="top center"
                            trigger={
                              <Button
                                aria-label={interfaceText("Mark {title} matched", { "title": (track.title) })}
                                disabled={track.state === 'Matched'}
                                icon="check"
                                onClick={() => setTrackState(playlist, track, 'Matched')}
                                size="small"
                               {...interfaceTextProps("Mark {title} matched")}/>
                            }
                           {...interfaceTextProps("Mark this row as matched for partial playlist completion review. This does not search or download it.")}/>
                          <Popup
                            content={interfaceText("Mark this row unmatched so it can be reviewed or rematched later without losing source identity.")}
                            position="top center"
                            trigger={
                              <Button
                                aria-label={interfaceText("Mark {title} unmatched", { "title": (track.title) })}
                                disabled={track.state === 'Unmatched'}
                                icon="question circle outline"
                                onClick={() =>
                                  setTrackState(playlist, track, 'Unmatched')
                                }
                                size="small"
                               {...interfaceTextProps("Mark {title} unmatched")}/>
                            }
                           {...interfaceTextProps("Mark this row unmatched so it can be reviewed or rematched later without losing source identity.")}/>
                          <Popup
                            content={interfaceText("Reject this row from playlist completion while keeping it in the imported source evidence.")}
                            position="top center"
                            trigger={
                              <Button
                                aria-label={interfaceText("Reject playlist row {title}", { "title": (track.title) })}
                                disabled={track.state === 'Rejected'}
                                icon="ban"
                                negative
                                onClick={() => setTrackState(playlist, track, 'Rejected')}
                                size="small"
                               {...interfaceTextProps("Reject playlist row {title}")}/>
                            }
                           {...interfaceTextProps("Reject this row from playlist completion while keeping it in the imported source evidence.")}/>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              );
            })()}
          </Segment>
        ))}
      </div>
    </Segment>
  );
};

export default PlaylistIntake;
