#!/usr/bin/env python3
import collections, hashlib, json, subprocess, sys
from pathlib import Path

ROOT = Path('/mnt/disks/scratch/task-scratch/slskdn-manual-review-window33-0abf10ae-20261102')
BASE = Path('/mnt/disks/scratch/task-worktrees/localization-20261030')
REPO = BASE / 'slskdn-pr409-batch4-docs-20261101'
BUNDLE = BASE / 'slskdn-populated-review-4c2b-20261101' / 'bundle'
RESULTS = BASE / 'semantic-review-results/slskdn-4c2b2e47-v1-912fadf3fce5'
EVIDENCE = REPO / 'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01'
LOCALES = ['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
BRANCH = 'refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'
EXPECTED_HEAD = '0abf10ae9f49d27d7cfef823cfe5d70765ee29f4'
EXPECTED_TREE = '8ac49de1cde7dc242484eadc597781819e26e1d2'
EXPECTED_SOURCE_TREE = '594e56c3f439bad476b1bd57e0de1665c62fa1bb'
EXPECTED_PREV_MANUAL = 9504
EXPECTED_PREV_KEYS = 797
EXPECTED_PREV_APPLIED = 1299
sys.path.insert(0, str(BASE / 'translation-tools'))
import strict_populated_semantic_review_runner_core as core

def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode('utf-8')).hexdigest()
def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
def git(*args):
    return subprocess.check_output(['git','-C',str(REPO),*args], text=True).strip()
def fail(message):
    raise SystemExit('FAIL: '+message)
def ghpr():
    raw = subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,mergeStateStatus,headRefOid'], text=True)
    return json.loads(raw)

pr = ghpr()
head, tree, source_tree = git('rev-parse','HEAD'), git('rev-parse','HEAD^{tree}'), git('rev-parse','HEAD:src/web/src')
remote_rows = subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin',BRANCH], text=True).splitlines()
remote = remote_rows[0].split()[0] if remote_rows else ''
if pr != {'state':'OPEN','isDraft':True,'mergeStateStatus':'CLEAN','headRefOid':EXPECTED_HEAD}:
    fail(f'PR state/head changed: {pr}')
if (head,tree,source_tree,remote) != (EXPECTED_HEAD,EXPECTED_TREE,EXPECTED_SOURCE_TREE,EXPECTED_HEAD):
    fail(f'pin changed local={head}/{tree}/{source_tree} remote={remote}')
if git('status','--porcelain'):
    fail('repo worktree must remain clean')

bm = json.loads((BUNDLE/'manifest.json').read_text(encoding='utf-8'))
bundle = core.load_bundle(BUNDLE,
    '912fadf3fce5d827fae0978323cfc7a3e96ded860be2d9c20fafe49b2720cbea',
    'dde0829c435956ee80c7efe64d70f4c6a787dc71cbd4652d88b88303e845e111',
    bm['headCommit'],bm['tree'],'snapetech-org/slskdN','slskdn',
    BASE/'slskdn-populated-review-4c2b-20261101'/'snapshot-repo')
formal_scan = core.scan_results(bundle, RESULTS)
if formal_scan['invalid'] or len(formal_scan['valid']) != 150 or len(formal_scan['missing']) != 1951:
    fail(f'formal accumulator counts changed: valid={len(formal_scan["valid"])} missing={len(formal_scan["missing"])} invalid={len(formal_scan["invalid"])}')
formal = {d['id'] for item in formal_scan['valid'].values() for d in item['decisions']}
if len(formal) != 4800:
    fail(f'formal cell count changed: {len(formal)}')

manual_ids, manual_keys, manual_cells = set(), set(), 0
window_counts = []
for win in range(1,33):
    path = EVIDENCE/f'window{win}'/'review-input.jsonl'
    if win == 32:
        path = EVIDENCE/'window32'/'review-packet'/'review-input.jsonl'
    rows = read_jsonl(path)
    ids = {row['id'] for row in rows}
    if len(ids) != len(rows) or manual_ids & ids:
        fail(f'duplicate/cross-window overlap in W{win}')
    manual_ids |= ids
    manual_keys |= {row['sourceId'] for row in rows}
    manual_cells += len(rows)
    window_counts.append({'window':win,'cells':len(rows),'sourceKeys':len({r['sourceId'] for r in rows})})
