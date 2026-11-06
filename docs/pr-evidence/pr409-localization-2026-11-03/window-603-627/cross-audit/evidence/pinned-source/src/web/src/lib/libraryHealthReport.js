import { interfaceText } from './interfaceLocale';
import { formatRegionalNumber } from './regionalFormat';

const normalizeText = (value = '') => String(value).trim();
const parseDiagnosticNumber = (value) => Number(String(value).replace(',', '.'));

const getIssueTypeLabel = (type) => {
  switch (type) {
    case 'SuspectedTranscode':
      return 'Suspected Transcode';
    case 'NonCanonicalVariant':
      return 'Non-Canonical Variant';
    case 'TrackNotInTaggedRelease':
      return 'Track Not in Tagged Release';
    case 'MissingTrackInRelease':
      return 'Missing Track in Release';
    case 'CorruptedFile':
      return 'Corrupted File';
    case 'MissingMetadata':
      return 'Missing Metadata';
    case 'MultipleVariants':
      return 'Multiple Variants';
    case 'WrongDuration':
      return 'Wrong Duration';
    default:
      return normalizeText(type) || 'Unknown';
  }
};

export { getIssueTypeLabel as getLibraryHealthIssueTypeLabel };

export const getLibraryHealthSeveritySource = (severity) => {
  switch (severity) {
    case 'Critical':
    case 'High':
    case 'Medium':
    case 'Low':
    case 'Info':
      return severity;
    default:
      return '';
  }
};

export const getLibraryHealthStatusSource = (status) => {
  switch (status) {
    case 'Detected':
    case 'Fixing':
    case 'Resolved':
    case 'Failed':
      return status;
    default:
      return '';
  }
};

const formatCountLine = (label, value) => interfaceText('{label}: {count}', {
  count: formatRegionalNumber(Number(value || 0)),
  label: interfaceText(label),
});

const localizeIssueType = (type) => {
  switch (type) {
    case 'SuspectedTranscode':
      return interfaceText('Suspected Transcode');
    case 'NonCanonicalVariant':
      return interfaceText('Non-Canonical Variant');
    case 'TrackNotInTaggedRelease':
      return interfaceText('Track Not in Tagged Release');
    case 'MissingTrackInRelease':
      return interfaceText('Missing Track in Release');
    case 'CorruptedFile':
      return interfaceText('Corrupted File');
    case 'MissingMetadata':
      return interfaceText('Missing Metadata');
    case 'MultipleVariants':
      return interfaceText('Multiple Variants');
    case 'WrongDuration':
      return interfaceText('Wrong Duration');
    default:
      return getIssueTypeLabel(type);
  }
};

const localizeSeverity = (severity) => {
  switch (severity) {
    case 'Critical':
      return interfaceText('Critical');
    case 'High':
      return interfaceText('High');
    case 'Medium':
      return interfaceText('Medium');
    case 'Low':
      return interfaceText('Low');
    case 'Info':
      return interfaceText('Info');
    default:
      return normalizeText(severity) || interfaceText('Unknown');
  }
};

export const formatLibraryHealthStatus = (status) => {
  switch (status) {
    case 'Detected':
      return interfaceText('Detected');
    case 'Fixing':
      return interfaceText('Fixing');
    case 'Resolved':
      return interfaceText('Resolved');
    case 'Failed':
      return interfaceText('Failed');
    default:
      return normalizeText(status);
  }
};

