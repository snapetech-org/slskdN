#!/usr/bin/env python3
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
BASE = "2dc64b9d00f6611aeb72713af81db53ccc5a4084"
TREE = "f13462300926ac897235cd92ae68c87695c38c31"
EVIDENCE_PREFIX = "docs/pr-evidence/pr409-localization-2026-11-03/window-553-577/"

def read_json(path):
    return json.loads(path.read_text())

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()

def sha_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def key_order_hash(keys):
    return sha_bytes(("\n".join(keys) + "\n").encode("utf-8"))

def placeholders(value):
    return re.findall(r"\{[^{}]+\}", value)

def tags(value):
    return re.findall(r"</?[A-Za-z][^>]*>", value)

def numbers(value):
    return re.findall(r"[0-9]+(?:[.,][0-9]+)?", value)

def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args], text=True).strip()

def git_bytes(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])

def write_or_check(path, content):
    if path.exists():
        assert path.read_text() == content, str(path)
    else:
        path.write_text(content)

assert git("rev-parse", BASE) == BASE
assert git("rev-parse", BASE + "^{tree}") == TREE

INPUT = ROOT / "candidate-free-input"
PRIMARY = ROOT / "primary-review"
BLIND = ROOT / "blind-review"
CROSS = ROOT / "cross-audit"

for folder, sums in (
    (INPUT, "PACKET-SHA256SUMS.txt"),
    (PRIMARY, "SHA256SUMS.txt"),
    (BLIND, "SHA256SUMS.txt"),
    (CROSS, "SHA256SUMS.txt")
):
    subprocess.run(["sha256sum", "-c", sums], cwd=folder, check=True, stdout=subprocess.DEVNULL)
subprocess.run(["python3", "verify_cross_audit.py"], cwd=CROSS, check=True, stdout=subprocess.DEVNULL)

manifest = read_json(INPUT / "manifest.json")
assert manifest["head"] == BASE and manifest["tree"] == TREE
primary_manifest = read_json(PRIMARY / "manifest.json")
blind_manifest = read_json(BLIND / "manifest.json")
cross_manifest = read_json(CROSS / "manifest.json")
assert primary_manifest["head"] == blind_manifest["head"] == cross_manifest["head"] == BASE
assert primary_manifest["tree"] == blind_manifest["tree"] == cross_manifest["tree"] == TREE
assert primary_manifest["blindPacketAccessed"] is False
assert blind_manifest["primaryMaterialOpened"] is False
assert blind_manifest["primaryMaterialUsed"] is False
pins = read_json(ROOT / "review-packet-pins.json")
assert pins["candidateFreeInputManifestSha256"] == sha_bytes((INPUT / "manifest.json").read_bytes())
assert pins["candidateFreeChecksumListSha256"] == sha_bytes((INPUT / "PACKET-SHA256SUMS.txt").read_bytes())
assert pins["primaryManifestSha256"] == sha_bytes((PRIMARY / "manifest.json").read_bytes())
assert pins["primaryChecksumListSha256"] == sha_bytes((PRIMARY / "SHA256SUMS.txt").read_bytes())
assert pins["blindManifestSha256"] == sha_bytes((BLIND / "manifest.json").read_bytes())
assert pins["blindChecksumListSha256"] == sha_bytes((BLIND / "SHA256SUMS.txt").read_bytes())
assert pins["crossAuditManifestSha256"] == sha_bytes((CROSS / "manifest.json").read_bytes())
assert pins["crossAuditChecksumListSha256"] == sha_bytes((CROSS / "SHA256SUMS.txt").read_bytes())
assert pins["crossAuditLedgerSha256"] == sha_bytes((CROSS / "cross-audit-ledger.jsonl").read_bytes())
assert pins["finalProposalHashesSha256"] == sha_bytes((CROSS / "final-proposal-hashes.txt").read_bytes())
assert primary_manifest["inputManifestSha256"] == pins["candidateFreeInputManifestSha256"]
assert primary_manifest["inputChecksumListSha256"] == pins["candidateFreeChecksumListSha256"]
assert blind_manifest["candidateFreeInputManifestSha256"] == pins["candidateFreeInputManifestSha256"]
assert cross_manifest["candidateFreeInputManifestSha256"] == pins["candidateFreeInputManifestSha256"]
assert cross_manifest["primaryManifestSha256"] == pins["primaryManifestSha256"]
assert cross_manifest["primaryChecksumListSha256"] == pins["primaryChecksumListSha256"]
assert cross_manifest["blindManifestSha256"] == pins["blindManifestSha256"]
assert cross_manifest["blindChecksumListSha256"] == pins["blindChecksumListSha256"]

