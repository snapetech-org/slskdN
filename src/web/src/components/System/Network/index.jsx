import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";


import * as slskdnAPI from '../../../lib/slskdn';
import { formatRegionalCompactNumber, formatRegionalNumber, useRegionalLocale } from '../../../lib/regionalFormat';
import { formatBytes as formatLocalizedBytes } from '../../../lib/util';
import FeatureGateNotice from '../../Shared/FeatureGateNotice';
import useFeatureGates, { isFeatureEnabled } from '../../Shared/useFeatureGates';
import {
  buildNetworkHealthScore,
  formatNetworkHealthReport,
} from '../../../lib/networkHealthScore';
import { getLocalStorageItem, setLocalStorageItem } from '../../../lib/storage';
import { ShrinkableButton } from '../../Shared';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'react-toastify';
import {
  Button,
  Card,
  Divider,
  Grid,
  Header,
  Icon,
  Label,
  List,
  Message,
  Popup,
  Progress,
  Segment,
  Statistic,
  Table,
} from 'semantic-ui-react';

const DHT_EXPOSURE_CONSENT_KEY = 'slskdn:ui:dht-public-exposure:consent-v1';
const NETWORK_POLL_INTERVAL_MS = 10_000;

const asArray = (value) => (Array.isArray(value) ? value : []);

const formatBytes = (bytes) => formatLocalizedBytes(bytes, 1);

const formatTimeAgo = (dateString, locale) => {
  if (!dateString) return <LocalizedText source="Never" />;
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return <LocalizedText source="Unknown" />;

  const seconds = Math.round((date.getTime() - Date.now()) / 1_000);
  const absoluteSeconds = Math.abs(seconds);
  const [value, unit] = absoluteSeconds < 60
    ? [seconds, 'second']
    : absoluteSeconds < 3_600
      ? [Math.round(seconds / 60), 'minute']
      : absoluteSeconds < 86_400
        ? [Math.round(seconds / 3_600), 'hour']
        : [Math.round(seconds / 86_400), 'day'];
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });
  const resolvedLocale = formatter.resolvedOptions().locale;
  const direction = /^ar(?:-|$)/i.test(resolvedLocale) ? 'rtl' : 'ltr';

  return <span lang={resolvedLocale} dir={direction}>{formatter.format(value, unit)}</span>;
};

const StatCard = ({ color, icon, inverted = false, label, subLabel, value }) => (
  <Card raised={inverted}>
    <Card.Content>
      <Card.Header style={inverted ? { color: 'rgba(255, 255, 255, 0.92)' } : undefined}>
        <Icon
          color={color}
          name={icon}
        />{' '}
        {value}
      </Card.Header>
      <Card.Meta style={inverted ? { color: 'rgba(255, 255, 255, 0.7)' } : undefined}>
        {label}
      </Card.Meta>
      {subLabel && (
        <Card.Description
          style={inverted ? { color: 'rgba(255, 255, 255, 0.82)' } : undefined}
        >
          {subLabel}
        </Card.Description>
      )}
    </Card.Content>
  </Card>
);

// eslint-disable-next-line complexity
const LocalizedNetworkFindingSummary = ({ source, locale }) => {
  const securityMatch = source.match(/^(\d+) mesh security signal(s?) visible$/);
  if (securityMatch) return <LocalizedText source={securityMatch[2] ? "{count} mesh security signals visible" : "{count} mesh security signal visible"} values={{ count: formatRegionalNumber(Number(securityMatch[1]), undefined, locale) }} />;
  const backfillMatch = source.match(/^(\d+) pending backfill candidates$/);
  if (backfillMatch) return <LocalizedText source="{count} pending backfill candidates" values={{ count: formatRegionalNumber(Number(backfillMatch[1]), undefined, locale) }} />;
  return <LocalizedText source={source} />;
};

const LocalizedMeshWarning = ({ source, locale }) => {
  const warningMatch = typeof source === 'string' && source.match(/^(Signature verification failures|Rate limit violations|Quarantine events) \((\d+)\) >= (\d+)$/);
  if (!warningMatch) return <LocalizedText source={source} />;

  const sourceByWarning = {
    'Signature verification failures': 'Signature verification failures ({count}) >= {threshold}',
    'Rate limit violations': 'Rate limit violations ({count}) >= {threshold}',
    'Quarantine events': 'Quarantine events ({count}) >= {threshold}',
  };
  return (
    <LocalizedText
      source={sourceByWarning[warningMatch[1]]}
      values={{
        count: formatRegionalNumber(Number(warningMatch[2]), undefined, locale),
        threshold: formatRegionalNumber(Number(warningMatch[3]), undefined, locale),
      }}
    />
  );
};