export const formatLibraryHealthReason = (reason) => {
  if (typeof reason !== 'string' || !reason) return reason || '';

  switch (reason) {
    case 'Unable to resolve MusicBrainz Recording ID via fingerprint or tags':
      return interfaceText('Unable to resolve MusicBrainz Recording ID via fingerprint or tags');
    case 'File cannot be read':
      return interfaceText('File cannot be read');
    case 'File scan failed':
      return interfaceText('File scan failed');
    case 'Lossy encoder signature in lossless file':
      return interfaceText('Lossy encoder signature in lossless file');
  }

  let match = /^Canonical variant available with quality score ([\d.,]+) vs current ([\d.,]+)$/.exec(reason);
  if (match) {
    return interfaceText('Canonical variant available with quality score {canonical} vs current {current}', {
      canonical: formatRegionalNumber(parseDiagnosticNumber(match[1])),
      current: formatRegionalNumber(parseDiagnosticNumber(match[2])),
    });
  }

  match = /^Album incomplete: (\d+)\/(\d+) tracks missing$/.exec(reason);
  if (match) {
    return interfaceText('Album incomplete: {missing}/{total} tracks missing', {
      missing: formatRegionalNumber(Number(match[1])),
      total: formatRegionalNumber(Number(match[2])),
    });
  }

  match = /^FLAC bitrate ([\d.,]+)kbps too low for ([\d.,]+)Hz\/(\d+)bit \(expected ≥([\d.,]+)kbps\)$/.exec(reason);
  if (match) {
    return interfaceText('FLAC bitrate {bitrate}kbps too low for {sampleRate}Hz/{bitDepth}bit (expected ≥{minimum}kbps)', {
      bitDepth: formatRegionalNumber(Number(match[3])),
      bitrate: formatRegionalNumber(parseDiagnosticNumber(match[1])),
      minimum: formatRegionalNumber(parseDiagnosticNumber(match[4])),
      sampleRate: formatRegionalNumber(parseDiagnosticNumber(match[2])),
    });
  }

  match = /^Lossless file with DR=([\d.,]+) suggests lossy source$/.exec(reason);
  if (match) {
    return interfaceText('Lossless file with DR={range} suggests lossy source', {
      range: formatRegionalNumber(parseDiagnosticNumber(match[1])),
    });
  }

  match = /^High-resolution audio has a measured ([\d.,]+)kHz cutoff consistent with upsampling from 44\.1\/48kHz audio$/.exec(reason);
  if (match) {
    return interfaceText('High-resolution audio has a measured {bandwidth}kHz cutoff consistent with upsampling from 44.1/48kHz audio', {
      bandwidth: formatRegionalNumber(parseDiagnosticNumber(match[1])),
    });
  }

  match = /^Spectral bandwidth ([\d.,]+)kHz suggests (\d+)kbps lossy source$/.exec(reason);
  if (match) {
    return interfaceText('Spectral bandwidth {bandwidth}kHz suggests {bitrate}kbps lossy source', {
      bandwidth: formatRegionalNumber(parseDiagnosticNumber(match[1])),
      bitrate: formatRegionalNumber(Number(match[2])),
    });
  }

  return reason;
};

const replacementIssueTypes = new Set([
  'CorruptedFile',
  'MissingTrackInRelease',
  'NonCanonicalVariant',
  'SuspectedTranscode',
  'WrongDuration',
]);

const quarantineIssueTypes = new Set([
  'CorruptedFile',
  'SuspectedTranscode',
]);

const buildReplacementQuery = (issue = {}) => {
  const parts = [
    issue.artist,
    issue.album,
    issue.title,
  ].map(normalizeText).filter(Boolean);

  if (parts.length > 0) {
    return parts.join(' ');
  }

  return normalizeText(issue.path || issue.filePath || issue.filename);
};

const getReplacementSearchIssues = (issues = []) =>
  issues.filter((issue) => replacementIssueTypes.has(issue.type));

const getQuarantineReviewIssues = (issues = []) =>
  issues.filter((issue) =>
    issue.severity === 'Critical' || quarantineIssueTypes.has(issue.type));

const getSafeFixIssues = (issues = []) =>
  issues.filter((issue) => issue.canAutoFix);