candidate_rows = read_jsonl(INPUT / "source-current-cells.jsonl")
primary_rows = read_jsonl(PRIMARY / "primary-ledger.jsonl")
blind_rows = read_jsonl(BLIND / "translation-ledger.jsonl")
cross_rows = read_jsonl(CROSS / "cross-audit-ledger.jsonl")
plan_rows = read_jsonl(ROOT / "application-plan.jsonl")
no_op_rows = read_jsonl(ROOT / "no-op-ledger.jsonl")
hold_rows = read_jsonl(ROOT / "hold-ledger.jsonl")
prior_rows = read_jsonl(INPUT / "prior-held-cell-reattestation.jsonl")
assert len(candidate_rows) == len(primary_rows) == len(blind_rows) == len(cross_rows) == 300
assert len(plan_rows) == 111 and len(no_op_rows) == 189 and len(hold_rows) == len(prior_rows) == 128

def keyed(rows):
    result = {(row["continuationRank"], row["locale"]): row for row in rows}
    assert len(result) == len(rows)
    return result

C = keyed(candidate_rows)
P = keyed(primary_rows)
B = keyed(blind_rows)
X = keyed(cross_rows)
assert set(C) == set(P) == set(B) == set(X)

for key, c in C.items():
    p, b, x = P[key], B[key], X[key]
    for field in ("sourceId", "source", "sourceSha256", "currentTarget", "currentTargetSha256",
                  "catalogPath", "catalogFileSha256", "catalogGitBlob", "callerContextSha256", "callerRefs"):
        assert p[field] == b[field] == x[field] == c[field], (key, field)
    assert c["sourceSha256"] == sha_text(c["source"])
    assert c["currentTargetSha256"] == sha_text(c["currentTarget"])
    assert p["head"] == b["head"] == x["head"] == BASE
    assert p["tree"] == b["tree"] == x["tree"] == TREE
    primary_target = p.get("proposedTarget", p["currentTarget"])
    blind_target = b["proposal"]
    assert p["reviewedTargetSha256"] == sha_text(primary_target)
    assert b["proposalSha256"] == sha_text(blind_target)
    assert x["primaryTarget"] == primary_target and x["blindTarget"] == blind_target
    assert x["primaryTargetSha256"] == sha_text(primary_target)
    assert x["blindTargetSha256"] == sha_text(blind_target)
    assert x["finalTargetSha256"] == sha_text(x["finalTarget"])
    assert x["catalogPath"] == c["catalogPath"]
    assert x["callerRefs"] and x["callerContextSha256"]

updates = keyed(plan_rows)
noops = keyed(no_op_rows)
assert len(updates) == 111 and len(noops) == 189
assert set(updates).isdisjoint(set(noops))
assert set(updates) | set(noops) == set(X)
for key, row in X.items():
    selected = updates[key] if key in updates else noops[key]
    for field in ("sourceId", "catalogPath", "currentTarget", "currentTargetSha256",
                  "finalTarget", "finalTargetSha256", "finalDisposition"):
        mapped = {
            "finalTarget": "selectedTarget",
            "finalTargetSha256": "selectedTargetSha256",
            "finalDisposition": "disposition"
        }.get(field, field)
        assert selected[mapped] == row[field], (key, mapped)
    assert selected["baseHead"] == BASE and selected["baseTree"] == TREE

structure_rows = read_jsonl(INPUT / "catalog-structure.jsonl")
structure = {row["catalogPath"]: row for row in structure_rows}
assert len(structure) == 12
BASE_CATALOGS = {}
CURRENT_CATALOGS = {}
updates_by_path = defaultdict(dict)
for row in plan_rows:
    path, key = row["catalogPath"], row["catalogKey"]
    assert key not in updates_by_path[path]
    updates_by_path[path][key] = row
