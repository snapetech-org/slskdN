import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
import '../System.css';
import { createLogsHubConnection } from '../../../lib/hubFactory';
import { downloadLogFile, getLogFile, getLogFiles } from '../../../lib/logs';
import { downloadFile, formatBytes, formatDate } from '../../../lib/util';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Button,
  ButtonGroup,
  Header,
  Icon,
  Message,
  Modal,
  Popup,
  Table,
} from 'semantic-ui-react';

const maxLogs = 500;

const filters = [
  {
    accessibleName: 'Show all severities',
    get description() { return interfaceText("Show every severity so you can inspect the full live log feed."); },
    get label() { return interfaceText("All"); },
    level: 'all',
  },
  {
    accessibleName: 'Show information logs',
    color: 'blue',
    get description() { return interfaceText("Show informational records to follow normal application activity."); },
    get label() { return interfaceText("Info"); },
    level: 'Information',
  },
  {
    accessibleName: 'Show warning logs',
    color: 'yellow',
    get description() { return interfaceText("Show warnings to review conditions that may need attention."); },
    get label() { return interfaceText("Warn"); },
    level: 'Warning',
  },
  {
    accessibleName: 'Show error logs',
    color: 'red',
    get description() { return interfaceText("Show errors to focus on failed operations and their causes."); },
    get label() { return interfaceText("Error"); },
    level: 'Error',
  },
  {
    accessibleName: 'Show debug logs',
    get description() { return interfaceText("Show debug records when investigating detailed application behavior."); },
    get label() { return interfaceText("Debug"); },
    level: 'Debug',
  },
];

const levels = {
  Debug: 'DBG',
  Error: 'ERR',
  Information: 'INF',
  Warning: 'WRN',
};

const getErrorMessage = (error, fallback) =>
  getApiErrorMessage(error, { t: interfaceText }, fallback);

const formatTimestamp = (timestamp) => {
  const date = new Date(timestamp);
  return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
};