export const getLibraryHealthReplacementSearchQueries = (
  issues = [],
  { limit = 3 } = {},
) => {
  const candidates = getReplacementSearchIssues(issues)
    .map((issue) => buildReplacementQuery(issue))
    .filter(Boolean);

  return candidates
    .filter((query, index) =>
      candidates.findIndex((other) =>
        other.toLowerCase() === query.toLowerCase()) === index)
    .slice(0, limit);
};

export const getLibraryHealthSafeFixIssueIds = (
  issues = [],
  { limit = 25 } = {},
) =>
  getSafeFixIssues(issues)
    .map((issue) => issue.issueId)
    .filter(Boolean)
    .slice(0, limit);

export const getLibraryHealthQuarantineReviewItems = (
  issues = [],
  { limit = 25 } = {},
) =>
  getQuarantineReviewIssues(issues)
    .filter((issue) => issue.issueId)
    .slice(0, limit)
    .map((issue) => ({
      evidenceKey: `library-health:${issue.issueId}`,
      networkImpact:
        'Review only; approving here does not move, quarantine, search, browse, or download files.',
      reason: issue.reason || `${getIssueTypeLabel(issue.type)} requires review.`,
      searchText: buildReplacementQuery(issue),
      source: 'Library Health',
      sourceId: issue.issueId,
      title: [
        issue.artist,
        issue.album,
        issue.title,
      ].map(normalizeText).filter(Boolean).join(' - ') ||
        issue.path ||
        issue.filePath ||
        issue.filename ||
        issue.issueId,
    }));

export const buildLibraryHealthReport = ({
  generatedAt = new Date(),
  issues = [],
  issuesByArtist = [],
  issuesByType = [],
  libraryPath = '',
  summary = {},
} = {}) => [
  interfaceText('Library Health Report'),
  interfaceText('Generated: {timestamp}', {
    timestamp: generatedAt instanceof Date ? generatedAt.toISOString() : generatedAt,
  }),
  interfaceText('Library: {path}', {
    path: normalizeText(libraryPath) || interfaceText('unspecified'),
  }),
  '',
  interfaceText('Summary:'),
  formatCountLine('Total issues', summary.totalIssues),
  formatCountLine('Open issues', summary.issuesOpen),
  formatCountLine('Resolved issues', summary.issuesResolved),
  '',
  interfaceText('Issues by type:'),
  ...(issuesByType.length > 0
    ? issuesByType.map((group) =>
      interfaceText('- {type}: {count}', {
        count: formatRegionalNumber(Number(group.count || 0)),
        type: localizeIssueType(group.type),
      }))
    : [interfaceText('- none')]),
  '',
  interfaceText('Top artists:'),
  ...(issuesByArtist.length > 0
    ? issuesByArtist.map((group) =>
      interfaceText('- {artist}: {count}', {
        artist: normalizeText(group.artist) || interfaceText('Unknown artist'),
        count: formatRegionalNumber(Number(group.count || 0)),
      }))
    : [interfaceText('- none')]),
  '',
  interfaceText('Issue sample:'),
  ...(issues.length > 0
    ? issues.slice(0, 50).map((issue) => [
      interfaceText('- {severity} {type}', {
        severity: localizeSeverity(issue.severity || 'Unknown'),
        type: localizeIssueType(issue.type),
      }),
      issue.artist ? interfaceText(' | Artist: {artist}', { artist: issue.artist }) : '',
      issue.title ? interfaceText(' | Title: {title}', { title: issue.title }) : '',
      issue.reason ? interfaceText(' | Reason: {reason}', { reason: formatLibraryHealthReason(issue.reason) }) : '',
      interfaceText(issue.canAutoFix ? ' | safe fix available' : ' | review only'),
    ].join(''))
    : [interfaceText('- none')]),
].join('\n');

