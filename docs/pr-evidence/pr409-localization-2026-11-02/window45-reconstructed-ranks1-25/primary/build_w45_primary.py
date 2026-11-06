from __future__ import annotations
import hashlib,json,re,subprocess
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
OUT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window45-primary-reconstructed-20261102')
WORK=Path('/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn')
HEAD='6a082138c09fa8af40aee3258beb98523ee821d9'; TREE='90142bfd8904d2a4428ea5f144848ba1c743bdd7'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def jl(path): return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
def dumpj(path,obj): Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
def dumpjl(path,rows): Path(path).write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rows))
def git(*args): return subprocess.check_output(['git','-C',str(WORK),*args])
assert git('rev-parse','HEAD').decode().strip()==HEAD
assert git('rev-parse','HEAD^{tree}').decode().strip()==TREE
assert git('status','--porcelain').decode().strip()==''
assert git('branch','--show-current').decode().strip()=='codex/slskdn-localization-apply-20261102'
selection=jl(OUT/'source-selection.jsonl'); cells=jl(OUT/'input-cells.jsonl'); calls=jl(OUT/'caller-context.jsonl')
assert len(selection)==25 and [x['selectionRank'] for x in selection]==list(range(1,26))
assert len(cells)==300 and len(calls)==25
byrank={x['selectionRank']:x for x in selection}; cellmap={(x['selectionRank'],x['locale']):x for x in cells}
assert set(cellmap)=={(r,l) for r in range(1,26) for l in LOCALES}
contexts={
1:'Transfer table shows the next scheduled retry time alongside a refresh glyph.',
2:'Discovery graph localization helper reports the number of attached evidence items.',
3:'Pod kind label in pod and port-forwarding UI; Pod is the product term.',
4:'Library health report appends this localized suffix and a normalized file path to an issue line.',
5:'Search candidate ranking reason label for a match based on title, album, and duration.',
6:'Discovery graph helper describes the seed artist that anchors discovery topology.',
7:'Admin policy input label and accessible name for the DHT UDP port field.',
8:'Mesh evidence review button tooltip describes the browser-local sample trust and privacy cases.',
9:'Admin policy field label for the list of script event names that trigger a configured script.',
10:'Discovery shelf preview label reports the count of items gated by missing consensus.',
11:'Directory tree toggle aria-label for expanding a named directory; TooltipButton translates the dynamic label.',
12:'VPN gateway service dialog cancel tooltip; TooltipButton routes tooltip strings through LocalizedPopup and t().',
13:'MediaCore statistics error section header.',
14:'Search candidate ranking reason for a preferred lossless audio-format match.',
15:'Retry tooltip in the unavailable adversarial-security-settings panel; adjacent copy defines these as security options for adversarial environments.',
16:'Admin policy tooltip for redirecting HTTP requests to HTTPS after certificate settings become valid.',
17:'Regional-format card description; a local helper passes the source through t().',
18:'Source-feed import limit validation API message; error code maps through interfaceTextOutput and renders as localized error output.',
19:'System Logs table column header for file modification time.',
20:'System Metrics unavailable/error header.',
21:'Files Explorer operation summary selects the plural source when multiple items were deleted; LocalizedText translates it dynamically.',
22:'Search page toast shown when the submitted search phrase is empty; a component helper passes the string through t().',
23:'Player file-list/search pagination tooltip for moving to the next page.',
24:'MediaCore warning about batch descriptor publication and safer default retrieval/statistics paths.',
25:'Member list/action label shared by Messaging, Pod port forwarding, and Share Groups.'}
# Explicit review proposals are keyed by reconstructed rank and locale.
C={
(2,'ar'):('تم إرفاق {count} من عناصر الأدلة.','propose-correction','Uses a count construction that does not force an Arabic plural form across changing count values.','moderate'),
(7,'id'):('Port UDP untuk DHT','propose-correction','Pelabuhan means a harbor; port is the network field name here, as confirmed by the DHT/UDP admin input.','high'),
(8,'ar'):('حمّل عينة محلية في المتصفح تحتوي على عنصر مقبول موقّع من النطاق وعنصر مرفوض بسبب خطر على الخصوصية.','propose-correction','Reorders the sentence so acceptable describes the item, and uses the catalog term نطاق for the Realm trust tier; privacy risk remains attached to the rejected item.','moderate'),
(8,'es'):('Cargue una muestra local del navegador que contenga un elemento aceptable firmado por el dominio y otro rechazado por riesgo para la privacidad.','propose-correction','Reorders the phrase so aceptable describes the item rather than the domain, and keeps the UI instruction in the formal Spanish register.','high'),
(8,'fr'):('Chargez un échantillon local du navigateur contenant un élément acceptable signé par le domaine et un autre rejeté en raison d’un risque pour la confidentialité.','propose-correction','Reorders the phrase so acceptable qualifies the item, with the privacy risk explaining why the second item is rejected.','moderate'),
(8,'id'):('Muat sampel lokal browser yang berisi satu item yang dapat diterima dan ditandatangani oleh ranah, serta satu item yang ditolak karena risiko privasi.','propose-correction','Bertanda alam means marked by nature; the replacement says the first item is signed by the Realm and the other is rejected for privacy risk.','high'),
(8,'pt-BR'):('Carregue uma amostra local do navegador contendo um item aceitável assinado pelo domínio e outro rejeitado por risco à privacidade.','propose-correction','Reorders the phrase so acceptable describes the item rather than the domain and keeps privacy risk attached to the rejected item.','high'),
(8,'vi'):('Tải một mẫu được lưu cục bộ trong trình duyệt, gồm một mục được ký bởi miền và được chấp nhận, cùng một mục bị từ chối vì rủi ro về quyền riêng tư.','propose-correction','Uses the catalog term miền for the Realm trust tier and makes acceptance apply to the signed item, while the second item is rejected because of privacy risk.','moderate'),
(9,'es'):('Eventos de script','propose-refinement','The caller is a software hook field for script event names; script is clearer in this programming context than guión, which can read as a screenplay.','moderate'),
(9,'id'):('Peristiwa Skrip','propose-correction','Naskah usually means a manuscript or screenplay; Peristiwa Skrip labels software script events in the hook configuration field.','moderate'),
(11,'hi'):('{directory} का विस्तार करें','propose-correction','The caller is an expand/collapse tree toggle; फैलाएँ means spread and does not express expanding a directory tree.','moderate'),
(11,'es'):('Expanda {directory}','propose-correction','The source is a user-facing expand action and its Spanish formal-lane cell is pinned; use the formal usted imperative rather than the current infinitive label.','moderate'),
(12,'es'):('Cierre el cuadro de diálogo y vuelva a los servicios registrados sin añadir esta entrada.','propose-correction','Changes the two informal imperatives to formal usted forms required by the pinned Spanish formality lane.','high'),
(14,'id'):('cocok dengan format tanpa kehilangan data yang disukai','propose-refinement','Uses the established Indonesian translation of Lossless, without kehilangan data, instead of leaving the audio-format property in English.','moderate'),
(15,'ar'):('حاول تحميل إعدادات البيئة العدائية مرة أخرى بعد تفعيلها على الخادم أو استعادة الاتصال.','propose-correction','The surrounding panel defines the feature as security options for adversarial environments; this avoids the awkward الخصومة phrasing and ties the settings to that context.','moderate'),
(15,'de'):('Versuchen Sie erneut, die Einstellungen für feindliche Umgebungen zu laden, nachdem Sie sie auf dem Server aktiviert oder die Verbindung wiederhergestellt haben.','propose-correction','The surrounding panel describes security options for adversarial environments; the current gegnerischen Einstellungen can read as settings belonging to an opponent.','moderate'),
(15,'es'):('Intente cargar de nuevo las configuraciones adversarias después de activarlas en el servidor o restablecer la conexión.','propose-correction','Adverse is not the same as adversarial in this security panel; this uses an adversarial form and preserves the formal imperative.','moderate'),
(15,'fr'):('Essayez de charger à nouveau les paramètres pour les environnements hostiles après les avoir activés sur le serveur ou après avoir rétabli la connexion.','propose-correction','Contradictoires means contradictory; the adjacent panel defines these as security options intended for adversarial environments.','moderate'),
(15,'hi'):('सर्वर पर उन्हें सक्षम करने या कनेक्शन पुनर्स्थापित करने के बाद विरोधात्मक सेटिंग्स फिर से लोड करने का प्रयास करें।','propose-correction','Uses the established Hindi equivalent विरोधात्मक for Adversarial rather than प्रतिकूल, which means adverse.','moderate'),
(15,'id'):('Coba muat ulang pengaturan untuk lingkungan yang bermusuhan setelah mengaktifkannya di server atau memulihkan koneksi.','propose-correction','The current pengaturan permusuhan reads as settings of hostility; nearby UI explains these are security options for hostile/adversarial environments.','moderate'),
(15,'pt-BR'):('Tente carregar novamente as configurações para ambientes adversariais depois de ativá-las no servidor ou restaurar a conexão.','propose-correction','The current configurações do adversário means settings belonging to an opponent; this conveys the security settings for adversarial environments.','moderate'),
(15,'vi'):('Hãy thử tải lại cài đặt dành cho môi trường đối kháng sau khi bật chúng trên máy chủ hoặc khôi phục kết nối.','propose-correction','Đối nghịch means opposite; the surrounding security panel calls the feature adversarial, for which đối kháng conveys the hostile/adversarial environment.','moderate'),
(16,'ar'):('أعِد توجيه طلبات HTTP إلى HTTPS بعد أن تصبح إعدادات الشهادة صالحة.','propose-correction','Changes the current nominal phrase into the imperative instruction used by this setting tooltip and preserves both protocol names exactly.','moderate'),
(17,'es'):('Elija cómo se muestran las fechas, las horas y los números. Este ajuste es independiente del idioma de la interfaz.','propose-correction','Changes the informal Elige to the formal usted imperative required by the pinned Spanish formality lane.','high'),
(17,'zh-Hans'):('选择日期、时间和数字的显示方式。此设置独立于界面语言。','propose-refinement','独立于 expresses that this format choice is independent of interface language more naturally than 分开.','moderate'),
(17,'zh-Hant'):('選擇日期、時間與數字的顯示方式。此設定獨立於介面語言。','propose-refinement','獨立於 expresses that this format choice is independent of interface language more naturally than 分開.','moderate'),
(19,'ko'):('최종 수정일','propose-refinement','The caller is a file modification-time table header; adding 일 makes this read as a date/time column label rather than a passive predicate.','moderate'),
(21,'ar'):('تم حذف {count} من العناصر.','propose-correction','Uses a count construction that avoids incorrect Arabic number/plural agreement for arbitrary item counts.','moderate'),
(22,'es'):('Por favor, introduzca una frase de búsqueda.','propose-correction','Changes the informal Introduce to formal usted and retains the explicit phrase concept required by the Spanish formality lane.','high'),
(22,'pt-BR'):('Digite uma frase de pesquisa.','propose-refinement','States that a search phrase is required; the current target says to enter a search but omits the phrase/query concept.','moderate'),
(24,'de'):('Durch die Stapelveröffentlichung können mehrere Deskriptoren gleichzeitig verfügbar gemacht werden. Behalten Sie Abruf und Statistiken als Standardpfad bei; verwenden Sie dies erst, nachdem Sie jede ContentID überprüft haben.','propose-correction','Lowercases verwenden after the semicolon, following German sentence punctuation; preserves the protected ContentID literal.','high'),
(24,'es'):('La publicación por lotes puede exponer varios descriptores a la vez. Mantenga la recuperación y las estadísticas como ruta predeterminada; úselo solo después de verificar cada ContentID.','propose-correction','Lowercases úselo after the semicolon, following Spanish punctuation; preserves the formal imperative and protected ContentID literal.','high'),
(24,'hi'):('बैच प्रकाशन एक साथ कई डिस्क्रिप्टर उजागर कर सकता है। पुनर्प्राप्ति और आँकड़ों को डिफ़ॉल्ट मार्ग बनाए रखें; प्रत्येक ContentID की जाँच करने के बाद ही इसका उपयोग करें।','propose-correction','Restores the protected ASCII ContentID identifier, which is transliterated in the current target.','high'),
(24,'ko'):('일괄 게시는 한 번에 여러 설명자를 노출할 수 있습니다. 조회와 통계를 기본 경로로 유지하세요. 각 ContentID를 확인한 후에만 사용하세요.','propose-correction','조회 is a descriptor retrieval/lookup path rather than 검색 (search), and the polite imperatives match the source advice; keeps ContentID unchanged.','moderate'),
(25,'hi'):('सदस्य','propose-correction','The source is a standalone member-list/table label; सदस्यों is an oblique/genitive plural and is incomplete without a following postposition.','moderate'),
}
# Exact source-specific protected literals.
PROTECTED={
1:['↻'],3:['Pod'],7:['DHT','UDP'],16:['HTTP','HTTPS'],24:['ContentID']}
# Caller paths that require the localization dataflow rather than a literal call on the use line.
MANUAL={
11:[('src/web/src/components/Shared/FileList.jsx',70,'localized-accessibility-source',True),('src/web/src/components/Shared/TooltipButton.jsx',49,'dynamic-aria-label-localizer',False),('src/web/src/components/Shared/TooltipButton.jsx',78,'dynamic-tooltip-localization-route',False),('src/web/src/components/Shared/TooltipButton.jsx',8,'dynamic-tooltip-translation',False)],
12:[('src/web/src/components/Pods/VpnGatewayConfig.jsx',803,'tooltip-source-prop',True),('src/web/src/components/Shared/TooltipButton.jsx',70,'tooltip-source-forwarder',False),('src/web/src/components/Shared/TooltipButton.jsx',78,'dynamic-tooltip-localization-route',False),('src/web/src/components/Shared/TooltipButton.jsx',8,'dynamic-tooltip-translation',False)],
17:[('src/web/src/components/System/ExperienceSettings/index.jsx',204,'localized-source-use',True),('src/web/src/components/System/ExperienceSettings/index.jsx',79,'dynamic-localization-helper',False),('src/web/src/components/System/ExperienceSettings/index.jsx',81,'dynamic-localization-call',False)],
18:[('src/web/src/lib/apiErrorMessages.js',9,'localized-api-error-source-map',True),('src/web/src/lib/apiErrorMessages.js',25,'api-error-code-to-source-resolver',False),('src/web/src/lib/apiErrorMessages.js',34,'dynamic-interface-output-localizer',False),('src/slskd/SourceFeeds/API/SourceFeedImportsController.cs',48,'production-api-error-emitter',True),('src/web/src/components/LoginForm.jsx',206,'localized-api-error-output-renderer',False)],
21:[('src/web/src/components/System/Files/Explorer.jsx',560,'dynamic-localized-source-selection',True),('src/web/src/components/Shared/LocalizedText.jsx',37,'localized-component-source-prop',False),('src/web/src/components/Shared/LocalizedText.jsx',42,'dynamic-localization-call',False)],
22:[('src/web/src/components/Search/Searches.jsx',532,'localized-toast-source-use',True),('src/web/src/components/Search/Searches.jsx',189,'dynamic-localization-helper',False),('src/web/src/components/Search/Searches.jsx',191,'dynamic-localization-call',False)],
}
# Build exact line refs from git blobs at the pinned tree.
file_cache={}; blob_cache={}
def ref(rank,path,line,role,exact):
 if path not in file_cache:
  raw=git('show',f'{HEAD}:{path}'); file_cache[path]=raw.decode('utf-8').splitlines(); blob_cache[path]=git('rev-parse',f'{HEAD}:{path}').decode().strip()
 lines=file_cache[path]; assert 1<=line<=len(lines),(path,line)
 item=byrank[rank]; src=item['source']; text=lines[line-1]
 if exact: assert src in text,(rank,path,line,src,text)
 return {'selectionRank':rank,'sourceId':item['sourceId'],'source':src,'sourceSha256':item['sourceSha256'],'path':path,'line':line,'lineText':text,'lineSha256':sha(text),'fileSha256':sha(git('show',f'{HEAD}:{path}')),'blobOid':blob_cache[path],'contextBefore':lines[max(0,line-4):line-1],'contextAfter':lines[line:min(len(lines),line+3)],'referenceRole':role,'exactSourceLiteralMatch':exact,'verifiedAtCurrentHead':True}
