#!/usr/bin/env python3
import hashlib, json, re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w67-ranks553-577-candidate-free-20261103/input")
EXPECTED_HEAD = "2dc64b9d00f6611aeb72713af81db53ccc5a4084"
EXPECTED_TREE = "f13462300926ac897235cd92ae68c87695c38c31"
EXPECTED_LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]

def readj(path):
    return json.loads(path.read_text())

def readl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def h(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def placeholders(value):
    return re.findall(r"\{[^{}]+\}", value)

def tags(value):
    return re.findall(r"</?[A-Za-z][^>]*>", value)

def numbers(value):
    return re.findall(r"[0-9]+(?:[.,][0-9]+)?", value)

M = readj(ROOT / "manifest.json")
S = readj(ROOT / "summary.json")
LA = readj(ROOT / "live-ref-attestation.json")
IM = readj(INPUT / "manifest.json")
assert M["head"] == IM["head"] == EXPECTED_HEAD
assert M["tree"] == IM["tree"] == EXPECTED_TREE
assert M["repository"] == "snapetech-org/slskdN" and M["pullRequest"] == 409
assert M["branch"] == "codex/slskdn-oidc-tooltip-localization-20261030"
assert M["livePRState"]["state"] == "OPEN" and M["livePRState"]["isDraft"] is True
assert M["livePRState"]["headRefOid"] == EXPECTED_HEAD
assert M["liveRefs"] == {
    "refs/heads/codex/slskdn-oidc-tooltip-localization-20261030": EXPECTED_HEAD,
    "refs/pull/409/head": EXPECTED_HEAD,
}
assert M["liveTree"] == EXPECTED_TREE
assert LA["result"] == "PASS" and LA["repository"] == "snapetech-org/slskdN"
assert LA["pullRequest"] == 409 and LA["state"] == "OPEN" and LA["isDraft"] is True
assert LA["head"] == EXPECTED_HEAD and LA["tree"] == EXPECTED_TREE
assert LA["branch"] == M["branch"] and LA["refs"] == M["liveRefs"]
assert M["liveRefAttestationSha256"] == hashlib.sha256((ROOT / "live-ref-attestation.json").read_bytes()).hexdigest()
assert M["candidateFreeInputManifestSha256"] == h((INPUT / "manifest.json").read_text())
assert M["candidateFreeInputChecksumListSha256"] == h((INPUT / "PACKET-SHA256SUMS.txt").read_text())

cells = readl(INPUT / "source-current-cells.jsonl")
C = {(x["continuationRank"], x["locale"]): x for x in cells}
L = readl(ROOT / "translation-ledger.jsonl")
assert len(cells) == len(C) == len(L) == 300
assert set(C) == {(rank, locale) for rank in range(553, 578) for locale in EXPECTED_LOCALES}
assert len({(x["continuationRank"], x["locale"]) for x in L}) == 300
assert {x["locale"] for x in L} == set(EXPECTED_LOCALES)
assert {x["continuationRank"] for x in L} == set(range(553, 578))

hash_rows = (ROOT / "proposal-hashes.txt").read_text().splitlines()
assert len(hash_rows) == 300
assert len({tuple(row.split("\t")[:2]) for row in hash_rows}) == 300
hash_map = {}
for row in hash_rows:
    rank, locale, source_id, digest = row.split("\t")
    key = (int(rank), locale)
    assert key not in hash_map
    hash_map[key] = (source_id, digest)

for x in L:
    key = (x["continuationRank"], x["locale"])
    c = C[key]
    p = x["proposal"]
    assert x["schema"] == "slskdn-blind-review-cell/v1"
    assert x["repository"] == "snapetech-org/slskdN" and x["pullRequest"] == 409
    assert x["head"] == EXPECTED_HEAD and x["tree"] == EXPECTED_TREE
    for field in ("sourceId", "source", "sourceSha256", "currentTarget", "currentTargetSha256",
                  "catalogPath", "catalogFileSha256", "catalogGitBlob", "callerContextSha256", "callerRefs"):
        assert x[field] == c[field], (key, field)
    assert x["sourceSha256"] == h(x["source"])
    assert x["currentTargetSha256"] == h(x["currentTarget"])
    assert x["proposalSha256"] == h(p)
    assert hash_map[key] == (x["sourceId"], x["proposalSha256"])
    assert Counter(placeholders(x["source"])) == Counter(placeholders(p))
    assert Counter(tags(x["source"])) == Counter(tags(p))
    assert Counter(numbers(x["source"])) == Counter(numbers(p))
    assert all(p.count(lit) == x["source"].count(lit) for lit in x["sourceProtectedLiterals"])
    assert x["primaryMaterialOpened"] is False
    assert x["candidateFreeCurrentTargetsVisible"] is True
    assert x["placeholderMismatch"] is False and x["markupMismatch"] is False
    assert x["numericTokenMismatch"] is False and x["protectedLiteralMismatch"] is False
    assert x["reviewDisposition"] in ("accept-current", "correction", "refinement", "hold")
    assert (x["reviewDisposition"] == "accept-current") == (p == c["currentTarget"])

input_holds = readl(INPUT / "prior-held-cell-reattestation.jsonl")
output_holds = readl(ROOT / "prior-held-cell-reattestation.jsonl")
assert len(input_holds) == len(output_holds) == 128
ih = {(x["continuationRank"], x["locale"]): x for x in input_holds}
oh = {(x["continuationRank"], x["locale"]): x for x in output_holds}
assert len(ih) == len(oh) == 128 and set(ih) == set(oh)
for key, prior in ih.items():
    held = oh[key]
    assert prior["status"] == "reattested-unchanged" and prior["priorDisposition"] == "hold"
    assert prior["matchesPriorCurrentValue"] is True
    assert prior["priorTargetSha256"] == prior["currentTargetSha256"] == h(prior["currentTarget"])
    assert held["status"] == "reattested-unchanged" and held["heldTargetTextIncluded"] is False
    assert held["priorDisposition"] == "hold"
    assert held["priorTargetSha256"] == held["currentTargetSha256"] == prior["priorTargetSha256"]
    assert held["continuationRank"] == prior["continuationRank"]
    assert held["locale"] == prior["locale"] and held["sourceId"] == prior["sourceId"]
    assert held["sourceSha256"] == prior["sourceSha256"]
    assert held["callerContextSha256"] == prior["currentCallerContextSha256"]
    assert held["callerCount"] == prior["currentCallerCount"]
    assert held["callerRefs"] == prior["currentCallerRefs"]
    assert held["catalogPath"] == prior["currentCatalogPath"]
    assert held["catalogFileSha256"] == prior["currentCatalogFileSha256"]
    assert held["catalogGitBlob"] == prior["currentCatalogGitBlob"]
    assert held["holdReason"] == prior["holdReason"]

counts = Counter(x["reviewDisposition"] for x in L)
assert counts == Counter(S["reviewDispositionCounts"])
assert sum(counts.values()) == 300
assert len([x for x in L if x["reviewDisposition"] == "hold"]) == 0
assert S["proposalCount"] == 300 and S["priorHoldsReattested"] == S["priorHoldsUnchanged"] == 128
assert S["newHolds"] == 0
assert S["proposalMismatchCount"] == {"placeholder": 0, "markup": 0, "numeric": 0, "protectedLiteral": 0}
assert S["protectedLiteralCorrections"] == 10
print(json.dumps({
    "result": "PASS", "head": EXPECTED_HEAD, "tree": EXPECTED_TREE,
    "cells": len(L), "proposalHashes": len(hash_rows), "dispositions": counts,
    "priorHoldsReattestedAndUnchanged": len(output_holds),
    "liveRefs": "PASS", "proposalTokenChecks": "PASS", "sourceCallerCatalogPins": "PASS"
}, indent=2))
