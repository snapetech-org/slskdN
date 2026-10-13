import React, { useSyncExternalStore } from 'react';
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

const applyDocumentLanguage = (language) => {
  if (typeof document === 'undefined') return;
  document.documentElement.lang = language;
  document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr';
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

export const useInterfaceLanguage = () => {
  const language = useSyncExternalStore(
    (listener) => { listeners.add(listener); return () => listeners.delete(listener); },
    () => activeLanguage,
    () => 'en',
  );
  const t = (source) => language === 'en' ? source : UI_LABELS[source]?.[language] || source;
  return { language, setLanguage: setInterfaceLanguage, t };
};
