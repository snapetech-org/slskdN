#!/usr/bin/env python3
import hashlib, json, re, subprocess
from functools import lru_cache
from pathlib import Path
I=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w68-ranks578-602-candidate-free-20261103/input")
REPO=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w68-apply-20261103/repo")
W67I=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w67-ranks553-577-candidate-free-20261103/input")
W67X=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w67-cross-audit-20261103")
HEAD="973a65312a475de4d8aa39aee837249553fd884e"
TREE="2a7b200dd1fe96f894bfdb663f656d6ffd48f487"
BRANCH="codex/slskdn-oidc-tooltip-localization-20261030"
INV_REL=Path("docs/pr-evidence/pr409-localization-2026-11-03/window49/primary/source-inventory.jsonl")
INV_SHA="17cb8a747939d4973733016b95f29284e191d5444910051e42fb153cf4f94225"
KEY_SHA="3ca04c40ebfed00b93fcd143109fc9d85da941cec30b6cb93f52e431498df6a7"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
def sha(b): return hashlib.sha256(b).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def j(p): return json.loads(p.read_text(encoding="utf-8"))
def jl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def git(*a): return subprocess.check_output(["git","-C",str(REPO),*a],text=True).strip()
def quoted(s):
 b=chr(92); q=chr(39); d=chr(34)
 return [q+s.replace(b,b+b).replace(q,b+q)+q,d+s.replace(b,b+b).replace(d,b+d)+d]
def ph(s): return sorted(set(re.findall(r"\{[^{}]+\}",s)))
def tags(s): return sorted(re.findall(r"</?[A-Za-z][^>]*>",s))
def nums(s): return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)
def prot(s):
 f=set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])",s))
 for x in ("Wishlist","Soulseek","Discogs","Pod"):
  if re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",s): f.add(x)
 return sorted(f)
@lru_cache(maxsize=None)
def scan(source):
 out=[]; forms=quoted(source)
 for p in sorted((REPO/"src/web/src").rglob("*")):
  if not p.is_file() or p.suffix.lower() not in {".js",".jsx",".ts",".tsx"}: continue
  rel=p.relative_to(REPO).as_posix().lower()
  if any(x in rel for x in (".test.",".spec.","/__tests__/","/tests/")): continue
  raw=p.read_bytes()
  try: lines=raw.decode("utf-8").splitlines()
  except UnicodeDecodeError: continue
  for i,line in enumerate(lines):
   if not any(q in line for q in forms): continue
   ctx=[{"line":n+1,"text":lines[n]} for n in range(max(0,i-3),min(len(lines),i+4))]
   out.append({"path":p.relative_to(REPO).as_posix(),"line":i+1,"lineText":line,"lineSha256":sha(line.encode()),"context":ctx,"contextSha256":sha(canon(ctx)),"fileBytes":len(raw),"fileSha256":sha(raw),"gitBlob":git("hash-object",str(p))})
 return sorted(out,key=lambda x:(x["path"],x["line"]))
def verify_sums(folder,name):
 n=0
 for line in (folder/name).read_text(encoding="utf-8").splitlines():
  if line.strip():
   digest,rel=line.split(None,1); p=folder/rel.strip().lstrip("*")
   if not p.is_file() or sha(p.read_bytes())!=digest: raise ValueError("checksum mismatch "+str(p))
   n+=1
 return n
