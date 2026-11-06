#!/usr/bin/env python3
"""Build the slskdN W82 cross-review from the three sealed review inputs."""
import argparse
import collections
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HEAD = "6e48a342d4b1c43918c23da3afcbaad19c87a005"
TREE = "b82ea7937cf9aa141a1c952283d5549dbe116ba5"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]

# These selections are reconciled from the pinned primary proposals and blind findings.
SELECTED = {
    (929, "es"): ("correction", "Máximo de elementos por importación", "Corrects the label's unnatural adjective/noun order while retaining the item limit and import scope."),
    (929, "id"): ("correction", "Jumlah maksimum item per impor", "Replaces an overly abbreviated settings label with the explicit maximum item count."),
    (929, "ko"): ("correction", "가져오기당 최대 항목 수", "Uses the software-import sense and states the maximum number of items."),
    (929, "vi"): ("refinement", "Số mục tối đa mỗi lần nhập", "Adds an explicit count noun to the existing concise limit label."),
    (936, "hi"): ("correction", "JWT कुंजी", "Restores the exact JWT protocol acronym required by the security setting."),
    (936, "zh-Hans"): ("correction", "JWT 密钥", "Restores the exact JWT protocol acronym required by the security setting."),
    (936, "zh-Hant"): ("correction", "JWT 金鑰", "Restores the exact JWT protocol acronym required by the security setting."),
    (938, "fr"): ("refinement", "Copier le plan", "The pinned control is an action button; the existing French reads as a copy plan noun phrase."),
    (938, "ja"): ("refinement", "プランをコピー", "The pinned control is an action button; the existing Japanese reads as a noun-like compound."),
    (939, "ar"): ("correction", "soulfind", "This value is an executable/command identifier; removes the unsupported package-like prefix."),
    (939, "de"): ("correction", "soulfind", "This value is an executable/command identifier and must remain literal."),
    (939, "es"): ("correction", "soulfind", "This value is an executable/command identifier and must remain literal."),
    (939, "fr"): ("correction", "soulfind", "This value is an executable/command identifier and must remain literal."),
    (939, "hi"): ("correction", "soulfind", "This value is an executable/command identifier and must remain literal."),
    (939, "id"): ("correction", "soulfind", "This value is an executable/command identifier and must remain literal."),
    (939, "ja"): ("correction", "soulfind", "This value is an executable/command identifier and must remain literal."),
    (939, "ko"): ("correction", "soulfind", "This value is an executable/command identifier and must remain literal."),
    (939, "pt-BR"): ("correction", "soulfind", "This value is an executable/command identifier and must remain literal."),
    (939, "vi"): ("correction", "soulfind", "This value is an executable/command identifier and must remain literal."),
    (939, "zh-Hans"): ("correction", "soulfind", "This value is an executable/command identifier and must remain literal."),
    (939, "zh-Hant"): ("correction", "soulfind", "This value is an executable/command identifier and must remain literal."),
    (941, "ar"): ("correction", "النشر عبر PodCore DHT", "Restores the exact PodCore product name and expresses publication through its DHT."),
    (941, "es"): ("correction", "Publicación en PodCore DHT", "Keeps PodCore intact and corrects the noun order in the heading."),
    (941, "fr"): ("correction", "Publication sur PodCore DHT", "Keeps PodCore intact and corrects the noun order in the heading."),
    (941, "hi"): ("correction", "PodCore DHT पर प्रकाशन", "Restores the exact PodCore product name in the heading."),
    (941, "ko"): ("correction", "PodCore DHT 게시", "Restores the exact PodCore product name in the heading."),
    (945, "de"): ("refinement", "Audioausgabe auswählen", "Uses a natural concise German action label for the output chooser."),
    (947, "ar"): ("correction", "انقل هذا المقطع إلى موضع أسبق في قائمة الانتظار.", "The player caller is a music track and the operation moves it to an earlier queue position, not an earlier time."),
    (950, "ar"): ("correction", "وضع علامة كمُشاهَد", "The current Arabic says that a mark was displayed; the control marks results as viewed."),
    (950, "es"): ("correction", "Marcar como visto", "Makes explicit that the action marks results as viewed."),
    (951, "id"): ("correction", "Coba kirim ulang status pemutaran saat ini untuk ruang ini setelah pembaruan gagal.", "Repairs word order and describes retrying the room playback-state update."),
    (951, "vi"): ("correction", "Thử gửi lại trạng thái phát hiện tại của phòng này sau khi cập nhật thất bại.", "Uses the broadcast/send sense of publishing state, rather than publishing an edition."),
    (952, "ja"): ("correction", "運用", "The health-check section covers runtime operations; 運営 suggests managing an organization."),
    (952, "vi"): ("correction", "Vận hành", "Names operational/runtime checks more precisely than the broad word for activity."),
}

