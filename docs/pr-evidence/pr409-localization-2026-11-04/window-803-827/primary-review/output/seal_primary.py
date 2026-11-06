#!/usr/bin/env python3
"""Seal the W77 primary review after live-ref and worktree reattestation."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent.parent / "candidate-free" / "input"
HEAD = "582ae64e5c3af275490f11f4350b33da7373a3c3"
TREE = "b8692bb066cede93b6668806d0b97816135ce647"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def readj(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def main():
    repo = Path(sys.argv[1] if len(sys.argv) > 1 else "/mnt/disks/scratch/task-worktrees/localization-20261104/slskdn-pr409-w76-778-802-source").resolve()
    before, after = readj("live-before.json"), readj("live-after.json")
    expected = {
        "repository": "snapetech-org/slskdN", "pullRequest": 409, "state": "OPEN", "draft": True, "merged": False,
        "headRefName": BRANCH, "headRefOid": HEAD, "branchRefOid": HEAD, "pullRefOid": HEAD,
        "baseRefName": "main", "baseRefOid": "f25d263a2a7cdb2c8f76c40c346cb10f749a9356",
        "liveMainSha": "bc6251ff4ea5a7e59f2d86e2400c90520601f46e",
        "liveMainTree": "4232b318aeaab4c327443638e5467ca089bbed53",
    }
    for live in (before, after):
        if any(live.get(key) != value for key, value in expected.items()):
            raise SystemExit("REFUSED: live PR/base/main refs changed")
    if any(before.get(key) != after.get(key) for key in set(before) | set(after) if key != "attestedUtc"):
        raise SystemExit("REFUSED: PR/base/main refs changed during primary review")
    if git(repo, "rev-parse", "HEAD") != HEAD or git(repo, "rev-parse", "HEAD^{tree}") != TREE:
        raise SystemExit("REFUSED: source worktree moved from pinned head/tree")
    if git(repo, "status", "--porcelain=v1"):
        raise SystemExit("REFUSED: source worktree is not clean")
    remote_text = subprocess.check_output([
        "git", "ls-remote", "https://github.com/snapetech-org/slskdN.git",
        f"refs/heads/{BRANCH}", "refs/pull/409/head"
    ], text=True)
    remote = {line.split()[1]: line.split()[0] for line in remote_text.splitlines() if line.strip()}
    if remote.get(f"refs/heads/{BRANCH}") != HEAD or remote.get("refs/pull/409/head") != HEAD:
        raise SystemExit("REFUSED: current remote PR refs differ from pinned head")

    summary = readj("summary.json")
    files = []
    for path in sorted(item for item in ROOT.iterdir() if item.is_file() and item.name not in {"manifest.json", "SHA256SUMS.txt"}):
        data = path.read_bytes()
        files.append({"path": path.name, "bytes": len(data), "sha256": sha(data)})
    manifest = {
        "artifact": "slskdN PR #409 W77 independent primary semantic review",
        "schemaVersion": 1, "repository": "snapetech-org/slskdN", "pullRequest": 409,
        "window": "W77", "branch": BRANCH, "candidateFree": True,
        "head": HEAD, "tree": TREE, "sourceCount": 25, "localeCount": 12, "cellCount": 300,
        "locales": ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"],
        "candidateFreeInputManifestSha256": sha((INPUT / "manifest.json").read_bytes()),
        "candidateFreeInputChecksumListSha256": sha((INPUT / "PACKET-SHA256SUMS.txt").read_bytes()),
        "sourceInventorySelectionSha256": sha((INPUT / "source-inventory-selection.jsonl").read_bytes()),
        "callerContextSha256": sha((INPUT / "caller-contexts.jsonl").read_bytes()),
        "baseApiSha": expected["baseRefOid"], "liveMainSha": expected["liveMainSha"],
        "dispositions": summary["dispositions"], "proposalCount": summary["proposedTargetCount"],
        "textFreeHoldCount": summary["holds"], "priorHeldCellsCarried": 319,
        "priorHoldResolutionHistoryRows": 13, "blindReviewUsed": False, "crossReviewUsed": False,
        "nativeSpeakerSignoff": False, "browserReview": False, "sourceRewriteRecommendations": 0,
        "worktreeHead": git(repo, "rev-parse", "HEAD"), "worktreeTree": git(repo, "rev-parse", "HEAD^{tree}"),
        "worktreeClean": True, "liveBefore": before, "liveAfter": after,
        "mainDriftSha256": sha((ROOT / "main-drift.json").read_bytes()),
        "files": files,
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    names = sorted([item["path"] for item in files] + ["manifest.json"])
    (ROOT / "SHA256SUMS.txt").write_text("".join(f"{sha((ROOT / name).read_bytes())}  {name}\n" for name in names), encoding="utf-8")
    print(json.dumps({
        "result": "SEALED-PRIMARY", "head": HEAD, "tree": TREE,
        "dispositions": summary["dispositions"], "proposalCount": summary["proposedTargetCount"],
        "textFreeHoldCount": summary["holds"], "manifestSha256": sha((ROOT / "manifest.json").read_bytes()),
        "checksumListSha256": sha((ROOT / "SHA256SUMS.txt").read_bytes()), "packetFiles": len(names),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
