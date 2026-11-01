import React from 'react';
import { act, render } from '@testing-library/react';
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
    await act(async () => {
      await resetInterfaceLanguage();
    });
    vi.unstubAllGlobals();
  });

  it('keeps inherited-property names as ordinary fallback text in a selected locale', async () => {
    await act(async () => { await setInterfaceLanguage('es'); });
    for (const source of ['toString', 'constructor', '__proto__', 'hasOwnProperty']) {
      expect(interfaceText(source)).toBe(source);
      const view = render(<LocalizedText source={source} />);
      expect(view.container.textContent).toBe(source);
      view.unmount();
    }
  });

  it('isolates interpolated values in Arabic display without changing plain localized text', async () => {
    const source = 'Hide the files inside {directory} while keeping this result open.';
    const directory = 'Music/Artist - Album (2026)';
    const translation = 'أخفِ الملفات داخل Music/Artist - Album (2026) مع إبقاء هذه النتيجة مفتوحة.';

    await act(async () => {
      await setInterfaceLanguage('ar');
    });
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

  it.each(['es', 'ar'])(
    'isolates opaque placeholders in English fallback when %s is selected',
    async (language) => {
      const source = 'Diagnostic placeholder boundary for {externalValue}.';
      const externalValue = 'العربية: provider-42';

      await act(async () => {
        await setInterfaceLanguage(language);
      });
      const { container } = render(
        <LocalizedText source={source} values={{ externalValue }} />,
      );

      const fallback = container.querySelector('[lang="en"]');
      expect(fallback).toHaveAttribute('dir', 'ltr');
      expect(fallback.textContent).toBe(source.replace('{externalValue}', externalValue));
      expect(fallback.querySelector('bdi')).toHaveAttribute('dir', 'auto');
      expect(fallback.querySelector('bdi')).toHaveAttribute('lang', 'und');
      expect(fallback.querySelector('bdi').textContent).toBe(externalValue);
    },
  );

  it('keeps the last complete locale when another catalog fails to load', async () => {
    await act(async () => {
      await setInterfaceLanguage('ar');
    });
    fetchMock.mockRejectedValueOnce(new Error('catalog unavailable'));

    await act(async () => {
      await setInterfaceLanguage('de');
    });

    const { container, getByTestId } = render(
      <><ActiveLanguage /><LocalizedText source="Overview" /></>,
    );
    expect(getByTestId('active-language')).toHaveTextContent('ar');
    expect(localStorage.getItem('slskdn.interface-language')).toBe('ar');
    expect(container.querySelector('[lang="ar"]')).toHaveTextContent('ملخص');
    expect(interfaceText('Overview')).toBe('ملخص');
  });

  it('localizes fixed server errors while preserving unmatched diagnostics', async () => {
    await act(async () => {
      await setInterfaceLanguage('es');
    });
    const dynamicDiagnostic = 'Provider returned diagnostic 429 for request abc-123';
    const { container } = render(
      <>
        <LocalizedText source="Failed to sync with peer" />
        <span>|</span>
        <LocalizedText source={dynamicDiagnostic} />
      </>,
    );

    expect(container.textContent).toBe(`No se pudo sincronizar con el par|${dynamicDiagnostic}`);
  });

  it('ignores an older locale request that finishes after the newer selection', async () => {
    let resolveGerman;
    fetchMock.mockImplementationOnce(() => new Promise((resolve) => { resolveGerman = resolve; }));
    let germanRequest;
    act(() => {
      germanRequest = setInterfaceLanguage('de');
    });

    await act(async () => {
      await setInterfaceLanguage('fr');
    });
    await act(async () => {
      resolveGerman(new Response(JSON.stringify({ Overview: 'Übersicht' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }));
      await germanRequest;
    });

    const { getByTestId } = render(<ActiveLanguage />);
    expect(getByTestId('active-language')).toHaveTextContent('fr');
    expect(localStorage.getItem('slskdn.interface-language')).toBe('fr');
  });
});
