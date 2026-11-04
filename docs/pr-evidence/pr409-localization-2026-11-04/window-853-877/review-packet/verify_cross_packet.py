#!/usr/bin/env python3
"""Verify the W79 cross-review packet, exact source/caller hashes, and locale tokens."""
import argparse
import collections
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEAD = "4d67527be0ca3b75e866f25bef5e58ae7f777f7f"
TREE = "99ba5d8f7d631de3337e6b02f74af6d14e46c2ff"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
RANKS = range(853, 878)
CALLERLESS_RANKS = {865, 868}
FORBIDDEN_TEXT = {
    "source", "catalogKey", "currentTarget", "target", "crossTarget",
    "primaryProposal", "proposedTarget", "blindIssues", "blindIssueCodes",
    "issues", "reason", "rationale", "tokenCheck",
}


def fail(message):
    raise SystemExit("FAIL: " + message)


def need(condition, message):
    if not condition:
        fail(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text_sha(value):
    return sha(value.encode("utf-8"))


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def rows_raw(path):
    out = []
    for line in path.read_bytes().splitlines():
        if line.strip():
            out.append((json.loads(line), line))
    return out


def readj(path):
    return json.loads(path.read_text(encoding="utf-8"))


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args]).strip()


def git_show(repo, path):
    return subprocess.check_output(["git", "-C", str(repo), "show", f"{HEAD}:{path}"])


def token_check(source, current, target=None):
    def ph(v):
        return collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", v))
    def tags(v):
        return collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", v))
    def nums(v):
        return ["".join(str(unicodedata.digit(ch)) if ch.isdigit() else ch for ch in m)
                for m in re.findall(r"\d+", v)]
    def prot(v):
        out = set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", v))
        out.update(x for x in ("slskdN", "Tor", "Wishlist", "Chromaprint") if x in v)
        return sorted(out)
    def not_less(src, dst):
        src, dst = collections.Counter(src), collections.Counter(dst)
        return all(dst[t] >= n for t, n in src.items())
    result = {
        "sourcePlaceholderTokens": sorted(ph(source).elements()),
        "currentPlaceholderTokens": sorted(ph(current).elements()),
        "sourceMarkupTokens": sorted(tags(source).elements()),
        "currentMarkupTokens": sorted(tags(current).elements()),
        "sourceNumericTokens": nums(source), "currentNumericTokens": nums(current),
        "sourceProtectedLiterals": prot(source),
        "currentProtectedLiterals": [x for x in prot(source) if x in current],
        "placeholderParityCurrent": ph(source) == ph(current),
        "markupParityCurrent": tags(source) == tags(current),
        "numericTokensPreservedCurrent": not_less(nums(source), nums(current)),
        "protectedLiteralsPreservedCurrent": all(x in current for x in prot(source)),
    }
    if target is not None:
        result["proposal"] = {
            "placeholderTokens": sorted(ph(target).elements()),
            "markupTokens": sorted(tags(target).elements()),
            "numericTokens": nums(target), "protectedLiterals": prot(target),
            "placeholderParity": ph(source) == ph(target),
            "markupParity": tags(source) == tags(target),
            "numericTokensPreserved": not_less(nums(source), nums(target)),
            "protectedLiteralsPreserved": all(x in target for x in prot(source)),
        }
    return result


