import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import * as discoveryGraph from '../../lib/discoveryGraph';
import * as searches from '../../lib/searches';
import { resolveTarget } from '../../lib/musicBrainz';
import React, { useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import {
  Button,
  Form,
  Header,
  Input,
  List,
  Popup,
  Segment,
} from 'semantic-ui-react';
import DiscoveryGraphModal from './DiscoveryGraphModal';

const asArray = (value) => (Array.isArray(value) ? value : []);

const isObject = (value) =>
  value !== null && typeof value === 'object' && !Array.isArray(value);

const normalizeResolvedTarget = (data) => {
  if (!isObject(data)) {
    return null;
  }

  if (isObject(data.album)) {
    return { album: data.album };
  }

  if (isObject(data.track)) {
    return { track: data.track };
  }

  return null;
};

const MusicBrainzLookup = ({ disabled }) => {
  useInterfaceLanguage();
  const [releaseInput, setReleaseInput] = useState('');
  const [recordingInput, setRecordingInput] = useState('');
  const [discogsInput, setDiscogsInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [target, setTarget] = useState(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphOpen, setGraphOpen] = useState(false);
  const [graphData, setGraphData] = useState(null);
  const [graphRequest, setGraphRequest] = useState(null);

  const openDiscoveryGraph = async (request) => {
    setGraphLoading(true);
    setGraphOpen(true);
    setGraphRequest(request);

    try {
      const graph = await discoveryGraph.buildDiscoveryGraph(request);
      setGraphData(graph);
    } catch (error) {
      console.error(error);
      toast.error(getApiErrorMessage(error, { t: interfaceText }, 'Failed to build discovery graph'));
      setGraphOpen(false);
    } finally {
      setGraphLoading(false);
    }
  };

  const handleLookup = async () => {
    if (!releaseInput && !recordingInput && !discogsInput) {
      toast.error(interfaceText("Provide at least one MusicBrainz or Discogs identifier"));
      return;
    }

    setLoading(true);

    try {
      const payload = {
        discogsReleaseId: discogsInput.trim() || undefined,
        recordingId: recordingInput.trim() || undefined,
        releaseId: releaseInput.trim() || undefined,
      };

      const response = await resolveTarget(payload);
      const resolvedTarget = normalizeResolvedTarget(response.data);
      if (!resolvedTarget) {
        throw new Error('MusicBrainz target response did not include a target');
      }

      setTarget(resolvedTarget);

      toast.success(
        resolvedTarget.album
          ? interfaceText('Loaded album {title}', { title: resolvedTarget.album.title })
          : interfaceText('Loaded track {title}', { title: resolvedTarget.track?.title }),
      );
    } catch (error) {
      console.error(error);
      toast.error(getApiErrorMessage(error, { t: interfaceText }));
    } finally {
      setLoading(false);
    }
  };

  const summary = useMemo(() => {
    if (!target) {
      return null;
    }

    if (target.album) {
      return (
        <List>
          <List.Item>
            <List.Header><LocalizedText source={"Album"} /></List.Header>
            <List.Description>
              {target.album.title} · {target.album.artist} ·{' '}
              {target.album.tracks?.length ?? 0} <LocalizedText source={"tracks"} /></List.Description>
          </List.Item>
        </List>
      );
    }

    if (target.track) {
      return (
        <List>
          <List.Item>
            <List.Header><LocalizedText source={"Track"} /></List.Header>
            <List.Description>
              {target.track.title} · {target.track.artist} ·{' '}
              {target.track.duration
                ? `${(target.track.duration / 60_000).toFixed(2)} min`
                : <LocalizedText source={"unknown length"} />}
            </List.Description>
          </List.Item>
        </List>
      );
    }

    return null;
  }, [target]);

  const handleOpenGraph = async () => {
    if (target?.album?.musicBrainzReleaseId) {
      await openDiscoveryGraph({
        scope: 'album',
        releaseId: target.album.musicBrainzReleaseId,
        album: target.album.title,
        artist: target.album.artist,
      });
      return;
    }

    if (target?.track?.musicBrainzRecordingId) {
      await openDiscoveryGraph({
        scope: 'track',
        recordingId: target.track.musicBrainzRecordingId,
        title: target.track.title,
        artist: target.track.artist,
      });
    }
  };

  const handleGraphRecenter = async (nodeId) => {
    if (!nodeId) {
      return;
    }

    const [nodeType, rawId] = nodeId.split(':');
    if (nodeType === 'artist') {
      await openDiscoveryGraph({ scope: 'artist', artistId: rawId });
      return;
    }

    if (nodeType === 'album' || nodeType === 'release-group') {
      await openDiscoveryGraph({ scope: 'album', releaseId: rawId });
      return;
    }

    if (nodeType === 'track') {
      await openDiscoveryGraph({ scope: 'track', recordingId: rawId });
    }
  };

  const handleGraphCompare = async (nodeId, label) => {
    if (!graphRequest || !nodeId) {
      return;
    }

    await openDiscoveryGraph({
      ...graphRequest,
      compareLabel: label,
      compareNodeId: nodeId,
    });
  };

  const handleQueueNearby = async (graph) => {
    const queries = asArray(graph?.nodes)
      .filter((node) => node.nodeType === 'track')
      .map((node) => node.label || '')
      .filter(Boolean)
      .slice(0, 8);

    if (queries.length === 0) {
      toast.error(interfaceText("No nearby track nodes were available to queue"));
      return;
    }

    try {
      const count = await searches.createBatch({ queries });
      toast.success(interfaceText("Started {count} nearby graph searches", { "count": (count) }));
    } catch (error) {
      console.error(error);
      toast.error(getApiErrorMessage(error, { t: interfaceText }));
    }
  };

  return (
    <>
      <Segment
        className="musicbrainz-lookup-segment"
        raised
      >
        <Header as="h4"><LocalizedText source={"MusicBrainz / Discogs Lookup"} /></Header>
        <Form>
          <Form.Field>
            <Input
              disabled={disabled || loading}
              label={interfaceText("MusicBrainz Release ID")}
              onChange={(event) => setReleaseInput(event.target.value)}
              placeholder={interfaceText("e.g. 1c3b3668-...")}
              value={releaseInput}
             {...interfaceTextProps("MusicBrainz Release ID")}/>
          </Form.Field>
          <Form.Field>
            <Input
              disabled={disabled || loading}
              label={interfaceText("MusicBrainz Recording ID")}
              onChange={(event) => setRecordingInput(event.target.value)}
              placeholder={interfaceText("e.g. 8af4c1b9-...")}
              value={recordingInput}
             {...interfaceTextProps("MusicBrainz Recording ID")}/>
          </Form.Field>
          <Form.Field>
            <Input
              disabled={disabled || loading}
              label={interfaceText("Discogs Release/Master ID")}
              onChange={(event) => setDiscogsInput(event.target.value)}
              placeholder={interfaceText("e.g. 123456")}
              value={discogsInput}
             {...interfaceTextProps("Discogs Release/Master ID")}/>
          </Form.Field>
          <Popup
            content={interfaceText("Resolve a canonical MusicBrainz or Discogs target when you already know an identifier and want exact metadata.")}
            position="top center"
            trigger={
              <Button
                disabled={disabled || loading}
                loading={loading}
                onClick={handleLookup}
                primary
              >
                <LocalizedText source={"Resolve target"} /></Button>
            }
           {...interfaceTextProps("Resolve a canonical MusicBrainz or Discogs target when you already know an identifier and want exact metadata.")}/>
          <Popup
            content={interfaceText("Open the Discovery Graph around the resolved MusicBrainz target to branch into nearby releases, tracks, and artists.")}
            position="top center"
            trigger={
              <Button
                disabled={!target}
                onClick={handleOpenGraph}
                style={{ marginLeft: '0.5em' }}
              >
                <LocalizedText source={"Graph"} /></Button>
            }
           {...interfaceTextProps("Open the Discovery Graph around the resolved MusicBrainz target to branch into nearby releases, tracks, and artists.")}/>
          <Popup
            content={interfaceText("Open the same canonical target as a wider atlas-style discovery surface for neighborhood browsing.")}
            position="top center"
            trigger={
              <Button
                disabled={!target}
                onClick={handleOpenGraph}
                style={{ marginLeft: '0.5em' }}
              >
                <LocalizedText source={"Atlas"} /></Button>
            }
           {...interfaceTextProps("Open the same canonical target as a wider atlas-style discovery surface for neighborhood browsing.")}/>
        </Form>
        {summary}
      </Segment>
      <DiscoveryGraphModal
        graph={graphData}
        loading={graphLoading}
        onClose={() => setGraphOpen(false)}
        onCompare={handleGraphCompare}
        onQueueNearby={handleQueueNearby}
        onRecenter={handleGraphRecenter}
        onRestoreBranch={(branch) => branch?.request && openDiscoveryGraph(branch.request)}
        open={graphOpen}
      />
    </>
  );
};

export default MusicBrainzLookup;
