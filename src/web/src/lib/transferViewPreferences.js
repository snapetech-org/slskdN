// <copyright file="transferViewPreferences.js" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import { ALL_COLUMNS } from './transferColumns';
import { getLocalStorageItem, setLocalStorageItem } from './storage';

const STORAGE_KEY = 'slskdn-transfer-view-preferences';
const VALID_STATUS_FILTERS = new Set([
  'active',
  'all',
  'completed',
  'failed',
  'queued',
]);
const SORTABLE_KEYS = new Set(
  ALL_COLUMNS.filter((column) => column.sortable).map((column) => column.key),
);

export const DEFAULT_TRANSFER_VIEW_STATE = {
  hideCompleted: true,
  statusFilter: 'all',
  sort: { direction: 'descending', key: 'requested' },
};

const getStoredPreferences = () => {
  try {
    const stored = getLocalStorageItem(STORAGE_KEY);
    const parsed = stored ? JSON.parse(stored) : {};
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? parsed
      : {};
  } catch {
    return {};
  }
};

const normalizeSort = (sort) => ({
  direction: ['ascending', 'descending'].includes(sort?.direction)
    ? sort.direction
    : DEFAULT_TRANSFER_VIEW_STATE.sort.direction,
  key: SORTABLE_KEYS.has(sort?.key) ? sort.key : DEFAULT_TRANSFER_VIEW_STATE.sort.key,
});

const normalizeState = (state) => ({
  hideCompleted: typeof state?.hideCompleted === 'boolean'
    ? state.hideCompleted
    : DEFAULT_TRANSFER_VIEW_STATE.hideCompleted,
  statusFilter: VALID_STATUS_FILTERS.has(state?.statusFilter)
    ? state.statusFilter
    : DEFAULT_TRANSFER_VIEW_STATE.statusFilter,
  sort: normalizeSort(state?.sort),
});

export const loadTransferViewState = (direction) => {
  const preferences = getStoredPreferences();
  return normalizeState(preferences[direction]);
};

export const saveTransferViewState = (direction, state) => {
  const preferences = getStoredPreferences();
  preferences[direction] = normalizeState(state);
  return setLocalStorageItem(STORAGE_KEY, JSON.stringify(preferences));
};
