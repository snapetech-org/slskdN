#!/usr/bin/env python3
import hashlib, json, re, subprocess, sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

TASK=Path(__file__).resolve().parent
OUT=TASK/"input"
REPO=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w69-apply-20261103/repo")
W69_INPUT=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w69-ranks603-627-candidate-free-20261103/input")
W69_PRIMARY=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w69-ranks603-627-primary-20261103/primary-review")
HEAD_EXPECTED="335a96a9ec125b30c20c31be219da4e27db1ab03"
TREE_EXPECTED="7168de556608115be3b7e16b9ceb30b977df904b"
BRANCH="codex/slskdn-oidc-tooltip-localization-20261030"
INV_REL=Path("docs/pr-evidence/pr409-localization-2026-11-03/window49/primary/source-inventory.jsonl")
INV_SHA_EXPECTED="17cb8a747939d4973733016b95f29284e191d5444910051e42fb153cf4f94225"
KEY_ORDER_SHA="3ca04c40ebfed00b93fcd143109fc9d85da941cec30b6cb93f52e431498df6a7"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
RANKS=list(range(628,653))

def sha(b): return hashlib.sha256(b).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def dumpj(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def dumpjl(p,rows): p.write_text("".join(json.dumps(r,ensure_ascii=False,separators=(",",":"))+"\n" for r in rows),encoding="utf-8")
def jl(p): return [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s.strip()]
def git(*args): return subprocess.check_output(["git","-C",str(REPO),*args],text=True).strip()
def blob(p): return subprocess.check_output(["git","-C",str(REPO),"hash-object",str(p)],text=True).strip()
def ph(s): return sorted(set(re.findall(r"\{[^{}]+\}",s)))
def tags(s): return sorted(re.findall(r"</?[A-Za-z][^>]*>",s))
def nums(s): return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)
def prot(s):
    found=set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])",s))
    for literal in ("Wishlist","Soulseek","Discogs","Pod"):
        if re.search(r"(?<![A-Za-z0-9])"+re.escape(literal)+r"(?![A-Za-z0-9])",s): found.add(literal)
    return sorted(found)
def quoted(s): return ["'"+s.replace("\\","\\\\").replace("'","\\'")+"'", '"'+s.replace("\\","\\\\").replace('"','\\"')+'"']
def run(cmd): return subprocess.check_output(cmd,text=True).strip()
def verify_sums(path, name):
    subprocess.check_output(["sha256sum","-c",name],cwd=path,text=True)
@lru_cache(maxsize=None)
def scan(source):
    found=[]; exts={".js",".jsx",".ts",".tsx"}
    for p in sorted((REPO/"src/web/src").rglob("*")):
        if not p.is_file() or p.suffix.lower() not in exts: continue
        rel=p.relative_to(REPO).as_posix().lower()
        if any(x in rel for x in (".test.",".spec.","/__tests__/","/tests/")): continue
        raw=p.read_bytes()
        try: lines=raw.decode("utf-8").splitlines()
        except UnicodeDecodeError: continue
        forms=quoted(source)
        for i,line in enumerate(lines):
            if not any(form in line for form in forms): continue
            ctx=[{"line":n+1,"text":lines[n]} for n in range(max(0,i-3),min(len(lines),i+4))]
            found.append({"path":p.relative_to(REPO).as_posix(),"line":i+1,"lineText":line,
              "lineSha256":sha(line.encode()),"context":ctx,"contextSha256":sha(canon(ctx)),
              "fileBytes":len(raw),"fileSha256":sha(raw),"gitBlob":blob(p)})
    return sorted(found,key=lambda x:(x["path"],x["line"]))

