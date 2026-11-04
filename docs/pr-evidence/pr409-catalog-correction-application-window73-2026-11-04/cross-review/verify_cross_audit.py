#!/usr/bin/env python3
import collections,hashlib,json,re
from pathlib import Path
O=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
load=lambda n:json.loads((O/n).read_text(encoding="utf-8"))
rows=[json.loads(x) for x in (O/"cross-review-ledger.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
props=[json.loads(x) for x in (O/"corrections.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
holds=[json.loads(x) for x in (O/"holds-hash-only.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
manifest=load("manifest.json"); summary=load("summary.json")
for line in (O/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
 digest,name=line.split("  ",1); assert sha((O/name).read_bytes())==digest.strip(),name
for file in manifest["files"]:
 raw=(O/file["path"]).read_bytes(); assert len(raw)==file["bytes"] and sha(raw)==file["sha256"]
assert len(rows)==300 and len({(r['sourceId'],r['locale']) for r in rows})==300
assert collections.Counter(r['crossDisposition'] for r in rows)=={'accept-current':216,'correct':72,'hold-text-free':12}
assert len(props)==72 and len(holds)==12
for r in rows:
 if r['crossDisposition']=='hold-text-free':
  assert not any(k in r for k in ('sourceText','currentTarget','finalTarget','primaryProposal','blindProposal','crossRationale'))
 else:
  assert sha(r['sourceText'].encode())==r['sourceSha256']
  assert sha(r['currentTarget'].encode())==r['currentTargetSha256']
  assert sha(r['finalTarget'].encode())==r['finalTargetSha256']
  assert collections.Counter(re.findall(r'\{[^{}]+\}',r['sourceText']))==collections.Counter(re.findall(r'\{[^{}]+\}',r['finalTarget']))
  assert collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',r['sourceText']))==collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',r['finalTarget']))
  assert all(x in r['finalTarget'] for x in r['sourceProtectedLiterals'])
  assert all(x in r['finalTarget'] for x in r['manualProtectedLiterals'])
  if r['continuationRank']==721: assert r['sourceText']=='alice' and r['finalTarget']=='alice'
  nums=lambda s:collections.Counter(re.findall(r'(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])',re.sub(r'\{[^{}]+\}','',s)))
  assert nums(r['sourceText'])==nums(r['finalTarget'])
  for op in ('>=','<=','!=','=='): assert r['sourceText'].count(op)==r['finalTarget'].count(op)
for h in holds: assert not any(k in h for k in ('sourceText','currentTarget','finalTarget','primaryProposal','blindProposal','crossRationale'))
assert all(p['recommendedTarget']!=p['currentTarget'] for p in props)
assert manifest['head']==summary['livePullRequest']['headRefOid'] and manifest['tree']==summary['livePullRequest']['treeOid']
print(json.dumps({'result':'PASS','head':manifest['head'],'tree':manifest['tree'],'cells':len(rows),'acceptCurrent':216,'correct':72,'holdsTextFree':len(holds),'corrections':len(props),'outputChecksums':True},sort_keys=True))
