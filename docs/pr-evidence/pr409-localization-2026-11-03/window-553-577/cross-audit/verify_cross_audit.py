#!/usr/bin/env python3
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEAD = "2dc64b9d00f6611aeb72713af81db53ccc5a4084"
TREE = "f13462300926ac897235cd92ae68c87695c38c31"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]

def read_json(path):
    return json.loads(path.read_text())

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def sha_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()

def placeholders(value):
    return re.findall(r"\{[^{}]+\}", value)

def tags(value):
    return re.findall(r"</?[A-Za-z][^>]*>", value)

def numbers(value):
    return re.findall(r"[0-9]+(?:[.,][0-9]+)?", value)

M = read_json(ROOT / "manifest.json")
S = read_json(ROOT / "summary.json")
assert M["repository"] == "snapetech-org/slskdN" and M["pullRequest"] == 409
assert M["branch"] == BRANCH and M["head"] == HEAD and M["tree"] == TREE
assert M["packetSealStatus"] == "sealed"
assert M["primaryMaterialOpened"] is True and M["blindMaterialOpened"] is True
assert M["repositoryOrPRFilesEdited"] is False
assert M["testsBuildsCiBrowserOrReleaseActionsRun"] is False

for name in ("live-ref-start.json", "live-ref-seal.json"):
    att = read_json(ROOT / name)
    assert att["result"] == "PASS"
    assert att["repository"] == "snapetech-org/slskdN" and att["pullRequest"] == 409
    assert att["state"] == "OPEN" and att["isDraft"] is True
    assert att["branch"] == BRANCH and att["head"] == HEAD and att["tree"] == TREE
    assert att["refs"] == {
        "refs/heads/" + BRANCH: HEAD,
        "refs/pull/409/head": HEAD
    }
assert M["liveRefStartAttestationSha256"] == sha_bytes((ROOT / "live-ref-start.json").read_bytes())
assert M["liveRefSealAttestationSha256"] == sha_bytes((ROOT / "live-ref-seal.json").read_bytes())

rows = read_jsonl(ROOT / "cross-audit-ledger.jsonl")
assert len(rows) == 300
cells = {(row["continuationRank"], row["locale"]): row for row in rows}
assert len(cells) == 300
expected_keys = {(rank, locale) for rank in range(553, 578) for locale in LOCALES}
assert set(cells) == expected_keys
category_counts = Counter()
selection_counts = Counter()
disposition_counts = Counter()
baseline_protected_mismatches = 0
final_protected_mismatches = 0
baseline_placeholder_mismatches = baseline_markup_mismatches = baseline_numeric_mismatches = 0

for key, row in cells.items():
    assert row["schema"] == "slskdn-w67-cross-audit-cell/v1"
    assert row["head"] == HEAD and row["tree"] == TREE
    assert row["repository"] == "snapetech-org/slskdN" and row["pullRequest"] == 409
    assert row["sourceSha256"] == sha_text(row["source"])
    assert row["currentTargetSha256"] == sha_text(row["currentTarget"])
    assert row["primaryTargetSha256"] == sha_text(row["primaryTarget"])
    assert row["blindTargetSha256"] == sha_text(row["blindTarget"])
    assert row["finalTargetSha256"] == sha_text(row["finalTarget"])
    assert row["catalogPath"] and row["catalogFileSha256"] and row["catalogGitBlob"]
    assert row["callerContextSha256"] and row["callerRefs"]
    assert row["crossAuditRationale"]
    assert row["primaryDisposition"] in {"accept-current", "correction", "refinement"}
    assert row["blindDisposition"] in {"accept-current", "correction", "refinement"}
    assert (row["primaryDisposition"] == "accept-current") == (row["primaryTarget"] == row["currentTarget"])
    assert (row["blindDisposition"] == "accept-current") == (row["blindTarget"] == row["currentTarget"])
    assert Counter(placeholders(row["source"])) == Counter(placeholders(row["finalTarget"]))
    assert Counter(tags(row["source"])) == Counter(tags(row["finalTarget"]))
    assert Counter(numbers(row["source"])) == Counter(numbers(row["finalTarget"]))
    assert all(row["finalTarget"].count(literal) == row["source"].count(literal)
               for literal in row["sourceProtectedLiterals"])
    if Counter(placeholders(row["source"])) != Counter(placeholders(row["currentTarget"])):
        baseline_placeholder_mismatches += 1
    if Counter(tags(row["source"])) != Counter(tags(row["currentTarget"])):
        baseline_markup_mismatches += 1
    if Counter(numbers(row["source"])) != Counter(numbers(row["currentTarget"])):
        baseline_numeric_mismatches += 1
    if any(row["currentTarget"].count(literal) != row["source"].count(literal)
           for literal in row["sourceProtectedLiterals"]):
        baseline_protected_mismatches += 1
    if any(row["finalTarget"].count(literal) != row["source"].count(literal)
           for literal in row["sourceProtectedLiterals"]):
        final_protected_mismatches += 1

    if row["primaryTarget"] == row["blindTarget"]:
        if row["primaryTarget"] == row["currentTarget"]:
            assert row["crossAuditCategory"] == "both-current"
            assert row["selection"] == "consensus-current"
            assert row["finalTarget"] == row["currentTarget"]
            assert row["finalDisposition"] == "accept-current"
        else:
            assert row["crossAuditCategory"] == "same-proposal"
            assert row["selection"] == "consensus-proposal"
            assert row["finalTarget"] == row["primaryTarget"] == row["blindTarget"]
            expected_disposition = "correction" if "correction" in {
                row["primaryDisposition"], row["blindDisposition"]} else "refinement"
            assert row["finalDisposition"] == expected_disposition
    else:
        assert row["crossAuditCategory"] == "proposal-disagreement"
        assert row["selection"] in {"primary", "blind"}
        expected_target = row["primaryTarget"] if row["selection"] == "primary" else row["blindTarget"]
        expected_disposition = row["primaryDisposition"] if row["selection"] == "primary" else row["blindDisposition"]
        assert row["finalTarget"] == expected_target
        assert row["finalDisposition"] == ("accept-current" if expected_target == row["currentTarget"] else expected_disposition)
    category_counts[row["crossAuditCategory"]] += 1
    selection_counts[row["selection"]] += 1
    disposition_counts[row["finalDisposition"]] += 1

