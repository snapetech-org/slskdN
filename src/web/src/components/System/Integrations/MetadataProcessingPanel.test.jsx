import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import MetadataProcessingPanel from './MetadataProcessingPanel';
import { getMetadataProcessingStatus } from '../../../lib/slskdn';

vi.mock('../../../lib/slskdn', () => ({
  getMetadataProcessingStatus: vi.fn(),
}));

test('shows active and completed metadata provider stages', async () => {
  getMetadataProcessingStatus.mockResolvedValue({
    active: [
      {
        id: 'active-1',
        filename: 'track.flac',
        stage: 'acoustid',
        status: 'running',
        startedAt: '2026-07-27T16:00:00Z',
      },
    ],
    history: [
      {
        id: 'history-1',
        filename: 'track.flac',
        stage: 'musicbrainz',
        status: 'complete',
        detail: 'Recording metadata found',
        startedAt: '2026-07-27T15:59:00Z',
      },
    ],
  });

  render(<MetadataProcessingPanel />);

  await waitFor(() => expect(screen.getByText('AcoustID')).toBeInTheDocument());
  expect(screen.getByText('MusicBrainz')).toBeInTheDocument();
  expect(screen.getByText('Recording metadata found')).toBeInTheDocument();
  expect(getMetadataProcessingStatus).toHaveBeenCalledWith(50);
});
