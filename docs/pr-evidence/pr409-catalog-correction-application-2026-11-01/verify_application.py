#!/usr/bin/env python3
"""Verify PR #409 manual review reconciliation and exact-hash catalog application."""
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = Path(__file__).resolve().parent
MANUAL = ROOT / 'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01'
LOCALES = ['ar', 'de', 'es', 'fr', 'hi', 'id', 'ja', 'ko', 'pt-BR', 'vi', 'zh-Hans', 'zh-Hant']
BASELINE = '4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb'


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_text(value):
    return sha_bytes(value.encode('utf-8'))


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def parse_json_unique(data, label):
    def pairs(items):
        obj = {}
        for k, v in items:
            if k in obj:
                raise ValueError(f'duplicate JSON key in {label}: {k!r}')
            obj[k] = v
        return obj
    return json.loads(data, object_pairs_hook=pairs)


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


def show_json(commit, path):
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{commit}:{path}'])
    return parse_json_unique(raw.decode('utf-8'), f'{commit}:{path}'), raw


def fail(message):
    raise SystemExit('FAIL: ' + message)


manifest = json.loads((BUNDLE / 'manifest.json').read_text(encoding='utf-8'))
preflight = json.loads((BUNDLE / 'preflight.json').read_text(encoding='utf-8'))
rows = load_jsonl(BUNDLE / 'applied-corrections.jsonl')
held = load_jsonl(BUNDLE / 'held-no-context.jsonl')
if manifest['repository'] != 'snapetech-org/slskdN' or manifest['pullRequest'] != 409:
    fail('repository/PR mismatch')
if sha_bytes((BUNDLE / 'applied-corrections.jsonl').read_bytes()) != manifest['inputArtifacts']['appliedCorrectionsSha256']:
    fail('correction evidence checksum mismatch')
if sha_bytes((BUNDLE / 'held-no-context.jsonl').read_bytes()) != manifest['inputArtifacts']['heldNoContextSha256']:
    fail('held evidence checksum mismatch')
if sha_bytes((BUNDLE / 'preflight.json').read_bytes()) != manifest['inputArtifacts']['preflightSha256']:
    fail('preflight checksum mismatch')
if preflight['formalOverlap'] != 0 or preflight['manualCellOverlap'] != 0:
    fail('preflight formal/manual overlap was nonzero')
if preflight['manualCells'] != 5100 or preflight['formalRowsCovered'] != 4800:
    fail('preflight scope counts mismatch')
if len(rows) != 736 or len(held) != 6:
    fail(f'proposal/held row count mismatch: {len(rows)}/{len(held)}')
row_ids = [r['id'] for r in rows]
if len(set(row_ids)) != len(row_ids):
    fail('duplicate applied row ID')
proposal_by_id = {r['id']: r for r in rows}
held_ids = {r['id'] for r in held}
if set(proposal_by_id) & held_ids:
    fail('applied/held overlap')
if len({r['sourceId'] for r in rows}) != 175:
    fail('applied source-key count mismatch')

