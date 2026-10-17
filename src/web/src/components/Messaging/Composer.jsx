import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Popup } from 'semantic-ui-react';

const ME_PREFIX = '/me ';

const getSendErrorMessage = (error) =>
  getApiErrorMessage(error, { t: interfaceText }, 'The message could not be sent.');

const matchSuggestions = (draft, commands) => {
  if (!draft.startsWith('/') || draft.startsWith('/ ')) return [];
  const space = draft.indexOf(' ');
  if (space !== -1) return [];
  const prefix = draft.slice(1).toLowerCase();
  if (prefix.length === 0) return commands;
  return commands.filter((command) => {
    if (command.name.toLowerCase().startsWith(prefix)) return true;
    return (command.aliases || []).some((alias) =>
      alias.toLowerCase().startsWith(prefix),
    );
  });
};

const Composer = ({
  adapter,
  commands = [],
  disabled,
  inputRef,
  label,
  onChange,
  onCommand,
  placeholder,
  value,
}) => {
  useInterfaceLanguage();
  const [busy, setBusy] = useState(false);
  const [cursor, setCursor] = useState(0);
  const [sendError, setSendError] = useState('');
  const localRef = useRef(null);
  const ref = inputRef || localRef;

  useEffect(() => {
    setCursor(0);
    setSendError('');
  }, [adapter]);

  const setValue = useCallback(
    (next) => {
      if (typeof onChange === 'function') onChange(next);
      setSendError('');
    },
    [onChange],
  );

  const draft = typeof value === 'string' ? value : '';

  const suggestions = useMemo(
    () => matchSuggestions(draft, commands),
    [commands, draft],
  );

  useEffect(() => {
    if (cursor >= suggestions.length) setCursor(0);
  }, [cursor, suggestions.length]);

  const submit = useCallback(async () => {
    const trimmed = draft.trim();
    if (!trimmed || busy || !adapter) return;

    if (trimmed.startsWith('/') && !trimmed.startsWith(ME_PREFIX)) {
      const [head, ...rest] = trimmed.slice(1).split(/\s+/);
      const handled = onCommand?.({
        argv: rest,
        name: head.toLowerCase(),
        raw: trimmed,
      });
      if (handled) {
        setValue('');
        return;
      }
    }

    setSendError('');
    setBusy(true);
    try {
      await adapter.send(trimmed);
      setValue('');
    } catch (error) {
      setSendError(getSendErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }, [adapter, busy, draft, onCommand, setValue]);

  const completeSuggestion = useCallback(() => {
    const choice = suggestions[cursor];
    if (!choice) return false;
    setValue(`/${choice.name} `);
    setCursor(0);
    return true;
  }, [cursor, setValue, suggestions]);

  const handleKeyDown = useCallback(
    (event) => {
      if (suggestions.length > 0) {
        if (event.key === 'ArrowDown') {
          event.preventDefault();
          setCursor((current) => Math.min(suggestions.length - 1, current + 1));
          return;
        }
        if (event.key === 'ArrowUp') {
          event.preventDefault();
          setCursor((current) => Math.max(0, current - 1));
          return;
        }
        if (event.key === 'Tab') {
          event.preventDefault();
          completeSuggestion();
          return;
        }
      }
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        submit();
      }
    },
    [completeSuggestion, submit, suggestions.length],
  );

  const isDisabled = disabled || !adapter;

  return (
    <div className="msgv2-composer-wrap">
      {suggestions.length > 0 && (
        <div
          aria-label={interfaceText("Command suggestions")}
          className="msgv2-composer-suggestions"
          role="listbox"
         {...interfaceTextProps("Command suggestions")}>
          {suggestions.map((command, index) => (
            <Popup
              content={`${command.description} Select to insert ${command.syntax || `/${command.name}`} in the composer.`}
              key={command.name}
              trigger={(
                <button
                  aria-selected={index === cursor}
                  className={`msgv2-composer-suggestion ${index === cursor ? 'is-active' : ''}`}
                  onClick={() => {
                    setCursor(index);
                    setValue(`/${command.name} `);
                    ref.current?.focus();
                  }}
                  onMouseEnter={() => setCursor(index)}
                  role="option"
                  type="button"
                >
                  <span className="msgv2-composer-suggestion-syntax">
                    {command.syntax || `/${command.name}`}
                  </span>
                  <span className="msgv2-composer-suggestion-desc">
                    {command.description}
                  </span>
                </button>
              )}
            />
          ))}
        </div>
      )}
      <div className="msgv2-composer">
        <textarea
          aria-label={label || interfaceText('Message composer')}
          className="msgv2-composer-input"
          disabled={isDisabled}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isDisabled
            ? interfaceText('Open a tab to start typing')
            : placeholder || interfaceText('Type a message — Enter sends, Shift+Enter newline')}
          ref={ref}
          rows={1}
          value={draft}
        />
        <Popup
          content={interfaceText(isDisabled || draft.trim().length === 0 || busy
            ? 'Enter a message in the active conversation before sending.'
            : 'Send this message to the active conversation. Press Enter to send; Shift+Enter adds a line break.')}
          trigger={(
            <span>
              <button
                aria-label={interfaceText("Send")}
                className="msgv2-composer-send"
                disabled={isDisabled || draft.trim().length === 0 || busy}
                onClick={submit}
                title={interfaceText("Send (Enter)")}
                type="button"
               {...interfaceTextProps("Send")}>
                {busy ? '…' : '▶'}
              </button>
            </span>
          )}
        />
      </div>
      {sendError && (
        <div
          aria-live="assertive"
          className="msgv2-composer-error"
          data-testid="message-send-error"
          role="alert"
        >
          {sendError} <LocalizedText source={"Your draft is still here; try Send again."} /></div>
      )}
    </div>
  );
};

export default Composer;
export { matchSuggestions };
