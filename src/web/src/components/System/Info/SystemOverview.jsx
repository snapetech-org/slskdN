import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import React from 'react';
import { Header, Icon, Label } from 'semantic-ui-react';

const getConnectionStatus = (server) => {
  if (!server) return { color: 'grey', label: interfaceText("Waiting for status") };
  if (server.isConnected || server.IsConnected) {
    return { color: 'green', label: interfaceText("Connected") };
  }
  if (
    server.isConnecting || server.IsConnecting ||
    server.isLoggingIn || server.IsLoggingIn
  ) {
    return { color: 'yellow', label: interfaceText("Connecting") };
  }

  return { color: 'red', label: interfaceText("Disconnected") };
};

const SystemOverview = ({ state = {} }) => {
  useInterfaceLanguage();
  const connection = getConnectionStatus(state.server);
  const version = state.version?.current || state.version?.full || interfaceText('Unavailable');
  const pendingActions = [
    state.pendingRestart && interfaceText('Restart required'),
    state.pendingReconnect && interfaceText('Reconnect required'),
    state.shares?.scanPending && interfaceText('Share scan pending'),
  ].filter(Boolean);

  return (
    <section
      aria-labelledby="system-overview-heading"
      className="system-overview"
      data-testid="system-overview"
    >
      <Header as="h2" id="system-overview-heading">
        <LocalizedText source={"System overview"} /></Header>
      <div className="system-overview-grid">
        <article className="system-overview-card">
          <span className="system-overview-label"><LocalizedText source={"Soulseek connection"} /></span>
          <strong className="system-overview-value">
            <Icon
              aria-hidden="true"
              color={connection.color}
              name="circle"
              size="tiny"
            />{' '}
            {connection.label}
          </strong>
          <span className="system-overview-detail">
            {state.user?.username || interfaceText('Account status unavailable')}
          </span>
        </article>
        <article className="system-overview-card">
          <span className="system-overview-label"><LocalizedText source={"slskdN version"} /></span>
          <strong className="system-overview-value">{version}</strong>
          {state.version?.isUpdateAvailable === true && (
            <span className="system-overview-detail">
              <LocalizedText source={"Version"} />{" "}{state.version.latest} <LocalizedText source={"is available"} /></span>
          )}
        </article>
        <article className="system-overview-card">
          <span className="system-overview-label"><LocalizedText source={"Pending actions"} /></span>
          {pendingActions.length > 0 ? (
            <ul className="system-overview-pending">
              {pendingActions.map((action) => <li key={action}>{action}</li>)}
            </ul>
          ) : (
            <strong className="system-overview-value">
              <Label color="green" size="mini"><LocalizedText source={"None"} /></Label>
            </strong>
          )}
        </article>
      </div>
    </section>
  );
};

export { getConnectionStatus };
export default SystemOverview;
