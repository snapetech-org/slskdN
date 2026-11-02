#!/usr/bin/env python3
"""Verify W35 root/independent ledgers and emit an exact apply plan in scratch."""
import collections, hashlib, json, re, subprocess
from pathlib import Path

SCRATCH = Path('/mnt/disks/scratch/task-scratch/slskdn-manual-review-window35-91727326-20261102')
ROOT_REVIEW = Path('/mnt/disks/scratch/task-scratch/slskdn-root-crossreview-window35-91727326-20261102')
INDEPENDENT = SCRATCH/'independent-review'
REPO = Path('/mnt/disks/scratch/task-worktrees/localization-20261102/slskdn-pr409-w35-review')
BASE = '917273260c49cca1c14576a0720fc84998d2846d'
TREE = '1cdd8c831d224a5706ac6f3e465add4fd249d2be'
SOURCE_TREE = '594e56c3f439bad476b1bd57e0de1665c62fa1bb'
REMOTE_REF = 'refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'
ROOT_SHA = '9370973a90aaef1e6a597a4aa31d6bd21fedd4b7f8ded71f4d93ee0533d0f749'
INDEPENDENT_SHA = '6053ad16c8c19ecccfcfb330987810b6f3fd30c19538b67e48488195e190a36f'
PACKET_SHA = '938f53404562111e77d388336c8756a21f90fb65323650164cb47c3ecbbc7b0f'
DECISION_SHA = 'f8cab36f2d4bb8b059f01920a8b64cd12e4569e720f55f539b7bacb6ecfac069'
LOCALES = ['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']


def sha(value): return hashlib.sha256(value if isinstance(value,bytes) else value.encode('utf-8')).hexdigest()
def read_jsonl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args])
def git_text(*args): return git(*args).decode('utf-8').strip()
def require(ok, message):
    if not ok: raise SystemExit('FAIL: '+message)
def blob(commit,path): return git('show',f'{commit}:{path}')
def verify_sums(directory):
    r=subprocess.run(['sha256sum','-c','SHA256SUMS.txt'],cwd=directory,capture_output=True,text=True)
    require(r.returncode==0,f'checksum file failed for {directory}: {r.stderr or r.stdout}')

verify_sums(SCRATCH)
verify_sums(ROOT_REVIEW)
verify_sums(INDEPENDENT)
require(sha((ROOT_REVIEW/'root-crossreview.jsonl').read_bytes())==ROOT_SHA,'root ledger SHA changed')
require(sha((INDEPENDENT/'independent-review.jsonl').read_bytes())==INDEPENDENT_SHA,'independent ledger SHA changed')
require(sha((SCRATCH/'crossreview-plan.jsonl').read_bytes())==PACKET_SHA,'manual candidate packet SHA changed')
require(sha((SCRATCH/'review-decisions.jsonl').read_bytes())==DECISION_SHA,'manual decision ledger SHA changed')
manifest=json.loads((SCRATCH/'manifest.json').read_text(encoding='utf-8'))
require((manifest['headCommit'],manifest['tree'],manifest['sourceSubtreeTree'])==(BASE,TREE,SOURCE_TREE),'frozen W35 manifest pin differs')
require(git_text('rev-parse','HEAD')==BASE,'worktree is not at W35 base')
require(git_text('rev-parse','HEAD^{tree}')==TREE,'worktree tree changed')
require(git_text('rev-parse','HEAD:src/web/src')==SOURCE_TREE,'source/caller subtree changed')
require(not git_text('status','--porcelain'),'worktree not clean before application')
pr=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,mergeStateStatus,headRefOid,headRefName'],text=True))
require(pr=={'headRefName':'codex/slskdn-oidc-tooltip-localization-20261030','headRefOid':BASE,'isDraft':True,'mergeStateStatus':'CLEAN','state':'OPEN'},f'live PR changed: {pr}')
remote_rows=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin',REMOTE_REF],text=True).splitlines()
remote=remote_rows[0].split()[0] if remote_rows else ''
require(remote==BASE,f'remote branch moved: {remote}')

