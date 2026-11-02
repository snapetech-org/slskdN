#!/usr/bin/env python3
import collections, hashlib, json, re, subprocess, sys
from pathlib import Path

BASE=Path('/mnt/disks/scratch/task-worktrees/localization-20261030')
REPO=BASE/'slskdn-pr409-batch4-docs-20261101'
APP=REPO/'docs/pr-evidence/pr409-catalog-correction-application-window26-2026-11-02'
MANUAL=REPO/'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01'
OLD=REPO/'docs/pr-evidence/pr409-catalog-correction-application-2026-11-01'
W18=REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows18-19-2026-11-02'
W20=REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows20-21-2026-11-02'
W22=REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02'
W24=REPO/'docs/pr-evidence/pr409-catalog-correction-application-window24-2026-11-02'
APP25=REPO/'docs/pr-evidence/pr409-catalog-correction-application-window25-2026-11-02'
BASELINE='4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb'
BASE_TREE='0eb84397dc2b4be4afd730f6818203bd5910cf15'
APP_BASE='7c3283a340324e19577a486bfc427eb40b6eb5f2'
APP_BASE_TREE='cf5e11244515bcd78b3bdea08226a52192b5aae3'
APP_BASE_SRC='4d8da43318bdd313ce7c05dcb751c0b5beb9015f'
APP_COMMIT='792f19f3ecf0370ff0cc65307cab376dd5512498'
APP_TREE='bb05bd2fb2d71937d12e2123237051ef02563013'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
EXPECTED_LOCALE_COUNTS={'ar':120,'de':57,'es':91,'fr':86,'hi':90,'id':94,'ja':60,'ko':78,'pt-BR':79,'vi':107,'zh-Hans':105,'zh-Hant':103}
def sha(b): return hashlib.sha256(b if isinstance(b,bytes) else b.encode('utf-8')).hexdigest()
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(*a): return subprocess.check_output(['git','-C',str(REPO),*a]).decode().strip()
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
def applied_target(r): return r.get('appliedTarget',r.get('proposedTarget',r.get('crossReviewedTarget',r.get('applied_target'))))

