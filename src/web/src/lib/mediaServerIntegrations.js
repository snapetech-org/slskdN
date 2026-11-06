import { interfaceText } from './interfaceLocale';
import { formatRegionalNumber } from './regionalFormat';
export const mediaServerAdapters = [
  {
    capabilities: ['Library scan', 'Playlist sync', 'Play history import', 'Rating sync'],
    id: 'plex',
    label: 'Plex',
    requiresToken: true,
  },
  {
    capabilities: ['Library scan', 'Playlist sync', 'Play history import', 'User mapping'],
    id: 'jellyfin',
    label: 'Jellyfin / Emby',
    requiresToken: true,
  },
  {
    capabilities: ['Library scan', 'Playlist sync', 'Play history import'],
    id: 'navidrome',
    label: 'Navidrome',
    requiresToken: true,
  },
];

const normalizePath = (value = '') =>
  value
    .trim()
    .replaceAll('\\', '/')
    .replace(/\/+/gu, '/')
    .replace(/\/$/u, '');

const matchesPathPrefix = (path, prefix) =>
  path === prefix || path.startsWith(`${prefix}/`);

export const buildMediaServerPathDiagnostic = ({
  localPath = '',
  serverPath = '',
  remotePathFrom = '',
  remotePathTo = '',
} = {}) => {
  const normalizedLocal = normalizePath(localPath);
  const normalizedServer = normalizePath(serverPath);
  const normalizedFrom = normalizePath(remotePathFrom);
  const normalizedTo = normalizePath(remotePathTo);

  if (!normalizedLocal || !normalizedServer) {
    return {
      color: 'grey',
      message: 'Enter both paths to check whether slskdN and the media server agree.',
      status: 'Incomplete',
    };
  }

  if (normalizedLocal === normalizedServer) {
    return {
      color: 'green',
      message: 'Paths match exactly. A media-server scan can reference the same completed files.',
      status: 'Aligned',
    };
  }

  if (
    normalizedFrom &&
    normalizedTo &&
    matchesPathPrefix(normalizedLocal, normalizedFrom)
  ) {
    const mapped = `${normalizedTo}${normalizedLocal.slice(normalizedFrom.length)}`;
    return {
      color: mapped === normalizedServer ? 'green' : 'yellow',
      mappedPath: mapped,
      message:
        mapped === normalizedServer
          ? 'Remote path mapping translates the slskdN path to the media-server path.'
          : 'Remote path mapping applies, but the translated path does not match the media-server path.',
      status: mapped === normalizedServer ? 'Mapped' : 'Mapping Mismatch',
    };
  }

  return {
    color: 'orange',
    message: 'Paths differ and no matching remote path map was provided.',
    status: 'Needs Mapping',
  };
};

const getAdapter = (adapterId) =>
  mediaServerAdapters.find((adapter) => adapter.id === adapterId) ||
  mediaServerAdapters[0];

export const buildMediaServerSyncPreview = ({
  adapterId = 'plex',
  baseUrl = '',
  localPath = '',
  remotePathFrom = '',
  remotePathTo = '',
  serverPath = '',
  tokenConfigured = false,
} = {}) => {
  const adapter = getAdapter(adapterId);
  const pathDiagnostic = buildMediaServerPathDiagnostic({
    localPath,
    remotePathFrom,
    remotePathTo,
    serverPath,
  });
  const checks = [
    {
      action: 'Configure the media-server base URL before enabling live scans.',
      label: 'Base URL configured',
      ready: Boolean(baseUrl.trim()),
    },
    {
      action: 'Store an API token or app token before any live media-server call.',
      label: 'Token configured',
      ready: Boolean(tokenConfigured),
    },
    {
      action: 'Add a remote path map or align completed-download and library paths.',
      label: 'Path mapping ready',
      ready: ['Aligned', 'Mapped'].includes(pathDiagnostic.status),
    },
  ];
  const readyCount = checks.filter((check) => check.ready).length;

  return {
    adapter,
    checks,
    pathDiagnostic,
    readyCount,
    status: readyCount === checks.length ? 'Ready for live adapter' : 'Needs setup',
    total: checks.length,
  };
};

