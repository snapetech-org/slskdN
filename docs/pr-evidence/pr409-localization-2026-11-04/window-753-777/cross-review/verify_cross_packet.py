#!/usr/bin/env python3
import hashlib, json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CF = ROOT / "inputs/candidate-free-input"
PR = ROOT / "inputs/primary-review"
BL = ROOT / "inputs/blind-review"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def shat(text):
    return sha(text.encode("utf-8"))

def j(path):
    return json.loads(path.read_text(encoding="utf-8"))

def jl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def req(condition, message):
    if not condition:
        raise SystemExit("FAIL: " + message)

def verify_sums(folder, filename):
    sums_file = folder / filename
    req(sums_file.is_file(), "missing checksum list " + str(sums_file))
    listed = {}
    for line in sums_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        listed[name.lstrip("* ")] = digest
    actual = {
        p.relative_to(folder).as_posix()
        for p in folder.rglob("*")
        if p.is_file() and p != sums_file
    }
    req(set(listed) == actual, "checksum inventory " + str(folder))
    for name, digest in listed.items():
        req(sha((folder / name).read_bytes()) == digest, "checksum " + str(folder / name))

verify_sums(CF, "PACKET-SHA256SUMS.txt")
verify_sums(PR, "SHA256SUMS.txt")
verify_sums(BL, "SHA256SUMS.txt")
verify_sums(ROOT, "SHA256SUMS.txt")

cman = j(CF / "manifest.json")
pman = j(PR / "manifest.json")
bman = j(BL / "manifest.json")
req(cman["repository"] == "snapetech-org/slskdN" and cman["pullRequest"] == 409, "candidate-free identity")
req(cman["window"] == "W75" and cman["continuationRankRange"] == [753, 777] and cman["cellCount"] == 300, "candidate-free scope")
req(cman["head"] == "99d6afbfb8cca4dccc018e72c01950bc304240db" and cman["tree"] == "f21cb5cde009ac35f5531ddc40612821aee6f471", "pinned head/tree")
req(pman["head"] == cman["head"] and pman["tree"] == cman["tree"] and pman["cellCount"] == 300, "primary pin")
req(pman["candidateFreeInputManifestSha256"] == sha((CF / "manifest.json").read_bytes()), "primary manifest linkage")
req(j(PR / "summary.json")["inputChecksumListSha256"] == sha((CF / "PACKET-SHA256SUMS.txt").read_bytes()), "primary checksum linkage")
req(bman["pr"]["head"] == cman["head"] and bman["pr"]["tree"] == cman["tree"], "blind pin")
req(bman["inputManifestSha256"] == sha((CF / "manifest.json").read_bytes()), "blind manifest linkage")
req(bman["inputChecksumsFileSha256"] == sha((CF / "PACKET-SHA256SUMS.txt").read_bytes()), "blind checksum linkage")

results = j(ROOT / "input-verifier-results.json")
req(results["candidateFree"]["result"] == results["primary"]["result"] == results["blind"]["result"] == "PASS", "input verifier results")
req(all(value == "PASS" for value in results["checksums"].values()), "input checksum results")
req(results["candidateFree"]["catalogPinsVerifiedAgainstExactHeadWorktree"] is True, "exact-head catalog verification")
req(results["livePRBeforeReview"] == "PASS", "live PR pre-review attestation")

cells_ordered = jl(CF / "source-current-cells.jsonl")
candidates = {(x["continuationRank"], x["locale"]): x for x in cells_ordered}
primary_rows = {(x["continuationRank"], x["locale"]): x for x in jl(PR / "primary-review.jsonl")}
primary_corrections = {(x["continuationRank"], x["locale"]): x for x in jl(PR / "corrections.jsonl")}
primary_holds = {(x["continuationRank"], x["locale"]): x for x in jl(PR / "holds-hash-only.jsonl")}
blind_rows = {(x["continuationRank"], x["locale"]): x for x in jl(BL / "blind-decisions.jsonl")}
ledger = jl(ROOT / "cross-ledger.jsonl")
reconciliation = jl(ROOT / "proposal-reconciliation.jsonl")
disagreements = jl(ROOT / "proposal-disagreements.jsonl")
holds = jl(ROOT / "holds-hash-only.jsonl")
req(len(candidates) == len(primary_rows) == len(blind_rows) == len(ledger) == 300, "cell counts")
req([(x["continuationRank"], x["locale"]) for x in ledger] == [(x["continuationRank"], x["locale"]) for x in cells_ordered], "ledger order")
req(len({(x["continuationRank"], x["locale"]) for x in ledger}) == 300, "duplicate cross cells")
req(len(primary_corrections) == 20 and len(primary_holds) == 12, "primary review counts")
req(sum(x["disposition"] == "revise" for x in blind_rows.values()) == 44, "blind review count")

def primary_record(p):
    if p is None:
        return None
    return {
        "target": p["target"],
        "targetSha256": shat(p["target"]),
        "rationale": p["rationale"],
        "confidence": p["confidence"],
        "sourceFile": "primary-review/corrections.jsonl",
    }

