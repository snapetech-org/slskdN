#!/usr/bin/env python3
import collections
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HEAD = "d0317d8258a31d05b7f163921c2e39f93deabfca"
REVIEW_TREE = "01475aeffa17f6151c4bf161890662167c959bb0"
APPLY = "f120ea15892aa1bd8e17ab43965822ac459e4a71"
APPLY_TREE = "a6b6e84f512e21b7f0bf3a44879ccf81815d3bcc"
LOCALES = ("ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def j(path):
    return json.loads(path.read_text(encoding="utf-8"))


def jl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify_sums(directory, filename="SHA256SUMS.txt"):
    entries = {}
    for line in (directory / filename).read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        entries[name] = digest
    assert entries, "empty checksum list: " + str(directory / filename)
    for name, digest in entries.items():
        assert sha((directory / name).read_bytes()) == digest, "checksum mismatch: " + str(directory / name)
    return entries


def ph(value):
    return sorted(re.findall(r"\{[^{}]+\}", value))


def tags(value):
    return sorted(re.findall(r"</?[A-Za-z][^>]*>", value))


def nums(value):
    return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])", value)


def prot(value):
    found = set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])", value))
    for term in ("Wishlist", "Soulseek", "Discogs", "Pod"):
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", value):
            found.add(term)
    return sorted(found)


def checks(source, target):
    missing = [term for term in prot(source) if term not in target]
    return {
        "placeholders": ph(source) == ph(target),
        "markup": tags(source) == tags(target),
        "numbers": nums(source) == nums(target),
        "protectedLiterals": not missing,
    }


def run_verifier(name, args):
    result = subprocess.run(args, check=True, capture_output=True, text=True)
    try:
        details = json.loads(result.stdout)
    except Exception:
        details = {"stdout": result.stdout.strip()}
    return {"name": name, "status": "PASS", "details": details}


