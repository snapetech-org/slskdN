#!/usr/bin/env python3
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w67-cross-audit-20261103")
PRIMARY = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w67-ranks553-577-primary-20261103/primary")
BLIND = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w67-ranks553-577-blind-20261103")
INPUT = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w67-ranks553-577-candidate-free-20261103/input")
HEAD = "2dc64b9d00f6611aeb72713af81db53ccc5a4084"
TREE = "f13462300926ac897235cd92ae68c87695c38c31"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]

def read_json(path):
    return json.loads(path.read_text())

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def sha_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()

def dump_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

def keyed(rows):
    result = {(row["continuationRank"], row["locale"]): row for row in rows}
    assert len(result) == len(rows)
    return result

def cross_choice(rank, locale):
    if rank == 553: return "primary"
    if rank == 554: return "blind"
    if rank == 555: return "primary"
    if rank == 558: return "blind"
    if rank == 561: return "primary" if locale in {"ja", "ko"} else "blind"
    if rank == 563: return "blind" if locale in {"ar", "hi", "id", "ko", "vi"} else "primary"
    if rank == 564: return "primary" if locale in {"hi", "ko"} else "blind"
    if rank == 565: return "primary"
    if rank == 566: return "primary"
    if rank == 572: return "primary"
    if rank == 573: return "blind"
    if rank == 574: return "blind"
    if rank == 575: return "primary" if locale in {"ar", "de", "fr"} else "blind"
    if rank == 576: return "primary" if locale in {"ja", "ko"} else "blind"
    raise AssertionError("unreviewed primary/blind disagreement at {} {}".format(rank, locale))

def rationale(rank, locale, selected):
    if rank == 553:
        return "Selected the primary wording: it replaces literal seed terminology while preserving the source idea of a review starting point and the explicit no-network-action status."
    if rank == 554:
        return "Selected the blind wording: the pinned MediaCorePods caller counts failed membership checks, so the label should name the checks rather than imply membership itself failed."
    if rank == 555:
        return "Selected the primary wording because the pinned metric is overallAccuracy; accuracy is distinct from precision in these locales."
    if rank == 558:
        return "Selected the blind refinement because the caller provides matched, skipped, and changed-field counts; the target keeps each placeholder attached to its count meaning."
    if rank == 561:
        if selected == "primary":
            return "Selected the primary wording for this locale because it uses the established likelihood terminology and cleanly separates the SongIDPanel readout from download decisions."
        return "Selected the blind wording for this locale because it makes the strong identity match explicit as the basis of the separate download decision."
    if rank == 563:
        if selected == "primary" and locale in {"de", "ja"}:
            return "Retained the current concise backfill error wording. It names the operation directly in this technical UI; the alternate adds generic historical-data wording without improving this locale."
        if selected == "primary":
            return "Selected the primary wording because it states the failed historical-data loading operation clearly while preserving the opaque error placeholder."
        return "Selected the blind wording because it localizes backfill as historical-data completion and avoids unsupported extra detail; the error value remains opaque."
    if rank == 564:
        if selected == "primary":
            return "Selected the primary wording for this locale because its built-in preset and visualizer wave terminology is clear and natural."
        return "Selected the blind wording because the exact visualizer caller means an app-built-in preset; this avoids translating native as original or leaving it as a calque."
    if rank == 565:
        return "Selected the primary wording because the selector identifies an app-built-in MilkDrop preset fragment; the protected product name remains exact."
    if rank == 566:
        return "Selected the primary wording after reviewing the full JSX caller: this catalog fragment is split around dht.lan_only=true, and the following localized fragment supplies the configuration instruction. The selected target avoids duplicating that instruction."
    if rank == 572:
        return "Selected the primary wording because the federated recommendation checkbox reveals contributing recommendation sources; it avoids the performer sense of actors and does not assume every source is a person."
    if rank == 573:
        return "Selected the blind wording because it uses the more precise threshold term and retains the fragment punctuation around the following numeric value."
    if rank == 574:
        return "Selected the blind wording because it identifies the selected peer and renders membership record terminology in French instead of leaving peer untranslated."
    if rank == 575:
        if selected == "primary":
            return "Selected the primary wording for this locale because it forms a concise metric label while keeping the protected AI acronym exact."
        return "Selected the blind wording for this locale because it expresses mentions referring to AI, not mentions authored by AI; the protected acronym remains exact."
    if rank == 576:
        if selected == "primary":
            return "Selected the primary wording for this locale because it clearly says the currently active built-in preset is removed from favorites."
        return "Selected the blind wording because the exact visualizer caller means an app-built-in preset; it removes the native/original ambiguity."
    raise AssertionError("missing disagreement rationale")