export const mediaServerAutomationContracts = [
  {
    description:
      'Pull recent plays from the selected media server into browser/server listening intelligence.',
    id: 'playHistoryImport',
    label: 'Play history import',
    requiresConfirmation: false,
    requiresUserMapping: true,
  },
  {
    description:
      'Export confirmed local plays or ratings back to the selected media server profile.',
    id: 'scrobbleExport',
    label: 'Scrobble and rating export',
    requiresConfirmation: true,
    requiresUserMapping: true,
  },
  {
    description:
      'Turn approved listening-intelligence gaps into acquisition queue candidates.',
    id: 'acquisitionQueue',
    label: 'Acquisition queue handoff',
    requiresConfirmation: true,
    requiresUserMapping: false,
  },
  {
    description:
      'Ask the selected media server to scan confirmed completed-download paths.',
    id: 'completedScan',
    label: 'Completed file scan',
    requiresConfirmation: true,
    requiresUserMapping: false,
  },
  {
    description:
      'Apply confirmed post-acquisition file actions after media-server visibility is verified.',
    id: 'confirmedFileActions',
    label: 'Confirmed file actions',
    requiresConfirmation: true,
    requiresUserMapping: false,
  },
];

const defaultAutomationEnabled = (automation) =>
  automation.id === 'playHistoryImport' || automation.id === 'completedScan';

export const defaultMediaServerAutomations = Object.freeze(
  Object.fromEntries(
    mediaServerAutomationContracts.map((automation) => [
      automation.id,
      defaultAutomationEnabled(automation),
    ]),
  ),
);

export const buildMediaServerExecutionContract = ({
  confirmationRequired = true,
  dedupeWindowHours = 24,
  enabledAutomations = {},
  rateLimitPerMinute = 6,
  syncPreview,
  userMappingConfigured = false,
} = {}) => {
  const normalizedRateLimit = Number(rateLimitPerMinute) || 0;
  const normalizedDedupeWindow = Number(dedupeWindowHours) || 0;
  const adapterReady = syncPreview?.status === 'Ready for live adapter';
  const contractChecks = [
    {
      action: 'Complete base URL, token, and path-map readiness before live execution.',
      id: 'adapterReady',
      label: 'Adapter readiness',
      ready: adapterReady,
    },
    {
      action: 'Configure an explicit media-server user mapping before importing or exporting user-scoped activity.',
      id: 'userMapping',
      label: 'User mapping configured',
      ready: Boolean(userMappingConfigured),
    },
    {
      action: 'Keep confirmation gates enabled before download, scan, scrobble, or file actions execute.',
      id: 'confirmation',
      label: 'Confirmation gates required',
      ready: Boolean(confirmationRequired),
    },
    {
      action: 'Set a positive per-minute limit so media-server calls stay bounded.',
      id: 'rateLimit',
      label: 'Rate limit configured',
      ready: normalizedRateLimit > 0,
    },
    {
      action: 'Set a dedupe window so repeated play-history and file-action attempts collapse.',
      id: 'dedupe',
      label: 'Dedupe window configured',
      ready: normalizedDedupeWindow > 0,
    },
  ];
  const automations = mediaServerAutomationContracts.map((automation) => {
    const enabled =
      enabledAutomations[automation.id] ?? defaultAutomationEnabled(automation);
    const blockers = [
      !adapterReady && 'Adapter is not ready.',
      automation.requiresUserMapping &&
        !userMappingConfigured &&
        'User mapping is required.',
      automation.requiresConfirmation &&
        !confirmationRequired &&
        'Confirmation gate is required.',
      normalizedRateLimit <= 0 && 'Rate limit must be positive.',
      normalizedDedupeWindow <= 0 && 'Dedupe window must be positive.',
    ].filter(Boolean);

    return {
      ...automation,
      blockedReasons: blockers,
      enabled,
      ready: Boolean(enabled) && blockers.length === 0,
    };
  });
  const readyCount = contractChecks.filter((check) => check.ready).length;
  const enabledReadyCount = automations.filter((automation) => automation.ready).length;
  const enabledCount = automations.filter((automation) => automation.enabled).length;

  return {
    adapter: syncPreview?.adapter,
    automations,
    checks: contractChecks,
    dedupeWindowHours: normalizedDedupeWindow,
    enabledCount,
    enabledReadyCount,
    rateLimitPerMinute: normalizedRateLimit,
    readyCount,
    status:
      readyCount === contractChecks.length && enabledReadyCount === enabledCount
        ? 'Execution contract ready'
        : 'Execution contract blocked',
    total: contractChecks.length,
  };
};

