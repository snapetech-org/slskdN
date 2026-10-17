import { getApiErrorMessage } from './apiErrorMessages';

describe('getApiErrorMessage', () => {
  const t = (source) => `translated:${source}`;

  it('translates allowlisted stable API error codes', () => {
    expect(getApiErrorMessage({
      response: {
        data: { parameters: { limit: 5 } },
        headers: { 'x-slskd-error-code': 'source-feed-import.limit-must-be-positive' },
      },
    }, { t })).toBe('translated:Limit must be greater than 0');
  });

  it('does not display unrecognized server error prose', () => {
    expect(getApiErrorMessage({
      message: 'Request failed with status code 500',
      response: {
        data: {
          code: 'server.exception',
          detail: 'Sensitive or untranslated server details',
          message: 'English backend message',
        },
        headers: {},
        statusText: 'Internal Server Error',
      },
    }, { t })).toBe('translated:The request failed. Try again.');
  });

  it('translates a caller-provided fallback for an unknown error', () => {
    expect(getApiErrorMessage(new Error('socket hang up'), { t }, 'Failed to load searches'))
      .toBe('translated:Failed to load searches');
  });
});