def check_live(expected_head):
    head=git("rev-parse","HEAD"); tree=git("rev-parse","HEAD^{tree}"); status=git("status","--porcelain=v1")
    if (head,tree,status)!=(expected_head,TREE_EXPECTED,""): raise SystemExit(f"checkout pin/cleanliness mismatch: {head} {tree} {status!r}")
    pr=json.loads(run(["gh","api","repos/snapetech-org/slskdN/pulls/409"]))
    if pr["state"]!="open" or pr["draft"] is not True or pr["head"]["sha"]!=head or pr["head"]["ref"]!=BRANCH or pr["head"]["repo"]["full_name"]!="snapetech-org/slskdN": raise SystemExit("live PR state/head/branch/repository changed")
    refs=subprocess.check_output(["git","-C",str(REPO),"ls-remote","origin",f"refs/heads/{BRANCH}","refs/pull/409/head"],text=True).splitlines()
    refmap={line.split()[1]:line.split()[0] for line in refs}
    if refmap.get(f"refs/heads/{BRANCH}")!=head or refmap.get("refs/pull/409/head")!=head: raise SystemExit("live branch/pull refs differ from checkout")
    return head,tree,pr,refmap

if OUT.exists() and any(OUT.iterdir()): raise SystemExit(f"refusing to overwrite {OUT}")
if not W69_INPUT.is_dir() or not W69_PRIMARY.is_dir(): raise SystemExit("prior W69 input/primary evidence missing")
verify_sums(W69_INPUT,"PACKET-SHA256SUMS.txt")
verify_sums(W69_PRIMARY,"SHA256SUMS.txt")
# The historical W69 verifier is expected to reject its old head after W69 was applied; its artifact checksums above are independently verified.
old_boundary=json.loads((W69_INPUT/"selection-and-boundary.json").read_text())
if old_boundary.get("head")!="9ef252a53d2c14201c736de41efd0531bc00965a" or old_boundary.get("nextUnselectedContinuationRank")!=628 or old_boundary.get("nextUnselectedSourceId")!="src_27f3ec760e95a097": raise SystemExit("W69 prior boundary evidence mismatch")
head,tree,pr,refmap=check_live(HEAD_EXPECTED)
inv_path=REPO/INV_REL; inv_raw=inv_path.read_bytes(); inv_sha=sha(inv_raw)
if inv_sha!=INV_SHA_EXPECTED: raise SystemExit("W49 source inventory SHA changed")
inventory=jl(inv_path)
if len(inventory)!=6176: raise SystemExit("source inventory row count changed")
eligible=[r for r in inventory if not r["excluded"] and not r["inW49"] and r["localeCoverage"]==12]
selected=[r for r in eligible if r["continuationRank"] in RANKS]
if len(selected)!=25 or [r["continuationRank"] for r in selected]!=RANKS: raise SystemExit("W70 next source window is not ranks 628-652")
if [r["remainingQueueRank"] for r in selected]!=list(range(528,553)): raise SystemExit("W70 remaining queue ranks do not match 528-552")
prev=next(r for r in eligible if r["continuationRank"]==627)
nxt=next(r for r in eligible if r["continuationRank"]==653)
if prev["sourceId"]!="src_27df4fc0d90249cf" or nxt["sourceId"]!="src_2919fe8558c441c9": raise SystemExit("W70 queue boundaries do not match pinned inventory")
prior_ids=[]
for r in inventory:
    if r["excluded"]:
        prior_ids.append({"sourceId":r["sourceId"],"source":r["source"],"sourceSha256":r["sourceSha256"],"selectionOrigin":"preexisting W1-W45 evidence-set exclusion","continuationRank":None,"remainingQueueRank":None,"excluded":True,"exclusionOrigins":r["exclusionOrigins"]})
    elif r["inW49"]:
        prior_ids.append({"sourceId":r["sourceId"],"source":r["source"],"sourceSha256":r["sourceSha256"],"selectionOrigin":"W49","continuationRank":None,"remainingQueueRank":None})
    elif r["localeCoverage"]==12 and r["continuationRank"] is not None and r["continuationRank"]<628:
        prior_ids.append({"sourceId":r["sourceId"],"source":r["source"],"sourceSha256":r["sourceSha256"],"selectionOrigin":"prior continuation window","continuationRank":r["continuationRank"],"remainingQueueRank":r["remainingQueueRank"]})
