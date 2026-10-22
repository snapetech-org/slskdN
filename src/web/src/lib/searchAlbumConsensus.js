// <copyright file="searchAlbumConsensus.js" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

const audioExtensions = new Set([
  'aac',
  'aif',
  'aiff',
  'alac',
  'ape',
  'flac',
  'm4a',
  'mp3',
  'ogg',
  'opus',
  'wav',
  'wma',
  'wv',
]);

const ignoredDirectoryTokens = new Set([
  '320',
  'aac',
  'audio',
  'flac',
  'lossless',
  'mp3',
  'music',
  'uploads',
]);

const ignoredTitleTokens = new Set([
  'audio',
  'official',
  'remaster',
  'remastered',
  'track',
]);

const MAX_ALBUM_CANDIDATES = 300;
const MAX_TRACKS_PER_ALBUM = 80;
const MIN_TRACKS_FOR_CONSENSUS = 3;
const MAX_TRACK_FILENAME_LENGTH = 2_048;
const MAX_DISPLAY_TITLE_LENGTH = 120;

const asArray = (value) => (Array.isArray(value) ? value : []);

const getWords = (value = '') =>
  String(value)
    .match(/[\p{L}\p{N}\p{M}]+/gu) || [];

const normalizeWord = (word) =>
  String(word)
    .normalize('NFKD')
    .replace(/\p{M}/gu, '')
    .toLowerCase();

const normalizeWords = (value = '') => getWords(value).map(normalizeWord);

const getExtension = (filename = '') => {
  const lastSegment = String(filename).split(/[\\/]/u).pop() || '';
  const index = lastSegment.lastIndexOf('.');
  return index >= 0 ? lastSegment.slice(index + 1).toLowerCase() : '';
};

const getDiscNumber = (directoryName = '') => {
  const match = String(directoryName).match(/^(?:cd|disc|disk)[\s._-]*0?(\d{1,2})$/iu);
  return match ? Number(match[1]) : null;
};

const parseTrackNumber = (basename, directoryDiscNumber) => {
  const discTrack = basename.match(/^(?:cd|disc|disk)[\s._-]*0?(\d{1,2})[\s._-]+0?(\d{1,3})[\s._-]+(.+)$/iu);
  if (discTrack) {
    return {
      disc: Number(discTrack[1]),
      number: Number(discTrack[2]),
      title: discTrack[3],
    };
  }

  const prefixedTrack = basename.match(/^(?:track[\s._-]*)?0?(\d{1,3})[\s._-]+(.+)$/iu);
  if (!prefixedTrack) {
    return { disc: directoryDiscNumber, number: null, title: basename };
  }

  return {
    disc: directoryDiscNumber,
    number: Number(prefixedTrack[1]),
    title: prefixedTrack[2],
  };
};

const getAlbumContext = (filename) => {
  const segments = String(filename).split(/[\\/]+/u).filter(Boolean);
  const directories = segments.slice(0, -1);
  const directoryDiscNumber = getDiscNumber(directories[directories.length - 1]);
  if (directoryDiscNumber !== null) {
    directories.pop();
  }

  const meaningfulDirectories = directories.filter((directory) =>
    !normalizeWords(directory).every((token) => ignoredDirectoryTokens.has(token)),
  );
  const relevantDirectories = meaningfulDirectories.slice(-2);
  const albumKey = normalizeWords(relevantDirectories.join(' '))
    .filter((token) => !ignoredDirectoryTokens.has(token))
    .join(' ');

  return {
    albumKey: albumKey || 'root',
    directoryDiscNumber,
    contextTokens: new Set(normalizeWords(relevantDirectories.join(' '))),
  };
};

