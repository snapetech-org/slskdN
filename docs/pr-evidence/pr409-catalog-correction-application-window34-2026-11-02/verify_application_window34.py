#!/usr/bin/env python3
"""Read-only exact-cell verifier for slskdN localization application W34."""
from __future__ import annotations

import argparse
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


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def require(ok: bool, message: str) -> None:
    if not ok:
        raise SystemExit(f"FAIL: {message}")


def blob(commit: str, path: str) -> bytes:
    return git("show", f"{commit}:{path}", raw=True)


def verify_sums(directory: Path) -> None:
    sums = directory / "SHA256SUMS.txt"
    require(sums.is_file(), f"missing evidence checksum file: {sums}")
    result = subprocess.run(["sha256sum", "-c", "SHA256SUMS.txt"], cwd=directory, capture_output=True, text=True)
    require(result.returncode == 0, f"evidence checksums failed in {directory}: {result.stderr or result.stdout}")


parser = argparse.ArgumentParser()
parser.add_argument("--record-manifest", action="store_true", help="record catalog commit and result hashes after catalog-only commit")
parser.add_argument("--write-report", action="store_true", help="write post-apply verification snapshot")
args = parser.parse_args()

plan = jsonl(HERE / "root-apply-plan-window34.jsonl")
applied = jsonl(HERE / "applied-corrections-window34.jsonl")
root_rows = jsonl(ROOT_REVIEW / "root-crossreview.jsonl")
independent_rows = jsonl(INDEPENDENT / "independent-crossreview-window34.jsonl")
inputs = jsonl(PACKET / "review-input.jsonl")
independent_summary = json.loads((INDEPENDENT / "independent-crossreview-summary.json").read_text(encoding="utf-8"))
review_preflight = json.loads((INDEPENDENT / "preflight-report.json").read_text(encoding="utf-8"))
for evidence_dir in (MANUAL, PACKET, INDEPENDENT, ROOT_REVIEW):
    verify_sums(evidence_dir)
if (HERE / "SHA256SUMS.txt").is_file():
    verify_sums(HERE)
manifest_path = HERE / "application-manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
require(len(plan) == len(applied) == 33 and len({row["id"] for row in plan}) == 33, "expected 33 unique applied targets")
by_root = {row["id"]: row for row in root_rows}
by_independent = {row["id"]: row for row in independent_rows}
by_input = {row["id"]: row for row in inputs}
plan_by_id = {row["id"]: row for row in plan}
applied_by_id = {row["id"]: row for row in applied}
require(set(plan_by_id) == set(applied_by_id), "plan/applied ID sets differ")
require(len(by_root) == 34 and len(by_independent) == 274 and len(by_input) == 274, "review evidence row count mismatch")
root_sha = sha((ROOT_REVIEW / "root-crossreview.jsonl").read_bytes())
independent_sha = sha((INDEPENDENT / "independent-crossreview-window34.jsonl").read_bytes())
require(independent_summary["ledgerSha256"] == independent_sha, "independent summary ledger SHA")
require((review_preflight["result"], review_preflight["prHead"], review_preflight["prTree"], review_preflight["sourceSubtreeTree"]) == ("PASS", BASE, BASE_TREE, SOURCE_TREE), "independent packet preflight pin")
require(review_preflight["exactCellOverlap"] == 0 and review_preflight["sourceKeyOverlap"] == 0 and review_preflight["appliedCorrectionRows"] == 1340, "prior-window overlap preflight")
require(review_preflight["formalOverlapClaimedZero"] and not review_preflight["formalRawRowsPresent"], "formal-overlap limitation differs")
independent_counts = collections.Counter(row["independentDisposition"] for row in independent_rows)
require(independent_counts == {"keep-current": 241, "accept-proposed": 32, "refine-proposed": 1}, f"independent disposition counts: {independent_counts}")
placeholder_re = re.compile(r"\{[^{}]+\}")
for ident, source in by_input.items():
    reviewed = by_independent[ident]
    require((reviewed["source"], reviewed["sourceSha256"]) == (source["source"], source["sourceSha256"]), f"independent source pin: {ident}")
    require((reviewed["currentTarget"], reviewed["currentTargetSha256"]) == (source["target"], source["targetSha256"]), f"independent current target pin: {ident}")
    require(reviewed["callerPins"] == source["sourceCallsites"], f"independent caller pin: {ident}")
    require(sha(reviewed["finalTarget"]) == reviewed["finalTargetSha256"], f"independent final target hash: {ident}")
    placeholders = collections.Counter(placeholder_re.findall(source["source"]))
    require(placeholders == collections.Counter(reviewed["placeholders"]) == collections.Counter(placeholder_re.findall(reviewed["finalTarget"])), f"independent placeholder pin: {ident}")
    for literal in source.get("protectedLiterals", []):
        require(source["source"].count(literal) == reviewed["finalTarget"].count(literal), f"independent protected literal: {ident}/{literal}")
    if reviewed["independentDisposition"] == "keep-current":
        require(reviewed["finalTarget"] == source["target"], f"independent keep changed value: {ident}")
    else:
        require(ident in by_root, f"independent correction lacks root final row: {ident}")
        require(reviewed["finalTarget"] == by_root[ident]["rootFinalTarget"], f"independent/root disagreement: {ident}")
