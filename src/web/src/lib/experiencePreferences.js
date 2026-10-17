import { getLocalStorageItem, setLocalStorageItem } from './storage';
import { useEffect, useState } from 'react';

export const EXPERIENCE_PREFERENCES_STORAGE_KEY =
  'slskdn:experience-preferences:v1';
export const EXPERIENCE_PREFERENCES_CHANGED_EVENT =
  'slskdn:experience-preferences-changed';

let inMemoryPreferences = null;

const readStoredExperiencePreferences = () => {
  const stored = getLocalStorageItem(EXPERIENCE_PREFERENCES_STORAGE_KEY);
  if (!stored) return {};

  try {
    const parsed = JSON.parse(stored);
    return parsed !== null && typeof parsed === 'object' && !Array.isArray(parsed)
      ? parsed
      : {};
  } catch {
    return {};
  }
};

export const readExperiencePreference = (key, fallback) => {
  if (inMemoryPreferences && Object.hasOwn(inMemoryPreferences, key)) {
    const value = inMemoryPreferences[key];
    return typeof value === typeof fallback ? value : fallback;
  }

  const value = readStoredExperiencePreferences()[key];
  return typeof value === typeof fallback ? value : fallback;
};

export const notifyExperiencePreferencesChanged = () => {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new window.Event(EXPERIENCE_PREFERENCES_CHANGED_EVENT));
};

export const setExperiencePreferencesSnapshot = (preferences) => {
  inMemoryPreferences =
    preferences !== null && typeof preferences === 'object' && !Array.isArray(preferences)
      ? { ...preferences }
      : {};
};

export const setExperiencePreference = (key, value) => {
  const next = {
    ...readStoredExperiencePreferences(),
    ...(inMemoryPreferences || {}),
    [key]: value,
  };
  const saved = setLocalStorageItem(
    EXPERIENCE_PREFERENCES_STORAGE_KEY,
    JSON.stringify(next),
  );
  inMemoryPreferences = next;
  notifyExperiencePreferencesChanged();
  return saved;
};

export const subscribeToExperiencePreferences = (callback) => {
  if (typeof window === 'undefined') return () => {};

  const handleStorageChange = (event) => {
    if (event.key === EXPERIENCE_PREFERENCES_STORAGE_KEY || event.key === null) {
      inMemoryPreferences = null;
      callback();
    }
  };

  window.addEventListener('storage', handleStorageChange);
  window.addEventListener(EXPERIENCE_PREFERENCES_CHANGED_EVENT, callback);

  return () => {
    window.removeEventListener('storage', handleStorageChange);
    window.removeEventListener(EXPERIENCE_PREFERENCES_CHANGED_EVENT, callback);
  };
};

export const useExperiencePreference = (key, fallback) => {
  const [value, setValue] = useState(() =>
    readExperiencePreference(key, fallback),
  );

  useEffect(() => {
    const refresh = () => setValue(readExperiencePreference(key, fallback));
    return subscribeToExperiencePreferences(refresh);
  }, [fallback, key]);

  return value;
};
