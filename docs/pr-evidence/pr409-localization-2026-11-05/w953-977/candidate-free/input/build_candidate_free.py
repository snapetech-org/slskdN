#!/usr/bin/env python3
"""Build a sealed candidate-free W83 packet from the exact PR head."""
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
HEAD = "fc8e42a06363ceee762ae084bbe716953d4a5d94"
TREE = "e04aa06b8cfb0ee41cae90aef601a0552b5e85bd"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
BASE = REPO / "docs/pr-evidence/pr409-localization-2026-11-05/window-928-952-w82"
PREV = BASE / "candidate-free/input"
PREV_PRIMARY = BASE / "primary-review"
PREV_APP = BASE / "root-application"
W82_HEAD = "6e48a342d4b1c43918c23da3afcbaad19c87a005"
W82_TREE = "b82ea7937cf9aa141a1c952283d5549dbe116ba5"
W82_PRODUCT = "807e0f1b6b21f8783483224aac01c159ccac08a5"
FIRST, LAST = 953, 977
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
TEXT_KEYS = {"source", "sourceText", "target", "currentTarget", "proposedTarget", "proposedTargetText", "candidateTarget", "resolvedTarget", "resolvedTargetText", "formerTargetText", "reason", "rationale"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tsha(text):
    return sha(text.encode("utf-8"))


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


def verify_checksum_tree(root, checksum_file, listed_prefix=""):
    lines = Path(checksum_file).read_text(encoding="utf-8").splitlines()
    recorded = {}
    for line in lines:
        digest, name = line.split("  ", 1)
        name = name.removeprefix(listed_prefix).removeprefix("./")
        path = Path(root) / name
        if not path.is_file() or sha(path.read_bytes()) != digest:
            raise SystemExit("REFUSED: predecessor checksum mismatch: " + name)
        if name in recorded:
            raise SystemExit("REFUSED: duplicate predecessor checksum path: " + name)
        recorded[name] = digest
    actual = {p.relative_to(root).as_posix() for p in Path(root).rglob("*")
              if p.is_file() and p.name != Path(checksum_file).name}
    if actual != set(recorded):
        raise SystemExit("REFUSED: predecessor packet inventory mismatch")
    return recorded


def capture_live():
    pr = json.loads(subprocess.check_output(["gh", "api", "repos/snapetech-org/slskdN/pulls/409"]))
    branch_ref = json.loads(subprocess.check_output(["gh", "api", "repos/snapetech-org/slskdN/git/ref/heads/" + BRANCH]))
    main_commit = json.loads(subprocess.check_output(["gh", "api", "repos/snapetech-org/slskdN/commits/main"]))
    remote = subprocess.check_output(["git", "-C", str(REPO), "ls-remote", "origin", "refs/pull/409/head", "refs/heads/" + BRANCH, "refs/heads/main"], text=True)
    remote_refs = {line.split()[1]: line.split()[0] for line in remote.splitlines() if line.strip()}
    result = {
        "repository": "snapetech-org/slskdN", "pullRequest": 409,
        "state": pr["state"], "draft": pr["draft"], "merged": pr["merged"],
        "baseRef": pr["base"]["ref"], "baseSha": pr["base"]["sha"],
        "headRef": pr["head"]["ref"], "headSha": pr["head"]["sha"],
        "headTree": git("rev-parse", HEAD + "^{tree}").decode().strip(),
        "branchRefSha": branch_ref["object"]["sha"],
        "pullRefSha": remote_refs.get("refs/pull/409/head"),
        "remoteBranchSha": remote_refs.get("refs/heads/" + BRANCH),
        "remoteMainSha": remote_refs.get("refs/heads/main"),
        "apiMainSha": main_commit["sha"], "apiMainTree": main_commit["commit"]["tree"]["sha"],
        "capturedAtHead": HEAD, "prBodyContentIncluded": False,
    }
    if result["state"] != "open" or result["draft"] is not True or result["merged"] is not False:
        raise SystemExit("REFUSED: PR state changed")
    if result["headRef"] != BRANCH or result["headSha"] != HEAD or result["headTree"] != TREE:
        raise SystemExit("REFUSED: live PR head/tree changed")
    if result["branchRefSha"] != HEAD or result["pullRefSha"] != HEAD or result["remoteBranchSha"] != HEAD:
        raise SystemExit("REFUSED: live branch/pull ref mismatch")
    if result["baseRef"] != "main" or result["remoteMainSha"] != result["apiMainSha"]:
        raise SystemExit("REFUSED: live PR base/main refs mismatch")
    return result


def token_data(source, target):
    placeholders = lambda s: collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", s))
    tags = lambda s: collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", s))
    nums = lambda s: ["".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in token) for token in re.findall(r"\d+", s)]
    protected = lambda s: sorted(set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", s)) | {x for x in ("slskdN", "PodCore", "Wishlist", "soulfind", "FFmpeg", "Lidarr") if x in s})
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


def scan_sources(sources, runtime):
    refs_by_source = {source: [] for source in sources}
    for rec in runtime:
        data = (REPO / rec["path"]).read_bytes()
        if sha(data) != rec["sha256"] or blob_sha(data) != rec["gitBlob"]:
            raise SystemExit("REFUSED: runtime file pin changed: " + rec["path"])
        lines = data.decode("utf-8").splitlines()
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


def main():
    if git("rev-parse", "HEAD").decode().strip() != HEAD or git("rev-parse", "HEAD^{tree}").decode().strip() != TREE:
        raise SystemExit("REFUSED: wrong pinned worktree")
    if git("status", "--porcelain=v1").decode().strip():
        raise SystemExit("REFUSED: worktree is not clean")
    live = capture_live()
    previous_packet_sums = verify_checksum_tree(BASE, BASE / "SHA256SUMS.txt", "./")
    predecessor_sums = verify_checksum_tree(PREV, PREV / "SHA256SUMS.txt")
    prev_manifest = json.loads((PREV / "manifest.json").read_text(encoding="utf-8"))
    if prev_manifest.get("head") != W82_HEAD or prev_manifest.get("tree") != W82_TREE or prev_manifest.get("candidateFree") is not True:
        raise SystemExit("REFUSED: W82 candidate-free predecessor identity")
    if prev_manifest.get("sourceCount") != 25 or prev_manifest.get("cellCount") != 300:
        raise SystemExit("REFUSED: W82 predecessor coverage")
    app_plan = json.loads((PREV_APP / "root-application-plan.json").read_text(encoding="utf-8"))
    app_commit = json.loads((PREV_APP / "product-commit-record.json").read_text(encoding="utf-8"))
    app_readback = read_jsonl(PREV_APP / "all-cell-readback.jsonl")
    app_review = read_jsonl(PREV_APP / "root-review-ledger.jsonl")
    app_summary = json.loads((PREV_APP / "root-review-summary.json").read_text(encoding="utf-8"))
    if app_commit.get("commit") != W82_PRODUCT or app_plan.get("sourcePin") != {"head": W82_HEAD, "tree": W82_TREE}:
        raise SystemExit("REFUSED: W82 product evidence pin")
    if subprocess.call(["git", "-C", str(REPO), "merge-base", "--is-ancestor", W82_PRODUCT, HEAD]) != 0:
        raise SystemExit("REFUSED: W82 product commit is not an ancestor of current head")
    if len(app_readback) != 300 or len(app_review) != 300 or len({(r["sourceId"], r["locale"]) for r in app_readback}) != 300:
        raise SystemExit("REFUSED: W82 root readback/review coverage")
    if app_summary.get("selectedChanges") != app_commit.get("selectedCells"):
        raise SystemExit("REFUSED: W82 applied-cell count mismatch")
    write_json("live-before.json", live)
    main_sha = live["apiMainSha"]
    main_names = subprocess.check_output(["git", "-C", str(REPO), "diff", "--name-status", HEAD + "..." + main_sha, "--", "src/web/src", "src/web/public/locales"], text=True)
    drift_rows = []
    for line in main_names.splitlines():
        status, path = line.split("\t", 1)
        drift_rows.append({"status": status, "path": path})
    write_json("main-drift.json", {"head": HEAD, "main": main_sha, "localizationAndRuntimePathChangesOnMain": drift_rows,
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
    if len(baseline) != 6175 or len(baseline_by_id) != 6175:
        raise SystemExit("REFUSED: W82 stable inventory")
    current_ids, baseline_ids = set(current_by_id), set(baseline_by_id)
    additions, retirements = sorted(current_ids - baseline_ids), sorted(baseline_ids - current_ids)
    if additions or retirements:
        raise SystemExit("REFUSED: unreviewed source inventory changes since W82")
    for sid, source in current_by_id.items():
        if baseline_by_id[sid]["sourceSha256"] != tsha(source):
            raise SystemExit("REFUSED: retained stable source hash changed")

    prior = read_jsonl(PREV / "prior-selected-id-exclusions-hash-only.jsonl")
    prev_selection = read_jsonl(PREV / "source-inventory-selection.jsonl")
    prior.extend({"sourceId": row["sourceId"], "sourceIdSha256": tsha(row["sourceId"]),
                  "sourceSha256": row["sourceSha256"], "selectionOrigin": "W82 selected source ID",
                  "continuationRank": row["continuationRank"], "remainingQueueRank": row["remainingQueueRank"],
                  "exclusionConfirmed": True, "sourceTextIncluded": False, "targetTextIncluded": False}
                 for row in prev_selection)
    prior_by_id = {row["sourceId"]: row for row in prior}
    if len(prior_by_id) != len(prior):
        raise SystemExit("REFUSED: duplicate prior selected source ID")
    for row in prior:
        if any(key in TEXT_KEYS for key in row):
            raise SystemExit("REFUSED: source or target text in prior ID lineage")

    ranked, inventory_rows = {}, []
    for sid in sorted(current_ids):
        old = baseline_by_id[sid]
        rank = old.get("continuationRank")
        queue = old.get("remainingQueueRank")
        baseline_excluded = old.get("baselineExcluded", old.get("excluded", False))
        if rank is not None:
            if rank in ranked:
                raise SystemExit("REFUSED: duplicate stable continuation rank")
            ranked[rank] = sid
        inventory_rows.append({"sourceId": sid, "sourceSha256": tsha(current_by_id[sid]),
                               "continuationRank": rank, "remainingQueueRank": queue,
                               "baselineExcluded": baseline_excluded,
                               "priorSelectedOrRewriteExcluded": sid in prior_by_id,
                               "eligibleForFreshWindow": rank is not None and not baseline_excluded and sid not in prior_by_id,
                               "localeCoverage": 12, "sourceTextIncluded": False})
    if len(ranked) != 4967:
        raise SystemExit("REFUSED: stable ranked inventory count")
    selected = []
    for rank in range(FIRST, LAST + 1):
        sid = ranked.get(rank)
        if not sid or sid not in current_by_id or sid in prior_by_id:
            raise SystemExit("REFUSED: current rank missing, stale, or previously selected: " + str(rank))
        selected.append({"continuationRank": rank, "remainingQueueRank": rank - 100, "sourceId": sid,
                         "sourceSha256": tsha(current_by_id[sid]), "source": current_by_id[sid]})
    if selected[0]["sourceId"] != "src_358f9860b3f4e247":
        raise SystemExit("REFUSED: first source ID does not match assigned window")
    previous_boundary = {"continuationRank": 952, "remainingQueueRank": 852, "sourceId": ranked[952],
                         "sourceSha256": tsha(current_by_id[ranked[952]])}
    next_boundary = {"continuationRank": 978, "remainingQueueRank": 878, "sourceId": ranked[978],
                     "sourceSha256": tsha(current_by_id[ranked[978]])}
    write_jsonl("source-inventory-pinned.jsonl", inventory_rows)
    write_jsonl("source-inventory-selection.jsonl", [{k: row[k] for k in ("continuationRank", "remainingQueueRank", "sourceId", "sourceSha256")} for row in selected])
    write_jsonl("selected-sources.jsonl", selected)
    write_jsonl("prior-selected-id-exclusions-hash-only.jsonl", sorted(prior, key=lambda row: row["sourceId"]))
    write_jsonl("source-inventory-reconciliation.jsonl", [])

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

    previous_holds = read_jsonl(PREV / "prior-held-cell-reattestation-hash-only.jsonl")
    previous_resolutions = read_jsonl(PREV / "prior-hold-resolution-history-hash-only.jsonl")
    old_applied = read_jsonl(PREV / "prior-applied-targets-reattestation-hash-only.jsonl")
    if len(previous_holds) != prev_manifest["priorActiveHoldsReattested"] or len(previous_resolutions) != prev_manifest["priorHoldResolutionHistoryRows"] or len(old_applied) != prev_manifest["priorAppliedTargetsReattested"]:
        raise SystemExit("REFUSED: W82 predecessor lineage counts")

    w82_holds = [row for row in app_review if row.get("rootDisposition", "").startswith("hold-")]
    if len(w82_holds) != app_plan["callerlessHoldCount"] + app_plan["languageHoldCount"]:
        raise SystemExit("REFUSED: W82 active hold count")
    readback_by_cell = {(r["sourceId"], r["locale"]): r for r in app_readback}
    for row in app_review:
        rb = readback_by_cell[(row["sourceId"], row["locale"])]
        if row["currentTargetSha256"] != rb["beforeTargetSha256"]:
            raise SystemExit("REFUSED: W82 root decision/readback preimage mismatch")
    changes = [row for row in app_readback if row["changed"]]
    if len(changes) != app_commit["selectedCells"]:
        raise SystemExit("REFUSED: W82 product selected-cell count")

    hold_source_ids = {row["sourceId"] for row in previous_holds}
    resolution_source_ids = {row["sourceId"] for row in previous_resolutions}
    selected_source_ids = {row["sourceId"] for row in selected}
    w82_hold_source_ids = {row["sourceId"] for row in w82_holds}
    scan_ids = selected_source_ids | hold_source_ids | (resolution_source_ids & current_ids) | w82_hold_source_ids
    source_texts_to_scan = {current_by_id[sid] for sid in scan_ids if sid in current_by_id}
    refs_by_source = scan_sources(source_texts_to_scan, runtime)
    caller_rows, selected_cells = [], []
    for row in selected:
        refs = refs_by_source[row["source"]]
        caller_rows.append({"continuationRank": row["continuationRank"], "remainingQueueRank": row["remainingQueueRank"],
                            "sourceId": row["sourceId"], "sourceSha256": row["sourceSha256"],
                            "productionCallerCount": len(refs),
                            "boundedScan": "Exact single- or double-quoted source literal scan over all pinned production JS/TS runtime files; tests/specs excluded.",
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

    hold_attestation, hold_status = [], collections.Counter()
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
            "priorCallerRefs": old.get("currentCallerRefs", []), "currentCallerCount": len(refs), "currentCallerContextSha256": context_hash,
            "currentCallerRefs": hash_refs(refs), "callerEvidenceUnchanged": context_hash == old["currentCallerContextSha256"],
            "currentCatalogPath": f"src/web/public/locales/{locale}.json", "currentCatalogFileSha256": sha((REPO / f"src/web/public/locales/{locale}.json").read_bytes()),
            "currentCatalogGitBlob": tree[f"src/web/public/locales/{locale}.json"]["gitBlob"], "status": status,
            "sourceTextIncluded": False, "targetTextIncluded": False})
    for old in w82_holds:
        sid, locale = old["sourceId"], old["locale"]
        source = current_by_id.get(sid)
        if not source or tsha(source) != old["sourceSha256"]:
            raise SystemExit("REFUSED: W82 held source no longer current")
        refs = refs_by_source[source]
        target_hash = tsha(catalogs[locale][source])
        reason_code = old["rootDisposition"]
        previous_hash = old["currentTargetSha256"]
        status = "reattested-unchanged" if target_hash == previous_hash and sha(canon(refs)) == old["callerContextSha256"] else "reattested-context-or-target-changed"
        hold_status[status] += 1
        hold_attestation.append({"priorWindow": "W82", "continuationRank": old["continuationRank"],
            "sourceId": sid, "sourceIdSha256": tsha(sid), "sourceSha256": tsha(source), "locale": locale,
            "priorDisposition": "hold", "priorHoldReasonCode": reason_code,
            "priorTargetSha256": previous_hash, "currentTargetSha256": target_hash,
            "matchesPriorCurrentValue": target_hash == previous_hash, "holdReasonSha256": tsha(reason_code),
            "priorCallerCount": old["callerCount"], "priorCallerContextSha256": old["callerContextSha256"],
            "priorCallerRefs": [], "currentCallerCount": len(refs), "currentCallerContextSha256": sha(canon(refs)),
            "currentCallerRefs": hash_refs(refs), "callerEvidenceUnchanged": sha(canon(refs)) == old["callerContextSha256"],
            "currentCatalogPath": f"src/web/public/locales/{locale}.json", "currentCatalogFileSha256": sha((REPO / f"src/web/public/locales/{locale}.json").read_bytes()),
            "currentCatalogGitBlob": tree[f"src/web/public/locales/{locale}.json"]["gitBlob"], "status": status,
            "sourceTextIncluded": False, "targetTextIncluded": False})
    if len({(r["sourceId"], r["locale"]) for r in hold_attestation}) != len(hold_attestation):
        raise SystemExit("REFUSED: duplicate active hold cell")

    resolution_rows = []
    for old in previous_resolutions:
        sid, locale = old["sourceId"], old["locale"]
        source = current_by_id.get(sid)
        row = {k: v for k, v in old.items() if k not in TEXT_KEYS}
        if source:
            refs = refs_by_source[source]
            current_hash = tsha(catalogs[locale][source])
            row.update({"currentTargetSha256": current_hash, "currentTargetMatchesResolution": current_hash == old.get("resolvedTargetSha256"),
                        "currentCallerCount": len(refs), "currentCallerContextSha256": sha(canon(refs)),
                        "currentCallerRefs": hash_refs(refs), "attestedAtHead": HEAD,
                        "sourceTextIncluded": False, "targetTextIncluded": False})
        else:
            row.update({"attestedAtHead": HEAD, "resolutionStatusAtCurrentHead": "historical-source-retired",
                        "sourceTextIncluded": False, "targetTextIncluded": False})
        resolution_rows.append(row)

    applied_rows = []
    for old in old_applied:
        sid, locale = old["sourceId"], old["locale"]
        source = current_by_id.get(sid)
        if not source or tsha(source) != old["sourceSha256"]:
            raise SystemExit("REFUSED: prior applied target source retired unexpectedly")
        target_hash = tsha(catalogs[locale][source])
        expected = old.get("appliedTargetSha256", old.get("targetSha256"))
        if target_hash != expected:
            raise SystemExit("REFUSED: prior applied target no longer present")
        row = {k: v for k, v in old.items() if k not in TEXT_KEYS}
        row.update({"attestedAtHead": HEAD, "currentTargetSha256": target_hash, "targetRemainsApplied": True,
                    "currentCatalogFileSha256": sha((REPO / f"src/web/public/locales/{locale}.json").read_bytes()),
                    "currentCatalogGitBlob": tree[f"src/web/public/locales/{locale}.json"]["gitBlob"],
                    "sourceTextIncluded": False, "targetTextIncluded": False})
        applied_rows.append(row)
    w82_readback_hash = sha((PREV_APP / "all-cell-readback.jsonl").read_bytes())
    w82_plan_hash = sha((PREV_APP / "root-application-plan.json").read_bytes())
    for row in changes:
        sid, locale = row["sourceId"], row["locale"]
        source = current_by_id[sid]
        target_hash = tsha(catalogs[locale][source])
        if target_hash != row["expectedAfterSha256"]:
            raise SystemExit("REFUSED: W82 selected application target drift")
        applied_rows.append({"priorWindow": "W82", "continuationRank": row["continuationRank"],
            "remainingQueueRank": row["remainingQueueRank"], "sourceId": sid, "sourceIdSha256": tsha(sid),
            "sourceSha256": row["sourceSha256"], "locale": locale, "appliedTargetSha256": target_hash,
            "currentTargetSha256": target_hash, "targetRemainsApplied": True, "productCommit": W82_PRODUCT,
            "applicationPlanSha256": w82_plan_hash, "applicationReadbackSha256": w82_readback_hash,
            "currentCatalogFileSha256": sha((REPO / f"src/web/public/locales/{locale}.json").read_bytes()),
            "currentCatalogGitBlob": tree[f"src/web/public/locales/{locale}.json"]["gitBlob"],
            "sourceTextIncluded": False, "targetTextIncluded": False})
    if len({(row["sourceId"], row["locale"]) for row in applied_rows}) != len(applied_rows):
        raise SystemExit("REFUSED: duplicate applied-target lineage cell")

    mismatches, mismatch_examples = collections.Counter(), []
    for row in selected_cells:
        evidence = row["tokenEvidence"]
        for kind, ok in (("placeholder", evidence["placeholders"]["matches"]),
                         ("markup", evidence["markup"]["matches"]),
                         ("numeric", evidence["numbers"]["sourcePreserved"]),
                         ("protectedLiteral", not evidence["protectedLiterals"]["missing"])):
            if not ok:
                mismatches[kind] += 1
                mismatch_examples.append({"continuationRank": row["continuationRank"], "sourceId": row["sourceId"], "locale": row["locale"], "kind": kind})

    write_jsonl("catalog-structure.jsonl", catalog_rows)
    write_jsonl("runtime-file-pins.jsonl", runtime)
    write_jsonl("caller-contexts.jsonl", caller_rows)
    write_jsonl("source-current-cells.jsonl", selected_cells)
    write_jsonl("prior-held-cell-reattestation-hash-only.jsonl", hold_attestation)
    write_jsonl("prior-hold-resolution-history-hash-only.jsonl", resolution_rows)
    write_jsonl("prior-applied-targets-reattestation-hash-only.jsonl", applied_rows)
    write_json("baseline-token-mismatch-summary.json", {"cellCount": len(selected_cells), "mismatchCounts": dict(mismatches),
                "mismatchExamples": mismatch_examples, "reviewCandidateTextIncluded": False})
    write_json("continuity-provenance.json", {"previousCandidateFreeWindow": "W82", "previousHead": W82_HEAD,
                "previousTree": W82_TREE, "W82PriorSelectedIdRows": len(read_jsonl(PREV / "prior-selected-id-exclusions-hash-only.jsonl")),
                "W82SelectedIdsAdded": len(prev_selection), "priorSelectedIdsExcluded": len(prior_by_id),
                "activePriorHolds": len(hold_attestation), "previousActiveHolds": len(previous_holds),
                "W82NewActiveHolds": len(w82_holds), "priorHoldResolutionHistoryRows": len(resolution_rows),
                "priorAppliedTargetsReattested": len(applied_rows), "previousAppliedTargets": len(old_applied),
                "W82AppliedTargetsAdded": len(changes), "W82ProductCommit": W82_PRODUCT,
                "W82RootTargetHashesMatch": True, "W82PacketChecksumCount": len(previous_packet_sums),
                "W82CandidateInputChecksumCount": len(predecessor_sums), "sourceTextIncluded": False,
                "targetTextIncluded": False, "blindReviewUsed": False, "crossReviewUsed": False})
    write_json("source-tree-attestation.json", {"head": HEAD, "tree": TREE, "treeEntryCount": len(tree),
                "productionFileCount": len(runtime), "sourceInventoryBaseline": "W82 stable inventory plus exact current-catalog reconciliation",
                "sourceInventoryRows": len(inventory_rows), "sourceInventoryHash": sha((ROOT / "source-inventory-pinned.jsonl").read_bytes()),
                "runtimeCallerScan": "Exact single- or double-quoted source literals across pinned production JS/TS files",
                "runtimeFilePinsSha256": sha((ROOT / "runtime-file-pins.jsonl").read_bytes())})
    write_json("selection-and-boundary.json", {"repository": "snapetech-org/slskdN", "pullRequest": 409, "window": "W83",
                "branch": BRANCH, "head": HEAD, "tree": TREE, "candidateFree": True, "locales": LOCALES,
                "sourceCount": 25, "cellCount": 300, "continuationRankRange": [FIRST, LAST],
                "remainingQueueRankRange": [853, 877], "previousWindow": "W82", "previousWindowFinalRank": previous_boundary,
                "nextUnselected": next_boundary, "sourceInventoryRows": len(inventory_rows), "stableRankedRows": len(ranked),
                "retiredStableRankRows": [185, 732, 750, 910], "sourceRewriteReplacementIdsExcluded": [],
                "orderedCatalogKeySha256": sha(("\n".join(ordered) + "\n").encode()), "catalogEntryCountPerLocale": 6175,
                "priorSelectedAndRewriteIdsExcluded": len(prior_by_id), "proposedTargetsIncluded": False, "reviewDecisionsIncluded": False})
    write_json("selection-boundary.json", {"previous-window-final": previous_boundary,
                "selected-window": [{k: row[k] for k in ("continuationRank", "remainingQueueRank", "sourceId", "sourceSha256")} for row in selected],
                "next-unselected": next_boundary})
    write_json("manifest.json", {"artifact": "slskdN PR #409 W83 continuation ranks candidate-free exact-head input",
                "schemaVersion": 1, "repository": "snapetech-org/slskdN", "pullRequest": 409, "branch": BRANCH,
                "window": "W83", "candidateFree": True, "head": HEAD, "tree": TREE,
                "continuationRankRange": [FIRST, LAST], "remainingQueueRankRange": [853, 877],
                "sourceCount": 25, "localeCount": 12, "cellCount": 300, "locales": LOCALES,
                "catalogEntryCountPerLocale": 6175, "catalogCount": 12, "productionCallerFileCount": len(runtime),
                "sourcesWithCallers": sum(bool(row["productionCallerCount"]) for row in caller_rows),
                "sourcesWithoutCallers": sum(not row["productionCallerCount"] for row in caller_rows),
                "priorSelectedIdsAndRewriteReplacements": len(prior_by_id), "priorActiveHoldsReattested": len(hold_attestation),
                "priorHoldResolutionHistoryRows": len(resolution_rows), "priorAppliedTargetsReattested": len(applied_rows),
                "baselineTokenMismatches": dict(mismatches), "proposedTargetsIncluded": False,
                "reviewDecisionsIncluded": False, "blindReviewUsed": False, "crossReviewUsed": False,
                "prBodyContentIncluded": False, "mainWasNotMerged": True, "files": []})
    readme = ("# slskdN PR #409 W83 candidate-free input\n\n"
              "This packet prepares stable continuation ranks 953–977 and remaining-queue ranks 853–877: 25 sources × 12 locales. "
              "It is pinned to head `" + HEAD + "` and tree `" + TREE + "`.\n\n"
              "The ordered 6,175-key catalogs agree across all 12 locales. The 25 selected sources continue directly after W82, beginning with `src_358f9860b3f4e247`; every selected source is unique, current, and absent from the prior-selected exclusion set. "
              "Current catalog values and exact production caller context are pinned, with source/caller/current-target hashes. The W82 application, prior active holds, and hold-resolution history are reattested at this head. "
              "No proposed targets or review decisions are present.\n\n"
              "The PR was open and draft at capture; current main is recorded in `live-before.json` and was not merged. PR body content is excluded. "
              "This packet contains no source/catalog edits. No tests, builds, scans, CI, merge, release, tag, browser review, or native-speaker signoff are claimed.\n")
    (ROOT / "README.md").write_text(readme, encoding="utf-8")

    files = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
                   if p.is_file() and p.name not in {"manifest.json", "SHA256SUMS.txt"})
    file_rows = [{"path": name, "sha256": sha((ROOT / name).read_bytes()), "bytes": (ROOT / name).stat().st_size} for name in files]
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"] = file_rows
    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    (ROOT / "SHA256SUMS.txt").write_text("\n".join(f"{sha((ROOT / name).read_bytes())}  {name}" for name in files) + "\n", encoding="utf-8")
    print(json.dumps({"result": "SEALED-CANDIDATE-FREE", "head": HEAD, "tree": TREE, "window": "W83",
                      "ranks": [FIRST, LAST], "queueRanks": [853, 877], "firstSourceId": selected[0]["sourceId"],
                      "sources": len(selected), "cells": len(selected_cells),
                      "callers": sum(bool(row["productionCallerCount"]) for row in caller_rows),
                      "callerless": sum(not row["productionCallerCount"] for row in caller_rows),
                      "priorHolds": len(hold_attestation), "priorHoldStatuses": dict(hold_status),
                      "priorResolutions": len(resolution_rows), "priorAppliedTargets": len(applied_rows), "files": len(files)}, indent=2))


if __name__ == "__main__":
    main()
