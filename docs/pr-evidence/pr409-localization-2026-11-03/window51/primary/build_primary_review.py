#!/usr/bin/env python3
"""Record a hash-bound primary review of slskdN PR #409 W51 cells."""
from pathlib import Path
import collections, hashlib, json, re

ROOT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window51-primary-20261103/primary')
HEAD = '45664e79a6d9bd41519b674d33464e5f7cb9ce2c'
TREE = 'dc5f6ab2aab3668f674dd583451d3464a3a1c081'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

# Primary candidate values are limited to caller-supported, concrete defects/refinements.
CANDIDATES = {
 (177,'ar'): ('قم بتنفيذ {title} الآن من خلال الإجراء الخلفي الحقيقي. تقوم \"إعادة محاولة قائمة الرغبات\" بتشغيل ما يصل إلى ثلاث عمليات بحث ممكّنة؛ تبدأ صحة المكتبة عملية الفحص للقراءة فقط التي تم تكوينها.','refinement','This is Automation Center help text. The action and feature names are app-owned UI labels; use the localized Library Health label instead of leaving the English name in Arabic copy.'),
 (177,'de'): ('Führen Sie {title} jetzt über die eigentliche Backend-Aktion aus. Die Aktion \"Wunschliste erneut versuchen\" führt bis zu drei aktivierte Suchen aus; Bibliotheksgesundheit startet den konfigurierten schreibgeschützten Scan.','refinement','This is Automation Center help text. Use the established localized feature label Bibliotheksgesundheit instead of leaving Library Health in English.'),
 (177,'es'): ('Ejecute {title} ahora mediante su acción real de backend. La acción «Reintentar la lista de deseos» ejecuta hasta tres búsquedas habilitadas; «Salud de la biblioteca» inicia el análisis configurado de solo lectura.','refinement','This is Automation Center help text. Wishlist Retry and Library Health are app-owned UI labels already translated elsewhere in this locale; use those labels in the explanatory sentence.'),
 (177,'fr'): ('Exécutez {title} maintenant via sa véritable action backend. La nouvelle tentative de liste de souhaits exécute jusqu’à trois recherches activées ; Santé des bibliothèques démarre l’analyse configurée en lecture seule.','refinement','This is Automation Center help text. Use the established localized feature label Santé des bibliothèques instead of leaving Library Health in English.'),
 (177,'hi'): ('अब इसकी वास्तविक बैकएंड कार्रवाई के माध्यम से {title} निष्पादित करें। “इच्छा सूची पुनः प्रयास करें” की कार्रवाई तीन सक्षम खोजें चलाती है; “पुस्तकालय स्वास्थ्य” कॉन्फ़िगर किया गया केवल-पठन स्कैन शुरू करता है।','refinement','This is Automation Center help text. Use the localized Wishlist Retry and Library Health feature labels rather than English transliteration for the feature names.'),
 (177,'id'): ('Jalankan {title} sekarang melalui aksi backend sebenarnya. Aksi “Daftar Keinginan Coba Lagi” menjalankan hingga tiga pencarian yang diaktifkan; “Kesehatan Perpustakaan” memulai pemindaian hanya-baca yang dikonfigurasi.','refinement','This is Automation Center help text. Wishlist Retry and Library Health are app-owned UI labels already translated elsewhere in this locale; use those labels in the explanatory sentence.'),
 (177,'ja'): ('実際のバックエンド アクションを通じて {title} を実行します。ウィッシュリストの再試行では、最大 3 つの有効な検索が実行されます。図書館の健全性は、構成された読み取り専用スキャンを開始します。','refinement','This is Automation Center help text. Use the established localized Library Health feature label 図書館の健全性 instead of leaving the English name in Japanese copy.'),
 (177,'ko'): ('이제 실제 백엔드 작업을 통해 {title}를 실행하세요. 위시리스트 재시도는 최대 3개의 활성화된 검색을 실행합니다. 도서관 건강은 구성된 읽기 전용 검색을 시작합니다.','refinement','This is Automation Center help text. Use the established localized Library Health feature label 도서관 건강 instead of leaving the English name in Korean copy.'),
 (177,'pt-BR'): ('Execute {title} agora através de sua ação de backend real. A repetição da lista de desejos executa até três pesquisas habilitadas; a Saúde da Biblioteca inicia a verificação somente leitura configurada.','refinement','This is Automation Center help text. Use the established localized Library Health feature label Saúde da Biblioteca instead of leaving the English name in Portuguese copy.'),
 (177,'vi'): ('Thực thi {title} ngay bây giờ thông qua hành động phụ trợ thực sự của nó. Danh sách mong muốn Thử lại chạy tối đa ba tìm kiếm được kích hoạt; Thư viện sức khỏe bắt đầu quá trình quét chỉ đọc đã định cấu hình.','refinement','This is Automation Center help text. Use the established localized Library Health feature label Thư viện sức khỏe instead of leaving the English name in Vietnamese copy.'),
 (181,'ja'): ('シグナルは無視されています','refinement','This is a persisted ignore-state badge with an eye-slash icon; the existing シグナルを無視 reads like an instruction to ignore signals, while this states that they are ignored.'),
 (182,'ar'): ('، عنوان IP:','refinement','This is the final comma-separated field in a user details line. Preserve the source separator with Arabic punctuation before the IP-address label.'),
 (185,'pt-BR'): ('formato sobre a carga útil canônica de entrada/saída e a chave pública fornecida.','correction','The caller is a technical explanation of signed Pod membership operations. licença means “license”; entrada/saída correctly expresses the join/leave events.'),
 (187,'id'): ('nama pengguna','correction','The callers use this as the Username placeholder in a message field and as a username value in interpolated labels. nama belakang means “surname/last name”.'),
 (188,'fr'): ('Lancez SQLite vacuum pour compacter la base de données locale des messages et récupérer l’espace disque inutilisé. Cela peut prendre du temps.','correction','The exact caller is maintenance for the local Pod message database. The current wording drops “messages” and the unused-disk-space detail; include both while retaining the SQLite vacuum operation.'),
 (191,'de'): ('Protokollstufe','refinement','The caller is the severity column in the system logs table; Protokollstufe is clearer than Ebene, which can mean a layer.'),
 (193,'ar'): ('مستوى الثقة:','refinement','The caller renders a numeric confidence score. This names its degree explicitly and matches the catalog’s “Avg Confidence:” term متوسط الثقة.'),
 (193,'de'): ('Konfidenz:','correction','The caller renders a numeric match-confidence score. Vertrauen means trust; the catalog uses Konfidenz in “Avg Confidence:”.'),
 (193,'hi'): ('विश्वास स्तर:','correction','The caller renders a numeric match-confidence score. आत्मविश्वास suggests personal self-confidence; this names the score level and follows the catalog’s “Avg Confidence:” term विश्वास.'),
 (193,'id'): ('Tingkat keyakinan:','correction','The caller renders a numeric match-confidence score. Kepercayaan diri means self-confidence; this names the score level and follows the catalog’s “Avg Confidence:” term Keyakinan.'),
 (193,'ja'): ('信頼度：','correction','The caller renders a numeric match-confidence score. 自信 means self-confidence; the catalog already uses 信頼度 in “Avg Confidence:”.'),
 (193,'ko'): ('신뢰도:','correction','The caller renders a numeric match-confidence score. 신뢰 is only “trust”; the catalog already uses 신뢰도 in “Avg Confidence:”.'),
 (193,'vi'): ('Độ tin cậy:','correction','The caller renders a numeric match-confidence score. Sự tự tin suggests personal self-confidence; the catalog already uses Độ tin cậy in “Avg Confidence:”.'),
 (193,'zh-Hans'): ('置信度：','refinement','The caller renders a numeric match-confidence score. 信心 is broad personal confidence; 置信度 is the established catalog term in “Avg Confidence:”.'),
 (193,'zh-Hant'): ('信賴度：','refinement','The caller renders a numeric match-confidence score. 信心 is broad personal confidence; 信賴度 is the established Traditional Chinese catalog term in “Avg Confidence:”.'),
 (194,'ar'): ('خطافات الأحداث، والأهداف البعيدة، وخطافات الأوامر، وإعدادات إعادة المحاولة.','refinement','This is the description of the Actions: Webhooks and Scripts card, whose fields expose webhook retry attempts and download retry behavior. إعدادات إعادة المحاولة expresses retry settings rather than a physical shape.'),
 (194,'de'): ('Ereignis-Hooks, Remote-Ziele, Befehls-Hooks und Einstellungen für Wiederholungsversuche.','refinement','The caller is the Actions: Webhooks and Scripts card with retry-attempt and retry-delay settings. Translate the awkward source phrase retry shape as retry settings.'),
 (194,'es'): ('Ganchos de eventos, destinos remotos, ganchos de comandos y configuración de reintentos.','refinement','The caller is the Actions: Webhooks and Scripts card with retry-attempt and retry-delay settings. configuración de reintentos expresses that configuration rather than a literal shape.'),
 (194,'fr'): ('Hooks d’événements, cibles distantes, hooks de commande et paramètres de nouvelle tentative.','refinement','The caller is the Actions: Webhooks and Scripts card with retry-attempt and retry-delay settings. paramètres de nouvelle tentative expresses the configuration rather than a literal shape.'),
 (194,'hi'): ('इवेंट हुक, दूरस्थ लक्ष्य, कमांड हुक और पुनः प्रयास सेटिंग्स।','refinement','The caller is the Actions: Webhooks and Scripts card with retry-attempt and retry-delay settings. पुनः प्रयास सेटिंग्स expresses retry settings rather than a literal shape.'),
 (194,'id'): ('Kait peristiwa, target jarak jauh, kait perintah, dan pengaturan percobaan ulang.','refinement','The caller is the Actions: Webhooks and Scripts card with retry-attempt and retry-delay settings. pengaturan percobaan ulang expresses retry settings rather than a literal shape.'),
 (194,'ja'): ('イベントフック、リモートターゲット、コマンドフック、再試行設定。','refinement','The caller is the Actions: Webhooks and Scripts card with retry-attempt and retry-delay settings. 再試行設定 expresses retry settings rather than a literal shape.'),
 (194,'ko'): ('이벤트 후크, 원격 대상, 명령 후크 및 재시도 설정.','refinement','The caller is the Actions: Webhooks and Scripts card with retry-attempt and retry-delay settings. 재시도 설정 expresses retry settings rather than a literal shape.'),
 (194,'pt-BR'): ('Ganchos de eventos, destinos remotos, ganchos de comando e configurações de novas tentativas.','refinement','The caller is the Actions: Webhooks and Scripts card with retry-attempt and retry-delay settings. configurações de novas tentativas expresses retry settings rather than a literal shape.'),
 (194,'vi'): ('Móc sự kiện, mục tiêu từ xa, móc lệnh và cài đặt thử lại.','refinement','The caller is the Actions: Webhooks and Scripts card with retry-attempt and retry-delay settings. cài đặt thử lại expresses retry settings rather than a literal shape.'),
 (194,'zh-Hans'): ('事件挂钩、远程目标、命令挂钩和重试设置。','refinement','The caller is the Actions: Webhooks and Scripts card with retry-attempt and retry-delay settings. 重试设置 expresses retry settings rather than a literal shape.'),
 (194,'zh-Hant'): ('事件掛鉤、遠端目標、命令掛鉤和重試設定。','refinement','The caller is the Actions: Webhooks and Scripts card with retry-attempt and retry-delay settings. 重試設定 expresses retry settings rather than a literal shape.'),
}

