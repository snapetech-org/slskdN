#!/usr/bin/env python3
import hashlib,json,subprocess
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[3]
BASE='973a65312a475de4d8aa39aee837249553fd884e'
TREE='2a7b200dd1fe96f894bfdb663f656d6ffd48f487'
BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
EVIDENCE_PREFIX='docs/pr-evidence/pr409-localization-2026-11-03/window-578-602/'
INPUT=ROOT/'candidate-free-input'; PRIMARY=ROOT/'primary-review'; BLIND=ROOT/'blind-review'; CROSS=ROOT/'cross-audit'
def sha(b):return hashlib.sha256(b).hexdigest()
def sht(s):return sha(s.encode('utf-8'))
def j(p):return json.loads(p.read_text(encoding='utf-8'))
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def dumpj(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def dumpjl(p,x):p.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in x),encoding='utf-8')
def git(*a):return subprocess.check_output(['git','-C',str(REPO),*a],text=True).strip()
assert git('rev-parse','HEAD')==BASE and git('rev-parse',BASE+'^{tree}')==TREE
assert git('diff','--name-only')=='' and git('diff','--cached','--name-only')==''
for folder,name in [(INPUT,'PACKET-SHA256SUMS.txt'),(PRIMARY,'SHA256SUMS.txt'),(BLIND,'SHA256SUMS'),(CROSS,'SHA256SUMS')]:
 subprocess.run(['sha256sum','-c',name],cwd=folder,check=True,stdout=subprocess.DEVNULL)
# The sealed candidate-free verifier, primary verifier, and blind verifier were rerun while this worktree's new evidence directory was temporarily staged outside the repository; see the recorded pre-application logs.
subprocess.run(['python3','verify_cross_audit.py','/home/keith/Documents/code/task-scratch'],cwd=CROSS,check=True,stdout=subprocess.DEVNULL)
im=j(INPUT/'manifest.json'); pm=j(PRIMARY/'manifest.json'); bm=j(BLIND/'manifest.json'); xm=j(CROSS/'manifest.json')
assert all((x['head'],x['tree'])==(BASE,TREE) for x in (im,pm,bm,xm))
assert pm['blindPacketAccessed'] is False and bm['primaryPacketOpened'] is False and bm['priorProposalsUsed'] is False
assert pm['priorHeldCellsReattested']==128 and bm['priorHeldCellsReattested']==128
catalog=jl(INPUT/'source-current-cells.jsonl'); cross=jl(CROSS/'cross-audit-ledger.jsonl'); held=jl(CROSS/'hold-cross-audit.jsonl')
assert len(catalog)==len(cross)==300 and len(held)==128
bykey={(r['continuationRank'],r['locale']):r for r in catalog}; assert len(bykey)==300
updates=[]; noops=[]
for r in cross:
 k=(r['continuationRank'],r['locale']); c=bykey[k]
 for f in ('sourceId','source','sourceSha256','currentTarget','currentTargetSha256','catalogPath','catalogFileSha256','catalogGitBlob','callerContextSha256','callerRefs'):
  assert r[f]==c[f],(k,f)
 assert r['selectedTargetSha256']==sht(r['selectedTarget'])
 assert r['selectedDisposition'] in ('accept-current','correction')
 assert r['selectedDisposition']!='correction' or r['selectedTarget']!=r['currentTarget']
 assert r['selectedDisposition']!='accept-current' or r['selectedTarget']==r['currentTarget']
 row={'schema':'slskdn-w68-application-cell/v1','repository':'snapetech-org/slskdN','pullRequest':409,'window':'W68','baseHead':BASE,'baseTree':TREE,'continuationRank':r['continuationRank'],'remainingQueueRank':r['remainingQueueRank'],'locale':r['locale'],'sourceId':r['sourceId'],'source':r['source'],'catalogPath':r['catalogPath'],'catalogKey':r['source'],'currentTarget':r['currentTarget'],'currentTargetSha256':r['currentTargetSha256'],'selectedTarget':r['selectedTarget'],'selectedTargetSha256':r['selectedTargetSha256'],'disposition':r['selectedDisposition'],'resolutionNote':r['resolutionNote'],'catalogFileSha256Before':r['catalogFileSha256'],'catalogGitBlobBefore':r['catalogGitBlob'],'callerContextSha256':r['callerContextSha256'],'callerRefs':r['callerRefs']}
 (updates if r['selectedDisposition']=='correction' else noops).append(row)
