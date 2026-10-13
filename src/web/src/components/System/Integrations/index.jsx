import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps } from "../../../lib/interfaceLocale";
import * as federationDiagnostics from '../../../lib/federationDiagnostics';
import * as lidarr from '../../../lib/lidarr';
import * as optionsApi from '../../../lib/options';
import * as YAML from 'yaml';
import MetadataSettingsPanel from './MetadataSettingsPanel';
import MetadataProcessingPanel from './MetadataProcessingPanel';
import FtpIntegrationPanel from './FtpIntegrationPanel';
import SourceFeedIntegrationsPanel from './SourceFeedIntegrationsPanel';
import VpnPanel from './VpnPanel';
import MediaServerPanel from './MediaServerPanel';
import NotificationIntegrationsPanel from './NotificationIntegrationsPanel';
import LidarrPanel from './LidarrPanel';
import ServarrReadinessPanel from './ServarrReadinessPanel';
import FederationDiagnosticsPanel from './FederationDiagnosticsPanel';
import {
  buildServarrCompatibilityPreview,
  buildServarrReadiness,
  formatServarrCompatibilityReport,
  summarizeServarrReadiness,
} from '../../../lib/servarrReadiness';
import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Checkbox,
  Form,
  Header,
  Icon,
  Input,
  Label,
  Message,
  Popup,
  Segment,
  Table,
} from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);

const getOption = (source, ...keys) => {
  for (const key of keys) {
    if (source && Object.prototype.hasOwnProperty.call(source, key)) {
      return source[key];
    }
  }

  return undefined;
};

const getIntegrationsOptions = (options = {}) =>
  getOption(options, 'integration', 'Integration', 'integrations', 'Integrations') ||
  {};

const getVpnOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'vpn', 'Vpn', 'VPN') || {};

const getLidarrOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'lidarr', 'Lidarr') || {};

const getSpotifyOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'spotify', 'Spotify') || {};

const getYouTubeOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'youtube', 'YouTube') || {};

const getLastFmOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'lastfm', 'lastFm', 'LastFm') || {};

const getPushbulletOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'pushbullet', 'Pushbullet') || {};

const getNtfyOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'ntfy', 'Ntfy') || {};

const getPushoverOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'pushover', 'Pushover') || {};

const getFtpOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'ftp', 'Ftp', 'FTP') || {};

const getChromaprintOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'chromaprint', 'Chromaprint') || {};

const getAcoustIdOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'acoustId', 'acoustid', 'AcoustId') ||
  {};

const getMusicBrainzOptions = (options = {}) =>
  getOption(
    getIntegrationsOptions(options),
    'musicBrainz',
    'musicbrainz',
    'MusicBrainz',
  ) || {};

const getVpnState = (state = {}) => getOption(state, 'vpn', 'Vpn', 'VPN') || {};

const boolLabel = (value, trueText = 'Enabled', falseText = 'Disabled') => (
  <Label color={value ? 'green' : 'grey'}>
    <Icon name={value ? 'check circle' : 'minus circle'} />
    {value ? trueText : falseText}
  </Label>
);

const valueOrDash = (value) =>
  value === undefined || value === null || value === '' ? '-' : value;

const isConfigured = (value) =>
  value !== undefined && value !== null && value !== '';