for r,refs in MANUAL.items():
 caller=next(x for x in calls if x['selectionRank']==r)
 new=[ref(r,*spec) for spec in refs]
 existing={(x['path'],x['line'],x['referenceRole']):x for x in caller['callerRefs']}
 for x in new: existing[(x['path'],x['line'],x['referenceRole'])]=x
 caller['callerRefs']=sorted(existing.values(),key=lambda x:(x['path'],x['line'],x['referenceRole']))
 caller['callerReferenceCount']=len(caller['callerRefs'])
 caller['productionLocalizationReferenceCount']=sum(x['referenceRole']=='direct-localized-caller' for x in caller['callerRefs'])
 caller['localizedProductionDisplayReferenceCount']=sum(x['referenceRole'] not in ('test-or-story-reference','exact-literal-reference') for x in caller['callerRefs'])
 caller['callerUseStatus']='production-localization-reference-found-via-indirect-localization-path'
 caller['contextSummary']=contexts[r]
for caller in calls:
 if caller['selectionRank'] not in MANUAL:
  caller['contextSummary']=contexts[caller['selectionRank']]
  caller['localizedProductionDisplayReferenceCount']=caller['productionLocalizationReferenceCount']
  if caller['productionLocalizationReferenceCount']>0: caller['callerUseStatus']='production-localization-reference-found'
  else: raise SystemExit(f"Unresolved caller gap at rank {caller['selectionRank']}: {caller['source']}")
