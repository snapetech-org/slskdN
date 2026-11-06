import {
  addDiscoveryInboxItem,
  getDiscoveryInboxItems,
} from './discoveryInbox';
import { interfaceText } from './interfaceLocale';
import { formatRegionalNumber } from './regionalFormat';

export const acquisitionRequestStates = {
  approved: {
    color: 'green',
    label: 'Approved',
    summary: 'Approved in Discovery Inbox for the next acquisition step.',
  },
  automatic: {
    color: 'blue',
    label: 'Automatic',
    summary: 'Enabled and allowed to auto-download through Wishlist policy.',
  },
  disabled: {
    color: 'grey',
    label: 'Disabled',
    summary: 'Saved but not eligible for scheduled wishlist processing.',
  },
  failed: {
    color: 'red',
    label: 'Failed',
    summary: 'A previous acquisition/import attempt failed and needs review.',
  },
  imported: {
    color: 'teal',
    label: 'Imported',
    summary: 'The request has been imported into the library.',
  },
  rejected: {
    color: 'red',
    label: 'Rejected',
    summary: 'Rejected in Discovery Inbox and suppressed for the same evidence.',
  },
  review: {
    color: 'yellow',
    label: 'Review',
    summary: 'Waiting in Discovery Inbox for approval or rejection.',
  },
  snoozed: {
    color: 'grey',
    label: 'Snoozed',
    summary: 'Snoozed in Discovery Inbox until later review.',
  },
  staged: {
    color: 'violet',
    label: 'Staged',
    summary: 'Downloaded or prepared for import review.',
  },
  wanted: {
    color: 'purple',
    label: 'Wanted',
    summary: 'Enabled wishlist request with manual download approval.',
  },
};

const localizeWishlistRequestCopy = (source) => {
  switch (source) {
    case 'Approved':
      return interfaceText('Approved');
    case 'Automatic':
      return interfaceText('Automatic');
    case 'Disabled':
      return interfaceText('Disabled');
    case 'Failed':
      return interfaceText('Failed');
    case 'Imported':
      return interfaceText('Imported');
    case 'Rejected':
      return interfaceText('Rejected');
    case 'Review':
      return interfaceText('Review');
    case 'Snoozed':
      return interfaceText('Snoozed');
    case 'Staged':
      return interfaceText('Staged');
    case 'Wanted':
      return interfaceText('Wanted');
    case 'Approved in Discovery Inbox for the next acquisition step.':
      return interfaceText('Approved in Discovery Inbox for the next acquisition step.');
    case 'Enabled and allowed to auto-download through Wishlist policy.':
      return interfaceText('Enabled and allowed to auto-download through Wishlist policy.');
    case 'Saved but not eligible for scheduled wishlist processing.':
      return interfaceText('Saved but not eligible for scheduled wishlist processing.');
    case 'A previous acquisition/import attempt failed and needs review.':
      return interfaceText('A previous acquisition/import attempt failed and needs review.');
    case 'The request has been imported into the library.':
      return interfaceText('The request has been imported into the library.');
    case 'Rejected in Discovery Inbox and suppressed for the same evidence.':
      return interfaceText('Rejected in Discovery Inbox and suppressed for the same evidence.');
    case 'Waiting in Discovery Inbox for approval or rejection.':
      return interfaceText('Waiting in Discovery Inbox for approval or rejection.');
    case 'Snoozed in Discovery Inbox until later review.':
      return interfaceText('Snoozed in Discovery Inbox until later review.');
    case 'Downloaded or prepared for import review.':
      return interfaceText('Downloaded or prepared for import review.');
    case 'Enabled wishlist request with manual download approval.':
      return interfaceText('Enabled wishlist request with manual download approval.');
    case 'Over quota':
      return interfaceText('Over quota');
    case 'Within quota':
      return interfaceText('Within quota');
    default:
      return source;
  }
};

const normalizeText = (value) => `${value || ''}`.trim().toLowerCase();

export const getWishlistEvidenceKey = (item) =>
  `wishlist:${item.id || normalizeText(item.searchText)}:${normalizeText(item.searchText)}:${normalizeText(item.filter)}`;

const mapInboxStateToRequestState = (state) => {
  switch (state) {
    case 'Approved':
      return 'approved';
    case 'Downloading':
      return 'automatic';
    case 'Failed':
      return 'failed';
    case 'Imported':
      return 'imported';
    case 'Rejected':
      return 'rejected';
    case 'Snoozed':
      return 'snoozed';
    case 'Staged':
      return 'staged';
    default:
      return 'review';
  }
};

