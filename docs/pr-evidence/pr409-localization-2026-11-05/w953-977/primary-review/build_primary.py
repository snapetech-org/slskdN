#!/usr/bin/env python3
"""Create the W83 independent primary review using sealed candidate-free input only."""
import collections
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent / "candidate-free" / "input"
REPO = Path(sys.argv[1]).resolve()
HEAD = "fc8e42a06363ceee762ae084bbe716953d4a5d94"
TREE = "e04aa06b8cfb0ee41cae90aef601a0552b5e85bd"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]

SOURCE_CONTEXT = {
    953: "MediaCore description of the request, acceptance, departure, and review flows for pod membership.",
    954: "Toast reports how many nearby atlas searches were started.",
    955: "Empty state in the Share Groups member list.",
    956: "Bridge settings description for stopping the local legacy-client bridge and disconnecting its active clients.",
    957: "MediaCore validation toast asking for pod JSON data before publishing a pod.",
    958: "Heading above the pod opinion review and read operations.",
    959: "Admin Policies numeric setting for the search-retention duration, measured in minutes.",
    960: "Accessible action label for disabling a named automation recipe.",
    961: "Fallback label for a room's browser tab.",
    962: "Mesh evidence-policy section heading for publication sent outward.",
    963: "Transfer-column label distinguishing a local file.",
    964: "Swarm Analytics retention/filter option covering three days.",
    965: "File Explorer confirmation asking whether a named file should be permanently deleted.",
    966: "Standalone spatial direction used for left-side alignment and placement in UI callers.",
    967: "MediaCore tooltip for changing a selected peer's pod role after verifying that peer.",
    968: "Messaging accessible label for collapsing a section and hiding its conversations.",
    969: "Shares tooltip for recounting files after file or exclusion changes.",
    970: "Discovery shelf policy-preview count for items promoted to a prominent position.",
    971: "Wishlist button that starts the enabled searches now.",
    972: "Playlist-intake policy label that displays the selected multi-artist policy value.",
    973: "Room creation modal label for a room restricted to invited members.",
    974: "Player modal heading for the playback queue.",
    975: "Automation recipe that scans the state of the media library.",
    976: "Lidarr toast reports how many files were queued for import.",
    977: "Media-server integration action that hands approved listening-intelligence gaps to the content-acquisition queue.",
}