def blind_record(b):
    if b is None:
        return None
    return {
        "target": b["proposedTarget"],
        "targetSha256": shat(b["proposedTarget"]),
        "rationale": b["rationale"],
        "confidence": b["confidenceInIssueOrDisposition"],
        "sourceFile": "blind-review/blind-decisions.jsonl",
    }

hold_keys = set()
current_count = proposal_count = hold_count = 0
proposal_sources = Counter()
decision_rows = {}
for row in ledger:
    key = (row["continuationRank"], row["locale"])
    c = candidates[key]
    p = primary_rows[key]
    b = blind_rows[key]
    pc = primary_corrections.get(key)
    ph = primary_holds.get(key)
    bp = b if b["disposition"] == "revise" else None
    req(row["sourceId"] == c["sourceId"] == p["sourceId"] == b["sourceId"], "source ID linkage " + str(key))
    req(row["sourceSha256"] == c["sourceSha256"] == p["sourceSha256"] == b["sourceSha256"], "source hash linkage " + str(key))
    req(row["sourceIdSha256"] == shat(c["sourceId"]), "source ID hash " + str(key))
    req(row["callerContextSha256"] == c["callerContextSha256"] == p["callerContextSha256"] == b["callerContextSha256"], "caller context linkage " + str(key))
    req(row["currentTargetSha256"] == c["currentTargetSha256"] == b["currentTargetSha256"], "current target hash linkage " + str(key))
    req(row["primaryDisposition"] == p["disposition"] and row["blindDisposition"] == b["disposition"], "review disposition linkage " + str(key))
    req(row["primaryProposal"] == primary_record(pc), "primary proposal exact linkage " + str(key))
    req(row["blindProposal"] == blind_record(bp), "blind proposal exact linkage " + str(key))
    req(row["selectedTargetSha256"] is not None, "missing selected target hash " + str(key))
    req(row["hold"] == (p["disposition"] == "hold"), "hold state mismatch " + str(key))

    if p["disposition"] == "hold":
        hold_count += 1
        hold_keys.add(key)
        req(key[0] == 754 and ph is not None and bp is None and b["disposition"] == "accept", "unexpected hold resolution " + str(key))
        req(row["sourceText"] is None and row["currentTarget"] is None and row["selectedTarget"] is None, "hold text leakage " + str(key))
        req(row["currentTargetSha256"] == ph["currentTargetSha256"] == row["selectedTargetSha256"], "hash-only hold target linkage " + str(key))
        req(row["sourceSha256"] == ph["sourceSha256"] and row["primaryHoldReasonSha256"] == shat(p["holdReason"]), "hold lineage linkage " + str(key))
        req(row["selectedProposalSources"] == [] and row["decision"] == "hold-hash-only", "hold decision " + str(key))
    else:
        req(key not in primary_holds, "unexpected primary hold row " + str(key))
        req(row["sourceText"] == c["source"] and shat(c["source"]) == c["sourceSha256"], "source text linkage " + str(key))
        req(row["currentTarget"] == c["currentTarget"] == b["currentTarget"], "current text linkage " + str(key))
        req(row["currentTargetSha256"] == shat(row["currentTarget"]), "current text hash " + str(key))
        req(row["selectedTarget"] is not None and row["selectedTargetSha256"] == shat(row["selectedTarget"]), "selected target hash " + str(key))
        if pc is None and bp is None:
            current_count += 1
            req(p["disposition"] == "accept-current" and b["disposition"] == "accept", "unreviewed current cell " + str(key))
            req(row["decision"] == "keep-current" and row["selectedTarget"] == row["currentTarget"], "keep-current decision " + str(key))
            req(row["selectedProposalSources"] == [], "keep-current proposal link " + str(key))
        else:
            proposal_count += 1
            candidates_for_target = {}
            if pc:
                candidates_for_target["primary"] = pc["target"]
            if bp:
                candidates_for_target["blind"] = bp["proposedTarget"]
            matched = [name for name, target in candidates_for_target.items() if target == row["selectedTarget"]]
            req(matched == row["selectedProposalSources"] and matched, "selected proposal exact linkage " + str(key))
            req(row["decision"] in ("select-primary-target", "select-blind-target", "select-agreed-target"), "proposal decision " + str(key))
            proposal_sources["+".join(matched)] += 1
    decision_rows[key] = row

expected_proposal_keys = set(primary_corrections) | {k for k, v in blind_rows.items() if v["disposition"] == "revise"}
recon_keys = {(x["continuationRank"], x["locale"]) for x in reconciliation}
req(recon_keys == expected_proposal_keys and len(recon_keys) == 49, "proposal reconciliation coverage")
different_keys = set()
for rec in reconciliation:
    key = (rec["continuationRank"], rec["locale"])
    row = decision_rows[key]
    pc = primary_corrections.get(key)
    b = blind_rows[key]
    bp = b if b["disposition"] == "revise" else None
    req(rec["primaryProposal"] == primary_record(pc) and rec["blindProposal"] == blind_record(bp), "proposal reconciliation exact linkage " + str(key))
    req(rec["selectedTarget"] == row["selectedTarget"] and rec["selectedTargetSha256"] == row["selectedTargetSha256"], "proposal reconciliation selection " + str(key))
    status = "same-target" if pc and bp and pc["target"] == bp["proposedTarget"] else "different-targets" if pc and bp else "primary-only" if pc else "blind-only"
    req(rec["status"] == status, "proposal reconciliation status " + str(key))
    if status == "different-targets":
        different_keys.add(key)
