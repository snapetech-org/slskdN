// <copyright file="index.test.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import * as bridge from '../../../lib/bridge';
import Bridge from './index';
import useFeatureGates from '../../Shared/useFeatureGates';
import { act, render, screen } from '@testing-library/react';
import React from 'react';

vi.mock('../../../lib/bridge', () => ({
  getConfig: vi.fn(),
  getDashboard: vi.fn(),
  startBridge: vi.fn(),
  stopBridge: vi.fn(),
  updateConfig: vi.fn(),
}));
vi.mock('../../Shared/useFeatureGates', () => ({
  default: vi.fn(),
  isFeatureEnabled: (featureGates, featureId) =>
    featureGates?.[featureId]?.enabled !== false,
}));

const config = {
  enabled: false,
  max_clients: 10,
  port: 2242,
  require_auth: true,
  soulfind_path: 'soulfind',
};

const dashboard = {
  connectedClients: [
    {
      clientId: 'client-1',
      clientType: 'Soulseek Legacy',
      ipAddress: '192.0.2.10',
      requestCount: 7,
    },
  ],
  health: {
    isHealthy: false,
    version: '1.0.0-proxy',
  },
  meshBenefits: {
    bytesViaMesh: 1024,
    bytesViaSoulseek: 1024,
    meshPercentage: 50,
  },
  stats: {
    currentConnections: 1,
    totalBytesProxied: 1024,
    totalDownloads: 3,
    totalSearches: 4,
    uptime: '00:00:10',
  },
};

describe('System Bridge polling', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.resetAllMocks();
    useFeatureGates.mockReturnValue({ featureGates: {}, ready: true });
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false,
    });
    bridge.getConfig.mockResolvedValue(config);
    bridge.getDashboard.mockResolvedValue(dashboard);
    bridge.startBridge.mockResolvedValue({ status: 'started' });
    bridge.stopBridge.mockResolvedValue({ status: 'stopped' });
    bridge.updateConfig.mockResolvedValue({ restart_required: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('shows the VirtualSoulfind gate without loading or polling bridge APIs', () => {
    useFeatureGates.mockReturnValue({
      featureGates: {
        virtualSoulfind: {
          enabled: false,
          message: 'Experimental feature is disabled.',
        },
      },
      ready: true,
    });

    render(<Bridge />);

    expect(screen.getByText('VirtualSoulfind is disabled')).toBeInTheDocument();
    expect(bridge.getConfig).not.toHaveBeenCalled();
    expect(bridge.getDashboard).not.toHaveBeenCalled();
  });

  it('starts only when visible and suspends its ten-second cadence while hidden', async () => {
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: true,
    });
    render(<Bridge />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000);
    });
    expect(bridge.getConfig).not.toHaveBeenCalled();
    expect(bridge.getDashboard).not.toHaveBeenCalled();

    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false,
    });
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
      await Promise.resolve();
    });
    expect(bridge.getConfig).toHaveBeenCalledTimes(1);
    expect(bridge.getDashboard).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(bridge.getDashboard).toHaveBeenCalledTimes(4);

    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: true,
    });
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
      await vi.advanceTimersByTimeAsync(60_000);
    });
    expect(bridge.getDashboard).toHaveBeenCalledTimes(4);
  });

  it('coalesces slow dashboard requests across interval ticks', async () => {
    let completeDashboard;
    bridge.getDashboard.mockReturnValue(
      new Promise((resolve) => {
        completeDashboard = resolve;
      }),
    );
    render(<Bridge />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(bridge.getDashboard).toHaveBeenCalledTimes(1);

    await act(async () => {
      completeDashboard(dashboard);
      await Promise.resolve();
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    expect(bridge.getDashboard).toHaveBeenCalledTimes(2);
  });

  it('retains its last successful dashboard after a transient poll failure', async () => {
    bridge.getDashboard
      .mockResolvedValueOnce(dashboard)
      .mockRejectedValueOnce(new Error('temporary failure'));
    render(<Bridge />);

    expect(await screen.findByText('Soulseek Legacy')).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });

    expect(screen.getByText('Soulseek Legacy')).toBeInTheDocument();
    expect(screen.queryByText('temporary failure')).not.toBeInTheDocument();
  });

  it('retries a failed shared config request when visibility returns', async () => {
    bridge.getConfig
      .mockRejectedValueOnce(new Error('config unavailable'))
      .mockResolvedValueOnce(config);
    render(<Bridge />);

    expect(await screen.findByText('The request failed. Try again.')).toBeInTheDocument();

    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: true,
    });
    document.dispatchEvent(new Event('visibilitychange'));
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false,
    });
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
      await Promise.resolve();
    });

    expect(bridge.getConfig).toHaveBeenCalledTimes(2);
    expect(await screen.findByText('Soulseek Legacy')).toBeInTheDocument();
  });

  it('does not rerender for an uptime-only dashboard change', async () => {
    const onRender = vi.fn();
    bridge.getDashboard
      .mockResolvedValueOnce(dashboard)
      .mockResolvedValueOnce({
        ...dashboard,
        stats: { ...dashboard.stats, uptime: '00:00:20' },
      })
      .mockResolvedValueOnce({
        ...dashboard,
        meshBenefits: { ...dashboard.meshBenefits, meshPercentage: 75 },
      });
    render(
      <React.Profiler
        id="bridge"
        onRender={onRender}
      >
        <Bridge />
      </React.Profiler>,
    );

    expect(await screen.findByText('Soulseek Legacy')).toBeInTheDocument();
    const commitsAfterHydration = onRender.mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });

    expect(bridge.getDashboard).toHaveBeenCalledTimes(2);
    expect(onRender).toHaveBeenCalledTimes(commitsAfterHydration);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    expect(screen.getByText('75.0%')).toBeInTheDocument();
    expect(onRender).toHaveBeenCalledTimes(commitsAfterHydration + 1);
  });
});
