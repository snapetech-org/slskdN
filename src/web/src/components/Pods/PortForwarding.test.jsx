// <copyright file="PortForwarding.test.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import '@testing-library/jest-dom';
import * as pods from '../../lib/pods';
import * as portForwarding from '../../lib/portForwarding';
import PortForwarding from './PortForwarding';
import { resetInterfaceLanguage, setInterfaceLanguage } from '../../lib/interfaceLocale';
import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { stubLocaleCatalogFetch } from '../../test/localeCatalogFetchMock';

vi.mock('../../lib/pods', () => ({
  get: vi.fn(),
  getMembers: vi.fn(),
  list: vi.fn(),
}));

vi.mock('../../lib/portForwarding', () => ({
  getAvailablePorts: vi.fn(),
  getForwardingStatus: vi.fn(),
  startForwarding: vi.fn(),
  stopForwarding: vi.fn(),
}));

const setDocumentHidden = (hidden) => {
  Object.defineProperty(document, 'hidden', {
    configurable: true,
    value: hidden,
  });
};

const forwarding = {
  activeConnections: 3,
  bytesForwarded: 12_288,
  destinationHost: 'service.internal',
  destinationPort: 443,
  isActive: true,
  localPort: 8_080,
  performance: {
    averageBytesPerConnection: 4_096,
    isHighThroughput: true,
  },
  podId: 'pod:test',
  serviceName: 'service',
  streamMappingEnabled: true,
};

