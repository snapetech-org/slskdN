import '@testing-library/jest-dom';
import * as optionsApi from '../../lib/options';
import DownloadExclusionsModal from './DownloadExclusionsModal';
import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import YAML from 'yaml';
import { resetInterfaceLanguage, setInterfaceLanguage } from '../../lib/interfaceLocale';
import { stubLocaleCatalogFetch } from '../../test/localeCatalogFetchMock';

vi.mock('../../lib/options', () => ({
  getYaml: vi.fn(),
  updateYaml: vi.fn(),
}));

vi.mock('react-toastify', () => ({
  toast: {
    success: vi.fn(),
  },
}));

describe('DownloadExclusionsModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    stubLocaleCatalogFetch(vi);
  });

  afterEach(async () => {
    await resetInterfaceLanguage();
    vi.unstubAllGlobals();
  });

  it('loads and saves filters without dropping unrelated YAML', async () => {
    optionsApi.getYaml.mockResolvedValue(
      'web:\n  authentication: {}\nfilters:\n  search:\n    request: [lossless]\n',
    );
    optionsApi.updateYaml.mockResolvedValue({});
    const onClose = vi.fn();
    const onSaved = vi.fn();

    render(
      <DownloadExclusionsModal
        onClose={onClose}
        onSaved={onSaved}
        open
        options={{
          filters: {
            download: {
              exclude: ['acapella'],
            },
          },
          remoteConfiguration: true,
        }}
      />,
    );

    const field = screen.getByLabelText('Global download exclusions');
    expect(field).toHaveValue('acapella');

    fireEvent.change(field, {
      target: { value: 'acapella\ninstrumental\na cappella' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Save download filters' }));

    await waitFor(() => expect(optionsApi.updateYaml).toHaveBeenCalledTimes(1));

    const saved = YAML.parse(optionsApi.updateYaml.mock.calls[0][0].yaml);
    expect(saved.web.authentication).toEqual({});
    expect(saved.filters.search.request).toEqual(['lossless']);
    expect(saved.filters.download.exclude).toEqual([
      'acapella',
      'instrumental',
      'a cappella',
    ]);
    expect(onSaved).toHaveBeenCalledWith([
      'acapella',
      'instrumental',
      'a cappella',
    ]);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('keeps the editor read-only when remote configuration is disabled', () => {
    render(
      <DownloadExclusionsModal
        onClose={vi.fn()}
        open
        options={{ remoteConfiguration: false }}
      />,
    );

    expect(screen.getByText(/Remote configuration is disabled/)).toBeInTheDocument();
    expect(screen.getByLabelText('Global download exclusions')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Save download filters' })).toBeDisabled();
  });

  it('localizes the exclusion field label and accessible name in Arabic', async () => {
    await setInterfaceLanguage('ar');
    render(
      <DownloadExclusionsModal
        onClose={vi.fn()}
        open
        options={{ remoteConfiguration: true }}
      />,
    );

    const field = screen.getByRole('textbox', { name: 'استثناءات التنزيل العالمية' });
    expect(field).toHaveAttribute('lang', 'ar');
    expect(field).toHaveAttribute('dir', 'rtl');
    expect(screen.getByText('مصطلحات محظورة في أسماء الملفات/المسارات')).toHaveAttribute('lang', 'ar');
    expect(screen.getByText('مصطلحات محظورة في أسماء الملفات/المسارات')).toHaveAttribute('dir', 'rtl');
  });
});
