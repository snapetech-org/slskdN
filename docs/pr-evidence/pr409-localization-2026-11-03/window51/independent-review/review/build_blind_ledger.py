import hashlib, json, pathlib, re
from collections import Counter

input_dir=pathlib.Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window51-blind-input-20261103/input')
out_dir=pathlib.Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window51-blind-review-20261103')
manifest_sha='f1c23a687dbe529e456f321dcb64b27caf05f52e69c15af926ada1f0b7651674'
att=json.loads((input_dir/'head-tree-attestation.json').read_text())
assert att['head']=='45664e79a6d9bd41519b674d33464e5f7cb9ce2c'
assert att['tree']=='dc5f6ab2aab3668f674dd583451d3464a3a1c081'

# (continuation rank, locale): (disposition, candidate, rationale, confidence)
changes={
(176,'ko'):('correction','캐시 성능 및 가져오기 통계','“검색 통계” means search statistics; the caller is descriptor retrieval, so use the retrieval/fetch term.','high'),
(177,'de'):('refinement','Führen Sie {title} jetzt mit der tatsächlichen Backend-Aktion aus. „Wishlist Retry“ führt bis zu drei aktivierte Suchvorgänge aus; „Library Health“ startet den konfigurierten Nur-Lese-Scan.','The current compound “Wunschliste-Wiederholung” is awkward for the named action; keep the action names distinct and use a natural read-only scan term.','moderate'),
(177,'es'):('refinement','Ejecute {title} ahora mediante su acción real en el backend. Wishlist Retry ejecuta hasta tres búsquedas habilitadas; Library Health inicia el análisis de solo lectura configurado.','“Acción real de backend” is a calque; make the actual backend action and configured read-only scan read naturally.','moderate'),
(177,'ja'):('refinement','実際のバックエンド処理で{title}を今すぐ実行します。Wishlist Retryでは最大3件の有効な検索を実行し、Library Healthでは設定済みの読み取り専用スキャンを開始します。','Remove inconsistent spaces and express the configured read-only scan naturally while preserving the placeholder and named actions.','moderate'),
(177,'ko'):('correction','지금 {title}의 실제 백엔드 작업을 실행하세요. Wishlist Retry는 활성화된 검색을 최대 3회 실행하고, Library Health는 구성된 읽기 전용 스캔을 시작합니다.','The current target calls the Library Health scan a search; the source says scan. Rework the opening to avoid an unreliable Korean particle after the dynamic title.','high'),
(177,'pt-BR'):('correction','Execute {title} agora pela ação real no backend. Wishlist Retry executa até três pesquisas habilitadas; Library Health inicia a verificação configurada somente para leitura.','“A repetição da lista de desejos” is unnatural for the named action; make the actual backend action and read-only verification clear.','high'),
(177,'vi'):('correction','Thực hiện {title} ngay bằng thao tác thực tế ở backend. Wishlist Retry chạy tối đa ba lượt tìm kiếm đã bật; Library Health bắt đầu quá trình quét chỉ đọc theo cấu hình.','“Hành động phụ trợ” means an auxiliary action, not a backend action; use a natural scan term for the configured read-only scan.','high'),
(177,'zh-Hans'):('refinement','现在通过实际的后端操作执行 {title}。愿望清单重试最多运行三个已启用的搜索；Library Health 会启动配置好的只读扫描。','Replace the awkward calque “库运行状况” with the named feature and keep the operation’s read-only scan meaning clear.','moderate'),
(177,'zh-Hant'):('refinement','現在透過實際的後端操作執行 {title}。願望清單重試最多執行三個已啟用的搜尋；Library Health 會啟動已設定的唯讀掃描。','Replace the awkward calque “庫運行狀況” with the named feature and keep the operation’s read-only scan meaning clear.','moderate'),
(178,'ar'):('refinement','حالة الفتحة غير متاحة','Use the singular slot-status label rather than the current plural “openings.”','moderate'),
(178,'es'):('refinement','Estado de la ranura no disponible','The source labels one slot’s status; use the singular form.','moderate'),
(178,'pt-BR'):('correction','Status do slot indisponível','“Vagas” means vacancies; retain the technical slot meaning in this user-card status.','high'),
(178,'vi'):('correction','Trạng thái slot không khả dụng','“Khe” means a gap/hole and is not the user slot here; retain the technical slot term.','high'),
(181,'ja'):('correction','シグナルは無視されました','The current wording is an unfinished verb; make the status label a complete passive statement.','high'),
(182,'ar'):('refinement','، عنوان IP:','Add the Arabic list comma represented by the source’s leading comma.','moderate'),
(183,'zh-Hant'):('correction','略過的資料列：','Use the Traditional Chinese term for data rows; “列” alone can be read as columns.','high'),
(184,'ar'):('correction','، لذلك يعطّل slskdN عمدًا محرك BitTorrent DHT العام. في وضع الخصوصية هذا،','Keep this localized clause at the same fragment boundary as the caller; the current added “expected count is” would duplicate the following count/predicate.','high'),
(184,'de'):('correction',', daher deaktiviert slskdN absichtlich die öffentliche BitTorrent-DHT-Engine. In diesem Datenschutzmodus','Keep this as the caller’s introductory fragment; remove the added “werden” and comma, which do not fit German word order/punctuation before the following subject.','high'),
(184,'es'):('correction',', por lo que slskdN desactiva intencionadamente el motor público de BitTorrent DHT. En este modo de privacidad,','Keep this as the caller’s introductory fragment; remove the added “se esperan,” which duplicates the later expected predicate.','high'),
(184,'fr'):('correction',', donc slskdN désactive volontairement le moteur DHT public de BitTorrent. Dans ce mode de confidentialité,','Keep the sentence fragment at the caller’s boundary; the current expectation phrase is repeated by the following clause.','high'),
(184,'hi'):('refinement',', इसलिए slskdN सार्वजनिक BitTorrent DHT इंजन को जानबूझकर अक्षम करता है। इस गोपनीयता मोड में,','Keep the source’s “in this privacy mode” fragment and preserve the exact product/protocol names.','moderate'),
(184,'id'):('correction',', jadi slskdN sengaja menonaktifkan mesin DHT publik BitTorrent. Dalam mode privasi ini,','Keep this as the source’s introductory fragment; remove “jumlah yang diharapkan adalah,” which repeats the following expected predicate.','high'),
(184,'ja'):('correction','、そのためslskdNはパブリックBitTorrent DHTエンジンを意図的に無効にします。このプライバシーモードでは、','The current fragment adds “DHT node count is” before the caller’s following “0 DHT nodes and,” causing duplication; retain only the source fragment.','high'),
(184,'ko'):('refinement',', 따라서 slskdN은 공개 BitTorrent DHT 엔진을 의도적으로 비활성화합니다. 이 개인정보 보호 모드에서는,','Keep this clause at the source boundary and preserve the exact product/protocol names.','moderate'),
(184,'pt-BR'):('correction',', portanto, slskdN desativa intencionalmente o mecanismo público de BitTorrent DHT. Neste modo de privacidade,','Keep the source’s introductory fragment; remove “espera-se encontrar,” which duplicates the following expected predicate.','high'),
(184,'vi'):('correction',', vì vậy slskdN cố tình vô hiệu hóa bộ máy BitTorrent DHT công khai. Trong chế độ riêng tư này,','Keep the clause at the source boundary; remove the added expectation phrase, which duplicates the following expected predicate.','high'),
(184,'zh-Hans'):('correction','，因此 slskdN 会有意禁用公共 BitTorrent DHT 引擎。在此隐私模式下，','Keep this as the source’s introductory fragment; remove “预计有,” which would duplicate the expected predicate after the inline counts.','high'),
(184,'zh-Hant'):('correction','，因此 slskdN 會刻意停用公開 BitTorrent DHT 引擎。在此隱私模式下，','Keep this as the source’s introductory fragment; remove “預期有,” which would duplicate the expected predicate after the inline counts.','high'),
(185,'es'):('refinement','formato aplicado a la carga útil canónica de unión/salida y a la clave pública proporcionada.','Use a natural technical relation for a signature format applied to the canonical membership payload and supplied public key.','moderate'),
(185,'hi'):('correction','ऐसा प्रारूप जो कैनोनिकल जॉइन/लीव पेलोड और दी गई सार्वजनिक कुंजी पर आधारित हो।','The current Hindi imperative means “format [it]”; the source describes a signature format based on a payload and public key.','high'),
(185,'ja'):('correction','正規の参加/離脱ペイロードと提供された公開鍵に基づく形式です。','The current wording says to use the format of the payload/key; make clear that the format is based on them.','high'),
(185,'ko'):('correction','정규 가입/탈퇴 페이로드와 제공된 공개 키를 기반으로 한 형식입니다.','The current target means “specify a format for”; the source describes a signature format based on the payload and key.','high'),
(185,'pt-BR'):('correction','formato aplicado ao payload canônico de entrada/saída e à chave pública fornecida.','“Licença” means license, not leave; use the membership-entry/exit sense and preserve the public-key meaning.','high'),
(185,'vi'):('correction','định dạng dựa trên payload tham gia/rời nhóm chính tắc và khóa công khai được cung cấp.','“Khóa chung” means shared/common key, not public key; correct it and make the canonical payload relation clear.','high'),
(187,'hi'):('refinement','उपयोगकर्ता नाम','Use the common Hindi phrase for a username instead of the rare compound.','moderate'),
(187,'id'):('correction','nama pengguna','The current “nama belakang” means surname, not username.','high'),
(188,'fr'):('correction','Lancez SQLite vacuum pour compacter la base de données locale des messages et récupérer de l’espace. Cela peut prendre du temps.','The current translation omits that this is the local message database; preserve the operation and warning.','high'),
(192,'ar'):('refinement','أولوية المزوّدين ضمن الملف الشخصي','Clarify that the priority is among providers within a profile, per the read-only routing-policy context.','moderate'),
(192,'de'):('refinement','Priorität der Anbieter im Profil','Clarify that the priority is among providers within a profile; the current wording reads as the profile provider’s priority.','moderate'),
(192,'es'):('refinement','Prioridad de los proveedores del perfil','Clarify that the priority concerns the providers assigned to the profile.','moderate'),
(192,'fr'):('refinement','Priorité des fournisseurs du profil','Clarify that the priority concerns providers assigned to the acquisition profile.','moderate'),
(192,'hi'):('refinement','प्रोफ़ाइल के प्रदाताओं की प्राथमिकता','Clarify that the priority is among providers within the profile.','moderate'),
(192,'id'):('refinement','Prioritas penyedia dalam profil','Clarify that priority is among providers within the profile, not priority of a profile provider.','moderate'),
(192,'ja'):('refinement','プロファイル内のプロバイダーの優先順位','Clarify that the priority order is among providers within the profile.','moderate'),
(192,'ko'):('refinement','프로필 내 공급자 우선순위','Clarify that the priority is among providers within the profile.','moderate'),
(192,'pt-BR'):('refinement','Prioridade dos provedores no perfil','Clarify that the priority is among providers within the acquisition profile.','moderate'),
(192,'vi'):('refinement','Thứ tự ưu tiên của các nhà cung cấp trong hồ sơ','Clarify that this is the priority order among providers in the profile.','moderate'),
(192,'zh-Hans'):('refinement','配置文件中的服务提供商优先级','Clarify that the priority is among service providers assigned within the profile.','moderate'),
(192,'zh-Hant'):('refinement','設定檔中的服務提供者優先順序','Clarify that the priority is among service providers assigned within the profile.','moderate'),
(193,'ar'):('refinement','مستوى الثقة:','The caller displays a confidence percentage; label the metric as a confidence level.','moderate'),
(193,'de'):('correction','Konfidenz:','The caller displays a confidence score, not interpersonal trust; use the technical metric term.','high'),
(193,'fr'):('refinement','Niveau de confiance :','Make explicit that this label introduces a confidence score/percentage.','moderate'),
(193,'hi'):('correction','विश्वास स्तर:','The current “आत्मविश्वास” means self-confidence; use a confidence-level label for the score.','high'),
(193,'id'):('correction','Tingkat keyakinan:','The current “kepercayaan diri” means self-confidence; use the confidence level of the match.','high'),
(193,'ja'):('correction','信頼度：','The current “自信” means personal confidence; use the confidence-score term.','high'),
(193,'ko'):('correction','신뢰도:','The current value is just trust; the caller displays a confidence score.','high'),
(193,'vi'):('correction','Mức độ tin cậy:','The current “sự tự tin” means self-confidence; label the reliability/confidence score.','high'),
(193,'zh-Hans'):('correction','置信度：','Use the established term for a model/match confidence score rather than generic confidence.','high'),
(193,'zh-Hant'):('refinement','信賴度：','Use the score/reliability sense of confidence in this percentage label.','moderate'),
(194,'ar'):('correction','خطافات الأحداث، والأهداف البعيدة، وخطافات الأوامر، ونمط إعادة المحاولة.','The current “شكل إعادة المحاولة” is a literal, unclear shape; use retry pattern.','high'),
(194,'de'):('correction','Event-Hooks, Remote-Ziele, Befehls-Hooks und Wiederholungsmuster.','“Wiederholungsform” is an unnatural literal rendering; use a retry pattern.','high'),
(194,'es'):('correction','Ganchos de eventos, destinos remotos, ganchos de comandos y patrón de reintentos.','Replace the unclear literal “forma de reintento” with a retry pattern.','high'),
(194,'fr'):('correction','Hooks d’événement, cibles distantes, hooks de commande et modèle de nouvelle tentative.','Replace the literal “forme de nouvelle tentative” with a retry pattern.','high'),
(194,'hi'):('correction','इवेंट हुक, रिमोट टार्गेट, कमांड हुक और पुनः प्रयास का पैटर्न।','The current “आकार” means geometric shape; use a retry pattern.','high'),
(194,'id'):('correction','Hook peristiwa, target jarak jauh, hook perintah, dan pola percobaan ulang.','Replace the literal “bentuk percobaan ulang” with a retry pattern.','high'),
(194,'ja'):('correction','イベントフック、リモートターゲット、コマンドフック、および再試行パターン。','The current “再試行形状” means retry shape literally; use the natural technical term for a retry pattern.','high'),
(194,'ko'):('correction','이벤트 훅, 원격 대상, 명령 훅 및 재시도 패턴.','Replace the unclear literal “재시도 형태” with a retry pattern.','high'),
(194,'pt-BR'):('correction','Ganchos de eventos, destinos remotos, ganchos de comando e padrão de novas tentativas.','Replace the unclear “formato de nova tentativa” with a retry pattern.','high'),
(194,'vi'):('correction','Hook sự kiện, đích từ xa, hook lệnh và mẫu thử lại.','The current “hình dạng thử lại” means a geometric shape; use a retry pattern.','high'),
(194,'zh-Hans'):('correction','事件钩子、远程目标、命令钩子和重试模式。','Replace literal “重试形状” with the natural term for retry pattern.','high'),
(194,'zh-Hant'):('correction','事件掛鉤、遠端目標、命令掛鉤和重試模式。','Replace literal “重試形狀” with the natural term for retry pattern.','high'),
(195,'ja'):('refinement','ウィッシュリストの項目「{searchText}」を削除しますか？','Use Japanese question punctuation for this confirmation prompt.','moderate'),
(195,'ko'):('correction','위시리스트에서 “{searchText}” 항목을 삭제하시겠습니까?','Attach the object particle to the fixed noun “항목,” not to a dynamic title whose final sound varies.','high'),
(195,'vi'):('refinement','Bạn có muốn xóa mục “{searchText}” khỏi danh sách yêu thích không?','Use a natural Vietnamese confirmation question rather than the current noun stack.','moderate'),
(197,'ar'):('refinement','توقفت الرسوم المتحركة مؤقتًا لأن خيار تقليل الحركة مفعّل.','Name the accessibility option that reduces motion instead of saying “low motion.”','moderate'),
(197,'de'):('refinement','Die Animation ist pausiert, weil „Bewegung reduzieren“ aktiviert ist.','Use the clear accessibility-setting wording for reduced motion.','moderate'),
(197,'es'):('refinement','La animación está pausada porque la opción de reducir el movimiento está activada.','Make clear that reduced motion is an enabled accessibility option.','moderate'),
(197,'hi'):('correction','एनीमेशन रोक दिया गया है, क्योंकि मोशन कम करने की सुविधा चालू है।','The current “कम गति” means low speed; the preference reduces motion.','high'),
(197,'id'):('refinement','Animasi dijeda karena opsi untuk mengurangi gerakan sedang aktif.','Use a natural enabled-option phrasing for the reduced-motion accessibility setting.','moderate'),
(197,'ja'):('correction','動きを減らす設定が有効なため、アニメーションを一時停止しています。','Use the natural setting name for reduced motion instead of the literal “motion shrinkage.”','high'),
(197,'ko'):('correction','동작 줄이기 설정이 켜져 있어 애니메이션이 일시 중지되었습니다.','Use natural Korean for an enabled reduced-motion setting instead of “motion reduction.”','high'),
(197,'pt-BR'):('refinement','A animação está pausada porque a opção de reduzir o movimento está ativada.','Make clear that reduced motion is an enabled accessibility option.','moderate'),
(197,'vi'):('correction','Hoạt ảnh đang tạm dừng vì chế độ giảm chuyển động đã bật.','The current “chuyển động giảm được bật” is a calque; use a natural reduced-motion mode phrase.','high'),
(197,'zh-Hans'):('refinement','由于已启用“减少动态效果”，动画已暂停。','Use the natural accessibility-setting term for reduced motion.','moderate'),
(197,'zh-Hant'):('refinement','由於已啟用「減少動態效果」，動畫已暫停。','Use the natural accessibility-setting term for reduced motion.','moderate'),
(199,'ar'):('refinement','حدد المجلد {folderName} لعرض محتوياته في متصفح الملفات المشتركة.','Clarify that this browser displays shared files/folders, not an internet sharing browser.','moderate'),
(199,'es'):('refinement','Seleccione la carpeta {folderName} para ver su contenido en el explorador de archivos compartidos.','Clarify that this is the browser for shared files, not a browser shared with someone.','moderate'),
(199,'fr'):('refinement','Sélectionnez le dossier {folderName} pour afficher son contenu dans le navigateur des partages.','Clarify that this is the browser for file shares.','moderate'),
(199,'hi'):('refinement','साझा फ़ोल्डरों के ब्राउज़र में इसकी सामग्री देखने के लिए फ़ोल्डर {folderName} चुनें।','Clarify that the browser is for shared folders.','moderate'),
(199,'id'):('refinement','Pilih folder {folderName} untuk melihat isinya di browser berkas bersama.','Clarify that the browser is for shared files.','moderate'),
(199,'pt-BR'):('refinement','Selecione a pasta {folderName} para ver o conteúdo no navegador de arquivos compartilhados.','Clarify that the browser is for shared files.','moderate'),
(199,'vi'):('refinement','Chọn thư mục {folderName} để xem nội dung trong trình duyệt các thư mục chia sẻ.','Clarify that this browser is for shared folders.','moderate'),
(199,'zh-Hans'):('refinement','选择文件夹 {folderName}，以在共享文件浏览器中查看其内容。','Clarify that the browser is for shared files.','moderate'),
(199,'zh-Hant'):('refinement','選擇資料夾 {folderName}，以在共用檔案瀏覽器中檢視其內容。','Clarify that the browser is for shared files.','moderate'),
}

