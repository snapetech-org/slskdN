import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import './Transfers.css';
import * as autoReplaceLibrary from '../../lib/autoReplace';
import { createTransfersHubConnection } from '../../lib/hubFactory';
import * as transfersLibrary from '../../lib/transfers';
import {
  createTransferStore,
  transferKey,
} from '../../lib/transferStore';
import {
  loadTransferViewState,
  saveTransferViewState,
} from '../../lib/transferViewPreferences';
import { PlaceholderSegment } from '../Shared';
import TransferTable from './TransferTable';
import TransfersHeader from './TransfersHeader';
import RequestDetailModal from './RequestDetailModal';

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from 'react';
import { Button, Input, Menu, Popup } from 'semantic-ui-react';
import { toast } from 'react-toastify';

const STATUS_FILTERS = [
  { key: 'all', get label() { return interfaceText("All"); }, match: () => true },
  {
    key: 'active',
    get label() { return interfaceText("Active"); },
    match: (t) => t.state === 'InProgress' || t.state === 'Initializing',
  },
  {
    key: 'queued',
    get label() { return interfaceText("Queued"); },
    match: (t) => String(t.state ?? '').includes('Queued'),
  },
  {
    key: 'completed',
    get label() { return interfaceText("Completed"); },
    match: (t) => t.state === 'Completed, Succeeded',
  },
  {
    key: 'failed',
    get label() { return interfaceText("Failed"); },
    match: (t) =>
      String(t.state ?? '').includes('Completed') &&
      t.state !== 'Completed, Succeeded',
  },
];

const FILTER_HELP_SOURCES = {
  all: 'Show transfers in every status.',
  active: 'Show only active transfers so you can focus on that part of the queue.',
  queued: 'Show only queued transfers so you can focus on that part of the queue.',
  completed: 'Show only completed transfers so you can focus on that part of the queue.',
  failed: 'Show only failed transfers so you can focus on that part of the queue.',
};

const RECONCILE_INTERVAL_MS = 15_000;
const ACTIVE_TRANSFER_PAGE_SIZE = 100;
const HISTORY_PAGE_SIZE = 250;

const getErrorMessage = (error) =>
  getApiErrorMessage(error, { t: interfaceText });

const summarizeBulkFailures = ({ failures }) => {
  if (failures.length === 0) {
    return;
  }

  toast.error(interfaceText('Some transfers could not be updated. Try again.'));
};

const matchesDirection = (transfer, direction) =>
  String(transfer.direction ?? '').toLowerCase() === direction;

const isSucceeded = (state) => state === 'Completed, Succeeded';

