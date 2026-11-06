import { interfaceText } from './interfaceLocale';
import { formatRegionalNumber } from './regionalFormat';
import {
  getLocalStorageItem,
  removeLocalStorageItem,
  setLocalStorageItem,
} from './storage';

const storageKey = 'slskdn.automationRecipeState';
const inputStorageKey = 'slskdn.automationRecipeInputs';
const executableRecipeIds = new Set(['wishlist-retry', 'library-health-scan']);

export const automationRecipes = [
  {
    approvalGate: 'None required',
    cadence: 'Continuous',
    cooldown: '5 minutes',
    description: 'Checks connection, shares, paths, and credentials for setup drift.',
    enabledByDefault: true,
    fileImpact: 'Read only',
    icon: 'stethoscope',
    id: 'local-diagnostics',
    maxRunTime: '30 seconds',
    networkImpact: 'Local',
    title: 'Local Diagnostics',
  },
  {
    approvalGate: 'None required',
    cadence: 'Daily',
    cooldown: '24 hours',
    description: 'Surfaces stale share-cache and library-scan reminders before users hit missing results.',
    enabledByDefault: true,
    fileImpact: 'Read only',
    icon: 'bell outline',
    id: 'stale-cache-reminders',
    maxRunTime: '1 minute',
    networkImpact: 'Local',
    title: 'Share and Library Reminders',
  },
  {
    approvalGate: 'None required',
    cadence: 'Every 15 minutes',
    cooldown: '15 minutes',
    description: 'Keeps local dashboard summaries fresh without contacting public peers.',
    enabledByDefault: true,
    fileImpact: 'Read only',
    icon: 'dashboard',
    id: 'dashboard-refresh',
    maxRunTime: '20 seconds',
    networkImpact: 'Local',
    title: 'Dashboard Refresh',
  },
  {
    approvalGate: 'Download approval',
    cadence: 'Manual or scheduled',
    cooldown: '2 hours',
    description: 'Retries failed Wishlist items using the selected acquisition profile.',
    enabledByDefault: false,
    fileImpact: 'Downloads after approval',
    icon: 'redo',
    id: 'wishlist-retry',
    maxRunTime: '20 minutes',
    networkImpact: 'Public peers possible',
    title: 'Wishlist Retry',
  },
  {
    approvalGate: 'Fix confirmation',
    cadence: 'Manual or scheduled',
    cooldown: '24 hours',
    description: 'Finds duplicates, dead files, metadata gaps, fake lossless files, and missing art.',
    enabledByDefault: false,
    fileImpact: 'Read only until fixed',
    icon: 'heartbeat',
    id: 'library-health-scan',
    maxRunTime: '30 minutes',
    networkImpact: 'Local',
    title: 'Library Health Scan',
  },
  {
    approvalGate: 'Configured import success',
    cadence: 'After import',
    cooldown: '10 minutes',
    description: 'Asks configured media servers to rescan after successful library imports.',
    enabledByDefault: false,
    fileImpact: 'Media-server scan',
    icon: 'server',
    id: 'media-server-rescan',
    maxRunTime: '2 minutes',
    networkImpact: 'Local network',
    title: 'Media Server Rescan',
  },
  {
    approvalGate: 'Explicit evidence publication opt-in',
    cadence: 'Manual or scheduled',
    cooldown: '12 hours',
    description: 'Publishes explicit opt-in signed quality and verification evidence to trusted mesh peers.',
    enabledByDefault: false,
    fileImpact: 'No file writes',
    icon: 'share alternate',
    id: 'mesh-evidence-publish',
    maxRunTime: '10 minutes',
    networkImpact: 'Trusted mesh',
    title: 'Mesh Evidence Publish',
  },
];

