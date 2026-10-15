import ShareGroups from './ShareGroups';
import * as collectionsAPI from '../../lib/collections';
import * as identityAPI from '../../lib/identity';
import React from 'react';
import userEvent from '@testing-library/user-event';
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('../../lib/collections', () => ({
  addShareGroupMember: vi.fn(),
  createShareGroup: vi.fn(),
  deleteShareGroup: vi.fn(),
  getShareGroups: vi.fn(),
  getShareGroupMembers: vi.fn(),
  removeShareGroupMember: vi.fn(),
}));

vi.mock('../../lib/identity', () => ({
  getContacts: vi.fn(),
}));

describe('ShareGroups', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    collectionsAPI.getShareGroups.mockResolvedValue({
      data: [
        {
          createdAt: '2026-05-06T00:00:00Z',
          id: 'group-1',
          name: 'Friends',
        },
      ],
    });
    identityAPI.getContacts.mockResolvedValue({ data: [] });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders structured delete errors as text', async () => {
    const user = userEvent.setup();
    collectionsAPI.deleteShareGroup.mockRejectedValue({
      response: {
        data: {
          detail: 'Share group still has grants',
          status: 400,
          title: 'Bad Request',
        },
      },
    });

    render(<ShareGroups />);

    await user.click(await screen.findByText('Delete'));

    expect(await screen.findByText('Failed to delete share group'))
      .toBeInTheDocument();
  });

  it('shows group members in a navigable dialog', async () => {
    const user = userEvent.setup();
    collectionsAPI.getShareGroupMembers.mockResolvedValue({
      data: [
        { contactNickname: 'Alice', userId: 'alice' },
        { userId: 'bob' },
      ],
    });
    render(<ShareGroups />);

    await user.click(await screen.findByTestId('group-view-members'));

    expect(await screen.findByText('Members of Friends'))
      .toBeInTheDocument();
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('bob')).toBeInTheDocument();
    expect(collectionsAPI.getShareGroupMembers).toHaveBeenCalledWith('group-1', true);
  });

  it('shows member-load errors and retries them in the dialog', async () => {
    const user = userEvent.setup();
    collectionsAPI.getShareGroupMembers
      .mockRejectedValueOnce({
        response: {
          data: {
            detail: 'Member service unavailable',
            status: 503,
          },
        },
      })
      .mockResolvedValueOnce({ data: [{ userId: 'alice' }] });
    render(<ShareGroups />);

    await user.click(await screen.findByTestId('group-view-members'));
    expect(await screen.findByText('Failed to load group members'))
      .toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Retry Members' }));

    expect(await screen.findByText('alice')).toBeInTheDocument();
    expect(collectionsAPI.getShareGroupMembers).toHaveBeenCalledTimes(2);
  });
});
