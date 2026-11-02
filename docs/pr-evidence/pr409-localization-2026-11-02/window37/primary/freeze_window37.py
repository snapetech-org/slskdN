#!/usr/bin/env python3
"""Freeze the next disjoint exact-head semantic review window into task scratch."""
import collections, copy, hashlib, json, subprocess
from pathlib import Path

ROOT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window37-primary-20261102')
BASE = Path('/mnt/disks/scratch/task-worktrees/localization-20261030')
REPO = Path('/mnt/disks/scratch/task-worktrees/localization-20261102/slskdn-pr409-w36-review')
BUNDLE = BASE / 'slskdn-populated-review-4c2b-20261101' / 'bundle'
HEAD = '2be3fa4dd46a0f0f49adad342f289721e4777035'
TREE = 'f838ae565086dec8639f8a54aa4c7d4572342b5f'
SRC = '594e56c3f439bad476b1bd57e0de1665c62fa1bb'
BRANCH = 'refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES = ['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
BASE_EVIDENCE = 'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01'
W36 = 'docs/pr-evidence/pr409-localization-2026-11-02/window36'
EXPECTED_BUNDLE_MANIFEST = '912fadf3fce5d827fae0978323cfc7a3e96ded860be2d9c20fafe49b2720cbea'
EXPECTED_BATCHES = 'dde0829c435956ee80c7efe64d70f4c6a787dc71cbd4652d88b88303e845e111'
FORMAL_FILE = f'{W36}/primary/formal-cell-ids.jsonl'


def fail(msg):
    raise SystemExit('FAIL: ' + msg)

def sha(value):
    if isinstance(value, str): value = value.encode('utf-8')
    return hashlib.sha256(value).hexdigest()

def jsonl_bytes(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n' for r in rows).encode('utf-8')

def parse_jsonl(raw):
    return [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]

def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args])

def git_text(*args):
    return git(*args).decode('utf-8').strip()

def show_jsonl(path):
    return parse_jsonl(git('show', f'{HEAD}:{path}'))

# Pin the live PR, object tree, source subtree, remote ref and clean inspection worktree.
pr = json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,mergeStateStatus,headRefOid,headRefName,baseRefName'], text=True))
expected_pr = {'state':'OPEN','isDraft':True,'mergeStateStatus':'CLEAN','headRefOid':HEAD,'headRefName':'codex/slskdn-oidc-tooltip-localization-20261030','baseRefName':'main'}
if pr != expected_pr: fail(f'live PR changed: {pr}')
if git_text('rev-parse', f'{HEAD}^{{tree}}') != TREE: fail('pinned commit tree mismatch')
if git_text('rev-parse', f'{HEAD}:src/web/src') != SRC: fail('pinned source subtree mismatch')
remote = subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin',BRANCH],text=True).split()
if not remote or remote[0] != HEAD: fail(f'remote branch mismatch: {remote}')
if git_text('status','--porcelain'): fail('inspection worktree is not clean')

# Verify the frozen baseline bundle and formal-lane IDs previously pinned at W36.
manifest_raw = (BUNDLE / 'manifest.json').read_bytes()
batches_raw = (BUNDLE / 'batches.json').read_bytes()
if sha(manifest_raw) != EXPECTED_BUNDLE_MANIFEST: fail('frozen catalog bundle manifest hash changed')
if sha(batches_raw) != EXPECTED_BATCHES: fail('frozen catalog bundle batches hash changed')
bundle_manifest = json.loads(manifest_raw)
if bundle_manifest.get('headCommit') != '4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb': fail('frozen catalog baseline head mismatch')
if bundle_manifest.get('tree') != '0eb84397dc2b4be4afd730f6818203bd5910cf15': fail('frozen catalog baseline tree mismatch')
formal_raw = git('show', f'{HEAD}:{FORMAL_FILE}')
formal_manifest = json.loads(git('show', f'{HEAD}:{W36}/primary/manifest.json'))
formal = {r['id'] for r in parse_jsonl(formal_raw)}
if len(formal) != 4800 or sha(formal_raw) != formal_manifest['formalAccumulator']['cellIdsSha256']:
    fail('formal Spanish/domain lane pin mismatch')

