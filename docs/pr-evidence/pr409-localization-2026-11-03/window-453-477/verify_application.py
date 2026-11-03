#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import subprocess

EVIDENCE = Path(__file__).resolve().parent
REPO = EVIDENCE.parents[3]
BASE = "1979c8dc4e59d5ca397251bcde73216a888aa9c9"
TREE = "8b5c0ef640f487741f0a08086cc6d60d5eef43a4"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

def load_jsonl_raw(path):
    rows = []
    for raw in path.read_bytes().splitlines(keepends=True):
        if raw.strip():
            rows.append((json.loads(raw), raw))
    return rows

def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, check=True, capture_output=True).stdout.decode().strip()

def git_bytes(path):
    return subprocess.run(["git", "show", f"{BASE}:{path}"], cwd=REPO, check=True, capture_output=True).stdout

def check_sums(root, name):
    for line in (root / name).read_text(encoding="utf-8").splitlines():
        digest, filename = line.split("  ", 1)
        assert sha((root / filename).read_bytes()) == digest, f"checksum: {root / filename}"

check_sums(EVIDENCE, "EVIDENCE-SHA256SUMS.txt")
check_sums(EVIDENCE / "candidate-free-input", "PACKET-SHA256SUMS.txt")
check_sums(EVIDENCE / "primary-review", "SHA256SUMS.txt")
check_sums(EVIDENCE / "blind-review", "SHA256SUMS.txt")
check_sums(EVIDENCE / "cross-audit", "SHA256SUMS.txt")
cross = EVIDENCE / "cross-audit"
assert (cross / "SHA256SUMS.sha256").read_text().strip() == sha((cross / "SHA256SUMS.txt").read_bytes())

inp = EVIDENCE / "candidate-free-input"
blind_root = EVIDENCE / "blind-review"
manifest = load_json(inp / "manifest.json")
att = load_json(inp / "head-tree-attestation.json")
assert manifest["repository"] == "snapetech-org/slskdN" and manifest["pullRequest"] == 409
assert manifest["head"] == BASE and manifest["tree"] == TREE
assert att["headRefOid"] == BASE and att["treeOid"] == TREE
assert att["branchRefOid"] == BASE and att["pullRefOid"] == BASE
assert load_json(blind_root / "blind-review" / "summary.json")["candidateFreeManifestJsonSha256"] == sha((inp / "manifest.json").read_bytes())

auth = load_json(EVIDENCE / "application-authorization.json")
plan = load_jsonl(EVIDENCE / "application-plan.jsonl")
readback = load_jsonl(EVIDENCE / "application-readback.jsonl")
verification = load_json(EVIDENCE / "application-verification.json")
cross_pairs = load_jsonl_raw(cross / "cross-audit-ledger.jsonl")
cross_rows = [r for r, _ in cross_pairs]
input_rows = load_jsonl(inp / "source-current-cells.jsonl")
assert auth["applicationApproved"] is True
assert auth["pinnedParentHead"] == BASE and auth["pinnedParentTree"] == TREE
assert auth["applicationPlanSha256"] == sha((EVIDENCE / "application-plan.jsonl").read_bytes())
assert len(plan) == 55 and len(readback) == 300 and len(cross_rows) == 300 and len(input_rows) == 300
assert auth["selectedUpdates"] == 55 and auth["retainedCurrent"] == 231 and auth["holdCount"] == 14
assert auth["reviewDisagreementRows"] == 59 and auth["unresolvedDisagreements"] == 0

key = lambda r: (r["continuationRank"], r["locale"])
cross_map = {key(r): r for r in cross_rows}
cross_raw_map = {key(r): raw for r, raw in cross_pairs}
input_map = {key(r): r for r in input_rows}
plan_map = {key(r): r for r in plan}
readback_map = {key(r): r for r in readback}
assert len(cross_map) == 300 and len(input_map) == 300 and len(plan_map) == 55 and len(readback_map) == 300