# Verify the formal-lane accumulator checksum and selected Spanish membership.
formal_path=WORK/'docs/pr-evidence/pr409-localization-2026-11-02/window36/primary/formal-cell-ids.jsonl'
formal_raw=formal_path.read_bytes(); formal_sha=sha(formal_raw); assert formal_sha=='7bd9c90a1176403feb36daadfecb7822616a818d15e9980c99c0bf5dc9d6f856'
formal_ids={json.loads(x)['id'] for x in formal_raw.decode().splitlines() if x.strip()}
formal_forms={1:[],2:[],3:[],4:[],5:[],6:[],7:[],8:['Load'],9:[],10:[],11:['Expand'],12:['Close','return'],13:[],14:[],15:['Try'],16:['Redirect'],17:['Choose'],18:[],19:[],20:[],21:[],22:['enter'],23:['Move'],24:['Keep','use'],25:[]}
applicability=[]
for r,item in byrank.items():
 es=cellmap[(r,'es')]; in_lane=f"es:{item['sourceId']}" in formal_ids
 forms=formal_forms[r]
 if forms: assert in_lane,(r,item['sourceId'],'expected formal lane')
 applicability.append({'selectionRank':r,'sourceId':item['sourceId'],'source':item['source'],'sourceSha256':item['sourceSha256'],'locale':'es','formalLaneAccumulatorCellPresent':in_lane,'formalLaneAccumulatorSha256':formal_sha,'englishDirectAddressForms':forms,'currentSpanishTarget':es['currentTarget'],'currentSpanishTargetSha256':es['currentTargetSha256'],'reviewedSpanishTarget':C.get((r,'es'),(es['currentTarget'],None,None,None))[0],'reviewedSpanishTargetSha256':sha(C.get((r,'es'),(es['currentTarget'],))[0]),'reviewedRegisterDisposition':'formal-imperative-current-or-proposed' if forms else 'neutral-label-or-non-address','formalRegisterApplicability':'formal-lane-applicable' if forms else ('accumulator-present-no-direct-address' if in_lane else 'not-applicable-no-direct-address-in-source'),'nativeSpeakerApproval':'outstanding'})
