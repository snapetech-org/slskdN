import LibraryHealth from './index';
import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import * as libraryHealth from '../../../lib/libraryHealth';
import * as searches from '../../../lib/searches';

vi.mock('../../../lib/libraryHealth', () => ({
  createRemediationJob: vi.fn(),
  getDashboard: vi.fn(),
  getIssues: vi.fn(),
  getIssuesByArtist: vi.fn(),
  getIssuesByType: vi.fn(),
  getScanStatus: vi.fn(),
  getSummary: vi.fn(),
  startScan: vi.fn(),
  updateIssueStatus: vi.fn(),
}));

vi.mock('../../../lib/searches', () => ({
  createBatch: vi.fn(),
}));

vi.mock('semantic-ui-react', async () => {
  const actual = await vi.importActual('semantic-ui-react');
  const ReactModule = await import('react');
  const TestTab = ({ activeIndex = 0, onTabChange, panes = [] }) =>
    ReactModule.default.createElement(
      'div',
      null,
      ReactModule.default.createElement(
        'div',
        { role: 'tablist' },
        panes.map((pane, index) => ReactModule.default.createElement(
          'button',
          {
            'aria-selected': activeIndex === index,
            key: pane.menuItem.key,
            onClick: (event) => onTabChange(event, { activeIndex: index }),
            role: 'tab',
            type: 'button',
          },
          pane.menuItem.content,
        )),
      ),
      panes[activeIndex]?.render(),
    );
  TestTab.Pane = ({ children }) =>
    ReactModule.default.createElement('div', null, children);

  return {
    ...actual,
    Tab: TestTab,
  };
});

const setDocumentHidden = (hidden) => {
  Object.defineProperty(document, 'hidden', {
    configurable: true,
    value: hidden,
  });
};

const pathInput = () => screen.getByLabelText('Library path on the server');
const openAllIssues = () => fireEvent.click(screen.getByRole('tab', { name: 'All Issues' }));
const resultPathText = (label, path) => screen.findByText((_, element) =>
  element?.textContent?.trim() === `${label}${path}`);

