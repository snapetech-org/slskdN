import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import * as discoveryGraph from '../../lib/discoveryGraph';
import * as searches from '../../lib/searches';
import { getLocalStorageItem } from '../../lib/storage';
import './Search.css';
import DiscoveryGraphAtlas from './DiscoveryGraphAtlas';
import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import {
  Button,
  Dropdown,
  Form,
  Header,
  Input,
  Label,
  List,
  Popup,
  Segment,
} from 'semantic-ui-react';

const scopeOptions = [
  { key: 'songid_run', get text() { return interfaceText("Song / Unknown Seed"); }, value: 'songid_run' },
  { key: 'track', get text() { return interfaceText("Track"); }, value: 'track' },
  { key: 'album', get text() { return interfaceText("Album"); }, value: 'album' },
  { key: 'artist', get text() { return interfaceText("Artist"); }, value: 'artist' },
];

const DiscoveryGraphAtlasPanel = ({ disabled, persistRoute = false }) => {
  useInterfaceLanguage();
  const location = useLocation();
  const navigate = useNavigate();
  const [scope, setScope] = useState('songid_run');
  const [artist, setArtist] = useState('');
  const [album, setAlbum] = useState('');
  const [title, setTitle] = useState('');
  const [artistId, setArtistId] = useState('');
  const [releaseId, setReleaseId] = useState('');
  const [recordingId, setRecordingId] = useState('');
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(false);
  const [maxDepth, setMaxDepth] = useState(2);
  const [minNodeWeight, setMinNodeWeight] = useState(0.2);
  const [activeEdgeTypes, setActiveEdgeTypes] = useState([]);
  const [pinnedNode, setPinnedNode] = useState(null);
  const [savedBranches, setSavedBranches] = useState([]);

  const loadSavedBranches = () => {
    try {
      const raw = getLocalStorageItem('slskdn.discoveryGraph.savedBranches');
      setSavedBranches(discoveryGraph.parseSavedDiscoveryGraphBranches(raw));
    } catch (error) {
      console.warn('Failed to load saved Discovery Graph branches', error);
      setSavedBranches([]);
    }
  };

  useEffect(() => {
    loadSavedBranches();
  }, []);

  useEffect(() => {
    if (!persistRoute) {
      return;
    }

    const request = discoveryGraph.fromQueryString(location.search);
    setScope(request.scope || 'songid_run');
    setArtist(request.artist || '');
    setAlbum(request.album || '');
    setTitle(request.title || '');
    setArtistId(request.artistId || '');
    setReleaseId(request.releaseId || '');
    setRecordingId(request.recordingId || '');

    const hasSeed =
      request.artist ||
      request.album ||
      request.title ||
      request.artistId ||
      request.releaseId ||
      request.recordingId ||
      request.songIdRunId;

    if (hasSeed) {
      openGraph(request);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [persistRoute, location.search]);

  const buildRequest = () => ({
    album: album.trim() || undefined,
    artist: artist.trim() || undefined,
    artistId: artistId.trim() || undefined,
    recordingId: recordingId.trim() || undefined,
    releaseId: releaseId.trim() || undefined,
    scope,
    title: title.trim() || undefined,
  });

  const openGraph = async (request) => {
    setLoading(true);

    try {
      const nextGraph = await discoveryGraph.buildDiscoveryGraph(request);
      setGraph(nextGraph);
      setActiveEdgeTypes([]);
      if (persistRoute) {
        const query = discoveryGraph.toQueryString(request);
        navigate({
          pathname: location.pathname,
          search: query ? `?${query}` : '',
        }, { replace: true });
      }
    } catch (error) {
      console.error(error);
      toast.error(getApiErrorMessage(error, { t: interfaceText }, 'Failed to build discovery graph'));
    } finally {
      setLoading(false);
    }
  };

  const handleBuild = async () => {
    await openGraph(buildRequest());
  };

  const handleRecenter = async (nodeId) => {
    if (!nodeId) {
      return;
    }

    const [nodeType, rawId] = nodeId.split(':');
    if (nodeType === 'artist') {
      await openGraph({ scope: 'artist', artistId: rawId });
      return;
    }

    if (nodeType === 'album' || nodeType === 'release-group') {
      await openGraph({ scope: 'album', releaseId: rawId });
      return;
    }

    if (nodeType === 'track') {
      await openGraph({ scope: 'track', recordingId: rawId });
      return;
    }

    await handleBuild();
  };

  const toggleEdgeType = (edgeType) => {
    setActiveEdgeTypes((current) =>
      current.includes(edgeType)
        ? current.filter((item) => item !== edgeType)
        : [...current, edgeType],
    );
  };

  const handleQueueNearby = async () => {
    const queries = discoveryGraph.buildDiscoveryGraphBranchPlan({
      edgeTypes: activeEdgeTypes,
      graph,
      maxDepth,
      minNodeWeight,
      pinnedNode,
    }).searchQueries;

    if (queries.length === 0) {
      toast.error(interfaceText("No nearby track nodes were available to queue"));
      return;
    }

    try {
      const count = await searches.createBatch({ queries });
      toast.success(interfaceText("Started {count} nearby atlas searches", { "count": (count) }));
    } catch (error) {
      console.error(error);
      toast.error(getApiErrorMessage(error, { t: interfaceText }));
    }
  };

  const copyBranchReport = async () => {
    const plan = discoveryGraph.buildDiscoveryGraphBranchPlan({
      edgeTypes: activeEdgeTypes,
      graph,
      maxDepth,
      minNodeWeight,
      pinnedNode,
    });
    const report = discoveryGraph.formatDiscoveryGraphBranchReport(plan);

    try {
      await navigator.clipboard.writeText(report);
      toast.success(interfaceText("Discovery Graph branch report copied"));
    } catch (error) {
      console.error(error);
      toast.error(interfaceText("Unable to copy Discovery Graph branch report"));
    }
  };

  const nodes = discoveryGraph.getDiscoveryGraphNodes(graph);
  const nodeMap = nodes.reduce((accumulator, node) => {
    accumulator[node.nodeId] = node;
    return accumulator;
  }, {});
  const availableEdgeTypes = Array.from(
    new Set(discoveryGraph.getDiscoveryGraphEdges(graph).map((edge) => edge.edgeType)),
  ).sort();
  const visibleGraph = discoveryGraph.getVisibleDiscoveryGraph({
    edgeTypes: activeEdgeTypes,
    graph,
    maxDepth,
    minNodeWeight,
  });
  const visibleEdges = visibleGraph.visibleEdges;
  const branchPlan = discoveryGraph.buildDiscoveryGraphBranchPlan({
    edgeTypes: activeEdgeTypes,
    graph,
    maxDepth,
    minNodeWeight,
    pinnedNode,
  });
  const edgeTypeSummary = Object.entries(branchPlan.edgeTypeCounts);

  return (
    <Segment
      className="discovery-graph-atlas-panel"
      raised
    >
      <Header as="h4"><LocalizedText source={"Discovery Graph Atlas"} /></Header>
      <p style={{ marginTop: 0 }}>
        <LocalizedText source={"Persistent graph surface for wandering the neighborhood around a seed without opening a modal. Use manual seeds, canonical ids, or saved branches to keep exploration in the page flow."} /></p>
      <Form className="discovery-graph-seed-form">
        <Form.Field>
          <label><LocalizedText source={"Seed Scope"} /></label>
          <Dropdown
            disabled={disabled || loading}
            fluid
            onChange={(_event, { value }) => setScope(value)}
            options={scopeOptions}
            selection
            value={scope}
          />
        </Form.Field>
        <Form.Group widths="equal">
          <Form.Field>
            <Input
              disabled={disabled || loading}
              label={interfaceText("Artist")}
              onChange={(event) => setArtist(event.target.value)}
              placeholder={interfaceText("Artist name")}
              value={artist}
             {...interfaceTextProps("Artist")}/>
          </Form.Field>
          <Form.Field>
            <Input
              disabled={disabled || loading}
              label={interfaceText("Album")}
              onChange={(event) => setAlbum(event.target.value)}
              placeholder={interfaceText("Album title")}
              value={album}
             {...interfaceTextProps("Album")}/>
          </Form.Field>
          <Form.Field>
            <Input
              disabled={disabled || loading}
              label={interfaceText("Title")}
              onChange={(event) => setTitle(event.target.value)}
              placeholder={interfaceText("Track title or seed label")}
              value={title}
             {...interfaceTextProps("Title")}/>
          </Form.Field>
        </Form.Group>
        <Form.Group widths="equal">
          <Form.Field>
            <Input
              disabled={disabled || loading}
              label={interfaceText("Artist MBID")}
              onChange={(event) => setArtistId(event.target.value)}
              placeholder={interfaceText("Optional artist id")}
              value={artistId}
             {...interfaceTextProps("Artist MBID")}/>
          </Form.Field>
          <Form.Field>
            <Input
              disabled={disabled || loading}
              label={interfaceText("Release ID")}
              onChange={(event) => setReleaseId(event.target.value)}
              placeholder={interfaceText("Optional release id")}
              value={releaseId}
             {...interfaceTextProps("Release ID")}/>
          </Form.Field>
          <Form.Field>
            <Input
              disabled={disabled || loading}
              label={interfaceText("Recording ID")}
              onChange={(event) => setRecordingId(event.target.value)}
              placeholder={interfaceText("Optional recording id")}
              value={recordingId}
             {...interfaceTextProps("Recording ID")}/>
          </Form.Field>
        </Form.Group>
        <Popup
          content={interfaceText("Build a persistent atlas in-page from the current seed fields instead of opening a temporary modal.")}
          position="top center"
          trigger={
            <Button
              disabled={disabled || loading}
              loading={loading}
              onClick={handleBuild}
              primary
            >
              <LocalizedText source={"Build Atlas"} /></Button>
          }
         {...interfaceTextProps("Build a persistent atlas in-page from the current seed fields instead of opening a temporary modal.")}/>
        <Popup
          content={interfaceText("Queue nearby track nodes from the current atlas into regular searches so exploration turns into acquisition work.")}
          position="top center"
          trigger={
            <Button
              disabled={!graph}
              onClick={handleQueueNearby}
              style={{ marginLeft: '0.5em' }}
            >
              <LocalizedText source={"Queue Nearby"} /></Button>
          }
         {...interfaceTextProps("Queue nearby track nodes from the current atlas into regular searches so exploration turns into acquisition work.")}/>
        <Popup
          content={interfaceText("Copy a branch review report with visible node families, edge families, suggested routes, and nearby search seeds.")}
          position="top center"
          trigger={
            <Button
              aria-label={interfaceText("Copy Discovery Graph branch report")}
              disabled={!graph}
              icon="copy"
              onClick={copyBranchReport}
              style={{ marginLeft: '0.5em' }}
             {...interfaceTextProps("Copy Discovery Graph branch report")}/>
          }
         {...interfaceTextProps("Copy a branch review report with visible node families, edge families, suggested routes, and nearby search seeds.")}/>
      </Form>
      <div className="discovery-graph-controls">
        <label className="discovery-graph-range">
          <span><LocalizedText source={"Depth"} />{" "}{maxDepth}</span>
          <Input
            max={4}
            min={0}
            onChange={(_event, { value }) =>
              setMaxDepth(Number.parseInt(value || '0', 10) || 0)
            }
            step={1}
            type="range"
            value={maxDepth}
          />
        </label>
        <label className="discovery-graph-range">
          <span><LocalizedText source={"Weight"} />{" "}{Math.round((minNodeWeight || 0) * 100)}</span>
          <Input
            max={1}
            min={0}
            onChange={(_event, { value }) =>
              setMinNodeWeight(Number.parseFloat(value || '0') || 0)
            }
            step={0.05}
            type="range"
            value={minNodeWeight}
          />
        </label>
      </div>
      {availableEdgeTypes.length > 0 ? (
        <div className="discovery-graph-edge-filter">
          {availableEdgeTypes.map((edgeType) => (
            <Label
              as="button"
              className="discovery-graph-edge-filter-label"
              color={activeEdgeTypes.includes(edgeType) ? 'blue' : undefined}
              key={edgeType}
              onClick={() => toggleEdgeType(edgeType)}
              size="tiny"
            >
              {edgeType}
            </Label>
          ))}
        </div>
      ) : null}
      {savedBranches.length > 0 ? (
        <div style={{ marginTop: '1em' }}>
          <Header as="h5"><LocalizedText source={"Saved Branches"} /></Header>
          <List horizontal relaxed>
            {savedBranches.slice(0, 6).map((branch) => (
              <List.Item key={branch.id}>
                <Popup
                  content={interfaceText("Restore this saved branch into the atlas panel.")}
                  position="top center"
                  trigger={
                    <Button
                      onClick={() => branch.request && openGraph(branch.request)}
                      size="mini"
                    >
                      {branch.title}
                    </Button>
                  }
                 {...interfaceTextProps("Restore this saved branch into the atlas panel.")}/>
              </List.Item>
            ))}
          </List>
        </div>
      ) : null}
      {graph ? (
        <>
          <Header as="h5" style={{ marginBottom: '0.35em', marginTop: '1em' }}>
            {graph.title}
          </Header>
          <p style={{ marginTop: 0 }}>{graph.summary}</p>
          {pinnedNode ? (
            <div style={{ marginBottom: '0.75em' }}>
              <Label color="pink" size="tiny">
                <LocalizedText source={"Pinned"} />{" "}{pinnedNode.label}
              </Label>
            </div>
          ) : null}
          <div style={{ marginBottom: '0.75em' }}>
            {edgeTypeSummary.map(([edgeType, count]) => (
              <Label key={edgeType} size="tiny">
                {edgeType} {count}
              </Label>
            ))}
          </div>
          <DiscoveryGraphAtlas
            edgeTypes={activeEdgeTypes}
            graph={graph}
            maxDepth={maxDepth}
            minNodeWeight={minNodeWeight}
            onNodeClick={handleRecenter}
          />
          {branchPlan.routeSuggestions.length > 0 ? (
            <>
              <Header as="h5" style={{ marginBottom: '0.35em', marginTop: '1em' }}>
                <LocalizedText source={"Suggested Branch Routes"} /></Header>
              <List divided relaxed>
                {branchPlan.routeSuggestions.slice(0, 5).map((route) => (
                  <List.Item
                    key={`${route.edge.sourceNodeId}-${route.edge.targetNodeId}-${route.edge.edgeType}-route`}
                  >
                    <List.Content floated="right">
                      <Popup
                        content={interfaceText("Pin this route target as the comparison point for the current atlas branch.")}
                        position="top center"
                        trigger={
                          <Button
                            onClick={() =>
                              setPinnedNode({
                                label: route.target.label,
                                nodeId: route.target.nodeId,
                              })
                            }
                            size="mini"
                          >
                            <LocalizedText source={"Pin"} /></Button>
                        }
                       {...interfaceTextProps("Pin this route target as the comparison point for the current atlas branch.")}/>
                      <Popup
                        content={interfaceText("Recenter the atlas on this suggested branch route.")}
                        position="top center"
                        trigger={
                          <Button
                            onClick={() => handleRecenter(route.target.nodeId)}
                            size="mini"
                            style={{ marginLeft: '0.5em' }}
                          >
                            <LocalizedText source={"Recenter"} /></Button>
                        }
                       {...interfaceTextProps("Recenter the atlas on this suggested branch route.")}/>
                    </List.Content>
                    <List.Content>
                      <List.Header>
                        {route.source.label} → {route.target.label}
                      </List.Header>
                      <List.Description>
                        {route.edge.edgeType} <LocalizedText source={"· score"} />{" "}{Math.round(route.score * 100)} ·{' '}
                        {route.edge.reason}
                      </List.Description>
                    </List.Content>
                  </List.Item>
                ))}
              </List>
            </>
          ) : null}
          <Header as="h5" style={{ marginBottom: '0.35em', marginTop: '1em' }}>
            <LocalizedText source={"Why These Nodes Are Near"} /></Header>
          <List divided relaxed>
            {visibleEdges.slice(0, 12).map((edge) => (
              <List.Item
                key={`${edge.sourceNodeId}-${edge.targetNodeId}-${edge.edgeType}`}
              >
                <List.Content floated="right">
                  <Popup
                    content={interfaceText("Recenter the atlas on this destination node so you can keep walking the graph from there.")}
                    position="top center"
                    trigger={
                      <Button
                        onClick={() => handleRecenter(edge.targetNodeId)}
                        size="mini"
                      >
                        <LocalizedText source={"Recenter"} /></Button>
                    }
                   {...interfaceTextProps("Recenter the atlas on this destination node so you can keep walking the graph from there.")}/>
                </List.Content>
                <List.Content>
                  <List.Header>
                    {(nodeMap[edge.sourceNodeId]?.label || edge.sourceNodeId)} →{' '}
                    {(nodeMap[edge.targetNodeId]?.label || edge.targetNodeId)}
                  </List.Header>
                  <List.Description>
                    {edge.edgeType} · {edge.reason}
                    {edge.provenance ? <LocalizedText source={"· {provenance}"} values={{ "provenance": (edge.provenance) }} /> : ''}
                  </List.Description>
                  {edge.scoreComponents &&
                  Object.keys(edge.scoreComponents).length > 0 ? (
                    <List.Description style={{ marginTop: '0.35em' }}>
                      {Object.entries(edge.scoreComponents)
                        .map(
                          ([key, value]) =>
                            `${key} ${Math.round((value || 0) * 100)}`,
                        )
                        .join(' | ')}
                    </List.Description>
                  ) : null}
                  {Array.isArray(edge.evidence) && edge.evidence.length > 0 ? (
                    <List.Description style={{ marginTop: '0.35em' }}>
                      {edge.evidence.join(' | ')}
                    </List.Description>
                  ) : null}
                </List.Content>
              </List.Item>
            ))}
          </List>
        </>
      ) : (
        <Segment
          className="discovery-graph-empty-state"
          placeholder
          secondary
          style={{ marginTop: '1em' }}
        >
          <LocalizedText source={"Build an atlas from a seed above or restore a saved branch."} /></Segment>
      )}
    </Segment>
  );
};

export default DiscoveryGraphAtlasPanel;
