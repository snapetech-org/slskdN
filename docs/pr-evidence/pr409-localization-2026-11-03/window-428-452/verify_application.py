#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import subprocess

EVIDENCE = Path(__file__).resolve().parent
REPO = EVIDENCE.parents[3]
BASE = "9674df03ab94a39da1eafe265c95d85a28be96c9"
BASE_TREE = "7be8469c96c8c703b1dc8ef0486baa9ff0777115"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
EXPECTED_CROSS_SUMS = "b735d3575066db9696b0de1aed59155fed078476cedf396495b88f34635cdca8"
EXPECTED_INPUT_SUMS = "005097b25bd89a302b4caebd4478013fbc5b239c210f841613b5edb6d706660b"
EXPECTED_INPUT_MANIFEST = "bb5c8dd36775fa59fe17335ed8260498484d40adf89b6e565386d92dd5d75bd4"
EXPECTED_PRIMARY_SUMS = "6057ebfea2c6d4d527059b414f1e91768b7b7fcf72709089d34b5092dfdeee28"
EXPECTED_BLIND_SUMS = "a24a3708b562a6219eb47559f4747bd8b42702b884d2b56029348a96e7df3464"
PLACEHOLDER = re.compile(r"\{[^{}]+\}")
MARKUP = re.compile(r"</?[A-Za-z][^>]*>")
NUMBER = re.compile(r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)*(?![A-Za-z0-9])")

def sha(data):
    return hashlib.sha256(data).hexdigest()

def j(path):
    return json.loads(path.read_text(encoding="utf-8"))

def jl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, check=True, capture_output=True).stdout

def verify_sums(directory, sums_name, exact_tree=True):
    sums = directory / sums_name
    entries = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, name = line.split(None, 1)
        name = name.lstrip("* ")
        path = (directory / name).resolve()
        if directory.resolve() not in path.parents:
            raise SystemExit(f"unsafe checksum path: {name}")
        if sha(path.read_bytes()) != expected:
            raise SystemExit(f"checksum mismatch: {directory.name}/{name}")
        entries[name] = expected
    if exact_tree:
        actual = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file() and p != sums}
        if actual != set(entries):
            raise SystemExit(f"checksum coverage mismatch: {directory}")
    return entries

def patch_catalog_bytes(raw, updates):
    lines = raw.decode("utf-8").splitlines(keepends=True)
    decoder = json.JSONDecoder()
    remaining = set(updates)
    out = []
    for line in lines:
        body = line.rstrip("\r\n")
        newline = line[len(body):]
        replacement = body + newline
        for key in tuple(remaining):
            encoded = json.dumps(key, ensure_ascii=False)
            indent = body[:len(body) - len(body.lstrip())]
            if not body.startswith(indent + encoded):
                continue
            key_end = len(indent) + len(encoded)
            colon_match = re.match(r"\s*:\s*", body[key_end:])
            if not colon_match:
                continue
            value_start = key_end + colon_match.end()
            current_value, value_end = decoder.raw_decode(body, value_start)
            expected_current = updates[key]["currentTarget"]
            if current_value != expected_current:
                raise SystemExit(f"baseline target mismatch: {key}")
            target = updates[key]["selectedTarget"]
            replacement = body[:value_start] + json.dumps(target, ensure_ascii=False) + body[value_end:] + newline
            remaining.remove(key)
            break
        out.append(replacement)
    if remaining:
        raise SystemExit(f"catalog keys missing from line-preserving patch: {sorted(remaining)}")
    return "".join(out).encode("utf-8")

if subprocess.run(["git", "rev-parse", BASE], cwd=REPO, check=True, capture_output=True, text=True).stdout.strip() == "":
    raise SystemExit("pinned parent commit is unavailable")
if subprocess.run(["git", "rev-parse", f"{BASE}^{{tree}}"], cwd=REPO, check=True, capture_output=True, text=True).stdout.strip() != BASE_TREE:
    raise SystemExit("pinned parent tree mismatch")

