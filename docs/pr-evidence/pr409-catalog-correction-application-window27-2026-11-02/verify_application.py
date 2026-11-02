#!/usr/bin/env python3
import collections, hashlib, json, re, subprocess, sys
from pathlib import Path

BASE=Path('/mnt/disks/scratch/task-worktrees/localization-20261030')
REPO=BASE/'slskdn-pr409-batch4-docs-20261101'
APP=REPO/'docs/pr-evidence/pr409-catalog-correction-application-window27-2026-11-02'
MANUAL=REPO/'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01'
OLD=REPO/'docs/pr-evidence/pr409-catalog-correction-application-2026-11-01'
W18=REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows18-19-2026-11-02'
W20=REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows20-21-2026-11-02'
W22=REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02'
W24=REPO/'docs/pr-evidence/pr409-catalog-correction-application-window24-2026-11-02'
APP25=REPO/'docs/pr-evidence/pr409-catalog-correction-application-window25-2026-11-02'
APP26=REPO/'docs/pr-evidence/pr409-catalog-correction-application-window26-2026-11-02'
BASELINE='4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb'
BASE_TREE='0eb84397dc2b4be4afd730f6818203bd5910cf15'
APP_BASE='11e7971bc33513c7aad65f2831e1d474e541a5e0'
APP_BASE_TREE='97b609cdbf423f55d595a77220b7362b9fd3d8ef'
APP_BASE_SRC='ee5969020b2184b7a6179e8e7b9805041c782fb7'
APP_COMMIT='3c25504c8c475ae40dab1acef2a85bdb37f1a620'
APP_TREE='349af6afff06f50d9583cecbe05847486affd15b'
CANDIDATE_SHA='c0fee30c06711138405301f4bd781fef1b12d3387a3bfd6f433a1ca457797c69'
ROOT_LEDGER_SHA='64d248714be02c9ee6f246b91f835193794eec8e946d726aadb9a35dba98af00'
ROOT_PLAN_SHA='7b901948fb2fe6ec473d7f961b18c89a07767d215dcb4f741071780e7e662227'
ROOT_SUMMARY_SHA='22c7ba81f4069d54d7c9d3945023262e97ade582e04ce0fca9a6aecfef2e361a'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
EXPECTED_LOCALE_COUNTS={'ar':124,'de':60,'es':94,'fr':90,'hi':93,'id':97,'ja':62,'ko':82,'pt-BR':82,'vi':111,'zh-Hans':110,'zh-Hant':109}
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
    if git('rev-parse',APP_BASE+'^{tree}')!=APP_BASE_TREE or git('rev-parse',APP_BASE+':src')!=APP_BASE_SRC: fail('window27 review base tree/source pin changed')
    if git('rev-parse',APP_COMMIT+'^')!=APP_BASE or git('rev-parse',APP_COMMIT+'^{tree}')!=APP_TREE: fail('window27 application commit parent/tree mismatch')
    head,tree=git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}')
    if subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',APP_COMMIT,'HEAD']).returncode: fail('window27 application commit is not current-head ancestor')
    state=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,headRefOid'],text=True))
    remote=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin','refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'],text=True).split()[0]
    if state!={'state':'OPEN','isDraft':True,'headRefOid':remote}: fail(f'PR state/head does not match remote: {state} {remote}')
    if remote not in {APP_BASE,head}: fail(f'remote head unexpectedly differs from review base/current head: {remote} {head}')
    push_state='pushed-and-current' if remote==head else 'local-reviewed-commit-ahead-before-push'
    app_paths=set(git('diff-tree','--no-commit-id','--name-only','-r',APP_COMMIT).splitlines())
    expected_app_paths={f'src/web/public/locales/{l}.json' for l in LOCALES}|{'docs/CHANGELOG.md'}
    if app_paths!=expected_app_paths: fail(f'window27 application path boundary mismatch: {sorted(app_paths^expected_app_paths)}')
    if any(p.startswith('.github/workflows/') for p in git('diff','--name-only',APP_BASE,APP_COMMIT).splitlines()): fail('workflow path changed in application commit')
    if any(p.startswith('src/') and '/locales/' not in p for p in git('diff','--name-only',APP_BASE,APP_COMMIT).splitlines()): fail('non-catalog source path changed in application commit')
    if '1,114 exact-hash-validated populated-catalog corrections across 265 source keys' not in show(APP_COMMIT,'docs/CHANGELOG.md').decode('utf-8'): fail('changelog cumulative correction count mismatch')

    # Reconcile all 27 disjoint manual windows.
    manual_ids=set(); manual_source_ids=set(); manual_by={}; verdicts=collections.Counter()
    for w in range(1,28):
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
            if (m['headCommit'],m['tree'],m['sourceSubtreeTree'])!=('7c3283a340324e19577a486bfc427eb40b6eb5f2','cf5e11244515bcd78b3bdea08226a52192b5aae3','4d8da43318bdd313ce7c05dcb751c0b5beb9015f'): fail('window26 exact review pins mismatch')
            if sha((d/'review-input.jsonl').read_bytes())!='14c65ba66c5ffd4d6074bc8b689d582b522cafe44906f1d3d6c468709604dfbb': fail('window26 input hash mismatch')
            if sha((d/'review-decisions.jsonl').read_bytes())!='44a724fff8734b42557997dfa2e8476c1159c625a23db4c35821d5e3b1ddd44c': fail('window26 decision hash mismatch')
            if sha((d/'proposal-plan.jsonl').read_bytes())!='c03732e03badefc2c8952d985c2dc89b5453b7dd3028b85d6ae75d71b08aaea5': fail('window26 proposal plan hash mismatch')
        if w==27:
            m=json.loads((d/'manifest.json').read_text(encoding='utf-8'))
            if (m['headCommit'],m['tree'],m['sourceSubtreeTree'])!=(APP_BASE,APP_BASE_TREE,APP_BASE_SRC): fail('window27 exact review pins mismatch')
            if sha((d/'review-input.jsonl').read_bytes())!='8a4954b9d45056abafb1646eb547c3aeccaba2a57b359289ac929d15d0fc0f86': fail('window27 input hash mismatch')
            if sha((d/'review-decisions.jsonl').read_bytes())!='5404625d7ff6b26dbe557aee95e1716b4854c892c832cc2e384fbf554d4ed858': fail('window27 decision hash mismatch')
            if sha((d/'crossreview-plan.jsonl').read_bytes())!=CANDIDATE_SHA: fail('window27 proposal plan hash mismatch')
        for r in ins:
            ident=r['id']
            if ident in manual_ids: fail(f'manual-window overlap: {ident}')
            if r['locale'] not in LOCALES or ident!=f"{r['locale']}:{r['sourceId']}": fail(f'manual row ID mismatch: {ident}')
            if sha(r['source'])!=r['sourceSha256'] or sha(r['target'])!=r['targetSha256']: fail(f'manual source/target hash mismatch: {ident}')
            manual_ids.add(ident); manual_source_ids.add(r['sourceId']); manual_by[ident]=(r,dm[ident])
            verdicts[dm[ident]['verdict']]+=1
    if len(manual_ids)!=8100 or len(manual_source_ids)!=675: fail('27-window cumulative coverage mismatch')
    if verdicts!=collections.Counter({'keep':6760,'correct':1108,'uncertain':232}): fail(f'manual verdict totals mismatch: {verdicts}')

    old=rows(OLD/'applied-corrections.jsonl'); w18=rows(W18/'applied-corrections.jsonl'); w20=rows(W20/'applied-corrections.jsonl')
    w22=rows(W22/'applied-corrections-windows22-23.jsonl'); realm=rows(W22/'applied-corrections-realm-window20.jsonl')
    w24=rows(W24/'applied-corrections-window24.jsonl'); w25=rows(APP25/'applied-corrections-window25.jsonl')
    w26=rows(APP26/'applied-corrections-window26.jsonl'); w27=rows(APP/'applied-corrections-window27.jsonl')
    held=rows(OLD/'held-no-context.jsonl'); applied=old+w18+w20+w22+realm+w24+w25+w26+w27
    applied_by={r['id']:r for r in applied}; held_by={r['id']:r for r in held}
    sizes=[len(x) for x in (old,w18,w20,w22,realm,w24,w25,w26,w27,held)]
    if sizes!=[736,82,51,53,12,45,43,48,44,6]: fail(f'application/hold ledger sizes mismatch: {sizes}')
    groups=[set(r['id'] for r in x) for x in (old,w18,w20,w22,realm,w24,w25,w26,w27,held)]
    if any(groups[i]&groups[j] for i in range(len(groups)) for j in range(i+1,len(groups))): fail('application/hold ledger overlap')
    if len(applied_by)!=1114 or len({r['sourceId'] for r in applied})!=265: fail('cumulative applied count/source-key mismatch')
    if collections.Counter(r['locale'] for r in applied)!=collections.Counter(EXPECTED_LOCALE_COUNTS): fail('cumulative per-locale applied count mismatch')
    realm_ids={r['id'] for r in realm}
    manual_correct={i for i,(r,d) in manual_by.items() if d['verdict']=='correct'}
    manual_uncertain={i for i,(r,d) in manual_by.items() if d['verdict']=='uncertain'}
    if set(applied_by)|set(held_by)!=manual_correct|realm_ids: fail('applied/held rows do not reconcile to correction and Realm dispositions')
    if len(manual_uncertain-realm_ids)!=220 or len(manual_correct)!=1108: fail('remaining uncertainty or manual correction total mismatch')

    # Verify the exact-root-review application for Window27.
    root_plan=rows(APP/'root-apply-plan-window27.jsonl')
    root=rows(APP/'root-crossreview-decisions-window27.jsonl')
    application=rows(APP/'applied-corrections-window27.jsonl')
    uncertain_rows=rows(APP/'uncertain-review-rows.jsonl')
    root_summary=json.loads((APP/'root-crossreview-summary-window27.json').read_text(encoding='utf-8'))
    manifest=json.loads((APP/'manifest.json').read_text(encoding='utf-8'))
    ledger_summary=json.loads((APP/'application-ledger-summary.json').read_text(encoding='utf-8'))
    if manifest.get('evidenceFiles'):
        evidence_files={p.name:sha(p.read_bytes()) for p in APP.iterdir() if p.is_file() and p.name not in {'manifest.json','SHA256SUMS'}}
        if manifest.get('evidenceFiles')!=evidence_files: fail('window27 manifest evidence-file hashes mismatch')
        if manifest.get('verificationReport',{}).get('sha256')!=sha((APP/'verification.json').read_bytes()): fail('window27 manifest verification-report hash mismatch')
        checksum_rows={}
        for line in (APP/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
            digest,name=line.split('  ',1); checksum_rows[name]=digest
        checksum_expected={p.name:sha(p.read_bytes()) for p in APP.iterdir() if p.is_file() and p.name!='SHA256SUMS'}
        if checksum_rows!=checksum_expected: fail('window27 SHA256SUMS inventory/hash mismatch')
    if len(root_plan)!=44 or len(root)!=44 or len(application)!=44 or len(uncertain_rows)!=0: fail('window27 root/application/uncertain row count mismatch')
    if (sha((APP/'root-apply-plan-window27.jsonl').read_bytes()),sha((APP/'root-crossreview-decisions-window27.jsonl').read_bytes()),sha((APP/'root-crossreview-summary-window27.json').read_bytes()))!=(ROOT_PLAN_SHA,ROOT_LEDGER_SHA,ROOT_SUMMARY_SHA): fail('window27 root evidence hash mismatch')
    if manifest.get('applicationCommit')!=APP_COMMIT or manifest.get('applicationTree')!=APP_TREE or manifest.get('applicationParent')!=APP_BASE: fail('window27 application manifest pin mismatch')
    if (manifest.get('reviewBaseHead'),manifest.get('reviewBaseTree'),manifest.get('reviewSourceSubtree'))!=(APP_BASE,APP_BASE_TREE,APP_BASE_SRC): fail('window27 application manifest review pin mismatch')
    if manifest.get('rootCrossReview',{}).get('ledgerSha256')!=ROOT_LEDGER_SHA or manifest.get('rootCrossReview',{}).get('applyPlanSha256')!=ROOT_PLAN_SHA: fail('window27 manifest root hash mismatch')
    if manifest.get('applicationLedger',{}).get('sha256')!=sha((APP/'applied-corrections-window27.jsonl').read_bytes()): fail('window27 manifest application ledger hash mismatch')
    if ledger_summary.get('sha256')!=manifest['applicationLedger']['sha256'] or ledger_summary.get('rows')!=44 or ledger_summary.get('uniqueSourceKeys')!=8: fail('window27 application summary hash/count mismatch')
    if ledger_summary.get('byLocale')!=dict(sorted(collections.Counter(r['locale'] for r in application).items())): fail('window27 application locale count mismatch')
    post=json.loads((APP/'post-apply-verification.json').read_text(encoding='utf-8'))
    if post.get('result')!='PASS' or post.get('baseHead')!=APP_BASE or post.get('applicationRows')!=44 or post.get('changedCells')!=44: fail('window27 post-apply verification pin/count mismatch')
    if post.get('rootLedgerSha256')!=ROOT_LEDGER_SHA or post.get('rootApplyPlanSha256')!=ROOT_PLAN_SHA: fail('window27 post-apply root provenance mismatch')
    if root_summary.get('candidateCount')!=44 or root_summary.get('applyCount')!=44 or root_summary.get('decisionCounts')!={'accepted':30,'refined':14} or root_summary.get('uncertain')!=0: fail('window27 root disposition summary mismatch')
    root_by={r['id']:r for r in root}; plan_by={r['id']:r for r in root_plan}; app_by={r['id']:r for r in application}
    if set(root_by)!=set(app_by) or set(plan_by)!=set(app_by): fail('window27 root/application row join mismatch')
    manual27={r['id']:r for r in rows(MANUAL/'window27'/'review-input.jsonl')}
    decisions27={r['id']:r for r in rows(MANUAL/'window27'/'review-decisions.jsonl')}
    candidates={r['id']:r for r in rows(MANUAL/'window27'/'crossreview-plan.jsonl')}
    for ident,a in app_by.items():
        r=root_by[ident];p=plan_by[ident];i=manual27[ident];d=decisions27[ident];c=candidates[ident]
        if d['verdict']!='correct' or d['target']!=a['proposedTarget']: fail(f'window27 decision/proposal mismatch {ident}')
        if (a['source'],a['sourceSha256'],a['catalogKey'],a['catalogPath'],a['currentTarget'],a['currentTargetSha256'])!=(r['source'],r['sourceSha256'],r['catalogKey'],r['catalogPath'],r['currentTarget'],r['currentTargetSha256']): fail(f'window27 root source/current join mismatch {ident}')
        if (a['source'],a['sourceSha256'],a['catalogKey'],a['catalogPath'],a['currentTarget'],a['currentTargetSha256'])!=(i['source'],i['sourceSha256'],i['catalogKey'],i['catalogPath'],i['target'],i['targetSha256']): fail(f'window27 manual source/current join mismatch {ident}')
        if (a['proposedTarget'],a['proposedTargetSha256'])!=(c['proposedTarget'],c['proposedTargetSha256']): fail(f'window27 proposal-plan join mismatch {ident}')
        if (a['appliedTarget'],a['appliedTargetSha256'])!=(r['rootTarget'],r['rootTargetSha256']): fail(f'window27 root final target mismatch {ident}')
        if a['rootDisposition']!=r['disposition'] or a['rootReason']!=r['rootReason']: fail(f'window27 root disposition/reason mismatch {ident}')
        if (p['id'],p['rootTarget'],p['rootTargetSha256'],p['currentTarget'],p['currentTargetSha256'])!=(ident,a['appliedTarget'],a['appliedTargetSha256'],a['currentTarget'],a['currentTargetSha256']): fail(f'window27 exact apply-plan mismatch {ident}')
        if (p['candidatePlanSha256'],p['rootLedgerSha256'],p['currentPrHead'],p['currentPrTree'],p['currentSourceSubtreeTree'])!=(CANDIDATE_SHA,ROOT_LEDGER_SHA,APP_BASE,APP_BASE_TREE,APP_BASE_SRC): fail(f'window27 apply-plan provenance mismatch {ident}')
        if sha(a['source'])!=a['sourceSha256'] or sha(a['currentTarget'])!=a['currentTargetSha256'] or sha(a['proposedTarget'])!=a['proposedTargetSha256'] or sha(a['appliedTarget'])!=a['appliedTargetSha256']: fail(f'window27 hash mismatch {ident}')
        if collections.Counter(re.findall(r'{[^{}]+}',a['source']))!=collections.Counter(re.findall(r'{[^{}]+}',a['appliedTarget'])): fail(f'window27 placeholder mismatch {ident}')
        if (a['reviewHead'],a['reviewTree'],a['sourceSubtreeTree'])!=(APP_BASE,APP_BASE_TREE,APP_BASE_SRC): fail(f'window27 review pins mismatch {ident}')
        if a['sourceCallsites']!=r['sourceCallsites']: fail(f'window27 caller-list mismatch {ident}')
        for call in a['sourceCallsites']:
            raw=show(APP_BASE,call['path'])
            if sha(raw)!=call['fileSha256']: fail(f'window27 caller file pin mismatch: {call["path"]}')
            line=raw.decode('utf-8').splitlines()[call['line']-1].strip()
            if line!=call['lineText'] or sha(line)!=call['lineTextSha256']: fail(f'window27 caller line pin mismatch: {call["path"]}:{call["line"]}')
    if len({r['sourceId'] for r in application})!=8: fail('window27 source-key count mismatch')

    # Compare every final catalog with the frozen catalog baseline and all applied ledgers.
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
    if sum(changed_by.values())!=1114: fail('exact catalog census does not show 1,114 changes')

    # Reconcile the manual set with the frozen formal accumulator.
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
    for name in ['review-input.jsonl','review-decisions.jsonl','crossreview-plan.jsonl','manifest.json']:
        p=MANUAL/'window27'/name; manual_evidence[name]=sha(p.read_bytes())
    w27by=collections.Counter(r['locale'] for r in application)
    summary={'result':'PASS','pullRequest':409,'livePrState':state['state'],'livePrDraft':state['isDraft'],'pushState':push_state,
      'reviewBaseHead':APP_BASE,'reviewBaseTree':APP_BASE_TREE,'reviewSourceSubtree':APP_BASE_SRC,
      'applicationCommit':APP_COMMIT,'applicationTree':APP_TREE,'applicationParent':APP_BASE,
      'currentHead':head,'currentTree':tree,'currentRemoteHead':remote,
      'manualCoverage':{'windows':27,'sourceKeys':675,'cells':8100,'verdicts':dict(verdicts),'formalOverlap':0,'manualWindowOverlap':0},
      'window27RootReview':{'rows':44,'acceptedAsProposed':30,'refined':14,'held':0,'semanticConfidence':'high','localeQualityConfidence':'moderate','nativeSpeakerApproval':False,'planSha256':ROOT_PLAN_SHA,'ledgerSha256':ROOT_LEDGER_SHA},
      'application':{'previousApplied':1070,'newApplied':44,'totalApplied':1114,'uniqueSourceKeys':265,'heldNoContext':6,'uncertainRemaining':220,'unreviewedCells':58980,'byLocale':EXPECTED_LOCALE_COUNTS,
        'window27ByLocale':dict(sorted(w27by.items())),'window27UncertainRows':len(uncertain_rows)},
      'catalogCensus':{'locales':12,'keysPerLocale':6169,'totalValues':74028,'changedCellsSinceFrozenBaseline':1114,'changedCellsByLocale':changed_by,'catalogFileSha256':catalog_hash},
      'formalAccumulator':{'validJobs':150,'missingJobs':1951,'invalidJobs':0,'cells':4800},
      'window27Rows':44,'window27SourceCallsitesRechecked':sum(len(r['sourceCallsites']) for r in application),
      'workflowChanges':0,'nonCatalogSourceChanges':0,'applicationCommitPaths':sorted(app_paths),
      'nativeSpeakerReview':'outstanding','headedBrowserReview':'outstanding','testsBuildCiReleaseOrTag':'not run','window27ManualEvidenceHashes':manual_evidence}
    out=json.dumps(summary,ensure_ascii=False,indent=2)+'\n'
    if '--no-write' not in sys.argv[1:]: (APP/'verification.json').write_text(out,encoding='utf-8')
    print(out,end='')
if __name__=='__main__': main()
