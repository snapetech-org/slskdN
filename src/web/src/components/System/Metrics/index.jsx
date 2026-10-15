import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
import { formatRegionalCompactNumber, formatRegionalNumber, useRegionalLocale } from '../../../lib/regionalFormat';
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

const formatBytes = (bytes, locale) => {
  if (bytes === undefined || bytes === null) return formatRegionalNumber(0, undefined, locale) + ' B';
  if (bytes === 0) return formatRegionalNumber(0, undefined, locale) + ' B';
  const k = 1_024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return formatRegionalNumber(bytes / k ** i, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }, locale) + ' ' + sizes[i];
};

const formatNumber = (value, locale) => {
  if (value === undefined || value === null) return '—';
  return formatRegionalCompactNumber(value, { maximumFractionDigits: 2 }, locale);
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
    get title() { return interfaceText("Transfers"); },
    icon: 'exchange',
    metrics: [
      { key: 'slskd_uploads_total', get label() { return interfaceText("Uploads Total"); }, format: formatNumber },
      { key: 'slskd_downloads_total', get label() { return interfaceText("Downloads Total"); }, format: formatNumber },
      { key: 'slskd_uploads_active', get label() { return interfaceText("Uploads Active"); }, format: formatNumber },
      { key: 'slskd_downloads_active', get label() { return interfaceText("Downloads Active"); }, format: formatNumber },
      { key: 'slskd_uploads_queued', get label() { return interfaceText("Uploads Queued"); }, format: formatNumber },
      { key: 'slskd_downloads_queued', get label() { return interfaceText("Downloads Queued"); }, format: formatNumber },
    ],
  },
  {
    key: 'search',
    get title() { return interfaceText("Search"); },
    icon: 'search',
    metrics: [
      { key: 'slskd_searches_incoming_requests_total', get label() { return interfaceText("Incoming Requests"); }, format: formatNumber },
      { key: 'slskd_searches_incoming_requests_dropped_total', get label() { return interfaceText("Dropped Requests"); }, format: formatNumber },
      { key: 'slskd_searches_outgoing_total', get label() { return interfaceText("Outgoing Searches"); }, format: formatNumber },
    ],
  },
  {
    key: 'process',
    get title() { return interfaceText("Process"); },
    icon: 'microchip',
    metrics: [
      { key: 'process_working_set_bytes', get label() { return interfaceText("Working Set"); }, format: formatBytes },
      { key: 'dotnet_total_memory_bytes', get label() { return interfaceText("Managed Memory"); }, format: formatBytes },
      { key: 'process_cpu_seconds_total', get label() { return interfaceText("CPU Seconds"); }, format: formatNumber },
    ],
  },
  {
    key: 'network',
    get title() { return interfaceText("Network"); },
    icon: 'wifi',
    metrics: [
      { key: 'microsoft_aspnetcore_server_kestrel_current_connections', get label() { return interfaceText("Kestrel Connections"); }, format: formatNumber },
      { key: 'system_net_sockets_connections_established_total', get label() { return interfaceText("Sockets Established"); }, format: formatNumber },
    ],
  },
];

const MetricGroup = ({ group, metrics }) => {
  useInterfaceLanguage();
  const regionalLocale = useRegionalLocale();
  const items = group.metrics
    .map(({ key, label, format }) => ({
      label,
      value: sampleValue(metrics[key]),
      format: (value) => format(value, regionalLocale),
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
  useInterfaceLanguage();
  const regionalLocale = useRegionalLocale();
  const slskdMetrics = Object.entries(metrics)
    .filter(([key]) => key.startsWith('slskd_'))
    .sort(([a], [b]) => a.localeCompare(b));

  if (slskdMetrics.length === 0) return null;

  return (
    <Segment>
      <Header size="small">
        <Icon name="table" />
        <LocalizedText source={"All slskdN Metrics"} /></Header>
      <div
        aria-label={interfaceText("Prometheus metric details")}
        className="system-metrics-table-scroll"
        role="region"
        tabIndex={0}
       {...interfaceTextProps("Prometheus metric details")}>
        <Table
          compact
          size="small"
          striped
        >
          <Table.Header>
            <Table.Row>
              <Table.HeaderCell><LocalizedText source={"Metric"} /></Table.HeaderCell>
              <Table.HeaderCell><LocalizedText source={"Type"} /></Table.HeaderCell>
              <Table.HeaderCell><LocalizedText source={"Value"} /></Table.HeaderCell>
              <Table.HeaderCell><LocalizedText source={"Help"} /></Table.HeaderCell>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {slskdMetrics.map(([key, metric]) => (
              <Table.Row key={key}>
                <Table.Cell>
                  <code>{key}</code>
                </Table.Cell>
                <Table.Cell>{metric.type}</Table.Cell>
                <Table.Cell>{formatNumber(sampleValue(metric), regionalLocale)}</Table.Cell>
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
  useInterfaceLanguage();
  const regionalLocale = useRegionalLocale();
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
      setError(getApiErrorMessage(err, { t: interfaceText }));
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
          header={interfaceText("Failed to load metrics")}
          content={error}
         {...interfaceTextProps("Failed to load metrics")}/>
        <Popup
          content={interfaceText("Try the Prometheus metrics request again after the current error.")}
          position="top center"
          trigger={(
            <Button
              onClick={fetchMetrics}
              primary
            >
              <Icon name="refresh" />
              <LocalizedText source={"Try Again"} /></Button>
          )}
         {...interfaceTextProps("Try the Prometheus metrics request again after the current error.")}/>
      </>
    );
  }

  const visibleMetrics = metrics || {};

  return (
    <div>
      <div className="system-metrics-header">
        <Header size="medium">
          <Icon name="chart bar" />
          <LocalizedText source={"Prometheus Metrics"} /></Header>
        <div className="system-metrics-refresh">
          {lastUpdated && (
            <span>
              <LocalizedText
                source="Updated {time}"
                values={{ time: lastUpdated.toLocaleTimeString(regionalLocale) }}
              />
            </span>
          )}
          <Popup
            content={interfaceText("Fetch the latest Prometheus metrics now to review current application activity.")}
            position="top center"
            trigger={(
              <Button
                disabled={loading}
                loading={loading}
                onClick={fetchMetrics}
              >
                <Icon name="refresh" />
                <LocalizedText source={"Refresh"} /></Button>
            )}
           {...interfaceTextProps("Fetch the latest Prometheus metrics now to review current application activity.")}/>
        </div>
      </div>

      {loading && !metrics && (
        <Message info>
          <Icon
            loading
            name="spinner"
          />
          <LocalizedText source={"Loading metrics"} /></Message>
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
