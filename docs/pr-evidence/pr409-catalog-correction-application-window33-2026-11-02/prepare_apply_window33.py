#!/usr/bin/env python3
import collections, hashlib, json, re, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
MANUAL = REPO / 'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01/window33'
PACKET = MANUAL / 'review-packet'
INDEP = MANUAL / 'independent-review'
ROOTPKT = MANUAL / 'root-cross-review'
HEAD = '0abf10ae9f49d27d7cfef823cfe5d70765ee29f4'
TREE = '8ac49de1cde7dc242484eadc597781819e26e1d2'
SRC = '594e56c3f439bad476b1bd57e0de1665c62fa1bb'
REMOTE_REF = 'refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'
INPUT_SHA = '9b919f98102d88f2c8de56b23a187531453ed38eac9034657b9f968b8412bcec'
REVIEW_SHA = '4484dd487cfbfd75b2e9e9e4895b2811af6c76f6de65de241050b0d90be4d2c3'
CANDIDATE_SHA = '906c3e8bb45b08e9bc9d26d9ac286def387a132c741e4e7f0be68deb0094df06'
INDEP_SHA = '647fcf26d3029795ca7e7763df68448a72c474f47db55d9db989360066e469b9'
ROOT_SHA = '2c4ca97f6df7cd87e4ba5e6bbec52ec135ebd12578eec163f8c398365b5e3dc0'
LOCALES = ['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
def sha(v): return hashlib.sha256(v if isinstance(v, bytes) else v.encode('utf-8')).hexdigest()
def read(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args], text=True).strip()
def show(commit, path): return subprocess.check_output(['git','-C',str(REPO),'show',f'{commit}:{path}'])
def fail(message): raise SystemExit('FAIL: '+message)
def unique(rows, label):
    result={r['id']:r for r in rows}
    if len(result)!=len(rows): fail(f'duplicate IDs in {label}')
    return result
# Frozen review evidence must be intact before planning any catalog writes.
for directory in (PACKET, INDEP, ROOTPKT):
    if subprocess.run(['sha256sum','-c','SHA256SUMS.txt'],cwd=directory,capture_output=True,text=True).returncode:
        fail(f'checksum mismatch in {directory}')
input_path=PACKET/'review-input.jsonl'; review_path=PACKET/'review-decisions.jsonl'; candidate_path=PACKET/'crossreview-plan.jsonl'
independent_path=INDEP/'independent-decisions.jsonl'; root_path=ROOTPKT/'root-disposition-ledger.jsonl'
for path, expected in ((input_path,INPUT_SHA),(review_path,REVIEW_SHA),(candidate_path,CANDIDATE_SHA),(independent_path,INDEP_SHA),(root_path,ROOT_SHA)):
    if sha(path.read_bytes())!=expected: fail(f'review artifact hash mismatch: {path.name}')
manifest=json.loads((PACKET/'manifest.json').read_text(encoding='utf-8'))
if (manifest['headCommit'],manifest['tree'],manifest['sourceSubtreeTree'])!=(HEAD,TREE,SRC): fail('frozen manifest pin mismatch')
inputs=unique(read(input_path),'input'); reviews=unique(read(review_path),'review'); candidates=unique(read(candidate_path),'candidate'); independent=unique(read(independent_path),'independent'); roots=unique(read(root_path),'root')
if (len(inputs),len(reviews),len(candidates),len(independent),len(roots))!=(274,274,41,41,41): fail('review row counts mismatch')
if set(candidates)!=set(independent) or set(candidates)!=set(roots): fail('cross-review ID sets differ')
manual_counts=collections.Counter(r['verdict'] for r in reviews.values())
root_counts=collections.Counter(r['rootDisposition'] for r in roots.values())
if manual_counts!=collections.Counter({'keep':222,'correct':41,'uncertain':11}): fail(f'manual dispositions mismatch: {dict(manual_counts)}')
if root_counts!=collections.Counter({'accept':40,'refine':1}): fail(f'root dispositions mismatch: {dict(root_counts)}')
pr=json.loads(subprocess.check_output(['gh','api','repos/snapetech-org/slskdN/pulls/409','--jq','{head:.head.sha,headRef:.head.ref,state:.state,draft:.draft}'],text=True))
head,tree,src=git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}'),git('rev-parse','HEAD:src/web/src')
remote=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin',REMOTE_REF],text=True).split()[0]
if pr!={'head':HEAD,'headRef':'codex/slskdn-oidc-tooltip-localization-20261030','state':'open','draft':True}: fail(f'live PR state/head changed: {pr}')
if (head,tree,src,remote)!=(HEAD,TREE,SRC,HEAD): fail(f'base/local/remote pin changed: {(head,tree,src,remote)}')
if git('status','--porcelain'):
    changed=git('status','--porcelain').splitlines()
    if any(not x.endswith('docs/pr-evidence/pr409-manual-semantic-review-2026-11-01/window33') and 'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01/window33/' not in x and 'docs/pr-evidence/pr409-catalog-correction-application-window33-2026-11-02/' not in x for x in changed):
        fail('unexpected worktree changes before application planning')
