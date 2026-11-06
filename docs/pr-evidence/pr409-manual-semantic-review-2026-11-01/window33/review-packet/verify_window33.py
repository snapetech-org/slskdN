#!/usr/bin/env python3
import collections, hashlib, json, re, subprocess
from pathlib import Path
ROOT=Path('/mnt/disks/scratch/task-scratch/slskdn-manual-review-window33-0abf10ae-20261102')
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261030/slskdn-pr409-batch4-docs-20261101')
BRANCH='refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'
def sha(data): return hashlib.sha256(data if isinstance(data,bytes) else data.encode('utf-8')).hexdigest()
def read_jsonl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
def fail(s): raise SystemExit('FAIL: '+s)
manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
pr=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,mergeStateStatus,headRefOid'],text=True))
head,tree,source_tree=git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}'),git('rev-parse','HEAD:src/web/src')
remote_rows=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin',BRANCH],text=True).splitlines()
remote=remote_rows[0].split()[0] if remote_rows else ''
if (pr['state'],pr['isDraft'],pr['mergeStateStatus'],pr['headRefOid']) != ('OPEN',True,'CLEAN',manifest['headCommit']): fail(f'live PR pin changed: {pr}')
if (head,tree,source_tree,remote)!=(manifest['headCommit'],manifest['tree'],manifest['sourceSubtreeTree'],manifest['headCommit']): fail('local/source/remote pin changed')
if git('status','--porcelain'): fail('repository worktree is not clean')
inputs=read_jsonl(ROOT/'review-input.jsonl')
ledger=read_jsonl(ROOT/'review-decisions.jsonl')
plan=read_jsonl(ROOT/'crossreview-plan.jsonl')
if sha((ROOT/'review-input.jsonl').read_bytes())!=manifest['reviewInput']['sha256']: fail('input hash mismatch')
if len(inputs)!=274 or len(ledger)!=len(inputs) or len({r['id'] for r in inputs})!=len(inputs): fail('input/decision coverage counts mismatch')
by_input={row['id']:row for row in inputs}
by_decision={row['id']:row for row in ledger}
by_plan={row['id']:row for row in plan}
if set(by_input)!=set(by_decision) or len(by_plan)!=len(plan): fail('decision/candidate ID coverage mismatch')
locales=manifest['scope']['directLocales']
for locale in locales:
 rel=f'src/web/public/locales/{locale}.json'
 raw=(REPO/rel).read_bytes()
 if sha(raw)!=manifest['currentCatalogFileSha256'][locale]: fail(f'catalog hash mismatch: {locale}')
 catalog=json.loads(raw.decode('utf-8'))
 for row in inputs:
  if row['locale']!=locale: continue
  if catalog.get(row['catalogKey'])!=row['target'] or sha(row['target'])!=row['targetSha256']: fail(f'current catalog target/hash mismatch: {row["id"]}')
  if sha(row['source'])!=row['sourceSha256']: fail(f'source hash mismatch: {row["id"]}')
  for caller in row.get('sourceCallsites',[]):
   caller_raw=(REPO/caller['path']).read_bytes()
   if sha(caller_raw)!=caller['fileSha256']: fail(f'caller blob mismatch: {row["id"]}/{caller["path"]}')
   lines=caller_raw.decode('utf-8').splitlines()
   if caller['line']<1 or caller['line']>len(lines): fail(f'caller line out of range: {row["id"]}')
   line=lines[caller['line']-1].strip()
   if line!=caller['lineText'] or sha(line)!=caller['lineTextSha256']: fail(f'caller line mismatch: {row["id"]}/{caller["path"]}:{caller["line"]}')
for ident,d in by_decision.items():
 row=by_input[ident]
 if d['sourceSha256']!=row['sourceSha256'] or d['currentTargetSha256']!=row['targetSha256']: fail(f'decision hash mismatch: {ident}')
 if d['verdict']=='correct':
  c=by_plan.get(ident)
  if not c or c['currentTargetSha256']!=row['targetSha256'] or c['proposedTargetSha256']!=sha(c['proposedTarget']): fail(f'candidate hash mismatch: {ident}')
  if sha(c['proposedTarget'])!=c['proposedTargetSha256']: fail(f'candidate target hash mismatch: {ident}')
  if sorted(re.findall(r'\{[^{}]+\}',row['source']))!=sorted(re.findall(r'\{[^{}]+\}',c['proposedTarget'])): fail(f'placeholder mismatch: {ident}')
  if any(lit not in c['proposedTarget'] for lit in row.get('protectedLiterals',[])): fail(f'protected literal missing: {ident}')
 elif ident in by_plan: fail(f'non-correction has candidate plan: {ident}')
counts=collections.Counter(r['verdict'] for r in ledger)
if dict(counts)!={'correct':41,'keep':222,'uncertain':11}: fail(f'verdict totals mismatch: {dict(counts)}')
if sha((ROOT/'review-decisions.jsonl').read_bytes())!=manifest['reviewDecisionLedger']['sha256']: fail('decision ledger hash mismatch')
if sha((ROOT/'crossreview-plan.jsonl').read_bytes())!=manifest['candidatePlan']['sha256']: fail('candidate plan hash mismatch')
summary=json.loads((ROOT/'review-summary.json').read_text(encoding='utf-8'))
if summary['verdicts']!=dict(sorted(counts.items())) or summary['cells']!=len(inputs): fail('review summary mismatch')
report={'result':'PASS','window':33,'livePrState':pr['state'],'livePrDraft':pr['isDraft'],'liveHead':head,'liveTree':tree,'sourceSubtreePath':manifest['sourceSubtreePath'],'sourceSubtreeTree':source_tree,'remoteHead':remote,'repositoryClean':True,'inputRows':len(inputs),'sourceKeys':len({r['sourceId'] for r in inputs}),'callerLinesRechecked':sum(len(r.get('sourceCallsites',[])) for r in inputs),'decisionRows':len(ledger),'candidateRows':len(plan),'verdicts':dict(sorted(counts.items())),'reviewInputSha256':sha((ROOT/'review-input.jsonl').read_bytes()),'decisionLedgerSha256':sha((ROOT/'review-decisions.jsonl').read_bytes()),'candidatePlanSha256':sha((ROOT/'crossreview-plan.jsonl').read_bytes()),'catalogHashes':manifest['currentCatalogFileSha256'],'crossReview':'pending','nativeSpeakerReview':'outstanding','catalogsEdited':False,'repositoryDocsEdited':False}
(ROOT/'verification-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
names=['review-input.jsonl','review-decisions.jsonl','crossreview-plan.jsonl','manifest.json','preflight.json','review-summary.json','verification-report.json','README.md','freeze_window33.py','build_packets_window33.py','verify_window33.py']
for name in names:
 if not (ROOT/name).is_file(): fail(f'missing checksummed artifact: {name}')
(ROOT/'SHA256SUMS.txt').write_text(''.join(f'{sha((ROOT/name).read_bytes())}  {name}\n' for name in names),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
