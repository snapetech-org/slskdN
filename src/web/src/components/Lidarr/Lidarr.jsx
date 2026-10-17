import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import { getRegionalLocale } from '../../lib/regionalFormat';
import './Lidarr.css';
import * as lidarrAPI from '../../lib/lidarr';
import * as wishlistAPI from '../../lib/wishlist';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'react-toastify';
import { TooltipButton } from '../Shared';
import {
  Button,
  Button as SemanticButton,
  Header,
  Icon,
  Input,
  Label,
  Loader,
  Popup,
  Segment,
  Table,
} from 'semantic-ui-react';

const formatDate = (iso) => {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(getRegionalLocale());
};

const formatRelative = (iso) => {
  if (!iso) return null;
  const diff = new Date(iso) - Date.now();
  if (diff < 0) return 'now';
  const mins = Math.round(diff / 60000);
  if (mins < 2) return 'in < 1 min';
  if (mins < 60) return `in ${mins} min`;
  return `in ${Math.round(mins / 60)}h`;
};

// ─── Status bar ──────────────────────────────────────────────────────────────

const StatusBar = ({ status, syncState, onSync, syncing }) => {
  useInterfaceLanguage();
  const connected = !!status?.version;

  return (
    <Segment className="lidarr-section">
      <div className="lidarr-section-header">
        <Header as="h3">
          <Icon name="music" />
          <Header.Content>
            <LocalizedText source={"Lidarr"} /><Header.Subheader>
              {connected
                ? <LocalizedText source={"{appName} {version}"} values={{ "appName": (status.appName), "version": (status.version) }} />
                : <LocalizedText source={"Not connected"} />}
            </Header.Subheader>
          </Header.Content>
        </Header>
        <TooltipButton
          disabled={syncing || !connected}
          icon="sync"
          loading={syncing}
          content={interfaceText("Sync Wanted Now")}
          onClick={onSync}
          primary
          size="small"
          tooltip="Fetch Lidarr's missing albums and add new ones to the slskdN wishlist."
         {...interfaceTextProps("Sync Wanted Now")}/>
      </div>

      <div className="lidarr-status-cards">
        <Label color={connected ? 'green' : 'red'} size="large">
          <Icon name={connected ? 'check circle' : 'times circle'} />
          {connected ? <LocalizedText source={"Connected"} /> : <LocalizedText source={"Disconnected"} />}
        </Label>

        {syncState?.isSyncing && (
          <Label color="yellow" size="large">
            <Icon name="spinner" loading />
            <LocalizedText source={"Syncing…"} /></Label>
        )}

        {syncState?.lastSyncAt && (
          <Label size="large" color="grey">
            <Icon name="clock" />
            <LocalizedText source={"Last sync:"} />{" "}{formatDate(syncState.lastSyncAt)}
          </Label>
        )}

        {syncState?.nextSyncAt && !syncState?.isSyncing && (
          <Label size="large" color="grey">
            <Icon name="time" />
            <LocalizedText source={"Next sync:"} />{" "}{formatRelative(syncState.nextSyncAt)}
          </Label>
        )}

        {syncState?.lastResult && (
          <>
            <Label color="green" size="large">
              <Icon name="plus" />
              {syncState.lastResult.createdCount ?? 0} <LocalizedText source={"added"} /></Label>
            <Label color="olive" size="large">
              <Icon name="copy" />
              {syncState.lastResult.duplicateCount ?? 0} <LocalizedText source={"duplicates"} /></Label>
            <Label color="grey" size="large">
              <Icon name="forward" />
              {syncState.lastResult.wantedCount ?? 0} <LocalizedText source={"total wanted"} /></Label>
          </>
        )}

        {syncState?.lastError && (
          <Label color="red" size="large">
            <Icon name="warning sign" />
            {interfaceText('The request failed. Try again.')}
          </Label>
        )}
      </div>
    </Segment>
  );
};

// ─── Wanted / Missing list ────────────────────────────────────────────────────

const PAGE_SIZE = 50;
const WISHLIST_PAGE_SIZE = 50;
const STATUS_POLL_INTERVAL_MS = 30_000;
const IMPORT_HISTORY_POLL_INTERVAL_MS = 5_000;

