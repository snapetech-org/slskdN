import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
import {
  getYaml,
  getYamlLocation,
  updateYaml,
  validateYaml,
} from '../../../lib/options';
import { Div, PlaceholderSegment, Switch } from '../../Shared';
import CodeEditor from '../../Shared/CodeEditor';
import React, { useEffect, useRef, useState } from 'react';
import { Button, Icon, Message, Modal, Popup } from 'semantic-ui-react';

const getErrorText = (error) =>
  getApiErrorMessage(error, { t: interfaceText });

const EditModal = ({ onClose, open, theme }) => {
  useInterfaceLanguage();
  // eslint-disable-next-line react/hook-use-state
  const [{ error, loading }, setLoading] = useState({
    error: false,
    loading: true,
  });
  // eslint-disable-next-line react/hook-use-state
  const [{ isDirty, location, yaml }, setYaml] = useState({
    isDirty: false,
    location: undefined,
    yaml: undefined,
  });
  const [yamlError, setYamlError] = useState();
  const [updateError, setUpdateError] = useState();
  const [saving, setSaving] = useState(false);
  const validationRequestId = useRef(0);

  const get = async () => {
    setLoading({ error: false, loading: true });

    try {
      const [locationResult, yamlResult] = await Promise.all([
        getYamlLocation(),
        getYaml(),
      ]);

      setYaml({ isDirty: false, location: locationResult, yaml: yamlResult });
      setLoading({ error: false, loading: false });
    } catch (getError) {
      setLoading({
        error: getErrorText(getError),
        loading: false,
      });
    }
  };

  const validate = async (newYaml) => {
    const requestId = ++validationRequestId.current;
    try {
      const response = await validateYaml({ yaml: newYaml });
      if (requestId !== validationRequestId.current) return undefined;
      const error = typeof response === 'string'
        ? getErrorText({ response: { data: response } })
        : response
          ? getErrorText({ response: { data: response } })
          : undefined;
      setYamlError(error);
      return error;
    } catch (error) {
      if (requestId !== validationRequestId.current) return undefined;
      const message = getErrorText(error);
      setYamlError(message);
      return message;
    }
  };

  const update = async (newYaml) => {
    setYaml({ isDirty: true, location, yaml: newYaml });
    setYamlError(undefined);
    await validate(newYaml);
  };

  const save = async (newYaml) => {
    setUpdateError(undefined);
    setSaving(true);
    const nextYamlError = await validate(newYaml);

    if (!nextYamlError) {
      try {
        await updateYaml({ yaml: newYaml });
        onClose();
      } catch (nextUpdateError) {
        setUpdateError(getErrorText(nextUpdateError));
      }
    }
    setSaving(false);
  };

  useEffect(() => {
    if (open) {
      get();
    }
  }, [open]);

  return (
    <Modal
      onClose={onClose}
      open={open}
      size="large"
    >
      <Modal.Header>
        <Icon name="edit" />
        <LocalizedText source={"Edit Options"} /><Div hidden={loading}>
          <Message
            className="no-grow edit-code-header"
            warning
          >
            <Icon name="warning sign" />
            <LocalizedText source={"Editing"} />{" "}{location}
          </Message>
        </Div>
      </Modal.Header>
      <Modal.Content
        className="edit-code-content"
        scrolling
      >
        <Switch
          error={error && (
            <Message negative>
              <Message.Content>{error}</Message.Content>
              <Popup
                content={interfaceText("Retry loading the remote YAML and its source location.")}
                trigger={(
                  <Button onClick={get} primary>
                    <LocalizedText source={"Retry Options"} /></Button>
                )}
               {...interfaceTextProps("Retry loading the remote YAML and its source location.")}/>
            </Message>
          )}
          loading={loading && <PlaceholderSegment loading />}
        >
          <div
            {...{
              className:
                yamlError || updateError
                  ? 'edit-code-container-error'
                  : 'edit-code-container',
            }}
          >
            <CodeEditor
              editable={!saving}
              onChange={(value) => update(value)}
              style={{ minHeight: 500 }}
              theme={theme}
              value={yaml}
            />
          </div>
        </Switch>
      </Modal.Content>
      <Modal.Actions>
        {(yamlError || updateError) && (
          <Message
            className="no-grow left-align"
            negative
          >
            <Icon name="x" />
            {[yamlError, updateError].filter(Boolean).join(' ')}
          </Message>
        )}
        <Popup
          content={interfaceText("Validate the current YAML and save it to the remote configuration file.")}
          trigger={(
            <span>
              <Button
                disabled={!isDirty || saving || loading}
                loading={saving}
                onClick={() => save(yaml)}
                primary
              >
                <Icon name="save" />
                <LocalizedText source={"Save"} /></Button>
            </span>
          )}
         {...interfaceTextProps("Validate the current YAML and save it to the remote configuration file.")}/>
        <Popup
          content={interfaceText("Close the editor without applying unsaved YAML changes.")}
          trigger={(
            <Button
              negative
              onClick={onClose}
            >
              <Icon name="close" />
              <LocalizedText source={"Cancel"} /></Button>
          )}
         {...interfaceTextProps("Close the editor without applying unsaved YAML changes.")}>
        </Popup>
      </Modal.Actions>
    </Modal>
  );
};

export default EditModal;
