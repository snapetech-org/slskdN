import { bands, resumeAudioGraph, setEqGains } from './audioGraph';
import { interfaceText } from '../../lib/interfaceLocale';
import { getLocalStorageItem, setLocalStorageItem } from '../../lib/storage';
import React, { useEffect, useState } from 'react';
import { Button, Dropdown, Icon, Popup } from 'semantic-ui-react';

const storageKey = 'slskdn.player.equalizer';

const presets = {
  Flat: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  Classical: [0, 0, 0, 0, 0, 0, -2, -2, -2, -3],
  Dance: [5, 4, 2, 0, 0, -2, -2, 2, 4, 5],
  Metal: [4, 3, 2, 1, -1, -2, 0, 2, 4, 5],
  Rock: [4, 3, 2, 0, -1, -1, 1, 2, 3, 4],
  Vocal: [-2, -2, -1, 2, 4, 4, 3, 1, 0, -1],
};

const defaultState = {
  enabled: false,
  gains: presets.Flat,
  preset: 'Flat',
};

const readStoredState = () => {
  try {
    const stored = JSON.parse(getLocalStorageItem(storageKey, 'null'));
    if (!stored || !Array.isArray(stored.gains)) return defaultState;
    return {
      enabled: stored.enabled === true,
      gains: bands.map((_, index) => {
        const gain = Number(stored.gains[index]);
        return Number.isFinite(gain) ? Math.max(-12, Math.min(12, Math.round(gain))) : 0;
      }),
      preset: stored.preset || 'Custom',
    };
  } catch {
    return defaultState;
  }
};

const formatBand = (frequency) =>
  frequency >= 1000 ? `${frequency / 1000}k` : String(frequency);

const Equalizer = ({ audioElement, fadeAudioElement, onAudioError }) => {
  const [state, setState] = useState(readStoredState);

  useEffect(() => {
    if (!audioElement) return;
    const gains = state.enabled ? state.gains : presets.Flat;
    [audioElement, fadeAudioElement].filter(Boolean).forEach((element) => {
      setEqGains(element, gains);
      if (!element.paused) {
        resumeAudioGraph(element, false).catch(() => {
          onAudioError('Could not enable the equalizer for this track.');
        });
      }
    });
  }, [audioElement, fadeAudioElement, onAudioError, state.enabled, state.gains]);

  useEffect(() => {
    setLocalStorageItem(storageKey, JSON.stringify(state));
  }, [state]);

  const presetOptions = Object.keys(presets).map((name) => ({
    key: name,
    text: interfaceText(name),
    value: name,
  }));

  return (
    <div className="player-eq" data-testid="player-equalizer">
      <div className="player-panel-header">
        <strong>EQ</strong>
        <div className="player-panel-actions">
          <Dropdown
            compact
            data-testid="player-eq-preset"
            onChange={(_, { value }) =>
              setState((existing) => ({
                ...existing,
                gains: presets[value],
                preset: value,
              }))
            }
            options={presetOptions}
            selection
            value={state.preset in presets ? state.preset : 'Flat'}
          />
          <Popup
            content={
              state.enabled
                ? interfaceText('Bypass the equalizer without losing your slider settings.')
                : interfaceText('Enable the equalizer for this browser player.')
            }
            trigger={
              <Button
                aria-label={state.enabled ? interfaceText('Disable equalizer') : interfaceText('Enable equalizer')}
                compact
                data-testid="player-eq-toggle"
                icon
                onClick={() =>
                  setState((existing) => ({
                    ...existing,
                    enabled: !existing.enabled,
                  }))
                }
                primary={state.enabled}
                size="mini"
              >
                <Icon name="sliders horizontal" />
              </Button>
            }
          />
        </div>
      </div>
      <div className="player-eq-bands">
        {bands.map((frequency, index) => (
          <label className="player-eq-band" key={frequency}>
            <input
              aria-label={interfaceText('{frequency} equalizer gain', { frequency: formatBand(frequency) })}
              aria-orientation="vertical"
              aria-valuetext={`${state.gains[index]} dB`}
              data-testid={`player-eq-slider-${frequency}`}
              disabled={!state.enabled}
              max="12"
              min="-12"
              onChange={(event) => {
                const gain = Number(event.target.value);
                setState((existing) => ({
                  enabled: existing.enabled,
                  gains: existing.gains.map((value, gainIndex) =>
                    gainIndex === index ? gain : value,
                  ),
                  preset: 'Custom',
                }));
              }}
              onKeyDown={(event) => {
                if (!['ArrowUp', 'ArrowRight', 'ArrowDown', 'ArrowLeft'].includes(event.key)) return;

                event.preventDefault();
                const adjustment = event.key === 'ArrowUp' || event.key === 'ArrowRight' ? 1 : -1;
                setState((existing) => {
                  const currentGain = existing.gains[index];
                  const gain = Math.max(-12, Math.min(12, currentGain + adjustment));
                  if (gain === currentGain) return existing;

                  return {
                    ...existing,
                    gains: existing.gains.map((value, gainIndex) =>
                      gainIndex === index ? gain : value,
                    ),
                    preset: 'Custom',
                  };
                });
              }}
              step="1"
              type="range"
              value={state.gains[index]}
            />
            <span>{formatBand(frequency)}</span>
          </label>
        ))}
      </div>
    </div>
  );
};

export default Equalizer;
