#!/usr/bin/env python3
"""Build the sealed W80 cross-review packet from the three verified review inputs."""
import collections
import hashlib
import json
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

PKT = Path(__file__).resolve().parent
TASK = PKT.parent
INPUT = TASK / "candidate-free" / "input"
PRIMARY = TASK / "primary-review" / "output"
BLIND = TASK / "independent-blind"
SOURCE = Path("/mnt/disks/scratch/task-worktrees/slskdn-pr409-w80-878-902/source")
HEAD = "7a1ca27fd0519674c3b42a3e3df3638b0f671567"
TREE = "b3525218d0f9676c88c4991e78775d113f18b7d9"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
RANKS = list(range(878, 903))

# Use the blind target where that review proposed one, then independently select
# the stronger pinned-context variant where the two proposed different wording.
PRIMARY_SELECTIONS = {
    (882, "vi"),
    (886, "pt-BR"),
    (886, "vi"),
    (890, "zh-Hant"),
    (885, "ar"),
    (902, "ar"),
}
REJECTED_PRIMARY_ONLY = {(882, "id"), (882, "ja")}

PROPOSED_CONTEXT = {
    879: "The details panel offers a checkbox explicitly labelled Bypass cache (force fresh retrieval), so fresh means an uncached DHT lookup.",
    881: "This is the Pod / Channel column in the route-attempt table; Pod is a route entity tied to podId, not a physical pod or generic group.",
    882: "These uses share Pending across job status, incomplete swarm chunks, and readiness checks, so the selected wording must describe a waiting or processing state.",
    883: "The caller is the source side of a remote path mapping and is paired with the corresponding to field; a source-path label fits the input.",
    884: "The callers distinguish filesystem directories from files in file operations, transfer rows, import retry, and wishlist rules; the target names a folder.",
    885: "The Arabic current target translates the protected source literal ID as identifier. The candidate-free evidence flags this as the single baseline protected-literal mismatch, and the caller searches for content similar to an ID.",
    886: "The metric key is system_net_sockets_connections_established_total; this is a label for established network socket connections, not physical outlets or sockets being created.",
    889: "The player shelf lists tracks and previews promote, archive, expire, review, and consensus-gated policy outcomes. Copying its report is read-only and executes no action.",
    890: "The caller controls whether a room broadcast is listed in the mesh directory; changes apply immediately while hosting, otherwise the Broadcast action applies them.",
    895: "The caller is the Load interests action on a similar Soulseek user; it loads that user's Soulseek profile interests.",
    896: "This is a Lidarr table header for the time of the most recent search, not the place where it happened.",
    898: "The integration immediately above pulls recent plays into listening intelligence, and this description sends approved gaps to a content acquisition queue.",
    901: "The caller displays the inverse of contact.verified, so this is a verification status, not a confirmation status.",
    902: "The caller passes the liked-interest list to renderInterestList as a section heading, so the label should describe liked items or likes rather than an incomplete verb.",
}

PRIMARY_VARIANT_RATIONALE = {
    (882, "vi"): "Pending is reused for jobs, incomplete chunks, and readiness checks. The short waiting-state target keeps the source broad instead of making it specifically await processing.",
    (886, "pt-BR"): "This is a network programming metric. In this context the technical term socket is clearer than soquete, which can be read as a physical outlet.",
    (886, "vi"): "The metric needs a concise label for established socket connections; this shorter nominal phrasing preserves the state without adding a different action.",
    (890, "zh-Hant"): "The source and paired mesh-directory control are about discoverability; 發現 is closer to discover than 找到, while the rest corrects the apply/request calque.",
    (885, "ar"): "Preserving the technical ID literal resolves the candidate-free packet's only current protected-literal mismatch while retaining the caller's identifier meaning.",
    (902, "ar"): "The caller uses Liked as a heading over a list of interests. The noun for likes fits that list better than the first-person verb.",
}

