import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import {
  isStateCancellable,
  isStateRetryable,
  isStateSucceeded,
} from '../../lib/transfers';
import {
  applyHumanChallengeAutoResponse,
  canApplyHumanChallengeAutoResponse,
  getHumanChallengeAutoResponseEnabled,
  readStoredHumanChallengeAutoResponse,
  writeStoredHumanChallengeAutoResponse,
} from '../../lib/humanChallengeAutoResponse';
import { getDownloadExclusions } from '../../lib/downloadFilters';
import AppContext from '../AppContext';
import { Div, Nbsp, TooltipButton } from '../Shared';
import DownloadExclusionsModal from './DownloadExclusionsModal';
import ShrinkableDropdownButton from '../Shared/ShrinkableDropdownButton';
import React, { useContext, useEffect, useMemo, useState } from 'react';

import { Checkbox, Icon, Popup, Segment } from 'semantic-ui-react';

const getRetryableFiles = ({ files, retryOption }) => {
  switch (retryOption) {
    case 'Errored':
      return files.filter((file) =>
        [
          'Completed, TimedOut',
          'Completed, Errored',
          'Completed, Rejected',
          'Completed, Aborted',
        ].includes(file.state),
      );
    case 'Cancelled':
      return files.filter((file) => file.state === 'Completed, Cancelled');
    case 'All':
      return files.filter((file) => isStateRetryable(file.state));
    default:
      return [];
  }
};

const getCancellableFiles = ({ cancelOption, files }) => {
  switch (cancelOption) {
    case 'All':
      return files.filter((file) => isStateCancellable(file.state));
    case 'Queued':
      return files.filter((file) =>
        ['Queued, Locally', 'Queued, Remotely'].includes(file.state),
      );
    case 'In Progress':
      return files.filter((file) => file.state === 'InProgress');
    default:
      return [];
  }
};

const getRemovableFiles = ({ files, removeOption }) => {
  switch (removeOption) {
    case 'Succeeded':
      return files.filter((file) => isStateSucceeded(file.state));
    case 'Errored':
      return files.filter((file) =>
        [
          'Completed, TimedOut',
          'Completed, Errored',
          'Completed, Rejected',
          'Completed, Aborted',
        ].includes(file.state),
      );
    case 'Cancelled':
      return files.filter((file) => file.state === 'Completed, Cancelled');
    case 'Completed':
      return files.filter((file) => isStateSucceeded(file.state));
    default:
      return [];
  }
};

