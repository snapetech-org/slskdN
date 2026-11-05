#!/usr/bin/env python3
"""Verify the sealed rank-910 catalog/source application and live PR readback."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


APP = Path(__file__).resolve().parent
PACKET = APP.parent
REVIEW = PACKET.parent / "window-903-927" / "rank-910-richtext-review"
SOURCE = (
    "In {mode} mode, each signature must follow the {signature} format and be "
    "verifiable against the canonical join/leave payload using the supplied public key."
)
OLD_KEYS = (
    "In Enforce mode, signatures must use the",
    "format over the canonical join/leave payload and the supplied public key.",
)
PRODUCT_PATHS = {
    "src/web/src/components/System/MediaCore/MediaCorePods.jsx",
    *(
        f"src/web/public/locales/{locale}.json"
        for locale in ("ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant")
    ),
}


def need(condition, message):
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    repo = Path(parser.parse_args().repo).resolve()
    product = read_json(APP / "product-commit.json")
    commit = product["commit"]
    parent = product["parent"]
    need(git(repo, "merge-base", "--is-ancestor", commit, "HEAD") is not None, "product ancestry")
    need(git(repo, "rev-parse", f"{commit}^{{tree}}").decode().strip() == product["tree"], "product tree")
    paths = set(git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", commit).decode().splitlines())
    need(paths == PRODUCT_PATHS, "product paths")
    need(not any(p.startswith(".github/workflows/") for p in paths), "workflow change")

    accepted = [
        json.loads(line)
        for line in (REVIEW / "root-manual-review" / "accepted-translations.jsonl")
        .read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    accepted_by_locale = {row["locale"]: row for row in accepted}
    need(len(accepted) == 12 and len(accepted_by_locale) == 12, "accepted translation count")
    plan = [json.loads(line) for line in (APP / "catalog-product-plan.json").read_text(encoding="utf-8").splitlines() if line.strip()]
    need(len(plan) == 12, "application plan count")
    readback = [json.loads(line) for line in (APP / "catalog-product-readback.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    need(len(readback) == 12, "catalog readback count")

    for row in readback:
        locale, path = row["locale"], row["catalogPath"]
        before = json.loads(git(repo, "show", f"{parent}:{path}").decode("utf-8"))
        after_bytes = git(repo, "show", f"{commit}:{path}")
        after = json.loads(after_bytes.decode("utf-8"))
        expected_keys = list(before)
        expected_keys[expected_keys.index(OLD_KEYS[0])] = SOURCE
        expected_keys.remove(OLD_KEYS[1])
        need(list(after) == expected_keys and len(after) == 6175, f"catalog order/count {locale}")
        accepted_row = accepted_by_locale[locale]
        need(after[SOURCE] == accepted_row["target"], f"catalog target {locale}")
        need(sha(after[SOURCE].encode("utf-8")) == accepted_row["targetSha256"] == row["targetSha256"], f"catalog target hash {locale}")
        need(OLD_KEYS[0] not in after and OLD_KEYS[1] not in after, f"obsolete split keys {locale}")
        need(sha(after_bytes) == row["fileSha256"], f"catalog file hash {locale}")
        need(git(repo, "rev-parse", f"{commit}:{path}").decode().strip() == row["gitBlob"], f"catalog blob {locale}")

    source_row = read_json(APP / "source-product-readback.json")
    source_bytes = git(repo, "show", f"{commit}:{source_row['path']}")
    source_text = source_bytes.decode("utf-8")
    need(SOURCE in source_text and source_text.count(f'source={{"{SOURCE}"}}') == 1, "localized source")
    need('<bdi dir="ltr" lang="en">Enforce</bdi>' in source_text, "mode node")
    need("<code>ed25519:&lt;base64 signature&gt;</code>" in source_text, "signature code node")
    need(sha(source_bytes) == source_row["fileSha256"], "source file hash")
    for pin in product["pins"]:
        pin_bytes = git(repo, "show", f"{commit}:{pin['path']}")
        need(sha(pin_bytes) == pin["productHeadSha256"], f"source/runtime pin {pin['name']}")
        need(git(repo, "rev-parse", f"{commit}:{pin['path']}").decode().strip() == pin["productHeadGitBlob"], f"source/runtime blob {pin['name']}")

    prefix = (APP / "pr-body-prefix-before-w910.txt").read_bytes()
    need(sha(prefix) == read_json(APP / "pr-body-prefix-before-w910.json")["bodySha256"], "saved PR body prefix hash")
    pr = json.loads(subprocess.check_output(["gh", "api", "repos/snapetech-org/slskdN/pulls/409"], text=True))
    branch = pr["head"]["ref"]
    branch_ref = json.loads(subprocess.check_output(["gh", "api", f"repos/snapetech-org/slskdN/git/ref/heads/{branch}"], text=True))["object"]["sha"]
    pull_ref = subprocess.check_output(["git", "-C", str(repo), "ls-remote", "origin", "refs/pull/409/head"], text=True).split()[0]
    need(pr["state"] == "open" and pr["draft"] and not pr["merged"], "PR state")
    need(pr["head"]["sha"] == branch_ref == pull_ref, "PR head refs")
    need(pr["body"].encode("utf-8").startswith(prefix), "PR body prefix")
    print(json.dumps({"result": "PASS", "productCommit": commit, "catalogs": 12, "translations": 12, "catalogKeys": 6175, "splitKeysRemoved": 2, "bodyPrefixBytes": len(prefix), "liveHead": pr["head"]["sha"], "prOpenDraft": True}, indent=2))


if __name__ == "__main__":
    main()