assert baseline_placeholder_mismatches == baseline_markup_mismatches == baseline_numeric_mismatches == 0
assert baseline_protected_mismatches == S["protectedLiteralBaselineMismatches"] == 10
assert final_protected_mismatches == S["protectedLiteralFinalMismatches"] == 0
assert S["placeholderMarkupNumericFinalMismatches"] == 0
assert category_counts == Counter({"both-current": 186, "proposal-disagreement": 105, "same-proposal": 9})
assert category_counts == Counter(S["categoryCounts"])
assert selection_counts == Counter(S["selectionCounts"])
assert disposition_counts == Counter(S["finalDispositionCounts"])
assert disposition_counts["correction"] + disposition_counts["refinement"] == S["updateCount"]
assert disposition_counts["accept-current"] == S["noOpCount"]
assert S["newHoldCount"] == 0

disagreements = read_jsonl(ROOT / "disagreements.jsonl")
expected_disagreements = [row for row in rows if row["crossAuditCategory"] == "proposal-disagreement"]
assert disagreements == expected_disagreements == [row for row in rows if row["crossAuditCategory"] != "both-current" and row["crossAuditCategory"] != "same-proposal"]

proposal_rows = (ROOT / "proposal-hashes.tsv").read_text().splitlines()
assert len(proposal_rows) == 300
for line, row in zip(proposal_rows, rows):
    values = line.split("\t")
    assert len(values) == 10
    expected = [
        str(row["continuationRank"]), row["locale"], row["sourceId"],
        row["primaryTargetSha256"], row["blindTargetSha256"], row["finalTargetSha256"],
        row["crossAuditCategory"], row["selection"], row["finalDisposition"], row["catalogGitBlob"]
    ]
    assert values == expected

final_hash_rows = (ROOT / "final-proposal-hashes.txt").read_text().splitlines()
assert len(final_hash_rows) == 300
for line, row in zip(final_hash_rows, rows):
    assert line.split("\t") == [
        str(row["continuationRank"]), row["locale"], row["sourceId"], row["finalTargetSha256"]
    ]

holds = read_jsonl(ROOT / "prior-held-cell-reattestation.jsonl")
assert len(holds) == 128
assert len({(row["continuationRank"], row["locale"]) for row in holds}) == 128
assert sum(row["callerCount"] == 0 for row in holds) == S["priorHoldCallerlessCount"]
for row in holds:
    assert row["schema"] == "slskdn-w67-cross-audit-hold/v1"
    assert row["priorDisposition"] == "hold"
    assert row["priorTargetSha256"] == row["currentTargetSha256"]
    assert row["status"] == "reattested-unchanged"
    assert row["heldTargetTextIncluded"] is False
    assert row["callerCount"] >= 0 and row["callerContextSha256"]
    assert row["catalogPath"] and row["catalogFileSha256"] and row["catalogGitBlob"]

assert S["cellCount"] == 300 and S["sourceCount"] == 25 and S["localeCount"] == 12
assert S["priorHoldsReattestedUnchanged"] == 128
assert S["updateCount"] == 111 and S["noOpCount"] == 189

listed = {}
for line in (ROOT / "SHA256SUMS.txt").read_text().splitlines():
    digest, name = line.split("  ", 1)
    listed[name] = digest
expected_names = {path.name for path in ROOT.iterdir() if path.is_file() and path.name != "SHA256SUMS.txt"}
assert set(listed) == expected_names
for name, digest in listed.items():
    assert sha_bytes((ROOT / name).read_bytes()) == digest, name

print(json.dumps({
    "result": "PASS",
    "head": HEAD,
    "tree": TREE,
    "cells": len(rows),
    "categories": dict(category_counts),
    "selectedBy": dict(selection_counts),
    "finalDisposition": dict(disposition_counts),
    "updates": S["updateCount"],
    "noOps": S["noOpCount"],
    "newHolds": S["newHoldCount"],
    "priorHoldsReattestedUnchanged": len(holds),
    "tokenAndProtectedLiteralChecks": "PASS",
    "selfContainedHashesAndChecksums": "PASS",
    "liveRefsStartAndSeal": "PASS"
}, indent=2))
