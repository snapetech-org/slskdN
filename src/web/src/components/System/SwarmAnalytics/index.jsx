import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";


import { getRegionalLocale } from '../../../lib/regionalFormat';
// <copyright file="index.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import * as swarmAnalyticsLibrary from '../../../lib/swarmAnalytics';
import FeatureGateNotice from '../../Shared/FeatureGateNotice';
import useFeatureGates, { isFeatureEnabled } from '../../Shared/useFeatureGates';
import { formatBytes } from '../../../lib/util';
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'react-toastify';
import {
  Card,
  Dropdown,
  Grid,
  Header,
  Icon,
  Label,
  Loader,
  Message,
  Progress,
  Segment,
  Statistic,
  Table,
} from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);
const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value);
const POLL_INTERVAL_MS = 30_000;
const normalizeDashboard = (value) => {
  const dashboard = isObject(value) ? value : {};
  return {
    efficiencyMetrics: isObject(dashboard.efficiencyMetrics)
      ? dashboard.efficiencyMetrics
      : null,
    peerRankings: asArray(dashboard.peerRankings).filter(isObject),
    performanceMetrics: isObject(dashboard.performanceMetrics)
      ? dashboard.performanceMetrics
      : null,
    recommendations: asArray(dashboard.recommendations).filter(isObject),
  };
};

