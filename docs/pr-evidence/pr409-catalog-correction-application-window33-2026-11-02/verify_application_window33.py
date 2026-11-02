#!/usr/bin/env python3
"""Read-only exact-pin, catalog-diff, held-row, and cumulative verifier for W33."""
import collections, hashlib, json, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
MANUAL=REPO/'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01/window33'
PACKET=MANUAL/'review-packet'; INDEP=MANUAL/'independent-review'; ROOTPKT=MANUAL/'root-cross-review'
BASE='0abf10ae9f49d27d7cfef823cfe5d70765ee29f4'; BASE_TREE='8ac49de1cde7dc242484eadc597781819e26e1d2'; SRC='594e56c3f439bad476b1bd57e0de1665c62fa1bb'
REMOTE_REF='refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES=['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
def sha(v): return hashlib.sha256(v if isinstance(v,bytes) else v.encode('utf-8')).hexdigest()
def read_jsonl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
def blob(commit,path): return subprocess.check_output(['git','-C',str(REPO),'show',f'{commit}:{path}'])
def require(ok,msg):
    if not ok: raise SystemExit('FAIL: '+msg)
def verify_sums(directory,required=True):
    sums=directory/'SHA256SUMS.txt'
    if not sums.exists():
        if required: require(False,f'missing checksums: {sums}')
        return
    result=subprocess.run(['sha256sum','-c','SHA256SUMS.txt'],cwd=directory,capture_output=True,text=True)
    require(result.returncode==0,f'checksum failure in {directory}: {result.stderr or result.stdout}')
for d in (PACKET,INDEP,ROOTPKT,MANUAL): verify_sums(d)
verify_sums(ROOT,required=False)
manifest=json.loads((ROOT/'application-manifest.json').read_text(encoding='utf-8'))
pre=json.loads((ROOT/'application-preflight-window33.json').read_text(encoding='utf-8'))
cumulative=json.loads((ROOT/'cumulative-verification-window33.json').read_text(encoding='utf-8'))
plan=read_jsonl(ROOT/'root-apply-plan-window33.jsonl'); applied=read_jsonl(ROOT/'applied-corrections-window33.jsonl'); held=read_jsonl(ROOT/'held-context-rows-window33.jsonl')
inputs={r['id']:r for r in read_jsonl(PACKET/'review-input.jsonl')}; reviews={r['id']:r for r in read_jsonl(PACKET/'review-decisions.jsonl')}; candidates={r['id']:r for r in read_jsonl(PACKET/'crossreview-plan.jsonl')}
independent={r['id']:r for r in read_jsonl(INDEP/'independent-decisions.jsonl')}; roots={r['id']:r for r in read_jsonl(ROOTPKT/'root-disposition-ledger.jsonl')}
require(len(plan)==len(applied)==41 and len(held)==11,'application/held row count')
require(len({r['id'] for r in plan})==41 and set(r['id'] for r in plan)==set(roots)==set(candidates)==set(independent),'candidate row set')
require(set(r['id'] for r in held)=={i for i,d in reviews.items() if d['verdict']=='uncertain'},'held row set')
require(collections.Counter(r['rootDisposition'] for r in plan)==collections.Counter({'accept':40,'refine':1}),'root decision counts')
require(collections.Counter(d['verdict'] for d in reviews.values())==collections.Counter({'keep':222,'correct':41,'uncertain':11}),'manual decision counts')
require(manifest['reviewBaseHead']==BASE and manifest['reviewBaseTree']==BASE_TREE and manifest['reviewBaseSourceSubtreeTree']==SRC,'manifest base pins')
require(pre['head']==BASE and pre['tree']==BASE_TREE and pre['sourceSubtreeTree']==SRC,'preflight base pins')
require(pre['applyPlanSha256']==sha((ROOT/'root-apply-plan-window33.jsonl').read_bytes()),'apply plan checksum')
require(pre['heldRowsSha256']==sha((ROOT/'held-context-rows-window33.jsonl').read_bytes()),'held ledger checksum')
require(manifest['catalogCommit']==git('rev-parse',manifest['catalogCommit']),'catalog commit exists')
require(git('rev-parse',manifest['catalogCommit']+'^{tree}')==manifest['catalogCommitTree'],'catalog commit tree')
require(git('merge-base','--is-ancestor',BASE,'HEAD')=='','base is not ancestor')
require(git('merge-base','--is-ancestor',manifest['catalogCommit'],'HEAD')=='','catalog commit is not ancestor')
pr=json.loads(subprocess.check_output(['gh','api','repos/snapetech-org/slskdN/pulls/409','--jq','{head:.head.sha,headRef:.head.ref,state:.state,draft:.draft}'],text=True))
head,tree,source_tree=git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}'),git('rev-parse','HEAD:src/web/src')
remote=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin',REMOTE_REF],text=True).split()[0]
require(pr=={'head':head,'headRef':'codex/slskdn-oidc-tooltip-localization-20261030','state':'open','draft':True},'live PR must remain open/draft at local head')
require(remote==head,'remote PR branch head differs from local head')
require(source_tree==SRC,'source/caller subtree changed')
workflow_diff=subprocess.check_output(['git','-C',str(REPO),'diff','--name-only',BASE,'HEAD','--','.github/workflows'],text=True).splitlines()
require(not workflow_diff,'workflow files changed')
allowed=collections.defaultdict(dict)
for r in plan: allowed[r['catalogPath']][r['catalogKey']]=r
changes={}; current_hashes={}; key_counts={}; placeholder=re.compile(r'\{[^{}]+\}')
for locale in LOCALES:
    rel=f'src/web/public/locales/{locale}.json'; before=json.loads(blob(BASE,rel).decode('utf-8')); current_raw=(REPO/rel).read_bytes(); after=json.loads(current_raw.decode('utf-8'))
    require(set(before)==set(after),f'catalog key set changed: {locale}')
    require(len(after)==6169,f'catalog key count changed: {locale}')
    current_hashes[locale]=sha(current_raw); key_counts[locale]=len(after)
    changed=[key for key in before if before[key]!=after[key]]
    for key,row in allowed.get(rel,{}).items():
        root=roots[row['id']]; inp=inputs[row['id']]
        require(root['pins']=={'prHead':BASE,'prTree':BASE_TREE,'sourceSubtreeTree':SRC},f'root pin {row["id"]}')
        require((before.get(key),root['currentTarget'])==(row['oldTarget'],row['oldTarget']),f'old target {row["id"]}')
        require(sha(before[key])==row['oldTargetSha256']==root['currentTargetSha256'],f'old target hash {row["id"]}')
        require(after.get(key)==row['newTarget']==root['rootFinalTarget'],f'final target {row["id"]}')
        require(sha(after[key])==row['newTargetSha256']==root['rootFinalTargetSha256'],f'final target hash {row["id"]}')
        require(sha(row['source'])==row['sourceSha256']==inp['sourceSha256'],f'source hash {row["id"]}')
        require(collections.Counter(placeholder.findall(row['source']))==collections.Counter(placeholder.findall(after[key])),f'placeholder {row["id"]}')
        for literal in inp.get('protectedLiterals',[]):
            require(after[key].count(literal)==row['source'].count(literal),f'protected literal {row["id"]}:{literal}')
    require(set(changed)==set(allowed.get(rel,{})),f'unexpected catalog diff {locale}: {set(changed)^set(allowed.get(rel,{}))}')
    if changed: changes[locale]=changed