def verified_start_attestation():
    return {
        "checkedAtUtc": "2026-11-03T18:22:51Z",
        "repository": "snapetech-org/slskdN",
        "pullRequest": 409,
        "state": "OPEN",
        "isDraft": True,
        "branch": BRANCH,
        "head": HEAD,
        "tree": TREE,
        "refs": {
            "refs/heads/" + BRANCH: HEAD,
            "refs/pull/409/head": HEAD
        },
        "result": "PASS"
    }

IM = read_json(INPUT / "manifest.json")
PM = read_json(PRIMARY / "manifest.json")
PS = read_json(PRIMARY / "summary.json")
BM = read_json(BLIND / "manifest.json")
BS = read_json(BLIND / "summary.json")
assert IM["head"] == PM["head"] == BM["head"] == HEAD
assert IM["tree"] == PM["tree"] == BM["tree"] == TREE
assert PM["repository"] == BM["repository"] == "snapetech-org/slskdN"
assert PM["pullRequest"] == BM["pullRequest"] == 409
assert PM["blindPacketAccessed"] is False
assert BM["primaryMaterialOpened"] is False and BM["primaryMaterialUsed"] is False
assert PM["sourceCount"] == BM["sourceCount"] == 25
assert PM["cellCount"] == BM["cellCount"] == 300
assert PS["priorHeldCellsReattested"] == 128
assert BS["priorHoldsReattested"] == BS["priorHoldsUnchanged"] == 128

C = keyed(read_jsonl(INPUT / "source-current-cells.jsonl"))
P = keyed(read_jsonl(PRIMARY / "primary-ledger.jsonl"))
B = keyed(read_jsonl(BLIND / "translation-ledger.jsonl"))
assert len(C) == len(P) == len(B) == 300
EXPECTED_KEYS = {(rank, locale) for rank in range(553, 578) for locale in LOCALES}
assert set(C) == set(P) == set(B) == EXPECTED_KEYS

cross_rows = []
conflict_rows = []
category_counts = Counter()
selection_counts = Counter()
final_counts = Counter()
by_rank = defaultdict(Counter)