if manual_cells != EXPECTED_PREV_MANUAL or len(manual_ids) != EXPECTED_PREV_MANUAL or len(manual_keys) != EXPECTED_PREV_KEYS:
    fail(f'prior manual totals changed cells={manual_cells} ids={len(manual_ids)} keys={len(manual_keys)}')
if formal & manual_ids:
    fail(f'formal/manual overlap: {len(formal & manual_ids)}')

applied_paths = [
 REPO/'docs/pr-evidence/pr409-catalog-correction-application-2026-11-01/applied-corrections.jsonl',
 REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows18-19-2026-11-02/applied-corrections.jsonl',
 REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows20-21-2026-11-02/applied-corrections.jsonl',
 REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02/applied-corrections-windows22-23.jsonl',
 REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02/applied-corrections-realm-window20.jsonl',
]+[REPO/f'docs/pr-evidence/pr409-catalog-correction-application-window{n}-2026-11-02/applied-corrections-window{n}.jsonl' for n in range(24,33)]
applied = []
for path in applied_paths:
    if not path.is_file(): fail(f'missing applied ledger {path}')
    applied.extend(read_jsonl(path))
applied_ids = {row['id'] for row in applied}
if len(applied) != EXPECTED_PREV_APPLIED or len(applied_ids) != EXPECTED_PREV_APPLIED or not applied_ids <= manual_ids:
    fail(f'applied ledger mismatch rows={len(applied)} ids={len(applied_ids)} not-manual={len(applied_ids-manual_ids)}')

pending_by_id = {}
for locale in LOCALES:
    for row in read_jsonl(BUNDLE/'pending'/f'{locale}.jsonl'):
        if row['id'] in pending_by_id: fail(f'duplicate pending row {row["id"]}')
        pending_by_id[row['id']] = row
if len(pending_by_id) != 67080:
    fail(f'frozen pending-cell total changed: {len(pending_by_id)}')
remaining = {ident:row for ident,row in pending_by_id.items() if ident not in formal and ident not in manual_ids}
by_source = collections.defaultdict(list)
for row in remaining.values(): by_source[row['sourceId']].append(row)
selected_sources = sorted(by_source)[:25]
if len(selected_sources) != 25: fail(f'expected 25 IDs, got {len(selected_sources)}')
rows = [row for sid in selected_sources for row in sorted(by_source[sid],key=lambda r:LOCALES.index(r['locale']))]
ids = [row['id'] for row in rows]
if len(ids) != len(set(ids)) or any(ident in formal or ident in manual_ids or ident in applied_ids for ident in ids):
    fail('selected IDs overlap formal, prior manual, or applied evidence')

catalogs, catalog_hashes, catalog_key_counts = {}, {}, {}
for locale in LOCALES:
    rel=f'src/web/public/locales/{locale}.json'
    raw=(REPO/rel).read_bytes()
    catalog_hashes[locale]=sha(raw)
    catalogs[locale]=json.loads(raw.decode('utf-8'))
    catalog_key_counts[locale]=len(catalogs[locale])
    if catalog_key_counts[locale] != 6169: fail(f'catalog key count {locale}: {catalog_key_counts[locale]}')
caller_lines = 0
for row in rows:
    ident, locale = row['id'], row['locale']
    if row.get('reviewDisposition') != 'pending': fail(f'not pending {ident}')
    if catalogs[locale].get(row['catalogKey']) != row['target'] or sha(row['target']) != row['targetSha256']:
        fail(f'current catalog target/hash mismatch {ident}')
    if sha(row['source']) != row['sourceSha256']: fail(f'source hash mismatch {ident}')
    for caller in row.get('sourceCallsites',[]):
        raw=(REPO/caller['path']).read_bytes()
        if sha(raw) != caller['fileSha256']: fail(f'caller blob changed {ident} {caller["path"]}')
        lines=raw.decode('utf-8').splitlines()
        if caller['line'] < 1 or caller['line'] > len(lines): fail(f'caller line out of range {ident}')
        text=lines[caller['line']-1].strip()
        if text != caller['lineText'] or sha(text) != caller['lineTextSha256']:
            fail(f'caller line pin mismatch {ident} {caller["path"]}:{caller["line"]}')
        caller_lines += 1
