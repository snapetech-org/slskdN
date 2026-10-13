import api from './api';
import { getLocalStorageItem, setLocalStorageItem } from './storage';
import { v4 as uuidv4 } from 'uuid';

const USER_DOWNLOAD_STATS_CACHE_TTL_MS = 30_000;
let userDownloadStatsCache = null;
let userDownloadStatsCacheExpiresAt = 0;
let userDownloadStatsInflight = null;

export const getAll = async (
  limit = 500,
  source = null,
  offset = 0,
  afterStartedAt = null,
  afterId = null,
) => {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (source && source !== 'all') {
    params.set('source', source);
  }
  if (afterStartedAt != null && afterId != null) {
    params.set('afterStartedAt', afterStartedAt);
    params.set('afterId', afterId);
  }
  return (await api.get(`/searches?${params.toString()}`)).data;
};

export const cleanupSearches = () => {
  return api.post('/searches/cleanup');
};

export const get = async ({ id }) => {
  return (await api.get(`/searches/${encodeURIComponent(id)}`)).data;
};

export const stop = ({ id }) => {
  return api.put(`/searches/${encodeURIComponent(id)}`);
};

export const remove = ({ id }) => {
  return api.delete(`/searches/${encodeURIComponent(id)}`);
};

export const removeAll = () => {
  return api.delete('/searches');
};

// User download stats for badges
export const getUserDownloadStats = () => {
  if (
    userDownloadStatsCache &&
    userDownloadStatsCacheExpiresAt > Date.now()
  ) {
    return Promise.resolve(userDownloadStatsCache);
  }

  if (userDownloadStatsInflight) {
    return userDownloadStatsInflight;
  }

  userDownloadStatsInflight = api
    .get('/transfers/downloads/user-stats')
    .then((response) => {
      const stats =
        response.data &&
        typeof response.data === 'object' &&
        !Array.isArray(response.data)
          ? response.data
          : {};
      userDownloadStatsCache = stats;
      userDownloadStatsCacheExpiresAt =
        Date.now() + USER_DOWNLOAD_STATS_CACHE_TTL_MS;
      return stats;
    })
    .finally(() => {
      userDownloadStatsInflight = null;
    });

  return userDownloadStatsInflight;
};

// Browser compatibility cache for the durable blocked-user policy.
export const BLOCKED_USERS_KEY = 'slskdn_blocked_users';

const normalizeBlockedUsername = (username) =>
  typeof username === 'string' ? username.trim() : '';

const uniqueUsernames = (usernames) => {
  const seen = new Set();
  return usernames.reduce((unique, username) => {
    const normalized = normalizeBlockedUsername(username);
    const key = normalized.toLocaleLowerCase();
    if (normalized && !seen.has(key)) {
      seen.add(key);
      unique.push(normalized);
    }
    return unique;
  }, []);
};

export const getBlockedUsers = () => {
  try {
    const blocked = getLocalStorageItem(BLOCKED_USERS_KEY);
    const parsed = blocked ? JSON.parse(blocked) : [];
    return Array.isArray(parsed) ? uniqueUsernames(parsed) : [];
  } catch {
    return [];
  }
};

export const setBlockedUsers = (usernames) => {
  const blocked = uniqueUsernames(Array.isArray(usernames) ? usernames : []);
  setLocalStorageItem(BLOCKED_USERS_KEY, JSON.stringify(blocked));
  return blocked;
};

export const blockUser = (username) => {
  const normalized = normalizeBlockedUsername(username);
  const blocked = getBlockedUsers();
  if (!normalized) {
    return blocked;
  }

  return setBlockedUsers([...blocked, normalized]);
};

export const unblockUser = (username) => {
  const normalized = normalizeBlockedUsername(username).toLocaleLowerCase();
  return setBlockedUsers(
    getBlockedUsers().filter(
      (blockedUsername) => blockedUsername.toLocaleLowerCase() !== normalized,
    ),
  );
};

