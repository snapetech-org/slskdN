from __future__ import annotations
import collections, hashlib, json, re, subprocess
from pathlib import Path

input_dir=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w60-ranks378-402-primary-20261103/input')
primary_dir=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w60-ranks378-402-primary-20261103/review')
blind_dir=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w60-independent-blind-20261103')
out=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w60-cross-audit-20261103')
head='3fbcea3185c02efca7c45d03a195acf488e70587'
tree='95604b428133b5e52247c1f3f00900c2c7d5192f'
locales=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

def sha(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def text_sha(s:str)->str: return sha(s.encode('utf-8'))
def canon(obj)->str: return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def verify(folder:Path, manifest:str): subprocess.check_call(['sha256sum','-c',manifest],cwd=folder,stdout=subprocess.DEVNULL)

def run_gh(path:str): return json.loads(subprocess.check_output(['gh','api',path],text=True))

# Confirm every source package before reconciling and re-attest live volatile PR state.
verify(input_dir,'PACKET-SHA256SUMS.txt')
verify(primary_dir,'PRIMARY-SHA256SUMS.txt')
verify(blind_dir,'SHA256SUMS.txt')
manifest=json.loads((input_dir/'manifest.json').read_text(encoding='utf-8'))
ps=json.loads((primary_dir/'summary.json').read_text(encoding='utf-8'))
bs=json.loads((blind_dir/'summary.json').read_text(encoding='utf-8'))
seal=json.loads((blind_dir/'blind-seal.json').read_text(encoding='utf-8'))
assert manifest['head']==ps['head']==bs['head']==seal['head']==head
assert manifest['tree']==ps['tree']==bs['tree']==seal['tree']==tree
input_manifest_sha=sha((input_dir/'PACKET-SHA256SUMS.txt').read_bytes())
assert ps['inputChecksumManifestSha256']==input_manifest_sha
assert bs['inputManifestSha256']==input_manifest_sha and seal['candidateFreeInputManifestSha256']==input_manifest_sha
assert ps['candidateFreeInputModified'] is False and bs['recommendationsSelectedForApplication']==0 and seal['primaryReviewNotConsulted'] is True
pr=run_gh('repos/snapetech-org/slskdN/pulls/409')
ref=run_gh('repos/snapetech-org/slskdN/git/ref/heads/codex/slskdn-oidc-tooltip-localization-20261030')
commit=run_gh(f'repos/snapetech-org/slskdN/git/commits/{head}')
assert pr['state']=='open' and pr['draft'] and pr['head']['sha']==head
assert pr['head']['ref']=='codex/slskdn-oidc-tooltip-localization-20261030'
assert ref['object']['sha']==head and commit['tree']['sha']==tree

# Cross-audit adjudications, keyed to stable continuation rank and direct locale.
final={}
def set_group(rank, disposition, target_by_locale, rationale):
    for loc,target in target_by_locale.items(): final[(rank,loc)]=(disposition,target,rationale)

# A declarative checkbox label accurately describes FTP's certificate-error behavior;
# the suggested imperative is stylistic, so preserve the current values.
set_group(379,'refinement',{
'ar':'أنشئ زوج مفاتيح جديدًا لتوقيع رسائل Pod. أبقِ المفتاح الخاص سرّيًا وخزّنه بأمان قبل مسح هذه النتيجة.',
'de':'Erzeugen Sie ein neues Schlüsselpaar zum Signieren von Pod-Nachrichten. Halten Sie den privaten Schlüssel geheim und bewahren Sie ihn sicher auf, bevor Sie dieses Ergebnis löschen.',
'es':'Genera un nuevo par de claves para firmar mensajes de Pod. Mantén en secreto la clave privada y guárdala de forma segura antes de borrar este resultado.',
'fr':'Générez une nouvelle paire de clés pour signer les messages Pod. Gardez la clé privée secrète et stockez-la en lieu sûr avant d’effacer ce résultat.',
'hi':'Pod संदेशों पर हस्ताक्षर के लिए नया कुंजी युग्म बनाएँ। इस परिणाम को मिटाने से पहले निजी कुंजी को गोपनीय रखें और सुरक्षित रूप से सहेजें.',
'id':'Buat pasangan kunci baru untuk menandatangani pesan Pod. Jaga kerahasiaan kunci privat dan simpan dengan aman sebelum menghapus hasil ini.',
'ja':'Pod メッセージ署名用の新しい鍵ペアを生成します。この結果を消す前に、秘密鍵を他人に知られないよう安全に保管してください。',
'ko':'Pod 메시지 서명용 새 키 쌍을 생성합니다. 이 결과를 지우기 전에 개인 키를 비밀로 유지하고 안전하게 보관하세요.',
'pt-BR':'Gere um novo par de chaves para assinar mensagens de Pod. Mantenha a chave privada em sigilo e guarde-a com segurança antes de limpar este resultado.',
'vi':'Tạo cặp khóa mới để ký tin nhắn Pod. Hãy giữ bí mật khóa riêng và lưu trữ an toàn trước khi xóa kết quả này.',
'zh-Hans':'生成用于 Pod 消息签名的新密钥对。清除此结果前，请对私钥保密并妥善保存。',
'zh-Hant':'產生新的金鑰組以簽署 Pod 訊息。清除此結果前，請對私鑰保密並妥善保存.'},'The tooltip has two safeguards: keep the private key secret and store it securely before clearing the generated result. Current targets mostly mention secure storage but omit the separate secrecy instruction; retain both requirements while preserving Pod terminology.')

set_group(381,'correction',{
'ar':'رحلة برية، مختارات من شركة تسجيلات، ترشيحات الأصدقاء',
'es':'Viaje por carretera, recopilatorio de un sello discográfico, recomendaciones de amigos',
'fr':"Road trip, compilation d'un label, recommandations d'amis",
'hi':'रोड ट्रिप, रिकॉर्ड लेबल का संकलन, दोस्तों की सिफ़ारिशें',
'id':'Perjalanan darat, kompilasi dari label rekaman, rekomendasi teman',
'ja':'ロードトリップ、レーベルのサンプラー、友人のおすすめ',
'pt-BR':'Viagem de carro, coletânea de uma gravadora, recomendações de amigos',
'vi':'Chuyến đi đường dài, tuyển tập từ hãng đĩa, gợi ý từ bạn bè',
'zh-Hans':'公路旅行、唱片公司精选合集、朋友推荐',
'zh-Hant':'公路旅行、唱片公司精選合輯、朋友推薦'},'This is a Playlist Intake example placeholder. The music context makes “label sampler” a sampler/compilation from a record label; “friend recs” means recommendations. Correct false-friend readings, the Indonesian-English fragments, and the lost road-trip specificity. The Simplified Chinese target also removes two unexpected zero-width characters.')
set_group(382,'correction',{'es':'ID de contenido:'},'The caller places this short label immediately before the returned identifier. “ID” is the exact technical label; “Identificación” describes identification rather than the identifier.')
set_group(384,'correction',{
'es':'Buscar salas existentes...',
'id':'Cari ruang obrolan yang ada...',
'ko':'기존 채팅방 검색...'},'The Rooms component is a chat-room chooser. Spanish “habitaciones” suggests house/guest rooms and Korean “회의실” means meeting rooms; Indonesian can name the chat-room context more clearly.')
final[(384,'id')]=('refinement','Cari ruang obrolan yang ada...','The Rooms component is a chat-room chooser; name the chat context explicitly for clarity.')
set_group(385,'correction',{'vi':'Audfprint'},'Audfprint is a library/algorithm name shown beside its score. Preserve the proper capitalization exactly.')
set_group(387,'refinement',{'de':'{itemType} löschen'},'This is a modal heading. The formal second-person “Löschen Sie …” is unnecessarily conversational; use a concise action heading and preserve the exact placeholder.')
set_group(388,'correction',{
'ar':'إغلاق التصوّر المرئي للتنزيل عبر swarm',
'id':'Tutup visualisasi unduhan swarm',
'ko':'스웜 다운로드 시각화 닫기',
'vi':'Đóng phần trực quan hóa swarm tải xuống',
'zh-Hans':'关闭 swarm 下载可视化',
'zh-Hant':'關閉 swarm 下載視覺化'},'The caller is a close label for the peer-swarm download visualization. Current translations in these locales read as a flock/herd or generic group, and Vietnamese says image; use a concise visualization label and retain the technical swarm term.')
set_group(388,'refinement',{'de':'Schwarm-Download-Visualisierung schließen'},'The source is an accessible close label. The short German action heading is clearer than the formal “Schließen Sie …” sentence.')

set_group(391,'correction',{
'ar':'يظل المزوّدون ظاهرين هنا لتسهيل التحقق من المزوّدين غير المفعّلين قبل تشغيل الأتمتة.',
'hi':'यहाँ प्रदाता दिखाई देते रहते हैं, ताकि स्वचालन शुरू करने से पहले यह जाँचा जा सके कि कौन-से प्रदाता अभी सक्रिय नहीं हैं।',
'id':'Penyedia tetap terlihat di sini agar dapat diperiksa penyedia mana yang belum diaktifkan sebelum otomatisasi dijalankan.',
'pt-BR':'Os provedores continuam visíveis aqui para que seja possível verificar quais ainda não estão habilitados antes de ativar a automação.',
'vi':'Các nhà cung cấp vẫn hiển thị ở đây để có thể kiểm tra những nhà cung cấp nào chưa được bật trước khi bật tính năng tự động hóa.',
'zh-Hans':'提供商在此处保持可见，方便在启用自动化前检查哪些提供商尚未启用。',
'zh-Hant':'提供者在此處保持可見，方便在啟用自動化前檢查哪些提供者尚未啟用。'},'SourceProviders makes clear this concerns provider enablement before acquisition automation. The current wording in these locales describes empowerment, capability, or support gaps instead of which providers are not enabled.')
set_group(391,'refinement',{
'de':'Anbieter bleiben hier sichtbar, damit sich vor dem Einschalten der Automatisierung prüfen lässt, welche Anbieter noch nicht aktiviert sind.',
'es':'Los proveedores siguen visibles aquí para poder revisar cuáles aún no están habilitados antes de activar la automatización.',
'fr':"Les fournisseurs restent visibles ici afin de repérer lesquels ne sont pas encore activés avant d'activer l'automatisation.",
'ja':'自動化をオンにする前に、どのプロバイダーがまだ有効になっていないか確認できるよう、プロバイダーはここに表示されます。',
'ko':'자동화를 켜기 전에 아직 활성화되지 않은 공급자를 확인할 수 있도록 여기에 계속 표시됩니다.'},'Replace literal “enablement gaps” with a direct, readable explanation that the visible provider list lets administrators inspect which integrations are not yet enabled.')

set_group(393,'correction',{
'ar':'إن تسجيل إدخالات اكتشاف Pod أو إلغاء تسجيلها أو تحديثها أو إعادة تحميلها يغيّر البيانات الوصفية العامة لـ Pod الظاهرة في DHT.',
'de':'Das Registrieren, Abmelden, Aktualisieren oder Neuladen von Pod-Erkennungseinträgen ändert öffentliche, im DHT sichtbare Pod-Metadaten.',
'es':'Registrar, cancelar el registro, actualizar o recargar las entradas de descubrimiento de Pod cambia los metadatos públicos del Pod visibles en DHT.',
'fr':'L’enregistrement, la désinscription, la mise à jour ou l’actualisation des entrées de découverte de Pod modifie les métadonnées publiques de Pod visibles dans le DHT.',
'pt-BR':'Registrar, cancelar o registro, atualizar ou recarregar entradas de descoberta de Pod altera os metadados públicos de Pod visíveis no DHT.',
'vi':'Việc đăng ký, hủy đăng ký, cập nhật hoặc làm mới các mục khám phá Pod sẽ thay đổi siêu dữ liệu Pod công khai hiển thị trên DHT.'},'This warning lists four distinct actions and identifies a Pod as the registered object. Current Arabic/Spanish/German/Portuguese repeat the same update verb for “updating” and “refreshing”; Arabic/French/Vietnamese also turn Pod into an unrelated pouch/space/group. Preserve DHT as a protocol acronym.')

set_group(396,'refinement',{
'ar':'حدّث فهرس اكتشاف Pod واجعل الإدخالات القديمة منتهية الصلاحية. استخدمه عندما تبدو نتائج الاكتشاف قديمة.',
'id':'Segarkan indeks penemuan Pod dan tandai entri usang sebagai kedaluwarsa. Gunakan saat hasil penemuan tampak sudah kedaluwarsa.',
'vi':'Làm mới chỉ mục khám phá Pod và đánh dấu các mục cũ là đã hết hạn. Dùng khi kết quả khám phá có vẻ đã lỗi thời.'},'The live caller reports “entriesExpired.” Explicitly say old entries become expired; avoid an awkward verb or a translation that sounds like deleting entries.')
set_group(396,'correction',{
'de':'Pod-Erkennungsindex aktualisieren und veraltete Einträge ablaufen lassen. Verwenden Sie dies, wenn die Entdeckungsergebnisse nicht mehr aktuell wirken.',
'es':'Actualiza el índice de descubrimiento de Pod y marca las entradas obsoletas como caducadas. Úsalo cuando los resultados parezcan desactualizados.',
'fr':'Actualisez l’index de découverte de Pod et faites expirer les entrées obsolètes. À utiliser lorsque les résultats de découverte semblent dépassés.',
'hi':'Pod खोज इंडेक्स रीफ़्रेश करें और पुरानी प्रविष्टियों को समाप्त घोषित करें। खोज के नतीजे पुराने लगें तो इसका उपयोग करें.',
'pt-BR':'Atualize o índice de descoberta de Pod e marque as entradas desatualizadas como expiradas. Use quando os resultados de descoberta parecerem desatualizados.',
'zh-Hans':'刷新 Pod 发现索引，并将过时条目标记为过期。若发现结果显得过时，可使用此功能。',
'zh-Hant':'重新整理 Pod 探索索引，並將過時項目標記為過期。若探索結果看起來過時，可使用此功能。'},'The implementation refreshes the index and reports entries expired; these current targets imply deletion/removal or make already-expired entries invalid. Mark stale entries as expired and keep the Pod discovery context.')
set_group(397,'correction',{
'ar':'ReplayGain لكل مقطوعة بعد الاستيراد',
'de':'ReplayGain pro Titel nach dem Import',
'es':'ReplayGain por pista después de la importación',
'fr':'ReplayGain par piste après l’importation',
'hi':'आयात के बाद हर ट्रैक के लिए ReplayGain',
'id':'ReplayGain per trek setelah impor',
'ja':'インポート後にトラック単位で ReplayGain を適用',
'ko':'가져온 후 트랙별 ReplayGain',
'pt-BR':'ReplayGain por faixa após a importação',
'vi':'ReplayGain theo từng bản nhạc sau khi nhập',
'zh-Hans':'导入后按曲目应用 ReplayGain',
'zh-Hant':'匯入後依曲目套用 ReplayGain'},'Adjacent replayGainPolicies entries contrast Album and Track modes. Here “Track” is a per-track processing mode, not the verb “track/follow.” Targets specify per-track ReplayGain and retain the exact ReplayGain token.')
set_group(398,'correction',{'vi':'Các Pod được lưu trên máy chủ, nên danh sách và tin nhắn vẫn còn sau khi tải lại trình duyệt hoặc khởi động lại daemon.'},'The caller is the Pods page and nearby terminology names Pod as a system entity. Vietnamese “nhóm” turns Pod into a generic group; preserve Pod.')
set_group(398,'refinement',{'zh-Hant':'Pod 由伺服器儲存，因此清單和訊息在重新載入瀏覽器或重新啟動守護程序後仍會保留。'},'Use the standard Traditional Chinese storage form 儲存 and state that the list and messages remain after either restart.')
set_group(401,'correction',{'id':'Tambahkan teman melalui undangan'},'This modal title adds a friend using an invitation. Indonesian “Undang” is the verb “invite”; the noun is “undangan.”')
set_group(401,'refinement',{'ja':'招待から友達を追加'},'This modal title reads more naturally with the object particle を.')
set_group(402,'correction',{
'ar':'تمكين حدود سرعة الرفع المجدولة',
'zh-Hans':'启用按计划设置的上传速度限制',
'zh-Hant':'啟用依排程設定的上傳速度限制'},'The pinned checkbox is for scheduled upload-speed limits. Arabic التحميل is ambiguous with download, and the Chinese current phrases can read as planned limits rather than limits governed by a schedule.')
set_group(402,'refinement',{
'hi':'अपलोड के लिए निर्धारित गति सीमाएँ सक्षम करें',
'ja':'アップロード速度のスケジュール制限を有効にする'},'Make the checkbox label more idiomatic and explicit about scheduled speed limits for uploads.')

input_rows=[json.loads(l) for l in (input_dir/'source-current-cells.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
primary_rows=[json.loads(l) for l in (primary_dir/'primary-ledger.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
blind_rows=[json.loads(l) for l in (blind_dir/'blind-decisions.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
P={(r['continuationRank'],r['locale']):r for r in primary_rows}
B={(r['continuationRank'],r['locale']):r for r in blind_rows}
I={(r['continuationRank'],r['locale']):r for r in input_rows}
assert len(I)==len(P)==len(B)==300
assert set(I)==set(P)==set(B)
assert len(final)==84

placeholder_re=re.compile(r'\{[^{}]+\}')
tag_re=re.compile(r'</?[A-Za-z][^>]*>')
ledger=[]; disagreement_rows=[]; disposition_counts=collections.Counter(); reconciliation_counts=collections.Counter()
for key in sorted(I):
    i=I[key]; p=P[key]; b=B[key]
    rank,loc=key
    assert p['head']==b['head']==manifest['head']==head and p['tree']==b['tree']==manifest['tree']==tree
    assert p['sourceId']==b['sourceId']==i['sourceId'] and p['source']==b['source']==i['source']
    assert p['currentTarget']==b['currentTarget']==i['currentTarget']
    assert p['currentTargetSha256']==i['currentTargetSha256'] and text_sha(i['currentTarget'])==i['currentTargetSha256']
    assert p['candidateFreeInputCellSha256']==b['inputRowSha256']
    assert b['inputRowSha256']==sha(canon(i).encode('utf-8'))
    assert p['catalogFileSha256']==i['catalogFileSha256'] and p['catalogGitBlob']==i['catalogGitBlob']
    assert p['callerContextSha256']==i['callerContextSha256']
    assert i['placeholderEvidence']['matches'] and i['markupEvidence']['matches']
    p_target=p['proposedTarget'] or p['currentTarget']
    b_target=b['recommendedTarget']
    p_disp=p['verdict']; b_disp=b['recommendedDisposition']
    if p_disp==b_disp and p_target==b_target: reconcile='agreement'
    elif p_disp==b_disp and p_target!=b_target: reconcile='same-disposition-different-target'
    elif p_target==b_target: reconcile='different-disposition-same-target'
    else: reconcile='different-disposition-and-target'
    reconciliation_counts[reconcile]+=1
    if key in final:
        disp,target,rationale=final[key]
    else:
        disp,target,rationale='accept-current',i['currentTarget'],'Both independent reviews accept the current value; the pinned caller supports the same meaning, and no material semantic or structural error was found.'
    assert disp in {'accept-current','correction','refinement'}
    assert target==i['currentTarget'] if disp=='accept-current' else target!=i['currentTarget']
    # Preserve exact placeholders, markup, and source numeric tokens.
    source_tokens=placeholder_re.findall(i['source'])
    target_tokens=placeholder_re.findall(target)
    assert collections.Counter(source_tokens)==collections.Counter(target_tokens),(rank,loc,'placeholder mismatch',source_tokens,target_tokens)
    assert collections.Counter(tag_re.findall(i['source']))==collections.Counter(tag_re.findall(target)),(rank,loc,'markup mismatch')
    target_nums=re.findall(r'(?<!\w)\d+(?:[.,]\d+)?(?!\w)',target)
    assert target_nums==i['sourceNumericTokens'],(rank,loc,'numeric-token mismatch',i['sourceNumericTokens'],target_nums)
    # Product/library/protocol names whose exact spelling is required in this window.
    protected={379:['Pod'],383:['ntfy'],385:['Audfprint'],393:['DHT'],397:['ReplayGain']}.get(rank,[])
    if rank==378 and 'FTP' in i['currentTarget']: protected=['FTP']
    for literal in protected:
        assert literal in target,(rank,loc,'protected literal missing',literal,target)
    changed=target!=i['currentTarget']
    if changed: disposition_counts[disp]+=1
    else: disposition_counts['accept-current']+=1
    if reconcile!='agreement':
        disagreement_rows.append({'continuationRank':rank,'sourceId':i['sourceId'],'source':i['source'],'locale':loc,'currentTarget':i['currentTarget'],'primaryDisposition':p_disp,'primaryTarget':p['proposedTarget'],'primaryRationale':p['rationale'],'blindDisposition':b_disp,'blindTarget':b_target,'blindRationale':b['rationale'],'crossAuditDisposition':disp,'crossAuditTarget':target if changed else None,'crossAuditRationale':rationale,'reconciliationClass':reconcile})
    ledger.append({
      'repository':'snapetech-org/slskdN','pullRequest':409,'head':head,'tree':tree,
      'continuationRank':rank,'historicalSourceOrdinal':i['historicalSourceOrdinal'],'sourceId':i['sourceId'],'source':i['source'],'sourceSha256':i['sourceSha256'],
      'locale':loc,'catalogPath':i['catalogPath'],'catalogFileSha256':i['catalogFileSha256'],'catalogGitBlob':i['catalogGitBlob'],
      'currentTarget':i['currentTarget'],'currentTargetSha256':i['currentTargetSha256'],
      'callerRefs':i['callerRefs'],'callerContextSha256':i['callerContextSha256'],
      'sourcePlaceholderTokens':source_tokens,'finalTargetPlaceholderTokens':target_tokens,'placeholderCheck':True,
      'sourceMarkupTags':tag_re.findall(i['source']),'finalTargetMarkupTags':tag_re.findall(target),'markupCheck':True,
      'sourceNumericTokens':i['sourceNumericTokens'],'finalTargetNumericTokens':target_nums,'numericTokenCheck':True,
      'primaryDisposition':p_disp,'primaryTarget':p['proposedTarget'],'primaryTargetSha256':p['proposedTargetSha256'],'primaryRationale':p['rationale'],
      'blindDisposition':b_disp,'blindTarget':b_target,'blindTargetSha256':b['recommendedTargetSha256'],'blindRationale':b['rationale'],
      'reconciliationClass':reconcile,'disposition':disp,'selectedTarget':target if changed else None,
      'selectedTargetSha256':text_sha(target) if changed else None,'selectedForApplication':changed,'changeFromCurrent':changed,
      'rationale':rationale,'inputCellSha256':sha(canon(i).encode('utf-8')),'primaryRowSha256':sha(canon(p).encode('utf-8')),'blindRowSha256':sha(canon(b).encode('utf-8'))
    })

assert len(disagreement_rows)==83
assert reconciliation_counts=={'agreement':217,'same-disposition-different-target':35,'different-disposition-and-target':45,'different-disposition-same-target':3},reconciliation_counts
assert len(ledger)==300 and len({(r['continuationRank'],r['locale']) for r in ledger})==300
assert disposition_counts=={'accept-current':216,'correction':57,'refinement':27},disposition_counts
assert sum(r['selectedForApplication'] for r in ledger)==84
assert all(r['selectedForApplication']==(r['selectedTarget'] is not None) for r in ledger)
assert all(r['placeholderCheck'] and r['markupCheck'] and r['numericTokenCheck'] for r in ledger)
assert all(i['callerRefs'] for i in input_rows)

out.mkdir(parents=True,exist_ok=True)
att_path=out/'live-pr-attestation.json'
assert att_path.exists()
att=json.loads(att_path.read_text(encoding='utf-8'))
assert att['head']==head and att['tree']==tree and att['branchRefHead']==head and att['checkRuns']==0 and att['deployments']==0
ledger_path=out/'cross-audit-ledger.jsonl'
ledger_path.write_text(''.join(canon(r)+'\n' for r in ledger),encoding='utf-8')
dis_summary={'schemaVersion':1,'window':'W60 ranks 378-402','disagreementCount':len(disagreement_rows),'reconciliationClasses':dict(sorted(reconciliation_counts.items())),'disagreements':disagreement_rows,'holds':[],'callerlessSourceIds':0,'heldCellCount':0}
(out/'disagreement-and-hold-summary.json').write_text(json.dumps(dis_summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
summary={'schemaVersion':1,'repository':'snapetech-org/slskdN','pullRequest':409,'window':'W60 ranks 378-402','head':head,'tree':tree,'sourceCount':25,'localeCount':12,'cellCount':300,'dispositions':dict(sorted(disposition_counts.items())),'primaryDispositions':ps['verdictCounts'],'blindDispositions':bs['dispositions'],'selectedChanges':84,'readbackRequired':True,'allSourcesCallerBacked':True,'callerlessHolds':0,'reconciliationClasses':dict(sorted(reconciliation_counts.items())),'disagreementCount':len(disagreement_rows),'placeholderChecksPassed':300,'markupChecksPassed':300,'numericTokenChecksPassed':300,'qualifiedNativeSpeakerApproval':False,'exactHeadBrowserReview':False,'releaseApproved':False,'candidateFreeInputManifestSha256':input_manifest_sha,'primaryLedgerSha256':sha((primary_dir/'primary-ledger.jsonl').read_bytes()),'blindLedgerSha256':sha((blind_dir/'blind-decisions.jsonl').read_bytes()),'livePrAttestationSha256':sha(att_path.read_bytes())}
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(out/'attestation.json').write_text(json.dumps({'livePr':att,'candidateFreeInputManifestSha256':input_manifest_sha,'primarySummarySha256':sha((primary_dir/'summary.json').read_bytes()),'blindSealSha256':sha((blind_dir/'blind-seal.json').read_bytes()),'crossAuditLedgerSha256':sha(ledger_path.read_bytes()),'sourceCellCount':len(input_rows),'allCrossAuditCellsPinnedToExactHead':True,'noRepositoryFilesEdited':True,'noTestsBuildsScansCiOrWorkflowsRun':True,'nativeSpeakerApproval':False,'exactHeadBrowserReview':False,'releaseApproved':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report=f'''# slskdN PR #409 W60 independent cross-audit\n\n- Exact base: `{head}` / tree `{tree}`; PR remains open and draft on `main`.\n- Coverage: 25 source IDs × 12 direct locales = 300 cells. All 25 have pinned production callers.\n- Cross-audit outcomes: 216 accept-current, 57 corrections, 27 refinements; 84 selected target changes and no callerless holds.\n- Primary/blind reconciliation: 217 full agreements, 35 same-disposition target disagreements, 45 disposition-and-target disagreements, and 3 disposition disagreements with the same target. Every disagreement is recorded row by row.\n- Placeholder, markup, numeric-token, catalog-file, caller-context, and target-hash pins were rechecked. The exact `{{itemType}}` placeholder, `FTP`, `ntfy`, `Audfprint`, `Pod`, `DHT`, and `ReplayGain` literals are retained where required.\n\n## Main cross-audit findings\n\n- Playlist Intake rank 381 uses music context: “label sampler” is a record-label sampler/compilation and “friend recs” are recommendations. Several existing cells mean recordings, lectures, label/tag samples, or contain untranslated fragments; the selected corrections repair those meanings and restore “road trip” where it was reduced to generic travel.\n- The neighboring Album/Track ReplayGain choices prove “Track” is the per-track policy, not a tracking verb. The selected targets state per-track ReplayGain in all locales.\n- Pod discovery warnings at ranks 393 and 396 concern a technical Pod entity and DHT-visible metadata; refresh/expiry is distinct from deletion. Selected targets preserve DHT and describe expiring stale entries.\n- Provider enablement wording now states which providers are not enabled before automation, rather than capability/support gaps.\n- Exact placeholders and named library/protocol/product literals are preserved.\n\nThe complete [row ledger](cross-audit-ledger.jsonl) records the source/current values, caller pins, both independent reviews, reconciliation class, final disposition, selected target/hash, and rationale for all 300 cells. The [disagreement and hold summary](disagreement-and-hold-summary.json) contains every non-agreement and confirms no callerless holds.\n\nThis machine-assisted cross-audit does not establish qualified native-speaker approval or exact-head browser acceptance, and it does not approve a release. No repository files, builds, tests, scans, CI, or workflows were changed or run.\n'''
(out/'report.md').write_text(report,encoding='utf-8')
# A verifier that rechecks the cross-audit's immutable accounting and content hashes.
verify_py='''import collections, hashlib, json, re\nfrom pathlib import Path\nroot=Path(__file__).resolve().parent\nrows=[json.loads(l) for l in (root/"cross-audit-ledger.jsonl").read_text().splitlines() if l.strip()]\nassert len(rows)==300 and len({(r["continuationRank"],r["locale"]) for r in rows})==300\nassert all(r["head"]=="3fbcea3185c02efca7c45d03a195acf488e70587" and r["tree"]=="95604b428133b5e52247c1f3f00900c2c7d5192f" for r in rows)\nassert all(hashlib.sha256(r["selectedTarget"].encode()).hexdigest()==r["selectedTargetSha256"] for r in rows if r["selectedForApplication"])\nassert sum(r["selectedForApplication"] for r in rows)==84\nassert collections.Counter(r["disposition"] for r in rows)=={"accept-current":216,"correction":57,"refinement":27}\nassert all(r["placeholderCheck"] and r["markupCheck"] and r["numericTokenCheck"] for r in rows)\nassert all(r["selectedForApplication"]==(r["selectedTarget"] is not None) for r in rows)\nsummary=json.loads((root/"summary.json").read_text())\nassert summary["cellCount"]==300 and summary["selectedChanges"]==84 and summary["disagreementCount"]==83\nprint("cross-audit evidence verified: 300 cells, 84 selected changes, 83 reconciled disagreements, 0 holds")\n'''
(out/'verify_cross_audit_evidence.py').write_text(verify_py,encoding='utf-8')
# Root manifest covers each file except itself.
files=sorted(p for p in out.rglob('*') if p.is_file() and p!=out/'SHA256SUMS.txt')
(out/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(out).as_posix()}\n' for p in files),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,sort_keys=True))
