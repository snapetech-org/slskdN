import {
  buildDiscoveryGraphBranchPlan,
  formatDiscoveryGraphBranchReport,
  fromQueryString,
  getDiscoveryGraphEdges,
  getDiscoveryGraphNodes,
  getVisibleDiscoveryGraph,
  parseSavedDiscoveryGraphBranches,
  toQueryString,
} from './discoveryGraph';

const graph = {
  edges: [
    {
      edgeType: 'metadata_similarity',
      reason: 'same artist and album neighborhood',
      sourceNodeId: 'track:center',
      targetNodeId: 'track:near',
      weight: 0.9,
    },
    {
      edgeType: 'taste_overlap',
      reason: 'trusted listeners overlap',
      sourceNodeId: 'track:center',
      targetNodeId: 'artist:far',
      weight: 0.6,
    },
    {
      edgeType: 'identity_linkage',
      reason: 'canonical recording bridge',
      sourceNodeId: 'track:center',
      targetNodeId: 'track:weak',
      weight: 0.4,
    },
  ],
  nodes: [
    {
      depth: 0,
      label: 'Center Track',
      nodeId: 'track:center',
      nodeType: 'track',
      weight: 1,
    },
    {
      depth: 1,
      label: 'Nearby Track',
      nodeId: 'track:near',
      nodeType: 'track',
      weight: 0.82,
    },
    {
      depth: 2,
      label: 'Far Artist',
      nodeId: 'artist:far',
      nodeType: 'artist',
      weight: 0.55,
    },
    {
      depth: 1,
      label: 'Weak Track',
      nodeId: 'track:weak',
      nodeType: 'track',
      weight: 0.12,
    },
  ],
  seedNodeId: 'track:center',
  summary: 'Fixture branch',
  title: 'Fixture Graph',
  evidenceSummary: [
    {
      count: 2,
      label: 'Identity',
      lane: 'identity',
      score: 0.85,
      summary: 'Identity appears on 2 graph edges.',
    },
  ],
};

describe('discoveryGraph helpers', () => {
  it('round trips atlas route query parameters', () => {
    const query = toQueryString({
      artist: 'Fixture Artist',
      recordingId: 'recording-1',
      scope: 'track',
      title: '',
    });

    expect(query).toContain('artist=Fixture+Artist');
    expect(query).toContain('recordingId=recording-1');
    expect(query).not.toContain('title=');
    expect(fromQueryString(query)).toMatchObject({
      artist: 'Fixture Artist',
      recordingId: 'recording-1',
      scope: 'track',
    });
  });

  it('filters visible graph nodes and edges by semantic controls', () => {
    const visible = getVisibleDiscoveryGraph({
      edgeTypes: ['metadata_similarity'],
      graph,
      maxDepth: 1,
      minNodeWeight: 0.2,
    });

    expect(visible.visibleNodes.map((node) => node.nodeId)).toEqual([
      'track:center',
      'track:near',
    ]);
    expect(visible.visibleEdges).toHaveLength(1);
    expect(visible.edgeTypeCounts).toEqual({ metadata_similarity: 1 });
    expect(visible.nodeTypeCounts).toEqual({ track: 2 });
  });

  it('treats malformed graph node and edge payloads as empty lists', () => {
    expect(getDiscoveryGraphNodes({ nodes: { nodeId: 'bad' } })).toEqual([]);
    expect(getDiscoveryGraphEdges({ edges: { edgeType: 'bad' } })).toEqual([]);
    expect(getVisibleDiscoveryGraph({
      graph: {
        edges: { edgeType: 'bad' },
        nodes: { nodeId: 'bad' },
      },
    })).toMatchObject({
      visibleEdges: [],
      visibleNodes: [],
    });
  });

  it('filters malformed saved branch entries before UI rendering', () => {
    const branches = parseSavedDiscoveryGraphBranches(JSON.stringify([
      null,
      'bad',
      ['bad'],
      { id: 'missing-title' },
      { id: 'branch-1', request: { scope: 'track' }, title: 'Valid Branch' },
    ]));

    expect(branches).toEqual([
      {
        id: 'branch-1',
        request: { scope: 'track' },
        title: 'Valid Branch',
      },
    ]);
  });

  it('builds branch plans with route suggestions and nearby search seeds', () => {
    const plan = buildDiscoveryGraphBranchPlan({
      graph,
      maxDepth: 2,
      minNodeWeight: 0.2,
      pinnedNode: { label: 'Pinned Artist', nodeId: 'artist:pinned' },
    });

    expect(plan.graphTitle).toBe('Fixture Graph');
    expect(plan.visibleNodeCount).toBe(3);
    expect(plan.routeSuggestions[0].target.label).toBe('Nearby Track');
    expect(plan.searchQueries).toEqual(['Center Track', 'Nearby Track']);
    expect(plan.evidenceSummary).toEqual(graph.evidenceSummary);
  });

  it('formats copyable branch reports', () => {
    const report = formatDiscoveryGraphBranchReport(
      buildDiscoveryGraphBranchPlan({
        graph,
        maxDepth: 2,
        minNodeWeight: 0.2,
        pinnedNode: { label: 'Pinned Artist', nodeId: 'artist:pinned' },
      }),
    );

    expect(report).toContain('slskdN Discovery Graph branch review');
    expect(report).toContain('Graph: Fixture Graph');
    expect(report).toContain('Pinned comparison: Pinned Artist');
    expect(report).toContain('- Artist: 1');
    expect(report).toContain('- metadata_similarity: 1');
    expect(report).toContain('Evidence lanes:');
    expect(report).toContain('- Identity: 85 (2) Identity appears on 2 graph edges.');
    expect(report).toContain('Center Track -> Nearby Track');
    expect(report).toContain('- Nearby Track');
  });

  it('formats malformed count maps as empty count sections', () => {
    const report = formatDiscoveryGraphBranchReport({
      activeEdgeTypes: [],
      edgeTypeCounts: [],
      evidenceSummary: [],
      graphTitle: 'Malformed Counts',
      maxDepth: 2,
      minNodeWeight: 0.2,
      nodeTypeCounts: 'bad',
      pinnedNode: null,
      routeSuggestions: [],
      searchQueries: [],
      seedNodeId: '',
      visibleEdgeCount: 0,
      visibleNodeCount: 0,
    });

    expect(report.match(/- none visible/g)).toHaveLength(2);
  });
});
