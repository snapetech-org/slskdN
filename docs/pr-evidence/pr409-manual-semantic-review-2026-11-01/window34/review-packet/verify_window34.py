#!/usr/bin/env python3
"""Read-only exact-pin and packet validator for the W34 review artifacts."""
import collections, hashlib, json, re, subprocess
from pathlib import Path

ROOT=Path('/mnt/disks/scratch/task-scratch/slskdn-manual-review-window34-dc8ed240-20261102')
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261030/slskdn-pr409-batch4-docs-20261101')
BRANCH='refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'
EVIDENCE='docs/pr-evidence/pr409-manual-semantic-review-2026-11-01'

def sha(value): return hashlib.sha256(value if isinstance(value,bytes) else value.encode('utf-8')).hexdigest()
def read_jsonl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
def git_bytes(*args): return subprocess.check_output(['git','-C',str(REPO),*args])
def fail(message): raise SystemExit('FAIL: '+message)

manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
head=manifest['headCommit']; tree=manifest['tree']; source_tree=manifest['sourceSubtreeTree']
pr=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,mergeStateStatus,headRefOid'],text=True))
if (pr['state'],pr['isDraft'],pr['mergeStateStatus'],pr['headRefOid'])!=('OPEN',True,'CLEAN',head): fail(f'live PR state/head changed: {pr}')
if git('rev-parse',f'{head}^{{tree}}')!=tree or git('rev-parse',f'{head}:src/web/src')!=source_tree: fail('PR commit/tree/source subtree mismatch')
remote_rows=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin',BRANCH],text=True).splitlines()
remote=remote_rows[0].split()[0] if remote_rows else ''
if remote!=head: fail(f'remote PR branch mismatch: {remote}')
repo_head=git('rev-parse','HEAD')
repo_status=git('status','--porcelain')
if repo_status: fail('inspection worktree is not clean')

# Reconfirm that the frozen source-key window does not overlap any prior manual
# window or any applied correction ledger carried by this exact PR head.
manual_ids=set(); manual_keys=set(); manual_cells=0
for n in range(1,34):
    path=f'{EVIDENCE}/window{n}/review-input.jsonl'
    if n==32: path=f'{EVIDENCE}/window32/review-packet/review-input.jsonl'
    if n==33: path=f'{EVIDENCE}/window33/review-packet/review-input.jsonl'
    try: prior=[json.loads(x) for x in git_bytes('show',f'{head}:{path}').decode('utf-8').splitlines() if x.strip()]
    except subprocess.CalledProcessError: fail(f'prior manual window missing: W{n}')
    ids={r['id'] for r in prior}
    if len(ids)!=len(prior) or manual_ids&ids: fail(f'prior manual windows overlap at W{n}')
    manual_ids|=ids; manual_keys|={r['sourceId'] for r in prior}; manual_cells+=len(prior)
if (manual_cells,len(manual_keys))!=(9778,822): fail(f'prior manual coverage changed: {manual_cells}/{len(manual_keys)}')
applied_paths=[
 'docs/pr-evidence/pr409-catalog-correction-application-2026-11-01/applied-corrections.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows18-19-2026-11-02/applied-corrections.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows20-21-2026-11-02/applied-corrections.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02/applied-corrections-windows22-23.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02/applied-corrections-realm-window20.jsonl',
]+[f'docs/pr-evidence/pr409-catalog-correction-application-window{n}-2026-11-02/applied-corrections-window{n}.jsonl' for n in range(24,34)]
applied_ids=set(); applied_rows=0
for path in applied_paths:
    try: rows=[json.loads(x) for x in git_bytes('show',f'{head}:{path}').decode('utf-8').splitlines() if x.strip()]
    except subprocess.CalledProcessError: fail(f'applied correction ledger missing: {path}')
    ids={r['id'] for r in rows}
    if len(ids)!=len(rows) or applied_ids&ids: fail(f'applied correction ledger overlaps: {path}')
    applied_ids|=ids; applied_rows+=len(rows)
if (applied_rows,len(applied_ids))!=(1340,1340): fail(f'applied correction total changed: {applied_rows}/{len(applied_ids)}')