# Reconstruct the entire previously selected cell set from all 36 exact review windows.
manual_ids, manual_source_ids, windows = set(), set(), []
window_counts = []
for n in range(1, 37):
    if n <= 31:
        path = f'{BASE_EVIDENCE}/window{n}/review-input.jsonl'
    elif n == 32:
        path = f'{BASE_EVIDENCE}/window32/review-packet/review-input.jsonl'
    elif n == 33:
        path = f'{BASE_EVIDENCE}/window33/review-packet/review-input.jsonl'
    elif n == 34:
        path = f'{BASE_EVIDENCE}/window34/review-packet/review-input.jsonl'
    elif n == 35:
        path = f'{BASE_EVIDENCE}/window35/review-packet/review-input.jsonl'
    else:
        path = f'{W36}/primary/review-input.jsonl'
    raw = git('show', f'{HEAD}:{path}')
    rows = parse_jsonl(raw)
    ids = [r['id'] for r in rows]
    if len(ids) != len(set(ids)): fail(f'duplicate cell in W{n}')
    if manual_ids.intersection(ids): fail(f'cell overlap at W{n}')
    window_keys = {r['sourceId'] for r in rows}
    if manual_source_ids.intersection(window_keys): fail(f'source-key overlap at W{n}')
    manual_ids.update(ids)
    manual_source_ids.update(window_keys)
    windows.append({'window':n,'path':path,'rows':len(rows),'sourceKeys':len(window_keys),'sha256':sha(raw)})
    window_counts.append({'window':n,'cells':len(rows),'sourceKeys':len(window_keys)})
if (len(manual_ids),len(manual_source_ids)) != (10601,897):
    fail(f'prior manual coverage mismatch: {len(manual_ids)} cells / {len(manual_source_ids)} source IDs')
if formal & manual_ids: fail(f'formal/manual cell overlap: {len(formal & manual_ids)}')

# Reconcile applied-correction ledgers through W35, and W36's exact 44-row apply plan.
applied_paths = [
 'docs/pr-evidence/pr409-catalog-correction-application-2026-11-01/applied-corrections.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows18-19-2026-11-02/applied-corrections.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows20-21-2026-11-02/applied-corrections.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02/applied-corrections-windows22-23.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02/applied-corrections-realm-window20.jsonl',
] + [f'docs/pr-evidence/pr409-catalog-correction-application-window{n}-2026-11-02/applied-corrections-window{n}.jsonl' for n in range(24,36)]
applied_rows, applied_hashes = [], {}
for path in applied_paths:
    raw = git('show', f'{HEAD}:{path}')
    applied_hashes[path] = sha(raw)
    applied_rows.extend(parse_jsonl(raw))
if len(applied_rows) != 1411 or len({r['id'] for r in applied_rows}) != 1411:
    fail('W1-W35 applied correction ledger count mismatch')
w36_apply_path = f'{W36}/exact-hash-apply-plan.jsonl'
w36_apply_raw = git('show', f'{HEAD}:{w36_apply_path}')
w36_applied = parse_jsonl(w36_apply_raw)
if len(w36_applied) != 44 or len({r['id'] for r in w36_applied}) != 44:
    fail('W36 apply plan count mismatch')
applied_rows.extend(w36_applied)
applied_ids = {r['id'] for r in applied_rows}
if len(applied_ids) != 1455 or not applied_ids <= manual_ids:
    fail(f'applied correction overlap/reconciliation mismatch: {len(applied_ids)} applied')

# Load all frozen pending rows and derive the next 25 source IDs, excluding every prior lane.
pending, locale_counts = {}, collections.Counter()
for locale in LOCALES:
    for line in (BUNDLE / 'pending' / f'{locale}.jsonl').read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        row = json.loads(line)
        if row['id'] in pending: fail(f'duplicate frozen pending cell {row["id"]}')
        pending[row['id']] = row
        locale_counts[locale] += 1
if len(pending) != 67080: fail(f'frozen pending count mismatch: {len(pending)}')
remaining = {ident: row for ident,row in pending.items() if ident not in formal and ident not in manual_ids}
by_source = collections.defaultdict(list)
for row in remaining.values(): by_source[row['sourceId']].append(row)
if set(by_source) & manual_source_ids: fail('remaining backlog contains a previously reviewed source ID')
selected_source_ids = sorted(by_source)[:25]
if len(selected_source_ids) != 25: fail(f'expected next 25 source IDs, found {len(selected_source_ids)}')
rows = [r for source_id in selected_source_ids for r in sorted(by_source[source_id], key=lambda x: LOCALES.index(x['locale']))]
row_ids = [r['id'] for r in rows]
if not rows or len(row_ids) != len(set(row_ids)): fail(f'W37 row identity mismatch: {len(rows)} rows')
if set(row_ids) & formal or set(row_ids) & manual_ids or set(row_ids) & applied_ids:
    fail('W37 cells overlap formal/manual/applied rows')
