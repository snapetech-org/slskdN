import { useExperiencePreference, readExperiencePreference } from './experiencePreferences';

export const REGIONAL_FORMAT_OPTIONS = [{"value": "system", "text": "Use browser settings", "key": "system"}, {"value": "es", "text": "Español — Spanish", "key": "es"}, {"value": "zh-CN", "text": "简体中文 — Chinese (Simplified)", "key": "zh-CN"}, {"value": "hi-IN", "text": "हिन्दी — Hindi", "key": "hi-IN"}, {"value": "de", "text": "Deutsch — German", "key": "de"}, {"value": "ja", "text": "日本語 — Japanese", "key": "ja"}, {"value": "fr", "text": "Français — French", "key": "fr"}, {"value": "pt-BR", "text": "Português (Brasil) — Brazilian Portuguese", "key": "pt-BR"}, {"value": "ar", "text": "العربية — Arabic", "key": "ar"}, {"value": "ko", "text": "한국어 — Korean", "key": "ko"}, {"value": "zh-TW", "text": "繁體中文 — Chinese (Traditional)", "key": "zh-TW"}, {"value": "vi", "text": "Tiếng Việt — Vietnamese", "key": "vi"}, {"value": "id", "text": "Bahasa Indonesia — Indonesian", "key": "id"}];
export const formatRegionalNumber = (value, options, locale = getRegionalLocale()) => {
  if (value === undefined || value === null) return value;
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return value;
  return new Intl.NumberFormat(locale, options).format(numericValue);
};

const supportedRegionalFormats = new Set(REGIONAL_FORMAT_OPTIONS.map((option) => option.value));

export const useRegionalLocale = () => {
  const value = useExperiencePreference('regionalFormat', 'system');
  return supportedRegionalFormats.has(value) && value !== 'system' ? value : undefined;
};

export const getRegionalLocale = () => {
  const value = readExperiencePreference('regionalFormat', 'system');
  return supportedRegionalFormats.has(value) && value !== 'system' ? value : undefined;
};

export const formatRegionalCompactNumber = (value, options = {}, locale = getRegionalLocale()) => {
  if (value === undefined || value === null) return value;
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return value;
  return new Intl.NumberFormat(locale, {
    notation: 'compact',
    maximumFractionDigits: 1,
    ...options,
  }).format(numericValue);
};
