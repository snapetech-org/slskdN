#!/usr/bin/env python3
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEAD = "03c73e7b6706d8a034d7a24d6984763134f61bac"
TREE = "fa3f2041bbc2d4bb4eb512c03e874db3dbf631a5"
IDS = {"src_1ebad52e6ebb059b", "src_21351b02a51c3a85", "src_227ab7b919019ee9"}
LOCALES = {"ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"}
EXPECTED = {("src_1ebad52e6ebb059b", locale) for locale in LOCALES} | {("src_21351b02a51c3a85", "ar")} | {("src_227ab7b919019ee9", locale) for locale in ("ar", "de", "es", "fr", "hi", "pt-BR")}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def j(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))

def jl(name):
    return [json.loads(line) for line in (ROOT / name).read_text(encoding="utf-8").splitlines() if line.strip()]

def tokens(text):
    placeholders = sorted(re.findall(r"\{[^{}]+\}", text))
    markup = sorted(re.findall(r"</?[A-Za-z][^>]*>", text))
    numbers = re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])", text)
    protected = set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])", text))
    for literal in ("Wishlist", "Soulseek", "Discogs", "Pod", "Prometheus", "Lidarr", "ReplayGain", "SongID", "WebSocket", "VBR"):
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(literal) + r"(?![A-Za-z0-9])", text):
            protected.add(literal)
    return placeholders, markup, numbers, sorted(protected)

