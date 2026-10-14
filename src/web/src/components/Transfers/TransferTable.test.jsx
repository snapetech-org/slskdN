// <copyright file="TransferTable.test.jsx" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import TransferTable from './TransferTable';
import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { setExperiencePreference } from '../../lib/experiencePreferences';
import { ALL_COLUMNS } from '../../lib/transferColumns';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

describe('TransferTable', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal(
      'ResizeObserver',
      class ResizeObserver {
        disconnect() {}

        observe() {}
      },
    );
  });

  afterEach(() => {
    localStorage.clear();
    vi.unstubAllGlobals();
  });

  const renderTable = (transfers = [], selectedFiles = [], direction = 'download') => render(
    <MemoryRouter>
      <TransferTable
        direction={direction}
        onCancel={vi.fn()}
        onCancelSelected={vi.fn()}
        onOpenRequest={vi.fn()}
        onRemove={vi.fn()}
        onRemoveSelected={vi.fn()}
        onRetry={vi.fn()}
        onRetrySelected={vi.fn()}
        onSelectAll={vi.fn()}
        onSelectionChange={vi.fn()}
        selectedFiles={selectedFiles}
        selectedKeys={new Set()}
        transfers={transfers}
      />
    </MemoryRouter>,
  );

  it('labels the column chooser', () => {
    renderTable();

    expect(
      screen.getByRole('button', { name: 'Choose transfer table columns' }),
    ).toBeInTheDocument();
  });

  it('sorts by newest request by default and exposes the date column', () => {
    renderTable([
      {
        direction: 'Download',
        filename: 'older.flac',
        id: 'older',
        requestedAt: '2026-10-12T10:00:00Z',
        size: 10,
        state: 'Queued',
        username: 'peer',
      },
      {
        direction: 'Download',
        filename: 'newer.flac',
        id: 'newer',
        requestedAt: '2026-10-13T10:00:00Z',
        size: 10,
        state: 'Queued',
        username: 'peer',
      },
    ]);

    expect(document.querySelector('[data-colkey="requested"]'))
      .toHaveAttribute('aria-sort', 'descending');
    const transferRows = screen.getAllByRole('row').filter((row) =>
      row.querySelector('[role="gridcell"]'),
    );
    expect(transferRows[0]).toHaveTextContent('newer.flac');
    expect(transferRows[1]).toHaveTextContent('older.flac');
  });

  it('formats request timestamps with the selected regional locale', () => {
    setExperiencePreference('regionalFormat', 'de');
    const requestedAt = '2026-10-13T10:00:00Z';

    renderTable([{
      direction: 'Download',
      filename: 'localized-date.flac',
      id: 'localized-date',
      requestedAt,
      size: 10,
      state: 'Queued',
      username: 'peer',
    }]);

    expect(screen.getByText(new Date(requestedAt).toLocaleString('de'))).toBeInTheDocument();
  });

  it('explains the scope of each selected-transfer action', async () => {
    renderTable([], [{ id: 'transfer-1' }, { id: 'transfer-2' }]);

    for (const [label, tooltip] of [
      ['Retry', 'Retry all 2 selected transfers.'],
      ['Cancel', 'Cancel all 2 selected transfers.'],
      ['Remove', 'Remove all 2 selected transfers from the list.'],
    ]) {
      const button = screen.getByRole('button', { name: label });
      fireEvent.mouseEnter(button);

      expect(await screen.findByText(tooltip)).toBeInTheDocument();
    }
  });

  it('hides retry actions for failed uploads, including selected transfers', () => {
    const transfer = {
      direction: 'Upload',
      filename: 'Artist/Track.flac',
      id: 'upload-1',
      size: 10,
      state: 'Errored',
      username: 'peer-one',
    };

    renderTable([transfer], [transfer], 'upload');

    expect(screen.queryByRole('button', { name: 'Retry transfer' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument();
  });

  it('applies each resize movement from the drag-start width', () => {
    renderTable();

    const handle = screen.getByLabelText('Resize Name column');
    fireEvent.mouseDown(handle, { clientX: 100 });
    fireEvent.mouseMove(document, { clientX: 120 });
    fireEvent.mouseMove(document, { clientX: 121 });
    fireEvent.mouseUp(document);

    const saved = JSON.parse(localStorage.getItem('slskdn-transfer-columns-download'));
    expect(saved.widths.name).toBe(221);
  });

  it('resets persisted transfer column widths', () => {
    renderTable();

    const handle = screen.getByLabelText('Resize Name column');
    fireEvent.mouseDown(handle, { clientX: 100 });
    fireEvent.mouseMove(document, { clientX: 260 });
    fireEvent.mouseUp(document);

    fireEvent.click(screen.getByRole('button', { name: 'Reset transfer column widths' }));

    const saved = JSON.parse(localStorage.getItem('slskdn-transfer-columns-download'));
    expect(saved.widths.name).toBe(200);
  });

  it('uses persisted column order for both headers and rows', () => {
    localStorage.setItem(
      'slskdn-transfer-columns-download',
      JSON.stringify({
        order: ['peer', 'name', 'size'],
        visible: Object.fromEntries(
          ALL_COLUMNS.map(({ key }) => [key, ['name', 'peer', 'size'].includes(key)]),
        ),
        widths: { name: 200, peer: 90, size: 120 },
      }),
    );

    const { container } = renderTable([{
      direction: 'Download',
      filename: 'Artist/Track.flac',
      id: 'transfer-1',
      size: 10,
      state: 'Queued',
      username: 'peer-one',
    }]);

    const headerKeys = [...container.querySelectorAll('.transfer-header-cell')]
      .map((element) => element.dataset.colkey);
    const rowKeys = [...container.querySelectorAll('.transfer-row:not(.transfer-header-row) [data-colkey]')]
      .map((element) => element.dataset.colkey);

    expect(headerKeys).toEqual(['peer', 'name', 'size']);
    expect(rowKeys).toEqual(['peer', 'name', 'size']);
    expect(headerKeys).not.toContain('actions');
  });
});
