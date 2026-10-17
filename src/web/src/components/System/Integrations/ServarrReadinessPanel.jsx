import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
// <copyright file="ServarrReadinessPanel.jsx" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import React, { useState, useMemo } from 'react';
import * as lidarrAPI from '../../../lib/lidarr';
import {
  buildServarrCompatibilityPreview,
  buildServarrReadiness,
  formatServarrCompatibilityReport,
  summarizeServarrReadiness,
} from '../../../lib/servarrReadiness';
import {
  Button,
  Card,
  Form,
  Header,
  Icon,
  Input,
  Message,
  Popup,
  Segment,
  Table,
  Label,
} from 'semantic-ui-react';

const getOption = (source, ...keys) => {
  for (const key of keys) {
    if (source && Object.prototype.hasOwnProperty.call(source, key)) {
      return source[key];
    }
  }
  return undefined;
};

const boolLabel = (value, trueText = 'Enabled', falseText = 'Disabled') => (
  <Label>
    <Label.Detail>
      <Icon color={value ? 'green' : 'grey'} name={value ? 'check' : 'close'} />
    </Label.Detail>
    {value ? trueText : falseText}
  </Label>
);


const getIntegrationsOptions = (options = {}) =>
  getOption(options, 'integration', 'Integration', 'integrations', 'Integrations') || {};

const getLidarrOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'lidarr', 'Lidarr') || {};

const valueOrDash = (value) =>
  value === undefined || value === null || value === '' ? '-' : value;

