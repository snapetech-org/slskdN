import React from 'react';
import { interfaceText } from '../../lib/interfaceLocale';

const accentColor = (accent) => {
  switch (accent) {
    case 'center':
      return '#0b6e4f';
    case 'segment':
      return '#b95c00';
    case 'release':
      return '#8b3dff';
    case 'neighbor':
      return '#1b6ca8';
    case 'compare':
      return '#a61e4d';
    default:
      return '#555';
  }
};

const nodeRadius = (node) => 20 + Math.round((node.weight || 0) * 12);

const buildLayout = (graph, width, height) => {
  if (!graph || !Array.isArray(graph.nodes) || graph.nodes.length === 0) {
    return [];
  }

  const center = graph.nodes.find((node) => node.nodeId === graph.seedNodeId) || graph.nodes[0];
  const depthOne = graph.nodes.filter((node) => node.nodeId !== center.nodeId && (node.depth || 0) <= 1);
  const depthTwo = graph.nodes.filter((node) => node.nodeId !== center.nodeId && (node.depth || 0) > 1);
  const centerX = width / 2;
  const centerY = height / 2;
  const layout = [
    {
      ...center,
      x: centerX,
      y: centerY,
    },
  ];

  depthOne.forEach((node, index) => {
    const angle = (Math.PI * 2 * index) / Math.max(depthOne.length, 1);
    layout.push({
      ...node,
      x: centerX + Math.cos(angle) * (width * 0.22),
      y: centerY + Math.sin(angle) * (height * 0.28),
    });
  });

  depthTwo.forEach((node, index) => {
    const angle = (Math.PI * 2 * index) / Math.max(depthTwo.length, 1);
    layout.push({
      ...node,
      x: centerX + Math.cos(angle) * (width * 0.34),
      y: centerY + Math.sin(angle) * (height * 0.38),
    });
  });

  return layout;
};

const DiscoveryGraphCanvas = ({
  graph,
  edgeTypes,
  height = 440,
  onNodeClick,
  width = 720,
}) => {
  const layout = buildLayout(graph, width, height);
  const nodeMap = layout.reduce((accumulator, node) => {
    accumulator[node.nodeId] = node;
    return accumulator;
  }, {});
  const activeEdgeTypes = Array.isArray(edgeTypes) && edgeTypes.length > 0 ? edgeTypes : null;
  const visibleEdges = Array.isArray(graph?.edges)
    ? graph.edges.filter((edge) => !activeEdgeTypes || activeEdgeTypes.includes(edge.edgeType))
    : [];

  return (
    <svg height={height} style={{ width: '100%' }} viewBox={`0 0 ${width} ${height}`}>
      {visibleEdges.map((edge) => {
        const source = nodeMap[edge.sourceNodeId];
        const target = nodeMap[edge.targetNodeId];
        if (!source || !target) {
          return null;
        }

        return (
          <line
            key={`${edge.sourceNodeId}-${edge.targetNodeId}-${edge.edgeType}`}
            stroke="#c7d0d9"
            strokeWidth={1 + Math.round((edge.weight || 0) * 3)}
            x1={source.x}
            x2={target.x}
            y1={source.y}
            y2={target.y}
          >
            <title>
              {interfaceText('{source} → {target} · {type}{reason}', {
                source: source.label,
                target: target.label,
                type: edge.edgeType,
                reason: edge.reason ? interfaceText(' · {reason}', { reason: edge.reason }) : '',
              })}
            </title>
          </line>
        );
      })}
      {layout.map((node) => (
        <g
          key={node.nodeId}
          onClick={() => onNodeClick && onNodeClick(node.nodeId)}
          style={onNodeClick ? { cursor: 'pointer' } : undefined}
        >
          <circle
            cx={node.x}
            cy={node.y}
            fill={accentColor(node.accent)}
            opacity={0.9}
            r={nodeRadius(node)}
          />
          <title>
            {interfaceText('{label} · {type} · weight {weight}', {
              label: node.label,
              type: node.nodeType,
              weight: Math.round((node.weight || 0) * 100),
            })}
          </title>
          <text
            fill="#fff"
            fontSize="11"
            textAnchor="middle"
            x={node.x}
            y={node.y + 3}
          >
            {node.label.length > 18 ? `${node.label.slice(0, 16)}..` : node.label}
          </text>
        </g>
      ))}
    </svg>
  );
};

export default DiscoveryGraphCanvas;
