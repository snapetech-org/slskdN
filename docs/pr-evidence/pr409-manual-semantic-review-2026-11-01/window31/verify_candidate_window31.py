#!/usr/bin/env python3
import collections,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=Path('/mnt/disks/scratch/task-worktrees/localization-20261030')
REPO=BASE/'slskdn-pr409-batch4-docs-20261101'
BUNDLE=BASE/'slskdn-populated-review-4c2b-20261101/bundle'
RESULTS=BASE/'semantic-review-results/slskdn-4c2b2e47-v1-912fadf3fce5'
EVIDENCE=REPO/'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01'
LOCALES=['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
BRANCH='refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(*a): return subprocess.check_output(['git','-C',str(REPO),*a],text=True).strip()
def show(commit,path): return subprocess.check_output(['git','-C',str(REPO),'show',f'{commit}:{path}'])
def fail(s): raise SystemExit('FAIL: '+s)
manifest=json.loads((ROOT/'manifest.json').read_text()); pre=json.loads((ROOT/'preflight.json').read_text()); summary=json.loads((ROOT/'review-summary.json').read_text())
state=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,mergeStateStatus,headRefOid'],text=True))
head,tree,src=git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}'),git('rev-parse','HEAD:src')
remote=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin',BRANCH],text=True).split()[0]
if state!={'state':'OPEN','isDraft':True,'mergeStateStatus':'CLEAN','headRefOid':head} or (head,tree,src,remote)!=(manifest['headCommit'],manifest['tree'],manifest['sourceSubtreeTree'],head): fail('live PR/local/remote exact pin mismatch')
if git('status','--porcelain'): fail('repository worktree is not clean')
if pre.get('result')!='PRECHECK_PASS' or pre.get('head')!=head or pre.get('tree')!=tree or pre.get('formalOverlap') or pre.get('manualOverlap'): fail('preflight pin/overlap mismatch')
inputs=rows(ROOT/'review-input.jsonl'); decisions=rows(ROOT/'review-decisions.jsonl'); plan=rows(ROOT/'crossreview-plan.jsonl')
for path,section,n in [(ROOT/'review-input.jsonl','reviewInput',274),(ROOT/'review-decisions.jsonl','reviewDecisions',274),(ROOT/'crossreview-plan.jsonl','crossReviewPlan',36)]:
 meta=manifest[section]
 if len(rows(path))!=n or sha(path.read_bytes())!=meta['sha256']: fail(f'count/hash mismatch: {path.name}')
byin={r['id']:r for r in inputs}; bydec={r['id']:r for r in decisions}; byplan={r['id']:r for r in plan}
if len(byin)!=274 or set(byin)!=set(bydec) or len(byplan)!=36: fail('evidence IDs are duplicate/mismatched')
selected=manifest['scope']['selectedSourceIds']
if len(selected)!=25 or len({r['sourceId'] for r in inputs})!=25: fail('source key count mismatch')
if set(selected)!={r['sourceId'] for r in inputs}: fail('selected key/input join mismatch')
# Reconstruct formal and prior manual coverage and prove this packet is disjoint.
sys.path.insert(0,str(BASE/'translation-tools')); import strict_populated_semantic_review_runner_core as core
bm=json.loads((BUNDLE/'manifest.json').read_text())
b=core.load_bundle(BUNDLE,'912fadf3fce5d827fae0978323cfc7a3e96ded860be2d9c20fafe49b2720cbea','dde0829c435956ee80c7efe64d70f4c6a787dc71cbd4652d88b88303e845e111',bm['headCommit'],bm['tree'],'snapetech-org/slskdN','slskdn',BASE/'slskdn-populated-review-4c2b-20261101/snapshot-repo')
fs=core.scan_results(b,RESULTS); formal={d['id'] for j in fs['valid'].values() for d in j['decisions']}
manual=set()
for n in range(1,31): manual|={r['id'] for r in rows(EVIDENCE/f'window{n}'/'review-input.jsonl')}
if len(formal)!=4800 or len(manual)!=8964 or formal&manual: fail('formal/prior manual accumulator mismatch')
if any(i in formal or i in manual for i in byin): fail('W31 candidate overlaps formal or earlier manual cells')
for loc in LOCALES:
 raw=show(head,f'src/web/public/locales/{loc}.json')
 if sha(raw)!=manifest['currentCatalogFileSha256'][loc]: fail(f'current catalog SHA changed for {loc}')
 catalog=json.loads(raw.decode())
 if len(catalog)!=6169: fail(f'catalog shape changed for {loc}')
 for r in inputs:
  if r['locale']==loc and catalog.get(r['catalogKey'])!=r['target']: fail(f'current catalog target mismatch {r["id"]}')
