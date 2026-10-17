// <copyright file="SearchList.test.jsx" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import SearchList from './SearchList';
import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import {
  getInterfaceTextDirection,
  getInterfaceTextLanguage,
  resetInterfaceLanguage,
  setInterfaceLanguage,
} from '../../../lib/interfaceLocale';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { stubLocaleCatalogFetch } from '../../../test/localeCatalogFetchMock';

vi.mock('./SearchListRow', () => ({
  default: ({ onSelectionChange, search, selected, selectionDisabled }) => (
    <tr>
      <td>
        <input
          aria-label={`Select search ${search.searchText || search.id}`}
          checked={selected}
          disabled={selectionDisabled}
          onChange={(event) => onSelectionChange(event.target.checked)}
          type="checkbox"
        />
      </td>
      <td>{search.id}</td>
    </tr>
  ),
}));

describe('SearchList', () => {
  beforeEach(() => stubLocaleCatalogFetch(vi));
  afterEach(async () => {
    await resetInterfaceLanguage();
    vi.unstubAllGlobals();
  });

  it('sets per-label Arabic metadata and falls back to English LTR for missing translations', async () => {
    expect(getInterfaceTextLanguage('Not a catalog label', 'ar')).toBe('en');
    expect(getInterfaceTextDirection('Not a catalog label', 'ar')).toBe('ltr');

    await setInterfaceLanguage('ar');
    render(
      <SearchList
        hasMoreFromServer
        searches={{ first: { id: 'first', startedAt: '2026-08-20T12:00:00Z' } }}
      />,
    );

    const loadMore = screen.getByText('تحميل المزيد من عمليات البحث');
    expect(loadMore).toHaveAttribute('lang', 'ar');
    expect(loadMore).toHaveAttribute('dir', 'rtl');
  });

  it('labels pagination actions', () => {
    const searches = Object.fromEntries(
      Array.from({ length: 101 }, (_, index) => [
        `search-${index}`,
        {
          id: `search-${index}`,
          startedAt: new Date(2026, 0, 1, 0, index).toISOString(),
        },
      ]),
    );

    render(<SearchList searches={searches} />);

    expect(
      screen.getByRole('button', { name: 'Previous search page' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Next search page' }),
    ).toBeInTheDocument();
  });

  it('loads another server page without clearing the current selection', async () => {
    const onLoadMore = vi.fn();
    const first = {
      id: 'first',
      startedAt: '2026-08-20T12:00:00Z',
      state: 'Completed',
    };
    const view = render(
      <SearchList
        hasMoreFromServer
        onLoadMore={onLoadMore}
        searches={{ first }}
      />,
    );

    fireEvent.click(screen.getByRole('checkbox', { name: 'Select search first' }));
    fireEvent.click(screen.getByRole('button', { name: 'Load more searches' }));

    expect(onLoadMore).toHaveBeenCalledTimes(1);
    view.rerender(
      <SearchList
        hasMoreFromServer={false}
        onLoadMore={onLoadMore}
        searches={{
          first,
          second: {
            id: 'second',
            startedAt: '2026-08-20T11:00:00Z',
            state: 'Completed',
          },
        }}
      />,
    );

    expect(screen.getByText('1 selected (1 completed, 0 active)')).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Select search first' })).toBeChecked();
  });

  it('selects the filtered list and routes actions to the eligible searches', async () => {
    const completed = {
      id: 'completed',
      searchText: 'finished query',
      startedAt: '2026-08-20T12:00:00Z',
      state: 'Completed',
    };
    const active = {
      id: 'active',
      searchText: 'running query',
      startedAt: '2026-08-20T11:00:00Z',
      state: 'InProgress',
    };
    const onRemoveSelected = vi.fn().mockResolvedValue(['completed']);
    const onStopSelected = vi.fn().mockResolvedValue(['active']);
    const onResearchSelected = vi.fn().mockResolvedValue(['completed']);

    render(
      <SearchList
        onRemoveSelected={onRemoveSelected}
        onResearchSelected={onResearchSelected}
        onStopSelected={onStopSelected}
        searches={{ active, completed }}
      />,
    );

    fireEvent.click(
      screen.getByRole('checkbox', { name: 'Select all searches in current list' }),
    );

    expect(screen.getByText('2 selected (1 completed, 1 active)')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Search Again' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Stop Active' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Delete Selected' })).toBeEnabled();

    fireEvent.click(screen.getByRole('button', { name: 'Delete Selected' }));

    await waitFor(() => {
      expect(onRemoveSelected).toHaveBeenCalledWith([completed]);
    });
    expect(screen.getByText('1 selected (0 completed, 1 active)')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Stop Active' }));

    await waitFor(() => {
      expect(onStopSelected).toHaveBeenCalledWith([active]);
    });
    expect(screen.queryByRole('toolbar', { name: 'Selected search actions' })).not.toBeInTheDocument();
  });
});