# Verify the seven published application commits and that each commit changes only its exact batch.
all_batch_ids = set()
expected_parent = manifest['applicationBaseHead']
for batch in manifest['batches']:
    commit = batch['commit']
    if git('rev-parse', commit + '^') != expected_parent or batch['parentCommit'] != expected_parent:
        fail(f"batch {batch['batch']} parent chain mismatch")
    if git('rev-parse', commit + '^{tree}') != batch['tree']:
        fail(f"batch {batch['batch']} tree mismatch")
    ids = set(batch['sourceIds'])
    if len(ids) != 25 or all_batch_ids & ids:
        fail(f"batch {batch['batch']} source-ID overlap/size mismatch")
    all_batch_ids |= ids
    batch_rows = [r for r in rows if r['sourceId'] in ids]
    canonical = '\n'.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) for r in batch_rows) + '\n'
    if sha_text(canonical) != batch['selectedRowsSha256'] or len(batch_rows) != batch['cellCount']:
        fail(f"batch {batch['batch']} row hash/count mismatch")
    locale_counts = Counter(r['locale'] for r in batch_rows)
    if dict(sorted(locale_counts.items())) != batch['perLocaleCellCounts']:
        fail(f"batch {batch['batch']} locale count mismatch")
    expected_locale_paths = {f'src/web/public/locales/{l}.json' for l in locale_counts}
    changed_paths = set(git('diff-tree', '--no-commit-id', '--name-only', '-r', commit).splitlines())
    if changed_paths != expected_locale_paths | {'docs/CHANGELOG.md'}:
        fail(f"batch {batch['batch']} changed unexpected paths: {sorted(changed_paths)}")
    for f in batch['changedCatalogFiles']:
        path = f['path']
        before, before_raw = show_json(expected_parent, path)
        after, after_raw = show_json(commit, path)
        if sha_bytes(before_raw) != f['beforeFileSha256'] or sha_bytes(after_raw) != f['afterFileSha256']:
            fail(f"batch {batch['batch']} file hash mismatch: {path}")
        selected = [r for r in batch_rows if r['catalogPath'] == path]
        expected = dict(before)
        for row in selected:
            key = row['catalogKey']
            if before.get(key) != row['currentTarget'] or sha_text(before.get(key, '')) != row['currentTargetSha256']:
                fail(f"batch {batch['batch']} pre-target mismatch: {row['id']}")
            if after.get(key) != row['proposedTarget'] or sha_text(after.get(key, '')) != row['proposedTargetSha256']:
                fail(f"batch {batch['batch']} proposed-target mismatch: {row['id']}")
            expected[key] = row['proposedTarget']
        if after != expected:
            fail(f"batch {batch['batch']} changed unproposed values in {path}")
    expected_parent = commit
if len(all_batch_ids) != 175 or expected_parent != manifest['verifiedCorrectionCommitHead']:
    fail('batch coverage/final correction head mismatch')
if git('rev-parse', manifest['verifiedCorrectionCommitHead'] + '^{tree}') != manifest['verifiedCorrectionCommitTree']:
    fail('final correction tree mismatch')

# Revalidate all source callsites and proposed hashes against the current source tree.
source_cache = {}
for row in rows:
    if sha_text(row['source']) != row['sourceSha256'] or sha_text(row['proposedTarget']) != row['proposedTargetSha256']:
        fail(f"source/proposed hash mismatch: {row['id']}")
    for callsite in row['sourceCallsites']:
        path = callsite['path']
        if path not in source_cache:
            source_cache[path] = (ROOT / path).read_bytes()
        raw = source_cache[path]
        if sha_bytes(raw) != callsite['fileSha256']:
            fail(f"source file hash mismatch: {path}")
        lines = raw.decode('utf-8').splitlines()
        actual = lines[callsite['line'] - 1].strip()
        if actual != callsite['lineText'] or sha_text(actual) != callsite['lineTextSha256']:
            fail(f"source line hash mismatch: {path}:{callsite['line']}")

# Census all locale catalogs and compare every changed value since the frozen baseline.
current_catalogs = {}
base_catalogs = {}
for locale in LOCALES:
    path = f'src/web/public/locales/{locale}.json'
    current_disk = (ROOT / path).read_bytes()
    current_head, current_head_raw = show_json('HEAD', path)
    base, _ = show_json(BASELINE, path)
    if current_disk != current_head_raw:
        fail(f'worktree catalog differs from current HEAD: {path}')
    if len(current_head) != 6169 or any(not isinstance(v, str) or not v for v in current_head.values()):
        fail(f'catalog key/value census failed: {path}')
    if set(current_head) != set(base):
        fail(f'catalog key set differs from frozen baseline: {path}')
    current_catalogs[locale] = current_head
    base_catalogs[locale] = base

