#!/usr/bin/env python3
import hashlib,json,re,subprocess
from pathlib import Path

I=Path(__file__).resolve().parent
REPO=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w65-ranks503-527-primary-20261103/source-checkout")
W65=REPO/"docs/pr-evidence/pr409-localization-2026-11-03/window-503-527"
BRANCH="codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
def sha(b): return hashlib.sha256(b).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def j(p): return json.loads(p.read_text(encoding="utf-8"))
def jl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def git(*a): return subprocess.check_output(["git","-C",str(REPO),*a],text=True).strip()
def quoted(s):
    return ["'"+s.replace("\\","\\\\").replace("'","\\'")+"'", '"'+s.replace("\\","\\\\").replace('"','\\"')+'"']
def ph(s): return sorted(set(re.findall(r"\{[^{}]+\}",s)))
def tags(s): return sorted(re.findall(r"</?[A-Za-z][^>]*>",s))
def nums(s): return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)
def prot(s):
    f=set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])",s))
    for x in ("Wishlist","Soulseek","Discogs","Pod"):
        if re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",s): f.add(x)
    return sorted(f)
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
            out.append({"path":p.relative_to(REPO).as_posix(),"line":i+1,"lineText":line,"lineSha256":sha(line.encode()),
              "context":ctx,"contextSha256":sha(canon(ctx)),"fileBytes":len(raw),"fileSha256":sha(raw),"gitBlob":git("hash-object",str(p))})
    return sorted(out,key=lambda x:(x["path"],x["line"]))
def verify_sums(folder,name):
    for line in (folder/name).read_text().splitlines():
        if not line.strip(): continue
        digest,n=line.split(None,1); n=n.strip().lstrip("*")
        assert sha((folder/n).read_bytes())==digest,(folder/n,"checksum")
manifest=j(I/"manifest.json")
assert manifest["candidateFree"] is True
assert (manifest["repository"],manifest["pullRequest"],manifest["branch"])==("snapetech-org/slskdN",409,BRANCH)
assert (manifest["sourceCount"],manifest["localeCount"],manifest["cellCount"])==(25,12,300)
assert manifest["continuationRankRange"]==[528,552] and manifest["remainingQueueRankRange"]==[428,452]
assert manifest["priorSelectedIdsExcluded"]==1632 and manifest["priorHeldCellsReattested"]==104
assert manifest["locales"]==LOCALES
# Verify packet checksums and the independently sealed W65 evidence used for boundaries/holds.
verify_sums(I,"PACKET-SHA256SUMS.txt")
verify_sums(W65,"SHA256SUMS.txt")
head=git("rev-parse","HEAD"); tree=git("rev-parse","HEAD^{tree}")
assert (head,tree)==(manifest["head"],manifest["tree"])
assert git("branch","--show-current")=="" and git("status","--porcelain=v1")==""
pr=json.loads(subprocess.check_output(["gh","api","repos/snapetech-org/slskdN/pulls/409"],text=True))
assert pr["state"]=="open" and pr["draft"] and pr["head"]["ref"]==BRANCH and pr["head"]["sha"]==head
refs=subprocess.check_output(["git","-C",str(REPO),"ls-remote","origin",f"refs/heads/{BRANCH}","refs/pull/409/head"],text=True).splitlines()
refmap={x.split()[1]:x.split()[0] for x in refs}
assert refmap.get(f"refs/heads/{BRANCH}")==head and refmap.get("refs/pull/409/head")==head
att=j(I/"head-tree-attestation.json")
assert (att["headRefOid"],att["treeOid"],att["branchRefOid"],att["pullRefOid"])==(head,tree,head,head)
# Verify source-inventory ordering, next source boundaries, and exclusions.
inv_path=REPO/"docs/pr-evidence/pr409-localization-2026-11-03/window49/primary/source-inventory.jsonl"
assert sha(inv_path.read_bytes())==manifest["sourceInventorySha256"]
inventory=jl(inv_path); assert len(inventory)==6176
eligible=[x for x in inventory if not x["excluded"] and not x["inW49"] and x["localeCoverage"]==12]
selected=[x for x in eligible if x["continuationRank"] in range(528,553)]
assert len(selected)==25 and [x["continuationRank"] for x in selected]==list(range(528,553))
assert [x["remainingQueueRank"] for x in selected]==list(range(428,453))
prev=next(x for x in eligible if x["continuationRank"]==527)
nxt=next(x for x in eligible if x["continuationRank"]==553)
assert manifest["nextUnselectedContinuationRank"]==553 and manifest["nextUnselectedSourceId"]==nxt["sourceId"]
boundary=jl(I/"selection-boundary.jsonl")
assert len(boundary)==27
assert [(x["boundaryRole"],x["continuationRank"]) for x in boundary]==[("previous-window-final",527)]+[("selected",n) for n in range(528,553)]+[("next-unselected",553)]
assert boundary[0]["sourceId"]==prev["sourceId"] and boundary[-1]["sourceId"]==nxt["sourceId"]
for row,expected in zip(boundary[1:-1],selected): assert row["sourceId"]==expected["sourceId"] and row["sourceSha256"]==expected["sourceSha256"]
prior_ids=jl(I/"prior-selected-id-exclusions.jsonl")
assert len(prior_ids)==1632 and len({x["sourceId"] for x in prior_ids})==1632
assert not ({x["sourceId"] for x in prior_ids}&{x["sourceId"] for x in selected})
sel=jl(I/"source-inventory-selection.jsonl")
assert sel==selected
# Verify exact live catalog blobs, ordered keys, all current target values and each caller occurrence.
structure=jl(I/"catalog-structure.jsonl")
assert len(structure)==12
catalogs={}
for s in structure:
    loc=s["locale"]; path=REPO/s["catalogPath"]; raw=path.read_bytes(); d=json.loads(raw)
    assert len(d)==6176 and sha(raw)==s["sha256"] and git("rev-parse",f"{head}:{s['catalogPath']}")==s["gitBlob"]
    assert git("hash-object",str(path))==s["gitBlob"]
    keys=list(d); assert sha(("\n".join(keys)+"\n").encode())==manifest["orderedCatalogKeySha256"]
    assert s["orderedKeySha256"]==manifest["orderedCatalogKeySha256"]
    catalogs[loc]=d
