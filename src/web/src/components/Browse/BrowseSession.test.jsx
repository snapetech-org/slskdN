import * as users from '../../lib/users';
import BrowseSession from './BrowseSession';
import { act, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import userEvent from '@testing-library/user-event';

vi.mock('../../lib/users', () => ({
  browse: vi.fn(),
  getBrowseStatus: vi.fn(),
}));

vi.mock('../../lib/userNotes', () => ({
  getNote: vi.fn(() => Promise.reject(new Error('no note'))),
}));

vi.mock('../../lib/transfers', () => ({
  download: vi.fn(),
}));

vi.mock('../Shared/UserCard', () => ({
  default: ({ children }) => <span>{children}</span>,
}));

vi.mock('../Users/UserNoteModal', () => ({
  default: () => null,
}));

const setDocumentHidden = (hidden) => {
  Object.defineProperty(document, 'hidden', {
    configurable: true,
    value: hidden,
  });
};

describe('BrowseSession', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    setDocumentHidden(false);
    users.getBrowseStatus.mockRejectedValue({ response: { status: 404 } });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    setDocumentHidden(false);
  });

  it('labels the browse action for assistive technology', () => {
    render(<BrowseSession />);

    expect(
      screen.getByRole('button', { name: 'Browse user files' }),
    ).toBeInTheDocument();
  });

  it('shows a localized fallback for a browse failure', async () => {
    users.browse.mockRejectedValue({
      response: {
        data: 'Unable to browse user; the remote peer is unavailable',
        status: 503,
      },
    });

    render(<BrowseSession username="alice" />);

    expect(
      await screen.findByText(
        'Failed to browse alice: Browse failed',
      ),
    ).toBeInTheDocument();

    await waitFor(() => expect(users.browse).toHaveBeenCalledWith({ username: 'alice' }));
  });

  it('explains peer-list refresh without sending another browse request on hover', async () => {
    const user = userEvent.setup();
    const sessionRef = React.createRef();
    render(<BrowseSession ref={sessionRef} />);
    await act(async () => {
      sessionRef.current.setState({
        browseState: 'complete',
        info: {
          directories: 1,
          files: 1,
          lockedDirectories: 0,
          lockedFiles: 0,
        },
        tree: [{ children: [], fileCount: 1, locked: false, name: 'Shared' }],
        username: 'alice',
      });
    });

    const refresh = await screen.findByRole('button', {
      name: "Refresh alice's shared files",
    });
    await user.hover(refresh);

    expect(await screen.findByText(/Request alice's current shared file list from Soulseek/))
      .toBeInTheDocument();
    expect(users.browse).not.toHaveBeenCalled();
  });

  it('polls once per second, rejects overlap, and catches up after visibility resumes', async () => {
    vi.useFakeTimers();
    setDocumentHidden(true);
    users.browse.mockReturnValue(new Promise(() => {}));

    let resolveStatus;
    users.getBrowseStatus
      .mockReturnValueOnce(new Promise((resolve) => {
        resolveStatus = resolve;
      }))
      .mockResolvedValue({
        data: {
          bytesRemaining: 50,
          bytesTransferred: 50,
          percentComplete: 50,
          size: 100,
        },
      });

    render(<BrowseSession username="alice" />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_050);
    });
    expect(users.browse).toHaveBeenCalledTimes(1);
    expect(users.getBrowseStatus).not.toHaveBeenCalled();

    await act(async () => {
      setDocumentHidden(false);
      document.dispatchEvent(new Event('visibilitychange'));
      await vi.advanceTimersByTimeAsync(3_000);
    });
    expect(users.getBrowseStatus).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveStatus({
        data: {
          bytesRemaining: 50,
          bytesTransferred: 50,
          percentComplete: 50,
          size: 100,
        },
      });
      await Promise.resolve();
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(2_000);
    });
    expect(users.getBrowseStatus).toHaveBeenCalledTimes(3);
  });

  it('suppresses state updates when browse progress is unchanged', async () => {
    const status = {
      bytesRemaining: 50,
      bytesTransferred: 50,
      percentComplete: 50,
      size: 100,
    };
    users.getBrowseStatus.mockResolvedValue({ data: { ...status } });

    const session = new BrowseSession({});
    session.browseGeneration = 1;
    session.mounted = true;
    session.state = {
      browseState: 'pending',
      browseStatus: status,
      username: 'alice',
    };
    session.setState = vi.fn();

    await session.fetchStatus();

    expect(users.getBrowseStatus).toHaveBeenCalledTimes(1);
    const update = session.setState.mock.calls[0][0](session.state);
    expect(update).toBeNull();
  });

  it('rejects status responses from an obsolete browse generation', async () => {
    let resolveStatus;
    users.getBrowseStatus.mockReturnValue(new Promise((resolve) => {
      resolveStatus = resolve;
    }));

    const session = new BrowseSession({});
    session.browseGeneration = 1;
    session.mounted = true;
    session.state = {
      browseState: 'pending',
      browseStatus: 0,
      username: 'alice',
    };
    session.setState = vi.fn();

    const request = session.fetchStatus();
    session.browseGeneration = 2;
    session.state = { ...session.state, username: 'bob' };
    resolveStatus({
      data: {
        bytesRemaining: 0,
        bytesTransferred: 100,
        percentComplete: 100,
        size: 100,
      },
    });
    await request;

    expect(session.setState).not.toHaveBeenCalled();
  });
});
