#!/usr/bin/env python3
"""Validate the frozen W34 review pins, create its exact apply plan, and apply it."""
from __future__ import annotations

import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MANUAL = REPO / "docs/pr-evidence/pr409-manual-semantic-review-2026-11-01/window34"
PACKET = MANUAL / "review-packet"
INDEPENDENT = MANUAL / "independent-review"
ROOT_REVIEW = MANUAL / "root-cross-review"
BASE = "dc8ed2406a2247600d487df1ae3128ce08cc7faa"
BASE_TREE = "9909f5d6e32dfcc78ba53aa0c838f95e9ba246d3"
SOURCE_TREE = "594e56c3f439bad476b1bd57e0de1665c62fa1bb"
REMOTE_REF = "refs/heads/codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES = ["es", "zh-Hans", "hi", "de", "ja", "fr", "pt-BR", "ar", "ko", "zh-Hant", "vi", "id"]


def sha(value: bytes | str) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode("utf-8")).hexdigest()


def git(*args: str, raw: bool = False) -> bytes | str:
    value = subprocess.check_output(["git", "-C", str(REPO), *args])
    return value if raw else value.decode("utf-8").strip()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def require(ok: bool, message: str) -> None:
    if not ok:
        raise SystemExit(f"FAIL: {message}")


def verify_sums(directory: Path) -> None:
    result = subprocess.run(["sha256sum", "-c", "SHA256SUMS.txt"], cwd=directory, capture_output=True, text=True)
    require(result.returncode == 0, f"checksum verification failed in {directory}: {result.stderr or result.stdout}")


def blob(commit: str, path: str) -> bytes:
    return git("show", f"{commit}:{path}", raw=True)


verify_sums(PACKET)
verify_sums(INDEPENDENT)
verify_sums(ROOT_REVIEW)
manifest = json.loads((PACKET / "manifest.json").read_text(encoding="utf-8"))
input_rows = read_jsonl(PACKET / "review-input.jsonl")
decision_rows = read_jsonl(PACKET / "review-decisions.jsonl")
candidate_rows = read_jsonl(PACKET / "crossreview-plan.jsonl")
independent_rows = read_jsonl(INDEPENDENT / "independent-crossreview-window34.jsonl")
inputs = {row["id"]: row for row in input_rows}
decisions = {row["id"]: row for row in decision_rows}
candidates = {row["id"]: row for row in candidate_rows}
independent = {row["id"]: row for row in independent_rows}
root_rows = read_jsonl(ROOT_REVIEW / "root-crossreview.jsonl")
root_by_id = {row["id"]: row for row in root_rows}
require(len(input_rows) == 274 and len(inputs) == 274 and len(decision_rows) == 274 and len(decisions) == 274 and len(independent_rows) == 274 and len(independent) == 274, "expected 274 unique packet/independent rows")
require(len(candidate_rows) == 33 and len(candidates) == 33 and len(root_rows) == 34 and len(root_by_id) == 34, "candidate/root row count mismatch")
require(set(inputs) == set(decisions) == set(independent), "packet/independent ID sets differ")
require(set(root_by_id) <= set(independent), "root row missing from independent ledger")
require(manifest["headCommit"] == BASE and manifest["tree"] == BASE_TREE and manifest["sourceSubtreeTree"] == SOURCE_TREE, "packet review pins differ")
require(git("rev-parse", "HEAD") == BASE, "worktree is not at exact reviewed PR head")
require(git("rev-parse", "HEAD^{tree}") == BASE_TREE, "review tree changed")
require(git("rev-parse", "HEAD:src/web/src") == SOURCE_TREE, "source/caller subtree changed")
require(not git("diff", "--name-only", "HEAD", "--"), "tracked files changed before application")

pr = json.loads(subprocess.check_output([
    "gh", "pr", "view", "409", "--repo", "snapetech-org/slskdN",
    "--json", "state,isDraft,mergeStateStatus,headRefOid,headRefName",
], text=True))
require(pr == {
    "headRefName": "codex/slskdn-oidc-tooltip-localization-20261030",
    "headRefOid": BASE,
    "isDraft": True,
    "mergeStateStatus": "CLEAN",
    "state": "OPEN",
}, f"live PR state/head changed: {pr}")
remote_rows = subprocess.check_output(["git", "-C", str(REPO), "ls-remote", "origin", REMOTE_REF], text=True).splitlines()
remote_head = remote_rows[0].split()[0] if remote_rows else ""
require(remote_head == BASE, f"remote PR branch moved: {remote_head}")

