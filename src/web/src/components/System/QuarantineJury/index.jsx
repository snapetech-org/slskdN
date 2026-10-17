import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getRegionalLocale } from '../../../lib/regionalFormat';
// <copyright file="index.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import * as quarantineJuryApi from '../../../lib/quarantineJury';
import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Form,
  Header,
  Icon,
  Label,
  Loader,
  Message,
  Modal,
  Popup,
  Segment,
  Statistic,
  Table,
} from 'semantic-ui-react';

const verdictNames = {
  0: 'Needs Manual Review',
  1: 'Uphold Quarantine',
  2: 'Release Candidate',
  NeedsManualReview: 'Needs Manual Review',
  ReleaseCandidate: 'Release Candidate',
  UpholdQuarantine: 'Uphold Quarantine',
};

const verdictColor = (verdict) => {
  const label = normalizeVerdict(verdict);
  if (label === 'Release Candidate') return 'green';
  if (label === 'Uphold Quarantine') return 'red';
  return 'yellow';
};

const normalizeVerdict = (verdict) =>
  verdictNames[verdict] || (verdict ? String(verdict) : interfaceText('Needs Manual Review'));

const valueOrDash = (value) => {
  if (Array.isArray(value)) return value.length > 0 ? value.join(', ') : '-';
  return value || '-';
};

const asArray = (value) => (Array.isArray(value) ? value : []);
const appOwnedRouteAttemptErrors = new Set([
  'Request not found.',
  'Route metadata must be opaque and safe.',
  'Route targets must be selected safe jurors.',
  'Routing backend is not available.',
]);

const RouteAttemptError = ({ message }) => appOwnedRouteAttemptErrors.has(message)
  ? <LocalizedText source={message} />
  : message || <LocalizedText source={'Failed'} />;

const normalizeRequest = (request = {}) => ({
  createdAt: request.createdAt ?? request.CreatedAt ?? '',
  evidence: request.evidence ?? request.Evidence ?? [],
  id: request.id ?? request.Id ?? '',
  jurors: request.jurors ?? request.Jurors ?? [],
  localReason: request.localReason ?? request.LocalReason ?? '',
  minJurorVotes: request.minJurorVotes ?? request.MinJurorVotes ?? 2,
});

const normalizeEvidence = (evidence = {}) => ({
  reference: evidence.reference ?? evidence.Reference ?? '',
  summary: evidence.summary ?? evidence.Summary ?? '',
  type: evidence.type ?? evidence.Type ?? '',
});

const normalizeAggregate = (aggregate = {}) => ({
  dissentingJurors:
    aggregate.dissentingJurors ?? aggregate.DissentingJurors ?? [],
  quorumReached: aggregate.quorumReached ?? aggregate.QuorumReached ?? false,
  reason: aggregate.reason ?? aggregate.Reason ?? '',
  recommendation:
    aggregate.recommendation ?? aggregate.Recommendation ?? 'NeedsManualReview',
  requiredVotes: aggregate.requiredVotes ?? aggregate.RequiredVotes ?? 0,
  totalVerdicts: aggregate.totalVerdicts ?? aggregate.TotalVerdicts ?? 0,
  verdictCounts: aggregate.verdictCounts ?? aggregate.VerdictCounts ?? {},
});

const normalizeVerdictRecord = (verdict = {}) => ({
  createdAt: verdict.createdAt ?? verdict.CreatedAt ?? '',
  evidence: verdict.evidence ?? verdict.Evidence ?? [],
  id: verdict.id ?? verdict.Id ?? '',
  juror: verdict.juror ?? verdict.Juror ?? '',
  reason: verdict.reason ?? verdict.Reason ?? '',
  verdict: verdict.verdict ?? verdict.Verdict ?? 'NeedsManualReview',
});

const normalizeRouteAttempt = (attempt = {}) => ({
  channelId: attempt.channelId ?? attempt.ChannelId ?? '',
  createdAt: attempt.createdAt ?? attempt.CreatedAt ?? '',
  errorMessage: attempt.errorMessage ?? attempt.ErrorMessage ?? '',
  failedJurors: attempt.failedJurors ?? attempt.FailedJurors ?? [],
  id: attempt.id ?? attempt.Id ?? '',
  podId: attempt.podId ?? attempt.PodId ?? '',
  routedJurors: attempt.routedJurors ?? attempt.RoutedJurors ?? [],
  success: attempt.success ?? attempt.Success ?? false,
  targetJurors: attempt.targetJurors ?? attempt.TargetJurors ?? [],
});

