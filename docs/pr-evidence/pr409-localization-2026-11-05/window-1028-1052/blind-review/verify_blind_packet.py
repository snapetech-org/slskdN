#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, re, subprocess, sys, unicodedata
from pathlib import Path

OUT = Path(__file__).resolve().parent
INPUT = Path("/mnt/disks/scratch/task-scratch/slskdn-pr409-w1028-1052-20261105/candidate-free")
REPO = Path("/home/keith/Documents/code/.task-worktrees/localization-20261105/slskdn-w978")
HEAD = "624e27d8bb108a764df6daab5cfb1c517ebac96d"
TREE = "d139a16988e23046ccb09f519db2d3b7ae0b86d1"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
PROTECTED = ["Ntfy", "Last.fm", "API", "WebGPU", "DHT", "Pod", "PodCore", "Wishlist", "soulfind", "FFmpeg", "Lidarr", "Soulseek", "slskdN"]
TEXT_KEYS = {"source", "currentTarget", "recommendedTarget", "candidateTarget", "proposedTarget", "sourceText", "targetText"}

def need(ok, message):
    if not ok:
        raise SystemExit("FAIL: " + message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def readj(path):
    return json.loads(path.read_text(encoding="utf-8"))

def readjl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def verify_sums(root, sum_name="SHA256SUMS.txt"):
    sums = {}
    for line in (root / sum_name).read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        need(name not in sums, "duplicate checksum " + name)
        path = root / name
        need(path.is_file() and sha(path.read_bytes()) == digest, "checksum mismatch " + name)
        sums[name] = digest
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and path.name != sum_name}
    need(actual == set(sums), "checksum inventory")
    return sums

