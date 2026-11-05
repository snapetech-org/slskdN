#!/usr/bin/env python3
"""Verify the W80 exact-hash application and its portable evidence packet."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import subprocess
from pathlib import Path

BASE = "7a1ca27fd0519674c3b42a3e3df3638b0f671567"
BASE_TREE = "b3525218d0f9676c88c4991e78775d113f18b7d9"
PLAN_SHA = "b6a55ca7c871b87977879dc7dbea043d9fb7751ba37619e4f2fef09cb27bb0fa"
ROOT_REVIEW_SHA = "2e85d1c162401e8b2538fb53864583bf1fb5f231aafbf0afd08c7aba62333ef7"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
CATALOGS = [f"src/web/public/locales/{locale}.json" for locale in LOCALES]
EVIDENCE = "docs/pr-evidence/pr409-localization-2026-11-04/window-878-902"


def fail(message: str) -> None:
    raise SystemExit("FAIL: " + message)


def need(ok: bool, message: str) -> None:
    if not ok:
        fail(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def readj(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_checksums(root: Path, sums_name: str) -> int:
    sums = root / sums_name
    count = 0
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        path = (root / name).resolve()
        need(path.is_relative_to(root.resolve()) and path.is_file(), f"checksum path exists and is safe: {name}")
        need(sha(path.read_bytes()) == digest, f"checksum: {name}")
        count += 1
    return count


def verify_manifest(root: Path, manifest_name: str, sums_name: str) -> int:
    manifest = readj(root / manifest_name)
    entries = manifest["files"]
    expected = {entry["path"] for entry in entries}
    need(len(expected) == len(entries), "manifest unique file paths")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
              and p.relative_to(root).as_posix() not in {manifest_name, sums_name}}
    need(actual == expected, "manifest file inventory exactly matches packet")
    for entry in entries:
        path = (root / entry["path"]).resolve()
        need(path.is_relative_to(root.resolve()) and path.is_file(), "safe manifest path " + entry["path"])
        data = path.read_bytes()
        need(len(data) == entry["bytes"] and sha(data) == entry["sha256"], "manifest file hash " + entry["path"])
    return len(entries)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--evidence-dir", type=Path)
    args = ap.parse_args()
    repo = args.repo.resolve()
    evidence = args.evidence_dir.resolve() if args.evidence_dir else repo / EVIDENCE
    app = evidence / "application"
    packet = evidence / "review-packet"

    nested_sums = 0
    nested_sums += verify_checksums(packet / "candidate-free-input", "PACKET-SHA256SUMS.txt")
    nested_sums += verify_checksums(packet / "primary-review", "SHA256SUMS.txt")
    nested_sums += verify_checksums(packet / "independent-blind", "SHA256SUMS.txt")
    nested_sums += verify_checksums(packet / "cross-review", "SHA256SUMS.txt")
    nested_sums += verify_checksums(packet / "root-manual-review", "SHA256SUMS.txt")

    candidate = packet / "candidate-free-input"
    primary = packet / "primary-review"
    blind = packet / "independent-blind"
    cross = packet / "cross-review"
    plan_bytes = (app / "application-plan.jsonl").read_bytes()
    need(sha(plan_bytes) == PLAN_SHA, "root-approved exact-hash plan SHA")
    need(plan_bytes == (cross / "proposal-apply-plan.jsonl").read_bytes(), "application plan byte-copies cross plan")
    plan = rows(app / "application-plan.jsonl")
    cross_rows = rows(cross / "cross-review-decisions.jsonl")
    readback = rows(app / "application-readback-300-cells.jsonl")
    need(len(plan) == 81 and len(cross_rows) == len(readback) == 300, "plan/cross/readback row counts")
    need(len({(r["continuationRank"], r["locale"]) for r in plan}) == 81, "unique selected targets")
    need(all(r["window"] == "W80" and 878 <= r["continuationRank"] <= 902 for r in plan), "W80 plan ranks")
    plan_map = {(r["locale"], r["continuationRank"]): r for r in plan}
    cross_map = {(r["locale"], r["continuationRank"]): r for r in cross_rows}
    readback_map = {(r["locale"], r["continuationRank"]): r for r in readback}
    need(len(cross_map) == len(readback_map) == 300, "unique 300-cell matrix")
    need(set(cross_map) == set(readback_map), "cross review/readback cell coverage")

    root_dir = packet / "root-manual-review"
    review_raw = (root_dir / "review.json").read_bytes()
    root_review = json.loads(review_raw.decode("utf-8"))
    need(sha(review_raw) == ROOT_REVIEW_SHA, "sealed root manual review SHA")
    need(root_review["crossProposalPlanSha256"] == PLAN_SHA and root_review["selectedChangeCount"] == 81
         and root_review["keepCount"] == 219 and root_review["holdCount"] == 0, "root review plan/count binding")
    need(len(rows(primary / "primary-review.jsonl")) == 300 and len(rows(blind / "decisions.jsonl")) == 300,
         "primary and blind review cells")

    summary = readj(app / "application-summary.json")
    need(summary["proposalCount"] == 81 and summary["keepCount"] == 219 and summary["newHoldCount"] == 0
         and summary["priorW79HoldsRetained"] == 39 and summary["readbackCellCount"] == 300,
         "application summary counts")
    need(summary["catalogKeyCountPerLocale"] == 6176 and summary["catalogKeyOrderUnchanged"], "catalog structure")
    write_result = readj(app / "application-write-result.json")
    need(write_result["result"] == "APPLIED" and write_result["baseHead"] == BASE
         and write_result["applyPlanSha256"] == PLAN_SHA and write_result["selectedTargets"] == 81,
         "application write attestation")
    need(set(write_result["files"]) == set(CATALOGS), "application wrote only twelve locale catalogs")

    prior_holds = rows(app / "prior-w79-holds-hash-only.jsonl")
    need(len(prior_holds) == 39 and all(h["priorWindow"] == "W79" and h["priorDisposition"] == "hold"
         and h["matchesPriorCurrentValue"] and h["callerEvidenceUnchanged"] for h in prior_holds),
         "prior 39 W79 holds preserved hash-only")
    need(not ({r["sourceId"] for r in plan} & {h["sourceId"] for h in prior_holds}), "W80 targets disjoint from W79 holds")
    need(len({r["sourceId"] for r in cross_rows}) == 25, "25 unique reviewed source strings")
    need(len({r["locale"] for r in plan}) == 12, "all 12 locales represented")

    main_drift = readj(app / "main-drift-check.json")
    need(main_drift["prBaseSha"] == "f25d263a2a7cdb2c8f76c40c346cb10f749a9356"
         and main_drift["currentMainSha"] == "bc6251ff4ea5a7e59f2d86e2400c90520601f46e"
         and main_drift["baseIsAncestorOfCurrentMain"] and main_drift["result"] == "PASS"
         and main_drift["overlapCount"] == 0 and not main_drift["overlapPaths"], "base/main drift no overlap")
    need(set(main_drift["w80CatalogPaths"]) == set(CATALOGS), "main drift catalog path set")

    for locale in LOCALES:
        path = f"src/web/public/locales/{locale}.json"
        before = subprocess.check_output(["git", "-C", str(repo), "show", f"{BASE}:{path}"])
        before_obj = json.loads(before.decode("utf-8"))
        need(len(before_obj) == 6176, f"parent catalog size {locale}")
        need(sha(before) == next(r["catalogFileSha256"] for r in plan if r["locale"] == locale),
             f"plan catalog preimage hash {locale}")
        post = subprocess.check_output(["git", "-C", str(repo), "show", f"HEAD:{path}"])
        evidence_post = (app / "postimages" / f"{locale}.json").read_bytes()
        need(post == evidence_post, f"catalog postimage evidence equals committed catalog {locale}")
        post_obj = json.loads(post.decode("utf-8"))
        need(list(post_obj) == list(before_obj) and len(post_obj) == 6176, f"ordered catalog keys {locale}")
        selected = {r["catalogKey"]: r for r in plan if r["locale"] == locale}
        for catalog_key, row in selected.items():
            need(before_obj[catalog_key] == row["currentTarget"]
                 and sha(before_obj[catalog_key].encode("utf-8")) == row["currentTargetSha256"],
                 f"exact plan current value {locale}/{row['continuationRank']}")
            need(sha(row["target"].encode("utf-8")) == row["targetSha256"] == row["crossTargetSha256"],
                 f"exact plan target value {locale}/{row['continuationRank']}")
        changed = {k for k in before_obj if before_obj[k] != post_obj[k]}
        need(changed == set(selected), f"only selected plan keys changed {locale}")
        expected_record = write_result["files"][path]
        need(sha(before) == expected_record["beforeFileSha256"] and git_blob(before) == expected_record["beforeGitBlob"],
             f"preimage file/blob hash {locale}")
        need(sha(post) == expected_record["afterFileSha256"] and git_blob(post) == expected_record["afterGitBlob"],
             f"postimage file/blob hash {locale}")

    for key, d in cross_map.items():
        rb = readback_map[key]
        plan_row = plan_map.get(key)
        need(d["crossDisposition"] == ("propose" if plan_row else "keep"), f"cross disposition binding {key}")
        expected = plan_row["target"] if plan_row else d["currentTarget"]
        expected_sha = plan_row["targetSha256"] if plan_row else d["currentTargetSha256"]
        path = d["catalogPath"]
        before_cat = json.loads(subprocess.check_output(["git", "-C", str(repo), "show", f"{BASE}:{path}"]).decode("utf-8"))
        need(before_cat[d["catalogKey"]] == d["currentTarget"]
             and sha(d["currentTarget"].encode("utf-8")) == d["currentTargetSha256"],
             f"300-cell exact preimage {key}")
        final_cat = json.loads(subprocess.check_output(["git", "-C", str(repo), "show", f"HEAD:{path}"]).decode("utf-8"))
        actual = final_cat[d["catalogKey"]]
        need(actual == expected and sha(actual.encode("utf-8")) == expected_sha, f"actual catalog target {key}")
        need(rb["sourceId"] == d["sourceId"] and rb["catalogKey"] == d["catalogKey"]
             and rb["preimageTargetSha256"] == d["currentTargetSha256"]
             and rb["readbackTarget"] == actual and rb["readbackTargetSha256"] == sha(actual.encode("utf-8"))
             and rb["matchesExpected"] is True, f"300-cell readback evidence {key}")
        if plan_row:
            need(rb["selectedPlanTargetSha256"] == plan_row["targetSha256"] and plan_row["targetSha256"] == plan_row["crossTargetSha256"],
                 f"selected plan target hash {key}")
            tc = plan_row["tokenCheck"]["proposal"]
            need(tc["placeholderParity"] and tc["markupParity"] and tc["numericTokensPreserved"]
                 and tc["protectedLiteralsPreserved"], f"selected target token parity {key}")
        else:
            need(rb["selectedPlanTargetSha256"] is None and rb["preimageTarget"] == actual,
                 f"cross keep remains unchanged {key}")

    counts = collections.Counter(r["crossDisposition"] for r in cross_rows)
    need(counts == {"keep": 219, "propose": 81}, "final 219 keeps / 81 proposals")
    need(sum(r["crossDisposition"] == "keep" and r["preimageTarget"] == r["readbackTarget"] for r in readback) == 219,
         "all 219 keeps read back unchanged")
    need(sum(r["crossDisposition"] == "propose" for r in readback) == 81, "all 81 accepted targets read back")
    ar_id = [r for r in plan if r["continuationRank"] == 885 and r["locale"] == "ar"]
    need(len(ar_id) == 1 and "ID" in ar_id[0]["target"], "rank 885 Arabic selected target retains protected literal ID")

    preapply = readj(app / "live-before-apply.json")
    need(preapply["state"] == "open" and preapply["draft"] is True and preapply["merged"] is False
         and preapply["headSha"] == BASE and preapply["headTree"] == BASE_TREE
         and preapply["remoteBranchSha"] == BASE and preapply["baseSha"] == main_drift["prBaseSha"]
         and preapply["liveMainSha"] == main_drift["currentMainSha"], "fresh PR/ref pre-apply attestation")
    postpush = readj(app / "live-after-product-push.json")
    need(postpush["state"] == "open" and postpush["draft"] is True and postpush["merged"] is False
         and postpush["headSha"] == postpush["remoteBranchSha"]
         and postpush["headSha"] == "81a2428c5ffc81100f07762f232d27150d1434ec"
         and postpush["exactHeadCheckRuns"] == 0 and postpush["exactHeadStatuses"] == 0
         and postpush["exactHeadWorkflowRuns"] == 0 and postpush["exactHeadDeployments"] == 0,
         "post-push PR state, checks, Actions, and deployment attestation")

    product = readj(app / "product-commit.json")
    product_sha = product["commit"]
    need(product["parent"] == BASE and git(repo, "rev-parse", product_sha + "^") == BASE, "product commit directly follows W80 parent")
    need(set(product["changedPaths"]) == set(CATALOGS), "product commit changed paths limited to locale catalogs")
    actual_product_paths = set(git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", product_sha).splitlines())
    need(actual_product_paths == set(CATALOGS), "Git product commit tree diff limited to twelve locale catalogs")
    need(git(repo, "rev-parse", "HEAD") == product_sha or git(repo, "merge-base", "--is-ancestor", product_sha, "HEAD") == "",
         "product commit present in evidence branch history")
    for path, expected in product["catalogGitBlobs"].items():
        need(git(repo, "rev-parse", f"{product_sha}:{path}") == expected, f"product commit catalog blob {path}")

    manifest_files = verify_manifest(evidence, "manifest.json", "SHA256SUMS.txt")
    nested_sums += verify_checksums(evidence, "SHA256SUMS.txt")
    print(json.dumps({"result": "PASS", "window": "W80", "baseHead": BASE, "productCommit": product_sha,
                      "planSha256": PLAN_SHA, "selectedTargets": 81, "keeps": 219, "newHolds": 0,
                      "priorW79Holds": 39, "readbackCells": len(readback), "catalogs": len(CATALOGS),
                      "entriesPerCatalog": 6176, "mainDriftOverlapPaths": 0,
                      "nestedChecksumEntries": nested_sums, "manifestEntries": manifest_files,
                      "nativeSpeakerApproval": False, "browserReview": False,
                      "testsBuildsScansCiRun": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
