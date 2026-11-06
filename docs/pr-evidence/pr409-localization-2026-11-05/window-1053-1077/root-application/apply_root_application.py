#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, json, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent/'root-adjudication'
LEDGER=ROOT/'root-disposition-ledger.jsonl'; PLAN=ROOT/'root-selected-targets.jsonl'; SUMMARY=ROOT/'summary.json'
def sha(v): return hashlib.sha256(v.encode('utf-8') if isinstance(v,str) else v).hexdigest()
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def write_rows(p,rs): p.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rs),encoding='utf-8')
def git(repo,*args): return subprocess.check_output(['git',*args],cwd=repo,text=True).strip()
def gitshow(repo,rev,path): return subprocess.check_output(['git','show',f'{rev}:{path}'],cwd=repo)
def key_for_hash(data,source_sha):
 keys=[k for k in data if sha(k)==source_sha]
 if len(keys)!=1: raise SystemExit(f'hash-only source-key mapping not unique ({len(keys)})')
 return keys[0]
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True,type=Path); g=ap.add_mutually_exclusive_group(required=True); g.add_argument('--preflight',action='store_true'); g.add_argument('--apply',action='store_true'); g.add_argument('--verify-after',action='store_true'); a=ap.parse_args(); repo=a.repo.resolve()
 ledger=rows(LEDGER); plan=rows(PLAN); sm=json.loads(SUMMARY.read_text(encoding='utf-8')); head=sm['head']; tree=sm['tree']
 if len(ledger)!=300 or len(plan)!=54: raise SystemExit('root ledger/plan cardinality mismatch')
 grouped={}
 for r in ledger: grouped.setdefault(r['catalogPath'],[]).append(r)
 if len(grouped)!=12: raise SystemExit('expected 12 locale catalogs')
 if a.preflight or a.apply:
  if git(repo,'rev-parse','HEAD')!=head or git(repo,'rev-parse','HEAD^{tree}')!=tree: raise SystemExit('input head/tree mismatch')
  if git(repo,'status','--porcelain'): raise SystemExit('worktree must be clean before catalog application')
  baseline_rev=head
 else:
  pin=json.loads((HERE/'product-pin.json').read_text(encoding='utf-8')); product=pin['productCommit']
  if git(repo,'rev-parse',f'{product}^{{tree}}')!=pin['productTree']: raise SystemExit('product commit/tree mismatch')
  if subprocess.run(['git','merge-base','--is-ancestor',product,git(repo,'rev-parse','HEAD')],cwd=repo).returncode: raise SystemExit('product commit is not an ancestor')
  baseline_rev=head
 expected={}; base_hashes={}
 for path,cells in grouped.items():
  raw=gitshow(repo,baseline_rev,path); hashes={r['catalogFileSha256'] for r in cells}
  if len(hashes)!=1 or sha(raw)!=next(iter(hashes)): raise SystemExit(f'baseline catalog hash mismatch {path}')
  data=json.loads(raw.decode('utf-8'))
  if len(data)!=6175 or (json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')!=raw: raise SystemExit(f'catalog shape/serialization mismatch {path}')
  out=copy.deepcopy(data)
  for r in cells:
   if r['rootDisposition']=='hold-hash-only':
    key=key_for_hash(data,r['sourceSha256'])
    if sha(data[key])!=r['currentTargetSha256']: raise SystemExit(f"hash-only target mismatch {r['continuationRank']}::{r['locale']}")
   else:
    key=r['sourceKey']
    if data.get(key)!=r['currentTarget'] or sha(data[key])!=r['currentTargetSha256']: raise SystemExit(f"current target mismatch {r['continuationRank']}::{r['locale']}")
    if r['rootDisposition'] in ('accept-current','hold-low-confidence') and (r['rootTarget']!=r['currentTarget'] or r['rootTargetSha256']!=r['currentTargetSha256']): raise SystemExit(f"retained/held target changed {r['continuationRank']}::{r['locale']}")
  for e in (x for x in plan if x['catalogPath']==path):
   if out.get(e['sourceKey'])!=e['before'] or sha(out[e['sourceKey']])!=e['beforeSha256']: raise SystemExit(f"plan before-hash mismatch {e['continuationRank']}::{e['locale']}")
   if sha(e['after'])!=e['afterSha256']: raise SystemExit(f"plan after-hash mismatch {e['continuationRank']}::{e['locale']}")
   out[e['sourceKey']]=e['after']
  expected[path]=out; base_hashes[path]=sha(raw)
 pre={'result':'PASS','window':'W1053-W1077','inputHead':head,'inputTree':tree,'reviewedCells':300,
  'selectedChanges':54,'corrections':53,'refinements':1,'acceptedCurrent':214,'lowConfidenceHolds':8,
  'callerlessHashOnlyHolds':24,'priorActiveHashOnlyHolds':433,'activeHashOnlyHoldsAfter':457,
  'catalogs':12,'entriesPerCatalog':6175,'allCurrentHashesMatch':True,'allHashOnlyHoldHashesMatch':True,
  'allSelectedTargetHashesMatch':True,'baselineCatalogSha256':base_hashes}
 if a.preflight:
  (HERE/'preflight.json').write_text(json.dumps(pre,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(pre,ensure_ascii=False,indent=2)); return
 if a.apply:
  for path,data in expected.items(): (repo/path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  (HERE/'preflight.json').write_text(json.dumps({**pre,'catalogWritesCompleted':12,'productCommitCreated':False},ensure_ascii=False,indent=2)+'\n')
  print(json.dumps({**pre,'catalogWritesCompleted':12,'next':'commit the 12 locale catalogs, create product-pin.json, then run --verify-after'},ensure_ascii=False,indent=2)); return
 pin=json.loads((HERE/'product-pin.json').read_text(encoding='utf-8')); readback=[]
 for path,cells in grouped.items():
  actual=(repo/path).read_bytes()
  if actual!=gitshow(repo,pin['productCommit'],path): raise SystemExit(f'working catalog differs from product commit: {path}')
  final=json.loads(actual.decode('utf-8')); base=json.loads(gitshow(repo,head,path).decode('utf-8'))
  if len(final)!=6175 or list(final)!=list(base) or final!=expected[path]: raise SystemExit(f'full catalog readback mismatch: {path}')
  for r in cells:
   if r['rootDisposition']=='hold-hash-only':
    value=final[key_for_hash(final,r['sourceSha256'])]; digest=sha(value)
    if digest!=r['currentTargetSha256']: raise SystemExit(f"post-commit hold mismatch {r['continuationRank']}::{r['locale']}")
    readback.append({'continuationRank':r['continuationRank'],'locale':r['locale'],'callerless':True,'sourceSha256':r['sourceSha256'],'beforeSha256':digest,'afterSha256':digest,'textIncluded':False,'matches':True})
   else:
    value=final[r['sourceKey']]; digest=sha(value)
    if value!=r['rootTarget'] or digest!=r['rootTargetSha256']: raise SystemExit(f"post-commit cell mismatch {r['continuationRank']}::{r['locale']}")
    readback.append({'continuationRank':r['continuationRank'],'locale':r['locale'],'callerless':False,'sourceId':r['sourceId'],'sourceKey':r['sourceKey'],'disposition':r['rootDisposition'],'beforeSha256':r['currentTargetSha256'],'after':value,'afterSha256':digest,'textIncluded':True,'matches':True})
 if len(readback)!=300 or sum(x['callerless'] for x in readback)!=24: raise SystemExit('unexpected 300-cell readback coverage')
 write_rows(HERE/'final-head-readback.jsonl',readback)
 report={**pre,'result':'PASS_POST_COMMIT_READBACK','productCommit':pin['productCommit'],'productTree':pin['productTree'],
  'verificationHead':git(repo,'rev-parse','HEAD'),'catalogsMatchPinnedProduct':True,'keyOrderPreserved':True,
  'readbackCells':300,'changedCells':54,'unchangedCallerBackedCells':222,'lowConfidenceHolds':8,
  'callerlessHashOnlyHoldsTextFree':24,'activeHashOnlyHoldsAfter':457,'nativeSpeakerApproval':False}
 (HERE/'application-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
