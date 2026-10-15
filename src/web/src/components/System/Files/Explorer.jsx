import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
import { deleteDirectory, deleteFile, deleteItems, list } from '../../../lib/files';
import { formatRegionalNumber, useRegionalLocale } from '../../../lib/regionalFormat';
import { formatBytes, formatDate } from '../../../lib/util';
import React, { useEffect, useRef, useState } from 'react';
import { Button, Checkbox, Header, Icon, Message, Modal, Popup, Table } from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);
const emptyDirectory = { directories: [], files: [] };
const itemKey = ({ path, type }) => `${type}:${path}`;
const joinPath = (...segments) => segments.filter(Boolean).join('/');

const getErrorMessage = (error, fallback) =>
  getApiErrorMessage(error, { t: interfaceText }, fallback);

const getDeleteErrorSource = (error) => ({
  'access-denied': 'Access was denied',
  'delete-failed': 'The file system could not delete this item',
  'not-found': 'The item no longer exists',
}[error] || 'The item could not be deleted');

const DeleteControl = ({ fullName, isDirectory, onDeleted, path, root }) => {
  useInterfaceLanguage();
  const [open, setOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState(null);
  const itemType = isDirectory ? 'directory' : 'file';
  const itemTypeLabel = interfaceText(isDirectory ? 'directory' : 'file');

  const remove = async () => {
    setDeleting(true);
    setError(null);

    try {
      const removeItem = isDirectory ? deleteDirectory : deleteFile;
      await removeItem({ path, root });
      setOpen(false);
      onDeleted({ name: fullName, type: itemType });
    } catch (error_) {
      setError(getErrorMessage(error_, `Unable to delete this ${itemType}.`));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <>
      <Popup
        content={interfaceText("Open confirmation to permanently delete {itemType} '{fullName}'.", { itemType: itemTypeLabel, fullName })}
        on={['hover', 'focus']}
        position="top center"
        trigger={(
          <Button
            aria-label={interfaceText("Delete {itemType} {fullName}", { itemType: itemTypeLabel, fullName })}
            basic
            icon="trash alternate"
            onClick={() => {
              setError(null);
              setOpen(true);
            }}
            size="small"
           {...interfaceTextProps("Delete {itemType} {fullName}", { itemType: itemTypeLabel, fullName })}/>
        )}
       {...interfaceTextProps("Open confirmation to permanently delete {itemType} '{fullName}'.", { itemType: itemTypeLabel, fullName })}/>
      <Modal
        onClose={() => !deleting && setOpen(false)}
        open={open}
        size="small"
      >
        <Modal.Header>
          <Icon name="trash alternate" />
          <LocalizedText source="Delete {itemType}" values={{ itemType: itemTypeLabel }} />
        </Modal.Header>
        <Modal.Content>
          <p><LocalizedText source="Are you sure you want to permanently delete '{fullName}'?" values={{ fullName }} /></p>
          {error ? (
            <Message
              error
              role="alert"
            ><LocalizedText source={error} values={{ itemType: itemTypeLabel }} /></Message>
          ) : null}
        </Modal.Content>
        <Modal.Actions>
          <Popup
            content={interfaceText("Close this confirmation without deleting the item.")}
            on={['hover', 'focus']}
            trigger={(
              <Button
                disabled={deleting}
                onClick={() => setOpen(false)}
              >
                <LocalizedText source={"Cancel"} /></Button>
            )}
           {...interfaceTextProps("Close this confirmation without deleting the item.")}/>
          <Popup
            content={<LocalizedText source="Permanently delete this {itemType}. This action cannot be undone." values={{ itemType: itemTypeLabel }} />}
            on={['hover', 'focus']}
            trigger={(
              <Button
                disabled={deleting}
                loading={deleting}
                negative
                onClick={remove}
              >
                <LocalizedText source={"Delete"} /></Button>
            )}
           {...interfaceTextProps("Permanently delete this {itemType}. This action cannot be undone.", { itemType: itemTypeLabel })}/>
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
}) => {
  const selectionSource = 'Select file {fullName}';
  const selectionLabel = interfaceText(selectionSource, { fullName });
  return (
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
          aria-label={selectionLabel}
          {...interfaceTextProps(selectionSource, { fullName })}
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
};

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
  useInterfaceLanguage();
  const isParent = name === '..';
  const descriptionSource = isParent
    ? 'Go up one directory.'
    : 'Open the {name} directory.';
  const description = interfaceText(descriptionSource, { name });
  const selectionSource = 'Select directory {fullName}';

  return (
    <Table.Row key={name}>
      <Table.Cell className="explorer-list-name">
        <Popup
          content={description}
          {...interfaceTextProps(descriptionSource, { name })}
          on={['hover', 'focus']}
          position="top left"
          trigger={(
            <Button
              aria-label={description}
              {...interfaceTextProps(descriptionSource, { name })}
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
            aria-label={interfaceText(selectionSource, { fullName })}
            {...interfaceTextProps(selectionSource, { fullName })}
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
  const regionalLocale = useRegionalLocale();
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
        content={<LocalizedText source="Permanently delete the selected files and directories. Selected directories are removed with their contents." />}
        {...interfaceTextProps('Permanently delete the selected files and directories. Selected directories are removed with their contents.')}
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
            <LocalizedText
              source="Delete selected ({count})"
              values={{ count: formatRegionalNumber(items.length, undefined, regionalLocale) }}
            />
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
          <LocalizedText source="Delete selected items" />
        </Modal.Header>
        <Modal.Content>
          <p>
            <LocalizedText
              source="Permanently delete {count} selected items? Directories will be deleted recursively."
              values={{ count: formatRegionalNumber(items.length, undefined, regionalLocale) }}
            />
          </p>
          <ul className="explorer-delete-preview">
            {items.slice(0, 8).map((item) => (
              <li key={`${item.type}:${item.path}`}>
                <strong><LocalizedText source={item.type === 'directory' ? 'Directory' : 'File'} /></strong>
                {' '}
                {item.path}
              </li>
            ))}
          </ul>
          {items.length > 8 ? (
            <p>
              <LocalizedText
                source="And {count} more items."
                values={{ count: formatRegionalNumber(items.length - 8, undefined, regionalLocale) }}
              />
            </p>
          ) : null}
          {error ? <Message error role="alert"><LocalizedText source={error} /></Message> : null}
        </Modal.Content>
        <Modal.Actions>
          <Popup
            content={<LocalizedText source="Close this confirmation without deleting any items." />}
            {...interfaceTextProps('Close this confirmation without deleting any items.')}
            on={['hover', 'focus']}
            trigger={(
              <Button disabled={deleting} onClick={() => setOpen(false)}>
                <LocalizedText source="Cancel" />
              </Button>
            )}
          />
          <Popup
            content={<LocalizedText source="Delete every listed file and directory. This action cannot be undone." />}
            {...interfaceTextProps('Delete every listed file and directory. This action cannot be undone.')}
            on={['hover', 'focus']}
            trigger={(
              <Button
                disabled={deleting}
                loading={deleting}
                negative
                onClick={remove}
              >
                <LocalizedText
                  source="Delete {count} items"
                  values={{ count: formatRegionalNumber(items.length, undefined, regionalLocale) }}
                />
              </Button>
            )}
          />
        </Modal.Actions>
      </Modal>
    </>
  );
};

const Explorer = ({ active = true, remoteFileManagement, root }) => {
  useInterfaceLanguage();
  const regionalLocale = useRegionalLocale();
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
          aria-label={interfaceText(remoteFileManagement ? 'File management actions' : 'Directory information actions')}
          className="explorer-actions"
          role="group"
          {...interfaceTextProps(remoteFileManagement ? 'File management actions' : 'Directory information actions')}
        >
          {remoteFileManagement ? (
            <>
              <Checkbox
                aria-label={interfaceText('Select all files and directories in this folder')}
                {...interfaceTextProps('Select all files and directories in this folder')}
                checked={allItemsSelected}
                disabled={selectableItems.length === 0}
                indeterminate={someItemsSelected}
                onChange={handleSelectAll}
              />
              <span>
                <LocalizedText
                  source="{count} selected"
                  values={{ count: formatRegionalNumber(selectedItems.length, undefined, regionalLocale) }}
                />
              </span>
              <BulkDeleteControl
                items={selectedItems}
                onDeleted={refreshAfterDelete}
                root={root}
              />
            </>
          ) : null}
          {directory.directories.length > 0 ? (
            <Popup
              content={<LocalizedText source="Calculate the size of every listed directory recursively. This only reads directory contents; it does not open or modify file data." />}
              {...interfaceTextProps('Calculate the size of every listed directory recursively. This only reads directory contents; it does not open or modify file data.')}
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
                  <LocalizedText source={includeDirectorySizes ? 'Refresh folder sizes' : 'Calculate folder sizes'} />
                </Button>
              )}
            />
          ) : null}
        </div>
      ) : null}

      {operationReport?.deleted > 0 ? (
        <Message
          positive
          role="status"
        >
          <LocalizedText
            source={operationReport.deleted === 1 ? 'Deleted 1 item.' : 'Deleted {count} items.'}
            values={{ count: formatRegionalNumber(operationReport.deleted, undefined, regionalLocale) }}
          />
        </Message>
      ) : null}
      {operationReport?.failed?.length > 0 ? (
        <Message error role="alert">
          <Message.Header>
            <LocalizedText
              source={operationReport.failed.length === 1 ? 'Could not delete 1 item' : 'Could not delete {count} items'}
              values={{ count: formatRegionalNumber(operationReport.failed.length, undefined, regionalLocale) }}
            />
          </Message.Header>
          <ul>
            {operationReport.failed.map((result) => (
              <li key={`${result.type}:${result.path}`}>
                <LocalizedText
                  source="{path}: {error}"
                  values={{ path: result.path, error: interfaceText(getDeleteErrorSource(result.error)) }}
                />
              </li>
            ))}
          </ul>
        </Message>
      ) : null}

      {error ? (
        <Message
          error
          header={interfaceText("Could not load this directory")}
          role="alert"
         {...interfaceTextProps("Could not load this directory")}>
          <p><LocalizedText source={error} /></p>
          <Popup
            content={interfaceText("Retry loading the current directory after the request error.")}
            on={['hover', 'focus']}
            position="top center"
            trigger={(
              <Button
                onClick={() => setRefreshSequence((current) => current + 1)}
                primary
              >
                <Icon name="refresh" />
                <LocalizedText source={"Try Again"} /></Button>
            )}
           {...interfaceTextProps("Retry loading the current directory after the request error.")}/>
        </Message>
      ) : null}

      <div
        aria-label={interfaceText('Files and directories')}
        className="explorer-table-scroll"
        role="region"
        tabIndex={0}
        {...interfaceTextProps('Files and directories')}
      >
        <Table
          aria-label={interfaceText("Files and directories")}
          className="unstackable explorer-table"
          size="large"
         {...interfaceTextProps("Files and directories")}>
          <Table.Header>
            <Table.Row>
              <Table.HeaderCell className="explorer-list-name">
                <LocalizedText source={"Name"} /></Table.HeaderCell>
              <Table.HeaderCell className="explorer-list-date">
                <LocalizedText source={"Date Modified"} /></Table.HeaderCell>
              <Table.HeaderCell className="explorer-list-size">
                <LocalizedText source={"Size"} /></Table.HeaderCell>
              <Table.HeaderCell className="explorer-list-action">
                <div className="explorer-list-action-heading">
                  <LocalizedText source={"Actions"} />
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
                      ? <LocalizedText source={"Loading files"} />
                      : error
                        ? <LocalizedText source="Directory contents are unavailable" />
                        : <LocalizedText source="No files or directories" />}
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
