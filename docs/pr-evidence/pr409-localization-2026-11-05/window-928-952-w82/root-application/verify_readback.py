#!/usr/bin/env python3
"""Verify the full slskdN W928-W952 application readback."""
import argparse, collections, copy, hashlib, json, subprocess
from pathlib import Path
HEAD='6e48a342d4b1c43918c23da3afcbaad19c87a005'
TREE='b82ea7937cf9aa141a1c952283d5549dbe116ba5'
PRODUCT='807e0f1b6b21f8783483224aac01c159ccac08a5'
PRODUCT_TREE='80bdc60197d1549536a96fc52d071d8c2c44893c'
def sha(b): return hashlib.sha256(b).hexdigest()
def sth(s): return sha(s.encode('utf-8'))
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def readjl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def fail(s): raise SystemExit('FAIL: '+s)
def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--root-ledger',type=Path,required=True);p.add_argument('--candidate-free',type=Path,required=True);p.add_argument('--cross-review',type=Path,required=True);p.add_argument('--readback',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    repo=a.repo.resolve();plan=json.loads(a.plan.read_text(encoding='utf-8')); ledger=readjl(a.root_ledger);cand=readjl(a.candidate_free);cross=readjl(a.cross_review)
    if git(repo,'rev-parse','HEAD')!=PRODUCT or git(repo,'rev-parse','HEAD^')!=HEAD or git(repo,'rev-parse','HEAD^{tree}')!=PRODUCT_TREE: fail('product HEAD/parent/tree mismatch')
    if plan['sourcePin']!={'head':HEAD,'tree':TREE} or len(plan['changes'])!=34: fail('plan pin or selected count mismatch')
    if len(ledger)!=300 or len(cand)!=300 or len(cross)!=300: fail('full 300-cell matrix incomplete')
    cm={(x['continuationRank'],x['locale']):x for x in cand};xm={(x['continuationRank'],x['locale']):x for x in cross};lm={(x['continuationRank'],x['locale']):x for x in ledger}
    if len(cm)!=300 or set(cm)!=set(xm) or set(cm)!=set(lm): fail('cell key sets differ')
    changes={(x['continuationRank'],x['locale']):x for x in plan['changes']}
    if len(changes)!=34: fail('duplicate selected cell')
    catalog_meta={x['path']:x for x in plan['catalogs']}
    base={}; live={}; expected={}; all_raw={}
    for path,meta in catalog_meta.items():
        base_raw=subprocess.check_output(['git','-C',str(repo),'show',f'{HEAD}:{path}'])
        if sha(base_raw)!=meta['preimageSha256']: fail('base catalog hash mismatch '+path)
        data=json.loads(base_raw)
        if len(data)!=meta['entryCount'] or sha(('\n'.join(data.keys())+'\n').encode())!=meta['orderedKeySha256']: fail('base catalog structure mismatch '+path)
        base[path]=data;expected[path]=copy.deepcopy(data)
        raw=(repo/path).read_bytes(); now=json.loads(raw)
        if raw!=(json.dumps(now,ensure_ascii=False,indent=2)+'\n').encode(): fail('live serialization mismatch '+path)
        live[path]=now;all_raw[path]=raw
    readback=[];counts=collections.Counter();changed=0
    for key in sorted(cm):
        c=cm[key];x=xm[key];r=lm[key];change=changes.get(key)
        if (c['sourceId']!=x['sourceId'] or c['sourceSha256']!=x['sourceSha256'] or c['currentTargetSha256']!=x['currentTargetSha256'] or c['callerContextSha256']!=x['callerContextSha256'] or c['callerCount']!=x['callerCount']): fail('candidate/cross binding mismatch '+str(key))
        if sth(c['currentTarget'])!=c['currentTargetSha256']: fail('candidate target hash mismatch '+str(key))
        if r['sourceId']!=c['sourceId'] or r['sourceSha256']!=c['sourceSha256'] or r['currentTargetSha256']!=c['currentTargetSha256'] or r['callerContextSha256']!=c['callerContextSha256'] or r['callerCount']!=c['callerCount']: fail('root ledger hash binding mismatch '+str(key))
        path=c['catalogPath']; catalog_key=c['source']
        if path not in live or catalog_key not in live[path]: fail('live catalog key missing '+str(key))
        observed=live[path][catalog_key]
        target=change['selectedTarget'] if change else c['currentTarget']
        if observed!=target or sth(observed)!=sth(target): fail('cell readback mismatch '+str(key))
        if change:
            if x['crossDisposition'] not in ('correction','refinement') or change['selectedTargetSha256']!=x['selectedTargetSha256']: fail('selected cell is not cross-reviewed '+str(key))
            expected[path][catalog_key]=target
            counts['accept-'+x['crossDisposition']]+=1;changed+=observed!=c['currentTarget']
        elif x['crossDisposition']=='hold':
            if r['rootDisposition'] not in ('hold-callerless','hold-qualified-language-review') or r.get('source') is not None or r.get('currentTarget') is not None or r.get('selectedTarget') is not None: fail('held row is not text-free '+str(key))
            if observed!=c['currentTarget']: fail('held cell changed '+str(key))
            if c['callerCount']==0:
                if r['rootDisposition']!='hold-callerless' or key[0]!=944: fail('callerless hold mismatch '+str(key))
                counts['hold-callerless']+=1
            else:
                if r['rootDisposition']!='hold-qualified-language-review' or key[0]!=950 or key[1] not in ('de','fr','hi'): fail('language hold mismatch '+str(key))
                counts['hold-qualified-language-review']+=1
        else:
            if x['crossDisposition']!='accept-current' or r['rootDisposition']!='accept-current' or observed!=c['currentTarget']: fail('unselected current cell changed '+str(key))
            counts['accept-current']+=1
        row={'continuationRank':key[0],'remainingQueueRank':c['remainingQueueRank'],'sourceId':c['sourceId'],'locale':key[1],'sourceSha256':c['sourceSha256'],'callerContextSha256':c['callerContextSha256'],'callerCount':c['callerCount'],'beforeTargetSha256':c['currentTargetSha256'],'expectedAfterSha256':sth(target),'observedAfterSha256':sth(observed),'changed':observed!=c['currentTarget'],'rootDisposition':r['rootDisposition']}
        if not c['callerCount']:
            pass
        elif change:
            row.update({'source':c['source'],'beforeTarget':c['currentTarget'],'afterTarget':observed})
        readback.append(row)
    if changed!=34: fail('expected exactly 34 changed cells')
    for path in live:
        if live[path]!=expected[path]: fail('non-target catalog values changed '+path)
        if len(live[path])!=6175 or list(live[path])!=list(base[path]): fail('catalog key count/order changed '+path)
    raw_status=subprocess.check_output(['git','-C',str(repo),'status','--porcelain=v1'],text=True).splitlines()
    status={line[3:] for line in raw_status if len(line)>=4}
    diff=set(git(repo,'diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines());expected_paths={p for p in live if any(c['catalogPath']==p for c in plan['changes'])}
    if diff!=expected_paths or status: fail('product commit paths or working tree unexpected')
    if any(p.startswith('.github/workflows/') for p in diff): fail('workflow path changed')
    a.readback.parent.mkdir(parents=True,exist_ok=True)
    a.readback.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in readback),encoding='utf-8')
    result={'result':'PASS','inputHead':HEAD,'inputTree':TREE,'head':PRODUCT,'tree':PRODUCT_TREE,'candidateCells':300,'observedChangedCells':changed,'dispositionCounts':dict(counts),'changedCatalogCount':len(expected_paths),'changedPaths':sorted(expected_paths),'allCatalogKeysPreserved':True,'allNonTargetCatalogValuesPreserved':True,'all12CatalogsReadBack':len(live)==12,'callerlessAndLanguageHoldsTextFree':True,'workflowChanges':0,'readbackSha256':sha(a.readback.read_bytes()),'postimageHashes':{p:sha(raw) for p,raw in all_raw.items()}}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='postimageHashes'},sort_keys=True))
if __name__=='__main__':main()
