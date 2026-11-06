#!/usr/bin/env python3
"""Verify the sealed slskdN PR #409 W74 review and application bundle."""

from __future__ import annotations

import collections
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HEAD = "70e5beffd5cd8d68b8aedffa5c85d16e2cc19b3f"
TREE = "14620c63bee971428fa1cd6cf1f4e944b86056a7"
LOCALES = ("ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_text(value: str) -> str:
    return sha_bytes(value.encode("utf-8"))


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def require(ok: bool, message: str) -> None:
    if not ok:
        raise SystemExit("FAIL: " + message)


def verify_manifest(folder: Path, manifest_name: str) -> int:
    manifest = folder / manifest_name
    entries = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        require(rel not in entries, f"duplicate path in {manifest_name}: {rel}")
        path = (folder / rel).resolve()
        require(path.is_relative_to(folder.resolve()), f"manifest path escapes folder: {rel}")
        require(path.is_file() and sha_bytes(path.read_bytes()) == digest, f"checksum mismatch: {rel}")
        entries[rel] = digest
    actual = {
        p.relative_to(folder).as_posix()
        for p in folder.rglob("*")
        if p.is_file() and p.resolve() != manifest.resolve()
    }
    require(set(entries) == actual, f"manifest inventory mismatch in {folder}")
    return len(entries)


def run_json_verifier(script: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=script.parent,
        check=True,
        text=True,
        capture_output=True,
    )
    try:
        value = json.loads(result.stdout.strip().splitlines()[-1])
    except Exception as exc:
        raise SystemExit(f"Verifier did not return JSON: {script}: {exc}\n{result.stdout}\n{result.stderr}")
    require(value.get("result") == "PASS", f"verifier failed: {script}")
    return value


def verify_application() -> dict:
    cross = ROOT / "cross-review"
    app = ROOT / "application"
    blind_output = ROOT / "blind-review/output"

    cross_result = run_json_verifier(cross / "verify_cross.py")
    blind_result = run_json_verifier(blind_output / "verify_blind_review.py")

    summary = read_json(cross / "cross-summary.json")
    primary_result = {"result": summary["primaryVerifier"], "validatedBy": "portable cross verifier"}
    require(summary["head"] == HEAD and summary["tree"] == TREE, "cross review pin mismatch")
    require(summary["counts"] == {"accept-current": 206, "hold-text-free": 0, "select-update": 94}, "cross counts mismatch")
    ledger = read_jsonl(cross / "cross-review-ledger.jsonl")
    updates = read_jsonl(cross / "selected-updates.jsonl")
    rewrites = read_json(cross / "source-rewrites.json")
    require(len(ledger) == 300 and len(updates) == 94 and len(rewrites) == 2, "cross packet row counts")

    plan = read_json(app / "application-plan.json")
    app_summary = read_json(app / "application-summary.json")
    commit = read_json(app / "application-commit.json")
    delivery = read_json(ROOT / "delivery/PR-attestation-after-catalog.json")
    require(plan["reviewHead"] == HEAD and plan["reviewTree"] == TREE, "application plan pin mismatch")
    require(plan["catalogSelectedUpdateCount"] == 94 and plan["acceptCurrentCount"] == 206 and plan["holdCount"] == 0, "application plan counts")
    require(len(plan["sourceRewrites"]) == 2 and plan["sourceRewriteTranslationCellCount"] == 24, "source rewrite plan counts")
    require(commit["parent"] == HEAD and commit["pathsChanged"] == 14 and commit["workflowPathsChanged"] == 0, "application commit metadata")
    require(delivery["state"] == "OPEN" and delivery["draft"] is True and delivery["head"] == commit["commit"], "post-application PR attestation")

    pre_dir = app / "preimage/locales"
    post_dir = app / "postimage/locales"
    require({p.stem for p in pre_dir.glob("*.json")} == set(LOCALES), "preimage locale set")
    require({p.stem for p in post_dir.glob("*.json")} == set(LOCALES), "postimage locale set")

    updates_by_cell = {(r["continuationRank"], r["locale"]): r for r in updates}
    require(len(updates_by_cell) == 94, "duplicate selected update")
    ledger_by_cell = {(r["continuationRank"], r["locale"]): r for r in ledger}
    require(len(ledger_by_cell) == 300, "duplicate cross cell")
    source_rewrite_map = {r["currentSource"]: r["proposedSource"] for r in rewrites}
    require(len(source_rewrite_map) == 2, "source rewrite key uniqueness")

    for locale in LOCALES:
        before = read_json(pre_dir / f"{locale}.json")
        after = read_json(post_dir / f"{locale}.json")
        expected = {}
        for key, value in before.items():
            require(key not in expected, f"duplicate preimage key in {locale}: {key}")
            expected[source_rewrite_map.get(key, key)] = value
        for row in updates:
            if row["locale"] != locale:
                continue
            key = row["selectedSource"]
            require(key in expected, f"selected source key absent in {locale}: {key}")
            require(expected[key] == row["currentTarget"], f"preimage target mismatch in {locale}: {key}")
            require(sha_text(expected[key]) == row["currentTargetSha256"], f"preimage hash mismatch in {locale}: {key}")
            expected[key] = row["selectedTarget"]
        require(list(after) == list(expected), f"catalog key order changed in {locale}")
        require(after == expected, f"unselected catalog value changed in {locale}")

    source_changes = {
        "src/web/src/components/System/Security/AdversarialSettings.jsx": (
            "Save the current adversarial settings to this server.",
            "Save the current privacy and anonymity settings to this server.",
            2,
        ),
        "src/web/src/components/System/Shares/ContentsModal.jsx": (
            "Close the share contents window.",
            "Close the window showing the contents of the selected share.",
            3,
        ),
    }
    for rel, (old, new, count) in source_changes.items():
        before = (app / "source-code/preimage" / rel).read_text(encoding="utf-8")
        after = (app / "source-code/postimage" / rel).read_text(encoding="utf-8")
        require(before.count(old) == count, f"source preimage occurrence count: {rel}")
        require(before.replace(old, new) == after, f"unexpected source code change: {rel}")

    readback = read_jsonl(app / "application-readback.jsonl")
    require(len(readback) == 300, "application readback must cover 300 cells")
    require(len({(r["continuationRank"], r["locale"]) for r in readback}) == 300, "duplicate application readback cell")
    for row in readback:
        cross_row = ledger_by_cell[(row["continuationRank"], row["locale"])]
        for field in ("source", "selectedSource", "locale", "disposition", "selectedTargetSha256"):
            expected_field = "source" if field == "source" else field
            require(row[expected_field] == cross_row[expected_field], f"readback linkage mismatch: {row['continuationRank']}/{row['locale']} {field}")
        require(row["readback"] == "PASS", "readback status")
        require(sha_text(row["selectedTarget"]) == row["selectedTargetSha256"], "readback target hash")
    counts = collections.Counter(r["disposition"] for r in readback)
    require(counts == {"accept-current": 206, "select-update": 94}, f"readback counts: {counts}")
    require(app_summary["allTargetReadbacks"] == "PASS" and app_summary["cellCount"] == 300, "application summary")

    app_manifest_count = 0
    if (app / "SHA256SUMS.txt").exists():
        app_manifest_count = verify_manifest(app, "SHA256SUMS.txt")
    root_manifest_count = 0
    if (ROOT / "SHA256SUMS.txt").exists():
        root_manifest_count = verify_manifest(ROOT, "SHA256SUMS.txt")

    return {
        "result": "PASS",
        "head": HEAD,
        "tree": TREE,
        "cells": len(readback),
        "counts": dict(counts),
        "sourceRewrites": len(rewrites),
        "sourceRewriteLocaleTargets": 24,
        "catalogLocales": len(LOCALES),
        "nestedVerifiers": {
            "cross": cross_result["result"],
            "primary": primary_result["result"],
            "blind": blind_result["result"],
        },
        "applicationChecksumEntries": app_manifest_count,
        "bundleChecksumEntries": root_manifest_count,
    }


if __name__ == "__main__":
    print(json.dumps(verify_application(), sort_keys=True))
