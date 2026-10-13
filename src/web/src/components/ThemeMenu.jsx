import LocalizedText from "./Shared/LocalizedText";
import { interfaceText, interfaceTextProps } from "../lib/interfaceLocale";
import { THEME_PALETTES } from '../lib/themes';
import React from 'react';
import { Icon, Menu, Popup } from 'semantic-ui-react';

const THEME_OPTIONS = [
  { key: 'slskdn', get text() { return interfaceText("slskdN"); }, value: 'slskdn' },
  { key: 'classic-dark', get text() { return interfaceText("Classic Dark"); }, value: 'classic-dark' },
  { key: 'light', get text() { return interfaceText("Light"); }, value: 'light' },
];

const ThemeMenu = ({
  closeThemeMenu,
  onSetPalette,
  onSetTheme,
  openThemeMenu,
  open,
  palette,
  semanticTheme,
  theme,
}) => (
  <Popup
    basic
    className="theme-picker-popup"
    on="click"
    onClose={closeThemeMenu}
    onOpen={openThemeMenu}
    open={open}
    pinned
    position="bottom right"
    trigger={(
      <Menu.Item
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={interfaceText("Choose the web UI color theme")}
        className={`theme-menu ${open ? 'visible' : ''}`}
        data-testid="theme-menu"
        title={interfaceText("Choose the web UI color theme")}
       {...interfaceTextProps("Choose the web UI color theme")}>
        <Icon name="paint brush" />
        <span className="theme-menu-label"><LocalizedText source={"Theme"} /></span>
      </Menu.Item>
    )}
  >
    <Menu
      className="theme-picker-menu"
      vertical
    >
      {THEME_OPTIONS.map((option) => {
        const description = interfaceText("Use the {theme} theme for the web UI.", { theme: interfaceText(option.text) });

        return (
          <Popup
            content={description}
            key={option.key}
            trigger={(
              <Menu.Item
                active={theme === option.value}
                aria-label={description}
                data-testid={`theme-option-${option.value}`}
                onClick={() => onSetTheme(option.value)}
                title={description}
              >
                <Icon name="theme" />
                {interfaceText(option.text)}
              </Menu.Item>
            )}
          />
        );
      })}
      {semanticTheme !== 'light' && (
        <>
          <Menu.Item
            style={{
              cursor: 'default',
              fontSize: '0.75rem',
              fontWeight: 600,
              letterSpacing: '0.04em',
              opacity: 0.55,
              textTransform: 'uppercase',
            }}
          >
            <LocalizedText source={"Palette"} /></Menu.Item>
          <div className="theme-palette-grid">
            {THEME_PALETTES.map((paletteOption) => {
              const description = interfaceText("Apply the {palette} palette to the dark theme.", { palette: interfaceText(paletteOption.name) });

              return (
                <Popup
                  content={description}
                  key={paletteOption.id}
                  trigger={(
                    <button
                      aria-label={description}
                      className={`theme-palette-swatch ${
                        palette === paletteOption.id ? 'active' : ''
                      }`}
                      onClick={() => onSetPalette(paletteOption.id)}
                      title={description}
                      type="button"
                    >
                      <span className="theme-palette-swatch-dots">
                        {paletteOption.swatches.map((swatch) => (
                          <span
                            className="theme-palette-dot"
                            key={`${paletteOption.id}-${swatch}`}
                            style={{ backgroundColor: swatch }}
                          />
                        ))}
                      </span>
                      <span className="theme-palette-swatch-name">
                        {interfaceText(paletteOption.name)}
                      </span>
                    </button>
                  )}
                />
              );
            })}
          </div>
          {palette && (
            <Popup
              content={interfaceText("Restore the default colors for the dark theme.")}
              trigger={(
                <Menu.Item
                  aria-label={interfaceText("Restore the default colors for the dark theme.")}
                  onClick={() => onSetPalette(null)}
                  title={interfaceText("Restore the default colors for the dark theme.")}
                  style={{ fontSize: '0.8rem', opacity: 0.65 }}
                 {...interfaceTextProps("Restore the default colors for the dark theme.")}>
                  <Icon name="undo" />
                  <LocalizedText source={"Reset palette"} /></Menu.Item>
              )}
             {...interfaceTextProps("Restore the default colors for the dark theme.")}/>
          )}
        </>
      )}
    </Menu>
  </Popup>
);

export default ThemeMenu;
