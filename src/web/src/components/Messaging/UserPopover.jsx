import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Popup } from 'semantic-ui-react';

const POPOVER_OFFSET = 6;
const POPOVER_MARGIN = 8;

const UserPopover = ({ anchor, onBrowse, onClose, onMessage, onProfile, open, username }) => {
  useInterfaceLanguage();
  const ref = useRef(null);
  const [position, setPosition] = useState({ left: 0, top: 0, ready: false });

  useLayoutEffect(() => {
    if (!open || !anchor || !ref.current) return;
    const node = ref.current;
    const rect = node.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    let left = anchor.x + POPOVER_OFFSET;
    let top = anchor.y + POPOVER_OFFSET;

    if (left + rect.width > viewportWidth - POPOVER_MARGIN) {
      left = Math.max(POPOVER_MARGIN, anchor.x - rect.width - POPOVER_OFFSET);
    }
    if (top + rect.height > viewportHeight - POPOVER_MARGIN) {
      top = Math.max(POPOVER_MARGIN, viewportHeight - rect.height - POPOVER_MARGIN);
    }

    setPosition({ left, ready: true, top });
  }, [anchor, open]);

  useEffect(() => {
    if (!open) return undefined;
    const handleKey = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      }
    };
    const handleClick = (event) => {
      if (ref.current && !ref.current.contains(event.target)) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKey);
    window.addEventListener('mousedown', handleClick);
    return () => {
      window.removeEventListener('keydown', handleKey);
      window.removeEventListener('mousedown', handleClick);
    };
  }, [onClose, open]);

  if (!open || !username) return null;

  return (
    <div
      aria-label={interfaceText("Actions for {username}", { "username": (username) })}
      className="msgv2-userpop"
      ref={ref}
      role="menu"
      style={{
        left: position.left,
        top: position.top,
        visibility: position.ready ? 'visible' : 'hidden',
      }}
     {...interfaceTextProps("Actions for {username}")}>
      <header className="msgv2-userpop-header">
        <span className="msgv2-userpop-name">{username}</span>
      </header>
      <Popup
        content={interfaceText("Open {username}'s profile to view available user details.", { "username": (username) })}
        trigger={(
          <button
            className="msgv2-userpop-action"
            onClick={() => onProfile(username)}
            role="menuitem"
            type="button"
          >
            <span className="msgv2-userpop-glyph"><LocalizedText source={"i"} /></span>
            <LocalizedText source={"Open profile"} /></button>
        )}
       {...interfaceTextProps("Open {username}'s profile to view available user details.")}/>
      <Popup
        content={interfaceText("Request {username}'s shared file list from Soulseek so you can browse their files.", { "username": (username) })}
        trigger={(
          <button
            className="msgv2-userpop-action"
            onClick={() => onBrowse(username)}
            role="menuitem"
            type="button"
          >
            <span className="msgv2-userpop-glyph">⤓</span>
            <LocalizedText source={"Browse shares"} /></button>
        )}
       {...interfaceTextProps("Request {username}'s shared file list from Soulseek so you can browse their files.")}/>
      <Popup
        content={interfaceText("Open a direct-message tab with {username} to send a private message.", { "username": (username) })}
        trigger={(
          <button
            className="msgv2-userpop-action"
            onClick={() => onMessage(username)}
            role="menuitem"
            type="button"
          >
            <span className="msgv2-userpop-glyph">@</span>
            <LocalizedText source={"Send DM"} /></button>
        )}
       {...interfaceTextProps("Open a direct-message tab with {username} to send a private message.")}/>
    </div>
  );
};

export default UserPopover;
