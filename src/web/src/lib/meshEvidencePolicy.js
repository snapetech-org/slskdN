import { formatRegionalNumber } from './regionalFormat';
import { interfaceText } from './interfaceLocale';
import meshEvidenceReasonSources from './meshEvidenceReasonSources.json';

export const getMeshEvidenceReasonSource = (reason) => reason &&
  typeof reason === 'object' && Object.hasOwn(meshEvidenceReasonSources, reason.id)
  ? meshEvidenceReasonSources[reason.id]
  : undefined;

export const getMeshEvidenceReasonValues = (reason, locale) => {
  const parameters = reason?.parameters || {};
  return ['low-confidence', 'few-witnesses'].includes(reason?.id)
    ? { ...parameters, minimum: formatRegionalNumber(parameters.minimum, undefined, locale) }
    : parameters;
};

export const formatMeshEvidenceReason = (reason) => {
  const source = getMeshEvidenceReasonSource(reason);
  // This formatter is also used in copied review reports. Keep those values
  // plain; the React presentation path uses LocalizedText and <bdi> instead.
  if (source) return interfaceText(source, getMeshEvidenceReasonValues(reason));
  return typeof reason === 'string' ? reason : JSON.stringify(reason);
};
import {
  getLocalStorageItem,
  removeLocalStorageItem,
  setLocalStorageItem,
} from './storage';

export const meshEvidencePolicyStorageKey = 'slskdn.meshEvidencePolicy';

export const inboundTrustTiers = [
  {
    description: 'Ignore all inbound mesh evidence until explicitly enabled.',
    id: 'disabled',
    label: 'Disabled',
  },
  {
    description: 'Apply evidence only from directly trusted peers and contacts.',
    id: 'trusted',
    label: 'Trusted peers',
  },
  {
    description: 'Apply trusted peer and realm-curated evidence with provenance.',
    id: 'realm',
    label: 'Trusted realms',
  },
];

export const outboundEvidenceTypes = [
  {
    description: 'Signed statements that a known hash verified locally.',
    id: 'hashVerification',
    label: 'Hash verification',
  },
  {
    description: 'Signed release-completeness observations without file paths.',
    id: 'releaseCompleteness',
    label: 'Release completeness',
  },
  {
    description: 'Signed warnings for suspicious fake-lossless candidates.',
    id: 'fakeLosslessWarning',
    label: 'Fake-lossless warnings',
  },
  {
    description: 'Signed metadata corrections reviewed by this operator.',
    id: 'metadataCorrection',
    label: 'Metadata corrections',
  },
  {
    description: 'Realm-curated subject index entries, never raw library dumps.',
    id: 'realmSubjectIndex',
    label: 'Realm subject indexes',
  },
];

export const defaultMeshEvidencePolicy = {
  evidenceReview: {
    minimumConfidence: 0.7,
    minimumWitnesses: 2,
  },
  inboundTrustTier: 'disabled',
  outbound: outboundEvidenceTypes.reduce((state, evidenceType) => {
    state[evidenceType.id] = false;
    return state;
  }, {}),
  provenanceRequired: true,
  updatedAt: null,
};

const sanitizePolicy = (policy = {}) => {
  const inboundTrustTier = inboundTrustTiers.some(
    (tier) => tier.id === policy.inboundTrustTier,
  )
    ? policy.inboundTrustTier
    : defaultMeshEvidencePolicy.inboundTrustTier;

  const outbound = outboundEvidenceTypes.reduce((state, evidenceType) => {
    state[evidenceType.id] = policy.outbound?.[evidenceType.id] === true;
    return state;
  }, {});

  return {
    evidenceReview: {
      minimumConfidence: Number.isFinite(policy.evidenceReview?.minimumConfidence)
        ? Math.min(Math.max(policy.evidenceReview.minimumConfidence, 0), 1)
        : defaultMeshEvidencePolicy.evidenceReview.minimumConfidence,
      minimumWitnesses: Number.isFinite(policy.evidenceReview?.minimumWitnesses)
        ? Math.max(Math.round(policy.evidenceReview.minimumWitnesses), 1)
        : defaultMeshEvidencePolicy.evidenceReview.minimumWitnesses,
    },
    inboundTrustTier,
    outbound,
    provenanceRequired: true,
    updatedAt: policy.updatedAt || null,
  };
};

export const getMeshEvidencePolicy = () => {
  const stored = getLocalStorageItem(meshEvidencePolicyStorageKey);
  if (!stored) {
    return defaultMeshEvidencePolicy;
  }

  try {
    return sanitizePolicy(JSON.parse(stored));
  } catch (_error) {
    removeLocalStorageItem(meshEvidencePolicyStorageKey);
    return defaultMeshEvidencePolicy;
  }
};

export const saveMeshEvidencePolicy = (policy) => {
  const sanitized = sanitizePolicy({
    ...policy,
    updatedAt: new Date().toISOString(),
  });

  setLocalStorageItem(meshEvidencePolicyStorageKey, JSON.stringify(sanitized));
  return sanitized;
};

export const setMeshEvidenceInboundTrustTier = (inboundTrustTier) =>
  saveMeshEvidencePolicy({
    ...getMeshEvidencePolicy(),
    inboundTrustTier,
  });

export const setMeshEvidenceOutboundEnabled = (evidenceTypeId, enabled) => {
  const policy = getMeshEvidencePolicy();
  return saveMeshEvidencePolicy({
    ...policy,
    outbound: {
      ...policy.outbound,
      [evidenceTypeId]: enabled === true,
    },
  });
};

