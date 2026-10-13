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
  verdictNames[verdict] || String(verdict || 'Needs Manual Review');

const valueOrDash = (value) => {
  if (Array.isArray(value)) return value.length > 0 ? value.join(', ') : '-';
  return value || '-';
};

const asArray = (value) => (Array.isArray(value) ? value : []);

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
        <Table.HeaderCell>Type</Table.HeaderCell>
        <Table.HeaderCell>Reference</Table.HeaderCell>
        <Table.HeaderCell>Summary</Table.HeaderCell>
      </Table.Row>
    </Table.Header>
    <Table.Body>
      {evidence.length === 0 ? (
        <Table.Row>
          <Table.Cell colSpan={3}>No evidence supplied.</Table.Cell>
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
          'Unable to load Quarantine Jury review',
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
          'Unable to load Quarantine Jury requests',
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
      setMessage('Quarantine Jury route attempt recorded.');
      await loadReview(selectedId);
    } catch (routeError) {
      setError(
        routeError?.response?.data?.errorMessage ||
          routeError?.response?.data ||
          routeError?.message ||
          'Unable to route Quarantine Jury request',
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
      setMessage('Release-candidate recommendation accepted for this review.');
      setAcceptOpen(false);
      await loadReview(selectedId);
    } catch (acceptError) {
      const errors = acceptError?.response?.data?.errors;
      setError(
        Array.isArray(errors)
          ? errors.join(' ')
          : acceptError?.response?.data ||
              acceptError?.message ||
              'Unable to accept release-candidate recommendation',
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
              Quarantine Jury
              <Header.Subheader>
                Review trusted juror evidence before local quarantine release decisions.
              </Header.Subheader>
            </Header.Content>
          </Header>
          <Popup
            content="Reload requests and the selected review without changing quarantine state."
            trigger={
              <Button
                aria-label="Refresh Quarantine Jury reviews"
                icon="refresh"
                loading={loadingRequests}
                onClick={loadRequests}
                type="button"
              />
            }
          />
        </div>
        <Statistic.Group
          className="quarantine-jury-summary"
          size="small"
          widths="four"
        >
          <Statistic>
            <Statistic.Value>{normalizedRequests.length}</Statistic.Value>
            <Statistic.Label>Requests</Statistic.Label>
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
            <Statistic.Label>Verdicts</Statistic.Label>
          </Statistic>
          <Statistic>
            <Statistic.Value>{aggregate.requiredVotes}</Statistic.Value>
            <Statistic.Label>Required</Statistic.Label>
          </Statistic>
          <Statistic color={aggregate.totalVerdicts === 0 ? undefined : verdictColor(aggregate.recommendation)}>
            <Statistic.Value>
              {aggregate.totalVerdicts === 0 ? 'No verdicts yet' : normalizeVerdict(aggregate.recommendation)}
            </Statistic.Value>
            <Statistic.Label>Recommendation</Statistic.Label>
          </Statistic>
        </Statistic.Group>
      </Segment>

      {error && (
        <Message
          error
          header="Quarantine Jury action failed"
          content={String(error)}
        />
      )}
      {message && (
        <Message
          info
          header="Quarantine Jury updated"
          content={message}
        />
      )}

      <div className="quarantine-jury-layout">
        <Segment className="quarantine-jury-list">
          <Header as="h4">Requests</Header>
          {loadingRequests ? (
            <Loader active inline="centered" />
          ) : normalizedRequests.length === 0 ? (
            <Message
              info
              content="No Quarantine Jury requests are available."
            />
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
                      {request.jurors.length} jurors
                    </Label>
                    <Label basic>
                      <Icon name="check" />
                      {request.minJurorVotes} votes
                    </Label>
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
              content="Select a request to inspect jury evidence."
            />
          ) : (
            <>
              <div className="quarantine-jury-detail-head">
                <Header as="h4">
                  <Icon name="file alternate outline" />
                  <Header.Content>
                    Review {selectedRequest?.id}
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
                  {aggregate.quorumReached ? 'Quorum Reached' : 'Awaiting Quorum'}
                </Label>
                <Label basic>
                  Release {getVerdictCount(aggregate.verdictCounts, 'ReleaseCandidate', 2)}
                </Label>
                <Label basic>
                  Uphold {getVerdictCount(aggregate.verdictCounts, 'UpholdQuarantine', 1)}
                </Label>
                <Label basic>
                  Manual {getVerdictCount(aggregate.verdictCounts, 'NeedsManualReview', 0)}
                </Label>
              </Label.Group>

              <Header as="h5">Request Evidence</Header>
              <EvidenceTable evidence={review.request.evidence} />

              <Header as="h5">Juror Verdicts</Header>
              <Table
                compact
                size="small"
              >
                <Table.Header>
                  <Table.Row>
                    <Table.HeaderCell>Juror</Table.HeaderCell>
                    <Table.HeaderCell>Verdict</Table.HeaderCell>
                    <Table.HeaderCell>Reason</Table.HeaderCell>
                    <Table.HeaderCell>Evidence</Table.HeaderCell>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  {review.verdicts.length === 0 ? (
                    <Table.Row>
                      <Table.Cell colSpan={4}>No juror verdicts yet.</Table.Cell>
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
                  header="Dissenting jurors"
                  content={aggregate.dissentingJurors.join(', ')}
                />
              )}

              <Header as="h5">Route Attempts</Header>
              <Table
                compact
                size="small"
              >
                <Table.Header>
                  <Table.Row>
                    <Table.HeaderCell>Created</Table.HeaderCell>
                    <Table.HeaderCell>Pod / Channel</Table.HeaderCell>
                    <Table.HeaderCell>Routed</Table.HeaderCell>
                    <Table.HeaderCell>Failed</Table.HeaderCell>
                    <Table.HeaderCell>Status</Table.HeaderCell>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  {review.routeAttempts.length === 0 ? (
                    <Table.Row>
                      <Table.Cell colSpan={5}>No route attempts recorded.</Table.Cell>
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
                            {attempt.success ? 'Routed' : attempt.errorMessage || 'Failed'}
                          </Label>
                        </Table.Cell>
                      </Table.Row>
                    ))
                  )}
                </Table.Body>
              </Table>

              <Segment>
                <Header as="h5">Manual Route Dispatch</Header>
                <Form>
                  <Form.Group widths="equal">
                    <Form.Input
                      label="Sender Peer ID"
                      onChange={(_event, { value }) =>
                        setRouteForm((current) => ({
                          ...current,
                          senderPeerId: value,
                        }))
                      }
                      value={routeForm.senderPeerId}
                    />
                    <Form.Input
                      label="Pod ID"
                      onChange={(_event, { value }) =>
                        setRouteForm((current) => ({
                          ...current,
                          podId: value,
                        }))
                      }
                      value={routeForm.podId}
                    />
                    <Form.Input
                      label="Channel ID"
                      onChange={(_event, { value }) =>
                        setRouteForm((current) => ({
                          ...current,
                          channelId: value,
                        }))
                      }
                      value={routeForm.channelId}
                    />
                  </Form.Group>
                  <Form.Input
                    label="Target Jurors"
                    onChange={(_event, { value }) =>
                      setRouteForm((current) => ({
                        ...current,
                        targetJurors: value,
                      }))
                    }
                    value={routeForm.targetJurors}
                  />
                  <Popup
                    content="Route this request only to the explicit target jurors listed here. Raw files are not attached."
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
                        Route to Jurors
                      </Button>
                    }
                  />
                </Form>
              </Segment>

              <Segment>
                <Header as="h5">Acceptance</Header>
                {accepted ? (
                  <Message
                    positive
                    header="Release candidate accepted"
                    content={`${normalizeAcceptance(review.acceptance).acceptedBy} accepted this recommendation at ${formatDate(normalizeAcceptance(review.acceptance).createdAt)}.`}
                  />
                ) : (
                  <>
                    <Message
                      info
                      content={review.acceptanceReason}
                    />
                    <Popup
                      content="Open the confirmation dialog. Accepting records a local decision only when the aggregate recommends Release Candidate."
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
                          Accept Release Candidate
                        </Button>
                      }
                    />
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
        <Modal.Header>Accept Release Candidate</Modal.Header>
        <Modal.Content>
          <Message
            warning
            content="This records a local acceptance decision for the jury recommendation. It does not automatically move files or broadcast a release."
          />
          <Form>
            <Form.Input
              label="Accepted By"
              onChange={(_event, { value }) =>
                setAcceptForm((current) => ({
                  ...current,
                  acceptedBy: value,
                }))
              }
              value={acceptForm.acceptedBy}
            />
            <Form.TextArea
              label="Review Note"
              onChange={(_event, { value }) =>
                setAcceptForm((current) => ({
                  ...current,
                  note: value,
                }))
              }
              value={acceptForm.note}
            />
          </Form>
        </Modal.Content>
        <Modal.Actions>
          <Popup
            content="Close without recording an acceptance decision."
            trigger={
              <Button
                disabled={saving}
                onClick={() => setAcceptOpen(false)}
                type="button"
              >
                Cancel
              </Button>
            }
          />
          <Popup
            content="Record the local acceptance decision for this release-candidate recommendation."
            trigger={
              <Button
                color="green"
                disabled={saving}
                loading={saving}
                onClick={submitAccept}
                type="button"
              >
                Accept Recommendation
              </Button>
            }
          />
        </Modal.Actions>
      </Modal>
    </div>
  );
};

export default QuarantineJury;
