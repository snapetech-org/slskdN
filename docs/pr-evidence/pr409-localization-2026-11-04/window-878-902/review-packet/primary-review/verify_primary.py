#!/usr/bin/env python3
"""Verify W80 primary-only decisions against sealed candidate-free input and exact head."""
import collections
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parent
INPUT=ROOT.parent.parent/"candidate-free"/"input"
HEAD="7a1ca27fd0519674c3b42a3e3df3638b0f671567"
TREE="b3525218d0f9676c88c4991e78775d113f18b7d9"
BRANCH="codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
TEXT_KEYS={"source","sourceText","target","currentTarget","proposedTarget","proposedTargetText","reason","resolvedTarget","resolvedTargetText","formerTargetText"}

def fail(x): raise SystemExit("FAIL: "+x)
def need(ok,x):
    if not ok: fail(x)
def sha(b): return hashlib.sha256(b).hexdigest()
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def ph(s): return collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}",s))
def tags(s): return collections.Counter(re.findall(r"</?[A-Za-z][^>]*>",s))
def nums(s): return ["".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in n) for n in re.findall(r"\d+",s)]
def prot(s):
    v=set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b",s)); v.update(x for x in ("slskdN","Tor","Wishlist","Chromaprint") if x in s); return sorted(v)
def not_less(a,b):
    x,y=collections.Counter(a),collections.Counter(b); return all(y[k]>=n for k,n in x.items())
def token_check(source,current,target=None):
    r={"sourcePlaceholderTokens":sorted(ph(source).elements()),"currentPlaceholderTokens":sorted(ph(current).elements()),
       "sourceMarkupTokens":sorted(tags(source).elements()),"currentMarkupTokens":sorted(tags(current).elements()),
       "sourceNumericTokens":nums(source),"currentNumericTokens":nums(current),"sourceProtectedLiterals":prot(source),
       "currentProtectedLiterals":[x for x in prot(source) if x in current],"placeholderParityCurrent":ph(source)==ph(current),
       "markupParityCurrent":tags(source)==tags(current),"numericTokensPreservedCurrent":not_less(nums(source),nums(current)),
       "protectedLiteralsPreservedCurrent":all(x in current for x in prot(source))}
    if target is not None: r["proposal"]={"placeholderTokens":sorted(ph(target).elements()),"markupTokens":sorted(tags(target).elements()),
        "numericTokens":nums(target),"protectedLiterals":prot(target),"placeholderParity":ph(source)==ph(target),"markupParity":tags(source)==tags(target),
        "numericTokensPreserved":not_less(nums(source),nums(target)),"protectedLiteralsPreserved":all(x in target for x in prot(source))}
    return r
def readj(root,name): return json.loads((root/name).read_text(encoding="utf-8"))
def rows(root,name): return [json.loads(x) for x in (root/name).read_text(encoding="utf-8").splitlines() if x.strip()]
def forbidden(v):
    if isinstance(v,dict): return any(k in TEXT_KEYS or forbidden(x) for k,x in v.items())
    if isinstance(v,list): return any(forbidden(x) for x in v)
    return False
def git(repo,*args): return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()
def verify_inventory():
    m=readj(ROOT,"manifest.json"); expected={x["path"] for x in m["files"]}; need(len(expected)==len(m["files"]),"duplicate manifest path")
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and p.name not in {"manifest.json","SHA256SUMS.txt"}}
    need(actual==expected,"primary manifest file inventory")
    for item in m["files"]:
        p=(ROOT/item["path"]).resolve(); need(p.is_relative_to(ROOT.resolve()) and p.is_file(),"unsafe/missing primary file")
        b=p.read_bytes(); need(len(b)==item["bytes"] and sha(b)==item["sha256"],"primary file hash: "+item["path"])
    sums={}
    for line in (ROOT/"SHA256SUMS.txt").read_text().splitlines():
        if not line.strip(): continue
        d,n=line.split("  ",1); need(n not in sums,"duplicate primary checksum"); sums[n]=d
        p=(ROOT/n).resolve(); need(p.is_relative_to(ROOT.resolve()) and p.is_file() and sha(p.read_bytes())==d,"primary checksum mismatch: "+n)
    need(set(sums)==expected|{"manifest.json"},"primary checksum inventory")
    need((m.get("artifact"),m.get("window"),m.get("head"),m.get("tree"),m.get("sourceCount"),m.get("localeCount"),m.get("cellCount"),m.get("proposalCount"),m.get("holdCount"))==
         ("slskdN PR #409 W80 independent primary semantic review","W80",HEAD,TREE,25,12,300,55,0),"primary manifest identity/count")
    need(m.get("candidateFree") is True and m.get("blindReviewUsed") is False and m.get("crossReviewUsed") is False and m.get("nativeSpeakerSignoff") is False and m.get("browserReview") is False and m.get("prBodyQueried") is False,"primary scope flags")
    return m,len(sums)
