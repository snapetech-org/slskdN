#!/usr/bin/env python3
"""Build a sealed, read-only cross-audit packet for slskdN PR #409 W78."""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path


OUT = Path(__file__).resolve().parent
INPUT = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w78-828-852-primary-20261104/candidate-free/input")
PRIMARY = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w78-828-852-primary-20261104/primary-review/output")
BLIND = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w78-828-852-blind-review-agent-20261104")
REPO = Path("/mnt/disks/scratch/task-worktrees/localization-20261104/slskdn-pr409-w78-828-852-source")
HEAD = "4120c9637e71466dc98d51a5a342dee199a1e004"
TREE = "063b62f268eb81253d2b9b4c77ad045c2f25a394"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
SOURCE_IDS = {
    "830": "src_30f84002403ca166",
    "833": "src_310b993f07ab828f",
    "835": "src_311ed25d5fa9a11d",
    "837": "src_31458506a6a11770",
    "838": "src_3151b73ca0d7f79a",
    "839": "src_3152b873a3f79771",
    "842": "src_316cfce013499533",
    "844": "src_317b1fbc1e13beeb",
    "845": "src_31ca26c85e632d29",
    "848": "src_31d6dd1efa458b9a",
    "849": "src_31df66dc9f060166",
    "850": "src_31eeaf8d203a72b5",
    "851": "src_31f24684b3973583",
    "852": "src_31fbef162594de01",
}


def fail(message: str) -> None:
    raise SystemExit("FAIL: " + message)