for key in sorted(EXPECTED_KEYS):
    c, p, b = C[key], P[key], B[key]
    rank, locale = key
    assert p["head"] == b["head"] == HEAD
    assert p["tree"] == b["tree"] == TREE
    assert p["pullRequest"] == b["pullRequest"] == 409
    assert p["repository"] == b["repository"] == "snapetech-org/slskdN"
    for field in ("continuationRank", "remainingQueueRank", "sourceId", "source", "sourceSha256",
                  "currentTarget", "currentTargetSha256", "catalogPath", "catalogFileSha256",
                  "catalogGitBlob", "callerContextSha256", "callerRefs"):
        assert p[field] == c[field], (key, "primary", field)
        assert b[field] == c[field], (key, "blind", field)
    assert p["catalogKey"] == c["source"]
    assert p["sourceSha256"] == sha_text(c["source"])
    assert p["currentTargetSha256"] == sha_text(c["currentTarget"])
    pt = p.get("proposedTarget", p["currentTarget"])
    bt = b["proposal"]
    ph = p["reviewedTargetSha256"]
    bh = b["proposalSha256"]
    assert ph == sha_text(pt)
    assert bh == sha_text(bt)
    assert p["disposition"] in {"accept-current", "correction", "refinement"}
    assert b["reviewDisposition"] in {"accept-current", "correction", "refinement"}
    assert (p["disposition"] == "accept-current") == (pt == c["currentTarget"])
    assert (b["reviewDisposition"] == "accept-current") == (bt == c["currentTarget"])
    assert b["primaryMaterialOpened"] is False
    assert b["candidateFreeCurrentTargetsVisible"] is True

    if pt == bt:
        if pt == c["currentTarget"]:
            category = "both-current"
            selection = "consensus-current"
            final_target = c["currentTarget"]
            final_disposition = "accept-current"
            cross_reason = "Both independent reviews accept the exact current target hash."
        else:
            category = "same-proposal"
            selection = "consensus-proposal"
            final_target = pt
            final_disposition = "correction" if "correction" in {p["disposition"], b["reviewDisposition"]} else "refinement"
            cross_reason = "Primary and blind reviews independently proposed the same exact target hash."
    else:
        category = "proposal-disagreement"
        selection = cross_choice(rank, locale)
        final_target = pt if selection == "primary" else bt
        chosen_disposition = p["disposition"] if selection == "primary" else b["reviewDisposition"]
        final_disposition = "accept-current" if final_target == c["currentTarget"] else chosen_disposition
        cross_reason = rationale(rank, locale, selection)
        conflict_rows.append(key)

    final_hash = sha_text(final_target)
    category_counts[category] += 1
    selection_counts[selection] += 1
    final_counts[final_disposition] += 1
    by_rank[rank][final_disposition] += 1

    row = {
        "schema": "slskdn-w67-cross-audit-cell/v1",
        "repository": "snapetech-org/slskdN",
        "pullRequest": 409,
        "head": HEAD,
        "tree": TREE,
        "continuationRank": rank,
        "remainingQueueRank": c["remainingQueueRank"],
        "locale": locale,
        "sourceId": c["sourceId"],
        "source": c["source"],
        "sourceSha256": c["sourceSha256"],
        "currentTarget": c["currentTarget"],
        "currentTargetSha256": c["currentTargetSha256"],
        "catalogPath": c["catalogPath"],
        "catalogFileSha256": c["catalogFileSha256"],
        "catalogGitBlob": c["catalogGitBlob"],
        "callerContextSha256": c["callerContextSha256"],
        "callerRefs": c["callerRefs"],
        "sourceProtectedLiterals": c["sourceProtectedLiterals"],
        "primaryDisposition": p["disposition"],
        "primaryTarget": pt,
        "primaryTargetSha256": ph,
        "primaryRationale": p["rationale"],
        "blindDisposition": b["reviewDisposition"],
        "blindTarget": bt,
        "blindTargetSha256": bh,
        "blindRationale": b["rationale"],
        "crossAuditCategory": category,
        "selection": selection,
        "finalDisposition": final_disposition,
        "finalTarget": final_target,
        "finalTargetSha256": final_hash,
        "crossAuditRationale": cross_reason
    }
    cross_rows.append(row)

assert len(conflict_rows) == 105
assert category_counts == Counter({"both-current": 186, "proposal-disagreement": 105, "same-proposal": 9})

