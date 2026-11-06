#!/usr/bin/env python3
import collections,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
EV=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
load=lambda p:json.loads(p.read_text(encoding="utf-8"))
lines=lambda p:[json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
manifest=load(EV/"application-manifest.json")
for line in (EV/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
 digest,name=line.split("  ",1);assert sha((EV/name).read_bytes())==digest.strip(),name
for file in manifest["files"]:
 raw=(EV/file["path"]).read_bytes();assert len(raw)==file["bytes"] and sha(raw)==file["sha256"],file["path"]
ledger=lines(EV/"cross-review/cross-review-ledger.jsonl")
readback=lines(EV/"application-readback.jsonl")
assert len(ledger)==len(readback)==300
assert sha((EV/"cross-review/manifest.json").read_bytes())==manifest["crossAuditManifestSha256"]
for line in (EV/"cross-review/SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
 digest,name=line.split("  ",1);assert sha((EV/"cross-review"/name).read_bytes())==digest.strip()
bykey={(r['sourceId'],r['locale']):r for r in ledger};assert len(bykey)==300
counts=collections.Counter();seen=set()
ph=lambda s:collections.Counter(re.findall(r'\{[^{}]+\}',s))
tags=lambda s:collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',s))
num=lambda s:collections.Counter(re.findall(r'(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])',re.sub(r'\{[^{}]+\}','',s)))
for a in readback:
 k=(a['sourceId'],a['locale']);assert k not in seen;seen.add(k);r=bykey[k]
 assert a['crossDisposition']==r['crossDisposition'] and a['sourceSha256']==r['sourceSha256']
 data=load(ROOT/a['catalogPath']);assert len(data)==6176
 matches=[key for key in data if sha(key.encode())==a['sourceSha256']];assert len(matches)==1
 target=data[matches[0]];targetsha=sha(target.encode())
 assert targetsha==a['readbackTargetSha256']==a['expectedFinalTargetSha256'] and a['matchesExpected']
 if r['crossDisposition']=='hold-text-free':
  assert a['textFree'] and not any(x in a for x in ('sourceText','currentTarget','finalTarget','proposedTarget'))
  counts['hold-text-free']+=1;continue
 assert not a['textFree'] and target==r['finalTarget'] and sha(r['sourceText'].encode())==r['sourceSha256']
 assert ph(r['sourceText'])==ph(target) and tags(r['sourceText'])==tags(target) and num(r['sourceText'])==num(target)
 assert all(x in target for x in r['sourceProtectedLiterals']) and all(x in target for x in r['manualProtectedLiterals'])
 for op in ('>=','<=','!=','=='):assert r['sourceText'].count(op)==target.count(op)
 if r['continuationRank']==721:assert r['sourceText']=='alice' and target=='alice'
 counts[r['crossDisposition']]+=1
for loc,info in manifest['catalogFiles'].items():
 raw=(ROOT/info['path']).read_bytes();assert sha(raw)==info['sha256After']
assert counts=={'accept-current':216,'correct':72,'hold-text-free':12} and len(seen)==300
print(json.dumps({'result':'PASS','reviewBaseHead':manifest['reviewBaseHead'],'catalogCommit':manifest['catalogCommit'],'cells':300,'corrected':72,'acceptedUnchanged':216,'heldUnchangedTextFree':12,'catalogs':12,'keysPerCatalog':6176},sort_keys=True))
