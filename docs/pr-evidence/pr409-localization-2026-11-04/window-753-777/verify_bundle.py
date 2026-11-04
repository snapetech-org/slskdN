#!/usr/bin/env python3
"""Verify slskdN PR #409 W75 review and application evidence."""
from __future__ import annotations
import collections
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
BASE_HEAD = "99d6afbfb8cca4dccc018e72c01950bc304240db"
BASE_TREE = "f21cb5cde009ac35f5531ddc40612821aee6f471"
LOCALES = ("ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant")
EVIDENCE_PREFIX = "docs/pr-evidence/pr409-localization-2026-11-04/window-753-777/"

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha_text(value: str) -> str:
    return sha(value.encode("utf-8"))

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def require(ok: bool, message: str) -> None:
    if not ok:
        raise SystemExit("FAIL: " + message)

def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()

def verify_manifest(folder: Path, name: str) -> int:
    manifest = folder / name
    entries = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        require(rel not in entries, f"duplicate checksum entry: {rel}")
        path = (folder / rel).resolve()
        require(path.is_relative_to(folder.resolve()), f"checksum path escapes directory: {rel}")
        require(path.is_file() and sha(path.read_bytes()) == digest, f"checksum mismatch: {rel}")
        entries[rel] = digest
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and p.resolve() != manifest.resolve()}
    require(set(entries) == actual, f"checksum inventory mismatch in {folder}")
    return len(entries)

def run_json_verifier(script: Path) -> dict:
    result = subprocess.run([sys.executable, str(script)], cwd=script.parent, check=True, text=True, capture_output=True)
    try:
        value = json.loads(result.stdout.strip())
    except Exception:
        try:
            value = json.loads(result.stdout.strip().splitlines()[-1])
        except Exception as exc:
            raise SystemExit(f"Verifier did not return JSON: {script}: {exc}\n{result.stdout}\n{result.stderr}")
    require(value.get("result") == "PASS", f"nested verifier failed: {script}")
    return value


