#!/usr/bin/env python3
"""Build candidate-free exact-head source/catalog/caller inputs for W78."""
import collections
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path(sys.argv[1] if len(sys.argv) > 1 else "/mnt/disks/scratch/task-worktrees/localization-20261104/slskdn-pr409-w78-828-852-source").resolve()
PREV = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w77-803-827-primary-20261104/candidate-free/input")
W77_CROSS_HOLDS = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w77-cross-20261104/holds-hash-only.jsonl")
HEAD = "4120c9637e71466dc98d51a5a342dee199a1e004"
TREE = "063b62f268eb81253d2b9b4c77ad045c2f25a394"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
INV_PATH = "docs/pr-evidence/pr409-localization-2026-11-03/window49/primary/source-inventory.jsonl"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
FIRST, LAST = 828, 852


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text_sha(value):
    return sha(value.encode("utf-8"))


def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(name, rows):
    with (ROOT / name).open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def placeholder_tokens(value):
    return collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", value))


def markup_tokens(value):
    return collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", value))


def numeric_tokens(value):
    output = []
    for match in re.findall(r"\d+", value):
        normalized = "".join(str(unicodedata.digit(ch)) if ch.isdigit() else ch for ch in match)
        output.append(normalized)
    return output


def protected_literals(value):
    tokens = set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", value))
    tokens.update(token for token in ("slskdN", "Tor", "Wishlist", "Chromaprint") if token in value)
    return sorted(tokens)


def prod_source_path(path):
    parts = path.split("/")
    name = parts[-1]
    suffix = Path(name).suffix.lower()
    if not path.startswith("src/web/src/") or suffix not in {".js", ".jsx", ".ts", ".tsx"}:
        return False
    if any(part in {"__tests__", "__specs__"} for part in parts):
        return False
    if any(marker in name for marker in (".test.", ".spec.")):
        return False
    if name.endswith((".test.js", ".test.jsx", ".test.ts", ".test.tsx", ".spec.js", ".spec.jsx", ".spec.ts", ".spec.tsx")):
        return False
    return True


def refs_for_source(source, runtime_files):
    pattern = re.compile(r"(?<![A-Za-z0-9_$])([\"'])" + re.escape(source) + r"\1")
    found = []
    for record in runtime_files:
        rel = record["path"]
        data = (REPO / rel).read_bytes()
        if sha(data) != record["sha256"]:
            raise SystemExit("runtime file changed while scanning: " + rel)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        lines = text.splitlines()
        for number, line in enumerate(lines, 1):
            if not pattern.search(line):
                continue
            context = [{"line": index + 1, "text": lines[index]}
                       for index in range(max(0, number - 4), min(len(lines), number + 2))]
            found.append({
                "path": rel, "line": number, "lineText": line,
                "lineSha256": text_sha(line), "context": context,
                "contextSha256": sha(canonical(context)), "fileBytes": len(data),
                "fileSha256": sha(data), "gitBlob": record["gitBlob"],
                "gitBlobSha1Check": blob_sha(data)
            })
    return found


def refs_hash_only(refs):
    return [{key: ref[key] for key in ("path", "line", "lineSha256", "contextSha256", "fileSha256", "gitBlob")}
            for ref in refs]


def sum_not_less(source, target):
    source_counts, target_counts = collections.Counter(source), collections.Counter(target)
    return all(target_counts[token] >= count for token, count in source_counts.items())


