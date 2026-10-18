import {
  buildSetupHealthChecks,
  formatSetupHealthReport,
} from './setupHealthCheck';

describe('setupHealthCheck', () => {
  it('summarizes ready local setup state without exposing credentials', () => {
    const summary = buildSetupHealthChecks({
      options: {
        directories: {
          downloads: '/fixture/downloads',
        },
        remoteConfiguration: false,
        web: {
          authentication: {
            apiKey: 'fixture-api-key',
          },
          urlBase: '/slskd',
        },
        shares: {
          directories: ['/fixture/music'],
        },
      },
      state: {
        automation: {
          recipes: [{ id: 'local-diagnostics' }],
        },
        connected: true,
        downloads: [],
        jobs: [],
        pendingRestart: false,
        user: {
          username: 'fixture_user',
        },
      },
    });

    expect(summary.readiness).toBe('Ready');
    expect(summary.score).toBe(100);
    expect(summary.totals).toEqual({ fail: 0, info: 0, pass: 12, warn: 0 });
    expect(summary.checks.map((item) => item.area)).toContain('Web mounting');
    expect(summary.groups).toEqual(
      expect.objectContaining({
        Access: expect.objectContaining({ pass: 3 }),
        Network: expect.objectContaining({ pass: 1 }),
        Operations: expect.objectContaining({ pass: 6 }),
        Storage: expect.objectContaining({ pass: 2 }),
      }),
    );
  });

  it('flags missing transfer prerequisites with concrete actions', () => {
    const summary = buildSetupHealthChecks({
      options: {
        shares: {
          directories: [],
        },
      },
      state: {
        connected: false,
      },
    });

    expect(summary.readiness).toBe('Needs attention');
    expect(summary.totals.fail).toBe(2);
    expect(summary.totals.warn).toBeGreaterThanOrEqual(1);
    expect(summary.nextSteps.length).toBeGreaterThan(0);
    expect(summary.checks.find((item) => item.area === 'Downloads')).toMatchObject({
      status: 'fail',
      summary: 'Download path missing',
    });
  });

  it('uses the live state contract for Soulseek connectivity', () => {
    const summary = buildSetupHealthChecks({
      state: {
        server: {
          isConnected: true,
          isLoggedIn: true,
          state: 'Connected, LoggedIn',
        },
      },
    });

    expect(summary.checks.find((item) => item.area === 'Soulseek session')).toMatchObject({
      status: 'pass',
      summary: 'Connected',
    });
  });

  it('recognizes current integration and API key collection shapes', () => {
    const summary = buildSetupHealthChecks({
      options: {
        integration: {
          youTube: {
            apiKey: '',
            enabled: true,
          },
        },
        web: {
          authentication: {
            apiKeys: {
              automation: {
                key: '*****',
              },
            },
          },
        },
      },
    });

    expect(summary.checks.find((item) => item.area === 'API access')).toMatchObject({
      status: 'pass',
      summary: 'API key configured',
    });
    expect(summary.checks.find((item) => item.area === 'Provider credentials')).toMatchObject({
      status: 'info',
      summary: 'Optional provider credential gaps',
    });
  });

  it('formats a copyable report from the local checks', () => {
    const summary = buildSetupHealthChecks({
      options: {},
      state: {
        connected: false,
      },
    });
    const report = formatSetupHealthReport(summary);

    expect(report).toContain('slskdN setup health check');
    expect(report).toContain('Score:');
    expect(report).toContain('Next steps:');
    expect(report).toContain('[FAIL] Network / Soulseek session: Not connected');
    expect(report).toContain('Action: Verify credentials');
  });

  it('flags disabled auth, enabled provider credential gaps, failed jobs, and queue pressure', () => {
    const summary = buildSetupHealthChecks({
      options: {
        directories: {
          downloads: '/fixture/downloads',
        },
        integrations: {
          youtube: {
            enabled: true,
          },
        },
        shares: {
          directories: ['/fixture/music'],
        },
        web: {
          authentication: {
            disabled: true,
          },
        },
      },
      state: {
        connected: true,
        downloads: Array.from({ length: 26 }, (_value, index) => ({
          id: index,
          state: 'Queued',
        })),
        jobs: [{ id: 'job-1', state: 'Failed' }],
        user: {
          username: 'fixture_user',
        },
      },
    });

    expect(summary.readiness).toBe('Needs attention');
    expect(summary.checks.find((item) => item.area === 'API access')).toMatchObject({
      status: 'fail',
      summary: 'Authentication disabled',
    });
    expect(summary.checks.find((item) => item.area === 'Provider credentials')).toMatchObject({
      status: 'info',
      summary: 'Optional provider credential gaps',
    });
    expect(summary.checks.find((item) => item.area === 'Queue pressure')).toMatchObject({
      status: 'warn',
      summary: 'Queue pressure high',
    });
    expect(summary.checks.find((item) => item.area === 'Job failures')).toMatchObject({
      status: 'warn',
      summary: 'Failed jobs present',
    });
  });
});