const toNumber = (value, fallback) => {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const portForwards = (vpn = {}) =>
  asArray(getOption(vpn, 'portForwards', 'PortForwards'));

const buildSourceFeedForm = (options = {}) => {
  const spotify = getSpotifyOptions(options);
  const youtube = getYouTubeOptions(options);
  const lastfm = getLastFmOptions(options);

  return {
    lastFmApiKey: '',
    lastFmConfigured: isConfigured(getOption(lastfm, 'apiKey', 'ApiKey')),
    lastFmEnabled: Boolean(getOption(lastfm, 'enabled', 'Enabled')),
    spotifyClientId: '',
    spotifyClientSecret: '',
    spotifyConfigured: isConfigured(getOption(spotify, 'clientId', 'ClientId')),
    spotifyEnabled: Boolean(getOption(spotify, 'enabled', 'Enabled')),
    spotifyMaxItems: String(
      getOption(spotify, 'maxItemsPerImport', 'MaxItemsPerImport') ?? 500,
    ),
    spotifyMarket: getOption(spotify, 'market', 'Market') || 'US',
    spotifyRedirectUri: getOption(spotify, 'redirectUri', 'RedirectUri') || '',
    spotifySecretConfigured: isConfigured(
      getOption(spotify, 'clientSecret', 'ClientSecret'),
    ),
    spotifyTimeout: String(getOption(spotify, 'timeoutSeconds', 'TimeoutSeconds') ?? 20),
    youTubeApiKey: '',
    youTubeConfigured: isConfigured(getOption(youtube, 'apiKey', 'ApiKey')),
    youTubeEnabled: Boolean(getOption(youtube, 'enabled', 'Enabled')),
  };
};

const buildNotificationForm = (options = {}) => {
  const pushbullet = getPushbulletOptions(options);
  const ntfy = getNtfyOptions(options);
  const pushover = getPushoverOptions(options);

  return {
    ntfyAccessToken: '',
    ntfyAccessTokenConfigured: isConfigured(
      getOption(ntfy, 'accessToken', 'AccessToken'),
    ),
    ntfyEnabled: Boolean(getOption(ntfy, 'enabled', 'Enabled')),
    ntfyNotifyOnPrivateMessage:
      getOption(ntfy, 'notifyOnPrivateMessage', 'NotifyOnPrivateMessage') ?? true,
    ntfyNotifyOnRoomMention:
      getOption(ntfy, 'notifyOnRoomMention', 'NotifyOnRoomMention') ?? true,
    ntfyPrefix: getOption(ntfy, 'notificationPrefix', 'NotificationPrefix') || 'slskdN',
    ntfyUrl: getOption(ntfy, 'url', 'Url') || '',
    pushbulletAccessToken: '',
    pushbulletAccessTokenConfigured: isConfigured(
      getOption(pushbullet, 'accessToken', 'AccessToken'),
    ),
    pushbulletCooldownTime: String(
      getOption(pushbullet, 'cooldownTime', 'CooldownTime') ?? 900000,
    ),
    pushbulletEnabled: Boolean(getOption(pushbullet, 'enabled', 'Enabled')),
    pushbulletNotifyOnPrivateMessage:
      getOption(
        pushbullet,
        'notifyOnPrivateMessage',
        'NotifyOnPrivateMessage',
      ) ?? true,
    pushbulletNotifyOnRoomMention:
      getOption(pushbullet, 'notifyOnRoomMention', 'NotifyOnRoomMention') ?? true,
    pushbulletPrefix:
      getOption(pushbullet, 'notificationPrefix', 'NotificationPrefix') ||
      'From slskdN:',
    pushbulletRetryAttempts: String(
      getOption(pushbullet, 'retryAttempts', 'RetryAttempts') ?? 3,
    ),
    pushoverEnabled: Boolean(getOption(pushover, 'enabled', 'Enabled')),
    pushoverNotifyOnPrivateMessage:
      getOption(
        pushover,
        'notifyOnPrivateMessage',
        'NotifyOnPrivateMessage',
      ) ?? true,
    pushoverNotifyOnRoomMention:
      getOption(pushover, 'notifyOnRoomMention', 'NotifyOnRoomMention') ?? true,
    pushoverPrefix:
      getOption(pushover, 'notificationPrefix', 'NotificationPrefix') || 'slskdN',
    pushoverToken: '',
    pushoverTokenConfigured: isConfigured(getOption(pushover, 'token', 'Token')),
    pushoverUserKey: '',
    pushoverUserKeyConfigured: isConfigured(
      getOption(pushover, 'userKey', 'UserKey'),
    ),
  };
};







const Integrations = ({ options = {}, state = {} }) => (
  <div className="integrations-admin">
    <Segment>
      <Header as="h3">
        <Icon name="plug" />
        <LocalizedText source={"Integrations"} /></Header>
      <p>
        <LocalizedText source={"Operational status and admin actions for integrations that affect connection routing, downloads, and external media managers."} /></p>
    </Segment>
    <VpnPanel
      options={options}
      state={state}
    />
    <LidarrPanel options={options} />
    <MetadataSettingsPanel options={options} />
    <MetadataProcessingPanel />
    <NotificationIntegrationsPanel options={options} />
    <SourceFeedIntegrationsPanel options={options} />
    <FtpIntegrationPanel options={options} />
    <ServarrReadinessPanel options={options} />
    <MediaServerPanel />
    <FederationDiagnosticsPanel />
  </div>
);

export default Integrations;
