#!/usr/bin/env python3
"""Portable standard-library verifier for the sealed W78 cross-audit packet."""
from __future__ import annotations

import collections
import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HEAD = "4120c9637e71466dc98d51a5a342dee199a1e004"
TREE = "063b62f268eb81253d2b9b4c77ad045c2f25a394"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
TEXT_FIELDS = {"source", "sourceText", "currentTarget", "target", "crossTarget", "proposedTarget"}


def fail(message: str) -> None:
    print("FAIL:", message, file=sys.stderr)
    raise SystemExit(1)


def need(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text_sha(value: str) -> str:
    return sha(value.encode("utf-8"))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rows(name: str) -> list[dict]:
    return [json.loads(line) for line in (ROOT / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def files_and_checksums() -> dict:
    manifest = load_json(ROOT / "manifest.json")
    expected = {item["path"]: item for item in manifest["files"]}
    need(len(expected) == len(manifest["files"]), "duplicate manifest paths")
    sum_members = {}
    for line in (ROOT / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(maxsplit=1)
        rel = rel.lstrip("* ")
        need(rel not in sum_members, "duplicate checksum entry: " + rel)
        sum_members[rel] = digest
        path = (ROOT / rel).resolve()
        need(ROOT.resolve() in path.parents, "checksum path escapes packet")
        need(path.is_file(), "missing checksum member: " + rel)
        need(sha(path.read_bytes()) == digest, "checksum mismatch: " + rel)
    need(set(sum_members) == set(expected) | {"manifest.json"}, "checksum membership mismatch")
    for name, item in expected.items():
        path = ROOT / name
        need(path.is_file() and path.stat().st_size == item["bytes"] and sha(path.read_bytes()) == item["sha256"],
             "manifest file hash/size mismatch: " + name)
    need(sum_members["manifest.json"] == sha((ROOT / "manifest.json").read_bytes()), "manifest checksum mismatch")
    return manifest


def token_check(source: str, target: str) -> dict:
    placeholders = lambda s: collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", s))
    tags = lambda s: collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", s))
    nums = lambda s: collections.Counter(re.findall(r"\d+", s))
    protected = lambda s: sorted(set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", s)) | {x for x in ("slskdN", "Tor", "Wishlist", "Chromaprint") if x in s})
    src_nums, dst_nums = nums(source), nums(target)
    missing = [x for x in protected(source) if x not in target]
    return {
        "placeholderParity": placeholders(source) == placeholders(target),
        "markupParity": tags(source) == tags(target),
        "numericTokensPreserved": all(dst_nums[n] >= count for n, count in src_nums.items()),
        "protectedLiteralsPreserved": not missing,
        "missingProtectedLiterals": missing,
    }


def main() -> None:
    manifest = files_and_checksums()
    need((manifest.get("head"), manifest.get("tree"), manifest.get("window")) == (HEAD, TREE, "W78"), "source pin")
    need(manifest.get("liveRefsMatchPin") is True, "live GitHub refs do not match pin")
    need(manifest.get("noRepositoryEdits") is True and manifest.get("noPullRequestEdits") is True, "packet claims edits")
    need(manifest.get("nativeSpeakerSignoff") is False and manifest.get("browserReview") is False, "unsupported review claim")

    live = load_json(ROOT / "live-github-api-attestation.json")
    need(live.get("matchesPin") is True and live.get("state") == "OPEN" and live.get("draft") is True and live.get("merged") is False,
         "live PR state/ref pin")
    need(live.get("headRefOid") == live.get("branchRefOid") == live.get("pullRefOid") == HEAD, "live refs disagree")
    need(live.get("headRefName") == "codex/slskdn-oidc-tooltip-localization-20261030", "live head branch name")
    source = load_json(ROOT / "source-worktree-attestation.json")
    need(source.get("head") == HEAD and source.get("tree") == TREE and source.get("clean") is True, "source checkout pin/status")
    need(source.get("checkoutState") == "detached", "source worktree checkout state")
    refs = source.get("localRefsReadOnly", {})
    need(refs.get("refs/remotes/origin/pr/409") != HEAD and refs.get("refs/remotes/origin/main") != live.get("baseRefOid"),
         "stale local remote refs were not recorded")
    need(refs.get("refs/heads/codex/slskdn-oidc-tooltip-localization-20261030") != HEAD,
         "stale local branch ref was not recorded")

    decisions = rows("cross-review-decisions.jsonl")
    plan = rows("selected-proposal-apply-plan.jsonl")
    noops = rows("no-op-ledger.jsonl")
    holds = rows("unresolved-holds-hash-only.jsonl")
    need(len(decisions) == 300, "expected 300 cross decisions")
    key = lambda row: (row["sourceId"], row["locale"])
    keys = [key(row) for row in decisions]
    need(len(set(keys)) == 300, "duplicate cross cell")
    by_key = {key(row): row for row in decisions}
    coverage = collections.defaultdict(set)
    for row in decisions:
        coverage[row["sourceId"]].add(row["locale"])
        need(828 <= row["continuationRank"] <= 852, "rank outside W78 window")
    need(len(coverage) == 25 and all(locales == set(LOCALES) for locales in coverage.values()), "source/locale coverage")
    counts = collections.Counter(row["crossDisposition"] for row in decisions)
    need(counts == {"propose": 63, "keep": 225, "hold": 12}, "cross decision counts: " + repr(dict(counts)))

    plans_by_key = {key(row): row for row in plan}
    noops_by_key = {key(row): row for row in noops}
    holds_by_key = {key(row): row for row in holds}
    need(len(plans_by_key) == 63 and len(noops_by_key) == 225 and len(holds_by_key) == 12, "ledger counts")
    need(not (set(plans_by_key) & set(noops_by_key) or set(plans_by_key) & set(holds_by_key) or set(noops_by_key) & set(holds_by_key)), "ledger overlap")
    need(set(plans_by_key) | set(noops_by_key) | set(holds_by_key) == set(by_key), "ledger partition mismatch")

    for row in decisions:
        k = key(row)
        disposition = row["crossDisposition"]
        if disposition == "hold":
            need(not (TEXT_FIELDS & set(row)), "callerless cross decision contains text")
            need(row.get("productionCallerCount") == 0, "held row has caller")
            h = holds_by_key[k]
            need(not (TEXT_FIELDS & set(h)) and h.get("sourceTextIncluded") is False and h.get("targetTextIncluded") is False,
                 "hold ledger is not text-free")
            need(h["currentTargetSha256"] == row["currentTargetSha256"], "hold target hash mismatch")
            continue
        source_text, current = row["sourceText"], row["currentTarget"]
        need(row.get("productionCallerCount", 0) > 0, "visible row lacks caller")
        need(text_sha(source_text) == row["sourceSha256"], "source text hash mismatch")
        need(text_sha(current) == row["currentTargetSha256"], "current target hash mismatch")
        need(row.get("callerRefs") is not None and row.get("callerContextSha256"), "caller evidence missing")
        if disposition == "propose":
            target = row["crossTarget"]
            need(target != current and text_sha(target) == row["crossTargetSha256"], "proposal text/hash mismatch")
            checks = token_check(source_text, target)
            need(all(checks[name] for name in ("placeholderParity", "markupParity", "numericTokensPreserved", "protectedLiteralsPreserved")),
                 "proposal token-integrity failure")
            proposal = plans_by_key[k]
            need(proposal["target"] == target and proposal["targetSha256"] == row["crossTargetSha256"], "apply plan target mismatch")
            need(proposal["currentTargetSha256"] == row["currentTargetSha256"], "apply plan current-value guard mismatch")
            need(proposal["catalogFileSha256"] == row["catalogFileSha256"] and proposal["catalogGitBlob"] == row["catalogGitBlob"],
                 "apply plan catalog guard mismatch")
            need(proposal["head"] == HEAD and proposal["tree"] == TREE, "apply plan pin mismatch")
        else:
            need(disposition == "keep" and row["crossTargetSha256"] == row["currentTargetSha256"], "bad no-op row")
            noop = noops_by_key[k]
            need(noop["currentTargetSha256"] == row["currentTargetSha256"], "no-op hash mismatch")

    prior = rows("prior-held-cell-reattestation-hash-only.jsonl")
    need(len(prior) == 331, "expected all 331 carried prior hold hashes")
    for row in prior:
        need(not (TEXT_FIELDS & set(row)) and row.get("sourceTextIncluded") is False and row.get("targetTextIncluded") is False,
             "carried prior hold lineage contains text")
    lineage = load_json(ROOT / "prior-hold-lineage-summary.json")
    need(lineage["carriedHoldCells"] == 331 and sum(lineage["holdLineage"].values()) == 331, "prior lineage counts")
    resolution_history = rows("prior-hold-resolution-history-hash-only.jsonl")
    need(len(resolution_history) == 13, "prior hold resolution history rows")

    summary = load_json(ROOT / "summary.json")
    need(summary["crossDecisionCounts"] == dict(counts), "summary cross counts")
    need(summary["priorHeldCellsCarried"] == 331 and summary["priorHeldTargetHashesAllMatch"] is True, "summary carried lineage")
    print(json.dumps({"result": "PASS", "cells": len(decisions), "decisionCounts": dict(counts),
                      "priorHeldHashes": len(prior), "resolutionHistoryRows": len(resolution_history)}, sort_keys=True))


if __name__ == "__main__":
    main()
