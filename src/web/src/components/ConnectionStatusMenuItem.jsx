import LocalizedText from "./Shared/LocalizedText";
import { interfaceText, interfaceTextProps } from "../lib/interfaceLocale";
import * as relayAPI from '../lib/relay';
import { connect, disconnect } from '../lib/server';
import React from 'react';
import { Icon, Menu, Popup } from 'semantic-ui-react';

const ConnectionStatusMenuItem = ({
  connectionWatchdog,
  controller = {},
  mode,
  pendingReconnect,
  server,
  user,
}) => {
  if (mode === 'Agent') {
    const controllerState = ['Connected', 'Connecting', 'Reconnecting', 'Disconnected'].includes(controller?.state)
      ? interfaceText(controller.state)
      : controller?.state;
    const isConnected = controller?.state === 'Connected';
    const isTransitioning = ['Connecting', 'Reconnecting'].includes(
      controller?.state,
    );
    const description = isConnected
      ? 'Disconnect from the relay controller.'
      : 'Connect to the relay controller.';

    return (
      <Popup
        content={description}
        trigger={(
          <Menu.Item
            aria-label={description}
            onClick={() =>
              isConnected ? relayAPI.disconnect() : relayAPI.connect()
            }
            title={description}
          >
            <Icon.Group className="menu-icon-group">
              <Icon
                color={
                  controller?.state === 'Connected'
                    ? 'green'
                    : isTransitioning
                      ? 'yellow'
                      : 'grey'
                }
                name="plug"
              />
              {!isConnected && (
                <Icon
                  className="menu-icon-no-shadow"
                  color="red"
                  corner="bottom right"
                  name="close"
                />
              )}
            </Icon.Group>
            <LocalizedText source={"Controller"} />{" "}{controllerState}
          </Menu.Item>
        )}
      />
    );
  }

  if (server?.isConnected) {
    const description = 'Disconnect from the Soulseek server.';

    return (
      <Popup
        content={description}
        trigger={(
          <Menu.Item
            aria-label={description}
            onClick={() => disconnect()}
            title={description}
          >
            <Icon.Group className="menu-icon-group">
              <Icon
                color={pendingReconnect ? 'yellow' : 'green'}
                name="plug"
              />
              {user?.privileges?.isPrivileged && (
                <Icon
                  className="menu-icon-no-shadow"
                  color="yellow"
                  corner
                  name="star"
                />
              )}
            </Icon.Group>
            <LocalizedText source={"Connected"} /></Menu.Item>
        )}
      />
    );
  }

  // The server is disconnected, and we need to give the user some information about what the client is doing.
  // It may be idle, actively connecting, or waiting for the next connection attempt.
  let icon = 'close';
  let color = 'red';

  if (connectionWatchdog?.isAttemptingConnection) {
    icon = 'clock';
    color = 'yellow';
  }

  if (server?.isConnecting || server?.IsLoggingIn) {
    icon = 'sync alternate loading';
    color = 'green';
  }

  const description = 'Connect to the Soulseek server.';

  return (
    <Popup
      content={description}
      trigger={(
        <Menu.Item
          aria-label={description}
          onClick={() => connect()}
          title={description}
        >
          <Icon.Group className="menu-icon-group">
            <Icon
              color="grey"
              name="plug"
            />
            <Icon
              className="menu-icon-no-shadow"
              color={color}
              corner="bottom right"
              name={icon}
            />
          </Icon.Group>
          <LocalizedText source={"Disconnected"} /></Menu.Item>
      )}
    />
  );
};

export default ConnectionStatusMenuItem;