HOLDS = {
    (944, locale): ("callerless_context_unresolved", "The pinned source has zero production callers; keep this cell text-free and unchanged.")
    for locale in LOCALES
}
for locale in ("de", "fr", "hi"):
    HOLDS[(950, locale)] = ("language_validation_pending", "The independent blind review could not clear this wording; retain it pending qualified language review.")

def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_text(value: str) -> str:
    return sha_bytes(value.encode("utf-8"))


def jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sums(path: Path):
    rows = {}
    for line in (path / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        rows[name.strip().lstrip("* ")] = digest
    for name, digest in rows.items():
        if sha_bytes((path / name).read_bytes()) != digest:
            raise ValueError(f"input checksum mismatch: {path}/{name}")
    return sha_bytes((path / "SHA256SUMS.txt").read_bytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-free", type=Path, required=True)
    ap.add_argument("--primary", type=Path, required=True)
    ap.add_argument("--blind", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    cf, primary, blind, out = [x.resolve() for x in (args.candidate_free, args.primary, args.blind, args.output)]
    cf_sums_sha = sums(cf)
    primary_sums_sha = sums(primary)
    blind_sums_sha = sums(blind)
    manifest = json.loads((cf / "manifest.json").read_text(encoding="utf-8"))
    pmanifest = json.loads((primary / "manifest.json").read_text(encoding="utf-8"))
    bmanifest = json.loads((blind / "blind-manifest.json").read_text(encoding="utf-8"))
    if (manifest["head"], manifest["tree"]) != (HEAD, TREE):
        raise ValueError("candidate-free anchor mismatch")
    if pmanifest["head"] != HEAD or pmanifest["tree"] != TREE or pmanifest["candidateFreeInputManifestSha256"] != sha_bytes((cf / "manifest.json").read_bytes()):
        raise ValueError("primary anchor/input mismatch")
    if bmanifest["head"] != HEAD or bmanifest["tree"] != TREE or bmanifest["inputManifestSha256"] != sha_bytes((cf / "manifest.json").read_bytes()):
        raise ValueError("blind anchor/input mismatch")
    cells = jsonl(cf / "source-current-cells.jsonl")
    p_rows = jsonl(primary / "primary-review.jsonl")
    proposals = jsonl(primary / "corrections.jsonl")
    b_rows = jsonl(blind / "blind-ledger.jsonl")
    key = lambda row: (row["continuationRank"], row["locale"])
    cm = {key(row): row for row in cells}
    pm = {key(row): row for row in p_rows}
    bm = {key(row): row for row in b_rows}
    prop = {key(row): row for row in proposals}
    expected = {(rank, locale) for rank in range(928, 953) for locale in LOCALES}
    if len(cells) != 300 or set(cm) != expected or set(pm) != expected or set(bm) != expected:
        raise ValueError("input rows do not form the exact 300-cell matrix")
    if len(prop) != 37 or set(prop) != {k for k, row in pm.items() if row["disposition"] == "correction"}:
        raise ValueError("primary proposals do not reconcile with the 37 corrections")
    if set(SELECTED) != set(prop) - {(950, "de"), (950, "fr"), (950, "hi")}:
        raise ValueError("cross-selected proposals do not reconcile with primary proposal set")
    if len(HOLDS) != 15:
        raise ValueError("expected 15 explicit holds")
    out.mkdir(parents=True, exist_ok=True)
    ledger = []
    for cell in sorted(cells, key=lambda x: (x["continuationRank"], LOCALES.index(x["locale"]))):
        k = key(cell)
        primary_row, blind_row = pm[k], bm[k]
        if primary_row["sourceSha256"] != cell["sourceSha256"] or primary_row["currentTargetSha256"] != cell["currentTargetSha256"]:
            raise ValueError(f"primary source/target pin mismatch: {k}")
        if blind_row["sourceSha256"] != cell["sourceSha256"] or blind_row["currentTargetSha256"] != cell["currentTargetSha256"]:
            raise ValueError(f"blind source/target pin mismatch: {k}")
        row = {
            "schemaVersion": 1,
            "continuationRank": cell["continuationRank"],
            "remainingQueueRank": cell["remainingQueueRank"],
            "sourceId": cell["sourceId"],
            "sourceSha256": cell["sourceSha256"],
            "locale": cell["locale"],
            "currentTargetSha256": cell["currentTargetSha256"],
            "callerCount": cell["callerCount"],
            "callerContextSha256": cell["callerContextSha256"],
            "primaryDisposition": primary_row["disposition"],
            "primaryProposalSha256": prop[k]["candidateTargetSha256"] if k in prop else None,
            "blindDisposition": blind_row["disposition"],
            "blindReasonCode": blind_row["reasonCode"],
            "sourceTextIncluded": False,
            "currentTargetTextIncluded": False,
            "selectedTargetTextIncluded": False,
            "crossRationale": None,
        }
        if k in HOLDS:
            reason_code, rationale = HOLDS[k]
            row.update({"crossDisposition": "hold", "crossReasonCode": reason_code, "selectedTarget": None, "selectedTargetSha256": None, "crossRationale": rationale})
            if k[0] == 944 and (cell["callerCount"] != 0 or blind_row["sourceTextIncluded"] or blind_row["currentTargetTextIncluded"]):
                raise ValueError("rank 944 must remain callerless and text-free in blind evidence")
        elif k in SELECTED:
            kind, target, rationale = SELECTED[k]
            candidate = prop[k]
            if candidate["candidateTarget"] != target:
                raise ValueError(f"selected value differs from primary proposal: {k}")
            if sha_text(target) != candidate["candidateTargetSha256"]:
                raise ValueError(f"selected target hash mismatch: {k}")
            row.update({"crossDisposition": kind, "crossReasonCode": "cross_review_selected_primary_proposal", "selectedTarget": target, "selectedTargetSha256": sha_text(target), "selectedTargetTextIncluded": True, "crossRationale": rationale})
        else:
            row.update({"crossDisposition": "accept-current", "crossReasonCode": "independent_reviews_clear_current_value", "selectedTarget": None, "selectedTargetSha256": None, "crossRationale": "The pinned source, caller context, current target, and both independent review ledgers provide no unresolved issue for this cell."})
        ledger.append(row)

    counts = collections.Counter(row["crossDisposition"] for row in ledger)
    if counts != {"accept-current": 251, "correction": 30, "refinement": 4, "hold": 15}:
        raise ValueError(f"unexpected cross disposition counts: {dict(counts)}")
    cross_path = out / "cross-ledger.jsonl"
    cross_path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in ledger), encoding="utf-8")
    selected_cells = [row for row in ledger if row["selectedTarget"] is not None]
    token_summary = {
        "candidateProtectedLiteralMismatches": 17,
        "additionalSoulfindPrefixSemanticIssue": 1,
        "affectedCells": 18,
        "placeholdersMarkupAndNumbers": "blind audit reports zero mismatches across all 300 cells",
        "literalGroups": {
            "JWT": {"rank": 936, "localeCount": 3},
            "soulfind": {"rank": 939, "localeCount": 12, "missing": 11, "unsupportedPrefix": 1},
            "PodCore": {"rank": 941, "localeCount": 3},
        },
    }
    summary = {
        "artifact": "slskdN PR #409 W82 cross-review",
        "schemaVersion": 1,
        "sealed": True,
        "sealedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repository": "snapetech-org/slskdN",
        "pullRequest": 409,
        "window": "W82",
        "head": HEAD,
        "tree": TREE,
        "continuationRankRange": [928, 952],
        "remainingQueueRankRange": [828, 852],
        "sourceCount": 25,
        "localeCount": 12,
        "cellCount": 300,
        "inputChecksumsSha256": {"candidateFree": cf_sums_sha, "primary": primary_sums_sha, "blind": blind_sums_sha},
        "inputManifestSha256": sha_bytes((cf / "manifest.json").read_bytes()),
        "primaryProposalCount": 37,
        "primaryBlindAgreement": {"sharedRevisions": 20, "primaryProposalsAcceptedAfterCrossReview": 14, "languageHolds": 3, "callerlessHolds": 12},
        "crossDispositionCounts": dict(sorted(counts.items())),
        "selectedChanges": len(selected_cells),
        "rootAdjudicationRequired": True,
        "nativeSpeakerValidationClaimed": False,
        "browserReviewClaimed": False,
        "sourceCatalogPrEditsMade": False,
        "testsBuildsScansCiRun": False,
        "workflowChanges": 0,
        "tokenFindings": token_summary,
        "rank944": {"callerCount": 0, "cells": 12, "disposition": "hold", "sourceTextIncluded": False, "currentTargetTextIncluded": False},
        "rank950LanguageHolds": {"locales": ["de", "fr", "hi"], "cells": 3, "sourceTextIncluded": False, "currentTargetTextIncluded": False, "qualifiedLanguageReviewPending": True},
        "nextWindow": {"continuationRanks": [953, 977], "remainingQueueRanks": [853, 877], "firstSourceId": "src_358f9860b3f4e247"},
        "ledgerSha256": sha_bytes(cross_path.read_bytes()),
        "ledgerCounts": dict(sorted(counts.items())),
    }
    (out / "cross-review-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files = [cross_path, out / "cross-review-summary.json", Path(__file__).resolve(), out / "verify_cross_review.py", out / "README.md"]
    checksum = "".join(f"{sha_bytes(path.read_bytes())}  {path.name}\n" for path in files if path.name != "SHA256SUMS.txt")
    (out / "SHA256SUMS.txt").write_text(checksum, encoding="utf-8")
    print(json.dumps({"result": "BUILT", "counts": dict(sorted(counts.items())), "selectedChanges": len(selected_cells), "ledgerSha256": summary["ledgerSha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