if len(prior_ids)!=1732 or len({r["sourceId"] for r in prior_ids})!=1732: raise SystemExit(f"prior/excluded ID accounting mismatch: {len(prior_ids)}")
if {r["sourceId"] for r in prior_ids}.intersection({r["sourceId"] for r in selected}): raise SystemExit("W70 overlaps prior IDs")
# Pin all 12 ordered catalogs at the exact live head.
catalogs={}; structure=[]
for locale in LOCALES:
    rel=Path(f"src/web/public/locales/{locale}.json"); p=REPO/rel; raw=p.read_bytes(); data=json.loads(raw); keys=list(data)
    key_hash=sha(("\n".join(keys)+"\n").encode())
    if len(keys)!=6176 or key_hash!=KEY_ORDER_SHA or any(not isinstance(v,str) or not v for v in data.values()): raise SystemExit(f"catalog structure/order mismatch: {locale}")
    catalogs[locale]=data
    structure.append({"locale":locale,"catalogPath":rel.as_posix(),"bytes":len(raw),"sha256":sha(raw),"gitBlob":blob(p),"entryCount":len(data),"nonemptyValueCount":sum(bool(v) for v in data.values()),"orderedKeySha256":key_hash})
# Source inventory rows are pinned against current catalog keys and hashes.
for src in selected:
    if not src["source"] or sha(src["source"].encode())!=src["sourceSha256"]: raise SystemExit(f"source text hash mismatch: {src['sourceId']}")
    if any(src["source"] not in catalogs[loc] for loc in LOCALES): raise SystemExit(f"selected source key missing: {src['sourceId']}")
caller_map={}; callers=[]
for src in selected:
    cs=scan(src["source"]); caller_map[src["sourceId"]]=cs
    callers.append({"continuationRank":src["continuationRank"],"remainingQueueRank":src["remainingQueueRank"],"sourceId":src["sourceId"],"source":src["source"],"sourceSha256":src["sourceSha256"],"productionCallerCount":len(cs),"boundedScan":"exact quoted-literal search in pinned src/web/src JavaScript/TypeScript production files; test/spec files excluded","callers":cs})
cells=[]
for src in selected:
    cs=caller_map[src["sourceId"]]; ctxsha=sha(canon([c["context"] for c in cs]))
    for locale in LOCALES:
        target=catalogs[locale].get(src["source"])
        if not isinstance(target,str): raise SystemExit(f"missing target for {src['sourceId']} {locale}")
        strow=next(x for x in structure if x["locale"]==locale)
        cells.append({"continuationRank":src["continuationRank"],"remainingQueueRank":src["remainingQueueRank"],"sourceId":src["sourceId"],"source":src["source"],"catalogKey":src["source"],"sourceSha256":src["sourceSha256"],"locale":locale,"catalogPath":strow["catalogPath"],"catalogFileSha256":strow["sha256"],"catalogGitBlob":strow["gitBlob"],"currentTarget":target,"currentTargetSha256":sha(target.encode()),"callerContextSha256":ctxsha,"callerRefs":[{"path":c["path"],"line":c["line"],"lineSha256":c["lineSha256"],"fileSha256":c["fileSha256"],"gitBlob":c["gitBlob"]} for c in cs],"placeholderEvidence":{"sourceTokens":ph(src["source"]),"currentTokens":ph(target),"matches":ph(src["source"])==ph(target)},"markupEvidence":{"sourceTags":tags(src["source"]),"currentTags":tags(target),"matches":tags(src["source"])==tags(target)},"sourceNumericTokens":nums(src["source"]),"currentNumericTokens":nums(target),"sourceProtectedLiterals":prot(src["source"]),"currentProtectedLiterals":prot(target),"protectedLiteralEvidence":{"sourceTokens":prot(src["source"]),"currentTokens":prot(target),"matches":all(x in target for x in prot(src["source"]))},"containsCandidate":False,"verdict":None})
