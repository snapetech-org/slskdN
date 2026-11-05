#!/usr/bin/env python3
"""Seal the W80 candidate-free input after a fresh filtered live-state capture."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEAD = "7a1ca27fd0519674c3b42a3e3df3638b0f671567"
TREE = "b3525218d0f9676c88c4991e78775d113f18b7d9"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]


def sha(data): return hashlib.sha256(data).hexdigest()
def j(path): return json.loads((ROOT / path).read_text(encoding="utf-8"))
def rows(path): return [json.loads(x) for x in (ROOT / path).read_text(encoding="utf-8").splitlines() if x.strip()]
def git(repo, *args): return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

def main():
    repo = Path(sys.argv[1]).resolve()
    subprocess.check_call(["python3", str(ROOT / "capture_live.py"), "after"], cwd=ROOT)
    before, after = j("live-before.json"), j("live-after.json")
    if (before["headRefOid"], before["commitTree"], after["headRefOid"], after["commitTree"]) != (HEAD, TREE, HEAD, TREE):
        raise SystemExit("REFUSED: W80 head/tree changed")
    if git(repo, "rev-parse", "HEAD") != HEAD or git(repo, "rev-parse", "HEAD^{tree}") != TREE or git(repo, "status", "--porcelain=v1"):
        raise SystemExit("REFUSED: W80 source worktree pin or cleanliness")
    remote = subprocess.check_output(["git", "ls-remote", "https://github.com/snapetech-org/slskdN.git", f"refs/heads/{BRANCH}", "refs/pull/409/head", "refs/pull/409/merge"], text=True)
    remote_rows = {line.split()[1]: line.split()[0] for line in remote.splitlines() if line.strip()}
    attestation = {"repository": "snapetech-org/slskdN", "pullRequest": 409, "headRefName": BRANCH, "headRefOid": HEAD,
                   "treeOid": TREE, "baseRefName": "main", "baseRefOid": before["baseRefOid"], "state": "OPEN", "draft": True,
                   "branchRefOid": remote_rows.get(f"refs/heads/{BRANCH}"), "pullRefOid": remote_rows.get("refs/pull/409/head"),
                   "pullMergeRefOid": remote_rows.get("refs/pull/409/merge"), "liveBefore": before, "liveAfter": after,
                   "localHead": git(repo, "rev-parse", "HEAD"), "localTree": git(repo, "rev-parse", "HEAD^{tree}"), "worktreeClean": True,
                   "prBodyQueried": False}
    (ROOT / "head-tree-attestation.json").write_text(json.dumps(attestation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    selected, cells, runtime, callers = rows("source-inventory-selection.jsonl"), rows("source-current-cells.jsonl"), rows("runtime-file-pins.jsonl"), rows("caller-contexts.jsonl")
    prior_ids, holds, resolutions = rows("prior-selected-id-exclusions-hash-only.jsonl"), rows("prior-held-cell-reattestation-hash-only.jsonl"), rows("prior-hold-resolution-history-hash-only.jsonl")
    applied, w79_holds, w79_applied = rows("prior-applied-targets-reattestation-hash-only.jsonl"), rows("previous-window-holds-hash-only.jsonl"), rows("previous-window-applied-targets-hash-only.jsonl")
    catalogs = rows("catalog-structure.jsonl")
    if (len(selected), len(cells), len(runtime), len(callers), len(prior_ids), len(holds), len(resolutions), len(applied), len(w79_holds), len(w79_applied), len(catalogs)) != (25, 300, 279, 25, 1957, 382, 13, 109, 39, 46, 12):
        raise SystemExit("REFUSED: W80 packet coverage")
    if not all(r["matchesPriorCurrentValue"] and r["callerEvidenceUnchanged"] for r in holds): raise SystemExit("REFUSED: prior hold reattestation mismatch")
    if not all(r["targetRemainsApplied"] for r in applied): raise SystemExit("REFUSED: prior applied target mismatch")
    prior_summary = j("prior-hold-lineage-summary.json")
    if prior_summary["holdLineage"].get("W79") != 39 or prior_summary["carriedHoldCells"] != 382:
        raise SystemExit("REFUSED: W79 hold carry not attested")
    drift = j("main-drift.json")
    if (drift["baseApiSha"], drift["liveMainBeforeSha"], drift["liveMainAfterSha"], drift["localizationOrCatalogChanges"]) != (before["baseRefOid"], before["liveMainSha"], after["liveMainSha"], False):
        raise SystemExit("REFUSED: base/main drift changed or catalog paths changed")
    files = []
    for path in sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name not in {"manifest.json", "PACKET-SHA256SUMS.txt"}):
        files.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path.read_bytes())})
    manifest = {"artifact": "slskdN PR #409 W80 ranks 878-902 candidate-free exact-head input", "schemaVersion": 1,
                "repository": "snapetech-org/slskdN", "pullRequest": 409, "branch": BRANCH, "window": "W80", "candidateFree": True,
                "head": HEAD, "tree": TREE, "liveBefore": before, "liveAfter": after, "continuationRankRange": [878, 902],
                "remainingQueueRankRange": [778, 802], "sourceCount": 25, "localeCount": 12, "cellCount": 300, "locales": LOCALES,
                "catalogEntryCountPerLocale": 6176, "sourceInventoryPath": "docs/pr-evidence/pr409-localization-2026-11-03/window49/primary/source-inventory.jsonl",
                "sourceInventoryRows": 6176, "sourceInventorySha256": j("source-tree-attestation.json")["sourceInventoryRawSha256"],
                "sourceInventoryProjectionSha256": sha((ROOT / "source-inventory-pinned.jsonl").read_bytes()),
                "orderedCatalogKeySha256": j("selection-and-boundary.json")["orderedCatalogKeySha256"],
                "productionCallerFileCount": len(runtime), "sourcesWithCallers": sum(x["productionCallerCount"] > 0 for x in callers),
                "sourcesWithoutCallers": sum(x["productionCallerCount"] == 0 for x in callers), "priorSelectedIdsExcluded": len(prior_ids),
                "priorHeldCellsReattested": len(holds), "priorHoldResolutionHistoryRows": len(resolutions), "priorAppliedTargetsReattested": len(applied),
                "priorAppliedTargetsByWindow": {"W78": 63, "W79": 46}, "previousWindowHolds": len(w79_holds), "previousWindowCallerlessHolds": sum(x["callerlessHashOnly"] for x in w79_holds),
                "priorHoldLineage": prior_summary["holdLineage"], "priorHeldTargetHashesAllMatch": all(x["matchesPriorCurrentValue"] for x in holds),
                "priorHeldCallerEvidenceUnchanged": sum(x["callerEvidenceUnchanged"] for x in holds), "priorHeldCallerEvidenceChanged": sum(not x["callerEvidenceUnchanged"] for x in holds),
                "baselineTokenMismatchSummary": j("baseline-token-mismatch-summary.json")["mismatchCounts"],
                "proposedTargetsIncluded": False, "reviewDecisionsIncluded": False, "blindReviewUsed": False, "crossReviewUsed": False,
                "prBodyQueried": False, "liveMainBefore": drift["liveMainBeforeSha"], "liveMainAfter": drift["liveMainAfterSha"],
                "mainDriftSha256": sha((ROOT / "main-drift.json").read_bytes()), "continuityProvenanceSha256": sha((ROOT / "continuity-provenance.json").read_bytes()), "files": files}
    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checksum_names = sorted([x["path"] for x in files] + ["manifest.json"])
    (ROOT / "PACKET-SHA256SUMS.txt").write_text("".join(f"{sha((ROOT / name).read_bytes())}  {name}\n" for name in checksum_names), encoding="utf-8")
    print(json.dumps({"result": "SEALED-CANDIDATE-FREE", "head": HEAD, "tree": TREE, "sources": len(selected), "cells": len(cells),
                      "runtimeFiles": len(runtime), "priorSelectedIds": len(prior_ids), "priorHeldCells": len(holds), "holdResolutions": len(resolutions),
                      "priorAppliedTargets": len(applied), "w79Corrections": 46, "w79Holds": len(w79_holds), "w79CallerlessHolds": sum(x["callerlessHashOnly"] for x in w79_holds),
                      "packetFiles": len(checksum_names), "prBodyQueried": False}, indent=2))


if __name__ == "__main__": main()
