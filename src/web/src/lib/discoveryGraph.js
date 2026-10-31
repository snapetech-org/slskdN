import { interfaceText } from './interfaceLocale';
import api from './api';
import { formatRegionalNumber } from './regionalFormat';
import {
  localizeDiscoveryGraphEdgeType,
  localizeDiscoveryGraphEvidenceLaneLabel,
  localizeDiscoveryGraphEvidenceLaneSummary,
  localizeDiscoveryGraphNodeType,
  localizeDiscoveryGraphReason,
} from './discoveryGraphLocale';

const asObject = (value) =>
  value && typeof value === 'object' && !Array.isArray(value) ? value : {};

export const buildDiscoveryGraph = async (request) => {
  const response = await api.post('/discovery-graph', request);
  return response.data;
};

export const toQueryString = (request = {}) => {
  const parameters = new URLSearchParams();

  Object.entries(request).forEach(([key, value]) => {
    if (value !== undefined && value !== null && `${value}`.trim() !== '') {
      parameters.set(key, value);
    }
  });

  return parameters.toString();
};

export const fromQueryString = (search = '') => {
  const parameters = new URLSearchParams(search.startsWith('?') ? search : `?${search}`);
  return {
    album: parameters.get('album') || undefined,
    artist: parameters.get('artist') || undefined,
    artistId: parameters.get('artistId') || undefined,
    compareLabel: parameters.get('compareLabel') || undefined,
    compareNodeId: parameters.get('compareNodeId') || undefined,
    recordingId: parameters.get('recordingId') || undefined,
    releaseId: parameters.get('releaseId') || undefined,
    scope: parameters.get('scope') || 'songid_run',
    songIdRunId: parameters.get('songIdRunId') || undefined,
    title: parameters.get('title') || undefined,
  };
};

const isSavedBranch = (branch) =>
  branch &&
  typeof branch === 'object' &&
  !Array.isArray(branch) &&
  typeof branch.id === 'string' &&
  branch.id.trim() &&
  typeof branch.title === 'string' &&
  branch.title.trim();

export const parseSavedDiscoveryGraphBranches = (raw) => {
  try {
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed)
      ? parsed.filter(isSavedBranch)
      : [];
  } catch {
    return [];
  }
};

export const getDiscoveryGraphNodes = (graph) =>
  Array.isArray(graph?.nodes) ? graph.nodes : [];

export const getDiscoveryGraphEdges = (graph) =>
  Array.isArray(graph?.edges) ? graph.edges : [];

export const getVisibleDiscoveryGraph = ({
  edgeTypes = [],
  graph,
  maxDepth = 99,
  minNodeWeight = 0,
} = {}) => {
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

  return {
    edgeTypeCounts: summarizeCounts(visibleEdges, 'edgeType'),
    nodeTypeCounts: summarizeCounts(visibleNodes, 'nodeType'),
    visibleEdges,
    visibleNodes,
  };
};

export const buildDiscoveryGraphBranchPlan = ({
  edgeTypes = [],
  graph,
  maxDepth = 99,
  minNodeWeight = 0,
  pinnedNode = null,
} = {}) => {
  const { edgeTypeCounts, nodeTypeCounts, visibleEdges, visibleNodes } =
    getVisibleDiscoveryGraph({
      edgeTypes,
      graph,
      maxDepth,
      minNodeWeight,
    });
  const nodeMap = visibleNodes.reduce((accumulator, node) => {
    accumulator[node.nodeId] = node;
    return accumulator;
  }, {});
  const routeSuggestions = visibleEdges
    .map((edge) => ({
      edge,
      score:
        (edge.weight || 0) +
        ((nodeMap[edge.targetNodeId]?.weight || 0) * 0.5) -
        ((nodeMap[edge.targetNodeId]?.depth || 0) * 0.05),
      source: nodeMap[edge.sourceNodeId],
      target: nodeMap[edge.targetNodeId],
    }))
    .filter((route) => route.source && route.target)
    .sort((left, right) => right.score - left.score)
    .slice(0, 8);
  const searchQueries = visibleNodes
    .filter((node) => node.nodeType === 'track')
    .map((node) => node.label || '')
    .filter(Boolean)
    .slice(0, 10);

  return {
    activeEdgeTypes: edgeTypes,
    edgeTypeCounts,
    evidenceSummary: Array.isArray(graph?.evidenceSummary)
      ? graph.evidenceSummary
      : [],
    graphTitle: graph?.title || 'Discovery Graph',
    maxDepth,
    minNodeWeight,
    nodeTypeCounts,
    pinnedNode,
    routeSuggestions,
    searchQueries,
    seedNodeId: graph?.seedNodeId || '',
    summary: graph?.summary || '',
    visibleEdgeCount: visibleEdges.length,
    visibleNodeCount: visibleNodes.length,
  };
};

