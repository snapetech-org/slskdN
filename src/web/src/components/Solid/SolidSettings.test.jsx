import SolidSettings from './SolidSettings';
import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import api from '../../lib/api';

vi.mock('../../lib/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('SolidSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('reports a status failure, retries, and resolves an accessible WebID field', async () => {
    api.get
      .mockRejectedValueOnce({
        response: { data: { detail: 'Solid status unavailable', status: 503 } },
      })
      .mockResolvedValueOnce({ data: { enabled: true, clientId: 'client-1' } });
    api.post.mockResolvedValue({ data: { webId: 'https://example.test/profile#me' } });

    render(<SolidSettings />);

    expect(await screen.findByRole('alert')).toHaveTextContent('The request failed. Try again.');
    fireEvent.click(screen.getByRole('button', { name: 'Retry Status' }));

    const webIdInput = await screen.findByRole('textbox', { name: 'WebID' });
    fireEvent.change(webIdInput, {
      target: { value: 'https://example.test/profile#me' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Resolve WebID' }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/solid/resolve-webid', {
        webId: 'https://example.test/profile#me',
      });
      expect(screen.getByText(/https:\/\/example\.test\/profile#me/)).toBeInTheDocument();
    });
    expect(api.get).toHaveBeenCalledTimes(2);
  });

  it('does not allow a WebID resolution while Solid is disabled', async () => {
    api.get.mockResolvedValue({ data: { enabled: false } });
    render(<SolidSettings />);

    expect(await screen.findByText(/Solid integration is disabled/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Resolve WebID' })).toBeDisabled();
    expect(api.post).not.toHaveBeenCalled();
  });
});
