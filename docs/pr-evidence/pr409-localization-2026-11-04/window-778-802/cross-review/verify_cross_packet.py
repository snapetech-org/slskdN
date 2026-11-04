#!/usr/bin/env python3
import argparse
import collections
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CF = ROOT / "inputs/candidate-free-input"
PR = ROOT / "inputs/primary-review"
BLROOT = ROOT / "inputs/blind-review-packet"
BL = BLROOT / "blind-review"
HEAD = "674156749ee86021ef91d896b1824be62cff9a93"
TREE = "86483dbf9227130cade6a3f4c9dc9ef5cf232450"
BLIND_SELECTIONS = {"781::zh-Hant", "786::zh-Hant", "798::vi"}


def fail(message):
    raise SystemExit("FAIL: " + message)


def req(condition, message):
    if not condition:
        fail(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def shat(text):
    return sha(text.encode("utf-8"))


def j(path):
    return json.loads(path.read_text(encoding="utf-8"))


def jl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify_sums(folder, filename):
    sums = folder / filename
    req(sums.is_file(), f"missing checksum list {sums}")
    listed = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(None, 1)
            listed[name.lstrip("* ")] = digest
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and p != sums}
    req(set(listed) == actual, f"checksum inventory mismatch in {folder}")
    for name, digest in listed.items():
        req(sha((folder / name).read_bytes()) == digest, f"checksum mismatch {folder / name}")


def verify_packet_scripts(repo):
    # The copied primary verifier expects its original packet directory layout.
    # A temporary relative alias restores that layout without changing packet files.
    alias_parent = ROOT / "candidate-free"
    alias = alias_parent / "input"
    made_parent = False
    made_alias = False
    if alias.exists() or alias.is_symlink():
        fail("temporary verifier alias already exists")
    if not alias_parent.exists():
        alias_parent.mkdir()
        made_parent = True
    os.symlink("../inputs/candidate-free-input", alias)
    made_alias = True
    try:
        outputs = {}
        commands = {
            "candidateFree": ["python3", str(CF / "verify_input.py"), "--repo", str(repo)],
            "primary": ["python3", str(PR / "verify_primary.py"), "--repo", str(repo)],
            "blind": ["python3", str(BL / "verify_blind_packet.py"), "--packet-root", str(BLROOT)],
        }
        for key, command in commands.items():
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
            if result.returncode:
                fail(f"{key} verifier failed: {result.stdout[-1600:]} {result.stderr[-1600:]}")
            outputs[key] = result.stdout
        return outputs
    finally:
        if made_alias and alias.is_symlink():
            alias.unlink()
        if made_parent and alias_parent.is_dir() and not any(alias_parent.iterdir()):
            alias_parent.rmdir()


for folder, name in ((CF, "PACKET-SHA256SUMS.txt"), (PR, "SHA256SUMS.txt"), (BLROOT, "SHA256SUMS.txt"), (BL, "SHA256SUMS.txt"), (ROOT, "SHA256SUMS.txt")):
    verify_sums(folder, name)

cfman = j(CF / "manifest.json")
pman = j(PR / "manifest.json")
bman = j(BL / "review-packet.json")
req(cfman["repository"] == "snapetech-org/slskdN" and cfman["pullRequest"] == 409, "candidate-free identity")
req(cfman["window"] == pman["window"] == bman["window"] == "W76", "window identity")
req(cfman["head"] == pman["head"] == bman["inputHead"] == HEAD, "head pin")
req(cfman["tree"] == pman["tree"] == bman["inputTree"] == TREE, "tree pin")
req(pman["candidateFreeInputManifestSha256"] == sha((CF / "manifest.json").read_bytes()), "primary input manifest linkage")
req(bman["candidateFreeManifestSha256"] == sha((BLROOT / "candidate-free/manifest.json").read_bytes()), "blind input manifest linkage")
req(bman["candidateFreeChecksumsSha256"] == sha((BLROOT / "candidate-free/PACKET-SHA256SUMS.txt").read_bytes()), "blind input checksum linkage")
req(cfman["cellCount"] == pman["cellCount"] == bman["cellCount"] == 300, "input cell counts")

