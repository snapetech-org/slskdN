// <copyright file="Searches.test.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import Searches from './Searches';
import { createSearchHubConnection } from '../../lib/hubFactory';
import { getCapabilities } from '../../lib/slskdn';
import * as library from '../../lib/searches';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

vi.mock('../../lib/hubFactory', () => ({
  createSearchHubConnection: vi.fn(),
}));
vi.mock('../../lib/slskdn', () => ({
  getCapabilities: vi.fn(),
}));
vi.mock('../../lib/searches', () => ({
  create: vi.fn(),
  get: vi.fn(),
  getAll: vi.fn(),
  createBatch: vi.fn(),
  remove: vi.fn(),
  removeAll: vi.fn(),
  stop: vi.fn(),
}));
vi.mock('./AlbumCompletionPanel', () => ({ default: () => null }));
vi.mock('./ArtistReleaseRadarPanel', () => ({ default: () => null }));
vi.mock('./DiscoveryGraphAtlasPanel', () => ({ default: () => null }));
vi.mock('./FederatedTasteRecommendationsPanel', () => ({ default: () => null }));
vi.mock('./MusicBrainzLookup', () => ({ default: () => null }));
vi.mock('./SongIDPanel', () => ({
  default: () => <div data-testid="songid-panel">SongID panel</div>,
}));
vi.mock('./Detail/SearchDetail', () => ({
  default: ({ search }) => <div data-testid="search-detail">{search.id}</div>,
}));
vi.mock('./List/SearchList', () => ({
  default: ({
    onRemoveSelected = async () => [],
    onResearchSelected = async () => [],
    onStopSelected = async () => [],
    hasMoreFromServer = false,
    onLoadMore = () => {},
    searches = {},
  }) => {
    const selectedSearch = Object.values(searches)[0];

    return (
      <div data-testid="search-list">
        {Object.keys(searches).join(',')}
        {hasMoreFromServer && (
          <button data-testid="search-list-load-more" onClick={onLoadMore} />
        )}
        {selectedSearch && (
          <>
            <button
              data-testid="search-list-research"
              onClick={() => onResearchSelected([selectedSearch])}
            />
            <button
              data-testid="search-list-remove"
              onClick={() => onRemoveSelected([selectedSearch])}
            />
            <button
              data-testid="search-list-stop"
              onClick={() => onStopSelected([selectedSearch])}
            />
          </>
        )}
      </div>
    );
  },
}));

const callbacks = {};

const renderSearches = async ({
  hubStart = async () => {
    callbacks.list?.([]);
  },
  initialEntries = ['/searches'],
  server = { isConnected: true },
  waitForInput = true,
} = {}) => {
  callbacks.list = undefined;
  createSearchHubConnection.mockReturnValue({
    on: vi.fn((eventName, callback) => {
      callbacks[eventName] = callback;
    }),
    onclose: vi.fn(),
    onreconnected: vi.fn(),
    onreconnecting: vi.fn(),
    start: vi.fn(hubStart),
    stop: vi.fn(),
  });

  render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route
          element={<Searches server={server} />}
          path="/searches"
        />
        <Route
          element={<Searches server={server} />}
          path="/searches/:id"
        />
        <Route
          element={<div data-testid="connection-settings">Connection settings</div>}
          path="/system/options"
        />
      </Routes>
    </MemoryRouter>,
  );

  return waitForInput ? screen.findByTestId('search-input') : undefined;
};

