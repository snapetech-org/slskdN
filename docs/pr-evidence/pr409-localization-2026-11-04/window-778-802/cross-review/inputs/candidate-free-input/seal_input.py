#!/usr/bin/env python3
"""Seal the W76 candidate-free packet after the live-after PR check."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEAD = "674156749ee86021ef91d896b1824be62cff9a93"
TREE = "86483dbf9227130cade6a3f4c9dc9ef5cf232450"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def lines(name):
    return [json.loads(line) for line in (ROOT / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def main():
    repo = Path(sys.argv[1] if len(sys.argv) > 1 else "/mnt/disks/scratch/task-worktrees/localization-20261104/slskdn-pr409-w76-778-802-source").resolve()
    before, after = load("live-before.json"), load("live-after.json")
    for live in (before, after):
        if (live.get("repository"), live.get("pullRequest"), live.get("state"), live.get("draft"), live.get("merged")) != ("snapetech-org/slskdN", 409, "OPEN", True, False):
            raise SystemExit("REFUSED: PR is not open/draft at the expected repository")
        if (live.get("headRefName"), live.get("headRefOid"), live.get("baseRefName"), live.get("baseRefOid")) != (
            BRANCH, HEAD, "main", "f25d263a2a7cdb2c8f76c40c346cb10f749a9356"
        ):
            raise SystemExit("REFUSED: PR ref/base changed")
        if (live.get("branchRefOid"), live.get("pullRefOid")) != (HEAD, HEAD):
            raise SystemExit("REFUSED: branch or pull head ref differs")
    fields = ("repository", "pullRequest", "state", "draft", "merged", "headRefName", "headRefOid", "branchRefOid", "pullRefOid", "baseRefName", "baseRefOid")
    if any(before.get(field) != after.get(field) for field in fields):
        raise SystemExit("REFUSED: PR state or refs changed during extraction")
    if git(repo, "rev-parse", "HEAD") != HEAD or git(repo, "rev-parse", "HEAD^{tree}") != TREE:
        raise SystemExit("REFUSED: local worktree pin changed")
    if git(repo, "status", "--porcelain=v1"):
        raise SystemExit("REFUSED: local worktree is dirty")
    refs = subprocess.check_output([
        "git", "ls-remote", "https://github.com/snapetech-org/slskdN.git",
        f"refs/heads/{BRANCH}", "refs/pull/409/head", "refs/pull/409/merge"
    ], text=True)
    remote = {line.split()[1]: line.split()[0] for line in refs.splitlines() if line.strip()}
    if remote.get(f"refs/heads/{BRANCH}") != HEAD or remote.get("refs/pull/409/head") != HEAD:
        raise SystemExit("REFUSED: live GitHub branch/pull refs differ from the pinned input")
    attestation = {
        "repository": "snapetech-org/slskdN", "pullRequest": 409, "headRefName": BRANCH,
        "headRefOid": HEAD, "treeOid": TREE, "baseRefName": "main",
        "baseRefOid": "f25d263a2a7cdb2c8f76c40c346cb10f749a9356",
        "state": "OPEN", "draft": True, "branchRefOid": remote[f"refs/heads/{BRANCH}"],
        "pullRefOid": remote["refs/pull/409/head"], "pullMergeRefOid": remote.get("refs/pull/409/merge"),
        "liveBefore": before, "liveAfter": after,
        "localHead": git(repo, "rev-parse", "HEAD"), "localTree": git(repo, "rev-parse", "HEAD^{tree}"),
        "worktreeClean": True
    }
    (ROOT / "head-tree-attestation.json").write_text(json.dumps(attestation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    selected = lines("source-inventory-selection.jsonl")
    cells = lines("source-current-cells.jsonl")
    runtime = lines("runtime-file-pins.jsonl")
    callers = lines("caller-contexts.jsonl")
    prior_holds = lines("prior-held-cell-reattestation-hash-only.jsonl")
    prior_ids = lines("prior-selected-id-exclusions-hash-only.jsonl")
    prior_resolutions = lines("prior-hold-resolution-history-hash-only.jsonl")
    catalog_rows = lines("catalog-structure.jsonl")
    selection = load("selection-and-boundary.json")
    token_summary = load("baseline-token-mismatch-summary.json")
    continuity = load("continuity-provenance.json")
    if (len(selected), len(cells), len(runtime), len(callers), len(prior_holds), len(prior_ids), len(prior_resolutions), len(catalog_rows)) != (25, 300, 279, 25, 271, 1857, 13, 12):
        raise SystemExit("REFUSED: packet coverage counts do not match W76")

    files = []
    for path in sorted(item for item in ROOT.rglob("*") if item.is_file() and item.name not in {"manifest.json", "PACKET-SHA256SUMS.txt"}):
        files.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path.read_bytes())})
    manifest = {
        "artifact": "slskdN PR #409 W76 ranks 778-802 candidate-free exact-head input",
        "schemaVersion": 1, "repository": "snapetech-org/slskdN", "pullRequest": 409,
        "branch": BRANCH, "window": "W76", "candidateFree": True,
        "head": HEAD, "tree": TREE, "liveBefore": before, "liveAfter": after,
        "continuationRankRange": [778, 802], "remainingQueueRankRange": [678, 702],
        "sourceCount": 25, "localeCount": 12, "cellCount": 300, "locales": LOCALES,
        "catalogEntryCountPerLocale": 6176,
        "sourceInventoryPath": "docs/pr-evidence/pr409-localization-2026-11-03/window49/primary/source-inventory.jsonl",
        "sourceInventoryRows": 6176, "sourceInventorySha256": sha((ROOT / "source-inventory-pinned.jsonl").read_bytes()),
        "orderedCatalogKeySha256": selection["orderedCatalogKeySha256"],
        "productionCallerFileCount": len(runtime), "callerlessSourceCount": sum(row["productionCallerCount"] == 0 for row in callers),
        "priorSelectedIdsExcluded": len(prior_ids), "priorHeldCellsReattested": len(prior_holds),
        "priorHoldResolutionHistoryRows": len(prior_resolutions),
        "priorHoldLineage": load("prior-hold-lineage-summary.json")["holdLineage"],
        "priorHeldTargetHashesAllMatch": load("prior-held-cell-reattestation-summary.json")["allTargetHashesMatchPrior"],
        "priorHeldCallerEvidenceUnchanged": load("prior-held-cell-reattestation-summary.json")["callerEvidenceUnchanged"],
        "priorHeldCallerEvidenceChanged": load("prior-held-cell-reattestation-summary.json")["callerEvidenceChanged"],
        "baselineTokenMismatchSummary": token_summary["mismatchCounts"],
        "proposedTargetsIncluded": False, "reviewDecisionsIncluded": False,
        "blindReviewUsed": False, "crossReviewUsed": False,
        "continuitySourceManifestSha256": continuity["previousCandidateFreeManifestSha256"],
        "continuitySourceChecksumListSha256": continuity["previousCandidateFreeChecksumListSha256"],
        "files": files
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checksum_rows = []
    for name in sorted([item["path"] for item in files] + ["manifest.json"]):
        checksum_rows.append(f"{sha((ROOT / name).read_bytes())}  {name}\n")
    (ROOT / "PACKET-SHA256SUMS.txt").write_text("".join(checksum_rows), encoding="utf-8")
    print(json.dumps({
        "result": "SEALED-CANDIDATE-FREE", "head": HEAD, "tree": TREE, "sourceCount": len(selected),
        "cellCount": len(cells), "runtimeFilePins": len(runtime), "priorSelectedIds": len(prior_ids),
        "priorHeldCells": len(prior_holds), "priorHoldResolutions": len(prior_resolutions),
        "candidateOutputsIncluded": False, "packetFiles": len(checksum_rows)
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
