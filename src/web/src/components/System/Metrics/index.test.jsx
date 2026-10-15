// <copyright file="index.test.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import * as telemetry from '../../../lib/telemetry';
import Metrics from '.';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';

vi.mock('../../../lib/telemetry');

describe('Metrics', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders while the first metrics request is still pending', () => {
    telemetry.getKpiMetrics.mockReturnValue(new Promise(() => {}));

    render(<Metrics />);

    expect(screen.getByText('Prometheus Metrics')).toBeInTheDocument();
    expect(screen.getByText('Loading metrics')).toBeInTheDocument();
  });

  it('renders empty metrics without crashing', async () => {
    telemetry.getKpiMetrics.mockResolvedValue({});

    render(<Metrics />);

    await waitFor(() =>
      expect(screen.getByText(/Updated /u)).toBeInTheDocument(),
    );
    expect(screen.getByText('Prometheus Metrics')).toBeInTheDocument();
  });

  it('refreshes metrics from a named button', async () => {
    telemetry.getKpiMetrics.mockResolvedValue({});

    render(<Metrics />);

    const refreshAction = await screen.findByRole('button', { name: 'Refresh' });
    fireEvent.click(refreshAction);

    await waitFor(() =>
      expect(telemetry.getKpiMetrics).toHaveBeenCalledTimes(2),
    );
  });

  it('offers a retry when the initial request fails', async () => {
    telemetry.getKpiMetrics
      .mockRejectedValueOnce(new Error('temporary metrics failure'))
      .mockResolvedValueOnce({});

    render(<Metrics />);

    expect(await screen.findByText('Failed to load metrics')).toBeInTheDocument();
    expect(screen.getByText('The request failed. Try again.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Try Again' }));

    await waitFor(() =>
      expect(telemetry.getKpiMetrics).toHaveBeenCalledTimes(2),
    );
    expect(await screen.findByText(/Updated /u)).toBeInTheDocument();
  });
});