def verify():
    sums = {}
    for line in (ROOT / "PACKET-SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        assert name not in sums
        sums[name] = digest
    actual = {path.name for path in ROOT.iterdir() if path.is_file() and path.name != "PACKET-SHA256SUMS.txt"}
    assert actual == set(sums)
    assert all(sha((ROOT / name).read_bytes()) == digest for name, digest in sums.items())
    manifest = j("manifest.json")
    assert manifest["candidateFree"] is True and manifest["head"] == HEAD and manifest["tree"] == TREE
    assert manifest["sourceCount"] == 3 and manifest["cellCount"] == 19
    assert manifest["proposedTargetsIncluded"] is False and manifest["reviewDecisionsIncluded"] is False
    files = {row["path"]: row for row in manifest["files"]}
    assert set(files) == actual - {"manifest.json"}
    for name, row in files.items():
        raw = (ROOT / name).read_bytes()
        assert len(raw) == row["bytes"] and sha(raw) == row["sha256"]
    inventory = jl("source-inventory-pinned.jsonl")
    assert len(inventory) == 6176 and sha((ROOT / "source-inventory-pinned.jsonl").read_bytes()) == manifest["sourceInventorySha256"]
    by_id = {row["sourceId"]: row for row in inventory}
    assert len(by_id) == 6176
    selected = jl("source-inventory-selection.jsonl")
    assert {row["sourceId"] for row in selected} == IDS and len(selected) == 3
    assert {row["continuationRank"] for row in selected} == {409, 475, 504}
    callers = {row["sourceId"]: row for row in jl("caller-contexts.jsonl")}
    assert set(callers) == IDS
    cells = jl("source-current-cells.jsonl")
    assert len(cells) == 19 and {(row["sourceId"], row["locale"]) for row in cells} == EXPECTED
    catalogs = {row["locale"]: row for row in jl("catalog-structure.jsonl")}
    assert set(catalogs) == LOCALES
    assert all(row["entryCount"] == 6176 and row["nonemptyValueCount"] == 6176 and row["orderedKeySha256"] == "3ca04c40ebfed00b93fcd143109fc9d85da941cec30b6cb93f52e431498df6a7" for row in catalogs.values())
    mismatches = Counter()
    for row in callers.values():
        source = by_id[row["sourceId"]]
        assert row["sourceSha256"] == source["sourceSha256"] and row["source"] == source["source"]
        assert row["productionCallerCount"] == len(row["callers"]) and row["productionCallerCount"] > 0
        for call in row["callers"]:
            assert sha(canon(call["context"])) == call["contextSha256"]
            line = next(item["text"] for item in call["context"] if item["line"] == call["line"])
            assert line == call["lineText"] and sha(line.encode("utf-8")) == call["lineSha256"]
            assert call["fileBytes"] > 0 and call["fileSha256"] and call["gitBlob"]
    for row in cells:
        source_id = row["sourceId"]
        source = by_id[source_id]
        assert row["source"] == source["source"] and row["sourceSha256"] == source["sourceSha256"]
        assert row["continuationRank"] == source["continuationRank"] and row["remainingQueueRank"] == source["remainingQueueRank"]
        assert row["sourceId"] == "src_" + row["sourceSha256"][:16] and sha(row["source"].encode("utf-8")) == row["sourceSha256"]
        assert sha(row["currentTarget"].encode("utf-8")) == row["currentTargetSha256"]
        assert row["catalogKey"] == row["source"]
        assert row["catalogFileSha256"] == catalogs[row["locale"]]["sha256"] and row["catalogGitBlob"] == catalogs[row["locale"]]["gitBlob"]
        caller = callers[source_id]
        assert row["callerContextSha256"] == sha(canon([item["context"] for item in caller["callers"]]))
        ref_keys = ("path", "line", "lineSha256", "contextSha256", "fileSha256", "gitBlob")
        assert row["callerRefs"] == [{key: call[key] for key in ref_keys} for call in caller["callers"]]
        assert row["containsCandidate"] is False and row["verdict"] is None and "proposedTarget" not in row
        source_ph, source_tags, source_nums, source_protected = tokens(row["source"])
        target_ph, target_tags, target_nums, target_protected = tokens(row["currentTarget"])
        assert row["placeholderEvidence"] == {"sourceTokens": source_ph, "currentTokens": target_ph, "matches": source_ph == target_ph}
        assert row["markupEvidence"] == {"sourceTags": source_tags, "currentTags": target_tags, "matches": source_tags == target_tags}
        assert row["sourceNumericTokens"] == source_nums and row["currentNumericTokens"] == target_nums
        assert row["numericTokensPreserved"] is (source_nums == target_nums)
        missing = [term for term in source_protected if term not in row["currentTarget"]]
        assert row["sourceProtectedLiterals"] == source_protected and row["currentProtectedLiterals"] == target_protected
        assert row["missingProtectedLiterals"] == missing
        assert row["protectedLiteralEvidence"] == {"sourceTokens": source_protected, "currentTokens": target_protected, "matches": not bool(missing)}
        mismatches["placeholder"] += not (source_ph == target_ph)
        mismatches["markup"] += not (source_tags == target_tags)
        mismatches["numeric"] += not (source_nums == target_nums)
        mismatches["protectedLiteral"] += bool(missing)
    baseline = j("baseline-token-mismatch-summary.json")
    assert baseline["cellCount"] == 19 and baseline["mismatches"] == dict(mismatches)
    historical = jl("historical-prior-hold-rows-hash-only.jsonl")
    assert len(historical) == 19
    assert {(row["sourceId"], row["locale"]) for row in historical} == EXPECTED
    assert all(row["sourceTextIncluded"] is False and row["targetTextIncluded"] is False and "source" not in row and "currentTarget" not in row for row in historical)
    all_holds = jl("prior-held-cell-reattestation-hash-only.jsonl")
    assert len(all_holds) == 152
    assert all(row["sourceTextIncluded"] is False and row["targetTextIncluded"] is False for row in all_holds)
    prior_ids = jl("prior-selected-id-exclusions-hash-only.jsonl")
    assert len(prior_ids) == 1782
    assert all(row["sourceTextIncluded"] is False and row["targetTextIncluded"] is False and "source" not in row and "target" not in row for row in prior_ids)
    corrections = jl("prior-hold-context-reconciliation-hash-only.jsonl")
    assert len(corrections) == 19
    cell_map = {(row["sourceId"], row["locale"]): row for row in cells}
    for row in corrections:
        cell = cell_map[row["sourceId"], row["locale"]]
        assert row["previousAttestationCallerCount"] == 0 and row["currentCallerCount"] == len(cell["callerRefs"]) > 0
        assert row["previousTargetSha256"] == row["currentTargetSha256"] == cell["currentTargetSha256"]
        assert row["targetHashUnchanged"] is True and row["sourceTextIncluded"] is False and row["targetTextIncluded"] is False
        assert row["callerInventoriesIdenticalBySourceSubtreePin"] is True
    finding = j("scope-correction-finding.json")
    assert finding["affectedCells"] == 19 and finding["catalogTargetHashesUnchanged"] is True
    attestation = j("head-tree-attestation.json")
    assert attestation["headRefOid"] == attestation["branchRefOid"] == attestation["pullRefOid"] == HEAD
    assert attestation["treeOid"] == TREE and attestation["deploymentsForHeadBefore"] == attestation["deploymentsForHeadAfter"] == 0
    print(json.dumps({"verifier": "PASS", "cells": 19, "sourceIds": 3, "callersBySourceId": {key: value["productionCallerCount"] for key, value in callers.items()}, "historicalRowsHashOnly": 19, "priorHoldHistoryHashOnly": 152, "priorIdsHashOnly": 1782, "scopeCorrectionsHashOnly": 19, "tokenMismatches": dict(mismatches), "head": HEAD, "tree": TREE}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    verify()