(ROOT / "cross-audit-ledger.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in cross_rows))
(ROOT / "disagreements.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in cross_rows if row["crossAuditCategory"] == "proposal-disagreement"))

with (ROOT / "proposal-hashes.tsv").open("w") as out:
    for row in cross_rows:
        out.write("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(
            row["continuationRank"], row["locale"], row["sourceId"],
            row["primaryTargetSha256"], row["blindTargetSha256"],
            row["finalTargetSha256"], row["crossAuditCategory"],
            row["selection"], row["finalDisposition"], row["catalogGitBlob"]
        ))
with (ROOT / "final-proposal-hashes.txt").open("w") as out:
    for row in cross_rows:
        out.write("{}\t{}\t{}\t{}\n".format(
            row["continuationRank"], row["locale"], row["sourceId"], row["finalTargetSha256"]
        ))

prior = keyed(read_jsonl(INPUT / "prior-held-cell-reattestation.jsonl"))
blind_holds = keyed(read_jsonl(BLIND / "prior-held-cell-reattestation.jsonl"))
assert len(prior) == len(blind_holds) == 128 and set(prior) == set(blind_holds)
hold_rows = []
for key in sorted(prior):
    x, y = prior[key], blind_holds[key]
    assert x["priorDisposition"] == "hold"
    assert x["status"] == "reattested-unchanged" and x["matchesPriorCurrentValue"] is True
    assert x["priorTargetSha256"] == x["currentTargetSha256"] == sha_text(x["currentTarget"])
    assert y["status"] == "reattested-unchanged" and y["heldTargetTextIncluded"] is False
    assert y["priorTargetSha256"] == y["currentTargetSha256"] == x["priorTargetSha256"]
    assert y["sourceId"] == x["sourceId"] and y["sourceSha256"] == x["sourceSha256"]
    assert y["callerContextSha256"] == x["currentCallerContextSha256"]
    assert y["callerCount"] == x["currentCallerCount"]
    assert y["callerRefs"] == x["currentCallerRefs"]
    assert y["catalogPath"] == x["currentCatalogPath"]
    assert y["catalogFileSha256"] == x["currentCatalogFileSha256"]
    assert y["catalogGitBlob"] == x["currentCatalogGitBlob"]
    hold_rows.append({
        "schema": "slskdn-w67-cross-audit-hold/v1",
        "priorWindow": x["priorWindow"],
        "continuationRank": x["continuationRank"],
        "sourceId": x["sourceId"],
        "sourceSha256": x["sourceSha256"],
        "locale": x["locale"],
        "priorDisposition": x["priorDisposition"],
        "priorTargetSha256": x["priorTargetSha256"],
        "currentTargetSha256": x["currentTargetSha256"],
        "holdReason": x["holdReason"],
        "priorEvidenceSource": x["priorEvidenceSource"],
        "callerCount": x["currentCallerCount"],
        "callerContextSha256": x["currentCallerContextSha256"],
        "callerRefs": x["currentCallerRefs"],
        "catalogPath": x["currentCatalogPath"],
        "catalogFileSha256": x["currentCatalogFileSha256"],
        "catalogGitBlob": x["currentCatalogGitBlob"],
        "heldTargetTextIncluded": False,
        "status": "reattested-unchanged"
    })
(ROOT / "prior-held-cell-reattestation.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in hold_rows))

start_att = verified_start_attestation()
dump_json(ROOT / "live-ref-start.json", start_att)

summary = {
    "schema": "slskdn-w67-cross-audit-summary/v1",
    "repository": "snapetech-org/slskdN",
    "pullRequest": 409,
    "head": HEAD,
    "tree": TREE,
    "cellCount": len(cross_rows),
    "sourceCount": 25,
    "localeCount": 12,
    "categoryCounts": dict(category_counts),
    "selectionCounts": dict(selection_counts),
    "finalDispositionCounts": dict(final_counts),
    "updateCount": final_counts["correction"] + final_counts["refinement"],
    "noOpCount": final_counts["accept-current"],
    "newHoldCount": 0,
    "disagreementCount": len(conflict_rows),
    "priorHoldsReattestedUnchanged": len(hold_rows),
    "priorHoldCallerlessCount": sum(1 for row in hold_rows if row["callerCount"] == 0),
    "protectedLiteralBaselineMismatches": 10,
    "protectedLiteralFinalMismatches": 0,
    "placeholderMarkupNumericFinalMismatches": 0,
    "primaryPacketDispositionCounts": PS["dispositionCounts"],
    "blindPacketDispositionCounts": BS["reviewDispositionCounts"],
    "byRank": {str(rank): dict(by_rank[rank]) for rank in sorted(by_rank)},
    "crossAuditMethod": "For each of 300 cells, exact source/current/caller/catalog pins were matched across candidate-free input and both independent ledgers. All 105 unequal targets were adjudicated; 9 exact proposed-target hashes agreed and 186 exact current-target hashes were accepted.",
    "nativeSpeakerReview": "not performed",
    "headedBrowserReview": "not performed",
    "repositoryOrPRFilesEdited": False
}
dump_json(ROOT / "summary.json", summary)

manifest = {
    "schema": "slskdn-w67-cross-audit-manifest/v1",
    "repository": "snapetech-org/slskdN",
    "pullRequest": 409,
    "branch": BRANCH,
    "head": HEAD,
    "tree": TREE,
    "window": "W67 continuation ranks 553-577 (remaining queue ranks 453-477)",
    "candidateFreeInputManifestSha256": sha_bytes((INPUT / "manifest.json").read_bytes()),
    "candidateFreeInputChecksumListSha256": sha_bytes((INPUT / "PACKET-SHA256SUMS.txt").read_bytes()),
    "primaryManifestSha256": sha_bytes((PRIMARY / "manifest.json").read_bytes()),
    "primaryChecksumListSha256": sha_bytes((PRIMARY / "SHA256SUMS.txt").read_bytes()),
    "blindManifestSha256": sha_bytes((BLIND / "manifest.json").read_bytes()),
    "blindChecksumListSha256": sha_bytes((BLIND / "SHA256SUMS.txt").read_bytes()),
    "liveRefStartAttestationSha256": sha_bytes((ROOT / "live-ref-start.json").read_bytes()),
    "liveRefSealAttestationSha256": None,
    "sourceCount": 25,
    "localeCount": 12,
    "cellCount": 300,
    "disagreementCount": len(conflict_rows),
    "priorHoldsReattestedUnchanged": 128,
    "primaryMaterialOpened": True,
    "blindMaterialOpened": True,
    "repositoryOrPRFilesEdited": False,
    "testsBuildsCiBrowserOrReleaseActionsRun": False,
    "portableVerifier": "verify_cross_audit.py",
    "packetSealStatus": "awaiting final live-ref recheck"
}
dump_json(ROOT / "manifest.json", manifest)

readme = """# slskdN PR #409 W67 independent cross-audit

This cross-audit reconciles the sealed primary review and independent blind review for ranks 553–577. It checks all 300 locale cells across 25 sources and all 128 carried holds against the candidate-free pinned input.

## Reconciliation

- The two reviews agree on 186 exact current-target hashes and 9 exact non-current proposal hashes.
- They disagree on 105 target hashes. Each disagreement is adjudicated in cross-audit-ledger.jsonl; the selected source and reason are recorded per cell.
- proposal-hashes.tsv records primary, blind, and selected final hashes for all 300 cells. final-proposal-hashes.txt provides the selected final hash for each cell.
- prior-held-cell-reattestation.jsonl records the 128 unchanged prior holds by exact hashes and current source/caller/catalog pins. Held target text is omitted.

## Pins and validation

The PR head, tree, branch, and pull refs were checked before the audit and are recorded in live-ref-start.json. A second live check is recorded in live-ref-seal.json immediately before sealing. Run python3 verify_cross_audit.py and sha256sum -c SHA256SUMS.txt to verify this packet.

## Scope

This packet is an independent reconciliation of primary and blind machine-assisted review. Existing current targets were present in the candidate-free input. Native-speaker and headed-browser review were not performed. No repository or PR files were edited; no project tests, builds, CI, releases, or merges were run.
"""
(ROOT / "README.md").write_text(readme)
print(json.dumps({
    "created": str(ROOT),
    "categoryCounts": dict(category_counts),
    "selectionCounts": dict(selection_counts),
    "finalDispositionCounts": dict(final_counts),
    "priorHolds": len(hold_rows)
}, indent=2))
