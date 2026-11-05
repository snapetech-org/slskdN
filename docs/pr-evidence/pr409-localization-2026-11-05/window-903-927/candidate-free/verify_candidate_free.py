#!/usr/bin/env python3
"""Portable exact-head verifier for the W81 candidate-free packet."""
import collections,hashlib,json,re,subprocess,sys,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parent
HEAD="91da6fff5d5b628ade7ee556386e3db1db6878fa"
TREE="56930b73d10a4c419edf68f0d951ceedaa63c990"
BRANCH="codex/slskdn-oidc-tooltip-localization-20261030"
BASE="f25d263a2a7cdb2c8f76c40c346cb10f749a9356"
INV="docs/pr-evidence/pr409-localization-2026-11-03/window49/primary/source-inventory.jsonl"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
TEXT_KEYS={"source","sourceText","target","currentTarget","proposedTarget","proposedTargetText","reason","resolvedTarget","resolvedTargetText","formerTargetText"}
def fail(s): raise SystemExit("FAIL: "+s)
def need(ok,s):
    if not ok: fail(s)
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode("utf-8"))
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def j(name): return json.loads((ROOT/name).read_text(encoding="utf-8"))
def rows(name): return [json.loads(x) for x in (ROOT/name).read_text(encoding="utf-8").splitlines() if x.strip()]
def git(repo,*args): return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()
def forbidden(v):
    if isinstance(v,dict): return any(k in TEXT_KEYS or forbidden(x) for k,x in v.items())
    if isinstance(v,list): return any(forbidden(x) for x in v)
    return False
def prod(path):
    parts=path.split("/"); name=parts[-1]; ext=Path(name).suffix.lower()
    return path.startswith("src/web/src/") and ext in {".js",".jsx",".ts",".tsx"} and not any(p in {"__tests__","__specs__"} for p in parts) and not any(x in name for x in (".test.",".spec."))
def scan(source,runtime,repo):
    pat=re.compile(r"(?<![A-Za-z0-9_$])([\"'])"+re.escape(source)+r"\1"); found=[]
    for rec in runtime:
        data=(repo/rec["path"]).read_bytes()
        need(sha(data)==rec["sha256"] and blob(data)==rec["gitBlob"],"runtime pin "+rec["path"])
        try: text=data.decode("utf-8")
        except UnicodeDecodeError: continue
        lines=text.splitlines()
        for n,line in enumerate(lines,1):
            if pat.search(line):
                ctx=[{"line":i+1,"text":lines[i]} for i in range(max(0,n-4),min(len(lines),n+2))]
                found.append({"path":rec["path"],"line":n,"lineText":line,"lineSha256":tsha(line),"context":ctx,
                    "contextSha256":sha(canon(ctx)),"fileBytes":len(data),"fileSha256":sha(data),"gitBlob":rec["gitBlob"],
                    "gitBlobSha1Check":blob(data)})
    return found
