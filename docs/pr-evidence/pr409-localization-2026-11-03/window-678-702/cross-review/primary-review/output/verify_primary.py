#!/usr/bin/env python3
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PACKET=ROOT.parent;INPUT=PACKET/"input"
HEAD="311127db7f4d5097dfd1dde5eaa2150f82f48f30";TREE="23210cd313efd929cca9ceda0fd78da19e5ed50d"
def sha(b):return hashlib.sha256(b).hexdigest()
def j(p):return json.loads(p.read_text(encoding="utf-8"))
def jl(p):return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def sums(root,name):
 d={}
 for line in (root/name).read_text(encoding="utf-8").splitlines():
  h,n=line.split("  ",1);d[n]=h
 assert d and all(sha((root/n).read_bytes())==h for n,h in d.items()),"checksum mismatch: "+str(root)
 return d
def checks(s,t):
 p=sorted(re.findall(r"\{[^{}]+\}",s))==sorted(re.findall(r"\{[^{}]+\}",t))
 g=sorted(re.findall(r"</?[A-Za-z][^>]*>",s))==sorted(re.findall(r"</?[A-Za-z][^>]*>",t))
 n=re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)==re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",t)
 q=set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])",s))
 for x in ("Wishlist","Soulseek","Discogs","Pod","Prometheus","Lidarr","ReplayGain","SongID","WebSocket","VBR"):
  if re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",s):q.add(x)
 return {"placeholders":p,"markup":g,"numbers":n,"protectedLiterals":all(x in t for x in q)}
def main():
 root_sums=sums(PACKET,"SHA256SUMS.txt")
 actual=sorted(x for x in PACKET.rglob("*") if x.is_file() and x.name!="SHA256SUMS.txt")
 assert set(root_sums)=={x.relative_to(PACKET).as_posix() for x in actual}
 sums(INPUT,"PACKET-SHA256SUMS.txt")
 subprocess.check_call([sys.executable,str(INPUT/"verify_input.py")],stdout=subprocess.DEVNULL)
 m=j(ROOT/"manifest.json");assert m["head"]==HEAD and m["tree"]==TREE and m["cells"]==300 and m["targetTextsIncluded"] is True
 assert m["inputChecksumListSha256"]==sha((INPUT/"PACKET-SHA256SUMS.txt").read_bytes())
 inp=jl(INPUT/"source-current-cells.jsonl");by={(x["continuationRank"],x["locale"]):x for x in inp}
 rows=jl(ROOT/"primary-review.jsonl");assert len(rows)==300 and len(by)==300
 counts={}
 for r in rows:
  c=by[(r["continuationRank"],r["locale"])]
  assert r["head"]==HEAD and r["tree"]==TREE and r["window"]=="W72"
  for k in ("sourceId","sourceSha256","source","currentTarget","currentTargetSha256","catalogPath","catalogFileSha256","catalogGitBlob","callerContextSha256"):
   assert r[k]==c[k],f"input pin mismatch: {k}"
  assert r["callerCount"]==len(c["callerRefs"]) and r["callerRefs"]==c["callerRefs"]
  assert r["disposition"] in ("accept-current","correct","refine","hold")
  assert (r["disposition"]=="hold")== (r["callerCount"]==0)
  if r["proposedTarget"] is None:
   assert r["proposedTargetSha256"] is None and r["proposedTokenChecks"] is None
   assert r["disposition"] in ("accept-current","hold")
  else:
   assert r["disposition"] in ("correct","refine")
   assert sha(r["proposedTarget"].encode())==r["proposedTargetSha256"]
   assert r["proposedTokenChecks"]==checks(r["source"],r["proposedTarget"])
   assert all(r["proposedTokenChecks"].values())
  counts[r["disposition"]]=counts.get(r["disposition"],0)+1
 assert counts==m["dispositions"] and m["proposals"]==counts.get("correct",0)+counts.get("refine",0)
 s=j(ROOT/"summary.json");assert s["reviewedCells"]==300 and s["dispositions"]==counts and s["proposedCells"]==m["proposals"]
 assert s["proposedTargetTokenFailures"]==0 and s["priorHoldsHashOnly"]==152 and s["priorSelectedIdsHashOnly"]==1782
 before=j(ROOT/"live-before.json");after=j(ROOT/"live-after.json")
 for x in (before,after):
  assert x["headRefOid"]==x["branchRefOid"]==x["pullRefOid"]==HEAD and x["treeOid"]==TREE
 assert before["deploymentsForHead"]==after["deploymentsForHead"]==0
 assert m["liveBefore"]["headRefOid"]==m["liveAfter"]["headRefOid"]==HEAD
 print(json.dumps({"verifier":"PASS","filesHashed":len(root_sums),"cells":len(rows),"dispositions":counts,"proposals":m["proposals"],"callerlessHolds":counts.get("hold",0),"candidateFreeInputVerified":True,"head":HEAD,"tree":TREE},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
