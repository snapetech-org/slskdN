import LocalizedText from "./LocalizedText";
import { interfaceText, interfaceTextProps } from "../../lib/interfaceLocale";


import './Footer.css';
import footerLogo from '../../assets/brand/slskdn-icon-wire.png';
import * as application from '../../lib/application';
import * as session from '../../lib/session';
import * as slskdnAPI from '../../lib/slskdn';
import { getLocalStorageItem } from '../../lib/storage';
import * as transfers from '../../lib/transfers';
import { urlBase } from '../../config';
import React, { Component } from 'react';
import { Icon } from 'semantic-ui-react';

const GITHUB_BASE = 'https://github.com/snapetech/slskdn';
const SLSKD_GITHUB = 'https://github.com/slskd/slskd';
const SPEED_POLL_INTERVAL_MS = 2_000;
const STATS_POLL_INTERVAL_MS = 10_000;

const formatSpeed = (bytesPerSec) => {
  if (!bytesPerSec || bytesPerSec === 0) return { unit: 'B', value: '0' };

  const kb = bytesPerSec / 1_024;
  const mb = kb / 1_024;
  const gb = mb / 1_024;

  if (gb >= 1) {
    return { unit: 'G', value: gb.toFixed(gb >= 10 ? 1 : 2) };
  }

  if (mb >= 1) {
    return { unit: 'M', value: mb.toFixed(mb >= 10 ? 1 : 2) };
  }

  if (kb >= 1) {
    return { unit: 'K', value: kb.toFixed(kb >= 10 ? 1 : 2) };
  }

  return { unit: 'B', value: bytesPerSec.toFixed(0) };
};

const formatBytes = (bytes) => {
  if (!bytes || bytes === 0) return { unit: 'B', value: '0' };
  const kb = bytes / 1_024;
  const mb = kb / 1_024;
  const gb = mb / 1_024;
  if (gb >= 1) return { unit: 'GB', value: gb.toFixed(gb >= 10 ? 1 : 2) };
  if (mb >= 1) return { unit: 'MB', value: mb.toFixed(mb >= 10 ? 1 : 2) };
  if (kb >= 1) return { unit: 'KB', value: kb.toFixed(kb >= 10 ? 1 : 2) };
  return { unit: 'B', value: bytes.toFixed(0) };
};

const formatCount = (value) => {
  if (value === undefined || value === null) return '0';
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toString();
};

const setFooterHeightVariable = (element) => {
  if (!element || typeof document === 'undefined') return;

  const height = Math.ceil(element.getBoundingClientRect().height);
  if (height > 0) {
    document.documentElement.style.setProperty(
      '--slskdn-footer-height',
      `${height}px`,
    );
  }
};

class Footer extends Component {
  constructor(props) {
    super(props);
    this.state = {
      buildInfo: null,
      slskdnStats: null,
      speeds: null,
      stats: null,
    };
    this.footerRef = React.createRef();
    this.footerResizeObserver = null;
    this._fetchSpeedsInFlight = false;
    this._fetchStatsInFlight = false;
    this._isMounted = false;
    this._displaySpeeds = null;
    this._lastNonZeroAt = 0;
    this._speedsInterval = null;
    this._statsInterval = null;
  }

  componentDidMount() {
    this._isMounted = true;
    this.updateFooterHeight();
    if (
      typeof window !== 'undefined' &&
      typeof window.ResizeObserver === 'function' &&
      this.footerRef.current
    ) {
      this.footerResizeObserver = new window.ResizeObserver(
        this.updateFooterHeight,
      );
      this.footerResizeObserver.observe(this.footerRef.current);
    }

    this.fetchBuildInfo();

    if (session.isLoggedIn()) {
      document.addEventListener('visibilitychange', this.handleVisibilityChange);
      this.startPolling();
    }
  }

  componentWillUnmount() {
    this._isMounted = false;
    document.removeEventListener(
      'visibilitychange',
      this.handleVisibilityChange,
    );
    this.stopPolling();
    if (this.footerResizeObserver) {
      this.footerResizeObserver.disconnect();
      this.footerResizeObserver = null;
    }
  }

