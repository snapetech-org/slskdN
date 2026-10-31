import { interfaceText } from './interfaceLocale';
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

export const formatMediaServerSyncReport = (preview) => {
  const lines = [
    interfaceText("slskdN media-server sync review"),
    `Adapter: ${preview.adapter.label}`,
    `Status: ${preview.status}`,
    `Checks: ${preview.readyCount}/${preview.total}`,
    `Path status: ${preview.pathDiagnostic.status}`,
    `Path message: ${preview.pathDiagnostic.message}`,
  ];

  if (preview.pathDiagnostic.mappedPath) {
    lines.push(`Mapped path: ${preview.pathDiagnostic.mappedPath}`);
  }

  lines.push('', 'Checks:');
  preview.checks.forEach((check) => {
    lines.push(`- ${check.ready ? 'READY' : 'PENDING'}: ${check.label}`);
    if (!check.ready) {
      lines.push(`  Action: ${check.action}`);
    }
  });

  return lines.join('\n');
};

export const formatMediaServerExecutionContractReport = (contract) => {
  const lines = [
    interfaceText("slskdN media-server execution contract"),
    `Adapter: ${contract.adapter?.label || 'Unknown'}`,
    `Status: ${contract.status}`,
    `Checks: ${contract.readyCount}/${contract.total}`,
    `Rate limit: ${contract.rateLimitPerMinute} calls/minute`,
    `Dedupe window: ${contract.dedupeWindowHours} hours`,
    `Enabled automations ready: ${contract.enabledReadyCount}/${contract.enabledCount}`,
    '',
    'Contract checks:',
  ];

  contract.checks.forEach((check) => {
    lines.push(`- ${check.ready ? 'READY' : 'BLOCKED'}: ${check.label}`);
    if (!check.ready) {
      lines.push(`  Action: ${check.action}`);
    }
  });

  lines.push('', 'Automations:');
  contract.automations.forEach((automation) => {
    lines.push(
      `- ${automation.enabled ? 'ENABLED' : 'DISABLED'} / ${
        automation.ready ? 'READY' : 'BLOCKED'
      }: ${automation.label}`,
    );
    lines.push(`  ${automation.description}`);
    automation.blockedReasons.forEach((reason) => {
      lines.push(`  Blocker: ${reason}`);
    });
  });

  return lines.join('\n');
};
