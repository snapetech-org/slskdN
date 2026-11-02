#!/usr/bin/env python3
"""Read-only independent validation of the supplied slskdN W34 packet."""
import collections, hashlib, json, re, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261030/slskdn-pr409-batch4-docs-20261101')
BRANCH='refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'

def sha(value):
    return hashlib.sha256(value if isinstance(value,bytes) else value.encode('utf-8')).hexdigest()
def git(*args, raw=False):
    b=subprocess.check_output(['git','-C',str(REPO),*args])
    return b if raw else b.decode('utf-8').strip()
def jsonl(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def check(condition, message):
    if not condition: raise AssertionError(message)

manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
head=manifest['headCommit']; tree=manifest['tree']; source_tree=manifest['sourceSubtreeTree']
# Confirm the supplied bundle is internally checksum-consistent without modifying it.
listed=set()
for line in (ROOT/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
    digest,name=line.split('  ',1); listed.add(name)
    check((ROOT/name).is_file(),f'missing checksummed artifact {name}')
    check(sha((ROOT/name).read_bytes())==digest,f'input checksum mismatch {name}')
actual_files={p.name for p in ROOT.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt'}
check(listed==actual_files,f'checksummed file set mismatch: listed={len(listed)} actual={len(actual_files)}')
# Live PR/API, remote ref, and exact git object pins.
pr=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,mergeStateStatus,headRefOid'],text=True))
check((pr['state'],pr['isDraft'],pr['mergeStateStatus'],pr['headRefOid'])==('OPEN',True,'CLEAN',head),f'live PR state/head changed: {pr}')
check(git('rev-parse',f'{head}^{{tree}}')==tree,'PR commit tree mismatch')
check(git('rev-parse',f'{head}:{manifest["sourceSubtreePath"]}')==source_tree,'source subtree tree mismatch')
remote_rows=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin',BRANCH],text=True).splitlines()
remote=remote_rows[0].split()[0] if remote_rows else ''
check(remote==head,f'remote branch head mismatch: {remote}')
check(not git('status','--porcelain'),'inspection worktree is dirty')
# Recheck all input and decision cells against exact current catalogs and caller blobs.
inputs=jsonl(ROOT/'review-input.jsonl'); decisions=jsonl(ROOT/'review-decisions.jsonl')
plan=jsonl(ROOT/'crossreview-plan.jsonl'); uncertain=jsonl(ROOT/'uncertain-ledger.jsonl')
check(len(inputs)==274 and len({r['id'] for r in inputs})==274,'input count or duplicate IDs')
check(len({r['sourceId'] for r in inputs})==25,'source key count')
check(len(decisions)==274 and len({r['id'] for r in decisions})==274,'decision count or duplicate IDs')
check(len(plan)==33 and len({r['id'] for r in plan})==33,'candidate count or duplicate IDs')
check(len(uncertain)==1 and len({r['id'] for r in uncertain})==1,'uncertain count or duplicate IDs')
by_input={r['id']:r for r in inputs}; by_decision={r['id']:r for r in decisions}
by_plan={r['id']:r for r in plan}; by_uncertain={r['id']:r for r in uncertain}
check(set(by_input)==set(by_decision),'input/decision ID set mismatch')
check({i for i,d in by_decision.items() if d['verdict']=='correct'}==set(by_plan),'candidate plan vs decisions mismatch')
check({i for i,d in by_decision.items() if d['verdict']=='uncertain'}==set(by_uncertain),'uncertain ledger vs decisions mismatch')
locales=manifest['scope']['directLocales']
check(len(locales)==12,'expected 12 direct locales')
counts=collections.Counter(r['locale'] for r in inputs)
check(dict(counts)==manifest['scope']['perLocaleCells'],'locale counts differ from manifest')
check(sum(counts.values())==274 and counts['es']==0 and counts['fr']==24,'expected 274 pending cells; Spanish none, French one short')
check(sum(len(r.get('sourceCallsites',[])) for r in inputs)==514,'caller line count differs from packet')
file_cache={}
for locale in locales:
    path=f'src/web/public/locales/{locale}.json'
    raw=git('show',f'{head}:{path}',raw=True)
    check(sha(raw)==manifest['currentCatalogFileSha256'][locale],f'catalog blob hash mismatch {locale}')
    catalog=json.loads(raw.decode('utf-8'))
    check(len(catalog)==manifest['catalogKeyCounts'][locale],f'catalog key count mismatch {locale}')
    for row in (r for r in inputs if r['locale']==locale):
        check(catalog.get(row['catalogKey'])==row['target'],f'catalog value mismatch {row["id"]}')
        check(sha(row['source'])==row['sourceSha256'],f'source hash mismatch {row["id"]}')
        check(sha(row['target'])==row['targetSha256'],f'current target hash mismatch {row["id"]}')
        source_ph=sorted(re.findall(r'\{[^{}]+\}',row['source']))
        check(source_ph==sorted(row.get('placeholders',[])),f'placeholder list mismatch {row["id"]}')
        check(source_ph==sorted(re.findall(r'\{[^{}]+\}',row['target'])),f'current placeholder mismatch {row["id"]}')
        current_mismatches=sorted(lit for lit in row.get('protectedLiterals',[]) if lit not in row['target'])
        reported_mismatches=sorted(row.get('targetDiagnostics',{}).get('protectedLiteralMismatches',[]))
        check(current_mismatches==reported_mismatches,f'protected-literal diagnostic mismatch {row["id"]}')
        for call in row.get('sourceCallsites',[]):
            p=call['path']
            if p not in file_cache: file_cache[p]=git('show',f'{head}:{p}',raw=True)
            blob=file_cache[p]
            check(sha(blob)==call['fileSha256'],f'caller file hash mismatch {row["id"]}/{p}')
            lines=blob.decode('utf-8').splitlines(); i=call['line']-1
            check(0<=i<len(lines),f'caller line out of range {row["id"]}/{p}')
            line=lines[i].strip()
            check(line==call['lineText'] and sha(line)==call['lineTextSha256'],f'caller line mismatch {row["id"]}/{p}:{call["line"]}')
for ident,d in by_decision.items():
    row=by_input[ident]
    check((d['sourceSha256'],d['currentTargetSha256'])==(row['sourceSha256'],row['targetSha256']),f'decision hashes mismatch {ident}')
    if ident in by_plan:
        c=by_plan[ident]
        check((c['sourceSha256'],c['currentTargetSha256'])==(row['sourceSha256'],row['targetSha256']),f'candidate input hashes mismatch {ident}')
        check(sha(c['proposedTarget'])==c['proposedTargetSha256'],f'proposal hash mismatch {ident}')
        check(sorted(re.findall(r'\{[^{}]+\}',row['source']))==sorted(re.findall(r'\{[^{}]+\}',c['proposedTarget'])),f'proposal placeholder mismatch {ident}')
        check(all(lit in c['proposedTarget'] for lit in row.get('protectedLiterals',[])),f'proposal protected literal mismatch {ident}')
        check((c['currentPrHead'],c['currentPrTree'],c['currentSourceSubtreeTree'])==(head,tree,source_tree),f'candidate git pin mismatch {ident}')
    current_mismatches=sorted(lit for lit in row.get('protectedLiterals',[]) if lit not in row['target'])
    if current_mismatches:
        check(ident in by_plan,f'protected-literal correction is not in candidate plan {ident}')
    if ident in by_uncertain:
        u=by_uncertain[ident]
        check((u['sourceSha256'],u['currentTargetSha256'])==(row['sourceSha256'],row['targetSha256']),f'uncertain target/source hash mismatch {ident}')
# Confirm the claimed prior manual and applied-correction sets; W34 must not duplicate them.
manual_ids=set(); manual_keys=set(); manual_cells=0
for n in range(1,34):
    path=f'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01/window{n}/review-input.jsonl'
    if n==32:path=f'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01/window32/review-packet/review-input.jsonl'
    if n==33:path=f'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01/window33/review-packet/review-input.jsonl'
    prior=jsonl_bytes=git('show',f'{head}:{path}')
    prior=[json.loads(x) for x in jsonl_bytes.splitlines() if x.strip()]
    ids={r['id'] for r in prior}; keys={r.get('sourceId') or r.get('source_id') for r in prior}
    check(len(ids)==len(prior) and not manual_ids&ids,f'prior manual window duplicate/overlap W{n}')
    manual_ids|=ids; manual_keys|=keys; manual_cells+=len(prior)
check((manual_cells,len(manual_keys))==(9778,822),f'prior manual totals differ: {manual_cells}/{len(manual_keys)}')
applied_paths=[
 'docs/pr-evidence/pr409-catalog-correction-application-2026-11-01/applied-corrections.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows18-19-2026-11-02/applied-corrections.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows20-21-2026-11-02/applied-corrections.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02/applied-corrections-windows22-23.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02/applied-corrections-realm-window20.jsonl',
]+[f'docs/pr-evidence/pr409-catalog-correction-application-window{n}-2026-11-02/applied-corrections-window{n}.jsonl' for n in range(24,34)]
applied=set(); applied_rows=0
for path in applied_paths:
    rows=[json.loads(x) for x in git('show',f'{head}:{path}').splitlines() if x.strip()]
    ids={r.get('id') or r.get('cellId') for r in rows}
    check(len(ids)==len(rows) and not applied&ids,f'applied ledger duplicate/overlap {path}')
    applied|=ids; applied_rows+=len(rows)
check((applied_rows,len(applied))==(1340,1340),f'applied totals differ: {applied_rows}/{len(applied)}')
input_ids=set(by_input)
check(not input_ids&manual_ids,'W34 has exact-cell overlap with previous manual windows')
check(not input_ids&applied,'W34 has exact-cell overlap with applied correction ledger')
check(not {r['sourceId'] for r in inputs}&manual_keys,'W34 source keys overlap prior manual windows')
# Formal overlap is claimed as zero by the frozen preflight; raw formal result rows are not part of this packet.
check(manifest['scope'].get('formalOverlap')==0,'formal overlap is not zero in manifest')
report={
 'result':'PASS', 'prState':pr['state'], 'prDraft':pr['isDraft'], 'prHead':head, 'prTree':tree,
 'remoteBranchHead':remote,'sourceSubtreeTree':source_tree,'currentCatalogFiles':len(locales),
 'inputRows':len(inputs),'uniqueSourceKeys':len({r['sourceId'] for r in inputs}),
 'perLocalePendingCells':dict(counts),'uniqueCallerFiles':len(file_cache),
 'callerLineReferences':sum(len(r.get('sourceCallsites',[])) for r in inputs),
 'priorManualCells':manual_cells,'priorManualSourceKeys':len(manual_keys),
 'appliedCorrectionRows':applied_rows,'exactCellOverlap':0,'sourceKeyOverlap':0,
 'formalOverlapClaimedZero':True,'formalRawRowsPresent':False,
 'decisionRows':len(decisions),'candidateRows':len(plan),'uncertainRows':len(uncertain),
 'sourceCurrentCallerPlaceholderProtectedLiteralPins':'all pass',
 'packetSha256':{n:sha((ROOT/n).read_bytes()) for n in ('review-input.jsonl','review-decisions.jsonl','crossreview-plan.jsonl','uncertain-ledger.jsonl','manifest.json','SHA256SUMS.txt')},
}
(ROOT/'independent-review'/'preflight-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