# Build all 300 exact-hash semantic dispositions and structural readbacks.
ph_re=re.compile(r'\{[A-Za-z0-9_]+\}'); markup_re=re.compile(r'</?[A-Za-z][^>]*>')
def tokens(t): return sorted(ph_re.findall(t)),sorted(markup_re.findall(t))
def litcount(t,v): return len(re.findall(r'(?<![A-Za-z0-9])'+re.escape(v)+r'(?![A-Za-z0-9])',t))
reviews=[]; proposals=[]; structural=[]; counts=Counter(); gaps=[]
for inp in cells:
 r=inp['selectionRank']; loc=inp['locale']; src=inp['source']; cur=inp['currentTarget']; item=byrank[r]; key=(r,loc)
 source_ph,source_markup=tokens(src); cur_ph,cur_markup=tokens(cur); protected=PROTECTED.get(r,[])
 missing_cur=[x for x in protected if litcount(cur,x)!=litcount(src,x)]
 cand=C.get(key)
 if cand:
  target,disp,reason,conf=cand; reviewed_sha=sha(target)
 else:
  target=cur; disp='accept-current'; reason='Current wording preserves the source meaning for the pinned caller context: '+contexts[r]
  conf='high' if r in (1,3,4,7,9,10,11,13,16,18,19,20,23,24) else 'moderate'
 reviewed_ph,reviewed_markup=tokens(target); missing_reviewed=[x for x in protected if litcount(target,x)!=litcount(src,x)]
 if source_ph!=cur_ph or source_markup!=cur_markup: raise SystemExit(f'current structure mismatch: {r}/{loc}')
 if source_ph!=reviewed_ph or source_markup!=reviewed_markup: raise SystemExit(f'review structure mismatch: {r}/{loc}')
 if missing_reviewed: raise SystemExit(f'protected literal missing from reviewed target {r}/{loc}: {missing_reviewed}')
 formal=next(x for x in applicability if x['selectionRank']==r)
 row={'exactHead':HEAD,'exactTree':TREE,'selectionRank':r,'selectionRankBasis':'lexicographic rank among pending source IDs; historical ordinal unavailable','sourceOrdinal':None,'sourceId':inp['sourceId'],'sourceText':src,'sourceSha256':inp['sourceSha256'],'locale':loc,'catalogPath':inp['catalogPath'],'catalogBlobOid':inp['catalogBlobOid'],'catalogFileSha256':inp['catalogFileSha256'],'currentTarget':cur,'currentTargetSha256':inp['currentTargetSha256'],'reviewedTarget':target,'reviewedTargetSha256':sha(target),'disposition':disp,'confidence':conf,'rationale':reason,'callerContextSummary':contexts[r],'callerUseStatus':next(x['callerUseStatus'] for x in calls if x['selectionRank']==r),'callerRefsSourceId':inp['sourceId'],'sourcePlaceholders':source_ph,'currentTargetPlaceholders':cur_ph,'reviewedTargetPlaceholders':reviewed_ph,'sourceMarkup':source_markup,'currentTargetMarkup':cur_markup,'reviewedTargetMarkup':reviewed_markup,'currentPlaceholderParity':'exact','reviewedPlaceholderParity':'exact','currentMarkupParity':'exact','reviewedMarkupParity':'exact','protectedLiterals':protected,'currentProtectedLiteralMismatches':missing_cur,'reviewedProtectedLiteralMismatches':missing_reviewed,'protectedLiteralParity':'exact' if not missing_reviewed else 'mismatch','spanishFormalApplicability':formal['formalRegisterApplicability'] if loc=='es' else None,'nativeSpeakerReview':'outstanding'}
 reviews.append(row); counts[disp]+=1
 if cand:
  proposals.append({'exactHead':HEAD,'exactTree':TREE,'selectionRank':r,'sourceOrdinal':None,'sourceId':inp['sourceId'],'source':src,'sourceSha256':inp['sourceSha256'],'locale':loc,'catalogPath':inp['catalogPath'],'catalogBlobOid':inp['catalogBlobOid'],'catalogFileSha256':inp['catalogFileSha256'],'currentTarget':cur,'currentTargetSha256':inp['currentTargetSha256'],'proposedTarget':target,'proposedTargetSha256':sha(target),'disposition':disp,'confidence':conf,'rationale':reason,'callerContextSummary':contexts[r],'callerRefsSourceId':inp['sourceId'],'sourcePlaceholders':source_ph,'proposedPlaceholders':reviewed_ph,'sourceMarkup':source_markup,'proposedMarkup':reviewed_markup,'protectedLiterals':protected,'proposedProtectedLiteralMismatches':missing_reviewed,'nativeSpeakerApproval':'outstanding'})
 structural.append({'selectionRank':r,'sourceOrdinal':None,'sourceId':inp['sourceId'],'locale':loc,'currentTargetSha256':inp['currentTargetSha256'],'reviewedTargetSha256':sha(target),'disposition':disp,'sourcePlaceholders':source_ph,'currentTargetPlaceholders':cur_ph,'reviewedTargetPlaceholders':reviewed_ph,'currentPlaceholderParity':'exact','reviewedPlaceholderParity':'exact','sourceMarkup':source_markup,'currentTargetMarkup':cur_markup,'reviewedTargetMarkup':reviewed_markup,'currentMarkupParity':'exact','reviewedMarkupParity':'exact','protectedLiterals':protected,'currentProtectedLiteralMismatches':missing_cur,'reviewedProtectedLiteralMismatches':missing_reviewed})