# Candidate root-final values must agree with all frozen source/current/proposal hashes and caller pins.
apply=[]; caller_count=0; locale_keys=collections.defaultdict(set)
pattern=re.compile(r'\{[^{}]+\}')
for ident, root in roots.items():
    row=inputs[ident]; candidate=candidates[ident]; independent_row=independent[ident]; decision=reviews[ident]
    locale=root['locale']; key=root['catalogKey']; target=root['rootFinalTarget']
    if root['window']!=33 or root['pins']!={'prHead':HEAD,'prTree':TREE,'sourceSubtreeTree':SRC}: fail(f'root pin mismatch {ident}')
    if (root['candidatePlanSha256'],root['independentLedgerSha256'])!=(CANDIDATE_SHA,INDEP_SHA): fail(f'root evidence reference mismatch {ident}')
    if decision['verdict']!='correct' or row['locale']!=locale or row['catalogKey']!=key or row['catalogPath']!=root['catalogPath'] or row['sourceId']!=root['sourceId']: fail(f'cell coordinates/review verdict mismatch {ident}')
    if (root['exactSource'],root['sourceSha256'],root['currentTarget'],root['currentTargetSha256'])!=(row['source'],row['sourceSha256'],row['target'],row['targetSha256']): fail(f'source/current mismatch {ident}')
    if sha(root['exactSource'])!=root['sourceSha256'] or sha(root['currentTarget'])!=root['currentTargetSha256']: fail(f'source/current hash mismatch {ident}')
    if (candidate['proposedTarget'],candidate['proposedTargetSha256'])!=(root['proposedTarget'],root['proposedTargetSha256']): fail(f'candidate proposal mismatch {ident}')
    if sha(root['proposedTarget'])!=root['proposedTargetSha256']: fail(f'candidate hash mismatch {ident}')
    if independent_row['sourceSha256']!=root['sourceSha256'] or independent_row['currentTargetSha256']!=root['currentTargetSha256'] or independent_row['proposedTargetSha256']!=root['proposedTargetSha256']: fail(f'independent review hash mismatch {ident}')
    if root['rootDisposition'] not in {'accept','refine'} or root['nativeSpeakerApproved'] is not False: fail(f'unsupported root disposition {ident}')
    if root['rootDisposition']=='accept' and (target!=root['proposedTarget'] or root['rootFinalTargetSha256']!=root['proposedTargetSha256']): fail(f'accepted target differs from proposal {ident}')
    if sha(target)!=root['rootFinalTargetSha256'] or not target: fail(f'root-final target hash/empty {ident}')
    if collections.Counter(pattern.findall(target))!=collections.Counter(pattern.findall(row['source'])): fail(f'placeholder mismatch {ident}')
    for literal in row.get('protectedLiterals',[]):
        if target.count(literal)!=row['source'].count(literal): fail(f'protected literal mismatch {ident}:{literal}')
    if root['sourceCallsites']!=row.get('sourceCallsites',[]) or root['sourceContexts']!=row.get('sourceContexts',[]): fail(f'caller/context mismatch {ident}')
    for caller in row.get('sourceCallsites',[]):
        raw=show(HEAD,caller['path']); lines=raw.decode('utf-8').splitlines(); line=lines[caller['line']-1].strip()
        if sha(raw)!=caller['fileSha256'] or line!=caller['lineText'] or sha(line)!=caller['lineTextSha256']: fail(f'caller pin mismatch {ident}:{caller["path"]}:{caller["line"]}')
        caller_count+=1
    raw=show(HEAD,root['catalogPath']); catalog=json.loads(raw.decode('utf-8'))
    if sha(raw)!=manifest['currentCatalogFileSha256'][locale] or catalog.get(key)!=row['target'] or sha(catalog[key])!=row['targetSha256']: fail(f'current catalog pin/value mismatch {ident}')
    locale_keys[locale].add(key)
    apply.append({'schemaVersion':1,'window':33,'id':ident,'sourceId':root['sourceId'],'locale':locale,'catalogPath':root['catalogPath'],'catalogKey':key,'source':row['source'],'sourceSha256':row['sourceSha256'],'oldTarget':row['target'],'oldTargetSha256':row['targetSha256'],'newTarget':target,'newTargetSha256':root['rootFinalTargetSha256'],'rootDisposition':root['rootDisposition'],'rootRationale':root['rootRationale'],'candidateTarget':candidate['proposedTarget'],'reviewInputSha256':INPUT_SHA,'reviewDecisionLedgerSha256':REVIEW_SHA,'candidatePlanSha256':CANDIDATE_SHA,'rootLedgerSha256':ROOT_SHA,'independentLedgerSha256':INDEP_SHA,'baseHead':HEAD,'baseTree':TREE,'baseSourceSubtreeTree':SRC,'baseCatalogFileSha256':manifest['currentCatalogFileSha256'][locale],'sourceCallsites':row.get('sourceCallsites',[]),'sourceContexts':row.get('sourceContexts',[]),'nativeSpeakerApproved':False})
