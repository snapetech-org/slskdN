import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
import * as mesh from '../../../lib/mesh';
import * as soulseekDiscovery from '../../../lib/soulseekDiscovery';
import FeatureGateNotice from '../../Shared/FeatureGateNotice';
import useFeatureGates, { isFeatureEnabled } from '../../Shared/useFeatureGates';
import MeshEvidencePolicy from './MeshEvidencePolicy';
import RealmSubjectIndexConflicts from './RealmSubjectIndexConflicts';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Button,
  Card,
  Grid,
  Header,
  Icon,
  Label,
  List,
  Loader,
  Message,
  Popup,
  Segment,
  Statistic,
} from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);
const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value);
const MESH_STATS_POLL_INTERVAL_MS = 30_000;

const sameMeshStats = (previous, next) =>
  previous?.dht === next?.dht &&
  previous?.overlay === next?.overlay &&
  previous?.natType === next?.natType &&
  previous?.status === next?.status &&
  previous?.description === next?.description &&
  previous?.totalPeers === next?.totalPeers &&
  previous?.activeDhtSessions === next?.activeDhtSessions &&
  previous?.activeOverlaySessions === next?.activeOverlaySessions &&
  previous?.activeMirroredSessions === next?.activeMirroredSessions &&
  previous?.routingTableSize === next?.routingTableSize &&
  previous?.bootstrapPeers === next?.bootstrapPeers &&
  previous?.dhtOperationsPerSecond === next?.dhtOperationsPerSecond &&
  previous?.messagesSent === next?.messagesSent &&
  previous?.messagesReceived === next?.messagesReceived &&
  previous?.peerChurnEvents === next?.peerChurnEvents &&
  previous?.routingTableHealthy === next?.routingTableHealthy &&
  previous?.peerConnectivityHealthy === next?.peerConnectivityHealthy &&
  previous?.messageFlowHealthy === next?.messageFlowHealthy;

