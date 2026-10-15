import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
// <copyright file="LidarrPanel.jsx" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import React, { useState, useMemo } from 'react';
import {
  getStatus as lidarrGetStatus,
  getWantedMissing as lidarrGetWantedMissing,
  syncWanted as lidarrSyncWanted,
  importCompletedDirectory as lidarrImportCompletedDirectory,
} from '../../../lib/lidarr';
import { formatRegionalNumber, useRegionalLocale } from '../../../lib/regionalFormat';

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

const getIntegrationsOptions = (options = {}) =>
  getOption(options, 'integration', 'Integration', 'integrations', 'Integrations') || {};

const getLidarrOptions = (options = {}) =>
  getOption(getIntegrationsOptions(options), 'lidarr', 'Lidarr') || {};

const isConfigured = (value) =>
  value !== undefined && value !== null && value !== '';

const boolLabel = (value, trueText = 'Enabled', falseText = 'Disabled') => (
  <Label>
    <Label.Detail>
      <Icon color={value ? 'green' : 'grey'} name={value ? 'check' : 'close'} />
    </Label.Detail>
    {value ? trueText : falseText}
  </Label>
);

const valueOrDash = (value) =>
  value === undefined || value === null || value === '' ? '-' : value;

const LidarrPanel = ({ options }) => {
  useInterfaceLanguage();
  const regionalLocale = useRegionalLocale();
  const formatCount = (value) => formatRegionalNumber(value, undefined, regionalLocale);
  const lidarrOptions = getLidarrOptions(options);
  const [status, setStatus] = useState(null);
  const [wanted, setWanted] = useState([]);
  const [syncResult, setSyncResult] = useState(null);
  const [importDirectory, setImportDirectory] = useState('');
  const [importResult, setImportResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState('');
  const enabled = getOption(lidarrOptions, 'enabled', 'Enabled');

  const maskedApiKey = useMemo(() => {
    const apiKey = getOption(lidarrOptions, 'apiKey', 'ApiKey');
    return apiKey ? 'Configured' : 'Not configured';
  }, [lidarrOptions]);

  const run = async (name, action) => {
    setLoading(name);
    setError('');

    try {
      await action();
    } catch (error) {
      setError(getApiErrorMessage(error, { t: interfaceText }));
    } finally {
      setLoading('');
    }
  };

  return (
    <Card fluid>
      <Card.Content>
        <Card.Header>
          <Icon name="music" />
          <LocalizedText source={"Lidarr"} /></Card.Header>
        <Card.Meta><LocalizedText source={"Wanted-album sync and completed-download import bridge."} /></Card.Meta>
      </Card.Content>
      <Card.Content>
        <div className="integration-status-row">
          {boolLabel(enabled)}
          {boolLabel(
            getOption(lidarrOptions, 'syncWantedToWishlist', 'SyncWantedToWishlist'),
            'Wanted Sync',
            'Wanted Sync Off',
          )}
          {boolLabel(
            getOption(lidarrOptions, 'autoImportCompleted', 'AutoImportCompleted'),
            'Auto Import',
            'Auto Import Off',
          )}
          <Label>
            <Icon name={maskedApiKey === 'Configured' ? 'key' : 'warning sign'} />
            <LocalizedText source={"API Key"} />{" "}{maskedApiKey}
          </Label>
        </div>
        <Table
          basic="very"
          compact
          definition
        >
          <Table.Body>
            <Table.Row>
              <Table.Cell>URL</Table.Cell>
              <Table.Cell>{valueOrDash(getOption(lidarrOptions, 'url', 'Url'))}</Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell><LocalizedText source={"Timeout"} /></Table.Cell>
              <Table.Cell>
                {valueOrDash(getOption(lidarrOptions, 'timeoutSeconds', 'TimeoutSeconds'))}
                {<LocalizedText source={"s"} />}
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell><LocalizedText source={"Sync Interval"} /></Table.Cell>
              <Table.Cell>
                {valueOrDash(getOption(lidarrOptions, 'syncIntervalSeconds', 'SyncIntervalSeconds'))}
                {<LocalizedText source={"s"} />}
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell><LocalizedText source={"Import Mode"} /></Table.Cell>
              <Table.Cell>{valueOrDash(getOption(lidarrOptions, 'importMode', 'ImportMode'))}</Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell><LocalizedText source={"Import Path Map"} /></Table.Cell>
              <Table.Cell>
                {valueOrDash(getOption(lidarrOptions, 'importPathFrom', 'ImportPathFrom'))}
                {' -> '}
                {valueOrDash(getOption(lidarrOptions, 'importPathTo', 'ImportPathTo'))}
              </Table.Cell>
            </Table.Row>
          </Table.Body>
        </Table>
        {error && (
          <Message
            negative
            size="small"
          >
            {error}
          </Message>
        )}
        <div className="integration-actions">
          <Popup
            content={interfaceText("Fetch Lidarr system status using the configured URL and API key.")}
            trigger={
              <Button
                icon
                labelPosition="left"
                loading={loading === 'status'}
                onClick={() =>
                  run('status', async () => setStatus(await lidarrGetStatus()))
                }
              >
                <Icon name="heartbeat" />
                <LocalizedText source={"Check Status"} /></Button>
            }
           {...interfaceTextProps("Fetch Lidarr system status using the configured URL and API key.")}/>
          <Popup
            content={interfaceText("Preview Lidarr wanted albums that can be synced into slskdN Wishlist.")}
            trigger={
              <Button
                icon
                labelPosition="left"
                loading={loading === 'wanted'}
                onClick={() =>
                  run('wanted', async () =>
                    setWanted(await lidarrGetWantedMissing({ pageSize: 25 })),
                  )
                }
              >
                <Icon name="list" />
                <LocalizedText source={"Load Wanted"} /></Button>
            }
           {...interfaceTextProps("Preview Lidarr wanted albums that can be synced into slskdN Wishlist.")}/>
          <Popup
            content={interfaceText("Create or refresh slskdN Wishlist entries from Lidarr wanted albums.")}
            trigger={
              <Button
                icon
                labelPosition="left"
                loading={loading === 'sync'}
                onClick={() =>
                  run('sync', async () => setSyncResult(await lidarrSyncWanted()))
                }
                primary
              >
                <Icon name="sync" />
                <LocalizedText source={"Sync Wanted"} /></Button>
            }
           {...interfaceTextProps("Create or refresh slskdN Wishlist entries from Lidarr wanted albums.")}/>
        </div>
        {status && (
          <Message
            positive
            size="small"
          >
            <LocalizedText source={"Lidarr responded:"} />{" "}{status.appName || status.AppName || 'Lidarr'}{' '}
            {status.version || status.Version || ''}
          </Message>
        )}
        {syncResult && (
          <Message
            info
            size="small"
          >
            <LocalizedText
              source={"Wanted sync: {created} created, {duplicates} duplicates, {skipped} skipped."}
              values={{
                created: formatCount(syncResult.createdCount ?? syncResult.CreatedCount ?? 0),
                duplicates: formatCount(syncResult.duplicateCount ?? syncResult.DuplicateCount ?? 0),
                skipped: formatCount(syncResult.skippedCount ?? syncResult.SkippedCount ?? 0),
              }}
            />
          </Message>
        )}
        {wanted.length > 0 && (
          <Table
            celled
            compact
          >
            <Table.Header>
              <Table.Row>
                <Table.HeaderCell><LocalizedText source={"Artist"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Album"} /></Table.HeaderCell>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {wanted.slice(0, 10).map((album) => (
                <Table.Row key={album.id || album.Id || `${album.title}-${album.foreignAlbumId}`}>
                  <Table.Cell>
                    {album.artist?.artistName || album.Artist?.ArtistName || '-'}
                  </Table.Cell>
                  <Table.Cell>{album.title || album.Title || '-'}</Table.Cell>
                </Table.Row>
              ))}
            </Table.Body>
          </Table>
        )}
        <Segment className="integration-manual-import">
          <Header as="h4"><LocalizedText source={"Manual Import"} /></Header>
          <Input
            action={(
              <Popup
                content={interfaceText("Ask Lidarr to scan this completed directory now. This manual action works even when automatic import is disabled and can be retried immediately.")}
                position="top center"
                trigger={(
                  <Button
                    content={interfaceText("Import")}
                    disabled={!importDirectory.trim()}
                    icon="download"
                    loading={loading === 'import'}
                    onClick={() =>
                      run('import', async () => {
                        const result = await lidarrImportCompletedDirectory({
                          directory: importDirectory.trim(),
                        });
                        setImportResult(result);
                        if (result?.commandId || result?.CommandId) {
                          setImportDirectory('');
                        }
                      })}
                   {...interfaceTextProps("Import")}/>
                )}
               {...interfaceTextProps("Ask Lidarr to scan this completed directory now. This manual action works even when automatic import is disabled and can be retried immediately.")}/>
            )}
            fluid
            onChange={(_, { value }) => setImportDirectory(value)}
            placeholder={interfaceText("Completed download directory visible to slskdN...")}
            value={importDirectory}
           {...interfaceTextProps("Completed download directory visible to slskdN...")}/>
          {importResult && (
            <Message
              positive={Boolean(importResult.commandId || importResult.CommandId)}
              size="small"
              warning={Boolean(importResult.skippedReason || importResult.SkippedReason)}
            >
              {importResult.skippedReason || importResult.SkippedReason ? (
                `Skipped: ${importResult.skippedReason || importResult.SkippedReason} ` +
                `(${importResult.candidateCount ?? importResult.CandidateCount ?? 0} candidate(s), ` +
                `${importResult.safeCandidateCount ?? importResult.SafeCandidateCount ?? 0} safe, ` +
                `${importResult.rejectedCandidateCount ?? importResult.RejectedCandidateCount ?? 0} rejected)`
              ) : (
                `Queued Lidarr command ${importResult.commandId || importResult.CommandId || '-'} ` +
                `(${importResult.safeCandidateCount ?? importResult.SafeCandidateCount ?? 0} safe candidate(s))`
              )}
            </Message>
          )}
        </Segment>
      </Card.Content>
    </Card>
  );
};



export default LidarrPanel;
