import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
import './AdminPolicies.css';
import * as optionsApi from '../../../lib/options';
import {
  formatDownloadExclusions,
  getDownloadExclusions,
  setDownloadExclusionsInYaml,
} from '../../../lib/downloadFilters';
import * as YAML from 'yaml';
import DownloadExclusionsField from '../../Shared/DownloadExclusionsField';
import React, { useEffect, useState } from 'react';
import {
  Button,
  Card,
  Checkbox,
  Form,
  Header,
  Icon,
  Label,
  Message,
  Popup,
  Segment,
  Table,
} from 'semantic-ui-react';

const getOption = (source, ...keys) => {
  for (const key of keys) {
    if (source && Object.prototype.hasOwnProperty.call(source, key)) {
      return source[key];
    }
  }

  return undefined;
};

const getAuthOptions = (options = {}) =>
  getOption(getOption(options, 'web', 'Web') || {}, 'authentication', 'Authentication') ||
  {};

const getTransferOptions = (options = {}) =>
  getOption(options, 'transfers', 'Transfers', 'global', 'Global') || {};

const getUploadOptions = (options = {}) =>
  getOption(getTransferOptions(options), 'upload', 'Upload') || {};

const getDownloadOptions = (options = {}) =>
  getOption(getTransferOptions(options), 'download', 'Download') || {};

const getIntegrationOptions = (options = {}) =>
  getOption(options, 'integration', 'Integration', 'integrations', 'Integrations') ||
  {};

const getShareOptions = (options = {}) => getOption(options, 'shares', 'Shares') || {};

const isConfigured = (value) =>
  value !== undefined && value !== null && value !== '';

const toLines = (value = []) => {
  if (Array.isArray(value)) {
    return value.join('\n');
  }

  return String(value || '');
};

const parseLines = (value = '') =>
  String(value)
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);

