#!/usr/bin/env python3
"""Portable verifier for the W78 review and application evidence bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


PIN = "4120c9637e71466dc98d51a5a342dee199a1e004"
TREE = "063b62f268eb81253d2b9b4c77ad045c2f25a394"


def fail(message: str) -> None:
    print("FAIL:", message, file=sys.stderr)
    raise SystemExit(1)


def need(ok: bool, message: str) -> None:
    if not ok:
        fail(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_sums(root: Path, name: str = "SHA256SUMS.txt") -> int:
    sums = root / name
    need(sums.is_file(), "missing checksum file: " + str(sums))
    entries = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split(maxsplit=1)
        relative = relative.lstrip("* ")
        need(relative not in entries, "duplicate checksum entry: " + relative)
        path = (root / relative).resolve()
        need(root.resolve() in path.parents, "checksum path escapes packet: " + relative)
        need(path.is_file(), "missing checksum member: " + relative)
        need(sha(path.read_bytes()) == digest, "checksum mismatch: " + relative)
        entries[relative] = digest
    return len(entries)


def run(args: list[str], cwd: Path) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if result.returncode != 0:
        fail("verifier failed: " + " ".join(args) + "\n" + result.stdout + result.stderr)
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True, help="clean local W78 application worktree")
    parser.add_argument("--source-checkout", type=Path, required=True, help="clean checkout at the exact candidate-free review head")
    args = parser.parse_args()
    bundle, repo, source = Path(__file__).resolve().parent, args.repo.resolve(), args.source_checkout.resolve()
    app, candidate, primary, blind, cross = (bundle / "application", bundle / "candidate-free" / "input",
        bundle / "primary-review" / "output", bundle / "blind-review" / "output", bundle / "cross-review")

    root_sum_count = verify_sums(bundle)
    candidate_sum_count = verify_sums(candidate, "PACKET-SHA256SUMS.txt")
    primary_sum_count = verify_sums(primary)
    blind_sum_count = verify_sums(blind, "SEALED-SHA256SUMS.txt")
    cross_sum_count = verify_sums(cross)
    app_sum_count = verify_sums(app)

    cross_manifest = read_json(cross / "manifest.json")
    need(sha((candidate / "manifest.json").read_bytes()) == cross_manifest["candidateFreeInputManifestSha256"], "candidate-free manifest linkage")
    need(sha((candidate / "PACKET-SHA256SUMS.txt").read_bytes()) == cross_manifest["candidateFreeInputChecksumListSha256"], "candidate-free checksum linkage")
    need(sha((primary / "manifest.json").read_bytes()) == cross_manifest["primaryManifestSha256"], "primary manifest linkage")
    need(sha((primary / "SHA256SUMS.txt").read_bytes()) == cross_manifest["primaryChecksumListSha256"], "primary checksum linkage")
    need(sha((blind / "manifest.json").read_bytes()) == cross_manifest["blindManifestSha256"], "blind manifest linkage")
    need(sha((blind / "SEALED-SHA256SUMS.txt").read_bytes()) == cross_manifest["blindChecksumListSha256"], "blind checksum linkage")
    need((app / "application-plan.jsonl").read_bytes() == (cross / "selected-proposal-apply-plan.jsonl").read_bytes(), "application plan differs from sealed cross plan")
    need((app / "holds-hash-only.jsonl").read_bytes() == (cross / "unresolved-holds-hash-only.jsonl").read_bytes(), "application holds differ from cross packet")

    before = (bundle / "delivery" / "PR-body-before.md").read_bytes()
    target = (bundle / "delivery" / "PR-body-update-target.md").read_bytes()
    need(target.startswith(before), "PR-body update target does not preserve the exact original prefix")
    need("W78 localization application (ranks 828\u2013852)".encode("utf-8") in target[len(before):], "W78 body appendix missing")
    workflow = read_json(bundle / "delivery" / "workflow-trigger-assessment.json")
    need(workflow["pushEventWorkflowCount"] == 0 and workflow["pushOrBodyUpdateWillDispatchWorkflow"] is False,
         "workflow preflight indicates an automatic push/body trigger")
    need(workflow["prBranchActiveRunCount"] == 0, "branch had active runs at preflight")

    head = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    tree = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD^{tree}"], text=True).strip()
    need((head, tree) == (PIN, TREE), "candidate-free source checkout pin")
    need(not subprocess.check_output(["git", "-C", str(source), "status", "--porcelain=v1"], text=True).strip(), "source review checkout is dirty")

    candidate_result = run([sys.executable, str(candidate / "verify_input.py"), "--repo", str(source)], candidate)
    need(json.loads(candidate_result).get("result") == "PASS", "candidate-free verifier")
    primary_result = run([sys.executable, str(primary / "verify_primary.py"), "--repo", str(source)], primary)
    need(json.loads(primary_result).get("result") == "PASS", "primary verifier")
    blind_result = run([sys.executable, str(blind / "verify_blind_packet.py")], blind)
    need(json.loads(blind_result).get("result") == "PASS", "blind verifier")
    cross_result = run([sys.executable, str(cross / "verify_cross_packet.py")], cross)
    need(json.loads(cross_result).get("result") == "PASS", "cross verifier")
    application_result = run([sys.executable, str(app / "verify_application.py"), "--repo", str(repo)], app)
    need(json.loads(application_result).get("result") == "PASS", "application verifier")

    readback = json.loads(application_result)
    print(json.dumps({"result": "PASS", "sourceHead": head, "sourceTree": tree,
        "candidateFreeInputMembers": candidate_sum_count, "primaryMembers": primary_sum_count,
        "blindMembers": blind_sum_count, "crossMembers": cross_sum_count,
        "applicationMembers": app_sum_count, "bundleMembers": root_sum_count,
        "application": readback}, sort_keys=True))


if __name__ == "__main__":
    main()
