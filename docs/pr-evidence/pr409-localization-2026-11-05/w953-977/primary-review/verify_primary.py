#!/usr/bin/env python3
"""Verify the W83 primary ledger, its candidate-free input binding, and token safety."""
import collections
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent / "candidate-free" / "input"
HEAD = "fc8e42a06363ceee762ae084bbe716953d4a5d94"
TREE = "e04aa06b8cfb0ee41cae90aef601a0552b5e85bd"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
TEXT_KEYS = {"source", "sourceText", "target", "currentTarget", "candidateTarget", "proposedTarget", "rationale"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tsha(text):
    return sha(text.encode("utf-8"))


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def fail(message):
    raise SystemExit("FAIL: " + message)


def protected(text):
    values = set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", text))
    values.update(x for x in ("slskdN", "PodCore", "Wishlist", "soulfind", "FFmpeg", "Lidarr") if x in text)
    return sorted(values)


def token_signature(source, value):
    ph = collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", value))
    source_ph = collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", source))
    tags = collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", value))
    source_tags = collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", source))
    nums = ["".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in n) for n in re.findall(r"\d+", value)]
    source_nums = ["".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in n) for n in re.findall(r"\d+", source)]
    missing = [token for token in protected(source) if token not in value]
    return {"placeholderParity": source_ph == ph, "markupParity": source_tags == tags,
            "numericTokensPreserved": all(nums.count(x) >= n for x, n in collections.Counter(source_nums).items()),
            "protectedLiteralsPreserved": not missing, "missingProtectedLiterals": missing}