inputs=read_jsonl(SCRATCH/'review-input.jsonl')
manual=read_jsonl(SCRATCH/'review-decisions.jsonl')
candidates=read_jsonl(SCRATCH/'crossreview-plan.jsonl')
root=read_jsonl(ROOT_REVIEW/'root-crossreview.jsonl')
independent=read_jsonl(INDEPENDENT/'independent-review.jsonl')
by_input={r['id']:r for r in inputs}
by_manual={r['id']:r for r in manual}
by_candidate={r['id']:r for r in candidates}
by_root={r['id']:r for r in root}
by_independent={r['id']:r for r in independent}
require(len(by_input)==len(inputs)==274 and len(by_manual)==len(manual)==274 and len(by_independent)==len(independent)==274,'input/manual/independent row count or uniqueness mismatch')
require(len(by_candidate)==len(candidates)==38 and len(by_root)==len(root)==38,'candidate/root row count or uniqueness mismatch')
require(set(by_input)==set(by_manual)==set(by_independent),'input/manual/independent ID sets differ')
require(set(by_candidate)==set(by_root),'candidate and root apply ID sets differ')
require(set(by_root)<=set(by_independent),'root candidate missing from independent ledger')
root_counts=collections.Counter(r.get('rootDisposition') for r in root)
independent_counts=collections.Counter(r.get('independentDisposition') for r in independent)
require(root_counts=={'accept-proposed':38},f'root disposition count changed: {root_counts}')
require(independent_counts=={'retain-current':236,'accept-proposed':38},f'independent disposition count changed: {independent_counts}')

placeholder_re=re.compile(r'\{[^{}]+\}')
def placeholders(value): return sorted(placeholder_re.findall(value))
plan=[]
catalogs={}
caller_blobs={}
for locale in LOCALES:
    path=f'src/web/public/locales/{locale}.json'
    raw=blob(BASE,path)
    require(sha(raw)==manifest['currentCatalogFileSha256'][locale],f'catalog base hash changed: {locale}')
    catalogs[locale]=json.loads(raw.decode('utf-8'))
    require(len(catalogs[locale])==6169,f'catalog key count changed: {locale}')

for ident,row in by_root.items():
    inp=by_input[ident]; decision=by_manual[ident]; candidate=by_candidate[ident]; independent_row=by_independent[ident]
    require(row['window']==35 and row['id']==ident,'root row window/ID mismatch')
    require((row['currentPrHead'],row['currentPrTree'],row['currentSourceSubtreeTree'])==(BASE,TREE,SOURCE_TREE),f'root pin mismatch: {ident}')
    require(independent_row['head']==BASE and independent_row['tree']==TREE and independent_row['sourceSubtreeTree']==SOURCE_TREE,f'independent pin mismatch: {ident}')
    require(row['locale']==inp['locale']==candidate['locale']==independent_row['locale'],f'locale mismatch: {ident}')
    require(row['sourceId']==inp['sourceId']==candidate['sourceId']==independent_row['sourceId'],f'source ID mismatch: {ident}')
    require(row['source']==inp['source']==candidate['source']==independent_row['source'],f'source text mismatch: {ident}')
    source_sha=sha(row['source'])
    require(candidate['sourceSha256']==source_sha and independent_row['sourceSha256']==source_sha,f'source hash mismatch: {ident}')
    require(row['currentTarget']==inp['target']==candidate['currentTarget']==independent_row['currentTarget'],f'current text mismatch: {ident}')
    current_sha=sha(row['currentTarget'])
    require(row['currentTargetSha256']==inp['targetSha256']==candidate['currentTargetSha256']==independent_row['currentTargetSha256']==current_sha,f'current target hash mismatch: {ident}')
    require(row['rootDisposition']=='accept-proposed',f'unsupported root disposition: {ident}/{row["rootDisposition"]}')
    final=row['rootFinalTarget']; final_sha=sha(final)
    require(row['rootFinalTargetSha256']==final_sha==row['proposedTargetSha256']==candidate['proposedTargetSha256']==independent_row['proposedTargetSha256']==independent_row['independentTargetSha256'],f'final/proposal hash mismatch: {ident}')
    require(final==row['proposedTarget']==candidate['proposedTarget']==independent_row['proposedTarget']==independent_row['independentTarget'],f'root/independent final target mismatch: {ident}')
    require(independent_row['independentDisposition']=='accept-proposed' and independent_row['packetVerdict']=='correct',f'independent candidate disposition mismatch: {ident}')
    require(independent_row['rootCrossReview']['comparison']=='exact-match' and independent_row['rootCrossReview']['disposition']=='accept-proposed' and independent_row['rootCrossReview']['finalTarget']==final,f'independent-root comparison mismatch: {ident}')
    require(decision['verdict']=='correct' and decision['sourceSha256']==source_sha and decision['currentTargetSha256']==current_sha and decision['candidateTargetSha256']==final_sha,f'manual decision mismatch: {ident}')
    require(row['sourceCallsites']==inp['sourceCallsites']==candidate['sourceCallsites']==independent_row['sourceCallsites'],f'caller pins differ: {ident}')
    require(row['sourceContexts']==inp['sourceContexts']==candidate['sourceContexts']==independent_row['sourceContexts'],f'caller contexts differ: {ident}')
    locale=row['locale']; catalog_path=inp['catalogPath']; catalog_key=inp['catalogKey']
    require(catalog_path==f'src/web/public/locales/{locale}.json' and catalog_key==candidate['catalogKey']==independent_row['catalogKey'],f'catalog mapping mismatch: {ident}')
    require(catalogs[locale].get(catalog_key)==row['currentTarget'],f'current exact catalog value mismatch: {ident}')
    require(placeholders(row['source'])==sorted(row.get('placeholders',[]))==placeholders(row['currentTarget'])==placeholders(final),f'placeholder mismatch: {ident}')
    literals=row.get('protectedLiterals',[])
    require(literals==candidate.get('protectedLiterals',[])==independent_row.get('protectedLiterals',[]),f'protected literal list mismatch: {ident}')
    for literal in literals:
        require(row['source'].count(literal)==row['currentTarget'].count(literal)==final.count(literal),f'protected literal mismatch: {ident}/{literal}')
    require(final != row['currentTarget'],'root final target is a no-op')
    for call in row['sourceCallsites']:
        path=call['path']
        if path not in caller_blobs: caller_blobs[path]=blob(BASE,path)
        caller=caller_blobs[path]
        require(sha(caller)==call['fileSha256'],f'caller file hash mismatch: {ident}/{path}')
        lines=caller.decode('utf-8').splitlines()
        require(1 <= call['line'] <= len(lines),f'caller line out of range: {ident}/{path}')
        line=lines[call['line']-1].strip()
        require(line==call['lineText'] and sha(line)==call['lineTextSha256'],f'caller line hash mismatch: {ident}/{path}:{call["line"]}')
    plan.append({'schemaVersion':1,'window':35,'id':ident,'locale':locale,'sourceId':row['sourceId'],'source':row['source'],'sourceSha256':source_sha,'catalogPath':catalog_path,'catalogKey':catalog_key,'currentTarget':row['currentTarget'],'currentTargetSha256':current_sha,'finalTarget':final,'finalTargetSha256':final_sha,'rootDisposition':row['rootDisposition'],'rootReason':row['rootReason'],'sourceCallsites':row['sourceCallsites'],'sourceContexts':row['sourceContexts'],'placeholders':row.get('placeholders',[]),'protectedLiterals':literals,'currentCatalogFileSha256':manifest['currentCatalogFileSha256'][locale],'currentPrHead':BASE,'currentPrTree':TREE,'currentSourceSubtreeTree':SOURCE_TREE,'rootLedgerSha256':ROOT_SHA,'independentLedgerSha256':INDEPENDENT_SHA,'candidatePlanSha256':PACKET_SHA})

