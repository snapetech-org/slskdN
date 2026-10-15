// <copyright file="Lidarr.test.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import * as lidarrAPI from '../../lib/lidarr';
import * as wishlistAPI from '../../lib/wishlist';
import Lidarr, {
  areLidarrStatusesEqual,
  areLidarrSyncStatesEqual,
} from './Lidarr';
import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { toast } from 'react-toastify';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../lib/lidarr', () => ({
  getStatus: vi.fn(),
  getSyncStatus: vi.fn(),
  getWantedMissing: vi.fn(),
  getImportHistory: vi.fn(),
  importCompletedDirectory: vi.fn(),
  retryImport: vi.fn(),
  syncWanted: vi.fn(),
}));

vi.mock('../../lib/wishlist', () => ({
  getAll: vi.fn(),
}));

vi.mock('react-toastify', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

describe('Lidarr', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false,
    });
    lidarrAPI.getStatus.mockResolvedValue({
      appName: 'Lidarr',
      version: '2.0.0',
    });
    lidarrAPI.getSyncStatus.mockResolvedValue({ isSyncing: false });
    lidarrAPI.getWantedMissing.mockResolvedValue({
      records: [],
      totalRecords: 0,
    });
    lidarrAPI.getImportHistory.mockResolvedValue([]);
    wishlistAPI.getAll.mockResolvedValue([]);
  });

  afterEach(() => {
    vi.useRealTimers();
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false,
    });
  });

  it('compares only status fields rendered by the dashboard', () => {
    const status = { appName: 'Lidarr', version: '2.0.0' };
    const syncState = {
      isSyncing: false,
      lastSyncAt: '2026-07-16T00:00:00Z',
      nextSyncAt: '2026-07-16T01:00:00Z',
      lastError: null,
      lastResult: {
        wantedCount: 3,
        createdCount: 1,
        duplicateCount: 2,
        skippedCount: 0,
      },
    };

    expect(areLidarrStatusesEqual(status, { ...status })).toBe(true);
    expect(areLidarrStatusesEqual(status, { ...status, version: '2.1.0' })).toBe(false);
    expect(areLidarrSyncStatesEqual(syncState, {
      ...syncState,
      lastResult: { ...syncState.lastResult },
    })).toBe(true);
    expect(areLidarrSyncStatesEqual(syncState, {
      ...syncState,
      lastResult: { ...syncState.lastResult, createdCount: 2 },
    })).toBe(false);
  });

  it('hydrates once after Strict Mode replays the polling effect', async () => {
    render(
      <React.StrictMode>
        <Lidarr />
      </React.StrictMode>,
    );

    expect(await screen.findByText('Lidarr 2.0.0')).toBeInTheDocument();
    expect(lidarrAPI.getStatus).toHaveBeenCalledTimes(1);
    expect(lidarrAPI.getSyncStatus).toHaveBeenCalledTimes(1);
  });

  it('explains that manual sync pulls missing albums into the wishlist', async () => {
    render(<Lidarr />);

    await screen.findByText('Lidarr 2.0.0');
    const syncButton = screen.getByRole('button', { name: 'Sync Wanted Now' });
    fireEvent.mouseEnter(syncButton);

    expect(
      await screen.findByText(
        "Fetch Lidarr's missing albums and add new ones to the slskdN wishlist.",
      ),
    ).toBeInTheDocument();
  });

  it('labels refresh and pagination actions', async () => {
    lidarrAPI.getWantedMissing.mockResolvedValue({
      records: [{ albumType: 'Album', id: 1, title: 'Album One' }],
      totalRecords: 51,
    });
    wishlistAPI.getAll.mockResolvedValue(
      Array.from({ length: 51 }, (_, index) => ({
        autoDownload: true,
        enabled: true,
        filter: 'flac',
        id: `wishlist-${index}`,
        searchText: `Album ${index}`,
      })),
    );

    render(<Lidarr />);

    expect(
      await screen.findByRole('button', {
        name: 'Refresh Lidarr wishlist items',
      }),
    ).toBeInTheDocument();
    await screen.findByText('Album One');
    await screen.findByText('Album 0');
    expect(
      screen.getByRole('button', { name: 'Previous Lidarr album page' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Next Lidarr album page' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Previous Lidarr wishlist page' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Next Lidarr wishlist page' }),
    ).toBeInTheDocument();
  });

  it('reports the queued file count for a manual import', async () => {
    lidarrAPI.importCompletedDirectory.mockResolvedValue({
      candidateCount: 3,
      commandId: 42,
      safeCandidateCount: 2,
    });

    render(<Lidarr />);

    const input = await screen.findByPlaceholderText('/mnt/datapool_lvm_media/download/music/Artist/Album');
    fireEvent.change(input, { target: { value: '/downloads/Artist/Album' } });
    fireEvent.click(await screen.findByRole('button', { name: 'Run Manual Import' }));

    await waitFor(() => {
      expect(lidarrAPI.importCompletedDirectory).toHaveBeenCalledWith({
        directory: '/downloads/Artist/Album',
      });
    });
    expect(toast.success).toHaveBeenCalledWith('Lidarr import queued: 2 file(s)');
    expect(input).toHaveValue('');
  });

  it('shows failed imports and retries the recorded directory', async () => {
    lidarrAPI.getImportHistory.mockResolvedValue([
      {
        candidateCount: 1,
        completedAt: '2026-08-17T12:00:00Z',
        directory: '/downloads/Artist/Album',
        errorMessage: 'Artist with ID 0 does not exist',
        id: 'history-1',
        safeCandidateCount: 1,
        startedAt: '2026-08-17T11:59:00Z',
        status: 'Failed',
      },
    ]);
    lidarrAPI.retryImport.mockResolvedValue({
      commandId: 42,
      safeCandidateCount: 1,
    });

    render(<Lidarr />);

    expect(await screen.findByText('The request failed. Try again.')).toBeInTheDocument();
    const retry = screen.getByRole('button', { name: 'Retry Lidarr import for /downloads/Artist/Album' });
    fireEvent.click(retry);

    await waitFor(() => {
      expect(lidarrAPI.retryImport).toHaveBeenCalledWith('history-1');
    });
    expect(toast.success).toHaveBeenCalledWith('Lidarr import queued: 1 file(s)');
  });

  it('does not overlap slow status polls', async () => {
    vi.useFakeTimers();
    let resolveStatus;
    lidarrAPI.getStatus.mockReturnValue(
      new Promise((resolve) => {
        resolveStatus = resolve;
      }),
    );

    render(<Lidarr />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(90_000);
    });

    expect(lidarrAPI.getStatus).toHaveBeenCalledTimes(1);
    expect(lidarrAPI.getSyncStatus).toHaveBeenCalledTimes(1);

    resolveStatus({ appName: 'Lidarr', version: '2.0.0' });
    await act(async () => {
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(30_000);
    });

    expect(lidarrAPI.getStatus).toHaveBeenCalledTimes(2);
    expect(lidarrAPI.getSyncStatus).toHaveBeenCalledTimes(2);
  });

  it('suspends polling while hidden and refreshes when visible', async () => {
    vi.useFakeTimers();
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: true,
    });

    render(<Lidarr />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(120_000);
    });
    expect(lidarrAPI.getStatus).not.toHaveBeenCalled();
    expect(lidarrAPI.getSyncStatus).not.toHaveBeenCalled();

    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false,
    });
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
      await Promise.resolve();
    });
    expect(lidarrAPI.getStatus).toHaveBeenCalledTimes(1);
    expect(lidarrAPI.getSyncStatus).toHaveBeenCalledTimes(1);

    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: true,
    });
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
      await vi.advanceTimersByTimeAsync(120_000);
    });
    expect(lidarrAPI.getStatus).toHaveBeenCalledTimes(1);
    expect(lidarrAPI.getSyncStatus).toHaveBeenCalledTimes(1);
  });
});
