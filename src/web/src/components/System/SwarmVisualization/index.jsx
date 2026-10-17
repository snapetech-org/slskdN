import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
// <copyright file="index.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import * as jobsLibrary from '../../../lib/jobs';
import { formatBytes } from '../../../lib/util';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Grid,
  Header,
  Icon,
  Label,
  Loader,
  Progress,
  Segment,
  Statistic,
  Table,
} from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);
const asObject = (value) =>
  value && typeof value === 'object' && !Array.isArray(value) ? value : {};
const STATUS_POLL_INTERVAL_MS = 2_000;
const TRACE_POLL_INTERVAL_MS = 10_000;

const sameJobStatus = (previous, next) =>
  previous?.activeWorkers === next?.activeWorkers &&
  previous?.bytesDownloaded === next?.bytesDownloaded &&
  previous?.chunksPerSecond === next?.chunksPerSecond &&
  previous?.completedChunks === next?.completedChunks &&
  previous?.estimatedSecondsRemaining === next?.estimatedSecondsRemaining &&
  previous?.jobId === next?.jobId &&
  previous?.state === next?.state &&
  previous?.totalChunks === next?.totalChunks;

const sameRecord = (previous, next) => {
  const previousEntries = Object.entries(asObject(previous));
  const nextObject = asObject(next);
  return (
    previousEntries.length === Object.keys(nextObject).length &&
    previousEntries.every(([key, value]) => value === nextObject[key])
  );
};

const sameTraceSummary = (previous, next) => {
  const previousPeers = asArray(previous?.peers);
  const nextPeers = asArray(next?.peers);
  return (
    previous?.totalEvents === next?.totalEvents &&
    previous?.duration === next?.duration &&
    previous?.rescueInvoked === next?.rescueInvoked &&
    sameRecord(previous?.bytesBySource, next?.bytesBySource) &&
    previousPeers.length === nextPeers.length &&
    previousPeers.every(
      (peer, index) =>
        peer.peerId === nextPeers[index]?.peerId &&
        peer.bytesServed === nextPeers[index]?.bytesServed &&
        peer.chunksCompleted === nextPeers[index]?.chunksCompleted &&
        peer.chunksFailed === nextPeers[index]?.chunksFailed &&
        peer.chunksTimedOut === nextPeers[index]?.chunksTimedOut,
    )
  );
};

