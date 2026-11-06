// <copyright file="playlistIntake.js" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import { getLocalStorageItem, setLocalStorageItem } from './storage';
import { scoreMetadataCandidate } from './metadataMatcher';
import { interfaceText } from './interfaceLocale';
import { formatRegionalNumber } from './regionalFormat';
import { v4 as uuidv4 } from 'uuid';

export const playlistIntakeStorageKey = 'slskdn.playlistIntake.items';
export const playlistRefreshCadences = ['Manual review', 'Daily', 'Weekly', 'Monthly'];

export const organizationPathTemplates = [
  {
    key: 'artist-album-track-title',
    text: 'Artist / Album / 01 - Title',
    value: '{artist}/{album}/{trackNumber} - {title}',
  },
  {
    key: 'album-track-artist-title',
    text: 'Album / 01 - Artist - Title',
    value: '{album}/{trackNumber} - {artist} - {title}',
  },
  {
    key: 'playlist-track-artist-title',
    text: 'Playlist / 01 - Artist - Title',
    value: '{playlist}/{trackNumber} - {artist} - {title}',
  },
];

export const multiArtistTagPolicies = [
  {
    key: 'preserve',
    text: 'Preserve source text',
    value: 'preserve',
  },
  {
    key: 'split',
    text: 'Split on common separators',
    value: 'split',
  },
  {
    key: 'primary',
    text: 'Use primary artist',
    value: 'primary',
  },
];

export const coverArtPolicies = [
  {
    key: 'sidecar',
    text: 'Write sidecar cover file',
    value: 'sidecar',
  },
  {
    key: 'embed',
    text: 'Embed cover art',
    value: 'embed',
  },
  {
    key: 'skip',
    text: 'Do not change cover art',
    value: 'skip',
  },
];

export const replayGainPolicies = [
  {
    key: 'skip',
    text: 'Do not run ReplayGain',
    value: 'skip',
  },
  {
    key: 'album',
    text: 'Album ReplayGain after import',
    value: 'album',
  },
  {
    key: 'track',
    text: 'Track ReplayGain after import',
    value: 'track',
  },
];

const now = () => new Date().toISOString();

const isPlainObject = (value) =>
  value && typeof value === 'object' && !Array.isArray(value);

const normalizeState = (state) =>
  ['Imported', 'Mirrored', 'Rejected'].includes(state) ? state : 'Staged';

const inferProvider = (source = '') => {
  const lower = source.toLowerCase();
  if (lower.includes('youtube') || lower.includes('youtu.be')) return 'YouTube';
  if (lower.includes('spotify')) return 'Spotify';
  if (lower.includes('listenbrainz')) return 'ListenBrainz';
  if (lower.includes('m3u')) return 'M3U';
  if (lower.includes('csv')) return 'CSV';
  return source.startsWith('http') ? 'Provider URL' : 'Local text';
};

const normalizeRefreshCadence = (cadence, mirrorEnabled) => {
  if (!mirrorEnabled) return 'Disabled';
  return playlistRefreshCadences.includes(cadence) ? cadence : 'Manual review';
};

const normalizeCooldownDays = (days) => {
  const parsed = Number.parseInt(days, 10);
  if (Number.isNaN(parsed)) return 7;
  return Math.min(Math.max(parsed, 1), 90);
};

const normalizeOptionValue = (value, options, fallback) =>
  options.some((option) => option.value === value) ? value : fallback;

const normalizeOrganizationOptions = (options = {}) => {
  const safeOptions = isPlainObject(options) ? options : {};
  return {
    albumTitle: safeOptions.albumTitle || '',
    coverArtPolicy: normalizeOptionValue(safeOptions.coverArtPolicy, coverArtPolicies, 'sidecar'),
    multiArtistPolicy: normalizeOptionValue(
      safeOptions.multiArtistPolicy,
      multiArtistTagPolicies,
      'preserve',
    ),
    pathTemplate: normalizeOptionValue(
      safeOptions.pathTemplate,
      organizationPathTemplates,
      organizationPathTemplates[0].value,
    ),
    replayGainPolicy: normalizeOptionValue(
      safeOptions.replayGainPolicy,
      replayGainPolicies,
      'skip',
    ),
  };
};

