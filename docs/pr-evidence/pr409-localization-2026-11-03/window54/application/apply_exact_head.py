#!/usr/bin/env python3
"""Apply the ratified slskdN W54 catalog decisions at their exact PR head."""
from __future__ import annotations

import collections
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
EVIDENCE = ROOT / "docs/pr-evidence/pr409-localization-2026-11-03/window54"
INPUT = EVIDENCE / "review/input"
PRIMARY = EVIDENCE / "review/primary"
BLIND = EVIDENCE / "review/independent-blind"
CROSS = EVIDENCE / "review/cross-audit"
ROOT_REVIEW = EVIDENCE / "review/root-adjudication"
BASE_HEAD = "5812e90c3018f0a8b563bff2ba95b5fd19076908"
BASE_TREE = "632924177388e15b594976774d2d879a098e8a72"
EXPECTED_ROWS = 300
EXPECTED_CHANGES = 50
EXPECTED_KEY_COUNT = 6176
EXPECTED_ORDER_HASH = "3ca04c40ebfed00b93fcd143109fc9d85da941cec30b6cb93f52e431498df6a7"


def fail(message: str) -> None:
    raise SystemExit(f"REFUSED: {message}")


def sha(data: bytes | str) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def verify_sha_manifest(directory: Path, name: str) -> None:
    manifest = directory / name
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, rel = line.split(maxsplit=1)
        path = directory / rel.lstrip("*").strip()
        if not path.is_file() or sha(path.read_bytes()) != digest:
            fail(f"checksum mismatch: {path.relative_to(EVIDENCE)}")