const Logs = () => {
  useInterfaceLanguage();
  const [logs, setLogs] = useState([]);
  const [filterLevel, setFilterLevel] = useState('all');
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [connectionError, setConnectionError] = useState('');
  const [connectionAttempt, setConnectionAttempt] = useState(0);
  const [view, setView] = useState('live');
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const [historyAttempt, setHistoryAttempt] = useState(0);
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState('');
  const previewRequestId = useRef(0);

  useEffect(() => () => { previewRequestId.current += 1; }, []);

  useEffect(() => {
    if (view !== 'live') return undefined;

    let active = true;
    const logsHub = createLogsHubConnection();

    logsHub.on('buffer', (buffer) => {
      if (!active) return;

      setLogs(Array.isArray(buffer) ? [...buffer].reverse().slice(0, maxLogs) : []);
      setConnectionStatus('connected');
      setConnectionError('');
    });

    logsHub.on('log', (log) => {
      if (!active) return;

      setLogs((current) => [log, ...current].slice(0, maxLogs));
      setConnectionStatus('connected');
      setConnectionError('');
    });

    logsHub.onreconnecting((error) => {
      if (!active) return;

      setConnectionStatus('reconnecting');
      setConnectionError(getErrorMessage(error, 'The live log connection was interrupted.'));
    });

    logsHub.onreconnected(() => {
      if (!active) return;

      setConnectionStatus('connected');
      setConnectionError('');
    });

    logsHub.onclose((error) => {
      if (!active) return;

      setConnectionStatus('disconnected');
      setConnectionError(getErrorMessage(error, 'The live log connection closed.'));
    });

    logsHub.start().then(
      () => {
        if (active) {
          setConnectionStatus('connected');
          setConnectionError('');
        }
      },
      (error) => {
        if (active) {
          setConnectionStatus('disconnected');
          setConnectionError(getErrorMessage(error, 'Unable to connect to live logs.'));
        }
      },
    );

    return () => {
      active = false;
      logsHub.stop().catch((error) => {
        console.error('[Logs] Failed to stop hub connection:', error);
      });
    };
  }, [connectionAttempt, view]);

  useEffect(() => {
    if (view !== 'history') return undefined;

    let active = true;

    getLogFiles().then(
      (files) => {
        if (active) setHistory(Array.isArray(files) ? files : []);
      },
      (error) => {
        if (active) setHistoryError(getErrorMessage(error, 'Unable to load retained log files.'));
      },
    ).finally(() => {
      if (active) setHistoryLoading(false);
    });

    return () => { active = false; };
  }, [historyAttempt, view]);

  const filteredLogs = useMemo(
    () =>
      filterLevel === 'all'
        ? logs
        : logs.filter((log) => log.level === filterLevel),
    [filterLevel, logs],
  );

  const retryConnection = () => {
    setConnectionError('');
    setConnectionStatus('connecting');
    setConnectionAttempt((attempt) => attempt + 1);
  };

  const selectHistory = () => {
    setHistoryLoading(true);
    setHistoryError('');
    if (view === 'history') {
      setHistoryAttempt((attempt) => attempt + 1);
    } else {
      setView('history');
    }
  };

  const refreshHistory = () => {
    setHistoryLoading(true);
    setHistoryError('');
    setHistoryAttempt((attempt) => attempt + 1);
  };

  const openPreview = async (file) => {
    const requestId = ++previewRequestId.current;
    setPreview({ file, content: '' });
    setPreviewLoading(true);
    setPreviewError('');

    try {
      const content = await getLogFile(file.name);
      if (requestId === previewRequestId.current) setPreview({ file, content });
    } catch (error) {
      if (requestId === previewRequestId.current) {
        setPreviewError(getErrorMessage(error, 'Unable to read this log file.'));
      }
    } finally {
      if (requestId === previewRequestId.current) setPreviewLoading(false);
    }
  };

  const download = async (file) => {
    try {
      const content = await downloadLogFile(file.name);
      downloadFile(content, file.name, 'text/plain');
    } catch (error) {
      setHistoryError(getErrorMessage(error, `Unable to download ${file.name}.`));
    }
  };

  const closePreview = () => {
    previewRequestId.current += 1;
    setPreview(null);
    setPreviewLoading(false);
    setPreviewError('');
  };

  const connectionMessage = {
    connected: null,
    connecting: {
      content: interfaceText("Recent log entries will appear here as they arrive."),
      header: interfaceText("Connecting to live logs"),
      info: true,
    },
    disconnected: {
      content: connectionError,
      header: interfaceText("Live logs are disconnected"),
      warning: true,
    },
    reconnecting: {
      content: connectionError
        ? interfaceText('{message} Buffered entries remain available while the connection recovers.', {
          message: connectionError,
        })
        : interfaceText('Buffered entries remain available while the connection recovers.'),
      header: interfaceText("Reconnecting to live logs"),
      warning: true,
    },
  }[connectionStatus];

  return (
    <div className="logs">
      <Header as="h2">
        <Header.Content><LocalizedText source={"System Logs"} /></Header.Content>
        <Header.Subheader>
          {view === 'live'
            ? <LocalizedText source={"Monitor the most recent application records as they arrive."} />
            : <LocalizedText source={"Browse and download retained daily application logs."} />}
        </Header.Subheader>
      </Header>

      <div className="logs-controls">
        <ButtonGroup
          aria-label={interfaceText("Choose system log view")}
          className="logs-view-buttons"
          role="group"
         {...interfaceTextProps("Choose system log view")}>
          <Popup
            content={interfaceText("Monitor recent application records as they arrive.")}
            on={['hover', 'focus']}
            position="top center"
            trigger={(
              <Button
                active={view === 'live'}
                aria-pressed={view === 'live'}
                onClick={() => {
                  closePreview();
                  setConnectionStatus('connecting');
                  setConnectionError('');
                  setView('live');
                }}
                toggle
              >
                <LocalizedText source={"Live"} /></Button>
            )}
           {...interfaceTextProps("Monitor recent application records as they arrive.")}/>
          <Popup
            content={interfaceText("Browse, inspect, and download retained daily log files.")}
            on={['hover', 'focus']}
            position="top center"
            trigger={(
              <Button
                active={view === 'history'}
                aria-pressed={view === 'history'}
                onClick={selectHistory}
                toggle
              >
                <LocalizedText source={"History"} /></Button>
            )}
           {...interfaceTextProps("Browse, inspect, and download retained daily log files.")}/>
        </ButtonGroup>

        {view === 'live' ? (
          <>
            <ButtonGroup
              aria-label={interfaceText("Filter log entries by severity")}
              className="logs-filter-buttons"
              role="group"
             {...interfaceTextProps("Filter log entries by severity")}>
              {filters.map(({ accessibleName, color, description, label, level }) => {
                const active = filterLevel === level;
                return (
                  <Popup
                    key={level}
                    content={description}
                    on={['hover', 'focus']}
                    position="top center"
                    trigger={(
                      <Button
                        active={active}
                        aria-label={interfaceText(accessibleName)}
                        aria-pressed={active}
                        color={active ? color : undefined}
                        onClick={() => setFilterLevel(level)}
                        toggle
                       {...interfaceTextProps(accessibleName)}
                      >
                        {label}
                      </Button>
                    )}
                  />
                );
              })}
            </ButtonGroup>

            <span
              aria-live="polite"
              className="logs-count"
            >
              {connectionStatus === 'connected'
                ? <LocalizedText source={"Showing {filteredCount} of {totalCount} logs"} values={{ "filteredCount": (filteredLogs.length), "totalCount": (logs.length) }} />
                : <LocalizedText source={"Showing {filteredCount} of {totalCount} buffered logs"} values={{ "filteredCount": (filteredLogs.length), "totalCount": (logs.length) }} />}
            </span>
          </>
        ) : (
          <div className="logs-history-actions">
            <span aria-live="polite" className="logs-count">
              {historyLoading ? <LocalizedText source={"Loading retained logs…"} /> : history.length === 1
                ? interfaceText('{count} retained log', { count: history.length })
                : interfaceText('{count} retained logs', { count: history.length })}
            </span>
            <Popup
              content={interfaceText("Refresh the list of retained log files.")}
              on={['hover', 'focus']}
              position="top center"
              trigger={(
                <Button
                  aria-label={interfaceText("Refresh retained logs")}
                  disabled={historyLoading}
                  icon
                  onClick={refreshHistory}
                  size="small"
                 {...interfaceTextProps("Refresh retained logs")}>
                  <Icon name="refresh" />
                </Button>
              )}
             {...interfaceTextProps("Refresh the list of retained log files.")}/>
          </div>
        )}
      </div>

      {view === 'live' && connectionMessage && (
        <Message
          className="logs-connection-message"
          info={connectionMessage.info}
          warning={connectionMessage.warning}
        >
          <Message.Header>{connectionMessage.header}</Message.Header>
          <p>{connectionMessage.content}</p>
          {connectionStatus === 'disconnected' && (
            <Popup
              content={interfaceText("Retry the live log connection to receive new records.")}
              on={['hover', 'focus']}
              position="top center"
              trigger={(
                <Button
                  aria-label={interfaceText("Retry live log connection")}
                  className="logs-retry"
                  onClick={retryConnection}
                  size="small"
                 {...interfaceTextProps("Retry live log connection")}>
                  <LocalizedText source={"Retry"} /></Button>
              )}
             {...interfaceTextProps("Retry the live log connection to receive new records.")}/>
          )}
        </Message>
      )}

      {view === 'history' && (
        <>
          {historyError ? (
            <Message content={historyError} error role="alert" />
          ) : null}
          <div
            aria-label={interfaceText("Retained system log files")}
            className="logs-table-scroll"
            role="region"
            tabIndex={0}
           {...interfaceTextProps("Retained system log files")}>
            <Table aria-label={interfaceText("Retained system log files")} className="logs-table" compact="very" unstackable {...interfaceTextProps("Retained system log files")}>
              <Table.Header>
                <Table.Row>
                  <Table.HeaderCell><LocalizedText source={"File"} /></Table.HeaderCell>
                  <Table.HeaderCell><LocalizedText source={"Last modified"} /></Table.HeaderCell>
                  <Table.HeaderCell><LocalizedText source={"Size"} /></Table.HeaderCell>
                  <Table.HeaderCell textAlign="right"><LocalizedText source={"Actions"} /></Table.HeaderCell>
                </Table.Row>
              </Table.Header>
              <Table.Body className="logs-table-body">
                {history.length === 0 ? (
                  <Table.Row>
                    <Table.Cell colSpan="4" textAlign="center">
                      {historyLoading ? <LocalizedText source={"Loading retained log files…"} /> : <LocalizedText source={"No retained log files"} />}
                    </Table.Cell>
                  </Table.Row>
                ) : history.map((file) => (
                  <Table.Row key={file.name}>
                    <Table.Cell className="logs-history-name">{file.name}</Table.Cell>
                    <Table.Cell>{formatDate(file.lastModified)}</Table.Cell>
                    <Table.Cell>{formatBytes(file.length)}</Table.Cell>
                    <Table.Cell textAlign="right">
                      <div className="logs-history-row-actions">
                        <Popup
                          content={interfaceText("Open {name} to inspect its contents.", { "name": (file.name) })}
                          on={['hover', 'focus']}
                          position="top center"
                          trigger={(
                            <Button
                              aria-label={interfaceText("View {name}", { "name": (file.name) })}
                              icon
                              onClick={() => openPreview(file)}
                              size="small"
                             {...interfaceTextProps("View {name}")}>
                              <Icon name="eye" />
                            </Button>
                          )}
                         {...interfaceTextProps("Open {name} to inspect its contents.")}/>
                        <Popup
                          content={interfaceText("Download {name} for offline review.", { "name": (file.name) })}
                          on={['hover', 'focus']}
                          position="top center"
                          trigger={(
                            <Button
                              aria-label={interfaceText("Download {name}", { "name": (file.name) })}
                              icon
                              onClick={() => download(file)}
                              size="small"
                             {...interfaceTextProps("Download {name}")}>
                              <Icon name="download" />
                            </Button>
                          )}
                         {...interfaceTextProps("Download {name} for offline review.")}/>
                      </div>
                    </Table.Cell>
                  </Table.Row>
                ))}
              </Table.Body>
            </Table>
          </div>
          <Modal
            onClose={closePreview}
            open={Boolean(preview)}
            size="large"
          >
            <Modal.Header>
              <Icon name="file alternate outline" />
              {preview?.file.name || <LocalizedText source={"Log file"} />}
            </Modal.Header>
            <Modal.Content scrolling>
              {previewError ? <Message content={previewError} error role="alert" /> : null}
              {previewLoading ? <Message info content={interfaceText("Loading log file…")}  {...interfaceTextProps("Loading log file…")}/> : null}
              {!previewLoading && !previewError ? (
                <pre className="logs-history-preview">{preview?.content}</pre>
              ) : null}
            </Modal.Content>
            <Modal.Actions>
              <Popup
                content={interfaceText("Close this log preview and return to the retained files.")}
                on={['hover', 'focus']}
                trigger={(
                  <Button onClick={closePreview}>
                    <LocalizedText source={"Close"} /></Button>
                )}
               {...interfaceTextProps("Close this log preview and return to the retained files.")}/>
            </Modal.Actions>
          </Modal>
        </>
      )}

      {view === 'live' && (
        <div
          aria-label={interfaceText("System log entries")}
          className="logs-table-scroll"
          role="region"
          tabIndex={0}
         {...interfaceTextProps("System log entries")}>
          <Table
            aria-label={interfaceText("System log entries")}
            className="logs-table"
            compact="very"
            unstackable
           {...interfaceTextProps("System log entries")}>
            <Table.Header>
              <Table.Row>
                <Table.HeaderCell><LocalizedText source={"Timestamp"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Level"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Message"} /></Table.HeaderCell>
              </Table.Row>
            </Table.Header>
            <Table.Body className="logs-table-body">
              {filteredLogs.length === 0 ? (
                <Table.Row>
                  <Table.Cell
                    colSpan="3"
                    textAlign="center"
                  >
                    {connectionStatus === 'connected'
                      ? <LocalizedText source={"No logs match the selected filter"} />
                      : <LocalizedText source={"No buffered log entries"} />}
                  </Table.Cell>
                </Table.Row>
              ) : (
                filteredLogs.map((log, index) => (
                  <Table.Row
                    key={`${log.timestamp}-${log.level}-${index}`}
                    negative={log.level === 'Error'}
                    warning={log.level === 'Warning'}
                  >
                    <Table.Cell>
                      {formatTimestamp(log.timestamp)}
                    </Table.Cell>
                    <Table.Cell>{levels[log.level] || log.level}</Table.Cell>
                    <Table.Cell className="logs-table-message">
                      {log.message}
                    </Table.Cell>
                  </Table.Row>
                ))
              )}
            </Table.Body>
          </Table>
        </div>
      )}
    </div>
  );
};

export default Logs;
