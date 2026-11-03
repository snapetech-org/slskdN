#!/usr/bin/env python3
"""Independently reconcile the sealed W55 ledgers and make the root apply plan."""
from __future__ import annotations

import collections
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
WINDOW = ROOT / "docs/pr-evidence/pr409-localization-2026-11-03/window55"
REVIEW = WINDOW / "review"
PRIMARY_PACKET = REVIEW / "primary-packet"
INPUT = PRIMARY_PACKET / "input"
PRIMARY = PRIMARY_PACKET / "primary"
BLIND = REVIEW / "independent-blind"
CROSS = REVIEW / "cross-audit"
ROOT_REVIEW = REVIEW / "root-adjudication"
APPLICATION = WINDOW / "application"
BASE_HEAD = "6a46b8f1dc87d899308fee141fa0db392e49e098"
BASE_TREE = "a22e9a896aae12aa89a1502d9748b12816d491ed"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
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


def verify_manifest(directory: Path, name: str) -> int:
    manifest = directory / name
    count = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, rel = line.split(maxsplit=1)
        rel = rel.lstrip("*").strip()
        path = directory / rel
        if not path.is_file() or sha(path.read_bytes()) != digest:
            fail(f"checksum mismatch: {path}")
        count += 1
    return count


def key(row: dict) -> tuple[str, str]:
    return row["sourceId"], row["locale"]


def slim_callers(context: dict) -> list[dict]:
    return [{k: caller[k] for k in ("path", "line", "lineSha256", "fileSha256", "gitBlob")} for caller in context.get("callers", [])]