const createTrack = (file, context) => {
  const filename = String(file?.filename || '');
  if (filename.length > MAX_TRACK_FILENAME_LENGTH) {
    return null;
  }

  const basename = filename.split(/[\\/]/u).pop() || '';
  const extension = getExtension(filename);
  if (!audioExtensions.has(extension)) {
    return null;
  }

  const withoutExtension = basename.slice(0, -(extension.length + 1));
  const parsed = parseTrackNumber(withoutExtension, context.directoryDiscNumber);
  const parsedTitleWords = getWords(parsed.title);
  const titleTokens = parsedTitleWords.map(normalizeWord).filter((token) =>
    !context.contextTokens.has(token) && !ignoredTitleTokens.has(token),
  );
  const title = titleTokens.join(' ') || normalizeWords(parsed.title).join(' ');
  if (!title) {
    return null;
  }

  const length = Number(file.length);
  const duration = Number.isFinite(length) && length >= 10 && length <= 7_200 ? length : null;
  const trackNumber = parsed.number === null
    ? null
    : ((parsed.disc || 0) * 1_000) + parsed.number;
  const displayTitle = parsedTitleWords
    .filter((token) => {
      const normalized = normalizeWord(token);
      return !context.contextTokens.has(normalized) && !ignoredTitleTokens.has(normalized);
    })
    .join(' ')
    .slice(0, MAX_DISPLAY_TITLE_LENGTH) || parsed.title.trim().slice(0, MAX_DISPLAY_TITLE_LENGTH);

  return {
    displayTitle,
    duration,
    number: trackNumber,
    title,
  };
};

const collectCandidates = (responses) => {
  const candidates = [];

  responses.forEach((response, responseIndex) => {
    if (candidates.length >= MAX_ALBUM_CANDIDATES) {
      return;
    }

    const files = [
      ...asArray(response?.files),
      ...asArray(response?.lockedFiles),
    ].slice(0, 2_000);
    const groups = new Map();

    files.forEach((file) => {
      const context = getAlbumContext(file?.filename);
      const track = createTrack(file, context);
      if (!track) {
        return;
      }

      if (!groups.has(context.albumKey)) {
        groups.set(context.albumKey, new Map());
      }

      const tracks = groups.get(context.albumKey);
      if (!tracks.has(track.title)) {
        tracks.set(track.title, track);
      } else {
        const existing = tracks.get(track.title);
        if (existing.duration === null && track.duration !== null) {
          tracks.set(track.title, { ...existing, duration: track.duration });
        }
      }
    });

    for (const [albumKey, trackMap] of groups) {
      const tracks = [...trackMap.values()].slice(0, MAX_TRACKS_PER_ALBUM);
      if (tracks.length < MIN_TRACKS_FOR_CONSENSUS) {
        continue;
      }

      candidates.push({
        albumKey,
        responseIndex,
        sourceKey: String(response?.username || `response-${responseIndex}`).toLowerCase(),
        tracks,
      });
      if (candidates.length >= MAX_ALBUM_CANDIDATES) {
        return candidates;
      }
    }
  });

  return candidates;
};

const getTrackMatches = (left, right) => {
  const rightTitles = new Set(right.tracks.map((track) => track.title));
  return left.tracks.filter((track) => rightTitles.has(track.title));
};

const getAlbumKeySimilarity = (left, right) => {
  const leftTokens = new Set(left.albumKey.split(' ').filter(Boolean));
  const rightTokens = new Set(right.albumKey.split(' ').filter(Boolean));
  if (leftTokens.size === 0 || rightTokens.size === 0) {
    return 0;
  }

  const shared = [...leftTokens].filter((token) => rightTokens.has(token)).length;
  return shared / new Set([...leftTokens, ...rightTokens]).size;
};

const areSimilarAlbums = (left, right) => {
  if (left.sourceKey === right.sourceKey) {
    return false;
  }

  const shared = getTrackMatches(left, right).length;
  if (shared < MIN_TRACKS_FOR_CONSENSUS) {
    return false;
  }

  const smallerCount = Math.min(left.tracks.length, right.tracks.length);
  const largerCount = Math.max(left.tracks.length, right.tracks.length);
  const containment = shared / smallerCount;
  const coverage = shared / largerCount;
  const albumSimilarity = getAlbumKeySimilarity(left, right);

  return (coverage >= 0.65 && shared >= 4) ||
    (albumSimilarity >= 0.8 && containment >= 0.8);
};

