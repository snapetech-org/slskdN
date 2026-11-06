#!/usr/bin/env python3
"""Portable W80 candidate-free packet verifier; PR API projections exclude body."""
import collections
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEAD = "7a1ca27fd0519674c3b42a3e3df3638b0f671567"
TREE = "b3525218d0f9676c88c4991e78775d113f18b7d9"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
BASE = "f25d263a2a7cdb2c8f76c40c346cb10f749a9356"
INV_PATH = "docs/pr-evidence/pr409-localization-2026-11-03/window49/primary/source-inventory.jsonl"
APP = "docs/pr-evidence/pr409-localization-2026-11-04/window-853-877/application/"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
TEXT_KEYS = {"source", "sourceText", "target", "currentTarget", "proposedTarget", "proposedTargetText", "reason", "resolvedTarget", "resolvedTargetText", "formerTargetText"}
PREV = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w79-853-877-primary-20261104/candidate-free/input")


def fail(m): raise SystemExit("FAIL: " + m)
def need(ok, m):
    if not ok: fail(m)
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode("utf-8"))
def blob_sha(b): return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()
def canon(v): return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
def readj(p): return json.loads((ROOT / p).read_text(encoding="utf-8"))
def rows(p): return [json.loads(x) for x in (ROOT / p).read_text(encoding="utf-8").splitlines() if x.strip()]
def git(repo, *args): return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
def ph(s): return collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", s))
def tags(s): return collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", s))
def nums(s): return ["".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in n) for n in re.findall(r"\d+", s)]
def protected(s):
    out = set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", s)); out.update(x for x in ("slskdN", "Tor", "Wishlist", "Chromaprint") if x in s); return sorted(out)
def hash_refs(refs): return [{k:r[k] for k in ("path", "line", "lineSha256", "contextSha256", "fileSha256", "gitBlob")} for r in refs]
def forbidden(v):
    if isinstance(v, dict): return any(k in TEXT_KEYS or forbidden(x) for k,x in v.items())
    if isinstance(v, list): return any(forbidden(x) for x in v)
    return False
def prod_path(path):
    parts=path.split("/"); name=parts[-1]; suffix=Path(name).suffix.lower()
    return path.startswith("src/web/src/") and suffix in {".js",".jsx",".ts",".tsx"} and not any(p in {"__tests__","__specs__"} for p in parts) and not any(x in name for x in (".test.",".spec."))
def scan(source, runtime, repo):
    pat=re.compile(r"(?<![A-Za-z0-9_$])([\"'])"+re.escape(source)+r"\1"); found=[]
    for rec in runtime:
        data=(repo/rec["path"]).read_bytes(); need(sha(data)==rec["sha256"] and blob_sha(data)==rec["gitBlob"],"runtime file pin: "+rec["path"])
        try: content=data.decode("utf-8")
        except UnicodeDecodeError: continue
        lines=content.splitlines()
        for n,line in enumerate(lines,1):
            if pat.search(line):
                context=[{"line":i+1,"text":lines[i]} for i in range(max(0,n-4),min(len(lines),n+2))]
                found.append({"path":rec["path"],"line":n,"lineText":line,"lineSha256":tsha(line),"context":context,"contextSha256":sha(canon(context)),"fileBytes":len(data),"fileSha256":sha(data),"gitBlob":rec["gitBlob"],"gitBlobSha1Check":blob_sha(data)})
    return found

def verify_manifest():
    m=readj("manifest.json"); expected={x["path"] for x in m["files"]}
    need(len(expected)==len(m["files"]),"duplicate manifest entry")
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and p.name not in {"manifest.json","PACKET-SHA256SUMS.txt"}}
    need(actual==expected,"manifest file inventory")
    for x in m["files"]:
        p=(ROOT/x["path"]).resolve(); need(p.is_relative_to(ROOT.resolve()) and p.is_file(),"unsafe/missing packet path")
        b=p.read_bytes(); need(len(b)==x["bytes"] and sha(b)==x["sha256"],"manifest hash: "+x["path"])
    sums={}
    for line in (ROOT/"PACKET-SHA256SUMS.txt").read_text().splitlines():
        if not line.strip(): continue
        digest,name=line.split("  ",1); need(name not in sums,"duplicate checksum path"); sums[name]=digest
        p=(ROOT/name).resolve(); need(p.is_relative_to(ROOT.resolve()) and p.is_file() and sha(p.read_bytes())==digest,"checksum mismatch: "+name)
    need(set(sums)==expected|{"manifest.json"},"checksum inventory")
    need((m.get("artifact"),m.get("window"),m.get("candidateFree"),m.get("head"),m.get("tree"),m.get("repository"),m.get("sourceCount"),m.get("localeCount"),m.get("cellCount"))==
         ("slskdN PR #409 W80 ranks 878-902 candidate-free exact-head input","W80",True,HEAD,TREE,"snapetech-org/slskdN",25,12,300),"manifest identity/coverage")
    need(m.get("prBodyQueried") is False and m.get("proposedTargetsIncluded") is False and m.get("reviewDecisionsIncluded") is False and m.get("blindReviewUsed") is False and m.get("crossReviewUsed") is False,"candidate-free purity flags")
    return m,len(sums)

