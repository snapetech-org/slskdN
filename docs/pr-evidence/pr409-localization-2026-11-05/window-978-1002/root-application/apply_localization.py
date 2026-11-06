#!/usr/bin/env python3
"""Guarded, exact-hash application and readback for slskdN W978-W1002."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
WINDOW = HERE.parent
REPO = HERE.parents[4]
CROSS = WINDOW / "cross-review" / "cross-review-ledger.jsonl"
ROOT_OPINION = WINDOW / "root-adjudication" / "root-adjudication-opinion.jsonl"
PLAN = HERE / "exact-hash-apply-plan.jsonl"
FINAL_LEDGER = HERE / "final-root-review-ledger.jsonl"
FINAL_ADJUDICATION = HERE / "root-final-adjudication.jsonl"
PINS = HERE / "input-pins.json"
SUMMARY = HERE / "application-summary.json"
READBACK = HERE / "final-head-readback.jsonl"


def sha(text: str | bytes) -> str:
    payload = text.encode("utf-8") if isinstance(text, str) else text
    return hashlib.sha256(payload).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def catalog_keys(obj: Any) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            found.append(key)
            found.extend(catalog_keys(value))
    elif isinstance(obj, list):
        for value in obj:
            found.extend(catalog_keys(value))
    return found


def find_source_key(obj: Any, source: str) -> list[tuple[dict[str, Any], str]]:
    found: list[tuple[dict[str, Any], str]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == source:
                found.append((obj, key))
            found.extend(find_source_key(value, source))
    elif isinstance(obj, list):
        for value in obj:
            found.extend(find_source_key(value, source))
    return found


def git_show(head: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{head}:{path}"], cwd=REPO)


def write_atomic(path: Path, payload: bytes) -> None:
    temp = path.with_name(path.name + ".localization-tmp")
    temp.write_bytes(payload)
    temp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="apply the exact-hash plan at the pinned input head")
    parser.add_argument("--verify-only", action="store_true", help="compare current catalogs against pinned base plus the recorded plan")
    args = parser.parse_args()

    input_rows = read_jsonl(CROSS)
    opinion_rows = read_jsonl(ROOT_OPINION)
    if len(input_rows) != 300 or len(opinion_rows) != 64:
        raise SystemExit("expected 300 cross-review rows and 64 root-adjudication opinions")

    head = input_rows[0]["exactHead"]
    tree = input_rows[0]["exactTree"]
    if any(row["exactHead"] != head or row["exactTree"] != tree for row in input_rows + opinion_rows):
        raise SystemExit("input packets are not pinned to one exact product head/tree")
    if any(row["rootAdjudicationPerformed"] for row in opinion_rows):
        raise SystemExit("advisory opinion input was modified; preserve its original status")

    if not args.verify_only:
        current_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
        if current_head != head:
            raise SystemExit(f"pre-apply HEAD mismatch: {current_head} != {head}")

    opinion_by_key = {(row["continuationRank"], row["locale"]): row for row in opinion_rows}
    cross_by_key = {(row["continuationRank"], row["locale"]): row for row in input_rows}
    if len(cross_by_key) != 300 or len(opinion_by_key) != 64:
        raise SystemExit("duplicate cell identity in input evidence")

    root_adjudications: list[dict[str, Any]] = []
    final_rows: list[dict[str, Any]] = []
    for row in input_rows:
        key = (row["continuationRank"], row["locale"])
        flagged = row["flagForRootAdjudication"]
        if flagged:
            opinion = opinion_by_key.pop(key, None)
            if opinion is None:
                raise SystemExit(f"missing root opinion for {key}")
            if (
                opinion["source"] != row["source"]
                or opinion["currentTarget"] != row["currentTarget"]
                or opinion["sourceSha256"] != row["sourceSha256"]
                or opinion["currentTargetSha256"] != row["currentTargetSha256"]
                or opinion["catalogPath"] != row["catalogPath"]
            ):
                raise SystemExit(f"root opinion binding mismatch for {key}")
            if opinion["recommendedDisposition"] != "correction" or not opinion["recommendedTarget"]:
                raise SystemExit(f"root recommendation is not an exact correction for {key}")
            token = opinion["recommendedTokenChecks"]
            rationale = opinion["localeSpecificRationale"]
            final_target = opinion["recommendedTarget"]
            final_basis = opinion["selectionBasis"]
            final_disposition = "correction"
            root_decision = {
                "continuationRank": row["continuationRank"],
                "remainingQueueRank": row["remainingQueueRank"],
                "locale": row["locale"],
                "sourceId": row["sourceId"],
                "source": row["source"],
                "sourceSha256": row["sourceSha256"],
                "currentTarget": row["currentTarget"],
                "currentTargetSha256": row["currentTargetSha256"],
                "catalogPath": row["catalogPath"],
                "finalDisposition": "correction",
                "finalTarget": final_target,
                "finalTargetSha256": sha(final_target),
                "advisorySelectionBasis": final_basis,
                "finalRationale": rationale,
                "selectedFrom": "independent root-adjudication opinion after manual review",
                "rootAdjudicationPerformed": True,
                "confidence": opinion["confidence"],
                "tokenChecks": token,
            }
            root_adjudications.append(root_decision)
        else:
            opinion = None
            final_disposition = row["independentDisposition"]
            if final_disposition == "correction":
                final_target = row["recommendedTarget"]
                final_basis = row["targetSelection"]
                rationale = row["independentRationale"]
                token = row["independentTokenChecks"]
            elif final_disposition == "accept-current":
                final_target = row["currentTarget"]
                final_basis = "cross-review accepted current value"
                rationale = row["independentRationale"]
                token = row["independentTokenChecks"]
            else:
                raise SystemExit(f"unsupported cross-review disposition {final_disposition} for {key}")
        if token["placeholders"]["matches"] is not True or token["markup"]["matches"] is not True:
            raise SystemExit(f"placeholder/markup mismatch for {key}")
        if token["numbers"]["sourcePreserved"] is not True or token["protectedLiterals"]["matches"] is not True:
            raise SystemExit(f"numeric/protected-literal mismatch for {key}")
        if sha(row["source"]) != row["sourceSha256"] or sha(row["currentTarget"]) != row["currentTargetSha256"]:
            raise SystemExit(f"source/current digest mismatch for {key}")
        if sha(final_target) != (opinion["recommendedTargetSha256"] if opinion else row["recommendedTargetSha256"] if final_disposition == "correction" else sha(row["currentTarget"])):
            raise SystemExit(f"final target digest mismatch for {key}")
        final_rows.append({
            "continuationRank": row["continuationRank"],
            "remainingQueueRank": row["remainingQueueRank"],
            "locale": row["locale"],
            "sourceId": row["sourceId"],
            "source": row["source"],
            "sourceSha256": row["sourceSha256"],
            "catalogPath": row["catalogPath"],
            "before": row["currentTarget"],
            "beforeSha256": row["currentTargetSha256"],
            "after": final_target,
            "afterSha256": sha(final_target),
            "disposition": final_disposition,
            "selectionBasis": final_basis,
            "rationale": rationale,
            "rootAdjudicationRequired": flagged,
            "rootAdjudicationPerformed": flagged,
            "protectedLiteralMismatchRepaired": row["baselineProtectedLiteralMismatch"],
            "tokenChecks": token,
        })
    if opinion_by_key:
        raise SystemExit(f"unmatched root opinions remain: {sorted(opinion_by_key)}")

    plan = [row for row in final_rows if row["disposition"] == "correction" and row["after"] != row["before"]]
    if len(plan) != 89 or len(root_adjudications) != 64:
        raise SystemExit(f"unexpected final edit/adjudication counts: {len(plan)}/{len(root_adjudications)}")
    if sum(row["protectedLiteralMismatchRepaired"] for row in plan) != 5:
        raise SystemExit("expected exactly five protected-literal baseline repairs")

    locales = sorted({row["locale"] for row in input_rows})
    if len(locales) != 12:
        raise SystemExit("expected twelve direct locales")

    pins = {
        "window": "W978-W1002",
        "continuationRankRange": [978, 1002],
        "remainingQueueRankRange": [878, 902],
        "inputHead": head,
        "inputTree": tree,
        "catalogCount": 12,
        "sourceCount": 25,
        "reviewedCellCount": 300,
        "rootAdjudicatedCellCount": 64,
        "exactHashEditCount": len(plan),
        "protectedLiteralRepairs": 5,
        "locales": locales,
        "reviewEvidence": {
            "candidateFree": "candidate-free/input",
            "primary": "primary-review",
            "blind": "blind-review",
            "crossReview": "cross-review",
            "rootAdvisory": "root-adjudication/root-adjudication-opinion.jsonl",
        },
        "exactHeadBinding": "all inputs at the same original product head/tree; product commit follows catalog application",
    }

    if args.verify_only:
        recorded_plan = read_jsonl(PLAN)
        recorded_final = read_jsonl(FINAL_LEDGER)
        if recorded_plan != plan or recorded_final != final_rows:
            raise SystemExit("recorded final plan/ledger differs from regenerated evidence")
        expected_by_path: dict[str, dict[str, Any]] = {}
        for change in plan:
            expected_by_path.setdefault(change["catalogPath"], {})[change["source"]] = change
        readback_rows = []
        for path, changes in expected_by_path.items():
            baseline_bytes = git_show(head, path)
            if sha(baseline_bytes) != next(row["catalogFileSha256"] for row in input_rows if row["catalogPath"] == path):
                raise SystemExit(f"baseline catalog digest mismatch for {path}")
            baseline = json.loads(baseline_bytes.decode("utf-8"))
            expected = copy.deepcopy(baseline)
            for source, change in changes.items():
                matches = find_source_key(expected, source)
                if len(matches) != 1:
                    raise SystemExit(f"expected one source key for {source!r} in {path}, found {len(matches)}")
                parent, key = matches[0]
                if parent[key] != change["before"]:
                    raise SystemExit(f"baseline value mismatch for {source!r} in {path}")
                parent[key] = change["after"]
            expected_bytes = (json.dumps(expected, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            actual_bytes = (REPO / path).read_bytes()
            if actual_bytes != expected_bytes:
                raise SystemExit(f"full-catalog readback mismatch for {path}")
            for cell in input_rows:
                if cell["catalogPath"] != path:
                    continue
                matches = find_source_key(expected, cell["source"])
                if len(matches) != 1:
                    raise SystemExit(f"expected one reviewed source key for {cell['source']!r} in {path}")
                value = matches[0][0][matches[0][1]]
                change = changes.get(cell["source"])
                expected_value = change["after"] if change else cell["currentTarget"]
                if value != expected_value:
                    raise SystemExit(f"reviewed cell mismatch for {cell['source']!r} in {path}")
                readback_rows.append({
                    "continuationRank": cell["continuationRank"],
                    "locale": cell["locale"],
                    "source": cell["source"],
                    "catalogPath": path,
                    "expectedValue": expected_value,
                    "actualValue": value,
                    "matches": value == expected_value,
                })
        if len(readback_rows) != 300:
            raise SystemExit(f"unexpected readback cell count: {len(readback_rows)}")
        write_jsonl(READBACK, readback_rows)
        summary = {
            **pins,
            "result": "PASS",
            "verifyMode": "full-catalog bytes regenerated from pinned parent plus 89 reviewed exact edits",
            "postCommitHead": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
            "fullCatalogReadbackCount": len(expected_by_path),
            "reviewedCellReadbackCount": len(readback_rows),
            "changedCells": len(plan),
            "unchangedReviewedCells": len(final_rows) - len(plan),
            "rootFinalDecisions": len(root_adjudications),
            "nonTargetContent": "byte-identical to pinned parent serialization outside the 89 exact source keys",
            "keyOrderPreserved": True,
            "catalogEntryCounts": {p: len(catalog_keys(json.loads(git_show(head, p).decode("utf-8")))) for p in sorted(expected_by_path)},
        }
        SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    # Preflight all 12 catalogs and all 300 reviewed cells before writing any.
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in input_rows:
        grouped.setdefault(row["catalogPath"], []).append(row)
    expected_catalogs = {}
    baseline_hashes = {}
    for path, rows in grouped.items():
        baseline_bytes = git_show(head, path)
        catalog_hash = sha(baseline_bytes)
        pinned_hash = rows[0]["catalogFileSha256"]
        if catalog_hash != pinned_hash:
            raise SystemExit(f"baseline catalog hash mismatch for {path}")
        baseline = json.loads(baseline_bytes.decode("utf-8"))
        if (json.dumps(baseline, ensure_ascii=False, indent=2) + "\n").encode("utf-8") != baseline_bytes:
            raise SystemExit(f"JSON serialization is not canonical two-space/UTF-8 form for {path}")
        expected = copy.deepcopy(baseline)
        for cell in rows:
            matches = find_source_key(expected, cell["source"])
            if len(matches) != 1:
                raise SystemExit(f"expected one source key for {cell['source']!r} in {path}, found {len(matches)}")
            parent, key = matches[0]
            if parent[key] != cell["currentTarget"]:
                raise SystemExit(f"current target mismatch for {cell['source']!r} in {path}")
        for change in [item for item in plan if item["catalogPath"] == path]:
            matches = find_source_key(expected, change["source"])
            parent, key = matches[0]
            if parent[key] != change["before"]:
                raise SystemExit(f"exact-hash guard failed for {change['source']!r} in {path}")
            parent[key] = change["after"]
        expected_catalogs[path] = expected
        baseline_hashes[path] = catalog_hash

    if not args.apply:
        raise SystemExit("preflight passed; rerun with --apply to write the catalogs")

    # Persist auditable plans before the first product-file write.
    write_jsonl(FINAL_LEDGER, final_rows)
    write_jsonl(FINAL_ADJUDICATION, root_adjudications)
    write_jsonl(PLAN, plan)
    PINS.write_text(json.dumps(pins, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    preflight = {
        **pins,
        "result": "PASS",
        "preApplyHead": head,
        "catalogsPreflighted": len(expected_catalogs),
        "reviewedCellsPreflighted": len(input_rows),
        "editsPreflighted": len(plan),
        "catalogFileSha256Before": baseline_hashes,
        "writeStartedAfterFullPreflight": True,
    }
    (HERE / "preflight.json").write_text(json.dumps(preflight, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for path, expected in expected_catalogs.items():
        payload = (json.dumps(expected, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        write_atomic(REPO / path, payload)
    print(json.dumps(preflight, ensure_ascii=False, indent=2))
    print("Catalogs written; run this script with --verify-only after committing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
