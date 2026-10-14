import ArtistReleaseRadarPanel from './ArtistReleaseRadarPanel';
import {
  fetchArtistReleaseRadarNotifications,
  fetchArtistReleaseRadarSubscriptions,
  routeArtistReleaseRadarNotification,
  subscribeArtistReleaseRadar,
} from '../../lib/musicBrainz';
import { resetInterfaceLanguage, setInterfaceLanguage } from '../../lib/interfaceLocale';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { stubLocaleCatalogFetch } from '../../test/localeCatalogFetchMock';

vi.mock('../../lib/musicBrainz', () => ({
  fetchArtistReleaseRadarNotifications: vi.fn(),
  fetchArtistReleaseRadarSubscriptions: vi.fn(),
  routeArtistReleaseRadarNotification: vi.fn(),
  subscribeArtistReleaseRadar: vi.fn(),
}));

describe('ArtistReleaseRadarPanel', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    fetchArtistReleaseRadarSubscriptions.mockResolvedValue({
      data: [
        {
          artistId: 'artist-1',
          artistName: 'Fixture Artist',
          enabled: true,
          id: 'sub-1',
          mutedReleaseGroupIds: ['rg-muted'],
          scope: 'trusted',
        },
      ],
    });
    fetchArtistReleaseRadarNotifications.mockResolvedValue({
      data: [
        {
          confidence: 0.91,
          id: 'notification-1',
          recordingId: 'recording-1',
          sourceRealm: 'trusted-realm',
          workRef: {
            artist: 'Fixture Artist',
            title: 'New Radar Track',
          },
        },
      ],
    });
    routeArtistReleaseRadarNotification.mockResolvedValue({
      data: {
        success: true,
      },
    });
    subscribeArtistReleaseRadar.mockResolvedValue({
      data: {},
    });
  });

  afterEach(async () => {
    cleanup();
    await resetInterfaceLanguage();
    vi.unstubAllGlobals();
  });

  it('shows subscriptions and direct routing actions for radar hits', async () => {
    render(<ArtistReleaseRadarPanel />);

    expect(await screen.findByText('Fixture Artist')).toBeInTheDocument();
    expect(screen.getByText('Fixture Artist - New Radar Track')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Route New Radar Track radar hit' }),
    ).toBeInTheDocument();
  });

  it('ignores malformed radar list payloads while loading', async () => {
    fetchArtistReleaseRadarSubscriptions.mockResolvedValue({
      data: {
        subscriptions: [
          {
            artistId: 'artist-1',
            artistName: 'Fixture Artist',
          },
        ],
      },
    });
    fetchArtistReleaseRadarNotifications.mockResolvedValue({
      data: {
        notifications: [
          {
            id: 'notification-1',
            workRef: {
              title: 'New Radar Track',
            },
          },
        ],
      },
    });

    render(<ArtistReleaseRadarPanel />);

    await waitFor(() => {
      expect(screen.getByText('Subscriptions')).toBeInTheDocument();
    });
    expect(screen.queryByText('Fixture Artist')).not.toBeInTheDocument();
    expect(screen.queryByText('New Radar Track')).not.toBeInTheDocument();
  });

  it('ignores malformed subscription entries and muted release group lists', async () => {
    fetchArtistReleaseRadarSubscriptions.mockResolvedValue({
      data: [
        null,
        'bad',
        ['bad'],
        {
          artistId: 'artist-1',
          artistName: 'Fixture Artist',
          mutedReleaseGroupIds: { muted: ['rg-muted'] },
          scope: 'trusted',
        },
      ],
    });

    render(<ArtistReleaseRadarPanel />);

    expect(await screen.findByText('Fixture Artist')).toBeInTheDocument();
    expect(screen.getByText('trusted scope · muted 0')).toBeInTheDocument();
  });

  it('saves artist radar subscriptions and routes notifications explicitly', async () => {
    render(<ArtistReleaseRadarPanel />);

    expect(await screen.findByText('Fixture Artist - New Radar Track')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Release radar artist MBID'), {
      target: { value: 'artist-2' },
    });
    fireEvent.change(screen.getByLabelText('Release radar artist name'), {
      target: { value: 'New Artist' },
    });
    fireEvent.change(screen.getByLabelText('Muted release group IDs'), {
      target: { value: 'rg-1, rg-2' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Watch Artist' }));

    await waitFor(() =>
      expect(subscribeArtistReleaseRadar).toHaveBeenCalledWith(
        expect.objectContaining({
          artistId: 'artist-2',
          artistName: 'New Artist',
          enabled: true,
          mutedReleaseGroupIds: ['rg-1', 'rg-2'],
          scope: 'trusted',
        }),
      ),
    );

    fireEvent.change(screen.getByLabelText('Release radar route target peers'), {
      target: { value: 'peer-a, peer-b' },
    });
    fireEvent.click(
      screen.getByRole('button', { name: 'Route New Radar Track radar hit' }),
    );

    await waitFor(() =>
      expect(routeArtistReleaseRadarNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          notificationId: 'notification-1',
          targetPeerIds: ['peer-a', 'peer-b'],
        }),
      ),
    );
  });

  it('localizes the Release Radar load failure', async () => {
    stubLocaleCatalogFetch(vi);
    await setInterfaceLanguage('de');
    fetchArtistReleaseRadarSubscriptions.mockRejectedValueOnce(new Error('offline'));
    fetchArtistReleaseRadarNotifications.mockRejectedValueOnce(new Error('offline'));

    render(<ArtistReleaseRadarPanel />);

    expect(await screen.findByText('Release Radar konnte nicht geladen werden.'))
      .toBeInTheDocument();
  });
});
