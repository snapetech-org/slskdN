#!/usr/bin/env python3
"""Verify the exact-hash correction batch from manual review windows 18–19."""
import collections, hashlib, json, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
BUNDLE = Path(__file__).resolve().parent
MANUAL = ROOT / 'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01'
OLD_APP = ROOT / 'docs/pr-evidence/pr409-catalog-correction-application-2026-11-01'
BASELINE = '4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
EXPECTED_TOTALS = {'ar':93,'de':44,'es':66,'fr':66,'hi':72,'id':78,'ja':43,'ko':57,'pt-BR':57,'vi':86,'zh-Hans':79,'zh-Hant':77}
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_text(s): return sha_bytes(s.encode('utf-8'))
def git(*a): return subprocess.check_output(['git','-C',str(ROOT),*a],text=True).strip()
def show(commit,path): return subprocess.check_output(['git','-C',str(ROOT),'show',f'{commit}:{path}'])
def parse(raw,label):
 def pairs(items):
  d={}
  for k,v in items:
   if k in d: raise ValueError(f'duplicate JSON key {k!r} in {label}')
   d[k]=v
  return d
 return json.loads(raw.decode('utf-8'),object_pairs_hook=pairs)
def jl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def fail(s): raise SystemExit('FAIL: '+s)

m=json.loads((BUNDLE/'manifest.json').read_text(encoding='utf-8'))
pf=json.loads((BUNDLE/'preflight.json').read_text(encoding='utf-8'))
appres=json.loads((BUNDLE/'application-result.json').read_text(encoding='utf-8'))
new=jl(BUNDLE/'applied-corrections.jsonl')
old=jl(OLD_APP/'applied-corrections.jsonl')
held=jl(OLD_APP/'held-no-context.jsonl')
if len(new)!=82 or len(old)!=736 or len(held)!=6: fail('applied/held row count mismatch')
if sha_bytes((BUNDLE/'applied-corrections.jsonl').read_bytes())!=m['newApplicationRowsSha256']: fail('new correction ledger checksum mismatch')
if sha_bytes((BUNDLE/'preflight.json').read_bytes())!=m['preflightSha256']: fail('preflight checksum mismatch')
if sha_bytes((BUNDLE/'application-result.json').read_bytes())!=m['applicationResultSha256']: fail('application-result checksum mismatch')
if pf['liveHead']!=m['applicationBaseHead'] or pf['liveTree']!=m['applicationBaseTree']: fail('application preflight head/tree mismatch')
if pf['newApplicationRowsSha256']!=m['newApplicationRowsSha256']: fail('preflight/application row hash mismatch')
if pf['oldCorrectionLedgerSha256']!=m['priorApplication']['appliedLedgerSha256']: fail('preflight prior ledger pin mismatch')
if sha_bytes((OLD_APP/'applied-corrections.jsonl').read_bytes())!=m['priorApplication']['appliedLedgerSha256']: fail('prior applied ledger checksum mismatch')
if sha_bytes((OLD_APP/'held-no-context.jsonl').read_bytes())!=m['priorApplication']['heldLedgerSha256']: fail('prior held ledger checksum mismatch')
state=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,headRefOid'],text=True))
head=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}')
if state['state']!='OPEN' or not state['isDraft'] or state['headRefOid']!=head: fail(f'PR state/head mismatch: {state}; local {head}')
if git('rev-parse',m['applicationBaseHead']+':src')!=m['sourceSubtreeTree']: fail('preflight source subtree pin mismatch')
if git('rev-parse',m['applicationCommit']+'^')!=m['applicationBaseHead']: fail('application commit parent mismatch')
if git('rev-parse',m['applicationCommit']+'^{tree}')!=m['applicationTree']: fail('application commit tree mismatch')
if subprocess.run(['git','-C',str(ROOT),'merge-base','--is-ancestor',m['applicationCommit'],'HEAD']).returncode: fail('application commit is not an ancestor of current head')
expected_paths={f'src/web/public/locales/{l}.json' for l in LOCALES}|{'docs/CHANGELOG.md'}
commit_paths=set(git('diff-tree','--no-commit-id','--name-only','-r',m['applicationCommit']).splitlines())
if commit_paths!=expected_paths: fail(f'application commit changed unexpected paths: {sorted(commit_paths^expected_paths)}')
old_by={r['id']:r for r in old};new_by={r['id']:r for r in new};held_by={r['id']:r for r in held}
if len(old_by)!=736 or len(new_by)!=82 or len(held_by)!=6: fail('duplicate applied/held IDs')
if set(old_by)&set(new_by) or set(old_by)&set(held_by) or set(new_by)&set(held_by): fail('applied/held overlap')
if len({r['sourceId'] for r in old+new})!=195: fail('applied source-key count mismatch')
if collections.Counter(r['locale'] for r in old+new)!=collections.Counter(EXPECTED_TOTALS): fail('cumulative per-locale correction counts mismatch')

