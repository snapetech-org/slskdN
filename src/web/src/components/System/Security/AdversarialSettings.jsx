import { getRegionalLocale } from '../../../lib/regionalFormat';
import './Security.css';
import * as securityApi from '../../../lib/security';
import React, { useCallback, useEffect, useState } from 'react';
import {
  Button,
  Checkbox,
  Dimmer,
  Dropdown,
  Form,
  Grid,
  Header,
  Icon,
  Input,
  Label,
  Loader,
  Message,
  Popup,
  Segment,
  Statistic,
  Tab,
  TextArea,
} from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);

const AdversarialSettings = () => {
  const [activeIndex, setActiveIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [settings, setSettings] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [status, setStatus] = useState(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [transportStatus, setTransportStatus] = useState(null);
  const [transportLoading, setTransportLoading] = useState(false);
  const [torStatus, setTorStatus] = useState(null);
  const [torLoading, setTorLoading] = useState(false);

  const fetchSettings = useCallback(async () => {
    try {
      setLoading(true);
      const data = await securityApi.getAdversarialSettings().catch(() => null);
      if (data) {
        setSettings(data);
        setError(null);
        return data;
      } else {
        setError('Adversarial features are not configured on this server');
      }
    } catch (fetchError) {
      setError(fetchError.message || 'Failed to load adversarial settings');
    } finally {
      setLoading(false);
    }

    return null;
  }, []);

  const fetchStatus = useCallback(async () => {
    try {
      setStatusLoading(true);
      const statusData = await securityApi
        .getAdversarialStats()
        .catch(() => null);
      if (statusData) {
        setStatus(statusData);
      }
    } catch (statusError) {
      console.error('Failed to load adversarial status:', statusError);
    } finally {
      setStatusLoading(false);
    }
  }, []);

  const fetchTransportStatus = useCallback(async () => {
    try {
      setTransportLoading(true);
      const transportData = await securityApi
        .getTransportStatus()
        .catch(() => null);
      if (transportData) {
        setTransportStatus(transportData);
      }
    } catch (transportError) {
      console.error('Failed to load transport status:', transportError);
    } finally {
      setTransportLoading(false);
    }
  }, []);

  const fetchTorStatus = useCallback(async () => {
    try {
      setTorLoading(true);
      const torData = await securityApi.getTorStatus().catch(() => null);
      if (torData) {
        setTorStatus(torData);
      }
    } catch (torError) {
      console.error('Failed to load Tor status:', torError);
    } finally {
      setTorLoading(false);
    }
  }, []);

  useEffect(() => {
    const initialize = async () => {
      const configuredSettings = await fetchSettings();
      fetchStatus();

      if (!configuredSettings?.Enabled) return;

      fetchTransportStatus();
      if (
        configuredSettings.Anonymity?.Enabled &&
        configuredSettings.Anonymity?.Mode === 'Tor'
      ) {
        fetchTorStatus();
      }
    };

    initialize();
  }, [fetchSettings, fetchStatus, fetchTorStatus, fetchTransportStatus]);

  const handleSave = async () => {
    if (!settings) return;

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      await securityApi.updateAdversarialSettings(settings);
      setSuccess('Adversarial settings updated successfully');
      setHasChanges(false);
    } catch (saveError) {
      setError(saveError.message || 'Failed to save adversarial settings');
    } finally {
      setSaving(false);
    }
  };

  const FORBIDDEN_KEYS = new Set(['__proto__', 'constructor', 'prototype']);

  const updateSetting = (path, value) => {
    setSettings((previous) => {
      const newSettings = { ...previous };
      const keys = path.split('.');

      if (keys.some((k) => FORBIDDEN_KEYS.has(k))) return newSettings;

      let current = newSettings;

      for (let index = 0; index < keys.length - 1; index++) {
        if (!Object.hasOwn(current, keys[index]) || typeof current[keys[index]] !== 'object') {
          current[keys[index]] = {};
        }
        current = current[keys[index]];
      }

      current[keys[keys.length - 1]] = value;
      return newSettings;
    });
    setHasChanges(true);
  };

  const updateArray = (path, index, value) => {
    setSettings((previous) => {
      const newSettings = { ...previous };
      const keys = path.split('.');

      if (keys.some((k) => FORBIDDEN_KEYS.has(k))) return newSettings;

      let current = newSettings;

      for (let index_ = 0; index_ < keys.length - 1; index_++) {
        if (!Object.hasOwn(current, keys[index_]) || typeof current[keys[index_]] !== 'object') {
          current[keys[index_]] = {};
        }
        current = current[keys[index_]];
      }

      if (!Array.isArray(current[keys[keys.length - 1]])) {
        current[keys[keys.length - 1]] = [];
      }

      current[keys[keys.length - 1]][index] = value;
      return newSettings;
    });
    setHasChanges(true);
  };

  const addArrayItem = (path) => {
    setSettings((previous) => {
      const newSettings = { ...previous };
      const keys = path.split('.');
      let current = newSettings;

      for (let index = 0; index < keys.length - 1; index++) {
        if (!current[keys[index]]) current[keys[index]] = {};
        current = current[keys[index]];
      }

      if (!Array.isArray(current[keys[keys.length - 1]])) {
        current[keys[keys.length - 1]] = [];
      }

      current[keys[keys.length - 1]].push('');
      return newSettings;
    });
    setHasChanges(true);
  };

  const removeArrayItem = (path, index) => {
    setSettings((previous) => {
      const newSettings = { ...previous };
      const keys = path.split('.');
      let current = newSettings;

      for (let index_ = 0; index_ < keys.length - 1; index_++) {
        if (!current[keys[index_]]) current[keys[index_]] = {};
        current = current[keys[index_]];
      }

      if (Array.isArray(current[keys[keys.length - 1]])) {
        current[keys[keys.length - 1]].splice(index, 1);
      }

      return newSettings;
    });
    setHasChanges(true);
  };

  if (loading) {
    return (
      <Segment placeholder>
        <Dimmer
          active
          inverted
        >
          <Loader>Loading Adversarial Settings...</Loader>
        </Dimmer>
      </Segment>
    );
  }

  if (error && !settings) {
    return (
      <Message negative>
        <Message.Header>Adversarial Features Unavailable</Message.Header>
        <p>{error}</p>
        <p>
          Adversarial features are advanced security options designed for users
          in adversarial environments. They are disabled by default and require
          explicit configuration.
        </p>
        <Popup
          content="Try loading adversarial settings again after enabling them on the server or restoring the connection."
          position="top center"
          trigger={(
            <Button
              aria-label="Retry loading adversarial settings"
              onClick={fetchSettings}
              size="small"
            >
              Retry
            </Button>
          )}
        />
      </Message>
    );
  }

  if (!settings) {
    return (
      <Message info>
        <Message.Header>Adversarial Settings Not Configured</Message.Header>
        <p>No adversarial configuration found.</p>
      </Message>
    );
  }

  const profileOptions = [
    { key: 'disabled', text: 'Disabled', value: 'Disabled' },
    { key: 'standard', text: 'Standard (Privacy)', value: 'Standard' },
    {
      key: 'enhanced',
      text: 'Enhanced (Privacy + Anonymity)',
      value: 'Enhanced',
    },
    { key: 'maximum', text: 'Maximum (All Features)', value: 'Maximum' },
    { key: 'custom', text: 'Custom', value: 'Custom' },
  ];

  const transportOptions = [
    { key: 'Direct', text: 'Direct', value: 'Direct' },
    { key: 'WebSocket', text: 'WebSocket', value: 'WebSocket' },
    { key: 'HttpTunnel', text: 'HTTP Tunnel', value: 'HttpTunnel' },
    { key: 'Obfs4', text: 'Obfs4', value: 'Obfs4' },
    { key: 'Meek', text: 'Meek', value: 'Meek' },
  ];

  const anonymityModeOptions = [
    { key: 'Direct', text: 'Direct', value: 'Direct' },
    { key: 'Tor', text: 'Tor', value: 'Tor' },
    { key: 'I2P', text: 'I2P', value: 'I2P' },
    { key: 'RelayOnly', text: 'Relay Only', value: 'RelayOnly' },
  ];

  const panes = [
    {
      menuItem: 'Overview',
      pane: (
        <Tab.Pane key="overview">
          <Header as="h3">
            <Icon name="shield alternate" />
            Adversarial Resilience Overview
          </Header>
          <p>
            <strong>⚠️ WARNING:</strong> These features are designed for users
            in repressive regimes or facing active surveillance. They are{' '}
            <strong>ALL DISABLED BY DEFAULT</strong> and may impact performance
            and compatibility. Only enable if you understand the security
            implications.
          </p>

          <Form>
            <Form.Field>
              <label>Adversarial Profile</label>
              <Dropdown
                onChange={(e, { value }) => updateSetting('Profile', value)}
                options={profileOptions}
                selection
                value={settings.Profile || 'Disabled'}
              />
            </Form.Field>

            <Form.Field>
              <Checkbox
                checked={settings.Enabled || false}
                label="Enable Adversarial Features"
                onChange={(e, { checked }) => updateSetting('Enabled', checked)}
              />
            </Form.Field>
          </Form>

          {settings.Enabled && (
            <>
              <Message info>
                <Message.Header>Active Features</Message.Header>
                <ul>
                  {settings.Privacy?.Enabled && (
                    <li>Privacy Layer (Traffic Analysis Protection)</li>
                  )}
                  {settings.Anonymity?.Enabled && (
                    <li>Anonymity Layer (IP Protection)</li>
                  )}
                  {settings.Transport?.Enabled && (
                    <li>Obfuscated Transport (Anti-DPI)</li>
                  )}
                  {settings.OnionRouting?.Enabled && (
                    <li>Onion Routing (Mesh Anonymity)</li>
                  )}
                  {settings.CensorshipResistance?.Enabled && (
                    <li>Censorship Resistance</li>
                  )}
                  {settings.PlausibleDeniability?.Enabled && (
                    <li>Plausible Deniability</li>
                  )}
                </ul>
              </Message>

              <Segment>
                <Header as="h4">
                  <Icon name="signal" />
                  Transport Status
                </Header>
                <Grid
                  columns={3}
                  stackable
                >
                  <Grid.Column>
                    <Statistic size="small">
                      <Statistic.Value>
                        {statusLoading ? (
                          <Loader
                            active
                            inline
                            size="mini"
                          />
                        ) : status?.AnonymityEnabled ? (
                          <Label color="green">
                            <Icon name="check" />
                            Enabled
                          </Label>
                        ) : (
                          <Label color="grey">
                            <Icon name="minus" />
                            Disabled
                          </Label>
                        )}
                      </Statistic.Value>
                      <Statistic.Label>Anonymity Layer</Statistic.Label>
                    </Statistic>
                  </Grid.Column>
                  <Grid.Column>
                    <Statistic size="small">
                      <Statistic.Value>
                        {statusLoading ? (
                          <Loader
                            active
                            inline
                            size="mini"
                          />
                        ) : settings.Anonymity?.Mode === 'Tor' ? (
                          <Label color="orange">
                            <Icon name="shield" />
                            Tor
                          </Label>
                        ) : settings.Anonymity?.Mode === 'I2P' ? (
                          <Label color="purple">
                            <Icon name="privacy" />
                            I2P
                          </Label>
                        ) : settings.Anonymity?.Mode === 'RelayOnly' ? (
                          <Label color="blue">
                            <Icon name="chain" />
                            Relay Only
                          </Label>
                        ) : (
                          <Label color="grey">
                            <Icon name="globe" />
                            Direct
                          </Label>
                        )}
                      </Statistic.Value>
                      <Statistic.Label>Transport Mode</Statistic.Label>
                    </Statistic>
                  </Grid.Column>
                  <Grid.Column>
                    <Statistic size="small">
                      <Statistic.Value>
                        <Label color="teal">
                          <Icon name="sync alternate" />
                          Auto
                        </Label>
                      </Statistic.Value>
                      <Statistic.Label>Failover</Statistic.Label>
                    </Statistic>
                  </Grid.Column>
                  <Grid.Column>
                    <Statistic size="small">
                      <Statistic.Value>
                        {transportLoading ? (
                          <Loader
                            active
                            inline
                            size="mini"
                          />
                        ) : transportStatus ? (
                          <Label
                            color={
                              transportStatus.PrimaryTransportAvailable
                                ? 'green'
                                : 'red'
                            }
                          >
                            <Icon name="shield" />
                            {transportStatus.AvailableTransports}/
                            {transportStatus.TotalTransports}
                          </Label>
                        ) : (
                          <Label color="grey">
                            <Icon name="question circle" />
                            N/A
                          </Label>
                        )}
                      </Statistic.Value>
                      <Statistic.Label>Transports Up</Statistic.Label>
                    </Statistic>
                  </Grid.Column>
                  <Grid.Column>
                    <Statistic size="small">
                      <Statistic.Value>
                        {torLoading ? (
                          <Loader
                            active
                            inline
                            size="mini"
                          />
                        ) : torStatus ? (
                          <Label
                            color={torStatus.IsAvailable ? 'green' : 'red'}
                          >
                            <Icon name="shield alternate" />
                            {torStatus.IsAvailable
                              ? 'Connected'
                              : 'Disconnected'}
                          </Label>
                        ) : (
                          <Label color="grey">
                            <Icon name="question circle" />
                            N/A
                          </Label>
                        )}
                      </Statistic.Value>
                      <Statistic.Label>Tor Status</Statistic.Label>
                    </Statistic>
                  </Grid.Column>
                </Grid>

                {settings.Anonymity?.Mode === 'Tor' && (
                  <Message info>
                    <Message.Header>Tor Configuration</Message.Header>
                    <p>
                      <strong>SOCKS Address:</strong>{' '}
                      {settings.Anonymity.Tor?.SocksAddress || '127.0.0.1:9050'}
                    </p>
                    <p>
                      <strong>Stream Isolation:</strong>{' '}
                      {settings.Anonymity.Tor?.IsolateStreams
                        ? 'Enabled'
                        : 'Disabled'}
                    </p>
                    <p>
                      <em>
                        Stream isolation prevents correlation attacks by using
                        different Tor circuits per peer.
                      </em>
                    </p>
                  </Message>
                )}

                {settings.Anonymity?.Mode === 'Tor' && torStatus && (
                  <Message color={torStatus.IsAvailable ? 'green' : 'red'}>
                    <Message.Header>Tor Status</Message.Header>
                    <p>
                      <strong>Status:</strong>{' '}
                      {torStatus.IsAvailable ? 'Connected' : 'Disconnected'}
                    </p>
                    {torStatus.LastError && (
                      <p>
                        <strong>Last Error:</strong> {torStatus.LastError}
                      </p>
                    )}
                    {torStatus.LastSuccessfulConnection && (
                      <p>
                        <strong>Last Connected:</strong>{' '}
                        {new Date(
                          torStatus.LastSuccessfulConnection,
                        ).toLocaleString(getRegionalLocale())}
                      </p>
                    )}
                    <p>
                      <strong>Active Connections:</strong>{' '}
                      {torStatus.ActiveConnections}
                    </p>
                    <p>
                      <strong>Total Attempts:</strong>{' '}
                      {torStatus.TotalConnectionsAttempted}
                    </p>
                    <p>
                      <strong>Successful Connections:</strong>{' '}
                      {torStatus.TotalConnectionsSuccessful}
                    </p>
                  </Message>
                )}

                {settings.Anonymity?.Mode === 'I2P' && (
                  <Message info>
                    <Message.Header>I2P Configuration</Message.Header>
                    <p>
                      <strong>SAM Address:</strong>{' '}
                      {settings.Anonymity.I2P?.SamAddress || '127.0.0.1:7656'}
                    </p>
                    <p>
                      <em>
                        I2P provides peer-to-peer anonymity with better
                        performance for persistent connections.
                      </em>
                    </p>
                  </Message>
                )}

                {settings.Anonymity?.Mode === 'RelayOnly' && (
                  <Message info>
                    <Message.Header>Relay-Only Configuration</Message.Header>
                    <p>
                      <strong>Trusted Relays:</strong>{' '}
                      {settings.Anonymity.RelayOnly?.TrustedRelayPeers
                        ?.length || 0}{' '}
                      configured
                    </p>
                    <p>
                      <strong>Max Chain Length:</strong>{' '}
                      {settings.Anonymity.RelayOnly?.MaxChainLength || 3}
                    </p>
                    <p>
                      <em>
                        Never reveals your IP address - all connections route
                        through trusted mesh relays.
                      </em>
                    </p>
                  </Message>
                )}
              </Segment>
            </>
          )}
        </Tab.Pane>
      ),
    },
    {
      menuItem: 'Privacy',
      pane: (
        <Tab.Pane key="privacy">
          <Header as="h4">Privacy Layer - Traffic Analysis Protection</Header>
          <p>
            Protect against traffic analysis by modifying message timing and
            size patterns.
          </p>

          <Form>
            <Form.Field>
              <Checkbox
                checked={settings.Privacy?.Enabled || false}
                label="Enable Privacy Layer"
                onChange={(e, { checked }) =>
                  updateSetting('Privacy.Enabled', checked)
                }
              />
            </Form.Field>

            {settings.Privacy?.Enabled && (
              <>
                <Header as="h5">Message Padding</Header>
                <Form.Field>
                  <Checkbox
                    checked={settings.Privacy.Padding?.Enabled || false}
                    label="Enable Message Padding"
                    onChange={(e, { checked }) =>
                      updateSetting('Privacy.Padding.Enabled', checked)
                    }
                  />
                </Form.Field>

                {settings.Privacy.Padding?.Enabled && (
                  <>
                    <Form.Field>
                      <label>Bucket Sizes (bytes)</label>
                      {asArray(settings.Privacy.Padding?.BucketSizes).map(
                        (size, index) => (
                          <Input
                            key={index}
                            onChange={(e) =>
                              updateArray(
                                'Privacy.Padding.BucketSizes',
                                index,
                                Number.parseInt(e.target.value),
                              )
                            }
                            style={{ marginBottom: '5px' }}
                            type="number"
                            value={size}
                          />
                        ),
                      )}
                      <Popup
                        content="Add another size to the message-padding list."
                        position="top center"
                        trigger={(
                          <Button
                            aria-label="Add message-padding bucket size"
                            icon="plus"
                            onClick={() =>
                              addArrayItem('Privacy.Padding.BucketSizes')
                            }
                            size="mini"
                          />
                        )}
                      />
                    </Form.Field>

                    <Form.Field>
                      <Checkbox
                        checked={
                          settings.Privacy.Padding?.UseRandomFill || false
                        }
                        label="Use Random Fill Bytes"
                        onChange={(e, { checked }) =>
                          updateSetting(
                            'Privacy.Padding.UseRandomFill',
                            checked,
                          )
                        }
                      />
                    </Form.Field>
                  </>
                )}

                <Header as="h5">Timing Obfuscation</Header>
                <Form.Field>
                  <Checkbox
                    checked={settings.Privacy.Timing?.Enabled || false}
                    label="Enable Timing Obfuscation"
                    onChange={(e, { checked }) =>
                      updateSetting('Privacy.Timing.Enabled', checked)
                    }
                  />
                </Form.Field>

                {settings.Privacy.Timing?.Enabled && (
                  <Form.Field>
                    <label>Jitter Range (ms)</label>
                    <Input
                      max="500"
                      min="0"
                      onChange={(e) =>
                        updateSetting(
                          'Privacy.Timing.JitterMs',
                          Number.parseInt(e.target.value),
                        )
                      }
                      type="number"
                      value={settings.Privacy.Timing?.JitterMs || 100}
                    />
                  </Form.Field>
                )}

                <Header as="h5">Message Batching</Header>
                <Form.Field>
                  <Checkbox
                    checked={settings.Privacy.Batching?.Enabled || false}
                    label="Enable Message Batching"
                    onChange={(e, { checked }) =>
                      updateSetting('Privacy.Batching.Enabled', checked)
                    }
                  />
                </Form.Field>

                {settings.Privacy.Batching?.Enabled && (
                  <Form.Field>
                    <label>Batch Window (ms)</label>
                    <Input
                      max="5000"
                      min="100"
                      onChange={(e) =>
                        updateSetting(
                          'Privacy.Batching.BatchWindowMs',
                          Number.parseInt(e.target.value),
                        )
                      }
                      type="number"
                      value={settings.Privacy.Batching?.BatchWindowMs || 1_000}
                    />
                  </Form.Field>
                )}

                <Header as="h5">Cover Traffic</Header>
                <Form.Field>
                  <Checkbox
                    checked={settings.Privacy.CoverTraffic?.Enabled || false}
                    label="Enable Cover Traffic"
                    onChange={(e, { checked }) =>
                      updateSetting('Privacy.CoverTraffic.Enabled', checked)
                    }
                  />
                </Form.Field>

                {settings.Privacy.CoverTraffic?.Enabled && (
                  <Form.Field>
                    <label>Interval (seconds)</label>
                    <Input
                      max="3600"
                      min="10"
                      onChange={(e) =>
                        updateSetting(
                          'Privacy.CoverTraffic.IntervalSeconds',
                          Number.parseInt(e.target.value),
                        )
                      }
                      type="number"
                      value={
                        settings.Privacy.CoverTraffic?.IntervalSeconds || 300
                      }
                    />
                  </Form.Field>
                )}
              </>
            )}
          </Form>
        </Tab.Pane>
      ),
    },
    {
      menuItem: 'Anonymity',
      pane: (
        <Tab.Pane key="anonymity">
          <Header as="h4">Anonymity Layer - IP Protection</Header>
          <p>
            Route traffic through anonymizing networks to hide your IP address.
          </p>

          <Form>
            <Form.Field>
              <Checkbox
                checked={settings.Anonymity?.Enabled || false}
                label="Enable Anonymity Layer"
                onChange={(e, { checked }) =>
                  updateSetting('Anonymity.Enabled', checked)
                }
              />
            </Form.Field>

            {settings.Anonymity?.Enabled && (
              <>
                <Form.Field>
                  <label>Anonymity Mode</label>
                  <Dropdown
                    onChange={(e, { value }) =>
                      updateSetting('Anonymity.Mode', value)
                    }
                    options={anonymityModeOptions}
                    selection
                    value={settings.Anonymity?.Mode || 'Direct'}
                  />
                </Form.Field>

                {settings.Anonymity?.Mode === 'Tor' && (
                  <>
                    <Header as="h5">Tor Configuration</Header>
                    <Form.Field>
                      <label>SOCKS Address</label>
                      <Input
                        onChange={(e) =>
                          updateSetting(
                            'Anonymity.Tor.SocksAddress',
                            e.target.value,
                          )
                        }
                        value={
                          settings.Anonymity.Tor?.SocksAddress ||
                          '127.0.0.1:9050'
                        }
                      />
                    </Form.Field>

                    <Form.Field>
                      <Checkbox
                        checked={
                          settings.Anonymity.Tor?.IsolateStreams || false
                        }
                        label="Isolate Streams Per Peer"
                        onChange={(e, { checked }) =>
                          updateSetting('Anonymity.Tor.IsolateStreams', checked)
                        }
                      />
                    </Form.Field>
                  </>
                )}

                {settings.Anonymity?.Mode === 'I2P' && (
                  <>
                    <Header as="h5">I2P Configuration</Header>
                    <Form.Field>
                      <label>SAM Address</label>
                      <Input
                        onChange={(e) =>
                          updateSetting(
                            'Anonymity.I2P.SamAddress',
                            e.target.value,
                          )
                        }
                        value={
                          settings.Anonymity.I2P?.SamAddress || '127.0.0.1:7656'
                        }
                      />
                    </Form.Field>
                  </>
                )}

                {settings.Anonymity?.Mode === 'RelayOnly' && (
                  <>
                    <Header as="h5">Relay Configuration</Header>
                    <Form.Field>
                      <label>Max Chain Length</label>
                      <Input
                        max="5"
                        min="1"
                        onChange={(e) =>
                          updateSetting(
                            'Anonymity.RelayOnly.MaxChainLength',
                            Number.parseInt(e.target.value),
                          )
                        }
                        type="number"
                        value={
                          settings.Anonymity.RelayOnly?.MaxChainLength || 3
                        }
                      />
                    </Form.Field>
                  </>
                )}
              </>
            )}
          </Form>
        </Tab.Pane>
      ),
    },
    {
      menuItem: 'Transport',
      pane: (
        <Tab.Pane key="transport">
          <Header as="h4">Obfuscated Transport - Anti-DPI</Header>
          <p>Use obfuscated protocols to bypass deep packet inspection.</p>

          <Form>
            <Form.Field>
              <Checkbox
                checked={settings.Transport?.Enabled || false}
                label="Enable Obfuscated Transport"
                onChange={(e, { checked }) =>
                  updateSetting('Transport.Enabled', checked)
                }
              />
            </Form.Field>

            {settings.Transport?.Enabled && (
              <>
                <Form.Field>
                  <label>Primary Transport</label>
                  <Dropdown
                    onChange={(e, { value }) =>
                      updateSetting('Transport.PrimaryTransport', value)
                    }
                    options={transportOptions}
                    selection
                    value={settings.Transport?.PrimaryTransport || 'Direct'}
                  />
                </Form.Field>

                {settings.Transport?.PrimaryTransport === 'WebSocket' && (
                  <>
                    <Header as="h5">WebSocket Configuration</Header>
                    <Form.Field>
                      <label>Server URL</label>
                      <Input
                        onChange={(e) =>
                          updateSetting(
                            'Transport.WebSocket.ServerUrl',
                            e.target.value,
                          )
                        }
                        placeholder="wss://websocket-server.example.com/tunnel"
                        value={settings.Transport.WebSocket?.ServerUrl || ''}
                      />
                      <small
                        style={{
                          color: '#666',
                          display: 'block',
                          marginTop: '5px',
                        }}
                      >
                        WebSocket server that will proxy connections. Traffic
                        appears as normal web traffic to DPI systems.
                      </small>
                    </Form.Field>

                    <Form.Field>
                      <Checkbox
                        checked={settings.Transport.WebSocket?.UseWss || false}
                        label="Use WSS (Secure WebSocket)"
                        onChange={(e, { checked }) =>
                          updateSetting('Transport.WebSocket.UseWss', checked)
                        }
                      />
                    </Form.Field>
                  </>
                )}

                {settings.Transport?.PrimaryTransport === 'HttpTunnel' && (
                  <>
                    <Header as="h5">HTTP Tunnel Configuration</Header>
                    <Form.Field>
                      <label>Proxy URL</label>
                      <Input
                        onChange={(e) =>
                          updateSetting(
                            'Transport.HttpTunnel.ProxyUrl',
                            e.target.value,
                          )
                        }
                        placeholder="https://http-proxy.example.com/tunnel"
                        value={settings.Transport.HttpTunnel?.ProxyUrl || ''}
                      />
                      <small
                        style={{
                          color: '#666',
                          display: 'block',
                          marginTop: '5px',
                        }}
                      >
                        HTTP proxy server that will tunnel connections. Traffic
                        appears as normal HTTP requests.
                      </small>
                    </Form.Field>

                    <Form.Field>
                      <label>HTTP Method</label>
                      <Dropdown
                        onChange={(e, { value }) =>
                          updateSetting('Transport.HttpTunnel.Method', value)
                        }
                        options={[
                          { key: 'POST', text: 'POST', value: 'POST' },
                          { key: 'GET', text: 'GET', value: 'GET' },
                          { key: 'PUT', text: 'PUT', value: 'PUT' },
                        ]}
                        selection
                        value={settings.Transport.HttpTunnel?.Method || 'POST'}
                      />
                    </Form.Field>

                    <Form.Field>
                      <Checkbox
                        checked={
                          settings.Transport.HttpTunnel?.UseHttps || false
                        }
                        label="Use HTTPS"
                        onChange={(e, { checked }) =>
                          updateSetting(
                            'Transport.HttpTunnel.UseHttps',
                            checked,
                          )
                        }
                      />
                    </Form.Field>
                  </>
                )}

                {settings.Transport?.PrimaryTransport === 'Obfs4' && (
                  <>
                    <Header as="h5">Obfs4 Configuration</Header>
                    <Form.Field>
                      <label>Obfs4 Proxy Path</label>
                      <Input
                        onChange={(e) =>
                          updateSetting(
                            'Transport.Obfs4.Obfs4ProxyPath',
                            e.target.value,
                          )
                        }
                        placeholder="/usr/bin/obfs4proxy"
                        value={settings.Transport.Obfs4?.Obfs4ProxyPath || ''}
                      />
                    </Form.Field>

                    <Form.Field>
                      <label>Bridge Lines</label>
                      <small
                        style={{
                          color: '#666',
                          display: 'block',
                          marginBottom: '10px',
                        }}
                      >
                        Tor bridge lines for Obfs4 bridges (one per line)
                      </small>
                      <TextArea
                        onChange={(e) => {
                          const lines = e.target.value
                            .split('\n')
                            .filter((line) => line.trim());
                          updateSetting('Transport.Obfs4.BridgeLines', lines);
                        }}
                        placeholder="obfs4 192.0.2.1:443 1234567890ABCDEF..."
                        rows={4}
                        value={asArray(settings.Transport.Obfs4?.BridgeLines).join('\n')}
                      />
                    </Form.Field>
                  </>
                )}

                {settings.Transport?.PrimaryTransport === 'Obfs4' && (
                  <>
                    <Header as="h5">Obfs4 Configuration</Header>
                    <Form.Field>
                      <label>Bridge Lines</label>
                      {asArray(settings.Transport.Obfs4?.BridgeLines).map(
                        (line, index) => (
                          <div
                            key={index}
                            style={{ marginBottom: '5px' }}
                          >
                            <Input
                              onChange={(e) =>
                                updateArray(
                                  'Transport.Obfs4.BridgeLines',
                                  index,
                                  e.target.value,
                                )
                              }
                              style={{ marginRight: '5px' }}
                              value={line}
                            />
                            <Popup
                              content="Remove this Obfs4 bridge line from the settings."
                              position="top center"
                              trigger={(
                                <Button
                                  aria-label={`Remove Obfs4 bridge line ${index + 1}`}
                                  icon="minus"
                                  onClick={() =>
                                    removeArrayItem(
                                      'Transport.Obfs4.BridgeLines',
                                      index,
                                    )
                                  }
                                  size="mini"
                                />
                              )}
                            />
                          </div>
                        ),
                      )}
                      <Popup
                        content="Add another bridge line for Obfs4 transport."
                        position="top center"
                        trigger={(
                          <Button
                            aria-label="Add Obfs4 bridge line"
                            icon="plus"
                            onClick={() =>
                              addArrayItem('Transport.Obfs4.BridgeLines')
                            }
                            size="mini"
                          />
                        )}
                      />
                    </Form.Field>
                  </>
                )}

                {settings.Transport?.PrimaryTransport === 'Meek' && (
                  <>
                    <Header as="h5">Meek Configuration</Header>
                    <Form.Field>
                      <label>Bridge URL</label>
                      <Input
                        onChange={(e) =>
                          updateSetting(
                            'Transport.Meek.BridgeUrl',
                            e.target.value,
                          )
                        }
                        placeholder="https://meek-bridge.example.com/connect"
                        value={settings.Transport?.Meek?.BridgeUrl || ''}
                      />
                      <small
                        style={{
                          color: '#666',
                          display: 'block',
                          marginTop: '5px',
                        }}
                      >
                        Meek bridge server URL that will proxy connections
                        through domain fronting.
                      </small>
                    </Form.Field>

                    <Form.Field>
                      <label>Front Domain</label>
                      <Input
                        onChange={(e) =>
                          updateSetting(
                            'Transport.Meek.FrontDomain',
                            e.target.value,
                          )
                        }
                        placeholder="www.google.com"
                        value={settings.Transport?.Meek?.FrontDomain || ''}
                      />
                      <small
                        style={{
                          color: '#666',
                          display: 'block',
                          marginTop: '5px',
                        }}
                      >
                        Domain to front through (e.g., major CDN domains).
                        Traffic appears to connect to this domain.
                      </small>
                    </Form.Field>
                  </>
                )}
              </>
            )}
          </Form>
        </Tab.Pane>
      ),
    },
  ];

  return (
    <div className="adversarial-settings">
      <div className="security-header">
        <Header as="h3">
          <Icon name="user secret" />
          <Header.Content>
            Adversarial Settings
            <Header.Subheader>
              Advanced privacy and anonymity features
            </Header.Subheader>
          </Header.Content>
        </Header>
        <div className="security-actions">
          <Popup
            content="Reload the current adversarial settings and transport status."
            position="top center"
            trigger={(
              <Button
                aria-label="Refresh adversarial settings and status"
                icon="refresh"
                onClick={() => {
                  fetchSettings();
                  fetchStatus();
                  fetchTransportStatus();
                  fetchTorStatus();
                }}
                size="tiny"
              />
            )}
          />
          <Popup
            content="Check whether the configured transport can connect."
            position="top center"
            trigger={(
              <Button
                aria-label="Test transport connectivity"
                icon="plug"
                loading={transportLoading}
                onClick={async () => {
                  try {
                    await securityApi.testTransportConnectivity();
                    setSuccess('Transport connectivity test completed');
                    fetchTransportStatus();
                  } catch (error) {
                    setError(
                      error?.response?.data ??
                        error?.message ??
                        'Transport test failed',
                    );
                  }
                }}
                size="tiny"
              />
            )}
          />
          <Popup
            content="Check whether the configured Tor service is reachable."
            position="top center"
            trigger={(
              <Button
                aria-label="Test Tor connectivity"
                icon="shield alternate"
                loading={torLoading}
                onClick={async () => {
                  try {
                    await securityApi.testTorConnectivity();
                    setSuccess('Tor connectivity test completed');
                    fetchTorStatus();
                  } catch (error) {
                    setError(
                      error?.response?.data ??
                        error?.message ??
                        'Tor test failed',
                    );
                  }
                }}
                size="tiny"
              />
            )}
          />
          <Popup
            content="Save the current adversarial settings to this server."
            position="top center"
            trigger={(
              <Button
                aria-label="Save adversarial settings"
                disabled={!hasChanges}
                icon="save"
                loading={saving}
                onClick={handleSave}
                primary
              >
                Save Changes
              </Button>
            )}
          />
        </div>
      </div>

      {error && (
        <Message negative>
          <Message.Header>Error</Message.Header>
          <p>{error}</p>
        </Message>
      )}

      {success && (
        <Message positive>
          <Message.Header>Success</Message.Header>
          <p>{success}</p>
        </Message>
      )}

      <Tab
        activeIndex={activeIndex}
        onTabChange={(_event, { activeIndex: nextIndex }) =>
          setActiveIndex(nextIndex)
        }
        panes={panes}
        renderActiveOnly={false}
      />
    </div>
  );
};

export default AdversarialSettings;
