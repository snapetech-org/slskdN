#!/usr/bin/env python3
import collections, hashlib, json, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261030/slskdn-pr409-batch4-docs-20261101')
def sha(v): return hashlib.sha256(v if isinstance(v,bytes) else v.encode('utf-8')).hexdigest()
def lines(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
m=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
inputs=lines(ROOT/'review-input.jsonl'); decisions=lines(ROOT/'review-decisions.jsonl'); plan=lines(ROOT/'crossreview-plan.jsonl')
assert len(inputs)==266 and len({r['id'] for r in inputs})==266
assert len(decisions)==266 and {d['id'] for d in decisions}=={r['id'] for r in inputs}
assert len(plan)==29 and {d['id'] for d in plan}=={d['id'] for d in decisions if d['verdict']=='correct'}
by={r['id']:r for r in inputs}; dby={d['id']:d for d in decisions}; pby={d['id']:d for d in plan}
for ident, r in by.items():
 d=dby[ident]
 if d['verdict']=='correct':
  p=pby[ident]; target=d['target']
  assert p['proposedTarget']==target and p['currentTarget']==r['target'] and p['currentTargetSha256']==sha(r['target']) and p['proposedTargetSha256']==sha(target)
  assert p['sourceSha256']==r['sourceSha256'] and p['source']==r['source']
  assert collections.Counter(re.findall(r'\{[^{}]+\}',target))==collections.Counter(re.findall(r'\{[^{}]+\}',r['source']))
  for lit in r.get('protectedLiterals',[]): assert target.count(lit)==r['source'].count(lit)
  if r['sourceId']=='src_0143a3db005e1e7f': assert 'mb:recording:12345-6789-...' in target
 elif d['verdict']!='keep': raise AssertionError((ident,d))
pr=json.loads(subprocess.check_output(['gh','api','repos/snapetech-org/slskdN/pulls/409','--jq','{head:.head.sha,state:.state,draft:.draft}'],text=True))
head=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()
tree=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD^{tree}'],text=True).strip()
source_tree=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD:src'],text=True).strip()
assert pr=={'head':m['headCommit'],'state':'open','draft':True}
assert head==m['headCommit'] and tree==m['tree'] and source_tree==m['sourceSubtreeTree']
assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain'],text=True).strip()
for loc,digest in m['currentCatalogFileSha256'].items():
 p=REPO/f'src/web/public/locales/{loc}.json'; assert sha(p.read_bytes())==digest
callers=0
for r in inputs:
 for c in r.get('sourceCallsites',[]):
  raw=(REPO/c['path']).read_bytes(); assert sha(raw)==c['fileSha256']
  text=raw.decode('utf-8').splitlines()[c['line']-1].strip(); assert text==c['lineText'] and sha(text)==c['lineTextSha256']; callers+=1
report={'result':'PASS','prHead':head,'tree':tree,'sourceSubtreeTree':source_tree,'inputRows':len(inputs),'decisionRows':len(decisions),'correctionRows':len(plan),'keepRows':sum(d['verdict']=='keep' for d in decisions),'callerPins':callers,'catalogPins':len(m['currentCatalogFileSha256']),'sourceTargetPlaceholderAndIdentifierChecks':'passed','repositoryWorktree':'clean','catalogsChanged':False,'testsBuildsScansCiRun':False}
(ROOT/'verification-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