const addDays = (timestamp, days) =>
  new Date(new Date(timestamp).getTime() + days * 24 * 60 * 60 * 1_000).toISOString();

const calculateNextRefreshAt = (playlist, timestamp = now()) => {
  if (!playlist.mirrorEnabled || !playlist.refreshAutomationEnabled) return '';
  return addDays(timestamp, normalizeCooldownDays(playlist.refreshCooldownDays));
};

const parseCsvLine = (line) => {
  const columns = line.split(',').map((column) => column.trim().replace(/^"|"$/g, ''));
  return {
    artist: columns[0] || '',
    title: columns[1] || columns[0] || '',
  };
};

const parseTextLine = (line) => {
  const [artist, title] = line.includes(' - ')
    ? line.split(' - ', 2).map((part) => part.trim())
    : ['', line.trim()];

  return {
    artist,
    title,
  };
};

const parsePlaylistRows = (content = '') => {
  const rows = content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith('#'));

  return rows.map((line, index) => {
    const parsed = line.includes(',') ? parseCsvLine(line) : parseTextLine(line);
    const title = parsed.title || line;

    return {
      artist: parsed.artist,
      id: uuidv4(),
      lineNumber: index + 1,
      sourceLine: line,
      state: parsed.artist && title ? 'Matched' : 'Unmatched',
      title,
    };
  });
};

const normalizeTrack = (track = {}, index = 0) => ({
  artist: track.artist || '',
  contentId: track.contentId || '',
  durationMs: track.durationMs || null,
  id: track.id || uuidv4(),
  lineNumber: track.lineNumber || index + 1,
  metadataMatch: track.metadataMatch || null,
  sourceLine: track.sourceLine || track.title || '',
  state: ['Matched', 'Rejected', 'Unmatched'].includes(track.state)
    ? track.state
    : 'Unmatched',
  title: track.title || track.sourceLine || 'Untitled track',
});

const normalizePlaylist = (playlist = {}) => {
  const timestamp = now();
  const tracks = Array.isArray(playlist.tracks)
    ? playlist.tracks
      .filter(isPlainObject)
      .map(normalizeTrack)
    : parsePlaylistRows(playlist.content);

  return {
    createdAt: playlist.createdAt || timestamp,
    id: playlist.id || uuidv4(),
    mirrorEnabled: playlist.mirrorEnabled === true,
    name: playlist.name || 'Untitled playlist',
    organizationApproval: playlist.organizationApproval || null,
    organizationOptions: normalizeOrganizationOptions(playlist.organizationOptions),
    organizationPlan: playlist.organizationPlan || null,
    provider: playlist.provider || inferProvider(playlist.source || playlist.name || ''),
    providerRefreshLimit: Math.min(
      Math.max(Number.parseInt(playlist.providerRefreshLimit, 10) || 500, 1),
      5_000,
    ),
    refreshAutomationEnabled:
      playlist.mirrorEnabled === true && playlist.refreshAutomationEnabled === true,
    refreshCadence: normalizeRefreshCadence(
      playlist.refreshCadence,
      playlist.mirrorEnabled === true,
    ),
    refreshCollectionId: playlist.refreshCollectionId || '',
    refreshCooldownDays: normalizeCooldownDays(playlist.refreshCooldownDays),
    refreshDiff: playlist.refreshDiff || null,
    refreshLastRunAt: playlist.refreshLastRunAt || '',
    refreshNextRunAt: playlist.refreshNextRunAt || '',
    refreshPreview:
      playlist.refreshPreview ||
      'Refresh preview only; no provider fetch, Soulseek search, peer browse, or download has started.',
    source: playlist.source || 'Pasted text',
    state: normalizeState(playlist.state),
    tracks,
    updatedAt: playlist.updatedAt || timestamp,
  };
};

const readPlaylists = (getItem = getLocalStorageItem) => {
  try {
    const parsed = JSON.parse(getItem(playlistIntakeStorageKey, '[]'));
    return Array.isArray(parsed)
      ? parsed.filter(isPlainObject).map(normalizePlaylist)
      : [];
  } catch {
    return [];
  }
};

