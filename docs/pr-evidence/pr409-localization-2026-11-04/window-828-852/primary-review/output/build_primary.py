#!/usr/bin/env python3
"""Build the W78 independent primary decisions from sealed candidate-free inputs."""
import collections
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent.parent / "candidate-free" / "input"
HEAD = "4120c9637e71466dc98d51a5a342dee199a1e004"
TREE = "063b62f268eb81253d2b9b4c77ad045c2f25a394"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]

# Exact proposals keyed by continuation rank and locale; reviewed against sealed candidate-free cells.
_decisions = json.loads((ROOT / "rationale-map.json").read_text(encoding="utf-8"))
PROPOSALS = {(int(key.split("|", 1)[0]), key.split("|", 1)[1]): value
             for key, value in json.loads((ROOT / "proposal-map.json").read_text(encoding="utf-8")).items()}
SOURCE_RATIONALES = {int(key): value for key, value in _decisions["accepted"].items()}
CORRECTION_RATIONALES = {int(key): value for key, value in _decisions["corrections"].items()}

def sha(data):
    return hashlib.sha256(data).hexdigest()


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


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


def write_rows(name, values):
    (ROOT / name).write_text("".join(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for value in values), encoding="utf-8")


def main():
    cells = [json.loads(line) for line in (INPUT / "source-current-cells.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    callers = {row["continuationRank"]: row for row in
               (json.loads(line) for line in (INPUT / "caller-contexts.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())}
    if len(cells) != 300 or len(PROPOSALS) != 56:
        raise SystemExit("refusing unexpected W78 coverage or proposal map")
    ledger, corrections, holds = [], [], []
    for cell in cells:
        rank, locale = cell["continuationRank"], cell["locale"]
        caller = callers[rank]
        proposal = PROPOSALS.get((rank, locale))
        base = {
            "schemaVersion": 1, "reviewPass": "independent-primary", "head": HEAD, "tree": TREE,
            "continuationRank": rank, "remainingQueueRank": cell["remainingQueueRank"],
            "sourceId": cell["sourceId"], "sourceSha256": cell["sourceSha256"], "locale": locale,
            "catalogPath": cell["catalogPath"], "catalogFileSha256": cell["catalogFileSha256"],
            "catalogGitBlob": cell["catalogGitBlob"], "currentTargetSha256": cell["currentTargetSha256"],
            "callerContextSha256": cell["callerContextSha256"], "callerRefs": cell["callerRefs"],
            "productionCallerCount": caller["productionCallerCount"],
            "sourceRewriteRecommendation": None,
        }
        if caller["productionCallerCount"] == 0:
            if proposal is not None:
                raise SystemExit(f"callerless cell may not receive a proposal: {rank}/{locale}")
            evidence = token_check(cell["source"], cell["currentTarget"])
            hold = dict(base)
            hold.update({
                "disposition": "hold", "confidence": "high",
                "holdReason": "No exact quoted production caller exists in the pinned runtime inventory, so the current locale value has no confirmed user-facing context. Hold unchanged pending caller context.",
                "holdReasonSha256": sha(b"No exact quoted production caller exists in the pinned runtime inventory, so the current locale value has no confirmed user-facing context. Hold unchanged pending caller context."),
                "sourceTextIncluded": False, "currentTargetTextIncluded": False,
                "tokenEvidence": {
                    "evidenceSha256": sha(canon(evidence)),
                    "placeholderParityCurrent": evidence["placeholderParityCurrent"],
                    "markupParityCurrent": evidence["markupParityCurrent"],
                    "numericTokensPreservedCurrent": evidence["numericTokensPreservedCurrent"],
                    "protectedLiteralsPreservedCurrent": evidence["protectedLiteralsPreservedCurrent"],
                },
            })
            ledger.append(hold)
            holds.append(hold)
            continue
        source, current = cell["source"], cell["currentTarget"]
        row = dict(base)
        row.update({
            "source": source, "catalogKey": cell["catalogKey"], "currentTarget": current,
            "disposition": "correct" if proposal is not None else "accept-current",
            "confidence": "moderate",
            "rationale": CORRECTION_RATIONALES[rank] if proposal is not None else SOURCE_RATIONALES[rank],
            "tokenCheck": token_check(source, current, proposal),
        })
        if proposal is not None:
            if not all((ph(source) == ph(proposal), tags(source) == tags(proposal),
                        not_less(nums(source), nums(proposal)), all(x in proposal for x in prot(source)))):
                raise SystemExit(f"proposal token check failed: {rank}/{locale}")
            row["target"] = proposal
            row["targetSha256"] = sha(proposal.encode("utf-8"))
            corrections.append(row)
        ledger.append(row)
    if len(ledger) != 300 or len(corrections) != 56 or len(holds) != 12:
        raise SystemExit("refusing unexpected W78 decision counts")
    write_rows("primary-review.jsonl", ledger)
    write_rows("corrections.jsonl", corrections)
    write_rows("holds-hash-only.jsonl", holds)
    (ROOT / "source-rewrite-recommendations.json").write_text(json.dumps({"schemaVersion": 1, "recommendations": []}, indent=2) + "\n", encoding="utf-8")
    counts = collections.Counter(row["disposition"] for row in ledger)
    summary = {
        "artifact": "slskdN PR #409 W78 independent primary semantic review",
        "head": HEAD, "tree": TREE, "sourceCount": 25, "localeCount": 12, "cellCount": 300,
        "dispositions": {key: counts[key] for key in ("accept-current", "correct", "hold")},
        "proposedTargetCount": len(corrections), "holds": len(holds),
        "callerlessSources": sum(row["productionCallerCount"] == 0 for row in callers.values()),
        "callerlessCells": len(holds),
        "candidateFreeInputManifestSha256": sha((INPUT / "manifest.json").read_bytes()),
        "candidateFreeInputChecksumListSha256": sha((INPUT / "PACKET-SHA256SUMS.txt").read_bytes()),
        "selectionBoundarySha256": sha((INPUT / "selection-boundary.jsonl").read_bytes()),
        "sourceInventorySelectionSha256": sha((INPUT / "source-inventory-selection.jsonl").read_bytes()),
        "callerContextSha256": sha((INPUT / "caller-contexts.jsonl").read_bytes()),
        "mainDriftSha256": sha((INPUT / "main-drift.json").read_bytes()),
        "liveMainSha": json.loads((INPUT / "live-after.json").read_text(encoding="utf-8"))["liveMainSha"],
        "baseApiSha": json.loads((INPUT / "live-after.json").read_text(encoding="utf-8"))["baseRefOid"],
        "priorHeldCellsCarried": 331, "priorHoldResolutionHistoryRows": 13,
        "blindReviewUsed": False, "crossReviewUsed": False,
        "nativeSpeakerSignoff": False, "browserReview": False,
        "sourceRewritesRecommended": 0,
        "proposals": [{"continuationRank": r, "sourceId": next(c["sourceId"] for c in cells if c["continuationRank"] == r),
                       "locale": l, "target": t, "targetSha256": sha(t.encode("utf-8"))}
                      for (r, l), t in PROPOSALS.items()],
        "heldCells": [{"continuationRank": row["continuationRank"], "sourceId": row["sourceId"], "locale": row["locale"],
                        "sourceSha256": row["sourceSha256"], "currentTargetSha256": row["currentTargetSha256"]} for row in holds],
    }
    (ROOT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": "BUILT-PRIMARY-UNSEALED", "head": HEAD, "tree": TREE,
                      "dispositions": summary["dispositions"], "proposalCount": len(corrections),
                      "hashOnlyHolds": len(holds)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