def main() -> None:
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != BASE_HEAD:
        fail("root adjudication must run at the exact W55 PR base head")
    if subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip() != BASE_TREE:
        fail("root adjudication must run at the exact W55 PR base tree")
    if subprocess.run(["git", "diff", "--quiet", "HEAD", "--"], cwd=ROOT).returncode != 0:
        fail("tracked changes exist before root adjudication")
    live = json.loads(subprocess.check_output([
        "gh", "pr", "view", "409", "--json", "state,isDraft,headRefName,headRefOid,body"
    ], cwd=ROOT, text=True))
    if (live.get("state"), live.get("isDraft"), live.get("headRefName"), live.get("headRefOid")) != ("OPEN", True, BRANCH, BASE_HEAD):
        fail("live PR is not the expected open draft at the exact W55 base")
    remote = subprocess.check_output(["git", "ls-remote", "origin", f"refs/heads/{BRANCH}"], cwd=ROOT, text=True).split()
    if not remote or remote[0] != BASE_HEAD:
        fail("remote PR branch no longer matches the exact W55 base")

    manifest_counts = {
        "primaryRootEntries": verify_manifest(PRIMARY_PACKET, "SHA256SUMS.txt"),
        "inputEntries": verify_manifest(INPUT, "PACKET-SHA256SUMS.txt"),
        "primaryEntries": verify_manifest(PRIMARY, "SHA256SUMS.txt"),
        "blindEntries": verify_manifest(BLIND, "PACKET-SHA256SUMS.txt"),
        "crossEntries": verify_manifest(CROSS, "PACKET-SHA256SUMS.txt"),
    }
    primary_root_manifest_sha = sha((PRIMARY_PACKET / "SHA256SUMS.txt").read_bytes())
    input_manifest_sha = sha((INPUT / "PACKET-SHA256SUMS.txt").read_bytes())
    primary_manifest_sha = sha((PRIMARY / "SHA256SUMS.txt").read_bytes())
    blind_manifest_sha = sha((BLIND / "PACKET-SHA256SUMS.txt").read_bytes())
    cross_manifest_sha = sha((CROSS / "PACKET-SHA256SUMS.txt").read_bytes())

    attestation = read_json(INPUT / "head-tree-attestation.json")
    selection = read_json(INPUT / "selection-and-boundary.json")
    primary_summary = read_json(PRIMARY / "review-summary.json")
    blind_summary = read_json(BLIND / "blind-review-summary.json")
    cross_summary = read_json(CROSS / "cross-audit-summary.json")
    if attestation.get("head") != BASE_HEAD or attestation.get("tree") != BASE_TREE:
        fail("candidate-free input does not pin the exact W55 head/tree")
    if selection.get("cellCount") != 300 or selection.get("sourceCount") != 25 or selection.get("localeOrder") != LOCALES:
        fail("W55 sequential selection or locale boundary changed")
    for summary in (primary_summary, blind_summary, cross_summary):
        if summary.get("exactHead") != BASE_HEAD or summary.get("exactTree") != BASE_TREE or summary.get("remoteBranchHead") != BASE_HEAD:
            fail("one review summary does not pin the exact current head/tree")
    if sha(live["body"]) != attestation.get("bodySha256"):
        fail("live PR body changed since the pinned review packets")

    input_rows = read_jsonl(INPUT / "source-current-cells.jsonl")
    primary_rows = read_jsonl(PRIMARY / "review-decisions.jsonl")
    blind_rows = read_jsonl(BLIND / "blind-review-ledger.jsonl")
    cross_rows = read_jsonl(CROSS / "cross-audit-ledger.jsonl")
    structures = read_jsonl(INPUT / "catalog-structure.jsonl")
    contexts = read_jsonl(INPUT / "caller-contexts.jsonl")
    expected_rows = 300
    if any(len(rows) != expected_rows for rows in (input_rows, primary_rows, blind_rows, cross_rows)):
        fail("one of the ledgers does not contain exactly 300 cells")
    maps = []
    for label, rows in (("input", input_rows), ("primary", primary_rows), ("blind", blind_rows), ("cross", cross_rows)):
        mapping = {key(row): row for row in rows}
        if len(mapping) != expected_rows:
            fail(f"duplicate or missing cells in {label}")
        maps.append(mapping)
    inputs, primaries, blinds, crosses = maps
    if not (set(inputs) == set(primaries) == set(blinds) == set(crosses)):
        fail("review ledgers do not cover the exact same source/locale cells")
    if len(structures) != len(LOCALES) or len({row["locale"] for row in structures}) != len(LOCALES):
        fail("expected exactly twelve distinct catalog pins")
    context_map = {row["sourceId"]: row for row in contexts}
    if len(context_map) != 25:
        fail("expected 25 source caller-context records")

    # Catalog pins, bytes, serialization, and ordered keys are checked independently.
    catalog_meta = {row["locale"]: row for row in structures}
    catalogs: dict[str, dict] = {}
    for locale in LOCALES:
        meta = catalog_meta[locale]
        path = ROOT / meta["catalogPath"]
        raw = path.read_bytes()
        blob = subprocess.check_output(["git", "hash-object", meta["catalogPath"]], cwd=ROOT, text=True).strip()
        if sha(raw) != meta["sha256"] or blob != meta["gitBlob"]:
            fail(f"catalog exact-head raw hash or Git blob mismatch: {locale}")
        catalog = json.loads(raw)
        if len(catalog) != KEY_COUNT or any(not isinstance(value, str) for value in catalog.values()):
            fail(f"catalog structure mismatch: {locale}")
        if sha("\n".join(catalog.keys()) + "\n") != ORDER_HASH or meta["orderedKeySha256"] != ORDER_HASH:
            fail(f"ordered catalog key hash mismatch: {locale}")
        if (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode("utf-8") != raw:
            fail(f"catalog JSON serialization mismatch: {locale}")
        catalogs[locale] = catalog

    # Caller references are pinned to source files, exact line numbers, and line hashes.
    caller_file_cache: dict[str, tuple[bytes, str]] = {}
    verified_caller_refs = 0
    for source_id, context in context_map.items():
        source_rows = [row for row in input_rows if row["sourceId"] == source_id]
        if len(source_rows) != len(LOCALES):
            fail(f"input source does not have twelve locale cells: {source_id}")
        if context["source"] != source_rows[0]["source"] or context["sourceSha256"] != source_rows[0]["sourceSha256"]:
            fail(f"caller context source pin mismatch: {source_id}")
        expected_callers = slim_callers(context)
        for source_row in source_rows:
            if source_row["callerRefs"] != expected_callers:
                fail(f"caller refs differ between input and caller-context packet: {source_id}/{source_row['locale']}")
            if source_row["callerContextSha256"] != sha(json.dumps(context["callers"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))):
                fail(f"caller-context aggregate hash mismatch: {source_id}/{source_row['locale']}")
        for caller in context.get("callers", []):
            rel = caller["path"]
            if rel not in caller_file_cache:
                raw = (ROOT / rel).read_bytes()
                blob = subprocess.check_output(["git", "hash-object", rel], cwd=ROOT, text=True).strip()
                if sha(raw) != caller["fileSha256"] or blob != caller["gitBlob"]:
                    fail(f"caller source file pin mismatch: {rel}")
                caller_file_cache[rel] = (raw, blob)
            raw, _ = caller_file_cache[rel]
            lines = raw.decode("utf-8").splitlines()
            if not (1 <= caller["line"] <= len(lines)):
                fail(f"caller line outside source file: {rel}:{caller['line']}")
            line = lines[caller["line"] - 1]
            if line != caller["lineText"] or sha(line) != caller["lineSha256"]:
                fail(f"caller line content/hash mismatch: {rel}:{caller['line']}")
            verified_caller_refs += 1

    # Candidate-free input must not contain proposals or reviewer fields.
    forbidden_keys = ("candidate", "proposal", "verdict", "rationale", "primary", "blind", "cross")
    for row in input_rows:
        if any(any(token in name.lower() for token in forbidden_keys) for name in row):
            fail("candidate-free source/current input contains a candidate/review field")

    dispositions = collections.Counter()
    primary_changes = blind_changes = cross_changes = 0
    candidate_text_disagreements = verdict_disagreements = disagreement_cells = 0
    root_rows: list[dict] = []
    apply_rows: list[dict] = []
    hold_rows: list[dict] = []
    per_locale_changes = collections.Counter()
    for cell_key in sorted(inputs, key=lambda item: (primaries[item]["continuationRank"], LOCALES.index(item[1]))):
        source = inputs[cell_key]
        primary = primaries[cell_key]
        blind = blinds[cell_key]
        cross = crosses[cell_key]
        adjudication = cross["crossAdjudication"]
        source_id, locale = cell_key
        if (source["continuationRank"], source["locale"]) != (primary["continuationRank"], primary["locale"]):
            fail(f"row identity mismatch: {cell_key}")
        for obj in (primary, blind):
            for field in ("continuationRank", "source", "sourceSha256", "locale", "catalogPath", "catalogFileSha256", "catalogGitBlob", "currentTarget", "currentTargetSha256", "callerContextSha256", "callerRefs"):
                if obj.get(field) != source.get(field):
                    fail(f"{field} pin mismatch for {cell_key}")
        for field in ("continuationRank", "source", "sourceSha256", "locale", "catalogPath", "catalogFileSha256", "catalogGitBlob", "currentTarget", "currentTargetSha256", "callerContextSha256", "callerRefs"):
            if cross.get(field) != source.get(field):
                fail(f"cross-audit {field} pin mismatch for {cell_key}")
        if sha(source["source"]) != source["sourceSha256"] or sha(source["currentTarget"]) != source["currentTargetSha256"]:
            fail(f"source/current text hash mismatch for {cell_key}")
        if catalogs[locale].get(source["source"]) != source["currentTarget"]:
            fail(f"catalog current value differs from exact input pin: {cell_key}")
        if source["placeholderEvidence"].get("matches") is not True or source["markupEvidence"].get("matches") is not True:
            fail(f"source/current placeholder or markup check failed: {cell_key}")
        if cross["checks"].get("cross") != {"placeholderParity": True, "markupParity": True, "numericParity": True, "protectedLiteralsPresent": True}:
            fail(f"cross candidate structural/protected-literal checks failed: {cell_key}")
        if primary["candidateTarget"] != cross["primary"]["candidateTarget"] or primary["verdict"] != cross["primary"]["verdict"] or primary["rationale"] != cross["primary"]["rationale"]:
            fail(f"cross-audit primary recommendation differs from sealed primary ledger: {cell_key}")
        if blind["candidateTarget"] != cross["blind"]["candidateTarget"] or blind["verdict"] != cross["blind"]["verdict"] or blind["rationale"] != cross["blind"]["rationale"]:
            fail(f"cross-audit blind recommendation differs from sealed blind ledger: {cell_key}")
        if primary["candidateTargetSha256"] != sha(primary["candidateTarget"]) or blind["candidateTargetSha256"] != sha(blind["candidateTarget"]):
            fail(f"review candidate text hash mismatch: {cell_key}")
        if adjudication["candidateTargetSha256"] != sha(adjudication["candidateTarget"]):
            fail(f"cross-adjudicated candidate text hash mismatch: {cell_key}")
        if cross["comparison"].get("candidateTextAgrees") != (primary["candidateTarget"] == blind["candidateTarget"]):
            fail(f"candidate disagreement indicator mismatch: {cell_key}")
        if cross["comparison"].get("verdictAgrees") != (primary["verdict"] == blind["verdict"]):
            fail(f"disposition disagreement indicator mismatch: {cell_key}")
        candidate_text_disagreements += primary["candidateTarget"] != blind["candidateTarget"]
        verdict_disagreements += primary["verdict"] != blind["verdict"]
        has_disagreement = primary["candidateTarget"] != blind["candidateTarget"] or primary["verdict"] != blind["verdict"]
        disagreement_cells += has_disagreement
        primary_changes += primary["candidateTarget"] != source["currentTarget"]
        blind_changes += blind["candidateTarget"] != source["currentTarget"]
        cross_changes += adjudication["candidateTarget"] != source["currentTarget"] and adjudication["verdict"] in ("correction", "refinement")

        verdict = adjudication["verdict"]
        target = adjudication["candidateTarget"]
        if verdict == "accept-current":
            if target != source["currentTarget"]:
                fail(f"accept-current disposition changes target: {cell_key}")
            action = "keep-current"
        elif verdict in ("correction", "refinement"):
            if target == source["currentTarget"]:
                fail(f"winner is a no-op: {cell_key}")
            action = "apply-candidate"
            per_locale_changes[locale] += 1
            apply_rows.append({
                "continuationRank": source["continuationRank"], "sourceId": source_id, "source": source["source"],
                "sourceSha256": source["sourceSha256"], "locale": locale, "catalogPath": source["catalogPath"],
                "catalogFileSha256": source["catalogFileSha256"], "catalogGitBlob": source["catalogGitBlob"],
                "oldTarget": source["currentTarget"], "oldTargetSha256": source["currentTargetSha256"],
                "newTarget": target, "newTargetSha256": sha(target), "disposition": verdict,
                "rationale": adjudication["rationale"], "crossResolution": adjudication["resolution"],
            })
        elif verdict == "hold-terminology":
            if target != source["currentTarget"]:
                fail(f"terminology hold changes target: {cell_key}")
            action = "hold-current"
            hold_rows.append({
                "continuationRank": source["continuationRank"], "sourceId": source_id, "source": source["source"],
                "locale": locale, "catalogPath": source["catalogPath"], "currentTarget": source["currentTarget"],
                "disposition": verdict, "rationale": adjudication["rationale"],
            })
        else:
            fail(f"unknown cross disposition {verdict!r} at {cell_key}")
        dispositions[verdict] += 1
        root_rows.append({
            "continuationRank": source["continuationRank"], "historicalSourceOrdinal": source.get("historicalSourceOrdinal"),
            "sourceId": source_id, "source": source["source"], "sourceSha256": source["sourceSha256"],
            "locale": locale, "catalogPath": source["catalogPath"], "catalogFileSha256": source["catalogFileSha256"],
            "catalogGitBlob": source["catalogGitBlob"], "currentTarget": source["currentTarget"],
            "currentTargetSha256": source["currentTargetSha256"], "callerContextSha256": source["callerContextSha256"],
            "callerRefs": source["callerRefs"],
            "primaryRecommendation": {"verdict": primary["verdict"], "candidateTarget": primary["candidateTarget"],
                                      "candidateTargetSha256": primary["candidateTargetSha256"], "rationale": primary["rationale"]},
            "blindRecommendation": {"verdict": blind["verdict"], "candidateTarget": blind["candidateTarget"],
                                    "candidateTargetSha256": blind["candidateTargetSha256"], "rationale": blind["rationale"]},
            "reviewComparison": cross["comparison"],
            "thirdPartyAdjudication": adjudication,
            "rootDecision": {"disposition": verdict, "target": target, "targetSha256": sha(target), "action": action,
                             "rationale": adjudication["rationale"], "basis": "adopted cross-audited exact candidate after independent pin/checksum and ledger-consistency validation"},
            "protectedPlaceholderMarkupNumericChecks": cross["checks"]["cross"],
        })
    if (candidate_text_disagreements, verdict_disagreements, disagreement_cells) != (15, 2, 15):
        fail("recomputed primary/blind disagreement counts do not match the sealed cross-audit summary")
    if dict(dispositions) != {"accept-current": 193, "correction": 59, "refinement": 12, "hold-terminology": 36}:
        fail(f"unexpected cross-adjudicated counts: {dict(dispositions)}")
    if (primary_changes, blind_changes, cross_changes) != (70, 71, 71):
        fail("recomputed candidate-change counts do not match all three review summaries")
    if (len(apply_rows), len(hold_rows), verified_caller_refs) != (71, 36, 40):
        fail("unexpected apply, hold, or caller-reference count")
    if not cross_summary.get("unresolvedDisagreementCount") == 0:
        fail("cross-audit reports unresolved recommendation disagreements")

    write_jsonl(ROOT_REVIEW / "root-adjudication.jsonl", root_rows)
    write_jsonl(APPLICATION / "apply-plan.jsonl", apply_rows)
    write_jsonl(ROOT_REVIEW / "holds.jsonl", hold_rows)
    ledger_sha = sha((ROOT_REVIEW / "root-adjudication.jsonl").read_bytes())
    summary = {
        "repository": "snapetech-org/slskdN", "pullRequest": 409, "window": "W55", "branch": BRANCH,
        "baseHead": BASE_HEAD, "baseTree": BASE_TREE, "remoteBranchHeadAtAdjudication": BASE_HEAD,
        "pinnedPrBodySha256": attestation["bodySha256"], "sourceRanks": [276, 300], "sourceCount": 25,
        "localeOrder": LOCALES, "localeCount": 12, "reviewedCells": len(root_rows), "callerReferenceCount": verified_caller_refs,
        "primaryCandidateChanges": primary_changes, "blindCandidateChanges": blind_changes, "crossAdjudicatedCandidateChanges": cross_changes,
        "primaryBlindCandidateTextDisagreements": candidate_text_disagreements,
        "primaryBlindDispositionDisagreements": verdict_disagreements, "cellsWithAnyDisagreement": disagreement_cells,
        "unresolvedDisagreements": 0, "rootDispositions": dict(sorted(dispositions.items())),
        "applyPlanRows": len(apply_rows), "applyChangesByLocale": dict(sorted(per_locale_changes.items())),
        "holdRows": len(hold_rows), "holdRanks": [278, 282, 289],
        "currentProtectedLiteralMismatchCount": cross_summary["currentProtectedLiteralMismatchCount"],
        "currentNumericMismatchCount": cross_summary["currentNumericMismatchCount"],
        "candidateProtectedLiteralMismatchCount": cross_summary["crossProtectedCandidateMismatchCount"],
        "candidateNumericMismatchCount": cross_summary["crossNumericCandidateMismatchCount"],
        "placeholderMismatchCount": cross_summary["placeholderMismatchCount"], "markupMismatchCount": cross_summary["markupMismatchCount"],
        "catalogCount": len(catalog_meta), "catalogKeysPerLocale": KEY_COUNT, "orderedCatalogKeySha256": ORDER_HASH,
        "catalogPins": {locale: {"path": catalog_meta[locale]["catalogPath"], "rawSha256": catalog_meta[locale]["sha256"],
                                  "gitBlob": catalog_meta[locale]["gitBlob"], "orderedKeySha256": catalog_meta[locale]["orderedKeySha256"]}
                        for locale in LOCALES},
        "sourcePacketChecksums": {"primaryRootManifestSha256": primary_root_manifest_sha, "inputManifestSha256": input_manifest_sha,
                                   "primaryManifestSha256": primary_manifest_sha, "blindManifestSha256": blind_manifest_sha,
                                   "crossAuditManifestSha256": cross_manifest_sha, "verifiedManifestEntries": manifest_counts},
        "rootLedgerSha256": ledger_sha, "nativeSpeakerApproval": False, "headedProductBrowserAcceptance": False,
        "testsBuildsScansCiRun": False, "workflowsChanged": False,
    }
    write_json(ROOT_REVIEW / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
