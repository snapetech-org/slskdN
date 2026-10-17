import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import './MessageStream.css';
import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Button, Popup } from 'semantic-ui-react';

const NICK_PALETTE = [
  '#e07b91',
  '#e09d3b',
  '#d6c93b',
  '#7bd66e',
  '#3bd6b5',
  '#5ac0d6',
  '#7b9be0',
  '#a87be0',
  '#d67bce',
  '#e07b7b',
];

const SAME_SENDER_WINDOW_MS = 60_000;
const MAX_RENDERED_MESSAGES = 300;

const nickColor = (name) => {
  if (!name) return NICK_PALETTE[0];
  let hash = 5381;
  for (let index = 0; index < name.length; index += 1) {
    hash = ((hash << 5) + hash + name.charCodeAt(index)) | 0;
  }
  return NICK_PALETTE[Math.abs(hash) % NICK_PALETTE.length];
};

const pad2 = (value) => `${value}`.padStart(2, '0');

const formatTime = (ts) => {
  if (!ts) return '--:--';
  const date = new Date(ts);
  return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
};

const formatDayHeader = (ts) => {
  if (!ts) return '';
  const date = new Date(ts);
  return new Intl.DateTimeFormat(undefined, {
    day: 'numeric',
    month: 'short',
    weekday: 'short',
    year: undefined,
  }).format(date);
};

const sameDay = (a, b) => {
  if (!a || !b) return false;
  const da = new Date(a);
  const db = new Date(b);
  return (
    da.getFullYear() === db.getFullYear() &&
    da.getMonth() === db.getMonth() &&
    da.getDate() === db.getDate()
  );
};

const buildItems = (messages, newSinceIndex) => {
  const items = [];
  let previousTs = null;
  let previousSender = null;
  let previousKind = null;

  for (let index = 0; index < messages.length; index += 1) {
    if (newSinceIndex !== null && index === newSinceIndex && index > 0) {
      items.push({ kind: 'newmarker' });
      previousSender = null;
    }
    const message = messages[index];
    if (!sameDay(previousTs, message.ts)) {
      items.push({ kind: 'day', ts: message.ts });
      previousSender = null;
    }
    const compactWithPrev =
      message.kind === 'text' &&
      previousKind === 'text' &&
      message.sender === previousSender &&
      previousTs &&
      message.ts - previousTs < SAME_SENDER_WINDOW_MS;
    items.push({
      kind: 'message',
      message,
      messageIndex: index,
      showSender: !compactWithPrev,
    });
    previousTs = message.ts;
    previousSender = message.sender;
    previousKind = message.kind;
  }

  return items;
};

