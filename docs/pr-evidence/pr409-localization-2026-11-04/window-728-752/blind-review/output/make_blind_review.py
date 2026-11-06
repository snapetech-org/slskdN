#!/usr/bin/env python3
"""Build the sealed blind review outputs from the copied candidate-free packet."""
import hashlib, json
from pathlib import Path
from datetime import datetime, timezone

OUT=Path(__file__).resolve().parent
IN=OUT/'input'
def jline(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def read_jsonl(name): return [json.loads(s) for s in (IN/name).read_text(encoding='utf-8').splitlines() if s.strip()]

PROPOSED={
 'src_2c318477f5e52efc': {'es':'Rechazado en la bandeja de descubrimiento y ocultado ante la misma evidencia.','fr':'Rejeté dans la boîte de découverte et masqué pour les mêmes preuves.'},
 'src_2c367aa22044c2c6': {'de':'Speichern Sie die aktuellen adversarialen Einstellungen auf diesem Server.','fr':'Enregistrez les paramètres adversariaux actuels sur ce serveur.','id':'Simpan pengaturan adversarial saat ini di server ini.','pt-BR':'Salve as configurações adversariais atuais neste servidor.','vi':'Lưu cài đặt đối kháng hiện tại trên máy chủ này.'},
 'src_2c4939b8285ea2f0': {'ar':'انتهى: {title}.'},
 'src_2c50bc62a8f1322a': {'ja':'この項目にはローカル検証の証拠があります。','ko':'이 항목에는 로컬 검증 근거가 있습니다.','vi':'Mục này có bằng chứng xác minh cục bộ.','zh-Hans':'此项目有本地验证证据。','zh-Hant':'此項目有本機驗證證據。'},
 'src_2c975542e8a238be': {'id':'Urutkan pekerjaan secara menaik'},
 'src_2cab593b7fab5716': {'de':'Verfolgte Peers','es':'Pares rastreados','hi':'ट्रैक किए गए पीयर','id':'Peer yang Dilacak','vi':'Peers được theo dõi','zh-Hans':'追踪的对等节点','zh-Hant':'追蹤的對等節點'},
 'src_2cbd71f1cb169516': {'id':'Jendela Batch (ms)'},
 'src_2cc71113f8e6356b': {'de':'Raum-Update erneut senden','es':'Reintentar la actualización de la transmisión a la sala','hi':'कक्ष प्रसारण अपडेट का फिर से प्रयास करें।','ja':'ルームへの配信更新を再試行する','vi':'Thử gửi lại bản cập nhật phát tới phòng'},
 'src_2cdab1ba1ad1fdfe': {'ar':'، تم تجميع {duplicatesRemoved} من التكرارات','de':', {duplicatesRemoved} Duplikate zusammengefasst','es':', {duplicatesRemoved} duplicados agrupados','fr':', {duplicatesRemoved} doublons regroupés','hi':', {duplicatesRemoved} डुप्लिकेट समेटे गए','id':', {duplicatesRemoved} duplikat dikelompokkan','ja':'、重複項目を{duplicatesRemoved}件折りたたみました','ko':', 중복 항목 {duplicatesRemoved}개를 접었습니다.','pt-BR':', {duplicatesRemoved} duplicatas agrupadas','vi':', đã gộp {duplicatesRemoved} mục trùng lặp'},
 'src_2d07fb50b9d34053': {'ar':'حدّد جميع مشكلات حالة المكتبة المحمّلة وعددها {length}','de':'Alle {length} geladenen Probleme zum Zustand der Bibliothek auswählen','es':'Seleccionar todos los {length} problemas del estado de la biblioteca cargados','fr':'Sélectionner tous les {length} problèmes d’intégrité de la bibliothèque chargés','hi':'लाइब्रेरी की सभी {length} लोड की गई स्वास्थ्य समस्याएँ चुनें।','id':'Pilih semua {length} masalah kesehatan pustaka yang dimuat','ja':'読み込み済みのライブラリ健全性の問題を{length}件すべて選択します','ko':'로드된 라이브러리 상태 문제 {length}개를 모두 선택하세요.','pt-BR':'Selecione todos os {length} problemas de integridade da biblioteca carregados','vi':'Chọn tất cả {length} vấn đề sức khỏe thư viện đã tải','zh-Hans':'选择全部 {length} 个已加载的库健康问题','zh-Hant':'選取所有 {length} 個已載入的媒體庫健康問題'},
 'src_2d275a74912cca2e': {'ar':'المقياس','de':'Kennzahl','es':'Métrica','ko':'지표','zh-Hans':'指标','zh-Hant':'指標'},
 'src_2d39938573431ca9': {'ar':'(جارٍ الاتصال بالغرفة)','de':'(Verbindung zum Raum wird hergestellt)','es':'(conectando a la sala)','fr':'(connexion à la salle en cours)','id':'(menghubungkan ke ruang)','ja':'(ルームに接続中)','ko':'(방에 연결 중)','pt-BR':'(conectando à sala)','vi':'(đang kết nối với phòng)','zh-Hans':'（正在连接到房间）','zh-Hant':'（正在連線至房間）'},
 'src_2d4bc8b68054a858': {'de':'Schließen Sie das Fenster mit den Inhalten der Freigabe.','es':'Cierra la ventana que muestra el contenido de la carpeta compartida.','hi':'साझा किए गए फ़ोल्डर की सामग्री दिखाने वाली विंडो बंद करें।','id':'Tutup jendela yang menampilkan isi folder bersama.','ja':'共有フォルダーの内容を表示するウィンドウを閉じます。','ko':'공유 폴더의 내용을 표시하는 창을 닫습니다.','pt-BR':'Feche a janela que exibe o conteúdo da pasta compartilhada.','vi':'Đóng cửa sổ hiển thị nội dung thư mục được chia sẻ.'},
 'src_2d5d62371cec0cdc': {'pt-BR':'O interesse {interest} foi adicionado.','vi':'Đã thêm {interest} vào danh sách quan tâm.'}
}
ISSUES={
 'src_2c318477f5e52efc':'The current wording weakens suppressed or changes evidence to unrelated items; the proposals preserve rejection plus suppression for the same evidence.',
 'src_2c367aa22044c2c6':'The current wording in these locales reads as an opponent’s settings, contradictory settings, hostility, or an adversary’s property. The proposals retain the technical adversarial-settings sense.',
 'src_2c4939b8285ea2f0':'The Arabic target is a noun meaning finishing; this playback status needs finished as a completed state.',
 'src_2c50bc62a8f1322a':'These targets use a geographic or on-site sense of local; software-local verification is more clearly rendered with the computing sense.',
 'src_2c975542e8a238be':'The Indonesian wording makes ascending order sound like sorting by size; the source refers to order direction for a sortable job list.',
 'src_2cab593b7fab5716':'These targets translate network peers as coworkers or colleagues; the caller is a network reputation statistic counting peers.',
 'src_2cbd71f1cb169516':'The Indonesian unit is mistyped as md; the source specifies milliseconds (ms).',
 'src_2cc71113f8e6356b':'The current phrase is awkward or leaves the retry/update action unclear in this button context; the proposal expresses retrying or resending the room update.',
 'src_2cdab1ba1ad1fdfe':'The current phrase is ungrammatical or uses a physical-collapse/reduction sense. The proposals describe duplicate entries being grouped or collapsed in the player list.',
 'src_2d07fb50b9d34053':'The current word order attaches the count to loaded with/by or otherwise makes the dynamic count unclear. The proposals identify all loaded issues and retain the count.',
 'src_2d275a74912cca2e':'In the metrics table this is a measurement/indicator field, not the metric system; the proposal uses the table-field sense.',
 'src_2d39938573431ca9':'The current target says connected or uses a bedroom/physical-room term; this is an in-progress connection status for a listening-party room.',
 'src_2d4bc8b68054a858':'The current wording reads as a window for sharing content; the caller is a window displaying the contents of an existing share.',
 'src_2d5d62371cec0cdc':'The current wording is gendered or describes a hobby/concern; the caller adds a Soulseek discovery interest to the interest list.'
}
ACCEPT_NOTES={
 'src_2c23db5f66510222':'The caller uses this as the short-folder candidate reason in album-complete search ranking; the target preserves folder size and candidate status.',
 'src_2c25a3f9b35b9916':'The target preserves the close action, unsaved state, and YAML configuration context.',
 'src_2c2fe286cef4b7d3':'The target preserves review, integration readiness, path mapping, and the dynamic adapter label.',
 'src_2c318477f5e52efc':'The target preserves rejection in Discovery Inbox and suppression tied to the same evidence.',
 'src_2c367aa22044c2c6':'The target preserves saving the current adversarial configuration to this server; no clear meaning error found in this locale.',
 'src_2c40cadadfed4ecc':'The target reports the active playback state and preserves the title placeholder.',
 'src_2c4939b8285ea2f0':'The target reports completed playback and preserves the title placeholder.',
 'src_2c50bc62a8f1322a':'The target indicates that the item has local verification evidence; no clear locale-specific meaning error found.',
 'src_2c8b1ed734a48fb6':'The target is an instruction to paste exported media-server play history and fits the aria-label caller.',
 'src_2c975542e8a238be':'The target describes sorting jobs in ascending order in a sort control.',
 'src_2c9f46eb2668f83b':'The target identifies the Classic Dark theme option and retains the named theme distinction.',
 'src_2cab593b7fab5716':'The target identifies the tracked network peers count; no clear peer-versus-colleague mismatch found in this locale.',
 'src_2cbd71f1cb169516':'The target identifies the batch window and milliseconds unit.',
 'src_2cc71113f8e6356b':'The target identifies retrying the room broadcast update in the host control.',
 'src_2ccfbbb3e086d4c3':'The target preserves the clipboard failure, visible conflict report, and manual-copy instruction.',
 'src_2cdab1ba1ad1fdfe':'The target describes duplicates being collapsed in the displayed player list and retains the dynamic count.',
 'src_2cecb583cf178b5a':'The target preserves both audio format names and the plus sign.',
 'src_2cff9baabf56ca00':'The target is a concise Import action across the supplied button and status contexts.',
 'src_2d07fb50b9d34053':'The target requests selection of all loaded Library Health issues and preserves the dynamic count.',
 'src_2d12a36f190d57f8':'The target preserves the product name slskdN and the discovered-client empty-state meaning.',
 'src_2d275a74912cca2e':'The target identifies the metric/measurement column in a metrics table.',
 'src_2d39938573431ca9':'The target expresses a pending connection to the listening-party room.',
 'src_2d4bc8b68054a858':'The target asks the user to close the window showing share contents.',
 'src_2d5d62371cec0cdc':'The target reports adding the supplied interest and preserves the dynamic interest placeholder.',
 'src_2d6044473bc8cfc9':'The target labels the average search time statistic, whose value is shown in milliseconds.'
}
ISSUE_CLASS={'src_2c318477f5e52efc':'semantic-precision','src_2c367aa22044c2c6':'technical-term','src_2c4939b8285ea2f0':'grammar-state','src_2c50bc62a8f1322a':'technical-term','src_2c975542e8a238be':'semantic-precision','src_2cab593b7fab5716':'domain-term','src_2cbd71f1cb169516':'unit-typo','src_2cc71113f8e6356b':'grammar-action','src_2cdab1ba1ad1fdfe':'grammar-semantic','src_2d07fb50b9d34053':'placeholder-order','src_2d275a74912cca2e':'domain-term','src_2d39938573431ca9':'status-meaning','src_2d4bc8b68054a858':'caller-context','src_2d5d62371cec0cdc':'grammar-domain'}
cells=read_jsonl('source-current-cells.jsonl')
now=datetime.now(timezone.utc).isoformat(timespec='seconds')
ledger=[]; proposals=[]
for c in cells:
 sid,loc=c['sourceId'],c['locale']
 target=PROPOSED.get(sid,{}).get(loc)
 revise=target is not None
 row={'reviewId':f"w74:{c['continuationRank']}:{sid}:{loc}",'window':'W74','continuationRank':c['continuationRank'],'remainingQueueRank':c['remainingQueueRank'],'sourceId':sid,'source':c['source'],'sourceSha256':c['sourceSha256'],'catalogKey':c['catalogKey'],'locale':loc,'catalogPath':c['catalogPath'],'catalogFileSha256':c['catalogFileSha256'],'catalogGitBlob':c['catalogGitBlob'],'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'callerRefs':c['callerRefs'],'disposition':'revise-current' if revise else 'accept-current','issueClass':ISSUE_CLASS[sid] if revise else None,'rationale':ISSUES[sid] if revise else ACCEPT_NOTES[sid],'proposedTarget':target,'reviewConfidence':'moderate','nativeSpeakerApproval':False,'reviewedAtUtc':now,'placeholderEvidence':c['placeholderEvidence'],'markupEvidence':c['markupEvidence'],'sourceNumericTokens':c['sourceNumericTokens'],'sourceProtectedLiterals':c['sourceProtectedLiterals'],'containsCandidate':False}
 ledger.append(row)
 if revise:
  proposals.append({k:row[k] for k in ('reviewId','sourceId','locale','catalogPath','catalogKey','sourceSha256','currentTargetSha256','currentTarget','proposedTarget','issueClass','rationale','callerContextSha256')})
(OUT/'blind-review-ledger.jsonl').write_text(''.join(jline(x)+'\n' for x in ledger),encoding='utf-8')
(OUT/'blind-review-proposals.jsonl').write_text(''.join(jline(x)+'\n' for x in proposals),encoding='utf-8')
(OUT/'blind-review-holds.jsonl').write_text('',encoding='utf-8')
counts={k:sum(x['disposition']==k for x in ledger) for k in ('accept-current','revise-current','hold-text-free')}
summary={'result':'SEALED','window':'W74','rankRange':[728,752],'remainingQueueRange':[628,652],'repository':'snapetech-org/slskdN','pullRequest':409,'reviewedHead':'70e5beffd5cd8d68b8aedffa5c85d16e2cc19b3f','reviewedTree':'14620c63bee971428fa1cd6cf1f4e944b86056a7','cellsReviewed':len(ledger),'sourcesReviewed':len({x['sourceId'] for x in ledger}),'locales':sorted({x['locale'] for x in ledger}),'counts':counts,'proposalCount':len(proposals),'holdCount':0,'holdPolicy':'No text-free holds; the copied caller context was sufficient to make a bounded disposition for every cell.','reviewMethod':'Independent clean-blind review of copied candidate-free source cells and their included caller context. No other review outputs or repository files were consulted.','nativeSpeakerApproval':False,'browserReviewClaimed':False,'reviewConfidence':'moderate','sealedAtUtc':now,'prAttestationBefore':'PR-attestation-before.json','prAttestationAfter':'PR-attestation-after.json','inputDirectory':'input/'}
(OUT/'review-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
readme=f"""# slskdN PR #409 W74 clean-blind review

- Reviewed window: W74, continuation ranks 728–752 (remaining queue ranks 628–652).
- Pin: 70e5beffd5cd8d68b8aedffa5c85d16e2cc19b3f / tree 14620c63bee971428fa1cd6cf1f4e944b86056a7.
- Scope: 25 source rows × 12 locales = {len(ledger)} cells.
- Dispositions: {counts['accept-current']} accept current, {counts['revise-current']} revise current, 0 text-free holds.
- The exact candidate-free input directory is copied under input/; the review used its source cells and bundled caller context. No staging, primary-review, proposal, or repository content was read.
- blind-review-proposals.jsonl contains proposed targets only for clear, caller-supported corrections. blind-review-holds.jsonl is intentionally empty.
- Confidence is moderate. No native-speaker approval or browser review is claimed.
- Live PR state/head/tree were rechecked and recorded in PR-attestation-before.json and PR-attestation-after.json; both must remain OPEN/DRAFT at the reviewed pin.

Run python3 verify_blind_review.py from any location after keeping the input/ folder beside the script. The verifier checks the copied packet, exact 300-cell coverage, source/current hashes, proposal linkage, token and protected-literal preservation, PR attestations, summary counts, and output checksums.
"""
(OUT/'README.md').write_text(readme,encoding='utf-8')
print(json.dumps({'ledger':len(ledger),'proposals':len(proposals),'counts':counts,'output':str(OUT)},indent=2))

