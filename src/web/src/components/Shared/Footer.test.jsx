import '@testing-library/jest-dom';
import Footer from './Footer';
import React from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';

const { getBuild, getSlskdnStats, getSpeeds, isLoggedIn } = vi.hoisted(() => ({
  getBuild: vi.fn(),
  getSlskdnStats: vi.fn(),
  getSpeeds: vi.fn(),
  isLoggedIn: vi.fn(),
}));

vi.mock('../../lib/application', () => ({
  getBuild,
}));

vi.mock('../../lib/session', () => ({
  isLoggedIn,
}));

vi.mock('../../lib/slskdn', () => ({
  getSlskdnStats,
}));

vi.mock('../../lib/transfers', () => ({
  getSpeeds,
}));

describe('Footer', () => {
  beforeEach(() => {
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false,
    });
    isLoggedIn.mockReturnValue(true);
    getSlskdnStats.mockResolvedValue({
      backfill: { isActive: true },
      dht: { discoveredPeerCount: 23, dhtNodeCount: 12 },
      hashDb: { currentSeqId: 14638, totalEntries: 7_300 },
      mesh: { connectedPeerCount: 6, isSyncing: true },
      swarmJobs: [{ id: 'job-1' }],
      transport: {
        dht: 12,
        natType: 'FullCone',
        overlay: 3,
      },
    });
    getSpeeds.mockResolvedValue({
      mesh: 2_048,
      soulseek: 4_096,
      total: 6_144,
    });
    getBuild.mockResolvedValue({
      current: '0.0.0-slskdn.manual.test',
      full: '0.0.0-slskdn.manual.test (0.0.0-slskdn.manual.test)',
      isUpdateAvailable: false,
      latest: '0.0.0-slskdn.manual.test',
      latestTag: '0.0.0-slskdn.manual.test',
      latestUrl: 'https://github.com/snapetech-org/slskdN/releases/tag/test',
    });
    localStorage.setItem('slskdn-karma', '2');
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders slskdN network stats in the footer', async () => {
    render(<Footer />);

    await waitFor(() => {
      expect(screen.getByText('23 dht')).toBeInTheDocument();
    });

    expect(screen.getByText('6 mesh')).toBeInTheDocument();
    expect(screen.getByText('7.3K hashes')).toBeInTheDocument();
    expect(screen.getByText('seq:14638')).toBeInTheDocument();
    expect(screen.getByText('1 swarm')).toBeInTheDocument();
    expect(screen.getByText('backfill')).toBeInTheDocument();
    expect(screen.getByText('+2')).toBeInTheDocument();
  });

  it('polls speeds more frequently than aggregate stats', async () => {
    vi.useFakeTimers();
    render(<Footer />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(6_000);
    });

    expect(getSpeeds).toHaveBeenCalledTimes(4);
    expect(getSlskdnStats).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(4_000);
    });

    expect(getSpeeds).toHaveBeenCalledTimes(6);
    expect(getSlskdnStats).toHaveBeenCalledTimes(2);
  });

  it('does not overlap slow aggregate stats polls', async () => {
    vi.useFakeTimers();
    let resolveStats;
    getSlskdnStats.mockReturnValue(
      new Promise((resolve) => {
        resolveStats = resolve;
      }),
    );

    render(<Footer />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });

    expect(getSlskdnStats).toHaveBeenCalledTimes(1);

    resolveStats({});
    await act(async () => {
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(10_000);
    });

    expect(getSlskdnStats).toHaveBeenCalledTimes(2);
  });

  it('does not overlap slow transfer speed polls', async () => {
    vi.useFakeTimers();
    let resolveSpeeds;
    getSpeeds.mockReturnValue(
      new Promise((resolve) => {
        resolveSpeeds = resolve;
      }),
    );

    render(<Footer />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    expect(getSpeeds).toHaveBeenCalledTimes(1);

    resolveSpeeds({ mesh: 0, soulseek: 0, total: 0 });
    await act(async () => {
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(2_000);
    });
    expect(getSpeeds).toHaveBeenCalledTimes(2);
  });

  it('stops global polling while hidden and catches up on visibility', async () => {
    vi.useFakeTimers();
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: true,
    });

    render(<Footer />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(20_000);
    });
    expect(getSpeeds).not.toHaveBeenCalled();
    expect(getSlskdnStats).not.toHaveBeenCalled();

    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false,
    });
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
      await Promise.resolve();
    });
    expect(getSpeeds).toHaveBeenCalledTimes(1);
    expect(getSlskdnStats).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_000);
    });
    expect(getSpeeds).toHaveBeenCalledTimes(2);
    expect(getSlskdnStats).toHaveBeenCalledTimes(1);

    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: true,
    });
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
      await vi.advanceTimersByTimeAsync(20_000);
    });
    expect(getSpeeds).toHaveBeenCalledTimes(2);
    expect(getSlskdnStats).toHaveBeenCalledTimes(1);
  });

  it('shows only attribution when logged out — no build badge, donation links, or telemetry', async () => {
    isLoggedIn.mockReturnValue(false);
    getBuild.mockResolvedValue({
      current: '0.0.0-slskdn.manual.local',
      full: '0.0.0-slskdn.manual.local (0.0.0-slskdn.manual.local)',
      isUpdateAvailable: true,
      latest: '2026050500-slskdn.221',
      latestTag: 'build-main-2026050500-slskdn.221',
      latestUrl: 'https://github.com/snapetech-org/slskdN/releases/tag/build-main-2026050500-slskdn.221',
    });

    render(<Footer />);

    expect(await screen.findByText('slskdN')).toBeInTheDocument();
    expect(screen.getByText('slskd')).toBeInTheDocument();
    expect(screen.queryByText('0.0.0-slskdn.manual.local')).not.toBeInTheDocument();
    expect(screen.queryByText(/PayPal/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Ko-fi/)).not.toBeInTheDocument();
    expect(getSlskdnStats).not.toHaveBeenCalled();
    expect(getSpeeds).not.toHaveBeenCalled();
  });
});
