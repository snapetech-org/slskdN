#!/usr/bin/env python3
"""Build a candidate-free W82 source/catalog packet at the pinned PR head."""
import collections
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path(sys.argv[1]).resolve()
HEAD = "6e48a342d4b1c43918c23da3afcbaad19c87a005"
TREE = "b82ea7937cf9aa141a1c952283d5549dbe116ba5"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
MAIN = "bc6251ff4ea5a7e59f2d86e2400c90520601f46e"
FIRST, LAST = 928, 952
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
W81 = REPO / "docs/pr-evidence/pr409-localization-2026-11-05/window-903-927/candidate-free"
PREV = W81
W81_PRIMARY = REPO / "docs/pr-evidence/pr409-localization-2026-11-05/window-903-927/primary-review"
W81_APP = REPO / "docs/pr-evidence/pr409-localization-2026-11-05/window-903-927/application"
W910_APP = REPO / "docs/pr-evidence/pr409-localization-2026-11-05/rank-910-richtext-followup/application"
W49_INV = "docs/pr-evidence/pr409-localization-2026-11-03/window49/primary/source-inventory.jsonl"
W910_PRODUCT = "1e33696072e322d98827c022c4432a57a76be2db"
TEXT_KEYS = {"source", "sourceText", "target", "currentTarget", "proposedTarget", "proposedTargetText", "reason", "resolvedTarget", "resolvedTargetText", "formerTargetText"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tsha(value):
    return sha(value.encode("utf-8"))


def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(name, rows):
    with (ROOT / name).open("w", encoding="utf-8", newline="\n") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate catalog key: " + key)
        out[key] = value
    return out


def production_path(path):
    parts = path.split("/")
    suffix = Path(path).suffix.lower()
    name = parts[-1]
    return (path.startswith("src/web/src/") and suffix in {".js", ".jsx", ".ts", ".tsx"}
            and not any(part in {"__tests__", "__specs__"} for part in parts)
            and not any(token in name for token in (".test.", ".spec.")))


def capture_live():
    pr = json.loads(subprocess.check_output(["gh", "api", "repos/snapetech-org/slskdN/pulls/409"]))
    branch_ref = json.loads(subprocess.check_output(["gh", "api", "repos/snapetech-org/slskdN/git/ref/heads/" + BRANCH]))
    main_commit = json.loads(subprocess.check_output(["gh", "api", "repos/snapetech-org/slskdN/commits/main"]))
    remote = subprocess.check_output(["git", "-C", str(REPO), "ls-remote", "origin", "refs/pull/409/head", "refs/heads/main"], text=True)
    remote_refs = {line.split()[1]: line.split()[0] for line in remote.splitlines() if line.strip()}
    result = {
        "repository": "snapetech-org/slskdN", "pullRequest": 409,
        "state": pr["state"], "draft": pr["draft"], "merged": pr["merged"],
        "baseRef": pr["base"]["ref"], "baseSha": pr["base"]["sha"],
        "headRef": pr["head"]["ref"], "headSha": pr["head"]["sha"],
        "headTree": git("rev-parse", HEAD + "^{tree}").decode().strip(),
        "branchRefSha": branch_ref["object"]["sha"],
        "pullRefSha": remote_refs.get("refs/pull/409/head"),
        "remoteMainSha": remote_refs.get("refs/heads/main"),
        "apiMainSha": main_commit["sha"], "apiMainTree": main_commit["commit"]["tree"]["sha"],
        "capturedAtHead": HEAD, "prBodyContentIncluded": False,
    }
    if result["headRef"] != BRANCH or result["headSha"] != HEAD or result["headTree"] != TREE:
        raise SystemExit("REFUSED: live PR head/tree changed")
    if result["branchRefSha"] != HEAD or result["pullRefSha"] != HEAD:
        raise SystemExit("REFUSED: live branch/pull ref mismatch")
    if result["baseRef"] != "main" or result["remoteMainSha"] != MAIN or result["apiMainSha"] != MAIN:
        raise SystemExit("REFUSED: live main changed")
    return result


def scan_sources(sources, runtime):
    refs_by_source = {source: [] for source in sources}
    for rec in runtime:
        data = (REPO / rec["path"]).read_bytes()
        if sha(data) != rec["sha256"] or blob_sha(data) != rec["gitBlob"]:
            raise SystemExit("REFUSED: runtime file pin changed: " + rec["path"])
        text = data.decode("utf-8")
        lines = text.splitlines()
        for source in sources:
            literal = re.compile(r"(?<![A-Za-z0-9_$])([\"'])" + re.escape(source) + r"\1")
            for idx, line in enumerate(lines):
                if not literal.search(line):
                    continue
                context = [{"line": n + 1, "text": lines[n]} for n in range(max(0, idx - 4), min(len(lines), idx + 3))]
                refs_by_source[source].append({
                    "path": rec["path"], "line": idx + 1, "lineText": line,
                    "lineSha256": tsha(line), "context": context, "contextSha256": sha(canon(context)),
                    "fileBytes": len(data), "fileSha256": sha(data), "gitBlob": rec["gitBlob"],
                })
    return refs_by_source


def hash_refs(refs):
    return [{k: ref[k] for k in ("path", "line", "lineSha256", "contextSha256", "fileSha256", "gitBlob")} for ref in refs]


def token_data(source, target):
    placeholders = lambda s: collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", s))
    tags = lambda s: collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", s))
    nums = lambda s: ["".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in token) for token in re.findall(r"\d+", s)]
    protected = lambda s: sorted(set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", s)) | {x for x in ("slskdN", "PodCore", "Wishlist", "soulfind", "FFmpeg") if x in s})
    source_placeholders, target_placeholders = placeholders(source), placeholders(target)
    source_tags, target_tags = tags(source), tags(target)
    source_nums, target_nums = nums(source), nums(target)
    source_protected, target_protected = protected(source), protected(target)
    missing_protected = [literal for literal in source_protected if literal not in target]
    return {
        "placeholders": {"source": sorted(source_placeholders.elements()), "target": sorted(target_placeholders.elements()), "matches": source_placeholders == target_placeholders},
        "markup": {"source": sorted(source_tags.elements()), "target": sorted(target_tags.elements()), "matches": source_tags == target_tags},
        "numbers": {"source": source_nums, "target": target_nums, "sourcePreserved": all(target_nums.count(x) >= n for x, n in collections.Counter(source_nums).items())},
        "protectedLiterals": {"source": source_protected, "target": target_protected, "missing": missing_protected},
    }


def main():
    if git("rev-parse", "HEAD").decode().strip() != HEAD or git("rev-parse", "HEAD^{tree}").decode().strip() != TREE:
        raise SystemExit("REFUSED: wrong pinned worktree")
    if git("status", "--porcelain=v1").decode().strip():
        raise SystemExit("REFUSED: worktree is not clean")
    live = capture_live()
    predecessor_sums = {}
    for line in (PREV / "PACKET-SHA256SUMS.txt").read_text().splitlines():
        digest, name = line.split("  ", 1)
        if not (PREV / name).is_file() or sha((PREV / name).read_bytes()) != digest:
            raise SystemExit("REFUSED: W81 predecessor checksum " + name)
        predecessor_sums[name] = digest
    expected_predecessor = {p.relative_to(PREV).as_posix() for p in PREV.rglob("*")
                            if p.is_file() and p.name != "PACKET-SHA256SUMS.txt"}
    if set(predecessor_sums) != expected_predecessor:
        raise SystemExit("REFUSED: W81 predecessor packet inventory")

    main_names = subprocess.check_output(["git", "-C", str(REPO), "diff", "--name-status", HEAD + "..." + MAIN, "--", "src/web/src", "src/web/public/locales"], text=True)
    drift_rows = []
    for line in main_names.splitlines():
        status, path = line.split("\t", 1)
        drift_rows.append({"status": status, "path": path})
    write_json("live-before.json", live)
    write_json("main-drift.json", {"head": HEAD, "main": MAIN, "localizationAndRuntimePathChangesOnMain": drift_rows,
                                    "catalogPathChanges": [r for r in drift_rows if r["path"].startswith("src/web/public/locales/")],
                                    "callerPathChanges": [r for r in drift_rows if r["path"].startswith("src/web/src/")],
                                    "mainWasNotMerged": True})

    tree = {}
    for item in git("ls-tree", "-r", "-z", HEAD).split(b"\0"):
        if not item:
            continue
        meta, raw_path = item.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        tree[raw_path.decode()] = {"mode": mode, "kind": kind, "gitBlob": oid}

    catalogs, catalog_rows, ordered = {}, [], None
    for locale in LOCALES:
        path = f"src/web/public/locales/{locale}.json"
        data = git("show", f"{HEAD}:{path}")
        if data != (REPO / path).read_bytes():
            raise SystemExit("REFUSED: local catalog differs from pinned HEAD: " + locale)
        obj = json.loads(data.decode("utf-8"), object_pairs_hook=no_duplicates)
        keys = list(obj)
        if len(keys) != 6175 or any(not isinstance(value, str) or not value for value in obj.values()):
            raise SystemExit("REFUSED: malformed catalog or coverage: " + locale)
        if ordered is None:
            ordered = keys
        elif keys != ordered:
            raise SystemExit("REFUSED: ordered locale keys differ: " + locale)
        catalogs[locale] = obj
        catalog_rows.append({"locale": locale, "path": path, "bytes": len(data), "sha256": sha(data),
                             "gitBlob": tree[path]["gitBlob"], "entryCount": len(keys),
                             "orderedKeySha256": sha(("\n".join(keys) + "\n").encode())})

    current_by_id = {"src_" + tsha(key)[:16]: key for key in ordered}
    if len(current_by_id) != len(ordered):
        raise SystemExit("REFUSED: source ID collision")
    baseline = read_jsonl(PREV / "source-inventory-pinned.jsonl")
    baseline_by_id = {row["sourceId"]: row for row in baseline}
    if len(baseline) != 6176 or len(baseline_by_id) != 6176:
        raise SystemExit("REFUSED: predecessor stable inventory")
    current_ids, baseline_ids = set(current_by_id), set(baseline_by_id)
    additions, retirements = sorted(current_ids - baseline_ids), sorted(baseline_ids - current_ids)
    expected_additions = ["src_41daa09c736a103b", "src_84420341dbb4e4a4", "src_c04ff600b79f3317"]
    expected_retirements = ["src_16d9b529ed6a96b4", "src_2c367aa22044c2c6", "src_2d4bc8b68054a858", "src_34419b72f6ec2d1e"]
    if additions != expected_additions or retirements != expected_retirements:
        raise SystemExit("REFUSED: unexpected source inventory delta")

    mapping = {
        "src_2c367aa22044c2c6": ("src_84420341dbb4e4a4", "W74 reviewed source rewrite", "b5311aea5", "src/web/src/components/System/Security/AdversarialSettings.jsx"),
        "src_2d4bc8b68054a858": ("src_41daa09c736a103b", "W74 reviewed source rewrite", "b5311aea5", "src/web/src/components/System/Shares/ContentsModal.jsx"),
        "src_16d9b529ed6a96b4": ("src_c04ff600b79f3317", "W910 reviewed rich-text source rewrite", W910_PRODUCT, "src/web/src/components/System/MediaCore/MediaCorePods.jsx"),
        "src_34419b72f6ec2d1e": ("src_c04ff600b79f3317", "W910 reviewed rich-text source rewrite", W910_PRODUCT, "src/web/src/components/System/MediaCore/MediaCorePods.jsx"),
    }
    w49 = {row["sourceId"]: row for row in read_jsonl(REPO / W49_INV)}
    rewrite_rows = []
    for old_id in retirements:
        previous = baseline_by_id[old_id]
        if old_id not in w49 or previous["sourceSha256"] != w49[old_id]["sourceSha256"]:
            raise SystemExit("REFUSED: source rewrite old identity")
        new_id, reason, commit_prefix, source_path = mapping[old_id]
        commit = git("rev-parse", commit_prefix + "^{commit}").decode().strip()
        old_source = w49[old_id]["source"]
        before = git("show", f"{commit}^:{source_path}")
        after = git("show", f"{commit}:{source_path}")
        new_source = current_by_id[new_id]
        if old_source.encode("utf-8") not in before or new_source.encode("utf-8") not in after:
            raise SystemExit("REFUSED: source rewrite commit does not pin expected old/new source")
        if commit == W910_PRODUCT and old_source.encode("utf-8") in after:
            raise SystemExit("REFUSED: retired W910 fragment remains in caller")
        rewrite_rows.append({"event": "retired-source-id", "oldSourceId": old_id, "oldSourceIdSha256": tsha(old_id),
                             "oldSourceSha256": previous["sourceSha256"], "oldContinuationRank": previous.get("continuationRank"),
                             "oldRemainingQueueRank": previous.get("remainingQueueRank"), "replacementSourceId": new_id,
                             "replacementSourceSha256": tsha(current_by_id[new_id]), "reason": reason,
                             "evidenceCommit": commit, "sourceFilePath": source_path,
                             "sourceFileBeforeSha256": sha(before), "sourceFileAfterSha256": sha(after),
                             "sourceTextIncluded": False, "targetTextIncluded": False})
    replacement_ranks = collections.defaultdict(list)
    for old_id in retirements:
        replacement_ranks[mapping[old_id][0]].append(baseline_by_id[old_id].get("continuationRank"))
    for new_id in additions:
        new_ranks = sorted(r for r in replacement_ranks[new_id] if r is not None)
        rewrite_rows.append({"event": "already-reviewed-replacement-source-id", "sourceId": new_id,
                             "sourceIdSha256": tsha(new_id), "sourceSha256": tsha(current_by_id[new_id]),
                             "priorContinuationRanks": new_ranks, "rankAssigned": False,
                             "reason": "replacement for source text previously reviewed in its rank; excluded from fresh queue",
                             "sourceTextIncluded": False, "targetTextIncluded": False})
    for row in rewrite_rows:
        sid = row.get("replacementSourceId", row.get("sourceId"))
        if sid not in current_by_id:
            raise SystemExit("REFUSED: source rewrite replacement absent")
    write_jsonl("source-inventory-reconciliation.jsonl", rewrite_rows)

    prior = read_jsonl(PREV / "prior-selected-id-exclusions-hash-only.jsonl")
    prev_selection = read_jsonl(PREV / "source-inventory-selection.jsonl")
    prior.extend({"sourceId": row["sourceId"], "sourceIdSha256": tsha(row["sourceId"]),
                  "sourceSha256": row["sourceSha256"], "selectionOrigin": "W81 selected source ID",
                  "continuationRank": row["continuationRank"], "remainingQueueRank": row["remainingQueueRank"],
                  "exclusionConfirmed": True, "sourceTextIncluded": False, "targetTextIncluded": False}
                 for row in prev_selection)
    rewrite_exclusions = []
    for new_id in additions:
        rewrite_exclusions.append({"sourceId": new_id, "sourceIdSha256": tsha(new_id),
                                   "sourceSha256": tsha(current_by_id[new_id]),
                                   "selectionOrigin": "previously reviewed source rewrite replacement",
                                   "exclusionConfirmed": True, "sourceTextIncluded": False, "targetTextIncluded": False})
    prior.extend(rewrite_exclusions)
    prior_by_id = {row["sourceId"]: row for row in prior}
    if len(prior_by_id) != len(prior):
        raise SystemExit("REFUSED: duplicate prior selected source ID")
    for row in prior:
        if any(key in TEXT_KEYS for key in row):
            raise SystemExit("REFUSED: source or target text in prior ID lineage")

    ranked = {}
    inventory_rows = []
    for sid in sorted(current_ids):
        key = current_by_id[sid]
        old = baseline_by_id.get(sid)
        if old:
            if old["sourceSha256"] != tsha(key):
                raise SystemExit("REFUSED: retained stable source hash changed")
            rank = old.get("continuationRank")
            queue = old.get("remainingQueueRank")
            baseline_excluded = old.get("excluded", False)
        else:
            rank = queue = None
            baseline_excluded = True
        if rank is not None:
            ranked[rank] = sid
        inventory_rows.append({"sourceId": sid, "sourceSha256": tsha(key), "continuationRank": rank,
                               "remainingQueueRank": queue, "baselineExcluded": baseline_excluded,
                               "priorSelectedOrRewriteExcluded": sid in prior_by_id,
                               "eligibleForFreshWindow": rank is not None and not baseline_excluded and sid not in prior_by_id,
                               "localeCoverage": 12, "sourceTextIncluded": False})
    if len(ranked) != len(set(ranked)) or len(ranked) != 4967:
        raise SystemExit("REFUSED: current ranked inventory count/uniqueness")
    selected = []
    for rank in range(FIRST, LAST + 1):
        sid = ranked.get(rank)
        if not sid or sid not in current_by_id:
            raise SystemExit("REFUSED: current rank missing: " + str(rank))
        selected.append({"continuationRank": rank, "remainingQueueRank": rank - 100, "sourceId": sid,
                         "sourceSha256": tsha(current_by_id[sid]), "source": current_by_id[sid]})
    previous_boundary = {"continuationRank": 927, "remainingQueueRank": 827, "sourceId": ranked[927],
                         "sourceSha256": tsha(current_by_id[ranked[927]])}
    next_boundary = {"continuationRank": 953, "remainingQueueRank": 853, "sourceId": ranked[953],
                     "sourceSha256": tsha(current_by_id[ranked[953]])}
    write_jsonl("source-inventory-pinned.jsonl", inventory_rows)
    write_jsonl("source-inventory-selection.jsonl", [{k: row[k] for k in ("continuationRank", "remainingQueueRank", "sourceId", "sourceSha256")} for row in selected])
    write_jsonl("selected-sources.jsonl", selected)
    write_jsonl("prior-selected-id-exclusions-hash-only.jsonl", sorted(prior, key=lambda row: row["sourceId"]))
    write_json("selection-and-boundary.json", {"repository": "snapetech-org/slskdN", "pullRequest": 409, "window": "W82",
                "branch": BRANCH, "head": HEAD, "tree": TREE, "candidateFree": True, "locales": LOCALES,
                "sourceCount": 25, "cellCount": 300, "continuationRankRange": [FIRST, LAST],
                "remainingQueueRankRange": [828, 852], "previousWindow": "W81 plus W910 source rewrite follow-up",
                "previousWindowFinalRank": previous_boundary, "nextUnselected": next_boundary,
                "sourceInventoryRows": len(inventory_rows), "stableRankedRows": len(ranked),
                "retiredStableRankRows": [185, 732, 750, 910], "sourceRewriteReplacementIdsExcluded": additions,
                "orderedCatalogKeySha256": sha(("\n".join(ordered) + "\n").encode()),
                "catalogEntryCountPerLocale": 6175, "priorSelectedAndRewriteIdsExcluded": len(prior_by_id),
                "proposedTargetsIncluded": False, "reviewDecisionsIncluded": False})

    runtime = []
    for path, entry in sorted(tree.items()):
        if not production_path(path):
            continue
        data = (REPO / path).read_bytes()
        if blob_sha(data) != entry["gitBlob"]:
            raise SystemExit("REFUSED: runtime blob mismatch: " + path)
        runtime.append({"path": path, "bytes": len(data), "sha256": sha(data), "gitBlob": entry["gitBlob"]})
    if len(runtime) != 279:
        raise SystemExit("REFUSED: production runtime file count")

    previous_holds = read_jsonl(PREV / "previous-window-prior-holds-hash-only.jsonl")
    previous_resolutions = read_jsonl(PREV / "prior-hold-resolution-history-hash-only.jsonl")
    w81_new_holds = read_jsonl(W81_PRIMARY / "review-holds.jsonl")
    w81_applied = read_jsonl(W81_APP / "application-plan.jsonl")
    old_applied = read_jsonl(PREV / "prior-applied-targets-reattestation-hash-only.jsonl")
    w910_plan = read_jsonl(W910_APP / "catalog-product-plan.json") if False else [json.loads(x) for x in (W910_APP / "catalog-product-plan.json").read_text().splitlines() if x.strip()]
    w910_product = json.loads((W910_APP / "product-commit.json").read_text())
    w910_source = json.loads((W910_APP / "source-product-readback.json").read_text())
    if len(previous_holds) != 382 or len(w81_new_holds) != 12 or len(w81_applied) != 64 or len(old_applied) != 190 or len(w910_plan) != 12:
        raise SystemExit("REFUSED: predecessor lineage counts")
    if w910_product.get("commit") != W910_PRODUCT or w910_product.get("selectedTargetsMatchRootHashes") is not True:
        raise SystemExit("REFUSED: W910 source/catalog root selection proof")
    new_source_id = w910_source["sourceId"]
    if new_source_id != "src_c04ff600b79f3317" or new_source_id not in current_by_id:
        raise SystemExit("REFUSED: W910 replacement source identity")
    w910_product_commit = w910_product["commit"]
    w81_product = json.loads((W81_APP / "product-commit.json").read_text())
    w81_product_commit = w81_product.get("commit")
    if w81_product.get("commit") != "868f93ef2ec8a242ff65d5da6f438633fc0fc152" or len(w81_product.get("files", [])) != 12:
        raise SystemExit("REFUSED: W81 product application proof")

    # Collect the exact current sources needed for selected callers and hold history.
    hold_source_ids = {row["sourceId"] for row in previous_holds}
    resolution_source_ids = {row["sourceId"] for row in previous_resolutions}
    selected_source_ids = {row["sourceId"] for row in selected}
    rewrite_current_ids = set(additions)
    scan_ids = selected_source_ids | hold_source_ids | (resolution_source_ids & current_ids) | rewrite_current_ids
    source_texts_to_scan = {current_by_id[sid] for sid in scan_ids}
    source_texts_to_scan.update(w49[row["sourceId"]]["source"] for row in w81_new_holds)
    refs_by_source = scan_sources(source_texts_to_scan, runtime)
    caller_rows, selected_cells = [], []
    source_by_id = {row["sourceId"]: row for row in selected}
    for row in selected:
        refs = refs_by_source[row["source"]]
        caller_rows.append({"continuationRank": row["continuationRank"], "remainingQueueRank": row["remainingQueueRank"],
                            "sourceId": row["sourceId"], "sourceSha256": row["sourceSha256"],
                            "productionCallerCount": len(refs), "boundedScan": "Exact single- or double-quoted source literal scan over all pinned production JS/TS runtime files; tests/specs excluded.",
                            "callers": refs, "sourceTextIncluded": bool(refs), **({"source": row["source"]} if refs else {})})
        for locale in LOCALES:
            target = catalogs[locale][row["source"]]
            cat = next(item for item in catalog_rows if item["locale"] == locale)
            selected_cells.append({"continuationRank": row["continuationRank"], "remainingQueueRank": row["remainingQueueRank"],
                "sourceId": row["sourceId"], "sourceSha256": row["sourceSha256"], "locale": locale,
                "catalogPath": cat["path"], "catalogFileSha256": cat["sha256"], "catalogGitBlob": cat["gitBlob"],
                "source": row["source"], "sourceTextIncluded": True, "currentTarget": target,
                "currentTargetSha256": tsha(target), "currentTargetTextIncluded": True,
                "callerContextSha256": sha(canon(refs)), "callerCount": len(refs), "callerRefs": hash_refs(refs),
                "tokenEvidence": token_data(row["source"], target), "containsCandidate": False, "decision": None})

    hold_attestation = []
    hold_status = collections.Counter()
    for old in previous_holds:
        sid, locale = old["sourceId"], old["locale"]
        source = current_by_id.get(sid)
        if not source or tsha(source) != old["sourceSha256"]:
            raise SystemExit("REFUSED: prior active hold source no longer current")
        target_hash = tsha(catalogs[locale][source])
        refs = refs_by_source[source]
        context_hash = sha(canon(refs))
        status = "reattested-unchanged" if target_hash == old["priorTargetSha256"] and context_hash == old["currentCallerContextSha256"] else "reattested-context-or-target-changed"
        hold_status[status] += 1
        hold_attestation.append({"priorWindow": old["priorWindow"], "continuationRank": old["continuationRank"],
            "sourceId": sid, "sourceIdSha256": tsha(sid), "sourceSha256": tsha(source), "locale": locale,
            "priorDisposition": "hold", "priorTargetSha256": old["priorTargetSha256"], "currentTargetSha256": target_hash,
            "matchesPriorCurrentValue": target_hash == old["priorTargetSha256"], "holdReasonSha256": old.get("holdReasonSha256"),
            "priorCallerCount": old["currentCallerCount"], "priorCallerContextSha256": old["currentCallerContextSha256"],
            "priorCallerRefs": old["currentCallerRefs"], "currentCallerCount": len(refs), "currentCallerContextSha256": context_hash,
            "currentCallerRefs": hash_refs(refs), "callerEvidenceUnchanged": context_hash == old["currentCallerContextSha256"],
            "currentCatalogPath": f"src/web/public/locales/{locale}.json", "currentCatalogFileSha256": sha((REPO / f"src/web/public/locales/{locale}.json").read_bytes()),
            "currentCatalogGitBlob": tree[f"src/web/public/locales/{locale}.json"]["gitBlob"], "status": status,
            "sourceTextIncluded": False, "targetTextIncluded": False})

    resolution_rows = []
    for old in previous_resolutions:
        sid, locale = old["sourceId"], old["locale"]
        source = current_by_id.get(sid)
        if source:
            refs = refs_by_source[source]
            current_hash = tsha(catalogs[locale][source])
            row = {k: v for k, v in old.items() if k not in TEXT_KEYS}
            row.update({"currentTargetSha256": current_hash, "currentTargetMatchesResolution": current_hash == old.get("resolvedTargetSha256"),
                        "currentCallerCount": len(refs), "currentCallerContextSha256": sha(canon(refs)),
                        "currentCallerRefs": hash_refs(refs), "attestedAtHead": HEAD,
                        "sourceTextIncluded": False, "targetTextIncluded": False})
        else:
            row = {k: v for k, v in old.items() if k not in TEXT_KEYS}
            row.update({"attestedAtHead": HEAD, "resolutionStatusAtCurrentHead": "historical-source-retired-by-reviewed-source-rewrite",
                        "sourceTextIncluded": False, "targetTextIncluded": False})
        resolution_rows.append(row)
    # W81 rank-910's 12 held fragments were resolved by W910's accepted unified source.
    for old in w81_new_holds:
        locale = old["locale"]
        source = current_by_id[new_source_id]
        target_hash = tsha(catalogs[locale][source])
        expected = next(item["targetSha256"] for item in w910_plan if item["locale"] == locale)
        if target_hash != expected:
            raise SystemExit("REFUSED: W910 root-selected target hash changed")
        resolution_rows.append({"priorWindow": "W81", "continuationRank": old["continuationRank"],
            "sourceId": old["sourceId"], "sourceIdSha256": tsha(old["sourceId"]), "sourceSha256": old["sourceSha256"],
            "locale": locale, "priorDisposition": "hold", "formerHoldTargetSha256": old["currentTargetSha256"],
            "holdReasonSha256": old["holdReasonSha256"], "formerCallerCount": old["productionCallerCount"],
            "formerCallerRefs": old["callerRefs"], "resolutionStatus": "resolved-by-W910-reviewed-source-rewrite",
            "resolvedBySourceId": new_source_id, "resolvedBySourceSha256": tsha(source),
            "resolvedTargetSha256": target_hash, "rootTargetHashMatch": True, "productCommit": w910_product_commit,
            "currentOldSourceCallerCount": len(refs_by_source.get(w49[old["sourceId"]]["source"], [])),
            "sourceTextIncluded": False, "targetTextIncluded": False})

    applied_rows = []
    for old in old_applied:
        sid, locale = old["sourceId"], old["locale"]
        source = current_by_id.get(sid)
        if not source or tsha(source) != old["sourceSha256"]:
            raise SystemExit("REFUSED: prior applied target source retired unexpectedly")
        target_hash = tsha(catalogs[locale][source])
        if target_hash != old["appliedTargetSha256"]:
            raise SystemExit("REFUSED: prior applied target no longer present")
        row = {k: v for k, v in old.items() if k not in TEXT_KEYS}
        row.update({"attestedAtHead": HEAD, "currentTargetSha256": target_hash, "targetRemainsApplied": True,
                    "currentCatalogFileSha256": sha((REPO / f"src/web/public/locales/{locale}.json").read_bytes()),
                    "currentCatalogGitBlob": tree[f"src/web/public/locales/{locale}.json"]["gitBlob"],
                    "sourceTextIncluded": False, "targetTextIncluded": False})
        applied_rows.append(row)
    for row in w81_applied:
        sid, locale = row["sourceId"], row["locale"]
        source = current_by_id[sid]
        if tsha(source) != row["sourceSha256"] or tsha(catalogs[locale][source]) != row["targetSha256"]:
            raise SystemExit("REFUSED: W81 selected application target drift")
        applied_rows.append({"priorWindow": "W81", "continuationRank": row["continuationRank"], "sourceId": sid,
            "sourceIdSha256": tsha(sid), "sourceSha256": row["sourceSha256"], "locale": locale,
            "appliedTargetSha256": row["targetSha256"], "currentTargetSha256": row["targetSha256"],
            "targetRemainsApplied": True, "productCommit": w81_product_commit,
            "applicationPlanSha256": sha((W81_APP / "application-plan.jsonl").read_bytes()),
            "currentCatalogFileSha256": sha((REPO / f"src/web/public/locales/{locale}.json").read_bytes()),
            "currentCatalogGitBlob": tree[f"src/web/public/locales/{locale}.json"]["gitBlob"],
            "sourceTextIncluded": False, "targetTextIncluded": False})
    for row in w910_plan:
        locale = row["locale"]
        source = current_by_id[new_source_id]
        if tsha(source) != w910_source["sourceTextSha256"] or tsha(catalogs[locale][source]) != row["targetSha256"]:
            raise SystemExit("REFUSED: W910 selected application target drift")
        applied_rows.append({"priorWindow": "W910 rich-text source rewrite", "continuationRank": 910,
            "sourceId": new_source_id, "sourceIdSha256": tsha(new_source_id), "sourceSha256": tsha(source),
            "locale": locale, "appliedTargetSha256": row["targetSha256"], "currentTargetSha256": row["targetSha256"],
            "targetRemainsApplied": True, "productCommit": w910_product_commit,
            "applicationPlanSha256": sha((W910_APP / "catalog-product-plan.json").read_bytes()),
            "currentCatalogFileSha256": sha((REPO / f"src/web/public/locales/{locale}.json").read_bytes()),
            "currentCatalogGitBlob": tree[f"src/web/public/locales/{locale}.json"]["gitBlob"],
            "sourceTextIncluded": False, "targetTextIncluded": False})
    if len({(row["sourceId"], row["locale"]) for row in applied_rows}) != len(applied_rows):
        raise SystemExit("REFUSED: duplicate applied-target lineage cell")

    # Record the W910 replacement caller and all prior selected current-only source IDs.
    rewrite_callers = []
    for sid in sorted(rewrite_current_ids):
        source = current_by_id[sid]
        rewrite_callers.append({"sourceId": sid, "sourceSha256": tsha(source), "callerCount": len(refs_by_source[source]),
                                "callerContextSha256": sha(canon(refs_by_source[source])),
                                "callerRefs": hash_refs(refs_by_source[source]), "sourceTextIncluded": False})

    mismatches = collections.Counter()
    mismatch_examples = []
    for row in selected_cells:
        evidence = row["tokenEvidence"]
        for kind, ok in (("placeholder", evidence["placeholders"]["matches"]),
                         ("markup", evidence["markup"]["matches"]),
                         ("numeric", evidence["numbers"]["sourcePreserved"]),
                         ("protectedLiteral", not evidence["protectedLiterals"]["missing"])):
            if not ok:
                mismatches[kind] += 1
                mismatch_examples.append({"continuationRank": row["continuationRank"], "sourceId": row["sourceId"],
                                          "locale": row["locale"], "kind": kind})

    write_jsonl("catalog-structure.jsonl", catalog_rows)
    write_jsonl("runtime-file-pins.jsonl", runtime)
    write_jsonl("caller-contexts.jsonl", caller_rows)
    write_jsonl("source-current-cells.jsonl", selected_cells)
    write_jsonl("prior-held-cell-reattestation-hash-only.jsonl", hold_attestation)
    write_jsonl("prior-hold-resolution-history-hash-only.jsonl", resolution_rows)
    write_jsonl("prior-applied-targets-reattestation-hash-only.jsonl", applied_rows)
    write_jsonl("already-reviewed-rewrite-callers-hash-only.jsonl", rewrite_callers)
    write_json("baseline-token-mismatch-summary.json", {"cellCount": len(selected_cells), "mismatchCounts": dict(mismatches),
                "mismatchExamples": mismatch_examples, "reviewCandidateTextIncluded": False})
    write_json("continuity-provenance.json", {"previousCandidateFreeWindow": "W81", "previousHead": "91da6fff5d5b628ade7ee556386e3db1db6878fa",
                "previousTree": "56930b73d10a4c419edf68f0d951ceedaa63c990", "W81PriorSelectedIdRows": len(read_jsonl(PREV / "prior-selected-id-exclusions-hash-only.jsonl")),
                "W81SelectedIdsAdded": len(prev_selection), "ReviewedRewriteReplacementIdsAdded": len(rewrite_exclusions),
                "priorSelectedAndRewriteIdRows": len(prior_by_id), "activePriorHolds": len(hold_attestation),
                "priorHoldResolutionHistoryRows": len(resolution_rows), "priorAppliedTargetsReattested": len(applied_rows),
                "W81AppliedTargetsAdded": len(w81_applied), "W910AppliedTargetsAdded": len(w910_plan),
                "W910ProductCommit": w910_product_commit, "W910RootTargetHashesMatch": True,
                "sourceRewriteDeltaSha256": sha((ROOT / "source-inventory-reconciliation.jsonl").read_bytes()),
                "sourceTextIncluded": False, "targetTextIncluded": False, "blindReviewUsed": False, "crossReviewUsed": False})
    write_json("source-tree-attestation.json", {"head": HEAD, "tree": TREE, "treeEntryCount": len(tree),
                "productionFileCount": len(runtime), "sourceInventoryBaseline": "W81 stable inventory plus exact current-catalog reconciliation",
                "sourceInventoryRows": len(inventory_rows), "sourceInventoryHash": sha((ROOT / "source-inventory-pinned.jsonl").read_bytes()),
                "runtimeCallerScan": "Exact single- or double-quoted source literals across pinned production JS/TS files",
                "runtimeFilePinsSha256": sha((ROOT / "runtime-file-pins.jsonl").read_bytes())})
    write_json("selection-boundary.json", {"previous-window-final": previous_boundary,
                "selected-window": [{k: row[k] for k in ("continuationRank", "remainingQueueRank", "sourceId", "sourceSha256")} for row in selected],
                "next-unselected": next_boundary})
    write_json("manifest.json", {"artifact": "slskdN PR #409 W82 continuation ranks candidate-free exact-head input",
                "schemaVersion": 1, "repository": "snapetech-org/slskdN", "pullRequest": 409, "branch": BRANCH,
                "window": "W82", "candidateFree": True, "head": HEAD, "tree": TREE,
                "continuationRankRange": [FIRST, LAST], "remainingQueueRankRange": [828, 852],
                "sourceCount": 25, "localeCount": 12, "cellCount": 300, "locales": LOCALES,
                "catalogEntryCountPerLocale": 6175, "catalogCount": 12, "productionCallerFileCount": len(runtime),
                "sourcesWithCallers": sum(bool(row["productionCallerCount"]) for row in caller_rows),
                "sourcesWithoutCallers": sum(not row["productionCallerCount"] for row in caller_rows),
                "priorSelectedIdsAndRewriteReplacements": len(prior_by_id), "priorActiveHoldsReattested": len(hold_attestation),
                "priorHoldResolutionHistoryRows": len(resolution_rows), "priorAppliedTargetsReattested": len(applied_rows),
                "baselineTokenMismatches": dict(mismatches), "proposedTargetsIncluded": False,
                "reviewDecisionsIncluded": False, "blindReviewUsed": False, "crossReviewUsed": False,
                "prBodyContentIncluded": False, "mainWasNotMerged": True, "files": []})
    readme = ("# slskdN PR #409 W82 candidate-free input\n\n"
              "This packet prepares stable continuation ranks 928–952 and remaining-queue ranks 828–852: 25 sources × 12 locales. "
              "It is pinned to head `" + HEAD + "` and tree `" + TREE + "`.\n\n"
              "The queue was recomputed against all 12 ordered catalogs at 6,175 keys each. The W81 baseline has 6,176 source IDs; "
              "four previously reviewed source IDs were retired and three already-reviewed rewrite replacements were added. The retired "
              "rank slots are 185, 732, 750, and 910; they remain historical holes. The W74 replacements map ranks 732 and 750, and the W910 "
              "rich-text replacement maps ranks 185 and 910. No source in ranks 928–952 is missing, duplicated, previously selected, or hash-stale.\n\n"
              "Each selected source has pinned current catalog values and exact production caller context. Rank 944 has no production caller and is "
              "included as a caller-context hold candidate; the other 24 sources have callers. Prior active holds, source rewrite resolution history, "
              "and recent applied target hashes are reattested at this head. No recommendations, proposed targets, or review decisions are present.\n\n"
              "The PR was open and draft at capture. Current main was captured as `" + MAIN + "` and was not merged. PR body content is not included. "
              "This packet contains no source/catalog edits. No tests, builds, repository scans, CI, merge, release, tag, browser review, or "
              "native-speaker signoff are claimed.\n")
    (ROOT / "README.md").write_text(readme, encoding="utf-8")

    # The manifest lists every other payload file; the checksum list covers the manifest too.
    files = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
                   if p.is_file() and p.name not in {"manifest.json", "SHA256SUMS.txt"})
    file_rows = [{"path": name, "sha256": sha((ROOT / name).read_bytes()), "bytes": (ROOT / name).stat().st_size} for name in files]
    manifest = json.loads((ROOT / "manifest.json").read_text())
    manifest["files"] = file_rows
    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    lines = [f"{sha((ROOT / name).read_bytes())}  {name}" for name in files]
    (ROOT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"result": "SEALED-CANDIDATE-FREE", "head": HEAD, "tree": TREE, "window": "W82",
                      "ranks": [FIRST, LAST], "sources": len(selected), "cells": len(selected_cells),
                      "callers": sum(bool(row["productionCallerCount"]) for row in caller_rows),
                      "callerless": sum(not row["productionCallerCount"] for row in caller_rows),
                      "priorHolds": len(hold_attestation), "priorResolutions": len(resolution_rows),
                      "priorAppliedTargets": len(applied_rows), "files": len(files)}, indent=2))


if __name__ == "__main__":
    main()
