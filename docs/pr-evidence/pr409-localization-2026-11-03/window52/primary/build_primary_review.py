#!/usr/bin/env python3
"""Record a hash-bound primary review of slskdN PR #409 W52 cells."""
from pathlib import Path
import collections, hashlib, json, re

ROOT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window52-primary-20261103/primary')
HEAD = 'f63c8c04f3b1c3fb5e1bc8971a0d83bbf8ca4e77'
TREE = 'ca9f1bf1d9f4373556476a51b863601668878eb3'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

# Caller-supported concrete corrections and focused refinements only.
CANDIDATES = {
 (202,'ar'): ('بدأ {title} فحص {libraryPath} (المعرّف {scanId}).','refinement','The caller reports a completed scan against the entered library path. This wording makes the scanned path explicit instead of describing it as something being searched for.'),
 (202,'de'): ('{title} hat den Scan {scanId} für {libraryPath} gestartet.','refinement','The caller reports a scan started against the entered path; für clearly identifies the path as the scan target.'),
 (202,'es'): ('{title} inició el análisis {scanId} de {libraryPath}.','refinement','The caller reports a scan of the entered library path. de avoids the current en busca de wording, which reads as searching for the path.'),
 (202,'vi'): ('{title} đã bắt đầu quét {libraryPath} (mã {scanId}).','refinement','The caller reports a scan of the entered library path. The current để tìm phrasing says the scan is looking for the path.'),
 (202,'zh-Hans'): ('{title} 已开始扫描 {libraryPath}（扫描 ID：{scanId}）。','refinement','The caller reports a scan against the entered library path; this names the path as the scan target.'),
 (202,'zh-Hant'): ('{title} 已開始掃描 {libraryPath}（掃描 ID：{scanId}）。','refinement','The caller reports a scan against the entered library path; this names the path as the scan target.'),
 (203,'es'): ('Filtros de descarga guardados','correction','This is a success toast after saving download filters. The current Descargar filtros guardados reads as an infinitive command, not saved filters.'),
 (203,'fr'): ('Filtres de téléchargement enregistrés','correction','This is a success toast after saving download filters. The current Télécharger les filtres enregistrés reads as an infinitive command.'),
 (203,'id'): ('Filter unduhan tersimpan','correction','This is a success toast after saving download filters. The current Unduh filter disimpan uses the verb “download” and has incorrect word order.'),
 (205,'zh-Hans'): ('下载：{downloadError}','correction','This is an alert label for a download error value, not a count of downloads; 次数 incorrectly means a number of times.'),
 (205,'zh-Hant'): ('下載：{downloadError}','correction','This is an alert label for a download error value, not a count of downloads; 次數 incorrectly means a number of times.'),
 (210,'hi'): ('सामग्री फिर से लोड करें','refinement','The button tooltip says it retries loading this collection’s contents. This expresses reloading content as an action.'),
 (210,'id'): ('Muat ulang konten','correction','The button tooltip says it retries loading this collection’s contents. The current wording is awkward and does not clearly express reloading.'),
 (210,'ja'): ('コンテンツを再読み込み','correction','The button tooltip says it retries loading this collection’s contents. This uses the normal UI action for reloading content.'),
 (210,'ko'): ('콘텐츠 다시 불러오기','correction','The button tooltip says it retries loading this collection’s contents. This uses the normal UI action for loading the content again.'),
 (210,'zh-Hans'): ('重新加载内容','correction','The button tooltip says it retries loading this collection’s contents. This expresses reloading the content rather than retrying the content itself.'),
 (210,'zh-Hant'): ('重新載入內容','correction','The button tooltip says it retries loading this collection’s contents. This expresses reloading the content rather than retrying the content itself.'),
 (211,'es'): ('Reconstruye el índice local de búsqueda de mensajes a partir de los mensajes almacenados si los resultados están desactualizados o incompletos.','correction','The caller describes rebuilding a local message-search index from stored messages. The current text omits the stored-message source.'),
 (211,'pt-BR'): ('Reconstrua o índice local de pesquisa de mensagens a partir das mensagens armazenadas se os resultados estiverem desatualizados ou incompletos.','correction','The caller describes rebuilding a local message-search index from stored messages. The current text says stored content and omits that the index is for message search.'),
 (212,'ar'): ('ابدأ ما يصل إلى ثلاث عمليات بحث من مسارات الجلسات الأخيرة المشابهة. تبدأ هذه العملية مهام البحث فقط.','correction','The caller starts bounded search jobs from recent listening-session tracks. The current البحث عن الوظائف means job hunting; مهام البحث means search tasks.'),
 (212,'es'): ('Inicie hasta tres búsquedas a partir de pistas de sesiones recientes similares. Esto solo inicia tareas de búsqueda.','correction','The caller starts search jobs, not employment searches. tareas de búsqueda names the technical jobs.'),
 (212,'fr'): ('Lancez jusqu’à trois recherches à partir de pistes de sessions récentes similaires. Cela lance uniquement des tâches de recherche.','correction','The caller starts search jobs, not job hunting. tâches de recherche names the technical tasks.'),
 (212,'hi'): ('समान हालिया सत्र ट्रैक से अधिकतम तीन खोजें शुरू करें। इससे केवल खोज कार्य शुरू होते हैं।','correction','The caller starts search jobs, not employment searches. खोज कार्य names the technical tasks.'),
 (212,'id'): ('Mulai hingga tiga pencarian dari trek sesi terbaru yang serupa. Ini hanya memulai tugas pencarian.','correction','The caller starts search jobs. tugas pencarian is clearer than pekerjaan pencarian, which can read as job hunting.'),
 (212,'pt-BR'): ('Inicie até três buscas a partir de faixas de sessões recentes semelhantes. Isso inicia apenas tarefas de busca.','correction','The caller starts search jobs; tarefas de busca avoids reading the technical search jobs as employment or research work.'),
 (212,'vi'): ('Bắt đầu tối đa ba lượt tìm kiếm từ các bản nhạc phiên gần đây tương tự. Thao tác này chỉ khởi chạy các tác vụ tìm kiếm.','refinement','The caller starts search jobs from recent session tracks. This makes the second sentence clearly refer to search tasks.'),
 (214,'ar'): ('تشغيل الإجراءات الجاهزة','correction','The button’s explicit tooltip says “Run ready Servarr actions now.” The current phrase is not a natural action label.'),
 (214,'de'): ('Bereitstehende Aktionen ausführen','correction','The button’s explicit tooltip says “Run ready Servarr actions now.” This is a natural German action label for actions that are ready.'),
 (214,'es'): ('Ejecutar acciones disponibles','correction','The button’s explicit tooltip says “Run ready Servarr actions now.” The current Ejecutar listo is ungrammatical.'),
 (214,'fr'): ('Exécuter les actions prêtes','correction','The button’s explicit tooltip says “Run ready Servarr actions now.” The current Prêt à courir is not an action label.'),
 (214,'hi'): ('तैयार कार्रवाइयाँ चलाएँ','correction','The button’s explicit tooltip says “Run ready Servarr actions now.” The current wording is ungrammatical.'),
 (214,'id'): ('Jalankan tindakan yang siap','correction','The button’s explicit tooltip says “Run ready Servarr actions now.” The current word order is unnatural.'),
 (214,'ja'): ('準備完了の操作を実行','correction','The button’s explicit tooltip says “Run ready Servarr actions now.” This is a concise Japanese action label.'),
 (214,'ko'): ('준비된 작업 실행','correction','The button’s explicit tooltip says “Run ready Servarr actions now.” This is a concise Korean action label.'),
 (214,'pt-BR'): ('Executar ações prontas','correction','The button’s explicit tooltip says “Run ready Servarr actions now.” The current Execute pronto is ungrammatical.'),
 (214,'vi'): ('Chạy các thao tác đã sẵn sàng','correction','The button’s explicit tooltip says “Run ready Servarr actions now.” This makes the action and ready state explicit.'),
 (214,'zh-Hans'): ('执行已就绪的操作','correction','The button’s explicit tooltip says “Run ready Servarr actions now.” This expresses executing the actions that are ready.'),
 (214,'zh-Hant'): ('執行已就緒的操作','correction','The button’s explicit tooltip says “Run ready Servarr actions now.” This expresses executing the actions that are ready.'),
 (215,'ar'): ('إنشاء Pod','correction','The caller creates a durable Pod with a default channel. جراب means a bag or pouch; Pod is the app’s group concept.'),
 (215,'fr'): ('Créer un Pod','correction','The caller creates a durable Pod with a default channel. module means a module and does not name this group concept.'),
 (218,'es'): ('Cargar recomendaciones','correction','This is a button that loads recommendations. Recomendaciones de carga reads as cargo/load recommendations.'),
 (218,'fr'): ('Charger les recommandations','correction','This is a button that loads recommendations. Recommandations de charge reads as freight/load recommendations.'),
 (218,'id'): ('Muat rekomendasi','refinement','This is a button action. The imperative muat is more suitable than the gerund Memuat.'),
 (218,'ja'): ('おすすめを読み込む','refinement','This is a button action to load recommendations; this is more natural Japanese UI wording than the katakana loanword.'),
 (218,'pt-BR'): ('Carregar recomendações','correction','This is a button that loads recommendations. Recomendações de carga reads as cargo/load recommendations.'),
 (218,'zh-Hans'): ('加载推荐','correction','This is a button action to load recommendations. 负载 means load/cargo rather than the verb “load.”'),
 (218,'zh-Hant'): ('載入推薦','correction','This is a button action to load recommendations. 負載 means load/cargo rather than the verb “load.”'),
 (219,'zh-Hans'): ('已启动 1 次范围受限的聆听种子搜索。','refinement','The caller reports a bounded search seeded from listening history. 有界 is a geometric/mathematical bound; 范围受限 expresses a constrained search.'),
 (219,'zh-Hant'): ('已啟動 1 次範圍受限的聆聽種子搜尋。','refinement','The caller reports a bounded search seeded from listening history. 有界 is a geometric/mathematical bound; 範圍受限 expresses a constrained search.'),
 (221,'ar'): ('غير مفعّل','correction','The caller displays a disabled state. عاجز describes a person as unable/incapacitated rather than a setting that is off.'),
 (221,'id'): ('nonaktif','correction','The caller displays a disabled state. dengan disabilitas means “with a disability,” not a setting that is off.'),
 (221,'ko'): ('비활성화됨','correction','The caller displays a disabled state. 장애가 있는 describes a person with a disability rather than a setting that is off.'),
 (221,'vi'): ('đã tắt','correction','The caller displays a disabled state. tàn tật describes disability rather than a setting that is off.'),
 (221,'zh-Hans'): ('已禁用','correction','The caller displays a disabled state. 残疾人 means a person with disabilities rather than a setting that is off.'),
 (221,'zh-Hant'): ('已停用','correction','The caller displays a disabled state. 殘障人士 means a person with disabilities rather than a setting that is off.'),
 (223,'fr'): ('Configuration du tunnel HTTP','refinement','The caller is the heading for the single HTTP tunnel configuration section; the current plural tunnels mismatches the source.'),
 (224,'ko'): ('입력된 서버 측 경로에 대한 재귀적 읽기 전용 스캔을 시작합니다.','correction','The caller reports a recursive scan. 반복적인 means repetitive, while 재귀적 means recursive.'),
}

