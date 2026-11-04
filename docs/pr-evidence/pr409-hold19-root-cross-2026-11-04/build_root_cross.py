#!/usr/bin/env python3
"""Build a root reconciliation for the 19 reopened slskdN prior holds."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "input" / "candidate-free-input"
PRIMARY = ROOT / "primary-review" / "output" / "primary-review.jsonl"
BLIND = ROOT / "independent-blind" / "sealed-review" / "review-ledger.jsonl"
ANCHOR = ROOT / "input" / "terminology-anchor.json"
OUT = ROOT / "cross-review"
HEAD = "03c73e7b6706d8a034d7a24d6984763134f61bac"
TREE = "fa3f2041bbc2d4bb4eb512c03e874db3dbf631a5"

MESSAGES = {
    "es": "La sincronización de elementos deseados aún no está lista; no se ejecutó ninguna acción de Servarr.",
    "zh-Hans": "同步所需项目尚未就绪；尚未执行任何 Servarr 操作。",
    "hi": "वांछित आइटम का समन्वयन अभी तैयार नहीं है; Servarr की कोई कार्रवाई नहीं की गई।",
    "de": "Die Synchronisierung gewünschter Einträge ist noch nicht bereit; es wurde keine Servarr-Aktion ausgeführt.",
    "ja": "希望項目の同期はまだ準備できていません。Servarr の操作は実行されませんでした。",
    "fr": "La synchronisation des éléments souhaités n’est pas encore prête ; aucune action de Servarr n’a été exécutée.",
    "pt-BR": "A sincronização de itens desejados ainda não está pronta; nenhuma ação do Servarr foi executada.",
    "ar": "مزامنة العناصر المطلوبة غير جاهزة بعد؛ لم يتم تنفيذ أي إجراء من Servarr.",
    "ko": "원하는 항목 동기화가 아직 준비되지 않았습니다. Servarr 작업은 실행되지 않았습니다.",
    "zh-Hant": "同步所需項目尚未就緒；尚未執行任何 Servarr 操作。",
    "vi": "Việc đồng bộ các mục mong muốn vẫn chưa sẵn sàng; chưa thực hiện thao tác nào của Servarr.",
    "id": "Sinkronisasi item yang diinginkan belum siap; tidak ada tindakan Servarr yang dijalankan.",
}


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main():
    sources = read_jsonl(INPUT / "source-current-cells.jsonl")
    primary_rows = read_jsonl(PRIMARY)
    blind_rows = read_jsonl(BLIND)
    anchor = json.loads(ANCHOR.read_text(encoding="utf-8"))
    key = lambda row: (row["continuationRank"], row["locale"])
    source_map = {key(row): row for row in sources}
    primary = {key(row): row for row in primary_rows}
    blind = {key(row): row for row in blind_rows}
    if any(len(mapping) != 19 for mapping in (source_map, primary, blind)):
        raise SystemExit("candidate-free, primary, and blind ledgers must have 19 unique cells")
    if set(source_map) != set(primary) or set(source_map) != set(blind):
        raise SystemExit("the three review inputs do not cover the same exact cells")
    if anchor["head"] != HEAD or anchor["tree"] != TREE or set(anchor["locales"]) != set(MESSAGES):
        raise SystemExit("terminology anchor pins or locale coverage differ")

    ledger = []
    counts = Counter()
    for cell in sorted(source_map):
        src, p, b = source_map[cell], primary[cell], blind[cell]
        rank, locale = cell
        if p["head"] != HEAD or p["tree"] != TREE or b["sourceId"] != src["sourceId"]:
            raise SystemExit(f"review pin/source mismatch at {cell}")
        if p["sourceId"] != src["sourceId"] or p["sourceSha256"] != src["sourceSha256"] or b["evidence"]["sourceSha256"] != src["sourceSha256"]:
            raise SystemExit(f"source identity mismatch at {cell}")
        if p["currentTarget"] != src["currentTarget"] or p["currentTargetSha256"] != src["currentTargetSha256"]:
            raise SystemExit(f"primary baseline mismatch at {cell}")
        if b["currentTarget"] != src["currentTarget"] or b["evidence"]["currentTargetSha256"] != src["currentTargetSha256"]:
            raise SystemExit(f"blind baseline mismatch at {cell}")

        base = {
            "continuationRank": rank,
            "remainingQueueRank": src["remainingQueueRank"],
            "locale": locale,
            "sourceId": src["sourceId"],
            "sourceSha256": src["sourceSha256"],
            "catalogPath": src["catalogPath"],
            "catalogKey": src["catalogKey"],
            "currentTargetSha256": src["currentTargetSha256"],
            "primaryDisposition": p["disposition"],
            "primaryProposal": p.get("target"),
            "independentBlindDisposition": b["disposition"],
            "independentBlindProposal": b.get("proposedTarget"),
            "crossReviewer": "root",
        }
        if rank == 409:
            target = MESSAGES[locale]
            term_row = anchor["locales"][locale]
            term = term_row["term"]
            if term.casefold() not in target.casefold() or "Servarr" not in target:
                raise SystemExit(f"rank-409 message does not reuse locale term or literal: {cell}")
            base.update({
                "source": src["source"],
                "sourceSha256": src["sourceSha256"],
                "currentTarget": src["currentTarget"],
                "primaryRationale": p["rationale"],
                "independentBlindRationale": b["rationale"],
                "selectedDisposition": "correction",
                "action": "update",
                "selectedFrom": "root-terminology-reconciliation",
                "selectedTarget": target,
                "selectedTargetSha256": digest(target),
                "establishedTerm": term,
                "establishedTermSha256": term_row["termSha256"],
                "selectionRationale": (
                    "The pinned caller checks supportsWantedPull and, when ready, invokes syncWanted(). "
                    "Earlier W7 evidence defines this localized feature as synchronizing wanted items into the Wishlist. "
                    "Both current proposals and the Arabic accepted value omit or misstate that established feature term, "
                    "so the root cross-review reuses it while preserving the not-ready and no-action status."
                ),
            })
        elif rank == 475:
            base.update({
                "source": src["source"],
                "currentTarget": src["currentTarget"],
                "primaryRationale": p["rationale"],
                "independentBlindRationale": b["rationale"],
                "selectedDisposition": "accept-current",
                "action": "no-op",
                "selectedFrom": "independent-agreement",
                "selectedTarget": src["currentTarget"],
                "selectedTargetSha256": digest(src["currentTarget"]),
                "selectionRationale": "Both independent reviewers accept the current Arabic label for the Format/Codec filter heading in its pinned search-filter caller.",
            })
        elif rank == 504:
            base.update({
                "source": None,
                "catalogKey": None,
                "catalogKeySha256": digest(src["catalogKey"]),
                "currentTarget": None,
                "primaryRationale": None,
                "independentBlindRationale": None,
                "selectedDisposition": "hold",
                "action": "hold",
                "selectedFrom": "root-semantic-hold",
                "selectedTarget": None,
                "selectedTargetSha256": None,
                "selectionRationale": "Retain the semantic hold. The generated reason maps a recording-related conflict but does not identify which product entity the subject refers to. The blind accept-current decision does not resolve that ambiguity. Source and translation text are intentionally omitted from this row.",
            })
        else:
            raise SystemExit(f"unexpected reopened rank: {rank}")
        counts[base["selectedDisposition"]] += 1
        ledger.append(base)

    if len(MESSAGES) != 12 or counts != {"correction": 12, "accept-current": 1, "hold": 6}:
        raise SystemExit(f"unexpected root cross counts: {counts}")
    OUT.mkdir(parents=True, exist_ok=True)
    ledger_path = OUT / "root-cross-ledger.jsonl"
    ledger_path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in ledger), encoding="utf-8")
    summary = {
        "repository": "snapetech-org/slskdN",
        "pullRequest": 409,
        "head": HEAD,
        "tree": TREE,
        "scope": "19 reopened prior holds across ranks 409, 475, and 504",
        "cells": len(ledger),
        "sourceIds": len({row["sourceId"] for row in ledger}),
        "primaryProposalCount": sum(row["disposition"] in ("correct", "refine") for row in primary_rows),
        "independentBlindProposalCount": sum(row.get("proposedTarget") is not None for row in blind_rows),
        "rootSelectedDispositionCounts": dict(sorted(counts.items())),
        "rank409TermReconciliations": 12,
        "rank475AcceptedCurrent": 1,
        "rank504TextFreeHolds": 6,
        "callerScopeCorrection": "all 19 cells reattested as caller-backed at the pinned tree; 1/1/2 production caller counts across source IDs",
        "terminologyAnchorPath": "input/terminology-anchor.json",
        "terminologyAnchorGitBlob": anchor["evidenceGitBlob"],
        "terminologyAnchorFileSha256": anchor["evidenceFileSha256"],
        "nativeSpeakerSignoff": "not claimed; confidence moderate pending fluent-speaker review",
        "browserAcceptance": "not performed at this exact head; deployments are zero",
        "catalogApplication": "pending",
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(
        "# slskdN PR #409 reopened prior holds — independent cross-review\n\n"
        f"Pinned head: {HEAD}\nPinned tree: {TREE}\n\n"
        "The packet reconciles the exact-head independent primary and clean-blind reviews for 19 reopened cells. All three source IDs now have pinned production callers; the initial callerless classification was incorrect.\n\n"
        "Root cross-review applies the repository’s earlier W7 terminology decision to all 12 rank-409 cells: the feature is synchronization of wanted items into the Wishlist, controlled by supportsWantedPull and executed through syncWanted(). The source-localized term is reused for each locale, followed by the not-ready and no-action status. Rank 475 Arabic is accepted by both reviewers. Six rank-504 cells remain text-free holds because the generated “recording subject” reason lacks enough domain context.\n\n"
        "No native-speaker signoff or exact-head browser acceptance is claimed. The PR remained open and draft with zero deployments when attested. Catalog application is pending.\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