def sha(v): return hashlib.sha256(v.encode('utf-8') if isinstance(v,str) else v).hexdigest()
def readjl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def ph(v): return collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',v))
def markup(v): return collections.Counter(re.findall(r'<\/?[A-Za-z][^>]*>',v))
PROTECTED={179:['Pod'],184:['slskdN','BitTorrent','DHT'],188:['SQLite'],198:['Meek']}

source_rows=readjl(ROOT/'source-current-cells.jsonl')
callers=readjl(ROOT/'caller-contexts.jsonl')
caller_by_id={r['sourceId']:r for r in callers}
assert len(source_rows)==300 and len(caller_by_id)==25
assert all(r['productionCallerCount']>0 for r in callers)
rows=[]; counts=collections.Counter(); changed_by_locale=collections.Counter(); changed_by_source=collections.Counter()
placeholder_mismatches=[]; markup_mismatches=[]; protected_current_mismatches=[]; protected_candidate_mismatches=[]
for item in source_rows:
    rank=item['continuationRank']
    source=item['source']; source_id=item['sourceId']; loc=item['locale']; current=item['currentTarget']
    candidate_info=CANDIDATES.get((rank,loc))
    if candidate_info:
        candidate,disposition,rationale=candidate_info
    else:
        candidate=current; disposition='accept-current'
        rationale='The current target preserves the source meaning in the pinned production caller and has no clear material defect. Placeholder and markup parity were checked.'
    source_ph=ph(source); current_ph=ph(current); candidate_ph=ph(candidate)
    source_markup=markup(source); current_markup=markup(current); candidate_markup=markup(candidate)
    ph_ok=source_ph==current_ph and source_ph==candidate_ph
    markup_ok=source_markup==current_markup and source_markup==candidate_markup
    if not ph_ok: placeholder_mismatches.append({'rank':rank,'sourceId':source_id,'locale':loc})
    if not markup_ok: markup_mismatches.append({'rank':rank,'sourceId':source_id,'locale':loc})
    caller=caller_by_id[source_id]
    protected_checks=[]
    for literal in PROTECTED.get(rank,[]):
        current_ok=literal in current; candidate_ok=literal in candidate
        protected_checks.append({'literal':literal,'policy':'exact case-sensitive product/protocol token','currentPreserved':current_ok,'candidatePreserved':candidate_ok})
        if not current_ok: protected_current_mismatches.append({'rank':rank,'sourceId':source_id,'locale':loc,'literal':literal})
        if not candidate_ok: protected_candidate_mismatches.append({'rank':rank,'sourceId':source_id,'locale':loc,'literal':literal})
    row={'continuationRank':rank,'historicalSourceOrdinal':None,'sourceId':source_id,'source':source,'sourceSha256':sha(source),'locale':loc,'catalogPath':item['catalogPath'],'catalogFileSha256':item['catalogFileSha256'],'catalogGitBlob':item['catalogGitBlob'],'currentTarget':current,'currentTargetSha256':sha(current),'candidateTarget':candidate,'candidateTargetSha256':sha(candidate),'verdict':disposition,'rationale':rationale,'confidence':'moderate' if disposition!='accept-current' else 'moderate','callerContextSha256':item['callerContextSha256'],'callerRefs':item['callerRefs'],'placeholderCheck':{'source':dict(source_ph),'current':dict(current_ph),'candidate':dict(candidate_ph),'sourceMatchesCurrent':source_ph==current_ph,'sourceMatchesCandidate':source_ph==candidate_ph},'markupCheck':{'source':dict(source_markup),'current':dict(current_markup),'candidate':dict(candidate_markup),'sourceMatchesCurrent':source_markup==current_markup,'sourceMatchesCandidate':source_markup==candidate_markup},'protectedLiteralChecks':protected_checks}
    rows.append(row); counts[disposition]+=1
    if candidate!=current:
        changed_by_locale[loc]+=1; changed_by_source[source_id]+=1
