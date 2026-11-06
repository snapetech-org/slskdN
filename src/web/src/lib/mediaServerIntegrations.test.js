import {
  buildMediaServerExecutionContract,
  buildMediaServerPathDiagnostic,
  buildMediaServerSyncPreview,
  formatMediaServerExecutionContractReport,
  formatMediaServerSyncReport,
  mediaServerAutomationContracts,
  mediaServerAdapters,
} from './mediaServerIntegrations';

describe('mediaServerIntegrations', () => {
  it('lists common media-server adapters without making them required', () => {
    expect(mediaServerAdapters.map((adapter) => adapter.id)).toEqual([
      'plex',
      'jellyfin',
      'navidrome',
    ]);
    expect(mediaServerAdapters.every((adapter) => adapter.requiresToken)).toBe(true);
  });

  it('lists visible live automation contracts with conservative defaults', () => {
    expect(mediaServerAutomationContracts.map((contract) => contract.id)).toEqual([
      'playHistoryImport',
      'scrobbleExport',
      'acquisitionQueue',
      'completedScan',
      'confirmedFileActions',
    ]);
  });

  it('detects matching report paths', () => {
    expect(
      buildMediaServerPathDiagnostic({
        localPath: '/media/music/Album/track.flac',
        serverPath: '/media/music/Album/track.flac',
      }),
    ).toEqual(
      expect.objectContaining({
        color: 'green',
        status: 'Aligned',
      }),
    );
  });

  it('detects valid remote path mappings', () => {
    expect(
      buildMediaServerPathDiagnostic({
        localPath: '/downloads/complete/Album/track.flac',
        remotePathFrom: '/downloads/complete',
        remotePathTo: '/library/music',
        serverPath: '/library/music/Album/track.flac',
      }),
    ).toEqual(
      expect.objectContaining({
        mappedPath: '/library/music/Album/track.flac',
        status: 'Mapped',
      }),
    );
  });

  it('warns when paths need mapping', () => {
    expect(
      buildMediaServerPathDiagnostic({
        localPath: '/downloads/complete/Album/track.flac',
        serverPath: '/library/music/Album/track.flac',
      }),
    ).toEqual(
      expect.objectContaining({
        color: 'orange',
        status: 'Needs Mapping',
      }),
    );
  });

  it('does not apply a path mapping to a sibling with the same string prefix', () => {
    expect(
      buildMediaServerPathDiagnostic({
        localPath: '/downloads-old/Album/track.flac',
        remotePathFrom: '/downloads',
        remotePathTo: '/library',
        serverPath: '/library-old/Album/track.flac',
      }),
    ).toEqual(
      expect.objectContaining({
        status: 'Needs Mapping',
      }),
    );
  });

  it('builds an explicit sync readiness preview', () => {
    const preview = buildMediaServerSyncPreview({
      adapterId: 'jellyfin',
      baseUrl: 'http://media.example.invalid',
      localPath: '/downloads/complete/Album/track.flac',
      remotePathFrom: '/downloads/complete',
      remotePathTo: '/library/music',
      serverPath: '/library/music/Album/track.flac',
      tokenConfigured: true,
    });

    expect(preview.status).toBe('Ready for live adapter');
    expect(preview.readyCount).toBe(3);
    expect(preview.adapter.label).toBe('Jellyfin / Emby');
  });

  it('formats sync review reports with missing actions', () => {
    const report = formatMediaServerSyncReport(
      buildMediaServerSyncPreview({
        adapterId: 'navidrome',
        localPath: '/downloads/complete/Album/track.flac',
        serverPath: '/library/music/Album/track.flac',
      }),
    );

    expect(report).toContain('slskdN media-server sync review');
    expect(report).toContain('Adapter: Navidrome');
    expect(report).toContain('Pending: Base URL configured');
    expect(report).toContain('Pending: Path mapping ready');
  });

  it('builds a live execution contract from adapter readiness and automation gates', () => {
    const syncPreview = buildMediaServerSyncPreview({
      adapterId: 'plex',
      baseUrl: 'http://media.example.invalid',
      localPath: '/downloads/complete/Album/track.flac',
      remotePathFrom: '/downloads/complete',
      remotePathTo: '/library/music',
      serverPath: '/library/music/Album/track.flac',
      tokenConfigured: true,
    });
    const contract = buildMediaServerExecutionContract({
      enabledAutomations: {
        acquisitionQueue: true,
        completedScan: true,
        playHistoryImport: true,
        scrobbleExport: true,
      },
      syncPreview,
      userMappingConfigured: true,
    });

    expect(contract.status).toBe('Execution contract ready');
    expect(contract.enabledCount).toBe(4);
    expect(contract.enabledReadyCount).toBe(4);
    expect(
      contract.automations.find((automation) => automation.id === 'scrobbleExport'),
    ).toEqual(
      expect.objectContaining({
        enabled: true,
        ready: true,
      }),
    );
  });

  it('keeps live execution blocked when user mapping and confirmation gates are missing', () => {
    const contract = buildMediaServerExecutionContract({
      confirmationRequired: false,
      enabledAutomations: {
        playHistoryImport: true,
        scrobbleExport: true,
      },
      syncPreview: buildMediaServerSyncPreview({
        adapterId: 'navidrome',
      }),
      userMappingConfigured: false,
    });

    expect(contract.status).toBe('Execution contract blocked');
    expect(contract.enabledReadyCount).toBe(0);
    expect(
      contract.automations.find((automation) => automation.id === 'playHistoryImport')
        .blockedReasons,
    ).toContain('User mapping is required.');

    const report = formatMediaServerExecutionContractReport(contract);
    expect(report).toContain('slskdN media-server execution contract');
    expect(report).toContain('Needs attention: User mapping configured');
    expect(report).toContain('Enabled / Needs attention: Scrobble and rating export');
  });
});
