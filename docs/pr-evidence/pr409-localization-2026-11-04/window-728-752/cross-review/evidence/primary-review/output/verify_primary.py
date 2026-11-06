#!/usr/bin/env python3
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
INPUT = ROOT.parent.parent / "candidate-free" / "input"

def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()

def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def fail(message):
    raise SystemExit("FAIL: " + message)

# Revalidate the source packet first, including its own file checksums.
iv = subprocess.check_output([sys.executable, str(INPUT / "verify_input.py")], text=True)
iv_obj = json.loads(iv)
if iv_obj.get("result") != "PASS":
    fail("candidate-free input verifier did not pass")
if iv_obj.get("head") != "70e5beffd5cd8d68b8aedffa5c85d16e2cc19b3f" or iv_obj.get("tree") != "14620c63bee971428fa1cd6cf1f4e944b86056a7":
    fail("candidate-free input pin mismatch")

input_manifest_sha = sha_bytes((INPUT / "manifest.json").read_bytes())
input_sums_sha = sha_bytes((INPUT / "PACKET-SHA256SUMS.txt").read_bytes())
boundary_sha = sha_bytes((INPUT / "selection-boundary.jsonl").read_bytes())
summary = json.loads((ROOT / "summary.json").read_text(encoding="utf-8"))
if summary["inputManifestSha256"] != input_manifest_sha or summary["inputChecksumListSha256"] != input_sums_sha or summary["selectionBoundarySha256"] != boundary_sha:
    fail("input evidence hash mismatch")

source_cells = jsonl(INPUT / "source-current-cells.jsonl")
ledger = jsonl(ROOT / "primary-review.jsonl")
corrections = jsonl(ROOT / "corrections.jsonl")
if len(source_cells) != 300 or len(ledger) != 300:
    fail("expected exactly 300 source and reviewed cells")
source_by_key = {(r["continuationRank"], r["locale"]): r for r in source_cells}
ledger_by_key = {(r["continuationRank"], r["locale"]): r for r in ledger}
if len(ledger_by_key) != 300 or set(source_by_key) != set(ledger_by_key):
    fail("cell coverage or uniqueness mismatch")

accepts = 0
corrects = 0
token_mismatch = 0
for key, source in source_by_key.items():
    row = ledger_by_key[key]
    rank, locale = key
    if row["head"] != "70e5beffd5cd8d68b8aedffa5c85d16e2cc19b3f" or row["tree"] != "14620c63bee971428fa1cd6cf1f4e944b86056a7":
        fail(f"wrong pin at {rank}/{locale}")
    for field in ("sourceId", "source", "sourceSha256", "catalogKey", "catalogPath", "currentTarget", "currentTargetSha256", "catalogFileSha256", "catalogGitBlob", "callerContextSha256", "callerRefs"):
        if row.get(field) != source.get(field):
            fail(f"input mismatch for {field} at {rank}/{locale}")
    if sha_bytes(row["source"].encode("utf-8")) != row["sourceSha256"]:
        fail(f"source hash mismatch at {rank}/{locale}")
    if sha_bytes(row["currentTarget"].encode("utf-8")) != row["currentTargetSha256"]:
        fail(f"current target hash mismatch at {rank}/{locale}")
    if not row["callerRefs"] or row["productionCallerCount"] < 1:
        fail(f"callerless decision at {rank}/{locale}")
    if not row["rationale"] or row["confidence"] not in ("high", "moderate", "low"):
        fail(f"missing rationale/confidence at {rank}/{locale}")
    if row["disposition"] == "accept-current":
        accepts += 1
        if row["target"] is not None:
            fail(f"accept-current has replacement at {rank}/{locale}")
    elif row["disposition"] == "correct":
        corrects += 1
        target = row["target"]
        if not isinstance(target, str) or not target:
            fail(f"correction has no text target at {rank}/{locale}")
        placeholders = re.findall(r"\{[^{}]+\}", row["source"])
        tags = re.findall(r"</?([A-Za-z][A-Za-z0-9]*)\b[^>]*>", row["source"])
        proposal = row["tokenCheck"]["proposedTargetCheck"]
        if proposal["placeholderTokens"] != placeholders or not proposal["placeholderParity"]:
            token_mismatch += 1
        if proposal["markupTags"] != tags or not proposal["markupParity"]:
            token_mismatch += 1
        if not proposal["numericTokensPreserved"] or not proposal["protectedLiteralsPreserved"]:
            token_mismatch += 1
    else:
        fail(f"unknown disposition at {rank}/{locale}")
