// Column definitions for the Downloads/Uploads transfer table.
// Column visibility, order, and widths are persisted to localStorage per direction.

const STORAGE_KEY = 'slskdn-transfer-columns';

export const ALL_COLUMNS = [
  { key: 'name',       label: 'Name',       sortable: true,  defaultWidth: 200, defaultVisible: true,  fixed: false },
  { key: 'peer',       label: 'Peer',       sortable: true,  defaultWidth: 90,  defaultVisible: true,  fixed: false },
  { key: 'extension',  label: 'Type',       sortable: true,  defaultWidth: 56,  defaultVisible: false, fixed: false },
  { key: 'size',       label: 'Size',       sortable: true,  defaultWidth: 120, defaultVisible: true,  fixed: false },
  { key: 'progress',   label: 'Progress',   sortable: true,  defaultWidth: 160, defaultVisible: true,  fixed: false },
  { key: 'speed',      label: 'Speed',      sortable: true,  defaultWidth: 90,  defaultVisible: true,  fixed: false },
  { key: 'bitrate',    label: 'Bitrate',   sortable: true,  defaultWidth: 60,  defaultVisible: true,  fixed: false },
  { key: 'samplerate', label: 'SampleRate',sortable: true,  defaultWidth: 70,  defaultVisible: false, fixed: false },
  { key: 'length',     label: 'Length',    sortable: true,  defaultWidth: 60,  defaultVisible: true,  fixed: false },
  { key: 'eta',        label: 'ETA',        sortable: true,  defaultWidth: 72,  defaultVisible: true,  fixed: false },
  { key: 'state',      label: 'State',      sortable: true,  defaultWidth: 90,  defaultVisible: true,  fixed: false },
  { key: 'directory',  label: 'Remote Folder', sortable: true, defaultWidth: 160, defaultVisible: true, fixed: false },
  { key: 'local',      label: 'Local File',  sortable: true,  defaultWidth: 180, defaultVisible: false, fixed: false },
  { key: 'artist',     label: 'Artist',     sortable: true,  defaultWidth: 120, defaultVisible: false, fixed: false },
  { key: 'album',      label: 'Album',      sortable: true,  defaultWidth: 140, defaultVisible: false, fixed: false },
  { key: 'title',      label: 'Title',      sortable: true,  defaultWidth: 140, defaultVisible: false, fixed: false },
  { key: 'track',      label: 'Track',      sortable: true,  defaultWidth: 55,  defaultVisible: false, fixed: false },
  { key: 'year',       label: 'Year',       sortable: true,  defaultWidth: 55,  defaultVisible: false, fixed: false },
  { key: 'elapsed',    label: 'Elapsed',    sortable: true,  defaultWidth: 70,  defaultVisible: false, fixed: false },
  { key: 'remaining',  label: 'Remaining',  sortable: true,  defaultWidth: 90,  defaultVisible: false, fixed: false },
  { key: 'started',    label: 'Added',      sortable: true,  defaultWidth: 110, defaultVisible: false, fixed: false },
  { key: 'requested',  label: 'Requested',  sortable: true,  defaultWidth: 150, defaultVisible: true,  fixed: false },
  { key: 'completed',  label: 'Done',       sortable: true,  defaultWidth: 110, defaultVisible: false, fixed: false },
  { key: 'actions',    label: '',           sortable: false, defaultWidth: 90,  defaultVisible: true,  fixed: true },
];

// Immutable columns always shown at fixed positions
const FIXED_LEFT = ['checkbox'];
const FIXED_RIGHT = ['actions'];

function getStorageKey(direction) {
  return `${STORAGE_KEY}-${direction}`;
}

function read(direction) {
  try {
    const raw = localStorage.getItem(getStorageKey(direction));
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function write(direction, state) {
  localStorage.setItem(getStorageKey(direction), JSON.stringify(state));
}

// Build default column order from ALL_COLUMNS (non-fixed columns in definition order)
function defaultOrder() {
  return ALL_COLUMNS
    .filter((c) => !c.fixed)
    .map((c) => c.key);
}

// Default widths map
function defaultWidths() {
  const widths = {};
  for (const col of ALL_COLUMNS) {
    widths[col.key] = col.defaultWidth;
  }
  return widths;
}

export function defaultColumnWidths() {
  return defaultWidths();
}

function detectMissing(keys) {
  const defined = ALL_COLUMNS.filter((c) => !c.fixed).map((c) => c.key);
  const validKeys = Array.isArray(keys)
    ? keys.filter((key, index) => defined.includes(key) && keys.indexOf(key) === index)
    : [];
  const missing = defined.filter((k) => !validKeys.includes(k));
  return [...validKeys, ...missing];
}

/**
 * Load persisted column state for a transfer direction.
 * Returns { order, visible, widths }.
 */
export function loadColumnState(direction) {
  const saved = read(direction);
  const defaultVis = {};
  for (const col of ALL_COLUMNS) {
    defaultVis[col.key] = col.defaultVisible;
  }

  if (!saved) {
    return {
      order: defaultOrder(),
      visible: { ...defaultVis },
      widths: defaultColumnWidths(),
    };
  }

  // Merge saved state with defaults, add any new columns
  const order = detectMissing(saved.order || defaultOrder());
  const visible = { ...defaultVis };
  for (const col of ALL_COLUMNS) {
    if (typeof saved.visible?.[col.key] === 'boolean') {
      visible[col.key] = saved.visible[col.key];
    }
  }
  const widths = { ...defaultColumnWidths() };
  for (const col of ALL_COLUMNS) {
    const width = Number(saved.widths?.[col.key]);
    if (Number.isFinite(width) && width >= columnMinWidth(col.key)) {
      widths[col.key] = width;
    }
  }

  return { order, visible, widths };
}

/**
 * Persist column state for a transfer direction.
 */
export function saveColumnState(direction, state) {
  write(direction, state);
}

/**
 * Return ordered list of visible column keys (excluding fixed columns).
 */
export function visibleColumnKeys(state) {
  return state.order.filter((k) => state.visible[k]);
}

/**
 * Return visible column definitions in the user's persisted order. Headers,
 * row cells, and grid tracks must all consume this same sequence.
 */
export function visibleColumnDefinitions(state) {
  const columnsByKey = new Map(ALL_COLUMNS.map((column) => [column.key, column]));
  return visibleColumnKeys(state)
    .map((key) => columnsByKey.get(key))
    .filter(Boolean);
}

/**
 * Get default width for a column.
 */
export function columnMinWidth(key) {
  const col = ALL_COLUMNS.find((c) => c.key === key);
  return col ? Math.max(40, col.defaultWidth / 2) : 40;
}

/**
 * Fixed columns that always appear at the left edge.
 */
export { FIXED_LEFT, FIXED_RIGHT };
