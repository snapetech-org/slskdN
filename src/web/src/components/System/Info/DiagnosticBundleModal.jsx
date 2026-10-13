import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { buildDiagnosticBundle } from '../../../lib/diagnosticBundle';
import React, { useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import {
  Button,
  Header,
  Icon,
  Message,
  Modal,
  Popup,
  TextArea,
} from 'semantic-ui-react';

const copyToClipboard = async (value) => {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return true;
  }

  return false;
};

const DiagnosticBundleModal = ({ options = {}, state = {} }) => {
  useInterfaceLanguage();
  const [open, setOpen] = useState(false);
  const bundle = useMemo(
    () =>
      buildDiagnosticBundle({
        options,
        state,
      }),
    [options, state],
  );

  const copyBundle = async () => {
    const copied = await copyToClipboard(bundle);

    if (copied) {
      toast.success(interfaceText("Diagnostic bundle copied"));
      return;
    }

    toast.info(interfaceText("Select the diagnostic bundle text to copy it manually"));
  };

  return (
    <>
      <Popup
        content={interfaceText("Open a redacted diagnostic bundle you can copy for support. Secrets, tokens, passwords, cookies, and API keys are removed.")}
        position="top center"
        trigger={
          <Button
            aria-label={interfaceText("Open diagnostic bundle")}
            disabled={!state}
            icon
            onClick={() => setOpen(true)}
           {...interfaceTextProps("Open diagnostic bundle")}>
            <Icon name="clipboard list" />
            <LocalizedText source={"Diagnostic Bundle"} /></Button>
        }
       {...interfaceTextProps("Open a redacted diagnostic bundle you can copy for support. Secrets, tokens, passwords, cookies, and API keys are removed.")}/>
      <Modal
        centered={false}
        closeIcon
        onClose={() => setOpen(false)}
        open={open}
        size="large"
      >
        <Modal.Header>
          <Icon name="clipboard list" />
          <LocalizedText source={"Diagnostic Bundle"} /></Modal.Header>
        <Modal.Content>
          <Message info>
            <Message.Header><LocalizedText source={"Redacted support snapshot"} /></Message.Header>
            <p>
              <LocalizedText source={"This bundle includes browser, route, setup-health summary, state, and option shape. It redacts secrets before display and does not contact the server."} /></p>
          </Message>
          <Header as="h4"><LocalizedText source={"Bundle"} /></Header>
          <TextArea
            aria-label={interfaceText("Redacted diagnostic bundle")}
            className="diagnostic-bundle-text"
            readOnly
            value={bundle}
           {...interfaceTextProps("Redacted diagnostic bundle")}/>
        </Modal.Content>
        <Modal.Actions>
          <Popup
            content={interfaceText("Copy the redacted diagnostic bundle to the clipboard.")}
            position="top center"
            trigger={
              <Button
                aria-label={interfaceText("Copy diagnostic bundle")}
                onClick={copyBundle}
                primary
               {...interfaceTextProps("Copy diagnostic bundle")}>
                <Icon name="copy" />
                <LocalizedText source={"Copy"} /></Button>
            }
           {...interfaceTextProps("Copy the redacted diagnostic bundle to the clipboard.")}/>
          <Popup
            content={interfaceText("Close the diagnostic bundle window without copying.")}
            position="top center"
            trigger={
              <Button
                aria-label={interfaceText("Close diagnostic bundle")}
                onClick={() => setOpen(false)}
               {...interfaceTextProps("Close diagnostic bundle")}>
                <LocalizedText source={"Close"} /></Button>
            }
           {...interfaceTextProps("Close the diagnostic bundle window without copying.")}/>
        </Modal.Actions>
      </Modal>
    </>
  );
};

export default DiagnosticBundleModal;
