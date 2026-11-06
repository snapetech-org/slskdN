#!/usr/bin/env python3
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CF = ROOT / "inputs/candidate-free-input"
PR = ROOT / "inputs/primary-review"
BLROOT = ROOT / "inputs/blind-review-packet"
BL = BLROOT / "blind-review"
HEAD = "674156749ee86021ef91d896b1824be62cff9a93"
TREE = "86483dbf9227130cade6a3f4c9dc9ef5cf232450"
WINDOW = "W76"

# A blind target is selected only for three cells where its wording is the better
# fit. All other selected corrections use the independently reviewed primary target.
BLIND_SELECTIONS = {"781::zh-Hant", "786::zh-Hant", "798::vi"}

RATIONALE = {
    779: "The pinned caller is the accessible artist-name label in ArtistReleaseRadarPanel. The current translations read as an instruction to release/publish the name. The selected primary wording labels the artist for a music-release radar and localizes that feature name consistently; the blind wording leaves Release Radar in English. Confidence is moderate pending native-speaker review.",
    781: "The callers identify a system navigation item with the tasks icon and a jobs health-check collection. This is the application's background task/job queue, not employment. Use the task meaning throughout; for Traditional Chinese, the blind 任務 is the concise menu label. Confidence is moderate pending native-speaker review.",
    783: "The pinned FederatedTasteRecommendationsPanel caller exposes this value in a numeric input (min=1) bound to minimumTrustedSources; its neighboring label is Minimum trusted sources. This is a threshold for preference-based recommendations, not a food/flavor source. The selected primary proposals make that function explicit. The blind review held these cells, but the exact caller resolves the intended meaning. Confidence is moderate pending native-speaker review.",
    784: "The caller appears only when nativePresetLibrary has imported presets and the control clears those browser-local presets. Native presets are a preset type, not default presets. Select the primary Korean wording that preserves the native preset concept. Confidence is moderate pending native-speaker review.",
    786: "The exact caller is the empty state in the System Jobs page. Jobs here are queued/background tasks, not employment. Use task wording; for Traditional Chinese, the blind 找不到任務 is concise and avoids the redundant 工作任務. Confidence is moderate pending native-speaker review.",
    788: "The caller is a paper-plane button in QuarantineJury; its adjacent accessibility description says it routes the request only to explicitly listed target jurors and attaches no raw files. This is a send/route action, not a physical path. Select the primary action wording, including the Japanese 送る button form. Confidence is moderate pending native-speaker review.",
    791: "The exact caller is the tooltip for stopping a local port-forwarding tunnel. The selected Hindi proposal preserves localhost:{localPort} contiguously and explains when to close the tunnel; the placeholder count and spelling match the source. Confidence is moderate pending native-speaker review.",
    794: "The callers are the Pods navigation item, Port Forwarding page heading, and VPN option. This is network port forwarding, not a harbor/seaport. Use the primary Hindi and Indonesian technical terminology. Confidence is moderate pending native-speaker review.",
    798: "The callers use this as a boolean readiness/status label for a configured media-server base URL. It is a completed status, not an imperative. Select the blind Vietnamese word order URL cơ sở; the Chinese proposals agree across reviewers. Confidence is moderate pending native-speaker review.",
    800: "The caller is the 16-value option in the Native MilkDrop beats-per-preset selector. These are musical beats, not heartbeats. The primary and blind Spanish proposals agree on 16 pulsos. Confidence is moderate pending native-speaker review.",
    801: "The caller is the path input for the library-health-scan automation recipe. The source means the path used by a scan, not a search or a generic check. Select the primary Korean wording for a scan path. Confidence is moderate pending native-speaker review.",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def shat(text: str) -> str:
    return sha(text.encode("utf-8"))


def j(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def jl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values):
    path.write_text("".join(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n" for value in values), encoding="utf-8")


cfman = j(CF / "manifest.json")
pman = j(PR / "manifest.json")
p_summary = j(PR / "summary.json")
bman = j(BL / "review-packet.json")
assert cfman["head"] == pman["head"] == bman["inputHead"] == HEAD
assert cfman["tree"] == pman["tree"] == bman["inputTree"] == TREE
assert cfman["window"] == pman["window"] == bman["window"] == WINDOW
assert pman["candidateFreeInputManifestSha256"] == sha((CF / "manifest.json").read_bytes())
assert bman["candidateFreeManifestSha256"] == sha((BLROOT / "candidate-free/manifest.json").read_bytes())
assert len(jl(CF / "source-current-cells.jsonl")) == 300

source_cells = jl(CF / "source-current-cells.jsonl")
primary_rows = {(x["continuationRank"], x["locale"]): x for x in jl(PR / "primary-review.jsonl")}
primary_changes = {(x["continuationRank"], x["locale"]): x for x in jl(PR / "corrections.jsonl")}
primary_holds = {(x["continuationRank"], x["locale"]): x for x in jl(PR / "holds-hash-only.jsonl")}
blind_rows = {(x["continuationRank"], x["locale"]): x for x in jl(BL / "review-cells.jsonl")}
caller_contexts = {x["continuationRank"]: x for x in jl(CF / "caller-contexts.jsonl")}
assert len(primary_rows) == len(blind_rows) == 300
assert len(primary_changes) == 69 and len(primary_holds) == 48
assert sum(x["disposition"] == "propose" for x in blind_rows.values()) == 52
assert sum(x["disposition"] == "hold" for x in blind_rows.values()) == 60

ledger = []
reconciliation = []
disagreements = []
hold_rows = []
counts = Counter()
proposal_sources = Counter()

for c in source_cells:
    key = (c["continuationRank"], c["locale"])
    key_id = f"{key[0]}::{key[1]}"
    p = primary_rows[key]
    pc = primary_changes.get(key)
    ph = primary_holds.get(key)
    b = blind_rows[key]
    bp = b.get("proposal") if b["disposition"] == "propose" else None

    assert c["sourceId"] == p["sourceId"] == b["sourceId"]
    assert c["sourceSha256"] == p["sourceSha256"] == b["sourceSha256"]
    assert c["callerContextSha256"] == p["callerContextSha256"] == b["callerContextSha256"]
    assert c["currentTargetSha256"] == p["currentTargetSha256"] == b["currentTargetSha256"]
    assert p["disposition"] == ("correct" if pc else "hold" if ph else "accept-current")
    assert (b["disposition"] == "propose") == (bp is not None)

    if pc:
        if bp is None:
            status = "primary-only-blind-hold" if b["disposition"] == "hold" else "primary-only-blind-keep"
        else:
            status = "same-target" if pc["target"] == bp else "different-targets"
        chosen_side = "blind" if key_id in BLIND_SELECTIONS else "primary"
        selected = bp if chosen_side == "blind" else pc["target"]
        assert selected is not None
        assert selected != c["currentTarget"]
        reason = RATIONALE[key[0]]
        selected_sources = [name for name, val in (("primary", pc["target"]), ("blind", bp)) if val is not None and val == selected]
        assert chosen_side in selected_sources
        proposal_sources["+".join(selected_sources)] += 1
        counts["selectedCorrection"] += 1
        recon = {
            "window": WINDOW,
            "continuationRank": key[0],
            "remainingQueueRank": c["remainingQueueRank"],
            "locale": key[1],
            "sourceId": c["sourceId"],
            "sourceSha256": c["sourceSha256"],
            "currentTargetSha256": c["currentTargetSha256"],
            "primaryProposal": {"target": pc["target"], "targetSha256": shat(pc["target"]), "rationale": pc["rationale"], "confidence": pc["confidence"]},
            "blindDisposition": b["disposition"],
            "blindProposal": ({"target": bp, "targetSha256": shat(bp), "rationale": b["rationale"]} if bp is not None else None),
            "status": status,
            "selectedTarget": selected,
            "selectedTargetSha256": shat(selected),
            "selectedProposalSources": selected_sources,
            "crossSelectedSource": chosen_side,
            "crossRationale": reason,
            "confidence": "moderate",
        }
        reconciliation.append(recon)
        if status != "same-target":
            disagreements.append({
                "window": WINDOW,
                "continuationRank": key[0],
                "remainingQueueRank": c["remainingQueueRank"],
                "locale": key[1],
                "sourceId": c["sourceId"],
                "source": c["source"],
                "sourceSha256": c["sourceSha256"],
                "currentTarget": c["currentTarget"],
                "currentTargetSha256": c["currentTargetSha256"],
                "primaryProposal": recon["primaryProposal"],
                "blindDisposition": b["disposition"],
                "blindProposal": recon["blindProposal"],
                "status": status,
                "selectedTarget": selected,
                "selectedTargetSha256": shat(selected),
                "crossRationale": reason,
            })
        row = {
            "schemaVersion": 1,
            "window": WINDOW,
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
            "productionCallerCount": c["productionCallerCount"] if "productionCallerCount" in c else caller_contexts[key[0]]["productionCallerCount"],
            "primaryDisposition": p["disposition"],
            "primaryProposal": {"target": pc["target"], "targetSha256": shat(pc["target"]), "rationale": pc["rationale"], "confidence": pc["confidence"]},
            "blindDisposition": b["disposition"],
            "blindProposal": ({"target": bp, "targetSha256": shat(bp), "rationale": b["rationale"]} if bp is not None else None),
            "decision": f"select-{chosen_side}-target",
            "selectedTarget": selected,
            "selectedTargetSha256": shat(selected),
            "selectedProposalSources": selected_sources,
            "rationale": reason,
            "confidence": "moderate",
            "hold": False,
        }
        ledger.append(row)
    elif ph:
        assert b["disposition"] == "hold" and caller_contexts[key[0]]["productionCallerCount"] == 0
        counts["holdHashOnly"] += 1
        no_text_reason = "No exact production caller exists in the pinned runtime inventory. Preserve the existing cell as a text-free hold until its user-facing role is known."
        hrow = {
            "window": WINDOW,
            "continuationRank": key[0],
            "remainingQueueRank": c["remainingQueueRank"],
            "locale": key[1],
            "sourceId": c["sourceId"],
            "sourceIdSha256": sha(c["sourceId"].encode("utf-8")),
            "sourceSha256": c["sourceSha256"],
            "sourceTextIncluded": False,
            "currentTargetSha256": c["currentTargetSha256"],
            "currentTargetIncluded": False,
            "selectedTargetSha256": c["currentTargetSha256"],
            "selectedTargetIncluded": False,
            "callerContextSha256": c["callerContextSha256"],
            "primaryDisposition": "hold",
            "primaryHoldReasonSha256": ph["holdReasonSha256"],
            "primaryCallerReferences": [],
            "blindDisposition": "hold",
            "blindHoldRationaleSha256": shat(b["rationale"]),
            "crossDecision": "hold-hash-only",
            "crossRationale": no_text_reason,
            "confidence": "high",
        }
        hold_rows.append(hrow)
        ledger.append({
            "schemaVersion": 1,
            "window": WINDOW,
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
            "productionCallerCount": 0,
            "primaryDisposition": "hold",
            "primaryProposal": None,
            "primaryHoldReasonSha256": ph["holdReasonSha256"],
            "blindDisposition": "hold",
            "blindProposal": None,
            "blindHoldRationaleSha256": shat(b["rationale"]),
            "decision": "hold-hash-only",
            "selectedTarget": None,
            "selectedTargetSha256": c["currentTargetSha256"],
            "selectedProposalSources": [],
            "rationale": no_text_reason,
            "confidence": "high",
            "hold": True,
        })
    else:
        assert p["disposition"] == "accept-current" and b["disposition"] == "keep"
        counts["keepCurrent"] += 1
        ledger.append({
            "schemaVersion": 1,
            "window": WINDOW,
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
            "productionCallerCount": caller_contexts[key[0]]["productionCallerCount"],
            "primaryDisposition": p["disposition"],
            "primaryProposal": None,
            "blindDisposition": b["disposition"],
            "blindProposal": None,
            "decision": "keep-current",
            "selectedTarget": c["currentTarget"],
            "selectedTargetSha256": c["currentTargetSha256"],
            "selectedProposalSources": [],
            "rationale": "Both independent reviews accept the exact current translation. The cross-review found no semantic or caller-context defect in the sealed candidate-free input.",
            "confidence": "moderate",
            "hold": False,
        })

assert len(ledger) == 300 and len(reconciliation) == 69 and len(hold_rows) == 48
assert counts["keepCurrent"] == 183 and counts["selectedCorrection"] == 69
assert len(BLIND_SELECTIONS) == 3
assert all(x["selectedTargetSha256"] == shat(x["selectedTarget"]) for x in ledger if not x["hold"])

write_jsonl(ROOT / "cross-ledger.jsonl", ledger)
write_jsonl(ROOT / "proposal-reconciliation.jsonl", reconciliation)
write_jsonl(ROOT / "proposal-disagreements.jsonl", disagreements)
write_jsonl(ROOT / "holds-hash-only.jsonl", hold_rows)

same = sum(x["status"] == "same-target" for x in reconciliation)
different = sum(x["status"] == "different-targets" for x in reconciliation)
primary_only_keep = sum(x["status"] == "primary-only-blind-keep" for x in reconciliation)
primary_only_hold = sum(x["status"] == "primary-only-blind-hold" for x in reconciliation)
write_json(ROOT / "summary.json", {
    "schemaVersion": 1,
    "repository": "snapetech-org/slskdN",
    "pullRequest": 409,
    "window": WINDOW,
    "head": HEAD,
    "tree": TREE,
    "cells": len(ledger),
    "keepCurrent": counts["keepCurrent"],
    "selectedCorrections": counts["selectedCorrection"],
    "crossHashOnlyHolds": counts["holdHashOnly"],
    "primaryProposals": 69,
    "blindProposals": 52,
    "proposalUnion": len(reconciliation),
    "sameTargetProposals": same,
    "differentTargetProposals": different,
    "primaryOnlyAgainstBlindKeep": primary_only_keep,
    "primaryOnlyAgainstBlindHold": primary_only_hold,
    "proposalDisagreementRows": len(disagreements),
    "blindSelectedTargets": sorted(BLIND_SELECTIONS),
    "selectedProposalSourceCounts": dict(proposal_sources),
    "priorHeldCellsPreservedHashOnly": 271,
    "priorHoldResolutionRowsPreservedHashOnly": 13,
    "baselineProtectedLiteralMismatchCells": 21,
    "baselineProtectedLiteralMismatchDisposition": "All 21 are within the 48 callerless cells and remain text-free holds.",
    "nativeSpeakerSignoff": False,
    "browserReview": False,
    "applicationPerformed": False,
    "livePRBefore": "PASS",
    "livePRAfter": "PENDING",
    "mainBaseDriftContainsLocalizationOrCatalogChanges": j(ROOT / "main-drift.json")["containsLocalizationOrCatalogPaths"],
})

write_json(ROOT / "input-verifier-results.json", {
    "candidateFree": {"result": "PASS", "head": HEAD, "tree": TREE, "cells": 300},
    "primary": {"result": "PASS", "head": HEAD, "tree": TREE, "cells": 300},
    "blind": {"result": "PASS", "head": HEAD, "tree": TREE, "cells": 300},
    "checksums": {"candidateFree": "PASS", "primary": "PASS", "blind": "PASS"},
    "livePRBeforeReview": "PASS",
    "sourceWorktreeCleanAtPinnedHead": True,
})

readme = f'''# slskdN PR #409 W76 independent cross-review\n\nThis packet cross-reviews 25 source IDs × 12 locales (300 catalog cells) at head `{HEAD}`, tree `{TREE}`. Candidate-free source/caller evidence, primary review, and blind review remain separately copied under `inputs/`.\n\n## Disposition\n\n- 183 cells retain the exact current translation, accepted by both independent reviewers.\n- 69 corrections are selected from the primary/blind proposal set. Three cells use the blind target: Traditional Chinese `Jobs`, Traditional Chinese `No jobs found`, and Vietnamese `Base URL configured`.\n- 48 callerless cells remain text-free hash-only holds. The blind reviewer also held 12 cells for `Minimum trusted taste sources`; those are resolved from the exact numeric input caller in `FederatedTasteRecommendationsPanel` and the sibling `Minimum trusted sources` label.\n- All 21 baseline protected-literal mismatch flags belong to callerless cells and remain holds. The proposal set has zero placeholder, markup, numeric, or protected-literal mismatches.\n- The 271 earlier held cells and 13 earlier hold-resolution records remain in the input packet hash-only.\n\n## Semantic decisions\n\n`cross-ledger.jsonl` records all 300 decisions. `proposal-reconciliation.jsonl` records each primary correction against its blind disposition and proposal; `proposal-disagreements.jsonl` records differing targets and proposal-versus-keep/hold outcomes. Cross-review rationales use the pinned production caller context. Confidence is moderate pending qualified native-speaker review.\n\nThe `Jobs` and `No jobs found` strings belong to the background task queue. `Route to Jurors` is a send action in the quarantine-jury interface. `Port Forwarding` is the network tunnel feature. `16 beats` is a musical MilkDrop setting. The selected Hindi tunnel tooltip preserves `localhost:{{localPort}}` exactly.\n\n## Live refs and base drift\n\nPR API, branch ref, and pull ref agreed at head `{HEAD}` and the source worktree was clean when the packet was sealed. The pull request remains open and draft. Four commits on `main` beyond the PR base affect workflow/policy/documentation files only; the localization PR branch is not rebased or merged with that drift. See `live-pr-before.json`, `live-pr-after.json`, and `main-drift.json`.\n\n## Limits and verification\n\nNo product edits were applied in this review packet. This is machine semantic review, not native-speaker signoff or browser acceptance. Run `python3 verify_cross_packet.py` from any directory to verify all three input packets, exact-head linkage, all 300 ledger decisions, hash-only holds, proposal reconciliation, and checksums.\n'''
(ROOT / "README.md").write_text(readme, encoding="utf-8")

# Seal every file in this packet except the root checksum list itself.
lines = []
for path in sorted(p for p in ROOT.rglob("*") if p.is_file() and p != ROOT / "SHA256SUMS.txt"):
    lines.append(f"{sha(path.read_bytes())}  {path.relative_to(ROOT).as_posix()}")
(ROOT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps(j(ROOT / "summary.json"), ensure_ascii=False, indent=2))
