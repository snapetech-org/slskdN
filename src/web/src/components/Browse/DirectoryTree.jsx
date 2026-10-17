import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import React, { memo, useCallback, useMemo, useState } from 'react';
import { List as WindowedList } from 'react-window';
import { Button, Icon, List, Popup } from 'semantic-ui-react';

const flattenVisibleDirectories = (nodes, expandedPaths) => {
  const rows = [];
  const pending = nodes.map((directory) => ({ directory, level: 0 })).reverse();

  while (pending.length > 0) {
    const row = pending.pop();
    rows.push(row);

    if (expandedPaths.has(row.directory.name) && row.directory.children?.length > 0) {
      for (let index = row.directory.children.length - 1; index >= 0; index--) {
        pending.push({ directory: row.directory.children[index], level: row.level + 1 });
      }
    }
  }

  return rows;
};

const DirectoryRow = memo(
  ({
    ariaAttributes,
    expandedPaths,
    index,
    onDownload,
    onToggleExpand,
    onSelect,
    rows,
    selectedDirectoryName,
    style,
  }) => {
    useInterfaceLanguage();
    const { directory, level } = rows[index];
    const isExpanded = expandedPaths.has(directory.name);
    const isActive = directory.name === selectedDirectoryName;
    const hasChildren = directory.children?.length > 0;
    const folderName = directory.name.split('\\').pop().split('/').pop();

    return (
      <List.Item
        {...ariaAttributes}
        style={{
          ...style,
          alignItems: 'center',
          boxSizing: 'border-box',
          display: 'flex',
          paddingLeft: level > 0 ? `${level}em` : 0,
          paddingBottom: 0,
          paddingTop: 0,
        }}
      >
        <List.Content>
          <div style={{ alignItems: 'center', display: 'flex', gap: '4px' }}>
            {hasChildren ? (
              <Popup
                content={interfaceText(isExpanded
                  ? 'Collapse {folder} to hide its subfolders.'
                  : 'Expand {folder} to show its subfolders.', { folder: folderName })}
                trigger={(
                  <button
                    aria-expanded={isExpanded}
                    aria-label={interfaceText(isExpanded ? 'Collapse {folder}' : 'Expand {folder}', { folder: folderName })}
                    onClick={() => onToggleExpand(directory.name)}
                    style={{
                      alignItems: 'center',
                      background: 'transparent',
                      border: 0,
                      color: 'inherit',
                      cursor: 'pointer',
                      display: 'inline-flex',
                      justifyContent: 'center',
                      padding: 0,
                      width: '16px',
                    }}
                    type="button"
                  >
                    <Icon name={isExpanded ? 'caret down' : 'caret right'} />
                  </button>
                )}
              />
            ) : (
              <span style={{ width: '16px' }} />
            )}

            <Icon
              className={directory.locked ? 'locked' : ''}
              name={
                directory.locked ? 'lock' : isExpanded ? 'folder open' : 'folder'
              }
              style={{ opacity: directory.locked ? 0.5 : 1 }}
            />

            <Popup
              content={interfaceText("Select folder {folderName} to view its contents in the share browser.", { "folderName": (folderName) })}
              trigger={(
                <button
                  onClick={() => onSelect(directory)}
                  style={{
                    background: 'transparent',
                    border: 0,
                    color: isActive ? '#2185d0' : 'inherit',
                    cursor: 'pointer',
                    font: 'inherit',
                    fontWeight: isActive ? 'bold' : 'normal',
                    margin: 0,
                    opacity: directory.locked ? 0.5 : 1,
                    padding: 0,
                    textAlign: 'left',
                  }}
                  type="button"
                >
                  {folderName}
                </button>
              )}
             {...interfaceTextProps("Select folder {folderName} to view its contents in the share browser.")}/>

            {level > 0 && (
              <Popup
                content={interfaceText("Download every file in {folderName} and its subdirectories to queue the whole folder tree at once.", { "folderName": (folderName) })}
                position="top center"
                trigger={(
                  <Button
                    aria-label={interfaceText("Download {folderName}", { "folderName": (folderName) })}
                    basic
                    compact
                    icon="download"
                    onClick={() => onDownload(directory)}
                    size="mini"
                   {...interfaceTextProps("Download {folderName}")}/>
                )}
               {...interfaceTextProps("Download every file in {folderName} and its subdirectories to queue the whole folder tree at once.")}/>
            )}

            {directory.fileCount > 0 && (
              <span
                style={{
                  background: '#555',
                  borderRadius: '10px',
                  color: '#fff',
                  fontSize: '0.75em',
                  marginLeft: '6px',
                  padding: '1px 6px',
                }}
              >
                {directory.fileCount}
              </span>
            )}
          </div>
        </List.Content>
      </List.Item>
    );
  },
);

DirectoryRow.displayName = 'DirectoryRow';

const DirectoryTree = ({ onDownload, onSelect, selectedDirectoryName, tree }) => {
  useInterfaceLanguage();
  const [expandedPaths, setExpandedPaths] = useState(new Set());

  const visibleDirectories = useMemo(
    () => flattenVisibleDirectories(tree, expandedPaths),
    [expandedPaths, tree],
  );

  const toggleExpand = useCallback((path) => {
    setExpandedPaths((previous) => {
      const updated = new Set(previous);

      if (updated.has(path)) {
        updated.delete(path);
      } else {
        updated.add(path);
      }

      return updated;
    });
  }, []);

  const selectDirectory = useCallback(
    (directory) => {
      onSelect(null, directory);
    },
    [onSelect],
  );

  const collapseAll = useCallback(() => {
    setExpandedPaths(new Set());
  }, []);

  const rowProps = useMemo(() => ({
    expandedPaths,
    onDownload,
    onSelect: selectDirectory,
    onToggleExpand: toggleExpand,
    rows: visibleDirectories,
    selectedDirectoryName,
  }), [
    expandedPaths,
    onDownload,
    selectDirectory,
    selectedDirectoryName,
    toggleExpand,
    visibleDirectories,
  ]);

  return (
    <div>
      <div
        style={{
          alignItems: 'center',
          borderBottom: '1px solid #333',
          display: 'flex',
          gap: '8px',
          marginBottom: '8px',
          paddingBottom: '8px',
        }}
      >
        <Popup
          content={interfaceText("Collapse every open folder to make the directory tree easier to scan.")}
          position="top center"
          trigger={(
            <Button compact onClick={collapseAll} size="tiny">
              <Icon name="compress" /> <LocalizedText source={"Collapse All"} /></Button>
          )}
         {...interfaceTextProps("Collapse every open folder to make the directory tree easier to scan.")}/>
      </div>

      <WindowedList
        className="ui list browse-folderlist-list"
        defaultHeight={400}
        defaultWidth={400}
        overscanCount={8}
        rowComponent={DirectoryRow}
        rowCount={visibleDirectories.length}
        rowHeight={36}
        rowProps={rowProps}
        style={{ height: 400, width: '100%' }}
      />
    </div>
  );
};

export default DirectoryTree;
