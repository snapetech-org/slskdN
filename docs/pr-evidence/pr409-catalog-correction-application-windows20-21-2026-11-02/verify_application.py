#!/usr/bin/env python3
import collections,hashlib,json,re,subprocess,sys
from pathlib import Path
BASE=Path('/mnt/disks/scratch/task-worktrees/localization-20261030')
REPO=BASE/'slskdn-pr409-batch4-docs-20261101'
ROOT=Path(__file__).resolve().parent
MANUAL=REPO/'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01'
OLD_APP=REPO/'docs/pr-evidence/pr409-catalog-correction-application-2026-11-01'
PREV_APP=REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows18-19-2026-11-02'
BASELINE='4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
EXPECTED_TOTALS={'ar':96,'de':44,'es':70,'fr':67,'hi':76,'id':79,'ja':46,'ko':62,'pt-BR':62,'vi':89,'zh-Hans':90,'zh-Hant':88}

def sha(b):return hashlib.sha256(b if isinstance(b,bytes) else b.encode('utf-8')).hexdigest()
def rows(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(*a):return subprocess.check_output(['git','-C',str(REPO),*a],text=True).strip()
def show(commit,path):return subprocess.check_output(['git','-C',str(REPO),'show',f'{commit}:{path}'])
def parse(raw,label):
 def hook(items):
  d={}
  for k,v in items:
   if k in d:raise ValueError(f'duplicate JSON key {k!r} in {label}')
   d[k]=v
  return d
 return json.loads(raw.decode('utf-8'),object_pairs_hook=hook)
def fail(s):raise SystemExit('FAIL: '+s)

def main():
 m=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
 pre=json.loads((ROOT/'preflight.json').read_text(encoding='utf-8'))
 app=json.loads((ROOT/'application-result.json').read_text(encoding='utf-8'))
 new=rows(ROOT/'applied-corrections.jsonl')
 old=rows(OLD_APP/'applied-corrections.jsonl');prev=rows(PREV_APP/'applied-corrections.jsonl')
 held=rows(OLD_APP/'held-no-context.jsonl')
 if len(new)!=51 or len(old)!=736 or len(prev)!=82 or len(held)!=6:fail('applied/held row count mismatch')
 if sha((ROOT/'applied-corrections.jsonl').read_bytes())!=pre['newApplicationRowsSha256']:fail('new correction ledger checksum mismatch')
 application_commit=m['applicationCommit']; application_tree=m['applicationTree']
 if pre['liveHead']!=git('rev-parse',application_commit+'^') or pre['liveTree']!=git('rev-parse',application_commit+'^1^{tree}'):fail('preflight base does not match application commit parent')
 if git('rev-parse',application_commit+'^{tree}')!=application_tree:fail('application commit tree mismatch')
 if subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',application_commit,'HEAD']).returncode:fail('application commit is not an ancestor of current head')
 head=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}')
 state=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,headRefOid'],text=True))
 remote=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin','refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'],text=True).split()[0]
 if state!={'state':'OPEN','isDraft':True,'headRefOid':head} or remote!=head:fail(f'PR/remote is not at final application head: {state}; remote={remote}; head={head}')
 if git('rev-parse','HEAD^')!=pre['liveHead']:fail('application commit parent mismatch')
 paths=set(git('diff-tree','--no-commit-id','--name-only','-r',application_commit).splitlines())
 expected_paths={f'src/web/public/locales/{l}.json' for l in LOCALES if any(r['locale']==l for r in new)}|{'docs/CHANGELOG.md'}
 if paths!=expected_paths:fail(f'application commit paths differ: {sorted(paths^expected_paths)}')
 status=git('status','--porcelain').splitlines()
 allowed=['docs/localization/pr409-populated-catalog-semantic-review-2026-11-01.md','docs/pr-evidence/pr409-catalog-correction-application-windows20-21-2026-11-02/']
 for item in status:
  path=item[2:].lstrip()
  if not any(path==a or path.startswith(a) for a in allowed):fail(f'unexpected worktree change during final census: {item}')
 if git('rev-parse',BASELINE+'^{tree}')!='0eb84397dc2b4be4afd730f6818203bd5910cf15':fail('frozen catalog baseline tree changed')
 if git('rev-parse',pre['liveHead']+':src')!=pre['sourceSubtreeTree']:fail('preflight source tree pin mismatch')
 old_by={r['id']:r for r in old};prev_by={r['id']:r for r in prev};new_by={r['id']:r for r in new};held_by={r['id']:r for r in held}
 if any(len(d)!=n for d,n in [(old_by,736),(prev_by,82),(new_by,51),(held_by,6)]):fail('duplicate ledger IDs')
 if (set(old_by)&set(prev_by))|(set(old_by)&set(new_by))|(set(prev_by)&set(new_by))|(set(held_by)&(set(old_by)|set(prev_by)|set(new_by))):fail('application/held ledger overlap')
 applied=old+prev+new
 if len({r['id'] for r in applied})!=869:fail('cumulative applied ID count mismatch')
 if len({r['sourceId'] for r in applied})!=211:fail('cumulative applied source-key count mismatch')
 if collections.Counter(r['locale'] for r in applied)!=collections.Counter(EXPECTED_TOTALS):fail('cumulative per-locale correction counts mismatch')
 # Verify source/value hashes and callsites for all corrections.
 for r in applied:
  target=r.get('proposedTarget',r.get('appliedTarget')); target_sha=r.get('proposedTargetSha256',r.get('appliedTargetSha256'))
  if sha(r['source'])!=r['sourceSha256'] or not target or sha(target)!=target_sha:fail(f'source/target hash mismatch: {r["id"]}')
  if collections.Counter(re.findall(r'{[^{}]+}',r['source']))!=collections.Counter(re.findall(r'{[^{}]+}',target)):fail(f'placeholder mismatch: {r["id"]}')
  for c in r.get('sourceCallsites',[]):
   raw=(REPO/c['path']).read_bytes()
   if sha(raw)!=c['fileSha256']:fail(f'callsite file hash mismatch: {c["path"]}')
   line=raw.decode('utf-8').splitlines()[c['line']-1].strip()
   if line!=c['lineText'] or sha(line)!=c['lineTextSha256']:fail(f'callsite line mismatch: {c["path"]}:{c["line"]}')
 basecat={};current={};after_hash={};changed_by={}
 for l in LOCALES:
  path=f'src/web/public/locales/{l}.json'
  basecat[l]=parse(show(BASELINE,path),f'{BASELINE}:{path}')
  current[l]=parse(show(head,path),f'{head}:{path}')
  if len(basecat[l])!=6169 or len(current[l])!=6169 or set(basecat[l])!=set(current[l]):fail(f'catalog census/key-set mismatch: {l}')
  if any(not isinstance(v,str) or not v for v in current[l].values()):fail(f'empty/nonstring catalog value: {l}')
  if show(head,path)!=(REPO/path).read_bytes():fail(f'worktree catalog differs from committed HEAD: {l}')
  before=show(pre['liveHead'],path)
  if sha(before)!=pre['beforeCatalogFileSha256'][l]:fail(f'preflight before-file hash mismatch: {l}')
  app_raw=show(application_commit,path);head_raw=show(head,path)
  if app_raw!=head_raw:fail(f'catalog changed after application commit: {l}')
  if sha(app_raw)!=app['files'].get(path,{}).get('afterFileSha256') and any(r['locale']==l for r in new):fail(f'application output file hash mismatch: {l}')
  after_hash[path]=sha(app_raw)
  changed={k for k in basecat[l] if basecat[l][k]!=current[l][k]}
  expected={r['catalogKey'] for r in applied if r['locale']==l}
  if changed!=expected:fail(f'changed-cell ledger mismatch {l}: actual {len(changed)}, expected {len(expected)}')
  changed_by[l]=len(changed)
 # All correction dispositions in the 21 manual windows must be applied or explicitly held.
 manual={};source_ids=set();verdicts=collections.Counter();formal_ids=set()
 for w in range(1,22):
  ins=rows(MANUAL/f'window{w}'/'review-input.jsonl');ds=rows(MANUAL/f'window{w}'/'review-decisions.jsonl')
  if len(ins)!=300 or len(ds)!=300:fail(f'window {w} row count mismatch')
  dm={d['id']:d for d in ds}
  if len(dm)!=300 or set(dm)!={r['id'] for r in ins}:fail(f'window {w} input/decision join mismatch')
  for r in ins:
   ident=r['id'];d=dm[ident]
   if ident in manual:fail(f'manual overlap: {ident}')
   manual[ident]=d;source_ids.add(r['sourceId']);verdicts[d['verdict']]+=1
   locale,key=r['locale'],r['catalogKey']
   if basecat[locale].get(key)!=r['target'] or sha(r['target'])!=r['targetSha256']:fail(f'frozen target mismatch: {ident}')
   if d['verdict']=='correct':
    if ident in new_by:
     if new_by[ident]['currentTarget']!=r['target'] or new_by[ident]['proposedTarget']!=d['target']:fail(f'new application does not match decision: {ident}')
    elif ident in prev_by:
     if prev_by[ident]['currentTarget']!=r['target'] or prev_by[ident]['proposedTarget']!=d['target']:fail(f'window18-19 application does not match decision: {ident}')
    elif ident in old_by:
     if old_by[ident].get('currentTarget')!=r['target'] or old_by[ident].get('proposedTarget')!=d['target']:fail(f'initial application does not match decision: {ident}')
    elif ident not in held_by:fail(f'unreconciled correction decision: {ident}')
   expected=(new_by[ident]['proposedTarget'] if ident in new_by else prev_by[ident]['proposedTarget'] if ident in prev_by else old_by[ident]['proposedTarget'] if ident in old_by else r['target'])
   if current[locale].get(key)!=expected:fail(f'final target does not match disposition: {ident}')
 if len(manual)!=6300 or len(source_ids)!=525:fail('manual totals mismatch')
 if verdicts!=collections.Counter({'keep':5217,'correct':875,'uncertain':208}):fail(f'manual decision counts mismatch: {verdicts}')
 if set(old_by)|set(prev_by)|set(new_by)|set(held_by)!={i for i,d in manual.items() if d['verdict']=='correct'}:fail('applied and held ledgers do not cover correction dispositions')
 # Formal accumulator and source/workflow boundary.
 sys.path.insert(0,str(BASE/'translation-tools'))
 import strict_populated_semantic_review_runner_core as core
 bundle_path=BASE/'slskdn-populated-review-4c2b-20261101'/'bundle';results_path=BASE/'semantic-review-results/slskdn-4c2b2e47-v1-912fadf3fce5'
 bm=json.loads((bundle_path/'manifest.json').read_text(encoding='utf-8'))
 bundle=core.load_bundle(bundle_path,sha((bundle_path/'manifest.json').read_bytes()),sha((bundle_path/'batches.json').read_bytes()),bm['headCommit'],bm['tree'],'snapetech-org/slskdN','slskdn',BASE/'slskdn-populated-review-4c2b-20261101'/'snapshot-repo')
 fs=core.scan_results(bundle,results_path)
 if fs['invalid'] or len(fs['valid'])!=150 or len(fs['missing'])!=1951:fail('formal accumulator changed/invalid')
 formal={d['id'] for x in fs['valid'].values() for d in x['decisions']}
 if len(formal)!=4800 or formal & set(manual):fail('formal/manual overlap or count mismatch')
 since=set(git('diff','--name-only',pre['liveHead'],head).splitlines())
 if any(p.startswith('.github/workflows/') for p in since):fail('workflow path changed')
 if any(p.startswith('src/') and '/locales/' not in p for p in since):fail('non-catalog source path changed')
 per_locale={l:{v:sum(1 for d in manual.values() if d['id'].startswith(l+':') and d['verdict']==v) for v in ['keep','correct','uncertain']} for l in LOCALES}
 summary={'result':'PASS','applicationBaseHead':pre['liveHead'],'applicationBaseTree':pre['liveTree'],'applicationCommit':application_commit,'applicationTree':application_tree,'currentHead':head,'currentTree':tree,'catalogCensus':{'locales':12,'keysPerLocale':6169,'totalValues':74028,'changedCellsSinceFrozenBaseline':869,'changedCellsByLocale':changed_by,'catalogFileSha256':after_hash},'application':{'initialAppliedCells':736,'windows18_19AppliedCells':82,'newAppliedCells':51,'totalAppliedCells':869,'appliedSourceKeys':211,'heldNoContext':6,'newPerLocaleCellCounts':pre['newPerLocaleCellCounts']},'manualReconciliation':{'windows':21,'keys':525,'cells':6300,'verdicts':dict(verdicts),'formalOverlap':0,'manualOverlap':0,'unreconciledCorrections':0,'perLocale':per_locale},'formalAccumulator':{'validJobs':150,'missingJobs':1951,'invalidJobs':0,'cells':4800},'workflowChanges':0,'nonCatalogSourceChanges':0,'changedPathsInApplicationCommit':sorted(paths)}
 out=json.dumps(summary,ensure_ascii=False,indent=2)+'\n'
 (ROOT/'verification.json').write_text(out,encoding='utf-8')
 print(out,end='')
if __name__=='__main__':main()
