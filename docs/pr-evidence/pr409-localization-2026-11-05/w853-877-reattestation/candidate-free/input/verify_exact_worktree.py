#!/usr/bin/env python3
"""Exact Git worktree verifier for the candidate-free slskdN packet."""
import collections, hashlib, json, re, subprocess, sys, unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parent
HEAD="cc600880606f374cebe3082789fa50f246ff614f"
TREE="440b9842d914a391f77cbb03737261b8798cc6e3"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
TEXT_KEYS={"source","sourceText","target","currentTarget","proposedTarget","proposedTargetText","candidateTarget","reviewTarget","rationale","reason"}
def need(ok,msg):
    if not ok: raise SystemExit("FAIL: "+msg)
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode("utf-8"))
def blobsha(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
def readj(name): return json.loads((ROOT/name).read_text(encoding="utf-8"))
def readjl(name): return [json.loads(x) for x in (ROOT/name).read_text(encoding="utf-8").splitlines() if x.strip()]
def git(repo,*args): return subprocess.check_output(["git","-C",str(repo),*args])
def production_path(path):
    parts=path.split("/"); name=parts[-1]
    return path.startswith("src/web/src/") and Path(path).suffix.lower() in {".js",".jsx",".ts",".tsx"} and not any(p in {"__tests__","__specs__"} for p in parts) and not any(x in name for x in (".test.",".spec."))
def token_data(source,target):
    placeholders=lambda s: collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}",s))
    tags=lambda s: collections.Counter(re.findall(r"</?[A-Za-z][^>]*>",s))
    nums=lambda s:["".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in tok) for tok in re.findall(r"\d+",s)]
    protected=lambda s:sorted(set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b",s)) | {x for x in ("slskdN","PodCore","Wishlist","soulfind","FFmpeg","Lidarr") if x in s})
    sp,tp=placeholders(source),placeholders(target); st,tt=tags(source),tags(target)
    sn,tn=nums(source),nums(target); sl,tl=protected(source),protected(target)
    return {"placeholders":{"source":sorted(sp.elements()),"target":sorted(tp.elements()),"matches":sp==tp},
      "markup":{"source":sorted(st.elements()),"target":sorted(tt.elements()),"matches":st==tt},
      "numbers":{"source":sn,"target":tn,"sourcePreserved":all(tn.count(x)>=n for x,n in collections.Counter(sn).items())},
      "protectedLiterals":{"source":sl,"target":tl,"missing":[x for x in sl if x not in target]}}
def main():
    if len(sys.argv)!=2: raise SystemExit("usage: verify_exact_worktree.py /path/to/exact-worktree")
    repo=Path(sys.argv[1]).resolve(); need(repo.is_dir(),"worktree path")
    need(git(repo,"rev-parse","HEAD").decode().strip()==HEAD,"worktree HEAD")
    need(git(repo,"rev-parse","HEAD^{tree}").decode().strip()==TREE,"worktree tree")
    need(not git(repo,"status","--porcelain=v1").decode().strip(),"worktree must be clean")
    m=readj("manifest.json"); need(m["head"]==HEAD and m["tree"]==TREE,"packet pin")
    need(git(repo,"rev-parse",m["baseSha"]+"^{tree}").decode().strip()==m["baseTree"],"base tree object")
    raw_tree=git(repo,"ls-tree","-r","-z",HEAD); tree={}
    for item in raw_tree.split(b"\0"):
        if not item: continue
        meta,path=item.split(b"\t",1); mode,kind,oid=meta.decode().split()
        tree[path.decode()]={"mode":mode,"kind":kind,"gitBlob":oid}
    catalog_struct=readjl("catalog-structure.jsonl"); need(len(catalog_struct)==12,"catalog structure rows")
    catalogs={}; ordered=None
    for pin in catalog_struct:
        path=pin["path"]; data=(repo/path).read_bytes()
        need(blobsha(data)==tree[path]["gitBlob"]==pin["gitBlob"],"catalog Git blob: "+pin["locale"])
        need(sha(data)==pin["sha256"] and len(data)==pin["bytes"],"catalog SHA/size: "+pin["locale"])
        dup=[]
        def pairs(ps):
            d={}
            for k,v in ps:
                if k in d: dup.append(k)
                d[k]=v
            return d
        obj=json.loads(data.decode("utf-8"),object_pairs_hook=pairs)
        need(not dup and len(obj)==6175,"catalog JSON/order/count: "+pin["locale"])
        keys=list(obj)
        if ordered is None: ordered=keys
        else: need(keys==ordered,"locale key order: "+pin["locale"])
        need(sha(("\n".join(keys)+"\n").encode())==pin["orderedKeySha256"],"catalog ordered key hash: "+pin["locale"])
        catalogs[pin["locale"]]=obj
    need(set(catalogs)==set(LOCALES),"locale set")
    source_by_id={"src_"+tsha(source)[:16]:source for source in ordered}
    need(len(source_by_id)==6175,"source ID collision")
    ordered_att=readj("catalog-key-order-attestation.json")
    need(ordered_att["entryCount"]==6175 and ordered_att["orderedKeySha256"]==sha(("\n".join(ordered)+"\n").encode()),"ordered source attestation")
    need(ordered_att["sourceIdOrderSha256"]==sha(b"".join(bytes.fromhex(tsha(k)) for k in ordered)),"source ID order attestation")
    need(ordered_att["sourceRecordOrderSha256"]==sha(b"".join(bytes.fromhex(tsha("src_"+tsha(k)[:16]))+bytes.fromhex(tsha(k)) for k in ordered)),"source record order attestation")
    selected=readjl("source-inventory-selection.jsonl"); full=readjl("selected-sources.jsonl")
    need(len(selected)==len(full)==25,"selected source count")
    byid={r["sourceId"]:r for r in selected}; need(len(byid)==25,"selected source IDs unique")
    need([r["continuationRank"] for r in selected]==list(range(953,978)) and [r["remainingQueueRank"] for r in selected]==list(range(853,878)),"rank mapping")
    source_rows={r["sourceId"]:r for r in full}
    for s in selected:
        source=source_by_id.get(s["sourceId"]); need(source is not None and tsha(source)==s["sourceSha256"],"selected current English source")
        v=source_rows[s["sourceId"]]; need(v["sourceIdSha256"]==tsha(v["sourceId"]) and v["sourceSha256"]==tsha(source),"selected source hashes")
        held=s["continuationRank"]==966
        if held: need("source" not in v and v.get("sourceTextIncluded") is False,"held selected text exposure")
        else: need(v.get("source")==source and v.get("sourceTextIncluded") is True,"selected source text")
    inventory=readjl("source-inventory-pinned.jsonl"); need(len(inventory)==6175,"source inventory count")
    inv={r["sourceId"]:r for r in inventory}; need(set(inv)==set(source_by_id),"source inventory ID coverage")
    for sid,source in source_by_id.items(): need(inv[sid]["sourceSha256"]==tsha(source),"source inventory hash")
    runtime=readjl("runtime-file-pins.jsonl"); need(len(runtime)==279,"runtime file count")
    expected={p for p,v in tree.items() if production_path(p)}; need(expected=={r["path"] for r in runtime},"runtime file path set")
    runtime_data={}
    for pin in runtime:
        p=pin["path"]; data=(repo/p).read_bytes()
        need(blobsha(data)==tree[p]["gitBlob"]==pin["gitBlob"] and sha(data)==pin["sha256"] and len(data)==pin["bytes"],"runtime file pin: "+p)
        runtime_data[p]=data.decode("utf-8").splitlines()
    cells=readjl("source-current-cells.jsonl"); need(len(cells)==300,"current 300-cell inventory")
    bycell={(r["sourceId"],r["locale"]):r for r in cells}; need(len(bycell)==300,"current cell duplicate")
    need(set(r["locale"] for r in cells)==set(LOCALES),"current cell locales")
    callers=readjl("caller-contexts.jsonl"); need(len(callers)==25,"caller source rows")
    callers_by={r["sourceId"]:r for r in callers}; need(set(callers_by)==set(byid),"caller source IDs")
    def get_refs(source):
        literal=re.compile(r"(?<![A-Za-z0-9_$])([\"'])"+re.escape(source)+r"\1")
        refs=[]
        for pin in runtime:
            lines=runtime_data[pin["path"]]
            for idx,line in enumerate(lines):
                if not literal.search(line): continue
                context=[{"line":n+1,"text":lines[n]} for n in range(max(0,idx-4),min(len(lines),idx+3))]
                refs.append({"path":pin["path"],"line":idx+1,"lineText":line,"lineSha256":tsha(line),
                  "context":context,"contextSha256":sha(canon(context)),"fileBytes":pin["bytes"],
                  "fileSha256":pin["sha256"],"gitBlob":pin["gitBlob"]})
        return refs
    token_mismatch=collections.Counter()
    for sid,s in byid.items():
        source=source_by_id[sid]; hold=s["continuationRank"]==966
        refs=get_refs(source); cr=callers_by[sid]
        need(len(refs)==cr["productionCallerCount"] and sha(canon(refs))==cr["callerContextSha256"],"exact caller context hash: "+sid)
        if hold:
            projected=[{k:r[k] for k in ("path","line","lineSha256","contextSha256","fileSha256","gitBlob")} for r in refs]
            need(projected==cr["callerRefsHashOnly"] and cr.get("sourceTextIncluded") is False and "callers" not in cr,"hash-only held caller refs")
        else:
            need(refs==cr["callers"] and cr["source"]==source,"caller context content")
        for locale in LOCALES:
            c=bycell[(sid,locale)]; target=catalogs[locale][source]; target_hash=tsha(target)
            need(c["sourceSha256"]==tsha(source) and c["currentTargetSha256"]==target_hash,"current catalog source/target hash")
            need(c["callerContextSha256"]==cr["callerContextSha256"] and c["callerCount"]==len(refs),"cell caller pin")
            evidence=token_data(source,target)
            pass_all=evidence["placeholders"]["matches"] and evidence["markup"]["matches"] and evidence["numbers"]["sourcePreserved"] and not evidence["protectedLiterals"]["missing"]
            need(c["tokenChecksPass"] is pass_all,"cell token status")
            if not pass_all: token_mismatch["mismatch"]+=1
            if hold:
                need(not(set(c)&TEXT_KEYS) and c["sourceTextIncluded"] is False and c["currentTargetTextIncluded"] is False,"held cell text exposure")
            else:
                need(c["source"]==source and c["currentTarget"]==target and sha(canon(evidence))==c["tokenEvidenceSha256"] and evidence==c["tokenEvidence"],"current cell text/token evidence")
    need(not token_mismatch,"current source/target token mismatch")
    for fn in ("prior-held-cell-reattestation-hash-only.jsonl","prior-applied-targets-reattestation-hash-only.jsonl"):
        rows=readjl(fn)
        for r in rows:
            source=source_by_id.get(r["sourceId"])
            need(source is not None and tsha(source)==r["sourceSha256"],"historical cell source reattestation")
            target_hash=tsha(catalogs[r["locale"]][source])
            expected_hash=r["currentTargetSha256"] if "currentTargetSha256" in r else r["appliedTargetSha256"]
            need(target_hash==expected_hash,"historical cell current target hash")
    resolutions=readjl("prior-hold-resolution-history-hash-only.jsonl")
    need(len(resolutions)==25,"resolution history count")
    for r in resolutions:
        source=source_by_id.get(r["sourceId"])
        if source is None:
            need(r["currentSourcePresent"] is False and r["currentTargetSha256"] is None,"absent historical source status")
        else:
            need(r["currentSourcePresent"] is True and tsha(source)==r["sourceSha256"],"historical resolution source hash")
            need(tsha(catalogs[r["locale"]][source])==r["currentTargetSha256"]==r["resolvedTargetSha256"],"historical resolution current target")
    readback=readjl("window-application-readback-hash-only.jsonl"); applied=readjl("window-applied-targets-reattestation-hash-only.jsonl"); holds=readjl("window-holds-hash-only.jsonl")
    need(len(readback)==300 and len(applied)==288 and len(holds)==12,"window readback counts")
    for r in readback:
        sid=next(x for x in selected if x["continuationRank"]==r["continuationRank"])["sourceId"]
        source=source_by_id[sid]; target_hash=tsha(catalogs[r["locale"]][source])
        need(r["currentCatalogTargetSha256"]==target_hash==r["rootObservedAfterSha256"] and r["readbackMatchesCurrent"],"application readback/current catalog")
    changed=git(repo,"diff","--name-only",m["baseSha"],HEAD).decode().splitlines()
    need(not any(path.startswith(".github/workflows/") for path in changed),"workflow tree diff")
    subprocess.run([sys.executable,"-B",str(ROOT/"verify_candidate_free.py")],check=True,cwd=ROOT)
    print(json.dumps({"result":"PASS","verifier":"exact-worktree","head":HEAD,"tree":TREE,"sourceIds":25,"cells":300,"catalogs":12,"runtimeFiles":279,"callerReferences":sum(x["productionCallerCount"] for x in callers),"applied":len(applied),"hashOnlyHolds":len(holds)},indent=2))
if __name__=="__main__": main()