cells=list(map(json.loads,(input_dir/'source-current-cells.jsonl').read_text().splitlines()))
catalogs={x['locale']:x for x in map(json.loads,(input_dir/'catalog-structure.jsonl').read_text().splitlines())}
contexts={x['continuationRank']:x for x in map(json.loads,(input_dir/'caller-contexts.jsonl').read_text().splitlines())}
boundary=list(map(json.loads,(input_dir/'selection-boundary.jsonl').read_text().splitlines()))
assert len(cells)==300 and len(contexts)==25 and len(boundary)==25 and len(catalogs)==12
assert len({x['orderedKeySha256'] for x in catalogs.values()})==1
assert {x['entryCount'] for x in catalogs.values()}=={6176}
assert len({(x['continuationRank'],x['locale']) for x in cells})==300
assert set(changes).issubset({(x['continuationRank'],x['locale']) for x in cells})
source_by_rank={x['continuationRank']:x for x in boundary}

def sha(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def placeholders(s): return sorted(re.findall(r'\{[^{}]+\}',s))
protected_tokens=['slskdN','BitTorrent','DHT','SQLite','Meek']
review=[]
for row in cells:
    rank=row['continuationRank']; locale=row['locale']; key=(rank,locale)
    src=source_by_rank[rank]
    assert src['sourceId']==row['sourceId'] and src['source']==row['source']
    assert src['sourceSha256']==row['sourceSha256']
    assert sha(row['source'])==row['sourceSha256']
    assert sha(row['currentTarget'])==row['currentTargetSha256']
    cat=catalogs[locale]
    assert (row['catalogPath'],row['catalogFileSha256'],row['catalogGitBlob'])==(cat['catalogPath'],cat['sha256'],cat['gitBlob']),(rank,locale,'catalog pin')
    known_calls=contexts[rank]['callers']
    for ref in row['callerRefs']:
        assert any((c['path'],c['line'],c['lineSha256'])==(ref['path'],ref['line'],ref['lineSha256']) for c in known_calls),(rank,locale,'caller ref')
    if key in changes:
        disposition,target,rationale,confidence=changes[key]
    else:
        disposition='accept-current'; target=row['currentTarget']; confidence='moderate'
        if rank==180:
            rationale='The caller shows this as a successful upload/download stream count; “files moved successfully” naturally conveys successful transfer files in this context.'
        elif rank==184:
            rationale='The existing fragment preserves the caller’s clause connection and the exact slskdN, BitTorrent, and DHT names without duplicating later text.'
        elif rank==198:
            rationale='Meek is the named transport; the exact product/transport name is preserved.'
        else:
            rationale='Current translation conveys the source meaning and is suitable in the supplied caller context.'
    assert placeholders(target)==placeholders(row['source']),(rank,locale,'placeholder mismatch',target,row['source'])
    for token in protected_tokens:
        if token in row['source']:
            assert token in target,(rank,locale,'protected literal mismatch',token,target)
    review.append({
      'repository':'snapetech-org/slskdN','pullRequest':409,
      'exactInputHead':att['head'],'exactInputTree':att['tree'],'packetManifestSha256':manifest_sha,
      'continuationRank':rank,'sourceId':row['sourceId'],'locale':locale,
      'source':row['source'],'sourceSha256':row['sourceSha256'],
      'currentTarget':row['currentTarget'],'currentTargetSha256':row['currentTargetSha256'],
      'catalogPath':row['catalogPath'],'catalogFileSha256':row['catalogFileSha256'],'catalogGitBlob':row['catalogGitBlob'],
      'callerContextSha256':row['callerContextSha256'],'callerRefs':row['callerRefs'],
      'disposition':disposition,'proposedTarget':target if disposition!='accept-current' else None,
      'proposedTargetSha256':sha(target),
      'proposedCatalogTranslationHash':sha(json.dumps(target,ensure_ascii=False,separators=(',',':'))),
      'confidence':confidence,'rationale':rationale,
      'placeholderParity':True,'protectedLiteralParity':True,
    })
assert len(review)==300
assert {(x['continuationRank'],x['locale']) for x in review}=={(x['continuationRank'],x['locale']) for x in cells}
counts=Counter(x['disposition'] for x in review)
summary={
 'repository':'snapetech-org/slskdN','pullRequest':409,'window':'W51','continuationRanks':[176,200],
 'sourceIds':25,'locales':12,'cellsReviewed':300,
 'inputPacketDirectory':str(input_dir.parent),'inputPacketManifestSha256':manifest_sha,
 'exactInputHead':att['head'],'exactInputTree':att['tree'],
 'dispositions':dict(counts),'changedProposals':sum(counts[x] for x in ('correction','refinement','hold-context')),
 'sourceHashMismatches':0,'currentTargetHashMismatches':0,'catalogFilePinMismatches':0,
 'placeholderMismatches':0,'protectedLiteralMismatches':0,
 'repositoryOrApiInspected':False,'primaryProposalsRead':False,'nativeSpeakerApproval':False,
 'historicalSourceOrdinalsInferred':False,
}
(out_dir/'independent-decisions.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in review))
(out_dir/'review-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
(out_dir/'review-manifest.json').write_text(json.dumps({
 'reviewer':'strict-blind independent reviewer','inputDirectory':str(input_dir.parent),
 'inputManifestSha256':manifest_sha,'head':att['head'],'tree':att['tree'],'window':'W51',
 'cellsReviewed':300,'allSourceAndCurrentTargetHashesVerified':True,
 'catalogFilePinsReadFromInputOnly':True,'catalogPinsVerified':True,'callerRefsVerified':True,'allPlaceholderSetsPreserved':True,
 'allProtectedSourceLiteralsPreserved':True,'repositoryOrApiInspected':False,
 'primaryProposalsRead':False,'nativeSpeakerApproval':False,
},ensure_ascii=False,indent=2)+'\n')
(out_dir/'README.md').write_text('''# slskdN PR #409 strict-blind review: W51\n\nThis independent ledger reviews the 25 pinned source IDs at continuation ranks 176–200 across all 12 locales (300 cells) using only the checksum-verified clean input packet. It is bound to input packet manifest digest `f1c23a687dbe529e456f321dcb64b27caf05f52e69c15af926ada1f0b7651674`, head `45664e79a6d9bd41519b674d33464e5f7cb9ce2c`, and tree `dc5f6ab2aab3668f674dd583451d3464a3a1c081`.\n\n`independent-decisions.jsonl` records one decision per source/locale cell, exact input and catalog pins, source and caller-context hashes, proposed target hashes, placeholder/protected-literal checks, confidence, and rationale. No primary proposals, repository checkout, or PR/API details were inspected during this review. No historical source ordinal was inferred.\n\nThis is machine-assisted review and does not establish native-speaker approval.\n''')
print(json.dumps({'counts':dict(counts),'changed':summary['changedProposals'],'manualReviewCells':len(review),'placeholdersVerified':True,'protectedLiteralsVerified':True},ensure_ascii=False,indent=2))
