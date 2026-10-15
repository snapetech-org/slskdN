import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
// <copyright file="SourceFeedIntegrationsPanel.jsx" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import React, { useEffect, useState } from 'react';
import * as YAML from 'yaml';
import * as optionsApi from '../../../lib/options';
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
} from 'semantic-ui-react';

const getOption = (source, ...keys) => {
  for (const key of keys) {
    if (source && Object.prototype.hasOwnProperty.call(source, key)) {
      return source[key];
    }
  }
  return undefined;
};


const getIntegrationsOptions = (options = {}) =>
  getOption(options, 'integration', 'Integration', 'integrations', 'Integrations') || {};

const getSpotifyOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'spotify', 'Spotify') || {};

const getYouTubeOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'youtube', 'YouTube', 'Youtube') || {};

const getLastFmOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'lastfm', 'LastFm') || {};

const boolLabel = (value, trueText = 'Enabled', falseText = 'Disabled') => (
  <Label>
    <Label.Detail>
      <Icon color={value ? 'green' : 'grey'} name={value ? 'check' : 'close'} />
    </Label.Detail>
    {value ? trueText : falseText}
  </Label>
);

const isConfigured = (value) =>
  value !== undefined && value !== null && value !== '';

const toNumber = (value, fallback) => {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
};

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
    spotifyTargetPlaylist:
      getOption(spotify, 'targetPlaylist', 'TargetPlaylist') || '',
    youTubeApiKey: '',
    youTubeConfigured: isConfigured(getOption(youtube, 'apiKey', 'ApiKey')),
    youTubeEnabled: Boolean(getOption(youtube, 'enabled', 'Enabled')),
  };
};

