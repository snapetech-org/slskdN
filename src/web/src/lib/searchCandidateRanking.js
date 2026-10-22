import { getCommunityQualitySummary } from './communityQualitySignals';
import { inferAlbumTrackConsensus } from './searchAlbumConsensus';

const losslessExtensions = new Set(['aif', 'aiff', 'alac', 'ape', 'flac', 'wav', 'wv']);
const lossyExtensions = new Set(['aac', 'm4a', 'mp3', 'ogg', 'opus', 'wma']);
const artworkExtensions = new Set(['gif', 'jpeg', 'jpg', 'png', 'webp']);

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
const asArray = (value) => (Array.isArray(value) ? value : []);

const getExtension = (filename = '') => {
  const lastSegment = filename.split(/[\\/]/u).pop() || '';
  const index = lastSegment.lastIndexOf('.');
  return index >= 0 ? lastSegment.slice(index + 1).toLowerCase() : '';
};

const getFiles = (response = {}) => [
  ...(Array.isArray(response.files) ? response.files : []),
  ...(Array.isArray(response.lockedFiles) ? response.lockedFiles : []),
];

const normalizeTokens = (value = '') =>
  value
    .toLowerCase()
    .replace(/[^\d a-z]+/gu, ' ')
    .split(/\s+/u)
    .filter((token) => token.length > 2);

const unique = (values) => [...new Set(values)];

const scoreQueryMatch = (files, searchText) => {
  const tokens = unique(normalizeTokens(searchText));
  if (tokens.length === 0 || files.length === 0) {
    return { points: 0, reason: null };
  }

  const bestCoverage = files.reduce((best, file) => {
    const filename = (file.filename || '').toLowerCase();
    const matched = tokens.filter((token) => filename.includes(token)).length;
    return Math.max(best, matched / tokens.length);
  }, 0);

  const points = Math.round(bestCoverage * 18);
  if (bestCoverage >= 0.8) {
    return { points, reason: 'strong filename match' };
  }

  if (bestCoverage >= 0.45) {
    return { points, reason: 'partial filename match' };
  }

  return { points, reason: 'weak filename match' };
};

const scoreFormat = (files, acquisitionProfile) => {
  const mediaFiles = files.filter((file) => !artworkExtensions.has(getExtension(file.filename)));
  if (mediaFiles.length === 0) {
    return { points: 0, reason: 'no media files visible' };
  }

  const losslessCount = mediaFiles.filter((file) => {
    const extension = getExtension(file.filename);
    return losslessExtensions.has(extension) || (file.bitDepth && file.sampleRate);
  }).length;
  const highBitrateLossyCount = mediaFiles.filter((file) => {
    const extension = getExtension(file.filename);
    return lossyExtensions.has(extension) && (file.bitRate || 0) >= 256;
  }).length;

  const losslessRatio = losslessCount / mediaFiles.length;
  const highBitrateLossyRatio = highBitrateLossyCount / mediaFiles.length;

  if (acquisitionProfile === 'fast-good-enough') {
    const points = Math.round((losslessRatio * 12) + (highBitrateLossyRatio * 16));
    const reason = losslessRatio > 0
      ? 'lossless fast-good-enough candidate'
      : highBitrateLossyRatio > 0
        ? 'high bitrate fast-good-enough candidate'
        : 'limited fast-good-enough quality evidence';
    return { points, reason };
  }

  if (acquisitionProfile === 'album-complete') {
    const points = Math.round((losslessRatio * 14) + clamp(mediaFiles.length, 0, 18));
    const reason = mediaFiles.length >= 8 ? 'broad folder candidate' : 'small folder candidate';
    return { points, reason };
  }

  const points = Math.round(losslessRatio * 28 + highBitrateLossyRatio * 6);
  const reason = losslessRatio >= 0.8
    ? 'mostly lossless files'
    : losslessRatio > 0
      ? 'mixed lossless files'
      : 'no lossless signal';
  return { points, reason };
};

