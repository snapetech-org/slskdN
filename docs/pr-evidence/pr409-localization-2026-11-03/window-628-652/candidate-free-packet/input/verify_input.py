#!/usr/bin/env python3
import hashlib,json,re,subprocess,sys
from collections import Counter
from pathlib import Path

I=Path(__file__).resolve().parent
REPO=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w69-apply-20261103/repo")
HEAD="335a96a9ec125b30c20c31be219da4e27db1ab03"; TREE="7168de556608115be3b7e16b9ceb30b977df904b"
BRANCH="codex/slskdn-oidc-tooltip-localization-20261030"
INV_SHA="17cb8a747939d4973733016b95f29284e191d5444910051e42fb153cf4f94225"
KEY_ORDER_SHA="3ca04c40ebfed00b93fcd143109fc9d85da941cec30b6cb93f52e431498df6a7"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
def sha(b): return hashlib.sha256(b if isinstance(b,bytes) else b.encode()).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def j(p): return json.loads(p.read_text(encoding="utf-8"))
def jl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def git(*args): return subprocess.check_output(["git","-C",str(REPO),*args],text=True).strip()
def blob(p): return subprocess.check_output(["git","-C",str(REPO),"hash-object",str(p)],text=True).strip()
def ph(s): return sorted(set(re.findall(r"\{[^{}]+\}",s)))
def tags(s): return sorted(re.findall(r"</?[A-Za-z][^>]*>",s))
def nums(s): return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)
def prot(s):
 found=set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])",s))
 for x in ("Wishlist","Soulseek","Discogs","Pod"):
  if re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",s): found.add(x)
 return sorted(found)
def quoted(s): return ["'"+s.replace("\\","\\\\").replace("'","\\'")+"'",'"'+s.replace("\\","\\\\").replace('"','\\"')+'"']
def run(args): return subprocess.check_output(args,text=True).strip()
def scan(source):
 found=[]; exts={".js",".jsx",".ts",".tsx"}
 for p in sorted((REPO/"src/web/src").rglob("*")):
  if not p.is_file() or p.suffix.lower() not in exts: continue
  rel=p.relative_to(REPO).as_posix().lower()
  if any(x in rel for x in (".test.",".spec.","/__tests__/","/tests/")): continue
  raw=p.read_bytes()
  try: lines=raw.decode("utf-8").splitlines()
  except UnicodeDecodeError: continue
  for i,line in enumerate(lines):
   if not any(form in line for form in quoted(source)): continue
   ctx=[{"line":n+1,"text":lines[n]} for n in range(max(0,i-3),min(len(lines),i+4))]
   found.append({"path":p.relative_to(REPO).as_posix(),"line":i+1,"lineText":line,"lineSha256":sha(line.encode()),"context":ctx,"contextSha256":sha(canon(ctx)),"fileBytes":len(raw),"fileSha256":sha(raw),"gitBlob":blob(p)})
 return sorted(found,key=lambda x:(x["path"],x["line"]))
def require(x,msg):
 if not x: raise SystemExit("FAIL: "+msg)

subprocess.run(["sha256sum","-c","PACKET-SHA256SUMS.txt"],cwd=I,check=True,capture_output=True,text=True)
m=j(I/"manifest.json"); att=j(I/"head-tree-attestation.json"); sel=j(I/"selection-and-boundary.json")
require((m["repository"],m["pullRequest"],m["branch"],m["head"],m["tree"],m["continuationRankRange"],m["remainingQueueRankRange"])==("snapetech-org/slskdN",409,BRANCH,HEAD,TREE,[628,652],[528,552]),"manifest exact head/window")
require(m["candidateFree"] is True and sel["candidateFree"] is True,"candidate-free marker")
listed={x["path"]:x for x in m["files"]}; actual={p.name for p in I.iterdir() if p.is_file() and p.name not in {"manifest.json","PACKET-SHA256SUMS.txt"}}
require(set(listed)==actual,"manifest file set")
for name,x in listed.items():
 b=(I/name).read_bytes(); require(len(b)==x["bytes"] and sha(b)==x["sha256"],"manifest file hash/size: "+name)