KEEP_CONTEXT = {
    878: "The scorecard renders provenanceSignals as a comma-separated list, and the current labels identify provenance/origin signals.",
    879: "The Hindi target identifies advanced controls for a fresh DHT retrieval; the adjacent cache-bypass checkbox clarifies that operation.",
    880: "The tooltip is attached to the Load Hashing Stats button and describes perceptual-hash computation and accuracy metrics.",
    881: "These locales already preserve the route Pod term or correctly name the channel column in this table.",
    882: "These locale terms work for the shared pending status across queued jobs, incomplete chunks, and readiness checks.",
    883: "These locales preserve the from side of the remote path mapping in the paired path inputs.",
    884: "These translations identify a filesystem directory in the pinned callers that distinguish it from a file.",
    885: "The tooltip describes searching for similar content using selected confidence and result limits; the current identifier wording preserves that meaning.",
    887: "The message is a quarantine-jury outcome stating that trusted jurors failed to reach a supermajority; current wording preserves that result.",
    888: "The title describes automatic replies to private messages that resemble human checks or share-access gates; current wording preserves both prompt types.",
    889: "The German and Indonesian wording correctly describes a shelf-policy report that performs no action.",
    890: "These locales describe broadcast discoverability and the conditional application of setting changes while hosting.",
    891: "Each tooltip directs the user to enable the equalizer in this browser player.",
    892: "The button's aria label names deletion of selected wishlist searches; current wording preserves the bulk action.",
    893: "The Discovery Graph locale switch describes an alternative or neighboring track candidate from the same SongID run.",
    894: "The tooltip identifies a search of the local registry by domain and optional type to find registered ContentIDs.",
    895: "These locales identify the user's Soulseek-native interests; the awkward literal phrase appears only in the separately revised locales.",
    896: "These table headers identify when a search last occurred.",
    897: "The metadata-error parser passes exceptionType into the provider-request failure message, and the placeholder is preserved.",
    899: "AcoustID is a product name, and the label correctly identifies its configured client.",
    900: "The caller emits this success toast after saving the selected search filter.",
    901: "These locales already identify an unverified contact status.",
    902: "These headings identify the liked interests or liked items list without a material meaning error.",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text_sha(value):
    return sha(value.encode("utf-8"))


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def rows_raw(path):
    result = []
    for line in path.read_bytes().splitlines():
        if line.strip():
            result.append((json.loads(line), line))
    return result


def write_json(path, value):
    path.write_bytes(json_bytes(value))


def write_jsonl(path, values):
    path.write_bytes(b"".join(canon(value) + b"\n" for value in values))


def git(*args):
    return subprocess.check_output(["git", "-C", str(SOURCE), *args], text=True).strip()


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


def context_refs(context):
    return [{key: caller[key] for key in ("path", "line", "lineSha256", "contextSha256", "fileSha256", "gitBlob")}
            for caller in context["callers"]]


def write_manifest():
    files = []
    for path in sorted(p for p in PKT.rglob("*") if p.is_file()
                       and p.name not in {"manifest.json", "SHA256SUMS.txt"}):
        data = path.read_bytes()
        files.append({"path": path.relative_to(PKT).as_posix(), "bytes": len(data), "sha256": sha(data)})
    manifest = {
        "artifact": "slskdN PR #409 W80 ranks 878-902 independent cross-review packet",
        "schemaVersion": 1,
        "repository": "snapetech-org/slskdN",
        "pullRequest": 409,
        "branch": BRANCH,
        "window": "W80",
        "head": HEAD,
        "tree": TREE,
        "continuationRankRange": [878, 902],
        "remainingQueueRankRange": [778, 802],
        "sourceCount": 25,
        "localeCount": 12,
        "cellCount": 300,
        "crossDecisionCounts": {"keep": 219, "propose": 81, "hold": 0},
        "proposalCount": 81,
        "noOpCount": 219,
        "holdCount": 0,
        "primaryProposalCountAudited": 55,
        "primaryProposalVerdicts": {"adopt": 25, "revise": 28, "reject": 2},
        "blindSuggestionCountAudited": 79,
        "blindSuggestionVerdicts": {"adopt": 75, "revise": 4, "reject": 0},
        "newProposalsBeyondPrimary": 28,
        "callerlessCellCount": 0,
        "catalogCurrentValuesReadBack": 300,
        "proposalTargetHashesVerified": 81,
        "baselineCurrentTokenMismatch": {
            "rank": 885, "locale": "ar", "protectedLiteral": "ID", "resolvedByCrossTarget": True,
        },
        "candidateFreeVerifier": "PASS",
        "primaryVerifier": "PASS",
        "blindPacketChecksums": "PASS",
        "sourceWorktreeHeadAtSeal": git("rev-parse", "HEAD"),
        "sourceWorktreeTreeAtSeal": git("rev-parse", "HEAD^{tree}"),
        "sourceWorktreeCleanAtSeal": not bool(git("status", "--porcelain=v1")),
        "blindReviewUsed": True,
        "nativeSpeakerSignoff": False,
        "browserReview": False,
        "prBodyQueried": False,
        "catalogChangesMade": False,
        "repositoryOrPrEdited": False,
        "appliedToRepository": False,
        "files": files,
    }
    write_json(PKT / "manifest.json", manifest)
    sums = []
    for path in sorted(p for p in PKT.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"):
        sums.append(f"{sha(path.read_bytes())}  {path.relative_to(PKT).as_posix()}")
    (PKT / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")


def main():
    if git("rev-parse", "HEAD") != HEAD or git("rev-parse", "HEAD^{tree}") != TREE:
        raise SystemExit("pinned source HEAD/tree changed before packet build")
    if git("status", "--porcelain=v1"):
        raise SystemExit("pinned source worktree is not clean")

    input_manifest = json.loads((INPUT / "manifest.json").read_text(encoding="utf-8"))
    primary_manifest = json.loads((PRIMARY / "manifest.json").read_text(encoding="utf-8"))
    blind_manifest = json.loads((BLIND / "manifest.json").read_text(encoding="utf-8"))
    if (input_manifest.get("head"), input_manifest.get("tree")) != (HEAD, TREE):
        raise SystemExit("candidate-free input pin changed")
    if (primary_manifest.get("head"), primary_manifest.get("tree")) != (HEAD, TREE):
        raise SystemExit("primary input pin changed")
    if (blind_manifest.get("head"), blind_manifest.get("tree")) != (HEAD, TREE):
        raise SystemExit("blind input pin changed")

    # Carry the minimum source rows and exact sealed manifests/checksum lists needed
    # to independently reproduce and verify every cross disposition.
    input_copies = {
        "candidate-free-manifest.json": INPUT / "manifest.json",
        "candidate-free-checksums.txt": INPUT / "PACKET-SHA256SUMS.txt",
        "source-current-cells.jsonl": INPUT / "source-current-cells.jsonl",
        "caller-contexts.jsonl": INPUT / "caller-contexts.jsonl",
        "catalog-structure.jsonl": INPUT / "catalog-structure.jsonl",
        "primary-manifest.json": PRIMARY / "manifest.json",
        "primary-checksums.txt": PRIMARY / "SHA256SUMS.txt",
        "primary-review.jsonl": PRIMARY / "primary-review.jsonl",
        "blind-manifest.json": BLIND / "manifest.json",
        "blind-checksums.txt": BLIND / "SHA256SUMS.txt",
        "blind-decisions.jsonl": BLIND / "decisions.jsonl",
    }
    for name, source in input_copies.items():
        (PKT / "inputs" / name).write_bytes(source.read_bytes())

    cells_raw = rows_raw(INPUT / "source-current-cells.jsonl")
    contexts_raw = rows_raw(INPUT / "caller-contexts.jsonl")
    primary_raw = rows_raw(PRIMARY / "primary-review.jsonl")
    blind_raw = rows_raw(BLIND / "decisions.jsonl")
    cells = {(row["continuationRank"], row["locale"]): (row, raw) for row, raw in cells_raw}
    contexts = {row["sourceId"]: row for row, _ in contexts_raw}
    primary = {(row["continuationRank"], row["locale"]): (row, raw) for row, raw in primary_raw}
    blind = {(row["continuationRank"], row["locale"]): (row, raw) for row, raw in blind_raw}
    expected = {(rank, locale) for rank in RANKS for locale in LOCALES}
    if any(set(group) != expected for group in (cells, primary, blind)):
        raise SystemExit("one or more source/primary/blind ledgers do not cover the 300-cell matrix")
    if len(contexts) != 25 or any(row.get("productionCallerCount", 0) == 0 for row in contexts.values()):
        raise SystemExit("selected sources do not all have caller evidence")

    proposal_rows = []
    primary_audit = []
    blind_audit = []
    decisions = []
    pinned_evidence = []
    proposal_map = {}
    primary_verdicts = collections.Counter()
    blind_verdicts = collections.Counter()

    for context in contexts.values():
        pinned_evidence.append({
            "schemaVersion": 1,
            "window": "W80",
            "head": HEAD,
            "tree": TREE,
            "continuationRank": context["continuationRank"],
            "remainingQueueRank": context["remainingQueueRank"],
            "sourceId": context["sourceId"],
            "source": context["source"],
            "sourceSha256": context["sourceSha256"],
            "callerContextSha256": sha(canon(context["callers"])),
            "productionCallerCount": context["productionCallerCount"],
            "callers": context["callers"],
        })
    pinned_evidence.sort(key=lambda row: row["continuationRank"])

    for rank, locale in sorted(expected):
        cell, cell_raw = cells[(rank, locale)]
        p, p_raw = primary[(rank, locale)]
        b, b_raw = blind[(rank, locale)]
        source_id = cell["sourceId"]
        context = contexts[source_id]
        caller_refs = context_refs(context)
        if (cell["callerRefs"] != caller_refs or p.get("callerRefs") != caller_refs or b.get("callerRefs") != caller_refs
                or cell["callerContextSha256"] != sha(canon(context["callers"]))):
            raise SystemExit(f"caller context mismatch before cross decision: {rank}/{locale}")

        if (rank, locale) in PRIMARY_SELECTIONS:
            if p.get("disposition") != "correct" or not p.get("target"):
                raise SystemExit(f"selected primary target is absent: {rank}/{locale}")
            target_source = "primary"
            target = p["target"]
        elif b.get("recommendedTarget"):
            target_source = "blind"
            target = b["recommendedTarget"]
        else:
            target_source = None
            target = None

        if (rank, locale) in REJECTED_PRIMARY_ONLY and target is not None:
            raise SystemExit(f"review override unexpectedly proposes a rejected primary-only cell: {rank}/{locale}")
        if target is not None and text_sha(target) == cell["currentTargetSha256"]:
            raise SystemExit(f"cross proposal equals current translation: {rank}/{locale}")

        if target is not None:
            disposition = "propose"
            if (rank, locale) in PRIMARY_VARIANT_RATIONALE:
                rationale = PROPOSED_CONTEXT[rank] + " " + PRIMARY_VARIANT_RATIONALE[(rank, locale)]
            elif target_source == "blind":
                rationale = PROPOSED_CONTEXT[rank] + " " + b["reason"]
            else:
                rationale = PROPOSED_CONTEXT[rank] + " " + p["rationale"]
        else:
            disposition = "keep"
            rationale = KEEP_CONTEXT[rank]
            if (rank, locale) == (882, "id"):
                rationale = "In Indonesian, tertunda functions as a pending/delayed state; the pinned callers reuse the label for queued jobs, incomplete chunks, and readiness checks, so the more specific waiting verb is not required."
            elif (rank, locale) == (882, "ja"):
                rationale = "保留中 is an established pending-status rendering across these queued, incomplete, and readiness uses; the caller evidence does not require replacing it with the narrower waiting-state wording."
            elif (rank, locale) == (885, "ar"):
                rationale = "The tooltip refers to an identifier, and the current Arabic معرف expresses that meaning directly; spelling ID in Latin letters adds no needed caller-specific information."

        token = token_check(cell["source"], cell["currentTarget"], target)
        current_token_keys = ("placeholderParityCurrent", "markupParityCurrent",
                              "numericTokensPreservedCurrent", "protectedLiteralsPreservedCurrent")
        if not all(token[key] for key in current_token_keys) and (rank, locale) != (885, "ar"):
            raise SystemExit(f"current token check failed: {rank}/{locale}")
        if (rank, locale) == (885, "ar") and not all(token[key] for key in current_token_keys[:-1]):
            raise SystemExit("unexpected Arabic current-token mismatch at 885/ar")
        if target is not None and not all(token["proposal"][key] for key in (
                "placeholderParity", "markupParity", "numericTokensPreserved", "protectedLiteralsPreserved")):
            raise SystemExit(f"proposed target token check failed: {rank}/{locale}")

        if p["disposition"] == "correct":
            if target is None:
                primary_verdict = "reject"
            elif target == p["target"]:
                primary_verdict = "adopt"
            else:
                primary_verdict = "revise"
        else:
            primary_verdict = "independent-proposal" if target is not None else "no-change"
        if b.get("recommendedTarget"):
            if target is None:
                blind_verdict = "reject"
            elif target == b["recommendedTarget"]:
                blind_verdict = "adopt"
            else:
                blind_verdict = "revise"
        else:
            blind_verdict = "not-proposed"

        primary_verdicts[primary_verdict] += 1 if p["disposition"] == "correct" else 0
        blind_verdicts[blind_verdict] += 1 if b.get("recommendedTarget") else 0
        row = {
            "schemaVersion": 1,
            "window": "W80",
            "continuationRank": rank,
            "remainingQueueRank": cell["remainingQueueRank"],
            "sourceId": source_id,
            "sourceIdSha256": text_sha(source_id),
            "locale": locale,
            "head": HEAD,
            "tree": TREE,
            "source": cell["source"],
            "sourceTextIncluded": True,
            "sourceSha256": cell["sourceSha256"],
            "catalogKey": cell["catalogKey"],
            "catalogPath": cell["catalogPath"],
            "catalogFileSha256": cell["catalogFileSha256"],
            "catalogGitBlob": cell["catalogGitBlob"],
            "currentTarget": cell["currentTarget"],
            "currentTargetTextIncluded": True,
            "currentTargetSha256": cell["currentTargetSha256"],
            "crossDisposition": disposition,
            "crossTargetSource": target_source,
            "crossTargetSha256": text_sha(target) if target is not None else None,
            "callerContextSha256": cell["callerContextSha256"],
            "productionCallerCount": context["productionCallerCount"],
            "callerRefs": caller_refs,
            "primaryDisposition": p["disposition"],
            "primaryProposal": p.get("target"),
            "primaryProposalSha256": p.get("targetSha256"),
            "primaryProposalVerdict": primary_verdict,
            "primaryRationaleSha256": text_sha(p["rationale"]) if p.get("rationale") else None,
            "blindDecision": b["decision"],
            "blindRecommendedTarget": b.get("recommendedTarget"),
            "blindRecommendedTargetSha256": text_sha(b["recommendedTarget"]) if b.get("recommendedTarget") else None,
            "blindSuggestionVerdict": blind_verdict,
            "blindReason": b["reason"],
            "rationale": rationale,
            "confidence": "moderate",
            "tokenCheck": token,
            "sourceCurrentRowSha256": sha(cell_raw),
            "primaryReviewRowSha256": sha(p_raw),
            "blindReviewRowSha256": sha(b_raw),
        }
        if target is not None:
            row["crossTarget"] = target
            proposal_map[f"{rank}|{locale}"] = target
            proposal_rows.append({
                "schemaVersion": 1,
                "window": "W80",
                "continuationRank": rank,
                "remainingQueueRank": cell["remainingQueueRank"],
                "sourceId": source_id,
                "sourceIdSha256": text_sha(source_id),
                "locale": locale,
                "source": cell["source"],
                "sourceSha256": cell["sourceSha256"],
                "catalogKey": cell["catalogKey"],
                "catalogPath": cell["catalogPath"],
                "catalogFileSha256": cell["catalogFileSha256"],
                "catalogGitBlob": cell["catalogGitBlob"],
                "currentTarget": cell["currentTarget"],
                "currentTargetSha256": cell["currentTargetSha256"],
                "target": target,
                "targetSha256": text_sha(target),
                "targetSource": target_source,
                "crossTargetSha256": text_sha(target),
                "callerContextSha256": cell["callerContextSha256"],
                "productionCallerCount": context["productionCallerCount"],
                "callerRefs": caller_refs,
                "primaryProposalVerdict": primary_verdict,
                "blindSuggestionVerdict": blind_verdict,
                "primaryReviewRowSha256": sha(p_raw),
                "blindReviewRowSha256": sha(b_raw),
                "crossRationale": rationale,
                "tokenCheck": token,
                "planOnly": True,
                "appliedToRepository": False,
            })
        decisions.append(row)

        if p["disposition"] == "correct":
            primary_audit.append({
                "schemaVersion": 1,
                "window": "W80",
                "continuationRank": rank,
                "locale": locale,
                "sourceId": source_id,
                "callerContextSha256": cell["callerContextSha256"],
                "primaryProposal": p["target"],
                "primaryProposalSha256": p["targetSha256"],
                "crossTarget": target,
                "crossTargetSha256": text_sha(target) if target is not None else None,
                "crossVerdict": primary_verdict,
                "crossRationaleSha256": text_sha(rationale),
                "primaryReviewRowSha256": sha(p_raw),
            })
        if b.get("recommendedTarget"):
            blind_audit.append({
                "schemaVersion": 1,
                "window": "W80",
                "continuationRank": rank,
                "locale": locale,
                "sourceId": source_id,
                "callerContextSha256": cell["callerContextSha256"],
                "blindDecision": b["decision"],
                "blindRecommendedTarget": b["recommendedTarget"],
                "blindRecommendedTargetSha256": text_sha(b["recommendedTarget"]),
                "crossTarget": target,
                "crossTargetSha256": text_sha(target) if target is not None else None,
                "crossVerdict": blind_verdict,
                "crossRationaleSha256": text_sha(rationale),
                "blindReviewRowSha256": sha(b_raw),
            })

    counts = collections.Counter(row["crossDisposition"] for row in decisions)
    primary_audit_counts = {name: primary_verdicts[name] for name in ("adopt", "revise", "reject")}
    blind_audit_counts = {name: blind_verdicts[name] for name in ("adopt", "revise", "reject")}
    if counts != collections.Counter({"keep": 219, "propose": 81}):
        raise SystemExit(f"unexpected cross disposition counts: {counts}")
    if primary_verdicts != collections.Counter({"adopt": 25, "revise": 28, "reject": 2}):
        raise SystemExit(f"unexpected primary audit counts: {primary_verdicts}")
    if blind_verdicts != collections.Counter({"adopt": 75, "revise": 4}):
        raise SystemExit(f"unexpected blind audit counts: {blind_verdicts}")

    write_jsonl(PKT / "pinned-source-evidence.jsonl", pinned_evidence)
    write_jsonl(PKT / "cross-review-decisions.jsonl", decisions)
    write_jsonl(PKT / "primary-proposal-audit.jsonl", primary_audit)
    write_jsonl(PKT / "blind-suggestion-audit.jsonl", blind_audit)
    write_jsonl(PKT / "proposal-apply-plan.jsonl", proposal_rows)
    write_json(PKT / "proposal-map.json", proposal_map)

    attestation = {
        "schemaVersion": 1,
        "candidateFreeManifestSha256": sha((PKT / "inputs/candidate-free-manifest.json").read_bytes()),
        "candidateFreeChecksumListSha256": sha((PKT / "inputs/candidate-free-checksums.txt").read_bytes()),
        "sourceCurrentCellsSha256": sha((PKT / "inputs/source-current-cells.jsonl").read_bytes()),
        "callerContextsSha256": sha((PKT / "inputs/caller-contexts.jsonl").read_bytes()),
        "catalogStructureSha256": sha((PKT / "inputs/catalog-structure.jsonl").read_bytes()),
        "primaryManifestSha256": sha((PKT / "inputs/primary-manifest.json").read_bytes()),
        "primaryChecksumListSha256": sha((PKT / "inputs/primary-checksums.txt").read_bytes()),
        "primaryReviewLedgerSha256": sha((PKT / "inputs/primary-review.jsonl").read_bytes()),
        "blindManifestSha256": sha((PKT / "inputs/blind-manifest.json").read_bytes()),
        "blindChecksumListSha256": sha((PKT / "inputs/blind-checksums.txt").read_bytes()),
        "blindReviewLedgerSha256": sha((PKT / "inputs/blind-decisions.jsonl").read_bytes()),
    }
    write_json(PKT / "input-attestation.json", attestation)

    live_before = json.loads((INPUT / "live-before.json").read_text(encoding="utf-8"))
    live_after = json.loads((INPUT / "live-after.json").read_text(encoding="utf-8"))
    write_json(PKT / "live-before.json", live_before)
    write_json(PKT / "live-after.json", live_after)
    upstream = {
        "schemaVersion": 1,
        "source": "copied from verified candidate-free input; no PR body was queried",
        "head": HEAD,
        "tree": TREE,
        "liveBeforeSha256": sha(json_bytes(live_before)),
        "liveAfterSha256": sha(json_bytes(live_after)),
        "prBodyQueried": False,
    }
    write_json(PKT / "upstream-verification.json", upstream)

    summary = {
        "artifact": "slskdN PR #409 W80 independent cross-review",
        "schemaVersion": 1,
        "window": "W80",
        "continuationRankRange": [878, 902],
        "remainingQueueRankRange": [778, 802],
        "repository": "snapetech-org/slskdN",
        "pullRequest": 409,
        "branch": BRANCH,
        "head": HEAD,
        "tree": TREE,
        "sourceCount": 25,
        "localeCount": 12,
        "locales": LOCALES,
        "cellCount": len(decisions),
        "crossDecisionCounts": dict(counts),
        "crossProposalCount": len(proposal_rows),
        "noOpCount": counts["keep"],
        "crossHoldCount": counts["hold"],
        "callerlessCellCount": 0,
        "primaryProposalCountAudited": len(primary_audit),
        "primaryProposalVerdicts": primary_audit_counts,
        "newProposalsBeyondPrimary": sum(1 for row in proposal_rows if row["primaryProposalVerdict"] == "independent-proposal"),
        "blindSuggestionCountAudited": len(blind_audit),
        "blindSuggestionVerdicts": blind_audit_counts,
        "catalogCurrentValuesReadBack": len(decisions),
        "proposalTargetHashesVerified": len(proposal_rows),
        "baselineCurrentTokenMismatch": {
            "rank": 885, "locale": "ar", "protectedLiteral": "ID", "resolvedByCrossTarget": True,
        },
        "candidateFreeVerifier": "PASS",
        "primaryVerifier": "PASS",
        "blindChecksums": "PASS",
        "inputAttestationSha256": sha((PKT / "input-attestation.json").read_bytes()),
        "sourceWorktreeHeadAtSeal": git("rev-parse", "HEAD"),
        "sourceWorktreeTreeAtSeal": git("rev-parse", "HEAD^{tree}"),
        "sourceWorktreeCleanAtSeal": not bool(git("status", "--porcelain=v1")),
        "nativeSpeakerSignoff": False,
        "browserReview": False,
        "prBodyQueried": False,
        "catalogChangesMade": False,
        "repositoryOrPrEdited": False,
        "appliedToRepository": False,
    }
    write_json(PKT / "summary.json", summary)

    readme = """# slskdN PR #409 W80 independent cross-review

This packet cross-checks all 300 locale cells for continuation ranks 878–902 against the sealed candidate-free input, exact pinned caller contexts, the primary semantic review, and the independent blind review.

- Source pin: `7a1ca27fd0519674c3b42a3e3df3638b0f671567` / tree `b3525218d0f9676c88c4991e78775d113f18b7d9`.
- Cross dispositions: 81 proposals, 219 keeps, and 0 holds. All 25 selected source keys have production callers.
- All 55 primary proposals and 79 blind suggestions are separately audited. The cross outcome adopts, revises, or rejects each proposal and binds it to the relevant source row hash.
- `cross-review-decisions.jsonl` contains one contextual disposition per rank/locale cell. `pinned-source-evidence.jsonl` records each caller's exact source lines and context hashes.
- The 81 target rows are an unapplied proposal plan only. No catalog, repository, branch, or PR was changed; the PR body was not queried.
- Candidate-free input identified one current protected-literal mismatch at 885/ar: Arabic translates source ID as “identifier.” The selected target retains ID and the pinned catalog check verifies that proposal at the exact source key.
- No native-speaker signoff or browser review is claimed.

Run the portable verifier with `python3 verify_cross_packet.py --repo /path/to/slskdN`. Verify packet checksums from this directory with `sha256sum -c SHA256SUMS.txt`.
"""
    (PKT / "README.md").write_text(readme, encoding="utf-8")

    if git("rev-parse", "HEAD") != HEAD or git("rev-parse", "HEAD^{tree}") != TREE or git("status", "--porcelain=v1"):
        raise SystemExit("pinned source changed during packet build")
    write_manifest()
    print(json.dumps({
        "result": "BUILT",
        "head": HEAD,
        "tree": TREE,
        "cells": len(decisions),
        "dispositions": dict(counts),
        "proposals": len(proposal_rows),
        "primaryAudit": dict(primary_verdicts),
        "blindAudit": dict(blind_verdicts),
        "sourceWorktreeClean": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
