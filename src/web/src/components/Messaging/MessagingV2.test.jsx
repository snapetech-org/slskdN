import '@testing-library/jest-dom';
import * as chat from '../../lib/chat';
import * as pods from '../../lib/pods';
import * as rooms from '../../lib/rooms';
import * as slskdn from '../../lib/slskdn';
import MessagingV2 from './MessagingV2';
import React from 'react';
import userEvent from '@testing-library/user-event';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../lib/chat', () => ({
  getAll: vi.fn(),
  remove: vi.fn(),
}));

vi.mock('../../lib/pods', () => ({
  create: vi.fn(),
  discoverAll: vi.fn(),
  get: vi.fn(),
  leave: vi.fn(),
  list: vi.fn(),
}));

vi.mock('../../lib/rooms', () => ({
  getAvailable: vi.fn(),
  getJoined: vi.fn(),
  getUsers: vi.fn(),
  join: vi.fn(),
  leave: vi.fn(),
}));

vi.mock('../../lib/slskdn', () => ({
  getCapabilities: vi.fn(),
}));

vi.mock('../../lib/humanChallengeAutoResponse', () => ({
  applyHumanChallengeAutoResponse: vi.fn(),
  canApplyHumanChallengeAutoResponse: vi.fn(() => false),
  getHumanChallengeAutoResponseEnabled: vi.fn(() => false),
  readStoredHumanChallengeAutoResponse: vi.fn(() => false),
  writeStoredHumanChallengeAutoResponse: vi.fn(),
}));

vi.mock('../Player/PodListenAlongPanel', () => ({
  default: ({ channelId, podId, user }) => (
    <div aria-label="Room playback" data-channel={channelId} data-pod={podId} data-user={user} role="region" />
  ),
}));

vi.mock('./CommandHelp', () => ({ default: () => null }));
vi.mock('./Composer', () => ({ default: () => null }));
vi.mock('./MessageStream', () => ({ default: () => null }));
vi.mock('./QuickSwitcher', () => ({ default: () => null }));
vi.mock('./UserPopover', () => ({ default: () => null }));

const savedPods = Array.from({ length: 10 }, (_, index) => ({
  channels: [
    {
      channelId: 'general',
      kind: 'General',
      name: 'General',
    },
  ],
  name: `Pod ${index + 1}`,
  podId: `pod:${String(index + 1).padStart(32, '0')}`,
}));

const setDocumentHidden = (hidden) => {
  Object.defineProperty(document, 'hidden', {
    configurable: true,
    value: hidden,
  });
};

const flushPromises = async () => {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
};

const renderMessaging = (props = {}) =>
  render(
    <MemoryRouter>
      <MessagingV2 {...props} state={{ user: { username: 'local-user' } }} />
    </MemoryRouter>,
  );

