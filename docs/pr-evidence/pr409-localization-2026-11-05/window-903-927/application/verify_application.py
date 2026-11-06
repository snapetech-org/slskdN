#!/usr/bin/env python3
"""Portable exact-product verification for slskdN PR #409 W81."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'application'
def need(ok,msg):
    if not ok: raise SystemExit('FAIL: '+msg)
def sha(data): return hashlib.sha256(data).hexdigest()
def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def rows(p): return [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args])
def verify_checksums():
    sums=ROOT/'SHA256SUMS.txt'
    expected={}
    for line in sums.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        digest,name=line.split('  ',1)
        need(name not in expected,'duplicate checksum entry')
        p=(ROOT/name).resolve()
        need(p.is_relative_to(ROOT.resolve()) and p.is_file(),'unsafe or missing checksum path '+name)
        need(sha(p.read_bytes())==digest,'checksum mismatch '+name)
        expected[name]=digest
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt' and '__pycache__' not in p.parts}
    need(set(expected)==actual,'evidence file inventory differs from checksum list')
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo',required=True)
    args=parser.parse_args(); repo=Path(args.repo).resolve()
    verify_checksums()
    summary=readj(APP/'application-summary.json'); product=readj(APP/'product-commit.json')
    cells=rows(ROOT/'candidate-free/source-current-cells.jsonl')
    selected=rows(ROOT/'root-manual-review/selected-dispositions.jsonl')
    applied=rows(APP/'application-plan.jsonl'); readback=rows(APP/'application-readback-300-cells.jsonl')
    structure=rows(ROOT/'candidate-free/catalog-structure.jsonl')
    post=readj(APP/'catalog-preimage-and-postimage.json')
    need(len(cells)==300 and len(selected)==64 and len(applied)==64 and len(readback)==300,'cell/selection counts')
    commit=summary['productCommit']
    need(product['commit']==commit and product['tree']==summary['productTree'] and product['parent']==summary['headBefore'],'product commit record')
    need(git(repo,'rev-parse',f'{commit}^').decode().strip()==summary['headBefore'],'product parent')
    need(git(repo,'rev-parse',f'{commit}^{{tree}}').decode().strip()==summary['productTree'],'product tree')
    paths=git(repo,'diff-tree','--no-commit-id','--name-only','-r',commit).decode().splitlines()
    expected_paths={r['catalogPath'] for r in structure}
    need(set(paths)==expected_paths and len(paths)==12 and all(p.startswith('src/web/public/locales/') for p in paths),'product commit paths')
    selected_map={(r['continuationRank'],r['locale']):r for r in selected}
    read_map={(r['continuationRank'],r['locale']):r for r in readback}
    need(len(read_map)==300,'duplicate readback rows')
    file_by_locale={r['locale']:r for r in post['catalogs']}
    need(len(file_by_locale)==12 and len(structure)==12,'catalog manifest count')
    counts={'applied':0,'retain-current':0,'hold':0}
    for rec in structure:
        locale=rec['locale']; path=rec['catalogPath']; data=git(repo,'show',f'{commit}:{path}')
        need(sha(data)==file_by_locale[locale]['postimageSha256'],'postimage file hash '+locale)
        blob=git(repo,'rev-parse',f'{commit}:{path}').decode().strip()
        need(blob==file_by_locale[locale]['postimageGitBlob'],'postimage git blob '+locale)
        image=(APP/'postimages'/f'{locale}.json').read_bytes()
        need(image==data,'postimage snapshot '+locale)
        obj=json.loads(data.decode('utf-8'))
        need(len(obj)==6176,'catalog key count '+locale)
        orderhash=sha(('\n'.join(obj.keys())+'\n').encode())
        need(orderhash==rec['orderedKeySha256']==file_by_locale[locale]['orderedKeySha256'],'catalog key order '+locale)
    for cell in cells:
        key=(cell['continuationRank'],cell['locale']); locale=cell['locale']; r=read_map[key]
        need(r['sourceId']==cell['sourceId'] and r['sourceSha256']==cell['sourceSha256'],'source binding '+str(key))
        need(r['callerContextSha256']==cell['callerContextSha256'],'caller context '+str(key))
        need(r['beforeTargetSha256']==cell['currentTargetSha256'] and r['beforeTarget']==cell['currentTarget'],'preimage binding '+str(key))
        obj=json.loads(git(repo,'show',f"{commit}:{cell['catalogPath']}").decode('utf-8'))
        actual=obj[cell['catalogKey']]
        need(actual==r['afterTarget'] and sha(actual.encode())==r['afterTargetSha256'],'actual target '+str(key))
        if key in selected_map:
            target=selected_map[key]
            need(actual==target['target'] and r['state']=='applied' and sha(actual.encode())==target['targetSha256'],'selected target '+str(key))
            counts['applied']+=1
        else:
            need(actual==cell['currentTarget'],'unchanged target '+str(key))
            if cell['continuationRank']==910:
                need(r['state']=='hold','rank 910 hold '+str(key)); counts['hold']+=1
            else:
                need(r['state']=='retain-current','retained target '+str(key)); counts['retain-current']+=1
    need(counts=={'applied':64,'retain-current':224,'hold':12},'final disposition counts')
    live=readj(APP/'live-after-product-push.json')
    need(live['headRefOid']==commit and live['branchRefOid']==commit and live['pullRefOid']==commit,'remote PR refs')
    need(live['state']=='open' and live['draft'] and not live['merged'] and live['workflowFilePaths']==[],'PR state/workflows')
    need((live['checkRunCount'],live['statusContextCount'],live['deploymentCount'])==(0,0,0),'exact-product checks/status/deployments')
    r910=readj(APP/'rank910-reattestation-after-w903-product.json')
    need(r910['head']==commit and r910['sourceAndRuntimePinsUnchanged'] and r910['branchRefOid']==commit and r910['pullRefOid']==commit,'rank-910 product-head reattestation')
    print(json.dumps({'result':'PASS','productCommit':commit,'cells':300,'applied':counts['applied'],'retained':counts['retain-current'],'holds':counts['hold'],'catalogs':12,'keyOrderPreserved':True,'workflowPaths':[],'checks':0,'statuses':0,'deployments':0}))
if __name__=='__main__': main()
