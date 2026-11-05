#!/usr/bin/env python3
"""Portable verifier for the sealed W80 cross-review packet. No network access is used."""
import argparse
import collections
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEAD = "7a1ca27fd0519674c3b42a3e3df3638b0f671567"
TREE = "b3525218d0f9676c88c4991e78775d113f18b7d9"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
RANKS = range(878, 903)


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


def readj(root, name):
    return json.loads((root / name).read_text(encoding="utf-8"))


def rows_raw(root, name):
    result = []
    for line in (root / name).read_bytes().splitlines():
        if line.strip():
            result.append((json.loads(line), line))
    return result


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args]).strip().decode("utf-8")


def git_bytes(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def token_check(source, current, target=None):
    def placeholders(value):
        return collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", value))
    def markup(value):
        return collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", value))
    def numbers(value):
        return ["".join(str(unicodedata.digit(ch)) if ch.isdigit() else ch for ch in item)
                for item in re.findall(r"\d+", value)]
    def protected(value):
        result = set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", value))
        result.update(item for item in ("slskdN", "Tor", "Wishlist", "Chromaprint") if item in value)
        return sorted(result)
    def not_less(source_tokens, target_tokens):
        source_tokens, target_tokens = collections.Counter(source_tokens), collections.Counter(target_tokens)
        return all(target_tokens[item] >= count for item, count in source_tokens.items())
    result = {
        "sourcePlaceholderTokens": sorted(placeholders(source).elements()),
        "currentPlaceholderTokens": sorted(placeholders(current).elements()),
        "sourceMarkupTokens": sorted(markup(source).elements()),
        "currentMarkupTokens": sorted(markup(current).elements()),
        "sourceNumericTokens": numbers(source),
        "currentNumericTokens": numbers(current),
        "sourceProtectedLiterals": protected(source),
        "currentProtectedLiterals": [item for item in protected(source) if item in current],
        "placeholderParityCurrent": placeholders(source) == placeholders(current),
        "markupParityCurrent": markup(source) == markup(current),
        "numericTokensPreservedCurrent": not_less(numbers(source), numbers(current)),
        "protectedLiteralsPreservedCurrent": all(item in current for item in protected(source)),
    }
    if target is not None:
        result["proposal"] = {
            "placeholderTokens": sorted(placeholders(target).elements()),
            "markupTokens": sorted(markup(target).elements()),
            "numericTokens": numbers(target),
            "protectedLiterals": protected(target),
            "placeholderParity": placeholders(source) == placeholders(target),
            "markupParity": markup(source) == markup(target),
            "numericTokensPreserved": not_less(numbers(source), numbers(target)),
            "protectedLiteralsPreserved": all(item in target for item in protected(source)),
        }
    return result


def verify_inventory():
    manifest = readj(ROOT, "manifest.json")
    listed = {item["path"] for item in manifest["files"]}
    need(len(listed) == len(manifest["files"]), "duplicate packet file path")
    need(not ({"manifest.json", "SHA256SUMS.txt"} & listed), "recursive packet inventory")
    actual = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*")
              if path.is_file() and path.name not in {"manifest.json", "SHA256SUMS.txt"}}
    need(actual == listed, "packet files differ from manifest")
    for item in manifest["files"]:
        path = (ROOT / item["path"]).resolve()
        need(path.is_relative_to(ROOT.resolve()) and path.is_file(), "unsafe or missing packet file " + item["path"])
        data = path.read_bytes()
        need(len(data) == item["bytes"] and sha(data) == item["sha256"], "manifest hash mismatch " + item["path"])
    sums = {}
    for line in (ROOT / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        need(name not in sums, "duplicate checksum path")
        path = (ROOT / name).resolve()
        need(path.is_relative_to(ROOT.resolve()) and path.is_file(), "unsafe checksum path " + name)
        need(sha(path.read_bytes()) == digest, "checksum mismatch " + name)
        sums[name] = digest
    need(set(sums) == listed | {"manifest.json"}, "checksum inventory mismatch")
    need((manifest.get("artifact"), manifest.get("window"), manifest.get("repository"),
          manifest.get("pullRequest"), manifest.get("branch"), manifest.get("head"),
          manifest.get("tree"), manifest.get("sourceCount"), manifest.get("localeCount"),
          manifest.get("cellCount")) ==
         ("slskdN PR #409 W80 ranks 878-902 independent cross-review packet", "W80",
          "snapetech-org/slskdN", 409, BRANCH, HEAD, TREE, 25, 12, 300), "packet identity")
    need(manifest.get("crossDecisionCounts") == {"keep": 219, "propose": 81, "hold": 0},
         "manifest disposition counts")
    need(manifest.get("proposalCount") == 81 and manifest.get("noOpCount") == 219
         and manifest.get("holdCount") == 0 and manifest.get("callerlessCellCount") == 0,
         "manifest proposal/hold totals")
    need(manifest.get("primaryProposalVerdicts") == {"adopt": 25, "revise": 28, "reject": 2},
         "manifest primary verdict counts")
    need(manifest.get("blindSuggestionVerdicts") == {"adopt": 75, "revise": 4, "reject": 0}
         and manifest.get("blindSuggestionCountAudited") == 79,
         "manifest blind verdict counts")
    need(manifest.get("candidateFreeVerifier") == "PASS" and manifest.get("primaryVerifier") == "PASS"
         and manifest.get("blindPacketChecksums") == "PASS", "upstream validation assertions")
    need(manifest.get("sourceWorktreeHeadAtSeal") == HEAD and manifest.get("sourceWorktreeTreeAtSeal") == TREE
         and manifest.get("sourceWorktreeCleanAtSeal") is True, "source worktree seal assertion")
    need(manifest.get("prBodyQueried") is False and manifest.get("catalogChangesMade") is False
         and manifest.get("repositoryOrPrEdited") is False and manifest.get("appliedToRepository") is False,
         "scope/mutation assertions")
    return manifest, len(sums)


def parse_checksum_list(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        need(name not in values, "duplicate upstream checksum entry " + name)
        values[name] = digest
    return values


def verify_input_attestation():
    att = readj(ROOT, "input-attestation.json")
    input_root = ROOT / "inputs"
    links = {
        "candidateFreeManifestSha256": "candidate-free-manifest.json",
        "candidateFreeChecksumListSha256": "candidate-free-checksums.txt",
        "sourceCurrentCellsSha256": "source-current-cells.jsonl",
        "callerContextsSha256": "caller-contexts.jsonl",
        "catalogStructureSha256": "catalog-structure.jsonl",
        "primaryManifestSha256": "primary-manifest.json",
        "primaryChecksumListSha256": "primary-checksums.txt",
        "primaryReviewLedgerSha256": "primary-review.jsonl",
        "blindManifestSha256": "blind-manifest.json",
        "blindChecksumListSha256": "blind-checksums.txt",
        "blindReviewLedgerSha256": "blind-decisions.jsonl",
    }
    for field, name in links.items():
        need(att.get(field) == sha((input_root / name).read_bytes()), "input attestation mismatch " + name)

    cm = readj(input_root, "candidate-free-manifest.json")
    pm = readj(input_root, "primary-manifest.json")
    bm = readj(input_root, "blind-manifest.json")
    need((cm.get("artifact"), cm.get("window"), cm.get("candidateFree"), cm.get("head"), cm.get("tree"),
          cm.get("cellCount"), cm.get("prBodyQueried"), cm.get("proposedTargetsIncluded"),
          cm.get("reviewDecisionsIncluded"), cm.get("blindReviewUsed"), cm.get("crossReviewUsed")) ==
         ("slskdN PR #409 W80 ranks 878-902 candidate-free exact-head input", "W80", True,
          HEAD, TREE, 300, False, False, False, False, False), "candidate-free manifest identity/purity")
    need((pm.get("artifact"), pm.get("window"), pm.get("head"), pm.get("tree"), pm.get("cellCount"),
          pm.get("proposalCount"), pm.get("holdCount"), pm.get("candidateFree"), pm.get("blindReviewUsed"),
          pm.get("crossReviewUsed"), pm.get("prBodyQueried")) ==
         ("slskdN PR #409 W80 independent primary semantic review", "W80", HEAD, TREE, 300, 55, 0,
          True, False, False, False), "primary manifest identity/purity")
    need((bm.get("artifact"), bm.get("window"), bm.get("head"), bm.get("tree"), bm.get("cellCount")) ==
         ("slskdN PR #409 W80 independent candidate-free blind semantic review", "W80", HEAD, TREE, 300),
         "blind manifest identity/purity")
    need(bm.get("exposure", {}).get("prBodyQueried") is False
         and bm.get("exposure", {}).get("primaryReviewOutputOpened") is False
         and bm.get("exposure", {}).get("proposedTargetsViewed") is False
         and bm.get("allCurrentTargetHashesMatchInput") is True, "blind independence/current hash assertion")

    candidate_checks = parse_checksum_list(input_root / "candidate-free-checksums.txt")
    primary_checks = parse_checksum_list(input_root / "primary-checksums.txt")
    blind_checks = parse_checksum_list(input_root / "blind-checksums.txt")
    copied_candidate = ["source-current-cells.jsonl", "caller-contexts.jsonl", "catalog-structure.jsonl"]
    for name in copied_candidate:
        data = (input_root / name).read_bytes()
        need(candidate_checks.get(name) == sha(data), "candidate-free original checksum linkage " + name)
    need(candidate_checks.get("manifest.json") == sha((input_root / "candidate-free-manifest.json").read_bytes()),
         "candidate-free manifest checksum linkage")
    need(primary_checks.get("primary-review.jsonl") == sha((input_root / "primary-review.jsonl").read_bytes()),
         "primary original checksum linkage")
    need(primary_checks.get("manifest.json") == sha((input_root / "primary-manifest.json").read_bytes()),
         "primary manifest checksum linkage")
    need(blind_checks.get("decisions.jsonl") == sha((input_root / "blind-decisions.jsonl").read_bytes()),
         "blind original checksum linkage")
    need(blind_checks.get("manifest.json") == sha((input_root / "blind-manifest.json").read_bytes()),
         "blind manifest checksum linkage")

    candidate_files = {item["path"]: item for item in cm["files"]}
    for name in copied_candidate:
        item = candidate_files[name]
        data = (input_root / name).read_bytes()
        need(len(data) == item["bytes"] and sha(data) == item["sha256"], "candidate manifest file link " + name)
    primary_files = {item["path"]: item for item in pm["files"]}
    primary_data = (input_root / "primary-review.jsonl").read_bytes()
    need(len(primary_data) == primary_files["primary-review.jsonl"]["bytes"]
         and sha(primary_data) == primary_files["primary-review.jsonl"]["sha256"], "primary manifest file link")
    blind_files = {item["path"]: item for item in bm["outputFiles"]}
    blind_data = (input_root / "blind-decisions.jsonl").read_bytes()
    need(len(blind_data) == blind_files["decisions.jsonl"]["bytes"]
         and sha(blind_data) == blind_files["decisions.jsonl"]["sha256"], "blind manifest file link")

    for name in ("candidate-free-checksums.txt", "primary-checksums.txt", "blind-checksums.txt"):
        need((input_root / name).is_file(), "missing upstream checksum list " + name)
    return cm, pm, bm


def refs_from_context(context):
    return [{"path": caller["path"], "line": caller["line"], "lineSha256": caller["lineSha256"],
             "contextSha256": caller["contextSha256"], "fileSha256": caller["fileSha256"],
             "gitBlob": caller["gitBlob"]} for caller in context["callers"]]


def verify_pinned_source(repo, cells, contexts, catalog_structures, pinned_evidence):
    need(git(repo, "rev-parse", "HEAD") == HEAD, "repository HEAD differs from pinned source")
    need(git(repo, "rev-parse", "HEAD^{tree}") == TREE, "repository tree differs from pinned source")
    need(git(repo, "cat-file", "-e", f"{HEAD}^{{commit}}") == "", "pinned commit object is unavailable")
    context_map = {row["sourceId"]: row for row in contexts}
    need(len(context_map) == 25 and len(pinned_evidence) == 25, "caller context coverage")
    evidence_map = {row["sourceId"]: row for row in pinned_evidence}
    need(len(evidence_map) == 25, "duplicate pinned evidence source")

    for source_id, context in context_map.items():
        caller_hash = sha(canon(context["callers"]))
        need(context["productionCallerCount"] == len(context["callers"]) and context["productionCallerCount"] > 0,
             "selected source missing callers " + source_id)
        evidence = evidence_map[source_id]
        for key in ("continuationRank", "remainingQueueRank", "sourceId", "source", "sourceSha256", "callers"):
            need(evidence.get(key) == context.get(key), "pinned evidence mismatch " + source_id + "/" + key)
        need(evidence.get("head") == HEAD and evidence.get("tree") == TREE
             and evidence.get("callerContextSha256") == caller_hash
             and evidence.get("productionCallerCount") == context["productionCallerCount"],
             "pinned evidence attestation " + source_id)
        for caller in context["callers"]:
            path = caller["path"]
            data = git_bytes(repo, "show", f"{HEAD}:{path}")
            need(sha(data) == caller["fileSha256"], "pinned caller file hash " + path)
            need(git(repo, "rev-parse", f"{HEAD}:{path}") == caller["gitBlob"], "pinned caller blob " + path)
            lines = data.decode("utf-8").splitlines()
            number = caller["line"]
            need(1 <= number <= len(lines), "caller line outside pinned file " + path)
            actual_line = lines[number - 1]
            need(actual_line == caller["lineText"] and text_sha(actual_line) == caller["lineSha256"],
                 "caller line text/hash " + path)
            for context_line in caller["context"]:
                context_number = context_line["line"]
                need(1 <= context_number <= len(lines) and lines[context_number - 1] == context_line["text"],
                     "caller context text " + path)
            need(sha(canon(caller["context"])) == caller["contextSha256"], "caller context hash " + path)

    need(len(catalog_structures) == 12, "catalog structure locale coverage")
    structures = {row["locale"]: row for row in catalog_structures}
    need(set(structures) == set(LOCALES), "catalog locale set")
    catalogs = {}
    for locale, structure in structures.items():
        path = structure["catalogPath"]
        data = git_bytes(repo, "show", f"{HEAD}:{path}")
        need(sha(data) == structure["sha256"], "catalog file SHA " + locale)
        need(git(repo, "rev-parse", f"{HEAD}:{path}") == structure["gitBlob"], "catalog blob " + locale)
        catalog = json.loads(data.decode("utf-8"))
        need(len(catalog) == structure["entryCount"] == 6176, "catalog key count " + locale)
        catalogs[locale] = (path, structure, catalog)

    for cell in cells:
        source_id = cell["sourceId"]
        context = context_map[source_id]
        refs = refs_from_context(context)
        need(cell["callerRefs"] == refs and cell["callerContextSha256"] == sha(canon(context["callers"])),
             "cell exact caller refs/context " + source_id)
        need(cell["sourceTextIncluded"] is True and cell["currentTargetTextIncluded"] is True,
             "caller-backed input text flags " + source_id)
        need(cell["sourceSha256"] == text_sha(cell["source"])
             and source_id == "src_" + text_sha(cell["source"])[:16], "source identity/hash " + source_id)
        path, structure, catalog = catalogs[cell["locale"]]
        need(cell["catalogPath"] == path and cell["catalogFileSha256"] == structure["sha256"]
             and cell["catalogGitBlob"] == structure["gitBlob"], "cell catalog pin " + source_id)
        need(cell["catalogKey"] == cell["source"] and catalog.get(cell["source"]) == cell["currentTarget"],
             "cell exact pinned current catalog target " + source_id + "/" + cell["locale"])
        need(cell["currentTargetSha256"] == text_sha(cell["currentTarget"]),
             "current target hash " + source_id + "/" + cell["locale"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path,
                        help="Git worktree or clone containing the exact pinned commit")
    args = parser.parse_args()
    repo = args.repo.resolve()
    manifest, checksum_count = verify_inventory()
    cm, pm, bm = verify_input_attestation()
    need(git(repo, "rev-parse", "HEAD") == HEAD and git(repo, "rev-parse", "HEAD^{tree}") == TREE,
         "exact pinned repository HEAD/tree")

    input_root = ROOT / "inputs"
    cell_rows = rows_raw(input_root, "source-current-cells.jsonl")
    context_rows = rows_raw(input_root, "caller-contexts.jsonl")
    catalog_rows = rows_raw(input_root, "catalog-structure.jsonl")
    primary_rows = rows_raw(input_root, "primary-review.jsonl")
    blind_rows = rows_raw(input_root, "blind-decisions.jsonl")
    cross_rows = rows_raw(ROOT, "cross-review-decisions.jsonl")
    proposal_rows = rows_raw(ROOT, "proposal-apply-plan.jsonl")
    primary_audit_rows = rows_raw(ROOT, "primary-proposal-audit.jsonl")
    blind_audit_rows = rows_raw(ROOT, "blind-suggestion-audit.jsonl")
    pinned_rows = rows_raw(ROOT, "pinned-source-evidence.jsonl")

    cells = [row for row, _ in cell_rows]
    contexts = [row for row, _ in context_rows]
    context_map = {row["sourceId"]: row for row in contexts}
    catalog_structures = [row for row, _ in catalog_rows]
    expected = {(rank, locale) for rank in RANKS for locale in LOCALES}
    cell_map = {(row["continuationRank"], row["locale"]): (row, raw) for row, raw in cell_rows}
    primary_map = {(row["continuationRank"], row["locale"]): (row, raw) for row, raw in primary_rows}
    blind_map = {(row["continuationRank"], row["locale"]): (row, raw) for row, raw in blind_rows}
    cross_map = {(row["continuationRank"], row["locale"]): (row, raw) for row, raw in cross_rows}
    need(len(cells) == len(primary_rows) == len(blind_rows) == len(cross_rows) == 300,
         "300-row ledger coverage")
    need(set(cell_map) == set(primary_map) == set(blind_map) == set(cross_map) == expected,
         "rank/locale key set")
    need([row["continuationRank"] for row in cells] == [rank for rank in RANKS for _ in LOCALES]
         and [row["locale"] for row in cells] == LOCALES * len(list(RANKS)), "candidate-free ordering")

    verify_pinned_source(repo, cells, contexts, catalog_structures, [row for row, _ in pinned_rows])

    cross_counts = collections.Counter()
    primary_verdicts = collections.Counter()
    blind_verdicts = collections.Counter()
    primary_corrections = set()
    blind_suggestions = set()
    current_token_mismatch_keys = set()
    for key in sorted(expected):
        rank, locale = key
        cell, cell_raw = cell_map[key]
        p, p_raw = primary_map[key]
        b, b_raw = blind_map[key]
        x, _ = cross_map[key]
        source_id = cell["sourceId"]
        for field in ("continuationRank", "remainingQueueRank", "sourceId", "sourceSha256", "locale",
                      "catalogPath", "catalogFileSha256", "catalogGitBlob", "currentTargetSha256",
                      "callerContextSha256", "callerRefs"):
            need(p.get(field) == cell.get(field), f"primary/input binding {rank}/{locale}/{field}")
        for field in ("continuationRank", "remainingQueueRank", "sourceId", "sourceSha256", "locale",
                      "catalogPath", "currentTargetSha256", "callerContextSha256", "callerRefs"):
            need(b.get(field) == cell.get(field), f"blind/input binding {rank}/{locale}/{field}")
        need(p.get("disposition") in {"accept-current", "correct"}, "primary disposition " + str(key))
        need(b.get("decision") in {"accept", "correction", "refinement"}, "blind decision " + str(key))
        if p["disposition"] == "correct":
            primary_corrections.add(key)
            need(p.get("target") and p.get("targetSha256") == text_sha(p["target"]), "primary target hash " + str(key))
        else:
            need("target" not in p and "targetSha256" not in p, "primary accept has proposal " + str(key))
        if b.get("recommendedTarget"):
            blind_suggestions.add(key)
            need(b["decision"] in {"correction", "refinement"}, "blind recommendation decision " + str(key))
        else:
            need(b["decision"] == "accept", "blind non-accept lacks recommendation " + str(key))
        if p["disposition"] == "correct":
            need(p.get("targetSha256") == text_sha(p["target"]), "primary proposed target hash " + str(key))
        if b.get("recommendedTarget"):
            need(isinstance(b["recommendedTarget"], str) and bool(b["recommendedTarget"]),
                 "blind target type " + str(key))

        need((x.get("schemaVersion"), x.get("window"), x.get("head"), x.get("tree")) ==
             (1, "W80", HEAD, TREE), "cross row identity " + str(key))
        for field in ("continuationRank", "remainingQueueRank", "sourceId", "sourceIdSha256", "locale",
                      "source", "sourceSha256", "catalogKey", "catalogPath", "catalogFileSha256",
                      "catalogGitBlob", "currentTarget", "currentTargetSha256", "callerContextSha256"):
            need(x.get(field) == cell.get(field) if field != "sourceIdSha256" else
                 x.get(field) == text_sha(cell["sourceId"]), f"cross/input binding {rank}/{locale}/{field}")
        need(x.get("sourceCurrentRowSha256") == sha(cell_raw)
             and x.get("primaryReviewRowSha256") == sha(p_raw)
             and x.get("blindReviewRowSha256") == sha(b_raw), "cross source row hashes " + str(key))
        need(x.get("primaryDisposition") == p["disposition"]
             and x.get("primaryProposal") == p.get("target")
             and x.get("primaryProposalSha256") == p.get("targetSha256"), "cross primary binding " + str(key))
        need(x.get("blindDecision") == b["decision"]
             and x.get("blindRecommendedTarget") == b.get("recommendedTarget")
             and x.get("blindRecommendedTargetSha256") == (text_sha(b["recommendedTarget"]) if b.get("recommendedTarget") else None)
             and x.get("blindReason") == b["reason"], "cross blind binding " + str(key))
        need(x.get("callerRefs") == cell["callerRefs"]
             and x.get("productionCallerCount") == context_map[cell["sourceId"]]["productionCallerCount"],
             "cross exact caller binding " + str(key))
        need(x.get("sourceTextIncluded") is True and x.get("currentTargetTextIncluded") is True
             and x.get("confidence") in {"high", "moderate", "low"} and bool(x.get("rationale")),
             "cross text/confidence/rationale " + str(key))

        target = x.get("crossTarget") if x["crossDisposition"] == "propose" else None
        expected_token = token_check(cell["source"], cell["currentTarget"], target)
        need(x.get("tokenCheck") == expected_token, "cross token record " + str(key))
        current_ok = all(expected_token[name] for name in (
            "placeholderParityCurrent", "markupParityCurrent", "numericTokensPreservedCurrent",
            "protectedLiteralsPreservedCurrent"))
        if not current_ok:
            current_token_mismatch_keys.add(key)
            need(key == (885, "ar") and expected_token["placeholderParityCurrent"]
                 and expected_token["markupParityCurrent"] and expected_token["numericTokensPreservedCurrent"]
                 and not expected_token["protectedLiteralsPreservedCurrent"],
                 "unexpected current target token mismatch " + str(key))
        if target is not None:
            need(x.get("crossDisposition") == "propose" and x.get("crossTargetSha256") == text_sha(target),
                 "cross target hash " + str(key))
            need(target != cell["currentTarget"], "cross target is unchanged " + str(key))
            need(x.get("crossTargetSource") in {"primary", "blind"}, "cross target source " + str(key))
            if x["crossTargetSource"] == "primary":
                need(p.get("disposition") == "correct" and target == p.get("target"),
                     "selected primary target mismatch " + str(key))
            else:
                need(target == b.get("recommendedTarget"), "selected blind target mismatch " + str(key))
            need(all(expected_token["proposal"][name] for name in (
                "placeholderParity", "markupParity", "numericTokensPreserved", "protectedLiteralsPreserved")),
                "proposal token safety " + str(key))
        else:
            need(x["crossDisposition"] == "keep" and x.get("crossTargetSource") is None
                 and x.get("crossTargetSha256") is None and "crossTarget" not in x,
                 "keep row contains cross target " + str(key))
        cross_counts[x["crossDisposition"]] += 1

        if p["disposition"] == "correct":
            verdict = x["primaryProposalVerdict"]
            need(verdict in {"adopt", "revise", "reject"}, "primary proposal verdict " + str(key))
            need((verdict == "adopt" and target == p["target"])
                 or (verdict == "revise" and target is not None and target != p["target"])
                 or (verdict == "reject" and target is None), "primary verdict/target mismatch " + str(key))
            primary_verdicts[verdict] += 1
        else:
            need(x["primaryProposalVerdict"] == ("independent-proposal" if target is not None else "no-change"),
                 "non-primary proposal provenance " + str(key))
        if b.get("recommendedTarget"):
            verdict = x["blindSuggestionVerdict"]
            need(verdict in {"adopt", "revise", "reject"}, "blind suggestion verdict " + str(key))
            need((verdict == "adopt" and target == b["recommendedTarget"])
                 or (verdict == "revise" and target is not None and target != b["recommendedTarget"])
                 or (verdict == "reject" and target is None), "blind verdict/target mismatch " + str(key))
            blind_verdicts[verdict] += 1
        else:
            need(x["blindSuggestionVerdict"] == "not-proposed", "unexpected blind suggestion verdict " + str(key))

    need(current_token_mismatch_keys == {(885, "ar")}, "baseline token mismatch key set")
    need(cm.get("baselineTokenMismatchSummary", {}).get("protectedLiteral") == 1,
         "candidate-free baseline mismatch count")
    need(cross_counts == collections.Counter({"keep": 219, "propose": 81}), "cross counts")
    need(primary_verdicts == collections.Counter({"adopt": 25, "revise": 28, "reject": 2}), "primary audits")
    need(blind_verdicts == collections.Counter({"adopt": 75, "revise": 4}), "blind audits")
    need(len(primary_corrections) == 55 and len(blind_suggestions) == 79, "input proposal/suggestion counts")

    primary_audits = [row for row, _ in primary_audit_rows]
    blind_audits = [row for row, _ in blind_audit_rows]
    primary_audit_map = {(row["continuationRank"], row["locale"]): row for row in primary_audits}
    blind_audit_map = {(row["continuationRank"], row["locale"]): row for row in blind_audits}
    need(len(primary_audits) == len(primary_corrections) and set(primary_audit_map) == primary_corrections,
         "primary proposal audit coverage")
    need(len(blind_audits) == len(blind_suggestions) and set(blind_audit_map) == blind_suggestions,
         "blind suggestion audit coverage")
    for key in primary_corrections:
        audit = primary_audit_map[key]
        cross = cross_map[key][0]
        primary = primary_map[key][0]
        need(audit.get("primaryProposal") == primary["target"]
             and audit.get("primaryProposalSha256") == primary["targetSha256"]
             and audit.get("crossTarget") == cross.get("crossTarget")
             and audit.get("crossTargetSha256") == cross.get("crossTargetSha256")
             and audit.get("crossVerdict") == cross["primaryProposalVerdict"]
             and audit.get("primaryReviewRowSha256") == cross["primaryReviewRowSha256"],
             "primary audit row binding " + str(key))
    for key in blind_suggestions:
        audit = blind_audit_map[key]
        cross = cross_map[key][0]
        blind = blind_map[key][0]
        need(audit.get("blindRecommendedTarget") == blind["recommendedTarget"]
             and audit.get("blindRecommendedTargetSha256") == text_sha(blind["recommendedTarget"])
             and audit.get("crossTarget") == cross.get("crossTarget")
             and audit.get("crossTargetSha256") == cross.get("crossTargetSha256")
             and audit.get("crossVerdict") == cross["blindSuggestionVerdict"]
             and audit.get("blindReviewRowSha256") == cross["blindReviewRowSha256"],
             "blind audit row binding " + str(key))

    proposal_map = readj(ROOT, "proposal-map.json")
    expected_proposals = {f"{rank}|{locale}": row[0]["crossTarget"] for (rank, locale), row in cross_map.items()
                          if row[0]["crossDisposition"] == "propose"}
    need(proposal_map == expected_proposals and len(proposal_map) == 81, "proposal map")
    plan = [row for row, _ in proposal_rows]
    plan_map = {(row["continuationRank"], row["locale"]): row for row in plan}
    expected_keys = {key for key, (row, _) in cross_map.items() if row["crossDisposition"] == "propose"}
    need(len(plan) == 81 and set(plan_map) == expected_keys, "proposal plan coverage")
    for key in expected_keys:
        row = cross_map[key][0]
        item = plan_map[key]
        need(item.get("target") == row["crossTarget"] and item.get("targetSha256") == row["crossTargetSha256"]
             and item.get("targetSource") == row["crossTargetSource"]
             and item.get("callerContextSha256") == row["callerContextSha256"]
             and item.get("catalogFileSha256") == row["catalogFileSha256"]
             and item.get("catalogGitBlob") == row["catalogGitBlob"]
             and item.get("primaryReviewRowSha256") == row["primaryReviewRowSha256"]
             and item.get("blindReviewRowSha256") == row["blindReviewRowSha256"]
             and item.get("planOnly") is True and item.get("appliedToRepository") is False,
             "proposal plan row binding " + str(key))

    summary = readj(ROOT, "summary.json")
    need(summary.get("crossDecisionCounts") == {"keep": 219, "propose": 81}
         and summary.get("crossProposalCount") == 81 and summary.get("noOpCount") == 219
         and summary.get("crossHoldCount") == 0 and summary.get("callerlessCellCount") == 0,
         "summary disposition totals")
    need(summary.get("catalogCurrentValuesReadBack") == 300
         and summary.get("proposalTargetHashesVerified") == 81
         and summary.get("baselineCurrentTokenMismatch") == {
             "rank": 885, "locale": "ar", "protectedLiteral": "ID", "resolvedByCrossTarget": True
         }, "summary current-value/proposal/baseline mismatch audit")
    need(summary.get("primaryProposalCountAudited") == 55
         and summary.get("primaryProposalVerdicts") == {"adopt": 25, "revise": 28, "reject": 2}
         and summary.get("newProposalsBeyondPrimary") == 28,
         "summary primary audit counts")
    need(summary.get("blindSuggestionCountAudited") == 79
         and summary.get("blindSuggestionVerdicts") == {"adopt": 75, "revise": 4, "reject": 0},
         "summary blind audit counts")
    need(summary.get("inputAttestationSha256") == sha((ROOT / "input-attestation.json").read_bytes()),
         "summary input attestation hash")
    need(summary.get("candidateFreeVerifier") == "PASS" and summary.get("primaryVerifier") == "PASS"
         and summary.get("blindChecksums") == "PASS" and summary.get("prBodyQueried") is False
         and summary.get("catalogChangesMade") is False and summary.get("repositoryOrPrEdited") is False
         and summary.get("appliedToRepository") is False, "summary scope assertions")
    live_before = readj(ROOT, "live-before.json")
    live_after = readj(ROOT, "live-after.json")
    need(live_before.get("prBodyQueried") is False and live_after.get("prBodyQueried") is False,
         "upstream PR body projection flags")
    need(live_before.get("headRefOid") == HEAD and live_before.get("branchRefOid") == HEAD
         and live_before.get("pullRefOid") == HEAD and live_before.get("commitTree") == TREE
         and live_after.get("headRefOid") == HEAD and live_after.get("branchRefOid") == HEAD
         and live_after.get("pullRefOid") == HEAD and live_after.get("commitTree") == TREE,
         "upstream live ref snapshots")
    upstream = readj(ROOT, "upstream-verification.json")
    need(upstream.get("head") == HEAD and upstream.get("tree") == TREE and upstream.get("prBodyQueried") is False
         and upstream.get("liveBeforeSha256") == sha((ROOT / "live-before.json").read_bytes())
         and upstream.get("liveAfterSha256") == sha((ROOT / "live-after.json").read_bytes()),
         "upstream verification linkage")

    print(json.dumps({
        "result": "PASS",
        "window": "W80",
        "head": HEAD,
        "tree": TREE,
        "cellCount": 300,
        "callerBackedCells": 300,
        "dispositions": dict(cross_counts),
        "proposals": len(expected_proposals),
        "primaryProposalAudit": dict(primary_verdicts),
        "blindSuggestionAudit": dict(blind_verdicts),
        "baselineCurrentTokenMismatch": {"rank": 885, "locale": "ar", "protectedLiteral": "ID",
                                         "resolvedByCrossTarget": True},
        "pinnedCallerAndCatalogVerification": "PASS",
        "packetChecksums": checksum_count,
        "prBodyQueried": False,
        "repositoryOrPrEdited": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