const Mesh = () => {
  useInterfaceLanguage();
  const { featureGates, ready: featureGatesReady } = useFeatureGates();
  const meshEnabled = featureGatesReady && isFeatureEnabled(featureGates, 'mesh');
  const dhtEnabled = featureGatesReady && isFeatureEnabled(featureGates, 'dht');
  const mountedRef = useRef(false);
  const statsFetchInFlightRef = useRef(false);
  const statsLoadedRef = useRef(false);
  const statsPollIntervalRef = useRef(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [rendezvousStatus, setRendezvousStatus] = useState(null);
  const [rendezvousUsers, setRendezvousUsers] = useState([]);
  const [capabilityRecords, setCapabilityRecords] = useState([]);
  const [rendezvousLoading, setRendezvousLoading] = useState(false);
  const [rendezvousMessage, setRendezvousMessage] = useState(null);

  const getRendezvousErrorText = (error_, fallback) =>
    getApiErrorMessage(error_, { t: interfaceText }, fallback);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const fetchStats = useCallback(async () => {
    if (
      !meshEnabled ||
      document.hidden ||
      !mountedRef.current ||
      statsFetchInFlightRef.current
    ) {
      return;
    }

    statsFetchInFlightRef.current = true;
    try {
      if (!statsLoadedRef.current) {
        setLoading(true);
        setError(null);
      }

      const data = await mesh.getStats();
      if (!mountedRef.current || document.hidden) return;
      statsLoadedRef.current = true;
      setStats((previous) =>
        sameMeshStats(previous, data) ? previous : data,
      );
      setError(null);
    } catch (error_) {
      if (!mountedRef.current || document.hidden) return;
      if (!statsLoadedRef.current) {
        setError(getApiErrorMessage(error_, { t: interfaceText }));
      }
    } finally {
      statsFetchInFlightRef.current = false;
      if (mountedRef.current && !document.hidden) {
        setLoading(false);
      }
    }
  }, [meshEnabled]);

  useEffect(() => {
    if (!featureGatesReady) return undefined;
    if (!meshEnabled) {
      setStats(null);
      setLoading(false);
      return undefined;
    }

    const stopPolling = () => {
      if (statsPollIntervalRef.current) {
        window.clearInterval(statsPollIntervalRef.current);
        statsPollIntervalRef.current = null;
      }
    };
    const startPolling = () => {
      if (document.hidden || statsPollIntervalRef.current) return;

      fetchStats();
      statsPollIntervalRef.current = window.setInterval(
        fetchStats,
        MESH_STATS_POLL_INTERVAL_MS,
      );
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
    };
  }, [fetchStats, featureGatesReady, meshEnabled]);

  useEffect(() => {
    if (!featureGatesReady || !dhtEnabled) return undefined;

    const fetchRendezvousStatus = async () => {
      try {
        const response = await soulseekDiscovery.getMeshRendezvousStatus();
        if (!mountedRef.current) return;
        setRendezvousStatus(isObject(response.data) ? response.data : {});
      } catch (error_) {
        if (!mountedRef.current) return;
        setRendezvousStatus({
          enabled: false,
          error: getApiErrorMessage(error_, { t: interfaceText }),
        });
      }
    };

    fetchRendezvousStatus();
    return undefined;
  }, [dhtEnabled, featureGatesReady]);

  const handleAddRendezvousInterest = async () => {
    if (!dhtEnabled) return;

    setRendezvousLoading(true);
    setRendezvousMessage(null);
    try {
      await soulseekDiscovery.addMeshRendezvousInterest();
      setRendezvousMessage({
        positive: true,
        text: interfaceText("Published the slskdN mesh rendezvous interest on this Soulseek account."),
      });
    } catch (error_) {
      setRendezvousMessage({
        negative: true,
        text:
          error_?.response?.status === 403
            ? 'Soulseek rendezvous is disabled in configuration. Enable mesh.enableSoulseekRendezvous before publishing this public interest.'
            : getRendezvousErrorText(error_, 'Unable to publish rendezvous interest.'),
      });
    } finally {
      setRendezvousLoading(false);
    }
  };

  const handleRemoveRendezvousInterest = async () => {
    if (!dhtEnabled) return;

    setRendezvousLoading(true);
    setRendezvousMessage(null);
    try {
      await soulseekDiscovery.removeMeshRendezvousInterest();
      setRendezvousMessage({
        positive: true,
        text: interfaceText("Removed the slskdN mesh rendezvous interest from this Soulseek account."),
      });
    } catch (error_) {
      setRendezvousMessage({
        negative: true,
        text:
          error_?.response?.status === 403
            ? 'Soulseek rendezvous is disabled in configuration. Enable mesh.enableSoulseekRendezvous to manage this public interest from the UI.'
            : getRendezvousErrorText(error_, 'Unable to remove rendezvous interest.'),
      });
    } finally {
      setRendezvousLoading(false);
    }
  };

  const handleLoadRendezvousUsers = async () => {
    if (!dhtEnabled) return;

    setRendezvousLoading(true);
    setRendezvousMessage(null);
    try {
      const response = await soulseekDiscovery.discoverMeshRendezvous();
      const data = isObject(response.data) ? response.data : {};
      const users = asArray(data.users).filter(isObject);
      const records = asArray(data.capabilityRecords).filter(isObject);
      setRendezvousUsers(users);
      setCapabilityRecords(records);
      setRendezvousMessage({
        positive: true,
        text: interfaceText('Discovered {users} Soulseek rendezvous candidate(s) and {records} runtime capability record(s).', {
          users: users.length,
          records: records.length,
        }),
      });
    } catch (error_) {
      setRendezvousUsers([]);
      setCapabilityRecords([]);
      setRendezvousMessage({
        negative: true,
        text:
          error_?.response?.status === 403
            ? 'Soulseek rendezvous is disabled in configuration. Enable mesh.enableSoulseekRendezvous before querying candidates.'
            : getRendezvousErrorText(error_, 'Unable to load rendezvous users.'),
      });
    } finally {
      setRendezvousLoading(false);
    }
  };

  const getHealthColor = (status) => {
    switch (status) {
      case 'Healthy':
        return 'green';
      case 'Degraded':
        return 'yellow';
      case 'Unhealthy':
        return 'red';
      default:
        return 'grey';
    }
  };

  const getHealthIcon = (status) => {
    switch (status) {
      case 'Healthy':
        return 'checkmark';
      case 'Degraded':
        return 'warning sign';
      case 'Unhealthy':
        return 'remove';
      default:
        return 'question';
    }
  };

  if (featureGatesReady && !meshEnabled) {
    return (
      <div>
        <Header as="h2">
          <Icon name="sitemap" />
          <LocalizedText source={"Mesh Network Status"} /></Header>
        <FeatureGateNotice
          configurationKeys={['feature.Mesh', 'mesh.enable_overlay']}
          featureGate={featureGates.mesh}
          featureName="Mesh"
        />
        <FeatureGateNotice
          configurationKeys={['feature.Dht', 'dht.enabled']}
          featureGate={featureGates.dht}
          featureName="DHT rendezvous"
        />
      </div>
    );
  }

  if (loading && !stats) {
    return (
      <Segment>
        <Loader
          active
          inline="centered"
        >
          <LocalizedText source={"Loading mesh statistics..."} /></Loader>
      </Segment>
    );
  }

  if (error) {
    return (
      <Message error>
        <Message.Header><LocalizedText source={"Failed to load mesh statistics"} /></Message.Header>
        <p>{error}</p>
      </Message>
    );
  }

  return (
    <div>
      <Header as="h2">
        <Icon name="sitemap" />
        <LocalizedText source={"Mesh Network Status"} /></Header>
      <FeatureGateNotice
        configurationKeys={['feature.Dht', 'dht.enabled']}
        featureGate={featureGates.dht}
        featureName="DHT rendezvous"
      />

      <Grid stackable>
        {/* Overall Health Status */}
        <Grid.Column width={16}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon
                  color={getHealthColor(stats?.status)}
                  name={getHealthIcon(stats?.status)}
                />
                <LocalizedText source={"Network Health:"} />{" "}{stats?.status || <LocalizedText source={"Unknown"} />}
              </Card.Header>
              <Card.Description>
                {stats?.description || <LocalizedText source={"No health information available"} />}
              </Card.Description>
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Key Statistics */}
        <Grid.Column width={16}>
          <Segment>
            <Header as="h3"><LocalizedText source={"Network Statistics"} /></Header>
            <Statistic.Group size="small">
              <Statistic>
                <Statistic.Value>{stats?.totalPeers || 0}</Statistic.Value>
                <Statistic.Label><LocalizedText source={"Total Peers"} /></Statistic.Label>
              </Statistic>
              <Statistic>
                <Statistic.Value>
                  {stats?.activeDhtSessions || 0}
                </Statistic.Value>
                <Statistic.Label><LocalizedText source={"DHT Sessions"} /></Statistic.Label>
              </Statistic>
              <Statistic>
                <Statistic.Value>
                  {stats?.activeOverlaySessions || 0}
                </Statistic.Value>
                <Statistic.Label><LocalizedText source={"Overlay Sessions"} /></Statistic.Label>
              </Statistic>
              <Statistic>
                <Statistic.Value>
                  {stats?.routingTableSize || 0}
                </Statistic.Value>
                <Statistic.Label><LocalizedText source={"Routing Table Size"} /></Statistic.Label>
              </Statistic>
            </Statistic.Group>
          </Segment>
        </Grid.Column>

        {/* Connection Details */}
        <Grid.Column width={8}>
          <Segment>
            <Header as="h3">
              <Icon name="plug" />
              <LocalizedText source={"Connections"} /></Header>
            <List
              divided
              relaxed
            >
              <List.Item>
                <List.Content>
                  <List.Header><LocalizedText source={"DHT Nodes"} /></List.Header>
                  <List.Description>
                    {stats?.activeDhtSessions || 0} <LocalizedText source={"active connections"} /></List.Description>
                </List.Content>
              </List.Item>
              <List.Item>
                <List.Content>
                  <List.Header><LocalizedText source={"Overlay Sessions"} /></List.Header>
                  <List.Description>
                    {stats?.activeOverlaySessions || 0} <LocalizedText source={"active sessions"} /></List.Description>
                </List.Content>
              </List.Item>
              <List.Item>
                <List.Content>
                  <List.Header><LocalizedText source={"Mirrored Sessions"} /></List.Header>
                  <List.Description>
                    {stats?.activeMirroredSessions || 0} <LocalizedText source={"relay connections"} /></List.Description>
                </List.Content>
              </List.Item>
              <List.Item>
                <List.Content>
                  <List.Header><LocalizedText source={"Bootstrap Peers"} /></List.Header>
                  <List.Description>
                    {stats?.bootstrapPeers || 0} <LocalizedText source={"bootstrap nodes"} /></List.Description>
                </List.Content>
              </List.Item>
            </List>
          </Segment>
        </Grid.Column>

        {/* Performance Metrics */}
        <Grid.Column width={8}>
          <Segment>
            <Header as="h3">
              <Icon name="chart line" />
              <LocalizedText source={"Performance"} /></Header>
            <List
              divided
              relaxed
            >
              <List.Item>
                <List.Content>
                  <List.Header><LocalizedText source={"DHT Operations/sec"} /></List.Header>
                  <List.Description>
                    {stats?.dhtOperationsPerSecond?.toFixed(1) || '0.0'} ops/sec
                  </List.Description>
                </List.Content>
              </List.Item>
              <List.Item>
                <List.Content>
                  <List.Header><LocalizedText source={"Messages Sent"} /></List.Header>
                  <List.Description>
                    {stats?.messagesSent || 0} <LocalizedText source={"total messages"} /></List.Description>
                </List.Content>
              </List.Item>
              <List.Item>
                <List.Content>
                  <List.Header><LocalizedText source={"Messages Received"} /></List.Header>
                  <List.Description>
                    {stats?.messagesReceived || 0} <LocalizedText source={"total messages"} /></List.Description>
                </List.Content>
              </List.Item>
              <List.Item>
                <List.Content>
                  <List.Header><LocalizedText source={"Peer Churn Events"} /></List.Header>
                  <List.Description>
                    {stats?.peerChurnEvents || 0} <LocalizedText source={"churn events"} /></List.Description>
                </List.Content>
              </List.Item>
            </List>
          </Segment>
        </Grid.Column>

        {/* NAT and Network Info */}
        <Grid.Column width={16}>
          <Segment>
            <Header as="h3">
              <Icon name="shield" />
              <LocalizedText source={"Network Configuration"} /></Header>
            <Grid>
              <Grid.Column width={8}>
                <List>
                  <List.Item>
                    <List.Content>
                      <List.Header><LocalizedText source={"NAT Type"} /></List.Header>
                      <List.Description>
                        <Label
                          color={
                            stats?.natType === 'Direct' ? 'green' : 'yellow'
                          }
                        >
                          {stats?.natType || <LocalizedText source={"Unknown"} />}
                        </Label>
                      </List.Description>
                    </List.Content>
                  </List.Item>
                </List>
              </Grid.Column>
              <Grid.Column width={8}>
                <List>
                  <List.Item>
                    <List.Content>
                      <List.Header><LocalizedText source={"Health Indicators"} /></List.Header>
                      <List.Description>
                        <Label
                          color={stats?.routingTableHealthy ? 'green' : 'red'}
                        >
                          <LocalizedText source={"Routing Table:"} />{' '}
                          {stats?.routingTableHealthy ? <LocalizedText source={"Healthy"} /> : <LocalizedText source={"Unhealthy"} />}
                        </Label>
                        <br />
                        <Label
                          color={
                            stats?.peerConnectivityHealthy ? 'green' : 'red'
                          }
                        >
                          <LocalizedText source={"Peer Connectivity:"} />{' '}
                          {stats?.peerConnectivityHealthy
                            ? <LocalizedText source={"Healthy"} />
                            : <LocalizedText source={"Unhealthy"} />}
                        </Label>
                        <br />
                        <Label
                          color={stats?.messageFlowHealthy ? 'green' : 'red'}
                        >
                          <LocalizedText source={"Message Flow:"} />{' '}
                          {stats?.messageFlowHealthy ? <LocalizedText source={"Healthy"} /> : <LocalizedText source={"Unhealthy"} />}
                        </Label>
                      </List.Description>
                    </List.Content>
                  </List.Item>
                </List>
              </Grid.Column>
            </Grid>
          </Segment>
        </Grid.Column>

        <Grid.Column width={16}>
          <Segment>
            <Header as="h3">
              <Icon name="users" />
              <LocalizedText source={"Soulseek Mesh Rendezvous"} /></Header>
            <Message
              icon
              warning={!rendezvousStatus?.enabled}
            >
              <Icon name={rendezvousStatus?.enabled ? 'privacy' : 'lock'} />
              <Message.Content>
                <Message.Header>
                  {!dhtEnabled
                    ? <LocalizedText source={"DHT rendezvous is disabled by its feature gate"} />
                    : rendezvousStatus?.enabled
                    ? <LocalizedText source={"Opt-in public rendezvous is enabled"} />
                    : <LocalizedText source={"Opt-in public rendezvous is disabled"} />}
                </Message.Header>
                <p>
                  {dhtEnabled
                    ? <LocalizedText source={"This feature uses the native Soulseek interest graph to find other slskdN mesh-capable accounts. Publishing the interest tag makes this account visibly identifiable as a slskdN mesh participant."} />
                    : <LocalizedText source={"Review the DHT feature gate notice above before using public rendezvous controls."} />}
                </p>
                {dhtEnabled && (
                  <p>
                    <LocalizedText source={"Interest tag:"} />{' '}
                    <code>{rendezvousStatus?.interestTag || 'slskdn-mesh-v1'}</code>
                  </p>
                )}
                {dhtEnabled && !rendezvousStatus?.enabled && (
                  <p>
                    <LocalizedText source={"Enable"} />{" "}<code>mesh.enableSoulseekRendezvous</code> <LocalizedText source={"in configuration before using these controls."} /></p>
                )}
              </Message.Content>
            </Message>
            {rendezvousMessage && (
              <Message
                negative={rendezvousMessage.negative}
                positive={rendezvousMessage.positive}
              >
                {rendezvousMessage.text}
              </Message>
            )}
            <div className="mesh-rendezvous-actions">
              <Popup
                content={interfaceText("Publish the slskdN rendezvous interest on this Soulseek account so other mesh-capable users can discover it.")}
                position="top center"
                trigger={(
                  <Button
                    disabled={!dhtEnabled || !rendezvousStatus?.enabled || rendezvousLoading}
                    loading={rendezvousLoading}
                    onClick={handleAddRendezvousInterest}
                    positive
                  >
                    <Icon name="bullhorn" />
                    <LocalizedText source={"Publish Interest"} /></Button>
                )}
               {...interfaceTextProps("Publish the slskdN rendezvous interest on this Soulseek account so other mesh-capable users can discover it.")}/>
              <Popup
                content={interfaceText("Remove this account's public slskdN rendezvous interest when you no longer want to appear in mesh discovery.")}
                position="top center"
                trigger={(
                  <Button
                    disabled={!dhtEnabled || !rendezvousStatus?.enabled || rendezvousLoading}
                    loading={rendezvousLoading}
                    onClick={handleRemoveRendezvousInterest}
                  >
                    <Icon name="remove circle" />
                    <LocalizedText source={"Remove Interest"} /></Button>
                )}
               {...interfaceTextProps("Remove this account's public slskdN rendezvous interest when you no longer want to appear in mesh discovery.")}/>
              <Popup
                content={interfaceText("Search the Soulseek interest graph for opted-in mesh accounts and their published capabilities.")}
                position="top center"
                trigger={(
                  <Button
                    disabled={!dhtEnabled || !rendezvousStatus?.enabled || rendezvousLoading}
                    loading={rendezvousLoading}
                    onClick={handleLoadRendezvousUsers}
                    primary
                  >
                    <Icon name="search" />
                    <LocalizedText source={"Load Candidates"} /></Button>
                )}
               {...interfaceTextProps("Search the Soulseek interest graph for opted-in mesh accounts and their published capabilities.")}/>
            </div>
            {rendezvousUsers.length > 0 && (
              <List
                divided
                relaxed
                style={{ marginTop: '1rem' }}
              >
                {rendezvousUsers.map((user) => (
                  <List.Item key={user.username || user.Username}>
                    <List.Icon
                      name="user"
                      verticalAlign="middle"
                    />
                    <List.Content>
                      <List.Header>{user.username || user.Username}</List.Header>
                      <List.Description>
                        <LocalizedText source={"Similarity rating:"} />{' '}
                        {user.rating ?? user.Rating ?? 'not reported'}
                      </List.Description>
                    </List.Content>
                  </List.Item>
                ))}
              </List>
            )}
            {capabilityRecords.length > 0 && (
              <List
                divided
                relaxed
                style={{ marginTop: '1rem' }}
              >
                {capabilityRecords.map((record) => (
                  <List.Item key={`${record.username}-${record.nonce}`}>
                    <List.Icon
                      name={record.signed ? 'certificate' : 'id card outline'}
                      verticalAlign="middle"
                    />
                    <List.Content>
                      <List.Header>{record.username}</List.Header>
                      <List.Description>
                        {record.peerId || 'unsigned peer'}, {' '}
                        {asArray(record.features).join(', ') || 'no features'}, {' '}
                        <LocalizedText source={"overlay port"} />{" "}{record.overlayPort || 'not advertised'}
                      </List.Description>
                    </List.Content>
                  </List.Item>
                ))}
              </List>
            )}
          </Segment>
        </Grid.Column>

        <Grid.Column width={16}>
          <MeshEvidencePolicy />
        </Grid.Column>

        <Grid.Column width={16}>
          <RealmSubjectIndexConflicts />
        </Grid.Column>
      </Grid>
    </div>
  );
};

export default Mesh;
