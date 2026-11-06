#!/usr/bin/env python3
"""Apply only the 34 root-adjudicated, hash-pinned slskdN W82 values."""
import argparse, collections, hashlib, json, os, subprocess, tempfile
from pathlib import Path
HEAD='6e48a342d4b1c43918c23da3afcbaad19c87a005'
TREE='b82ea7937cf9aa141a1c952283d5549dbe116ba5'
def sha(b): return hashlib.sha256(b).hexdigest()
def sth(s): return sha(s.encode('utf-8'))
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def fail(s): raise SystemExit('FAIL: '+s)
def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    repo=a.repo.resolve();plan=json.loads(a.plan.read_text(encoding='utf-8'))
    if git(repo,'rev-parse','HEAD')!=HEAD or git(repo,'rev-parse','HEAD^{tree}')!=TREE: fail('exact source HEAD/tree mismatch')
    if git(repo,'status','--porcelain=v1'): fail('worktree is not clean before apply')
    if plan['sourcePin']!={'head':HEAD,'tree':TREE} or len(plan['changes'])!=34 or plan['candidateCells']!=300: fail('plan source or dimensions mismatch')
    catalogs={}; before={}; keysets={}; paths=set()
    for meta in plan['catalogs']:
        path=meta['path'];paths.add(path);raw=(repo/path).read_bytes()
        if sha(raw)!=meta['preimageSha256']: fail('catalog preimage hash mismatch '+path)
        data=json.loads(raw)
        if len(data)!=meta['entryCount']: fail('catalog entry count mismatch '+path)
        if raw!=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode(): fail('catalog serialization mismatch '+path)
        if sha(('\n'.join(data.keys())+'\n').encode())!=meta['orderedKeySha256']: fail('catalog key-order hash mismatch '+path)
        catalogs[path]=data;before[path]=raw;keysets[path]=list(data)
    seen=set(); bypath=collections.defaultdict(list)
    for c in plan['changes']:
        cell=(c['sourceId'],c['locale'])
        if cell in seen: fail('duplicate selected cell '+str(cell))
        seen.add(cell);path=c['catalogPath']
        if path not in catalogs: fail('selected catalog missing from pins '+path)
        if sth(c['selectedTarget'])!=c['selectedTargetSha256']: fail('selected target hash mismatch '+str(cell))
        data=catalogs[path]
        catalog_key=c['source']
        if catalog_key not in data: fail('source key missing from catalog '+str(cell))
        current=data[catalog_key]
        if current!=c['currentTarget'] or sth(current)!=c['currentTargetSha256']: fail('current target hash/value mismatch '+str(cell))
        bypath[path].append(c)
    if len(seen)!=34 or not bypath: fail('application row count mismatch')
    for path,items in bypath.items():
        data=catalogs[path]
        for c in items: data[c['source']]=c['selectedTarget']
        if list(data)!=keysets[path]: fail('catalog order changed in memory '+path)
        output=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode();temp=None
        try:
            with tempfile.NamedTemporaryFile(prefix='.w82-',suffix='.tmp',dir=(repo/path).parent,delete=False) as f:
                f.write(output);f.flush();os.fsync(f.fileno());temp=f.name
            os.replace(temp,repo/path)
        finally:
            if temp and os.path.exists(temp): os.unlink(temp)
        if (repo/path).read_bytes()!=output: fail('postimage write mismatch '+path)
    changed=set(git(repo,'diff','--name-only').splitlines())
    status_text=subprocess.check_output(['git','-C',str(repo),'status','--porcelain=v1'],text=True)
    status={line[3:] for line in status_text.splitlines() if len(line)>=4}
    expected={p for p,rows in bypath.items() if rows}
    if changed!=expected or status!=expected: fail('working paths are not exactly selected locale catalogs')
    if any(p.startswith('.github/workflows/') for p in changed): fail('workflow path changed')
    result={'result':'PASS','sourcePin':plan['sourcePin'],'candidateCells':300,'selectedChanges':34,'changedCatalogCount':len(expected),'changedCatalogPaths':sorted(expected),'workflowChanges':0,'catalogs':[],'hooks':{'preCommit':'not run; commit with hooks disabled because scans/tests are not authorized','prePush':'not run; push with hooks disabled because scans/tests are not authorized'}}
    for m in plan['catalogs']:
        path=m['path'];raw=(repo/path).read_bytes();data=json.loads(raw)
        result['catalogs'].append({'locale':m['locale'],'path':path,'preimageSha256':sha(before[path]),'postimageSha256':sha(raw),'entryCount':len(data),'orderedKeySha256':sha(('\n'.join(data.keys())+'\n').encode()),'changedCellCount':len(bypath.get(path,[]))})
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'result':'PASS','selectedChanges':34,'changedCatalogCount':len(expected),'changedPaths':sorted(expected)},sort_keys=True))
if __name__=='__main__':main()