# (target, rationale, confidence). These were drafted after the candidate-free packet sealed.
PROPOSALS = {
    (953, "ar"): ("تدفقات طلب عضوية Pod وقبولها ومغادرتها ومراجعتها.", "The current wording translates pod as a capsule and makes the verbs act on the flows. This names the Pod membership flows and their four actions.", "moderate"),
    (953, "de"): ("Abläufe zum Beantragen, Annehmen, Verlassen und Prüfen einer Pod-Mitgliedschaft.", "The current wording reads as a series of formal commands applied to workflows. The source describes workflows for these membership actions.", "moderate"),
    (953, "es"): ("Flujos para solicitar, aceptar, abandonar y revisar una membresía de pod.", "The current wording is a sequence of commands to request and leave the flows. The source describes flows for pod-membership actions.", "moderate"),
    (953, "fr"): ("Flux d’adhésion à un pod : demande, acceptation, départ et examen.", "The current imperative wording makes users request or leave the flows themselves. The source names the membership flows and their actions.", "moderate"),
    (953, "hi"): ("पॉड सदस्यता के अनुरोध, स्वीकृति, छोड़ने और समीक्षा के प्रवाह।", "The current imperatives act on the flows themselves. The source describes the flows for requesting, accepting, leaving, and reviewing pod membership.", "moderate"),
    (953, "id"): ("Alur untuk mengajukan, menerima, meninggalkan, dan meninjau keanggotaan pod.", "The current wording can read as commands to request and leave the flows. This describes the four pod-membership actions covered by the flows.", "moderate"),
    (953, "ja"): ("Pod メンバーシップの申請、承認、退会、審査の各フロー。", "The current verb sequence acts on the flows themselves. This names the flows for membership requests, acceptance, departure, and review.", "moderate"),
    (953, "ko"): ("Pod 멤버십 요청, 수락, 탈퇴 및 검토 흐름.", "The current wording makes the verbs operate on the flows. This describes the membership flows and the actions they cover.", "moderate"),
    (953, "pt-BR"): ("Fluxos para solicitar, aceitar, sair e revisar uma associação a um pod.", "The current wording reads as commands applied to the flows. This describes flows for the four pod-membership actions.", "moderate"),
    (953, "vi"): ("Quy trình yêu cầu, chấp nhận, rời và xem xét tư cách thành viên pod.", "The current wording says group membership and uses verbs as commands. This names the pod-membership flows and their actions.", "moderate"),
    (953, "zh-Hans"): ("Pod 成员资格的申请、接受、退出和审核流程。", "The current wording makes the verbs act on the flows. This names the Pod membership processes and their four actions.", "moderate"),
    (953, "zh-Hant"): ("Pod 成員資格的申請、接受、退出與審核流程。", "The current wording makes the verbs act on the flows. This names the Pod membership processes and their four actions.", "moderate"),

    (954, "ar"): ("بدأ {count} من عمليات البحث القريبة في الأطلس.", "The current wording puts the count after the search phrase and makes the nearby modifier hard to parse. This places the count before the searches.", "moderate"),
    (954, "de"): ("{count} nahegelegene Atlas-Suchen gestartet", "The current compound is singular and attaches the count to it awkwardly. Use the plural Atlas-Suchen after the count.", "moderate"),
    (954, "es"): ("Se iniciaron {count} búsquedas cercanas en el atlas.", "The current wording puts the count at the end and makes the atlas searches read as searches for nearby atlases. This puts the count before nearby searches.", "moderate"),
    (954, "fr"): ("{count} recherches à proximité dans l’atlas ont été lancées.", "The count currently trails the sentence, and the nearby modifier can attach to the atlas. This makes the count and proximity explicit.", "moderate"),
    (954, "hi"): ("आस-पास की {count} एटलस खोजें शुरू की गईं।", "The current word order places the count after the searches. This puts the number next to the plural search phrase.", "moderate"),
    (954, "id"): ("Memulai {count} pencarian atlas di sekitar.", "The current count follows the search phrase. This uses natural Indonesian order with the count before the nearby atlas searches.", "moderate"),
    (954, "ja"): ("近くのアトラス検索を {count} 件開始しました。", "The current wording lacks a Japanese counter for the number of searches. 件 makes the count relationship clear.", "moderate"),
    (954, "ko"): ("근처 아틀라스 검색 {count}건을 시작했습니다.", "The current wording leaves the count unmarked. 건 is the natural counter for this set of search jobs.", "moderate"),
    (954, "pt-BR"): ("Foram iniciadas {count} pesquisas próximas no atlas.", "The current wording puts the count last and makes its relationship to the searches unclear. This places the count before the searches.", "moderate"),
    (954, "vi"): ("Đã bắt đầu {count} lượt tìm kiếm atlas lân cận.", "The current wording places the count after the search phrase. This puts the count before a natural Vietnamese classifier phrase.", "moderate"),
    (954, "zh-Hans"): ("已开始 {count} 次附近的图集搜索。", "The current wording omits the Chinese counter for a number of searches. 次 makes the count grammatical.", "moderate"),
    (954, "zh-Hant"): ("已開始 {count} 次附近的圖集搜尋。", "The current wording omits the Chinese counter for a number of searches. 次 makes the count grammatical.", "moderate"),

    (956, "fr"): ("Arrêtez le pont local pour les clients d’ancienne génération et déconnectez ses clients actifs.", "The current translation uses existant for legacy, changing the meaning to an existing client bridge. This names the bridge for older-generation clients.", "high"),

    (957, "ar"): ("يرجى إدخال بيانات JSON الخاصة بـPod.", "The current word جراب means a pouch or case, not the MediaCore pod object, and JSON modifies the wrong noun. This keeps JSON and names the pod.", "moderate"),
    (957, "de"): ("Bitte geben Sie die JSON-Daten des Pods ein.", "The current word order makes JSON sound like a modifier on Pod data. This clearly asks for the pod's data in JSON format.", "moderate"),
    (957, "es"): ("Por favor, ingrese los datos JSON del pod.", "The current word order makes JSON modify the pod rather than its data. This clearly names JSON data belonging to the pod.", "moderate"),
    (957, "fr"): ("Veuillez saisir les données JSON du pod.", "The current word order makes JSON modify the pod rather than the data. This clearly asks for the pod data in JSON format.", "moderate"),
    (957, "hi"): ("कृपया Pod का JSON डेटा दर्ज करें।", "The current noun sequence is awkward. This clearly identifies the JSON data as belonging to the Pod.", "moderate"),
    (957, "id"): ("Silakan masukkan data JSON untuk pod.", "The current noun sequence is awkward and leaves the JSON relationship unclear. This directly names JSON data for the pod.", "moderate"),
    (957, "ja"): ("Pod の JSON データを入力してください。", "The current wording lacks the Japanese possessive relation between pod and JSON data. This expresses it directly.", "moderate"),
    (957, "pt-BR"): ("Insira os dados JSON do pod.", "The current word order makes JSON modify the pod rather than its data. This clearly asks for the pod data in JSON format.", "moderate"),
    (957, "vi"): ("Vui lòng nhập dữ liệu JSON của pod.", "The current translation uses nhóm, meaning group, for the MediaCore pod object. This identifies the pod and its JSON data.", "high"),

    (958, "de"): ("Meinungen prüfen", "As a section heading, the current formal imperative is unnecessarily conversational. This is the compact heading for reviewing pod opinions.", "moderate"),
    (958, "fr"): ("Consulter les avis", "The current wording means review notices rather than a section for reading opinions. This uses the standard UI term for user opinions.", "moderate"),
    (958, "ja"): ("意見を確認", "The current phrase combines review as a noun with opinions and reads unnaturally. This is a concise heading to inspect opinions.", "moderate"),

    (959, "ar"): ("مدة الاحتفاظ بعمليات البحث (بالدقائق)", "The current wording reads as searching for retention minutes. This names how long search records are retained and gives the unit.", "moderate"),
    (959, "de"): ("Aufbewahrungsdauer der Suchanfragen (Minuten)", "The current wording means search for retention minutes. This labels the duration that search queries are kept.", "moderate"),
    (959, "hi"): ("खोज इतिहास बनाए रखने की अवधि (मिनट)", "The current wording reads as an instruction to search for retention minutes. This labels the search-history retention duration.", "moderate"),

    (962, "ja"): ("外部への公開", "The current katakana phrase is a literal technical calque. This naturally describes publishing evidence outward from the service.", "moderate"),
    (962, "ko"): ("외부 공개", "The current wording is a literal loanword phrase. This naturally describes publication sent outside the service.", "moderate"),
    (962, "vi"): ("Công bố ra bên ngoài", "The current phrase means a publication sent to a foreign country. This describes making evidence public outside the service.", "high"),
    (962, "zh-Hans"): ("对外发布", "The current phrase means publishing abroad. This section governs evidence publication to outside recipients.", "high"),
    (962, "zh-Hant"): ("對外發布", "The current phrase means publishing abroad. This section governs evidence publication to outside recipients.", "high"),

    (964, "es"): ("3 días", "The current target omits the accent in días. This is the correctly spelled duration.", "high"),
    (966, "ar"): ("يسار", "The current target means left/departed as a verb. This source is a spatial direction for left-side alignment and placement.", "high"),

    (967, "ko"): ("peer를 확인한 뒤 Pod 역할을 변경해 중재자 또는 소유자 권한을 부여하거나 회수합니다.", "The current translation leaves moderator and owner in English and reads as mixed-language UI text. This uses the Korean role names and keeps the technical peer term.", "moderate"),

    (970, "ar"): ("إبراز", "This is an item-action count in the discovery shelf preview. The current verb form describes someone promoting instead of naming the featured-placement action.", "moderate"),
    (970, "de"): ("Hervorhebungen", "This is an item-action count in the discovery shelf preview. The current verb can mean funding or encouraging; this names featured placements.", "moderate"),
    (970, "es"): ("elementos destacados", "This label follows a count in the policy preview. A noun phrase for featured items fits that count better than the current infinitive.", "moderate"),
    (970, "fr"): ("mises en avant", "This label follows a count in the policy preview. The current infinitive does not fit that count; this names items featured on the shelf.", "moderate"),
    (970, "hi"): ("प्रमुख स्थान पर प्रदर्शन", "This is a count of items placed prominently on the discovery shelf. The current wording suggests a personnel promotion.", "moderate"),
    (970, "id"): ("penempatan unggulan", "This is a count of items featured on the discovery shelf. The current word means pushing or encouraging, not featured placement.", "moderate"),
    (970, "ja"): ("おすすめ表示", "This is an item-action count in the discovery shelf preview. The current verb means driving or promoting generally; this names featured display.", "moderate"),
    (970, "ko"): ("상위 노출", "This is an item-action count in the discovery shelf preview. The current verb means advertising; this names higher placement on the shelf.", "moderate"),
    (970, "pt-BR"): ("destaques", "This label follows an item count in the policy preview. The current infinitive does not fit that count; this names featured items.", "moderate"),
    (970, "vi"): ("lượt làm nổi bật", "This is a count of items featured on the discovery shelf. The current wording means encourage, not feature or promote an item.", "moderate"),
    (970, "zh-Hans"): ("推荐展示", "This is a count of items featured on the discovery shelf. The current verb means push or advance; this names recommendation display.", "moderate"),
    (970, "zh-Hant"): ("推薦展示", "This is a count of items featured on the discovery shelf. The current verb means push or advance; this names recommendation display.", "moderate"),

    (971, "ar"): ("تشغيل عمليات البحث المفعّلة", "The current short label omits the object and reads as running enabled things. The caller is a Wishlist searches button, so this names the enabled searches.", "moderate"),
    (971, "de"): ("Aktivierte Suchen starten", "The current wording is a clipped label with an awkward verb. The caller starts the enabled Wishlist searches.", "moderate"),
    (971, "es"): ("Ejecutar las búsquedas habilitadas", "The current wording omits its noun and leaves the feminine plural without a clear referent. The caller is a button for enabled searches.", "moderate"),
    (971, "fr"): ("Lancer les recherches activées", "The current label does not clearly state what is being run. The caller starts the enabled Wishlist searches.", "moderate"),
    (971, "hi"): ("सक्षम खोजें चलाएँ", "The current target means run enabled and omits the searches. The button starts enabled Wishlist searches.", "moderate"),
    (971, "id"): ("Jalankan pencarian yang diaktifkan", "The current target says run active ones without naming the searches. The caller starts enabled Wishlist searches.", "moderate"),
    (971, "ja"): ("有効な検索を実行", "The current target calls these enabled items rather than searches. The caller starts enabled Wishlist searches.", "moderate"),
    (971, "ko"): ("활성화된 검색 실행", "The current target calls these active items rather than searches. The caller starts enabled Wishlist searches.", "moderate"),
    (971, "pt-BR"): ("Executar as pesquisas ativadas", "The current target omits its noun and leaves the feminine plural unclear. The caller is a button for enabled searches.", "moderate"),
    (971, "vi"): ("Chạy các tìm kiếm đã bật", "The current target names enabled items but not the searches. The caller starts enabled Wishlist searches.", "moderate"),
    (971, "zh-Hans"): ("运行已启用的搜索", "The current target names enabled items generically. The caller starts enabled Wishlist searches.", "moderate"),
    (971, "zh-Hant"): ("執行已啟用的搜尋", "The current target names enabled items generically. The caller starts enabled Wishlist searches.", "moderate"),

    (972, "zh-Hant"): ("多位藝人政策：{policy}", "The current phrase means a multi-person policy, not a multi-artist policy. This names the selected policy for multiple artists.", "high"),

    (973, "de"): ("Privater Chatraum", "The current word Privatzimmer suggests a private bedroom. This is a private chat room in the room-creation dialog.", "high"),
    (973, "es"): ("Sala privada", "The current word habitación suggests a bedroom. This label names a private chat room.", "high"),
    (973, "fr"): ("Salon privé", "The current word chambre suggests a bedroom. This label names a private chat room.", "high"),
    (973, "id"): ("Ruang pribadi", "The current word kamar can suggest a bedroom. This is a private chat room, so ruang is the suitable term.", "moderate"),
    (973, "ja"): ("プライベートルーム", "The current word 個室 suggests a private booth or individual room. This label names a private chat room.", "moderate"),
    (973, "pt-BR"): ("Sala privada", "The current word quarto suggests a bedroom. This label names a private chat room.", "high"),

    (975, "de"): ("Medienbibliothek prüfen", "The current compound is an unnatural calque and can suggest a physical library health scan. This names checking the media library.", "moderate"),
    (975, "es"): ("Análisis del estado de la biblioteca", "The current word exploración means exploration rather than a scan or analysis. This names a media-library health check.", "high"),
    (975, "hi"): ("मीडिया लाइब्रेरी की स्थिति की जाँच", "The current wording is a literal health-scan calque. This clearly names a check of the media library's state.", "moderate"),
    (975, "id"): ("Pemeriksaan kondisi pustaka", "The current term perpustakaan suggests a physical library. Pustaka is the appropriate term for a digital or media library.", "moderate"),
    (975, "ja"): ("ライブラリの状態をスキャン", "The current katakana compound is a literal calque. This naturally names scanning the library's status.", "moderate"),
    (975, "ko"): ("미디어 라이브러리 상태 검사", "The current 도서관 means a physical library. This is a scan of the media library's state.", "high"),
    (975, "zh-Hans"): ("媒体库状态扫描", "The current wording can mean a physical library health scan. This names scanning the media library's state.", "high"),
    (975, "zh-Hant"): ("媒體庫狀態掃描", "The current wording can mean a physical library health scan. This names scanning the media library's state.", "high"),

    (976, "ar"): ("تمت إضافة {safeCandidates} من الملفات إلى قائمة انتظار استيراد Lidarr.", "The current parenthetical file(s) phrase is awkward and puts the count after the noun. This keeps Lidarr exact and places the count before the files.", "moderate"),
    (976, "de"): ("Lidarr-Import in der Warteschlange: {safeCandidates} Datei(en)", "The current compound attaches the count directly to Datei(en) and uses awkward ordering. This keeps the count and optional plural marker separate.", "moderate"),
    (976, "es"): ("Importación de Lidarr en cola: {safeCandidates} archivo(s)", "The current wording puts archivo(s) before the count. This places the count with the queued Lidarr import status.", "moderate"),
    (976, "fr"): ("Importation Lidarr en attente : {safeCandidates} fichier(s)", "The current wording puts fichier(s) before the count. This places the count with the queued Lidarr import status.", "moderate"),
    (976, "hi"): ("Lidarr आयात के लिए {safeCandidates} फ़ाइलें कतार में जोड़ी गईं।", "The current parenthetical repeats the word file and puts the noun before the count. This states that the counted files were queued for Lidarr import.", "moderate"),
    (976, "id"): ("Impor Lidarr dalam antrean: {safeCandidates} file", "The current word antri is not the natural queue noun and the count comes after file. This uses antrean and natural count order.", "moderate"),
    (976, "ja"): ("Lidarr のインポート用に {safeCandidates} 件のファイルをキューに追加しました。", "The current phrase lacks a Japanese counter and presents the count as a bare file quantity. 件のファイル is natural for a queued file count.", "moderate"),
    (976, "ko"): ("Lidarr 가져오기 대기열에 파일 {safeCandidates}개가 추가되었습니다.", "The current target omits the Korean counter and leaves the file count as an English-style noun sequence. This uses the natural 개 counter.", "moderate"),
    (976, "pt-BR"): ("Importação do Lidarr na fila: {safeCandidates} arquivo(s)", "The current target places arquivo(s) before the count. This places the count next to the queued import status.", "moderate"),
    (976, "vi"): ("Đã đưa {safeCandidates} tệp vào hàng đợi nhập của Lidarr.", "The current parenthetical các tệp is awkward before the count. This states naturally that the counted files were queued for import.", "moderate"),
    (976, "zh-Hans"): ("已将 {safeCandidates} 个文件加入 Lidarr 导入队列。", "The current wording omits the Chinese classifier for files. 个 makes the count grammatical and preserves Lidarr.", "moderate"),
    (976, "zh-Hant"): ("已將 {safeCandidates} 個檔案加入 Lidarr 匯入佇列。", "The current wording omits the Chinese classifier for files. 個 makes the count grammatical and preserves Lidarr.", "moderate"),

    (977, "ar"): ("تسليم إلى قائمة انتظار اقتناء المحتوى", "The current wording reads as handing off the queue itself. The caller describes sending content candidates to an acquisition queue.", "moderate"),
    (977, "de"): ("Übergabe an die Medienbeschaffungswarteschlange", "The current wording names transfer of the queue rather than a handoff to it. This describes handing work to a media-acquisition queue.", "moderate"),
    (977, "es"): ("Traspaso a la cola de adquisición de contenido", "The current wording can mean transfer of the acquisition queue. This names a handoff to the queue for content candidates.", "moderate"),
    (977, "fr"): ("Transmission vers la file d’attente d’acquisition de contenu", "The current wording can mean transfer of the queue itself. This names a handoff to the content-acquisition queue.", "moderate"),
    (977, "hi"): ("सामग्री प्राप्ति कतार को सौंपना", "The current target can suggest a corporate acquisition queue. This names handing content candidates to an acquisition queue.", "moderate"),
    (977, "id"): ("Penyerahan ke antrean perolehan konten", "The current term akuisisi can suggest a corporate acquisition. This names a handoff to a content-acquisition queue.", "moderate"),
    (977, "ja"): ("コンテンツ取得キューへの引き渡し", "The current wording can read as handing off the queue itself. This names handing content candidates to the acquisition queue.", "moderate"),
    (977, "ko"): ("콘텐츠 확보 대기열로 전달", "The current wording names a handoff of the queue. This describes transferring content candidates into the acquisition queue.", "moderate"),
    (977, "pt-BR"): ("Encaminhamento para a fila de aquisição de conteúdo", "The current wording can read as transfer of the queue itself. This names forwarding content candidates to that queue.", "moderate"),
    (977, "vi"): ("Chuyển giao vào hàng đợi tiếp nhận nội dung", "The current term mua lại means buy back. This describes handing content candidates to an acquisition queue.", "moderate"),
    (977, "zh-Hans"): ("移交至内容获取队列", "The current term 切换 means switching and does not express a handoff. This names transfer to the content-acquisition queue.", "moderate"),
    (977, "zh-Hant"): ("移交至內容取得佇列", "The current term 切換 means switching and does not express a handoff. This names transfer to the content-acquisition queue.", "moderate"),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tsha(text):
    return sha(text.encode("utf-8"))


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def protected(text):
    values = set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", text))
    values.update(x for x in ("slskdN", "PodCore", "Wishlist", "soulfind", "FFmpeg", "Lidarr") if x in text)
    return sorted(values)


def token_check(source, current, candidate=None):
    ph = lambda s: collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", s))
    tags = lambda s: collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", s))
    nums = lambda s: ["".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in n) for n in re.findall(r"\d+", s)]
    source_nums = nums(source)
    source_literals = protected(source)
    def check(value):
        return {"placeholderParity": ph(source) == ph(value), "markupParity": tags(source) == tags(value),
                "numericTokensPreserved": all(nums(value).count(x) >= n for x, n in collections.Counter(source_nums).items()),
                "protectedLiteralsPreserved": all(token in value for token in source_literals),
                "missingProtectedLiterals": [token for token in source_literals if token not in value]}
    return {"current": check(current), "candidate": check(candidate) if candidate is not None else None}


