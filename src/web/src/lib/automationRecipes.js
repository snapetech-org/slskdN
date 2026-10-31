import { interfaceText } from './interfaceLocale';
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
  const lines = [
    interfaceText("slskdN automation review history"),
    `Entries: ${history.length}`,
    '',
  ];

  if (history.length === 0) {
    lines.push('No enabled recipes or dry-run checkpoints.');
    return lines.join('\n');
  }

  history.forEach((entry) => {
    lines.push(`- ${entry.title}`);
    lines.push(`  Enabled: ${entry.enabled ? 'yes' : 'no'}`);
    lines.push(`  Last run: ${entry.lastRunAt || 'not recorded'}`);
    if (entry.lastRunReport) {
      lines.push(`  Run summary: ${entry.lastRunReport.summary}`);
      lines.push(`  Network impact: ${entry.lastRunReport.networkImpact}`);
      lines.push(`  File impact: ${entry.lastRunReport.fileImpact}`);
    }
    lines.push(`  Last dry run: ${entry.lastDryRunAt || 'not recorded'}`);
    if (entry.lastDryRunReport) {
      lines.push(`  Executed: ${entry.lastDryRunReport.executed ? 'yes' : 'no'}`);
      lines.push(`  Network impact: ${entry.lastDryRunReport.networkImpact}`);
      lines.push(`  File impact: ${entry.lastDryRunReport.fileImpact}`);
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
