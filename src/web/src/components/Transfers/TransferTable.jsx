import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getRegionalLocale, useRegionalLocale } from '../../lib/regionalFormat';
import {
  formatTransferState,
  getFailureReason,
  isStateCancellable,
  isStateRemovable,
  isStateRetryable,
} from '../../lib/transfers';
import { transferKey } from '../../lib/transferStore';
import {
  formatBytes,
  formatBytesAsUnit,
  formatSeconds,
  getExtension,
  getDirectoryName,
  getFileName,
} from '../../lib/util';
import {
  ALL_COLUMNS,
  columnMinWidth,
  defaultColumnWidths,
  loadColumnState,
  saveColumnState,
  visibleColumnDefinitions,
} from '../../lib/transferColumns';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button, Checkbox, Dropdown, Icon, Popup } from 'semantic-ui-react';
import { List } from 'react-window';

const ROW_HEIGHT = 28;
const CHECKBOX_WIDTH = 28;
const RESIZE_HANDLE = 6;

const stateColor = (state) => {
  switch (state) {
    case 'InProgress':                         return 'blue';
    case 'Completed, Succeeded':                return 'green';
    case 'Requested': case 'Queued':
    case 'Queued, Locally': case 'Queued, Remotely': return 'neutral';
    case 'Initializing':                       return 'teal';
    default:                                   return 'red';
  }
};

const formatSize = ({ bytesTransferred, size }) => {
  const [s, unit] = formatBytes(size ?? 0, 1).split(' ');
  const t = formatBytesAsUnit(bytesTransferred ?? 0, unit, 1);
  return `${t} / ${s} ${unit}`;
};

const formatEta = (transfer) => {
  if (transfer.state !== 'InProgress') return '-';
  const ms = transfer.remainingTime;
  if (ms === null || ms === undefined || ms <= 0) return '-';
  return formatSeconds(Math.round(ms / 1_000));
};

const formatClock = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '-' : date.toLocaleTimeString(getRegionalLocale());
};

const formatElapsed = (ms) => {
  if (!ms || ms <= 0) return '-';
  return formatSeconds(Math.round(ms / 1000));
};

const getRemoteDirectory = (filename) => getDirectoryName(filename || '') || '-';

const INTERACTIVE_SELECTOR = 'button, a, input, label, .ui.checkbox, .ui.dropdown';

