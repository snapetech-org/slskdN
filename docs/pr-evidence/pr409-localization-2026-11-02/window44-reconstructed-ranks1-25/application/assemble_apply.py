import collections
import hashlib
import json
import re
import shutil
from pathlib import Path

REPO = Path('/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn')
SCRATCH = Path('/mnt/disks/scratch/task-scratch')
PRIMARY = SCRATCH / 'slskdn-pr409-window44-primary-reconstructed-20261102'
CROSS = SCRATCH / 'slskdn-pr409-window44-crossreview-20261102'
ADJ = SCRATCH / 'slskdn-pr409-window44-additional-adjudication-20261102'
EVIDENCE = REPO / 'docs/pr-evidence/pr409-localization-2026-11-02/window44-reconstructed-ranks1-25'
EXPECTED_HEAD = 'f3fbd3f8db10f78768b9951a67b4b9de8581a408'
EXPECTED_TREE = '9495c35a540ef2d2e845c833acb709365e0e26ac'

sha_bytes = lambda value: hashlib.sha256(value).hexdigest()
sha_text = lambda value: hashlib.sha256(value.encode('utf-8')).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def render_catalog(value, original=None):
    result = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if original is not None and original.endswith(b'\n'):
        result += b'\n'
    return result


def ordered_key_hash(keys):
    return sha_text('\n'.join(keys))


def verify_manifest(directory, manifest_name):
    manifest = directory / manifest_name
    rows = []
    for line in manifest.read_text(encoding='utf-8').splitlines():
        digest, relative = line.split('  ', 1)
        path = directory / relative
        assert path.is_file(), path
        assert sha_bytes(path.read_bytes()) == digest, relative
        rows.append(relative)
    assert rows
    return sha_bytes(manifest.read_bytes()), len(rows)


assert not EVIDENCE.exists(), EVIDENCE
assert REPO.joinpath('.git').exists()

primary_manifest_sha, primary_manifest_rows = verify_manifest(PRIMARY, 'SHA256SUMS.txt')
cross_manifest_sha, cross_manifest_rows = verify_manifest(CROSS, 'SHA256SUMS.txt')
adj_manifest_sha, adj_manifest_rows = verify_manifest(ADJ, 'SHA256SUMS.txt')

primary_summary = read_json(PRIMARY / 'summary.json')
cross_summary = read_json(CROSS / 'cross-review-summary.json')
adj_summary = read_json(ADJ / 'summary.json')
assert primary_summary['head'] == EXPECTED_HEAD and primary_summary['tree'] == EXPECTED_TREE
assert cross_summary['exactHead'] == EXPECTED_HEAD and cross_summary['exactTree'] == EXPECTED_TREE
assert adj_summary['exactHead'] == EXPECTED_HEAD and adj_summary['exactTree'] == EXPECTED_TREE
assert cross_summary['scope']['cells'] == 300 and cross_summary['scope']['sourceIds'] == 25
assert cross_summary['scope']['historicalSourceOrdinalRange'] is None
assert cross_summary['scope']['selectionRanks'] == [1, 25]
assert cross_summary['sourceCallerGapsHeld'] == 24
assert adj_summary['verdictCounts'] == {
    'accept-additional-correction': 2,
    'accept-additional-refinement': 2,
}
assert adj_summary['allFinalTargetsMatchCandidates'] is True
assert adj_summary['callerGapHoldsRevisited'] is False
assert adj_summary['structuralChecksPassed'] is True

cross_rows = read_jsonl(CROSS / 'cross-review-ledger.jsonl')
adj_rows = read_jsonl(ADJ / 'adjudication.jsonl')
assert len(cross_rows) == 300 and len(adj_rows) == 4
cmap = {(row['selectionRank'], row['locale']): row for row in cross_rows}
amap = {(row['selectionRank'], row['locale']): row for row in adj_rows}
assert len(cmap) == 300 and len(amap) == 4
counts = collections.Counter(row['crossReviewDisposition'] for row in cross_rows)
assert counts == collections.Counter(cross_summary['crossReviewDispositionCounts'])