def token_evidence(source, target):
    placeholders = lambda text: collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", text))
    tags = lambda text: collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", text))
    numbers = lambda text: ["".join(str(unicodedata.digit(ch)) if ch.isdigit() else ch for ch in token) for token in re.findall(r"\d+", text)]
    sp, tp = placeholders(source), placeholders(target)
    st, tt = tags(source), tags(target)
    sn, tn = numbers(source), numbers(target)
    protected = sorted(set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", source)) | {literal for literal in PROTECTED if literal in source})
    missing = [literal for literal in protected if literal not in target]
    return {
        "placeholdersMatch": sp == tp,
        "sourcePlaceholders": sorted(sp.elements()),
        "targetPlaceholders": sorted(tp.elements()),
        "markupMatches": st == tt,
        "sourceMarkup": sorted(st.elements()),
        "targetMarkup": sorted(tt.elements()),
        "numericSequencePreserved": all(tn.count(value) >= count for value, count in collections.Counter(sn).items()),
        "sourceNumbers": sn,
        "targetNumbers": tn,
        "protectedLiteralsPreserved": not missing,
        "sourceProtectedLiterals": protected,
        "missingProtectedLiterals": missing,
        "matches": sp == tp and st == tt and all(tn.count(value) >= count for value, count in collections.Counter(sn).items()) and not missing
    }

def main():
    need(subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip() == HEAD, "worktree HEAD")
    need(subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD^{tree}"], text=True).strip() == TREE, "worktree tree")
    need(not subprocess.check_output(["git", "-C", str(REPO), "status", "--porcelain=v1"], text=True).strip(), "worktree dirty")

    input_verifier = subprocess.run([sys.executable, "-B", str(INPUT / "verify_candidate_free.py"), str(REPO)], capture_output=True, text=True)
    need(input_verifier.returncode == 0, "candidate-free verifier")
    input_sums = verify_sums(INPUT)

    manifest = readj(OUT / "manifest.json")
    summary = readj(OUT / "summary.json")
    need(manifest["head"] == HEAD and manifest["tree"] == TREE, "manifest pin")
    need(manifest["window"] == "W86 / W1028-W1052" and manifest["cellCount"] == 300, "manifest scope")
    need(manifest["candidateFreeInputPath"] == str(INPUT), "candidate-free path")
    need(manifest["candidateFreeManifestSha256"] == sha((INPUT / "manifest.json").read_bytes()), "candidate-free manifest hash")
    need(manifest["candidateFreeChecksumListSha256"] == sha((INPUT / "SHA256SUMS.txt").read_bytes()), "candidate-free checksum-list hash")
    need(manifest["candidateFreeInputVerifiedFiles"] == len(input_sums), "candidate-free checksum count")
    need(manifest["primaryReviewRead"] is False and manifest["W1003W1027RecommendationsOrProposalsRead"] is False, "independence flags")
    need(manifest["catalogsEdited"] is False and manifest["testsBuildsScansCiRun"] is False, "scope flags")
    need(summary["candidateFreeVerifier"] == "PASS" and summary["primaryPacketRead"] is False, "summary verifier/independence")
    need(summary["W1003W1027RecommendationsOrProposalsRead"] is False, "summary prior-window independence")

    output_sums = verify_sums(OUT)
    listed = {row["path"]: row for row in manifest["files"]}
    need(set(listed) == set(output_sums) - {"manifest.json"}, "manifest checksum inventory")
    for name, row in listed.items():
        need(row["sha256"] == output_sums[name] and row["bytes"] == (OUT / name).stat().st_size, "manifest checksum " + name)

    input_rows = readjl(INPUT / "source-current-cells.jsonl")
    ledger = readjl(OUT / "blind-review.jsonl")
    need(len(input_rows) == 300 and len(ledger) == 300, "cell count")
    input_by_id = {row["sourceId"] + "::" + row["locale"]: row for row in input_rows}
    ledger_by_id = {row["cellId"]: row for row in ledger}
    need(len(input_by_id) == 300 and len(ledger_by_id) == 300 and set(input_by_id) == set(ledger_by_id), "cell key coverage")

    decisions = collections.Counter(row["decision"] for row in ledger)
    need(decisions == collections.Counter({"accept": 264, "revise": 24, "hold_hash_only": 12}), "decision distribution")
    proposals = 0
    token_failures = []
    numeric_exceptions = []
    for cell_id, source_row in input_by_id.items():
        row = ledger_by_id[cell_id]
        for field in ("continuationRank", "remainingQueueRank", "sourceId", "sourceIdSha256", "sourceSha256", "locale", "currentTargetSha256", "callerContextSha256", "callerCount"):
            need(row.get(field) == source_row.get(field), "cell metadata mismatch " + cell_id + " " + field)
        need(row.get("candidateFreeInputOnly") is True, "ledger provenance " + cell_id)
        if source_row.get("candidateFreeHold") is True:
            need(row["decision"] == "hold_hash_only", "hold decision " + cell_id)
            need(not (TEXT_KEYS & set(row)), "hold text leak " + cell_id)
            need(row.get("sourceTextIncluded") is False and row.get("targetTextIncluded") is False, "hold disclosure flags " + cell_id)
            need(row.get("recommendedTargetIncluded") is False, "hold recommendation flag " + cell_id)
            need(source_row.get("callerCount") == 0, "hold caller count " + cell_id)
            continue
        need(source_row.get("sourceTextIncluded") is True and source_row.get("currentTargetTextIncluded") is True, "source input text missing " + cell_id)
        need(row.get("source") == source_row["source"] and row.get("currentTarget") == source_row["currentTarget"], "current text mismatch " + cell_id)
        if row["decision"] == "revise":
            proposals += 1
            need(row.get("recommendedTargetIncluded") is True and isinstance(row.get("recommendedTarget"), str), "recommendation missing " + cell_id)
            evidence = token_evidence(row["source"], row["recommendedTarget"])
            need(row.get("recommendationTokenEvidence") == evidence, "recommendation token evidence " + cell_id)
            need(row.get("recommendationTokenEvidenceSha256") == sha(canonical(evidence)), "recommendation token evidence hash " + cell_id)
            if not evidence["matches"]:
                token_failures.append(cell_id)
        else:
            need(row["decision"] == "accept", "unexpected decision " + cell_id)
            need("recommendedTarget" not in row and row.get("recommendedTargetIncluded") is False, "accept row has recommendation " + cell_id)
            if row.get("baselineTokenException"):
                numeric_exceptions.append(cell_id)
                need(cell_id == "src_39639ee9d9b7cce1::ar", "unexpected numeric exception " + cell_id)
                need(row["baselineTokenException"]["sourceNumericToken"] == "1", "numeric exception source")
                need(row["baselineTokenException"]["currentTargetWordsForOne"] == "واحد", "numeric exception target")

    need(proposals == 24 and not token_failures, "recommendation safety")
    need(numeric_exceptions == ["src_39639ee9d9b7cce1::ar"], "baseline numeric mismatch disposition")

    prior_holds = readjl(OUT / "prior-active-holds-hash-only.jsonl")
    current_holds = readjl(OUT / "current-window-holds-hash-only.jsonl")
    resolutions = readjl(OUT / "prior-hold-resolution-history-hash-only.jsonl")
    need((len(prior_holds), len(current_holds), len(resolutions)) == (421, 12, 25), "hold continuity counts")
    need((OUT / "prior-active-holds-hash-only.jsonl").read_bytes() == (INPUT / "prior-held-cell-reattestation-hash-only.jsonl").read_bytes(), "prior active-hold reattestation changed")
    need((OUT / "current-window-holds-hash-only.jsonl").read_bytes() == (INPUT / "window-holds-hash-only.jsonl").read_bytes(), "current hold reattestation changed")
    need((OUT / "prior-hold-resolution-history-hash-only.jsonl").read_bytes() == (INPUT / "prior-hold-resolution-history-hash-only.jsonl").read_bytes(), "prior hold resolution history changed")
    for rows, label in ((prior_holds, "prior active holds"), (current_holds, "current holds"), (resolutions, "hold history")):
        for row in rows:
            need(not (TEXT_KEYS & set(row)), label + " text leak")
            need(row.get("sourceTextIncluded") is False and row.get("targetTextIncluded") is False, label + " disclosure flag")
    need(summary["priorActiveHoldsCarriedHashOnly"] == 421 and summary["currentWindowHashOnlyHolds"] == 12 and summary["resultingActiveHashOnlyHolds"] == 433, "summary hold counts")

    print(json.dumps({
        "result": "PASS",
        "verifier": "slskdn-w1028-1052-independent-blind",
        "head": HEAD,
        "tree": TREE,
        "cells": len(ledger),
        "callerBacked": 288,
        "hashOnlyHolds": 12,
        "decisions": dict(sorted(decisions.items())),
        "recommendations": proposals,
        "recommendationTokenFailures": len(token_failures),
        "baselineNumericException": numeric_exceptions[0],
        "priorActiveHoldsCarried": len(prior_holds),
        "currentWindowHolds": len(current_holds),
        "priorHoldResolutionRows": len(resolutions),
        "candidateFreeVerifier": "PASS",
        "candidateFreeChecksummedFiles": len(input_sums),
        "outputChecksummedFiles": len(output_sums)
    }, ensure_ascii=False, sort_keys=True, indent=2))

if __name__ == "__main__":
    main()

