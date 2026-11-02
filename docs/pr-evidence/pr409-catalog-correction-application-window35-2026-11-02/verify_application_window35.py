#!/usr/bin/env python3
"""Read-only exact-target and pushed-PR verifier for slskdN W35."""
import argparse, collections, hashlib, json, re, subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
MANUAL=REPO/'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01/window35'
PACKET=MANUAL/'review-packet'
ROOT_REVIEW=MANUAL/'root-cross-review'
INDEPENDENT=MANUAL/'independent-review'
BASE='917273260c49cca1c14576a0720fc84998d2846d'
BASE_TREE='1cdd8c831d224a5706ac6f3e465add4fd249d2be'
SOURCE_TREE='594e56c3f439bad476b1bd57e0de1665c62fa1bb'
REMOTE_REF='refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES=['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']

def sha(v): return hashlib.sha256(v if isinstance(v,bytes) else v.encode('utf-8')).hexdigest()
def jl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(*args,raw=False):
    v=subprocess.check_output(['git','-C',str(REPO),*args])
    return v if raw else v.decode('utf-8').strip()
def blob(commit,path): return git('show',f'{commit}:{path}',raw=True)
def need(ok,msg):
    if not ok: raise SystemExit('FAIL: '+msg)
def sums(directory):
    need((directory/'SHA256SUMS.txt').is_file(),f'missing checksums: {directory}')
    p=subprocess.run(['sha256sum','-c','SHA256SUMS.txt'],cwd=directory,text=True,capture_output=True)
    need(p.returncode==0,f'checksum failure: {directory}: {p.stderr or p.stdout}')
def placeholders(v): return sorted(re.findall(r'\{[^{}]+\}',v))

ap=argparse.ArgumentParser()
ap.add_argument('--allow-unpushed',action='store_true',help='verify the local evidence commit while PR/remote remain at the pinned base')
args=ap.parse_args()
manifest=json.loads((HERE/'application-manifest.json').read_text(encoding='utf-8'))
BASE_COMMIT=manifest['reviewBaseHead']; CATALOG=manifest['catalogCommit']
need(BASE_COMMIT==BASE and manifest['reviewBaseTree']==BASE_TREE and manifest['reviewBaseSourceSubtreeTree']==SOURCE_TREE,'manifest base pin mismatch')
need(git('rev-parse',f'{BASE_COMMIT}^{{tree}}')==BASE_TREE and git('rev-parse',f'{BASE_COMMIT}:src/web/src')==SOURCE_TREE,'base tree/source pin mismatch')
need(git('rev-parse',f'{CATALOG}^')==BASE and git('rev-parse',f'{CATALOG}^{{tree}}')==manifest['catalogCommitTree'],'catalog commit parent/tree mismatch')
need(git('rev-parse','HEAD')==CATALOG or git('merge-base','--is-ancestor',CATALOG,'HEAD')=='','catalog commit is not ancestor of HEAD')
need(git('rev-parse','HEAD:src/web/src')==SOURCE_TREE,'current source/caller subtree changed')
need(not git('status','--porcelain'),'verification worktree is dirty')

# Verify each evidence bundle and the exact cross-review decision chain.
for d in (MANUAL,PACKET,ROOT_REVIEW,INDEPENDENT,HERE): sums(d)
inputs=jl(PACKET/'review-input.jsonl'); decisions=jl(PACKET/'review-decisions.jsonl'); candidates=jl(PACKET/'crossreview-plan.jsonl')
root=jl(ROOT_REVIEW/'root-crossreview.jsonl'); independent=jl(INDEPENDENT/'independent-review.jsonl')
apply=jl(HERE/'root-apply-plan-window35.jsonl'); applied=jl(HERE/'applied-corrections-window35.jsonl')
by_input={r['id']:r for r in inputs}; by_decision={r['id']:r for r in decisions}; by_candidate={r['id']:r for r in candidates}; by_root={r['id']:r for r in root}; by_ind={r['id']:r for r in independent}; by_apply={r['id']:r for r in apply}; by_applied={r['id']:r for r in applied}
need(len(inputs)==len(by_input)==274 and len(decisions)==len(by_decision)==274 and len(independent)==len(by_ind)==274,'review rows/uniqueness mismatch')
need(len(candidates)==len(by_candidate)==38 and len(root)==len(by_root)==38 and len(apply)==len(by_apply)==38 and len(applied)==len(by_applied)==38,'candidate/apply row count mismatch')
need(set(by_input)==set(by_decision)==set(by_ind),'review ID sets differ')
need(set(by_candidate)==set(by_root)==set(by_apply)==set(by_applied),'candidate/root/apply ID sets differ')
need(collections.Counter(r['rootDisposition'] for r in root)=={'accept-proposed':38},'root disposition counts differ')
need(collections.Counter(r['independentDisposition'] for r in independent)=={'retain-current':236,'accept-proposed':38},'independent disposition counts differ')
need(sha((ROOT_REVIEW/'root-crossreview.jsonl').read_bytes())==manifest['rootCrossReviewLedgerSha256'],'root ledger SHA mismatch')
need(sha((INDEPENDENT/'independent-review.jsonl').read_bytes())==manifest['independentCrossReviewLedgerSha256'],'independent ledger SHA mismatch')