const buildClusters = (candidates) => {
  const parents = candidates.map((_, index) => index);
  const find = (index) => {
    if (parents[index] !== index) {
      parents[index] = find(parents[index]);
    }
    return parents[index];
  };
  const join = (left, right) => {
    const leftRoot = find(left);
    const rightRoot = find(right);
    if (leftRoot !== rightRoot) {
      parents[rightRoot] = leftRoot;
    }
  };

  for (let left = 0; left < candidates.length; left += 1) {
    for (let right = left + 1; right < candidates.length; right += 1) {
      if (areSimilarAlbums(candidates[left], candidates[right])) {
        join(left, right);
      }
    }
  }

  const clusters = new Map();
  candidates.forEach((candidate, index) => {
    const root = find(index);
    if (!clusters.has(root)) {
      clusters.set(root, []);
    }
    clusters.get(root).push(candidate);
  });
  return [...clusters.values()];
};

const selectSourceCandidates = (cluster) => {
  const bySource = new Map();
  cluster.forEach((candidate) => {
    if (!bySource.has(candidate.sourceKey)) {
      bySource.set(candidate.sourceKey, []);
    }
    bySource.get(candidate.sourceKey).push(candidate);
  });

  return [...bySource.values()].map((sourceCandidates) => {
    const ranked = sourceCandidates.map((candidate) => ({
      candidate,
      support: cluster.filter((other) =>
        other.sourceKey !== candidate.sourceKey && areSimilarAlbums(candidate, other),
      ).length,
    }));
    ranked.sort((left, right) =>
      (right.support - left.support) ||
      (right.candidate.tracks.length - left.candidate.tracks.length),
    );
    return ranked[0].candidate;
  });
};

const getCanonicalTracks = (sourceCandidates) => {
  const sourceCount = sourceCandidates.length;
  // With two sources, use their union so a complete release can outrank a
  // partial copy. Larger clusters use a strict majority to filter one-off noise.
  const requiredVotes = sourceCount === 2 ? 1 : Math.floor(sourceCount / 2) + 1;
  const votes = new Map();

  sourceCandidates.forEach((candidate) => {
    candidate.tracks.forEach((track) => {
      if (!votes.has(track.title)) {
        votes.set(track.title, {
          displayTitles: [],
          durations: [],
          numbers: [],
          sources: new Set(),
        });
      }

      const vote = votes.get(track.title);
      vote.sources.add(candidate.sourceKey);
      vote.displayTitles.push(track.displayTitle);
      if (track.duration !== null) {
        vote.durations.push(track.duration);
      }
      if (track.number !== null) {
        vote.numbers.push(track.number);
      }
    });
  });

  const median = (values) => {
    const sorted = [...values].sort((left, right) => left - right);
    if (sorted.length === 0) {
      return null;
    }
    const middle = Math.floor(sorted.length / 2);
    return sorted.length % 2 === 0
      ? (sorted[middle - 1] + sorted[middle]) / 2
      : sorted[middle];
  };

  return [...votes.entries()]
    .filter(([, vote]) => vote.sources.size >= requiredVotes)
    .map(([title, vote]) => ({
      duration: median(vote.durations),
      displayTitle: vote.displayTitles[0] || title,
      number: median(vote.numbers),
      title,
    }))
    .sort((left, right) => {
      if (left.number !== null && right.number !== null) {
        return left.number - right.number;
      }
      if (left.number !== null) return -1;
      if (right.number !== null) return 1;
      return left.title.localeCompare(right.title);
    });
};

