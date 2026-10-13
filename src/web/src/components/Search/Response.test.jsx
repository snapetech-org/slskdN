// <copyright file="Response.test.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import Response, { buildDownloadRequestFiles, buildSearchItemActionPath } from './Response';
import { buildPeerStreamUrl } from '../../lib/streaming';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import { render, screen } from '@testing-library/react';

describe('Search Response action routes', () => {
  it('encodes search and item identifiers per route segment', () => {
    expect(
      buildSearchItemActionPath('search/with?intent', '0:1/2', 'download'),
    ).toBe('/searches/search%2Fwith%3Fintent/items/0%3A1%2F2/download');
  });

  it('encodes the selected destination for bridged downloads', () => {
    expect(
      buildSearchItemActionPath(
        'search-id',
        '0:1',
        'download',
        '/downloads/Music & Audio',
      ),
    ).toBe(
      '/searches/search-id/items/0%3A1/download?destination=%2Fdownloads%2FMusic%20%26%20Audio',
    );
  });

  it('retains the originating search context on queued files', () => {
    expect(buildDownloadRequestFiles([
      { filename: 'album/song.flac', size: 4096, bitRate: 320 },
    ], 'search-7', 'artist album')).toEqual([
      {
        filename: 'album/song.flac',
        size: 4096,
        bitRate: 320,
        sampleRate: undefined,
        bitDepth: undefined,
        length: undefined,
        searchId: 'search-7',
        searchText: 'artist album',
      },
    ]);
  });
});

describe('Peer stream URLs', () => {
  it('roots relative peer stream URLs at the configured app base', () => {
    expect(buildPeerStreamUrl('/api/v0/peer-streams/ticket-1')).toContain(
      '/api/v0/peer-streams/ticket-1',
    );
  });
});

describe('Search Response actions', () => {
  it('explains why download is disabled before files are selected', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Response
          response={{
            files: [],
            hasFreeUploadSlot: true,
            lockedFiles: [],
            username: 'alice',
          }}
          searchId="search-1"
        />
      </MemoryRouter>,
    );

    const download = screen.getByRole('button', { name: 'Download selected files' });
    expect(download).toBeDisabled();
    await user.hover(download.parentElement);

    expect(await screen.findByText(
      'Select one or more files before starting a peer download.',
    )).toBeInTheDocument();
  });
});
