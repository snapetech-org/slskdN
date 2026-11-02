#!/usr/bin/env python3
"""Cumulative exact-hash audit for slskdN PR #409 through window 29."""
import collections, hashlib, json, re, subprocess, sys
from pathlib import Path
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261030/slskdn-pr409-batch4-docs-20261101')
BASE=Path('/mnt/disks/scratch/task-worktrees/localization-20261030')
MANUAL=REPO/'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01'
OLD=REPO/'docs/pr-evidence/pr409-catalog-correction-application-2026-11-01'
W18=REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows18-19-2026-11-02'
W20=REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows20-21-2026-11-02'
W22=REPO/'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02'
W24=REPO/'docs/pr-evidence/pr409-catalog-correction-application-window24-2026-11-02'
W25=REPO/'docs/pr-evidence/pr409-catalog-correction-application-window25-2026-11-02'
W26=REPO/'docs/pr-evidence/pr409-catalog-correction-application-window26-2026-11-02'
W27=REPO/'docs/pr-evidence/pr409-catalog-correction-application-window27-2026-11-02'
APP=REPO/'docs/pr-evidence/pr409-catalog-correction-application-window28-2026-11-02'
APP29=REPO/'docs/pr-evidence/pr409-catalog-correction-application-window29-2026-11-02'
BUNDLE=BASE/'slskdn-populated-review-4c2b-20261101'/'bundle'
RESULTS=BASE/'semantic-review-results/slskdn-4c2b2e47-v1-912fadf3fce5'
BASELINE='4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb'
BASE_TREE='0eb84397dc2b4be4afd730f6818203bd5910cf15'
REVIEW_BASE='17e8d8b829867065b882423ef81c69f1f31c7d07'
REVIEW_TREE='7562b0dd09a92398a898d84e1c936119492015be'
REVIEW_SRC='6d80c43cea32f0a5721f31235ec80e6eaa6d1896'
APP_COMMIT='c420ebc057d675586eaf931d6f5daeb152a16c78'
APP_TREE='ff1c49d7bc72cae70e9d5c4b4c86442358a3474b'
CANDIDATE_SHA='f5ac0b1afa7ac50c6138dfbb11297f09c51a61e99fa52344519ea06c8750d574'
ROOT_LEDGER_SHA='2e913a85844b83658c057667a65831f50bb3897bc61255a6196d29cbe865259b'
ROOT_PLAN_SHA='ade3ade63ee11a972eb95c175b48ad38161ab4883e0f14c97e417425be8ea161'
ROOT_SUMMARY_SHA='2601d94cf69ac8e08d5c19ec66b845c7c5179fa2c68b30e26ab9f470b144ec5b'
REVIEW29_BASE='3aac5309e1dba8265ac8736aea74723ff0f6ef31'
REVIEW29_TREE='8070731f8ee7529b9f4353720ca6214941b1ae21'
REVIEW29_SRC='299b4318cd8fc2a03173ab510ee265a779964034'
APP29_COMMIT='dff0b0281483d777c01c5e7dd68e24b51fdc67f8'
APP29_TREE='37f299d9e8f2f476bbc3eaefe872f3c727a4b17d'
CANDIDATE29_SHA='b0d0cd3ebfc890d02edd0f89069d3e4bf452cb1785e969a5bc6e00a60a4c3568'
ROOT29_LEDGER_SHA='005cf0d557f5a919311f233763033102194a0bd7a0ce37f27f077df1b6c3f4ee'
ROOT29_PLAN_SHA='005cf0d557f5a919311f233763033102194a0bd7a0ce37f27f077df1b6c3f4ee'
ROOT29_SUMMARY_SHA='f985587187abfd975968a65ecd3255b836ec6fd8b0c83b486cc02bc3dbd64d20'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
EXPECTED_LOCALE_COUNTS={'ar':131,'de':67,'es':102,'fr':99,'hi':99,'id':103,'ja':67,'ko':88,'pt-BR':88,'vi':120,'zh-Hans':116,'zh-Hant':115}
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
    if git('rev-parse',BASELINE+'^{tree}')!=BASE_TREE: fail('frozen baseline tree pin changed')
    if git('rev-parse',REVIEW_BASE+'^{tree}')!=REVIEW_TREE or git('rev-parse',REVIEW_BASE+':src')!=REVIEW_SRC: fail('window28 review source/catalog pin changed')
    if git('rev-parse',APP_COMMIT+'^')!=REVIEW_BASE or git('rev-parse',APP_COMMIT+'^{tree}')!=APP_TREE: fail('window28 application parent/tree mismatch')
    head,tree=git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}')
    if subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',APP_COMMIT,'HEAD']).returncode: fail('window28 application commit is not an ancestor of current head')
    state=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,headRefOid'],text=True))
    remote=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin','refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'],text=True).split()[0]
    if state.get('state')!='OPEN' or state.get('isDraft') is not True or state.get('headRefOid')!=remote: fail(f'PR state/head mismatch: {state} remote={remote}')
    if remote not in {REVIEW_BASE,APP_COMMIT,REVIEW29_BASE,APP29_COMMIT,head}: fail(f'remote head is neither review base nor reviewed local/app head: {remote} {head}')
    push_state='pushed-and-current' if remote==head else 'reviewed-local-commit-ahead-before-push'
    app_paths=set(git('diff-tree','--no-commit-id','--name-only','-r',APP_COMMIT).splitlines())
    expected_app_paths={f'src/web/public/locales/{l}.json' for l in LOCALES}|{'docs/CHANGELOG.md'}
    if app_paths!=expected_app_paths: fail(f'application commit path boundary mismatch: {sorted(app_paths^expected_app_paths)}')
    if git('rev-parse',REVIEW_BASE+':.github/workflows')!=git('rev-parse',APP_COMMIT+':.github/workflows'): fail('workflow subtree changed in application commit')
    changed_from_base=git('diff','--name-only',BASELINE,APP_COMMIT).splitlines()
    if any(p.startswith('.github/workflows/') for p in changed_from_base): fail('workflow path changed since frozen baseline')
    if any(p.startswith('src/') and '/locales/' not in p for p in changed_from_base): fail('non-catalog source path changed since frozen baseline')
    if '1,195 exact-hash-validated populated-catalog corrections across 275 source keys' not in show(APP29_COMMIT,'docs/CHANGELOG.md').decode('utf-8'): fail('changelog cumulative count mismatch')
    if git('rev-parse',REVIEW29_BASE+'^{tree}')!=REVIEW29_TREE or git('rev-parse',REVIEW29_BASE+':src')!=REVIEW29_SRC: fail('window29 review source/catalog pin changed')
    if git('rev-parse',APP29_COMMIT+'^')!=REVIEW29_BASE or git('rev-parse',APP29_COMMIT+'^{tree}')!=APP29_TREE: fail('window29 application parent/tree mismatch')
    app29_paths=set(git('diff-tree','--no-commit-id','--name-only','-r',APP29_COMMIT).splitlines())
    expected_app_paths={f'src/web/public/locales/{l}.json' for l in LOCALES}|{'docs/CHANGELOG.md'}
    if app29_paths!=expected_app_paths: fail(f'window29 application path boundary mismatch: {sorted(app29_paths^expected_app_paths)}')
    if git('rev-parse',REVIEW29_BASE+':.github/workflows')!=git('rev-parse',APP29_COMMIT+':.github/workflows'): fail('workflow subtree changed in window29 application commit')

    # Validate the 29 disjoint 25-key/300-cell manual windows.
    manual_ids=set(); source_ids=set(); manual_by={}; verdicts=collections.Counter()
    for w in range(1,30):
        d=MANUAL/f'window{w}'; inp=rows(d/'review-input.jsonl'); dec=rows(d/'review-decisions.jsonl'); dm={x['id']:x for x in dec}
        if len(inp)!=300 or len(dec)!=300 or len(dm)!=300 or set(dm)!={x['id'] for x in inp}: fail(f'window {w} row count/ID join mismatch')
        if w==27:
            m=json.loads((d/'manifest.json').read_text(encoding='utf-8'))
            if (m['headCommit'],m['tree'],m['sourceSubtreeTree'])!=('11e7971bc33513c7aad65f2831e1d474e541a5e0','97b609cdbf423f55d595a77220b7362b9fd3d8ef','ee5969020b2184b7a6179e8e7b9805041c782fb7'): fail('window27 review pins mismatch')
            if sha((d/'review-input.jsonl').read_bytes())!='8a4954b9d45056abafb1646eb547c3aeccaba2a57b359289ac929d15d0fc0f86': fail('window27 input hash mismatch')
            if sha((d/'review-decisions.jsonl').read_bytes())!='5404625d7ff6b26dbe557aee95e1716b4854c892c832cc2e384fbf554d4ed858': fail('window27 decision hash mismatch')
            if sha((d/'crossreview-plan.jsonl').read_bytes())!='c0fee30c06711138405301f4bd781fef1b12d3387a3bfd6f433a1ca457797c69': fail('window27 proposal hash mismatch')
        if w==28:
            m=json.loads((d/'manifest.json').read_text(encoding='utf-8'))
            if (m['headCommit'],m['tree'],m['sourceSubtreeTree'])!=(REVIEW_BASE,REVIEW_TREE,REVIEW_SRC): fail('window28 review pins mismatch')
            if sha((d/'review-input.jsonl').read_bytes())!='44b2c98fba43c0e3cffea0ad9e4cb14c7a844fcc0a11a2ad54751422f9ed3731': fail('window28 input hash mismatch')
            if sha((d/'review-decisions.jsonl').read_bytes())!='cc7b85e6324e04fb232691cbdab41fa9e649900f6bc7ffd8b4ce1d305233dd34': fail('window28 decision hash mismatch')
            if sha((d/'crossreview-plan.jsonl').read_bytes())!=CANDIDATE_SHA: fail('window28 proposal hash mismatch')
        if w==29:
            m=json.loads((d/'manifest.json').read_text(encoding='utf-8'))
            if (m['headCommit'],m['tree'],m['sourceSubtreeTree'])!=(REVIEW29_BASE,REVIEW29_TREE,REVIEW29_SRC): fail('window29 review pins mismatch')
            if sha((d/'review-input.jsonl').read_bytes())!='fc41b5f62ac2feaad4c5184d1d09d481b114703596f734804718d5a651942307': fail('window29 input hash mismatch')
            if sha((d/'review-decisions.jsonl').read_bytes())!='99c398c8439ed2d41870be80940ad5e0409e18d021e9e66d566bd863950375af': fail('window29 decision hash mismatch')
            if sha((d/'crossreview-plan.jsonl').read_bytes())!=CANDIDATE29_SHA: fail('window29 proposal hash mismatch')
        for r in inp:
            ident=r['id']
            if ident in manual_ids: fail(f'manual window overlap at {ident}')
            if r['locale'] not in LOCALES or ident!=f"{r['locale']}:{r['sourceId']}": fail(f'manual row ID mismatch {ident}')
            if sha(r['source'])!=r['sourceSha256'] or sha(r['target'])!=r['targetSha256']: fail(f'manual source/target hash mismatch {ident}')
            manual_ids.add(ident);source_ids.add(r['sourceId']);manual_by[ident]=(r,dm[ident]);verdicts[dm[ident]['verdict']]+=1
    if len(manual_ids)!=8700 or len(source_ids)!=725: fail('29-window coverage mismatch')
    if verdicts!=collections.Counter({'keep':7255,'correct':1189,'uncertain':256}): fail(f'manual verdict totals mismatch {verdicts}')

    # Reconcile every historical application ledger, held row, and the new window.
    old=rows(OLD/'applied-corrections.jsonl');w18=rows(W18/'applied-corrections.jsonl');w20=rows(W20/'applied-corrections.jsonl')
    w22=rows(W22/'applied-corrections-windows22-23.jsonl');realm=rows(W22/'applied-corrections-realm-window20.jsonl')
    w24=rows(W24/'applied-corrections-window24.jsonl');w25=rows(W25/'applied-corrections-window25.jsonl');w26=rows(W26/'applied-corrections-window26.jsonl')
    w27=rows(W27/'applied-corrections-window27.jsonl');w28=rows(APP/'applied-corrections-window28.jsonl');w29=rows(APP29/'applied-corrections-window29.jsonl');held=rows(OLD/'held-no-context.jsonl')
    applied=old+w18+w20+w22+realm+w24+w25+w26+w27+w28+w29
    applied_by={r['id']:r for r in applied};held_by={r['id']:r for r in held}
    sizes=[len(x) for x in (old,w18,w20,w22,realm,w24,w25,w26,w27,w28,w29,held)]
    if sizes!=[736,82,51,53,12,45,43,48,44,39,42,6]: fail(f'ledger row counts mismatch {sizes}')
    sets=[{r['id'] for r in x} for x in (old,w18,w20,w22,realm,w24,w25,w26,w27,w28,w29,held)]
    if any(sets[i]&sets[j] for i in range(len(sets)) for j in range(i+1,len(sets))): fail('application/hold ledgers overlap')
    if len(applied_by)!=1195 or len({r['sourceId'] for r in applied})!=275: fail('cumulative applied count/source key mismatch')
    if collections.Counter(r['locale'] for r in applied)!=collections.Counter(EXPECTED_LOCALE_COUNTS): fail('cumulative locale count mismatch')
    realm_ids={r['id'] for r in realm}
    manual_correct={i for i,(r,d) in manual_by.items() if d['verdict']=='correct'}
    manual_uncertain={i for i,(r,d) in manual_by.items() if d['verdict']=='uncertain'}
    if set(applied_by)|set(held_by)!=manual_correct|realm_ids: fail('manual correction/Realm disposition reconciliation mismatch')
    if len(manual_correct)!=1189 or len(manual_uncertain-realm_ids)!=244: fail('remaining uncertainty/manual correct count mismatch')

    # Verify window28 root review, application rows, and the unchanged contextless cells.
    root_plan=rows(APP/'root-apply-plan-window28.jsonl');root=rows(APP/'root-crossreview-decisions-window28.jsonl')
    application=rows(APP/'applied-corrections-window28.jsonl');uncertain_rows=rows(APP/'uncertain-review-rows.jsonl')
    root_summary=json.loads((APP/'root-crossreview-summary-window28.json').read_text(encoding='utf-8'))
    manifest=json.loads((APP/'manifest.json').read_text(encoding='utf-8'));ledger_summary=json.loads((APP/'application-ledger-summary.json').read_text(encoding='utf-8'))
    if manifest.get('evidenceFiles'):
        evidence_files={p.name:sha(p.read_bytes()) for p in APP.iterdir() if p.is_file() and p.name not in {'manifest.json','SHA256SUMS'}}
        if manifest.get('evidenceFiles')!=evidence_files: fail('window28 manifest evidence-file hashes mismatch')
        if manifest.get('verificationReport',{}).get('sha256')!=sha((APP/'verification.json').read_bytes()): fail('window28 verification-report hash mismatch')
        checksum_rows={}
        for line in (APP/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
            digest,name=line.split('  ',1);checksum_rows[name]=digest
        checksum_expected={p.name:sha(p.read_bytes()) for p in APP.iterdir() if p.is_file() and p.name!='SHA256SUMS'}
        if checksum_rows!=checksum_expected: fail('window28 SHA256SUMS inventory/hash mismatch')
    if (sha((APP/'root-apply-plan-window28.jsonl').read_bytes()),sha((APP/'root-crossreview-decisions-window28.jsonl').read_bytes()),sha((APP/'root-crossreview-summary-window28.json').read_bytes()))!=(ROOT_PLAN_SHA,ROOT_LEDGER_SHA,ROOT_SUMMARY_SHA): fail('window28 root evidence hash mismatch')
    if len(root_plan)!=39 or len(root)!=39 or len(application)!=39 or len(uncertain_rows)!=24: fail('window28 review/application/uncertain count mismatch')
    if manifest.get('applicationCommit')!=APP_COMMIT or manifest.get('applicationTree')!=APP_TREE or manifest.get('applicationParent')!=REVIEW_BASE: fail('window28 application commit/tree manifest mismatch')
    if (manifest.get('reviewBaseHead'),manifest.get('reviewBaseTree'),manifest.get('reviewSourceSubtree'))!=(REVIEW_BASE,REVIEW_TREE,REVIEW_SRC): fail('window28 review pin manifest mismatch')
    if manifest.get('rootCrossReview',{}).get('ledgerSha256')!=ROOT_LEDGER_SHA or manifest.get('rootCrossReview',{}).get('applyPlanSha256')!=ROOT_PLAN_SHA: fail('window28 root hash manifest mismatch')
    if manifest.get('applicationLedger',{}).get('sha256')!=sha((APP/'applied-corrections-window28.jsonl').read_bytes()): fail('window28 app ledger manifest hash mismatch')
    if ledger_summary.get('sha256')!=manifest['applicationLedger']['sha256'] or ledger_summary.get('rows')!=39 or ledger_summary.get('uniqueSourceKeys')!=5: fail('window28 app summary mismatch')
    if ledger_summary.get('byLocale')!=dict(sorted(collections.Counter(r['locale'] for r in application).items())): fail('window28 per-locale app summary mismatch')
    post=json.loads((APP/'post-apply-verification.json').read_text(encoding='utf-8'))
    if post.get('result')!='PASS' or post.get('baseHead')!=REVIEW_BASE or post.get('applicationRows')!=39 or post.get('changedCells')!=39: fail('window28 post-apply report pin/count mismatch')
    if post.get('candidatePlanSha256')!=CANDIDATE_SHA or post.get('rootLedgerSha256')!=ROOT_LEDGER_SHA or post.get('rootApplyPlanSha256')!=ROOT_PLAN_SHA: fail('window28 post-apply provenance mismatch')
    if root_summary.get('candidateRows')!=39 or root_summary.get('applyCount')!=39 or root_summary.get('decisionCounts')!={'accepted':39,'held':0,'refined':0}: fail('window28 root disposition summary mismatch')
    root_by={r['id']:r for r in root};plan_by={r['id']:r for r in root_plan};app_by={r['id']:r for r in application}
    if set(root_by)!=set(app_by) or set(plan_by)!=set(app_by): fail('window28 root/application row join mismatch')
    manual28={r['id']:r for r in rows(MANUAL/'window28'/'review-input.jsonl')};decisions28={r['id']:r for r in rows(MANUAL/'window28'/'review-decisions.jsonl')};candidates={r['id']:r for r in rows(MANUAL/'window28'/'crossreview-plan.jsonl')}
    placeholder=lambda s:collections.Counter(re.findall(r'{[^{}]+}',s))
    for ident,a in app_by.items():
        r=root_by[ident];p=plan_by[ident];i=manual28[ident];d=decisions28[ident];c=candidates[ident]
        if r['disposition']!='accepted': fail(f'window28 target not root accepted {ident}')
        if d.get('verdict')!='correct' or d.get('target')!=a['proposedTarget']: fail(f'window28 decision/proposal mismatch {ident}')
        if (a['source'],a['sourceSha256'],a['catalogKey'],a['catalogPath'],a['currentTarget'],a['currentTargetSha256'])!=(r['source'],r['sourceSha256'],r['catalogKey'],r['catalogPath'],r['currentTarget'],r['currentTargetSha256']): fail(f'window28 root current/source mismatch {ident}')
        if (a['source'],a['sourceSha256'],a['catalogKey'],a['catalogPath'],a['currentTarget'],a['currentTargetSha256'])!=(i['source'],i['sourceSha256'],i['catalogKey'],i['catalogPath'],i['target'],i['targetSha256']): fail(f'window28 manual current/source mismatch {ident}')
        if (a['proposedTarget'],a['proposedTargetSha256'])!=(c['proposedTarget'],c['proposedTargetSha256']): fail(f'window28 candidate plan mismatch {ident}')
        if (a['appliedTarget'],a['appliedTargetSha256'])!=(r['rootTarget'],r['rootTargetSha256']): fail(f'window28 root final target mismatch {ident}')
        if p.get('rootTarget')!=a['appliedTarget'] or p.get('rootTargetSha256')!=a['appliedTargetSha256'] or p.get('currentTarget')!=a['currentTarget'] or p.get('currentTargetSha256')!=a['currentTargetSha256']: fail(f'window28 apply plan exact target mismatch {ident}')
        if (p.get('candidatePlanSha256'),p.get('rootLedgerSha256'),p.get('currentPrHead'),p.get('currentPrTree'),p.get('currentSourceSubtreeTree'))!=(CANDIDATE_SHA,ROOT_LEDGER_SHA,REVIEW_BASE,REVIEW_TREE,REVIEW_SRC): fail(f'window28 apply plan pin mismatch {ident}')
        if any(sha(a[v])!=a[h] for v,h in [('source','sourceSha256'),('currentTarget','currentTargetSha256'),('proposedTarget','proposedTargetSha256'),('appliedTarget','appliedTargetSha256')]): fail(f'window28 row hash mismatch {ident}')
        if placeholder(a['source'])!=placeholder(a['appliedTarget']): fail(f'window28 placeholder mismatch {ident}')
        if a['sourceCallsites']!=r['sourceCallsites']: fail(f'window28 caller join mismatch {ident}')
        for call in a['sourceCallsites']:
            raw=show(REVIEW_BASE,call['path'])
            if sha(raw)!=call['fileSha256']: fail(f'window28 caller file hash mismatch {call["path"]}')
            line=raw.decode('utf-8').splitlines()[call['line']-1].strip()
            if line!=call['lineText'] or sha(line)!=call['lineTextSha256']: fail(f'window28 caller line mismatch {call["path"]}:{call["line"]}')
    if len({r['sourceId'] for r in application})!=5: fail('window28 source-key count mismatch')
    uncertain_by={r['id']:r for r in uncertain_rows}
    expected_uncertain={f'{l}:{sid}' for l in LOCALES for sid in ('src_fd96813fb2cc612b','src_fe60c7ad5a5617f7')}
    if set(uncertain_by)!=expected_uncertain: fail('window28 uncertain ledger IDs mismatch')
    for ident,u in uncertain_by.items():
        i=manual28[ident];d=decisions28[ident]
        if d.get('verdict')!='uncertain' or u.get('currentTarget')!=i['target'] or u.get('currentTargetSha256')!=i['targetSha256'] or u.get('reason')!=d['reason']: fail(f'window28 uncertain ledger join mismatch {ident}')

    # Verify window29 root review and exact-hash application.
    root29_plan=rows(APP29/'root-apply-plan-window29.jsonl')
    root29=rows(APP29/'root-crossreview-decisions-window29.jsonl')
    application29=rows(APP29/'applied-corrections-window29.jsonl')
    uncertain29=rows(APP29/'uncertain-review-rows.jsonl')
    root29_summary=json.loads((APP29/'root-crossreview-summary-window29.json').read_text(encoding='utf-8'))
    manifest29=json.loads((APP29/'manifest.json').read_text(encoding='utf-8'))
    ledger29=json.loads((APP29/'application-ledger-summary.json').read_text(encoding='utf-8'))
    post29=json.loads((APP29/'post-apply-verification.json').read_text(encoding='utf-8'))
    if sha((APP29/'root-apply-plan-window29.jsonl').read_bytes())!=ROOT29_PLAN_SHA: fail('window29 root apply plan hash mismatch')
    if sha((APP29/'root-crossreview-decisions-window29.jsonl').read_bytes())!=ROOT29_LEDGER_SHA: fail('window29 root cross-review ledger hash mismatch')
    if sha((APP29/'root-crossreview-summary-window29.json').read_bytes())!=ROOT29_SUMMARY_SHA: fail('window29 root summary hash mismatch')
    if len(root29_plan)!=42 or len(root29)!=42 or len(application29)!=42 or uncertain29: fail('window29 review/application/uncertain count mismatch')
    if (manifest29.get('reviewBaseHead'),manifest29.get('reviewBaseTree'),manifest29.get('reviewSourceSubtree'))!=(REVIEW29_BASE,REVIEW29_TREE,REVIEW29_SRC): fail('window29 review pin manifest mismatch')
    if (manifest29.get('applicationCommit'),manifest29.get('applicationTree'),manifest29.get('applicationParent'))!=(APP29_COMMIT,APP29_TREE,REVIEW29_BASE): fail('window29 app commit/tree manifest mismatch')
    if manifest29.get('candidatePlanSha256')!=CANDIDATE29_SHA or manifest29.get('rootCrossReview',{}).get('ledgerSha256')!=ROOT29_LEDGER_SHA or manifest29.get('rootCrossReview',{}).get('applyPlanSha256')!=ROOT29_PLAN_SHA: fail('window29 candidate/root manifest hashes mismatch')
    if manifest29.get('applicationLedger',{}).get('sha256')!=sha((APP29/'applied-corrections-window29.jsonl').read_bytes()): fail('window29 app ledger manifest hash mismatch')
    if ledger29.get('sha256')!=manifest29['applicationLedger']['sha256'] or ledger29.get('rows')!=42 or ledger29.get('uniqueSourceKeys')!=5: fail('window29 application summary mismatch')
    if ledger29.get('byLocale')!=dict(sorted(collections.Counter(r['locale'] for r in application29).items())): fail('window29 per-locale application summary mismatch')
    if root29_summary.get('reviewedCandidates')!=42 or root29_summary.get('applyCount')!=42 or root29_summary.get('accepted')!=38 or root29_summary.get('refined')!=4 or root29_summary.get('held')!=0: fail('window29 root disposition summary mismatch')
    if post29.get('result')!='PASS' or post29.get('baseHead')!=REVIEW29_BASE or post29.get('applicationCommit')!=APP29_COMMIT or post29.get('applicationRows')!=42 or post29.get('changedCells')!=42: fail('window29 post-apply report pin/count mismatch')
    if (post29.get('candidatePlanSha256'),post29.get('rootLedgerSha256'),post29.get('rootApplyPlanSha256'))!=(CANDIDATE29_SHA,ROOT29_LEDGER_SHA,ROOT29_PLAN_SHA): fail('window29 post-apply provenance mismatch')
    root29_by={r['id']:r for r in root29}; plan29_by={r['id']:r for r in root29_plan}; app29_by={r['id']:r for r in application29}
    if set(root29_by)!=set(app29_by) or set(plan29_by)!=set(app29_by): fail('window29 root/application ID join mismatch')
    manual29={r['id']:r for r in rows(MANUAL/'window29'/'review-input.jsonl')}
    decisions29={r['id']:r for r in rows(MANUAL/'window29'/'review-decisions.jsonl')}
    candidates29={r['id']:r for r in rows(MANUAL/'window29'/'crossreview-plan.jsonl')}
    for ident,a in app29_by.items():
        r=root29_by[ident]; p=plan29_by[ident]; i=manual29[ident]; d=decisions29[ident]; c=candidates29[ident]
        if r['disposition'] not in {'accepted','refined'}: fail(f'window29 row not approved {ident}')
        if d.get('verdict')!='correct' or d.get('target')!=c['proposedTarget']: fail(f'window29 decision/candidate mismatch {ident}')
        if (a['source'],a['sourceSha256'],a['catalogKey'],a['catalogPath'],a['currentTarget'],a['currentTargetSha256'])!=(r['source'],r['sourceSha256'],r['catalogKey'],r['catalogPath'],r['currentTarget'],r['currentTargetSha256']): fail(f'window29 root current/source mismatch {ident}')
        if (a['source'],a['sourceSha256'],a['catalogKey'],a['catalogPath'],a['currentTarget'],a['currentTargetSha256'])!=(i['source'],i['sourceSha256'],i['catalogKey'],i['catalogPath'],i['target'],i['targetSha256']): fail(f'window29 manual current/source mismatch {ident}')
        if (a['proposedTarget'],a['proposedTargetSha256'])!=(c['proposedTarget'],c['proposedTargetSha256']): fail(f'window29 candidate target mismatch {ident}')
        if (a['appliedTarget'],a['appliedTargetSha256'])!=(r['rootTarget'],r['rootTargetSha256']): fail(f'window29 root final target mismatch {ident}')
        if (p.get('rootTarget'),p.get('rootTargetSha256'),p.get('currentTarget'),p.get('currentTargetSha256'))!=(a['appliedTarget'],a['appliedTargetSha256'],a['currentTarget'],a['currentTargetSha256']): fail(f'window29 apply plan exact target mismatch {ident}')
        if (p.get('candidatePlanSha256'),p.get('currentPrHead'),p.get('currentPrTree'),p.get('currentSourceSubtreeTree'))!=(CANDIDATE29_SHA,REVIEW29_BASE,REVIEW29_TREE,REVIEW29_SRC): fail(f'window29 apply plan pin mismatch {ident}')
        if any(sha(a[v])!=a[h] for v,h in [('source','sourceSha256'),('currentTarget','currentTargetSha256'),('proposedTarget','proposedTargetSha256'),('appliedTarget','appliedTargetSha256')]): fail(f'window29 row hash mismatch {ident}')
        if placeholder(a['source'])!=placeholder(a['appliedTarget']): fail(f'window29 placeholder mismatch {ident}')
        if a['sourceCallsites']!=r['sourceCallsites'] or a['sourceCallsites']!=i['sourceCallsites']: fail(f'window29 caller join mismatch {ident}')
        for call in a['sourceCallsites']:
            raw=show(REVIEW29_BASE,call['path'])
            if sha(raw)!=call['fileSha256']: fail(f'window29 caller file hash mismatch {call["path"]}')
            line=raw.decode('utf-8').splitlines()[call['line']-1].strip()
            if line!=call['lineText'] or sha(line)!=call['lineTextSha256']: fail(f'window29 caller line mismatch {call["path"]}:{call["line"]}')
    if len({r['sourceId'] for r in application29})!=5: fail('window29 source-key count mismatch')

    # Exact cumulative census from the frozen populated-catalog baseline.
    changed_by={};catalog_hash={}
    for locale in LOCALES:
        rel=f'src/web/public/locales/{locale}.json';base=unique(show(BASELINE,rel),f'{BASELINE}:{rel}');final_raw=show(APP29_COMMIT,rel);final=unique(final_raw,f'{APP29_COMMIT}:{rel}')
        if (REPO/rel).read_bytes()!=final_raw: fail(f'worktree catalog differs from application commit: {locale}')
        if len(base)!=6169 or len(final)!=6169 or set(base)!=set(final): fail(f'catalog shape mismatch {locale}')
        if any(not isinstance(v,str) or not v for v in final.values()): fail(f'empty/non-string catalog value {locale}')
        expected={r['catalogKey'] for r in applied if r['locale']==locale};changed={k for k in base if base[k]!=final[k]}
        if changed!=expected: fail(f'changed key ledger mismatch {locale}: {sorted(changed^expected)}')
        for r in applied:
            if r['locale']==locale and final.get(r['catalogKey'])!=applied_target(r): fail(f'final target mismatch {r["id"]}')
        changed_by[locale]=len(changed);catalog_hash[rel]=sha(final_raw)
    if sum(changed_by.values())!=1195: fail('cumulative catalog census does not equal 1,195')

    # Confirm the frozen formal accumulator still has no overlap with manual/application evidence.
    sys.path.insert(0,str(BASE/'translation-tools'))
    import strict_populated_semantic_review_runner_core as core
    bm=json.loads((BUNDLE/'manifest.json').read_text(encoding='utf-8'))
    bundle=core.load_bundle(BUNDLE,sha((BUNDLE/'manifest.json').read_bytes()),sha((BUNDLE/'batches.json').read_bytes()),bm['headCommit'],bm['tree'],'snapetech-org/slskdN','slskdn',BASE/'slskdn-populated-review-4c2b-20261101'/'snapshot-repo')
    fs=core.scan_results(bundle,RESULTS);formal={d['id'] for x in fs['valid'].values() for d in x['decisions']}
    if fs['invalid'] or len(fs['valid'])!=150 or len(fs['missing'])!=1951 or len(formal)!=4800: fail('formal accumulator count/validity mismatch')
    if formal&manual_ids or formal&set(applied_by): fail('formal/manual/application overlap')
    if git('rev-parse',head+':src')!=git('rev-parse',APP29_COMMIT+':src'): fail('later commit changed application source/catalog subtree')

    if manifest29.get('evidenceFiles'):
        evidence_files={p.name:sha(p.read_bytes()) for p in APP29.iterdir() if p.is_file() and p.name not in {'manifest.json','SHA256SUMS'}}
        if manifest29.get('evidenceFiles')!=evidence_files: fail('window29 manifest evidence-file hashes mismatch')
        if manifest29.get('verificationReport',{}).get('sha256')!=sha((APP29/'verification.json').read_bytes()): fail('window29 verification-report hash mismatch')
        checksum_rows={}
        for line in (APP29/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
            digest,name=line.split('  ',1);checksum_rows[name]=digest
        checksum_expected={p.name:sha(p.read_bytes()) for p in APP29.iterdir() if p.is_file() and p.name!='SHA256SUMS'}
        if checksum_rows!=checksum_expected: fail('window29 SHA256SUMS inventory/hash mismatch')
    manual_hashes={n:sha((MANUAL/'window29'/n).read_bytes()) for n in ('review-input.jsonl','review-decisions.jsonl','crossreview-plan.jsonl','manifest.json')}
    per28=collections.Counter(r['locale'] for r in application)
    output={'result':'PASS','pullRequest':409,'livePrState':state['state'],'livePrDraft':state['isDraft'],'pushState':push_state,
      'reviewBaseHead':REVIEW_BASE,'reviewBaseTree':REVIEW_TREE,'reviewSourceSubtree':REVIEW_SRC,
      'applicationCommit':APP29_COMMIT,'applicationTree':APP29_TREE,'applicationParent':REVIEW29_BASE,'currentHead':head,'currentTree':tree,'currentRemoteHead':remote,
      'manualCoverage':{'windows':29,'sourceKeys':725,'cells':8700,'verdicts':dict(verdicts),'formalOverlap':0,'manualWindowOverlap':0},
      'window28RootReview':{'rows':39,'acceptedAsProposed':39,'refined':0,'held':0,'semanticConfidence':'moderate','localeQualityConfidence':'moderate','nativeSpeakerApproval':False,'planSha256':ROOT_PLAN_SHA,'ledgerSha256':ROOT_LEDGER_SHA},
      'window29RootReview':{'rows':42,'acceptedAsProposed':38,'refinedAndAccepted':4,'held':0,'semanticConfidence':'moderate','localeQualityConfidence':'moderate','nativeSpeakerApproval':False,'candidatePlanSha256':CANDIDATE29_SHA,'ledgerSha256':ROOT29_LEDGER_SHA,'applyPlanSha256':ROOT29_PLAN_SHA,'summarySha256':ROOT29_SUMMARY_SHA},
      'application':{'previousApplied':1153,'newApplied':42,'totalApplied':1195,'uniqueSourceKeys':275,'heldNoContext':6,'uncertainRemaining':244,'unreviewedCells':58380,'byLocale':EXPECTED_LOCALE_COUNTS,'window29ByLocale':dict(sorted(collections.Counter(r['locale'] for r in application29).items())),'window29UncertainRows':0},
      'catalogCensus':{'locales':12,'keysPerLocale':6169,'totalValues':74028,'changedCellsSinceFrozenBaseline':1195,'changedCellsByLocale':changed_by,'catalogFileSha256':catalog_hash},
      'formalAccumulator':{'validJobs':150,'missingJobs':1951,'invalidJobs':0,'cells':4800},'window29Rows':42,'window29SourceCallsitesRechecked':sum(len(r['sourceCallsites']) for r in application29),
      'workflowChanges':0,'nonCatalogSourceChanges':0,'applicationCommitPaths':sorted(app29_paths),'nativeSpeakerReview':'outstanding','headedBrowserReview':'outstanding','testsBuildCiReleaseOrTag':'not run','window29ManualEvidenceHashes':manual_hashes}
    out=json.dumps(output,ensure_ascii=False,indent=2)+'\n'
    if '--no-write' not in sys.argv[1:]: (APP29/'verification.json').write_text(out,encoding='utf-8')
    print(out,end='')
if __name__=='__main__':main()