def main():
    if git("rev-parse", "HEAD").decode().strip() != HEAD:
        raise SystemExit("REFUSED: worktree is not at the pinned W78 head")
    if git("rev-parse", "HEAD^{tree}").decode().strip() != TREE:
        raise SystemExit("REFUSED: worktree tree differs from the pinned W77 tree")
    if git("status", "--porcelain=v1").decode().strip():
        raise SystemExit("REFUSED: isolated worktree is not clean")
    if not PREV.is_dir():
        raise SystemExit("REFUSED: prior candidate-free input is missing")

    inventory_raw = git("show", f"{HEAD}:{INV_PATH}")
    if inventory_raw != (REPO / INV_PATH).read_bytes():
        raise SystemExit("REFUSED: pinned source inventory differs from checkout")
    inventory = [json.loads(line) for line in inventory_raw.decode("utf-8").splitlines() if line.strip()]
    if len(inventory) != 6176:
        raise SystemExit("REFUSED: source inventory entry count")
    inventory_by_rank = {row["continuationRank"]: row for row in inventory if row.get("continuationRank") is not None}
    selected = [inventory_by_rank[rank] for rank in range(FIRST, LAST + 1)]
    if len(selected) != 25 or any(row.get("excluded") or row.get("localeCoverage") != 12 for row in selected):
        raise SystemExit("REFUSED: rank selection includes excluded or incomplete source")
    if [row["remainingQueueRank"] for row in selected] != list(range(728, 753)):
        raise SystemExit("REFUSED: remaining queue ranks differ from W78 expectation")

    prior_exclusions_path = PREV / "prior-selected-id-exclusions-hash-only.jsonl"
    prior_exclusions = read_jsonl(prior_exclusions_path)
    previous_selected = read_jsonl(PREV / "source-inventory-selection.jsonl")
    w77_manifest = read_json(PREV / "manifest.json")
    if (w77_manifest.get("window"), w77_manifest.get("head"), w77_manifest.get("tree")) != (
        "W77", "582ae64e5c3af275490f11f4350b33da7373a3c3", "b8692bb066cede93b6668806d0b97816135ce647"
    ):
        raise SystemExit("REFUSED: W77 candidate-free predecessor pin")
    w77_selection = read_json(PREV / "selection-and-boundary.json")
    if w77_selection.get("nextUnselectedContinuationRank") != FIRST or w77_selection.get("nextUnselectedSourceId") != selected[0]["sourceId"]:
        raise SystemExit("REFUSED: W77 continuation pointer does not match W78 first row")
    if len(previous_selected) != 25:
        raise SystemExit("REFUSED: W77 selection coverage")
    w77_id_rows = []
    for row in previous_selected:
        w77_id_rows.append({
            "sourceId": row["sourceId"], "sourceIdSha256": text_sha(row["sourceId"]),
            "sourceSha256": row["sourceSha256"], "selectionOrigin": "W77 candidate-free continuation selection",
            "continuationRank": row["continuationRank"], "remainingQueueRank": row["remainingQueueRank"],
            "exclusionConfirmed": True, "sourceTextIncluded": False, "targetTextIncluded": False,
            "selectionEvidenceSha256": sha((PREV / "selection-and-boundary.json").read_bytes())
        })
    prior_exclusions.extend(w77_id_rows)
    prior_exclusions.sort(key=lambda row: row["sourceId"])
    prior_exclusions_raw = b"".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
        for row in prior_exclusions
    )
    (ROOT / "previous-window-selection-hash-only.jsonl").write_bytes(
        b"".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
                 for row in sorted(w77_id_rows, key=lambda row: row["sourceId"]))
    )

    previous_holds = read_jsonl(PREV / "prior-held-cell-reattestation-hash-only.jsonl")
    w77_caller_rows = read_jsonl(PREV / "caller-contexts.jsonl")
    w77_callers_by_rank = {row["continuationRank"]: row for row in w77_caller_rows}
    w77_cross_holds = read_jsonl(W77_CROSS_HOLDS)
    if len(w77_cross_holds) != 12 or {row["continuationRank"] for row in w77_cross_holds} != {814}:
        raise SystemExit("REFUSED: W77 cross hold set is not the sealed 12-cell callerless set")
    w77_previous_cells = {(row["continuationRank"], row["locale"]): row
                          for row in read_jsonl(PREV / "source-current-cells.jsonl")}
    for row in w77_cross_holds:
        caller = w77_callers_by_rank[row["continuationRank"]]
        refs = refs_hash_only(caller["callers"])
        if (row["window"] != "W77" or row["holdReasonCode"] != "CALLERLESS_TEXT_FREE_HOLD" or
                row["productionCallerCount"] != 0 or row["sourceId"] != caller["sourceId"] or
                row["callerContextSha256"] != sha(canonical(refs))):
            raise SystemExit("REFUSED: W77 hold identity/caller pin")
        previous_cell = w77_previous_cells[(row["continuationRank"], row["locale"])]
        if (previous_cell["currentTargetSha256"] != row["currentTargetSha256"] or
                row["catalogFileSha256"] != previous_cell["catalogFileSha256"] or
                row["catalogGitBlob"] != previous_cell["catalogGitBlob"] or
                row["catalogPath"] != previous_cell["catalogPath"] or len(refs) != 0):
            raise SystemExit("REFUSED: W77 hold target is not anchored to candidate-free input")
        previous_holds.append({
            "priorWindow": "W77", "continuationRank": row["continuationRank"],
            "sourceId": row["sourceId"], "sourceIdSha256": text_sha(row["sourceId"]),
            "sourceSha256": row["sourceSha256"], "locale": row["locale"], "priorDisposition": "hold",
            "priorTargetSha256": row["currentTargetSha256"], "holdReasonSha256": sha(row["holdReasonCode"].encode("utf-8")),
            "crossRationaleSha256": sha(canonical({"holdReasonCode": row["holdReasonCode"], "productionCallerCount": 0})),
            "priorCallerCount": len(refs), "priorCallerContextSha256": row["callerContextSha256"],
            "priorCallerRefs": refs, "currentCallerCount": len(refs),
            "currentCallerContextSha256": row["callerContextSha256"], "currentCallerRefs": refs,
            "callerEvidenceUnchanged": True, "currentTargetSha256": row["currentTargetSha256"],
            "matchesPriorCurrentValue": True, "sourceTextIncluded": False, "targetTextIncluded": False
        })
    previous_resolutions_raw = (PREV / "prior-hold-resolution-history-hash-only.jsonl").read_bytes()
    previous_resolutions = [json.loads(line) for line in previous_resolutions_raw.decode().splitlines() if line.strip()]
    previous_summary = read_json(PREV / "prior-hold-lineage-summary.json")
    previous_summary["carriedHoldCells"] = len(previous_holds)
    previous_summary["holdLineage"] = dict(previous_summary["holdLineage"])
    previous_summary["holdLineage"]["W77"] = len(w77_cross_holds)
    previous_manifest_raw = (PREV / "manifest.json").read_bytes()
    previous_checksums_raw = (PREV / "PACKET-SHA256SUMS.txt").read_bytes()
    if len(prior_exclusions) != 1907 or len(previous_holds) != 331 or len(previous_resolutions) != 13:
        raise SystemExit("REFUSED: prior continuity counts do not match sealed W77 candidate-free and cross hold inputs")
    prior_ids = {row["sourceId"] for row in prior_exclusions}
    if len(prior_ids) != len(prior_exclusions) or prior_ids.intersection(row["sourceId"] for row in selected):
        raise SystemExit("REFUSED: W77 selection overlaps prior selected source IDs")
    for row in prior_exclusions:
        if any(field in row for field in ("source", "sourceText", "target", "currentTarget", "proposedTarget")):
            raise SystemExit("REFUSED: prior selected-ID ledger contains text")
        current = next((item for item in inventory if item["sourceId"] == row["sourceId"]), None)
        if not current or current["sourceSha256"] != row["sourceSha256"]:
            raise SystemExit("REFUSED: prior selected source hash differs from current inventory")

    # Read all twelve exact catalogs and bind their ordered structure to the pinned Git tree.
    catalogs, catalog_rows = {}, []
    ordered_keys = None
    tree_listing = git("ls-tree", "-r", "-z", HEAD)
    tree_entries = {}
    for entry in tree_listing.split(b"\0"):
        if not entry:
            continue
        meta, path_bytes = entry.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        tree_entries[path_bytes.decode("utf-8")] = {"mode": mode, "type": kind, "gitBlob": oid}
    for locale in LOCALES:
        path = f"src/web/public/locales/{locale}.json"
        data = git("show", f"{HEAD}:{path}")
        if data != (REPO / path).read_bytes():
            raise SystemExit("REFUSED: locale catalog differs from exact head: " + path)
        obj = json.loads(data.decode("utf-8"))
        keys = list(obj)
        if ordered_keys is None:
            ordered_keys = keys
        if keys != ordered_keys or len(keys) != 6176 or any(not isinstance(value, str) or not value for value in obj.values()):
            raise SystemExit("REFUSED: catalog structure or coverage: " + path)
        catalogs[locale] = obj
        catalog_rows.append({
            "locale": locale, "catalogPath": path, "bytes": len(data), "sha256": sha(data),
            "gitBlob": tree_entries[path]["gitBlob"], "entryCount": len(keys),
            "nonemptyValueCount": sum(bool(value) for value in obj.values()),
            "orderedKeySha256": sha(("\n".join(keys) + "\n").encode("utf-8"))
        })
    key_order_hash = sha(("\n".join(ordered_keys) + "\n").encode("utf-8"))

    # Record every tracked production JS/TS file in the bounded caller-scan domain.
    runtime_files = []
    for path, entry in sorted(tree_entries.items()):
        if not prod_source_path(path):
            continue
        data = (REPO / path).read_bytes()
        expected_blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if expected_blob != entry["gitBlob"]:
            raise SystemExit("REFUSED: production caller file differs from pinned Git blob: " + path)
        runtime_files.append({"path": path, "bytes": len(data), "sha256": sha(data), "gitBlob": entry["gitBlob"]})
    if len(runtime_files) != 279:
        raise SystemExit(f"REFUSED: expected 279 bounded production files, found {len(runtime_files)}")

    selected_ids = {row["sourceId"] for row in selected}
    prior_hold_ids = {row["sourceId"] for row in previous_holds}
    prior_resolution_ids = {row["sourceId"] for row in previous_resolutions}
    sources_to_pin = selected_ids | prior_hold_ids | prior_resolution_ids
    source_by_id = {row["sourceId"]: row for row in inventory}
    full_refs = {source_id: refs_for_source(source_by_id[source_id]["source"], runtime_files) for source_id in sorted(sources_to_pin)}

    caller_context_rows = []
    for source_row in selected:
        sid = source_row["sourceId"]
        refs = full_refs[sid]
        caller_context_rows.append({
            "continuationRank": source_row["continuationRank"],
            "remainingQueueRank": source_row["remainingQueueRank"],
            "sourceId": sid, "source": source_row["source"], "sourceSha256": source_row["sourceSha256"],
            "productionCallerCount": len(refs),
            "boundedScan": "Exact single- or double-quoted source literal scan of pinned src/web/src JS/TS runtime files; test/spec files excluded by file naming and __tests__/__specs__ directories.",
            "callers": refs
        })

    # Hash-only continuity reattestation for active holds and historical resolutions.
    prior_hold_rows, prior_resolution_rows = [], []
    held_status_counts = collections.Counter()
    for old in previous_holds:
        sid, locale = old["sourceId"], old["locale"]
        source = source_by_id.get(sid)
        if not source or source["sourceSha256"] != old["sourceSha256"] or locale not in catalogs:
            raise SystemExit("REFUSED: prior held source identity cannot be reattested")
        target_hash = text_sha(catalogs[locale][source["source"]])
        refs = full_refs[sid]
        caller_hash = sha(canonical(refs))
        unchanged = caller_hash == old["currentCallerContextSha256"]
        matches = target_hash == old["priorTargetSha256"]
        status = "reattested-unchanged" if unchanged and matches else "reattested-context-or-target-changed"
        held_status_counts[status] += 1
        prior_hold_rows.append({
            "priorWindow": old["priorWindow"], "continuationRank": old["continuationRank"],
            "sourceId": sid, "sourceIdSha256": old["sourceIdSha256"], "sourceSha256": old["sourceSha256"],
            "locale": locale, "priorDisposition": old["priorDisposition"],
            "priorTargetSha256": old["priorTargetSha256"], "currentTargetSha256": target_hash,
            "matchesPriorCurrentValue": matches, "holdReasonSha256": old["holdReasonSha256"],
            "priorCallerCount": old["currentCallerCount"], "priorCallerContextSha256": old["currentCallerContextSha256"],
            "priorCallerRefs": old["currentCallerRefs"], "currentCallerCount": len(refs),
            "currentCallerContextSha256": caller_hash, "currentCallerRefs": refs_hash_only(refs),
            "callerEvidenceUnchanged": unchanged,
            "currentCatalogPath": f"src/web/public/locales/{locale}.json",
            "currentCatalogFileSha256": next(row["sha256"] for row in catalog_rows if row["locale"] == locale),
            "currentCatalogGitBlob": next(row["gitBlob"] for row in catalog_rows if row["locale"] == locale),
            "status": status, "sourceTextIncluded": False, "targetTextIncluded": False
        })
    for old in previous_resolutions:
        sid, locale = old["sourceId"], old["locale"]
        source = source_by_id.get(sid)
        if not source or source["sourceSha256"] != old["sourceSha256"] or locale not in catalogs:
            raise SystemExit("REFUSED: historical hold resolution cannot be reattested")
        refs = full_refs[sid]
        target_hash = text_sha(catalogs[locale][source["source"]])
        row = dict(old)
        row.update({
            "currentTargetSha256": target_hash, "currentTargetMatchesResolution": target_hash == old["resolvedTargetSha256"],
            "currentCallerCount": len(refs), "currentCallerContextSha256": sha(canonical(refs)),
            "currentCallerRefs": refs_hash_only(refs),
            "currentCatalogPath": f"src/web/public/locales/{locale}.json",
            "currentCatalogFileSha256": next(record["sha256"] for record in catalog_rows if record["locale"] == locale),
            "currentCatalogGitBlob": next(record["gitBlob"] for record in catalog_rows if record["locale"] == locale),
            "sourceTextIncluded": False, "formerTargetTextIncluded": False,
            "resolvedTargetTextIncluded": False, "currentTargetTextIncluded": False
        })
        prior_resolution_rows.append(row)

    # Candidate-free current cells include only the observed source, current target, caller pins, and token parity.
    current_cells = []
    mismatch_counts = collections.Counter()
    mismatch_examples = []
    for source_row in selected:
        sid, source = source_row["sourceId"], source_row["source"]
        refs = full_refs[sid]
        compact_refs = refs_hash_only(refs)
        caller_hash = sha(canonical(refs))
        for locale in LOCALES:
            current = catalogs[locale][source]
            source_ph, current_ph = placeholder_tokens(source), placeholder_tokens(current)
            source_markup, current_markup = markup_tokens(source), markup_tokens(current)
            source_nums, current_nums = numeric_tokens(source), numeric_tokens(current)
            source_protected, current_protected = protected_literals(source), protected_literals(current)
            missing_protected = [token for token in source_protected if token not in current]
            ph_ok = source_ph == current_ph
            markup_ok = source_markup == current_markup
            numeric_ok = sum_not_less(source_nums, current_nums)
            protected_ok = not missing_protected
            for name, ok in (("placeholder", ph_ok), ("markup", markup_ok), ("numeric", numeric_ok), ("protectedLiteral", protected_ok)):
                if not ok:
                    mismatch_counts[name] += 1
                    mismatch_examples.append({"continuationRank": source_row["continuationRank"], "sourceId": sid, "locale": locale, "kind": name})
            catalog_record = next(record for record in catalog_rows if record["locale"] == locale)
            current_cells.append({
                "continuationRank": source_row["continuationRank"], "remainingQueueRank": source_row["remainingQueueRank"],
                "sourceId": sid, "source": source, "sourceSha256": source_row["sourceSha256"],
                "catalogKey": source, "locale": locale, "catalogPath": catalog_record["catalogPath"],
                "catalogFileSha256": catalog_record["sha256"], "catalogGitBlob": catalog_record["gitBlob"],
                "currentTarget": current, "currentTargetSha256": text_sha(current),
                "callerContextSha256": caller_hash, "callerRefs": compact_refs,
                "placeholderEvidence": {"sourceTokens": sorted(source_ph.elements()), "currentTokens": sorted(current_ph.elements()), "matches": ph_ok},
                "markupEvidence": {"sourceTags": sorted(source_markup.elements()), "currentTags": sorted(current_markup.elements()), "matches": markup_ok},
                "sourceNumericTokens": source_nums, "currentNumericTokens": current_nums, "numericTokensPreserved": numeric_ok,
                "sourceProtectedLiterals": source_protected, "currentProtectedLiterals": [token for token in source_protected if token in current],
                "missingProtectedLiterals": missing_protected,
                "protectedLiteralEvidence": {"sourceTokens": source_protected, "currentTokens": [token for token in source_protected if token in current], "matches": protected_ok},
                "containsCandidate": False, "verdict": None
            })

    # Verify the exact continuation boundary and carry prior files without any translation text.
    previous_boundary = inventory_by_rank[827]
    next_boundary = inventory_by_rank[853]
    boundary = [{**previous_boundary, "boundaryRole": "previous-window-final"}]
    boundary.extend({**row, "boundaryRole": "selected-window"} for row in selected)
    boundary.append({**next_boundary, "boundaryRole": "next-unselected"})
    selected_rows = [dict(row) for row in selected]
    for row in selected_rows:
        row["excluded"] = False
    if (selected[0]["sourceId"] != "src_30f0dd08d39c6d5e" or
            previous_boundary["sourceId"] != "src_30e4834932cfcf4d" or
            next_boundary["continuationRank"] != 853):
        raise SystemExit("REFUSED: W77/W78 continuation boundary changed")

    # Write sealed candidate-free artifacts (the manifest and checksum list are written by seal_input.py).
    (ROOT / "source-inventory-pinned.jsonl").write_bytes(inventory_raw)
    write_jsonl("source-inventory-selection.jsonl", selected_rows)
    write_jsonl("selection-boundary.jsonl", boundary)
    write_jsonl("catalog-structure.jsonl", catalog_rows)
    write_jsonl("runtime-file-pins.jsonl", runtime_files)
    write_jsonl("caller-contexts.jsonl", caller_context_rows)
    write_jsonl("source-current-cells.jsonl", current_cells)
    write_jsonl("prior-held-cell-reattestation-hash-only.jsonl", prior_hold_rows)
    write_jsonl("prior-hold-resolution-history-hash-only.jsonl", prior_resolution_rows)
    (ROOT / "prior-selected-id-exclusions-hash-only.jsonl").write_bytes(prior_exclusions_raw)
    write_json("prior-hold-lineage-summary.json", previous_summary)
    (ROOT / "previous-window-input-manifest.json").write_bytes(previous_manifest_raw)
    (ROOT / "previous-window-input-checksums.txt").write_bytes(previous_checksums_raw)
    write_jsonl("previous-window-prior-holds-hash-only.jsonl", previous_holds)
    (ROOT / "previous-window-hold-resolutions-hash-only.jsonl").write_bytes(previous_resolutions_raw)

    write_json("prior-held-cell-reattestation-summary.json", {
        "priorHeldCellsReattested": len(prior_hold_rows),
        "allTargetHashesMatchPrior": all(row["matchesPriorCurrentValue"] for row in prior_hold_rows),
        "callerEvidenceUnchanged": sum(row["callerEvidenceUnchanged"] for row in prior_hold_rows),
        "callerEvidenceChanged": sum(not row["callerEvidenceUnchanged"] for row in prior_hold_rows),
        "statusCounts": dict(held_status_counts), "holdRowsTextFree": True
    })
    write_json("baseline-token-mismatch-summary.json", {
        "cellCount": len(current_cells), "mismatchCellCount": sum(mismatch_counts.values()),
        "mismatchCounts": {key: mismatch_counts.get(key, 0) for key in ("placeholder", "markup", "numeric", "protectedLiteral")},
        "mismatchExamples": mismatch_examples
    })
    write_json("continuity-provenance.json", {
        "previousWindow": "W77", "previousHead": "582ae64e5c3af275490f11f4350b33da7373a3c3",
        "previousTree": "b8692bb066cede93b6668806d0b97816135ce647",
        "previousCandidateFreeManifestSha256": sha(previous_manifest_raw),
        "previousCandidateFreeChecksumListSha256": sha(previous_checksums_raw),
        "priorSelectedIdExclusionRows": len(prior_exclusions), "priorHeldCells": len(previous_holds),
        "priorResolvedHoldHistoryRows": len(previous_resolutions),
        "priorSelectedIdsSha256": sha(prior_exclusions_raw),
        "priorHoldInputSha256": sha((ROOT / "previous-window-prior-holds-hash-only.jsonl").read_bytes()),
        "priorResolutionInputSha256": sha(previous_resolutions_raw),
        "w77CrossHoldInputSha256": sha(W77_CROSS_HOLDS.read_bytes()),
        "w77SelectedIdInputSha256": sha((ROOT / "previous-window-selection-hash-only.jsonl").read_bytes()),
        "previousCrossHoldRows": len(w77_cross_holds),
        "previousPrimaryProposalTargetsUsed": False,
        "priorPrimaryReviewUsed": False, "blindReviewUsed": False, "crossReviewUsed": False
    })
    write_json("selection-and-boundary.json", {
        "repository": "snapetech-org/slskdN", "pullRequest": 409, "window": "W78",
        "branch": BRANCH, "head": HEAD, "tree": TREE, "candidateFree": True,
        "locales": LOCALES, "sourceCount": 25, "cellCount": 300,
        "continuationRankRange": [FIRST, LAST], "remainingQueueRankRange": [728, 752],
        "previousWindow": "W77", "previousWindowFinalContinuationRank": 827,
        "previousWindowFinalSourceId": previous_boundary["sourceId"],
        "nextUnselectedContinuationRank": 853, "nextUnselectedSourceId": next_boundary["sourceId"],
        "orderedCatalogKeySha256": key_order_hash,
        "catalogEntryCountPerLocale": len(ordered_keys), "priorSelectedIdsExcluded": len(prior_exclusions),
        "priorHeldCellsReattested": len(prior_hold_rows), "priorHoldResolutionHistoryRows": len(prior_resolution_rows),
        "proposedTargetsIncluded": False, "reviewDecisionsIncluded": False
    })
    write_json("source-tree-attestation.json", {
        "head": HEAD, "tree": TREE, "sourceRoot": "src/web/src", "treeEnumeration": "git ls-tree -r -z at exact pinned commit",
        "treeEntryCount": len(tree_entries), "productionFileCount": len(runtime_files),
        "callerScan": "exact single- or double-quoted source literal scan",
        "testAndSpecFilesExcluded": True,
        "runtimeFilePinsSha256": sha((ROOT / "runtime-file-pins.jsonl").read_bytes())
    })
    print(json.dumps({
        "result": "BUILT-CANDIDATE-FREE-UNSEALED", "head": HEAD, "tree": TREE,
        "sourceCount": len(selected), "localeCount": len(LOCALES), "cellCount": len(current_cells),
        "runtimeFiles": len(runtime_files), "sourcesWithCallers": sum(bool(row["productionCallerCount"]) for row in caller_context_rows),
        "sourcesWithoutCallers": sum(not row["productionCallerCount"] for row in caller_context_rows),
        "priorSelectedIds": len(prior_exclusions), "priorHeldCells": len(prior_hold_rows),
        "priorResolutionHistory": len(prior_resolution_rows), "tokenMismatches": dict(mismatch_counts),
        "note": "live-after attestation and final seal are still required"
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