const getOrderScore = (candidate, canonicalTracks, matchedTitles) => {
  const orderedCandidate = candidate.tracks
    .filter((track) => matchedTitles.has(track.title) && track.number !== null)
    .sort((left, right) => left.number - right.number);
  const canonicalOrder = new Map(
    canonicalTracks.map((track, index) => [track.title, index]),
  );
  const orderedCanonicalIndexes = orderedCandidate
    .map((track) => canonicalOrder.get(track.title))
    .filter((index) => index !== undefined);

  if (orderedCanonicalIndexes.length < 2) {
    return null;
  }

  let orderedPairs = 0;
  let pairCount = 0;
  for (let left = 0; left < orderedCanonicalIndexes.length; left += 1) {
    for (let right = left + 1; right < orderedCanonicalIndexes.length; right += 1) {
      pairCount += 1;
      if (orderedCanonicalIndexes[left] < orderedCanonicalIndexes[right]) {
        orderedPairs += 1;
      }
    }
  }

  return pairCount === 0 ? null : orderedPairs / pairCount;
};

const scoreCandidate = (candidate, canonicalTracks) => {
  const canonicalTitles = new Set(canonicalTracks.map((track) => track.title));
  const matchedTracks = candidate.tracks.filter((track) => canonicalTitles.has(track.title));
  const matchedTitles = new Set(matchedTracks.map((track) => track.title));
  if (matchedTitles.size < MIN_TRACKS_FOR_CONSENSUS) {
    return null;
  }

  const coverage = matchedTitles.size / canonicalTracks.length;
  const precision = matchedTitles.size / Math.max(candidate.tracks.length, canonicalTracks.length);
  const orderScore = getOrderScore(candidate, canonicalTracks, matchedTitles);
  const canonicalByTitle = new Map(canonicalTracks.map((track) => [track.title, track]));
  const durationMatches = matchedTracks
    .map((track) => ({ actual: track.duration, expected: canonicalByTitle.get(track.title)?.duration }))
    .filter((match) => match.actual !== null && match.expected !== null);
  const durationScore = durationMatches.length < MIN_TRACKS_FOR_CONSENSUS
    ? null
    : durationMatches.reduce((sum, match) => {
      const largest = Math.max(match.actual, match.expected);
      return sum + (largest === 0 ? 1 : 1 - (Math.abs(match.actual - match.expected) / largest));
    }, 0) / durationMatches.length;

  const weightedScores = [
    { score: coverage, weight: 0.6 },
    { score: precision, weight: 0.2 },
  ];
  if (orderScore !== null) {
    weightedScores.push({ score: orderScore, weight: 0.12 });
  }
  if (durationScore !== null) {
    weightedScores.push({ score: durationScore, weight: 0.08 });
  }

  const totalWeight = weightedScores.reduce((sum, entry) => sum + entry.weight, 0);
  const score = weightedScores.reduce((sum, entry) => sum + (entry.score * entry.weight), 0) / totalWeight;
  return Math.max(0, Math.min(100, Math.round(score * 100)));
};

export const inferAlbumTrackConsensus = (responses = []) => {
  const results = asArray(responses).map(() => null);
  const candidates = collectCandidates(asArray(responses));
  if (candidates.length < 2) {
    return results;
  }

  for (const cluster of buildClusters(candidates)) {
    const sourceCandidates = selectSourceCandidates(cluster);
    if (sourceCandidates.length < 2) {
      continue;
    }

    const canonicalTracks = getCanonicalTracks(sourceCandidates);
    if (canonicalTracks.length < MIN_TRACKS_FOR_CONSENSUS) {
      continue;
    }

    for (const candidate of cluster) {
      const score = scoreCandidate(candidate, canonicalTracks);
      if (score === null) {
        continue;
      }

      const current = results[candidate.responseIndex];
      if (!current || score > current.score) {
        results[candidate.responseIndex] = {
          canonicalTrackTitles: canonicalTracks.map((track) => track.displayTitle),
          canonicalTrackCount: canonicalTracks.length,
          peers: sourceCandidates.length,
          score,
        };
      }
    }
  }

  return results;
};
