// <copyright file="index.test.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import * as securityApi from '../../../lib/security';
import Security from './index';
import { act, fireEvent, render, screen } from '@testing-library/react';
import React from 'react';

vi.mock('../../../lib/security', () => ({
  getDashboard: vi.fn(),
}));

vi.mock('./AdversarialSettings', () => ({
  default: () => <div>Adversarial Settings</div>,
}));

const dashboard = {
  eventStats: { totalEvents: 4 },
  networkGuardStats: { globalConnections: 1 },
  reputationStats: { totalPeers: 2 },
  violationStats: { trackedIps: 3 },
};

describe('System Security polling', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.resetAllMocks();
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false,
    });
    securityApi.getDashboard.mockResolvedValue(dashboard);
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it('pauses polling while hidden and catches up when visible', async () => {
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: true,
    });
    render(<Security />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(90_000);
    });
    expect(securityApi.getDashboard).not.toHaveBeenCalled();

    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false,
    });
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
      await Promise.resolve();
    });
    expect(securityApi.getDashboard).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(securityApi.getDashboard).toHaveBeenCalledTimes(2);

    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: true,
    });
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
      await vi.advanceTimersByTimeAsync(90_000);
    });
    expect(securityApi.getDashboard).toHaveBeenCalledTimes(2);
  });

  it('does not overlap slow dashboard requests', async () => {
    let completeRequest;
    securityApi.getDashboard.mockReturnValue(
      new Promise((resolve) => {
        completeRequest = resolve;
      }),
    );
    render(<Security />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(90_000);
    });
    expect(securityApi.getDashboard).toHaveBeenCalledTimes(1);

    await act(async () => {
      completeRequest(dashboard);
      await Promise.resolve();
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(securityApi.getDashboard).toHaveBeenCalledTimes(2);
  });

  it('retains the last successful dashboard after a transient failure', async () => {
    securityApi.getDashboard
      .mockResolvedValueOnce(dashboard)
      .mockRejectedValueOnce(new Error('temporary failure'));
    render(<Security />);

    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByText('Security Status')).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(screen.getByText('Security Status')).toBeInTheDocument();
    expect(screen.queryByText('Security Module Unavailable')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Adversarial'));
    expect(screen.getByText('Adversarial Settings')).toBeInTheDocument();
  });

  it('clears a manual refresh spinner when hidden during the request', async () => {
    let completeRequest;
    securityApi.getDashboard
      .mockResolvedValueOnce(dashboard)
      .mockReturnValueOnce(
        new Promise((resolve) => {
          completeRequest = resolve;
        }),
      );
    render(<Security />);

    await act(async () => {
      await Promise.resolve();
    });

    const refreshButton = screen.getByRole('button', {
      name: 'Refresh the security dashboard',
    });
    fireEvent.click(refreshButton);
    expect(refreshButton).toHaveClass('loading');

    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: true,
    });
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
      await Promise.resolve();
    });
    expect(refreshButton).not.toHaveClass('loading');

    completeRequest(dashboard);
  });

  it('reports an initial dashboard failure', async () => {
    securityApi.getDashboard.mockRejectedValue(new Error('unavailable'));
    render(<Security />);

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText('Security Module Unavailable')).toBeInTheDocument();
    expect(screen.getByText('unavailable')).toBeInTheDocument();
  });
});
