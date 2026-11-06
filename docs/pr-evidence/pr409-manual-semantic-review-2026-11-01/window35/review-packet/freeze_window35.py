#!/usr/bin/env python3
"""Freeze W35 from the current PR object into task-scratch; repository reads only."""
import collections,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path('/mnt/disks/scratch/task-scratch/slskdn-manual-review-window35-91727326-20261102')
BASE=Path('/mnt/disks/scratch/task-worktrees/localization-20261030')
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261102/slskdn-pr409-w35-review')
BUNDLE=BASE/'slskdn-populated-review-4c2b-20261101'/'bundle'
RESULTS=BASE/'semantic-review-results/slskdn-4c2b2e47-v1-912fadf3fce5'
EVIDENCE='docs/pr-evidence/pr409-manual-semantic-review-2026-11-01'
HEAD='917273260c49cca1c14576a0720fc84998d2846d'
TREE='1cdd8c831d224a5706ac6f3e465add4fd249d2be'
SRC='594e56c3f439bad476b1bd57e0de1665c62fa1bb'
BRANCH='refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES=['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
sys.path.insert(0,str(BASE/'translation-tools'))
import strict_populated_semantic_review_runner_core as core

def sha(v): return hashlib.sha256(v if isinstance(v,bytes) else v.encode('utf-8')).hexdigest()
def jsonl_bytes(rows): return ''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in rows).encode('utf-8')
def read_jsonl_bytes(raw): return [json.loads(x) for x in raw.decode('utf-8').splitlines() if x.strip()]
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args])
def git_text(*args): return git(*args).decode('utf-8').strip()
def show_jsonl(path): return read_jsonl_bytes(git('show',f'{HEAD}:{path}'))
def fail(message): raise SystemExit('FAIL: '+message)
# Confirm exact live and stored PR pins before using the frozen backlog.
pr=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,mergeStateStatus,headRefOid'],text=True))
if pr!={'state':'OPEN','isDraft':True,'mergeStateStatus':'CLEAN','headRefOid':HEAD}: fail(f'PR state/head changed: {pr}')
if git_text('rev-parse',f'{HEAD}^{{tree}}')!=TREE or git_text('rev-parse',f'{HEAD}:src/web/src')!=SRC: fail('PR commit/tree/source subtree mismatch')
remote=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin',BRANCH],text=True).split()
if len(remote)<1 or remote[0]!=HEAD: fail(f'remote PR branch mismatch: {remote}')
if git_text('status','--porcelain'): fail('shared inspection worktree is not clean')
# Validate the frozen baseline and formal lane without changing them.
bm=json.loads((BUNDLE/'manifest.json').read_text(encoding='utf-8'))
bundle=core.load_bundle(BUNDLE,'912fadf3fce5d827fae0978323cfc7a3e96ded860be2d9c20fafe49b2720cbea','dde0829c435956ee80c7efe64d70f4c6a787dc71cbd4652d88b88303e845e111',bm['headCommit'],bm['tree'],'snapetech-org/slskdN','slskdn',BASE/'slskdn-populated-review-4c2b-20261101'/'snapshot-repo')
formal_scan=core.scan_results(bundle,RESULTS)
if formal_scan['invalid'] or len(formal_scan['valid'])!=150 or len(formal_scan['missing'])!=1951: fail(f'formal accumulator mismatch {len(formal_scan["valid"])}/{len(formal_scan["missing"])}/{len(formal_scan["invalid"])}')
formal={d['id'] for group in formal_scan['valid'].values() for d in group['decisions']}
if len(formal)!=4800: fail(f'formal cell count mismatch: {len(formal)}')
formal_rows=[{'id':ident} for ident in sorted(formal)]
(ROOT/'formal-cell-ids.jsonl').write_bytes(jsonl_bytes(formal_rows))
# Confirm the prior 34 review windows remain pairwise disjoint and match cumulative totals.
manual_ids=set(); manual_keys=set(); manual_cells=0; window_counts=[]
for n in range(1,35):
 path=f'{EVIDENCE}/window{n}/review-input.jsonl'
 if n==32: path=f'{EVIDENCE}/window32/review-packet/review-input.jsonl'
 if n==33: path=f'{EVIDENCE}/window33/review-packet/review-input.jsonl'
 if n==34: path=f'{EVIDENCE}/window34/review-packet/review-input.jsonl'
 rows=show_jsonl(path); ids={r['id'] for r in rows}
 if len(ids)!=len(rows) or manual_ids&ids: fail(f'manual window overlap at W{n}')
 manual_ids|=ids; manual_keys|={r['sourceId'] for r in rows}; manual_cells+=len(rows)
 window_counts.append({'window':n,'cells':len(rows),'sourceKeys':len({r['sourceId'] for r in rows})})
