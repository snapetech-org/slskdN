#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parent; BASE=ROOT.parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def j(p):return json.loads(p.read_text(encoding="utf-8"))
def rows(p):return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
i=j(BASE/"candidate-free-input.json"); b=rows(BASE/"blind-translation-review.jsonl"); x=rows(ROOT/"cross-review-ledger.jsonl"); s=j(ROOT/"cross-review-summary.json"); a=j(ROOT/"independent-assessment.json"); seal=j(ROOT/"independent-seal.json")
expected=["es","zh-Hans","hi","de","ja","fr","pt-BR","ar","ko","zh-Hant","vi","id"]
assert seal["proposalFilesOpenedBeforeSeal"] is False and seal["assessmentSha256"]==sha((ROOT/"independent-assessment.json").read_bytes())
assert s["candidateFreeInputSha256"]==sha((BASE/"candidate-free-input.json").read_bytes())
assert s["independentAssessmentSha256"]==sha((ROOT/"independent-assessment.json").read_bytes())
assert s["independentSealSha256"]==sha((ROOT/"independent-seal.json").read_bytes())
assert s["translationProposalSha256"]==sha((BASE/"blind-translation-review.jsonl").read_bytes())
assert len(b)==len(x)==12 and [r["locale"] for r in b]==expected and [r["locale"] for r in x]==expected
assert s["head"]==i["head"] and s["tree"]==i["tree"] and s["sourceId"]==i["proposedSourceId"] and s["sourceSha256"]==i["proposedSourceSha256"]
for src,tgt in zip(b,x):
 assert tgt["decision"]=="accept" and tgt["locale"]==src["locale"] and tgt["sourceId"]==src["sourceId"]
 assert tgt["sourceSha256"]==src["sourceSha256"] and tgt["target"]==src["target"] and tgt["targetSha256"]==src["targetSha256"]==sha(src["target"].encode())
 assert tgt["placeholderCounts"]=={"mode":1,"signature":1}
 assert src["target"].count("{mode}")==1 and src["target"].count("{signature}")==1
 assert src["modeAndSignatureAsCallerNodes"] is True
assert s["counts"]=={"accept":12,"hold":0} and s["confidenceCounts"]=={"moderate":11,"low":1}
assert s["lowConfidenceLocales"]==["hi"] and s["nativeSpeakerSignoff"] is False and s["browserReview"] is False
print(json.dumps({"result":"PASS","head":s["head"],"tree":s["tree"],"accepted":12,"holds":0,"lowConfidenceLocales":["hi"]}))
