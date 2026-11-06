#!/usr/bin/env python3
"""Guarded slskdN W1028-W1052 localization application and readback."""
from __future__ import annotations
import argparse, copy, hashlib, json, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=HERE.parent if HERE.name=='root-application' else HERE
REPO: Path
ROOT=BASE/'root-adjudication'; APP=BASE/'root-application'
LEDGER=ROOT/'root-disposition-ledger.jsonl'; PLAN=ROOT/'root-selected-targets.jsonl'; SUMMARY=ROOT/'summary.json'
PREFLIGHT=APP/'preflight.json'; PRODUCT_PIN=APP/'product-pin.json'; READBACK=APP/'final-head-readback.jsonl'; APP_SUMMARY=APP/'application-summary.json'
def sha(v): return hashlib.sha256(v.encode('utf-8') if isinstance(v,str) else v).hexdigest()
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def write_rows(p,rs): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rs),encoding='utf-8')
def git(*args): return subprocess.check_output(['git',*args],cwd=REPO,text=True).strip()
def gitshow(rev,path): return subprocess.check_output(['git','show',f'{rev}:{path}'],cwd=REPO)
def key_for_hash(data,source_sha):
 keys=[k for k in data if sha(k)==source_sha]
 if len(keys)!=1: raise SystemExit('hash-only source key mapping is not unique')
 return keys[0]
