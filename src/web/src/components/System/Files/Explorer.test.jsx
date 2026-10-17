import * as files from '../../../lib/files';
import Explorer from './Explorer';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';

vi.mock('../../../lib/files', () => ({
  deleteDirectory: vi.fn(),
  deleteFile: vi.fn(),
  deleteItems: vi.fn(),
  list: vi.fn(),
}));

const emptyDirectory = { directories: [], files: [] };

describe('System Files Explorer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    files.deleteDirectory.mockResolvedValue(undefined);
    files.deleteFile.mockResolvedValue(undefined);
    files.deleteItems.mockResolvedValue({ results: [] });
    files.list.mockResolvedValue(emptyDirectory);
  });

  it('does not fetch file listings while inactive', () => {
    render(
      <Explorer
        active={false}
        remoteFileManagement={false}
        root="incomplete"
      />,
    );

    expect(files.list).not.toHaveBeenCalled();
  });

  it('fetches file listings when activated', async () => {
    const { rerender } = render(
      <Explorer
        active={false}
        remoteFileManagement={false}
        root="incomplete"
      />,
    );

    rerender(
      <Explorer
        active
        remoteFileManagement={false}
        root="incomplete"
      />,
    );

    await waitFor(() =>
      expect(files.list).toHaveBeenCalledWith({
        root: 'incomplete',
        subdirectory: '',
      }),
    );
  });

  it('starts at the new root without fetching its previous subdirectory', async () => {
    const user = userEvent.setup();
    files.list
      .mockResolvedValueOnce({
        directories: [{ fullName: 'Albums', name: 'Albums' }],
        files: [],
      })
      .mockResolvedValue(emptyDirectory);

    const { rerender } = render(
      <Explorer
        remoteFileManagement={false}
        root="downloads"
      />,
    );

    const albumButton = await screen.findByRole('button', {
      name: 'Open the Albums directory.',
    });
    await user.click(albumButton);
    await waitFor(() =>
      expect(files.list).toHaveBeenNthCalledWith(2, {
        root: 'downloads',
        subdirectory: 'Albums',
      }),
    );

    rerender(
      <Explorer
        remoteFileManagement={false}
        root="incomplete"
      />,
    );

    await waitFor(() =>
      expect(files.list).toHaveBeenLastCalledWith({
        root: 'incomplete',
        subdirectory: '',
      }),
    );
    expect(screen.getByText('/incomplete/')).toBeInTheDocument();
  });

  it('reports listing failures and retries the active directory', async () => {
    const user = userEvent.setup();
    files.list
      .mockRejectedValueOnce(new Error('temporary directory failure'))
      .mockResolvedValueOnce(emptyDirectory);

    render(
      <Explorer
        remoteFileManagement={false}
        root="downloads"
      />,
    );

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to load this directory.',
    );
    await user.click(screen.getByRole('button', { name: 'Try Again' }));

    await waitFor(() => expect(files.list).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    expect(screen.getByText('No files or directories')).toBeInTheDocument();
  });

  it('ignores a slow directory response after navigating back', async () => {
    const user = userEvent.setup();
    let resolveNested;
    let resolveRootRefresh;
    files.list
      .mockResolvedValueOnce({
        directories: [{ fullName: 'Albums', name: 'Albums' }],
        files: [],
      })
      .mockImplementationOnce(() => new Promise((resolve) => {
        resolveNested = resolve;
      }))
      .mockImplementationOnce(() => new Promise((resolve) => {
        resolveRootRefresh = resolve;
      }));

    render(
      <Explorer
        remoteFileManagement={false}
        root="downloads"
      />,
    );

    const albumButton = await screen.findByRole('button', {
      name: 'Open the Albums directory.',
    });
    albumButton.focus();
    await user.keyboard('{Enter}');
    await waitFor(() =>
      expect(files.list).toHaveBeenNthCalledWith(2, {
        root: 'downloads',
        subdirectory: 'Albums',
      }),
    );

    const parentButton = screen.getByRole('button', {
      name: 'Go up one directory.',
    });
    parentButton.focus();
    await user.keyboard('{Enter}');
    await waitFor(() => expect(files.list).toHaveBeenCalledTimes(3));

    resolveRootRefresh({
      directories: [{ fullName: 'Current', name: 'Current' }],
      files: [],
    });
    await screen.findByRole('button', { name: 'Open the Current directory.' });

    resolveNested({
      directories: [{ fullName: 'Stale', name: 'Stale' }],
      files: [],
    });

    expect(await screen.findByRole('button', { name: 'Open the Current directory.' }))
      .toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Open the Stale directory.' }))
      .not.toBeInTheDocument();
  });

  it('explains delete actions, preserves failures, and refreshes after deletion', async () => {
    const user = userEvent.setup();
    files.list
      .mockResolvedValueOnce({
        directories: [],
        files: [{ fullName: 'sample.flac', length: 1024, name: 'sample.flac' }],
      })
      .mockResolvedValueOnce(emptyDirectory);
    files.deleteFile
      .mockRejectedValueOnce(new Error('temporary delete failure'))
      .mockResolvedValueOnce(undefined);

    render(
      <Explorer
        remoteFileManagement
        root="downloads"
      />,
    );

    const deleteTrigger = await screen.findByRole('button', {
      name: 'Delete file sample.flac',
    });
    fireEvent.mouseOver(deleteTrigger);
    expect(await screen.findByText(
      "Open confirmation to permanently delete file 'sample.flac'.",
    )).toBeInTheDocument();

    deleteTrigger.focus();
    await user.keyboard('{Enter}');
    expect(await screen.findByText(
      "Are you sure you want to permanently delete 'sample.flac'?",
    )).toBeInTheDocument();
    const confirmDelete = screen.getByRole('button', { name: 'Delete', exact: true });
    fireEvent.mouseOver(confirmDelete);
    expect(await screen.findByText(
      'Permanently delete this file. This action cannot be undone.',
    )).toBeInTheDocument();

    await user.click(confirmDelete);
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to delete this file.',
    );
    expect(screen.getByText(
      "Are you sure you want to permanently delete 'sample.flac'?",
    )).toBeInTheDocument();

    await user.click(confirmDelete);
    await waitFor(() => expect(files.deleteFile).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(files.list).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.queryByText(
      "Are you sure you want to permanently delete 'sample.flac'?",
    )).not.toBeInTheDocument());
    expect(files.deleteFile).toHaveBeenLastCalledWith({
      path: 'sample.flac',
      root: 'downloads',
    });
    expect(screen.getByText('No files or directories')).toBeInTheDocument();
  });

  it('deletes nested directories using a relative path and refreshes them', async () => {
    const user = userEvent.setup();
    files.list
      .mockResolvedValueOnce({
        directories: [{ fullName: 'Albums', name: 'Albums' }],
        files: [],
      })
      .mockResolvedValueOnce({
        directories: [{ fullName: 'Live', name: 'Live' }],
        files: [],
      })
      .mockResolvedValueOnce(emptyDirectory);

    render(
      <Explorer
        remoteFileManagement
        root="downloads"
      />,
    );

    await user.click(await screen.findByRole('button', {
      name: 'Open the Albums directory.',
    }));
    await screen.findByRole('button', { name: 'Delete directory Live' });
    await user.click(screen.getByRole('button', { name: 'Delete directory Live' }));
    await user.click(screen.getByRole('button', { name: 'Delete', exact: true }));

    await waitFor(() => expect(files.deleteDirectory).toHaveBeenCalledWith({
      path: 'Albums/Live',
      root: 'downloads',
    }));
    await waitFor(() => expect(files.list).toHaveBeenCalledTimes(3));
    expect(await screen.findByText('No files or directories')).toBeInTheDocument();
  });

  it('calculates directory sizes only after the user requests the filesystem scan', async () => {
    const user = userEvent.setup();
    files.list.mockResolvedValue({
      directories: [{ fullName: 'Album', name: 'Album', length: 2048 }],
      files: [],
    });

    render(
      <Explorer
        remoteFileManagement={false}
        root="downloads"
      />,
    );

    await user.click(await screen.findByRole('button', { name: 'Calculate folder sizes' }));

    await waitFor(() => expect(files.list).toHaveBeenLastCalledWith({
      root: 'downloads',
      subdirectory: '',
      includeDirectorySizes: true,
    }));
    expect(await screen.findByText(/2.*KB/i)).toBeInTheDocument();
  });

  it('selects multiple items, confirms once, and reports partial delete results', async () => {
    const user = userEvent.setup();
    files.list
      .mockResolvedValueOnce({
        directories: [{ fullName: 'Album', name: 'Album' }],
        files: [{ fullName: 'single.flac', length: 12, name: 'single.flac' }],
      })
      .mockResolvedValueOnce({
        directories: [],
        files: [{ fullName: 'single.flac', length: 12, name: 'single.flac' }],
      });
    files.deleteItems.mockResolvedValue({
      results: [
        { path: 'Album', type: 'directory', succeeded: true },
        { path: 'single.flac', type: 'file', succeeded: false, error: 'access-denied' },
      ],
    });

    render(
      <Explorer
        remoteFileManagement
        root="downloads"
      />,
    );

    await user.click(await screen.findByRole('checkbox', { name: 'Select directory Album' }));
    await user.click(screen.getByRole('checkbox', { name: 'Select file single.flac' }));
    expect(screen.getByText('2 selected')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Delete selected (2)' }));
    expect(await screen.findByText(/Directories will be deleted recursively/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Delete 2 items' }));

    await waitFor(() => expect(files.deleteItems).toHaveBeenCalledWith({
      root: 'downloads',
      items: [
        { path: 'Album', type: 'directory' },
        { path: 'single.flac', type: 'file' },
      ],
    }));
    expect(await screen.findByRole('status')).toHaveTextContent('Deleted 1 item.');
    expect(await screen.findByRole('alert')).toHaveTextContent('single.flac: Access was denied');
    expect(screen.getByRole('checkbox', { name: 'Select file single.flac' })).toBeChecked();
  });
});
