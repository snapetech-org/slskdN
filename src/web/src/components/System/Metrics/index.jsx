import { getRegionalLocale } from '../../../lib/regionalFormat';
import { getKpiMetrics } from '../../../lib/telemetry';
import React, { useCallback, useEffect, useState } from 'react';
import {
  Button,
  Divider,
  Grid,
  Header,
  Icon,
  Message,
  Popup,
  Segment,
  Statistic,
  Table,
} from 'semantic-ui-react';

const formatBytes = (bytes) => {
  if (!bytes) return '0 B';
  const k = 1_024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / k ** i).toFixed(1)} ${sizes[i]}`;
};

const formatNumber = (value) => {
  if (value === undefined || value === null) return '—';
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return Number.parseFloat(value.toFixed(2)).toString();
};

// Extract the first sample value from a metric, or null
const sampleValue = (metric) => {
  if (!metric) return null;
  if (metric.samples && metric.samples.length > 0) return metric.samples[0].value;
  return null;
};

const KPI_GROUPS = [
  {
    key: 'transfers',
    title: 'Transfers',
    icon: 'exchange',
    metrics: [
      { key: 'slskd_uploads_total', label: 'Uploads Total', format: formatNumber },
      { key: 'slskd_downloads_total', label: 'Downloads Total', format: formatNumber },
      { key: 'slskd_uploads_active', label: 'Uploads Active', format: formatNumber },
      { key: 'slskd_downloads_active', label: 'Downloads Active', format: formatNumber },
      { key: 'slskd_uploads_queued', label: 'Uploads Queued', format: formatNumber },
      { key: 'slskd_downloads_queued', label: 'Downloads Queued', format: formatNumber },
    ],
  },
  {
    key: 'search',
    title: 'Search',
    icon: 'search',
    metrics: [
      { key: 'slskd_searches_incoming_requests_total', label: 'Incoming Requests', format: formatNumber },
      { key: 'slskd_searches_incoming_requests_dropped_total', label: 'Dropped Requests', format: formatNumber },
      { key: 'slskd_searches_outgoing_total', label: 'Outgoing Searches', format: formatNumber },
    ],
  },
  {
    key: 'process',
    title: 'Process',
    icon: 'microchip',
    metrics: [
      { key: 'process_working_set_bytes', label: 'Working Set', format: formatBytes },
      { key: 'dotnet_total_memory_bytes', label: 'Managed Memory', format: formatBytes },
      { key: 'process_cpu_seconds_total', label: 'CPU Seconds', format: formatNumber },
    ],
  },
  {
    key: 'network',
    title: 'Network',
    icon: 'wifi',
    metrics: [
      { key: 'microsoft_aspnetcore_server_kestrel_current_connections', label: 'Kestrel Connections', format: formatNumber },
      { key: 'system_net_sockets_connections_established_total', label: 'Sockets Established', format: formatNumber },
    ],
  },
];

const MetricGroup = ({ group, metrics }) => {
  const items = group.metrics
    .map(({ key, label, format }) => ({
      label,
      value: sampleValue(metrics[key]),
      format,
    }))
    .filter(({ value }) => value !== null);

  if (items.length === 0) return null;

  return (
    <Segment className="system-metrics-kpi">
      <Header size="small">
        <Icon name={group.icon} />
        {group.title}
      </Header>
      <Statistic.Group
        className="system-metrics-statistics"
        size="mini"
      >
        {items.map(({ label, value, format }) => (
          <Statistic key={label}>
            <Statistic.Value>{format(value)}</Statistic.Value>
            <Statistic.Label>{label}</Statistic.Label>
          </Statistic>
        ))}
      </Statistic.Group>
    </Segment>
  );
};

const SlskdMetricsTable = ({ metrics }) => {
  const slskdMetrics = Object.entries(metrics)
    .filter(([key]) => key.startsWith('slskd_'))
    .sort(([a], [b]) => a.localeCompare(b));

  if (slskdMetrics.length === 0) return null;

  return (
    <Segment>
      <Header size="small">
        <Icon name="table" />
        All slskdN Metrics
      </Header>
      <div
        aria-label="Prometheus metric details"
        className="system-metrics-table-scroll"
        role="region"
        tabIndex={0}
      >
        <Table
          compact
          size="small"
          striped
        >
          <Table.Header>
            <Table.Row>
              <Table.HeaderCell>Metric</Table.HeaderCell>
              <Table.HeaderCell>Type</Table.HeaderCell>
              <Table.HeaderCell>Value</Table.HeaderCell>
              <Table.HeaderCell>Help</Table.HeaderCell>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {slskdMetrics.map(([key, metric]) => (
              <Table.Row key={key}>
                <Table.Cell>
                  <code>{key}</code>
                </Table.Cell>
                <Table.Cell>{metric.type}</Table.Cell>
                <Table.Cell>{formatNumber(sampleValue(metric))}</Table.Cell>
                <Table.Cell>{metric.help}</Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table>
      </div>
    </Segment>
  );
};

const Metrics = () => {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getKpiMetrics();
      setMetrics(data);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err?.response?.data?.message || err.message || 'Failed to load metrics');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  if (error) {
    return (
      <>
        <Message
          error
          header="Failed to load metrics"
          content={error}
        />
        <Popup
          content="Try the Prometheus metrics request again after the current error."
          position="top center"
          trigger={(
            <Button
              onClick={fetchMetrics}
              primary
            >
              <Icon name="refresh" />
              Try Again
            </Button>
          )}
        />
      </>
    );
  }

  const visibleMetrics = metrics || {};

  return (
    <div>
      <div className="system-metrics-header">
        <Header size="medium">
          <Icon name="chart bar" />
          Prometheus Metrics
        </Header>
        <div className="system-metrics-refresh">
          {lastUpdated && (
            <span>Updated {lastUpdated.toLocaleTimeString(getRegionalLocale())}</span>
          )}
          <Popup
            content="Fetch the latest Prometheus metrics now to review current application activity."
            position="top center"
            trigger={(
              <Button
                disabled={loading}
                loading={loading}
                onClick={fetchMetrics}
              >
                <Icon name="refresh" />
                Refresh
              </Button>
            )}
          />
        </div>
      </div>

      {loading && !metrics && (
        <Message info>
          <Icon
            loading
            name="spinner"
          />
          Loading metrics
        </Message>
      )}

      <Grid stackable>
        {KPI_GROUPS.map((group) => (
          <Grid.Column key={group.key} width={8}>
            <MetricGroup
              group={group}
              metrics={visibleMetrics}
            />
          </Grid.Column>
        ))}
      </Grid>

      <Divider />

      <SlskdMetricsTable metrics={visibleMetrics} />
    </div>
  );
};

export default Metrics;
