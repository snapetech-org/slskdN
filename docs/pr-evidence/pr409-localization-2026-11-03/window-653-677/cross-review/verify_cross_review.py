#!/usr/bin/env python3
import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

HEAD = "d0317d8258a31d05b7f163921c2e39f93deabfca"
TREE = "01475aeffa17f6151c4bf161890662167c959bb0"
LOCALES = ("ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def verify_sums(directory, filename):
    entries = {}
    for line in (directory / filename).read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        entries[name] = digest
    assert entries, "empty checksum list"
    for name, digest in entries.items():
        assert sha((directory / name).read_bytes()) == digest, "checksum mismatch: " + name
    return entries


def ph(value):
    return sorted(re.findall(r"\{[^{}]+\}", value))


def tags(value):
    return sorted(re.findall(r"</?[A-Za-z][^>]*>", value))


def nums(value):
    return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])", value)


def prot(value):
    found = set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])", value))
    for term in ("Wishlist", "Soulseek", "Discogs", "Pod"):
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", value):
            found.add(term)
    return sorted(found)


def checks(source, target):
    missing = [term for term in prot(source) if term not in target]
    return {
        "placeholders": {"source": ph(source), "target": ph(target), "matches": ph(source) == ph(target)},
        "markupTags": {"source": tags(source), "target": tags(target), "matches": tags(source) == tags(target)},
        "numericTokens": {"source": nums(source), "target": nums(target), "matches": nums(source) == nums(target)},
        "protectedLiterals": {"source": prot(source), "target": prot(target), "missing": missing, "matches": not missing},
    }


