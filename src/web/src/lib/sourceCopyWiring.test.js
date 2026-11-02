import { beforeEach, describe, expect, it, vi } from 'vitest';
import { interfaceText } from './interfaceLocale';
import { evaluateMeshEvidenceEntries, formatMeshEvidenceReviewReport } from './meshEvidencePolicy';
import { formatRealmSubjectIndexConflictReport } from './realmSubjectIndexes';
import { formatAutomationRunHistoryReport } from './automationRecipes';
import { formatDiscoveryGraphBranchReport } from './discoveryGraph';
import {
  buildMediaServerSyncPreview,
  buildMediaServerExecutionContract,
  formatMediaServerSyncReport,
  formatMediaServerExecutionContractReport,
} from './mediaServerIntegrations';
import { buildSetupHealthChecks, formatSetupHealthReport } from './setupHealthCheck';
import { buildNetworkHealthScore, formatNetworkHealthReport } from './networkHealthScore';
import { buildSearchActionPreview, formatSearchActionPreview } from './searchActionPreview';
import { buildServarrCompatibilityPreview, formatServarrCompatibilityReport } from './servarrReadiness';
import { buildPlayerRadioPlan, getPlayerRadioCopyText } from './playerRadio';

const locale = vi.hoisted(() => ({ prefix: 'localized:' }));
vi.mock('./interfaceLocale', () => ({
  interfaceText: vi.fn((source, parameters = {}) => locale.prefix + source.replace(
    /\{([a-zA-Z][a-zA-Z0-9_]*)\}/g,
    (token, name) => Object.hasOwn(parameters, name) ? String(parameters[name]) : token,
  )),
}));

beforeEach(() => { vi.clearAllMocks(); locale.prefix = 'localized:'; });