assert len(reviews)==300 and len(proposals)==len(C)
assert sum(x['localizedProductionDisplayReferenceCount']>0 for x in calls)==25
assert not gaps
# Preserve an exact current W44 apply-readback reattestation, tying prior window selection to W45 exclusion.
W44=Path('/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn/docs/pr-evidence/pr409-localization-2026-11-02/window44-reconstructed-ranks1-25')
w44rows=jl(W44/'application/apply-readback.jsonl'); assert len(w44rows)==300
w44check=[]
for x in w44rows:
 loc=x['locale']; src=x['source']; cat=git('show',f'{HEAD}:src/web/public/locales/{loc}.json'); obj=json.loads(cat); val=obj[src]
 assert val==x['finalTarget'] and sha(val)==x['finalTargetSha256']==x['readbackTargetSha256']
 w44check.append({'selectionRank':x['selectionRank'],'sourceId':x['sourceId'],'sourceSha256':x['sourceSha256'],'locale':loc,'catalogBlobOid':git('rev-parse',f'{HEAD}:src/web/public/locales/{loc}.json').decode().strip(),'currentTargetSha256':sha(val),'priorFinalTargetSha256':x['finalTargetSha256'],'priorReadbackTargetSha256':x['readbackTargetSha256'],'currentValueMatchesPriorW44Readback':True})
