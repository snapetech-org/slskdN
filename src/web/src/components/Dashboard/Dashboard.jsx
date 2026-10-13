import './Dashboard.css';
import { getTransferSummary } from '../../lib/reports';
import { formatBytes } from '../../lib/util';
import ErrorSegment from '../Shared/ErrorSegment';
import PlaceholderSegment from '../Shared/PlaceholderSegment';
import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button, Header, Icon, Popup, Segment } from 'semantic-ui-react';

const readProperty = (value, property) => {
  if (!value || typeof value !== 'object') return undefined;
  const key = Object.keys(value).find(
    (candidate) => candidate.toLowerCase() === property.toLowerCase(),
  );
  return key ? value[key] : undefined;
};

const getSuccessfulSummary = (summary, direction) => {
  const directionSummary = readProperty(summary, direction);
  const success = Object.entries(directionSummary ?? {}).find(([state]) =>
    state.toLowerCase().includes('succeed'),
  )?.[1];
  const count = Number(readProperty(success, 'count'));
  const bytes = Number(readProperty(success, 'totalBytes'));

  return {
    bytes: Number.isFinite(bytes) && bytes > 0 ? bytes : 0,
    count: Number.isFinite(count) && count > 0 ? count : 0,
  };
};

const TransferStream = ({ direction, summary }) => {
  const isDownload = direction === 'download';
  const stats = getSuccessfulSummary(summary, isDownload ? 'Download' : 'Upload');
  const label = isDownload ? 'Downloads' : 'Uploads';

  return (
    <section className={`dashboard-stream dashboard-stream-${direction}`}>
      <h2 className="dashboard-stream-title">
        <Icon name={isDownload ? 'download' : 'upload'} />
        {label}
      </h2>
      <div className="dashboard-stream-bytes" data-testid={`${direction}-bytes`}>
        {formatBytes(stats.bytes)}
      </div>
      <p className="dashboard-stream-count" data-testid={`${direction}-count`}>
        {stats.count.toLocaleString()} successful {stats.count === 1 ? 'file' : 'files'}
      </p>
      <Link className="dashboard-stream-link" to={`/${direction}s`}>
        Open {direction} list
      </Link>
    </section>
  );
};

const Dashboard = () => {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSummary(await getTransferSummary());
    } catch (requestError) {
      setError(
        requestError?.response?.data ??
          requestError?.message ??
          'Transfer totals could not be loaded.',
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="view dashboard-view" data-testid="dashboard-root">
      <Segment className="dashboard-panel" raised>
        <header className="dashboard-heading">
          <div>
            <Header as="h1" className="dashboard-title">
              Transfer overview
            </Header>
            <p className="dashboard-intro">
              Successful files moved in the last seven days.
            </p>
          </div>
          <Popup
            content="Refresh the seven-day totals from the transfer history."
            position="top center"
            trigger={(
              <Button
                aria-label="Refresh transfer overview"
                disabled={loading}
                icon="refresh"
                loading={loading}
                onClick={refresh}
                size="small"
              />
            )}
          />
        </header>

        {loading && !summary ? (
          <PlaceholderSegment caption="Loading transfer totals" icon="exchange" />
        ) : error ? (
          <ErrorSegment caption={error} />
        ) : (
          <>
            <div className="dashboard-streams">
              <TransferStream direction="download" summary={summary} />
              <TransferStream direction="upload" summary={summary} />
            </div>
            <p className="dashboard-footnote">
              Totals use bytes actually transferred and count successful transfers only.
            </p>
          </>
        )}
      </Segment>
    </div>
  );
};

export default Dashboard;