const SwarmAnalytics = () => {
  useInterfaceLanguage();
  const { featureGates, ready: featureGatesReady } = useFeatureGates();
  const multiSourceEnabled =
    featureGatesReady && isFeatureEnabled(featureGates, 'multiSourceDownloads');
  const analyticsSignatureRef = useRef(null);
  const fetchRequestRef = useRef(null);
  const mountedRef = useRef(false);
  const pollIntervalRef = useRef(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timeWindow, setTimeWindow] = useState(24);
  const [rankingLimit, setRankingLimit] = useState(20);
  const performanceMetrics = analytics?.performanceMetrics ?? null;
  const peerRankings = analytics?.peerRankings ?? [];
  const efficiencyMetrics = analytics?.efficiencyMetrics ?? null;
  const recommendations = analytics?.recommendations ?? [];

  const timeWindowOptions = [
    { key: '1', text: interfaceText("1 hour"), value: 1 },
    { key: '6', text: interfaceText("6 hours"), value: 6 },
    { key: '24', text: interfaceText("24 hours"), value: 24 },
    { key: '72', text: interfaceText("3 days"), value: 72 },
    { key: '168', text: interfaceText("7 days"), value: 168 },
  ];

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const fetchAnalytics = useCallback(async () => {
    if (!multiSourceEnabled) return;
    const requestKey = `${timeWindow}:${rankingLimit}`;
    if (
      document.hidden ||
      fetchRequestRef.current?.requestKey === requestKey
    ) {
      return;
    }

    const request = { requestKey };
    fetchRequestRef.current = request;
    try {
      if (analyticsSignatureRef.current === null) setLoading(true);
      const dashboard = normalizeDashboard(
        await swarmAnalyticsLibrary.getDashboard(timeWindow, rankingLimit),
      );

      if (!mountedRef.current) return;
      if (document.hidden || fetchRequestRef.current !== request) return;

      const signature = JSON.stringify(dashboard);
      if (analyticsSignatureRef.current !== signature) {
        analyticsSignatureRef.current = signature;
        setAnalytics(dashboard);
      }
    } catch (error) {
      if (
        !mountedRef.current ||
        document.hidden ||
        fetchRequestRef.current !== request
      ) return;
      toast.error(getApiErrorMessage(error, { t: interfaceText }, 'Failed to load analytics'));
      console.error('Failed to fetch analytics:', error);
    } finally {
      if (fetchRequestRef.current === request) {
        fetchRequestRef.current = null;
      }
      if (mountedRef.current && fetchRequestRef.current === null) {
        setLoading(false);
      }
    }
  }, [multiSourceEnabled, rankingLimit, timeWindow]);

  useEffect(() => {
    if (!featureGatesReady) return undefined;
    if (!multiSourceEnabled) {
      setLoading(false);
      return undefined;
    }

    const stopPolling = () => {
      if (!pollIntervalRef.current) return;
      window.clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    };
    const startPolling = () => {
      if (document.hidden || pollIntervalRef.current) return;
      fetchAnalytics();
      pollIntervalRef.current = window.setInterval(
        fetchAnalytics,
        POLL_INTERVAL_MS,
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
  }, [fetchAnalytics, featureGatesReady, multiSourceEnabled]);

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'Critical':
        return 'red';
      case 'High':
        return 'orange';
      case 'Medium':
        return 'yellow';
      case 'Low':
        return 'blue';
      default:
        return 'grey';
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'PeerSelection':
        return 'users';
      case 'ChunkSize':
        return 'puzzle piece';
      case 'SourceCount':
        return 'sitemap';
      case 'NetworkConfig':
        return 'wifi';
      case 'PerformanceTuning':
        return 'tachometer alternate';
      default:
        return 'info circle';
    }
  };

  if (featureGatesReady && !multiSourceEnabled) {
    return (
      <div>
        <Header
          as="h2"
          dividing
        >
          <Icon name="chart line" />
          <Header.Content><LocalizedText source={"Swarm Analytics"} /></Header.Content>
        </Header>
        <FeatureGateNotice
          configurationKeys={['feature.MultiSourceDownloads']}
          featureGate={featureGates.multiSourceDownloads}
          featureName="Multi-source downloads"
        />
      </div>
    );
  }

  return (
    <div>
      <Header
        as="h2"
        dividing
      >
        <Icon name="chart line" />
        <Header.Content><LocalizedText source={"Swarm Analytics"} /></Header.Content>
      </Header>

      {/* Controls */}
      <Segment>
        <Grid columns={2}>
          <Grid.Column>
            <label><LocalizedText source={"Time Window"} /></label>
            <Dropdown
              onChange={(e, { value }) => setTimeWindow(value)}
              options={timeWindowOptions}
              selection
              value={timeWindow}
            />
          </Grid.Column>
          <Grid.Column>
            <label><LocalizedText source={"Peer Rankings Limit"} /></label>
            <Dropdown
              onChange={(e, { value }) => setRankingLimit(value)}
              options={[
                { key: '10', text: interfaceText("Top 10"), value: 10 },
                { key: '20', text: interfaceText("Top 20"), value: 20 },
                { key: '50', text: interfaceText("Top 50"), value: 50 },
                { key: '100', text: interfaceText("Top 100"), value: 100 },
              ]}
              selection
              value={rankingLimit}
            />
          </Grid.Column>
        </Grid>
      </Segment>

      {loading && (
        <Loader
          active
          inline="centered"
        />
      )}

      {!loading && (
        <>
          {/* Performance Metrics */}
          {performanceMetrics && (
            <Card fluid>
              <Card.Content>
                <Card.Header><LocalizedText source={"Performance Metrics"} /></Card.Header>
                <Card.Meta>
                  <LocalizedText
                    source={timeWindow === 1 ? "Last hour" : "Last {count} hours"}
                    values={{ count: timeWindow }}
                  />
                </Card.Meta>
              </Card.Content>
              <Card.Content>
                <Grid
                  columns={4}
                  divided
                >
                  <Grid.Column>
                    <Statistic>
                      <Statistic.Value>
                        {performanceMetrics.totalDownloads?.toLocaleString(getRegionalLocale()) ??
                          0}
                      </Statistic.Value>
                      <Statistic.Label><LocalizedText source={"Total Downloads"} /></Statistic.Label>
                    </Statistic>
                  </Grid.Column>
                  <Grid.Column>
                    <Statistic>
                      <Statistic.Value>
                        {(performanceMetrics.successRate * 100).toFixed(1)}%
                      </Statistic.Value>
                      <Statistic.Label><LocalizedText source={"Success Rate"} /></Statistic.Label>
                    </Statistic>
                  </Grid.Column>
                  <Grid.Column>
                    <Statistic>
                      <Statistic.Value>
                        {formatBytes(
                          performanceMetrics.averageSpeedBytesPerSecond,
                        )}
                        /s
                      </Statistic.Value>
                      <Statistic.Label><LocalizedText source={"Avg Speed"} /></Statistic.Label>
                    </Statistic>
                  </Grid.Column>
                  <Grid.Column>
                    <Statistic>
                      <Statistic.Value>
                        {performanceMetrics.averageDurationSeconds?.toFixed(
                          1,
                        ) ?? 0}
                        <LocalizedText source={"s"} /></Statistic.Value>
                      <Statistic.Label><LocalizedText source={"Avg Duration"} /></Statistic.Label>
                    </Statistic>
                  </Grid.Column>
                </Grid>
                <Grid
                  columns={3}
                  style={{ marginTop: '1em' }}
                >
                  <Grid.Column>
                    <Statistic size="small">
                      <Statistic.Value>
                        {formatBytes(performanceMetrics.totalBytesDownloaded)}
                      </Statistic.Value>
                      <Statistic.Label><LocalizedText source={"Total Bytes"} /></Statistic.Label>
                    </Statistic>
                  </Grid.Column>
                  <Grid.Column>
                    <Statistic size="small">
                      <Statistic.Value>
                        {performanceMetrics.totalChunksCompleted?.toLocaleString(getRegionalLocale()) ??
                          0}
                      </Statistic.Value>
                      <Statistic.Label><LocalizedText source={"Chunks Completed"} /></Statistic.Label>
                    </Statistic>
                  </Grid.Column>
                  <Grid.Column>
                    <Statistic size="small">
                      <Statistic.Value>
                        {(performanceMetrics.chunkSuccessRate * 100).toFixed(1)}
                        %
                      </Statistic.Value>
                      <Statistic.Label><LocalizedText source={"Chunk Success Rate"} /></Statistic.Label>
                    </Statistic>
                  </Grid.Column>
                </Grid>
              </Card.Content>
            </Card>
          )}

          {/* Efficiency Metrics */}
          {efficiencyMetrics && (
            <Card
              fluid
              style={{ marginTop: '1em' }}
            >
              <Card.Content>
                <Card.Header><LocalizedText source={"Efficiency Metrics"} /></Card.Header>
              </Card.Content>
              <Card.Content>
                <Grid
                  columns={3}
                  divided
                >
                  <Grid.Column>
                    <div>
                      <label><LocalizedText source={"Chunk Utilization"} /></label>
                      <Progress
                        indicating
                        percent={efficiencyMetrics.chunkUtilization * 100}
                      />
                    </div>
                  </Grid.Column>
                  <Grid.Column>
                    <div>
                      <label><LocalizedText source={"Peer Utilization"} /></label>
                      <Progress
                        indicating
                        percent={efficiencyMetrics.peerUtilization * 100}
                      />
                    </div>
                  </Grid.Column>
                  <Grid.Column>
                    <div>
                      <label><LocalizedText source={"Redundancy Factor"} /></label>
                      <Statistic size="small">
                        <Statistic.Value>
                          {efficiencyMetrics.redundancyFactor?.toFixed(2) ?? 0}
                        </Statistic.Value>
                      </Statistic>
                    </div>
                  </Grid.Column>
                </Grid>
              </Card.Content>
            </Card>
          )}

          {/* Peer Rankings */}
          {peerRankings.length > 0 && (
            <Card
              fluid
              style={{ marginTop: '1em' }}
            >
              <Card.Content>
                <Card.Header><LocalizedText source={"Top Peer Rankings"} /></Card.Header>
              </Card.Content>
              <Card.Content>
                <Table celled>
                  <Table.Header>
                    <Table.Row>
                      <Table.HeaderCell><LocalizedText source={"Rank"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Peer ID"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Source"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Reputation"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Avg RTT"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Avg Throughput"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Chunks"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Success Rate"} /></Table.HeaderCell>
                    </Table.Row>
                  </Table.Header>
                  <Table.Body>
                    {peerRankings.map((peer) => (
                      <Table.Row key={peer.peerId}>
                        <Table.Cell>
                          <Label
                            circular
                            color="blue"
                          >
                            {peer.rank}
                          </Label>
                        </Table.Cell>
                        <Table.Cell>{peer.peerId}</Table.Cell>
                        <Table.Cell>
                          <Label>{peer.source}</Label>
                        </Table.Cell>
                        <Table.Cell>
                          <Progress
                            color={
                              peer.reputationScore > 0.7
                                ? 'green'
                                : peer.reputationScore > 0.4
                                  ? 'yellow'
                                  : 'red'
                            }
                            percent={peer.reputationScore * 100}
                            size="tiny"
                          />
                          {(peer.reputationScore * 100).toFixed(1)}%
                        </Table.Cell>
                        <Table.Cell>
                          {peer.averageRttMs?.toFixed(1)} <LocalizedText source={"ms"} /></Table.Cell>
                        <Table.Cell>
                          {formatBytes(peer.averageThroughputBytesPerSecond)}/s
                        </Table.Cell>
                        <Table.Cell>
                          {peer.chunksCompleted?.toLocaleString(getRegionalLocale()) ?? 0}
                        </Table.Cell>
                        <Table.Cell>
                          {(peer.chunkSuccessRate * 100).toFixed(1)}%
                        </Table.Cell>
                      </Table.Row>
                    ))}
                  </Table.Body>
                </Table>
              </Card.Content>
            </Card>
          )}

          {/* Recommendations */}
          {recommendations.length > 0 && (
            <Card
              fluid
              style={{ marginTop: '1em' }}
            >
              <Card.Content>
                <Card.Header><LocalizedText source={"Optimization Recommendations"} /></Card.Header>
              </Card.Content>
              <Card.Content>
                {recommendations.map((rec, index) => (
                  <Message
                    color={getPriorityColor(rec.priority)}
                    icon
                    key={index}
                  >
                    <Icon name={getTypeIcon(rec.type)} />
                    <Message.Content>
                      <Message.Header>
                        {rec.title}
                        <Label
                          color={getPriorityColor(rec.priority)}
                          size="tiny"
                          style={{ marginLeft: '0.5em' }}
                        >
                          {rec.priority}
                        </Label>
                      </Message.Header>
                      <p>{rec.description}</p>
                      <p>
                        <strong><LocalizedText source={"Action:"} /></strong> {rec.action}
                      </p>
                      <p>
                        <strong><LocalizedText source={"Estimated Impact:"} /></strong>{' '}
                        {(rec.estimatedImpact * 100).toFixed(0)}%
                      </p>
                    </Message.Content>
                  </Message>
                ))}
              </Card.Content>
            </Card>
          )}

          {!performanceMetrics &&
            !efficiencyMetrics &&
            peerRankings.length === 0 &&
            recommendations.length === 0 && (
              <Message info>
                <Message.Header><LocalizedText source={"No Analytics Data"} /></Message.Header>
                <p>
                  <LocalizedText source={"No swarm analytics data available. Start some swarm downloads to see metrics."} /></p>
              </Message>
            )}
        </>
      )}
    </div>
  );
};

export default SwarmAnalytics;
