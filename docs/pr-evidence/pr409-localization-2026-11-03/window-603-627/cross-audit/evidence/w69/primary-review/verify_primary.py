#!/usr/bin/env python3
import hashlib,json,re,subprocess,sys
from collections import Counter
from pathlib import Path
I=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w69-ranks603-627-candidate-free-20261103/input")
O=Path(__file__).resolve().parent
REPO=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w68-apply-20261103/repo")
HEAD="9ef252a53d2c14201c736de41efd0531bc00965a"; TREE="becf17f8be3f3251691002dbce487c1e94693e63"; BRANCH="codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode("utf-8")).hexdigest()
def j(p): return json.loads(p.read_text(encoding="utf-8"))
def jl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def ph(s): return sorted(set(re.findall(r"\{[^{}]+\}",s)))
def tags(s): return sorted(re.findall(r"</?[A-Za-z][^>]*>",s))
def nums(s): return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)
def prot(s):
 found=set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])",s))
 for x in ("Wishlist","Soulseek","Discogs","Pod"):
  if re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",s): found.add(x)
 return sorted(found)
def tok(s): return {"placeholders":ph(s),"markup":tags(s),"numeric":nums(s),"protectedLiterals":prot(s)}
def checks(source,target):
 a,b=tok(source),tok(target)
 return {"placeholdersPreserved":a["placeholders"]==b["placeholders"],"markupPreserved":a["markup"]==b["markup"],"numericTokensPreserved":a["numeric"]==b["numeric"],"protectedLiteralsPreserved":all(target.count(x)>=source.count(x) for x in a["protectedLiterals"])}
def git(*args): return subprocess.check_output(["git","-C",str(REPO),*args],text=True).strip()
def run(args,cwd=None): return subprocess.run(args,cwd=cwd,check=True,capture_output=True,text=True).stdout
subprocess.run([sys.executable,str(I/"verify_input.py")],check=True)
run(["sha256sum","-c","PACKET-SHA256SUMS.txt"],cwd=I)
run(["sha256sum","-c","SHA256SUMS.txt"],cwd=O)
im=j(I/"manifest.json"); m=j(O/"manifest.json"); s=j(O/"summary.json")
assert (im["head"],im["tree"],im["continuationRankRange"],im["remainingQueueRankRange"])==(HEAD,TREE,[603,627],[503,527])
assert (m["repository"],m["pullRequest"],m["branch"],m["window"],m["head"],m["tree"])==("snapetech-org/slskdN",409,BRANCH,"W69",HEAD,TREE)
assert (m["sourceCount"],m["localeCount"],m["cellCount"],m["priorHeldCellsReattested"])==(25,12,300,128)
assert m["blindPacketAccessed"] is False and s["blindPacketAccessed"] is False
assert s["candidateFreeInputVerified"] is True and s["repositoryOrPRFilesEdited"] is False
assert s["nativeSpeakerReview"]==m["nativeSpeakerReview"]=="not performed"
assert s["browserReview"]==m["browserReview"]=="not performed"
assert m["inputManifestSha256"]==sha((I/"manifest.json").read_bytes())
assert m["inputChecksumListSha256"]==sha((I/"PACKET-SHA256SUMS.txt").read_bytes())
assert m["inputCellLedgerSha256"]==sha((I/"source-current-cells.jsonl").read_bytes())
assert m["inputCallerContextSha256"]==sha((I/"caller-contexts.jsonl").read_bytes())
assert (git("rev-parse","HEAD"),git("rev-parse","HEAD^{tree}"),git("status","--porcelain=v1"))==(HEAD,TREE,"")
pr=json.loads(run(["gh","api","repos/snapetech-org/slskdN/pulls/409"]))
assert pr["state"]=="open" and pr["draft"] is True and pr["head"]["sha"]==HEAD and pr["head"]["ref"]==BRANCH
refs=run(["git","-C",str(REPO),"ls-remote","origin",f"refs/heads/{BRANCH}","refs/pull/409/head"]).splitlines()
refmap={x.split()[1]:x.split()[0] for x in refs}
assert refmap.get(f"refs/heads/{BRANCH}")==HEAD and refmap.get("refs/pull/409/head")==HEAD
listed={x["path"]:x for x in m["files"]}
actual={p.name for p in O.iterdir() if p.is_file()}-{"manifest.json","SHA256SUMS.txt"}
assert set(listed)==actual
for name,item in listed.items():
 data=(O/name).read_bytes()
 assert len(data)==item["bytes"] and sha(data)==item["sha256"],name