describe('MessagingV2 hydration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    setDocumentHidden(false);
    chat.getAll.mockResolvedValue([]);
    rooms.getAvailable.mockResolvedValue(['ambient']);
    rooms.getJoined.mockResolvedValue([]);
    rooms.getUsers.mockResolvedValue([]);
    pods.discoverAll.mockResolvedValue([]);
    pods.list.mockResolvedValue(savedPods);
    slskdn.getCapabilities.mockResolvedValue({
      featureGates: { pods: { enabled: true, status: 'Experimental' } },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    setDocumentHidden(false);
  });

  it('mounts room playback on the active pod channel and removes it for Soulseek chat', async () => {
    rooms.getJoined.mockResolvedValue(['ambient']);
    renderMessaging();
    fireEvent.click(await screen.findByText('Pod 1 / General'));
    const playback = await screen.findByRole('region', { name: 'Room playback' });
    expect(playback).toHaveAttribute('data-pod', savedPods[0].podId);
    expect(playback.closest('main')).toHaveClass('msgv2-view-with-playback');
    expect(playback).toHaveAttribute('data-channel', 'general');
    expect(playback).toHaveAttribute('data-user', 'local-user');
    fireEvent.click(screen.getByText('ambient'));
    await waitFor(() => expect(screen.queryByRole('region', { name: 'Room playback' })).not.toBeInTheDocument());
  });

  it('keeps DirectMessage channels out of the room playback surface even with a custom name', async () => {
    pods.list.mockResolvedValue([{ ...savedPods[0], channels: [{ channelId: 'notes', name: 'Private notes', kind: 'DirectMessage' }] }]);
    renderMessaging();
    await waitFor(() => expect(pods.list).toHaveBeenCalled());
    await flushPromises();
    expect(screen.queryByText('Pod 1 / Private notes')).not.toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Room playback' })).not.toBeInTheDocument();
    expect(screen.getByRole('main')).not.toHaveClass('msgv2-view-with-playback');
  });

  it('uses channel details from the pod list without per-pod detail requests', async () => {
    renderMessaging();

    await waitFor(() => {
      expect(screen.getByText('Pod 1 / General')).toBeInTheDocument();
    });

    expect(chat.getAll).toHaveBeenCalledTimes(1);
    expect(rooms.getJoined).toHaveBeenCalledTimes(1);
    expect(pods.list).toHaveBeenCalledTimes(1);
    expect(pods.discoverAll).toHaveBeenCalledTimes(1);
    expect(pods.get).not.toHaveBeenCalled();
  });

  it('explains network filters and disabled conversation actions on hover', async () => {
    const user = userEvent.setup();
    renderMessaging();

    const allNetworks = screen.getByRole('button', { name: 'All networks' });
    await user.hover(allNetworks);
    expect(await screen.findByText(/Show direct messages and rooms from all messaging networks/))
      .toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Start a direct message' }));
    const startDm = screen.getByRole('button', { name: 'DM' });
    expect(startDm).toBeDisabled();
    await user.hover(startDm.parentElement);
    expect(await screen.findByText(/Enter a name to enable this action/))
      .toBeInTheDocument();
    expect(chat.remove).not.toHaveBeenCalled();
  });

  it('keeps the tab close action separate, keyboard reachable, and scoped to the tab', async () => {
    const user = userEvent.setup();
    rooms.getJoined.mockResolvedValue(['ambient']);
    const { container } = renderMessaging();

    await user.click(await screen.findByRole('button', { name: '#ambient' }));
    const tabStrip = container.querySelector('.msgv2-tabs-strip');
    const tabs = within(tabStrip);
    const close = tabs.getByRole('button', { name: 'Close #ambient' });
    expect(close).toBeEnabled();
    expect(close).not.toHaveAttribute('tabindex', '-1');

    await user.hover(close);
    expect(await screen.findByText(/Close #ambient without closing the other message tabs/))
      .toBeInTheDocument();
    expect(tabs.getByRole('button', { name: '#ambient' })).toBeInTheDocument();
    expect(rooms.leave).not.toHaveBeenCalled();

    await user.click(close);
    expect(tabs.queryByRole('button', { name: '#ambient' })).not.toBeInTheDocument();
    expect(rooms.leave).not.toHaveBeenCalled();
  });

  it('keeps pod routes available with a clear state and skips pod APIs when the server gate is disabled', async () => {
    slskdn.getCapabilities.mockResolvedValue({
      featureGates: { pods: { enabled: false, status: 'Disabled' } },
    });

    renderMessaging({ initialKind: 'pod' });

    expect(await screen.findByText('Mesh Pods are disabled by server configuration.'))
      .toBeInTheDocument();
    expect(screen.getByText('feature.Pods')).toBeInTheDocument();
    expect(screen.getByText('Mesh Pods are disabled')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Mesh only' }))
      .not.toBeInTheDocument();
    expect(screen.queryByText('Mesh · Pod channels')).not.toBeInTheDocument();
    expect(pods.list).not.toHaveBeenCalled();
    expect(pods.discoverAll).not.toHaveBeenCalled();
  });

  it('polls messaging every ten seconds and pod metadata every sixty seconds', async () => {
    vi.useFakeTimers();
    renderMessaging();
    await flushPromises();

    expect(chat.getAll).toHaveBeenCalledTimes(1);
    expect(pods.list).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(59_999);
    });

    expect(chat.getAll).toHaveBeenCalledTimes(6);
    expect(rooms.getJoined).toHaveBeenCalledTimes(6);
    expect(pods.list).toHaveBeenCalledTimes(1);
    expect(pods.discoverAll).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });

    expect(chat.getAll).toHaveBeenCalledTimes(7);
    expect(rooms.getJoined).toHaveBeenCalledTimes(7);
    expect(pods.list).toHaveBeenCalledTimes(2);
    expect(pods.discoverAll).toHaveBeenCalledTimes(2);
  });

  it('does not overlap slow messaging hydration', async () => {
    vi.useFakeTimers();
    let resolveConversations;
    chat.getAll.mockReturnValue(new Promise((resolve) => {
      resolveConversations = resolve;
    }));

    renderMessaging();
    await flushPromises();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });

    expect(chat.getAll).toHaveBeenCalledTimes(1);
    expect(rooms.getJoined).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveConversations([]);
      await Promise.resolve();
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(10_000);
    });

    expect(chat.getAll).toHaveBeenCalledTimes(2);
    expect(rooms.getJoined).toHaveBeenCalledTimes(2);
  });

  it('starts on visibility and suspends both polling cadences while hidden', async () => {
    vi.useFakeTimers();
    setDocumentHidden(true);
    renderMessaging();
    await flushPromises();

    expect(chat.getAll).not.toHaveBeenCalled();
    expect(pods.list).not.toHaveBeenCalled();

    await act(async () => {
      setDocumentHidden(false);
      document.dispatchEvent(new Event('visibilitychange'));
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(chat.getAll).toHaveBeenCalledTimes(1);
    expect(pods.list).toHaveBeenCalledTimes(1);

    await act(async () => {
      setDocumentHidden(true);
      document.dispatchEvent(new Event('visibilitychange'));
      await vi.advanceTimersByTimeAsync(60_000);
    });

    expect(chat.getAll).toHaveBeenCalledTimes(1);
    expect(rooms.getJoined).toHaveBeenCalledTimes(1);
    expect(pods.list).toHaveBeenCalledTimes(1);
    expect(pods.discoverAll).toHaveBeenCalledTimes(1);
  });

  it('polls active members every ten seconds and suspends while hidden', async () => {
    vi.useFakeTimers();
    rooms.getJoined.mockResolvedValue(['ambient']);
    rooms.getUsers.mockResolvedValue([{ username: 'alice' }]);

    renderMessaging({ initialKind: 'room' });
    await flushPromises();
    await flushPromises();
    await flushPromises();
    await flushPromises();

    expect(rooms.getUsers).toHaveBeenCalledTimes(1);
    expect(screen.getByText('alice')).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(9_999);
    });
    expect(rooms.getUsers).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(rooms.getUsers).toHaveBeenCalledTimes(2);

    await act(async () => {
      setDocumentHidden(true);
      document.dispatchEvent(new Event('visibilitychange'));
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(rooms.getUsers).toHaveBeenCalledTimes(2);

    await act(async () => {
      setDocumentHidden(false);
      document.dispatchEvent(new Event('visibilitychange'));
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(rooms.getUsers).toHaveBeenCalledTimes(3);
  });

  it('does not overlap member polls and retains the last successful snapshot', async () => {
    vi.useFakeTimers();
    let resolveMembers;
    rooms.getJoined.mockResolvedValue(['ambient']);
    rooms.getUsers
      .mockReturnValueOnce(new Promise((resolve) => {
        resolveMembers = resolve;
      }))
      .mockRejectedValueOnce(new Error('temporary failure'));

    renderMessaging({ initialKind: 'room' });
    await flushPromises();
    await flushPromises();
    await flushPromises();
    await flushPromises();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(rooms.getUsers).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveMembers([{ username: 'alice' }]);
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(screen.getByText('alice')).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    expect(rooms.getUsers).toHaveBeenCalledTimes(2);
    expect(screen.getByText('alice')).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    expect(rooms.getUsers).toHaveBeenCalledTimes(3);
    expect(screen.queryByText('alice')).not.toBeInTheDocument();
    expect(screen.getByText('No members reported yet.')).toBeInTheDocument();
  });

  it('shows a failed pod-create action while preserving the entered name', async () => {
    const user = userEvent.setup();
    pods.create.mockRejectedValueOnce({
      response: { data: { detail: 'Pod service unavailable', status: 503 } },
    });
    renderMessaging();

    await user.click(await screen.findByRole('button', { name: 'Create a pod room' }));
    const nameInput = screen.getByPlaceholderText('pod room name');
    await user.type(nameInput, 'Listening room');
    await user.click(screen.getByRole('button', { name: 'Create' }));

    expect(await screen.findByTestId('messaging-action-error'))
      .toHaveTextContent('Could not create the pod room: Please try again.');
    expect(nameInput).toHaveValue('Listening room');
  });

  it('distinguishes failed conversation loading from an empty history and retries', async () => {
    const user = userEvent.setup();
    chat.getAll.mockRejectedValueOnce(new Error('Conversation store offline'));
    renderMessaging();

    expect(await screen.findByTestId('messaging-list-error'))
      .toHaveTextContent('Could not load saved conversations and joined rooms: Please try again.');
    expect(screen.queryByText('No saved direct messages.')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', {
      name: 'Retry loading saved conversations',
    }));

    await waitFor(() => expect(chat.getAll).toHaveBeenCalledTimes(2));
    expect(await screen.findByText('No saved direct messages.')).toBeInTheDocument();
    expect(screen.queryByTestId('messaging-list-error')).not.toBeInTheDocument();
  });

  it('keeps pod list failures distinct from an empty pod list and retries', async () => {
    const user = userEvent.setup();
    pods.list.mockRejectedValueOnce(new Error('Pod storage offline'));
    renderMessaging();

    expect(await screen.findByTestId('pod-list-error'))
      .toHaveTextContent('Could not load saved pod channels: Please try again.');
    expect(screen.queryByText('No pod rooms or discovered pods yet.'))
      .not.toBeInTheDocument();
    await user.click(screen.getByRole('button', {
      name: 'Retry loading saved pod channels',
    }));

    await waitFor(() => expect(pods.list).toHaveBeenCalledTimes(2));
    expect(await screen.findByText('Pod 1 / General')).toBeInTheDocument();
    expect(screen.queryByTestId('pod-list-error')).not.toBeInTheDocument();
  });
});
