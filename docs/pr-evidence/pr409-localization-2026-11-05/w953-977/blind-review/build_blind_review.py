#!/usr/bin/env python3
"""Build a sealed W953-W977 blind review from candidate-free input only."""
from __future__ import annotations
import hashlib, json, re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

TASK = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
INPUT = TASK / "candidate-free" / "input"
HEAD = "fc8e42a06363ceee762ae084bbe716953d4a5d94"
TREE = "e04aa06b8cfb0ee41cae90aef601a0552b5e85bd"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
START, END = 953, 977

# The cross-language decisions below were made against candidate-free source,
# current values, pinned caller contexts, and local product terminology only.
# Each item is (decision, exact proposed target, rationale, confidence).
CHANGES = {
 (953,"ar"): ("correction", "إجراءات عضوية Pod: تقديم الطلبات وقبولها، ومغادرة Pod ومراجعة الإجراءات.", "The caller describes the Pod Join/Leave workflow. الكبسولة means a capsule; preserving the product entity Pod avoids changing the feature name.", "moderate"),
 (953,"es"): ("correction", "Gestiona la membresía del Pod: solicita unirte, acepta solicitudes, abandona el Pod y revisa el proceso.", "The workflow caller is about joining and leaving a Pod; grupo replaces that product object with a generic group.", "moderate"),
 (953,"vi"): ("correction", "Quản lý quy trình thành viên Pod: gửi yêu cầu tham gia, chấp nhận yêu cầu, rời Pod và xem xét quy trình.", "The caller describes Pod membership actions. nhóm changes the named Pod into a generic group; this keeps Pod and makes the actions clear.", "moderate"),

 (954,"ar"): ("correction", "بدأت عمليات البحث القريبة في الأطلس: {count}", "The current عن {count} reads as ‘about {count}’; the replacement keeps the count attached to the completed nearby atlas searches.", "moderate"),
 (954,"de"): ("correction", "Es wurden {count} nahegelegene Atlas-Suchen gestartet", "The current compound uses a singular Atlas-Suche with a count. The replacement gives a natural plural count and preserves nearby Atlas searches.", "moderate"),
 (954,"es"): ("correction", "Se iniciaron {count} búsquedas cercanas en el atlas", "The current wording can mean searches for nearby atlases and puts the count after the noun phrase. This states that nearby searches in the atlas started.", "moderate"),
 (954,"fr"): ("correction", "{count} recherches à proximité dans l’atlas ont démarré", "The current fragment puts the count at the end and reads as a search in an atlas nearby. This places the count before the nearby searches.", "moderate"),
 (954,"hi"): ("correction", "आस-पास की {count} एटलस खोजें शुरू की गईं", "The current order separates the count from the searches. The replacement gives a natural count phrase for nearby Atlas searches.", "moderate"),
 (954,"id"): ("correction", "Memulai {count} pencarian atlas terdekat", "The current count trails the noun phrase; Indonesian places the number before the counted search records.", "moderate"),
 (954,"ja"): ("refinement", "近隣のアトラス検索を{count}件開始しました", "件 is the natural counter for search jobs, keeping the count attached to the nearby Atlas searches.", "moderate"),
 (954,"ko"): ("refinement", "근처 아틀라스 검색 {count}건을 시작했습니다", "건 is the natural counter for search jobs. The current translation omits the counter and adds punctuation absent from the source.", "moderate"),
 (954,"pt-BR"): ("correction", "Foram iniciadas {count} buscas próximas no atlas", "The current próximo de {count} attaches proximity to the count. The replacement places the count before the nearby searches.", "moderate"),
 (954,"vi"): ("correction", "Đã bắt đầu {count} lượt tìm kiếm Atlas lân cận", "The current word order makes the count interrupt ‘map search’. This places the count before the nearby Atlas-search unit and retains the feature name.", "moderate"),
 (954,"zh-Hans"): ("correction", "已启动 {count} 次附近的图谱搜索", "The Discovery Graph Atlas uses 图谱 terminology, while 图集 commonly means an image collection. 次 also counts the search operations.", "moderate"),
 (954,"zh-Hant"): ("correction", "已啟動 {count} 次附近的圖譜搜尋", "The Discovery Graph Atlas uses 圖譜 terminology, while 圖集 commonly means an image collection. 次 also counts the search operations.", "moderate"),

 (955,"hi"): ("correction", "इस समूह में कोई सदस्य निर्धारित नहीं है।", "नियुक्त means appointed, which is a different relationship. निर्धारित states that the group has no assigned members.", "moderate"),
 (956,"fr"): ("correction", "Arrêtez le pont local vers les anciens clients et déconnectez ses clients actifs.", "The current existant means existing, not legacy. The caller is the bridge stop control; anciens clients preserves the legacy-client meaning.", "moderate"),

 (957,"ar"): ("correction", "الرجاء إدخال بيانات Pod بصيغة JSON", "جراب means a pouch or bag. The caller submits a MediaCore Pod object encoded as JSON, so the product term should remain Pod.", "moderate"),
 (957,"de"): ("correction", "Bitte geben Sie die JSON-Daten des Pods ein", "The caller asks for JSON input for a Pod. JSON-Daten des Pods is grammatical and avoids the current noun order Pod-Daten JSON.", "moderate"),
 (957,"es"): ("correction", "Por favor, ingrese los datos JSON del Pod", "The current pod JSON data order is awkward. The caller requests JSON data belonging to a Pod; this places JSON with datos and retains the product term.", "moderate"),
 (957,"vi"): ("correction", "Vui lòng nhập dữ liệu JSON của Pod", "The caller submits JSON for a MediaCore Pod object. nhóm means a generic group; keeping Pod preserves the domain object.", "moderate"),

 (958,"fr"): ("correction", "Examiner les avis", "This is a section header above pod-opinion refresh and review controls. Avis d’examen means examination notice; Examiner les avis expresses reviewing the opinions.", "moderate"),
 (958,"ja"): ("correction", "意見を確認", "The header introduces controls for reading and refreshing pod opinions. 意見の確認 conveys review/checking opinions; レビューの意見 is an awkward compound.", "moderate"),

 (959,"ar"): ("correction", "مدة الاحتفاظ بعمليات البحث بالدقائق", "This is an aria-label for a duration setting. The current wording says to search for retention minutes; the replacement names the search-retention duration in minutes.", "moderate"),
 (959,"de"): ("correction", "Suchaufbewahrungsdauer in Minuten", "The current Sie suchen phrase reads as an instruction to search. The caller is a numeric setting for how long searches are retained.", "moderate"),
 (959,"hi"): ("correction", "खोजों को सुरक्षित रखने की अवधि (मिनट)", "The current खोजें reads as the imperative ‘search’. The caller labels a retention-duration setting; this states how long searches are kept.", "moderate"),

 (962,"ja"): ("correction", "外部への公開", "The section controls whether mesh evidence is published outside the local policy. 出版 refers to publishing books; 外部への公開 describes external publication.", "moderate"),
 (962,"ko"): ("correction", "외부 게시", "This section controls publication of mesh evidence outside the local policy. 출판 means book publishing; 게시 is the appropriate software publishing/posting term.", "moderate"),
 (962,"vi"): ("correction", "Công bố ra bên ngoài", "The section governs outbound publication of mesh evidence. Ấn phẩm ra nước ngoài means publications overseas, rather than publishing evidence externally.", "moderate"),
 (962,"zh-Hans"): ("correction", "对外发布", "This is a section for publishing mesh evidence to external recipients. 出境出版 reads as publication abroad; 对外发布 names outward publication.", "moderate"),
 (962,"zh-Hant"): ("correction", "對外發布", "This is a section for publishing mesh evidence to external recipients. 出境出版 reads as publication abroad; 對外發布 names outward publication.", "moderate"),

 (969,"ar"): ("correction", "أعد إحصاء الملفات في المجلدات المشتركة المُهيأة بعد تغيير الملفات أو الاستثناءات.", "The caller is a rescan control for configured file shares. The current المشاركات المضبوطة is ambiguous; المجلدات المشتركة identifies the configured shared folders.", "moderate"),
 (969,"id"): ("correction", "Hitung ulang berkas di folder bersama yang dikonfigurasi setelah perubahan pada berkas atau pengecualian.", "The current berbagi yang dikonfigurasi treats berbagi as a verb. Folder bersama is the configured share location in this rescan tooltip.", "moderate"),
 (969,"pt-BR"): ("correction", "Conte novamente os arquivos dos compartilhamentos configurados após alterar arquivos ou exclusões.", "The current arquivos compartilhados means shared files and drops that the shares are configured locations. The caller recounts files inside configured shares.", "moderate"),

 (970,"ko"): ("correction", "승격", "In the shelf policy preview, promote is an action category for high-rated candidates. 홍보하다 means advertise; 승격 expresses raising a candidate's standing.", "moderate"),
 (970,"vi"): ("correction", "nâng hạng", "The shelf preview counts candidates selected for promotion. khuyến khích means encourage; nâng hạng expresses moving a candidate up.", "moderate"),

 (972,"zh-Hant"): ("correction", "多位藝人政策：{policy}", "The current 多人 means multiple people and omits artists. This restores the source's multi-artist policy and preserves {policy}.", "moderate"),

 (973,"de"): ("correction", "Privater Chatraum", "RoomCreateModal identifies this as a chat room unsupported by the server API. Privatzimmer suggests a private bedroom or lodging room.", "moderate"),
 (973,"es"): ("correction", "Sala de chat privada", "The caller is the private chat-room creation option. Habitación privada can suggest a physical room; sala de chat names the application room.", "moderate"),
 (973,"fr"): ("correction", "Salle de discussion privée", "The caller is a chat-room type unsupported by the server API. Chambre privée means a private bedroom; salle de discussion keeps the chat context.", "moderate"),
 (973,"id"): ("correction", "Ruang obrolan pribadi", "The caller labels a chat room. Kamar pribadi can suggest a physical private room; ruang obrolan preserves the chat function.", "moderate"),
 (973,"pt-BR"): ("correction", "Sala de chat privada", "The caller labels a chat room. Quarto privado can suggest a bedroom; sala de chat preserves the application context.", "moderate"),

 (975,"id"): ("refinement", "Pemindaian kondisi koleksi musik", "The automation recipe scans the app's media library. koleksi musik makes that collection meaning explicit instead of suggesting a public library.", "moderate"),
 (975,"ko"): ("refinement", "미디어 라이브러리 상태 점검", "The automation recipe checks the local media collection. 도서관 means a public library; 미디어 라이브러리 states the software-library sense.", "moderate"),
 (975,"vi"): ("refinement", "Quét kiểm tra tình trạng thư viện nhạc", "The automation recipe scans the app's music library. Adding nhạc makes thư viện clearly mean a media collection rather than a public library.", "moderate"),
 (975,"zh-Hans"): ("correction", "媒体库健康检查", "The automation recipe scans the app's media library. 图书馆 means a public library building; 媒体库 identifies the local media collection.", "moderate"),
 (975,"zh-Hant"): ("correction", "媒體庫健康檢查", "The automation recipe scans the app's media library. 圖書館 means a public library building; 媒體庫 identifies the local media collection.", "moderate"),

 (976,"ar"): ("correction", "تمت إضافة استيراد Lidarr إلى قائمة الانتظار: {safeCandidates} ملف/ملفات", "The caller is a success toast and safeCandidates is a count. The current target places the count after file(s); this gives the count-first order and preserves Lidarr.", "moderate"),
 (976,"de"): ("correction", "Lidarr-Import in die Warteschlange gestellt: {safeCandidates} Datei(en)", "The current {count}-Datei(en) compound is not a natural German count. The replacement puts the count before the singular/plural file notation.", "moderate"),
 (976,"es"): ("correction", "Se puso en cola la importación de Lidarr: {safeCandidates} archivo(s)", "The success toast gives a file count; the current target places archivo(s) before the number. This uses a natural count-first order.", "moderate"),
 (976,"fr"): ("correction", "Importation de Lidarr mise en file d’attente : {safeCandidates} fichier(s)", "The success toast gives a file count; the current target places fichier(s) before the number. This uses a natural count-first order.", "moderate"),
 (976,"hi"): ("refinement", "Lidarr आयात कतार में जोड़ा गया: {safeCandidates} फ़ाइल(ें)", "The current target repeats the full plural word in parentheses. फ़ाइल(ें) is the compact singular/plural form for the dynamic count.", "moderate"),
 (976,"id"): ("correction", "Impor Lidarr diantrekan: {safeCandidates} berkas", "The current target puts the count after file. Indonesian uses the count before the noun, and berkas works for singular or plural counts.", "moderate"),
 (976,"ja"): ("refinement", "Lidarr のインポートをキューに登録しました: {safeCandidates} 件のファイル", "件 provides a natural counter for the file count in this success toast.", "moderate"),
 (976,"ko"): ("correction", "Lidarr 가져오기 대기열에 추가됨: 파일 {safeCandidates}개", "The caller reports a number of files. Korean needs the counter 개; the current target gives a bare number before 파일.", "moderate"),
 (976,"pt-BR"): ("correction", "Importação do Lidarr na fila: {safeCandidates} arquivo(s)", "The success toast gives a file count; the current target places arquivo(s) before the number. This uses a natural count-first order.", "moderate"),
 (976,"vi"): ("correction", "Đã đưa lệnh nhập Lidarr vào hàng đợi: {safeCandidates} tệp", "The current target places the number after the noun. Vietnamese puts the count before the file noun; tệp is not pluralized.", "moderate"),
 (976,"zh-Hans"): ("correction", "Lidarr 导入已排队：{safeCandidates} 个文件", "Mandarin uses the 个 classifier between the dynamic count and 文件.", "moderate"),
 (976,"zh-Hant"): ("correction", "Lidarr 匯入已排隊：{safeCandidates} 個檔案", "Traditional Chinese uses the 個 classifier between the dynamic count and 檔案.", "moderate"),

 (977,"de"): ("correction", "Übergabe an die Beschaffungswarteschlange", "The media-server capability hands candidates to an acquisition queue. Erfassung refers to capture/recording; Beschaffung names content acquisition.", "moderate"),
 (977,"ja"): ("refinement", "取得キューへの引き渡し", "The capability hands content-acquisition candidates to a queue. キューへの引き渡し expresses a handoff to that queue rather than a handoff of it.", "moderate"),
 (977,"ko"): ("refinement", "획득 대기열로 전달", "The capability sends candidates to an acquisition queue. 대기열로 전달 states delivery to the queue more clearly than the English loan 핸드오프.", "moderate"),
 (977,"pt-BR"): ("refinement", "Encaminhamento para a fila de aquisição", "The capability hands candidates to the acquisition queue. Encaminhamento para expresses routing to the queue, rather than transferring the queue itself.", "moderate"),
 (977,"vi"): ("correction", "Chuyển tiếp sang hàng đợi thu mua", "The capability sends candidate content to an acquisition queue. mua lại means repurchase; thu mua expresses acquisition/procurement.", "moderate"),
 (977,"zh-Hans"): ("correction", "采集队列移交", "The capability hands candidates to an acquisition queue. 切换 means switching; 移交 expresses the handoff.", "moderate"),
 (977,"zh-Hant"): ("correction", "採集隊列移交", "The capability hands candidates to an acquisition queue. 切換 means switching; 移交 expresses the handoff.", "moderate"),
}