if set(selected_source_ids) & manual_source_ids: fail('W37 source IDs overlap prior manual windows')

# Read exact current catalogs, then re-attest selected source, target and every caller line.
catalogs, catalog_hashes, catalog_key_counts = {}, {}, {}
for locale in LOCALES:
    path = f'src/web/public/locales/{locale}.json'
    raw = git('show', f'{HEAD}:{path}')
    catalogs[locale] = json.loads(raw.decode('utf-8'))
    catalog_hashes[locale] = sha(raw)
    catalog_key_counts[locale] = len(catalogs[locale])
    if catalog_key_counts[locale] != 6169: fail(f'catalog key count changed: {locale}={catalog_key_counts[locale]}')
caller_attestations = {}
source_map = {}
for row in rows:
    locale, key, source_id = row['locale'], row['catalogKey'], row['sourceId']
    if row.get('reviewDisposition') != 'pending': fail(f'non-pending row {row["id"]}')
    current = catalogs[locale].get(key)
    if current != row['target'] or sha(current) != row['targetSha256']:
        fail(f'current target mismatch at pinned head: {row["id"]}')
    if sha(row['source']) != row['sourceSha256']:
        fail(f'source hash mismatch: {row["id"]}')
    prior = source_map.setdefault(source_id, row)
    if prior['source'] != row['source'] or prior['sourceSha256'] != row['sourceSha256']:
        fail(f'source identity mismatch for {source_id}')
    for caller in row.get('sourceCallsites', []):
        raw = git('show', f'{HEAD}:{caller["path"]}')
        if sha(raw) != caller['fileSha256']: fail(f'caller file hash mismatch: {row["id"]} {caller["path"]}')
        lines = raw.decode('utf-8').splitlines()
        if not 1 <= caller['line'] <= len(lines): fail(f'caller line out of range {row["id"]}')
        line = lines[caller['line']-1].strip()
        if line != caller['lineText'] or sha(line) != caller['lineTextSha256']:
            fail(f'caller line hash mismatch: {row["id"]} {caller["path"]}:{caller["line"]}')
        key_tuple = (caller['path'], caller['line'])
        entry = caller_attestations.setdefault(key_tuple, {
            'path':caller['path'],'line':caller['line'],'lineText':line,
            'lineTextSha256':sha(line),'fileSha256AtHead':sha(raw),'sourceIds':set(),'cellIds':set()
        })
        if entry['fileSha256AtHead'] != sha(raw) or entry['lineTextSha256'] != sha(line): fail('caller tuple collision')
        entry['sourceIds'].add(source_id)
        entry['cellIds'].add(row['id'])

# Preserve ES cells already routed to the frozen formal lane for selected sources.
all_es = {}
for line in (BUNDLE / 'all' / 'es.jsonl').read_text(encoding='utf-8').splitlines():
    if line.strip():
        r = json.loads(line); all_es[r['sourceId']] = r
preserved_es = []
preserved_es_reused = []
for source_id in selected_source_ids:
    formal_id = f'es:{source_id}'
    row = all_es.get(source_id)
    if not row: fail(f'missing frozen Spanish row for source {source_id}')
    current = catalogs['es'].get(row['catalogKey'])
    if current is None: fail(f'missing current Spanish target {formal_id}')
    if current != row['target'] or sha(current) != row['targetSha256']:
        fail(f'current Spanish target differs from frozen lane row: {formal_id}')
    if sha(row['source']) != row['sourceSha256']: fail(f'Spanish source hash mismatch {formal_id}')
    caller_refs = []
    for c in row.get('sourceCallsites', []):
        raw = git('show', f'{HEAD}:{c["path"]}')
        if sha(raw) != c['fileSha256']: fail(f'Spanish caller file mismatch {formal_id}')
        line = raw.decode('utf-8').splitlines()[c['line']-1].strip()
        if line != c['lineText'] or sha(line) != c['lineTextSha256']: fail(f'Spanish caller line mismatch {formal_id}')
        caller_refs.append({'path':c['path'],'line':c['line'],'fileSha256':sha(raw),'lineTextSha256':sha(line)})
    if formal_id in formal:
        preserved_es.append({
            'id':formal_id,'locale':'es','sourceId':source_id,'source':row['source'],
            'sourceSha256':row['sourceSha256'],'catalogKey':row['catalogKey'],
            'catalogPath':row['catalogPath'],'currentTarget':current,
            'currentTargetSha256':sha(current),'formalCellIdPresent':True,
            'callerRefs':caller_refs,
            'preservationDisposition':'already routed through the formal review lane; no W37 decision emitted'
        })
    elif row.get('reviewDisposition') == 'reused_prior_exact':
        preserved_es_reused.append({
            'id':formal_id,'locale':'es','sourceId':source_id,'source':row['source'],
            'sourceSha256':row['sourceSha256'],'catalogKey':row['catalogKey'],
            'catalogPath':row['catalogPath'],'currentTarget':current,
            'currentTargetSha256':sha(current),'reviewDisposition':'reused_prior_exact',
            'callerRefs':caller_refs,
            'preservationDisposition':'exact prior semantic reuse in the frozen inventory; no W37 decision emitted'
        })
    elif formal_id not in {r['id'] for r in rows}:
        fail(f'Spanish cell is neither formal, reused, nor in W37 pending scope: {formal_id}')