export const resetMeshEvidencePolicy = () => {
  removeLocalStorageItem(meshEvidencePolicyStorageKey);
  return defaultMeshEvidencePolicy;
};

export const getMeshEvidencePolicySummary = (policy = getMeshEvidencePolicy()) => {
  const enabledOutbound = outboundEvidenceTypes.filter(
    (evidenceType) => policy.outbound[evidenceType.id],
  );
  const inboundTier = inboundTrustTiers.find(
    (tier) => tier.id === policy.inboundTrustTier,
  );

  return {
    enabledOutbound,
    inboundEnabled: policy.inboundTrustTier !== 'disabled',
    inboundTier,
    outboundEnabled: enabledOutbound.length > 0,
    privateByDefault:
      policy.inboundTrustTier === 'disabled' && enabledOutbound.length === 0,
  };
};

const trustedInboundTiers = {
  disabled: new Set(),
  realm: new Set(['trusted', 'realm']),
  trusted: new Set(['trusted']),
};

const normalizeEvidenceEntries = (entries) => {
  if (Array.isArray(entries)) return entries;
  if (Array.isArray(entries?.evidence)) return entries.evidence;
  if (Array.isArray(entries?.items)) return entries.items;
  return [];
};

const normalizeEvidenceEntry = (entry = {}) => ({
  confidence: Number.isFinite(entry.confidence) ? entry.confidence : 0,
  containsExactHoldings: entry.containsExactHoldings === true,
  containsPath: entry.containsPath === true,
  containsRawListeningHistory: entry.containsRawListeningHistory === true,
  id: entry.id || `${entry.type || 'evidence'}:${entry.subject || 'unknown'}`,
  provenance: {
    peerId: entry.provenance?.peerId || entry.peerId || '',
    realmId: entry.provenance?.realmId || entry.realmId || '',
    signature: entry.provenance?.signature || entry.signature || '',
    trustTier: entry.provenance?.trustTier || entry.trustTier || 'untrusted',
  },
  subject: entry.subject || 'unknown',
  type: entry.type || 'unknown',
  witnessCount: Number.isFinite(entry.witnessCount) ? entry.witnessCount : 0,
});

export const evaluateMeshEvidenceEntries = (
  entries,
  policy = getMeshEvidencePolicy(),
) => {
  const sanitizedPolicy = sanitizePolicy(policy);
  const trustedTiers = trustedInboundTiers[sanitizedPolicy.inboundTrustTier];
  const normalized = normalizeEvidenceEntries(entries).map(normalizeEvidenceEntry);

  const results = normalized.map((entry) => {
    const reasons = [];

    if (sanitizedPolicy.inboundTrustTier === 'disabled') {
      reasons.push({ id: 'inbound-disabled', parameters: {} });
    }

    if (!entry.provenance.signature || !entry.provenance.peerId) {
      reasons.push({ id: 'missing-provenance', parameters: {} });
    }

    if (!trustedTiers.has(entry.provenance.trustTier)) {
      reasons.push({ id: 'untrusted-tier', parameters: { tier: entry.provenance.trustTier } });
    }

    if (entry.confidence < sanitizedPolicy.evidenceReview.minimumConfidence) {
      reasons.push({ id: 'low-confidence', parameters: { minimum: sanitizedPolicy.evidenceReview.minimumConfidence } });
    }

    if (entry.witnessCount < sanitizedPolicy.evidenceReview.minimumWitnesses) {
      reasons.push({ id: 'few-witnesses', parameters: { minimum: sanitizedPolicy.evidenceReview.minimumWitnesses } });
    }

    if (entry.containsPath) {
      reasons.push({ id: 'contains-path', parameters: {} });
    }

    if (entry.containsExactHoldings) {
      reasons.push({ id: 'exact-holdings', parameters: {} });
    }

    if (entry.containsRawListeningHistory) {
      reasons.push({ id: 'raw-history', parameters: {} });
    }

    return {
      ...entry,
      accepted: reasons.length === 0,
      reasons,
    };
  });

  const accepted = results.filter((entry) => entry.accepted);

  return {
    accepted,
    rejected: results.filter((entry) => !entry.accepted),
    results,
    summary: {
      accepted: accepted.length,
      rejected: results.length - accepted.length,
      total: results.length,
    },
  };
};

export const parseMeshEvidenceReviewInput = (value) => {
  if (!value?.trim()) return [];

  const parsed = JSON.parse(value);
  return normalizeEvidenceEntries(parsed);
};

export const formatMeshEvidenceReviewReport = (review) => {
  const lines = [
    interfaceText("slskdN mesh evidence review"),
    `Total: ${review.summary.total}`,
    `Accepted: ${review.summary.accepted}`,
    `Rejected: ${review.summary.rejected}`,
    '',
  ];

  review.results.forEach((entry) => {
    lines.push(
      `[${entry.accepted ? 'ACCEPT' : 'REJECT'}] ${entry.type} ${entry.subject}`,
    );
    lines.push(`Confidence: ${entry.confidence}`);
    lines.push(`Witnesses: ${entry.witnessCount}`);
    lines.push(`Provenance: ${entry.provenance.trustTier} ${entry.provenance.peerId}`);
    if (entry.reasons.length > 0) {
      lines.push(`Reasons: ${entry.reasons.map(formatMeshEvidenceReason).join('; ')}`);
    }
    lines.push('');
  });

  return lines.join('\n').trim();
};