if (accepts, corrects, token_mismatch) != (226, 74, 0):
    fail(f"disposition/token counts differ: accepts={accepts} corrects={corrects} token_mismatch={token_mismatch}")
if corrections != [r for r in ledger if r["disposition"] == "correct"]:
    fail("corrections extract differs from full ledger")

source_rewrites = json.loads((ROOT / "source-rewrite-recommendations.json").read_text(encoding="utf-8"))
if len(source_rewrites) != 2:
    fail("expected two source rewrite recommendations")
if {r["continuationRank"] for r in source_rewrites} != {732, 750}:
    fail("source rewrite rank mismatch")
for rewrite in source_rewrites:
    if len(rewrite["translations"]) != 12 or rewrite["translationCount"] != 12:
        fail(f"source rewrite locale coverage mismatch at {rewrite['continuationRank']}")
    matching = [r for r in corrections if r["continuationRank"] == rewrite["continuationRank"]]
    if len(matching) != 12:
        fail(f"source rewrite targets are not a complete 12-locale correction group at {rewrite['continuationRank']}")
    for row in matching:
        if rewrite["translations"].get(row["locale"]) != row["target"]:
            fail(f"source rewrite target mismatch at {rewrite['continuationRank']}/{row['locale']}")
        if row["sourceRewriteRecommendation"]["proposedSource"] != rewrite["proposedSource"]:
            fail(f"source rewrite link mismatch at {rewrite['continuationRank']}/{row['locale']}")

before = json.loads((ROOT / "live-before.json").read_text(encoding="utf-8"))
after = json.loads((ROOT / "live-after.json").read_text(encoding="utf-8"))
for live in (before, after):
    if live.get("state") != "OPEN" or live.get("isDraft") is not True or live.get("headRefOid") != "70e5beffd5cd8d68b8aedffa5c85d16e2cc19b3f":
        fail("PR live-state/head pin mismatch")
    if live.get("baseRefName") != "main" or "pull/409" not in live.get("url", ""):
        fail("PR base or URL mismatch")
if before != after:
    fail("PR state/head changed during primary review")

# Validate the output inventory and checksums. The manifest excludes itself and the
# checksum list to avoid a recursive digest; the checksum list includes the manifest.
manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
expected_paths = {item["path"] for item in manifest["files"]}
if "manifest.json" in expected_paths or "SHA256SUMS.txt" in expected_paths:
    fail("recursive manifest entry")
for item in manifest["files"]:
    p = ROOT / item["path"]
    if not p.is_file():
        fail("missing output file " + item["path"])
    data = p.read_bytes()
    if len(data) != item["bytes"] or sha_bytes(data) != item["sha256"]:
        fail("manifest file digest mismatch " + item["path"])
sum_entries = {}
for line in (ROOT / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    digest, name = line.split("  ", 1)
    sum_entries[name] = digest
if len(sum_entries) != len(set(sum_entries)):
    fail("duplicate checksum name")
for name, digest in sum_entries.items():
    p = ROOT / name
    if not p.is_file() or sha_bytes(p.read_bytes()) != digest:
        fail("checksum mismatch " + name)
if sum_entries.get("manifest.json") != sha_bytes((ROOT / "manifest.json").read_bytes()):
    fail("manifest checksum missing/mismatch")
if set(sum_entries) != (expected_paths | {"manifest.json"}):
    fail("checksum inventory differs from manifest inventory")

print(json.dumps({
    "result": "PASS",
    "head": summary["head"],
    "tree": summary["tree"],
    "sourceCount": summary["sourceCount"],
    "localeCount": summary["localeCount"],
    "cellCount": summary["cellCount"],
    "acceptCurrent": accepts,
    "correct": corrects,
    "sourceRewriteRecommendations": len(source_rewrites),
    "sourceRewriteTranslationCells": sum(r["translationCount"] for r in source_rewrites),
    "tokenMismatches": token_mismatch,
    "inputVerifier": "PASS",
    "livePr": "OPEN/DRAFT/CLEAN at pinned head",
    "checksums": len(sum_entries),
}, ensure_ascii=False))