if (manual_cells,len(manual_ids),len(manual_keys))!=(10052,10052,847): fail(f'prior manual totals mismatch {manual_cells}/{len(manual_ids)}/{len(manual_keys)}')
if formal&manual_ids: fail(f'formal/manual overlap: {len(formal&manual_ids)}')
# Read exact application ledgers through W34 from the pinned commit; ensure no duplicates.
applied_paths=[
 'docs/pr-evidence/pr409-catalog-correction-application-2026-11-01/applied-corrections.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows18-19-2026-11-02/applied-corrections.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows20-21-2026-11-02/applied-corrections.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02/applied-corrections-windows22-23.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02/applied-corrections-realm-window20.jsonl',
]+[f'docs/pr-evidence/pr409-catalog-correction-application-window{n}-2026-11-02/applied-corrections-window{n}.jsonl' for n in range(24,35)]
applied=[]; applied_hashes={}
for path in applied_paths:
 raw=git('show',f'{HEAD}:{path}'); applied_hashes[path]=sha(raw); applied.extend(read_jsonl_bytes(raw))
applied_ids={r['id'] for r in applied}
if len(applied)!=1373 or len(applied_ids)!=1373 or not applied_ids<=manual_ids: fail(f'applied ledger mismatch rows={len(applied)} unique={len(applied_ids)} outsideManual={len(applied_ids-manual_ids)}')
# Read the frozen pending cells and select the next 25 sorted source IDs.
pending={}
for locale in LOCALES:
 for row in core.read_jsonl(BUNDLE/'pending'/f'{locale}.jsonl'):
  if row['id'] in pending: fail(f'duplicate frozen pending ID {row["id"]}')
  pending[row['id']]=row
if len(pending)!=67080: fail(f'frozen pending count changed: {len(pending)}')
remaining={i:r for i,r in pending.items() if i not in formal and i not in manual_ids}
by_source=collections.defaultdict(list)
for row in remaining.values(): by_source[row['sourceId']].append(row)
selected=sorted(by_source)[:25]
if len(selected)!=25: fail(f'expected 25 next source keys, got {len(selected)}')
rows=[r for sid in selected for r in sorted(by_source[sid],key=lambda x:LOCALES.index(x['locale']))]
ids=[r['id'] for r in rows]
if len(ids)!=len(set(ids)) or any(i in formal or i in manual_ids or i in applied_ids for i in ids): fail('W35 selected rows overlap existing decisions')
# Re-read all locale catalogs and source/caller files from the exact PR commit object.
catalogs={}; catalog_hashes={}; catalog_key_counts={}; caller_count=0
for locale in LOCALES:
 path=f'src/web/public/locales/{locale}.json'; raw=git('show',f'{HEAD}:{path}')
 catalogs[locale]=json.loads(raw.decode('utf-8')); catalog_hashes[locale]=sha(raw); catalog_key_counts[locale]=len(catalogs[locale])
 if catalog_key_counts[locale]!=6169: fail(f'catalog key count changed: {locale}={catalog_key_counts[locale]}')
for row in rows:
 ident,locale=row['id'],row['locale']
 if row.get('reviewDisposition')!='pending': fail(f'non-pending selected row {ident}')
 if catalogs[locale].get(row['catalogKey'])!=row['target'] or sha(row['target'])!=row['targetSha256']: fail(f'current catalog target/hash mismatch {ident}')
 if sha(row['source'])!=row['sourceSha256']: fail(f'source hash mismatch {ident}')
 for caller in row.get('sourceCallsites',[]):
  raw=git('show',f'{HEAD}:{caller["path"]}')
  if sha(raw)!=caller['fileSha256']: fail(f'caller source file hash mismatch {ident} {caller["path"]}')
  lines=raw.decode('utf-8').splitlines()
  if not 1<=caller['line']<=len(lines): fail(f'caller line out of range {ident}')
  line=lines[caller['line']-1].strip()
  if line!=caller['lineText'] or sha(line)!=caller['lineTextSha256']: fail(f'caller context line mismatch {ident} {caller["path"]}:{caller["line"]}')
  caller_count+=1
