#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import hashlib,json,re,subprocess
T=Path('/home/keith/Documents/code/task-scratch/slskdn-pr409-w64-blind-20261103')
IN=Path('/home/keith/Documents/code/task-scratch/slskdn-pr409-w64-ranks478-502-primary-20261103/input')
OUT=T/'review'
HEAD='3cc9db334cfb1693dd6bd93bb83cfeba65930adb'; TREE='9d40e239e7e717a81bd176d143d1ce067fe026a1'; BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
INPUT_MANIFEST_SHA='4f428c69b3abec8db8ad9d7796f5c9a6e9e6da9234361cc644721b932de05456'
INPUT_SUMS_SHA='2064eb36dcd2bc27344f73c57b62e8e3078d087da115fe04d52348a30855e5c8'
PH=re.compile(r'\{[^{}\r\n]+\}'); MK=re.compile(r'</?[A-Za-z][^<>]*?/?>'); NUM=re.compile(r'(?<!\w)[+-]?\d+(?:[.,]\d+)?%?(?!\w)')
def sha(b): return hashlib.sha256(b).hexdigest()
def st(s): return sha(s.encode('utf-8'))
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def verify_sums(d):
 for line in (d/'PACKET-SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
  if line.strip():
   h,n=line.split(None,1); n=n.strip().lstrip('*'); assert sha((d/n).read_bytes())==h,(d/n,'input checksum')
def caller_refs(c):
 return [{'path':x['path'],'line':x['line'],'lineText':x['lineText'],'lineSha256':x['lineSha256'],'contextSha256':x['contextSha256'],'fileSha256':x['fileSha256'],'gitBlob':x['gitBlob']} for x in c['callers']]
def live():
 pr=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','number,state,isDraft,headRefName,headRefOid,baseRefName'],text=True))
 refs=subprocess.check_output(['git','ls-remote','https://github.com/snapetech-org/slskdN.git',f'refs/heads/{BRANCH}','refs/pull/409/head'],text=True)
 rm={x.split()[1]:x.split()[0] for x in refs.splitlines() if x.strip()}
 tree=subprocess.check_output(['gh','api',f'repos/snapetech-org/slskdN/commits/{HEAD}','--jq','.commit.tree.sha'],text=True).strip()
 assert (pr['number'],pr['state'],pr['isDraft'],pr['headRefName'],pr['headRefOid'],pr['baseRefName'])==(409,'OPEN',True,BRANCH,HEAD,'main')
 assert rm=={f'refs/heads/{BRANCH}':HEAD,'refs/pull/409/head':HEAD} and tree==TREE
verify_sums(IN)
assert sha((IN/'manifest.json').read_bytes())==INPUT_MANIFEST_SHA
assert sha((IN/'PACKET-SHA256SUMS.txt').read_bytes())==INPUT_SUMS_SHA
input_check=subprocess.check_output(['python3',str(IN/'verify_input.py')],text=True)
manifest=j(IN/'manifest.json'); assert (manifest['head'],manifest['tree'],manifest['cellCount'])==(HEAD,TREE,300)
boundary=j(IN/'selection-and-boundary.json'); assert boundary['selection']['continuationRankStart']==478 and boundary['selection']['continuationRankEnd']==502
inputs=jl(IN/'source-current-cells.jsonl'); callers={x['continuationRank']:x for x in jl(IN/'caller-contexts.jsonl')}
assert len(inputs)==300 and len(callers)==25
for rank in range(478,503):
 assert len({x['callerContextSha256'] for x in inputs if x['continuationRank']==rank})==1
 assert re.fullmatch(r'[0-9a-f]{64}',next(x['callerContextSha256'] for x in inputs if x['continuationRank']==rank))
ledger=jl(OUT/'blind-ledger.jsonl'); selected=jl(OUT/'selected-direct-locale-cells.jsonl')
summary=j(OUT/'summary.json'); provenance=j(OUT/'provenance.json'); attest=j(OUT/'live-attestation.json')
assert len(ledger)==300 and len(selected)==summary['proposedChanges']
assert (summary['head'],summary['tree'],provenance['head'],provenance['tree'])==(HEAD,TREE,HEAD,TREE)
assert summary['candidateFreeManifestJsonSha256']==provenance['candidateFreeManifestJsonSha256']==INPUT_MANIFEST_SHA
assert summary['candidateFreeChecksumListSha256']==provenance['candidateFreeChecksumListSha256']==INPUT_SUMS_SHA
assert provenance['reviewType']=='independent blind semantic review using candidate-free input only'
assert provenance['primaryReviewRead'] is False and provenance['otherAuditRead'] is False
assert provenance['all300CellsReviewed'] is True and summary['independentBlindReview'] is True
assert summary['nativeSpeakerApproval'] is False and summary['browserReview'] is False
assert attest['state']=='OPEN' and attest['draft'] is True and attest['branch']==BRANCH and attest['baseBranch']=='main'
assert attest['branchRef']==attest['pullRef']==HEAD and attest['tree']==TREE
expected={(x['continuationRank'],x['locale']):x for x in inputs}; assert len(expected)==300
bykey={(x['continuationRank'],x['locale']):x for x in ledger}; assert set(bykey)==set(expected)
byrank=callers
sel={(x['continuationRank'],x['locale']):x for x in selected}; assert len(sel)==len(selected)
counts=Counter(x['disposition'] for x in ledger); assert dict(counts)==summary['dispositions']
assert counts['accept-current']+counts['correction']+counts['refinement']+counts['hold']==300
assert counts['hold']==12 and counts['correction']+counts['refinement']==len(selected)
assert summary['proposedChanges']==len(selected)
assert summary['priorHeldCellsReattestedAndPreserved']==provenance['priorHeldCellsReattestedAndPreserved']==86
prior=j(IN/'prior-held-cell-reattestation-summary.json'); assert prior['priorHeldCellsReattested']==86 and prior['allTargetHashesMatchPrior'] is True
assert summary['currentCallerlessHoldCells']==12 and summary['currentCallerlessHoldRanks']==[486]
base_protected=sum(not x['protectedLiteralEvidence']['matches'] for x in inputs)
assert base_protected==summary['baselineProtectedLiteralMismatches']==23
for key,row in bykey.items():
 inp=expected[key]; c=byrank[key[0]]
 assert row['sourceId']==inp['sourceId'] and row['source']==inp['source'] and row['sourceSha256']==inp['sourceSha256']
 assert row['currentTarget']==inp['currentTarget'] and row['currentTargetSha256']==inp['currentTargetSha256']
 assert row['locale']==inp['locale'] and row['catalogPath']==inp['catalogPath'] and row['catalogFileSha256']==inp['catalogFileSha256'] and row['catalogGitBlob']==inp['catalogGitBlob']
 assert row['callerContextSha256']==inp['callerContextSha256'] and row['productionCallerCount']==c['productionCallerCount']
 assert row['productionCallerCount']==len(row['callerReferences'])
 assert row['callerReferences']==caller_refs(c)
 assert row['rationale'].strip() and row['confidence'] in {'high','moderate','low'}
 t=row['blindTarget']; assert row['blindTargetSha256']==st(t)
 assert row['placeholderChecks']['sourceTokens']==PH.findall(inp['source'])==PH.findall(t)
 assert row['markupChecks']['sourceTags']==MK.findall(inp['source'])==MK.findall(t)
 assert row['numericChecks']['sourceTokens']==NUM.findall(inp['source'])==NUM.findall(t)
 assert row['protectedLiteralChecks']['sourceLiterals']==inp['sourceProtectedLiterals']
 assert all(x in t for x in inp['sourceProtectedLiterals'])
 assert row['protectedLiteralChecks']['blindMatchesSource'] is True
 if c['productionCallerCount']==0:
  assert key[0]==486 and row['disposition']=='hold' and t==inp['currentTarget'] and key not in sel
 elif row['disposition']=='accept-current':
  assert t==inp['currentTarget'] and key not in sel
 else:
  assert key in sel and sel[key]['blindTarget']==t and sel[key]['rationale']==row['rationale']
assert {k for k,v in bykey.items() if v['disposition']!='accept-current' and v['disposition']!='hold'}==set(sel)
assert {k for k,v in bykey.items() if v['disposition']=='hold'}=={(486,loc) for loc in {x['locale'] for x in inputs}}
assert summary['blindPlaceholderMismatches']==summary['blindMarkupMismatches']==summary['blindNumericMismatches']==summary['blindProtectedLiteralMismatches']==0
# The review packet's checksum list covers every sibling artifact except itself.
listed=set()
for line in (OUT/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
 if line.strip():
  h,n=line.split(None,1); n=n.strip().lstrip('*'); assert sha((OUT/n).read_bytes())==h,n; listed.add(n)
assert listed=={p.name for p in OUT.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt'}
print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'cells':300,'dispositions':dict(counts),'proposedChanges':len(selected),'callerlessHolds':12,'priorHeldCellsReattested':86,'baselineProtectedLiteralMismatches':23,'candidateFreeManifestJsonSha256':INPUT_MANIFEST_SHA,'candidateFreeChecksumListSha256':INPUT_SUMS_SHA,'blindChecksumListSha256':sha((OUT/'SHA256SUMS.txt').read_bytes()),'blindChecksumEntries':len(listed),'liveInputVerifier':'PASS'},ensure_ascii=False,indent=2))