def live_check(m, repo):
    before,after=readj("live-before.json"),readj("live-after.json"); att=readj("head-tree-attestation.json")
    need(att.get("liveBefore")==before and att.get("liveAfter")==after,"head attestation linkage")
    for s in (before,after):
        need(not any("body" in k.lower() for k in s if k != "prBodyQueried") and s.get("prBodyQueried") is False,"PR body exposure flag/key")
        need((s.get("repository"),s.get("pullRequest"),s.get("state"),s.get("draft"),s.get("merged"),s.get("headRefName"),s.get("headRefOid"),s.get("branchRefOid"),s.get("pullRefOid"),s.get("baseRefName"),s.get("baseRefOid"),s.get("commitTree"))==
             ("snapetech-org/slskdN",409,"OPEN",True,False,BRANCH,HEAD,HEAD,HEAD,"main",BASE,TREE),"filtered live PR/ref snapshot")
    stable=("repository","pullRequest","state","draft","merged","headRefName","headRefOid","branchRefOid","pullRefOid","baseRefName","baseRefOid","liveMainSha","commitTree")
    need(all(before.get(k)==after.get(k) for k in stable),"live refs changed during extraction")
    need(git(repo,"rev-parse","HEAD")==HEAD and git(repo,"rev-parse","HEAD^{tree}")==TREE and not git(repo,"status","--porcelain=v1"),"source worktree head/tree/clean")
    pr=json.loads(subprocess.check_output(["gh","api","repos/snapetech-org/slskdN/pulls/409","--jq","{state:.state,draft:.draft,merged:(.merged_at!=null),headRefName:.head.ref,headRefOid:.head.sha,baseRefName:.base.ref,baseRefOid:.base.sha}"]))
    branch=json.loads(subprocess.check_output(["gh","api",f"repos/snapetech-org/slskdN/git/ref/heads/{BRANCH}","--jq","{oid:.object.sha}"]))
    commit=json.loads(subprocess.check_output(["gh","api",f"repos/snapetech-org/slskdN/commits/{HEAD}","--jq","{sha:.sha,tree:.commit.tree.sha}"]))
    main=subprocess.check_output(["gh","api","repos/snapetech-org/slskdN/commits/main","--jq",".sha"],text=True).strip()
    need((pr["state"],pr["draft"],pr["merged"],pr["headRefName"],pr["headRefOid"],pr["baseRefName"],pr["baseRefOid"])==("open",True,False,BRANCH,HEAD,"main",BASE),"live API pull projection")
    need(branch.get("oid")==HEAD and commit=={"sha":HEAD,"tree":TREE} and main==after["liveMainSha"],"live API refs/main")
    remote=subprocess.check_output(["git","ls-remote","https://github.com/snapetech-org/slskdN.git",f"refs/heads/{BRANCH}","refs/pull/409/head"],text=True)
    refs={l.split()[1]:l.split()[0] for l in remote.splitlines() if l.strip()}
    need(refs.get(f"refs/heads/{BRANCH}")==HEAD and refs.get("refs/pull/409/head")==HEAD,"live branch/pull refs")
    drift=readj("main-drift.json"); driftb=readj("main-drift-before.json")
    need((drift["baseApiSha"],drift["liveMainBeforeSha"],drift["liveMainAfterSha"],drift["localizationOrCatalogChanges"])==(BASE,before["liveMainSha"],after["liveMainSha"],False),"main drift attestation")
    need(driftb["changedPaths"]==drift["changedPaths"] and drift["liveMainSha"]==after["liveMainSha"],"main drift snapshots changed")