assert len(rows)==300 and not placeholder_mismatches and not markup_mismatches and not protected_candidate_mismatches
( ROOT/'review-decisions.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
summary={'repository':'snapetech-org/slskdN','pullRequest':409,'exactHead':HEAD,'exactTree':TREE,'window':'W51 exact W49 stable-ID inventory ranks 176-200; historical source ordinals unavailable','sourceCount':25,'localeCount':12,'cellCount':300,'dispositionCounts':dict(counts),'candidateChangeCount':sum(changed_by_locale.values()),'changedCellsByLocale':dict(changed_by_locale),'changedCellsBySource':dict(changed_by_source),'holdCount':counts['hold-context'],'callerReferenceCount':sum(x['productionCallerCount'] for x in callers),'callerlessSourceIds':[x['sourceId'] for x in callers if x['productionCallerCount']==0],'placeholderMismatchCount':len(placeholder_mismatches),'markupMismatchCount':len(markup_mismatches),'currentProtectedLiteralMismatchCount':len(protected_current_mismatches),'candidateProtectedLiteralMismatchCount':len(protected_candidate_mismatches),'nativeSpeakerApproval':False,'headedBrowserReview':False,'testsBuildScansCiRun':False,'repositoryModified':False,'remoteMutation':False,'reviewConfidence':'moderate machine-assisted primary review only','rankBasis':'W49 pinned stable-ID inventory; W50 declared 126-150 labels map to W49 ranks 151-175; W51 continues W49 ranks 176-200','changes':[{ 'rank':r['continuationRank'],'sourceId':r['sourceId'],'source':r['source'],'locale':r['locale'],'from':r['currentTarget'],'to':r['candidateTarget'],'disposition':r['verdict'],'rationale':r['rationale']} for r in rows if r['candidateTarget']!=r['currentTarget']]}
(ROOT/'review-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:summary[k] for k in ['exactHead','exactTree','sourceCount','cellCount','dispositionCounts','candidateChangeCount','changedCellsByLocale','callerReferenceCount','placeholderMismatchCount','markupMismatchCount']},ensure_ascii=False,indent=2))
