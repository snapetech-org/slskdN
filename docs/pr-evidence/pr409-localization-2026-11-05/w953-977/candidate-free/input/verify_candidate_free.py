#!/usr/bin/env python3
"""Verify the sealed W83 candidate-free packet against its exact-head worktree."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEAD = "fc8e42a06363ceee762ae084bbe716953d4a5d94"
TREE = "e04aa06b8cfb0ee41cae90aef601a0552b5e85bd"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
TEXT_KEYS = {"source", "sourceText", "target", "currentTarget", "proposedTarget", "proposedTargetText", "candidateTarget", "resolvedTarget", "resolvedTargetText", "formerTargetText", "rationale"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tsha(text):
    return sha(text.encode("utf-8"))


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key: " + key)
        out[key] = value
    return out


def fail(message):
    raise SystemExit("FAIL: " + message)


def main():
    repo = Path(sys.argv[1]).resolve()
    if subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip() != HEAD:
        fail("repo head")
    if subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"], text=True).strip() != TREE:
        fail("repo tree")
    sums = {}
    for line in (ROOT / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        file = ROOT / name
        if not file.is_file() or sha(file.read_bytes()) != digest:
            fail("checksum " + name)
        sums[name] = digest
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"}
    if set(sums) != actual:
        fail("checksum inventory")
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("head") != HEAD or manifest.get("tree") != TREE or manifest.get("window") != "W83" or manifest.get("candidateFree") is not True:
        fail("manifest identity")
    if manifest.get("continuationRankRange") != [953, 977] or manifest.get("remainingQueueRankRange") != [853, 877]:
        fail("manifest rank range")
    if manifest.get("locales") != LOCALES or manifest.get("cellCount") != 300:
        fail("manifest coverage")
    listed = {row["path"]: row for row in manifest["files"]}
    if set(listed) != actual - {"manifest.json"}:
        fail("manifest file inventory")
    for name, row in listed.items():
        if row["sha256"] != sha((ROOT / name).read_bytes()) or row["bytes"] != (ROOT / name).stat().st_size:
            fail("manifest payload " + name)

    structures = {row["locale"]: row for row in read_jsonl(ROOT / "catalog-structure.jsonl")}
    if list(structures) != LOCALES:
        fail("catalog locale order")
    catalogs = {}
    for locale in LOCALES:
        path = repo / f"src/web/public/locales/{locale}.json"
        data = path.read_bytes()
        if sha(data) != structures[locale]["sha256"]:
            fail("catalog file hash " + locale)
        obj = json.loads(data.decode("utf-8"), object_pairs_hook=no_duplicates)
        if len(obj) != 6175 or list(obj) != list(json.loads((repo / f"src/web/public/locales/ar.json").read_text(encoding="utf-8"), object_pairs_hook=no_duplicates)):
            fail("catalog structure " + locale)
        catalogs[locale] = obj

    selected = read_jsonl(ROOT / "selected-sources.jsonl")
    if len(selected) != 25 or [r["continuationRank"] for r in selected] != list(range(953, 978)):
        fail("selected rank sequence")
    if [r["remainingQueueRank"] for r in selected] != list(range(853, 878)):
        fail("remaining queue sequence")
    if selected[0]["sourceId"] != "src_358f9860b3f4e247":
        fail("first source ID")
    cells = read_jsonl(ROOT / "source-current-cells.jsonl")
    if len(cells) != 300 or len({(r["continuationRank"], r["locale"]) for r in cells}) != 300:
        fail("source/current coverage")
    if [(r["continuationRank"], r["locale"]) for r in cells] != [(rank, locale) for rank in range(953, 978) for locale in LOCALES]:
        fail("source/current ordered coverage")
    sel_by_rank = {r["continuationRank"]: r for r in selected}
    for row in cells:
        if row.get("containsCandidate") is not False or row.get("decision") is not None:
            fail("candidate or decision present")
        if row["remainingQueueRank"] != row["continuationRank"] - 100:
            fail("cell queue rank")
        if row["sourceId"] != sel_by_rank[row["continuationRank"]]["sourceId"] or row["sourceSha256"] != tsha(row["source"]):
            fail("source identity/hash")
        if row["source"] not in catalogs[row["locale"]] or catalogs[row["locale"]][row["source"]] != row["currentTarget"]:
            fail("current catalog target")
        if row["currentTargetSha256"] != tsha(row["currentTarget"]):
            fail("current target hash")
        if row["catalogFileSha256"] != structures[row["locale"]]["sha256"]:
            fail("cell catalog pin")
        token = row["tokenEvidence"]
        if token["placeholders"]["matches"] != (token["placeholders"]["source"] == token["placeholders"]["target"]):
            fail("placeholder evidence")
        if token["markup"]["matches"] != (token["markup"]["source"] == token["markup"]["target"]):
            fail("markup evidence")

    caller_rows = read_jsonl(ROOT / "caller-contexts.jsonl")
    if len(caller_rows) != 25:
        fail("caller coverage")
    for row in caller_rows:
        refs = row["callers"]
        if len(refs) != row["productionCallerCount"]:
            fail("caller count")
        if row["sourceTextIncluded"] != bool(refs) or (not refs and "source" in row):
            fail("callerless source text")
        if refs:
            full = []
            for ref in refs:
                context = ref["context"]
                if ref["lineSha256"] != tsha(ref["lineText"]) or ref["contextSha256"] != sha(canon(context)):
                    fail("caller line/context hash")
                full.append(ref)
            if sha(canon(full)) != next(c["callerContextSha256"] for c in cells if c["sourceId"] == row["sourceId"]):
                fail("caller context binding")

    for name in ("prior-held-cell-reattestation-hash-only.jsonl", "prior-hold-resolution-history-hash-only.jsonl", "prior-applied-targets-reattestation-hash-only.jsonl", "prior-selected-id-exclusions-hash-only.jsonl"):
        for row in read_jsonl(ROOT / name):
            if any(key in TEXT_KEYS for key in row):
                fail("text in hash-only artifact " + name)
            if row.get("sourceIdSha256") and row["sourceIdSha256"] != tsha(row["sourceId"]):
                fail("hash-only source ID hash " + name)
    if len(read_jsonl(ROOT / "prior-held-cell-reattestation-hash-only.jsonl")) != manifest["priorActiveHoldsReattested"]:
        fail("prior hold count")
    if len(read_jsonl(ROOT / "prior-applied-targets-reattestation-hash-only.jsonl")) != manifest["priorAppliedTargetsReattested"]:
        fail("prior applied target count")
    print(json.dumps({"result": "PASS", "head": HEAD, "tree": TREE, "sources": len(selected), "cells": len(cells),
                      "locales": len(LOCALES), "callers": sum(bool(r["productionCallerCount"]) for r in caller_rows),
                      "callerless": sum(not r["productionCallerCount"] for r in caller_rows),
                      "priorHolds": manifest["priorActiveHoldsReattested"],
                      "priorAppliedTargets": manifest["priorAppliedTargetsReattested"], "checksummedFiles": len(sums)}, indent=2))


if __name__ == "__main__":
    main()