# Rank 966 has literal source matches, but the candidate-free caller snapshot shows
# only layout attributes, not user-facing localization calls. Hold every locale
# hash-only until a real translated UI call is established.
CONTEXT_HOLD_RANKS = {966}
HOLD_REASON = "No user-facing localization call is demonstrated; the captured references are layout/alignment attributes. Keep the current cell hash-only pending a genuine translation caller."
ACCEPT_RATIONALES = {
 953: "The target conveys the Pod membership request, acceptance, departure, and review workflow in the supplied source context.",
 954: "The target communicates that nearby Atlas searches have started and preserves the dynamic count.",
 955: "The target says that this group has no assigned members.",
 956: "The target tells the operator to stop the local legacy-client bridge and disconnect its active clients.",
 957: "The target requests JSON data for the Pod without changing the data format.",
 958: "The target labels the pod-opinion review section in a way that fits the controls below it.",
 959: "The target identifies the search-retention duration setting in minutes.",
 960: "The target tells the user to disable the named item and preserves its title placeholder.",
 961: "The target names a new tab for a room in the chat interface.",
 962: "The target describes publication directed outside the local mesh-evidence policy.",
 963: "The target labels a file stored on the local device.",
 964: "The target preserves the three-day duration.",
 965: "The target asks for confirmation before permanently deleting the named item.",
 966: "The target is held because the pinned source contexts do not show a user-facing localization call.",
 967: "The target explains changing a peer's Pod role to grant or remove moderator/owner duties after verification.",
 968: "The target explains that collapsing the section hides its conversations and preserves the section placeholder.",
 969: "The target explains recounting files in configured shares after file or exclusion changes.",
 970: "The target names the promote action category in the discovery-shelf preview.",
 971: "The target labels running the enabled Wishlist searches.",
 972: "The target labels the multi-artist policy and preserves its dynamic value.",
 973: "The target labels a private chat-room type that the server API does not support.",
 974: "The target labels the playback queue.",
 975: "The target names an automation that scans the application's media library.",
 976: "The target reports that the Lidarr import was queued and includes the safe-candidate count.",
 977: "The target names handing approved acquisition candidates to the acquisition queue.",
}
PLACEHOLDER = re.compile(r"\{[^{}]+\}")
MARKUP = re.compile(r"</?[A-Za-z][^>]*>")
NUMBER = re.compile(r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)*(?![A-Za-z0-9])")