const TransfersHeader = ({
  acceleratedEnabled = false,
  autoReplaceEnabled = false,
  autoReplaceThreshold = 5,
  cancelling = false,
  direction,
  hideCompleted = true,
  onAcceleratedChange,
  onAutoReplaceChange,
  onCancelAll,
  onHideCompletedChange,
  onRemoveAll,
  onRetryAll,
  removing = false,
  retrying = false,
  server = { isConnected: true },
  totalCount = null,
  transfers,
}) => {
  const { language, t } = useInterfaceLanguage();
  const localizedText = (value) => <span lang={language} dir={language === 'ar' ? 'rtl' : 'ltr'}>{value}</span>;
  const appContext = useContext(AppContext) || {};
  const options = appContext.options || {};
  const [removeOption, setRemoveOption] = useState('Succeeded');
  const [cancelOption, setCancelOption] = useState('All');
  const [retryOption, setRetryOption] = useState('Errored');
  const [humanCheckAutoResponseEnabled, setHumanCheckAutoResponseEnabled] =
    useState(() =>
      getHumanChallengeAutoResponseEnabled(options) ||
      readStoredHumanChallengeAutoResponse(),
    );
  const [humanCheckSaving, setHumanCheckSaving] = useState(false);
  const [humanCheckError, setHumanCheckError] = useState(false);
  const [downloadFilterOpen, setDownloadFilterOpen] = useState(false);
  const [downloadExclusions, setDownloadExclusions] = useState(() =>
    getDownloadExclusions(options),
  );
  const canApplyHumanCheck = canApplyHumanChallengeAutoResponse(options);

  useEffect(() => {
    setDownloadExclusions(getDownloadExclusions(options));
  }, [options]);

  useEffect(() => {
    setHumanCheckAutoResponseEnabled(
      getHumanChallengeAutoResponseEnabled(options) ||
        readStoredHumanChallengeAutoResponse(),
    );
  }, [options]);

  const files = useMemo(() => {
    return transfers
      .reduce((accumulator, username) => {
        const allUserFiles = username.directories.reduce(
          (directoryAccumulator, directory) => {
            return directoryAccumulator.concat(directory.files);
          },
          [],
        );

        return accumulator.concat(allUserFiles);
      }, [])
      .filter((file) => file.direction.toLowerCase() === direction);
  }, [direction, transfers]);

  const empty = (totalCount ?? files.length) === 0;
  const retryableFiles = getRetryableFiles({ files, retryOption });
  const cancellableFiles = getCancellableFiles({ cancelOption, files });
  const removableFiles = getRemovableFiles({ files, removeOption });
  const useBulkClear =
    removeOption === 'Completed' || removeOption === 'Succeeded';
  const hasRemovableFiles = useBulkClear ? !empty : removableFiles.length > 0;
  const downloadFilterCount = downloadExclusions.filter((term) =>
    String(term).trim(),
  ).length;

  const setHumanCheckAutoResponse = async (enabled) => {
    setHumanCheckAutoResponseEnabled(enabled);
    writeStoredHumanChallengeAutoResponse(enabled);
    setHumanCheckError(false);

    if (!canApplyHumanCheck) {
      setHumanCheckError(true);
      return;
    }

    setHumanCheckSaving(true);
    try {
      await applyHumanChallengeAutoResponse(enabled);
    } catch {
      setHumanCheckError(true);
    } finally {
      setHumanCheckSaving(false);
    }
  };

  return (
    <>
      <Segment
        className="transfers-header-segment"
      >
        <div className="transfers-segment-icon">
          <Icon
            name={direction}
            size="large"
          />
        </div>
        <div className="transfers-header-actions">
          {direction === 'download' && (
            <TooltipButton
              aria-label={interfaceText("Open download filters")}
              className="download-filter-button"
              icon="filter"
              onClick={() => setDownloadFilterOpen(true)}
              size="small"
              title={interfaceText("Download filters")}
              tooltip="Block unwanted downloads by matching literal terms anywhere in remote filenames or folder paths."
             {...interfaceTextProps("Open download filters")}>
              {localizedText(downloadFilterCount > 0
                ? `${t('Download filters')} (${downloadFilterCount})`
                : t('Download filters'))}
            </TooltipButton>
          )}
          <Div
            className="transfers-header-buttons"
            hidden={empty}
          >
        <ShrinkableDropdownButton
          color="green"
          disabled={retrying || retryableFiles.length === 0 || !server.isConnected}
          hidden={direction === 'upload'}
          icon="redo"
          loading={retrying}
          mediaQuery="(max-width: 715px)"
          onChange={(_, data) => setRetryOption(data.value)}
          onClick={() => onRetryAll(retryableFiles)}
          menuLabel="Choose downloads to retry"
          options={[
            { key: 'errored', text: localizedText(t('Errored')), value: 'Errored' },
            { key: 'cancelled', text: localizedText(t('Cancelled')), value: 'Cancelled' },
            { key: 'all', text: localizedText(t('All')), value: 'All' },
          ]}
          tooltip="Retry every eligible download in the chosen status group. This sends new requests to Soulseek peers; use the arrow menu to choose Errored, Cancelled, or All."
        >
          {localizedText(`${t('Retry')} ${retryOption === 'All' ? t('All') : `${t('All')} ${t(retryOption)}`}`)}
        </ShrinkableDropdownButton>
        <Nbsp />
        <ShrinkableDropdownButton
          color="red"
          disabled={cancelling || cancellableFiles.length === 0}
          icon="x"
          loading={cancelling}
          mediaQuery="(max-width: 715px)"
          onChange={(_, data) => setCancelOption(data.value)}
          onClick={() =>
            onCancelAll(cancellableFiles)
          }
          menuLabel="Choose transfers to cancel"
          options={[
            { key: 'all', text: localizedText(t('All')), value: 'All' },
            { key: 'queued', text: localizedText(t('Queued')), value: 'Queued' },
            { key: 'inProgress', text: localizedText(t('In Progress')), value: 'In Progress' },
          ]}
          tooltip="Cancel transfers in the chosen state group to stop queued or active peer traffic. Use the arrow menu to choose All, Queued, or In Progress."
        >
          {localizedText(`${t('Cancel')} ${cancelOption === 'All' ? t('All') : `${t('All')} ${t(cancelOption)}`}`)}
        </ShrinkableDropdownButton>
        <Nbsp />
        <ShrinkableDropdownButton
          disabled={removing || !hasRemovableFiles}
          icon="trash alternate"
          loading={removing}
          mediaQuery="(max-width: 715px)"
          onChange={(_, data) => setRemoveOption(data.value)}
          onClick={() =>
            onRemoveAll(
              removableFiles,
              false,
              { useBulkClear },
            )
          }
          menuLabel="Choose transfer rows to remove"
          options={[
            { key: 'succeeded', text: localizedText(t('Succeeded')), value: 'Succeeded' },
            { key: 'errored', text: localizedText(t('Errored')), value: 'Errored' },
            { key: 'cancelled', text: localizedText(t('Cancelled')), value: 'Cancelled' },
            { key: 'completed', text: localizedText(t('Completed')), value: 'Completed' },
          ]}
          tooltip="Remove matching transfer rows from this list; completed files remain on disk. Use the arrow menu to choose which result group to remove."
        >
          {localizedText(`${t('Remove')} ${t('All')} ${t(removeOption)}`)}
        </ShrinkableDropdownButton>
        <Nbsp />
        <Popup
          content={interfaceText("Allow slow or stalled downloads to use verified alternate sources. Soulseek peers use sequential failover; true multipart chunking is reserved for trusted slskdN mesh peers.")}
          position="bottom right"
          trigger={
            <Checkbox
              checked={acceleratedEnabled}
              className="accelerated-downloads-toggle"
              disabled={!server.isConnected}
              hidden={direction === 'upload'}
              label={localizedText(t('Accelerated'))}
              onChange={(_, data) => onAcceleratedChange?.(data.checked)}
              toggle
            />
          }
         {...interfaceTextProps("Allow slow or stalled downloads to use verified alternate sources. Soulseek peers use sequential failover; true multipart chunking is reserved for trusted slskdN mesh peers.")}/>
        <Nbsp />
        <Popup
          content={interfaceText("Automatically find and replace stuck downloads with alternative sources. Replacements must be within {autoReplaceThreshold}% file size. This is separate from automatic retry of failed downloads; disable transfers.download.auto_retry.enabled to stop those retries.", { "autoReplaceThreshold": (autoReplaceThreshold) })}
          position="bottom right"
          trigger={
            <Checkbox
              checked={autoReplaceEnabled}
              className="auto-replace-toggle"
              disabled={!server.isConnected}
              hidden={direction === 'upload'}
              label={localizedText(t('Auto-Replace'))}
              onChange={(_, data) => onAutoReplaceChange?.(data.checked)}
              toggle
            />
          }
         {...interfaceTextProps("Automatically find and replace stuck downloads with alternative sources. Replacements must be within {autoReplaceThreshold}% file size. This is separate from automatic retry of failed downloads; disable transfers.download.auto_retry.enabled to stop those retries.")}/>
        <Nbsp />
        <Popup
          content={
            canApplyHumanCheck
              ? 'Automatically answer private messages that look like human-check or share-gate prompts. This helps with peer gates before or during downloads.'
              : 'Remember this preference in the browser. Enable remote configuration to apply it to the daemon so replies are sent even when you are not on this pane.'
          }
          position="bottom right"
          trigger={
            <Checkbox
              checked={humanCheckAutoResponseEnabled}
              className="human-check-auto-response-toggle"
              disabled={humanCheckSaving}
              hidden={direction === 'upload'}
              label={humanCheckError ? 'Auto Reply (local)' : 'Auto Reply'}
              onChange={(_, data) => setHumanCheckAutoResponse(data.checked)}
              toggle
            />
          }
        />
        <Nbsp />
        <Popup
          content={interfaceText("Hide successful 100% transfers from the list. Failed, aborted, timed-out, and rejected downloads stay visible for retry or review.")}
          position="bottom right"
          trigger={
            <Checkbox
              checked={hideCompleted}
              className="hide-completed-toggle"
              label={interfaceText("Hide Complete")}
              onChange={(_, data) => onHideCompletedChange?.(data.checked)}
              toggle
             {...interfaceTextProps("Hide Complete")}/>
          }
         {...interfaceTextProps("Hide successful 100% transfers from the list. Failed, aborted, timed-out, and rejected downloads stay visible for retry or review.")}/>
          </Div>
        </div>
      </Segment>
      <DownloadExclusionsModal
        onClose={() => setDownloadFilterOpen(false)}
        onSaved={setDownloadExclusions}
        open={downloadFilterOpen}
        options={options}
      />
    </>
  );
};

export default TransfersHeader;
