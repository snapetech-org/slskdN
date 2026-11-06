#!/usr/bin/env python3
"""Build W80 candidate-free exact-head source, caller, catalog, and hash lineage inputs."""
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
PREV = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w79-853-877-primary-20261104/candidate-free/input")
HEAD = "7a1ca27fd0519674c3b42a3e3df3638b0f671567"
TREE = "b3525218d0f9676c88c4991e78775d113f18b7d9"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
INV_PATH = "docs/pr-evidence/pr409-localization-2026-11-03/window49/primary/source-inventory.jsonl"
APP_PREFIX = "docs/pr-evidence/pr409-localization-2026-11-04/window-853-877/application/"
W79_PRODUCT = "7317d8fa46a54746f09853da18c16a8ef1845291"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
FIRST, LAST = 878, 902
FORBIDDEN = {"source", "sourceText", "target", "currentTarget", "proposedTarget", "proposedTargetText", "reason", "resolvedTarget", "resolvedTargetText", "formerTargetText"}


def sha(data): return hashlib.sha256(data).hexdigest()
def tsha(value): return sha(value.encode("utf-8"))
def blob_sha(data): return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
def canon(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
def git(*args): return subprocess.check_output(["git", "-C", str(REPO), *args])
def jread(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def jlines(path): return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
def wjson(name, value): (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
def wjsonl(name, values):
    with (ROOT / name).open("w", encoding="utf-8", newline="\n") as out:
        for value in values: out.write(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
def ph(value): return collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", value))
def tags(value): return collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", value))
def nums(value):
    return ["".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in token) for token in re.findall(r"\d+", value)]
def protected(value):
    vals = set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", value))
    vals.update(x for x in ("slskdN", "Tor", "Wishlist", "Chromaprint") if x in value)
    return sorted(vals)
def not_less(source, target):
    a, b = collections.Counter(source), collections.Counter(target)
    return all(b[token] >= n for token, n in a.items())
def hash_refs(refs):
    return [{k: r[k] for k in ("path", "line", "lineSha256", "contextSha256", "fileSha256", "gitBlob")} for r in refs]
def prod_path(path):
    parts = path.split("/"); name = parts[-1]; suffix = Path(name).suffix.lower()
    if not path.startswith("src/web/src/") or suffix not in {".js", ".jsx", ".ts", ".tsx"}: return False
    if any(p in {"__tests__", "__specs__"} for p in parts): return False
    if any(mark in name for mark in (".test.", ".spec.")): return False
    return True
def refs_for(source, runtime):
    pat = re.compile(r"(?<![A-Za-z0-9_$])([\"'])" + re.escape(source) + r"\1")
    found = []
    for rec in runtime:
        data = (REPO / rec["path"]).read_bytes()
        if sha(data) != rec["sha256"] or blob_sha(data) != rec["gitBlob"]: raise SystemExit("REFUSED: pinned runtime file changed: " + rec["path"])
        try: content = data.decode("utf-8")
        except UnicodeDecodeError: continue
        lines = content.splitlines()
        for n, line in enumerate(lines, 1):
            if not pat.search(line): continue
            context = [{"line": i + 1, "text": lines[i]} for i in range(max(0, n - 4), min(len(lines), n + 2))]
            found.append({"path": rec["path"], "line": n, "lineText": line, "lineSha256": tsha(line), "context": context,
                          "contextSha256": sha(canon(context)), "fileBytes": len(data), "fileSha256": sha(data),
                          "gitBlob": rec["gitBlob"], "gitBlobSha1Check": blob_sha(data)})
    return found
def forbidden_recursive(value):
    if isinstance(value, dict):
        return any(k in FORBIDDEN or forbidden_recursive(v) for k, v in value.items())
    if isinstance(value, list): return any(forbidden_recursive(v) for v in value)
    return False

def tree_entries():
    out = {}
    for ent in git("ls-tree", "-r", "-z", HEAD).split(b"\0"):
        if not ent: continue
        meta, path = ent.split(b"\t", 1); mode, kind, oid = meta.decode().split()
        out[path.decode()] = {"mode": mode, "type": kind, "gitBlob": oid}
    return out

def load_catalogs(tree):
    cats, rows, key_order = {}, [], None
    def no_duplicates(pairs):
        out = {}
        for key, val in pairs:
            if key in out: raise ValueError("duplicate key " + key)
            out[key] = val
        return out
    for locale in LOCALES:
        path = f"src/web/public/locales/{locale}.json"; raw = git("show", f"{HEAD}:{path}")
        if raw != (REPO / path).read_bytes(): raise SystemExit("REFUSED: catalog differs from pinned HEAD: " + locale)
        try: obj = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates)
        except Exception as ex: raise SystemExit("REFUSED: invalid/duplicate catalog " + locale + ": " + str(ex))
        keys = list(obj)
        if key_order is None: key_order = keys
        if keys != key_order or len(keys) != 6176 or any(not isinstance(v, str) or not v for v in obj.values()):
            raise SystemExit("REFUSED: catalog structure/coverage " + locale)
        cats[locale] = obj
        rows.append({"locale": locale, "catalogPath": path, "bytes": len(raw), "sha256": sha(raw), "gitBlob": tree[path]["gitBlob"],
                     "entryCount": len(keys), "nonemptyValueCount": sum(bool(v) for v in obj.values()),
                     "orderedKeySha256": sha(("\n".join(keys) + "\n").encode())})
    return cats, rows, key_order

def verify_checksums(folder):
    sums = {}
    for line in (folder / "PACKET-SHA256SUMS.txt").read_text().splitlines():
        if not line.strip(): continue
        digest, name = line.split("  ", 1)
        if name in sums: raise SystemExit("REFUSED: duplicate prior checksum name")
        sums[name] = digest
        if not (folder / name).is_file() or sha((folder / name).read_bytes()) != digest: raise SystemExit("REFUSED: prior W79 checksum mismatch: " + name)
    expected = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and p.name not in {"manifest.json", "PACKET-SHA256SUMS.txt"}}
    if set(sums) != expected | {"manifest.json"} or sha((folder / "manifest.json").read_bytes()) != sums["manifest.json"]:
        raise SystemExit("REFUSED: W79 prior packet inventory/checksum mismatch")
    return sha((folder / "manifest.json").read_bytes()), sha((folder / "PACKET-SHA256SUMS.txt").read_bytes())

def main():
    if git("rev-parse", "HEAD").decode().strip() != HEAD or git("rev-parse", "HEAD^{tree}").decode().strip() != TREE:
        raise SystemExit("REFUSED: source worktree is not exact W80 head/tree")
    if git("status", "--porcelain=v1").decode().strip(): raise SystemExit("REFUSED: source worktree is not clean")
    prev_manifest_sha, prev_checksums_sha = verify_checksums(PREV)
    w79_select = jlines(PREV / "source-inventory-selection.jsonl")
    w79_boundary = jread(PREV / "selection-and-boundary.json")
    w79_manifest = jread(PREV / "manifest.json")
    if (w79_manifest.get("window"), w79_manifest.get("head"), w79_manifest.get("tree"), w79_manifest.get("sourceCount")) != ("W79", "4d67527be0ca3b75e866f25bef5e58ae7f777f7f", "99ba5d8f7d631de3337e6b02f74af6d14e46c2ff", 25):
        raise SystemExit("REFUSED: W79 candidate-free predecessor identity")
    if len(w79_select) != 25 or (w79_boundary.get("nextUnselectedContinuationRank"), w79_boundary.get("nextUnselectedSourceId")) != (FIRST, "src_32ee02817c827552"):
        raise SystemExit("REFUSED: W79 continuation pointer/coverage")

    inv_raw = git("show", f"{HEAD}:{INV_PATH}")
    if inv_raw != (REPO / INV_PATH).read_bytes(): raise SystemExit("REFUSED: inventory differs from exact HEAD")
    inv = [json.loads(line) for line in inv_raw.decode().splitlines() if line.strip()]
    if len(inv) != 6176: raise SystemExit("REFUSED: inventory count")
    by_id = {r["sourceId"]: r for r in inv}; by_rank = {r["continuationRank"]: r for r in inv if r.get("continuationRank") is not None}
    if len(by_id) != len(inv): raise SystemExit("REFUSED: source IDs not unique")
    for r in inv:
        if r["sourceId"] != "src_" + tsha(r["source"])[:16] or r["sourceSha256"] != tsha(r["source"]): raise SystemExit("REFUSED: source inventory identity/hash")
    selected = [by_rank[n] for n in range(FIRST, LAST + 1)]
    if len(selected) != 25 or any(r.get("excluded") or r.get("localeCoverage") != 12 for r in selected): raise SystemExit("REFUSED: selected range excluded/incomplete")
    if [r["remainingQueueRank"] for r in selected] != list(range(778, 803)): raise SystemExit("REFUSED: W80 remaining ranks")
    if selected[0]["sourceId"] != w79_boundary["nextUnselectedSourceId"]: raise SystemExit("REFUSED: W79/W80 first source mismatch")

    old_ids = jlines(PREV / "prior-selected-id-exclusions-hash-only.jsonl")
    prev_sel_rows = []
    w79_evidence_sha = sha((PREV / "selection-and-boundary.json").read_bytes())
    for r in w79_select:
        prev_sel_rows.append({"sourceId": r["sourceId"], "sourceIdSha256": tsha(r["sourceId"]), "sourceSha256": r["sourceSha256"],
                              "selectionOrigin": "W79 candidate-free continuation selection", "continuationRank": r["continuationRank"],
                              "remainingQueueRank": r["remainingQueueRank"], "exclusionConfirmed": True,
                              "sourceTextIncluded": False, "targetTextIncluded": False, "selectionEvidenceSha256": w79_evidence_sha})
    all_ids = sorted(old_ids + prev_sel_rows, key=lambda r: r["sourceId"])
    if len(all_ids) != 1957 or len({r["sourceId"] for r in all_ids}) != len(all_ids): raise SystemExit("REFUSED: selected-ID lineage count/uniqueness")
    if any(forbidden_recursive(r) for r in all_ids): raise SystemExit("REFUSED: text in selected-ID hash ledger")
    for r in all_ids:
        now = by_id.get(r["sourceId"])
        if not now or now["sourceSha256"] != r["sourceSha256"]: raise SystemExit("REFUSED: selected-ID source hash drift")
    if {r["sourceId"] for r in all_ids} & {r["sourceId"] for r in selected}: raise SystemExit("REFUSED: selected source ID repeats prior window")

    tree = tree_entries()
    cats, catalog_rows, ordered = load_catalogs(tree)
    runtime = []
    for path, entry in sorted(tree.items()):
        if not prod_path(path): continue
        data = (REPO / path).read_bytes()
        if blob_sha(data) != entry["gitBlob"]: raise SystemExit("REFUSED: runtime git blob mismatch " + path)
        runtime.append({"path": path, "bytes": len(data), "sha256": sha(data), "gitBlob": entry["gitBlob"]})
    if len(runtime) != 279: raise SystemExit("REFUSED: bounded runtime file count differs")

    # W79 active hold lineage comes from its sealed candidate-free history plus its committed application holds.
    old_hold_inputs = jlines(PREV / "previous-window-prior-holds-hash-only.jsonl")
    old_resolutions = jlines(PREV / "prior-hold-resolution-history-hash-only.jsonl")
    old_lineage = jread(PREV / "prior-hold-lineage-summary.json")
    w79_callers = {r["sourceId"]: r for r in jlines(PREV / "caller-contexts.jsonl")}
    app_plan_raw = git("show", f"{HEAD}:{APP_PREFIX}application-plan.jsonl")
    app_holds_raw = git("show", f"{HEAD}:{APP_PREFIX}holds-hash-only.jsonl")
    product_raw = git("show", f"{HEAD}:{APP_PREFIX}product-commit.json")
    app_summary_raw = git("show", f"{HEAD}:{APP_PREFIX}application-summary.json")
    app_plan = [json.loads(line) for line in app_plan_raw.decode().splitlines() if line.strip()]
    app_holds = [json.loads(line) for line in app_holds_raw.decode().splitlines() if line.strip()]
    product = json.loads(product_raw.decode()); app_summary = json.loads(app_summary_raw.decode())
    if (len(app_plan), len(app_holds), product.get("commit"), product.get("parent"), product.get("changedValueCount"), app_summary.get("proposalCount"), app_summary.get("holdCount")) != (46, 39, W79_PRODUCT, "4d67527be0ca3b75e866f25bef5e58ae7f777f7f", 46, 46, 39):
        raise SystemExit("REFUSED: W79 committed application summary/plan coverage")
    if product.get("workflowPathsChanged") not in (None, 0) and app_summary.get("workflowPathsChanged") != 0: raise SystemExit("REFUSED: W79 application indicates workflow changes")
    subprocess.check_call(["git", "-C", str(REPO), "merge-base", "--is-ancestor", W79_PRODUCT, HEAD], stdout=subprocess.DEVNULL)
    w79_prev_callers = {r["sourceId"]: r for r in jlines(PREV / "caller-contexts.jsonl")}
    new_hold_inputs = []
    for h in app_holds:
        src = by_id.get(h["sourceId"]); caller = w79_prev_callers.get(h["sourceId"])
        if not src or not caller or src["sourceSha256"] != h["sourceSha256"] or caller["continuationRank"] != h["continuationRank"]:
            raise SystemExit("REFUSED: W79 hold source identity")
        refs = caller["callers"]; cref = hash_refs(refs); ctx_sha = sha(canon(refs))
        if ctx_sha != h["callerContextSha256"] or len(refs) != h["productionCallerCount"]: raise SystemExit("REFUSED: W79 hold caller evidence hash/count")
        if (h["sourceTextIncluded"], h["targetTextIncluded"]) != (False, False): raise SystemExit("REFUSED: W79 hold artifact text flags")
        row = {"schemaVersion": 1, "priorWindow": "W79", "continuationRank": h["continuationRank"], "remainingQueueRank": h["remainingQueueRank"],
               "sourceId": h["sourceId"], "sourceIdSha256": h["sourceIdSha256"], "sourceSha256": h["sourceSha256"], "locale": h["locale"],
               "priorDisposition": "hold", "priorTargetSha256": h["currentTargetSha256"], "holdReasonCode": h["holdReasonCode"],
               "holdReasonSha256": tsha(h["holdReasonCode"]), "priorCallerCount": len(refs), "priorCallerContextSha256": ctx_sha,
               "priorCallerRefs": cref, "currentCallerCount": len(refs), "currentCallerContextSha256": ctx_sha, "currentCallerRefs": cref,
               "callerEvidenceUnchanged": True, "currentTargetSha256": h["currentTargetSha256"], "matchesPriorCurrentValue": True,
               "callerlessHashOnly": len(refs) == 0, "sourceTextIncluded": False, "targetTextIncluded": False}
        new_hold_inputs.append(row)
    if sum(r["callerlessHashOnly"] for r in new_hold_inputs) != 24: raise SystemExit("REFUSED: W79 callerless hold count")
    previous_holds = old_hold_inputs + new_hold_inputs
    if len(previous_holds) != 382 or len(old_hold_inputs) != 343 or len(old_resolutions) != 13: raise SystemExit("REFUSED: W79 active hold/history lineage counts")
    if forbidden_recursive(previous_holds) or forbidden_recursive(old_resolutions): raise SystemExit("REFUSED: text in previous hold/resolution lineage")
    for h in previous_holds:
        if h.get("priorDisposition") != "hold": raise SystemExit("REFUSED: prior hold disposition")

    # Caller scans cover selected sources plus all active holds and historical resolutions.
    source_ids = {r["sourceId"] for r in selected} | {r["sourceId"] for r in previous_holds} | {r["sourceId"] for r in old_resolutions}
    full_refs = {sid: refs_for(by_id[sid]["source"], runtime) for sid in sorted(source_ids)}
    caller_rows = []
    for r in selected:
        refs = full_refs[r["sourceId"]]
        caller = {"continuationRank": r["continuationRank"], "remainingQueueRank": r["remainingQueueRank"], "sourceId": r["sourceId"],
                  "sourceSha256": r["sourceSha256"], "productionCallerCount": len(refs), "boundedScan": "Exact single- or double-quoted source literal scan of pinned src/web/src JS/TS runtime files; test/spec files excluded by filename and test/spec directories.",
                  "callers": refs, "sourceTextIncluded": bool(refs)}
        if refs: caller["source"] = r["source"]
        caller_rows.append(caller)

    # Reattest every active hold and resolution against W80 source, catalog, and bounded caller evidence.
    hold_attest, hold_counts = [], collections.Counter()
    for old in previous_holds:
        src = by_id.get(old["sourceId"]); locale = old["locale"]
        if not src or src["sourceSha256"] != old["sourceSha256"] or locale not in cats: raise SystemExit("REFUSED: prior hold source/catalog identity")
        refs = full_refs[old["sourceId"]]; ctx = sha(canon(refs)); current = cats[locale][src["source"]]; th = tsha(current)
        unchanged, target_same = ctx == old["currentCallerContextSha256"], th == old["priorTargetSha256"]
        status = "reattested-unchanged" if unchanged and target_same else "reattested-context-or-target-changed"
        hold_counts[status] += 1; cat = next(c for c in catalog_rows if c["locale"] == locale)
        hold_attest.append({"priorWindow": old["priorWindow"], "continuationRank": old["continuationRank"], "sourceId": old["sourceId"],
                            "sourceIdSha256": old["sourceIdSha256"], "sourceSha256": old["sourceSha256"], "locale": locale,
                            "priorDisposition": "hold", "priorTargetSha256": old["priorTargetSha256"], "currentTargetSha256": th,
                            "matchesPriorCurrentValue": target_same, "holdReasonSha256": old.get("holdReasonSha256", old.get("holdReasonSha256")),
                            "priorCallerCount": old["currentCallerCount"], "priorCallerContextSha256": old["currentCallerContextSha256"],
                            "priorCallerRefs": old["currentCallerRefs"], "currentCallerCount": len(refs), "currentCallerContextSha256": ctx,
                            "currentCallerRefs": hash_refs(refs), "callerEvidenceUnchanged": unchanged,
                            "currentCatalogPath": cat["catalogPath"], "currentCatalogFileSha256": cat["sha256"], "currentCatalogGitBlob": cat["gitBlob"],
                            "status": status, "sourceTextIncluded": False, "targetTextIncluded": False})
    resolution_attest = []
    for old in old_resolutions:
        src = by_id.get(old["sourceId"]); locale = old["locale"]
        if not src or src["sourceSha256"] != old["sourceSha256"] or locale not in cats: raise SystemExit("REFUSED: historical resolution identity")
        refs = full_refs[old["sourceId"]]; current_hash = tsha(cats[locale][src["source"]]); cat = next(c for c in catalog_rows if c["locale"] == locale)
        row = dict(old); row.update({"currentTargetSha256": current_hash, "currentTargetMatchesResolution": current_hash == old["resolvedTargetSha256"],
                                     "currentCallerCount": len(refs), "currentCallerContextSha256": sha(canon(refs)), "currentCallerRefs": hash_refs(refs),
                                     "currentCatalogPath": cat["catalogPath"], "currentCatalogFileSha256": cat["sha256"], "currentCatalogGitBlob": cat["gitBlob"],
                                     "sourceTextIncluded": False, "formerTargetTextIncluded": False, "resolvedTargetTextIncluded": False, "currentTargetTextIncluded": False})
        if forbidden_recursive(row): raise SystemExit("REFUSED: text in resolution lineage")
        resolution_attest.append(row)

    # Reattest all applied W78 targets and W79's 46 applied corrections using hashes only.
    prev_applied = jlines(PREV / "previous-window-applied-targets-hash-only.jsonl")
    if len(prev_applied) != 63 or forbidden_recursive(prev_applied): raise SystemExit("REFUSED: W78 applied-target lineage input")
    applied = []
    for old in prev_applied:
        src = by_id.get(old["sourceId"]); locale = old["locale"]
        if not src or src["sourceSha256"] != old["sourceSha256"] or locale not in cats: raise SystemExit("REFUSED: W78 applied target identity")
        target_hash = tsha(cats[locale][src["source"]]); cat = next(c for c in catalog_rows if c["locale"] == locale)
        if target_hash != old["appliedTargetSha256"]: raise SystemExit("REFUSED: W78 applied target changed at W80")
        row = dict(old); row.update({"attestedAtHead": HEAD, "currentTargetSha256": target_hash, "targetRemainsApplied": True,
                                    "currentCatalogFileSha256": cat["sha256"], "currentCatalogGitBlob": cat["gitBlob"],
                                    "sourceTextIncluded": False, "targetTextIncluded": False})
        applied.append(row)
    new_applied = []
    app_plan_sha = sha(app_plan_raw); catalog_by_locale = {c["locale"]: c for c in catalog_rows}
    for r in app_plan:
        src = by_id.get(r["sourceId"]); locale = r["locale"]
        if not src or src["sourceSha256"] != r["sourceSha256"] or r["catalogPath"] != f"src/web/public/locales/{locale}.json" or r["catalogKey"] != src["source"]: raise SystemExit("REFUSED: W79 applied plan source/catalog identity")
        if tsha(r["target"]) != r["targetSha256"]: raise SystemExit("REFUSED: W79 target hash in application plan")
        target_hash = tsha(cats[locale][src["source"]]); cat = catalog_by_locale[locale]
        if target_hash != r["targetSha256"]: raise SystemExit("REFUSED: W79 applied target no longer matches W80 catalog")
        row = {"priorWindow": "W79", "appliedHead": HEAD, "productCommit": W79_PRODUCT, "applicationPlanSha256": app_plan_sha,
               "continuationRank": r["continuationRank"], "remainingQueueRank": r["remainingQueueRank"], "sourceId": r["sourceId"],
               "sourceIdSha256": r["sourceIdSha256"], "sourceSha256": r["sourceSha256"], "locale": locale, "catalogPath": r["catalogPath"],
               "priorCurrentTargetSha256": r["currentTargetSha256"], "appliedTargetSha256": r["targetSha256"], "currentTargetSha256": target_hash,
               "targetRemainsApplied": True, "currentCatalogFileSha256": cat["sha256"], "currentCatalogGitBlob": cat["gitBlob"],
               "sourceTextIncluded": False, "targetTextIncluded": False}
        new_applied.append(row)
    if len(new_applied) != 46 or len(applied) + len(new_applied) != 109: raise SystemExit("REFUSED: applied-target lineage coverage")
    if forbidden_recursive(applied + new_applied): raise SystemExit("REFUSED: text in applied-target ledger")

    # Candidate-free current selected cells and token parity evidence.
    cells, mismatch = [], collections.Counter(); mismatch_examples = []
    for source in selected:
        sid, src_text = source["sourceId"], source["source"]; refs = full_refs[sid]; compact = hash_refs(refs); ctx = sha(canon(refs))
        for locale in LOCALES:
            current = cats[locale][src_text]; sph, cph = ph(src_text), ph(current); st, ct = tags(src_text), tags(current)
            sn, cn = nums(src_text), nums(current); sp, cp = protected(src_text), protected(current)
            oks = {"placeholder": sph == cph, "markup": st == ct, "numeric": not_less(sn, cn), "protectedLiteral": all(x in current for x in sp)}
            for kind, ok in oks.items():
                if not ok: mismatch[kind] += 1; mismatch_examples.append({"continuationRank": source["continuationRank"], "sourceId": sid, "locale": locale, "kind": kind})
            cat = catalog_by_locale[locale]
            row = {"continuationRank": source["continuationRank"], "remainingQueueRank": source["remainingQueueRank"], "sourceId": sid,
                   "sourceSha256": source["sourceSha256"], "locale": locale, "catalogPath": cat["catalogPath"],
                   "catalogFileSha256": cat["sha256"], "catalogGitBlob": cat["gitBlob"], "currentTargetSha256": tsha(current),
                   "callerContextSha256": ctx, "callerRefs": compact, "sourceTextIncluded": bool(refs), "currentTargetTextIncluded": bool(refs),
                   "containsCandidate": False, "verdict": None}
            if refs:
                row.update({"source": src_text, "catalogKey": src_text, "currentTarget": current,
                            "placeholderEvidence": {"sourceTokens": sorted(sph.elements()), "currentTokens": sorted(cph.elements()), "matches": oks["placeholder"]},
                            "markupEvidence": {"sourceTags": sorted(st.elements()), "currentTags": sorted(ct.elements()), "matches": oks["markup"]},
                            "sourceNumericTokens": sn, "currentNumericTokens": cn, "numericTokensPreserved": oks["numeric"],
                            "sourceProtectedLiterals": sp, "currentProtectedLiterals": [x for x in sp if x in current],
                            "missingProtectedLiterals": [x for x in sp if x not in current],
                            "protectedLiteralEvidence": {"sourceTokens": sp, "currentTokens": [x for x in sp if x in current], "matches": oks["protectedLiteral"]}})
            else:
                row["tokenEvidenceSha256"] = sha(canon({"placeholderParity": oks["placeholder"], "markupParity": oks["markup"],
                                                         "numericTokensPreserved": oks["numeric"], "protectedLiteralsPreserved": oks["protectedLiteral"]}))
            cells.append(row)
    if len(cells) != 300: raise SystemExit("REFUSED: selected cell coverage")

    boundary_prev, boundary_next = by_rank[877], by_rank[903]
    def boundary_row(r, role): return {"continuationRank": r["continuationRank"], "remainingQueueRank": r["remainingQueueRank"], "sourceId": r["sourceId"],
                                      "sourceSha256": r["sourceSha256"], "localeCoverage": r["localeCoverage"], "excluded": r.get("excluded", False),
                                      "boundaryRole": role, "sourceTextIncluded": False}
    boundary = [boundary_row(boundary_prev, "previous-window-final")] + [boundary_row(r, "selected-window") for r in selected] + [boundary_row(boundary_next, "next-unselected")]
    selection_rows = [{"continuationRank": r["continuationRank"], "remainingQueueRank": r["remainingQueueRank"], "sourceId": r["sourceId"],
                       "sourceSha256": r["sourceSha256"], "localeCoverage": r["localeCoverage"], "excluded": False, "sourceTextIncluded": False} for r in selected]

    inv_projection = [{k: r[k] for k in ("sourceId", "sourceSha256", "continuationRank", "remainingQueueRank", "localeCoverage", "excluded") if k in r} for r in inv]
    wjsonl("source-inventory-pinned.jsonl", inv_projection); wjsonl("source-inventory-selection.jsonl", selection_rows); wjsonl("selection-boundary.jsonl", boundary)
    wjsonl("catalog-structure.jsonl", catalog_rows); wjsonl("runtime-file-pins.jsonl", runtime); wjsonl("caller-contexts.jsonl", caller_rows)
    wjsonl("source-current-cells.jsonl", cells); wjsonl("prior-selected-id-exclusions-hash-only.jsonl", all_ids); wjsonl("previous-window-selection-hash-only.jsonl", prev_sel_rows)
    wjsonl("previous-window-prior-holds-hash-only.jsonl", previous_holds); wjsonl("previous-window-holds-hash-only.jsonl", new_hold_inputs)
    wjsonl("prior-held-cell-reattestation-hash-only.jsonl", hold_attest); wjsonl("prior-hold-resolution-history-hash-only.jsonl", resolution_attest)
    wjsonl("previous-window-applied-targets-hash-only.jsonl", new_applied); wjsonl("prior-applied-targets-reattestation-hash-only.jsonl", applied + new_applied)
    (ROOT / "previous-window-product-commit.json").write_bytes(product_raw)
    wjson("previous-window-application-summary.json", {k: app_summary[k] for k in ("artifact", "window", "headBeforeApply", "treeBeforeApply", "productCommit", "proposalCount", "keepCount", "holdCount", "callerlessHashOnlyHoldCount", "callerBackedHoldCount", "readbackCellCount", "catalogCount", "catalogKeyCountPerLocale", "catalogKeyOrderUnchanged", "workflowPathsChanged", "testsBuildsScansCiRun") if k in app_summary} | {"applicationPlanSha256": app_plan_sha, "applicationHoldsSha256": sha(app_holds_raw), "sourceTextIncluded": False, "targetTextIncluded": False})
    wjson("prior-hold-lineage-summary.json", {"carriedHoldCells": len(previous_holds), "holdLineage": dict(old_lineage["holdLineage"]) | {"W79": len(new_hold_inputs)},
         "previouslyResolvedHistoricalRows": len(old_resolutions), "resolutionRowsTextFree": True})
    wjson("prior-held-cell-reattestation-summary.json", {"priorHeldCellsReattested": len(hold_attest), "allTargetHashesMatchPrior": all(r["matchesPriorCurrentValue"] for r in hold_attest),
         "callerEvidenceUnchanged": sum(r["callerEvidenceUnchanged"] for r in hold_attest), "callerEvidenceChanged": sum(not r["callerEvidenceUnchanged"] for r in hold_attest),
         "statusCounts": dict(hold_counts), "holdRowsTextFree": True})
    wjson("prior-applied-targets-summary.json", {"priorAppliedTargetsReattested": len(applied + new_applied), "allTargetsRemainApplied": all(r["targetRemainsApplied"] for r in applied + new_applied),
         "windows": {"W78": len(applied), "W79": len(new_applied)}, "targetTextIncluded": False, "sourceTextIncluded": False})
    wjson("baseline-token-mismatch-summary.json", {"cellCount": len(cells), "mismatchCellCount": sum(mismatch.values()),
         "mismatchCounts": {k: mismatch.get(k, 0) for k in ("placeholder", "markup", "numeric", "protectedLiteral")}, "mismatchExamples": mismatch_examples})
    wjson("continuity-provenance.json", {"previousWindow": "W79", "previousHead": "4d67527be0ca3b75e866f25bef5e58ae7f777f7f", "previousTree": "99ba5d8f7d631de3337e6b02f74af6d14e46c2ff",
         "previousCandidateFreeManifestSha256": prev_manifest_sha, "previousCandidateFreeChecksumListSha256": prev_checksums_sha,
         "priorSelectedIdExclusionRows": len(all_ids), "w79SelectedIdsAdded": len(prev_sel_rows), "priorHeldCells": len(previous_holds), "w79HoldsAdded": len(new_hold_inputs),
         "priorResolvedHoldHistoryRows": len(resolution_attest), "priorSelectedIdsSha256": sha((ROOT / "prior-selected-id-exclusions-hash-only.jsonl").read_bytes()),
         "activeHoldLedgerSha256": sha((ROOT / "previous-window-prior-holds-hash-only.jsonl").read_bytes()),
         "priorHoldReattestationSha256": sha((ROOT / "prior-held-cell-reattestation-hash-only.jsonl").read_bytes()),
         "priorResolutionReattestationSha256": sha((ROOT / "prior-hold-resolution-history-hash-only.jsonl").read_bytes()),
         "w79ApplicationPlanSha256": app_plan_sha, "w79ApplicationHoldsSha256": sha(app_holds_raw), "w79ProductCommitSha256": sha(product_raw),
         "w79AppliedTargetHashLedgerSha256": sha((ROOT / "previous-window-applied-targets-hash-only.jsonl").read_bytes()),
         "priorAppliedTargetsReattested": len(applied + new_applied), "previousAppliedTargetsByWindow": {"W78": len(applied), "W79": len(new_applied)},
         "previousPrimaryReviewTargetsUsed": False, "blindReviewUsed": False, "crossReviewUsed": False, "prBodyQueried": False})
    wjson("selection-and-boundary.json", {"repository": "snapetech-org/slskdN", "pullRequest": 409, "window": "W80", "branch": BRANCH, "head": HEAD, "tree": TREE,
         "candidateFree": True, "locales": LOCALES, "sourceCount": 25, "cellCount": 300, "continuationRankRange": [FIRST, LAST], "remainingQueueRankRange": [778, 802],
         "previousWindow": "W79", "previousWindowFinalContinuationRank": 877, "previousWindowFinalSourceId": boundary_prev["sourceId"], "firstSelectedSourceId": selected[0]["sourceId"],
         "nextUnselectedContinuationRank": 903, "nextUnselectedSourceId": boundary_next["sourceId"], "orderedCatalogKeySha256": sha(("\n".join(ordered) + "\n").encode()),
         "catalogEntryCountPerLocale": 6176, "priorSelectedIdsExcluded": len(all_ids), "priorHeldCellsReattested": len(hold_attest),
         "priorHoldResolutionHistoryRows": len(resolution_attest), "priorAppliedTargetsReattested": len(applied + new_applied), "proposedTargetsIncluded": False, "reviewDecisionsIncluded": False})
    wjson("source-tree-attestation.json", {"head": HEAD, "tree": TREE, "sourceRoot": "src/web/src", "treeEnumeration": "git ls-tree -r -z at exact pinned commit",
         "treeEntryCount": len(tree), "productionFileCount": len(runtime), "sourceInventoryPath": INV_PATH, "sourceInventoryRawSha256": sha(inv_raw),
         "sourceInventoryProjectionSha256": sha((ROOT / "source-inventory-pinned.jsonl").read_bytes()), "callerScan": "exact single- or double-quoted source literal scan",
         "testAndSpecFilesExcluded": True, "runtimeFilePinsSha256": sha((ROOT / "runtime-file-pins.jsonl").read_bytes())})
    print(json.dumps({"result": "BUILT-CANDIDATE-FREE-UNSEALED", "head": HEAD, "tree": TREE, "sourceCount": len(selected), "localeCount": len(LOCALES),
         "cellCount": len(cells), "runtimeFiles": len(runtime), "sourcesWithCallers": sum(bool(r["productionCallerCount"]) for r in caller_rows),
         "sourcesWithoutCallers": sum(not r["productionCallerCount"] for r in caller_rows), "priorSelectedIds": len(all_ids), "priorHeldCells": len(hold_attest),
         "priorHoldResolutions": len(resolution_attest), "priorAppliedTargets": len(applied + new_applied), "w79CorrectionsReattested": len(new_applied),
         "w79Holds": len(new_hold_inputs), "w79CallerlessHolds": sum(r["callerlessHashOnly"] for r in new_hold_inputs),
         "allPriorHoldTargetsMatch": all(r["matchesPriorCurrentValue"] for r in hold_attest), "allPriorCallerEvidenceUnchanged": all(r["callerEvidenceUnchanged"] for r in hold_attest),
         "tokenMismatches": {k: mismatch.get(k, 0) for k in ("placeholder", "markup", "numeric", "protectedLiteral")}, "prBodyQueried": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
