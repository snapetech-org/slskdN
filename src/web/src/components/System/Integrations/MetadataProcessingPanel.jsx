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

const MetadataProcessingPanel = () => {
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
          <Icon name="music" /> Metadata processing activity
        </Header>
        <p>
          Live and recent hashing, Chromaprint, AcoustID, and MusicBrainz stages
          for completed audio downloads.
        </p>
        {rows.length === 0 ? (
          <Message info content="No metadata processing activity has been recorded since startup." />
        ) : (
          <Table compact selectable stackable>
            <Table.Header>
              <Table.Row>
                <Table.HeaderCell>File</Table.HeaderCell>
                <Table.HeaderCell>Stage</Table.HeaderCell>
                <Table.HeaderCell>Status</Table.HeaderCell>
                <Table.HeaderCell>Started</Table.HeaderCell>
                <Table.HeaderCell>Result</Table.HeaderCell>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {rows.map((item) => (
                <Table.Row key={item.id}>
                  <Table.Cell>{item.filename}</Table.Cell>
                  <Table.Cell>{item.stage}</Table.Cell>
                  <Table.Cell>
                    <Label color={labelColor(item.status)}>{item.status}</Label>
                  </Table.Cell>
                  <Table.Cell>{new Date(item.startedAt).toLocaleString(getRegionalLocale())}</Table.Cell>
                  <Table.Cell>{item.detail || 'In progress'}</Table.Cell>
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
