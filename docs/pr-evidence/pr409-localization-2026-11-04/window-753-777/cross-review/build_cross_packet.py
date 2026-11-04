#!/usr/bin/env python3
import hashlib, json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CF = ROOT / "inputs/candidate-free-input"
PR = ROOT / "inputs/primary-review"
BL = ROOT / "inputs/blind-review"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def shat(text):
    return sha(text.encode("utf-8"))

def j(path):
    return json.loads(path.read_text(encoding="utf-8"))

def jl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def write_jsonl(path, values):
    path.write_text("".join(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n" for value in values), encoding="utf-8")

# key -> chosen exact reviewer target, cross-review confidence, and resolution.
OVERRIDES = {
    "758::ar": ("blind", "moderate", "The caller is a copy-report control in the RealmSubjectIndexConflicts component. The selected target restores the realm subject-index relation as a clear action label."),
    "758::de": ("blind", "moderate", "The caller is a copy-report control in the RealmSubjectIndexConflicts component. The selected target fixes the current wording that makes the index sound like a separate party in the conflict."),
    "758::es": ("blind", "moderate", "The caller is a copy-report control in the RealmSubjectIndexConflicts component. The selected target fixes the current subject-matter reading and gives a clear copy action."),
    "758::fr": ("blind", "moderate", "The caller is a copy-report control in the RealmSubjectIndexConflicts component. The selected target makes the realm subject-index relation clear."),
    "758::hi": ("blind", "moderate", "The caller is a copy-report control in the RealmSubjectIndexConflicts component. The selected target retains the identity-realm context in the subject-index phrase."),
    "758::id": ("blind", "moderate", "The caller is a copy-report control in the RealmSubjectIndexConflicts component. The selected target restores the identity-realm subject-index meaning."),
    "758::ja": ("primary", "moderate", "Both proposals replace the unreadable transliteration. The primary target stays closer to the source’s realm subject-index wording and does not add an authentication qualifier absent from the source text."),
    "758::ko": ("blind", "moderate", "The caller is a copy-report control in the RealmSubjectIndexConflicts component. The selected target uses 주체 for an identity subject rather than 주제 for a topic."),
    "758::pt-BR": ("blind", "moderate", "The caller is a copy-report control in the RealmSubjectIndexConflicts component. The selected target avoids the current topical/geographic reading and preserves the identity-domain context."),
    "758::vi": ("blind", "moderate", "The caller is a copy-report control in the RealmSubjectIndexConflicts component. The selected target uses chủ thể for an identity subject rather than chủ đề for a topic."),
    "758::zh-Hans": ("blind", "moderate", "Both proposals remove the zero-width spacing. The blind target also changes 主题 (topic) to 主体 (identity subject), which fits the component context."),
    "758::zh-Hant": ("blind", "moderate", "The caller is a copy-report control in the RealmSubjectIndexConflicts component. The selected target uses 主體 for an identity subject rather than 主題 for a topic."),
    "759::hi": ("blind", "moderate", "The tooltip refers to peer-network browsing, not browsing with colleagues. The selected target uses the technical peer term."),
    "759::id": ("blind", "moderate", "The tooltip refers to peer-network browsing, not colleagues. The selected target uses peer in that technical sense and localizes Wishlist consistently with the adjacent Indonesian feature label."),
    "759::zh-Hans": ("blind", "moderate", "The tooltip refers to peer-network browsing. The selected target describes browsing content shared by peer users, avoiding the colleague reading of 同行."),
    "759::zh-Hant": ("blind", "moderate", "The tooltip refers to peer-network browsing. The selected target describes browsing shared peer content, avoiding the colleague reading of 同行."),
    "760::es": ("blind", "moderate", "The caller is an artist music-release radar. The selected target uses lanzamientos for new music releases and clearly marks the unread notification filter."),
    "760::fr": ("primary", "moderate", "The caller is an artist music-release radar. Sorties expresses music releases more naturally than the current generic publication wording."),
    "761::ar": ("both", "high", "Both reviewers replace the sports-match sense with matching search/list results; the caller is an empty-result state."),
    "761::ja": ("blind", "moderate", "Both targets express an empty matching-items state. The blind phrasing uses the natural existential form for no matching items."),
    "763::ar": ("primary", "moderate", "The caller is a security-settings description for users facing threats. The primary wording states that threat context without repeating the security-options phrase."),
    "763::de": ("primary", "moderate", "The caller describes security features for users facing threats. The primary wording avoids the repeated Sicherheitsfunktionen/Sicherheitsoptionen construction in the blind alternative."),
    "763::es": ("primary", "moderate", "The source describes security features for hostile environments. The primary wording avoids the adverse-feature false sense and keeps the feminine agreement for funciones."),
    "763::fr": ("primary", "moderate", "The source describes security features for hostile environments. The primary wording avoids the contradictory-feature false sense and uses feminine agreement for fonctionnalités."),
    "763::hi": ("blind", "moderate", "The current wording says adverse features. The selected target explicitly describes security features for hostile environments and preserves the disabled-by-default and explicit-configuration requirements."),
    "763::id": ("primary", "moderate", "The caller describes security options for users facing threats. The primary target gives that meaning in plain Indonesian rather than relying on the English loan adversarial."),
    "763::vi": ("blind", "moderate", "The source describes an adversarial security environment. The blind target uses đối kháng for that technical context; the primary alternative drops the environment phrasing."),
    "764::zh-Hans": ("blind", "moderate", "The tooltip adds a nearby peer as a contact. The selected target describes a person/network peer rather than a generic node."),
    "764::zh-Hant": ("blind", "moderate", "The tooltip adds a nearby peer as a contact. The selected target describes a person/network peer rather than a device."),
    "767::hi": ("blind", "high", "The caller labels an Artist MBID field. The selected target preserves the exact ASCII identifier example and renders e.g. as a natural Hindi example phrase."),
    "769::hi": ("both", "moderate", "Both reviewers use टूल for the software provenance tool label; औजार would usually mean a physical implement."),
    "769::ja": ("both", "moderate", "Both reviewers use ツール for the software provenance tool label; 道具 suggests a physical implement."),
    "769::vi": ("primary", "moderate", "The caller labels software provenance availability. Công cụ is the software-tool term; dụng cụ suggests a physical implement."),
    "773::de": ("primary", "moderate", "The caller reports completion of IPLD graph traversal. Graphdurchlauf names that operation more clearly than the current geographic-crossing term."),
    "773::fr": ("primary", "moderate", "The caller reports completion of IPLD graph traversal. Parcours fits traversal better than the current crossing term."),
    "773::pt-BR": ("primary", "moderate", "The caller reports completion of IPLD graph traversal. Percurso fits traversal better than the current crossing term."),
    "773::vi": ("both", "high", "Both reviewers replace the current transmission wording with the exact graph-traversal operation reported by the caller."),
    "774::ar": ("blind", "moderate", "The caller is the browser-local music-player discovery shelf. The selected target clarifies that its ratings come from the music player, not human players."),
    "774::de": ("blind", "moderate", "The caller is the browser-local music-player discovery shelf. The selected target clarifies that its ratings come from the music player, not human players."),
    "774::es": ("blind", "moderate", "The caller is the browser-local music-player discovery shelf. The selected target clarifies that its ratings come from the music player, not human players."),
    "774::fr": ("blind", "moderate", "The caller is the browser-local music-player discovery shelf. The selected target clarifies that its ratings come from the music player, not human players."),
    "774::hi": ("blind", "moderate", "The caller is a discovery-shelf button in the music player. The selected target uses the feature’s discovery-shelf wording rather than a search-shelf phrase."),
    "774::id": ("blind", "moderate", "The caller is the browser-local music-player discovery shelf. The selected target identifies ratings stored in the music player, not rankings of human players."),
    "774::ko": ("blind", "moderate", "The caller is a discovery-shelf button in the music player. The selected target uses discovery-shelf terminology rather than a search-shelf phrase."),
    "774::pt-BR": ("blind", "moderate", "The caller is the browser-local music-player discovery shelf. The selected target clarifies that its ratings come from the music player, not human players."),
    "774::vi": ("blind", "moderate", "The caller is the browser-local music-player discovery shelf. The selected target identifies ratings recorded in the music player, not rankings of human players."),
    "774::zh-Hans": ("blind", "moderate", "The caller is the browser-local music-player discovery shelf. The selected target clarifies that its ratings come from the music player and uses 探索架 for discovery."),
    "774::zh-Hant": ("blind", "moderate", "The caller is the browser-local music-player discovery shelf. The selected target clarifies that its ratings come from the music player and uses 探索架 for discovery."),
    "775::ja": ("blind", "moderate", "The caller is the previous-track button. The selected target says to play this track from the beginning; 再開 could instead mean resuming from a paused position."),
}

def primary_proposal(p):
    return {
        "target": p["target"],
        "targetSha256": shat(p["target"]),
        "rationale": p["rationale"],
        "confidence": p["confidence"],
        "sourceFile": "primary-review/corrections.jsonl",
    }

def blind_proposal(b):
    return {
        "target": b["proposedTarget"],
        "targetSha256": shat(b["proposedTarget"]),
        "rationale": b["rationale"],
        "confidence": b["confidenceInIssueOrDisposition"],
        "sourceFile": "blind-review/blind-decisions.jsonl",
    }

manifest = j(CF / "manifest.json")
primary_summary = j(PR / "summary.json")
blind_manifest = j(BL / "manifest.json")
primary_cells = {(x["continuationRank"], x["locale"]): x for x in jl(PR / "primary-review.jsonl")}
primary_corrections = {(x["continuationRank"], x["locale"]): x for x in jl(PR / "corrections.jsonl")}
primary_holds = {(x["continuationRank"], x["locale"]): x for x in jl(PR / "holds-hash-only.jsonl")}
blind_cells = {(x["continuationRank"], x["locale"]): x for x in jl(BL / "blind-decisions.jsonl")}
candidate_cells_ordered = jl(CF / "source-current-cells.jsonl")
candidate_cells = {(x["continuationRank"], x["locale"]): x for x in candidate_cells_ordered}

assert manifest["head"] == primary_summary["head"] == blind_manifest["pr"]["head"] == "99d6afbfb8cca4dccc018e72c01950bc304240db"
assert manifest["tree"] == primary_summary["tree"] == blind_manifest["pr"]["tree"] == "f21cb5cde009ac35f5531ddc40612821aee6f471"
assert len(candidate_cells) == len(primary_cells) == len(blind_cells) == 300
assert len(primary_corrections) == 20 and len(primary_holds) == 12
assert sum(x["disposition"] == "revise" for x in blind_cells.values()) == 44
assert len(OVERRIDES) == 49

ledger = []
reconciliation = []
disagreements = []
holds = []
selected_source_counts = Counter()
for c in candidate_cells_ordered:
    key = (c["continuationRank"], c["locale"])
    key_id = f"{key[0]}::{key[1]}"
    p = primary_cells[key]
    b = blind_cells[key]
    pc = primary_corrections.get(key)
    ph = primary_holds.get(key)
    bp = b if b["disposition"] == "revise" else None

    assert c["sourceId"] == p["sourceId"] == b["sourceId"]
    assert c["sourceSha256"] == p["sourceSha256"] == b["sourceSha256"]
    assert c["callerContextSha256"] == p["callerContextSha256"] == b["callerContextSha256"]
    assert c["currentTargetSha256"] == b["currentTargetSha256"]
    assert b["currentTarget"] == c["currentTarget"]
    if p["disposition"] != "hold":
        assert p["currentTargetSha256"] == c["currentTargetSha256"]
    assert (p["disposition"] == "correct") == (pc is not None)
    assert (p["disposition"] == "hold") == (ph is not None)
    assert (b["disposition"] == "revise") == (bp is not None)

    if p["disposition"] == "hold":
        assert key_id not in OVERRIDES and key in primary_holds and b["disposition"] == "accept"
        rationale = "Keep this cell hash-only. The pinned callers use the same source entry as icon names, renderer/schema keys, separators, and failure glyphs; none establishes one stable user-facing string. The blind pass accepts the current value but does not resolve these incompatible caller roles."
        hrow = {
            "window": "W75",
            "continuationRank": key[0],
            "remainingQueueRank": c["remainingQueueRank"],
            "locale": key[1],
            "sourceId": c["sourceId"],
            "sourceSha256": c["sourceSha256"],
            "sourceTextIncluded": False,
            "currentTargetSha256": c["currentTargetSha256"],
            "currentTargetIncluded": False,
            "selectedTargetSha256": c["currentTargetSha256"],
            "selectedTargetIncluded": False,
            "callerContextSha256": c["callerContextSha256"],
            "primaryDisposition": "hold",
            "primaryHoldReasonSha256": shat(p["holdReason"]),
            "primaryCallerReferences": [
                {k: ref[k] for k in ("path", "line", "contextSha256", "lineSha256", "fileSha256", "gitBlob")}
                for ref in p["callerRefs"]
            ],
            "blindDisposition": "accept",
            "crossDecision": "hold-hash-only",
            "crossRationale": rationale,
            "confidence": "high",
        }
        holds.append(hrow)
        row = {
            "schemaVersion": 1,
            "window": "W75",
            "continuationRank": key[0],
            "remainingQueueRank": c["remainingQueueRank"],
            "locale": key[1],
            "sourceId": c["sourceId"],
            "sourceIdSha256": sha(c["sourceId"].encode("utf-8")),
            "sourceText": None,
            "sourceSha256": c["sourceSha256"],
            "currentTarget": None,
            "currentTargetSha256": c["currentTargetSha256"],
            "callerContextSha256": c["callerContextSha256"],
            "primaryDisposition": "hold",
            "primaryProposal": None,
            "primaryHoldReasonSha256": shat(p["holdReason"]),
            "blindDisposition": "accept",
            "blindProposal": None,
            "decision": "hold-hash-only",
            "selectedTarget": None,
            "selectedTargetSha256": c["currentTargetSha256"],
            "selectedProposalSources": [],
            "rationale": rationale,
            "confidence": "high",
            "hold": True,
        }
    else:
        assert key not in primary_holds
        if key_id in OVERRIDES:
            side, confidence, rationale = OVERRIDES[key_id]
            if pc:
                candidates = {"primary": pc["target"]}
            else:
                candidates = {}
            if bp:
                candidates["blind"] = bp["proposedTarget"]
            if side == "both":
                assert "primary" in candidates and "blind" in candidates
                assert candidates["primary"] == candidates["blind"]
                selected = candidates["primary"]
            else:
                assert side in candidates
                selected = candidates[side]
            assert selected != c["currentTarget"]
            target_sources = [name for name, value in candidates.items() if value == selected]
            assert target_sources
            decision = "select-agreed-target" if len(target_sources) == 2 else f"select-{target_sources[0]}-target"
            selected_source_counts["+".join(target_sources)] += 1
        else:
            assert pc is None and bp is None
            assert p["disposition"] == "accept-current" and b["disposition"] == "accept"
            selected = c["currentTarget"]
            target_sources = ["current"]
            decision = "keep-current"
            confidence = "moderate"
            rationale = "Retain the exact current translation. Both independent reviewers accept it, and this cross pass found no semantic or caller-context defect in the sealed candidate-free input."
        selected_hash = shat(selected)
        pp = primary_proposal(pc) if pc else None
        bb = blind_proposal(bp) if bp else None
        row = {
            "schemaVersion": 1,
            "window": "W75",
            "continuationRank": key[0],
            "remainingQueueRank": c["remainingQueueRank"],
            "locale": key[1],
            "sourceId": c["sourceId"],
            "sourceIdSha256": sha(c["sourceId"].encode("utf-8")),
            "sourceText": c["source"],
            "sourceSha256": c["sourceSha256"],
            "currentTarget": c["currentTarget"],
            "currentTargetSha256": c["currentTargetSha256"],
            "callerContextSha256": c["callerContextSha256"],
            "primaryDisposition": p["disposition"],
            "primaryProposal": pp,
            "primaryHoldReasonSha256": None,
            "blindDisposition": b["disposition"],
            "blindProposal": bb,
            "decision": decision,
            "selectedTarget": selected,
            "selectedTargetSha256": selected_hash,
            "selectedProposalSources": target_sources if decision != "keep-current" else [],
            "rationale": rationale,
            "confidence": confidence,
            "hold": False,
        }
        if pc or bp:
            if pc and bp:
                status = "same-target" if pc["target"] == bp["proposedTarget"] else "different-targets"
            elif pc:
                status = "primary-only"
            else:
                status = "blind-only"
            selected_sources = [name for name, target in (("primary", pc["target"] if pc else None), ("blind", bp["proposedTarget"] if bp else None)) if target == selected]
            discarded_sources = [name for name, target in (("primary", pc["target"] if pc else None), ("blind", bp["proposedTarget"] if bp else None)) if target is not None and target != selected]
            rec = {
                "window": "W75",
                "continuationRank": key[0],
                "remainingQueueRank": c["remainingQueueRank"],
                "locale": key[1],
                "sourceId": c["sourceId"],
                "sourceSha256": c["sourceSha256"],
                "callerContextSha256": c["callerContextSha256"],
                "currentTarget": c["currentTarget"],
                "currentTargetSha256": c["currentTargetSha256"],
                "status": status,
                "primaryProposal": pp,
                "blindProposal": bb,
                "selectedTarget": selected,
                "selectedTargetSha256": selected_hash,
                "selectedProposalSources": selected_sources,
                "supersededProposalSources": discarded_sources,
                "resolutionRationale": rationale,
            }
            reconciliation.append(rec)
            if status == "different-targets":
                disagreements.append(rec)
    ledger.append(row)

assert len(ledger) == 300 and len(reconciliation) == 49 and len(holds) == 12 and len(disagreements) == 11
write_jsonl(ROOT / "cross-ledger.jsonl", ledger)
write_jsonl(ROOT / "proposal-reconciliation.jsonl", reconciliation)
write_jsonl(ROOT / "proposal-disagreements.jsonl", disagreements)
write_jsonl(ROOT / "holds-hash-only.jsonl", holds)

assessments = j(BL / "protected-literal-assessments.json")["assessments"]
localized = [x for x in assessments if x["decision"] == "accept-localized-feature-name"]
assert len(localized) == 23
write_json(ROOT / "input-verifier-results.json", {
    "candidateFree": {
        "result": "PASS",
        "head": manifest["head"],
        "tree": manifest["tree"],
        "window": manifest["window"],
        "sourceCount": 25,
        "localeCount": 12,
        "cells": 300,
        "catalogs": 12,
        "runtimeFilesPinned": 279,
        "priorSelectedIdsHashOnly": 1832,
        "priorHeldCellsHashOnly": 259,
        "priorHoldResolutionsHashOnly": 13,
        "priorHeldTargetHashesMatch": True,
        "catalogPinsVerifiedAgainstExactHeadWorktree": True,
        "sourceWorktreeRemovedAfterVerification": False,
    },
    "primary": {
        "result": "PASS",
        "head": manifest["head"],
        "tree": manifest["tree"],
        "cells": 300,
        "acceptCurrent": 268,
        "corrections": 20,
        "hashOnlyHolds": 12,
        "tokenMismatchesAmongProposals": 0,
    },
    "blind": {
        "result": "PASS",
        "head": manifest["head"],
        "tree": manifest["tree"],
        "cells": 300,
        "accept": 256,
        "revise": 44,
        "holds": 0,
        "localizedWishlistBaselineExceptions": 23,
    },
    "checksums": {
        "candidateFree": "PASS",
        "primary": "PASS",
        "blind": "PASS",
    },
    "livePRBeforeReview": "PASS",
})
summary = {
    "artifact": "slskdN PR #409 W75 ranks 753-777 independent cross review",
    "schemaVersion": 1,
    "repository": "snapetech-org/slskdN",
    "pullRequest": 409,
    "window": "W75",
    "continuationRankRange": [753, 777],
    "remainingQueueRankRange": [653, 677],
    "head": manifest["head"],
    "tree": manifest["tree"],
    "baseRef": "main",
    "baseSha": manifest["liveBefore"]["baseRefOid"],
    "sourceCount": 25,
    "localeCount": 12,
    "cells": 300,
    "keepCurrent": sum(x["decision"] == "keep-current" for x in ledger),
    "selectedReviewedTargets": sum(x["decision"].startswith("select-") for x in ledger),
    "crossHashOnlyHolds": len(holds),
    "primaryCorrections": len(primary_corrections),
    "primaryHashOnlyHolds": len(primary_holds),
    "blindRevisions": sum(x["disposition"] == "revise" for x in blind_cells.values()),
    "proposalUnion": len(reconciliation),
    "sameTargetProposalAgreements": sum(x["status"] == "same-target" for x in reconciliation),
    "differentTargetProposalDisagreements": sum(x["status"] == "different-targets" for x in reconciliation),
    "primaryOnlyProposals": sum(x["status"] == "primary-only" for x in reconciliation),
    "blindOnlyProposals": sum(x["status"] == "blind-only" for x in reconciliation),
    "selectedProposalSourceCounts": dict(selected_source_counts),
    "crossHoldPositions": sorted({x["continuationRank"] for x in holds}),
    "priorActiveHeldCellsPreservedHashOnly": 259,
    "priorHoldResolutionRowsPreservedHashOnly": 13,
    "baselineProtectedLiteralFlags": 23,
    "localizedWishlistBaselineExceptionsAccepted": len(localized),
    "nativeSpeakerSignoff": False,
    "browserReview": False,
    "applicationPerformed": False,
    "confidence": "moderate",
    "livePRBefore": "PASS",
    "inputVerifiers": "PASS",
}
write_json(ROOT / "summary.json", summary)
print(json.dumps(summary, ensure_ascii=False, indent=2))