def live_check(repo,manifest):
    before=readj(ROOT,"live-before.json"); after=readj(ROOT,"live-after.json"); att=readj(ROOT,"head-tree-attestation.json")
    need(att.get("liveBefore")==before and att.get("liveAfter")==after,"primary live attestation")
    for x in (before,after):
        need(not any("body" in k.lower() for k in x if k!="prBodyQueried") and x.get("prBodyQueried") is False,"primary PR body key/flag")
        need((x.get("repository"),x.get("pullRequest"),x.get("state"),x.get("draft"),x.get("merged"),x.get("headRefName"),x.get("headRefOid"),x.get("branchRefOid"),x.get("pullRefOid"),x.get("baseRefName"),x.get("baseRefOid"),x.get("commitTree"))==
             ("snapetech-org/slskdN",409,"OPEN",True,False,BRANCH,HEAD,HEAD,HEAD,"main","f25d263a2a7cdb2c8f76c40c346cb10f749a9356",TREE),"primary live exact ref snapshot")
    keys=("repository","pullRequest","state","draft","merged","headRefName","headRefOid","branchRefOid","pullRefOid","baseRefName","baseRefOid","liveMainSha","commitTree")
    need(all(before.get(k)==after.get(k) for k in keys),"primary live state changed during review")
    need(git(repo,"rev-parse","HEAD")==HEAD and git(repo,"rev-parse","HEAD^{tree}")==TREE and not git(repo,"status","--porcelain=v1"),"primary source worktree exact clean head")
    remote=subprocess.check_output(["git","ls-remote","https://github.com/snapetech-org/slskdN.git",f"refs/heads/{BRANCH}","refs/pull/409/head"],text=True)
    refs={x.split()[1]:x.split()[0] for x in remote.splitlines() if x.strip()}
    need(refs.get(f"refs/heads/{BRANCH}")==HEAD and refs.get("refs/pull/409/head")==HEAD,"primary live branch/pull ref")

