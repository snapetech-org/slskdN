#!/usr/bin/env python3
"""Verify the root cross-review for slskdN's 19 reopened prior holds."""
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "input" / "candidate-free-input"
PRIMARY = ROOT / "primary-review"
BLIND = ROOT / "independent-blind"
CROSS = ROOT / "cross-review"
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


def jl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run(args, cwd):
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode:
        raise ValueError("command failed: " + " ".join(args) + "\n" + result.stdout)
    return result.stdout


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main():
    run([sys.executable, str(INPUT / "verify_input.py")], INPUT)
    run([sys.executable, str(PRIMARY / "output" / "verify_primary.py")], PRIMARY / "output")
    run([sys.executable, str(BLIND / "sealed-review" / "verify_review.py")], BLIND / "sealed-review")
    for directory, manifest in (
        (INPUT, "PACKET-SHA256SUMS.txt"),
        (PRIMARY / "input", "PACKET-SHA256SUMS.txt"),
        (PRIMARY / "output", "SHA256SUMS.txt"),
        (BLIND / "input" / "input", "PACKET-SHA256SUMS.txt"),
        (BLIND / "sealed-review", "SHA256SUMS.txt"),
    ):
        run(["sha256sum", "-c", manifest], directory)

    manifest = json.loads((INPUT / "manifest.json").read_text(encoding="utf-8"))
    if manifest["head"] != HEAD or manifest["tree"] != TREE or manifest["candidateFree"] is not True:
        raise ValueError("candidate-free exact pins differ")
    sources = jl(INPUT / "source-current-cells.jsonl")
    primary_rows = jl(PRIMARY / "output" / "primary-review.jsonl")
    blind_rows = jl(BLIND / "sealed-review" / "review-ledger.jsonl")
    cross_rows = jl(CROSS / "root-cross-ledger.jsonl")
    key = lambda row: (row["continuationRank"], row["locale"])
    maps = [{key(row): row for row in rows} for rows in (sources, primary_rows, blind_rows, cross_rows)]
    if any(len(item) != 19 for item in maps) or not all(set(maps[0]) == set(item) for item in maps[1:]):
        raise ValueError("input and review packets do not cover the same 19 unique cells")
    anchor = json.loads((ROOT / "input" / "terminology-anchor.json").read_text(encoding="utf-8"))
    if anchor["head"] != HEAD or anchor["tree"] != TREE or set(anchor["locales"]) != set(MESSAGES):
        raise ValueError("term anchor pins or locale coverage differ")
    if anchor["termSourceId"] != "src_e2632921eacdad49" or anchor["termSource"] != "Wanted Pull":
        raise ValueError("unexpected terminology anchor source")
    summary = json.loads((CROSS / "summary.json").read_text(encoding="utf-8"))
    attestation = json.loads((CROSS / "PR-attestation.json").read_text(encoding="utf-8"))
    if attestation["headRefOid"] != HEAD or attestation["tree"] != TREE or attestation["state"] != "OPEN" or attestation["isDraft"] is not True or attestation["deploymentsForHead"] != []:
        raise ValueError("live PR/deployment attestation differs from review scope")

    dispositions = Counter()
    locales_409 = set()
    rank504 = 0
    for cell in sorted(maps[0]):
        src, p, b, x = (item[cell] for item in maps)
        rank, locale = cell
        for row in (p, b, x):
            if row["sourceId"] != src["sourceId"]:
                raise ValueError(f"source ID mismatch at {cell}")
        if p["sourceSha256"] != src["sourceSha256"] or b["evidence"]["sourceSha256"] != src["sourceSha256"]:
            raise ValueError(f"source hash mismatch at {cell}")
        if p["currentTarget"] != src["currentTarget"] or p["currentTargetSha256"] != src["currentTargetSha256"]:
            raise ValueError(f"primary current-target mismatch at {cell}")
        if b["currentTarget"] != src["currentTarget"] or b["evidence"]["currentTargetSha256"] != src["currentTargetSha256"]:
            raise ValueError(f"blind current-target mismatch at {cell}")
        if x["currentTargetSha256"] != src["currentTargetSha256"] or x["sourceSha256"] != src["sourceSha256"]:
            raise ValueError(f"cross hash mismatch at {cell}")

        if rank == 409:
            locales_409.add(locale)
            target = MESSAGES[locale]
            term_row = anchor["locales"][locale]
            term = term_row["term"]
            correction_rows = [item["sourceCorrectionRow"] for item in (term_row,)]
            correction = correction_rows[0]
            if correction["proposedTarget"] != term or correction["sourceSha256"] != anchor["termSourceSha256"]:
                raise ValueError(f"term anchor row mismatch at {locale}")
            if term.casefold() not in target.casefold() or x["selectedTarget"] != target or "Servarr" not in target:
                raise ValueError(f"root terminology target mismatch at {cell}")
            if x["selectedDisposition"] != "correction" or x["action"] != "update" or x["selectedFrom"] != "root-terminology-reconciliation":
                raise ValueError(f"rank-409 decision mismatch at {cell}")
            if x["source"] != src["source"] or x["currentTarget"] != src["currentTarget"]:
                raise ValueError(f"rank-409 text baseline mismatch at {cell}")
            if re.search(r"\{[^{}]+\}|<[^>]+>|\d", target):
                raise ValueError(f"unexpected placeholder/markup/number in selected text at {cell}")
        elif rank == 475:
            if locale != "ar" or x["selectedDisposition"] != "accept-current" or x["action"] != "no-op" or x["selectedTarget"] != src["currentTarget"]:
                raise ValueError(f"rank-475 acceptance mismatch at {cell}")
            if p["disposition"] != "accept-current" or b["disposition"] != "accept-current":
                raise ValueError("rank-475 reviewers did not agree to accept current")
        elif rank == 504:
            rank504 += 1
            if p["disposition"] != "hold" or b["disposition"] != "accept-current":
                raise ValueError(f"rank-504 source review dispositions mismatch at {cell}")
            for field in ("source", "catalogKey", "currentTarget", "primaryProposal", "independentBlindProposal", "primaryRationale", "independentBlindRationale", "selectedTarget", "selectedTargetSha256"):
                if x.get(field) is not None:
                    raise ValueError(f"rank-504 hold row exposes text: {cell} {field}")
            if x["selectedDisposition"] != "hold" or x["action"] != "hold":
                raise ValueError(f"rank-504 cross hold missing at {cell}")
            if "Recording subject conflict" in x["selectionRationale"]:
                raise ValueError(f"rank-504 hold rationale quotes source text: {cell}")
        else:
            raise ValueError(f"unexpected source rank {rank}")
        dispositions[x["selectedDisposition"]] += 1

    if locales_409 != set(MESSAGES) or rank504 != 6 or dispositions != {"correction": 12, "accept-current": 1, "hold": 6}:
        raise ValueError(f"unexpected root cross totals/locales: {dispositions}, {locales_409}, rank504={rank504}")
    if summary["cells"] != 19 or summary["rootSelectedDispositionCounts"] != dict(sorted(dispositions.items())):
        raise ValueError("root cross summary differs from ledger")
    if summary["terminologyAnchorFileSha256"] != anchor["evidenceFileSha256"] or summary["terminologyAnchorGitBlob"] != anchor["evidenceGitBlob"]:
        raise ValueError("summary terminology anchor pin differs")
    print(json.dumps({
        "result": "PASS",
        "head": HEAD,
        "tree": TREE,
        "cells": len(cross_rows),
        "rootDispositionCounts": dict(sorted(dispositions.items())),
        "rank409Locales": len(locales_409),
        "rank504TextFreeHolds": rank504,
        "terminologyAnchors": len(anchor["locales"]),
        "nativeSpeakerSignoff": "not claimed",
        "browserAcceptance": "not performed; deployments are zero",
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
