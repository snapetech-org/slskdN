#!/usr/bin/env python3
"""Verify slskdN PR #409 W70 application from committed Git objects."""
from pathlib import Path
from collections import Counter
import hashlib,json,subprocess,sys
APP=Path(__file__).resolve().parent
W=APP.parent
R=APP.parents[4]
BASE="335a96a9ec125b30c20c31be219da4e27db1ab03"
BASE_TREE="7168de556608115be3b7e16b9ceb30b977df904b"
CATALOG="76820443c2fa5c40c0e27f83414a821f7cfc2424"
CATALOG_TREE="af822569576d9b8ee5e0bb05ed630b2ad052e6e2"
def die(s): raise SystemExit("FAIL: "+s)
def sha(b): return hashlib.sha256(b).hexdigest()
def j(p): return json.loads(p.read_text(encoding="utf-8"))
def jl(p): return [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s.strip()]
def git(*x): return subprocess.check_output(["git","-C",str(R),*x],text=True).strip()
def obj(rev,path):
    try: raw=subprocess.check_output(["git","-C",str(R),"show",f"{rev}:{path}"])
    except subprocess.CalledProcessError: die("missing Git object "+path)
    return raw,json.loads(raw.decode("utf-8"))
cross=W/"cross-audit"
cf=W/"candidate-free-packet"/"input"
def files(dir): return {p.relative_to(dir).as_posix():p for p in dir.rglob("*") if p.is_file()}
def same_tree(a,b):
    x,y=files(a),files(b)
    if set(x)!=set(y): die("packet file inventory differs "+str(a))
    for n in x:
        if x[n].read_bytes()!=y[n].read_bytes(): die("packet copy differs "+n)
same_tree(W/"candidate-free-packet",cross/"candidate-free-packet")
same_tree(W/"primary-packet",cross/"primary-packet")
same_tree(W/"blind-packet",cross/"blind-packet")
m=j(APP/"commit-record.json")
if [m["parentHead"],m["parentTree"],m["catalogCommit"],m["catalogTree"]]!=[BASE,BASE_TREE,CATALOG,CATALOG_TREE]: die("commit pins")
if m.get("rebasePerformed") is not False: die("unexpected rebase record")
if git("rev-parse",BASE)!=BASE or git("rev-parse",f"{BASE}^{{tree}}")!=BASE_TREE: die("parent Git object")
if git("rev-parse",CATALOG)!=CATALOG or git("rev-parse",f"{CATALOG}^{{tree}}")!=CATALOG_TREE: die("catalog Git object")
if git("rev-list","--parents","-n","1",CATALOG).split()!=[CATALOG,BASE]: die("catalog commit parent")
if git("merge-base","--is-ancestor",CATALOG,"HEAD")!="": die("catalog commit not ancestor of current evidence head")
allow="--allow-uncommitted" in sys.argv
if allow:
    if git("rev-parse","HEAD")!=CATALOG or git("diff","--name-only"): die("uncommitted mode only allowed at catalog commit with clean tracked files")
    prefix=W.relative_to(R).as_posix()+"/"
    extra=git("ls-files","--others","--exclude-standard").splitlines()
    if any(not x.startswith(prefix) for x in extra): die("uncommitted files outside evidence directory")