const savePlaylists = (playlists, setItem = setLocalStorageItem) => {
  const normalized = playlists.filter(isPlainObject).map(normalizePlaylist);
  setItem(playlistIntakeStorageKey, JSON.stringify(normalized));
  return normalized;
};

export const getPlaylistIntakes = () => readPlaylists();

export const addPlaylistIntake = (
  playlist,
  {
    getItem = getLocalStorageItem,
    setItem = setLocalStorageItem,
  } = {},
) => {
  const next = normalizePlaylist(playlist);
  const existing = readPlaylists(getItem).filter(
    (item) => item.source.toLowerCase() !== next.source.toLowerCase(),
  );

  return savePlaylists([next, ...existing], setItem);
};

const getTrackKey = (track) =>
  [track.artist, track.title]
    .filter(Boolean)
    .join('|')
    .trim()
    .toLowerCase();

export const buildPlaylistCompletionSummary = (playlist) =>
  playlist.tracks.reduce(
    (summary, track) => ({
      ...summary,
      [track.state]: (summary[track.state] || 0) + 1,
      total: summary.total + 1,
    }),
    {
      Matched: 0,
      Rejected: 0,
      Unmatched: 0,
      total: 0,
    },
  );

export const buildPlaylistRefreshDiff = (playlist, content = '') => {
  const existing = new Map(playlist.tracks.map((track) => [getTrackKey(track), track]));
  const incoming = parsePlaylistRows(content);
  const incomingKeys = new Set(incoming.map(getTrackKey));
  const added = incoming.filter((track) => !existing.has(getTrackKey(track)));
  const removed = playlist.tracks.filter((track) => !incomingKeys.has(getTrackKey(track)));
  const unchanged = incoming.filter((track) => existing.has(getTrackKey(track)));
  const changed = incoming
    .map((track, index) => {
      const previous = playlist.tracks[index];
      return previous && getTrackKey(previous) !== getTrackKey(track)
        ? {
            incoming: track,
            lineNumber: index + 1,
            previous,
          }
        : null;
    })
    .filter(Boolean);

  return {
    added,
    addedCount: added.length,
    changed,
    changedCount: changed.length,
    removed,
    removedCount: removed.length,
    totalIncoming: incoming.length,
    unchangedCount: unchanged.length,
  };
};

export const updatePlaylistIntakeTrackState = (
  playlistId,
  trackId,
  state,
  {
    getItem = getLocalStorageItem,
    setItem = setLocalStorageItem,
  } = {},
) => {
  const nextState = ['Matched', 'Rejected'].includes(state) ? state : 'Unmatched';
  const updated = readPlaylists(getItem).map((playlist) =>
    playlist.id === playlistId
      ? {
          ...playlist,
          tracks: playlist.tracks.map((track) =>
            track.id === trackId ? { ...track, state: nextState } : track,
          ),
          updatedAt: now(),
        }
      : playlist,
  );

  return savePlaylists(updated, setItem);
};

export const updatePlaylistRefreshAutomation = (
  playlistId,
  {
    enabled,
    cadence,
    cooldownDays,
    providerRefreshLimit,
  },
  {
    getItem = getLocalStorageItem,
    setItem = setLocalStorageItem,
  } = {},
) => {
  const timestamp = now();
  const updated = readPlaylists(getItem).map((playlist) => {
    if (playlist.id !== playlistId) {
      return playlist;
    }

    const next = {
      ...playlist,
      providerRefreshLimit:
        providerRefreshLimit === undefined
          ? playlist.providerRefreshLimit
          : providerRefreshLimit,
      refreshAutomationEnabled: enabled === true,
      refreshCadence: cadence || playlist.refreshCadence,
      refreshCooldownDays:
        cooldownDays === undefined ? playlist.refreshCooldownDays : cooldownDays,
      updatedAt: timestamp,
    };

    return {
      ...next,
      refreshNextRunAt: calculateNextRefreshAt(next, timestamp),
    };
  });

  return savePlaylists(updated, setItem);
};

