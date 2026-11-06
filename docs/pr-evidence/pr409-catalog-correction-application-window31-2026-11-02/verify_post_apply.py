#!/usr/bin/env python3
import collections,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=Path('/mnt/disks/scratch/task-worktrees/localization-20261030')
REPO=BASE/'slskdn-pr409-batch4-docs-20261101'
MANUAL=REPO/'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01'
APP0=REPO/'docs/pr-evidence/pr409-catalog-correction-application-2026-11-01'
APP18=REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows18-19-2026-11-02'
APP20=REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows20-21-2026-11-02'
APP22=REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02'
APP_WINDOWS={n:REPO/f'docs/pr-evidence/pr409-catalog-correction-application-window{n}-2026-11-02' for n in range(24,31)}
ROOT_PACKET=BASE/'slskdn-root-crossreview-W31-fbafaae2-20261102'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
HEAD='fbafaae2e05af8ce51a263c7be2a92a8728ceb94'
BASELINE='4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb'
PLAN_SHA='70067d1a6a13349d1d72db7227d3e79fae1757cc97e50e37330456d3121a64ca'
CANDIDATE_SHA='320f88df56d7f9f1f1ec2fe20fab467235ab59471fe7812b63f8ba8979de5bba'
ROOT_SHA='4e0809fcad3782ab73027cb22f2dea97ce18a3c891e91a7ad872a1ee74d67005'
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(*a): return subprocess.check_output(['git','-C',str(REPO),*a],text=True).strip()
def show(commit,path): return subprocess.check_output(['git','-C',str(REPO),'show',f'{commit}:{path}'])
def json_unique(raw,label):
 def hook(items):
  d={}
  for k,v in items:
   if k in d: raise ValueError(f'duplicate JSON key {k!r}: {label}')
   d[k]=v
  return d
 return json.loads(raw.decode('utf-8'),object_pairs_hook=hook)
def fail(s): raise SystemExit('FAIL: '+s)
manifest=json.loads((ROOT/'manifest.json').read_text()); pre=json.loads((ROOT/'application-preflight-window31.json').read_text()); audit=json.loads((ROOT/'apply-audit-window31.json').read_text())
plan=rows(ROOT/'root-apply-plan-window31.jsonl'); ledger=rows(ROOT/'applied-corrections-window31.jsonl'); inputs=rows(ROOT/'review-input.jsonl'); decisions=rows(ROOT/'review-decisions.jsonl')
if (git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}'),git('rev-parse','HEAD:src'))!=(HEAD,'ee4d11c5cf5b3c1053fcbdafff69dee9d2cb09d9','150c9fc80ce9a8f491926aa25f4397a12c8efc73'): fail('base HEAD/tree/source pin changed during apply')
if pre.get('result')!='READY_TO_APPLY' or pre.get('applyPlanSha256')!=PLAN_SHA or sha((ROOT/'root-apply-plan-window31.jsonl').read_bytes())!=PLAN_SHA: fail('apply plan/preflight checksum mismatch')
if sha((ROOT/'crossreview-plan.jsonl').read_bytes())!=CANDIDATE_SHA or sha((ROOT_PACKET/'root-decisions.jsonl').read_bytes())!=ROOT_SHA: fail('cross-review packet checksum mismatch')
if len(plan)!=36 or len(ledger)!=36 or len(inputs)!=274 or len(decisions)!=274: fail('W31 row count mismatch')
plan_by={r['id']:r for r in plan}; ledger_by={r['id']:r for r in ledger}; input_by={r['id']:r for r in inputs}; decision_by={r['id']:r for r in decisions}
if len(plan_by)!=36 or set(plan_by)!=set(ledger_by) or set(input_by)!=set(decision_by): fail('W31 row IDs not unique/exact')
if git('diff','--check')!='': fail('git diff --check reported whitespace errors')
paths=set(git('diff','--name-only','HEAD').splitlines())
expected_paths={r['catalogPath'] for r in plan}|{'docs/CHANGELOG.md'}
if paths!=expected_paths: fail(f'working diff path scope mismatch: {sorted(paths^expected_paths)}')
if git('diff','--name-only','HEAD','--','.github/workflows'): fail('workflow path changed')
if {p for p in paths if p.startswith('src/') and p not in {r['catalogPath'] for r in plan}}: fail('source path changed beyond locale catalogs')
changed_per_locale=collections.Counter()
new_hashes={}; catalogs={}; baseline_catalogs={}
ph=lambda s:collections.Counter(re.findall(r'\{[^{}]+\}',s))
for locale in LOCALES:
 rel=f'src/web/public/locales/{locale}.json'; before=json_unique(show(HEAD,rel),f'{HEAD}:{rel}')
 raw=(REPO/rel).read_bytes(); final=json_unique(raw,f'worktree:{rel}')
 new_hashes[locale]=sha(raw);catalogs[locale]=final;baseline_catalogs[locale]=json_unique(show(BASELINE,rel),f'{BASELINE}:{rel}')
 if len(before)!=6169 or len(final)!=6169 or len(baseline_catalogs[locale])!=6169 or set(before)!=set(final) or set(baseline_catalogs[locale])!=set(final): fail(f'catalog key shape mismatch: {locale}')
 if any(not isinstance(v,str) or not v for v in final.values()): fail(f'empty/non-string value in {locale}')
 expected_changed={r['catalogKey'] for r in plan if r['locale']==locale}
 changed={key for key in before if before[key]!=final[key]}
 if changed!=expected_changed: fail(f'W31 changed-cell set mismatch {locale}: {sorted(changed^expected_changed)}')
 changed_per_locale[locale]=len(changed)
 for key,value in final.items():
  if ph(key)!=ph(value): fail(f'placeholder parity mismatch {locale}:{key}')
 for r in plan:
  if r['locale']==locale:
   if before.get(r['catalogKey'])!=r['currentTarget'] or sha(r['currentTarget'])!=r['currentTargetSha256']: fail(f'base value/hash mismatch {r["id"]}')
   if final.get(r['catalogKey'])!=r['rootTarget'] or sha(r['rootTarget'])!=r['rootTargetSha256']: fail(f'new value/hash mismatch {r["id"]}')
