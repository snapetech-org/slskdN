#!/usr/bin/env python3
"""Verify the W1003-W1027 review packets and exact product catalog commit."""
import argparse, collections, hashlib, json, re, subprocess
from pathlib import Path
BASE=Path(__file__).resolve().parent
CF=BASE/'candidate-free'; PRIMARY=BASE/'primary-review'; BLIND=BASE/'blind-review'
CROSS=BASE/'cross-review'; ADVISORY=BASE/'advisory-review'; ROOT=BASE/'root-adjudication'; APP=BASE/'root-application'
HEAD='8c752c49281418fdd96341ed46f5c321627b625f'; TREE='b930b0d82679e843849e54456f3250e422c4682c'
PRODUCT='1f93b356f08b7c4bf7b2876d9d541b97dc03b82f'
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def verify_sums(d):
 p=d/'SHA256SUMS.txt'
 if not p.exists(): return False
 r=subprocess.run(['sha256sum','-c','SHA256SUMS.txt'],cwd=d,capture_output=True,text=True)
 assert r.returncode==0,(d,r.stdout,r.stderr)
 return True
def token_ok(source,target,protected):
 pats=[r'\{[^{}]+\}',r'<[^>]+>',r'(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])']
 return all(collections.Counter(re.findall(p,source))==collections.Counter(re.findall(p,target)) for p in pats) and all(x in target for x in protected)