# Check exact source and proposed-target hashes, placeholders, and source callsites.
for r in old+new:
 target=r.get('proposedTarget',r.get('appliedTarget'))
 target_sha=r.get('proposedTargetSha256',r.get('appliedTargetSha256'))
 if sha_text(r['source'])!=r['sourceSha256'] or not target or sha_text(target)!=target_sha: fail(f'source/target hash mismatch: {r["id"]}')
 if collections.Counter(re.findall(r'{[^{}]+}',r['source']))!=collections.Counter(re.findall(r'{[^{}]+}',target)): fail(f'placeholder mismatch: {r["id"]}')
 for c in r['sourceCallsites']:
  raw=(ROOT/c['path']).read_bytes()
  if sha_bytes(raw)!=c['fileSha256']: fail(f'callsite file hash mismatch: {c["path"]}')
  line=raw.decode('utf-8').splitlines()[c['line']-1].strip()
  if line!=c['lineText'] or sha_text(line)!=c['lineTextSha256']: fail(f'callsite line mismatch: {c["path"]}:{c["line"]}')

# Read the frozen catalog baseline and exact current catalogs from Git objects.
basecat={};current={}
for l in LOCALES:
 path=f'src/web/public/locales/{l}.json'
 basecat[l]=parse(show(BASELINE,path),f'{BASELINE}:{path}')
 before_raw=show(m['applicationBaseHead'],path)
 if sha_bytes(before_raw)!=pf['beforeCatalogFileSha256'][l]: fail(f'preflight before-file hash mismatch: {l}')
 result_file=appres['files'][path]
 if result_file['beforeFileSha256']!=pf['beforeCatalogFileSha256'][l]: fail(f'application result before-file hash mismatch: {l}')
 app_raw=show(m['applicationCommit'],path);head_raw=show('HEAD',path)
 if sha_bytes(app_raw)!=m['afterCatalogFileSha256'][path] or result_file['afterFileSha256']!=sha_bytes(app_raw): fail(f'application catalog hash mismatch: {l}')
 if app_raw!=head_raw: fail(f'catalog changed after application commit: {l}')
 current[l]=parse(head_raw,f'HEAD:{path}')
 if len(basecat[l])!=6169 or len(current[l])!=6169 or set(basecat[l])!=set(current[l]): fail(f'catalog census/key-set mismatch: {l}')
 if any(not isinstance(v,str) or not v for v in current[l].values()): fail(f'empty/non-string catalog value: {l}')
 if (ROOT/path).read_bytes()!=head_raw: fail(f'worktree catalog differs from HEAD: {l}')

# Reconcile every one of the 5,700 manual decisions against the final catalogs.
manual={};source_ids=set();verdicts=collections.Counter();input_by_id={}
for w in range(1,20):
 folder=MANUAL/f'window{w}';inputs=jl(folder/'review-input.jsonl');decisions=jl(folder/'review-decisions.jsonl')
 if len(inputs)!=300 or len(decisions)!=300: fail(f'window {w} row count mismatch')
 dm={d['id']:d for d in decisions}
 if len(dm)!=300 or set(dm)!={r['id'] for r in inputs}: fail(f'window {w} input/decision join mismatch')
 for r in inputs:
  ident=r['id']
  if ident in manual: fail(f'manual evidence overlap: {ident}')
  manual[ident]=dm[ident];input_by_id[ident]=r;source_ids.add(r['sourceId'])
  verdicts[dm[ident]['verdict']]+=1
  locale,key=r['locale'],r['catalogKey']
  if basecat[locale].get(key)!=r['target'] or sha_text(r['target'])!=r['targetSha256']: fail(f'frozen target mismatch: {ident}')
  if dm[ident]['verdict']=='correct' and ident in new_by:
   if new_by[ident]['currentTarget']!=r['target'] or new_by[ident]['proposedTarget']!=dm[ident]['target']: fail(f'new application does not match review decision: {ident}')
   for lit in r.get('protectedLiterals',[]):
    if dm[ident]['target'].count(lit)!=r['source'].count(lit): fail(f'protected literal mismatch {lit!r}: {ident}')
  if dm[ident]['verdict']=='correct' and ident in old_by:
   if old_by[ident].get('currentTarget')!=r['target'] or old_by[ident].get('proposedTarget')!=dm[ident]['target']: fail(f'old application does not match review decision: {ident}')
  if dm[ident]['verdict']=='correct' and ident not in old_by|new_by|held_by: fail(f'unreconciled correction decision: {ident}')
  expected=(new_by[ident]['proposedTarget'] if ident in new_by else old_by[ident]['proposedTarget'] if ident in old_by else r['target'])
  if current[locale].get(key)!=expected: fail(f'final catalog does not match disposition: {ident}')