  componentDidUpdate() {
    this.updateFooterHeight();
  }

  updateFooterHeight = () => {
    setFooterHeightVariable(this.footerRef.current);
  };

  startPolling = () => {
    if (document.hidden || !session.isLoggedIn()) return;

    this.fetchStats();
    this.fetchSpeeds();
    if (!this._speedsInterval) {
      this._speedsInterval = window.setInterval(
        this.fetchSpeeds,
        SPEED_POLL_INTERVAL_MS,
      );
    }
    if (!this._statsInterval) {
      this._statsInterval = window.setInterval(
        this.fetchStats,
        STATS_POLL_INTERVAL_MS,
      );
    }
  };

  stopPolling = () => {
    window.clearInterval(this._speedsInterval);
    window.clearInterval(this._statsInterval);
    this._speedsInterval = null;
    this._statsInterval = null;
  };

  handleVisibilityChange = () => {
    if (document.hidden) {
      this.stopPolling();
    } else {
      this.startPolling();
    }
  };

  fetchStats = async () => {
    if (
      document.hidden ||
      !session.isLoggedIn() ||
      this._fetchStatsInFlight
    ) {
      return;
    }

    this._fetchStatsInFlight = true;
    try {
      const slskdnStats = await slskdnAPI.getSlskdnStats();

      if (this._isMounted && !document.hidden) {
        this.setState({
          slskdnStats,
          stats: slskdnStats?.transport ?? null,
        });
      }
    } catch (error) {
      // Silently fail - stats are non-critical
      console.debug('Failed to fetch mesh stats:', error);
    } finally {
      this._fetchStatsInFlight = false;
    }
  };

  fetchSpeeds = async () => {
    if (
      document.hidden ||
      !session.isLoggedIn() ||
      this._fetchSpeedsInFlight
    ) {
      return;
    }

    this._fetchSpeedsInFlight = true;
    try {
      const raw = await transfers.getSpeeds();
      if (!this._isMounted || document.hidden) return;

      const now = Date.now();
      const HOLD_MS = 3_000;
      const DECAY = 0.65;
      const FLOOR = 512; // below this, snap to 0 during decay

      let displayed;
      if (!this._displaySpeeds || raw.total > 0) {
        // Active or first poll: snap to live value
        displayed = raw;
        if (raw.total > 0) this._lastNonZeroAt = now;
      } else {
        const idleMs = now - this._lastNonZeroAt;
        if (idleMs < HOLD_MS) {
          // Hold: keep last displayed speeds
          displayed = { ...this._displaySpeeds, sessionBytesDownloaded: raw.sessionBytesDownloaded, sessionBytesUploaded: raw.sessionBytesUploaded, sessionBytesTotal: raw.sessionBytesTotal };
        } else {
          // Decay: exponential fade toward zero
          const fade = (v) => (v > FLOOR ? v * DECAY : 0);
          displayed = {
            total: fade(this._displaySpeeds.total),
            soulseek: fade(this._displaySpeeds.soulseek),
            mesh: fade(this._displaySpeeds.mesh),
            download: fade(this._displaySpeeds.download),
            upload: fade(this._displaySpeeds.upload),
            sessionBytesDownloaded: raw.sessionBytesDownloaded,
            sessionBytesUploaded: raw.sessionBytesUploaded,
            sessionBytesTotal: raw.sessionBytesTotal,
          };
        }
      }

      this._displaySpeeds = displayed;
      this.setState({ speeds: displayed });
    } catch (error) {
      console.debug('Failed to fetch transfer speeds:', error);
    } finally {
      this._fetchSpeedsInFlight = false;
    }
  };

  fetchBuildInfo = async () => {
    try {
      const buildInfo = await application.getBuild({ checkForUpdates: true });
      this.setState({ buildInfo });
    } catch (error) {
      console.debug('Failed to fetch build info:', error);
    }
  };