plan = []
for cell, row in sorted(cmap.items()):
    rank, locale = cell
    assert row['exactHead'] == EXPECTED_HEAD and row['exactTree'] == EXPECTED_TREE
    assert row['sourceOrdinal'] is None
    assert sha_text(row['source']) == row['sourceSha256']
    assert sha_text(row['currentTarget']) == row['currentTargetSha256']
    assert row['protectedLiteralsPreserved'] is True
    disposition = row['crossReviewDisposition']
    adjudication = None
    if disposition == 'accept-current':
        final_target = row['currentTarget']
    elif disposition in ('accept-primary-correction', 'accept-primary-refinement'):
        final_target = row['crossReviewFinalTarget']
        assert final_target is not None
        assert sha_text(final_target) == row['crossReviewFinalTargetSha256']
    elif disposition in ('propose-additional-correction', 'propose-additional-refinement'):
        adjudication = amap[cell]
        assert adjudication['sourceId'] == row['sourceId']
        assert adjudication['sourceSha256'] == row['sourceSha256']
        assert adjudication['currentTarget'] == row['currentTarget']
        assert adjudication['currentTargetSha256'] == row['currentTargetSha256']
        assert adjudication['verdict'] in ('accept-additional-correction', 'accept-additional-refinement')
        final_target = adjudication['finalTarget']
        assert sha_text(final_target) == adjudication['finalTargetSha256']
        assert adjudication['structureChecks']['placeholders']['parity'] is True
        assert adjudication['structureChecks']['markup']['parity'] is True
        assert adjudication['structureChecks']['protectedLiteralParity'] is True
    elif disposition == 'retain-hold':
        final_target = row['currentTarget']
    else:
        raise AssertionError((cell, disposition))
    source_tokens = sorted(row['sourcePlaceholders'])
    current_tokens = sorted(row['currentTargetPlaceholders'])
    final_tokens = sorted(re.findall(r'\{[^{}]+\}', final_target))
    if disposition == 'retain-hold':
        assert current_tokens == source_tokens
        assert row['currentProtectedLiteralsPreserved'] is True
    else:
        assert final_tokens == source_tokens
        assert sorted(row['finalPlaceholders']) == source_tokens
        assert row['finalMarkup'] == row['sourceMarkup']
    path = row['catalogPath']
    plan.append({
        'selectionRank': rank,
        'sourceId': row['sourceId'],
        'source': row['source'],
        'sourceSha256': row['sourceSha256'],
        'locale': locale,
        'catalogPath': path,
        'catalogBlobOidBefore': row['catalogBlobOid'],
        'catalogFileSha256Before': row['catalogFileSha256'],
        'currentTarget': row['currentTarget'],
        'currentTargetSha256': row['currentTargetSha256'],
        'primaryDisposition': row['primaryDisposition'],
        'primaryTarget': row['primaryTarget'],
        'crossReviewDisposition': disposition,
        'crossReviewTarget': row['crossReviewFinalTarget'],
        'adjudicationVerdict': adjudication['verdict'] if adjudication else None,
        'adjudicatedTarget': adjudication['finalTarget'] if adjudication else None,
        'finalTarget': final_target,
        'finalTargetSha256': sha_text(final_target),
        'heldForCallerGap': disposition == 'retain-hold',
        'changed': final_target != row['currentTarget'],
    })

assert len(plan) == 300
assert sum(row['changed'] for row in plan) == 35
assert sum(row['heldForCallerGap'] for row in plan) == 24
assert {row['source'] for row in plan if row['heldForCallerGap']} == {
    'pods', 'Private Message from {username}'
}
assert {row['selectionRank'] for row in plan} == set(range(1, 26))
assert {row['sourceId'] for row in plan if row['source'] == 'pods'}.__len__() == 1
assert {row['sourceId'] for row in plan if row['source'] == 'Private Message from {username}'}.__len__() == 1

catalogs = {}
preapply_pins = []
locale_paths = {}
for row in plan:
    locale_paths[row['locale']] = row['catalogPath']
assert len(locale_paths) == 12
for locale, relative in sorted(locale_paths.items()):
    path = REPO / relative
    raw = path.read_bytes()
    data = json.loads(raw)
    assert render_catalog(data, raw) == raw, relative
    catalogs[relative] = {'path': path, 'raw': raw, 'data': data}
    preapply_pins.append({
        'locale': locale,
        'catalogPath': relative,
        'sha256': sha_bytes(raw),
        'keyCount': len(data),
        'orderedKeySetSha256': ordered_key_hash(list(data)),
    })
key_sets = [set(entry['data']) for entry in catalogs.values()]
assert all(keys == key_sets[0] for keys in key_sets)

for row in plan:
    data = catalogs[row['catalogPath']]['data']
    assert data[row['source']] == row['currentTarget']
    assert sha_text(data[row['source']]) == row['currentTargetSha256']
    if row['changed']:
        data[row['source']] = row['finalTarget']

prepared = {}
for relative, entry in catalogs.items():
    content = render_catalog(entry['data'], entry['raw'])
    check = json.loads(content)
    assert set(check) == key_sets[0] and len(check) == len(entry['data'])
    prepared[relative] = content

EVIDENCE.mkdir(parents=True)
shutil.copytree(PRIMARY, EVIDENCE / 'primary')
shutil.copytree(CROSS, EVIDENCE / 'crossreview')
shutil.copytree(ADJ, EVIDENCE / 'additional-adjudication')
application = EVIDENCE / 'application'
application.mkdir()
shutil.copy2(Path(__file__), application / 'assemble_apply.py')
(application / 'catalog-preapply-pins.jsonl').write_text(
    ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in preapply_pins),
    encoding='utf-8',
)
(application / 'apply-plan.jsonl').write_text(
    ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in plan),
    encoding='utf-8',
)

for relative, content in prepared.items():
    (REPO / relative).write_bytes(content)

