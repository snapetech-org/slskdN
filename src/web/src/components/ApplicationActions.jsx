import LocalizedText from "./Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../lib/interfaceLocale";
import React, { useState } from 'react';
import { Button, Icon, Menu, Modal, Popup } from 'semantic-ui-react';

const RELEASES_URL = 'https://github.com/snapetech/slskdn/releases';

const VersionUpdateMenuItem = ({ current, latest }) => {
  useInterfaceLanguage();
  const [open, setOpen] = useState(false);
  const description = `Version ${latest} is available. Review the release notes to see what's changed.`;

  return (
    <>
      <Popup
        content={description}
        trigger={(
          <Menu.Item
            aria-haspopup="dialog"
            aria-label={description}
            data-testid="nav-update-available"
            onClick={() => setOpen(true)}
            position="right"
            title={description}
          >
            <Icon color="yellow" name="bullhorn" />
            <LocalizedText source={"Update available"} /></Menu.Item>
        )}
      />
      <Modal
        centered
        onClose={() => setOpen(false)}
        open={open}
        size="mini"
      >
        <Modal.Header><LocalizedText source={"slskdN update available"} /></Modal.Header>
        <Modal.Content>
          <p>
            <LocalizedText source={"You are running version"} />{" "}<strong>{current || 'unknown'}</strong><LocalizedText source={". Version"} />{" "}<strong>{latest || 'unknown'}</strong> <LocalizedText source={"is available."} /></p>
        </Modal.Content>
        <Modal.Actions>
          <Popup
            content={interfaceText("Close this update notice and keep using the current version.")}
            trigger={(
              <Button onClick={() => setOpen(false)}>
                <LocalizedText source={"Close"} /></Button>
            )}
           {...interfaceTextProps("Close this update notice and keep using the current version.")}/>
          <Popup
            content={interfaceText("Read the release notes for details about the available version.")}
            trigger={(
              <Button
                href={RELEASES_URL}
                onClick={() => setOpen(false)}
                primary
              >
                <LocalizedText source={"See Release Notes"} /></Button>
            )}
           {...interfaceTextProps("Read the release notes for details about the available version.")}/>
        </Modal.Actions>
      </Modal>
    </>
  );
};

const LogoutMenuItem = ({ onLogout }) => {
  useInterfaceLanguage();
  const [open, setOpen] = useState(false);

  const confirmLogout = () => {
    setOpen(false);
    onLogout();
  };

  return (
    <>
      <Popup
        content={interfaceText("End this web session and return to the login screen.")}
        trigger={(
          <Menu.Item
           {...interfaceTextProps("Log out of this web session.")}
            aria-haspopup="dialog"
            aria-label={interfaceText("Log out of this web session.")}
            data-testid="logout"
            onClick={() => setOpen(true)}
            title={interfaceText("End this web session and return to the login screen.")}
          >
            <Icon name="sign-out" />
            <LocalizedText source={"Log Out"} /></Menu.Item>
        )}
       {...interfaceTextProps("End this web session and return to the login screen.")}/>
      <Modal
        centered
        onClose={() => setOpen(false)}
        open={open}
        size="mini"
      >
        <Modal.Header>
          <Icon name="sign-out" />
          <LocalizedText source={"Confirm Log Out"} /></Modal.Header>
        <Modal.Content><LocalizedText source={"Are you sure you want to log out?"} /></Modal.Content>
        <Modal.Actions>
          <Popup
            content={interfaceText("Close this prompt and keep the current session active.")}
            trigger={(
              <Button onClick={() => setOpen(false)}>
                <LocalizedText source={"Cancel"} /></Button>
            )}
           {...interfaceTextProps("Close this prompt and keep the current session active.")}/>
          <Popup
            content={interfaceText("End this web session and return to the login screen.")}
            trigger={(
              <Button negative onClick={confirmLogout}>
                <LocalizedText source={"Log Out"} /></Button>
            )}
           {...interfaceTextProps("End this web session and return to the login screen.")}/>
        </Modal.Actions>
      </Modal>
    </>
  );
};

const ApplicationActions = ({
  children,
  current,
  isLoggedIn,
  isUpdateAvailable,
  latest,
  onLogout,
}) => (
  <>
    {isUpdateAvailable && (
      <VersionUpdateMenuItem current={current} latest={latest} />
    )}
    {children}
    {isLoggedIn && <LogoutMenuItem onLogout={onLogout} />}
  </>
);

export default ApplicationActions;
