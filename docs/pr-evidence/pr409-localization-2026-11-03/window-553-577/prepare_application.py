#!/usr/bin/env python3
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
BASE = "2dc64b9d00f6611aeb72713af81db53ccc5a4084"
TREE = "f13462300926ac897235cd92ae68c87695c38c31"

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

def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args], text=True).strip()

def dump_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

assert git("rev-parse", "HEAD") == BASE
assert git("rev-parse", BASE + "^{tree}") == TREE
assert git("diff", "--name-only") == ""
assert git("diff", "--cached", "--name-only") == ""

for folder, sums in [
    (ROOT / "candidate-free-input", "PACKET-SHA256SUMS.txt"),
    (ROOT / "primary-review", "SHA256SUMS.txt"),
    (ROOT / "blind-review", "SHA256SUMS.txt"),
    (ROOT / "cross-audit", "SHA256SUMS.txt")
]:
    subprocess.run(["sha256sum", "-c", sums], cwd=folder, check=True, stdout=subprocess.DEVNULL)

subprocess.run(["python3", "verify_cross_audit.py"], cwd=ROOT / "cross-audit", check=True, stdout=subprocess.DEVNULL)

input_manifest = read_json(ROOT / "candidate-free-input" / "manifest.json")
primary_manifest = read_json(ROOT / "primary-review" / "manifest.json")
blind_manifest = read_json(ROOT / "blind-review" / "manifest.json")
cross_manifest = read_json(ROOT / "cross-audit" / "manifest.json")
assert input_manifest["head"] == primary_manifest["head"] == blind_manifest["head"] == cross_manifest["head"] == BASE
assert input_manifest["tree"] == primary_manifest["tree"] == blind_manifest["tree"] == cross_manifest["tree"] == TREE
assert primary_manifest["blindPacketAccessed"] is False
assert blind_manifest["primaryMaterialOpened"] is False and blind_manifest["primaryMaterialUsed"] is False

catalog_rows = read_jsonl(ROOT / "candidate-free-input" / "source-current-cells.jsonl")
cross_rows = read_jsonl(ROOT / "cross-audit" / "cross-audit-ledger.jsonl")
held_input = read_jsonl(ROOT / "candidate-free-input" / "prior-held-cell-reattestation.jsonl")
held_cross = read_jsonl(ROOT / "cross-audit" / "prior-held-cell-reattestation.jsonl")
structure_rows = read_jsonl(ROOT / "candidate-free-input" / "catalog-structure.jsonl")
assert len(catalog_rows) == len(cross_rows) == 300
assert len(held_input) == len(held_cross) == 128

input_cells = {(row["continuationRank"], row["locale"]): row for row in catalog_rows}
cross_cells = {(row["continuationRank"], row["locale"]): row for row in cross_rows}
assert len(input_cells) == len(cross_cells) == 300 and set(input_cells) == set(cross_cells)

for key, row in cross_cells.items():
    src = input_cells[key]
    for field in ("sourceId", "source", "sourceSha256", "currentTarget", "currentTargetSha256",
                  "catalogPath", "catalogFileSha256", "catalogGitBlob", "callerContextSha256", "callerRefs"):
        assert row[field] == src[field], (key, field)
    assert row["head"] == BASE and row["tree"] == TREE
    assert row["sourceSha256"] == sha_text(row["source"])
    assert row["currentTargetSha256"] == sha_text(row["currentTarget"])
    assert row["finalTargetSha256"] == sha_text(row["finalTarget"])

structure = {row["catalogPath"]: row for row in structure_rows}
assert len(structure) == 12

catalog_baseline = {}
for path, row in structure.items():
    file_path = REPO / path
    raw = file_path.read_bytes()
    assert sha_bytes(raw) == row["sha256"]
    assert git("rev-parse", BASE + ":" + path) == row["gitBlob"]
    obj = json.loads(raw)
    keys = list(obj.keys())
    assert len(keys) == row["entryCount"] == 6176
    assert key_order_hash(keys) == row["orderedKeySha256"]
    catalog_baseline[path] = obj

for key, cell in input_cells.items():
    path, source = cell["catalogPath"], cell["source"]
    assert source in catalog_baseline[path]
    assert catalog_baseline[path][source] == cell["currentTarget"]

