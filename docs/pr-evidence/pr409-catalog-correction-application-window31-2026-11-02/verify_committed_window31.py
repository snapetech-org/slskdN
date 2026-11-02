#!/usr/bin/env python3
import hashlib,json,subprocess
from pathlib import Path
BASE=Path('/mnt/disks/scratch/task-worktrees/localization-20261030')
REPO=BASE/'slskdn-pr409-batch4-docs-20261101'
EVIDENCE=REPO/'docs/pr-evidence/pr409-catalog-correction-application-window31-2026-11-02'
MANUAL=REPO/'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01/window31'
APP='b38a95fb75ec4ac691ad02c4b2c7393f8a1389b7';BASE_HEAD='fbafaae2e05af8ce51a263c7be2a92a8728ceb94';TREE='f2e7a734d60555964f0487377066a955308fd8c9'
CANDIDATE='320f88df56d7f9f1f1ec2fe20fab467235ab59471fe7812b63f8ba8979de5bba';ROOT_LEDGER='4e0809fcad3782ab73027cb22f2dea97ce18a3c891e91a7ad872a1ee74d67005';APPLY_PLAN='70067d1a6a13349d1d72db7227d3e79fae1757cc97e50e37330456d3121a64ca';APPLIED_LEDGER='2704474b3d89611ab953246fa99e3230a82e3214bf09ff707dda6bf5939011f7'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
def g(*args):return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
def sha(b):return hashlib.sha256(b).hexdigest()
def show(commit,path):return subprocess.check_output(['git','-C',str(REPO),'show',f'{commit}:{path}'])
head=g('rev-parse','HEAD');tree=g('rev-parse','HEAD^{tree}')
remote=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin','refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'],text=True).split()[0]
pr=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,mergeStateStatus,headRefOid'],text=True))
if g('rev-parse',APP+'^')!=BASE_HEAD or g('rev-parse',APP+'^{tree}')!=TREE: raise SystemExit('W31 application commit parent/tree mismatch')
if subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',APP,head]).returncode: raise SystemExit('W31 app commit not in current PR head chain')
if remote!=head or pr!={'state':'OPEN','isDraft':True,'mergeStateStatus':'CLEAN','headRefOid':head}: raise SystemExit('current PR/local/remote state mismatch')
if g('status','--porcelain'): raise SystemExit('repo worktree must be clean')
expected={'docs/CHANGELOG.md'}|{f'src/web/public/locales/{x}.json' for x in LOCALES if x!='es'}
paths=set(g('diff-tree','--no-commit-id','--name-only','-r',APP).splitlines())
if paths!=expected: raise SystemExit(f'app commit paths mismatch: {paths^expected}')
if g('rev-parse',BASE_HEAD+':.github/workflows')!=g('rev-parse',APP+':.github/workflows'): raise SystemExit('workflow subtree changed')
if g('rev-parse',BASE_HEAD+':src/web/src')!=g('rev-parse',APP+':src/web/src'): raise SystemExit('source code subtree changed')
if subprocess.run(['git','-C',str(REPO),'diff','--check',BASE_HEAD,APP]).returncode: raise SystemExit('app commit diff check failed')
plan=EVIDENCE/'root-apply-plan-window31.jsonl'; root=EVIDENCE/'root-crossreview-decisions-window31.jsonl'; applied=EVIDENCE/'applied-corrections-window31.jsonl';audit=json.loads((EVIDENCE/'apply-audit.json').read_text())
for p,h in [(EVIDENCE/'root-apply-plan-window31.jsonl',APPLY_PLAN),(root,ROOT_LEDGER),(applied,APPLIED_LEDGER),(MANUAL/'crossreview-plan.jsonl',CANDIDATE)]:
 if sha(p.read_bytes())!=h: raise SystemExit(f'evidence checksum mismatch {p.name}')
plans=[json.loads(x) for x in plan.read_text().splitlines() if x.strip()]
ledgers=[json.loads(x) for x in applied.read_text().splitlines() if x.strip()]
root_rows=[json.loads(x) for x in root.read_text().splitlines() if x.strip()]
if len(plans)!=36 or len(ledgers)!=36 or len(root_rows)!=36 or any(x['decision']!='accept' for x in root_rows): raise SystemExit('W31 evidence row count/disposition mismatch')
by={r['id']:r for r in plans}
for row in ledgers:
 p=by[row['id']]
 base_cat=json.loads(show(APP+'^',row['catalogPath']).decode())
 final_cat=json.loads(show(APP,row['catalogPath']).decode())
 if base_cat.get(row['catalogKey'])!=p['currentTarget'] or final_cat.get(row['catalogKey'])!=p['rootTarget']: raise SystemExit(f'commit cell value mismatch {row["id"]}')
 if row['oldTarget']!=p['currentTarget'] or row['oldTargetSha256']!=p['currentTargetSha256'] or row['newTarget']!=p['rootTarget'] or row['newTargetSha256']!=p['rootTargetSha256']: raise SystemExit(f'application row mismatch {row["id"]}')
 if hashlib.sha256(row['source'].encode()).hexdigest()!=row['sourceSha256']: raise SystemExit(f'source hash mismatch {row["id"]}')
 for c in row['sourceCallsites']:
  raw=show(APP+'^',c['path']);line=raw.decode().splitlines()[c['line']-1].strip()
  if hashlib.sha256(raw).hexdigest()!=c['fileSha256'] or line!=c['lineText'] or hashlib.sha256(line.encode()).hexdigest()!=c['lineTextSha256']: raise SystemExit(f'caller pin mismatch {row["id"]}')
for loc,h in audit['newCatalogFileSha256'].items():
 if sha(show(APP,f'src/web/public/locales/{loc}.json'))!=h: raise SystemExit(f'application catalog SHA mismatch {loc}')
result={'result':'PASS','applicationCommit':APP,'applicationTree':TREE,'applicationParent':BASE_HEAD,'currentHead':head,'currentTree':tree,'remoteHead':remote,'prState':pr['state'],'prDraft':pr['isDraft'],'mergeStateStatus':pr['mergeStateStatus'],'applicationPaths':sorted(paths),'applicationRows':36,'candidatePlanSha256':CANDIDATE,'rootDecisionLedgerSha256':ROOT_LEDGER,'rootApplyPlanSha256':APPLY_PLAN,'appliedLedgerSha256':APPLIED_LEDGER,'sourceCodeSubtreeEqual':True,'workflowSubtreeEqual':True,'diffCheck':'PASS','worktree':'clean'}
(BASE/'slskdn-manual-review-window31-fbafaae2-20261102'/'post-push-verification-window31.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