def main():
    if git('rev-parse',BASELINE+'^{tree}')!=BASE_TREE: fail('frozen catalog baseline pin changed')
    if git('rev-parse',APP_BASE+'^{tree}')!=APP_BASE_TREE or git('rev-parse',APP_BASE+':src')!=APP_BASE_SRC: fail('window26 review base tree/source pin changed')
    if git('rev-parse',APP_COMMIT+'^')!=APP_BASE or git('rev-parse',APP_COMMIT+'^{tree}')!=APP_TREE: fail('window26 application commit parent/tree mismatch')
    if git('rev-parse',APP_COMMIT+':src')==APP_BASE_SRC: fail('expected locale catalog subtree changes are absent')
    head,tree=git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}')
    if subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',APP_COMMIT,'HEAD']).returncode: fail('window26 application commit is not current-head ancestor')
    state=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,headRefOid'],text=True))
    remote=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin','refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'],text=True).split()[0]
    if state!={'state':'OPEN','isDraft':True,'headRefOid':remote}: fail(f'PR state/head does not match remote: {state} {remote}')
    if remote not in {APP_BASE,head}: fail(f'remote head unexpectedly differs from review base/current head: {remote} {head}')
    push_state='pushed-and-current' if remote==head else 'local-evidence-commit-ahead-before-push'
    app_paths=set(git('diff-tree','--no-commit-id','--name-only','-r',APP_COMMIT).splitlines())
    expected_app_paths={f'src/web/public/locales/{l}.json' for l in LOCALES}|{'docs/CHANGELOG.md'}
    if app_paths!=expected_app_paths: fail(f'window26 application path boundary mismatch: {sorted(app_paths^expected_app_paths)}')
    if any(p.startswith('.github/workflows/') for p in git('diff','--name-only',APP_BASE,APP_COMMIT).splitlines()): fail('workflow path changed in application commit')
    if any(p.startswith('src/') and '/locales/' not in p for p in git('diff','--name-only',APP_BASE,APP_COMMIT).splitlines()): fail('non-catalog source path changed in application commit')
    if '1,070 exact-hash-validated populated-catalog corrections' not in show(APP_COMMIT,'docs/CHANGELOG.md').decode('utf-8'): fail('changelog cumulative correction count mismatch')

    # Reconcile all manual windows and their exact source/target hashes.
    manual_ids=set(); manual_source_ids=set(); manual_by={}; verdicts=collections.Counter()
    per_locale=collections.defaultdict(collections.Counter)
    for w in range(1,27):
        d=MANUAL/f'window{w}'; ins=rows(d/'review-input.jsonl'); dec=rows(d/'review-decisions.jsonl')
        dm={x['id']:x for x in dec}
        if len(ins)!=300 or len(dec)!=300 or len(dm)!=300 or set(dm)!={x['id'] for x in ins}: fail(f'window {w} row count/ID join mismatch')
        if w==25:
            m=json.loads((d/'manifest.json').read_text(encoding='utf-8'))
            if (m['headCommit'],m['tree'],m['sourceSubtreeTree'])!=('5aba995a65d5901d9b92bd760072e1763d05c47d','b950c5e51b38b49033f1d85ab03609d70a2fd90f','a518acd202aebcfe7f17372017cba519e432ab9a'): fail('window25 exact review pins mismatch')
            if sha((d/'review-input.jsonl').read_bytes())!='e3763d124513fde73ddc786fdf32ec17bce713d5ced15f26e14d62c1fc13e79e': fail('window25 input hash mismatch')
            if sha((d/'review-decisions.jsonl').read_bytes())!='eb40c90a6cf2d2e2b63b9f0ccd738ab8c8e1ce5da1930df52d246193f7346aaf': fail('window25 decision hash mismatch')
            if sha((d/'proposal-plan.jsonl').read_bytes())!='e91822aa4846ad711ba9fd2393d87ad87ade9a7ec024c3307ab4a082441b0764': fail('window25 proposal plan hash mismatch')
        if w==26:
            m=json.loads((d/'manifest.json').read_text(encoding='utf-8'))
            if (m['headCommit'],m['tree'],m['sourceSubtreeTree'])!=(APP_BASE,APP_BASE_TREE,APP_BASE_SRC): fail('window26 exact review pins mismatch')
            if sha((d/'review-input.jsonl').read_bytes())!='14c65ba66c5ffd4d6074bc8b689d582b522cafe44906f1d3d6c468709604dfbb': fail('window26 input hash mismatch')
            if sha((d/'review-decisions.jsonl').read_bytes())!='44a724fff8734b42557997dfa2e8476c1159c625a23db4c35821d5e3b1ddd44c': fail('window26 decision hash mismatch')
            if sha((d/'proposal-plan.jsonl').read_bytes())!='c03732e03badefc2c8952d985c2dc89b5453b7dd3028b85d6ae75d71b08aaea5': fail('window26 proposal plan hash mismatch')
        for r in ins:
            ident=r['id']
            if ident in manual_ids: fail(f'manual-window overlap: {ident}')
            if r['locale'] not in LOCALES or ident!=f"{r['locale']}:{r['sourceId']}": fail(f'manual row ID mismatch: {ident}')
            if sha(r['source'])!=r['sourceSha256'] or sha(r['target'])!=r['targetSha256']: fail(f'manual source/target hash mismatch: {ident}')
            manual_ids.add(ident); manual_source_ids.add(r['sourceId']); manual_by[ident]=(r,dm[ident])
            verdicts[dm[ident]['verdict']]+=1; per_locale[r['locale']][dm[ident]['verdict']]+=1
    if len(manual_ids)!=7800 or len(manual_source_ids)!=650: fail('26-window cumulative coverage mismatch')
    if verdicts!=collections.Counter({'keep':6504,'correct':1064,'uncertain':232}): fail(f'manual verdict totals mismatch: {verdicts}')

    old=rows(OLD/'applied-corrections.jsonl'); w18=rows(W18/'applied-corrections.jsonl'); w20=rows(W20/'applied-corrections.jsonl')
    w22=rows(W22/'applied-corrections-windows22-23.jsonl'); realm=rows(W22/'applied-corrections-realm-window20.jsonl')
    w24=rows(W24/'applied-corrections-window24.jsonl'); w25=rows(APP25/'applied-corrections-window25.jsonl'); w26=rows(APP/'applied-corrections-window26.jsonl')
    held=rows(OLD/'held-no-context.jsonl'); applied=old+w18+w20+w22+realm+w24+w25+w26
    applied_by={r['id']:r for r in applied}; held_by={r['id']:r for r in held}
    sizes=[len(x) for x in (old,w18,w20,w22,realm,w24,w25,w26,held)]
    if sizes!=[736,82,51,53,12,45,43,48,6]: fail(f'application/hold ledger sizes mismatch: {sizes}')
    groups=[set(r['id'] for r in x) for x in (old,w18,w20,w22,realm,w24,w25,w26,held)]
    if any(groups[i]&groups[j] for i in range(len(groups)) for j in range(i+1,len(groups))): fail('application/hold ledger overlap')
    if len(applied_by)!=1070 or len({r['sourceId'] for r in applied})!=257: fail('cumulative applied count/source-key mismatch')
    if collections.Counter(r['locale'] for r in applied)!=collections.Counter(EXPECTED_LOCALE_COUNTS): fail('cumulative per-locale applied count mismatch')
    realm_ids={r['id'] for r in realm}
    manual_correct={i for i,(r,d) in manual_by.items() if d['verdict']=='correct'}
    manual_uncertain={i for i,(r,d) in manual_by.items() if d['verdict']=='uncertain'}
    if set(applied_by)|set(held_by)!=manual_correct|realm_ids: fail('applied/held rows do not reconcile to correction and Realm dispositions')
    if len(manual_uncertain-realm_ids)!=220 or len(manual_correct)!=1064: fail('remaining uncertainty or manual correction total mismatch')

    # Validate the new root review and applied ledger independently.
    root_plan=rows(APP/'root-exact-hash-apply-plan-window26.jsonl')
    root=rows(APP/'root-independent-cross-review-window26.jsonl')
    application=rows(APP/'applied-corrections-window26.jsonl')
    uncertain_rows=rows(APP/'uncertain-review-rows.jsonl')
    root_summary=json.loads((APP/'root-cross-review-summary-window26.json').read_text(encoding='utf-8'))
    manifest=json.loads((APP/'manifest.json').read_text(encoding='utf-8'))
    ledger_summary=json.loads((APP/'application-ledger-summary.json').read_text(encoding='utf-8'))
    evidence_files={p.name:sha(p.read_bytes()) for p in APP.iterdir() if p.is_file() and p.name not in {'manifest.json','SHA256SUMS'}}
    if manifest.get('evidenceFiles')!=evidence_files: fail('window26 manifest evidence-file hashes mismatch')
    if manifest.get('verificationReport',{}).get('sha256')!=sha((APP/'verification.json').read_bytes()): fail('window26 manifest verification-report hash mismatch')
    checksum_rows={}
    for line in (APP/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        digest,name=line.split('  ',1); checksum_rows[name]=digest
    checksum_expected={p.name:sha(p.read_bytes()) for p in APP.iterdir() if p.is_file() and p.name!='SHA256SUMS'}
    if checksum_rows!=checksum_expected: fail('window26 SHA256SUMS inventory/hash mismatch')
    plan_hash='abc2142cec0e7d54f45690108f4678bc78929a20365cb816a11337546745050a'
    root_hash='bbe17de3a97b1417bba86683ac795b1b3708fc288d3ea87527acf6149ede9da3'
    if len(root_plan)!=48 or len(root)!=48 or len(application)!=48 or len(uncertain_rows)!=12: fail('window26 root/application/uncertain row count mismatch')
    if sha((APP/'root-exact-hash-apply-plan-window26.jsonl').read_bytes())!=plan_hash or sha((APP/'root-independent-cross-review-window26.jsonl').read_bytes())!=root_hash: fail('window26 root evidence hash mismatch')
    if manifest.get('applicationCommit')!=APP_COMMIT or manifest.get('applicationTree')!=APP_TREE: fail('window26 application manifest pin mismatch')
    if (manifest.get('reviewBaseHead'),manifest.get('reviewBaseTree'),manifest.get('reviewSourceSubtree'))!=(APP_BASE,APP_BASE_TREE,APP_BASE_SRC): fail('window26 application manifest review pin mismatch')
    if manifest.get('rootCrossReview',{}).get('ledgerSha256')!=root_hash or manifest.get('rootCrossReview',{}).get('applyPlanSha256')!=plan_hash: fail('window26 manifest root hash mismatch')
    if manifest.get('applicationLedger',{}).get('sha256')!=sha((APP/'applied-corrections-window26.jsonl').read_bytes()): fail('window26 manifest application ledger hash mismatch')
    if ledger_summary.get('sha256')!=manifest['applicationLedger']['sha256'] or ledger_summary.get('rows')!=48: fail('window26 application summary hash/count mismatch')
    if ledger_summary.get('uniqueSourceKeys')!=10 or ledger_summary.get('byLocale')!=dict(sorted(collections.Counter(r['locale'] for r in application).items())): fail('window26 application locale/source-key summary mismatch')
    post=json.loads((APP/'post-apply-verification.json').read_text(encoding='utf-8'))
    if post.get('result')!='PASS' or (post.get('applicationBaseHead'),post.get('applicationBaseTree'),post.get('applicationBaseSourceTree'))!=(APP_BASE,APP_BASE_TREE,APP_BASE_SRC) or post.get('changedCells')!=48 or post.get('applicationRows')!=48 or post.get('uncertainRows')!=12: fail('window26 post-apply verifier pin/count mismatch')
    if post.get('uncertainRowsSha256')!=sha((APP/'uncertain-review-rows.jsonl').read_bytes()): fail('window26 uncertain-row provenance hash mismatch')
    if root_summary.get('acceptedAsProposed')!=48 or root_summary.get('refinedAndAccepted')!=0 or root_summary.get('held')!=0: fail('window26 root disposition summary mismatch')
    root_by={r['locale']+':'+r['source_id']:r for r in root}; plan_by={r['locale']+':'+r['source_id']:r for r in root_plan}
    app_by={r['id']:r for r in application}
    if set(root_by)!=set(app_by) or set(plan_by)!=set(app_by): fail('window26 root/application row join mismatch')
    for ident,a in app_by.items():
        r,d=manual_by[ident]; c=root_by[ident]; p=plan_by[ident]
        if d['verdict']!='correct' or d['target']!=a['proposedTarget']: fail(f'window26 decision/proposal mismatch {ident}')
        if (a['source'],a['sourceSha256'],a['catalogKey'],a['catalogPath'])!=(r['source'],r['sourceSha256'],r['catalogKey'],r['catalogPath']): fail(f'window26 source/catalog mismatch {ident}')
        if (a['source'],a['sourceSha256'],a['catalogKey'],a['catalogPath'],a['currentTarget'],a['currentTargetSha256'])!=(c['source'],c['source_sha256'],c['catalog_key'],c['catalog_path'],c['current_target'],c['current_target_sha256']): fail(f'window26 independent source/current join mismatch {ident}')
        if a['sourceCallsites']!=c['source_callsites']: fail(f'window26 independent caller-list mismatch {ident}')
        if a['proposedTarget']!=c['candidate_target'] or a['proposedTargetSha256']!=c['candidate_target_sha256']: fail(f'window26 root candidate hash mismatch {ident}')
        if (a['currentTarget'],a['currentTargetSha256'])!=(r['target'],r['targetSha256']): fail(f'window26 old target mismatch {ident}')
        if (a['appliedTarget'],a['appliedTargetSha256'])!=(d['target'],sha(d['target'])): fail(f'window26 applied proposal mismatch {ident}')
        if c['disposition']!='accepted-proposal' or c['final_target']!=a['appliedTarget'] or c['final_target_sha256']!=a['appliedTargetSha256']: fail(f'window26 independent review target mismatch {ident}')
        if (p['source'],p['source_sha256'],p['catalog_key'],p['catalog_path'],p['current_target_sha256'])!=(a['source'],a['sourceSha256'],a['catalogKey'],a['catalogPath'],a['currentTargetSha256']): fail(f'window26 apply-plan source/current join mismatch {ident}')
        if p['disposition']!='accepted-proposal' or p['final_target']!=a['appliedTarget'] or p['final_target_sha256']!=a['appliedTargetSha256']: fail(f'window26 exact apply-plan mismatch {ident}')
        if sha(a['currentTarget'])!=a['currentTargetSha256'] or sha(a['proposedTarget'])!=a['proposedTargetSha256'] or sha(a['appliedTarget'])!=a['appliedTargetSha256']: fail(f'window26 target hash mismatch {ident}')
        if collections.Counter(re.findall(r'{[^{}]+}',a['source']))!=collections.Counter(re.findall(r'{[^{}]+}',a['appliedTarget'])): fail(f'window26 placeholder mismatch {ident}')
        if (a['reviewHead'],a['reviewTree'],a['sourceSubtreeTree'])!=(APP_BASE,APP_BASE_TREE,APP_BASE_SRC): fail(f'window26 review pins mismatch {ident}')
        for call in a['sourceCallsites']:
            raw=show(APP_BASE,call['path'])
            if sha(raw)!=call['fileSha256']: fail(f'window26 caller file pin mismatch: {call["path"]}')
            line=raw.decode('utf-8').splitlines()[call['line']-1].strip()
            if line!=call['lineText'] or sha(line)!=call['lineTextSha256']: fail(f'window26 caller line pin mismatch: {call["path"]}:{call["line"]}')
    if len({r['sourceId'] for r in application})!=10: fail('window26 source-key count mismatch')
    if {r['id'] for r in uncertain_rows}!={i for i,(r,d) in manual_by.items() if d['verdict']=='uncertain' and r['sourceId']=='src_fb8da46694bfa931'}: fail('window26 no-caller uncertainty ledger mismatch')

    # Reconcile every catalog against the frozen baseline and cumulative correction ledgers.
    changed_by={}; catalog_hash={}
    for locale in LOCALES:
        rel=f'src/web/public/locales/{locale}.json'; base=unique(show(BASELINE,rel),f'{BASELINE}:{rel}')
        final_raw=show(APP_COMMIT,rel); final=unique(final_raw,f'{APP_COMMIT}:{rel}')
        if show(head,rel)!=final_raw or (REPO/rel).read_bytes()!=final_raw: fail(f'catalog changed after application commit: {locale}')
        if len(base)!=6169 or len(final)!=6169 or set(base)!=set(final): fail(f'catalog key census mismatch: {locale}')
        if any(not isinstance(v,str) or not v for v in final.values()): fail(f'empty/non-string catalog value: {locale}')
        expected={r['catalogKey'] for r in applied if r['locale']==locale}
        changed={k for k in base if base[k]!=final[k]}
        if changed!=expected: fail(f'cumulative catalog changed-key mismatch {locale}: {sorted(changed^expected)}')
        for r in applied:
            if r['locale']==locale and final.get(r['catalogKey'])!=applied_target(r): fail(f'cumulative final target mismatch {r["id"]}')
        changed_by[locale]=len(changed); catalog_hash[rel]=sha(final_raw)
    if sum(changed_by.values())!=1070: fail('exact catalog census does not show 1,070 changes')

    # Verify the formal accumulator remains disjoint from the manual and applied rows.
    sys.path.insert(0,str(BASE/'translation-tools'))
    import strict_populated_semantic_review_runner_core as core
    bp=BASE/'slskdn-populated-review-4c2b-20261101'/'bundle'; rp=BASE/'semantic-review-results/slskdn-4c2b2e47-v1-912fadf3fce5'
    bm=json.loads((bp/'manifest.json').read_text(encoding='utf-8'))
    bundle=core.load_bundle(bp,sha((bp/'manifest.json').read_bytes()),sha((bp/'batches.json').read_bytes()),bm['headCommit'],bm['tree'],'snapetech-org/slskdN','slskdn',BASE/'slskdn-populated-review-4c2b-20261101'/'snapshot-repo')
    fs=core.scan_results(bundle,rp)
    formal={d['id'] for x in fs['valid'].values() for d in x['decisions']}
    if fs['invalid'] or len(fs['valid'])!=150 or len(fs['missing'])!=1951 or len(formal)!=4800: fail('formal accumulator count/validity mismatch')
    if formal&manual_ids or formal&set(applied_by): fail('formal/manual/application overlap')

    manual_evidence={}
    for name in ['review-input.jsonl','review-decisions.jsonl','proposal-plan.jsonl','manifest.json']:
        p=MANUAL/'window26'/name
        manual_evidence[name]=sha(p.read_bytes())
    summary={'result':'PASS','pullRequest':409,'livePrState':state['state'],'livePrDraft':state['isDraft'],'pushState':push_state,
      'reviewBaseHead':APP_BASE,'reviewBaseTree':APP_BASE_TREE,'reviewSourceSubtree':APP_BASE_SRC,
      'applicationCommit':APP_COMMIT,'applicationTree':APP_TREE,'applicationParent':APP_BASE,
      'currentHead':head,'currentTree':tree,'currentRemoteHead':remote,
      'manualCoverage':{'windows':26,'sourceKeys':650,'cells':7800,'verdicts':dict(verdicts),'formalOverlap':0,'manualWindowOverlap':0},
      'window26RootReview':{'rows':48,'acceptedAsProposed':48,'refined':0,'held':0,'semanticConfidence':'high','localeQualityConfidence':'moderate','nativeSpeakerApproval':False,'planSha256':plan_hash,'ledgerSha256':root_hash},
      'application':{'previousApplied':1022,'newApplied':48,'totalApplied':1070,'uniqueSourceKeys':257,'heldNoContext':6,'uncertainRemaining':220,'unreviewedCells':59280,'byLocale':EXPECTED_LOCALE_COUNTS,
        'window26ByLocale':dict(sorted(collections.Counter(r['locale'] for r in application).items())),
        'window26UncertainRows':len(uncertain_rows),'window26UncertainLedgerSha256':sha((APP/'uncertain-review-rows.jsonl').read_bytes())},
      'catalogCensus':{'locales':12,'keysPerLocale':6169,'totalValues':74028,'changedCellsSinceFrozenBaseline':1070,'changedCellsByLocale':changed_by,'catalogFileSha256':catalog_hash},
      'formalAccumulator':{'validJobs':150,'missingJobs':1951,'invalidJobs':0,'cells':4800},
      'window26Rows':48,'window26SourceCallsitesRechecked':sum(len(r['sourceCallsites']) for r in application),
      'workflowChanges':0,'nonCatalogSourceChanges':0,'applicationCommitPaths':sorted(app_paths),
      'nativeSpeakerReview':'outstanding','headedBrowserReview':'outstanding','testsBuildCiReleaseOrTag':'not run','window26ManualEvidenceHashes':manual_evidence}
    out=json.dumps(summary,ensure_ascii=False,indent=2)+'\n'
    if '--no-write' not in sys.argv[1:]: (APP/'verification.json').write_text(out,encoding='utf-8')
    print(out,end='')

if __name__=='__main__': main()