payload=jsonl_bytes(rows)
(ROOT/'review-input.jsonl').write_bytes(payload)
cell_counts=collections.Counter(r['locale'] for r in rows)
# Record exact pins, previous scope, source files, and freeze results.
manifest={'schemaVersion':1,'artifactKind':'manual exact-head populated-catalog semantic review evidence','window':35,'repository':'snapetech-org/slskdN','pullRequest':409,'livePullRequestState':'OPEN','livePullRequestDraft':True,'livePullRequestMergeState':'CLEAN','headCommit':HEAD,'tree':TREE,'remoteBranchHead':remote[0],'sourceSubtreePath':'src/web/src','sourceSubtreeTree':SRC,'frozenCatalogBaseline':{'head':bm['headCommit'],'tree':bm['tree'],'bundleManifestSha256':'912fadf3fce5d827fae0978323cfc7a3e96ded860be2d9c20fafe49b2720cbea','batchesSha256':'dde0829c435956ee80c7efe64d70f4c6a787dc71cbd4652d88b88303e845e111'},'formalAccumulator':{'validJobs':len(formal_scan['valid']),'missingJobs':len(formal_scan['missing']),'invalidJobs':len(formal_scan['invalid']),'formalCells':len(formal),'cellIdsPath':'formal-cell-ids.jsonl','cellIdsSha256':sha((ROOT/'formal-cell-ids.jsonl').read_bytes())},'priorManualCoverage':{'windows':34,'cells':manual_cells,'sourceKeys':len(manual_keys),'windowCounts':window_counts,'overlapPairs':0},'priorAppliedCorrectionLedger':{'rows':len(applied),'uniqueIds':len(applied_ids),'perFileSha256':applied_hashes},'scope':{'selectedSourceIds':selected,'sourceKeyCount':len(selected),'cells':len(rows),'pendingCellsFrozen':len(pending),'remainingNonOverlappingCellsBeforeSelection':len(remaining),'remainingSourceIdsBeforeSelection':len(by_source),'directLocales':LOCALES,'perLocaleCells':dict(sorted(cell_counts.items())),'allSelectedRowsPending':True,'allSelectedTargetsMatchCurrentCatalog':True,'formalOverlap':0,'priorManualOverlap':0,'priorCorrectionOverlap':0},'reviewInput':{'path':'review-input.jsonl','rows':len(rows),'sha256':sha(payload)},'currentCatalogFileSha256':catalog_hashes,'catalogKeyCounts':catalog_key_counts,'sourceCallerLinesPreflighted':caller_count,'reviewerMethod':'manual semantic review of each selected locale cell against exact English source and caller contexts, product terminology, placeholders, and protected literals; no model/API call','nativeSpeakerReview':'not performed; remains required','targetsApplied':False,'catalogsEdited':False,'sourceEdited':False,'formalLedgerEdited':False,'prBodyEdited':False,'modelCalls':0,'translationApiCalls':0}
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
pre={'result':'PRECHECK_PASS','window':35,'livePrState':'OPEN','livePrDraft':True,'livePrMergeState':'CLEAN','head':HEAD,'tree':TREE,'remoteHead':remote[0],'sourceSubtreeTree':SRC,'sourceKeys':len(selected),'selectedSourceIds':selected,'cells':len(rows),'perLocaleCells':dict(sorted(cell_counts.items())),'formalCells':len(formal),'formalCellIdsSha256':sha((ROOT/'formal-cell-ids.jsonl').read_bytes()),'priorManualCells':manual_cells,'priorManualKeys':len(manual_keys),'priorAppliedCorrections':len(applied),'remainingNonOverlappingCells':len(remaining),'remainingSourceIds':len(by_source),'callerLinesRechecked':caller_count,'reviewInputSha256':sha(payload),'catalogHashes':catalog_hashes,'formalOverlap':0,'manualOverlap':0,'appliedOverlap':0,'repoFilesWritten':False}
(ROOT/'preflight.json').write_text(json.dumps(pre,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
summary={'result':'FROZEN_PENDING_MANUAL_REVIEW','window':35,'reviewBaseHead':HEAD,'reviewBaseTree':TREE,'sourceSubtreePath':'src/web/src','sourceSubtreeTree':SRC,'sourceKeys':len(selected),'cells':len(rows),'perLocalePendingCells':dict(sorted(cell_counts.items())),'manualDecisionsPending':len(rows),'correctionRows':0,'keepRows':0,'uncertainRows':0,'nativeSpeakerReview':'outstanding'}
(ROOT/'freeze-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(pre,ensure_ascii=False,indent=2))
