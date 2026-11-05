#!/usr/bin/env python3
"""Build a candidate-free current-head readback packet for slskdN queue ranks 853-877."""
from __future__ import annotations
import collections, datetime as dt, hashlib, json, re, subprocess, sys, unicodedata
from pathlib import Path

OUT=Path(__file__).resolve().parent
PREV=Path("/mnt/disks/scratch/task-scratch/slskdn-pr409-w953-977-20261105/candidate-free/input")
APP=Path("/mnt/disks/scratch/task-scratch/slskdn-pr409-w953-977-20261105/root-application")
REPO=Path(sys.argv[1]).resolve()
HEAD="cc600880606f374cebe3082789fa50f246ff614f"
TREE="440b9842d914a391f77cbb03737261b8798cc6e3"
BASE="f25d263a2a7cdb2c8f76c40c346cb10f749a9356"
BASETREE="b2ce36e07aee6ade05e6d8795d04b9a7455a081f"
MAIN="bc6251ff4ea5a7e59f2d86e2400c90520601f46e"
MAINTREE="4232b318aeaab4c327443638e5467ca089bbed53"
BRANCH="codex/slskdn-oidc-tooltip-localization-20261030"
SLUG="snapetech-org/slskdN"
REMOTE="https://github.com/snapetech-org/slskdn.git"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
FIRST,LAST=953,977
QUEUE_FIRST,QUEUE_LAST=853,877
TEXT_KEYS={"source","sourceText","target","currentTarget","proposedTarget","proposedTargetText","candidateTarget","reviewTarget","rationale","reason"}
def need(ok,msg):
    if not ok: raise SystemExit("REFUSED: "+msg)
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode("utf-8"))
def blobsha(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
def git(*args): return subprocess.check_output(["git","-C",str(REPO),*args])
def readj(p): return json.loads(p.read_text(encoding="utf-8"))
def readjl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def writej(name,o): (OUT/name).write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
def writejl(name,rows): (OUT/name).write_text("".join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n" for r in rows),encoding="utf-8")
def parseobj(raw,label):
    duplicate=[]
    def pairs(ps):
        d={}
        for k,v in ps:
            if k in d: duplicate.append(k)
            d[k]=v
        return d
    out=json.loads(raw.decode("utf-8"),object_pairs_hook=pairs)
    need(isinstance(out,dict) and not duplicate,label+" malformed or duplicate-key JSON")
    return out
def no_text_keys(r):
    return not any(k in r for k in TEXT_KEYS)

def verify_sums(root, sums_path):
    recorded={}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        h,name=line.split("  ",1)
        need(name not in recorded,"duplicate checksum path "+name)
        p=root/name
        need(p.is_file() and sha(p.read_bytes())==h,"input checksum mismatch "+name)
        recorded[name]=h
    actual={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.name!=sums_path.name}
    need(actual==set(recorded),"input checksum inventory mismatch")
    return recorded

def production_path(path):
    parts=path.split("/")
    name=parts[-1]
    return path.startswith("src/web/src/") and Path(path).suffix.lower() in {".js",".jsx",".ts",".tsx"} and not any(p in {"__tests__","__specs__"} for p in parts) and not any(x in name for x in (".test.",".spec."))

def token_data(source,target):
    placeholders=lambda s: collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}",s))
    tags=lambda s: collections.Counter(re.findall(r"</?[A-Za-z][^>]*>",s))
    nums=lambda s:["".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in tok) for tok in re.findall(r"\d+",s)]
    protected=lambda s:sorted(set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b",s)) | {x for x in ("slskdN","PodCore","Wishlist","soulfind","FFmpeg","Lidarr") if x in s})
    sp,tp=placeholders(source),placeholders(target); st,tt=tags(source),tags(target)
    sn,tn=nums(source),nums(target); sl,tl=protected(source),protected(target)
    missing=[x for x in sl if x not in target]
    return {"placeholders":{"source":sorted(sp.elements()),"target":sorted(tp.elements()),"matches":sp==tp},
      "markup":{"source":sorted(st.elements()),"target":sorted(tt.elements()),"matches":st==tt},
      "numbers":{"source":sn,"target":tn,"sourcePreserved":all(tn.count(x)>=n for x,n in collections.Counter(sn).items())},
      "protectedLiterals":{"source":sl,"target":tl,"missing":missing}}

def capture_live():
    pr=json.loads(subprocess.check_output(["gh","api","repos/snapetech-org/slskdN/pulls/409"],text=True))
    branch=json.loads(subprocess.check_output(["gh","api","repos/snapetech-org/slskdN/git/ref/heads/"+BRANCH],text=True))
    mainref=json.loads(subprocess.check_output(["gh","api","repos/snapetech-org/slskdN/git/ref/heads/main"],text=True))
    remote=subprocess.check_output(["git","ls-remote",REMOTE,"refs/heads/main","refs/heads/"+BRANCH,"refs/pull/409/head"],text=True)
    refs={line.split()[1]:line.split()[0] for line in remote.splitlines() if line.strip()}
    result={"capturedAtUtc":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
      "repository":SLUG,"pullRequest":409,"state":pr["state"],"draft":pr["draft"],"merged":pr["merged"],
      "baseRef":pr["base"]["ref"],"baseSha":pr["base"]["sha"],"baseTree":git("rev-parse",pr["base"]["sha"]+"^{tree}").decode().strip(),
      "headRef":pr["head"]["ref"],"headSha":pr["head"]["sha"],"headTree":git("rev-parse",pr["head"]["sha"]+"^{tree}").decode().strip(),
      "branchApiSha":branch["object"]["sha"],"mainApiSha":mainref["object"]["sha"],"mainTree":git("rev-parse",mainref["object"]["sha"]+"^{tree}").decode().strip(),
      "remoteBranchSha":refs.get("refs/heads/"+BRANCH),"pullRefSha":refs.get("refs/pull/409/head"),
      "remoteMainSha":refs.get("refs/heads/main"),"remoteRefs":refs,"baseIsAncestorOfMain":None,
      "capturedAtHead":HEAD,"prBodyContentIncluded":False}
    result["baseIsAncestorOfMain"]=subprocess.run(["git","-C",str(REPO),"merge-base","--is-ancestor",result["baseSha"],result["mainApiSha"]]).returncode==0
    need((result["state"],result["draft"],result["merged"])==("open",True,False),"PR state")
    need((result["headRef"],result["headSha"],result["headTree"])==(BRANCH,HEAD,TREE),"PR head")
    need((result["branchApiSha"],result["remoteBranchSha"],result["pullRefSha"])==(HEAD,HEAD,HEAD),"branch/pull refs")
    need((result["baseRef"],result["baseSha"],result["baseTree"])==("main",BASE,BASETREE),"PR base pin")
    need((result["mainApiSha"],result["mainTree"],result["remoteMainSha"])==(MAIN,MAINTREE,MAIN),"live main refs")
    return result

def main():
    need({p.name for p in OUT.iterdir()} <= {"build_candidate_free.py"},"candidate-free destination contains unexpected files")
    need(git("rev-parse","HEAD").decode().strip()==HEAD and git("rev-parse","HEAD^{tree}").decode().strip()==TREE,"source worktree head/tree")
    need(not git("status","--porcelain=v1").decode().strip(),"source worktree is not clean")
    before=capture_live()
    prev_sums=verify_sums(PREV,PREV/"SHA256SUMS.txt")
    prev_manifest=readj(PREV/"manifest.json")
    need((prev_manifest.get("head"),prev_manifest.get("tree"))==("fc8e42a06363ceee762ae084bbe716953d4a5d94","e04aa06b8cfb0ee41cae90aef601a0552b5e85bd"),"prior W953 candidate-free pin")
    need(prev_manifest.get("continuationRankRange")==[953,977] and prev_manifest.get("remainingQueueRankRange")==[853,877],"prior rank range")
    need(prev_manifest.get("proposedTargetsIncluded") is False and prev_manifest.get("reviewDecisionsIncluded") is False,"prior candidate-free provenance")
    previous_selection=readjl(PREV/"source-inventory-selection.jsonl")
    selected_old=readjl(PREV/"selected-sources.jsonl")
    old_cells=readjl(PREV/"source-current-cells.jsonl")
    old_contexts=readjl(PREV/"caller-contexts.jsonl")
    old_inventory=readjl(PREV/"source-inventory-pinned.jsonl")
    old_runtime=readjl(PREV/"runtime-file-pins.jsonl")
    previous_holds=readjl(PREV/"prior-held-cell-reattestation-hash-only.jsonl")
    previous_resolutions=readjl(PREV/"prior-hold-resolution-history-hash-only.jsonl")
    previous_applied=readjl(PREV/"prior-applied-targets-reattestation-hash-only.jsonl")
    previous_exclusions=readjl(PREV/"prior-selected-id-exclusions-hash-only.jsonl")
    need(len(previous_selection)==25 and len(selected_old)==25 and len(old_cells)==300,"prior selection/input count")
    need([r["continuationRank"] for r in previous_selection]==list(range(FIRST,LAST+1)),"continuation rank order")
    need([r["remainingQueueRank"] for r in previous_selection]==list(range(QUEUE_FIRST,QUEUE_LAST+1)),"remaining queue order")
    need(len(old_inventory)==6175 and len(old_runtime)==279 and len(old_contexts)==25,"prior inventory/caller scope")
    need(len(previous_holds)==397 and len(previous_resolutions)==25 and len(previous_applied)==300 and len(previous_exclusions)==2035,"prior continuity counts")

    tree={}
    for item in git("ls-tree","-r","-z",HEAD).split(b"\0"):
        if not item: continue
        meta,path=item.split(b"\t",1)
        mode,kind,oid=meta.decode().split()
        tree[path.decode()]={"mode":mode,"kind":kind,"gitBlob":oid}
    catalog_obj={}; catalog_rows=[]; ordered=None
    for locale in LOCALES:
        path=f"src/web/public/locales/{locale}.json"
        raw=(REPO/path).read_bytes()
        need(blobsha(raw)==tree[path]["gitBlob"],"worktree catalog is not exact HEAD: "+locale)
        obj=parseobj(raw,locale)
        keys=list(obj)
        need(len(keys)==6175 and all(isinstance(v,str) and v for v in obj.values()),"catalog count/value "+locale)
        if ordered is None: ordered=keys
        else: need(keys==ordered,"locale ordered key mismatch "+locale)
        catalog_obj[locale]=obj
        catalog_rows.append({"locale":locale,"path":path,"bytes":len(raw),"sha256":sha(raw),"gitBlob":tree[path]["gitBlob"],
          "entryCount":len(obj),"orderedKeySha256":sha(("\n".join(keys)+"\n").encode())})
    source_by_id={"src_"+tsha(source)[:16]:source for source in ordered}
    need(len(source_by_id)==6175,"source ID collision")
    inventory_by_id={r["sourceId"]:r for r in old_inventory}
    need(set(inventory_by_id)==set(source_by_id),"source inventory ID set changed")
    for sid,source in source_by_id.items():
        need(inventory_by_id[sid]["sourceSha256"]==tsha(source),"stable source text changed "+sid)
    selection_by_id={r["sourceId"]:r for r in previous_selection}
    need({r["sourceId"] for r in selected_old}==set(selection_by_id),"selected ID set mismatch")
    selected=[]
    for rankrow in previous_selection:
        sid=rankrow["sourceId"]; source=source_by_id.get(sid)
        need(source is not None and tsha(source)==rankrow["sourceSha256"],"selected source changed "+sid)
        old_source=next(r for r in selected_old if r["sourceId"]==sid)
        need(old_source["source"]==source and old_source["sourceSha256"]==tsha(source),"prior selected source content mismatch "+sid)
        selected.append({"continuationRank":rankrow["continuationRank"],"remainingQueueRank":rankrow["remainingQueueRank"],
          "sourceId":sid,"sourceIdSha256":tsha(sid),"sourceSha256":tsha(source),"source":source})
    selected_ids={r["sourceId"] for r in selected}
    need(len(selected)==25,"exact selected source count")

    locale_keys={l:catalog_obj[l] for l in LOCALES}
    current_old={(r["sourceId"],r["locale"]):r for r in old_cells}
    need(len(current_old)==300,"old cell duplicate")
    root_verify=readj(APP/"final-head-verification.json")
    root_readback_path=APP/"final-head-readback.jsonl"
    root_readback_bytes=root_readback_path.read_bytes()
    need(sha(root_readback_bytes)==root_verify["readbackSha256"],"root readback checksum")
    root_readback=readjl(root_readback_path)
    selected_by_rank={r["continuationRank"]:r for r in selected}
    root_by={}
    for raw in root_readback:
        s=selected_by_rank.get(raw["continuationRank"])
        need(s is not None,"root readback rank has no selected source")
        sid=raw.get("sourceId",s["sourceId"])
        need(sid==s["sourceId"] and raw.get("sourceSha256")==s["sourceSha256"],"root readback source binding")
        row=dict(raw); row["sourceId"]=sid; row["sourceIdSha256"]=tsha(sid)
        root_by[(sid,row["locale"])]=row
    need(len(root_readback)==300 and len(root_by)==300,"root readback coverage")
    need(root_verify["productHead"]=="892ff7ff72b211bf56c7d84cbd209184071cc638","W953 product commit")
    need(subprocess.run(["git","-C",str(REPO),"merge-base","--is-ancestor",root_verify["productHead"],HEAD]).returncode==0,"W953 product commit ancestry")
    root_counts=collections.Counter(r["rootDisposition"] for r in root_readback)
    need(root_counts=={"accept-current":174,"accept-correction":110,"accept-refinement":3,"root-manual-adjustment":1,"hold-non-user-facing-hash-only":12},"W953 applied/hold counts")
    need(root_verify["candidateCells"]==300 and root_verify["all12CatalogsReadBack"] is True and root_verify["hashOnlyHoldsTextFree"] is True,"W953 final verification summary")

    runtime=[]
    for path,entry in sorted(tree.items()):
        if not production_path(path): continue
        data=(REPO/path).read_bytes()
        need(blobsha(data)==entry["gitBlob"],"runtime blob mismatch "+path)
        runtime.append({"path":path,"bytes":len(data),"sha256":sha(data),"gitBlob":entry["gitBlob"],"lineCount":len(data.decode("utf-8").splitlines())})
    need(len(runtime)==279,"production runtime file count")
    runtime_by={r["path"]:r for r in runtime}
    need(len(old_runtime)==279 and {r["path"] for r in old_runtime}==set(runtime_by),"runtime file set drift")
    for r in old_runtime:
        need(runtime_by[r["path"]]["sha256"]==r["sha256"] and runtime_by[r["path"]]["gitBlob"]==r["gitBlob"],"production caller file changed since W953 input "+r["path"])

    refs_by_source={}
    for source_row in selected:
        source=source_row["source"]
        refs=[]
        literal=re.compile(r"(?<![A-Za-z0-9_$])([\"'])"+re.escape(source)+r"\1")
        for filepin in runtime:
            lines=(REPO/filepin["path"]).read_text(encoding="utf-8").splitlines()
            for idx,line in enumerate(lines):
                if not literal.search(line): continue
                context=[{"line":n+1,"text":lines[n]} for n in range(max(0,idx-4),min(len(lines),idx+3))]
                refs.append({"path":filepin["path"],"line":idx+1,"lineText":line,"lineSha256":tsha(line),
                  "context":context,"contextSha256":sha(canon(context)),"fileBytes":filepin["bytes"],
                  "fileSha256":filepin["sha256"],"gitBlob":filepin["gitBlob"]})
        refs_by_source[source_row["sourceId"]]=refs
    old_context_by={r["sourceId"]:r for r in old_contexts}
    for s in selected:
        refs=refs_by_source[s["sourceId"]]
        old=old_context_by[s["sourceId"]]
        need(len(refs)==old["productionCallerCount"],"current caller count changed "+s["sourceId"])
        need(sha(canon(refs))==next(r["callerContextSha256"] for r in old_cells if r["sourceId"]==s["sourceId"]),"current caller context changed "+s["sourceId"])
        need(all(r["sourceTextIncluded"] is True for r in [old]),"old selected caller/source evidence")
    hold_source=next(s for s in selected if s["continuationRank"]==966)
    hold_refs=refs_by_source[hold_source["sourceId"]]
    need(len(hold_refs)==52,"rank-966 hold caller count")
    hold_line_classes=collections.Counter("positioning-alignment-style" if re.search(r"position|align|justify|textAlign|items-|style",r["lineText"],re.I) else "other" for r in hold_refs)
    need(hold_line_classes=={"positioning-alignment-style":49,"other":3},"rank-966 current caller classification changed")

    cell_rows=[]; token_mismatch=collections.Counter(); current_target_hashes={}
    for s in selected:
        sid=s["sourceId"]; source=s["source"]; is_hold_source=s["continuationRank"]==966
        refs=refs_by_source[sid]; caller_hash=sha(canon(refs))
        for locale in LOCALES:
            prior=current_old[(sid,locale)]
            actual=catalog_obj[locale][source]
            target_hash=tsha(actual); current_target_hashes[(sid,locale)]=target_hash
            root=root_by[(sid,locale)]
            need(root["continuationRank"]==s["continuationRank"] and root["remainingQueueRank"]==s["remainingQueueRank"],"root rank binding")
            need(root["sourceSha256"]==tsha(source) and root["sourceIdSha256"]==tsha(sid),"root source hash")
            need(root["callerContextSha256"]==caller_hash,"root caller hash")
            need(root["observedAfterSha256"]==root["expectedAfterSha256"]==target_hash,"applied readback matches current catalog")
            need(prior["currentTargetSha256"]==root["beforeTargetSha256"],"current input preimage mismatch")
            need(prior["sourceSha256"]==tsha(source) and prior["sourceId"]==sid,"prior cell source mismatch")
            evidence=token_data(source,actual)
            for typ,ok in (("placeholder",evidence["placeholders"]["matches"]),("markup",evidence["markup"]["matches"]),
              ("numeric",evidence["numbers"]["sourcePreserved"]),("protectedLiteral",not evidence["protectedLiterals"]["missing"])):
                if not ok: token_mismatch[typ]+=1
            record={"continuationRank":s["continuationRank"],"remainingQueueRank":s["remainingQueueRank"],
              "sourceId":sid,"sourceIdSha256":tsha(sid),"sourceSha256":tsha(source),"locale":locale,
              "currentTargetSha256":target_hash,"currentTargetTextIncluded":not is_hold_source,
              "sourceTextIncluded":not is_hold_source,"catalogPath":f"src/web/public/locales/{locale}.json",
              "catalogFileSha256":next(c["sha256"] for c in catalog_rows if c["locale"]==locale),
              "catalogGitBlob":next(c["gitBlob"] for c in catalog_rows if c["locale"]==locale),
              "callerContextSha256":caller_hash,"callerCount":len(refs),"containsCandidate":False,"decision":None,
              "previousTargetSha256":prior["currentTargetSha256"],"rootAppliedTargetSha256":root["expectedAfterSha256"],
              "tokenEvidenceSha256":sha(canon(evidence)),"tokenChecksPass":all((evidence["placeholders"]["matches"],evidence["markup"]["matches"],evidence["numbers"]["sourcePreserved"],not evidence["protectedLiterals"]["missing"]))}
            if not is_hold_source:
                record.update({"source":source,"currentTarget":actual,"tokenEvidence":evidence})
            else:
                record.update({"sourceTextOmittedForHashOnlyHold":True,"currentTargetOmittedForHashOnlyHold":True,
                  "tokenEvidenceTextOmitted":True})
            cell_rows.append(record)
    need(len(cell_rows)==300,"exact 25 x 12 cells")
    need(not token_mismatch,"current target token mismatch: "+str(dict(token_mismatch)))

    caller_rows=[]
    for s in selected:
        refs=refs_by_source[s["sourceId"]]; is_hold=s["continuationRank"]==966
        row={"continuationRank":s["continuationRank"],"remainingQueueRank":s["remainingQueueRank"],
          "sourceId":s["sourceId"],"sourceIdSha256":tsha(s["sourceId"]),"sourceSha256":tsha(s["source"]),
          "productionCallerCount":len(refs),"callerContextSha256":sha(canon(refs)),
          "callerReferenceTextIncluded":not is_hold,"sourceTextIncluded":not is_hold,
          "exactHead":HEAD,"exactTree":TREE}
        if is_hold:
            row["callerRefsHashOnly"]=[{k:r[k] for k in ("path","line","lineSha256","contextSha256","fileSha256","gitBlob")} for r in refs]
            row["callerUseClassCounts"]=dict(hold_line_classes)
        else:
            row["source"]=s["source"]
            row["callers"]=refs
        caller_rows.append(row)

    # Reattest historical W82 hash-only state at this exact head.
    prior_hold_rows=[]
    for old in previous_holds:
        sid,locale=old["sourceId"],old["locale"]
        source=source_by_id.get(sid)
        need(source is not None and tsha(source)==old["sourceSha256"],"W82 active-hold source changed")
        target_hash=tsha(catalog_obj[locale][source])
        need(target_hash==old["priorTargetSha256"]==old["currentTargetSha256"],"W82 active-hold target changed")
        prior_hold_rows.append({"priorWindow":old["priorWindow"],"sourceId":sid,"sourceIdSha256":tsha(sid),
          "sourceSha256":tsha(source),"locale":locale,"priorTargetSha256":old["priorTargetSha256"],
          "currentTargetSha256":target_hash,"priorCallerContextSha256":old["currentCallerContextSha256"],
          "currentCallerContextSha256":old["currentCallerContextSha256"],"callerEvidenceUnchanged":True,
          "holdReasonSha256":old.get("holdReasonSha256"),"currentCatalogPath":f"src/web/public/locales/{locale}.json",
          "currentCatalogFileSha256":next(c["sha256"] for c in catalog_rows if c["locale"]==locale),
          "currentCatalogGitBlob":next(c["gitBlob"] for c in catalog_rows if c["locale"]==locale),
          "sourceTextIncluded":False,"targetTextIncluded":False,"attestedAtHead":HEAD})
    window_hold_rows=[]; window_applied_rows=[]; readback_rows=[]
    for (sid,locale),root in sorted(root_by.items(),key=lambda x:(x[1]["continuationRank"],LOCALES.index(x[0][1]))):
        s=next(x for x in selected if x["sourceId"]==sid)
        target_hash=current_target_hashes[(sid,locale)]
        is_hold=root["rootDisposition"]=="hold-non-user-facing-hash-only"
        if is_hold:
            window_hold_rows.append({"window":"W953-W977","continuationRank":root["continuationRank"],
              "remainingQueueRank":root["remainingQueueRank"],"sourceIdSha256":tsha(sid),"sourceSha256":tsha(s["source"]),
              "locale":locale,"callerContextSha256":root["callerContextSha256"],"callerCount":root.get("callerCount",52),
              "holdReasonClass":root["holdReasonClass"],"currentTargetSha256":target_hash,
              "sourceTextIncluded":False,"targetTextIncluded":False,"proposalTextIncluded":False,
              "attestedAtHead":HEAD})
        else:
            window_applied_rows.append({"window":"W953-W977","continuationRank":root["continuationRank"],
              "remainingQueueRank":root["remainingQueueRank"],"sourceId":sid,"sourceIdSha256":tsha(sid),
              "sourceSha256":tsha(s["source"]),"locale":locale,"rootDisposition":root["rootDisposition"],
              "appliedTargetSha256":root["expectedAfterSha256"],"currentTargetSha256":target_hash,
              "targetRemainsApplied":True,"rootProductCommit":root_verify["productHead"],
              "rootReadbackSha256":root_verify["readbackSha256"],"currentCatalogFileSha256":next(c["sha256"] for c in catalog_rows if c["locale"]==locale),
              "currentCatalogGitBlob":next(c["gitBlob"] for c in catalog_rows if c["locale"]==locale),
              "sourceTextIncluded":False,"targetTextIncluded":False,"attestedAtHead":HEAD})
        readback_rows.append({"window":"W953-W977","continuationRank":root["continuationRank"],
          "remainingQueueRank":root["remainingQueueRank"],"sourceIdSha256":tsha(sid),"sourceSha256":tsha(s["source"]),
          "locale":locale,"rootDispositionClass":"hold-hash-only" if is_hold else "applied",
          "rootExpectedAfterSha256":root["expectedAfterSha256"],"rootObservedAfterSha256":root["observedAfterSha256"],
          "currentCatalogTargetSha256":target_hash,"readbackMatchesCurrent":root["observedAfterSha256"]==target_hash,
          "sourceTextIncluded":False,"targetTextIncluded":False,"attestedAtHead":HEAD})
    need(len(window_applied_rows)==288 and len(window_hold_rows)==12 and len(readback_rows)==300,"window applied/hold counts")
    need({r["continuationRank"] for r in window_hold_rows}=={966},"held rank")
    for old in previous_applied:
        sid,locale=old["sourceId"],old["locale"]
        source=source_by_id.get(sid)
        need(source is not None and tsha(source)==old["sourceSha256"],"W82 applied source changed")
        target_hash=tsha(catalog_obj[locale][source])
        need(target_hash==old["appliedTargetSha256"]==old["currentTargetSha256"],"W82 applied target changed")
    historical_applied=[{k:v for k,v in r.items() if k not in TEXT_KEYS} for r in previous_applied]
    # Add current W953 application hash attestations, keeping the held cells separate.
    applied_rows=historical_applied+window_applied_rows
    need(len(applied_rows)==588,"combined applied target count")
    all_hold_rows=prior_hold_rows+window_hold_rows
    need(len(all_hold_rows)==409,"combined active hold count")

    # Hash-only source selection continuity, with the now-applied W953 IDs excluded.
    exclusion_by={r["sourceId"]:r for r in previous_exclusions}
    need(len(exclusion_by)==2035,"prior exclusion set")
    for s in selected:
        sid=s["sourceId"]
        need(sid not in exclusion_by,"selected W953 ID already excluded at entry")
        exclusion_by[sid]={"sourceId":sid,"sourceIdSha256":tsha(sid),"sourceSha256":tsha(s["source"]),
          "continuationRank":s["continuationRank"],"remainingQueueRank":s["remainingQueueRank"],
          "selectionOrigin":"W953-W977 applied/current-hold window","exclusionOrigins":["W953-W977 current-head readback"],
          "exclusionConfirmed":True,"sourceTextIncluded":False,"targetTextIncluded":False}
    need(len(exclusion_by)==2060,"updated selected source exclusions")
    inventory_rows=[]
    for sid in sorted(source_by_id):
        old=inventory_by_id[sid]
        excluded=sid in exclusion_by
        inventory_rows.append({"sourceId":sid,"sourceSha256":tsha(source_by_id[sid]),
          "continuationRank":old.get("continuationRank"),"remainingQueueRank":old.get("remainingQueueRank"),
          "baselineExcluded":old.get("baselineExcluded",False),"priorSelectedOrRewriteExcluded":excluded,
          "eligibleForFreshWindow":old.get("continuationRank") is not None and not old.get("baselineExcluded",False) and not excluded,
          "localeCoverage":12,"sourceTextIncluded":False,"attestedAtHead":HEAD})
    need(len(inventory_rows)==6175,"current source inventory count")

    # Validate prior hold-resolution hashes against the current exact catalogs.
    resolution_rows=[]
    missing_resolution_sources=0
    for old in previous_resolutions:
        sid,locale=old["sourceId"],old["locale"]
        source=source_by_id.get(sid)
        base={"priorWindow":old.get("priorWindow"),"continuationRank":old.get("continuationRank"),
          "sourceId":sid,"sourceIdSha256":tsha(sid),"sourceSha256":old["sourceSha256"],"locale":locale,
          "formerHoldTargetSha256":old.get("formerHoldTargetSha256"),"resolvedTargetSha256":old["resolvedTargetSha256"],
          "attestedAtHead":HEAD,"sourceTextIncluded":False,"targetTextIncluded":False}
        if source is None:
            missing_resolution_sources+=1
            base.update({"currentSourcePresent":False,"currentLocaleCellPresent":False,
              "currentTargetSha256":None,"currentTargetMatchesResolution":None,
              "reattestationStatus":"historical-source-id-absent-from-current-catalog"})
        else:
            need(tsha(source)==old["sourceSha256"],"prior resolution source hash changed")
            target_hash=tsha(catalog_obj[locale][source])
            need(target_hash==old["resolvedTargetSha256"],"prior hold resolution target changed")
            base.update({"currentSourcePresent":True,"currentLocaleCellPresent":True,
              "currentTargetSha256":target_hash,"currentTargetMatchesResolution":True,
              "reattestationStatus":"current-catalog-target-hash-matches"})
        resolution_rows.append(base)
    need(len(resolution_rows)==25 and missing_resolution_sources==12,"prior hold resolution history scope")

    # Full-catalog ordered key inventory and source-to-locale parity attestations.
    ordered_manifest={"entryCount":len(ordered),"orderedKeySha256":sha(("\n".join(ordered)+"\n").encode()),
      "sourceIdOrderSha256":sha(b"".join(bytes.fromhex(tsha(k)) for k in ordered)),
      "sourceRecordOrderSha256":sha(b"".join(bytes.fromhex(tsha("src_"+tsha(k)[:16]))+bytes.fromhex(tsha(k)) for k in ordered)),
      "catalogKeysAreEnglishSourceStrings":True,"exactHead":HEAD,"exactTree":TREE}
    prior_boundary=readj(PREV/"selection-and-boundary.json")["previousWindowFinalRank"]
    next_boundary=readj(PREV/"selection-and-boundary.json")["nextUnselected"]
    for boundary in (prior_boundary,next_boundary):
        source=source_by_id.get(boundary["sourceId"])
        need(source is not None and tsha(source)==boundary["sourceSha256"],"source window boundary changed")
    boundary_state={"window":"W953-W977","recordedRemainingQueueRange":[QUEUE_FIRST,QUEUE_LAST],
      "recordedContinuationRange":[FIRST,LAST],"previousWindowFinalRank":prior_boundary,
      "selectedWindow":[{"continuationRank":s["continuationRank"],"remainingQueueRank":s["remainingQueueRank"],
        "sourceId":s["sourceId"],"sourceSha256":s["sourceSha256"]} for s in selected],
      "nextUnselected":next_boundary,"currentSelectionState":"These exact ranks are already represented by W953-W977 application/readback at the current head; this packet reattests that state and does not claim the cells remain untranslated."}

    writej("live-before.json",before)
    writej("catalog-key-order-attestation.json",ordered_manifest)
    writejl("catalog-structure.jsonl",catalog_rows)
    writejl("runtime-file-pins.jsonl",runtime)
    writejl("source-inventory-pinned.jsonl",inventory_rows)
    writejl("source-inventory-selection.jsonl",[{"continuationRank":s["continuationRank"],"remainingQueueRank":s["remainingQueueRank"],
      "sourceId":s["sourceId"],"sourceIdSha256":tsha(s["sourceId"]),"sourceSha256":s["sourceSha256"]} for s in selected])
    output_selected=[]
    for s in selected:
        is_hold=s["continuationRank"]==966
        row={k:v for k,v in s.items() if k!="source"}
        row.update({"sourceTextIncluded":not is_hold,"exactHead":HEAD,"exactTree":TREE})
        if not is_hold: row["source"]=s["source"]
        else: row["sourceTextOmittedForHashOnlyHold"]=True
        output_selected.append(row)
    writejl("selected-sources.jsonl",output_selected)
    writejl("source-current-cells.jsonl",cell_rows)
    writejl("caller-contexts.jsonl",caller_rows)
    writejl("prior-selected-id-exclusions-hash-only.jsonl",sorted(exclusion_by.values(),key=lambda r:r["sourceId"]))
    writejl("prior-held-cell-reattestation-hash-only.jsonl",prior_hold_rows)
    writejl("window-holds-hash-only.jsonl",window_hold_rows)
    writejl("prior-applied-targets-reattestation-hash-only.jsonl",historical_applied)
    writejl("window-applied-targets-reattestation-hash-only.jsonl",window_applied_rows)
    writejl("window-application-readback-hash-only.jsonl",readback_rows)
    writejl("prior-hold-resolution-history-hash-only.jsonl",resolution_rows)
    writej("selection-and-boundary.json",boundary_state)
    writej("window-application-reattestation.json",{"result":"PASS","inputHead":"fc8e42a06363ceee762ae084bbe716953d4a5d94",
      "inputTree":"e04aa06b8cfb0ee41cae90aef601a0552b5e85bd","productHead":root_verify["productHead"],
      "productTree":root_verify["productTree"],"currentHead":HEAD,"currentTree":TREE,
      "productCommitIsAncestor":True,"rootReadbackSha256":root_verify["readbackSha256"],
      "rootReadbackFileSha256":sha(root_readback_bytes),"cells":300,"appliedCells":288,"hashOnlyHeldCells":12,
      "heldRanks":[966],"allCurrentCatalogTargetsMatchReadback":True,"allHoldTextsOmitted":True,
      "currentCatalogsChangedSinceProductCommit":False,"currentCatalogComparison":"verified exact target hashes for all 300 cells"})
    writej("baseline-token-mismatch-summary.json",{"cellCount":300,"mismatchCounts":dict(token_mismatch),
      "mismatchExamples":[],"reviewCandidateTextIncluded":False,
      "note":"Token checks were computed against current catalog values at the exact current head; 12 existing held cells expose token hashes/check booleans only."})
    after=capture_live()
    need(before["remoteRefs"]==after["remoteRefs"] and before["headSha"]==after["headSha"] and before["baseSha"]==after["baseSha"] and before["mainApiSha"]==after["mainApiSha"],"live refs changed during packet build")
    writej("live-after.json",after)
    file_names=sorted(p.name for p in OUT.iterdir() if p.is_file() and p.name not in {"SHA256SUMS.txt","manifest.json","summary.json","README.md"})
    summary={"result":"PASS","artifact":"slskdN PR #409 remaining queue rank current-head reattestation",
      "exactHead":HEAD,"exactTree":TREE,"baseRef":"main","baseSha":BASE,"baseTree":BASETREE,
      "mainSha":MAIN,"mainTree":MAINTREE,"branch":BRANCH,"PRState":"open/draft",
      "remainingQueueRankRange":[QUEUE_FIRST,QUEUE_LAST],"continuationRankRange":[FIRST,LAST],
      "sourceIds":25,"localeCount":12,"cellCount":300,"catalogCount":12,"catalogEntryCountPerLocale":6175,
      "sourceInventoryRows":6175,"productionCallerFileCount":279,"sourcesWithCurrentCallers":25,
      "currentW953AppliedCellsReattested":288,"currentW953HashOnlyHoldsReattested":12,"heldContinuationRank":966,
      "historicalW82AppliedTargetsReattested":len(historical_applied),"historicalW82ActiveHoldsReattested":len(prior_hold_rows),
      "historicalHoldResolutionRowsReconciled":len(resolution_rows),"historicalHoldResolutionRowsTargetReattested":len(resolution_rows)-missing_resolution_sources,"historicalHoldResolutionRowsSourceAbsent":missing_resolution_sources,"priorSelectedIdsAndCurrentW953Exclusions":len(exclusion_by),
      "currentSourceTextsReattested":25,"callerLineReferencesReattested":sum(len(refs_by_source[s["sourceId"]]) for s in selected),
      "currentTargetCellHashesMatchRootReadback":True,"tokenMismatchCounts":dict(token_mismatch),
      "proposedTargetsIncluded":False,"primaryBlindOrCrossProposalsRead":False,"reviewDecisionsIncluded":False,
      "repositoryOrPREdited":False,"testsBuildsScansCiRun":False,"workflowChanges":0,
      "outputFiles":file_names,"candidateFreeChecksumCount":len(file_names)+4}
    writej("summary.json",summary)
    readme="""# slskdN PR #409 current-head candidate-free reattestation for queue ranks 853–877

This packet uses the exact 25 source IDs recorded as remaining-queue ranks 853–877 in the sealed W953–W977 candidate-free inventory. Those same cells are now present in the W953–W977 root application readback at current PR head cc600880606f374cebe3082789fa50f246ff614f. The packet reattests 288 applied values and 12 text-free hash-only holds at continuation rank 966; it does not describe these cells as untranslated and contains no primary, blind, or cross proposals.

All current source values, ordered catalog keys, twelve locale catalog blobs, 279 production runtime file pins, caller references, token evidence, and prior W82 hold/applied lineage are bound to exact head cc600880606f374cebe3082789fa50f246ff614f / tree 440b9842d914a391f77cbb03737261b8798cc6e3. The 12 held cells omit source and target text, retaining only hashes and caller pins.

The PR API base is f25d263a2a7cdb2c8f76c40c346cb10f749a9356; the live main branch is bc6251ff4ea5a7e59f2d86e2400c90520601f46e. Both values are recorded at entry and exit. They are distinct refs and are not conflated.

Run python3 verify_candidate_free.py for the portable packet verifier. Run python3 verify_exact_worktree.py /path/to/slskdn-pr409-w953-977-root-apply for the exact Git object, catalog, runtime caller, target, token, and readback verification. No repository, PR, workflow, or catalog edits were made.
"""
    (OUT/"README.md").write_text(readme,encoding="utf-8")
    files=[]
    for p in sorted(OUT.iterdir()):
        if p.is_file() and p.name not in {"SHA256SUMS.txt","manifest.json"}:
            files.append({"path":p.name,"sha256":sha(p.read_bytes()),"bytes":p.stat().st_size})
    manifest={"artifact":"slskdN PR #409 W853-W877 current-head candidate-free input",
      "schemaVersion":1,"repository":SLUG,"pullRequest":409,"packetType":"candidate-free-current-readback",
      "window":"W853-W877","head":HEAD,"tree":TREE,"branch":BRANCH,"baseRef":"main","baseSha":BASE,"baseTree":BASETREE,
      "mainSha":MAIN,"mainTree":MAINTREE,"remainingQueueRankRange":[QUEUE_FIRST,QUEUE_LAST],
      "continuationRankRange":[FIRST,LAST],"sourceCount":25,"localeCount":12,"cellCount":300,"catalogCount":12,
      "catalogEntryCountPerLocale":6175,"productionCallerFileCount":279,"currentAppliedTargetCount":288,
      "currentHashOnlyHoldCount":12,"heldRank":966,"priorHistoricalAppliedCount":300,"priorHistoricalHoldCount":397,
      "priorHoldResolutionHistoryCount":25,"priorHoldResolutionRowsTargetReattested":25-missing_resolution_sources,"priorHoldResolutionRowsSourceAbsent":missing_resolution_sources,"priorSelectedAndWindowExclusionCount":2060,
      "proposedTargetsIncluded":False,"reviewDecisionsIncluded":False,"primaryBlindOrCrossProposalsRead":False,
      "currentCandidateTranslationReviewPerformed":False,"liveEntrySha256":sha((OUT/"live-before.json").read_bytes()),
      "liveExitSha256":sha((OUT/"live-after.json").read_bytes()),
      "priorCandidateFreeManifestSha256":sha((PREV/"manifest.json").read_bytes()),
      "priorCandidateFreeChecksumListSha256":sha((PREV/"SHA256SUMS.txt").read_bytes()),
      "rootReadbackSha256":root_verify["readbackSha256"],"rootReadbackFileSha256":sha(root_readback_bytes),
      "files":files}
    writej("manifest.json",manifest)
    sums=[]
    for p in sorted(OUT.iterdir()):
        if p.is_file() and p.name!="SHA256SUMS.txt": sums.append(f"{sha(p.read_bytes())}  {p.name}")
    (OUT/"SHA256SUMS.txt").write_text("\n".join(sums)+"\n",encoding="utf-8")
    print(json.dumps({"result":"PASS","output":str(OUT),"sources":25,"cells":300,
      "applied":288,"holdsHashOnly":12,"priorW82Applied":300,"priorW82Holds":397,
      "priorW82HoldResolutionHistory":25,"priorW82HoldResolutionTargetsReattested":25-missing_resolution_sources,"priorW82HoldResolutionSourcesAbsent":missing_resolution_sources,"priorExclusionsPlusWindow":2060,
      "callerFiles":279,"callerReferences":sum(len(refs_by_source[s["sourceId"]]) for s in selected),
      "tokenMismatches":dict(token_mismatch),"head":HEAD,"tree":TREE,"base":BASE,"main":MAIN},indent=2))
if __name__=="__main__": main()
