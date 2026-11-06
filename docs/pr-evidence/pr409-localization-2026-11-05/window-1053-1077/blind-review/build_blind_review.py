#!/usr/bin/env python3
"""Build an independent blind review using only the sealed candidate-free packet."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import unicodedata
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
INPUT = ROOT / "candidate-free"
HEAD = "ba692c15ca54942108cc9da37757f585969e6173"
TREE = "27c09a8fe24030f5bb0995d809794a9e4829dc64"
WINDOW = "W1053-W1077"

REVISIONS = {}
REVIEWS = {}

def revise(rank, locale, target, rationale, code, confidence="moderate"):
    REVISIONS[(rank, locale)] = {
        "target": target,
        "rationale": rationale,
        "issueCodes": [code],
        "confidence": confidence,
    }

def review(rank, locale, rationale, code, suggestion=None):
    REVIEWS[(rank, locale)] = {
        "rationale": rationale,
        "issueCodes": [code],
        "suggestion": suggestion,
    }

# Source position 1055 is the numeric setting labeled Mesh Permits/min in its caller.
for locale, target in {
    "ar": "الطلبات المسموح بها لكل دقيقة عبر بوابة Mesh",
    "de": "Zulässige Mesh-Gateway-Anfragen pro Minute",
    "es": "Solicitudes permitidas por minuto a través de la puerta de enlace Mesh",
    "fr": "Requêtes autorisées par minute via la passerelle Mesh",
    "hi": "Mesh गेटवे पर प्रति मिनट अनुमत अनुरोध",
    "id": "Jumlah permintaan yang diizinkan per menit melalui gateway Mesh",
    "ja": "Mesh ゲートウェイで毎分許可するリクエスト数",
    "ko": "Mesh 게이트웨이에서 분당 허용되는 요청 수",
    "pt-BR": "Solicitações permitidas por minuto pelo gateway Mesh",
    "vi": "Số yêu cầu được phép mỗi phút qua cổng Mesh",
    "zh-Hans": "Mesh 网关每分钟允许的请求数",
    "zh-Hant": "Mesh 閘道每分鐘允許的請求數",
}.items():
    revise(
        1055, locale, target,
        "The pinned caller exposes a numeric Mesh Permits/min field. The current wording can read as permissions or permits rather than a per-minute request allowance; make the quantity clear.",
        "RATE_LIMIT_UNIT_CLARITY",
    )

revise(1058, "ar", "التحقق من الواصف",
       "The caller describes verifying a descriptor signature and freshness. The current Arabic says description, which changes the technical object.",
       "TECHNICAL_TERM")
for locale, target in {
    "zh-Hans": "IP 地址,",
    "zh-Hant": "IP 位址,",
}.items():
    revise(1062, locale, target,
           "The caller counts tracked IP addresses. The current Chinese means intellectual property, not Internet Protocol addresses.",
           "IP_ADDRESS_MISTRANSLATION")
revise(1066, "es", "Salas de Soulseek coincidentes",
       "The caller is a messaging room-search result list. Habitaciones suggests physical rooms; salas is the chat-room sense.",
       "CHAT_ROOM_TERM")
revise(1066, "fr", "Salons Soulseek correspondants",
       "The caller is a messaging room-search result list. Pièces suggests rooms in a building; salons expresses chat rooms.",
       "CHAT_ROOM_TERM")
revise(1066, "ko", "일치하는 Soulseek 채팅방",
       "The caller is a messaging room-search result list. 객실 suggests guest rooms; 채팅방 makes the chat-room meaning explicit.",
       "CHAT_ROOM_TERM")
revise(1067, "ja", "実行契約の準備完了",
       "The caller uses this as an adapter execution-contract status. 約定契約 is redundant and does not clearly express execution.",
       "TECHNICAL_TERM")
revise(1067, "vi", "Hợp đồng thực thi đã sẵn sàng",
       "The caller uses this as an adapter execution-contract status. The current thi công wording means a construction contract.",
       "TECHNICAL_TERM")
for locale, target in {
    "ar": "فعّل رفع الملفات عبر FTP بعد اكتمال التنزيلات",
    "hi": "डाउनलोड पूरा होने के बाद FTP अपलोड सक्षम करें",
    "id": "Aktifkan upload FTP setelah unduhan selesai",
    "ja": "ダウンロード完了後のFTPアップロードを有効にする",
    "ko": "다운로드 완료 후 FTP 업로드 사용",
    "pt-BR": "Ativar uploads via FTP após a conclusão dos downloads",
    "vi": "Bật tải lên qua FTP sau khi tải xuống hoàn tất",
    "zh-Hans": "启用下载完成后的 FTP 上传",
    "zh-Hant": "啟用下載完成後的 FTP 上傳",
}.items():
    revise(1069, locale, target,
           "The caller describes enabling FTP uploads after completed downloads. The current wording is unclear about whether completion applies to the download or the upload; make the timing explicit and preserve FTP.",
           "COMPLETED_DOWNLOAD_UPLOAD_CLARITY")
revise(1070, "de",
       "Validieren Sie das aktuelle YAML und speichern Sie es in der Remote-Konfigurationsdatei.",
       "The current German uses den aktuellen YAML; the technical noun is used with das. The proposal also preserves the remote configuration destination.",
       "GERMAN_GRAMMAR")
revise(1071, "vi", "mã băm",
       "The caller shows a count of stored hash values. băm is the hashing action; mã băm names the values being counted.",
       "HASH_VALUE_TERM")

# Locale-specific terminology flags remain provisional for human locale review.
review(1054, "ar",
       "The source and caller identify a selected Pod entity. The current Arabic uses a generic group term; confirm whether Pod should remain the product term in this locale.",
       "PRODUCT_TERM_REVIEW",
       "يؤدي حظر الأعضاء وتغيير الأدوار إلى نشر حالة العضوية للـ Pod والنظير المحددين. تحقّق من سجل العضوية الحالي قبل تطبيق التغييرات.")
review(1054, "es",
       "The source and caller identify a selected Pod entity. The current Spanish uses the generic grupo; confirm whether Pod is the established product term in this locale.",
       "PRODUCT_TERM_REVIEW",
       "Prohibir a los miembros y cambiar roles publica el estado de membresía del Pod y el par seleccionados. Verifique el registro de membresía actual antes de aplicar los cambios.")
review(1054, "vi",
       "The source and caller identify a selected Pod entity. The current Vietnamese uses the generic nhóm; confirm the established localized product term.",
       "PRODUCT_TERM_REVIEW",
       "Việc cấm thành viên và thay đổi vai trò sẽ công bố trạng thái thành viên cho Pod và peer đã chọn. Xác minh hồ sơ thành viên hiện tại trước khi áp dụng thay đổi.")
review(1056, "ar",
       "The Arabic translation uses المجموعة for both the share group and the collection. The caller shows these are separate objects; confirm the established Arabic term for a user collection.",
       "COLLECTION_TERM_REVIEW")
review(1063, "zh-Hans",
       "The caller is the empty state for the Collections page. 收藏 can read as favorites; confirm the established Simplified Chinese term for a user-created collection.",
       "COLLECTION_TERM_REVIEW",
       "还没有收藏集")
review(1063, "zh-Hant",
       "The caller is the empty state for the Collections page. 收藏 can read as favorites; confirm the established Traditional Chinese term for a user-created collection.",
       "COLLECTION_TERM_REVIEW",
       "還沒有收藏集")
review(1071, "fr",
       "The caller counts hash values in the footer. hachages can name the hashing operation; confirm the preferred French term for the resulting values.",
       "HASH_VALUE_TERM_REVIEW",
       "Valeurs de hachage")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def token_signature(source: str, target: str):
    placeholders = lambda s: Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", s))
    tags = lambda s: Counter(re.findall(r"</?[A-Za-z][^>]*>", s))
    numbers = lambda s: ["".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in t) for t in re.findall(r"\d+", s)]
    protected = lambda s: sorted(set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", s)) | {x for x in ("slskdN", "PodCore", "Wishlist", "soulfind", "FFmpeg", "Lidarr") if x in s})
    sp, tp = placeholders(source), placeholders(target)
    st, tt = tags(source), tags(target)
    sn, tn = numbers(source), numbers(target)
    sl, tl = protected(source), protected(target)
    return {
        "placeholders": {"source": sorted(sp.elements()), "target": sorted(tp.elements()), "matches": sp == tp},
        "markup": {"source": sorted(st.elements()), "target": sorted(tt.elements()), "matches": st == tt},
        "numbers": {"source": sn, "target": tn, "sourcePreserved": all(tn.count(x) >= n for x, n in Counter(sn).items())},
        "protectedLiterals": {"source": sl, "target": tl, "missing": [x for x in sl if x not in target]},
    }


def caller_pins(ctx):
    return [
        {
            "path": caller["path"],
            "line": caller["line"],
            "lineText": caller["lineText"],
            "lineSha256": caller["lineSha256"],
            "contextStartLine": caller["context"][0]["line"],
            "contextEndLine": caller["context"][-1]["line"],
            "contextSha256": caller["contextSha256"],
            "fileSha256": caller["fileSha256"],
            "gitBlob": caller["gitBlob"],
            "literalOccurrenceCount": caller["literalOccurrenceCount"],
        }
        for caller in ctx["callers"]
    ]


def checksum_output():
    lines = []
    for path in sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"):
        lines.append(f"{sha256(path.read_bytes())}  {path.relative_to(OUT).as_posix()}")
    (OUT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    if OUT.exists() and any(p.name not in {"build_blind_review.py", "verify_blind_review.py"} for p in OUT.iterdir()):
        raise SystemExit(f"refusing to overwrite generated output in {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)

    manifest_in = read_json(INPUT / "manifest.json")
    summary_in = read_json(INPUT / "summary.json")
    if (manifest_in["head"], manifest_in["tree"]) != (HEAD, TREE):
        raise SystemExit("candidate-free exact-head/tree pin mismatch")
    if manifest_in["candidateFree"] is not True or manifest_in["reviewDecisionsIncluded"] is not False:
        raise SystemExit("input is not candidate-free")

    cells = read_jsonl(INPUT / "source-current-cells.jsonl")
    contexts = {r["continuationRank"]: r for r in read_jsonl(INPUT / "caller-contexts.jsonl")}
    if len(cells) != 300:
        raise SystemExit("expected exactly 300 current-cell rows")
    if len(REVISIONS) + len(REVIEWS) != len(set(REVISIONS) | set(REVIEWS)):
        raise SystemExit("overlapping review decisions")

    ledger = []
    counts = Counter()
    baseline_mismatches = Counter()
    suggested_mismatches = Counter({"placeholder": 0, "markup": 0, "numeric": 0, "protectedLiteral": 0})
    for current in cells:
        rank, locale = current["continuationRank"], current["locale"]
        source_included = current.get("sourceTextIncluded") is True
        target_included = current.get("currentTargetTextIncluded") is True
        if current.get("callerCount") == 0:
            if source_included or target_included or current.get("source") is not None or current.get("currentTarget") is not None:
                raise SystemExit(f"callerless cell unexpectedly includes text at {rank}/{locale}")
            if not current.get("candidateFreeHold") or not current.get("sourceTextOmittedForNoCallerHold") or not current.get("currentTargetOmittedForNoCallerHold"):
                raise SystemExit(f"callerless row is not a hash-only hold at {rank}/{locale}")
            row = {
                "window": "W1053-W1077",
                "head": HEAD,
                "tree": TREE,
                "continuationRank": rank,
                "remainingQueueRank": current["remainingQueueRank"],
                "sourceId": current["sourceId"],
                "sourceIdSha256": current["sourceIdSha256"],
                "sourceSha256": current["sourceSha256"],
                "locale": locale,
                "callerContextSha256": current["callerContextSha256"],
                "callerCount": 0,
                "catalogPath": current["catalogPath"],
                "catalogFileSha256": current["catalogFileSha256"],
                "catalogGitBlob": current["catalogGitBlob"],
                "currentTargetSha256": current["currentTargetSha256"],
                "proposalTextIncluded": False,
                "sourceTextIncluded": False,
                "currentTargetTextIncluded": False,
                "disposition": "hold",
                "status": "hold",
                "issueCodes": ["NO_PINNED_PRODUCTION_CALLER"],
                "rationale": "No pinned production caller exists for this source position. Preserve the exact cell as a hash-only hold without exposing source, current target, or proposal text.",
                "confidence": "unknown",
                "nativeSpeakerApproval": False,
            }
            ledger.append(row)
            counts["hold"] += 1
            continue

        if not source_included or not target_included:
            raise SystemExit(f"caller-backed cell missing text at {rank}/{locale}")
        if rank not in contexts:
            raise SystemExit(f"caller context missing at {rank}")
        ctx = contexts[rank]
        if ctx["source"] != current["source"] or ctx["sourceSha256"] != current["sourceSha256"] or ctx["callerContextSha256"] != current["callerContextSha256"]:
            raise SystemExit(f"source/caller context pin mismatch at {rank}/{locale}")
        if ctx["exactHead"] != HEAD or ctx["exactTree"] != TREE:
            raise SystemExit(f"source/caller context head/tree mismatch at {rank}/{locale}")

        key = (rank, locale)
        rule = REVISIONS.get(key)
        review_rule = REVIEWS.get(key)
        if rule:
            status = "revise"
            proposal = rule["target"]
            rationale = rule["rationale"]
            issue_codes = rule["issueCodes"]
            confidence = rule["confidence"]
        elif review_rule:
            status = "review"
            proposal = review_rule["suggestion"]
            rationale = review_rule["rationale"]
            issue_codes = review_rule["issueCodes"]
            confidence = "low"
        else:
            status = "retain"
            proposal = None
            rationale = "No material semantic or technical mismatch was identified in the supplied source, current target, caller context, and token evidence."
            issue_codes = []
            confidence = "moderate"

        source = current["source"]
        current_target = current["currentTarget"]
        if sha256(source.encode("utf-8")) != current["sourceSha256"]:
            raise SystemExit(f"source string hash mismatch at {rank}/{locale}")
        if sha256(current_target.encode("utf-8")) != current["currentTargetSha256"]:
            raise SystemExit(f"current target hash mismatch at {rank}/{locale}")

        baseline = current["tokenEvidence"]
        for key_name, pass_value in [
            ("placeholder", baseline["placeholders"]["matches"]),
            ("markup", baseline["markup"]["matches"]),
            ("numeric", baseline["numbers"]["sourcePreserved"]),
            ("protectedLiteral", not baseline["protectedLiterals"]["missing"]),
        ]:
            if not pass_value:
                baseline_mismatches[key_name] += 1

        if status == "revise":
            selected_target = proposal
        else:
            selected_target = current_target
        selected_tokens = token_signature(source, selected_target)
        target_tokens_pass = (
            selected_tokens["placeholders"]["matches"]
            and selected_tokens["markup"]["matches"]
            and selected_tokens["numbers"]["sourcePreserved"]
            and not selected_tokens["protectedLiterals"]["missing"]
        )
        if not target_tokens_pass:
            raise SystemExit(f"selected blind target fails token fidelity at {rank}/{locale}")

        suggestion_tokens = token_signature(source, proposal) if isinstance(proposal, str) else None
        if isinstance(proposal, str):
            suggestion_passes = (
                suggestion_tokens["placeholders"]["matches"]
                and suggestion_tokens["markup"]["matches"]
                and suggestion_tokens["numbers"]["sourcePreserved"]
                and not suggestion_tokens["protectedLiterals"]["missing"]
            )
            if not suggestion_passes:
                raise SystemExit(f"review suggestion fails token fidelity at {rank}/{locale}")
        else:
            suggestion_passes = None
        if status == "retain" and not target_tokens_pass:
            raise SystemExit(f"retained target has a token mismatch at {rank}/{locale}")

        row = {
            "window": "W1053-W1077",
            "head": HEAD,
            "tree": TREE,
            "continuationRank": rank,
            "remainingQueueRank": current["remainingQueueRank"],
            "sourceId": current["sourceId"],
            "sourceIdSha256": current["sourceIdSha256"],
            "sourceSha256": current["sourceSha256"],
            "source": source,
            "locale": locale,
            "sourceTextIncluded": True,
            "currentTarget": current_target,
            "currentTargetSha256": current["currentTargetSha256"],
            "currentTargetTextIncluded": True,
            "callerContextSha256": current["callerContextSha256"],
            "callerCount": current["callerCount"],
            "callerReferences": caller_pins(ctx),
            "catalogPath": current["catalogPath"],
            "catalogFileSha256": current["catalogFileSha256"],
            "catalogGitBlob": current["catalogGitBlob"],
            "candidateFreeTokenEvidence": baseline,
            "disposition": status,
            "status": status,
            "issueCodes": issue_codes,
            "rationale": rationale,
            "confidence": confidence,
            "reviewTarget": selected_target,
            "reviewTargetSha256": sha256(selected_target.encode("utf-8")),
            "reviewTargetTextIncluded": True,
            "reviewTargetTokenEvidence": selected_tokens,
            "reviewTargetTokenChecksPass": target_tokens_pass,
            "reviewerSuggestionUnapproved": proposal if status in {"revise", "review"} else None,
            "reviewerSuggestionSha256": sha256(proposal.encode("utf-8")) if status in {"revise", "review"} and isinstance(proposal, str) else None,
            "reviewerSuggestionTokenChecksPass": suggestion_passes,
            "nativeSpeakerApproval": False,
        }
        ledger.append(row)
        counts[status] += 1

    if len(ledger) != 300:
        raise SystemExit("blind ledger coverage is not 300")
    if [r["continuationRank"] for r in ledger] != [r["continuationRank"] for r in cells]:
        raise SystemExit("ledger order differs from candidate-free cell order")
    if sum(counts.values()) != 300 or counts["hold"] != 24:
        raise SystemExit("disposition counts or callerless holds mismatch")

    # Copy all current active hold rows byte-for-byte, plus current window hash-only holds.
    prior_holds = INPUT / "prior-held-cell-reattestation-hash-only.jsonl"
    window_holds = INPUT / "window-holds-hash-only.jsonl"
    prior_history = INPUT / "prior-hold-resolution-history-hash-only.jsonl"
    shutil.copyfile(prior_holds, OUT / "prior-active-holds-reattestation-hash-only.jsonl")
    shutil.copyfile(window_holds, OUT / "window-callerless-holds-hash-only.jsonl")
    shutil.copyfile(prior_history, OUT / "prior-hold-resolution-history-hash-only.jsonl")
    shutil.copyfile(INPUT / "caller-contexts.jsonl", OUT / "caller-contexts.jsonl")

    boundary = read_json(INPUT / "selection-and-boundary.json")["nextUnselected"]
    if boundary["continuationRank"] != 1078:
        raise SystemExit("unexpected next continuation rank")

    # Write ledger in the exact input order.
    (OUT / "blind-review-ledger.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in ledger),
        encoding="utf-8",
    )

    input_checksums_hash = sha256((INPUT / "SHA256SUMS.txt").read_bytes())
    manifest = {
        "artifact": "slskdN PR #409 W1053-W1077 independent blind review",
        "repository": "snapetech-org/slskdN",
        "pullRequest": 409,
        "head": HEAD,
        "tree": TREE,
        "window": "W1053-W1077",
        "continuationRankRange": [1053, 1077],
        "remainingQueueRankRange": [953, 977],
        "localeOrder": manifest_in["locales"],
        "cellCount": 300,
        "callerBackedCellCount": 276,
        "callerlessHashOnlyHoldCount": 24,
        "sourceCount": 25,
        "sourceCallerReferenceCount": manifest_in["sourceCallerReferenceCount"],
        "sourceCallerOccurrenceCount": manifest_in["sourceCallerOccurrenceCount"],
        "input": {
            "path": INPUT.relative_to(ROOT).as_posix(),
            "sha256SumsFileSha256": input_checksums_hash,
            "manifestSha256": sha256((INPUT / "manifest.json").read_bytes()),
            "sourceCurrentCellsSha256": sha256((INPUT / "source-current-cells.jsonl").read_bytes()),
            "callerContextsSha256": sha256((INPUT / "caller-contexts.jsonl").read_bytes()),
            "priorActiveHoldsSha256": sha256(prior_holds.read_bytes()),
            "windowHoldsSha256": sha256(window_holds.read_bytes()),
            "priorHoldResolutionHistorySha256": sha256(prior_history.read_bytes()),
        },
        "dispositions": dict(sorted(counts.items())),
        "baselineTokenMismatchCounts": dict(sorted(baseline_mismatches.items())),
        "reviewedProposalTokenMismatchCounts": dict(sorted(suggested_mismatches.items())),
        "priorActiveHoldCount": manifest_in["priorActiveHoldsReattested"],
        "priorActiveHoldsCopiedByteForByte": True,
        "priorHoldResolutionHistoryCopiedByteForByte": True,
        "callerlessWindowHoldsCopiedByteForByte": True,
        "nextBoundary": boundary,
        "reviewMethod": "Independent blind semantic review using only the candidate-free exact-head source/current/caller/runtime evidence; no primary or prior proposal packet opened.",
        "blindReview": True,
        "crossReviewUsed": False,
        "nativeSpeakerApproval": False,
        "productFilesEdited": False,
        "testsBuildsScansCiRun": False,
        "confidence": "moderate",
        "checksumCoverage": "SHA256SUMS.txt covers every regular output file except itself.",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    readme = f"""# slskdN PR #409 W1053-W1077 independent blind review

Pinned product head/tree: {HEAD} / {TREE}.

This blind ledger covers all 300 cells in the candidate-free order. It contains {counts['retain']} retain, {counts['revise']} revise, {counts['review']} review, and {counts['hold']} hash-only hold dispositions. The 24 rows with no pinned production caller expose only source/current-target hashes and remain holds.

Review used only the candidate-free packet. No primary-review or prior-proposal packet was opened. Prior active holds, the callerless window hold file, prior hold resolution history, and caller contexts were copied byte-for-byte where noted in the manifest.

No native-speaker approval is included. No repository, product, PR, tests, builds, or CI were changed or run.

## Verification

Run python3 -B verify_blind_review.py from this directory. The verifier checks the sealed input and output checksums, exact head/tree, 300-row order and coverage, callerless hash-only holds, every source/current/proposed hash and token audit, byte-for-byte hold lineage, and next boundary.

SHA256SUMS.txt covers every regular output file except itself.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    checksum_output()
    print(json.dumps({
        "output": str(OUT),
        "cells": len(ledger),
        "dispositions": dict(sorted(counts.items())),
        "baselineTokenMismatchCounts": dict(sorted(baseline_mismatches.items())),
        "nextBoundary": boundary,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