def verify_input():
    checksums = {}
    for line in (INPUT / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        path = INPUT / name
        if not path.is_file() or sha(path.read_bytes()) != digest:
            raise SystemExit("REFUSED: candidate-free input checksum " + name)
        checksums[name] = digest
    actual = {p.relative_to(INPUT).as_posix() for p in INPUT.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"}
    if set(checksums) != actual:
        raise SystemExit("REFUSED: candidate-free input checksum inventory")
    manifest = json.loads((INPUT / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("head") != HEAD or manifest.get("tree") != TREE or manifest.get("candidateFree") is not True or manifest.get("window") != "W83":
        raise SystemExit("REFUSED: candidate-free packet identity")
    if subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip() != HEAD:
        raise SystemExit("REFUSED: primary worktree head drift")
    if subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD^{tree}"], text=True).strip() != TREE:
        raise SystemExit("REFUSED: primary worktree tree drift")
    if subprocess.check_output(["git", "-C", str(REPO), "status", "--porcelain=v1"], text=True).strip():
        raise SystemExit("REFUSED: primary worktree not clean")
    return manifest, sha((INPUT / "manifest.json").read_bytes()), sha((INPUT / "SHA256SUMS.txt").read_bytes())


def main():
    input_manifest, input_manifest_sha, input_checksums_sha = verify_input()
    rows = read_jsonl(INPUT / "source-current-cells.jsonl")
    if len(rows) != 300 or len({(row["continuationRank"], row["locale"]) for row in rows}) != 300:
        raise SystemExit("REFUSED: candidate-free cell coverage")

    output, corrections, holds = [], [], []
    for source_row in rows:
        rank, locale = source_row["continuationRank"], source_row["locale"]
        source, current = source_row["source"], source_row["currentTarget"]
        proposal = PROPOSALS.get((rank, locale))
        if source_row["callerCount"] == 0:
            disposition, target = "hold", None
            rationale, confidence = "No pinned production caller supplies enough context to decide this cell.", "high"
        elif proposal:
            target, rationale, confidence = proposal
            disposition = "correction"
        else:
            target = None
            disposition = "accept-current"
            rationale = f"The current translation accurately conveys the source in this caller context: {SOURCE_CONTEXT[rank]}"
            confidence = "moderate"
        token_evidence = token_check(source, current, target)
        if target is not None:
            candidate_check = token_evidence["candidate"]
            if not all(candidate_check[key] for key in ("placeholderParity", "markupParity", "numericTokensPreserved", "protectedLiteralsPreserved")):
                raise SystemExit(f"REFUSED: candidate token mismatch at {rank}/{locale}: {candidate_check}")
        row = {"schemaVersion": 1, "reviewPass": "primary", "head": HEAD, "tree": TREE,
               "continuationRank": rank, "remainingQueueRank": source_row["remainingQueueRank"],
               "sourceId": source_row["sourceId"], "sourceSha256": source_row["sourceSha256"],
               "locale": locale, "catalogPath": source_row["catalogPath"],
               "catalogFileSha256": source_row["catalogFileSha256"], "catalogGitBlob": source_row["catalogGitBlob"],
               "source": source, "sourceTextIncluded": True, "currentTarget": current,
               "currentTargetSha256": source_row["currentTargetSha256"], "currentTargetTextIncluded": True,
               "callerCount": source_row["callerCount"], "callerContextSha256": source_row["callerContextSha256"],
               "callerRefs": source_row["callerRefs"], "disposition": disposition, "rationale": rationale,
               "confidence": confidence, "tokenCheck": token_evidence,
               "candidateTarget": target, "candidateTargetSha256": tsha(target) if target is not None else None,
               "candidateTargetTextIncluded": target is not None}
        output.append(row)
        if disposition == "correction":
            corrections.append({k: row[k] for k in ("continuationRank", "remainingQueueRank", "sourceId", "sourceSha256", "locale",
                "currentTargetSha256", "candidateTarget", "candidateTargetSha256", "rationale", "confidence")})
        if disposition == "hold":
            holds.append({"continuationRank": rank, "remainingQueueRank": source_row["remainingQueueRank"],
                          "sourceId": source_row["sourceId"], "sourceSha256": source_row["sourceSha256"],
                          "locale": locale, "currentTargetSha256": source_row["currentTargetSha256"],
                          "callerCount": 0, "callerContextSha256": source_row["callerContextSha256"],
                          "holdReasonCode": "NO_PINNED_PRODUCTION_CALLER", "holdReasonSha256": tsha(rationale),
                          "sourceTextIncluded": False, "targetTextIncluded": False})

    def write_json(name, obj):
        (ROOT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    def write_jsonl(name, items):
        with (ROOT / name).open("w", encoding="utf-8", newline="\n") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")

    write_jsonl("primary-review.jsonl", output)
    write_jsonl("corrections.jsonl", corrections)
    write_jsonl("holds-hash-only.jsonl", holds)
    counts = collections.Counter(row["disposition"] for row in output)
    write_json("summary.json", {"artifact": "slskdN PR #409 W83 primary review", "window": "W83", "head": HEAD, "tree": TREE,
        "inputManifestSha256": input_manifest_sha, "sourceCount": 25, "cellCount": 300, "localeCount": 12,
        "dispositionCounts": dict(counts), "correctionCount": len(corrections), "holdCellCount": len(holds),
        "heldSourceRanks": sorted({row["continuationRank"] for row in holds}), "sourceRewriteRecommendations": 0,
        "candidateFreeInputOnly": True, "blindReviewUsed": False, "crossReviewUsed": False,
        "rootAdjudicationDone": False, "nativeSpeakerSignoff": False, "browserReview": False})
    readme = ("# slskdN PR #409 W83 primary review\n\n"
        "This independent primary review covers continuation ranks 953–977 and remaining-queue ranks 853–877: 300 cells across 12 locales. "
        "It is tied to candidate-free input manifest SHA-256 `" + input_manifest_sha + "`, head `" + HEAD + "`, and tree `" + TREE + "`.\n\n"
        "The review records " + str(counts["accept-current"]) + " accept-current cells, " + str(counts["correction"]) +
        " correction candidates, and " + str(counts["hold"]) + " holds. Candidate translations preserve placeholders, markup, numeric tokens, and protected literals.\n\n"
        "This is primary review only and used the sealed candidate-free input without blind or cross-review proposals. No root adjudication, browser review, or native-speaker signoff is claimed. "
        "No catalog/source/workflow edits are proposed for application; no tests, builds, scans, CI, merge, release, or tag were performed.\n")
    (ROOT / "README.md").write_text(readme, encoding="utf-8")

    payloads = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and p.name not in {"manifest.json", "SHA256SUMS.txt"})
    file_rows = [{"path": name, "sha256": sha((ROOT / name).read_bytes()), "bytes": (ROOT / name).stat().st_size} for name in payloads]
    write_json("manifest.json", {"artifact": "slskdN PR #409 W83 primary review", "schemaVersion": 1,
        "repository": "snapetech-org/slskdN", "pullRequest": 409, "window": "W83", "head": HEAD, "tree": TREE,
        "candidateFreeInputManifestSha256": input_manifest_sha, "candidateFreeInputChecksumListSha256": input_checksums_sha,
        "sourceCount": 25, "localeCount": 12, "cellCount": len(output), "dispositionCounts": dict(counts),
        "correctionCount": len(corrections), "holdCellCount": len(holds), "sourceRewriteRecommendations": 0,
        "candidateFreeInputOnly": True, "blindReviewUsed": False, "crossReviewUsed": False,
        "rootAdjudicationDone": False, "nativeSpeakerSignoff": False, "browserReview": False, "files": file_rows})
    sealed = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    (ROOT / "SHA256SUMS.txt").write_text("\n".join(f"{sha((ROOT / name).read_bytes())}  {name}" for name in sealed) + "\n", encoding="utf-8")
    print(json.dumps({"result": "SEALED-PRIMARY", "head": HEAD, "tree": TREE, "cellCount": len(output),
                      "dispositions": dict(counts), "corrections": len(corrections), "holds": len(holds),
                      "inputManifestSha256": input_manifest_sha}, indent=2))


if __name__ == "__main__":
    main()
