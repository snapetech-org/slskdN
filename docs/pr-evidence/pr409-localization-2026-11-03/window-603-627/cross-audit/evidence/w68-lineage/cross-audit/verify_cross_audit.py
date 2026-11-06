#!/usr/bin/env python3
"""Verify cross-audit files and, when available, their pinned evidence packets."""
import hashlib,json,re,sys
from collections import Counter
from pathlib import Path
root=Path(__file__).resolve().parent
evidence=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root.parent
def fail(s): raise SystemExit('FAIL: '+s)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]
sums=root/'SHA256SUMS'
if not sums.is_file(): fail('SHA256SUMS missing')
listed={}
for line in sums.read_text(encoding='utf-8').splitlines():
 if not line.strip(): continue
 q=line.split('  ',1)
 if len(q)!=2: fail('malformed SHA256SUMS')
 listed[q[1]]=q[0]
for name,want in listed.items():
 p=root/name
 if not p.is_file() or digest(p)!=want: fail('output checksum mismatch: '+name)
m=j(root/'manifest.json')
for f in m['files']:
 p=root/f['path']
 if not p.is_file() or p.stat().st_size!=f['bytes'] or digest(p)!=f['sha256']: fail('manifest mismatch: '+f['path'])
 if listed.get(f['path'])!=f['sha256']: fail('manifest/SHA256SUMS mismatch: '+f['path'])
L=jl(root/'cross-audit-ledger.jsonl'); H=jl(root/'hold-cross-audit.jsonl'); S=j(root/'cross-audit-summary.json')
if len(L)!=300 or len({(x['sourceId'],x['locale']) for x in L})!=300: fail('300-cell coverage mismatch')
if {x['continuationRank'] for x in L}!=set(range(578,603)): fail('rank range mismatch')
v=Counter(x['selectedDisposition'] for x in L)
if v!=Counter({'accept-current':271,'correction':29}): fail('final disposition counts mismatch')
if len(H)!=128 or not all(x['hashesMatch'] for x in H): fail('128-hold hash mismatch')
if any(x['selectedTargetSha256']!=hashlib.sha256(x['selectedTarget'].encode()).hexdigest() for x in L): fail('selected target SHA mismatch')
if any(not all(x['selectedTokenAudit'][z] for z in ('placeholdersPreserved','markupPreserved','numericTokensPreserved','protectedLiteralsPreserved')) for x in L): fail('selected token mismatch')
if any(x['selectedDisposition']=='correction' and x['selectedTarget']!=x['primary']['proposedTarget'] for x in L): fail('selected correction target mismatch')
if sum(x['comparison']['relation']=='primary-only-correction' for x in L)!=2: fail('primary-only difference count mismatch')
if sum(x['comparison']['relation']=='both-correct-target-differs' for x in L)!=16: fail('proposal-text difference count mismatch')
if sum(x['comparison']['relation']=='blind-only-correction' for x in L)!=0: fail('unexpected blind-only correction')
if len(S['reconciliation']['differences'])!=18: fail('difference adjudication count mismatch')
need=[evidence/'slskdn-pr409-w68-ranks578-602-candidate-free-20261103/input',
 evidence/'slskdn-pr409-w68-ranks578-602-blind-review-20261103',
 evidence/'slskdn-pr409-w68-ranks578-602-primary-20261103/primary-review']
if all(p.is_dir() for p in need):
 inp,blind,primary=need
 def check_manifest(folder):
  mm=j(folder/'manifest.json')
  for f in mm.get('files',[]):
   p=folder/f['path']
   if not p.is_file() or p.stat().st_size!=f['bytes'] or digest(p)!=f['sha256']: fail('evidence manifest mismatch: '+str(p))
  return mm
 check_manifest(inp); check_manifest(blind); check_manifest(primary)
 if digest(inp/'manifest.json')!=S['inputPins']['candidateFreeManifestSha256']: fail('candidate-free manifest pin mismatch')
 if digest(blind/'manifest.json')!=S['inputPins']['blindManifestSha256']: fail('blind manifest pin mismatch')
 if digest(primary/'manifest.json')!=S['inputPins']['primaryManifestSha256']: fail('primary manifest pin mismatch')
 I={(x['sourceId'],x['locale']):x for x in jl(inp/'source-current-cells.jsonl')}
 B={(x['sourceId'],x['locale']):x for x in jl(blind/'review-ledger.jsonl')}
 P={(x['sourceId'],x['locale']):x for x in jl(primary/'primary-ledger.jsonl')}
 X={(x['sourceId'],x['locale']):x for x in L}
 if not (len(I)==len(B)==len(P)==len(X)==300 and set(I)==set(B)==set(P)==set(X)): fail('evidence coverage/key mismatch')
 for k,x in X.items():
  i,b,p=I[k],B[k],P[k]
  if (x['source'],x['currentTarget'],x['currentTargetSha256'])!=(i['source'],i['currentTarget'],i['currentTargetSha256']): fail('source/current mismatch')
  if (x['primary']['disposition'],x['primary']['proposedTarget'])!=(p['disposition'],p.get('proposedTarget')): fail('primary decision mismatch')
  if (x['blind']['verdict'],x['blind']['suggestedTarget'])!=(b['verdict'],b.get('suggestedTarget')): fail('blind decision mismatch')
 IH={(x['sourceId'],x['locale']):x for x in jl(inp/'prior-held-cell-reattestation.jsonl')}
 BH={(x['sourceId'],x['locale']):x for x in jl(blind/'held-cell-reattestation.jsonl')}
 HX={(x['sourceId'],x['locale']):x for x in H}
 if not (len(IH)==len(BH)==len(HX)==128 and set(IH)==set(BH)==set(HX)): fail('carried-hold coverage mismatch')
 for k,x in HX.items():
  if IH[k]['priorTargetSha256']!=x['candidateFreeCurrentTargetSha256'] or BH[k]['recomputedCurrentTargetSha256']!=x['blindRecomputedCurrentTargetSha256']: fail('carried-hold hash evidence mismatch')
 print('OK: output checksums; 300 aligned candidate-free/blind/primary rows; 128 hold hashes; pinned evidence')
else:
 print('OK: output checksums, 300-cell internal coverage, selected tokens, and 128 hold hashes; evidence packs unavailable so external cross-check skipped')
