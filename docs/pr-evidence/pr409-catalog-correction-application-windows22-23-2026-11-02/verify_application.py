#!/usr/bin/env python3
import collections,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
BASE=REPO.parent
MANUAL=REPO/'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01'
OLD_APP=REPO/'docs/pr-evidence/pr409-catalog-correction-application-2026-11-01'
PREV_APP=REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows18-19-2026-11-02'
LATEST_APP=REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows20-21-2026-11-02'
BASELINE='4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
EXPECTED_TOTALS={'ar':104,'de':47,'es':77,'fr':75,'hi':80,'id':85,'ja':51,'ko':66,'pt-BR':68,'vi':95,'zh-Hans':94,'zh-Hant':92}
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
 crosspre=json.loads((ROOT/'cross-review-preflight.json').read_text(encoding='utf-8'))
 app=json.loads((ROOT/'apply-result.json').read_text(encoding='utf-8'))
 crossapp=json.loads((ROOT/'cross-review-apply-result.json').read_text(encoding='utf-8'))
 new=rows(ROOT/'applied-corrections.jsonl');cross=rows(ROOT/'cross-review-applied-corrections.jsonl')
 old=rows(OLD_APP/'applied-corrections.jsonl');prev=rows(PREV_APP/'applied-corrections.jsonl');latest=rows(LATEST_APP/'applied-corrections.jsonl');held=rows(OLD_APP/'held-no-context.jsonl')
 parent_ledger=ROOT/'independent-cross-review-ledger.jsonl';parent_summary=ROOT/'independent-cross-review-summary.json'
 if sha(parent_ledger.read_bytes())!='4767ca0981a52863f848185554857afbeb7479602b9a339c3da730e31c3911f5':fail('parent cross-review ledger checksum mismatch')
 if sha((ROOT/'cross-review-application-rows.jsonl').read_bytes())!=crosspre['crossReviewApplicationRowsSha256']:fail('cross-review application row checksum mismatch')
 if sha((ROOT/'applied-corrections.jsonl').read_bytes())!=pre['newApplicationRowsSha256']:fail('manual application row checksum mismatch')
 if len(new)!=53 or len(cross)!=12 or len(old)!=736 or len(prev)!=82 or len(latest)!=51 or len(held)!=6:fail('application/held row count mismatch')
 manual_cross=rows(ROOT/'independent-cross-reviews/windows22-23/review.jsonl');manual_summary=json.loads((ROOT/'independent-cross-reviews/windows22-23/review-summary.json').read_text(encoding='utf-8'))
 manual_review_spec=m['independentCrossReviews']['windows22_23']
 if sha((ROOT/manual_review_spec['evidencePath']).read_bytes())!=manual_review_spec['evidenceSha256'] or sha((ROOT/manual_review_spec['summaryPath']).read_bytes())!=manual_review_spec['summarySha256']:fail('windows 22-23 independent review checksum mismatch')
 if len(manual_cross)!=53 or manual_summary.get('rows')!=53 or manual_summary.get('acceptedAsProposed')!=53 or manual_summary.get('refined')!=0 or manual_summary.get('holds')!=0 or manual_summary.get('applicationCommit')!=m['applicationCommit'] or manual_summary.get('currentPrHead')!=m['applicationCommit'] or manual_summary.get('currentPrTree')!=m['applicationTree'] or manual_summary.get('semanticConfidence')!='high' or manual_summary.get('localeQualityConfidence')!='moderate' or manual_summary.get('nativeSpeakerReview')!='outstanding':fail('windows 22-23 independent review summary mismatch')
 for p,c in zip(sorted(manual_cross,key=lambda r:r['id']),sorted(new,key=lambda r:r['id'])):
  if p['id']!=c['id'] or p['crossReviewDisposition']!='accepted-as-proposed' or p['crossReviewedTarget']!=c['proposedTarget'] or p['crossReviewedTargetHash']!=c['proposedTargetSha256'] or p['expectedCurrentTargetHash']!=c['currentTargetSha256'] or p['source']!=c['source'] or p['sourceHash']!=c['sourceSha256']:fail(f'windows 22-23 independent/application ledger mismatch {p["id"]}')
 application_commit=m['applicationCommit'];application_tree=m['applicationTree']
 if git('rev-parse',application_commit+'^')!=pre['liveHead'] or git('rev-parse',application_commit+'^1^{tree}')!=pre['liveTree']:fail('application commit parent/base mismatch')
 if git('rev-parse',application_commit+'^{tree}')!=application_tree:fail('application tree mismatch')
 if subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',application_commit,'HEAD']).returncode:fail('application commit is not an ancestor of current head')
 head=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}')
 state=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,headRefOid'],text=True))
 remote=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin','refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'],text=True).split()[0]
 if state!={'state':'OPEN','isDraft':True,'headRefOid':head} or remote!=head:fail(f'PR/remote not at current head: {state}, remote={remote}, head={head}')
 paths=set(git('diff-tree','--no-commit-id','--name-only','-r',application_commit).splitlines())
 expected_paths={f'src/web/public/locales/{l}.json' for l in LOCALES}|{'docs/CHANGELOG.md'}
 if paths!=expected_paths:fail(f'application commit paths differ: {sorted(paths^expected_paths)}')
 status=git('status','--porcelain').splitlines()
 allowed=['docs/localization/pr409-populated-catalog-semantic-review-2026-11-01.md','docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02/']
 for item in status:
  path=item[2:].lstrip()
  if not any(path==a or path.startswith(a) for a in allowed):fail(f'unexpected worktree change: {item}')
 if git('rev-parse',BASELINE+'^{tree}')!='0eb84397dc2b4be4afd730f6818203bd5910cf15':fail('frozen catalog baseline tree changed')
 if git('rev-parse',pre['liveHead']+':src')!=pre['sourceSubtreeTree']:fail('application-base source tree mismatch')
 if git('rev-parse',pre['liveHead'])!=crosspre['liveHead'] or pre['liveHead']!=m['applicationBaseHead']:fail('manual/cross-review base head mismatch')
 old_by={r['id']:r for r in old};prev_by={r['id']:r for r in prev};latest_by={r['id']:r for r in latest};new_by={r['id']:r for r in new};cross_by={r['id']:r for r in cross};held_by={r['id']:r for r in held}
 if any(len(d)!=n for d,n in [(old_by,736),(prev_by,82),(latest_by,51),(new_by,53),(cross_by,12),(held_by,6)]):fail('duplicate application/held IDs')
 allgroups=[set(old_by),set(prev_by),set(latest_by),set(new_by),set(cross_by),set(held_by)]
 if any(allgroups[i]&allgroups[j] for i in range(len(allgroups)) for j in range(i+1,len(allgroups))):fail('application/cross-review/held ledger overlap')
 applied=old+prev+latest+new+cross;applied_by={r['id']:r for r in applied}
 if len(applied_by)!=934:fail('cumulative applied ID count mismatch')
 if len({r['sourceId'] for r in applied})!=228:fail('cumulative applied source-key count mismatch')
 if collections.Counter(r['locale'] for r in applied)!=collections.Counter(EXPECTED_TOTALS):fail('cumulative per-locale target counts mismatch')
 # Validate source, target, placeholder, and exact caller hashes for each applied cell.
 for r in applied:
  target=r.get('proposedTarget',r.get('crossReviewedTarget',r.get('appliedTarget')))
  target_sha=r.get('proposedTargetSha256',r.get('crossReviewedTargetHash',r.get('appliedTargetSha256')))
  source_sha=r.get('sourceSha256',r.get('sourceHash'))
  if sha(r['source'])!=source_sha or not target or sha(target)!=target_sha:fail(f'source/target hash mismatch: {r["id"]}')
  if collections.Counter(re.findall(r'{[^{}]+}',r['source']))!=collections.Counter(re.findall(r'{[^{}]+}',target)):fail(f'placeholder mismatch: {r["id"]}')
  for c in r.get('sourceCallsites',r.get('sourceContextCallsites',[])):
   raw=(REPO/c['path']).read_bytes()
   if sha(raw)!=c['fileSha256']:fail(f'callsite file hash mismatch: {c["path"]}')
   line=raw.decode('utf-8').splitlines()[c['line']-1].strip()
   if line!=c['lineText'] or sha(line)!=c['lineTextSha256']:fail(f'callsite line mismatch: {c["path"]}:{c["line"]}')
 # Manual evidence: keep/correct/uncertain counts are retained; cross-review resolves 12 of the uncertain cells.
 manual={};source_ids=set();verdicts=collections.Counter();manual_rows={}
 for w in range(1,24):
  ins=rows(MANUAL/f'window{w}'/'review-input.jsonl');ds=rows(MANUAL/f'window{w}'/'review-decisions.jsonl');dm={d['id']:d for d in ds}
  if len(ins)!=300 or len(ds)!=300 or set(dm)!={r['id'] for r in ins}:fail(f'window {w} row count/join mismatch')
  for r in ins:
   ident=r['id'];d=dm[ident]
   if ident in manual:fail(f'manual overlap {ident}')
   manual[ident]=d;manual_rows[ident]=r;source_ids.add(r['sourceId']);verdicts[d['verdict']]+=1
   if r['targetSha256']!=sha(r['target']):fail(f'manual target hash mismatch {ident}')
   if d['verdict']=='correct':
    appliedrow=applied_by.get(ident)
    if appliedrow:
     if appliedrow['currentTarget']!=r['target'] or appliedrow.get('proposedTarget')!=d['target']:fail(f'correct application mismatch {ident}')
    elif ident in held_by:
     held_target=held_by[ident].get('currentTarget',held_by[ident].get('target'))
     if held_target is not None and held_target!=r['target']:fail(f'held current target mismatch {ident}')
    else:fail(f'correct decision neither applied nor held: {ident}')
   elif d['verdict']=='keep':
    if ident in applied_by or ident in held_by:fail(f'keep value changed {ident}')
   elif d['verdict']=='uncertain':
    if ident in cross_by:
     cr=cross_by[ident]
     if cr['currentTarget']!=r['target'] or not cr['proposedTarget'] or cr['crossReviewDisposition'] not in ('accepted-as-proposed','refined-and-accepted'):fail(f'cross-review resolution mismatch {ident}')
    elif ident in applied_by or ident in held_by:fail(f'unreviewed uncertain value changed {ident}')
   else:fail(f'unknown manual verdict {d["verdict"]}')
 if len(manual)!=6900 or len(source_ids)!=575:fail('manual coverage totals mismatch')
 if verdicts!=collections.Counter({'keep':5752,'correct':928,'uncertain':220}):fail(f'manual verdict counts mismatch: {verdicts}')
 correct_ids={i for i,d in manual.items() if d['verdict']=='correct'}
 cross_ids=set(cross_by)
 uncertain_ids={i for i,d in manual.items() if d['verdict']=='uncertain'}
 if not cross_ids<=uncertain_ids or len(cross_ids)!=12:fail('independent cross-review does not resolve the expected 12 uncertain cells')
 if set(held_by)|set(applied_by)!=correct_ids|cross_ids:fail('applied/held ledgers do not cover manual correct plus cross-reviewed uncertain dispositions')
 if len(uncertain_ids-cross_ids)!=208:fail('remaining uncertain count mismatch')
 # The parent cross-review ledger and summary must match the separate application ledger.
 parent_rows=rows(ROOT/'independent-cross-review-ledger.jsonl');ps=json.loads(parent_summary.read_text(encoding='utf-8'))
 if len(parent_rows)!=12 or ps['rows']!=12 or ps['holds']!=0 or ps['semanticConfidence']!='high' or ps['localeQualityConfidence']!='moderate' or ps['nativeSpeakerReview']!='outstanding':fail('independent cross-review summary mismatch')
 if sha(parent_summary.read_bytes())!=m['independentCrossReview']['evidenceSummarySha256']:fail('cross-review summary hash mismatch')
 for p,c in zip(parent_rows,cross):
  if p['id']!=c['id'] or p['crossReviewedTarget']!=c['proposedTarget'] or p['crossReviewedTargetHash']!=c['proposedTargetSha256'] or p['expectedCurrentTargetHash']!=c['currentTargetSha256']:fail(f'parent/cross applied ledger mismatch {p["id"]}')
 # Exact catalog census against frozen baseline and both separate new ledgers.
 basecat={};current={};after_hash={};changed_by={}
 for l in LOCALES:
  rel=f'src/web/public/locales/{l}.json';basecat[l]=parse(show(BASELINE,rel),f'{BASELINE}:{rel}');current[l]=parse(show(head,rel),f'{head}:{rel}')
  if len(basecat[l])!=6169 or len(current[l])!=6169 or set(basecat[l])!=set(current[l]):fail(f'catalog census/key-set mismatch {l}')
  if any(not isinstance(v,str) or not v for v in current[l].values()):fail(f'empty/nonstring value {l}')
  if show(head,rel)!=(REPO/rel).read_bytes():fail(f'worktree catalog differs from committed head {l}')
  raw=show(application_commit,rel)
  if crossapp.get('files',{}).get(rel,{}).get('beforeWorktreeFileSha256')!=app.get('files',{}).get(rel,{}).get('afterFileSha256'):fail(f'manual/cross-review intermediate file hash mismatch {rel}')
  if sha(raw)!=crossapp.get('files',{}).get(rel,{}).get('afterFileSha256'):fail(f'cross-review after-file hash mismatch {rel}')
  after_hash[rel]=sha(raw)
  changed={k for k in basecat[l] if basecat[l][k]!=current[l][k]};expected={r['catalogKey'] for r in applied if r['locale']==l}
  if changed!=expected:fail(f'changed-cell ledger mismatch {l}: actual {len(changed)}, expected {len(expected)}')
  for r in applied:
   if r['locale']==l and current[l].get(r['catalogKey'])!=r.get('proposedTarget',r.get('crossReviewedTarget')):fail(f'final value mismatch {r["id"]}')
  changed_by[l]=len(changed)
 if sum(changed_by.values())!=934:fail('catalog diff from baseline is not exactly 934 cells')
 # Formal accumulator and source/workflow boundary.
 sys.path.insert(0,str(BASE/'translation-tools'))
 import strict_populated_semantic_review_runner_core as core
 bundle_path=BASE/'slskdn-populated-review-4c2b-20261101'/'bundle';results_path=BASE/'semantic-review-results/slskdn-4c2b2e47-v1-912fadf3fce5'
 bm=json.loads((bundle_path/'manifest.json').read_text(encoding='utf-8'))
 bundle=core.load_bundle(bundle_path,sha((bundle_path/'manifest.json').read_bytes()),sha((bundle_path/'batches.json').read_bytes()),bm['headCommit'],bm['tree'],'snapetech-org/slskdN','slskdn',BASE/'slskdn-populated-review-4c2b-20261101'/'snapshot-repo')
 fs=core.scan_results(bundle,results_path)
 if fs['invalid'] or len(fs['valid'])!=150 or len(fs['missing'])!=1951:fail('formal accumulator changed or has invalid rows')
 formal={d['id'] for x in fs['valid'].values() for d in x['decisions']}
 if len(formal)!=4800 or formal&set(manual):fail('formal/manual overlap or count mismatch')
 since=set(git('diff','--name-only',pre['liveHead'],application_commit).splitlines())
 if any(p.startswith('.github/workflows/') for p in since):fail('workflow path changed')
 if any(p.startswith('src/') and '/locales/' not in p for p in since):fail('non-catalog source path changed')
 per_locale={l:{v:sum(d['id'].startswith(l+':') and d['verdict']==v for d in manual.values()) for v in ('keep','correct','uncertain')} for l in LOCALES}
 summary={'result':'PASS','applicationBaseHead':pre['liveHead'],'applicationBaseTree':pre['liveTree'],'applicationCommit':application_commit,'applicationTree':application_tree,'currentHead':head,'currentTree':tree,'catalogCensus':{'locales':12,'keysPerLocale':6169,'totalValues':74028,'changedCellsSinceFrozenBaseline':934,'changedCellsByLocale':changed_by,'catalogFileSha256':after_hash},'application':{'previousAppliedCells':869,'newManualWindowCells':53,'newIndependentCrossReviewCells':12,'newAppliedCells':65,'totalAppliedCells':934,'appliedSourceKeys':228,'heldNoContext':6,'newPerLocaleCellCounts':pre['newPerLocaleCellCounts']},'independentManualCorrectionReview':{'rows':53,'acceptedAsProposed':53,'refinements':0,'holds':0,'semanticConfidence':'high','localeQualityConfidence':'moderate','nativeSpeakerReview':'outstanding','sourceLedgerSha256':manual_review_spec['evidenceSha256']},'independentCrossReview':{'rows':12,'sourceId':'src_f41792666b3f8d5b','acceptedAsProposed':10,'refinedAndAccepted':2,'holds':0,'resolvedUncertainCells':12,'remainingUncertainCells':208,'semanticConfidence':'high','localeQualityConfidence':'moderate','nativeSpeakerReview':'outstanding','sourceLedgerSha256':m['independentCrossReview']['evidenceSha256']},'manualReconciliation':{'windows':23,'keys':575,'cells':6900,'verdicts':dict(verdicts),'correctPlusCrossReviewDispositions':940,'appliedAndHeld':{'applied':934,'held':6},'uncertainBeforeCrossReview':220,'independentlyResolved':12,'uncertainRemaining':208,'formalOverlap':0,'manualOverlap':0,'unreconciledCorrections':0,'perLocale':per_locale},'formalAccumulator':{'validJobs':150,'missingJobs':1951,'invalidJobs':0,'cells':4800},'workflowChanges':0,'nonCatalogSourceChanges':0,'changedPathsInApplicationCommit':sorted(paths)}
 out=json.dumps(summary,ensure_ascii=False,indent=2)+'\n';(ROOT/'verification.json').write_text(out,encoding='utf-8');print(out,end='')
if __name__=='__main__':main()