fr_catalog_at_base = json.loads(blob(BASE, "src/web/public/locales/fr.json").decode("utf-8"))
french_keep = by_root["fr:src_03c73a8121cec12f"]
require(french_keep["rootDisposition"] == "keep-current" and french_keep["rootFinalTarget"] == french_keep["currentTarget"], "French transfer-policy row is not retained unchanged")
require(fr_catalog_at_base.get("Upload Slots") == "Emplacements d’envoi", "French Upload Slots sibling terminology changed")
require(fr_catalog_at_base.get("Download Slots") == "Emplacements de téléchargement", "French Download Slots sibling terminology changed")
per_locale = collections.Counter(row["locale"] for row in plan)
keys_by_locale: dict[str, set[str]] = collections.defaultdict(set)
for row in plan:
    ident = row["id"]
    root = by_root[ident]
    independent = by_independent[ident]
    source = by_input[ident]
    actual = applied_by_id[ident]
    require(root["rootDisposition"] in ("accept", "refine"), f"non-correction in plan: {ident}")
    require(root["rootFinalTarget"] == row["newTarget"] == actual["appliedTarget"], f"final target mismatch: {ident}")
    require(root["rootFinalTargetSha256"] == row["newTargetSha256"] == actual["appliedTargetSha256"] == sha(row["newTarget"]), f"final hash mismatch: {ident}")
    require(root["currentTarget"] == row["oldTarget"] == actual["currentTarget"], f"old target mismatch: {ident}")
    require(root["currentTargetSha256"] == row["oldTargetSha256"] == actual["currentTargetSha256"] == sha(row["oldTarget"]), f"old hash mismatch: {ident}")
    require(independent["finalTarget"] == row["newTarget"] and independent["finalTargetSha256"] == row["newTargetSha256"], f"cross-review mismatch: {ident}")
    require(source["source"] == row["source"] and source["sourceSha256"] == row["sourceSha256"] == sha(row["source"]), f"source mismatch: {ident}")
    require(root["sourceCallsites"] == row["sourceCallsites"], f"caller pin mismatch: {ident}")
    require((row["rootLedgerSha256"], row["independentLedgerSha256"]) == (root_sha, independent_sha), f"ledger checksum pin mismatch: {ident}")
    keys_by_locale[row["locale"]].add(row["catalogKey"])

