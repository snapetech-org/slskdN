const API_ERROR_TEXT = {
  'source-feed-import.source-text-required': 'SourceText is required',
  'source-feed-import.limit-must-be-positive': 'Limit must be greater than 0',
  'songid.source-required': 'SongID source is required.',
  'songid.request-invalid': 'SongID request is invalid.',
  'songid.analysis-queue-failed': 'SongID analysis could not be queued.',
};

const interpolateSafeParameters = (message, parameters) =>
  message.replace(/\{([a-z][a-z0-9]*)\}/giu, (placeholder, name) => {
    const value = parameters?.[name];
    return typeof value === 'string' || typeof value === 'number'
      ? String(value)
      : placeholder;
  });

export const getApiErrorMessage = (error, { t }, fallback) => {
  const response = error?.response || (
    error && typeof error === 'object' &&
    ('data' in error || 'headers' in error)
      ? error
      : undefined
  );
  const data = response?.data;
  const code = response?.headers?.['x-slskd-error-code'] ||
    (data && typeof data === 'object' ? data.code : undefined);
  const source = API_ERROR_TEXT[code];
  if (source) {
    const parameters = data?.parameters && typeof data.parameters === 'object' && !Array.isArray(data.parameters)
      ? data.parameters
      : {};
    return interpolateSafeParameters(t(source), parameters);
  }

  const genericMessage = typeof fallback === 'string' && fallback
    ? fallback
    : 'The request failed. Try again.';
  return t(genericMessage);
};
