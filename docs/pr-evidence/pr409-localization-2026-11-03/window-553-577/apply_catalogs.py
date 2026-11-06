#!/usr/bin/env python3
import hashlib
import json
import subprocess
from collections import defaultdict
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

def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args], text=True).strip()

def skip_ws(text, index):
    while index < len(text) and text[index] in " \t\r\n":
        index += 1
    return index

def top_level_value_spans(text):
    decoder = json.JSONDecoder()
    index = skip_ws(text, 0)
    assert text[index] == "{"
    index += 1
    result = {}
    while True:
        index = skip_ws(text, index)
        if text[index] == "}":
            index += 1
            break
        key, consumed = decoder.raw_decode(text[index:])
        assert isinstance(key, str)
        index += consumed
        index = skip_ws(text, index)
        assert text[index] == ":"
        index = skip_ws(text, index + 1)
        start = index
        value, consumed = decoder.raw_decode(text[index:])
        assert isinstance(value, str)
        index += consumed
        assert key not in result
        result[key] = (start, index, value)
        index = skip_ws(text, index)
        if text[index] == ",":
            index += 1
        elif text[index] == "}":
            index += 1
            break
        else:
            raise AssertionError("invalid object delimiter")
    assert skip_ws(text, index) == len(text)
    return result

assert git("rev-parse", "HEAD") == BASE
assert git("rev-parse", BASE + "^{tree}") == TREE
assert git("diff", "--name-only") == ""
assert git("diff", "--cached", "--name-only") == ""

status = git("status", "--porcelain")
for line in status.splitlines():
    assert line.startswith("?? docs/pr-evidence/pr409-localization-2026-11-03/window-553-577"), line

plan = read_jsonl(ROOT / "application-plan.jsonl")
all_cells = read_jsonl(ROOT / "cross-audit" / "cross-audit-ledger.jsonl")
input_cells = read_jsonl(ROOT / "candidate-free-input" / "source-current-cells.jsonl")
structure_rows = read_jsonl(ROOT / "candidate-free-input" / "catalog-structure.jsonl")
assert len(plan) == 111 and len(all_cells) == len(input_cells) == 300
structure = {row["catalogPath"]: row for row in structure_rows}
updates_by_path = defaultdict(dict)
for row in plan:
    path, key = row["catalogPath"], row["catalogKey"]
    assert row["baseHead"] == BASE and row["baseTree"] == TREE
    assert row["selectedTargetSha256"] == sha_text(row["selectedTarget"])
    assert key not in updates_by_path[path]
    updates_by_path[path][key] = row

expected_hash = {row["catalogPath"]: row["catalogFileSha256Before"] for row in plan}
expected_blob = {row["catalogPath"]: row["catalogGitBlobBefore"] for row in plan}
assert set(updates_by_path) == set(structure)
changed_catalogs = []
for path in sorted(updates_by_path):
    file_path = REPO / path
    original_bytes = file_path.read_bytes()
    assert sha_bytes(original_bytes) == structure[path]["sha256"] == expected_hash[path]
    assert git("rev-parse", BASE + ":" + path) == structure[path]["gitBlob"] == expected_blob[path]
    original_text = original_bytes.decode("utf-8")
    before = json.loads(original_text)
    keys_before = list(before)
    assert len(keys_before) == structure[path]["entryCount"] == 6176
    spans = top_level_value_spans(original_text)
    assert list(spans) == keys_before
    replacements = []
    for key, row in updates_by_path[path].items():
        assert key in before and before[key] == row["currentTarget"]
        assert sha_text(before[key]) == row["currentTargetSha256"]
        replacements.append((spans[key][0], spans[key][1], json.dumps(row["selectedTarget"], ensure_ascii=False)))
    updated_text = original_text
    for start, end, value_token in sorted(replacements, reverse=True):
        updated_text = updated_text[:start] + value_token + updated_text[end:]
    after = json.loads(updated_text)
    assert list(after) == keys_before
    changed = {key for key in before if before[key] != after[key]}
    assert changed == set(updates_by_path[path])
    for key, row in updates_by_path[path].items():
        assert after[key] == row["selectedTarget"]
        assert sha_text(after[key]) == row["selectedTargetSha256"]
    for key in before:
        if key not in changed:
            assert after[key] == before[key]
    file_path.write_bytes(updated_text.encode("utf-8"))
    after_bytes = file_path.read_bytes()
    changed_catalogs.append({
        "catalogPath": path,
        "catalogSha256Before": sha_bytes(original_bytes),
        "catalogSha256After": sha_bytes(after_bytes),
        "catalogGitBlobBefore": expected_blob[path],
        "catalogGitBlobAfter": git("hash-object", path),
        "keyCountBefore": len(keys_before),
        "keyCountAfter": len(after),
        "changedEntryCount": len(changed),
        "changedCatalogKeys": sorted(changed),
        "nonTargetValuesChanged": 0
    })

result = {
    "schema": "slskdn-w67-application-result/v1",
    "repository": "snapetech-org/slskdN",
    "pullRequest": 409,
    "window": "W67",
    "baseHead": BASE,
    "baseTree": TREE,
    "reviewedCells": len(all_cells),
    "updateCount": len(plan),
    "updatesByDisposition": {
        "correction": sum(row["disposition"] == "correction" for row in plan),
        "refinement": sum(row["disposition"] == "refinement" for row in plan)
    },
    "catalogsChanged": len(changed_catalogs),
    "catalogs": changed_catalogs,
    "noOpCount": 189,
    "priorHoldsRetainedUnchanged": 128,
    "newHolds": 0,
    "applicationMethod": "Surgical JSON string-token replacement; preserves all non-target bytes, entry order, and key set.",
    "projectTestsBuildsCiBrowserActions": "not run"
}
(ROOT / "application-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
summary_path = ROOT / "application-plan-summary.json"
summary = read_json(summary_path)
summary["applicationPerformed"] = True
summary["applicationResultSha256"] = sha_bytes((ROOT / "application-result.json").read_bytes())
summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
print(json.dumps(result, ensure_ascii=False, indent=2))