const normalizeAcceptance = (acceptance = {}) => ({
  acceptedBy: acceptance.acceptedBy ?? acceptance.AcceptedBy ?? '',
  createdAt: acceptance.createdAt ?? acceptance.CreatedAt ?? '',
  id: acceptance.id ?? acceptance.Id ?? '',
  note: acceptance.note ?? acceptance.Note ?? '',
});

const normalizeReview = (review = {}) => ({
  acceptance: review.acceptance ?? review.Acceptance ?? null,
  acceptanceReason: review.acceptanceReason ?? review.AcceptanceReason ?? '',
  aggregate: normalizeAggregate(review.aggregate ?? review.Aggregate),
  canAcceptReleaseCandidate:
    review.canAcceptReleaseCandidate ??
    review.CanAcceptReleaseCandidate ??
    false,
  request: normalizeRequest(review.request ?? review.Request),
  routeAttempts: asArray(review.routeAttempts ?? review.RouteAttempts)
    .map(normalizeRouteAttempt),
  verdicts: asArray(review.verdicts ?? review.Verdicts)
    .map(normalizeVerdictRecord),
});

const formatDate = (value) => {
  if (!value) return '-';
  return new Date(value).toLocaleString(getRegionalLocale());
};

const getVerdictCount = (counts = {}, key, numericKey) =>
  counts[key] ?? counts[numericKey] ?? counts[String(numericKey)] ?? 0;

const parseJurors = (value = '') =>
  value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);

const EvidenceTable = ({ evidence = [] }) => (
  <Table
    compact
    size="small"
  >
    <Table.Header>
      <Table.Row>
        <Table.HeaderCell><LocalizedText source={"Type"} /></Table.HeaderCell>
        <Table.HeaderCell><LocalizedText source={"Reference"} /></Table.HeaderCell>
        <Table.HeaderCell><LocalizedText source={"Summary"} /></Table.HeaderCell>
      </Table.Row>
    </Table.Header>
    <Table.Body>
      {evidence.length === 0 ? (
        <Table.Row>
          <Table.Cell colSpan={3}><LocalizedText source={"No evidence supplied."} /></Table.Cell>
        </Table.Row>
      ) : (
        evidence.map((item, index) => {
          const normalized = normalizeEvidence(item);
          return (
            <Table.Row key={`${normalized.type}-${normalized.reference}-${index}`}>
              <Table.Cell>{normalized.type}</Table.Cell>
              <Table.Cell>{normalized.reference || '-'}</Table.Cell>
              <Table.Cell>{normalized.summary || '-'}</Table.Cell>
            </Table.Row>
          );
        })
      )}
    </Table.Body>
  </Table>
);