root_counts = collections.Counter(row["rootDisposition"] for row in root_rows)
require(root_counts == {"accept": 32, "refine": 1, "keep-current": 1}, f"unexpected root dispositions: {root_counts}")
require(set(candidates) == {row["id"] for row in root_rows if row["rootDisposition"] != "keep-current"}, "root correction IDs differ from packet candidates")
root_sha = sha((ROOT_REVIEW / "root-crossreview.jsonl").read_bytes())
independent_sha = sha((INDEPENDENT / "independent-crossreview-window34.jsonl").read_bytes())
source_calls = {}
catalogs: dict[str, dict] = {}
catalog_raw: dict[str, bytes] = {}
catalog_paths = {f"src/web/public/locales/{locale}.json" for locale in LOCALES}
for locale in LOCALES:
    path = f"src/web/public/locales/{locale}.json"
    raw = blob(BASE, path)
    require(sha(raw) == manifest["currentCatalogFileSha256"][locale], f"catalog base hash mismatch: {locale}")
    catalog_raw[locale] = raw
    catalogs[locale] = json.loads(raw.decode("utf-8"))
    require(len(catalogs[locale]) == manifest["catalogKeyCounts"][locale], f"catalog key count mismatch: {locale}")

placeholder_re = re.compile(r"\{[^{}]+\}")
plan: list[dict] = []
for ident, row in root_by_id.items():
    source = inputs[ident]
    independent_row = independent[ident]
    decision = decisions[ident]
    require(row["currentPrHead"] == BASE and row["currentPrTree"] == BASE_TREE, f"root git pin mismatch: {ident}")
    require(row["currentSourceSubtreeTree"] == SOURCE_TREE, f"root source subtree pin mismatch: {ident}")
    require(row["source"] == source["source"] == independent_row["source"], f"source value mismatch: {ident}")
    require(row["sourceSha256"] == source["sourceSha256"] == independent_row["sourceSha256"] == sha(row["source"]), f"source hash mismatch: {ident}")
    require(row["currentTarget"] == source["target"] == independent_row["currentTarget"], f"old target mismatch: {ident}")
    require(row["currentTargetSha256"] == source["targetSha256"] == independent_row["currentTargetSha256"] == sha(row["currentTarget"]), f"old target hash mismatch: {ident}")
    require(row["rootFinalTarget"] == independent_row["finalTarget"], f"cross-review target mismatch: {ident}")
    require(row["rootFinalTargetSha256"] == independent_row["finalTargetSha256"] == sha(row["rootFinalTarget"]), f"final target hash mismatch: {ident}")
    require(row["sourceCallsites"] == source["sourceCallsites"] == independent_row["callerPins"], f"caller pin rows mismatch: {ident}")
    require(row["catalogPath"] == source["catalogPath"] and row["catalogKey"] == source["catalogKey"], f"catalog mapping mismatch: {ident}")
    locale = row["locale"]
    require(row["currentCatalogFileSha256"] == manifest["currentCatalogFileSha256"][locale], f"catalog hash pin mismatch: {ident}")
    require(catalogs[locale].get(row["catalogKey"]) == row["currentTarget"], f"exact current catalog value mismatch: {ident}")
    require(sha(row["source"]) == row["sourceSha256"], f"source SHA mismatch: {ident}")
    placeholders = collections.Counter(placeholder_re.findall(row["source"]))
    require(placeholders == collections.Counter(placeholder_re.findall(row["currentTarget"])), f"current placeholder mismatch: {ident}")
    require(placeholders == collections.Counter(placeholder_re.findall(row["rootFinalTarget"])), f"final placeholder mismatch: {ident}")
    for literal in independent_row.get("protectedLiterals", []):
        require(row["rootFinalTarget"].count(literal) == row["source"].count(literal), f"protected literal mismatch: {ident}/{literal}")
    for call in row["sourceCallsites"]:
        path = call["path"]
        if path not in source_calls:
            source_calls[path] = blob(BASE, path)
        caller_blob = source_calls[path]
        require(sha(caller_blob) == call["fileSha256"], f"caller file hash mismatch: {ident}/{path}")
        lines = caller_blob.decode("utf-8").splitlines()
        index = call["line"] - 1
        require(0 <= index < len(lines), f"caller line out of range: {ident}/{path}")
        line = lines[index].strip()
        require(line == call["lineText"] and sha(line) == call["lineTextSha256"], f"caller line mismatch: {ident}/{path}:{call['line']}")
    require(decision["sourceSha256"] == row["sourceSha256"] and decision["currentTargetSha256"] == row["currentTargetSha256"], f"packet decision hash mismatch: {ident}")
    if row["rootDisposition"] == "keep-current":
        require(row["rootFinalTarget"] == row["currentTarget"], f"keep-current row changes target: {ident}")
        require(independent_row["independentDisposition"] == "keep-current", f"independent keep-current mismatch: {ident}")
        continue
    require(row["rootDisposition"] in ("accept", "refine"), f"unsupported root disposition: {ident}")
    require(row["id"] in candidates, f"root correction is not in packet candidate set: {ident}")
    candidate = candidates[ident]
    require(candidate["sourceSha256"] == row["sourceSha256"] and candidate["currentTargetSha256"] == row["currentTargetSha256"], f"candidate hashes mismatch: {ident}")
    require(row["candidateTarget"] == candidate["proposedTarget"] and row["candidateTargetSha256"] == candidate["proposedTargetSha256"], f"candidate target mismatch: {ident}")
    plan.append({
        "id": ident,
        "locale": locale,
        "sourceId": row["sourceId"],
        "source": row["source"],
        "sourceSha256": row["sourceSha256"],
        "catalogPath": row["catalogPath"],
        "catalogKey": row["catalogKey"],
        "oldTarget": row["currentTarget"],
        "oldTargetSha256": row["currentTargetSha256"],
        "candidateTarget": row["candidateTarget"],
        "candidateTargetSha256": row["candidateTargetSha256"],
        "newTarget": row["rootFinalTarget"],
        "newTargetSha256": row["rootFinalTargetSha256"],
        "rootDisposition": row["rootDisposition"],
        "rootReason": row["rootReason"],
        "sourceCallsites": row["sourceCallsites"],
        "prBaseHead": BASE,
        "prBaseTree": BASE_TREE,
        "sourceSubtreeTree": SOURCE_TREE,
        "rootLedgerSha256": root_sha,
        "independentLedgerSha256": independent_sha,
    })