def sha(v): return hashlib.sha256(v.encode('utf-8') if isinstance(v,str) else v).hexdigest()
def readjl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def ph(v): return collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',v))
def markup(v): return collections.Counter(re.findall(r'<\/?[A-Za-z][^>]*>',v))
PROTECTED={207:['I2P'],213:['320'],222:['SourceText'],223:['HTTP']}

source_rows=readjl(ROOT/'source-current-cells.jsonl')
callers=readjl(ROOT/'caller-contexts.jsonl')
caller_by_id={r['sourceId']:r for r in callers}
assert len(source_rows)==300 and len(caller_by_id)==25
assert all(r['productionCallerCount']>0 for r in callers)
assert all((rank,loc) in {(r['continuationRank'],r['locale']) for r in source_rows} for rank,loc in CANDIDATES)
assert len(CANDIDATES)==len(set(CANDIDATES))
rows=[]; counts=collections.Counter(); changed_by_locale=collections.Counter(); changed_by_source=collections.Counter()
placeholder_mismatches=[]; markup_mismatches=[]; protected_current_mismatches=[]; protected_candidate_mismatches=[]
for item in source_rows:
    rank=item['continuationRank']; source=item['source']; source_id=item['sourceId']; loc=item['locale']; current=item['currentTarget']
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
        protected_checks.append({'literal':literal,'policy':'exact case-sensitive API/protocol/metric token','currentPreserved':current_ok,'candidatePreserved':candidate_ok})
        if not current_ok: protected_current_mismatches.append({'rank':rank,'sourceId':source_id,'locale':loc,'literal':literal})
        if not candidate_ok: protected_candidate_mismatches.append({'rank':rank,'sourceId':source_id,'locale':loc,'literal':literal})
    row={'continuationRank':rank,'historicalSourceOrdinal':None,'sourceId':source_id,'source':source,'sourceSha256':sha(source),'locale':loc,'catalogPath':item['catalogPath'],'catalogFileSha256':item['catalogFileSha256'],'catalogGitBlob':item['catalogGitBlob'],'currentTarget':current,'currentTargetSha256':sha(current),'candidateTarget':candidate,'candidateTargetSha256':sha(candidate),'verdict':disposition,'rationale':rationale,'confidence':'moderate','callerContextSha256':item['callerContextSha256'],'callerRefs':item['callerRefs'],'placeholderCheck':{'source':dict(source_ph),'current':dict(current_ph),'candidate':dict(candidate_ph),'sourceMatchesCurrent':source_ph==current_ph,'sourceMatchesCandidate':source_ph==candidate_ph},'markupCheck':{'source':dict(source_markup),'current':dict(current_markup),'candidate':dict(candidate_markup),'sourceMatchesCurrent':source_markup==current_markup,'sourceMatchesCandidate':source_markup==candidate_markup},'protectedLiteralChecks':protected_checks}
    rows.append(row); counts[disposition]+=1
    if candidate!=current:
        changed_by_locale[loc]+=1; changed_by_source[source_id]+=1
