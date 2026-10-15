import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
// <copyright file="FtpIntegrationPanel.jsx" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import React, { useEffect, useState } from 'react';
import * as YAML from 'yaml';
import * as optionsApi from '../../../lib/options';
import {
  Button,
  Card,
  Checkbox,
  Dropdown,
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

const getFtpOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'ftp', 'Ftp', 'FTP') || {};

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

const ftpEncryptionOptions = ['auto', 'none', 'implicit', 'explicit'].map((value) => ({
  key: value,
  text: value,
  value,
}));

const buildFtpForm = (options = {}) => {
  const ftp = getFtpOptions(options);

  return {
    address: getOption(ftp, 'address', 'Address') || '',
    connectionTimeout: String(
      getOption(ftp, 'connectionTimeout', 'ConnectionTimeout') ?? 5000,
    ),
    enabled: Boolean(getOption(ftp, 'enabled', 'Enabled')),
    encryptionMode:
      getOption(ftp, 'encryptionMode', 'EncryptionMode') || 'auto',
    ignoreCertificateErrors: Boolean(
      getOption(ftp, 'ignoreCertificateErrors', 'IgnoreCertificateErrors'),
    ),
    overwriteExisting:
      getOption(ftp, 'overwriteExisting', 'OverwriteExisting') ?? true,
    password: '',
    passwordConfigured: isConfigured(getOption(ftp, 'password', 'Password')),
    port: String(getOption(ftp, 'port', 'Port') ?? 21),
    remotePath: getOption(ftp, 'remotePath', 'RemotePath') || '/',
    retryAttempts: String(getOption(ftp, 'retryAttempts', 'RetryAttempts') ?? 3),
    username: getOption(ftp, 'username', 'Username') || '',
  };
};

