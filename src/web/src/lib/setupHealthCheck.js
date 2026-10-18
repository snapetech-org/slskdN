const getPath = (value, paths) => {
  for (const path of paths) {
    const result = path.reduce((current, key) => {
      if (!current || typeof current !== 'object') return undefined;
      return current[key];
    }, value);

    if (result !== undefined && result !== null) return result;
  }

  return undefined;
};

const asArray = (value) => {
  if (Array.isArray(value)) return value;
  if (value && typeof value === 'object') return Object.values(value);
  return [];
};

const hasValue = (value) => {
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === 'string') return value.trim().length > 0;
  return value !== undefined && value !== null && value !== false;
};

const check = ({ action, area, destination, evidence, group, status, summary }) => ({
  action,
  area,
  destination,
  evidence,
  group,
  status,
  summary,
});

const getEnabledIntegrationGaps = (options = {}) => {
  const integrations = getPath(options, [
    ['integration'],
    ['integrations'],
    ['Integration'],
    ['Integrations'],
  ]) || {};
  const providers = [
    ['Spotify', integrations.spotify || integrations.Spotify],
    [
      'YouTube',
      integrations.youtube || integrations.youTube || integrations.YouTube,
    ],
    [
      'Last.fm',
      integrations.lastfm ||
        integrations.lastFm ||
        integrations.LastFm ||
        integrations.lastFM,
    ],
  ];

  return providers
    .filter(([, provider]) => provider?.enabled || provider?.Enabled)
    .filter(([, provider]) => !hasValue(provider.apiKey || provider.ApiKey))
    .map(([name]) => name);
};

const getQueueDepth = (state = {}) =>
  asArray(
    getPath(state, [
      ['transfers', 'downloads'],
      ['Transfers', 'Downloads'],
      ['downloads'],
      ['Downloads'],
    ]),
  ).filter((item) => !['Completed', 'Cancelled', 'Failed'].includes(item.state)).length;

