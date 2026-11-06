#!/usr/bin/env python3
import argparse
import collections
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "674156749ee86021ef91d896b1824be62cff9a93"
BASE_TREE = "86483dbf9227130cade6a3f4c9dc9ef5cf232450"
PRODUCT_COMMIT = "7bfcab0e1eae810f8af1e1398f0e429c862b42ee"


def fail(message):
    raise SystemExit("FAIL: " + message)


def req(ok, message):
    if not ok:
        fail(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def j(path):
    return json.loads(path.read_text(encoding="utf-8"))


def jl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run(args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def verify_sums(folder, filename):
    sums = folder / filename
    req(sums.is_file(), "missing checksum list " + str(sums))
    listed = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(None, 1)
            listed[name.lstrip("* ")] = digest
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and p != sums}
    req(set(listed) == actual, "checksum inventory " + str(folder))
    for name, digest in listed.items():
        req(sha((folder / name).read_bytes()) == digest, "checksum " + name)


parser = argparse.ArgumentParser()
parser.add_argument("--repo", type=Path, required=True, help="checkout containing the pushed W76 product and evidence commits")
parser.add_argument("--base-checkout", type=Path, help="clean checkout at the pinned W76 base head, for offline cross-packet replay")
args = parser.parse_args()
repo = args.repo.resolve()

verify_sums(ROOT, "SHA256SUMS.txt")
verify_sums(ROOT / "application", "SHA256SUMS.txt")
verify_sums(ROOT / "cross-review", "SHA256SUMS.txt")

product = j(ROOT / "application/product-commit.json")
product_sha = product["sha"]
req(product_sha.startswith(PRODUCT_COMMIT), "product commit prefix")
req(run(["git", "rev-parse", f"{product_sha}^"], cwd=repo) == BASE, "product commit parent")
req(run(["git", "rev-parse", f"{BASE}^{{tree}}"], cwd=repo) == BASE_TREE, "base tree")
product_paths = set(run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", product_sha], cwd=repo).splitlines())
plan = jl(ROOT / "application/application-plan.jsonl")
readback = jl(ROOT / "application/application-readback.jsonl")
prepost = j(ROOT / "application/catalog-preimage-and-postimage.json")
source_cells = jl(ROOT / "cross-review/inputs/candidate-free-input/source-current-cells.jsonl")
ledger = jl(ROOT / "cross-review/cross-ledger.jsonl")
req(len(plan) == 69 and len(readback) == 300 and len(source_cells) == len(ledger) == 300, "application row counts")
req(product_paths == {r["catalogPath"] for r in plan} and len(product_paths) == 12, "product commit file scope")
cell_map = {(x["continuationRank"], x["locale"]): x for x in source_cells}
ledger_map = {(x["continuationRank"], x["locale"]): x for x in ledger}
plan_map = {(x["continuationRank"], x["locale"]): x for x in plan}
read_map = {(x["continuationRank"], x["locale"]): x for x in readback}
req(len(plan_map) == 69 and len(read_map) == 300, "duplicate application rows")
req(set(read_map) == set(cell_map) == set(ledger_map), "readback key coverage")
req(set(plan_map) == {k for k, row in ledger_map.items() if not row["hold"] and row["decision"] != "keep-current"}, "application plan/cross linkage")

pre_map = {x["catalogPath"]: x for x in prepost["catalogs"]}
for path in product_paths:
    before = subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=repo)
    after = subprocess.check_output(["git", "show", f"{product_sha}:{path}"], cwd=repo)
    old = json.loads(before.decode("utf-8"))
    new = json.loads(after.decode("utf-8"))
    pp = pre_map[path]
    req(sha(before) == pp["preimageSha256"], "catalog preimage hash " + path)
    req(sha(after) == pp["postimageSha256"], "catalog postimage hash " + path)
    req(len(old) == len(new) == 6176 and list(old) == list(new), "catalog key set/order " + path)
    changes = {key for key in old if old[key] != new[key]}
    rows = [x for x in plan if x["catalogPath"] == path]
    req(changes == {x["catalogKey"] for x in rows}, "catalog changed keys " + path)
    for row in rows:
        req(old[row["catalogKey"]] == row["currentTarget"], "catalog old target " + path)
        req(new[row["catalogKey"]] == row["selectedTarget"], "catalog new target " + path)
        req(sha(new[row["catalogKey"]].encode("utf-8")) == row["selectedTargetSha256"], "catalog selected hash " + path)

counts = collections.Counter()
for key, cell in cell_map.items():
    cross = ledger_map[key]
    row = read_map[key]
    actual = json.loads(subprocess.check_output(["git", "show", f"{product_sha}:{cell['catalogPath']}"], cwd=repo))[cell["catalogKey"]]
    req(row["sourceId"] == cell["sourceId"] and row["sourceSha256"] == cell["sourceSha256"], "readback source linkage " + str(key))
    if cross["hold"]:
        counts["hold"] += 1
        req(row["decision"] == "hold-hash-only", "hold readback disposition " + str(key))
        req(actual == cell["currentTarget"] and row["postReadbackSha256"] == sha(actual.encode("utf-8")), "held target unchanged " + str(key))
        req(row["sourceTextIncluded"] is False and row["currentTargetIncluded"] is False and row["selectedTargetIncluded"] is False, "hold text flags " + str(key))
        req(not any(f in row for f in ("source", "sourceText", "currentTarget", "selectedTarget", "catalogKey")), "hold text leak " + str(key))
    elif key in plan_map:
        counts["updated"] += 1
        selected = plan_map[key]["selectedTarget"]
        req(actual == selected == row["selectedTarget"], "selected target readback " + str(key))
        req(row["decision"] == cross["decision"], "selected decision readback " + str(key))
        req(row["postReadbackSha256"] == sha(actual.encode("utf-8")), "selected hash readback " + str(key))
    else:
        counts["keep"] += 1
        req(actual == cell["currentTarget"] == row["selectedTarget"], "current target readback " + str(key))
        req(row["decision"] == "keep-current" and row["postReadbackSha256"] == cell["currentTargetSha256"], "keep readback " + str(key))
req(counts == {"updated": 69, "keep": 183, "hold": 48}, "application readback counts")

summary = j(ROOT / "application/application-summary.json")
req(summary["result"] == "PASS" and summary["cellsReadBack"] == 300 and summary["selectedUpdates"] == 69 and summary["unchangedCells"] == 183 and summary["hashOnlyHolds"] == 48, "application summary")
req(len(jl(ROOT / "application/prior-held-cell-reattestation-hash-only.jsonl")) == 271, "prior holds preserved")
req(len(jl(ROOT / "application/prior-hold-resolution-history-hash-only.jsonl")) == 13, "prior hold resolution history preserved")
req(len(jl(ROOT / "application/prior-selected-id-exclusions-hash-only.jsonl")) == 1857, "prior selected IDs preserved")

if args.base_checkout:
    cross_verifier = ROOT / "cross-review/verify_cross_packet.py"
    output = subprocess.check_output(["python3", str(cross_verifier), "--offline", "--repo", str(args.base_checkout.resolve())], text=True, cwd=ROOT)
    req('"result": "PASS"' in output, "cross-review verifier")

print(json.dumps({"result": "PASS", "productCommit": product_sha, "cells": 300, "selectedUpdates": counts["updated"], "unchanged": counts["keep"], "hashOnlyHolds": counts["hold"], "catalogFiles": len(product_paths), "allChecksums": "PASS", "crossVerifier": "PASS" if args.base_checkout else "not rerun"}, ensure_ascii=False, indent=2))
