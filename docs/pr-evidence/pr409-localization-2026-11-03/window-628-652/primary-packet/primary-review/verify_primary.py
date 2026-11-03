#!/usr/bin/env python3
import hashlib,json,re,subprocess,sys
from collections import Counter
from pathlib import Path
O=Path(__file__).resolve().parent
I=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w70-ranks628-652-candidate-free-20261103/input")
REPO=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w69-apply-20261103/repo")
HEAD="335a96a9ec125b30c20c31be219da4e27db1ab03"; TREE="7168de556608115be3b7e16b9ceb30b977df904b"
BRANCH="codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def j(p): return json.loads(p.read_text(encoding="utf-8"))
def jl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def git(*args): return subprocess.check_output(["git","-C",str(REPO),*args],text=True).strip()
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
def req(x,msg):
 if not x: raise SystemExit("FAIL: "+msg)
subprocess.run([sys.executable,str(I/"verify_input.py")],check=True)
subprocess.run(["sha256sum","-c","SHA256SUMS.txt"],cwd=O,check=True,capture_output=True,text=True)
m=j(O/"manifest.json"); s=j(O/"summary.json"); im=j(I/"manifest.json")
req((m["repository"],m["pullRequest"],m["branch"],m["window"],m["head"],m["tree"])==("snapetech-org/slskdN",409,BRANCH,"W70",HEAD,TREE),"primary exact-head/window")
req((m["sourceCount"],m["localeCount"],m["cellCount"],m["carriedHoldsReattested"],m["priorSelectedIdsExcluded"])==(25,12,300,140,1732),"primary coverage/lineage counts")
req(m["blindPacketAccessed"] is False and m["crossAuditPacketAccessed"] is False and s["blindPacketAccessed"] is False and s["crossAuditPacketAccessed"] is False,"blind/cross packet access flags")
req(s["candidateFreeInputVerified"] and s["repositoryOrPRFilesEdited"] is False,"primary process summary")
req(m["inputManifestSha256"]==sha((I/"manifest.json").read_bytes()) and m["inputChecksumListSha256"]==sha((I/"PACKET-SHA256SUMS.txt").read_bytes()) and m["inputCellLedgerSha256"]==sha((I/"source-current-cells.jsonl").read_bytes()) and m["inputCallerContextSha256"]==sha((I/"caller-contexts.jsonl").read_bytes()),"input hash references")
listed={x["path"]:x for x in m["files"]}; actual={p.name for p in O.iterdir() if p.is_file()}-{"manifest.json","SHA256SUMS.txt"}
req(set(listed)==actual,"output manifest file set")
for name,x in listed.items():
 b=(O/name).read_bytes(); req(len(b)==x["bytes"] and sha(b)==x["sha256"],"output manifest file hash: "+name)