expected_catalog_paths = {f"src/web/public/locales/{locale}.json" for locale in per_locale}
all_catalog_hashes: dict[str, str] = {}
changed_by_locale: dict[str, list[str]] = {}
placeholder_re = re.compile(r"\{[^{}]+\}")
for locale in LOCALES:
    rel = f"src/web/public/locales/{locale}.json"
    base_data = json.loads(blob(BASE, rel).decode("utf-8"))
    current_raw = (REPO / rel).read_bytes()
    current_data = json.loads(current_raw.decode("utf-8"))
    require(set(base_data) == set(current_data), f"catalog key parity changed: {locale}")
    require(len(current_data) == len(base_data) == 6169, f"catalog key count changed: {locale}")
    changed = {key for key in base_data if base_data[key] != current_data[key]}
    expected = keys_by_locale.get(locale, set())
    require(changed == expected, f"unexpected changed keys in {locale}: {sorted(changed ^ expected)}")
    for row in (item for item in plan if item["locale"] == locale):
        require(base_data.get(row["catalogKey"]) == row["oldTarget"], f"base target mismatch: {row['id']}")
        require(current_data.get(row["catalogKey"]) == row["newTarget"], f"applied target mismatch: {row['id']}")
        source = row["source"]
        current = row["oldTarget"]
        final = row["newTarget"]
        require(collections.Counter(placeholder_re.findall(source)) == collections.Counter(placeholder_re.findall(current)), f"old placeholder mismatch: {row['id']}")
        require(collections.Counter(placeholder_re.findall(source)) == collections.Counter(placeholder_re.findall(final)), f"new placeholder mismatch: {row['id']}")
        for literal in by_independent[row["id"]].get("protectedLiterals", []):
            require(source.count(literal) == final.count(literal), f"protected literal mismatch: {row['id']}/{literal}")
    if changed:
        changed_by_locale[locale] = sorted(changed)
    all_catalog_hashes[locale] = sha(current_raw)
require(sum(len(keys) for keys in changed_by_locale.values()) == 33 and len(changed_by_locale) == 11, "catalog changed-cell/file totals")
require(git("rev-parse", "HEAD:src/web/src") == SOURCE_TREE, "source/caller subtree changed")
workflow_paths = git("diff", "--name-only", BASE, "HEAD", "--", ".github/workflows").splitlines()
require(not workflow_paths, f"workflow paths changed: {workflow_paths}")
all_changed_paths = set(git("diff", "--name-only", BASE, "HEAD").splitlines())
allowed_paths = expected_catalog_paths | {"docs/CHANGELOG.md"}
for prefix in (
    "docs/pr-evidence/pr409-catalog-correction-application-window34-2026-11-02/",
    "docs/pr-evidence/pr409-manual-semantic-review-2026-11-01/window34/",
):
    allowed_paths |= {path for path in all_changed_paths if path.startswith(prefix)}
require(all_changed_paths <= allowed_paths, f"out-of-scope changed paths: {sorted(all_changed_paths - allowed_paths)}")

