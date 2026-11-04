#!/usr/bin/env python3
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PACKET=ROOT.parent
INPUT=PACKET/"input"
HEAD="311127db7f4d5097dfd1dde5eaa2150f82f48f30"
TREE="23210cd313efd929cca9ceda0fd78da19e5ed50d"
def sha(b):return hashlib.sha256(b).hexdigest()
def j(p):return json.loads(p.read_text(encoding="utf-8"))
def jl(p):return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def verify_sums(root,name):
 rows={}
 for line in (root/name).read_text(encoding="utf-8").splitlines():
  h,p=line.split("  ",1);rows[p]=h
 assert rows and all(sha((root/p).read_bytes())==h for p,h in rows.items()),"checksum mismatch "+str(root)
 return rows
def main():
 sums=verify_sums(PACKET,"SHA256SUMS.txt")
 actual=sorted(p for p in PACKET.rglob("*") if p.is_file() and p.name!="SHA256SUMS.txt")
 assert set(sums)=={p.relative_to(PACKET).as_posix() for p in actual},"packet file inventory mismatch"
 verify_sums(INPUT,"PACKET-SHA256SUMS.txt")
 subprocess.check_call([sys.executable,str(INPUT/"verify_input.py")],stdout=subprocess.DEVNULL)
 m=j(ROOT/"manifest.json")
 assert m["head"]==HEAD and m["tree"]==TREE and m["cells"]==300 and m["targetTextsIncluded"] is False
 assert m["inputChecksumListSha256"]==sha((INPUT/"PACKET-SHA256SUMS.txt").read_bytes())
 cells=jl(INPUT/"source-current-cells.jsonl")
 bykey={(x["continuationRank"],x["locale"]):x for x in cells}
 ledger=jl(ROOT/"blind-ledger.jsonl")
 assert len(ledger)==300 and len(bykey)==300
 counts={}
 for r in ledger:
  k=(r["continuationRank"],r["locale"]);c=bykey[k]
  assert r["head"]==HEAD and r["tree"]==TREE and r["window"]=="W72"
  assert r["sourceId"]==c["sourceId"] and r["sourceSha256"]==c["sourceSha256"]
  assert r["currentTargetSha256"]==c["currentTargetSha256"] and r["callerContextSha256"]==c["callerContextSha256"]
  assert r["callerCount"]==len(c["callerRefs"]) and r["targetTextIncluded"] is False
  assert r["recommendation"] in ("accept-current","correct","refine","hold")
  assert (r["recommendation"]=="hold")==(r["callerCount"]==0)
  if r["recommendation"] in ("correct","refine"):
   assert re.fullmatch(r"[0-9a-f]{64}",r["recommendedTargetSha256"] or "")
   assert r["recommendedTokenChecks"] and all(r["recommendedTokenChecks"].values())
  else:assert r["recommendedTargetSha256"] is None and r["recommendedTokenChecks"] is None
  assert "recommendedTarget" not in r and "currentTarget" not in r and "source" not in r
  counts[r["recommendation"]]=counts.get(r["recommendation"],0)+1
 assert counts==m["dispositions"] and sum(counts.values())==300
 assert counts.get("hold")==108 and m["callerlessHolds"]==108 and m["proposals"]==counts.get("correct",0)+counts.get("refine",0)
 s=j(ROOT/"summary.json")
 assert s["dispositions"]==counts and s["reviewedCells"]==300 and s["proposals"]==m["proposals"]
 assert s["priorHoldsHashOnly"]==152 and s["priorSelectedIdsHashOnly"]==1782 and s["targetTextsIncluded"] is False
 before=j(ROOT/"live-before.json");after=j(ROOT/"live-after.json")
 for a in (before,after):
  assert a["headRefOid"]==a["branchRefOid"]==a["pullRefOid"]==HEAD and a["treeOid"]==TREE
 assert before["deploymentsForHead"]==after["deploymentsForHead"]==0
 assert m["liveBefore"]["headRefOid"]==m["liveAfter"]["headRefOid"]==HEAD
 assert m["liveBefore"]["treeOid"]==m["liveAfter"]["treeOid"]==TREE
 assert not any(p.name.startswith("slskdn-pr409-w71-es-hi-vi") for p in ROOT.iterdir())
 print(json.dumps({"verifier":"PASS","filesHashed":len(sums),"blindCells":len(ledger),"dispositions":counts,"proposals":m["proposals"],"callerlessHolds":108,"candidateFreeInputVerified":True,"head":HEAD,"tree":TREE},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
