import SharedWithMe from './SharedWithMe';
import * as collectionsAPI from '../../lib/collections';
import * as identityAPI from '../../lib/identity';
import { createRemoteShareStreamUrl } from '../../lib/streaming';
import React from 'react';
import userEvent from '@testing-library/user-event';
import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('../../lib/collections', () => ({
  backfillShare: vi.fn(),
  getCollection: vi.fn(),
  getShareManifest: vi.fn(),
  getShares: vi.fn(),
}));

vi.mock('../../lib/identity', () => ({
  getContacts: vi.fn(),
}));

vi.mock('../../lib/streaming', () => ({
  createRemoteShareStreamUrl: vi.fn(),
}));

const shareToken = 'reusable-share-token';

describe('SharedWithMe', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    collectionsAPI.getShares.mockResolvedValue({
      data: [
        {
          allowDownload: true,
          allowStream: true,
          collectionId: 'collection-1',
          id: 'share-1',
          shareToken,
        },
      ],
    });
    collectionsAPI.getCollection.mockResolvedValue({
      data: {
        ownerUserId: 'owner-1',
        title: 'Shared Album',
        type: 'ShareList',
      },
    });
    collectionsAPI.getShareManifest.mockResolvedValue({
      data: {
        items: { contentId: 'bad-shape' },
        title: 'Shared Album',
      },
    });
    identityAPI.getContacts.mockResolvedValue({ data: [] });
    createRemoteShareStreamUrl.mockResolvedValue(
      'https://owner.example/api/v0/streams/sha256%3Atrack?ticket=short-lived-ticket',
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders a manifest with malformed items as an empty collection', async () => {
    const user = userEvent.setup();
    render(<SharedWithMe />);

    expect(await screen.findByText('Shared Album')).toBeInTheDocument();
    await user.click(screen.getByTestId('incoming-share-open'));

    await waitFor(() => expect(collectionsAPI.getShareManifest).toHaveBeenCalledWith('share-1'));
    expect(await screen.findByText('No items in this collection')).toBeInTheDocument();
  });

  it('explains when an incoming share has no peer-reachable stream endpoint', async () => {
    const user = userEvent.setup();
    collectionsAPI.getShareManifest.mockResolvedValue({
      data: {
        items: [{ contentId: 'sha256:track', mediaKind: 'Audio', streamUrl: null }],
        title: 'Shared Album',
      },
    });
    render(<SharedWithMe />);

    expect(await screen.findByText('Shared Album')).toBeInTheDocument();
    await user.click(screen.getByTestId('incoming-share-open'));

    expect(await screen.findByTestId('incoming-stream-unavailable'))
      .toHaveTextContent('sharing.externalEndpoint');
    expect(screen.queryByTestId('incoming-stream-track')).not.toBeInTheDocument();
  });

  it('normalizes malformed backfill responses before rendering results', async () => {
    const user = userEvent.setup();
    collectionsAPI.backfillShare.mockResolvedValue({ data: null });
    render(<SharedWithMe />);

    expect(await screen.findByText('Shared Album')).toBeInTheDocument();
    await user.click(screen.getByTestId('incoming-share-open'));
    await screen.findByText('No items in this collection');
    await user.click(screen.getByTestId('incoming-backfill'));

    await waitFor(() => expect(collectionsAPI.backfillShare).toHaveBeenCalledWith('share-1'));
    expect(await screen.findByText(/0 enqueued, 0 failed/)).toBeInTheDocument();
  });

  it('renders structured backfill errors in the open collection dialog', async () => {
    const user = userEvent.setup();
    collectionsAPI.backfillShare.mockRejectedValue({
      response: {
        data: {
          detail: 'Backfill is disabled for this share',
          status: 400,
          title: 'Bad Request',
        },
      },
    });
    render(<SharedWithMe />);

    expect(await screen.findByText('Shared Album')).toBeInTheDocument();
    await user.click(screen.getByTestId('incoming-share-open'));
    await screen.findByText('No items in this collection');
    await user.click(screen.getByTestId('incoming-backfill'));

    expect(await screen.findByText('Failed to start backfill'))
      .toBeInTheDocument();
  });

  it('shows manifest errors inside the dialog and retries the same request', async () => {
    const user = userEvent.setup();
    collectionsAPI.getShareManifest.mockRejectedValueOnce({
      response: {
        data: {
          detail: 'Manifest token expired',
          status: 403,
          title: 'Forbidden',
        },
      },
    });
    render(<SharedWithMe />);

    expect(await screen.findByText('Shared Album')).toBeInTheDocument();
    await user.click(screen.getByTestId('incoming-share-open'));
    expect(await screen.findByTestId('incoming-manifest-error'))
      .toHaveTextContent('Failed to load manifest');
    await user.click(screen.getByRole('button', { name: 'Retry Contents' }));

    expect(await screen.findByText('No items in this collection')).toBeInTheDocument();
    expect(collectionsAPI.getShareManifest).toHaveBeenCalledTimes(2);
  });

  it('does not claim there are no shares after a failed list request and can retry', async () => {
    const user = userEvent.setup();
    collectionsAPI.getShares.mockRejectedValueOnce({
      response: { data: { detail: 'Share list unavailable' } },
    });
    render(<SharedWithMe />);

    expect(await screen.findByText('Failed to load incoming shares')).toBeInTheDocument();
    expect(screen.queryByText('No shares yet')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Retry' }));

    expect(await screen.findByText('Shared Album')).toBeInTheDocument();
    expect(collectionsAPI.getShares).toHaveBeenCalledTimes(2);
  });

  it('opens a ticketed stream and never navigates to a reusable-token URL', async () => {
    const user = userEvent.setup();
    const popup = {
      close: vi.fn(),
      closed: false,
      location: { replace: vi.fn() },
      opener: {},
    };
    vi.spyOn(window, 'open').mockReturnValue(popup);
    collectionsAPI.getShareManifest.mockResolvedValue({
      data: {
        items: [
          {
            contentId: 'sha256:track',
            fileName: 'track.mp3',
            mediaKind: 'Audio',
            streamUrl: `https://owner.example/api/v0/streams/sha256%3Atrack?token=${shareToken}`,
          },
        ],
        title: 'Shared Album',
      },
    });
    render(<SharedWithMe />);

    expect(await screen.findByText('Shared Album')).toBeInTheDocument();
    await user.click(screen.getByTestId('incoming-share-open'));
    await screen.findByTestId('shared-manifest');
    await user.click(screen.getByTestId('incoming-stream-track'));

    await waitFor(() => expect(popup.location.replace).toHaveBeenCalledWith(
      'https://owner.example/api/v0/streams/sha256%3Atrack?ticket=short-lived-ticket',
    ));
    expect(createRemoteShareStreamUrl).toHaveBeenCalledWith(
      `https://owner.example/api/v0/streams/sha256%3Atrack?token=${shareToken}`,
      'sha256:track',
      shareToken,
    );
    expect(window.open).toHaveBeenCalledWith('about:blank', '_blank');
    expect(popup.location.replace.mock.calls[0][0]).not.toContain(shareToken);
  });

  it('explains failed secure stream preparation in the manifest dialog', async () => {
    const user = userEvent.setup();
    const popup = {
      close: vi.fn(),
      closed: false,
      location: { replace: vi.fn() },
      opener: {},
    };
    vi.spyOn(window, 'open').mockReturnValue(popup);
    createRemoteShareStreamUrl.mockRejectedValue(new TypeError('Failed to fetch'));
    collectionsAPI.getShareManifest.mockResolvedValue({
      data: {
        items: [
          {
            contentId: 'sha256:track',
            fileName: 'track.mp3',
            mediaKind: 'Audio',
            streamUrl: `https://owner.example/api/v0/streams/sha256%3Atrack?token=${shareToken}`,
          },
        ],
        title: 'Shared Album',
      },
    });
    render(<SharedWithMe />);

    expect(await screen.findByText('Shared Album')).toBeInTheDocument();
    await user.click(screen.getByTestId('incoming-share-open'));
    await screen.findByTestId('shared-manifest');
    await user.click(screen.getByTestId('incoming-stream-track'));

    expect(await screen.findByTestId('incoming-stream-error'))
      .toHaveTextContent('CORS settings');
    expect(popup.close).toHaveBeenCalled();
  });
});