candidate = EVIDENCE / "candidate-free-input"
primary = EVIDENCE / "primary-review"
blind = EVIDENCE / "blind-review"
audit = EVIDENCE / "cross-audit"
verify_sums(candidate, "PACKET-SHA256SUMS.txt")
verify_sums(primary, "PRIMARY-SHA256SUMS.txt")
verify_sums(blind, "SHA256SUMS.txt")
verify_sums(audit, "SHA256SUMS.txt")
verify_sums(EVIDENCE, "EVIDENCE-SHA256SUMS.txt")
assert sha((candidate/"manifest.json").read_bytes()) == EXPECTED_INPUT_MANIFEST
assert sha((candidate/"PACKET-SHA256SUMS.txt").read_bytes()) == EXPECTED_INPUT_SUMS
assert sha((primary/"PRIMARY-SHA256SUMS.txt").read_bytes()) == EXPECTED_PRIMARY_SUMS
assert sha((blind/"SHA256SUMS.txt").read_bytes()) == EXPECTED_BLIND_SUMS
assert sha((audit/"SHA256SUMS.txt").read_bytes()) == EXPECTED_CROSS_SUMS

# The sealed source reviewers remain reproducibly verifiable from the copied evidence tree.
subprocess.run(["python3", str(blind/"verify_blind_review.py")], cwd=EVIDENCE, check=True, capture_output=True, text=True)
subprocess.run(["python3", str(audit/"verify_cross_audit.py")], cwd=EVIDENCE, check=True, capture_output=True, text=True)

manifest = j(candidate/"manifest.json")
cross_summary = j(audit/"summary.json")
authorization = j(EVIDENCE/"application-authorization.json")
verification = j(EVIDENCE/"application-verification.json")
assert manifest["head"] == BASE and manifest["tree"] == BASE_TREE
assert cross_summary["head"] == BASE and cross_summary["tree"] == BASE_TREE
assert cross_summary["reviewedCells"] == 300 and cross_summary["selectedUpdates"] == 76
assert cross_summary["dispositions"] == {"accept-current":200,"correction":45,"hold":24,"refinement":31}
assert authorization["applicationApproved"] is True
assert authorization["pinnedParentHead"] == BASE and authorization["pinnedParentTree"] == BASE_TREE
assert authorization["rootCrossAuditChecksumListSha256"] == EXPECTED_CROSS_SUMS

plan = jl(EVIDENCE/"application-plan.jsonl")
ledger = jl(audit/"cross-audit-ledger.jsonl")
readback = jl(EVIDENCE/"application-readback.jsonl")
plan_by_key = {(x["continuationRank"],x["locale"]):x for x in plan}
ledger_by_key = {(x["continuationRank"],x["locale"]):x for x in ledger}
readback_by_key = {(x["continuationRank"],x["locale"]):x for x in readback}
assert len(ledger) == len(readback) == 300 and len(plan) == 76
assert len(plan_by_key) == 76 and len(ledger_by_key) == 300 and len(readback_by_key) == 300
assert set(ledger_by_key) == set(readback_by_key)
expected_plan = {key:row for key,row in ledger_by_key.items() if row["selectedTarget"] != row["currentTarget"]}
assert set(plan_by_key) == set(expected_plan)
for key, row in plan_by_key.items():
    source = expected_plan[key]
    assert row["source"] == source["source"]
    assert row["sourceId"] == source["sourceId"]
    assert row["currentTarget"] == source["currentTarget"]
    assert row["currentTargetSha256"] == source["currentTargetSha256"]
    assert row["selectedTarget"] == source["selectedTarget"]
    assert row["selectedTargetSha256"] == source["selectedTargetSha256"]
    assert row["disposition"] == source["disposition"]
assert Counter(x["disposition"] for x in plan) == {"correction":45,"refinement":31}
assert {x["continuationRank"] for x in ledger if x["disposition"]=="hold"} == {438,452}
assert sum(x["disposition"]=="hold" for x in ledger) == 24

