import {
  addWishlistItemToDiscoveryInbox,
  buildWishlistRequestReviewPacket,
  buildWishlistRequestSummary,
  buildWishlistDiscoveryInboxItem,
  formatWishlistRequestReviewPacket,
  getWishlistEvidenceKey,
  getWishlistRequestState,
  getRunnableWishlistRequests,
} from './acquisitionRequests';
import { discoveryInboxStorageKey } from './discoveryInbox';

describe('acquisitionRequests', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('creates stable wishlist evidence keys', () => {
    expect(
      getWishlistEvidenceKey({
        filter: 'FLAC',
        id: 'abc',
        searchText: 'Artist - Track',
      }),
    ).toBe('wishlist:abc:artist - track:flac');
  });

  it('maps wishlist defaults to unified request states', () => {
    expect(
      getWishlistRequestState({
        autoDownload: false,
        enabled: false,
        id: 'disabled',
        searchText: 'disabled',
      }).label,
    ).toBe('Disabled');
    expect(
      getWishlistRequestState({
        autoDownload: false,
        enabled: true,
        id: 'wanted',
        searchText: 'wanted',
      }).label,
    ).toBe('Wanted');
    expect(
      getWishlistRequestState({
        autoDownload: true,
        enabled: true,
        id: 'auto',
        searchText: 'auto',
      }).label,
    ).toBe('Automatic');
  });

  it('maps matching Discovery Inbox decisions over wishlist defaults', () => {
    const item = {
      autoDownload: true,
      enabled: true,
      id: 'rare',
      searchText: 'rare track',
    };

    addWishlistItemToDiscoveryInbox(item);

    expect(getWishlistRequestState(item).label).toBe('Review');
  });

  it('builds Discovery Inbox items from wishlist requests without starting work', () => {
    const item = {
      autoDownload: false,
      enabled: true,
      filter: 'flac',
      id: 'wish-1',
      searchText: 'rare album',
    };

    expect(buildWishlistDiscoveryInboxItem(item)).toEqual(
      expect.objectContaining({
        evidenceKey: 'wishlist:wish-1:rare album:flac',
        networkImpact:
          'Review only; approving here does not start peer search, browse, or download work.',
        reason: 'Saved Wishlist request with filter "flac".',
        searchText: 'rare album',
        source: 'Wishlist',
        sourceId: 'wish-1',
        title: 'rare album',
      }),
    );

    addWishlistItemToDiscoveryInbox(item);

    const persisted = JSON.parse(localStorage.getItem(discoveryInboxStorageKey));
    expect(persisted).toHaveLength(1);
    expect(persisted[0]).toEqual(
      expect.objectContaining({
        evidenceKey: 'wishlist:wish-1:rare album:flac',
        source: 'Wishlist',
        sourceId: 'wish-1',
      }),
    );
  });

  it('builds request summaries with quota-style status', () => {
    const items = [
      {
        autoDownload: false,
        enabled: true,
        id: 'wish-1',
        searchText: 'manual request',
      },
      {
        autoDownload: true,
        enabled: true,
        id: 'wish-2',
        searchText: 'automatic request',
      },
      {
        autoDownload: false,
        enabled: false,
        id: 'wish-3',
        searchText: 'disabled request',
      },
    ];

    addWishlistItemToDiscoveryInbox(items[0]);

    expect(buildWishlistRequestSummary({ items, quota: 2 })).toEqual(
      expect.objectContaining({
        automatic: 1,
        enabled: 2,
        quota: 2,
        quotaRemaining: 0,
        quotaStatus: 'Over quota',
        reviewCount: 1,
        total: 3,
      }),
    );
  });

  it('formats review packets for operator approval without starting work', () => {
    const packet = buildWishlistRequestReviewPacket({
      items: [
        {
          autoDownload: true,
          enabled: true,
          id: 'wish-1',
          searchText: 'rare album',
        },
      ],
      quota: 1,
    });
    const report = formatWishlistRequestReviewPacket(packet);

    expect(packet.rows[0]).toEqual(
      expect.objectContaining({
        searchText: 'rare album',
        state: 'Automatic',
      }),
    );
    expect(report).toContain('slskdN Wishlist request review');
    expect(report).toContain('[Automatic] rare album');
  });

  it('preserves unknown states and quota labels in copied request packets', () => {
    const report = formatWishlistRequestReviewPacket({
      generatedAt: '2026-10-31T00:00:00.000Z',
      rows: [{
        autoDownload: false,
        enabled: true,
        searchText: 'user supplied title',
        state: 'adapter-state:{room}',
      }],
      summary: {
        automatic: 0,
        enabled: 1,
        quotaRemaining: 0,
        quotaStatus: 'adapter quota:{room}',
        reviewCount: 0,
        total: 1,
      },
    });

    expect(report).toContain('adapter quota:{room}');
    expect(report).toContain('adapter-state:{room}');
    expect(report).toContain('user supplied title');
  });

  it('selects bounded runnable wishlist requests', () => {
    const requests = getRunnableWishlistRequests([
      { enabled: true, id: 'one', searchText: 'one' },
      { enabled: false, id: 'two', searchText: 'two' },
      { enabled: true, id: 'three', searchText: 'three' },
      { enabled: true, id: 'four', searchText: 'four' },
    ], { limit: 2 });

    expect(requests.map((item) => item.id)).toEqual(['one', 'three']);
  });
});