if len(manual)!=5700 or len(source_ids)!=475: fail('manual review coverage mismatch')
if verdicts!=collections.Counter({'keep':4704,'correct':824,'uncertain':172}): fail(f'manual verdict totals mismatch: {verdicts}')
if set(new_by)|set(old_by)|set(held_by) != {i for i,d in manual.items() if d['verdict']=='correct'}: fail('correction ledger does not reconcile all correction decisions')

# Exactly 818 cells changed since the frozen catalog baseline.
expected_cells={(r['locale'],r['catalogKey']) for r in old+new}
if len(expected_cells)!=818: fail('duplicate correction cell')
changed_by={}
for l in LOCALES:
 changed={k for k in basecat[l] if basecat[l][k]!=current[l][k]}
 expected={key for locale,key in expected_cells if locale==l}
 if changed!=expected: fail(f'changed-cell ledger mismatch for {l}: {len(changed)} vs {len(expected)}')
 changed_by[l]=len(changed)

# Recompute the formal accumulator and overlap from its frozen inputs.
base=Path('/mnt/disks/scratch/task-worktrees/localization-20261030')
sys.path.insert(0,str(base/'translation-tools'))
import strict_populated_semantic_review_runner_core as core
bundle_path=base/'slskdn-populated-review-4c2b-20261101'/'bundle';results_path=base/'semantic-review-results/slskdn-4c2b2e47-v1-912fadf3fce5'
bm=json.loads((bundle_path/'manifest.json').read_text(encoding='utf-8'))
bh=sha_bytes((bundle_path/'manifest.json').read_bytes());batches=sha_bytes((bundle_path/'batches.json').read_bytes())
bundle=core.load_bundle(bundle_path,bh,batches,bm['headCommit'],bm['tree'],'snapetech-org/slskdN','slskdn',base/'slskdn-populated-review-4c2b-20261101'/'snapshot-repo')
formal_state=core.scan_results(bundle,results_path)
if formal_state['invalid'] or len(formal_state['valid'])!=150 or len(formal_state['missing'])!=1951: fail('formal accumulator changed or contains invalid jobs')
formal={d['id'] for x in formal_state['valid'].values() for d in x['decisions']}
if len(formal)!=4800 or set(manual)&formal: fail('formal/manual overlap or formal cell count mismatch')
post_base=set(git('diff','--name-only',m['applicationBaseHead'],'HEAD').splitlines())
if any(p.startswith('.github/workflows/') for p in post_base) or any(p.startswith('src/') and '/locales/' not in p for p in post_base): fail('workflow or non-catalog source changes after application preflight')
summary={'result':'PASS','head':head,'tree':tree,'applicationCommit':m['applicationCommit'],
 'catalogCensus':{'locales':12,'keysPerLocale':6169,'totalValues':74028,'changedCellsSinceFrozenBaseline':818,'changedCellsByLocale':changed_by},
 'application':{'priorAppliedCells':736,'newAppliedCells':82,'totalAppliedCells':818,'appliedSourceKeys':195,'heldNoContext':6},
 'manualReconciliation':{'windows':19,'keys':475,'cells':5700,'verdicts':dict(verdicts),'formalOverlap':0,'manualOverlap':0,'unreconciledCells':0},
 'formalAccumulator':{'validJobs':150,'missingJobs':1951,'invalidJobs':0,'cells':4800},'workflowChanges':0,'nonCatalogSourceChanges':0}
print(json.dumps(summary,ensure_ascii=False,indent=2))