const localizeAutomationRecipeCopy = (value) => {
  switch (value) {
    case 'Local Diagnostics':
      return interfaceText('Local Diagnostics');
    case 'Share and Library Reminders':
      return interfaceText('Share and Library Reminders');
    case 'Dashboard Refresh':
      return interfaceText('Dashboard Refresh');
    case 'Wishlist Retry':
      return interfaceText('Wishlist Retry');
    case 'Library Health Scan':
      return interfaceText('Library Health Scan');
    case 'Media Server Rescan':
      return interfaceText('Media Server Rescan');
    case 'Mesh Evidence Publish':
      return interfaceText('Mesh Evidence Publish');
    case 'Checks connection, shares, paths, and credentials for setup drift.':
      return interfaceText('Checks connection, shares, paths, and credentials for setup drift.');
    case 'Surfaces stale share-cache and library-scan reminders before users hit missing results.':
      return interfaceText('Surfaces stale share-cache and library-scan reminders before users hit missing results.');
    case 'Keeps local dashboard summaries fresh without contacting public peers.':
      return interfaceText('Keeps local dashboard summaries fresh without contacting public peers.');
    case 'Retries failed Wishlist items using the selected acquisition profile.':
      return interfaceText('Retries failed Wishlist items using the selected acquisition profile.');
    case 'Finds duplicates, dead files, metadata gaps, fake lossless files, and missing art.':
      return interfaceText('Finds duplicates, dead files, metadata gaps, fake lossless files, and missing art.');
    case 'Asks configured media servers to rescan after successful library imports.':
      return interfaceText('Asks configured media servers to rescan after successful library imports.');
    case 'Publishes explicit opt-in signed quality and verification evidence to trusted mesh peers.':
      return interfaceText('Publishes explicit opt-in signed quality and verification evidence to trusted mesh peers.');
    case 'None required':
      return interfaceText('None required');
    case 'Download approval':
      return interfaceText('Download approval');
    case 'Fix confirmation':
      return interfaceText('Fix confirmation');
    case 'Configured import success':
      return interfaceText('Configured import success');
    case 'Explicit evidence publication opt-in':
      return interfaceText('Explicit evidence publication opt-in');
    case 'Continuous':
      return interfaceText('Continuous');
    case 'Daily':
      return interfaceText('Daily');
    case 'Every 15 minutes':
      return interfaceText('Every 15 minutes');
    case 'Manual or scheduled':
      return interfaceText('Manual or scheduled');
    case 'After import':
      return interfaceText('After import');
    case '5 minutes':
      return interfaceText('5 minutes');
    case '24 hours':
      return interfaceText('24 hours');
    case '15 minutes':
      return interfaceText('15 minutes');
    case '2 hours':
      return interfaceText('2 hours');
    case '10 minutes':
      return interfaceText('10 minutes');
    case '12 hours':
      return interfaceText('12 hours');
    case '30 seconds':
      return interfaceText('30 seconds');
    case '1 minute':
      return interfaceText('1 minute');
    case '20 seconds':
      return interfaceText('20 seconds');
    case '20 minutes':
      return interfaceText('20 minutes');
    case '30 minutes':
      return interfaceText('30 minutes');
    case '2 minutes':
      return interfaceText('2 minutes');
    case 'Local':
      return interfaceText('Local');
    case 'Public peers possible':
      return interfaceText('Public peers possible');
    case 'Local network':
      return interfaceText('Local network');
    case 'Trusted mesh':
      return interfaceText('Trusted mesh');
    case 'Read only':
      return interfaceText('Read only');
    case 'Downloads after approval':
      return interfaceText('Downloads after approval');
    case 'Read only until fixed':
      return interfaceText('Read only until fixed');
    case 'Media-server scan':
      return interfaceText('Media-server scan');
    case 'No file writes':
      return interfaceText('No file writes');
    default:
      return value;
  }
};

const defaultState = automationRecipes.reduce((state, recipe) => {
  state[recipe.id] = {
    enabled: recipe.enabledByDefault,
    lastDryRunAt: null,
  };
  return state;
}, {});

const readStoredState = () => {
  const stored = getLocalStorageItem(storageKey);
  if (!stored) {
    return {};
  }

  try {
    const parsed = JSON.parse(stored);
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? parsed
      : {};
  } catch {
    removeLocalStorageItem(storageKey);
    return {};
  }
};

const readStoredInputs = () => {
  const stored = getLocalStorageItem(inputStorageKey);
  if (!stored) {
    return {};
  }

  try {
    const parsed = JSON.parse(stored);
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? parsed
      : {};
  } catch {
    removeLocalStorageItem(inputStorageKey);
    return {};
  }
};