def main():
    repo = Path(sys.argv[1]).resolve()
    if subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip() != HEAD:
        fail("worktree head")
    if subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"], text=True).strip() != TREE:
        fail("worktree tree")
    if subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain=v1"], text=True).strip():
        fail("worktree dirty")

    sums = {}
    for line in (ROOT / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        path = ROOT / name
        if not path.is_file() or sha(path.read_bytes()) != digest:
            fail("checksum " + name)
        sums[name] = digest
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"}
    if set(sums) != actual:
        fail("checksum inventory")
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    input_manifest = json.loads((INPUT / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("window") != "W83" or manifest.get("head") != HEAD or manifest.get("tree") != TREE:
        fail("primary manifest identity")
    if manifest.get("candidateFreeInputOnly") is not True or manifest.get("blindReviewUsed") or manifest.get("crossReviewUsed") or manifest.get("rootAdjudicationDone"):
        fail("review provenance")
    if input_manifest.get("candidateFree") is not True or input_manifest.get("head") != HEAD or input_manifest.get("tree") != TREE:
        fail("candidate-free input identity")
    if manifest.get("candidateFreeInputManifestSha256") != sha((INPUT / "manifest.json").read_bytes()):
        fail("candidate-free manifest hash")
    if manifest.get("candidateFreeInputChecksumListSha256") != sha((INPUT / "SHA256SUMS.txt").read_bytes()):
        fail("candidate-free checksum-list hash")
    listed = {row["path"]: row for row in manifest["files"]}
    if set(listed) != actual - {"manifest.json"}:
        fail("primary payload inventory")
    for name, row in listed.items():
        if row["sha256"] != sha((ROOT / name).read_bytes()) or row["bytes"] != (ROOT / name).stat().st_size:
            fail("primary payload manifest " + name)

    candidate_rows = read_jsonl(INPUT / "source-current-cells.jsonl")
    if len(candidate_rows) != 300:
        fail("input cells")
    candidate_by_cell = {(r["continuationRank"], r["locale"]): r for r in candidate_rows}
    output = read_jsonl(ROOT / "primary-review.jsonl")
    if len(output) != 300 or len({(r["continuationRank"], r["locale"]) for r in output}) != 300:
        fail("primary coverage")
    expected_order = [(rank, locale) for rank in range(953, 978) for locale in LOCALES]
    if [(r["continuationRank"], r["locale"]) for r in output] != expected_order:
        fail("primary row order")
    counts = collections.Counter(r["disposition"] for r in output)
    if dict(counts) != manifest.get("dispositionCounts") or len(output) != manifest.get("cellCount"):
        fail("disposition counts")
    if manifest.get("correctionCount") != counts["correction"] or manifest.get("holdCellCount") != counts["hold"]:
        fail("review summary counts")
    correction_rows = read_jsonl(ROOT / "corrections.jsonl")
    held_rows = read_jsonl(ROOT / "holds-hash-only.jsonl")
    if len(correction_rows) != counts["correction"] or len(held_rows) != counts["hold"]:
        fail("correction/hold ledgers")
    correction_by_cell = {(r["continuationRank"], r["locale"]): r for r in correction_rows}

    for row in output:
        key = (row["continuationRank"], row["locale"])
        source = candidate_by_cell[key]
        for field in ("remainingQueueRank", "sourceId", "sourceSha256", "catalogPath", "catalogFileSha256", "catalogGitBlob",
                      "source", "currentTarget", "currentTargetSha256", "callerCount", "callerContextSha256", "callerRefs"):
            expected = source["callerRefs"] if field == "callerRefs" else source[field]
            if row[field] != expected:
                fail("input binding " + str(key) + " " + field)
        if row["head"] != HEAD or row["tree"] != TREE or row["reviewPass"] != "primary":
            fail("row pin " + str(key))
        if row["sourceSha256"] != tsha(row["source"]) or row["currentTargetSha256"] != tsha(row["currentTarget"]):
            fail("source/current hash " + str(key))
        if row["confidence"] not in {"high", "moderate", "low", "unknown"} or not row["rationale"]:
            fail("review rationale/confidence " + str(key))
        current_check = token_signature(row["source"], row["currentTarget"])
        if row["tokenCheck"]["current"] != current_check:
            fail("current token evidence " + str(key))
        if row["disposition"] == "correction":
            target = row["candidateTarget"]
            if not target or row["candidateTargetTextIncluded"] is not True or row["candidateTargetSha256"] != tsha(target):
                fail("candidate hash/text " + str(key))
            candidate_check = token_signature(row["source"], target)
            if row["tokenCheck"]["candidate"] != candidate_check:
                fail("candidate token evidence " + str(key))
            if not all(candidate_check[name] for name in ("placeholderParity", "markupParity", "numericTokensPreserved", "protectedLiteralsPreserved")):
                fail("candidate token mismatch " + str(key))
            c = correction_by_cell.get(key)
            if not c or c["candidateTarget"] != target or c["candidateTargetSha256"] != row["candidateTargetSha256"] or c["rationale"] != row["rationale"]:
                fail("correction ledger binding " + str(key))
        elif row["disposition"] == "accept-current":
            if row["candidateTarget"] is not None or row["candidateTargetSha256"] is not None or row["candidateTargetTextIncluded"] is not False:
                fail("accept-current has candidate " + str(key))
            if row["tokenCheck"]["candidate"] is not None:
                fail("accept-current candidate token evidence " + str(key))
            if key in correction_by_cell:
                fail("accept-current in corrections " + str(key))
        elif row["disposition"] == "hold":
            if row["candidateTarget"] is not None or row["candidateTargetTextIncluded"] is not False:
                fail("hold contains candidate " + str(key))
        else:
            fail("unknown disposition " + str(key))
    for row in held_rows:
        if any(key in TEXT_KEYS for key in row):
            fail("text in hash-only hold")
    print(json.dumps({"result": "PASS", "head": HEAD, "tree": TREE, "cells": len(output),
                      "dispositions": dict(counts), "corrections": len(correction_rows), "holds": len(held_rows),
                      "protectedPlaceholderMarkupNumberChecks": "PASS", "checksummedFiles": len(sums)}, indent=2))


if __name__ == "__main__":
    main()
