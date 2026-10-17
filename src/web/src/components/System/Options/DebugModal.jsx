import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
import { getCurrentDebugView } from '../../../lib/options';
import { CodeEditor, PlaceholderSegment, Switch } from '../../Shared';
import React, { useEffect, useRef, useState } from 'react';
import { Button, Icon, Message, Modal, Popup } from 'semantic-ui-react';

const getErrorText = (error) =>
  getApiErrorMessage(error, { t: interfaceText }, 'Could not load the debug view.');

const DebugModal = ({ onClose, open, theme }) => {
  useInterfaceLanguage();
  const [loading, setLoading] = useState(true);
  const [debugView, setDebugView] = useState();
  const [error, setError] = useState();
  const requestId = useRef(0);

  const get = async () => {
    const nextRequestId = ++requestId.current;
    setLoading(true);
    setError(undefined);

    try {
      const result = await getCurrentDebugView();
      if (nextRequestId === requestId.current) setDebugView(result);
    } catch (caught) {
      if (nextRequestId === requestId.current) setError(getErrorText(caught));
    } finally {
      if (nextRequestId === requestId.current) setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      get();
    }
    return () => {
      requestId.current += 1;
    };
  }, [open]);

  return (
    <Modal
      onClose={onClose}
      open={open}
      size="large"
    >
      <Modal.Header>
        <Icon name="bug" />
        <LocalizedText source={"Options (Debug View)"} /></Modal.Header>
      <Modal.Content
        className="debug-view-content"
        scrolling
      >
        <Switch loading={loading && <PlaceholderSegment loading />}>
          {error ? (
            <Message negative>
              <Message.Content>{error}</Message.Content>
              <Popup
                content={interfaceText("Retry loading the current debug view.")}
                trigger={(
                  <Button onClick={get} primary>
                    <LocalizedText source={"Retry Debug View"} /></Button>
                )}
               {...interfaceTextProps("Retry loading the current debug view.")}/>
            </Message>
          ) : (
            <CodeEditor
              basicSetup={false}
              editable={false}
              style={{ minHeight: 500 }}
              theme={theme}
              value={debugView}
            />
          )}
        </Switch>
      </Modal.Content>
      <Modal.Actions>
        <Popup
          content={interfaceText("Close the debug view and return to Options.")}
          trigger={<Button onClick={onClose}><LocalizedText source={"Close"} /></Button>}
         {...interfaceTextProps("Close the debug view and return to Options.")}/>
      </Modal.Actions>
    </Modal>
  );
};

export default DebugModal;