export const buildAutomationDryRunReport = (
  recipe,
  timestamp = new Date().toISOString(),
) => ({
  approvalGate: recipe.approvalGate,
  cooldown: recipe.cooldown,
  executed: false,
  fileImpact: recipe.fileImpact,
  generatedAt: timestamp,
  maxRunTime: recipe.maxRunTime,
  networkImpact: recipe.networkImpact,
  recipeId: recipe.id,
  title: recipe.title,
});

export const isAutomationRecipeExecutable = (recipe) =>
  executableRecipeIds.has(recipe?.id);

export const buildAutomationExecutionReport = (
  recipe,
  result = {},
  timestamp = new Date().toISOString(),
) => ({
  approvalGate: recipe.approvalGate,
  cooldown: recipe.cooldown,
  executed: true,
  failed: result.failed || 0,
  fileImpact: recipe.fileImpact,
  generatedAt: timestamp,
  maxRunTime: recipe.maxRunTime,
  networkImpact: recipe.networkImpact,
  recipeId: recipe.id,
  runLimit: result.runLimit || 0,
  ...(result.scanId ? { scanId: result.scanId } : {}),
  ...(typeof result.libraryPath === 'string' ? { libraryPath: result.libraryPath } : {}),
  skipped: result.skipped || 0,
  started: result.started || 0,
  summary:
    result.summary ||
    `Started ${result.started || 0} action(s); ${result.failed || 0} failed; ${result.skipped || 0} skipped.`,
  title: recipe.title,
});

export const buildAutomationRunHistory = (state = getAutomationRecipeState()) =>
  automationRecipes
    .map((recipe) => ({
      enabled: state[recipe.id]?.enabled === true,
      lastDryRunAt: state[recipe.id]?.lastDryRunAt || null,
      lastDryRunReport: state[recipe.id]?.lastDryRunReport || null,
      lastRunAt: state[recipe.id]?.lastRunAt || null,
      lastRunReport: state[recipe.id]?.lastRunReport || null,
      recipeId: recipe.id,
      title: recipe.title,
    }))
    .filter((entry) => entry.enabled || entry.lastDryRunAt || entry.lastRunAt);

