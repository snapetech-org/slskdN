#!/usr/bin/env python3
"""Read-only integrity and exact-head verifier for the W52 review packet."""
from pathlib import Path
import collections, hashlib, json, subprocess

REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261103/slskdn-pr409-w52-primary-20261103')
PRIMARY=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window52-primary-20261103/primary')
BLIND=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window52-blind-input-20261103')
HEAD='f63c8c04f3b1c3fb5e1bc8971a0d83bbf8ca4e77'; TREE='ca9f1bf1d9f4373556476a51b863601668878eb3'
BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'; BODY='9e44ad9c48f8cfb4efbd4855737940e57ed212aaaad3c5e5942d4efb02838bc9'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

def run(*args,cwd=REPO,text=True): return subprocess.check_output(list(args),cwd=cwd,text=text)
def sha(b): return hashlib.sha256(b.encode() if isinstance(b,str) else b).hexdigest()
def git_blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def readjl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def verify_manifest(directory, filename):
    checks=[]
    for line in (directory/filename).read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        expected,rel=line.split(None,1); rel=rel.strip().lstrip('*')
        actual=sha((directory/rel).read_bytes()); checks.append({'path':rel,'expected':expected,'actual':actual,'matches':expected==actual})
    assert checks and all(x['matches'] for x in checks),(directory,checks)
    return checks

head=run('git','rev-parse','HEAD').strip(); tree=run('git','rev-parse','HEAD^{tree}').strip()
assert head==HEAD and tree==TREE and not run('git','status','--porcelain=v1').strip()
pr=json.loads(run('gh','pr','view','409','--repo','snapetech-org/slskdN','--json','body,headRefOid,headRefName,isDraft,state,url'))
assert pr['state']=='OPEN' and pr['isDraft'] and pr['headRefOid']==HEAD and pr['headRefName']==BRANCH and sha(pr['body'])==BODY
remote=run('git','ls-remote','origin',f'refs/heads/{BRANCH}').strip().split(); assert len(remote)==2 and remote[0]==HEAD
primary_checks=verify_manifest(PRIMARY,'SHA256SUMS.txt')
blind_checks=verify_manifest(BLIND,'PACKET-SHA256SUMS.txt')
blind_manifest_sha=sha((BLIND/'PACKET-SHA256SUMS.txt').read_bytes())

selection=json.loads((PRIMARY/'selection-and-boundary.json').read_text())
source_rows=readjl(PRIMARY/'source-current-cells.jsonl'); callers=readjl(PRIMARY/'caller-contexts.jsonl'); catalogs=readjl(PRIMARY/'catalog-structure.jsonl'); decisions=readjl(PRIMARY/'review-decisions.jsonl')
assert len(source_rows)==len(decisions)==300 and len(callers)==25 and len(catalogs)==12
assert [r['locale'] for r in catalogs]==LOCALES
assert selection['pins']['head']==HEAD and selection['pins']['tree']==TREE and selection['pins']['bodySha256']==BODY
assert selection['sourceCount']==25 and selection['localeCount']==12 and selection['cellCount']==300
ids_by_rank={}; cells=[]
for r in source_rows:
    ids_by_rank.setdefault(r['continuationRank'],(r['sourceId'],r['source']))
    cells.append((r['continuationRank'],r['locale']))
assert sorted(ids_by_rank)==list(range(201,226))
assert cells==[(rank,loc) for rank in range(201,226) for loc in LOCALES]
assert len({(r['sourceId'],r['locale']) for r in source_rows})==300
assert set((r['sourceId'],r['locale']) for r in source_rows)==set((r['sourceId'],r['locale']) for r in decisions)

W49=REPO/'docs/pr-evidence/pr409-localization-2026-11-03/window49'; W50=REPO/'docs/pr-evidence/pr409-localization-2026-11-03/window50'; W51=REPO/'docs/pr-evidence/pr409-localization-2026-11-03/window51'
prior=[]
for folder in (W49,W50,W51): prior.append({'path':str(folder),'verifiedEntries':len(verify_manifest(folder,'EVIDENCE-SHA256SUMS.txt')),'manifestSha256':sha((folder/'EVIDENCE-SHA256SUMS.txt').read_bytes())})
inventory=readjl(W49/'primary/source-inventory.jsonl')
byrank={r['continuationRank']:r for r in inventory}
assert all(ids_by_rank[r][0]==byrank[r]['sourceId'] and ids_by_rank[r][1]==byrank[r]['source'] for r in range(201,226))
w50_rows=readjl(W50/'primary/selection-boundary.jsonl'); w51_rows=readjl(W51/'primary/selection-boundary.jsonl')
w50={r['sourceId'] for r in w50_rows if r.get('role')=='selected-W50'}; w51={r['sourceId'] for r in w51_rows if r.get('role')=='selected-W51'}
excluded={r['sourceId'] for r in inventory if r['continuationRank'] in range(126,151)}
selected={r[0] for r in ids_by_rank.values()}
assert len(w50)==len(w51)==len(excluded)==len(selected)==25
assert w50=={byrank[r]['sourceId'] for r in range(151,176)}
assert w51=={byrank[r]['sourceId'] for r in range(176,201)}
assert not selected & (w50|w51|excluded)

