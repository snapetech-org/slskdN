import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";


import * as discoveryGraph from '../../lib/discoveryGraph';
import * as jobs from '../../lib/jobs';
import * as musicBrainz from '../../lib/musicBrainz';
import * as searches from '../../lib/searches';
import * as songId from '../../lib/songid';
import { getApiErrorMessage } from '../../lib/apiErrorMessages';

import DiscoveryGraphCanvas from './DiscoveryGraphCanvas';
import DiscoveryGraphModal from './DiscoveryGraphModal';
import FeatureGateNotice from '../Shared/FeatureGateNotice';
import useFeatureGates, { isFeatureEnabled } from '../Shared/useFeatureGates';
import React, { useEffect, useRef, useState } from 'react';
import { toast } from 'react-toastify';
import {
  Button,
  Divider,
  Form,
  Header,
  Input,
  Label,
  List,
  Message,
  Popup,
  Progress,
  Grid,
  Segment,
} from 'semantic-ui-react';
import { v4 as uuidv4 } from 'uuid';

const asObject = (value) =>
  value && typeof value === 'object' && !Array.isArray(value) ? value : {};

const getSyntheticVerdictColor = (verdict) => {
  switch (verdict) {
    case 'strong_suspicion':
      return 'orange';
    case 'moderate_suspicion':
      return 'yellow';
    case 'mixed_or_inconclusive':
      return 'grey';
    case 'low_signal':
      return 'green';
    default:
      return undefined;
  }
};

const getIdentityVerdictColor = (verdict) => {
  switch (verdict) {
    case 'recognized_cataloged_track':
      return 'green';
    case 'candidate_match_found':
      return 'blue';
    case 'likely_ai_or_channel_original':
      return 'orange';
    case 'needs_manual_review':
      return 'yellow';
    default:
      return undefined;
  }
};

const formatPercent = (value) => Math.round((value || 0) * 100);

const asArray = (value) => (Array.isArray(value) ? value : []);

const getStatusColor = (status) => {
  switch (status) {
    case 'completed':
      return 'green';
    case 'failed':
      return 'red';
    case 'running':
      return 'blue';
    case 'queued':
      return 'grey';
    default:
      return undefined;
  }
};

const getRunTitle = (item) =>
  item?.metadata?.title ||
  item?.query ||
  item?.summary ||
  item?.sourceType ||
  'SongID run';

const getTrackKey = (candidate) =>
  `${(candidate?.artist || '').trim().toLowerCase()}::${(candidate?.title || '').trim().toLowerCase()}`;

const getDedupedTracks = (tracks) => {
  if (!Array.isArray(tracks)) {
    return [];
  }

  const map = new Map();
  tracks.forEach((candidate) => {
    const key = getTrackKey(candidate);
    const current = map.get(key);
    if (!current || (candidate.actionScore || 0) > (current.actionScore || 0)) {
      map.set(key, {
        ...candidate,
        duplicateCount: (current?.duplicateCount || 0) + 1,
      });
    } else {
      current.duplicateCount = (current.duplicateCount || 1) + 1;
    }
  });

  return Array.from(map.values()).sort(
    (left, right) => (right.actionScore || 0) - (left.actionScore || 0),
  );
};

const getOptionKey = (option) => [
  option?.actionKind || '',
  option?.scope || '',
  option?.mode || '',
  option?.targetId || '',
  option?.searchText || '',
  Array.isArray(option?.searchTexts) ? option.searchTexts.join('|') : '',
].join('::');

const getDedupedOptions = (options) => {
  if (!Array.isArray(options)) {
    return [];
  }

  const map = new Map();
  options.forEach((option) => {
    const key = getOptionKey(option);
    const current = map.get(key);
    if (!current || (option.overallScore || 0) > (current.overallScore || 0)) {
      map.set(key, {
        ...option,
        duplicateCount: (current?.duplicateCount || 0) + 1,
      });
    } else {
      current.duplicateCount = (current.duplicateCount || 1) + 1;
    }
  });

  return Array.from(map.values()).sort(
    (left, right) => (right.overallScore || 0) - (left.overallScore || 0),
  );
};

const getPlanKey = (plan) => [
  plan?.kind || '',
  plan?.targetId || '',
  plan?.profile || '',
  plan?.searchText || '',
  plan?.title || '',
].join('::');

const getDedupedPlans = (plans) => {
  if (!Array.isArray(plans)) {
    return [];
  }

  const map = new Map();
  plans.forEach((plan) => {
    const key = getPlanKey(plan);
    const current = map.get(key);
    if (!current || (plan.actionScore || 0) > (current.actionScore || 0)) {
      map.set(key, {
        ...plan,
        duplicateCount: (current?.duplicateCount || 0) + 1,
      });
    } else {
      current.duplicateCount = (current.duplicateCount || 1) + 1;
    }
  });

  return Array.from(map.values()).sort(
    (left, right) => (right.actionScore || 0) - (left.actionScore || 0),
  );
};

const getUniqueTopActions = (actions, limit) => {
  const seen = new Set();
  return actions.filter((action) => {
    const key = (action.label || '').toLowerCase();
    if (seen.has(key)) {
      return false;
    }

    seen.add(key);
    return true;
  }).slice(0, limit);
};

const hasScorecardSignal = (scorecard) => scorecard && [
  'clipCount',
  'acoustIdHitCount',
  'rawAcoustIdHitCount',
  'songRecHitCount',
  'songRecDistinctMatchCount',
  'transcriptCount',
  'ocrCount',
  'commentFindingCount',
  'timestampHintCount',
  'chapterHintCount',
  'playlistRequestCount',
  'aiCommentMentionCount',
  'panakoHitCount',
  'audfprintHitCount',
  'corpusMatchCount',
  'provenanceSignalCount',
  'aiArtifactClipCount',
].some((key) => (scorecard[key] || 0) > 0);

const detailStyle = {
  borderTop: '1px solid rgba(34, 36, 38, 0.15)',
  marginTop: '1em',
  paddingTop: '0.75em',
};

const detailSummaryStyle = {
  cursor: 'pointer',
  fontWeight: 600,
};