export const formatAutomationRunHistoryReport = (
  history = buildAutomationRunHistory(),
) => {
  const formatRunSummary = (report) => {
    if (!report || typeof report !== 'object') return '';
    if (report.recipeId === 'wishlist-retry' && Number.isFinite(report.started)) {
      return interfaceText('Ran {started} Wishlist searches; {failed} failed; {skipped} skipped.', {
        failed: formatRegionalNumber(report.failed || 0),
        skipped: formatRegionalNumber(report.skipped || 0),
        started: formatRegionalNumber(report.started || 0),
      });
    }
    if (report.recipeId === 'library-health-scan' && report.scanId && typeof report.libraryPath === 'string') {
      return interfaceText('Started Library Health scan {scanId} for {libraryPath}.', {
        libraryPath: report.libraryPath,
        scanId: report.scanId,
      });
    }

    // Older saved reports contain the same app-authored English templates.
    // Keep unknown backend or user-provided summaries verbatim.
    const summary = typeof report.summary === 'string' ? report.summary : '';
    const wishlistMatch = summary.match(/^Ran (\d+) Wishlist searches; (\d+) failed; (\d+) skipped\.$/u);
    if (report.recipeId === 'wishlist-retry' && wishlistMatch) {
      return interfaceText('Ran {started} Wishlist searches; {failed} failed; {skipped} skipped.', {
        failed: formatRegionalNumber(Number(wishlistMatch[2])),
        skipped: formatRegionalNumber(Number(wishlistMatch[3])),
        started: formatRegionalNumber(Number(wishlistMatch[1])),
      });
    }
    const healthMatch = summary.match(/^Started Library Health scan (.+) for (.*)\.$/u);
    if (report.recipeId === 'library-health-scan' && healthMatch) {
      return interfaceText('Started Library Health scan {scanId} for {libraryPath}.', {
        libraryPath: healthMatch[2],
        scanId: healthMatch[1],
      });
    }
    return summary;
  };

  const lines = [
    interfaceText("slskdN automation review history"),
    interfaceText('Entries: {count}', { count: formatRegionalNumber(history.length) }),
    '',
  ];

  if (history.length === 0) {
    lines.push(interfaceText('No enabled recipes or dry-run checkpoints.'));
    return lines.join('\n');
  }

  history.forEach((entry) => {
    lines.push(interfaceText('- {title}', { title: localizeAutomationRecipeCopy(entry.title) }));
    lines.push(interfaceText('  Enabled: {enabled}', {
      enabled: interfaceText(entry.enabled ? 'yes' : 'no'),
    }));
    lines.push(interfaceText('  Last run: {time}', {
      time: entry.lastRunAt || interfaceText('not recorded'),
    }));
    if (entry.lastRunReport) {
      lines.push(interfaceText('  Run summary: {summary}', {
        summary: formatRunSummary(entry.lastRunReport),
      }));
      lines.push(interfaceText('  Network impact: {impact}', {
        impact: localizeAutomationRecipeCopy(entry.lastRunReport.networkImpact),
      }));
      lines.push(interfaceText('  File impact: {impact}', {
        impact: localizeAutomationRecipeCopy(entry.lastRunReport.fileImpact),
      }));
    }
    lines.push(interfaceText('  Last dry run: {time}', {
      time: entry.lastDryRunAt || interfaceText('not recorded'),
    }));
    if (entry.lastDryRunReport) {
      lines.push(interfaceText('  Executed: {executed}', {
        executed: interfaceText(entry.lastDryRunReport.executed ? 'yes' : 'no'),
      }));
      lines.push(interfaceText('  Network impact: {impact}', {
        impact: localizeAutomationRecipeCopy(entry.lastDryRunReport.networkImpact),
      }));
      lines.push(interfaceText('  File impact: {impact}', {
        impact: localizeAutomationRecipeCopy(entry.lastDryRunReport.fileImpact),
      }));
    }
  });

  return lines.join('\n');
};

export const getAutomationRecipeState = () => ({
  ...defaultState,
  ...readStoredState(),
});

export const getAutomationRecipeInputs = () => readStoredInputs();

export const setAutomationRecipeInput = (id, input) => {
  const inputs = getAutomationRecipeInputs();
  const nextInputs = {
    ...inputs,
    [id]: {
      ...(inputs[id] || {}),
      ...input,
    },
  };

  setLocalStorageItem(inputStorageKey, JSON.stringify(nextInputs));
  return nextInputs;
};

export const setAutomationRecipeEnabled = (id, enabled) => {
  const state = getAutomationRecipeState();
  const recipeState = state[id] ?? {};
  const nextState = {
    ...state,
    [id]: {
      ...recipeState,
      enabled,
    },
  };

  setLocalStorageItem(storageKey, JSON.stringify(nextState));
  return nextState;
};

export const setAutomationRecipeDryRun = (id, timestamp = new Date().toISOString()) => {
  const state = getAutomationRecipeState();
  const recipeState = state[id] ?? {};
  const recipe = automationRecipes.find((item) => item.id === id);
  const nextState = {
    ...state,
    [id]: {
      ...recipeState,
      lastDryRunAt: timestamp,
      lastDryRunReport: recipe
        ? buildAutomationDryRunReport(recipe, timestamp)
        : undefined,
    },
  };

  setLocalStorageItem(storageKey, JSON.stringify(nextState));
  return nextState;
};

export const setAutomationRecipeExecution = (
  id,
  report,
  timestamp = new Date().toISOString(),
) => {
  const state = getAutomationRecipeState();
  const recipeState = state[id] ?? {};
  const nextState = {
    ...state,
    [id]: {
      ...recipeState,
      lastRunAt: timestamp,
      lastRunReport: report,
    },
  };

  setLocalStorageItem(storageKey, JSON.stringify(nextState));
  return nextState;
};

export const automationRecipeStorageKey = storageKey;
export const automationRecipeInputStorageKey = inputStorageKey;
