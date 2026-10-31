import { interfaceText } from './interfaceLocale';
import { formatRegionalNumber } from './regionalFormat';

const localizeSetupHealthText = (source) => {
  switch (source) {
    case 'Needs attention':
      return interfaceText('Needs attention');
    case 'Review recommended':
      return interfaceText('Review recommended');
    case 'Ready':
      return interfaceText('Ready');
    case 'Network':
      return interfaceText('Network');
    case 'Access':
      return interfaceText('Access');
    case 'Storage':
      return interfaceText('Storage');
    case 'Operations':
      return interfaceText('Operations');
    case 'Soulseek session':
      return interfaceText('Soulseek session');
    case 'Account identity':
      return interfaceText('Account identity');
    case 'API access':
      return interfaceText('API access');
    case 'Shares':
      return interfaceText('Shares');
    case 'Downloads':
      return interfaceText('Downloads');
    case 'Runtime state':
      return interfaceText('Runtime state');
    case 'Web mounting':
      return interfaceText('Web mounting');
    case 'Remote configuration':
      return interfaceText('Remote configuration');
    case 'Provider credentials':
      return interfaceText('Provider credentials');
    case 'Queue pressure':
      return interfaceText('Queue pressure');
    case 'Job failures':
      return interfaceText('Job failures');
    case 'Automation visibility':
      return interfaceText('Automation visibility');
    case 'Connected':
      return interfaceText('Connected');
    case 'Not connected':
      return interfaceText('Not connected');
    case 'Identity loaded':
      return interfaceText('Identity loaded');
    case 'Identity missing':
      return interfaceText('Identity missing');
    case 'Authentication disabled':
      return interfaceText('Authentication disabled');
    case 'API key configured':
      return interfaceText('API key configured');
    case 'Optional: API key not configured':
      return interfaceText('Optional: API key not configured');
    case 'Shares configured':
      return interfaceText('Shares configured');
    case 'Optional: no shares configured':
      return interfaceText('Optional: no shares configured');
    case 'Download path configured':
      return interfaceText('Download path configured');
    case 'Download path missing':
      return interfaceText('Download path missing');
    case 'Restart pending':
      return interfaceText('Restart pending');
    case 'No restart pending':
      return interfaceText('No restart pending');
    case 'Subpath hosting configured':
      return interfaceText('Subpath hosting configured');
    case 'Root hosting configured':
      return interfaceText('Root hosting configured');
    case 'Runtime edits enabled':
      return interfaceText('Runtime edits enabled');
    case 'Runtime edits disabled':
      return interfaceText('Runtime edits disabled');
    case 'Optional provider credential gaps':
      return interfaceText('Optional provider credential gaps');
    case 'Provider credentials clear':
      return interfaceText('Provider credentials clear');
    case 'Queue pressure high':
      return interfaceText('Queue pressure high');
    case 'Queue pressure normal':
      return interfaceText('Queue pressure normal');
    case 'Failed jobs present':
      return interfaceText('Failed jobs present');
    case 'No failed jobs visible':
      return interfaceText('No failed jobs visible');
    case 'Automation visible':
      return interfaceText('Automation visible');
    case 'No automation state visible':
      return interfaceText('No automation state visible');
    case 'No action needed.':
      return interfaceText('No action needed.');
    case 'Verify credentials and network reachability before starting searches or transfers.':
      return interfaceText('Verify credentials and network reachability before starting searches or transfers.');
    case 'Log in or configure credentials so requests, messages, and transfer ownership have a local identity.':
      return interfaceText('Log in or configure credentials so requests, messages, and transfer ownership have a local identity.');
    case 'Enable authentication before exposing this Web UI outside a trusted local network.':
      return interfaceText('Enable authentication before exposing this Web UI outside a trusted local network.');
    case 'Optional: configure an API key only when using mutating API clients or automation integrations.':
      return interfaceText('Optional: configure an API key only when using mutating API clients or automation integrations.');
    case 'Review share paths if peers cannot browse your library.':
      return interfaceText('Review share paths if peers cannot browse your library.');
    case 'Sharing is optional. Add a share root only when you want other peers to browse selected folders.':
      return interfaceText('Sharing is optional. Add a share root only when you want other peers to browse selected folders.');
    case 'Configure a download folder before starting acquisition workflows.':
      return interfaceText('Configure a download folder before starting acquisition workflows.');
    case 'Restart after reviewing unsaved or runtime-only option changes.':
      return interfaceText('Restart after reviewing unsaved or runtime-only option changes.');
    case 'Use the subpath smoke check before tagging release builds that change frontend tooling.':
      return interfaceText('Use the subpath smoke check before tagging release builds that change frontend tooling.');
    case 'No action needed for root-hosted Web UI deployments.':
      return interfaceText('No action needed for root-hosted Web UI deployments.');
    case 'Review admin access before exposing the Web UI beyond trusted operators.':
      return interfaceText('Review admin access before exposing the Web UI beyond trusted operators.');
    case 'Use YAML save or restart flows for persistent settings changes.':
      return interfaceText('Use YAML save or restart flows for persistent settings changes.');
    case 'Review queued transfers before enabling more acquisition automation.':
      return interfaceText('Review queued transfers before enabling more acquisition automation.');
    case 'Open System -> Jobs and review failed job details before retrying automation.':
      return interfaceText('Open System -> Jobs and review failed job details before retrying automation.');
    case 'Review recipe dry-run reports before enabling unattended actions.':
      return interfaceText('Review recipe dry-run reports before enabling unattended actions.');
    case 'Add or review automation recipes only after diagnostics are clean.':
      return interfaceText('Add or review automation recipes only after diagnostics are clean.');
    case 'Connected state is true.':
      return interfaceText('Connected state is true.');
    case 'Connected state is not true.':
      return interfaceText('Connected state is not true.');
    case 'A local username is present.':
      return interfaceText('A local username is present.');
    case 'No local username is visible in state.':
      return interfaceText('No local username is visible in state.');
    case 'Web authentication is disabled.':
      return interfaceText('Web authentication is disabled.');
    case 'An API key is visible in options.':
      return interfaceText('An API key is visible in options.');
    case 'No API key is visible in options.':
      return interfaceText('No API key is visible in options.');
    case 'A download path is configured.':
      return interfaceText('A download path is configured.');
    case 'No download path is visible in options.':
      return interfaceText('No download path is visible in options.');
    case 'The daemon reports a pending restart.':
      return interfaceText('The daemon reports a pending restart.');
    case 'No pending restart is reported.':
      return interfaceText('No pending restart is reported.');
    case 'No URL base is configured.':
      return interfaceText('No URL base is configured.');
    case 'Runtime option changes are enabled.':
      return interfaceText('Runtime option changes are enabled.');
    case 'Runtime option changes are not enabled.':
      return interfaceText('Runtime option changes are not enabled.');
    case 'No enabled provider credential gaps were detected in loaded options.':
      return interfaceText('No enabled provider credential gaps were detected in loaded options.');
    case 'Configured URL base: {urlBase}':
      return interfaceText('Configured URL base: {urlBase}');
    case 'Add credentials or disable: {providers}.':
      return interfaceText('Add credentials or disable: {providers}.');
    case 'Pass':
      return interfaceText('Pass');
    case 'Warn':
      return interfaceText('Warn');
    case 'Fail':
      return interfaceText('Fail');
    case 'Info':
      return interfaceText('Info');
    default:
      return source;
  }
};

