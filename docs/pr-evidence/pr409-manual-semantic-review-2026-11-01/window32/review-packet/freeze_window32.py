#!/usr/bin/env python3
import collections, hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=Path('/mnt/disks/scratch/task-worktrees/localization-20261030')
REPO=BASE/'slskdn-pr409-batch4-docs-20261101'
BUNDLE=BASE/'slskdn-populated-review-4c2b-20261101'/'bundle'
RESULTS=BASE/'semantic-review-results/slskdn-4c2b2e47-v1-912fadf3fce5'
EVIDENCE=REPO/'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01'
LOCALES=['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
BRANCH='refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'
EXPECTED_HEAD='dfb9707f946bf2686210bcf1072b9d70c8442a62'
EXPECTED_TREE='9458e836ae12c02573535b5c9dc052f055b7820d'
EXPECTED_SOURCE_TREE='469e060d9e0a3fd6f54bc75a69993ee2651d3e4b'
sys.path.insert(0,str(BASE/'translation-tools'))
import strict_populated_semantic_review_runner_core as core

def sha(data): return hashlib.sha256(data if isinstance(data,bytes) else data.encode('utf-8')).hexdigest()
def read_jsonl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
def fail(s): raise SystemExit('FAIL: '+s)
pr=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,mergeStateStatus,headRefOid'],text=True))
head,tree,source_tree=git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}'),git('rev-parse','HEAD:src')
remote=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin',BRANCH],text=True).split()[0]
if pr!={'state':'OPEN','isDraft':True,'mergeStateStatus':'CLEAN','headRefOid':EXPECTED_HEAD}: fail(f'PR state/head changed: {pr}')
if (head,tree,source_tree,remote)!=(EXPECTED_HEAD,EXPECTED_TREE,EXPECTED_SOURCE_TREE,head): fail(f'current pin changed: {head}/{tree}/{source_tree}/{remote}')
if git('status','--porcelain'): fail('repo worktree must remain clean')
bm=json.loads((BUNDLE/'manifest.json').read_text(encoding='utf-8'))
bundle=core.load_bundle(BUNDLE,'912fadf3fce5d827fae0978323cfc7a3e96ded860be2d9c20fafe49b2720cbea','dde0829c435956ee80c7efe64d70f4c6a787dc71cbd4652d88b88303e845e111',bm['headCommit'],bm['tree'],'snapetech-org/slskdN','slskdn',BASE/'slskdn-populated-review-4c2b-20261101'/'snapshot-repo')
fs=core.scan_results(bundle,RESULTS)
if fs['invalid'] or len(fs['valid'])!=150 or len(fs['missing'])!=1951: fail(f'formal accumulator mismatch {len(fs["valid"])}/{len(fs["missing"])}/{len(fs["invalid"])}')
formal={d['id'] for item in fs['valid'].values() for d in item['decisions']}
if len(formal)!=4800: fail(f'formal cells mismatch: {len(formal)}')
manual=set(); manual_keys=set(); manual_cells=0
for win in range(1,32):
    rows=read_jsonl(EVIDENCE/f'window{win}'/'review-input.jsonl')
    ids={row['id'] for row in rows}
    if len(ids)!=len(rows) or manual&ids: fail(f'duplicate/cross-window overlap at {win}')
    manual|=ids; manual_keys|={row['sourceId'] for row in rows}; manual_cells+=len(rows)
if len(manual)!=9238 or len(manual_keys)!=772 or manual_cells!=9238: fail(f'prior manual totals mismatch {len(manual)}/{len(manual_keys)}/{manual_cells}')
if formal&manual: fail(f'formal/manual overlap {len(formal&manual)}')
applied_paths=[
 REPO/'docs/pr-evidence/pr409-catalog-correction-application-2026-11-01/applied-corrections.jsonl',
 REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows18-19-2026-11-02/applied-corrections.jsonl',
 REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows20-21-2026-11-02/applied-corrections.jsonl',
 REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02/applied-corrections-windows22-23.jsonl',
 REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02/applied-corrections-realm-window20.jsonl',
]+[REPO/f'docs/pr-evidence/pr409-catalog-correction-application-window{n}-2026-11-02/applied-corrections-window{n}.jsonl' for n in range(24,32)]
applied=[]
for p in applied_paths:
 if not p.is_file(): fail(f'missing applied correction ledger {p}')
 applied+=read_jsonl(p)
applied_ids={row['id'] for row in applied}
if len(applied)!=1270 or len(applied_ids)!=1270 or not applied_ids<=manual: fail(f'applied correction ledgers mismatch {len(applied)}/{len(applied_ids)}')
pending_by_id={}
for locale in LOCALES:
 for row in read_jsonl(BUNDLE/'pending'/f'{locale}.jsonl'):
  if row['id'] in pending_by_id: fail(f'duplicate pending row {row["id"]}')
  pending_by_id[row['id']]=row
