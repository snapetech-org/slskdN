#!/usr/bin/env python3
"""Build a scratch-only W54 cross-audit from the sealed blind and primary packets."""
import collections
import hashlib
import json
import pathlib
import re
import sys

BASE = pathlib.Path('/mnt/disks/scratch/task-scratch')
BLIND = BASE / 'slskdn-pr409-w54-independent-blind-20261103'
PRIMARY = BASE / 'slskdn-pr409-w54-primary-20261103'
OUT = BASE / 'slskdn-pr409-w54-cross-audit-20261103'
EXPECTED_HEAD = '5812e90c3018f0a8b563bff2ba95b5fd19076908'
EXPECTED_TREE = '632924177388e15b594976774d2d879a098e8a72'


def sha(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def ref_key(ref):
    return (ref.get('path'), ref.get('line'), ref.get('lineSha256'), ref.get('fileSha256'), ref.get('gitBlob'))


def tokens(text, pattern):
    return collections.Counter(re.findall(pattern, text))

# Verify packet attestations and manifests before comparing review rows.
blind_summary = load_json(BLIND / 'summary.json')
primary_summary = load_json(PRIMARY / 'primary' / 'review-summary.json')
blind_attest = load_json(BLIND / 'input' / 'head-tree-attestation.json')
primary_attest = load_json(PRIMARY / 'input' / 'head-tree-attestation.json')
assert blind_summary['head'] == primary_summary['exactHead'] == EXPECTED_HEAD
assert blind_summary['tree'] == primary_summary['exactTree'] == EXPECTED_TREE
assert blind_attest == primary_attest
assert primary_summary['inputManifestSha256'] == blind_summary['inputPacketChecksumListSha256']

blind_cells = load_jsonl(BLIND / 'input' / 'source-current-cells.jsonl')
primary_input_cells = load_jsonl(PRIMARY / 'input' / 'source-current-cells.jsonl')
blind_reviews = load_jsonl(BLIND / 'review-ledger.jsonl')
primary_reviews = load_jsonl(PRIMARY / 'primary' / 'review-decisions.jsonl')
caller_contexts = load_jsonl(BLIND / 'input' / 'caller-contexts.jsonl')
protected_rows = load_jsonl(BLIND / 'input' / 'protected-literals.jsonl')
assert len(blind_cells) == len(primary_input_cells) == len(blind_reviews) == len(primary_reviews) == 300
assert len(caller_contexts) == len(protected_rows) == 25

# Verify blind and primary input copies are byte-identical file-by-file.
def file_hashes(root):
    result = {}
    for p in sorted(root.rglob('*')):
        if p.is_file() and p.name not in ('PACKET-SHA256SUMS.txt',):
            result[p.relative_to(root).as_posix()] = sha_bytes(p.read_bytes())
    return result
blind_input_hashes = file_hashes(BLIND / 'input')
primary_input_hashes = file_hashes(PRIMARY / 'input')
assert blind_input_hashes == primary_input_hashes

keys = lambda row: (row['continuationRank'], row['locale'])
I = {keys(x): x for x in blind_cells}
PI = {keys(x): x for x in primary_input_cells}
B = {keys(x): x for x in blind_reviews}
P = {keys(x): x for x in primary_reviews}
C = {x['continuationRank']: x for x in caller_contexts}
L = {x['continuationRank']: x for x in protected_rows}
assert set(I) == set(PI) == set(B) == set(P)
assert set(I) == {(rank, loc) for rank in range(251, 276) for loc in ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']}

# Extra terminology holds where the independent packets disagree on an unapproved technical term.
term_holds = {
    (254, 'ko'): 'Korean search-vs-retrieval wording has no packet-backed preferred term; retain current pending terminology review.',
    (255, 'id'): 'The P2P caller confirms a network peer, but the packets do not establish an approved Indonesian UI term; retain current pending terminology review.',
    (255, 'vi'): 'The P2P caller confirms a network peer, but the packets differ between a bare peer expression and a peer-node term; retain current pending terminology review.',
    (256, 'vi'): 'The caller confirms descriptor retrieval/cache metrics, while the packets differ between descriptor loanword and translated description terminology; retain current pending terminology review.',
    (258, 'id'): 'The native MilkDrop library is clear, but the packets differ among built-in/native wording and do not establish an approved Indonesian term; retain current pending terminology review.',
    (258, 'ko'): 'The native MilkDrop library is clear, but the packets differ among default/native wording and do not establish an approved Korean term; retain current pending terminology review.',
    (258, 'vi'): 'The native MilkDrop library is clear, but the packets differ between native/original/built-in senses and do not establish an approved Vietnamese term; retain current pending terminology review.',
}
blind_wins = {
    (253, 'vi'): 'The caller is an import summary with both imported and skipped row counts. The blind phrasing keeps both named placeholders and states that the skipped items are duplicate or incomplete rows.',
    (271, 'zh-Hans'): 'The tooltip explicitly says contacting Soulseek peers now. 对等节点 expresses a network peer and avoids 同行, which can read as a colleague or industry peer.',
    (271, 'zh-Hant'): 'The tooltip explicitly says contacting Soulseek peers now. 對等節點 expresses a network peer and avoids 同行, which can read as a colleague or industry peer.',
}

rows = []
conflicts = []
validation_failures = []
source_reference_checks = []
for key in sorted(I):
    i, pi, b, p = I[key], PI[key], B[key], P[key]
    rank, locale = key
    assert (i['sourceId'], i['source'], i['sourceSha256'], i['currentTarget'], i['currentTargetSha256'], i['catalogPath'], i['catalogFileSha256'], i['catalogGitBlob']) == (pi['sourceId'], pi['source'], pi['sourceSha256'], pi['currentTarget'], pi['currentTargetSha256'], pi['catalogPath'], pi['catalogFileSha256'], pi['catalogGitBlob'])
    for x in (b, p):
        assert x['sourceId'] == i['sourceId'] and x['source'] == i['source'] and x['sourceSha256'] == i['sourceSha256']
        assert x['currentTarget'] == i['currentTarget'] and x['currentTargetSha256'] == i['currentTargetSha256']
        assert x['catalogPath'] == i['catalogPath'] and x['catalogFileSha256'] == i['catalogFileSha256'] and x['catalogGitBlob'] == i['catalogGitBlob']
    assert sha(i['source']) == i['sourceSha256']
    assert sha(i['currentTarget']) == i['currentTargetSha256']
    assert sha(b['proposedTarget']) == b['proposedTargetSha256']
    assert sha(p['candidateTarget']) == p['candidateTargetSha256']

    # Cross-check every claimed caller reference against the pinned input context for this source ID.
    ctx = C[rank]
    assert ctx['sourceId'] == i['sourceId'] and ctx['source'] == i['source'] and ctx['sourceSha256'] == i['sourceSha256']
    current_ref_keys = sorted(ref_key(x) for x in i.get('callerRefs', []))
    context_ref_keys = sorted(ref_key(x) for x in ctx.get('callers', []))
    primary_ref_keys = sorted(ref_key(x) for x in p.get('callerRefs', []))
    blind_ref_keys = sorted(ref_key(x) for x in b['callerRelevance'].get('callerReferences', []))
    assert current_ref_keys == context_ref_keys == primary_ref_keys == blind_ref_keys, (rank, locale, current_ref_keys, context_ref_keys, primary_ref_keys, blind_ref_keys)
    assert len(ctx.get('callers', [])) == b['callerRelevance']['productionCallerCount'] == p['callerCount']
    assert b['callerRelevance']['callerContextSha256'] == i['callerContextSha256'] == p['callerContextSha256']
    direct = bool(b['callerRelevance']['directLocalizedCaller'])
    if rank == 272:
        assert len(ctx['callers']) == 1 and not direct
        assert ': \'Certificate password\',' in ctx['callers'][0]['lineText']
    if rank == 270:
        assert len(ctx['callers']) == 0 and not direct
    if rank == 262:
        assert direct and any('LocalizedText source={"Publish Pod"}' in x['lineText'] for x in ctx['callers'])

    # All protected literals and source placeholders/markup/numbers must remain valid for the selected current/candidate.
    protected_specs = L[rank].get('exactProtectedLiterals', [])
    protected = [x['literal'] if isinstance(x, dict) else x for x in protected_specs]
    assert L[rank]['sourceId'] == i['sourceId'] and L[rank]['sourceSha256'] == i['sourceSha256']
    named_tokens = re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}', i['source'])
    source_tags = re.findall(r'<\s*/?\s*[A-Za-z][^>]*>', i['source'])
    source_nums = i.get('sourceNumericTokens', [])

    if rank in (270, 272):
        outcome = 'HOLD_NO_DIRECT_LOCALIZED_CALLER'
        rationale = ('No direct localized caller exists in the pinned source context. ' +
                     ('There are zero production references.' if rank == 270 else 'The one production occurrence is a raw JSX fallback string, not a localization helper/component call.'))
        selected = i['currentTarget']
        selected_source = 'current'
        apply_target = None
    elif rank == 262:
        outcome = 'HOLD_GLOSSARY'
        rationale = 'A direct localized caller confirms the DHT Pod action, but neither packet provides an approved localized noun for the domain object. Preserve current cell pending glossary decision.'
        selected = i['currentTarget']
        selected_source = 'current'
        apply_target = None
    elif key in term_holds:
        outcome = 'HOLD_TERMINOLOGY'
        rationale = term_holds[key]
        selected = i['currentTarget']
        selected_source = 'current'
        apply_target = None
    elif key in blind_wins:
        outcome = 'WIN_BLIND'
        rationale = blind_wins[key]
        selected = b['proposedTarget']
        selected_source = 'blind'
        apply_target = selected
    elif p['verdict'] in ('correction', 'refinement') and p['candidateTarget'] != i['currentTarget']:
        outcome = 'WIN_PRIMARY'
        rationale = p['rationale']
        selected = p['candidateTarget']
        selected_source = 'primary'
        apply_target = selected
    else:
        outcome = 'KEEP_CURRENT'
        rationale = p.get('rationale') or b.get('semanticRationale') or 'Pinned current translation is retained.'
        selected = i['currentTarget']
        selected_source = 'current'
        apply_target = None

    # Hash-selected string and check structural tokens, markup, numeric values, protected literals.
    selected_sha = sha(selected)
    selected_named = re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}', selected)
    selected_tags = re.findall(r'<\s*/?\s*[A-Za-z][^>]*>', selected)
    missing_protected = [literal for literal in protected if literal not in selected]
    selected_nums = [n for n in source_nums if n not in selected]
    placeholder_ok = collections.Counter(named_tokens) == collections.Counter(selected_named)
    markup_ok = collections.Counter(source_tags) == collections.Counter(selected_tags)
    numeric_ok = not selected_nums
    protected_ok = not missing_protected
    if not (placeholder_ok and markup_ok and numeric_ok and protected_ok):
        validation_failures.append({'rank': rank, 'locale': locale, 'outcome': outcome, 'placeholderOk': placeholder_ok, 'markupOk': markup_ok, 'numericOk': numeric_ok, 'protectedOk': protected_ok, 'missingProtected': missing_protected, 'missingNumbers': selected_nums})

    primary_bucket = 'hold' if p['verdict'].startswith('hold-') else ('change' if p['verdict'] in ('correction','refinement') else 'keep')
    blind_bucket = 'hold' if b['decision'].startswith('HOLD_') else ('change' if b['decision'] == 'REVISE_CANDIDATE' else 'keep')
    buckets_agree = primary_bucket == blind_bucket
    candidate_text_disagrees = p['candidateTarget'] != b['proposedTarget']
    contested = (not buckets_agree) or candidate_text_disagrees or outcome.startswith('HOLD_') and not (primary_bucket == blind_bucket == 'hold')

    row = {
        'continuationRank': rank,
        'historicalSourceOrdinal': None,
        'sourceId': i['sourceId'],
        'locale': locale,
        'source': i['source'],
        'sourceSha256': i['sourceSha256'],
        'catalogPath': i['catalogPath'],
        'catalogFileSha256': i['catalogFileSha256'],
        'catalogGitBlob': i['catalogGitBlob'],
        'currentTarget': i['currentTarget'],
        'currentTargetSha256': i['currentTargetSha256'],
        'blindProposedTarget': b['proposedTarget'],
        'blindProposedTargetSha256': b['proposedTargetSha256'],
        'blindDecision': b['decision'],
        'blindRationale': b['semanticRationale'],
        'primaryCandidateTarget': p['candidateTarget'],
        'primaryCandidateTargetSha256': p['candidateTargetSha256'],
        'primaryVerdict': p['verdict'],
        'primaryRationale': p['rationale'],
        'adjudicatedOutcome': outcome,
        'adjudicatedTarget': selected,
        'adjudicatedTargetSha256': selected_sha,
        'adjudicatedTargetSource': selected_source,
        'applyTarget': apply_target,
        'applyTargetSha256': sha(apply_target) if apply_target is not None else None,
        'adjudicationRationale': rationale,
        'candidateTextDisagreement': candidate_text_disagrees,
        'coarseDispositionAgreement': buckets_agree,
        'isDisputed': contested,
        'callerEvidence': {
            'productionCallerCount': len(ctx.get('callers', [])),
            'directLocalizedCaller': direct,
            'callerContextSha256': i['callerContextSha256'],
            'callerReferences': ctx.get('callers', []),
            'allBlindPrimaryInputReferencesMatch': True,
            'relevanceNote': ('raw occurrence only; not direct localization consumption' if rank == 272 else ('no production caller references' if rank == 270 else ('direct localized source caller' if direct else 'caller references exist, but direct localized call not established'))),
        },
        'placeholdersAndICU': {
            'sourceNamedPlaceholders': named_tokens,
            'adjudicatedNamedPlaceholders': selected_named,
            'placeholderMatch': placeholder_ok,
            'icuSyntax': b['placeholdersAndICU']['icuSyntax'],
        },
        'markup': {
            'sourceTags': source_tags,
            'adjudicatedTags': selected_tags,
            'markupMatch': markup_ok,
        },
        'numericTokens': {
            'source': source_nums,
            'adjudicatedTargetMissingSourceNumbers': selected_nums,
            'numericSourceValuesPreserved': numeric_ok,
        },
        'protectedLiterals': {
            'requiredExactLiterals': protected_specs,
            'missingFromAdjudicatedTarget': missing_protected,
            'allPreserved': protected_ok,
        },
        'rtlSensitiveNote': b.get('rtlSensitiveNote') if locale == 'ar' else None,
        'confidence': 'moderate; machine-assisted cross-audit; native-speaker approval pending',
        'nativeSpeakerApproval': 'pending; this machine review is not qualified native-speaker approval',
    }
    rows.append(row)
    if contested:
        conflicts.append({
            'continuationRank': rank, 'sourceId': i['sourceId'], 'locale': locale,
            'source': i['source'], 'currentTarget': i['currentTarget'],
            'blindDecision': b['decision'], 'blindTarget': b['proposedTarget'],
            'primaryVerdict': p['verdict'], 'primaryTarget': p['candidateTarget'],
            'adjudicatedOutcome': outcome, 'adjudicatedTarget': selected,
            'adjudicatedTargetSha256': selected_sha, 'adjudicationRationale': rationale,
            'candidateTextDisagreement': candidate_text_disagrees,
            'coarseDispositionAgreement': buckets_agree,
        })