before = j(ROOT / "live-pr-before.json")
after = j(ROOT / "live-pr-after.json")
for name, snap in (("before", before), ("after", after)):
    req(snap["repository"] == "snapetech-org/slskdN" and snap["pullRequest"] == 409, f"live identity {name}")
    req(snap["state"] == "open" and snap["draft"] is True and snap["merged"] is False, f"live PR state {name}")
    req(snap["headRef"] == "codex/slskdn-oidc-tooltip-localization-20261030" and snap["baseRef"] == "main", f"live refs {name}")
    req(snap["headShaApi"] == snap["branchRefSha"] == snap["pullRefSha"] == HEAD, f"live PR/API refs {name}")
    req(snap["headTree"] == TREE, f"live tree {name}")
    req(snap["baseShaApi"] == cfman["liveBefore"]["baseRefOid"], f"base ref linkage {name}")
    req(snap["mergeableState"] in ("clean", "unstable"), f"merge state {name}")
req(before["attestedUtc"] <= after["attestedUtc"], "live attestation order")
drift = j(ROOT / "main-drift.json")
req(drift["baseSha"] == before["baseShaApi"] and drift["liveMainSha"] == before["liveMainSha"], "main drift pins")
req(drift["containsLocalizationOrCatalogPaths"] is False, "unexpected localization/catalog base drift")

cells = jl(CF / "source-current-cells.jsonl")
contexts = {x["continuationRank"]: x for x in jl(CF / "caller-contexts.jsonl")}
primary = {(x["continuationRank"], x["locale"]): x for x in jl(PR / "primary-review.jsonl")}
changes = {(x["continuationRank"], x["locale"]): x for x in jl(PR / "corrections.jsonl")}
primary_holds = {(x["continuationRank"], x["locale"]): x for x in jl(PR / "holds-hash-only.jsonl")}
blind = {(x["continuationRank"], x["locale"]): x for x in jl(BL / "review-cells.jsonl")}
ledger = jl(ROOT / "cross-ledger.jsonl")
recon = jl(ROOT / "proposal-reconciliation.jsonl")
disagreements = jl(ROOT / "proposal-disagreements.jsonl")
holds = jl(ROOT / "holds-hash-only.jsonl")
req(len(cells) == len(primary) == len(blind) == len(ledger) == 300, "300-cell coverage")
ordered_keys = [(x["continuationRank"], x["locale"]) for x in cells]
req([(x["continuationRank"], x["locale"]) for x in ledger] == ordered_keys, "ledger source order")
req(len(set(ordered_keys)) == 300 and len(set((x["continuationRank"], x["locale"]) for x in ledger)) == 300, "duplicate cell")
req(len(changes) == 69 and len(primary_holds) == 48, "primary dispositions")
req(sum(x["disposition"] == "propose" for x in blind.values()) == 52, "blind proposal count")
req(sum(x["disposition"] == "hold" for x in blind.values()) == 60, "blind hold count")