m=j(I/"manifest.json")
if m.get("candidateFree") is not True or (m.get("head"),m.get("tree"))!=(HEAD,TREE): raise ValueError("candidate-free manifest pin")
if m.get("continuationRankRange")!=[578,602] or m.get("remainingQueueRankRange")!=[478,502] or m.get("sourceCount")!=25 or m.get("cellCount")!=300: raise ValueError("window manifest coverage")
if m.get("priorSelectedIdsExcluded")!=1682 or m.get("priorHeldCellsReattested")!=128: raise ValueError("lineage counts")
if m.get("sourceInventorySha256")!=INV_SHA or m.get("sourceInventoryRows")!=6176 or m.get("locales")!=LOCALES: raise ValueError("source inventory or locale pin")
for folder,name in [(W67I,"PACKET-SHA256SUMS.txt"),(W67X,"SHA256SUMS.txt")]: verify_sums(folder,name)
old_manifest=j(W67I/"manifest.json"); old_cross=j(W67X/"manifest.json")
if old_manifest.get("head")!=old_cross.get("head") or old_manifest.get("tree")!=old_cross.get("tree") or not str(old_cross.get("window","")).startswith("W67 "): raise ValueError("W67 lineage packet mismatch")
lineage=m["priorLineagePins"]
if lineage["W67CandidateFreeChecksumsSha256"]!=sha((W67I/"PACKET-SHA256SUMS.txt").read_bytes()) or lineage["W67CrossAuditManifestSha256"]!=sha((W67X/"manifest.json").read_bytes()) or lineage["W67CrossAuditChecksumsSha256"]!=sha((W67X/"SHA256SUMS.txt").read_bytes()): raise ValueError("W67 lineage pin mismatch")
verify_sums(I,"PACKET-SHA256SUMS.txt")
files={r["path"]:r for r in m["files"]}
actual={p.name for p in I.iterdir() if p.is_file() and p.name not in {"manifest.json","PACKET-SHA256SUMS.txt"}}
if set(files)!=actual: raise ValueError("manifest file set")
for name,r in files.items():
 p=I/name
 if p.stat().st_size!=r["bytes"] or sha(p.read_bytes())!=r["sha256"]: raise ValueError("manifest file hash "+name)
head=git("rev-parse","HEAD"); tree=git("rev-parse","HEAD^{tree}"); branch=git("branch","--show-current"); status=git("status","--porcelain=v1")
if (head,tree,status)!=(HEAD,TREE,""): raise ValueError("source checkout state")
pr=json.loads(subprocess.check_output(["gh","api","repos/snapetech-org/slskdN/pulls/409"],text=True))
if pr["state"]!="open" or pr["draft"] is not True or pr["head"]["sha"]!=HEAD or pr["head"]["ref"]!=BRANCH or pr["head"]["repo"]["full_name"]!="snapetech-org/slskdN": raise ValueError("live PR state/head")
refs=subprocess.check_output(["git","-C",str(REPO),"ls-remote","origin",f"refs/heads/{BRANCH}","refs/pull/409/head"],text=True).splitlines()
refmap={x.split()[1]:x.split()[0] for x in refs}
if refmap.get(f"refs/heads/{BRANCH}")!=HEAD or refmap.get("refs/pull/409/head")!=HEAD: raise ValueError("live PR refs")
att=j(I/"head-tree-attestation.json")
if (att["headRefOid"],att["treeOid"],att["branchRefOid"],att["pullRefOid"])!=(HEAD,TREE,HEAD,HEAD): raise ValueError("attestation record")
inv_path=REPO/INV_REL
if sha(inv_path.read_bytes())!=INV_SHA: raise ValueError("source inventory digest")
inv=jl(inv_path)
if len(inv)!=6176: raise ValueError("source inventory row count")
elig=[x for x in inv if not x["excluded"] and not x["inW49"] and x["localeCoverage"]==12]
selected=[x for x in elig if 578<=x["continuationRank"]<=602]
if len(selected)!=25 or [x["continuationRank"] for x in selected]!=list(range(578,603)) or [x["remainingQueueRank"] for x in selected]!=list(range(478,503)): raise ValueError("selected boundary/ranks")
prev=next(x for x in elig if x["continuationRank"]==577); nxt=next(x for x in elig if x["continuationRank"]==603)
boundary=jl(I/"selection-boundary.jsonl")
if len(boundary)!=27 or [(x["boundaryRole"],x["continuationRank"]) for x in boundary]!=[("previous-window-final",577)]+[("selected",n) for n in range(578,603)]+[("next-unselected",603)]: raise ValueError("boundary rows")
if boundary[0]["sourceId"]!=prev["sourceId"] or boundary[-1]["sourceId"]!=nxt["sourceId"]: raise ValueError("boundary source IDs")
for row,src in zip(boundary[1:-1],selected):
 if row["sourceId"]!=src["sourceId"] or row["sourceSha256"]!=src["sourceSha256"]: raise ValueError("selected boundary identity")