# Reattest every previously carried hold: 128 pre-W69 cells plus W69 rank-615 holds.
old_holds=jl(W69_INPUT/"prior-held-cell-reattestation.jsonl")
if len(old_holds)!=128: raise SystemExit("W69 prior-hold ledger should contain 128 carried cells")
w69_rows=jl(W69_PRIMARY/"primary-ledger.jsonl")
new_holds=[r for r in w69_rows if r.get("disposition")=="hold"]
if len(w69_rows)!=300 or len(new_holds)!=12 or {r["continuationRank"] for r in new_holds}!={615}: raise SystemExit("W69 primary hold lineage mismatch")
prior=[]
def repin(item, prior_sha, reason, prior_window, old_caller_count=None, prior_evidence=""):
    source=item["source"]; sid=item["sourceId"]; locale=item["locale"]
    current=catalogs[locale].get(source)
    if not isinstance(current,str): raise SystemExit(f"prior held key missing {sid} {locale}")
    current_sha=sha(current.encode())
    if current_sha!=prior_sha: raise SystemExit(f"prior held value changed: {sid} {locale}")
    cs=scan(source)
    if old_caller_count is not None and old_caller_count!=len(cs): raise SystemExit(f"prior held caller count changed: {sid} {locale}")
    row=next(x for x in structure if x["locale"]==locale)
    prior.append({"priorWindow":prior_window,"continuationRank":item["continuationRank"],"sourceId":sid,"source":source,"sourceSha256":item["sourceSha256"],"locale":locale,"priorDisposition":"hold","priorTargetSha256":prior_sha,"currentTarget":current,"currentTargetSha256":current_sha,"matchesPriorCurrentValue":current_sha==prior_sha,"priorCallerCount":old_caller_count,"currentCallerCount":len(cs),"currentCallerRefs":[{"path":c["path"],"line":c["line"],"lineSha256":c["lineSha256"],"fileSha256":c["fileSha256"],"gitBlob":c["gitBlob"]} for c in cs],"currentCallerContextSha256":sha(canon([c["context"] for c in cs])),"currentCatalogPath":row["catalogPath"],"currentCatalogFileSha256":row["sha256"],"currentCatalogGitBlob":row["gitBlob"],"holdReason":reason,"priorEvidenceSource":prior_evidence,"status":"reattested-unchanged"})
for old in old_holds:
    item={"continuationRank":old["continuationRank"],"sourceId":old["sourceId"],"source":old["source"],"sourceSha256":old["sourceSha256"],"locale":old["locale"]}
    repin(item,old["priorTargetSha256"],old["holdReason"],old["priorWindow"],old.get("currentCallerCount"),"W69 candidate-free prior-held-cell-reattestation.jsonl")
for old in new_holds:
    item={"continuationRank":old["continuationRank"],"sourceId":old["sourceId"],"source":old["source"],"sourceSha256":old["sourceSha256"],"locale":old["locale"]}
    repin(item,old["currentTargetSha256"],old["rationale"],"W69",len(old["callerContexts"]),"W69 primary-review/primary-ledger.jsonl")
