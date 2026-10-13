import * as rooms from '../../lib/rooms';
import RoomSession from './RoomSession';
import { act, fireEvent, render, screen } from '@testing-library/react';
import React from 'react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../lib/rooms', () => ({
  getMessages: vi.fn(),
  getUsers: vi.fn(),
  sendMessage: vi.fn(),
}));

vi.mock('../Shared/UserCard', () => ({
  default: ({ children }) => <span>{children}</span>,
}));

const setDocumentHidden = (hidden) => {
  Object.defineProperty(document, 'hidden', {
    configurable: true,
    value: hidden,
  });
};

describe('RoomSession', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    setDocumentHidden(false);
    rooms.getMessages.mockResolvedValue([]);
    rooms.getUsers.mockResolvedValue([]);
  });

  afterEach(() => {
    vi.useRealTimers();
    setDocumentHidden(false);
  });

  it('renders inactive rooms as a lightweight shell without polling room data', () => {
    render(
      <RoomSession
        active={false}
        roomName="slskdn"
      />,
    );

    expect(screen.getByText('slskdn')).toBeInTheDocument();
    expect(rooms.getMessages).not.toHaveBeenCalled();
    expect(rooms.getUsers).not.toHaveBeenCalled();
  });

  it('does not focus the composer when room message text is clicked', async () => {
    const roomSessionRef = React.createRef();
    rooms.getMessages.mockResolvedValue([
      {
        id: 'selectable-room-message',
        message: 'A message worth copying',
        timestamp: '2026-10-13T12:00:00.000Z',
        username: 'peer',
      },
    ]);
    render(
      <RoomSession
        active
        ref={roomSessionRef}
        roomName="slskdn"
      />,
    );

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    const composer = screen.getByRole('textbox');
    expect(composer).not.toHaveFocus();
    const focusInput = vi.spyOn(roomSessionRef.current, 'focusInput');

    fireEvent.click(screen.getByText('A message worth copying'));

    expect(focusInput).not.toHaveBeenCalled();
  });

  it('explains the server leave action before sending it', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const onLeaveRoom = vi.fn();
    render(
      <RoomSession
        active={false}
        onLeaveRoom={onLeaveRoom}
        roomName="slskdn"
      />,
    );

    const leave = screen.getByRole('button', { name: 'Leave slskdn' });
    await user.hover(leave);
    expect(await screen.findByText(/Send a leave request for slskdn to the Soulseek server/))
      .toBeInTheDocument();
    expect(onLeaveRoom).not.toHaveBeenCalled();
  });

  it('polls messages and users on separate cadences', async () => {
    render(
      <RoomSession
        active
        roomName="slskdn"
      />,
    );

    await act(async () => {
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(10_000);
    });

    expect(rooms.getMessages).toHaveBeenCalledTimes(6);
    expect(rooms.getUsers).toHaveBeenCalledTimes(2);
  });

  it('stops all polling while hidden and refreshes immediately when visible', async () => {
    setDocumentHidden(true);
    render(
      <RoomSession
        active
        roomName="slskdn"
      />,
    );

    expect(rooms.getMessages).not.toHaveBeenCalled();
    expect(rooms.getUsers).not.toHaveBeenCalled();

    await act(async () => {
      setDocumentHidden(false);
      document.dispatchEvent(new Event('visibilitychange'));
      await Promise.resolve();
    });

    expect(rooms.getMessages).toHaveBeenCalledTimes(1);
    expect(rooms.getUsers).toHaveBeenCalledTimes(1);

    await act(async () => {
      setDocumentHidden(true);
      document.dispatchEvent(new Event('visibilitychange'));
      await vi.advanceTimersByTimeAsync(20_000);
    });

    expect(rooms.getMessages).toHaveBeenCalledTimes(1);
    expect(rooms.getUsers).toHaveBeenCalledTimes(1);
  });

  it('does not overlap slow message refreshes', async () => {
    let resolveMessages;
    rooms.getMessages.mockImplementation(
      () => new Promise((resolve) => {
        resolveMessages = resolve;
      }),
    );
    render(
      <RoomSession
        active
        roomName="slskdn"
      />,
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(6_000);
    });
    expect(rooms.getMessages).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveMessages([]);
      await Promise.resolve();
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(2_000);
    });
    expect(rooms.getMessages).toHaveBeenCalledTimes(2);
  });

  it('merges overlapping message deltas and advances the cursor', async () => {
    const first = {
      id: 'room-message-1',
      message: 'first',
      timestamp: '2026-07-15T12:00:00.100Z',
      username: 'friend',
    };
    const second = {
      id: 'room-message-2',
      message: 'second',
      timestamp: '2026-07-15T12:00:00.200Z',
      username: 'friend',
    };
    const third = {
      id: 'room-message-3',
      message: 'third',
      timestamp: '2026-07-15T12:00:00.300Z',
      username: 'friend',
    };
    rooms.getMessages
      .mockResolvedValueOnce([first, second])
      .mockResolvedValueOnce([second, third]);

    render(
      <RoomSession
        active
        roomName="slskdn"
      />,
    );
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(rooms.getMessages).toHaveBeenNthCalledWith(1, {
      roomName: 'slskdn',
      since: null,
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_000);
    });

    expect(rooms.getMessages).toHaveBeenNthCalledWith(2, {
      roomName: 'slskdn',
      since: Date.parse(second.timestamp) - 1,
    });
    expect(screen.getByText('first')).toBeInTheDocument();
    expect(screen.getByText('second')).toBeInTheDocument();
    expect(screen.getByText('third')).toBeInTheDocument();
  });
});