export const getWishlistRequestState = (
  item,
  inboxItems = getDiscoveryInboxItems(),
) => {
  const inboxItem = inboxItems.find(
    (candidate) => candidate.evidenceKey === getWishlistEvidenceKey(item),
  );

  if (inboxItem) {
    return acquisitionRequestStates[mapInboxStateToRequestState(inboxItem.state)];
  }

  if (!item.enabled) {
    return acquisitionRequestStates.disabled;
  }

  if (item.autoDownload) {
    return acquisitionRequestStates.automatic;
  }

  return acquisitionRequestStates.wanted;
};

export const buildWishlistDiscoveryInboxItem = (item) => ({
  evidenceKey: getWishlistEvidenceKey(item),
  networkImpact: item.autoDownload
    ? 'Review only; approving here does not start download work. This Wishlist item is configured for auto-download when its scheduler runs.'
    : 'Review only; approving here does not start peer search, browse, or download work.',
  reason: `Saved Wishlist request${item.filter ? ` with filter "${item.filter}"` : ''}.`,
  searchText: item.searchText,
  source: 'Wishlist',
  sourceId: item.id,
  title: item.searchText,
});

export const addWishlistItemToDiscoveryInbox = (item) =>
  addDiscoveryInboxItem(buildWishlistDiscoveryInboxItem(item));

export const buildWishlistRequestSummary = ({
  inboxItems = getDiscoveryInboxItems(),
  items = [],
  quota = 25,
} = {}) => {
  const counts = items.reduce(
    (summary, item) => {
      const state = getWishlistRequestState(item, inboxItems).label;
      summary.byState[state] = (summary.byState[state] || 0) + 1;
      if (item.enabled) summary.enabled += 1;
      if (item.autoDownload) summary.automatic += 1;
      return summary;
    },
    {
      automatic: 0,
      byState: {},
      enabled: 0,
      total: items.length,
    },
  );

  return {
    ...counts,
    quota,
    quotaRemaining: Math.max(quota - items.length, 0),
    quotaStatus: items.length > quota ? 'Over quota' : 'Within quota',
    reviewCount:
      (counts.byState.Review || 0) +
      (counts.byState.Approved || 0) +
      (counts.byState.Snoozed || 0),
  };
};

export const buildWishlistRequestReviewPacket = ({
  inboxItems = getDiscoveryInboxItems(),
  items = [],
  quota = 25,
} = {}) => {
  const summary = buildWishlistRequestSummary({ inboxItems, items, quota });
  const rows = items.map((item) => {
    const state = getWishlistRequestState(item, inboxItems);

    return {
      autoDownload: Boolean(item.autoDownload),
      enabled: Boolean(item.enabled),
      id: item.id,
      searchText: item.searchText,
      state: state.label,
    };
  });

  return {
    generatedAt: new Date().toISOString(),
    rows,
    summary,
  };
};

export const formatWishlistRequestReviewPacket = (packet) => {
  const lines = [
    interfaceText('slskdN Wishlist request review'),
    interfaceText('Generated: {timestamp}', { timestamp: packet.generatedAt }),
    interfaceText('Requests: {count}', { count: formatRegionalNumber(packet.summary.total) }),
    interfaceText('Enabled: {count}', { count: formatRegionalNumber(packet.summary.enabled) }),
    interfaceText('Automatic: {count}', { count: formatRegionalNumber(packet.summary.automatic) }),
    interfaceText('Needs review: {count}', { count: formatRegionalNumber(packet.summary.reviewCount) }),
    interfaceText('Quota: {status} ({count} remaining)', {
      count: formatRegionalNumber(packet.summary.quotaRemaining),
      status: localizeWishlistRequestCopy(packet.summary.quotaStatus),
    }),
    '',
    interfaceText('Requests:'),
  ];

  packet.rows.forEach((row) => {
    lines.push(interfaceText('- [{state}] {searchText} ({enabled}, {downloadMode})', {
      downloadMode: interfaceText(row.autoDownload ? 'Automatic' : 'Manual'),
      enabled: interfaceText(row.enabled ? 'Enabled' : 'Disabled'),
      searchText: row.searchText,
      state: localizeWishlistRequestCopy(row.state),
    }));
  });

  return lines.join('\n');
};

export const getRunnableWishlistRequests = (items = [], { limit = 3 } = {}) =>
  items
    .filter((item) => item.enabled)
    .filter((item) => item.id)
    .slice(0, limit);