const SwarmVisualization = ({ jobId }) => {
  const activeJobIdRef = useRef(jobId);
  const mountedRef = useRef(false);
  const statusInFlightRef = useRef(false);
  const statusIntervalRef = useRef(null);
  const statusRequestGenerationRef = useRef(0);
  const traceInFlightRef = useRef(false);
  const traceIntervalRef = useRef(null);
  const traceRequestGenerationRef = useRef(0);
  const [jobStatus, setJobStatus] = useState(null);
  const [traceSummary, setTraceSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const fetchStatus = useCallback(async () => {
    if (
      !mountedRef.current ||
      document.hidden ||
      !jobId ||
      statusInFlightRef.current
    ) {
      return;
    }

    statusInFlightRef.current = true;
    const requestGeneration = statusRequestGenerationRef.current;
    const requestJobId = jobId;
    try {
      const status = await jobsLibrary.getSwarmJobStatus(requestJobId);

      if (!mountedRef.current) return;
      if (document.hidden) return;
      if (
        activeJobIdRef.current !== requestJobId ||
        statusRequestGenerationRef.current !== requestGeneration
      ) {
        return;
      }

      setJobStatus((previous) =>
        sameJobStatus(previous, status) ? previous : status,
      );
      setError(null);
    } catch (error_) {
      if (!mountedRef.current) return;
      if (document.hidden) return;
      if (
        activeJobIdRef.current !== requestJobId ||
        statusRequestGenerationRef.current !== requestGeneration
      ) {
        return;
      }
      setError(getApiErrorMessage(error_, { t: interfaceText }, 'Failed to fetch swarm data'));
      console.error('Failed to fetch swarm visualization data:', error_);
    } finally {
      if (statusRequestGenerationRef.current === requestGeneration) {
        statusInFlightRef.current = false;
      }
      if (
        mountedRef.current &&
        statusRequestGenerationRef.current === requestGeneration
      ) {
        setLoading(false);
      }
    }
  }, [jobId]);

  const fetchTrace = useCallback(async () => {
    if (
      !mountedRef.current ||
      document.hidden ||
      !jobId ||
      traceInFlightRef.current
    ) {
      return;
    }

    traceInFlightRef.current = true;
    const requestGeneration = traceRequestGenerationRef.current;
    const requestJobId = jobId;
    try {
      const summary = await jobsLibrary.getSwarmTraceSummary(requestJobId);

      if (!mountedRef.current) return;
      if (document.hidden || !summary) return;
      if (
        activeJobIdRef.current !== requestJobId ||
        traceRequestGenerationRef.current !== requestGeneration
      ) {
        return;
      }

      setTraceSummary((previous) =>
        sameTraceSummary(previous, summary) ? previous : summary,
      );
    } catch (error_) {
      if (!mountedRef.current) return;
      if (document.hidden) return;
      if (
        activeJobIdRef.current !== requestJobId ||
        traceRequestGenerationRef.current !== requestGeneration
      ) {
        return;
      }
      console.debug('Failed to fetch swarm trace summary:', error_);
    } finally {
      if (traceRequestGenerationRef.current === requestGeneration) {
        traceInFlightRef.current = false;
      }
    }
  }, [jobId]);

  useEffect(() => {
    activeJobIdRef.current = jobId;
    statusRequestGenerationRef.current += 1;
    traceRequestGenerationRef.current += 1;
    statusInFlightRef.current = false;
    traceInFlightRef.current = false;
    setError(null);
    setJobStatus(null);
    setLoading(Boolean(jobId));
    setTraceSummary(null);

    if (!jobId) {
      return undefined;
    }

    const stopPolling = () => {
      if (statusIntervalRef.current) {
        window.clearInterval(statusIntervalRef.current);
        statusIntervalRef.current = null;
      }

      if (traceIntervalRef.current) {
        window.clearInterval(traceIntervalRef.current);
        traceIntervalRef.current = null;
      }
    };
    const startPolling = () => {
      if (document.hidden || statusIntervalRef.current) return;

      fetchStatus();
      fetchTrace();
      statusIntervalRef.current = window.setInterval(
        fetchStatus,
        STATUS_POLL_INTERVAL_MS,
      );
      traceIntervalRef.current = window.setInterval(
        fetchTrace,
        TRACE_POLL_INTERVAL_MS,
      );
    };
    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopPolling();
      } else {
        startPolling();
      }
    };

    startPolling();
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      stopPolling();
    };
  }, [fetchStatus, fetchTrace, jobId]);

  const peerContributions = useMemo(() => {
    const peers = asArray(traceSummary?.peers);
    if (peers.length > 0) {
      return peers.map((peer) => ({
        bytesServed: peer.bytesServed || 0,
        chunksCompleted: peer.chunksCompleted || 0,
        chunksFailed: peer.chunksFailed || 0,
        chunksTimedOut: peer.chunksTimedOut || 0,
        peerId: peer.peerId,
        successRate:
          peer.chunksCompleted + peer.chunksFailed + peer.chunksTimedOut > 0
            ? (peer.chunksCompleted /
                (peer.chunksCompleted +
                  peer.chunksFailed +
                  peer.chunksTimedOut)) *
              100
            : 0,
      }));
    }

    return [];
  }, [traceSummary]);

  const chunkHeatmap = useMemo(() => {
    if (!jobStatus || !traceSummary) return null;

    const totalChunks = jobStatus.totalChunks || 0;
    const completedChunks = jobStatus.completedChunks || 0;
    const chunksPerRow = Math.ceil(Math.sqrt(totalChunks)) || 20;

    // Create a simple grid representation
    const rows = [];
    for (let index = 0; index < totalChunks; index += chunksPerRow) {
      const rowChunks = [];
      for (
        let index_ = 0;
        index_ < chunksPerRow && index + index_ < totalChunks;
        index_++
      ) {
        const chunkIndex = index + index_;
        const isCompleted = chunkIndex < completedChunks;
        rowChunks.push({
          completed: isCompleted,
          index: chunkIndex,
        });
      }

      rows.push(rowChunks);
    }

    return { chunksPerRow, rows };
  }, [jobStatus, traceSummary]);

  if (loading && !jobStatus) {
    return (
      <Segment>
        <Loader
          active
          inline="centered"
        />
      </Segment>
    );
  }

  if (error && !jobStatus) {
    return (
      <Segment>
        <Header
          as="h4"
          color="red"
        >
          <Icon name="exclamation triangle" />
          <Header.Content><LocalizedText source={"Error Loading Swarm Data"} /></Header.Content>
        </Header>
        <p>{error}</p>
      </Segment>
    );
  }

  if (!jobStatus) {
    return (
      <Segment placeholder>
        <Header icon>
          <Icon name="info circle" />
          <LocalizedText source={"No swarm job selected"} /></Header>
        <p><LocalizedText source={"Select a swarm download job to view visualization"} /></p>
      </Segment>
    );
  }

  const percentComplete =
    jobStatus.totalChunks > 0
      ? (jobStatus.completedChunks / jobStatus.totalChunks) * 100
      : 0;

  return (
    <div>
      {/* Job Overview */}
      <Segment>
        <Header as="h3">
          <Icon name="bolt" />
          <Header.Content><LocalizedText source={"Swarm Download Status"} /></Header.Content>
        </Header>
        <Grid columns={4}>
          <Grid.Column>
            <Statistic>
              <Statistic.Value>
                {jobStatus.completedChunks || 0} / {jobStatus.totalChunks || 0}
              </Statistic.Value>
              <Statistic.Label><LocalizedText source={"Chunks"} /></Statistic.Label>
            </Statistic>
          </Grid.Column>
          <Grid.Column>
            <Statistic>
              <Statistic.Value>{jobStatus.activeWorkers || 0}</Statistic.Value>
              <Statistic.Label><LocalizedText source={"Active Workers"} /></Statistic.Label>
            </Statistic>
          </Grid.Column>
          <Grid.Column>
            <Statistic>
              <Statistic.Value>
                {jobStatus.chunksPerSecond
                  ? jobStatus.chunksPerSecond.toFixed(1)
                  : '0.0'}
              </Statistic.Value>
              <Statistic.Label><LocalizedText source={"Chunks per second"} /></Statistic.Label>
            </Statistic>
          </Grid.Column>
          <Grid.Column>
            <Statistic>
              <Statistic.Value>
                {jobStatus.estimatedSecondsRemaining > 0
                  ? `${Math.round(jobStatus.estimatedSecondsRemaining)}s`
                  : interfaceText('N/A')}
              </Statistic.Value>
              <Statistic.Label><LocalizedText source={"ETA"} /></Statistic.Label>
            </Statistic>
          </Grid.Column>
        </Grid>
        <Progress
          active
          color="blue"
          percent={percentComplete}
          progress
          size="large"
          style={{ marginTop: '1em' }}
        />
        <div style={{ fontSize: '0.9em', marginTop: '0.5em' }}>
          {formatBytes(jobStatus.bytesDownloaded || 0)} /{' '}
          {formatBytes((jobStatus.totalChunks || 0) * 512 * 1_024)}
        </div>
      </Segment>

      {/* Peer Contributions */}
      {peerContributions.length > 0 && (
        <Segment>
          <Header as="h3">
            <Icon name="users" />
            <Header.Content><LocalizedText source={"Peer Contributions"} /></Header.Content>
          </Header>
          <Table celled>
            <Table.Header>
              <Table.Row>
                <Table.HeaderCell><LocalizedText source={"Peer"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Chunks Completed"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Chunks Failed"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Bytes Served"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Success Rate"} /></Table.HeaderCell>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {peerContributions.map((peer) => (
                <Table.Row key={peer.peerId}>
                  <Table.Cell>
                    <Icon name="user" />
                    {peer.peerId}
                  </Table.Cell>
                  <Table.Cell>
                    <Label color="green">{peer.chunksCompleted}</Label>
                  </Table.Cell>
                  <Table.Cell>
                    {peer.chunksFailed > 0 && (
                      <Label color="red">{peer.chunksFailed}</Label>
                    )}
                    {peer.chunksFailed === 0 && '-'}
                  </Table.Cell>
                  <Table.Cell>{formatBytes(peer.bytesServed)}</Table.Cell>
                  <Table.Cell>
                    <Progress
                      color={
                        peer.successRate >= 80
                          ? 'green'
                          : peer.successRate >= 50
                            ? 'yellow'
                            : 'red'
                      }
                      percent={peer.successRate}
                      progress
                      size="small"
                    />
                    <span style={{ fontSize: '0.9em', marginLeft: '0.5em' }}>
                      {peer.successRate.toFixed(1)}%
                    </span>
                  </Table.Cell>
                </Table.Row>
              ))}
            </Table.Body>
          </Table>
        </Segment>
      )}

      {/* Chunk Assignment Heatmap */}
      {chunkHeatmap && (
        <Segment>
          <Header as="h3">
            <Icon name="grid layout" />
            <Header.Content><LocalizedText source={"Chunk Progress Heatmap"} /></Header.Content>
            <Header.Subheader>
              <LocalizedText source={"Visual representation of chunk completion status"} /></Header.Subheader>
          </Header>
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '2px',
              maxHeight: '400px',
              overflow: 'auto',
            }}
          >
            {chunkHeatmap.rows.map((row, rowIndex) => (
              <div
                key={rowIndex}
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '2px',
                }}
              >
                {row.map((chunk) => (
                  <div
                    key={chunk.index}
                    style={{
                      backgroundColor: chunk.completed ? '#21ba45' : '#767676',
                      borderRadius: '2px',
                      cursor: 'pointer',
                      height: '12px',
                      title: interfaceText('Chunk {index}: {status}', {
                        index: chunk.index + 1,
                        status: interfaceText(chunk.completed ? 'Completed' : 'Pending'),
                      }),
                      width: '12px',
                    }}
                  />
                ))}
              </div>
            ))}
          </div>
          <div
            style={{
              display: 'flex',
              fontSize: '0.9em',
              gap: '1em',
              marginTop: '0.5em',
            }}
          >
            <div>
              <span
                style={{
                  backgroundColor: '#21ba45',
                  borderRadius: '2px',
                  display: 'inline-block',
                  height: '12px',
                  marginRight: '0.25em',
                  width: '12px',
                }}
              />
              <LocalizedText source={"Completed"} /></div>
            <div>
              <span
                style={{
                  backgroundColor: '#767676',
                  borderRadius: '2px',
                  display: 'inline-block',
                  height: '12px',
                  marginRight: '0.25em',
                  width: '12px',
                }}
              />
              <LocalizedText source={"Pending"} /></div>
          </div>
        </Segment>
      )}

      {/* Performance Metrics */}
      {traceSummary && (
        <Segment>
          <Header as="h3">
            <Icon name="chart line" />
            <Header.Content><LocalizedText source={"Performance Metrics"} /></Header.Content>
          </Header>
          <Grid columns={3}>
            <Grid.Column>
              <Statistic>
                <Statistic.Value>
                  {traceSummary.totalEvents || 0}
                </Statistic.Value>
                <Statistic.Label><LocalizedText source={"Total Events"} /></Statistic.Label>
              </Statistic>
            </Grid.Column>
            <Grid.Column>
              <Statistic>
                <Statistic.Value>
                  {traceSummary.duration
                    ? (() => {
                        // TimeSpan serializes as string (e.g., "00:01:23") or object with properties
                        if (typeof traceSummary.duration === 'string') {
                          // Parse "HH:MM:SS" format
                          const parts = traceSummary.duration.split(':');
                          if (parts.length === 3) {
                            const totalSeconds =
                              Number.parseInt(parts[0], 10) * 3_600 +
                              Number.parseInt(parts[1], 10) * 60 +
                              Number.parseInt(parts[2], 10);
                            return `${totalSeconds}s`;
                          }
                        } else if (
                          typeof traceSummary.duration === 'object' &&
                          traceSummary.duration
                        ) {
                          const dur = traceSummary.duration;
                          if (dur.totalSeconds !== undefined) {
                            return `${Math.round(dur.totalSeconds)}s`;
                          }

                          if (dur.seconds !== undefined) {
                            return `${Math.round(dur.seconds)}s`;
                          }
                        }

                        return interfaceText('N/A');
                      })()
                    : interfaceText('N/A')}
                </Statistic.Value>
                <Statistic.Label><LocalizedText source={"Duration"} /></Statistic.Label>
              </Statistic>
            </Grid.Column>
            <Grid.Column>
              <Statistic>
                <Statistic.Value>
                  {traceSummary.rescueInvoked ? (
                    <Icon
                      color="orange"
                      name="exclamation triangle"
                    />
                  ) : (
                    <Icon
                      color="green"
                      name="check circle"
                    />
                  )}
                </Statistic.Value>
                <Statistic.Label>
                  {traceSummary.rescueInvoked ? <LocalizedText source={"Rescue Invoked"} /> : <LocalizedText source={"Normal"} />}
                </Statistic.Label>
              </Statistic>
            </Grid.Column>
          </Grid>
          {Object.keys(asObject(traceSummary.bytesBySource)).length > 0 && (
              <div style={{ marginTop: '1em' }}>
                <Header
                  as="h4"
                  size="small"
                >
                  <LocalizedText source={"Bytes by Source"} /></Header>
                <Table size="small">
                  <Table.Body>
                    {Object.entries(asObject(traceSummary.bytesBySource))
                      .sort((a, b) => b[1] - a[1])
                      .map(([source, bytes]) => (
                        <Table.Row key={source}>
                          <Table.Cell>{source}</Table.Cell>
                          <Table.Cell>{formatBytes(bytes)}</Table.Cell>
                        </Table.Row>
                      ))}
                  </Table.Body>
                </Table>
              </div>
            )}
        </Segment>
      )}

      {!traceSummary && (
        <Segment>
          <Header
            as="h4"
            color="grey"
            size="small"
          >
            <Icon name="info circle" />
            <Header.Content><LocalizedText source={"Trace Data Not Available"} /></Header.Content>
          </Header>
          <p>
            <LocalizedText source={"Detailed peer contribution and performance metrics require trace data. This may not be available for all swarm downloads."} /></p>
        </Segment>
      )}
    </div>
  );
};

export default SwarmVisualization;
