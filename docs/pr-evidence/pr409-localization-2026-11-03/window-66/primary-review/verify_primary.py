#!/usr/bin/env python3
import hashlib,json,re,subprocess,sys
from collections import Counter
from pathlib import Path
O=Path(__file__).resolve().parent
I=O.parent/"input"
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def j(p): return json.loads(p.read_text(encoding="utf-8"))
def jl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def ph(s): return sorted(set(re.findall(r"\{[^{}]+\}",s)))
def tags(s): return sorted(re.findall(r"</?[A-Za-z][^>]*>",s))
def nums(s): return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)
def prot(s):
 f=set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])",s))
 for x in ("Wishlist","Soulseek","Discogs","Pod"):
  if re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",s): f.add(x)
 return sorted(f)
def tok(s): return {"placeholders":ph(s),"markup":tags(s),"numeric":nums(s),"protectedLiterals":prot(s)}
def verify_sums(folder,name):
 for line in (folder/name).read_text().splitlines():
  if not line.strip(): continue
  digest,n=line.split(None,1); n=n.strip().lstrip("*")
  assert sha((folder/n).read_bytes())==digest,(folder/n,"checksum")
input_result=subprocess.run([sys.executable,str(I/"verify_input.py")],capture_output=True,text=True)
assert input_result.returncode==0,input_result.stdout+input_result.stderr
im=j(I/"manifest.json"); m=j(O/"manifest.json"); s=j(O/"summary.json")
assert im["candidateFree"] is True
assert (m["repository"],m["pullRequest"],m["window"],m["head"],m["tree"])==(
 im["repository"],im["pullRequest"],"W66",im["head"],im["tree"])
assert (m["sourceCount"],m["localeCount"],m["cellCount"],m["priorHeldCellsReattested"])==(25,12,300,104)
assert m["inputManifestSha256"]==sha((I/"manifest.json").read_bytes())
assert m["inputChecksumListSha256"]==sha((I/"PACKET-SHA256SUMS.txt").read_bytes())
verify_sums(O,"SHA256SUMS.txt")
actual={p.name for p in O.iterdir() if p.is_file()}
mf={x["path"]:x for x in m["files"]}
assert set(mf)==actual-{"manifest.json","SHA256SUMS.txt"}
for name,x in mf.items():
 b=(O/name).read_bytes()
 assert len(b)==x["bytes"] and sha(b)==x["sha256"],name
cells=jl(I/"source-current-cells.jsonl")
contexts=jl(I/"caller-contexts.jsonl")
rows=jl(O/"primary-ledger.jsonl")
assert len(cells)==len(rows)==300 and len(contexts)==25
ci={(x["continuationRank"],x["locale"]):x for x in cells}
cx={x["continuationRank"]:x for x in contexts}
seen=set(); counts=Counter(); base=Counter(); final=Counter(); proposal_count=0
for r in rows:
 k=(r["continuationRank"],r["locale"])
 assert k not in seen
 seen.add(k)
 x=ci[k]; c=cx[k[0]]
 counts[r["disposition"]]+=1
 assert (r["repository"],r["pullRequest"],r["window"],r["head"],r["tree"])==(
  im["repository"],im["pullRequest"],"W66",im["head"],im["tree"])
 for f in ("sourceId","source","sourceSha256","catalogKey","catalogPath","catalogFileSha256","catalogGitBlob",
           "currentTarget","currentTargetSha256","callerContextSha256","callerRefs","continuationRank","remainingQueueRank","locale"):
  assert r[f]==x[f],(k,f)
 assert r["callerContexts"]==c["callers"]
 assert r["callerContextSourceId"]==c["sourceId"] and r["callerContextSourceSha256"]==c["sourceSha256"]
 assert r["containsCandidate"] is False and r["verdict"] is None and r["rationale"]
 assert r["confidence"] in ("high","moderate","low")
 assert r["disposition"] in ("accept-current","correction","refinement","hold")
 if r["disposition"] in ("correction","refinement"):
  assert isinstance(r.get("proposedTarget"),str) and r["proposedTarget"]
  target=r["proposedTarget"]; proposal_count+=1
 else:
  assert "proposedTarget" not in r
  target=r["currentTarget"]
 if r["disposition"]=="hold":
  assert r["confidence"]=="low" and r["continuationRank"] in (533,541)
  assert target==r["currentTarget"]
 assert r["reviewedTargetSha256"]==sha(target)
 st,ct,rt=tok(r["source"]),tok(r["currentTarget"]),tok(target)
 checks={"placeholdersPreserved":st["placeholders"]==rt["placeholders"],
  "markupPreserved":st["markup"]==rt["markup"],"numericTokensPreserved":st["numeric"]==rt["numeric"],
  "protectedLiteralsPreserved":all(z in target for z in st["protectedLiterals"])}
 assert r["tokenAudit"]=={"source":st,"current":ct,"reviewed":rt,"checks":checks}
 assert all(checks.values()),(k,checks)
 base["placeholder"]+=st["placeholders"]!=ct["placeholders"]
 base["markup"]+=st["markup"]!=ct["markup"]
 base["numeric"]+=st["numeric"]!=ct["numeric"]
 base["protectedLiteral"]+=not all(z in r["currentTarget"] for z in st["protectedLiterals"])
 final["placeholder"]+=not checks["placeholdersPreserved"]
 final["markup"]+=not checks["markupPreserved"]
 final["numeric"]+=not checks["numericTokensPreserved"]
 final["protectedLiteral"]+=not checks["protectedLiteralsPreserved"]
assert seen==set(ci)
assert dict(base)==im["baselineTokenMismatchSummary"]
assert dict(final)=={"placeholder":0,"markup":0,"numeric":0,"protectedLiteral":0}
assert counts==Counter({"accept-current":227,"correction":36,"refinement":13,"hold":24}),counts
assert proposal_count==49
assert all((r["continuationRank"] in (533,541))==(r["disposition"]=="hold") for r in rows)
assert all(sum(r["continuationRank"]==rank for r in rows if r["disposition"]=="hold")==12 for rank in (533,541))
assert s["dispositionCounts"]==dict(counts) and s["proposalCount"]==proposal_count
assert s["baselineTokenMismatches"]==dict(base) and s["reviewedTokenMismatches"]==dict(final)
assert s["priorHeldCellsReattested"]==104 and s["callerlessSelectedRanks"]==[533,541]
assert s["candidateFreeInputVerified"] is True and s["blindPacketAccessed"] is False
assert s["nativeSpeakerReview"]=="not performed" and s["browserReview"]=="not performed"
assert m["dispositionCounts"]==dict(counts) and m["proposalCount"]==proposal_count
assert m["blindPacketAccessed"] is False and m["nativeSpeakerReview"]=="not performed" and m["browserReview"]=="not performed"
print(json.dumps({"pass":True,"inputVerifier":"PASS","checksums":"PASS","head":m["head"],"tree":m["tree"],
 "rows":300,"dispositions":dict(counts),"proposals":proposal_count,"baselineTokenMismatches":dict(base),
 "reviewedTokenMismatches":dict(final),"priorHoldsReattested":104,"callerlessHolds":[533,541],
 "browserReview":"not performed","nativeSpeakerReview":"not performed","repositoryOrPRFilesEdited":False},ensure_ascii=False,indent=2))
