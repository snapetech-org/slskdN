#!/usr/bin/env python3
"""Capture the GitHub PR API and Git branch/pull refs for PR #409."""
import argparse
import datetime
import json
import subprocess
from pathlib import Path

REPOSITORY = "snapetech-org/slskdN"
PR_NUMBER = 409
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
EXPECTED_HEAD = "4d67527be0ca3b75e866f25bef5e58ae7f777f7f"


def command(args):
    return subprocess.check_output(args, text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    pr = json.loads(command(["gh", "api", f"repos/{REPOSITORY}/pulls/{PR_NUMBER}"]))
    refs = command([
        "git", "-C", str(repo), "ls-remote", "origin",
        f"refs/heads/{BRANCH}", f"refs/pull/{PR_NUMBER}/head",
        f"refs/pull/{PR_NUMBER}/merge", "refs/heads/main"
    ])
    ref_map = {}
    for line in refs.splitlines():
        if line.strip():
            oid, ref = line.split("\t", 1)
            ref_map[ref] = oid
    commit_tree = command([
        "git", "-C", str(repo), "rev-parse", f"{EXPECTED_HEAD}^{{tree}}"
    ])
    value = {
        "repository": REPOSITORY,
        "pullRequest": PR_NUMBER,
        "state": str(pr["state"]).upper(),
        "draft": bool(pr["draft"]),
        "merged": bool(pr["merged"]),
        "headRefName": pr["head"]["ref"],
        "headRefOid": pr["head"]["sha"],
        "headRepository": (pr.get("head", {}).get("repo") or {}).get("full_name"),
        "branchRefOid": ref_map.get(f"refs/heads/{BRANCH}"),
        "pullRefOid": ref_map.get(f"refs/pull/{PR_NUMBER}/head"),
        "pullMergeRefOid": ref_map.get(f"refs/pull/{PR_NUMBER}/merge"),
        "baseRefName": pr["base"]["ref"],
        "baseRefOid": pr["base"]["sha"],
        "liveMainRefName": "main",
        "liveMainSha": ref_map.get("refs/heads/main"),
        "commitTree": commit_tree,
        "apiCheckedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
