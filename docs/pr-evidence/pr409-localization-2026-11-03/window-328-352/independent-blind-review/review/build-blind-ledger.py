#!/usr/bin/env python3
"""Build a sealed independent blind review ledger from W58 candidate-free cells."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w58-independent-blind-20261103')
INPUT = ROOT / 'input'
OUT = ROOT / 'review'
EXPECTED_HEAD = '47735fbdb8df3de8dc5fd297c2717dc332764431'
EXPECTED_TREE = 'b29397903a036d40af1c6551dedbe070e735cfed'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

# Entries are (disposition, exact candidate, reason, confidence).
proposals = {
    (328,'zh-Hant'): ('correction','HTTPS 連接埠','Traditional Chinese uses 連接埠 for a network port; 端口 is the Simplified form. HTTPS remains an opaque protocol acronym.','high'),
    (329,'ar'): ('correction','أنشئ أطلسًا دائمًا داخل الصفحة من حقول البذور الحالية بدلًا من فتح نافذة منبثقة مؤقتة.','ثابت means fixed or stable rather than persistently retained, and نموذج مؤقت reads as a temporary form/model rather than a modal dialog.','moderate'),
    (329,'de'): ('refinement','Erstellen Sie aus den aktuellen Seed-Feldern einen dauerhaft auf der Seite eingebetteten Atlas, statt ein temporäres Dialogfenster zu öffnen.','The current In-Page-Atlas and Modal are untranslated English compounds; this states the in-page persistent atlas and the temporary dialog in idiomatic German.','moderate'),
    (329,'hi'): ('correction','वर्तमान बीज फ़ील्ड से पेज के भीतर स्थायी एटलस बनाएँ, अस्थायी मोडल खोलने के बजाय।','सतत means continuous; स्थायी expresses persistent. The rest is clear in the UI context.','moderate'),
    (329,'ja'): ('refinement','現在のシードフィールドからページ内に永続的なアトラスを構築し、一時的なモーダルを開かないようにします。','The existing compound ページはめ込み永続アトラス is difficult to parse; the proposal preserves the in-page persistent atlas and modal contrast.','moderate'),
    (329,'ko'): ('refinement','현재 시드 필드에서 페이지 안에 지속적으로 유지되는 아틀라스를 만들고, 임시 모달을 열지 않습니다.','The current 인페이지 compound is awkward. This makes the persistent in-page atlas and modal distinction clear.','moderate'),
    (329,'pt-BR'): ('refinement','Crie um atlas persistente dentro da página usando os campos de semente atuais, em vez de abrir um modal temporário.','The current campos iniciais means initial fields and loses the technical seed-field meaning.','moderate'),
    (329,'vi'): ('correction','Tạo một sơ đồ tổng quan thường trực trong trang từ các trường seed hiện tại, thay vì mở hộp thoại tạm thời.','The current liên tục means continuous and phương thức means method or mode; the source describes a persistent in-page atlas instead of a temporary modal.','moderate'),
    (329,'zh-Hans'): ('correction','根据当前种子字段在页面内构建持久化图谱，而不是打开临时对话框。','图集 suggests a picture collection, while the pinned caller is a discovery graph atlas; 模式 means mode, not modal dialog.','moderate'),
    (329,'zh-Hant'): ('correction','根據目前種子欄位在頁面內建構持久化圖譜，而不是開啟臨時對話框。','圖集 suggests a picture collection, while the pinned caller is a discovery graph atlas; 模式 means mode, not modal dialog.','moderate'),
    (332,'id'): ('refinement','Salin teks pesan ini ke papan klip.','clipboard is left in English; papan klip is the localized Indonesian term.','moderate'),
    (332,'vi'): ('refinement','Sao chép văn bản của tin nhắn này vào bảng tạm.','clipboard is left in English; bảng tạm is the Vietnamese UI term. The candidate also tracks source text rather than broad content.','moderate'),
    (334,'ar'): ('correction','كبّر أداة العرض المرئي إلى وضع ملء الشاشة.','المتخيل means imagined person/object rather than a visualizer tool.','moderate'),
    (334,'ko'): ('correction','시각화 도구를 전체 화면으로 최대화하세요.','도우미 means assistant/helper; the caller is an audio visualizer control, so 도구 is the correct tool label.','moderate'),
    (335,'zh-Hans'): ('correction','当前启用的功能','主动功能 means proactive features rather than currently active/enabled features in the Security settings heading.','high'),
    (335,'zh-Hant'): ('correction','目前啟用的功能','主動功能 means proactive features rather than currently active/enabled features in the Security settings heading.','high'),
    (335,'pt-BR'): ('refinement','Funcionalidades ativas','Recursos can read as active resources; this heading lists enabled security features.','moderate'),
    (336,'de'): ('refinement','Keine Befunde zum Zustand des lokalen Netzwerks','The current compound Netzwerkgesundheitsbefunde is understandable but unnatural.','moderate'),
    (336,'hi'): ('refinement','स्थानीय नेटवर्क की स्थिति से जुड़ी कोई समस्या नहीं मिली','This is more natural than the literal network-health finding compound and matches the positive empty-state context.','moderate'),
    (336,'ko'): ('refinement','로컬 네트워크 상태에서 발견된 문제가 없습니다','The current noun chain 상태 발견 항목 is unnatural; this expresses the no-findings state clearly.','moderate'),
    (336,'pt-BR'): ('correction','Não foram encontrados problemas de integridade na rede local','descoberta de saúde is a literal calque. The pinned message describes a healthy local-network check with no findings.','moderate'),
    (336,'vi'): ('refinement','Không phát hiện vấn đề nào về tình trạng mạng cục bộ','The current phát hiện tình trạng construction is awkward; this preserves the no-findings meaning in the positive health-check message.','moderate'),
    (336,'zh-Hans'): ('correction','未发现本地网络健康问题','调查结果 means investigation results, not health findings; the caller presents a positive no-findings status.','high'),
    (336,'zh-Hant'): ('correction','未發現本地網路健康問題','調查結果 means investigation results, not health findings; the caller presents a positive no-findings status.','high'),
    (342,'de'): ('refinement','Das Teilen ist optional. Fügen Sie nur dann ein Freigabeverzeichnis hinzu, wenn andere Peers ausgewählte Ordner durchsuchen können sollen.','The current phrase ends with the awkward double modal dürfen sollen and shifts peers to users.','moderate'),
    (342,'es'): ('correction','Compartir es opcional. Añade una carpeta para compartir solo si quieres que otros pares puedan explorar las carpetas seleccionadas.','The current vean means see, while the source says peers can browse selected folders.','moderate'),
    (343,'ar'): ('correction','نقطة الالتقاء عبر DHT مفعّلة، ويمكن لهذه العقدة نشر نقطة النهاية العامة ضمن شبكة DHT العامة التابعة لـ BitTorrent. وهذا متوقع عند تفعيل نقطة الالتقاء العامة؛ ويهدف هذا الإشعار فقط إلى تنبيه المشغّلين إلى أن أقران slskdN الآخرين يستطيعون اكتشاف العقدة لمزامنة الشبكة المتداخلة.','موعد DHT and موعد عام mean an appointment/deadline. The candidate retains the rendezvous concept and exact protocol/product literals.','moderate'),
    (343,'de'): ('refinement','Das DHT-Rendezvous ist aktiviert, und dieser Knoten kann seinen öffentlichen Endpunkt in der öffentlichen BitTorrent-DHT veröffentlichen. Das ist erwartbar, wenn das öffentliche Rendezvous aktiviert ist; dieser Hinweis soll Betreiber lediglich darauf aufmerksam machen, dass andere slskdN-Peers den Knoten für die Mesh-Synchronisierung entdecken können.','The current translation is understandable, but erkennt means recognize rather than discover and the sentence structure/capitalization is rough.','moderate'),
    (343,'es'): ('correction','El mecanismo de encuentro DHT está habilitado y este nodo puede publicar su punto de conexión público en la DHT pública de BitTorrent. Esto es lo esperado cuando se habilita el encuentro público; este aviso solo informa a los operadores de que otros pares de slskdN pueden descubrir el nodo para sincronizar la malla.','punto final is a period/full stop, not a network endpoint; BitTorrent DHT also has incorrect word order.','moderate'),
    (343,'fr'): ('correction','Le mécanisme de rendez-vous DHT est activé et ce nœud peut publier son point de terminaison public dans la DHT publique de BitTorrent. C’est normal lorsque le rendez-vous public est activé ; cet avis sert uniquement à informer les opérateurs que d’autres pairs slskdN peuvent découvrir le nœud pour la synchronisation du maillage.','The current le public BitTorrent DHT is ungrammatical and reverses the DHT/BitTorrent relationship.','moderate'),
    (343,'hi'): ('refinement','DHT मिलन-बिंदु सक्षम है और यह नोड अपना सार्वजनिक एंडपॉइंट सार्वजनिक BitTorrent DHT में प्रकाशित कर सकता है। सार्वजनिक मिलन-बिंदु सक्षम होने पर यह अपेक्षित है; यह सूचना केवल ऑपरेटरों को बताने के लिए है कि अन्य slskdN पीयर मेश सिंक के लिए नोड को खोज सकते हैं।','मिलन स्थल is an overly literal rendezvous place; मिलन-बिंदु is a clearer technical rendezvous point. Technical names stay unchanged.','moderate'),
    (343,'id'): ('correction','Titik temu DHT aktif dan node ini dapat memublikasikan endpoint publiknya ke DHT publik BitTorrent. Hal ini memang diharapkan saat titik temu publik diaktifkan; pemberitahuan ini hanya agar operator mengetahui bahwa peer slskdN lain dapat menemukan node ini untuk sinkronisasi mesh.','Pertemuan DHT and pertemuan publik mean meetings; endpoint publik is also clearer than titik akhir publik.','moderate'),
    (343,'ko'): ('refinement','DHT 랑데부가 활성화되어 이 노드는 공개 엔드포인트를 공개 BitTorrent DHT에 게시할 수 있습니다. 공개 랑데부가 활성화된 경우 정상적인 동작입니다. 이 알림은 다른 slskdN 피어가 메시 동기화를 위해 노드를 발견할 수 있음을 운영자에게 알리기 위한 것입니다.','Rendezvous is an established technical term, but 랑데뷰 is a nonstandard spelling; 랑데부 is conventional. This also smooths the long notice.','moderate'),
    (343,'pt-BR'): ('correction','O rendezvous DHT está ativado, e este nó pode publicar seu endpoint público na DHT pública do BitTorrent. Isso é esperado quando o rendezvous público está ativado; este aviso serve apenas para informar aos operadores que outros pares slskdN podem descobrir o nó para sincronização da malha.','encontro DHT and terminal público mistranslate technical rendezvous and network endpoint; BitTorrent DHT is also in unnatural order.','moderate'),
    (343,'vi'): ('correction','Điểm hẹn DHT đã bật và nút này có thể công bố endpoint công khai của mình lên DHT công khai của BitTorrent. Đây là điều bình thường khi bật điểm hẹn công khai; thông báo này chỉ để các nhà vận hành biết rằng các nút ngang hàng slskdN khác có thể phát hiện nút này để đồng bộ hóa mạng lưới.','The current đồng nghiệp means colleagues, not network peers. The candidate preserves the technical endpoint and peer meaning.','moderate'),
    (343,'zh-Hans'): ('refinement','DHT 会合已启用，该节点可以将其公共端点发布到 BitTorrent 公共 DHT 中。启用公共会合时出现这种情况是正常的；此通知仅提醒操作人员，其他 slskdN 对等节点可以发现该节点以进行网格同步。','This clarifies DHT as the rendezvous mechanism and keeps named protocols and product identifiers opaque.','moderate'),
    (346,'ar'): ('correction','{shownFileCount} من أصل {totalFiles} مسارًا','The current phrase begins with مسارات then places the counts after it; this orders the displayed and total counts naturally.','moderate'),
    (346,'de'): ('correction','{shownFileCount} von {totalFiles} Titeln','oder means or, not of; Titel is natural for music tracks in the player count.','high'),
    (346,'es'): ('correction','{shownFileCount} de {totalFiles} pistas','The current noun-first wording is ungrammatical for a shown-of-total count.','high'),
    (346,'fr'): ('correction','{shownFileCount} sur {totalFiles} pistes','The current des pistes {totalFiles} orders the total incorrectly; sur expresses shown out of total tracks.','high'),
    (346,'id'): ('correction','{shownFileCount} dari {totalFiles} trek','The current trek {totalFiles} order is ungrammatical for a shown-of-total count.','high'),
    (346,'ko'): ('correction','{totalFiles}개 트랙 중 {shownFileCount}개','The current {totalFiles} 트랙의 {shownFileCount} is an awkward possessive; 중 marks shown among total tracks.','moderate'),
    (346,'pt-BR'): ('correction','{shownFileCount} de {totalFiles} faixas','The current faixas {totalFiles} order is ungrammatical for a shown-of-total count.','high'),
    (346,'vi'): ('correction','{shownFileCount} trong số {totalFiles} bản nhạc','The current của các bản nhạc {totalFiles} puts the total in an ungrammatical position.','high'),
    (346,'zh-Hans'): ('correction','已显示 {shownFileCount} 首，共 {totalFiles} 首','The current 轨道的 {shownFileCount} misorders the count and uses an imprecise music-track classifier.','moderate'),
    (346,'zh-Hant'): ('correction','已顯示 {shownFileCount} 首，共 {totalFiles} 首','The current 轨道的 uses an imprecise music-track word and misorders the shown/total counts.','moderate'),
    (348,'ar'): ('correction','افتح أداة العرض المرئي في نافذة المتصفح','المتخيل means imagined; the caller is a visualizer control that opens it in a browser window.','moderate'),
    (348,'ko'): ('correction','시각화 도구를 브라우저 창에서 최대화하세요.','도우미 means assistant/helper; the caller is a visualizer control, so 도구 is the correct noun.','moderate'),
    (348,'zh-Hans'): ('refinement','将可视化工具最大化至浏览器窗口中','The current wording can read as the browser window’s visualizer; this makes the destination of maximization explicit.','moderate'),
    (348,'zh-Hant'): ('refinement','將視覺化工具最大化至瀏覽器視窗中','The current wording can read as the browser window’s visualizer; this makes the destination of maximization explicit.','moderate'),
    (351,'hi'): ('correction','समन्वयन अंतराल','अंतराल सिंक करना reads like an instruction to sync an interval rather than a configuration interval.','high'),
}

rows=[json.loads(line) for line in (INPUT/'source-current-cells.jsonl').read_text().splitlines() if line]
assert len(rows)==300
assert {r['continuationRank'] for r in rows}==set(range(328,353))
assert {r['locale'] for r in rows}==set(LOCALES)
assert all(not r['containsCandidate'] for r in rows)
assert all(r['placeholderEvidence']['matches'] and r['markupEvidence']['matches'] for r in rows)
assert all(len(r['callerRefs'])>0 for r in rows)
placeholder_pattern=re.compile(r'\{[^{}]+\}')
protected=['HTTPS','SongID','Soulseek','DHT','BitTorrent','slskdN']
ledger=[]
for r in sorted(rows,key=lambda x:(x['continuationRank'],LOCALES.index(x['locale']))):
    key=(r['continuationRank'],r['locale'])
    item=proposals.get(key)
    if item:
        disposition,candidate,rationale,confidence=item
    else:
        disposition='accept-current'; candidate=None
        if r['continuationRank']==347:
            rationale='In the pinned QuarantineJury context, this wording correctly describes an already accepted recommendation to release an item from quarantine; it is not a software release-candidate phrase.'
        elif r['continuationRank'] in {330,339,343}:
            rationale='The current translation preserves the pinned technical context and exact named protocol/product terms; no material semantic defect was identified.'
        else:
            rationale='The current translation conveys the action or label in its pinned production caller; no material semantic or structural defect was identified.'
        confidence='moderate'
    source_tokens=set(placeholder_pattern.findall(r['source']))
    target=r['currentTarget'] if candidate is None else candidate
    target_tokens=set(placeholder_pattern.findall(target))
    assert source_tokens==target_tokens,(r['continuationRank'],r['locale'],source_tokens,target_tokens)
    terms=[term for term in protected if term in r['source']]
    missing=[term for term in terms if term not in target]
    assert not missing,(r['continuationRank'],r['locale'],missing)
    ledger.append({
      'schemaVersion':1,'reviewType':'independent-blind-semantic-review','repository':'snapetech-org/slskdN','pullRequest':409,
      'window':'W58-ranks-328-352','head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'continuationRank':r['continuationRank'],
      'historicalSourceOrdinal':None,'sourceId':r['sourceId'],'source':r['source'],'sourceSha256':r['sourceSha256'],
      'locale':r['locale'],'catalogPath':r['catalogPath'],'catalogGitBlob':r['catalogGitBlob'],'catalogFileSha256':r['catalogFileSha256'],
      'currentTarget':r['currentTarget'],'currentTargetSha256':r['currentTargetSha256'],
      'placeholderEvidence':r['placeholderEvidence'],'markupEvidence':r['markupEvidence'],
      'sourceNumericTokens':r['sourceNumericTokens'],'currentNumericTokens':r['currentNumericTokens'],
      'disposition':disposition,'proposedTarget':candidate,'rationale':rationale,'confidence':confidence,
      'callerRefs':r['callerRefs'],'callerContextSha256':r['callerContextSha256'],'protectedSourceTerms':terms,
      'protectedSourceTermsPreserved':True,'nativeSpeakerApproval':False
    })
counts=Counter(r['disposition'] for r in ledger)
assert len(ledger)==300 and counts['hold']==0
ledger_path=OUT/'blind-decisions.jsonl'
ledger_path.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in ledger))
summary={
 'repository':'snapetech-org/slskdN','pullRequest':409,'window':'W58-ranks-328-352','head':EXPECTED_HEAD,'tree':EXPECTED_TREE,
 'candidateFreeManifestFile':'PACKET-SHA256SUMS.txt','candidateFreeManifestSha256':hashlib.sha256((INPUT/'PACKET-SHA256SUMS.txt').read_bytes()).hexdigest(),
 'reviewedCells':300,'sourceCount':25,'localeCount':12,'dispositionCounts':dict(sorted(counts.items())),
 'holdsByRank':{},'callerRefsPresentCells':sum(bool(r['callerRefs']) for r in rows),
 'structuralChecks':{'cells':300,'placeholderMismatches':0,'markupMismatches':0,'protectedProtocolProductLiteralMismatches':0},
 'reviewLimit':'Independent machine-assisted semantic review, not native-speaker approval.'}
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
print(json.dumps({'ledgerRows':len(ledger),'counts':dict(counts),'ledgerSha256':hashlib.sha256(ledger_path.read_bytes()).hexdigest(),'candidateFreeManifestSha256':summary['candidateFreeManifestSha256']},indent=2))
