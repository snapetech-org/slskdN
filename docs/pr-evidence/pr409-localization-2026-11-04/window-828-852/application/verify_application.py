#!/usr/bin/env python3
"""Verify W78 exact application readback, hash-only holds, and catalog postimages."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import subprocess
from pathlib import Path


PIN = "4120c9637e71466dc98d51a5a342dee199a1e004"
TREE = "063b62f268eb81253d2b9b4c77ad045c2f25a394"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
TEXT_FIELDS = {"source", "sourceText", "currentTarget", "target", "crossTarget", "proposedTarget", "readbackTarget"}


def fail(message: str) -> None:
    raise SystemExit("FAIL: " + message)


def need(ok: bool, message: str) -> None:
    if not ok:
        fail(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text_sha(value: str) -> str:
    return sha(value.encode("utf-8"))


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def canon(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    app, bundle, repo = Path(__file__).resolve().parent, Path(__file__).resolve().parent.parent, args.repo.resolve()
    git = lambda *cmd: subprocess.check_output(["git", "-C", str(repo), *cmd], text=True).strip()
    plan = rows(app / "application-plan.jsonl")
    readback = rows(app / "application-readback-300-cells.jsonl")
    holds = rows(app / "holds-hash-only.jsonl")
    cross = rows(bundle / "cross-review" / "cross-review-decisions.jsonl")
    current = rows(bundle / "candidate-free" / "input" / "source-current-cells.jsonl")
    need(len(plan) == 63 and len(readback) == len(cross) == len(current) == 300 and len(holds) == 12, "cell/plan/hold counts")
    key = lambda row: (row["sourceId"], row["locale"])
    cross_by_key, current_by_key = {key(row): row for row in cross}, {key(row): row for row in current}
    need(len(cross_by_key) == len(current_by_key) == 300, "duplicate cross/input cell")
    plan_by_key, readback_by_key, holds_by_key = {key(row): row for row in plan}, {key(row): row for row in readback}, {key(row): row for row in holds}
    need(len(plan_by_key) == 63 and len(readback_by_key) == 300 and len(holds_by_key) == 12, "duplicate application rows")
    counts = collections.Counter(row["crossDisposition"] for row in cross)
    need(counts == {"propose": 63, "keep": 225, "hold": 12}, "cross disposition counts")
    need(set(plan_by_key) == {key(row) for row in cross if row["crossDisposition"] == "propose"}, "plan coverage")
    need(set(holds_by_key) == {key(row) for row in cross if row["crossDisposition"] == "hold"}, "hold coverage")

    catalogs: dict[str, tuple[dict, bytes]] = {}
    for metadata in load_json(app / "catalog-preimage-and-postimage.json")["catalogs"]:
        path = metadata["path"]
        data_bytes = (repo / path).read_bytes()
        need(sha(data_bytes) == metadata["postimageSha256"], "catalog postimage SHA: " + path)
        need(blob_sha(data_bytes) == metadata["postimageGitBlob"], "catalog postimage blob: " + path)
        parsed = json.loads(data_bytes.decode("utf-8"))
        need(len(parsed) == 6176, "catalog entry count: " + path)
        key_order_sha = sha(canon(list(parsed.keys())))
        need(key_order_sha == metadata["keyOrderSha256"] and metadata["keyOrderUnchanged"] is True,
             "catalog key order: " + path)
        catalogs[path] = (parsed, data_bytes)
    need(len(catalogs) == 12, "catalog postimage count")

    for k, row in cross_by_key.items():
        rb = readback_by_key[k]
        cell = current_by_key[k]
        need(rb["currentTargetSha256"] == row["currentTargetSha256"], "readback preimage hash: " + repr(k))
        need(rb["sourceSha256"] == row["sourceSha256"], "readback source hash: " + repr(k))
        disposition = row["crossDisposition"]
        if disposition == "hold":
            need(not (TEXT_FIELDS & set(rb)) and not (TEXT_FIELDS & set(holds_by_key[k])), "callerless hold contains text")
            need(rb.get("catalogTextIncluded") is False and rb.get("readbackTextIncluded") is False, "hold text inclusion flags")
            need(rb.get("productionCallerCount") == 0 and holds_by_key[k].get("productionCallerCount") == 0, "held cell is not callerless")
            source_cell = current_by_key[k]
            catalog = json.loads((repo / source_cell["catalogPath"]).read_text(encoding="utf-8"))
            actual_sha = text_sha(catalog[source_cell["catalogKey"]])
            need(actual_sha == row["currentTargetSha256"] == rb["expectedTargetSha256"] == rb["readbackTargetSha256"],
                 "hash-only held value readback")
        else:
            path, catalog_key = row["catalogPath"], row["catalogKey"]
            need(path in catalogs and catalog_key in catalogs[path][0], "readback catalog key")
            actual = catalogs[path][0][catalog_key]
            actual_sha = text_sha(actual)
            need(rb.get("readbackTarget") == actual and rb["readbackTargetSha256"] == actual_sha, "catalog value readback")
            need(text_sha(rb["sourceText"]) == row["sourceSha256"], "readback source-text hash")
            if disposition == "propose":
                proposal = plan_by_key[k]
                need(proposal["target"] == row["crossTarget"] == actual, "selected proposal readback")
                need(proposal["targetSha256"] == row["crossTargetSha256"] == actual_sha, "selected proposal hash readback")
                need(proposal["currentTargetSha256"] == row["currentTargetSha256"], "proposal current-value guard")
                need(rb["expectedTargetSha256"] == actual_sha, "proposal expected-target readback")
            else:
                need(disposition == "keep" and actual_sha == row["currentTargetSha256"], "no-op value readback")
                need(rb["expectedTargetSha256"] == row["currentTargetSha256"], "no-op expected hash")

    app_summary = load_json(app / "application-summary.json")
    need(app_summary["productChangeCount"] == 63 and app_summary["retainedCurrentCount"] == 225 and
         app_summary["callerlessHashOnlyHoldCount"] == 12 and app_summary["readbackCellCount"] == 300 and
         app_summary["catalogKeyOrderUnchanged"] is True, "application summary")
    product = load_json(app / "product-commit.json")
    need(product["parent"] == PIN and product["expectedParent"] == PIN and product["changedValueCount"] == 63,
         "product commit parent/count")
    product_paths = subprocess.check_output(["git", "-C", str(repo), "diff-tree", "--no-commit-id", "--name-only", "-r", product["commit"]], text=True).splitlines()
    need(product_paths == product["changedPaths"] and len(product_paths) == 12 and
         all(path.startswith("src/web/public/locales/") and path.endswith(".json") for path in product_paths),
         "product commit path scope")
    need(not git("status", "--porcelain=v1"), "worktree must be clean")
    print(json.dumps({"result": "PASS", "productCommit": product["commit"], "selected": 63,
                      "retained": 225, "hashOnlyHolds": 12, "readbackCells": 300,
                      "catalogs": len(catalogs), "keyOrder": "unchanged"}, sort_keys=True))


if __name__ == "__main__":
    main()