describe('Searches', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    getCapabilities.mockResolvedValue({ features: [] });
    library.create.mockResolvedValue({});
    library.get.mockRejectedValue({ response: { status: 404 } });
    library.getAll.mockResolvedValue([]);
  });

  it('keeps ScenePodBridge disabled by default and creates ordinary searches without providers', async () => {
    const input = await renderSearches();

    expect(screen.queryByText('Search Sources:')).not.toBeInTheDocument();

    fireEvent.change(input, { target: { value: 'beatles' } });
    fireEvent.keyUp(input, { key: 'Enter' });

    await waitFor(() => expect(library.create).toHaveBeenCalledTimes(1));
    expect(library.create).toHaveBeenCalledWith(
      expect.objectContaining({
        acquisitionProfile: 'lossless-exact',
        providers: null,
        searchText: 'beatles',
      }),
    );
  });

  it('loads a bounded REST page if the live search hub cannot start', async () => {
    await renderSearches({
      hubStart: async () => {
        throw new Error('hub unavailable');
      },
    });

    await waitFor(() => expect(library.getAll).toHaveBeenCalledTimes(1));
    expect(library.getAll).toHaveBeenCalledWith(250, null, 0, null, null);
  });

  it('continues after the last row even when a new search arrives between pages', async () => {
    const firstPage = Array.from({ length: 500 }, (_, index) => ({
      id: `search-${index}`,
      startedAt: new Date(2026, 0, 1, 0, index).toISOString(),
    }));
    library.getAll.mockResolvedValueOnce([
      { id: 'older-search', startedAt: '2025-12-31T00:00:00Z' },
    ]);

    await renderSearches({
      hubStart: async () => callbacks.list?.(firstPage),
    });
    callbacks.create({ id: 'live-newest', startedAt: '2026-01-02T00:00:00Z' });
    fireEvent.click(await screen.findByTestId('search-list-load-more'));

    await waitFor(() => expect(library.getAll).toHaveBeenCalledTimes(1));
    expect(library.getAll).toHaveBeenNthCalledWith(
      1,
      250,
      null,
      0,
      firstPage.at(-1).startedAt,
      firstPage.at(-1).id,
    );
    expect(screen.getByTestId('search-list')).toHaveTextContent('search-0');
    expect(screen.getByTestId('search-list')).toHaveTextContent('live-newest');
    expect(screen.getByTestId('search-list')).toHaveTextContent('older-search');
  });

  it('explains the disconnected search state and opens Soulseek settings', async () => {
    const input = await renderSearches({ server: { isConnected: false } });

    expect(input).toBeDisabled();
    expect(input).toHaveAttribute(
      'placeholder',
      'Connect to Soulseek to search',
    );
    expect(screen.getByText('Soulseek connection needed')).toBeInTheDocument();
    expect(
      screen.getByText(/use Disconnected in the top bar to reconnect/i),
    ).toBeInTheDocument();

    const settingsLink = screen.getByRole('link', {
      name: 'Open connection settings',
    });
    expect(settingsLink).toHaveAttribute('href', '/system/options');
    fireEvent.click(settingsLink);

    expect(await screen.findByTestId('connection-settings')).toBeInTheDocument();
  });

  it('shows connection progress without directing users to change settings', async () => {
    const input = await renderSearches({
      server: { isConnected: false, isConnecting: true },
    });

    expect(input).toBeDisabled();
    expect(input).toHaveAttribute('placeholder', 'Connecting to Soulseek…');
    expect(screen.getByText('Connecting to Soulseek')).toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: 'Open connection settings' }),
    ).not.toBeInTheDocument();
  });

  it('loads the REST snapshot only when the hub connection fails', async () => {
    library.getAll.mockResolvedValue([{ id: 'fallback-search' }]);

    await renderSearches({
      hubStart: async () => {
        throw new Error('hub unavailable');
      },
    });

    await waitFor(() => expect(library.getAll).toHaveBeenCalledTimes(1));
    expect(screen.getByTestId('search-list')).toHaveTextContent('fallback-search');
  });

  it('only sends bridge providers when the backend explicitly advertises ScenePodBridge', async () => {
    getCapabilities.mockResolvedValue({
      feature: { scenePodBridge: true },
      features: ['scene_pod_bridge'],
    });
    const input = await renderSearches();

    expect(await screen.findByText('Search Sources:')).toBeInTheDocument();

    fireEvent.change(input, { target: { value: 'beatles' } });
    fireEvent.keyUp(input, { key: 'Enter' });

    await waitFor(() => expect(library.create).toHaveBeenCalledTimes(1));
    expect(library.create).toHaveBeenCalledWith(
      expect.objectContaining({
        acquisitionProfile: 'lossless-exact',
        providers: ['pod', 'scene'],
        searchText: 'beatles',
      }),
    );
  });

  it('replays a selected search with the current acquisition profile and providers', async () => {
    getCapabilities.mockResolvedValue({
      feature: { scenePodBridge: true },
      features: ['scene_pod_bridge'],
    });
    library.createBatch.mockResolvedValue(1);

    await renderSearches({
      hubStart: async () => {
        callbacks.list?.([
          {
            id: 'completed-search',
            searchText: 'rare live set',
            state: 'Completed',
          },
        ]);
      },
    });

    fireEvent.click(screen.getByTestId('search-list-research'));

    await waitFor(() => expect(library.createBatch).toHaveBeenCalledTimes(1));
    expect(library.createBatch).toHaveBeenCalledWith({
      acquisitionProfile: 'lossless-exact',
      providers: ['pod', 'scene'],
      queries: ['rare live set'],
    });
  });

  it('defaults secondary search sections closed and remembers expanded state', async () => {
    await renderSearches();

    expect(
      screen.getByRole('button', { name: 'Expand Music discovery tools' }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Expand SongID' }),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId('songid-panel')).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole('button', { name: 'Expand Music discovery tools' }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Expand SongID' }));

    expect(await screen.findByTestId('songid-panel')).toBeInTheDocument();
    expect(localStorage.getItem('slskdn.search.section.songid')).toBe('open');
    expect(localStorage.getItem('slskdn.search.section.discoveryTools')).toBe(
      'open',
    );
  });

  it('preserves previously expanded discovery tools when the page is grouped', async () => {
    localStorage.setItem('slskdn.search.section.songid', 'open');

    await renderSearches();

    expect(await screen.findByTestId('songid-panel')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Collapse Music discovery tools' }),
    ).toBeInTheDocument();
  });

  it('loads a direct search detail URL when the initial list does not include it', async () => {
    library.get.mockResolvedValue({
      fileCount: 1,
      id: 'search-older-than-list',
      isComplete: true,
      lockedFileCount: 0,
      responseCount: 1,
      searchText: 'older result',
      state: 'Complete',
    });

    await renderSearches({
      initialEntries: ['/searches/search-older-than-list'],
      waitForInput: false,
    });

    expect(await screen.findByTestId('search-detail')).toHaveTextContent(
      'search-older-than-list',
    );
    expect(library.get).toHaveBeenCalledWith({ id: 'search-older-than-list' });
  });

  it('shows and persists the selected acquisition profile', async () => {
    await renderSearches();

    expect(screen.getByText('Acquisition Profile')).toBeInTheDocument();
    expect(screen.getAllByText('Lossless Exact').length).toBeGreaterThan(0);

    fireEvent.click(screen.getByTestId('acquisition-profile-select'));
    fireEvent.click(screen.getByText('Conservative Network'));

    expect(localStorage.getItem('slskdn.acquisitionProfile')).toBe(
      'conservative-network',
    );
    expect(
      screen.getAllByText('Lower concurrency, no automatic public-peer retries.')
        .length,
    ).toBeGreaterThan(0);

    const input = screen.getByTestId('search-input');
    fireEvent.change(input, { target: { value: 'rare live set' } });
    fireEvent.keyUp(input, { key: 'Enter' });

    await waitFor(() => expect(library.create).toHaveBeenCalledTimes(1));
    expect(library.create).toHaveBeenCalledWith(
      expect.objectContaining({
        acquisitionProfile: 'conservative-network',
        searchText: 'rare live set',
      }),
    );
  });

  it('uses stored collapsed state for primary search sections', async () => {
    localStorage.setItem('slskdn.search.section.search', 'closed');

    await renderSearches({ waitForInput: false });

    expect(screen.getByRole('button', { name: 'Expand Search' })).toBeInTheDocument();
    expect(screen.queryByTestId('search-input')).not.toBeInTheDocument();
  });

  it('keeps manual search out of acquisition review', async () => {
    await renderSearches();

    expect(
      screen.queryByRole('button', { name: 'Add search phrase to Discovery Inbox' }),
    ).not.toBeInTheDocument();
  });

  it('creates searches from URL query text without double-decoding percent sequences', async () => {
    library.create.mockResolvedValue('search-1');

    await renderSearches({
      initialEntries: ['/searches?q=100%25%20encoded%2520literal'],
    });

    await waitFor(() => expect(library.create).toHaveBeenCalledTimes(1));
    expect(library.create).toHaveBeenCalledWith(
      expect.objectContaining({
        searchText: '100% encoded%20literal',
      }),
    );
  });

  it('treats malformed hub list events as empty search lists', async () => {
    await renderSearches();

    callbacks.list?.({ searches: [{ id: 'bad' }] });

    expect(screen.getByTestId('search-input')).toBeInTheDocument();
  });

  it('ignores malformed hub mutation events without creating undefined searches', async () => {
    await renderSearches();

    callbacks.create?.({ query: 'missing id' });
    callbacks.update?.(null);
    callbacks.delete?.({ id: 42 });
    callbacks.create?.({ id: 'search-1', query: 'valid' });

    expect(await screen.findByTestId('search-list')).toHaveTextContent('search-1');
    expect(screen.getByTestId('search-list')).not.toHaveTextContent('undefined');
  });
});
