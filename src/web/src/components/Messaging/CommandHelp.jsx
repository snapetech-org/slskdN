import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";


import React, { useEffect } from 'react';
import { Popup } from 'semantic-ui-react';

const CommandHelp = ({ commands, onClose, open }) => {
  useInterfaceLanguage();
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, open]);

  if (!open) return null;

  return (
    <div
      aria-modal="true"
      className="msgv2-help-overlay"
      onClick={onClose}
      role="dialog"
    >
      <div
        className="msgv2-help-modal"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="msgv2-help-header">
          <span className="msgv2-help-title"><LocalizedText source={"Commands"} /></span>
          <Popup
            content={interfaceText("Close the command reference and return to the message workspace.")}
            trigger={(
              <button
                aria-label={interfaceText("Close")}
                className="msgv2-help-close"
                onClick={onClose}
                type="button"
               {...interfaceTextProps("Close")}>
                ×
              </button>
            )}
           {...interfaceTextProps("Close the command reference and return to the message workspace.")}/>
        </header>
        <ul className="msgv2-help-list">
          {commands.map((command) => (
            <li
              className="msgv2-help-item"
              key={command.name}
            >
              <code className="msgv2-help-syntax">
                {command.syntax || `/${command.name}`}
              </code>
              <span className="msgv2-help-desc">{command.description}</span>
              {command.aliases && command.aliases.length > 0 && (
                <span className="msgv2-help-aliases">
                  <LocalizedText source={"aliases:"} />{" "}{command.aliases.map((alias) => `/${alias}`).join(', ')}
                </span>
              )}
            </li>
          ))}
        </ul>
        <footer className="msgv2-help-footer">
          <span>
            <kbd><LocalizedText source={"Tab"} /></kbd> <LocalizedText source={"autocompletes"} />{" "}<kbd>↑</kbd>
            <kbd>↓</kbd> <LocalizedText source={"navigates suggestions"} /></span>
          <span>
            <kbd><LocalizedText source={"Esc"} /></kbd> <LocalizedText source={"closes"} /></span>
        </footer>
      </div>
    </div>
  );
};

export default CommandHelp;
