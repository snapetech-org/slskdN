import * as transfers from '../../lib/transfers';
import Directory from './Directory';
import React from 'react';
import userEvent from '@testing-library/user-event';
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('../../lib/transfers', () => ({
  download: vi.fn(),
}));

describe('Directory', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows network download errors without requiring an HTTP response', async () => {
    const user = userEvent.setup();
    transfers.download.mockRejectedValue(new Error('Network unavailable'));

    render(
      <Directory
        destination="downloads"
        files={[{ filename: 'track.mp3', size: 1024 }]}
        locked={false}
        name="Music"
        username="alice"
      />,
    );

    await user.click(screen.getByRole('checkbox', { name: 'Select track.mp3' }));
    await user.click(screen.getByRole('button', { name: 'Download' }));

    expect(await screen.findByTestId('browse-download-error'))
      .toHaveTextContent('The download request could not be completed.');
  });
});