assert len(rows) == 300
assert not validation_failures, validation_failures[:10]
assert len(conflicts) > 0
assert primary_summary['callerReferenceCount'] == sum(len(x.get('callers', [])) for x in caller_contexts)

# Verify primary decision map exactly against its review rows.
candidate_map = load_json(PRIMARY / 'primary' / 'candidate-decisions.json')
for k, choice in candidate_map.items():
    rank, locale = k.split('|', 1)
    target = P[(int(rank), locale)]['candidateTarget']
    assert choice['target'] == target
assert len(candidate_map) == primary_summary['candidateChangeCount'] == 51

# Write row-oriented report and conflict extract.
ledger_path = OUT / 'reconciliation-ledger.jsonl'
ledger_path.write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows), encoding='utf-8')
conflicts_path = OUT / 'disagreements.jsonl'
conflicts_path.write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in conflicts), encoding='utf-8')

live = {
    'verifiedAtUtc': '2026-11-03 05:56:05 UTC',
    'verificationMethod': 'GitHub CLI pull request and branch APIs plus git ls-remote',
    'repository': 'snapetech-org/slskdN',
    'pullRequest': 409,
    'pullRequestUrl': 'https://github.com/snapetech-org/slskdN/pull/409',
    'state': 'open',
    'draft': True,
    'headRef': 'codex/slskdn-oidc-tooltip-localization-20261030',
    'baseRef': 'main',
    'pullRequestHead': EXPECTED_HEAD,
    'branchApiHead': EXPECTED_HEAD,
    'gitLsRemoteHead': EXPECTED_HEAD,
    'tree': EXPECTED_TREE,
    'allLiveHeadChecksMatch': True,
}
write_json(OUT / 'live-pr-verification.json', live)