req((git("rev-parse","HEAD"),git("rev-parse","HEAD^{tree}"),git("status","--porcelain=v1"))==(HEAD,TREE,""),"clean exact-head checkout")
pr=json.loads(subprocess.check_output(["gh","api","repos/snapetech-org/slskdN/pulls/409"],text=True))
req(pr["state"]=="open" and pr["draft"] is True and pr["head"]["sha"]==HEAD and pr["head"]["ref"]==BRANCH,"live PR")
refs=subprocess.check_output(["git","-C",str(REPO),"ls-remote","origin",f"refs/heads/{BRANCH}","refs/pull/409/head"],text=True).splitlines()
rm={x.split()[1]:x.split()[0] for x in refs}
req(rm.get(f"refs/heads/{BRANCH}")==HEAD and rm.get("refs/pull/409/head")==HEAD,"live branch/pull refs")
cells=jl(I/"source-current-cells.jsonl"); contexts=jl(I/"caller-contexts.jsonl"); rows=jl(O/"primary-ledger.jsonl")
req(len(cells)==len(rows)==300 and len(contexts)==25,"review row count")
ci={(x["continuationRank"],x["locale"]):x for x in cells}; cx={x["continuationRank"]:x for x in contexts}
seen=set(); counts=Counter(); base=Counter(); final=Counter(); changes=0
for r in rows:
 key=(r["continuationRank"],r["locale"])
 req(key not in seen and key in ci,"duplicate or unexpected cell"); seen.add(key); x=ci[key]; c=cx[key[0]]
 counts[r["disposition"]]+=1
 req(r["locale"] in LOCALES and r["disposition"] in ("accept-current","correction","refinement","hold"),"valid disposition")
 req((r["repository"],r["pullRequest"],r["window"],r["head"],r["tree"])==(im["repository"],409,"W70",HEAD,TREE),"row head/window")
 for field in ("sourceId","source","sourceSha256","catalogKey","catalogPath","catalogFileSha256","catalogGitBlob","currentTarget","currentTargetSha256","callerContextSha256","callerRefs","continuationRank","remainingQueueRank","locale"):
  req(r[field]==x[field],"input pin "+str(key)+" "+field)
 req(r["callerContexts"]==c["callers"] and r["callerContextSourceId"]==c["sourceId"] and r["callerContextSourceSha256"]==c["sourceSha256"],"caller context "+str(key))
 req(r["containsCandidate"] is False and r["verdict"] is None and r["rationale"] and r["confidence"] in ("high","moderate","low"),"review metadata "+str(key))
 if r["disposition"] in ("correction","refinement"):
  req(r.get("proposedTarget")==r["selectedTarget"] and r["selectedTarget"]!=r["currentTarget"],"changed target "+str(key)); changes+=1
 else:
  req("proposedTarget" not in r and r["selectedTarget"]==r["currentTarget"],"unchanged target "+str(key))
 st,ct,tt=tok(r["source"]),tok(r["currentTarget"]),tok(r["selectedTarget"])
 ck=checks(r["source"],r["selectedTarget"])
 req(r["selectedTargetSha256"]==sha(r["selectedTarget"]),"selected exact target hash")
 req(r["tokenAudit"]=={"source":st,"current":ct,"selected":tt,"checks":ck},"token audit record")
 req(all(ck.values()),"selected token check "+str(key))
 base["placeholder"]+=st["placeholders"]!=ct["placeholders"]; base["markup"]+=st["markup"]!=ct["markup"]; base["numeric"]+=st["numeric"]!=ct["numeric"]; base["protectedLiteral"]+=not all(r["currentTarget"].count(x)>=r["source"].count(x) for x in st["protectedLiterals"])
 final["placeholder"]+=not ck["placeholdersPreserved"]; final["markup"]+=not ck["markupPreserved"]; final["numeric"]+=not ck["numericTokensPreserved"]; final["protectedLiteral"]+=not ck["protectedLiteralsPreserved"]
req(seen==set(ci),"complete cell coverage")
req(dict(base)==im["baselineTokenMismatchSummary"]==s["baselineTokenMismatches"],"baseline token mismatches")
req(dict(final)==s["reviewedTokenMismatches"] and not any(final.values()),"reviewed target token mismatches")
req(counts["hold"]==0 and s["holdCount"]==0,"unexpected holds")
req(changes==m["proposalCount"]==s["proposalCount"] and dict(counts)==m["dispositionCounts"]==s["dispositionCounts"],"decision counts")
ps=j(I/"prior-held-cell-reattestation-summary.json")
req(ps["priorHeldCellsReattested"]==140 and ps["allTargetHashesMatchPrior"] and ps["allCurrentCallerAndCatalogEvidenceRepinned"] and s["carriedHoldsUnchanged"],"carried holds")
req(m["nativeSpeakerReview"]==s["nativeSpeakerReview"]=="not performed" and m["browserReview"]==s["browserReview"]=="not performed","review scope")
print(json.dumps({"pass":True,"head":HEAD,"tree":TREE,"window":"W70","sources":25,"cells":300,"dispositions":dict(counts),"changedTargets":changes,"baselineTokenMismatches":dict(base),"selectedTokenMismatches":dict(final),"carriedHoldsReattested":140,"priorIds":1732,"PR":"OPEN/DRAFT","blindPacketAccessed":False,"crossAuditPacketAccessed":False},ensure_ascii=False,indent=2))
