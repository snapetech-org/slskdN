import PlaylistIntake from './PlaylistIntake';
import * as collectionsAPI from '../../lib/collections';
import { resetInterfaceLanguage, setInterfaceLanguage } from '../../lib/interfaceLocale';
import { playlistIntakeStorageKey } from '../../lib/playlistIntake';
import { fireEvent, render, screen, within } from '@testing-library/react';
import React from 'react';
import { afterEach, beforeEach, vi } from 'vitest';
import { stubLocaleCatalogFetch } from '../../test/localeCatalogFetchMock';

vi.mock('../../lib/collections', () => ({
  addCollectionItem: vi.fn(),
  createCollection: vi.fn(),
}));

describe('PlaylistIntake', () => {
  afterEach(async () => {
    await resetInterfaceLanguage();
    vi.unstubAllGlobals();
  });

  beforeEach(() => {
    stubLocaleCatalogFetch(vi);
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('imports playlist rows locally for direct review', () => {
    render(<PlaylistIntake />);

    fireEvent.change(screen.getByLabelText('Playlist name'), {
      target: { value: 'Road trip' },
    });
    fireEvent.change(screen.getByLabelText('Playlist source'), {
      target: { value: 'local:road-trip.csv' },
    });
    fireEvent.change(screen.getByLabelText('Playlist rows'), {
      target: {
        value: 'Stereolab,French Disko\nBroadcast - Come On Let\'s Go',
      },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Import playlist for review' }));

    const persisted = JSON.parse(localStorage.getItem(playlistIntakeStorageKey));
    expect(persisted).toHaveLength(1);
    expect(persisted[0]).toMatchObject({
      name: 'Road trip',
      provider: 'CSV',
      source: 'local:road-trip.csv',
    });
    expect(persisted[0].tracks).toHaveLength(2);
    expect(screen.getByText('Tracks')).toBeInTheDocument();
    expect(screen.getByText('Ready for review')).toBeInTheDocument();
  });

  it('sets Arabic language and direction on the multi-artist policy control', async () => {
    await setInterfaceLanguage('ar');
    render(<PlaylistIntake />);

    fireEvent.change(screen.getByLabelText('اسم قائمة التشغيل'), {
      target: { value: 'Road trip' },
    });
    fireEvent.change(screen.getByLabelText('مصدر قائمة التشغيل'), {
      target: { value: 'local:road-trip.csv' },
    });
    fireEvent.change(screen.getByLabelText('صفوف قائمة التشغيل'), {
      target: { value: 'Stereolab,French Disko' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'استيراد قائمة التشغيل للمراجعة' }));

    const label = screen.getByText('فنانون متعددون');
    expect(label).toHaveAttribute('lang', 'ar');
    expect(label).toHaveAttribute('dir', 'rtl');
    const control = label.closest('.field').querySelector('[role="listbox"]');
    expect(control).toHaveAttribute('lang', 'ar');
    expect(control).toHaveAttribute('dir', 'rtl');
  });

  it('supports row review states and playlist previews', () => {
    render(<PlaylistIntake />);

    fireEvent.change(screen.getByLabelText('Playlist name'), {
      target: { value: 'Mirror queue' },
    });
    fireEvent.change(screen.getByLabelText('Playlist source'), {
      target: { value: 'local:mirror.m3u' },
    });
    fireEvent.change(screen.getByLabelText('Playlist rows'), {
      target: {
        value: 'Stereolab - French Disko\nBroadcast - Come On Let\'s Go',
      },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Import playlist for review' }));

    expect(screen.getByText('Ready for review')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Mark French Disko unmatched' }));
    expect(screen.getByText('Partial completion allowed')).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole('button', { name: 'Reject playlist row Come On Let\'s Go' }),
    );
    const playlistCard = screen.getByText('Mirror queue').closest('.playlist-intake-card');
    expect(playlistCard.querySelector('.playlist-intake-summary'))
      .toHaveTextContent('Rejected 1');

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Preview slskdN playlist for Mirror queue',
      }),
    );
    expect(
      screen.getByText(/Playlist build preview only; creating it writes/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/# Mirror queue/)).toBeInTheDocument();
  });

  it('creates playlist collections from matched rows', async () => {
    collectionsAPI.createCollection.mockResolvedValue({
      data: { id: 'collection-1' },
    });
    collectionsAPI.addCollectionItem.mockResolvedValue({});

    render(<PlaylistIntake />);

    fireEvent.change(screen.getByLabelText('Playlist name'), {
      target: { value: 'Provider mirror' },
    });
    fireEvent.change(screen.getByLabelText('Playlist source'), {
      target: { value: 'https://open.spotify.com/playlist/test' },
    });
    fireEvent.change(screen.getByLabelText('Playlist rows'), {
      target: { value: 'Stereolab - French Disko' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Import playlist for review' }));

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Create slskdN playlist for Provider mirror',
      }),
    );

    expect(
      await screen.findByText(/Created playlist collection for Provider mirror/),
    ).toBeInTheDocument();
    expect(collectionsAPI.createCollection).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Provider mirror',
        type: 'Playlist',
      }),
    );
    expect(collectionsAPI.addCollectionItem).toHaveBeenCalledWith(
      'collection-1',
      expect.objectContaining({
        mediaKind: 'PlannedTrack',
      }),
    );
  });

  it('previews tag organization plans without writing files', () => {
    render(<PlaylistIntake />);

    fireEvent.change(screen.getByLabelText('Playlist name'), {
      target: { value: 'Organization queue' },
    });
    fireEvent.change(screen.getByLabelText('Playlist source'), {
      target: { value: 'local:organization.csv' },
    });
    fireEvent.change(screen.getByLabelText('Playlist rows'), {
      target: {
        value: 'Stereolab,French Disko\nUntitled',
      },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Import playlist for review' }));

    fireEvent.change(
      screen.getByLabelText('Organization album title for Organization queue'),
      {
        target: { value: 'Road Trip Tags' },
      },
    );
    fireEvent.click(
      screen.getByRole('button', {
        name: 'Preview tag organization for Organization queue',
      }),
    );

    expect(
      screen.getByText(/Prepared tag and organization dry run for Organization queue/),
    ).toBeInTheDocument();
    expect(screen.getByText(/no tag write, cover-art write/i)).toBeInTheDocument();
    expect(
      screen.getByText('Stereolab/Road Trip Tags/01 - French Disko.flac'),
    ).toBeInTheDocument();
    expect(screen.getByText('Changed fields')).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Copy tag organization report for Organization queue',
      }),
    );
    expect(
      screen.getByText(/Prepared tag and organization report for Organization queue/),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Approve tag organization snapshot for Organization queue',
      }),
    );
    expect(
      screen.getByText(/Approved tag and organization snapshot for Organization queue/),
    ).toBeInTheDocument();
    expect(screen.getByText('Snapshot approved')).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Clear tag organization snapshot for Organization queue',
      }),
    );
    expect(
      screen.getByText(/Cleared tag and organization snapshot for Organization queue/),
    ).toBeInTheDocument();

    const persisted = JSON.parse(localStorage.getItem(playlistIntakeStorageKey));
    expect(persisted[0].organizationPlan.summary).toMatchObject({
      matched: 1,
      skipped: 1,
    });
    expect(persisted[0].organizationApproval).toBeNull();
    expect(persisted[0].tracks.map((track) => track.state)).toEqual([
      'Matched',
      'Unmatched',
    ]);
  });
});
