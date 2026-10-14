import React, { useCallback, useSyncExternalStore } from 'react';

export const INTERFACE_LANGUAGE_OPTIONS = [
  { key: 'en', text: 'English', value: 'en' },
  { key: 'es', text: 'Español — Spanish', value: 'es' },
  { key: 'zh-Hans', text: '简体中文 — Simplified Chinese', value: 'zh-Hans' },
  { key: 'hi', text: 'हिन्दी — Hindi', value: 'hi' },
  { key: 'de', text: 'Deutsch — German', value: 'de' },
  { key: 'ja', text: '日本語 — Japanese', value: 'ja' },
  { key: 'fr', text: 'Français — French', value: 'fr' },
  { key: 'pt-BR', text: 'Português (Brasil) — Brazilian Portuguese', value: 'pt-BR' },
  { key: 'ar', text: 'العربية — Arabic', value: 'ar' },
  { key: 'ko', text: '한국어 — Korean', value: 'ko' },
  { key: 'zh-Hant', text: '繁體中文 — Traditional Chinese', value: 'zh-Hant' },
  { key: 'vi', text: 'Tiếng Việt — Vietnamese', value: 'vi' },
  { key: 'id', text: 'Bahasa Indonesia — Indonesian', value: 'id' },
];

const STORAGE_KEY = 'slskdn.interface-language';
const supportedLanguages = new Set(INTERFACE_LANGUAGE_OPTIONS.map((option) => option.value));
const listeners = new Set();
const catalogCache = new Map();
const catalogLoads = new Map();
let activeLanguage;
let activeCatalog = null;
let revision = 0;
let languageRequest = 0;

const notify = () => {
  revision += 1;
  listeners.forEach((listener) => listener());
};

const browserLanguage = () => {
  if (typeof navigator === 'undefined') return 'en';
  const candidates = navigator.languages?.length ? navigator.languages : [navigator.language];
  for (const candidate of candidates) {
    const normalized = candidate.toLowerCase();
    const base = normalized.split(/[-_]/)[0];
    if (base === 'zh') return /(?:hant|tw|hk|mo)/.test(normalized) ? 'zh-Hant' : 'zh-Hans';
    if (base === 'pt') return 'pt-BR';
    if (supportedLanguages.has(base)) return base;
  }
  return 'en';
};

const readLanguage = () => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return supportedLanguages.has(stored) ? stored : browserLanguage();
  } catch {
    return browserLanguage();
  }
};

const applyDocumentLanguage = (_language) => {
  if (typeof document === 'undefined') return;
  document.documentElement.lang = 'en';
  document.documentElement.dir = 'ltr';
};

const loadCatalog = (language) => {
  if (language === 'en') return Promise.resolve(null);
  if (catalogCache.has(language)) return Promise.resolve(catalogCache.get(language));
  if (catalogLoads.has(language)) return catalogLoads.get(language);

  const request = fetch(`${import.meta.env.BASE_URL}locales/${encodeURIComponent(language)}.json`, {
    headers: { Accept: 'application/json' },
  })
    .then((response) => {
      if (!response.ok) throw new Error(`Locale catalog request failed (${response.status}).`);
      return response.json();
    })
    .then((catalog) => {
      if (!catalog || typeof catalog !== 'object' || Array.isArray(catalog) || Object.keys(catalog).length === 0) {
        throw new Error('Locale catalog is empty or invalid.');
      }
      catalogCache.set(language, catalog);
      return catalog;
    })
    .catch(() => null)
    .finally(() => catalogLoads.delete(language));

  catalogLoads.set(language, request);
  return request;
};

const activateLanguage = (language, { persist = false } = {}) => {
  if (!supportedLanguages.has(language)) return Promise.resolve();
  const request = ++languageRequest;
  const activate = (nextLanguage, catalog) => {
    activeLanguage = nextLanguage;
    activeCatalog = nextLanguage === 'en' ? null : catalog;
    applyDocumentLanguage(nextLanguage);
    notify();
    if (persist) {
      try { localStorage.setItem(STORAGE_KEY, nextLanguage); } catch { /* Keep this tab usable without browser storage. */ }
    }
  };

  if (language === 'en') {
    activate('en', null);
    return Promise.resolve();
  }

  const cachedCatalog = catalogCache.get(language);
  if (cachedCatalog) {
    activate(language, cachedCatalog);
    return Promise.resolve();
  }

  return loadCatalog(language).then((catalog) => {
    if (request !== languageRequest || !catalog) return;
    activate(language, catalog);
  });
};

export const getInterfaceTextLanguage = (source, language) => {
  const catalog = catalogCache.get(language) || (language === activeLanguage ? activeCatalog : null);
  return language !== 'en' && typeof catalog?.[source] === 'string' && catalog[source]
    ? language
    : 'en';
};

export const getInterfaceTextDirection = (source, language) =>
  getInterfaceTextLanguage(source, language) === 'ar' ? 'rtl' : 'ltr';

const formatInterfaceText = (source, parameters = {}) => {
  if (typeof source !== 'string') return source;
  const translated = activeLanguage === 'en' ? source : activeCatalog?.[source] || source;
  return translated.replace(/\{([a-zA-Z][a-zA-Z0-9_]*)\}/g, (placeholder, name) => {
    const value = parameters?.[name];
    return typeof value === 'string' || typeof value === 'number'
      ? String(value)
      : placeholder;
  });
};

export const interfaceText = (source, parameters = {}) =>
  formatInterfaceText(source, parameters);

export const interfaceTextProps = (source, parameters = {}) => {
  const translated = activeLanguage !== 'en' ? activeCatalog?.[source] : undefined;
  const text = formatInterfaceText(source, parameters);
  const unresolved = typeof text === 'string' && /\{[a-zA-Z][a-zA-Z0-9_]*\}/.test(text);
  const props = {
    dir: translated && activeLanguage === 'ar' ? 'rtl' : 'ltr',
    lang: translated ? activeLanguage : 'en',
  };
  if (!unresolved) {
    props['aria-label'] = text;
    props.title = text;
  }
  if (parameters && Object.keys(parameters).length > 0) props.parameters = parameters;
  return props;
};

activeLanguage = 'en';

if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (event.key !== STORAGE_KEY && event.key !== null) return;
    void activateLanguage(readLanguage());
  });
}

export const applyInitialInterfaceLanguage = () => activateLanguage(readLanguage());

export const setInterfaceLanguage = (language) => {
  return activateLanguage(language, { persist: true });
};

export const resetInterfaceLanguage = () => {
  try { localStorage.removeItem(STORAGE_KEY); } catch { /* Use the browser language for this tab. */ }
  return activateLanguage(browserLanguage());
};

export const useInterfaceLanguage = () => {
  useSyncExternalStore(
    (listener) => { listeners.add(listener); return () => listeners.delete(listener); },
    () => revision,
    () => 0,
  );
  const language = activeLanguage;
  const t = useCallback((source, parameters) => {
    const translated = language === 'en' ? source : activeCatalog?.[source] || source;
    if (!parameters || typeof translated !== 'string') return translated;
    return translated.replace(/\{([a-zA-Z][a-zA-Z0-9_]*)\}/g, (placeholder, name) => {
      const value = parameters[name];
      return typeof value === 'string' || typeof value === 'number'
        ? String(value)
        : placeholder;
    });
  }, [language]);
  const languageFor = useCallback((source) => getInterfaceTextLanguage(source, language), [language]);
  const directionFor = useCallback((source) => getInterfaceTextDirection(source, language), [language]);
  return { language, setLanguage: setInterfaceLanguage, t, languageFor, directionFor };
};