const SongIDPanel = ({ disabled }) => {
  const { t } = useInterfaceLanguage();
  const { featureGates, ready: featureGatesReady } = useFeatureGates();
  const songIdEnabled = featureGatesReady && isFeatureEnabled(featureGates, 'songId');
  const [source, setSource] = useState('');
  const [targetDirectory, setTargetDirectory] = useState('');
  const [loading, setLoading] = useState(false);
  const [run, setRun] = useState(null);
  const [runs, setRuns] = useState([]);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphOpen, setGraphOpen] = useState(false);
  const [graphData, setGraphData] = useState(null);
  const [graphRequest, setGraphRequest] = useState(null);
  const currentRunIdRef = useRef(null);

  useEffect(() => {
    currentRunIdRef.current = run?.id || null;
  }, [run]);

  useEffect(() => {
    if (!songIdEnabled) return undefined;

    const connection = songId.createHub();
    let active = true;

    connection.on('LIST', (runs) => {
      if (active && Array.isArray(runs)) {
        setRuns(runs);
        if (runs.length > 0 && !currentRunIdRef.current) {
          setRun(runs[0]);
        }
      }
    });

    connection.on('CREATE', (nextRun) => {
      if (active && nextRun?.id) {
        setRuns((currentRuns) => {
          const existing = currentRuns.filter((item) => item.id !== nextRun.id);
          return [nextRun, ...existing].slice(0, 25);
        });
        if (nextRun.id === currentRunIdRef.current || !currentRunIdRef.current) {
          setRun(nextRun);
        }
      }
    });

    connection.on('UPDATE', (nextRun) => {
      if (active && nextRun?.id) {
        setRuns((currentRuns) => {
          const existing = currentRuns.filter((item) => item.id !== nextRun.id);
          return [nextRun, ...existing]
            .sort((left, right) => new Date(right.createdAt) - new Date(left.createdAt))
            .slice(0, 25);
        });
        if (nextRun.id === currentRunIdRef.current) {
          setRun(nextRun);
        }
      }
    });

    connection.start().catch((error) => {
      console.warn('SongID hub connection failed', error);
    });

    return () => {
      active = false;
      connection.stop().catch(() => {});
    };
  }, [songIdEnabled]);

  const handleAnalyze = async () => {
    const trimmed = source.trim();
    if (!trimmed) {
      toast.error(t('Provide a URL, server-side file path, or text query'));
      return;
    }

    setLoading(true);
    try {
      const result = await songId.createRun(trimmed);
      setRun(result);
      setRuns((currentRuns) => [result, ...currentRuns.filter((item) => item.id !== result.id)].slice(0, 25));
      toast.success(t('SongID analysis queued'));
    } catch (error) {
      console.error(error);
      toast.error(getApiErrorMessage(error, { t }, 'SongID analysis failed'));
    } finally {
      setLoading(false);
    }
  };

  const handleTrackSearch = async (candidate) => {
    try {
      await searches.create({
        id: uuidv4(),
        searchText: candidate.searchText,
      });
      toast.success(interfaceText("Started search for {artist} - {title}", { "artist": (candidate.artist), "title": (candidate.title) }));
    } catch (error) {
      console.error(error);
      toast.error(getApiErrorMessage(error, { t }));
    }
  };

  const handleTrackSearchBatch = async (queries) => {
    const validQueries = Array.isArray(queries)
      ? queries.map((query) => (query || '').trim()).filter(Boolean)
      : [];
    if (validQueries.length === 0) {
      toast.error(interfaceText("No candidate searches were available"));
      return;
    }

    try {
      const count = await searches.createBatch({ queries: validQueries });
      toast.success(interfaceText("Started {count} candidate searches", { "count": (count) }));
    } catch (error) {
      console.error(error);
      toast.error(getApiErrorMessage(error, { t }));
    }
  };

  const handleMixSearch = async (mix) => {
    if (!mix?.searchText) {
      toast.error(interfaceText("No mix queries were available"));
      return;
    }

    const queries = mix.searchText
      .split('+')
      .map((value) => (value || '').trim())
      .filter(Boolean);
    if (queries.length === 0) {
      toast.error(interfaceText("No mix queries were available"));
      return;
    }

    try {
      const count = await searches.createBatch({ queries });
      toast.success(interfaceText("Started {count} mix search(es) for {segmentCount} segments", { "count": (count), "segmentCount": (mix.segmentCount) }));
    } catch (error) {
      console.error(error);
      toast.error(getApiErrorMessage(error, { t }));
    }
  };

  const handleAlbumPrepare = async (candidate) => {
    try {
      await musicBrainz.resolveTarget({ releaseId: candidate.releaseId });
      toast.success(interfaceText("Prepared album target for {title}", { "title": (candidate.title) }));
    } catch (error) {
      console.error(error);
      toast.error(getApiErrorMessage(error, { t }));
    }
  };

  const handleDiscography = async (candidate) => {
    try {
      const response = await jobs.createDiscographyJob({
        artistId: candidate.artistId,
        profile: candidate.recommendedProfile || 'CoreDiscography',
        targetDirectory: targetDirectory.trim(),
      });
      toast.success(interfaceText("Planned discography job {job_id}", { "job_id": (response?.job_id) }));
    } catch (error) {
      console.error(error);
      toast.error(getApiErrorMessage(error, { t }));
    }
  };

  if (!featureGatesReady) {
    return <Message info size="small"><LocalizedText source={"Checking SongID availability…"} /></Message>;
  }

  if (!songIdEnabled) {
    return (
      <FeatureGateNotice
        configurationKeys={['feature.SongId']}
        featureGate={featureGates.songId}
        featureName="SongID"
      />
    );
  }

  const handleMbReleaseJob = async (candidate) => {
    try {
      const response = await jobs.createMbReleaseJob({
        mbReleaseId: candidate.releaseId,
        targetDir: targetDirectory.trim(),
      });
      toast.success(interfaceText("Planned album job {job_id}", { "job_id": (response?.job_id) }));
    } catch (error) {
      console.error(error);
      toast.error(getApiErrorMessage(error, { t }));
    }
  };

  const copyForensicMatrix = async () => {
    if (!run?.id || !run?.forensicMatrix) {
      toast.error(interfaceText("No forensic matrix is available for this SongID run"));
      return;
    }

    try {
      const matrix = await songId.getForensicMatrix(run.id);
      await navigator.clipboard.writeText(JSON.stringify(matrix, null, 2));
      toast.success(interfaceText("SongID forensic matrix copied"));
    } catch (error) {
      console.error(error);
      toast.error(getApiErrorMessage(error, { t }));
    }
  };

  const openDiscoveryGraph = async (request) => {
    setGraphLoading(true);
    setGraphOpen(true);
    setGraphRequest(request);

    try {
      const graph = await discoveryGraph.buildDiscoveryGraph(request);
      setGraphData(graph);
    } catch (error) {
      console.error(error);
      toast.error(getApiErrorMessage(error, { t }, 'Failed to build discovery graph'));
      setGraphOpen(false);
    } finally {
      setGraphLoading(false);
    }
  };

  const handleGraphRecenter = async (nodeId) => {
    if (!nodeId) {
      return;
    }

    const [nodeType, rawId] = nodeId.split(':');
    const nextRequest = {
      songIdRunId: run?.id,
    };

    if (nodeType === 'track') {
      nextRequest.scope = 'track';
      nextRequest.recordingId = rawId;
    } else if (nodeType === 'album' || nodeType === 'release-group') {
      nextRequest.scope = 'album';
      nextRequest.releaseId = rawId;
    } else if (nodeType === 'artist') {
      nextRequest.scope = 'artist';
      nextRequest.artistId = rawId;
    } else {
      nextRequest.scope = graphRequest?.scope || 'songid_run';
    }

    await openDiscoveryGraph(nextRequest);
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

  const handleQueueNearbyFromGraph = async (graph) => {
    const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
    const queries = nodes
      .filter((node) => node.nodeType === 'track')
      .map((node) => {
        const recordingId = node.nodeId.split(':')[1];
        const candidate = asArray(run?.tracks).find(
          (item) => item.recordingId === recordingId,
        );
        if (candidate?.searchText) {
          return candidate.searchText;
        }

        return node.label || '';
      })
      .filter(Boolean)
      .slice(0, 8);

    await handleTrackSearchBatch(queries);
  };

  const handlePlanAction = async (plan) => {
    if (plan.kind === 'track') {
      await handleTrackSearch({
        artist: plan.title.split(' - ')[0] || '',
        title: plan.title.split(' - ').slice(1).join(' - ') || plan.title,
        searchText: plan.searchText,
      });
      return;
    }

    if (plan.kind === 'album') {
      await handleAlbumPrepare({ releaseId: plan.targetId, title: plan.title });
      return;
    }

    if (plan.kind === 'artist') {
      await handleDiscography({
        artistId: plan.targetId,
        recommendedProfile: plan.profile,
      });
    }
  };

  const handleOptionAction = async (option) => {
    if (option.actionKind === 'track_search') {
      const segments = option.title.split(' - ');
      await handleTrackSearch({
        artist: segments[0] || '',
        title: segments.slice(1).join(' - ') || option.title,
        searchText: option.searchText,
      });
      return;
    }

    if (option.actionKind === 'track_search_batch') {
      await handleTrackSearchBatch(option.searchTexts);
      return;
    }

    if (option.actionKind === 'album_prepare') {
      await handleAlbumPrepare({ releaseId: option.targetId, title: option.title });
      return;
    }

    if (option.actionKind === 'mb_release_job') {
      await handleMbReleaseJob({ releaseId: option.targetId });
      return;
    }

    if (option.actionKind === 'discography_job') {
      await handleDiscography({
        artistId: option.targetId,
        recommendedProfile: option.profile,
      });
    }
  };

  const renderScores = (item) => (
    <div style={{ marginTop: '0.35em' }}>
      <Label size="tiny"><LocalizedText source={"Identity"} />{" "}{Math.round((item.identityScore || 0) * 100)}</Label>
      <Label size="tiny"><LocalizedText source={"Byzantine"} />{" "}{Math.round((item.byzantineScore || 0) * 100)}</Label>
      {item.canonicalScore ? (
        <Label color="teal" size="tiny">
          <LocalizedText source={"Canonical"} />{" "}{Math.round((item.canonicalScore || 0) * 100)}
        </Label>
      ) : null}
      <Label color="blue" size="tiny">
        <LocalizedText source={"Action"} />{" "}{Math.round((item.actionScore || 0) * 100)}
      </Label>
    </div>
  );

  const renderOptionScores = (item) => (
    <div style={{ marginTop: '0.35em' }}>
      <Label color="blue" size="tiny">
        <LocalizedText source={"Overall"} />{" "}{Math.round((item.overallScore || 0) * 100)}
      </Label>
      <Label size="tiny"><LocalizedText source={"Quality"} />{" "}{Math.round((item.qualityScore || 0) * 100)}</Label>
      <Label size="tiny"><LocalizedText source={"Byzantine"} />{" "}{Math.round((item.byzantineScore || 0) * 100)}</Label>
      <Label size="tiny"><LocalizedText source={"Ready"} />{" "}{Math.round((item.readinessScore || 0) * 100)}</Label>
    </div>
  );

  const renderSyntheticPopupContent = () => {
    if (!run?.forensicMatrix) {
      return run?.syntheticAssessment?.summary || 'No synthetic detail available.';
    }

    const matrix = run.forensicMatrix;
    return (
      <div style={{ maxWidth: 360 }}>
        <div>
          <LocalizedText source={"Synthetic score"} />{" "}{matrix.syntheticScore || 0} <LocalizedText source={"· confidence"} />{' '}
          {matrix.confidenceScore || 0} <LocalizedText source={"· family"} />{" "}{matrix.familyLabel || <LocalizedText source={"none"} />}
        </div>
        {Array.isArray(matrix.topEvidenceFor) && matrix.topEvidenceFor.length > 0 ? (
          <div style={{ marginTop: '0.5em' }}>
            <LocalizedText source={"For:"} />{" "}{matrix.topEvidenceFor.slice(0, 3).join(' | ')}
          </div>
        ) : null}
        {Array.isArray(matrix.topEvidenceAgainst) &&
        matrix.topEvidenceAgainst.length > 0 ? (
          <div style={{ marginTop: '0.5em' }}>
            <LocalizedText source={"Against:"} />{" "}{matrix.topEvidenceAgainst.slice(0, 3).join(' | ')}
          </div>
        ) : null}
        {Array.isArray(matrix.notes) && matrix.notes.length > 0 ? (
          <div style={{ marginTop: '0.5em' }}>
            <LocalizedText source={"Notes:"} />{" "}{matrix.notes.slice(0, 4).join(' | ')}
          </div>
        ) : null}
      </div>
    );
  };

  const renderLane = (label, lane) => {
    if (!lane) {
      return null;
    }

    const metricSummary = Object.entries(asObject(lane.metrics))
      .slice(0, 5)
      .map(([key, value]) => `${key}: ${value}`)
      .join(' | ');

    return (
      <Popup
        key={label}
        content={
          <div style={{ maxWidth: 360 }}>
            <div>{lane.summary || <LocalizedText source={"No lane summary."} />}</div>
            {metricSummary ? (
              <div style={{ marginTop: '0.5em' }}>{metricSummary}</div>
            ) : null}
          </div>
        }
        position="top left"
        trigger={
          <Label size="tiny">
            {label} {Math.round((lane.score || 0) * 100)}
          </Label>
        }
      />
    );
  };

  const tracks = getDedupedTracks(run?.tracks);
  const options = getDedupedOptions(run?.options);
  const plans = getDedupedPlans(run?.plans);
  const bestTrack = tracks[0];
  const bestAlbum = Array.isArray(run?.albums) ? run.albums[0] : null;
  const bestArtist = Array.isArray(run?.artists) ? run.artists[0] : null;
  const topActions = getUniqueTopActions([
    bestTrack ? {
      label: interfaceText("Search Best Track"),
      track: bestTrack,
      type: 'track',
    } : null,
    bestAlbum ? {
      album: bestAlbum,
      label: interfaceText("Download Best Album"),
      type: 'album',
    } : null,
    bestArtist ? {
      artist: bestArtist,
      label: interfaceText("Plan Best Artist"),
      type: 'artist',
    } : null,
    ...options.slice(0, 4).map((option) => ({
      label: option.actionLabel,
      option,
      type: 'option',
    })),
    ...plans.slice(0, 4).map((plan) => ({
      label: plan.actionLabel,
      plan,
      type: 'plan',
    })),
  ].filter(Boolean), 5);
  const identityVerdict = run?.identityAssessment?.verdict || run?.assessment?.verdict;
  const identityConfidence = (run?.identityAssessment?.confidence ?? run?.assessment?.confidence) || 0;
  const identitySummary = run?.identityAssessment?.summary || run?.assessment?.summary;
  const showIdentity = Boolean(identitySummary || identityConfidence > 0 || (identityVerdict && identityVerdict !== 'unclassified'));
  const showSynthetic = Boolean(
    run?.syntheticAssessment?.summary ||
    (run?.syntheticAssessment?.verdict && run.syntheticAssessment.verdict !== 'insufficient_evidence') ||
    run?.forensicMatrix?.familyLabel ||
    hasScorecardSignal(run?.scorecard),
  );

  return (
    <>
    <Segment
      className="songid-panel"
      raised
    >
      <Header as="h4"><LocalizedText source={"SongID"} /></Header>
      <p style={{ marginTop: 0 }}>
        <LocalizedText source={"Identify a likely track, album, or artist from a YouTube URL, Spotify URL, server-side file path, or direct text query, then fan the result out into slskdN actions."} /></p>
      <Form>
        <Form.Field>
          <Input
            disabled={disabled || loading}
            onChange={(event) => setSource(event.target.value)}
            placeholder={interfaceText("Paste a source URL, local server path, or text query")}
            value={source}
           {...interfaceTextProps("Paste a source URL, local server path, or text query")}/>
        </Form.Field>
        <Form.Field>
          <Input
            disabled={disabled || loading}
            onChange={(event) => setTargetDirectory(event.target.value)}
            placeholder={interfaceText("Optional target directory for album or discography jobs")}
            value={targetDirectory}
           {...interfaceTextProps("Optional target directory for album or discography jobs")}/>
        </Form.Field>
        <Popup
          content={interfaceText("Analyze the source and rank likely track, album, and artist candidates so you can search or plan downloads from the result.")}
          position="top right"
          trigger={
            <Button
              disabled={disabled || loading}
              loading={loading}
              onClick={handleAnalyze}
              primary
            >
              <LocalizedText source={"Analyze with SongID"} /></Button>
          }
         {...interfaceTextProps("Analyze the source and rank likely track, album, and artist candidates so you can search or plan downloads from the result.")}/>
      </Form>

      <Grid stackable columns={2} style={{ marginTop: '1em' }}>
        <Grid.Column width={5}>
          <Segment
            className="songid-queue-panel"
            secondary
          >
            <Header as="h5" style={{ marginTop: 0 }}>
              <LocalizedText source={"Queue"} /></Header>
            {runs.length === 0 ? (
              <p style={{ marginBottom: 0 }}><LocalizedText source={"No SongID runs yet."} /></p>
            ) : (
              <List divided relaxed>
                {runs.map((item) => (
                  <List.Item key={item.id}>
                    <List.Content floated="right">
                      <Popup
                        content={interfaceText("Open this SongID run and follow its queue position, evidence, and download options.")}
                        position="top center"
                        trigger={
                          <Button
                            size="mini"
                            onClick={() => setRun(item)}
                            primary={run?.id === item.id}
                          >
                            <LocalizedText source={"View"} /></Button>
                        }
                       {...interfaceTextProps("Open this SongID run and follow its queue position, evidence, and download options.")}/>
                      <Popup
                        content={interfaceText("Open the Discovery Graph centered on this SongID run so you can inspect its neighborhood without leaving the queue.")}
                        position="top center"
                        trigger={
                          <Button
                            onClick={() =>
                              openDiscoveryGraph({
                                scope: 'songid_run',
                                songIdRunId: item.id,
                                title: item.query || item.summary,
                              })
                            }
                            size="mini"
                            style={{ marginLeft: '0.5em' }}
                          >
                            <LocalizedText source={"Graph"} /></Button>
                        }
                       {...interfaceTextProps("Open the Discovery Graph centered on this SongID run so you can inspect its neighborhood without leaving the queue.")}/>
                    </List.Content>
                    <List.Content>
                      <List.Header>{getRunTitle(item)}</List.Header>
                      <List.Description>
                        <Label
                          color={getStatusColor(item.status)}
                          size="tiny"
                        >
                          {item.status || <LocalizedText source={"unknown"} />}
                        </Label>
                        <Label size="tiny">{item.sourceType || <LocalizedText source={"unknown"} />}</Label>
                        {item.percentComplete ? (
                          <Label size="tiny">
                            {formatPercent(item.percentComplete)}%
                          </Label>
                        ) : null}
                      </List.Description>
                      <List.Description style={{ marginTop: '0.35em' }}>
                        {item.queuePosition !== null &&
                        item.queuePosition !== undefined ? (
                          <Label size="tiny"><LocalizedText source={"Queue"} />{" "}{item.queuePosition}</Label>
                        ) : null}
                        {item.workerSlot !== null &&
                        item.workerSlot !== undefined ? (
                          <Label size="tiny"><LocalizedText source={"Worker"} />{" "}{item.workerSlot}</Label>
                        ) : null}
                        {item.currentStage ? (
                          <Label size="tiny">{item.currentStage}</Label>
                        ) : null}
                      </List.Description>
                      {item.summary ? (
                        <List.Description style={{ marginTop: '0.35em' }}>
                          {item.summary}
                        </List.Description>
                      ) : null}
                    </List.Content>
                  </List.Item>
                ))}
              </List>
            )}
          </Segment>
        </Grid.Column>
        <Grid.Column width={11}>
      {run ? (
            <Segment
              className="songid-result-panel"
              secondary
            >
          <Header as="h5" style={{ marginTop: 0 }}>
            <LocalizedText source={"Result"} /></Header>
          <div style={{ marginBottom: '1em' }}>
            <Popup
              content={interfaceText("Open the Discovery Graph for this SongID run and move sideways through nearby tracks, albums, artists, and decomposed segments.")}
              position="top center"
              trigger={
                <Button
                  onClick={() =>
                    openDiscoveryGraph({
                      scope: 'songid_run',
                      songIdRunId: run?.id,
                      title: run?.query || run?.metadata?.title,
                    })
                  }
                  size="small"
                >
                  <LocalizedText source={"Open Discovery Graph"} /></Button>
              }
             {...interfaceTextProps("Open the Discovery Graph for this SongID run and move sideways through nearby tracks, albums, artists, and decomposed segments.")}/>
          </div>
                  <Segment className="songid-result-summary">
            <Header as="h4" style={{ marginTop: 0 }}>
              {bestTrack
                ? <LocalizedText source={"{artist} - {title}"} values={{ "artist": (bestTrack.artist), "title": (bestTrack.title) }} />
                : getRunTitle(run)}
            </Header>
            <div style={{ marginBottom: '0.75em' }}>
              <Label color={getStatusColor(run.status)} size="small">
                {run.status || <LocalizedText source={"unknown"} />}
              </Label>
              <Label size="small">{run.currentStage || <LocalizedText source={"queued"} />}</Label>
              <Label size="small">{run.sourceType || <LocalizedText source={"unknown"} />}</Label>
              {run.workerSlot !== null && run.workerSlot !== undefined ? (
                <Label size="small"><LocalizedText source={"Worker"} />{" "}{run.workerSlot}</Label>
              ) : null}
              {run.queuePosition !== null && run.queuePosition !== undefined ? (
                <Label size="small"><LocalizedText source={"Queue"} />{" "}{run.queuePosition}</Label>
              ) : null}
            </div>
            {run.summary ? <p>{run.summary}</p> : null}
            {run.query ? (
              <p style={{ marginBottom: 0 }}>
                <strong><LocalizedText source={"Query:"} /></strong> {run.query}
              </p>
            ) : null}
          </Segment>
          <Progress
            color={run.status === 'failed' ? 'red' : 'blue'}
            percent={Math.round((run.percentComplete || 0) * 100)}
            precision={0}
            progress
            size="small"
          >
            {run.currentStage || <LocalizedText source={"queued"} />}
          </Progress>
          {topActions.length > 0 ? (
            <>
              <Header as="h5"><LocalizedText source={"Best Next Actions"} /></Header>
              <div style={{ marginBottom: '1em' }}>
                {topActions.map((action, index) => {
                  const content = {
                    album: 'Create a single-release job from the strongest album candidate.',
                    artist: 'Create a discography job from the strongest artist candidate.',
                    option: 'Run this ranked SongID acquisition option.',
                    plan: 'Run this ranked SongID plan.',
                    track: 'Start a regular slskdN search using the strongest SongID track candidate.',
                  }[action.type];
                  const onClick = () => {
                    if (action.type === 'track') {
                      return handleTrackSearch(action.track);
                    }
                    if (action.type === 'album') {
                      return handleMbReleaseJob(action.album);
                    }
                    if (action.type === 'artist') {
                      return handleDiscography(action.artist);
                    }
                    if (action.type === 'option') {
                      return handleOptionAction(action.option);
                    }

                    return handlePlanAction(action.plan);
                  };

                  return (
                    <Popup
                      key={`${action.type}-${action.label}-${index}`}
                      content={content}
                      position="top center"
                      trigger={
                        <Button
                          onClick={onClick}
                          primary={index === 0}
                          size="small"
                          style={{ marginLeft: index === 0 ? 0 : '0.5em' }}
                        >
                          {action.label}
                        </Button>
                      }
                    />
                  );
                })}
              </div>
            </>
          ) : null}
          {graphData && graphRequest?.songIdRunId === run?.id ? (
            <>
              <Divider />
              <Header as="h5"><LocalizedText source={"Mini-map"} /></Header>
              <Segment secondary>
                <DiscoveryGraphCanvas
                  graph={graphData}
                  height={220}
                  onNodeClick={handleGraphRecenter}
                  width={520}
                />
              </Segment>
            </>
          ) : null}

          {Array.isArray(run.mixGroups) && run.mixGroups.length > 0 ? (
            <>
              <Header as="h5"><LocalizedText source={"Mix Clusters"} /></Header>
              <List divided relaxed>
                {run.mixGroups.map((mix) => (
                  <List.Item key={mix.mixId}>
                    <List.Content floated="right">
                      <Popup
                        content={interfaceText("Queue the mix cluster segments as a batch of SongID searches.")}
                        position="top center"
                        trigger={
                          <Button
                            onClick={() => handleMixSearch(mix)}
                            size="small"
                          >
                            <LocalizedText source={"Search Mix"} /></Button>
                        }
                       {...interfaceTextProps("Queue the mix cluster segments as a batch of SongID searches.")}/>
                    </List.Content>
                    <List.Content>
                      <List.Header>{mix.label}</List.Header>
                      <List.Description>
                        {mix.segmentCount} <LocalizedText source={"segments · confidence"} />{" "}{Math.round((mix.confidence || 0) * 100)}
                      </List.Description>
                      <List.Description>
                        <LocalizedText source={"Identity"} />{" "}{Math.round((mix.identityScore || 0) * 100)} <LocalizedText source={"· Byzantine"} />{" "}{Math.round((mix.byzantineScore || 0) * 100)}
                      </List.Description>
                      {mix.searchText ? (
                        <List.Description>
                          <LocalizedText source={"Query:"} />{" "}{mix.searchText}
                        </List.Description>
                      ) : null}
                    </List.Content>
                  </List.Item>
                ))}
              </List>
            </>
          ) : null}

          {showIdentity ? (
            <>
              <Header as="h5"><LocalizedText source={"Identity"} /></Header>
              <p>
                <strong><LocalizedText source={"Verdict:"} /></strong>{' '}
                <Label
                  color={getIdentityVerdictColor(identityVerdict)}
                  size="tiny"
                >
                  {identityVerdict || <LocalizedText source={"unclassified"} />}
                </Label>
                <br />
                <strong><LocalizedText source={"Confidence:"} /></strong> {formatPercent(identityConfidence)}
                <br />
                <strong><LocalizedText source={"Reasoning:"} /></strong> {identitySummary || <LocalizedText source={"None"} />}
              </p>
            </>
          ) : null}

          {showSynthetic ? (
            <>
              <Header as="h5"><LocalizedText source={"Synthetic Signals"} /></Header>
              <div style={{ marginBottom: '1em' }}>
                <Popup
                  content={renderSyntheticPopupContent()}
                  position="top left"
                  trigger={
                    <Label
                      color={getSyntheticVerdictColor(
                        run.syntheticAssessment?.verdict,
                      )}
                      size="tiny"
                    >
                      <LocalizedText source={"Synthetic"} />{" "}{run.syntheticAssessment?.verdict || 'unknown'}
                    </Label>
                  }
                />
                <Popup
                  content={interfaceText("Confidence applies to the synthetic-likelihood readout only. It does not control download decisions when identity is strong.")}
                  position="top left"
                  trigger={
                    <Label size="tiny">
                      <LocalizedText source={"Confidence"} />{' '}
                      {run.forensicMatrix?.confidenceScore ||
                        run.syntheticAssessment?.confidence ||
                        'low'}
                    </Label>
                  }
                 {...interfaceTextProps("Confidence applies to the synthetic-likelihood readout only. It does not control download decisions when identity is strong.")}/>
                {run.forensicMatrix?.familyLabel ? (
                  <Popup
                    content={`Known-family score ${run.forensicMatrix.knownFamilyScore || 0}. This is a hint lane, not a download-control signal.`}
                    position="top left"
                    trigger={
                      <Label size="tiny">
                        <LocalizedText source={"Family"} />{" "}{run.forensicMatrix.familyLabel}
                      </Label>
                    }
                  />
                ) : null}
                {run.forensicMatrix?.qualityClass ? (
                  <Label size="tiny">
                    <LocalizedText source={"Quality"} />{" "}{run.forensicMatrix.qualityClass}
                  </Label>
                ) : null}
                {run.forensicMatrix?.perturbationStability !== undefined ? (
                  <Label size="tiny">
                    <LocalizedText source={"Stability"} />{' '}
                    {Math.round(
                      (run.forensicMatrix.perturbationStability || 0) * 100,
                    )}
                  </Label>
                ) : null}
              </div>
              {run.syntheticAssessment?.summary ? (
                <p style={{ marginTop: 0 }}>
                  {run.syntheticAssessment.summary}
                </p>
              ) : null}
              <div style={{ marginBottom: '1em' }}>
                {renderLane('Provenance', run.forensicMatrix?.provenanceLane)}
                {renderLane('Spectral', run.forensicMatrix?.spectralArtifactLane)}
                {renderLane('Descriptor', run.forensicMatrix?.descriptorPriorsLane)}
                {renderLane('Lyrics', run.forensicMatrix?.lyricsSpeechLane)}
                {renderLane('Structure', run.forensicMatrix?.structuralLane)}
                {renderLane('Family', run.forensicMatrix?.generatorFamilyLane)}
              </div>
            </>
          ) : null}

          {hasScorecardSignal(run.scorecard) ? (
            <details style={detailStyle}>
              <summary style={detailSummaryStyle}><LocalizedText source={"Scorecard"} /></summary>
              <div style={{ marginBottom: '1em' }}>
                <Label size="tiny"><LocalizedText source={"Audio"} />{" "}{run.scorecard.analysisAudioSource || <LocalizedText source={"none"} />}</Label>
                <Label size="tiny"><LocalizedText source={"Clips"} />{" "}{run.scorecard.clipCount || 0}</Label>
                <Label size="tiny"><LocalizedText source={"AcoustID"} />{" "}{run.scorecard.acoustIdHitCount || 0}</Label>
                <Label size="tiny"><LocalizedText source={"AcoustID Raw"} />{" "}{run.scorecard.rawAcoustIdHitCount || 0}</Label>
                <Label size="tiny"><LocalizedText source={"SongRec"} />{" "}{run.scorecard.songRecHitCount || 0}</Label>
                <Label size="tiny"><LocalizedText source={"SongRec Distinct"} />{" "}{run.scorecard.songRecDistinctMatchCount || 0}</Label>
                <Label size="tiny"><LocalizedText source={"Transcript"} />{" "}{run.scorecard.transcriptCount || 0}</Label>
                <Label size="tiny">OCR {run.scorecard.ocrCount || 0}</Label>
                <Label size="tiny"><LocalizedText source={"Comments"} />{" "}{run.scorecard.commentFindingCount || 0}</Label>
                <Label size="tiny"><LocalizedText source={"Timestamps"} />{" "}{run.scorecard.timestampHintCount || 0}</Label>
                <Label size="tiny"><LocalizedText source={"Chapters"} />{" "}{run.scorecard.chapterHintCount || 0}</Label>
                <Label size="tiny"><LocalizedText source={"Playlist Requests"} />{" "}{run.scorecard.playlistRequestCount || 0}</Label>
                <Label size="tiny"><LocalizedText source={"AI Mentions"} />{" "}{run.scorecard.aiCommentMentionCount || 0}</Label>
                <Label size="tiny"><LocalizedText source={"Panako"} />{" "}{run.scorecard.panakoHitCount || 0}</Label>
                <Label size="tiny"><LocalizedText source={"Audfprint"} />{" "}{run.scorecard.audfprintHitCount || 0}</Label>
                <Label size="tiny"><LocalizedText source={"Corpus"} />{" "}{run.scorecard.corpusMatchCount || 0}</Label>
                <Label size="tiny">
                  <LocalizedText source={"Provenance"} />{" "}{run.scorecard.provenanceSignalCount || 0}
                </Label>
                <Label size="tiny">
                  <LocalizedText source={"AI Heuristics"} />{" "}{run.scorecard.aiArtifactClipCount || 0}
                </Label>
              </div>
              {Array.isArray(run.scorecard.embeddedMetadataKeys) &&
              run.scorecard.embeddedMetadataKeys.length > 0 ? (
                <div style={{ marginBottom: '1em' }}>
                  <strong><LocalizedText source={"Metadata Keys:"} /></strong>{' '}
                  {run.scorecard.embeddedMetadataKeys.join(', ')}
                </div>
              ) : null}
              {Array.isArray(run.scorecard.provenanceSignals) &&
              run.scorecard.provenanceSignals.length > 0 ? (
                <div style={{ marginBottom: '1em' }}>
                  <strong><LocalizedText source={"Provenance Signals:"} /></strong>{' '}
                  {run.scorecard.provenanceSignals.join(', ')}
                </div>
              ) : null}
            </details>
          ) : null}

          {run.fullSourceFingerprint ? (
            <details style={detailStyle}>
              <summary style={detailSummaryStyle}><LocalizedText source={"Full-Source Fingerprint"} /></summary>
              <p>
                <strong><LocalizedText source={"Duration:"} /></strong>{' '}
                {Math.round(run.fullSourceFingerprint.durationSeconds || 0)}<LocalizedText source={"s"} /><br />
                <strong><LocalizedText source={"Fingerprint Length:"} /></strong>{' '}
                {run.fullSourceFingerprint.fingerprintLength || 0}
                <br />
                <strong><LocalizedText source={"Path:"} /></strong> {run.fullSourceFingerprint.path}
              </p>
            </details>
          ) : null}

          {run.provenance && run.provenance.signalCount > 0 ? (
            <>
              <Header as="h5"><LocalizedText source={"Provenance"} /></Header>
              <div style={{ marginBottom: '0.75em' }}>
                <Label size="tiny">
                  <LocalizedText source={"Tool"} />{" "}{run.provenance.toolAvailable ? <LocalizedText source={"available"} /> : <LocalizedText source={"unavailable"} />}
                </Label>
                <Label size="tiny">
                  <LocalizedText source={"Manifest"} />{" "}{run.provenance.manifestHint ? <LocalizedText source={"hinted"} /> : <LocalizedText source={"none"} />}
                </Label>
                <Label size="tiny">
                  <LocalizedText source={"Validation"} />{" "}{run.provenance.validationState || <LocalizedText source={"unknown"} />}
                </Label>
                {run.provenance.verified ? (
                  <Label color="green" size="tiny">
                    <LocalizedText source={"verified"} /></Label>
                ) : null}
              </div>
              <List bulleted>
                {asArray(run.provenance.signals).map((signal) => (
                  <List.Item key={signal}>{signal}</List.Item>
                ))}
              </List>
            </>
          ) : null}

          {run.aiHeuristics ? (
            <details style={detailStyle}>
              <summary style={detailSummaryStyle}><LocalizedText source={"AI Audio Heuristics"} /></summary>
              <div style={{ marginBottom: '1em' }}>
                <Label size="tiny">
                  <LocalizedText source={"Score"} />{" "}{Math.round((run.aiHeuristics.artifactScore || 0) * 100)}
                </Label>
                <Label size="tiny">{run.aiHeuristics.artifactLabel || <LocalizedText source={"unknown"} />}</Label>
                <Label size="tiny">
                  <LocalizedText source={"Peaks"} />{" "}{run.aiHeuristics.peakCount || 0}
                </Label>
                <Label size="tiny">
                  <LocalizedText source={"Periodicity"} />{' '}
                  {Math.round((run.aiHeuristics.periodicityStrength || 0) * 100)}
                </Label>
                <Label size="tiny">
                  <LocalizedText source={"Centroid"} />{" "}{Math.round(run.aiHeuristics.spectralCentroid || 0)}
                </Label>
                <Label size="tiny">
                  <LocalizedText source={"Flux"} />{" "}{Math.round((run.aiHeuristics.spectralFlux || 0) * 1000)}
                </Label>
                <Label size="tiny">
                  <LocalizedText source={"Pitch"} />{" "}{Math.round((run.aiHeuristics.pitchSalience || 0) * 100)}
                </Label>
              </div>
            </details>
          ) : null}

          {Array.isArray(run.perturbations) && run.perturbations.length > 0 ? (
            <details style={detailStyle}>
              <summary style={detailSummaryStyle}>
                <LocalizedText source={"Perturbation Stability ("} />{run.perturbations.length})
              </summary>
              <List divided relaxed>
                {run.perturbations.map((item) => (
                  <List.Item key={item.perturbationId}>
                    <List.Content>
                      <List.Header>{item.label}</List.Header>
                      <List.Description>
                        <LocalizedText source={"Delta"} />{" "}{Math.round((item.baselineDelta || 0) * 100)}
                      </List.Description>
                      {item.heuristics ? (
                        <List.Description style={{ marginTop: '0.35em' }}>
                          <LocalizedText source={"Score"} />{" "}{Math.round((item.heuristics.artifactScore || 0) * 100)} ·
                          {` `}<LocalizedText source={"Label"} />{" "}{item.heuristics.artifactLabel || <LocalizedText source={"unknown"} />}
                        </List.Description>
                      ) : null}
                    </List.Content>
                  </List.Item>
                ))}
              </List>
            </details>
          ) : null}

          {Array.isArray(run.corpusMatches) && run.corpusMatches.length > 0 ? (
            <>
              <Header as="h5"><LocalizedText source={"Corpus Matches"} /></Header>
              <List divided relaxed>
                {run.corpusMatches.map((match) => (
                  <List.Item key={match.matchId}>
                    <List.Content>
                      <List.Header>{match.label || match.source}</List.Header>
                      <List.Description>
                        <LocalizedText source={"Similarity"} />{" "}{Math.round((match.similarityScore || 0) * 100)}
                      </List.Description>
                      {match.artist || match.title ? (
                        <List.Description style={{ marginTop: '0.35em' }}>
                          {[match.artist, match.title].filter(Boolean).join(' - ')}
                        </List.Description>
                      ) : null}
                      {match.recordingId ? (
                        <List.Description style={{ marginTop: '0.35em' }}>
                          <LocalizedText source={"Recording:"} />{" "}{match.recordingId}
                        </List.Description>
                      ) : null}
                    </List.Content>
                  </List.Item>
                ))}
              </List>
            </>
          ) : null}

          {Array.isArray(run.stems) && run.stems.length > 0 ? (
            <>
              <Header as="h5"><LocalizedText source={"Demucs Stems"} /></Header>
              <List bulleted>
                {run.stems.map((stem) => (
                  <List.Item key={stem.artifactId}>
                    {stem.label}: {stem.path}
                  </List.Item>
                ))}
              </List>
            </>
          ) : null}

          {Array.isArray(run.evidence) && run.evidence.length > 0 ? (
            <details style={detailStyle}>
              <summary style={detailSummaryStyle}>
                <LocalizedText source={"Evidence ("} />{run.evidence.length})
              </summary>
              <List bulleted>
                {run.evidence.map((item) => (
                  <List.Item key={item}>{item}</List.Item>
                ))}
              </List>
            </details>
          ) : null}

          {Array.isArray(run.segments) && run.segments.length > 0 ? (
            <>
              <Header as="h5"><LocalizedText source={"Segment Decomposition"} /></Header>
              <List divided relaxed>
                {run.segments.map((segment) => (
                  <List.Item key={segment.segmentId}>
                    <List.Content>
                      <List.Header>
                        {segment.label}{' '}
                        <Label size="tiny">
                          {Math.round((segment.confidence || 0) * 100)}%
                        </Label>
                      </List.Header>
                      <List.Description>
                        {segment.decompositionLabel || segment.sourceLabel}
                      </List.Description>
                      <List.Description style={{ marginTop: '0.35em' }}>
                        <LocalizedText source={"Search:"} />{" "}<code>{segment.query}</code>
                      </List.Description>
                      {Array.isArray(segment.candidates) &&
                      segment.candidates.length > 0 ? (
                        <List.Description style={{ marginTop: '0.5em' }}>
                          {segment.candidates.map((candidate) => (
                            <Label key={candidate.candidateId} size="tiny">
                              {candidate.artist} - {candidate.title}
                            </Label>
                          ))}
                        </List.Description>
                      ) : null}
                      <div style={{ marginTop: '0.5em' }}>
                        {Array.isArray(segment.options) &&
                        segment.options.length > 0 ? (
                          <Popup
                            content={interfaceText("Run the best segment-level SongID action for this decomposed portion of the source.")}
                            position="top center"
                            trigger={
                              <Button
                                onClick={() => handleOptionAction(segment.options[0])}
                                size="mini"
                              >
                                {segment.options[0].actionLabel}
                              </Button>
                            }
                           {...interfaceTextProps("Run the best segment-level SongID action for this decomposed portion of the source.")}/>
                        ) : (
                          <Popup
                            content={interfaceText("Search this decomposed segment directly when SongID found a plausible chapter or timestamp clue.")}
                            position="top center"
                            trigger={
                              <Button
                                onClick={() =>
                                  handleTrackSearchBatch([segment.query])
                                }
                                size="mini"
                              >
                                <LocalizedText source={"Search Segment"} /></Button>
                            }
                           {...interfaceTextProps("Search this decomposed segment directly when SongID found a plausible chapter or timestamp clue.")}/>
                        )}
                      </div>
                    </List.Content>
                  </List.Item>
                ))}
              </List>
            </>
          ) : null}

          {options.length > 0 ? (
            <details style={detailStyle}>
              <summary style={detailSummaryStyle}>
                <LocalizedText source={"Ranked Download Options ("} />{options.length})
              </summary>
              <List divided relaxed>
                {options.map((option) => (
                  <List.Item key={option.optionId}>
                    <List.Content floated="right">
                      <Popup
                        content={interfaceText("Run this SongID acquisition option using the scored track, album, or discography path shown here.")}
                        position="top center"
                        trigger={
                          <Button
                            onClick={() => handleOptionAction(option)}
                            size="small"
                          >
                            {option.actionLabel}
                          </Button>
                        }
                       {...interfaceTextProps("Run this SongID acquisition option using the scored track, album, or discography path shown here.")}/>
                    </List.Content>
                    <List.Content>
                      <List.Header>
                        {option.title}{' '}
                        <Label size="tiny">{option.scope}</Label>
                        <Label size="tiny">{option.mode}</Label>
                        {option.duplicateCount > 1 ? (
                          <Label color="grey" size="tiny">
                            {option.duplicateCount} <LocalizedText source={"matches"} /></Label>
                        ) : null}
                      </List.Header>
                      <List.Description>{option.description}</List.Description>
                      {option.searchText ? (
                        <List.Description style={{ marginTop: '0.35em' }}>
                          <LocalizedText source={"Search:"} />{" "}<code>{option.searchText}</code>
                        </List.Description>
                      ) : null}
                      {Array.isArray(option.searchTexts) &&
                      option.searchTexts.length > 0 ? (
                        <List.Description style={{ marginTop: '0.35em' }}>
                          <LocalizedText source={"Searches:"} />{" "}<code>{option.searchTexts.join(' | ')}</code>
                        </List.Description>
                      ) : null}
                      {option.profile ? (
                        <List.Description style={{ marginTop: '0.35em' }}>
                          <LocalizedText source={"Profile:"} />{" "}{option.profile}
                        </List.Description>
                      ) : null}
                      {renderOptionScores(option)}
                    </List.Content>
                  </List.Item>
                ))}
              </List>
            </details>
          ) : null}

          {Array.isArray(run.clips) && run.clips.length > 0 ? (
            <details style={detailStyle}>
              <summary style={detailSummaryStyle}>
                <LocalizedText source={"Clip Findings ("} />{run.clips.length})
              </summary>
              <List divided relaxed>
                {run.clips.map((clip) => (
                  <List.Item key={clip.clipId}>
                    <List.Content>
                      <List.Header>
                        {clip.profile} @ {clip.startSeconds}<LocalizedText source={"s"} /></List.Header>
                      <List.Description>
                        {clip.durationSeconds}<LocalizedText source={"s clip"} /></List.Description>
                      {clip.acoustId ? (
                        <List.Description style={{ marginTop: '0.35em' }}>
                          <LocalizedText source={"AcoustID:"} />{" "}{clip.acoustId.artist} - {clip.acoustId.title}
                        </List.Description>
                      ) : null}
                      {clip.songRec ? (
                        <List.Description style={{ marginTop: '0.35em' }}>
                          <LocalizedText source={"SongRec:"} />{" "}{clip.songRec.artist} - {clip.songRec.title}
                        </List.Description>
                      ) : null}
                      {clip.panako ? (
                        <List.Description style={{ marginTop: '0.35em' }}>
                          <LocalizedText source={"Panako:"} />{" "}{clip.panako.title || clip.panako.sourcePath}
                        </List.Description>
                      ) : null}
                      {clip.audfprint ? (
                        <List.Description style={{ marginTop: '0.35em' }}>
                          <LocalizedText source={"Audfprint:"} />{" "}{clip.audfprint.title}
                        </List.Description>
                      ) : null}
                      {clip.aiHeuristics ? (
                        <List.Description style={{ marginTop: '0.35em' }}>
                          <LocalizedText source={"AI Heuristics:"} />{" "}{clip.aiHeuristics.artifactLabel} (
                          {Math.round((clip.aiHeuristics.artifactScore || 0) * 100)})
                        </List.Description>
                      ) : null}
                    </List.Content>
                  </List.Item>
                ))}
              </List>
            </details>
          ) : null}

          {Array.isArray(run.transcripts) && run.transcripts.length > 0 ? (
            <details style={detailStyle}>
              <summary style={detailSummaryStyle}>
                <LocalizedText source={"Transcripts ("} />{run.transcripts.length})
              </summary>
              <List divided relaxed>
                {run.transcripts.map((transcript) => (
                  <List.Item key={transcript.transcriptId}>
                    <List.Content>
                      <List.Header>{transcript.source}</List.Header>
                      <List.Description>{transcript.text}</List.Description>
                      <List.Description style={{ marginTop: '0.35em' }}>
                        <LocalizedText source={"Segments:"} />{" "}{transcript.segmentCount || 0} <LocalizedText source={"· Language:"} />{' '}
                        {transcript.language || <LocalizedText source={"unknown"} />} <LocalizedText source={"· Excerpt:"} />{' '}
                        {transcript.excerptStartSeconds || 0}<LocalizedText source={"s /"} />{' '}
                        {transcript.excerptDurationSeconds || 0}<LocalizedText source={"s"} /></List.Description>
                      {Array.isArray(transcript.musicBrainzQueries) &&
                      transcript.musicBrainzQueries.length > 0 ? (
                        <List.Description style={{ marginTop: '0.35em' }}>
                          <LocalizedText source={"Queries:"} />{" "}{transcript.musicBrainzQueries.join(' | ')}
                        </List.Description>
                      ) : null}
                    </List.Content>
                  </List.Item>
                ))}
              </List>
            </details>
          ) : null}

          {Array.isArray(run.ocr) && run.ocr.length > 0 ? (
            <details style={detailStyle}>
              <summary style={detailSummaryStyle}><LocalizedText source={"OCR ("} />{run.ocr.length})</summary>
              <List bulleted>
                {run.ocr.map((item) => (
                  <List.Item key={item.ocrId}>
                    {item.timestampSeconds}s: {item.text}
                  </List.Item>
                ))}
              </List>
            </details>
          ) : null}

          {Array.isArray(run.comments) && run.comments.length > 0 ? (
            <details style={detailStyle}>
              <summary style={detailSummaryStyle}>
                <LocalizedText source={"Comments ("} />{run.comments.length})
              </summary>
              <List bulleted>
                {run.comments.map((comment) => (
                  <List.Item key={comment.commentId}>
                    {comment.author ? <LocalizedText source={"{author}:"} values={{ "author": (comment.author) }} /> : ''}
                    {comment.text}
                    {comment.timestampSeconds !== null &&
                    comment.timestampSeconds !== undefined
                      ? <LocalizedText source={"({timestampSeconds}s)"} values={{ "timestampSeconds": (comment.timestampSeconds) }} />
                      : ''}
                  </List.Item>
                ))}
              </List>
            </details>
          ) : null}

          {Array.isArray(run.chapters) && run.chapters.length > 0 ? (
            <>
              <Header as="h5"><LocalizedText source={"Chapters"} /></Header>
              <List bulleted>
                {run.chapters.map((chapter) => (
                  <List.Item key={chapter.chapterId}>
                    {chapter.startSeconds}s: {chapter.title || <LocalizedText source={"untitled chapter"} />}
                    {chapter.endSeconds !== null &&
                    chapter.endSeconds !== undefined
                      ? <LocalizedText source={"-> {endSeconds}s"} values={{ "endSeconds": (chapter.endSeconds) }} />
                      : ''}
                  </List.Item>
                ))}
              </List>
            </>
          ) : null}

          {run.forensicMatrix ? (
            <details style={detailStyle}>
              <summary style={detailSummaryStyle}><LocalizedText source={"Forensic Matrix"} /></summary>
              <div style={{ marginBottom: '1em' }}>
                <Popup
                  content={interfaceText("Copy the complete forensic matrix JSON for this SongID run without changing ranking, downloads, or local files.")}
                  position="top left"
                  trigger={
                    <Button
                      aria-label={interfaceText("Copy SongID forensic matrix JSON")}
                      icon="copy"
                      onClick={copyForensicMatrix}
                      size="mini"
                     {...interfaceTextProps("Copy SongID forensic matrix JSON")}/>
                  }
                 {...interfaceTextProps("Copy the complete forensic matrix JSON for this SongID run without changing ranking, downloads, or local files.")}/>
              </div>
              <div style={{ marginBottom: '1em' }}>
                <Label size="tiny"><LocalizedText source={"Identity"} />{" "}{run.forensicMatrix.identityScore || 0}</Label>
                <Label size="tiny">
                  <LocalizedText source={"Synthetic"} />{" "}{run.forensicMatrix.syntheticScore || 0}
                </Label>
                <Label size="tiny">
                  <LocalizedText source={"Confidence"} />{" "}{run.forensicMatrix.confidenceScore || 0}
                </Label>
                <Label size="tiny">
                  <LocalizedText source={"Family Score"} />{" "}{run.forensicMatrix.knownFamilyScore || 0}
                </Label>
              </div>
              <div style={{ marginBottom: '1em' }}>
                {run.forensicMatrix.identityLane ? (
                  <Popup
                    content={run.forensicMatrix.identityLane.summary}
                    position="top left"
                    trigger={
                      <Label size="tiny">
                        <LocalizedText source={"Identity Lane"} />{" "}{Math.round((run.forensicMatrix.identityLane.score || 0) * 100)}
                      </Label>
                    }
                  />
                ) : null}
                {run.forensicMatrix.confidenceLane ? (
                  <Popup
                    content={run.forensicMatrix.confidenceLane.summary}
                    position="top left"
                    trigger={
                      <Label size="tiny">
                        <LocalizedText source={"Confidence Lane"} />{" "}{Math.round((run.forensicMatrix.confidenceLane.score || 0) * 100)}
                      </Label>
                    }
                  />
                ) : null}
                {run.forensicMatrix.spectralArtifactLane ? (
                  <Popup
                    content={run.forensicMatrix.spectralArtifactLane.summary}
                    position="top left"
                    trigger={
                      <Label size="tiny">
                        <LocalizedText source={"Spectral"} />{" "}{Math.round((run.forensicMatrix.spectralArtifactLane.score || 0) * 100)}
                      </Label>
                    }
                  />
                ) : null}
                {run.forensicMatrix.lyricsSpeechLane ? (
                  <Popup
                    content={run.forensicMatrix.lyricsSpeechLane.summary}
                    position="top left"
                    trigger={
                      <Label size="tiny">
                        <LocalizedText source={"Lyrics"} />{" "}{Math.round((run.forensicMatrix.lyricsSpeechLane.score || 0) * 100)}
                      </Label>
                    }
                  />
                ) : null}
                {run.forensicMatrix.structuralLane ? (
                  <Popup
                    content={run.forensicMatrix.structuralLane.summary}
                    position="top left"
                    trigger={
                      <Label size="tiny">
                        <LocalizedText source={"Structure"} />{" "}{Math.round((run.forensicMatrix.structuralLane.score || 0) * 100)}
                      </Label>
                    }
                  />
                ) : null}
                {run.forensicMatrix.provenanceLane ? (
                  <Popup
                    content={run.forensicMatrix.provenanceLane.summary}
                    position="top left"
                    trigger={
                      <Label size="tiny">
                        <LocalizedText source={"Provenance"} />{" "}{Math.round((run.forensicMatrix.provenanceLane.score || 0) * 100)}
                      </Label>
                    }
                  />
                ) : null}
              </div>
              {Array.isArray(run.forensicMatrix.topEvidenceFor) &&
              run.forensicMatrix.topEvidenceFor.length > 0 ? (
                <div style={{ marginBottom: '0.75em' }}>
                  <strong><LocalizedText source={"For:"} /></strong> {run.forensicMatrix.topEvidenceFor.join(' | ')}
                </div>
              ) : null}
              {Array.isArray(run.forensicMatrix.topEvidenceAgainst) &&
              run.forensicMatrix.topEvidenceAgainst.length > 0 ? (
                <div style={{ marginBottom: '0.75em' }}>
                  <strong><LocalizedText source={"Against:"} /></strong>{' '}
                  {run.forensicMatrix.topEvidenceAgainst.join(' | ')}
                </div>
              ) : null}
              {Array.isArray(run.forensicMatrix.notes) &&
              run.forensicMatrix.notes.length > 0 ? (
                <div style={{ marginBottom: '0.75em' }}>
                  <strong><LocalizedText source={"Notes:"} /></strong> {run.forensicMatrix.notes.join(' | ')}
                </div>
              ) : null}
            </details>
          ) : null}

          {plans.length > 0 ? (
            <details style={detailStyle}>
              <summary style={detailSummaryStyle}>
                <LocalizedText source={"Ranked Plans ("} />{plans.length})
              </summary>
              <List divided relaxed>
                {plans.map((plan) => (
                  <List.Item key={plan.planId}>
                    <List.Content floated="right">
                      <Popup
                        content={interfaceText("Run the highest-value SongID action path for this candidate using the current scored plan.")}
                        position="top center"
                        trigger={
                          <Button
                            onClick={() => handlePlanAction(plan)}
                            size="small"
                          >
                            {plan.actionLabel}
                          </Button>
                        }
                       {...interfaceTextProps("Run the highest-value SongID action path for this candidate using the current scored plan.")}/>
                    </List.Content>
                    <List.Content>
                      <List.Header>
                        {plan.title}{' '}
                        {plan.duplicateCount > 1 ? (
                          <Label color="grey" size="tiny">
                            {plan.duplicateCount} <LocalizedText source={"matches"} /></Label>
                        ) : null}
                      </List.Header>
                      <List.Description>{plan.subtitle}</List.Description>
                      {renderScores(plan)}
                    </List.Content>
                  </List.Item>
                ))}
              </List>
            </details>
          ) : null}

          {tracks.length > 0 ? (
            <>
              <Header as="h5"><LocalizedText source={"Tracks"} /></Header>
              <List divided relaxed>
                {tracks.map((candidate) => (
                  <List.Item key={candidate.candidateId}>
                    <List.Content floated="right">
                      <Popup
                        content={interfaceText("Start a regular slskdN search using this SongID track candidate so you can inspect sources and begin downloading.")}
                        position="top center"
                        trigger={
                          <Button
                            onClick={() => handleTrackSearch(candidate)}
                            size="small"
                          >
                            <LocalizedText source={"Search Song"} /></Button>
                        }
                       {...interfaceTextProps("Start a regular slskdN search using this SongID track candidate so you can inspect sources and begin downloading.")}/>
                      <Popup
                        content={interfaceText("Open the Discovery Graph around this track candidate and explore nearby identities, ambiguity branches, and adjacent context.")}
                        position="top center"
                        trigger={
                          <Button
                            onClick={() =>
                              openDiscoveryGraph({
                                scope: 'track',
                                songIdRunId: run?.id,
                                recordingId: candidate.recordingId,
                                title: candidate.title,
                                artist: candidate.artist,
                              })
                            }
                            size="small"
                            style={{ marginLeft: '0.5em' }}
                          >
                            <LocalizedText source={"Graph"} /></Button>
                        }
                       {...interfaceTextProps("Open the Discovery Graph around this track candidate and explore nearby identities, ambiguity branches, and adjacent context.")}/>
                    </List.Content>
                    <List.Content>
                      <List.Header>
                        {candidate.artist} - {candidate.title}{' '}
                        {candidate.isExact ? (
                          <Label color="green" size="tiny">
                            <LocalizedText source={"exact"} /></Label>
                        ) : null}
                        {candidate.duplicateCount > 1 ? (
                          <Label color="grey" size="tiny">
                            {candidate.duplicateCount} <LocalizedText source={"matches"} /></Label>
                        ) : null}
                      </List.Header>
                      <List.Description>{candidate.recordingId}</List.Description>
                      {candidate.canonicalVariantCount ? (
                        <List.Description style={{ marginTop: '0.35em' }}>
                          <LocalizedText source={"Canonical variants:"} />{" "}{candidate.canonicalVariantCount}
                          {candidate.hasLosslessCanonical ? <LocalizedText source={"· lossless available"} /> : ''}
                        </List.Description>
                      ) : null}
                      {renderScores(candidate)}
                    </List.Content>
                  </List.Item>
                ))}
              </List>
            </>
          ) : null}

          {Array.isArray(run.albums) && run.albums.length > 0 ? (
            <>
              <Header as="h5"><LocalizedText source={"Albums"} /></Header>
              <List divided relaxed>
                {run.albums.map((candidate) => (
                  <List.Item key={candidate.candidateId}>
                    <List.Content floated="right">
                      <Button.Group size="small">
                        <Popup
                          content={interfaceText("Resolve and cache this MusicBrainz release in slskdN so album completion and downstream download workflows can use it.")}
                          position="top center"
                          trigger={
                            <Button onClick={() => handleAlbumPrepare(candidate)}>
                              <LocalizedText source={"Prepare Album"} /></Button>
                          }
                         {...interfaceTextProps("Resolve and cache this MusicBrainz release in slskdN so album completion and downstream download workflows can use it.")}/>
                        <Popup
                          content={interfaceText("Create a single-release job from this SongID album candidate so slskdN can plan album acquisition directly.")}
                          position="top center"
                          trigger={
                            <Button onClick={() => handleMbReleaseJob(candidate)}>
                              <LocalizedText source={"Download Album"} /></Button>
                          }
                         {...interfaceTextProps("Create a single-release job from this SongID album candidate so slskdN can plan album acquisition directly.")}/>
                        <Popup
                          content={interfaceText("Open the Discovery Graph around this album candidate to explore adjacent tracks, artist context, and nearby branches.")}
                          position="top center"
                          trigger={
                            <Button
                              onClick={() =>
                                openDiscoveryGraph({
                                  scope: 'album',
                                  songIdRunId: run?.id,
                                  releaseId: candidate.releaseId,
                                  album: candidate.title,
                                  artist: candidate.artist,
                                })
                              }
                            >
                              <LocalizedText source={"Graph"} /></Button>
                          }
                         {...interfaceTextProps("Open the Discovery Graph around this album candidate to explore adjacent tracks, artist context, and nearby branches.")}/>
                      </Button.Group>
                    </List.Content>
                    <List.Content>
                      <List.Header>
                        {candidate.artist} - {candidate.title}{' '}
                        {candidate.isExact ? (
                          <Label color="green" size="tiny">
                            <LocalizedText source={"exact"} /></Label>
                        ) : null}
                      </List.Header>
                      <List.Description>
                        {candidate.trackCount} <LocalizedText source={"track(s) ·"} />{" "}{candidate.releaseId}
                      </List.Description>
                      {candidate.canonicalSupportCount ? (
                        <List.Description style={{ marginTop: '0.35em' }}>
                          <LocalizedText source={"Canonical support from"} />{" "}{candidate.canonicalSupportCount} <LocalizedText source={"track candidate(s)"} /></List.Description>
                      ) : null}
                      {renderScores(candidate)}
                    </List.Content>
                  </List.Item>
                ))}
              </List>
            </>
          ) : null}

          {Array.isArray(run.artists) && run.artists.length > 0 ? (
            <>
              <Header as="h5"><LocalizedText source={"Artists"} /></Header>
              <List divided relaxed>
                {run.artists.map((candidate) => (
                  <List.Item key={candidate.candidateId}>
                    <List.Content floated="right">
                      <Popup
                        content={interfaceText("Create a discography job from this SongID artist candidate so slskdN can plan a catalog-scale acquisition workflow.")}
                        position="top center"
                        trigger={
                          <Button
                            onClick={() => handleDiscography(candidate)}
                            size="small"
                          >
                            <LocalizedText source={"Plan Discography"} /></Button>
                        }
                       {...interfaceTextProps("Create a discography job from this SongID artist candidate so slskdN can plan a catalog-scale acquisition workflow.")}/>
                      <Popup
                        content={interfaceText("Open the Discovery Graph around this artist candidate and branch into nearby artists, releases, and SongID context.")}
                        position="top center"
                        trigger={
                          <Button
                            onClick={() =>
                              openDiscoveryGraph({
                                scope: 'artist',
                                songIdRunId: run?.id,
                                artistId: candidate.artistId,
                                artist: candidate.name,
                              })
                            }
                            size="small"
                            style={{ marginLeft: '0.5em' }}
                          >
                            <LocalizedText source={"Graph"} /></Button>
                        }
                       {...interfaceTextProps("Open the Discovery Graph around this artist candidate and branch into nearby artists, releases, and SongID context.")}/>
                    </List.Content>
                    <List.Content>
                      <List.Header>{candidate.name}</List.Header>
                      <List.Description>
                        {candidate.releaseGroupCount} <LocalizedText source={"release group(s) ·"} />{' '}
                        {candidate.artistId}
                      </List.Description>
                      {candidate.canonicalSupportCount ? (
                        <List.Description style={{ marginTop: '0.35em' }}>
                          <LocalizedText source={"Canonical support from"} />{" "}{candidate.canonicalSupportCount} <LocalizedText source={"track candidate(s)"} /></List.Description>
                      ) : null}
                      {renderScores(candidate)}
                    </List.Content>
                  </List.Item>
                ))}
              </List>
            </>
          ) : null}
        </Segment>
      ) : null}
        </Grid.Column>
      </Grid>
    </Segment>
    <DiscoveryGraphModal
      graph={graphData}
      loading={graphLoading}
      onCompare={handleGraphCompare}
      onClose={() => setGraphOpen(false)}
      onQueueNearby={handleQueueNearbyFromGraph}
      onRecenter={handleGraphRecenter}
      onRestoreBranch={(branch) => branch?.request && openDiscoveryGraph(branch.request)}
      open={graphOpen}
    />
    </>
  );
};

export default SongIDPanel;
