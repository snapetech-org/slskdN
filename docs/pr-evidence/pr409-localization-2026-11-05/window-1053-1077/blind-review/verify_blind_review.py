#!/usr/bin/env python3
"""Verify the blind review packet using only the sealed candidate-free input."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

PACKET_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PACKET_ROOT / "candidate-free"
HEAD = "ba692c15ca54942108cc9da37757f585969e6173"
TREE = "27c09a8fe24030f5bb0995d809794a9e4829dc64"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def require(condition: bool, message: str):
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def verify_checksum_coverage(directory: Path):
    checksum_path = directory / "SHA256SUMS.txt"
    expected = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("  ", 1)
        require(len(parts) == 2, f"malformed checksum line in {checksum_path}")
        sha, rel = parts
        p = Path(rel)
        require(not p.is_absolute() and ".." not in p.parts, f"unsafe checksum path in {checksum_path}")
        require(rel not in expected, f"duplicate checksum path in {checksum_path}")
        expected[rel] = sha
    actual = {
        p.relative_to(directory).as_posix()
        for p in directory.rglob("*")
        if p.is_file() and p.name != "SHA256SUMS.txt"
    }
    require(actual == set(expected), f"checksum coverage mismatch in {directory}")
    for rel, sha in expected.items():
        require(digest((directory / rel).read_bytes()) == sha, f"checksum mismatch: {directory / rel}")
    return expected


def token_signature(source: str, target: str):
    placeholders = lambda s: Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", s))
    tags = lambda s: Counter(re.findall(r"</?[A-Za-z][^>]*>", s))
    numbers = lambda s: ["".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in t) for t in re.findall(r"\d+", s)]
    protected = lambda s: sorted(set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", s)) | {x for x in ("slskdN", "PodCore", "Wishlist", "soulfind", "FFmpeg", "Lidarr") if x in s})
    sp, tp = placeholders(source), placeholders(target)
    st, tt = tags(source), tags(target)
    sn, tn = numbers(source), numbers(target)
    sl, tl = protected(source), protected(target)
    return {
        "placeholders": {"source": sorted(sp.elements()), "target": sorted(tp.elements()), "matches": sp == tp},
        "markup": {"source": sorted(st.elements()), "target": sorted(tt.elements()), "matches": st == tt},
        "numbers": {"source": sn, "target": tn, "sourcePreserved": all(tn.count(x) >= n for x, n in Counter(sn).items())},
        "protectedLiterals": {"source": sl, "target": tl, "missing": [x for x in sl if x not in target]},
    }


def caller_pins(ctx):
    return [
        {
            "path": caller["path"],
            "line": caller["line"],
            "lineText": caller["lineText"],
            "lineSha256": caller["lineSha256"],
            "contextStartLine": caller["context"][0]["line"],
            "contextEndLine": caller["context"][-1]["line"],
            "contextSha256": caller["contextSha256"],
            "fileSha256": caller["fileSha256"],
            "gitBlob": caller["gitBlob"],
            "literalOccurrenceCount": caller["literalOccurrenceCount"],
        }
        for caller in ctx["callers"]
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-free", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    inp = args.candidate_free.resolve()
    out = args.output.resolve()

    manifest = read_json(out / "manifest.json")
    require((manifest["head"], manifest["tree"]) == (HEAD, TREE), "output head/tree mismatch")
    require(manifest["blindReview"] is True and manifest["crossReviewUsed"] is False, "blind-review mode mismatch")
    require(manifest["nativeSpeakerApproval"] is False, "native-speaker status must be false")

    require(digest((inp / "SHA256SUMS.txt").read_bytes()) == manifest["input"]["sha256SumsFileSha256"], "candidate-free checksum-list pin mismatch")
    verify_checksum_coverage(inp)
    candidate_manifest = read_json(inp / "manifest.json")
    require((candidate_manifest["head"], candidate_manifest["tree"]) == (HEAD, TREE), "candidate-free exact head/tree mismatch")
    require(candidate_manifest["candidateFree"] is True and candidate_manifest["proposedTargetsIncluded"] is False and candidate_manifest["reviewDecisionsIncluded"] is False, "input is not candidate-free")

    input_hashes = [
        (inp / "manifest.json", manifest["input"]["manifestSha256"]),
        (inp / "source-current-cells.jsonl", manifest["input"]["sourceCurrentCellsSha256"]),
        (inp / "caller-contexts.jsonl", manifest["input"]["callerContextsSha256"]),
        (inp / "prior-held-cell-reattestation-hash-only.jsonl", manifest["input"]["priorActiveHoldsSha256"]),
        (inp / "window-holds-hash-only.jsonl", manifest["input"]["windowHoldsSha256"]),
        (inp / "prior-hold-resolution-history-hash-only.jsonl", manifest["input"]["priorHoldResolutionHistorySha256"]),
    ]
    for path, sha in input_hashes:
        require(digest(path.read_bytes()) == sha, f"candidate-free input file pin mismatch: {path.name}")

    source_rows = read_jsonl(inp / "source-current-cells.jsonl")
    ledger = read_jsonl(out / "blind-review-ledger.jsonl")
    require(len(source_rows) == len(ledger) == 300, "ledger does not contain exactly 300 rows")
    require([(r["continuationRank"], r["locale"]) for r in ledger] == [(r["continuationRank"], r["locale"]) for r in source_rows], "ledger cell order differs from candidate-free order")

    contexts = {r["continuationRank"]: r for r in read_jsonl(inp / "caller-contexts.jsonl")}
    counts = Counter()
    baseline_counts = Counter()
    proposal_counts = Counter()
    locale_order = candidate_manifest["locales"]
    require(manifest["localeOrder"] == locale_order, "locale order differs")
    for current, row in zip(source_rows, ledger):
        rank, locale = current["continuationRank"], current["locale"]
        require((row["head"], row["tree"]) == (HEAD, TREE), f"row pin mismatch at {rank}/{locale}")
        require(row["window"] == "W1053-W1077" and row["locale"] == locale, f"row identity mismatch at {rank}/{locale}")
        require(row["sourceId"] == current["sourceId"], f"source id mismatch at {rank}/{locale}")
        require(row["sourceIdSha256"] == current["sourceIdSha256"], f"source-id hash mismatch at {rank}/{locale}")
        require(row["sourceSha256"] == current["sourceSha256"], f"source hash mismatch at {rank}/{locale}")
        require(row["callerContextSha256"] == current["callerContextSha256"], f"caller context hash mismatch at {rank}/{locale}")
        require(row["currentTargetSha256"] == current["currentTargetSha256"], f"current target hash mismatch at {rank}/{locale}")
        require(row["catalogPath"] == current["catalogPath"] and row["catalogFileSha256"] == current["catalogFileSha256"] and row["catalogGitBlob"] == current["catalogGitBlob"], f"catalog pin mismatch at {rank}/{locale}")
        require(row["nativeSpeakerApproval"] is False, f"native-speaker status mismatch at {rank}/{locale}")

        if current["callerCount"] == 0:
            require(row["status"] == row["disposition"] == "hold", f"callerless cell is not held at {rank}/{locale}")
            require(row["confidence"] == "unknown" and row["callerCount"] == 0, f"callerless hold metadata mismatch at {rank}/{locale}")
            require(row["sourceTextIncluded"] is False and row["currentTargetTextIncluded"] is False and row["proposalTextIncluded"] is False, f"callerless hold exposes text at {rank}/{locale}")
            for forbidden in ["source", "currentTarget", "reviewTarget", "reviewerSuggestionUnapproved", "proposedTarget"]:
                require(forbidden not in row, f"callerless hold contains {forbidden} at {rank}/{locale}")
            counts["hold"] += 1
            continue

        require(current["sourceTextIncluded"] is True and current["currentTargetTextIncluded"] is True, f"caller-backed source target missing at {rank}/{locale}")
        require(row["sourceTextIncluded"] is True and row["currentTargetTextIncluded"] is True, f"caller-backed ledger text missing at {rank}/{locale}")
        require(row["source"] == current["source"] and row["currentTarget"] == current["currentTarget"], f"source/current target text mismatch at {rank}/{locale}")
        require(digest(row["source"].encode("utf-8")) == current["sourceSha256"], f"source string digest mismatch at {rank}/{locale}")
        require(digest(row["currentTarget"].encode("utf-8")) == current["currentTargetSha256"], f"current target digest mismatch at {rank}/{locale}")
        ctx = contexts[rank]
        require(ctx["source"] == row["source"] and ctx["sourceSha256"] == row["sourceSha256"] and ctx["callerContextSha256"] == row["callerContextSha256"], f"source caller-context mismatch at {rank}/{locale}")
        require(row["callerReferences"] == caller_pins(ctx), f"caller references differ at {rank}/{locale}")
        require(row["callerCount"] == current["callerCount"] == ctx["productionCallerCount"], f"caller count differs at {rank}/{locale}")
        require(row["candidateFreeTokenEvidence"] == current["tokenEvidence"], f"candidate-free token evidence mismatch at {rank}/{locale}")

        evidence = current["tokenEvidence"]
        if not evidence["placeholders"]["matches"]:
            baseline_counts["placeholder"] += 1
        if not evidence["markup"]["matches"]:
            baseline_counts["markup"] += 1
        if not evidence["numbers"]["sourcePreserved"]:
            baseline_counts["numeric"] += 1
        if evidence["protectedLiterals"]["missing"]:
            baseline_counts["protectedLiteral"] += 1

        status = row["status"]
        require(status in {"retain", "revise", "review"}, f"invalid caller-backed disposition at {rank}/{locale}")
        counts[status] += 1
        if status == "revise":
            require(row["reviewerSuggestionUnapproved"] is not None, f"revise lacks a target at {rank}/{locale}")
            require(row["reviewTarget"] == row["reviewerSuggestionUnapproved"], f"revise target differs from suggestion at {rank}/{locale}")
        elif status == "retain":
            require(row["reviewerSuggestionUnapproved"] is None and row["reviewTarget"] == row["currentTarget"], f"retain target mismatch at {rank}/{locale}")
        else:
            require(row["reviewTarget"] == row["currentTarget"], f"review status must retain the current readback pending locale decision at {rank}/{locale}")

        review_target = row["reviewTarget"]
        require(row["reviewTargetTextIncluded"] is True, f"review target text missing at {rank}/{locale}")
        require(row["reviewTargetSha256"] == digest(review_target.encode("utf-8")), f"review target hash mismatch at {rank}/{locale}")
        target_tokens = token_signature(row["source"], review_target)
        require(row["reviewTargetTokenEvidence"] == target_tokens, f"review target token evidence mismatch at {rank}/{locale}")
        target_pass = (
            target_tokens["placeholders"]["matches"]
            and target_tokens["markup"]["matches"]
            and target_tokens["numbers"]["sourcePreserved"]
            and not target_tokens["protectedLiterals"]["missing"]
        )
        require(row["reviewTargetTokenChecksPass"] is target_pass and target_pass, f"review target token checks failed at {rank}/{locale}")

        suggestion = row["reviewerSuggestionUnapproved"]
        if suggestion is None:
            require(row["reviewerSuggestionSha256"] is None and row["reviewerSuggestionTokenChecksPass"] is None, f"unexpected suggestion evidence at {rank}/{locale}")
        else:
            require(row["reviewerSuggestionSha256"] == digest(suggestion.encode("utf-8")), f"suggestion hash mismatch at {rank}/{locale}")
            suggestion_tokens = token_signature(row["source"], suggestion)
            suggestion_pass = (
                suggestion_tokens["placeholders"]["matches"]
                and suggestion_tokens["markup"]["matches"]
                and suggestion_tokens["numbers"]["sourcePreserved"]
                and not suggestion_tokens["protectedLiterals"]["missing"]
            )
            require(row["reviewerSuggestionTokenChecksPass"] is suggestion_pass and suggestion_pass, f"suggestion token checks failed at {rank}/{locale}")
            proposal_counts["placeholder"] += int(not suggestion_tokens["placeholders"]["matches"])
            proposal_counts["markup"] += int(not suggestion_tokens["markup"]["matches"])
            proposal_counts["numeric"] += int(not suggestion_tokens["numbers"]["sourcePreserved"])
            proposal_counts["protectedLiteral"] += int(bool(suggestion_tokens["protectedLiterals"]["missing"]))

    require(dict(sorted(counts.items())) == manifest["dispositions"], "disposition counts differ from manifest")
    require(dict(sorted(baseline_counts.items())) == manifest["baselineTokenMismatchCounts"], "baseline token mismatch counts differ from manifest")
    require(dict(sorted(proposal_counts.items())) == manifest["reviewedProposalTokenMismatchCounts"], "proposal token mismatch counts differ from manifest")
    require(sum(counts.values()) == 300 and counts["hold"] == 24, "hold count or total differs")
    require(counts["revise"] == len([r for r in ledger if r["status"] == "revise"]), "revise count differs")
    require(manifest["callerBackedCellCount"] == 276 and manifest["callerlessHashOnlyHoldCount"] == 24, "caller-backed/callerless totals differ")
    require(manifest["priorActiveHoldsCopiedByteForByte"] is True, "prior holds copy flag missing")
    require(manifest["priorHoldResolutionHistoryCopiedByteForByte"] is True, "prior hold history copy flag missing")
    require(manifest["callerlessWindowHoldsCopiedByteForByte"] is True, "window hold copy flag missing")
    require(manifest["productFilesEdited"] is False and manifest["testsBuildsScansCiRun"] is False, "work-status flags differ")

    require((out / "caller-contexts.jsonl").read_bytes() == (inp / "caller-contexts.jsonl").read_bytes(), "caller context copy is not byte-for-byte")
    require((out / "prior-active-holds-reattestation-hash-only.jsonl").read_bytes() == (inp / "prior-held-cell-reattestation-hash-only.jsonl").read_bytes(), "prior active hold reattestation changed")
    prior_holds = read_jsonl(out / "prior-active-holds-reattestation-hash-only.jsonl")
    require(len(prior_holds) == 433 and all(x["sourceTextIncluded"] is False and x["targetTextIncluded"] is False for x in prior_holds), "prior active hold file is not 433 hash-only rows")
    require((out / "window-callerless-holds-hash-only.jsonl").read_bytes() == (inp / "window-holds-hash-only.jsonl").read_bytes(), "callerless window holds changed")
    window_holds = read_jsonl(out / "window-callerless-holds-hash-only.jsonl")
    require(len(window_holds) == 24 and all(x["sourceTextIncluded"] is False and x["targetTextIncluded"] is False and x["proposalTextIncluded"] is False for x in window_holds), "callerless window hold file is not 24 hash-only rows")
    require((out / "prior-hold-resolution-history-hash-only.jsonl").read_bytes() == (inp / "prior-hold-resolution-history-hash-only.jsonl").read_bytes(), "prior hold resolution history changed")

    next_boundary = read_json(inp / "selection-and-boundary.json")["nextUnselected"]
    require(manifest["nextBoundary"] == next_boundary and next_boundary["continuationRank"] == 1078, "next boundary mismatch")

    output_entries = verify_checksum_coverage(out)
    print(json.dumps({
        "result": "PASS",
        "verifiedCells": len(ledger),
        "dispositions": dict(sorted(counts.items())),
        "baselineTokenMismatchCounts": dict(sorted(baseline_counts.items())),
        "reviewedProposalTokenMismatchCounts": dict(sorted(proposal_counts.items())),
        "priorActiveHoldsCopiedByteForByte": len(prior_holds),
        "callerlessWindowHolds": len(window_holds),
        "nextBoundary": next_boundary,
        "outputPayloadFilesChecksumCovered": len(output_entries),
        "outputChecksumListSha256": digest((out / "SHA256SUMS.txt").read_bytes()),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