counts = collections.Counter()
proposal_sources = collections.Counter()
ledger_by_key = {}
for c, row in zip(cells, ledger):
    key = (c["continuationRank"], c["locale"])
    key_id = f"{key[0]}::{key[1]}"
    p, b = primary[key], blind[key]
    pc, ph = changes.get(key), primary_holds.get(key)
    bp = b.get("proposal") if b["disposition"] == "propose" else None
    req(row["sourceId"] == c["sourceId"] == p["sourceId"] == b["sourceId"], f"source ID binding {key}")
    req(row["sourceSha256"] == c["sourceSha256"] == p["sourceSha256"] == b["sourceSha256"], f"source hash binding {key}")
    req(row["sourceIdSha256"] == shat(c["sourceId"]), f"source ID hash {key}")
    req(row["callerContextSha256"] == c["callerContextSha256"] == p["callerContextSha256"] == b["callerContextSha256"], f"caller hash binding {key}")
    req(row["currentTargetSha256"] == c["currentTargetSha256"] == p["currentTargetSha256"] == b["currentTargetSha256"], f"current target hash {key}")
    req(row["primaryDisposition"] == p["disposition"] and row["blindDisposition"] == b["disposition"], f"review disposition {key}")
    req(row["hold"] == bool(ph), f"hold flag {key}")
    ledger_by_key[key] = row

    if ph:
        counts["hold"] += 1
        req(key not in changes and b["disposition"] == "hold", f"callerless hold disagreement {key}")
        req(contexts[key[0]]["productionCallerCount"] == 0, f"hold lacks callerless evidence {key}")
        req(row["productionCallerCount"] == 0, f"hold caller count {key}")
        req(row["sourceText"] is None and row["currentTarget"] is None and row["selectedTarget"] is None, f"hold text leak {key}")
        req(row["primaryProposal"] is None and row["blindProposal"] is None, f"hold proposal leak {key}")
        req(row["selectedTargetSha256"] == row["currentTargetSha256"], f"hold current hash {key}")
        req(row["decision"] == "hold-hash-only" and row["selectedProposalSources"] == [], f"hold disposition {key}")
        continue

    req(row["sourceText"] == c["source"] and shat(row["sourceText"]) == c["sourceSha256"], f"source text/hash {key}")
    req(row["currentTarget"] == c["currentTarget"] and shat(row["currentTarget"]) == row["currentTargetSha256"], f"current text/hash {key}")
    req(row["selectedTarget"] is not None and shat(row["selectedTarget"]) == row["selectedTargetSha256"], f"selected target hash {key}")
    if pc:
        counts["correction"] += 1
        expected_side = "blind" if key_id in BLIND_SELECTIONS else "primary"
        expected_target = bp if expected_side == "blind" else pc["target"]
        req(expected_target is not None and row["decision"] == f"select-{expected_side}-target", f"selected proposal side {key}")
        req(row["selectedTarget"] == expected_target, f"selected proposal exact text {key}")
        proposal_names = [name for name, value in (("primary", pc["target"]), ("blind", bp)) if value is not None and value == expected_target]
        req(row["selectedProposalSources"] == proposal_names and expected_side in proposal_names, f"selected proposal source linkage {key}")
        req(row["primaryProposal"]["target"] == pc["target"] and row["primaryProposal"]["targetSha256"] == shat(pc["target"]), f"primary proposal linkage {key}")
        if bp is None:
            req(row["blindProposal"] is None, f"blind proposal should be absent {key}")
        else:
            req(row["blindProposal"]["target"] == bp and row["blindProposal"]["targetSha256"] == shat(bp), f"blind proposal linkage {key}")
        proposal_sources["+".join(proposal_names)] += 1
        # Selected proposal token parity: preserve all source placeholders, tags, numbers, and protected literals.
        src = c["source"]
        tgt = row["selectedTarget"]
        req(collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", src)) <= collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", tgt)), f"placeholder parity {key}")
        req(collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", src)) <= collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", tgt)), f"markup parity {key}")
        source_numbers = ["".join(str(__import__("unicodedata").digit(ch)) if ch.isdigit() else ch for ch in m) for m in re.findall(r"\d+", src)]
        target_numbers = ["".join(str(__import__("unicodedata").digit(ch)) if ch.isdigit() else ch for ch in m) for m in re.findall(r"\d+", tgt)]
        req(collections.Counter(source_numbers) <= collections.Counter(target_numbers), f"numeric parity {key}")
        for literal in c["sourceProtectedLiterals"]:
            req(literal in tgt, f"protected literal {literal} missing {key}")
    else:
        counts["keep"] += 1
        req(p["disposition"] == "accept-current" and b["disposition"] == "keep", f"unreviewed keep {key}")
        req(row["selectedTarget"] == c["currentTarget"] and row["decision"] == "keep-current", f"keep-current mismatch {key}")

    # Every non-hold decision has visible text and a text-free hold cannot leak through sidecars.
    req(row["productionCallerCount"] == contexts[key[0]]["productionCallerCount"], f"caller count binding {key}")

req(len(recon) == 69, "proposal reconciliation coverage")
recon_keys = {(x["continuationRank"], x["locale"]) for x in recon}
req(recon_keys == set(changes), "proposal reconciliation keys")
expected_disagreements = set()
status_counts = collections.Counter()
for rec in recon:
    key = (rec["continuationRank"], rec["locale"])
    p, b = primary[key], blind[key]
    pc = changes[key]
    bp = b.get("proposal") if b["disposition"] == "propose" else None
    expected = "same-target" if bp == pc["target"] else "different-targets" if bp is not None else "primary-only-blind-hold" if b["disposition"] == "hold" else "primary-only-blind-keep"
    req(rec["status"] == expected, f"proposal status {key}")
    req(rec["primaryProposal"]["target"] == pc["target"] and rec["primaryProposal"]["targetSha256"] == shat(pc["target"]), f"reconciliation primary target {key}")
    req(rec["blindDisposition"] == b["disposition"], f"reconciliation blind disposition {key}")
    req((rec["blindProposal"]["target"] if rec["blindProposal"] else None) == bp, f"reconciliation blind target {key}")
    row = ledger_by_key[key]
    req(rec["selectedTarget"] == row["selectedTarget"] and rec["selectedTargetSha256"] == row["selectedTargetSha256"], f"reconciliation selection {key}")
    status_counts[expected] += 1
    if expected != "same-target":
        expected_disagreements.add(key)