export const buildLibraryHealthActionPlan = ({
  generatedAt = new Date(),
  issues = [],
  libraryPath = '',
} = {}) => {
  const safeFixes = getSafeFixIssues(issues);
  const replacementSearches = getReplacementSearchIssues(issues);
  const quarantineReviews = getQuarantineReviewIssues(issues);

  return [
    interfaceText('Library Health Action Plan'),
    interfaceText('Generated: {timestamp}', {
      timestamp: generatedAt instanceof Date ? generatedAt.toISOString() : generatedAt,
    }),
    interfaceText('Library: {path}', {
      path: normalizeText(libraryPath) || interfaceText('unspecified'),
    }),
    interfaceText('Selected issues: {count}', { count: formatRegionalNumber(issues.length) }),
    interfaceText('Safe fix previews: {count}', { count: formatRegionalNumber(safeFixes.length) }),
    interfaceText('Replacement search previews: {count}', { count: formatRegionalNumber(replacementSearches.length) }),
    interfaceText('Quarantine review previews: {count}', { count: formatRegionalNumber(quarantineReviews.length) }),
    '',
    interfaceText('Selected issue plan:'),
    ...(issues.length > 0
      ? issues.map((issue) => [
        interfaceText('- {id}: {severity} {type}', {
          id: issue.issueId || interfaceText('unknown'),
          severity: localizeSeverity(issue.severity || 'Unknown'),
          type: localizeIssueType(issue.type),
        }),
        issue.artist ? interfaceText(' | Artist: {artist}', { artist: issue.artist }) : '',
        issue.title ? interfaceText(' | Title: {title}', { title: issue.title }) : '',
        interfaceText(issue.canAutoFix ? ' | safe fix preview' : ' | manual review'),
        replacementIssueTypes.has(issue.type) ? interfaceText(' | replacement search candidate') : '',
        quarantineReviews.includes(issue) ? interfaceText(' | quarantine review candidate') : '',
      ].join(''))
      : [interfaceText('- none')]),
    '',
    interfaceText('No remediation, replacement search, quarantine, or file mutation was started by this report.'),
  ].join('\n');
};

export const buildLibraryHealthSafeFixManifest = ({
  generatedAt = new Date(),
  issues = [],
  libraryPath = '',
} = {}) => {
  const safeFixIssues = getSafeFixIssues(issues);

  return [
    interfaceText('Library Health Safe Fix Manifest'),
    interfaceText('Generated: {timestamp}', {
      timestamp: generatedAt instanceof Date ? generatedAt.toISOString() : generatedAt,
    }),
    interfaceText('Library: {path}', {
      path: normalizeText(libraryPath) || interfaceText('unspecified'),
    }),
    interfaceText('Selected issues: {count}', { count: formatRegionalNumber(issues.length) }),
    interfaceText('Safe fix candidates: {count}', { count: formatRegionalNumber(safeFixIssues.length) }),
    '',
    interfaceText('Safe fix candidates:'),
    ...(safeFixIssues.length > 0
      ? safeFixIssues.map((issue) => [
        interfaceText('- {id}: {severity} {type}', {
          id: issue.issueId || interfaceText('unknown'),
          severity: localizeSeverity(issue.severity || 'Unknown'),
          type: localizeIssueType(issue.type),
        }),
        issue.artist ? interfaceText(' | Artist: {artist}', { artist: issue.artist }) : '',
        issue.album ? interfaceText(' | Album: {album}', { album: issue.album }) : '',
        issue.title ? interfaceText(' | Title: {title}', { title: issue.title }) : '',
        issue.reason ? interfaceText(' | Reason: {reason}', { reason: formatLibraryHealthReason(issue.reason) }) : '',
        issue.path || issue.filePath || issue.filename
          ? interfaceText(' | Target: {path}', { path: normalizeText(issue.path || issue.filePath || issue.filename) })
          : '',
      ].join(''))
      : [interfaceText('- none')]),
    '',
    interfaceText('No remediation job, safe-fix execution, quarantine state change, search, download, or file mutation was started by this manifest.'),
  ].join('\n');
};