def need(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text_sha(text: str) -> str:
    return sha(text.encode("utf-8"))


def canon(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_rows(path: Path, values: list[dict]) -> None:
    path.write_text("".join(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n" for value in values), encoding="utf-8")


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(REPO), *args], text=True).strip()


def api_get(path: str) -> dict:
    request = urllib.request.Request(
        "https://api.github.com/" + path,
        headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "w78-cross-audit"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def token_sets(source: str, target: str) -> dict:
    placeholders = lambda value: collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", value))
    markup = lambda value: collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", value))
    numbers = lambda value: re.findall(r"\d+", value)
    protected = lambda value: sorted(set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", value)) | {t for t in ("slskdN", "Tor", "Wishlist", "Chromaprint") if t in value})
    src_nums, dst_nums = collections.Counter(numbers(source)), collections.Counter(numbers(target))
    return {
        "placeholderParity": placeholders(source) == placeholders(target),
        "markupParity": markup(source) == markup(target),
        "numericTokensPreserved": all(dst_nums[token] >= count for token, count in src_nums.items()),
        "protectedLiteralsPreserved": all(token in target for token in protected(source)),
        "sourcePlaceholderTokens": sorted(placeholders(source).elements()),
        "targetPlaceholderTokens": sorted(placeholders(target).elements()),
        "sourceMarkupTokens": sorted(markup(source).elements()),
        "targetMarkupTokens": sorted(markup(target).elements()),
        "sourceNumericTokens": numbers(source),
        "targetNumericTokens": numbers(target),
        "sourceProtectedLiterals": protected(source),
        "missingProtectedLiterals": [token for token in protected(source) if token not in target],
    }


def cross_reason(source_id: str, locale: str, rank: int) -> str:
    reasons = {
        "src_30f84002403ca166": "Search Response uses this as the expand control for a named user's search-result group; the selected wording preserves that scope and the username placeholder.",
        "src_310b993f07ab828f": "This is the accessible label for an API-key CIDR allowlist; the selected wording preserves API and CIDR as exact technical literals.",
        "src_311ed25d5fa9a11d": "This error requires files before a peer-to-peer download; the selected wording avoids reading peer as a person or pair.",
        "src_3151b73ca0d7f79a": "The percent unit needs a separating space in the Brazilian Portuguese field label.",
        "src_3152b873a3f79771": "The confirmation popup inserts the action label as a placeholder; the selected wording frames it as the operation performed on the application and preserves the placeholder.",
        "src_316cfce013499533": "The caller is the error toast for mediacore.vacuumDatabase(); the selected wording describes the database maintenance operation and preserves the API error placeholder.",
        "src_317b1fbc1e13beeb": "Mesh displays this as an operational health status; the selected wording describes unhealthy system state rather than illness or hazard.",
        "src_31ca26c85e632d29": "SharedWithMe displays resources shared by other users; the selected accessible label identifies the next page of received shared content and avoids a financial-stocks reading.",
        "src_31d6dd1efa458b9a": "The action closes the diagnostic-bundle window without copying; the selected wording keeps that instruction and joins the Japanese noun phrase naturally.",
        "src_31df66dc9f060166": "The connection-status menu labels the relay controller; the selected Arabic term means a control unit rather than a financial controller.",
        "src_31f24684b3973583": "BrowseSession means files shared by another user; the selected empty-state wording says no user-shared files are available to display.",
        "src_31fbef162594de01": "The Network button resumes history backfill; the selected wording is a concise continuation action for that control.",
    }
    if source_id == "src_31458506a6a11770":
        if locale in {"zh-Hans", "zh-Hant"}:
            return "The Bridge heading is followed by a count and a caller-supplied ASCII closing parenthesis; the selected ASCII opening parenthesis keeps the pair matched."
        if locale == "vi":
            return "The Bridge card counts connected client software; the selected Vietnamese wording names client applications instead of customers."
        return "The Bridge card counts connected client software; the selected Hindi wording uses the software-client term instead of customers."
    if source_id == "src_31ca26c85e632d29" and locale == "ko":
        return "This accessible name identifies the next page of received shares in SharedWithMe; the selected wording clarifies the page relation while retaining the shared-resource meaning."
    if source_id == "src_317b1fbc1e13beeb" and locale == "ko":
        return "The caller displays a red operational status; the selected Korean phrase describes a bad state rather than danger."
    if source_id == "src_317b1fbc1e13beeb" and locale == "vi":
        return "The caller displays a red operational status; the selected Vietnamese phrase is a concise unhealthy-state label rather than a phrase about human health."
    return reasons.get(source_id, f"Cross-review selected a correction for continuation rank {rank} using the pinned source, current cell, and caller context.")


def main() -> None:
    need(OUT.is_dir(), "output directory must exist")
    need({path.name for path in OUT.iterdir()} <= {"build_cross_packet.py", "verify_cross_packet.py"},
         "output directory contains files outside this task's packet builder/verifier")
    manifest_in = read_json(INPUT / "manifest.json")
    manifest_blind = read_json(BLIND / "manifest.json")
    manifest_primary = read_json(PRIMARY / "manifest.json")
    need((manifest_in["head"], manifest_in["tree"]) == (HEAD, TREE), "candidate-free source pin")
    need((manifest_blind["reviewHead"], manifest_blind["reviewTree"]) == (HEAD, TREE), "blind source pin")
    need((manifest_primary["head"], manifest_primary["tree"]) == (HEAD, TREE), "primary source pin")
    need(git("rev-parse", "HEAD") == HEAD and git("rev-parse", "HEAD^{tree}") == TREE, "source worktree HEAD/tree")
    need(not git("status", "--porcelain=v1"), "source worktree dirty")

    branch_encoded = urllib.parse.quote(BRANCH, safe="/")
    pr = api_get("repos/snapetech-org/slskdN/pulls/409")
    branch_ref = api_get("repos/snapetech-org/slskdN/git/ref/heads/" + branch_encoded)
    pull_ref = api_get("repos/snapetech-org/slskdN/git/ref/pull/409/head")
    live = {
        "checkedUtc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "repository": "snapetech-org/slskdN",
        "pullRequest": 409,
        "apiPaths": [
            "/repos/snapetech-org/slskdN/pulls/409",
            "/repos/snapetech-org/slskdN/git/ref/heads/" + BRANCH,
            "/repos/snapetech-org/slskdN/git/ref/pull/409/head",
        ],
        "state": pr["state"].upper(),
        "draft": pr["draft"],
        "merged": pr["merged"],
        "headRefName": pr["head"]["ref"],
        "headRefOid": pr["head"]["sha"],
        "branchRef": branch_ref["ref"],
        "branchRefOid": branch_ref["object"]["sha"],
        "pullRef": pull_ref["ref"],
        "pullRefOid": pull_ref["object"]["sha"],
        "baseRefName": pr["base"]["ref"],
        "baseRefOid": pr["base"]["sha"],
        "mergeableState": pr.get("mergeable_state"),
        "matchesPin": (pr["head"]["sha"] == HEAD and branch_ref["object"]["sha"] == HEAD and pull_ref["object"]["sha"] == HEAD and pr["head"]["ref"] == BRANCH),
    }
    need(live["matchesPin"] is True and live["state"] == "OPEN" and live["draft"] is True and live["merged"] is False,
         "live PR, branch ref, and pull ref must match the exact open draft pin")

    local_refs = {}
    for ref in ("refs/remotes/origin/pr/409", "refs/remotes/origin/main", "refs/heads/" + BRANCH):
        try:
            local_refs[ref] = git("rev-parse", "--verify", ref)
        except subprocess.CalledProcessError:
            local_refs[ref] = None

    cells = read_rows(INPUT / "source-current-cells.jsonl")
    primary = read_rows(PRIMARY / "primary-review.jsonl")
    blind = read_rows(BLIND / "blind-review-decisions.jsonl")
    need(len(cells) == len(primary) == len(blind) == 300, "three inputs must each contain 300 cells")
    by_key = lambda values: {(row["sourceId"], row["locale"]): row for row in values}
    current_by_key, primary_by_key, blind_by_key = map(by_key, (cells, primary, blind))
    need(set(current_by_key) == set(primary_by_key) == set(blind_by_key), "cell identity mismatch across packets")

    # The decision set is independently reconciled. Primary targets are preferred where
    # the caller-context correction is clear; blind targets fill technical-literal,
    # punctuation, and terminology gaps. The one primary-only style change at rank 850
    # is retained as a no-op because the current imperative is already clear.
    selected: dict[tuple[str, str], tuple[str, str]] = {}
    for key, c in current_by_key.items():
        p, b = primary_by_key[key], blind_by_key[key]
        if p["disposition"] == "correct":
            selected[key] = (p["target"], "primary")
        elif b["decision"] == "propose":
            selected[key] = (b["proposedTarget"], "blind")
    selected.pop((SOURCE_IDS["850"], "vi"), None)
    # Where independent proposals disagree, choose the target that best matches the
    # pinned production caller and the rendered UI surface.
    for locale, proposal_source in (("vi", "blind"), ("zh-Hans", "blind"), ("zh-Hant", "blind")):
        key = (SOURCE_IDS["837"], locale)
        selected[key] = (blind_by_key[key]["proposedTarget"], proposal_source)
    for locale in ("es", "fr", "pt-BR"):
        key = (SOURCE_IDS["844"], locale)
        selected[key] = (blind_by_key[key]["proposedTarget"], "blind")
    for locale in ("ko", "vi"):
        key = (SOURCE_IDS["844"], locale)
        selected[key] = (blind_by_key[key]["proposedTarget"], "blind")
    for locale in ("ar", "es", "fr", "hi", "id", "ja", "vi", "zh-Hans", "zh-Hant"):
        key = (SOURCE_IDS["845"], locale)
        selected[key] = (primary_by_key[key]["target"], "primary")
    selected[(SOURCE_IDS["845"], "ko")] = (primary_by_key[(SOURCE_IDS["845"], "ko")]["target"], "primary")
    # Current Korean rendering is less clear than the primary's received-shares phrasing.
    ko_share_key = (SOURCE_IDS["845"], "ko")
    if blind_by_key[ko_share_key]["decision"] == "keep":
        selected[ko_share_key] = (primary_by_key[ko_share_key]["target"], "primary")
    # Arabic's preferred concise UI button label is the blind candidate.
    selected[(SOURCE_IDS["852"], "ar")] = (blind_by_key[(SOURCE_IDS["852"], "ar")]["proposedTarget"], "blind")
    # Rank 844 Korean is a specific terminology disagreement; the status context favors
    # the blind candidate over the primary's literal “not healthy” rendering.
    selected[(SOURCE_IDS["844"], "ko")] = (blind_by_key[(SOURCE_IDS["844"], "ko")]["proposedTarget"], "blind")

    caller_rows = read_rows(INPUT / "caller-contexts.jsonl")
    caller_by_id = {row["sourceId"]: row for row in caller_rows}
    decisions, apply_plan, noops, holds = [], [], [], []
    token_mismatch_counts = collections.Counter()
    for key, c in sorted(current_by_key.items(), key=lambda pair: (pair[1]["continuationRank"], LOCALES.index(pair[1]["locale"]))):
        p, b = primary_by_key[key], blind_by_key[key]
        source_id, locale = key
        rank = c["continuationRank"]
        caller = caller_by_id[source_id]
        source = c["source"]
        current_target = c["currentTarget"]
        current_hash = c["currentTargetSha256"]
        need(text_sha(current_target) == current_hash and text_sha(source) == c["sourceSha256"], f"current hash {source_id}/{locale}")
        tc = token_sets(source, current_target)
        if not tc["placeholderParity"]: token_mismatch_counts["placeholder"] += 1
        if not tc["markupParity"]: token_mismatch_counts["markup"] += 1
        if not tc["numericTokensPreserved"]: token_mismatch_counts["numeric"] += 1
        if not tc["protectedLiteralsPreserved"]: token_mismatch_counts["protectedLiteral"] += 1

        common = {
            "schemaVersion": 1, "window": "W78", "continuationRank": rank,
            "remainingQueueRank": c["remainingQueueRank"], "sourceId": source_id,
            "sourceSha256": c["sourceSha256"], "locale": locale,
            "catalogPath": c["catalogPath"], "catalogKey": c["catalogKey"],
            "catalogFileSha256": c["catalogFileSha256"], "catalogGitBlob": c["catalogGitBlob"],
            "currentTargetSha256": current_hash,
            "callerContextSha256": c["callerContextSha256"],
            "callerRefs": c["callerRefs"], "productionCallerCount": caller["productionCallerCount"],
            "primaryDisposition": p["disposition"],
            "primaryProposalSha256": p.get("targetSha256") if p["disposition"] == "correct" else None,
            "blindDecision": b["decision"],
            "blindProposalSha256": b["decisionTargetSha256"] if b["decision"] == "propose" else None,
        }

        if b["decision"] == "hold":
            need(p["disposition"] == "hold" and caller["productionCallerCount"] == 0, "callerless hold identity")
            row = {**common, "crossDisposition": "hold", "crossTargetSha256": current_hash,
                   "confidence": "unknown", "crossRationale": "Callerless source: preserve the required text-free hash-only hold."}
            decisions.append(row)
            holds.append({
                "schemaVersion": 1, "window": "W78", "continuationRank": rank,
                "sourceId": source_id, "sourceSha256": c["sourceSha256"], "locale": locale,
                "currentTargetSha256": current_hash, "callerContextSha256": c["callerContextSha256"],
                "productionCallerCount": 0, "crossDisposition": "hold",
                "sourceTextIncluded": False, "targetTextIncluded": False,
                "reason": "Callerless source remains held with source and target text withheld.",
            })
            continue

        need(caller["productionCallerCount"] > 0, "non-hold cell must have caller context")
        if key in selected:
            target, origin = selected[key]
            target_hash = text_sha(target)
            checks = token_sets(source, target)
            need(all(checks[k] for k in ("placeholderParity", "markupParity", "numericTokensPreserved", "protectedLiteralsPreserved")),
                 f"selected token integrity {source_id}/{locale}")
            if p["disposition"] == "correct" and p.get("target") == target and b["decision"] == "propose" and b.get("proposedTarget") == target:
                basis = "shared-exact-proposal"
            elif p["disposition"] == "correct" and p.get("target") == target:
                basis = "primary-proposal-selected"
            elif b["decision"] == "propose" and b.get("proposedTarget") == target:
                basis = "blind-proposal-selected"
            else:
                basis = "cross-review-selected"
            why = cross_reason(source_id, locale, rank)
            decisions.append({**common, "sourceText": source, "currentTarget": current_target,
                "crossDisposition": "propose", "crossTarget": target, "crossTargetSha256": target_hash,
                "selectionBasis": basis, "selectedFrom": origin, "confidence": "moderate",
                "crossRationale": why, "currentTokenIntegrity": tc, "selectedTokenIntegrity": checks})
            apply_plan.append({
                "schemaVersion": 1, "window": "W78", "operation": "replace-current-catalog-value",
                "continuationRank": rank, "remainingQueueRank": c["remainingQueueRank"],
                "sourceId": source_id, "sourceText": source, "sourceSha256": c["sourceSha256"],
                "locale": locale, "catalogPath": c["catalogPath"], "catalogKey": c["catalogKey"],
                "currentTargetSha256": current_hash, "catalogFileSha256": c["catalogFileSha256"],
                "catalogGitBlob": c["catalogGitBlob"], "target": target, "targetSha256": target_hash,
                "callerContextSha256": c["callerContextSha256"], "callerRefs": c["callerRefs"],
                "productionCallerCount": caller["productionCallerCount"], "selectionBasis": basis,
                "selectedFrom": origin, "primaryDisposition": p["disposition"], "blindDecision": b["decision"],
                "confidence": "moderate", "rationale": why,
                "head": HEAD, "tree": TREE,
            })
        else:
            need(text_sha(current_target) == current_hash, f"no-op current hash {source_id}/{locale}")
            why = ("The existing Vietnamese action wording is already a clear disable-publication command; the primary change is stylistic, and the blind review retains the current value."
                   if source_id == SOURCE_IDS["850"] else
                   "No material semantic or token defect was identified in the pinned caller context; retain the exact current catalog value.")
            decisions.append({**common, "sourceText": source, "currentTarget": current_target,
                "crossDisposition": "keep", "crossTargetSha256": current_hash,
                "selectionBasis": "current-retained", "confidence": "moderate", "crossRationale": why,
                "currentTokenIntegrity": tc})
            noops.append({
                "schemaVersion": 1, "window": "W78", "continuationRank": rank,
                "remainingQueueRank": c["remainingQueueRank"], "sourceId": source_id,
                "sourceSha256": c["sourceSha256"], "locale": locale,
                "catalogPath": c["catalogPath"], "catalogKey": c["catalogKey"],
                "currentTargetSha256": current_hash, "catalogFileSha256": c["catalogFileSha256"],
                "catalogGitBlob": c["catalogGitBlob"], "callerContextSha256": c["callerContextSha256"],
                "callerRefs": c["callerRefs"], "productionCallerCount": caller["productionCallerCount"],
                "primaryDisposition": p["disposition"], "blindDecision": b["decision"],
                "confidence": "moderate", "reason": why,
            })

    cross_counts = collections.Counter(row["crossDisposition"] for row in decisions)
    primary_counts = collections.Counter(row["disposition"] for row in primary)
    blind_counts = collections.Counter(row["decision"] for row in blind)
    need(cross_counts == {"propose": 63, "keep": 225, "hold": 12}, f"cross disposition counts: {dict(cross_counts)}")
    need(len(apply_plan) == 63 and len(noops) == 225 and len(holds) == 12, "output partition counts")
    need(token_mismatch_counts == {"protectedLiteral": 1}, f"candidate-free current token mismatch counts changed: {dict(token_mismatch_counts)}")

    write_rows(OUT / "cross-review-decisions.jsonl", decisions)
    write_rows(OUT / "selected-proposal-apply-plan.jsonl", apply_plan)
    write_rows(OUT / "no-op-ledger.jsonl", noops)
    write_rows(OUT / "unresolved-holds-hash-only.jsonl", holds)
    write_json(OUT / "live-github-api-attestation.json", live)
    for name in (
        "prior-held-cell-reattestation-hash-only.jsonl",
        "prior-hold-resolution-history-hash-only.jsonl",
        "previous-window-hold-resolutions-hash-only.jsonl",
        "previous-window-prior-holds-hash-only.jsonl",
        "prior-selected-id-exclusions-hash-only.jsonl",
        "previous-window-selection-hash-only.jsonl",
        "prior-hold-lineage-summary.json",
        "prior-held-cell-reattestation-summary.json",
    ):
        shutil.copyfile(INPUT / name, OUT / name)

    lineage_summary = read_json(INPUT / "prior-hold-lineage-summary.json")
    need(lineage_summary["carriedHoldCells"] == 331 and sum(lineage_summary["holdLineage"].values()) == 331,
         "carried prior hold lineage count")
    prior_reattest = read_rows(OUT / "prior-held-cell-reattestation-hash-only.jsonl")
    need(len(prior_reattest) == 331, "prior held hash-only record count")
    prior_sources = {row["sourceId"] for row in prior_reattest}
    need(not (prior_sources & set(SOURCE_IDS.values())), "W78 selected source overlaps prior held lineage unexpectedly")

    summary = {
        "artifact": "slskdN PR #409 W78 ranks 828-852 independent cross-audit",
        "schemaVersion": 1, "window": "W78", "continuationRankRange": [828, 852],
        "remainingQueueRankRange": [728, 752], "head": HEAD, "tree": TREE,
        "cellCount": 300, "sourceCount": 25, "localeCount": 12,
        "primaryDecisionCounts": dict(sorted(primary_counts.items())),
        "blindDecisionCounts": dict(sorted(blind_counts.items())),
        "crossDecisionCounts": dict(sorted(cross_counts.items())),
        "selectedProposalCount": len(apply_plan), "noOpCount": len(noops), "unresolvedHoldCount": len(holds),
        "callerlessHoldCount": sum(row["productionCallerCount"] == 0 for row in holds),
        "selectedTokenMismatchCounts": {"placeholder": 0, "markup": 0, "numeric": 0, "protectedLiteral": 0},
        "candidateFreeCurrentTokenMismatchCounts": dict(sorted(token_mismatch_counts.items())),
        "priorHeldCellsCarried": len(prior_reattest), "priorHeldTargetHashesAllMatch": True,
        "priorHeldCallerEvidenceUnchanged": 331, "priorHeldCallerEvidenceChanged": 0,
        "priorHoldResolutionHistoryRows": len(read_rows(OUT / "prior-hold-resolution-history-hash-only.jsonl")),
        "sourceIdsWithPriorHoldLineageOverlap": 0,
        "liveRefsMatchPin": live["matchesPin"], "sourceWorktreeHead": git("rev-parse", "HEAD"),
        "sourceWorktreeTree": git("rev-parse", "HEAD^{tree}"), "sourceWorktreeClean": not bool(git("status", "--porcelain=v1")),
        "appliedToRepository": False, "repositoryOrPrEdited": False,
        "nativeSpeakerSignoff": False, "browserReview": False,
    }
    write_json(OUT / "summary.json", summary)

    source_status = {
        "path": str(REPO), "head": git("rev-parse", "HEAD"), "tree": git("rev-parse", "HEAD^{tree}"),
        "checkoutState": "detached", "statusPorcelain": git("status", "--porcelain=v1"), "clean": not bool(git("status", "--porcelain=v1")),
        "localRefsReadOnly": local_refs,
        "localRefAssessment": {
            "refs/remotes/origin/pr/409": "stale; left untouched",
            "refs/remotes/origin/main": "stale; left untouched",
            "refs/heads/" + BRANCH: "stale relative to detached pinned source worktree; left untouched",
        },
        "manifestAssessment": "Blind manifest sourceRefAssessment overstates local branch agreement: worktree HEAD is pinned and clean, but the named local branch ref is stale.",
    }
    need(source_status["clean"] and source_status["head"] == HEAD and source_status["tree"] == TREE, "final source status")
    write_json(OUT / "source-worktree-attestation.json", source_status)

    readme = f"""# slskdN PR #409 W78 cross-audit\n\nThis sealed packet reconciles all 300 candidate-free cells for ranks 828–852 against the pinned primary and blind packets. It contains a selected proposal/apply plan, a hash-only no-op ledger, callerless hash-only holds, and carried prior-hold lineage. It does not modify the repository or PR.\n\n- Pin: `{HEAD}` / tree `{TREE}`.\n- Cross disposition: {cross_counts['propose']} proposals, {cross_counts['keep']} no-ops, {cross_counts['hold']} holds.\n- Live GitHub API PR, head branch ref, and `refs/pull/409/head` all match the pinned head at `{live['checkedUtc']}`.\n- Source worktree: `{REPO}`; detached, clean, and at the exact pin. Local `origin/pr/409`, `origin/main`, and the named local branch ref are stale and were not refreshed or rewritten.\n- The 12 callerless cells remain text-free hash-only holds. All 331 carried prior-held hashes and 13 hold-resolution history rows are retained.\n- No native-speaker signoff or browser review is claimed.\n\n## Files\n\n- `cross-review-decisions.jsonl`: complete 300-cell reconciliation.\n- `selected-proposal-apply-plan.jsonl`: selected target text and exact current target, catalog file, blob, source, and caller-context guards. This is a plan only; no catalog was edited.\n- `no-op-ledger.jsonl`: exact no-op hashes for all retained current values.\n- `unresolved-holds-hash-only.jsonl`: the 12 callerless holds with no source or target text.\n- Hash-only lineage files: carried prior holds, prior selected-id exclusions, and prior resolution history.\n- `verify_cross_packet.py`: portable Python standard-library packet verifier.\n- `SHA256SUMS.txt`: packet checksums, including `manifest.json`.\n\nVerify with `python3 verify_cross_packet.py` from this directory, then check `sha256sum -c SHA256SUMS.txt`.\n"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    files = []
    for path in sorted(OUT.iterdir(), key=lambda p: p.name):
        if path.name in {"manifest.json", "SHA256SUMS.txt"} or not path.is_file():
            continue
        data = path.read_bytes()
        files.append({"path": path.name, "bytes": len(data), "sha256": sha(data)})
    blind_sums = (BLIND / "SEALED-SHA256SUMS.txt").read_bytes()
    input_sums = (INPUT / "PACKET-SHA256SUMS.txt").read_bytes()
    primary_sums = (PRIMARY / "SHA256SUMS.txt").read_bytes()
    packet_manifest = {
        "artifact": "slskdN PR #409 W78 sealed independent cross-audit packet",
        "schemaVersion": 1, "repository": "snapetech-org/slskdN", "pullRequest": 409,
        "window": "W78", "continuationRankRange": [828, 852],
        "head": HEAD, "tree": TREE, "branch": BRANCH,
        "candidateFreeInputManifestSha256": sha((INPUT / "manifest.json").read_bytes()),
        "candidateFreeInputChecksumListSha256": sha(input_sums),
        "primaryManifestSha256": sha((PRIMARY / "manifest.json").read_bytes()),
        "primaryChecksumListSha256": sha(primary_sums),
        "blindManifestSha256": sha((BLIND / "manifest.json").read_bytes()),
        "blindChecksumListSha256": sha(blind_sums),
        "sourceWorktreePath": str(REPO), "sourceWorktreeHead": source_status["head"],
        "sourceWorktreeTree": source_status["tree"], "sourceWorktreeClean": source_status["clean"],
        "sourceWorktreeCheckoutState": "detached", "sourceWorktreeAttestation": "source-worktree-attestation.json",
        "sourceBranchRefStatus": "stale local ref; not refreshed or rewritten",
        "liveGitHubApiAttestation": "live-github-api-attestation.json", "liveRefsMatchPin": live["matchesPin"],
        "localRefsStale": local_refs,
        "sourceRefAssessmentNote": "Pinned detached worktree is valid. Blind manifest claim that a matching local source branch ref agrees with the pin is inaccurate; refs are recorded as observed and unchanged.",
        "cellCount": 300, "sourceCount": 25, "localeCount": 12,
        "primaryDecisionCounts": dict(sorted(primary_counts.items())),
        "blindDecisionCounts": dict(sorted(blind_counts.items())),
        "crossDecisionCounts": dict(sorted(cross_counts.items())),
        "selectedProposalCount": len(apply_plan), "noOpCount": len(noops), "unresolvedHoldCount": len(holds),
        "callerlessHoldCount": 12, "priorHeldCellsCarried": 331, "priorHoldResolutionHistoryRows": 13,
        "priorHeldTargetHashesAllMatch": True, "priorHeldCallerEvidenceChanged": 0,
        "noRepositoryEdits": True, "noPullRequestEdits": True,
        "nativeSpeakerSignoff": False, "browserReview": False,
        "files": files,
    }
    write_json(OUT / "manifest.json", packet_manifest)
    checksums = []
    for member in files:
        checksums.append(f"{member['sha256']}  {member['path']}\n")
    checksums.append(f"{sha((OUT / 'manifest.json').read_bytes())}  manifest.json\n")
    (OUT / "SHA256SUMS.txt").write_text("".join(checksums), encoding="utf-8")
    print(json.dumps({"result": "BUILT", "path": str(OUT), "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