def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("--repo",required=True); repo=Path(ap.parse_args().repo).resolve()
    manifest,checks=verify_inventory()
    input_result=json.loads(subprocess.check_output(["python3",str(INPUT/"verify_input.py"),"--repo",str(repo)],text=True))
    need(input_result.get("result")=="PASS" and input_result.get("head")==HEAD and input_result.get("tree")==TREE and input_result.get("window")=="W80","candidate-free verifier")
    live_check(repo,manifest)
    need(manifest["candidateFreeInputManifestSha256"]==sha((INPUT/"manifest.json").read_bytes()) and manifest["candidateFreeInputChecksumListSha256"]==sha((INPUT/"PACKET-SHA256SUMS.txt").read_bytes()),"candidate-free packet link")
    for field,name in (("sourceInventorySelectionSha256","source-inventory-selection.jsonl"),("callerContextSha256","caller-contexts.jsonl"),("sourceCurrentCellsSha256","source-current-cells.jsonl"),("selectionBoundarySha256","selection-boundary.jsonl")):
        need(manifest.get(field)==sha((INPUT/name).read_bytes()),"candidate-free link: "+name)
    primary_drift=readj(ROOT,"main-drift.json"); input_drift=readj(INPUT,"main-drift.json")
    need((primary_drift["baseApiSha"],primary_drift["liveMainBeforeSha"],primary_drift["liveMainAfterSha"],primary_drift["localizationOrCatalogChanges"])==
         (input_drift["baseApiSha"],input_drift["liveMainBeforeSha"],input_drift["liveMainAfterSha"],False),"primary/main drift")
    source_cells=rows(INPUT,"source-current-cells.jsonl"); callers=rows(INPUT,"caller-contexts.jsonl"); ledger=rows(ROOT,"primary-review.jsonl"); corrections=rows(ROOT,"corrections.jsonl"); holds=rows(ROOT,"holds-hash-only.jsonl")
    need((len(source_cells),len(callers),len(ledger),len(corrections),len(holds))==(300,25,300,55,0),"primary cell/proposal coverage")
    need([ (r["continuationRank"],r["locale"]) for r in ledger ]==[(r["continuationRank"],r["locale"]) for r in source_cells],"primary ledger ordering/coverage")
    caller_by_id={r["sourceId"]:r for r in callers}; corrmap={(r["continuationRank"],r["locale"]):r for r in corrections}
    need(len(corrmap)==55,"duplicate correction cell")
    for inp,row in zip(source_cells,ledger):
        rank,locale=inp["continuationRank"],inp["locale"]; caller=caller_by_id[inp["sourceId"]]
        for key in ("continuationRank","remainingQueueRank","sourceId","sourceSha256","locale","catalogPath","catalogFileSha256","catalogGitBlob","currentTargetSha256","callerContextSha256","callerRefs"):
            need(row.get(key)==inp.get(key),f"primary/input binding {rank}/{locale}/{key}")
        need(row.get("productionCallerCount")==caller["productionCallerCount"] and row.get("callerRefs")==inp["callerRefs"],f"caller binding {rank}/{locale}")
        if caller["productionCallerCount"]:
            need(row.get("source")==inp["source"] and row.get("catalogKey")==inp["catalogKey"] and row.get("currentTarget")==inp["currentTarget"],f"visible text binding {rank}/{locale}")
            need(row.get("sourceTextIncluded") is True and row.get("currentTargetTextIncluded") is True,f"text flags {rank}/{locale}")
            expected_token=token_check(inp["source"],inp["currentTarget"],row.get("target") if row.get("disposition")=="correct" else None)
            need(row.get("tokenCheck")==expected_token,f"token evidence {rank}/{locale}")
        else:
            need(row.get("disposition")=="hold" and row.get("sourceTextIncluded") is False and row.get("currentTargetTextIncluded") is False and not any(k in row for k in ("source","catalogKey","currentTarget","target")),f"callerless text-free hold {rank}/{locale}")
            need(not forbidden(row),f"callerless hold forbidden text {rank}/{locale}")
        disposition=row.get("disposition")
        need(disposition in {"accept-current","correct","hold"},f"invalid disposition {rank}/{locale}")
        if disposition=="correct":
            need(row.get("target") and row.get("targetSha256")==sha(row["target"].encode("utf-8")),f"target hash {rank}/{locale}")
            need(row.get("proposalTokenCheck")==token_check(inp["source"],inp["currentTarget"],row["target"])["proposal"],f"proposal token record {rank}/{locale}")
            need(ph(inp["source"])==ph(row["target"]) and tags(inp["source"])==tags(row["target"]) and not_less(nums(inp["source"]),nums(row["target"])) and all(t in row["target"] for t in prot(inp["source"])),f"proposal token safety {rank}/{locale}")
            need((rank,locale) in corrmap and corrmap[(rank,locale)]==row,f"correction map row {rank}/{locale}")
        elif disposition=="accept-current":
            need(not any(k in row for k in ("target","targetSha256","proposedTarget")),f"accept-current target field {rank}/{locale}")
            need((rank,locale) not in corrmap,f"accept-current appears in correction ledger {rank}/{locale}")
        else:
            need((rank,locale) not in corrmap,f"hold appears in correction ledger {rank}/{locale}")
    proposal_map=readj(ROOT,"proposal-map.json")
    need(set(proposal_map)=={f"{r['continuationRank']}|{r['locale']}" for r in corrections},"proposal map keys")
    need(all(proposal_map[f"{r['continuationRank']}|{r['locale']}"]==r["target"] for r in corrections),"proposal map targets")
    recs=readj(ROOT,"source-rewrite-recommendations.json"); need(recs=={"schemaVersion":1,"recommendations":[]},"source rewrite recommendations")
    summary=readj(ROOT,"summary.json"); counts=collections.Counter(r["disposition"] for r in ledger)
    expected={k:counts.get(k,0) for k in ("accept-current","correct","hold")}
    need(summary["dispositions"]==expected and expected=={"accept-current":245,"correct":55,"hold":0},"primary summary counts")
    need(summary["proposedTargetCount"]==55 and summary["hashOnlyHoldCount"]==0 and summary["priorSelectedIdsExcluded"]==1957 and summary["priorHeldCellsCarried"]==382 and summary["priorHoldResolutionHistoryRows"]==13 and summary["priorAppliedTargetsReattested"]==109 and summary["w79AppliedTargets"]==46 and summary["w79HoldsCarried"]==39 and summary["w79CallerlessHoldsHashOnly"]==24,"primary continuity summary")
    need(not holds,"unexpected W80 primary holds")
    print(json.dumps({"result":"PASS","window":"W80","head":HEAD,"tree":TREE,"sourceCount":25,"localeCount":12,"cellCount":300,
                      "dispositions":expected,"proposals":55,"primaryHolds":0,"priorHeldCells":382,"priorAppliedTargets":109,"w79Corrections":46,
                      "w79Holds":39,"w79CallerlessHoldsHashOnly":24,"candidateFreeVerifier":"PASS","liveRefs":"PASS","packetChecksums":checks,
                      "prBodyQueried":False,"blindReviewUsed":False,"crossReviewUsed":False},ensure_ascii=False,indent=2))


if __name__=="__main__": main()