const TransferManager = ({ direction, server = { isConnected: true } }) => {
  const { language, t, languageFor, directionFor } = useInterfaceLanguage();
  const localizedText = (source) => (
    <span lang={languageFor(source)} dir={directionFor(source)}>{t(source)}</span>
  );
  const testId = direction === 'download' ? 'downloads-root' : 'uploads-root';

  const storeRef = useRef();
  if (!storeRef.current) {
    storeRef.current = createTransferStore();
  }

  const store = storeRef.current;
  const version = useSyncExternalStore(store.subscribe, store.getVersion);
  const allTransfers = useMemo(
    () => store.getAll(),
    // version is the change signal for the external store snapshot
    [store, version],
  );

  const [activeTab, setActiveTab] = useState(direction);
  const [connecting, setConnecting] = useState(true);
  const [connected, setConnected] = useState(false);
  const [viewState, setViewState] = useState(() => loadTransferViewState(direction));
  const [initialSnapshotLoaded, setInitialSnapshotLoaded] = useState(false);
  const [totalCounts, setTotalCounts] = useState(null);
  const [historyVersion, setHistoryVersion] = useState(0);
  const [searchText, setSearchText] = useState('');
  const [selectedKeys, setSelectedKeys] = useState(() => new Set());

  const [autoReplaceEnabled, setAutoReplaceEnabled] = useState(false);
  const [acceleratedEnabled, setAcceleratedEnabled] = useState(false);

  const [retryingSingle, setRetryingSingle] = useState(false);
  const [cancellingSingle, setCancellingSingle] = useState(false);
  const [removingSingle, setRemovingSingle] = useState(false);
  const [openRequestId, setOpenRequestId] = useState(null);
  const [bulkCounts, setBulkCounts] = useState({
    cancel: 0,
    remove: 0,
    retry: 0,
  });

  const { hideCompleted, statusFilter, sort } = viewState;

  const updateViewState = useCallback((patch) => {
    setViewState((current) => {
      const next = {
        ...current,
        ...patch,
        sort: patch.sort ? { ...current.sort, ...patch.sort } : current.sort,
      };
      saveTransferViewState(activeTab, next);
      return next;
    });
  }, [activeTab]);

  const bulkQueueRef = useRef([]);
  const queuedBulkKeysRef = useRef(new Set());
  const bulkQueueRunningRef = useRef(false);
  const completedHistoryRef = useRef({
    download: { asOf: null, hasMore: true, loading: false, offset: 0 },
    upload: { asOf: null, hasMore: true, loading: false, offset: 0 },
  });
  const activeTransferPagesRef = useRef({
    download: {
      afterId: null,
      afterRequestedAt: null,
      asOf: null,
      hasMore: false,
      loading: false,
    },
    upload: {
      afterId: null,
      afterRequestedAt: null,
      asOf: null,
      hasMore: false,
      loading: false,
    },
  });

  const retrying = retryingSingle || bulkCounts.retry > 0;
  const cancelling = cancellingSingle || bulkCounts.cancel > 0;
  const removing = removingSingle || bulkCounts.remove > 0;

  // Follow the route when it changes (e.g. nav from /downloads to /uploads).
  useEffect(() => {
    setActiveTab(direction);
  }, [direction]);

  useEffect(() => {
    setViewState(loadTransferViewState(activeTab));
    setSearchText('');
    setSelectedKeys(new Set());
  }, [activeTab]);

  // Seed from REST, stream deltas over SignalR, reconcile indexed deltas on a slow timer.
  useEffect(() => {
    let disposed = false;
    let cursor = null;
    let interval = null;
    let pendingEvents = [];
    let reconcileRequest = null;
    let seeded = false;

    const reconcile = () => {
      if (disposed || document.hidden) {
        return Promise.resolve();
      }
      if (reconcileRequest) {
        return reconcileRequest;
      }

      const since = cursor === null ? null : Math.max(0, cursor - 1);
      reconcileRequest = (async () => {
        try {
          if (!seeded) {
            const downloadSnapshot = await transfersLibrary.getChanges({
              direction: 'download',
              limit: ACTIVE_TRANSFER_PAGE_SIZE,
            });
            if (disposed || document.hidden) {
              return;
            }

            const uploadSnapshot = await transfersLibrary.getChanges({
              direction: 'upload',
              limit: ACTIVE_TRANSFER_PAGE_SIZE,
              snapshot: downloadSnapshot.cursor,
            });
            if (disposed || document.hidden) {
              return;
            }

            store.seed([
              ...downloadSnapshot.transfers,
              ...uploadSnapshot.transfers,
            ].filter((transfer) => !transfer.removed));
            activeTransferPagesRef.current.download = {
              afterId: downloadSnapshot.nextAfterId,
              afterRequestedAt: downloadSnapshot.nextAfterRequestedAt,
              asOf: downloadSnapshot.cursor,
              hasMore: downloadSnapshot.hasMore,
              loading: false,
            };
            activeTransferPagesRef.current.upload = {
              afterId: uploadSnapshot.nextAfterId,
              afterRequestedAt: uploadSnapshot.nextAfterRequestedAt,
              asOf: uploadSnapshot.cursor,
              hasMore: uploadSnapshot.hasMore,
              loading: false,
            };
            seeded = true;
            pendingEvents.forEach(({ callback, event }) => callback(event));
            pendingEvents = [];
            cursor = downloadSnapshot.cursor;
            setTotalCounts(downloadSnapshot.counts);
            setInitialSnapshotLoaded(true);
            setHistoryVersion((version) => version + 1);
          } else {
            const snapshot = await transfersLibrary.getChanges({ since });
            if (disposed || document.hidden) {
              return;
            }

            store.applySnapshot(snapshot.transfers);
            if (snapshot.cursor !== null) {
              cursor = Math.max(cursor ?? 0, snapshot.cursor);
            }
            setTotalCounts(snapshot.counts);
          }
        } catch (error) {
          if (!disposed) {
            console.error('transfer reconcile failed', error);
          }
        } finally {
          if (!disposed) {
            setConnecting(false);
          }
        }
      })().finally(() => {
        reconcileRequest = null;
      });

      return reconcileRequest;
    };

    const stopPolling = () => {
      if (interval) {
        window.clearInterval(interval);
        interval = null;
      }
    };

    const startPolling = () => {
      if (disposed || document.hidden || interval) {
        return;
      }

      reconcile();
      interval = window.setInterval(reconcile, RECONCILE_INTERVAL_MS);
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        pendingEvents = [];
        stopPolling();
      } else {
        startPolling();
      }
    };

    const applyWhenVisible = (callback) => (event) => {
      if (!disposed && !document.hidden) {
        if (seeded) {
          callback(event);
        } else {
          pendingEvents.push({ callback, event });
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    const hub = createTransfersHubConnection();
    hub.on('activity', applyWhenVisible(store.applyActivity));
    hub.on('progress', applyWhenVisible(store.applyProgress));
    hub.on('removed', applyWhenVisible(store.applyRemoved));
    hub.onreconnecting(() => {
      if (!disposed) {
        setConnected(false);
      }
    });
    hub.onreconnected(() => {
      if (!disposed) {
        setConnected(true);
        reconcile();
      }
    });
    hub.onclose(() => {
      if (!disposed) {
        setConnected(false);
      }
    });
    hub.start().then(
      () => {
        if (!disposed) {
          setConnected(true);
        }
      },
      () => {
        if (!disposed) {
          setConnected(false);
        }
      },
    );

    startPolling();

    return () => {
      disposed = true;
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      hub.stop();
    };
  }, [store]);

  const loadCompletedHistory = useCallback(async (historyDirection) => {
    const status = completedHistoryRef.current[historyDirection];
    if (document.hidden || status.loading || !status.hasMore) return;

    status.loading = true;
    setHistoryVersion((version) => version + 1);
    try {
      const page = await transfersLibrary.getHistory({
        asOf: status.asOf,
        direction: historyDirection,
        limit: HISTORY_PAGE_SIZE,
        offset: status.offset,
      });
      if (document.hidden) return;

      store.applySnapshot(page.transfers);
      status.asOf = page.asOf;
      status.hasMore = page.hasMore;
      status.offset = page.nextOffset;
    } catch (error) {
      console.error('completed transfer history failed', error);
    } finally {
      status.loading = false;
      setHistoryVersion((version) => version + 1);
    }
  }, [store]);

  const loadMoreActiveTransfers = useCallback(async (pageDirection) => {
    const status = activeTransferPagesRef.current[pageDirection];
    if (document.hidden || status.loading || !status.hasMore) return;

    status.loading = true;
    setHistoryVersion((version) => version + 1);
    try {
      const page = await transfersLibrary.getChanges({
        afterId: status.afterId,
        afterRequestedAt: status.afterRequestedAt,
        direction: pageDirection,
        limit: ACTIVE_TRANSFER_PAGE_SIZE,
        snapshot: status.asOf,
      });
      if (document.hidden) return;

      store.applySnapshot(page.transfers);
      status.afterId = page.nextAfterId;
      status.afterRequestedAt = page.nextAfterRequestedAt;
      status.hasMore = page.hasMore;
    } catch (error) {
      console.error('active transfer page failed', error);
      toast.error(interfaceText('Could not load more transfers'));
    } finally {
      status.loading = false;
      setHistoryVersion((version) => version + 1);
    }
  }, [store]);

  useEffect(() => {
    if (hideCompleted || !initialSnapshotLoaded) return undefined;

    const loadWhenVisible = () => {
      if (!document.hidden) {
        loadCompletedHistory(activeTab);
      }
    };
    document.addEventListener('visibilitychange', loadWhenVisible);
    loadWhenVisible();
    return () => document.removeEventListener('visibilitychange', loadWhenVisible);
  }, [activeTab, hideCompleted, initialSnapshotLoaded, loadCompletedHistory]);

  useEffect(() => {
    const fetchDownloadModeStatus = async () => {
      try {
        const [autoReplaceStatus, acceleratedStatus] = await Promise.all([
          autoReplaceLibrary.getAutoReplaceStatus(),
          transfersLibrary.getAcceleratedMode(),
        ]);
        setAutoReplaceEnabled(autoReplaceStatus?.enabled ?? false);
        setAcceleratedEnabled(acceleratedStatus?.enabled ?? false);
      } catch (error) {
        console.error('Failed to fetch download mode status:', error);
      }
    };

    fetchDownloadModeStatus();
  }, []);

  const changeBulkCount = (action, delta) => {
    setBulkCounts((previous) => ({
      ...previous,
      [action]: Math.max(0, previous[action] + delta),
    }));
  };

  const runBulkQueue = async () => {
    if (bulkQueueRunningRef.current) {
      return;
    }

    bulkQueueRunningRef.current = true;

    while (bulkQueueRef.current.length > 0) {
      const operation = bulkQueueRef.current.shift();

      try {
        await operation.run();
      } catch (error) {
        operation.batch.failures.push({
          label: operation.label,
          message: getErrorMessage(error),
        });
      } finally {
        queuedBulkKeysRef.current.delete(operation.key);
        changeBulkCount(operation.action, -1);
        operation.batch.remaining -= 1;

        if (operation.batch.remaining === 0) {
          summarizeBulkFailures({
            action: operation.batch.action,
            failures: operation.batch.failures,
          });
        }
      }
    }

    bulkQueueRunningRef.current = false;
  };

  const enqueueBulkOperations = ({ action, operations }) => {
    const batch = { action, failures: [], remaining: 0 };
    let enqueued = 0;

    operations.forEach((operation) => {
      if (queuedBulkKeysRef.current.has(operation.key)) {
        return;
      }

      queuedBulkKeysRef.current.add(operation.key);
      bulkQueueRef.current.push({ ...operation, action, batch });
      batch.remaining += 1;
      enqueued += 1;
    });

    if (enqueued === 0) {
      return;
    }

    changeBulkCount(action, enqueued);
    runBulkQueue();
  };

  const retry = async ({
    file,
    suppressErrorToast = false,
    suppressStateChange = false,
  }) => {
    const { filename, size, username } = file;

    try {
      if (!suppressStateChange) {
        setRetryingSingle(true);
      }

      await transfersLibrary.download({
        files: [{ filename, size }],
        username,
      });
    } catch (error) {
      console.error(error);
      if (!suppressErrorToast) {
        toast.error(getErrorMessage(error));
      }

      throw error;
    } finally {
      if (!suppressStateChange) {
        setRetryingSingle(false);
      }
    }
  };

  const cancel = async ({
    file,
    suppressErrorToast = false,
    suppressStateChange = false,
  }) => {
    const { direction: fileDirection, id, username } = file;

    try {
      if (!suppressStateChange) {
        setCancellingSingle(true);
      }

      await transfersLibrary.cancel({
        direction: String(fileDirection ?? activeTab).toLowerCase(),
        id,
        username,
      });
    } catch (error) {
      console.error(error);
      if (!suppressErrorToast) {
        toast.error(getErrorMessage(error));
      }

      throw error;
    } finally {
      if (!suppressStateChange) {
        setCancellingSingle(false);
      }
    }
  };

  const remove = async ({
    deleteFile = false,
    file,
    suppressErrorToast = false,
    suppressStateChange = false,
  }) => {
    const { direction: fileDirection, id, username } = file;

    try {
      if (!suppressStateChange) {
        setRemovingSingle(true);
      }

      await transfersLibrary.cancel({
        deleteFile,
        direction: String(fileDirection ?? activeTab).toLowerCase(),
        id,
        remove: true,
        username,
      });
      // Snappy local removal; the REMOVED hub event and reconcile agree.
      store.removeByKey(transferKey(file));
    } catch (error) {
      console.error(error);
      if (!suppressErrorToast) {
        toast.error(getErrorMessage(error));
      }

      throw error;
    } finally {
      if (!suppressStateChange) {
        setRemovingSingle(false);
      }
    }
  };

  const retryAll = (filesToRetry) => {
    enqueueBulkOperations({
      action: 'retry',
      operations: filesToRetry.map((file) => ({
        key: `retry:${transferKey(file)}`,
        label: `${file.username}/${file.filename}`,
        run: () =>
          retry({
            file,
            suppressErrorToast: true,
            suppressStateChange: true,
          }),
      })),
    });
  };

  const cancelAll = (filesToCancel) => {
    enqueueBulkOperations({
      action: 'cancel',
      operations: filesToCancel.map((file) => ({
        key: `cancel:${transferKey(file)}`,
        label: `${file.username}/${file.filename}`,
        run: () =>
          cancel({
            file,
            suppressErrorToast: true,
            suppressStateChange: true,
          }),
      })),
    });
  };

  const removeAll = (filesToRemove, deleteFile = false, options = {}) => {
    const { useBulkClear = false } = options;

    if (useBulkClear && !deleteFile) {
      enqueueBulkOperations({
        action: 'remove',
        operations: [
          {
            key: `remove:clear-completed:${activeTab}`,
            label: `all completed ${activeTab}s`,
            run: async () => {
              await transfersLibrary.clearCompleted({ direction: activeTab });
              filesToRemove.forEach((file) =>
                store.removeByKey(transferKey(file)),
              );
            },
          },
        ],
      });
      return;
    }

    enqueueBulkOperations({
      action: 'remove',
      operations: filesToRemove.map((file) => ({
        key: `remove:${transferKey(file)}:${deleteFile ? 'delete' : 'keep'}`,
        label: `${file.username}/${file.filename}`,
        run: () =>
          remove({
            deleteFile,
            file,
            suppressErrorToast: true,
            suppressStateChange: true,
          }),
      })),
    });
  };

  const handleAutoReplaceChange = async (enabled) => {
    try {
      if (enabled) {
        await autoReplaceLibrary.enableAutoReplace();
        setAutoReplaceEnabled(true);
        toast.info(
          interfaceText("Auto-replace enabled. Backend will check for stuck downloads periodically."),
        );
      } else {
        await autoReplaceLibrary.disableAutoReplace();
        setAutoReplaceEnabled(false);
        toast.info(
          interfaceText("Auto-replace disabled. Automatic retry is separate; disable transfers.download.auto_retry.enabled to stop retries of failed downloads."),
        );
      }
    } catch (error) {
      console.error('Failed to toggle auto-replace:', error);
      toast.error(interfaceText("Failed to toggle auto-replace"));
    }
  };

  const handleAcceleratedChange = async (enabled) => {
    try {
      const status = await transfersLibrary.setAcceleratedMode({ enabled });
      setAcceleratedEnabled(status?.enabled ?? enabled);
      toast.info(
        enabled
          ? interfaceText('Accelerated mode enabled. Slow or stalled downloads can use verified alternate sources.')
          : interfaceText('Accelerated mode disabled'),
      );
    } catch (error) {
      console.error('Failed to toggle accelerated mode:', error);
      toast.error(interfaceText("Failed to toggle accelerated mode"));
    }
  };

  const loadedCounts = useMemo(() => {
    let download = 0;
    let upload = 0;

    for (const transfer of allTransfers) {
      if (matchesDirection(transfer, 'download')) {
        download += 1;
      } else if (matchesDirection(transfer, 'upload')) {
        upload += 1;
      }
    }

    return { download, upload };
  }, [allTransfers]);

  const counts = totalCounts ?? loadedCounts;

  const tabTransfers = useMemo(
    () => allTransfers.filter((t) => matchesDirection(t, activeTab)),
    [allTransfers, activeTab],
  );

  const visibleTransfers = useMemo(() => {
    if (!hideCompleted) {
      return tabTransfers;
    }

    return tabTransfers.filter((t) => !isSucceeded(t.state));
  }, [tabTransfers, hideCompleted]);

  const filteredTransfers = useMemo(() => {
    const statusMatch =
      STATUS_FILTERS.find((f) => f.key === statusFilter)?.match ?? (() => true);
    const needle = searchText.trim().toLowerCase();

    return visibleTransfers.filter((t) => {
      if (!statusMatch(t)) {
        return false;
      }

      if (!needle) {
        return true;
      }

      return (
        String(t.filename ?? '')
          .toLowerCase()
          .includes(needle) ||
        String(t.username ?? '')
          .toLowerCase()
          .includes(needle)
      );
    });
  }, [visibleTransfers, statusFilter, searchText]);

  const statusCounts = useMemo(() => {
    const result = {};
    for (const filter of STATUS_FILTERS) {
      result[filter.key] = visibleTransfers.filter(filter.match).length;
    }

    return result;
  }, [visibleTransfers]);

  // TransfersHeader derives its bulk-action file lists from a nested
  // (user -> directory -> files) shape; give it a single synthetic group.
  const headerTransfers = useMemo(
    () => [
      {
        username: '',
        directories: [{ directory: '', files: tabTransfers }],
      },
    ],
    [tabTransfers],
  );

  const handleSelectionChange = (file, selected) => {
    setSelectedKeys((previous) => {
      const next = new Set(previous);
      const key = transferKey(file);

      if (selected) {
        next.add(key);
      } else {
        next.delete(key);
      }

      return next;
    });
  };

  const handleSelectAll = (files, selected) => {
    setSelectedKeys((previous) => {
      const next = new Set(previous);

      files.forEach((file) => {
        const key = transferKey(file);
        if (selected) {
          next.add(key);
        } else {
          next.delete(key);
        }
      });

      return next;
    });
  };

  const selectedFiles = useMemo(
    () => filteredTransfers.filter((t) => selectedKeys.has(transferKey(t))),
    [filteredTransfers, selectedKeys],
  );

  const historyStatus = useMemo(
    () => completedHistoryRef.current[activeTab],
    [activeTab, historyVersion],
  );
  const activePageStatus = useMemo(
    () => activeTransferPagesRef.current[activeTab],
    [activeTab, historyVersion],
  );
  const isEmpty = counts[activeTab] === 0;

  return (
    <div data-testid={testId} style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, overflow: 'hidden' }}>
      <Menu
        className="transfer-direction-menu"
        pointing
        secondary
        style={{ marginBottom: 0, minHeight: '36px' }}
      >
        <Menu.Item
          active={activeTab === 'download'}
          onClick={() => setActiveTab('download')}
          style={{ fontSize: '0.85em', padding: '0.4em 0.8em' }}
        >
          {interfaceText("Downloads ({download})", { "download": (counts.download) })}
        </Menu.Item>
        <Menu.Item
          active={activeTab === 'upload'}
          onClick={() => setActiveTab('upload')}
          style={{ fontSize: '0.85em', padding: '0.4em 0.8em' }}
        >
          {interfaceText("Uploads ({upload})", { "upload": (counts.upload) })}
        </Menu.Item>
        <Menu.Menu position="right">
          <Menu.Item
            style={{ fontSize: '0.78em', padding: '0.3em 0.6em' }}
            title={
              connected
                ? interfaceText('Live transfer feed connected')
                : interfaceText('Live feed disconnected — using periodic refresh')
            }
            {...interfaceTextProps(connected
              ? 'Live transfer feed connected'
              : 'Live feed disconnected — using periodic refresh')}
          >
            <span
              className={`transfer-feed-dot ${connected ? 'is-live' : 'is-offline'}`}
            />
            {connected ? <LocalizedText source={"Live"} /> : <LocalizedText source={"Reconnecting"} />}
          </Menu.Item>
        </Menu.Menu>
      </Menu>

      <TransfersHeader
        acceleratedEnabled={acceleratedEnabled}
        autoReplaceEnabled={autoReplaceEnabled}
        cancelling={cancelling}
        direction={activeTab}
        hideCompleted={hideCompleted}
        onAcceleratedChange={handleAcceleratedChange}
        onAutoReplaceChange={handleAutoReplaceChange}
        onCancelAll={cancelAll}
        onHideCompletedChange={(value) => updateViewState({ hideCompleted: value })}
        onRemoveAll={removeAll}
        onRetryAll={retryAll}
        removing={removing}
        retrying={retrying}
        server={server}
        totalCount={counts[activeTab]}
        transfers={headerTransfers}
      />

      {!isEmpty && (
        <div className="transfer-filter-bar">
          <div className="transfer-loaded-note" role="status">
            <LocalizedText
              source="Loaded {loadedCount} of {totalCount} transfers. Filters and queue actions apply to loaded rows; completed-transfer removal applies server-wide."
              values={{ loadedCount: tabTransfers.length, totalCount: counts[activeTab] }}
            />
          </div>
          <div className="transfer-filter-chips">
            {STATUS_FILTERS.map((filter) => (
              <Popup
                content={interfaceText(FILTER_HELP_SOURCES[filter.key])}
                key={filter.key}
                {...interfaceTextProps(FILTER_HELP_SOURCES[filter.key])}
                trigger={(
                  <button
                    className={`transfer-chip${
                      statusFilter === filter.key ? ' is-active' : ''
                    }`}
                    onClick={() => updateViewState({ statusFilter: filter.key })}
                    type="button"
                    lang={languageFor(filter.label)}
                    dir={directionFor(filter.label)}
                  >
                    {`${t(filter.label)} (${statusCounts[filter.key] ?? 0})`}
                  </button>
                )}
              />
            ))}
          </div>
          <Input
            className="transfer-filter-search"
            icon="search"
            onChange={(_, data) => setSearchText(data.value)}
            placeholder={t('Filter by name or peer…')}
            lang={language}
            dir={language === 'ar' ? 'rtl' : 'ltr'}
            size="small"
            value={searchText}
          />
          {!hideCompleted && historyStatus.hasMore && (
            <Popup
              content={interfaceText("Load the next 250 successful transfers from the server without loading the entire history.")}
              trigger={
                <Button
                  content={t('Load older completed')}
                  lang={languageFor('Load older completed')}
                  dir={directionFor('Load older completed')}
                  disabled={historyStatus.loading}
                  icon="history"
                  loading={historyStatus.loading}
                  onClick={() => loadCompletedHistory(activeTab)}
                  size="small"
                />
              }
             {...interfaceTextProps("Load the next 250 successful transfers from the server without loading the entire history.")}/>
          )}
          {activePageStatus.hasMore && (
            <Popup
              content={interfaceText('Load the next 100 active and unsuccessful transfer records from the server. Selection and live updates are retained as more rows arrive.')}
              trigger={(
                <Button
                  content={t('Load more transfers')}
                  lang={languageFor('Load more transfers')}
                  dir={directionFor('Load more transfers')}
                  disabled={activePageStatus.loading}
                  icon="ellipsis horizontal"
                  loading={activePageStatus.loading}
                  onClick={() => loadMoreActiveTransfers(activeTab)}
                  size="small"
                />
              )}
             {...interfaceTextProps('Load the next 100 active and unsuccessful transfer records from the server. Selection and live updates are retained as more rows arrive.')}
            />
          )}
        </div>
      )}

      {isEmpty ? (
        <PlaceholderSegment
          caption={
            connecting
              ? localizedText(activeTab === 'download' ? 'Loading downloads' : 'Loading uploads')
              : localizedText(activeTab === 'download' ? 'No downloads to display' : 'No uploads to display')
          }
          icon={activeTab}
        />
      ) : filteredTransfers.length === 0 ? (
        <PlaceholderSegment
          caption={
            searchText.trim() || statusFilter !== 'all'
              ? localizedText('No transfers match the current filter')
              : hideCompleted
                ? localizedText('Completed transfers are hidden')
              : historyStatus.loading
                ? localizedText('Loading completed history')
                : localizedText('All loaded transfers are complete')
          }
          icon={searchText.trim() || statusFilter !== 'all' ? 'filter' : 'check'}
        />
      ) : (
        <TransferTable
          direction={activeTab}
          onCancel={(file) => cancel({ file })}
          onRemove={(file) => remove({ file })}
          onRetry={(file) => retry({ file }).catch(() => {})}
          onOpenRequest={(requestId) => setOpenRequestId(requestId)}
          onSelectAll={handleSelectAll}
          onSelectionChange={handleSelectionChange}
          onCancelSelected={() => cancelAll(selectedFiles)}
          onRemoveSelected={() => removeAll(selectedFiles)}
          onRetrySelected={() => retryAll(selectedFiles)}
          selectedKeys={selectedKeys}
          selectedFiles={selectedFiles}
          sort={sort}
          onSortChange={(nextSort) => updateViewState({ sort: nextSort })}
          transfers={filteredTransfers}
        />
      )}
      <RequestDetailModal
        onClose={() => setOpenRequestId(null)}
        open={Boolean(openRequestId)}
        requestId={openRequestId}
      />
    </div>
  );
};

export default TransferManager;
