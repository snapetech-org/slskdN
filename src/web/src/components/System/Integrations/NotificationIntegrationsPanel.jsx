import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
// <copyright file="NotificationIntegrationsPanel.js" company="slskdN Team">
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
  getOption(options, 'integration', 'Integration', 'integrations', 'Integrations') ||
  {};

const getPushbulletOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'pushbullet', 'Pushbullet') || {};

const getNtfyOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'ntfy', 'Ntfy') || {};

const getPushoverOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'pushover', 'Pushover') || {};

const boolLabel = (value, trueText = 'Enabled', falseText = 'Disabled') => (
  <Label>
    <Label.Detail>
      <Icon
        color={value ? 'green' : 'grey'}
        name={value ? 'check' : 'close'}
      />
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
    pushoverUserKeyConfigured: isConfigured(getOption(pushover, 'userKey', 'UserKey')),
  };
};

const NotificationIntegrationsPanel = ({ options }) => {
  useInterfaceLanguage();
  const remoteConfiguration = Boolean(
    getOption(options, 'remoteConfiguration', 'RemoteConfiguration'),
  );
  const [form, setForm] = useState(() => buildNotificationForm(options));
  const [savingAction, setSavingAction] = useState('');
  const [message, setMessage] = useState(null);
  const saving = Boolean(savingAction);

  useEffect(() => {
    setForm(buildNotificationForm(options));
  }, [options]);

  const update = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const reset = () => {
    setForm(buildNotificationForm(options));
    setMessage(null);
  };

  const missingRequiredSettings = [
    form.pushbulletEnabled &&
      !form.pushbulletAccessTokenConfigured &&
      !form.pushbulletAccessToken.trim() &&
      'Pushbullet needs an access token before notifications can be sent.',
    form.ntfyEnabled &&
      !form.ntfyUrl.trim() &&
      'Ntfy needs a topic URL before notifications can be sent.',
    form.pushoverEnabled &&
      !form.pushoverUserKeyConfigured &&
      !form.pushoverUserKey.trim() &&
      'Pushover needs a user key before notifications can be sent.',
    form.pushoverEnabled &&
      !form.pushoverTokenConfigured &&
      !form.pushoverToken.trim() &&
      'Pushover needs an API token before notifications can be sent.',
  ].filter(Boolean);

  const buildOverlay = () => {
    const pushbulletPatch = {
      cooldownTime: toNumber(form.pushbulletCooldownTime, 900000),
      enabled: form.pushbulletEnabled,
      notificationPrefix: form.pushbulletPrefix.trim(),
      notifyOnPrivateMessage: form.pushbulletNotifyOnPrivateMessage,
      notifyOnRoomMention: form.pushbulletNotifyOnRoomMention,
      retryAttempts: toNumber(form.pushbulletRetryAttempts, 3),
    };

    if (form.pushbulletAccessToken.trim()) {
      pushbulletPatch.accessToken = form.pushbulletAccessToken.trim();
    }

    const ntfyPatch = {
      enabled: form.ntfyEnabled,
      notificationPrefix: form.ntfyPrefix.trim(),
      notifyOnPrivateMessage: form.ntfyNotifyOnPrivateMessage,
      notifyOnRoomMention: form.ntfyNotifyOnRoomMention,
      url: form.ntfyUrl.trim(),
    };

    if (form.ntfyAccessToken.trim()) {
      ntfyPatch.accessToken = form.ntfyAccessToken.trim();
    }

    const pushoverPatch = {
      enabled: form.pushoverEnabled,
      notificationPrefix: form.pushoverPrefix.trim(),
      notifyOnPrivateMessage: form.pushoverNotifyOnPrivateMessage,
      notifyOnRoomMention: form.pushoverNotifyOnRoomMention,
    };

    if (form.pushoverUserKey.trim()) {
      pushoverPatch.userKey = form.pushoverUserKey.trim();
    }

    if (form.pushoverToken.trim()) {
      pushoverPatch.token = form.pushoverToken.trim();
    }

    return {
      integration: {
        ntfy: ntfyPatch,
        pushbullet: pushbulletPatch,
        pushover: pushoverPatch,
      },
    };
  };

  const markSecretsConfigured = (overlay) => {
    const pushbulletPatch = overlay.integration.pushbullet;
    const ntfyPatch = overlay.integration.ntfy;
    const pushoverPatch = overlay.integration.pushover;

    setForm((current) => ({
      ...current,
      ntfyAccessToken: '',
      ntfyAccessTokenConfigured:
        current.ntfyAccessTokenConfigured || Boolean(ntfyPatch.accessToken),
      pushbulletAccessToken: '',
      pushbulletAccessTokenConfigured:
        current.pushbulletAccessTokenConfigured ||
        Boolean(pushbulletPatch.accessToken),
      pushoverToken: '',
      pushoverTokenConfigured:
        current.pushoverTokenConfigured || Boolean(pushoverPatch.token),
      pushoverUserKey: '',
      pushoverUserKeyConfigured:
        current.pushoverUserKeyConfigured || Boolean(pushoverPatch.userKey),
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
        text: interfaceText("Notification integration settings applied for this running daemon."),
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
      const pushbulletPatch = overlay.integration.pushbullet;
      const ntfyPatch = overlay.integration.ntfy;
      const pushoverPatch = overlay.integration.pushover;

      set(['integrations', 'pushbullet', 'enabled'], pushbulletPatch.enabled);
      set(
        ['integrations', 'pushbullet', 'notification_prefix'],
        pushbulletPatch.notificationPrefix,
      );
      set(
        ['integrations', 'pushbullet', 'notify_on_private_message'],
        pushbulletPatch.notifyOnPrivateMessage,
      );
      set(
        ['integrations', 'pushbullet', 'notify_on_room_mention'],
        pushbulletPatch.notifyOnRoomMention,
      );
      set(
        ['integrations', 'pushbullet', 'retry_attempts'],
        pushbulletPatch.retryAttempts,
      );
      set(
        ['integrations', 'pushbullet', 'cooldown_time'],
        pushbulletPatch.cooldownTime,
      );
      if (pushbulletPatch.accessToken) {
        set(
          ['integrations', 'pushbullet', 'access_token'],
          pushbulletPatch.accessToken,
        );
      }

      set(['integrations', 'ntfy', 'enabled'], ntfyPatch.enabled);
      set(['integrations', 'ntfy', 'url'], ntfyPatch.url);
      set(
        ['integrations', 'ntfy', 'notification_prefix'],
        ntfyPatch.notificationPrefix,
      );
      set(
        ['integrations', 'ntfy', 'notify_on_private_message'],
        ntfyPatch.notifyOnPrivateMessage,
      );
      set(
        ['integrations', 'ntfy', 'notify_on_room_mention'],
        ntfyPatch.notifyOnRoomMention,
      );
      if (ntfyPatch.accessToken) {
        set(['integrations', 'ntfy', 'access_token'], ntfyPatch.accessToken);
      }

      set(['integrations', 'pushover', 'enabled'], pushoverPatch.enabled);
      set(
        ['integrations', 'pushover', 'notification_prefix'],
        pushoverPatch.notificationPrefix,
      );
      set(
        ['integrations', 'pushover', 'notify_on_private_message'],
        pushoverPatch.notifyOnPrivateMessage,
      );
      set(
        ['integrations', 'pushover', 'notify_on_room_mention'],
        pushoverPatch.notifyOnRoomMention,
      );
      if (pushoverPatch.userKey) {
        set(['integrations', 'pushover', 'user_key'], pushoverPatch.userKey);
      }

      if (pushoverPatch.token) {
        set(['integrations', 'pushover', 'token'], pushoverPatch.token);
      }

      await optionsApi.updateYaml({ yaml: document.toString() });
      markSecretsConfigured(overlay);
      setMessage({
        positive: true,
        text: interfaceText("Notification integration settings saved to YAML."),
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
          <Icon name="bell" />
          <LocalizedText source={"Notifications"} /></Card.Header>
        <Card.Meta>
          <LocalizedText source={"Push notifications for private messages and room mentions."} /></Card.Meta>
      </Card.Content>
      <Card.Content>
        <div className="integration-status-row">
          {boolLabel(form.pushbulletEnabled, 'Pushbullet On', 'Pushbullet Off')}
          <Label>
            <Icon
              name={form.pushbulletAccessTokenConfigured ? 'key' : 'warning sign'}
            />
            <LocalizedText source={"Pushbullet Token"} />{' '}
            {form.pushbulletAccessTokenConfigured ? <LocalizedText source={"Configured"} /> : <LocalizedText source={"Missing"} />}
          </Label>
          {boolLabel(form.ntfyEnabled, 'Ntfy On', 'Ntfy Off')}
          <Label>
            <Icon name={form.ntfyUrl ? 'linkify' : 'warning sign'} />
            <LocalizedText source={"Ntfy URL"} />{" "}{form.ntfyUrl ? <LocalizedText source={"Configured"} /> : <LocalizedText source={"Missing"} />}
          </Label>
          {boolLabel(form.pushoverEnabled, 'Pushover On', 'Pushover Off')}
          <Label>
            <Icon
              name={
                form.pushoverUserKeyConfigured && form.pushoverTokenConfigured
                  ? 'key'
                  : 'warning sign'
              }
            />
            <LocalizedText source={"Pushover Secrets"} />{' '}
            {form.pushoverUserKeyConfigured && form.pushoverTokenConfigured
              ? <LocalizedText source={"Configured"} />
              : <LocalizedText source={"Missing"} />}
          </Label>
        </div>

        {!remoteConfiguration && (
          <Message
            info
            size="small"
          >
            <LocalizedText source={"Runtime configuration changes are disabled. Enable remote configuration or edit YAML in the Options tab to change notification settings."} /></Message>
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

        <Form className="notification-settings-form">
          <Segment>
            <Header as="h4">
              <Icon name="paper plane" />
              <LocalizedText source={"Pushbullet"} /></Header>
            <Popup
              content={interfaceText("Turn on Pushbullet delivery for enabled notification triggers.")}
              trigger={
                <Checkbox
                  aria-label={interfaceText("Enable Pushbullet notifications")}
                  checked={form.pushbulletEnabled}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Enable Pushbullet")}
                  onChange={(_, { checked }) =>
                    update('pushbulletEnabled', checked)
                  }
                  toggle
                 {...interfaceTextProps("Enable Pushbullet notifications")}/>
              }
             {...interfaceTextProps("Turn on Pushbullet delivery for enabled notification triggers.")}/>
            <Form.Group widths="equal">
              <Form.Input
                aria-label={interfaceText("Pushbullet access token")}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("Access Token")}
                onChange={(_, { value }) => update('pushbulletAccessToken', value)}
                placeholder={
                  form.pushbulletAccessTokenConfigured
                    ? 'Configured'
                    : 'Pushbullet access token'
                }
                type="password"
                value={form.pushbulletAccessToken}
               {...interfaceTextProps("Pushbullet access token")}/>
              <Form.Input
                aria-label={interfaceText("Pushbullet notification prefix")}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("Title Prefix")}
                onChange={(_, { value }) => update('pushbulletPrefix', value)}
                value={form.pushbulletPrefix}
               {...interfaceTextProps("Pushbullet notification prefix")}/>
            </Form.Group>
            <Form.Group widths="equal">
              <Form.Input
                aria-label={interfaceText("Pushbullet retry attempts")}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("Retry Attempts")}
                max={5}
                min={0}
                onChange={(_, { value }) =>
                  update('pushbulletRetryAttempts', value)
                }
                type="number"
                value={form.pushbulletRetryAttempts}
               {...interfaceTextProps("Pushbullet retry attempts")}/>
              <Form.Input
                aria-label={interfaceText("Pushbullet cooldown milliseconds")}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("Cooldown Milliseconds")}
                min={0}
                onChange={(_, { value }) =>
                  update('pushbulletCooldownTime', value)
                }
                type="number"
                value={form.pushbulletCooldownTime}
               {...interfaceTextProps("Pushbullet cooldown milliseconds")}/>
            </Form.Group>
            <Form.Group grouped>
              <Popup
                content={interfaceText("Send Pushbullet notifications when a private message arrives.")}
                trigger={
                  <Checkbox
                    aria-label={interfaceText("Pushbullet private message notifications")}
                    checked={form.pushbulletNotifyOnPrivateMessage}
                    disabled={!remoteConfiguration || saving}
                    label={interfaceText("Private messages")}
                    onChange={(_, { checked }) =>
                      update('pushbulletNotifyOnPrivateMessage', checked)
                    }
                   {...interfaceTextProps("Pushbullet private message notifications")}/>
                }
               {...interfaceTextProps("Send Pushbullet notifications when a private message arrives.")}/>
              <Popup
                content={interfaceText("Send Pushbullet notifications when your username is mentioned in a joined room.")}
                trigger={
                  <Checkbox
                    aria-label={interfaceText("Pushbullet room mention notifications")}
                    checked={form.pushbulletNotifyOnRoomMention}
                    disabled={!remoteConfiguration || saving}
                    label={interfaceText("Room mentions")}
                    onChange={(_, { checked }) =>
                      update('pushbulletNotifyOnRoomMention', checked)
                    }
                   {...interfaceTextProps("Pushbullet room mention notifications")}/>
                }
               {...interfaceTextProps("Send Pushbullet notifications when your username is mentioned in a joined room.")}/>
            </Form.Group>
          </Segment>

          <Segment>
            <Header as="h4">
              <Icon name="rss" />
              <LocalizedText source={"ntfy"} /></Header>
            <Popup
              content={interfaceText("Turn on Ntfy delivery for enabled notification triggers.")}
              trigger={
                <Checkbox
                  aria-label={interfaceText("Enable Ntfy notifications")}
                  checked={form.ntfyEnabled}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Enable Ntfy")}
                  onChange={(_, { checked }) => update('ntfyEnabled', checked)}
                  toggle
                 {...interfaceTextProps("Enable Ntfy notifications")}/>
              }
             {...interfaceTextProps("Turn on Ntfy delivery for enabled notification triggers.")}/>
            <Form.Group widths="equal">
              <Form.Input
                aria-label={interfaceText("Ntfy topic URL")}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("Topic URL")}
                onChange={(_, { value }) => update('ntfyUrl', value)}
                placeholder="https://ntfy.sh/mytopic"
                value={form.ntfyUrl}
               {...interfaceTextProps("Ntfy topic URL")}/>
              <Form.Input
                aria-label={interfaceText("Ntfy access token")}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("Access Token")}
                onChange={(_, { value }) => update('ntfyAccessToken', value)}
                placeholder={interfaceText(form.ntfyAccessTokenConfigured
                  ? 'Configured'
                  : 'Optional Ntfy token')}
                type="password"
                value={form.ntfyAccessToken}
               {...interfaceTextProps("Ntfy access token")}/>
            </Form.Group>
            <Form.Input
              aria-label={interfaceText("Ntfy notification prefix")}
              disabled={!remoteConfiguration || saving}
              label={interfaceText("Title Prefix")}
              onChange={(_, { value }) => update('ntfyPrefix', value)}
              value={form.ntfyPrefix}
             {...interfaceTextProps("Ntfy notification prefix")}/>
            <Form.Group grouped>
              <Popup
                content={interfaceText("Send Ntfy notifications when a private message arrives.")}
                trigger={
                  <Checkbox
                    aria-label={interfaceText("Ntfy private message notifications")}
                    checked={form.ntfyNotifyOnPrivateMessage}
                    disabled={!remoteConfiguration || saving}
                    label={interfaceText("Private messages")}
                    onChange={(_, { checked }) =>
                      update('ntfyNotifyOnPrivateMessage', checked)
                    }
                   {...interfaceTextProps("Ntfy private message notifications")}/>
                }
               {...interfaceTextProps("Send Ntfy notifications when a private message arrives.")}/>
              <Popup
                content={interfaceText("Send Ntfy notifications when your username is mentioned in a joined room.")}
                trigger={
                  <Checkbox
                    aria-label={interfaceText("Ntfy room mention notifications")}
                    checked={form.ntfyNotifyOnRoomMention}
                    disabled={!remoteConfiguration || saving}
                    label={interfaceText("Room mentions")}
                    onChange={(_, { checked }) =>
                      update('ntfyNotifyOnRoomMention', checked)
                    }
                   {...interfaceTextProps("Ntfy room mention notifications")}/>
                }
               {...interfaceTextProps("Send Ntfy notifications when your username is mentioned in a joined room.")}/>
            </Form.Group>
          </Segment>

          <Segment>
            <Header as="h4">
              <Icon name="mobile alternate" />
              <LocalizedText source={"Pushover"} /></Header>
            <Popup
              content={interfaceText("Turn on Pushover delivery for enabled notification triggers.")}
              trigger={
                <Checkbox
                  aria-label={interfaceText("Enable Pushover notifications")}
                  checked={form.pushoverEnabled}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Enable Pushover")}
                  onChange={(_, { checked }) => update('pushoverEnabled', checked)}
                  toggle
                 {...interfaceTextProps("Enable Pushover notifications")}/>
              }
             {...interfaceTextProps("Turn on Pushover delivery for enabled notification triggers.")}/>
            <Form.Group widths="equal">
              <Form.Input
                aria-label={interfaceText("Pushover user key")}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("User Key")}
                onChange={(_, { value }) => update('pushoverUserKey', value)}
                placeholder={
                  form.pushoverUserKeyConfigured
                    ? 'Configured'
                    : 'Pushover user key'
                }
                type="password"
                value={form.pushoverUserKey}
               {...interfaceTextProps("Pushover user key")}/>
              <Form.Input
                aria-label={interfaceText("Pushover API token")}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("API Token")}
                onChange={(_, { value }) => update('pushoverToken', value)}
                placeholder={interfaceText(form.pushoverTokenConfigured
                  ? 'Configured'
                  : 'Pushover application token')}
                type="password"
                value={form.pushoverToken}
               {...interfaceTextProps("Pushover API token")}/>
            </Form.Group>
            <Form.Input
              aria-label={interfaceText("Pushover notification prefix")}
              disabled={!remoteConfiguration || saving}
              label={interfaceText("Title Prefix")}
              onChange={(_, { value }) => update('pushoverPrefix', value)}
              value={form.pushoverPrefix}
             {...interfaceTextProps("Pushover notification prefix")}/>
            <Form.Group grouped>
              <Popup
                content={interfaceText("Send Pushover notifications when a private message arrives.")}
                trigger={
                  <Checkbox
                    aria-label={interfaceText("Pushover private message notifications")}
                    checked={form.pushoverNotifyOnPrivateMessage}
                    disabled={!remoteConfiguration || saving}
                    label={interfaceText("Private messages")}
                    onChange={(_, { checked }) =>
                      update('pushoverNotifyOnPrivateMessage', checked)
                    }
                   {...interfaceTextProps("Pushover private message notifications")}/>
                }
               {...interfaceTextProps("Send Pushover notifications when a private message arrives.")}/>
              <Popup
                content={interfaceText("Send Pushover notifications when your username is mentioned in a joined room.")}
                trigger={
                  <Checkbox
                    aria-label={interfaceText("Pushover room mention notifications")}
                    checked={form.pushoverNotifyOnRoomMention}
                    disabled={!remoteConfiguration || saving}
                    label={interfaceText("Room mentions")}
                    onChange={(_, { checked }) =>
                      update('pushoverNotifyOnRoomMention', checked)
                    }
                   {...interfaceTextProps("Pushover room mention notifications")}/>
                }
               {...interfaceTextProps("Send Pushover notifications when your username is mentioned in a joined room.")}/>
            </Form.Group>
          </Segment>
        </Form>

        <div className="integration-actions">
          <Popup
            content={interfaceText("Apply these notification settings through the runtime configuration overlay.")}
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
           {...interfaceTextProps("Apply these notification settings through the runtime configuration overlay.")}/>
          <Popup
            content={interfaceText("Persist these notification settings to the YAML configuration file.")}
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
           {...interfaceTextProps("Persist these notification settings to the YAML configuration file.")}/>
          <Popup
            content={interfaceText("Discard unsaved notification edits and restore the values currently reported by the daemon.")}
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
           {...interfaceTextProps("Discard unsaved notification edits and restore the values currently reported by the daemon.")}/>
        </div>
      </Card.Content>
    </Card>
  );
};

export default NotificationIntegrationsPanel;