cells=jl(I/"source-current-cells.jsonl"); contexts=jl(I/"caller-contexts.jsonl"); rows=jl(O/"primary-ledger.jsonl")
assert len(cells)==len(rows)==300 and len(contexts)==25
ci={(x["continuationRank"],x["locale"]):x for x in cells}; cx={x["continuationRank"]:x for x in contexts}
seen=set(); counts=Counter(); base=Counter(); final=Counter(); proposal_count=0
assert all((x["callers"] or x["productionCallerCount"]==0) and x["productionCallerCount"]==len(x["callers"]) for x in contexts)
assert sorted(cx)==list(range(603,628))
for r in rows:
 key=(r["continuationRank"],r["locale"])
 assert key not in seen and key in ci
 seen.add(key); x=ci[key]; c=cx[key[0]]; counts[r["disposition"]]+=1
 assert r["locale"] in LOCALES and r["disposition"] in ("accept-current","correction","refinement","hold")
 assert (r["repository"],r["pullRequest"],r["window"],r["head"],r["tree"])==(im["repository"],409,"W69",HEAD,TREE)
 for field in ("sourceId","source","sourceSha256","catalogKey","catalogPath","catalogFileSha256","catalogGitBlob","currentTarget","currentTargetSha256","callerContextSha256","callerRefs","continuationRank","remainingQueueRank","locale"):
  assert r[field]==x[field],(key,field)
 assert r["callerContexts"]==c["callers"] and r["callerContextSourceId"]==c["sourceId"] and r["callerContextSourceSha256"]==c["sourceSha256"]
 assert r["containsCandidate"] is False and r["verdict"] is None and r["rationale"] and r["confidence"] in ("high","moderate","low")
 if r["disposition"] in ("correction","refinement"):
  target=r["proposedTarget"]; assert target and target!=r["currentTarget"]; proposal_count+=1
 else:
  target=r["currentTarget"]; assert "proposedTarget" not in r
 if r["disposition"]=="hold": assert r["continuationRank"]==615
 st,ct,rt=tok(r["source"]),tok(r["currentTarget"]),tok(target)
 ck=checks(r["source"],target)
 assert r["reviewedTargetSha256"]==sha(target)
 assert r["tokenAudit"]=={"source":st,"current":ct,"reviewed":rt,"checks":ck}
 assert all(ck.values()),key
 base["placeholder"]+=st["placeholders"]!=ct["placeholders"]; base["markup"]+=st["markup"]!=ct["markup"]; base["numeric"]+=st["numeric"]!=ct["numeric"]; base["protectedLiteral"]+=not all(r["currentTarget"].count(x)>=r["source"].count(x) for x in st["protectedLiterals"])
 final["placeholder"]+=not ck["placeholdersPreserved"]; final["markup"]+=not ck["markupPreserved"]; final["numeric"]+=not ck["numericTokensPreserved"]; final["protectedLiteral"]+=not ck["protectedLiteralsPreserved"]
assert seen==set(ci)
assert dict(base)==im["baselineTokenMismatchSummary"]==s["baselineTokenMismatches"]
assert dict(final)==s["reviewedTokenMismatches"] and not any(final.values())
assert sorted(x["continuationRank"] for x in contexts if x["productionCallerCount"]==0)==[615]
assert counts["hold"]==12 and counts["correction"]==26 and counts["refinement"]==5 and counts["accept-current"]==257
assert proposal_count==31 and s["proposalCount"]==m["proposalCount"]==proposal_count
assert s["dispositionCounts"]==dict(counts) and m["dispositionCounts"]==dict(counts)
ps=j(I/"prior-held-cell-reattestation-summary.json")
assert ps["expectedHeldCells"]==ps["priorHeldCellsReattested"]==128 and ps["allTargetHashesMatchPrior"] and ps["allCurrentCallerAndCatalogEvidenceRepinned"]
assert s["priorHeldCellsReattested"]==128 and s["priorHeldCellsUnchanged"] is True
print(json.dumps({"pass":True,"head":HEAD,"tree":TREE,"window":"W69","cells":300,"sources":25,"locales":12,"dispositions":dict(counts),"proposals":proposal_count,"baselineTokenMismatches":dict(base),"reviewedTokenMismatches":dict(final),"carriedHoldsReattested":128,"callerlessHeldRanks":[615],"PR":"OPEN/DRAFT","blindPacketAccessed":False,"nativeSpeakerReview":"not performed","browserReview":"not performed"},ensure_ascii=False,indent=2))
