import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { deleteDirectory, deleteFile, list } from '../../../lib/files';
import { formatBytes, formatDate } from '../../../lib/util';
import React, { useEffect, useRef, useState } from 'react';
import { Button, Header, Icon, Message, Modal, Popup, Table } from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);
const emptyDirectory = { directories: [], files: [] };

const getErrorMessage = (error, fallback) => {
  const response = error?.response?.data;
  if (typeof response === 'string' && response.trim()) {
    return response;
  }

  return response?.message || error?.message || fallback;
};

const DeleteControl = ({ fullName, isDirectory, onDeleted, path, root }) => {
  useInterfaceLanguage();
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
      onDeleted();
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
        content={interfaceText("Open confirmation to permanently delete {itemType} '{fullName}'.", { "itemType": (itemType), "fullName": (fullName) })}
        on={['hover', 'focus']}
        position="top center"
        trigger={(
          <Button
            aria-label={interfaceText("Delete {itemType} {fullName}", { "itemType": (itemType), "fullName": (fullName) })}
            basic
            icon="trash alternate"
            onClick={() => {
              setError(null);
              setOpen(true);
            }}
            size="small"
           {...interfaceTextProps("Delete {itemType} {fullName}")}/>
        )}
       {...interfaceTextProps("Open confirmation to permanently delete {itemType} '{fullName}'.")}/>
      <Modal
        onClose={() => !deleting && setOpen(false)}
        open={open}
        size="small"
      >
        <Modal.Header>
          <Icon name="trash alternate" />
          {interfaceText("Delete {itemType}", { "itemType": (itemType) })}
        </Modal.Header>
        <Modal.Content>
          <p>{interfaceText("Are you sure you want to permanently delete '{fullName}'?", { "fullName": (fullName) })}</p>
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
            content={interfaceText("Permanently delete this {itemType}. This action cannot be undone.", { "itemType": (itemType) })}
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
           {...interfaceTextProps("Permanently delete this {itemType}. This action cannot be undone.")}/>
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
      {length ? formatBytes(length) : ''}
    </Table.Cell>
    <Table.Cell className="explorer-list-action">
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
  modifiedAt,
  name,
  onClick = () => {},
  onDeleted,
  remoteFileManagement,
  root,
  subdirectory,
}) => {
  useInterfaceLanguage();
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
      <Table.Cell className="explorer-list-size" />
      <Table.Cell className="explorer-list-action">
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

const Explorer = ({ active = true, remoteFileManagement, root }) => {
  useInterfaceLanguage();
  const [directory, setDirectory] = useState(emptyDirectory);
  const [subdirectory, setSubdirectory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
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
        const result = await list({
          root,
          subdirectory: subdirectory.join('/'),
        });
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
  }, [active, refreshSequence, root, subdirectory]);

  const select = (path) => {
    setSubdirectory((current) => [...current, path]);
  };

  const upOneSubdirectory = () => {
    setSubdirectory((current) => current.slice(0, -1));
  };

  const total = directory.directories.length + directory.files.length;

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

      {error ? (
        <Message
          error
          header={interfaceText("Could not load this directory")}
          role="alert"
         {...interfaceTextProps("Could not load this directory")}>
          <p>{error}</p>
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
        aria-label={`${root === 'downloads' ? 'Downloads' : 'Incomplete'} files and directories`}
        className="explorer-table-scroll"
        role="region"
        tabIndex={0}
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
                <LocalizedText source={"Actions"} /></Table.HeaderCell>
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
                  {...item}
                />
              ))}
              {directory.files.map((item) => (
                <FileRow
                  key={item.name}
                  onDeleted={() => setRefreshSequence((current) => current + 1)}
                  remoteFileManagement={remoteFileManagement}
                  root={root}
                  subdirectory={subdirectory}
                  {...item}
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
