#!/usr/bin/env python3
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REVIEW_HEAD = "311127db7f4d5097dfd1dde5eaa2150f82f48f30"
REVIEW_TREE = "23210cd313efd929cca9ceda0fd78da19e5ed50d"
APPLY = "3aebbc99f2de17da71971edf9602503dca747658"
APPLY_TREE = "42cd101d3ec0d43fa6da35e92da3e33662f4b215"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def j(path):
    return json.loads(path.read_text(encoding="utf-8"))

def jl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def verify_sums(directory, filename="SHA256SUMS.txt", exact=True):
    entries = {}
    for line in (directory / filename).read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        entries[name] = digest
    assert entries, "empty checksum list: " + str(directory / filename)
    assert all(sha((directory / name).read_bytes()) == digest for name, digest in entries.items()), "checksum mismatch: " + str(directory)
    if exact:
        actual = {path.relative_to(directory).as_posix() for path in directory.rglob("*") if path.is_file() and path != directory / filename}
        assert set(entries) == actual, "file inventory mismatch: " + str(directory)
    return entries

def run_verifier(name, args):
    stdout = subprocess.check_output(args, text=True)
    try:
        details = json.loads(stdout)
    except Exception:
        details = {"stdout": stdout.strip()}
    return {"name": name, "status": "PASS", "details": details}

