import { deleteDirectory, deleteFile, deleteItems, list } from '../../../lib/files';
import { formatBytes, formatDate } from '../../../lib/util';
import React, { useEffect, useRef, useState } from 'react';
import { Button, Checkbox, Header, Icon, Message, Modal, Popup, Table } from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);
const emptyDirectory = { directories: [], files: [] };
const itemKey = ({ path, type }) => `${type}:${path}`;
const joinPath = (...segments) => segments.filter(Boolean).join('/');

const getErrorMessage = (error, fallback) => {
  const response = error?.response?.data;
  if (typeof response === 'string' && response.trim()) {
    return response;
  }

  return response?.message || error?.message || fallback;
};

const getDeleteErrorMessage = (error) => ({
  'access-denied': 'Access was denied',
  'delete-failed': 'The file system could not delete this item',
  'not-found': 'The item no longer exists',
}[error] || 'The item could not be deleted');

const DeleteControl = ({ fullName, isDirectory, onDeleted, path, root }) => {
  const [open, setOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState(null);
  const itemType = isDirectory ? 'directory' : 'file';

  const remove = async () => {
    setDeleting(true);
    setError(null);

    try {
      const removeItem = isDirectory ? deleteDirectory : deleteFile;
      await removeItem({ path, root });
      setOpen(false);
      onDeleted({ name: fullName, type: itemType });
    } catch (error_) {
      setError(
        getErrorMessage(error_, `Unable to delete this ${itemType}.`),
      );
    } finally {
      setDeleting(false);
    }
  };

  return (
    <>
      <Popup
        content={`Open confirmation to permanently delete ${itemType} '${fullName}'.`}
        on={['hover', 'focus']}
        position="top center"
        trigger={(
          <Button
            aria-label={`Delete ${itemType} ${fullName}`}
            basic
            icon="trash alternate"
            onClick={() => {
              setError(null);
              setOpen(true);
            }}
            size="small"
          />
        )}
      />
      <Modal
        onClose={() => !deleting && setOpen(false)}
        open={open}
        size="small"
      >
        <Modal.Header>
          <Icon name="trash alternate" />
          {`Delete ${itemType}`}
        </Modal.Header>
        <Modal.Content>
          <p>{`Are you sure you want to permanently delete '${fullName}'?`}</p>
          {error ? (
            <Message
              content={error}
              error
              role="alert"
            />
          ) : null}
        </Modal.Content>
        <Modal.Actions>
          <Popup
            content="Close this confirmation without deleting the item."
            on={['hover', 'focus']}
            trigger={(
              <Button
                disabled={deleting}
                onClick={() => setOpen(false)}
              >
                Cancel
              </Button>
            )}
          />
          <Popup
            content={`Permanently delete this ${itemType}. This action cannot be undone.`}
            on={['hover', 'focus']}
            trigger={(
              <Button
                disabled={deleting}
                loading={deleting}
                negative
                onClick={remove}
              >
                Delete
              </Button>
            )}
          />
        </Modal.Actions>
      </Modal>
    </>
  );
};

const FileRow = ({
  fullName,
  length,
  modifiedAt,
  name,
  onDeleted,
  selected,
  onSelectionChange,
  remoteFileManagement,
  root,
  subdirectory,
}) => (
  <Table.Row key={fullName}>
    <Table.Cell className="explorer-list-name">
      <Icon name="file outline" />
      {name}
    </Table.Cell>
    <Table.Cell className="explorer-list-date">
      {modifiedAt ? formatDate(modifiedAt) : ''}
    </Table.Cell>
    <Table.Cell className="explorer-list-size">
      {length === null || length === undefined ? '' : formatBytes(length)}
    </Table.Cell>
    <Table.Cell className="explorer-list-action">
      {remoteFileManagement ? (
        <Checkbox
          aria-label={`Select file ${fullName}`}
          checked={selected}
          onChange={(_event, { checked }) => onSelectionChange(checked)}
        />
      ) : null}
      {remoteFileManagement ? (
        <DeleteControl
          fullName={fullName}
          isDirectory={false}
          onDeleted={onDeleted}
          path={[...subdirectory, fullName].filter(Boolean).join('/')}
          root={root}
        />
      ) : null}
    </Table.Cell>
  </Table.Row>
);

const DirectoryRow = ({
  deletable = true,
  fullName,
  length,
  modifiedAt,
  name,
  onClick = () => {},
  onDeleted,
  selected,
  onSelectionChange,
  remoteFileManagement,
  root,
  subdirectory,
}) => {
  const isParent = name === '..';
  const description = isParent
    ? 'Go up one directory.'
    : `Open the ${name} directory.`;

  return (
    <Table.Row key={name}>
      <Table.Cell className="explorer-list-name">
        <Popup
          content={description}
          on={['hover', 'focus']}
          position="top left"
          trigger={(
            <Button
              aria-label={description}
              basic
              className="explorer-directory-button"
              onClick={onClick}
            >
              <Icon name={isParent ? 'level up' : 'folder'} />
              {name}
            </Button>
          )}
        />
      </Table.Cell>
      <Table.Cell className="explorer-list-date">
        {modifiedAt ? formatDate(modifiedAt) : ''}
      </Table.Cell>
      <Table.Cell className="explorer-list-size">
        {length === null || length === undefined ? '' : formatBytes(length)}
      </Table.Cell>
      <Table.Cell className="explorer-list-action">
        {remoteFileManagement && deletable ? (
          <Checkbox
            aria-label={`Select directory ${fullName}`}
            checked={selected}
            onChange={(_event, { checked }) => onSelectionChange(checked)}
          />
        ) : null}
        {remoteFileManagement && deletable ? (
          <DeleteControl
            fullName={fullName}
            isDirectory
            onDeleted={onDeleted}
            path={[...subdirectory, fullName].filter(Boolean).join('/')}
            root={root}
          />
        ) : null}
      </Table.Cell>
    </Table.Row>
  );
};

const BulkDeleteControl = ({ items, onDeleted, root }) => {
  const [open, setOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState(null);

  const remove = async () => {
    setDeleting(true);
    setError(null);

    try {
      const response = await deleteItems({
        root,
        items: items.map(({ path, type }) => ({ path, type })),
      });
      setOpen(false);
      onDeleted(response?.results ?? []);
    } catch (error_) {
      setError(getErrorMessage(error_, 'Unable to delete the selected items.'));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <>
      <Popup
        content="Permanently delete the selected files and directories. Selected directories are removed with their contents."
        on={['hover', 'focus']}
        position="top center"
        trigger={(
          <Button
            disabled={items.length === 0}
            negative
            onClick={() => {
              setError(null);
              setOpen(true);
            }}
          >
            {`Delete selected (${items.length})`}
          </Button>
        )}
      />
      <Modal
        onClose={() => !deleting && setOpen(false)}
        open={open}
        size="small"
      >
        <Modal.Header>
          <Icon name="trash alternate" />
          Delete selected items
        </Modal.Header>
        <Modal.Content>
          <p>{`Permanently delete ${items.length} selected items? Directories will be deleted recursively.`}</p>
          <ul className="explorer-delete-preview">
            {items.slice(0, 8).map((item) => (
              <li key={`${item.type}:${item.path}`}>
                <strong>{item.type}</strong>
                {' '}
                {item.path}
              </li>
            ))}
          </ul>
          {items.length > 8 ? <p>{`And ${items.length - 8} more items.`}</p> : null}
          {error ? <Message content={error} error role="alert" /> : null}
        </Modal.Content>
        <Modal.Actions>
          <Popup
            content="Close this confirmation without deleting anything."
            on={['hover', 'focus']}
            trigger={(
              <Button disabled={deleting} onClick={() => setOpen(false)}>
                Cancel
              </Button>
            )}
          />
          <Popup
            content="Delete every listed file and directory. This action cannot be undone."
            on={['hover', 'focus']}
            trigger={(
              <Button
                disabled={deleting}
                loading={deleting}
                negative
                onClick={remove}
              >
                {`Delete ${items.length} items`}
              </Button>
            )}
          />
        </Modal.Actions>
      </Modal>
    </>
  );
};

const Explorer = ({ active = true, remoteFileManagement, root }) => {
  const [directory, setDirectory] = useState(emptyDirectory);
  const [subdirectory, setSubdirectory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [includeDirectorySizes, setIncludeDirectorySizes] = useState(false);
  const [selectedKeys, setSelectedKeys] = useState(() => new Set());
  const [operationReport, setOperationReport] = useState(null);
  const [refreshSequence, setRefreshSequence] = useState(0);
  const previousRoot = useRef(root);

  useEffect(() => {
    if (previousRoot.current !== root) {
      previousRoot.current = root;
      if (subdirectory.length > 0) {
        setSubdirectory([]);
        return undefined;
      }
    }

    if (!active) {
      return undefined;
    }

    let requestIsCurrent = true;
    const loadDirectory = async () => {
      setLoading(true);
      setError(null);
      setDirectory(emptyDirectory);

      try {
        const request = {
          root,
          subdirectory: subdirectory.join('/'),
        };
        if (includeDirectorySizes) request.includeDirectorySizes = true;
        const result = await list(request);
        if (!requestIsCurrent) return;

        setDirectory({
          directories: asArray(result?.directories),
          files: asArray(result?.files),
        });
      } catch (error_) {
        if (!requestIsCurrent) return;
        setError(getErrorMessage(error_, 'Unable to load this directory.'));
      } finally {
        if (requestIsCurrent) setLoading(false);
      }
    };

    loadDirectory();
    return () => {
      requestIsCurrent = false;
    };
  }, [active, includeDirectorySizes, refreshSequence, root, subdirectory]);

  useEffect(() => {
    setSelectedKeys(new Set());
    setOperationReport(null);
  }, [root, subdirectory]);

  const select = (path) => {
    setSubdirectory((current) => [...current, path]);
  };

  const upOneSubdirectory = () => {
    setSubdirectory((current) => current.slice(0, -1));
  };

  const total = directory.directories.length + directory.files.length;
  const selectableItems = [
    ...directory.directories.map((item) => ({
      name: item.name,
      path: joinPath(subdirectory.join('/'), item.fullName || item.name),
      type: 'directory',
    })),
    ...directory.files.map((item) => ({
      name: item.name,
      path: joinPath(subdirectory.join('/'), item.fullName || item.name),
      type: 'file',
    })),
  ];
  const selectedItems = selectableItems.filter((item) => selectedKeys.has(itemKey(item)));
  const allItemsSelected = selectableItems.length > 0 && selectedItems.length === selectableItems.length;
  const someItemsSelected = selectedItems.length > 0 && !allItemsSelected;

  const updateSelection = (item, checked) => {
    const key = itemKey(item);
    setSelectedKeys((current) => {
      const next = new Set(current);
      if (checked) next.add(key);
      else next.delete(key);
      return next;
    });
  };

  const handleSelectAll = (_event, { checked }) => {
    setSelectedKeys(checked
      ? new Set(selectableItems.map(itemKey))
      : new Set());
  };

  const refreshAfterDelete = (results) => {
    const successful = results.filter((result) => result.succeeded);
    const failed = results.filter((result) => !result.succeeded);
    setOperationReport({ deleted: successful.length, failed });
    setSelectedKeys(new Set(failed.map((result) => itemKey({ path: result.path, type: result.type }))));
    setRefreshSequence((current) => current + 1);
  };

  const handleSingleDelete = (item) => {
    setOperationReport({ deleted: 1, failed: [] });
    setRefreshSequence((current) => current + 1);
  };

  if (!active) {
    return (
      <Header
        className="explorer-working-directory"
        size="small"
      >
        <Icon name="folder" />
        {'/' + root + '/'}
      </Header>
    );
  }

  return (
    <section className="system-files-explorer">
      <Header
        className="explorer-working-directory"
        size="small"
      >
        <Icon name="folder open" />
        {'/' + root + '/' + subdirectory.join('/')}
      </Header>

      {remoteFileManagement || directory.directories.length > 0 ? (
        <div
          aria-label={remoteFileManagement ? 'File management actions' : 'Directory information actions'}
          className="explorer-actions"
          role="group"
        >
          {remoteFileManagement ? (
            <>
              <Checkbox
                aria-label="Select all files and directories in this folder"
                checked={allItemsSelected}
                disabled={selectableItems.length === 0}
                indeterminate={someItemsSelected}
                onChange={handleSelectAll}
              />
              <span>{`${selectedItems.length} selected`}</span>
              <BulkDeleteControl
                items={selectedItems}
                onDeleted={refreshAfterDelete}
                root={root}
              />
            </>
          ) : null}
          {directory.directories.length > 0 ? (
            <Popup
              content="Calculate the size of every listed directory by totaling its files recursively. This reads directory contents but does not open or modify file data."
              on={['hover', 'focus']}
              position="top center"
              trigger={(
                <Button
                  disabled={loading}
                  loading={loading && includeDirectorySizes}
                  onClick={() => {
                    setIncludeDirectorySizes(true);
                    setRefreshSequence((current) => current + 1);
                  }}
                >
                  {includeDirectorySizes ? 'Refresh folder sizes' : 'Calculate folder sizes'}
                </Button>
              )}
            />
          ) : null}
        </div>
      ) : null}

      {operationReport?.deleted > 0 ? (
        <Message
          content={`Deleted ${operationReport.deleted} item${operationReport.deleted === 1 ? '' : 's'}.`}
          positive
          role="status"
        />
      ) : null}
      {operationReport?.failed?.length > 0 ? (
        <Message error role="alert">
          <Message.Header>{`Could not delete ${operationReport.failed.length} item${operationReport.failed.length === 1 ? '' : 's'}`}</Message.Header>
          <ul>
            {operationReport.failed.map((result) => (
              <li key={`${result.type}:${result.path}`}>
                {`${result.path}: ${getDeleteErrorMessage(result.error)}`}
              </li>
            ))}
          </ul>
        </Message>
      ) : null}

      {error ? (
        <Message
          error
          header="Could not load this directory"
          role="alert"
        >
          <p>{error}</p>
          <Popup
            content="Retry loading the current directory after the request error."
            on={['hover', 'focus']}
            position="top center"
            trigger={(
              <Button
                onClick={() => setRefreshSequence((current) => current + 1)}
                primary
              >
                <Icon name="refresh" />
                Try Again
              </Button>
            )}
          />
        </Message>
      ) : null}

      <div
        aria-label={`${root === 'downloads' ? 'Downloads' : 'Incomplete'} files and directories`}
        className="explorer-table-scroll"
        role="region"
        tabIndex={0}
      >
        <Table
          aria-label="Files and directories"
          className="unstackable explorer-table"
          size="large"
        >
          <Table.Header>
            <Table.Row>
              <Table.HeaderCell className="explorer-list-name">
                Name
              </Table.HeaderCell>
              <Table.HeaderCell className="explorer-list-date">
                Date Modified
              </Table.HeaderCell>
              <Table.HeaderCell className="explorer-list-size">
                Size
              </Table.HeaderCell>
              <Table.HeaderCell className="explorer-list-action">
                <div className="explorer-list-action-heading">
                  Actions
                </div>
              </Table.HeaderCell>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            <>
              {subdirectory.length > 0 && (
                <DirectoryRow
                  deletable={false}
                  fullName=".."
                  name=".."
                  onClick={upOneSubdirectory}
                  remoteFileManagement={remoteFileManagement}
                  root={root}
                  subdirectory={subdirectory}
                />
              )}
              {total === 0 ? (
                <Table.Row>
                  <Table.Cell colSpan={4}>
                    {loading
                      ? 'Loading files'
                      : error
                        ? 'Directory contents are unavailable'
                        : 'No files or directories'}
                  </Table.Cell>
                </Table.Row>
              ) : null}
              {directory.directories.map((item) => (
                <DirectoryRow
                  key={item.name}
                  onClick={() => select(item.name)}
                  onDeleted={() => setRefreshSequence((current) => current + 1)}
                  remoteFileManagement={remoteFileManagement}
                  root={root}
                  subdirectory={subdirectory}
                  selected={selectedKeys.has(itemKey({
                    path: joinPath(subdirectory.join('/'), item.fullName || item.name),
                    type: 'directory',
                  }))}
                  onSelectionChange={(checked) => updateSelection({
                    path: joinPath(subdirectory.join('/'), item.fullName || item.name),
                    type: 'directory',
                  }, checked)}
                  {...item}
                  onDeleted={handleSingleDelete}
                />
              ))}
              {directory.files.map((item) => (
                <FileRow
                  key={item.name}
                  onDeleted={() => setRefreshSequence((current) => current + 1)}
                  remoteFileManagement={remoteFileManagement}
                  root={root}
                  subdirectory={subdirectory}
                  selected={selectedKeys.has(itemKey({
                    path: joinPath(subdirectory.join('/'), item.fullName || item.name),
                    type: 'file',
                  }))}
                  onSelectionChange={(checked) => updateSelection({
                    path: joinPath(subdirectory.join('/'), item.fullName || item.name),
                    type: 'file',
                  }, checked)}
                  {...item}
                  onDeleted={handleSingleDelete}
                />
              ))}
            </>
          </Table.Body>
        </Table>
      </div>
    </section>
  );
};

export default Explorer;
