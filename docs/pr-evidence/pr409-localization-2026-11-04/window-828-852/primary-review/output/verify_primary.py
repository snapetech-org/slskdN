#!/usr/bin/env python3
"""Portable verifier for the W78 independent primary review packet."""
import argparse
import collections
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent.parent / "candidate-free" / "input"
HEAD = "4120c9637e71466dc98d51a5a342dee199a1e004"
TREE = "063b62f268eb81253d2b9b4c77ad045c2f25a394"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
FORBIDDEN_HOLD_TEXT_FIELDS = {"source", "catalogKey", "currentTarget", "target", "proposedTarget"}


def fail(message):
    raise SystemExit("FAIL: " + message)


def need(condition, message):
    if not condition:
        fail(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def readj(path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def ph(value):
    return collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", value))


def tags(value):
    return collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", value))


def nums(value):
    return ["".join(str(unicodedata.digit(ch)) if ch.isdigit() else ch for ch in match)
            for match in re.findall(r"\d+", value)]


def prot(value):
    tokens = set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", value))
    tokens.update(token for token in ("slskdN", "Tor", "Wishlist", "Chromaprint") if token in value)
    return sorted(tokens)


def not_less(source, target):
    src, dst = collections.Counter(source), collections.Counter(target)
    return all(dst[token] >= count for token, count in src.items())


def token_check(source, current, target=None):
    result = {
        "sourcePlaceholderTokens": sorted(ph(source).elements()),
        "currentPlaceholderTokens": sorted(ph(current).elements()),
        "sourceMarkupTokens": sorted(tags(source).elements()),
        "currentMarkupTokens": sorted(tags(current).elements()),
        "sourceNumericTokens": nums(source), "currentNumericTokens": nums(current),
        "sourceProtectedLiterals": prot(source), "currentProtectedLiterals": [x for x in prot(source) if x in current],
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


def file_inventory():
    manifest = readj(ROOT / "manifest.json")
    expected = {item["path"] for item in manifest["files"]}
    need(len(expected) == len(manifest["files"]), "duplicate manifest paths")
    need(not ({"manifest.json", "SHA256SUMS.txt"} & expected), "recursive manifest")
    for item in manifest["files"]:
        path = (ROOT / item["path"]).resolve()
        need(path.is_relative_to(ROOT.resolve()) and path.is_file(), "missing/unsafe file " + item["path"])
        data = path.read_bytes()
        need(len(data) == item["bytes"] and sha(data) == item["sha256"], "manifest digest " + item["path"])
    actual = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*")
              if path.is_file() and path.name not in {"manifest.json", "SHA256SUMS.txt"}}
    need(actual == expected, "manifest file inventory differs")
    sums = {}
    for line in (ROOT / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split("  ", 1)
            need(name not in sums, "duplicate checksum path")
            sums[name] = digest
    need(set(sums) == expected | {"manifest.json"}, "checksum inventory differs")
    for name, digest in sums.items():
        need((ROOT / name).is_file() and sha((ROOT / name).read_bytes()) == digest, "checksum mismatch " + name)
    return manifest, len(sums)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="clean worktree at the pinned PR head")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    manifest, checksum_count = file_inventory()
    input_result = json.loads(subprocess.check_output(
        ["python3", str(INPUT / "verify_input.py"), "--repo", str(repo)], text=True))
    need(input_result.get("result") == "PASS" and input_result.get("head") == HEAD and input_result.get("tree") == TREE,
         "candidate-free input verifier")
    need(subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip() == HEAD and
         subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"], text=True).strip() == TREE,
         "local source head/tree")
    need(not subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain=v1"], text=True).strip(),
         "local source worktree is dirty")
    need((manifest.get("artifact"), manifest.get("window"), manifest.get("head"), manifest.get("tree"),
          manifest.get("candidateFree"), manifest.get("sourceCount"), manifest.get("localeCount"), manifest.get("cellCount")) ==
         ("slskdN PR #409 W78 independent primary semantic review", "W78", HEAD, TREE, True, 25, 12, 300),
         "primary manifest pin/coverage")
    need(manifest.get("blindReviewUsed") is False and manifest.get("crossReviewUsed") is False and
         manifest.get("nativeSpeakerSignoff") is False and manifest.get("browserReview") is False,
         "review scope flags")

    input_manifest = readj(INPUT / "manifest.json")
    need(manifest.get("candidateFreeInputManifestSha256") == sha((INPUT / "manifest.json").read_bytes()) and
         manifest.get("candidateFreeInputChecksumListSha256") == sha((INPUT / "PACKET-SHA256SUMS.txt").read_bytes()),
         "candidate-free linkage")
    need(manifest.get("sourceInventorySelectionSha256") == sha((INPUT / "source-inventory-selection.jsonl").read_bytes()) and
         manifest.get("callerContextSha256") == sha((INPUT / "caller-contexts.jsonl").read_bytes()), "source/caller linkage")
    need((ROOT / "main-drift.json").read_bytes() == (INPUT / "main-drift.json").read_bytes(), "main drift snapshot differs from candidate-free input")
    need(readj(ROOT / "live-before.json") == input_manifest["liveAfter"], "primary review did not start at candidate-free live-after attestation")
    drift = readj(ROOT / "main-drift.json")
    need((drift["baseApiSha"], drift["liveMainBeforeSha"], drift["liveMainAfterSha"], drift["localizationOrCatalogChanges"]) ==
         (input_manifest["liveAfter"]["baseRefOid"], input_manifest["liveAfter"]["liveMainSha"],
          input_manifest["liveAfter"]["liveMainSha"], False) and
         drift["liveMainBeforeSha"] == drift["liveMainAfterSha"], "base/main drift")

    cells = rows(INPUT / "source-current-cells.jsonl")
    callers = {row["continuationRank"]: row for row in rows(INPUT / "caller-contexts.jsonl")}
    ledger = rows(ROOT / "primary-review.jsonl")
    corrections = rows(ROOT / "corrections.jsonl")
    holds = rows(ROOT / "holds-hash-only.jsonl")
    expected = {(row["continuationRank"], row["locale"]): row for row in cells}
    actual = {(row["continuationRank"], row["locale"]): row for row in ledger}
    need(len(expected) == len(actual) == 300 and set(expected) == set(actual), "decision coverage/uniqueness")
    need([row["locale"] for row in cells[:12]] == LOCALES, "locale order")
    counts = collections.Counter()
    expected_corrections, expected_holds = [], []
    for key, cell in expected.items():
        rank, locale = key
        row = actual[key]
        disposition = row.get("disposition")
        counts[disposition] += 1
        need(row.get("reviewPass") == "independent-primary" and row.get("head") == HEAD and row.get("tree") == TREE,
             f"decision provenance {rank}/{locale}")
        for field in ("continuationRank", "remainingQueueRank", "sourceId", "sourceSha256", "locale", "catalogPath",
                      "catalogFileSha256", "catalogGitBlob", "currentTargetSha256", "callerContextSha256", "callerRefs"):
            need(row.get(field) == cell.get(field), f"candidate-free binding {field} {rank}/{locale}")
        caller = callers[rank]
        need(row.get("productionCallerCount") == caller["productionCallerCount"], f"caller count {rank}/{locale}")
        source, current = cell["source"], cell["currentTarget"]
        if disposition == "hold":
            need(caller["productionCallerCount"] == 0, f"hold has production caller {rank}/{locale}")
            need(not (FORBIDDEN_HOLD_TEXT_FIELDS & set(row)), f"hold exposes text {rank}/{locale}")
            need(row.get("sourceTextIncluded") is False and row.get("currentTargetTextIncluded") is False,
                 f"hold text flags {rank}/{locale}")
            need(row.get("sourceSha256") == sha(source.encode("utf-8")) and
                 row.get("currentTargetSha256") == sha(current.encode("utf-8")), f"hold hashes {rank}/{locale}")
            need(row.get("holdReasonSha256") == sha(row.get("holdReason", "").encode("utf-8")) and bool(row.get("holdReason")),
                 f"hold reason hash {rank}/{locale}")
            evidence = token_check(source, current)
            expected_evidence = {
                "evidenceSha256": sha(canon(evidence)),
                "placeholderParityCurrent": evidence["placeholderParityCurrent"],
                "markupParityCurrent": evidence["markupParityCurrent"],
                "numericTokensPreservedCurrent": evidence["numericTokensPreservedCurrent"],
                "protectedLiteralsPreservedCurrent": evidence["protectedLiteralsPreservedCurrent"],
            }
            need(row.get("tokenEvidence") == expected_evidence, f"hash-only token evidence {rank}/{locale}")
            need(row.get("callerRefs") == [] and caller["productionCallerCount"] == 0, f"callerless hold refs {rank}/{locale}")
            expected_holds.append(row)
            continue
        need(caller["productionCallerCount"] > 0, f"callerless cell not held {rank}/{locale}")
        for field, value in (("source", source), ("catalogKey", cell["catalogKey"]), ("currentTarget", current)):
            need(row.get(field) == value, f"decision text {field} {rank}/{locale}")
        need(row.get("sourceSha256") == sha(source.encode("utf-8")) and
             row.get("currentTargetSha256") == sha(current.encode("utf-8")), f"source/current hash {rank}/{locale}")
        need(bool(row.get("rationale")) and row.get("confidence") in ("high", "moderate", "low"),
             f"rationale/confidence {rank}/{locale}")
        if disposition == "accept-current":
            need("target" not in row and "proposal" not in row.get("tokenCheck", {}), f"accept contains proposal {rank}/{locale}")
            expected_tokens = token_check(source, current)
        elif disposition == "correct":
            target = row.get("target")
            need(isinstance(target, str) and bool(target) and row.get("targetSha256") == sha(target.encode("utf-8")),
                 f"proposal/hash {rank}/{locale}")
            expected_tokens = token_check(source, current, target)
            expected_corrections.append(row)
        else:
            fail(f"unknown disposition {rank}/{locale}")
        need(row.get("tokenCheck") == expected_tokens, f"token evidence {rank}/{locale}")
    need(counts == collections.Counter({"accept-current": 232, "correct": 56, "hold": 12}), f"disposition counts {counts}")
    callerless = {rank for rank, data in callers.items() if data["productionCallerCount"] == 0}
    need(callerless == {829}, f"callerless source inventory {callerless}")
    need(corrections == expected_corrections and holds == expected_holds, "proposal/hold extracts differ from ledger")
    need(all(not (FORBIDDEN_HOLD_TEXT_FIELDS & set(row)) for row in holds), "hold extract exposes text")
    summary = readj(ROOT / "summary.json")
    need(summary.get("dispositions") == {"accept-current": 232, "correct": 56, "hold": 12} and
         summary.get("proposedTargetCount") == len(corrections) == 56 and summary.get("holds") == len(holds) == 12 and
         summary.get("candidateFreeInputManifestSha256") == sha((INPUT / "manifest.json").read_bytes()), "summary linkage/counts")
    proposal_summary = {(row["continuationRank"], row["locale"]): (row["target"], row["targetSha256"])
                        for row in summary.get("proposals", [])}
    need(proposal_summary == {(row["continuationRank"], row["locale"]): (row["target"], row["targetSha256"])
                              for row in corrections}, "summary proposal targets")
    held_summary = {(row["continuationRank"], row["locale"]): (row["sourceSha256"], row["currentTargetSha256"])
                    for row in summary.get("heldCells", [])}
    need(held_summary == {(row["continuationRank"], row["locale"]): (row["sourceSha256"], row["currentTargetSha256"])
                          for row in holds}, "summary hold hashes")
    need(readj(ROOT / "source-rewrite-recommendations.json") == {"schemaVersion": 1, "recommendations": []},
         "source rewrite recommendations")

    before, after = readj(ROOT / "live-before.json"), readj(ROOT / "live-after.json")
    for live in (before, after):
        need((live.get("repository"), live.get("pullRequest"), live.get("state"), live.get("draft"), live.get("merged")) ==
             ("snapetech-org/slskdN", 409, "OPEN", True, False), "PR state")
        for field, value in (("headRefOid", HEAD), ("branchRefOid", HEAD), ("pullRefOid", HEAD),
                             ("headRefName", BRANCH), ("baseRefName", "main"),
                             ("baseRefOid", input_manifest["liveAfter"]["baseRefOid"]),
                             ("liveMainSha", input_manifest["liveAfter"]["liveMainSha"]),
                             ("liveMainTree", input_manifest["liveAfter"]["liveMainTree"])):
            need(live.get(field) == value, "live ref " + field)
    stable = set(before) | set(after)
    need(all(before.get(key) == after.get(key) for key in stable if key != "attestedUtc"), "live refs changed during review")
    remote_text = subprocess.check_output(["git", "ls-remote", "https://github.com/snapetech-org/slskdN.git",
                                            f"refs/heads/{BRANCH}", "refs/pull/409/head"], text=True)
    remote = {line.split()[1]: line.split()[0] for line in remote_text.splitlines() if line.strip()}
    need(remote.get(f"refs/heads/{BRANCH}") == HEAD and remote.get("refs/pull/409/head") == HEAD, "current GitHub refs")

    print(json.dumps({
        "result": "PASS", "head": HEAD, "tree": TREE, "window": "W78",
        "sourceCount": 25, "localeCount": 12, "cellCount": len(ledger),
        "acceptCurrent": counts["accept-current"], "correct": counts["correct"],
        "callerlessHashOnlyHolds": counts["hold"], "callerlessSources": len(callerless),
        "callerlessCells": len(holds), "candidateFreeVerifier": "PASS",
        "PRRefs": "OPEN/DRAFT at exact branch and pull head", "baseSha": before["baseRefOid"],
        "liveMainSha": before["liveMainSha"], "checksums": checksum_count,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