catalog_paths = sorted({r["catalogPath"] for r in cross_rows})
assert len(catalog_paths) == 12
before = {}
after = {}
ordered_keys = None
for path in catalog_paths:
    raw = git_bytes(path)
    obj = json.loads(raw)
    pin = next(r for r in cross_rows if r["catalogPath"] == path)
    assert len(obj) == 6176
    assert sha(raw) == pin["catalogFileSha256"]
    assert git("rev-parse", f"{BASE}:{path}") == pin["catalogGitBlob"]
    keys = list(obj)
    assert len(keys) == 6176
    assert sha(("\n".join(keys) + "\n").encode()) == load_jsonl(EVIDENCE / "candidate-free-input" / "catalog-structure.jsonl")[0]["orderedKeySha256"]
    if ordered_keys is None:
        ordered_keys = keys
    else:
        assert keys == ordered_keys
    before[path] = obj
    after[path] = json.loads((REPO / path).read_text(encoding="utf-8"))
    assert list(after[path]) == keys

expected_changes = set()
for row in plan:
    k = key(row)
    cr = cross_map[k]
    ir = input_map[k]
    assert cr["crossAuditDisposition"] == "propose-update"
    assert row["selectedTarget"] == cr["crossAuditTarget"]
    assert row["currentTarget"] == ir["currentTarget"] == cr["currentTarget"]
    assert row["catalogPath"] == cr["catalogPath"] == ir["catalogPath"]
    assert row["sourceId"] == cr["sourceId"] == ir["sourceId"]
    assert row["crossAuditLedgerRowSha256"] == sha(cross_raw_map[k])
    expected_changes.add((row["catalogPath"], row["catalogKey"], row["currentTarget"], row["selectedTarget"]))

actual_changes = set()
for path in catalog_paths:
    for catalog_key, old in before[path].items():
        new = after[path][catalog_key]
        if old != new:
            actual_changes.add((path, catalog_key, old, new))
assert actual_changes == expected_changes and len(actual_changes) == 55

for k, row in cross_map.items():
    ir = input_map[k]
    assert row["currentTarget"] == ir["currentTarget"]
    expected = row["crossAuditTarget"] if row["crossAuditDisposition"] == "propose-update" else row["currentTarget"]
    actual = after[row["catalogPath"]][row["catalogKey"]]
    rb = readback_map[k]
    assert actual == expected
    assert rb["expectedTargetSha256"] == sha(expected.encode())
    assert rb["actualTargetSha256"] == sha(actual.encode()) and rb["readbackMatches"] is True
    if row["crossAuditDisposition"] == "hold":
        assert row["continuationRank"] in {459, 475, 476}
        assert actual == row["currentTarget"]
assert sum(1 for r in cross_rows if r["crossAuditDisposition"] == "hold") == 14
assert sum(1 for r in cross_rows if r["crossAuditDisposition"] == "retain-current") == 231
assert sum(1 for r in cross_rows if r["crossAuditDisposition"] == "propose-update") == 55

assert verification["status"] == "PASS"
assert verification["parentHead"] == BASE and verification["parentTree"] == TREE
assert verification["readbackRows"] == 300 and verification["readbackMismatches"] == 0
assert verification["nonTargetValueChanges"] == 0
assert verification["planSha256"] == sha((EVIDENCE / "application-plan.jsonl").read_bytes())
assert verification["readbackSha256"] == sha((EVIDENCE / "application-readback.jsonl").read_bytes())
for path in catalog_paths:
    assert verification["baseCatalogSha256"][path] == sha(git_bytes(path))
    assert verification["postCatalogSha256"][path] == sha((REPO / path).read_bytes())

changed_names = git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()
if git("rev-parse", "HEAD") != BASE:
    assert git("rev-parse", "HEAD^") == BASE
    assert all(name.startswith("src/web/public/locales/") or name.startswith("docs/pr-evidence/pr409-localization-2026-11-03/window-453-477/") for name in changed_names)
    assert ".github/workflows" not in changed_names

print(json.dumps({
    "status": "PASS",
    "reviewedCells": 300,
    "updates": 55,
    "retained": 231,
    "holds": 14,
    "catalogs": 12,
    "orderedKeysPerCatalog": 6176,
    "nonTargetValueChanges": 0,
    "checksummedEvidenceFiles": len((EVIDENCE / "EVIDENCE-SHA256SUMS.txt").read_text().splitlines()),
}, indent=2))