if manifest is None and args.record_manifest:
    catalog_commit = git("rev-parse", "HEAD")
    require(git("rev-parse", f"{catalog_commit}^") == BASE, "catalog commit is not a direct child of review head")
    commit_paths = set(git("diff-tree", "--no-commit-id", "--name-only", "-r", catalog_commit).splitlines())
    require(commit_paths == expected_catalog_paths, f"catalog commit path set mismatch: {sorted(commit_paths ^ expected_catalog_paths)}")
    manifest = {
        "schemaVersion": 1,
        "artifactKind": "slskdN W34 exact localization correction application",
        "pullRequest": 409,
        "reviewBaseHead": BASE,
        "reviewBaseTree": BASE_TREE,
        "reviewBaseSourceSubtreeTree": SOURCE_TREE,
        "remotePrBranch": "codex/slskdn-oidc-tooltip-localization-20261030",
        "catalogCommit": catalog_commit,
        "catalogCommitTree": git("rev-parse", f"{catalog_commit}^{{tree}}"),
        "reviewInputSha256": sha((PACKET / "review-input.jsonl").read_bytes()),
        "reviewDecisionSha256": sha((PACKET / "review-decisions.jsonl").read_bytes()),
        "candidatePlanSha256": sha((PACKET / "crossreview-plan.jsonl").read_bytes()),
        "independentSummarySha256": sha((INDEPENDENT / "independent-crossreview-summary.json").read_bytes()),
        "independentPreflightSha256": sha((INDEPENDENT / "preflight-report.json").read_bytes()),
        "manualReviewBundleChecksumsSha256": sha((MANUAL / "SHA256SUMS.txt").read_bytes()),
        "reviewPacketChecksumsSha256": sha((PACKET / "SHA256SUMS.txt").read_bytes()),
        "independentReviewChecksumsSha256": sha((INDEPENDENT / "SHA256SUMS.txt").read_bytes()),
        "rootReviewChecksumsSha256": sha((ROOT_REVIEW / "SHA256SUMS.txt").read_bytes()),
        "rootCrossReviewLedgerSha256": root_sha,
        "independentCrossReviewLedgerSha256": independent_sha,
        "rootApplyPlanSha256": sha((HERE / "root-apply-plan-window34.jsonl").read_bytes()),
        "appliedLedgerSha256": sha((HERE / "applied-corrections-window34.jsonl").read_bytes()),
        "rootDispositionCounts": {"accept": 32, "refine": 1, "keep-current": 1},
        "independentDispositionCounts": dict(independent_counts),
        "reviewedCells": 274,
        "reviewedSourceKeys": 25,
        "packetCallerLineReferences": 514,
        "appliedTargets": 33,
        "uniqueAppliedSourceKeysThisWindow": len({row["sourceId"] for row in plan}),
        "catalogFilesChanged": {
            locale: {
                "baseSha256": sha(blob(BASE, f"src/web/public/locales/{locale}.json")),
                "resultSha256": all_catalog_hashes[locale],
                "changedKeys": changed_by_locale[locale],
                "changedCellCount": len(changed_by_locale[locale]),
            }
            for locale in sorted(changed_by_locale)
        },
        "nativeSpeakerApproval": False,
        "testsBuildScansCiRun": False,
        "workflowChanges": False,
        "releaseTagMerge": False,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if manifest is not None:
    require(manifest["reviewBaseHead"] == BASE and manifest["reviewBaseTree"] == BASE_TREE, "application manifest base pins")
    require(manifest["catalogCommit"] == git("rev-parse", manifest["catalogCommit"]), "catalog commit missing")
    require(git("rev-parse", f"{manifest['catalogCommit']}^") == BASE, "catalog commit parent mismatch")
    require(git("rev-parse", f"{manifest['catalogCommit']}^{{tree}}") == manifest["catalogCommitTree"], "catalog commit tree mismatch")
    require(manifest["appliedLedgerSha256"] == sha((HERE / "applied-corrections-window34.jsonl").read_bytes()), "applied ledger SHA mismatch")

report = {
    "result": "PASS",
    "window": 34,
    "verifiedAtHead": git("rev-parse", "HEAD"),
    "verifiedAtTree": git("rev-parse", "HEAD^{tree}"),
    "reviewBaseHead": BASE,
    "reviewBaseTree": BASE_TREE,
    "sourceSubtreeTree": SOURCE_TREE,
    "catalogCommit": manifest["catalogCommit"] if manifest else None,
    "rootApprovedCorrections": len(plan),
    "rootAcceptedAsProposed": 32,
    "rootRefined": 1,
    "rootKeepCurrent": 1,
    "independentReviewRows": len(independent_rows),
    "independentKeptRows": independent_counts["keep-current"],
    "catalogFilesChanged": len(changed_by_locale),
    "changedCells": sum(len(keys) for keys in changed_by_locale.values()),
    "changedKeysByLocale": {locale: len(keys) for locale, keys in sorted(changed_by_locale.items())},
    "localeKeyCounts": {locale: 6169 for locale in LOCALES},
    "catalogFileSha256": all_catalog_hashes,
    "placeholdersAndProtectedLiterals": "passed for all 33 applied cells",
    "sourceCallerAndCatalogPins": "passed at review base",
    "workflowChanges": len(workflow_paths),
    "changedPaths": len(all_changed_paths),
    "changedPathsWithinCatalogChangelogAndWindow34Evidence": True,
    "testsBuildScansCiRun": False,
    "nativeSpeakerApproved": False,
}
if args.write_report:
    report_path = HERE / "post-apply-verification-window34.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
