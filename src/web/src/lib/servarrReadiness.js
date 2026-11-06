import { interfaceText } from './interfaceLocale';
import { formatRegionalNumber } from './regionalFormat';

const hasValue = (value) =>
  value !== undefined && value !== null && String(value).trim() !== '';

export const buildServarrReadiness = ({
  autoImportCompleted = false,
  enabled = false,
  importPathFrom = '',
  importPathTo = '',
  syncWantedToWishlist = false,
  url = '',
  apiKey = '',
} = {}) => [
  {
    description: 'Lidarr/Radarr/Sonarr-compatible clients need a reachable slskdN URL.',
    id: 'base-url',
    ready: enabled && hasValue(url),
    title: 'Base URL configured',
  },
  {
    description: 'External Servarr apps should use a scoped API key, not an operator session.',
    id: 'api-key',
    ready: hasValue(apiKey),
    title: 'API key configured',
  },
  {
    description: 'Wanted and cutoff-unmet items can be pulled into slskdN Wishlist review.',
    id: 'wanted-pull',
    ready: enabled && syncWantedToWishlist === true,
    title: 'Wanted pull enabled',
  },
  {
    description: 'Completed download import can hand files back to the Servarr app after review.',
    id: 'completed-import',
    ready: enabled && autoImportCompleted === true,
    title: 'Completed import enabled',
  },
  {
    description: 'Remote path mapping prevents container path mismatches during import.',
    id: 'path-map',
    ready: !hasValue(importPathFrom) || hasValue(importPathTo),
    title: 'Remote path mapping sane',
  },
];

export const summarizeServarrReadiness = (checks) => {
  const ready = checks.filter((check) => check.ready).length;

  return {
    ready,
    total: checks.length,
    status: ready === checks.length ? 'Ready' : 'Needs Setup',
  };
};

const localizeServarrCopy = (value) => {
  switch (value) {
    case 'Ready':
      return interfaceText('Ready');
    case 'Needs Setup':
      return interfaceText('Needs Setup');
    case 'Base URL configured':
      return interfaceText('Base URL configured');
    case 'API key configured':
      return interfaceText('API key configured');
    case 'Wanted pull enabled':
      return interfaceText('Wanted pull enabled');
    case 'Completed import enabled':
      return interfaceText('Completed import enabled');
    case 'Remote path mapping sane':
      return interfaceText('Remote path mapping sane');
    case 'Lidarr/Radarr/Sonarr-compatible clients need a reachable slskdN URL.':
      return interfaceText('Lidarr/Radarr/Sonarr-compatible clients need a reachable slskdN URL.');
    case 'External Servarr apps should use a scoped API key, not an operator session.':
      return interfaceText('External Servarr apps should use a scoped API key, not an operator session.');
    case 'Wanted and cutoff-unmet items can be pulled into slskdN Wishlist review.':
      return interfaceText('Wanted and cutoff-unmet items can be pulled into slskdN Wishlist review.');
    case 'Completed download import can hand files back to the Servarr app after review.':
      return interfaceText('Completed download import can hand files back to the Servarr app after review.');
    case 'Remote path mapping prevents container path mismatches during import.':
      return interfaceText('Remote path mapping prevents container path mismatches during import.');
    case 'Enable completed import review before using move-style import handoff.':
      return interfaceText('Enable completed import review before using move-style import handoff.');
    default:
      return value;
  }
};

export const buildServarrCompatibilityPreview = ({
  apiKey = '',
  autoImportCompleted = false,
  enabled = false,
  importMode = 'copy',
  importPathFrom = '',
  importPathTo = '',
  syncWantedToWishlist = false,
  url = '',
} = {}) => {
  const checks = buildServarrReadiness({
    apiKey,
    autoImportCompleted,
    enabled,
    importPathFrom,
    importPathTo,
    syncWantedToWishlist,
    url,
  });
  const summary = summarizeServarrReadiness(checks);
  const actions = checks
    .filter((check) => !check.ready)
    .map((check) => check.description);

  if (enabled && importMode === 'move' && !autoImportCompleted) {
    actions.push('Enable completed import review before using move-style import handoff.');
  }

  return {
    actions,
    checks,
    importMode,
    summary,
    supportsCompletedImport: enabled && autoImportCompleted === true,
    supportsWantedPull: enabled && syncWantedToWishlist === true,
  };
};

export const formatServarrCompatibilityReport = (preview) => {
  const lines = [
    interfaceText('slskdN Servarr compatibility review'),
    interfaceText('Status: {status}', { status: localizeServarrCopy(preview.summary.status) }),
    interfaceText('Checks: {ready}/{total}', {
      ready: formatRegionalNumber(preview.summary.ready),
      total: formatRegionalNumber(preview.summary.total),
    }),
    interfaceText('Wanted pull: {status}', {
      status: interfaceText(preview.supportsWantedPull ? 'Ready' : 'Needs attention'),
    }),
    interfaceText('Completed import: {status}', {
      status: interfaceText(preview.supportsCompletedImport ? 'Ready' : 'Needs attention'),
    }),
    interfaceText('Import mode: {mode}', {
      mode: preview.importMode === 'move'
        ? interfaceText('Move')
        : preview.importMode === 'copy'
          ? interfaceText('Copy')
          : preview.importMode,
    }),
    '',
    interfaceText('Checks:'),
  ];

  preview.checks.forEach((check) => {
    lines.push(interfaceText('- {status}: {title}', {
      status: interfaceText(check.ready ? 'Ready' : 'Pending'),
      title: localizeServarrCopy(check.title),
    }));
  });

  lines.push('', interfaceText('Actions:'));
  if (preview.actions.length === 0) {
    lines.push(interfaceText('- none'));
  } else {
    preview.actions.forEach((action) => lines.push(interfaceText('- {action}', {
      action: localizeServarrCopy(action),
    })));
  }

  return lines.join('\n');
};