inputs=read_jsonl(ROOT/'review-input.jsonl')
decisions=read_jsonl(ROOT/'review-decisions.jsonl')
plan=read_jsonl(ROOT/'crossreview-plan.jsonl')
uncertain=read_jsonl(ROOT/'uncertain-ledger.jsonl')
if sha((ROOT/'review-input.jsonl').read_bytes())!=manifest['reviewInput']['sha256']: fail('review input checksum mismatch')
if len(inputs)!=274 or len({r['id'] for r in inputs})!=len(inputs): fail('input row/unique ID count mismatch')
if len({r['sourceId'] for r in inputs})!=25: fail('source key count mismatch')
if any(r.get('reviewDisposition')!='pending' for r in inputs): fail('selected input cell is not pending')
if any(r['id'] in manual_ids or r['sourceId'] in manual_keys for r in inputs): fail('W34 overlaps a prior manual source key/cell')
if any(r['id'] in applied_ids for r in inputs): fail('W34 overlaps an applied correction')
if manifest['scope'].get('formalOverlap')!=0 or manifest['scope'].get('priorManualOverlap')!=0 or manifest['scope'].get('priorCorrectionOverlap')!=0: fail('manifest reports an unexpected prior overlap')
by_input={r['id']:r for r in inputs}; by_decision={r['id']:r for r in decisions}; by_plan={r['id']:r for r in plan}; by_uncertain={r['id']:r for r in uncertain}
if len(decisions)!=len(inputs) or set(by_input)!=set(by_decision): fail('decision ledger does not cover every input exactly once')
if len(by_plan)!=len(plan) or len(by_uncertain)!=len(uncertain): fail('duplicate correction or uncertain IDs')
if {i for i,d in by_decision.items() if d['verdict']=='correct'}!=set(by_plan): fail('candidate plan does not match correction decisions')
if {i for i,d in by_decision.items() if d['verdict']=='uncertain'}!=set(by_uncertain): fail('separate uncertain ledger does not match uncertain decisions')

locales=manifest['scope']['directLocales']
for locale in locales:
    catalog_path=f'src/web/public/locales/{locale}.json'
    raw=git_bytes('show',f'{head}:{catalog_path}')
    if sha(raw)!=manifest['currentCatalogFileSha256'][locale]: fail(f'catalog blob hash mismatch: {locale}')
    catalog=json.loads(raw.decode('utf-8'))
    for row in inputs:
        if row['locale']!=locale: continue
        if catalog.get(row['catalogKey'])!=row['target'] or sha(row['target'])!=row['targetSha256']: fail(f'catalog target/hash mismatch: {row["id"]}')
        if sha(row['source'])!=row['sourceSha256']: fail(f'source hash mismatch: {row["id"]}')
        source_placeholders=sorted(re.findall(r'\{[^{}]+\}',row['source']))
        if source_placeholders!=sorted(row.get('placeholders',[])): fail(f'frozen source placeholder list mismatch: {row["id"]}')
        if source_placeholders!=sorted(re.findall(r'\{[^{}]+\}',row['target'])): fail(f'current target placeholder mismatch: {row["id"]}')
        for caller in row.get('sourceCallsites',[]):
            caller_raw=git_bytes('show',f'{head}:{caller["path"]}')
            if sha(caller_raw)!=caller['fileSha256']: fail(f'caller file hash mismatch: {row["id"]}/{caller["path"]}')
            lines=caller_raw.decode('utf-8').splitlines()
            if not 1<=caller['line']<=len(lines): fail(f'caller line out of range: {row["id"]}')
            line=lines[caller['line']-1].strip()
            if line!=caller['lineText'] or sha(line)!=caller['lineTextSha256']: fail(f'caller line text/hash mismatch: {row["id"]}/{caller["path"]}:{caller["line"]}')

