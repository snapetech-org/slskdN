#!/usr/bin/env python3
"""Reconcile slskdN W54 review outputs into a root exact-hash ledger."""
from __future__ import annotations

import collections
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
EVIDENCE = ROOT / "docs/pr-evidence/pr409-localization-2026-11-03/window54"
INPUT = EVIDENCE / "review/input"
PRIMARY = EVIDENCE / "review/primary"
BLIND = EVIDENCE / "review/independent-blind"
CROSS = EVIDENCE / "review/cross-audit"
OUTPUT = EVIDENCE / "review/root-adjudication/root-adjudication.jsonl"
SUMMARY = EVIDENCE / "review/root-adjudication/summary.json"
BASE_HEAD = "5812e90c3018f0a8b563bff2ba95b5fd19076908"
BASE_TREE = "632924177388e15b594976774d2d879a098e8a72"
EXPECTED_CELLS = 300
EXPECTED_SOURCE_COUNT = 25
EXPECTED_LOCALE_COUNT = 12
EXPECTED_WINNERS = 50
EXPECTED_HOLDS = 43


def sha(data: bytes | str) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def fail(message: str) -> None:
    raise SystemExit(f"REFUSED: {message}")


def row_key(row: dict) -> tuple[str, str]:
    return row["sourceId"], row["locale"]


