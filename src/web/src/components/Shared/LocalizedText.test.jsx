import React from 'react';
import { render } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { interfaceText, resetInterfaceLanguage, setInterfaceLanguage, useInterfaceLanguage } from '../../lib/interfaceLocale';
import { stubLocaleCatalogFetch } from '../../test/localeCatalogFetchMock';
import LocalizedText from './LocalizedText';

const ActiveLanguage = () => {
  const { language } = useInterfaceLanguage();
  return <span data-testid="active-language">{language}</span>;
};

describe('LocalizedText', () => {
  let fetchMock;

  beforeEach(() => { fetchMock = stubLocaleCatalogFetch(vi); });

  afterEach(async () => {
    await resetInterfaceLanguage();
    vi.unstubAllGlobals();
  });

  it('isolates interpolated values in Arabic display without changing plain localized text', async () => {
    const source = 'Hide the files inside {directory} while keeping this result open.';
    const directory = 'Music/Artist - Album (2026)';
    const translation = 'أخفِ الملفات داخل Music/Artist - Album (2026) مع إبقاء هذه النتيجة مفتوحة.';

    await setInterfaceLanguage('ar');
    const { container } = render(
      <LocalizedText source={source} values={{ directory }} />,
    );

    const localized = container.firstElementChild;
    expect(localized).toHaveAttribute('lang', 'ar');
    expect(localized).toHaveAttribute('dir', 'rtl');
    expect(localized.textContent).toBe(translation);

    const isolatedValue = localized.querySelector('bdi');
    expect(isolatedValue).toHaveAttribute('dir', 'auto');
    expect(isolatedValue.textContent).toBe(directory);

    expect(interfaceText(source, { directory })).toBe(translation);
    expect(interfaceText(source, { directory })).not.toMatch(/[\u2066-\u2069]/);
  });

  it('keeps the last complete locale when another catalog fails to load', async () => {
    await setInterfaceLanguage('ar');
    fetchMock.mockRejectedValueOnce(new Error('catalog unavailable'));

    await setInterfaceLanguage('de');

    const { container, getByTestId } = render(
      <><ActiveLanguage /><LocalizedText source="Overview" /></>,
    );
    expect(getByTestId('active-language')).toHaveTextContent('ar');
    expect(localStorage.getItem('slskdn.interface-language')).toBe('ar');
    expect(container.querySelector('[lang="ar"]')).toHaveTextContent('ملخص');
    expect(interfaceText('Overview')).toBe('ملخص');
  });

  it('ignores an older locale request that finishes after the newer selection', async () => {
    let resolveGerman;
    fetchMock.mockImplementationOnce(() => new Promise((resolve) => { resolveGerman = resolve; }));
    const germanRequest = setInterfaceLanguage('de');

    await setInterfaceLanguage('fr');
    resolveGerman(new Response(JSON.stringify({ Overview: 'Übersicht' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }));
    await germanRequest;

    const { getByTestId } = render(<ActiveLanguage />);
    expect(getByTestId('active-language')).toHaveTextContent('fr');
    expect(localStorage.getItem('slskdn.interface-language')).toBe('fr');
  });
});
