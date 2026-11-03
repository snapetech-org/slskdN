#!/usr/bin/env python3
"""Portable integrity and completeness verifier for this blind translation review."""
import hashlib,json,sys
from collections import Counter
from pathlib import Path
root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent
def fail(s): raise SystemExit('FAIL: '+s)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]
sp=root/'SHA256SUMS'
if not sp.is_file(): fail('SHA256SUMS missing')
listed={}
for line in sp.read_text(encoding='utf-8').splitlines():
 if not line.strip(): continue
 a=line.split('  ',1)
 if len(a)!=2: fail('malformed SHA256SUMS line')
 listed[a[1]]=a[0]
for n,h in listed.items():
 p=root/n
 if not p.is_file(): fail(n+' missing')
 if digest(p)!=h: fail(n+' checksum mismatch')
m=j(root/'manifest.json')
for x in m['files']:
 p=root/x['path']
 if not p.is_file(): fail(x['path']+' missing')
 if p.stat().st_size!=x['bytes'] or digest(p)!=x['sha256']: fail(x['path']+' manifest mismatch')
 if listed.get(x['path'])!=x['sha256']: fail(x['path']+' manifest/SHA256SUMS mismatch')
L=jl(root/'review-ledger.jsonl'); H=jl(root/'held-cell-reattestation.jsonl'); S=j(root/'review-summary.json')
if len(L)!=300: fail('expected 300 review rows')
if len({(x['sourceId'],x['locale']) for x in L})!=300: fail('duplicate/missing source-locale key')
if {x['continuationRank'] for x in L}!=set(range(578,603)): fail('rank coverage mismatch')
v=Counter(x['verdict'] for x in L)
if any(v.get(k,0)!=S['verdictCounts'].get(k,0) for k in ('accept','revise','hold')): fail('verdict count mismatch')
if v['revise']!=27 or v['accept']!=273 or v['hold']!=0: fail('review totals mismatch')
if len(H)!=128: fail('expected 128 held-cell reattestations')
if not all(x['targetHashMatchesPrior'] and x['priorTargetSha256']==x['recomputedCurrentTargetSha256'] for x in H): fail('carried hold hash mismatch')
if any(not x['tokenAudit']['placeholderEvidence']['matches'] for x in L): fail('placeholder mismatch')
if any(not x['tokenAudit']['markupEvidence']['matches'] for x in L): fail('markup mismatch')
if any(x['tokenAudit']['sourceNumericTokens']!=x['tokenAudit']['currentNumericTokens'] for x in L): fail('numeric mismatch')
print(f"OK: {len(L)} locale cells, {v['revise']} revisions, {len(H)} carried holds reattested, checksums valid")