def main():
    out = Path(__file__).resolve().parent
    manifest = j(out / "manifest.json")
    root_sums = verify_sums(out)
    inventory = jl(out / "inventory.jsonl")
    actual_files = sorted(path for path in out.rglob("*") if path.is_file() and path not in (out / "inventory.jsonl", out / "SHA256SUMS.txt"))
    expected_inventory = [{"path": path.relative_to(out).as_posix(), "sha256": sha(path.read_bytes()), "sizeBytes": path.stat().st_size} for path in actual_files]
    assert inventory == expected_inventory, "root inventory differs"
    assert manifest["inventoryRowCount"] == len(inventory)
    assert manifest["rootChecksumEntryCount"] == len(root_sums)
    for path in out.rglob("*"):
        if path.is_file():
            relative = path.relative_to(out).as_posix()
            assert not relative.startswith(".github/workflows/") and "/.github/workflows/" not in relative, "workflow path present"
    assert manifest["workflowFilesIncluded"] == 0 and manifest["pushPerformed"] is True
    assert manifest["reviewHead"] == REVIEW_HEAD and manifest["reviewTree"] == REVIEW_TREE
    assert manifest["applicationCommit"] == APPLY and manifest["applicationParent"] == REVIEW_HEAD and manifest["applicationTree"] == APPLY_TREE
    assert manifest["evidenceOnlyCommitParent"] == APPLY
    assert manifest["scope"] == {"window": "W72", "continuationRankStart": 678, "continuationRankEnd": 702, "sourceIds": 25, "locales": 12, "cells": 300}
    assert manifest["reviewDispositionCounts"] == {"accept-current": 161, "correct": 24, "hold": 108, "refine": 7}
    assert manifest["comparison"]["selectedTargets"] == 31 and manifest["comparison"]["blindOnlySelected"] == 9
    assert manifest["application"]["selectedCells"] == 31 and manifest["application"]["catalogFiles"] == 10
    assert manifest["application"]["currentWindowCallerlessHoldsHashOnly"] == 108
    assert manifest["application"]["priorHeldCellsHashOnly"] == 152 and manifest["application"]["priorSelectedIdsHashOnly"] == 1782
    assert manifest["application"]["nativeSpeakerSignoff"] == "not claimed"
    cf = out / "candidate-free" / "input"
    primary = out / "primary-review"
    blind = out / "blind-review"
    cross = out / "cross-review"
    app = out / "application"
    assert (blind / "input" / "verify_input.py").is_file() and (blind / "output" / "blind-ledger.jsonl").is_file()
    assert not any("partial" in path.name.lower() or "language-subset" in path.name.lower() for path in out.rglob("*"))
    cf_sums = verify_sums(cf, "PACKET-SHA256SUMS.txt")
    primary_sums = verify_sums(primary)
    blind_sums = verify_sums(blind)
    cross_sums = verify_sums(cross, exact=False)
    app_sums = verify_sums(app)
    source = manifest["sourcePackets"]
    assert sha((cf / "PACKET-SHA256SUMS.txt").read_bytes()) == source["candidateFreePacketChecksumListSha256"]
    assert sha((primary / "SHA256SUMS.txt").read_bytes()) == source["primaryPacketChecksumListSha256"]
    assert sha((blind / "SHA256SUMS.txt").read_bytes()) == source["canonicalFullBlindPacketChecksumListSha256"]
    assert sha((cross / "SHA256SUMS.txt").read_bytes()) == source["sealedCrossReviewChecksumListSha256"]
    assert sha((app / "SHA256SUMS.txt").read_bytes()) == source["applicationChecksumListSha256"]
    nested = [
        run_verifier("candidate-free", [sys.executable, str(cf / "verify_input.py")]),
        run_verifier("primary", [sys.executable, str(primary / "output" / "verify_primary.py")]),
        run_verifier("canonical-full-blind", [sys.executable, str(blind / "output" / "verify_review.py")]),
        run_verifier("cross-review", [sys.executable, str(cross / "output" / "verify_cross_review.py")]),
        run_verifier("application-readback", [sys.executable, str(app / "verify_application_readback.py")]),
    ]
    recorded = j(out / "verification-results.json")
    assert recorded["allPassed"] is True and recorded["nestedVerifiers"] == nested
    assert all(item["status"] == "PASS" for item in nested)
    candidate = j(cf / "manifest.json")
    primary_manifest = j(primary / "output" / "manifest.json")
    blind_manifest = j(blind / "output" / "manifest.json")
    cross_manifest = j(cross / "output" / "manifest.json")
    assert candidate["head"] == primary_manifest["head"] == blind_manifest["head"] == cross_manifest["head"] == REVIEW_HEAD
    assert candidate["tree"] == primary_manifest["tree"] == blind_manifest["tree"] == cross_manifest["tree"] == REVIEW_TREE
    assert candidate["cellCount"] == 300 and primary_manifest["cells"] == 300 and blind_manifest["cells"] == 300
    assert cross_manifest["finalDispositionCounts"] == manifest["reviewDispositionCounts"]
    plan = j(app / "application-plan.json")
    application_commit = j(app / "application-commit.json")
    summary = j(app / "application-summary.json")
    assert plan["applicationCommit"] == APPLY and application_commit["commit"] == APPLY
    assert application_commit["parent"] == REVIEW_HEAD and application_commit["tree"] == APPLY_TREE
    assert application_commit["changedFileCount"] == 10 and application_commit["changedCellCount"] == 31
    assert application_commit["workflowFilesChanged"] == 0 and len(plan["targetRows"]) == 31
    assert summary["readbackMatches"] == 31 and summary["readbackMismatches"] == 0
    holds = jl(app / "held-cells-hash-only.jsonl")
    prior = jl(app / "prior-held-cell-reattestation-hash-only.jsonl")
    ids = jl(app / "prior-selected-id-exclusions-hash-only.jsonl")
    assert len(holds) == 108 and len(prior) == 152 and len(ids) == 1782
    assert all(row["sourceTextIncluded"] is False and row["currentTargetTextIncluded"] is False and row["recommendedTargetTextIncluded"] is False for row in holds)
    assert all(row["sourceTextIncluded"] is False and row["targetTextIncluded"] is False for row in prior + ids)
    live = j(out / "live-pr-before-evidence-commit.json")
    assert live["headRefOid"] == live["branchRefOid"] == live["pullRefOid"] == APPLY
    assert live["treeOid"] == APPLY_TREE and live["pullRequest"] == 409 and live["state"] == "OPEN" and live["draft"] is True
    assert live["deploymentsForHead"] == 0
    assert manifest["livePRBeforeEvidenceCommit"] == {"head": live["headRefOid"], "tree": live["treeOid"], "attestedUtc": live["attestedUtc"]}
    repo = out
    while repo != repo.parent and not (repo / ".git").exists():
        repo = repo.parent
    git_state = "not in a git worktree; commit chain pins verified from records"
    if (repo / ".git").exists():
        head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        if head == APPLY:
            git_state = "pre-evidence-commit; catalog commit is HEAD"
        else:
            parent = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD^"], text=True).strip()
            assert parent == APPLY, "evidence commit parent mismatch"
            changed = subprocess.check_output(["git", "-C", str(repo), "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], text=True).splitlines()
            prefix = "docs/pr-evidence/pr409-localization-2026-11-03/window-678-702/"
            assert changed and all(path.startswith(prefix) for path in changed), "commit contains paths outside this evidence directory"
            git_state = "evidence-only commit directly follows catalog commit"
    print(json.dumps({"verifier": "PASS", "rootFilesVerified": len(root_sums), "inventoryRows": len(inventory), "nestedVerifiers": nested, "selectedTargets": 31, "readbackMatches": 31, "callerlessHoldsHashOnly": len(holds), "priorHoldsHashOnly": len(prior), "priorIdsHashOnly": len(ids), "applicationCommit": APPLY, "livePRHeadBeforeEvidenceCommit": live["headRefOid"], "gitBoundary": git_state, "workflowFilesIncluded": 0}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