req({(x["continuationRank"], x["locale"]) for x in disagreements} == expected_disagreements, "disagreement rows coverage")
req(len(holds) == 48 and {(x["continuationRank"], x["locale"]) for x in holds} == set(primary_holds), "hold sidecar coverage")
for h in holds:
    key = (h["continuationRank"], h["locale"])
    row = ledger_by_key[key]
    req(h["sourceTextIncluded"] is False and h["currentTargetIncluded"] is False and h["selectedTargetIncluded"] is False, f"hold sidecar flags {key}")
    req(h["sourceSha256"] == row["sourceSha256"] and h["currentTargetSha256"] == row["currentTargetSha256"] and h["callerContextSha256"] == row["callerContextSha256"], f"hold sidecar hashes {key}")
    req(not any(field in h for field in ("source", "sourceText", "currentTarget", "selectedTarget", "target", "proposal", "proposedTarget")), f"hold sidecar plaintext {key}")

summary = j(ROOT / "summary.json")
req(summary["cells"] == 300 and summary["keepCurrent"] == counts["keep"] == 183, "summary keep count")
req(summary["selectedCorrections"] == counts["correction"] == 69 and summary["crossHashOnlyHolds"] == counts["hold"] == 48, "summary changes/holds")
req(summary["proposalUnion"] == len(recon) == 69 and summary["blindProposals"] == 52 and summary["primaryProposals"] == 69, "summary proposal union")
req(summary["sameTargetProposals"] == status_counts["same-target"], "summary same targets")
req(summary["differentTargetProposals"] == status_counts["different-targets"], "summary different targets")
req(summary["primaryOnlyAgainstBlindKeep"] == status_counts["primary-only-blind-keep"], "summary primary/keep")
req(summary["primaryOnlyAgainstBlindHold"] == status_counts["primary-only-blind-hold"], "summary primary/hold")
req(summary["proposalDisagreementRows"] == len(disagreements), "summary disagreement count")
req(summary["blindSelectedTargets"] == sorted(BLIND_SELECTIONS), "blind override allowlist")
req(summary["selectedProposalSourceCounts"] == dict(proposal_sources), "selected proposal source counts")
req(summary["priorHeldCellsPreservedHashOnly"] == cfman["priorHeldCellsReattested"] == 271, "prior held lineage")
req(summary["priorHoldResolutionRowsPreservedHashOnly"] == cfman["priorHoldResolutionHistoryRows"] == 13, "prior hold resolution lineage")
req(summary["baselineProtectedLiteralMismatchCells"] == 21 and "remain text-free holds" in summary["baselineProtectedLiteralMismatchDisposition"], "baseline token holds")
req(summary["nativeSpeakerSignoff"] is False and summary["browserReview"] is False and summary["applicationPerformed"] is False, "cross review scope limits")
req(summary["livePRBefore"] == "PASS" and summary["livePRAfter"] == "PASS", "live ref attestations")

parser = argparse.ArgumentParser()
parser.add_argument("--repo", type=Path, required=True, help="clean checkout at the pinned W76 source head")
parser.add_argument("--offline", action="store_true", help="verify sealed historical packet after the live PR head has advanced")
args = parser.parse_args()
if args.offline:
    repo = args.repo.resolve()
    req(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip() == HEAD, "offline source checkout head")
    req(subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=repo, text=True).strip() == TREE, "offline source checkout tree")
    req(subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True).strip() == "", "offline source checkout is dirty")
    verifier_replay = "skipped after live PR advanced; historical PASS is recorded in input-verifier-results.json"
else:
    verifier_outputs = verify_packet_scripts(args.repo.resolve())
    for name, output in verifier_outputs.items():
        req("PASS" in output, f"{name} verifier output missing PASS")
    verifier_replay = "PASS"


print(json.dumps({
    "result": "PASS",
    "head": HEAD,
    "tree": TREE,
    "window": "W76",
    "cells": 300,
    "keepCurrent": counts["keep"],
    "selectedCorrections": counts["correction"],
    "hashOnlyHolds": counts["hold"],
    "proposalStatuses": dict(status_counts),
    "proposalDisagreementRows": len(disagreements),
    "selectedProposalSourceCounts": dict(proposal_sources),
    "priorHeldCellsHashOnly": 271,
    "livePRBeforeAndAfter": "PASS",
    "candidateFreePrimaryBlindVerifierReplay": verifier_replay,
    "allChecksums": "PASS",
}, ensure_ascii=False, indent=2))