export const areLidarrStatusesEqual = (left, right) =>
  left === right ||
  (left?.appName === right?.appName && left?.version === right?.version);

export const areLidarrSyncStatesEqual = (left, right) =>
  left === right ||
  (left?.isSyncing === right?.isSyncing &&
    left?.lastSyncAt === right?.lastSyncAt &&
    left?.nextSyncAt === right?.nextSyncAt &&
    left?.lastError === right?.lastError &&
    left?.lastResult?.wantedCount === right?.lastResult?.wantedCount &&
    left?.lastResult?.createdCount === right?.lastResult?.createdCount &&
    left?.lastResult?.duplicateCount === right?.lastResult?.duplicateCount &&
    left?.lastResult?.skippedCount === right?.lastResult?.skippedCount);

const WantedSection = ({ connected }) => {
  useInterfaceLanguage();
  const [wanted, setWanted] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (p) => {
    if (!connected) return;
    setLoading(true);
    try {
      const data = await lidarrAPI.getWantedMissing({ page: p, pageSize: PAGE_SIZE });
      setWanted(data.records ?? []);
      setTotal(data.totalRecords ?? 0);
      setPage(p);
    } catch (err) {
      toast.error(interfaceText("Failed to load wanted: {message}", { "message": getApiErrorMessage(err, { t: interfaceText }) }));
    } finally {
      setLoading(false);
    }
  }, [connected]);

  useEffect(() => { load(1); }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const start = (page - 1) * PAGE_SIZE + 1;
  const end = Math.min(page * PAGE_SIZE, total);

  return (
    <div className="lidarr-section">
      <div className="lidarr-section-header">
        <Header as="h4">
          <Icon name="list" />
          <Header.Content>
            <LocalizedText source={"Wanted / Missing"} />{total > 0 && (
              <Header.Subheader>{total.toLocaleString(getRegionalLocale())} <LocalizedText source={"albums"} /></Header.Subheader>
            )}
          </Header.Content>
        </Header>
      </div>

      {!connected ? (
        <div className="lidarr-empty"><LocalizedText source={"Connect Lidarr to see wanted albums."} /></div>
      ) : loading ? (
        <Segment basic padded><Loader active inline="centered" /></Segment>
      ) : wanted.length === 0 ? (
        <div className="lidarr-empty"><LocalizedText source={"No wanted albums — Lidarr is satisfied!"} /></div>
      ) : (
        <>
          <Table celled compact size="small" unstackable>
            <Table.Header>
              <Table.Row>
                <Table.HeaderCell><LocalizedText source={"Artist"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Album"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Type"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Released"} /></Table.HeaderCell>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {wanted.map((album) => (
                <Table.Row key={album.id}>
                  <Table.Cell>{album.artist?.artistName ?? '—'}</Table.Cell>
                  <Table.Cell><strong>{album.title}</strong></Table.Cell>
                  <Table.Cell>{album.albumType ?? '—'}</Table.Cell>
                  <Table.Cell>
                    {album.releaseDate
                      ? new Date(album.releaseDate).toLocaleDateString(getRegionalLocale())
                      : '—'}
                  </Table.Cell>
                </Table.Row>
              ))}
            </Table.Body>
          </Table>

          <div className="lidarr-pagination">
            <span className="lidarr-pagination-info">
              {start}–{end} <LocalizedText source={"of"} />{" "}{total.toLocaleString(getRegionalLocale())}
            </span>
            <Popup
              content={interfaceText("Load the previous page of Lidarr albums.")}
              position="top center"
              trigger={
                <span>
                  <SemanticButton
                    aria-label={interfaceText("Previous Lidarr album page")}
                    disabled={page <= 1}
                    icon="chevron left"
                    onClick={() => load(page - 1)}
                    size="mini"
                   {...interfaceTextProps("Previous Lidarr album page")}/>
                </span>
              }
             {...interfaceTextProps("Load the previous page of Lidarr albums.")}/>
            <Popup
              content={interfaceText("Load the next page of Lidarr albums.")}
              position="top center"
              trigger={
                <span>
                  <SemanticButton
                    aria-label={interfaceText("Next Lidarr album page")}
                    disabled={page >= totalPages}
                    icon="chevron right"
                    onClick={() => load(page + 1)}
                    size="mini"
                   {...interfaceTextProps("Next Lidarr album page")}/>
                </span>
              }
             {...interfaceTextProps("Load the next page of Lidarr albums.")}/>
          </div>
        </>
      )}
    </div>
  );
};

