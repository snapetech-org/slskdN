#!/usr/bin/env python3
"""Verify candidate-free W76 input, exact source/catalog/caller pins, and continuity."""
import argparse
import collections
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEAD = "674156749ee86021ef91d896b1824be62cff9a93"
TREE = "86483dbf9227130cade6a3f4c9dc9ef5cf232450"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
INV_PATH = "docs/pr-evidence/pr409-localization-2026-11-03/window49/primary/source-inventory.jsonl"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
TEXT_FIELDS_FORBIDDEN = {"sourceText", "target", "currentTarget", "proposedTarget", "resolvedTarget", "formerTargetText", "resolvedTargetText"}


def fail(message):
    raise SystemExit("FAIL: " + message)


def need(condition, message):
    if not condition:
        fail(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text_sha(value):
    return sha(value.encode("utf-8"))


def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(name):
    return [json.loads(line) for line in (ROOT / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def placeholder_tokens(value):
    return collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", value))


def markup_tokens(value):
    return collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", value))


def numeric_tokens(value):
    output = []
    for match in re.findall(r"\d+", value):
        output.append("".join(str(unicodedata.digit(ch)) if ch.isdigit() else ch for ch in match))
    return output


def protected_literals(value):
    tokens = set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", value))
    tokens.update(token for token in ("slskdN", "Tor", "Wishlist", "Chromaprint") if token in value)
    return sorted(tokens)


def sum_not_less(source, target):
    source_counts, target_counts = collections.Counter(source), collections.Counter(target)
    return all(target_counts[token] >= count for token, count in source_counts.items())


def refs_hash_only(refs):
    return [{key: ref[key] for key in ("path", "line", "lineSha256", "contextSha256", "fileSha256", "gitBlob")}
            for ref in refs]


def scan_refs(source, runtime_files, repo):
    pattern = re.compile(r"(?<![A-Za-z0-9_$])([\"'])" + re.escape(source) + r"\1")
    found = []
    for record in runtime_files:
        data = (repo / record["path"]).read_bytes()
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        lines = content.splitlines()
        for number, line in enumerate(lines, 1):
            if not pattern.search(line):
                continue
            context = [{"line": index + 1, "text": lines[index]}
                       for index in range(max(0, number - 4), min(len(lines), number + 2))]
            found.append({
                "path": record["path"], "line": number, "lineText": line,
                "lineSha256": text_sha(line), "context": context,
                "contextSha256": sha(canonical(context)), "fileBytes": len(data),
                "fileSha256": sha(data), "gitBlob": record["gitBlob"],
                "gitBlobSha1Check": blob_sha(data)
            })
    return found


def verify_file_inventory():
    manifest = read_json(ROOT / "manifest.json")
    expected_paths = {item["path"] for item in manifest["files"]}
    need(len(expected_paths) == len(manifest["files"]), "duplicate manifest file")
    need(not ({"manifest.json", "PACKET-SHA256SUMS.txt"} & expected_paths), "recursive manifest entry")
    for item in manifest["files"]:
        path = (ROOT / item["path"]).resolve()
        need(path.is_relative_to(ROOT.resolve()) and path.is_file(), f"missing or unsafe file: {item['path']}")
        data = path.read_bytes()
        need(len(data) == item["bytes"] and sha(data) == item["sha256"], f"manifest digest mismatch: {item['path']}")
    actual_paths = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*")
                    if path.is_file() and path.name not in {"manifest.json", "PACKET-SHA256SUMS.txt"}}
    need(actual_paths == expected_paths, "manifest file set differs from candidate-free input directory")
    checksum_entries = {}
    for number, line in enumerate((ROOT / "PACKET-SHA256SUMS.txt").read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        need(name not in checksum_entries, f"duplicate checksum path at line {number}")
        checksum_entries[name] = digest
        path = (ROOT / name).resolve()
        need(path.is_relative_to(ROOT.resolve()) and path.is_file() and sha(path.read_bytes()) == digest,
             f"checksum mismatch: {name}")
    need(set(checksum_entries) == expected_paths | {"manifest.json"}, "checksum inventory mismatch")
    need(checksum_entries["manifest.json"] == sha((ROOT / "manifest.json").read_bytes()), "manifest checksum missing")
    return manifest, len(checksum_entries)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True, help="clean checkout/worktree at the pinned PR head")
    args = parser.parse_args()
    repo = args.repo.resolve()

    manifest, checksum_count = verify_file_inventory()
    need(manifest.get("candidateFree") is True and manifest.get("head") == HEAD and manifest.get("tree") == TREE,
         "candidate-free manifest pin")
    need(manifest.get("window") == "W76" and manifest.get("repository") == "snapetech-org/slskdN", "window/repository")
    need(manifest.get("proposedTargetsIncluded") is False and manifest.get("reviewDecisionsIncluded") is False,
         "candidate-free purity flags")
    need(manifest.get("blindReviewUsed") is False and manifest.get("crossReviewUsed") is False,
         "blind/cross output was used in candidate-free pass")
    need(git(repo, "rev-parse", "HEAD") == HEAD and git(repo, "rev-parse", "HEAD^{tree}") == TREE,
         "local repository head/tree differs from pin")
    need(not git(repo, "status", "--porcelain=v1"), "pinned worktree is dirty")
    head_attestation = read_json(ROOT / "head-tree-attestation.json")
    before, after = read_json(ROOT / "live-before.json"), read_json(ROOT / "live-after.json")
    need(head_attestation["liveBefore"] == before and head_attestation["liveAfter"] == after, "live attestation linkage")
    for live in (before, after):
        need((live["state"], live["draft"], live["merged"], live["headRefOid"], live["branchRefOid"], live["pullRefOid"]) ==
             ("OPEN", True, False, HEAD, HEAD, HEAD), "PR/branch/pull ref state")
        need((live["baseRefName"], live["baseRefOid"], live["headRefName"]) ==
             ("main", "f25d263a2a7cdb2c8f76c40c346cb10f749a9356", BRANCH), "PR base/head ref")
    stable_fields = ("state", "draft", "merged", "headRefOid", "branchRefOid", "pullRefOid", "baseRefOid", "headRefName")
    need(all(before[field] == after[field] for field in stable_fields), "PR state/ref changed during input capture")
    remote_text = subprocess.check_output([
        "git", "ls-remote", "https://github.com/snapetech-org/slskdN.git",
        f"refs/heads/{BRANCH}", "refs/pull/409/head"
    ], text=True)
    remote = {line.split()[1]: line.split()[0] for line in remote_text.splitlines() if line.strip()}
    need(remote.get(f"refs/heads/{BRANCH}") == HEAD and remote.get("refs/pull/409/head") == HEAD,
         "current remote branch/pull refs no longer match the attested pin")

    inventory_raw = subprocess.check_output(["git", "-C", str(repo), "show", f"{HEAD}:{INV_PATH}"])
    need(inventory_raw == (repo / INV_PATH).read_bytes(), "source inventory differs from pinned Git blob")
    need(sha(inventory_raw) == manifest["sourceInventorySha256"], "source inventory digest")
    inventory = [json.loads(line) for line in inventory_raw.decode("utf-8").splitlines() if line.strip()]
    need(len(inventory) == manifest["sourceInventoryRows"] == 6176, "source inventory row count")
    source_by_id = {row["sourceId"]: row for row in inventory}
    need(len(source_by_id) == 6176, "source ID uniqueness")
    for row in inventory:
        need(row["sourceId"] == "src_" + text_sha(row["source"])[:16] and row["sourceSha256"] == text_sha(row["source"]),
             f"source ID/hash mismatch: {row['sourceId']}")

    tree_raw = subprocess.check_output(["git", "-C", str(repo), "ls-tree", "-r", "-z", HEAD])
    tree_entries = {}
    for entry in tree_raw.split(b"\0"):
        if not entry:
            continue
        meta, path_bytes = entry.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        tree_entries[path_bytes.decode("utf-8")] = {"mode": mode, "type": kind, "gitBlob": oid}
    source_tree = read_json(ROOT / "source-tree-attestation.json")
    runtime_files = rows("runtime-file-pins.jsonl")
    need(source_tree["head"] == HEAD and source_tree["tree"] == TREE, "runtime source-tree pin")
    need(source_tree["treeEntryCount"] == len(tree_entries) and source_tree["productionFileCount"] == len(runtime_files) == 279,
         "runtime source-tree counts")
    need(source_tree["runtimeFilePinsSha256"] == sha((ROOT / "runtime-file-pins.jsonl").read_bytes()), "runtime file pin-list hash")
    need(len({row["path"] for row in runtime_files}) == len(runtime_files), "runtime file path uniqueness")
    for row in runtime_files:
        data = (repo / row["path"]).read_bytes()
        need(row["path"] in tree_entries and tree_entries[row["path"]]["gitBlob"] == row["gitBlob"],
             f"runtime file Git blob mismatch: {row['path']}")
        need(len(data) == row["bytes"] and sha(data) == row["sha256"] and blob_sha(data) == row["gitBlob"],
             f"runtime file bytes/hash mismatch: {row['path']}")

    catalog_rows = rows("catalog-structure.jsonl")
    need([row["locale"] for row in catalog_rows] == LOCALES, "locale catalog order")
    catalogs, ordered_keys = {}, None
    for row in catalog_rows:
        path = row["catalogPath"]
        need(path == f"src/web/public/locales/{row['locale']}.json", f"catalog path: {row['locale']}")
        raw = subprocess.check_output(["git", "-C", str(repo), "show", f"{HEAD}:{path}"])
        need(raw == (repo / path).read_bytes() and sha(raw) == row["sha256"] and len(raw) == row["bytes"],
             f"catalog file bytes/hash: {row['locale']}")
        need(tree_entries[path]["gitBlob"] == row["gitBlob"], f"catalog Git blob: {row['locale']}")
        catalog = json.loads(raw.decode("utf-8"))
        keys = list(catalog)
        ordered_keys = keys if ordered_keys is None else ordered_keys
        need(keys == ordered_keys and len(keys) == row["entryCount"] == row["nonemptyValueCount"] == 6176,
             f"catalog ordered key coverage: {row['locale']}")
        need(sha(("\n".join(keys) + "\n").encode("utf-8")) == row["orderedKeySha256"], f"catalog key hash: {row['locale']}")
        catalogs[row["locale"]] = catalog
    ordered_hash = sha(("\n".join(ordered_keys) + "\n").encode("utf-8"))
    need(ordered_hash == manifest["orderedCatalogKeySha256"], "ordered catalog key hash")

    selected = rows("source-inventory-selection.jsonl")
    boundary = rows("selection-boundary.jsonl")
    selection = read_json(ROOT / "selection-and-boundary.json")
    expected_selected = [row for row in inventory if row.get("continuationRank") in range(778, 803)]
    need(len(selected) == len(expected_selected) == 25 and selected == expected_selected, "selection rows do not match pinned inventory")
    need([row["continuationRank"] for row in selected] == list(range(778, 803)), "continuation rank sequence")
    need([row["remainingQueueRank"] for row in selected] == list(range(678, 703)), "queue rank sequence")
    need(len(boundary) == 27 and boundary[0]["boundaryRole"] == "previous-window-final" and
         boundary[-1]["boundaryRole"] == "next-unselected", "selection boundary count/roles")
    need([row["boundaryRole"] for row in boundary[1:-1]] == ["selected-window"] * 25, "selected boundary roles")
    need(boundary[0]["continuationRank"] == 777 and boundary[-1]["continuationRank"] == 803, "boundary ranks")
    need(selection["continuationRankRange"] == [778, 802] and selection["remainingQueueRankRange"] == [678, 702], "selection summary ranks")
    need(selection["previousWindowFinalSourceId"] == boundary[0]["sourceId"] and
         selection["nextUnselectedSourceId"] == boundary[-1]["sourceId"], "selection boundary IDs")

    prior_ids = rows("prior-selected-id-exclusions-hash-only.jsonl")
    prior_holds = rows("prior-held-cell-reattestation-hash-only.jsonl")
    prior_resolutions = rows("prior-hold-resolution-history-hash-only.jsonl")
    previous_holds = rows("previous-window-prior-holds-hash-only.jsonl")
    previous_resolutions = rows("previous-window-hold-resolutions-hash-only.jsonl")
    continuity = read_json(ROOT / "continuity-provenance.json")
    need(len(prior_ids) == len({row["sourceId"] for row in prior_ids}) == 1857, "prior selected-ID count")
    need(len(prior_holds) == len(previous_holds) == 271 and len(prior_resolutions) == len(previous_resolutions) == 13,
         "prior hold lineage counts")
    need(sha((ROOT / "prior-selected-id-exclusions-hash-only.jsonl").read_bytes()) == continuity["priorSelectedIdsSha256"],
         "prior selected-ID input hash")
    need(sha((ROOT / "previous-window-prior-holds-hash-only.jsonl").read_bytes()) == continuity["priorHoldInputSha256"],
         "prior hold input hash")
    need(sha((ROOT / "previous-window-hold-resolutions-hash-only.jsonl").read_bytes()) == continuity["priorResolutionInputSha256"],
         "prior resolution input hash")
    for row in prior_ids:
        need(not (TEXT_FIELDS_FORBIDDEN & set(row)) and row.get("sourceTextIncluded") is False and row.get("targetTextIncluded") is False,
             "prior selected ID ledger contains text")
        source = source_by_id.get(row["sourceId"])
        need(source and source["sourceSha256"] == row["sourceSha256"], f"prior source hash changed: {row['sourceId']}")
    selected_ids = {row["sourceId"] for row in selected}
    need(not selected_ids & {row["sourceId"] for row in prior_ids}, "selected source overlaps prior selection")

    # Re-run the exact quoted-literal scan and verify all current selected and carried caller evidence.
    source_ids_to_scan = selected_ids | {row["sourceId"] for row in prior_holds} | {row["sourceId"] for row in prior_resolutions}
    caller_map = {sid: scan_refs(source_by_id[sid]["source"], runtime_files, repo) for sid in sorted(source_ids_to_scan)}
    caller_contexts = rows("caller-contexts.jsonl")
    need(len(caller_contexts) == 25 and {row["sourceId"] for row in caller_contexts} == selected_ids, "caller-context source coverage")
    for row in caller_contexts:
        expected_refs = caller_map[row["sourceId"]]
        need(row["callers"] == expected_refs and row["productionCallerCount"] == len(expected_refs),
             f"caller scan mismatch: {row['sourceId']}")
    current_cells = rows("source-current-cells.jsonl")
    need(len(current_cells) == 300, "current cell count")
    locales_by_rank = [(row["continuationRank"], row["locale"]) for row in current_cells]
    need(len(set(locales_by_rank)) == 300 and set(locales_by_rank) == {(rank, locale) for rank in range(778, 803) for locale in LOCALES},
         "source/locale cell coverage")
    selected_by_id = {row["sourceId"]: row for row in selected}
    mismatch_counts = collections.Counter()
    for row in current_cells:
        source = selected_by_id.get(row["sourceId"])
        need(source is not None and row["continuationRank"] == source["continuationRank"] and row["source"] == source["source"],
             f"current cell source identity: {row['sourceId']}/{row['locale']}")
        need(row["sourceSha256"] == text_sha(row["source"]), f"current source hash: {row['sourceId']}")
        target = catalogs[row["locale"]].get(row["catalogKey"])
        need(isinstance(target, str) and row["catalogKey"] == row["source"] and target == row["currentTarget"],
             f"current locale catalog target: {row['sourceId']}/{row['locale']}")
        need(row["currentTargetSha256"] == text_sha(target), f"current target hash: {row['sourceId']}/{row['locale']}")
        catalog = next(item for item in catalog_rows if item["locale"] == row["locale"])
        need(row["catalogPath"] == catalog["catalogPath"] and row["catalogFileSha256"] == catalog["sha256"] and
             row["catalogGitBlob"] == catalog["gitBlob"], f"cell catalog pin: {row['sourceId']}/{row['locale']}")
        refs = caller_map[row["sourceId"]]
        need(row["callerContextSha256"] == sha(canonical(refs)) and row["callerRefs"] == refs_hash_only(refs),
             f"cell caller pin: {row['sourceId']}/{row['locale']}")
        source_ph, current_ph = placeholder_tokens(row["source"]), placeholder_tokens(target)
        source_markup, current_markup = markup_tokens(row["source"]), markup_tokens(target)
        source_numeric, current_numeric = numeric_tokens(row["source"]), numeric_tokens(target)
        source_protected, missing = protected_literals(row["source"]), [token for token in protected_literals(row["source"]) if token not in target]
        checks = {
            "placeholder": source_ph == current_ph,
            "markup": source_markup == current_markup,
            "numeric": sum_not_less(source_numeric, current_numeric),
            "protectedLiteral": not missing
        }
        need(row["placeholderEvidence"] == {"sourceTokens": sorted(source_ph.elements()), "currentTokens": sorted(current_ph.elements()), "matches": checks["placeholder"]},
             f"placeholder evidence: {row['sourceId']}/{row['locale']}")
        need(row["markupEvidence"] == {"sourceTags": sorted(source_markup.elements()), "currentTags": sorted(current_markup.elements()), "matches": checks["markup"]},
             f"markup evidence: {row['sourceId']}/{row['locale']}")
        need(row["sourceNumericTokens"] == source_numeric and row["currentNumericTokens"] == current_numeric and row["numericTokensPreserved"] == checks["numeric"],
             f"numeric evidence: {row['sourceId']}/{row['locale']}")
        need(row["sourceProtectedLiterals"] == source_protected and row["missingProtectedLiterals"] == missing and
             row["protectedLiteralEvidence"]["matches"] == checks["protectedLiteral"],
             f"protected literal evidence: {row['sourceId']}/{row['locale']}")
        need(row.get("containsCandidate") is False and row.get("verdict") is None and not any(k in row for k in ("candidateTarget", "proposedTarget", "reviewDecision")),
             f"candidate/review content in input: {row['sourceId']}/{row['locale']}")
        for name, ok in checks.items():
            if not ok:
                mismatch_counts[name] += 1
    token_summary = read_json(ROOT / "baseline-token-mismatch-summary.json")
    expected_token_counts = {key: mismatch_counts.get(key, 0) for key in ("placeholder", "markup", "numeric", "protectedLiteral")}
    need(token_summary["mismatchCounts"] == expected_token_counts and token_summary["cellCount"] == 300,
         "baseline token summary")

    for row in prior_holds:
        source = source_by_id.get(row["sourceId"])
        need(source is not None and row["sourceSha256"] == source["sourceSha256"], "prior held source hash")
        need(not (TEXT_FIELDS_FORBIDDEN & set(row)) and row.get("sourceTextIncluded") is False and row.get("targetTextIncluded") is False,
             "prior held row contains text")
        target = catalogs[row["locale"]][source["source"]]
        refs = caller_map[row["sourceId"]]
        need(row["currentTargetSha256"] == text_sha(target) and row["matchesPriorCurrentValue"] == (row["priorTargetSha256"] == text_sha(target)),
             f"prior held target hash: {row['sourceId']}/{row['locale']}")
        need(row["currentCallerCount"] == len(refs) and row["currentCallerContextSha256"] == sha(canonical(refs)) and
             row["currentCallerRefs"] == refs_hash_only(refs), f"prior held current caller pin: {row['sourceId']}/{row['locale']}")
        need(all("lineText" not in ref and "context" not in ref for ref in row["currentCallerRefs"]), "prior held caller text included")
    for row in prior_resolutions:
        source = source_by_id.get(row["sourceId"])
        need(source is not None and not (TEXT_FIELDS_FORBIDDEN & set(row)), "resolved history contains text")
        target = catalogs[row["locale"]][source["source"]]
        refs = caller_map[row["sourceId"]]
        need(row["currentTargetSha256"] == text_sha(target) and row["currentCallerContextSha256"] == sha(canonical(refs)) and
             row["currentCallerRefs"] == refs_hash_only(refs), f"resolved history current pin: {row['sourceId']}/{row['locale']}")
    hold_summary = read_json(ROOT / "prior-held-cell-reattestation-summary.json")
    need(hold_summary["priorHeldCellsReattested"] == 271 and hold_summary["holdRowsTextFree"] is True,
         "prior hold summary")
    need(hold_summary["callerEvidenceUnchanged"] + hold_summary["callerEvidenceChanged"] == 271,
         "prior hold caller-change summary")

    print(json.dumps({
        "result": "PASS", "head": HEAD, "tree": TREE, "window": "W76",
        "sourceCount": 25, "localeCount": 12, "cellCount": len(current_cells),
        "catalogs": len(catalog_rows), "catalogEntriesPerLocale": 6176,
        "runtimeFilesPinned": len(runtime_files), "selectedSourcesWithCallers": sum(bool(row["productionCallerCount"]) for row in caller_contexts),
        "callerlessSelectedSources": sum(not row["productionCallerCount"] for row in caller_contexts),
        "priorSelectedIdsHashOnly": len(prior_ids), "priorHeldCellsHashOnly": len(prior_holds),
        "priorHoldResolutionsHashOnly": len(prior_resolutions),
        "priorHeldTargetHashesMatch": hold_summary["allTargetHashesMatchPrior"],
        "priorHeldCallerEvidenceUnchanged": hold_summary["callerEvidenceUnchanged"],
        "priorHeldCallerEvidenceChanged": hold_summary["callerEvidenceChanged"],
        "tokenMismatchCounts": expected_token_counts, "checksums": checksum_count
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
