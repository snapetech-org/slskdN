#!/usr/bin/env python3
import collections, hashlib, json, re, subprocess, sys
from pathlib import Path

BASE = Path('/mnt/disks/scratch/task-worktrees/localization-20261030')
REPO = BASE / 'slskdn-pr409-batch4-docs-20261101'
APP = REPO / 'docs/pr-evidence/pr409-catalog-correction-application-window24-2026-11-02'
MANUAL = REPO / 'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01'
OLD = REPO / 'docs/pr-evidence/pr409-catalog-correction-application-2026-11-01'
W18 = REPO / 'docs/pr-evidence/pr409-catalog-correction-application-windows18-19-2026-11-02'
W20 = REPO / 'docs/pr-evidence/pr409-catalog-correction-application-windows20-21-2026-11-02'
W22 = REPO / 'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02'
BASELINE = '4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb'
APP_COMMIT = '00ee3b76686a3b4cdafd4d9a24a02342d5f36bb2'
APP_TREE = 'd0a640b4716f3363264cf96ee5fa9aea0e417a20'
BASE_HEAD = '805246b87e208cedcbdd0e2f33a83f912f4ad84b'
BASE_TREE = '4377ade660fa379731a41b54ba387c4eff2bcf32'
SRC_BEFORE = 'c3d06e298da7f7e04e69bee3c2596805a03d1e4b'
SRC_AFTER = 'a518acd202aebcfe7f17372017cba519e432ab9a'
ROOT_PLAN_SHA = 'e4181de90b344aea2ea13c199852886969a2a65088689fce4363f87c5ea87d2d'
ROOT_LEDGER_SHA = '2afa2c49dcfbf885afc70c40e8341ec8cdd4b91429825a743b460159da8c53e6'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PREVIOUS_COUNTS = {'ar':104,'de':47,'es':77,'fr':75,'hi':80,'id':85,'ja':51,'ko':66,'pt-BR':68,'vi':95,'zh-Hans':94,'zh-Hant':92}
NEW_COUNTS = {'ar':4,'de':3,'es':6,'fr':3,'hi':2,'id':2,'ja':4,'ko':4,'pt-BR':4,'vi':5,'zh-Hans':4,'zh-Hant':4}

def sha(b): return hashlib.sha256(b if isinstance(b, bytes) else b.encode('utf-8')).hexdigest()
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(*a): return subprocess.check_output(['git','-C',str(REPO),*a],text=True).strip()
def show(commit,path): return subprocess.check_output(['git','-C',str(REPO),'show',f'{commit}:{path}'])
def unique(raw,label):
    def hook(items):
        out={}
        for k,v in items:
            if k in out: raise ValueError(f'duplicate JSON key {k!r} in {label}')
            out[k]=v
        return out
    return json.loads(raw.decode('utf-8'),object_pairs_hook=hook)
def fail(msg): raise SystemExit('FAIL: '+msg)

