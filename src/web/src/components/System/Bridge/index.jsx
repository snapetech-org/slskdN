import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';


import * as bridge from '../../../lib/bridge';
import FeatureGateNotice from '../../Shared/FeatureGateNotice';
import useFeatureGates, { isFeatureEnabled } from '../../Shared/useFeatureGates';
import React, { useEffect, useRef, useState } from 'react';
import {
  Button,
  Card,
  Checkbox,
  Form,
  Grid,
  Header,
  Icon,
  Input,
  Label,
  List,
  Loader,
  Message,
  Popup,
  Segment,
  Statistic,
  Table,
} from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);

const dashboardRenderSignature = (dashboard) =>
  JSON.stringify({
    clients: asArray(dashboard?.connectedClients).map((client) => ({
      clientId: client?.clientId,
      clientType: client?.clientType,
      ipAddress: client?.ipAddress,
      requestCount: client?.requestCount,
    })),
    health: dashboard?.health
      ? {
          isHealthy: dashboard.health.isHealthy,
          version: dashboard.health.version,
        }
      : null,
    meshBenefits: dashboard?.meshBenefits
      ? {
          bytesViaMesh: dashboard.meshBenefits.bytesViaMesh,
          bytesViaSoulseek: dashboard.meshBenefits.bytesViaSoulseek,
          meshPercentage: dashboard.meshBenefits.meshPercentage,
        }
      : null,
    stats: dashboard?.stats
      ? {
          currentConnections: dashboard.stats.currentConnections,
          totalBytesProxied: dashboard.stats.totalBytesProxied,
          totalDownloads: dashboard.stats.totalDownloads,
          totalSearches: dashboard.stats.totalSearches,
        }
      : null,
  });