elif git("status","--porcelain","--untracked-files=all"): die("repository worktree not clean")
if git("diff","--name-only",BASE,CATALOG,"--",".github/workflows"): die("workflow path changed")
ledger=jl(cross/"cross-audit-ledger.jsonl")
selected=jl(cross/"changed-selections.jsonl")
plan=jl(APP/"application-plan.jsonl")
readback=jl(APP/"application-readback.jsonl")
if len(ledger)!=300 or len(readback)!=300 or len(selected)!=97 or len(plan)!=97: die("cell/plan coverage")
counts=Counter(x["crossAuditDisposition"] for x in ledger)
if counts!=Counter({"accept-current":203,"correction":47,"refinement":50}): die("cross disposition counts")
cell=lambda x:(x["continuationRank"],x["locale"])
lm={cell(x):x for x in ledger}; sm={cell(x):x for x in selected}; pm={cell(x):x for x in plan}; rm={cell(x):x for x in readback}
if len(lm)!=300 or len(sm)!=97 or len(pm)!=97 or len(rm)!=300: die("duplicate cell")
if set(sm)!={k for k,x in lm.items() if x["crossAuditDisposition"] in ("correction","refinement")}: die("selected cell set")
if set(rm)!=set(lm): die("readback cell set")
paths={x["catalogPath"] for x in selected}
if len(paths)!=12 or set(git("diff","--name-only",BASE,CATALOG).splitlines())!=paths: die("catalog commit path scope")
structures={x["catalogPath"]:x for x in jl(cf/"catalog-structure.jsonl")}
invariants={x["catalogPath"]:x for x in j(APP/"catalog-invariants.json")["catalogs"]}
if len(structures)!=12 or set(structures)!=paths or set(invariants)!=paths: die("catalog invariant coverage")
catalogs={}
for p,s in structures.items():
    oldraw,old=obj(BASE,p); newraw,new=obj(CATALOG,p)
    keyhash=sha(("\n".join(old.keys())+"\n").encode("utf-8"))
    inv=invariants[p]
    if len(old)!=6176 or len(new)!=6176 or list(old)!=list(new) or keyhash!=s["orderedKeySha256"]: die("catalog keys/order "+p)
    if sha(oldraw)!=s["sha256"] or git("rev-parse",f"{BASE}:{p}")!=s["gitBlob"]: die("catalog baseline blob/hash "+p)
    if sha(newraw)!=inv["afterSha256"] or git("rev-parse",f"{CATALOG}:{p}")!=inv["afterGitBlob"]: die("catalog final blob/hash "+p)
    if inv["beforeSha256"]!=sha(oldraw) or inv["beforeGitBlob"]!=s["gitBlob"] or inv["keyCount"]!=6176 or inv["orderedKeySha256"]!=keyhash or inv["nonTargetValuesPreserved"] is not True: die("catalog invariant row "+p)
    changed={k for k in old if old[k]!=new[k]}
    wanted={x["catalogKey"] for x in selected if x["catalogPath"]==p}
    if changed!=wanted or len(changed)!=inv["selectedKeyCount"] or set(inv["selectedKeys"])!=wanted: die("catalog changed-key set "+p)
    catalogs[p]=(old,new)
for k,x in lm.items():
    p=x["catalogPath"]; key=x["catalogKey"]; old,new=catalogs[p]
    if old.get(key)!=x["currentTarget"] or sha(old[key].encode("utf-8"))!=x["currentTargetSha256"]: die("target preimage "+str(k))
    if sha(x["selectedTarget"].encode("utf-8"))!=x["selectedTargetSha256"]: die("selected hash "+str(k))
    if any(v is not True for v in x["tokenAudit"]["checks"].values()): die("selected token check "+str(k))
    actual=new[key]
    if actual!=x["selectedTarget"] or sha(actual.encode("utf-8"))!=x["selectedTargetSha256"]: die("catalog readback "+str(k))
    q=rm[k]
    expected=(x["continuationRank"],x["remainingQueueRank"],x["sourceId"],x["locale"],p,key,x["crossAuditDisposition"],x["currentTarget"],x["currentTargetSha256"],x["selectedTarget"],x["selectedTargetSha256"])
    got=(q["continuationRank"],q["remainingQueueRank"],q["sourceId"],q["locale"],q["catalogPath"],q["catalogKey"],q["disposition"],q["preimageTarget"],q["preimageSha256"],q["readbackTarget"],q["readbackTargetSha256"])
    if got!=expected or q["matches"] is not True: die("readback ledger mismatch "+str(k))
    if x["crossAuditDisposition"]=="accept-current" and old[key]!=new[key]: die("accept-current changed "+str(k))
    if x["crossAuditDisposition"] in ("correction","refinement"):
        s=sm[k];p0=pm[k]
        if p0["preimageTarget"]!=old[key] or p0["preimageSha256"]!=sha(old[key].encode()) or p0["selectedTarget"]!=new[key] or p0["selectedTargetSha256"]!=sha(new[key].encode()): die("plan target mismatch "+str(k))
        for f in ("catalogPath","catalogKey","selectedTarget","selectedTargetSha256","currentTarget","currentTargetSha256","crossAuditDisposition"):
            if s.get(f)!=x.get(f): die("cross selection mismatch "+str(k)+"/"+f)