const localizeMediaServerSourceText = (value) => {
  switch (value) {
    case 'Incomplete':
      return interfaceText('Incomplete');
    case 'Aligned':
      return interfaceText('Aligned');
    case 'Mapped':
      return interfaceText('Mapped');
    case 'Mapping Mismatch':
      return interfaceText('Mapping Mismatch');
    case 'Needs Mapping':
      return interfaceText('Needs Mapping');
    case 'Ready for live adapter':
      return interfaceText('Ready for live adapter');
    case 'Needs setup':
      return interfaceText('Needs setup');
    case 'Execution contract ready':
      return interfaceText('Execution contract ready');
    case 'Execution contract blocked':
      return interfaceText('Execution contract blocked');
    case 'Enter both paths to check whether slskdN and the media server agree.':
      return interfaceText('Enter both paths to check whether slskdN and the media server agree.');
    case 'Paths match exactly. A media-server scan can reference the same completed files.':
      return interfaceText('Paths match exactly. A media-server scan can reference the same completed files.');
    case 'Remote path mapping translates the slskdN path to the media-server path.':
      return interfaceText('Remote path mapping translates the slskdN path to the media-server path.');
    case 'Remote path mapping applies, but the translated path does not match the media-server path.':
      return interfaceText('Remote path mapping applies, but the translated path does not match the media-server path.');
    case 'Paths differ and no matching remote path map was provided.':
      return interfaceText('Paths differ and no matching remote path map was provided.');
    case 'Base URL configured':
      return interfaceText('Base URL configured');
    case 'Token configured':
      return interfaceText('Token configured');
    case 'Path mapping ready':
      return interfaceText('Path mapping ready');
    case 'Adapter readiness':
      return interfaceText('Adapter readiness');
    case 'User mapping configured':
      return interfaceText('User mapping configured');
    case 'Confirmation gates required':
      return interfaceText('Confirmation gates required');
    case 'Rate limit configured':
      return interfaceText('Rate limit configured');
    case 'Dedupe window configured':
      return interfaceText('Dedupe window configured');
    case 'Configure the media-server base URL before enabling live scans.':
      return interfaceText('Configure the media-server base URL before enabling live scans.');
    case 'Store an API token or app token before any live media-server call.':
      return interfaceText('Store an API token or app token before any live media-server call.');
    case 'Add a remote path map or align completed-download and library paths.':
      return interfaceText('Add a remote path map or align completed-download and library paths.');
    case 'Complete base URL, token, and path-map readiness before live execution.':
      return interfaceText('Complete base URL, token, and path-map readiness before live execution.');
    case 'Configure an explicit media-server user mapping before importing or exporting user-scoped activity.':
      return interfaceText('Configure an explicit media-server user mapping before importing or exporting user-scoped activity.');
    case 'Keep confirmation gates enabled before download, scan, scrobble, or file actions execute.':
      return interfaceText('Keep confirmation gates enabled before download, scan, scrobble, or file actions execute.');
    case 'Set a positive per-minute limit so media-server calls stay bounded.':
      return interfaceText('Set a positive per-minute limit so media-server calls stay bounded.');
    case 'Set a dedupe window so repeated play-history and file-action attempts collapse.':
      return interfaceText('Set a dedupe window so repeated play-history and file-action attempts collapse.');
    case 'Play history import':
      return interfaceText('Play history import');
    case 'Scrobble and rating export':
      return interfaceText('Scrobble and rating export');
    case 'Acquisition queue handoff':
      return interfaceText('Acquisition queue handoff');
    case 'Completed file scan':
      return interfaceText('Completed file scan');
    case 'Confirmed file actions':
      return interfaceText('Confirmed file actions');
    case 'Pull recent plays from the selected media server into browser/server listening intelligence.':
      return interfaceText('Pull recent plays from the selected media server into browser/server listening intelligence.');
    case 'Export confirmed local plays or ratings back to the selected media server profile.':
      return interfaceText('Export confirmed local plays or ratings back to the selected media server profile.');
    case 'Turn approved listening-intelligence gaps into acquisition queue candidates.':
      return interfaceText('Turn approved listening-intelligence gaps into acquisition queue candidates.');
    case 'Ask the selected media server to scan confirmed completed-download paths.':
      return interfaceText('Ask the selected media server to scan confirmed completed-download paths.');
    case 'Apply confirmed post-acquisition file actions after media-server visibility is verified.':
      return interfaceText('Apply confirmed post-acquisition file actions after media-server visibility is verified.');
    case 'Adapter is not ready.':
      return interfaceText('Adapter is not ready.');
    case 'User mapping is required.':
      return interfaceText('User mapping is required.');
    case 'Confirmation gate is required.':
      return interfaceText('Confirmation gate is required.');
    case 'Rate limit must be positive.':
      return interfaceText('Rate limit must be positive.');
    case 'Dedupe window must be positive.':
      return interfaceText('Dedupe window must be positive.');
    default:
      return value;
  }
};