const Bridge = () => {
  useInterfaceLanguage();
  const { featureGates, ready: featureGatesReady } = useFeatureGates();
  const virtualSoulfindEnabled =
    featureGatesReady && isFeatureEnabled(featureGates, 'virtualSoulfind');
  const appliedDashboardSequenceRef = useRef(0);
  const configLoadedRef = useRef(false);
  const configRequestRef = useRef(null);
  const dashboardRequestRef = useRef(null);
  const dashboardSequenceRef = useRef(0);
  const dashboardSignatureRef = useRef(null);
  const lifecycleRef = useRef(0);
  const mountedRef = useRef(false);
  const pollIntervalRef = useRef(null);
  const [config, setConfig] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [bridgeAction, setBridgeAction] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const isCurrentLifecycle = React.useCallback(
    (lifecycle) => mountedRef.current && lifecycleRef.current === lifecycle,
    [],
  );

  const requestDashboard = React.useCallback(
    async (lifecycle, requireFresh = false) => {
      if (
        !virtualSoulfindEnabled ||
        document.hidden ||
        !isCurrentLifecycle(lifecycle)
      ) return null;

      if (requireFresh && dashboardRequestRef.current) {
        try {
          await dashboardRequestRef.current.promise;
        } catch {
          // The fresh request below owns the post-action result.
        }
        if (document.hidden || !isCurrentLifecycle(lifecycle)) return null;
      }

      let request = dashboardRequestRef.current;
      if (!request) {
        request = {
          promise: bridge.getDashboard(),
          sequence: ++dashboardSequenceRef.current,
        };
        dashboardRequestRef.current = request;
      }

      try {
        const dashboardData = await request.promise;
        if (document.hidden || !isCurrentLifecycle(lifecycle)) return dashboardData;
        if (request.sequence < appliedDashboardSequenceRef.current) return dashboardData;

        appliedDashboardSequenceRef.current = request.sequence;
        const signature = dashboardRenderSignature(dashboardData);
        if (dashboardSignatureRef.current !== signature) {
          dashboardSignatureRef.current = signature;
          setDashboard(dashboardData);
        }

        return dashboardData;
      } finally {
        if (dashboardRequestRef.current === request) {
          dashboardRequestRef.current = null;
        }
      }
    },
    [isCurrentLifecycle, virtualSoulfindEnabled],
  );

  const hydrate = React.useCallback(
    async (lifecycle) => {
      if (
        !virtualSoulfindEnabled ||
        document.hidden ||
        !isCurrentLifecycle(lifecycle)
      ) return;

      const needsConfig = !configLoadedRef.current;
      let configRequest = null;
      try {
        if (needsConfig) {
          setLoading(true);
          setError(null);
          if (!configRequestRef.current) {
            configRequestRef.current = bridge.getConfig();
          }

          configRequest = configRequestRef.current;
          const [configData] = await Promise.all([
            configRequest,
            requestDashboard(lifecycle),
          ]);
          if (!isCurrentLifecycle(lifecycle) || document.hidden) return;
          configLoadedRef.current = true;
          setConfig(configData);
        } else {
          await requestDashboard(lifecycle);
        }
      } catch (error_) {
        if (!isCurrentLifecycle(lifecycle) || document.hidden) return;
        if (needsConfig) {
          setError(getApiErrorMessage(error_, { t: interfaceText }));
        }
      } finally {
        if (configRequest && configRequestRef.current === configRequest) {
          configRequestRef.current = null;
        }
        if (isCurrentLifecycle(lifecycle) && !document.hidden && needsConfig) {
          setLoading(false);
        }
      }
    },
    [isCurrentLifecycle, requestDashboard, virtualSoulfindEnabled],
  );

  useEffect(() => {
    mountedRef.current = true;
    const lifecycle = ++lifecycleRef.current;
    const stopPolling = () => {
      if (pollIntervalRef.current) {
        window.clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
    const startPolling = () => {
      if (
        !featureGatesReady ||
        !virtualSoulfindEnabled ||
        document.hidden ||
        pollIntervalRef.current
      ) return;

      hydrate(lifecycle);
      pollIntervalRef.current = window.setInterval(() => {
        requestDashboard(lifecycle).catch(() => {});
      }, 10_000);
    };
    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopPolling();
      } else {
        startPolling();
      }
    };

    startPolling();
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      stopPolling();
      mountedRef.current = false;
      lifecycleRef.current++;
    };
  }, [featureGatesReady, hydrate, requestDashboard, virtualSoulfindEnabled]);

  const handleConfigChange = (field, value) => {
    setConfig((previous) => ({
      ...previous,
      [field]: value,
    }));
  };

  const handleSaveConfig = async () => {
    if (!virtualSoulfindEnabled) return;

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      await bridge.updateConfig(config);
      if (!mountedRef.current) return;
      setSuccess(
        interfaceText("Configuration updated. Restart bridge service to apply changes."),
      );
    } catch (error_) {
      if (!mountedRef.current) return;
      setError(getApiErrorMessage(error_, { t: interfaceText }));
    } finally {
      if (mountedRef.current) {
        setSaving(false);
      }
    }
  };

  const handleStartBridge = async () => {
    if (!virtualSoulfindEnabled) return;

    try {
      setBridgeAction('start');
      setError(null);
      await bridge.startBridge();
      await requestDashboard(lifecycleRef.current, true);
    } catch (error_) {
      if (!mountedRef.current) return;
      setError(getApiErrorMessage(error_, { t: interfaceText }));
    } finally {
      if (mountedRef.current) {
        setBridgeAction(null);
      }
    }
  };

  const handleStopBridge = async () => {
    if (!virtualSoulfindEnabled) return;

    try {
      setBridgeAction('stop');
      setError(null);
      await bridge.stopBridge();
      await requestDashboard(lifecycleRef.current, true);
    } catch (error_) {
      if (!mountedRef.current) return;
      setError(getApiErrorMessage(error_, { t: interfaceText }));
    } finally {
      if (mountedRef.current) {
        setBridgeAction(null);
      }
    }
  };

  if (featureGatesReady && !virtualSoulfindEnabled) {
    return (
      <div>
        <Header as="h2">
          <Icon name="exchange" />
          <LocalizedText source={"Legacy Client Bridge"} /></Header>
        <FeatureGateNotice
          configurationKeys={['feature.VirtualSoulfind']}
          featureGate={featureGates.virtualSoulfind}
          featureName="VirtualSoulfind"
        />
      </div>
    );
  }

  if (loading && !config) {
    return (
      <Segment>
        <Loader
          active
          inline="centered"
        >
          <LocalizedText source={"Loading bridge configuration..."} /></Loader>
      </Segment>
    );
  }

  const health = dashboard?.health;
  const stats = dashboard?.stats;
  const clients = asArray(dashboard?.connectedClients);
  const meshBenefits = dashboard?.meshBenefits;

  return (
    <div>
      <Header as="h2">
        <Icon name="exchange" />
        <LocalizedText source={"Legacy Client Bridge"} /></Header>

      {error && (
        <Message error>
          <Message.Header><LocalizedText source={"Error"} /></Message.Header>
          <p>{error}</p>
        </Message>
      )}

      {success && (
        <Message success>
          <Message.Header><LocalizedText source={"Success"} /></Message.Header>
          <p>{success}</p>
        </Message>
      )}

      <Grid stackable>
        {/* Configuration */}
        <Grid.Column width={16}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="cog" />
                <LocalizedText source={"Configuration"} /></Card.Header>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Group widths="equal">
                  <Form.Field>
                    <Checkbox
                      checked={config?.enabled || false}
                      label={interfaceText("Enable Bridge")}
                      onChange={(e, { checked }) =>
                        handleConfigChange('enabled', checked)
                      }
                      toggle
                     {...interfaceTextProps("Enable Bridge")}/>
                    <small>
                      <LocalizedText source={"Allow legacy Soulseek clients to connect via bridge"} /></small>
                  </Form.Field>
                </Form.Group>
                <Form.Group widths="equal">
                  <Form.Field>
                    <label><LocalizedText source={"Port"} /></label>
                    <Input
                      disabled={!config?.enabled}
                      onChange={(e, { value }) =>
                        handleConfigChange(
                          'port',
                          Number.parseInt(value, 10) || 2_242,
                        )
                      }
                      type="number"
                      value={config?.port || 2_242}
                    />
                    <small><LocalizedText source={"Soulseek protocol port (default: 2242)"} /></small>
                  </Form.Field>
                  <Form.Field>
                    <label><LocalizedText source={"Soulfind Path"} /></label>
                    <Input
                      disabled={!config?.enabled}
                      onChange={(e, { value }) =>
                        handleConfigChange('soulfind_path', value)
                      }
                      placeholder={interfaceText("soulfind")}
                      value={config?.soulfind_path || 'soulfind'}
                     {...interfaceTextProps("soulfind")}/>
                    <small><LocalizedText source={"Path to Soulfind binary"} /></small>
                  </Form.Field>
                </Form.Group>
                <Form.Group widths="equal">
                  <Form.Field>
                    <label><LocalizedText source={"Max Clients"} /></label>
                    <Input
                      disabled={!config?.enabled}
                      max={50}
                      min={1}
                      onChange={(e, { value }) =>
                        handleConfigChange(
                          'max_clients',
                          Number.parseInt(value, 10) || 10,
                        )
                      }
                      type="number"
                      value={config?.max_clients || 10}
                    />
                    <small><LocalizedText source={"Maximum concurrent legacy clients"} /></small>
                  </Form.Field>
                  <Form.Field>
                    <Checkbox
                      checked={config?.require_auth || false}
                      disabled={!config?.enabled}
                      label={interfaceText("Require Authentication")}
                      onChange={(e, { checked }) =>
                        handleConfigChange('require_auth', checked)
                      }
                      toggle
                     {...interfaceTextProps("Require Authentication")}/>
                    <small><LocalizedText source={"Require password for bridge connections"} /></small>
                  </Form.Field>
                </Form.Group>
                <Popup
                  content={interfaceText("Save the bridge settings for the next service restart. This does not start or restart the bridge.")}
                  position="top center"
                  trigger={
                    <Button
                      loading={saving}
                      onClick={handleSaveConfig}
                      primary
                    >
                      <LocalizedText source={"Save Configuration"} /></Button>
                  }
                 {...interfaceTextProps("Save the bridge settings for the next service restart. This does not start or restart the bridge.")}/>
              </Form>
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Service Control */}
        <Grid.Column width={16}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="power" />
                <LocalizedText source={"Service Control"} /></Card.Header>
            </Card.Content>
            <Card.Content>
              <div
                style={{ alignItems: 'center', display: 'flex', gap: '10px' }}
              >
                <Popup
                  content={interfaceText("Start the configured local legacy-client bridge so compatible clients can connect.")}
                  position="top center"
                  trigger={
                    <Button
                      color="green"
                      disabled={health?.isHealthy || bridgeAction !== null}
                      loading={bridgeAction === 'start'}
                      onClick={handleStartBridge}
                    >
                      <Icon name="play" />
                      <LocalizedText source={"Start Bridge"} /></Button>
                  }
                 {...interfaceTextProps("Start the configured local legacy-client bridge so compatible clients can connect.")}/>
                <Popup
                  content={interfaceText("Stop the local legacy-client bridge and disconnect its active clients.")}
                  position="top center"
                  trigger={
                    <Button
                      color="red"
                      disabled={!health?.isHealthy || bridgeAction !== null}
                      loading={bridgeAction === 'stop'}
                      onClick={handleStopBridge}
                    >
                      <Icon name="stop" />
                      <LocalizedText source={"Stop Bridge"} /></Button>
                  }
                 {...interfaceTextProps("Stop the local legacy-client bridge and disconnect its active clients.")}/>
                <Label
                  color={health?.isHealthy ? 'green' : 'red'}
                  size="large"
                >
                  <Icon name={health?.isHealthy ? 'checkmark' : 'remove'} />
                  {health?.isHealthy ? <LocalizedText source={"Running"} /> : <LocalizedText source={"Stopped"} />}
                </Label>
                {health?.version && <Label><LocalizedText source={"Version:"} />{" "}{health.version}</Label>}
              </div>
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Statistics */}
        {stats && (
          <Grid.Column width={16}>
            <Card fluid>
              <Card.Content>
                <Card.Header>
                  <Icon name="chart bar" />
                  <LocalizedText source={"Statistics"} /></Card.Header>
              </Card.Content>
              <Card.Content>
                <Statistic.Group size="small">
                  <Statistic>
                    <Statistic.Value>
                      {stats.currentConnections || 0}
                    </Statistic.Value>
                    <Statistic.Label><LocalizedText source={"Active Connections"} /></Statistic.Label>
                  </Statistic>
                  <Statistic>
                    <Statistic.Value>
                      {stats.totalSearches || 0}
                    </Statistic.Value>
                    <Statistic.Label><LocalizedText source={"Total Searches"} /></Statistic.Label>
                  </Statistic>
                  <Statistic>
                    <Statistic.Value>
                      {stats.totalDownloads || 0}
                    </Statistic.Value>
                    <Statistic.Label><LocalizedText source={"Total Downloads"} /></Statistic.Label>
                  </Statistic>
                  <Statistic>
                    <Statistic.Value>
                      {(stats.totalBytesProxied / 1_024 / 1_024).toFixed(2)}
                    </Statistic.Value>
                    <Statistic.Label><LocalizedText source={"MB Proxied"} /></Statistic.Label>
                  </Statistic>
                </Statistic.Group>
              </Card.Content>
            </Card>
          </Grid.Column>
        )}

        {/* Mesh Benefits */}
        {meshBenefits && (
          <Grid.Column width={8}>
            <Card fluid>
              <Card.Content>
                <Card.Header>
                  <Icon name="sitemap" />
                  <LocalizedText source={"Mesh Benefits"} /></Card.Header>
              </Card.Content>
              <Card.Content>
                <Statistic.Group size="small">
                  <Statistic>
                    <Statistic.Value>
                      {meshBenefits.meshPercentage.toFixed(1)}%
                    </Statistic.Value>
                    <Statistic.Label><LocalizedText source={"Via Mesh"} /></Statistic.Label>
                  </Statistic>
                  <Statistic>
                    <Statistic.Value>
                      {(meshBenefits.bytesViaMesh / 1_024 / 1_024).toFixed(2)}
                    </Statistic.Value>
                    <Statistic.Label><LocalizedText source={"MB via Mesh"} /></Statistic.Label>
                  </Statistic>
                </Statistic.Group>
              </Card.Content>
            </Card>
          </Grid.Column>
        )}

        {/* Connected Clients */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="users" />
                <LocalizedText source={"Connected Clients ("} />{clients.length})
              </Card.Header>
            </Card.Content>
            <Card.Content>
              {clients.length === 0 ? (
                <Message info><LocalizedText source={"No clients connected"} /></Message>
              ) : (
                <Table
                  compact
                  size="small"
                >
                  <Table.Header>
                    <Table.Row>
                      <Table.HeaderCell><LocalizedText source={"Client"} /></Table.HeaderCell>
                      <Table.HeaderCell>IP</Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Requests"} /></Table.HeaderCell>
                    </Table.Row>
                  </Table.Header>
                  <Table.Body>
                    {clients.map((client) => (
                      <Table.Row key={client.clientId}>
                        <Table.Cell>{client.clientType}</Table.Cell>
                        <Table.Cell>{client.ipAddress}</Table.Cell>
                        <Table.Cell>{client.requestCount}</Table.Cell>
                      </Table.Row>
                    ))}
                  </Table.Body>
                </Table>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>
      </Grid>
    </div>
  );
};

export default Bridge;
