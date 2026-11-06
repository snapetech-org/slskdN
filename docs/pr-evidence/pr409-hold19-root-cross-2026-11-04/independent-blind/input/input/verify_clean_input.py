#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEAD = "03c73e7b6706d8a034d7a24d6984763134f61bac"
TREE = "fa3f2041bbc2d4bb4eb512c03e874db3dbf631a5"
IDS = {"src_1ebad52e6ebb059b", "src_21351b02a51c3a85", "src_227ab7b919019ee9"}
RANKS = {"src_1ebad52e6ebb059b": 409, "src_21351b02a51c3a85": 475, "src_227ab7b919019ee9": 504}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def j(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))

def jl(name):
    return [json.loads(line) for line in (ROOT / name).read_text(encoding="utf-8").splitlines() if line.strip()]

def main():
    sums = {}
    for line in (ROOT / "PACKET-SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        sums[name] = digest
    actual = {path.name for path in ROOT.iterdir() if path.is_file() and path.name != "PACKET-SHA256SUMS.txt"}
    assert actual == set(sums) and all(sha((ROOT / name).read_bytes()) == digest for name, digest in sums.items())
    manifest = j("manifest.json")
    assert manifest["candidateFree"] is True and manifest["head"] == HEAD and manifest["tree"] == TREE
    assert manifest["historicalDispositionsIncluded"] is False and manifest["cellCount"] == 19
    files = {row["path"]: row for row in manifest["files"]}
    assert set(files) == actual - {"manifest.json"}
    for name, row in files.items():
        raw = (ROOT / name).read_bytes()
        assert len(raw) == row["bytes"] and sha(raw) == row["sha256"]
    cells = jl("source-current-cells.jsonl")
    assert len(cells) == 19 and {row["sourceId"] for row in cells} == IDS
    assert all(row["containsCandidate"] is False and row["verdict"] is None and "proposedTarget" not in row for row in cells)
    assert not any((ROOT / name).exists() for name in ("historical-prior-hold-rows-hash-only.jsonl", "prior-hold-context-reconciliation-hash-only.jsonl", "prior-held-cell-reattestation-hash-only.jsonl", "prior-selected-id-exclusions-hash-only.jsonl"))
    callers = {row["sourceId"]: row for row in jl("caller-contexts.jsonl")}
    assert set(callers) == IDS
    assert all(row["productionCallerCount"] > 0 for row in callers.values())
    for cell in cells:
        assert cell["sourceId"] == "src_" + cell["sourceSha256"][:16] and sha(cell["source"].encode("utf-8")) == cell["sourceSha256"]
        assert cell["continuationRank"] == RANKS[cell["sourceId"]]
        assert sha(cell["currentTarget"].encode("utf-8")) == cell["currentTargetSha256"]
        caller = callers[cell["sourceId"]]
        assert caller["sourceSha256"] == cell["sourceSha256"] and cell["callerContextSha256"]
        ref_keys = ("path", "line", "lineSha256", "contextSha256", "fileSha256", "gitBlob")
        assert cell["callerRefs"] == [{key: ref[key] for key in ref_keys} for ref in caller["callers"]]
    assert not any("priorDisposition" in row or "priorHold" in row for row in cells)
    print(json.dumps({"verifier": "PASS", "cells": 19, "sourceIds": 3, "historicalDispositionsIncluded": False, "head": HEAD, "tree": TREE}, indent=2))

if __name__ == "__main__":
    main()