changed_by_locale = Counter()
expected_cells = {(r['locale'], r['catalogKey']): r for r in rows}
for locale in LOCALES:
    changed = {k for k in base_catalogs[locale] if base_catalogs[locale][k] != current_catalogs[locale][k]}
    expected = {key for (loc, key) in expected_cells if loc == locale}
    if changed != expected:
        fail(f"frozen-baseline changed-cell set mismatch for {locale}: actual={len(changed)}, expected={len(expected)}")
    changed_by_locale[locale] = len(changed)
    for key in expected:
        row = expected_cells[(locale, key)]
        if base_catalogs[locale][key] != row['currentTarget'] or current_catalogs[locale][key] != row['proposedTarget']:
            fail(f"frozen/current catalog value mismatch: {locale}:{key}")

# Reconcile all 5,100 manual decisions against baseline and current catalogs.
manual_rows = {}
verdicts = Counter()
for window in range(1, 18):
    folder = MANUAL / f'window{window}'
    inputs = load_jsonl(folder / 'review-input.jsonl')
    decisions = load_jsonl(folder / 'review-decisions.jsonl')
    if len(inputs) != 300 or len(decisions) != 300:
        fail(f'window {window} row count mismatch')
    decision_map = {r['id']: r['verdict'] for r in decisions}
    if len(decision_map) != 300 or set(decision_map) != {r['id'] for r in inputs}:
        fail(f'window {window} input/decision join mismatch')
    for row in inputs:
        ident = row['id']
        if ident in manual_rows:
            fail(f'manual review overlap: {ident}')
        manual_rows[ident] = row
        verdict = decision_map[ident]
        verdicts[verdict] += 1
        locale, key = row['locale'], row['catalogKey']
        if sha_text(row['target']) != row['targetSha256'] or base_catalogs[locale].get(key) != row['target']:
            fail(f'frozen review target mismatch: {ident}')
        current = current_catalogs[locale].get(key)
        if verdict == 'correct' and ident in proposal_by_id:
            expected = proposal_by_id[ident]['proposedTarget']
        elif verdict == 'correct' and ident in held_ids:
            expected = row['target']
        elif verdict in ('keep', 'uncertain'):
            expected = row['target']
        else:
            fail(f'unreconciled manual verdict: {ident} {verdict}')
        if current != expected:
            fail(f'current catalog does not reconcile to verdict: {ident}')
if len(manual_rows) != 5100 or len({r['sourceId'] for r in manual_rows.values()}) != 425:
    fail('manual review census mismatch')
if verdicts != Counter({'keep': 4187, 'correct': 742, 'uncertain': 171}):
    fail(f'manual verdict totals mismatch: {verdicts}')
if set(r['id'] for r in manual_rows.values() if any(r['id'] == h['id'] for h in held)) != held_ids:
    fail('held rows are not in the manual evidence')

# Check the repository delta contains no workflow changes and no source changes.
changed_repo_paths = set(git('diff', '--name-only', BASELINE, 'HEAD').splitlines())
workflow_paths = [p for p in changed_repo_paths if p.startswith('.github/workflows/')]
source_paths = [p for p in changed_repo_paths if p.startswith('src/') and '/locales/' not in p]
if workflow_paths or source_paths:
    fail(f'unexpected workflow/source changes: workflows={workflow_paths}; source={source_paths}')

summary = {
 'result':'PASS',
 'head':git('rev-parse','HEAD'),
 'catalogCensus':{'locales':len(LOCALES),'keysPerLocale':6169,'totalValues':6169*len(LOCALES),'changedCellsSinceFrozenBaseline':sum(changed_by_locale.values()),'changedCellsByLocale':dict(changed_by_locale)},
 'application':{'appliedCells':len(rows),'appliedSourceKeys':len({r['sourceId'] for r in rows}),'heldNoContext':len(held),'applicationCommits':len(manifest['batches'])},
 'manualReconciliation':{'windows':17,'keys':len({r['sourceId'] for r in manual_rows.values()}),'cells':len(manual_rows),'verdicts':dict(verdicts),'manualOverlap':0,'formalOverlap':preflight['formalOverlap'],'formalCellsCovered':preflight['formalRowsCovered']},
 'sourceCallsiteFilesVerified':len(source_cache),
 'workflowChanges':0,
 'nonCatalogSourceChanges':0,
}
print(json.dumps(summary,ensure_ascii=False,indent=2))