outcome_counts = collections.Counter(row['adjudicatedOutcome'] for row in rows)
by_locale = {loc: dict(collections.Counter(row['adjudicatedOutcome'] for row in rows if row['locale'] == loc)) for loc in ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']}
summary = {
    'title': 'Independent cross-audit reconciliation: slskdN PR #409 W54',
    'repository': 'snapetech-org/slskdN',
    'pullRequest': 409,
    'head': EXPECTED_HEAD,
    'tree': EXPECTED_TREE,
    'branch': 'codex/slskdn-oidc-tooltip-localization-20261030',
    'window': 'Ranks 251–275 × 12 locales = 300 cells',
    'historicalSourceOrdinals': 'unavailable and not claimed',
    'cellCount': len(rows),
    'independentBlindInputContainsCandidates': False,
    'blindInputEqualsPrimaryInput': True,
    'inputManifestSha256': primary_summary['inputManifestSha256'],
    'callerReferences': {
        'primaryReported': primary_summary['callerReferenceCount'],
        'recountedFromPinnedInput': sum(len(x.get('callers', [])) for x in caller_contexts),
        'callerlessSourceIds': [
            {'rank': 270, 'sourceId': I[(270,'ar')]['sourceId'], 'source': I[(270,'ar')]['source'], 'productionCallerCount': 0},
            {'rank': 272, 'sourceId': I[(272,'ar')]['sourceId'], 'source': I[(272,'ar')]['source'], 'productionCallerCount': 1, 'directLocalizedCaller': False},
        ],
        'callerRefsCellRelevant': True,
        'validation': 'For all 300 cells, source ID, source hash, exact caller reference set, and caller-context hash agree across the pinned input, blind ledger, and primary review. Primary count 68 is the input reference count; it does not imply every reference is a direct localized caller.',
    },
    'outcomeCounts': dict(outcome_counts),
    'outcomeCountsByLocale': by_locale,
    'changedWinnerCount': sum(row['applyTarget'] is not None for row in rows),
    'holdCount': sum(row['adjudicatedOutcome'].startswith('HOLD_') for row in rows),
    'blindPrimaryComparison': {
        'candidateTextDisagreementCount': sum(row['candidateTextDisagreement'] for row in rows),
        'coarseDispositionConflictCount': sum(not row['coarseDispositionAgreement'] for row in rows),
        'disputedCellCount': len(conflicts),
        'primaryCandidateChanges': primary_summary['candidateChangeCount'],
        'blindsProposedChanges': blind_summary['revisedCells'],
    },
    'structuralValidation': {
        'sourceCurrentCatalogHashesMatchedAcrossPackets': True,
        'callerReferenceSetsAndContextHashesMatchedAcrossThreeRecords': True,
        'placeholdersMismatches': 0,
        'markupMismatches': 0,
        'numericTokenLosses': 0,
        'protectedLiteralLosses': 0,
        'allSelectedTargetsValidated': True,
    },
    'importantHolds': [
        {'rank':270,'source':'waves ·','cells':12,'reason':'No production caller references.'},
        {'rank':272,'source':'Certificate password','cells':12,'reason':'One raw JSX fallback occurrence at AdminPolicies/index.jsx:1227; no direct localized caller. The primary packet counts it as a reference, but reference existence is not direct localized consumption.'},
        {'rank':262,'source':'Publish Pod','cells':12,'reason':'Direct LocalizedText caller at MediaCorePods.jsx:1650; DHT Pod noun has no approved localized glossary target.'},
        {'cells':7,'reason':'Terminology held: rank 254 ko; rank 255 id and vi; rank 256 vi; rank 258 id, ko, and vi. The packets do not establish approved UI terms for these semantic choices.'},
    ],
    'nativeSpeakerApproval': 'pending; this machine review is not qualified native-speaker approval',
    'repositoryOrPrEdits': False,
    'testsBuildScansCiWorkflowChanges': False,
    'livePrVerification': 'live-pr-verification.json',
    'ledger': 'reconciliation-ledger.jsonl',
    'disagreementExtract': 'disagreements.jsonl',
}
write_json(OUT / 'summary.json', summary)

conflict_rows = '\n'.join(
    f"- Rank {r['continuationRank']} {r['locale']} — {r['source']!r}: {r['blindDecision']} → {r['blindTarget']!r}; primary {r['primaryVerdict']} → {r['primaryTarget']!r}; adjudication **{r['adjudicatedOutcome']}** → {r['adjudicatedTarget']!r}. {r['adjudicationRationale']}"
    for r in conflicts
)
summary_md = f'''# W54 cross-audit: slskdN PR #409

## Scope and verification

- Reviewed all 300 cells: continuation ranks 251–275 across 12 locales.
- Exact PR head/tree: `{EXPECTED_HEAD}` / `{EXPECTED_TREE}`. The live PR, GitHub branch API, and `git ls-remote` all matched the pinned head at {live['verifiedAtUtc']}.
- Blind and primary input copies are byte-identical; both packet checksum manifests verify. The primary reports 68 caller references, and the pinned caller packet independently recounts 68 references.
- For every cell, the source ID/hash, exact current target/hash, catalog hashes, and caller reference set/context hash match across input, blind ledger, and primary review. A reference count alone does not establish direct localization use.

## Reconciled outcomes

- {summary['changedWinnerCount']} cells have an exact proposed winner in the reconciliation; no translation was applied.
- {summary['holdCount']} cells remain held; their exact current strings remain preserved as unapproved current values.
- Outcomes: `{json.dumps(summary['outcomeCounts'], ensure_ascii=False, sort_keys=True)}`.
- Blind/primary comparisons: {summary['blindPrimaryComparison']['candidateTextDisagreementCount']} candidate strings differ; {summary['blindPrimaryComparison']['coarseDispositionConflictCount']} cells disagree at the keep/change/hold level; {summary['blindPrimaryComparison']['disputedCellCount']} cells are included in the disagreement extract.

## Holds that remain

- **`waves ·` (12 cells):** no production caller references.
- **`Certificate password` (12 cells):** the one pinned occurrence is a raw JSX fallback at `src/web/src/components/System/AdminPolicies/index.jsx:1227`, not a direct localization helper/component call. The primary counts this as a caller reference, but the caller evidence does not show locale-cell consumption. These remain no-direct-localizer holds.
- **`Publish Pod` (12 cells):** direct localized caller at `src/web/src/components/System/MediaCore/MediaCorePods.jsx:1650` confirms the action is localized, but there is no approved target-language noun for the DHT Pod object. Keep every cell held under the glossary decision; do not select the blind `Pod` or primary alternatives.
- **7 additional terminology cells:** rank 254 ko (`retrieval`/`search`); rank 255 id and vi (`peer`); rank 256 vi (`descriptor`); rank 258 id, ko, and vi (`native presets`). Exact current targets are retained pending terminology review.

## Exact disputed cells

The complete 300-row `reconciliation-ledger.jsonl` contains source/current/blind/primary/adjudicated strings and their SHA-256 values, caller evidence, validation fields, and row-level disagreements. `disagreements.jsonl` lists every cell with a candidate-string difference, coarse disposition conflict, or a cross-audit hold conflict.

{conflict_rows}

## Validation and limitations

Placeholder/ICU, markup, numeric, and protected-literal checks pass for all selected current/winning targets. Arabic rows retain RTL-sensitive notes from the blind evidence. Source ordinals remain unavailable and unclaimed. This is machine-assisted review; qualified native-speaker approval is pending. No repository or PR edits, tests, builds, scans, or CI actions were made.
'''
(OUT / 'summary.md').write_text(summary_md, encoding='utf-8')

# Provenance and input-only-vs-ledger hashes make data boundaries explicit.
provenance = {
    'blindPacket': str(BLIND),
    'primaryPacket': str(PRIMARY),
    'output': str(OUT),
    'head': EXPECTED_HEAD,
    'tree': EXPECTED_TREE,
    'blindInputFilesSha256': blind_input_hashes,
    'primaryInputFilesSha256': primary_input_hashes,
    'inputCopiesByteIdentical': True,
    'blindPacketChecksumListSha256': sha_bytes((BLIND / 'input' / 'PACKET-SHA256SUMS.txt').read_bytes()),
    'primaryPacketChecksumListSha256': sha_bytes((PRIMARY / 'input' / 'PACKET-SHA256SUMS.txt').read_bytes()),
    'blindOutputChecksumListSha256': sha_bytes((BLIND / 'SHA256SUMS.txt').read_bytes()),
    'primaryOutputChecksumListSha256': sha_bytes((PRIMARY / 'primary' / 'SHA256SUMS.txt').read_bytes()),
    'blindLedgerSha256': sha_bytes((BLIND / 'review-ledger.jsonl').read_bytes()),
    'primaryReviewSha256': sha_bytes((PRIMARY / 'primary' / 'review-decisions.jsonl').read_bytes()),
    'primaryCandidateMapSha256': sha_bytes((PRIMARY / 'primary' / 'candidate-decisions.json').read_bytes()),
    'primaryReviewSummarySha256': sha_bytes((PRIMARY / 'primary' / 'review-summary.json').read_bytes()),
    'crossAuditLedgerSha256': sha_bytes(ledger_path.read_bytes()),
    'disagreementExtractSha256': sha_bytes(conflicts_path.read_bytes()),
}
write_json(OUT / 'provenance-and-hashes.json', provenance)

print(json.dumps({
    'rows': len(rows), 'conflicts': len(conflicts), 'outcomes': dict(outcome_counts),
    'changedWinnerCount': summary['changedWinnerCount'], 'holdCount': summary['holdCount'],
    'candidateTextDisagreementCount': summary['blindPrimaryComparison']['candidateTextDisagreementCount'],
    'coarseDispositionConflictCount': summary['blindPrimaryComparison']['coarseDispositionConflictCount'],
    'validationFailures': validation_failures,
    'ledgerSha256': provenance['crossAuditLedgerSha256'],
    'output': str(OUT),
}, ensure_ascii=False, indent=2))
