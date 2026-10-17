import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import * as discoveryGraph from '../../lib/discoveryGraph';
import { getLocalStorageItem, setLocalStorageItem } from '../../lib/storage';
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  Divider,
  Header,
  Input,
  Label,
  List,
  Loader,
  Modal,
  Popup,
  Segment,
} from 'semantic-ui-react';
import DiscoveryGraphAtlas from './DiscoveryGraphAtlas';
import DiscoveryGraphCanvas from './DiscoveryGraphCanvas';

const DiscoveryGraphModal = ({
  graph,
  loading,
  onClose,
  onCompare,
  onQueueNearby,
  onRecenter,
  onRestoreBranch,
  open,
}) => {
  useInterfaceLanguage();
  const navigate = useNavigate();
  const [activeEdgeTypes, setActiveEdgeTypes] = useState([]);
  const [atlasMode, setAtlasMode] = useState(false);
  const [maxDepth, setMaxDepth] = useState(2);
  const [minNodeWeight, setMinNodeWeight] = useState(0.25);
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
    setActiveEdgeTypes([]);
    setAtlasMode(false);
    setMaxDepth(2);
    setMinNodeWeight(0.25);
    loadSavedBranches();
  }, [graph?.seedNodeId]);

  const nodes = discoveryGraph.getDiscoveryGraphNodes(graph);
  const nodeMap = nodes.reduce((accumulator, node) => {
    accumulator[node.nodeId] = node;
    return accumulator;
  }, {});
  const availableEdgeTypes = Array.from(
    new Set(discoveryGraph.getDiscoveryGraphEdges(graph).map((edge) => edge.edgeType)),
  ).sort();
  const visibleEdges = discoveryGraph.getDiscoveryGraphEdges(graph).filter(
    (edge) =>
      activeEdgeTypes.length === 0 || activeEdgeTypes.includes(edge.edgeType),
  );
  const visibleNodeIds = new Set(
    nodes
      .filter(
        (node) =>
          (node.depth || 0) <= maxDepth && (node.weight || 0) >= minNodeWeight,
      )
      .map((node) => node.nodeId),
  );
  const semanticEdges = visibleEdges.filter(
    (edge) =>
      visibleNodeIds.has(edge.sourceNodeId) &&
      visibleNodeIds.has(edge.targetNodeId),
  );

  const toggleEdgeType = (edgeType) => {
    setActiveEdgeTypes((current) =>
      current.includes(edgeType)
        ? current.filter((item) => item !== edgeType)
        : [...current, edgeType],
    );
  };

  const handleSaveBranch = () => {
    if (!graph) {
      return;
    }

    const nextBranch = {
      id: `${graph.seedNodeId}-${Date.now()}`,
      savedAt: new Date().toISOString(),
      seedNodeId: graph.seedNodeId,
      title: graph.title,
      request: graph.request || null,
    };
    const nextSavedBranches = [nextBranch, ...savedBranches].slice(0, 12);
    setLocalStorageItem(
      'slskdn.discoveryGraph.savedBranches',
      JSON.stringify(nextSavedBranches),
    );
    setSavedBranches(nextSavedBranches);
  };

  return (
    <Modal closeIcon onClose={onClose} open={open} size="large">
      <Modal.Header><LocalizedText source={"Discovery Graph"} /></Modal.Header>
      <Modal.Content scrolling>
        {loading ? (
          <Loader active inline="centered">
            <LocalizedText source={"Building neighborhood"} /></Loader>
        ) : null}
        {!loading && graph ? (
          <>
            <p style={{ marginTop: 0 }}>
              <strong>{graph.title}</strong>
              <br />
              {graph.summary}
            </p>
            {availableEdgeTypes.length > 0 ? (
              <div style={{ marginBottom: '1em' }}>
                {availableEdgeTypes.map((edgeType) => (
                  <Label
                    as="a"
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
            <div style={{ marginBottom: '1em' }}>
              <Popup
                content={interfaceText("Switch between the compact neighborhood view and a wider atlas-style map with semantic filtering.")}
                position="top center"
                trigger={
                  <Button
                    onClick={() => setAtlasMode((current) => !current)}
                    size="small"
                  >
                    {atlasMode ? <LocalizedText source={"Compact View"} /> : <LocalizedText source={"Atlas View"} />}
                  </Button>
                }
               {...interfaceTextProps("Switch between the compact neighborhood view and a wider atlas-style map with semantic filtering.")}/>
              <Popup
                content={interfaceText("Open this graph in the dedicated atlas page so the neighborhood has its own addressable route and persistent workspace.")}
                position="top center"
                trigger={
                  <Button
                    disabled={!graph?.request}
                    onClick={() => {
                      if (!graph?.request) {
                        return;
                      }

                      const query = discoveryGraph.toQueryString(graph.request);
                      navigate(`/discovery-graph?${query}`);
                    }}
                    size="small"
                    style={{ marginLeft: '0.5em' }}
                  >
                    <LocalizedText source={"Full Atlas"} /></Button>
                }
               {...interfaceTextProps("Open this graph in the dedicated atlas page so the neighborhood has its own addressable route and persistent workspace.")}/>
              <Popup
                content={interfaceText("Pin the current graph center so you can compare another node or reopen this branch later.")}
                position="top center"
                trigger={
                  <Button
                    disabled={!graph?.seedNodeId}
                    onClick={() =>
                      setPinnedNode({
                        label: graph?.title || graph?.seedNodeId,
                        nodeId: graph?.seedNodeId,
                      })
                    }
                    size="small"
                    style={{ marginLeft: '0.5em' }}
                  >
                    <LocalizedText source={"Pin Center"} /></Button>
                }
               {...interfaceTextProps("Pin the current graph center so you can compare another node or reopen this branch later.")}/>
              <Popup
                content={interfaceText("Queue searches for nearby graph nodes with track-like identities so this neighborhood turns directly into acquisition work.")}
                position="top center"
                trigger={
                  <Button
                    disabled={!onQueueNearby || nodes.length === 0}
                    onClick={() => onQueueNearby && onQueueNearby(graph)}
                    size="small"
                    style={{ marginLeft: '0.5em' }}
                  >
                    <LocalizedText source={"Queue Nearby"} /></Button>
                }
               {...interfaceTextProps("Queue searches for nearby graph nodes with track-like identities so this neighborhood turns directly into acquisition work.")}/>
              <Popup
                content={interfaceText("Save this current branch in the browser so you can reopen the same discovery path later.")}
                position="top center"
                trigger={
                  <Button onClick={handleSaveBranch} size="small" style={{ marginLeft: '0.5em' }}>
                    <LocalizedText source={"Save Branch"} /></Button>
                }
               {...interfaceTextProps("Save this current branch in the browser so you can reopen the same discovery path later.")}/>
              <Popup
                content={interfaceText("Compare the current graph center with the pinned node by adding an explicit comparison bridge.")}
                position="top center"
                trigger={
                  <Button
                    disabled={!pinnedNode || pinnedNode.nodeId === graph?.seedNodeId}
                    onClick={() =>
                      onCompare &&
                      pinnedNode &&
                      onCompare(pinnedNode.nodeId, pinnedNode.label)
                    }
                    size="small"
                    style={{ marginLeft: '0.5em' }}
                  >
                    <LocalizedText source={"Compare Pinned"} /></Button>
                }
               {...interfaceTextProps("Compare the current graph center with the pinned node by adding an explicit comparison bridge.")}/>
            </div>
            {pinnedNode ? (
              <div style={{ marginBottom: '1em' }}>
                <Label color="pink" size="tiny">
                  <LocalizedText source={"Pinned"} />{" "}{pinnedNode.label}
                </Label>
              </div>
            ) : null}
            {atlasMode ? (
              <>
                <Segment secondary>
                  <Header as="h5" style={{ marginTop: 0 }}>
                    <LocalizedText source={"Semantic Zoom"} /></Header>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75em' }}>
                    <div>
                      <div style={{ fontSize: '0.85em', marginBottom: '0.35em' }}>
                        <LocalizedText source={"Max depth"} /></div>
                      <Input
                        min={0}
                        onChange={(_event, { value }) =>
                          setMaxDepth(Number.parseInt(value || '0', 10) || 0)
                        }
                        step={1}
                        type="range"
                        value={maxDepth}
                      />
                      <Label size="tiny">{maxDepth}</Label>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.85em', marginBottom: '0.35em' }}>
                        <LocalizedText source={"Min weight"} /></div>
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
                      <Label size="tiny">
                        {Math.round((minNodeWeight || 0) * 100)}
                      </Label>
                    </div>
                  </div>
                </Segment>
                <DiscoveryGraphAtlas
                  edgeTypes={activeEdgeTypes}
                  graph={graph}
                  maxDepth={maxDepth}
                  minNodeWeight={minNodeWeight}
                  onNodeClick={onRecenter}
                />
              </>
            ) : (
              <Segment secondary>
                <DiscoveryGraphCanvas
                  edgeTypes={activeEdgeTypes}
                  graph={graph}
                  onNodeClick={onRecenter}
                />
              </Segment>
            )}
            <div style={{ marginBottom: '1em' }}>
              {nodes.map((node) => (
                <Label key={node.nodeId} size="tiny">
                  {node.nodeType} {Math.round((node.weight || 0) * 100)}
                </Label>
              ))}
            </div>
            <Header as="h5"><LocalizedText source={"Why These Nodes Are Near"} /></Header>
            <List divided relaxed>
              {semanticEdges.slice(0, atlasMode ? 24 : 16).map((edge) => (
                <List.Item
                  key={`${edge.sourceNodeId}-${edge.targetNodeId}-${edge.edgeType}`}
                >
                  <List.Content floated="right">
                    <Popup
                      content={interfaceText("Recenter the graph on this destination node and rebuild the visible neighborhood from there.")}
                      position="top center"
                      trigger={
                        <Button
                          onClick={() => onRecenter(edge.targetNodeId)}
                          size="mini"
                        >
                          <LocalizedText source={"Recenter"} /></Button>
                      }
                     {...interfaceTextProps("Recenter the graph on this destination node and rebuild the visible neighborhood from there.")}/>
                    <Popup
                      content={interfaceText("Pin this node so you can compare it against another branch or keep it handy while exploring.")}
                      position="top center"
                      trigger={
                        <Button
                          onClick={() =>
                            setPinnedNode({
                              label: nodeMap[edge.targetNodeId]?.label || edge.targetNodeId,
                              nodeId: edge.targetNodeId,
                            })
                          }
                          size="mini"
                          style={{ marginLeft: '0.5em' }}
                        >
                          <LocalizedText source={"Pin"} /></Button>
                      }
                     {...interfaceTextProps("Pin this node so you can compare it against another branch or keep it handy while exploring.")}/>
                    <Popup
                      content={interfaceText("Add a direct comparison bridge between the current graph center and this node.")}
                      position="top center"
                      trigger={
                        <Button
                          onClick={() =>
                            onCompare &&
                            onCompare(
                              edge.targetNodeId,
                              nodeMap[edge.targetNodeId]?.label || edge.targetNodeId,
                            )
                          }
                          size="mini"
                          style={{ marginLeft: '0.5em' }}
                        >
                          <LocalizedText source={"Compare"} /></Button>
                      }
                     {...interfaceTextProps("Add a direct comparison bridge between the current graph center and this node.")}/>
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
            {savedBranches.length > 0 ? (
              <>
                <Divider />
                <Header as="h5"><LocalizedText source={"Saved Branches"} /></Header>
                <div>
                  {savedBranches.slice(0, 6).map((branch) => (
                    <Popup
                      key={branch.id}
                      content={interfaceText("Reopen this saved discovery branch from the browser-local branch shelf.")}
                      position="top center"
                      trigger={
                        <Label
                          as="a"
                          onClick={() =>
                            onRestoreBranch
                              ? onRestoreBranch(branch)
                              : branch.request && onRecenter(branch.seedNodeId)
                          }
                          size="tiny"
                        >
                          {branch.title}
                        </Label>
                      }
                     {...interfaceTextProps("Reopen this saved discovery branch from the browser-local branch shelf.")}/>
                  ))}
                </div>
              </>
            ) : null}
          </>
        ) : null}
      </Modal.Content>
    </Modal>
  );
};

export default DiscoveryGraphModal;