for ident,row in by_apply.items():
    inp=by_input[ident]; root_row=by_root[ident]; ind=by_ind[ident]; cand=by_candidate[ident]; app=by_applied[ident]
    need(row['currentPrHead']==BASE and row['currentPrTree']==BASE_TREE and row['currentSourceSubtreeTree']==SOURCE_TREE,'apply plan pin mismatch: '+ident)
    need(root_row['currentPrHead']==BASE and root_row['currentPrTree']==BASE_TREE and root_row['currentSourceSubtreeTree']==SOURCE_TREE,'root pin mismatch: '+ident)
    need((row['source'],row['sourceSha256'])==(inp['source'],inp['sourceSha256'])==(ind['source'],ind['sourceSha256']),'source mismatch: '+ident)
    need(sha(row['source'])==row['sourceSha256'],'source hash mismatch: '+ident)
    need((row['currentTarget'],row['currentTargetSha256'])==(inp['target'],inp['targetSha256'])==(ind['currentTarget'],ind['currentTargetSha256']),'current mismatch: '+ident)
    need(sha(row['currentTarget'])==row['currentTargetSha256'],'current target hash mismatch: '+ident)
    need((row['finalTarget'],row['finalTargetSha256'])==(root_row['rootFinalTarget'],root_row['rootFinalTargetSha256'])==(ind['independentTarget'],ind['independentTargetSha256'])==(ind['rootCrossReview']['finalTarget'],ind['rootCrossReview']['finalTargetSha256']),'final target disagreement: '+ident)
    need(row['finalTarget']==cand['proposedTarget']==app['newTarget']==app['appliedTarget'],'applied target differs: '+ident)
    need(sha(row['finalTarget'])==row['finalTargetSha256']==app['newTargetSha256']==app['appliedTargetSha256'],'final target hash mismatch: '+ident)
    need(ind['independentDisposition']=='accept-proposed' and ind['packetVerdict']=='correct' and root_row['rootDisposition']=='accept-proposed','candidate disposition mismatch: '+ident)
    need(ind['rootCrossReview']['comparison']=='exact-match' and ind['rootCrossReview']['disposition']=='accept-proposed','cross-review reconciliation mismatch: '+ident)
    need(row['sourceCallsites']==inp['sourceCallsites']==ind['sourceCallsites'],'caller pins differ: '+ident)
    need(row['catalogPath']==inp['catalogPath'] and row['catalogKey']==inp['catalogKey'],'catalog mapping differs: '+ident)
    need(placeholders(row['source'])==placeholders(row['currentTarget'])==placeholders(row['finalTarget'])==sorted(row['placeholders']),'placeholder mismatch: '+ident)
    for literal in row['protectedLiterals']:
        need(row['source'].count(literal)==row['currentTarget'].count(literal)==row['finalTarget'].count(literal),'protected literal mismatch: '+ident+'/'+literal)
    need(row['rootLedgerSha256']==manifest['rootCrossReviewLedgerSha256'] and row['independentLedgerSha256']==manifest['independentCrossReviewLedgerSha256'],'apply evidence checksum pin mismatch: '+ident)

# Check all callers at the frozen base and all changed cells at the catalog commit.
caller_blobs={}
for row in apply:
    for call in row['sourceCallsites']:
        path=call['path']
        if path not in caller_blobs: caller_blobs[path]=blob(BASE,path)
        raw=caller_blobs[path]; lines=raw.decode('utf-8').splitlines()
        need(sha(raw)==call['fileSha256'],'caller file hash mismatch: '+path)
        need(1<=call['line']<=len(lines),'caller line out of range: '+path)
        line=lines[call['line']-1].strip()
        need(line==call['lineText'] and sha(line)==call['lineTextSha256'],'caller line pin mismatch: '+path)

