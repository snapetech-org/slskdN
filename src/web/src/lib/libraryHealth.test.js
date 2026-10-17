// <copyright file="libraryHealth.test.js" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import api from './api';
import * as libraryHealth from './libraryHealth';

vi.mock('./api', () => ({
  __esModule: true,
  default: {
    get: vi.fn(),
    patch: vi.fn(),
    post: vi.fn(),
  },
}));

describe('libraryHealth', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('starts scans through the versioned API client path', async () => {
    api.post.mockResolvedValue({ data: { scanId: 'scan-1' } });

    await libraryHealth.startScan('/music');

    expect(api.post).toHaveBeenCalledWith('/library/health/scans', {
      includeSpectralAnalysis: false,
      includeSubdirectories: true,
      libraryPath: '/music',
    });
  });

  it('requests spectral analysis only when asked', async () => {
    api.post.mockResolvedValue({ data: { scanId: 'scan-1' } });

    await libraryHealth.startScan('/music', { includeSpectralAnalysis: true });

    expect(api.post).toHaveBeenCalledWith('/library/health/scans', {
      includeSpectralAnalysis: true,
      includeSubdirectories: true,
      libraryPath: '/music',
    });
  });

  it('loads scan status without embedding an extra api prefix', async () => {
    api.get.mockResolvedValue({ data: { status: 'Completed' } });

    await libraryHealth.getScanStatus('scan/1');

    expect(api.get).toHaveBeenCalledWith('/library/health/scans/scan%2F1');
  });

  it('loads summary and issues with encoded query parameters', async () => {
    api.get.mockResolvedValue({ data: {} });

    await libraryHealth.getSummary('/music/Artist Name');
    await libraryHealth.getIssues({ libraryPath: '/music/Artist Name', limit: 25 });

    expect(api.get).toHaveBeenCalledWith(
      '/library/health/summary?libraryPath=%2Fmusic%2FArtist%20Name',
    );
    expect(api.get).toHaveBeenCalledWith(
      '/library/health/issues?libraryPath=%2Fmusic%2FArtist+Name&limit=25',
    );
  });

  it('loads the bounded dashboard through one encoded request', async () => {
    api.get.mockResolvedValue({ data: {} });

    await libraryHealth.getDashboard('/music/Artist Name', 8, 75);

    expect(api.get).toHaveBeenCalledWith(
      '/library/health/dashboard?artistLimit=8&issueLimit=75&libraryPath=%2Fmusic%2FArtist+Name',
    );
  });

  it('updates and remediates issues through versioned paths', async () => {
    api.patch.mockResolvedValue({});
    api.post.mockResolvedValue({});

    await libraryHealth.updateIssueStatus('issue/1', 'Ignored');
    await libraryHealth.createRemediationJob(['issue-1']);

    expect(api.patch).toHaveBeenCalledWith('/library/health/issues/issue%2F1', {
      status: 'Ignored',
    });
    expect(api.post).toHaveBeenCalledWith('/library/health/issues/fix', {
      issueIds: ['issue-1'],
    });
  });
});
