import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getVersion, restart, shutdown } from '../../../lib/application';
import DiagnosticBundleModal from './DiagnosticBundleModal';
import SetupHealthCheckModal from './SetupHealthCheckModal';
import {
  CodeEditor,
  LoaderSegment,
  ShrinkableButton,
  Switch,
} from '../../Shared';
import SystemOverview from './SystemOverview';
import React, { useEffect, useState } from 'react';
import { Button, Divider, Icon, Modal, Popup } from 'semantic-ui-react';
import YAML from 'yaml';

const ConfirmApplicationAction = ({
  actionLabel,
  children,
  disabled,
  icon,
  mediaQuery,
  onConfirm,
  prompt,
  title,
  triggerColor,
  triggerNegative,
}) => {
  useInterfaceLanguage();
  const [open, setOpen] = useState(false);

  const confirm = () => {
    setOpen(false);
    onConfirm();
  };

  return (
    <>
      <ShrinkableButton
        color={triggerColor}
        disabled={disabled}
        icon={icon}
        mediaQuery={mediaQuery}
        negative={triggerNegative}
        onClick={() => setOpen(true)}
        tooltip={title}
      >
        {children || actionLabel}
      </ShrinkableButton>
      <Modal
        centered
        onClose={() => setOpen(false)}
        open={open}
        size="mini"
      >
        <Modal.Header>
          <Icon name={icon} />
          <LocalizedText source={"Confirm"} />{" "}{actionLabel}
        </Modal.Header>
        <Modal.Content>{prompt}</Modal.Content>
        <Modal.Actions>
          <Popup
            content={interfaceText("Close this prompt without changing the application state.")}
            trigger={(
              <Button onClick={() => setOpen(false)}>
                <LocalizedText source={"Cancel"} /></Button>
            )}
           {...interfaceTextProps("Close this prompt without changing the application state.")}/>
          <Popup
            content={interfaceText("{actionLabel} the application.", { "actionLabel": (actionLabel) })}
            trigger={(
              <Button negative onClick={confirm}>
                {actionLabel}
              </Button>
            )}
           {...interfaceTextProps("{actionLabel} the application.")}/>
        </Modal.Actions>
      </Modal>
    </>
  );
};

const Info = ({ options, state, theme }) => {
  useInterfaceLanguage();
  const [contents, setContents] = useState();

  useEffect(() => {
    let active = true;
    const timeout = window.setTimeout(() => {
      if (!active) return;

      setContents(
        YAML.stringify(state, { simpleKeys: true, sortMapEntries: false }),
      );
    }, 250);

    return () => {
      active = false;
      window.clearTimeout(timeout);
    };
  }, [state]);

  const { pendingRestart } = state;

  return (
    <>
      <SystemOverview state={state} />
      <div className="header-buttons">
        <div style={{ float: 'left' }}>
          <ShrinkableButton
            icon="refresh"
            mediaQuery="(max-width: 686px)"
            onClick={() => getVersion({ forceCheck: true })}
            primary
            tooltip="Check GitHub for the latest slskdN release."
          >
            <LocalizedText source={"Check for Updates"} /></ShrinkableButton>
          {/* Neutral, not amber — this is an optional external upsell from
              Soulseek itself, not an app action that needs to alarm anyone. */}
          <ShrinkableButton
            disabled={!state?.user?.username}
            icon="star"
            mediaQuery="(max-width: 686px)"
            onClick={() =>
              window.open(
                `http://www.slsknet.org/qtlogin.php?username=${state?.user?.username}`,
                '_blank',
              )
            }
            tooltip="Review Soulseek privilege options for this account."
          >
            <LocalizedText source={"Get Privileges"} /></ShrinkableButton>
          <DiagnosticBundleModal
            options={options}
            state={state}
          />
          <SetupHealthCheckModal
            options={options}
            state={state}
          />
        </div>
        <ConfirmApplicationAction
          actionLabel="Shut Down"
          icon="shutdown"
          mediaQuery="(max-width: 686px)"
          onConfirm={shutdown}
          prompt="Shutting down stops the application. You'll need to start it manually to use it again."
          title={interfaceText("Shut down the application. Use this when you need to stop the server completely.")}
         {...interfaceTextProps("Shut down the application. Use this when you need to stop the server completely.")}/>
        <ConfirmApplicationAction
          actionLabel="Restart"
          icon="redo"
          mediaQuery="(max-width: 686px)"
          onConfirm={restart}
          prompt="Restarting briefly interrupts the web app and Soulseek connections."
          title={interfaceText("Restart slskdN to apply pending changes or recover the application.")}
          triggerColor={pendingRestart ? 'yellow' : undefined}
          triggerNegative={!pendingRestart}
         {...interfaceTextProps("Restart slskdN to apply pending changes or recover the application.")}/>
      </div>
      <Divider />
      <details className="system-state-details">
        <summary><LocalizedText source={"Application state (advanced)"} /></summary>
        <Switch loading={!contents && <LoaderSegment />}>
          <CodeEditor
            basicSetup={false}
            editable={false}
            theme={theme}
            value={contents}
          />
        </Switch>
      </details>
    </>
  );
};

export default Info;