def verify_sha_manifest(directory: Path, name: str) -> None:
    manifest = directory / name
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, rel = line.split(maxsplit=1)
        rel = rel.lstrip("*")
        path = directory / rel.strip()
        if not path.is_file() or sha(path.read_bytes()) != digest:
            fail(f"checksum mismatch: {path.relative_to(EVIDENCE)}")


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip()
    if (head, tree) != (BASE_HEAD, BASE_TREE):
        fail(f"expected exact PR base {BASE_HEAD}/{BASE_TREE}, found {head}/{tree}")

    verify_sha_manifest(INPUT, "PACKET-SHA256SUMS.txt")
    verify_sha_manifest(PRIMARY, "SHA256SUMS.txt")
    verify_sha_manifest(BLIND, "SHA256SUMS.txt")
    verify_sha_manifest(CROSS, "SHA256SUMS.txt")
    verify_sha_manifest(BLIND / "input", "PACKET-SHA256SUMS.txt")

    pin = read_json(INPUT / "head-tree-attestation.json")
    live = read_json(CROSS / "live-pr-verification.json")
    if pin.get("head") != BASE_HEAD or pin.get("tree") != BASE_TREE:
        fail("candidate-free packet head/tree changed")
    if live.get("pullRequestHead") != BASE_HEAD or live.get("tree") != BASE_TREE or live.get("state") != "open" or live.get("draft") is not True or live.get("allLiveHeadChecksMatch") is not True:
        fail("live PR attestation is not the expected open draft head")

    primary_input = read_jsonl(INPUT / "source-current-cells.jsonl")
    blind_input = read_jsonl(BLIND / "input/source-current-cells.jsonl")
    primary = read_jsonl(PRIMARY / "review-decisions.jsonl")
    blind = read_jsonl(BLIND / "review-ledger.jsonl")
    cross = read_jsonl(CROSS / "reconciliation-ledger.jsonl")
    structures = read_jsonl(INPUT / "catalog-structure.jsonl")
    contexts = read_jsonl(INPUT / "caller-contexts.jsonl")
    if len(primary_input) != EXPECTED_CELLS or len(blind_input) != EXPECTED_CELLS or len(primary) != EXPECTED_CELLS or len(blind) != EXPECTED_CELLS or len(cross) != EXPECTED_CELLS:
        fail("a 300-row review packet has changed size")
    if len(structures) != EXPECTED_LOCALE_COUNT or len(contexts) != EXPECTED_SOURCE_COUNT:
        fail("expected 12 catalog pins and 25 caller-context records")

    maps = []
    for label, rows in (("primary input", primary_input), ("blind input", blind_input), ("primary", primary), ("blind", blind), ("cross-audit", cross)):
        mapping = {row_key(r): r for r in rows}
        if len(mapping) != EXPECTED_CELLS:
            fail(f"duplicate or missing rows in {label}")
        maps.append(mapping)
    input_map, blind_input_map, primary_map, blind_map, cross_map = maps
    if set(input_map) != set(blind_input_map) or set(input_map) != set(primary_map) or set(input_map) != set(blind_map) or set(input_map) != set(cross_map):
        fail("review packets do not cover the same exact 300 cells")

    if (INPUT / "source-current-cells.jsonl").read_bytes() != (BLIND / "input/source-current-cells.jsonl").read_bytes():
        fail("candidate-free primary and blind inputs are not byte-identical")

    catalog_meta = {row["locale"]: row for row in structures}
    if len(catalog_meta) != EXPECTED_LOCALE_COUNT:
        fail("duplicate locale catalog pin")
    for locale, meta in catalog_meta.items():
        path = ROOT / meta["catalogPath"]
        raw = path.read_bytes()
        if sha(raw) != meta["sha256"]:
            fail(f"catalog raw-byte hash mismatch before application: {locale}")
        blob = subprocess.check_output(["git", "hash-object", meta["catalogPath"]], cwd=ROOT, text=True).strip()
        if blob != meta["gitBlob"]:
            fail(f"catalog Git blob mismatch before application: {locale}")
        catalog = json.loads(raw)
        if len(catalog) != 6176 or any(not isinstance(value, str) for value in catalog.values()):
            fail(f"catalog entry count or value type changed: {locale}")
        if sha("\n".join(catalog.keys()) + "\n") != meta["orderedKeySha256"]:
            fail(f"ordered catalog keys changed: {locale}")
        if (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode() != raw:
            fail(f"catalog serialization changed: {locale}")

    # Verify every pinned production caller file against the exact base tree.
    caller_files = {}
    for context in contexts:
        for caller in context.get("callers", []):
            caller_files[caller["path"]] = caller
    for rel, expected in caller_files.items():
        raw = (ROOT / rel).read_bytes()
        if sha(raw) != expected["fileSha256"]:
            fail(f"caller file SHA-256 mismatch: {rel}")
        blob = subprocess.check_output(["git", "hash-object", rel], cwd=ROOT, text=True).strip()
        if blob != expected["gitBlob"]:
            fail(f"caller Git blob mismatch: {rel}")

    final = []
    dispositions = collections.Counter()
    winners = collections.Counter()
    holds = collections.Counter()
    for key in sorted(input_map, key=lambda pair: (input_map[pair]["continuationRank"], pair[1])):
        source = input_map[key]
        blind_source = blind_input_map[key]
        primary_row = primary_map[key]
        blind_row = blind_map[key]
        cross_row = cross_map[key]
        if row_key(source) != key or source["source"] != blind_source["source"] or source["sourceSha256"] != blind_source["sourceSha256"]:
            fail(f"source mismatch between primary and blind input: {key}")
        if source["currentTarget"] != blind_source["currentTarget"] or source["currentTargetSha256"] != blind_source["currentTargetSha256"]:
            fail(f"current target mismatch between primary and blind input: {key}")
        if source["sourceSha256"] != sha(source["source"]) or source["currentTargetSha256"] != sha(source["currentTarget"]):
            fail(f"source/current content hash mismatch: {key}")
        for row in (primary_row, blind_row, cross_row):
            if row["sourceSha256"] != source["sourceSha256"] or row["currentTargetSha256"] != source["currentTargetSha256"]:
                fail(f"review source/current hashes differ from the frozen input: {key}")
            context_hash = row.get("callerContextSha256")
            if row is blind_row:
                context_hash = row.get("callerRelevance", {}).get("callerContextSha256")
            elif row is cross_row:
                context_hash = row.get("callerEvidence", {}).get("callerContextSha256")
            if context_hash != source["callerContextSha256"]:
                fail(f"caller-context hash mismatch: {key}")
        if cross_row["adjudicatedTargetSha256"] != sha(cross_row["adjudicatedTarget"]):
            fail(f"cross-audit final-target hash mismatch: {key}")
        if cross_row["catalogFileSha256"] != source["catalogFileSha256"] or cross_row["catalogGitBlob"] != source["catalogGitBlob"] or cross_row["catalogPath"] != source["catalogPath"]:
            fail(f"catalog pin mismatch: {key}")
        if cross_row["placeholdersAndICU"]["placeholderMatch"] is not True or cross_row["markup"]["markupMatch"] is not True:
            fail(f"placeholder or markup review failed: {key}")
        if cross_row["numericTokens"]["numericSourceValuesPreserved"] is not True or cross_row["protectedLiterals"]["allPreserved"] is not True:
            fail(f"numeric or protected-literal review failed: {key}")
        if source["placeholderEvidence"].get("matches") is not True or source["markupEvidence"].get("matches") is not True:
            fail(f"source/current structural checks failed: {key}")

        outcome = cross_row["adjudicatedOutcome"]
        target = cross_row["adjudicatedTarget"]
        if outcome == "KEEP_CURRENT":
            disposition = "accept-current"
            if target != source["currentTarget"]:
                fail(f"accept-current row changes target: {key}")
        elif outcome in {"WIN_PRIMARY", "WIN_BLIND"}:
            if target == source["currentTarget"] or cross_row["applyTarget"] != target:
                fail(f"winner is a no-op or apply target mismatch: {key}")
            disposition = "correction" if (cross_row["adjudicatedTargetSource"] == "blind" or cross_row["primaryVerdict"] == "correction") else "refinement"
            if cross_row["adjudicatedTargetSource"] not in {"primary", "blind"}:
                fail(f"winner has no reviewed source: {key}")
            winners[cross_row["adjudicatedTargetSource"]] += 1
        elif outcome == "HOLD_NO_DIRECT_LOCALIZED_CALLER":
            disposition = "hold-context"
            if target != source["currentTarget"] or cross_row["applyTarget"] is not None:
                fail(f"context-held row changed target: {key}")
            holds["hold-context"] += 1
        elif outcome in {"HOLD_GLOSSARY", "HOLD_TERMINOLOGY"}:
            disposition = "hold-terminology"
            if target != source["currentTarget"] or cross_row["applyTarget"] is not None:
                fail(f"terminology-held row changed target: {key}")
            holds["hold-terminology"] += 1
        else:
            fail(f"unrecognized cross-audit outcome {outcome!r}: {key}")

        catalog = json.loads((ROOT / source["catalogPath"]).read_text(encoding="utf-8"))
        if catalog.get(source["source"]) != source["currentTarget"]:
            fail(f"catalog value differs from the exact pinned current target: {key}")
        dispositions[disposition] += 1
        final.append({
            "continuationRank": source["continuationRank"],
            "historicalSourceOrdinal": source.get("historicalSourceOrdinal"),
            "sourceId": source["sourceId"],
            "source": source["source"],
            "sourceSha256": source["sourceSha256"],
            "locale": source["locale"],
            "catalogPath": source["catalogPath"],
            "catalogFileSha256": source["catalogFileSha256"],
            "catalogGitBlob": source["catalogGitBlob"],
            "currentTarget": source["currentTarget"],
            "currentTargetSha256": source["currentTargetSha256"],
            "callerContextSha256": source["callerContextSha256"],
            "callerRefs": source.get("callerRefs", []),
            "primaryVerdict": primary_row["verdict"],
            "primaryCandidateTarget": primary_row["candidateTarget"],
            "primaryRationale": primary_row["rationale"],
            "blindDecision": blind_row["decision"],
            "blindProposedTarget": blind_row["proposedTarget"],
            "blindRationale": blind_row["semanticRationale"],
            "independentCrossAuditOutcome": outcome,
            "rootDisposition": disposition,
            "finalTarget": target,
            "finalTargetSha256": sha(target),
            "adjudicationRationale": cross_row["adjudicationRationale"],
            "placeholderMarkupNumericAndProtectedChecks": {
                "placeholderMatch": cross_row["placeholdersAndICU"]["placeholderMatch"],
                "markupMatch": cross_row["markup"]["markupMatch"],
                "numericSourceValuesPreserved": cross_row["numericTokens"]["numericSourceValuesPreserved"],
                "protectedLiteralsPreserved": cross_row["protectedLiterals"]["allPreserved"],
            },
            "nativeSpeakerApproval": "pending; machine-assisted review is not qualified native-speaker approval",
        })

    if len(final) != EXPECTED_CELLS:
        fail("root ledger row count changed")
    if winners != {"primary": 47, "blind": 3}:
        fail(f"winner counts changed: {dict(winners)}")
    if holds != {"hold-context": 24, "hold-terminology": 19}:
        fail(f"hold counts changed: {dict(holds)}")
    if dispositions != {"accept-current": 207, "correction": 43, "refinement": 7, "hold-context": 24, "hold-terminology": 19}:
        fail(f"root disposition counts changed: {dict(dispositions)}")
    OUTPUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in final), encoding="utf-8")
    summary = {
        "repository": "snapetech-org/slskdN",
        "pullRequest": 409,
        "window": "W54, stable-ID continuation ranks 251–275",
        "baseHead": BASE_HEAD,
        "baseTree": BASE_TREE,
        "reviewedCells": len(final),
        "sourceCount": EXPECTED_SOURCE_COUNT,
        "localeCount": EXPECTED_LOCALE_COUNT,
        "rootDispositions": dict(sorted(dispositions.items())),
        "winningCandidateSources": dict(sorted(winners.items())),
        "heldCounts": dict(sorted(holds.items())),
        "appliedCandidateCount": sum(winners.values()),
        "callerReferencesReattested": sum(len(row.get("callers", [])) for row in contexts),
        "catalogKeyCountPerLocale": 6176,
        "orderedCatalogKeySha256": catalog_meta["ar"]["orderedKeySha256"],
        "nativeSpeakerApproval": False,
        "headedProductBrowserAcceptance": False,
        "testsBuildsScansOrCiRun": False,
        "workflowsChanged": False,
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
