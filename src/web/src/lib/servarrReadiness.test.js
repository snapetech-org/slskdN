import {
  buildServarrCompatibilityPreview,
  buildServarrReadiness,
  formatServarrCompatibilityReport,
  summarizeServarrReadiness,
} from './servarrReadiness';

describe('servarrReadiness', () => {
  it('marks a fully configured integration ready', () => {
    const checks = buildServarrReadiness({
      apiKey: 'fixture-key',
      autoImportCompleted: true,
      enabled: true,
      importPathFrom: '/downloads',
      importPathTo: '/library',
      syncWantedToWishlist: true,
      url: 'http://example.invalid:8686',
    });

    expect(checks.every((check) => check.ready)).toBe(true);
    expect(summarizeServarrReadiness(checks)).toEqual({
      ready: checks.length,
      status: 'Ready',
      total: checks.length,
    });
  });

  it('flags missing setup without exposing secrets', () => {
    const checks = buildServarrReadiness({
      enabled: true,
      importPathFrom: '/downloads',
      syncWantedToWishlist: false,
    });
    const summary = summarizeServarrReadiness(checks);

    expect(summary.status).toBe('Needs Setup');
    expect(checks.find((check) => check.id === 'api-key').ready).toBe(false);
    expect(checks.find((check) => check.id === 'path-map').ready).toBe(false);
  });

  it('builds a compatibility preview for wanted and import handoffs', () => {
    const preview = buildServarrCompatibilityPreview({
      apiKey: 'fixture-key',
      autoImportCompleted: true,
      enabled: true,
      importMode: 'move',
      importPathFrom: '/downloads',
      importPathTo: '/library',
      syncWantedToWishlist: true,
      url: 'http://example.invalid:8686',
    });

    expect(preview.summary.status).toBe('Ready');
    expect(preview.supportsCompletedImport).toBe(true);
    expect(preview.supportsWantedPull).toBe(true);
    expect(preview.actions).toEqual([]);
  });

  it('formats compatibility reports without secrets', () => {
    const report = formatServarrCompatibilityReport(
      buildServarrCompatibilityPreview({
        enabled: true,
        importMode: 'move',
        importPathFrom: '/downloads',
        syncWantedToWishlist: false,
      }),
    );

    expect(report).toContain('slskdN Servarr compatibility review');
    expect(report).toContain('Wanted pull: Needs attention');
    expect(report).toContain('Completed import: Needs attention');
    expect(report).toContain('- Pending: Base URL configured');
    expect(report).toContain('Enable completed import review');
    expect(report).not.toContain('fixture-key');
  });
});
