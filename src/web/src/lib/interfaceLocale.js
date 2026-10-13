import React, { useCallback, useSyncExternalStore } from 'react';
import UI_LABELS from './ui-labels.json';

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

export const getInterfaceTextLanguage = (source, language) =>
  language !== 'en' && UI_LABELS[source]?.[language] ? language : 'en';

export const getInterfaceTextDirection = (source, language) =>
  getInterfaceTextLanguage(source, language) === 'ar' ? 'rtl' : 'ltr';

const formatInterfaceText = (source, parameters = {}) => {
  if (typeof source !== 'string') return source;
  const translated = activeLanguage === 'en' ? source : UI_LABELS[source]?.[activeLanguage] || source;
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
  const translated = activeLanguage !== 'en' ? UI_LABELS[source]?.[activeLanguage] : undefined;
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

let activeLanguage = readLanguage();
const notify = () => listeners.forEach((listener) => listener());

if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (event.key !== STORAGE_KEY && event.key !== null) return;
    activeLanguage = readLanguage();
    applyDocumentLanguage(activeLanguage);
    notify();
  });
}

export const applyInitialInterfaceLanguage = () => {
  activeLanguage = readLanguage();
  applyDocumentLanguage(activeLanguage);
};

export const setInterfaceLanguage = (language) => {
  if (!supportedLanguages.has(language)) return;
  activeLanguage = language;
  try { localStorage.setItem(STORAGE_KEY, language); } catch { /* Keep this tab usable without browser storage. */ }
  applyDocumentLanguage(language);
  notify();
};

export const resetInterfaceLanguage = () => {
  try { localStorage.removeItem(STORAGE_KEY); } catch { /* Use the browser language for this tab. */ }
  activeLanguage = browserLanguage();
  applyDocumentLanguage(activeLanguage);
  notify();
};

export const useInterfaceLanguage = () => {
  const language = useSyncExternalStore(
    (listener) => { listeners.add(listener); return () => listeners.delete(listener); },
    () => activeLanguage,
    () => 'en',
  );
  const t = useCallback((source, parameters) => {
    const translated = language === 'en' ? source : UI_LABELS[source]?.[language] || source;
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
