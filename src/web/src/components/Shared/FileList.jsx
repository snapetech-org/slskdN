import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import {
  formatAttributes,
  formatBytes,
  formatSeconds,
  getFileName,
} from '../../lib/util';
import React, { useMemo, useState } from 'react';
import TooltipButton from './TooltipButton';

import { Checkbox, Header, Icon, List, Table } from 'semantic-ui-react';

const FileList = ({
  directoryName,
  disabled,
  files,
  footer,
  locked,
  onClose,
  onSelectionChange,
}) => {
  const { t, languageFor, directionFor } = useInterfaceLanguage();
  const localized = (source, parameters) => (
    <span lang={languageFor(source)} dir={directionFor(source)}>
      {t(source, parameters)}
    </span>
  );
  const [folded, setFolded] = useState(false);
  const [lastSelectedIndex, setLastSelectedIndex] = useState(null);
  const sortedFiles = useMemo(
    () =>
      files
        ? [...files].sort((a, b) => (a.filename > b.filename ? 1 : -1))
        : [],
    [files],
  );
  const allSelected =
    sortedFiles.length > 0 && sortedFiles.every((file) => file.selected);
  const handleSelectionChange = (event, file, index, checked) => {
    if (
      event.shiftKey &&
      lastSelectedIndex !== null &&
      lastSelectedIndex !== index
    ) {
      const start = Math.min(lastSelectedIndex, index);
      const end = Math.max(lastSelectedIndex, index);
      sortedFiles
        .slice(start, end + 1)
        .forEach((rangeFile) => onSelectionChange(rangeFile, checked));
    } else {
      onSelectionChange(file, checked);
    }

    setLastSelectedIndex(index);
  };

  return (
    <div
      className="filelist"
      style={{ opacity: locked ? 0.5 : 1 }}
    >
      <Header
        className="filelist-header"
        size="small"
      >
        <div className="filelist-title">
          <TooltipButton
            aria-label={locked
              ? '{directory} is locked'
              : folded ? 'Expand {directory}' : 'Collapse {directory}'}
            basic
            className="filelist-action-button"
            compact
            disabled={locked}
            icon
            parameters={{ directory: directoryName }}
            lang={languageFor(locked
              ? '{directory} is locked'
              : folded ? 'Expand {directory}' : 'Collapse {directory}')}
            dir={directionFor(locked
              ? '{directory} is locked'
              : folded ? 'Expand {directory}' : 'Collapse {directory}')}
            onClick={() => setFolded(!folded)}
            tooltip={locked
              ? 'Directory {directory} is locked by the peer and cannot be expanded.'
              : folded
                ? 'Show the files inside {directory}.'
                : 'Hide the files inside {directory} while keeping this result open.'}
          >
            <Icon
              name={locked ? 'lock' : folded ? 'folder' : 'folder open'}
              size="large"
            />
          </TooltipButton>
          {directoryName}

          {Boolean(onClose) && (
            <TooltipButton
              aria-label={t('Close {directory} file list', { directory: directoryName })}
              basic
              className="close-button"
              compact
              icon
              parameters={{ directory: directoryName }}
              onClick={() => onClose()}
              tooltip="Close the {directory} file list and return to the surrounding search results."
              lang={languageFor('Close the {directory} file list and return to the surrounding search results.')}
              dir={directionFor('Close the {directory} file list and return to the surrounding search results.')}
              title={t('Close the {directory} file list and return to the surrounding search results.', { directory: directoryName })}
            >
              <Icon color="red" name="close" />
            </TooltipButton>
          )}
        </div>
      </Header>
      {!folded && sortedFiles.length > 0 && (
        <List>
          <List.Item>
            <Table className="filelist-table">
              <Table.Header>
                <Table.Row>
                  <Table.HeaderCell className="filelist-selector">
                    <Checkbox
                      aria-label={t('Select all files in {directory}', { directory: directoryName })}
                      lang={languageFor('Select all files in {directory}')}
                      dir={directionFor('Select all files in {directory}')}
                      checked={allSelected}
                      disabled={disabled}
                      fitted
                      onChange={(event, data) =>
                        sortedFiles.map((f) => onSelectionChange(f, data.checked))
                      }
                    />
                  </Table.HeaderCell>
                  <Table.HeaderCell className="filelist-filename">
                    {localized('File')}
                  </Table.HeaderCell>
                  <Table.HeaderCell className="filelist-size">
                    {localized('Size')}
                  </Table.HeaderCell>
                  <Table.HeaderCell className="filelist-attributes">
                    {localized('Attributes')}
                  </Table.HeaderCell>
                  <Table.HeaderCell className="filelist-length">
                    {localized('Length')}
                  </Table.HeaderCell>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {sortedFiles.map((f, index) => (
                  <Table.Row key={f.filename}>
                    <Table.Cell className="filelist-selector">
                      <Checkbox
                        aria-label={t('Select {filename}', { filename: f.filename })}
                        lang={languageFor('Select {filename}')}
                        dir={directionFor('Select {filename}')}
                        checked={f.selected}
                        disabled={disabled}
                        fitted
                        onChange={(event, data) =>
                          handleSelectionChange(event, f, index, data.checked)
                        }
                      />
                    </Table.Cell>
                    <Table.Cell className="filelist-filename">
                      {locked ? <Icon name="lock" /> : ''}
                      {getFileName(f.filename)}
                    </Table.Cell>
                    <Table.Cell className="filelist-size">
                      {formatBytes(f.size)}
                    </Table.Cell>
                    <Table.Cell className="filelist-attributes">
                      {formatAttributes(f)}
                    </Table.Cell>
                    <Table.Cell className="filelist-length">
                      {formatSeconds(f.length)}
                    </Table.Cell>
                  </Table.Row>
                ))}
              </Table.Body>
              {footer && (
                <Table.Footer fullWidth>
                  <Table.Row>
                    <Table.HeaderCell colSpan="5">{footer}</Table.HeaderCell>
                  </Table.Row>
                </Table.Footer>
              )}
            </Table>
          </List.Item>
        </List>
      )}
    </div>
  );
};

export default FileList;