export const formatDiscoveryGraphBranchReport = (plan) => {
  const lines = [
    interfaceText("slskdN Discovery Graph branch review"),
    interfaceText('Graph: {graphTitle}', { graphTitle: plan.graphTitle }),
    interfaceText('Seed: {seed}', { seed: plan.seedNodeId || interfaceText('unknown') }),
    interfaceText('Visible nodes: {count}', { count: formatRegionalNumber(plan.visibleNodeCount) }),
    interfaceText('Visible edges: {count}', { count: formatRegionalNumber(plan.visibleEdgeCount) }),
    interfaceText('Depth: {depth}', { depth: formatRegionalNumber(plan.maxDepth) }),
    interfaceText('Minimum weight: {percent}%', {
      percent: formatRegionalNumber(Math.round((plan.minNodeWeight || 0) * 100)),
    }),
  ];

  if (plan.pinnedNode?.nodeId) {
    lines.push(interfaceText('Pinned comparison: {node}', {
      node: plan.pinnedNode.label || plan.pinnedNode.nodeId,
    }));
  }

  lines.push('', interfaceText('Node families:'));
  appendCounts(lines, plan.nodeTypeCounts, localizeDiscoveryGraphNodeType);
  lines.push('', interfaceText('Edge families:'));
  appendCounts(lines, plan.edgeTypeCounts, localizeDiscoveryGraphEdgeType);

  if (plan.routeSuggestions.length > 0) {
    lines.push('', interfaceText('Suggested branch routes:'));
    plan.routeSuggestions.forEach((route) => {
      lines.push(
        interfaceText('- {source} -> {target} [{type}, {weight}] {reason}', {
          source: route.source.label,
          target: route.target.label,
          type: localizeDiscoveryGraphEdgeType(route.edge.edgeType),
          weight: formatRegionalNumber(Math.round((route.edge.weight || 0) * 100)),
          reason: localizeDiscoveryGraphReason(route.edge.reason || ''),
        }).trim(),
      );
    });
  }

  if (plan.evidenceSummary.length > 0) {
    lines.push('', interfaceText('Evidence lanes:'));
    plan.evidenceSummary
      .slice()
      .sort((left, right) => (right.score || 0) - (left.score || 0))
      .forEach((lane) => {
        lines.push(
          interfaceText('- {label}: {score} ({count}) {summary}', {
            label: localizeDiscoveryGraphEvidenceLaneLabel(lane.lane, lane.label),
            score: formatRegionalNumber(Math.round((lane.score || 0) * 100)),
            count: formatRegionalNumber(lane.count || 0),
            summary: localizeDiscoveryGraphEvidenceLaneSummary(lane),
          }).trim(),
        );
      });
  }

  if (plan.searchQueries.length > 0) {
    lines.push('', interfaceText('Nearby search seeds:'));
    plan.searchQueries.forEach((query) => lines.push(`- ${query}`));
  }

  return lines.join('\n');
};

const summarizeCounts = (items, property) =>
  items.reduce((accumulator, item) => {
    const key = item[property] || 'unknown';
    accumulator[key] = (accumulator[key] || 0) + 1;
    return accumulator;
  }, {});

const appendCounts = (lines, counts, localizeKey = (key) => key) => {
  const entries = Object.entries(asObject(counts));
  if (entries.length === 0) {
    lines.push(interfaceText('- none visible'));
    return;
  }

  entries
    .sort(([left], [right]) => left.localeCompare(right))
    .forEach(([key, count]) => lines.push(interfaceText('- {key}: {count}', {
      key: localizeKey(key),
      count: formatRegionalNumber(count),
    })));
};