assert len(updates)==29 and len(noops)==271 and not any(r['selectedDisposition']=='hold' for r in cross)
assert Counter(r['disposition'] for r in updates)==Counter({'correction':29})
updates_by_path={}
for r in updates:
 d=updates_by_path.setdefault(r['catalogPath'],{})
 assert r['catalogKey'] not in d; d[r['catalogKey']]=r
structure=jl(INPUT/'catalog-structure.jsonl'); assert len(structure)==12
structure_by={r['catalogPath']:r for r in structure}; assert set(updates_by_path)==set(structure_by)
for p,row in structure_by.items():
 data=(REPO/p).read_bytes(); assert sha(data)==row['sha256']
 assert git('rev-parse',BASE+':'+p)==row['gitBlob']
 obj=json.loads(data); assert len(obj)==row['entryCount']==6176
 assert sha(('\n'.join(obj.keys())+'\n').encode('utf-8'))==row['orderedKeySha256']
 for r in updates_by_path[p].values():
  assert obj[r['catalogKey']]==r['currentTarget'] and sht(obj[r['catalogKey']])==r['currentTargetSha256']

dumpjl(ROOT/'application-plan.jsonl',updates); dumpjl(ROOT/'no-op-ledger.jsonl',noops)
dumpjl(ROOT/'hold-ledger.jsonl',[{'schema':'slskdn-w68-application-hold/v1','action':'retain-unchanged',**r} for r in held])
pins={'candidateFreeManifestSha256':sha((INPUT/'manifest.json').read_bytes()),'candidateFreeChecksumSha256':sha((INPUT/'PACKET-SHA256SUMS.txt').read_bytes()),'primaryManifestSha256':sha((PRIMARY/'manifest.json').read_bytes()),'primaryChecksumSha256':sha((PRIMARY/'SHA256SUMS.txt').read_bytes()),'blindManifestSha256':sha((BLIND/'manifest.json').read_bytes()),'blindChecksumSha256':sha((BLIND/'SHA256SUMS').read_bytes()),'crossAuditManifestSha256':sha((CROSS/'manifest.json').read_bytes()),'crossAuditChecksumSha256':sha((CROSS/'SHA256SUMS').read_bytes()),'crossAuditLedgerSha256':sha((CROSS/'cross-audit-ledger.jsonl').read_bytes()),'crossAuditHoldLedgerSha256':sha((CROSS/'hold-cross-audit.jsonl').read_bytes()),'crossAuditScratchPathAtCreation':'/home/keith/Documents/code/task-scratch/slskdn-pr409-w68-ranks578-602-cross-audit-20261103'}
dumpj(ROOT/'review-packet-pins.json',pins)
byloc=Counter(r['locale'] for r in updates)
summary={'schema':'slskdn-w68-application-plan-summary/v1','baseHead':BASE,'baseTree':TREE,'reviewedCells':300,'updateCount':29,'dispositionCounts':{'correction':29,'refinement':0},'noOpCount':271,'priorHoldsRetainedUnchanged':128,'newHolds':0,'updatesByLocale':{x:byloc[x] for x in sorted(byloc)},'catalogFilesExpectedToChange':sorted(updates_by_path),'catalogKeyCountPerFile':{x:structure_by[x]['entryCount'] for x in sorted(structure_by)},'orderedKeySha256':structure[0]['orderedKeySha256'],'reviewPacketPins':pins,'applicationPerformed':False}
dumpj(ROOT/'application-plan-summary.json',summary)
print(json.dumps(summary,ensure_ascii=False,indent=2))