  render() {
    const year = new Date().getFullYear();
    const { buildInfo, slskdnStats, speeds, stats } = this.state;
    const isLoggedIn = session.isLoggedIn();
    const currentBuild = buildInfo?.current || buildInfo?.full || 'unknown';
    const fullBuild = buildInfo?.full || currentBuild;
    const latestBuild = buildInfo?.latest || '';
    const latestTag = buildInfo?.latestTag || latestBuild;
    const latestUrl = buildInfo?.latestUrl || `${GITHUB_BASE}/releases`;
    const isUpdateAvailable = buildInfo?.isUpdateAvailable === true;
    const dht = slskdnStats?.dht || {};
    const hashDb = slskdnStats?.hashDb || {};
    const meshStats = slskdnStats?.mesh || {};
    const swarmJobs = Array.isArray(slskdnStats?.swarmJobs)
      ? slskdnStats.swarmJobs
      : [];
    const dhtNodes = Number(dht.dhtNodeCount) || Number(stats?.dht) || 0;
    const discoveredPeers = Number(dht.discoveredPeerCount) || 0;
    const displayedDhtPeers = discoveredPeers || dhtNodes;
    const meshPeers = Number(meshStats.connectedPeerCount) || 0;
    const hashCount = Number(hashDb.totalEntries) || 0;
    const seqId =
      Number(hashDb.currentSeqId) || Number(meshStats.localSeqId) || 0;
    const isSyncing = Boolean(meshStats.isSyncing);
    const backfillActive = Boolean(slskdnStats?.backfill?.isActive);
    const activeSwarms = swarmJobs.length;
    const karma = Number.parseInt(getLocalStorageItem('slskdn-karma', '0'), 10);
    const totalSpeed = isLoggedIn && speeds ? formatSpeed(speeds.total) : null;
    const soulseekSpeed =
      isLoggedIn && speeds ? formatSpeed(speeds.soulseek) : null;
    const meshSpeed = isLoggedIn && speeds ? formatSpeed(speeds.mesh) : null;
    const sessionTotal =
      isLoggedIn && speeds != null
        ? formatBytes(speeds.sessionBytesTotal ?? 0)
        : null;

    // Determine if stats are connected
    const isDhtConnected = isLoggedIn && displayedDhtPeers > 0;
    const isOverlayConnected = isLoggedIn && stats && stats.overlay > 0;
    const isNatResolved =
      isLoggedIn && stats && stats.natType && stats.natType !== 'Unknown';

    // Format NAT type tooltip
    const natTooltip = isLoggedIn && stats
      ? interfaceText('NAT Type: {natType}', { natType: stats.natType || interfaceText('Unknown') })
      : interfaceText('NAT: Login to see stats');
    const networkTooltip = isLoggedIn
      ? interfaceText('DHT peers: {dhtPeers}; DHT nodes: {dhtNodes}; mesh peers: {meshPeers}; hashes: {hashes}; seq: {sequence}', {
        dhtPeers: displayedDhtPeers,
        dhtNodes,
        meshPeers,
        hashes: hashCount,
        sequence: seqId,
      })
      : interfaceText('Login to see slskdN network stats');

    if (!isLoggedIn) {
      // Nothing here is real yet — no donation asks, build badge, or live
      // telemetry before someone has even signed in. Just attribution.
      return (
        <footer
          className="slskdn-footer slskdn-footer-minimal"
          ref={this.footerRef}
        >
          <span className="slskdn-footer-copyright">
            © {year}{' '}
            <a
              href={GITHUB_BASE}
              rel="noopener noreferrer"
              target="_blank"
              title={interfaceText("slskdN project")}
             {...interfaceTextProps("slskdN project")}>
              <LocalizedText source={"slskdN"} /></a>
            <span className="slskdn-footer-note"><LocalizedText source={"unofficial fork of"} /></span>
            <a
              href={SLSKD_GITHUB}
              rel="noopener noreferrer"
              target="_blank"
              title={interfaceText("slskd upstream project")}
             {...interfaceTextProps("slskd upstream project")}>
              <LocalizedText source={"slskd"} /></a>
          </span>
        </footer>
      );
    }

    return (
      <footer
        className="slskdn-footer"
        ref={this.footerRef}
      >
        <div className="slskdn-footer-content">
          <div className="slskdn-footer-left">
            <div className="slskdn-footer-brand">
              <a
                className="slskdn-footer-logo"
                href={GITHUB_BASE}
                rel="noopener noreferrer"
                target="_blank"
                title={interfaceText("Open the slskdN GitHub project")}
               {...interfaceTextProps("Open the slskdN GitHub project")}>
                <img
                  alt={interfaceText("slskdN")}
                  src={footerLogo}
                 {...interfaceTextProps("slskdN")}/>
              </a>



              <span className="slskdn-footer-copyright">
                © {year}{' '}
                <a
                  href={GITHUB_BASE}
                  rel="noopener noreferrer"
                  target="_blank"
                  title={interfaceText("slskdN project")}
                 {...interfaceTextProps("slskdN project")}>
                  <LocalizedText source={"slskdN"} /></a>
                <span className="slskdn-footer-note"><LocalizedText source={"unofficial fork of"} /></span>
                <a
                  href={SLSKD_GITHUB}
                  rel="noopener noreferrer"
                  target="_blank"
                  title={interfaceText("slskd upstream project")}
                 {...interfaceTextProps("slskd upstream project")}>
                  <LocalizedText source={"slskd"} /></a>
              </span>
              <a
                className={`slskdn-footer-build ${isUpdateAvailable ? 'update-available' : ''}`}
                href={isUpdateAvailable ? latestUrl : `${GITHUB_BASE}/releases`}
                rel="noopener noreferrer"
                target="_blank"
                title={isUpdateAvailable
                  ? interfaceText('Running {currentBuild}; GitHub has {latestBuild}', {
                    currentBuild: fullBuild,
                    latestBuild: latestTag || latestBuild,
                  })
                  : interfaceText('Running {currentBuild}', { currentBuild: fullBuild })}
              >
                <Icon name={isUpdateAvailable ? 'bullhorn' : 'code branch'} />
                <span className="slskdn-footer-build-label"><LocalizedText source={"Build"} /></span>
                <code>{currentBuild}</code>
                {isUpdateAvailable && (
                  <span className="slskdn-footer-update-label">
                    <LocalizedText source={"update"} />{" "}{latestBuild}
                  </span>
                )}
              </a>
            </div>
          </div>

          <div className="slskdn-footer-center">
            <div
              className={`slskdn-footer-speeds ${isLoggedIn && speeds ? 'active' : ''}`}
              aria-label={interfaceText("Transfer speeds")}
             {...interfaceTextProps("Transfer speeds")}>
              <span className="slskdn-footer-group-label"><LocalizedText source={"Speed"} /></span>
              <span
                className="slskdn-footer-speed-item"
                title={interfaceText(isLoggedIn
                  ? 'Total transfer speed (upload + download)'
                  : 'Login to see real-time speeds')}
              >
                <strong>T:</strong>{' '}
                <span className="speed-value">
                  {totalSpeed ? totalSpeed.value : '0'}
                </span>
                <span className="speed-unit">{totalSpeed ? totalSpeed.unit : <LocalizedText source={"B"} />}</span>
              </span>
              <span
                className="slskdn-footer-speed-item"
                title={interfaceText(isLoggedIn
                  ? 'Soulseek network speed'
                  : 'Login to see real-time speeds')}
              >
                <strong>S:</strong>{' '}
                <span className="speed-value">
                  {soulseekSpeed ? soulseekSpeed.value : '0'}
                </span>
                <span className="speed-unit">
                  {soulseekSpeed ? soulseekSpeed.unit : <LocalizedText source={"B"} />}
                </span>
              </span>
              <span
                className="slskdn-footer-speed-item"
                title={interfaceText(isLoggedIn
                  ? 'Mesh network speed'
                  : 'Login to see real-time speeds')}
              >
                <strong>M:</strong>{' '}
                <span className="speed-value">
                  {meshSpeed ? meshSpeed.value : '0'}
                </span>
                <span className="speed-unit">{meshSpeed ? meshSpeed.unit : <LocalizedText source={"B"} />}</span>
              </span>
              {sessionTotal && (
                <span
                  className="slskdn-footer-speed-item slskdn-footer-session-total"
                  title={interfaceText('Session total: {downloaded} / {uploaded}', {
                    downloaded: speeds.sessionBytesDownloaded
                      ? `${formatBytes(speeds.sessionBytesDownloaded).value}${formatBytes(speeds.sessionBytesDownloaded).unit} ↓`
                      : '0',
                    uploaded: speeds.sessionBytesUploaded
                      ? `${formatBytes(speeds.sessionBytesUploaded).value}${formatBytes(speeds.sessionBytesUploaded).unit} ↑`
                      : '0',
                  })}
                >
                  <span className="speed-value">{sessionTotal.value}</span>
                  <span className="speed-unit">{sessionTotal.unit}</span>
                  <span className="slskdn-footer-session-label"><LocalizedText source={"session"} /></span>
                </span>
              )}
            </div>
          </div>

          <div className="slskdn-footer-right">
            <a
              className={`slskdn-footer-network ${isLoggedIn && slskdnStats ? 'active' : ''}`}
              href={`${urlBase}/system/network`}
              title={networkTooltip}
            >
              <span className="slskdn-footer-group-label"><LocalizedText source={"Network"} /></span>
              <span className="slskdn-footer-network-item">
                <Icon
                  color={displayedDhtPeers > 0 ? 'green' : 'grey'}
                  name="rss"
                />
                {formatCount(displayedDhtPeers)} <LocalizedText source={"dht"} /></span>
              <span className="slskdn-footer-network-item">
                <Icon
                  color={meshPeers > 0 ? 'green' : 'grey'}
                  name="sitemap"
                />
                {formatCount(meshPeers)} <LocalizedText source={"mesh"} /></span>
              <span className="slskdn-footer-network-item">
                <Icon
                  color={hashCount > 0 ? 'blue' : 'grey'}
                  name="database"
                />
                {formatCount(hashCount)} <LocalizedText source={"hashes"} /></span>
              <span
                className={`slskdn-footer-network-item ${isSyncing ? 'syncing' : ''}`}
              >
                <Icon
                  color={isSyncing ? 'yellow' : 'grey'}
                  loading={isSyncing}
                  name="sync"
                />
                <LocalizedText source={"seq:"} />{seqId}
              </span>
              {activeSwarms > 0 && (
                <span className="slskdn-footer-network-item active">
                  <Icon name="bolt" />
                  {activeSwarms} <LocalizedText source={activeSwarms === 1 ? "swarm" : "swarms"} />
                </span>
              )}
              {backfillActive && (
                <span className="slskdn-footer-network-item active">
                  <Icon
                    loading
                    name="clock"
                  />
                  <LocalizedText source={"backfill"} /></span>
              )}
              <span className="slskdn-footer-network-item">
                <Icon name="trophy" />
                {karma > 0 ? '+' : ''}
                {karma}
              </span>
            </a>

            <div
              className="slskdn-footer-stats"
              aria-label={interfaceText("Transport health")}
             {...interfaceTextProps("Transport health")}>
              <Icon
                className={
                  isDhtConnected
                    ? 'slskdn-footer-stat-icon connected'
                    : 'slskdn-footer-stat-icon'
                }
                name="sitemap"
                title={isLoggedIn && stats
                  ? interfaceText('DHT Nodes: {count}', { count: stats.dht })
                  : interfaceText('DHT: Login to see stats')}
              />
              <Icon
                className={
                  isNatResolved
                    ? 'slskdn-footer-stat-icon connected'
                    : 'slskdn-footer-stat-icon'
                }
                name="shield alternate"
                title={natTooltip}
              />
              <Icon
                className={
                  isOverlayConnected
                    ? 'slskdn-footer-stat-icon connected'
                    : 'slskdn-footer-stat-icon'
                }
                name="globe"
                title={isLoggedIn && stats
                  ? interfaceText('Overlay Peers: {count}', { count: stats.overlay })
                  : interfaceText('Overlay: Login to see stats')}
              />
            </div>
          </div>
        </div>
      </footer>
    );
  }
}

export default Footer;
