#!/usr/bin/env python3
"""Build the W81 candidate-free review packet at an exact slskdN PR head."""
import collections, hashlib, json, re, subprocess, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path(sys.argv[1]).resolve()
PREV = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w80-878-902-20261104/candidate-free/input")
HEAD = "91da6fff5d5b628ade7ee556386e3db1db6878fa"
TREE = "56930b73d10a4c419edf68f0d951ceedaa63c990"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
BASE = "f25d263a2a7cdb2c8f76c40c346cb10f749a9356"
INV_PATH = "docs/pr-evidence/pr409-localization-2026-11-03/window49/primary/source-inventory.jsonl"
APP_PREFIX = "docs/pr-evidence/pr409-localization-2026-11-04/window-878-902/application/"
W80_PRODUCT = "81a2428c5ffc81100f07762f232d27150d1434ec"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
FIRST, LAST = 903, 927
TEXT_KEYS = {"source", "sourceText", "target", "currentTarget", "proposedTarget", "proposedTargetText", "reason", "resolvedTarget", "resolvedTargetText", "formerTargetText"}

def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode("utf-8"))
def blob_sha(b): return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()
def canon(v): return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
def git(*args): return subprocess.check_output(["git", "-C", str(REPO), *args])
def jread(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def jlines(p): return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]
def wjson(name, value): (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
def wjsonl(name, values):
    with (ROOT / name).open("w", encoding="utf-8", newline="\n") as out:
        for value in values: out.write(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
def ph(s): return collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", s))
def tags(s): return collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", s))
def nums(s): return ["".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in token) for token in re.findall(r"\d+", s)]
def protected(s):
    vals = set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", s))
    vals.update(x for x in ("slskdN", "Tor", "Wishlist", "Chromaprint") if x in s)
    return sorted(vals)
def not_less(source, target):
    a, b = collections.Counter(source), collections.Counter(target)
    return all(b[token] >= count for token, count in a.items())
def hash_refs(refs):
    return [{k:r[k] for k in ("path","line","lineSha256","contextSha256","fileSha256","gitBlob")} for r in refs]
def forbidden(v):
    if isinstance(v, dict): return any(k in TEXT_KEYS or forbidden(x) for k,x in v.items())
    if isinstance(v, list): return any(forbidden(x) for x in v)
    return False
def prod_path(path):
    parts=path.split("/"); name=parts[-1]; suffix=Path(name).suffix.lower()
    return path.startswith("src/web/src/") and suffix in {".js",".jsx",".ts",".tsx"} and not any(p in {"__tests__","__specs__"} for p in parts) and not any(x in name for x in (".test.",".spec."))
def tree_entries():
    out={}
    for ent in git("ls-tree","-r","-z",HEAD).split(b"\0"):
        if not ent: continue
        meta,path=ent.split(b"\t",1); mode,kind,oid=meta.decode().split()
        out[path.decode()]={"mode":mode,"type":kind,"gitBlob":oid}
    return out
def load_catalogs(tree):
    cats, rows, key_order = {}, [], None
    def no_duplicates(pairs):
        out={}
        for k,v in pairs:
            if k in out: raise ValueError("duplicate key "+k)
            out[k]=v
        return out
    for locale in LOCALES:
        path=f"src/web/public/locales/{locale}.json"; raw=git("show",f"{HEAD}:{path}")
        if raw!=(REPO/path).read_bytes(): raise SystemExit("REFUSED: catalog differs from exact HEAD: "+locale)
        obj=json.loads(raw.decode("utf-8"),object_pairs_hook=no_duplicates); keys=list(obj)
        if key_order is None: key_order=keys
        if keys!=key_order or len(keys)!=6176 or any(not isinstance(v,str) or not v for v in obj.values()):
            raise SystemExit("REFUSED: catalog structure/coverage: "+locale)
        cats[locale]=obj
        rows.append({"locale":locale,"catalogPath":path,"bytes":len(raw),"sha256":sha(raw),"gitBlob":tree[path]["gitBlob"],
                     "entryCount":len(keys),"nonemptyValueCount":sum(bool(v) for v in obj.values()),
                     "orderedKeySha256":sha(("\n".join(keys)+"\n").encode())})
    return cats,rows,key_order
def refs_for(source,runtime):
    pat=re.compile(r"(?<![A-Za-z0-9_$])([\"'])"+re.escape(source)+r"\1"); found=[]
    for rec in runtime:
        data=(REPO/rec["path"]).read_bytes()
        if sha(data)!=rec["sha256"] or blob_sha(data)!=rec["gitBlob"]: raise SystemExit("REFUSED: runtime pin: "+rec["path"])
        try: content=data.decode("utf-8")
        except UnicodeDecodeError: continue
        lines=content.splitlines()
        for n,line in enumerate(lines,1):
            if not pat.search(line): continue
            context=[{"line":i+1,"text":lines[i]} for i in range(max(0,n-4),min(len(lines),n+2))]
            found.append({"path":rec["path"],"line":n,"lineText":line,"lineSha256":tsha(line),"context":context,
                          "contextSha256":sha(canon(context)),"fileBytes":len(data),"fileSha256":sha(data),
                          "gitBlob":rec["gitBlob"],"gitBlobSha1Check":blob_sha(data)})
    return found
def verify_prior():
    sums={}
    for line in (PREV/"PACKET-SHA256SUMS.txt").read_text().splitlines():
        if not line.strip(): continue
        digest,name=line.split("  ",1); sums[name]=digest
        if not (PREV/name).is_file() or sha((PREV/name).read_bytes())!=digest: raise SystemExit("REFUSED: W80 prior checksum "+name)
    expected={p.relative_to(PREV).as_posix() for p in PREV.rglob("*") if p.is_file() and p.name not in {"manifest.json","PACKET-SHA256SUMS.txt"}}
    if set(sums)!=expected|{"manifest.json"} or sha((PREV/"manifest.json").read_bytes())!=sums["manifest.json"]:
        raise SystemExit("REFUSED: W80 prior packet inventory")
    m=jread(PREV/"manifest.json")
    if (m.get("window"),m.get("head"),m.get("tree"),m.get("sourceCount"),m.get("cellCount"))!=("W80","7a1ca27fd0519674c3b42a3e3df3638b0f671567","b3525218d0f9676c88c4991e78775d113f18b7d9",25,300):
        raise SystemExit("REFUSED: W80 predecessor manifest")
    return sha((PREV/"manifest.json").read_bytes()),sha((PREV/"PACKET-SHA256SUMS.txt").read_bytes()),m

def main():
    if git("rev-parse","HEAD").decode().strip()!=HEAD or git("rev-parse","HEAD^{tree}").decode().strip()!=TREE:
        raise SystemExit("REFUSED: source worktree is not exact W81 head/tree")
    if git("status","--porcelain=v1").decode().strip(): raise SystemExit("REFUSED: source worktree is not clean")
    live_before=jread(ROOT/"live-before.json"); drift_before=jread(ROOT/"main-drift-before.json")
    if (live_before.get("headRefOid"),live_before.get("commitTree"),live_before.get("baseRefOid"),live_before.get("prBodyQueried"))!=(HEAD,TREE,BASE,False):
        raise SystemExit("REFUSED: exact live before snapshot")
    prev_manifest_sha,prev_sums_sha,prev_manifest=verify_prior()
    prev_selected=jlines(PREV/"source-inventory-selection.jsonl"); prev_boundary=jread(PREV/"selection-and-boundary.json")
    if len(prev_selected)!=25 or prev_boundary.get("nextUnselectedContinuationRank")!=FIRST:
        raise SystemExit("REFUSED: W80 selection/boundary coverage")
    if prev_boundary.get("nextUnselectedContinuationRank")!=FIRST: raise SystemExit("REFUSED: W80 next continuation rank")
    inv_raw=git("show",f"{HEAD}:{INV_PATH}")
    if inv_raw!=(REPO/INV_PATH).read_bytes(): raise SystemExit("REFUSED: inventory differs from exact HEAD")
    inv=[json.loads(x) for x in inv_raw.decode().splitlines() if x.strip()]
    if len(inv)!=6176: raise SystemExit("REFUSED: inventory row count")
    by_id={r["sourceId"]:r for r in inv}; by_rank={r["continuationRank"]:r for r in inv if r.get("continuationRank") is not None}
    if len(by_id)!=len(inv): raise SystemExit("REFUSED: duplicate source ids")
    for r in inv:
        if r["sourceId"]!="src_"+tsha(r["source"])[:16] or r["sourceSha256"]!=tsha(r["source"]): raise SystemExit("REFUSED: source inventory id/hash")
    selected=[by_rank[n] for n in range(FIRST,LAST+1)]
    if len(selected)!=25 or any(r.get("excluded") or r.get("localeCoverage")!=12 for r in selected): raise SystemExit("REFUSED: selected range incomplete")
    if [r["remainingQueueRank"] for r in selected]!=list(range(803,828)): raise SystemExit("REFUSED: W81 remaining queue rank mismatch")
    if selected[0]["sourceId"]!=prev_boundary["nextUnselectedSourceId"]: raise SystemExit("REFUSED: W80/W81 boundary source mismatch")

    old_ids=jlines(PREV/"prior-selected-id-exclusions-hash-only.jsonl")
    prev_sel_rows=[]
    for r in prev_selected:
        prev_sel_rows.append({"sourceId":r["sourceId"],"sourceIdSha256":tsha(r["sourceId"]),"sourceSha256":r["sourceSha256"],
                              "selectionOrigin":"W80 candidate-free continuation selection","continuationRank":r["continuationRank"],
                              "remainingQueueRank":r["remainingQueueRank"],"exclusionConfirmed":True,"sourceTextIncluded":False,"targetTextIncluded":False,
                              "selectionEvidenceSha256":sha((PREV/"selection-and-boundary.json").read_bytes())})
    all_ids=sorted(old_ids+prev_sel_rows,key=lambda r:r["sourceId"])
    if len(all_ids)!=1982 or len({r["sourceId"] for r in all_ids})!=len(all_ids): raise SystemExit("REFUSED: prior selected id continuity")
    if any(forbidden(r) for r in all_ids): raise SystemExit("REFUSED: source text in prior selection ledger")
    for r in all_ids:
        now=by_id.get(r["sourceId"])
        if not now or now["sourceSha256"]!=r["sourceSha256"]: raise SystemExit("REFUSED: prior selected source drift")
    if {r["sourceId"] for r in all_ids}&{r["sourceId"] for r in selected}: raise SystemExit("REFUSED: selected source already reviewed")

    tree=tree_entries(); cats,catalog_rows,ordered=load_catalogs(tree)
    runtime=[]
    for path,entry in sorted(tree.items()):
        if not prod_path(path): continue
        data=(REPO/path).read_bytes()
        if blob_sha(data)!=entry["gitBlob"]: raise SystemExit("REFUSED: exact runtime blob "+path)
        runtime.append({"path":path,"bytes":len(data),"sha256":sha(data),"gitBlob":entry["gitBlob"]})
    if len(runtime)!=279: raise SystemExit("REFUSED: runtime file count")

    old_holds=jlines(PREV/"previous-window-prior-holds-hash-only.jsonl")
    old_resolutions=jlines(PREV/"prior-hold-resolution-history-hash-only.jsonl")
    old_lineage=jread(PREV/"prior-hold-lineage-summary.json")
    if len(old_holds)!=382 or len(old_resolutions)!=13: raise SystemExit("REFUSED: W80 hold lineage counts")
    app_plan_raw=git("show",f"{HEAD}:{APP_PREFIX}application-plan.jsonl")
    product_raw=git("show",f"{HEAD}:{APP_PREFIX}product-commit.json")
    app_summary_raw=git("show",f"{HEAD}:{APP_PREFIX}application-summary.json")
    app_plan=[json.loads(x) for x in app_plan_raw.decode().splitlines() if x.strip()]
    product=json.loads(product_raw.decode()); app_summary=json.loads(app_summary_raw.decode())
    if (len(app_plan),product.get("commit"),product.get("parent"),product.get("insertions"),product.get("deletions"),app_summary.get("proposalCount"),app_summary.get("keepCount"),app_summary.get("newHoldCount"))!=(81,W80_PRODUCT,"7a1ca27fd0519674c3b42a3e3df3638b0f671567",81,81,81,219,0):
        raise SystemExit("REFUSED: W80 committed application summary")
    if product.get("changedPathsLimitedToLocaleCatalogs") is not True or app_summary.get("workflowPathsChanged")!=0:
        raise SystemExit("REFUSED: W80 product scope/workflow")
    subprocess.check_call(["git","-C",str(REPO),"merge-base","--is-ancestor",W80_PRODUCT,HEAD],stdout=subprocess.DEVNULL)
    if len(old_lineage.get("holdLineage",{}))==0: raise SystemExit("REFUSED: empty prior hold lineage")
    w80_application_sha=sha(app_plan_raw); w80_product_sha=sha(product_raw)
    w80_callers={r["sourceId"]:r for r in jlines(PREV/"caller-contexts.jsonl")}
    new_hold_inputs=[] # W80 added no new holds.
    previous_holds=old_holds
    if any(forbidden(r) for r in previous_holds+old_resolutions): raise SystemExit("REFUSED: text in prior hold lineage")

    # Scan every selected source plus active holds and historical resolutions at exact W81 tree.
    source_ids={r["sourceId"] for r in selected}|{r["sourceId"] for r in previous_holds}|{r["sourceId"] for r in old_resolutions}
    full_refs={sid:refs_for(by_id[sid]["source"],runtime) for sid in sorted(source_ids)}
    caller_rows=[]
    for r in selected:
        refs=full_refs[r["sourceId"]]
        caller={"continuationRank":r["continuationRank"],"remainingQueueRank":r["remainingQueueRank"],"sourceId":r["sourceId"],
                "sourceSha256":r["sourceSha256"],"productionCallerCount":len(refs),
                "boundedScan":"Exact single- or double-quoted source literal scan of pinned src/web/src JS/TS runtime files; test/spec files excluded.",
                "callers":refs,"sourceTextIncluded":bool(refs)}
        if refs: caller["source"]=r["source"]
        caller_rows.append(caller)

    hold_attest=[]; hold_counts=collections.Counter()
    for old in previous_holds:
        src=by_id.get(old["sourceId"]); locale=old["locale"]
        if not src or src["sourceSha256"]!=old["sourceSha256"] or locale not in cats: raise SystemExit("REFUSED: prior hold identity")
        refs=full_refs[old["sourceId"]]; ctx=sha(canon(refs)); target=cats[locale][src["source"]]; th=tsha(target)
        same_ctx=ctx==old["currentCallerContextSha256"]; same_target=th==old["priorTargetSha256"]
        status="reattested-unchanged" if same_ctx and same_target else "reattested-context-or-target-changed"
        hold_counts[status]+=1; cat=next(c for c in catalog_rows if c["locale"]==locale)
        hold_attest.append({"priorWindow":old["priorWindow"],"continuationRank":old["continuationRank"],"sourceId":old["sourceId"],
                            "sourceIdSha256":old["sourceIdSha256"],"sourceSha256":old["sourceSha256"],"locale":locale,
                            "priorDisposition":"hold","priorTargetSha256":old["priorTargetSha256"],"currentTargetSha256":th,
                            "matchesPriorCurrentValue":same_target,"holdReasonSha256":old.get("holdReasonSha256"),
                            "priorCallerCount":old["currentCallerCount"],"priorCallerContextSha256":old["currentCallerContextSha256"],
                            "priorCallerRefs":old["currentCallerRefs"],"currentCallerCount":len(refs),"currentCallerContextSha256":ctx,
                            "currentCallerRefs":hash_refs(refs),"callerEvidenceUnchanged":same_ctx,"currentCatalogPath":cat["catalogPath"],
                            "currentCatalogFileSha256":cat["sha256"],"currentCatalogGitBlob":cat["gitBlob"],"status":status,
                            "sourceTextIncluded":False,"targetTextIncluded":False})
    resolution_attest=[]
    for old in old_resolutions:
        src=by_id.get(old["sourceId"]); locale=old["locale"]
        if not src or src["sourceSha256"]!=old["sourceSha256"] or locale not in cats: raise SystemExit("REFUSED: hold resolution identity")
        refs=full_refs[old["sourceId"]]; current_hash=tsha(cats[locale][src["source"]]); cat=next(c for c in catalog_rows if c["locale"]==locale)
        row={k:v for k,v in old.items() if k not in {"source","sourceText","target","currentTarget","proposedTarget","resolvedTargetText","formerTargetText"}}
        row.update({"currentTargetSha256":current_hash,"currentTargetMatchesResolution":current_hash==old["resolvedTargetSha256"],
                    "currentCallerCount":len(refs),"currentCallerContextSha256":sha(canon(refs)),"currentCallerRefs":hash_refs(refs),
                    "currentCatalogPath":cat["catalogPath"],"currentCatalogFileSha256":cat["sha256"],"currentCatalogGitBlob":cat["gitBlob"],
                    "sourceTextIncluded":False,"formerTargetTextIncluded":False,"resolvedTargetTextIncluded":False,"currentTargetTextIncluded":False})
        if forbidden(row): raise SystemExit("REFUSED: text in resolution reattestation")
        resolution_attest.append(row)

    prior_applied=jlines(PREV/"prior-applied-targets-reattestation-hash-only.jsonl")
    if len(prior_applied)!=109 or any(forbidden(r) for r in prior_applied): raise SystemExit("REFUSED: W80 prior applied target lineage")
    applied=[]
    for old in prior_applied:
        src=by_id.get(old["sourceId"]); locale=old["locale"]
        if not src or src["sourceSha256"]!=old["sourceSha256"] or locale not in cats: raise SystemExit("REFUSED: prior applied target identity")
        th=tsha(cats[locale][src["source"]])
        if th!=old["appliedTargetSha256"]: raise SystemExit("REFUSED: historical applied target no longer present")
        cat=next(c for c in catalog_rows if c["locale"]==locale)
        row=dict(old); row.update({"attestedAtHead":HEAD,"currentTargetSha256":th,"targetRemainsApplied":True,
                                  "currentCatalogFileSha256":cat["sha256"],"currentCatalogGitBlob":cat["gitBlob"],
                                  "sourceTextIncluded":False,"targetTextIncluded":False})
        applied.append(row)
    new_applied=[]; app_plan_sha=sha(app_plan_raw); catalog_by_locale={c["locale"]:c for c in catalog_rows}
    for r in app_plan:
        src=by_id.get(r["sourceId"]); locale=r["locale"]
        if not src or src["sourceSha256"]!=r["sourceSha256"] or r["catalogPath"]!=f"src/web/public/locales/{locale}.json" or r["catalogKey"]!=src["source"]:
            raise SystemExit("REFUSED: W80 application plan source")
        if tsha(r["target"])!=r["targetSha256"]: raise SystemExit("REFUSED: W80 applied target hash")
        th=tsha(cats[locale][src["source"]])
        if th!=r["targetSha256"]: raise SystemExit("REFUSED: W80 target not present at W81")
        cat=catalog_by_locale[locale]
        new_applied.append({"priorWindow":"W80","appliedHead":HEAD,"productCommit":W80_PRODUCT,"applicationPlanSha256":app_plan_sha,
                            "continuationRank":r["continuationRank"],"remainingQueueRank":r["remainingQueueRank"],"sourceId":r["sourceId"],
                            "sourceIdSha256":r["sourceIdSha256"],"sourceSha256":r["sourceSha256"],"locale":locale,"catalogPath":r["catalogPath"],
                            "priorCurrentTargetSha256":r["currentTargetSha256"],"appliedTargetSha256":r["targetSha256"],"currentTargetSha256":th,
                            "targetRemainsApplied":True,"currentCatalogFileSha256":cat["sha256"],"currentCatalogGitBlob":cat["gitBlob"],
                            "sourceTextIncluded":False,"targetTextIncluded":False})
    if len(new_applied)!=81 or len(applied)+len(new_applied)!=190: raise SystemExit("REFUSED: cumulative applied-target counts")
    if any(forbidden(r) for r in applied+new_applied): raise SystemExit("REFUSED: source/target text in applied history")

    cells=[]; mismatch=collections.Counter(); mismatch_examples=[]
    for source in selected:
        sid,source_text=source["sourceId"],source["source"]; refs=full_refs[sid]; compact=hash_refs(refs); ctx=sha(canon(refs))
        for locale in LOCALES:
            current=cats[locale][source_text]; sph,cph=ph(source_text),ph(current); st,ct=tags(source_text),tags(current)
            sn,cn=nums(source_text),nums(current); sp=protected(source_text); present=[x for x in sp if x in current]
            oks={"placeholder":sph==cph,"markup":st==ct,"numeric":not_less(sn,cn),"protectedLiteral":all(x in current for x in sp)}
            for kind,ok in oks.items():
                if not ok: mismatch[kind]+=1; mismatch_examples.append({"continuationRank":source["continuationRank"],"sourceId":sid,"locale":locale,"kind":kind})
            cat=catalog_by_locale[locale]
            row={"continuationRank":source["continuationRank"],"remainingQueueRank":source["remainingQueueRank"],"sourceId":sid,
                 "sourceSha256":source["sourceSha256"],"locale":locale,"catalogPath":cat["catalogPath"],"catalogFileSha256":cat["sha256"],
                 "catalogGitBlob":cat["gitBlob"],"currentTargetSha256":tsha(current),"callerContextSha256":ctx,"callerRefs":compact,
                 "sourceTextIncluded":bool(refs),"currentTargetTextIncluded":bool(refs),"containsCandidate":False,"verdict":None}
            if refs:
                row.update({"source":source_text,"catalogKey":source_text,"currentTarget":current,
                            "placeholderEvidence":{"sourceTokens":sorted(sph.elements()),"currentTokens":sorted(cph.elements()),"matches":oks["placeholder"]},
                            "markupEvidence":{"sourceTags":sorted(st.elements()),"currentTags":sorted(ct.elements()),"matches":oks["markup"]},
                            "sourceNumericTokens":sn,"currentNumericTokens":cn,"numericTokensPreserved":oks["numeric"],
                            "sourceProtectedLiterals":sp,"currentProtectedLiterals":present,"missingProtectedLiterals":[x for x in sp if x not in current],
                            "protectedLiteralEvidence":{"sourceTokens":sp,"currentTokens":present,"matches":oks["protectedLiteral"]}})
            else:
                row["tokenEvidenceSha256"]=sha(canon({"placeholderParity":oks["placeholder"],"markupParity":oks["markup"],
                                                       "numericTokensPreserved":oks["numeric"],"protectedLiteralsPreserved":oks["protectedLiteral"]}))
            cells.append(row)
    if len(cells)!=300: raise SystemExit("REFUSED: W81 source-cell coverage")
    boundary_prev,boundary_next=by_rank[902],by_rank[928]
    def boundary_row(r,role):
        return {"continuationRank":r["continuationRank"],"remainingQueueRank":r["remainingQueueRank"],"sourceId":r["sourceId"],
                "sourceSha256":r["sourceSha256"],"localeCoverage":r["localeCoverage"],"excluded":r.get("excluded",False),
                "boundaryRole":role,"sourceTextIncluded":False}
    boundary=[boundary_row(boundary_prev,"previous-window-final")]+[boundary_row(r,"selected-window") for r in selected]+[boundary_row(boundary_next,"next-unselected")]
    selection_rows=[{"continuationRank":r["continuationRank"],"remainingQueueRank":r["remainingQueueRank"],"sourceId":r["sourceId"],
                     "sourceSha256":r["sourceSha256"],"localeCoverage":r["localeCoverage"],"excluded":False,"sourceTextIncluded":False} for r in selected]
    inv_projection=[{k:r[k] for k in ("sourceId","sourceSha256","continuationRank","remainingQueueRank","localeCoverage","excluded") if k in r} for r in inv]
    wjsonl("source-inventory-pinned.jsonl",inv_projection); wjsonl("source-inventory-selection.jsonl",selection_rows)
    wjsonl("selected-sources.jsonl",[{"continuationRank":r["continuationRank"],"remainingQueueRank":r["remainingQueueRank"],"sourceId":r["sourceId"],
                                     "sourceSha256":r["sourceSha256"],"source":r["source"]} for r in selected])
    wjsonl("selection-boundary.jsonl",boundary); wjsonl("catalog-structure.jsonl",catalog_rows)
    wjsonl("runtime-file-pins.jsonl",runtime); wjsonl("caller-contexts.jsonl",caller_rows); wjsonl("source-current-cells.jsonl",cells)
    wjsonl("prior-selected-id-exclusions-hash-only.jsonl",all_ids)
    wjsonl("previous-window-selection-hash-only.jsonl",prev_sel_rows)
    wjsonl("previous-window-prior-holds-hash-only.jsonl",previous_holds)
    wjsonl("previous-window-holds-hash-only.jsonl",new_hold_inputs)
    wjsonl("prior-held-cell-reattestation-hash-only.jsonl",hold_attest)
    wjsonl("prior-hold-resolution-history-hash-only.jsonl",resolution_attest)
    wjsonl("previous-window-applied-targets-hash-only.jsonl",new_applied)
    wjsonl("prior-applied-targets-reattestation-hash-only.jsonl",applied+new_applied)
    (ROOT/"previous-window-product-commit.json").write_bytes(product_raw)
    wjson("previous-window-application-summary.json",{k:app_summary[k] for k in ("artifact","window","baseHead","baseTree","proposalCount","keepCount","newHoldCount","priorW79HoldsRetained","readbackCellCount","catalogCount","catalogKeyCountPerLocale","catalogKeyOrderUnchanged","workflowPathsChanged","testsBuildsScansCiRun") if k in app_summary}|{"applicationPlanSha256":app_plan_sha,"sourceTextIncluded":False,"targetTextIncluded":False})
    lineage=dict(old_lineage.get("holdLineage",{}))
    wjson("prior-hold-lineage-summary.json",{"carriedHoldCells":len(previous_holds),"holdLineage":lineage,"previouslyResolvedHistoricalRows":len(old_resolutions),
         "resolutionRowsTextFree":True,"W80NewHolds":0})
    wjson("prior-held-cell-reattestation-summary.json",{"priorHeldCellsReattested":len(hold_attest),
         "allTargetHashesMatchPrior":all(r["matchesPriorCurrentValue"] for r in hold_attest),
         "callerEvidenceUnchanged":sum(r["callerEvidenceUnchanged"] for r in hold_attest),
         "callerEvidenceChanged":sum(not r["callerEvidenceUnchanged"] for r in hold_attest),
         "statusCounts":dict(hold_counts),"holdRowsTextFree":True})
    wjson("prior-applied-targets-summary.json",{"priorAppliedTargetsReattested":len(applied+new_applied),
         "allTargetsRemainApplied":all(r["targetRemainsApplied"] for r in applied+new_applied),
         "windows":{"priorThroughW79":len(applied),"W80":len(new_applied)},"targetTextIncluded":False,"sourceTextIncluded":False})
    wjson("baseline-token-mismatch-summary.json",{"cellCount":len(cells),"mismatchCellCount":sum(mismatch.values()),
         "mismatchCounts":{k:mismatch.get(k,0) for k in ("placeholder","markup","numeric","protectedLiteral")},"mismatchExamples":mismatch_examples})
    wjson("continuity-provenance.json",{"previousWindow":"W80","previousHead":prev_manifest["head"],"previousTree":prev_manifest["tree"],
         "previousManifestSha256":prev_manifest_sha,"previousPacketChecksumListSha256":prev_sums_sha,
         "priorSelectedIdExclusionRows":len(all_ids),"W80SelectedIdsAdded":len(prev_sel_rows),"priorHeldCells":len(hold_attest),
         "W80NewHoldsAdded":0,"priorResolvedHoldHistoryRows":len(resolution_attest),"priorAppliedTargetsReattested":len(applied+new_applied),
         "W80AppliedTargetsAdded":len(new_applied),"priorSelectedIdsSha256":sha((ROOT/"prior-selected-id-exclusions-hash-only.jsonl").read_bytes()),
         "activeHoldLedgerSha256":sha((ROOT/"previous-window-prior-holds-hash-only.jsonl").read_bytes()),
         "priorHoldReattestationSha256":sha((ROOT/"prior-held-cell-reattestation-hash-only.jsonl").read_bytes()),
         "priorResolutionReattestationSha256":sha((ROOT/"prior-hold-resolution-history-hash-only.jsonl").read_bytes()),
         "w80ApplicationPlanSha256":app_plan_sha,"w80ProductCommitSha256":sha(product_raw),
         "w80AppliedTargetHashLedgerSha256":sha((ROOT/"previous-window-applied-targets-hash-only.jsonl").read_bytes()),
         "sourceTextIncluded":False,"targetTextIncluded":False,"previousPrimaryReviewTargetsUsed":False,"blindReviewUsed":False,"crossReviewUsed":False,"prBodyQueried":False})
    wjson("selection-and-boundary.json",{"repository":"snapetech-org/slskdN","pullRequest":409,"window":"W81","branch":BRANCH,"head":HEAD,"tree":TREE,
         "candidateFree":True,"locales":LOCALES,"sourceCount":25,"cellCount":300,"continuationRankRange":[FIRST,LAST],"remainingQueueRankRange":[803,827],
         "previousWindow":"W80","previousWindowFinalContinuationRank":902,"previousWindowFinalSourceId":boundary_prev["sourceId"],
         "firstSelectedSourceId":selected[0]["sourceId"],"nextUnselectedContinuationRank":928,"nextUnselectedSourceId":boundary_next["sourceId"],
         "orderedCatalogKeySha256":sha(("\n".join(ordered)+"\n").encode()),"catalogEntryCountPerLocale":6176,
         "priorSelectedIdsExcluded":len(all_ids),"priorHeldCellsReattested":len(hold_attest),"priorHoldResolutionHistoryRows":len(resolution_attest),
         "priorAppliedTargetsReattested":len(applied+new_applied),"proposedTargetsIncluded":False,"reviewDecisionsIncluded":False})
    wjson("source-tree-attestation.json",{"head":HEAD,"tree":TREE,"sourceRoot":"src/web/src","treeEnumeration":"git ls-tree -r -z at exact pinned commit",
         "treeEntryCount":len(tree),"productionFileCount":len(runtime),"sourceInventoryPath":INV_PATH,"sourceInventoryRawSha256":sha(inv_raw),
         "sourceInventoryProjectionSha256":sha((ROOT/"source-inventory-pinned.jsonl").read_bytes()),
         "callerScan":"Exact single- or double-quoted source literal scan","testAndSpecFilesExcluded":True,
         "runtimeFilePinsSha256":sha((ROOT/"runtime-file-pins.jsonl").read_bytes())})
    wjson("head-tree-attestation.json",{"head":HEAD,"tree":TREE,"liveBefore":live_before,"mainDriftBefore":drift_before,
         "prBodyQueried":False,"sourceWorktreeClean":True})
    drift=jread(ROOT/"main-drift.json")
    wjson("main-drift.json",drift)
    manifest={"artifact":"slskdN PR #409 W903-W927 ranks candidate-free exact-head input","schemaVersion":1,
         "repository":"snapetech-org/slskdN","pullRequest":409,"branch":BRANCH,"window":"W81","candidateFree":True,"head":HEAD,"tree":TREE,
         "continuationRankRange":[FIRST,LAST],"remainingQueueRankRange":[803,827],"sourceCount":25,"localeCount":12,"cellCount":300,
         "locales":LOCALES,"catalogEntryCountPerLocale":6176,"sourceInventoryPath":INV_PATH,"sourceInventoryRows":len(inv),
         "sourceInventorySha256":sha(inv_raw),"sourceInventoryProjectionSha256":sha((ROOT/"source-inventory-pinned.jsonl").read_bytes()),
         "orderedCatalogKeySha256":sha(("\n".join(ordered)+"\n").encode()),"productionCallerFileCount":len(runtime),
         "sourcesWithCallers":sum(bool(r["productionCallerCount"]) for r in caller_rows),
         "sourcesWithoutCallers":sum(not r["productionCallerCount"] for r in caller_rows),
         "priorSelectedIdsExcluded":len(all_ids),"priorHeldCellsReattested":len(hold_attest),
         "priorHoldResolutionHistoryRows":len(resolution_attest),"priorAppliedTargetsReattested":len(applied+new_applied),
         "priorAppliedTargetsByWindow":{"priorThroughW79":len(applied),"W80":len(new_applied)},
         "previousWindowHolds":0,"activePriorHoldCount":len(previous_holds),
         "priorHoldLineage":lineage,"priorHeldTargetHashesAllMatch":all(r["matchesPriorCurrentValue"] for r in hold_attest),
         "priorHeldCallerEvidenceUnchanged":sum(r["callerEvidenceUnchanged"] for r in hold_attest),
         "priorHeldCallerEvidenceChanged":sum(not r["callerEvidenceUnchanged"] for r in hold_attest),
         "baselineTokenMismatchSummary":{k:mismatch.get(k,0) for k in ("placeholder","markup","numeric","protectedLiteral")},
         "proposedTargetsIncluded":False,"reviewDecisionsIncluded":False,"blindReviewUsed":False,"crossReviewUsed":False,"prBodyQueried":False,
         "liveMainBefore":live_before["liveMainSha"],"mainDriftSha256":sha((ROOT/"main-drift.json").read_bytes()),
         "continuityProvenanceSha256":sha((ROOT/"continuity-provenance.json").read_bytes()),"files":[]}
    wjson("manifest.json",manifest)
    print(json.dumps({"result":"BUILT-CANDIDATE-FREE-UNSEALED","head":HEAD,"tree":TREE,"sourceCount":25,"localeCount":12,"cellCount":300,
         "runtimeFiles":len(runtime),"sourcesWithCallers":sum(bool(r["productionCallerCount"]) for r in caller_rows),
         "sourcesWithoutCallers":sum(not r["productionCallerCount"] for r in caller_rows),"priorSelectedIds":len(all_ids),
         "priorHeldCells":len(hold_attest),"priorHoldResolutions":len(resolution_attest),"priorAppliedTargets":len(applied+new_applied),
         "holdReattestationStatuses":dict(hold_counts),"tokenMismatches":{k:mismatch.get(k,0) for k in ("placeholder","markup","numeric","protectedLiteral")},
         "liveMain":live_before["liveMainSha"],"mainLocalizationChanges":drift.get("localizationOrCatalogChanges"),"prBodyQueried":False},ensure_ascii=False,indent=2))

if __name__ == "__main__": main()

