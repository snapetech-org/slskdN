import {
  interfaceTextOutput,
  isInterfaceOpaqueOutput,
  isInterfaceTextOutput,
} from './interfaceLocale';

const API_ERROR_TEXT = {
  'source-feed-import.source-text-required': 'SourceText is required',
  'source-feed-import.limit-must-be-positive': 'Limit must be greater than 0',
  'songid.source-required': 'SongID source is required.',
  'songid.request-invalid': 'SongID request is invalid.',
  'songid.analysis-queue-failed': 'SongID analysis could not be queued.',
};

export const getApiErrorMessageOutput = (error, localeOrFallback, legacyFallback) => {
  const response = error?.response || (
    error && typeof error === 'object' &&
    ('data' in error || 'headers' in error)
      ? error
      : undefined
  );
  const data = response?.data;
  const code = response?.headers?.['x-slskd-error-code'] ||
    (data && typeof data === 'object' ? data.code : undefined);
  const source = typeof code === 'string' && Object.hasOwn(API_ERROR_TEXT, code)
    ? API_ERROR_TEXT[code]
    : undefined;
  if (source) {
    const rawParameters = data?.parameters && typeof data.parameters === 'object' && !Array.isArray(data.parameters)
      ? data.parameters
      : {};
    const values = Object.fromEntries(Object.entries(rawParameters).filter(([, value]) =>
      typeof value === 'string' || typeof value === 'number'));
    return interfaceTextOutput(source, values);
  }

  const isOutput = isInterfaceOpaqueOutput(localeOrFallback) || isInterfaceTextOutput(localeOrFallback);
  const fallback = typeof localeOrFallback === 'string' || isOutput
    ? localeOrFallback
    : legacyFallback;
  if (isInterfaceTextOutput(fallback) || isInterfaceOpaqueOutput(fallback)) return fallback;
  const genericMessage = typeof fallback === 'string' && fallback
    ? fallback
    : 'The request failed. Try again.';
  return interfaceTextOutput(genericMessage);
};

export const getApiErrorMessage = (error, { t }, fallback) => {
  const output = getApiErrorMessageOutput(error, fallback);
  if (isInterfaceOpaqueOutput(output)) return output.text;
  return t(output.source, output.values);
};
