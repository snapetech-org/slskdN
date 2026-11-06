from __future__ import annotations
import hashlib,json,re,subprocess
from pathlib import Path
OUT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window45-primary-reconstructed-20261102')
WORK=Path('/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn')
HEAD='6a082138c09fa8af40aee3258beb98523ee821d9'; TREE='90142bfd8904d2a4428ea5f144848ba1c743bdd7'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
def sha(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def jl(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def git(*args):return subprocess.check_output(['git','-C',str(WORK),*args])
assert git('rev-parse','HEAD').decode().strip()==HEAD and git('rev-parse','HEAD^{tree}').decode().strip()==TREE and git('status','--porcelain').decode().strip()==''
# Ordered catalog parity, exact source and current value hashes.
keys=None; catalogs={}; catalograw={}; source_map={}
for loc in LOCALES:
 p=f'src/web/public/locales/{loc}.json'; raw=git('show',f'{HEAD}:{p}'); obj=json.loads(raw)
 assert len(obj)==6170 and len(set(obj))==6170
 if keys is None:keys=list(obj)
 else:assert list(obj)==keys
 catalogs[loc]=obj;catalograw[loc]=raw
 for k in obj:
  sid='src_'+sha(k)[:16]
  assert sid not in source_map or source_map[sid]==k
  source_map[sid]=k
assert len(source_map)==6170
inputs=jl(OUT/'input-cells.jsonl');selection=jl(OUT/'source-selection.jsonl');prior=jl(OUT/'prior-source-ids.jsonl');inventory=jl(OUT/'source-inventory.jsonl')
assert len(inputs)==300 and len(selection)==25 and len(prior)==1097 and len(inventory)==6170
assert len({x['sourceId'] for x in prior})==1097
for x in prior:
 assert x['sourceId']=='src_'+sha(x['source'])[:16] and x['sourceSha256']==sha(x['source']) and source_map[x['sourceId']]==x['source']
pending=sorted(set(source_map)-{x['sourceId'] for x in prior})
assert len(pending)==5073 and [x['sourceId'] for x in selection]==pending[:25] and [x['sourceOrdinal'] for x in selection]==[None]*25
for x in inputs:
 loc=x['locale'];src=x['source'];p=x['catalogPath'];raw=catalograw[loc]
 assert p==f'src/web/public/locales/{loc}.json'
 assert sha(raw)==x['catalogFileSha256'] and git('rev-parse',f'{HEAD}:{p}').decode().strip()==x['catalogBlobOid']
 assert sha(src)==x['sourceSha256'] and catalogs[loc][src]==x['currentTarget'] and sha(x['currentTarget'])==x['currentTargetSha256']
# Exact complete cell ledger and proposal/readback consistency.
decisions=jl(OUT/'review-decisions.jsonl');proposals=jl(OUT/'candidate-proposals.jsonl');struct=jl(OUT/'structural-validation.jsonl')
assert len(decisions)==300 and len({(x['selectionRank'],x['locale']) for x in decisions})==300
assert len(proposals)==35 and len(struct)==300
inputmap={(x['selectionRank'],x['locale']):x for x in inputs}; dmap={(x['selectionRank'],x['locale']):x for x in decisions}; pmap={(x['selectionRank'],x['locale']):x for x in proposals}
assert set(dmap)==set(inputmap)
for key,d in dmap.items():
 i=inputmap[key]
 assert d['exactHead']==HEAD and d['exactTree']==TREE and d['sourceOrdinal'] is None
 assert (d['sourceId'],d['sourceSha256'],d['sourceText'],d['currentTarget'],d['currentTargetSha256'])==(i['sourceId'],i['sourceSha256'],i['source'],i['currentTarget'],i['currentTargetSha256'])
 if d['disposition']=='accept-current': assert d['reviewedTarget']==i['currentTarget'] and d['reviewedTargetSha256']==i['currentTargetSha256']
 else:
  assert key in pmap and pmap[key]['proposedTarget']==d['reviewedTarget'] and pmap[key]['proposedTargetSha256']==d['reviewedTargetSha256'] and sha(d['reviewedTarget'])==d['reviewedTargetSha256']
 assert d['sourcePlaceholders']==d['currentTargetPlaceholders']==d['reviewedTargetPlaceholders']
 assert d['sourceMarkup']==d['currentTargetMarkup']==d['reviewedTargetMarkup']
 assert not d['reviewedProtectedLiteralMismatches']
assert sum(x['disposition']=='accept-current' for x in decisions)==265
assert sum(x['disposition']=='propose-correction' for x in decisions)==29
assert sum(x['disposition']=='propose-refinement' for x in decisions)==6
# Protected literal current mismatch is only Hindi ContentID; all reviewed proposals fix it.
cur_mismatch=[x for x in decisions if x['currentProtectedLiteralMismatches']]
assert [(x['selectionRank'],x['locale'],x['currentProtectedLiteralMismatches']) for x in cur_mismatch]==[(24,'hi',['ContentID'])]
# Every source has a production localization display path; verify all refs against the exact Git blob/line.
callers=jl(OUT/'caller-context.jsonl');assert len(callers)==25
for c in callers:
 assert c['localizedProductionDisplayReferenceCount']>0
 for r in c['callerRefs']:
  raw=git('show',f"{HEAD}:{r['path']}");lines=raw.decode('utf-8').splitlines()
  assert r['line']<=len(lines) and lines[r['line']-1]==r['lineText'] and sha(r['lineText'])==r['lineSha256'] and sha(raw)==r['fileSha256'] and git('rev-parse',f"{HEAD}:{r['path']}").decode().strip()==r['blobOid']
  if r['exactSourceLiteralMatch']: assert c['source'] in r['lineText']
assert len(jl(OUT/'source-runtime-gaps.jsonl'))==0
# Spanish formality lane exact pin.
f=WORK/'docs/pr-evidence/pr409-localization-2026-11-02/window36/primary/formal-cell-ids.jsonl'
assert sha(f.read_bytes())=='7bd9c90a1176403feb36daadfecb7822616a818d15e9980c99c0bf5dc9d6f856'
# W44 apply-readback exact current values, and prior manifests.
w44=WORK/'docs/pr-evidence/pr409-localization-2026-11-02/window44-reconstructed-ranks1-25'
for d in [w44,w44/'primary',w44/'crossreview']:
 outp=subprocess.run(['sha256sum','-c',str(d/'SHA256SUMS.txt')],cwd=d,text=True,capture_output=True);assert outp.returncode==0
assert len(jl(OUT/'prior-window-input-reattestation.jsonl'))==300 and all(x['currentValueMatchesPriorW44Readback'] for x in jl(OUT/'prior-window-input-reattestation.jsonl'))
# Start/end live PR snapshots preserve exact #409 pin; only the concurrent #190 head changed.
pre=json.loads((OUT/'live-seven-pr-heads-start.json').read_text());post=json.loads((OUT/'live-seven-pr-heads-final.json').read_text())
a={x['number']:x for x in pre['pullRequests']};b={x['number']:x for x in post['pullRequests']}
assert set(a)==set(b)=={418,190,155,70,204,409,243}
assert b[409]['headRefOid']==HEAD and b[409]['headTree']==TREE and b[409]['remoteBranchOid']==HEAD and b[409]['state']=='OPEN' and b[409]['isDraft']
changes=[n for n in a if (a[n]['headRefOid'],a[n]['headTree'])!=(b[n]['headRefOid'],b[n]['headTree'])]
assert changes==[190]
print(json.dumps({'verified':True,'sourceCatalogKeys':len(keys),'priorStableIDs':len(prior),'selectionRanks':len(selection),'cells':len(decisions),'proposals':len(proposals),'callers':len(callers),'callerGaps':0,'currentProtectedLiteralMismatchCells':1,'reviewedProtectedLiteralMismatchCells':0,'w44Readbacks':300,'allSevenPrChanges':[{'number':n,'start':a[n]['headRefOid'],'final':b[n]['headRefOid']} for n in changes]},ensure_ascii=False,indent=2))
