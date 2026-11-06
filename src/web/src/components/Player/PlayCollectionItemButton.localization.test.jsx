import React from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { interfacePresentationText } from '../../lib/interfaceLocale';
import PlayCollectionItemButton from './PlayCollectionItemButton';

vi.mock('./PlayerContext', () => ({ usePlayer: () => ({ playItem: vi.fn(), playerVisible: true }) }));
vi.mock('../../lib/interfaceLocale', () => ({
  useInterfaceLanguage: () => ({ directionFor: () => 'ltr', languageFor: () => 'en', t: (source) => source }),
  interfaceText: (source) => source,
  interfaceTextProps: () => ({}),
  interfacePresentationText: vi.fn((source, parameters = {}) => 'localized:' + source.replace(
    /\{([a-zA-Z][a-zA-Z0-9_]*)\}/g,
    (token, name) => Object.hasOwn(parameters, name) ? String(parameters[name]) : token,
  )),
}));
afterEach(() => cleanup());

it('passes opaque track labels as values rather than constructing a new source key', () => {
  const track = 'user/{track}/العربية';
  render(<PlayCollectionItemButton item={{ title: track, contentId: 'opaque-id' }} />);
  expect(screen.getByRole('button', { name: `localized:Play ${track} in the browser player` })).toBeTruthy();
  expect(interfacePresentationText).toHaveBeenCalledWith('Play {track} in the browser player', { track });
});
