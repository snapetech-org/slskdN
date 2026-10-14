import React, { useState } from 'react';
import { Button, Icon, Menu, Modal, Popup } from 'semantic-ui-react';

const RELEASES_URL = 'https://github.com/snapetech-org/slskdN/releases';

const VersionUpdateMenuItem = ({ current, latest }) => {
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
            Update available
          </Menu.Item>
        )}
      />
      <Modal
        centered
        onClose={() => setOpen(false)}
        open={open}
        size="mini"
      >
        <Modal.Header>slskdN update available</Modal.Header>
        <Modal.Content>
          <p>
            You are running version <strong>{current || 'unknown'}</strong>.
            Version <strong>{latest || 'unknown'}</strong> is available.
          </p>
        </Modal.Content>
        <Modal.Actions>
          <Popup
            content="Close this update notice and keep using the current version."
            trigger={(
              <Button onClick={() => setOpen(false)}>
                Close
              </Button>
            )}
          />
          <Popup
            content="Read the release notes for details about the available version."
            trigger={(
              <Button
                href={RELEASES_URL}
                onClick={() => setOpen(false)}
                primary
              >
                See Release Notes
              </Button>
            )}
          />
        </Modal.Actions>
      </Modal>
    </>
  );
};

const LogoutMenuItem = ({ onLogout }) => {
  const [open, setOpen] = useState(false);

  const confirmLogout = () => {
    setOpen(false);
    onLogout();
  };

  return (
    <>
      <Popup
        content="End this web session and return to the login screen."
        trigger={(
          <Menu.Item
            aria-haspopup="dialog"
            aria-label="Log out of this web session."
            data-testid="logout"
            onClick={() => setOpen(true)}
            title="End this web session and return to the login screen."
          >
            <Icon name="sign-out" />
            Log Out
          </Menu.Item>
        )}
      />
      <Modal
        centered
        onClose={() => setOpen(false)}
        open={open}
        size="mini"
      >
        <Modal.Header>
          <Icon name="sign-out" />
          Confirm Log Out
        </Modal.Header>
        <Modal.Content>Are you sure you want to log out?</Modal.Content>
        <Modal.Actions>
          <Popup
            content="Close this prompt and keep the current session active."
            trigger={(
              <Button onClick={() => setOpen(false)}>
                Cancel
              </Button>
            )}
          />
          <Popup
            content="End this web session and return to the login screen."
            trigger={(
              <Button negative onClick={confirmLogout}>
                Log Out
              </Button>
            )}
          />
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