require((git("rev-parse","HEAD"),git("rev-parse","HEAD^{tree}"),git("status","--porcelain=v1"))==(HEAD,TREE,""),"clean exact-head checkout")
pr=json.loads(run(["gh","api","repos/snapetech-org/slskdN/pulls/409"]))
require(pr["state"]=="open" and pr["draft"] is True and pr["head"]["sha"]==HEAD and pr["head"]["ref"]==BRANCH and pr["head"]["repo"]["full_name"]=="snapetech-org/slskdN","live PR state/head")
refs=run(["git","-C",str(REPO),"ls-remote","origin",f"refs/heads/{BRANCH}","refs/pull/409/head"]).splitlines(); rm={x.split()[1]:x.split()[0] for x in refs}
require(rm.get(f"refs/heads/{BRANCH}")==HEAD and rm.get("refs/pull/409/head")==HEAD,"live branch and pull refs")
inv_raw=(I/"source-inventory-pinned.jsonl").read_bytes(); require(sha(inv_raw)==INV_SHA==m["sourceInventorySha256"],"pinned source inventory hash")
inventory=[json.loads(x) for x in inv_raw.decode().splitlines() if x]; require(len(inventory)==6176,"pinned inventory row count")
eligible=[r for r in inventory if not r["excluded"] and not r["inW49"] and r["localeCoverage"]==12]
want=[r for r in eligible if 628<=r["continuationRank"]<=652]; require(len(want)==25,"queue window source count")
selected=jl(I/"source-inventory-selection.jsonl"); require(selected==want,"selected sources equal deterministic inventory ranks")
require([r["remainingQueueRank"] for r in selected]==list(range(528,553)),"remaining queue ranks")
prev=next(r for r in eligible if r["continuationRank"]==627); nxt=next(r for r in eligible if r["continuationRank"]==653)
require((prev["sourceId"],nxt["sourceId"])==("src_27df4fc0d90249cf","src_2919fe8558c441c9"),"exact prior and next boundaries")
require(sel["previousWindowFinalContinuationRank"]==627 and sel["previousWindowFinalSourceId"]==prev["sourceId"] and sel["nextUnselectedContinuationRank"]==653 and sel["nextUnselectedSourceId"]==nxt["sourceId"],"boundary manifest")
prior=[]
for r in inventory:
 if r["excluded"]: prior.append({"sourceId":r["sourceId"],"source":r["source"],"sourceSha256":r["sourceSha256"],"selectionOrigin":"preexisting W1-W45 evidence-set exclusion","continuationRank":None,"remainingQueueRank":None,"excluded":True,"exclusionOrigins":r["exclusionOrigins"]})
 elif r["inW49"]: prior.append({"sourceId":r["sourceId"],"source":r["source"],"sourceSha256":r["sourceSha256"],"selectionOrigin":"W49","continuationRank":None,"remainingQueueRank":None})
 elif r["localeCoverage"]==12 and r["continuationRank"] is not None and r["continuationRank"]<628: prior.append({"sourceId":r["sourceId"],"source":r["source"],"sourceSha256":r["sourceSha256"],"selectionOrigin":"prior continuation window","continuationRank":r["continuationRank"],"remainingQueueRank":r["remainingQueueRank"]})
require(len(prior)==1732 and jl(I/"prior-selected-id-exclusions.jsonl")==prior,"all prior/excluded IDs and no gaps")
struct=jl(I/"catalog-structure.jsonl"); require(len(struct)==12,"catalog structure count")
catalogs={}; sm={x["locale"]:x for x in struct}
for loc in LOCALES:
 rel=f"src/web/public/locales/{loc}.json"; p=REPO/rel; raw=p.read_bytes(); data=json.loads(raw); keys=list(data); kh=sha(("\n".join(keys)+"\n").encode()); s=sm[loc]
 require(len(keys)==6176 and kh==KEY_ORDER_SHA and s["orderedKeySha256"]==kh,"catalog key order "+loc)
 require((s["catalogPath"],s["bytes"],s["sha256"],s["gitBlob"],s["entryCount"])==(rel,len(raw),sha(raw),blob(p),len(data)),"catalog pin "+loc)
 catalogs[loc]=data