def main():
    if len(sys.argv)==3 and sys.argv[1]=="--repo": repo=Path(sys.argv[2]).resolve()
    elif len(sys.argv)==2: repo=Path(sys.argv[1]).resolve()
    else: raise SystemExit("usage: verify_candidate_free.py --repo WORKTREE")
    m=j("manifest.json")
    expected={x["path"] for x in m["files"]}
    need(len(expected)==len(m["files"]),"duplicate manifest path")
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and p.name not in {"manifest.json","PACKET-SHA256SUMS.txt"} and "__pycache__" not in p.parts}
    need(actual==expected,"manifest file inventory")
    for rec in m["files"]:
        p=(ROOT/rec["path"]).resolve()
        need(p.is_relative_to(ROOT.resolve()) and p.is_file(),"unsafe/missing packet file")
        data=p.read_bytes(); need(len(data)==rec["bytes"] and sha(data)==rec["sha256"],"manifest file hash "+rec["path"])
    checks={}
    for line in (ROOT/"PACKET-SHA256SUMS.txt").read_text().splitlines():
        if not line.strip(): continue
        digest,name=line.split("  ",1); need(name not in checks,"duplicate checksum")
        p=(ROOT/name).resolve(); need(p.is_relative_to(ROOT.resolve()) and p.is_file() and sha(p.read_bytes())==digest,"checksum "+name)
        checks[name]=digest
    need(set(checks)==expected|{"manifest.json"},"checksum file inventory")
    need((m["repository"],m["pullRequest"],m["branch"],m["window"],m["candidateFree"],m["head"],m["tree"],m["sourceCount"],m["localeCount"],m["cellCount"])==
        ("snapetech-org/slskdN",409,BRANCH,"W81",True,HEAD,TREE,25,12,300),"manifest identity")
    need(m["locales"]==LOCALES and m["continuationRankRange"]==[903,927] and m["remainingQueueRankRange"]==[803,827],"window selection")
    need(not any(m.get(k) for k in ("proposedTargetsIncluded","reviewDecisionsIncluded","blindReviewUsed","crossReviewUsed","prBodyQueried")),"candidate-free flags")
    need(git(repo,"rev-parse","HEAD")==HEAD and git(repo,"rev-parse","HEAD^{tree}")==TREE and not git(repo,"status","--porcelain=v1"),"source worktree head/tree/clean")
    before,after=j("live-before.json"),j("live-after.json")
    for s in (before,after):
        need((s.get("repository"),s.get("pullRequest"),s.get("state"),s.get("draft"),s.get("merged"),s.get("headRefName"),s.get("headRefOid"),
              s.get("branchRefOid"),s.get("pullRefOid"),s.get("baseRefName"),s.get("baseRefOid"),s.get("commitTree"),s.get("prBodyQueried"))==
             ("snapetech-org/slskdN",409,"OPEN",True,False,BRANCH,HEAD,HEAD,HEAD,"main",BASE,TREE,False),"filtered live snapshot")
    stable=("repository","pullRequest","state","draft","merged","headRefName","headRefOid","branchRefOid","pullRefOid","baseRefName","baseRefOid","liveMainSha","commitTree")
    need(all(before.get(k)==after.get(k) for k in stable),"live refs changed during capture")
    pr=json.loads(subprocess.check_output(["gh","api","repos/snapetech-org/slskdN/pulls/409","--jq","{state:.state,draft:.draft,merged:(.merged_at!=null),headRefName:.head.ref,headRefOid:.head.sha,baseRefName:.base.ref,baseRefOid:.base.sha}"]))
    branch=json.loads(subprocess.check_output(["gh","api",f"repos/snapetech-org/slskdN/git/ref/heads/{BRANCH}","--jq","{oid:.object.sha}"]))
    commit=json.loads(subprocess.check_output(["gh","api",f"repos/snapetech-org/slskdN/commits/{HEAD}","--jq","{sha:.sha,tree:.commit.tree.sha}"]))
    mainsha=subprocess.check_output(["gh","api","repos/snapetech-org/slskdN/commits/main","--jq",".sha"],text=True).strip()
    need((pr["state"],pr["draft"],pr["merged"],pr["headRefName"],pr["headRefOid"],pr["baseRefName"],pr["baseRefOid"])==("open",True,False,BRANCH,HEAD,"main",BASE),"live PR API")
    need(branch["oid"]==HEAD and commit=={"sha":HEAD,"tree":TREE} and mainsha==after["liveMainSha"],"live ref API")
    remote=subprocess.check_output(["git","ls-remote","https://github.com/snapetech-org/slskdN.git",f"refs/heads/{BRANCH}","refs/pull/409/head"],text=True)
    refs={line.split()[1]:line.split()[0] for line in remote.splitlines() if line.strip()}
    need(refs.get(f"refs/heads/{BRANCH}")==HEAD and refs.get("refs/pull/409/head")==HEAD,"remote refs")
    drift=j("main-drift.json")
    need((drift["baseApiSha"],drift["liveMainBeforeSha"],drift["liveMainAfterSha"],drift["localizationOrCatalogChanges"])==(BASE,before["liveMainSha"],after["liveMainSha"],False),"main drift")
    need(not any(p.startswith("src/web/public/locales/") or p.startswith("src/web/src/") or p.endswith("source-inventory.jsonl") for p in drift["changedPaths"]),"main drift overlaps locale/source/caller paths")

    invraw=subprocess.check_output(["git","-C",str(repo),"show",f"{HEAD}:{INV}"])
    need(sha(invraw)==m["sourceInventorySha256"],"source inventory raw hash")
    inv=[json.loads(x) for x in invraw.decode().splitlines() if x.strip()]
    need(len(inv)==6176,"source inventory rows")
    byid={r["sourceId"]:r for r in inv}; byr={r["continuationRank"]:r for r in inv if r.get("continuationRank") is not None}
    need(len(byid)==len(inv),"source ID uniqueness")
    for r in inv: need(r["sourceId"]=="src_"+tsha(r["source"])[:16] and r["sourceSha256"]==tsha(r["source"]),"source identity/hash")
    selected=rows("source-inventory-selection.jsonl")
    need([r["continuationRank"] for r in selected]==list(range(903,928)),"selected ranks")
    need([r["remainingQueueRank"] for r in selected]==list(range(803,828)),"remaining queue ranks")
    need([r["sourceId"] for r in selected]==[byr[n]["sourceId"] for n in range(903,928)],"selected inventory binding")
    boundary=rows("selection-boundary.jsonl")
    need(len(boundary)==27 and boundary[0]["continuationRank"]==902 and boundary[-1]["continuationRank"]==928,"boundary ranks")
    need(boundary[1]["sourceId"]==selected[0]["sourceId"] and boundary[-1]["sourceId"]==byr[928]["sourceId"],"boundary source IDs")
    projection=rows("source-inventory-pinned.jsonl")
    need(len(projection)==6176 and sha((ROOT/"source-inventory-pinned.jsonl").read_bytes())==j("source-tree-attestation.json")["sourceInventoryProjectionSha256"],"source projection")
    runtime=rows("runtime-file-pins.jsonl")
    need(len(runtime)==279 and all(prod(x["path"]) for x in runtime),"runtime file inventory")
    cats={}
    order=None
    def no_dup(pairs):
        d={}
        for k,v in pairs:
            need(k not in d,"duplicate catalog key")
            d[k]=v
        return d
    structure=rows("catalog-structure.jsonl")
    need(len(structure)==12,"catalog structure count")
    for rec in structure:
        data=(repo/rec["catalogPath"]).read_bytes()
        need(sha(data)==rec["sha256"] and blob(data)==rec["gitBlob"],"catalog file pin "+rec["locale"])
        obj=json.loads(data.decode("utf-8"),object_pairs_hook=no_dup)
        keys=list(obj)
        need(len(keys)==6176 and keys==list(obj) and all(isinstance(v,str) and v for v in obj.values()),"catalog key/value structure")
        kh=sha(("\n".join(keys)+"\n").encode())
        need(kh==rec["orderedKeySha256"],"ordered catalog keys "+rec["locale"])
        if order is None: order=keys
        need(keys==order,"locale catalog parity")
        cats[rec["locale"]]=obj
    caller_rows=rows("caller-contexts.jsonl"); cell_rows=rows("source-current-cells.jsonl")
    need(len(caller_rows)==25 and len(cell_rows)==300,"cell/caller counts")
    caller_map={r["sourceId"]:r for r in caller_rows}; sources={r["sourceId"]:r for r in rows("selected-sources.jsonl")}
    for sid,src in sources.items():
        full=scan(src["source"],runtime,repo); saved=caller_map[sid]
        need(saved["productionCallerCount"]==len(full) and saved["callers"]==full,"caller context "+sid)
        need(src["sourceSha256"]==tsha(src["source"]) and src["sourceSha256"]==byid[sid]["sourceSha256"],"selected source hash")
    for row in cell_rows:
        src=sources[row["sourceId"]]; locale=row["locale"]; target=cats[locale][src["source"]]
        need(row["sourceSha256"]==src["sourceSha256"] and row["currentTargetSha256"]==tsha(target),"current cell hash")
        need(row.get("source")==src["source"] and row.get("currentTarget")==target,"current text binding")
        need(row["callerContextSha256"]==sha(canon(scan(src["source"],runtime,repo))),"cell caller fingerprint")
        need(row["containsCandidate"] is False and row.get("verdict") is None,"candidate/review leakage")

    prior_ids=rows("prior-selected-id-exclusions-hash-only.jsonl")
    need(len(prior_ids)==1982 and len({x["sourceId"] for x in prior_ids})==1982,"prior selected ID count")
    need(not ({x["sourceId"] for x in prior_ids}&set(sources)),"prior/selected overlap")
    need(all(x["sourceId"] in byid and byid[x["sourceId"]]["sourceSha256"]==x["sourceSha256"] for x in prior_ids),"prior selected source hash")
    holds=rows("previous-window-prior-holds-hash-only.jsonl"); hold_att=rows("prior-held-cell-reattestation-hash-only.jsonl")
    need(len(holds)==len(hold_att)==382 and all(x["matchesPriorCurrentValue"] and x["callerEvidenceUnchanged"] for x in hold_att),"active hold continuity")
    for h,a in zip(holds,hold_att):
        need(h["sourceId"]==a["sourceId"] and h["locale"]==a["locale"] and h["priorTargetSha256"]==a["priorTargetSha256"],"hold row linkage")
        src=byid[h["sourceId"]]; target=cats[h["locale"]][src["source"]]
        need(tsha(target)==a["currentTargetSha256"]==h["priorTargetSha256"],"held target hash")
        need(sha(canon(scan(src["source"],runtime,repo)))==a["currentCallerContextSha256"],"held caller context")
    resolutions=rows("prior-hold-resolution-history-hash-only.jsonl")
    need(len(resolutions)==13 and all(not forbidden(x) for x in resolutions),"resolution history continuity")
    applied=rows("prior-applied-targets-reattestation-hash-only.jsonl")
    need(len(applied)==190 and all(x["targetRemainsApplied"] for x in applied),"applied target continuity")
    for a in applied:
        src=byid[a["sourceId"]]; target=cats[a["locale"]][src["source"]]
        need(tsha(target)==a["currentTargetSha256"]==a["appliedTargetSha256"],"applied target hash")
    need(j("prior-hold-lineage-summary.json")["holdLineage"]==m["priorHoldLineage"],"hold lineage summary")
    need(j("baseline-token-mismatch-summary.json")["cellCount"]==300,"token audit coverage")
    print(json.dumps({"result":"PASS","head":HEAD,"tree":TREE,"cells":len(cell_rows),"sourcesWithCallers":25,
      "priorSelectedIds":len(prior_ids),"priorHeldCells":len(holds),"holdResolutions":len(resolutions),
      "priorAppliedTargets":len(applied),"mainLocalizationChanges":False,"prBodyQueried":False},indent=2))
if __name__=="__main__": main()

