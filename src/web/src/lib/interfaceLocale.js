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
const interfaceTextOutputBrand = Symbol('slskdn.interface-text-output');
const interfaceOpaqueOutputBrand = Symbol('slskdn.interface-opaque-output');
const MAX_OUTPUT_SOURCE_LENGTH = 512;
const MAX_OUTPUT_PARAMETER_COUNT = 24;
const MAX_OUTPUT_PARAMETER_LENGTH = 2048;
const MAX_OUTPUT_PARAMETER_TOTAL_LENGTH = 8192;
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

const applyDocumentLanguage = (language) => {
  if (typeof document === 'undefined') return;
  document.documentElement.lang = language;
  document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr';
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

const translationFor = (source, language) => {
  const catalog = catalogCache.get(language) || (language === activeLanguage ? activeCatalog : null);
  return language !== 'en' && catalog && Object.hasOwn(catalog, source) &&
    typeof catalog[source] === 'string' && catalog[source]
    ? catalog[source]
    : undefined;
};

// Supports only cardinal plural selectors with a named numeric value, CLDR
// categories, and `#` replacement. Branches are plain text; this is not a
// general ICU MessageFormat parser (no nested selectors, ordinal, or offset).
const parsePluralBranches = (message) => {
  const branches = {};
  let index = 0;
  while (index < message.length) {
    while (/[\s,]/.test(message[index] || '')) index += 1;
    const keyMatch = /^(zero|one|two|few|many|other|=-?\d+)/.exec(message.slice(index));
    if (!keyMatch) break;
    const key = keyMatch[0];
    index += key.length;
    while (/\s/.test(message[index] || '')) index += 1;
    if (message[index] !== '{') break;
    const start = ++index;
    let depth = 1;
    while (index < message.length && depth > 0) {
      if (message[index] === '{') depth += 1;
      else if (message[index] === '}') depth -= 1;
      index += 1;
    }
    if (depth !== 0) break;
    branches[key] = message.slice(start, index - 1);
  }
  return branches;
};

const formatCardinalPluralMessages = (message, parameters, language) => {
  const selector = /\{([a-zA-Z][a-zA-Z0-9_]*),\s*plural,\s*/g;
  let output = '';
  let copiedThrough = 0;
  let match;

  while ((match = selector.exec(message)) !== null) {
    let end = selector.lastIndex;
    let depth = 1;
    while (end < message.length && depth > 0) {
      if (message[end] === '{') depth += 1;
      else if (message[end] === '}') depth -= 1;
      end += 1;
    }
    if (depth !== 0) break;

    const count = Number(parameters?.[match[1]]);
    if (!Number.isFinite(count)) {
      selector.lastIndex = end;
      continue;
    }
    const branches = parsePluralBranches(message.slice(selector.lastIndex, end - 1));
    let category = 'other';
    try {
      category = new Intl.PluralRules(language).select(count);
    } catch {
      category = new Intl.PluralRules('en').select(count);
    }
    const branch = branches[`=${count}`] ?? branches[category] ?? branches.other;
    if (branch === undefined) {
      selector.lastIndex = end;
      continue;
    }

    let countText;
    try {
      countText = new Intl.NumberFormat(language).format(count);
    } catch {
      countText = new Intl.NumberFormat('en').format(count);
    }
    if (language === 'ar') countText = `\u2068${countText}\u2069`;
    output += message.slice(copiedThrough, match.index) + branch.replace(/#/g, countText);
    copiedThrough = end;
    selector.lastIndex = end;
  }

  return copiedThrough === 0
    ? message
    : output + message.slice(copiedThrough);
};

export const getInterfaceTextLanguage = (source, language) => {
  const translated = translationFor(source, language);
  return translated && translated !== source ? language : 'en';
};

export const getInterfaceTextDirection = (source, language) =>
  getInterfaceTextLanguage(source, language) === 'ar' ? 'rtl' : 'ltr';

const formatInterfaceText = (source, parameters = {}) => {
  if (typeof source !== 'string') return source;
  const translated = formatCardinalPluralMessages(
    translationFor(source, activeLanguage) || source,
    parameters,
    activeLanguage,
  );
  return translated.replace(/\{([a-zA-Z][a-zA-Z0-9_]*)\}/g, (placeholder, name) => {
    const value = parameters?.[name];
    return typeof value === 'string' || typeof value === 'number'
      ? String(value)
      : placeholder;
  });
};

export const isInterfaceTextOutput = (value) =>
  Boolean(value && typeof value === 'object' && value[interfaceTextOutputBrand] === true);

export const isInterfaceOpaqueOutput = (value) =>
  Boolean(value && typeof value === 'object' && value[interfaceOpaqueOutputBrand] === true);

const rawOutputValue = (value) => {
  if (isInterfaceOpaqueOutput(value)) return value.text;
  if (isInterfaceTextOutput(value)) return formatRawOutput(value.source, value.values);
  return typeof value === 'string' || (typeof value === 'number' && Number.isFinite(value))
    ? String(value)
    : undefined;
};

const formatRawOutput = (source, values = {}) => {
  if (typeof source !== 'string') return '';
  return source.replace(/\{([a-zA-Z][a-zA-Z0-9_]*)\}/g, (placeholder, name) =>
    rawOutputValue(values?.[name]) ?? placeholder);
};

const makeOpaqueOutput = (text) => Object.freeze({
  [interfaceOpaqueOutputBrand]: true,
  text,
});

const boundedOutputValues = (source, values) => {
  if (!values || typeof values !== 'object' || Array.isArray(values)) {
    return Object.freeze({});
  }
  const names = new Set(Array.from(
    source.matchAll(/\{([a-zA-Z][a-zA-Z0-9_]*)\}/g),
    (match) => match[1],
  ));
  if (names.size > MAX_OUTPUT_PARAMETER_COUNT) return undefined;
  const bounded = {};
  let totalLength = 0;
  for (const name of names) {
    if (!/^[a-zA-Z][a-zA-Z0-9_]{0,63}$/.test(name)) continue;
    if (!Object.hasOwn(values, name)) continue;
    const value = values[name];
    if (isInterfaceTextOutput(value) || isInterfaceOpaqueOutput(value)) {
      const rawValue = rawOutputValue(value);
      if (rawValue.length > MAX_OUTPUT_PARAMETER_LENGTH ||
        totalLength + rawValue.length > MAX_OUTPUT_PARAMETER_TOTAL_LENGTH) {
        return undefined;
      }
      totalLength += rawValue.length;
      bounded[name] = value;
      continue;
    }
    if (typeof value === 'number' && Number.isFinite(value)) {
      bounded[name] = value;
      continue;
    }
    if (typeof value !== 'string') continue;
    if (value.length > MAX_OUTPUT_PARAMETER_LENGTH ||
      totalLength + value.length > MAX_OUTPUT_PARAMETER_TOTAL_LENGTH) {
      return undefined;
    }
    bounded[name] = value;
    totalLength += value.length;
  }
  return Object.freeze(bounded);
};

export const interfaceTextOutput = (source, values = {}) => {
  if (typeof source !== 'string') return undefined;
  if (source.length > MAX_OUTPUT_SOURCE_LENGTH) {
    return makeOpaqueOutput(formatRawOutput(source, values));
  }
  const boundedValues = boundedOutputValues(source, values);
  if (boundedValues === undefined) {
    return makeOpaqueOutput(formatRawOutput(source, values));
  }
  return Object.freeze({
    [interfaceTextOutputBrand]: true,
    source,
    values: boundedValues,
  });
};

export const interfaceToastText = (source, values = {}) =>
  interfaceTextOutput(source, values);

export const interfaceText = (source, parameters = {}) => {
  return formatInterfaceText(source, parameters);
};

const isolateNativePresentationParameters = (parameters = {}) =>
  Object.fromEntries(Object.entries(parameters).map(([name, value]) => [
    name,
    (typeof value === 'string' || typeof value === 'number') && String(value)
      ? `\u2068${value}\u2069`
      : value,
  ]));

const isolateNativeDialogParameters = (source, parameters = {}) => {
  const pluralParameters = new Set(
    typeof source === 'string'
      ? Array.from(
        source.matchAll(/\{([a-zA-Z][a-zA-Z0-9_]*),\s*plural,/g),
        (match) => match[1],
      )
      : [],
  );
  return Object.fromEntries(Object.entries(parameters).map(([name, value]) => {
    if (pluralParameters.has(name)) return [name, value];
    const shouldIsolate =
      (typeof value === 'string' || typeof value === 'number') && String(value);
    return [name, shouldIsolate ? `\u2068${value}\u2069` : value];
  }));
};

// Native attribute/dialog text cannot contain <bdi>. Keep isolates at this
// presentation boundary; ordinary helpers and stored data remain unchanged.
export const interfacePresentationText = (source, parameters = {}) => {
  const values = activeLanguage === 'ar'
    ? isolateNativePresentationParameters(parameters)
    : parameters;
  return formatInterfaceText(source, values);
};

// Native aria-label/title strings cannot contain structured <bdi> elements.
// Isolate interpolated values in every locale without changing stored text.
export const interfaceAttributeText = (source, parameters = {}) => {
  return formatInterfaceText(source, isolateNativePresentationParameters(parameters));
};

// Native confirm dialogs isolate opaque values while leaving numeric plural
// selectors unwrapped for cardinal selection and locale-aware number output.
export const interfaceDialogText = (source, parameters = {}) =>
  formatInterfaceText(source, isolateNativeDialogParameters(source, parameters));

export const interfaceTextProps = (source, parameters = {}) => {
  const textLanguage = getInterfaceTextLanguage(source, activeLanguage);
  const text = formatInterfaceText(source, parameters);
  const unresolved = typeof text === 'string' && /\{[a-zA-Z][a-zA-Z0-9_]*\}/.test(text);
  const props = {
    dir: textLanguage === 'ar' ? 'rtl' : 'ltr',
    lang: textLanguage,
  };
  if (!unresolved) {
    props['aria-label'] = text;
    props.title = text;
  }
  if (parameters && Object.keys(parameters).length > 0) props.parameters = parameters;
  return props;
};

export const interfaceAttributeTextProps = (source, parameters = {}) => {
  const props = interfaceTextProps(source, parameters);
  if (!Object.hasOwn(props, 'aria-label')) return props;
  const text = interfaceAttributeText(source, parameters);
  return { ...props, 'aria-label': text, title: text };
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
    const translated = translationFor(source, language) || source;
    if (typeof translated !== 'string') return translated;
    if (!parameters) return translated;
    const withPlurals = formatCardinalPluralMessages(translated, parameters, language);
    return withPlurals.replace(/\{([a-zA-Z][a-zA-Z0-9_]*)\}/g, (placeholder, name) => {
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
