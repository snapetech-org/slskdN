#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent; B=R.parent; C=B/"cross-review"
sha=lambda b:hashlib.sha256(b).hexdigest()
def j(p):return json.loads(p.read_text(encoding="utf-8"))
def rows(p):return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
a=j(R/"review.json"); inp=j(B/"candidate-free-input.json"); blind=rows(B/"blind-translation-review.jsonl"); cross=rows(C/"cross-review-ledger.jsonl"); out=rows(R/"accepted-translations.jsonl"); s=j(C/"cross-review-summary.json")
assert len(blind)==len(cross)==len(out)==12 and a["acceptedCount"]==12 and a["holdCount"]==0
assert a["head"]==inp["head"]==s["head"] and a["tree"]==inp["tree"]==s["tree"]
assert a["sourceId"]==inp["proposedSourceId"]==s["sourceId"] and a["sourceSha256"]==inp["proposedSourceSha256"]==s["sourceSha256"]
assert a["candidateFreeInputSha256"]==sha((B/"candidate-free-input.json").read_bytes())
assert a["blindTranslationLedgerSha256"]==sha((B/"blind-translation-review.jsonl").read_bytes())
assert a["crossReviewLedgerSha256"]==sha((C/"cross-review-ledger.jsonl").read_bytes())
assert a["crossReviewSummarySha256"]==sha((C/"cross-review-summary.json").read_bytes())
assert a["enumEvidence"]["fileSha256"]=="c0cff69ea19915e7d00404f99c4a8355b6995b08dc175b4315e085579f4333f0"
assert a["joinModeEvidence"]["fileSha256"]=="49b0fcaa71b0aa446a5e6df84359c2cb2619a1458db0a2338f31e0187b531b79"
assert a["verificationEvidence"]["fileSha256"]=="c917846757571639e2cacef090746f595b6200ab0cc02691b088b45cfee84194"
for b,c,r in zip(blind,cross,out):
 assert c["decision"]=="accept" and r["rootDisposition"]=="accept" and b["locale"]==c["locale"]==r["locale"]
 assert b["target"]==c["target"]==r["target"] and b["targetSha256"]==c["targetSha256"]==r["targetSha256"]==sha(r["target"].encode())
 assert b["target"].count("{mode}")==b["target"].count("{signature}")==1
assert [r["locale"] for r in out]==s["localeOrder"]
print(json.dumps({"result":"PASS","head":a["head"],"accepted":12,"holds":0,"lowConfidenceLocales":a["lowConfidenceLocales"],"enumVerified":True}))
