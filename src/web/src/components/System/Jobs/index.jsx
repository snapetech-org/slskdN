import { getRegionalLocale } from '../../../lib/regionalFormat';
// <copyright file="index.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import * as jobsLibrary from '../../../lib/jobs';
import FeatureGateNotice from '../../Shared/FeatureGateNotice';
import useFeatureGates, { isFeatureEnabled } from '../../Shared/useFeatureGates';
import { formatBytes } from '../../../lib/util';
import SwarmVisualization from '../SwarmVisualization';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'react-toastify';
import {
  Button,
  Card,
  Dropdown,
  Grid,
  Header,
  Icon,
  Label,
  Loader,
  Modal,
  Pagination,
  Popup,
  Progress,
  Segment,
  Statistic,
  Table,
} from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);
const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value);
const SWARM_POLL_INTERVAL_MS = 5_000;

const sameSwarmJobs = (previous, next) =>
  previous.length === next.length &&
  previous.every(
    (job, index) =>
      job.jobId === next[index]?.jobId &&
      job.filename === next[index]?.filename &&
      job.activeSources === next[index]?.activeSources &&
      job.downloadedBytes === next[index]?.downloadedBytes &&
      job.totalBytes === next[index]?.totalBytes &&
      job.progressPercent === next[index]?.progressPercent &&
      job.percentComplete === next[index]?.percentComplete &&
      job.completedChunks === next[index]?.completedChunks &&
      job.totalChunks === next[index]?.totalChunks &&
      job.state === next[index]?.state &&
      job.chunksPerSecond === next[index]?.chunksPerSecond &&
      job.estimatedSecondsRemaining ===
        next[index]?.estimatedSecondsRemaining,
  );