# Verify all 25 callers: direct or helper-linked production localization evidence is present.
for x in calls:
 assert x['localizedProductionDisplayReferenceCount']>0,x['selectionRank']
# Read-only integrity outputs.
dumpjl(OUT/'caller-context.jsonl',calls)
dumpjl(OUT/'caller-source-hits.jsonl',[ref for x in calls for ref in x['callerRefs']])
dumpjl(OUT/'review-decisions.jsonl',reviews)
dumpjl(OUT/'candidate-proposals.jsonl',proposals)
dumpjl(OUT/'structural-validation.jsonl',structural)
dumpjl(OUT/'spanish-formal-applicability.jsonl',applicability)
dumpjl(OUT/'prior-window-input-reattestation.jsonl',w44check)
dumpjl(OUT/'source-runtime-gaps.jsonl',gaps)
dumpj(OUT/'review-summary.json',{'exactHead':HEAD,'exactTree':TREE,'windowLabel':'W45 reconstructed source-ID ranks 1-25; no historical ordinal established','cellCount':len(reviews),'sourceCount':25,'localeCount':12,'dispositionCounts':dict(sorted(counts.items())),'proposalCount':len(proposals),'callerRowsWithProductionLocalizedDisplay':sum(x['localizedProductionDisplayReferenceCount']>0 for x in calls),'callerGapSourceCount':len(gaps),'currentPlaceholderMismatches':sum(x['currentPlaceholderParity']!='exact' for x in structural),'reviewedPlaceholderMismatches':sum(x['reviewedPlaceholderParity']!='exact' for x in structural),'currentMarkupMismatches':sum(x['currentMarkupParity']!='exact' for x in structural),'reviewedMarkupMismatches':sum(x['reviewedMarkupParity']!='exact' for x in structural),'currentProtectedLiteralMismatchCellCount':sum(bool(x['currentProtectedLiteralMismatches']) for x in reviews),'reviewedProtectedLiteralMismatchCellCount':sum(bool(x['reviewedProtectedLiteralMismatches']) for x in reviews),'w44ApplyReadbacksReattested':len(w44check),'nativeSpeakerApproval':'outstanding','browserReview':'not performed','testsBuildScansCi':'not run','repositoryMutation':'none'})
print(json.dumps({'rows':len(reviews),'proposals':len(proposals),'proposalCounts':dict(Counter(x['disposition'] for x in proposals)),'dispositionCounts':dict(counts),'callerRows':len(calls),'callerReferences':sum(x['callerReferenceCount'] for x in calls),'callerGaps':len(gaps),'w44Readbacks':len(w44check)},ensure_ascii=False,indent=2))
