#!/usr/bin/env python3
"""Apply and read back slskdN W1003-W1027 using exact source/target hashes."""
import argparse, collections, hashlib, json, re, subprocess
from pathlib import Path
TASK=Path(__file__).resolve().parents[1]
CF=TASK/'candidate-free'; ROOT=TASK/'root-adjudication'; APP=TASK/'root-application'
HEAD='8c752c49281418fdd96341ed46f5c321627b625f'; TREE='b930b0d82679e843849e54456f3250e422c4682c'
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def token_ok(source,target,protected):
 patterns=[r'\{[^{}]+\}',r'<[^>]+>',r'(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])']
 return all(collections.Counter(re.findall(p,source))==collections.Counter(re.findall(p,target)) for p in patterns) and all(x in target for x in protected)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=Path,required=True); ap.add_argument('--apply',action='store_true'); ap.add_argument('--verify-only',action='store_true'); a=ap.parse_args(); repo=a.repo.resolve()
 assert git(repo,'rev-parse','HEAD')==HEAD and git(repo,'rev-parse','HEAD^{tree}')==TREE
 assert git(repo,'status','--porcelain=v1','--untracked-files=all')==''
 cfraw=[x for x in (CF/'source-current-cells.jsonl').read_bytes().splitlines() if x.strip()]
 cfrows=[json.loads(x) for x in cfraw]; cm={(r['continuationRank'],r['locale']):r for r in cfrows}
 xm={(r['continuationRank'],r['locale']):r for r in rows(TASK/'cross-review'/'cross-review.jsonl')}
 rootrows=rows(ROOT/'root-disposition-ledger.jsonl'); decisions={(r['continuationRank'],r['locale']):r for r in rootrows}
 selected=rows(ROOT/'selected-targets.jsonl')
 assert len(cm)==len(xm)==len(decisions)==300 and len(selected)==71
 expected={r['catalogPath']:r['catalogFileSha256'] for r in xm.values() if not r['candidateFreeHold']}
 assert len(expected)==12
 paths=sorted(expected)
 before={}; before_data={}; after_data={}; modifications=[]
 for path in paths:
  raw=subprocess.check_output(['git','-C',str(repo),'show',f'{HEAD}:{path}'])
  assert sha(raw)==expected[path]
  data=json.loads(raw)
  assert len(data)==6175 and (json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')==raw
  before[path]=raw; before_data[path]=data; after_data[path]=json.loads(raw)
 catalog_updates=collections.defaultdict(list)
 for r in selected:
  k=(r['continuationRank'],r['locale']); c=cm[k]; x=xm[k]; rd=decisions[k]
  assert r['sourceId']==c['sourceId'] and r['source']==c['source'] and r['before']==c['currentTarget']
  assert r['sourceSha256']==c['sourceSha256'] and r['beforeSha256']==c['currentTargetSha256']
  assert r['callerContextSha256']==c['callerContextSha256']
  assert r['afterSha256']==tsha(r['after']) and r['after']==rd['rootTarget']
  assert rd['rootDisposition']=='correction' and rd['rootTargetSha256']==tsha(r['after'])
  assert token_ok(r['source'],r['after'],c.get('sourceProtectedLiterals',[])) if 'sourceProtectedLiterals' in c else token_ok(r['source'],r['after'],c['tokenEvidence']['protectedLiterals']['source'])
  path=r['catalogPath']; data=after_data[path]; source=r['source']
  assert source in data and data[source]==r['before'] and tsha(data[source])==r['beforeSha256']
  data[source]=r['after']; catalog_updates[path].append(r)
  modifications.append({'continuationRank':r['continuationRank'],'remainingQueueRank':r['remainingQueueRank'],
   'locale':r['locale'],'catalogPath':path,'sourceId':r['sourceId'],'source':source,
   'before':r['before'],'beforeSha256':r['beforeSha256'],'after':r['after'],'afterSha256':r['afterSha256'],
   'rootOverrideApplied':r['overrideApplied']})
 assert len(modifications)==71 and len(catalog_updates)==12
 expected_changed=set((r['catalogPath'],r['source']) for r in selected)
 output={}
 for path in paths:
  data=after_data[path]
  raw=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
  old=before_data[path]; changed=[]
  for key,value in old.items():
   if data[key]!=value: changed.append((key,value,data[key]))
  assert {(path,k) for k,_,_ in changed}=={x for x in expected_changed if x[0]==path}
  assert list(old)==list(data) and len(data)==6175
  output[path]=raw
 if a.apply:
  for path,raw in output.items(): (repo/path).write_bytes(raw)
 elif not a.verify_only:
  raise SystemExit('select --apply or --verify-only')
 readback=[]
 for key in sorted(cm):
  c=cm[key]; d=decisions[key]
  if c['candidateFreeHold']:
   assert d['rootDisposition']=='hold-hash-only' and d['rootTarget'] is None
   readback.append({'continuationRank':key[0],'remainingQueueRank':c['remainingQueueRank'],'locale':key[1],
    'sourceSha256':c['sourceSha256'],'beforeSha256':c['currentTargetSha256'],
    'afterSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],
    'disposition':'hold-hash-only','sourceTextIncluded':False,'targetTextIncluded':False})
  else:
   path=c['catalogPath']; target=after_data[path][c['source']]
   assert tsha(target)==d['rootTargetSha256']
   readback.append({'continuationRank':key[0],'remainingQueueRank':c['remainingQueueRank'],'locale':key[1],
    'sourceId':c['sourceId'],'source':c['source'],'sourceSha256':c['sourceSha256'],
    'before':c['currentTarget'],'beforeSha256':c['currentTargetSha256'],'after':target,'afterSha256':tsha(target),
    'callerContextSha256':c['callerContextSha256'],'disposition':d['rootDisposition'],
    'sourceTextIncluded':True,'targetTextIncluded':True})
 if a.apply:
  for path in paths: assert (repo/path).read_bytes()==output[path]
  (APP/'final-head-readback.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in readback),encoding='utf-8')
  summary={'artifact':'slskdN PR #409 W1003-W1027 exact-hash application','inputHead':HEAD,'inputTree':TREE,
   'changedCellCount':71,'changedCatalogCount':12,'reviewedCells':300,'callerBackedCells':288,
   'unchangedCallerBackedCells':217,'callerlessHashOnlyHolds':12,'catalogKeysPerLocale':6175,
   'allNonTargetValuesUnchanged':True,'catalogKeyOrderPreserved':True,'heldTextRedacted':True,
   'activePriorHoldsReattested':409,'resultingActiveHolds':421,
   'rootOverridesApplied':4,'rootOverrideRanksLocales':[
     {'rank':1004,'locale':'fr'},{'rank':1004,'locale':'hi'},{'rank':1004,'locale':'id'},{'rank':1021,'locale':'vi'}],
   'catalogHashesAfter':{p:sha(raw) for p,raw in output.items()},'productCommitPending':True,
   'nativeSpeakerApproval':False,'headedBrowserReviewPerformed':False}
  (APP/'application-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'result':'PASS','changedCellCount':71,'changedCatalogCount':12,
  'reviewedCells':300,'callerBacked':288,'retainedCurrent':217,'hashOnlyHolds':12,
  'rootOverrides':4,'keyOrderPreserved':True,'allNonTargetValuesUnchanged':True,
  'readback':str(APP/'final-head-readback.jsonl') if a.apply else 'verify-only'},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
