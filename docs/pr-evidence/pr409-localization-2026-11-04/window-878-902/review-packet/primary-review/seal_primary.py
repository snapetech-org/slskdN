#!/usr/bin/env python3
"""Seal the W80 independent primary-review packet after live-ref recheck."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEAD = "7a1ca27fd0519674c3b42a3e3df3638b0f671567"
TREE = "b3525218d0f9676c88c4991e78775d113f18b7d9"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
INPUT = ROOT.parent.parent / "candidate-free" / "input"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]


def sha(b): return hashlib.sha256(b).hexdigest()
def readj(path): return json.loads((ROOT/path).read_text(encoding="utf-8"))
def rows(path): return [json.loads(x) for x in (ROOT/path).read_text(encoding="utf-8").splitlines() if x.strip()]
def git(repo,*args): return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()

def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("--repo",required=True); repo=Path(ap.parse_args().repo).resolve()
    subprocess.check_call(["python3",str(ROOT/"capture_live.py"),"after"],cwd=ROOT)
    before,after=readj("live-before.json"),readj("live-after.json")
    if (before["headRefOid"],before["commitTree"],after["headRefOid"],after["commitTree"])!=(HEAD,TREE,HEAD,TREE): raise SystemExit("REFUSED: primary live head/tree")
    if git(repo,"rev-parse","HEAD")!=HEAD or git(repo,"rev-parse","HEAD^{tree}")!=TREE or git(repo,"status","--porcelain=v1"): raise SystemExit("REFUSED: primary source worktree pin/cleanliness")
    if (ROOT/"main-drift-before.json").read_bytes() != (INPUT/"main-drift.json").read_bytes():
        # Capture time differs from the input packet; compare stable underlying state instead of requiring byte identity.
        primary_drift=readj("main-drift-before.json"); input_drift=json.loads((INPUT/"main-drift.json").read_text(encoding="utf-8"))
        if (primary_drift["baseApiSha"],primary_drift["liveMainSha"],primary_drift["changedPaths"]) != (input_drift["baseApiSha"],input_drift["liveMainAfterSha"],input_drift["changedPaths"]):
            raise SystemExit("REFUSED: candidate-free and primary main drift differs")
    remote=subprocess.check_output(["git","ls-remote","https://github.com/snapetech-org/slskdN.git",f"refs/heads/{BRANCH}","refs/pull/409/head","refs/pull/409/merge"],text=True)
    refs={x.split()[1]:x.split()[0] for x in remote.splitlines() if x.strip()}
    att={"repository":"snapetech-org/slskdN","pullRequest":409,"headRefName":BRANCH,"headRefOid":HEAD,"treeOid":TREE,
         "baseRefName":"main","baseRefOid":before["baseRefOid"],"state":"OPEN","draft":True,"branchRefOid":refs.get(f"refs/heads/{BRANCH}"),
         "pullRefOid":refs.get("refs/pull/409/head"),"pullMergeRefOid":refs.get("refs/pull/409/merge"),"liveBefore":before,"liveAfter":after,
         "localHead":git(repo,"rev-parse","HEAD"),"localTree":git(repo,"rev-parse","HEAD^{tree}"),"worktreeClean":True,"prBodyQueried":False}
    (ROOT/"head-tree-attestation.json").write_text(json.dumps(att,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary=readj("summary.json"); ledger=rows("primary-review.jsonl"); corrections=rows("corrections.jsonl"); holds=rows("holds-hash-only.jsonl")
    if (len(ledger),len(corrections),len(holds))!=(300,55,0): raise SystemExit("REFUSED: W80 primary counts")
    files=[]
    for p in sorted(x for x in ROOT.rglob("*") if x.is_file() and x.name not in {"manifest.json","SHA256SUMS.txt"}):
        files.append({"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())})
    manifest={"artifact":"slskdN PR #409 W80 independent primary semantic review","schemaVersion":1,"repository":"snapetech-org/slskdN","pullRequest":409,
              "branch":BRANCH,"window":"W80","head":HEAD,"tree":TREE,"candidateFree":True,"candidateFreeInputManifestSha256":summary["candidateFreeInputManifestSha256"],
              "candidateFreeInputChecksumListSha256":summary["candidateFreeInputChecksumListSha256"],"sourceInventorySelectionSha256":summary["sourceInventorySelectionSha256"],
              "callerContextSha256":summary["callerContextSha256"],"sourceCurrentCellsSha256":summary["sourceCurrentCellsSha256"],"selectionBoundarySha256":summary["selectionBoundarySha256"],
              "sourceCount":25,"localeCount":12,"cellCount":300,"locales":LOCALES,"decisionCounts":summary["dispositions"],"proposalCount":len(corrections),"holdCount":len(holds),
              "blindReviewUsed":False,"crossReviewUsed":False,"nativeSpeakerSignoff":False,"browserReview":False,"sourceRewriteRecommendations":0,"prBodyQueried":False,
              "liveBefore":before,"liveAfter":after,"files":files}
    (ROOT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    names=sorted([x["path"] for x in files]+["manifest.json"])
    (ROOT/"SHA256SUMS.txt").write_text("".join(f"{sha((ROOT/n).read_bytes())}  {n}\n" for n in names),encoding="utf-8")
    print(json.dumps({"result":"SEALED-PRIMARY","head":HEAD,"tree":TREE,"sourceCount":25,"cellCount":300,"decisionCounts":summary["dispositions"],
                      "proposalCount":len(corrections),"holdCount":len(holds),"packetFiles":len(names),"prBodyQueried":False},ensure_ascii=False,indent=2))


if __name__=="__main__": main()