changed_by_locale=collections.defaultdict(set)
for locale in LOCALES:
    rel=f'src/web/public/locales/{locale}.json'
    base_raw=blob(BASE,rel); catalog_raw=blob(CATALOG,rel)
    base=json.loads(base_raw.decode('utf-8')); current=json.loads(catalog_raw.decode('utf-8'))
    need(len(base)==len(current)==6169 and set(base)==set(current),'catalog keys/count mismatch: '+locale)
    need(sha(base_raw)==manifest['catalogFilesChanged'].get(locale,{}).get('baseSha256',sha(base_raw)),'base catalog checksum mismatch: '+locale)
    need(sha(catalog_raw)==manifest['catalogFilesChanged'].get(locale,{}).get('resultSha256',sha(catalog_raw)),'result catalog checksum mismatch: '+locale)
    expected={r['catalogKey']:r['finalTarget'] for r in apply if r['locale']==locale}
    actual={k:v for k,v in current.items() if base[k]!=v}
    need(actual==expected,'unexpected changed catalog values: '+locale)
    changed_by_locale[locale]=set(actual)
    for row in (r for r in apply if r['locale']==locale):
        need(base.get(row['catalogKey'])==row['currentTarget'],'base catalog value mismatch: '+row['id'])
        need(current.get(row['catalogKey'])==row['finalTarget'],'catalog final target mismatch: '+row['id'])
# All twelve catalogs have the same complete set of keys.
all_keys=[set(json.loads(blob(CATALOG,f'src/web/public/locales/{loc}.json').decode('utf-8'))) for loc in LOCALES]
need(all(all_keys[0]==keys for keys in all_keys[1:]),'locale catalog key parity mismatch')

catalog_paths=set(git('diff-tree','--no-commit-id','--name-only','-r',CATALOG).splitlines())
expected_catalog_paths={f'src/web/public/locales/{r["locale"]}.json' for r in apply}
need(catalog_paths==expected_catalog_paths,'catalog commit contains unexpected paths')
need(not git('diff','--name-only',BASE,'HEAD','--','.github/workflows'),'workflow path changed')
all_changed=set(git('diff','--name-only',BASE,'HEAD').splitlines())
allowed=set()
allowed|={p for p in all_changed if p.startswith('docs/pr-evidence/pr409-manual-semantic-review-2026-11-01/window35/')}
allowed|={p for p in all_changed if p.startswith('docs/pr-evidence/pr409-catalog-correction-application-window35-2026-11-02/')}
allowed.add('docs/CHANGELOG.md')
allowed|=expected_catalog_paths
need(all_changed<=allowed,'out-of-scope changes: '+str(sorted(all_changed-allowed)))
need(git('diff','--check',BASE,'HEAD')=='','git diff --check failed')

# The pushed PR must remain open/draft; before push, --allow-unpushed accepts the exact base state only.
pr=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,mergeStateStatus,headRefOid,headRefName'],text=True))
remote_rows=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin',REMOTE_REF],text=True).splitlines()
remote=remote_rows[0].split()[0] if remote_rows else ''
head=git('rev-parse','HEAD')
if args.allow_unpushed:
    need(pr['headRefOid']==BASE and remote==BASE,'remote PR moved before push')
else:
    need(pr['headRefOid']==head and remote==head,'live PR/remote do not match current head')
need(pr['state']=='OPEN' and pr['isDraft'] is True,'PR state/draft changed')

report={'result':'PASS','window':35,'livePrState':pr['state'],'livePrDraft':pr['isDraft'],'livePrMergeState':pr['mergeStateStatus'],'livePrHead':pr['headRefOid'],'remotePrBranchHead':remote,'verifiedLocalHead':head,'verifiedLocalTree':git('rev-parse','HEAD^{tree}'),'reviewBaseHead':BASE,'reviewBaseTree':BASE_TREE,'sourceSubtreeTree':SOURCE_TREE,'catalogCommit':CATALOG,'catalogCommitTree':manifest['catalogCommitTree'],'rootCorrections':38,'independentRows':274,'independentKeptRows':236,'catalogFilesChanged':len(expected_catalog_paths),'changedCells':38,'callerFilesRechecked':len(caller_blobs),'callerLineReferences':sum(len(r['sourceCallsites']) for r in apply),'localeKeyCount':6169,'catalogKeyParity':True,'placeholdersProtectedLiteralsAndExactHashes':'PASS','gitDiffCheck':'PASS','workflowChanges':False,'outOfScopePaths':[],'testsBuildScansCiRun':False,'nativeSpeakerApproved':False,'catalogHashes':{loc:sha(blob(CATALOG,f'src/web/public/locales/{loc}.json')) for loc in LOCALES}}
print(json.dumps(report,ensure_ascii=False,indent=2))