contexts=jl(I/"caller-contexts.jsonl")
assert len(contexts)==25
cellrows=jl(I/"source-current-cells.jsonl")
assert len(cellrows)==300
expected_keys={(s["continuationRank"],loc) for s in selected for loc in LOCALES}
assert {(x["continuationRank"],x["locale"]) for x in cellrows}==expected_keys
ctxmap={x["continuationRank"]:x for x in contexts}
assert set(ctxmap)==set(range(528,553))
for rank,src in zip(range(528,553),selected):
    fresh=scan(src["source"])
    assert ctxmap[rank]["callers"]==fresh
    assert ctxmap[rank]["productionCallerCount"]==len(fresh)
    for loc in LOCALES:
        x=next(r for r in cellrows if r["continuationRank"]==rank and r["locale"]==loc)
        target=catalogs[loc][src["source"]]
        assert (x["sourceId"],x["source"],x["sourceSha256"],x["catalogKey"])==(src["sourceId"],src["source"],src["sourceSha256"],src["source"])
        assert x["currentTarget"]==target and x["currentTargetSha256"]==sha(target.encode())
        assert x["catalogFileSha256"]==next(y["sha256"] for y in structure if y["locale"]==loc)
        assert x["catalogGitBlob"]==next(y["gitBlob"] for y in structure if y["locale"]==loc)
        assert x["callerContextSha256"]==sha(canon([c["context"] for c in fresh]))
        assert x["callerRefs"]==[{"path":c["path"],"line":c["line"],"lineSha256":c["lineSha256"],"fileSha256":c["fileSha256"],"gitBlob":c["gitBlob"]} for c in fresh]
        assert x["containsCandidate"] is False and x["verdict"] is None
        assert x["placeholderEvidence"]["sourceTokens"]==ph(src["source"]) and x["placeholderEvidence"]["currentTokens"]==ph(target)
        assert x["markupEvidence"]["sourceTags"]==tags(src["source"]) and x["markupEvidence"]["currentTags"]==tags(target)
        assert x["sourceNumericTokens"]==nums(src["source"]) and x["currentNumericTokens"]==nums(target)
        assert x["sourceProtectedLiterals"]==prot(src["source"]) and x["currentProtectedLiterals"]==prot(target)
# Recompute the exact 104 prior-hold set from sealed W65 source evidence.
old98=jl(W65/"candidate-free-input/prior-held-cell-reattestation.jsonl")
w65ledger=jl(W65/"cross-audit/crossaudit-decisions.jsonl")
w65holds=[x for x in w65ledger if x.get("crossAudit",{}).get("disposition")=="hold"]
assert len(old98)==98 and len(w65holds)==6
expected_holds={(x["continuationRank"],x["locale"]) for x in old98}
expected_holds|={(x["continuationRank"],x["locale"]) for x in w65holds}
prior=jl(I/"prior-held-cell-reattestation.jsonl")
assert len(prior)==104 and {(x["continuationRank"],x["locale"]) for x in prior}==expected_holds
assert all(x["matchesPriorCurrentValue"] and x["status"]=="reattested-unchanged" for x in prior)
for x in prior:
    value=catalogs[x["locale"]][x["source"]]
    assert sha(value.encode())==x["priorTargetSha256"]==x["currentTargetSha256"]
    fresh=scan(x["source"])
    assert x["currentCallerCount"]==len(fresh)
    assert x["currentCallerRefs"]==[{"path":c["path"],"line":c["line"],"lineSha256":c["lineSha256"],"fileSha256":c["fileSha256"],"gitBlob":c["gitBlob"]} for c in fresh]
    assert x["currentCatalogFileSha256"]==next(y["sha256"] for y in structure if y["locale"]==x["locale"])
assert all(r["containsCandidate"] is False and r["verdict"] is None for r in cellrows)
print(json.dumps({"pass":True,"mode":"candidate-free-input","head":head,"tree":tree,"sources":25,"cells":300,
 "ranks":[528,552],"remainingQueue":[428,452],"priorSelectedIdsExcluded":len(prior_ids),"priorHoldsReattested":len(prior),
 "callerCounts":{str(k):v["productionCallerCount"] for k,v in ctxmap.items()},
 "catalogKeysPerLocale":6176,"targetRowsPinned":True,"noCandidates":True,"livePRRefs":"PASS","checksums":"PASS"},ensure_ascii=False,indent=2))
