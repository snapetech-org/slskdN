import {
  buildPlayerRadioDiscoveryItems,
  buildPlayerRadioPlan,
  buildPlayerRadioSearchPath,
  getPlayerRadioQueries,
  getPlayerRadioCopyText,
  getPlayerRadioReasonSource,
} from './playerRadio';

describe('playerRadio', () => {
  it('builds smart radio searches from now-playing metadata', () => {
    const plan = buildPlayerRadioPlan({
      album: 'Fixture Album',
      artist: 'Fixture Artist',
      genre: 'Fixture Genre',
      title: 'Fixture Track',
    });

    expect(plan.ready).toBe(true);
    expect(plan.seedLabel).toBe('Fixture Artist - Fixture Track');
    expect(plan.queries).toEqual([
      {
        id: 'radio-query-1',
        query: 'Fixture Artist Fixture Track',
        reason: 'Similar track seed',
      },
      {
        id: 'radio-query-2',
        query: 'Fixture Artist Fixture Album',
        reason: 'Album neighborhood',
      },
      {
        id: 'radio-query-3',
        query: 'Fixture Artist Fixture Genre',
        reason: 'Artist and genre seed',
      },
      {
        id: 'radio-query-4',
        query: 'Fixture Artist',
        reason: 'Artist radio seed',
      },
    ]);
  });

  it('falls back to available metadata without creating empty queries', () => {
    const plan = buildPlayerRadioPlan({
      fileName: 'Loose Fixture.ogg',
    });

    expect(plan.ready).toBe(true);
    expect(plan.primaryQuery).toBe('Loose Fixture.ogg');
    expect(plan.queries).toHaveLength(1);
  });

  it('uses scalar genre when normalized tags are empty', () => {
    const plan = buildPlayerRadioPlan({
      artist: 'Fixture Artist',
      genre: 'Fixture Genre',
      tags: [],
      title: 'Fixture Track',
    });

    expect(plan.queries.map((item) => item.query)).toContain(
      'Fixture Artist Fixture Genre',
    );
  });

  it('formats explicit search paths and copy text', () => {
    const plan = buildPlayerRadioPlan({
      artist: 'Fixture Artist',
      title: 'Fixture Track',
    });

    expect(buildPlayerRadioSearchPath(plan.primaryQuery)).toBe(
      '/searches?q=Fixture%20Artist%20Fixture%20Track',
    );
    expect(getPlayerRadioCopyText(plan)).toContain(
      'Similar track seed: "Fixture Artist Fixture Track"',
    );
    expect(getPlayerRadioQueries(plan, { limit: 2 })).toEqual([
      'Fixture Artist Fixture Track',
      'Fixture Artist',
    ]);
    expect(buildPlayerRadioDiscoveryItems(plan)).toEqual([
      expect.objectContaining({
        acquisitionProfile: 'mesh-preferred',
        evidenceKey: 'smart-radio:similar track seed:fixture artist fixture track',
        searchText: 'Fixture Artist Fixture Track',
        source: 'Smart Radio',
      }),
      expect.objectContaining({
        searchText: 'Fixture Artist',
      }),
    ]);
  });

  it('maps generated reason labels through fixed catalog sources and preserves unknown values', () => {
    const reasons = [
      'Similar track seed',
      'Album neighborhood',
      'Artist and genre seed',
      'Artist radio seed',
    ];

    expect(reasons.map(getPlayerRadioReasonSource)).toEqual(reasons);
    expect(getPlayerRadioReasonSource('adapter supplied reason')).toBe(
      'adapter supplied reason',
    );
    expect(getPlayerRadioCopyText({
      queries: [{ query: 'Fixture Query', reason: 'adapter supplied reason' }],
      ready: true,
      seedLabel: 'Fixture Seed',
    })).toContain('adapter supplied reason: "Fixture Query"');
  });

  it('localizes the reachable untitled seed for album-only metadata', () => {
    const plan = buildPlayerRadioPlan({ album: 'Fixture Album' });

    expect(plan.ready).toBe(true);
    expect(getPlayerRadioCopyText(plan)).toContain('Smart radio seed: Untitled seed');
  });

  it('ignores malformed persisted radio query lists', () => {
    const plan = {
      primaryQuery: 'Fixture Artist',
      queries: { 0: { query: 'bad' }, length: 1 },
      ready: true,
      seedLabel: 'Fixture Artist',
    };

    expect(getPlayerRadioQueries(plan)).toEqual([]);
    expect(buildPlayerRadioDiscoveryItems(plan)).toEqual([]);
    expect(getPlayerRadioCopyText(plan)).toBe('Smart radio seed: Fixture Artist');
  });

  it('returns an inert plan without a selected track', () => {
    expect(buildPlayerRadioPlan(null)).toEqual({
      basis: [],
      primaryQuery: '',
      queries: [],
      ready: false,
      seedLabel: 'No track selected',
    });
    expect(buildPlayerRadioSearchPath('')).toBe('/searches');
  });
});
