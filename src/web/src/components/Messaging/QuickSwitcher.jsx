import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import React, { useEffect, useMemo, useRef, useState } from 'react';

const QuickSwitcher = ({ items, onClose, onPick, open }) => {
  useInterfaceLanguage();
  const [query, setQuery] = useState('');
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    setQuery('');
    setCursor(0);
    const id = window.setTimeout(() => inputRef.current?.focus(), 0);
    return () => window.clearTimeout(id);
  }, [open]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (item) =>
        item.label.toLowerCase().includes(q) ||
        (item.sublabel && item.sublabel.toLowerCase().includes(q)),
    );
  }, [items, query]);

  useEffect(() => {
    if (cursor >= filtered.length) setCursor(0);
  }, [cursor, filtered.length]);

  useEffect(() => {
    if (!listRef.current) return;
    const node = listRef.current.children[cursor];
    if (node && node.scrollIntoView) {
      node.scrollIntoView({ block: 'nearest' });
    }
  }, [cursor]);

  if (!open) return null;

  const handleKeyDown = (event) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setCursor((value) => Math.min(filtered.length - 1, value + 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setCursor((value) => Math.max(0, value - 1));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      const item = filtered[cursor];
      if (item) onPick(item);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      onClose();
    }
  };

  return (
    <div
      aria-modal="true"
      className="msgv2-qs-overlay"
      onClick={onClose}
      role="dialog"
    >
      <div
        className="msgv2-qs-modal"
        onClick={(event) => event.stopPropagation()}
      >
        <input
          aria-label={interfaceText("Quick switcher search")}
          className="msgv2-qs-input"
          onChange={(event) => {
            setQuery(event.target.value);
            setCursor(0);
          }}
          onKeyDown={handleKeyDown}
          placeholder={interfaceText("Jump to a conversation…")}
          ref={inputRef}
          type="text"
          value={query}
         {...interfaceTextProps("Quick switcher search")}/>
        <ul
          className="msgv2-qs-list"
          ref={listRef}
        >
          {filtered.length === 0 ? (
            <li className="msgv2-qs-empty"><LocalizedText source={"No matches"} /></li>
          ) : (
            filtered.map((item, index) => (
              <li
                aria-selected={index === cursor}
                className={`msgv2-qs-item ${index === cursor ? 'is-active' : ''}`}
                data-accent={item.accent}
                key={item.id}
                onClick={() => onPick(item)}
                onMouseEnter={() => setCursor(index)}
                role="option"
              >
                <span className="msgv2-qs-prefix">{item.prefix}</span>
                <span className="msgv2-qs-label">{item.label}</span>
                {item.sublabel && (
                  <span className="msgv2-qs-sublabel">{item.sublabel}</span>
                )}
              </li>
            ))
          )}
        </ul>
        <div className="msgv2-qs-hint">
          <kbd>↑</kbd>
          <kbd>↓</kbd>
          <LocalizedText source={"to navigate"} /><kbd><LocalizedText source={"Enter"} /></kbd>
          <LocalizedText source={"to open"} /><kbd><LocalizedText source={"Esc"} /></kbd>
          <LocalizedText source={"to close"} /></div>
      </div>
    </div>
  );
};

export default QuickSwitcher;
