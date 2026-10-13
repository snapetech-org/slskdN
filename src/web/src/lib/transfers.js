import api from './api';

export const getAll = async ({ direction, includeCompleted = true }) => {
  const params = includeCompleted ? '' : '?includeCompleted=false';
  const response = (
    await api.get(`/transfers/${encodeURIComponent(direction)}s${params}`)
  ).data;

  if (!Array.isArray(response)) {
    console.warn('got non-array response from transfers API', response);
    return [];
  }

  return response;
};

/**
 * Flat, ungrouped snapshot of transfers across both directions. Used by the
 * TransferManager store as the initial seed and the periodic reconcile.
 * @param {{ direction?: 'download'|'upload', includeCompleted?: boolean, includeRemoved?: boolean }} [opts]
 * @returns {Promise<Array>} flat array of transfer records
 */
export const getFlat = async ({
  direction,
  includeCompleted = true,
  includeRemoved = false,
} = {}) => {
  const params = new URLSearchParams();
  if (direction) params.set('direction', direction);
  if (!includeCompleted) params.set('includeCompleted', 'false');
  if (includeRemoved) params.set('includeRemoved', 'true');

  const query = params.toString();
  const response = (await api.get(`/transfers${query ? `?${query}` : ''}`))
    .data;

  if (!Array.isArray(response)) {
    console.warn('got non-array response from flat transfers API', response);
    return [];
  }

  return response;
};

/**
 * Server-watermarked transfer snapshot/delta used by TransferManager.
 * The first call omits `since`; later calls pass the prior cursor.
 * @param {{ afterId?: string|null, afterRequestedAt?: string|null, direction?: 'download'|'upload'|null, includeCompleted?: boolean, limit?: number|null, since?: number|null, snapshot?: number|null }} [opts]
 * @returns {Promise<{cursor: number|null, transfers: Array}>}
 */
export const getChanges = async ({
  afterId = null,
  afterRequestedAt = null,
  direction = null,
  includeCompleted = false,
  limit = null,
  since = null,
  snapshot = null,
} = {}) => {
  const params = new URLSearchParams();
  if (since != null) {
    params.set('since', since);
  } else {
    params.set('includeCompleted', String(includeCompleted));
    if (direction) params.set('direction', direction);
    if (limit != null) params.set('limit', String(limit));
    if (snapshot != null) params.set('asOf', String(snapshot));
    if (afterRequestedAt != null) {
      params.set('afterRequestedAt', String(afterRequestedAt));
    }
    if (afterId != null) params.set('afterId', String(afterId));
  }
  const response = (await api.get(`/transfers/changes?${params}`)).data;
  const cursor = Number(response?.cursor);
  const downloadCount = Number(response?.counts?.download);
  const uploadCount = Number(response?.counts?.upload);

  return {
    counts: {
      download: Number.isFinite(downloadCount) ? downloadCount : 0,
      upload: Number.isFinite(uploadCount) ? uploadCount : 0,
    },
    cursor: Number.isFinite(cursor) ? cursor : null,
    hasMore: response?.hasMore === true,
    nextAfterId: typeof response?.nextAfterId === 'string'
      ? response.nextAfterId
      : null,
    nextAfterRequestedAt:
      typeof response?.nextAfterRequestedAt === 'string'
        ? response.nextAfterRequestedAt
        : null,
    transfers: Array.isArray(response?.transfers) ? response.transfers : [],
  };
};

export const getHistory = async ({
  direction,
  asOf = null,
  offset = 0,
  limit = 250,
}) => {
  const params = new URLSearchParams({ direction, limit, offset });
  if (asOf != null) params.set('asOf', asOf);
  const response = (await api.get(`/transfers/history?${params}`)).data;
  const snapshotAt = Number(response?.asOf);
  const nextOffset = Number(response?.nextOffset);

  return {
    asOf: Number.isFinite(snapshotAt) ? snapshotAt : null,
    hasMore: response?.hasMore === true,
    nextOffset: Number.isFinite(nextOffset) ? nextOffset : offset,
    transfers: Array.isArray(response?.transfers) ? response.transfers : [],
  };
};

export const getSpeeds = async () => {
  const response = await api.get('/transfers/speeds');
  return response.data;
};

export const getAcceleratedMode = async () => {
  const response = await api.get('/transfers/downloads/accelerated');
  return response.data;
};

export const setAcceleratedMode = async ({ enabled }) => {
  const response = await api.put('/transfers/downloads/accelerated', {
    enabled,
  });
  return response.data;
};

export const download = ({ username, files = [], destination }) => {
  const parameters = destination
    ? `?destination=${encodeURIComponent(destination)}`
    : '';
  return api.post(
    `/transfers/downloads/${encodeURIComponent(username)}${parameters}`,
    files,
  );
};

export const cancel = ({
  direction,
  username,
  id,
  remove = false,
  deleteFile = false,
}) => {
  return api.delete(
    `/transfers/${direction}s/${encodeURIComponent(username)}/${encodeURIComponent(id)}?remove=${remove}&deleteFile=${deleteFile}`,
  );
};

export const clearCompleted = ({ direction }) => {
  return api.delete(`/transfers/${direction}s/all/completed`);
};

// 'Requested'
// 'Queued, Remotely'
// 'Queued, Locally'
// 'Initializing'
// 'InProgress'
// 'Completed, Succeeded'
// 'Completed, Cancelled'
// 'Completed, TimedOut'
// 'Completed, Errored'
// 'Completed, Rejected'
// 'Completed, Aborted'

export const getPlaceInQueue = ({ username, id }) => {
  return api.get(
    `/transfers/downloads/${encodeURIComponent(username)}/${encodeURIComponent(id)}/position`,
  );
};

