#!/usr/bin/env python3
"""Attest the sealed candidate-free W55 input without opening any review ledger."""
from pathlib import Path
import collections, hashlib, json, re, subprocess
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261103/slskdn-pr409-w52-primary-20261103')
IN=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w55-primary-20261103/input')
OUT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w55-independent-blind-20261103')
HEAD='6a46b8f1dc87d899308fee141fa0db392e49e098'; TREE='a22e9a896aae12aa89a1502d9748b12816d491ed'; BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
def run(*args,text=True): return subprocess.check_output(list(args),cwd=REPO,text=text)
def sha(x): return hashlib.sha256(x.encode('utf-8') if isinstance(x,str) else x).hexdigest()
def blob(x): return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def canonical(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def verify_manifest(d,name):
 rows=[]
 for line in (d/name).read_text().splitlines():
  if not line.strip(): continue
  h,r=line.split(None,1); r=r.strip().lstrip('*'); rows.append({'path':r,'matches':sha((d/r).read_bytes())==h})
 assert rows and all(x['matches'] for x in rows),(d/name,rows)
 return rows
assert REPO.exists() and IN.exists()
head=run('git','rev-parse','HEAD').strip(); tree=run('git','rev-parse','HEAD^{tree}').strip(); status=run('git','status','--porcelain=v1').strip()
assert (head,tree,status)==(HEAD,TREE,''),(head,tree,status)
pr=json.loads(run('gh','pr','view','409','--repo','snapetech-org/slskdN','--json','body,headRefName,headRefOid,isDraft,state,url'))
body_sha=sha(pr['body']); assert pr['state']=='OPEN' and pr['isDraft'] is True and pr['headRefName']==BRANCH and pr['headRefOid']==HEAD
remote=run('git','ls-remote','origin',f'refs/heads/{BRANCH}').split(); assert len(remote)==2 and remote[0]==HEAD
input_manifest=verify_manifest(IN,'PACKET-SHA256SUMS.txt'); att=json.loads((IN/'head-tree-attestation.json').read_text()); selection=json.loads((IN/'selection-and-boundary.json').read_text())
assert (att['head'],att['tree'],att['branch'],att['bodySha256'],att['remoteBranchHead'])==(HEAD,TREE,BRANCH,body_sha,HEAD)
assert selection['inputContainsCandidates'] is False
cells=jl(IN/'source-current-cells.jsonl'); caller_rows=jl(IN/'caller-contexts.jsonl'); cat_rows=jl(IN/'catalog-structure.jsonl'); protected=jl(IN/'protected-literals.jsonl')
assert len(cells)==300 and len(caller_rows)==25 and len(cat_rows)==12 and len(protected)==25
assert all(not any(k in x for k in ('candidateTarget','verdict','disposition','candidate','adjudication')) for x in cells)
assert [(x['continuationRank'],x['locale']) for x in cells]==[(r,l) for r in range(276,301) for l in LOCALES]
caller_by_id={x['sourceId']:x for x in caller_rows}
ordered_hashes=set(); catalog_data={}
for cat in cat_rows:
 data=(REPO/cat['catalogPath']).read_bytes(); doc=json.loads(data); keys=list(doc); gitblob=run('git','rev-parse',f'{HEAD}:{cat["catalogPath"]}').strip()
 assert sha(data)==cat['sha256'] and blob(data)==cat['gitBlob']==gitblob
 assert len(keys)==cat['entryCount']==6176 and cat['orderedKeySha256']==sha('\n'.join(keys)+'\n')
 ordered_hashes.add(cat['orderedKeySha256']); catalog_data[cat['locale']]=doc
assert len(ordered_hashes)==1 and next(iter(ordered_hashes))==selection['orderedCatalogKeySha256']
caller_reference_count=0
for cell in cells:
 assert sha(cell['source'])==cell['sourceSha256'] and 'src_'+sha(cell['source'])[:16]==cell['sourceId']
 assert cell['source'] in catalog_data[cell['locale']] and catalog_data[cell['locale']][cell['source']]==cell['currentTarget']
 assert sha(cell['currentTarget'])==cell['currentTargetSha256']
 cat=next(x for x in cat_rows if x['locale']==cell['locale']); assert cell['catalogPath']==cat['catalogPath'] and cell['catalogFileSha256']==cat['sha256'] and cell['catalogGitBlob']==cat['gitBlob']
 source_callers=caller_by_id[cell['sourceId']]
 assert sha(canonical(source_callers['callers']))==cell['callerContextSha256']
 compact=[{'path':x['path'],'line':x['line'],'lineSha256':x['lineSha256'],'fileSha256':x['fileSha256'],'gitBlob':x['gitBlob']} for x in source_callers['callers']]
 assert cell['callerRefs']==compact
caller_rows_checked=[]
for c in caller_rows:
 assert sha(c['source'])==c['sourceSha256'] and c['sourceId']=='src_'+sha(c['source'])[:16]
 assert len(c['callers'])==c['productionCallerCount']
 for ref in c['callers']:
  data=(REPO/ref['path']).read_bytes(); lines=data.decode('utf-8').splitlines(); rel=ref['path']
  actual_blob=run('git','rev-parse',f'{HEAD}:{rel}').strip()
  assert sha(data)==ref['fileSha256'] and blob(data)==ref['gitBlob']==actual_blob
  assert lines[ref['line']-1]==ref['lineText'] and sha(lines[ref['line']-1])==ref['lineSha256']
  context=[{'line':i+1,'text':lines[i]} for i in range(max(0,ref['line']-3),min(len(lines),ref['line']+3))]
  assert context==ref['context'] and sha(canonical(context))==ref['contextSha256']
  caller_reference_count+=1
 caller_rows_checked.append({'sourceId':c['sourceId'],'continuationRank':c['continuationRank'],'callerCount':c['productionCallerCount']})
assert caller_reference_count==40
report={'verification':'passed','repository':'snapetech-org/slskdN','pullRequest':409,'url':pr['url'],'state':'OPEN','isDraft':True,'branch':BRANCH,'head':HEAD,'tree':TREE,'remoteBranchHead':remote[0],'prBodySha256':body_sha,'worktreeClean':True,'inputDir':str(IN),'inputManifestEntriesVerified':len(input_manifest),'inputManifestSha256':sha((IN/'PACKET-SHA256SUMS.txt').read_bytes()),'sourceCount':25,'localeCount':12,'cellCount':300,'catalogCount':len(cat_rows),'orderedCatalogKeySha256':next(iter(ordered_hashes)),'callerSourceCount':len(caller_rows),'callerReferenceCount':caller_reference_count,'callerlessSourceCount':sum(c['productionCallerCount']==0 for c in caller_rows),'inputContainsCandidates':False,'callerReferencesChecked':caller_rows_checked}
(OUT/'pin-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