describe('Pod port forwarding', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setDocumentHidden(false);
    pods.getMembers.mockResolvedValue([
      { peerId: 'peer-one' },
      { peerId: 'peer-two' },
      { peerId: 'peer-three' },
    ]);
    pods.list.mockResolvedValue([
      {
        capabilities: ['PrivateServiceGateway'],
        name: 'Test Pod',
        podId: 'pod:test',
        privateServicePolicy: { enabled: true },
      },
    ]);
    portForwarding.getAvailablePorts.mockResolvedValue({
      availablePortCount: 64_512,
      availablePorts: [1_024, 1_025],
      usedPortCount: 0,
    });
    portForwarding.getForwardingStatus.mockResolvedValue([forwarding]);
  });

  afterEach(async () => {
    cleanup();
    await resetInterfaceLanguage();
    vi.unstubAllGlobals();
    vi.useRealTimers();
    vi.restoreAllMocks();
    setDocumentHidden(false);
  });

  it('localizes port-range validation and hides unknown service error prose', async () => {
    stubLocaleCatalogFetch(vi);
    await setInterfaceLanguage('de');
    render(<PortForwarding />);

    await waitFor(() => {
      expect(portForwarding.getForwardingStatus).toHaveBeenCalledTimes(1);
    });
    fireEvent.click(screen.getByRole('button', { name: 'Weiterleitung hinzufügen' }));
    fireEvent.click(screen.getByRole('listbox', { name: 'Wählen Sie einen VPN-fähigen Pod aus' }));
    fireEvent.click(screen.getByRole('option', { name: 'Test Pod' }));
    const numberFields = screen.getAllByRole('spinbutton');
    fireEvent.change(numberFields[0], {
      target: { value: '1023' },
    });
    fireEvent.change(screen.getAllByRole('textbox')[0], {
      target: { value: 'service.internal' },
    });
    fireEvent.change(numberFields[1], {
      target: { value: '5432' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Weiterleitung starten' }));

    expect(await screen.findByText('Der lokale Port muss zwischen 1024 und 65535 liegen'))
      .toBeInTheDocument();
    expect(portForwarding.startForwarding).not.toHaveBeenCalled();
    portForwarding.startForwarding.mockRejectedValueOnce(
      new Error('Pod service says retry later.'),
    );
    fireEvent.change(numberFields[0], { target: { value: '8080' } });
    fireEvent.click(screen.getByRole('button', { name: 'Weiterleitung starten' }));
    expect(await screen.findByText('Die Anfrage ist fehlgeschlagen. Versuchen Sie es erneut.')).toBeInTheDocument();
    expect(portForwarding.startForwarding).toHaveBeenCalledOnce();
  });

  it('lazy-loads bounded secondary-tab data and renders only the active pane', async () => {
    render(<PortForwarding />);

    await waitFor(() => {
      expect(portForwarding.getForwardingStatus).toHaveBeenCalledTimes(1);
      expect(pods.list).toHaveBeenCalledTimes(1);
    });
    expect(portForwarding.getAvailablePorts).not.toHaveBeenCalled();
    expect(pods.getMembers).not.toHaveBeenCalled();
    expect(screen.queryByText('Available ports for forwarding (1024-65535):'))
      .not.toBeInTheDocument();
    expect(screen.queryByText('Total Connections')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Available Ports'));

    await waitFor(() => {
      expect(portForwarding.getAvailablePorts).toHaveBeenCalledWith(
        1_024,
        65_535,
        100,
      );
    });
    expect(screen.getByText('64512')).toBeInTheDocument();
    expect(screen.getByText(/\(\+64510 more\)/)).toBeInTheDocument();

    fireEvent.click(screen.getByText('VPN Pods'));

    await waitFor(() => {
      expect(pods.getMembers).toHaveBeenCalledWith('pod:test');
    });
    expect(screen.getByText('Total Members').previousElementSibling)
      .toHaveTextContent('3');
  });

  it('explains setup, stop, cancel, and dismiss actions before they run', async () => {
    render(<PortForwarding />);

    await waitFor(() => {
      expect(portForwarding.getForwardingStatus).toHaveBeenCalledTimes(1);
    });

    const stop = screen.getByRole('button', {
      name: 'Stop forwarding on local port 8080',
    });
    fireEvent.mouseEnter(stop);
    expect(
      await screen.findByText(
        'Stop forwarding on localhost:8080 and close this tunnel when you no longer need the local route.',
      ),
    ).toBeInTheDocument();
    expect(portForwarding.stopForwarding).not.toHaveBeenCalled();

    const addForwarding = screen.getByRole('button', { name: 'Add Forwarding' });
    fireEvent.mouseEnter(addForwarding);
    expect(
      await screen.findByText(
        'Open the setup form for a loopback-only port forward through a VPN-capable pod. Use it to reach a remote service from an app on this machine.',
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText('VPN Pod')).not.toBeInTheDocument();
    expect(portForwarding.startForwarding).not.toHaveBeenCalled();

    fireEvent.click(addForwarding);
    expect(await screen.findByText('VPN Pod')).toBeInTheDocument();
    const start = screen.getByRole('button', { name: 'Start Forwarding' });
    expect(start).toBeDisabled();
    fireEvent.mouseEnter(start.parentElement);
    expect(
      await screen.findByText(
        'Open a loopback-only listener on localhost:the selected port and route local app connections through this VPN pod to the remote service. Use this when you need local access to that service.',
      ),
    ).toBeInTheDocument();
    const cancel = screen.getByRole('button', { name: 'Cancel' });
    fireEvent.mouseEnter(cancel);
    expect(
      await screen.findByText(
        'Close this setup form without starting the port forward.',
      ),
    ).toBeInTheDocument();
    fireEvent.click(cancel);
    expect(portForwarding.startForwarding).not.toHaveBeenCalled();

    fireEvent.click(stop);
    expect(
      await screen.findByText('Successfully stopped forwarding on port 8080'),
    ).toBeInTheDocument();
    const dismiss = screen.getByRole('button', { name: 'Dismiss' });
    fireEvent.mouseEnter(dismiss);
    expect(
      await screen.findByText(
        'Dismiss this success message. It does not change forwarding or configuration.',
      ),
    ).toBeInTheDocument();
    expect(portForwarding.stopForwarding).toHaveBeenCalledTimes(1);
  });

  it('renders real forwarding statistics without a synthetic stats timer', async () => {
    render(<PortForwarding />);
    await waitFor(() => {
      expect(portForwarding.getForwardingStatus).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(screen.getByText('Tunnel Statistics'));

    expect(screen.getByText('Total Connections')).toBeInTheDocument();
    expect(screen.getByText('12.0 KB')).toBeInTheDocument();
    expect(screen.getByText('4.0 KB')).toBeInTheDocument();
    expect(screen.getByText('High')).toBeInTheDocument();
  });

  it('defers initial hydration until a hidden document becomes visible', async () => {
    vi.useFakeTimers();
    setDocumentHidden(true);

    render(<PortForwarding />);
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(pods.list).not.toHaveBeenCalled();
    expect(portForwarding.getForwardingStatus).not.toHaveBeenCalled();

    await act(async () => {
      setDocumentHidden(false);
      document.dispatchEvent(new Event('visibilitychange'));
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(pods.list).toHaveBeenCalledTimes(1);
    expect(portForwarding.getForwardingStatus).toHaveBeenCalledTimes(1);
  });

  it('retains the last successful status when a poll fails', async () => {
    vi.useFakeTimers();
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    portForwarding.getForwardingStatus
      .mockResolvedValueOnce([forwarding])
      .mockRejectedValueOnce(new Error('temporary failure'));

    render(<PortForwarding />);
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(screen.getByText('localhost:8080')).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    expect(portForwarding.getForwardingStatus).toHaveBeenCalledTimes(2);
    expect(screen.getByText('localhost:8080')).toBeInTheDocument();
    consoleError.mockRestore();
  });

  it('rejects overlapping status polls and suspends them while hidden', async () => {
    vi.useFakeTimers();
    let resolveStatus;
    portForwarding.getForwardingStatus.mockReturnValue(
      new Promise((resolve) => {
        resolveStatus = resolve;
      }),
    );

    render(<PortForwarding />);
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(portForwarding.getForwardingStatus).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveStatus([]);
      await Promise.resolve();
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(10_000);
    });
    expect(portForwarding.getForwardingStatus).toHaveBeenCalledTimes(2);

    await act(async () => {
      setDocumentHidden(true);
      document.dispatchEvent(new Event('visibilitychange'));
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(portForwarding.getForwardingStatus).toHaveBeenCalledTimes(2);

    await act(async () => {
      setDocumentHidden(false);
      document.dispatchEvent(new Event('visibilitychange'));
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(portForwarding.getForwardingStatus).toHaveBeenCalledTimes(3);
  });
});
