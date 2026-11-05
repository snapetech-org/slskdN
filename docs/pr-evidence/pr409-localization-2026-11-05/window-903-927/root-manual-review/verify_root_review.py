#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent; BASE=ROOT.parent; CROSS=BASE/"cross-review"/"output"
sha=lambda b:hashlib.sha256(b).hexdigest()
def readj(p):return json.loads(p.read_text(encoding="utf-8"))
def rows(p):return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
a=readj(ROOT/"review.json"); cm=readj(CROSS/"cross-review-manifest.json"); summ=readj(CROSS/"proposal-reconciliation-summary.json"); cr=rows(CROSS/"cross-review-ledger.jsonl"); selected=rows(ROOT/"selected-dispositions.jsonl")
assert len(cr)==300 and len(selected)==64
assert a["head"]==cm["head"] and a["tree"]==cm["tree"] and a["crossReviewLedgerSha256"]==cm["crossReviewLedgerSha256"]
assert a["crossReviewManifestSha256"]==sha((CROSS/"cross-review-manifest.json").read_bytes())
assert a["candidateFreeInputTreeSha256"]==summ["candidateFreeInputTreeSha256"]
assert (a["selectedChangeCount"],a["keepCount"],a["holdCount"])==(64,224,12)
by={(r["continuationRank"],r["locale"]):r for r in cr}; seen=set()
for x in selected:
 k=(x["continuationRank"],x["locale"]); assert k not in seen; seen.add(k); r=by[k]
 assert r["finalDecision"] in {"correct","refinement"} and r["finalTarget"]==x["target"] and r["finalTargetSha256"]==x["targetSha256"]
 assert r["sourceId"]==x["sourceId"] and r["sourceSha256"]==x["sourceSha256"] and r["currentTargetSha256"]==x["currentTargetSha256"]
 assert sha(x["source"].encode())==x["sourceSha256"] and sha(x["currentTarget"].encode())==x["currentTargetSha256"] and sha(x["target"].encode())==x["targetSha256"]
assert seen=={(r["continuationRank"],r["locale"]) for r in cr if r["finalDecision"] in {"correct","refinement"}}
assert sum(r["finalDecision"]=="hold" for r in cr)==12 and sum(r["finalDecision"]=="retain-current" for r in cr)==224
print(json.dumps({"result":"PASS","head":a["head"],"tree":a["tree"],"selected":64,"retained":224,"holds":12}))