// ─── Lidarr-seeded wishlist items ─────────────────────────────────────────────

const WishlistSection = () => {
  useInterfaceLanguage();
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const all = await wishlistAPI.getAll();
      // Lidarr-seeded items have autoDownload=true and a non-empty filter
      setItems(all.filter((i) => i.autoDownload && i.filter));
      setPage(1);
    } catch (err) {
      toast.error(interfaceText("Failed to load wishlist: {message}", { "message": getApiErrorMessage(err, { t: interfaceText }) }));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const totalPages = Math.max(1, Math.ceil(items.length / WISHLIST_PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const start = (currentPage - 1) * WISHLIST_PAGE_SIZE;
  const pageItems = items.slice(start, start + WISHLIST_PAGE_SIZE);
  const pageStart = items.length === 0 ? 0 : start + 1;
  const pageEnd = Math.min(start + WISHLIST_PAGE_SIZE, items.length);

  return (
    <div className="lidarr-section">
      <div className="lidarr-section-header">
        <Header as="h4">
          <Icon name="star" />
          <Header.Content>
            <LocalizedText source={"Wishlist (Lidarr-seeded)"} />{!loading && (
              <Header.Subheader>{items.length} <LocalizedText source={"searches"} /></Header.Subheader>
            )}
          </Header.Content>
        </Header>
        <Popup
          content={interfaceText("Refresh Lidarr-seeded wishlist items from the local database.")}
          position="top center"
          trigger={
            <Button
              aria-label={interfaceText("Refresh Lidarr wishlist items")}
              icon="refresh"
              loading={loading}
              onClick={load}
              size="mini"
             {...interfaceTextProps("Refresh Lidarr wishlist items")}/>
          }
         {...interfaceTextProps("Refresh Lidarr-seeded wishlist items from the local database.")}/>
      </div>

      {loading ? (
        <Segment basic padded><Loader active inline="centered" /></Segment>
      ) : items.length === 0 ? (
        <div className="lidarr-empty">
          <LocalizedText source={"No Lidarr-seeded wishlist items yet. Run a sync to populate."} /></div>
      ) : (
        <>
          <Table celled compact size="small" unstackable>
            <Table.Header>
              <Table.Row>
                <Table.HeaderCell><LocalizedText source={"Search"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Filter"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Auto-download"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Last Searched"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Matches"} /></Table.HeaderCell>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {pageItems.map((item) => (
                <Table.Row key={item.id}>
                  <Table.Cell>
                    <Icon
                      name={item.enabled ? 'check circle' : 'circle outline'}
                      color={item.enabled ? 'green' : 'grey'}
                    />
                    {item.searchText}
                  </Table.Cell>
                  <Table.Cell>
                    {item.filter
                      ? <Label size="tiny" color="teal">{item.filter}</Label>
                      : '—'}
                  </Table.Cell>
                  <Table.Cell textAlign="center">
                    <Icon
                      name={item.autoDownload ? 'download' : 'minus'}
                      color={item.autoDownload ? 'green' : 'grey'}
                    />
                  </Table.Cell>
                  <Table.Cell>{formatDate(item.lastSearchedAt)}</Table.Cell>
                  <Table.Cell textAlign="center">
                    {item.lastMatchCount ?? '—'}
                  </Table.Cell>
                </Table.Row>
              ))}
            </Table.Body>
          </Table>

          <div className="lidarr-pagination">
            <span className="lidarr-pagination-info">
              {pageStart}–{pageEnd} <LocalizedText source={"of"} />{" "}{items.length.toLocaleString(getRegionalLocale())}
            </span>
            <Popup
              content={interfaceText("Go to the previous page of Lidarr-seeded wishlist items.")}
              position="top center"
              trigger={
                <span>
                  <Button
                    aria-label={interfaceText("Previous Lidarr wishlist page")}
                    disabled={currentPage <= 1}
                    icon="chevron left"
                    onClick={() => setPage(currentPage - 1)}
                    size="mini"
                   {...interfaceTextProps("Previous Lidarr wishlist page")}/>
                </span>
              }
             {...interfaceTextProps("Go to the previous page of Lidarr-seeded wishlist items.")}/>
            <Popup
              content={interfaceText("Go to the next page of Lidarr-seeded wishlist items.")}
              position="top center"
              trigger={
                <span>
                  <Button
                    aria-label={interfaceText("Next Lidarr wishlist page")}
                    disabled={currentPage >= totalPages}
                    icon="chevron right"
                    onClick={() => setPage(currentPage + 1)}
                    size="mini"
                   {...interfaceTextProps("Next Lidarr wishlist page")}/>
                </span>
              }
             {...interfaceTextProps("Go to the next page of Lidarr-seeded wishlist items.")}/>
          </div>
        </>
      )}
    </div>
  );
};

// ─── Manual import ────────────────────────────────────────────────────────────

const ImportSection = ({ connected, onHistoryChanged }) => {
  useInterfaceLanguage();
  const [directory, setDirectory] = useState('');
  const [importing, setImporting] = useState(false);

  const handleImport = async () => {
    if (!directory.trim()) return;
    setImporting(true);
    try {
      const result = await lidarrAPI.importCompletedDirectory({ directory: directory.trim() });
      const safeCandidates = result?.safeCandidateCount ?? 0;
      if (result?.commandId) {
        toast.success(interfaceText("Lidarr import queued: {safeCandidates} file(s)", { "safeCandidates": (safeCandidates) }));
        setDirectory('');
      } else {
        toast.error(interfaceText('The request failed. Try again.'));
      }
    } catch (err) {
      toast.error(interfaceText("Import failed: {message}", { "message": getApiErrorMessage(err, { t: interfaceText }) }));
    } finally {
      setImporting(false);
      onHistoryChanged?.();
    }
  };

  return (
    <div className="lidarr-section">
      <div className="lidarr-section-header">
        <Header as="h4">
          <Icon name="upload" />
          <Header.Content><LocalizedText source={"Manual Import"} /></Header.Content>
        </Header>
      </div>

      <p style={{ color: '#aaa', marginBottom: '0.75em' }}>
        <LocalizedText source={"Run Lidarr&apos;s manual-import scan for a completed download directory. This works even when automatic import is disabled and can be retried immediately. Only cleanly-matched files (artist + album + tracks resolved, no rejections) are submitted automatically."} /></p>

      <Input
        action={
          <Popup
            content={interfaceText("Ask Lidarr to scan this directory now. Automatic-import settings and the normal retry debounce do not block this manual action.")}
            position="top center"
            trigger={
              <Button
                color="blue"
                content={interfaceText("Run Manual Import")}
                disabled={!connected || !directory.trim() || importing}
                loading={importing}
                onClick={handleImport}
               {...interfaceTextProps("Run Manual Import")}/>
            }
           {...interfaceTextProps("Ask Lidarr to scan this directory now. Automatic-import settings and the normal retry debounce do not block this manual action.")}/>
        }
        disabled={!connected}
        fluid
        onChange={(_, { value }) => setDirectory(value)}
        onKeyDown={(e) => e.key === 'Enter' && handleImport()}
        placeholder="/mnt/datapool_lvm_media/download/music/Artist/Album"
        value={directory}
      />
    </div>
  );
};

// ─── Import history ───────────────────────────────────────────────────────────

const importStatusColor = {
  Queued: 'grey',
  Running: 'blue',
  Successful: 'green',
  Failed: 'red',
  Skipped: 'yellow',
};

const ImportHistorySection = ({ connected, refreshKey }) => {
  useInterfaceLanguage();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [retryingId, setRetryingId] = useState(null);

  const load = useCallback(async () => {
    if (!connected) return;
    setLoading(true);
    try {
      const data = await lidarrAPI.getImportHistory({ limit: 50 });
      setHistory(Array.isArray(data) ? data : []);
    } catch (err) {
      toast.error(interfaceText("Failed to load Lidarr import history: {message}", { "message": getApiErrorMessage(err, { t: interfaceText }) }));
    } finally {
      setLoading(false);
    }
  }, [connected]);

  useEffect(() => {
    if (!connected) return undefined;

    let interval = null;
    const stopPolling = () => {
      if (interval) {
        window.clearInterval(interval);
        interval = null;
      }
    };
    const startPolling = () => {
      if (document.hidden || interval) return;
      load();
      interval = window.setInterval(load, IMPORT_HISTORY_POLL_INTERVAL_MS);
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
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [connected, load, refreshKey]);

  const handleRetry = async (historyId) => {
    setRetryingId(historyId);
    try {
      const result = await lidarrAPI.retryImport(historyId);
      if (result?.commandId) {
        toast.success(interfaceText('Lidarr import queued: {safeCandidates} file(s)', {
          safeCandidates: result.safeCandidateCount ?? 0,
        }));
      } else {
        toast.error(interfaceText('The request failed. Try again.'));
      }
      await load();
    } catch (err) {
      toast.error(interfaceText("Import retry failed: {message}", { "message": getApiErrorMessage(err, { t: interfaceText }) }));
    } finally {
      setRetryingId(null);
    }
  };

  return (
    <div className="lidarr-section">
      <div className="lidarr-section-header">
        <Header as="h4">
          <Icon name="history" />
          <Header.Content>
            <LocalizedText source={"Import History"} />{!loading && (
              <Header.Subheader>{history.length} <LocalizedText source={"recent attempts"} /></Header.Subheader>
            )}
          </Header.Content>
        </Header>
        <Popup
          content={interfaceText("Refresh the recent Lidarr import attempts and their latest command status.")}
          position="top center"
          trigger={
            <Button
              aria-label={interfaceText("Refresh Lidarr import history")}
              icon="refresh"
              loading={loading}
              onClick={load}
              size="mini"
             {...interfaceTextProps("Refresh Lidarr import history")}/>
          }
         {...interfaceTextProps("Refresh the recent Lidarr import attempts and their latest command status.")}/>
      </div>

      {!connected ? (
        <div className="lidarr-empty"><LocalizedText source={"Connect Lidarr to see import history."} /></div>
      ) : loading && history.length === 0 ? (
        <Segment basic padded><Loader active inline="centered" /></Segment>
      ) : history.length === 0 ? (
        <div className="lidarr-empty">
          <LocalizedText source={"No Lidarr imports recorded yet. Run a manual import to start tracking attempts."} /></div>
      ) : (
        <Table celled compact size="small" unstackable>
          <Table.Header>
            <Table.Row>
              <Table.HeaderCell><LocalizedText source={"Status"} /></Table.HeaderCell>
              <Table.HeaderCell><LocalizedText source={"Directory"} /></Table.HeaderCell>
              <Table.HeaderCell><LocalizedText source={"Files"} /></Table.HeaderCell>
              <Table.HeaderCell><LocalizedText source={"Started"} /></Table.HeaderCell>
              <Table.HeaderCell><LocalizedText source={"Finished"} /></Table.HeaderCell>
              <Table.HeaderCell><LocalizedText source={"Details"} /></Table.HeaderCell>
              <Table.HeaderCell><LocalizedText source={"Actions"} /></Table.HeaderCell>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {history.map((entry) => {
              const status = entry.status || 'Queued';
              const canRetry = status === 'Failed' || status === 'Skipped';
              const details = entry.errorMessage || entry.skippedReason
                ? interfaceText('The request failed. Try again.')
                : '—';
              return (
                <Table.Row key={entry.id}>
                  <Table.Cell>
                    <Label color={importStatusColor[status] || 'grey'} size="tiny">
                      {Object.hasOwn(importStatusColor, status)
                        ? <LocalizedText source={status} />
                        : status}
                    </Label>
                  </Table.Cell>
                  <Table.Cell className="lidarr-import-directory" title={entry.directory}>
                    {entry.directory || '—'}
                  </Table.Cell>
                  <Table.Cell>
                    {entry.candidateCount > 0
                      ? `${entry.safeCandidateCount ?? 0}/${entry.candidateCount}`
                      : '—'}
                  </Table.Cell>
                  <Table.Cell>{formatDate(entry.startedAt)}</Table.Cell>
                  <Table.Cell>{formatDate(entry.completedAt)}</Table.Cell>
                  <Table.Cell className="lidarr-import-details" title={details}>
                    {details}
                  </Table.Cell>
                  <Table.Cell textAlign="center">
                    {canRetry && (
                      <Popup
                        content={interfaceText("Run this directory through Lidarr again and record a new import attempt.")}
                        position="top center"
                        trigger={
                          <Button
                            aria-label={interfaceText("Retry Lidarr import for {directory}", { "directory": (entry.directory) })}
                            disabled={retryingId !== null}
                            icon="redo"
                            loading={retryingId === entry.id}
                            onClick={() => handleRetry(entry.id)}
                            size="mini"
                           {...interfaceTextProps("Retry Lidarr import for {directory}")}/>
                        }
                       {...interfaceTextProps("Run this directory through Lidarr again and record a new import attempt.")}/>
                    )}
                  </Table.Cell>
                </Table.Row>
              );
            })}
          </Table.Body>
        </Table>
      )}
    </div>
  );
};

// ─── Root ─────────────────────────────────────────────────────────────────────

const Lidarr = () => {
  useInterfaceLanguage();
  const [status, setStatus] = useState(null);
  const [syncState, setSyncState] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);
  const mountedRef = useRef(false);
  const statusInflightRef = useRef(false);

  const loadStatus = useCallback(async () => {
    if (statusInflightRef.current) return;

    statusInflightRef.current = true;
    try {
      const [s, ss] = await Promise.all([
        lidarrAPI.getStatus(),
        lidarrAPI.getSyncStatus(),
      ]);
      if (mountedRef.current && !document.hidden) {
        setStatus((previous) =>
          areLidarrStatusesEqual(previous, s) ? previous : s,
        );
        setSyncState((previous) =>
          areLidarrSyncStatesEqual(previous, ss) ? previous : ss,
        );
      }
    } catch {
      if (mountedRef.current && !document.hidden) {
        setStatus((previous) => (previous === null ? previous : null));
      }
    } finally {
      statusInflightRef.current = false;
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    let interval = null;

    const stopPolling = () => {
      if (interval) {
        window.clearInterval(interval);
        interval = null;
      }
    };
    const startPolling = () => {
      if (document.hidden || interval) return;

      loadStatus();
      interval = window.setInterval(loadStatus, STATUS_POLL_INTERVAL_MS);
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
      mountedRef.current = false;
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [loadStatus]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const result = await lidarrAPI.syncWanted();
      toast.success(
        `Sync complete — ${result.createdCount ?? 0} added, ` +
        `${result.duplicateCount ?? 0} duplicates, ` +
        `${result.wantedCount ?? 0} total wanted`
      );
      await loadStatus();
    } catch (err) {
      toast.error(interfaceText("Sync failed: {message}", { "message": getApiErrorMessage(err, { t: interfaceText }) }));
    } finally {
      setSyncing(false);
    }
  };

  const connected = !!status?.version;
  const handleHistoryChanged = useCallback(() => {
    setHistoryRefreshKey((key) => key + 1);
  }, []);

  return (
    <div className="lidarr-container">
      <Header as="h2" className="lidarr-header">
        <Icon name="music" />
        <Header.Content>
          <LocalizedText source={"Lidarr"} /><Header.Subheader><LocalizedText source={"Music acquisition via Lidarr"} /></Header.Subheader>
        </Header.Content>
      </Header>

      <StatusBar
        status={status}
        syncState={syncState}
        onSync={handleSync}
        syncing={syncing}
      />

      <WantedSection connected={connected} />

      <WishlistSection />

      <ImportSection
        connected={connected}
        onHistoryChanged={handleHistoryChanged}
      />

      <ImportHistorySection
        connected={connected}
        refreshKey={historyRefreshKey}
      />
    </div>
  );
};

export default Lidarr;
