#!/usr/bin/env python3
"""Verify the remaining-queue rank alias and exact-head readback evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
INPUT = HERE / "candidate-free" / "input"
REVIEW_REL = Path("docs/pr-evidence/pr409-localization-2026-11-05/w953-977")
PINNED_HEAD = "cc600880606f374cebe3082789fa50f246ff614f"
PINNED_TREE = "440b9842d914a391f77cbb03737261b8798cc6e3"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    rows = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if raw.strip():
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc
    return rows


def cell_map(rows, source_hash_field):
    result = {}
    for row in rows:
        key = cell_key(row)
        if key in result:
            raise ValueError(f"duplicate cell {key}")
        result[key] = (
            row[source_hash_field],
            row["callerContextSha256"],
        )
    return result


def cell_key(row):
    identity_hash = row.get("sourceIdSha256")
    if not identity_hash:
        identity_hash = hashlib.sha256(row["sourceId"].encode("utf-8")).hexdigest()
    return ("sha256:" + identity_hash, row["locale"])


def run_json(command, cwd: Path):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}")
    decoder = json.JSONDecoder()
    values = []
    offset = 0
    while offset < len(proc.stdout):
        while offset < len(proc.stdout) and proc.stdout[offset].isspace():
            offset += 1
        if offset == len(proc.stdout):
            break
        value, offset = decoder.raw_decode(proc.stdout, offset)
        values.append(value)
    return values


def git(path: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path, help="PR checkout containing W953 evidence")
    parser.add_argument("--exact-checkout", required=True, type=Path, help="clean detached checkout at cc600880…")
    args = parser.parse_args()
    repo = args.repo.resolve()
    exact = args.exact_checkout.resolve()

    manifest = read_json(INPUT / "summary.json")
    boundary = read_json(INPUT / "selection-and-boundary.json")
    reattestation = read_json(INPUT / "window-application-reattestation.json")
    stored_readback = read_json(HERE / "exact-worktree-readback.json")
    prior = repo / REVIEW_REL

    if manifest["exactHead"] != PINNED_HEAD or manifest["exactTree"] != PINNED_TREE:
        raise ValueError("candidate-free packet exact head/tree do not match this bundle")
    if boundary["recordedRemainingQueueRange"] != [853, 877]:
        raise ValueError("remaining-queue rank range mismatch")
    if boundary["recordedContinuationRange"] != [953, 977]:
        raise ValueError("continuation rank range mismatch")

    selection = read_jsonl(INPUT / "selected-sources.jsonl")
    if len(selection) != 25 or len({row["sourceId"] for row in selection}) != 25:
        raise ValueError("expected 25 unique selected source IDs")
    if any(row["continuationRank"] != row["remainingQueueRank"] + 100 for row in selection):
        raise ValueError("rank alias is not a constant +100 mapping")

    current_rows = read_jsonl(INPUT / "source-current-cells.jsonl")
    primary_rows = read_jsonl(prior / "primary-review" / "primary-review.jsonl")
    cross_rows = read_jsonl(prior / "cross-review" / "cross-review-ledger.jsonl")
    root_rows = read_jsonl(prior / "root-application" / "root-review-ledger.jsonl")
    readback_rows = read_jsonl(prior / "root-application" / "final-head-readback.jsonl")
    expected_keys = {cell_key(row) for row in current_rows}
    if len(expected_keys) != 300:
        raise ValueError("candidate-free cell matrix does not contain 300 unique rows")

    prior_maps = [
        ("primary", cell_map(primary_rows, "sourceSha256")),
        ("cross", cell_map(cross_rows, "sourceTextSha256")),
        ("root", cell_map(root_rows, "sourceSha256")),
    ]
    current_source_map = cell_map(current_rows, "sourceSha256")
    if set(current_source_map) != expected_keys:
        raise ValueError("candidate-free source map mismatch")
    for label, mapping in prior_maps:
        if set(mapping) != expected_keys:
            raise ValueError(f"{label} review does not cover the same 300 cells")
        for key in expected_keys:
            if mapping[key] != current_source_map[key]:
                raise ValueError(f"{label} source/caller pins changed for {key}")

    readback_map = {}
    for row in readback_rows:
        key = cell_key(row)
        if key in readback_map:
            raise ValueError(f"duplicate prior readback cell {key}")
        readback_map[key] = row.get("observedAfterSha256") or row.get("expectedAfterSha256")
    if set(readback_map) != expected_keys:
        raise ValueError("prior root readback does not cover the same 300 cells")
    for row in current_rows:
        key = cell_key(row)
        if row["currentTargetSha256"] != readback_map[key]:
            raise ValueError(f"current target hash differs from root readback for {key}")

    old_root = read_json(prior / "root-application" / "root-review-summary.json")
    current_exact_head = git(exact, "rev-parse", "HEAD")
    current_tree = git(exact, "rev-parse", "HEAD^{tree}")
    exact_status = git(exact, "status", "--porcelain")
    if current_exact_head != PINNED_HEAD or current_tree != PINNED_TREE or exact_status:
        raise ValueError("exact checkout must be clean at the pinned head/tree")

    verifier_runs = run_json(
        [sys.executable, "-B", str(INPUT / "verify_exact_worktree.py"), str(exact)],
        cwd=INPUT,
    )
    if len(verifier_runs) != 2 or any(item.get("result") != "PASS" for item in verifier_runs):
        raise ValueError("portable/exact worktree verifier did not return two PASS results")
    exact_result = verifier_runs[1]
    if (exact_result["head"], exact_result["tree"], exact_result["cells"], exact_result["applied"], exact_result["hashOnlyHolds"]) != (
        PINNED_HEAD,
        PINNED_TREE,
        300,
        288,
        12,
    ):
        raise ValueError("exact verifier results do not match the recorded readback")
    if stored_readback["exactWorktreeVerifier"] != exact_result:
        raise ValueError("stored exact readback does not match a fresh verifier run")
    if not reattestation["allCurrentCatalogTargetsMatchReadback"] or not reattestation["allHoldTextsOmitted"]:
        raise ValueError("current-head application reattestation failed")
    if old_root["rootDispositionCounts"].get("hold-hash-only") != 12:
        raise ValueError("prior rank-966 holds do not match this reattestation")

    output = {
        "result": "PASS",
        "rankAlias": "remainingQueueRank = continuationRank - 100",
        "sourceIds": 25,
        "cells": 300,
        "priorReviewSets": {label: "same source/caller pins" for label, _ in prior_maps},
        "priorRootReadback": "all 300 target hashes match current candidate-free hashes",
        "exactWorktreeVerifier": exact_result,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