export const isUserBlocked = (username) => {
  const normalized = normalizeBlockedUsername(username).toLocaleLowerCase();
  return Boolean(normalized) && getBlockedUsers().some(
    (blockedUsername) => blockedUsername.toLocaleLowerCase() === normalized,
  );
};

export const create = ({
  acquisitionProfile = null,
  id,
  searchText,
  providers = null,
}) => {
  const body = { id, searchText };

  if (acquisitionProfile) {
    body.acquisitionProfile = acquisitionProfile;
  }

  // Include providers if specified (for Scene ↔ Pod Bridging)
  if (providers && Array.isArray(providers)) {
    body.providers = providers;
  }

  return api.post('/searches', body);
};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const isSerializedSearchCreateError = (error) =>
  error?.response?.status === 429 &&
  /only one concurrent operation is permitted/i.test(
    error?.response?.data || error?.message || '',
  );

const createWithRetry = async (
  request,
  { maxAttempts = 4, retryDelayMs = 300 } = {},
) => {
  let attempt = 0;

  while (attempt < maxAttempts) {
    attempt += 1;

    try {
      return await create(request);
    } catch (error) {
      if (!isSerializedSearchCreateError(error) || attempt >= maxAttempts) {
        throw error;
      }

      await sleep(retryDelayMs * attempt);
    }
  }

  throw new Error('Search batch retry loop exhausted unexpectedly.');
};

export const createBatch = async ({
  acquisitionProfile = null,
  queries = [],
  providers = null,
} = {}) => {
  const normalizedQueries = Array.isArray(queries)
    ? queries.map((query) => (query || '').trim()).filter(Boolean)
    : [];

  await normalizedQueries.reduce(
    (chain, searchText) =>
      chain.then(() =>
        createWithRetry({
          acquisitionProfile,
          id: uuidv4(),
          providers,
          searchText,
        }),
      ),
    Promise.resolve(),
  );

  return normalizedQueries.length;
};

export const getStatus = async ({ id, includeResponses = false }) => {
  return (
    await api.get(
      `/searches/${encodeURIComponent(id)}?includeResponses=${includeResponses}`,
    )
  ).data;
};

export const getResponses = async ({ id }) => {
  const response = (
    await api.get(`/searches/${encodeURIComponent(id)}/responses`)
  ).data;

  if (!Array.isArray(response)) {
    console.warn('got non-array response from searches API', response);
    return [];
  }

  return response;
};

const getNthMatch = (string, regex, n) => {
  const match = string.match(regex);

  if (match) {
    return Number.parseInt(match[n], 10);
  }

  return undefined;
};

// Parse size with unit (kb, mb, gb). Without unit, defaults to bytes.
const parseSize = (value, unit) => {
  const parsedNumber = Number.parseInt(value, 10);
  switch (unit?.toLowerCase()) {
    case 'gb':
      return parsedNumber * 1_024 * 1_024 * 1_024;
    case 'mb':
      return parsedNumber * 1_024 * 1_024;
    case 'kb':
      return parsedNumber * 1_024;
    case 'b':
    default:
      // Without unit, treat as bytes (most intuitive for raw numbers)
      return parsedNumber;
  }
};

const getSizeFromRegex = (string, regex) => {
  const match = string.match(regex);
  if (match) {
    const value = match[2];
    const unit = match[3];
    if (unit) {
      return parseSize(value, unit);
    }

    return Number.parseInt(value, 10);
  }

  return undefined;
};