def main() -> None:
    if sys.argv[1:] != ["--apply"]:
        fail("run only with --apply from the exact PR worktree")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip()
    if (head, tree) != (BASE_HEAD, BASE_TREE):
        fail(f"expected exact base {BASE_HEAD}/{BASE_TREE}, found {head}/{tree}")

    for directory, manifest in ((INPUT, "PACKET-SHA256SUMS.txt"), (PRIMARY, "SHA256SUMS.txt"), (BLIND, "SHA256SUMS.txt"), (BLIND / "input", "PACKET-SHA256SUMS.txt"), (CROSS, "SHA256SUMS.txt")):
        verify_sha_manifest(directory, manifest)

    input_rows = read_jsonl(INPUT / "source-current-cells.jsonl")
    root_rows = read_jsonl(ROOT_REVIEW / "root-adjudication.jsonl")
    structures = read_jsonl(INPUT / "catalog-structure.jsonl")
    root_summary = json.loads((ROOT_REVIEW / "summary.json").read_text(encoding="utf-8"))
    if len(input_rows) != EXPECTED_ROWS or len(root_rows) != EXPECTED_ROWS or len(structures) != 12:
        fail("review row or catalog-pin count changed")
    if root_summary.get("baseHead") != BASE_HEAD or root_summary.get("baseTree") != BASE_TREE or root_summary.get("appliedCandidateCount") != EXPECTED_CHANGES:
        fail("root adjudication summary does not match this exact application")

    inputs = {(r["sourceId"], r["locale"]): r for r in input_rows}
    adjudicated = {(r["sourceId"], r["locale"]): r for r in root_rows}
    if len(inputs) != EXPECTED_ROWS or len(adjudicated) != EXPECTED_ROWS or set(inputs) != set(adjudicated):
        fail("duplicate or mismatched source/locale rows")

    catalog_meta = {r["locale"]: r for r in structures}
    if len(catalog_meta) != 12:
        fail("expected exactly twelve direct locale catalogs")
    catalogs: dict[str, dict] = {}
    original_bytes: dict[str, bytes] = {}
    for locale, meta in catalog_meta.items():
        path = ROOT / meta["catalogPath"]
        raw = path.read_bytes()
        if sha(raw) != meta["sha256"]:
            fail(f"catalog raw-byte hash changed before application: {locale}")
        blob = subprocess.check_output(["git", "hash-object", meta["catalogPath"]], cwd=ROOT, text=True).strip()
        if blob != meta["gitBlob"]:
            fail(f"catalog Git blob changed before application: {locale}")
        catalog = json.loads(raw)
        if len(catalog) != EXPECTED_KEY_COUNT or any(not isinstance(v, str) for v in catalog.values()):
            fail(f"catalog structure changed: {locale}")
        if sha("\n".join(catalog.keys()) + "\n") != EXPECTED_ORDER_HASH or sha("\n".join(catalog.keys()) + "\n") != meta["orderedKeySha256"]:
            fail(f"ordered key set changed: {locale}")
        if (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode("utf-8") != raw:
            fail(f"catalog serialization changed: {locale}")
        catalogs[locale] = catalog
        original_bytes[locale] = raw

    plans = []
    readback = []
    dispositions = collections.Counter()
    changes_by_locale = collections.Counter()
    final_catalogs = {locale: dict(catalog) for locale, catalog in catalogs.items()}
    for key in sorted(inputs, key=lambda pair: (inputs[pair]["continuationRank"], pair[1])):
        src = inputs[key]
        row = adjudicated[key]
        if row["sourceSha256"] != src["sourceSha256"] or row["currentTargetSha256"] != src["currentTargetSha256"] or row["callerContextSha256"] != src["callerContextSha256"]:
            fail(f"exact source/current/caller hash mismatch: {key}")
        if src["sourceSha256"] != sha(src["source"]) or src["currentTargetSha256"] != sha(src["currentTarget"]):
            fail(f"input hash does not match content: {key}")
        if row["finalTargetSha256"] != sha(row["finalTarget"]):
            fail(f"root target hash does not match content: {key}")
        if row["catalogPath"] != src["catalogPath"] or row["catalogFileSha256"] != src["catalogFileSha256"] or row["catalogGitBlob"] != src["catalogGitBlob"]:
            fail(f"exact catalog file pin mismatch: {key}")
        if src["placeholderEvidence"].get("matches") is not True or src["markupEvidence"].get("matches") is not True:
            fail(f"source/current placeholder or markup contract failed: {key}")
        checks = row["placeholderMarkupNumericAndProtectedChecks"]
        if checks != {"placeholderMatch": True, "markupMatch": True, "numericSourceValuesPreserved": True, "protectedLiteralsPreserved": True}:
            fail(f"final placeholder/markup/numeric/protected check failed: {key}")
        if final_catalogs[src["locale"]].get(src["source"]) != src["currentTarget"]:
            fail(f"catalog current value does not match exact input: {key}")

        disposition = row["rootDisposition"]
        target = row["finalTarget"]
        if disposition in {"correction", "refinement"}:
            if target == src["currentTarget"]:
                fail(f"change disposition is a no-op: {key}")
            plan = {
                "continuationRank": src["continuationRank"],
                "sourceId": src["sourceId"],
                "source": src["source"],
                "locale": src["locale"],
                "catalogPath": src["catalogPath"],
                "currentTargetSha256": src["currentTargetSha256"],
                "finalDisposition": disposition,
                "finalTarget": target,
                "finalTargetSha256": sha(target),
                "callerContextSha256": src["callerContextSha256"],
                "winner": row["independentCrossAuditOutcome"],
            }
            plans.append(plan)
            changes_by_locale[src["locale"]] += 1
            final_catalogs[src["locale"]][src["source"]] = target
        elif disposition in {"accept-current", "hold-context", "hold-terminology"}:
            if target != src["currentTarget"]:
                fail(f"non-change disposition changes target: {key}")
        else:
            fail(f"unknown root disposition {disposition!r}: {key}")
        dispositions[disposition] += 1
        readback.append({
            "continuationRank": src["continuationRank"],
            "sourceId": src["sourceId"],
            "locale": src["locale"],
            "catalogPath": src["catalogPath"],
            "disposition": disposition,
            "changed": disposition in {"correction", "refinement"},
            "currentTargetSha256": src["currentTargetSha256"],
            "finalTargetSha256": sha(target),
            "callerContextSha256": src["callerContextSha256"],
        })

    if len(plans) != EXPECTED_CHANGES:
        fail(f"expected {EXPECTED_CHANGES} exact-hash changes, found {len(plans)}")
    if dispositions != {"accept-current": 207, "correction": 43, "refinement": 7, "hold-context": 24, "hold-terminology": 19}:
        fail(f"root dispositions changed: {dict(dispositions)}")
    if sum(changes_by_locale.values()) != EXPECTED_CHANGES:
        fail("per-locale change counts do not match total changes")

    output_bytes = {locale: (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode("utf-8") for locale, catalog in final_catalogs.items()}
    for locale, meta in catalog_meta.items():
        path = ROOT / meta["catalogPath"]
        if path.read_bytes() != original_bytes[locale]:
            fail(f"catalog changed during preflight: {locale}")

    for locale, meta in catalog_meta.items():
        (ROOT / meta["catalogPath"]).write_bytes(output_bytes[locale])
    for row in readback:
        src = inputs[(row["sourceId"], row["locale"])]
        actual = json.loads((ROOT / row["catalogPath"]).read_text(encoding="utf-8"))[src["source"]]
        expected = adjudicated[(row["sourceId"], row["locale"])]["finalTarget"]
        if actual != expected:
            fail(f"post-write readback mismatch: {(row['sourceId'], row['locale'])}")
        row["readbackTargetSha256"] = sha(actual)
        row["readbackMatches"] = True

    app_dir = EVIDENCE / "application"
    write_jsonl(app_dir / "apply-plan.jsonl", plans)
    write_jsonl(app_dir / "readback.jsonl", readback)
    summary = {
        "repository": "snapetech-org/slskdN",
        "pullRequest": 409,
        "window": "W54",
        "baseHead": BASE_HEAD,
        "baseTree": BASE_TREE,
        "reviewedCells": EXPECTED_ROWS,
        "changedCells": len(plans),
        "changedByLocale": dict(sorted(changes_by_locale.items())),
        "finalDispositions": dict(sorted(dispositions.items())),
        "noCallerHolds": 24,
        "terminologyAndGlossaryHolds": 19,
        "catalogs": {
            locale: {
                "path": meta["catalogPath"],
                "entryCount": EXPECTED_KEY_COUNT,
                "orderedKeySha256": EXPECTED_ORDER_HASH,
                "beforeSha256": meta["sha256"],
                "afterSha256": sha(output_bytes[locale]),
            }
            for locale, meta in sorted(catalog_meta.items())
        },
        "readbackRows": len(readback),
        "readbackMismatches": sum(not r["readbackMatches"] for r in readback),
        "nativeSpeakerApproval": False,
        "headedProductBrowserAcceptance": False,
        "testsBuildsScansOrCiRun": False,
        "workflowsChanged": False,
    }
    (app_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
