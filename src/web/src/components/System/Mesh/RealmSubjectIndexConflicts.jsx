import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
// <copyright file="RealmSubjectIndexConflicts.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import {
  fetchRealmSubjectIndexConflicts,
  getRealmSubjectIndexConflictValues,
  getRealmSubjectIndexConflicts,
  formatRealmSubjectIndexConflictReport,
  summarizeRealmSubjectIndexConflicts,
} from '../../../lib/realmSubjectIndexes';
import React, { useMemo, useState } from 'react';
import {
  Button,
  Header,
  Icon,
  Input,
  Label,
  Message,
  Popup,
  Segment,
  Statistic,
  Table,
} from 'semantic-ui-react';

const get = (source, camel, pascal, fallback = '') =>
  source?.[camel] ?? source?.[pascal] ?? fallback;

const RealmSubjectIndexConflicts = () => {
  useInterfaceLanguage();
  const [copyStatus, setCopyStatus] = useState('');
  const [disabledAuthorities, setDisabledAuthorities] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [realmId, setRealmId] = useState('scene-realm');
  const [report, setReport] = useState(null);
  const conflicts = getRealmSubjectIndexConflicts(report || {});
  const summary = useMemo(
    () => summarizeRealmSubjectIndexConflicts(report || {}),
    [report],
  );

  const loadConflicts = async () => {
    const trimmedRealmId = realmId.trim();
    if (!trimmedRealmId) {
      setError(interfaceText("Enter a realm id before loading subject-index conflicts."));
      return;
    }

    setCopyStatus('');
    setError('');
    setLoading(true);
    try {
      const response = await fetchRealmSubjectIndexConflicts({
        realmId: trimmedRealmId,
      });
      setReport(response.data);
    } catch (loadError) {
      setError(getApiErrorMessage(loadError, { t: interfaceText }));
    } finally {
      setLoading(false);
    }
  };

  const copyReport = async () => {
    if (!report) return;

    const text = formatRealmSubjectIndexConflictReport({
      disabledAuthorities,
      report,
    });

    if (!navigator.clipboard?.writeText) {
      setCopyStatus(interfaceText('Clipboard unavailable; copy the visible conflict report manually.'));
      return;
    }

    try {
      await navigator.clipboard.writeText(text);
      setCopyStatus(interfaceText('Realm subject-index conflict report copied.'));
    } catch {
      setCopyStatus(interfaceText('Unable to copy realm subject-index conflict report.'));
    }
  };

  const toggleAuthority = (authorityKey) => {
    setDisabledAuthorities((current) =>
      current.includes(authorityKey)
        ? current.filter((key) => key !== authorityKey)
        : [...current, authorityKey],
    );
  };

  return (
    <Segment className="realm-subject-index-conflicts">
      <div className="mesh-evidence-policy-header">
        <Header as="h3">
          <Icon name="object group" />
          <Header.Content>
            <LocalizedText source={"Realm Subject Index Conflicts"} /><Header.Subheader>
              <LocalizedText source={"Review accepted realm index disagreements with provenance before trusting a realm authority."} /></Header.Subheader>
          </Header.Content>
        </Header>
        <div className="integration-actions">
          <Popup
            content={interfaceText("Load the read-only conflict report for this realm. This does not publish, disable, search, browse, or download.")}
            position="top center"
            trigger={
              <Button
                aria-label={interfaceText("Load realm subject-index conflicts")}
                loading={loading}
                onClick={loadConflicts}
                primary
               {...interfaceTextProps("Load realm subject-index conflicts")}>
                <Icon name="refresh" />
                <LocalizedText source={"Load Conflicts"} /></Button>
            }
           {...interfaceTextProps("Load the read-only conflict report for this realm. This does not publish, disable, search, browse, or download.")}/>
          <Popup
            content={interfaceText("Copy the visible conflict report, including local authority disable selections. This does not change backend realm governance.")}
            position="top center"
            trigger={
              <Button
                aria-label={interfaceText("Copy realm subject-index conflict report")}
                disabled={!report}
                onClick={copyReport}
               {...interfaceTextProps("Copy realm subject-index conflict report")}>
                <Icon name="copy" />
                <LocalizedText source={"Copy Report"} /></Button>
            }
           {...interfaceTextProps("Copy the visible conflict report, including local authority disable selections. This does not change backend realm governance.")}/>
        </div>
      </div>
      <Input
        aria-label={interfaceText("Realm subject-index realm id")}
        fluid
        label={interfaceText("Realm ID")}
        onChange={(_, { value }) => setRealmId(value)}
        placeholder="scene-realm"
        value={realmId}
       {...interfaceTextProps("Realm subject-index realm id")}/>
      {error && (
        <Message
          error
          size="small"
        >
          {String(error)}
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
      {report && (
        <>
          <Statistic.Group
            size="small"
            widths="five"
          >
            <Statistic>
              <Statistic.Value>{summary.indexCount}</Statistic.Value>
              <Statistic.Label><LocalizedText source={"Indexes"} /></Statistic.Label>
            </Statistic>
            <Statistic>
              <Statistic.Value>{summary.entryCount}</Statistic.Value>
              <Statistic.Label><LocalizedText source={"Entries"} /></Statistic.Label>
            </Statistic>
            <Statistic color={summary.conflictCount > 0 ? 'orange' : 'green'}>
              <Statistic.Value>{summary.conflictCount}</Statistic.Value>
              <Statistic.Label><LocalizedText source={"Conflicts"} /></Statistic.Label>
            </Statistic>
            <Statistic>
              <Statistic.Value>{summary.conflictTypeCount}</Statistic.Value>
              <Statistic.Label><LocalizedText source={"Types"} /></Statistic.Label>
            </Statistic>
            <Statistic color={disabledAuthorities.length > 0 ? 'yellow' : 'grey'}>
              <Statistic.Value>{disabledAuthorities.length}</Statistic.Value>
              <Statistic.Label><LocalizedText source={"Local Disables"} /></Statistic.Label>
            </Statistic>
          </Statistic.Group>
          {conflicts.length === 0 ? (
            <Message
              positive
              size="small"
            >
              <LocalizedText source={"No subject-index conflicts reported for"} />{" "}{get(report, 'realmId', 'RealmId')}.
            </Message>
          ) : (
            <Table
              celled
              compact
              stackable
            >
              <Table.Header>
                <Table.Row>
                  <Table.HeaderCell><LocalizedText source={"Conflict"} /></Table.HeaderCell>
                  <Table.HeaderCell><LocalizedText source={"Subject"} /></Table.HeaderCell>
                  <Table.HeaderCell><LocalizedText source={"Values"} /></Table.HeaderCell>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {conflicts.map((conflict) => (
                  <Table.Row key={get(conflict, 'id', 'Id', get(conflict, 'key', 'Key'))}>
                    <Table.Cell>
                      <Label color="orange">
                        {get(conflict, 'type', 'Type', 'unknown')}
                      </Label>
                      <div>
                        <strong>{get(conflict, 'key', 'Key', '-')}</strong>
                      </div>
                      <div className="integration-muted-copy">
                        {get(conflict, 'description', 'Description', '-')}
                      </div>
                    </Table.Cell>
                    <Table.Cell>
                      <div>{get(conflict, 'subjectId', 'SubjectId', '-')}</div>
                      <div className="integration-muted-copy">
                        {get(conflict, 'subjectNamespace', 'SubjectNamespace', '-')}
                      </div>
                    </Table.Cell>
                    <Table.Cell>
                      {getRealmSubjectIndexConflictValues(conflict).map((value) => {
                        const authorityKey = get(
                          value,
                          'authorityKey',
                          'AuthorityKey',
                          '-',
                        );
                        const disabled = disabledAuthorities.includes(authorityKey);

                        return (
                          <Segment
                            compact
                            key={`${authorityKey}:${get(value, 'value', 'Value')}`}
                          >
                            <div className="integration-status-row">
                              <Label color={disabled ? 'grey' : 'green'}>
                                {disabled ? <LocalizedText source={"Locally disabled"} /> : <LocalizedText source={"Active"} />}
                              </Label>
                              <Label basic>{authorityKey}</Label>
                              <Popup
                                content={`${disabled ? 'Re-enable' : 'Disable'} this authority locally for review. This only changes browser review state and does not update realm governance.`}
                                position="top center"
                                trigger={
                                  <Button
                                    aria-label={`${disabled ? 'Enable' : 'Disable'} authority ${authorityKey}`}
                                    onClick={() => toggleAuthority(authorityKey)}
                                    size="mini"
                                  >
                                    <Icon name={disabled ? 'unlock' : 'ban'} />
                                    {disabled ? <LocalizedText source={"Enable"} /> : <LocalizedText source={"Disable"} />}
                                  </Button>
                                }
                              />
                            </div>
                            <div>{get(value, 'value', 'Value', '-')}</div>
                            <div className="integration-muted-copy">
                              {get(value, 'provenance', 'Provenance', '-')}
                            </div>
                          </Segment>
                        );
                      })}
                    </Table.Cell>
                  </Table.Row>
                ))}
              </Table.Body>
            </Table>
          )}
        </>
      )}
    </Segment>
  );
};

export default RealmSubjectIndexConflicts;
