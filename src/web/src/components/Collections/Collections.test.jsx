import Collections from './Collections';
import * as collectionsAPI from '../../lib/collections';
import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('../../lib/collections', () => ({
  createCollection: vi.fn(),
  createShare: vi.fn(),
  addCollectionItem: vi.fn(),
  deleteCollection: vi.fn(),
  getCollectionItems: vi.fn(),
  getCollections: vi.fn(),
  getShareGroups: vi.fn(),
  getSharesByCollection: vi.fn(),
  searchLibraryItems: vi.fn(),
}));

vi.mock('../Player/PlayCollectionItemButton', () => ({
  default: () => null,
}));

describe('Collections', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    collectionsAPI.getCollections.mockResolvedValue({
      data: [
        {
          id: 'collection-1',
          itemCount: 0,
          title: 'Fixture Collection',
          type: 'Playlist',
        },
      ],
    });
    collectionsAPI.getShareGroups.mockResolvedValue({
      data: [{ id: 'group-1', name: 'Friends' }],
    });
    collectionsAPI.getCollectionItems.mockResolvedValue({ data: [] });
    collectionsAPI.getSharesByCollection.mockResolvedValue({ data: [] });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders structured delete errors as text', async () => {
    collectionsAPI.deleteCollection.mockRejectedValue({
      response: {
        data: {
          detail: 'Collection is still shared',
          status: 400,
          title: 'Bad Request',
        },
      },
    });

    render(<Collections />);

    await screen.findByText('Fixture Collection');
    fireEvent.click(screen.getByText('Delete'));

    expect(await screen.findByText('Failed to delete collection'))
      .toBeInTheDocument();
  });

  it('renders structured share creation errors as text', async () => {
    collectionsAPI.createShare.mockRejectedValue({
      response: {
        data: {
          detail: 'Share group no longer exists',
          status: 400,
          title: 'Bad Request',
        },
      },
    });

    render(<Collections />);

    fireEvent.click(await screen.findByText('Fixture Collection'));
    await waitFor(() => expect(collectionsAPI.getCollectionItems).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId('share-create'));
    fireEvent.click(await screen.findByTestId('share-create-submit'));

    expect(await screen.findByText('Failed to create share'))
      .toBeInTheDocument();
  });

  it('explains collection actions without invoking them on hover', async () => {
    render(<Collections />);

    const expectTooltip = async (button, tooltip) => {
      const trigger = button.disabled ? button.parentElement : button;
      fireEvent.mouseEnter(trigger);
      expect(await screen.findByText(tooltip)).toBeInTheDocument();
      fireEvent.mouseLeave(trigger);
    };

    await expectTooltip(
      await screen.findByTestId('collections-create'),
      'Open the collection form to create a playlist or list for organizing items.',
    );
    await expectTooltip(
      screen.getByRole('button', { name: 'Delete' }),
      'Delete this collection after confirmation when you no longer need it.',
    );

    fireEvent.click(screen.getByTestId('collections-create'));
    await expectTooltip(
      screen.getByRole('button', { name: 'Cancel' }),
      'Close the form and discard the collection details you entered.',
    );
    await expectTooltip(
      screen.getByTestId('collections-create-submit'),
      'Save this collection so you can organize items here. Enter a title first to enable creation.',
    );
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    fireEvent.click(screen.getByText('Fixture Collection'));
    await waitFor(() => {
      expect(collectionsAPI.getCollectionItems).toHaveBeenCalled();
    });
    await expectTooltip(
      screen.getByTestId('collection-add-item'),
      'Open item search so you can add a library item or content ID to this collection.',
    );
    await expectTooltip(
      screen.getByTestId('share-create'),
      'Choose a share group and permissions so its members can access this collection.',
    );

    fireEvent.click(screen.getByTestId('share-create'));
    await expectTooltip(
      screen.getByRole('button', { name: 'Cancel' }),
      'Close this form without creating a share.',
    );
    await expectTooltip(
      screen.getByTestId('share-create-submit'),
      'Share this collection with the selected group using the permissions below. Choose a group first to enable sharing.',
    );
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    fireEvent.click(screen.getByTestId('collection-add-item'));
    await expectTooltip(
      screen.getByRole('button', { name: 'Cancel' }),
      'Close item search and clear the current query and results.',
    );
    await expectTooltip(
      screen.getByTestId('collection-add-item-submit'),
      'Add the selected search result or entered content ID to this collection. Enter a query first to enable.',
    );

    expect(window.confirm).not.toHaveBeenCalled();
    expect(collectionsAPI.addCollectionItem).not.toHaveBeenCalled();
    expect(collectionsAPI.createCollection).not.toHaveBeenCalled();
    expect(collectionsAPI.createShare).not.toHaveBeenCalled();
    expect(collectionsAPI.deleteCollection).not.toHaveBeenCalled();
  });

  it('explains the empty-state collection action', async () => {
    collectionsAPI.getCollections.mockResolvedValue({ data: [] });
    render(<Collections />);

    const button = await screen.findByTestId('collections-create-empty');
    fireEvent.mouseEnter(button);

    expect(await screen.findByText(
      'Open the collection form to create a playlist or list for organizing items.',
    )).toBeInTheDocument();
    expect(collectionsAPI.createCollection).not.toHaveBeenCalled();
  });

  it('names collection pagination controls for assistive technology', async () => {
    collectionsAPI.getCollections.mockResolvedValue({
      data: Array.from({ length: 101 }, (_, index) => ({
        id: `collection-${index}`,
        itemCount: 0,
        title: `Collection ${index}`,
        type: 'Playlist',
      })),
    });
    render(<Collections />);

    expect(await screen.findByRole('button', { name: 'Previous collections page' }))
      .toBeDisabled();
    expect(screen.getByRole('button', { name: 'Next collections page' }))
      .toBeEnabled();
  });
});
