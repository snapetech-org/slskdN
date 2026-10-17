import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import * as optionsApi from '../../lib/options';
import {
  formatDownloadExclusions,
  getDownloadExclusions,
  getDownloadExclusionsValidationError,
  parseDownloadExclusions,
  setDownloadExclusionsInYaml,
} from '../../lib/downloadFilters';
import DownloadExclusionsField from '../Shared/DownloadExclusionsField';
import TooltipButton from '../Shared/TooltipButton';
import React, { useEffect, useRef, useState } from 'react';
import * as YAML from 'yaml';
import { Icon, Message, Modal } from 'semantic-ui-react';
import { toast } from 'react-toastify';

const getOption = (source, ...keys) => {
  for (const key of keys) {
    if (source && Object.prototype.hasOwnProperty.call(source, key)) {
      return source[key];
    }
  }

  return undefined;
};

const getErrorMessage = (error) =>
  getApiErrorMessage(error, { t: interfaceText }, 'Failed to save download filters.');

const DownloadExclusionsModal = ({
  onClose,
  onSaved,
  open,
  options = {},
}) => {
  useInterfaceLanguage();
  const remoteConfiguration = Boolean(
    getOption(options, 'remoteConfiguration', 'RemoteConfiguration'),
  );
  const [value, setValue] = useState(() =>
    formatDownloadExclusions(getDownloadExclusions(options)),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const wasOpen = useRef(false);

  useEffect(() => {
    if (open && !wasOpen.current) {
      setValue(formatDownloadExclusions(getDownloadExclusions(options)));
      setError(null);
    }

    wasOpen.current = open;
  }, [open, options]);

  const validationError = getDownloadExclusionsValidationError(value);

  const save = async () => {
    if (validationError) {
      setError(validationError);
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const yaml = await optionsApi.getYaml();
      const document = YAML.parseDocument(yaml || '{}');
      const exclusions = setDownloadExclusionsInYaml(
        document,
        parseDownloadExclusions(value),
      );

      await optionsApi.updateYaml({ yaml: document.toString() });
      onSaved?.(exclusions);
      toast.success(interfaceText("Download filters saved"));
      onClose();
    } catch (saveError) {
      setError(getErrorMessage(saveError));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      onClose={onClose}
      open={open}
      size="small"
    >
      <Modal.Header>
        <Icon name="filter" />
        <LocalizedText source={"Download filters"} /></Modal.Header>
      <Modal.Content>
        <p>
          <LocalizedText source={"Prevent unwanted files from being downloaded by blocking literal terms found anywhere in remote filenames or folder paths. This global filter applies to new downloads, retries, replacements, wishlist downloads, peer previews, pod downloads, and multi-source transfers."} /></p>
        {!remoteConfiguration && (
          <Message
            info
            size="small"
          >
            <LocalizedText source={"Remote configuration is disabled. You can review the current filters, but saving them requires remote configuration to be enabled."} /></Message>
        )}
        {error && (
          <Message
            negative
            size="small"
          >
            {error}
          </Message>
        )}
        <DownloadExclusionsField
          disabled={!remoteConfiguration || saving}
          onChange={(nextValue) => {
            setValue(nextValue);
            setError(null);
          }}
          value={value}
        />
        {validationError && (
          <Message
            negative
            size="small"
          >
            {validationError}
          </Message>
        )}
      </Modal.Content>
      <Modal.Actions>
        <TooltipButton
          disabled={saving}
          onClick={onClose}
          title={interfaceText("Cancel download filter changes")}
          tooltip="Close this editor without saving the terms you changed."
         {...interfaceTextProps("Cancel download filter changes")}>
          <LocalizedText source={"Cancel"} /></TooltipButton>
        <TooltipButton
          disabled={!remoteConfiguration || saving || Boolean(validationError)}
          loading={saving}
          onClick={save}
          primary
          title={interfaceText("Save download filters")}
          tooltip="Apply these terms globally to future and active downloads."
         {...interfaceTextProps("Save download filters")}>
          <LocalizedText source={"Save filters"} /></TooltipButton>
      </Modal.Actions>
    </Modal>
  );
};

export default DownloadExclusionsModal;
