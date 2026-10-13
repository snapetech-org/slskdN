import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps } from "../../lib/interfaceLocale";
import React from 'react';
import { Header, Label, Segment } from 'semantic-ui-react';
import DiscoveryGraphCanvas from './DiscoveryGraphCanvas';
import {
  getDiscoveryGraphEdges,
  getDiscoveryGraphNodes,
} from '../../lib/discoveryGraph';

const DiscoveryGraphAtlas = ({
  edgeTypes = [],
  graph,
  maxDepth = 99,
  minNodeWeight = 0,
  onNodeClick,
}) => {
  const nodes = getDiscoveryGraphNodes(graph);
  const visibleNodes = nodes.filter(
    (node) => (node.depth || 0) <= maxDepth && (node.weight || 0) >= minNodeWeight,
  );
  const visibleNodeIds = new Set(visibleNodes.map((node) => node.nodeId));
  const visibleEdges = getDiscoveryGraphEdges(graph).filter(
    (edge) =>
      visibleNodeIds.has(edge.sourceNodeId) &&
      visibleNodeIds.has(edge.targetNodeId) &&
      (edgeTypes.length === 0 || edgeTypes.includes(edge.edgeType)),
  );
  const sparse = visibleNodes.length <= 1 || visibleEdges.length === 0;

  const typeCounts = visibleNodes.reduce((accumulator, node) => {
    accumulator[node.nodeType] = (accumulator[node.nodeType] || 0) + 1;
    return accumulator;
  }, {});

  return (
    <Segment
      className="discovery-graph-atlas-card"
      secondary
    >
      <Header as="h5" style={{ marginTop: 0 }}>
        <LocalizedText source={"Atlas"} /></Header>
      <p style={{ marginTop: 0 }}>
        <LocalizedText source={"Wider neighborhood view with semantic filtering. Raise the threshold to suppress weak nodes and lower depth to stay at artist or album scale."} /></p>
      <div style={{ marginBottom: '0.75em' }}>
        {Object.entries(typeCounts).map(([type, count]) => (
          <Label key={type} size="tiny">
            {type} {count}
          </Label>
        ))}
        <Label size="tiny"><LocalizedText source={"Edges"} />{" "}{visibleEdges.length}</Label>
      </div>
      {sparse ? (
        <p className="discovery-graph-sparse-note">
          <LocalizedText source={"This seed has no visible neighbors at the current depth and weight. Lower the weight threshold, broaden the seed, or open a SongID run with candidate tracks to expand the atlas."} /></p>
      ) : null}
      <div
        className={`discovery-graph-canvas-shell ${sparse ? 'sparse' : ''}`}
      >
        <DiscoveryGraphCanvas
          edgeTypes={edgeTypes}
          graph={{
            ...graph,
            edges: visibleEdges,
            nodes: visibleNodes,
          }}
          height={sparse ? 280 : 440}
          onNodeClick={onNodeClick}
        />
      </div>
    </Segment>
  );
};

export default DiscoveryGraphAtlas;
