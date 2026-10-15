import '@testing-library/jest-dom';
import * as chat from '../../lib/chat';
import Messaging from './Messaging';
import * as pods from '../../lib/pods';
import React from 'react';
import * as rooms from '../../lib/rooms';
import * as slskdn from '../../lib/slskdn';
import { MemoryRouter } from 'react-router-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../Player/PodListenAlongPanel', () => ({ default: () => null }));

vi.mock('../../lib/chat', () => ({
  acknowledge: vi.fn(),
  get: vi.fn(),
  getAll: vi.fn(),
  remove: vi.fn(),
  send: vi.fn(),
  sendBatch: vi.fn(),
}));

vi.mock('../../lib/pods', () => ({
  create: vi.fn(),
  discoverAll: vi.fn(),
  get: vi.fn(),
  getMembers: vi.fn(),
  getMessages: vi.fn(),
  leave: vi.fn(),
  list: vi.fn(),
  sendMessage: vi.fn(),
}));

vi.mock('../../lib/rooms', () => ({
  getAvailable: vi.fn(),
  getJoined: vi.fn(),
  getMessages: vi.fn(),
  getUsers: vi.fn(),
  join: vi.fn(),
  leave: vi.fn(),
  sendMessage: vi.fn(),
}));

vi.mock('../../lib/slskdn', () => ({
  getCapabilities: vi.fn(),
}));

const renderMessaging = (props = {}) =>
  render(
    <MemoryRouter>
      <Messaging state={{ user: { username: 'me' } }} {...props} />
    </MemoryRouter>,
  );

