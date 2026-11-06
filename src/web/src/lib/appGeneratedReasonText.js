import { interfaceText } from './interfaceLocale';
import { formatRegionalNumber } from './regionalFormat';

const asText = (value, fallback = '') =>
  typeof value === 'string' || typeof value === 'number'
    ? String(value)
    : fallback;

export const getRealmSubjectIndexConflictTypePresentation = (value) => {
  switch (value) {
    case 'external-id':
      return { source: 'External ID conflict' };
    case 'recording-subject':
      return { source: 'Recording subject conflict' };
    case 'workref-identity':
      return { source: 'WorkRef identity conflict' };
    case 'alias-subject':
      return { source: 'Alias subject conflict' };
    default:
      return { text: asText(value, 'unknown') };
  }
};

export const localizeRealmSubjectIndexConflictType = (value) => {
  switch (value) {
    case 'external-id':
      return interfaceText('External ID conflict');
    case 'recording-subject':
      return interfaceText('Recording subject conflict');
    case 'workref-identity':
      return interfaceText('WorkRef identity conflict');
    case 'alias-subject':
      return interfaceText('Alias subject conflict');
    default:
      return asText(value, 'unknown');
  }
};

export const getRealmSubjectIndexConflictDescriptionPresentation = (conflict = {}) => {
  const type = asText(conflict.type || conflict.Type);
  const subjectId = asText(conflict.subjectId || conflict.SubjectId);
  const key = asText(conflict.key || conflict.Key);
  const description = asText(conflict.description || conflict.Description, '-');

  switch (type) {
    case 'external-id':
      if (!subjectId || !key) return { text: description };
      return {
        source: "Subject '{subjectId}' has conflicting external id values for '{key}'.",
        values: { key, subjectId },
      };
    case 'recording-subject':
      if (!key) return { text: description };
      return {
        source: "Recording '{recordingId}' maps to multiple realm subjects.",
        values: { recordingId: key },
      };
    case 'workref-identity':
      if (!subjectId) return { text: description };
      return {
        source: "Subject '{subjectId}' has conflicting title or creator values.",
        values: { subjectId },
      };
    case 'alias-subject':
      if (!key) return { text: description };
      return {
        source: "Alias '{alias}' maps to multiple realm subjects.",
        values: { alias: key },
      };
    default:
      return { text: description };
  }
};

export const localizeRealmSubjectIndexConflictDescription = (conflict = {}) => {
  const type = asText(conflict.type || conflict.Type);
  const subjectId = asText(conflict.subjectId || conflict.SubjectId);
  const key = asText(conflict.key || conflict.Key);
  const description = asText(conflict.description || conflict.Description, '-');

  switch (type) {
    case 'external-id':
      if (!subjectId || !key) return description;
      return interfaceText(
        "Subject '{subjectId}' has conflicting external id values for '{key}'.",
        { key, subjectId },
      );
    case 'recording-subject':
      if (!key) return description;
      return interfaceText(
        "Recording '{recordingId}' maps to multiple realm subjects.",
        { recordingId: key },
      );
    case 'workref-identity':
      if (!subjectId) return description;
      return interfaceText(
        "Subject '{subjectId}' has conflicting title or creator values.",
        { subjectId },
      );
    case 'alias-subject':
      if (!key) return description;
      return interfaceText(
        "Alias '{alias}' maps to multiple realm subjects.",
        { alias: key },
      );
    default:
      return description;
  }
};

export const getTasteRecommendationReasonPresentation = (value) => {
  const reason = asText(value);
  let match = reason.match(/^appeared in (\d+) trusted federated music libraries$/);
  if (match) {
    return {
      source: 'Appeared in {count} trusted federated music libraries',
      values: { count: formatRegionalNumber(Number(match[1])) },
    };
  }

  if (reason === 'suggested by Soulseek native recommendations') {
    return { source: 'Suggested by Soulseek native recommendations' };
  }

  match = reason.match(/^near your federated music graph for (.+)$/);
  if (match) {
    return {
      source: 'Near your federated music graph for {creator}',
      values: { creator: match[1] },
    };
  }

  if (reason === 'has MusicBrainz identity evidence') {
    return { source: 'Has MusicBrainz identity evidence' };
  }

  match = reason.match(/^near a Discovery Graph neighborhood with (\d+) nodes$/);
  if (match) {
    return {
      source: 'Near a Discovery Graph neighborhood with {count} nodes',
      values: { count: formatRegionalNumber(Number(match[1])) },
    };
  }

  match = reason.match(/^connected by (\d+) graph evidence edges$/);
  if (match) {
    return {
      source: 'Connected by {count} graph evidence edges',
      values: { count: formatRegionalNumber(Number(match[1])) },
    };
  }

  return { text: reason };
};

