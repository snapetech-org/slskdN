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

  it('localizes the six report headings without rewriting provider or user fields', () => {
    const evidence = formatMeshEvidenceReviewReport({ summary: { total: 0, accepted: 0, rejected: 0 }, results: [] });
    const realm = formatRealmSubjectIndexConflictReport({ report: { realmId: 'provider:{room}' } });
    const automation = formatAutomationRunHistoryReport([]);
    const graph = formatDiscoveryGraphBranchReport({
      graphTitle: 'user:{count}', seedNodeId: 'node/raw', visibleNodeCount: 0, visibleEdgeCount: 0,
      maxDepth: 1, minNodeWeight: 0, nodeTypeCounts: {}, edgeTypeCounts: {},
      routeSuggestions: [], evidenceSummary: [], searchQueries: [],
    });
    const preview = buildMediaServerSyncPreview();
    const contract = buildMediaServerExecutionContract({ syncPreview: preview });
    const reports = [evidence, realm, automation, graph, formatMediaServerSyncReport(preview), formatMediaServerExecutionContractReport(contract)];

    for (const report of reports) expect(report).toMatch(/^localized:slskdN /);
    expect(realm).toContain('provider:{room}');
    expect(graph).toContain('user:{count}');
  });
});