def main():
    parser = argparse.ArgumentParser(description="Verify the W71 cross-review packet against its three source packets.")
    parser.add_argument("--candidate-free", type=Path)
    parser.add_argument("--primary", type=Path)
    parser.add_argument("--blind", type=Path)
    args = parser.parse_args()
    out = Path(__file__).resolve().parent
    manifest = read_json(out / "manifest.json")
    candidate = args.candidate_free or Path(manifest["candidateFreeInput"]["path"])
    primary = args.primary or Path(manifest["primaryInput"]["path"])
    blind = args.blind or Path(manifest["blindInput"]["path"])
    assert candidate.is_dir() and primary.is_dir() and blind.is_dir(), "input path missing; pass --candidate-free, --primary, and --blind"
    out_sums = verify_sums(out, "SHA256SUMS.txt")
    verify_sums(candidate, "PACKET-SHA256SUMS.txt")
    verify_sums(primary, "SHA256SUMS.txt")
    verify_sums(blind, "SHA256SUMS.txt")
    assert sha((candidate / "PACKET-SHA256SUMS.txt").read_bytes()) == manifest["candidateFreeInput"]["checksumListSha256"]
    assert sha((primary / "SHA256SUMS.txt").read_bytes()) == manifest["primaryInput"]["checksumListSha256"]
    assert sha((blind / "SHA256SUMS.txt").read_bytes()) == manifest["blindInput"]["checksumListSha256"]
    candidate_manifest = read_json(candidate / "manifest.json")
    primary_manifest = read_json(primary / "manifest.json")
    blind_manifest = read_json(blind / "manifest.json")
    assert candidate_manifest["sourceInventorySha256"] == manifest["candidateFreeInput"]["sourceInventorySha256"]
    assert primary_manifest["head"] == blind_manifest["head"] == HEAD
    assert primary_manifest["tree"] == blind_manifest["tree"] == TREE

    source_rows = read_jsonl(candidate / "source-current-cells.jsonl")
    context_rows = {row["sourceId"]: row for row in read_jsonl(candidate / "caller-contexts.jsonl")}
    primary_rows = {(row["sourceId"], row["locale"]): row for row in read_jsonl(primary / "primary-review.jsonl")}
    blind_rows = {(row["sourceId"], row["locale"]): row for row in read_jsonl(blind / "blind-ledger.jsonl")}
    review_rows = read_jsonl(out / "cross-review.jsonl")
    assert len(source_rows) == len(primary_rows) == len(blind_rows) == len(review_rows) == 300
    assert len({(row["sourceId"], row["locale"]) for row in review_rows}) == 300
    assert manifest["head"] == HEAD and manifest["tree"] == TREE
    assert sha((candidate / "PACKET-SHA256SUMS.txt").read_bytes()) == manifest["candidateFreeInput"]["checksumListSha256"]
    assert manifest["scope"] == {"window": "W71", "continuationRankStart": 653, "continuationRankEnd": 677, "sourceIds": 25, "locales": 12, "cells": 300}
    assert {(row["continuationRank"], row["locale"]) for row in source_rows} == {(rank, locale) for rank in range(653, 678) for locale in LOCALES}

    baseline = collections.Counter()
    for item in source_rows:
        current_check = checks(item["source"], item["currentTarget"])
        for field, keyname in (("placeholderMismatch", "placeholders"), ("markupMismatch", "markupTags"), ("numericMismatch", "numericTokens"), ("protectedLiteralMismatch", "protectedLiterals")):
            baseline[field] += not current_check[keyname]["matches"]
    final_counts = collections.Counter()
    exact_diff = normalized_diff = accept_change_diff = common = primary_only = blind_only = 0
    selected_primary = selected_blind = selected_blind_only = primary_unselected = blind_unselected = 0
    for item, row in zip(source_rows, review_rows):
        key = (item["sourceId"], item["locale"])
        p = primary_rows[key]
        b = blind_rows[key]
        context = context_rows[item["sourceId"]]
        assert row["head"] == HEAD and row["tree"] == TREE
        for name in ("sourceId", "sourceSha256", "locale", "catalogPath", "catalogFileSha256", "catalogGitBlob", "currentTargetSha256", "callerContextSha256"):
            assert row[name] == item[name], "input pin mismatch: " + name
        assert row["callerCount"] == context["productionCallerCount"]
        assert row["callerContextSha256"] == item["callerContextSha256"]
        for name in ("sourceSha256", "currentTargetSha256", "callerContextSha256", "catalogFileSha256", "catalogGitBlob"):
            assert row[name] == p[name]
        assert row["primaryDisposition"] == p["disposition"]
        assert row["primaryProposalPresent"] == bool(p["proposedTarget"])
        assert row["primaryProposalSha256"] == p["proposedTargetSha256"]
        assert row["blindDisposition"] == b["disposition"]
        assert row["blindProposalPresent"] == bool(b.get("proposedTargetSha256"))
        assert row["blindProposalSha256"] == b.get("proposedTargetSha256")
        expected_refs = [{k: v for k, v in ref.items() if k != "lineText"} for ref in item["callerRefs"]]
        assert row["callerRefs"] == expected_refs
        assert row["baselineDiagnostics"] == b["baselineDiagnostics"]
        exact_diff += p["disposition"] != b["disposition"]
        status_p = "change" if p["disposition"] not in ("accept-current", "hold") else p["disposition"]
        status_b = "change" if b["disposition"] not in ("accept-current", "hold") else b["disposition"]
        accept_change_diff += status_p != status_b
        normalized_p = {"correct": "correct", "correction": "correct", "refine": "refine", "refinement": "refine"}.get(p["disposition"], p["disposition"])
        normalized_b = {"correct": "correct", "correction": "correct", "refine": "refine", "refinement": "refine"}.get(b["disposition"], b["disposition"])
        normalized_diff += normalized_p != normalized_b
        has_p = p["disposition"] not in ("accept-current", "hold")
        has_b = b["disposition"] not in ("accept-current", "hold")
        common += has_p and has_b
        primary_only += has_p and not has_b
        blind_only += has_b and not has_p
        rec = row["recommendation"]
        final_counts[rec] += 1
        if item["continuationRank"] == 654:
            assert rec == "hold"
            assert row["sourceIncluded"] is False and row["currentTargetIncluded"] is False
            assert "source" not in row and "currentTarget" not in row and "recommendedTarget" not in row
            assert row["recommendedTargetIncluded"] is False and row["recommendedTargetSha256"] is None
            assert row["targetTextIncluded"] is False and row["currentTokenChecks"] is None and row["recommendedTokenChecks"] is None
            assert context["productionCallerCount"] == 0
            assert p["disposition"] == b["disposition"] == "hold"
        else:
            assert row["sourceIncluded"] is True and row["currentTargetIncluded"] is True
            assert row["source"] == item["source"] and row["currentTarget"] == item["currentTarget"]
            assert sha(row["source"].encode("utf-8")) == item["sourceSha256"]
            assert sha(row["currentTarget"].encode("utf-8")) == item["currentTargetSha256"]
            assert row["currentTokenChecks"] == checks(item["source"], item["currentTarget"])
            if rec in ("correct", "refine"):
                target = row.get("recommendedTarget")
                assert target and row["recommendedTargetIncluded"] is True and row["targetTextIncluded"] is True
                assert sha(target.encode("utf-8")) == row["recommendedTargetSha256"]
                assert row["recommendedTokenChecks"] == checks(item["source"], target)
                assert all(value["matches"] for value in row["recommendedTokenChecks"].values())
                assert row["recommendationBasis"]
            else:
                assert rec == "accept-current" and row.get("recommendedTarget") is None
                assert row["recommendedTargetIncluded"] is False and row["recommendedTargetSha256"] is None
                assert row["recommendedTokenChecks"] is None
        if rec in ("correct", "refine"):
            selected_primary += bool(p["proposedTarget"])
            selected_blind += bool(b.get("proposedTargetSha256"))
            selected_blind_only += (not has_p) and has_b
        else:
            primary_unselected += has_p
            blind_unselected += has_b

    assert dict(final_counts) == manifest["finalDispositionCounts"]
    assert dict(collections.Counter(row["disposition"] for row in primary_rows.values())) == manifest["primaryDispositionCounts"]
    assert dict(collections.Counter(row["disposition"] for row in blind_rows.values())) == manifest["blindDispositionCounts"]
    comparison = manifest["primaryBlindComparison"]
    assert comparison["cellsWithExactDispositionLabelDifference"] == exact_diff
    assert comparison["cellsWithNormalizedDispositionDifference"] == normalized_diff
    assert comparison["cellsWithAcceptVersusChangeDifference"] == accept_change_diff
    assert comparison["proposalsBoth"] == common and comparison["primaryOnlyProposals"] == primary_only and comparison["blindOnlyProposals"] == blind_only
    assert comparison["selectedPrimaryFlaggedChanges"] == selected_primary
    assert comparison["selectedBlindFlaggedChanges"] == selected_blind
    assert comparison["selectedBlindOnlyChanges"] == selected_blind_only
    assert comparison["primaryOnlyFlagsRetainedAsCurrent"] == primary_unselected
    assert comparison["blindOnlyFlagsRetainedAsCurrent"] == blind_unselected
    assert dict(baseline) == manifest["baselineTokenMismatches"]
    assert baseline == {"placeholderMismatch": 0, "markupMismatch": 0, "numericMismatch": 2, "protectedLiteralMismatch": 1}
    assert comparison["cellsWithAcceptVersusChangeDifference"] == 36
    assert final_counts == {"accept-current": 231, "hold": 12, "correct": 40, "refine": 17}
    assert sum(row["recommendation"] in ("correct", "refine") for row in review_rows) == manifest["targetTextIncludedForSelectedChanges"] == 57

    prior_holds = read_jsonl(out / "prior-held-cell-reattestation-hash-only.jsonl")
    prior_selected = read_jsonl(out / "prior-selected-id-exclusions-hash-only.jsonl")
    assert len(prior_holds) == manifest["hashOnlyLineage"]["priorHeldCells"] == 140
    assert len(prior_selected) == manifest["hashOnlyLineage"]["priorSelectedSourceIds"] == 1757
    assert all(row.get("targetTextIncluded") is False and "holdReason" not in row and "currentTarget" not in row and "priorTarget" not in row for row in prior_holds)
    assert all(row.get("sourceTextIncluded") is False and row.get("targetTextIncluded") is False and "source" not in row and "target" not in row for row in prior_selected)
    assert manifest["hashOnlyLineage"]["containsPriorSourceText"] is False and manifest["hashOnlyLineage"]["containsPriorTargetText"] is False
    assert sum(row["recommendation"] == "hold" for row in review_rows) == manifest["hashOnlyLineage"]["newCallerlessRank654Holds"] == 12

    supplemental = read_json(out / "supplemental-caller-context.json")
    assert supplemental["head"] == HEAD and supplemental["path"] == "src/web/src/components/Player/Visualizer.jsx"
    rank664 = next(row for row in source_rows if row["continuationRank"] == 664)
    ref = rank664["callerRefs"][0]
    assert supplemental["gitBlob"] == ref["gitBlob"] and supplemental["fileSha256"] == ref["fileSha256"]
    before = read_json(out / "live-before.json")
    after = read_json(out / "live-after.json")
    for attestation in (before, after):
        assert attestation["repository"] == "snapetech-org/slskdN" and attestation["pullRequest"] == 409
        assert attestation["headRefOid"] == attestation["branchRefOid"] == attestation["pullRefOid"] == HEAD
        assert attestation["treeOid"] == TREE
    assert before["headRefOid"] == after["headRefOid"] and before["treeOid"] == after["treeOid"]

    print(json.dumps({"verifier": "PASS", "outputFilesVerified": len(out_sums), "cells": len(review_rows), "finalDispositionCounts": dict(final_counts), "selectedTargets": 57, "primaryBlindAcceptChangeDisagreements": accept_change_diff, "priorHeldHashes": len(prior_holds), "priorSelectedIdsHashOnly": len(prior_selected), "baselineTokenMismatches": dict(baseline), "recordedLiveHeadTree": "unchanged"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
