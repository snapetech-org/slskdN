import '@testing-library/jest-dom';
import Info from './index';
import React from 'react';
import YAML from 'yaml';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';

const { getVersion, restart, shutdown } = vi.hoisted(() => ({
  getVersion: vi.fn(),
  restart: vi.fn(),
  shutdown: vi.fn(),
}));

vi.mock('../../../lib/application', () => ({
  getVersion,
  restart,
  shutdown,
}));

vi.mock('../../Shared', () => ({
  CodeEditor: ({ value }) => <pre data-testid="application-state">{value}</pre>,
  LoaderSegment: () => <div>Loading application state</div>,
  ShrinkableButton: ({ children, disabled, onClick, tooltip }) => (
    <button disabled={disabled} onClick={onClick} title={tooltip}>
      {children}
    </button>
  ),
  Switch: ({ children, loading }) => children || loading,
}));

describe('System Info', () => {
  beforeEach(() => vi.clearAllMocks());

  it('leads with a readable overview and puts the raw state behind an advanced disclosure', async () => {
    render(
      <Info
        options={{}}
        state={{
          pendingRestart: true,
          server: { isConnected: true },
          shares: { scanPending: false },
          user: { username: 'fixture-user' },
          version: { current: '1.2.3' },
        }}
        theme="dark"
      />,
    );

    expect(screen.getByTestId('system-overview')).toHaveTextContent('Connected');
    expect(screen.getByTestId('system-overview')).toHaveTextContent('fixture-user');
    expect(screen.getByTestId('system-overview')).toHaveTextContent('Restart required');
    expect(screen.getByTestId('application-state')).not.toBeVisible();

    fireEvent.click(screen.getByText('Application state (advanced)'));
    await waitFor(() => {
      expect(screen.getByTestId('application-state')).toHaveTextContent('pendingRestart: true');
    });
  });

  it('explains update and privilege actions', async () => {
    render(<Info options={{}} state={{ user: { username: 'fixture-user' } }} theme="light" />);

    const checkForUpdates = await screen.findByRole('button', { name: 'Check for Updates' });
    const getPrivileges = screen.getByRole('button', { name: 'Get Privileges' });
    expect(checkForUpdates).toHaveAttribute(
      'title',
      'Check GitHub for the latest slskdN release.',
    );
    expect(getPrivileges).toHaveAttribute(
      'title',
      'Review Soulseek privilege options for this account.',
    );

    fireEvent.click(checkForUpdates);
    expect(getVersion).toHaveBeenCalledWith({ forceCheck: true });
  });

  it('cancels pending state serialization when the page unmounts', () => {
    vi.useFakeTimers();
    const stringify = vi.spyOn(YAML, 'stringify');
    const setTimeoutSpy = vi.spyOn(window, 'setTimeout');
    const clearTimeoutSpy = vi.spyOn(window, 'clearTimeout');
    const state = { version: { current: '1.2.3' } };

    try {
      const { unmount } = render(
        <Info options={{}} state={state} theme="light" />,
      );
      const timerIndex = setTimeoutSpy.mock.calls.findIndex(([, delay]) => delay === 250);
      expect(timerIndex).not.toBe(-1);
      const serializationTimer = setTimeoutSpy.mock.results[timerIndex].value;

      unmount();
      expect(clearTimeoutSpy).toHaveBeenCalledWith(serializationTimer);
      act(() => vi.advanceTimersByTime(250));

      expect(stringify.mock.calls.some(([value]) => value === state)).toBe(false);
    } finally {
      stringify.mockRestore();
      setTimeoutSpy.mockRestore();
      clearTimeoutSpy.mockRestore();
      vi.useRealTimers();
    }
  });

  it.each([
    ['Restart', restart],
    ['Shut Down', shutdown],
  ])('requires confirmation before %s', async (actionLabel, action) => {
    render(<Info options={{}} state={{}} theme="light" />);

    const trigger = await screen.findByRole('button', { name: actionLabel });
    expect(trigger.getAttribute('title')?.toLocaleLowerCase()).toContain(
      actionLabel.toLocaleLowerCase(),
    );
    fireEvent.click(trigger);

    const prompt = actionLabel === 'Restart'
      ? 'Restarting briefly interrupts the web app and Soulseek connections.'
      : "Shutting down stops the application. You'll need to start it manually to use it again.";
    const modal = screen.getByText(prompt).closest('.ui.modal');
    expect(modal).toBeInTheDocument();

    fireEvent.click(within(modal).getByRole('button', { name: 'Cancel' }));
    expect(action).not.toHaveBeenCalled();

    fireEvent.click(trigger);
    const confirmModal = screen.getByText(prompt).closest('.ui.modal');
    fireEvent.click(within(confirmModal).getByRole('button', { name: actionLabel }));
    expect(action).toHaveBeenCalledTimes(1);
  });
});