apply.sort(key=lambda r:(LOCALES.index(r['locale']),r['sourceId']))
plan_bytes=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in apply).encode('utf-8')
(ROOT/'root-apply-plan-window33.jsonl').write_bytes(plan_bytes)
# Freeze the eleven context-mismatched uncertain rows for explicit unchanged-cell verification.
held=[]
for ident, decision in reviews.items():
    if decision['verdict']!='uncertain': continue
    row=inputs[ident]; locale=row['locale']; raw=show(HEAD,row['catalogPath']); catalog=json.loads(raw.decode('utf-8'))
    if catalog.get(row['catalogKey'])!=row['target'] or sha(row['target'])!=row['targetSha256']: fail(f'held cell differs at base {ident}')
    if row.get('sourceCallsites') or row.get('sourceContexts'): fail(f'uncertain context-mismatch row unexpectedly has callers {ident}')
    held.append({'schemaVersion':1,'window':33,'id':ident,'sourceId':row['sourceId'],'locale':locale,'catalogPath':row['catalogPath'],'catalogKey':row['catalogKey'],'source':row['source'],'sourceSha256':row['sourceSha256'],'currentTarget':row['target'],'currentTargetSha256':row['targetSha256'],'reviewDisposition':'hold','reason':decision['reason'],'sourceCallsites':row.get('sourceCallsites',[]),'sourceContexts':row.get('sourceContexts',[]),'baseHead':HEAD,'baseTree':TREE,'baseCatalogFileSha256':manifest['currentCatalogFileSha256'][locale],'unchanged':True})
if len(held)!=11: fail(f'held row count mismatch: {len(held)}')
held.sort(key=lambda r:(LOCALES.index(r['locale']),r['sourceId']))
held_bytes=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in held).encode('utf-8')
(ROOT/'held-context-rows-window33.jsonl').write_bytes(held_bytes)
pre={'result':'READY_TO_APPLY','window':33,'pr':409,'livePrState':'OPEN','livePrDraft':True,'head':head,'tree':tree,'sourceSubtreeTree':src,'remoteHead':remote,'reviewInputSha256':INPUT_SHA,'reviewDecisionLedgerSha256':REVIEW_SHA,'candidatePlanSha256':CANDIDATE_SHA,'independentReviewLedgerSha256':INDEP_SHA,'rootDispositionLedgerSha256':ROOT_SHA,'applyPlanSha256':sha(plan_bytes),'heldRowsSha256':sha(held_bytes),'cellsToApply':len(apply),'acceptedAsProposed':root_counts['accept'],'refinedAndAccepted':root_counts['refine'],'heldContextMismatch':len(held),'callerPinsRechecked':caller_count,'localeFilesPinned':len(manifest['currentCatalogFileSha256']),'allOldValuesMatchLiveCatalog':True,'allFinalHashesPlaceholdersAndProtectedLiteralsPass':True,'heldRowsMatchCurrentCatalogAndHaveNoCallers':True,'nativeSpeakerApproved':False}
(ROOT/'application-preflight-window33.json').write_text(json.dumps(pre,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(pre,ensure_ascii=False,indent=2))