const localizeCheckStatus = (status) => {
  switch (status) {
    case 'pass':
      return localizeSetupHealthText('Pass');
    case 'warn':
      return localizeSetupHealthText('Warn');
    case 'fail':
      return localizeSetupHealthText('Fail');
    case 'info':
      return localizeSetupHealthText('Info');
    default:
      return status;
  }
};

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
  const formatEvidence = (source) => {
    const patterns = [
      [/^(\d+) share entry visible in options\.$/u, '{count} share entry visible in options.'],
      [/^(\d+) share entries visible in options\.$/u, '{count} share entries visible in options.'],
      [/^(\d+) enabled provider credential gap found\.$/u, '{count} enabled provider credential gap found.'],
      [/^(\d+) enabled provider credential gaps found\.$/u, '{count} enabled provider credential gaps found.'],
      [/^(\d+) active queued transfer item visible in state\.$/u, '{count} active queued transfer item visible in state.'],
      [/^(\d+) active queued transfer items visible in state\.$/u, '{count} active queued transfer items visible in state.'],
      [/^(\d+) failed job entry visible in state\.$/u, '{count} failed job entry visible in state.'],
      [/^(\d+) failed job entries visible in state\.$/u, '{count} failed job entries visible in state.'],
      [/^(\d+) automation recipe entry visible in state\.$/u, '{count} automation recipe entry visible in state.'],
      [/^(\d+) automation recipe entries visible in state\.$/u, '{count} automation recipe entries visible in state.'],
    ];
    for (const [pattern, template] of patterns) {
      const match = source.match(pattern);
      if (match) return interfaceText(template, { count: formatRegionalNumber(Number(match[1])) });
    }
    const urlMatch = source.match(/^Configured URL base: (.*)$/u);
    if (urlMatch) return interfaceText('Configured URL base: {urlBase}', { urlBase: urlMatch[1] });
    return localizeSetupHealthText(source);
  };
  const formatAction = (source) => {
    const providerMatch = source.match(/^Add credentials or disable: (.*)\.$/u);
    return providerMatch
      ? interfaceText('Add credentials or disable: {providers}.', { providers: providerMatch[1] })
      : localizeSetupHealthText(source);
  };

  const lines = [
    interfaceText('slskdN setup health check'),
    interfaceText('Readiness: {readiness}', { readiness: localizeSetupHealthText(summary.readiness) }),
    interfaceText('Score: {score}/100', { score: formatRegionalNumber(summary.score) }),
    interfaceText('Pass: {pass}  Warn: {warn}  Fail: {fail}', {
      fail: formatRegionalNumber(summary.totals.fail),
      pass: formatRegionalNumber(summary.totals.pass),
      warn: formatRegionalNumber(summary.totals.warn),
    }),
    '',
  ];

  if (summary.nextSteps.length > 0) {
    lines.push(interfaceText('Next steps:'));
    summary.nextSteps.forEach((item) => {
      lines.push(interfaceText('- [{severity}] {area}: {action}', {
        action: formatAction(item.action),
        area: localizeSetupHealthText(item.area),
        severity: localizeCheckStatus(item.severity),
      }));
    });
    lines.push('');
  }

  summary.checks.forEach((item) => {
    lines.push(interfaceText('[{status}] {group} / {area}: {summary}', {
      area: localizeSetupHealthText(item.area),
      group: localizeSetupHealthText(item.group),
      status: localizeCheckStatus(item.status),
      summary: localizeSetupHealthText(item.summary),
    }));
    lines.push(interfaceText('Evidence: {evidence}', { evidence: formatEvidence(item.evidence) }));
    lines.push(interfaceText('Action: {action}', { action: formatAction(item.action) }));
    lines.push('');
  });

  return lines.join('\n').trim();
};