structure = {x["catalogPath"]:x for x in jl(candidate/"catalog-structure.jsonl")}
assert len(structure) == 12
updates_by_file = {}
for row in plan:
    updates_by_file.setdefault(row["catalogPath"], {})[row["catalogKey"]] = row
catalogs_before = {}
catalogs_after = {}
expected_bytes_by_file = {}
for path, pin in structure.items():
    base_bytes = git("show", f"{BASE}:{path}")
    assert sha(base_bytes) == pin["sha256"]
    assert git("rev-parse", f"{BASE}:{path}").decode().strip() == pin["gitBlob"]
    base_obj = json.loads(base_bytes)
    assert len(base_obj) == pin["entryCount"] == 6176
    catalogs_before[path] = base_obj
    updates = updates_by_file.get(path, {})
    expected_bytes = patch_catalog_bytes(base_bytes, updates) if updates else base_bytes
    expected_bytes_by_file[path] = expected_bytes
    actual_bytes = (REPO/path).read_bytes()
    if actual_bytes != expected_bytes:
        raise SystemExit(f"exact line-preserving catalog patch mismatch: {path}")
    actual_obj = json.loads(actual_bytes)
    assert list(actual_obj.keys()) == list(base_obj.keys())
    assert len(actual_obj) == len(base_obj) == 6176
    for key, old_value in base_obj.items():
        expected_value = updates[key]["selectedTarget"] if key in updates else old_value
        if actual_obj.get(key) != expected_value:
            raise SystemExit(f"catalog value/readback mismatch: {path}:{key}")
    catalogs_after[path] = actual_obj
assert len(updates_by_file) == 12

for key, row in ledger_by_key.items():
    plan_row = plan_by_key.get(key)
    target = plan_row["selectedTarget"] if plan_row else row["currentTarget"]
    actual = catalogs_after[row["catalogPath"]][row["source"]]
    assert actual == target
    rb = readback_by_key[key]
    assert rb["expectedTarget"] == target and rb["actualTarget"] == actual
    assert rb["actualTargetSha256"] == sha(actual.encode("utf-8"))
    assert rb["sourceId"] == row["sourceId"]
    assert rb["catalogPath"] == row["catalogPath"]
    assert rb["status"] == ("applied" if plan_row else "hold-preserved" if row["disposition"]=="hold" else "unchanged-current")
    assert Counter(PLACEHOLDER.findall(row["source"])) == Counter(PLACEHOLDER.findall(target))
    assert MARKUP.findall(row["source"]) == MARKUP.findall(target)
    assert Counter(NUMBER.findall(row["source"])) == Counter(NUMBER.findall(target))

verify_meta = verification
assert verify_meta["status"] == "passed"
assert verify_meta["parentHead"] == BASE and verify_meta["parentTree"] == BASE_TREE
assert verify_meta["appliedCellCount"] == 76
assert verify_meta["unchangedCellCount"] == 224
assert verify_meta["heldCellCount"] == 24
assert verify_meta["readbackCellCount"] == 300
assert verify_meta["catalogFileCount"] == 12
assert verify_meta["orderedCatalogKeysPreserved"] is True
assert verify_meta["nonTargetValuesUnchanged"] is True

print(json.dumps({
    "result":"PASS",
    "parentHead":BASE,
    "parentTree":BASE_TREE,
    "readbackCells":len(readback),
    "appliedUpdates":len(plan),
    "unchangedAcceptCurrent":200,
    "holdsPreserved":24,
    "holdRanks":[438,452],
    "catalogFiles":len(structure),
    "orderedKeysPerCatalog":6176,
    "orderedCatalogKeysPreserved":True,
    "nonTargetValuesUnchanged":True,
    "evidenceChecksumListSha256":sha((EVIDENCE/"EVIDENCE-SHA256SUMS.txt").read_bytes()),
},ensure_ascii=False,indent=2))