for r in plan:
 if r['id'] not in input_by or r['id'] not in decision_by or r['id'] not in ledger_by: fail(f'W31 join missing {r["id"]}')
 applied=ledger_by[r['id']]
 if applied['oldTarget']!=r['currentTarget'] or applied['oldTargetSha256']!=r['currentTargetSha256'] or applied['newTarget']!=r['rootTarget'] or applied['newTargetSha256']!=r['rootTargetSha256']: fail(f'applied ledger exact target mismatch {r["id"]}')
 for c in r['sourceCallsites']:
  raw=show(HEAD,c['path']);line=raw.decode().splitlines()[c['line']-1].strip()
  if sha(raw)!=c['fileSha256'] or line!=c['lineText'] or sha(line)!=c['lineTextSha256']: fail(f'caller pin mismatch {r["id"]}')
# Cumulative manual-window and correction-ledger reconciliation.
manual_ids=set(); manual_keys=set(); manual_by={}; verdicts=collections.Counter(); per_locale_verdicts=collections.defaultdict(collections.Counter)
for n in range(1,31):
 d=MANUAL/f'window{n}';ins=rows(d/'review-input.jsonl');dec=rows(d/'review-decisions.jsonl');db={r['id']:r for r in dec}
 if len(ins)!=(264 if n==30 else 300) or len(dec)!=len(ins) or len(db)!=len(ins): fail(f'prior W{n} row count mismatch')
 for r in ins:
  ident=r['id'];v=db[ident]
  if ident in manual_ids: fail(f'prior manual overlap {ident}')
  manual_ids.add(ident);manual_keys.add(r['sourceId']);manual_by[ident]=(r,v);verdicts[v['verdict']]+=1;per_locale_verdicts[r['locale']][v['verdict']]+=1
for r in inputs:
 if r['id'] in manual_ids: fail(f'W31 overlap with prior manual cell {r["id"]}')
 manual_ids.add(r['id']);manual_keys.add(r['sourceId']);v=decision_by[r['id']];manual_by[r['id']]=(r,v);verdicts[v['verdict']]+=1;per_locale_verdicts[r['locale']][v['verdict']]+=1