const Network = ({ theme }) => {
  useInterfaceLanguage();
  const regionalLocale = useRegionalLocale();
  const formatNumber = (value) => {
    if (value === undefined || value === null) {
      return formatRegionalCompactNumber(0, { maximumFractionDigits: 1 }, regionalLocale);
    }
    return formatRegionalCompactNumber(value, { maximumFractionDigits: 1 }, regionalLocale);
  };
  const { featureGates, ready: featureGatesReady } = useFeatureGates();
  const meshEnabled = featureGatesReady && isFeatureEnabled(featureGates, 'mesh');
  const multiSourceEnabled =
    featureGatesReady && isFeatureEnabled(featureGates, 'multiSourceDownloads');
  const fetchInFlightRef = useRef(false);
  const mountedRef = useRef(false);
  const pollIntervalRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({});
  const [meshPeers, setMeshPeers] = useState([]);
  const [discoveredPeers, setDiscoveredPeers] = useState([]);
  const [syncing, setSyncing] = useState({});
  const [backfilling, setBackfilling] = useState(false);
  const [backfillProgress, setBackfillProgress] = useState(null);
  const [dhtExposureAcknowledged, setDhtExposureAcknowledged] = useState(() => {
    return getLocalStorageItem(DHT_EXPOSURE_CONSENT_KEY) === 'acknowledged';
  });

  const fetchData = useCallback(async () => {
    if (document.hidden || fetchInFlightRef.current) {
      return;
    }

    fetchInFlightRef.current = true;
    try {
      const statsData = await slskdnAPI.getSlskdnStats({
        includePeers: true,
      });

      if (!mountedRef.current) return;

      setStats(statsData || {});
      setMeshPeers(asArray(statsData?.meshPeers));
      setDiscoveredPeers(asArray(statsData?.discoveredPeers));
    } catch (error) {
      if (!mountedRef.current) return;
      console.error('Failed to fetch network stats:', error);
      // Don't show toast on every poll failure
    } finally {
      fetchInFlightRef.current = false;
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  const dismissDhtExposureConsent = () => {
    setLocalStorageItem(DHT_EXPOSURE_CONSENT_KEY, 'acknowledged');
    setDhtExposureAcknowledged(true);
  };

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    const stopPolling = () => {
      if (pollIntervalRef.current) {
        window.clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
    const startPolling = () => {
      if (document.hidden || pollIntervalRef.current) {
        return;
      }

      fetchData();
      pollIntervalRef.current = window.setInterval(
        fetchData,
        NETWORK_POLL_INTERVAL_MS,
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
  }, [fetchData]);

  const handleSync = async (username) => {
    if (!meshEnabled) return;

    setSyncing((previous) => ({ ...previous, [username]: true }));
    try {
      const result = await slskdnAPI.triggerMeshSync(username);
      if (!result?.success) {
        toast.error(result?.error || `Failed to sync with ${username}`);
        return;
      }

      toast.success(interfaceText("Sync initiated with {username}", { "username": (username) }));
    } catch {
      toast.error(interfaceText("Failed to sync with {username}", { "username": (username) }));
    } finally {
      setSyncing((previous) => ({ ...previous, [username]: false }));
    }
  };

  const handleBackfillFromHistory = async (reset = false) => {
    setBackfilling(true);
    try {
      const result = await slskdnAPI.backfillFromSearchHistory({
        batchSize: 50,
        reset,
      });

      if (result.error) {
        toast.error(interfaceText("Backfill failed: {error}", { "error": (result.error) }));
        setBackfillProgress(null);
      } else {
        setBackfillProgress(result);

        if (result.complete) {
          toast.success(
            <LocalizedText
              source="Backfill complete! Processed {searches} searches, discovered {files} FLACs."
              values={{
                searches: formatNumber(result.searchesProcessed ?? 0),
                files: formatNumber(result.flacsDiscovered ?? 0),
              }}
            />,
          );
        } else {
          toast.info(
            <LocalizedText
              source="Processed {searches} searches, discovered {files} FLACs. {remaining} searches remaining - click again to continue."
              values={{
                searches: formatNumber(result.searchesProcessed ?? 0),
                files: formatNumber(result.flacsDiscovered ?? 0),
                remaining: formatNumber(result.remainingSearches ?? 0),
              }}
            />,
          );
        }

        fetchData(); // Refresh stats
      }
    } catch {
      toast.error(interfaceText("Failed to trigger backfill from search history"));
      setBackfillProgress(null);
    } finally {
      setBackfilling(false);
    }
  };

  const { backfill, capabilities, hashDb, mesh, swarmJobs } = stats;
  const obfuscation = capabilities?.obfuscation;
  const darkTheme = theme === 'dark';
  const dhtIsLanOnly = stats?.dht?.isLanOnly ?? stats?.dht?.lanOnly ?? false;
  const dhtIsRunning = stats?.dht?.isDhtRunning ?? false;
  const dhtNodeCount = stats?.dht?.dhtNodeCount ?? 0;
  const dhtDiscoveredPeerCount =
    stats?.dht?.discoveredPeerCount ?? stats?.dht?.totalPeersDiscovered ?? 0;
  const dhtActiveMeshCount = stats?.dht?.activeMeshConnections ?? 0;
  const observedMeshPeerCount = Math.max(
    meshPeers.length,
    mesh?.connectedPeerCount ?? 0,
    dhtActiveMeshCount,
  );
  const observedDiscoveredPeerCount = Math.max(
    discoveredPeers.length,
    dhtDiscoveredPeerCount,
  );
  const shouldExplainLanOnlyDht =
    dhtIsLanOnly &&
    (stats?.dht?.isEnabled ?? false) &&
    dhtNodeCount === 0 &&
    observedMeshPeerCount === 0 &&
    observedDiscoveredPeerCount === 0;
  const shouldWarnAboutConnectivity =
    !shouldExplainLanOnlyDht &&
    dhtIsRunning &&
    dhtNodeCount === 0 &&
    observedMeshPeerCount === 0 &&
    observedDiscoveredPeerCount === 0;
  const shouldShowDhtExposureNotice =
    (stats?.dht?.isEnabled ?? false) &&
    !dhtIsLanOnly &&
    dhtIsRunning &&
    !dhtExposureAcknowledged;
  const networkHealth = buildNetworkHealthScore({
    discoveredPeers,
    meshPeers,
    stats,
  });

  const copyNetworkHealthReport = async () => {
    const report = formatNetworkHealthReport(networkHealth);
    if (navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(report);
        toast.success(interfaceText("Network health report copied"));
      } catch {
        toast.error(interfaceText("Unable to copy network health report"));
      }
      return;
    }

    toast.info(interfaceText("Clipboard unavailable; select the report text manually"));
  };

  return (
    <div className="network-dashboard">
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
      <FeatureGateNotice
        configurationKeys={['feature.MultiSourceDownloads']}
        featureGate={featureGates.multiSourceDownloads}
        featureName="Multi-source downloads"
      />
      {loading && (
        <Message info>
          <Icon
            loading
            name="spinner"
          />
          <LocalizedText source={"Loading network status"} /></Message>
      )}
      {shouldExplainLanOnlyDht && (
        <Message
          className="network-diagnostic-message"
          info
        >
          <Message.Header><LocalizedText source={"LAN-only DHT is isolated"} /></Message.Header>
          <p>
            <LocalizedText source={"LAN-only mesh uses"} />{" "}<code>dhtRendezvous.lanOnly: true</code><LocalizedText source={", so slskdN intentionally disables the public BitTorrent DHT engine. In this privacy mode,"} />{" "}<code>0</code> <LocalizedText source={"DHT nodes and"} />{" "}<code>0</code> <LocalizedText source={"discovered peers are expected, even when the overlay and DHT ports are open."} /></p>
          <p>
            <LocalizedText source={"To discover public slskdN peers through DHT rendezvous, set"} /><code> dhtRendezvous.lanOnly: false</code> <LocalizedText source={"and restart. Keep LAN-only enabled if you want discovery limited to local or already-known private peers."} /></p>
        </Message>
      )}
      {shouldWarnAboutConnectivity && (
        <Message
          className="network-diagnostic-message"
          warning
        >
          <Message.Header><LocalizedText source={"Connectivity diagnostics"} /></Message.Header>
          <p>
            <LocalizedText source={"slskdN is not seeing reachable peers yet. If you can log into the Soulseek server but uploads, downloads, and peer counts stay at zero, verify that your configured Soulseek listen port is reachable from other peers. The default is"} />{" "}<code>50300/tcp</code>.
          </p>
          <p>
            <LocalizedText source={"Check local firewall rules, router/NAT forwarding, container port publishing, and any reverse-proxy setup that might expose the Web UI but not the Soulseek listen port."} /></p>
        </Message>
      )}
      {shouldShowDhtExposureNotice && (
        <Message
          className="network-diagnostic-message"
          info
        >
          <div className="network-dht-exposure-header">
            <Message.Header><LocalizedText source={"Public DHT exposure notice"} /></Message.Header>
            <Popup
              content={interfaceText("Dismiss this public DHT exposure notice on this browser after reviewing it.")}
              position="top right"
              trigger={(
                <Button
                  aria-label={interfaceText("Dismiss public DHT exposure notice")}
                  basic
                  className="network-dht-dismiss-button"
                  icon
                  onClick={dismissDhtExposureConsent}
                  title={interfaceText("Dismiss public DHT exposure notice")}
                 {...interfaceTextProps("Dismiss public DHT exposure notice")}>
                  <Icon name="close" />
                </Button>
              )}
             {...interfaceTextProps("Dismiss this public DHT exposure notice on this browser after reviewing it.")}/>
          </div>
          <p>
            <LocalizedText source={"DHT rendezvous is enabled and this node can publish its public endpoint into the public BitTorrent DHT. This is expected when public rendezvous is enabled; this notice is only here so operators are aware that other slskdN peers can discover the node for mesh sync."} /></p>
          <p>
            <LocalizedText source={"If you want to keep mesh discovery confined to trusted local peers, set"} />{" "}<code>dht.lan_only=true</code> <LocalizedText source={"in configuration before long-term operation."} /></p>
        </Message>
      )}

      {/* Header Stats */}
      <Card.Group
        itemsPerRow={4}
        stackable
      >
        <StatCard
          color="blue"
          icon="sitemap"
          inverted={darkTheme}
          label={<LocalizedText source="Mesh Peers" />}
          subLabel={<LocalizedText source="slskdN clients connected" />}
          value={formatNumber(mesh?.connectedPeerCount ?? meshPeers.length ?? 0)}
        />
        <StatCard
          color="green"
          icon="database"
          inverted={darkTheme}
          label={<LocalizedText source="Hash Entries" />}
          subLabel={
            hashDb?.dbSizeBytes !== undefined && hashDb?.dbSizeBytes !== null
              ? <LocalizedText source="{size} on disk" values={{ size: formatBytes(hashDb.dbSizeBytes) }} />
              : <LocalizedText source="Local database" />
          }
          value={formatNumber(hashDb?.totalEntries ?? 0)}
        />
        <StatCard
          color="purple"
          icon="sync"
          inverted={darkTheme}
          label={<LocalizedText source="Sequence ID" />}
          subLabel={<LocalizedText source="Mesh sync position" />}
          value={formatRegionalNumber(hashDb?.currentSeqId ?? mesh?.localSeqId ?? 0, undefined, regionalLocale)}
        />
        <StatCard
          color="orange"
          icon="bolt"
          inverted={darkTheme}
          label={<LocalizedText source="Active Swarms" />}
          subLabel={<LocalizedText source="Multi-source downloads" />}
          value={multiSourceEnabled ? formatNumber(swarmJobs?.length ?? 0) : <LocalizedText source="Disabled" />}
        />
      </Card.Group>

      <Divider />

      <Segment className="network-health-panel">
        <div className="network-health-head">
          <Header as="h4">
            <Icon name="heartbeat" />
            <Header.Content>
              <LocalizedText source={"Network Health"} /><Header.Subheader>
                <LocalizedText source={"Local readiness score from already-loaded mesh, DHT, HashDb, and security counters"} /></Header.Subheader>
            </Header.Content>
          </Header>
          <Popup
            content={interfaceText("Copy a local network-health report for diagnostics. This does not query peers or change network state.")}
            position="top center"
            trigger={
              <Button
                aria-label={interfaceText("Copy network health report")}
                onClick={copyNetworkHealthReport}
                size="small"
               {...interfaceTextProps("Copy network health report")}>
                <Icon name="copy" />
                <LocalizedText source={"Copy Report"} /></Button>
            }
           {...interfaceTextProps("Copy a local network-health report for diagnostics. This does not query peers or change network state.")}/>
        </div>
        <div className="network-health-score-row">
          <Progress
            color={
              networkHealth.score >= 85
                ? 'green'
                : networkHealth.score >= 65
                  ? 'yellow'
                  : 'red'
            }
            percent={networkHealth.score}
            progress
          >
            <LocalizedText source={networkHealth.label} />
          </Progress>
          {/* These four are inputs to the score above, not states of their
              own — one neutral pill style, not four unrelated hues. */}
          <Label basic>
            <LocalizedText source={"Mesh"} /><Label.Detail>{formatNumber(networkHealth.inputs.meshCount)}</Label.Detail>
          </Label>
          <Label basic>
            <LocalizedText source={"Discovered"} /><Label.Detail>{formatNumber(networkHealth.inputs.discoveredCount)}</Label.Detail>
          </Label>
          <Label basic>
            DHT
            <Label.Detail>{formatNumber(networkHealth.inputs.dhtNodes)}</Label.Detail>
          </Label>
          <Label
            basic={networkHealth.inputs.securityWarningCount === 0}
            color={networkHealth.inputs.securityWarningCount > 0 ? 'orange' : undefined}
          >
            <LocalizedText source={"Security"} /><Label.Detail>{formatNumber(networkHealth.inputs.securityWarningCount)}</Label.Detail>
          </Label>
        </div>
        {networkHealth.findings.length > 0 ? (
          <List
            divided
            relaxed
          >
            {networkHealth.findings.map((finding) => (
              <List.Item key={`${finding.area}-${finding.summary}`}>
                <List.Icon
                  color={
                    finding.severity === 'fail'
                      ? 'red'
                      : finding.severity === 'warn'
                        ? 'yellow'
                        : 'blue'
                  }
                  name={
                    finding.severity === 'fail'
                      ? 'warning sign'
                      : finding.severity === 'warn'
                        ? 'exclamation triangle'
                        : 'info circle'
                  }
                  verticalAlign="middle"
                />
                <List.Content>
                  <List.Header>
                    <LocalizedText source={finding.area} />: <LocalizedNetworkFindingSummary source={finding.summary} locale={regionalLocale} />
                  </List.Header>
                  <List.Description><LocalizedText source={finding.action} /></List.Description>
                </List.Content>
              </List.Item>
            ))}
          </List>
        ) : (
          <Message
            className="network-diagnostic-message"
            positive
          >
            <Message.Header><LocalizedText source={"No local network-health findings"} /></Message.Header>
            <p>
              <LocalizedText source={"Mesh, DHT, HashDb, and security counters look healthy from the already-loaded dashboard data."} /></p>
          </Message>
        )}
      </Segment>

      {/* Our Capabilities */}
      <Segment>
        <Header as="h4">
          <Icon name="id card" />
          <Header.Content>
            <LocalizedText source={"Our Capabilities"} /><Header.Subheader>
              <LocalizedText source={"What we advertise to other slskdN peers"} /></Header.Subheader>
          </Header.Content>
        </Header>

        <Label.Group>
          <Label color="blue">
            <Icon name="code branch" />
            {capabilities?.version ?? 'slskdN'}
          </Label>
          {asArray(capabilities?.features).map((feature) => (
            <Label
              color="teal"
              key={feature}
            >
              <Icon name="check" />
              {feature}
            </Label>
          )) ?? (
            <>
              <Label color="teal">
                <Icon name="check" />
                multi_source
              </Label>
              <Label color="teal">
                <Icon name="check" />
                hash_db
              </Label>
              <Label color="teal">
                <Icon name="check" />
                mesh_sync
              </Label>
            </>
          )}
        </Label.Group>
        {obfuscation && (
          <Message
            info={!obfuscation.enabled}
            warning={obfuscation.enabled && !obfuscation.runtimeSupported}
            positive={obfuscation.enabled && obfuscation.runtimeSupported}
          >
            <Message.Header><LocalizedText source={"Soulseek Type-1 Obfuscation"} /></Message.Header>
            <p>{obfuscation.summary}</p>
            <Label.Group>
              <Label color={obfuscation.enabled ? 'teal' : 'grey'}>
                {obfuscation.enabled ? <LocalizedText source={"enabled"} /> : <LocalizedText source={"disabled"} />}
              </Label>
              <Label color="blue"><LocalizedText source={"mode:"} />{" "}{obfuscation.mode}</Label>
              <Label color="blue"><LocalizedText source={"type:"} />{" "}{obfuscation.type}</Label>
              <Label color="blue">
                <LocalizedText source={"streams:"} />{" "}{(obfuscation.supportedConnectionTypes ?? []).join(', ') || interfaceText('unset')}
              </Label>
              <Label color="blue">
                <LocalizedText source={"obfuscated port:"} />{" "}{obfuscation.effectiveListenPort ?? interfaceText('unset')}
              </Label>
              <Label color={obfuscation.advertiseRegularPort ? 'green' : 'grey'}>
                <LocalizedText source={"regular fallback:"} />{' '}
                {obfuscation.advertiseRegularPort ? <LocalizedText source={"advertised"} /> : <LocalizedText source={"off"} />}
              </Label>
              <Label color={obfuscation.runtimeSupported ? 'green' : 'orange'}>
                <LocalizedText source={"runtime:"} />{" "}{obfuscation.runtimeState}
              </Label>
            </Label.Group>
          </Message>
        )}
      </Segment>

      <Grid
        columns={2}
        stackable
      >
        {/* Mesh Peers */}
        <Grid.Column>
          <Segment>
            <Header as="h4">
              <Icon name="sitemap" />
              <Header.Content>
                <LocalizedText source={"Mesh Peers"} /><Header.Subheader>
                  <LocalizedText source={"Connected slskdN clients for hash sync"} /></Header.Subheader>
              </Header.Content>
            </Header>

            {meshPeers.length === 0 ? (
              <Segment
                basic
                placeholder
                textAlign="center"
              >
                <Header icon>
                  <Icon name="users" />
                  <LocalizedText source={"No mesh peers connected"} /></Header>
                <p><LocalizedText source={"Other slskdN clients will appear here when discovered"} /></p>
              </Segment>
            ) : (
              <Table
                basic="very"
                compact
              >
                <Table.Header>
                  <Table.Row>
                    <Table.HeaderCell><LocalizedText source={"Peer"} /></Table.HeaderCell>
                    <Table.HeaderCell><LocalizedText source={"Seq ID"} /></Table.HeaderCell>
                    <Table.HeaderCell><LocalizedText source={"Last Sync"} /></Table.HeaderCell>
                    <Table.HeaderCell><LocalizedText source={"Actions"} /></Table.HeaderCell>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  {meshPeers.map((peer) => (
                    <Table.Row key={peer.username}>
                      <Table.Cell>
                        <Icon
                          color="green"
                          name="circle"
                          size="tiny"
                        />{' '}
                        {peer.username}
                      </Table.Cell>
                      <Table.Cell>{peer.lastSeqId == null ? '-' : formatRegionalNumber(peer.lastSeqId, undefined, regionalLocale)}</Table.Cell>
                      <Table.Cell>{formatTimeAgo(peer.lastSyncAt, regionalLocale)}</Table.Cell>
                      <Table.Cell>
                        <ShrinkableButton
                          compact
                          disabled={!meshEnabled || syncing[peer.username]}
                          icon="sync"
                          loading={syncing[peer.username]}
                          mediaQuery="(max-width: 500px)"
                          onClick={() => handleSync(peer.username)}
                          primary
                          size="mini"
                          tooltip={`Sync hash data with ${peer.username}. Use this when its sequence is behind yours.`}
                        >
                          <LocalizedText source={"Sync"} /></ShrinkableButton>
                      </Table.Cell>
                    </Table.Row>
                  ))}
                </Table.Body>
              </Table>
            )}
          </Segment>
        </Grid.Column>

        {/* Discovered Peers */}
        <Grid.Column>
          <Segment>
            <Header as="h4">
              <Icon name="search" />
              <Header.Content>
                <LocalizedText source={"Discovered slskdN Peers"} /><Header.Subheader>
                  <LocalizedText source={"Peers with slskdN capabilities detected"} /></Header.Subheader>
              </Header.Content>
            </Header>

            {discoveredPeers.length === 0 ? (
              <Segment
                basic
                placeholder
                textAlign="center"
              >
                <Header icon>
                  <Icon name="radar" />
                  <LocalizedText source={"No slskdN peers discovered yet"} /></Header>
                <p><LocalizedText source={"Peers are discovered through searches and downloads"} /></p>
              </Segment>
            ) : (
              <List
                divided
                relaxed
              >
                {discoveredPeers.slice(0, 10).map((peer) => (
                  <List.Item key={peer.username}>
                    <List.Icon
                      color="blue"
                      name="user"
                      verticalAlign="middle"
                    />
                    <List.Content>
                      <List.Header>{peer.username}</List.Header>
                      <List.Description>
                        {peer.version ?? 'slskdN'} <LocalizedText source={"• Last seen:"} />{' '}
                        {formatTimeAgo(peer.lastSeenAt, regionalLocale)}
                      </List.Description>
                    </List.Content>
                  </List.Item>
                ))}
                {discoveredPeers.length > 10 && (
                  <List.Item>
                    <List.Content>
                      <em>
                      <LocalizedText
                        source={"...and {count} more"}
                        values={{ count: formatNumber(discoveredPeers.length - 10) }}
                      />
                      </em>
                    </List.Content>
                  </List.Item>
                )}
              </List>
            )}
          </Segment>
        </Grid.Column>
      </Grid>

      <Divider />

      {/* Mesh Sync Security */}
      <Segment>
        <Header as="h4">
          <Icon name="shield alternate" />
          <Header.Content>
            <LocalizedText source={"Mesh Sync Security"} /><Header.Subheader>
              <LocalizedText source={"Counters for signatures, reputation, rate limits, and quarantine"} /></Header.Subheader>
          </Header.Content>
        </Header>
        {asArray(mesh?.warnings).length > 0 && (
          <Message
            attached="top"
            negative
            size="small"
          >
            <Message.Header>
              <Icon name="exclamation triangle" />
              <LocalizedText source={"Security threshold alerts"} /></Message.Header>
            <List
              bulleted
              size="small"
            >
              {asArray(mesh?.warnings).map((warning, index) => (
                <List.Item key={index}><LocalizedMeshWarning source={warning} locale={regionalLocale} /></List.Item>
              ))}
            </List>
          </Message>
        )}
        <Statistic.Group
          inverted={darkTheme}
          size="small"
          widths={7}
        >
          <Statistic>
            <Statistic.Value>
              {formatNumber(mesh?.signatureVerificationFailures ?? 0)}
            </Statistic.Value>
            <Statistic.Label><LocalizedText source={"Sig. failures"} /></Statistic.Label>
          </Statistic>
          <Statistic>
            <Statistic.Value>
              {formatNumber(mesh?.reputationBasedRejections ?? 0)}
            </Statistic.Value>
            <Statistic.Label><LocalizedText source={"Rep. rejections"} /></Statistic.Label>
          </Statistic>
          <Statistic>
            <Statistic.Value>
              {formatNumber(mesh?.rateLimitViolations ?? 0)}
            </Statistic.Value>
            <Statistic.Label><LocalizedText source={"Rate limits"} /></Statistic.Label>
          </Statistic>
          <Statistic>
            <Statistic.Value>
              {formatNumber(mesh?.quarantinedPeers ?? 0)}
            </Statistic.Value>
            <Statistic.Label><LocalizedText source={"Quarantined"} /></Statistic.Label>
          </Statistic>
          <Statistic>
            <Statistic.Value>
              {formatNumber(mesh?.quarantineEvents ?? 0)}
            </Statistic.Value>
            <Statistic.Label><LocalizedText source={"Quarantine events"} /></Statistic.Label>
          </Statistic>
          <Statistic>
            <Statistic.Value>
              {formatNumber(mesh?.rejectedMessages ?? 0)}
            </Statistic.Value>
            <Statistic.Label><LocalizedText source={"Rejected msgs"} /></Statistic.Label>
          </Statistic>
          <Statistic>
            <Statistic.Value>
              {formatNumber(mesh?.skippedEntries ?? 0)}
            </Statistic.Value>
            <Statistic.Label><LocalizedText source={"Skipped entries"} /></Statistic.Label>
          </Statistic>
        </Statistic.Group>
      </Segment>

      <Divider />

      {/* Hash Database Details */}
      <Segment>
        <Header as="h4">
          <Icon name="database" />
          <Header.Content>
            <LocalizedText source={"Hash Database"} /><Header.Subheader>
              <LocalizedText source={"Content-addressed FLAC fingerprints"} /></Header.Subheader>
          </Header.Content>
          <span style={{ float: 'right', marginTop: '-0.5em' }}>
            {backfillProgress && !backfillProgress.complete && (
              <Label
                size="tiny"
                style={{ marginRight: '0.5em' }}
              >
                {formatNumber(backfillProgress.remainingSearches)} <LocalizedText source={"searches left"} /></Label>
            )}
            <Popup
              content={
                backfillProgress && !backfillProgress.complete
                  ? <LocalizedText
                    source="Continue processing search history ({remaining} of {total} searches remain)."
                    values={{
                      remaining: formatNumber(backfillProgress.remainingSearches ?? 0),
                      total: formatNumber(backfillProgress.totalSearches ?? 0),
                    }}
                  />
                  : <LocalizedText source="Scan past searches to add their FLAC files to the hash inventory for multi-source downloads. Large histories are processed in batches; click again to continue." />
              }
              position="top right"
              trigger={
                <ShrinkableButton
                  compact
                  disabled={backfilling}
                  icon={
                    backfillProgress && !backfillProgress.complete
                      ? 'play'
                      : 'history'
                  }
                  loading={backfilling}
                  mediaQuery="(max-width: 500px)"
                  onClick={() => handleBackfillFromHistory(false)}
                  primary
                  size="mini"
                >
                  {backfillProgress && !backfillProgress.complete
                    ? <LocalizedText source={"Continue"} />
                    : <LocalizedText source={"Backfill from History"} />}
                </ShrinkableButton>
              }
            />
            {backfillProgress && (
              <Popup
                content={interfaceText("Reset progress and start backfill from the beginning")}
                position="top right"
                trigger={
                  <ShrinkableButton
                    compact
                    disabled={backfilling}
                    icon="redo"
                    mediaQuery="(max-width: 500px)"
                    onClick={() => handleBackfillFromHistory(true)}
                    size="mini"
                    style={{ marginLeft: '0.3em' }}
                  >
                    <LocalizedText source={"Reset"} /></ShrinkableButton>
                }
               {...interfaceTextProps("Reset progress and start backfill from the beginning")}/>
            )}
          </span>
        </Header>

        <Statistic.Group
          inverted={darkTheme}
          size="tiny"
          widths={4}
        >
          <Statistic>
            <Statistic.Value>
              {formatNumber(hashDb?.totalEntries ?? 0)}
            </Statistic.Value>
            <Statistic.Label><LocalizedText source={"Total Entries"} /></Statistic.Label>
          </Statistic>
          <Statistic>
            <Statistic.Value>
              {formatNumber(hashDb?.uniqueFiles ?? hashDb?.totalEntries ?? 0)}
            </Statistic.Value>
            <Statistic.Label><LocalizedText source={"Unique Files"} /></Statistic.Label>
          </Statistic>
          <Statistic>
            <Statistic.Value>
              {formatBytes(hashDb?.dbSizeBytes ?? 0)}
            </Statistic.Value>
            <Statistic.Label><LocalizedText source={"Database Size"} /></Statistic.Label>
          </Statistic>
          <Statistic>
            <Statistic.Value>{formatRegionalNumber(hashDb?.currentSeqId ?? 0, undefined, regionalLocale)}</Statistic.Value>
            <Statistic.Label><LocalizedText source={"Sequence ID"} /></Statistic.Label>
          </Statistic>
        </Statistic.Group>

        {hashDb?.coveragePercent !== undefined && (
          <>
            <Divider hidden />
            <Progress
              color="green"
              percent={hashDb.coveragePercent}
              progress
              size="small"
            >
              <LocalizedText source={"Coverage of shared FLACs"} /></Progress>
          </>
        )}
      </Segment>

      {/* Backfill Scheduler */}
      <Segment>
        <Header as="h4">
          <Icon name="clock" />
          <Header.Content>
            <LocalizedText source={"Backfill Scheduler"} /><Header.Subheader>
              <LocalizedText source={"Conservative discovery of hashes from non-slskdN peers"} /></Header.Subheader>
          </Header.Content>
        </Header>

        <Grid
          columns={4}
          stackable
        >
          <Grid.Column>
            <Statistic
              inverted={darkTheme}
              size="mini"
            >
              <Statistic.Value>
                <Icon
                  color={backfill?.isActive ? 'green' : 'grey'}
                  name="circle"
                />{' '}
                {backfill?.isActive ? <LocalizedText source={"Active"} /> : <LocalizedText source={"Idle"} />}
              </Statistic.Value>
              <Statistic.Label><LocalizedText source={"Status"} /></Statistic.Label>
            </Statistic>
          </Grid.Column>
          <Grid.Column>
            <Statistic
              inverted={darkTheme}
              size="mini"
            >
              <Statistic.Value>{formatNumber(backfill?.pendingCount ?? 0)}</Statistic.Value>
              <Statistic.Label><LocalizedText source={"Pending Files"} /></Statistic.Label>
            </Statistic>
          </Grid.Column>
          <Grid.Column>
            <Statistic
              inverted={darkTheme}
              size="mini"
            >
              <Statistic.Value>{formatNumber(backfill?.completedToday ?? 0)}</Statistic.Value>
              <Statistic.Label><LocalizedText source={"Completed Today"} /></Statistic.Label>
            </Statistic>
          </Grid.Column>
          <Grid.Column>
            <Statistic
              inverted={darkTheme}
              size="mini"
            >
              <Statistic.Value>
                {formatNumber(backfill?.discoveryRate ?? 0)}/hr
              </Statistic.Value>
              <Statistic.Label><LocalizedText source={"Discovery Rate"} /></Statistic.Label>
            </Statistic>
          </Grid.Column>
        </Grid>
      </Segment>

      {/* Active Swarm Downloads */}
      {multiSourceEnabled && swarmJobs && swarmJobs.length > 0 && (
        <Segment>
          <Header as="h4">
            <Icon name="bolt" />
            <Header.Content>
              <LocalizedText source={"Active Swarm Downloads"} /><Header.Subheader>
                <LocalizedText source={"Multi-source downloads in progress"} /></Header.Subheader>
            </Header.Content>
          </Header>

          {swarmJobs.map((job) => (
            <Card
              fluid
              key={job.jobId}
            >
              <Card.Content>
                <Card.Header>
                  <Icon
                    color="yellow"
                    name="bolt"
                  />
                  {job.filename?.split('/').pop() ?? 'Unknown file'}
                </Card.Header>
                <Card.Meta>
                  {formatNumber(job.activeSources ?? 0)} <LocalizedText source={"sources •"} />{' '}
                  {formatBytes(job.downloadedBytes ?? 0)} /{' '}
                  {formatBytes(job.totalBytes ?? 0)}
                </Card.Meta>
                <Progress
                  active
                  color="blue"
                  percent={job.progressPercent ?? 0}
                  progress
                  size="small"
                />
                {asArray(job.workers).length > 0 && (
                  <List
                    horizontal
                    size="small"
                  >
                    {asArray(job.workers).slice(0, 5).map((worker) => (
                      <List.Item key={worker.username}>
                        <Label size="tiny">
                          <Icon name="user" />
                          {worker.username}
                          <Label.Detail>
                            {formatBytes(worker.speedBps ?? 0)}/s
                          </Label.Detail>
                        </Label>
                      </List.Item>
                    ))}
                    {job.workers.length > 5 && (
                      <List.Item>
                        <Label size="tiny">
                          +{formatNumber(job.workers.length - 5)} <LocalizedText source={"more"} /></Label>
                      </List.Item>
                    )}
                  </List>
                )}
              </Card.Content>
            </Card>
          ))}
        </Segment>
      )}
    </div>
  );
};

export default Network;
