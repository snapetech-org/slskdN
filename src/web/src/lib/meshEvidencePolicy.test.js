import {
  getMeshEvidencePolicy,
  getMeshEvidencePolicySummary,
  evaluateMeshEvidenceEntries,
  formatMeshEvidenceReviewReport,
  meshEvidencePolicyStorageKey,
  parseMeshEvidenceReviewInput,
  resetMeshEvidencePolicy,
  setMeshEvidenceInboundTrustTier,
  setMeshEvidenceOutboundEnabled,
} from './meshEvidencePolicy';

describe('meshEvidencePolicy', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('defaults to private inbound and outbound mesh evidence handling', () => {
    const policy = getMeshEvidencePolicy();
    const summary = getMeshEvidencePolicySummary(policy);

    expect(policy.inboundTrustTier).toBe('disabled');
    expect(Object.values(policy.outbound).every((enabled) => !enabled)).toBe(true);
    expect(policy.provenanceRequired).toBe(true);
    expect(summary.privateByDefault).toBe(true);
  });

  it('persists inbound trust tier selection', () => {
    const policy = setMeshEvidenceInboundTrustTier('trusted');

    expect(policy.inboundTrustTier).toBe('trusted');
    expect(JSON.parse(localStorage.getItem(meshEvidencePolicyStorageKey))).toEqual(
      expect.objectContaining({
        inboundTrustTier: 'trusted',
        evidenceReview: {
          minimumConfidence: 0.7,
          minimumWitnesses: 2,
        },
        provenanceRequired: true,
      }),
    );
  });

  it('persists explicit outbound evidence opt-ins', () => {
    const policy = setMeshEvidenceOutboundEnabled('hashVerification', true);
    const summary = getMeshEvidencePolicySummary(policy);

    expect(policy.outbound.hashVerification).toBe(true);
    expect(policy.outbound.metadataCorrection).toBe(false);
    expect(summary.outboundEnabled).toBe(true);
    expect(summary.enabledOutbound.map((item) => item.id)).toEqual([
      'hashVerification',
    ]);
  });

  it('sanitizes invalid stored policy data', () => {
    localStorage.setItem(
      meshEvidencePolicyStorageKey,
      JSON.stringify({
        inboundTrustTier: 'everyone',
        outbound: {
          hashVerification: true,
          rawLibraryDump: true,
        },
        provenanceRequired: false,
      }),
    );

    const policy = getMeshEvidencePolicy();

    expect(policy.inboundTrustTier).toBe('disabled');
    expect(policy.outbound.hashVerification).toBe(true);
    expect(policy.outbound.rawLibraryDump).toBeUndefined();
    expect(policy.provenanceRequired).toBe(true);
  });

  it('resets policy to private defaults', () => {
    setMeshEvidenceInboundTrustTier('realm');
    setMeshEvidenceOutboundEnabled('metadataCorrection', true);

    const policy = resetMeshEvidencePolicy();

    expect(policy).toEqual(getMeshEvidencePolicy());
    expect(localStorage.getItem(meshEvidencePolicyStorageKey)).toBeNull();
  });

  it('evaluates inbound evidence against provenance, trust, privacy, and k-anonymity gates', () => {
    const policy = setMeshEvidenceInboundTrustTier('realm');
    const review = evaluateMeshEvidenceEntries(
      [
        {
          confidence: 0.91,
          provenance: {
            peerId: 'fixture-peer',
            signature: 'fixture-signature',
            trustTier: 'realm',
          },
          subject: 'mbid:recording:fixture',
          type: 'metadataCorrection',
          witnessCount: 3,
        },
        {
          confidence: 0.95,
          containsPath: true,
          provenance: {
            peerId: 'unknown-peer',
            signature: 'fixture-signature',
            trustTier: 'untrusted',
          },
          subject: 'private-path',
          type: 'releaseCompleteness',
          witnessCount: 1,
        },
      ],
      policy,
    );

    expect(review.summary).toEqual({
      accepted: 1,
      rejected: 1,
      total: 2,
    });
    expect(review.rejected[0].reasons).toEqual(
      expect.arrayContaining([
        { id: 'untrusted-tier', parameters: { tier: 'untrusted' } },
        { id: 'few-witnesses', parameters: { minimum: 2 } },
        { id: 'contains-path', parameters: {} },
      ]),
    );
  });

  it('parses and formats mesh evidence review reports', () => {
    const entries = parseMeshEvidenceReviewInput(
      JSON.stringify({
        evidence: [
          {
            confidence: 0.1,
            subject: 'fixture',
            type: 'fakeLosslessWarning',
          },
        ],
      }),
    );
    const report = formatMeshEvidenceReviewReport(
      evaluateMeshEvidenceEntries(entries, getMeshEvidencePolicy()),
    );

    expect(entries).toHaveLength(1);
    expect(report).toContain('slskdN mesh evidence review');
    expect(report).toContain('[REJECT] fakeLosslessWarning fixture');
    expect(report).toContain('inbound mesh evidence disabled');
  });
});