require(len(plan)==38 and len({r['id'] for r in plan})==38,'final apply plan does not contain 38 unique cells')
by_file=collections.Counter(r['catalogPath'] for r in plan)
by_locale=collections.Counter(r['locale'] for r in plan)
require(len(by_file)==11 and sum(by_file.values())==38,'expected 38 edits across 11 catalog files')
apply_path=SCRATCH/'root-apply-plan-window35.jsonl'
apply_path.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in sorted(plan,key=lambda r:r['id'])),encoding='utf-8')
preflight={'result':'READY_TO_APPLY','window':35,'pullRequest':409,'reviewBaseHead':BASE,'reviewBaseTree':TREE,'reviewBaseSourceSubtreeTree':SOURCE_TREE,'remotePrBranch':'codex/slskdn-oidc-tooltip-localization-20261030','livePrState':pr['state'],'livePrDraft':pr['isDraft'],'livePrMergeState':pr['mergeStateStatus'],'remoteHead':remote,'manualCandidatePlanSha256':PACKET_SHA,'manualDecisionLedgerSha256':DECISION_SHA,'rootCrossReviewLedgerSha256':ROOT_SHA,'independentFullReviewLedgerSha256':INDEPENDENT_SHA,'rootRows':len(root),'rootDispositions':dict(root_counts),'independentRows':len(independent),'independentDispositions':dict(independent_counts),'allCandidateRootIndependentTargetsMatch':True,'cellsToApply':len(plan),'catalogFilesToChange':len(by_file),'cellsByLocale':dict(sorted(by_locale.items())),'callerFilesPinned':len(caller_blobs),'callerLineReferences':sum(len(r['sourceCallsites']) for r in plan),'catalogFilesPinned':len(LOCALES),'allCurrentValuesAndHashesMatch':True,'allFinalHashesPlaceholdersProtectedLiteralsPass':True,'trackedChangesBeforeApplication':0,'nativeSpeakerApproved':False,'testsBuildScansCiRun':False,'workflowFilesChanged':False}
(SCRATCH/'application-preflight-window35.json').write_text(json.dumps(preflight,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(preflight,ensure_ascii=False,indent=2))
print('rootApplyPlanSha256='+sha(apply_path.read_bytes()))