describe('LibraryHealth', () => {
  beforeEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    setDocumentHidden(false);
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
    libraryHealth.startScan.mockResolvedValue({ data: { scanId: 'scan-1' } });
    libraryHealth.getScanStatus.mockResolvedValue({ data: { status: 'Completed' } });
    libraryHealth.getDashboard.mockResolvedValue({
      data: {
        summary: {
          issuesOpen: 1,
          issuesResolved: 2,
          totalIssues: 3,
        },
        issuesByType: [{ count: 1, type: 'SuspectedTranscode' }],
        issuesByArtist: [{ artist: 'Fixture Artist', count: 1 }],
        issues: [
          {
            album: 'Fixture Album',
            artist: 'Fixture Artist',
            canAutoFix: true,
            issueId: 'issue-1',
            reason: 'Fixture reason',
            severity: 'High',
            status: 'Detected',
            title: 'Fixture Track',
            type: 'SuspectedTranscode',
          },
        ],
      },
    });
    searches.createBatch.mockResolvedValue(1);
  });

  afterEach(() => {
    vi.useRealTimers();
    setDocumentHidden(false);
  });

  it('copies a read-only health report from loaded scan data', async () => {
    vi.useFakeTimers();
    render(<LibraryHealth />);

    fireEvent.change(pathInput(), {
      target: { value: '/fixture/music' },
    });
    fireEvent.click(screen.getByLabelText('Start a recursive Library Health scan for this path'));

    await vi.advanceTimersByTimeAsync(2_000);
    await waitFor(() => expect(libraryHealth.getDashboard).toHaveBeenCalledWith('/fixture/music', 10, 100));
    expect(libraryHealth.getSummary).not.toHaveBeenCalled();
    expect(libraryHealth.getIssuesByType).not.toHaveBeenCalled();
    expect(libraryHealth.getIssuesByArtist).not.toHaveBeenCalled();
    expect(libraryHealth.getIssues).not.toHaveBeenCalled();
    fireEvent.click(await screen.findByTestId('library-health-copy-report'));

    await waitFor(() => expect(screen.getByTestId('library-health-report-message')).toHaveTextContent(
      'Library Health report copied to the clipboard.',
    ));

    openAllIssues();
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select Fixture Artist — Fixture Track' }));
    fireEvent.click(screen.getByTestId('library-health-copy-action-plan'));

    await waitFor(() => expect(screen.getByTestId('library-health-report-message')).toHaveTextContent(
      'Library Health action plan copied to the clipboard.',
    ));

    fireEvent.click(screen.getByTestId('library-health-copy-safe-fix-manifest'));

    await waitFor(() => expect(screen.getByTestId('library-health-report-message')).toHaveTextContent(
      'Library Health safe-fix manifest copied to the clipboard.',
    ));

    fireEvent.click(screen.getByTestId('library-health-copy-search-seeds'));

    await waitFor(() => expect(screen.getByTestId('library-health-report-message')).toHaveTextContent(
      'Library Health replacement search seeds copied to the clipboard.',
    ));

    fireEvent.click(screen.getByTestId('library-health-copy-quarantine-packet'));

    await waitFor(() => expect(screen.getByTestId('library-health-report-message')).toHaveTextContent(
      'Library Health quarantine review packet copied to the clipboard.',
    ));
    expect(libraryHealth.createRemediationJob).not.toHaveBeenCalled();
  });

  it('runs bounded replacement searches and exposes quarantine review packet copies', async () => {
    vi.useFakeTimers();
    render(<LibraryHealth />);

    fireEvent.change(pathInput(), {
      target: { value: '/fixture/music' },
    });
    fireEvent.click(screen.getByLabelText('Start a recursive Library Health scan for this path'));

    await vi.advanceTimersByTimeAsync(2_000);
    openAllIssues();
    await screen.findByText('Fixture Track');
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select Fixture Artist — Fixture Track' }));
    await act(async () => {
      fireEvent.click(screen.getByTestId('library-health-run-replacement-searches'));
    });

    await waitFor(() => {
      expect(searches.createBatch).toHaveBeenCalledWith({
        queries: ['Fixture Artist Fixture Album Fixture Track'],
      });
    });
    expect(screen.getByTestId('library-health-report-message')).toHaveTextContent(
      'Started 1 bounded replacement search for selected Library Health issues.',
    );

    expect(screen.queryByTestId('library-health-send-quarantine-review')).not.toBeInTheDocument();
    expect(screen.getByTestId('library-health-copy-quarantine-packet')).toBeInTheDocument();
  });

  it('queues remediation jobs only for selected auto-fixable issue ids', async () => {
    vi.useFakeTimers();
    render(<LibraryHealth />);

    fireEvent.change(pathInput(), {
      target: { value: '/fixture/music' },
    });
    fireEvent.click(screen.getByLabelText('Start a recursive Library Health scan for this path'));

    await vi.advanceTimersByTimeAsync(2_000);
    openAllIssues();
    await screen.findByText('Fixture Track');
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select Fixture Artist — Fixture Track' }));
    await act(async () => {
      fireEvent.click(screen.getByTestId('library-health-fix-selected'));
    });

    await waitFor(() => {
      expect(libraryHealth.createRemediationJob).toHaveBeenCalledWith(['issue-1']);
    });
    expect(screen.getByTestId('library-health-report-message')).toHaveTextContent(
      'Queued remediation for 1 auto-fixable issue.',
    );
  });

  it('keeps keyboard focus in the path input while the controlled value changes', async () => {
    const user = userEvent.setup();
    render(<LibraryHealth />);

    const input = pathInput();
    await user.type(input, '/fixture/music');

    expect(input).toHaveValue('/fixture/music');
    expect(document.activeElement).toBe(input);
  });

  it('does not claim an unscanned library is healthy and keeps reports tied to loaded results', async () => {
    render(<LibraryHealth />);

    openAllIssues();
    expect(screen.getByText(/Load saved results or scan a library/)).toBeInTheDocument();
    expect(screen.queryByText('No issues detected')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'Overview' }));
    fireEvent.change(pathInput(), { target: { value: '/fixture/old-library' } });
    fireEvent.click(screen.getByLabelText('Load saved Library Health results for this path'));
    await resultPathText('Results for ', '/fixture/old-library');

    fireEvent.change(pathInput(), { target: { value: '/fixture/new-library' } });
    expect(screen.queryByText('Results for /fixture/old-library')).not.toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Load saved Library Health results for this path'));
    await resultPathText('Results for ', '/fixture/new-library');

    openAllIssues();
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select Fixture Artist — Fixture Track' }));
    fireEvent.click(screen.getByTestId('library-health-copy-action-plan'));

    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenLastCalledWith(
      expect.stringContaining('Library: /fixture/new-library'),
    ));
    expect(await resultPathText('Showing results for ', '/fixture/new-library')).toBeInTheDocument();
  });

  it('retries saved dashboard loading without starting another scan', async () => {
    libraryHealth.getDashboard
      .mockRejectedValueOnce(new Error('dashboard unavailable'));
    render(<LibraryHealth />);

    fireEvent.change(pathInput(), { target: { value: '/fixture/music' } });
    fireEvent.click(screen.getByLabelText('Load saved Library Health results for this path'));
    expect(await screen.findByText('Failed to load library health data')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Retry loading saved Library Health results'));

    await waitFor(() => expect(libraryHealth.getDashboard).toHaveBeenCalledTimes(2));
    expect(libraryHealth.startScan).not.toHaveBeenCalled();
    expect(await resultPathText('Results for ', '/fixture/music')).toBeInTheDocument();
  });

  it('shows the generated report when clipboard access fails', async () => {
    navigator.clipboard.writeText.mockRejectedValueOnce(new Error('clipboard denied'));
    render(<LibraryHealth />);

    fireEvent.change(pathInput(), { target: { value: '/fixture/music' } });
    fireEvent.click(screen.getByLabelText('Load saved Library Health results for this path'));
    await waitFor(() => expect(libraryHealth.getDashboard).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByTestId('library-health-copy-report'));

    const reportText = await screen.findByLabelText('Library Health report text to copy manually');
    expect(reportText.value).toContain('Library: /fixture/music');
    expect(screen.getByTestId('library-health-report-message')).toHaveTextContent(
      'Clipboard access failed. Select and copy the library health report below.',
    );
  });

  it('limits bulk remediation to 25 and keeps the remaining issues selected', async () => {
    vi.useFakeTimers();
    const issues = Array.from({ length: 30 }, (_, index) => ({
      artist: 'Fixture Artist',
      canAutoFix: true,
      issueId: `issue-${index + 1}`,
      reason: 'Fixture reason',
      severity: 'High',
      status: 'Detected',
      title: `Fixture Track ${index + 1}`,
      type: 'SuspectedTranscode',
    }));
    libraryHealth.getDashboard.mockResolvedValue({
      data: {
        summary: { issuesOpen: 30, issuesResolved: 0, totalIssues: 30 },
        issuesByType: [],
        issuesByArtist: [],
        issues,
      },
    });
    render(<LibraryHealth />);

    fireEvent.change(pathInput(), { target: { value: '/fixture/music' } });
    fireEvent.click(screen.getByLabelText('Start a recursive Library Health scan for this path'));
    await vi.advanceTimersByTimeAsync(2_000);
    openAllIssues();
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select all 30 loaded Library Health issues' }));

    expect(screen.getByTestId('library-health-fix-selected')).toHaveTextContent(
      'Queue fixes for 25 of 30 auto-fixable issues',
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId('library-health-fix-selected'));
    });

    expect(libraryHealth.createRemediationJob).toHaveBeenCalledWith(
      Array.from({ length: 25 }, (_, index) => `issue-${index + 1}`),
    );
    expect(screen.getByTestId('library-health-fix-selected')).toHaveTextContent(
      'Queue fixes for 5 auto-fixable issues',
    );
    expect(screen.getByText('5 issues selected')).toBeInTheDocument();
  });

  it('surfaces failed scans and refreshes saved results', async () => {
    vi.useFakeTimers();
    libraryHealth.getScanStatus.mockResolvedValue({
      data: {
        errorMessage: 'Directory access was denied',
        filesScanned: 3,
        issuesDetected: 1,
        status: 'Failed',
      },
    });
    render(<LibraryHealth />);

    fireEvent.change(pathInput(), { target: { value: '/fixture/music' } });
    fireEvent.click(screen.getByLabelText('Start a recursive Library Health scan for this path'));
    await vi.advanceTimersByTimeAsync(2_000);

    expect(screen.getByText('Directory access was denied')).toBeInTheDocument();
    await waitFor(() => expect(libraryHealth.getDashboard).toHaveBeenCalledWith('/fixture/music', 10, 100));
    expect(screen.queryByLabelText('Retry Library Health scan status checks')).not.toBeInTheDocument();
  });

  it('ignores malformed Library Health group and issue list payloads', async () => {
    vi.useFakeTimers();
    libraryHealth.getDashboard.mockResolvedValue({
      data: {
        summary: {},
        issuesByType: { type: 'SuspectedTranscode' },
        issuesByArtist: { artist: 'Fixture Artist' },
        issues: { issueId: 'issue-1', title: 'Fixture Track' },
      },
    });

    render(<LibraryHealth />);

    fireEvent.change(pathInput(), {
      target: { value: '/fixture/music' },
    });
    fireEvent.click(screen.getByLabelText('Start a recursive Library Health scan for this path'));

    await vi.advanceTimersByTimeAsync(2_000);
    await screen.findByTestId('library-health-copy-report');
    expect(screen.queryByText('Fixture Track')).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText('No issues detected').length).toBeGreaterThan(0));
  });

  it('does not poll when scan creation omits a scan id', async () => {
    vi.useFakeTimers();
    libraryHealth.startScan.mockResolvedValue({ data: {} });

    render(<LibraryHealth />);

    fireEvent.change(pathInput(), {
      target: { value: '/fixture/music' },
    });
    fireEvent.click(screen.getByLabelText('Start a recursive Library Health scan for this path'));

    expect(
      await screen.findAllByText(/Failed to start scan/),
    ).not.toHaveLength(0);
    expect(libraryHealth.getScanStatus).not.toHaveBeenCalled();
  });

  it('leaves the spectral transcode check off unless it is selected', async () => {
    render(<LibraryHealth />);

    fireEvent.change(pathInput(), {
      target: { value: '/fixture/music' },
    });
    fireEvent.click(screen.getByLabelText('Start a recursive Library Health scan for this path'));

    await waitFor(() => expect(libraryHealth.startScan).toHaveBeenCalledWith(
      '/fixture/music',
      { includeSpectralAnalysis: false },
    ));
  });

  it('requests the spectral transcode check when it is selected', async () => {
    render(<LibraryHealth />);

    fireEvent.change(pathInput(), {
      target: { value: '/fixture/music' },
    });
    fireEvent.click(screen.getByLabelText('Spectral transcode check (slower)'));
    fireEvent.click(screen.getByLabelText('Start a recursive Library Health scan for this path'));

    await waitFor(() => expect(libraryHealth.startScan).toHaveBeenCalledWith(
      '/fixture/music',
      { includeSpectralAnalysis: true },
    ));
  });

  it('cleans scan polling timers when unmounted', async () => {
    vi.useFakeTimers();
    const { unmount } = render(<LibraryHealth />);

    fireEvent.change(pathInput(), {
      target: { value: '/fixture/music' },
    });
    fireEvent.click(screen.getByLabelText('Start a recursive Library Health scan for this path'));

    await waitFor(() => expect(libraryHealth.startScan).toHaveBeenCalled());
    unmount();
    await vi.advanceTimersByTimeAsync(60_000);

    expect(libraryHealth.getScanStatus).not.toHaveBeenCalled();
    expect(libraryHealth.getDashboard).not.toHaveBeenCalledWith('/fixture/music', 10, 100);
  });

  it('stops scanning and surfaces polling failures', async () => {
    vi.useFakeTimers();
    libraryHealth.getScanStatus
      .mockRejectedValueOnce(new Error('poll failed'))
      .mockResolvedValue({ data: { status: 'Running' } });

    render(<LibraryHealth />);

    fireEvent.change(pathInput(), {
      target: { value: '/fixture/music' },
    });
    fireEvent.click(screen.getByLabelText('Start a recursive Library Health scan for this path'));

    await vi.advanceTimersByTimeAsync(2_000);

    await waitFor(() =>
      expect(screen.getAllByText('Failed to poll Library Health scan status').length).toBeGreaterThan(0),
    );
    await vi.advanceTimersByTimeAsync(2_000);
    expect(libraryHealth.getScanStatus).toHaveBeenCalledTimes(1);

    await act(async () => {
      fireEvent.click(screen.getByLabelText('Retry Library Health scan status checks'));
    });
    expect(libraryHealth.getScanStatus).toHaveBeenCalledTimes(2);
    expect(screen.getAllByText(/Scan in progress: 0 files checked/).length).toBeGreaterThan(0);
  });

  it('schedules the next status poll only after a slow request completes', async () => {
    vi.useFakeTimers();
    let resolveStatus;
    libraryHealth.getScanStatus
      .mockImplementationOnce(
        () => new Promise((resolve) => {
          resolveStatus = resolve;
        }),
      )
      .mockResolvedValue({ data: { status: 'Running' } });

    render(<LibraryHealth />);
    fireEvent.change(pathInput(), {
      target: { value: '/fixture/music' },
    });
    fireEvent.click(screen.getByLabelText('Start a recursive Library Health scan for this path'));

    await vi.advanceTimersByTimeAsync(2_000);
    expect(libraryHealth.getScanStatus).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(10_000);
    expect(libraryHealth.getScanStatus).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveStatus({ data: { status: 'Running' } });
      await Promise.resolve();
    });
    await vi.advanceTimersByTimeAsync(1_999);
    expect(libraryHealth.getScanStatus).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(libraryHealth.getScanStatus).toHaveBeenCalledTimes(2);
  });

  it('pauses while hidden without extending the scan polling deadline', async () => {
    vi.useFakeTimers();
    libraryHealth.getScanStatus.mockResolvedValue({ data: { status: 'Running' } });

    render(<LibraryHealth />);
    fireEvent.change(pathInput(), {
      target: { value: '/fixture/music' },
    });
    fireEvent.click(screen.getByLabelText('Start a recursive Library Health scan for this path'));
    await waitFor(() => expect(libraryHealth.startScan).toHaveBeenCalledTimes(1));

    await act(async () => {
      setDocumentHidden(true);
      document.dispatchEvent(new Event('visibilitychange'));
      await vi.advanceTimersByTimeAsync(60_000);
    });
    expect(libraryHealth.getScanStatus).not.toHaveBeenCalled();

    await act(async () => {
      setDocumentHidden(false);
      document.dispatchEvent(new Event('visibilitychange'));
      await Promise.resolve();
    });
    expect(libraryHealth.getScanStatus).not.toHaveBeenCalled();
    await waitFor(() => expect(libraryHealth.getDashboard).toHaveBeenCalledWith('/fixture/music', 10, 100));
    expect(screen.getByText(/Status checks paused after one minute/)).toBeInTheDocument();
    expect(screen.getByLabelText('Retry Library Health scan status checks')).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByLabelText('Retry Library Health scan status checks'));
    });
    expect(libraryHealth.getScanStatus).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('Start a recursive Library Health scan for this path')).toHaveTextContent('Scanning...');
  });
});