require(len(plan) == 33 and len({row["id"] for row in plan}) == 33, "expected 33 unique correction cells")
per_locale = collections.Counter(row["locale"] for row in plan)
for row in plan:
    locale = row["locale"]
    catalogs[locale][row["catalogKey"]] = row["newTarget"]
rendered: dict[str, bytes] = {}
for locale in sorted(per_locale):
    raw = (json.dumps(catalogs[locale], ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    require(raw != catalog_raw[locale], f"catalog unexpectedly unchanged: {locale}")
    rendered[locale] = raw

preflight = {
    "result": "READY_TO_APPLY",
    "window": 34,
    "pullRequest": 409,
    "reviewBaseHead": BASE,
    "reviewBaseTree": BASE_TREE,
    "reviewBaseSourceSubtreeTree": SOURCE_TREE,
    "remotePrBranch": "codex/slskdn-oidc-tooltip-localization-20261030",
    "livePrState": pr["state"],
    "livePrDraft": pr["isDraft"],
    "livePrMergeState": pr["mergeStateStatus"],
    "remoteHead": remote_head,
    "reviewPacketSha256": sha((PACKET / "review-input.jsonl").read_bytes()),
    "rootCrossReviewLedgerSha256": root_sha,
    "independentCrossReviewLedgerSha256": independent_sha,
    "rootRows": len(root_rows),
    "rootDispositions": dict(root_counts),
    "cellsToApply": len(plan),
    "catalogFilesToChange": len(per_locale),
    "cellsByLocale": dict(sorted(per_locale.items())),
    "callerFilesPinned": len(source_calls),
    "catalogFilesPinned": len(LOCALES),
    "allOldValuesAndHashesMatch": True,
    "allFinalHashesPlaceholdersAndProtectedLiteralsPass": True,
    "packetRootKeepCell": "fr:src_03c73a8121cec12f",
    "packetKeepRationale": "Adjacent Upload Slots and Download Slots controls use Emplacements d’envoi and Emplacements de téléchargement; retain the established transfer-slot term.",
    "trackedChangesBeforeApplication": 0,
    "nativeSpeakerApproved": False,
    "testsBuildScansCiRun": False,
    "workflowFilesChanged": False,
}
(HERE / "application-preflight-window34.json").write_text(json.dumps(preflight, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(HERE / "root-apply-plan-window34.jsonl").write_text(
    "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in plan), encoding="utf-8"
)

# No catalog is written until every PR, ledger, source, caller, old-value, and final-value check passes.
for locale, raw in rendered.items():
    (REPO / f"src/web/public/locales/{locale}.json").write_bytes(raw)

print(json.dumps({
    "result": "APPLIED_IN_WORKTREE",
    "baseHead": BASE,
    "cells": len(plan),
    "localeFiles": len(per_locale),
    "cellsByLocale": dict(sorted(per_locale.items())),
    "rootLedgerSha256": root_sha,
    "independentLedgerSha256": independent_sha,
    "callerFilesPinned": len(source_calls),
}, ensure_ascii=False, indent=2))