export const previewPlaylistIntakeRefresh = (
  playlistId,
  content,
  {
    getItem = getLocalStorageItem,
    setItem = setLocalStorageItem,
  } = {},
) => {
  const updated = readPlaylists(getItem).map((playlist) => {
    if (playlist.id !== playlistId) {
      return playlist;
    }

    const refreshDiff = buildPlaylistRefreshDiff(playlist, content);

    return {
      ...playlist,
      refreshDiff,
      refreshPreview:
        `Refresh diff preview only: ${refreshDiff.addedCount} added, ${refreshDiff.removedCount} removed, ${refreshDiff.changedCount} changed, ${refreshDiff.unchangedCount} unchanged. No provider fetch, Soulseek search, peer browse, download, or playlist mutation has started.`,
      updatedAt: now(),
    };
  });

  return savePlaylists(updated, setItem);
};

export const applyPlaylistIntakeRefresh = (
  playlistId,
  content,
  {
    getItem = getLocalStorageItem,
    setItem = setLocalStorageItem,
    sourceLabel = 'manual refresh',
  } = {},
) => {
  const timestamp = now();
  const updated = readPlaylists(getItem).map((playlist) => {
    if (playlist.id !== playlistId) {
      return playlist;
    }

    const previousByKey = new Map(
      playlist.tracks.map((track) => [getTrackKey(track), track]),
    );
    const incoming = parsePlaylistRows(content).map((track) => {
      const previous = previousByKey.get(getTrackKey(track));
      return previous
        ? {
            ...track,
            id: previous.id,
            state: previous.state,
          }
        : track;
    });
    const refreshDiff = buildPlaylistRefreshDiff(playlist, content);
    const next = {
      ...playlist,
      refreshDiff,
      refreshLastRunAt: timestamp,
      refreshPreview:
        `Applied ${sourceLabel}: ${refreshDiff.addedCount} added, ${refreshDiff.removedCount} removed, ${refreshDiff.changedCount} changed, ${refreshDiff.unchangedCount} unchanged. No Soulseek search, peer browse, or download was started.`,
      state: 'Mirrored',
      tracks: incoming,
      updatedAt: timestamp,
    };

    return {
      ...next,
      refreshNextRunAt: calculateNextRefreshAt(next, timestamp),
    };
  });

  return savePlaylists(updated, setItem);
};

export const markPlaylistCollectionCreated = (
  playlistId,
  collectionId,
  {
    getItem = getLocalStorageItem,
    setItem = setLocalStorageItem,
  } = {},
) => {
  const updated = readPlaylists(getItem).map((playlist) =>
    playlist.id === playlistId
      ? {
          ...playlist,
          refreshCollectionId: collectionId || playlist.refreshCollectionId,
          state: 'Imported',
          updatedAt: now(),
        }
      : playlist,
  );

  return savePlaylists(updated, setItem);
};

export const buildPlaylistIntakeSummary = (playlists = []) =>
  playlists.reduce(
    (summary, playlist) => {
      const unmatched = playlist.tracks.filter(
        (track) => track.state === 'Unmatched',
      ).length;

      return {
        ...summary,
        mirrored: playlist.mirrorEnabled ? summary.mirrored + 1 : summary.mirrored,
        total: summary.total + 1,
        tracks: summary.tracks + playlist.tracks.length,
        unmatched: summary.unmatched + unmatched,
      };
    },
    {
      mirrored: 0,
      total: 0,
      tracks: 0,
      unmatched: 0,
    },
  );

export const buildPlaylistDiscoverySeed = (playlist, track) => ({
  evidenceKey: `playlist:${playlist.id}:${track.lineNumber}:${track.title}`.toLowerCase(),
  networkImpact:
    'Playlist intake review seed only; no provider fetch, Soulseek search, peer browse, or download has started.',
  reason: `Imported from ${playlist.name} (${playlist.provider}) line ${track.lineNumber}.`,
  searchText: [track.artist, track.title].filter(Boolean).join(' '),
  source: 'Playlist Intake',
  sourceId: playlist.id,
  title: [track.artist, track.title].filter(Boolean).join(' - ') || track.title,
});