assert set(updates_by_path) == set(structure)

for path, s in structure.items():
    base_bytes = git_bytes("show", BASE + ":" + path)
    base_obj = json.loads(base_bytes)
    base_keys = list(base_obj)
    assert sha_bytes(base_bytes) == s["sha256"]
    assert git("rev-parse", BASE + ":" + path) == s["gitBlob"]
    assert len(base_keys) == s["entryCount"] == 6176
    assert key_order_hash(base_keys) == s["orderedKeySha256"]
    BASE_CATALOGS[path] = base_obj
    current_bytes = (REPO / path).read_bytes()
    current_obj = json.loads(current_bytes)
    current_keys = list(current_obj)
    assert current_keys == base_keys and len(current_keys) == 6176
    assert key_order_hash(current_keys) == s["orderedKeySha256"]
    expected_keys = set(updates_by_path[path])
    changed_keys = {key for key in base_obj if base_obj[key] != current_obj[key]}
    assert changed_keys == expected_keys, (path, sorted(changed_keys ^ expected_keys))
    for key, value in base_obj.items():
        if key not in expected_keys:
            assert current_obj[key] == value, (path, key)
    for key, row in updates_by_path[path].items():
        assert base_obj[key] == row["currentTarget"]
        assert sha_text(base_obj[key]) == row["currentTargetSha256"]
        assert current_obj[key] == row["selectedTarget"]
        assert sha_text(current_obj[key]) == row["selectedTargetSha256"]
    CURRENT_CATALOGS[path] = current_obj

readback_rows = []
baseline_literal_mismatches = 0
for key in sorted(X):
    row = X[key]
    actual = CURRENT_CATALOGS[row["catalogPath"]][row["source"]]
    assert actual == row["finalTarget"] and sha_text(actual) == row["finalTargetSha256"]
    assert Counter(placeholders(row["source"])) == Counter(placeholders(actual))
    assert Counter(tags(row["source"])) == Counter(tags(actual))
    assert Counter(numbers(row["source"])) == Counter(numbers(actual))
    assert all(actual.count(lit) == row["source"].count(lit) for lit in row["sourceProtectedLiterals"])
    if any(row["currentTarget"].count(lit) != row["source"].count(lit) for lit in row["sourceProtectedLiterals"]):
        baseline_literal_mismatches += 1
    readback_rows.append({
        "schema": "slskdn-w67-catalog-readback/v1",
        "continuationRank": row["continuationRank"],
        "remainingQueueRank": row["remainingQueueRank"],
        "locale": row["locale"],
        "sourceId": row["sourceId"],
        "catalogPath": row["catalogPath"],
        "catalogKey": row["source"],
        "reviewDisposition": row["finalDisposition"],
        "selection": row["selection"],
        "currentTargetSha256": row["currentTargetSha256"],
        "selectedTargetSha256": row["finalTargetSha256"],
        "readbackTarget": actual,
        "readbackTargetSha256": sha_text(actual),
        "matchesSelectedHash": True
    })
prior = keyed(prior_rows)
holds = keyed(hold_rows)
assert set(prior) == set(holds) and len(holds) == 128
for key, source in prior.items():
    held = holds[key]
    path, catalog_key = source["currentCatalogPath"], source["source"]
    assert held["priorTargetSha256"] == held["currentTargetSha256"] == source["currentTargetSha256"]
    assert source["matchesPriorCurrentValue"] is True
    assert source["priorTargetSha256"] == sha_text(source["currentTarget"])
    assert held["status"] == "reattested-unchanged" and held["heldTargetTextIncluded"] is False
    assert CURRENT_CATALOGS[path][catalog_key] == source["currentTarget"]
    assert sha_text(CURRENT_CATALOGS[path][catalog_key]) == source["currentTargetSha256"]
    assert held["callerContextSha256"] == source["currentCallerContextSha256"]
    assert held["callerCount"] == source["currentCallerCount"]
    assert held["callerRefs"] == source["currentCallerRefs"]
    assert held["catalogPath"] == path
    assert held["catalogFileSha256"] == source["currentCatalogFileSha256"]
    assert held["catalogGitBlob"] == source["currentCatalogGitBlob"]