holds=jl(cf/"prior-held-cell-reattestation.jsonl")
hr=jl(APP/"prior-hold-readback.jsonl")
if len(holds)!=140 or len(hr)!=140: die("carried hold count")
hmap={(x["continuationRank"],x["locale"],x["sourceId"]):x for x in hr}
for h in holds:
    p=h["currentCatalogPath"];key=h["source"];old,new=catalogs[p]
    k=(h["continuationRank"],h["locale"],h["sourceId"]);q=hmap.get(k)
    if old.get(key)!=h["currentTarget"] or new.get(key)!=h["currentTarget"] or sha(new[key].encode())!=h["currentTargetSha256"] or not q or q["preserved"] is not True or q["readbackTargetSha256"]!=h["currentTargetSha256"]: die("carried hold mismatch "+str(k))
excluded=jl(cf/"prior-selected-id-exclusions.jsonl")
exsum=j(APP/"prior-id-exclusion-readback.json")
ids={x["sourceId"] for x in excluded}; selected_ids={x["sourceId"] for x in plan}
if len(excluded)!=1732 or len(ids)!=1732 or ids&selected_ids or exsum["excludedIdCount"]!=1732 or exsum["excludedIdRecordsSha256"]!=sha((cf/"prior-selected-id-exclusions.jsonl").read_bytes()) or exsum["excludedIdsOverlappedCurrentWindow"] is not False: die("prior ID exclusion readback")
pre=j(APP/"application-preflight.json")
if pre["result"]!="PASS" or pre["parentHead"]!=BASE or pre["parentTree"]!=BASE_TREE or pre["state"]!="OPEN" or pre["draft"] is not True or pre["prApiBaseSha"]!="f25d263a2a7cdb2c8f76c40c346cb10f749a9356" or pre["mainHistoryRebased"] is not False or pre["currentMainTip"]!="bc6251ff4ea5a7e59f2d86e2400c90520601f46e" or pre["aheadOfCurrentMain"]!=142 or pre["behindCurrentMain"]!=4: die("preflight/divergence record")
result=j(APP/"application-verification.json")
expected={"result":"PASS","cellsReadBack":300,"selectedChanges":97,"corrections":47,"refinements":50,"acceptCurrent":203,"carriedHoldsPreserved":140,"priorIdsExcluded":1732,"catalogFilesChanged":12,"catalogKeyCountsAndOrderPreserved":True,"nonTargetValuesPreserved":True,"selectedTokenFailures":0,"workflowsChanged":False}
for k,v in expected.items():
    if result.get(k)!=v: die("application summary mismatch "+k)
print(json.dumps({"result":"PASS","parent":BASE,"parentTree":BASE_TREE,"catalogCommit":CATALOG,"catalogTree":CATALOG_TREE,"cellsReadBack":300,"selectedChanges":97,"corrections":47,"refinements":50,"acceptCurrent":203,"catalogFilesChanged":12,"carriedHoldsPreserved":140,"priorIdsExcluded":1732,"keyCountPerCatalog":6176,"selectedTokenFailures":0,"rebasePerformed":False,"workflowsChanged":False},indent=2))