req(len(different_keys) == 11, "different-target proposal count")
req({(x["continuationRank"], x["locale"]) for x in disagreements} == different_keys and len(disagreements) == 11, "disagreement file coverage")
req({(x["continuationRank"], x["locale"]) for x in holds} == hold_keys and len(holds) == hold_count == 12, "hash-only hold file coverage")
for h in holds:
    key = (h["continuationRank"], h["locale"])
    row = decision_rows[key]
    req(row["decision"] == h["crossDecision"] == "hold-hash-only", "hold sidecar decision " + str(key))
    req(h["sourceTextIncluded"] is False and h["currentTargetIncluded"] is False and h["selectedTargetIncluded"] is False, "hold sidecar text flags " + str(key))
    req(row["sourceSha256"] == h["sourceSha256"] and row["currentTargetSha256"] == h["currentTargetSha256"] and row["callerContextSha256"] == h["callerContextSha256"], "hold sidecar hashes " + str(key))
    req(not any(field in h for field in ("source", "sourceText", "currentTarget", "selectedTarget", "target", "proposedTarget")), "hold sidecar contains text " + str(key))

assessments = j(BL / "protected-literal-assessments.json")
baseline_missing = {
    (x["continuationRank"], x["locale"])
    for x in cells_ordered
    if x["missingProtectedLiterals"]
}
accepted_localized = {
    (x["continuationRank"], x["locale"])
    for x in assessments["assessments"]
    if x["decision"] == "accept-localized-feature-name"
}
req(len(baseline_missing) == 23 and accepted_localized == baseline_missing, "Wishlist protected-literal exceptions")
summary = j(ROOT / "summary.json")
req(summary["cells"] == 300 and summary["keepCurrent"] == current_count == 239, "current decision count")
req(summary["selectedReviewedTargets"] == proposal_count == 49 and summary["crossHashOnlyHolds"] == hold_count == 12, "cross decision counts")
req(summary["proposalUnion"] == 49 and summary["sameTargetProposalAgreements"] == 4 and summary["differentTargetProposalDisagreements"] == 11, "proposal agreement counts")
req(summary["primaryOnlyProposals"] == 5 and summary["blindOnlyProposals"] == 29, "one-sided proposal counts")
req(summary["selectedProposalSourceCounts"] == dict(proposal_sources) == {"blind": 34, "primary": 11, "primary+blind": 4}, "selected proposal source counts")
req(summary["priorActiveHeldCellsPreservedHashOnly"] == 259 and summary["priorHoldResolutionRowsPreservedHashOnly"] == 13, "prior hold lineage")
req(summary["baselineProtectedLiteralFlags"] == summary["localizedWishlistBaselineExceptionsAccepted"] == 23, "protected literal exception count")
req(summary["nativeSpeakerSignoff"] is False and summary["browserReview"] is False and summary["applicationPerformed"] is False, "review limitations")
req(summary.get("livePRAfter") == "PASS", "live PR after attestation")
for name in ("live-pr-before.json", "live-pr-after.json"):
    snap = j(ROOT / name)
    pr = snap["pullRequest"]
    req(pr["number"] == 409 and pr["state"] == "open" and pr["draft"] is True and pr["merged"] is False, "live PR state " + name)
    req(pr["headRef"] == "codex/slskdn-oidc-tooltip-localization-20261030" and pr["baseRef"] == "main", "live PR refs " + name)
    req(pr["headRepository"] == "snapetech-org/slskdN" and pr["headSha"] == cman["head"], "live PR head " + name)
    req(pr["baseSha"] == cman["liveBefore"]["baseRefOid"], "live PR base " + name)
    req(snap["commitTree"] == cman["tree"] and snap["branchRefSha"] == cman["head"] and snap["pullRefSha"] == cman["head"], "live refs/tree " + name)
    req(snap["deploymentCountAtExpectedHead"] == 0, "deployment count " + name)
print(json.dumps({
    "result": "PASS",
    "head": cman["head"],
    "tree": cman["tree"],
    "window": "W75",
    "cells": 300,
    "keepCurrent": current_count,
    "selectedReviewedTargets": proposal_count,
    "proposalUnion": len(reconciliation),
    "sameTargetAgreements": 4,
    "differentTargetDisagreements": len(different_keys),
    "hashOnlyHolds": hold_count,
    "priorHeldCellsPreservedHashOnly": 259,
    "wishlistBaselineExceptions": len(accepted_localized),
    "livePRBeforeAndAfter": "PASS",
    "inputAndRootChecksums": "PASS",
}, ensure_ascii=False, indent=2))