require(sum(len(v) for v in changes.values())==41 and len(changes)==11,'catalog diff totals')
require({loc:current_hashes[loc] for loc in manifest['postCatalogFileSha256']}==manifest['postCatalogFileSha256'],'catalog file hashes differ from manifest')
require(len(applied)==41 and {r['id'] for r in applied}=={r['id'] for r in plan},'applied ledger row set')
for r in held:
    path=r['catalogPath']; before=json.loads(blob(BASE,path).decode('utf-8')); after=json.loads((REPO/path).read_bytes())
    require(before.get(r['catalogKey'])==r['currentTarget']==after.get(r['catalogKey']),f'held value changed: {r["id"]}')
    require(sha(after[r['catalogKey']])==r['currentTargetSha256'],f'held hash changed: {r["id"]}')
    require(not r['sourceCallsites'] and not r['sourceContexts'],f'held row has source callers: {r["id"]}')
require(cumulative['manualCoverage']=={'windows':33,'sourceKeys':822,'cells':9778,'verdicts':{'correct':1334,'keep':8165,'uncertain':279},'manualWindowOverlap':0},'cumulative manual counts')
require(cumulative['application']['totalApplied']==1340 and cumulative['application']['uniqueAppliedSourceKeys']==311,'cumulative application counts')
require(cumulative['application']['uncertainRemaining']==267 and cumulative['application']['cellsOutsideFormalAndManualReview']==52502,'cumulative unresolved counts')
require(cumulative['catalogs']['catalogFileSha256']==manifest['postCatalogFileSha256'],'cumulative catalog hashes')
require(not (REPO/'.github/workflows').is_dir() or not workflow_diff,'workflow safety')
report={'result':'PASS','verifiedAtHead':head,'verifiedAtTree':tree,'remotePrHead':remote,'prState':pr['state'],'prDraft':pr['draft'],'reviewBaseHead':BASE,'reviewBaseTree':BASE_TREE,'reviewBaseSourceSubtreeTree':SRC,'catalogCommit':manifest['catalogCommit'],'rootFinalCells':41,'acceptedAsProposed':40,'refinedAndAccepted':1,'heldContextMismatchCells':11,'changedCatalogFiles':len(changes),'changedCells':sum(len(v) for v in changes.values()),'changedByLocale':{k:len(v) for k,v in sorted(changes.items())},'localeKeyCounts':key_counts,'catalogFileSha256':current_hashes,'heldCellsUnchanged':len(held),'sourceSubtreeUnchanged':source_tree==SRC,'workflowFilesChanged':len(workflow_diff),'manualCoverageCells':9778,'manualCoverageSourceKeys':822,'totalAppliedCorrections':1340,'uncertainRemaining':267,'cellsOutsideFormalAndManualReview':52502,'allReviewBundlesAndChecksumsValid':True,'testsBuildScansCiRun':False,'nativeSpeakerApproved':False}
print(json.dumps(report,ensure_ascii=False,indent=2))
