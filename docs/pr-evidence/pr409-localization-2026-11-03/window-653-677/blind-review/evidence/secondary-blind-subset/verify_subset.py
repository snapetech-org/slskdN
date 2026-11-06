#!/usr/bin/env python3
import collections
import hashlib
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w71-653-677-20261103/candidate-free-packet/input")
OUT = pathlib.Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w71-es-hi-vi-653-677-independent-blind-20261103")
LOCALES = ("es", "hi", "vi")
RANKS = set(range(653, 678))

def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()

def digest_text(value):
    return digest_bytes(value.encode("utf-8"))

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def placeholders(value):
    return re.findall(r"\{[^{}]+\}", value)

def numeric_tokens(value):
    return re.findall(r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])", value)

subprocess.run(["sha256sum", "-c", "PACKET-SHA256SUMS.txt"], cwd=ROOT, text=True, capture_output=True, check=True)
input_check = subprocess.run(["python3", "verify_input.py"], cwd=ROOT, text=True, capture_output=True, check=True)
input_summary = json.loads(input_check.stdout)
assert input_summary["verifier"] == "PASS"
metadata = read_json(OUT / "subset-metadata.json")
ledger = read_jsonl(OUT / "subset-ledger.jsonl")
rationales = (OUT / "subset-rationale.md").read_text(encoding="utf-8")

input_cells = [x for x in read_jsonl(ROOT / "source-current-cells.jsonl") if x.get("locale") in LOCALES and x.get("continuationRank") in RANKS]
input_by_key = {(x["continuationRank"], x["locale"]): x for x in input_cells}
ledger_by_key = {(x["continuationRank"], x["locale"]): x for x in ledger}
assert len(input_by_key) == 75
assert len(ledger) == 75
assert len(ledger_by_key) == 75
assert set(ledger_by_key) == set(input_by_key)
assert all(x["locale"] in LOCALES and x["continuationRank"] in RANKS for x in ledger)

for key, output in ledger_by_key.items():
    source = input_by_key[key]
    assert output["sourceId"] == source["sourceId"]
    assert output["source"] == source["source"]
    assert output["sourceSha256"] == source["sourceSha256"] == digest_text(source["source"])
    assert output["currentTarget"] == source["currentTarget"]
    assert output["currentTargetSha256"] == source["currentTargetSha256"] == digest_text(source["currentTarget"])
    assert output["reviewedTargetSha256"] == digest_text(output["reviewedTarget"])
    assert output["callerContextSha256"] == source["callerContextSha256"]
    assert output["callerCount"] == len(source["callerRefs"])
    assert output["callerRefs"] == [{
        "path": ref["path"],
        "line": ref["line"],
        "lineSha256": ref["lineSha256"],
        "contextSha256": ref["contextSha256"]
    } for ref in source["callerRefs"]]
    if output["decision"] == "revise":
        assert output["reviewedTarget"] != output["currentTarget"]
    else:
        assert output["reviewedTarget"] == output["currentTarget"]
    evidence = source
    assert collections.Counter(placeholders(output["reviewedTarget"])) == collections.Counter(evidence["placeholderEvidence"]["sourceTokens"])
    assert all(token in output["reviewedTarget"] for token in evidence["markupEvidence"]["sourceTags"])
    assert all(token in output["reviewedTarget"] for token in evidence["sourceNumericTokens"])
    assert all(output["reviewedTarget"].count(token) >= evidence["sourceProtectedLiterals"].count(token) for token in evidence["sourceProtectedLiterals"])
    assert output["literalAudit"]["placeholdersPreserved"] is True
    assert output["literalAudit"]["markupPreserved"] is True
    assert output["literalAudit"]["numericTokensPreserved"] is True
    assert output["literalAudit"]["protectedLiteralsPreserved"] is True

counts = collections.Counter(x["decision"] for x in ledger)
assert counts == {"accept": 51, "revise": 21, "hold_context": 3}
assert rationales.count(" — **") == 75
assert metadata["cellCount"] == 75
assert metadata["dispositionCounts"] == dict(counts)
assert metadata["priorHeldCellReattestation"]["count"] == 140
assert metadata["priorHeldCellReattestation"]["targetHashMatches"] == 140
assert metadata["priorHeldCellReattestation"]["targetHashMismatches"] == 0
assert metadata["priorHeldCellReattestation"]["targetTextEmitted"] is False
assert metadata["selectionReattestation"]["sourceTextHashMismatches"] == 0
assert metadata["selectionReattestation"]["selectedSourceTextEmitted"] is False
assert metadata["reviewedTargetLiteralAuditStatus"] == "PASS"
assert metadata["reviewedTargetLiteralMismatches"] == {}

result = {
    "verifier": "PASS",
    "inputChecksumsVerified": 16,
    "inputVerifier": input_summary["verifier"],
    "head": metadata["head"],
    "tree": metadata["tree"],
    "subsetCells": len(ledger),
    "locales": list(LOCALES),
    "continuationRankRange": [653, 677],
    "dispositionCounts": dict(counts),
    "priorHeldTargetHashMatches": 140,
    "priorHeldTargetHashMismatches": 0,
    "selectionSourceHashMismatches": 0,
    "reviewedTargetLiteralMismatches": {},
    "priorTargetTextEmitted": False
}
(OUT / "verification-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2))

