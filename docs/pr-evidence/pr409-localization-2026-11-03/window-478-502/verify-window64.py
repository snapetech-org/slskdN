#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import hashlib,json,re,subprocess
E=Path(__file__).resolve().parent
REPO=E.parents[3]
sha=lambda b:hashlib.sha256(b).hexdigest()
def load_json(path):return json.loads(path.read_text(encoding='utf-8'))
def load_jsonl(path):return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()]
def git_show(rev,path):return subprocess.check_output(['git','-C',str(REPO),'show',f'{rev}:{path}'])
def verify_sums(folder,name):
    for line in (folder/name).read_text(encoding='utf-8').splitlines():
        if not line.strip():continue
        expected,rel=line.split(None,1); rel=rel.strip().lstrip('*')
        assert sha((folder/rel).read_bytes())==expected,(folder/rel,'checksum mismatch')
I=E/'candidate-free-input'; P=E/'primary-review'; B=E/'independent-blind-review'
verify_sums(I,'PACKET-SHA256SUMS.txt'); verify_sums(P,'SHA256SUMS.txt'); verify_sums(B,'SHA256SUMS.txt')
manifest=load_json(E/'cross-audit-manifest.json')
summary=load_json(E/'cross-audit-summary.json')
plan=load_json(E/'cross-audit-apply-plan.json')
base=manifest['head']
assert (manifest['repository'],manifest['pullRequest'],manifest['window'],manifest['tree'])==('snapetech-org/slskdN',409,'W64-ranks-478-502','9d40e239e7e717a81bd176d143d1ce067fe026a1')
assert sha((I/'manifest.json').read_bytes())==manifest['candidateFreeManifestSha256']
assert sha((I/'PACKET-SHA256SUMS.txt').read_bytes())==manifest['candidateFreeChecksumListSha256']
assert sha((P/'SHA256SUMS.txt').read_bytes())==manifest['primaryChecksumListSha256']
assert sha((B/'SHA256SUMS.txt').read_bytes())==manifest['blindChecksumListSha256']
input_manifest=load_json(I/'manifest.json'); primary_summary=load_json(P/'summary.json'); blind_summary=load_json(B/'summary.json')
assert input_manifest['head']==primary_summary['head']==blind_summary['head']==base
assert input_manifest['tree']==primary_summary['tree']==blind_summary['tree']==manifest['tree']
inputs=load_jsonl(I/'source-current-cells.jsonl')
primary=load_jsonl(P/'review-decisions.jsonl'); blind=load_jsonl(B/'blind-ledger.jsonl')
root=load_jsonl(E/'cross-audit-decisions.jsonl')
assert len(inputs)==len(primary)==len(blind)==len(root)==300
index=lambda rows:{(r['continuationRank'],r['locale']):r for r in rows}
ii,pp,bb,rr=map(index,(inputs,primary,blind,root))
assert set(ii)==set(pp)==set(bb)==set(rr) and len(ii)==300
count=Counter(); updates=[]; disagreements=0
for key,c in ii.items():
    p=pp[key]; b=bb[key]; r=rr[key]
    assert r['head']==base and r['tree']==manifest['tree']
    for field in ('sourceId','source','sourceSha256','locale','catalogKey','catalogPath','catalogFileSha256','catalogGitBlob','currentTarget','currentTargetSha256','callerContextSha256','callerRefs'):
        assert r[field]==c[field],(key,field)
    assert r['primaryDisposition']==p['disposition'] and r['primaryTarget']==p['selectedTarget']
    assert r['blindDisposition']==b['disposition'] and r['blindTarget']==b['blindTarget']
    assert r['primaryTargetSha256']==p['selectedTargetSha256']
    assert r['blindTargetSha256']==b['blindTargetSha256']
    assert r['selectedTargetSha256']==sha(r['selectedTarget'].encode('utf-8'))
    assert r['candidateFreeInputCellSha256']==sha(json.dumps(c,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8'))
    if p['selectedTarget']!=b['blindTarget']:disagreements+=1
    count[r['rootDisposition']]+=1
    t=r['tokenAudit']
    assert t['sourcePlaceholders']==t['selectedPlaceholders']
    assert t['sourceMarkup']==t['selectedMarkup']
    assert t['sourceNumericTokens']==t['selectedNumericTokens']
    assert t['placeholdersMatch'] and t['markupMatches'] and t['numericTokensMatch']
    if r['continuationRank']==501:
        assert r['rootDisposition']=='accept-current' and r['selectedTarget']==c['currentTarget']
        assert t['localizedStatusLiteralException'] and 'interfaceText' in t['localizedStatusExceptionRationale']
    else:
        assert t['selectedProtectedLiteralMatch']
    if r['continuationRank']==486:
        assert r['rootDisposition']=='hold' and r['selectedTarget']==c['currentTarget'] and len(c['callerRefs'])==0
    else:
        assert r['rootDisposition']!='hold'
    if r['selectedTarget']!=c['currentTarget']:updates.append(r)
assert count==Counter({'accept-current':202,'correction':79,'refinement':7,'hold':12})
assert disagreements==79 and len(updates)==86
assert plan['head']==base and plan['tree']==manifest['tree'] and plan['updateCount']==86
plan_updates={(x['continuationRank'],x['locale']):x for x in plan['updates']}
assert len(plan_updates)==86 and set(plan_updates)=={(x['continuationRank'],x['locale']) for x in updates}
for key,r in rr.items():
    if r['selectedTarget']!=r['currentTarget']:
        p=plan_updates[key]
        assert (p['catalogPath'],p['catalogKey'],p['currentTarget'],p['selectedTarget'],p['selectedTargetSha256'])==(r['catalogPath'],r['catalogKey'],r['currentTarget'],r['selectedTarget'],r['selectedTargetSha256'])
assert summary['rootDispositions']==dict(count)
assert summary['primaryBlindTargetDisagreements']==disagreements and summary['selectedUpdates']==len(updates)
assert len(load_jsonl(I/'prior-held-cell-reattestation.jsonl'))==86
expected_files={}
for c in inputs:
    path=c['catalogPath']
    assert path not in expected_files or expected_files[path]==c['catalogFileSha256']
    expected_files[path]=c['catalogFileSha256']
catalog_updates={}
for r in updates:catalog_updates.setdefault(r['catalogPath'],{})[r['catalogKey']]=r
assert set(catalog_updates)==set(expected_files) and len(catalog_updates)==12
for path,initial_sha in expected_files.items():
    original=json.loads(git_show(base,path).decode('utf-8'))
    final=json.loads((REPO/path).read_text(encoding='utf-8'))
    assert sha(git_show(base,path))==initial_sha,(path,'base catalog hash mismatch')
    assert list(original)==list(final) and set(original)==set(final),(path,'catalog key order/shape changed')
    for key in original:
        row=catalog_updates[path].get(key)
        if row:
            assert original[key]==row['currentTarget'] and final[key]==row['selectedTarget'],(path,key,'target mismatch')
        else:
            assert final[key]==original[key],(path,key,'non-target value changed')
prior=load_jsonl(I/'prior-held-cell-reattestation.jsonl')
assert len(prior)==86
for h in prior:
    assert h['matchesPriorCurrentValue'] is True and h['priorTargetSha256']==h['currentTargetSha256']
    value=json.loads((REPO/h['currentCatalogPath']).read_text(encoding='utf-8'))[h['source']]
    assert value==h['currentTarget'] and sha(value.encode('utf-8'))==h['currentTargetSha256']
assert summary['nativeSpeakerApproval'] is False and summary['exactHeadBrowserReview'] is False
assert not any(p.startswith('.github/workflows/') for p in subprocess.check_output(['git','-C',str(REPO),'diff','--name-only',base],text=True).splitlines())
# Verify current staged/worktree changes contain only the catalog edits and this evidence window.
status=subprocess.check_output(['git','-C',str(REPO),'status','--short','--untracked-files=all'],text=True).splitlines()
allowed_catalogs=set(expected_files)
for line in status:
    path=line[3:]
    assert path in allowed_catalogs or path.startswith(str(E.relative_to(REPO))+'/'),('unexpected repository change',line)
check=subprocess.run(['git','-C',str(REPO),'diff','--check',base,'--','src/web/public/locales'],text=True,capture_output=True)
assert check.returncode==0,check.stdout+check.stderr
print(json.dumps({'result':'PASS','head':base,'tree':manifest['tree'],'cells':300,'rootDispositions':dict(count),'primaryBlindTargetDisagreements':disagreements,'updates':len(updates),'updateCatalogs':len(catalog_updates),'nonTargetChanges':0,'priorHoldsReattestedAndPreserved':86,'callerlessHolds':12,'tokenMismatches':0,'workflowFilesTouched':False,'gitDiffCheck':'PASS'},ensure_ascii=False,indent=2))
