#!/usr/bin/env python3
"""Apply the root-adjudicated W55 winners to the exact PR head."""
from __future__ import annotations

import collections
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
WINDOW = ROOT / "docs/pr-evidence/pr409-localization-2026-11-03/window55"
INPUT = WINDOW / "review/primary-packet/input"
ROOT_REVIEW = WINDOW / "review/root-adjudication"
APPLICATION = WINDOW / "application"
BASE_HEAD = "6a46b8f1dc87d899308fee141fa0db392e49e098"
BASE_TREE = "a22e9a896aae12aa89a1502d9748b12816d491ed"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
KEY_COUNT = 6176
ORDER_HASH = "3ca04c40ebfed00b93fcd143109fc9d85da941cec30b6cb93f52e431498df6a7"


def fail(message: str) -> None:
    raise SystemExit(f"REFUSED: {message}")


def sha(data: bytes | str) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip()
    if (head, tree) != (BASE_HEAD, BASE_TREE):
        fail(f"expected exact application base {BASE_HEAD}/{BASE_TREE}; found {head}/{tree}")
    if subprocess.run(["git", "diff", "--quiet", "HEAD", "--"], cwd=ROOT).returncode != 0:
        fail("tracked changes exist before applying W55 catalog winners")

    root_rows = read_jsonl(ROOT_REVIEW / "root-adjudication.jsonl")
    apply_rows = read_jsonl(APPLICATION / "apply-plan.jsonl")
    root_summary = read_json(ROOT_REVIEW / "summary.json")
    structures = read_jsonl(INPUT / "catalog-structure.jsonl")
    input_rows = read_jsonl(INPUT / "source-current-cells.jsonl")
    if root_summary.get("baseHead") != BASE_HEAD or root_summary.get("baseTree") != BASE_TREE:
        fail("root adjudication is not pinned to the exact application base")
    if root_summary.get("rootLedgerSha256") != sha((ROOT_REVIEW / "root-adjudication.jsonl").read_bytes()):
        fail("root adjudication ledger checksum mismatch")
    if len(root_rows) != 300 or len(input_rows) != 300 or len(apply_rows) != 71 or len(structures) != 12:
        fail("root ledger, input, plan, or catalog count changed")
    if (root_summary.get("applyPlanRows"), root_summary.get("holdRows")) != (71, 36):
        fail("root counts do not match the approved 71 changes and 36 holds")

    inputs = {(row["sourceId"], row["locale"]): row for row in input_rows}
    adjudicated = {(row["sourceId"], row["locale"]): row for row in root_rows}
    if len(inputs) != 300 or len(adjudicated) != 300 or set(inputs) != set(adjudicated):
        fail("duplicate or mismatched source/locale cells")
    catalog_meta = {row["locale"]: row for row in structures}
    if len(catalog_meta) != 12:
        fail("expected exactly twelve locale catalog pins")

    catalogs: dict[str, dict] = {}
    original_bytes: dict[str, bytes] = {}
    for locale, meta in catalog_meta.items():
        path = ROOT / meta["catalogPath"]
        raw = path.read_bytes()
        blob = subprocess.check_output(["git", "hash-object", meta["catalogPath"]], cwd=ROOT, text=True).strip()
        if sha(raw) != meta["sha256"] or blob != meta["gitBlob"]:
            fail(f"catalog exact-head pin mismatch: {locale}")
        catalog = json.loads(raw)
        if len(catalog) != KEY_COUNT or any(not isinstance(value, str) for value in catalog.values()):
            fail(f"catalog key/value shape changed: {locale}")
        if sha("\n".join(catalog.keys()) + "\n") != ORDER_HASH:
            fail(f"catalog ordered-key checksum mismatch: {locale}")
        if (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode("utf-8") != raw:
            fail(f"catalog serialization differs from pinned format: {locale}")
        catalogs[locale] = catalog
        original_bytes[locale] = raw

    plan_map = {(row["sourceId"], row["locale"]): row for row in apply_rows}
    if len(plan_map) != 71:
        fail("duplicate apply-plan cell")
    if any(not 276 <= row["continuationRank"] <= 300 for row in apply_rows):
        fail("apply plan includes a rank outside W55 (276-300)")
    if any(row["continuationRank"] in (301, 302) for row in apply_rows):
        fail("apply plan includes prohibited ranks 301 or 302")

    for key, row in inputs.items():
        root_row = adjudicated[key]
        if root_row["catalogPath"] != row["catalogPath"] or root_row["currentTarget"] != row["currentTarget"]:
            fail(f"root adjudication differs from candidate-free input: {key}")
        decision = root_row["rootDecision"]
        actual = catalogs[row["locale"]].get(row["source"])
        if actual != row["currentTarget"]:
            fail(f"catalog current value changed since review: {key}")
        if decision["action"] == "apply-candidate":
            plan = plan_map.get(key)
            if not plan or plan["newTarget"] != decision["target"] or plan["oldTarget"] != row["currentTarget"]:
                fail(f"apply plan does not match root decision: {key}")
            if plan["newTargetSha256"] != sha(plan["newTarget"]):
                fail(f"apply target checksum mismatch: {key}")
        elif decision["action"] in ("keep-current", "hold-current"):
            if key in plan_map or decision["target"] != row["currentTarget"]:
                fail(f"retained or held cell is incorrectly scheduled for application: {key}")
        else:
            fail(f"unknown root action at {key}: {decision['action']}")
    if set(plan_map) != {key for key, row in adjudicated.items() if row["rootDecision"]["action"] == "apply-candidate"}:
        fail("apply plan does not exactly cover all root-adjudicated winners")

    final_catalogs = {locale: dict(catalog) for locale, catalog in catalogs.items()}
    changed_by_locale = collections.Counter()
    for key, plan in plan_map.items():
        locale = plan["locale"]
        if plan["catalogFileSha256"] != catalog_meta[locale]["sha256"] or plan["catalogGitBlob"] != catalog_meta[locale]["gitBlob"]:
            fail(f"apply plan catalog pin mismatch: {key}")
        source = plan["source"]
        if final_catalogs[locale].get(source) != plan["oldTarget"]:
            fail(f"old target changed before write: {key}")
        final_catalogs[locale][source] = plan["newTarget"]
        changed_by_locale[locale] += 1

    output_bytes = {}
    for locale, catalog in final_catalogs.items():
        if len(catalog) != KEY_COUNT or sha("\n".join(catalog.keys()) + "\n") != ORDER_HASH:
            fail(f"key order or count changed in planned output: {locale}")
        output = (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        output_bytes[locale] = output
        if locale not in changed_by_locale and output != original_bytes[locale]:
            fail(f"unplanned catalog serialization change: {locale}")
    for locale, count in changed_by_locale.items():
        if count == 0:
            fail(f"empty locale apply bucket: {locale}")

    # Recheck the original bytes immediately before writing, then update only planned catalogs.
    for locale, meta in catalog_meta.items():
        if (ROOT / meta["catalogPath"]).read_bytes() != original_bytes[locale]:
            fail(f"catalog changed during preflight: {locale}")
    for locale in changed_by_locale:
        (ROOT / catalog_meta[locale]["catalogPath"]).write_bytes(output_bytes[locale])

    readback = []
    mismatches = []
    for key, root_row in adjudicated.items():
        locale = root_row["locale"]
        actual = json.loads((ROOT / root_row["catalogPath"]).read_text(encoding="utf-8"))[root_row["source"]]
        expected = root_row["rootDecision"]["target"]
        matches = actual == expected
        if not matches:
            mismatches.append({"sourceId": key[0], "locale": locale, "expected": expected, "actual": actual})
        readback.append({
            "continuationRank": root_row["continuationRank"], "sourceId": key[0], "source": root_row["source"],
            "locale": locale, "catalogPath": root_row["catalogPath"], "disposition": root_row["rootDecision"]["disposition"],
            "action": root_row["rootDecision"]["action"], "expectedTarget": expected,
            "expectedTargetSha256": sha(expected), "readbackTarget": actual, "readbackTargetSha256": sha(actual),
            "readbackMatches": matches,
        })
    if mismatches:
        fail(f"post-write readback mismatch count={len(mismatches)}")

    catalogs_after = {}
    for locale, meta in catalog_meta.items():
        raw = (ROOT / meta["catalogPath"]).read_bytes()
        current = json.loads(raw)
        if len(current) != KEY_COUNT or sha("\n".join(current.keys()) + "\n") != ORDER_HASH:
            fail(f"post-write catalog structure changed: {locale}")
        if (json.dumps(current, ensure_ascii=False, indent=2) + "\n").encode("utf-8") != raw:
            fail(f"post-write serialization check failed: {locale}")
        catalogs_after[locale] = {"path": meta["catalogPath"], "entryCount": KEY_COUNT,
                                  "orderedKeySha256": ORDER_HASH, "beforeSha256": sha(original_bytes[locale]),
                                  "afterSha256": sha(raw), "changedCells": changed_by_locale.get(locale, 0)}

    diff_check = subprocess.run(["git", "diff", "--check", "HEAD", "--"], cwd=ROOT, text=True, capture_output=True)
    if diff_check.returncode != 0:
        fail("git diff --check failed after catalog application: " + diff_check.stdout + diff_check.stderr)
    write_jsonl(APPLICATION / "readback.jsonl", readback)
    summary = {
        "repository": "snapetech-org/slskdN", "pullRequest": 409, "window": "W55",
        "baseHead": BASE_HEAD, "baseTree": BASE_TREE, "reviewedCells": 300, "changedCells": len(plan_map),
        "changedByLocale": dict(sorted(changed_by_locale.items())),
        "finalDispositions": root_summary["rootDispositions"], "retainedCurrentCells": 193,
        "terminologyHolds": 36, "holdRanks": [278, 282, 289], "appliedRankRange": [276, 300],
        "ranks301And302Touched": False, "readbackRows": len(readback), "readbackMismatches": 0,
        "gitDiffCheck": "passed", "catalogs": catalogs_after,
        "nativeSpeakerApproval": False, "headedProductBrowserAcceptance": False,
        "testsBuildsScansCiRun": False, "workflowsChanged": False,
    }
    write_json(APPLICATION / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