const QuarantineJury = () => {
  useInterfaceLanguage();
  const [requests, setRequests] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [review, setReview] = useState(null);
  const [loadingRequests, setLoadingRequests] = useState(true);
  const [loadingReview, setLoadingReview] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [routeForm, setRouteForm] = useState({
    channelId: '',
    podId: 'quarantine-jury',
    senderPeerId: 'local-quarantine-jury',
    targetJurors: '',
  });
  const [acceptForm, setAcceptForm] = useState({
    acceptedBy: 'local-user',
    note: '',
  });
  const [acceptOpen, setAcceptOpen] = useState(false);
  const [message, setMessage] = useState('');

  const normalizedRequests = useMemo(
    () => requests.map(normalizeRequest),
    [requests],
  );
  const selectedRequest = normalizedRequests.find(
    (request) => request.id === selectedId,
  );

  const loadReview = async (requestId) => {
    if (!requestId) return;
    setLoadingReview(true);
    setError('');

    try {
      const nextReview = normalizeReview(
        await quarantineJuryApi.getReview(requestId),
      );
      setReview(nextReview);
      setRouteForm((current) => ({
        ...current,
        targetJurors: nextReview.request.jurors.join(', '),
      }));
    } catch (loadError) {
      setReview(null);
      setError(
        loadError?.response?.data ||
          loadError?.response?.statusText ||
          loadError?.message ||
          interfaceText('Unable to load Quarantine Jury review'),
      );
    } finally {
      setLoadingReview(false);
    }
  };

  const loadRequests = async () => {
    setLoadingRequests(true);
    setError('');

    try {
      const nextRequests = await quarantineJuryApi.getRequests();
      setRequests(nextRequests);
      const normalized = nextRequests.map(normalizeRequest);
      const nextSelected =
        selectedId && normalized.some((request) => request.id === selectedId)
          ? selectedId
          : normalized[0]?.id || '';
      setSelectedId(nextSelected);
      if (nextSelected) {
        await loadReview(nextSelected);
      } else {
        setReview(null);
      }
    } catch (loadError) {
      setError(
        loadError?.response?.data ||
          loadError?.response?.statusText ||
          loadError?.message ||
          interfaceText('Unable to load Quarantine Jury requests'),
      );
    } finally {
      setLoadingRequests(false);
    }
  };

  useEffect(() => {
    loadRequests();
  }, []);

  const selectRequest = (requestId) => {
    setSelectedId(requestId);
    setMessage('');
    loadReview(requestId);
  };

  const submitRoute = async () => {
    if (!selectedId) return;
    setSaving(true);
    setError('');

    try {
      await quarantineJuryApi.routeRequest(selectedId, {
        channelId: routeForm.channelId,
        podId: routeForm.podId,
        senderPeerId: routeForm.senderPeerId,
        targetJurors: parseJurors(routeForm.targetJurors),
      });
      setMessage(interfaceText("Quarantine Jury route attempt recorded."));
      await loadReview(selectedId);
    } catch (routeError) {
      setError(
        routeError?.response?.data?.errorMessage ||
          routeError?.response?.data ||
          routeError?.message ||
          interfaceText('Unable to route Quarantine Jury request'),
      );
    } finally {
      setSaving(false);
    }
  };

  const submitAccept = async () => {
    if (!selectedId) return;
    setSaving(true);
    setError('');

    try {
      await quarantineJuryApi.acceptReleaseCandidate(selectedId, acceptForm);
      setMessage(interfaceText("Release-candidate recommendation accepted for this review."));
      setAcceptOpen(false);
      await loadReview(selectedId);
    } catch (acceptError) {
      const errors = acceptError?.response?.data?.errors;
      setError(
        Array.isArray(errors)
          ? errors.join(' ')
          : acceptError?.response?.data ||
              acceptError?.message ||
              interfaceText('Unable to accept release-candidate recommendation'),
      );
    } finally {
      setSaving(false);
    }
  };

  const aggregate = review?.aggregate || normalizeAggregate();
  const accepted = Boolean(review?.acceptance);

  return (
    <div className="quarantine-jury">
      <Segment>
        <div className="quarantine-jury-header">
          <Header as="h3">
            <Icon name="shield" />
            <Header.Content>
              <LocalizedText source={"Quarantine Jury"} /><Header.Subheader>
                <LocalizedText source={"Review trusted juror evidence before local quarantine release decisions."} /></Header.Subheader>
            </Header.Content>
          </Header>
          <Popup
            content={interfaceText("Reload requests and the selected review without changing quarantine state.")}
            trigger={
              <Button
                aria-label={interfaceText("Refresh Quarantine Jury reviews")}
                icon="refresh"
                loading={loadingRequests}
                onClick={loadRequests}
                type="button"
               {...interfaceTextProps("Refresh Quarantine Jury reviews")}/>
            }
           {...interfaceTextProps("Reload requests and the selected review without changing quarantine state.")}/>
        </div>
        <Statistic.Group
          className="quarantine-jury-summary"
          size="small"
          widths="four"
        >
          <Statistic>
            <Statistic.Value>{normalizedRequests.length}</Statistic.Value>
            <Statistic.Label><LocalizedText source={"Requests"} /></Statistic.Label>
          </Statistic>
          {/* Nothing to review yet isn't a warning state — only color these
              once a verdict has actually been cast. */}
          <Statistic
            color={
              aggregate.totalVerdicts === 0
                ? undefined
                : aggregate.quorumReached ? 'green' : 'orange'
            }
          >
            <Statistic.Value>{aggregate.totalVerdicts}</Statistic.Value>
            <Statistic.Label><LocalizedText source={"Verdicts"} /></Statistic.Label>
          </Statistic>
          <Statistic>
            <Statistic.Value>{aggregate.requiredVotes}</Statistic.Value>
            <Statistic.Label><LocalizedText source={"Required"} /></Statistic.Label>
          </Statistic>
          <Statistic color={aggregate.totalVerdicts === 0 ? undefined : verdictColor(aggregate.recommendation)}>
            <Statistic.Value>
              {aggregate.totalVerdicts === 0 ? <LocalizedText source={"No verdicts yet"} /> : normalizeVerdict(aggregate.recommendation)}
            </Statistic.Value>
            <Statistic.Label><LocalizedText source={"Recommendation"} /></Statistic.Label>
          </Statistic>
        </Statistic.Group>
      </Segment>

      {error && (
        <Message
          error
          header={interfaceText("Quarantine Jury action failed")}
          content={String(error)}
         {...interfaceTextProps("Quarantine Jury action failed")}/>
      )}
      {message && (
        <Message
          info
          header={interfaceText("Quarantine Jury updated")}
          content={message}
         {...interfaceTextProps("Quarantine Jury updated")}/>
      )}

      <div className="quarantine-jury-layout">
        <Segment className="quarantine-jury-list">
          <Header as="h4"><LocalizedText source={"Requests"} /></Header>
          {loadingRequests ? (
            <Loader active inline="centered" />
          ) : normalizedRequests.length === 0 ? (
            <Message
              info
              content={interfaceText("No Quarantine Jury requests are available.")}
             {...interfaceTextProps("No Quarantine Jury requests are available.")}/>
          ) : (
            <Card.Group itemsPerRow={1}>
              {normalizedRequests.map((request) => (
                <Card
                  className={
                    request.id === selectedId
                      ? 'quarantine-jury-request active'
                      : 'quarantine-jury-request'
                  }
                  key={request.id}
                  onClick={() => selectRequest(request.id)}
                >
                  <Card.Content>
                    <Card.Header>{request.id}</Card.Header>
                    <Card.Meta>{formatDate(request.createdAt)}</Card.Meta>
                    <Card.Description>{request.localReason || '-'}</Card.Description>
                  </Card.Content>
                  <Card.Content extra>
                    <Label basic>
                      <Icon name="users" />
                      {request.jurors.length} <LocalizedText source={"jurors"} /></Label>
                    <Label basic>
                      <Icon name="check" />
                      {request.minJurorVotes} <LocalizedText source={"votes"} /></Label>
                  </Card.Content>
                </Card>
              ))}
            </Card.Group>
          )}
        </Segment>

        <Segment className="quarantine-jury-detail">
          {loadingReview ? (
            <Loader active inline="centered" />
          ) : !review ? (
            <Message
              info
              content={interfaceText("Select a request to inspect jury evidence.")}
             {...interfaceTextProps("Select a request to inspect jury evidence.")}/>
          ) : (
            <>
              <div className="quarantine-jury-detail-head">
                <Header as="h4">
                  <Icon name="file alternate outline" />
                  <Header.Content>
                    <LocalizedText source={"Review"} />{" "}{selectedRequest?.id}
                    <Header.Subheader>
                      {review.acceptanceReason || aggregate.reason}
                    </Header.Subheader>
                  </Header.Content>
                </Header>
                <Label color={verdictColor(aggregate.recommendation)}>
                  {normalizeVerdict(aggregate.recommendation)}
                </Label>
              </div>

              <Label.Group>
                <Label color={aggregate.quorumReached ? 'green' : 'orange'}>
                  {aggregate.quorumReached ? <LocalizedText source={"Quorum Reached"} /> : <LocalizedText source={"Awaiting Quorum"} />}
                </Label>
                <Label basic>
                  <LocalizedText source={"Release"} />{" "}{getVerdictCount(aggregate.verdictCounts, 'ReleaseCandidate', 2)}
                </Label>
                <Label basic>
                  <LocalizedText source={"Uphold"} />{" "}{getVerdictCount(aggregate.verdictCounts, 'UpholdQuarantine', 1)}
                </Label>
                <Label basic>
                  <LocalizedText source={"Manual"} />{" "}{getVerdictCount(aggregate.verdictCounts, 'NeedsManualReview', 0)}
                </Label>
              </Label.Group>

              <Header as="h5"><LocalizedText source={"Request Evidence"} /></Header>
              <EvidenceTable evidence={review.request.evidence} />

              <Header as="h5"><LocalizedText source={"Juror Verdicts"} /></Header>
              <Table
                compact
                size="small"
              >
                <Table.Header>
                  <Table.Row>
                    <Table.HeaderCell><LocalizedText source={"Juror"} /></Table.HeaderCell>
                    <Table.HeaderCell><LocalizedText source={"Verdict"} /></Table.HeaderCell>
                    <Table.HeaderCell><LocalizedText source={"Reason"} /></Table.HeaderCell>
                    <Table.HeaderCell><LocalizedText source={"Evidence"} /></Table.HeaderCell>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  {review.verdicts.length === 0 ? (
                    <Table.Row>
                      <Table.Cell colSpan={4}><LocalizedText source={"No juror verdicts yet."} /></Table.Cell>
                    </Table.Row>
                  ) : (
                    review.verdicts.map((verdict) => (
                      <Table.Row key={verdict.id}>
                        <Table.Cell>{verdict.juror || '-'}</Table.Cell>
                        <Table.Cell>
                          <Label color={verdictColor(verdict.verdict)}>
                            {normalizeVerdict(verdict.verdict)}
                          </Label>
                        </Table.Cell>
                        <Table.Cell>{verdict.reason || '-'}</Table.Cell>
                        <Table.Cell>{verdict.evidence.length}</Table.Cell>
                      </Table.Row>
                    ))
                  )}
                </Table.Body>
              </Table>

              {aggregate.dissentingJurors.length > 0 && (
                <Message
                  warning
                  header={interfaceText("Dissenting jurors")}
                  content={aggregate.dissentingJurors.join(', ')}
                 {...interfaceTextProps("Dissenting jurors")}/>
              )}

              <Header as="h5"><LocalizedText source={"Route Attempts"} /></Header>
              <Table
                compact
                size="small"
              >
                <Table.Header>
                  <Table.Row>
                    <Table.HeaderCell><LocalizedText source={"Created"} /></Table.HeaderCell>
                    <Table.HeaderCell><LocalizedText source={"Pod / Channel"} /></Table.HeaderCell>
                    <Table.HeaderCell><LocalizedText source={"Routed"} /></Table.HeaderCell>
                    <Table.HeaderCell><LocalizedText source={"Failed"} /></Table.HeaderCell>
                    <Table.HeaderCell><LocalizedText source={"Status"} /></Table.HeaderCell>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  {review.routeAttempts.length === 0 ? (
                    <Table.Row>
                      <Table.Cell colSpan={5}><LocalizedText source={"No route attempts recorded."} /></Table.Cell>
                    </Table.Row>
                  ) : (
                    review.routeAttempts.map((attempt) => (
                      <Table.Row key={attempt.id}>
                        <Table.Cell>{formatDate(attempt.createdAt)}</Table.Cell>
                        <Table.Cell>
                          {attempt.podId || '-'} / {attempt.channelId || '-'}
                        </Table.Cell>
                        <Table.Cell>{valueOrDash(attempt.routedJurors)}</Table.Cell>
                        <Table.Cell>{valueOrDash(attempt.failedJurors)}</Table.Cell>
                        <Table.Cell>
                          <Label color={attempt.success ? 'green' : 'red'}>
                            {attempt.success ? <LocalizedText source={"Routed"} /> : <RouteAttemptError message={attempt.errorMessage} />}
                          </Label>
                        </Table.Cell>
                      </Table.Row>
                    ))
                  )}
                </Table.Body>
              </Table>

              <Segment>
                <Header as="h5"><LocalizedText source={"Manual Route Dispatch"} /></Header>
                <Form>
                  <Form.Group widths="equal">
                    <Form.Input
                      label={interfaceText("Sender Peer ID")}
                      onChange={(_event, { value }) =>
                        setRouteForm((current) => ({
                          ...current,
                          senderPeerId: value,
                        }))
                      }
                      value={routeForm.senderPeerId}
                     {...interfaceTextProps("Sender Peer ID")}/>
                    <Form.Input
                      label={interfaceText("Pod ID")}
                      onChange={(_event, { value }) =>
                        setRouteForm((current) => ({
                          ...current,
                          podId: value,
                        }))
                      }
                      value={routeForm.podId}
                     {...interfaceTextProps("Pod ID")}/>
                    <Form.Input
                      label={interfaceText("Channel ID")}
                      onChange={(_event, { value }) =>
                        setRouteForm((current) => ({
                          ...current,
                          channelId: value,
                        }))
                      }
                      value={routeForm.channelId}
                     {...interfaceTextProps("Channel ID")}/>
                  </Form.Group>
                  <Form.Input
                    label={interfaceText("Target Jurors")}
                    onChange={(_event, { value }) =>
                      setRouteForm((current) => ({
                        ...current,
                        targetJurors: value,
                      }))
                    }
                    value={routeForm.targetJurors}
                   {...interfaceTextProps("Target Jurors")}/>
                  <Popup
                    content={interfaceText("Route this request only to the explicit target jurors listed here. Raw files are not attached.")}
                    trigger={
                      <Button
                        disabled={saving}
                        icon
                        labelPosition="left"
                        loading={saving}
                        onClick={submitRoute}
                        type="button"
                      >
                        <Icon name="paper plane" />
                        <LocalizedText source={"Route to Jurors"} /></Button>
                    }
                   {...interfaceTextProps("Route this request only to the explicit target jurors listed here. Raw files are not attached.")}/>
                </Form>
              </Segment>

              <Segment>
                <Header as="h5"><LocalizedText source={"Acceptance"} /></Header>
                {accepted ? (
                  <Message
                    positive
                    header={interfaceText("Release candidate accepted")}
                    content={interfaceText('{acceptedBy} accepted this recommendation at {time}.', {
                      acceptedBy: normalizeAcceptance(review.acceptance).acceptedBy,
                      time: formatDate(normalizeAcceptance(review.acceptance).createdAt),
                    })}
                   {...interfaceTextProps("Release candidate accepted")}/>
                ) : (
                  <>
                    <Message
                      info
                      content={review.acceptanceReason}
                    />
                    <Popup
                      content={interfaceText("Open the confirmation dialog. Accepting records a local decision only when the aggregate recommends Release Candidate.")}
                      trigger={
                        <Button
                          color="green"
                          disabled={!review.canAcceptReleaseCandidate || saving}
                          icon
                          labelPosition="left"
                          onClick={() => setAcceptOpen(true)}
                          type="button"
                        >
                          <Icon name="check circle" />
                          <LocalizedText source={"Accept Release Candidate"} /></Button>
                      }
                     {...interfaceTextProps("Open the confirmation dialog. Accepting records a local decision only when the aggregate recommends Release Candidate.")}/>
                  </>
                )}
              </Segment>
            </>
          )}
        </Segment>
      </div>

      <Modal
        onClose={() => setAcceptOpen(false)}
        open={acceptOpen}
        size="small"
      >
        <Modal.Header><LocalizedText source={"Accept Release Candidate"} /></Modal.Header>
        <Modal.Content>
          <Message
            warning
            content={interfaceText("This records a local acceptance decision for the jury recommendation. It does not automatically move files or broadcast a release.")}
           {...interfaceTextProps("This records a local acceptance decision for the jury recommendation. It does not automatically move files or broadcast a release.")}/>
          <Form>
            <Form.Input
              label={interfaceText("Accepted By")}
              onChange={(_event, { value }) =>
                setAcceptForm((current) => ({
                  ...current,
                  acceptedBy: value,
                }))
              }
              value={acceptForm.acceptedBy}
             {...interfaceTextProps("Accepted By")}/>
            <Form.TextArea
              label={interfaceText("Review Note")}
              onChange={(_event, { value }) =>
                setAcceptForm((current) => ({
                  ...current,
                  note: value,
                }))
              }
              value={acceptForm.note}
             {...interfaceTextProps("Review Note")}/>
          </Form>
        </Modal.Content>
        <Modal.Actions>
          <Popup
            content={interfaceText("Close without recording an acceptance decision.")}
            trigger={
              <Button
                disabled={saving}
                onClick={() => setAcceptOpen(false)}
                type="button"
              >
                <LocalizedText source={"Cancel"} /></Button>
            }
           {...interfaceTextProps("Close without recording an acceptance decision.")}/>
          <Popup
            content={interfaceText("Record the local acceptance decision for this release-candidate recommendation.")}
            trigger={
              <Button
                color="green"
                disabled={saving}
                loading={saving}
                onClick={submitAccept}
                type="button"
              >
                <LocalizedText source={"Accept Recommendation"} /></Button>
            }
           {...interfaceTextProps("Record the local acceptance decision for this release-candidate recommendation.")}/>
        </Modal.Actions>
      </Modal>
    </div>
  );
};

export default QuarantineJury;
