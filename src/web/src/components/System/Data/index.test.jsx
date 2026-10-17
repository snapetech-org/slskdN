import '@testing-library/jest-dom';
import Data from './index';
import React from 'react';
import { clearCompleted } from '../../../lib/transfers';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../../lib/transfers', () => ({
  clearCompleted: vi.fn(),
}));

vi.mock('react-toastify', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

describe('System Transfer Data', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('explains the upload cleanup before keyboard activation', async () => {
    clearCompleted.mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<Data />);

    const uploadAction = screen.getByRole('button', {
      name: 'Clear All Completed Uploads',
    });
    uploadAction.focus();

    expect(await screen.findByText(
      'Remove completed upload records from transfer history to keep the Uploads page responsive.',
    )).toBeVisible();
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(clearCompleted).toHaveBeenCalledWith({ direction: 'upload' });
    });
  });

  it('recovers after a failed clear and allows a successful retry', async () => {
    clearCompleted
      .mockRejectedValueOnce({
        response: { data: { message: 'Transfer history is unavailable.' } },
      })
      .mockResolvedValueOnce(undefined);
    const user = userEvent.setup();
    render(<Data />);

    const downloadAction = screen.getByRole('button', {
      name: 'Clear All Completed Downloads',
    });
    await user.click(downloadAction);

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Downloads: The request failed. Try again.',
    );
    expect(downloadAction).toBeEnabled();
    await user.click(downloadAction);

    await waitFor(() => {
      expect(clearCompleted).toHaveBeenCalledTimes(2);
    });
    expect(clearCompleted).toHaveBeenLastCalledWith({ direction: 'download' });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