export const buildSetupHealthChecks = ({ options = {}, state = {} } = {}) => {
  const shares = asArray(
    getPath(options, [
      ['shares', 'directories'],
      ['Shares', 'Directories'],
      ['shares'],
      ['Shares'],
    ]),
  );
  const downloads = getPath(options, [
    ['directories', 'downloads'],
    ['Directories', 'Downloads'],
    ['downloads', 'directory'],
    ['Downloads', 'Directory'],
  ]);
  const username = getPath(state, [
    ['user', 'username'],
    ['User', 'Username'],
  ]);
  const urlBase = getPath(options, [
    ['web', 'urlBase'],
    ['web', 'url_base'],
    ['Web', 'UrlBase'],
    ['Web', 'Url_Base'],
  ]);
  const remoteConfiguration = getPath(options, [
    ['remoteConfiguration'],
    ['RemoteConfiguration'],
    ['web', 'remoteConfiguration'],
    ['Web', 'RemoteConfiguration'],
  ]);
  const soulseekConnected = getPath(state, [
    ['connected'],
    ['isConnected'],
    ['server', 'connected'],
    ['server', 'isConnected'],
    ['Server', 'Connected'],
    ['Server', 'IsConnected'],
  ]);
  const pendingRestart = getPath(state, [
    ['pendingRestart'],
    ['PendingRestart'],
  ]);
  const apiKey = getPath(options, [
    ['web', 'authentication', 'apiKey'],
    ['Web', 'Authentication', 'ApiKey'],
    ['apiKey'],
    ['ApiKey'],
  ]);
  const apiKeys = asArray(
    getPath(options, [
      ['web', 'authentication', 'apiKeys'],
      ['web', 'authentication', 'api_keys'],
      ['Web', 'Authentication', 'ApiKeys'],
    ]),
  );
  const apiKeyConfigured =
    hasValue(apiKey) ||
    apiKeys.some((entry) => hasValue(entry?.key || entry?.Key || entry));
  const authDisabled =
    getPath(options, [
      ['web', 'authentication', 'disabled'],
      ['Web', 'Authentication', 'Disabled'],
    ]) === true;
  const enabledProviderGaps = getEnabledIntegrationGaps(options);
  const queueDepth = getQueueDepth(state);
  const automationRecipes = asArray(
    getPath(state, [
      ['automation', 'recipes'],
      ['Automation', 'Recipes'],
      ['recipes'],
      ['Recipes'],
    ]),
  );
  const failedJobs = asArray(
    getPath(state, [
      ['jobs'],
      ['Jobs'],
    ]),
  ).filter((job) => ['Failed', 'Faulted', 'Error'].includes(job.state || job.State));

  const checks = [
    check({
      action: soulseekConnected
        ? 'No action needed.'
        : 'Verify credentials and network reachability before starting searches or transfers.',
      area: 'Soulseek session',
      destination: soulseekConnected ? undefined : { label: 'Options', path: '/system/options' },
      evidence: soulseekConnected ? 'Connected state is true.' : 'Connected state is not true.',
      group: 'Network',
      status: soulseekConnected ? 'pass' : 'fail',
      summary: soulseekConnected ? 'Connected' : 'Not connected',
    }),
    check({
      action: hasValue(username)
        ? 'No action needed.'
        : 'Log in or configure credentials so requests, messages, and transfer ownership have a local identity.',
      area: 'Account identity',
      evidence: hasValue(username) ? 'A local username is present.' : 'No local username is visible in state.',
      group: 'Access',
      status: hasValue(username) ? 'pass' : 'warn',
      summary: hasValue(username) ? 'Identity loaded' : 'Identity missing',
    }),
    check({
      action: authDisabled
        ? 'Enable authentication before exposing this Web UI outside a trusted local network.'
        : apiKeyConfigured
          ? 'No action needed.'
          : 'Optional: configure an API key only when using mutating API clients or automation integrations.',
      destination: authDisabled || !apiKeyConfigured
        ? { label: 'Policies', path: '/system/policies' }
        : undefined,
      area: 'API access',
      evidence: authDisabled
        ? 'Web authentication is disabled.'
        : apiKeyConfigured
          ? 'An API key is visible in options.'
          : 'No API key is visible in options.',
      group: 'Access',
      status: authDisabled ? 'fail' : apiKeyConfigured ? 'pass' : 'info',
      summary: authDisabled
        ? 'Authentication disabled'
        : apiKeyConfigured
          ? 'API key configured'
          : 'Optional: API key not configured',
    }),
    check({
      action: shares.length
        ? 'Review share paths if peers cannot browse your library.'
        : 'Sharing is optional. Add a share root only when you want other peers to browse selected folders.',
      area: 'Shares',
      destination: { label: 'Shares', path: '/system/shares' },
      evidence: `${shares.length} share ${shares.length === 1 ? 'entry' : 'entries'} visible in options.`,
      group: 'Storage',
      status: shares.length ? 'pass' : 'info',
      summary: shares.length ? 'Shares configured' : 'Optional: no shares configured',
    }),
    check({
      action: hasValue(downloads)
        ? 'No action needed.'
        : 'Configure a download folder before starting acquisition workflows.',
      area: 'Downloads',
      destination: hasValue(downloads) ? undefined : { label: 'Options', path: '/system/options' },
      evidence: hasValue(downloads) ? 'A download path is configured.' : 'No download path is visible in options.',
      group: 'Storage',
      status: hasValue(downloads) ? 'pass' : 'fail',
      summary: hasValue(downloads) ? 'Download path configured' : 'Download path missing',
    }),
    check({
      action: pendingRestart
        ? 'Restart after reviewing unsaved or runtime-only option changes.'
        : 'No action needed.',
      area: 'Runtime state',
      evidence: pendingRestart ? 'The daemon reports a pending restart.' : 'No pending restart is reported.',
      group: 'Operations',
      status: pendingRestart ? 'warn' : 'pass',
      summary: pendingRestart ? 'Restart pending' : 'No restart pending',
    }),
    check({
      action: hasValue(urlBase)
        ? 'Use the subpath smoke check before tagging release builds that change frontend tooling.'
        : 'No action needed for root-hosted Web UI deployments.',
      area: 'Web mounting',
      evidence: hasValue(urlBase) ? `Configured URL base: ${urlBase}` : 'No URL base is configured.',
      group: 'Access',
      status: 'pass',
      summary: hasValue(urlBase) ? 'Subpath hosting configured' : 'Root hosting configured',
    }),
    check({
      action: remoteConfiguration
        ? 'Review admin access before exposing the Web UI beyond trusted operators.'
        : 'Use YAML save or restart flows for persistent settings changes.',
      area: 'Remote configuration',
      evidence: remoteConfiguration
        ? 'Runtime option changes are enabled.'
        : 'Runtime option changes are not enabled.',
      group: 'Operations',
      status: remoteConfiguration ? 'warn' : 'pass',
      summary: remoteConfiguration ? 'Runtime edits enabled' : 'Runtime edits disabled',
    }),
    check({
      action: enabledProviderGaps.length
        ? `Add credentials or disable: ${enabledProviderGaps.join(', ')}.`
        : 'No action needed.',
      area: 'Provider credentials',
      destination: enabledProviderGaps.length ? { label: 'Options', path: '/system/options' } : undefined,
      evidence: enabledProviderGaps.length
        ? `${enabledProviderGaps.length} enabled provider credential ${enabledProviderGaps.length === 1 ? 'gap' : 'gaps'} found.`
        : 'No enabled provider credential gaps were detected in loaded options.',
      group: 'Operations',
      status: enabledProviderGaps.length ? 'info' : 'pass',
      summary: enabledProviderGaps.length ? 'Optional provider credential gaps' : 'Provider credentials clear',
    }),
    check({
      action: queueDepth > 25
        ? 'Review queued transfers before enabling more acquisition automation.'
        : 'No action needed.',
      area: 'Queue pressure',
      evidence: `${queueDepth} active queued transfer ${queueDepth === 1 ? 'item' : 'items'} visible in state.`,
      group: 'Operations',
      status: queueDepth > 25 ? 'warn' : 'pass',
      summary: queueDepth > 25 ? 'Queue pressure high' : 'Queue pressure normal',
    }),
    check({
      action: failedJobs.length
        ? 'Open System -> Jobs and review failed job details before retrying automation.'
        : 'No action needed.',
      area: 'Job failures',
      evidence: `${failedJobs.length} failed job ${failedJobs.length === 1 ? 'entry' : 'entries'} visible in state.`,
      group: 'Operations',
      status: failedJobs.length ? 'warn' : 'pass',
      summary: failedJobs.length ? 'Failed jobs present' : 'No failed jobs visible',
    }),
    check({
      action: automationRecipes.length
        ? 'Review recipe dry-run reports before enabling unattended actions.'
        : 'Add or review automation recipes only after diagnostics are clean.',
      area: 'Automation visibility',
      evidence: `${automationRecipes.length} automation recipe ${automationRecipes.length === 1 ? 'entry' : 'entries'} visible in state.`,
      group: 'Operations',
      status: 'pass',
      summary: automationRecipes.length ? 'Automation visible' : 'No automation state visible',
    }),
  ];

  const totals = checks.reduce(
    (result, item) => ({
      ...result,
      [item.status]: result[item.status] + 1,
    }),
    { fail: 0, info: 0, pass: 0, warn: 0 },
  );

  const score = Math.max(
    0,
    Math.min(100, 100 - (totals.fail * 22) - (totals.warn * 9)),
  );
  const nextSteps = checks
    .filter((item) => item.status === 'fail' || item.status === 'warn')
    .map((item) => ({
      action: item.action,
      area: item.area,
      destination: item.destination,
      group: item.group,
      severity: item.status,
    }))
    .slice(0, 5);
  const groups = checks.reduce((result, item) => {
    const existing = result[item.group] || { fail: 0, info: 0, pass: 0, total: 0, warn: 0 };
    return {
      ...result,
      [item.group]: {
        ...existing,
        [item.status]: existing[item.status] + 1,
        total: existing.total + 1,
      },
    };
  }, {});

  return {
    checks,
    groups,
    nextSteps,
    readiness:
      totals.fail > 0 ? 'Needs attention' : totals.warn > 0 ? 'Review recommended' : 'Ready',
    score,
    totals,
  };
};

export const formatSetupHealthReport = (summary) => {
  const lines = [
    'slskdN setup health check',
    `Readiness: ${summary.readiness}`,
    `Score: ${summary.score}/100`,
    `Pass: ${summary.totals.pass}  Warn: ${summary.totals.warn}  Fail: ${summary.totals.fail}`,
    '',
  ];

  if (summary.nextSteps.length > 0) {
    lines.push('Next steps:');
    summary.nextSteps.forEach((item) => {
      lines.push(`- [${item.severity.toUpperCase()}] ${item.area}: ${item.action}`);
    });
    lines.push('');
  }

  summary.checks.forEach((item) => {
    lines.push(`[${item.status.toUpperCase()}] ${item.group} / ${item.area}: ${item.summary}`);
    lines.push(`Evidence: ${item.evidence}`);
    lines.push(`Action: ${item.action}`);
    lines.push('');
  });

  return lines.join('\n').trim();
};