const Jobs = () => {
  const { featureGates, ready: featureGatesReady } = useFeatureGates();
  const multiSourceEnabled =
    featureGatesReady && isFeatureEnabled(featureGates, 'multiSourceDownloads');
  const mountedRef = useRef(false);
  const swarmFetchInFlightRef = useRef(false);
  const swarmPollIntervalRef = useRef(null);
  const [jobs, setJobs] = useState([]);
  const [swarmJobs, setSwarmJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [swarmLoading, setSwarmLoading] = useState(true);
  const [selectedSwarmJobId, setSelectedSwarmJobId] = useState(null);
  const [showVisualization, setShowVisualization] = useState(false);
  const [filters, setFilters] = useState({
    sortBy: 'created_at',
    sortOrder: 'desc',
    status: null,
    type: null,
  });
  const [pagination, setPagination] = useState({
    hasMore: false,
    limit: 20,
    offset: 0,
    total: 0,
  });

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const fetchJobs = useCallback(async () => {
    try {
      setLoading(true);
      const response = await jobsLibrary.getJobs({
        limit: pagination.limit,
        offset: pagination.offset,
        sortBy: filters.sortBy,
        sortOrder: filters.sortOrder,
        status: filters.status || undefined,
        type: filters.type || undefined,
      });
      if (!mountedRef.current) return;
      setJobs(asArray(response?.jobs).filter(isObject));
      setPagination((previous) => ({
        ...previous,
        hasMore: response?.has_more || false,
        total: response?.total || 0,
      }));
    } catch (error) {
      if (!mountedRef.current) return;
      toast.error(
        error?.response?.data?.message ||
          error?.message ||
          'Failed to fetch jobs',
      );
      console.error('Failed to fetch jobs:', error);
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [filters, pagination.limit, pagination.offset]);

  const fetchSwarmJobs = useCallback(async () => {
    if (
      !multiSourceEnabled ||
      document.hidden ||
      !mountedRef.current ||
      swarmFetchInFlightRef.current
    ) {
      return;
    }

    swarmFetchInFlightRef.current = true;
    try {
      const jobs = await jobsLibrary.getActiveSwarmJobs();
      if (!mountedRef.current || document.hidden) return;

      const next = asArray(jobs).filter(isObject);
      setSwarmJobs((previous) =>
        sameSwarmJobs(previous, next) ? previous : next,
      );
    } catch (error) {
      if (!mountedRef.current || document.hidden) return;
      console.debug('Failed to fetch swarm jobs:', error);
    } finally {
      swarmFetchInFlightRef.current = false;
      if (mountedRef.current) {
        setSwarmLoading(false);
      }
    }
  }, [multiSourceEnabled]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  useEffect(() => {
    if (!featureGatesReady) return undefined;
    if (!multiSourceEnabled) {
      setSwarmJobs([]);
      setSwarmLoading(false);
      return undefined;
    }

    const stopPolling = () => {
      if (swarmPollIntervalRef.current) {
        window.clearInterval(swarmPollIntervalRef.current);
        swarmPollIntervalRef.current = null;
      }
    };
    const startPolling = () => {
      if (document.hidden || swarmPollIntervalRef.current) return;

      fetchSwarmJobs();
      swarmPollIntervalRef.current = window.setInterval(
        fetchSwarmJobs,
        SWARM_POLL_INTERVAL_MS,
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
  }, [fetchSwarmJobs, featureGatesReady, multiSourceEnabled]);

  const analytics = useMemo(() => {
    const allJobs = [...jobs, ...swarmJobs];
    const byStatus = allJobs.reduce((accumulator, job) => {
      const status = job.status || 'unknown';
      accumulator[status] = (accumulator[status] || 0) + 1;
      return accumulator;
    }, {});

    const byType = allJobs.reduce((accumulator, job) => {
      const type = job.type || 'unknown';
      accumulator[type] = (accumulator[type] || 0) + 1;
      return accumulator;
    }, {});

    const activeCount = allJobs.filter(
      (index) => index.status === 'running' || index.status === 'pending',
    ).length;

    const completedCount = allJobs.filter(
      (index) => index.status === 'completed',
    ).length;

    return {
      active: activeCount,
      byStatus,
      byType,
      completed: completedCount,
      total: allJobs.length,
    };
  }, [jobs, swarmJobs]);

  const handleFilterChange = (key, value) => {
    setFilters((previous) => ({ ...previous, [key]: value }));
    setPagination((previous) => ({ ...previous, offset: 0 })); // Reset to first page
  };

  const handlePageChange = (_event, { activePage }) => {
    setPagination((previous) => ({
      ...previous,
      offset: (activePage - 1) * previous.limit,
    }));
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'running':
        return 'blue';
      case 'pending':
        return 'yellow';
      case 'completed':
        return 'green';
      case 'failed':
        return 'red';
      default:
        return 'grey';
    }
  };

  const getStatusIcon = (status) => {
    switch (status?.toLowerCase()) {
      case 'running':
        return 'spinner';
      case 'pending':
        return 'clock';
      case 'completed':
        return 'check circle';
      case 'failed':
        return 'times circle';
      default:
        return 'question circle';
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleString(getRegionalLocale());
    } catch {
      return dateString;
    }
  };

  const totalPages = Math.ceil(pagination.total / pagination.limit);
  const closeSwarmVisualization = () => {
    setShowVisualization(false);
    setSelectedSwarmJobId(null);
  };

  return (
    <div className="system-jobs-dashboard">
      <FeatureGateNotice
        configurationKeys={['feature.MultiSourceDownloads']}
        featureGate={featureGates.multiSourceDownloads}
        featureName="Multi-source downloads"
      />
      {/* Analytics Overview */}
      <Segment>
        <Header as="h3">
          <Icon name="chart bar" />
          <Header.Content>Job Analytics</Header.Content>
        </Header>
        <Grid
          columns={4}
          stackable
        >
          <Grid.Column>
            <Statistic>
              <Statistic.Value>{analytics.total}</Statistic.Value>
              <Statistic.Label>Total Jobs</Statistic.Label>
            </Statistic>
          </Grid.Column>
          <Grid.Column>
            <Statistic>
              <Statistic.Value>
                <Icon
                  color="blue"
                  name="spinner"
                />
                {analytics.active}
              </Statistic.Value>
              <Statistic.Label>Active</Statistic.Label>
            </Statistic>
          </Grid.Column>
          <Grid.Column>
            <Statistic>
              <Statistic.Value>
                <Icon
                  color="green"
                  name="check circle"
                />
                {analytics.completed}
              </Statistic.Value>
              <Statistic.Label>Completed</Statistic.Label>
            </Statistic>
          </Grid.Column>
          <Grid.Column>
            <Statistic>
              <Statistic.Value>
                {Object.keys(analytics.byType).length}
              </Statistic.Value>
              <Statistic.Label>Job Types</Statistic.Label>
            </Statistic>
          </Grid.Column>
        </Grid>
      </Segment>

      {/* Active Swarm Jobs */}
      {swarmJobs.length > 0 && (
        <Segment>
          <Header as="h3">
            <Icon name="bolt" />
            <Header.Content>
              Active Swarm Downloads
              <Header.Subheader>
                Multi-source downloads in progress
              </Header.Subheader>
            </Header.Content>
          </Header>
          {swarmLoading && (
            <Loader
              active
              inline="centered"
            />
          )}
          <Grid
            columns={2}
            stackable
          >
            {swarmJobs.map((job) => (
              <Grid.Column key={job.jobId}>
                <Card fluid>
                  <Card.Content>
                    <Card.Header>
                      <Icon
                        color="yellow"
                        name="bolt"
                      />
                      {job.filename?.split('/').pop() ?? 'Unknown file'}
                    </Card.Header>
                    <Card.Meta>
                      {job.activeSources ?? 0} sources •{' '}
                      {formatBytes(job.downloadedBytes ?? 0)} /{' '}
                      {formatBytes(job.totalBytes ?? 0)}
                    </Card.Meta>
                    <Progress
                      active
                      color="blue"
                      percent={job.progressPercent ?? job.percentComplete ?? 0}
                      progress
                      size="small"
                    />
                    {job.chunksPerSecond && (
                      <Label size="tiny">
                        <Icon name="tachometer alternate" />
                        {job.chunksPerSecond.toFixed(1)} chunks/s
                      </Label>
                    )}
                    {job.estimatedSecondsRemaining && (
                      <Label size="tiny">
                        <Icon name="clock" />
                        {Math.round(job.estimatedSecondsRemaining)}s remaining
                      </Label>
                    )}
                    <div style={{ marginTop: '0.5em' }}>
                      <Popup
                        content={`Inspect contributing sources and chunk progress for ${job.filename?.split('/').pop() ?? 'this swarm download'}.`}
                        position="top center"
                        trigger={(
                          <Button
                            aria-label={`View swarm download details for ${job.filename?.split('/').pop() ?? 'unknown file'}`}
                            compact
                            onClick={() => {
                              setSelectedSwarmJobId(job.jobId);
                              setShowVisualization(true);
                            }}
                            size="small"
                          >
                            <Icon name="chart bar" />
                            View Details
                          </Button>
                        )}
                      />
                    </div>
                  </Card.Content>
                </Card>
              </Grid.Column>
            ))}
          </Grid>
        </Segment>
      )}

      {/* Swarm Visualization Modal */}
      <Modal
        closeIcon={false}
        onClose={closeSwarmVisualization}
        open={showVisualization}
        size="large"
      >
        <Modal.Header className="system-jobs-visualization-header">
          <span className="system-jobs-visualization-title">
            <Icon name="chart bar" />
            Swarm Download Visualization
          </span>
          <Popup
            content="Close the swarm visualization and return to the job list."
            position="left center"
            trigger={(
              <Button
                aria-label="Close swarm download visualization"
                basic
                icon
                onClick={closeSwarmVisualization}
                title="Close swarm download visualization"
              >
                <Icon name="close" />
              </Button>
            )}
          />
        </Modal.Header>
        <Modal.Content scrolling>
          {selectedSwarmJobId && (
            <SwarmVisualization jobId={selectedSwarmJobId} />
          )}
        </Modal.Content>
      </Modal>

      {/* Job List */}
      <Segment>
        <Header as="h3">
          <Icon name="tasks" />
          <Header.Content>All Jobs</Header.Content>
        </Header>

        {/* Filters */}
        <div className="system-jobs-filters">
          <Dropdown
            clearable
            onChange={(_e, { value }) => handleFilterChange('type', value)}
            options={[
              { key: 'discography', text: 'Discography', value: 'discography' },
              {
                key: 'label_crate',
                text: 'Label Crate',
                value: 'label_crate',
              },
            ]}
            placeholder="Filter by Type"
            selection
            value={filters.type}
          />
          <Dropdown
            clearable
            onChange={(_e, { value }) => handleFilterChange('status', value)}
            options={[
              { key: 'pending', text: 'Pending', value: 'pending' },
              { key: 'running', text: 'Running', value: 'running' },
              { key: 'completed', text: 'Completed', value: 'completed' },
              { key: 'failed', text: 'Failed', value: 'failed' },
            ]}
            placeholder="Filter by Status"
            selection
            value={filters.status}
          />
          <Dropdown
            onChange={(_e, { value }) => handleFilterChange('sortBy', value)}
            options={[
              { key: 'created_at', text: 'Created Date', value: 'created_at' },
              { key: 'status', text: 'Status', value: 'status' },
              { key: 'id', text: 'ID', value: 'id' },
            ]}
            placeholder="Sort By"
            selection
            value={filters.sortBy}
          />
          <Popup
            content={
              filters.sortOrder === 'asc'
                ? 'Sort the current job list in descending order.'
                : 'Sort the current job list in ascending order.'
            }
            position="top center"
            trigger={(
              <Button
                aria-label={
                  filters.sortOrder === 'asc'
                    ? 'Sort jobs in descending order'
                    : 'Sort jobs in ascending order'
                }
                icon
                onClick={() =>
                  handleFilterChange(
                    'sortOrder',
                    filters.sortOrder === 'asc' ? 'desc' : 'asc',
                  )
                }
                title={
                  filters.sortOrder === 'asc'
                    ? 'Sort jobs in descending order'
                    : 'Sort jobs in ascending order'
                }
                toggle
              >
                <Icon
                  name={filters.sortOrder === 'asc' ? 'sort up' : 'sort down'}
                />
                {filters.sortOrder === 'asc' ? 'Ascending' : 'Descending'}
              </Button>
            )}
          />
          <Popup
            content="Reload the current job list after job status or page data changes."
            position="top center"
            trigger={(
              <Button
                aria-label="Refresh job list"
                icon
                onClick={fetchJobs}
                title="Refresh the current job list."
              >
                <Icon name="refresh" />
                Refresh
              </Button>
            )}
          />
        </div>

        {loading ? (
          <Loader
            active
            inline="centered"
          />
        ) : jobs.length === 0 ? (
          <Segment placeholder>
            <Header icon>
              <Icon name="inbox" />
              No jobs found
            </Header>
            <p>No jobs match the current filters.</p>
          </Segment>
        ) : (
          <>
            <div
              aria-label="Job list"
              className="system-jobs-table-scroll"
              role="region"
              tabIndex={0}
            >
              <Table celled>
                <Table.Header>
                  <Table.Row>
                    <Table.HeaderCell>ID</Table.HeaderCell>
                    <Table.HeaderCell>Type</Table.HeaderCell>
                    <Table.HeaderCell>Status</Table.HeaderCell>
                    <Table.HeaderCell>Progress</Table.HeaderCell>
                    <Table.HeaderCell>Created</Table.HeaderCell>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  {jobs.map((job) => (
                    <Table.Row key={job.id}>
                      <Table.Cell>
                        <code>{job.id}</code>
                      </Table.Cell>
                      <Table.Cell>
                        <Label>{job.type || 'unknown'}</Label>
                      </Table.Cell>
                      <Table.Cell>
                        <Label color={getStatusColor(job.status)}>
                          <Icon name={getStatusIcon(job.status)} />
                          {job.status || 'unknown'}
                        </Label>
                      </Table.Cell>
                      <Table.Cell>
                        {job.progress ? (
                          <div>
                            <Progress
                              color={getStatusColor(job.status)}
                              percent={
                                job.progress.releases_total > 0
                                  ? (job.progress.releases_done /
                                      job.progress.releases_total) *
                                    100
                                  : 0
                              }
                              progress
                              size="small"
                            />
                            <div
                              style={{ fontSize: '0.9em', marginTop: '0.25em' }}
                            >
                              {job.progress.releases_done || 0} /{' '}
                              {job.progress.releases_total || 0} releases
                              {job.progress.releases_failed > 0 && (
                                <Label
                                  color="red"
                                  size="tiny"
                                >
                                  {job.progress.releases_failed} failed
                                </Label>
                              )}
                            </div>
                          </div>
                        ) : (
                          'N/A'
                        )}
                      </Table.Cell>
                      <Table.Cell>{formatDate(job.created_at)}</Table.Cell>
                    </Table.Row>
                  ))}
                </Table.Body>
              </Table>
            </div>

            {totalPages > 1 && (
              <Pagination
                activePage={
                  Math.floor(pagination.offset / pagination.limit) + 1
                }
                onPageChange={handlePageChange}
                totalPages={totalPages}
              />
            )}
          </>
        )}
      </Segment>
    </div>
  );
};

export default Jobs;