if len(prior)!=140 or not all(r["matchesPriorCurrentValue"] for r in prior): raise SystemExit("expected all 140 carried holds to reattest unchanged")
# Record exact prior boundary and current window selection.
boundary=[{"boundaryRole":"previous-window-final",**prev}]
boundary += [{"boundaryRole":"selected",**r} for r in selected]
boundary += [{"boundaryRole":"next-unselected",**nxt}]
# Live PR/refs must still match after all source, catalog, caller, and hold evidence was captured.
head2,tree2,pr2,refs2=check_live(HEAD_EXPECTED)
if (head2,tree2)!=(head,tree): raise SystemExit("live head/tree changed during extraction")
OUT.mkdir(parents=True,exist_ok=True)
# Preserve the pinned source inventory so deterministic ranking can be checked without a mutable external copy.
(OUT/"source-inventory-pinned.jsonl").write_bytes(inv_raw)
dumpjl(OUT/"source-inventory-selection.jsonl",selected)
dumpjl(OUT/"prior-selected-id-exclusions.jsonl",prior_ids)
dumpjl(OUT/"selection-boundary.jsonl",boundary)
dumpj(OUT/"selection-and-boundary.json",{"repository":"snapetech-org/slskdN","pullRequest":409,"state":"OPEN","draft":True,"branch":BRANCH,"head":head,"tree":tree,"previousWindow":"W69","previousWindowFinalContinuationRank":627,"previousWindowFinalSourceId":prev["sourceId"],"priorBoundaryEvidence":"W69 candidate-free input selection-and-boundary.json, live exact head 335a96a9; W49 source-inventory pinned by SHA-256","sourceInventoryPath":INV_REL.as_posix(),"sourceInventorySha256":inv_sha,"sourceInventoryRows":len(inventory),"selection":{"window":"W70","continuationRankStart":628,"continuationRankEnd":652,"remainingQueueRankStart":528,"remainingQueueRankEnd":552,"sourceCount":25,"localeCount":12,"cellCount":300},"nextUnselectedContinuationRank":653,"nextUnselectedSourceId":nxt["sourceId"],"priorSelectedIdsExcluded":{"preexistingW1W45ExcludedRows":sum(r["selectionOrigin"]=="preexisting W1-W45 evidence-set exclusion" for r in prior_ids),"w49":sum(r["selectionOrigin"]=="W49" for r in prior_ids),"priorContinuationQueue":sum(r["selectionOrigin"]=="prior continuation window" for r in prior_ids),"totalUnavailableIds":len(prior_ids),"selectionRule":"Pinned W49 inventory excludes all excluded=true and inW49=true rows; continuation IDs through rank 627 are excluded; select the immediate next ranks 628-652."},"orderedCatalogKeySha256":KEY_ORDER_SHA,"catalogEntryCountPerLocale":6176,"locales":LOCALES,"candidateFree":True})
dumpjl(OUT/"caller-contexts.jsonl",callers)
dumpjl(OUT/"catalog-structure.jsonl",structure)
dumpjl(OUT/"source-current-cells.jsonl",cells)
dumpjl(OUT/"prior-held-cell-reattestation.jsonl",prior)
dumpj(OUT/"prior-held-cell-reattestation-summary.json",{"expectedHeldCells":140,"priorHeldCellsReattested":len(prior),"preW69Holds":len(old_holds),"w69Holds":len(new_holds),"allTargetHashesMatchPrior":all(r["matchesPriorCurrentValue"] for r in prior),"allCurrentCallerAndCatalogEvidenceRepinned":True})
dumpj(OUT/"head-tree-attestation.json",{"repository":"snapetech-org/slskdN","pullRequest":409,"state":"OPEN","draft":True,"baseRefName":pr2["base"]["ref"],"headRefName":BRANCH,"headRefOid":head,"treeOid":tree,"branchRefOid":refs2[f"refs/heads/{BRANCH}"],"pullRefOid":refs2["refs/pull/409/head"],"attestedAtUtc":datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),"checkoutClean":True,"sourceInventorySha256":inv_sha})
if len(cells)!=300 or any(r["containsCandidate"] is not False or r["verdict"] is not None for r in cells): raise SystemExit("candidate-free cell invariant failed")
if len({r["sourceId"] for r in selected})!=25 or len({r["sourceId"] for r in prior_ids})!=1732: raise SystemExit("source ID uniqueness failed")
mismatches={"placeholder":0,"markup":0,"numeric":0,"protectedLiteral":0}
for r in cells:
    mismatches["placeholder"]+=int(not r["placeholderEvidence"]["matches"])
    mismatches["markup"]+=int(not r["markupEvidence"]["matches"])
    mismatches["numeric"]+=int(r["sourceNumericTokens"]!=r["currentNumericTokens"])
    mismatches["protectedLiteral"]+=int(not r["protectedLiteralEvidence"]["matches"])