def verify_inventory():
    manifest = readj(ROOT / "manifest.json")
    expected = {item["path"] for item in manifest["files"]}
    need(len(expected) == len(manifest["files"]), "duplicate manifest file path")
    need(not ({"manifest.json", "SHA256SUMS.txt"} & expected), "recursive manifest file")
    for item in manifest["files"]:
        path = (ROOT / item["path"]).resolve()
        need(path.is_relative_to(ROOT.resolve()) and path.is_file(), "missing/unsafe file " + item["path"])
        data = path.read_bytes()
        need(len(data) == item["bytes"] and sha(data) == item["sha256"], "manifest hash " + item["path"])
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
              if p.is_file() and p.name not in {"manifest.json", "SHA256SUMS.txt"}}
    need(actual == expected, "packet file inventory differs")
    sums = {}
    for line in (ROOT / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split("  ", 1)
            need(name not in sums, "duplicate checksum entry")
            sums[name] = digest
    need(set(sums) == expected | {"manifest.json"}, "checksum-list inventory differs")
    for name, digest in sums.items():
        path = (ROOT / name).resolve()
        need(path.is_relative_to(ROOT.resolve()) and path.is_file() and sha(path.read_bytes()) == digest,
             "checksum mismatch " + name)
    return manifest, len(sums)


def refs_from_context(context):
    return [{
        "path": row["path"], "line": row["line"], "lineSha256": row["lineSha256"],
        "contextSha256": row["contextSha256"], "fileSha256": row["fileSha256"],
        "gitBlob": row["gitBlob"],
    } for row in context["callers"]]


def verify_source_callers(repo, contexts, cells):
    need(git(repo, "cat-file", "-e", f"{HEAD}^{{commit}}") is not None, "pinned commit object missing")
    need(git(repo, "rev-parse", f"{HEAD}^{{tree}}").decode() == TREE, "pinned commit tree mismatch")
    sources = {}
    for context in contexts.values():
        refs = refs_from_context(context)
        # Candidate-free callerContextSha256 binds the complete scan records,
        # including their line/context material; cell callerRefs are the
        # deliberately compact projection verified separately below.
        caller_hash = sha(canon(context["callers"]))
        source_id = context["sourceId"]
        sources[source_id] = {"refs": refs, "callerHash": caller_hash}
        need(context["productionCallerCount"] == len(refs), "caller count differs from refs")
        for caller in context["callers"]:
            path = caller["path"]
            data = git_show(repo, path)
            need(sha(data) == caller["fileSha256"], "caller file SHA " + path)
            blob = git(repo, "rev-parse", f"{HEAD}:{path}").decode()
            need(blob == caller["gitBlob"], "caller git blob " + path)
            lines = data.decode("utf-8").splitlines()
            line_number = caller["line"]
            need(1 <= line_number <= len(lines), "caller line outside file " + path)
            actual_line = lines[line_number - 1]
            need(actual_line == caller["lineText"] and text_sha(actual_line) == caller["lineSha256"],
                 "caller line hash/text " + path)
            actual_context = caller["context"]
            for item in actual_context:
                number = item["line"]
                need(1 <= number <= len(lines) and lines[number - 1] == item["text"],
                     "caller context line mismatch " + path)
            need(sha(canon(actual_context)) == caller["contextSha256"], "caller context hash " + path)
        for cell in cells:
            if cell["sourceId"] != source_id:
                continue
            need(cell["callerContextSha256"] == caller_hash, "cell caller-context digest")
            if context["productionCallerCount"] > 0:
                need(cell["callerRefs"] == refs, "cell caller refs differ from context scan")
            else:
                need(cell["callerRefs"] == [], "callerless refs are nonempty")
    return sources


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True, help="Git repository containing the pinned source commit")
    parser.add_argument("--blind-input", type=Path,
                        default=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w79-853-877-blind-20261104/review-cells.jsonl"),
                        help="Original blind ledger used only to recheck its row hashes; never copied into the packet")
    args = parser.parse_args()
    repo = args.repo.resolve()
    manifest, checksum_count = verify_inventory()
    need((manifest["artifact"], manifest["window"], manifest["repository"], manifest["pullRequest"],
          manifest["branch"], manifest["head"], manifest["tree"], manifest["cellCount"]) ==
         ("slskdN PR #409 W79 ranks 853-877 independent cross-review packet", "W79",
          "snapetech-org/slskdN", 409, BRANCH, HEAD, TREE, 300), "packet identity")
    need(manifest.get("callerlessTextIncluded") is False and
         manifest.get("blindCallerlessIssueDetailsIncluded") is False and
         manifest.get("catalogChangesMade") is False and manifest.get("prChanged") is False,
         "callerless/redaction or mutation assertion")

    attestation = readj(ROOT / "input-attestation.json")
    candidate_manifest = readj(ROOT / "inputs/candidate-free-manifest.json")
    primary_manifest = readj(ROOT / "inputs/primary-manifest.json")
    blind_manifest = readj(ROOT / "inputs/blind-manifest.json")
    need(attestation["candidateFreeManifest"]["sha256"] == sha((ROOT / "inputs/candidate-free-manifest.json").read_bytes()),
         "candidate-free manifest hash linkage")
    need(attestation["sourceCurrentCellsSha256"] == sha((ROOT / "inputs/source-current-cells.jsonl").read_bytes()),
         "candidate-free cells hash linkage")
    need(attestation["callerContextsSha256"] == sha((ROOT / "inputs/caller-contexts.jsonl").read_bytes()),
         "caller-context packet hash linkage")
    need(attestation["primaryReviewManifestSha256"] == sha((ROOT / "inputs/primary-manifest.json").read_bytes()),
         "primary manifest hash linkage")
    need(attestation["primaryReviewLedgerSha256"] == sha((ROOT / "inputs/primary-review.jsonl").read_bytes()),
         "primary ledger hash linkage")
    need(attestation["blindReviewManifestSha256"] == sha((ROOT / "inputs/blind-manifest.json").read_bytes()),
         "blind manifest hash linkage")
    input_files = {item["path"]: item for item in candidate_manifest["files"]}
    need(input_files["source-current-cells.jsonl"]["sha256"] == attestation["sourceCurrentCellsSha256"],
         "source-current input manifest binding")
    need(input_files["caller-contexts.jsonl"]["sha256"] == attestation["callerContextsSha256"],
         "caller-context input manifest binding")
    primary_files = {item["path"]: item for item in primary_manifest["files"]}
    need(primary_files["primary-review.jsonl"]["sha256"] == attestation["primaryReviewLedgerSha256"],
         "primary ledger manifest binding")
    blind_info = blind_manifest["files"]["review-cells.jsonl"]
    need(blind_info["sha256"] == attestation["blindOriginalReviewLedgerSha256"],
         "original blind ledger manifest binding")
    need(candidate_manifest["head"] == HEAD and candidate_manifest["tree"] == TREE
         and primary_manifest["head"] == HEAD and primary_manifest["tree"] == TREE,
         "upstream pin mismatch")

    cells_raw = rows_raw(ROOT / "inputs/source-current-cells.jsonl")
    contexts_raw = rows_raw(ROOT / "inputs/caller-contexts.jsonl")
    primary_raw = rows_raw(ROOT / "inputs/primary-review.jsonl")
    cross_raw = rows_raw(ROOT / "cross-review-decisions.jsonl")
    primary_audit = [r for r, _ in rows_raw(ROOT / "primary-proposal-audit.jsonl")]
    proposal_plan = [r for r, _ in rows_raw(ROOT / "proposal-apply-plan.jsonl")]
    noops = [r for r, _ in rows_raw(ROOT / "no-op-ledger-hash-only.jsonl")]
    unresolved = [r for r, _ in rows_raw(ROOT / "unresolved-holds.jsonl")]
    callerless_holds = [r for r, _ in rows_raw(ROOT / "callerless-holds-hash-only.jsonl")]
    blind_redacted = [r for r, _ in rows_raw(ROOT / "blind-review-redacted.jsonl")]
    blind_hashes = [r for r, _ in rows_raw(ROOT / "blind-review-row-hashes.jsonl")]

    cells = [r for r, _ in cells_raw]
    contexts = {r["sourceId"]: r for r, _ in contexts_raw}
    primary_map = {(r["continuationRank"], r["locale"]): (r, raw) for r, raw in primary_raw}
    cross_map = {(r["continuationRank"], r["locale"]): (r, raw) for r, raw in cross_raw}
    expected = {(rank, locale) for rank in RANKS for locale in LOCALES}
    cell_map = {(r["continuationRank"], r["locale"]): (r, raw) for r, raw in cells_raw}
    need(set(cell_map) == expected and set(primary_map) == expected and set(cross_map) == expected,
         "300-cell coverage")
    need(len(contexts) == 25 and len(blind_redacted) == 300 and len(blind_hashes) == 300,
         "context/blind coverage")
    need(len({r["sourceId"] for r in cells}) == 25, "source ID coverage")
    need(all(len([r for r in cells if r["continuationRank"] == rank]) == 12 for rank in RANKS),
         "locale count per rank")
    source_evidence = verify_source_callers(repo, contexts, cells)
    blind_path = args.blind_input.resolve()
    need(blind_path.is_file(), "original blind input unavailable")
    blind_raw = rows_raw(blind_path)
    need(sha(blind_path.read_bytes()) == attestation["blindOriginalReviewLedgerSha256"],
         "original blind input file hash")
    blind_map = {(r["continuationRank"], r["locale"]): (r, raw) for r, raw in blind_raw}
    need(set(blind_map) == expected, "original blind input cell coverage")
    redacted_map = {(r["continuationRank"], r["locale"]): r for r in blind_redacted}
    blind_hash_map = {(r["continuationRank"], r["locale"]): r for r in blind_hashes}
    need(set(redacted_map) == expected and set(blind_hash_map) == expected, "redacted blind coverage")

    catalog_cache = {}
    cross_counts = collections.Counter()
    primary_verdicts = collections.Counter()
    callerless_keys = set()
    primary_correction_keys = set()
    blind_hold_cross = collections.Counter()
    for key in sorted(expected):
        rank, locale = key
        cell, cell_raw = cell_map[key]
        p, p_raw = primary_map[key]
        x, x_raw = cross_map[key]
        b, b_raw = blind_map[key]
        br = redacted_map[key]
        bh = blind_hash_map[key]
        source_id = cell["sourceId"]
        ctx = contexts[source_id]
        backed = ctx["productionCallerCount"] > 0
        expected_ref = source_evidence[source_id]["refs"]
        caller_hash = source_evidence[source_id]["callerHash"]
        need(p["sourceId"] == source_id and x["sourceId"] == source_id and b["sourceId"] == source_id,
             f"source ID binding {rank}/{locale}")
        need(cell["callerContextSha256"] == p["callerContextSha256"] == x["callerContextSha256"] == b["callerContextSha256"] == caller_hash,
             f"caller hash binding {rank}/{locale}")
        need(x["sourceCurrentRowSha256"] == sha(cell_raw), f"candidate-free row hash {rank}/{locale}")
        need(x["primaryReviewRowSha256"] == sha(p_raw), f"primary row hash {rank}/{locale}")
        need(x["blindReviewRowSha256"] == sha(b_raw) == bh["blindReviewRowSha256"],
             f"blind row hash {rank}/{locale}")
        need(bh["sourceSha256"] == cell["sourceSha256"] and
             bh["currentTargetSha256"] == cell["currentTargetSha256"] and
             bh["callerContextSha256"] == caller_hash and bh["blindDecision"] == b["decision"],
             f"blind row hash metadata {rank}/{locale}")
        need(x["blindDecision"] == b["decision"] == br["decision"], f"blind disposition {rank}/{locale}")
        need(x["primaryDisposition"] == p["disposition"], f"primary disposition {rank}/{locale}")

        if not backed:
            callerless_keys.add(key)
            need(rank in CALLERLESS_RANKS and x["crossDisposition"] == "hold",
                 f"callerless cell not held {rank}/{locale}")
            need(x.get("productionCallerCount") == 0 and x.get("callerRefs") is None,
                 f"callerless cross caller evidence {rank}/{locale}")
            need(x.get("sourceTextIncluded") is False and x.get("currentTargetTextIncluded") is False
                 and x.get("primaryProposalTextIncluded") is False and x.get("crossTargetTextIncluded") is False,
                 f"callerless cross text flags {rank}/{locale}")
            need(not (FORBIDDEN_TEXT & set(x)), f"callerless cross text field {rank}/{locale}")
            need(not (FORBIDDEN_TEXT & set(cell)), f"callerless candidate-free text field {rank}/{locale}")
            need(not (FORBIDDEN_TEXT & set(p)), f"callerless primary text field {rank}/{locale}")
            need(not (FORBIDDEN_TEXT & set(bh)) and not (FORBIDDEN_TEXT & set(br)),
                 f"callerless blind text field {rank}/{locale}")
            need("issues" not in br and "blindIssues" not in x and "blindIssueCodes" not in x
                 and br.get("blindIssueDetailsOmitted") is True,
                 f"callerless blind issue details included {rank}/{locale}")
            need(br["sourceTextIncluded"] is False and br["targetTextIncluded"] is False,
                 f"callerless blind text flags {rank}/{locale}")
            need(x["tokenEvidenceSha256"] == p["tokenEvidenceSha256"],
                 f"callerless token evidence hash {rank}/{locale}")
            need(x["sourceSha256"] == cell["sourceSha256"] == p["sourceSha256"]
                 and x["currentTargetSha256"] == cell["currentTargetSha256"] == p["currentTargetSha256"],
                 f"callerless source/current hashes {rank}/{locale}")
            need(x["crossDisposition"] == "hold" and x["holdReasonCode"] == "CALLERLESS_NO_PRODUCTION_CALLER",
                 f"callerless hold reason {rank}/{locale}")
            cross_counts["hold"] += 1
            if b["decision"] == "hold":
                blind_hold_cross["hold"] += 1
            continue

        need(cell.get("sourceTextIncluded") is True and cell.get("currentTargetTextIncluded") is True,
             f"caller-backed candidate text flags {rank}/{locale}")
        need(p.get("sourceTextIncluded") is True and p.get("currentTargetTextIncluded") is True,
             f"caller-backed primary text flags {rank}/{locale}")
        source = cell["source"]
        current = cell["currentTarget"]
        need(text_sha(source) == cell["sourceSha256"] == p["sourceSha256"] == x["sourceSha256"],
             f"source text/hash {rank}/{locale}")
        need(text_sha(current) == cell["currentTargetSha256"] == p["currentTargetSha256"] == x["currentTargetSha256"],
             f"current target text/hash {rank}/{locale}")
        need(p["source"] == source and p["currentTarget"] == current and p["callerRefs"] == expected_ref,
             f"primary text/caller binding {rank}/{locale}")
        need(x.get("source") == source and x.get("currentTarget") == current and x.get("callerRefs") == expected_ref,
             f"cross text/caller binding {rank}/{locale}")
        need(b.get("currentTarget") == current and b.get("currentTargetSha256") == cell["currentTargetSha256"],
             f"blind current text/hash {rank}/{locale}")
        need(b["decision"] in {"accept", "hold"} and br["sourceTextIncluded"] is True and br["targetTextIncluded"] is True,
             f"blind caller-backed row {rank}/{locale}")
        need(br.get("issues", []) == b.get("issues", []), f"redacted blind issue linkage {rank}/{locale}")

        path = cell["catalogPath"]
        if path not in catalog_cache:
            data = git_show(repo, path)
            need(sha(data) == cell["catalogFileSha256"], "catalog file SHA " + path)
            blob = git(repo, "rev-parse", f"{HEAD}:{path}").decode()
            need(blob == cell["catalogGitBlob"], "catalog blob " + path)
            catalog_cache[path] = json.loads(data)
        need(catalog_cache[path].get(source) == current, f"pinned catalog target {rank}/{locale}")

        current_tokens = token_check(source, current)
        need(all(current_tokens[k] for k in (
            "placeholderParityCurrent", "markupParityCurrent",
            "numericTokensPreservedCurrent", "protectedLiteralsPreservedCurrent",
        )), f"current token parity {rank}/{locale}")
        primary_target = p.get("target")
        if p["disposition"] == "correct":
            primary_correction_keys.add(key)
            need(isinstance(primary_target, str) and text_sha(primary_target) == p["targetSha256"],
                 f"primary target hash {rank}/{locale}")
            primary_token = token_check(source, current, primary_target)
            need(p.get("tokenCheck") == primary_token, f"primary token evidence {rank}/{locale}")
            need(all(primary_token["proposal"][k] for k in (
                "placeholderParity", "markupParity", "numericTokensPreserved", "protectedLiteralsPreserved",
            )), f"primary proposal token parity {rank}/{locale}")
            need(x.get("primaryProposal") == primary_target and x.get("primaryProposalSha256") == p["targetSha256"],
                 f"primary proposal audit binding {rank}/{locale}")
            need(x.get("primaryProposalVerdict") in {"adopt", "revise", "cross-hold"},
                 f"primary proposal verdict {rank}/{locale}")
        else:
            need(p["disposition"] == "accept-current", f"unsupported primary disposition {rank}/{locale}")
            need(p.get("tokenCheck") == current_tokens, f"primary current token evidence {rank}/{locale}")
            if x["crossDisposition"] == "propose":
                need(x.get("primaryProposalVerdict") == "independent-proposal",
                     f"new proposal provenance {rank}/{locale}")
            elif x["crossDisposition"] == "keep":
                need(x.get("primaryProposalVerdict") == "no-change", f"keep verdict {rank}/{locale}")
            elif x["crossDisposition"] == "hold":
                need(x.get("primaryProposalVerdict") == "cross-hold", f"cross hold verdict {rank}/{locale}")

        target = x.get("target") if x["crossDisposition"] == "propose" else None
        expected_tokens = token_check(source, current, target) if target is not None else current_tokens
        need(x.get("tokenCheck") == expected_tokens, f"cross token evidence {rank}/{locale}")
        need(x.get("tokenCheckSha256") == sha(canon(expected_tokens)), f"cross token hash {rank}/{locale}")
        need(all(expected_tokens[k] for k in (
            "placeholderParityCurrent", "markupParityCurrent",
            "numericTokensPreservedCurrent", "protectedLiteralsPreservedCurrent",
        )), f"cross current tokens {rank}/{locale}")
        if target is not None:
            need(x.get("crossTargetTextIncluded") is True and text_sha(target) == x["targetSha256"],
                 f"cross proposal hash {rank}/{locale}")
            need(all(expected_tokens["proposal"][k] for k in (
                "placeholderParity", "markupParity", "numericTokensPreserved", "protectedLiteralsPreserved",
            )), f"cross proposal tokens {rank}/{locale}")
        else:
            need(x.get("crossTargetTextIncluded") is not True and "target" not in x,
                 f"non-proposal target text {rank}/{locale}")

        if b["decision"] == "hold":
            blind_hold_cross[x["crossDisposition"]] += 1
        cross_counts[x["crossDisposition"]] += 1
        if x["crossDisposition"] == "hold":
            need(bool(x.get("rationale")) and x.get("holdReasonCode"),
                 f"caller-backed hold needs evidence/rationale {rank}/{locale}")
            unresolved_key = key
        elif x["crossDisposition"] == "keep":
            unresolved_key = None
        elif x["crossDisposition"] == "propose":
            need(bool(x.get("rationale")), f"proposal rationale missing {rank}/{locale}")
            unresolved_key = None
        else:
            fail(f"invalid cross disposition {rank}/{locale}")

    need(callerless_keys == {(rank, locale) for rank in CALLERLESS_RANKS for locale in LOCALES},
         "callerless source set")
    need(cross_counts == collections.Counter({"propose": 46, "keep": 215, "hold": 39}),
         "cross disposition counts")
    need(len(proposal_plan) == 46 and len(noops) == 215 and len(unresolved) == 15 and len(callerless_holds) == 24,
         "proposal/no-op/hold ledger counts")
    need({(r["continuationRank"], r["locale"]) for r in callerless_holds} == callerless_keys,
         "callerless hold ledger coverage")
    need(all(not (FORBIDDEN_TEXT & set(r)) and r.get("sourceTextIncluded") is False
             and r.get("currentTargetTextIncluded") is False for r in callerless_holds),
         "callerless hash-only ledger includes text")
    need({(r["continuationRank"], r["locale"]) for r in unresolved}
         == {(r, l) for r, ls in ((855, LOCALES), (869, {"ja", "zh-Hans", "zh-Hant"})) for l in ls},
         "caller-backed unresolved hold coverage")
    need({(r["continuationRank"], r["locale"]) for r in proposal_plan}
         == {key for key, (row, _) in cross_map.items() if row["crossDisposition"] == "propose"},
         "proposal apply-plan coverage")
    need({(r["continuationRank"], r["locale"]) for r in noops}
         == {key for key, (row, _) in cross_map.items() if row["crossDisposition"] == "keep"},
         "no-op ledger coverage")

    # The source data and selected proposal ledgers are independently reproducible.
    proposal_map = readj(ROOT / "proposal-map.json")
    expected_proposals = {
        f"{rank}|{locale}": row["target"]
        for (rank, locale), (row, _) in cross_map.items()
        if row["crossDisposition"] == "propose"
    }
    need(proposal_map == expected_proposals and len(proposal_map) == 46, "proposal-map linkage")
    for plan in proposal_plan:
        key = (plan["continuationRank"], plan["locale"])
        row = cross_map[key][0]
        need(plan["target"] == row["target"] and plan["targetSha256"] == row["targetSha256"]
             and plan["callerContextSha256"] == row["callerContextSha256"]
             and plan["catalogFileSha256"] == row["catalogFileSha256"]
             and plan["catalogGitBlob"] == row["catalogGitBlob"],
             f"apply plan binding {key}")

    need(len(primary_audit) == len(primary_correction_keys) == 32, "primary proposal audit coverage")
    audit_map = {(r["continuationRank"], r["locale"]): r for r in primary_audit}
    need(set(audit_map) == primary_correction_keys, "primary audit key set")
    primary_verdicts = collections.Counter()
    for key in primary_correction_keys:
        audit = audit_map[key]
        cross = cross_map[key][0]
        primary = primary_map[key][0]
        need(audit["primaryProposal"] == primary["target"]
             and audit["primaryProposalSha256"] == primary["targetSha256"]
             and audit["crossProposal"] == cross.get("target")
             and audit["crossProposalSha256"] == cross.get("targetSha256")
             and audit["crossVerdict"] == cross.get("primaryProposalVerdict"),
             f"primary proposal audit row {key}")
        primary_verdicts[audit["crossVerdict"]] += 1
    need(primary_verdicts == collections.Counter({"adopt": 30, "revise": 2}),
         "primary proposal verdict counts")

    # Verify additional locale terminology evidence against catalogs at the exact commit.
    term_rows = [r for r, _ in rows_raw(ROOT / "locale-term-evidence.jsonl")]
    term_index = {}
    for row in term_rows:
        path = row["catalogPath"]
        data = git_show(repo, path)
        need(sha(data) == row["catalogFileSha256"], "locale term catalog file hash " + path)
        need(git(repo, "rev-parse", f"{HEAD}:{path}").decode() == row["catalogGitBlob"],
             "locale term catalog blob " + path)
        catalog = json.loads(data)
        need(catalog.get(row["sourceKey"]) == row["translation"]
             and text_sha(row["translation"]) == row["translationSha256"],
             "locale term value/hash " + row["locale"])
        term_index[(row["category"], row["locale"], row["sourceKey"])] = row
    source_evidence_rows = [r for r, _ in rows_raw(ROOT / "pinned-source-evidence.jsonl")]
    source_evidence_index = {}
    for row in source_evidence_rows:
        data = git_show(repo, row["path"])
        lines = data.decode("utf-8").splitlines()
        excerpt = [{"line": n, "text": lines[n - 1]} for n in range(row["lineStart"], row["lineEnd"] + 1)]
        need(sha(data) == row["fileSha256"] and git(repo, "rev-parse", f"{HEAD}:{row['path']}").decode() == row["gitBlob"],
             "pinned documentation file hash " + row["path"])
        need(excerpt == row["excerpt"] and sha(canon(excerpt)) == row["excerptSha256"],
             "pinned documentation excerpt " + row["evidenceId"])
        source_evidence_index[row["evidenceId"]] = row
    for row, _ in cross_raw:
        for ref in row.get("supplementalEvidenceRefs", []):
            if ref["kind"] == "pinned-source":
                need(ref["evidenceId"] in source_evidence_index, "missing pinned source reference")
            else:
                key = (ref["category"], ref["locale"], ref["sourceKey"])
                need(key in term_index, "missing locale-term reference " + str(key))

    live_before = readj(ROOT / "live-before.json")
    live_after = readj(ROOT / "live-after.json")
    for snapshot in (live_before, live_after):
        need(snapshot["repository"] == "snapetech-org/slskdN" and snapshot["pullRequest"] == 409
             and snapshot["headRefName"] == BRANCH and snapshot["headRefOid"] == HEAD
             and snapshot["branchRefOid"] == HEAD and snapshot["pullRefOid"] == HEAD
             and snapshot["commitTree"] == TREE and snapshot["state"] == "OPEN"
             and snapshot["draft"] is True and snapshot["merged"] is False,
             "live PR API/branch/pull ref mismatch")
    for field in ("headRefOid", "branchRefOid", "pullRefOid", "pullMergeRefOid", "commitTree"):
        need(live_before[field] == live_after[field], "live ref moved during cross-review: " + field)
    need(manifest.get("liveBeforeSha256") == sha((ROOT / "live-before.json").read_bytes())
         and manifest.get("liveAfterSha256") == sha((ROOT / "live-after.json").read_bytes()),
         "live snapshot checksum in manifest")

    summary = readj(ROOT / "summary.json")
    need(summary["crossDecisionCounts"] == {"keep": 215, "hold": 39, "propose": 46}
         and summary["primaryProposalVerdicts"] == {"adopt": 30, "revise": 2}
         and summary["blindHoldCrossDispositionCounts"] == {"hold": 27, "propose": 44}
         and summary["candidateFreeVerifier"] == "PASS" and summary["primaryVerifier"] == "PASS"
         and summary["liveRefsMatchPin"] is True,
         "summary counts/status")
    upstream = readj(ROOT / "upstream-verification.json")
    need(upstream["pinnedHead"] == HEAD and upstream["pinnedTree"] == TREE
         and upstream["candidateFreeVerifier"]["result"] == "PASS"
         and upstream["primaryVerifier"]["result"] == "PASS"
         and upstream["candidateFreeVerifier"]["tokenMismatchCounts"] ==
             {"placeholder": 0, "markup": 0, "numeric": 0, "protectedLiteral": 0},
         "upstream verification evidence")

    print(json.dumps({
        "result": "PASS", "head": HEAD, "tree": TREE, "cells": 300,
        "callerBackedCells": 276, "callerlessHashOnlyCells": len(callerless_keys),
        "crossDecisions": dict(cross_counts), "primaryProposalsAudited": len(primary_audit),
        "primaryProposalVerdicts": dict(primary_verdicts),
        "blindHoldsAdjudicated": sum(blind_hold_cross.values()),
        "blindHoldCrossDispositionCounts": dict(blind_hold_cross),
        "callerFilesVerified": sum(len(ctx["callers"]) for ctx in contexts.values()),
        "tokenChecksVerified": 276, "localeTermEvidenceRows": len(term_rows),
        "pinnedDocumentationEvidenceRows": len(source_evidence_rows),
        "checksumEntries": checksum_count,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
