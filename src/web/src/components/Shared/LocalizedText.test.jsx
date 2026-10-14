import React from 'react';
import { render } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { interfaceText, resetInterfaceLanguage, setInterfaceLanguage } from '../../lib/interfaceLocale';
import { stubLocaleCatalogFetch } from '../../test/localeCatalogFetchMock';
import LocalizedText from './LocalizedText';

describe('LocalizedText', () => {
  beforeEach(() => stubLocaleCatalogFetch(vi));

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
});
