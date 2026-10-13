// <copyright file="Dashboard.test.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import Dashboard from './Dashboard';
import { getTransferSummary } from '../../lib/reports';
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../lib/reports', () => ({
  getTransferSummary: vi.fn(),
}));

describe('Dashboard', () => {
  it('shows successful files and actual transferred bytes for both directions', async () => {
    getTransferSummary.mockResolvedValue({
      Download: {
        Errored: { count: 5, totalBytes: 9000 },
        Succeeded: { count: 3, totalBytes: 1536 },
      },
      Upload: {
        Succeeded: { count: 1, totalBytes: 1024 },
      },
    });

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId('download-bytes')).toHaveTextContent('1.5 KB'));
    expect(screen.getByTestId('download-count')).toHaveTextContent('3 successful files');
    expect(screen.getByTestId('upload-bytes')).toHaveTextContent('1 KB');
    expect(screen.getByTestId('upload-count')).toHaveTextContent('1 successful file');
    expect(screen.getByRole('link', { name: 'Open download list' })).toHaveAttribute(
      'href',
      '/downloads',
    );
  });
});