def main():
 global REPO
 ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=Path,required=True); g=ap.add_mutually_exclusive_group(required=True); g.add_argument('--preflight',action='store_true'); g.add_argument('--apply',action='store_true'); g.add_argument('--verify-after',action='store_true'); a=ap.parse_args(); REPO=a.repo.resolve()
 ledger=rows(LEDGER); plan=rows(PLAN); summary=json.loads(SUMMARY.read_text(encoding='utf-8'))
 head=summary['head']; tree=summary['tree']
 if len(ledger)!=300 or len(plan)!=44: raise SystemExit('root ledger/plan cardinality mismatch')
 grouped={}
 for r in ledger: grouped.setdefault(r['catalogPath'],[]).append(r)
 if len(grouped)!=12: raise SystemExit('expected 12 locale catalogs')
 if a.preflight or a.apply:
  if git('rev-parse','HEAD')!=head or git('rev-parse','HEAD^{tree}')!=tree: raise SystemExit('exact input head/tree mismatch')
  if git('status','--porcelain'): raise SystemExit('worktree must be clean before catalog application')
  baseline_rev=head
 else:
  if not PRODUCT_PIN.exists(): raise SystemExit('product-pin.json is missing')
  pin=json.loads(PRODUCT_PIN.read_text(encoding='utf-8')); product=pin['productCommit']
  if git('rev-parse',f'{product}^{{tree}}')!=pin['productTree']: raise SystemExit('product commit/tree mismatch')
  if subprocess.run(['git','merge-base','--is-ancestor',product,'HEAD'],cwd=REPO).returncode: raise SystemExit('product commit is not an ancestor of HEAD')
  baseline_rev=head
 expected_catalogs={}; baseline_hashes={}
 for path,cells in grouped.items():
  raw=gitshow(baseline_rev,path)
  hashes={r['catalogFileSha256'] for r in cells}
  if len(hashes)!=1 or sha(raw)!=next(iter(hashes)): raise SystemExit(f'baseline catalog hash mismatch: {path}')
  data=json.loads(raw.decode('utf-8'))
  if len(data)!=6175 or (json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')!=raw: raise SystemExit(f'catalog shape/serialization mismatch: {path}')
  expected=copy.deepcopy(data)
  for r in cells:
   if r['rootDisposition']=='hold-hash-only':
    key=key_for_hash(data,r['sourceSha256'])
    if sha(data[key])!=r['currentTargetSha256']: raise SystemExit(f'hash-only hold mismatch: {r["continuationRank"]}::{r["locale"]}')
   else:
    key=r['sourceKey']
    if key not in data or data[key]!=r['currentTarget'] or sha(data[key])!=r['currentTargetSha256']:
     raise SystemExit(f'current target mismatch: {path}::{r["continuationRank"]}::{r["locale"]}')
  for e in (x for x in plan if x['catalogPath']==path):
   if expected.get(e['sourceKey'])!=e['before'] or sha(expected[e['sourceKey']])!=e['beforeSha256']:
    raise SystemExit(f'exact plan before-hash mismatch: {e["continuationRank"]}::{e["locale"]}')
   if sha(e['after'])!=e['afterSha256']: raise SystemExit(f'exact after-hash mismatch: {e["continuationRank"]}::{e["locale"]}')
   expected[e['sourceKey']]=e['after']
  expected_catalogs[path]=expected; baseline_hashes[path]=sha(raw)
 pre={'result':'PASS','window':'W1028-W1052','inputHead':head,'inputTree':tree,'reviewedCells':300,
  'selectedChanges':44,'rootOverrides':1,'acceptedCurrent':244,'hashOnlyHolds':12,'catalogs':12,'entriesPerCatalog':6175,
  'allCallerBackedCurrentHashesMatch':True,'allHashOnlyHoldHashesMatch':True,'allSelectedTargetHashesMatch':True,
  'baselineCatalogSha256':baseline_hashes}
 if a.preflight:
  PREFLIGHT.parent.mkdir(parents=True,exist_ok=True); PREFLIGHT.write_text(json.dumps(pre,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(pre,ensure_ascii=False,indent=2)); return
 if a.apply:
  for path,data in expected_catalogs.items(): (REPO/path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  PREFLIGHT.write_text(json.dumps({**pre,'catalogWritesCompleted':12,'productCommitCreated':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  print(json.dumps({**pre,'catalogWritesCompleted':12,'next':'commit focused catalogs, create product-pin.json, then run --verify-after'},ensure_ascii=False,indent=2)); return
 pin=json.loads(PRODUCT_PIN.read_text(encoding='utf-8')); readback=[]
 for path,cells in grouped.items():
  actual=(REPO/path).read_bytes(); committed=gitshow(pin['productCommit'],path)
  if actual!=committed: raise SystemExit(f'working catalog differs from pinned product commit: {path}')
  final=json.loads(actual.decode('utf-8')); base=json.loads(gitshow(head,path).decode('utf-8'))
  if len(final)!=6175 or list(final)!=list(base): raise SystemExit(f'catalog key/order mismatch after application: {path}')
  if final!=expected_catalogs[path]: raise SystemExit(f'full catalog readback mismatch: {path}')
  for r in cells:
   key=key_for_hash(final,r['sourceSha256']) if r['rootDisposition']=='hold-hash-only' else r['sourceKey']
   value=final[key]; digest=sha(value)
   if r['rootDisposition']=='hold-hash-only':
    if digest!=r['currentTargetSha256']: raise SystemExit(f'post-commit hold hash mismatch: {r["continuationRank"]}::{r["locale"]}')
    readback.append({'continuationRank':r['continuationRank'],'locale':r['locale'],'callerless':True,'sourceSha256':r['sourceSha256'],'beforeSha256':r['currentTargetSha256'],'afterSha256':digest,'textIncluded':False,'matches':True})
   else:
    if value!=r['rootTarget'] or digest!=r['rootTargetSha256']: raise SystemExit(f'post-commit cell mismatch: {r["continuationRank"]}::{r["locale"]}')
    readback.append({'continuationRank':r['continuationRank'],'locale':r['locale'],'callerless':False,'sourceId':r['sourceId'],'sourceKey':key,'disposition':r['rootDisposition'],'beforeSha256':r['currentTargetSha256'],'after':value,'afterSha256':digest,'textIncluded':True,'matches':True})
 if len(readback)!=300 or sum(r['callerless'] for r in readback)!=12: raise SystemExit('readback coverage mismatch')
 write_rows(READBACK,readback)
 report={**pre,'result':'PASS_POST_COMMIT_READBACK','productCommit':pin['productCommit'],'productTree':pin['productTree'],
  'verificationHead':git('rev-parse','HEAD'),'catalogsMatchPinnedProduct':True,'keyOrderPreserved':True,
  'readbackCells':300,'changedCells':44,'unchangedCells':244,'hashOnlyHoldsTextFree':12,'activeHoldsAfter':433,'nativeSpeakerApproval':False}
 APP_SUMMARY.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