def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("--repo",required=True); args=ap.parse_args(); repo=Path(args.repo).resolve()
    manifest,checksum_count=verify_manifest(); live_check(manifest,repo)
    invraw=subprocess.check_output(["git","-C",str(repo),"show",f"{HEAD}:{INV_PATH}"])
    need(invraw==(repo/INV_PATH).read_bytes() and sha(invraw)==manifest["sourceInventorySha256"],"pinned inventory bytes/hash")
    inv=[json.loads(x) for x in invraw.decode().splitlines() if x.strip()]; need(len(inv)==6176,"inventory row count")
    byid={r["sourceId"]:r for r in inv}; byrank={r["continuationRank"]:r for r in inv if r.get("continuationRank") is not None}
    need(len(byid)==len(inv),"inventory ID uniqueness")
    for r in inv: need(r["sourceId"]=="src_"+tsha(r["source"])[:16] and r["sourceSha256"]==tsha(r["source"]),"inventory source identity")
    projection=[{k:r[k] for k in ("sourceId","sourceSha256","continuationRank","remainingQueueRank","localeCoverage","excluded") if k in r} for r in inv]
    need(rows("source-inventory-pinned.jsonl")==projection,"hash-only inventory projection")
    selected=rows("source-inventory-selection.jsonl"); boundary=rows("selection-boundary.jsonl"); sel=readj("selection-and-boundary.json")
    need([r["continuationRank"] for r in selected]==list(range(878,903)) and [r["remainingQueueRank"] for r in selected]==list(range(778,803)),"selection rank/queue range")
    need([r["sourceId"] for r in selected]==[byrank[n]["sourceId"] for n in range(878,903)],"selected source inventory map")
    need([r["continuationRank"] for r in boundary]==[877,*range(878,903),903] and [r["boundaryRole"] for r in boundary]==["previous-window-final"]+["selected-window"]*25+["next-unselected"],"selection boundary range/roles")
    need(boundary[0]["sourceId"]==byrank[877]["sourceId"] and boundary[-1]["sourceId"]==byrank[903]["sourceId"] and sel["nextUnselectedSourceId"]==byrank[903]["sourceId"],"boundary continuity")
    tree={}
    for ent in subprocess.check_output(["git","-C",str(repo),"ls-tree","-r","-z",HEAD]).split(b"\0"):
        if ent:
            meta,path=ent.split(b"\t",1); mode,kind,oid=meta.decode().split(); tree[path.decode()]={"mode":mode,"type":kind,"gitBlob":oid}
    st=readj("source-tree-attestation.json"); need(st["head"]==HEAD and st["tree"]==TREE and st["sourceInventoryRawSha256"]==sha(invraw),"source tree attestation")
    runtime=rows("runtime-file-pins.jsonl"); expected_runtime=[]
    for p,e in sorted(tree.items()):
        if prod_path(p):
            d=(repo/p).read_bytes(); expected_runtime.append({"path":p,"bytes":len(d),"sha256":sha(d),"gitBlob":e["gitBlob"]})
            need(blob_sha(d)==e["gitBlob"],"runtime git blob: "+p)
    need(runtime==expected_runtime and len(runtime)==279,"runtime file inventory")
    catalogs=rows("catalog-structure.jsonl"); need([r["locale"] for r in catalogs]==LOCALES,"locale order")
    cats={}; keyorder=None
    def no_dup(pairs):
        o={}
        for k,v in pairs:
            need(k not in o,"duplicate locale key"); o[k]=v
        return o
    for r in catalogs:
        raw=subprocess.check_output(["git","-C",str(repo),"show",f"{HEAD}:{r['catalogPath']}"]); d=(repo/r["catalogPath"]).read_bytes()
        need(raw==d and sha(d)==r["sha256"] and blob_sha(d)==r["gitBlob"],"catalog pin: "+r["locale"])
        o=json.loads(d.decode(),object_pairs_hook=no_dup); keys=list(o)
        if keyorder is None: keyorder=keys
        need(keys==keyorder and len(keys)==6176 and all(isinstance(v,str) and v for v in o.values()),"catalog order/value coverage")
        need(r["entryCount"]==6176 and r["orderedKeySha256"]==sha(("\n".join(keys)+"\n").encode()),"catalog structure row")
        cats[r["locale"]]=o
    need(sel["orderedCatalogKeySha256"]==sha(("\n".join(keyorder)+"\n").encode()),"catalog ordered key hash")
    callerrows=rows("caller-contexts.jsonl"); cells=rows("source-current-cells.jsonl")
    need(len(callerrows)==25 and len(cells)==300,"caller/cell coverage")
    callers={r["sourceId"]:r for r in callerrows}; need(len(callers)==25,"caller source uniqueness")
    holds=rows("previous-window-prior-holds-hash-only.jsonl"); resolutions=rows("prior-hold-resolution-history-hash-only.jsonl")
    holdatt=rows("prior-held-cell-reattestation-hash-only.jsonl"); applied=rows("prior-applied-targets-reattestation-hash-only.jsonl")
    w79holds=rows("previous-window-holds-hash-only.jsonl"); w79applied=rows("previous-window-applied-targets-hash-only.jsonl")
    oldids=rows("prior-selected-id-exclusions-hash-only.jsonl"); selection_add=rows("previous-window-selection-hash-only.jsonl")
    need((len(holds),len(resolutions),len(holdatt),len(applied),len(w79holds),len(w79applied),len(oldids),len(selection_add))==(382,13,382,109,39,46,1957,25),"W79 full lineage counts")
    for group in (holds,resolutions,holdatt,applied,w79holds,w79applied,oldids,selection_add): need(not any(forbidden(x) for x in group),"text in hash-only lineage")
    need(len({r["sourceId"] for r in oldids})==1957 and not ({r["sourceId"] for r in oldids}&{r["sourceId"] for r in selected}),"prior selected IDs overlap")
    for r in oldids: need(byid.get(r["sourceId"]) and byid[r["sourceId"]]["sourceSha256"]==r["sourceSha256"],"prior selected hash drift")
    need(sum(bool(r["callerlessHashOnly"]) for r in w79holds)==24 and all(r["sourceTextIncluded"] is False and r["targetTextIncluded"] is False for r in w79holds),"W79 callerless holds text flags")
    source_ids={r["sourceId"] for r in selected}|{r["sourceId"] for r in holds}|{r["sourceId"] for r in resolutions}
    refs={sid:scan(byid[sid]["source"],runtime,repo) for sid in sorted(source_ids)}
    for cr in callerrows:
        now=refs[cr["sourceId"]]; need(now==cr["callers"] and cr["productionCallerCount"]==len(now),"selected caller scan: "+cr["sourceId"])
        need(cr["sourceTextIncluded"]==bool(now) and (not now or cr.get("source")==byid[cr["sourceId"]]["source"]),"caller source text flags")
    cellmap={}
    for cell in cells:
        key=(cell["continuationRank"],cell["locale"]); need(key not in cellmap,"duplicate selected cell"); cellmap[key]=cell
        src=byrank[cell["continuationRank"]]; locale=cell["locale"]; current=cats[locale][src["source"]]; now=refs[src["sourceId"]]
        need(cell["sourceId"]==src["sourceId"] and cell["sourceSha256"]==src["sourceSha256"] and cell["currentTargetSha256"]==tsha(current),"selected cell/source/current hash")
        need(cell["callerRefs"]==hash_refs(now) and cell["callerContextSha256"]==sha(canon(now)),"selected cell caller refs/hash")
        need(cell["sourceTextIncluded"]==bool(now) and cell["currentTargetTextIncluded"]==bool(now),"selected cell text flags")
        if now: need(cell.get("source")==src["source"] and cell.get("catalogKey")==src["source"] and cell.get("currentTarget")==current,"selected cell visible text")
        else: need(not any(k in cell for k in ("source","catalogKey","currentTarget")),"callerless selected cell text exposure")
    need(set(cellmap)=={(r,l) for r in range(878,903) for l in LOCALES},"selected cell matrix")
    for h,a in zip(holds,holdatt):
        need((h["priorWindow"],h["sourceId"],h["locale"])==(a["priorWindow"],a["sourceId"],a["locale"]),"hold attestation identity")
        src=byid[h["sourceId"]]; locale=h["locale"]; refs_now=refs[h["sourceId"]]; th=tsha(cats[locale][src["source"]]); ctx=sha(canon(refs_now))
        need(a["currentTargetSha256"]==th and a["priorTargetSha256"]==h["priorTargetSha256"] and a["matchesPriorCurrentValue"]==(th==h["priorTargetSha256"]),"hold target hash reattestation")
        need(a["currentCallerContextSha256"]==ctx and a["currentCallerRefs"]==hash_refs(refs_now) and a["callerEvidenceUnchanged"]==(ctx==h["currentCallerContextSha256"]),"hold caller reattestation")
    for r in resolutions:
        src=byid[r["sourceId"]]; need(r["currentTargetSha256"]==tsha(cats[r["locale"]][src["source"]]),"resolution current target")
        need(r["currentCallerContextSha256"]==sha(canon(refs[r["sourceId"]])) and r["currentCallerRefs"]==hash_refs(refs[r["sourceId"]]),"resolution caller reattestation")
    for r in applied:
        src=byid[r["sourceId"]]; need(r["currentTargetSha256"]==tsha(cats[r["locale"]][src["source"]])==r["appliedTargetSha256"] and r["targetRemainsApplied"],"applied target reattestation")
    planraw=subprocess.check_output(["git","-C",str(repo),"show",f"{HEAD}:{APP}application-plan.jsonl"]); plan=[json.loads(x) for x in planraw.decode().splitlines() if x.strip()]
    need(len(plan)==46 and sha(planraw)==readj("continuity-provenance.json")["w79ApplicationPlanSha256"],"W79 plan attestation")
    pmap={(x["sourceId"],x["locale"]):x for x in plan}
    need(len(pmap)==46,"W79 applied plan uniqueness")
    for r in w79applied:
        x=pmap[(r["sourceId"],r["locale"])]; src=byid[r["sourceId"]]
        need(x["targetSha256"]==r["appliedTargetSha256"]==tsha(x["target"]) and r["currentTargetSha256"]==tsha(cats[r["locale"]][src["source"]]),"W79 correction hash lineage")
    rawholds=subprocess.check_output(["git","-C",str(repo),"show",f"{HEAD}:{APP}holds-hash-only.jsonl"]); planholds=[json.loads(x) for x in rawholds.decode().splitlines() if x.strip()]
    need(len(planholds)==39 and sha(rawholds)==readj("continuity-provenance.json")["w79ApplicationHoldsSha256"],"W79 hold source attestation")
    need({(r["sourceId"],r["locale"],r["currentTargetSha256"]) for r in w79holds}=={(r["sourceId"],r["locale"],r["currentTargetSha256"]) for r in planholds},"W79 hold matrix preservation")
    prior_sum=readj("prior-hold-lineage-summary.json"); need(prior_sum["carriedHoldCells"]==382 and prior_sum["holdLineage"].get("W79")==39 and sum(prior_sum["holdLineage"].values())==382,"hold lineage summary")
    token_summary=readj("baseline-token-mismatch-summary.json"); mismatch=collections.Counter()
    for cell in cells:
        source,current=cell.get("source"),cell.get("currentTarget")
        if source is None: continue
        checks={"placeholder":ph(source)==ph(current),"markup":tags(source)==tags(current),"numeric":all(collections.Counter(nums(current))[x]>=n for x,n in collections.Counter(nums(source)).items()),"protectedLiteral":all(t in current for t in protected(source))}
        for k,v in checks.items():
            if not v: mismatch[k]+=1
    need(token_summary["cellCount"]==300 and token_summary["mismatchCounts"]=={k:mismatch.get(k,0) for k in ("placeholder","markup","numeric","protectedLiteral")},"baseline token mismatch counts")
    print(json.dumps({"result":"PASS","window":"W80","head":HEAD,"tree":TREE,"sourceCount":25,"localeCount":12,"cellCount":300,
                      "sourcesWithCallers":25,"sourcesWithoutCallers":0,"priorSelectedIds":len(oldids),"priorHolds":len(holds),"holdResolutions":len(resolutions),
                      "priorAppliedTargets":len(applied),"w79AppliedTargets":len(w79applied),"w79Holds":len(w79holds),"w79CallerlessHolds":sum(r["callerlessHashOnly"] for r in w79holds),
                      "tokenMismatches":token_summary["mismatchCounts"],"liveRefs":"PASS","packetChecksums":checksum_count,"prBodyQueried":False},ensure_ascii=False,indent=2))


if __name__=="__main__": main()
