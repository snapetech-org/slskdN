import { interfaceText } from './interfaceLocale';

const normalizeText = (value = '') => String(value).trim();

const unique = (values) => [...new Set(values.filter(Boolean))];
const asArray = (value) => (Array.isArray(value) ? value : []);

const quoteIfNeeded = (value) => {
  const normalized = normalizeText(value);
  if (!normalized) return '';
  return /\s/u.test(normalized) ? `"${normalized}"` : normalized;
};

const getTagValues = (track = {}) => {
  const tags = Array.isArray(track.tags) ? track.tags.map(normalizeText) : [];
  if (tags.filter(Boolean).length > 0) return tags;

  const genres = Array.isArray(track.genres) ? track.genres.map(normalizeText) : [];
  if (genres.filter(Boolean).length > 0) return genres;

  if (track.genre) return [normalizeText(track.genre)];
  return [];
};

export const buildPlayerRadioPlan = (track = {}) => {
  if (!track) {
    return {
      basis: [],
      primaryQuery: '',
      queries: [],
      ready: false,
      seedLabel: 'No track selected',
    };
  }

  const artist = normalizeText(track.artist);
  const title = normalizeText(track.title || track.fileName);
  const album = normalizeText(track.album);
  const tags = unique(getTagValues(track));
  const trackQuery = unique([artist, title]).join(' ');
  const artistQuery = artist;
  const albumQuery = unique([artist, album]).join(' ');
  const genreQuery = unique([artist, tags[0]]).join(' ');

  const queries = unique([
    trackQuery,
    albumQuery,
    genreQuery,
    artistQuery,
  ]).map((query, index) => ({
    id: `radio-query-${index + 1}`,
    query,
    reason:
      query === trackQuery
        ? 'Similar track seed'
        : query === albumQuery
          ? 'Album neighborhood'
          : query === genreQuery
            ? 'Artist and genre seed'
            : 'Artist radio seed',
  }));

  return {
    basis: [
      artist ? `Artist: ${artist}` : '',
      title ? `Track: ${title}` : '',
      album ? `Album: ${album}` : '',
      tags.length > 0 ? `Tags: ${tags.slice(0, 3).join(', ')}` : '',
    ].filter(Boolean),
    primaryQuery: queries[0]?.query || '',
    queries,
    ready: queries.length > 0,
    seedLabel: unique([artist, title]).join(' - ') || title || artist || 'Untitled seed',
  };
};

export const buildPlayerRadioSearchPath = (query) => {
  const normalized = normalizeText(query);
  return normalized ? `/searches?q=${encodeURIComponent(normalized)}` : '/searches';
};

export const getPlayerRadioReasonSource = (value) => {
  switch (value) {
    case 'Similar track seed':
      return 'Similar track seed';
    case 'Album neighborhood':
      return 'Album neighborhood';
    case 'Artist and genre seed':
      return 'Artist and genre seed';
    case 'Artist radio seed':
      return 'Artist radio seed';
    default:
      return value;
  }
};

const localizePlayerRadioReason = (value) => {
  switch (value) {
    case 'Similar track seed':
      return interfaceText('Similar track seed');
    case 'Album neighborhood':
      return interfaceText('Album neighborhood');
    case 'Artist and genre seed':
      return interfaceText('Artist and genre seed');
    case 'Artist radio seed':
      return interfaceText('Artist radio seed');
    default:
      return value;
  }
};

export const getPlayerRadioQueries = (plan = {}, { limit = 3 } = {}) =>
  asArray(plan.queries)
    .map((item) => item.query)
    .filter(Boolean)
    .filter((query, index, queries) =>
      queries.findIndex((other) =>
        other.toLowerCase() === query.toLowerCase()) === index)
    .slice(0, limit);

export const buildPlayerRadioDiscoveryItems = (
  plan = {},
  { acquisitionProfile = 'mesh-preferred', limit = 4 } = {},
) =>
  asArray(plan.queries).slice(0, limit).map((item) => ({
    acquisitionProfile,
    evidenceKey: `smart-radio:${normalizeText(item.reason).toLowerCase()}:${normalizeText(item.query).toLowerCase()}`,
    networkImpact:
      'Smart radio review seed only; approval is required before any search execution, peer browse, download, or file mutation.',
    reason: `${item.reason} generated from current player seed ${plan.seedLabel || 'unknown seed'}.`,
    searchText: normalizeText(item.query),
    source: 'Smart Radio',
    sourceId: item.id,
    title: `${item.reason}: ${normalizeText(item.query)}`,
  }));

export const getPlayerRadioCopyText = (plan) => {
  if (!plan?.ready) return '';

  const seed = plan.seedLabel === 'Untitled seed'
    ? interfaceText('Untitled seed')
    : plan.seedLabel;
  return [
    interfaceText('Smart radio seed: {seed}', { seed }),
    ...asArray(plan.queries).map((item) => interfaceText('{reason}: {query}', {
      query: quoteIfNeeded(item.query),
      reason: localizePlayerRadioReason(item.reason),
    })),
  ].join('\n');
};