const toNumber = (value, fallback) => {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const REQUIRED_INTEGER_FIELDS = [
  ['autoReplaceInterval', 'Auto-replace interval'],
  ['autoReplaceMaxRetries', 'Auto-replace max retries'],
  ['dhtAnnounceIntervalSeconds', 'DHT announce interval'],
  ['dhtOverlayPort', 'DHT overlay TCP port'],
  ['dhtPort', 'DHT UDP port'],
  ['downloadRetryAttempts', 'Download retry attempts'],
  ['downloadRetryDelay', 'Download retry delay'],
  ['downloadRetryMaxDelay', 'Download retry max delay'],
  ['downloadSlots', 'Download slots'],
  ['downloadSpeedLimit', 'Download speed limit'],
  ['eventsRetention', 'Event retention'],
  ['httpsPort', 'HTTPS port'],
  ['jwtTtl', 'JWT time to live'],
  ['logRetention', 'Log retention'],
  ['rateLimitApi', 'API rate limit'],
  ['rateLimitApiWindow', 'API rate-limit window'],
  ['rateLimitFederation', 'Federation rate limit'],
  ['rateLimitFederationWindow', 'Federation rate-limit window'],
  ['rateLimitMesh', 'Mesh rate limit'],
  ['rateLimitMeshWindow', 'Mesh rate-limit window'],
  ['rescueModeMaxQueueSeconds', 'Rescue queue time'],
  ['searchIncomingCircuitBreaker', 'Incoming search circuit breaker'],
  ['searchIncomingConcurrency', 'Incoming search concurrency'],
  ['searchIncomingResponseFileLimit', 'Incoming search response file limit'],
  ['searchRetentionCleanupInterval', 'Search cleanup interval'],
  ['searchRetentionMaxAgeDays', 'Search retention max age'],
  ['searchRetentionMaxCount', 'Search retention max count'],
  ['shareCacheWorkers', 'Share-cache workers'],
  ['uploadSlots', 'Upload slots'],
  ['uploadSpeedLimit', 'Upload speed limit'],
  ['webhookRetryAttempts', 'Webhook retry attempts'],
  ['webhookTimeout', 'Webhook timeout'],
];

const OPTIONAL_INTEGER_FIELDS = [
  ['retentionSearch', 'Search retention'],
  ['retentionUploadSucceeded', 'Upload succeeded retention'],
  ['retentionUploadErrored', 'Upload errored retention'],
  ['retentionUploadCancelled', 'Upload cancelled retention'],
  ['retentionDownloadSucceeded', 'Download succeeded retention'],
  ['retentionDownloadErrored', 'Download errored retention'],
  ['retentionDownloadCancelled', 'Download cancelled retention'],
  ['fileCompleteRetention', 'Complete-file retention'],
  ['fileIncompleteRetention', 'Incomplete-file retention'],
  ['shareCacheRetention', 'Share-cache retention'],
];

const isWholeNumber = (value) => /^\d+$/u.test(String(value ?? '').trim()) &&
  Number.isSafeInteger(Number(value));

const boolLabel = (value, trueText = 'Enabled', falseText = 'Disabled') => (
  <Label color={value ? 'green' : 'grey'}>
    <Icon name={value ? 'check circle' : 'minus circle'} />
    {value ? trueText : falseText}
  </Label>
);

const buildForm = (options = {}) => {
  const auth = getAuthOptions(options);
  const jwt = getOption(auth, 'jwt', 'Jwt') || {};
  const passthrough = getOption(auth, 'passthrough', 'Passthrough') || {};
  const apiKeys = getOption(auth, 'apiKeys', 'api_keys', 'ApiKeys') || {};
  const web = getOption(options, 'web', 'Web') || {};
  const https = getOption(web, 'https', 'Https', 'HTTPS') || {};
  const certificate = getOption(https, 'certificate', 'Certificate') || {};
  const rateLimiting = getOption(web, 'rateLimiting', 'rate_limiting', 'RateLimiting') || {};
  const upload = getUploadOptions(options);
  const download = getDownloadOptions(options);
  const autoReplace = getOption(options, 'autoReplace', 'auto_replace', 'AutoReplace') || {};
  const scheduledLimits =
    getOption(options, 'scheduledLimits', 'scheduled_limits', 'ScheduledLimits') || {};
  const filters = getOption(options, 'filters', 'Filters') || {};
  const searchFilters = getOption(filters, 'search', 'Search') || {};
  const blacklist = getOption(options, 'blacklist', 'Blacklist') || {};
  const throttling = getOption(options, 'throttling', 'Throttling') || {};
  const incoming =
    getOption(
      getOption(getOption(throttling, 'search', 'Search') || {}, 'incoming', 'Incoming') ||
        {},
      'incoming',
      'Incoming',
    ) || getOption(getOption(throttling, 'search', 'Search') || {}, 'incoming', 'Incoming') || {};
  const retention = getOption(options, 'retention', 'Retention') || {};
  const retentionTransfers = getOption(retention, 'transfers', 'Transfers') || {};
  const retentionUpload = getOption(retentionTransfers, 'upload', 'Upload') || {};
  const retentionDownload = getOption(retentionTransfers, 'download', 'Download') || {};
  const retentionFiles = getOption(retention, 'files', 'Files') || {};
  const sharesCache = getOption(getShareOptions(options), 'cache', 'Cache') || {};
  const webhooks = getOption(getIntegrationOptions(options), 'webhooks', 'Webhooks') || {};
  const scripts = getOption(getIntegrationOptions(options), 'scripts', 'Scripts') || {};
  const firstWebhookName = Object.keys(webhooks)[0] || '';
  const firstWebhook = webhooks[firstWebhookName] || {};
  const firstWebhookCall = getOption(firstWebhook, 'call', 'Call') || {};
  const firstWebhookRetry = getOption(firstWebhook, 'retry', 'Retry') || {};
  const firstScriptName = Object.keys(scripts)[0] || '';
  const firstScript = scripts[firstScriptName] || {};
  const firstScriptRun = getOption(firstScript, 'run', 'Run') || {};
  const firstApiKeyName = Object.keys(apiKeys)[0] || '';
  const firstApiKey = apiKeys[firstApiKeyName] || {};
  const firstApiKeyConfiguredName = isConfigured(
    getOption(firstApiKey, 'key', 'Key'),
  ) ? firstApiKeyName : '';
  const retry = getOption(download, 'retry', 'Retry') || {};
  const uploadScheduledLimits =
    getOption(upload, 'scheduledLimits', 'scheduled_limits', 'ScheduledLimits') ||
    scheduledLimits;
  const downloadScheduledLimits =
    getOption(download, 'scheduledLimits', 'scheduled_limits', 'ScheduledLimits') ||
    scheduledLimits;
  const shares = getShareOptions(options);
  const features = getOption(options, 'features', 'Features') || {};
  const dht = getOption(options, 'dht', 'dhtRendezvous', 'DhtRendezvous') || {};
  const rescueMode = getOption(options, 'rescueMode', 'rescue_mode', 'RescueMode') || {};

  return {
    allowRemoteNoAuth: Boolean(getOption(web, 'allowRemoteNoAuth', 'allow_remote_no_auth', 'AllowRemoteNoAuth')),
    apiKeyCidr: getOption(firstApiKey, 'cidr', 'Cidr') || '127.0.0.1/32,::1/128',
    apiKeyConfigured: isConfigured(getOption(firstApiKey, 'key', 'Key')),
    apiKeyConfiguredName: firstApiKeyConfiguredName,
    apiKeyName: firstApiKeyName,
    apiKeyRole: getOption(firstApiKey, 'role', 'Role') || 'ReadOnly',
    apiKeyScopes: getOption(firstApiKey, 'scopes', 'Scopes') || '*',
    apiKeyValue: '',
    autoReplaceInterval: String(
      getOption(autoReplace, 'intervalSeconds', 'interval_seconds', 'IntervalSeconds') ??
        getOption(download, 'autoReplaceInterval', 'auto_replace_interval') ??
        300,
    ),
    autoReplaceMaxRetries: String(
      getOption(autoReplace, 'maxRetries', 'max_retries', 'MaxRetries') ?? 3,
    ),
    autoReplaceStuck: Boolean(getOption(download, 'autoReplaceStuck', 'auto_replace_stuck')),
    autoReplaceThreshold: String(
      getOption(
        autoReplace,
        'sizeThresholdPercent',
        'size_threshold_percent',
        'SizeThresholdPercent',
      ) ??
        getOption(download, 'autoReplaceThreshold', 'auto_replace_threshold') ??
        0,
    ),
    blacklistEnabled: Boolean(getOption(blacklist, 'enabled', 'Enabled')),
    blacklistFile: getOption(blacklist, 'file', 'File') || '',
    downloadSlots: String(getOption(download, 'slots', 'Slots') ?? 500),
    downloadSpeedLimit: String(getOption(download, 'speedLimit', 'speed_limit', 'SpeedLimit') ?? 0),
    downloadRetryAttempts: String(getOption(retry, 'attempts', 'Attempts') ?? 1),
    downloadRetryDelay: String(getOption(retry, 'delay', 'Delay') ?? 5000),
    downloadRetryIncomplete: getOption(retry, 'incomplete', 'Incomplete') || 'resume',
    downloadRetryMaxDelay: String(getOption(retry, 'maxDelay', 'max_delay', 'MaxDelay') ?? 60000),
    downloadFilterExclude: formatDownloadExclusions(getDownloadExclusions(options)),
    downloadScheduledLimitsEnabled: Boolean(getOption(downloadScheduledLimits, 'enabled', 'Enabled')),
    dhtAnnounceIntervalSeconds: String(getOption(dht, 'announceIntervalSeconds', 'announce_interval_seconds', 'AnnounceIntervalSeconds') ?? 900),
    dhtBootstrapRouters: toLines(getOption(dht, 'bootstrapRouters', 'bootstrap_routers', 'BootstrapRouters') || []),
    dhtEnabled: getOption(dht, 'enabled', 'Enabled') ?? true,
    dhtLanOnly: Boolean(getOption(dht, 'lanOnly', 'lan_only', 'LanOnly')),
    dhtPort: String(getOption(dht, 'dhtPort', 'dht_port', 'DhtPort') ?? 50305),
    dhtOverlayPort: String(getOption(dht, 'overlayPort', 'overlay_port', 'OverlayPort') ?? 50305),
    enforceSecurity: Boolean(getOption(web, 'enforceSecurity', 'enforce_security', 'EnforceSecurity')),
    eventsRetention: String(getOption(retention, 'events', 'Events') ?? 30),
    featureScenePodBridge: Boolean(getOption(features, 'scenePodBridge', 'ScenePodBridge')),
    fileCompleteRetention: String(getOption(retentionFiles, 'complete', 'Complete') ?? ''),
    fileIncompleteRetention: String(getOption(retentionFiles, 'incomplete', 'Incomplete') ?? ''),
    forceHttps: Boolean(getOption(https, 'force', 'Force')),
    httpsCertificatePassword: '',
    httpsCertificatePasswordConfigured: isConfigured(
      getOption(certificate, 'password', 'Password'),
    ),
    httpsCertificatePfx: getOption(certificate, 'pfx', 'Pfx') || '',
    httpsDisabled: getOption(https, 'disabled', 'Disabled') ?? true,
    httpsPort: String(getOption(https, 'port', 'Port') ?? 5031),
    jwtConfigured: isConfigured(getOption(jwt, 'key', 'Key')),
    jwtKey: '',
    jwtTtl: String(getOption(jwt, 'ttl', 'Ttl') ?? 3600000),
    logRetention: String(getOption(retention, 'logs', 'Logs') ?? 14),
    noAuth: Boolean(getOption(auth, 'disabled', 'Disabled')),
    passthroughCidrs: getOption(passthrough, 'allowedCidrs', 'allowed_cidrs', 'AllowedCidrs') || '',
    rateLimitApi: String(getOption(rateLimiting, 'apiPermitLimit', 'api_permit_limit', 'ApiPermitLimit') ?? 200),
    rateLimitApiWindow: String(getOption(rateLimiting, 'apiWindowSeconds', 'api_window_seconds', 'ApiWindowSeconds') ?? 60),
    rateLimitEnabled: getOption(rateLimiting, 'enabled', 'Enabled') ?? true,
    rateLimitFederation: String(
      getOption(rateLimiting, 'federationPermitLimit', 'federation_permit_limit', 'FederationPermitLimit') ?? 30,
    ),
    rateLimitFederationWindow: String(
      getOption(rateLimiting, 'federationWindowSeconds', 'federation_window_seconds', 'FederationWindowSeconds') ?? 60,
    ),
    rateLimitMesh: String(
      getOption(rateLimiting, 'meshGatewayPermitLimit', 'mesh_gateway_permit_limit', 'MeshGatewayPermitLimit') ?? 60,
    ),
    rateLimitMeshWindow: String(
      getOption(rateLimiting, 'meshGatewayWindowSeconds', 'mesh_gateway_window_seconds', 'MeshGatewayWindowSeconds') ?? 60,
    ),
    retentionDownloadCancelled: String(getOption(retentionDownload, 'cancelled', 'Cancelled') ?? ''),
    retentionDownloadErrored: String(getOption(retentionDownload, 'errored', 'Errored') ?? ''),
    retentionDownloadSucceeded: String(getOption(retentionDownload, 'succeeded', 'Succeeded') ?? ''),
    retentionSearch: String(getOption(retention, 'search', 'Search') ?? ''),
    searchRetentionMaxAgeDays: String(getOption(filters, 'searchRetention', 'maxAgeDays', 'MaxAgeDays') ?? 30),
    searchRetentionMaxCount: String(getOption(filters, 'searchRetention', 'maxCount', 'MaxCount') ?? 1000),
    searchRetentionCleanupInterval: String(getOption(filters, 'searchRetention', 'cleanupIntervalSeconds', 'CleanupIntervalSeconds') ?? 86400),
    retentionUploadCancelled: String(getOption(retentionUpload, 'cancelled', 'Cancelled') ?? ''),
    retentionUploadErrored: String(getOption(retentionUpload, 'errored', 'Errored') ?? ''),
    retentionUploadSucceeded: String(getOption(retentionUpload, 'succeeded', 'Succeeded') ?? ''),
    rescueModeEnabled: Boolean(getOption(rescueMode, 'enabled', 'Enabled')),
    rescueModeMaxQueueSeconds: String(getOption(rescueMode, 'maxQueueTimeSeconds', 'max_queue_time_seconds', 'MaxQueueTimeSeconds') ?? 1800),
    scheduledLimitsEnabled: Boolean(getOption(scheduledLimits, 'enabled', 'Enabled')),
    scriptArgs: getOption(firstScriptRun, 'args', 'Args') || '',
    scriptCommand: getOption(firstScriptRun, 'command', 'Command') || '',
    scriptEvents: toLines(getOption(firstScript, 'on', 'On') || []),
    scriptExecutable: getOption(firstScriptRun, 'executable', 'Executable') || '',
    scriptName: firstScriptName,
    searchFilterRequest: toLines(getOption(searchFilters, 'request', 'Request') || []),
    searchIncomingCircuitBreaker: String(
      getOption(incoming, 'circuitBreaker', 'circuit_breaker', 'CircuitBreaker') ?? 500,
    ),
    searchIncomingConcurrency: String(getOption(incoming, 'concurrency', 'Concurrency') ?? 10),
    searchIncomingResponseFileLimit: String(
      getOption(incoming, 'responseFileLimit', 'response_file_limit', 'ResponseFileLimit') ?? 500,
    ),
    shareCacheRetention: String(getOption(sharesCache, 'retention', 'Retention') ?? ''),
    shareCacheWorkers: String(getOption(sharesCache, 'workers', 'Workers') ?? 4),
    shareProbeMediaAttributes: getOption(shares, 'probeMediaAttributes', 'probe_media_attributes', 'ProbeMediaAttributes') ?? true,
    uploadSlots: String(getOption(upload, 'slots', 'Slots') ?? 20),
    uploadSpeedLimit: String(getOption(upload, 'speedLimit', 'speed_limit', 'SpeedLimit') ?? 0),
    uploadScheduledLimitsEnabled: Boolean(getOption(uploadScheduledLimits, 'enabled', 'Enabled')),
    webhookEvents: toLines(getOption(firstWebhook, 'on', 'On') || []),
    webhookIgnoreCertificateErrors: Boolean(getOption(firstWebhookCall, 'ignoreCertificateErrors', 'ignore_certificate_errors', 'IgnoreCertificateErrors')),
    webhookName: firstWebhookName,
    webhookRetryAttempts: String(
      getOption(firstWebhookRetry, 'attempts', 'Attempts') ?? 1,
    ),
    webhookTimeout: String(getOption(firstWebhook, 'timeout', 'Timeout') ?? 5000),
    webhookUrl: getOption(firstWebhookCall, 'url', 'Url') || '',
  };
};

const setOptionalNumber = (document, path, value) => {
  const trimmed = String(value ?? '').trim();
  document.setIn(path, trimmed ? toNumber(trimmed, null) : null);
};

const AdminPolicies = ({ options = {} }) => {
  useInterfaceLanguage();
  const remoteConfiguration = Boolean(
    getOption(options, 'remoteConfiguration', 'RemoteConfiguration'),
  );
  const [form, setForm] = useState(() => buildForm(options));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    setForm(buildForm(options));
  }, [options]);

  const update = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const apiKeyDraftStarted = !form.apiKeyConfiguredName && (
    form.apiKeyName.trim() ||
    form.apiKeyValue.trim() ||
    form.apiKeyRole !== 'ReadOnly' ||
    form.apiKeyCidr !== '127.0.0.1/32,::1/128' ||
    form.apiKeyScopes !== '*'
  );
  const invalidRequiredNumbers = REQUIRED_INTEGER_FIELDS
    .filter(([field]) => !isWholeNumber(form[field]))
    .map(([, label]) => `${label} must be a whole number.`);
  const invalidOptionalNumbers = OPTIONAL_INTEGER_FIELDS
    .filter(([field]) => {
      const value = String(form[field] ?? '').trim();
      return value && !isWholeNumber(value);
    })
    .map(([, label]) => `${label} must be a whole number or blank.`);
  const invalidAutoReplaceThreshold = String(form.autoReplaceThreshold).trim() === '' ||
    !Number.isFinite(Number(form.autoReplaceThreshold));

  const missing = [
    form.webhookUrl.trim() &&
      !form.webhookName.trim() &&
      'Webhook settings need a stable name.',
    form.webhookName.trim() &&
      !form.webhookUrl.trim() &&
      'Webhook settings need a target URL.',
    form.scriptCommand.trim() &&
      !form.scriptName.trim() &&
      'Script settings need a stable name.',
    form.scriptExecutable.trim() &&
      !form.scriptName.trim() &&
      'Script settings need a stable name.',
    form.scriptName.trim() &&
      !form.scriptCommand.trim() &&
      !form.scriptExecutable.trim() &&
      'Script settings need either a command or an executable.',
    form.scriptCommand.trim() &&
      form.scriptExecutable.trim() &&
      'Script settings must use either a command or an executable, not both.',
    form.noAuth &&
      form.allowRemoteNoAuth &&
      !form.passthroughCidrs.trim() &&
      'Remote no-auth mode needs an explicit CIDR allowlist.',
    form.blacklistEnabled &&
      !form.blacklistFile.trim() &&
      'Managed blacklist needs a file path.',
    form.apiKeyConfiguredName &&
      !form.apiKeyName.trim() &&
      'Keep a name for the configured API key; this form does not remove keys.',
    form.apiKeyConfiguredName &&
      form.apiKeyName.trim() !== form.apiKeyConfiguredName &&
      !form.apiKeyValue.trim() &&
      'Enter a key value before adding API key settings under a different name.',
    apiKeyDraftStarted &&
      (!form.apiKeyName.trim() || !form.apiKeyValue.trim()) &&
      'A new API key needs a name and value before its policy can be saved.',
    ...invalidRequiredNumbers,
    ...invalidOptionalNumbers,
    invalidAutoReplaceThreshold &&
      'Auto-replace size threshold must be a number.',
  ].filter(Boolean);

  const reset = () => {
    setForm(buildForm(options));
    setMessage(null);
  };

  const saveYaml = async () => {
    setSaving(true);
    setMessage(null);

    try {
      const yaml = await optionsApi.getYaml();
      const document = YAML.parseDocument(yaml || '{}');

      if (form.webhookName.trim()) {
        const base = ['integrations', 'webhooks', form.webhookName.trim()];
        document.setIn([...base, 'on'], parseLines(form.webhookEvents));
        document.setIn([...base, 'call', 'url'], form.webhookUrl.trim());
        document.setIn(
          [...base, 'call', 'ignore_certificate_errors'],
          form.webhookIgnoreCertificateErrors,
        );
        document.setIn([...base, 'timeout'], toNumber(form.webhookTimeout, 5000));
        document.setIn([...base, 'retry', 'attempts'], toNumber(form.webhookRetryAttempts, 1));
      }

      if (form.scriptName.trim()) {
        const base = ['integrations', 'scripts', form.scriptName.trim()];
        document.setIn([...base, 'on'], parseLines(form.scriptEvents));
        document.setIn([...base, 'run', 'command'], form.scriptCommand.trim());
        document.setIn([...base, 'run', 'executable'], form.scriptExecutable.trim());
        document.setIn([...base, 'run', 'args'], form.scriptArgs.trim());
      }

      document.setIn(['transfers', 'upload', 'slots'], toNumber(form.uploadSlots, 20));
      document.setIn(
        ['transfers', 'upload', 'speed_limit'],
        toNumber(form.uploadSpeedLimit, 0),
      );
      document.setIn(['transfers', 'download', 'slots'], toNumber(form.downloadSlots, 500));
      document.setIn(
        ['transfers', 'download', 'speed_limit'],
        toNumber(form.downloadSpeedLimit, 0),
      );
      document.setIn(
        ['transfers', 'download', 'retry', 'incomplete'],
        form.downloadRetryIncomplete,
      );
      document.setIn(
        ['transfers', 'download', 'retry', 'attempts'],
        toNumber(form.downloadRetryAttempts, 1),
      );
      document.setIn(
        ['transfers', 'download', 'retry', 'delay'],
        toNumber(form.downloadRetryDelay, 5000),
      );
      document.setIn(
        ['transfers', 'download', 'retry', 'max_delay'],
        toNumber(form.downloadRetryMaxDelay, 60000),
      );
      document.setIn(['transfers', 'download', 'auto_replace_stuck'], form.autoReplaceStuck);
      document.setIn(['auto_replace', 'interval_seconds'], toNumber(form.autoReplaceInterval, 300));
      document.setIn(
        ['auto_replace', 'size_threshold_percent'],
        Number.parseFloat(form.autoReplaceThreshold) || 0,
      );
      document.setIn(['auto_replace', 'max_retries'], toNumber(form.autoReplaceMaxRetries, 3));
      document.setIn(
        ['transfers', 'upload', 'scheduled_limits', 'enabled'],
        form.uploadScheduledLimitsEnabled,
      );
      document.setIn(
        ['transfers', 'download', 'scheduled_limits', 'enabled'],
        form.downloadScheduledLimitsEnabled,
      );

      document.setIn(['web', 'enforce_security'], form.enforceSecurity);
      document.setIn(['web', 'allow_remote_no_auth'], form.allowRemoteNoAuth);
      document.setIn(['web', 'authentication', 'disabled'], form.noAuth);
      document.setIn(['web', 'authentication', 'jwt', 'ttl'], toNumber(form.jwtTtl, 3600000));
      if (form.jwtKey.trim()) {
        document.setIn(['web', 'authentication', 'jwt', 'key'], form.jwtKey.trim());
      }
      if (form.apiKeyName.trim()) {
        const base = ['web', 'authentication', 'api_keys', form.apiKeyName.trim()];
        const existingKey = document.getIn([...base, 'key']);
        if (form.apiKeyValue.trim() || (typeof existingKey === 'string' && existingKey.trim())) {
          if (form.apiKeyValue.trim()) {
            document.setIn([...base, 'key'], form.apiKeyValue.trim());
          }
          document.setIn([...base, 'role'], form.apiKeyRole);
          document.setIn([...base, 'cidr'], form.apiKeyCidr.trim());
          document.setIn([...base, 'scopes'], form.apiKeyScopes.trim() || '*');
        }
      }
      document.setIn(
        ['web', 'authentication', 'passthrough', 'allowed_cidrs'],
        form.passthroughCidrs.trim(),
      );
      document.setIn(['web', 'https', 'disabled'], form.httpsDisabled);
      document.setIn(['web', 'https', 'port'], toNumber(form.httpsPort, 5031));
      document.setIn(['web', 'https', 'force'], form.forceHttps);
      document.setIn(['web', 'https', 'certificate', 'pfx'], form.httpsCertificatePfx.trim());
      if (form.httpsCertificatePassword.trim()) {
        document.setIn(
          ['web', 'https', 'certificate', 'password'],
          form.httpsCertificatePassword.trim(),
        );
      }
      document.setIn(['web', 'rate_limiting', 'enabled'], form.rateLimitEnabled);
      document.setIn(['web', 'rate_limiting', 'api_permit_limit'], toNumber(form.rateLimitApi, 200));
      document.setIn(
        ['web', 'rate_limiting', 'api_window_seconds'],
        toNumber(form.rateLimitApiWindow, 60),
      );
      document.setIn(
        ['web', 'rate_limiting', 'federation_permit_limit'],
        toNumber(form.rateLimitFederation, 30),
      );
      document.setIn(
        ['web', 'rate_limiting', 'federation_window_seconds'],
        toNumber(form.rateLimitFederationWindow, 60),
      );
      document.setIn(
        ['web', 'rate_limiting', 'mesh_gateway_permit_limit'],
        toNumber(form.rateLimitMesh, 60),
      );
      document.setIn(
        ['web', 'rate_limiting', 'mesh_gateway_window_seconds'],
        toNumber(form.rateLimitMeshWindow, 60),
      );

      document.setIn(['filters', 'search', 'request'], parseLines(form.searchFilterRequest));
      setDownloadExclusionsInYaml(document, form.downloadFilterExclude);
      document.setIn(['filters', 'search_retention', 'max_age_days'], toNumber(form.searchRetentionMaxAgeDays, 30));
      document.setIn(['filters', 'search_retention', 'max_count'], toNumber(form.searchRetentionMaxCount, 1000));
      document.setIn(['filters', 'search_retention', 'cleanup_interval_seconds'], toNumber(form.searchRetentionCleanupInterval, 86400));
      document.setIn(['blacklist', 'enabled'], form.blacklistEnabled);
      document.setIn(['blacklist', 'file'], form.blacklistFile.trim());
      document.setIn(['dht', 'enabled'], form.dhtEnabled);
      document.setIn(['dht', 'lan_only'], form.dhtLanOnly);
      document.setIn(['dht', 'overlay_port'], toNumber(form.dhtOverlayPort, 50305));
      document.setIn(['dht', 'dht_port'], toNumber(form.dhtPort, 50305));
      document.setIn(['dht', 'bootstrap_routers'], parseLines(form.dhtBootstrapRouters));
      document.setIn(
        ['dht', 'announce_interval_seconds'],
        toNumber(form.dhtAnnounceIntervalSeconds, 900),
      );
      document.setIn(['feature', 'scene_pod_bridge'], form.featureScenePodBridge);
      document.setIn(['rescue_mode', 'enabled'], form.rescueModeEnabled);
      document.setIn(
        ['rescue_mode', 'max_queue_time_seconds'],
        toNumber(form.rescueModeMaxQueueSeconds, 1800),
      );
      document.setIn(
        ['throttling', 'search', 'incoming', 'concurrency'],
        toNumber(form.searchIncomingConcurrency, 10),
      );
      document.setIn(
        ['throttling', 'search', 'incoming', 'circuit_breaker'],
        toNumber(form.searchIncomingCircuitBreaker, 500),
      );
      document.setIn(
        ['throttling', 'search', 'incoming', 'response_file_limit'],
        toNumber(form.searchIncomingResponseFileLimit, 500),
      );

      setOptionalNumber(document, ['retention', 'search'], form.retentionSearch);
      document.setIn(['retention', 'events'], toNumber(form.eventsRetention, 30));
      document.setIn(['retention', 'logs'], toNumber(form.logRetention, 14));
      setOptionalNumber(
        document,
        ['retention', 'transfers', 'upload', 'succeeded'],
        form.retentionUploadSucceeded,
      );
      setOptionalNumber(
        document,
        ['retention', 'transfers', 'upload', 'errored'],
        form.retentionUploadErrored,
      );
      setOptionalNumber(
        document,
        ['retention', 'transfers', 'upload', 'cancelled'],
        form.retentionUploadCancelled,
      );
      setOptionalNumber(
        document,
        ['retention', 'transfers', 'download', 'succeeded'],
        form.retentionDownloadSucceeded,
      );
      setOptionalNumber(
        document,
        ['retention', 'transfers', 'download', 'errored'],
        form.retentionDownloadErrored,
      );
      setOptionalNumber(
        document,
        ['retention', 'transfers', 'download', 'cancelled'],
        form.retentionDownloadCancelled,
      );
      setOptionalNumber(document, ['retention', 'files', 'complete'], form.fileCompleteRetention);
      setOptionalNumber(document, ['retention', 'files', 'incomplete'], form.fileIncompleteRetention);
      document.setIn(['shares', 'probe_media_attributes'], form.shareProbeMediaAttributes);
      document.setIn(['shares', 'cache', 'workers'], toNumber(form.shareCacheWorkers, 4));
      setOptionalNumber(document, ['shares', 'cache', 'retention'], form.shareCacheRetention);

      await optionsApi.updateYaml({ yaml: document.toString() });
      setForm((current) => ({
        ...current,
        apiKeyConfigured: current.apiKeyConfigured || Boolean(current.apiKeyValue.trim()),
        apiKeyConfiguredName: current.apiKeyValue.trim()
          ? current.apiKeyName.trim()
          : current.apiKeyConfiguredName,
        apiKeyValue: '',
        httpsCertificatePassword: '',
        httpsCertificatePasswordConfigured:
          current.httpsCertificatePasswordConfigured ||
          Boolean(current.httpsCertificatePassword.trim()),
        jwtConfigured: current.jwtConfigured || Boolean(current.jwtKey.trim()),
        jwtKey: '',
      }));
      setMessage({
        positive: true,
        text: interfaceText("Policy settings saved to YAML. Restart-signalled options still require a daemon restart."),
      });
    } catch (error) {
      setMessage({
        negative: true,
        text: getApiErrorMessage(error, { t: interfaceText }),
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="admin-policies">
      <Segment>
        <Header as="h3">
          <Icon name="sliders horizontal" />
          <LocalizedText source={"Policies"} /></Header>
        <p>
          <LocalizedText source={"Guided YAML controls for operator policies that are otherwise easy to miss in raw configuration."} /></p>
      </Segment>

      {!remoteConfiguration && (
        <Message
          info
          size="small"
        >
          <LocalizedText source={"Remote configuration is disabled. These controls show the settings shape, but YAML saving is disabled until remote configuration is enabled."} /></Message>
      )}

      {message && (
        <Message
          negative={message.negative}
          positive={message.positive}
          size="small"
        >
          {message.text}
        </Message>
      )}
      {missing.length > 0 && (
        <Message
          size="small"
          warning
        >
          <Message.List items={missing} />
        </Message>
      )}

      <Card.Group
        itemsPerRow={1}
        stackable
      >
        <Card fluid>
          <Card.Content>
            <Card.Header>
              <Icon name="bolt" />
              <LocalizedText source={"Actions: Webhooks and Scripts"} /></Card.Header>
            <Card.Meta><LocalizedText source={"Event hooks, remote targets, command hooks, and retry shape."} /></Card.Meta>
          </Card.Content>
          <Card.Content>
            <Form>
              <Form.Group grouped>
                <Popup
                  className="admin-policy-popup"
                  content={interfaceText("Probe shared audio files for bitrate, duration, and sample metadata during share scans. Disable on slow or remote storage.")}
                  trigger={
                    <Checkbox
                      aria-label={interfaceText("Probe share media attributes")}
                      checked={form.shareProbeMediaAttributes}
                      disabled={!remoteConfiguration || saving}
                      label={interfaceText("Probe share media attributes")}
                      onChange={(_, { checked }) =>
                        update('shareProbeMediaAttributes', Boolean(checked))
                      }
                      toggle
                     {...interfaceTextProps("Probe share media attributes")}/>
                  }
                 {...interfaceTextProps("Probe shared audio files for bitrate, duration, and sample metadata during share scans. Disable on slow or remote storage.")}/>
              </Form.Group>
              <Form.Group widths="equal">
                <Form.Input
                  aria-label={interfaceText("Webhook policy name")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Webhook Name")}
                  onChange={(_, { value }) => update('webhookName', value)}
                  value={form.webhookName}
                 {...interfaceTextProps("Webhook policy name")}/>
                <Form.Input
                  aria-label={interfaceText("Webhook target URL")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Webhook URL")}
                  onChange={(_, { value }) => update('webhookUrl', value)}
                  placeholder="https://example.invalid/slskdn-hook"
                  value={form.webhookUrl}
                 {...interfaceTextProps("Webhook target URL")}/>
                <Form.Input
                  aria-label={interfaceText("Webhook retry attempts")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Retry Attempts")}
                  min={1}
                  onChange={(_, { value }) => update('webhookRetryAttempts', value)}
                  type="number"
                  value={form.webhookRetryAttempts}
                 {...interfaceTextProps("Webhook retry attempts")}/>
                <Form.Input
                  aria-label={interfaceText("Webhook timeout milliseconds")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Timeout ms")}
                  min={1000}
                  onChange={(_, { value }) => update('webhookTimeout', value)}
                  type="number"
                  value={form.webhookTimeout}
                 {...interfaceTextProps("Webhook timeout milliseconds")}/>
              </Form.Group>
              <Form.TextArea
                aria-label={interfaceText("Webhook event names")}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("Webhook Events")}
                onChange={(_, { value }) => update('webhookEvents', value)}
                placeholder={interfaceText("PrivateMessageReceived&#10;DownloadFileComplete")}
                value={form.webhookEvents}
               {...interfaceTextProps("Webhook event names")}/>
              <Popup
                className="admin-policy-popup"
                content={interfaceText("Allow this webhook to call a target with a self-signed or otherwise untrusted certificate.")}
                trigger={
                  <Checkbox
                    aria-label={interfaceText("Ignore webhook certificate errors")}
                    checked={form.webhookIgnoreCertificateErrors}
                    disabled={!remoteConfiguration || saving}
                    label={interfaceText("Ignore webhook certificate errors")}
                    onChange={(_, { checked }) =>
                      update('webhookIgnoreCertificateErrors', Boolean(checked))
                    }
                    toggle
                   {...interfaceTextProps("Ignore webhook certificate errors")}/>
                }
               {...interfaceTextProps("Allow this webhook to call a target with a self-signed or otherwise untrusted certificate.")}/>
              <Form.Group widths="equal">
                <Form.Input
                  aria-label={interfaceText("Script policy name")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Script Name")}
                  onChange={(_, { value }) => update('scriptName', value)}
                  value={form.scriptName}
                 {...interfaceTextProps("Script policy name")}/>
                <Form.Input
                  aria-label={interfaceText("Script command")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Script Command")}
                  onChange={(_, { value }) => update('scriptCommand', value)}
                  placeholder="/usr/local/bin/slskdn-hook"
                  value={form.scriptCommand}
                 {...interfaceTextProps("Script command")}/>
              </Form.Group>
              <Form.Group widths="equal">
                <Form.Input
                  aria-label={interfaceText("Script executable")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Script Executable")}
                  onChange={(_, { value }) => update('scriptExecutable', value)}
                  placeholder="/bin/sh"
                  value={form.scriptExecutable}
                 {...interfaceTextProps("Script executable")}/>
                <Form.Input
                  aria-label={interfaceText("Script arguments")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Script Args")}
                  onChange={(_, { value }) => update('scriptArgs', value)}
                  placeholder="-c ./hook.sh"
                  value={form.scriptArgs}
                 {...interfaceTextProps("Script arguments")}/>
              </Form.Group>
              <Form.TextArea
                aria-label={interfaceText("Script event names")}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("Script Events")}
                onChange={(_, { value }) => update('scriptEvents', value)}
                placeholder={interfaceText("DownloadFileComplete")}
                value={form.scriptEvents}
               {...interfaceTextProps("Script event names")}/>
            </Form>
          </Card.Content>
        </Card>

        <Card fluid>
          <Card.Content>
            <Card.Header>
              <Icon name="exchange" />
              <LocalizedText source={"Transfer Policy"} /></Card.Header>
            <Card.Meta><LocalizedText source={"Slots, speed ceilings, auto-replace, and schedule enablement."} /></Card.Meta>
          </Card.Content>
          <Card.Content>
            <div className="integration-status-row">
              {boolLabel(form.scheduledLimitsEnabled, 'Schedules On', 'Schedules Off')}
              {boolLabel(form.autoReplaceStuck, 'Auto-Replace On', 'Auto-Replace Off')}
            </div>
            <Segment
              className="download-policy-panel"
              secondary
            >
              <Header as="h4">
                <Icon name="ban" />
                <LocalizedText source={"Global download exclusions"} /></Header>
              <p>
                <LocalizedText source={"Advanced operator view of the same global filter available from the Downloads view. Use it when managing YAML policy alongside the rest of the daemon configuration."} /></p>
              <DownloadExclusionsField
                disabled={!remoteConfiguration || saving}
                onChange={(value) => update('downloadFilterExclude', value)}
                value={form.downloadFilterExclude}
              />
            </Segment>
            <Form>
              <Form.Group widths="equal">
                <Form.Input
                  aria-label={interfaceText("Global upload slots")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Upload Slots")}
                  onChange={(_, { value }) => update('uploadSlots', value)}
                  type="number"
                  value={form.uploadSlots}
                 {...interfaceTextProps("Global upload slots")}/>
                <Form.Input
                  aria-label={interfaceText("Global upload speed limit")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Upload KiB/s")}
                  onChange={(_, { value }) => update('uploadSpeedLimit', value)}
                  type="number"
                  value={form.uploadSpeedLimit}
                 {...interfaceTextProps("Global upload speed limit")}/>
                <Form.Input
                  aria-label={interfaceText("Global download slots")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Download Slots")}
                  onChange={(_, { value }) => update('downloadSlots', value)}
                  type="number"
                  value={form.downloadSlots}
                 {...interfaceTextProps("Global download slots")}/>
                <Form.Input
                  aria-label={interfaceText("Global download speed limit")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Download KiB/s")}
                  onChange={(_, { value }) => update('downloadSpeedLimit', value)}
                  type="number"
                  value={form.downloadSpeedLimit}
                 {...interfaceTextProps("Global download speed limit")}/>
              </Form.Group>
              <Form.Group widths="equal">
                <Form.Select
                  aria-label={interfaceText("Download retry incomplete strategy")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Retry Partial Files")}
                  onChange={(_, { value }) => update('downloadRetryIncomplete', value)}
                  options={[
                    { key: 'resume', text: interfaceText("resume"), value: 'resume' },
                    { key: 'overwrite', text: interfaceText("overwrite"), value: 'overwrite' },
                  ]}
                  value={form.downloadRetryIncomplete}
                 {...interfaceTextProps("Download retry incomplete strategy")}/>
                <Form.Input
                  aria-label={interfaceText("Download retry attempts")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Retry Attempts")}
                  min={1}
                  onChange={(_, { value }) => update('downloadRetryAttempts', value)}
                  type="number"
                  value={form.downloadRetryAttempts}
                 {...interfaceTextProps("Download retry attempts")}/>
                <Form.Input
                  aria-label={interfaceText("Download retry delay milliseconds")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Retry Delay ms")}
                  min={0}
                  onChange={(_, { value }) => update('downloadRetryDelay', value)}
                  type="number"
                  value={form.downloadRetryDelay}
                 {...interfaceTextProps("Download retry delay milliseconds")}/>
                <Form.Input
                  aria-label={interfaceText("Download retry max delay milliseconds")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Retry Max Delay ms")}
                  min={1000}
                  onChange={(_, { value }) => update('downloadRetryMaxDelay', value)}
                  type="number"
                  value={form.downloadRetryMaxDelay}
                 {...interfaceTextProps("Download retry max delay milliseconds")}/>
              </Form.Group>
              <Form.Group widths="equal">
                <Form.Input
                  aria-label={interfaceText("Auto replace interval seconds")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Auto-Replace Interval")}
                  min={60}
                  onChange={(_, { value }) => update('autoReplaceInterval', value)}
                  type="number"
                  value={form.autoReplaceInterval}
                 {...interfaceTextProps("Auto replace interval seconds")}/>
                <Form.Input
                  aria-label={interfaceText("Auto replace size threshold")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Size Threshold %")}
                  min={0}
                  onChange={(_, { value }) => update('autoReplaceThreshold', value)}
                  type="number"
                  value={form.autoReplaceThreshold}
                 {...interfaceTextProps("Auto replace size threshold")}/>
                <Form.Input
                  aria-label={interfaceText("Auto replace max retries")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Max Retries")}
                  min={0}
                  onChange={(_, { value }) => update('autoReplaceMaxRetries', value)}
                  type="number"
                  value={form.autoReplaceMaxRetries}
                 {...interfaceTextProps("Auto replace max retries")}/>
              </Form.Group>
              <Form.Group grouped>
                <Popup
                  className="admin-policy-popup"
                  content={interfaceText("Enable automatic replacement of stuck downloads with alternative sources.")}
                  trigger={
                    <Checkbox
                      aria-label={interfaceText("Enable auto replace stuck downloads")}
                      checked={form.autoReplaceStuck}
                      disabled={!remoteConfiguration || saving}
                      label={interfaceText("Enable auto-replace stuck downloads")}
                      onChange={(_, { checked }) =>
                        update('autoReplaceStuck', Boolean(checked))
                      }
                      toggle
                     {...interfaceTextProps("Enable auto replace stuck downloads")}/>
                  }
                 {...interfaceTextProps("Enable automatic replacement of stuck downloads with alternative sources.")}/>
                <Popup
                  className="admin-policy-popup"
                  content={interfaceText("Enable the legacy top-level scheduled speed-limit policy in YAML.")}
                  trigger={
                    <Checkbox
                      aria-label={interfaceText("Enable scheduled speed limits")}
                      checked={form.scheduledLimitsEnabled}
                      disabled={!remoteConfiguration || saving}
                      label={interfaceText("Enable scheduled speed limits")}
                      onChange={(_, { checked }) =>
                        update('scheduledLimitsEnabled', Boolean(checked))
                      }
                      toggle
                     {...interfaceTextProps("Enable scheduled speed limits")}/>
                  }
                 {...interfaceTextProps("Enable the legacy top-level scheduled speed-limit policy in YAML.")}/>
                <Popup
                  className="admin-policy-popup"
                  content={interfaceText("Enable scheduled upload speed limits under global upload policy.")}
                  trigger={
                    <Checkbox
                      aria-label={interfaceText("Enable upload scheduled speed limits")}
                      checked={form.uploadScheduledLimitsEnabled}
                      disabled={!remoteConfiguration || saving}
                      label={interfaceText("Enable upload schedules")}
                      onChange={(_, { checked }) =>
                        update('uploadScheduledLimitsEnabled', Boolean(checked))
                      }
                      toggle
                     {...interfaceTextProps("Enable upload scheduled speed limits")}/>
                  }
                 {...interfaceTextProps("Enable scheduled upload speed limits under global upload policy.")}/>
                <Popup
                  className="admin-policy-popup"
                  content={interfaceText("Enable scheduled download speed limits under global download policy.")}
                  trigger={
                    <Checkbox
                      aria-label={interfaceText("Enable download scheduled speed limits")}
                      checked={form.downloadScheduledLimitsEnabled}
                      disabled={!remoteConfiguration || saving}
                      label={interfaceText("Enable download schedules")}
                      onChange={(_, { checked }) =>
                        update('downloadScheduledLimitsEnabled', Boolean(checked))
                      }
                      toggle
                     {...interfaceTextProps("Enable download scheduled speed limits")}/>
                  }
                 {...interfaceTextProps("Enable scheduled download speed limits under global download policy.")}/>
              </Form.Group>
            </Form>
          </Card.Content>
        </Card>

        <Card fluid>
          <Card.Content>
            <Card.Header>
              <Icon name="lock" />
              <LocalizedText source={"Security and Access"} /></Card.Header>
            <Card.Meta><LocalizedText source={"Authentication, API keys, HTTPS, CORS-adjacent rate limits, and restart cues."} /></Card.Meta>
          </Card.Content>
          <Card.Content>
            <div className="integration-status-row">
              {boolLabel(!form.noAuth, 'Auth On', 'No Auth')}
              {boolLabel(form.jwtConfigured, 'JWT Key Set', 'JWT Key Missing')}
              {boolLabel(form.apiKeyConfigured, 'API Key Set', 'API Key Missing')}
              {boolLabel(!form.httpsDisabled, 'HTTPS On', 'HTTPS Off')}
              {boolLabel(
                form.httpsCertificatePasswordConfigured,
                'Certificate Password Set',
                'Certificate Password Missing',
              )}
            </div>
            <Form>
              <Form.Group grouped>
                <Popup
                  className="admin-policy-popup"
                  content={interfaceText("Enable strict startup and request hardening checks for exposed deployments.")}
                  trigger={
                    <Checkbox
                      aria-label={interfaceText("Enforce web security hardening")}
                      checked={form.enforceSecurity}
                      disabled={!remoteConfiguration || saving}
                      label={interfaceText("Enforce security hardening")}
                      onChange={(_, { checked }) =>
                        update('enforceSecurity', Boolean(checked))
                      }
                      toggle
                     {...interfaceTextProps("Enforce web security hardening")}/>
                  }
                 {...interfaceTextProps("Enable strict startup and request hardening checks for exposed deployments.")}/>
                <Popup
                  className="admin-policy-popup"
                  content={interfaceText("Disable Web UI authentication only for tightly controlled loopback deployments.")}
                  trigger={
                    <Checkbox
                      aria-label={interfaceText("Disable web authentication")}
                      checked={form.noAuth}
                      disabled={!remoteConfiguration || saving}
                      label={interfaceText("Disable authentication")}
                      onChange={(_, { checked }) => update('noAuth', Boolean(checked))}
                      toggle
                     {...interfaceTextProps("Disable web authentication")}/>
                  }
                 {...interfaceTextProps("Disable Web UI authentication only for tightly controlled loopback deployments.")}/>
                <Popup
                  className="admin-policy-popup"
                  content={interfaceText("Allow no-auth access from explicitly configured non-loopback CIDRs.")}
                  trigger={
                    <Checkbox
                      aria-label={interfaceText("Allow remote no-auth CIDRs")}
                      checked={form.allowRemoteNoAuth}
                      disabled={!remoteConfiguration || saving}
                      label={interfaceText("Allow remote no-auth CIDRs")}
                      onChange={(_, { checked }) =>
                        update('allowRemoteNoAuth', Boolean(checked))
                      }
                      toggle
                     {...interfaceTextProps("Allow remote no-auth CIDRs")}/>
                  }
                 {...interfaceTextProps("Allow no-auth access from explicitly configured non-loopback CIDRs.")}/>
                <Popup
                  className="admin-policy-popup"
                  content={interfaceText("Enable HTTP rate limiting for API, federation, and mesh gateway policies.")}
                  trigger={
                    <Checkbox
                      aria-label={interfaceText("Enable HTTP rate limiting")}
                      checked={form.rateLimitEnabled}
                      disabled={!remoteConfiguration || saving}
                      label={interfaceText("Enable HTTP rate limiting")}
                      onChange={(_, { checked }) =>
                        update('rateLimitEnabled', Boolean(checked))
                      }
                      toggle
                     {...interfaceTextProps("Enable HTTP rate limiting")}/>
                  }
                 {...interfaceTextProps("Enable HTTP rate limiting for API, federation, and mesh gateway policies.")}/>
              </Form.Group>
              <Form.Group widths="equal">
                <Form.Input
                  aria-label={interfaceText("JWT replacement key")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("JWT Key")}
                  onChange={(_, { value }) => update('jwtKey', value)}
                  placeholder={interfaceText(form.jwtConfigured ? 'Configured' : 'New JWT key')}
                  type="password"
                  value={form.jwtKey}
                 {...interfaceTextProps("JWT replacement key")}/>
                <Form.Input
                  aria-label={interfaceText("JWT TTL milliseconds")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("JWT TTL ms")}
                  min={3600}
                  onChange={(_, { value }) => update('jwtTtl', value)}
                  type="number"
                  value={form.jwtTtl}
                 {...interfaceTextProps("JWT TTL milliseconds")}/>
                <Form.Input
                  aria-label={interfaceText("No auth allowed CIDRs")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("No-Auth CIDRs")}
                  onChange={(_, { value }) => update('passthroughCidrs', value)}
                  value={form.passthroughCidrs}
                 {...interfaceTextProps("No auth allowed CIDRs")}/>
              </Form.Group>
              <Form.Group widths="equal">
                <Form.Input
                  aria-label={interfaceText("API key policy name")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("API Key Name")}
                  onChange={(_, { value }) => update('apiKeyName', value)}
                  value={form.apiKeyName}
                 {...interfaceTextProps("API key policy name")}/>
                <Form.Input
                  aria-label={interfaceText("API key replacement value")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("API Key")}
                  onChange={(_, { value }) => update('apiKeyValue', value)}
                  placeholder={interfaceText(form.apiKeyConfigured ? 'Configured' : 'New API key')}
                  type="password"
                  value={form.apiKeyValue}
                 {...interfaceTextProps("API key replacement value")}/>
                <Form.Select
                  aria-label={interfaceText("API key role")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Role")}
                  onChange={(_, { value }) => update('apiKeyRole', value)}
                  options={[
                    { key: 'ReadOnly', text: interfaceText("ReadOnly"), value: 'ReadOnly' },
                    { key: 'ReadWrite', text: interfaceText("ReadWrite"), value: 'ReadWrite' },
                    {
                      key: 'Administrator',
                      text: interfaceText("Administrator"),
                      value: 'Administrator',
                    },
                  ]}
                  value={form.apiKeyRole}
                 {...interfaceTextProps("API key role")}/>
              </Form.Group>
              <Form.Group widths="equal">
                <Form.Input
                  aria-label={interfaceText("API key CIDR allowlist")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("API CIDRs")}
                  onChange={(_, { value }) => update('apiKeyCidr', value)}
                  value={form.apiKeyCidr}
                 {...interfaceTextProps("API key CIDR allowlist")}/>
                <Form.Input
                  aria-label={interfaceText("API key scopes")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("API Scopes")}
                  onChange={(_, { value }) => update('apiKeyScopes', value)}
                  value={form.apiKeyScopes}
                 {...interfaceTextProps("API key scopes")}/>
              </Form.Group>
              <Form.Group grouped>
                <Popup
                  className="admin-policy-popup"
                  content={interfaceText("Disable HTTPS listener. Keep this off when exposing the Web UI beyond localhost.")}
                  trigger={
                    <Checkbox
                      aria-label={interfaceText("Disable HTTPS listener")}
                      checked={form.httpsDisabled}
                      disabled={!remoteConfiguration || saving}
                      label={interfaceText("Disable HTTPS")}
                      onChange={(_, { checked }) =>
                        update('httpsDisabled', Boolean(checked))
                      }
                      toggle
                     {...interfaceTextProps("Disable HTTPS listener")}/>
                  }
                 {...interfaceTextProps("Disable HTTPS listener. Keep this off when exposing the Web UI beyond localhost.")}/>
                <Popup
                  className="admin-policy-popup"
                  content={interfaceText("Redirect HTTP requests to HTTPS after certificate settings are valid.")}
                  trigger={
                    <Checkbox
                      aria-label={interfaceText("Force HTTPS redirects")}
                      checked={form.forceHttps}
                      disabled={!remoteConfiguration || saving}
                      label={interfaceText("Force HTTPS")}
                      onChange={(_, { checked }) =>
                        update('forceHttps', Boolean(checked))
                      }
                     {...interfaceTextProps("Force HTTPS redirects")}/>
                  }
                 {...interfaceTextProps("Redirect HTTP requests to HTTPS after certificate settings are valid.")}/>
              </Form.Group>
              <Form.Group widths="equal">
                <Form.Input
                  aria-label={interfaceText("HTTPS port")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("HTTPS Port")}
                  onChange={(_, { value }) => update('httpsPort', value)}
                  type="number"
                  value={form.httpsPort}
                 {...interfaceTextProps("HTTPS port")}/>
                <Form.Input
                  aria-label={interfaceText("HTTPS certificate PFX path")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Certificate PFX (optional)")}
                  onChange={(_, { value }) => update('httpsCertificatePfx', value)}
                  value={form.httpsCertificatePfx}
                 {...interfaceTextProps("HTTPS certificate PFX path")}/>
                <Form.Input
                  aria-label={interfaceText("HTTPS certificate password")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Certificate Password")}
                  onChange={(_, { value }) =>
                    update('httpsCertificatePassword', value)
                  }
                  placeholder={interfaceText(
                    form.httpsCertificatePasswordConfigured
                      ? 'Configured'
                      : 'Certificate password',
                  )}
                  type="password"
                  value={form.httpsCertificatePassword}
                 {...interfaceTextProps("HTTPS certificate password")}/>
              </Form.Group>
              <Form.Group widths="equal">
                <Form.Input
                  aria-label={interfaceText("API rate limit permits")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("API Permits/min")}
                  onChange={(_, { value }) => update('rateLimitApi', value)}
                  type="number"
                  value={form.rateLimitApi}
                 {...interfaceTextProps("API rate limit permits")}/>
                <Form.Input
                  aria-label={interfaceText("API rate limit window seconds")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("API Window sec")}
                  onChange={(_, { value }) => update('rateLimitApiWindow', value)}
                  type="number"
                  value={form.rateLimitApiWindow}
                 {...interfaceTextProps("API rate limit window seconds")}/>
                <Form.Input
                  aria-label={interfaceText("Federation rate limit permits")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Federation Permits/min")}
                  onChange={(_, { value }) => update('rateLimitFederation', value)}
                  type="number"
                  value={form.rateLimitFederation}
                 {...interfaceTextProps("Federation rate limit permits")}/>
                <Form.Input
                  aria-label={interfaceText("Federation rate limit window seconds")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Federation Window sec")}
                  onChange={(_, { value }) =>
                    update('rateLimitFederationWindow', value)
                  }
                  type="number"
                  value={form.rateLimitFederationWindow}
                 {...interfaceTextProps("Federation rate limit window seconds")}/>
              </Form.Group>
              <Form.Group widths="equal">
                <Form.Input
                  aria-label={interfaceText("Mesh gateway rate limit permits")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Mesh Permits/min")}
                  onChange={(_, { value }) => update('rateLimitMesh', value)}
                  type="number"
                  value={form.rateLimitMesh}
                 {...interfaceTextProps("Mesh gateway rate limit permits")}/>
                <Form.Input
                  aria-label={interfaceText("Mesh gateway rate limit window seconds")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Mesh Window sec")}
                  onChange={(_, { value }) => update('rateLimitMeshWindow', value)}
                  type="number"
                  value={form.rateLimitMeshWindow}
                 {...interfaceTextProps("Mesh gateway rate limit window seconds")}/>
              </Form.Group>
            </Form>
          </Card.Content>
        </Card>

        <Card fluid>
          <Card.Content>
            <Card.Header>
              <Icon name="sitemap" />
              <LocalizedText source={"Search and Network Policy"} /></Card.Header>
            <Card.Meta><LocalizedText source={"Incoming search throttles, request filters, and managed blacklist setup."} /></Card.Meta>
          </Card.Content>
          <Card.Content>
            <div className="integration-status-row">
              {boolLabel(form.blacklistEnabled, 'Blacklist On', 'Blacklist Off')}
              {boolLabel(form.dhtEnabled, 'DHT On', 'DHT Off')}
              {boolLabel(form.dhtLanOnly, 'LAN Only', 'Public DHT')}
              {boolLabel(form.featureScenePodBridge, 'Bridge On', 'Bridge Off')}
              {boolLabel(form.rescueModeEnabled, 'Rescue On', 'Rescue Off')}
            </div>
            <Form>
              <Form.TextArea
                aria-label={interfaceText("Incoming search request filters")}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("Incoming Search Filter Regexes")}
                onChange={(_, { value }) => update('searchFilterRequest', value)}
                placeholder="(?i)forbidden term"
                value={form.searchFilterRequest}
               {...interfaceTextProps("Incoming search request filters")}/>
              <Form.Group widths="equal">
                <Form.Input
                  aria-label={interfaceText("Incoming search concurrency")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Incoming Concurrency")}
                  onChange={(_, { value }) =>
                    update('searchIncomingConcurrency', value)
                  }
                  type="number"
                  value={form.searchIncomingConcurrency}
                 {...interfaceTextProps("Incoming search concurrency")}/>
                <Form.Input
                  aria-label={interfaceText("Incoming search circuit breaker")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Circuit Breaker")}
                  onChange={(_, { value }) =>
                    update('searchIncomingCircuitBreaker', value)
                  }
                  type="number"
                  value={form.searchIncomingCircuitBreaker}
                 {...interfaceTextProps("Incoming search circuit breaker")}/>
                <Form.Input
                  aria-label={interfaceText("Incoming search response file limit")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Response File Limit")}
                  onChange={(_, { value }) =>
                    update('searchIncomingResponseFileLimit', value)
                  }
                  type="number"
                  value={form.searchIncomingResponseFileLimit}
                 {...interfaceTextProps("Incoming search response file limit")}/>
              </Form.Group>
              <Form.Group widths="equal">
                <Popup
                  className="admin-policy-popup"
                  content={interfaceText("Enable loading a managed CIDR/P2P/DAT blacklist file at startup.")}
                  trigger={
                    <Checkbox
                      aria-label={interfaceText("Enable managed blacklist")}
                      checked={form.blacklistEnabled}
                      disabled={!remoteConfiguration || saving}
                      label={interfaceText("Enable managed blacklist")}
                      onChange={(_, { checked }) =>
                        update('blacklistEnabled', Boolean(checked))
                      }
                      toggle
                     {...interfaceTextProps("Enable managed blacklist")}/>
                  }
                 {...interfaceTextProps("Enable loading a managed CIDR/P2P/DAT blacklist file at startup.")}/>
                <Form.Input
                  aria-label={interfaceText("Managed blacklist file path")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Blacklist File")}
                  onChange={(_, { value }) => update('blacklistFile', value)}
                  value={form.blacklistFile}
                 {...interfaceTextProps("Managed blacklist file path")}/>
              </Form.Group>
              <Form.Group grouped>
                <Popup
                  className="admin-policy-popup"
                  content={interfaceText("Enable DHT rendezvous. Disable this when you want no DHT peer discovery.")}
                  trigger={
                    <Checkbox
                      aria-label={interfaceText("Enable DHT rendezvous")}
                      checked={form.dhtEnabled}
                      disabled={!remoteConfiguration || saving}
                      label={interfaceText("Enable DHT rendezvous")}
                      onChange={(_, { checked }) =>
                        update('dhtEnabled', Boolean(checked))
                      }
                      toggle
                     {...interfaceTextProps("Enable DHT rendezvous")}/>
                  }
                 {...interfaceTextProps("Enable DHT rendezvous. Disable this when you want no DHT peer discovery.")}/>
                <Popup
                  className="admin-policy-popup"
                  content={interfaceText("Keep DHT discovery away from public bootstrap routers and use only private or local discovery paths.")}
                  trigger={
                    <Checkbox
                      aria-label={interfaceText("Use LAN-only DHT rendezvous")}
                      checked={form.dhtLanOnly}
                      disabled={!remoteConfiguration || saving}
                      label={interfaceText("LAN-only DHT")}
                      onChange={(_, { checked }) =>
                        update('dhtLanOnly', Boolean(checked))
                      }
                      toggle
                     {...interfaceTextProps("Use LAN-only DHT rendezvous")}/>
                  }
                 {...interfaceTextProps("Keep DHT discovery away from public bootstrap routers and use only private or local discovery paths.")}/>
                <Popup
                  className="admin-policy-popup"
                  content={interfaceText("Opt in to experimental Scene and Pod bridge aggregation.")}
                  trigger={
                    <Checkbox
                      aria-label={interfaceText("Enable Scene Pod Bridge")}
                      checked={form.featureScenePodBridge}
                      disabled={!remoteConfiguration || saving}
                      label={interfaceText("Enable Scene Pod Bridge")}
                      onChange={(_, { checked }) =>
                        update('featureScenePodBridge', Boolean(checked))
                      }
                      toggle
                     {...interfaceTextProps("Enable Scene Pod Bridge")}/>
                  }
                 {...interfaceTextProps("Opt in to experimental Scene and Pod bridge aggregation.")}/>
                <Popup
                  className="admin-policy-popup"
                  content={interfaceText("Enable underperformance rescue policies for queued or stalled downloads.")}
                  trigger={
                    <Checkbox
                      aria-label={interfaceText("Enable rescue mode")}
                      checked={form.rescueModeEnabled}
                      disabled={!remoteConfiguration || saving}
                      label={interfaceText("Enable rescue mode")}
                      onChange={(_, { checked }) =>
                        update('rescueModeEnabled', Boolean(checked))
                      }
                      toggle
                     {...interfaceTextProps("Enable rescue mode")}/>
                  }
                 {...interfaceTextProps("Enable underperformance rescue policies for queued or stalled downloads.")}/>
              </Form.Group>
              <Form.Group widths="equal">
                <Form.Input
                  aria-label={interfaceText("DHT overlay TCP port")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Overlay TCP Port")}
                  onChange={(_, { value }) => update('dhtOverlayPort', value)}
                  type="number"
                  value={form.dhtOverlayPort}
                 {...interfaceTextProps("DHT overlay TCP port")}/>
                <Form.Input
                  aria-label={interfaceText("DHT UDP port")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("DHT UDP Port")}
                  onChange={(_, { value }) => update('dhtPort', value)}
                  type="number"
                  value={form.dhtPort}
                 {...interfaceTextProps("DHT UDP port")}/>
                <Form.Input
                  aria-label={interfaceText("DHT announce interval seconds")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("DHT Announce sec")}
                  onChange={(_, { value }) =>
                    update('dhtAnnounceIntervalSeconds', value)
                  }
                  type="number"
                  value={form.dhtAnnounceIntervalSeconds}
                 {...interfaceTextProps("DHT announce interval seconds")}/>
                <Form.Input
                  aria-label={interfaceText("Rescue max queue seconds")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Rescue Queue sec")}
                  onChange={(_, { value }) =>
                    update('rescueModeMaxQueueSeconds', value)
                  }
                  type="number"
                  value={form.rescueModeMaxQueueSeconds}
                 {...interfaceTextProps("Rescue max queue seconds")}/>
              </Form.Group>
              <Form.TextArea
                aria-label={interfaceText("DHT bootstrap routers")}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("DHT Bootstrap Routers")}
                onChange={(_, { value }) => update('dhtBootstrapRouters', value)}
                placeholder="router.bittorrent.com"
                value={form.dhtBootstrapRouters}
               {...interfaceTextProps("DHT bootstrap routers")}/>
            </Form>
          </Card.Content>
        </Card>

        <Card fluid>
          <Card.Content>
            <Card.Header>
              <Icon name="archive" />
              <LocalizedText source={"Retention and Storage"} /></Card.Header>
            <Card.Meta><LocalizedText source={"Search/event/log cleanup, transfer history, file records, share cache pressure, and search retention (max age, max count, cleanup interval)."} /></Card.Meta>
          </Card.Content>
          <Card.Content>
            <Form>
              <Form.Group widths="equal">
                <Form.Input
                  aria-label={interfaceText("Search retention minutes")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Search Retention min")}
                  onChange={(_, { value }) => update('retentionSearch', value)}
                  value={form.retentionSearch}
                 {...interfaceTextProps("Search retention minutes")}/>
                <Form.Input
                  aria-label={interfaceText("Event retention days")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Events Retention days")}
                  onChange={(_, { value }) => update('eventsRetention', value)}
                  type="number"
                  value={form.eventsRetention}
                 {...interfaceTextProps("Event retention days")}/>
                <Form.Input
                  aria-label={interfaceText("Log retention days")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Logs Retention days")}
                  min={2}
                  onChange={(_, { value }) => update('logRetention', value)}
                  type="number"
                  value={form.logRetention}
                 {...interfaceTextProps("Log retention days")}/>
              </Form.Group>
              <Form.Group widths="equal">
                <Form.Input
                  aria-label={interfaceText("Search retention max age days")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Search Max Age (days)")}
                  onChange={(_, { value }) => update('searchRetentionMaxAgeDays', value)}
                  type="number"
                  value={form.searchRetentionMaxAgeDays}
                 {...interfaceTextProps("Search retention max age days")}/>
                <Form.Input
                  aria-label={interfaceText("Search retention max count")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Search Max Count")}
                  onChange={(_, { value }) => update('searchRetentionMaxCount', value)}
                  type="number"
                  value={form.searchRetentionMaxCount}
                 {...interfaceTextProps("Search retention max count")}/>
                <Form.Input
                  aria-label={interfaceText("Search retention cleanup interval seconds")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Cleanup Interval (sec)")}
                  onChange={(_, { value }) => update('searchRetentionCleanupInterval', value)}
                  type="number"
                  value={form.searchRetentionCleanupInterval}
                 {...interfaceTextProps("Search retention cleanup interval seconds")}/>
              </Form.Group>
              <div
                aria-label={interfaceText("Transfer history retention settings")}
                className="admin-policy-table-scroll"
                role="region"
                tabIndex={0}
               {...interfaceTextProps("Transfer history retention settings")}>
                <Table
                  aria-label={interfaceText("Transfer history retention settings by status")}
                  celled
                  className="admin-policy-retention-table"
                  compact
                 {...interfaceTextProps("Transfer history retention settings by status")}>
                  <Table.Header>
                    <Table.Row>
                      <Table.HeaderCell><LocalizedText source={"History"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Succeeded"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Errored"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Cancelled"} /></Table.HeaderCell>
                    </Table.Row>
                  </Table.Header>
                  <Table.Body>
                    <Table.Row>
                      <Table.Cell><LocalizedText source={"Uploads"} /></Table.Cell>
                      <Table.Cell>
                        <Form.Input
                          aria-label={interfaceText("Upload succeeded retention minutes")}
                          disabled={!remoteConfiguration || saving}
                          onChange={(_, { value }) =>
                            update('retentionUploadSucceeded', value)
                          }
                          value={form.retentionUploadSucceeded}
                         {...interfaceTextProps("Upload succeeded retention minutes")}/>
                      </Table.Cell>
                      <Table.Cell>
                        <Form.Input
                          aria-label={interfaceText("Upload errored retention minutes")}
                          disabled={!remoteConfiguration || saving}
                          onChange={(_, { value }) =>
                            update('retentionUploadErrored', value)
                          }
                          value={form.retentionUploadErrored}
                         {...interfaceTextProps("Upload errored retention minutes")}/>
                      </Table.Cell>
                      <Table.Cell>
                        <Form.Input
                          aria-label={interfaceText("Upload cancelled retention minutes")}
                          disabled={!remoteConfiguration || saving}
                          onChange={(_, { value }) =>
                            update('retentionUploadCancelled', value)
                          }
                          value={form.retentionUploadCancelled}
                         {...interfaceTextProps("Upload cancelled retention minutes")}/>
                      </Table.Cell>
                    </Table.Row>
                    <Table.Row>
                      <Table.Cell><LocalizedText source={"Downloads"} /></Table.Cell>
                      <Table.Cell>
                        <Form.Input
                          aria-label={interfaceText("Download succeeded retention minutes")}
                          disabled={!remoteConfiguration || saving}
                          onChange={(_, { value }) =>
                            update('retentionDownloadSucceeded', value)
                          }
                          value={form.retentionDownloadSucceeded}
                         {...interfaceTextProps("Download succeeded retention minutes")}/>
                      </Table.Cell>
                      <Table.Cell>
                        <Form.Input
                          aria-label={interfaceText("Download errored retention minutes")}
                          disabled={!remoteConfiguration || saving}
                          onChange={(_, { value }) =>
                            update('retentionDownloadErrored', value)
                          }
                          value={form.retentionDownloadErrored}
                         {...interfaceTextProps("Download errored retention minutes")}/>
                      </Table.Cell>
                      <Table.Cell>
                        <Form.Input
                          aria-label={interfaceText("Download cancelled retention minutes")}
                          disabled={!remoteConfiguration || saving}
                          onChange={(_, { value }) =>
                            update('retentionDownloadCancelled', value)
                          }
                          value={form.retentionDownloadCancelled}
                         {...interfaceTextProps("Download cancelled retention minutes")}/>
                      </Table.Cell>
                    </Table.Row>
                  </Table.Body>
                </Table>
              </div>
              <Form.Group widths="equal">
                <Form.Input
                  aria-label={interfaceText("Complete file retention minutes")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Complete Files min")}
                  onChange={(_, { value }) => update('fileCompleteRetention', value)}
                  value={form.fileCompleteRetention}
                 {...interfaceTextProps("Complete file retention minutes")}/>
                <Form.Input
                  aria-label={interfaceText("Incomplete file retention minutes")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Incomplete Files min")}
                  onChange={(_, { value }) =>
                    update('fileIncompleteRetention', value)
                  }
                  value={form.fileIncompleteRetention}
                 {...interfaceTextProps("Incomplete file retention minutes")}/>
                <Form.Input
                  aria-label={interfaceText("Share cache workers")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Share Cache Workers")}
                  onChange={(_, { value }) => update('shareCacheWorkers', value)}
                  type="number"
                  value={form.shareCacheWorkers}
                 {...interfaceTextProps("Share cache workers")}/>
                <Form.Input
                  aria-label={interfaceText("Share cache retention minutes")}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Share Cache Retention min")}
                  onChange={(_, { value }) => update('shareCacheRetention', value)}
                  value={form.shareCacheRetention}
                 {...interfaceTextProps("Share cache retention minutes")}/>
              </Form.Group>
            </Form>
          </Card.Content>
        </Card>
      </Card.Group>

      <div className="integration-actions admin-policy-actions">
        <Popup
          className="admin-policy-popup"
          content={interfaceText("Persist the policy settings above to YAML. This does not test webhooks, run scripts, contact peers, restart the daemon, or mutate downloads.")}
          trigger={
            <Button
              disabled={!remoteConfiguration || missing.length > 0}
              icon
              labelPosition="left"
              loading={saving}
              onClick={saveYaml}
              primary
            >
              <Icon name="file alternate" />
              <LocalizedText source={"Save YAML"} /></Button>
          }
         {...interfaceTextProps("Persist the policy settings above to YAML. This does not test webhooks, run scripts, contact peers, restart the daemon, or mutate downloads.")}/>
        <Popup
          className="admin-policy-popup"
          content={interfaceText("Discard unsaved policy edits and restore values currently reported by the daemon.")}
          trigger={
            <Button
              disabled={saving}
              icon
              labelPosition="left"
              onClick={reset}
            >
              <Icon name="undo" />
              <LocalizedText source={"Reset"} /></Button>
          }
         {...interfaceTextProps("Discard unsaved policy edits and restore values currently reported by the daemon.")}/>
      </div>
    </div>
  );
};

export default AdminPolicies;