selection=jl(I/"source-inventory-selection.jsonl")
if selection!=selected: raise ValueError("selected source rows differ")
prior_ids=jl(I/"prior-selected-id-exclusions.jsonl")
expected_prior=[x for x in inv if x["excluded"] or x["inW49"] or (x["localeCoverage"]==12 and x["continuationRank"] is not None and x["continuationRank"]<578)]
if len(prior_ids)!=1682 or len({x["sourceId"] for x in prior_ids})!=1682 or {x["sourceId"] for x in prior_ids}!={x["sourceId"] for x in expected_prior}: raise ValueError("prior selected ID exclusion set")
if {x["sourceId"] for x in prior_ids}&{x["sourceId"] for x in selected}: raise ValueError("selection overlap")
structure=jl(I/"catalog-structure.jsonl")
if len(structure)!=12: raise ValueError("catalog structure count")
catalogs={}; structs={}
for s in structure:
 loc=s["locale"]; p=REPO/s["catalogPath"]; raw=p.read_bytes(); d=json.loads(raw); keys=list(d)
 if len(d)!=6176 or any(not isinstance(v,str) or not v for v in d.values()) or sha(raw)!=s["sha256"] or git("hash-object",str(p))!=s["gitBlob"]: raise ValueError("catalog file pin "+loc)
 if sha(("\n".join(keys)+"\n").encode())!=KEY_SHA or s["orderedKeySha256"]!=KEY_SHA: raise ValueError("catalog key order "+loc)
 if git("rev-parse", "{}:{}".format(HEAD,s["catalogPath"]))!=s["gitBlob"]: raise ValueError("catalog tree blob "+loc)
 catalogs[loc]=d; structs[loc]=s
contexts=jl(I/"caller-contexts.jsonl"); cells=jl(I/"source-current-cells.jsonl")
if len(contexts)!=25 or len(cells)!=300: raise ValueError("caller/cell counts")
ctx={x["sourceId"]:x for x in contexts}; srcmap={x["sourceId"]:x for x in selected}
if set(ctx)!=set(srcmap): raise ValueError("caller source map")
for src in selected:
 fresh=scan(src["source"]); c=ctx[src["sourceId"]]
 if c["callers"]!=fresh or c["productionCallerCount"]!=len(fresh) or c["sourceSha256"]!=src["sourceSha256"]: raise ValueError("caller evidence "+src["sourceId"])
for src in selected:
 for loc in LOCALES:
  row=next(x for x in cells if x["continuationRank"]==src["continuationRank"] and x["locale"]==loc)
  target=catalogs[loc].get(src["source"])
  fresh=scan(src["source"]); s=structs[loc]
  expected_refs=[{"path":c["path"],"line":c["line"],"lineSha256":c["lineSha256"],"fileSha256":c["fileSha256"],"gitBlob":c["gitBlob"]} for c in fresh]
  if target is None or (row["sourceId"],row["source"],row["sourceSha256"],row["catalogKey"])!=(src["sourceId"],src["source"],src["sourceSha256"],src["source"]): raise ValueError("cell source binding")
  if row["currentTarget"]!=target or row["currentTargetSha256"]!=sha(target.encode()) or row["catalogFileSha256"]!=s["sha256"] or row["catalogGitBlob"]!=s["gitBlob"]: raise ValueError("current catalog cell pin")
  if row["callerContextSha256"]!=sha(canon([x["context"] for x in fresh])) or row["callerRefs"]!=expected_refs: raise ValueError("cell caller pin")
  if row["containsCandidate"] is not False or row["verdict"] is not None: raise ValueError("candidate contamination")
  if row["placeholderEvidence"]!={"sourceTokens":ph(src["source"]),"currentTokens":ph(target),"matches":ph(src["source"])==ph(target)}: raise ValueError("placeholder evidence")
  if row["markupEvidence"]!={"sourceTags":tags(src["source"]),"currentTags":tags(target),"matches":tags(src["source"])==tags(target)}: raise ValueError("markup evidence")
  if row["sourceNumericTokens"]!=nums(src["source"]) or row["currentNumericTokens"]!=nums(target): raise ValueError("numeric evidence")
  if row["sourceProtectedLiterals"]!=prot(src["source"]) or row["currentProtectedLiterals"]!=prot(target) or row["protectedLiteralEvidence"]!={"sourceTokens":prot(src["source"]),"currentTokens":prot(target),"matches":all(x in target for x in prot(src["source"]))}: raise ValueError("protected literal evidence")