dumpj(OUT/"baseline-token-mismatch-summary.json",{"cellCount":300,"mismatches":mismatches})
readme=f"""# slskdN PR #409 W70 ranks 628–652 candidate-free input

Live PR #409 was OPEN/DRAFT at branch {BRANCH}; branch and pull refs matched exact head {head}, tree {tree} both before and after extraction. The repository checkout was clean.

The pinned W49 source inventory {INV_REL.as_posix()} has 6,176 rows and SHA-256 {inv_sha}. Rechecking its eligible queue and the W69 recorded next boundary confirms W70 is the immediate 25-source window at continuation ranks 628–652 (remaining-queue ranks 528–552); rank 627 is the previous boundary and rank 653 is next. The packet includes the pinned inventory, selected rows, and 1,732 prior/excluded IDs so the queue order can be checked independently.

All twelve catalog files have 6,176 ordered nonempty entries. The 25 source definitions, 300 current catalog values, exact-literal production caller contexts, catalog blobs, and caller line/file hashes are pinned at {head}. All 140 carried holds were reattested unchanged: 128 earlier holds and 12 W69 callerless rank-615 holds. No candidate proposals or W70 review decisions are present.

The historical W69 live verifier now rejects its original 9ef252a head because W69 was applied; its packet checksums pass, and this W70 input reattests the W69 hold hashes and source boundary against the current exact head.
"""
(OUT/"README.md").write_text(readme,encoding="utf-8")
files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name not in ("manifest.json","PACKET-SHA256SUMS.txt"))
manifest={"schemaVersion":1,"artifact":"slskdN PR #409 W70 ranks 628-652 candidate-free exact-head input","candidateFree":True,"repository":"snapetech-org/slskdN","pullRequest":409,"branch":BRANCH,"head":head,"tree":tree,"sourceCount":25,"localeCount":12,"cellCount":300,"sourceInventoryPath":INV_REL.as_posix(),"sourceInventorySha256":inv_sha,"sourceInventoryRows":len(inventory),"remainingQueueRankRange":[528,552],"continuationRankRange":[628,652],"previousWindow":"W69","nextUnselectedContinuationRank":653,"nextUnselectedSourceId":nxt["sourceId"],"priorSelectedIdsExcluded":len(prior_ids),"priorHeldCellsReattested":len(prior),"priorHoldLineage":{"carriedFromPriorW68":len(old_holds),"addedAndHeldInW69":len(new_holds)},"orderedCatalogKeySha256":KEY_ORDER_SHA,"catalogEntryCountPerLocale":6176,"baselineTokenMismatchSummary":mismatches,"w69LineagePins":{"candidateFreeManifestSha256":sha((W69_INPUT/"manifest.json").read_bytes()),"candidateFreeChecksumsSha256":sha((W69_INPUT/"PACKET-SHA256SUMS.txt").read_bytes()),"primaryManifestSha256":sha((W69_PRIMARY/"manifest.json").read_bytes()),"primaryChecksumsSha256":sha((W69_PRIMARY/"SHA256SUMS.txt").read_bytes()),"primaryLedgerSha256":sha((W69_PRIMARY/"primary-ledger.jsonl").read_bytes())},"locales":LOCALES,"files":[{"path":p.name,"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for p in files]}
dumpj(OUT/"manifest.json",manifest)
files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name!="PACKET-SHA256SUMS.txt")
(OUT/"PACKET-SHA256SUMS.txt").write_text("".join(f"{sha(p.read_bytes())}  {p.name}\n" for p in files),encoding="utf-8")
print(json.dumps({"built":True,"output":str(OUT),"head":head,"tree":tree,"sources":25,"cells":len(cells),"priorIds":len(prior_ids),"priorHolds":len(prior),"selectedRanks":[RANKS[0],RANKS[-1]],"remainingQueueRanks":[528,552],"nextBoundary":{"rank":653,"sourceId":nxt["sourceId"]},"baselineTokenMismatches":mismatches,"sourceInventorySha256":inv_sha},ensure_ascii=False,indent=2))