export const buildLibraryHealthSearchSeeds = ({
  generatedAt = new Date(),
  issues = [],
  libraryPath = '',
} = {}) => {
  const queries = getLibraryHealthReplacementSearchQueries(issues, {
    limit: Number.MAX_SAFE_INTEGER,
  });
  const dedupedCandidates = queries.map((query) => ({
    issue: getReplacementSearchIssues(issues).find((issue) =>
      buildReplacementQuery(issue).toLowerCase() === query.toLowerCase()),
    query,
  }));

  return [
    interfaceText('Library Health Replacement Search Seeds'),
    interfaceText('Generated: {timestamp}', {
      timestamp: generatedAt instanceof Date ? generatedAt.toISOString() : generatedAt,
    }),
    interfaceText('Library: {path}', {
      path: normalizeText(libraryPath) || interfaceText('unspecified'),
    }),
    interfaceText('Selected issues: {count}', { count: formatRegionalNumber(issues.length) }),
    interfaceText('Replacement candidates: {count}', { count: formatRegionalNumber(dedupedCandidates.length) }),
    '',
    interfaceText('Search seeds:'),
    ...(dedupedCandidates.length > 0
      ? dedupedCandidates.map(({ issue, query }) => [
        interfaceText('- {query}', { query }),
        issue.issueId ? interfaceText(' | Issue {id}', { id: issue.issueId }) : '',
        issue.severity ? interfaceText(' | {severity}', { severity: localizeSeverity(issue.severity) }) : '',
        issue.type ? interfaceText(' | {type}', { type: localizeIssueType(issue.type) }) : '',
      ].join(''))
      : [interfaceText('- none')]),
    '',
    interfaceText('No search, peer browse, download, quarantine, or file mutation was started by this export.'),
  ].join('\n');
};

export const buildLibraryHealthQuarantinePacket = ({
  generatedAt = new Date(),
  issues = [],
  libraryPath = '',
} = {}) => {
  const reviewIssues = getQuarantineReviewIssues(issues);

  return [
    interfaceText('Library Health Quarantine Review Packet'),
    interfaceText('Generated: {timestamp}', {
      timestamp: generatedAt instanceof Date ? generatedAt.toISOString() : generatedAt,
    }),
    interfaceText('Library: {path}', {
      path: normalizeText(libraryPath) || interfaceText('unspecified'),
    }),
    interfaceText('Selected issues: {count}', { count: formatRegionalNumber(issues.length) }),
    interfaceText('Quarantine review candidates: {count}', { count: formatRegionalNumber(reviewIssues.length) }),
    '',
    interfaceText('Review checklist:'),
    ...(reviewIssues.length > 0
      ? reviewIssues.map((issue) => [
        interfaceText('- {id}: {severity} {type}', {
          id: issue.issueId || interfaceText('unknown'),
          severity: localizeSeverity(issue.severity || 'Unknown'),
          type: localizeIssueType(issue.type),
        }),
        issue.artist ? interfaceText(' | Artist: {artist}', { artist: issue.artist }) : '',
        issue.album ? interfaceText(' | Album: {album}', { album: issue.album }) : '',
        issue.title ? interfaceText(' | Title: {title}', { title: issue.title }) : '',
        issue.reason ? interfaceText(' | Reason: {reason}', { reason: formatLibraryHealthReason(issue.reason) }) : '',
        issue.path || issue.filePath || issue.filename
          ? interfaceText(' | Local evidence: {path}', { path: normalizeText(issue.path || issue.filePath || issue.filename) })
          : '',
        interfaceText(issue.canAutoFix ? ' | safe fix preview also available' : ' | manual review required'),
      ].join(''))
      : [interfaceText('- none')]),
    '',
    interfaceText('No quarantine state, file movement, peer message, remediation job, search, download, or file mutation was started by this packet.'),
  ].join('\n');
};

export default buildLibraryHealthReport;
