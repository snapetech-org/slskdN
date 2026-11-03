#!/usr/bin/env python3
import json,re,hashlib,pathlib,sys
from collections import Counter
def sha(b): return hashlib.sha256(b).hexdigest()
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def rows(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def need(x,m):
 if not x: raise SystemExit("FAIL: "+m)
def sums(s):
 d={}
 for line in s.splitlines():
  if line.strip():
   a=line.split("  ",1); need(len(a)==2,"bad checksum line"); d[a[1]]=a[0]
 return d
def tok(p,s): return re.findall(p,s)
def main():
 if len(sys.argv)!=2: raise SystemExit("Usage: verify_blind.py CANDIDATE_FREE_INPUT_DIR")
 out=pathlib.Path(__file__).resolve().parent; inp=pathlib.Path(sys.argv[1]).resolve()
 need(inp.is_dir(),"input directory missing"); im=load(inp/"manifest.json")
 need(im.get("candidateFree") is True and im.get("head")=="335a96a9ec125b30c20c31be219da4e27db1ab03" and im.get("tree")=="7168de556608115be3b7e16b9ceb30b977df904b","candidate-free input pin")
 for n,h in sums((inp/"PACKET-SHA256SUMS.txt").read_text(encoding="utf-8")).items():
  p=inp/n; need(p.is_file() and sha(p.read_bytes())==h,"input checksum "+n)
 for f in im["files"]:
  p=inp/f["path"]; need(p.is_file() and p.stat().st_size==f["bytes"] and sha(p.read_bytes())==f["sha256"],"input manifest "+f["path"])
 m=load(out/"manifest.json")
 need(m.get("artifact")=="slskdN PR #409 W70 independent blind semantic review","output manifest")
 need(m["candidateFreeInputManifestSha256"]==sha((inp/"manifest.json").read_bytes()) and m["candidateFreePacketChecksumsSha256"]==sha((inp/"PACKET-SHA256SUMS.txt").read_bytes()),"input pin hashes")
 need(m["head"]==im["head"] and m["tree"]==im["tree"],"output head/tree")
 for n,h in sums((out/"SHA256SUMS.txt").read_text(encoding="utf-8")).items():
  p=out/n; need(p.is_file() and sha(p.read_bytes())==h,"output checksum "+n)
 for f in m["files"]:
  p=out/f["path"]; need(p.is_file() and p.stat().st_size==f["bytes"] and sha(p.read_bytes())==f["sha256"],"output manifest "+f["path"])
 src=rows(inp/"source-current-cells.jsonl"); ctx=rows(inp/"caller-contexts.jsonl"); old=rows(inp/"prior-held-cell-reattestation.jsonl")
 led=rows(out/"blind-ledger.jsonl"); hold=rows(out/"prior-hold-reattestation.jsonl")
 need(len(src)==len(led)==300 and len(old)==len(hold)==140,"row counts")
 need(all(r.get("containsCandidate") is False for r in src+led),"candidate marker")
 cm={(x["continuationRank"],x["sourceId"]):x for x in ctx}; counts=Counter(); allowed={"accept-current","correction","refinement","hold"}
 for i,(a,b) in enumerate(zip(src,led)):
  for f in ("continuationRank","remainingQueueRank","sourceId","locale"): need(a[f]==b[f],f"cell order/key {i}")
  for f in ("source","sourceSha256","catalogKey","catalogPath","catalogFileSha256","catalogGitBlob","currentTarget","currentTargetSha256","callerContextSha256","callerRefs"): need(a[f]==b[f],f"input join {f} row {i}")
  need(sha(b["source"].encode())==b["sourceSha256"] and sha(b["currentTarget"].encode())==b["currentTargetSha256"] and sha(b["selectedTarget"].encode())==b["selectedTargetSha256"],f"target/source hash row {i}")
  c=cm[(a["continuationRank"],a["sourceId"])]
  expected_refs=[{k:v for k,v in q.items() if k in ("path","line","lineSha256","fileSha256","gitBlob")} for q in c["callers"]]
  need(c["sourceSha256"]==b["sourceSha256"] and c["productionCallerCount"]==b["productionCallerCount"]==len(expected_refs)>0 and expected_refs==b["callerRefs"] and a["callerContextSha256"]==b["callerContextSha256"],f"caller pin/ref row {i}")
  d=b["disposition"]; need(d in allowed,f"disposition row {i}"); counts[d]+=1
  need((b["selectedTarget"]==b["currentTarget"]) if d in ("accept-current","hold") else (b["selectedTarget"]!=b["currentTarget"]),f"target disposition row {i}")
  s=b["source"]; t=b["selectedTarget"]
  ev={"placeholders":{"source":tok(r"\{[^{}]+\}",s),"selected":tok(r"\{[^{}]+\}",t)},"markup":{"source":tok(r"<[^>]+>",s),"selected":tok(r"<[^>]+>",t)},"numericTokens":{"source":tok(r"\d+",s),"selected":tok(r"\d+",t)},"protectedLiterals":{"source":a["sourceProtectedLiterals"],"selected":[x for x in a["sourceProtectedLiterals"] if x in t]}}
  for k,v in ev.items():
   need(v["source"]==v["selected"],f"{k} mismatch row {i}")
   rec=b["tokenChecks"][k]; need(rec["source"]==v["source"] and rec["selected"]==v["selected"] and rec["matches"] is True,f"{k} evidence row {i}")
  need(b["confidence"] in ("high","moderate","low","unknown"),f"confidence row {i}")
 need(dict(counts)==m["dispositionCounts"] and sum(counts.values())==300,"decision totals")
 for i,(a,b) in enumerate(zip(old,hold)):
  for f in ("priorWindow","continuationRank","sourceId","sourceSha256","locale","priorDisposition","priorTargetSha256","currentTargetSha256","matchesPriorCurrentValue","priorCallerCount","currentCallerCount","currentCallerContextSha256","currentCatalogPath","currentCatalogFileSha256","currentCatalogGitBlob","currentCallerRefs","holdReason"): need(a[f]==b[f],f"hold join {f} {i}")
  need(a["priorTargetSha256"]==a["currentTargetSha256"] and a["matchesPriorCurrentValue"] is True and b["status"]=="reattested-unchanged" and b["targetTextOmitted"] is True,"prior hold hash/status")
  need(not any(k in b for k in ("currentTarget","selectedTarget","targetText")),"prior target text omitted")
 need(m["priorHoldReattestationCount"]==140,"manifest hold count")
 print("PASS: 300 blind-reviewed cells; "+", ".join(f"{x}={counts[x]}" for x in ("accept-current","correction","refinement","hold"))+"; 140 prior holds hash-reattested; token/context/hash/checksum pins valid.")
if __name__=="__main__": main()