export const parseFiltersFromString = (string) => {
  const filters = {
    exclude: [],
    extensions: [],
    include: [],
    isCBR: false,
    isLossless: false,
    isLossy: false,
    isVBR: false,
    maxFileSize: Number.MAX_SAFE_INTEGER,
    minBitDepth: 0,
    minBitRate: 0,
    minFilesInFolder: 0,
    minFileSize: 0,
    minLength: 0,
    minSampleRate: 0,
    preferExtensions: [],
    preferLossless: false,
    preferMinBitRate: 0,
  };

  filters.minBitRate =
    getNthMatch(string, /(minbr|minbitrate):(\d+)/iu, 2) || filters.minBitRate;
  filters.minBitDepth =
    getNthMatch(string, /(minbd|minbitdepth):(\d+)/iu, 2) ||
    filters.minBitDepth;
  filters.minSampleRate =
    getNthMatch(string, /(minsr|minsamplerate):(\d+)/iu, 2) ||
    filters.minSampleRate;

  filters.minFileSize =
    getSizeFromRegex(string, /(minfs|minfilesize):(\d+)(kb|mb|gb)?/iu) ||
    filters.minFileSize;

  filters.maxFileSize =
    getSizeFromRegex(string, /(maxfs|maxfilesize):(\d+)(kb|mb|gb)?/iu) ||
    filters.maxFileSize;

  filters.minLength =
    getNthMatch(string, /(minlen|minlength):(\d+)/iu, 2) || filters.minLength;
  filters.minFilesInFolder =
    getNthMatch(string, /(minfif|minfilesinfolder):(\d+)/iu, 2) ||
    filters.minFilesInFolder;

  filters.isVBR = Boolean(/isvbr/iu.test(string));
  filters.isCBR = Boolean(/iscbr/iu.test(string));
  filters.isLossless = Boolean(/islossless/iu.test(string));
  filters.isLossy = Boolean(/islossy/iu.test(string));
  filters.preferLossless = Boolean(/preferlossless/iu.test(string));
  filters.preferMinBitRate =
    getNthMatch(string, /(prefbr|preferbr|preferbitrate):(\d+)/iu, 2) ||
    filters.preferMinBitRate;

  // Parse extensions: ext:flac,mp3 or ext:flac mp3
  const extensionMatch = string.match(/ext:(\S+)/iu);
  if (extensionMatch) {
    filters.extensions = extensionMatch[1]
      .split(/[ ,]/)
      .map((e) => e.toLowerCase().trim())
      .filter((e) => e.length > 0);
  }

  const preferredExtensionMatch = string.match(/prefext:(\S+)/iu);
  if (preferredExtensionMatch) {
    filters.preferExtensions = preferredExtensionMatch[1]
      .split(/[ ,]/)
      .map((e) => e.toLowerCase().trim())
      .filter((e) => e.length > 0);
  }

  const terms = (string.toLowerCase().match(/-?"[^"]+"|\S+/gu) || [])
    .map((term) => {
      const excluded = term.startsWith('-');
      const value = (excluded ? term.slice(1) : term).replace(/^"|"$/gu, '');
      return excluded ? `-${value}` : value;
    })
    .filter(
      (term) =>
        !term.includes(':') &&
        term !== 'isvbr' &&
        term !== 'iscbr' &&
        term !== 'islossless' &&
        term !== 'islossy' &&
        term !== 'preferlossless' &&
        !term.startsWith('ext:') &&
        !term.startsWith('prefext:'),
    );

  filters.include = terms.filter((term) => !term.startsWith('-'));
  filters.exclude = terms
    .filter((term) => term.startsWith('-'))
    .map((term) => term.slice(1));

  return filters;
};

// eslint-disable-next-line complexity
const filterFile = (file, filters) => {
  const {
    bitRate,
    size,
    length,
    filename,
    sampleRate,
    bitDepth,
    isVariableBitRate,
  } = file;
  const {
    isCBR,
    isVBR,
    isLossless,
    isLossy,
    minBitRate,
    minBitDepth,
    minSampleRate,
    maxFileSize,
    minFileSize,
    minLength,
    include = [],
    exclude = [],
    extensions = [],
  } = filters;

  if (isCBR && (isVariableBitRate === undefined || isVariableBitRate))
    return false;
  if (isVBR && (isVariableBitRate === undefined || !isVariableBitRate))
    return false;
  if (isLossless && (!sampleRate || !bitDepth)) return false;
  if (isLossy && (sampleRate || bitDepth)) return false;
  if (bitRate < minBitRate) return false;
  if (bitDepth < minBitDepth) return false;
  if (minSampleRate && sampleRate && sampleRate < minSampleRate) return false;
  if (size < minFileSize) return false;
  if (size > maxFileSize) return false;
  if (length < minLength) return false;

  // Filter by file extension
  if (extensions.length > 0) {
    const fileExtension = filename.split('.').pop()?.toLowerCase();
    if (!fileExtension || !extensions.includes(fileExtension)) return false;
  }

  if (
    include.length > 0 &&
    include.filter((term) => filename.toLowerCase().includes(term)).length !==
      include.length
  ) {
    return false;
  }

  if (exclude.some((term) => filename.toLowerCase().includes(term)))
    return false;

  return true;
};

export const filterResponse = ({
  filters = {
    exclude: [],
    extensions: [],
    include: [],
    isCBR: false,
    isLossless: false,
    isLossy: false,
    isVBR: false,
    maxFileSize: Number.MAX_SAFE_INTEGER,
    minBitDepth: 0,
    minBitRate: 0,
    minFilesInFolder: 0,
    minFileSize: 0,
    minLength: 0,
    minSampleRate: 0,
    preferExtensions: [],
    preferLossless: false,
    preferMinBitRate: 0,
  },
  response = {
    files: [],
    lockedFiles: [],
  },
}) => {
  const { files = [], lockedFiles = [] } = response;

  if (
    response.fileCount + response.lockedFileCount <
    filters.minFilesInFolder
  ) {
    return { ...response, files: [] };
  }

  const filterFiles = (filesToFilter) =>
    filesToFilter.filter((file) => filterFile(file, filters));

  const filteredFiles = filterFiles(files);
  const filteredLockedFiles = filterFiles(lockedFiles);

  return {
    ...response,
    fileCount: filteredFiles.length,
    files: filteredFiles,
    lockedFileCount: filteredLockedFiles.length,
    lockedFiles: filteredLockedFiles,
  };
};

export const serializeFiltersToString = (filters) => {
  const parts = [];

  if (filters.include && filters.include.length > 0)
    parts.push(...filters.include);
  if (filters.exclude && filters.exclude.length > 0)
    parts.push(...filters.exclude.map((term) => `-${term}`));

  if (filters.minBitRate) parts.push(`minbr:${filters.minBitRate}`);
  if (filters.minBitDepth) parts.push(`minbd:${filters.minBitDepth}`);
  if (filters.minSampleRate) parts.push(`minsr:${filters.minSampleRate}`);
  if (filters.minFileSize) parts.push(`minfs:${filters.minFileSize}`);
  if (filters.maxFileSize && filters.maxFileSize < Number.MAX_SAFE_INTEGER)
    parts.push(`maxfs:${filters.maxFileSize}`);
  if (filters.minLength) parts.push(`minlen:${filters.minLength}`);
  if (filters.minFilesInFolder)
    parts.push(`minfif:${filters.minFilesInFolder}`);

  if (filters.isVBR) parts.push('isvbr');
  if (filters.isCBR) parts.push('iscbr');
  if (filters.isLossless) parts.push('islossless');
  if (filters.isLossy) parts.push('islossy');
  if (filters.preferLossless) parts.push('preferlossless');
  if (filters.preferMinBitRate) parts.push(`prefbr:${filters.preferMinBitRate}`);

  if (filters.extensions && filters.extensions.length > 0) {
    parts.push(`ext:${filters.extensions.join(',')}`);
  }

  if (filters.preferExtensions && filters.preferExtensions.length > 0) {
    parts.push(`prefext:${filters.preferExtensions.join(',')}`);
  }

  return parts.join(' ');
};