const ServarrReadinessPanel = ({ options }) => {
  useInterfaceLanguage();
  const lidarrOptions = getLidarrOptions(options);
  const [copyStatus, setCopyStatus] = useState('');
  const [running, setRunning] = useState(false);
  const checks = buildServarrReadiness({
    apiKey: getOption(lidarrOptions, 'apiKey', 'ApiKey'),
    autoImportCompleted: getOption(
      lidarrOptions,
      'autoImportCompleted',
      'AutoImportCompleted',
    ),
    enabled: getOption(lidarrOptions, 'enabled', 'Enabled'),
    importPathFrom: getOption(lidarrOptions, 'importPathFrom', 'ImportPathFrom'),
    importPathTo: getOption(lidarrOptions, 'importPathTo', 'ImportPathTo'),
    syncWantedToWishlist: getOption(
      lidarrOptions,
      'syncWantedToWishlist',
      'SyncWantedToWishlist',
    ),
    url: getOption(lidarrOptions, 'url', 'Url'),
  });
  const summary = summarizeServarrReadiness(checks);
  const compatibility = buildServarrCompatibilityPreview({
    apiKey: getOption(lidarrOptions, 'apiKey', 'ApiKey'),
    autoImportCompleted: getOption(
      lidarrOptions,
      'autoImportCompleted',
      'AutoImportCompleted',
    ),
    enabled: getOption(lidarrOptions, 'enabled', 'Enabled'),
    importMode: getOption(lidarrOptions, 'importMode', 'ImportMode') || 'copy',
    importPathFrom: getOption(lidarrOptions, 'importPathFrom', 'ImportPathFrom'),
    importPathTo: getOption(lidarrOptions, 'importPathTo', 'ImportPathTo'),
    syncWantedToWishlist: getOption(
      lidarrOptions,
      'syncWantedToWishlist',
      'SyncWantedToWishlist',
    ),
    url: getOption(lidarrOptions, 'url', 'Url'),
  });

  const copyCompatibilityReport = async () => {
    const report = formatServarrCompatibilityReport(compatibility);
    if (!navigator.clipboard?.writeText) {
      setCopyStatus(interfaceText('Clipboard unavailable; copy the Servarr review manually.'));
      return;
    }

    try {
      await navigator.clipboard.writeText(report);
      setCopyStatus(interfaceText('Servarr compatibility review copied.'));
    } catch {
      setCopyStatus(interfaceText('Unable to copy Servarr compatibility review.'));
    }
  };

  const runReadyActions = async () => {
    setRunning(true);
    setCopyStatus('');

    try {
      if (!compatibility.supportsWantedPull) {
        setCopyStatus(interfaceText('Wanted pull is not ready; no Servarr action was run.'));
        return;
      }

      const result = await lidarrAPI.syncWanted();
      setCopyStatus(interfaceText(
        'Wanted sync ran: {created} created, {duplicates} duplicates, {skipped} skipped.',
        {
          created: result.createdCount ?? result.CreatedCount ?? 0,
          duplicates: result.duplicateCount ?? result.DuplicateCount ?? 0,
          skipped: result.skippedCount ?? result.SkippedCount ?? 0,
        },
      ));
    } catch (error) {
      setCopyStatus(getApiErrorMessage(error, { t: interfaceText }, 'Servarr action failed.'));
    } finally {
      setRunning(false);
    }
  };

  return (
    <Card fluid>
      <Card.Content>
        <Card.Header>
          <Icon name="settings" />
          <LocalizedText source={"Servarr Setup"} /></Card.Header>
        <Card.Meta>
          <LocalizedText source={"Local readiness checklist for indexer/download-client style integration."} /></Card.Meta>
      </Card.Content>
      <Card.Content>
        <div className="integration-section-header">
          <Header as="h4">
            <Icon name="clipboard check" />
            <LocalizedText source={"Compatibility Review"} /></Header>
          <Popup
            content={interfaceText("Copy the local Servarr compatibility review. This does not call Lidarr, create download clients, pull wanted items, or trigger imports.")}
            position="top center"
            trigger={
              <Button
                aria-label={interfaceText("Copy Servarr compatibility review")}
                onClick={copyCompatibilityReport}
                size="small"
               {...interfaceTextProps("Copy Servarr compatibility review")}>
                <Icon name="copy" />
                <LocalizedText source={"Copy Review"} /></Button>
              }
             {...interfaceTextProps("Copy the local Servarr compatibility review. This does not call Lidarr, create download clients, pull wanted items, or trigger imports.")}/>
          <Popup
            content={interfaceText("Run ready Servarr actions now. Currently this calls the configured Lidarr wanted-sync endpoint when wanted pull is ready; imports still require an explicit directory in the Lidarr panel.")}
            position="top center"
            trigger={
              <Button
                aria-label={interfaceText("Run ready Servarr actions")}
                disabled={!compatibility.supportsWantedPull}
                loading={running}
                onClick={runReadyActions}
                primary
                size="small"
               {...interfaceTextProps("Run ready Servarr actions")}>
                <Icon name="play" />
                <LocalizedText source={"Run Ready"} /></Button>
            }
           {...interfaceTextProps("Run ready Servarr actions now. Currently this calls the configured Lidarr wanted-sync endpoint when wanted pull is ready; imports still require an explicit directory in the Lidarr panel.")}/>
        </div>
        <div className="integration-status-row">
          <Label color={summary.status === 'Ready' ? 'green' : 'orange'}>
            <Icon name={summary.status === 'Ready' ? 'check circle' : 'warning sign'} />
            <LocalizedText source={summary.status} />
          </Label>
          <Label>
            {summary.ready}/{summary.total} <LocalizedText source={"checks ready"} /></Label>
          <Label color={compatibility.supportsWantedPull ? 'green' : 'grey'}>
            <LocalizedText source={"Wanted Pull"} />{" "}{compatibility.supportsWantedPull ? <LocalizedText source={"Ready"} /> : <LocalizedText source={"Not Ready"} />}
          </Label>
          <Label color={compatibility.supportsCompletedImport ? 'green' : 'grey'}>
            <LocalizedText source={"Import"} />{" "}{compatibility.supportsCompletedImport ? <LocalizedText source={"Ready"} /> : <LocalizedText source={"Not Ready"} />}
          </Label>
        </div>
        <Table
          celled
          compact
        >
          <Table.Header>
            <Table.Row>
              <Table.HeaderCell><LocalizedText source={"Check"} /></Table.HeaderCell>
              <Table.HeaderCell><LocalizedText source={"Status"} /></Table.HeaderCell>
              <Table.HeaderCell><LocalizedText source={"Why it matters"} /></Table.HeaderCell>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {checks.map((check) => (
              <Table.Row key={check.id}>
                <Table.Cell><LocalizedText source={check.title} /></Table.Cell>
                <Table.Cell>
                  {boolLabel(check.ready, 'Ready', 'Needs Setup')}
                </Table.Cell>
                <Table.Cell><LocalizedText source={check.description} /></Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table>
        <Message
          info
          size="small"
        >
          <LocalizedText source={"This checklist is diagnostic only. It does not register indexers, create download clients, pull wanted items, or trigger imports."} /></Message>
        {compatibility.actions.length > 0 && (
          <Message
            size="small"
            warning
          >
            <Message.Header><LocalizedText source={"Compatibility Actions"} /></Message.Header>
            <ul>
              {compatibility.actions.map((action) => (
                <li key={action}>{action}</li>
              ))}
            </ul>
          </Message>
        )}
        {copyStatus && (
          <Message
            info
            size="small"
          >
            {copyStatus}
          </Message>
        )}
      </Card.Content>
    </Card>
  );
};

export default ServarrReadinessPanel;