export const buildPlaylistDiscoverySeeds = (playlist) =>
  playlist.tracks
    .filter((track) => track.state !== 'Rejected')
    .map((track) => buildPlaylistDiscoverySeed(playlist, track));

export const buildSlskdPlaylistPreview = (playlist) => {
  const completion = buildPlaylistCompletionSummary(playlist);
  const tracks = playlist.tracks.filter((track) => track.state === 'Matched');
  const lines = tracks.map(
    (track, index) =>
      `${index + 1}. ${[track.artist, track.title].filter(Boolean).join(' - ') || track.title}`,
  );

  return {
    completion,
    lineCount: lines.length,
    lines,
    name: playlist.name,
    networkImpact:
      'Playlist build preview only; creating it writes a playlist Collection locally and does not search Soulseek, browse peers, or download.',
    text: [`# ${playlist.name}`, ...lines].join('\n'),
  };
};

export const getDuePlaylistRefreshes = (
  playlists = readPlaylists(),
  timestamp = Date.now(),
) =>
  playlists.filter((playlist) => {
    if (!playlist.mirrorEnabled || !playlist.refreshAutomationEnabled) return false;
    if (!playlist.refreshNextRunAt) return true;

    const dueAt = Date.parse(playlist.refreshNextRunAt);
    return Number.isNaN(dueAt) || dueAt <= timestamp;
  });

export const buildPlaylistProviderRefreshContent = (result = {}) =>
  (Array.isArray(result.suggestions) ? result.suggestions : [])
    .map((suggestion) =>
      [suggestion.artist, suggestion.title || suggestion.searchText]
        .filter(Boolean)
        .join(' - '),
    )
    .filter(Boolean)
    .join('\n');

export const buildPlaylistCollectionItems = (playlist) =>
  playlist.tracks
    .filter((track) => track.state === 'Matched')
    .map((track) => ({
      album: track.album || playlist.title || '',
      artist: track.artist || '',
      contentId:
        track.contentId || `playlist-intake:${playlist.id}:${track.lineNumber}:${track.id}`,
      fileName: [track.artist, playlist.title, track.title || track.searchText]
        .filter(Boolean)
        .join(' - '),
      mediaKind: 'PlannedTrack',
      title: track.title || track.searchText || '',
    }));