const scoreSizeSanity = (files) => {
  const audioFiles = files.filter((file) => {
    const extension = getExtension(file.filename);
    return losslessExtensions.has(extension) || lossyExtensions.has(extension);
  });

  if (audioFiles.length === 0) {
    return { points: 0, reason: null };
  }

  const plausibleFiles = audioFiles.filter((file) => {
    const size = file.size || 0;
    const length = file.length || 0;
    const extension = getExtension(file.filename);

    if (losslessExtensions.has(extension)) {
      return size >= 8_000_000 && size <= 250_000_000;
    }

    if (lossyExtensions.has(extension)) {
      if (length > 0) {
        return size >= Math.min(length * 8, 2_000_000) && size <= 80_000_000;
      }

      return size >= 1_000_000 && size <= 80_000_000;
    }

    return false;
  });

  const ratio = plausibleFiles.length / audioFiles.length;
  const points = Math.round(ratio * 9);
  return {
    points,
    reason: ratio >= 0.8 ? 'plausible file sizes' : 'mixed file size evidence',
  };
};

const scoreAvailability = (response = {}) => {
  const reasons = [];
  let points = 0;

  if (response.hasFreeUploadSlot) {
    points += 12;
    reasons.push('free upload slot');
  } else {
    reasons.push('queued upload');
  }

  const queueLength = response.queueLength ?? 0;
  const queuePoints = clamp(10 - queueLength * 2, 0, 10);
  points += queuePoints;
  if (queueLength <= 1) {
    reasons.push('short queue');
  } else if (queueLength >= 5) {
    reasons.push('long queue');
  }

  const uploadSpeed = response.uploadSpeed ?? 0;
  const speedPoints = clamp(Math.round((uploadSpeed / 5_242_880) * 10), 0, 10);
  points += speedPoints;
  if (uploadSpeed >= 2_097_152) {
    reasons.push('fast peer');
  }

  return { points, reasons };
};

const scoreHistory = (downloadStats) => {
  if (!downloadStats) {
    return { points: 0, reason: null };
  }

  const successes = downloadStats.successfulDownloads || 0;
  const failures = downloadStats.failedDownloads || 0;
  const points = clamp(successes * 2 - failures * 3, -9, 10);
  const reason = points >= 5
    ? 'trusted download history'
    : points < 0
      ? 'poor download history'
      : 'limited download history';

  return { points, reason };
};

const scoreProvider = (response = {}) => {
  const providers = asArray(response.sourceProviders);
  if (providers.includes('local')) {
    return { points: 8, reason: 'local source available' };
  }

  if (providers.includes('mesh') || providers.includes('pod')) {
    return { points: 5, reason: 'mesh source available' };
  }

  return { points: 0, reason: null };
};

const scoreCommunityQuality = (summary) => {
  if (!summary || (summary.signals.length === 0 && !summary.override)) {
    return { points: 0, reason: null };
  }

  if (summary.override?.mode === 'ignore') {
    return { points: 0, reason: 'local quality signals ignored' };
  }

  if (summary.override?.mode === 'trust') {
    return { points: 8, reason: 'local trust override' };
  }

  if (summary.override?.mode === 'caution') {
    return { points: -6, reason: 'local caution override' };
  }

  if (summary.score >= 8) {
    return { points: Math.min(summary.score, 10), reason: 'positive local quality signals' };
  }

  if (summary.score <= -6) {
    return { points: Math.max(summary.score, -15), reason: 'local caution signals' };
  }

  return { points: summary.score, reason: 'mixed local quality signals' };
};