contexts=jl(I/"caller-contexts.jsonl"); require(len(contexts)==25,"caller context count")
cm={x["sourceId"]:x for x in contexts}; require(len(cm)==25,"caller context unique IDs")
cells=jl(I/"source-current-cells.jsonl"); require(len(cells)==300,"cell count")
source_rows={r["sourceId"]:r for r in selected}; seen=set(); base=Counter()
for c in cells:
 key=(c["continuationRank"],c["locale"]); require(key not in seen,"duplicate cell"); seen.add(key)
 src=source_rows[c["sourceId"]]; loc=c["locale"]; target=catalogs[loc][src["source"]]
 require(c["source"]==src["source"] and c["sourceSha256"]==src["sourceSha256"]==sha(src["source"].encode()),"source pin")
 require(c["currentTarget"]==target and c["currentTargetSha256"]==sha(target.encode()),"current target preimage")
 require((c["catalogFileSha256"],c["catalogGitBlob"])==(sm[loc]["sha256"],sm[loc]["gitBlob"]),"catalog cell pin")
 base["placeholder"]+=ph(src["source"])!=ph(target); base["markup"]+=tags(src["source"])!=tags(target); base["numeric"]+=nums(src["source"])!=nums(target); base["protectedLiteral"]+=not all(x in target for x in prot(src["source"]))
 require(c["containsCandidate"] is False and c["verdict"] is None,"cell must be candidate-free")
require(seen=={(r["continuationRank"],loc) for r in selected for loc in LOCALES},"all source-locale cells")
require(dict(base)==m["baselineTokenMismatchSummary"],"baseline token mismatch summary")
for x in contexts:
 actual=scan(x["source"])
 require(actual==x["callers"] and x["productionCallerCount"]==len(actual),"exact quoted caller scan "+str(x["continuationRank"]))
 require(x["sourceId"] in source_rows and x["sourceSha256"]==source_rows[x["sourceId"]]["sourceSha256"],"caller source pin")
holds=jl(I/"prior-held-cell-reattestation.jsonl"); require(len(holds)==140,"carried holds count")
require(len({(x["sourceId"],x["locale"]) for x in holds})==140,"unique carried hold cells")
for h in holds:
 current=catalogs[h["locale"]][h["source"]]; cs=scan(h["source"])
 require(sha(current.encode())==h["priorTargetSha256"]==h["currentTargetSha256"] and h["matchesPriorCurrentValue"],"held target exact hash")
 require(len(cs)==h["currentCallerCount"] and h["currentCatalogFileSha256"]==sm[h["locale"]]["sha256"],"held context/catalog repin")
 require(h["status"]=="reattested-unchanged","hold disposition")
ps=j(I/"prior-held-cell-reattestation-summary.json")
require(ps["priorHeldCellsReattested"]==140 and ps["preW69Holds"]==128 and ps["w69Holds"]==12 and ps["allTargetHashesMatchPrior"] and ps["allCurrentCallerAndCatalogEvidenceRepinned"],"hold summary")
require(att["headRefOid"]==HEAD and att["treeOid"]==TREE and att["branchRefOid"]==HEAD and att["pullRefOid"]==HEAD and att["checkoutClean"],"attestation")
print(json.dumps({"pass":True,"head":HEAD,"tree":TREE,"pr":"OPEN/DRAFT","sources":25,"cells":300,"ranks":[628,652],"remainingQueueRanks":[528,552],"nextBoundary":{"rank":653,"sourceId":nxt["sourceId"]},"priorIds":1732,"carriedHolds":140,"callerContexts":sum(x["productionCallerCount"] for x in contexts),"baselineTokenMismatches":dict(base)},ensure_ascii=False,indent=2))