def verify(repo):
 repo=Path(repo).resolve()
 for d in (BASE,CF,PRIMARY,BLIND,CROSS,ADVISORY,ROOT,APP): verify_sums(d)
 # Verify the blind packet and its candidate-free inputs using the correct pinned directories.
 r=subprocess.run(['sha256sum','-c','../blind-review/input-SHA256SUMS.txt'],cwd=CF,capture_output=True,text=True)
 assert r.returncode==0,(r.stdout,r.stderr)
 cfraw=[x for x in (CF/'source-current-cells.jsonl').read_bytes().splitlines() if x.strip()]
 cfs=[json.loads(x) for x in cfraw]; cm={(r['continuationRank'],r['locale']):r for r in cfs}
 rowhash={(r['continuationRank'],r['locale']):sha(line) for r,line in zip(cfs,cfraw)}
 pm={(r['continuationRank'],r['locale']):r for r in jl(PRIMARY/'primary-review.jsonl')}
 ph={(r['continuationRank'],r['locale']):r for r in jl(PRIMARY/'holds-hash-only.jsonl')}
 bm={(r['continuationRank'],r['locale']):r for r in jl(BLIND/'review-cells.jsonl')}
 xm={(r['continuationRank'],r['locale']):r for r in jl(CROSS/'cross-review.jsonl')}
 am={(r['continuationRank'],r['locale']):r for r in jl(ADVISORY/'findings.jsonl')}
 rootrows=jl(ROOT/'root-disposition-ledger.jsonl'); selected=jl(ROOT/'selected-targets.jsonl'); overrides=jl(ROOT/'root-overrides.jsonl')
 assert len(cm)==len(bm)==len(xm)==len(rootrows)==300 and len(pm)==288 and len(ph)==12 and len(selected)==71 and len(overrides)==4
 assert set(cm)==set(bm)==set(xm) and set(cm)==set(pm)|set(ph)
 counts=collections.Counter()
 for r in rootrows:
  k=(r['continuationRank'],r['locale']); c,b,x=cm[k],bm[k],xm[k]; p=pm.get(k,ph.get(k))
  assert p is not None and r['exactHead']==HEAD and r['exactTree']==TREE
  assert r['candidateFreeRowSha256']==rowhash[k]
  assert r['sourceSha256']==c['sourceSha256']==x['sourceSha256']
  assert r['currentTargetSha256']==c['currentTargetSha256']==x['currentTargetSha256']
  assert r['callerContextSha256']==c['callerContextSha256']==x['callerContextSha256']
  assert r['primaryDisposition']==p['disposition'] and r['blindDecision']==b['decision']
  if c['candidateFreeHold']:
   assert r['rootDisposition']=='hold-hash-only' and r['rootTarget'] is None
   assert not any(f in r for f in ('source','sourceId','currentTarget'))
   assert r['sourceTextIncluded'] is False and r['currentTargetTextIncluded'] is False
  else:
   assert r['source']==c['source']==x['source'] and r['sourceId']==c['sourceId']
   assert r['currentTarget']==c['currentTarget']==x['currentTarget']
   assert tsha(r['rootTarget'])==r['rootTargetSha256']
   protected=c['tokenEvidence']['protectedLiterals']['source']
   assert token_ok(c['source'],r['rootTarget'],protected)
   if r['rootDisposition']=='accept-current': assert r['rootTarget']==c['currentTarget'] and x['crossDisposition']=='accept-current'
   else: assert r['rootDisposition']=='correction' and x['crossDisposition']=='correction'
  counts[r['rootDisposition']]+=1
 assert counts=={'accept-current':217,'correction':71,'hold-hash-only':12}
 att=j(ROOT/'input-attestation.json'); iv=j(ROOT/'input-verifier-results.json')
 assert att['head']==HEAD and att['tree']==TREE and att['rootOverrides']==4
 assert all(iv[k]['result']=='PASS' for k in ('candidateFree','primary','cross','advisory'))
 assert iv['blind']['checksums']=='PASS' and iv['blind']['candidateFreeInputChecksums']=='PASS'
 assert all(iv[k]['head']==HEAD and iv[k]['tree']==TREE for k in ('candidateFree','primary','blind','cross'))
 assert att['resultingActiveHolds']==421
 assert len(am)==71 and len(overrides)==4
 override_map={(r['continuationRank'],r['locale']):r for r in overrides}
 for r in overrides:
  k=(r['continuationRank'],r['locale']); a=am[k]; x=xm[k]; d=next(q for q in selected if (q['continuationRank'],q['locale'])==k)
  assert a['suggestedAlternative']==r['rootTarget']==d['after']
  assert a['crossRecommendation']==x['crossTarget']==r['crossTarget']
  assert r['callerContextSha256']==x['callerContextSha256'] and tsha(r['rootTarget'])==r['rootTargetSha256']
 # Product commit is exactly the reviewed catalog change set following the pinned input head.
 assert git(repo,'rev-parse',PRODUCT+'^')==HEAD
 names=git(repo,'diff-tree','--no-commit-id','--name-only','-r',PRODUCT).splitlines()
 assert len(names)==12 and all(p.startswith('src/web/public/locales/') and p.endswith('.json') for p in names)
 assert all(not p.startswith('.github/workflows/') for p in names)
 app=j(APP/'application-summary.json')
 assert app['productCommit']==PRODUCT and app['commitParent']==HEAD and app['productCommitNames']==names
 readback={(r['continuationRank'],r['locale']):r for r in jl(APP/'final-head-readback.jsonl')}
 assert len(readback)==300
 catalog_paths=sorted({r['catalogPath'] for r in xm.values() if not r['candidateFreeHold']})
 assert set(names)==set(catalog_paths)
 for path in catalog_paths:
  before=subprocess.check_output(['git','-C',str(repo),'show',f'{HEAD}:{path}'])
  after=subprocess.check_output(['git','-C',str(repo),'show',f'{PRODUCT}:{path}'])
  data=json.loads(before); expected=json.loads(before)
  assert sha(before)==next(r['catalogFileSha256'] for r in xm.values() if r['catalogPath']==path)
  assert len(data)==6175 and (json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')==before
  for r in selected:
   if r['catalogPath']==path: expected[r['source']]=r['after']
  assert (json.dumps(expected,ensure_ascii=False,indent=2)+'\n').encode('utf-8')==after
  assert list(data)==list(json.loads(after)) and len(json.loads(after))==6175
  assert sha(after)==app['catalogHashesAfter'][path]
 for k,c in cm.items():
  rd=next(r for r in rootrows if (r['continuationRank'],r['locale'])==k)
  rb=readback[k]
  assert rb['sourceSha256']==c['sourceSha256'] and rb['beforeSha256']==c['currentTargetSha256']
  assert rb['callerContextSha256']==c['callerContextSha256']
  if c['candidateFreeHold']:
   assert rb['disposition']=='hold-hash-only' and rb['afterSha256']==c['currentTargetSha256']
   assert not any(f in rb for f in ('source','sourceId','before','after'))
  else:
   assert rb['source']==c['source'] and rb['after']==rd['rootTarget']
   assert rb['afterSha256']==tsha(rb['after'])
 if git(repo,'rev-parse','HEAD')!=PRODUCT:
  assert subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',PRODUCT,'HEAD']).returncode==0
 return {'result':'PASS','window':'W1003-W1027','inputHead':HEAD,'inputTree':TREE,'productCommit':PRODUCT,
   'rootDispositionCounts':dict(counts),'changedCells':71,'changedLocaleCatalogs':12,'reviewedCells':300,
   'rootOverrides':4,'hashOnlyHolds':12,'activeHolds':421,'catalogKeysPerLocale':6175,
   'packetChecksums':'PASS','exactCatalogReadback':'PASS','workflowChanges':'none'}
if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True); a=ap.parse_args()
 print(json.dumps(verify(a.repo),ensure_ascii=False,indent=2))