export const isStateSucceeded = (state) => state === 'Completed, Succeeded';

export const isStateTerminal = (state = '') => state.includes('Completed');

export const isStateRetryable = (state) =>
  isStateTerminal(state) && !isStateSucceeded(state);

export const isStateCancellable = (state) =>
  [
    'InProgress',
    'Requested',
    'Queued',
    'Queued, Remotely',
    'Queued, Locally',
    'Initializing',
  ].find((s) => s === state);

export const isStateRemovable = (state) => isStateTerminal(state);

const isRemoteUnavailableTransferError = (message = '') =>
  [
    'Remote connection closed',
    'Connection reset by peer',
    'Failed to establish a direct or indirect message connection',
    'Failed to establish a direct or indirect transfer connection',
    'Download reported as failed by remote client',
    'Transfer rejected:',
  ].some((token) => message.includes(token));

/**
 * Extracts a concise, user-facing reason from a transfer exception string.
 * Returns the original exception if no common pattern is identified.
 */
export const getFailureReason = (exception = '') => {
  if (!exception) return '';

  // TransferRejectedException: Transfer rejected: File not shared.
  const rejectedMatch = exception.match(/Transfer\s+rejected:\s*(.+?)\.?$/im);
  if (rejectedMatch) return rejectedMatch[1].trim();

  // TransferRejectedException: Transfer rejected: Enqueue failed due to internal error
  const enqueueFailedMatch = exception.match(/Enqueue\s+failed\s+due\s+to\s+(.+?)(?:;|\.|$)/im);
  if (enqueueFailedMatch) return enqueueFailedMatch[1].trim();

  // TransferSizeMismatchException: Transfer aborted: the remote size of X does not match expected size Y
  const sizeMismatchMatch = exception.match(/the\s+remote\s+size\s+of\s+\d+\s+does\s+not\s+match\s+expected\s+size\s+\d+/im);
  if (sizeMismatchMatch) return 'Size mismatch';

  // UserOfflineException: User X appears to be offline
  const offlineMatch = exception.match(/appears\s+to\s+be\s+offline/i);
  if (offlineMatch) return 'User offline';

  // Timeout
  const timeoutMatch = exception.match(/timed?\s*out/i);
  if (timeoutMatch) return 'Timed out';

  // Remote connection closed / Connection reset
  const connectionMatch = exception.match(/(Remote\s+connection\s+closed|Connection\s+reset\s+by\s+peer)/i);
  if (connectionMatch) return 'Connection lost';

  // Truncate verbose exception type prefixes
  return exception
    .replace(/^(Soulseek\.)?\w+Exception:\s*/i, '')
    .replace(/; remoteReason=.*$/, '')
    .trim();
};

export const formatTransferState = (state, exception = '') => {
  switch (state) {
    case 'Completed, Succeeded':
      return 'Complete';
    case 'Completed, Cancelled':
      return 'Cancelled';
    case 'Completed, TimedOut':
      return 'Timed out';
    case 'Completed, Errored':
      return isRemoteUnavailableTransferError(exception)
        ? 'Peer unavailable'
        : 'Error';
    case 'Completed, Rejected': {
      const reason = getFailureReason(exception);
      return reason ? `Rejected (${reason})` : 'Rejected';
    }
    case 'Completed, Aborted':
      return 'Aborted';
    default:
      return state;
  }
};

/**
 * Returns the appropriate affordance (actionable suggestion) for a given
 * failure reason string.  Each affordance has a label, icon, and action
 * type that the UI can turn into a button or tooltip.
 *
 * @param {string} reason - the failure reason from getFailureReason()
 * @returns {{ action: string, label: string, icon: string, description: string }}
 */
export const getErrorAffordance = (reason = '') => {
  const r = reason.toLowerCase();

  // Peer-specific limits / capacity
  if (r.includes('too many megabytes')) {
    return {
      action: 'retry',
      label: 'Find other sources',
      icon: 'search',
      description: 'This user reached their transfer limit. Retry to find another peer who has this file.',
    };
  }

  if (r.includes('overwhelmed')) {
    return {
      action: 'retry',
      label: 'Retry later',
      icon: 'clock',
      description: 'This user is busy. Retry when they have capacity.',
    };
  }

  // The remote peer no longer shares the file
  if (r.includes('not shared') || r.includes('file not found')) {
    return {
      action: 'retry',
      label: 'Find other sources',
      icon: 'search',
      description: 'This user no longer shares this file. Retry to find another peer.',
    };
  }

  // File version mismatch
  if (r.includes('size mismatch') || r.includes('does not match expected size')) {
    return {
      action: 'retry',
      label: 'Find other sources',
      icon: 'search',
      description: 'File size differs between sources. Retry to find a matching copy.',
    };
  }

  // Remote internal error
  if (r.includes('internal error')) {
    return {
      action: 'retry',
      label: 'Find other sources',
      icon: 'search',
      description: 'The remote peer encountered an error. Retry to find a different peer.',
    };
  }

  // Peer offline
  if (r.includes('offline') || r.includes('unavailable') || r.includes('appears to be offline')) {
    return {
      action: 'wait',
      label: 'Wait for online',
      icon: 'pause',
      description: 'The user is currently offline. The system will retry automatically when they come back.',
    };
  }

  // Connection lost
  if (r.includes('connection lost') || r.includes('connection closed') || r.includes('reset by peer')) {
    return {
      action: 'retry',
      label: 'Retry',
      icon: 'redo',
      description: 'The connection was lost. Retry to re-establish the transfer.',
    };
  }

  // Generic retry
  return {
    action: 'retry',
    label: 'Retry',
    icon: 'redo',
    description: 'Retry the download to attempt again or find other sources.',
  };
};
