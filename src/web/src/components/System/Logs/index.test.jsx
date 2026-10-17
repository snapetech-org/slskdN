import '@testing-library/jest-dom';
import Logs from './index';
import React from 'react';
import { createLogsHubConnection } from '../../../lib/hubFactory';
import { downloadLogFile, getLogFile, getLogFiles } from '../../../lib/logs';
import { downloadFile } from '../../../lib/util';
import { resetInterfaceLanguage, setInterfaceLanguage } from '../../../lib/interfaceLocale';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { stubLocaleCatalogFetch } from '../../../test/localeCatalogFetchMock';

vi.mock('../../../lib/hubFactory', () => ({
  createLogsHubConnection: vi.fn(),
}));

vi.mock('../../../lib/logs', () => ({
  downloadLogFile: vi.fn(),
  getLogFile: vi.fn(),
  getLogFiles: vi.fn(),
}));

vi.mock('../../../lib/util', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, downloadFile: vi.fn() };
});

const createHub = ({ start } = {}) => {
  const handlers = new Map();
  const lifecycle = {};

  return {
    emit: (event, ...args) => handlers.get(event)?.(...args),
    on: vi.fn((event, handler) => handlers.set(event, handler)),
    onclose: vi.fn((handler) => { lifecycle.close = handler; }),
    onreconnected: vi.fn((handler) => { lifecycle.reconnected = handler; }),
    onreconnecting: vi.fn((handler) => { lifecycle.reconnecting = handler; }),
    start: start || vi.fn().mockResolvedValue(undefined),
    stop: vi.fn().mockResolvedValue(undefined),
    trigger: (event, ...args) => lifecycle[event]?.(...args),
  };
};

const records = [
  {
    level: 'Information',
    message: 'An information record',
    timestamp: '2026-10-03T00:00:01Z',
  },
  {
    level: 'Warning',
    message: 'A warning record',
    timestamp: '2026-10-03T00:00:02Z',
  },
];

describe('System Logs', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(async () => {
    cleanup();
    await resetInterfaceLanguage();
    vi.unstubAllGlobals();
  });

  it('renders the server buffer newest-first and filters by severity', async () => {
    const hub = createHub();
    createLogsHubConnection.mockReturnValue(hub);
    const user = userEvent.setup();

    render(<Logs />);
    await screen.findByText('Showing 0 of 0 logs');
    act(() => hub.emit('buffer', records));

    expect(await screen.findByText('A warning record')).toBeInTheDocument();
    const rows = screen.getAllByRole('row');
    expect(rows[1]).toHaveTextContent('A warning record');
    expect(rows[2]).toHaveTextContent('An information record');

    const warningFilter = screen.getByRole('button', { name: 'Show warning logs' });
    expect(warningFilter).toHaveAttribute('aria-pressed', 'false');
    await user.click(warningFilter);

    expect(warningFilter).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('A warning record')).toBeInTheDocument();
    expect(screen.queryByText('An information record')).not.toBeInTheDocument();
    expect(screen.getByText('Showing 1 of 2 logs')).toBeInTheDocument();
  });

  it('explains the severity filter on keyboard focus', async () => {
    const hub = createHub();
    createLogsHubConnection.mockReturnValue(hub);
    render(<Logs />);

    const allFilter = screen.getByRole('button', { name: 'Show all severities' });
    allFilter.focus();

    expect(await screen.findByText(
      'Show every severity so you can inspect the full live log feed.',
    )).toBeVisible();
  });

  it('shows a retry action after startup fails and reconnects on activation', async () => {
    const firstHub = createHub({
      start: vi.fn().mockRejectedValueOnce(new Error('logs unavailable')),
    });
    const secondHub = createHub();
    createLogsHubConnection
      .mockReturnValueOnce(firstHub)
      .mockReturnValueOnce(secondHub);
    const user = userEvent.setup();

    render(<Logs />);

    expect(await screen.findByText('Unable to connect to live logs.')).toBeInTheDocument();
    const retry = screen.getByRole('button', { name: 'Retry live log connection' });
    expect(retry).toBeVisible();
    await user.click(retry);

    await waitFor(() => expect(createLogsHubConnection).toHaveBeenCalledTimes(2));
    expect(firstHub.stop).toHaveBeenCalledOnce();
    expect(await screen.findByText('Showing 0 of 0 logs')).toBeInTheDocument();
  });

  it('keeps buffered entries available while reconnecting', async () => {
    const hub = createHub();
    createLogsHubConnection.mockReturnValue(hub);
    render(<Logs />);
    await screen.findByText('Showing 0 of 0 logs');
    act(() => hub.emit('buffer', records));

    act(() => hub.trigger('reconnecting', new Error('network changed')));

    expect(screen.getByText('A warning record')).toBeInTheDocument();
    expect(screen.getByText('Reconnecting to live logs', { exact: true })).toBeInTheDocument();
    expect(screen.getByText(/Buffered entries remain available/u)).toBeInTheDocument();
  });

  it('stops the live hub and ignores later records when the page unmounts', async () => {
    const hub = createHub();
    createLogsHubConnection.mockReturnValue(hub);
    const { unmount } = render(<Logs />);

    unmount();

    await waitFor(() => expect(hub.stop).toHaveBeenCalledOnce());
    expect(() => hub.emit('log', records[0])).not.toThrow();
  });

  it('loads, previews, and downloads retained log files', async () => {
    const hub = createHub();
    const file = {
      lastModified: '2026-10-12T10:20:30Z',
      length: 1_024,
      name: 'slskd-20261012.log',
    };
    createLogsHubConnection.mockReturnValue(hub);
    getLogFiles.mockResolvedValue([file]);
    getLogFile.mockResolvedValue('server started');
    downloadLogFile.mockResolvedValue(new Blob(['server started']));
    const user = userEvent.setup();

    render(<Logs />);
    await user.click(screen.getByRole('button', { name: 'History' }));

    expect(await screen.findByText(file.name)).toBeInTheDocument();
    expect(getLogFiles).toHaveBeenCalledOnce();
    await user.click(screen.getByRole('button', { name: `View ${file.name}` }));
    expect(await screen.findByText('server started')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Close' }));

    await user.click(screen.getByRole('button', { name: `Download ${file.name}` }));
    await waitFor(() => expect(downloadLogFile).toHaveBeenCalledWith(file.name));
    expect(downloadFile).toHaveBeenCalledWith(expect.any(Blob), file.name, 'text/plain');
  });

  it('ignores a preview response after the preview closes', async () => {
    const hub = createHub();
    const file = { lastModified: '2026-10-12T10:20:30Z', length: 20, name: 'slskd-20261012.log' };
    let resolvePreview;
    createLogsHubConnection.mockReturnValue(hub);
    getLogFiles.mockResolvedValue([file]);
    getLogFile.mockImplementation(() => new Promise((resolve) => { resolvePreview = resolve; }));
    const user = userEvent.setup();

    render(<Logs />);
    await user.click(screen.getByRole('button', { name: 'History' }));
    await screen.findByText(file.name);
    await user.click(screen.getByRole('button', { name: `View ${file.name}` }));
    await user.click(await screen.findByRole('button', { name: 'Close' }));

    await act(async () => resolvePreview('late preview response'));

    expect(screen.queryByText('late preview response')).not.toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('localizes the accessible name of severity filters', async () => {
    stubLocaleCatalogFetch(vi);
    await setInterfaceLanguage('de');
    createLogsHubConnection.mockReturnValue(createHub());

    render(<Logs />);

    expect(await screen.findByRole('button', { name: 'Warnungsprotokolle anzeigen' }))
      .toBeInTheDocument();
  });
});