export const localizeTasteRecommendationReason = (value) => {
  const reason = asText(value);
  let match = reason.match(/^appeared in (\d+) trusted federated music libraries$/);
  if (match) {
    return interfaceText('Appeared in {count} trusted federated music libraries', {
      count: formatRegionalNumber(Number(match[1])),
    });
  }

  if (reason === 'suggested by Soulseek native recommendations') {
    return interfaceText('Suggested by Soulseek native recommendations');
  }

  match = reason.match(/^near your federated music graph for (.+)$/);
  if (match) {
    return interfaceText('Near your federated music graph for {creator}', {
      creator: match[1],
    });
  }

  if (reason === 'has MusicBrainz identity evidence') {
    return interfaceText('Has MusicBrainz identity evidence');
  }

  match = reason.match(/^near a Discovery Graph neighborhood with (\d+) nodes$/);
  if (match) {
    return interfaceText('Near a Discovery Graph neighborhood with {count} nodes', {
      count: formatRegionalNumber(Number(match[1])),
    });
  }

  match = reason.match(/^connected by (\d+) graph evidence edges$/);
  if (match) {
    return interfaceText('Connected by {count} graph evidence edges', {
      count: formatRegionalNumber(Number(match[1])),
    });
  }

  return reason;
};

const localizeMatchConfidence = (value) => {
  switch (value) {
    case 'Strong':
      return interfaceText('Strong');
    case 'Medium':
      return interfaceText('Medium');
    case 'Weak':
      return interfaceText('Weak');
    case 'None':
      return interfaceText('None');
    default:
      return value;
  }
};

export const getMediaCoreMatchReasonPresentation = (value) => {
  const reason = asText(value);
  const sources = {
    'MBID + duration match': 'MBID + duration match',
    'MBID matches but duration mismatch': 'MBID matches but duration does not match',
    'Title + artist + duration match': 'Title + artist + duration match',
    'Title + album + duration match': 'Title + album + duration match',
    'Title + artist match': 'Title + artist match',
    'Title + duration match': 'Title + duration match',
    'Filename title + artist similarity': 'Filename title + artist similarity',
    'Filename similarity': 'Filename similarity',
    'No match': 'No match',
  };
  if (Object.hasOwn(sources, reason)) return { source: sources[reason] };

  const match = reason.match(/^Verification failed: only (Strong|Medium|Weak|None) confidence$/);
  if (!match) return { text: reason };
  return {
    source: 'Verification failed: only {confidence} confidence',
    values: { confidence: localizeMatchConfidence(match[1]) },
  };
};

export const localizeMediaCoreMatchReason = (value) => {
  const reason = asText(value);
  switch (reason) {
    case 'MBID + duration match':
      return interfaceText('MBID + duration match');
    case 'MBID matches but duration mismatch':
      return interfaceText('MBID matches but duration does not match');
    case 'Title + artist + duration match':
      return interfaceText('Title + artist + duration match');
    case 'Title + album + duration match':
      return interfaceText('Title + album + duration match');
    case 'Title + artist match':
      return interfaceText('Title + artist match');
    case 'Title + duration match':
      return interfaceText('Title + duration match');
    case 'Filename title + artist similarity':
      return interfaceText('Filename title + artist similarity');
    case 'Filename similarity':
      return interfaceText('Filename similarity');
    case 'No match':
      return interfaceText('No match');
    default: {
      const match = reason.match(/^Verification failed: only (Strong|Medium|Weak|None) confidence$/);
      if (!match) return reason;
      return interfaceText('Verification failed: only {confidence} confidence', {
        confidence: localizeMatchConfidence(match[1]),
      });
    }
  }
};