def verify() -> dict:
    cross = ROOT / "cross-review"
    cf = cross / "inputs/candidate-free-input"
    app = ROOT / "application"
    delivery = ROOT / "delivery"
    root_sum_count = verify_manifest(ROOT, "SHA256SUMS.txt")
    app_sum_count = verify_manifest(app, "SHA256SUMS.txt")
    delivery_sum_count = verify_manifest(delivery, "SHA256SUMS.txt")
    cross_result = run_json_verifier(cross / "verify_cross_packet.py")

    product = read_json(app / "product-commit.json")
    require(product["parent"] == BASE_HEAD and product["selectedCatalogCells"] == 49, "product commit parent/count")
    require(git("rev-parse", f"{product['commit']}^{{tree}}") == product["tree"], "product commit/tree mismatch")
    product_paths = git("diff-tree", "--no-commit-id", "--name-only", "-r", product["commit"]).splitlines()
    require(product_paths == product["paths"] and len(product_paths) == 12, "product commit path list")
    require(all(path in {f"src/web/public/locales/{locale}.json" for locale in LOCALES} for path in product_paths), "product commit contains non-catalog path")
    require(product["workflowPathsChanged"] == 0, "workflow path change recorded")

    current_head = git("rev-parse", "HEAD")
    if current_head != product["commit"]:
        require(git("rev-parse", "HEAD^") == product["commit"], "evidence commit must directly follow product commit")
        evidence_paths = git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()
        require(bool(evidence_paths) and all(p.startswith(EVIDENCE_PREFIX) for p in evidence_paths), "evidence commit contains non-evidence path")
        require(not git("status", "--porcelain"), "working tree is not clean after evidence commit")

    ledger = read_jsonl(cross / "cross-ledger.jsonl")
    cells = read_jsonl(cf / "source-current-cells.jsonl")
    plan = read_jsonl(app / "application-plan.jsonl")
    readback = read_jsonl(app / "application-readback.jsonl")
    hold_readback = read_jsonl(app / "holds-hash-only.jsonl")
    require(len(ledger) == len(cells) == len(readback) == 300, "300-cell inventory")
    require(len(plan) == 49 and len(hold_readback) == 12, "selected/hold inventory")
    cell_by_key = {(r["locale"], r["sourceId"], r["continuationRank"]): r for r in cells}
    ledger_by_key = {(r["locale"], r["sourceId"], r["continuationRank"]): r for r in ledger}
    plan_by_cell = {(r["continuationRank"], r["locale"]): r for r in plan}
    readback_by_cell = {(r["continuationRank"], r["locale"]): r for r in readback}
    require(len(cell_by_key) == len(ledger_by_key) == 300, "duplicate candidate-free/cross cell")
    require(len(plan_by_cell) == 49 and len(readback_by_cell) == 300, "duplicate plan/readback cell")

    selected_counts = collections.Counter()
    decision_counts = collections.Counter()
    held_cells = set()
    for row in ledger:
        lk = (row["locale"], row["sourceId"], row["continuationRank"])
        cell = cell_by_key[lk]
        rb = readback_by_cell[(row["continuationRank"], row["locale"])]
        require((rb["decision"], rb["sourceIdSha256"], rb["sourceSha256"], rb["callerContextSha256"]) ==
                (row["decision"], row["sourceIdSha256"], row["sourceSha256"], row["callerContextSha256"]), "readback linkage mismatch")
        require(rb["catalogPath"] == cell["catalogPath"], "readback catalog path mismatch")
        require(rb["catalogKeySha256"] == sha_text(cell["catalogKey"]), "readback catalog key hash mismatch")
        catalog_path = REPO / cell["catalogPath"]
        post_bytes = catalog_path.read_bytes()
        post_obj = json.loads(post_bytes.decode("utf-8"))
        require(cell["catalogKey"] in post_obj, "catalog key missing")
        actual = post_obj[cell["catalogKey"]]
        actual_hash = sha_text(actual)
        require(rb["readback"] == "PASS" and rb["readbackTargetSha256"] == actual_hash, "exact target hash readback")
        require(rb["catalogPostimageSha256"] == sha(post_bytes), "catalog postimage hash mismatch")
        require(rb["catalogPostimageGitBlob"] == git("hash-object", str(catalog_path)), "catalog postimage Git blob mismatch")
        decision_counts[row["decision"]] += 1
        if row["hold"]:
            held_cells.add((row["continuationRank"], row["locale"]))
            require(row["decision"] == "hold-hash-only", "unexpected hold disposition")
            require(row["currentTarget"] is None and row["selectedTarget"] is None and row["sourceText"] is None, "cross hold exposes target/source text")
            require(rb.get("targetTextOmitted") is True and not any(k in rb for k in ("target", "currentTarget", "selectedTarget")), "application hold is not hash-only")
            require(actual_hash == row["currentTargetSha256"] == cell["currentTargetSha256"], "held current target hash changed")
            require(rb["expectedCurrentTargetSha256"] == row["currentTargetSha256"], "held expected hash mismatch")
            continue
        if row["decision"].startswith("select-"):
            selected_counts[row["locale"]] += 1
            p = plan_by_cell[(row["continuationRank"], row["locale"])]
            require(p["decision"] == row["decision"] and p["selectedProposalSources"] == row["selectedProposalSources"], "selected proposal linkage mismatch")
            require(p["sourceId"] == row["sourceId"] and p["source"] == row["sourceText"], "selected source linkage mismatch")
            require(p["catalogPath"] == cell["catalogPath"] and p["catalogKey"] == cell["catalogKey"], "selected catalog linkage mismatch")
            require(p["currentTarget"] == cell["currentTarget"] and p["currentTargetSha256"] == row["currentTargetSha256"], "selected preimage linkage mismatch")
            require(p["selectedTarget"] == row["selectedTarget"] and p["selectedTargetSha256"] == row["selectedTargetSha256"], "selected target linkage mismatch")
            require(actual == row["selectedTarget"] == rb["target"], "selected target exact readback")
            require(actual_hash == row["selectedTargetSha256"] == rb["selectedTargetSha256"], "selected target hash readback")
        else:
            require(row["decision"] == "keep-current", "unknown non-hold disposition")
            require(actual == cell["currentTarget"] == rb["target"], "kept current value changed")
            require(actual_hash == row["currentTargetSha256"] == rb["expectedTargetSha256"], "kept current hash mismatch")

    require(sum(decision_counts[k] for k in decision_counts if k.startswith("select-")) == 49, "selected decision count")
    require(decision_counts["keep-current"] == 239 and decision_counts["hold-hash-only"] == 12, "cell decision counts")
    require(len(held_cells) == len(hold_readback) == 12, "hold readback count")
    require({(r["continuationRank"], r["locale"]) for r in hold_readback} == held_cells, "hash-only hold linkage")

    updates_by_path = collections.defaultdict(list)
    for row in plan:
        updates_by_path[row["catalogPath"]].append(row)
    require(set(updates_by_path) == {f"src/web/public/locales/{loc}.json" for loc in LOCALES}, "locale catalog coverage")
    for rel, updates in updates_by_path.items():
        pre_bytes = subprocess.check_output(["git", "show", f"{BASE_HEAD}:{rel}"], cwd=REPO)
        pre_obj = json.loads(pre_bytes.decode("utf-8"))
        post_obj = json.loads((REPO / rel).read_text(encoding="utf-8"))
        require(len(pre_obj) == len(post_obj) == 6176 and list(pre_obj) == list(post_obj), f"catalog key sequence changed: {rel}")
        expected = dict(pre_obj)
        for update in updates:
            require(pre_obj.get(update["catalogKey"]) == update["currentTarget"], f"pinned preimage value mismatch: {rel}")
            expected[update["catalogKey"]] = update["selectedTarget"]
        require(post_obj == expected, f"non-target catalog value changed: {rel}")
        pre_sha = sha(pre_bytes)
        pre_blob = subprocess.check_output(["git", "hash-object", "--stdin"], input=pre_bytes, cwd=REPO, text=False).decode().strip()
        locale = Path(rel).stem
        locale_rows = [r for r in cells if r["locale"] == locale]
        require(all(r["catalogFileSha256"] == pre_sha and r["catalogGitBlob"] == pre_blob for r in locale_rows), f"candidate-free catalog preimage mismatch: {rel}")

    for name in ("prior-held-cell-reattestation-hash-only.jsonl", "prior-hold-resolution-history-hash-only.jsonl", "prior-selected-id-exclusions-hash-only.jsonl"):
        require((app / name).read_bytes() == (cf / name).read_bytes(), f"prior hash-only lineage changed: {name}")
    summary = read_json(app / "application-summary.json")
    require(summary["allTargetReadbacks"] == "PASS" and summary["cellCount"] == 300, "application summary")
    require(summary["selectedCatalogUpdateCount"] == 49 and summary["acceptCurrentCount"] == 239 and summary["hashOnlyHoldCount"] == 12, "application summary counts")

    att = read_json(delivery / "PR-attestation-after-product.json")
    require(att["state"] == "OPEN" and att["draft"] is True and att["head"] == product["commit"], "PR product attestation state/head")
    require(att["refsMatch"] is True and att["branchRef"] == att["pullRef"] == product["commit"], "PR product ref attestation")
    body = (delivery / "PR-body-before.md").read_bytes()
    require(sha(body) == att["bodySha256"] and len(body) == att["bodyBytes"] and att["bodyMatchesCapturedPrefix"], "PR body prefix capture")
    verifiers = read_json(ROOT / "verification-results.json")
    require(all(verifiers[k]["result"] == "PASS" for k in ("candidateFree", "primary", "blind", "cross", "applicationPrecommit", "liveAfterProductPush")), "recorded verifier results")

    return {
        "result": "PASS", "reviewHead": BASE_HEAD, "reviewTree": BASE_TREE,
        "productCommit": product["commit"], "productTree": product["tree"], "head": current_head,
        "cells": 300, "selected": 49, "keepCurrent": 239, "hashOnlyHolds": 12,
        "selectedByLocale": dict(sorted(selected_counts.items())),
        "catalogFiles": len(updates_by_path), "catalogEntriesPerLocale": 6176,
        "crossVerifier": cross_result["result"],
        "checksums": {"root": root_sum_count, "application": app_sum_count, "delivery": delivery_sum_count},
        "state": "product committed" if current_head == product["commit"] else "evidence committed"
    }

if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, sort_keys=True))
