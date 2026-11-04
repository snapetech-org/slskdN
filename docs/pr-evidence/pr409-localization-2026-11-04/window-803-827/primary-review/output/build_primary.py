#!/usr/bin/env python3
"""Build the W77 independent primary decisions from sealed candidate-free inputs."""
import collections
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent.parent / "candidate-free" / "input"
HEAD = "582ae64e5c3af275490f11f4350b33da7373a3c3"
TREE = "b8692bb066cede93b6668806d0b97816135ce647"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]

# Exact proposals, keyed by continuation rank and locale.
PROPOSALS = {
    (805, "ar"): "فشلت مزامنة الملء الرجعي للبود: {message}",
    (805, "es"): "No se pudo sincronizar la carga retroactiva del pod: {message}",
    (805, "fr"): "Échec de la synchronisation du backfill du pod : {message}",
    (805, "pt-BR"): "Falha ao sincronizar o backfill do pod: {message}",
    (805, "vi"): "Không thể đồng bộ hóa tác vụ backfill của pod: {message}",
    (806, "ar"): "أخضر زيتوني",
    (806, "es"): "Verde oliva",
    (806, "hi"): "जैतूनी",
    (806, "id"): "Hijau zaitun",
    (806, "pt-BR"): "Verde-oliva",
    (806, "vi"): "Xanh ô liu",
    (806, "zh-Hans"): "橄榄绿",
    (806, "zh-Hant"): "橄欖綠",
    (807, "ko"): "라이브러리 상태 검사가 시작되었습니다. 검사 ID: {scanId}, 라이브러리 경로: {libraryPath}.",
    (808, "ar"): "جارٍ تحميل سجل عمليات النقل المكتملة",
    (808, "de"): "Verlauf abgeschlossener Übertragungen wird geladen",
    (808, "es"): "Cargando el historial de transferencias completadas",
    (808, "fr"): "Chargement de l’historique des transferts terminés",
    (808, "hi"): "पूरे हुए ट्रांसफ़र का इतिहास लोड हो रहा है",
    (808, "id"): "Memuat riwayat transfer yang selesai",
    (808, "ja"): "完了した転送の履歴を読み込み中",
    (808, "ko"): "완료된 전송 기록을 불러오는 중",
    (808, "pt-BR"): "Carregando o histórico de transferências concluídas",
    (808, "vi"): "Đang tải lịch sử các lượt truyền đã hoàn tất",
    (808, "zh-Hans"): "正在加载已完成传输的历史记录",
    (808, "zh-Hant"): "正在載入已完成傳輸的歷史記錄",
    (809, "ja"): "プレイリスト「{playlistName}」に追加できる一致行はありません",
    (811, "ar"): "نشر أدلة الشبكة",
    (811, "hi"): "मेश साक्ष्य प्रकाशन",
    (815, "zh-Hans"): "强",
    (815, "zh-Hant"): "強",
    (816, "ar"): "تم وضع مهمة البحث في قائمة الانتظار عبر ملف الاقتناء المحدد. لن يبدأ أي تنزيل حتى يتم تحديد نتيجة صراحةً.",
    (816, "es"): "La tarea de búsqueda se puso en cola mediante el perfil de adquisición seleccionado. No se iniciará ninguna descarga hasta que se seleccione un resultado de forma explícita.",
    (816, "hi"): "चयनित अधिग्रहण प्रोफ़ाइल के माध्यम से खोज कार्य कतार में लगाया गया है। किसी परिणाम को स्पष्ट रूप से चुनने तक कोई डाउनलोड शुरू नहीं होगा।",
    (816, "id"): "Tugas pencarian telah diantrekan melalui profil akuisisi yang dipilih. Tidak ada unduhan yang dimulai sampai suatu hasil dipilih secara eksplisit.",
    (816, "ja"): "選択した取得プロファイルを通じて検索ジョブがキューに追加されました。結果が明示的に選択されるまで、ダウンロードは開始されません。",
    (816, "ko"): "선택한 획득 프로필을 통해 검색 작업이 대기열에 추가되었습니다. 결과를 명시적으로 선택하기 전까지 다운로드가 시작되지 않습니다.",
    (816, "pt-BR"): "A tarefa de busca foi colocada na fila pelo perfil de aquisição selecionado. Nenhum download será iniciado até que um resultado seja selecionado explicitamente.",
    (816, "vi"): "Tác vụ tìm kiếm đã được đưa vào hàng đợi thông qua hồ sơ tải xuống đã chọn. Không có nội dung nào được tải xuống cho đến khi một kết quả được chọn rõ ràng.",
    (816, "zh-Hans"): "搜索任务已通过选定的获取配置排入队列。在明确选择某个结果之前，不会开始下载。",
    (816, "zh-Hant"): "搜尋工作已透過選定的取得設定檔排入佇列。在明確選取某項結果之前，不會開始下載。",
    (817, "de"): "Die Raumübertragung konnte nicht gestartet werden. Versuchen Sie es erneut.",
    (821, "fr"): "Page suivante des collections",
    (825, "ar"): "تم تعطيل نقطة التقاء DHT بواسطة بوابة الميزات الخاصة بها",
    (825, "es"): "El punto de encuentro DHT está deshabilitado por su indicador de funcionalidad",
    (825, "fr"): "Le point de rendez-vous DHT est désactivé par son indicateur de fonctionnalité",
    (825, "ko"): "DHT 랑데부 기능은 해당 기능 게이트로 인해 비활성화됩니다.",
    (825, "pt-BR"): "O ponto de encontro DHT está desativado pelo controle de ativação do recurso",
    (825, "zh-Hans"): "DHT 会合功能已由对应的功能开关禁用",
    (825, "zh-Hant"): "DHT 會合功能已由對應的功能開關停用",
}