const scorePreferredConditions = (files, preferredConditions = {}) => {
  const reasons = [];
  let points = 0;

  const preferredExtensions = asArray(preferredConditions.preferExtensions);
  if (preferredExtensions.length > 0 && files.length > 0) {
    const matching = files.filter((file) =>
      preferredExtensions.includes(getExtension(file.filename)),
    ).length;
    if (matching > 0) {
      points += Math.min(Math.round((matching / files.length) * 10), 10);
      reasons.push('preferred extension match');
    } else {
      points -= 4;
      reasons.push('missing preferred extension');
    }
  }

  if (preferredConditions.preferLossless && files.length > 0) {
    const lossless = files.filter((file) => {
      const extension = getExtension(file.filename);
      return losslessExtensions.has(extension) || (file.bitDepth && file.sampleRate);
    }).length;
    if (lossless > 0) {
      points += Math.min(Math.round((lossless / files.length) * 12), 12);
      reasons.push('preferred lossless match');
    } else {
      points -= 6;
      reasons.push('missing preferred lossless files');
    }
  }

  if (preferredConditions.preferMinBitRate && files.length > 0) {
    const matchingBitRate = files.filter(
      (file) => (file.bitRate || 0) >= preferredConditions.preferMinBitRate,
    ).length;
    if (matchingBitRate > 0) {
      points += Math.min(Math.round((matchingBitRate / files.length) * 8), 8);
      reasons.push('preferred bitrate match');
    } else {
      points -= 3;
      reasons.push('below preferred bitrate');
    }
  }

  return { points, reasons };
};

export const rankSearchCandidate = ({
  acquisitionProfile = 'lossless-exact',
  communityQualitySummary,
  downloadStats,
  preferredConditions = {},
  response = {},
  searchText = '',
} = {}) => {
  const files = getFiles(response);
  const reasons = [];
  let score = 0;

  const queryMatch = scoreQueryMatch(files, searchText);
  score += queryMatch.points;
  if (queryMatch.reason) reasons.push(queryMatch.reason);

  const format = scoreFormat(files, acquisitionProfile);
  score += format.points;
  if (format.reason) reasons.push(format.reason);

  const size = scoreSizeSanity(files);
  score += size.points;
  if (size.reason) reasons.push(size.reason);

  const availability = scoreAvailability(response);
  score += availability.points;
  reasons.push(...availability.reasons);

  const history = scoreHistory(downloadStats);
  score += history.points;
  if (history.reason) reasons.push(history.reason);

  const provider = scoreProvider(response);
  score += provider.points;
  if (provider.reason) reasons.push(provider.reason);

  const qualitySignals = scoreCommunityQuality(communityQualitySummary);
  score += qualitySignals.points;
  if (qualitySignals.reason) reasons.push(qualitySignals.reason);

  const preferred = scorePreferredConditions(files, preferredConditions);
  score += preferred.points;
  reasons.push(...preferred.reasons);

  return {
    reasons: unique(reasons).slice(0, 9),
    score: clamp(Math.round(score), 0, 100),
  };
};

export const rankSearchResponses = ({
  acquisitionProfile = 'lossless-exact',
  communityQualityByUser = {},
  preferredConditions = {},
  responses = [],
  searchText = '',
  userStats = {},
} = {}) => {
  const albumConsensus = inferAlbumTrackConsensus(responses);

  return responses.map((response, responseIndex) => {
    const communityQualitySummary =
      communityQualityByUser[response.username] ||
      getCommunityQualitySummary(response.username);
    const downloadStats = userStats[response.username];
    const consensus = albumConsensus[responseIndex];
    const candidateRank = rankSearchCandidate({
      acquisitionProfile,
      communityQualitySummary,
      downloadStats,
      preferredConditions,
      response,
      searchText,
    });
    const consensusReason = consensus
      ? [`album track consensus ${consensus.score}/100 across ${consensus.peers} sources`]
      : [];
    const smartScore = consensus
      ? Math.round((candidateRank.score * 0.8) + (consensus.score * 0.2))
      : candidateRank.score;
    const rankedCandidate = {
      ...candidateRank,
      albumConsensusScore: consensus?.score ?? null,
      albumConsensusPeers: consensus?.peers ?? 0,
      canonicalTrackTitles: consensus?.canonicalTrackTitles ?? [],
      canonicalTrackCount: consensus?.canonicalTrackCount ?? 0,
      reasons: unique([...consensusReason, ...candidateRank.reasons]).slice(0, 9),
      score: smartScore,
    };

    return {
      ...response,
      albumConsensusScore: consensus?.score ?? null,
      candidateRank: rankedCandidate,
      communityQualitySummary,
      downloadStats,
      smartScore,
    };
  });
};