const URL_REGEX = /\b(?:https?|ftp):\/\/[^\s<>"'()]+[^\s<>"'(),.!?:;]/g;

const messageRenderKey = (message, fallbackIndex) =>
  message.id ||
  `${message.timestamp || message.time || message.ts || ''}\u0001${message.sender || ''}\u0001${message.body || ''}\u0001${fallbackIndex}`;

const messageListSignature = (messages) =>
  messages
    .map((message, index) => messageRenderKey(message, index))
    .join('\u0002');

const getErrorText = (error) =>
  getApiErrorMessage(error, { t: interfaceText }, 'The message history could not be loaded.');

const autolink = (text) => {
  if (typeof text !== 'string' || text.length === 0) return [text];
  const parts = [];
  let lastIndex = 0;
  URL_REGEX.lastIndex = 0;
  let match = URL_REGEX.exec(text);
  while (match !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    parts.push({ url: match[0] });
    lastIndex = match.index + match[0].length;
    match = URL_REGEX.exec(text);
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts;
};

const highlightText = (text, query) => {
  if (!query || typeof text !== 'string') return [text];
  const lower = text.toLowerCase();
  const needle = query.toLowerCase();
  const parts = [];
  let start = 0;
  let index = lower.indexOf(needle);

  while (index !== -1) {
    if (index > start) parts.push(text.slice(start, index));
    parts.push({ highlight: text.slice(index, index + needle.length) });
    start = index + needle.length;
    index = lower.indexOf(needle, start);
  }

  if (start < text.length) parts.push(text.slice(start));
  return parts;
};

const renderBody = (text, searchQuery) =>
  autolink(text).map((part, index) =>
    typeof part === 'string' ? (
      <React.Fragment key={index}>
        {highlightText(part, searchQuery).map((piece, pieceIndex) =>
          typeof piece === 'string' ? (
            <React.Fragment key={pieceIndex}>{piece}</React.Fragment>
          ) : (
            <mark
              className="msg-stream-search-hit"
              key={pieceIndex}
            >
              {piece.highlight}
            </mark>
          ),
        )}
      </React.Fragment>
    ) : (
      <a
        className="msg-stream-link"
        href={part.url}
        key={index}
        rel="noopener noreferrer"
        target="_blank"
      >
        {part.url}
      </a>
    ),
  );

const ListenAlongCard = ({ message }) => {
  useInterfaceLanguage();
  const meta = message.meta || {};
  const action = (meta.action || '').toLowerCase();
  const glyph = action === 'stop' ? '■' : '▶';
  const title = meta.title || 'unknown track';
  const artist = meta.artist;
  const album = meta.album;

  return (
    <div className="msg-stream-listenalong">
      <span className="msg-stream-listenalong-glyph">{glyph}</span>
      <span className="msg-stream-listenalong-host">{message.sender}</span>
      <span className="msg-stream-listenalong-action">
        {action === 'stop' ? <LocalizedText source={"stopped listenalong"} /> : <LocalizedText source={"is playing"} />}
      </span>
      <span className="msg-stream-listenalong-title">{title}</span>
      {artist && (
        <span className="msg-stream-listenalong-artist">— {artist}</span>
      )}
      {album && (
        <span className="msg-stream-listenalong-album">· {album}</span>
      )}
    </div>
  );
};

const MessageActions = ({ message, onCopy, onQuote }) => {
  useInterfaceLanguage();
  if (!onCopy && !onQuote) return null;
  return (
    <div
      aria-label={interfaceText("Message actions")}
      className="msg-stream-actions"
      role="toolbar"
     {...interfaceTextProps("Message actions")}>
      {onQuote && (
        <Popup
          content={interfaceText("Insert this message into the composer so you can reply in context.")}
          trigger={(
            <button
              aria-label={interfaceText("Quote message")}
              className="msg-stream-action"
              onClick={() => onQuote(message)}
              title={interfaceText("Quote in composer")}
              type="button"
             {...interfaceTextProps("Quote message")}>
              ❝
            </button>
          )}
         {...interfaceTextProps("Insert this message into the composer so you can reply in context.")}/>
      )}
      {onCopy && (
        <Popup
          content={interfaceText("Copy this message's text to the clipboard.")}
          trigger={(
            <button
              aria-label={interfaceText("Copy message")}
              className="msg-stream-action"
              onClick={() => onCopy(message)}
              title={interfaceText("Copy text")}
              type="button"
             {...interfaceTextProps("Copy message")}>
              ⎘
            </button>
          )}
         {...interfaceTextProps("Copy this message's text to the clipboard.")}/>
      )}
    </div>
  );
};

const messageMatches = (message, query) => {
  if (!query) return false;
  const needle = query.toLowerCase();
  return [message.sender, message.body, message.meta?.title, message.meta?.artist]
    .filter(Boolean)
    .some((value) => `${value}`.toLowerCase().includes(needle));
};

const MessageRow = ({
  activeMatch,
  item,
  matchesSearch,
  onCopy,
  onQuote,
  onSenderClick,
  searchQuery,
}) => {
  useInterfaceLanguage();
  const { message, showSender } = item;
  const color = useMemo(() => nickColor(message.sender), [message.sender]);
  const rowRef = useRef(null);

  useEffect(() => {
    if (activeMatch) {
      rowRef.current?.scrollIntoView?.({ block: 'center' });
    }
  }, [activeMatch]);

  if (message.kind === 'listenalong') {
    return (
      <div
        className="msg-stream-row msg-stream-row-listenalong"
        data-search-match={matchesSearch ? 'true' : undefined}
        data-search-active={activeMatch ? 'true' : undefined}
        data-self={message.isSelf ? 'true' : undefined}
        ref={rowRef}
      >
        <span className="msg-stream-time">{formatTime(message.ts)}</span>
        <ListenAlongCard message={message} />
        <MessageActions message={message} onCopy={onCopy} onQuote={onQuote} />
      </div>
    );
  }

  if (message.kind === 'me') {
    return (
      <div
        className="msg-stream-row msg-stream-row-me"
        data-search-match={matchesSearch ? 'true' : undefined}
        data-search-active={activeMatch ? 'true' : undefined}
        data-self={message.isSelf ? 'true' : undefined}
        ref={rowRef}
      >
        <span className="msg-stream-time">{formatTime(message.ts)}</span>
        <span className="msg-stream-me-glyph">*</span>
        <Popup
          content={interfaceText("Open the available actions for {sender}.", { "sender": (message.sender) })}
          trigger={(
            <button
              className="msg-stream-me-sender"
              onClick={(event) => onSenderClick?.(message.sender, event)}
              style={{ color }}
              type="button"
            >
              {message.sender}
            </button>
          )}
         {...interfaceTextProps("Open the available actions for {sender}.")}/>
        <span className="msg-stream-me-body">{renderBody(message.body, searchQuery)}</span>
        <MessageActions message={message} onCopy={onCopy} onQuote={onQuote} />
      </div>
    );
  }

  return (
    <div
      className="msg-stream-row msg-stream-row-text"
      data-compact={!showSender ? 'true' : undefined}
      data-search-match={matchesSearch ? 'true' : undefined}
      data-search-active={activeMatch ? 'true' : undefined}
      data-self={message.isSelf ? 'true' : undefined}
      ref={rowRef}
    >
      <span className="msg-stream-time">
        {showSender ? formatTime(message.ts) : ''}
      </span>
      {showSender ? (
        <Popup
          content={interfaceText("Open the available actions for {sender}.", { "sender": (message.sender) })}
          trigger={(
            <button
              className="msg-stream-sender"
              onClick={(event) => onSenderClick?.(message.sender, event)}
              style={{ color }}
              title={message.sender}
              type="button"
            >
              {message.sender}
            </button>
          )}
         {...interfaceTextProps("Open the available actions for {sender}.")}/>
      ) : (
        <span className="msg-stream-sender-spacer" aria-hidden="true" />
      )}
      <span className="msg-stream-body">{renderBody(message.body, searchQuery)}</span>
      <MessageActions message={message} onCopy={onCopy} onQuote={onQuote} />
    </div>
  );
};

const DaySeparator = ({ ts }) => (
  <div className="msg-stream-day">
    <span className="msg-stream-day-line" aria-hidden="true" />
    <span className="msg-stream-day-label">{formatDayHeader(ts)}</span>
    <span className="msg-stream-day-line" aria-hidden="true" />
  </div>
);

const MessageStream = ({ adapter, emptyHint, onCopy, onQuote, onSenderClick }) => {
  useInterfaceLanguage();
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [lastSeenCount, setLastSeenCount] = useState(0);
  const [searchCursor, setSearchCursor] = useState(0);
  const [searchDraft, setSearchDraft] = useState('');
  const [stuck, setStuck] = useState(true);
  const scrollRef = useRef(null);
  const stuckRef = useRef(true);
  const activeAdapterRef = useRef(adapter);
  const mountedRef = useRef(false);
  const pollIntervalRef = useRef(null);
  const refreshInFlightRef = useRef(null);

  activeAdapterRef.current = adapter;

  const setStuckBoth = useCallback((value) => {
    stuckRef.current = value;
    setStuck(value);
  }, []);

  const refresh = useCallback(() => {
    if (!adapter) return Promise.resolve();
    if (refreshInFlightRef.current) return refreshInFlightRef.current;

    const requestedAdapter = adapter;
    const request = (async () => {
      try {
        const result = await requestedAdapter.list();
        if (!mountedRef.current || activeAdapterRef.current !== requestedAdapter) return;

        const next = Array.isArray(result?.messages) ? result.messages : [];
        setMessages((previous) =>
          messageListSignature(previous) === messageListSignature(next) ? previous : next,
        );
        setError(null);
      } catch (caught) {
        console.error('MessageStream refresh failed:', caught);
        if (mountedRef.current && activeAdapterRef.current === requestedAdapter) {
          setError(getErrorText(caught));
        }
      } finally {
        if (mountedRef.current && activeAdapterRef.current === requestedAdapter) {
          setIsInitialLoad(false);
        }
      }
    })();
    const trackedRequest = request.finally(() => {
      if (refreshInFlightRef.current === trackedRequest) {
        refreshInFlightRef.current = null;
      }
    });
    refreshInFlightRef.current = trackedRequest;
    return trackedRequest;
  }, [adapter]);

  useEffect(() => {
    mountedRef.current = true;
    activeAdapterRef.current = adapter;
    refreshInFlightRef.current = null;
    setMessages([]);
    setIsInitialLoad(true);
    setSearchCursor(0);
    setSearchDraft('');
    setStuckBoth(true);
    setLastSeenCount(0);
    const stopPolling = () => {
      if (pollIntervalRef.current) {
        window.clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
    const startPolling = () => {
      if (!adapter || document.hidden || pollIntervalRef.current) return;
      pollIntervalRef.current = window.setInterval(
        refresh,
        adapter.pollIntervalMs || 2_000,
      );
    };
    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopPolling();
        return;
      }

      refresh();
      startPolling();
    };

    if (adapter && !document.hidden) {
      refresh();
      startPolling();
    }
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      mountedRef.current = false;
      activeAdapterRef.current = null;
      refreshInFlightRef.current = null;
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [adapter, refresh, setStuckBoth]);

  useLayoutEffect(() => {
    const node = scrollRef.current;
    if (!node) return;
    if (stuckRef.current) {
      node.scrollTop = node.scrollHeight;
      setLastSeenCount(messages.length);
    }
  }, [messages]);

  const handleScroll = useCallback(
    (event) => {
      const node = event.currentTarget;
      const distanceFromBottom = node.scrollHeight - node.clientHeight - node.scrollTop;
      const atBottom = distanceFromBottom < 32;
      if (atBottom !== stuckRef.current) setStuckBoth(atBottom);
      if (atBottom) setLastSeenCount(messages.length);
    },
    [messages.length, setStuckBoth],
  );

  const jumpToLatest = useCallback(() => {
    const node = scrollRef.current;
    if (!node) return;
    node.scrollTop = node.scrollHeight;
    setStuckBoth(true);
    setLastSeenCount(messages.length);
  }, [messages.length, setStuckBoth]);

  const newSinceIndex =
    !stuck && lastSeenCount > 0 && lastSeenCount < messages.length
      ? lastSeenCount
      : null;

  const newCount = newSinceIndex !== null ? messages.length - newSinceIndex : 0;
  const searchQuery = searchDraft.trim();
  const searchActive = searchQuery.length > 0;
  const visibleOffset = searchActive
    ? 0
    : Math.max(0, messages.length - MAX_RENDERED_MESSAGES);
  const visibleMessages = useMemo(
    () => messages.slice(visibleOffset),
    [messages, visibleOffset],
  );
  const visibleNewSinceIndex =
    newSinceIndex !== null && newSinceIndex >= visibleOffset
      ? newSinceIndex - visibleOffset
      : null;
  const hiddenMessageCount = visibleOffset;

  const items = useMemo(
    () => buildItems(visibleMessages, visibleNewSinceIndex),
    [visibleMessages, visibleNewSinceIndex],
  );

  const matchingIndexes = useMemo(
    () =>
      searchActive
        ? messages
            .map((message, index) => (messageMatches(message, searchQuery) ? index : null))
            .filter((index) => index !== null)
        : [],
    [messages, searchActive, searchQuery],
  );
  const matchingIndexSet = useMemo(
    () => new Set(matchingIndexes),
    [matchingIndexes],
  );
  const activeMatchIndex = matchingIndexes[searchCursor] ?? null;

  useEffect(() => {
    if (searchCursor >= matchingIndexes.length) {
      setSearchCursor(0);
    }
  }, [matchingIndexes.length, searchCursor]);

  const moveSearch = useCallback(
    (delta) => {
      if (matchingIndexes.length === 0) return;
      setSearchCursor((current) =>
        (current + delta + matchingIndexes.length) % matchingIndexes.length,
      );
    },
    [matchingIndexes.length],
  );

  return (
    <div className="msg-stream-wrap">
      <div className="msg-stream-search">
        <input
          aria-label={interfaceText("Search active conversation")}
          className="msg-stream-search-input"
          onChange={(event) => {
            setSearchDraft(event.target.value);
            setSearchCursor(0);
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault();
              moveSearch(event.shiftKey ? -1 : 1);
            } else if (event.key === 'Escape') {
              setSearchDraft('');
              setSearchCursor(0);
            }
          }}
          placeholder={interfaceText("Search in conversation")}
          type="search"
          value={searchDraft}
         {...interfaceTextProps("Search active conversation")}/>
        <span className="msg-stream-search-count">
          {searchQuery
            ? `${matchingIndexes.length ? searchCursor + 1 : 0}/${matchingIndexes.length}`
            : ''}
        </span>
        <Popup
          content={interfaceText("Move to the previous matching message.")}
          trigger={(
            <span className="msg-stream-search-control">
              <button
                aria-label={interfaceText("Previous search match")}
                className="msg-stream-search-button"
                disabled={matchingIndexes.length === 0}
                onClick={() => moveSearch(-1)}
                title={interfaceText("Previous search match")}
                type="button"
               {...interfaceTextProps("Previous search match")}>
                ↑
              </button>
            </span>
          )}
         {...interfaceTextProps("Move to the previous matching message.")}/>
        <Popup
          content={interfaceText("Move to the next matching message.")}
          trigger={(
            <span className="msg-stream-search-control">
              <button
                aria-label={interfaceText("Next search match")}
                className="msg-stream-search-button"
                disabled={matchingIndexes.length === 0}
                onClick={() => moveSearch(1)}
                title={interfaceText("Next search match")}
                type="button"
               {...interfaceTextProps("Next search match")}>
                ↓
              </button>
            </span>
          )}
         {...interfaceTextProps("Move to the next matching message.")}/>
      </div>
      {error && (
        <div className="msg-stream-error" role="alert">
          <span>{error}</span>
          <Popup
            content={interfaceText("Retry loading this conversation's messages.")}
            trigger={(
              <Button
                basic
                className="msg-stream-retry"
                onClick={refresh}
                size="mini"
              >
                <LocalizedText source={"Retry"} /></Button>
            )}
           {...interfaceTextProps("Retry loading this conversation's messages.")}/>
        </div>
      )}
      <div
        className="msg-stream"
        onScroll={handleScroll}
        ref={scrollRef}
      >
        {isInitialLoad ? (
          <div className="msg-stream-loading"><LocalizedText source={"Loading…"} /></div>
        ) : items.length === 0 && error ? null : items.length === 0 ? (
          <div className="msg-stream-empty">
            {emptyHint || <LocalizedText source={"No messages yet."} />}
          </div>
        ) : (
          <>
            {hiddenMessageCount > 0 && (
              <div className="msg-stream-truncated">
                <LocalizedText source={"Showing latest"} />{" "}{MAX_RENDERED_MESSAGES} <LocalizedText source={"of"} />{" "}{messages.length} <LocalizedText source={"messages. Use search to scan full history."} /></div>
            )}
            {items.map((item, index) => {
              if (item.kind === 'day') {
                return <DaySeparator key={`day-${item.ts}-${index}`} ts={item.ts} />;
              }
              if (item.kind === 'newmarker') {
                return <NewMessagesMarker key={`new-${index}`} />;
              }
              return (
                <MessageRow
                  activeMatch={item.messageIndex + visibleOffset === activeMatchIndex}
                  item={item}
                  key={messageRenderKey(item.message, item.messageIndex + visibleOffset)}
                  matchesSearch={searchActive && matchingIndexSet.has(item.messageIndex + visibleOffset)}
                  onCopy={onCopy}
                  onQuote={onQuote}
                  onSenderClick={onSenderClick}
                  searchQuery={searchActive ? searchQuery : ''}
                />
              );
            })}
          </>
        )}
      </div>
      {!stuck && (
        <Popup
          content={interfaceText("Scroll to the newest messages in this conversation.")}
          trigger={(
            <button
              aria-label={interfaceText("Jump to latest")}
              className="msg-stream-jump"
              onClick={jumpToLatest}
              type="button"
             {...interfaceTextProps("Jump to latest")}>
              {newCount > 0
                ? `↓ ${newCount} new ${newCount === 1 ? 'message' : 'messages'}`
                : <LocalizedText source={"↓ Jump to latest"} />}
            </button>
          )}
         {...interfaceTextProps("Scroll to the newest messages in this conversation.")}/>
      )}
    </div>
  );
};

const NewMessagesMarker = () => (
  <div
    aria-label={interfaceText("New messages below")}
    className="msg-stream-newmarker"
    role="separator"
   {...interfaceTextProps("New messages below")}>
    <span className="msg-stream-newmarker-line" aria-hidden="true" />
    <span className="msg-stream-newmarker-label"><LocalizedText source={"new"} /></span>
    <span className="msg-stream-newmarker-line" aria-hidden="true" />
  </div>
);

export default React.memo(MessageStream);
export { autolink, nickColor };
