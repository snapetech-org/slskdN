import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getRegionalLocale } from '../../../lib/regionalFormat';
// <copyright file="MetadataProcessingPanel.jsx" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import React, { useEffect, useState } from 'react';
import { Card, Header, Icon, Label, Message, Table } from 'semantic-ui-react';
import { getMetadataProcessingStatus } from '../../../lib/slskdn';

const labelColor = (status) =>
  ({ complete: 'green', failed: 'red', running: 'blue', skipped: 'grey' })[
    status
  ] || 'grey';

const MetadataStageLabels = {
  acoustid: 'AcoustID',
  auto_tagging: 'Auto-tagging',
  chromaprint: 'Chromaprint',
  hash: 'Hashing',
  musicbrainz: 'MusicBrainz',
};

const MetadataStatusLabels = {
  complete: 'Complete',
  failed: 'Failed',
  running: 'Running',
  skipped: 'Skipped',
};

const localizedMetadataStage = (value) => {
  const key = String(value || '').toLowerCase();
  const label = MetadataStageLabels[key];
  return label ? <LocalizedText source={label} /> : value;
};

const localizedMetadataStatus = (value) => {
  const key = String(value || '').toLowerCase();
  const label = MetadataStatusLabels[key];
  return label ? <LocalizedText source={label} /> : value;
};

const LocalizedMetadataDetail = ({ source }) => {
  if (!source || source.toLowerCase() === 'in progress') return <LocalizedText source="In Progress" />;
  const templates = [
    [/^Fingerprint extraction failed: ([^:]+): (.*)$/, 'Fingerprint extraction failed: {exceptionType}: {message}', (m) => ({ exceptionType: m[1], message: m[2] })],
    [/^Hash processing failed \((.*)\)$/, 'Hash processing failed ({exceptionType})', (m) => ({ exceptionType: m[1] })],
    [/^Auto-tagging failed \((.*)\)$/, 'Auto-tagging failed ({exceptionType})', (m) => ({ exceptionType: m[1] })],
    [/^Provider request failed \((.*)\)$/, 'Provider request failed ({exceptionType})', (m) => ({ exceptionType: m[1] })],
    [/^Recording (.*)$/, 'Recording {recordingId}', (m) => ({ recordingId: m[1] })],
  ];
  for (const [pattern, template, values] of templates) {
    const match = source.match(pattern);
    if (match) return <LocalizedText source={template} values={values(match)} />;
  }
  const known = new Set([
    'Not a supported audio file', 'File is too small for hashing',
    'Existing hash reused', 'Hash computation failed', 'Hash stored',
    'Fingerprint stored', 'No fingerprint produced', 'Chromaprint is not configured',
    'AcoustID or MusicBrainz is not configured', 'Fingerprint data is unavailable',
    'No recording match', 'Recording metadata not found', 'Recording metadata found',
    'Tags updated', 'No tag changes needed', 'Recording resolved',
  ]);
  return known.has(source) ? <LocalizedText source={source} /> : source;
};

const MetadataProcessingPanel = () => {
  useInterfaceLanguage();
  const [status, setStatus] = useState({ active: [], history: [] });

  useEffect(() => {
    let mounted = true;
    const refresh = async () => {
      const next = await getMetadataProcessingStatus(50);
      if (mounted) setStatus(next || { active: [], history: [] });
    };
    refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);

  const rows = [...(status.active || []), ...(status.history || [])];
  return (
    <Card fluid>
      <Card.Content>
        <Header as="h3">
          <Icon name="music" /> <LocalizedText source={"Metadata processing activity"} /></Header>
        <p>
          <LocalizedText source={"Live and recent hashing, Chromaprint, AcoustID, and MusicBrainz stages for completed audio downloads."} /></p>
        {rows.length === 0 ? (
          <Message info content={interfaceText("No metadata processing activity has been recorded since startup.")}  {...interfaceTextProps("No metadata processing activity has been recorded since startup.")}/>
        ) : (
          <Table compact selectable stackable>
            <Table.Header>
              <Table.Row>
                <Table.HeaderCell><LocalizedText source={"File"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Stage"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Status"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Started"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Result"} /></Table.HeaderCell>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {rows.map((item) => (
                <Table.Row key={item.id}>
                  <Table.Cell>{item.filename}</Table.Cell>
                  <Table.Cell>{localizedMetadataStage(item.stage)}</Table.Cell>
                  <Table.Cell>
                    <Label color={labelColor(item.status)}>{localizedMetadataStatus(item.status)}</Label>
                  </Table.Cell>
                  <Table.Cell>{new Date(item.startedAt).toLocaleString(getRegionalLocale())}</Table.Cell>
                  <Table.Cell><LocalizedMetadataDetail source={item.detail || 'In Progress'} /></Table.Cell>
                </Table.Row>
              ))}
            </Table.Body>
          </Table>
        )}
      </Card.Content>
    </Card>
  );
};

export default MetadataProcessingPanel;