def main():
    if git('rev-parse',BASELINE+'^{tree}')!='0eb84397dc2b4be4afd730f6818203bd5910cf15': fail('frozen baseline tree changed')
    if git('rev-parse',BASE_HEAD)!=BASE_HEAD or git('rev-parse',BASE_HEAD+'^{tree}')!=BASE_TREE or git('rev-parse',BASE_HEAD+':src')!=SRC_BEFORE: fail('reviewed application base pin changed')
    if git('rev-parse',APP_COMMIT+'^')!=BASE_HEAD or git('rev-parse',APP_COMMIT+'^1^{tree}')!=BASE_TREE or git('rev-parse',APP_COMMIT+'^{tree}')!=APP_TREE: fail('application commit/tree/parent mismatch')
    if git('rev-parse',APP_COMMIT+':src')!=SRC_AFTER: fail('post-application src tree mismatch')
    head,tree=git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}')
    if subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',APP_COMMIT,'HEAD']).returncode: fail('application commit is not current-head ancestor')
    state=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,headRefOid'],text=True))
    remote=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin','refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'],text=True).split()[0]
    if head==remote and state=={'state':'OPEN','isDraft':True,'headRefOid':head}:
        push_state='pushed-and-current'
    elif head!=remote and state=={'state':'OPEN','isDraft':True,'headRefOid':remote} and remote==BASE_HEAD:
        push_state='local-commit-ahead-before-push'
    else: fail(f'PR/remote/local state unexpected: {state}, {remote}, {head}')
    if git('rev-parse',APP_COMMIT+':docs/CHANGELOG.md') == git('rev-parse',BASE_HEAD+':docs/CHANGELOG.md'): fail('changelog correction count was not updated')
    app_paths=set(git('diff-tree','--no-commit-id','--name-only','-r',APP_COMMIT).splitlines())
    expected_app_paths={f'src/web/public/locales/{l}.json' for l in LOCALES}|{'docs/CHANGELOG.md'}
    if app_paths!=expected_app_paths: fail(f'application commit path boundary mismatch: {sorted(app_paths^expected_app_paths)}')
    if any(p.startswith('.github/workflows/') for p in git('diff','--name-only',BASE_HEAD,APP_COMMIT).splitlines()): fail('workflow path changed')
    if any(p.startswith('src/') and '/locales/' not in p for p in git('diff','--name-only',BASE_HEAD,APP_COMMIT).splitlines()): fail('non-catalog source path changed')

    # Frozen 24-window manual coverage: all twelve locale cells per selected source key.
    manual_ids=set(); manual_source_ids=set(); manual_by={}; verdicts=collections.Counter(); per_locale=collections.defaultdict(collections.Counter)
    for w in range(1,25):
        d=MANUAL/f'window{w}'
        ins=rows(d/'review-input.jsonl'); dec=rows(d/'review-decisions.jsonl')
        dm={x['id']:x for x in dec}
        if len(ins)!=300 or len(dec)!=300 or len(dm)!=300 or set(dm)!={x['id'] for x in ins}: fail(f'window {w} row count/ID join mismatch')
        if w==24:
            mm=json.loads((d/'manifest.json').read_text(encoding='utf-8'))
            if mm['headCommit']!=BASE_HEAD or mm['tree']!=BASE_TREE or mm['sourceSubtreeTree']!=SRC_BEFORE: fail('window24 review pin mismatch')
            if sha((d/'review-input.jsonl').read_bytes())!='c8b6b51bb57d476b9272d05f27386f7f7829bacaa14f077db91003eac7898270': fail('window24 input hash mismatch')
            if sha((d/'review-decisions.jsonl').read_bytes())!='b0a2e8e9a082db42423fbc08dccaed95a72f0aee5c24f48d92b56b31f2c94d69': fail('window24 decision hash mismatch')
            if sha((d/'proposal-plan.jsonl').read_bytes())!='a32015312fd7bb99e8428bbc0d42e0d5e5794c9f06d29203d4c03dadf531cfce': fail('corrected window24 proposal hash mismatch')
        for r in ins:
            ident=r['id']; dec_row=dm[ident]
            if ident in manual_ids: fail(f'manual-window overlap {ident}')
            if r['locale'] not in LOCALES or ident!=f"{r['locale']}:{r['sourceId']}": fail(f'manual ID/locale/source mismatch {ident}')
            if sha(r['source'])!=r['sourceSha256'] or sha(r['target'])!=r['targetSha256']: fail(f'manual source/target hash mismatch {ident}')
            manual_ids.add(ident); manual_source_ids.add(r['sourceId']); manual_by[ident]=(r,dec_row)
            verdicts[dec_row['verdict']]+=1; per_locale[r['locale']][dec_row['verdict']]+=1
    if len(manual_ids)!=7200 or len(manual_source_ids)!=600: fail('24-window total coverage mismatch')
    if verdicts!=collections.Counter({'keep':6007,'correct':973,'uncertain':220}): fail(f'manual verdict totals mismatch: {verdicts}')
    # Per-window 24 root independent review is separately pinned from the original proposal.
    app_rows=rows(APP/'applied-corrections-window24.jsonl')
    root_plan=rows(APP/'root-exact-hash-apply-plan-window24.jsonl')
    root_ledger=rows(APP/'root-independent-cross-review-window24.jsonl')
    if len(app_rows)!=45 or len(root_plan)!=45 or len(root_ledger)!=45: fail('window24 independent/application ledger row count mismatch')
    for p,expected in [('root-exact-hash-apply-plan-window24.jsonl',ROOT_PLAN_SHA),('root-independent-cross-review-window24.jsonl',ROOT_LEDGER_SHA)]:
        if sha((APP/p).read_bytes())!=expected: fail(f'{p} checksum mismatch')
    plan_by={r['id']:r for r in root_plan}; root_by={r['id']:r for r in root_ledger}; app_by={r['id']:r for r in app_rows}
    if len(plan_by)!=45 or len(root_by)!=45 or len(app_by)!=45 or len(set(app_by)&manual_ids)!=45: fail('window24 IDs missing, duplicated, or outside manual window')
    dispositions=collections.Counter(r['rootDisposition'] for r in root_plan)
    if dispositions!=collections.Counter({'accepted-proposal':43,'refined':2}): fail(f'root disposition counts mismatch {dispositions}')
    for ident,a in app_by.items():
        r,d=manual_by[ident];p=plan_by[ident];c=root_by[ident]
        if d['verdict']!='correct' or a['currentTarget']!=r['target'] or a['proposedTarget']!=d['target']: fail(f'window24 decision/application mismatch {ident}')
        if a['appliedTarget']!=p['reviewedTarget'] or a['appliedTargetSha256']!=p['reviewedTargetHash'] or c['rootReviewedTarget']!=a['appliedTarget']: fail(f'root target/application mismatch {ident}')
        if a['rootDisposition']!=p['rootDisposition'] or p['rootCrossReviewLedgerSha256']!=ROOT_LEDGER_SHA: fail(f'root disposition/hash mismatch {ident}')
        if sha(a['currentTarget'])!=a['currentTargetSha256'] or sha(a['appliedTarget'])!=a['appliedTargetSha256']: fail(f'window24 target hash mismatch {ident}')
        if collections.Counter(re.findall(r'{[^{}]+}',a['source']))!=collections.Counter(re.findall(r'{[^{}]+}',a['appliedTarget'])): fail(f'placeholder mismatch {ident}')
        if not a.get('sourceCallsites'): fail(f'missing caller evidence {ident}')
    if collections.Counter(r['locale'] for r in app_rows)!=collections.Counter(NEW_COUNTS): fail('window24 per-locale correction counts mismatch')

    old=rows(OLD/'applied-corrections.jsonl')
    w18=rows(W18/'applied-corrections.jsonl')
    w20=rows(W20/'applied-corrections.jsonl')
    w22=rows(W22/'applied-corrections-windows22-23.jsonl')
    realm=rows(W22/'applied-corrections-realm-window20.jsonl')
    held=rows(OLD/'held-no-context.jsonl')
    applied=old+w18+w20+w22+realm+app_rows
    applied_by={r['id']:r for r in applied}; held_by={r['id']:r for r in held}
    if [len(x) for x in (old,w18,w20,w22,realm,app_rows,held)] != [736,82,51,53,12,45,6]: fail('prior/current application or hold row count mismatch')
    groups=[set(r['id'] for r in x) for x in (old,w18,w20,w22,realm,app_rows,held)]
    if any(groups[i]&groups[j] for i in range(len(groups)) for j in range(i+1,len(groups))): fail('application/hold ledger overlap')
    if len(applied_by)!=979 or len({r['sourceId'] for r in applied})!=238: fail('cumulative applied rows/source-key count mismatch')
    expected_totals={l:PREVIOUS_COUNTS[l]+NEW_COUNTS[l] for l in LOCALES}
    if collections.Counter(r['locale'] for r in applied)!=collections.Counter(expected_totals): fail('cumulative per-locale correction counts mismatch')
    if set(applied_by)|set(held_by)!={i for i,(r,d) in manual_by.items() if d['verdict']=='correct'}|{i for i,(r,d) in manual_by.items() if d['verdict']=='uncertain' and i in realm_by_id(realm)}:
        fail('applied/held rows do not reconcile with manual correction and independently resolved Realm rows')
    if len({i for i,(r,d) in manual_by.items() if d['verdict']=='uncertain'}-set(realm_by_id(realm)))!=208: fail('remaining uncertain count mismatch')
    if len({i for i,(r,d) in manual_by.items() if d['verdict']=='correct'})!=973: fail('manual correction row count mismatch')

    # Exact catalog census and changed-cell reconciliation against frozen baseline.
    changed_by={}; after_hash={}
    for l in LOCALES:
        rel=f'src/web/public/locales/{l}.json'
        basecat=unique(show(BASELINE,rel),f'{BASELINE}:{rel}')
        finalraw=show(APP_COMMIT,rel); finalcat=unique(finalraw,f'{APP_COMMIT}:{rel}')
        if show(head,rel)!=finalraw: fail(f'catalog changed after application commit: {l}')
        if len(basecat)!=6169 or len(finalcat)!=6169 or set(basecat)!=set(finalcat): fail(f'catalog census/key set mismatch: {l}')
        if any(not isinstance(v,str) or not v for v in finalcat.values()): fail(f'non-string/empty catalog value: {l}')
        expected_keys={r['catalogKey'] for r in applied if r['locale']==l}
        changed={k for k in basecat if basecat[k]!=finalcat[k]}
        if changed!=expected_keys: fail(f'catalog changed-key ledger mismatch {l}: {sorted(changed^expected_keys)}')
        for r in applied:
            if r['locale']==l:
                target=r.get('appliedTarget',r.get('proposedTarget',r.get('crossReviewedTarget')))
                if finalcat.get(r['catalogKey'])!=target: fail(f'final catalog target mismatch {r["id"]}')
        changed_by[l]=len(changed); after_hash[rel]=sha(finalraw)
    if sum(changed_by.values())!=979: fail('exact catalog census does not show 979 changed values')
    if '979 exact-hash-validated populated-catalog corrections' not in show(APP_COMMIT,'docs/CHANGELOG.md').decode('utf-8'): fail('changelog does not report 979 corrections')

    # Formal result accumulator, exact set disjointness, and caller/source integrity.
    sys.path.insert(0,str(BASE/'translation-tools'))
    import strict_populated_semantic_review_runner_core as core
    bundle_path=BASE/'slskdn-populated-review-4c2b-20261101'/'bundle'
    result_path=BASE/'semantic-review-results/slskdn-4c2b2e47-v1-912fadf3fce5'
    bm=json.loads((bundle_path/'manifest.json').read_text(encoding='utf-8'))
    bundle=core.load_bundle(bundle_path,sha((bundle_path/'manifest.json').read_bytes()),sha((bundle_path/'batches.json').read_bytes()),bm['headCommit'],bm['tree'],'snapetech-org/slskdN','slskdn',BASE/'slskdn-populated-review-4c2b-20261101'/'snapshot-repo')
    fs=core.scan_results(bundle,result_path)
    if fs['invalid'] or len(fs['valid'])!=150 or len(fs['missing'])!=1951: fail('formal result accumulator count/validity changed')
    formal={d['id'] for x in fs['valid'].values() for d in x['decisions']}
    if len(formal)!=4800 or formal&manual_ids: fail('formal/manual overlap or formal cell count mismatch')
    if any(i in applied_by for i in formal): fail('formal ledger overlaps an applied correction')
    # Verify exact source + caller pins for every newly applied row.
    call_count=0
    for r in app_rows:
        for c in root_by[r['id']].get('sourceCallsites',[]):
            raw=show(BASE_HEAD,c['path'])
            if sha(raw)!=c['fileSha256']: fail(f'window24 caller file pin mismatch: {c["path"]}')
            line=raw.decode('utf-8').splitlines()[c['line']-1].strip()
            if line!=c['lineText'] or sha(line)!=c['lineTextSha256']: fail(f'window24 caller line pin mismatch: {c["path"]}:{c["line"]}')
            call_count+=1
    summary={
      'result':'PASS','pullRequest':409,'livePrState':state['state'],'livePrDraft':state['isDraft'],'pushState':push_state,
      'reviewBaseHead':BASE_HEAD,'reviewBaseTree':BASE_TREE,'reviewSourceSubtree':SRC_BEFORE,
      'applicationCommit':APP_COMMIT,'applicationTree':APP_TREE,'applicationParent':BASE_HEAD,'applicationParentTree':BASE_TREE,
      'currentHead':head,'currentTree':tree,'currentRemoteHead':remote,
      'manualCoverage':{'windows':24,'sourceKeys':600,'cells':7200,'verdicts':dict(verdicts),'formalOverlap':0,'manualWindowOverlap':0},
      'rootWindow24Review':{'rows':45,'acceptedAsProposed':43,'refinedAndAccepted':2,'held':0,'semanticConfidence':'high','localeQualityConfidence':'moderate','nativeSpeakerApproval':False,'planSha256':ROOT_PLAN_SHA,'ledgerSha256':ROOT_LEDGER_SHA},
      'application':{'previousApplied':934,'newApplied':45,'totalApplied':979,'uniqueSourceKeys':238,'heldNoContext':6,'uncertainRemaining':208,'unreviewedCells':59880,'byLocale':expected_totals,'window24ByLocale':NEW_COUNTS},
      'catalogCensus':{'locales':12,'keysPerLocale':6169,'totalValues':74028,'changedCellsSinceFrozenBaseline':979,'changedCellsByLocale':changed_by,'catalogFileSha256':after_hash},
      'formalAccumulator':{'validJobs':150,'missingJobs':1951,'invalidJobs':0,'cells':4800},
      'callerPinsRechecked':call_count,'workflowChanges':0,'nonCatalogSourceChanges':0,
      'applicationCommitPaths':sorted(app_paths),'nativeSpeakerReview':'outstanding','testsBuildCiReleaseOrTag':'not run'
    }
    out=json.dumps(summary,ensure_ascii=False,indent=2)+'\n'
    if '--no-write' not in sys.argv[1:]:
        (APP/'verification.json').write_text(out,encoding='utf-8')
    print(out,end='')

def realm_by_id(rows_): return {r['id']:r for r in rows_}

if __name__=='__main__': main()