function cellContent(transfer, key) {
  switch (key) {
    case 'extension':
      return (
        <span className="transfer-state-pill" style={{ fontSize: '0.78em', textTransform: 'uppercase' }}>
          {getExtension(transfer.filename) || '-'}
        </span>
      );
    case 'directory':
      return (
        <span style={{ fontSize: '0.85em', opacity: 0.8, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
              title={transfer.filename}>
          {getRemoteDirectory(transfer.filename)}
        </span>
      );
    case 'local':
      return (
        <span style={{ fontSize: '0.85em', opacity: 0.8, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
              title={transfer.localFilename || transfer.destinationDirectory || ''}>
          {transfer.localFilename || transfer.destinationDirectory || '-'}
        </span>
      );
    case 'artist':
      return <span title={transfer.artist || ''}>{transfer.artist || '-'}</span>;
    case 'album':
      return <span title={transfer.album || ''}>{transfer.album || '-'}</span>;
    case 'title':
      return <span title={transfer.title || ''}>{transfer.title || '-'}</span>;
    case 'track':
      return <span style={{ fontVariantNumeric: 'tabular-nums' }}>{transfer.trackNumber || '-'}</span>;
    case 'year':
      return <span style={{ fontVariantNumeric: 'tabular-nums' }}>{transfer.year || '-'}</span>;
    case 'elapsed':
      return <span style={{ fontVariantNumeric: 'tabular-nums' }}>{formatElapsed(transfer.elapsedTime)}</span>;
    case 'remaining':
      return <span style={{ fontVariantNumeric: 'tabular-nums' }}>{transfer.bytesRemaining != null ? formatBytes(transfer.bytesRemaining) : '-'}</span>;
    case 'requested': {
      const requestedAt = transfer.requestedAt || transfer.enqueuedAt || transfer.startTime || transfer.endTime;
      return <span>{requestedAt ? new Date(requestedAt).toLocaleString(getRegionalLocale()) : '-'}</span>;
    }
    case 'started':
      return <span style={{ fontSize: '0.85em' }}>{transfer.startTime ? new Date(transfer.startTime).toLocaleString(getRegionalLocale()) : '-'}</span>;
    case 'completed':
      return <span style={{ fontSize: '0.85em' }}>{transfer.endTime ? new Date(transfer.endTime).toLocaleString(getRegionalLocale()) : '-'}</span>;
    case 'bitrate':
      return <span style={{ fontVariantNumeric: 'tabular-nums' }}>{transfer.bitRate ? <LocalizedText source={"{bitRate} kbps"} values={{ "bitRate": (transfer.bitRate) }} /> : '-'}</span>;
    case 'samplerate':
      return <span style={{ fontVariantNumeric: 'tabular-nums' }}>{transfer.sampleRate ? `${(transfer.sampleRate / 1000).toFixed(1)} kHz` : '-'}</span>;
    case 'length':
      return <span style={{ fontVariantNumeric: 'tabular-nums' }}>{transfer.length ? formatSeconds(transfer.length) : '-'}</span>;
    default:
      return null;
  }
}

const Row = React.memo(({ index, style, ...data }) => {
  useInterfaceLanguage();
  const {
    onCancel, onRemove, onRetry, onOpenRequest,
    onSelectionChange, selectedKeys, transfers,
    cols: columnOrder, widths, direction,
  } = data;
  const transfer = transfers[index];
  const key = transferKey(transfer);
  const selected = selectedKeys.has(key);
  const inProgress = transfer.state === 'InProgress';
  const color = stateColor(transfer.state);
  const retryable = direction === 'download' && isStateRetryable(transfer.state);
  const cancellable = Boolean(isStateCancellable(transfer.state));
  const removable = isStateRemovable(transfer.state);
  const attempts = transfer.attempts ?? 1;
  const nextAttempt = formatClock(transfer.nextAttemptAt);

  const toggleSelection = () => onSelectionChange(transfer, !selected);
  const handleRowClick = (event) => {
    if (event.target.closest(INTERACTIVE_SELECTOR)) return;
    toggleSelection();
  };
  const handleRowKeyDown = (event) => {
    if (event.target !== event.currentTarget) return;
    if (event.key === ' ' || event.key === 'Enter') {
      event.preventDefault();
      toggleSelection();
    }
  };

  const cols = columnOrder.map((k) => `${widths[k] || 60}px`);
  const template = `${CHECKBOX_WIDTH}px ${cols.join(' ')} 100px`;

  return (
    <div
      aria-selected={selected}
      className={`transfer-row ${index % 2 === 0 ? 'is-even' : 'is-odd'}${selected ? ' is-selected' : ''}`}
      onClick={handleRowClick}
      onKeyDown={handleRowKeyDown}
      role="row"
      style={{ ...style, gridTemplateColumns: template }}
      tabIndex={0}
    >
      <div className="transfer-cell transfer-cell-check" role="gridcell">
        <Checkbox
          aria-label={`Select ${getFileName(transfer.filename)}`}
          checked={selected}
          fitted
          onChange={(_, d) => onSelectionChange(transfer, d.checked)}
          style={{ transform: 'scale(0.85)' }}
        />
      </div>
      {columnOrder.map((k) => (
        <div key={k}
          className={`transfer-cell ${k === 'name' ? 'transfer-cell-name' : ''} ${['progress','speed','eta','elapsed','remaining','size','bitrate','samplerate','length','track','year'].includes(k) ? 'transfer-cell-num' : ''}`}
          data-colkey={k}
          role="gridcell"
          title={transfer.filename}
        >
          {k === 'name' && (
            <div className="transfer-cell-name-stack">
              <span className="transfer-cell-name-primary">{getFileName(transfer.filename)}</span>
              {(transfer.artist || transfer.title) && (
                <span className="transfer-cell-name-secondary" title={[transfer.artist, transfer.album, transfer.title].filter(Boolean).join(' — ')}>
                  {[transfer.artist, transfer.title].filter(Boolean).join(' — ')}
                </span>
              )}
            </div>
          )}
          {k === 'peer' && (
            <div className="transfer-cell-peer">
              <span className="transfer-peer-name">{transfer.username}</span>
              <Popup
                content={interfaceText("Open this peer's shared files in the Browse view.")}
                position="top center"
                trigger={
                  <Button
                    aria-label={interfaceText("Browse {username} files", { "username": (transfer.username) })}
                    as={Link} compact icon="folder open" size="mini"
                    state={{ user: transfer.username }}
                    style={{ fontSize: '0.65rem', padding: '2px 4px' }}
                    to={`/browse?user=${encodeURIComponent(transfer.username)}`}
                   {...interfaceTextProps("Browse {username} files")}/>
                }
               {...interfaceTextProps("Open this peer's shared files in the Browse view.")}/>
            </div>
          )}
          {k === 'size' && <span>{formatSize(transfer)}</span>}
          {k === 'progress' && inProgress && (
            <div className="transfer-progress">
              <div className="transfer-progress-track">
                <div className="transfer-progress-fill" style={{ width: `${Math.min(100, Math.round(transfer.percentComplete ?? 0))}%` }} />
              </div>
              <span className="transfer-progress-label">{`${Math.round(transfer.percentComplete ?? 0)}%`}</span>
            </div>
          )}
          {k === 'progress' && !inProgress && (
            <Popup
              content={transfer.exception ? getFailureReason(transfer.exception) || transfer.exception : null}
              disabled={!transfer.exception}
              inverted position="top left"
              trigger={
                <span className={`transfer-state-pill transfer-state-${color}`}>
                  <LocalizedTransferState state={transfer.state} exception={transfer.exception} />
                  {transfer.placeInQueue ? <LocalizedText source={"(#{placeInQueue})"} values={{ "placeInQueue": (transfer.placeInQueue) }} /> : ''}
                </span>
              }
            />
          )}
          {k === 'speed' && <span>{inProgress && transfer.averageSpeed ? `${formatBytes(transfer.averageSpeed)}/s` : '-'}</span>}
          {k === 'eta' && <span>{formatEta(transfer)}</span>}
          {k === 'state' && (
            <div className="transfer-cell-state">
              <span className={`transfer-state-pill transfer-state-${color}`}>
                <LocalizedTransferState state={transfer.state} exception={transfer.exception} />
              </span>
              {attempts > 1 && (
                <span className="transfer-retry-badge">
                  <Icon name="redo" />{attempts}
                </span>
              )}
              {nextAttempt && transfer.nextAttemptAt && !retryable && (
                <span className="transfer-next-attempt">{interfaceText("↻ {nextAttempt}", { "nextAttempt": (nextAttempt) })}</span>
              )}
            </div>
          )}
          {cellContent(transfer, k)}
        </div>
      ))}
      <div className="transfer-cell transfer-cell-actions" role="gridcell">
        {transfer.requestId && onOpenRequest && (
          <Popup
            content={interfaceText("Open the originating request to review its name and history.")}
            position="top center"
            trigger={
              <Button aria-label={interfaceText("Open originating request")} icon="info" onClick={() => onOpenRequest(transfer.requestId)} size="mini" style={{ fontSize: '0.65rem', padding: '2px 6px' }}  {...interfaceTextProps("Open originating request")}/>
            }
           {...interfaceTextProps("Open the originating request to review its name and history.")}/>
        )}
        {retryable && (
          <Popup
            content={interfaceText("Retry this failed transfer.")}
            position="top center"
            trigger={
              <Button aria-label={interfaceText("Retry transfer")} color="green" icon="redo" onClick={() => onRetry(transfer)} size="mini" style={{ fontSize: '0.65rem', padding: '2px 6px' }}  {...interfaceTextProps("Retry transfer")}/>
            }
           {...interfaceTextProps("Retry this failed transfer.")}/>
        )}
        {cancellable && (
          <Popup
            content={interfaceText("Cancel this transfer while it is in progress or queued.")}
            position="top center"
            trigger={
              <Button aria-label={interfaceText("Cancel transfer")} color="red" icon="x" onClick={() => onCancel(transfer)} size="mini" style={{ fontSize: '0.65rem', padding: '2px 6px' }}  {...interfaceTextProps("Cancel transfer")}/>
            }
           {...interfaceTextProps("Cancel this transfer while it is in progress or queued.")}/>
        )}
        {removable && (
          <Popup
            content={interfaceText("Remove this transfer from the list without changing the source file.")}
            position="top center"
            trigger={
              <Button aria-label={interfaceText("Remove transfer")} icon="trash alternate" onClick={() => onRemove(transfer)} size="mini" style={{ fontSize: '0.65rem', padding: '2px 6px' }}  {...interfaceTextProps("Remove transfer")}/>
            }
           {...interfaceTextProps("Remove this transfer from the list without changing the source file.")}/>
        )}
      </div>
    </div>
  );
});
Row.displayName = 'TransferTableRow';

const LocalizedTransferState = ({ state, exception }) => {
  const source = formatTransferState(state, exception);
  const rejectedMatch = source.match(/^Rejected \((.*)\)$/);
  if (rejectedMatch) return <LocalizedText source="Rejected ({reason})" values={{ reason: rejectedMatch[1] }} />;
  return <LocalizedText source={source} />;
};

const TransferTable = ({
  direction,
  onCancel, onCancelSelected,
  onRemove, onRemoveSelected,
  onRetry, onRetrySelected,
  onOpenRequest,
  onSelectAll,
  onSelectionChange,
  selectedFiles, selectedKeys,
  transfers,
  sort: controlledSort,
  onSortChange,
}) => {
  useInterfaceLanguage();
  const regionalLocale = useRegionalLocale();
  const [colState, setColState] = useState(() => loadColumnState(direction));
  const [localSort, setLocalSort] = useState({ direction: 'descending', key: 'requested' });

  useEffect(() => {
    setColState(loadColumnState(direction));
  }, [direction]);

  const persistAndSave = useCallback((updater) => {
    setColState((prev) => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      saveColumnState(direction, next);
      return next;
    });
  }, [direction]);

  const toggleVisible = useCallback((key) => {
    persistAndSave((prev) => ({
      ...prev,
      visible: { ...prev.visible, [key]: !prev.visible[key] },
    }));
  }, [persistAndSave]);

  const setColumnWidth = useCallback((key, width) => {
    persistAndSave((prev) => ({
      ...prev,
      widths: {
        ...prev.widths,
        [key]: Math.max(columnMinWidth(key), width),
      },
    }));
  }, [persistAndSave]);

  const resetWidths = useCallback(() => {
    persistAndSave((prev) => ({
      ...prev,
      widths: defaultColumnWidths(),
    }));
  }, [persistAndSave]);

  const startDragRef = useRef(null);

  const handleDragStart = useCallback((event, key) => {
    startDragRef.current = key;
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', key);
  }, []);

  const handleDragOver = useCallback((event) => {
    event.preventDefault();
  }, []);

  const handleDrop = useCallback((event) => {
    event.preventDefault();
    const from = startDragRef.current;
    const to = event.currentTarget.dataset.colkey;
    if (!from || !to || from === to) return;
    persistAndSave((prev) => {
      const order = [...prev.order];
      const i = order.indexOf(from);
      const j = order.indexOf(to);
      if (i < 0 || j < 0) return prev;
      order.splice(i, 1);
      order.splice(j, 0, from);
      return { ...prev, order };
    });
  }, [persistAndSave]);

  const toggleSort = useCallback((key) => {
    const nextSort = (controlledSort ?? localSort).key === key
      ? {
        ...(controlledSort ?? localSort),
        direction: (controlledSort ?? localSort).direction === 'ascending' ? 'descending' : 'ascending',
      }
      : { direction: 'ascending', key };
    if (onSortChange) {
      onSortChange(nextSort);
    } else {
      setLocalSort(nextSort);
    }
  }, [controlledSort, localSort, onSortChange]);

  const sort = controlledSort ?? localSort;

  const visibleCols = visibleColumnDefinitions(colState);
  const keys = visibleCols.map((column) => column.key);
  const headerTemplate = `${CHECKBOX_WIDTH}px ${keys.map((k) => `${colState.widths[k] || 60}px`).join(' ')} 100px`;

  const sortValue = useCallback((transfer, k) => {
    switch (k) {
      case 'name':       return (getFileName(transfer.filename) ?? '').toLowerCase();
      case 'peer':       return (transfer.username ?? '').toLowerCase();
      case 'extension':  return getExtension(transfer.filename)?.toLowerCase() ?? '';
      case 'directory':  return (transfer.filename ?? '').toLowerCase();
      case 'local':      return (transfer.localFilename ?? transfer.destinationDirectory ?? '').toLowerCase();
      case 'artist':     return (transfer.artist ?? '').toLowerCase();
      case 'album':      return (transfer.album ?? '').toLowerCase();
      case 'title':      return (transfer.title ?? '').toLowerCase();
      case 'track':      return transfer.trackNumber ?? 0;
      case 'year':       return transfer.year ?? 0;
      case 'size':       return transfer.size ?? 0;
      case 'progress':   return transfer.percentComplete ?? 0;
      case 'speed':      return transfer.state === 'InProgress' ? transfer.averageSpeed ?? 0 : -1;
      case 'eta':        return transfer.state === 'InProgress' ? transfer.remainingTime ?? Number.MAX_SAFE_INTEGER : Number.MAX_SAFE_INTEGER;
      case 'state':      return (transfer.state ?? '').toLowerCase();
      case 'elapsed':    return transfer.elapsedTime ?? 0;
      case 'remaining':  return transfer.bytesRemaining ?? 0;
      case 'requested':  return new Date(transfer.requestedAt || transfer.enqueuedAt || transfer.startTime || transfer.endTime || 0).getTime();
      case 'started':    return transfer.startTime ? new Date(transfer.startTime).getTime() : 0;
      case 'completed':  return transfer.endTime ? new Date(transfer.endTime).getTime() : 0;
      case 'bitrate':    return transfer.bitRate ?? 0;
      case 'samplerate': return transfer.sampleRate ?? 0;
      case 'length':     return transfer.length ?? 0;
      default:           return 0;
    }
  }, []);

  const sorted = useMemo(() => {
    const rows = [...transfers];
    rows.sort((a, b) => {
      const av = sortValue(a, sort.key);
      const bv = sortValue(b, sort.key);
      if (av < bv) return sort.direction === 'ascending' ? -1 : 1;
      if (av > bv) return sort.direction === 'ascending' ? 1 : -1;
      return 0;
    });
    return rows;
  }, [transfers, sort, sortValue]);

  const allSelected = sorted.length > 0 && sorted.every((t) => selectedKeys.has(transferKey(t)));

  const itemData = useMemo(() => ({
    onCancel, onRemove, onRetry, onOpenRequest,
    onSelectionChange, selectedKeys,
    transfers: sorted,
    direction,
    regionalLocale,
    cols: keys, widths: colState.widths,
  }), [onCancel, onRemove, onRetry, onOpenRequest, onSelectionChange, selectedKeys, sorted, direction, regionalLocale, keys, colState.widths]);

  const gridRef = useRef(null);
  const [gridHeight, setGridHeight] = useState(400);

  useEffect(() => {
    const grid = gridRef.current;
    if (!grid) return;
    const measure = () => {
      const gridRect = grid.getBoundingClientRect();
      const header = grid.querySelector('.transfer-header-row');
      const headerHeight = header ? header.getBoundingClientRect().height : 30;
      const available = gridRect.height - headerHeight;
      if (available > 0) setGridHeight(available);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(grid);
    return () => observer.disconnect();
  }, []);

  const listHeight = Math.max(ROW_HEIGHT, Math.min(gridHeight, sorted.length * ROW_HEIGHT));

  const handleResizeMouseDown = useCallback((event, key) => {
    event.preventDefault();
    event.stopPropagation();
    const startX = event.clientX;
    const startWidth = colState.widths[key] || 60;
    const onMove = (ev) => { setColumnWidth(key, startWidth + ev.clientX - startX); };
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [colState.widths, setColumnWidth]);

  const chooserOptions = ALL_COLUMNS
    .filter((c) => !c.fixed)
    .map((c) => ({
      key: c.key,
      text: interfaceText(c.label),
      icon: colState.visible[c.key] ? 'checkmark' : undefined,
      onClick: () => toggleVisible(c.key),
    }));

  const hasSelection = selectedFiles.length > 0;

  return (
    <div
      aria-label={interfaceText("Transfer table. Use the Left and Right Arrow keys to view all columns.")}
      className="transfer-table-wrapper"
      onKeyDown={(event) => {
        if (event.target !== event.currentTarget) return;
        if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
        event.preventDefault();
        const direction = event.key === 'ArrowRight' ? 1 : -1;
        event.currentTarget.scrollLeft += direction * Math.max(
          80,
          Math.floor(event.currentTarget.clientWidth * 0.8),
        );
      }}
      role="region"
      tabIndex={0}
     {...interfaceTextProps("Transfer table. Use the Left and Right Arrow keys to view all columns.")}>
      {hasSelection && (
        <div className="transfer-bulk-bar">
          <span>{interfaceText("{length} selected", { "length": (selectedFiles.length) })}</span>
          <Button.Group size="small">
            {direction === 'download' && (
              <Popup
                content={interfaceText("Retry all {length} selected transfers.", { "length": (selectedFiles.length) })}
                position="top center"
                trigger={<Button color="green" content={interfaceText("Retry")} icon="redo" onClick={onRetrySelected}  {...interfaceTextProps("Retry")}/>}
               {...interfaceTextProps("Retry all {length} selected transfers.")}/>
            )}
            <Popup
              content={interfaceText("Cancel all {length} selected transfers.", { "length": (selectedFiles.length) })}
              position="top center"
              trigger={<Button color="red" content={interfaceText("Cancel")} icon="x" onClick={onCancelSelected}  {...interfaceTextProps("Cancel")}/>}
             {...interfaceTextProps("Cancel all {length} selected transfers.")}/>
            <Popup
              content={interfaceText("Remove all {length} selected transfers from the list.", { "length": (selectedFiles.length) })}
              position="top center"
              trigger={<Button content={interfaceText("Remove")} icon="trash alternate" onClick={onRemoveSelected}  {...interfaceTextProps("Remove")}/>}
             {...interfaceTextProps("Remove all {length} selected transfers from the list.")}/>
          </Button.Group>
        </div>
      )}
      <div aria-label={interfaceText("Transfers")} aria-rowcount={sorted.length} className="transfer-grid" ref={gridRef} role="grid" {...interfaceTextProps("Transfers")}>
        <div className="transfer-header-row" role="row" style={{ gridTemplateColumns: headerTemplate, display: 'grid' }}>
          <div className="transfer-cell transfer-cell-check" role="columnheader">
            <Checkbox
              aria-label={interfaceText("Select all transfers")}
              checked={allSelected}
              fitted
              onChange={(_, d) => onSelectAll(sorted, d.checked)}
              style={{ transform: 'scale(0.85)' }}
             {...interfaceTextProps("Select all transfers")}/>
          </div>
          {visibleCols.map((col) => {
            const isSorted = sort.key === col.key;
            return (
              <div
                aria-sort={col.sortable ? (isSorted ? sort.direction : 'none') : undefined}
                className={`transfer-cell transfer-header-cell${col.sortable ? ' is-sortable' : ''}`}
                key={col.key}
                data-colkey={col.key}
                draggable
                role="columnheader"
                style={{ position: 'relative' }}
                onClick={() => col.sortable && toggleSort(col.key)}
                onDragStart={(e) => handleDragStart(e, col.key)}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <LocalizedText source={col.label} />
                  {isSorted && <Icon name={sort.direction === 'ascending' ? 'caret up' : 'caret down'} />}
                </span>
                <div
                  aria-label={interfaceText("Resize {label} column", { "label": interfaceText(col.label || col.key) })}
                  className="resize-handle"
                  role="separator"
                  style={{
                    position: 'absolute', top: 0, right: -3, bottom: 0, width: RESIZE_HANDLE,
                    cursor: 'col-resize', zIndex: 10,
                  }}
                  tabIndex={0}
                  onClick={(e) => e.stopPropagation()}
                  onMouseDown={(e) => handleResizeMouseDown(e, col.key)}
                />
              </div>
            );
          })}
          <div className="transfer-cell transfer-column-tools" role="columnheader">
            <Popup
              content={interfaceText("Reset all transfer column widths to their defaults.")}
              position="top center"
              trigger={
                <Button
                  aria-label={interfaceText("Reset transfer column widths")}
                  compact
                  icon="undo"
                  onClick={resetWidths}
                  size="mini"
                  style={{ fontSize: '0.65rem', margin: 0, padding: '2px 4px' }}
                  type="button"
                 {...interfaceTextProps("Reset transfer column widths")}/>
              }
             {...interfaceTextProps("Reset all transfer column widths to their defaults.")}/>
            <Popup
              content={interfaceText("Choose which transfer columns are visible; your order and widths remain saved for this direction.")}
              trigger={
                <Button
                  aria-label={interfaceText("Choose transfer table columns")}
                  compact
                  icon="columns"
                  size="mini"
                  style={{ fontSize: '0.65rem', margin: 0, padding: '2px 4px' }}
                 {...interfaceTextProps("Choose transfer table columns")}/>
              }
              flowing
              on="click"
              pinned
             {...interfaceTextProps("Choose which transfer columns are visible; your order and widths remain saved for this direction.")}>
              <Popup.Content>
                <Dropdown.Menu style={{ maxHeight: 300, overflowY: 'auto' }}>
                  {chooserOptions.map((opt) => (
                    <Dropdown.Item key={opt.key} text={opt.text} icon={opt.icon} onClick={opt.onClick} />
                  ))}
                </Dropdown.Menu>
              </Popup.Content>
            </Popup>
          </div>
        </div>
        <List
          overscanCount={8}
          rowComponent={Row}
          rowCount={sorted.length}
          rowHeight={ROW_HEIGHT}
          rowProps={itemData}
          style={{ height: listHeight, width: '100%' }}
        />
      </div>
    </div>
  );
};

export default TransferTable;