def main():
    out = Path(__file__).resolve().parent
    manifest = j(out / "manifest.json")
    root_sums = verify_sums(out)
    inventory_rows = jl(out / "inventory.jsonl")
    actual_files = sorted(p for p in out.rglob("*") if p.is_file() and p.name not in ("inventory.jsonl", "SHA256SUMS.txt"))
    expected_inventory = [{"path": p.relative_to(out).as_posix(), "sha256": sha(p.read_bytes()), "sizeBytes": p.stat().st_size} for p in actual_files]
    assert inventory_rows == expected_inventory, "root inventory differs"
    for p in out.rglob("*"):
        if p.is_file():
            rel = p.relative_to(out).as_posix()
            assert not rel.startswith(".github/workflows/") and "/.github/workflows/" not in rel, "workflow path present"
    assert manifest["workflowFilesIncluded"] == 0
    assert manifest["pushPerformed"] is False
    assert manifest["applicationCommit"] == APPLY and manifest["applicationParent"] == HEAD and manifest["applicationTree"] == APPLY_TREE
    assert manifest["reviewHead"] == HEAD and manifest["reviewTree"] == REVIEW_TREE
    assert manifest["evidenceOnlyCommitParent"] == APPLY

    cf = out / "candidate-free/input"
    primary = out / "primary-review/output"
    blind = out / "blind-review"
    cross = out / "cross-review"
    audit = out / "second-person-audit"
    addendum = audit / "concern-resolution-addendum"
    app = out / "application"
    verify_sums(cf, "PACKET-SHA256SUMS.txt")
    verify_sums(primary)
    verify_sums(blind)
    verify_sums(cross)
    verify_sums(audit)
    verify_sums(addendum)
    assert sha((cf / "PACKET-SHA256SUMS.txt").read_bytes()) == manifest["sourcePackets"]["candidateFreePacketChecksumListSha256"]
    assert sha((primary / "SHA256SUMS.txt").read_bytes()) == manifest["sourcePackets"]["primaryPacketChecksumListSha256"]
    assert sha((blind / "SHA256SUMS.txt").read_bytes()) == manifest["sourcePackets"]["canonicalFullBlindPacketChecksumListSha256"]
    assert sha((cross / "SHA256SUMS.txt").read_bytes()) == manifest["sourcePackets"]["sealedCrossReviewChecksumListSha256"]
    assert sha((audit / "SHA256SUMS.txt").read_bytes()) == manifest["sourcePackets"]["secondPersonAuditChecksumListSha256"]
    assert sha((addendum / "SHA256SUMS.txt").read_bytes()) == manifest["sourcePackets"]["concernResolutionAddendumChecksumListSha256"]

    # The source copy of primary has a legacy absolute candidate-free path. Run it if that original input still exists; otherwise the checks below validate the copied packet independently.
    verifiers = []
    verifiers.append(run_verifier("candidate-free", [sys.executable, str(cf / "verify_input.py")]))
    legacy_candidate = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w71-653-677-20261103/candidate-free-packet/input")
    if legacy_candidate.is_dir():
        verifiers.append(run_verifier("primary", [sys.executable, str(primary / "verify_primary.py")]))
    else:
        p_rows = jl(primary / "primary-review.jsonl")
        src_rows = {(r["sourceId"], r["locale"]): r for r in jl(cf / "source-current-cells.jsonl")}
        assert len(p_rows) == 300
        for r in p_rows:
            src = src_rows[r["sourceId"], r["locale"]]
            assert r["sourceSha256"] == src["sourceSha256"] and r["currentTargetSha256"] == src["currentTargetSha256"]
            if r["proposedTarget"] is not None:
                assert all(checks(src["source"], r["proposedTarget"]).values())
        verifiers.append({"name":"primary-portable-fallback","status":"PASS","details":{"cells":len(p_rows)}})
    verifiers.append(run_verifier("canonical-full-blind", [sys.executable, str(blind / "verify_review.py")]))
    verifiers.append(run_verifier("cross-review", [sys.executable, str(cross / "verify_cross_review.py"), "--candidate-free", str(cf), "--primary", str(primary), "--blind", str(blind)]))
    legacy_audit = Path(j(addendum / "manifest.json")["secondPersonAuditPath"])
    if legacy_audit.is_dir():
        verifiers.append(run_verifier("concern-resolution-addendum", [sys.executable, str(addendum / "verify_addendum.py"), "--addendum", str(addendum), "--cross-review", str(cross), "--candidate-free", str(cf), "--primary", str(primary), "--blind", str(blind)]))
    else:
        # Portable addendum fallback uses the pinned source/context and the independently sealed target rows.
        source_by_key = {(r["continuationRank"], r["locale"]): r for r in jl(cf / "source-current-cells.jsonl")}
        cross_by_key = {(r["continuationRank"], r["locale"]): r for r in jl(cross / "cross-review.jsonl")}
        add_rows = jl(addendum / "target-resolution-addendum.jsonl")
        assert len(add_rows) == 3
        for r in add_rows:
            src = source_by_key[r["continuationRank"], r["locale"]]
            old = cross_by_key[r["continuationRank"], r["locale"]]
            assert r["sourceSha256"] == src["sourceSha256"] and r["currentTargetSha256"] == src["currentTargetSha256"]
            assert r["originalRecommendedTargetSha256"] == old["recommendedTargetSha256"]
            assert all(checks(src["source"], r["revisedRecommendedTarget"]).values())
        verifiers.append({"name":"concern-resolution-addendum-portable-fallback","status":"PASS","details":{"resolvedCells":len(add_rows)}})
    verifiers.append(run_verifier("application-readback", [sys.executable, str(app / "verify_application_readback.py")]))
    assert all(r["status"] == "PASS" for r in verifiers)
    recorded = j(out / "verification-results.json")
    assert recorded["allPassed"] is True and all(r["status"] == "PASS" for r in recorded["nestedVerifiers"])

    # Verify lineage dispositions stay hash-only in decision/application exports.
    held = jl(app / "held-cells-hash-only.jsonl")
    assert len(held) == 12 and all(r["recommendation"] == "hold" and r["callerCount"] == 0 for r in held)
    assert all(r["sourceTextIncluded"] is False and r["currentTargetTextIncluded"] is False and r["recommendedTargetTextIncluded"] is False for r in held)
    assert len(jl(cross / "prior-held-cell-reattestation-hash-only.jsonl")) == 140
    assert len(jl(cross / "prior-selected-id-exclusions-hash-only.jsonl")) == 1757
    assert len(jl(audit / "rank654-hold-audit-hash-only.jsonl")) == 12
    assert not any(p.name.startswith("slskdn-pr409-w71-es-hi-vi") for p in out.iterdir())

    # Application commit and pre-commit PR snapshot are exact.
    commit = j(app / "application-commit.json")
    assert commit["commit"] == APPLY and commit["parent"] == HEAD and commit["tree"] == APPLY_TREE
    assert commit["changedFiles"] == j(app / "application-plan.json")["filesChanged"]
    assert commit["changedFileCount"] == 12 and commit["workflowFilesChanged"] == 0
    live = j(out / "live-pr-before-evidence-commit.json")
    assert live["headRefOid"] == live["branchRefOid"] == live["pullRefOid"] == APPLY
    assert live["treeOid"] == APPLY_TREE and live["pullRequest"] == 409
    assert manifest["livePRBeforeEvidenceCommit"] == {"head": live["headRefOid"], "tree": live["treeOid"], "attestedUtc": live["attestedUtc"]}
    assert len(root_sums) >= 50
    print(json.dumps({"verifier":"PASS","rootFilesVerified":len(root_sums),"inventoryRows":len(inventory_rows),"nestedVerifiers":verifiers,"applicationReadbackRows":57,"callerlessHoldsHashOnly":12,"priorHeldHashes":140,"priorSelectedIdsHashOnly":1757,"applicationCommit":APPLY,"livePRHead":live["headRefOid"],"workflowFilesIncluded":0},ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