export const formatMediaServerSyncReport = (preview) => {
  const lines = [
    interfaceText("slskdN media-server sync review"),
    interfaceText('Adapter: {name}', { name: preview.adapter.label }),
    interfaceText('Status: {status}', { status: localizeMediaServerSourceText(preview.status) }),
    interfaceText('Checks: {ready}/{total}', {
      ready: formatRegionalNumber(preview.readyCount),
      total: formatRegionalNumber(preview.total),
    }),
    interfaceText('Path status: {status}', {
      status: localizeMediaServerSourceText(preview.pathDiagnostic.status),
    }),
    interfaceText('Path message: {message}', {
      message: localizeMediaServerSourceText(preview.pathDiagnostic.message),
    }),
  ];

  if (preview.pathDiagnostic.mappedPath) {
    lines.push(interfaceText('Mapped path: {path}', { path: preview.pathDiagnostic.mappedPath }));
  }

  lines.push('', interfaceText('Checks:'));
  preview.checks.forEach((check) => {
    lines.push(interfaceText('- {status}: {label}', {
      status: interfaceText(check.ready ? 'Ready' : 'Pending'),
      label: localizeMediaServerSourceText(check.label),
    }));
    if (!check.ready) {
      lines.push(interfaceText('  Action: {action}', { action: localizeMediaServerSourceText(check.action) }));
    }
  });

  return lines.join('\n');
};

export const formatMediaServerExecutionContractReport = (contract) => {
  const lines = [
    interfaceText("slskdN media-server execution contract"),
    interfaceText('Adapter: {name}', { name: contract.adapter?.label || interfaceText('Unknown') }),
    interfaceText('Status: {status}', { status: localizeMediaServerSourceText(contract.status) }),
    interfaceText('Checks: {ready}/{total}', {
      ready: formatRegionalNumber(contract.readyCount),
      total: formatRegionalNumber(contract.total),
    }),
    interfaceText('Rate limit: {count} calls/minute', {
      count: formatRegionalNumber(contract.rateLimitPerMinute),
    }),
    interfaceText('Dedupe window: {count} hours', {
      count: formatRegionalNumber(contract.dedupeWindowHours),
    }),
    interfaceText('Enabled automations ready: {ready}/{enabled}', {
      ready: formatRegionalNumber(contract.enabledReadyCount),
      enabled: formatRegionalNumber(contract.enabledCount),
    }),
    '',
    interfaceText('Contract checks:'),
  ];

  contract.checks.forEach((check) => {
    lines.push(interfaceText('- {status}: {label}', {
      status: interfaceText(check.ready ? 'Ready' : 'Needs attention'),
      label: localizeMediaServerSourceText(check.label),
    }));
    if (!check.ready) {
      lines.push(interfaceText('  Action: {action}', { action: localizeMediaServerSourceText(check.action) }));
    }
  });

  lines.push('', interfaceText('Automations:'));
  contract.automations.forEach((automation) => {
    lines.push(
      interfaceText('- {enabled} / {status}: {label}', {
        enabled: interfaceText(automation.enabled ? 'Enabled' : 'Disabled'),
        status: interfaceText(automation.ready ? 'Ready' : 'Needs attention'),
        label: localizeMediaServerSourceText(automation.label),
      }),
    );
    lines.push(interfaceText('  {description}', {
      description: localizeMediaServerSourceText(automation.description),
    }));
    automation.blockedReasons.forEach((reason) => {
      lines.push(interfaceText('  Blocker: {reason}', { reason: localizeMediaServerSourceText(reason) }));
    });
  });

  return lines.join('\n');
};