def sha(value: bytes | str) -> str:
    if isinstance(value, str): value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()

def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def read_json(path: Path): return json.loads(path.read_text(encoding="utf-8"))
def read_jsonl(path: Path): return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
def write_json(path: Path, value): path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
def write_jsonl(path: Path, rows): path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")

def check_sums(path: Path):
    sums_path = path / "SHA256SUMS.txt"
    listed = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        digest, name = line.split("  ", 1)
        if name in listed: raise SystemExit(f"FAIL duplicate checksum {path.name}/{name}")
        candidate = (path / name).resolve()
        if not candidate.is_relative_to(path.resolve()) or not candidate.is_file() or sha(candidate.read_bytes()) != digest:
            raise SystemExit(f"FAIL checksum {path.name}/{name}")
        listed[name] = digest
    actual = {p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file() and p != sums_path}
    if set(listed) != actual: raise SystemExit(f"FAIL checksum coverage {path.name}")
    return listed

def token_checks(source: str, target: str, protected: list[str]):
    return {
        "placeholderSequencePreserved": PLACEHOLDER.findall(source) == PLACEHOLDER.findall(target),
        "markupPreserved": MARKUP.findall(source) == MARKUP.findall(target),
        "numericTokensPreserved": NUMBER.findall(source) == NUMBER.findall(target),
        "protectedLiteralsPreserved": all(item in target for item in protected),
    }