assert len(rows)==300 and not placeholder_mismatches and not markup_mismatches and not protected_candidate_mismatches
(ROOT/'review-decisions.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
selection=json.loads((ROOT/'selection-and-boundary.json').read_text(encoding='utf-8'))
summary={'repository':'snapetech-org/slskdN','pullRequest':409,'exactHead':HEAD,'exactTree':TREE,'pinnedBodySha256':'9e44ad9c48f8cfb4efbd4855737940e57ed212aaaad3c5e5942d4efb02838bc9','window':'W52 exact W49 stable-ID inventory ranks 201-225; historical source ordinals unavailable','sourceCount':25,'localeCount':12,'cellCount':300,'dispositionCounts':dict(counts),'candidateChangeCount':sum(changed_by_locale.values()),'changedCellsByLocale':dict(changed_by_locale),'changedCellsBySource':dict(changed_by_source),'holdCount':counts['hold-context'],'callerReferenceCount':sum(x['productionCallerCount'] for x in callers),'callerlessSourceIds':[x['sourceId'] for x in callers if x['productionCallerCount']==0],'placeholderMismatchCount':len(placeholder_mismatches),'markupMismatchCount':len(markup_mismatches),'currentProtectedLiteralMismatchCount':len(protected_current_mismatches),'candidateProtectedLiteralMismatchCount':len(protected_candidate_mismatches),'nativeSpeakerApproval':False,'headedBrowserReview':False,'testsBuildScansCiRun':False,'repositoryModified':False,'remoteMutation':False,'reviewConfidence':'moderate machine-assisted primary review only','rankBasis':'W49 pinned stable-ID inventory; W50 declared ranks 126-150 map to W49 ranks 151-175; W51 used ranks 176-200; W52 continues ranks 201-225. W49 ranks 126-150 remain unreviewed.','selectionFirstSourceId':selection['firstSelected']['sourceId'],'selectionLastSourceId':selection['lastSelected']['sourceId'],'selectionNextBoundarySourceId':selection['nextBoundary']['sourceId'],'changes':[{'rank':r['continuationRank'],'sourceId':r['sourceId'],'source':r['source'],'locale':r['locale'],'from':r['currentTarget'],'to':r['candidateTarget'],'disposition':r['verdict'],'rationale':r['rationale']} for r in rows if r['candidateTarget']!=r['currentTarget']]}
(ROOT/'review-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:summary[k] for k in ['exactHead','exactTree','sourceCount','cellCount','dispositionCounts','candidateChangeCount','changedCellsByLocale','callerReferenceCount','placeholderMismatchCount','markupMismatchCount','candidateProtectedLiteralMismatchCount']},ensure_ascii=False,indent=2))
