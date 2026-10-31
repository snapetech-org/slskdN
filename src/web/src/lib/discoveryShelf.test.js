import {
  clearDiscoveryShelf,
  discoveryShelfStorageKey,
  exportDiscoveryShelfPolicyReport,
  getDiscoveryShelfPromoteItems,
  getDiscoveryShelfAction,
  getDiscoveryShelfPolicyPreview,
  getDiscoveryShelfSummary,
  removeDiscoveryShelfItem,
  upsertDiscoveryShelfItem,
} from './discoveryShelf';

describe('discoveryShelf', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('stores local shelf actions from player ratings', () => {
    upsertDiscoveryShelfItem({
      artist: 'Fixture Artist',
      contentId: 'sha256:fixture',
      sourceProviders: ['local', 'mesh'],
      title: 'Fixture Track',
    }, 5, '2026-04-30T00:00:00.000Z');

    const [item] = JSON.parse(localStorage.getItem(discoveryShelfStorageKey));

    expect(item).toMatchObject({
      action: 'promote-preview',
      artist: 'Fixture Artist',
      key: 'content:sha256:fixture',
      rating: 5,
      reviewedAt: '2026-04-30T00:00:00.000Z',
      title: 'Fixture Track',
    });
  });

  it('summarizes expiry-watch actions using the same key that unrated items store', () => {
    expect(getDiscoveryShelfAction(0)).toBe('expiry-watch');

    upsertDiscoveryShelfItem({
      contentId: 'sha256:unrated',
      title: 'Unrated Track',
    }, 0);

    expect(getDiscoveryShelfSummary()).toMatchObject({
      'expiry-watch': 1,
      total: 1,
    });
  });

  it('removes and clears shelf items', () => {
    upsertDiscoveryShelfItem({
      contentId: 'sha256:remove',
      title: 'Remove Track',
    }, 1);

    removeDiscoveryShelfItem('content:sha256:remove');
    expect(getDiscoveryShelfSummary().total).toBe(0);

    upsertDiscoveryShelfItem({
      contentId: 'sha256:clear',
      title: 'Clear Track',
    }, 3);
    clearDiscoveryShelf();

    expect(getDiscoveryShelfSummary().total).toBe(0);
  });

  it('ignores malformed persisted shelf entries before summarizing', () => {
    localStorage.setItem(
      discoveryShelfStorageKey,
      JSON.stringify([
        null,
        'bad',
        ['bad'],
        {
          action: 'promote-preview',
          key: 'content:valid',
          title: 'Valid Track',
        },
      ]),
    );

    expect(getDiscoveryShelfSummary()).toMatchObject({
      'promote-preview': 1,
      total: 1,
    });
  });

  it('previews promote archive and expiry policy without enabling file actions', () => {
    upsertDiscoveryShelfItem({
      contentId: 'sha256:promote',
      title: 'Promote Track',
    }, 5, '2026-04-30T00:00:00.000Z');
    upsertDiscoveryShelfItem({
      contentId: 'sha256:archive',
      title: 'Archive Track',
    }, 1, '2026-04-30T00:00:00.000Z');
    upsertDiscoveryShelfItem({
      contentId: 'sha256:expire',
      title: 'Expire Track',
    }, 0, '2026-04-01T00:00:00.000Z');
    upsertDiscoveryShelfItem({
      contentId: 'sha256:review',
      title: 'Review Track',
    }, 3, '2026-04-30T00:00:00.000Z');

    expect(getDiscoveryShelfPolicyPreview({
      expiryDays: 14,
      now: '2026-04-30T00:00:00.000Z',
      requireConsensus: true,
    })).toEqual({
      archive: 1,
      blockedByConsensus: 2,
      canApply: false,
      expire: 1,
      expiryDays: 14,
      promote: 1,
      requireConsensus: true,
      review: 1,
    });
  });

  it('exports a copyable policy report for review', () => {
    upsertDiscoveryShelfItem({
      album: 'Fixture Album',
      artist: 'Fixture Artist',
      contentId: 'sha256:report',
      title: 'Report Track',
    }, 5, '2026-04-30T00:00:00.000Z');

    const report = exportDiscoveryShelfPolicyReport({
      now: '2026-04-30T21:20:00.000Z',
      requireConsensus: true,
    });

    expect(report).toContain('Discovery Shelf Policy Preview');
    expect(report).toContain('Promote candidates: 1');
    expect(report).toContain('Consensus required for destructive actions: yes');
    expect(report).toContain('- Promote preview: Report Track\n  Artist: Fixture Artist\n  Album: Fixture Album\n  Rating: 5');
  });

  it('builds bounded Discovery Inbox promote handoffs', () => {
    upsertDiscoveryShelfItem({
      album: 'Fixture Album',
      artist: 'Fixture Artist',
      contentId: 'sha256:promote',
      title: 'Promote Track',
    }, 5, '2026-04-30T00:00:00.000Z');
    upsertDiscoveryShelfItem({
      artist: 'Archive Artist',
      contentId: 'sha256:archive',
      title: 'Archive Track',
    }, 1, '2026-04-30T00:00:00.000Z');

    expect(getDiscoveryShelfPromoteItems()).toEqual([
      expect.objectContaining({
        evidenceKey: 'discovery-shelf:content:sha256:promote',
        searchText: 'Fixture Artist Fixture Album Promote Track',
        source: 'Discovery Shelf',
        title: 'Fixture Artist - Fixture Album - Promote Track',
      }),
    ]);
  });
});