def main():
    if OUT.exists() and any(p.name not in {"build_blind_review.py", "verify_blind_review.py"} for p in OUT.iterdir()):
        raise SystemExit("FAIL blind-review output directory is not empty")
    OUT.mkdir(parents=True, exist_ok=True)
    candidate_sums = check_sums(INPUT)
    manifest = read_json(INPUT / "manifest.json")
    if (manifest.get("head"), manifest.get("tree"), manifest.get("window"), manifest.get("cellCount")) != (HEAD, TREE, "W83", 300):
        raise SystemExit("FAIL candidate-free pin/cardinality")
    if manifest.get("proposedTargetsIncluded") is not False or manifest.get("reviewDecisionsIncluded") is not False:
        raise SystemExit("FAIL candidate-free input contains proposals/decisions")
    if manifest.get("locales") != LOCALES or manifest.get("continuationRankRange") != [START, END]:
        raise SystemExit("FAIL locale/rank selection")
    cells = read_jsonl(INPUT / "source-current-cells.jsonl")
    contexts = read_jsonl(INPUT / "caller-contexts.jsonl")
    selected = read_jsonl(INPUT / "selected-sources.jsonl")
    if len(cells) != 300 or len(contexts) != 25 or len(selected) != 25:
        raise SystemExit("FAIL candidate-free input count")
    ctx_by = {r["continuationRank"]: r for r in contexts}
    selected_by = {r["continuationRank"]: r for r in selected}
    if set(ctx_by) != set(range(START, END + 1)) or set(selected_by) != set(range(START, END + 1)):
        raise SystemExit("FAIL candidate-free source rank coverage")
    expected = [(rank, locale) for rank in range(START, END + 1) for locale in LOCALES]
    if [(r["continuationRank"], r["locale"]) for r in cells] != expected:
        raise SystemExit("FAIL exact locale-cell order")
    if set(CHANGES) & set((rank, locale) for rank, locale in expected if rank in CONTEXT_HOLD_RANKS):
        raise SystemExit("FAIL proposal overlaps a held source")

    rows, proposals, holds = [], [], []
    counts = Counter()
    for cell in cells:
        rank, locale = cell["continuationRank"], cell["locale"]
        ctx = ctx_by[rank]
        src = selected_by[rank]
        if not (cell["sourceId"] == ctx["sourceId"] == src["sourceId"] and cell["source"] == ctx["source"] == src["source"]):
            raise SystemExit(f"FAIL source binding {rank}/{locale}")
        if not (cell["sourceSha256"] == ctx["sourceSha256"] == src["sourceSha256"] == sha(cell["source"])):
            raise SystemExit(f"FAIL source hash binding {rank}/{locale}")
        if cell["callerCount"] != ctx["productionCallerCount"]:
            raise SystemExit(f"FAIL caller count binding {rank}/{locale}")
        if cell.get("containsCandidate") is not False:
            raise SystemExit(f"FAIL candidate-free input contains candidate text {rank}/{locale}")
        caller_pins_hash = sha(canonical(ctx["callers"]))
        is_hold = ctx["productionCallerCount"] == 0 or rank in CONTEXT_HOLD_RANKS
        if is_hold:
            reason = HOLD_REASON if rank in CONTEXT_HOLD_RANKS else "No production caller is present in the pinned candidate-free context; preserve this cell as a text-free hold."
            hold = {
                "head": HEAD, "tree": TREE, "continuationRank": rank, "remainingQueueRank": cell["remainingQueueRank"],
                "sourceIdSha256": sha(cell["sourceId"]), "sourceSha256": cell["sourceSha256"], "locale": locale,
                "currentTargetSha256": cell["currentTargetSha256"], "callerContextSha256": cell["callerContextSha256"],
                "callerReferencePinsSha256": caller_pins_hash, "callerCount": cell["callerCount"],
                "decision": "hold", "holdReason": reason, "sourceTextOmitted": True,
                "currentTargetTextOmitted": True, "proposedTargetTextOmitted": True,
            }
            if any(k in hold for k in ("source", "sourceText", "currentTarget", "currentTargetText", "proposedTarget", "target")):
                raise SystemExit("FAIL text in hash-only hold")
            holds.append(hold)
            row = {
                "head": HEAD, "tree": TREE, "continuationRank": rank, "remainingQueueRank": cell["remainingQueueRank"],
                "sourceIdSha256": sha(cell["sourceId"]), "sourceSha256": cell["sourceSha256"], "locale": locale,
                "currentTargetSha256": cell["currentTargetSha256"], "callerContextSha256": cell["callerContextSha256"],
                "callerReferencePinsSha256": caller_pins_hash, "callerCount": cell["callerCount"],
                "reviewPass": "independent-blind", "decision": "hold",
                "rationale": reason, "confidence": "moderate",
                "sourceTextIncluded": False, "currentTargetTextIncluded": False,
                "tokenEvidenceSha256": sha(canonical(cell["tokenEvidence"])),
            }
            rows.append(row); counts["hold"] += 1
            continue

        proposal = CHANGES.get((rank, locale))
        if proposal:
            decision, target, rationale, confidence = proposal
            target_hash = sha(target)
            checks = token_checks(cell["source"], target, cell["tokenEvidence"]["protectedLiterals"]["source"])
            if not all(checks.values()):
                raise SystemExit(f"FAIL proposal token check {rank}/{locale}: {checks}")
            target_for_row = target
            target_hash_for_row = target_hash
            counts[decision] += 1
        else:
            decision, rationale, confidence = "accept-current", ACCEPT_RATIONALES[rank], "moderate"
            target = None
            target_hash = None
            checks = token_checks(cell["source"], cell["currentTarget"], cell["tokenEvidence"]["protectedLiterals"]["source"])
            if not all(checks.values()): raise SystemExit(f"FAIL current token check {rank}/{locale}")
            target_for_row = None
            target_hash_for_row = None
            counts[decision] += 1
        row = {
            "head": HEAD, "tree": TREE, "continuationRank": rank, "remainingQueueRank": cell["remainingQueueRank"],
            "sourceId": cell["sourceId"], "source": cell["source"], "sourceSha256": cell["sourceSha256"],
            "locale": locale, "catalogPath": cell["catalogPath"], "catalogFileSha256": cell["catalogFileSha256"],
            "catalogGitBlob": cell["catalogGitBlob"], "currentTarget": cell["currentTarget"],
            "currentTargetSha256": cell["currentTargetSha256"], "callerContextSha256": cell["callerContextSha256"],
            "callerReferencePinsSha256": caller_pins_hash, "callerCount": cell["callerCount"],
            "reviewPass": "independent-blind", "decision": decision, "proposedTarget": target_for_row,
            "proposedTargetSha256": target_hash_for_row, "rationale": rationale, "confidence": confidence,
            "tokenCheck": checks,
        }
        rows.append(row)
        if proposal:
            proposals.append({
                "head": HEAD, "tree": TREE, "continuationRank": rank, "remainingQueueRank": cell["remainingQueueRank"],
                "sourceId": cell["sourceId"], "sourceSha256": cell["sourceSha256"], "locale": locale,
                "currentTargetSha256": cell["currentTargetSha256"], "callerContextSha256": cell["callerContextSha256"],
                "decision": decision, "proposedTarget": target, "proposedTargetSha256": target_hash,
                "rationale": rationale, "confidence": confidence, "tokenCheck": checks,
            })

    if set(CHANGES) != {(r["continuationRank"], r["locale"]) for r in rows if r["decision"] in {"correction", "refinement"}}:
        raise SystemExit("FAIL proposal coverage")
    write_jsonl(OUT / "blind-ledger.jsonl", rows)
    write_jsonl(OUT / "proposals.jsonl", proposals)
    write_jsonl(OUT / "holds-hash-only.jsonl", holds)
    used_files = ["manifest.json", "SHA256SUMS.txt", "selected-sources.jsonl", "source-current-cells.jsonl", "caller-contexts.jsonl", "runtime-file-pins.jsonl", "selection-and-boundary.json", "selection-boundary.json", "localization-runtime-context.json"]
    input_note = {
        "head": HEAD, "tree": TREE, "candidateFreeInputPath": str(INPUT),
        "candidateFreeChecksumListSha256": sha((INPUT / "SHA256SUMS.txt").read_bytes()),
        "inputManifestSha256": sha((INPUT / "manifest.json").read_bytes()),
        "filesConsulted": {name: sha((INPUT / name).read_bytes()) for name in used_files if (INPUT / name).is_file()},
        "primaryReviewOpened": False, "blindReviewUsesOnlyCandidateFreeReviewContext": True,
        "supplementalPinnedSourceFilesRead": [
            "src/web/src/components/System/MediaCore/MediaCorePods.jsx",
            "src/web/src/components/System/Mesh/MeshEvidencePolicy.jsx",
            "src/web/src/components/Player/PlayerBar.jsx",
            "src/web/src/lib/discoveryShelf.js",
            "src/web/src/components/Lidarr/Lidarr.jsx",
        ],
        "selection": "Stable continuation ranks 953-977; exact candidate-free source/current cells and caller context were reviewed for all locales.",
        "hashOnlyHoldNote": "Rank 966 has 52 literal matches, all captured lines are UI layout/alignment attributes rather than localization calls; its 12 locale values are withheld as text-free holds pending a genuine caller.",
    }
    write_json(OUT / "input-inventory-note.json", input_note)
    summary = {
        "artifact": "slskdN PR #409 W953-W977 independent blind semantic review",
        "repository": "snapetech-org/slskdN", "pullRequest": 409, "branch": BRANCH,
        "head": HEAD, "tree": TREE, "window": "W953-W977", "continuationRankRange": [START, END],
        "remainingQueueRankRange": [853, 877], "sourceCount": 25, "localeCount": 12, "cellCount": len(rows),
        "decisions": dict(sorted(counts.items())), "proposalCount": len(proposals), "holdCellCount": len(holds),
        "holdSourceCount": len({r["continuationRank"] for r in holds}), "candidateFreeCallerlessSourceCount": manifest["sourcesWithoutCallers"],
        "contextAmbiguityHoldSourceCount": len(CONTEXT_HOLD_RANKS), "placeholderMarkupNumericProtectedLiteralChecks": "PASS",
        "blindReview": True, "primaryReviewAccessed": False, "crossReviewAccessed": False,
        "nativeSpeakerSignoff": False, "browserReview": False, "repositoryChangesApplied": False,
        "candidateFreeChecksumListSha256": input_note["candidateFreeChecksumListSha256"],
        "candidateFreeManifestSha256": input_note["inputManifestSha256"],
        "currentCellsSha256": sha((INPUT / "source-current-cells.jsonl").read_bytes()),
        "callerContextsSha256": sha((INPUT / "caller-contexts.jsonl").read_bytes()),
        "reviewedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    write_json(OUT / "summary.json", summary)
    (OUT / "README.md").write_text(f'''# slskdN PR #409 W953–W977 independent blind review

Blind semantic review of 300 candidate-free locale cells (25 source strings × 12 locales), pinned to head `{HEAD}` and tree `{TREE}`. The exact PR/API/branch/pull refs were checked before review; PR #409 was open and draft.

- Candidate-free checksum-list SHA-256: `{input_note['candidateFreeChecksumListSha256']}`.
- Decisions: `{json.dumps(dict(sorted(counts.items())), ensure_ascii=False, sort_keys=True)}`.
- Rank 966 has 52 captured literal matches, all layout/alignment attributes rather than localization calls. Its 12 locale cells are retained as hash-only holds with source and current-target text omitted.
- Every reviewed current value and proposal is bound to the source hash, catalog path/hash/blob, exact caller-context hash, and token checks. The candidate-free input reports no original callerless sources; the 12 holds mark this caller-context ambiguity.
- `primary-review/` was not opened. No primary or cross-review decisions were consulted. No repository/catalog/PR/workflow changes, tests, builds, scans, CI, browser review, or native-speaker signoff are claimed.

Run `python3 verify_blind_review.py /path/to/the-exact-fc8e42a-worktree` from this directory.
''', encoding="utf-8")
    live_pins = {
        "checkedBeforeReview": True, "repository": "snapetech-org/slskdN", "pullRequest": 409,
        "state": "open", "draft": True, "merged": False,
        "headRef": BRANCH, "apiHeadSha": HEAD, "remoteBranchSha": HEAD, "pullRefSha": HEAD,
        "headTree": TREE, "baseRef": "main", "baseApiSha": "f25d263a2a7cdb2c8f76c40c346cb10f749a9356",
        "liveMainRefSha": "bc6251ff4ea5a7e59f2d86e2400c90520601f46e",
        "evidence": "gh API pull 409, origin refs/heads/codex/slskdn-oidc-tooltip-localization-20261030, refs/pull/409/head, refs/heads/main, and exact clean detached source worktree.",
    }
    write_json(OUT / "pin-attestation.json", live_pins)
    # The manifest covers every packet file except itself and the checksum list.
    packet_files = sorted(p for p in OUT.iterdir() if p.is_file() and p.name not in {"manifest.json", "SHA256SUMS.txt"})
    manifest_out = {
        "artifact": "slskdN PR #409 W953-W977 blind review packet",
        "repository": "snapetech-org/slskdN", "pullRequest": 409, "branch": BRANCH,
        "head": HEAD, "tree": TREE, "window": "W953-W977", "sourceCount": 25,
        "localeCount": 12, "cellCount": 300, "decisionCounts": dict(sorted(counts.items())),
        "proposalCount": len(proposals), "holdCellCount": len(holds), "primaryReviewAccessed": False,
        "candidateFreeChecksumListSha256": input_note["candidateFreeChecksumListSha256"],
        "files": [{"path": p.name, "sha256": sha(p.read_bytes()), "bytes": p.stat().st_size} for p in packet_files],
    }
    write_json(OUT / "manifest.json", manifest_out)
    sums = sorted(p for p in OUT.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt")
    (OUT / "SHA256SUMS.txt").write_text("".join(f"{sha(p.read_bytes())}  {p.name}\n" for p in sums), encoding="utf-8")
    print(json.dumps({"result":"BLIND_REVIEW_BUILT", "head":HEAD, "tree":TREE, "cells":len(rows), "decisions":dict(sorted(counts.items())), "proposals":len(proposals), "hashOnlyHolds":len(holds)}, ensure_ascii=False, sort_keys=True))

if __name__ == "__main__": main()
