#!/usr/bin/env python3
"""Seal the W81 candidate-free input after final filtered live-state capture."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
HEAD="91da6fff5d5b628ade7ee556386e3db1db6878fa"
TREE="56930b73d10a4c419edf68f0d951ceedaa63c990"
BRANCH="codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
def sha(b): return hashlib.sha256(b).hexdigest()
def j(name): return json.loads((ROOT/name).read_text(encoding="utf-8"))
def rows(name): return [json.loads(x) for x in (ROOT/name).read_text(encoding="utf-8").splitlines() if x.strip()]
def git(repo,*args): return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()
def main():
    repo=Path(sys.argv[1]).resolve()
    subprocess.check_call(["python3",str(ROOT/"capture_live.py"),"after"],cwd=ROOT)
    before,after=j("live-before.json"),j("live-after.json")
    if (before["headRefOid"],before["commitTree"],after["headRefOid"],after["commitTree"])!=(HEAD,TREE,HEAD,TREE):
        raise SystemExit("REFUSED: W81 live head/tree changed")
    if git(repo,"rev-parse","HEAD")!=HEAD or git(repo,"rev-parse","HEAD^{tree}")!=TREE or git(repo,"status","--porcelain=v1"):
        raise SystemExit("REFUSED: W81 worktree pin/cleanliness")
    stable=("repository","pullRequest","state","draft","merged","headRefName","headRefOid","branchRefOid","pullRefOid","baseRefName","baseRefOid","liveMainSha","commitTree")
    if any(before.get(k)!=after.get(k) for k in stable): raise SystemExit("REFUSED: live PR refs changed during extraction")
    att={"repository":"snapetech-org/slskdN","pullRequest":409,"headRefName":BRANCH,"headRefOid":HEAD,"treeOid":TREE,
         "baseRefName":"main","baseRefOid":before["baseRefOid"],"state":"OPEN","draft":True,
         "branchRefOid":after["branchRefOid"],"pullRefOid":after["pullRefOid"],"pullMergeRefOid":after.get("pullMergeRefOid"),
         "liveBefore":before,"liveAfter":after,"localHead":git(repo,"rev-parse","HEAD"),
         "localTree":git(repo,"rev-parse","HEAD^{tree}"),"worktreeClean":True,"prBodyQueried":False}
    (ROOT/"head-tree-attestation.json").write_text(json.dumps(att,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    selected,cells,runtime,callers=(rows(n) for n in ("source-inventory-selection.jsonl","source-current-cells.jsonl","runtime-file-pins.jsonl","caller-contexts.jsonl"))
    prior_ids,holds,resolutions,applied=(rows(n) for n in ("prior-selected-id-exclusions-hash-only.jsonl","prior-held-cell-reattestation-hash-only.jsonl","prior-hold-resolution-history-hash-only.jsonl","prior-applied-targets-reattestation-hash-only.jsonl"))
    previous_holds,previous_new_holds,previous_applied,catalogs=(rows(n) for n in ("previous-window-prior-holds-hash-only.jsonl","previous-window-holds-hash-only.jsonl","previous-window-applied-targets-hash-only.jsonl","catalog-structure.jsonl"))
    if (len(selected),len(cells),len(runtime),len(callers),len(prior_ids),len(holds),len(resolutions),len(applied),len(previous_holds),len(previous_new_holds),len(previous_applied),len(catalogs))!=(25,300,279,25,1982,382,13,190,382,0,81,12):
        raise SystemExit("REFUSED: W81 candidate-free coverage")
    if not all(x["matchesPriorCurrentValue"] and x["callerEvidenceUnchanged"] for x in holds):
        raise SystemExit("REFUSED: prior hold current-target/caller reattestation")
    if not all(x["targetRemainsApplied"] for x in applied):
        raise SystemExit("REFUSED: prior applied-target reattestation")
    if any(x["containsCandidate"] or x.get("verdict") is not None for x in cells):
        raise SystemExit("REFUSED: candidate/review decision appeared in input")
    if any(x["sourceWithoutCaller"] if "sourceWithoutCaller" in x else False for x in callers):
        raise SystemExit("REFUSED: malformed caller row")
    drift=j("main-drift.json")
    if (drift["baseApiSha"],drift["liveMainBeforeSha"],drift["liveMainAfterSha"],drift["localizationOrCatalogChanges"])!=(before["baseRefOid"],before["liveMainSha"],after["liveMainSha"],False):
        raise SystemExit("REFUSED: main drift changed or includes source/catalog paths")
    prior=j("prior-hold-lineage-summary.json")
    if prior["carriedHoldCells"]!=382 or prior["previouslyResolvedHistoricalRows"]!=13:
        raise SystemExit("REFUSED: prior hold lineage summary")
    base=j("manifest.json")
    base.update({"liveBefore":before,"liveAfter":after,"liveMainBefore":drift["liveMainBeforeSha"],"liveMainAfter":drift["liveMainAfterSha"],
                 "sourcesWithCallers":sum(x["productionCallerCount"]>0 for x in callers),
                 "sourcesWithoutCallers":sum(x["productionCallerCount"]==0 for x in callers),
                 "priorHeldTargetHashesAllMatch":all(x["matchesPriorCurrentValue"] for x in holds),
                 "priorHeldCallerEvidenceUnchanged":sum(x["callerEvidenceUnchanged"] for x in holds),
                 "priorHeldCallerEvidenceChanged":sum(not x["callerEvidenceUnchanged"] for x in holds),
                 "previousWindowHolds":len(previous_new_holds),"previousWindowPriorHolds":len(previous_holds),
                 "previousWindowAppliedTargets":len(previous_applied),"prBodyQueried":False,
                 "proposedTargetsIncluded":False,"reviewDecisionsIncluded":False,"blindReviewUsed":False,"crossReviewUsed":False})
    files=[]
    excluded={"manifest.json","PACKET-SHA256SUMS.txt","__pycache__"}
    for p in sorted(x for x in ROOT.rglob("*") if x.is_file() and not any(part in excluded for part in x.relative_to(ROOT).parts)):
        files.append({"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())})
    base["files"]=files
    (ROOT/"manifest.json").write_text(json.dumps(base,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    names=sorted([f["path"] for f in files]+["manifest.json"])
    (ROOT/"PACKET-SHA256SUMS.txt").write_text("".join(f"{sha((ROOT/n).read_bytes())}  {n}\n" for n in names),encoding="utf-8")
    print(json.dumps({"result":"SEALED-CANDIDATE-FREE","head":HEAD,"tree":TREE,"sourceCount":len(selected),"cellCount":len(cells),
        "runtimeFiles":len(runtime),"sourcesWithCallers":sum(x["productionCallerCount"]>0 for x in callers),"priorSelectedIds":len(prior_ids),
        "priorHolds":len(holds),"priorHoldResolutions":len(resolutions),"priorAppliedTargets":len(applied),
        "newPriorWindowHolds":len(previous_new_holds),"newPriorWindowApplied":len(previous_applied),
        "tokenMismatches":base["baselineTokenMismatchSummary"],"mainLocalizationChanges":drift["localizationOrCatalogChanges"],
        "packetFiles":len(names),"prBodyQueried":False},ensure_ascii=False,indent=2))
if __name__=="__main__": main()