SOURCE_RATIONALES = {
    803: "The caller renders this as progress while search-history backfill continues; the current translation preserves both count placeholders and the remaining-search meaning.",
    804: "The SearchDetail caller uses this as the error caption when results cannot load; the current text clearly directs the user to retry later.",
    805: "MediaCorePods supplies an API error message to the backfill-sync toast; the proposal names the pod backfill operation and preserves the dynamic error text.",
    806: "The user-note color selector pairs this label with the olive color swatch; the proposal names the color rather than the olive fruit.",
    807: "The automation recipe reports a started Library Health scan with both scan ID and library path; the proposal avoids attaching a language-dependent particle to the dynamic ID.",
    808: "TransferManager displays this while loading the history of completed transfers; the proposal makes completed modify transfers rather than the loading action.",
    809: "PlaylistIntake displays this when its matched-item list is empty; the proposal states that no matching rows can be added to the named playlist.",
    810: "The playlist-intake dry-run output uses this as a label before the playlist name; the current translation preserves the name placeholder.",
    811: "The automation recipe registry uses this as the Mesh Evidence Publish title; the proposal fixes the Arabic word order and the Hindi transliteration of Mesh.",
    812: "MediaCorePods uses this as the heading for the membership-record publishing form; the current translations preserve the publish action and record concept.",
    813: "The notification integrations panel shows this as an informational runtime-configuration notice; the current text preserves both allowed ways to change the settings.",
    815: "The match-confidence switch uses Strong as a confidence tier; the Chinese proposals express strength without the current sense of power or might.",
    816: "The acquisition-plan caller describes a queued search task and explicitly says downloads wait for a selected result; the proposals preserve that safety condition and profile terminology.",
    817: "The listen-along caller uses this as the start-broadcast error fallback; the German proposal matches the formal retry style used by nearby German messages.",
    818: "VpnGatewayConfig uses this as helper text for the maximum tunnel lifetime field; the current wording preserves that constraint.",
    819: "MediaCoreStats uses this as a card heading for DHT publishing controls; the current translations describe content publishing.",
    820: "AcquisitionRequests uses this as the failed-state summary; the current text preserves the prior-attempt, acquisition/import, and review-needed meaning.",
    821: "Collections uses this as the accessible label for the next-page button; the French proposal means the next page within the collections list.",
    822: "DiscoveryGraphCanvas inserts raw graph source, target, type, and reason values into this SVG title; the unchanged form preserves all placeholders and separators.",
    823: "Contacts uses this as an accessible action label with the contact nickname or peer ID; the current translations preserve the shared-files action and placeholder.",
    824: "MeshEvidencePolicy uses this as both the JSON text-area label and accessible name; the current translations identify the evidence-review JSON input.",
    825: "The Mesh system notice is selected by the DHT-enabled state; proposals clarify that the rendezvous feature is disabled by its feature control.",
    826: "MediaCoreStats uses this as the confirmation tooltip for clearing accumulated statistics; the current text preserves the confirm-before-clear condition.",
    827: "PlayerBar uses this for the collections-browser button title and accessible label; the current translation preserves the open action.",
}

CORRECTION_RATIONALES = {
    805: "The exact MediaCorePods caller names a pod backfill stats operation; the previous wording suggests replenishing or filling a container instead of the technical backfill task.",
    806: "The caller's olive-valued swatch makes this a color name; the current value names the olive fruit or omits the green-color sense.",
    807: "The exact caller includes both dynamic values; this wording reports the scan start and labels the ID and path without a particle whose form depends on the ID text.",
    808: "TransferManager uses completed to describe transfers in the history, not a history whose loading has finished.",
    809: "The current Japanese stacks two modifiers unnaturally; this proposal says no matching rows can be added to the named playlist.",
    811: "The caller uses this as a recipe title; the current Arabic word order is ungrammatical and Hindi मेष means ram rather than the Mesh network term.",
    815: "This is a match-confidence tier; 强大/強大 means powerful, while 强/強 is the appropriate strength rating.",
    816: "The current wording describes searching for jobs or queued jobs rather than stating that a search task has been queued; Vietnamese also uses the unrelated conversion-profile term. The proposals preserve the explicit no-download-until-selection condition.",
    817: "The current German message uses informal singular address while the adjacent search error uses formal Sie; the proposal keeps the formal UI address.",
    821: "The current French phrasing means a page about upcoming collections; this is the next page in the collections browser.",
    825: "The current wording has a false-friend or literal-gate problem in these locales; the proposals identify the DHT rendezvous and its feature control clearly.",
}


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
    if len(cells) != 300 or len(PROPOSALS) != 50:
        raise SystemExit("refusing unexpected W77 coverage or proposal map")
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
    if len(ledger) != 300 or len(corrections) != 50 or len(holds) != 12:
        raise SystemExit("refusing unexpected W77 decision counts")
    write_rows("primary-review.jsonl", ledger)
    write_rows("corrections.jsonl", corrections)
    write_rows("holds-hash-only.jsonl", holds)
    (ROOT / "source-rewrite-recommendations.json").write_text(json.dumps({"schemaVersion": 1, "recommendations": []}, indent=2) + "\n", encoding="utf-8")
    counts = collections.Counter(row["disposition"] for row in ledger)
    summary = {
        "artifact": "slskdN PR #409 W77 independent primary semantic review",
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
        "liveMainSha": "bc6251ff4ea5a7e59f2d86e2400c90520601f46e",
        "baseApiSha": "f25d263a2a7cdb2c8f76c40c346cb10f749a9356",
        "priorHeldCellsCarried": 319, "priorHoldResolutionHistoryRows": 13,
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
