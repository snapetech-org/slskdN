// <copyright file="AppRoutes.test.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import AppRoutes from './AppRoutes';
import { getTransferSummary } from '../lib/reports';
import React, { Suspense } from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../lib/reports', () => ({ getTransferSummary: vi.fn() }));
vi.mock('./System/System', () => ({
  default: () => <div data-testid="system-route">System</div>,
}));

const renderRoutes = (initialEntry, isAgent = false) =>
  render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Suspense fallback={<div>Loading route</div>}>
        <AppRoutes
          applicationOptions={{}}
          applicationState={{ server: { isConnected: true } }}
          isAgent={isAgent}
          theme="dark"
        />
      </Suspense>
    </MemoryRouter>,
  );

describe('AppRoutes', () => {
  beforeEach(() => {
    getTransferSummary.mockResolvedValue({ Download: {}, Upload: {} });
  });

  it('uses the dashboard as the normal home and unknown-route destination', async () => {
    const { unmount } = renderRoutes('/');
    expect(await screen.findByRole('heading', { name: 'Transfer overview' })).toBeInTheDocument();

    unmount();
    renderRoutes('/unknown-page');
    expect(await screen.findByRole('heading', { name: 'Transfer overview' })).toBeInTheDocument();
  });

  it('keeps agent mode in System when the home route is opened', async () => {
    renderRoutes('/', true);
    expect(await screen.findByTestId('system-route')).toBeInTheDocument();
  });
});