if len(manual_ids)!=9238 or len(manual_keys)!=772: fail('31-window manual coverage mismatch')
if verdicts!=collections.Counter({'keep':7706,'correct':1264,'uncertain':268}): fail(f'cumulative manual verdict totals mismatch {dict(verdicts)}')
# Existing application ledgers in exact committed evidence.
app_paths=[
 APP0/'applied-corrections.jsonl',APP18/'applied-corrections.jsonl',APP20/'applied-corrections.jsonl',
 APP22/'applied-corrections-windows22-23.jsonl',APP22/'applied-corrections-realm-window20.jsonl',
]+[APP_WINDOWS[n]/f'applied-corrections-window{n}.jsonl' for n in range(24,31)]
prior_applied=[]
for p in app_paths: prior_applied+=rows(p)
held=rows(APP0/'held-no-context.jsonl')
applied=prior_applied+ledger
applied_by={r['id']:r for r in applied};held_by={r['id']:r for r in held}
if len(prior_applied)!=1234 or len(ledger)!=36 or len(applied)!=1270 or len(applied_by)!=1270 or len(held_by)!=6: fail('cumulative applied/held row count mismatch')
if len({r['sourceId'] for r in applied})!=290: fail('cumulative applied source-key count mismatch')
if set(applied_by)&set(held_by): fail('applied/held overlap')
realm_ids={r['id'] for r in rows(APP22/'applied-corrections-realm-window20.jsonl')}
manual_correct={i for i,(r,d) in manual_by.items() if d['verdict']=='correct'}
manual_uncertain={i for i,(r,d) in manual_by.items() if d['verdict']=='uncertain'}
if set(applied_by)|set(held_by)!=manual_correct|realm_ids: fail('manual corrections+Realm do not reconcile to applications/holds')
if len(manual_uncertain-realm_ids)!=256: fail('uncertain remaining count mismatch')
# Formal accumulator disjointness check.
sys.path.insert(0,str(BASE/'translation-tools'));import strict_populated_semantic_review_runner_core as core
bundle_dir=BASE/'slskdn-populated-review-4c2b-20261101/bundle';bm=json.loads((bundle_dir/'manifest.json').read_text())
bundle=core.load_bundle(bundle_dir,'912fadf3fce5d827fae0978323cfc7a3e96ded860be2d9c20fafe49b2720cbea','dde0829c435956ee80c7efe64d70f4c6a787dc71cbd4652d88b88303e845e111',bm['headCommit'],bm['tree'],'snapetech-org/slskdN','slskdn',BASE/'slskdn-populated-review-4c2b-20261101/snapshot-repo')
scan=core.scan_results(bundle,BASE/'semantic-review-results/slskdn-4c2b2e47-v1-912fadf3fce5');formal={d['id'] for j in scan['valid'].values() for d in j['decisions']}
if scan['invalid'] or len(scan['valid'])!=150 or len(scan['missing'])!=1951 or len(formal)!=4800 or formal&manual_ids or formal&set(applied_by)|formal&set(held_by): fail('formal accumulator invalid or overlaps manual/application rows')
for loc in LOCALES:
 changed={k for k in baseline_catalogs[loc] if baseline_catalogs[loc][k]!=catalogs[loc][k]}
 expected={r['catalogKey'] for r in applied if r['locale']==loc}
 if changed!=expected: fail(f'cumulative frozen-baseline changed-key set mismatch {loc}: {len(changed)} vs {len(expected)}')
 for r in applied:
  if r['locale']==loc:
   target=next((r[k] for k in ('newTarget','appliedTarget','rootTarget','proposedTarget','crossReviewedTarget','applied_target') if k in r),None)
   if catalogs[loc].get(r['catalogKey'])!=target: fail(f'cumulative applied target mismatch {r["id"]}')
changelog=(REPO/'docs/CHANGELOG.md').read_text(encoding='utf-8')
if '1,270 exact-hash-validated populated-catalog corrections across 290 source keys' not in changelog: fail('cumulative changelog wording mismatch')
result={'result':'PASS','window':31,'baseHead':HEAD,'baseTree':'ee4d11c5cf5b3c1053fcbdafff69dee9d2cb09d9','baseSourceSubtreeTree':'150c9fc80ce9a8f491926aa25f4397a12c8efc73','changedPaths':sorted(paths),'changedCatalogCells':len(ledger),'changedCatalogKeysByLocale':dict(sorted(changed_per_locale.items())),'changelogUpdated':True,'window31RootReview':{'rows':36,'accepted':36,'refined':0,'held':0,'candidatePlanSha256':CANDIDATE_SHA,'decisionLedgerSha256':ROOT_SHA,'applyPlanSha256':PLAN_SHA},'manualCoverage':{'windows':31,'sourceKeys':772,'cells':9238,'verdicts':dict(verdicts),'formalOverlap':0,'manualOverlap':0},'application':{'previousApplied':1234,'window31Applied':36,'totalApplied':1270,'uniqueSourceKeys':290,'heldNoContext':6,'uncertainOriginally':268,'uncertainResolvedByRealm':12,'uncertainRemaining':256,'unreviewedCells':57842,'byLocale':dict(sorted(collections.Counter(r['locale'] for r in applied).items())),'window31ByLocale':dict(sorted(collections.Counter(r['locale'] for r in ledger).items()))},'catalogCensus':{'locales':12,'keysPerLocale':6169,'totalValues':74028,'changedCellsSinceFrozenBaseline':1270,'placeholderChecks':74028,'catalogFileSha256':new_hashes},'formalAccumulator':{'validJobs':150,'missingJobs':1951,'invalidJobs':0,'cells':4800},'workflowChanges':0,'nativeSpeakerReview':'outstanding','headedBrowserReview':'outstanding','testsBuildCiReleaseOrTag':'not run','diffCheck':'PASS','worktreeStatus':'expected application paths only'}
(ROOT/'post-apply-verification-window31.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
