#!/usr/bin/env python3
"""Apply ratified slskdN W53 locale edits at one pinned PR head."""

from __future__ import annotations

import collections
import hashlib
import json
import subprocess
import sys
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent.parent
REVIEW = EVIDENCE / "review"
INPUT = REVIEW / "input"
BASE_HEAD = "6d5723e244338a550e3dfa5182a45857156467a7"
BASE_TREE = "8435576260e9aa760609be6a28001b2bb38b8c11"
EXPECTED_ROWS = 300
EXPECTED_CHANGES = 82
EXPECTED_KEY_COUNT = 6176
EXPECTED_ORDER_HASH = "3ca04c40ebfed00b93fcd143109fc9d85da941cec30b6cb93f52e431498df6a7"


def fail(message: str) -> None:
    raise SystemExit(f"REFUSED: {message}")


def sha(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=EVIDENCE.parents[3], text=True).strip()


def main() -> None:
    if sys.argv[1:] != ["--apply"]:
        fail("run only with --apply from the repository worktree")

    repo = EVIDENCE.parents[3]
    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    if head != BASE_HEAD or tree != BASE_TREE:
        fail(f"expected exact base {BASE_HEAD}/{BASE_TREE}, found {head}/{tree}")

    input_rows = read_jsonl(INPUT / "source-current-cells.jsonl")
    ratified_path = REVIEW / "cross-review" / "ratified.jsonl"
    ratified_rows = read_jsonl(ratified_path)
    guards_path = REVIEW / "cross-review" / "independent-hash-audit" / "ratified-hash-guards.jsonl"
    guards = read_jsonl(guards_path)
    structures = read_jsonl(INPUT / "catalog-structure.jsonl")
    cross_summary = json.loads((REVIEW / "cross-review" / "summary.json").read_text(encoding="utf-8"))
    guard_summary = json.loads((REVIEW / "cross-review" / "independent-hash-audit" / "summary.json").read_text(encoding="utf-8"))
    pinned_artifacts = {
        REVIEW / "input" / "PACKET-SHA256SUMS.txt": cross_summary["inputManifestSha256"],
        REVIEW / "primary" / "review-decisions.jsonl": cross_summary["primaryReviewLedgerSha256"],
        REVIEW / "root-blind" / "ledger.jsonl": cross_summary["independentLedgerSha256"],
        ratified_path: cross_summary["ratifiedLedgerSha256"],
        guards_path: guard_summary["ratifiedHashGuardsSha256"],
    }
    for path, expected_hash in pinned_artifacts.items():
        if sha(path.read_bytes()) != expected_hash:
            fail(f"review artifact hash changed: {path.relative_to(REVIEW)}")
    if not (len(input_rows) == len(ratified_rows) == len(guards) == EXPECTED_ROWS):
        fail("input, ratified ledger, or independent hash-guard row count changed")

    inputs = {(r["sourceId"], r["locale"]): r for r in input_rows}
    ratified = {(r["sourceId"], r["locale"]): r for r in ratified_rows}
    guard_map = {(r["sourceId"], r["locale"]): r for r in guards}
    if len(inputs) != EXPECTED_ROWS or set(inputs) != set(ratified) or set(inputs) != set(guard_map):
        fail("duplicate or mismatched source/locale rows")

    disposition_counts = collections.Counter()
    changes_by_locale = collections.Counter()
    plans = []
    readback_rows = []
    catalogs: dict[str, dict] = {}
    catalog_bytes: dict[str, bytes] = {}
    catalog_structures = {r["locale"]: r for r in structures}
    if len(catalog_structures) != 12:
        fail("expected exactly 12 direct locale catalogs")

    for locale, meta in catalog_structures.items():
        rel = meta["catalogPath"]
        path = repo / rel
        raw = path.read_bytes()
        if sha(raw) != meta["sha256"]:
            fail(f"catalog byte hash changed before apply: {locale}")
        blob = git("hash-object", rel)
        if blob != meta["gitBlob"]:
            fail(f"catalog Git blob changed before apply: {locale}")
        catalog = json.loads(raw)
        if len(catalog) != EXPECTED_KEY_COUNT or any(not isinstance(v, str) for v in catalog.values()):
            fail(f"catalog shape changed: {locale}")
        ordered_hash = sha("\n".join(catalog.keys()) + "\n")
        if ordered_hash != EXPECTED_ORDER_HASH or ordered_hash != meta["orderedKeySha256"]:
            fail(f"catalog key set/order changed: {locale}")
        if (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode("utf-8") != raw:
            fail(f"catalog serialization differs from the pinned format: {locale}")
        catalogs[locale] = catalog
        catalog_bytes[locale] = raw

    for key in sorted(inputs, key=lambda pair: (inputs[pair]["continuationRank"], pair[1])):
        source = inputs[key]
        final = ratified[key]
        guard = guard_map[key]
        meta = catalog_structures[source["locale"]]
        if source["catalogPath"] != meta["catalogPath"]:
            fail(f"catalog path mismatch for {key}")
        if source["catalogFileSha256"] != meta["sha256"] or source["catalogGitBlob"] != meta["gitBlob"]:
            fail(f"catalog file pin mismatch for {key}")
        if guard["sourceSha256"] != source["sourceSha256"] or guard["currentTargetSha256"] != source["currentTargetSha256"]:
            fail(f"independent source/current hash mismatch for {key}")
        if guard["numericTokens"] != source["sourceNumericTokens"]:
            fail(f"independent source numeric-token mismatch for {key}")
        if source["sourceSha256"] != sha(source["source"]):
            fail(f"source text hash mismatch for {key}")
        if source["sourceSha256"] != final["sourceSha256"]:
            fail(f"source pin mismatch between input and ratification for {key}")
        if source["currentTarget"] != final["currentTarget"] or source["currentTargetSha256"] != final["currentTargetSha256"]:
            fail(f"current target pin mismatch for {key}")
        if source["currentTargetSha256"] != sha(source["currentTarget"]):
            fail(f"current target hash mismatch for {key}")
        if source["callerContextSha256"] != final["callerContextSha256"] or source["callerContextSha256"] != guard["callerContextSha256"]:
            fail(f"caller-context pin mismatch for {key}")
        if source["placeholderEvidence"].get("matches") is not True or source["markupEvidence"].get("matches") is not True:
            fail(f"input placeholder or markup check failed for {key}")
        if final["placeholderEvidence"].get("matches") is not True or final["markupEvidence"].get("matches") is not True:
            fail(f"ratified placeholder or markup check failed for {key}")
        if guard["placeholderMatch"] is not True or guard["numericTokensPreserved"] is not True or guard["protectedLiteralsPreserved"] is not True:
            fail(f"independent structural guard failed for {key}")
        target = final["finalTarget"]
        target_hash = sha(target)
        if guard["ratifiedTarget"] != target or guard["ratifiedTargetSha256"] != target_hash:
            fail(f"independent final-target hash guard mismatch for {key}")
        if final["finalDisposition"] != guard["ratifiedDisposition"]:
            fail(f"independent disposition mismatch for {key}")
        if catalogs[source["locale"]].get(source["source"]) != source["currentTarget"]:
            fail(f"catalog source key/current value mismatch for {key}")

        disposition = final["finalDisposition"]
        disposition_counts[disposition] += 1
        changed = disposition in {"correction", "refinement"}
        actual_before = catalogs[source["locale"]][source["source"]]
        if changed:
            if target == actual_before:
                fail(f"changed disposition is a no-op for {key}")
            plan = {
                "continuationRank": source["continuationRank"],
                "sourceId": source["sourceId"],
                "source": source["source"],
                "locale": source["locale"],
                "catalogPath": source["catalogPath"],
                "currentTargetSha256": source["currentTargetSha256"],
                "finalDisposition": disposition,
                "finalTarget": target,
                "finalTargetSha256": target_hash,
                "callerContextSha256": source["callerContextSha256"],
            }
            plans.append(plan)
            changes_by_locale[source["locale"]] += 1
            catalogs[source["locale"]][source["source"]] = target
        elif target != actual_before:
            fail(f"non-change disposition unexpectedly differs from current for {key}")

        readback_rows.append({
            "continuationRank": source["continuationRank"],
            "sourceId": source["sourceId"],
            "locale": source["locale"],
            "catalogPath": source["catalogPath"],
            "disposition": disposition,
            "changed": changed,
            "currentTargetSha256": source["currentTargetSha256"],
            "finalTargetSha256": target_hash,
            "callerContextSha256": source["callerContextSha256"],
            "readbackTargetSha256": sha(catalogs[source["locale"]][source["source"]]),
            "readbackMatches": catalogs[source["locale"]][source["source"]] == target,
        })

    if len(plans) != EXPECTED_CHANGES:
        fail(f"expected {EXPECTED_CHANGES} changes, found {len(plans)}")
    if disposition_counts != {"accept-current": 194, "correction": 68, "refinement": 14, "hold-context": 24}:
        fail(f"ratified disposition counts changed: {dict(disposition_counts)}")
    if sum(changes_by_locale.values()) != EXPECTED_CHANGES:
        fail("per-locale change count does not sum to the expected total")

    output_bytes = {}
    for locale, catalog in catalogs.items():
        output_bytes[locale] = (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    for locale, meta in catalog_structures.items():
        path = repo / meta["catalogPath"]
        if path.read_bytes() != catalog_bytes[locale]:
            fail(f"catalog changed during preflight: {locale}")

    for locale, meta in catalog_structures.items():
        (repo / meta["catalogPath"]).write_bytes(output_bytes[locale])

    for row in readback_rows:
        source = inputs[(row["sourceId"], row["locale"])]
        catalog = json.loads((repo / row["catalogPath"]).read_text(encoding="utf-8"))
        actual = catalog[source["source"]]
        if actual != ratified[(row["sourceId"], row["locale"])]["finalTarget"]:
            fail(f"post-write readback failed for {(row['sourceId'], row['locale'])}")
        row["readbackTargetSha256"] = sha(actual)
        row["readbackMatches"] = True

    application_dir = EVIDENCE / "application"
    application_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(application_dir / "apply-plan.jsonl", plans)
    write_jsonl(application_dir / "readback.jsonl", readback_rows)
    summary = {
        "repository": "snapetech-org/slskdN",
        "pullRequest": 409,
        "window": "W53",
        "baseHead": BASE_HEAD,
        "baseTree": BASE_TREE,
        "reviewedCells": EXPECTED_ROWS,
        "changedCells": len(plans),
        "changedByLocale": dict(sorted(changes_by_locale.items())),
        "finalDispositions": dict(sorted(disposition_counts.items())),
        "noCallerHolds": sum(r["disposition"] == "hold-context" for r in readback_rows),
        "catalogs": {
            locale: {
                "path": meta["catalogPath"],
                "entryCount": EXPECTED_KEY_COUNT,
                "orderedKeySha256": EXPECTED_ORDER_HASH,
                "beforeSha256": meta["sha256"],
                "afterSha256": sha(output_bytes[locale]),
            }
            for locale, meta in sorted(catalog_structures.items())
        },
        "readbackRows": len(readback_rows),
        "readbackMismatches": sum(not r["readbackMatches"] for r in readback_rows),
        "nativeSpeakerApproval": False,
        "headedBrowserAcceptance": False,
        "testsBuildsScansOrCiRun": False,
        "workflowsChanged": False,
    }
    (application_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