ordered=None; cat_by_loc={}
for row in catalogs:
    p=REPO/row['catalogPath']; data=p.read_bytes(); doc=json.loads(data); keys=list(doc)
    if ordered is None: ordered=keys
    assert keys==ordered and len(keys)==6176
    assert sha(data)==row['sha256'] and git_blob(data)==row['gitBlob'] and run('git','rev-parse',f'{HEAD}:{row["catalogPath"]}').strip()==row['gitBlob']
    assert sha('\n'.join(keys)+'\n')==row['orderedKeySha256']
    cat_by_loc[row['locale']]=doc
assert sha('\n'.join(ordered)+'\n')==selection['orderedCatalogKeySha256']=='3ca04c40ebfed00b93fcd143109fc9d85da941cec30b6cb93f52e431498df6a7'
for r in source_rows:
    assert r['source'] in cat_by_loc[r['locale']]
    assert cat_by_loc[r['locale']][r['source']]==r['currentTarget']
    assert sha(r['source'])==r['sourceSha256'] and sha(r['currentTarget'])==r['currentTargetSha256']

caller_by_id={r['sourceId']:r for r in callers}; assert len(caller_by_id)==25
assert all(r['productionCallerCount']>0 for r in callers)
for src in callers:
    assert src['sourceId'] in selected
    assert sha(src['source'])==src['sourceSha256']
    refs=src['callers']; assert len(refs)==src['productionCallerCount']
    for ref in refs:
        p=REPO/ref['path']; data=p.read_bytes()
        assert sha(data)==ref['fileSha256'] and git_blob(data)==ref['gitBlob'] and run('git','rev-parse',f'{HEAD}:{ref["path"]}').strip()==ref['gitBlob']
        lines=data.decode().splitlines(); assert sha(lines[ref['line']-1])==ref['lineSha256']
assert sum(r['productionCallerCount'] for r in callers)==47

assert all(r['verdict'] in {'accept-current','correction','refinement','hold-context'} for r in decisions)
assert all(r['historicalSourceOrdinal'] is None for r in decisions)
assert all(r['candidateTargetSha256']==sha(r['candidateTarget']) and r['currentTargetSha256']==sha(r['currentTarget']) for r in decisions)
assert all(r['placeholderCheck']['sourceMatchesCurrent'] and r['placeholderCheck']['sourceMatchesCandidate'] for r in decisions)
assert all(r['markupCheck']['sourceMatchesCurrent'] and r['markupCheck']['sourceMatchesCandidate'] for r in decisions)
counts=collections.Counter(r['verdict'] for r in decisions); changes=[r for r in decisions if r['candidateTarget']!=r['currentTarget']]
summary=json.loads((PRIMARY/'review-summary.json').read_text())
assert dict(counts)==summary['dispositionCounts'] and len(changes)==summary['candidateChangeCount']==57
assert summary['changedCellsByLocale']==dict(collections.Counter(r['locale'] for r in changes))
assert summary['changedCellsBySource']==dict(collections.Counter(r['sourceId'] for r in changes))
assert summary['placeholderMismatchCount']==summary['markupMismatchCount']==summary['candidateProtectedLiteralMismatchCount']==0

report={'verification':'passed','pr':{'url':pr['url'],'state':pr['state'],'isDraft':pr['isDraft'],'head':HEAD,'tree':TREE,'remoteBranchHead':remote[0],'bodySha256':BODY},'selection':{'rankBasis':'W49 stable-ID inventory ranks 201-225','sources':len(selected),'locales':12,'cells':300,'firstSourceId':ids_by_rank[201][0],'lastSourceId':ids_by_rank[225][0],'nextBoundarySourceId':selection['nextBoundary']['sourceId'],'historicalSourceOrdinalsClaimed':False,'disjointFromW50':True,'disjointFromW51':True,'disjointFromUnreviewedW49Ranks126To150':True},'catalogs':{'count':len(catalogs),'keysPerCatalog':6176,'orderedKeySha256':selection['orderedCatalogKeySha256'],'allCurrentValuesAndGitBlobsMatch':True},'callers':{'totalReferences':47,'callerlessSourceIds':[],'allFilesAndLinePinsMatch':True},'primaryReview':{'acceptCurrent':counts['accept-current'],'corrections':counts['correction'],'refinements':counts['refinement'],'holds':counts['hold-context'],'candidateChanges':len(changes),'candidateChangedSourceIds':len({r['sourceId'] for r in changes}),'placeholderMismatches':0,'markupMismatches':0,'protectedCandidateMismatches':0},'primaryManifestSha256':sha((PRIMARY/'SHA256SUMS.txt').read_bytes()),'primaryManifestEntriesVerified':len(primary_checks),'blindInputManifestSha256':blind_manifest_sha,'blindInputEntriesVerified':len(blind_checks),'priorEvidenceManifests':prior,'repoWorktreeClean':True,'repositoryOrPRMutated':False,'testsBuildScansCiRun':False}
out=PRIMARY.parent/'packet-validation.json'; out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
