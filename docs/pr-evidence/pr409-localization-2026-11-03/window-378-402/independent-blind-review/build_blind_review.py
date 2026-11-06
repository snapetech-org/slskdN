from __future__ import annotations
import collections, hashlib, json
from pathlib import Path

input_dir=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w60-ranks378-402-primary-20261103/input')
out=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w60-independent-blind-20261103')
head='3fbcea3185c02efca7c45d03a195acf488e70587'
tree='95604b428133b5e52247c1f3f00900c2c7d5192f'
locales=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

def sha(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def text_sha(s:str)->str: return sha(s.encode('utf-8'))
def line(obj)->str: return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'))

targets={}
def set_targets(rank, disposition, rationale, values):
    for locale,target in values.items(): targets[(rank,locale)]=(disposition,target,rationale)

set_targets(378,'refinement','Pinned callers show this is the aria-label and checkbox label for a user setting. Recast declarative “FTP ignores” translations as concise action labels.',{
'ar':'تجاهل أخطاء شهادة FTP','de':'FTP-Zertifikatsfehler ignorieren','es':'Ignorar errores de certificado FTP','fr':'Ignorer les erreurs de certificat FTP','id':'Abaikan kesalahan sertifikat FTP','ja':'FTP の証明書エラーを無視','ko':'FTP 인증서 오류 무시','pt-BR':'Ignorar erros de certificado FTP','vi':'Bỏ qua lỗi chứng chỉ FTP'})
set_targets(381,'correction','This is a playlist-name placeholder. “Label sampler” refers to a music-record-label sampler, and “friend recs” means recommendations, not recordings or lectures.',{
'ar':'رحلة برية، مختارات من إصدارات شركة إنتاج موسيقي، وتوصيات الأصدقاء','es':'Viaje por carretera, recopilatorio de un sello discográfico, recomendaciones de amigos','fr':"Road trip, compilation d'un label, recommandations d'amis",'hi':'रोड ट्रिप, रिकॉर्ड लेबल का संकलन, दोस्तों की सिफ़ारिशें','id':'Perjalanan darat, kompilasi dari label rekaman, rekomendasi teman','ja':'ロードトリップ、レーベルのサンプラー、友人のおすすめ','pt-BR':'Viagem de carro, coletânea de uma gravadora, recomendações de amigos','vi':'Chuyến đi đường dài, tuyển tập của hãng đĩa, gợi ý từ bạn bè','zh-Hans':'公路旅行、唱片公司的精选合辑、朋友推荐','zh-Hant':'公路旅行、唱片公司的精選合輯、朋友推薦'})
set_targets(382,'refinement','Pinned caller displays this as a short field label immediately before the content identifier; “ID” is the precise technical term.',{'es':'ID de contenido:'})
set_targets(384,'correction','Pinned Rooms chooser is a chat-room selector. Replace Spanish “habitaciones” (house/guest rooms) and Korean “회의실” (meeting rooms) with chat-room wording.',{'es':'Buscar salas existentes...','ko':'기존 채팅방 검색...'})
set_targets(385,'correction','Audfprint is the proper library/algorithm name shown beside its score; preserve exact capitalization.',{'vi':'Audfprint'})
set_targets(387,'refinement','Pinned caller is a modal heading. German “Löschen Sie …” addresses the user formally; use a concise action heading and keep the exact placeholder.',{'de':'{itemType} löschen'})
set_targets(388,'refinement','Pinned caller is the accessible close label for a download-swarm visualization. Use the technical swarm term instead of wording that reads as an animal herd/image.',{'vi':'Đóng phần trực quan hóa swarm tải xuống'})
set_targets(391,'correction','This provider-status explanation is about checking which providers are enabled before acquisition automation starts. Translate that explicit state, not capability, empowerment, or support gaps.',{
'ar':'يظل المزوّدون ظاهرين هنا لتسهيل التحقق من المزوّدين غير المفعّلين قبل تشغيل الأتمتة.',
'de':'Anbieter bleiben hier sichtbar, damit sich vor dem Einschalten der Automatisierung prüfen lässt, welche Anbieter noch nicht aktiviert sind.',
'es':'Los proveedores siguen visibles aquí para poder revisar cuáles aún no están habilitados antes de activar la automatización.',
'fr':"Les fournisseurs restent visibles ici afin de repérer lesquels ne sont pas encore activés avant d'activer l'automatisation.",
'hi':'यहाँ प्रदाता दिखाई देते रहते हैं, ताकि स्वचालन शुरू करने से पहले यह जाँचा जा सके कि कौन-से प्रदाता अभी सक्रिय नहीं हैं।',
'id':'Penyedia tetap terlihat di sini agar dapat diperiksa penyedia mana yang belum diaktifkan sebelum otomatisasi dijalankan.',
'ja':'自動化をオンにする前に、どのプロバイダーがまだ有効になっていないか確認できるよう、プロバイダーはここに表示されます。',
'ko':'자동화를 켜기 전에 아직 활성화되지 않은 공급자를 확인할 수 있도록 공급자는 여기에 계속 표시됩니다.',
'pt-BR':'Os provedores continuam visíveis aqui para que seja possível verificar quais ainda não estão habilitados antes de ativar a automação.',
'vi':'Các nhà cung cấp vẫn hiển thị ở đây để có thể kiểm tra những nhà cung cấp nào chưa được bật trước khi bật tính năng tự động hóa.',
'zh-Hans':'提供商在此处保持可见，方便在启用自动化前检查哪些提供商尚未启用。',
'zh-Hant':'提供者在此處保持可見，方便在啟用自動化前檢查哪些提供者尚未啟用。'})
# Enablement wording is wrong in these locales; the others need clarity but preserve meaning.
for locale in ['ar','hi','id','pt-BR','vi','zh-Hans','zh-Hant']:
    targets[(391,locale)]=('correction',targets[(391,locale)][1],targets[(391,locale)][2])
for locale in ['de','es','fr','ja','ko']:
    targets[(391,locale)]=('refinement',targets[(391,locale)][1],targets[(391,locale)][2])
set_targets(393,'correction','The warning describes four distinct actions and a Pod as the technical entity. Correct duplicated update/refresh verbs and preserve Pod where the current translation says pouch, space, or group.',{
'ar':'إن تسجيل إدخالات اكتشاف Pod أو إلغاء تسجيلها أو تحديثها أو إعادة تحميلها يغيّر البيانات الوصفية العامة لـ Pod الظاهرة في DHT.',
'de':'Das Registrieren, Abmelden, Aktualisieren oder Neuladen von Pod-Erkennungseinträgen ändert öffentliche, im DHT sichtbare Pod-Metadaten.',
'es':'Registrar, cancelar el registro, actualizar o recargar las entradas de descubrimiento de Pod cambia los metadatos públicos del Pod visibles en DHT.',
'fr':'L’enregistrement, la désinscription, la mise à jour ou l’actualisation des entrées de découverte de Pod modifie les métadonnées publiques de Pod visibles dans le DHT.',
'pt-BR':'Registrar, cancelar o registro, atualizar ou recarregar entradas de descoberta de Pod altera os metadados públicos de Pod visíveis no DHT.',
'vi':'Việc đăng ký, hủy đăng ký, cập nhật hoặc làm mới các mục khám phá Pod sẽ thay đổi siêu dữ liệu Pod công khai hiển thị trên DHT.'})
set_targets(396,'correction','The caller reports refreshed and expired-entry counts, so the tooltip must say stale records expire rather than being deleted. Preserve Pod terminology.',{
'ar':'حدّث فهرس اكتشاف Pod واجعل الإدخالات القديمة منتهية الصلاحية. استخدم ذلك عندما تبدو نتائج الاكتشاف قديمة.',
'de':'Pod-Erkennungsindex aktualisieren und veraltete Einträge ablaufen lassen. Verwenden, wenn die Suchergebnisse veraltet wirken.',
'es':'Actualiza el índice de descubrimiento de Pod y marca las entradas obsoletas como caducadas. Úsalo cuando los resultados parezcan desactualizados.',
'fr':'Actualisez l’index de découverte de Pod et faites expirer les entrées obsolètes. À utiliser lorsque les résultats de découverte semblent dépassés.',
'hi':'Pod खोज इंडेक्स रीफ़्रेश करें और पुरानी प्रविष्टियों को समाप्त घोषित करें। खोज के नतीजे पुराने लगें तो इसका उपयोग करें.',
'id':'Segarkan indeks penemuan Pod dan tandai entri lama sebagai kedaluwarsa. Gunakan saat hasil penemuan tampak sudah usang.',
'pt-BR':'Atualize o índice de descoberta de Pod e marque as entradas antigas como expiradas. Use quando os resultados parecerem desatualizados.',
'zh-Hans':'刷新 Pod 发现索引，并将过时条目标记为过期。若发现结果显得过时，可使用此功能。',
'zh-Hant':'重新整理 Pod 探索索引，並將過時項目標記為過期。若探索結果看起來過時，可使用此功能。'})
set_targets(397,'correction','Adjacent replayGainPolicies entries distinguish “Album ReplayGain after import” from “Track ReplayGain after import”; Track is the per-track mode, not the verb “track/follow.” Preserve ReplayGain.',{
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
'zh-Hant':'匯入後依曲目套用 ReplayGain'})
set_targets(398,'correction','The caller is the Pods page and nearby strings preserve Pod as the named system entity. Vietnamese “nhóm” changes it to a generic group.',{'vi':'Pod được máy chủ lưu trữ nên danh sách và tin nhắn vẫn còn sau khi trình duyệt tải lại và daemon khởi động lại.'})
set_targets(401,'correction','Pinned caller is a modal header for adding a friend from an invitation. Indonesian “Undang” is the verb “invite,” not the noun “invitation.”',{'id':'Tambahkan teman dari undangan'})
set_targets(402,'correction','Pinned caller is specifically the upload-speed policy checkbox. Arabic “التحميل” can mean downloading; use the upload term رفع.',{'ar':'تمكين حدود سرعة الرفع المجدولة'})
set_targets(402,'refinement','Make the scheduled upload-speed meaning explicit and idiomatic for the checkbox label.',{'hi':'अपलोड के लिए निर्धारित गति सीमाएँ सक्षम करें','ja':'アップロード速度のスケジュール制限を有効にする','zh-Hans':'启用计划的上传速度限制','zh-Hant':'啟用排程的上傳速度限制'})

assert out.exists() and [x.name for x in out.iterdir()]==['build_blind_review.py'], f'refusing unexpected existing output: {list(out.iterdir()) if out.exists() else out}'
rows=[json.loads(line) for line in (input_dir/'source-current-cells.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
manifest=json.loads((input_dir/'manifest.json').read_text(encoding='utf-8'))
assert len(rows)==300 and manifest['head']==head and manifest['tree']==tree
assert len({(r['continuationRank'],r['locale']) for r in rows})==300
contexts={json.loads(line)['sourceId']:json.loads(line) for line in (input_dir/'caller-contexts.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()}
assert len(contexts)==25 and all(c['productionCallerCount']>0 for c in contexts.values())
assert set(locales)=={r['locale'] for r in rows}
assert all((rank,locale) in {(r['continuationRank'],r['locale']) for r in rows} for rank,locale in targets)

ledger=[]
for r in rows:
    key=(r['continuationRank'],r['locale'])
    if key in targets:
        disposition,target,rationale=targets[key]
    else:
        disposition='accept-current'; target=r['currentTarget']
        rationale='Current target accurately conveys the source in its pinned production caller context; protected technical terms, placeholders, and markup are preserved.'
    assert disposition in {'accept-current','correction','refinement'}
    assert r['placeholderEvidence']['matches'] and r['markupEvidence']['matches']
    ledger.append({
      'head':head,'tree':tree,'continuationRank':r['continuationRank'],'historicalSourceOrdinal':r['historicalSourceOrdinal'],
      'sourceId':r['sourceId'],'source':r['source'],'sourceSha256':r['sourceSha256'],'locale':r['locale'],
      'catalogPath':r['catalogPath'],'catalogFileSha256':r['catalogFileSha256'],'catalogGitBlob':r['catalogGitBlob'],
      'currentTarget':r['currentTarget'],'currentTargetSha256':r['currentTargetSha256'],
      'recommendedDisposition':disposition,'recommendedTarget':target,'recommendedTargetSha256':text_sha(target),
      'changeFromCurrent':target!=r['currentTarget'],'selectedForApplication':False,
      'callerRefs':r['callerRefs'],'callerContextSha256':r['callerContextSha256'],
      'placeholderEvidence':r['placeholderEvidence'],'markupEvidence':r['markupEvidence'],
      'rationale':rationale,'inputRowSha256':sha(line(r).encode('utf-8'))
    })
assert len(ledger)==300
counts=collections.Counter(r['recommendedDisposition'] for r in ledger)
assert sum(r['changeFromCurrent'] for r in ledger)==sum(counts[d] for d in ('correction','refinement'))
assert len(contexts)==manifest['sourceCount']

out.mkdir(parents=True,exist_ok=True)
ledger_path=out/'blind-decisions.jsonl'
ledger_path.write_text(''.join(line(r)+'\n' for r in ledger),encoding='utf-8')
summary={'schemaVersion':1,'reviewer':'independent blind machine review','repository':'snapetech-org/slskdN','pullRequest':409,'window':'W60 ranks 378-402','head':head,'tree':tree,'inputManifestSha256':sha((input_dir/'PACKET-SHA256SUMS.txt').read_bytes()),'sourceCount':25,'localeCount':12,'cellCount':300,'callerlessSourceIds':0,'dispositions':dict(sorted(counts.items())),'recommendedChangedCells':sum(r['changeFromCurrent'] for r in ledger),'recommendationsSelectedForApplication':0,'qualifiedNativeSpeakerApproval':False,'exactHeadBrowserReview':False,'releaseApproved':False}
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(out/'provenance.json').write_text(json.dumps({'reviewMethod':'independent target-only review from checksummed candidate-free input; no primary review consulted','inputDirectory':str(input_dir),'inputManifestSha256':summary['inputManifestSha256'],'inputHead':head,'inputTree':tree,'sealedBeforePrimaryReviewCompletion':True,'allSourceIdsHavePinnedCallers':True,'sourceLocaleRows':len(rows)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(out/'README.md').write_text(f'''# slskdN PR #409 W60 independent blind review\n\nThis independent review covers 25 source IDs × 12 locales (300 cells) at exact parent head `{head}` / tree `{tree}`. It used only the candidate-free input at `{input_dir}`; no primary review or proposed primary targets were consulted. All 25 sources have pinned production callers, and source-placeholder/markup evidence passed for every cell.\n\nThe ledger records current and recommended values, hashes, caller pins, disposition, and rationale. Recommendations are not selected for application; an independent cross-audit must reconcile them with the primary review.\n\nDisposition counts: {dict(sorted(counts.items()))}. Recommended changed cells: {summary['recommendedChangedCells']}. Qualified native-speaker approval and exact-head browser review are not established. This packet does not approve a release.\n''',encoding='utf-8')
seal={'repository':'snapetech-org/slskdN','pullRequest':409,'window':'W60 ranks 378-402','head':head,'tree':tree,'candidateFreeInputManifestSha256':summary['inputManifestSha256'],'blindLedgerSha256':sha(ledger_path.read_bytes()),'cellCount':300,'dispositionCounts':dict(sorted(counts.items())),'recommendedChangedCells':summary['recommendedChangedCells'],'primaryReviewNotConsulted':True}
(out/'blind-seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
files=sorted(p for p in out.rglob('*') if p.is_file() and p!=out/'SHA256SUMS.txt')
(out/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(out).as_posix()}\n' for p in files),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,sort_keys=True))
