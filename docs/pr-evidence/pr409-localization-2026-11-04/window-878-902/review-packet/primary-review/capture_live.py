#!/usr/bin/env python3
"""Capture filtered live PR/branch/ref/main state for W80; never materialize PR body."""
import datetime
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = "snapetech-org/slskdN"
PR = 409
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
HEAD = "7a1ca27fd0519674c3b42a3e3df3638b0f671567"
TREE = "b3525218d0f9676c88c4991e78775d113f18b7d9"
BASE = "f25d263a2a7cdb2c8f76c40c346cb10f749a9356"


def api(path, jq):
    return json.loads(subprocess.check_output(["gh", "api", path, "--jq", jq], text=True))


def run(args):
    return subprocess.check_output(args, text=True).strip()


def capture():
    pr = api(f"repos/{REPO}/pulls/{PR}", "{state:.state,draft:.draft,merged:(.merged_at != null),headRefName:.head.ref,headRefOid:.head.sha,baseRefName:.base.ref,baseRefOid:.base.sha,updatedAt:.updated_at}")
    branch = api(f"repos/{REPO}/git/ref/heads/{BRANCH}", "{ref:.ref,oid:.object.sha}")
    commit = api(f"repos/{REPO}/commits/{HEAD}", "{sha:.sha,tree:.commit.tree.sha}")
    main = api(f"repos/{REPO}/commits/main", "{sha:.sha}")
    compare = api(f"repos/{REPO}/compare/{BASE}...{main['sha']}", "{status:.status,ahead_by:.ahead_by,behind_by:.behind_by,total_commits:.total_commits,commits:[.commits[].sha],files:[.files[].filename]}")
    remote_raw = run(["git", "ls-remote", f"https://github.com/{REPO}.git", f"refs/heads/{BRANCH}", f"refs/pull/{PR}/head", f"refs/pull/{PR}/merge"])
    remote = {line.split("\t", 1)[1]: line.split("\t", 1)[0] for line in remote_raw.splitlines() if "\t" in line}
    if (pr["state"], pr["draft"], pr["merged"], pr["headRefName"], pr["headRefOid"], pr["baseRefName"], pr["baseRefOid"]) != ("open", True, False, BRANCH, HEAD, "main", BASE):
        raise SystemExit("REFUSED: live PR state/head/base differs from W80 pin")
    if branch.get("oid") != HEAD or commit != {"sha": HEAD, "tree": TREE}:
        raise SystemExit("REFUSED: live branch or commit/tree differs from W80 pin")
    if remote.get(f"refs/heads/{BRANCH}") != HEAD or remote.get(f"refs/pull/{PR}/head") != HEAD:
        raise SystemExit("REFUSED: live branch/pull refs differ from W80 pin")
    paths = sorted(compare.get("files", []))
    localization_changes = any(path.startswith("src/web/public/locales/") or path.endswith("source-inventory.jsonl") for path in paths)
    checked = datetime.datetime.now(datetime.timezone.utc).isoformat()
    snapshot = {
        "repository": REPO, "pullRequest": PR, "state": pr["state"].upper(), "draft": pr["draft"], "merged": pr["merged"],
        "headRefName": pr["headRefName"], "headRefOid": pr["headRefOid"], "branchRefOid": remote[f"refs/heads/{BRANCH}"],
        "pullRefOid": remote[f"refs/pull/{PR}/head"], "pullMergeRefOid": remote.get(f"refs/pull/{PR}/merge"),
        "baseRefName": pr["baseRefName"], "baseRefOid": pr["baseRefOid"], "liveMainRefName": "main",
        "liveMainSha": main["sha"], "commitTree": commit["tree"], "apiCheckedAtUtc": checked,
        "prBodyQueried": False
    }
    drift = {
        "baseApiSha": BASE, "liveMainSha": main["sha"], "compareStatus": compare["status"],
        "aheadBy": compare["ahead_by"], "behindBy": compare["behind_by"], "totalCommits": compare["total_commits"],
        "commits": compare["commits"], "changedPaths": paths, "localizationOrCatalogChanges": localization_changes,
        "comparisonCheckedAtUtc": checked
    }
    return snapshot, drift


def main():
    phase = sys.argv[1]
    if phase not in {"before", "after"}:
        raise SystemExit("usage: capture_live.py before|after")
    snapshot, drift = capture()
    if phase == "before":
        (ROOT / "live-before.json").write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
        (ROOT / "main-drift-before.json").write_text(json.dumps(drift, indent=2) + "\n", encoding="utf-8")
    else:
        before = json.loads((ROOT / "live-before.json").read_text(encoding="utf-8"))
        drift_before = json.loads((ROOT / "main-drift-before.json").read_text(encoding="utf-8"))
        stable = ("repository", "pullRequest", "state", "draft", "merged", "headRefName", "headRefOid", "branchRefOid", "pullRefOid", "baseRefName", "baseRefOid", "liveMainSha", "commitTree")
        if any(before.get(field) != snapshot.get(field) for field in stable):
            raise SystemExit("REFUSED: live PR refs/base/main changed during W80 extraction")
        if (drift_before["baseApiSha"], drift_before["liveMainSha"], drift_before["changedPaths"]) != (drift["baseApiSha"], drift["liveMainSha"], drift["changedPaths"]):
            raise SystemExit("REFUSED: main compare changed during W80 extraction")
        drift.update({"liveMainBeforeSha": drift_before["liveMainSha"], "liveMainAfterSha": drift["liveMainSha"]})
        (ROOT / "live-after.json").write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
        (ROOT / "main-drift.json").write_text(json.dumps(drift, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"phase": phase, "head": snapshot["headRefOid"], "tree": snapshot["commitTree"], "liveMain": snapshot["liveMainSha"], "mainLocalizationChanges": drift["localizationOrCatalogChanges"], "prBodyQueried": False}, indent=2))


if __name__ == "__main__":
    main()
