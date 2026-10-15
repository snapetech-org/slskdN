import '@testing-library/jest-dom';
import ExperienceSettings from './index';
import React from 'react';
import userEvent from '@testing-library/user-event';
import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { resetInterfaceLanguage, setInterfaceLanguage, useInterfaceLanguage } from '../../../lib/interfaceLocale';
import { stubLocaleCatalogFetch } from '../../../test/localeCatalogFetchMock';

const storageKey = 'slskdn:experience-preferences:v1';
const interfaceLanguageStorageKey = 'slskdn.interface-language';

const ActiveLanguage = () => {
  const { language } = useInterfaceLanguage();
  return <span data-testid="active-language">{language}</span>;
};

describe('ExperienceSettings', () => {
  beforeEach(() => {
    stubLocaleCatalogFetch(vi);
    localStorage.clear();
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  afterEach(async () => {
    await resetInterfaceLanguage();
    vi.unstubAllGlobals();
  });

  it('surfaces only the Search and Player preferences currently used by the app', () => {
    render(<ExperienceSettings />);

    expect(screen.getByText('Search')).toBeInTheDocument();
    expect(screen.getByText('Player')).toBeInTheDocument();
    expect(screen.getByLabelText('Show browser player preference')).toBeChecked();
    expect(screen.getByLabelText('Show album candidates preference')).toBeChecked();
    expect(
      screen.queryByLabelText('Enable search duplicate folding preference'),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText('Show unread message badges preference'),
    ).not.toBeInTheDocument();
  });

  it('saves supported preferences without changing legacy stored keys', () => {
    localStorage.setItem(storageKey, JSON.stringify({
      messagesDenseMode: true,
      playerRadioSeedMode: 'queue',
    }));
    render(<ExperienceSettings />);

    fireEvent.click(screen.getByLabelText('Show browser player preference'));
    fireEvent.click(screen.getByLabelText('Show album candidates preference'));
    fireEvent.click(screen.getByRole('button', { name: 'Save Local Preferences' }));

    const saved = JSON.parse(localStorage.getItem(storageKey));
    expect(saved.messagesDenseMode).toBe(true);
    expect(saved.playerRadioSeedMode).toBe('queue');
    expect(saved.playerVisible).toBe(false);
    expect(saved.searchAlbumCandidatesVisible).toBe(false);
    expect(
      screen.getByText('Experience preferences saved locally in this browser.'),
    ).toBeInTheDocument();
  });

  it('ignores malformed persisted preference shapes', () => {
    localStorage.setItem(storageKey, JSON.stringify(['bad']));

    render(<ExperienceSettings />);

    expect(screen.getByLabelText('Show browser player preference')).toBeChecked();
    expect(screen.getByLabelText('Show album candidates preference')).toBeChecked();
    expect(
      screen.queryByLabelText('Show unread message badges preference'),
    ).not.toBeInTheDocument();
  });

  it('ignores malformed active preference values in the report', () => {
    localStorage.setItem(
      storageKey,
      JSON.stringify({
        playerVisible: 'false',
        searchAlbumCandidatesVisible: 'false',
      }),
    );

    render(<ExperienceSettings />);

    expect(screen.getByLabelText('Show browser player preference')).toBeChecked();
    expect(screen.getByLabelText('Show album candidates preference')).toBeChecked();

    fireEvent.click(screen.getByRole('button', { name: 'Copy Report' }));

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining('Search: album_candidates=true'),
    );
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining('Player: visible=true'),
    );
  });

  it('copies a preference report', () => {
    render(<ExperienceSettings />);

    fireEvent.click(screen.getByRole('button', { name: 'Copy Report' }));

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining('slskdN browser experience preferences'),
    );
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining('Search: album_candidates=true'),
    );
  });

  it('clears the separately stored interface-language override on reset', async () => {
    await setInterfaceLanguage('fr');
    localStorage.setItem(storageKey, JSON.stringify({ regionalFormat: 'de' }));
    render(<><ExperienceSettings /><ActiveLanguage /></>);

    expect(screen.getByTestId('active-language')).toHaveTextContent('fr');
    fireEvent.click(screen.getByRole('button', { name: 'Réinitialiser' }));

    expect(localStorage.getItem(interfaceLanguageStorageKey)).toBeNull();
    expect(localStorage.getItem(storageKey)).toBeNull();
    expect(screen.getByTestId('active-language')).toHaveTextContent('en');
  });

  it('reports clipboard failures instead of claiming the report was copied', async () => {
    const user = userEvent.setup();
    vi.spyOn(navigator.clipboard, 'writeText').mockRejectedValue(
      new Error('Clipboard permission denied'),
    );
    render(<ExperienceSettings />);

    await user.click(screen.getByRole('button', { name: 'Copy Report' }));

    expect(await screen.findByText('Could not copy the preference report.'))
      .toBeInTheDocument();
    expect(screen.queryByText('Experience preference report copied.'))
      .not.toBeInTheDocument();
  });
});