readback_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in readback_rows)
write_or_check(ROOT / "catalog-readback.jsonl", readback_text)
invariants = []
for path, s in sorted(structure.items()):
    base_obj = BASE_CATALOGS[path]
    current_obj = CURRENT_CATALOGS[path]
    changed = sorted(updates_by_path[path])
    base_bytes = git_bytes("show", BASE + ":" + path)
    current_bytes = (REPO / path).read_bytes()
    invariants.append({
        "catalogPath": path,
        "catalogSha256Before": sha_bytes(base_bytes),
        "catalogSha256After": sha_bytes(current_bytes),
        "catalogGitBlobBefore": git("rev-parse", BASE + ":" + path),
        "catalogGitBlobAfter": git("hash-object", path),
        "keyCountBefore": len(base_obj),
        "keyCountAfter": len(current_obj),
        "orderedKeySha256Before": key_order_hash(list(base_obj)),
        "orderedKeySha256After": key_order_hash(list(current_obj)),
        "keySetPreserved": set(base_obj) == set(current_obj),
        "keyOrderPreserved": list(base_obj) == list(current_obj),
        "changedEntryCount": len(changed),
        "changedCatalogKeys": changed,
        "nonTargetValuesChanged": 0
    })
invariants_text = json.dumps({
    "schema": "slskdn-w67-catalog-invariants/v1",
    "baseHead": BASE,
    "baseTree": TREE,
    "catalogCount": len(invariants),
    "catalogKeyCountPerFile": {row["catalogPath"]: row["keyCountAfter"] for row in invariants},
    "orderedKeySha256": structure_rows[0]["orderedKeySha256"],
    "catalogs": invariants
}, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
write_or_check(ROOT / "catalog-invariants.json", invariants_text)

changed_paths = set(git("diff", "--name-only", BASE).splitlines())
expected_catalog_paths = set(updates_by_path)
for path in changed_paths:
    assert path in expected_catalog_paths or path.startswith(EVIDENCE_PREFIX), path
for path in expected_catalog_paths:
    assert path in changed_paths
assert not any(path.startswith(".github/workflows/") for path in changed_paths)
status_output = subprocess.check_output(["git", "-C", str(REPO), "status", "--porcelain=1", "--untracked-files=all"], text=True)
for line in status_output.splitlines():
    path = line[3:]
    assert path.startswith(EVIDENCE_PREFIX) or path in expected_catalog_paths, line

application_result = read_json(ROOT / "application-result.json")
assert application_result["updateCount"] == 111
assert application_result["updatesByDisposition"] == {"correction": 72, "refinement": 39}
assert application_result["priorHoldsRetainedUnchanged"] == 128
assert application_result["newHolds"] == 0
assert baseline_literal_mismatches == 10
verification = {
    "schema": "slskdn-w67-application-verification/v1",
    "result": "PASS",
    "repository": "snapetech-org/slskdN",
    "pullRequest": 409,
    "baseHead": BASE,
    "baseTree": TREE,
    "reviewedCells": 300,
    "readbackCells": len(readback_rows),
    "updates": 111,
    "corrections": 72,
    "refinements": 39,
    "noOps": 189,
    "newHolds": 0,
    "priorHoldsRetainedUnchanged": 128,
    "catalogs": 12,
    "catalogKeysPerFile": 6176,
    "orderedKeySetAndOrderPreserved": True,
    "nonTargetCatalogValuesChanged": 0,
    "baselineProtectedLiteralMismatches": baseline_literal_mismatches,
    "finalProtectedLiteralMismatches": 0,
    "placeholderMarkupNumericMismatchCount": 0,
    "sourceCallerCatalogPins": "PASS",
    "completePrimaryBlindCrossEvidence": "PASS",
    "changedPathsWithinCatalogsAndEvidence": "PASS",
    "workflowFilesChanged": False,
    "projectTestsBuildsCiBrowserOrReleaseActions": "not run"
}
verification_text = json.dumps(verification, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
write_or_check(ROOT / "verification.json", verification_text)
print(json.dumps(verification, ensure_ascii=False, indent=2))