describe('Messaging', () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.useRealTimers();
    vi.clearAllMocks();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    chat.get.mockResolvedValue({ messages: [] });
    chat.getAll.mockResolvedValue([]);
    chat.remove.mockResolvedValue({});
    chat.send.mockResolvedValue({});
    pods.getMembers.mockResolvedValue([]);
    pods.getMessages.mockResolvedValue([]);
    pods.leave.mockResolvedValue({});
    pods.list.mockResolvedValue([]);
    pods.create.mockResolvedValue({});
    pods.discoverAll.mockResolvedValue([]);
    rooms.getAvailable.mockResolvedValue([]);
    rooms.getJoined.mockResolvedValue([]);
    rooms.getMessages.mockResolvedValue([]);
    rooms.getUsers.mockResolvedValue([]);
    rooms.join.mockResolvedValue({});
    rooms.leave.mockResolvedValue({});
    rooms.sendMessage.mockResolvedValue({});
    slskdn.getCapabilities.mockResolvedValue({ featureGates: {} });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders the V2 workspace without requiring the legacy feature flag', async () => {
    chat.getAll.mockResolvedValue([{ username: 'friend' }]);

    renderMessaging();

    expect(await screen.findByText('Channels')).toBeInTheDocument();
    expect(screen.getByText('Soulseek · DMs')).toBeInTheDocument();
    expect(screen.queryByText('Workspace')).not.toBeInTheDocument();
    expect(window.localStorage.getItem('slskd-messaging-v2')).toBeNull();
  });

  it('opens a direct-message tab from the V2 channel tree', async () => {
    chat.getAll.mockResolvedValue([{ username: 'friend' }]);
    chat.get.mockResolvedValue({
      messages: [
        {
          direction: 'In',
          message: 'hello from friend',
          timestamp: 1_700_000_000_000,
          username: 'friend',
        },
      ],
    });

    renderMessaging();

    fireEvent.click(await screen.findByTitle('@friend'));

    expect(await screen.findByText('@friend')).toBeInTheDocument();
    expect(await screen.findByText('hello from friend')).toBeInTheDocument();
  });

  it('joins a room from the V2 room search form', async () => {
    renderMessaging();

    fireEvent.click(await screen.findByLabelText('Join or create a room'));
    fireEvent.change(screen.getByLabelText('Search or create Soulseek room'), {
      target: { value: 'slskdn' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Join/Create room' }));

    await waitFor(() => {
      expect(rooms.join).toHaveBeenCalledWith({ roomName: 'slskdn' });
    });
  });

  it('filters available rooms instead of dumping the server room list', async () => {
    rooms.getAvailable.mockResolvedValue(['ambient', 'jazz', 'slskdn']);

    renderMessaging();

    fireEvent.click(await screen.findByLabelText('Join or create a room'));
    expect(screen.queryByTitle('ambient')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Search or create Soulseek room'), {
      target: { value: 'amb' },
    });
    fireEvent.click(await screen.findByRole('button', { name: 'Join ambient' }));

    await waitFor(() => {
      expect(rooms.join).toHaveBeenCalledWith({ roomName: 'ambient' });
    });
  });

  it('keeps room suggestions after a degraded directory refresh', async () => {
    rooms.getAvailable
      .mockResolvedValueOnce(['ambient', 'jazz', 'slskdn'])
      .mockResolvedValueOnce([]);

    renderMessaging();

    fireEvent.click(await screen.findByLabelText('Join or create a room'));
    fireEvent.change(screen.getByLabelText('Search or create Soulseek room'), {
      target: { value: 'amb' },
    });
    expect(await screen.findByRole('button', { name: 'Join ambient' })).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('Refresh'));
    fireEvent.change(screen.getByLabelText('Search or create Soulseek room'), {
      target: { value: '' },
    });
    fireEvent.change(screen.getByLabelText('Search or create Soulseek room'), {
      target: { value: 'jaz' },
    });

    expect(await screen.findByRole('button', { name: 'Join jazz' })).toBeInTheDocument();
  });

  it('retries room directory loading when the first response is degraded', async () => {
    vi.useFakeTimers();
    rooms.getAvailable
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce(['ambient']);

    renderMessaging();

    fireEvent.click(await screen.findByLabelText('Join or create a room'));

    await waitFor(() => {
      expect(rooms.getAvailable).toHaveBeenCalledTimes(1);
    });

    await vi.advanceTimersByTimeAsync(1_500);

    await waitFor(() => {
      expect(rooms.getAvailable).toHaveBeenCalledTimes(2);
    });

    fireEvent.change(screen.getByLabelText('Search or create Soulseek room'), {
      target: { value: 'amb' },
    });

    expect(await screen.findByRole('button', { name: 'Join ambient' })).toBeInTheDocument();
  });

  it('suggests joined rooms from the room search form', async () => {
    rooms.getJoined.mockResolvedValue(['slskdn']);

    renderMessaging();

    fireEvent.click(await screen.findByLabelText('Join or create a room'));
    fireEvent.change(screen.getByLabelText('Search or create Soulseek room'), {
      target: { value: 'sls' },
    });
    fireEvent.click(await screen.findByRole('button', { name: 'Open slskdn' }));

    await waitFor(() => {
      expect(rooms.join).toHaveBeenCalledWith({ roomName: 'slskdn' });
    });
  });

  it('keeps the room picker open when join fails', async () => {
    rooms.join.mockRejectedValueOnce({
      response: {
        data: 'Soulseek is reconnecting; try again shortly.',
      },
    });

    renderMessaging();

    fireEvent.click(await screen.findByLabelText('Join or create a room'));
    fireEvent.change(screen.getByLabelText('Search or create Soulseek room'), {
      target: { value: 'slskdn' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Join/Create room' }));

    expect(await screen.findByText('Room join failed. Try again shortly.')).toBeInTheDocument();
    expect(screen.getByLabelText('Search or create Soulseek room')).toHaveValue('slskdn');
  });

  it('keeps pod direct channels hidden while showing pod room channels', async () => {
    pods.list.mockResolvedValue([
      {
        channels: [
          { channelId: 'dm', kind: 'Direct', name: 'dm' },
          { channelId: 'general', kind: 'Room', name: 'General' },
        ],
        name: 'Gold Star Club',
        podId: 'pod-1',
      },
    ]);
    pods.get.mockResolvedValue({
      channels: [
        { channelId: 'dm', kind: 'Direct', name: 'dm' },
        { channelId: 'general', kind: 'Room', name: 'General' },
      ],
      name: 'Gold Star Club',
      podId: 'pod-1',
    });

    renderMessaging();

    expect(await screen.findByText('Gold Star Club / General')).toBeInTheDocument();
    expect(screen.queryByText('Gold Star Club / dm')).not.toBeInTheDocument();
  });

  it('uses slash leave to call the active room leave action', async () => {
    rooms.getJoined.mockResolvedValue(['indie']);
    const user = userEvent.setup();

    renderMessaging({ initialKind: 'room' });

    expect(await screen.findByText('#indie')).toBeInTheDocument();
    expect(await screen.findByText('No messages yet in #indie.')).toBeInTheDocument();
    const composer = screen.getByLabelText('Message #indie');
    expect(composer).toBeEnabled();
    await user.type(composer, '/leave');
    expect(composer).toHaveValue('/leave');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(rooms.leave).toHaveBeenCalledWith({ roomName: 'indie' });
    });
  });
});