pattern=lambda s:collections.Counter(re.findall(r'\{[^{}]+\}',s))
caller_count=0
for ident,r in byin.items():
 if ident!=f'{r["locale"]}:{r["sourceId"]}' or r['sourceId'] not in selected: fail(f'malformed ID {ident}')
 if sha(r['source'])!=r['sourceSha256'] or sha(r['target'])!=r['targetSha256']: fail(f'source/current target hash mismatch {ident}')
 for c in r.get('sourceCallsites',[]):
  raw=show(head,c['path']); lines=raw.decode().splitlines(); line=lines[c['line']-1].strip()
  if sha(raw)!=c['fileSha256'] or line!=c['lineText'] or sha(line)!=c['lineTextSha256']: fail(f'caller pin mismatch {ident} {c["path"]}:{c["line"]}')
  caller_count+=1
 d=bydec[ident]
 if d['verdict']=='keep':
  if set(d)!={'id','verdict'}: fail(f'malformed keep {ident}')
 elif d['verdict']=='correct':
  t=d['target']
  if not t.strip() or t==r['target'] or pattern(t)!=pattern(r['source']): fail(f'placeholder/target mismatch {ident}')
  for literal in r.get('protectedLiterals',[]):
   if t.count(literal)!=r['source'].count(literal): fail(f'literal mismatch {ident}')
 else: fail(f'unknown decision {ident}')
for ident,p in byplan.items():
 r,d=byin[ident],bydec[ident]; loc=r['locale']
 exact=(p['id']==ident and p['sourceId']==r['sourceId'] and p['locale']==loc and p['catalogPath']==r['catalogPath'] and p['catalogKey']==r['catalogKey'] and p['source']==r['source'] and p['sourceSha256']==r['sourceSha256'] and p['currentTarget']==r['target'] and p['currentTargetSha256']==r['targetSha256'] and p['proposedTarget']==d['target'] and p['proposedTargetSha256']==sha(d['target']) and p['sourceCallsites']==r.get('sourceCallsites',[]))
 pins=(p['currentPrHead']==head and p['currentPrTree']==tree and p['currentSourceSubtreeTree']==src and p['currentCatalogFileSha256']==manifest['currentCatalogFileSha256'][loc])
 if not exact or not pins or p['confidence']!='high': fail(f'exact candidate join/pin mismatch {ident}')
counts=collections.Counter(d['verdict'] for d in decisions)
if counts!=collections.Counter({'keep':238,'correct':36}): fail(f'verdict counts mismatch {dict(counts)}')
if set(byplan)!={i for i,d in bydec.items() if d['verdict']=='correct'}: fail('candidate plan/disposition join mismatch')
result={'result':'PASS','head':head,'tree':tree,'sourceSubtreeTree':src,'prState':state['state'],'prDraft':state['isDraft'],'mergeStateStatus':state['mergeStateStatus'],'remoteHead':remote,'sourceKeys':len(selected),'cells':len(inputs),'perLocaleCells':pre['perLocaleCells'],'verdicts':dict(sorted(counts.items())),'correctionRows':len(plan),'correctionSourceKeys':len({r['sourceId'] for r in plan}),'candidatePlanSha256':sha((ROOT/'crossreview-plan.jsonl').read_bytes()),'decisionsSha256':sha((ROOT/'review-decisions.jsonl').read_bytes()),'inputSha256':sha((ROOT/'review-input.jsonl').read_bytes()),'formalCells':len(formal),'formalOverlap':0,'priorManualCells':len(manual),'manualOverlap':0,'callerLinesRechecked':caller_count,'placeholderAndProtectedLiteralAudit':'PASS','repoWorktree':'clean','targetsApplied':False}
(ROOT/'candidate-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.name}\n' for p in sorted(ROOT.glob('*')) if p.is_file() and p.name!='SHA256SUMS.txt'),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