readback = []
for row in plan:
    data = read_json(REPO / row['catalogPath'])
    value = data[row['source']]
    assert value == row['finalTarget'] and sha_text(value) == row['finalTargetSha256']
    copy = dict(row)
    copy['readbackTargetSha256'] = sha_text(value)
    readback.append(copy)

post_catalogs = []
for locale, relative in sorted(locale_paths.items()):
    raw = (REPO / relative).read_bytes()
    data = json.loads(raw)
    assert render_catalog(data, raw) == raw
    assert set(data) == key_sets[0]
    post_catalogs.append({
        'locale': locale,
        'catalogPath': relative,
        'sha256': sha_bytes(raw),
        'keyCount': len(data),
        'orderedKeySetSha256': ordered_key_hash(list(data)),
    })

(application / 'apply-readback.jsonl').write_text(
    ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in readback),
    encoding='utf-8',
)
(application / 'post-apply-catalog-attestation.json').write_text(
    json.dumps({'catalogs': post_catalogs, 'allKeySetsEqual': True}, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
    encoding='utf-8',
)
summary = {
    'repository': 'snapetech-org/slskdN',
    'pullRequest': 409,
    'state': 'OPEN',
    'draft': True,
    'exactInputHead': EXPECTED_HEAD,
    'exactInputTree': EXPECTED_TREE,
    'selectionRanks': [1, 25],
    'historicalOrdinalRange': None,
    'selectionWasReconstructed': True,
    'sourceIds': 25,
    'locales': 12,
    'cellsReviewed': 300,
    'crossReviewCounts': dict(counts),
    'adjudicatedAdditionalProposals': 4,
    'finalChangedCatalogCells': sum(row['changed'] for row in plan),
    'callerGapHolds': 24,
    'callerGapHoldSourceText': ['pods', 'Private Message from {username}'],
    'priorW98HoldsReattestedAndOutstanding': 11,
    'callerReferencesReattested': cross_summary['callerRefsVerified'],
    'catalogs': post_catalogs,
    'catalogKeySetsEqual': True,
    'placeholderMarkupProtectedLiteralFailures': 0,
    'primaryManifestSha256': primary_manifest_sha,
    'primaryManifestFilesVerified': primary_manifest_rows,
    'crossReviewManifestSha256': cross_manifest_sha,
    'crossReviewManifestFilesVerified': cross_manifest_rows,
    'adjudicationManifestSha256': adj_manifest_sha,
    'adjudicationManifestFilesVerified': adj_manifest_rows,
    'nativeSpeakerApproval': False,
    'nativeSpeakerReviewOutstanding': True,
    'browserReview': 'not performed; exact input-head preview availability must be checked after push',
    'testsBuildsCiRun': False,
    'workflowFilesTouched': False,
    'mergeReleaseTag': False,
}
(application / 'apply-summary.json').write_text(
    json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8'
)
readme = '''# slskdN PR #409 W44 reconstructed ranking slice

The primary selection is reconstructed from current pending IDs because the historical W44 ordinal boundary and W40 frozen queue are unavailable. This packet covers ranks 1–25 and makes no claim that those ranks are the original W44 source ordinals.

Primary review, independent cross-review, and separate adjudication cover 300 cells (25 source IDs × 12 locales). The cross-review accepted 15 primary corrections and 16 primary refinements, proposed two additional Arabic corrections and two evidence-label refinements, and retained 24 caller-gap cells. Third-party adjudication accepted all four additional proposals. Application changed 35 catalog values and read back all 300 targets.

The 24 held values remain unchanged because `pods` and `Private Message from {username}` have no production localization caller. The separate 11 W98 holds were reattested and remain outstanding. All twelve catalogs retain the same key set; placeholder, markup, and protected-literal checks passed. The cross-review reattested 41 caller references.

The full primary, cross-review, and adjudication packets are preserved with their original checksum manifests. `application/` records pre-apply catalog pins, the 300-cell plan, exact readback, and post-apply catalog attestations.

This is machine-assisted review, not qualified native-speaker approval. Browser review was not performed here; verify exact-SHA deployment state before headed review. No tests, builds, scans, CI dispatches, workflow edits, merges, releases, or tags were made.

The repository's local pre-commit and pre-push hooks invoke security scans outside the private-JIT route, so they were not run for this commit/push.
'''
(EVIDENCE / 'README.md').write_text(readme, encoding='utf-8')
manifest_path = EVIDENCE / 'SHA256SUMS.txt'
manifest_lines = []
for path in sorted(p for p in EVIDENCE.rglob('*') if p.is_file() and p != manifest_path):
    manifest_lines.append(f'{sha_bytes(path.read_bytes())}  {path.relative_to(EVIDENCE).as_posix()}')
manifest_path.write_text('\n'.join(manifest_lines) + '\n', encoding='utf-8')
print(json.dumps({'evidence': str(EVIDENCE), 'manifestFiles': len(manifest_lines), 'summary': summary}, ensure_ascii=False, indent=2))