const FtpIntegrationPanel = ({ options }) => {
  useInterfaceLanguage();
  const remoteConfiguration = Boolean(
    getOption(options, 'remoteConfiguration', 'RemoteConfiguration'),
  );
  const [form, setForm] = useState(() => buildFtpForm(options));
  const [savingAction, setSavingAction] = useState('');
  const [message, setMessage] = useState(null);
  const saving = Boolean(savingAction);

  useEffect(() => {
    setForm(buildFtpForm(options));
  }, [options]);

  const update = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const reset = () => {
    setForm(buildFtpForm(options));
    setMessage(null);
  };

  const missingRequiredSettings = [
    form.enabled &&
      !form.address.trim() &&
      'FTP needs a server address before completed downloads can be uploaded.',
  ].filter(Boolean);

  const buildOverlay = () => {
    const ftpPatch = {
      address: form.address.trim(),
      connectionTimeout: toNumber(form.connectionTimeout, 5000),
      enabled: form.enabled,
      encryptionMode: form.encryptionMode,
      ignoreCertificateErrors: form.ignoreCertificateErrors,
      overwriteExisting: form.overwriteExisting,
      port: toNumber(form.port, 21),
      remotePath: form.remotePath.trim() || '/',
      retryAttempts: toNumber(form.retryAttempts, 3),
      username: form.username.trim(),
    };

    if (form.password.trim()) {
      ftpPatch.password = form.password.trim();
    }

    return {
      integration: {
        ftp: ftpPatch,
      },
    };
  };

  const markSecretsConfigured = (overlay) => {
    const ftpPatch = overlay.integration.ftp;

    setForm((current) => ({
      ...current,
      password: '',
      passwordConfigured: current.passwordConfigured || Boolean(ftpPatch.password),
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
        text: interfaceText("FTP integration settings applied for this running daemon."),
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
      const ftpPatch = overlay.integration.ftp;

      set(['integrations', 'ftp', 'enabled'], ftpPatch.enabled);
      set(['integrations', 'ftp', 'address'], ftpPatch.address);
      set(['integrations', 'ftp', 'port'], ftpPatch.port);
      set(['integrations', 'ftp', 'username'], ftpPatch.username);
      if (ftpPatch.password) {
        set(['integrations', 'ftp', 'password'], ftpPatch.password);
      }

      set(['integrations', 'ftp', 'remote_path'], ftpPatch.remotePath);
      set(['integrations', 'ftp', 'encryption_mode'], ftpPatch.encryptionMode);
      set(
        ['integrations', 'ftp', 'ignore_certificate_errors'],
        ftpPatch.ignoreCertificateErrors,
      );
      set(
        ['integrations', 'ftp', 'overwrite_existing'],
        ftpPatch.overwriteExisting,
      );
      set(
        ['integrations', 'ftp', 'connection_timeout'],
        ftpPatch.connectionTimeout,
      );
      set(['integrations', 'ftp', 'retry_attempts'], ftpPatch.retryAttempts);

      await optionsApi.updateYaml({ yaml: document.toString() });
      markSecretsConfigured(overlay);
      setMessage({
        positive: true,
        text: interfaceText("FTP integration settings saved to YAML."),
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
          <Icon name="upload" />
          <LocalizedText source={"FTP Uploads"} /></Card.Header>
        <Card.Meta>
          <LocalizedText source={"Completed-download upload target and connection policy."} /></Card.Meta>
      </Card.Content>
      <Card.Content>
        <div className="integration-status-row">
          {boolLabel(form.enabled, 'FTP On', 'FTP Off')}
          <Label>
            <Icon name={form.address ? 'server' : 'warning sign'} />
            <LocalizedText source={"Address"} />{" "}{form.address ? <LocalizedText source={"Configured"} /> : <LocalizedText source={"Missing"} />}
          </Label>
          <Label>
            <Icon name={form.passwordConfigured ? 'key' : 'lock'} />
            <LocalizedText source={"Password"} />{" "}{form.passwordConfigured ? <LocalizedText source={"Configured"} /> : <LocalizedText source={"Optional"} />}
          </Label>
          {boolLabel(
            form.overwriteExisting,
            'Overwrite Existing',
            'Skip Existing',
          )}
        </div>

        {!remoteConfiguration && (
          <Message
            info
            size="small"
          >
            <LocalizedText source={"Runtime configuration changes are disabled. Enable remote configuration or edit YAML in the Options tab to change FTP settings."} /></Message>
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

        <Form className="ftp-settings-form">
          <Popup
            content={interfaceText("Turn on FTP uploads after completed downloads. This affects future completed-transfer handling.")}
            trigger={
              <Checkbox
                aria-label={interfaceText("Enable FTP completed-download uploads")}
                checked={form.enabled}
                disabled={!remoteConfiguration || saving}
                label={interfaceText("Enable FTP uploads")}
                onChange={(_, { checked }) => update('enabled', checked)}
                toggle
               {...interfaceTextProps("Enable FTP completed-download uploads")}/>
            }
           {...interfaceTextProps("Turn on FTP uploads after completed downloads. This affects future completed-transfer handling.")}/>
          <Form.Group widths="equal">
            <Form.Input
              aria-label={interfaceText("FTP server address")}
              disabled={!remoteConfiguration || saving}
              label={interfaceText("Server Address")}
              onChange={(_, { value }) => update('address', value)}
              placeholder="ftp.example.net"
              value={form.address}
             {...interfaceTextProps("FTP server address")}/>
            <Form.Input
              aria-label={interfaceText("FTP server port")}
              disabled={!remoteConfiguration || saving}
              label={interfaceText("Port")}
              max={65535}
              min={1}
              onChange={(_, { value }) => update('port', value)}
              type="number"
              value={form.port}
             {...interfaceTextProps("FTP server port")}/>
            <Form.Select
              aria-label={interfaceText("FTP encryption mode")}
              disabled={!remoteConfiguration || saving}
              label={interfaceText("Encryption")}
              onChange={(_, { value }) => update('encryptionMode', value)}
              options={ftpEncryptionOptions}
              value={form.encryptionMode}
             {...interfaceTextProps("FTP encryption mode")}/>
          </Form.Group>
          <Form.Group widths="equal">
            <Form.Input
              aria-label={interfaceText("FTP username")}
              disabled={!remoteConfiguration || saving}
              label={interfaceText("Username")}
              onChange={(_, { value }) => update('username', value)}
              value={form.username}
             {...interfaceTextProps("FTP username")}/>
            <Form.Input
              aria-label={interfaceText("FTP password")}
              disabled={!remoteConfiguration || saving}
              label={interfaceText("Password")}
              onChange={(_, { value }) => update('password', value)}
              placeholder={form.passwordConfigured ? 'Configured' : 'Optional password'}
              type="password"
              value={form.password}
             {...interfaceTextProps("FTP password")}/>
          </Form.Group>
          <Form.Input
            aria-label={interfaceText("FTP remote upload path")}
            disabled={!remoteConfiguration || saving}
            label={interfaceText("Remote Path")}
            onChange={(_, { value }) => update('remotePath', value)}
            value={form.remotePath}
           {...interfaceTextProps("FTP remote upload path")}/>
          <Form.Group widths="equal">
            <Form.Input
              aria-label={interfaceText("FTP connection timeout milliseconds")}
              disabled={!remoteConfiguration || saving}
              label={interfaceText("Connection Timeout Milliseconds")}
              min={0}
              onChange={(_, { value }) => update('connectionTimeout', value)}
              type="number"
              value={form.connectionTimeout}
             {...interfaceTextProps("FTP connection timeout milliseconds")}/>
            <Form.Input
              aria-label={interfaceText("FTP retry attempts")}
              disabled={!remoteConfiguration || saving}
              label={interfaceText("Retry Attempts")}
              max={5}
              min={0}
              onChange={(_, { value }) => update('retryAttempts', value)}
              type="number"
              value={form.retryAttempts}
             {...interfaceTextProps("FTP retry attempts")}/>
          </Form.Group>
          <Form.Group grouped>
            <Popup
              content={interfaceText("Overwrite files already present at the remote FTP path instead of skipping them.")}
              trigger={
                <Checkbox
                  aria-label={interfaceText("FTP overwrite existing remote files")}
                  checked={form.overwriteExisting}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Overwrite existing remote files")}
                  onChange={(_, { checked }) =>
                    update('overwriteExisting', checked)
                  }
                 {...interfaceTextProps("FTP overwrite existing remote files")}/>
              }
             {...interfaceTextProps("Overwrite files already present at the remote FTP path instead of skipping them.")}/>
            <Popup
              content={interfaceText("Allow FTP certificate validation failures for self-signed or untrusted certificates.")}
              trigger={
                <Checkbox
                  aria-label={interfaceText("FTP ignore certificate errors")}
                  checked={form.ignoreCertificateErrors}
                  disabled={!remoteConfiguration || saving}
                  label={interfaceText("Ignore certificate errors")}
                  onChange={(_, { checked }) =>
                    update('ignoreCertificateErrors', checked)
                  }
                 {...interfaceTextProps("FTP ignore certificate errors")}/>
              }
             {...interfaceTextProps("Allow FTP certificate validation failures for self-signed or untrusted certificates.")}/>
          </Form.Group>
        </Form>

        <div className="integration-actions">
          <Popup
            content={interfaceText("Apply these FTP settings through the runtime configuration overlay.")}
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
           {...interfaceTextProps("Apply these FTP settings through the runtime configuration overlay.")}/>
          <Popup
            content={interfaceText("Persist these FTP settings to the YAML configuration file.")}
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
           {...interfaceTextProps("Persist these FTP settings to the YAML configuration file.")}/>
          <Popup
            content={interfaceText("Discard unsaved FTP edits and restore the values currently reported by the daemon.")}
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
           {...interfaceTextProps("Discard unsaved FTP edits and restore the values currently reported by the daemon.")}/>
        </div>
      </Card.Content>
    </Card>
  );
};


export default FtpIntegrationPanel;