if len(pending_by_id)!=67080: fail(f'frozen pending-cell count changed: {len(pending_by_id)}')
remaining={i:r for i,r in pending_by_id.items() if i not in formal and i not in manual}
by_source=collections.defaultdict(list)
for row in remaining.values(): by_source[row['sourceId']].append(row)
selected_sources=sorted(by_source)[:25]
if len(selected_sources)!=25: fail(f'expected 25 source IDs, got {len(selected_sources)}')
rows=[row for sid in selected_sources for row in sorted(by_source[sid],key=lambda r:LOCALES.index(r['locale']))]
ids=[r['id'] for r in rows]
if len(ids)!=len(set(ids)) or any(i in formal or i in manual or i in applied_ids for i in ids): fail('candidate overlap')
catalogs={}; catalog_hashes={}; catalog_key_counts={}
for locale in LOCALES:
 rel=f'src/web/public/locales/{locale}.json'; raw=(REPO/rel).read_bytes(); catalog_hashes[locale]=sha(raw); catalogs[locale]=json.loads(raw.decode('utf-8')); catalog_key_counts[locale]=len(catalogs[locale])
 if catalog_key_counts[locale]!=6169: fail(f'catalog key count {locale}: {catalog_key_counts[locale]}')
caller_lines=0
for row in rows:
 ident=row['id']; locale=row['locale']
 if row.get('reviewDisposition')!='pending': fail(f'not pending {ident}')
 if catalogs[locale].get(row['catalogKey'])!=row['target'] or sha(row['target'])!=row['targetSha256']: fail(f'catalog value/hash mismatch {ident}')
 if sha(row['source'])!=row['sourceSha256']: fail(f'source hash mismatch {ident}')
 for c in row.get('sourceCallsites',[]):
  raw=(REPO/c['path']).read_bytes()
  if sha(raw)!=c['fileSha256']: fail(f'caller blob mismatch {ident} {c["path"]}')
  lines=raw.decode('utf-8').splitlines()
  if c['line']<1 or c['line']>len(lines): fail(f'caller line invalid {ident}')
  line=lines[c['line']-1].strip()
  if line!=c['lineText'] or sha(line)!=c['lineTextSha256']: fail(f'caller line pin mismatch {ident} {c["path"]}:{c["line"]}')
  caller_lines+=1
payload=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in rows).encode('utf-8')
(ROOT/'review-input.jsonl').write_bytes(payload)
counts=collections.Counter(r['locale'] for r in rows)
manifest={'schemaVersion':1,'artifactKind':'manual exact-head populated-catalog semantic review evidence','window':32,'repository':'snapetech-org/slskdN','pullRequest':409,'livePullRequestState':'OPEN','livePullRequestDraft':True,'headCommit':head,'tree':tree,'sourceSubtreeTree':source_tree,'frozenCatalogBaseline':{'head':bm['headCommit'],'tree':bm['tree'],'bundleManifestSha256':'912fadf3fce5d827fae0978323cfc7a3e96ded860be2d9c20fafe49b2720cbea','batchesSha256':'dde0829c435956ee80c7efe64d70f4c6a787dc71cbd4652d88b88303e845e111'},'formalAccumulator':{'validJobs':len(fs['valid']),'missingJobs':len(fs['missing']),'invalidJobs':len(fs['invalid']),'formalCells':len(formal)},'priorManualCoverage':{'windows':31,'cells':manual_cells,'sourceKeys':len(manual_keys),'overlapPairs':0},'priorAppliedCorrectionLedger':{'rows':len(applied),'uniqueIds':len(applied_ids),'perFileSha256':{str(p.relative_to(REPO)):sha(p.read_bytes()) for p in applied_paths}},'scope':{'selectedSourceIds':selected_sources,'sourceKeyCount':len(selected_sources),'cells':len(rows),'pendingCellsFrozen':len(pending_by_id),'remainingNonOverlappingCellsBeforeSelection':len(remaining),'remainingSourceIdsBeforeSelection':len(by_source),'directLocales':LOCALES,'perLocaleCells':dict(sorted(counts.items())),'allSelectedRowsPending':True,'allSelectedTargetsMatchCurrentCatalog':True,'formalOverlap':0,'priorManualOverlap':0,'priorCorrectionOverlap':0},'reviewInput':{'path':'review-input.jsonl','rows':len(rows),'sha256':sha(payload)},'currentCatalogFileSha256':catalog_hashes,'catalogKeyCounts':catalog_key_counts,'sourceCallerLinesPreflighted':caller_lines,'reviewerMethod':'manual semantic review against exact source callsites and UI context; no model/API call','nativeSpeakerReview':'not performed; remains required','targetsApplied':False,'catalogsEdited':False,'sourceEdited':False,'formalLedgerEdited':False,'prBodyEdited':False,'modelCalls':0,'apiCalls':0}
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report={'result':'PRECHECK_PASS','head':head,'tree':tree,'sourceSubtreeTree':source_tree,'sourceKeys':len(selected_sources),'selectedSourceIds':selected_sources,'cells':len(rows),'perLocaleCells':dict(sorted(counts.items())),'formalCells':len(formal),'priorManualCells':manual_cells,'priorManualKeys':len(manual_keys),'allPriorAppliedCorrections':len(applied),'remainingNonOverlappingCells':len(remaining),'remainingSourceIds':len(by_source),'callerLinesRechecked':caller_lines,'reviewInputSha256':sha(payload),'catalogHashes':catalog_hashes,'formalOverlap':0,'manualOverlap':0,'appliedOverlap':0}
(ROOT/'preflight.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.name}\n' for p in sorted(ROOT.glob('*')) if p.is_file() and p.name!='SHA256SUMS.txt'),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
