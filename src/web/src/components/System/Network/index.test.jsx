// <copyright file="index.test.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import * as slskdnAPI from '../../../lib/slskdn';
import { resetInterfaceLanguage, setInterfaceLanguage } from '../../../lib/interfaceLocale';
import { stubLocaleCatalogFetch } from '../../../test/localeCatalogFetchMock';
import Network from '.';
import useFeatureGates from '../../Shared/useFeatureGates';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import userEvent from '@testing-library/user-event';
import { toast } from 'react-toastify';

vi.mock('../../../lib/slskdn');
vi.mock('../../Shared/useFeatureGates', () => ({
  default: vi.fn(),
  isFeatureEnabled: (featureGates, featureId) =>
    featureGates?.[featureId]?.enabled !== false,
}));
vi.mock('../../Shared', () => ({
  LoaderSegment: () => <div>Loading...</div>,
  ShrinkableButton: ({ children, tooltip, ...props }) => (
    <button
      title={tooltip}
      {...props}
    >
      {children}
    </button>
  ),
}));
vi.mock('react-toastify', () => ({
  toast: {
    error: vi.fn(),
    info: vi.fn(),
    success: vi.fn(),
  },
}));

describe('Network', () => {
  beforeEach(async () => {
    stubLocaleCatalogFetch(vi);
    jest.clearAllMocks();
    useFeatureGates.mockReturnValue({ featureGates: {}, ready: true });
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
    window.localStorage.clear();
    await act(async () => {
      await setInterfaceLanguage('en');
    });
    slskdnAPI.getSlskdnStats.mockResolvedValue({
      backfill: {
        completedToday: 0,
        discoveryRate: 0,
        isActive: false,
        pendingCount: 0,
      },
      capabilities: { features: [], version: 'slskdn' },
      dht: {
        dhtNodeCount: 0,
        isEnabled: true,
        isLanOnly: false,
        isDhtRunning: true,
      },
      discoveredPeers: [],
      hashDb: { currentSeqId: 0, totalEntries: 0 },
      mesh: {
        connectedPeerCount: 0,
        warnings: [],
      },
      meshPeers: [],
      swarmJobs: [],
    });
  });

  afterEach(async () => {
    await act(async () => {
      await resetInterfaceLanguage();
    });
    vi.useRealTimers();
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false,
    });
  });

  it('disables mesh actions and labels gated network features when unavailable', async () => {
    useFeatureGates.mockReturnValue({
      featureGates: {
        dht: { enabled: false, message: 'Experimental feature is disabled.' },
        mesh: { enabled: false, message: 'Experimental feature is disabled.' },
        multiSourceDownloads: {
          enabled: false,
          message: 'Experimental feature is disabled.',
        },
      },
      ready: true,
    });
    slskdnAPI.getSlskdnStats.mockResolvedValue({
      capabilities: { features: [], version: 'slskdn' },
      dht: { dhtNodeCount: 0, isDhtRunning: false },
      discoveredPeers: [],
      hashDb: { currentSeqId: 0, totalEntries: 0 },
      mesh: { connectedPeerCount: 1, warnings: [] },
      meshPeers: [{ username: 'mesh-peer' }],
      swarmJobs: [{ filename: '/tmp/file.flac', jobId: 'swarm-disabled' }],
    });

    render(<Network theme="light" />);

    expect(await screen.findByText('Mesh is disabled')).toBeInTheDocument();
    expect(screen.getByText('DHT rendezvous is disabled')).toBeInTheDocument();
    expect(screen.getByText('Multi-source downloads is disabled')).toBeInTheDocument();
    expect(screen.getByText('Disabled')).toBeInTheDocument();
    expect(screen.queryByText('swarm-disabled')).not.toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Sync' }),
    ).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Sync' }));
    expect(slskdnAPI.triggerMeshSync).not.toHaveBeenCalled();
  });
  it('shows the connectivity diagnostics warning when no peers are reachable', async () => {
    render(<Network theme="light" />);

    await waitFor(() => {
      expect(screen.getByText('Connectivity diagnostics')).toBeInTheDocument();
    });

    expect(
      screen.getByText(/configured Soulseek listen port is reachable/i),
    ).toBeInTheDocument();
    expect(screen.getByText('Network Health')).toBeInTheDocument();
    expect(screen.getByText('Needs attention')).toBeInTheDocument();
  });

  it('copies a network health report', async () => {
    render(<Network theme="light" />);

    await waitFor(() => {
      expect(screen.getByText('Network Health')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Copy network health report' }));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        expect.stringContaining('slskdN network health report'),
      );
    });
  });

  it('reports a mesh sync error instead of showing a success toast', async () => {
    slskdnAPI.getSlskdnStats.mockResolvedValueOnce({
      capabilities: { features: [], version: 'slskdN' },
      dht: {},
      hashDb: {},
      mesh: { connectedPeerCount: 1, warnings: [] },
      meshPeers: [{ username: 'mesh-peer' }],
      swarmJobs: [],
    });
    slskdnAPI.triggerMeshSync.mockResolvedValueOnce({
      error: 'Failed to sync with peer',
      success: false,
    });

    render(<Network theme="light" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Sync' }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to sync with peer');
    });
    expect(toast.success).not.toHaveBeenCalledWith('Sync initiated with mesh-peer');
  });

  it('translates fixed server mesh-sync errors', async () => {
    await act(async () => {
      await setInterfaceLanguage('es');
    });
    slskdnAPI.getSlskdnStats.mockResolvedValueOnce({
      capabilities: { features: [], version: 'slskdN' },
      dht: {},
      hashDb: {},
      mesh: { connectedPeerCount: 1, warnings: [] },
      meshPeers: [{ username: 'mesh-peer' }],
      swarmJobs: [],
    });
    slskdnAPI.triggerMeshSync.mockResolvedValueOnce({
      error: 'Failed to sync with peer',
      success: false,
    });

    render(<Network theme="light" />);
    fireEvent.click(await screen.findByRole('button', { name: /sincronizar/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('No se pudo sincronizar con el par');
    });
  });

  it('shows success only when the mesh sync result reports success', async () => {
    slskdnAPI.getSlskdnStats.mockResolvedValueOnce({
      capabilities: { features: [], version: 'slskdN' },
      dht: {},
      hashDb: {},
      mesh: { connectedPeerCount: 1, warnings: [] },
      meshPeers: [{ username: 'mesh-peer' }],
      swarmJobs: [],
    });
    slskdnAPI.triggerMeshSync.mockResolvedValueOnce({ success: true });

    render(<Network theme="light" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Sync' }));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Sync initiated with mesh-peer');
    });
  });

  it('explains zero-node DHT when LAN-only mode disables public bootstrap', async () => {
    slskdnAPI.getSlskdnStats.mockResolvedValueOnce({
      backfill: {
        completedToday: 0,
        discoveryRate: 0,
        isActive: false,
        pendingCount: 0,
      },
      capabilities: { features: [], version: 'slskdn' },
      dht: {
        dhtNodeCount: 0,
        isEnabled: true,
        isLanOnly: true,
        isDhtRunning: false,
      },
      hashDb: { currentSeqId: 0, totalEntries: 0 },
      mesh: {
        connectedPeerCount: 0,
        warnings: [],
      },
      swarmJobs: [],
    });

    render(<Network theme="light" />);

    await waitFor(() => {
      expect(screen.getByText('LAN-only DHT is isolated')).toBeInTheDocument();
    });

    expect(screen.queryByText('Connectivity diagnostics')).not.toBeInTheDocument();
    expect(
      screen.getByText(/intentionally disables the public BitTorrent DHT engine/i),
    ).toBeInTheDocument();
  });

  it('dismisses the public DHT notice with the keyboard and remembers the choice', async () => {
    const user = userEvent.setup();
    render(<Network theme="light" />);

    await waitFor(() => {
      expect(
        screen.getByText('Public DHT exposure notice'),
      ).toBeInTheDocument();
    });

    const dismissButton = screen.getByRole('button', {
      name: 'Dismiss public DHT exposure notice',
    });
    dismissButton.focus();
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(
        screen.queryByText('Public DHT exposure notice'),
      ).not.toBeInTheDocument();
    });

    expect(
      window.localStorage.getItem('slskdn:ui:dht-public-exposure:consent-v1'),
    ).toBe('acknowledged');
  });

  it('does not show the DHT exposure notice if already acknowledged', async () => {
    window.localStorage.setItem('slskdn:ui:dht-public-exposure:consent-v1', 'acknowledged');

    render(<Network theme="light" />);

    await waitFor(() => {
      expect(
        screen.queryByText('Public DHT exposure notice'),
      ).not.toBeInTheDocument();
    });
  });

  it('does not show connectivity diagnostics when DHT status has peers', async () => {
    window.localStorage.setItem('slskdn:ui:dht-public-exposure:consent-v1', 'acknowledged');
    slskdnAPI.getSlskdnStats.mockResolvedValueOnce({
      backfill: {
        completedToday: 0,
        discoveryRate: 0,
        isActive: false,
        pendingCount: 0,
      },
      capabilities: { features: [], version: 'slskdn' },
      dht: {
        activeMeshConnections: 1,
        dhtNodeCount: 155,
        discoveredPeerCount: 37,
        isEnabled: true,
        isLanOnly: false,
        isDhtRunning: true,
      },
      hashDb: { currentSeqId: 0, totalEntries: 0 },
      mesh: {
        connectedPeerCount: 0,
        warnings: [],
      },
      swarmJobs: [],
    });

    render(<Network theme="light" />);

    await waitFor(() => {
      expect(screen.getByText('Mesh Sync Security')).toBeInTheDocument();
    });

    expect(screen.queryByText('Connectivity diagnostics')).not.toBeInTheDocument();
    expect(screen.getByText('Healthy')).toBeInTheDocument();
  });

  it('does not show the DHT exposure notice when DHT is LAN-only', async () => {
    slskdnAPI.getSlskdnStats.mockResolvedValueOnce({
      backfill: {
        completedToday: 0,
        discoveryRate: 0,
        isActive: false,
        pendingCount: 0,
      },
      capabilities: { features: [], version: 'slskdn' },
      dht: {
        dhtNodeCount: 3,
        isEnabled: true,
        isLanOnly: true,
        isDhtRunning: true,
      },
      hashDb: { currentSeqId: 0, totalEntries: 0 },
      mesh: {
        connectedPeerCount: 0,
        warnings: [],
      },
      swarmJobs: [],
    });

    render(<Network theme="light" />);

    await waitFor(() => {
      expect(screen.queryByText('Public DHT exposure notice')).not.toBeInTheDocument();
    });
  });

  it('does not show the DHT exposure notice when the backend reports lanOnly', async () => {
    slskdnAPI.getSlskdnStats.mockResolvedValueOnce({
      backfill: {
        completedToday: 0,
        discoveryRate: 0,
        isActive: false,
        pendingCount: 0,
      },
      capabilities: { features: [], version: 'slskdn' },
      dht: {
        dhtNodeCount: 3,
        isEnabled: true,
        lanOnly: true,
        isDhtRunning: true,
      },
      hashDb: { currentSeqId: 0, totalEntries: 0 },
      mesh: {
        connectedPeerCount: 0,
        warnings: [],
      },
      swarmJobs: [],
    });

    render(<Network theme="light" />);

    await waitFor(() => {
      expect(screen.queryByText('Public DHT exposure notice')).not.toBeInTheDocument();
    });
  });

  it('renders inverted statistics in dark theme', async () => {
    const { container } = render(<Network theme="dark" />);

    await waitFor(() => {
      expect(screen.getByText('Mesh Sync Security')).toBeInTheDocument();
    });

    expect(container.querySelector('.ui.inverted.statistics')).not.toBeNull();
  });

  it('loads the dashboard and peer lists through one combined request', async () => {
    slskdnAPI.getSlskdnStats.mockResolvedValueOnce({
      capabilities: { features: [], version: 'slskdn' },
      dht: {},
      discoveredPeers: [{ username: 'discovered-peer' }],
      hashDb: {},
      mesh: { warnings: [] },
      meshPeers: [{ username: 'mesh-peer' }],
      swarmJobs: [],
    });

    render(<Network theme="light" />);

    expect(await screen.findByText('mesh-peer')).toBeInTheDocument();
    expect(screen.getByText('discovered-peer')).toBeInTheDocument();
    expect(slskdnAPI.getSlskdnStats).toHaveBeenCalledWith({
      includePeers: true,
    });
    expect(slskdnAPI.getMeshPeers).not.toHaveBeenCalled();
    expect(slskdnAPI.getDiscoveredPeers).not.toHaveBeenCalled();
  });

  it('does not overlap slow dashboard polls', async () => {
    vi.useFakeTimers();
    let resolveStats;
    slskdnAPI.getSlskdnStats.mockReturnValue(
      new Promise((resolve) => {
        resolveStats = resolve;
      }),
    );

    render(<Network theme="light" />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });

    expect(slskdnAPI.getSlskdnStats).toHaveBeenCalledTimes(1);

    resolveStats({
      discoveredPeers: [],
      meshPeers: [],
    });
    await act(async () => {
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(10_000);
    });

    expect(slskdnAPI.getSlskdnStats).toHaveBeenCalledTimes(2);
  });

  it('pauses polling while the browser document is hidden', async () => {
    vi.useFakeTimers();
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: true,
    });

    render(<Network theme="light" />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(slskdnAPI.getSlskdnStats).not.toHaveBeenCalled();

    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false,
    });
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
      await Promise.resolve();
    });

    expect(slskdnAPI.getSlskdnStats).toHaveBeenCalledTimes(1);
  });
});