updates = []
noops = []
for row in cross_rows:
    record = {
        "schema": "slskdn-w67-application-cell/v1",
        "repository": row["repository"],
        "pullRequest": row["pullRequest"],
        "window": "W67",
        "baseHead": BASE,
        "baseTree": TREE,
        "continuationRank": row["continuationRank"],
        "remainingQueueRank": row["remainingQueueRank"],
        "locale": row["locale"],
        "sourceId": row["sourceId"],
        "catalogPath": row["catalogPath"],
        "catalogKey": row["source"],
        "currentTarget": row["currentTarget"],
        "currentTargetSha256": row["currentTargetSha256"],
        "selectedTarget": row["finalTarget"],
        "selectedTargetSha256": row["finalTargetSha256"],
        "disposition": row["finalDisposition"],
        "crossAuditSelection": row["selection"],
        "crossAuditCategory": row["crossAuditCategory"],
        "catalogFileSha256Before": row["catalogFileSha256"],
        "catalogGitBlobBefore": row["catalogGitBlob"],
        "callerContextSha256": row["callerContextSha256"],
        "callerRefs": row["callerRefs"]
    }
    if row["finalDisposition"] in {"correction", "refinement"}:
        assert row["currentTarget"] != row["finalTarget"]
        updates.append(record)
    else:
        assert row["finalDisposition"] == "accept-current"
        assert row["currentTarget"] == row["finalTarget"]
        noops.append(record)

assert len(updates) == 111
assert Counter(row["disposition"] for row in updates) == Counter({"correction": 72, "refinement": 39})
assert len(noops) == 189
assert not any(row["finalDisposition"] == "hold" for row in cross_rows)

(ROOT / "application-plan.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in updates))
(ROOT / "no-op-ledger.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in noops))

hold_keyed = {(row["continuationRank"], row["locale"]): row for row in held_cross}
hold_inputs = {(row["continuationRank"], row["locale"]): row for row in held_input}
assert set(hold_keyed) == set(hold_inputs)
for key, row in hold_keyed.items():
    src = hold_inputs[key]
    assert row["priorTargetSha256"] == row["currentTargetSha256"] == src["currentTargetSha256"]
    assert row["sourceId"] == src["sourceId"] and row["sourceSha256"] == src["sourceSha256"]
    assert row["catalogPath"] == src["currentCatalogPath"]
(ROOT / "hold-ledger.jsonl").write_text("".join(json.dumps({
    "schema": "slskdn-w67-application-hold/v1",
    "action": "retain-unchanged",
    **row
}, ensure_ascii=False, sort_keys=True) + "\n" for row in held_cross))

by_locale = Counter(row["locale"] for row in updates)
review_pins = {
    "candidateFreeInputManifestSha256": sha_bytes((ROOT / "candidate-free-input" / "manifest.json").read_bytes()),
    "candidateFreeChecksumListSha256": sha_bytes((ROOT / "candidate-free-input" / "PACKET-SHA256SUMS.txt").read_bytes()),
    "primaryManifestSha256": sha_bytes((ROOT / "primary-review" / "manifest.json").read_bytes()),
    "primaryChecksumListSha256": sha_bytes((ROOT / "primary-review" / "SHA256SUMS.txt").read_bytes()),
    "blindManifestSha256": sha_bytes((ROOT / "blind-review" / "manifest.json").read_bytes()),
    "blindChecksumListSha256": sha_bytes((ROOT / "blind-review" / "SHA256SUMS.txt").read_bytes()),
    "crossAuditManifestSha256": sha_bytes((ROOT / "cross-audit" / "manifest.json").read_bytes()),
    "crossAuditChecksumListSha256": sha_bytes((ROOT / "cross-audit" / "SHA256SUMS.txt").read_bytes()),
    "crossAuditChecksumListDigest": sha_bytes((ROOT / "cross-audit" / "SHA256SUMS.txt").read_bytes()),
    "crossAuditLedgerSha256": sha_bytes((ROOT / "cross-audit" / "cross-audit-ledger.jsonl").read_bytes()),
    "finalProposalHashesSha256": sha_bytes((ROOT / "cross-audit" / "final-proposal-hashes.txt").read_bytes()),
    "crossAuditPacketPathAtCreation": "/home/keith/Documents/code/task-scratch/slskdn-pr409-w67-cross-audit-20261103"
}
dump_json(ROOT / "review-packet-pins.json", review_pins)

plan_summary = {
    "schema": "slskdn-w67-application-plan-summary/v1",
    "baseHead": BASE,
    "baseTree": TREE,
    "reviewedCells": 300,
    "updateCount": len(updates),
    "dispositionCounts": dict(Counter(row["disposition"] for row in updates)),
    "noOpCount": len(noops),
    "priorHoldsRetainedUnchanged": len(held_cross),
    "newHolds": 0,
    "updatesByLocale": {locale: by_locale[locale] for locale in sorted(by_locale)},
    "catalogFilesExpectedToChange": sorted({row["catalogPath"] for row in updates}),
    "catalogKeyCountPerLocale": {path: len(values) for path, values in sorted(catalog_baseline.items())},
    "orderedKeySha256": structure_rows[0]["orderedKeySha256"],
    "reviewPacketPins": review_pins,
    "applicationPerformed": False
}
dump_json(ROOT / "application-plan-summary.json", plan_summary)
print(json.dumps(plan_summary, ensure_ascii=False, indent=2))