describe('app-authored helper source boundaries', () => {
  it('localizes fixed mesh rejection reasons while retaining opaque provenance values', () => {
    const tier = 'provider:{minimum}/العربية';
    const review = evaluateMeshEvidenceEntries([{
      confidence: 0,
      containsExactHoldings: true,
      containsPath: true,
      containsRawListeningHistory: true,
      provenance: { trustTier: tier },
      subject: 'user/subject',
      type: 'provider-type',
      witnessCount: 0,
    }], {
      inboundTrustTier: 'disabled',
      evidenceReview: { minimumConfidence: 0.7, minimumWitnesses: 2 },
    });

    expect(review.rejected[0].reasons).toHaveLength(8);
    expect(review.rejected[0].reasons).toContainEqual({ id: 'untrusted-tier', parameters: { tier } });
    expect(interfaceText).not.toHaveBeenCalled();
    const frozen = JSON.stringify(review);
    const report = formatMeshEvidenceReviewReport(review);
    expect(report).toContain(`localized:untrusted provenance tier: ${tier}`);
    expect(report).not.toMatch(/[\u2066-\u2069]/);
    locale.prefix = 'new-language:';
    expect(formatMeshEvidenceReviewReport(review)).toContain(`new-language:untrusted provenance tier: ${tier}`);
    expect(JSON.stringify(review)).toBe(frozen);
    expect(review.rejected[0].subject).toBe('user/subject');
    expect(review.rejected[0].provenance.trustTier).toBe(tier);
    expect(interfaceText).toHaveBeenCalledWith('untrusted provenance tier: {tier}', { tier });
  });

  it('localizes copied report bodies without rewriting provider or user fields', () => {
    const evidence = formatMeshEvidenceReviewReport({ summary: { total: 0, accepted: 0, rejected: 0 }, results: [] });
    const realm = formatRealmSubjectIndexConflictReport({ report: { realmId: 'provider:{room}' } });
    const automation = formatAutomationRunHistoryReport([{
      enabled: true,
      lastDryRunAt: null,
      lastDryRunReport: null,
      lastRunAt: '2026-10-31T00:00:00.000Z',
      lastRunReport: {
        failed: 1,
        fileImpact: 'Downloads after approval',
        networkImpact: 'Public peers possible',
        recipeId: 'wishlist-retry',
        skipped: 3,
        started: 2,
        summary: 'Ran 2 Wishlist searches; 1 failed; 3 skipped.',
      },
      recipeId: 'wishlist-retry',
      title: 'Wishlist Retry',
    }]);
    const graph = formatDiscoveryGraphBranchReport({
      graphTitle: 'user:{count}', seedNodeId: 'node/raw', visibleNodeCount: 0, visibleEdgeCount: 0,
      maxDepth: 1, minNodeWeight: 0, nodeTypeCounts: {}, edgeTypeCounts: {},
      routeSuggestions: [], evidenceSummary: [], searchQueries: [],
    });
    const preview = buildMediaServerSyncPreview();
    const contract = buildMediaServerExecutionContract({ syncPreview: preview });
    const setupHealth = formatSetupHealthReport(buildSetupHealthChecks({
      options: {
        directories: { downloads: '/downloads' },
        shares: { directories: ['/music'] },
        web: {
          authentication: { apiKey: 'configured', disabled: false },
          urlBase: '/ui/{room}',
        },
      },
      state: { connected: true, user: { username: 'user:{room}' } },
    }));
    const sync = formatMediaServerSyncReport(preview);
    const execution = formatMediaServerExecutionContractReport(contract);
    const reports = [evidence, realm, automation, graph, setupHealth, sync, execution];

    for (const report of reports) expect(report).toMatch(/^localized:slskdN /);
    expect(evidence).toContain('localized:Total: 0');
    expect(realm).toContain('localized:Realm: provider:{room}');
    expect(automation).toContain('localized:  Run summary: localized:Ran 2 Wishlist searches; 1 failed; 3 skipped.');
    expect(graph).toContain('user:{count}');
    expect(graph).toContain('localized:Visible nodes: 0');
    expect(setupHealth).toContain('localized:Configured URL base: /ui/{room}');
    expect(sync).toContain('localized:Path message: localized:Enter both paths to check whether slskdN and the media server agree.');
    expect(execution).toContain('localized:Contract checks:');
  });

  it('localizes allowlisted media-server copy while preserving unknown provider text', () => {
    const preview = buildMediaServerSyncPreview();
    const sync = formatMediaServerSyncReport(preview);

    expect(sync).toContain('localized:Status: localized:Needs setup');
    expect(sync).toContain('localized:Path status: localized:Incomplete');
    expect(interfaceText).toHaveBeenCalledWith('Configure the media-server base URL before enabling live scans.');
    expect(interfaceText).toHaveBeenCalledWith('Base URL configured');

    const unknownPreview = {
      ...preview,
      checks: [{
        ...preview.checks[0],
        action: 'provider action {room}',
        label: 'provider label {room}',
        ready: false,
      }],
      pathDiagnostic: {
        ...preview.pathDiagnostic,
        message: 'provider message {room}',
        status: 'provider status {room}',
      },
      status: 'provider status {room}',
    };
    const unknownSync = formatMediaServerSyncReport(unknownPreview);

    expect(unknownSync).toContain('localized:Status: provider status {room}');
    expect(unknownSync).toContain('localized:Path status: provider status {room}');
    expect(unknownSync).toContain('localized:Path message: provider message {room}');
    expect(unknownSync).toContain('localized:- localized:Pending: provider label {room}');
    expect(unknownSync).toContain('localized:  Action: provider action {room}');
    expect(interfaceText).not.toHaveBeenCalledWith('provider status {room}');
    expect(interfaceText).not.toHaveBeenCalledWith('provider message {room}');
    expect(interfaceText).not.toHaveBeenCalledWith('provider label {room}');
    expect(interfaceText).not.toHaveBeenCalledWith('provider action {room}');

    const contract = buildMediaServerExecutionContract({ syncPreview: preview });
    formatMediaServerExecutionContractReport(contract);
    expect(interfaceText).toHaveBeenCalledWith('Execution contract blocked');
    expect(interfaceText).toHaveBeenCalledWith('User mapping is required.');
    expect(interfaceText).toHaveBeenCalledWith('Play history import');

    const readyPreview = buildMediaServerSyncPreview({
      baseUrl: 'https://media.example.invalid',
      localPath: '/media/music',
      serverPath: '/media/music',
      tokenConfigured: true,
    });
    const readyContract = buildMediaServerExecutionContract({
      syncPreview: readyPreview,
      userMappingConfigured: true,
    });
    formatMediaServerExecutionContractReport(readyContract);
    expect(interfaceText).toHaveBeenCalledWith('Execution contract ready');
  });

  it('localizes generated player, network, search, and Servarr copy with fixed sources', () => {
    const radio = getPlayerRadioCopyText(buildPlayerRadioPlan({
      album: 'Fixture Album',
      artist: 'Fixture Artist',
      genre: 'Fixture Genre',
      title: 'Fixture Track',
    }));
    expect(radio).toContain('localized:Similar track seed');
    expect(radio).toContain('localized:Album neighborhood');
    expect(radio).toContain('localized:Artist and genre seed');
    expect(radio).toContain('localized:Artist radio seed');

    const network = formatNetworkHealthReport(buildNetworkHealthScore({
      stats: { dht: { isEnabled: false } },
    }));
    expect(network).toContain('localized:- [localized:Info] localized:DHT: localized:DHT rendezvous disabled');

    const search = formatSearchActionPreview({
      candidateScore: null,
      fileCount: 0,
      filenames: [],
      providerLabels: ['soulseek'],
      route: 'download',
      totalSizeBytes: 0,
      username: 'peer',
      warnings: [
        'No free upload slot is currently advertised',
        'Local caution signals exist for this peer',
        'Local quality signals are ignored by reviewer override',
        'opaque warning:{room}',
      ],
    });
    expect(search).toContain('localized:No free upload slot is currently advertised');
    expect(search).toContain('localized:Local caution signals exist for this peer');
    expect(search).toContain('localized:Local quality signals are ignored by reviewer override');
    expect(search).toContain('opaque warning:{room}');
    expect(interfaceText).not.toHaveBeenCalledWith('opaque warning:{room}');

    const servarr = formatServarrCompatibilityReport(buildServarrCompatibilityPreview({
      enabled: true,
      importMode: 'move',
      importPathFrom: '/downloads',
    }));
    expect(servarr).toContain('localized:Enable completed import review before using move-style import handoff.');
  });

  it('preserves unknown setup-health report fields as opaque data', () => {
    const value = 'provider:{room}/العربية';
    const report = formatSetupHealthReport({
      checks: [{
        action: value,
        area: value,
        evidence: value,
        group: value,
        status: value,
        summary: value,
      }],
      nextSteps: [{
        action: value,
        area: value,
        destination: undefined,
        group: value,
        severity: value,
      }],
      readiness: value,
      score: 0,
      totals: { fail: 0, info: 0, pass: 0, warn: 0 },
    });

    expect(report).toContain(`Readiness: ${value}`);
    expect(report).toContain(`${value} / ${value}: ${value}`);
    expect(report).toContain(`Evidence: ${value}`);
    expect(report).toContain(`Action: ${value}`);
    expect(interfaceText).not.toHaveBeenCalledWith(value);
  });
});
