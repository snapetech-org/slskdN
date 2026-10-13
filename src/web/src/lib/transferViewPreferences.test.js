// <copyright file="transferViewPreferences.test.js" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import {
  DEFAULT_TRANSFER_VIEW_STATE,
  loadTransferViewState,
  saveTransferViewState,
} from './transferViewPreferences';

describe('transfer view preferences', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('round-trips independent preferences for each transfer direction', () => {
    saveTransferViewState('download', {
      hideCompleted: false,
      statusFilter: 'failed',
      sort: { direction: 'descending', key: 'size' },
    });
    saveTransferViewState('upload', {
      hideCompleted: true,
      statusFilter: 'active',
      sort: { direction: 'ascending', key: 'peer' },
    });

    expect(loadTransferViewState('download')).toEqual({
      hideCompleted: false,
      statusFilter: 'failed',
      sort: { direction: 'descending', key: 'size' },
    });
    expect(loadTransferViewState('upload')).toEqual({
      hideCompleted: true,
      statusFilter: 'active',
      sort: { direction: 'ascending', key: 'peer' },
    });
  });

  it('defaults new views to newest requests first', () => {
    expect(loadTransferViewState('download').sort).toEqual({
      direction: 'descending',
      key: 'requested',
    });
  });

  it('keeps an existing saved sort choice', () => {
    localStorage.setItem(
      'slskdn-transfer-view-preferences',
      JSON.stringify({
        download: {
          sort: { direction: 'ascending', key: 'name' },
        },
      }),
    );

    expect(loadTransferViewState('download').sort).toEqual({
      direction: 'ascending',
      key: 'name',
    });
  });

  it('repairs malformed values instead of poisoning the next render', () => {
    localStorage.setItem(
      'slskdn-transfer-view-preferences',
      JSON.stringify({
        download: {
          hideCompleted: 'false',
          statusFilter: 'not-a-filter',
          sort: { direction: 'sideways', key: 'not-a-column' },
        },
      }),
    );

    expect(loadTransferViewState('download')).toEqual(DEFAULT_TRANSFER_VIEW_STATE);
  });
});