const sanitizePathPart = (value, fallback = 'Unknown') => {
  const text = `${value || fallback}`
    .split('')
    .filter((character) => character.charCodeAt(0) >= 32)
    .join('')
    .replace(/[<>:"\\|?*]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  return text || fallback;
};

const formatTrackNumber = (track, index, total) => {
  const width = total >= 100 ? 3 : 2;
  return `${track.trackNumber || index + 1}`.padStart(width, '0');
};

const splitArtists = (artist = '') =>
  artist
    .split(/\s+(?:&|and|feat\.?|featuring|\+)\s+|,\s*/i)
    .map((part) => part.trim())
    .filter(Boolean);

const applyMultiArtistPolicy = (artist, policy) => {
  const artists = splitArtists(artist);
  if (policy === 'split') {
    return artists.length > 0 ? artists : [artist || 'Unknown Artist'];
  }

  if (policy === 'primary') {
    return artists[0] || artist || 'Unknown Artist';
  }

  return artist || 'Unknown Artist';
};

const renderOrganizationPath = (template, values) => {
  const rendered = template.replace(/\{(artist|album|playlist|title|trackNumber)\}/g, (
    _match,
    key,
  ) => sanitizePathPart(values[key], key));

  return `${rendered}.flac`.replace(/\/+/g, '/');
};

export const buildPlaylistTagOrganizationPlan = (
  playlist,
  options = {},
) => {
  const normalizedOptions = normalizeOrganizationOptions({
    ...playlist.organizationOptions,
    ...options,
  });
  const albumTitle =
    normalizedOptions.albumTitle.trim() || playlist.name || 'Playlist Intake';
  const reviewableTracks = playlist.tracks.filter((track) => track.state !== 'Rejected');
  const matchedTracks = reviewableTracks.filter((track) => track.state === 'Matched');
  const skippedTracks = reviewableTracks.filter((track) => track.state !== 'Matched');
  const generatedAt = now();
  const trackPreviews = matchedTracks.map((track, index) => {
    const trackNumber = formatTrackNumber(track, index, matchedTracks.length);
    const artistTag = applyMultiArtistPolicy(
      track.artist,
      normalizedOptions.multiArtistPolicy,
    );
    const tagPreview = {
      album: albumTitle,
      artist: artistTag,
      title: track.title,
      trackNumber,
    };
    const destinationPath = renderOrganizationPath(normalizedOptions.pathTemplate, {
      album: albumTitle,
      artist: Array.isArray(artistTag) ? artistTag.join('; ') : artistTag,
      playlist: playlist.name,
      title: track.title,
      trackNumber,
    });

    return {
      changedFields: ['artist', 'title', 'album', 'trackNumber'],
      destinationPath,
      lineNumber: track.lineNumber,
      metadataSnapshot: {
        proposed: tagPreview,
        source: {
          album: track.album || '',
          artist: track.artist || '',
          title: track.title || track.sourceLine || '',
          trackNumber: track.trackNumber || '',
        },
      },
      sourceLine: track.sourceLine,
      tagPreview,
      trackId: track.id,
      warnings: [
        !track.artist ? 'Artist is missing; using Unknown Artist for preview.' : '',
        !track.title ? 'Title is missing; using source line for preview.' : '',
      ].filter(Boolean),
    };
  });

  return {
    coverArtAction:
      normalizedOptions.coverArtPolicy === 'skip'
        ? 'Cover art will not be changed.'
        : normalizedOptions.coverArtPolicy === 'embed'
          ? 'Cover art would be embedded after explicit import approval.'
          : 'A sidecar cover file would be written after explicit import approval.',
    generatedAt,
    networkImpact:
      'Tag and organization dry run only; no tag write, cover-art write, ReplayGain run, file move, provider lookup, Soulseek search, peer browse, or download has started.',
    options: {
      ...normalizedOptions,
      albumTitle,
    },
    replayGainAction:
      normalizedOptions.replayGainPolicy === 'skip'
        ? 'ReplayGain will not run.'
        : `${normalizedOptions.replayGainPolicy === 'album' ? 'Album' : 'Track'} ReplayGain would run after explicit import approval.`,
    skippedTracks: skippedTracks.map((track) => ({
      reason: `${track.state} rows are not included in tag-write previews.`,
      title: [track.artist, track.title].filter(Boolean).join(' - ') || track.title,
      trackId: track.id,
    })),
    summary: {
      changedFieldCount: trackPreviews.reduce(
        (total, preview) => total + preview.changedFields.length,
        0,
      ),
      matched: matchedTracks.length,
      skipped: skippedTracks.length,
      total: reviewableTracks.length,
    },
    trackPreviews,
  };
};

export const previewPlaylistTagOrganizationPlan = (
  playlistId,
  options = {},
  {
    getItem = getLocalStorageItem,
    setItem = setLocalStorageItem,
  } = {},
) => {
  const updated = readPlaylists(getItem).map((playlist) => {
    if (playlist.id !== playlistId) {
      return playlist;
    }

    const organizationPlan = buildPlaylistTagOrganizationPlan(playlist, options);

    return {
      ...playlist,
      organizationOptions: organizationPlan.options,
      organizationPlan,
      updatedAt: now(),
    };
  });

  return savePlaylists(updated, setItem);
};

export const getPlaylistCoverArtActionSource = (action) => {
  switch (action) {
    case 'Cover art will not be changed.':
    case 'Cover art would be embedded after explicit import approval.':
    case 'A sidecar cover file would be written after explicit import approval.':
      return action;
    default:
      return '';
  }
};

export const getPlaylistReplayGainActionPresentation = (action) => {
  if (action === 'ReplayGain will not run.') {
    return { source: action, values: {} };
  }
  const match = /^(Album|Track) ReplayGain would run after explicit import approval\.$/.exec(action || '');
  if (match) {
    return {
      source: '{scope} ReplayGain would run after explicit import approval.',
      values: { scope: match[1] === 'Album' ? interfaceText('Album') : interfaceText('Track') },
    };
  }
  return undefined;
};

export const getPlaylistNetworkImpactSource = (impact) =>
  impact === 'Tag and organization dry run only; no tag write, cover-art write, ReplayGain run, file move, provider lookup, Soulseek search, peer browse, or download has started.'
    ? impact
    : '';

export const getPlaylistChangedFieldSource = (field) => {
  switch (field) {
    case 'artist':
      return 'Artist';
    case 'title':
      return 'Title';
    case 'album':
      return 'Album';
    case 'trackNumber':
      return 'Track number';
    default:
      return '';
  }
};

export const getPlaylistSkippedReasonSource = (reason) =>
  reason === 'Unmatched rows are not included in tag-write previews.' ? reason : '';

const localizePlaylistCoverArtAction = (action) => {
  switch (action) {
    case 'Cover art will not be changed.':
      return interfaceText('Cover art will not be changed.');
    case 'Cover art would be embedded after explicit import approval.':
      return interfaceText('Cover art would be embedded after explicit import approval.');
    case 'A sidecar cover file would be written after explicit import approval.':
      return interfaceText('A sidecar cover file would be written after explicit import approval.');
    default:
      return action;
  }
};

const localizePlaylistReplayGainAction = (action) => {
  if (action === 'ReplayGain will not run.') {
    return interfaceText('ReplayGain will not run.');
  }
  const match = /^(Album|Track) ReplayGain would run after explicit import approval\.$/.exec(action || '');
  if (match) {
    const scope = match[1] === 'Album' ? interfaceText('Album') : interfaceText('Track');
    return interfaceText('{scope} ReplayGain would run after explicit import approval.', { scope });
  }
  return action;
};

const localizePlaylistNetworkImpact = (impact) => {
  if (impact === 'Tag and organization dry run only; no tag write, cover-art write, ReplayGain run, file move, provider lookup, Soulseek search, peer browse, or download has started.') {
    return interfaceText('Tag and organization dry run only; no tag write, cover-art write, ReplayGain run, file move, provider lookup, Soulseek search, peer browse, or download has started.');
  }
  return impact;
};

const localizePlaylistChangedField = (field) => {
  switch (field) {
    case 'artist':
      return interfaceText('Artist');
    case 'title':
      return interfaceText('Title');
    case 'album':
      return interfaceText('Album');
    case 'trackNumber':
      return interfaceText('Track number');
    default:
      return field;
  }
};

const localizePlaylistSkippedReason = (reason) => {
  if (reason === 'Unmatched rows are not included in tag-write previews.') {
    return interfaceText('Unmatched rows are not included in tag-write previews.');
  }
  return reason;
};

export const formatPlaylistTagOrganizationReport = (
  playlist,
  plan = playlist.organizationPlan,
) => {
  if (!plan) {
    return [
      interfaceText('slskdN tag and organization dry run'),
      interfaceText('Playlist: {name}', { name: playlist.name }),
      interfaceText('No dry-run plan has been prepared.'),
    ].join('\n');
  }

  const policyLabel = (value) => {
    switch (value) {
      case 'preserve':
        return interfaceText('Preserve source text');
      case 'split':
        return interfaceText('Split on common separators');
      case 'primary':
        return interfaceText('Use primary artist');
      default:
        return value;
    }
  };
  const lines = [
    interfaceText('slskdN tag and organization dry run'),
    interfaceText('Playlist: {name}', { name: playlist.name }),
    interfaceText('Generated: {timestamp}', { timestamp: plan.generatedAt }),
    interfaceText('Album title: {title}', { title: plan.options.albumTitle }),
    interfaceText('Path template: {template}', { template: plan.options.pathTemplate }),
    interfaceText('Multi-artist policy: {policy}', {
      policy: policyLabel(plan.options.multiArtistPolicy),
    }),
    interfaceText('Cover art: {action}', { action: localizePlaylistCoverArtAction(plan.coverArtAction) }),
    interfaceText('ReplayGain: {action}', { action: localizePlaylistReplayGainAction(plan.replayGainAction) }),
    interfaceText('Summary: {matched} matched, {skipped} skipped, {changed} changed fields', {
      changed: formatRegionalNumber(plan.summary.changedFieldCount),
      matched: formatRegionalNumber(plan.summary.matched),
      skipped: formatRegionalNumber(plan.summary.skipped),
    }),
    interfaceText('Impact: {impact}', { impact: localizePlaylistNetworkImpact(plan.networkImpact) }),
    '',
    interfaceText('Track previews:'),
    ...plan.trackPreviews.map((preview) => {
      const source = preview.metadataSnapshot?.source || {};
      const proposed = preview.metadataSnapshot?.proposed || {};
      return [
        interfaceText('- Line {line}: {path}', {
          line: formatRegionalNumber(preview.lineNumber),
          path: preview.destinationPath,
        }),
        interfaceText('  Changed: {fields}', {
          fields: preview.changedFields.map(localizePlaylistChangedField).join(', '),
        }),
        interfaceText('  Source metadata: Artist: {artist} | Title: {title} | Album: {album} | Track number: {trackNumber}', {
          album: source.album || '-',
          artist: source.artist || '-',
          title: source.title || '-',
          trackNumber: source.trackNumber || '-',
        }),
        interfaceText('  Proposed tags: Artist: {artist} | Title: {title} | Album: {album} | Track number: {trackNumber}', {
          album: proposed.album || '-',
          artist: Array.isArray(proposed.artist) ? proposed.artist.join('; ') : proposed.artist || '-',
          title: proposed.title || '-',
          trackNumber: proposed.trackNumber || '-',
        }),
      ].join('\n');
    }),
  ];

  if (plan.skippedTracks.length > 0) {
    lines.push('', interfaceText('Skipped rows:'));
    lines.push(
      ...plan.skippedTracks.map((track) => interfaceText('- {title}: {reason}', {
        reason: localizePlaylistSkippedReason(track.reason),
        title: track.title,
      })),
    );
  }

  lines.push(
    '',
    interfaceText('No tag write, cover-art write, ReplayGain run, file move, provider lookup, Soulseek search, peer browse, or download was started by this report.'),
  );

  return lines.join('\n');
};

export const approvePlaylistTagOrganizationPlan = (
  playlistId,
  {
    getItem = getLocalStorageItem,
    setItem = setLocalStorageItem,
  } = {},
) => {
  const timestamp = now();
  const updated = readPlaylists(getItem).map((playlist) => {
    if (playlist.id !== playlistId || !playlist.organizationPlan) {
      return playlist;
    }

    return {
      ...playlist,
      organizationApproval: {
        approvedAt: timestamp,
        impact:
          'Approval snapshot only; no tag write, cover-art write, ReplayGain run, file move, provider lookup, Soulseek search, peer browse, or download has started.',
        planGeneratedAt: playlist.organizationPlan.generatedAt,
        summary: playlist.organizationPlan.summary,
        trackSnapshots: playlist.organizationPlan.trackPreviews.map((preview) => ({
          changedFields: preview.changedFields,
          destinationPath: preview.destinationPath,
          metadataSnapshot: preview.metadataSnapshot,
          trackId: preview.trackId,
        })),
      },
      updatedAt: timestamp,
    };
  });

  return savePlaylists(updated, setItem);
};

export const clearPlaylistTagOrganizationApproval = (
  playlistId,
  {
    getItem = getLocalStorageItem,
    setItem = setLocalStorageItem,
  } = {},
) => {
  const updated = readPlaylists(getItem).map((playlist) =>
    playlist.id === playlistId
      ? {
          ...playlist,
          organizationApproval: null,
          updatedAt: now(),
        }
      : playlist,
  );

  return savePlaylists(updated, setItem);
};

export const scorePlaylistTrackCandidate = (track, candidate = {}) =>
  scoreMetadataCandidate(
    {
      artist: track.artist,
      durationMs: track.durationMs,
      title: track.title,
    },
    candidate,
  );