for ident,d in by_decision.items():
    row=by_input[ident]
    if (d['sourceSha256'],d['currentTargetSha256'])!=(row['sourceSha256'],row['targetSha256']): fail(f'decision source/current hash mismatch: {ident}')
    if d['verdict']=='correct':
        c=by_plan[ident]
        if (c['sourceSha256'],c['currentTargetSha256'])!=(row['sourceSha256'],row['targetSha256']): fail(f'candidate source/current hash mismatch: {ident}')
        if sha(c['proposedTarget'])!=c['proposedTargetSha256'] or d['candidateTargetSha256']!=c['proposedTargetSha256']: fail(f'candidate target hash mismatch: {ident}')
        if sorted(re.findall(r'\{[^{}]+\}',row['source']))!=sorted(re.findall(r'\{[^{}]+\}',c['proposedTarget'])): fail(f'proposed placeholder mismatch: {ident}')
        if any(lit not in c['proposedTarget'] for lit in row.get('protectedLiterals',[])): fail(f'proposed protected literal mismatch: {ident}')
        if c['currentPrHead']!=head or c['currentPrTree']!=tree or c['currentSourceSubtreeTree']!=source_tree: fail(f'candidate pin mismatch: {ident}')
    elif ident in by_plan: fail(f'non-correction unexpectedly has a candidate: {ident}')
    if d['verdict']=='uncertain':
        u=by_uncertain[ident]
        if (u['sourceSha256'],u['currentTargetSha256'])!=(row['sourceSha256'],row['targetSha256']): fail(f'uncertain row hash mismatch: {ident}')

counts=collections.Counter(d['verdict'] for d in decisions)
if dict(counts)!={'correct':33,'keep':240,'uncertain':1}: fail(f'decision counts unexpected: {dict(counts)}')
per_locale={loc:dict(collections.Counter(d['verdict'] for d in decisions if d['locale']==loc)) for loc in locales if any(d['locale']==loc for d in decisions)}
if sum(len(r.get('sourceCallsites',[])) for r in inputs)!=manifest['sourceCallerLinesPreflighted']: fail('source caller line count mismatch')
for path,key in [('review-decisions.jsonl','reviewDecisionLedger'),('crossreview-plan.jsonl','candidatePlan'),('uncertain-ledger.jsonl','uncertainLedger')]:
    if sha((ROOT/path).read_bytes())!=manifest[key]['sha256']: fail(f'{path} manifest checksum mismatch')
summary=json.loads((ROOT/'review-summary.json').read_text(encoding='utf-8'))
if summary['verdicts']!=dict(sorted(counts.items())) or summary['cells']!=len(inputs): fail('review summary mismatch')
if summary['rootCrossReview']!='pending' or summary['nativeSpeakerReview']!='outstanding': fail('review state misrepresented')

report={'result':'PASS','window':34,'livePrState':pr['state'],'livePrDraft':pr['isDraft'],'livePrHead':head,'livePrTree':tree,'sourceSubtreePath':manifest['sourceSubtreePath'],'sourceSubtreeTree':source_tree,'remotePrBranchHead':remote,'inspectionWorktreeHead':repo_head,'inspectionWorktreeClean':True,'priorManualCells':manual_cells,'priorManualSourceKeys':len(manual_keys),'appliedCorrectionRows':applied_rows,'inputCells':len(inputs),'sourceKeys':len({r['sourceId'] for r in inputs}),'localeCells':dict(collections.Counter(r['locale'] for r in inputs)),'callerLinesRechecked':sum(len(r.get('sourceCallsites',[])) for r in inputs),'decisionCounts':dict(sorted(counts.items())),'candidateRows':len(plan),'uncertainRows':len(uncertain),'reviewInputSha256':sha((ROOT/'review-input.jsonl').read_bytes()),'decisionLedgerSha256':sha((ROOT/'review-decisions.jsonl').read_bytes()),'candidatePlanSha256':sha((ROOT/'crossreview-plan.jsonl').read_bytes()),'uncertainLedgerSha256':sha((ROOT/'uncertain-ledger.jsonl').read_bytes()),'catalogHashes':manifest['currentCatalogFileSha256'],'crossReview':'pending','nativeSpeakerReview':'outstanding','catalogsEdited':False,'repositoryDocsEdited':False}
(ROOT/'verification-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
checksum_names=['review-input.jsonl','review-decisions.jsonl','crossreview-plan.jsonl','uncertain-ledger.jsonl','manifest.json','preflight.json','freeze-summary.json','review-summary.json','verification-report.json','README.md','freeze_window34.py','build_packets_window34.py','verify_window34.py']
for name in checksum_names:
    if not (ROOT/name).is_file(): fail(f'checksummed artifact missing: {name}')
(ROOT/'SHA256SUMS.txt').write_text(''.join(f'{sha((ROOT/name).read_bytes())}  {name}\n' for name in checksum_names),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
