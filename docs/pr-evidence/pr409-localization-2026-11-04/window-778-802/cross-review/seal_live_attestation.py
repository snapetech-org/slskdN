#!/usr/bin/env python3
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = "snapetech-org/slskdN"
PR = 409
HEAD = "674156749ee86021ef91d896b1824be62cff9a93"
TREE = "86483dbf9227130cade6a3f4c9dc9ef5cf232450"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
WORKTREE = Path("/mnt/disks/scratch/task-worktrees/localization-20261104/slskdn-pr409-w76-pristine-check")


def run(args):
    return subprocess.check_output(args, text=True).strip()


def api_json(path):
    return json.loads(run(["gh", "api", path]))


def snapshot():
    pull = api_json(f"repos/{REPO}/pulls/{PR}")
    branch = pull["head"]["ref"]
    base = pull["base"]["ref"]
    branch_ref = run(["git", "ls-remote", f"https://github.com/{REPO}.git", f"refs/heads/{branch}"]).split()[0]
    pull_ref = run(["git", "ls-remote", f"https://github.com/{REPO}.git", f"refs/pull/{PR}/head"]).split()[0]
    tree = run(["gh", "api", f"repos/{REPO}/git/commits/{HEAD}", "--jq", ".tree.sha"])
    main_sha = run(["git", "ls-remote", f"https://github.com/{REPO}.git", f"refs/heads/{base}"]).split()[0]
    compare = api_json(f"repos/{REPO}/compare/{pull['base']['sha']}...{main_sha}")
    drift_files = sorted(x["filename"] for x in compare.get("files", []))
    contains_catalog = any("/locales/" in f or "localization" in f.lower() or "catalog" in f.lower() for f in drift_files)
    status = run(["git", "-C", str(WORKTREE), "status", "--porcelain"])
    wt_head = run(["git", "-C", str(WORKTREE), "rev-parse", "HEAD"])
    wt_tree = run(["git", "-C", str(WORKTREE), "rev-parse", "HEAD^{tree}"])
    if status or wt_head != HEAD or wt_tree != TREE:
        raise SystemExit("source worktree is not clean at pinned head/tree")
    snap = {
        "repository": REPO,
        "pullRequest": PR,
        "state": pull["state"],
        "draft": pull["draft"],
        "merged": pull["merged"],
        "mergeableState": pull.get("mergeable_state"),
        "headRef": branch,
        "headShaApi": pull["head"]["sha"],
        "branchRefSha": branch_ref,
        "pullRefSha": pull_ref,
        "headTree": tree,
        "baseRef": base,
        "baseShaApi": pull["base"]["sha"],
        "liveMainSha": main_sha,
        "baseCompareStatus": compare.get("status"),
        "baseCompareAheadBy": compare.get("ahead_by"),
        "baseDriftFiles": drift_files,
        "baseDriftContainsLocalizationOrCatalogPaths": contains_catalog,
        "sourceWorktreeClean": not status,
        "sourceWorktreeHead": wt_head,
        "sourceWorktreeTree": wt_tree,
        "attestedUtc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
    req = snap["state"] == "open" and snap["draft"] is True and snap["merged"] is False
    req = req and branch == BRANCH and pull["base"]["ref"] == "main"
    req = req and pull["head"]["sha"] == branch_ref == pull_ref == HEAD and tree == TREE
    req = req and pull["base"]["sha"] == "f25d263a2a7cdb2c8f76c40c346cb10f749a9356"
    req = req and not contains_catalog
    if not req:
        raise SystemExit("live PR/base re-attestation mismatch: " + json.dumps(snap, ensure_ascii=False))
    return snap


before = json.loads((ROOT / "live-pr-before.json").read_text(encoding="utf-8"))
after = snapshot()
if after["attestedUtc"] < before["attestedUtc"]:
    raise SystemExit("after attestation predates before attestation")
(ROOT / "live-pr-after.json").write_text(json.dumps(after, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
summary_path = ROOT / "summary.json"
summary = json.loads(summary_path.read_text(encoding="utf-8"))
summary["livePRAfter"] = "PASS"
summary["livePRAfterAttestedUtc"] = after["attestedUtc"]
summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

lines = []
for path in sorted(p for p in ROOT.rglob("*") if p.is_file() and p != ROOT / "SHA256SUMS.txt"):
    lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT).as_posix()}")
(ROOT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps(after, ensure_ascii=False, indent=2))