# Preserve every explicit active hold register through W36 byte-for-byte, including
# the no-context hold ledgers from W26/W28 and source-context hold from W33.
hold_paths = [
 'docs/pr-evidence/pr409-catalog-correction-application-window26-2026-11-02/uncertain-review-rows.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-window27-2026-11-02/uncertain-review-rows.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-window28-2026-11-02/uncertain-review-rows.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-window29-2026-11-02/uncertain-review-rows.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-window33-2026-11-02/held-context-rows-window33.jsonl',
 f'{W36}/crossreview/holds.jsonl'
]
hold_sources, hold_rows = [], []
for path in hold_paths:
    raw = git('show', f'{HEAD}:{path}')
    parsed = parse_jsonl(raw)
    hold_sources.append({'path':path,'raw':raw,'sha256':sha(raw),'rows':parsed})
    hold_rows.extend((path, idx, r) for idx,r in enumerate(parsed, start=1))
if len(hold_rows) != 50: fail(f'active prior hold inventory changed: {len(hold_rows)} rows')
if len({r['id'] for _,_,r in hold_rows}) != len(hold_rows): fail('duplicate prior hold row across ledgers')
hold_source_ids = {r['sourceId'] for _,_,r in hold_rows}
if hold_source_ids & set(selected_source_ids): fail('W37 overlaps an existing held source ID')
w36_hold_raw = next(x['raw'] for x in hold_sources if x['path'] == f'{W36}/crossreview/holds.jsonl')
if sha(w36_hold_raw) != sha(Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window36-crossreview-20261102/holds.jsonl').read_bytes()):
    fail('W36 scratch hold ledger differs from the exact PR head')
hold_revalidation, preserved_hold_records = [], []
hold_missing_caller_count = 0
for source_path, row_index, r in hold_rows:
    locale = r['locale']; key = r['source']
    current = catalogs[locale].get(key)
    if current != r['currentTarget'] or sha(current) != r['currentTargetSha256']:
        fail(f'prior hold target changed at pinned head: {r["id"]}')
    if sha(r['source']) != r['sourceSha256']: fail(f'prior hold source mismatch: {r["id"]}')
    caller_refs = []
    if not r.get('sourceCallsites'): hold_missing_caller_count += 1
    for c in r.get('sourceCallsites', []):
        raw = git('show', f'{HEAD}:{c["path"]}')
        if sha(raw) != c['fileSha256']: fail(f'prior hold caller file changed: {r["id"]}')
        line = raw.decode('utf-8').splitlines()[c['line']-1].strip()
        if line != c['lineText'] or sha(line) != c['lineTextSha256']:
            fail(f'prior hold caller line changed: {r["id"]}')
        caller_refs.append({'path':c['path'],'line':c['line'],'fileSha256AtW37Head':sha(raw),'lineTextSha256':sha(line)})
    hold_revalidation.append({
        'id':r['id'],'sourceId':r['sourceId'],'locale':locale,'sourceSha256':sha(r['source']),
        'currentTargetSha256AtW37Head':sha(current),'currentTargetUnchanged':True,
        'callerRefsAtW37Head':caller_refs,'callerRefsMissingInOriginalHold':not bool(r.get('sourceCallsites')),
        'sourceHoldLedgerPath':source_path,'sourceHoldLedgerRow':row_index,'holdStillPreserved':True
    })
    preserved_hold_records.append({'sourceHoldLedgerPath':source_path,'sourceHoldLedgerRow':row_index,
        'sourceHoldLedgerSha256':next(x['sha256'] for x in hold_sources if x['path']==source_path),'record':r})

# Emit exact frozen inputs and attestations.
(ROOT / 'formal-cell-ids.jsonl').write_bytes(formal_raw)
input_rows = copy.deepcopy(rows)
for row in input_rows: row['window'] = 37
input_raw = jsonl_bytes(input_rows)
(ROOT / 'review-input.jsonl').write_bytes(input_raw)
(ROOT / 'preserved-prior-routed.jsonl').write_bytes(jsonl_bytes(preserved_es))
(ROOT / 'preserved-spanish-reused.jsonl').write_bytes(jsonl_bytes(preserved_es_reused))
(ROOT / 'preserved-prior-holds.jsonl').write_bytes(jsonl_bytes(preserved_hold_records))
(ROOT / 'hold-revalidation.jsonl').write_bytes(jsonl_bytes(hold_revalidation))
hold_copy_dir = ROOT / 'prior-holds'
for item in hold_sources:
    dest = hold_copy_dir / Path(item['path']).parent.name / Path(item['path']).name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(item['raw'])
source_attest = []
for source_id in selected_source_ids:
    r = source_map[source_id]
    source_attest.append({'window':37,'sourceId':source_id,'source':r['source'],'sourceSha256':sha(r['source']),
                          'sourceFingerprint':r.get('sourceFingerprint'),'sourceSubtreeTree':SRC,
                          'cellIds':sorted(x['id'] for x in rows if x['sourceId']==source_id)})
(ROOT / 'source-attestation.jsonl').write_bytes(jsonl_bytes(source_attest))
caller_rows = []
for _,e in sorted(caller_attestations.items()):
    e = dict(e); e['sourceIds'] = sorted(e['sourceIds']); e['cellIds'] = sorted(e['cellIds']); caller_rows.append(e)
(ROOT / 'caller-attestation.jsonl').write_bytes(jsonl_bytes(caller_rows))

per_locale = dict(sorted(collections.Counter(r['locale'] for r in rows).items()))
if sum(per_locale.values()) != len(rows) or any(not 0 < n <= len(selected_source_ids) for n in per_locale.values()):
    fail(f'W37 locale cell count mismatch: {per_locale}')
manifest = {
 'schemaVersion':1,'artifactKind':'primary exact-head populated-catalog semantic review evidence',
 'window':37,'repository':'snapetech-org/slskdN','pullRequest':409,
 'livePullRequestState':'OPEN','livePullRequestDraft':True,'livePullRequestMergeState':'CLEAN',
 'headCommit':HEAD,'tree':TREE,'remoteBranchHead':remote[0],
 'sourceSubtreePath':'src/web/src','sourceSubtreeTree':SRC,
 'frozenCatalogBaseline':{'head':bundle_manifest['headCommit'],'tree':bundle_manifest['tree'],
   'bundleManifestSha256':sha(manifest_raw),'batchesSha256':sha(batches_raw)},
 'formalAccumulator':{'formalCells':len(formal),'path':FORMAL_FILE,'sha256':sha(formal_raw)},
 'priorManualCoverage':{'windows':36,'cells':len(manual_ids),'sourceKeys':len(manual_source_ids),
   'windowCounts':window_counts,'reviewInputEvidence':windows,'cellOverlapPairs':0,'sourceKeyOverlapPairs':0},
 'priorAppliedCorrectionLedger':{'windows1Through35Rows':1411,'window36ApplyPlanRows':44,
   'rows':len(applied_rows),'uniqueIds':len(applied_ids),'allAppliedIdsWithinPriorManualCells':True,
   'perFileSha256':applied_hashes,'window36ApplyPlanPath':w36_apply_path,'window36ApplyPlanSha256':sha(w36_apply_raw)},
 'priorHolds':{'explicitHoldRows':len(hold_rows),'uniqueHeldSourceIds':len(hold_source_ids),
   'sourceLedgers':[{'path':x['path'],'rows':len(x['rows']),'sha256':x['sha256']} for x in hold_sources],
   'allCurrentTargetsAndAvailableCallersReattested':True,'originalRowsMissingCallerRefs':hold_missing_caller_count,
   'allHoldSourceIdsExcludedFromW37':True,'preservedLedgerPath':'preserved-prior-holds.jsonl',
   'byteExactCopiesDirectory':'prior-holds/'},
 'scope':{'selectedSourceIds':selected_source_ids,'sourceKeyCount':len(selected_source_ids),
   'cells':len(rows),'pendingCellsFrozen':len(pending),'remainingNonOverlappingCellsBeforeSelection':len(remaining),
   'remainingSourceIdsBeforeSelection':len(by_source),'directLocales':LOCALES,
   'perLocaleCells':per_locale,'allSelectedRowsPending':True,'allSelectedTargetsMatchCurrentCatalog':True,
   'formalOverlap':0,'priorManualCellOverlap':0,'priorManualSourceKeyOverlap':0,'priorCorrectionOverlap':0,
   'priorHoldSourceKeyOverlap':0,'preservedFormalSpanishRows':len(preserved_es),
   'preservedSpanishExactReuseRows':len(preserved_es_reused)},
 'reviewInput':{'path':'review-input.jsonl','rows':len(rows),'sha256':sha(input_raw)},
 'currentCatalogFileSha256':catalog_hashes,'catalogKeyCounts':catalog_key_counts,
 'sourceAttestation':{'path':'source-attestation.jsonl','rows':len(source_attest),'sha256':sha((ROOT/'source-attestation.jsonl').read_bytes())},
 'callerAttestation':{'path':'caller-attestation.jsonl','uniquePathLineReferences':len(caller_rows),
   'sha256':sha((ROOT/'caller-attestation.jsonl').read_bytes())},
 'reviewerMethod':'manual semantic review of each selected locale cell against the exact English source, current locale target, caller context, terminology, placeholders and protected literals; no model/API call',
 'nativeSpeakerReview':'not performed; remains required','targetsApplied':False,'catalogsEdited':False,
 'sourceEdited':False,'formalLedgerEdited':False,'prBodyEdited':False,'modelCalls':0,'translationApiCalls':0,
 'testsBuildsScansCiOrReleasesRun':False,'repositoryOrPullRequestMutated':False
}
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
preflight = {
 'result':'PRECHECK_PASS','window':37,'livePrState':'OPEN','livePrDraft':True,
 'head':HEAD,'tree':TREE,'remoteHead':remote[0],'sourceSubtreeTree':SRC,
 'sourceKeys':len(selected_source_ids),'selectedSourceIds':selected_source_ids,'cells':len(rows),
 'perLocaleCells':per_locale,'formalCells':len(formal),'priorManualCells':len(manual_ids),
 'priorManualSourceKeys':len(manual_source_ids),'priorAppliedCorrections':len(applied_ids),
 'priorHoldRows':len(hold_rows),'priorHoldSourceIds':len(hold_source_ids),
 'priorHoldReattestationRows':len(hold_revalidation),'priorHoldCallerRefsMissing':hold_missing_caller_count,
 'preservedSpanishRows':len(preserved_es),'preservedSpanishExactReuseRows':len(preserved_es_reused),
 'remainingNonOverlappingCells':len(remaining),
 'remainingSourceIds':len(by_source),'callerLinesRechecked':len(caller_rows),
 'reviewInputSha256':sha(input_raw),'catalogHashes':catalog_hashes,
 'formalOverlap':0,'manualCellOverlap':0,'manualSourceKeyOverlap':0,'appliedOverlap':0,'holdSourceKeyOverlap':0,
 'repoFilesWritten':False
}
(ROOT/'preflight.json').write_text(json.dumps(preflight,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
summary = {'result':'FROZEN_PENDING_MANUAL_REVIEW','window':37,'reviewBaseHead':HEAD,'reviewBaseTree':TREE,
           'sourceSubtreePath':'src/web/src','sourceSubtreeTree':SRC,'sourceKeys':len(selected_source_ids),
           'cells':len(rows),'perLocalePendingCells':per_locale,'manualDecisionsPending':len(rows),
           'correctionRows':0,'keepRows':0,'uncertainRows':0,'preservedPriorHolds':len(hold_rows),
           'preservedPriorSpanishRows':len(preserved_es),'preservedSpanishExactReuseRows':len(preserved_es_reused),
           'nativeSpeakerReview':'outstanding'}
(ROOT/'freeze-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(preflight,ensure_ascii=False,indent=2))
