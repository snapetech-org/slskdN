#!/usr/bin/env python3
import hashlib,json,re,subprocess,sys
from collections import Counter
from pathlib import Path
O=Path(__file__).resolve().parent
I=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w65-ranks503-527-primary-20261103/input")
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
run=subprocess.run([sys.executable,str(I/"verify_input.py")],capture_output=True,text=True)
assert run.returncode==0,run.stdout+run.stderr
im=j(I/"manifest.json"); m=j(O/"manifest.json")
assert im["candidateFree"] is True
assert m["inputManifestSha256"]==sha((I/"manifest.json").read_bytes())
assert m["inputChecksumListSha256"]==sha((I/"PACKET-SHA256SUMS.txt").read_bytes())
assert (m["repository"],m["pullRequest"],m["head"],m["tree"])==(im["repository"],im["pullRequest"],im["head"],im["tree"])
assert (m["sourceCount"],m["localeCount"],m["cellCount"])==(25,12,300)
actual={p.name for p in O.iterdir() if p.is_file()}
mf={x["path"]:x for x in m["files"]}
assert set(mf)==actual-{"manifest.json","SHA256SUMS.txt"}
for n,x in mf.items():
 b=(O/n).read_bytes(); assert len(b)==x["bytes"] and sha(b)==x["sha256"],n
sums={}
for line in (O/"SHA256SUMS.txt").read_text().splitlines():
 d,n=line.split(None,1); n=n.strip().lstrip("*"); assert Path(n).name==n; sums[n]=d
assert set(sums)==actual-{"SHA256SUMS.txt"}
for n,d in sums.items(): assert sha((O/n).read_bytes())==d,n
cells=jl(I/"source-current-cells.jsonl"); ctxs=jl(I/"caller-contexts.jsonl"); rows=jl(O/"primary-ledger.jsonl")
assert len(cells)==len(rows)==300 and len(ctxs)==25
ci={(x["continuationRank"],x["locale"]):x for x in cells}; cx={x["continuationRank"]:x for x in ctxs}
seen=set(); counts=Counter(); base=Counter(); final=Counter()
for r in rows:
 k=(r["continuationRank"],r["locale"]); assert k not in seen; seen.add(k)
 x=ci[k]; c=cx[k[0]]; counts[r["disposition"]]+=1
 assert (r["repository"],r["pullRequest"],r["head"],r["tree"])==(im["repository"],im["pullRequest"],im["head"],im["tree"])
 for f in ("sourceId","source","sourceSha256","catalogKey","catalogPath","catalogFileSha256","catalogGitBlob","currentTarget","currentTargetSha256","callerContextSha256","callerRefs","continuationRank","remainingQueueRank","locale"):
  assert r[f]==x[f],(k,f)
 assert r["callerContexts"]==c["callers"] and r["callerContextSourceId"]==c["sourceId"] and r["callerContextSourceSha256"]==c["sourceSha256"]
 assert r["containsCandidate"] is False and r["verdict"] is None and r["rationale"]
 assert r["confidence"] in ("high","moderate","low")
 assert r["disposition"] in ("accept-current","correction","refinement","hold")
 if r["disposition"] in ("correction","refinement"):
  assert isinstance(r.get("proposedTarget"),str) and r["proposedTarget"]; target=r["proposedTarget"]
 else:
  assert "proposedTarget" not in r; target=r["currentTarget"]
 if r["disposition"]=="hold": assert r["confidence"]=="low" and k[0]==504
 assert r["reviewedTargetSha256"]==sha(target)
 st=tok(r["source"]); ct=tok(r["currentTarget"]); rt=tok(target)
 checks={"placeholdersPreserved":st["placeholders"]==rt["placeholders"],"markupPreserved":st["markup"]==rt["markup"],"numericTokensPreserved":st["numeric"]==rt["numeric"],"protectedLiteralsPreserved":all(z in target for z in st["protectedLiterals"])}
 assert r["tokenAudit"]=={"source":st,"current":ct,"reviewed":rt,"checks":checks} and all(checks.values()),k
 base["placeholder"]+=st["placeholders"]!=ct["placeholders"]; base["markup"]+=st["markup"]!=ct["markup"]
 base["numeric"]+=st["numeric"]!=ct["numeric"]; base["protectedLiteral"]+=not all(z in r["currentTarget"] for z in st["protectedLiterals"])
 final["placeholder"]+=not checks["placeholdersPreserved"]; final["markup"]+=not checks["markupPreserved"]
 final["numeric"]+=not checks["numericTokensPreserved"]; final["protectedLiteral"]+=not checks["protectedLiteralsPreserved"]
assert seen==set(ci) and dict(base)==im["baselineTokenMismatchSummary"]
assert dict(final)=={"placeholder":0,"markup":0,"numeric":0,"protectedLiteral":0}
expected=Counter({"accept-current":227,"correction":60,"refinement":7,"hold":6})
assert counts==expected,counts
assert all((rank==504 and locale in ("ar","de","es","fr","hi","pt-BR"))==(r["disposition"]=="hold") for r in rows for rank,locale in [(r["continuationRank"],r["locale"])])
s=j(O/"summary.json")
assert s["dispositionCounts"]==dict(counts) and s["proposalCount"]==67
assert s["baselineTokenMismatches"]==dict(base) and s["reviewedTokenMismatches"]==dict(final)
assert s["priorHeldCellsReattested"]==98 and s["candidateFreeInputVerified"] is True and s["blindPacketAccessed"] is False
assert s["nativeSpeakerReview"]=="not performed" and s["browserReview"]=="not performed"
assert m["dispositionCounts"]==dict(counts) and m["priorHeldCellsReattested"]==98
print(json.dumps({"pass":True,"inputVerifier":"PASS","checksumVerifier":"PASS","rows":300,"dispositions":dict(counts),"baselineTokenMismatches":dict(base),"reviewedTokenMismatches":dict(final),"head":m["head"],"tree":m["tree"]},ensure_ascii=False,indent=2))