payload=''.join(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for row in rows).encode('utf-8')
(ROOT/'review-input.jsonl').write_bytes(payload)
counts=collections.Counter(row['locale'] for row in rows)
manifest={
 'schemaVersion':1,'artifactKind':'manual exact-head populated-catalog semantic review evidence','window':33,
 'repository':'snapetech-org/slskdN','pullRequest':409,'livePullRequestState':'OPEN','livePullRequestDraft':True,
 'headCommit':head,'tree':tree,'remoteBranchHead':remote,'pullRequestMergeStateStatus':pr['mergeStateStatus'],'sourceSubtreePath':'src/web/src','sourceSubtreeTree':source_tree,'compositeSrcTree':git('rev-parse','HEAD:src'),'localeCatalogTree':git('rev-parse','HEAD:src/web/public/locales'),
 'frozenCatalogBaseline':{'head':bm['headCommit'],'tree':bm['tree'],'bundleManifestSha256':'912fadf3fce5d827fae0978323cfc7a3e96ded860be2d9c20fafe49b2720cbea','batchesSha256':'dde0829c435956ee80c7efe64d70f4c6a787dc71cbd4652d88b88303e845e111'},
 'formalAccumulator':{'validJobs':len(formal_scan['valid']),'missingJobs':len(formal_scan['missing']),'invalidJobs':len(formal_scan['invalid']),'formalCells':len(formal)},
 'priorManualCoverage':{'windows':32,'cells':manual_cells,'sourceKeys':len(manual_keys),'windowCounts':window_counts,'overlapPairs':0},
 'priorAppliedCorrectionLedger':{'rows':len(applied),'uniqueIds':len(applied_ids),'perFileSha256':{str(p.relative_to(REPO)):sha(p.read_bytes()) for p in applied_paths}},
 'scope':{'selectedSourceIds':selected_sources,'sourceKeyCount':len(selected_sources),'cells':len(rows),'pendingCellsFrozen':len(pending_by_id),'remainingNonOverlappingCellsBeforeSelection':len(remaining),'remainingSourceIdsBeforeSelection':len(by_source),'directLocales':LOCALES,'perLocaleCells':dict(sorted(counts.items())),'allSelectedRowsPending':True,'allSelectedTargetsMatchCurrentCatalog':True,'formalOverlap':0,'priorManualOverlap':0,'priorCorrectionOverlap':0},
 'reviewInput':{'path':'review-input.jsonl','rows':len(rows),'sha256':sha(payload)},
 'currentCatalogFileSha256':catalog_hashes,'catalogKeyCounts':catalog_key_counts,'sourceCallerLinesPreflighted':caller_lines,
 'reviewerMethod':'manual semantic review against exact source callsites and UI context; no translation model or API call',
 'nativeSpeakerReview':'not performed; remains required','targetsApplied':False,'catalogsEdited':False,'sourceEdited':False,'formalLedgerEdited':False,'prBodyEdited':False,'modelCalls':0,'apiCalls':0
}
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report={'result':'PRECHECK_PASS','window':33,'head':head,'tree':tree,'sourceSubtreeTree':source_tree,'sourceKeys':len(selected_sources),'selectedSourceIds':selected_sources,'cells':len(rows),'perLocaleCells':dict(sorted(counts.items())),'formalCells':len(formal),'priorManualCells':manual_cells,'priorManualKeys':len(manual_keys),'priorAppliedCorrections':len(applied),'remainingNonOverlappingCells':len(remaining),'remainingSourceIds':len(by_source),'callerLinesRechecked':caller_lines,'reviewInputSha256':sha(payload),'catalogHashes':catalog_hashes,'formalOverlap':0,'manualOverlap':0,'appliedOverlap':0}
(ROOT/'preflight.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'SHA256SUMS.freeze.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.name}\n' for p in sorted(ROOT.glob('*')) if p.is_file() and p.name not in {'SHA256SUMS.freeze.txt','freeze_window33.py'}),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