const SourceFeedIntegrationsPanel = ({ options }) => {
  useInterfaceLanguage();
  const remoteConfiguration = Boolean(
    getOption(options, 'remoteConfiguration', 'RemoteConfiguration'),
  );
  const [form, setForm] = useState(() => buildSourceFeedForm(options));
  const [savingAction, setSavingAction] = useState('');
  const [message, setMessage] = useState(null);
  const saving = Boolean(savingAction);

  useEffect(() => {
    setForm(buildSourceFeedForm(options));
  }, [options]);

  const update = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const reset = () => {
    setForm(buildSourceFeedForm(options));
    setMessage(null);
  };

  const missingRequiredSettings = [
    form.spotifyEnabled &&
      !form.spotifyConfigured &&
      !form.spotifyClientId.trim() &&
      'Spotify needs a client ID before account connection or provider imports can run.',
    form.youTubeEnabled &&
      !form.youTubeConfigured &&
      !form.youTubeApiKey.trim() &&
      'YouTube needs a Data API key before playlist expansion can run.',
    form.lastFmEnabled &&
      !form.lastFmConfigured &&
      !form.lastFmApiKey.trim() &&
      'Last.fm needs an API key before loved/recent/top imports can run.',
  ].filter(Boolean);
  const inferredSpotifyRedirectUri =
    form.spotifyRedirectUri.trim() ||
    (typeof window !== 'undefined'
      ? `${window.location.origin}/api/v0/integrations/spotify/callback`
      : '/api/v0/integrations/spotify/callback');

  const buildOverlay = () => {
    const spotifyPatch = {
      enabled: form.spotifyEnabled,
      maxItemsPerImport: toNumber(form.spotifyMaxItems, 500),
      market: form.spotifyMarket.trim().toUpperCase(),
      redirectUri: form.spotifyRedirectUri.trim(),
      timeoutSeconds: toNumber(form.spotifyTimeout, 20),
    };

    if (form.spotifyClientId.trim()) {
      spotifyPatch.clientId = form.spotifyClientId.trim();
    }

    if (form.spotifyClientSecret.trim()) {
      spotifyPatch.clientSecret = form.spotifyClientSecret.trim();
    }

    const youTubePatch = {
      enabled: form.youTubeEnabled,
    };

    if (form.youTubeApiKey.trim()) {
      youTubePatch.apiKey = form.youTubeApiKey.trim();
    }

    const lastFmPatch = {
      enabled: form.lastFmEnabled,
    };

    if (form.lastFmApiKey.trim()) {
      lastFmPatch.apiKey = form.lastFmApiKey.trim();
    }

    return {
      integration: {
        lastFm: lastFmPatch,
        spotify: spotifyPatch,
        youTube: youTubePatch,
      },
    };
  };

  const markSecretsConfigured = (overlay) => {
    const spotifyPatch = overlay.integration.spotify;
    const youTubePatch = overlay.integration.youTube;
    const lastFmPatch = overlay.integration.lastFm;

    setForm((current) => ({
      ...current,
      lastFmApiKey: '',
      lastFmConfigured: current.lastFmConfigured || Boolean(lastFmPatch.apiKey),
      spotifyClientId: '',
      spotifyClientSecret: '',
      spotifyConfigured: current.spotifyConfigured || Boolean(spotifyPatch.clientId),
      spotifySecretConfigured:
        current.spotifySecretConfigured || Boolean(spotifyPatch.clientSecret),
      youTubeApiKey: '',
      youTubeConfigured: current.youTubeConfigured || Boolean(youTubePatch.apiKey),
    }));
  };

  const applyRuntime = async () => {
    setSavingAction('runtime');
    setMessage(null);
    const overlay = buildOverlay();

    try {
      await optionsApi.applyOverlay(overlay);
      markSecretsConfigured(overlay);
      setMessage({
        positive: true,
        text: interfaceText("Source-feed integration settings applied for this running daemon."),
      });
    } catch (error) {
      setMessage({
        negative: true,
        text: getApiErrorMessage(error, { t: interfaceText }),
      });
    } finally {
      setSavingAction('');
    }
  };

  const saveYaml = async () => {
    setSavingAction('yaml');
    setMessage(null);
    const overlay = buildOverlay();

    try {
      const yaml = await optionsApi.getYaml();
      const document = YAML.parseDocument(yaml || '{}');
      const set = (path, value) => document.setIn(path, value);
      const spotifyPatch = overlay.integration.spotify;
      const youTubePatch = overlay.integration.youTube;
      const lastFmPatch = overlay.integration.lastFm;

      set(['integrations', 'spotify', 'enabled'], spotifyPatch.enabled);
      set(['integrations', 'spotify', 'redirect_uri'], spotifyPatch.redirectUri);
      set(['integrations', 'spotify', 'timeout_seconds'], spotifyPatch.timeoutSeconds);
      set(['integrations', 'spotify', 'max_items_per_import'], spotifyPatch.maxItemsPerImport);
      set(['integrations', 'spotify', 'market'], spotifyPatch.market);
      if (spotifyPatch.clientId) {
        set(['integrations', 'spotify', 'client_id'], spotifyPatch.clientId);
      }

      if (spotifyPatch.clientSecret) {
        set(['integrations', 'spotify', 'client_secret'], spotifyPatch.clientSecret);
      }

      set(['integrations', 'youtube', 'enabled'], youTubePatch.enabled);
      if (youTubePatch.apiKey) {
        set(['integrations', 'youtube', 'api_key'], youTubePatch.apiKey);
      }

      set(['integrations', 'lastfm', 'enabled'], lastFmPatch.enabled);
      if (lastFmPatch.apiKey) {
        set(['integrations', 'lastfm', 'api_key'], lastFmPatch.apiKey);
      }

      await optionsApi.updateYaml({ yaml: document.toString() });
      markSecretsConfigured(overlay);
      setMessage({
        positive: true,
        text: interfaceText("Source-feed integration settings saved to YAML."),
      });
    } catch (error) {
      setMessage({
        negative: true,
        text: getApiErrorMessage(error, { t: interfaceText }),
      });
    } finally {
      setSavingAction('');
    }
  };

  return (
    <Card fluid>
      <Card.Content>
        <Card.Header>
          <Icon name="rss" />
          <LocalizedText source={"Source Feed Imports"} /></Card.Header>
        <Card.Meta>
          <LocalizedText source={"Provider settings for Wishlist Import Feed previews."} /></Card.Meta>
      </Card.Content>
      <Card.Content>
        <div className="integration-status-row">
          {boolLabel(form.spotifyEnabled, 'Spotify On', 'Spotify Off')}
          <Label>
            <Icon name={form.spotifyConfigured ? 'key' : 'warning sign'} />
            <LocalizedText source={"Spotify Client ID"} />{" "}{form.spotifyConfigured ? <LocalizedText source={"Configured"} /> : <LocalizedText source={"Missing"} />}
          </Label>
          {boolLabel(form.youTubeEnabled, 'YouTube On', 'YouTube Off')}
          <Label>
            <Icon name={form.youTubeConfigured ? 'key' : 'warning sign'} />
            <LocalizedText source={"YouTube API Key"} />{" "}{form.youTubeConfigured ? <LocalizedText source={"Configured"} /> : <LocalizedText source={"Missing"} />}
          </Label>
          {boolLabel(form.lastFmEnabled, 'Last.fm On', 'Last.fm Off')}
          <Label>
            <Icon name={form.lastFmConfigured ? 'key' : 'warning sign'} />
            <LocalizedText source={"Last.fm API Key"} />{" "}{form.lastFmConfigured ? <LocalizedText source={"Configured"} /> : <LocalizedText source={"Missing"} />}
          </Label>
        </div>

        {!remoteConfiguration && (
          <Message
            info
            size="small"
          >
            <LocalizedText source={"Runtime configuration changes are disabled. Enable remote configuration or edit YAML in the Options tab to change these provider settings."} /></Message>
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
        {missingRequiredSettings.length > 0 && (
          <Message
            size="small"
            warning
          >
            <Message.List items={missingRequiredSettings} />
          </Message>
        )}

        <Form className="source-feed-settings-form">
          <Segment>
            <Header as="h4">
              <Icon name="spotify" />
              <LocalizedText source={"Spotify"} /></Header>
            <Message
              info
              size="small"
            >
              <Message.Header><LocalizedText source={"Spotify authorization redirect URI"} /></Message.Header>
              <LocalizedText source={"Register this Redirect URI in the Spotify developer dashboard:"} />{' '}
              <code>{inferredSpotifyRedirectUri}</code>
            </Message>
            <Popup
              content={interfaceText("Turns on Spotify source-feed imports and account connection. Private liked/saved/followed feeds still require a connected Spotify account or bearer token.")}
              trigger={
                <Checkbox
                  aria-label={interfaceText("Enable Spotify source-feed imports")}
                  checked={form.spotifyEnabled}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Enable Spotify imports")}
                  onChange={(_, { checked }) => update('spotifyEnabled', checked)}
                  toggle
                 {...interfaceTextProps("Enable Spotify source-feed imports")}/>
              }
             {...interfaceTextProps("Turns on Spotify source-feed imports and account connection. Private liked/saved/followed feeds still require a connected Spotify account or bearer token.")}/>
            <Form.Group widths="equal">
              <Form.Input
                aria-label={interfaceText("Spotify client ID")}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("Client ID")}
                onChange={(_, { value }) => update('spotifyClientId', value)}
                placeholder={form.spotifyConfigured ? 'Configured' : 'Spotify app client ID'}
                type="password"
                value={form.spotifyClientId}
               {...interfaceTextProps("Spotify client ID")}/>
              <Form.Input
                aria-label={interfaceText("Spotify client secret")}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("Client Secret")}
                onChange={(_, { value }) => update('spotifyClientSecret', value)}
                placeholder={
                  form.spotifySecretConfigured
                    ? 'Configured'
                    : 'Optional for OAuth; required for app-token public imports'
                }
                type="password"
                value={form.spotifyClientSecret}
               {...interfaceTextProps("Spotify client secret")}/>
            </Form.Group>
            <Form.Group widths="equal">
              <Form.Input
                aria-label={interfaceText("Spotify redirect URI")}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("Redirect URI")}
                onChange={(_, { value }) => update('spotifyRedirectUri', value)}
                placeholder={inferredSpotifyRedirectUri}
                value={form.spotifyRedirectUri}
               {...interfaceTextProps("Spotify redirect URI")}/>
              <Form.Input
                aria-label={interfaceText("Spotify market")}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("Market")}
                maxLength={2}
                onChange={(_, { value }) => update('spotifyMarket', value)}
                value={form.spotifyMarket}
               {...interfaceTextProps("Spotify market")}/>
            </Form.Group>
            <Form.Group widths="equal">
              <Form.Input
                aria-label={interfaceText("Spotify timeout seconds")}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("Timeout Seconds")}
                min={1}
                onChange={(_, { value }) => update('spotifyTimeout', value)}
                type="number"
                value={form.spotifyTimeout}
               {...interfaceTextProps("Spotify timeout seconds")}/>
              <Form.Input
                aria-label={interfaceText("Spotify max items per import")}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("Max Items Per Import")}
                min={1}
                onChange={(_, { value }) => update('spotifyMaxItems', value)}
                type="number"
                value={form.spotifyMaxItems}
               {...interfaceTextProps("Spotify max items per import")}/>
            </Form.Group>
          </Segment>

          <Segment>
            <Header as="h4">
              <Icon name="youtube play" />
              <LocalizedText source={"YouTube"} /></Header>
            <Popup
              content={interfaceText("Turns on YouTube Data API playlist expansion for explicitly previewed Import Feed URLs.")}
              trigger={
                <Checkbox
                  aria-label={interfaceText("Enable YouTube playlist source-feed imports")}
                  checked={form.youTubeEnabled}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Enable YouTube playlist expansion")}
                  onChange={(_, { checked }) => update('youTubeEnabled', checked)}
                  toggle
                 {...interfaceTextProps("Enable YouTube playlist source-feed imports")}/>
              }
             {...interfaceTextProps("Turns on YouTube Data API playlist expansion for explicitly previewed Import Feed URLs.")}/>
            <Form.Input
              aria-label={interfaceText("YouTube Data API key")}
              disabled={!remoteConfiguration || saving}
              label={interfaceText("API Key")}
              onChange={(_, { value }) => update('youTubeApiKey', value)}
              placeholder={form.youTubeConfigured ? 'Configured' : 'YouTube Data API key'}
              type="password"
              value={form.youTubeApiKey}
             {...interfaceTextProps("YouTube Data API key")}/>
          </Segment>

          <Segment>
            <Header as="h4">
              <Icon name="lastfm" />
              Last.fm
            </Header>
            <Popup
              content={interfaceText("Turns on Last.fm API imports for explicitly previewed loved, recent, and top-track user URLs.")}
              trigger={
                <Checkbox
                  aria-label={interfaceText("Enable Last.fm source-feed imports")}
                  checked={form.lastFmEnabled}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Enable Last.fm imports")}
                  onChange={(_, { checked }) => update('lastFmEnabled', checked)}
                  toggle
                 {...interfaceTextProps("Enable Last.fm source-feed imports")}/>
              }
             {...interfaceTextProps("Turns on Last.fm API imports for explicitly previewed loved, recent, and top-track user URLs.")}/>
            <Form.Input
              aria-label={interfaceText("Last.fm API key")}
              disabled={!remoteConfiguration || saving}
              label={interfaceText("API Key")}
              onChange={(_, { value }) => update('lastFmApiKey', value)}
              placeholder={form.lastFmConfigured ? 'Configured' : 'Last.fm API key'}
              type="password"
              value={form.lastFmApiKey}
             {...interfaceTextProps("Last.fm API key")}/>
          </Segment>
        </Form>

        <div className="integration-actions">
          <Popup
            content={interfaceText("Apply these source-feed integration settings through the runtime configuration overlay.")}
            trigger={
              <Button
                disabled={!remoteConfiguration || missingRequiredSettings.length > 0}
                icon
                labelPosition="left"
                loading={savingAction === 'runtime'}
                onClick={applyRuntime}
                primary
              >
                <Icon name="save" />
                <LocalizedText source={"Apply Runtime"} /></Button>
            }
           {...interfaceTextProps("Apply these source-feed integration settings through the runtime configuration overlay.")}/>
          <Popup
            content={interfaceText("Persist these source-feed integration settings to the YAML configuration file.")}
            trigger={
              <Button
                disabled={!remoteConfiguration || missingRequiredSettings.length > 0}
                icon
                labelPosition="left"
                loading={savingAction === 'yaml'}
                onClick={saveYaml}
              >
                <Icon name="file alternate" />
                <LocalizedText source={"Save YAML"} /></Button>
            }
           {...interfaceTextProps("Persist these source-feed integration settings to the YAML configuration file.")}/>
          <Popup
            content={interfaceText("Discard unsaved edits and restore the values currently reported by the daemon.")}
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
           {...interfaceTextProps("Discard unsaved edits and restore the values currently reported by the daemon.")}/>
        </div>
      </Card.Content>
    </Card>
  );
};


export default SourceFeedIntegrationsPanel;
