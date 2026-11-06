#!/usr/bin/env python3
"""Verify the sealed W953-W977 blind packet, candidate-free input bindings, and optional exact-head worktree."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parent
INPUT = OUT.parent / "candidate-free" / "input"
HEAD = "fc8e42a06363ceee762ae084bbe716953d4a5d94"
TREE = "e04aa06b8cfb0ee41cae90aef601a0552b5e85bd"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
START, END = 953, 977
PH = re.compile(r"\{[^{}]+\}")
TAG = re.compile(r"</?[A-Za-z][^>]*>")
NUM = re.compile(r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)*(?![A-Za-z0-9])")
TEXT_KEYS = {"source", "sourceText", "currentTarget", "currentTargetText", "proposedTarget", "target", "targetText", "resolvedTarget"}

def fail(message): raise SystemExit("FAIL: " + message)
def sha(value): return hashlib.sha256(value.encode("utf-8") if isinstance(value,str) else value).hexdigest()
def canon(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
def j(path): return json.loads(path.read_text(encoding="utf-8"))
def jl(path): return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s]
def check_sums(root):
    sums_path=root/"SHA256SUMS.txt"; listed={}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        digest,name=line.split("  ",1)
        if name in listed: fail("duplicate checksum "+name)
        file=(root/name).resolve()
        if not file.is_relative_to(root.resolve()) or not file.is_file() or sha(file.read_bytes())!=digest: fail("checksum "+name)
        listed[name]=digest
    actual={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p!=sums_path}
    if set(listed)!=actual: fail("checksum coverage")
    return listed

def token_checks(source,target,protected):
    return {
        "placeholderSequencePreserved":PH.findall(source)==PH.findall(target),
        "markupPreserved":TAG.findall(source)==TAG.findall(target),
        "numericTokensPreserved":NUM.findall(source)==NUM.findall(target),
        "protectedLiteralsPreserved":all(item in target for item in protected),
    }

def verify(repo=None):
    outer=check_sums(OUT)
    candidate_sums=check_sums(INPUT)
    packet=j(OUT/"manifest.json"); summary=j(OUT/"summary.json"); note=j(OUT/"input-inventory-note.json"); pin=j(OUT/"pin-attestation.json")
    if (packet.get("head"),packet.get("tree"),packet.get("window"),packet.get("cellCount"),packet.get("branch"))!=(HEAD,TREE,"W953-W977",300,BRANCH): fail("packet pin/cardinality")
    if packet.get("primaryReviewAccessed") is not False or note.get("primaryReviewOpened") is not False: fail("blind stage boundary")
    if summary.get("primaryReviewAccessed") is not False or summary.get("crossReviewAccessed") is not False: fail("summary stage boundary")
    candidate_manifest=j(INPUT/"manifest.json")
    if (candidate_manifest.get("head"),candidate_manifest.get("tree"),candidate_manifest.get("window"),candidate_manifest.get("cellCount"))!=(HEAD,TREE,"W83",300): fail("candidate-free pin")
    if packet.get("candidateFreeChecksumListSha256")!=sha((INPUT/"SHA256SUMS.txt").read_bytes()) or note.get("candidateFreeChecksumListSha256")!=sha((INPUT/"SHA256SUMS.txt").read_bytes()): fail("candidate-free checksum-list pin")
    if packet.get("files") is None: fail("packet file inventory missing")
    manifest_files={r["path"]:r for r in packet["files"]}
    actual_without_manifest={p.name for p in OUT.iterdir() if p.is_file() and p.name not in {"manifest.json","SHA256SUMS.txt"}}
    if set(manifest_files)!=actual_without_manifest: fail("manifest file inventory")
    for name,row in manifest_files.items():
        path=OUT/name
        if row.get("sha256")!=sha(path.read_bytes()) or row.get("bytes")!=path.stat().st_size: fail("manifest file hash "+name)
    if (pin.get("checkedBeforeReview"),pin.get("state"),pin.get("draft"),pin.get("merged"),pin.get("headRef"),pin.get("apiHeadSha"),pin.get("remoteBranchSha"),pin.get("pullRefSha"),pin.get("headTree"))!=(True,"open",True,False,BRANCH,HEAD,HEAD,HEAD,TREE): fail("pre-review PR/ref attestation")
    if summary.get("candidateFreeManifestSha256")!=sha((INPUT/"manifest.json").read_bytes()): fail("candidate-free manifest pin")
    if summary.get("currentCellsSha256")!=sha((INPUT/"source-current-cells.jsonl").read_bytes()) or summary.get("callerContextsSha256")!=sha((INPUT/"caller-contexts.jsonl").read_bytes()): fail("candidate-free source/context hash")

    cells=jl(INPUT/"source-current-cells.jsonl"); contexts=jl(INPUT/"caller-contexts.jsonl"); selected=jl(INPUT/"selected-sources.jsonl")
    ledger=jl(OUT/"blind-ledger.jsonl"); proposals=jl(OUT/"proposals.jsonl"); holds=jl(OUT/"holds-hash-only.jsonl")
    if len(cells)!=300 or len(ledger)!=300 or len(contexts)!=25 or len(selected)!=25: fail("cell/source cardinality")
    expected=[(r,l) for r in range(START,END+1) for l in LOCALES]
    if [(x["continuationRank"],x["locale"]) for x in cells]!=expected or [(x["continuationRank"],x["locale"]) for x in ledger]!=expected: fail("ordered 300-cell coverage")
    c_by={(x["continuationRank"],x["locale"]):x for x in cells}; l_by={(x["continuationRank"],x["locale"]):x for x in ledger}
    ctx_by={x["continuationRank"]:x for x in contexts}; src_by={x["continuationRank"]:x for x in selected}
    if len(c_by)!=300 or len(l_by)!=300 or len(ctx_by)!=25 or len(src_by)!=25: fail("unique source/cell coverage")
    proposal_by={(x["continuationRank"],x["locale"]):x for x in proposals}
    hold_by={(x["continuationRank"],x["locale"]):x for x in holds}
    if len(proposal_by)!=len(proposals) or len(hold_by)!=len(holds): fail("duplicate proposal/hold")
    counts=Counter(); hold_keys=[]
    for key in expected:
        c,l=c_by[key],l_by[key]; pos,loc=key; ctx=ctx_by[pos]; selected_row=src_by[pos]
        if not (c["sourceId"]==ctx["sourceId"]==selected_row["sourceId"] and c["source"]==ctx["source"]==selected_row["source"]): fail("source binding "+str(key))
        if not (c["sourceSha256"]==ctx["sourceSha256"]==selected_row["sourceSha256"]==sha(c["source"]) and l["sourceSha256"]==c["sourceSha256"]): fail("source hash "+str(key))
        caller_hash=c["callerContextSha256"]
        refs_hash=sha(canon(ctx["callers"]))
        if l.get("callerContextSha256")!=caller_hash or l.get("callerReferencePinsSha256")!=refs_hash or l.get("callerCount")!=c["callerCount"] or c["callerCount"]!=ctx["productionCallerCount"]: fail("caller/context binding "+str(key))
        if l.get("head")!=HEAD or l.get("tree")!=TREE or l.get("reviewPass")!="independent-blind": fail("row pin/pass "+str(key))
        if l.get("currentTargetSha256")!=c["currentTargetSha256"] or c["currentTargetSha256"]!=sha(c["currentTarget"]): fail("current target hash "+str(key))
        expected_hold=(pos==966 or c["callerCount"]==0)
        if expected_hold:
            hold=hold_by.get(key)
            if hold is None or l.get("decision")!="hold": fail("required hold missing "+str(key))
            if any(k in hold for k in TEXT_KEYS) or any(k in l for k in TEXT_KEYS): fail("text in hash-only hold "+str(key))
            if hold.get("sourceSha256")!=c["sourceSha256"] or hold.get("sourceIdSha256")!=sha(c["sourceId"]) or hold.get("currentTargetSha256")!=c["currentTargetSha256"] or hold.get("callerContextSha256")!=caller_hash or hold.get("callerReferencePinsSha256")!=refs_hash: fail("hash-only hold binding "+str(key))
            if l.get("sourceSha256")!=c["sourceSha256"] or l.get("sourceIdSha256")!=sha(c["sourceId"]) or l.get("tokenEvidenceSha256")!=sha(canon(c["tokenEvidence"])): fail("blind hold source/token hash "+str(key))
            hold_keys.append(key); counts["hold"]+=1; continue
        if l.get("sourceId")!=c["sourceId"] or l.get("source")!=c["source"] or l.get("currentTarget")!=c["currentTarget"]: fail("review text binding "+str(key))
        expected_tokens=token_checks(c["source"], l["proposedTarget"] if l["proposedTarget"] is not None else c["currentTarget"], c["tokenEvidence"]["protectedLiterals"]["source"])
        if l.get("tokenCheck")!=expected_tokens or not all(expected_tokens.values()): fail("token check "+str(key))
        if l["decision"]=="accept-current":
            if l.get("proposedTarget") is not None or l.get("proposedTargetSha256") is not None or key in proposal_by: fail("accept-current proposal field "+str(key))
        elif l["decision"] in {"correction","refinement"}:
            target=l.get("proposedTarget")
            if not isinstance(target,str) or l.get("proposedTargetSha256")!=sha(target): fail("proposal target hash "+str(key))
            prop=proposal_by.get(key)
            if prop is None or prop.get("proposedTarget")!=target or prop.get("proposedTargetSha256")!=sha(target) or prop.get("rationale")!=l.get("rationale"): fail("proposal ledger link "+str(key))
        else: fail("unknown decision "+str(key))
        if not l.get("rationale") or l.get("confidence") not in {"high","moderate","low","unknown"}: fail("rationale/confidence "+str(key))
        counts[l["decision"]]+=1
    if set(proposal_by)!={(k) for k,x in l_by.items() if x["decision"] in {"correction","refinement"}}: fail("proposal ledger coverage")
    if set(hold_by)!=set(hold_keys): fail("hash-only hold inventory")
    if any(k[0]!=966 for k in hold_keys) or len(hold_keys)!=12: fail("context-ambiguity hold count")
    if summary.get("decisions")!=dict(sorted(counts.items())) or summary.get("proposalCount")!=len(proposals) or summary.get("holdCellCount")!=len(holds): fail("summary decision counts")
    if summary.get("contextAmbiguityHoldSourceCount")!=1 or summary.get("candidateFreeCallerlessSourceCount")!=0: fail("summary hold provenance")
    if summary.get("placeholderMarkupNumericProtectedLiteralChecks")!="PASS" or summary.get("repositoryChangesApplied") is not False: fail("summary integrity/scope")
    if repo is not None:
        repo=repo.resolve()
        if subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD"],text=True).strip()!=HEAD: fail("repo head")
        if subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD^{tree}"],text=True).strip()!=TREE: fail("repo tree")
        if subprocess.check_output(["git","-C",str(repo),"status","--porcelain=v1","--untracked-files=all"],text=True).strip(): fail("repo worktree dirty")
    return {"result":"PASS","head":HEAD,"tree":TREE,"cells":len(ledger),"decisions":dict(sorted(counts.items())),"proposals":len(proposals),"hashOnlyHolds":len(holds),"primaryReviewAccessed":False,"candidateFreeChecksumsVerified":len(candidate_sums),"artifactFiles":len(outer),"exactHeadWorktreeChecked":repo is not None}

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("repo",nargs="?",type=Path)
    args=parser.parse_args(); print(json.dumps(verify(args.repo),ensure_ascii=False,sort_keys=True))