# Reattest the 128 prior holds; W67 added none.
old=jl(W67I/"prior-held-cell-reattestation.jsonl")
prev_rows=jl(W67X/"cross-audit-ledger.jsonl")
new=[x for x in prev_rows if x["finalDisposition"]=="hold"]
if len(old)!=128 or len(new)!=0: raise ValueError("W67 hold source set")
prior=jl(I/"prior-held-cell-reattestation.jsonl")
old_keys={(x["continuationRank"],x["locale"],x["sourceId"]):x["priorTargetSha256"] for x in old}
new_keys={(x["continuationRank"],x["locale"],x["sourceId"]):x["resolution"]["selectedTargetSha256"] for x in new}
expected_holds={**old_keys,**new_keys}
prior_keys={(x["continuationRank"],x["locale"],x["sourceId"]):x for x in prior}
if len(prior)!=128 or set(prior_keys)!=set(expected_holds): raise ValueError("prior hold coverage")
for k,exp in expected_holds.items():
 x=prior_keys[k]; target=catalogs[x["locale"]].get(x["source"]); fresh=scan(x["source"]); s=structs[x["locale"]]
 if target is None or sha(target.encode())!=exp or x["priorTargetSha256"]!=exp or x["currentTargetSha256"]!=exp or x["currentTarget"]!=target or x["matchesPriorCurrentValue"] is not True or x["status"]!="reattested-unchanged": raise ValueError("prior hold value changed "+str(k))
 if x["sourceSha256"]!=next(z["sourceSha256"] for z in inv if z["sourceId"]==x["sourceId"]): raise ValueError("prior hold source hash")
 if x["currentCallerCount"]!=len(fresh) or x["currentCallerRefs"]!=[{"path":c["path"],"line":c["line"],"lineSha256":c["lineSha256"],"fileSha256":c["fileSha256"],"gitBlob":c["gitBlob"]} for c in fresh]: raise ValueError("prior hold caller reattestation")
 if x["currentCatalogFileSha256"]!=s["sha256"] or x["currentCatalogGitBlob"]!=s["gitBlob"]: raise ValueError("prior hold catalog pin")
summary=j(I/"baseline-token-mismatch-summary.json")
computed={"placeholder":sum(not x["placeholderEvidence"]["matches"] for x in cells),"markup":sum(not x["markupEvidence"]["matches"] for x in cells),"numeric":sum(x["sourceNumericTokens"]!=x["currentNumericTokens"] for x in cells),"protectedLiteral":sum(not x["protectedLiteralEvidence"]["matches"] for x in cells)}
if summary!={"cellCount":300,"mismatches":computed}: raise ValueError("token mismatch summary")
print(json.dumps({"pass":True,"head":HEAD,"tree":TREE,"sourceCount":25,"cellCount":300,"continuationRanks":[578,602],"remainingQueueRanks":[478,502],"priorSelectedIdsExcluded":len(prior_ids),"priorHoldsReattested":len(prior),"newW67Holds":len(new),"callerlessSelectedSources":[x["continuationRank"] for x in contexts if x["productionCallerCount"]==0],"catalogKeysPerLocale":6176,"catalogKeyOrderSha256":KEY_SHA,"baselineTokenMismatches":computed,"livePR":"PASS","checksums":"PASS"},ensure_ascii=False,indent=2))
