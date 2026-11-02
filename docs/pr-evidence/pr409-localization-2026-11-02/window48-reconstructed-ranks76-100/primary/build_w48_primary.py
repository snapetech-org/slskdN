#!/usr/bin/env python3
"""Build a pinned, scratch-only primary review packet for slskdN PR #409 W48."""
import collections, hashlib, json, re, subprocess
from pathlib import Path

REPO=Path('/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn')
OUT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window48-primary-20261102')
W47=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window47-primary-20261102')
EVIDENCE=REPO/'docs/pr-evidence/pr409-localization-2026-11-02'
HEAD='0a6cbdcb606de1888045df358427eb2b81c85546'
TREE='dcef8f70ea7c10926058c5db7430611b5faa07db'
PR='https://github.com/snapetech-org/slskdN/pull/409'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
CATALOGS=[f'src/web/public/locales/{l}.json' for l in LOCALES]
RICH_ID='src_9f923ae09ae2aeb7'
RICH_SOURCE='Security monitoring will begin automatically once peer activity is detected. Check connectivity in the {tab} tab.'

TRANSLATIONS={
'Show the previous page of incoming shares.':{
'ar':'عرض الصفحة السابقة للعناصر التي تمت مشاركتها معي.','de':'Vorherige Seite der mit mir geteilten Inhalte anzeigen.','es':'Mostrar la página anterior de los elementos compartidos conmigo.','fr':'Afficher la page précédente des éléments partagés avec moi.','hi':'मेरे साथ साझा की गई सामग्री का पिछला पृष्ठ दिखाएँ।','id':'Tampilkan halaman sebelumnya untuk item yang dibagikan kepada saya.','ja':'自分と共有された項目の前のページを表示します。','ko':'나와 공유된 항목의 이전 페이지를 표시합니다.','pt-BR':'Mostrar a página anterior dos itens compartilhados comigo.','vi':'Hiển thị trang trước của các mục được chia sẻ với tôi.','zh-Hans':'显示与我共享内容的上一页。','zh-Hant':'顯示與我分享內容的上一頁。'},
'Could not load saved pod channels: {message}':{
'ar':'تعذّر تحميل قنوات Pod المحفوظة: {message}','es':'No se pudieron cargar los canales de Pod guardados: {message}','fr':'Impossible de charger les chaînes Pod enregistrées : {message}','hi':'सहेजे गए Pod चैनल लोड नहीं हो सके: {message}','id':'Tidak dapat memuat saluran Pod yang tersimpan: {message}','ja':'保存済みのPodチャンネルを読み込めませんでした: {message}','ko':'저장된 Pod 채널을 불러오지 못했습니다: {message}','pt-BR':'Não foi possível carregar os canais de Pod salvos: {message}','vi':'Không thể tải các kênh Pod đã lưu: {message}'},
'Phonetic Similarity:':{'ja':'発音の類似度:','ko':'발음 유사도:','zh-Hans':'发音相似度：','zh-Hant':'發音相似度：'},
'Show transfers in every status.':{'vi':'Hiển thị các lượt truyền ở mọi trạng thái.'},
'Freshness Valid:':{'es':'Frescura válida:','ko':'신선도 유효성:'},
'Auto-replace enabled. Backend will check for stuck downloads periodically.':{'vi':'Đã bật tính năng tự động thay thế. Dịch vụ nền sẽ định kỳ kiểm tra các lượt tải xuống bị kẹt.'},
'Tag and Organization Preview':{
'ar':'معاينة الوسوم وتنظيم الملفات','de':'Vorschau für Tags und Dateiorganisierung','es':'Vista previa del etiquetado y la organización de archivos','fr':'Aperçu du balisage et de l’organisation des fichiers','hi':'टैग और फ़ाइल संगठन का पूर्वावलोकन','id':'Pratinjau penandaan dan penataan file','ja':'タグ付けとファイル整理のプレビュー','ko':'태그 및 파일 정리 미리보기','pt-BR':'Prévia de tags e organização de arquivos','vi':'Xem trước việc gắn thẻ và sắp xếp tệp','zh-Hans':'标签与文件整理预览','zh-Hant':'標籤與檔案整理預覽'},
'Webhook target URL':{
'ar':'عنوان URL المستهدف لخطاف الويب','de':'Ziel-URL des Webhooks','es':'URL de destino del webhook','fr':'URL cible du webhook','hi':'वेबहुक का लक्ष्य URL','id':'URL tujuan webhook','pt-BR':'URL de destino do webhook','vi':'URL đích của webhook'},
'ALL DISABLED BY DEFAULT':{'de':'STANDARDMÄSSIG ALLES DEAKTIVIERT'},
'Copy a safe-fix manifest for selected Library Health issues':{
'es':'Copie un manifiesto de correcciones seguras para los problemas seleccionados de Salud de la biblioteca','fr':'Copiez un manifeste de correctifs sûrs pour les problèmes sélectionnés de Santé des bibliothèques','pt-BR':'Copie um manifesto de correções seguras para os problemas selecionados de Saúde da Biblioteca'},
'Review accepted realm index disagreements with provenance before trusting a realm authority.':{
'ar':'راجع الخلافات المقبولة في فهرس موضوعات النطاق مع بيانات المصدر قبل الوثوق بجهة معتمدة للنطاق.','de':'Prüfen Sie akzeptierte Abweichungen im Realm-Themenindex samt Provenienz, bevor Sie einer Realm-Autorität vertrauen.','es':'Revise las discrepancias aceptadas en el índice de materias del dominio y su procedencia antes de confiar en una autoridad del dominio.','fr':'Examinez les divergences acceptées dans l’index de sujets du domaine avec leurs données de provenance avant de faire confiance à une autorité du domaine.','hi':'किसी क्षेत्र प्राधिकारी पर भरोसा करने से पहले, क्षेत्र विषय सूचकांक में स्वीकार किए गए मतभेदों की स्रोत जानकारी सहित समीक्षा करें।','id':'Tinjau perbedaan yang diterima di indeks subjek ranah beserta asal-usulnya sebelum mempercayai otoritas ranah.','ja':'レルム権威を信頼する前に、レルムのサブジェクトインデックスで受け入れられた不一致を、その出所情報とともに確認してください。','ko':'영역 권한을 신뢰하기 전에, 출처 정보와 함께 영역 주제 인덱스에서 승인된 불일치를 검토하세요.','pt-BR':'Revise as divergências aceitas no índice de assuntos do domínio com suas informações de procedência antes de confiar em uma autoridade do domínio.','vi':'Hãy xem xét các bất đồng đã được chấp nhận trong chỉ mục chủ đề của miền cùng thông tin nguồn gốc trước khi tin cậy cơ quan có thẩm quyền của miền.','zh-Hans':'在信任领域权威之前，请结合来源信息，审查领域主题索引中已接受的分歧。','zh-Hant':'在信任領域權威之前，請連同來源資訊一起檢視領域主題索引中已接受的歧異。'},
'Signed release-completeness observations without file paths.':{'es':'Observaciones firmadas sobre la integridad del lanzamiento, sin rutas de archivo.','fr':'Observations signées sur l’exhaustivité de la sortie, sans chemins de fichiers.','pt-BR':'Observações assinadas sobre a completude do lançamento, sem caminhos de arquivo.'},
}
HOLDS={('Quarantine Jury updated',l):'The exact source term is marked protected in earlier review evidence. Window 14 retained localized forms in this locale only as an unresolved exception; preserve the current value and hold until the protected-name policy is resolved.' for l in ['ja','ko','zh-Hans','zh-Hant']}
RATIONALES={
'Show the previous page of incoming shares.':('The caller paginates the “Shared with Me” view. In this context, “shares” are items shared with the user, not stock or financial shares. The proposed wording names the shared content directly.','high'),
'Could not load saved pod channels: {message}':('MessagingV2 loads channels attached to the registered Pod entity. The project catalog maps the product name “Pod” unchanged in all locales; this proposal aligns the wording with that term and keeps {message} exactly once.','high'),
'Phonetic Similarity:':('MediaCore displays this value beside text similarity as a percentage computed from phonetic similarity. Use pronunciation similarity in the affected locale rather than acoustic or speech similarity.','high'),
'Show transfers in every status.':('The transfer manager filters file transfers. In Vietnamese, the current “giao dịch” can mean a transaction; “lượt truyền” names data transfers.','high'),
'Freshness Valid:':('This is a Boolean descriptor-verification label. Spanish requires feminine agreement with “frescura”; the Korean proposal uses a validity noun for the field label.','high'),
'Auto-replace enabled. Backend will check for stuck downloads periodically.':('The transfer-manager toast says the backend checks stalled downloads. The current Vietnamese “Phần cuối” reads as “the final part”; the proposal uses the project’s established “Dịch vụ nền” term for Backend.','high'),
'Tag and Organization Preview':('The caller places this heading over a dry run of tag, cover-art, ReplayGain, and path decisions. Here “organization” means organizing files, not organizations. The proposed wording makes that scope explicit.','high'),
'Webhook target URL':('This is the accessible name of the Webhook destination field. The current wording is literal or grammatically awkward in several locales; the proposal expresses a target/destination URL and keeps URL intact.','high'),
'ALL DISABLED BY DEFAULT':('German all-caps text must render ß as SS; the current uppercase string contains lowercase ß in STANDARDMÄßIG.','high'),
'Copy a safe-fix manifest for selected Library Health issues':('The caller is the safe-fix manifest button in Library Health. The localized catalog entry for “Library Health” is available in each locale; the proposal reuses that term instead of leaving the English feature name in Spanish, French, and Brazilian Portuguese.','moderate'),
'Review accepted realm index disagreements with provenance before trusting a realm authority.':('The caller is the subtitle for Realm Subject Index Conflicts. The proposal makes “accepted” modify the disagreements, keeps provenance attached to those conflicts, and uses the established localized term for Realm.','moderate'),
'Signed release-completeness observations without file paths.':('This is an outbound Mesh evidence type with id releaseCompleteness. The app context is content releases; Spanish, French, and Brazilian Portuguese currently use “version”/“versão,” which can read as software version. “Lanzamiento/sortie” expresses a content release.','moderate')}
GENERIC={
'Publish Opinion':'The MediaCore control publishes a user opinion for a Pod/content ID; the existing target is a clear action label.',
'Close another room before opening listen-along here.':'The room hook emits this fixed message when the listener already occupies the maximum number of observed rooms; the existing target preserves the instruction and sequence.',
'Quarantine Jury updated':'This is the informational header shown after the Quarantine Jury view updates; the existing localized form is retained where earlier evidence did not flag the protected-name conflict.',
'Wave alpha':'This labels the wave_a visualizer parameter; the existing target conveys wave alpha in the parameter context.',
'Swarm Download Status':'This is the heading for swarm download metrics; the existing target preserves the download-status meaning.',
'Speed unavailable':'This tooltip appears when upload speed is not available on the user card; the existing target is concise and accurate.',
'Skipped':'This status is used for skipped playlist-intake items and metadata-processing stages; the existing target works as a compact status label.',
'Mesh network speed':'This footer tooltip identifies the Mesh network-speed value; the existing target matches the localized Mesh term and speed context.',
'Filter wishlist...':'This is a search placeholder for filtering the Wishlist view; the existing target is an appropriate short prompt.',
'Load Full Dashboard':'This button loads the full MediaCore metrics dashboard; the existing target is a clear action label.',
'The request failed. Try again.':'This is a shared API error fallback used across several feature surfaces; the existing target preserves the retry instruction.',
'Some transfers could not be updated. Try again.':'The transfer manager displays this error after an update request fails for some transfers; the existing target preserves scope and retry instruction.',
'Copy a safe-fix manifest for selected Library Health issues':'The caller is the safe-fix manifest button in Library Health; the existing target conveys copying a manifest for selected issues.',
'Create wishlist searches from the parsed CSV rows using the selected options.':'This tooltip describes the CSV import action; the existing target preserves parsed rows, Wishlist searches, and selected options.',
'Signed release-completeness observations without file paths.':'This describes one outbound Mesh evidence type; the current target preserves signed observations, release completeness, and the omission of file paths.'}

def sha(b): return hashlib.sha256(b).hexdigest()
def sid(s): return 'src_'+sha(s.encode())[:16]
def blob_sha(b):
    return subprocess.check_output(['git','-C',str(REPO),'hash-object','--stdin'],input=b).decode().strip()
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args])
def rj(p): return json.loads(p.read_text(encoding='utf-8'))
def rjl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def wj(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def wjl(p,rows):
    with p.open('w',encoding='utf-8',newline='\n') as f:
        for x in rows:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
def verify_sums(d,filename):
    rows=[]
    for line in (d/filename).read_text().splitlines():
        if not line.strip():continue
        h,n=line.split(None,1);n=n.strip().lstrip('*');actual=sha((d/n).read_bytes())
        rows.append({'path':n,'expectedSha256':h,'actualSha256':actual,'matches':h==actual})
    return rows
def ph(s):return collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s))
def tags(s):return collections.Counter(re.findall(r'<\/?[A-Za-z][^>]*>',s))
def hits(source):
    pat=re.compile(r'(?<![A-Za-z0-9_$])(["\'])'+re.escape(source)+r'\1');found=[]
    for p in (REPO/'src/web/src').rglob('*'):
        if p.suffix not in {'.js','.jsx','.ts','.tsx'} or p.name.endswith('.test'+p.suffix) or '.test.' in p.name or '__tests__' in p.parts:continue
        try:lines=p.read_text(encoding='utf-8').splitlines()
        except (UnicodeDecodeError,OSError):continue
        for n,line in enumerate(lines,1):
            if not pat.search(line):continue
            rel=str(p.relative_to(REPO));data=git('show',f'{HEAD}:{rel}');assert data==p.read_bytes(),rel
            found.append({'path':rel,'line':n,'lineText':line,'lineSha256':sha(line.encode()),'fileBytes':len(data),'fileSha256':sha(data),'gitBlob':git('rev-parse',f'{HEAD}:{rel}').decode().strip(),'gitBlobSha1Check':blob_sha(data),'context':[{'line':i+1,'text':lines[i]} for i in range(max(0,n-3),min(len(lines),n+2))]})
    return sorted({(x['path'],x['line']):x for x in found}.values(),key=lambda x:(x['path'],x['line']))

assert OUT.exists() and {x.name for x in OUT.iterdir()}=={'build_w48_primary.py'},list(OUT.iterdir())
assert git('rev-parse','HEAD').decode().strip()==HEAD and git('rev-parse','HEAD^{tree}').decode().strip()==TREE
assert not git('status','--porcelain=v1').decode().strip()
pr=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','headRefOid,isDraft,state,url']))
remote=json.loads(subprocess.check_output(['gh','api',f'repos/snapetech-org/slskdN/git/commits/{HEAD}']))
assert pr['state']=='OPEN' and pr['isDraft'] and pr['headRefOid']==HEAD and remote['tree']['sha']==TREE

w47sum=verify_sums(W47,'SHA256SUMS.txt');assert len(w47sum)==20 and all(x['matches'] for x in w47sum),w47sum
w47sumry=rj(W47/'review-summary.json');assert w47sumry['exactHead']=='cb6739864b3651d72412b6aeb4590537cbf23d4e' and w47sumry['exactTree']=='a0946207555e494a558707008ba051013964b447'
prior=rjl(W47/'prior-source-ids.jsonl');w46=rjl(W47/'w46-selected-ids.jsonl');w46f=rjl(W47/'w46-followup-source-ids.jsonl');w47=rjl(W47/'source-selection.jsonl')
assert (len(prior),len(w46),len(w46f),len(w47))==(1122,25,5,25)
excluded=[]
for label,rows in [('W1-W45 evidence set',prior),('W46 reconstructed ranks 26-50',w46),('W46 caller-aware follow-up',w46f),('W47 reconstructed ranks 51-75',w47)]:
    for x in rows:excluded.append({'sourceId':x['sourceId'],'source':x.get('source',x.get('sourceText')),'sourceSha256':x['sourceSha256'],'origin':label})
excluded.append({'sourceId':RICH_ID,'source':RICH_SOURCE,'sourceSha256':sha(RICH_SOURCE.encode()),'origin':'W47 W71 rich-text source/caller follow-up'})
excluded_ids=[x['sourceId'] for x in excluded];assert len(excluded_ids)==1178 and len(set(excluded_ids))==1178

catalogs={};catrows=[];keyorder=None
for locale,path in zip(LOCALES,CATALOGS):
    data=git('show',f'{HEAD}:{path}');assert data==(REPO/path).read_bytes(),path
    c=json.loads(data.decode());keys=list(c)
    if keyorder is None:keyorder=keys
    else:assert keys==keyorder,path
    assert len(keys)==6176 and all(isinstance(v,str) and v for v in c.values()),path
    catalogs[locale]=c;catrows.append({'locale':locale,'path':path,'bytes':len(data),'sha256':sha(data),'gitBlob':git('rev-parse',f'{HEAD}:{path}').decode().strip(),'gitBlobSha1Check':blob_sha(data),'entryCount':len(keys),'nonemptyValueCount':sum(bool(v) for v in c.values())})
keyorder_sha=sha(('\n'.join(keyorder)+'\n').encode());source_by_id={sid(s):s for s in keyorder};assert len(source_by_id)==6176
assert all(x in source_by_id for x in excluded_ids),[x for x in excluded_ids if x not in source_by_id]
exset=set(excluded_ids);pending=sorted(set(source_by_id)-exset);assert len(pending)==4998
selected_ids=pending[:25];selected=[source_by_id[x] for x in selected_ids]
assert selected[0]=='Publish Opinion' and selected[-1]=='Signed release-completeness observations without file paths.' and source_by_id[pending[25]]=='On'

rich=rj(EVIDENCE/'window47-rich-text-followup/root-adjudication-and-readback.json');rich_checks=[]
for locale in LOCALES:
    expected=rich['targets'][locale];actual=catalogs[locale].get(RICH_SOURCE)
    rich_checks.append({'locale':locale,'sourceId':RICH_ID,'targetSha256':sha(actual.encode()) if actual else None,'matchesW47Readback':actual==expected['target'] and sha(actual.encode())==expected['targetSha256']})
assert all(x['matchesW47Readback'] for x in rich_checks)
runtime=rj(EVIDENCE/'window47-runtime-followup/catalog-key-readback.json');runtime_checks=[]
for locale in LOCALES:
    for source in runtime['sources']:
        actual=catalogs[locale].get(source);expect=runtime['coverage'][locale][source]
        runtime_checks.append({'locale':locale,'sourceId':sid(source),'source':source,'targetSha256':sha(actual.encode()) if actual else None,'matchesW47RuntimeReadback':actual==expect['target'] and sha(actual.encode())==expect['targetSha256']})
assert len(runtime_checks)==84 and all(x['matchesW47RuntimeReadback'] for x in runtime_checks)

excluded_origins=collections.defaultdict(list)
for x in excluded:excluded_origins[x['sourceId']].append(x['origin'])
pending_index={x:i+1 for i,x in enumerate(pending)}
inventory=[]
for source_id,source in sorted(source_by_id.items()):
    qrank=pending_index.get(source_id)
    inventory.append({'sourceId':source_id,'source':source,'sourceSha256':sha(source.encode()),'excluded':source_id in exset,'exclusionOrigins':excluded_origins.get(source_id,[]),'remainingQueueRank':qrank,'continuationRank':75+qrank if qrank else None,'inW48':source_id in selected_ids,'localeCoverage':sum(source in catalogs[l] for l in LOCALES)})
assert len(inventory)==6176 and all(x['localeCoverage']==12 for x in inventory)

callers=[];caller_by_id={}
for rank,source in enumerate(selected,76):
    refs=hits(source);caller_by_id[sid(source)]=refs
    callers.append({'windowRank':rank,'remainingQueueRank':rank-75,'sourceId':sid(source),'source':source,'sourceSha256':sha(source.encode()),'productionCallerCount':len(refs),'callers':refs,'callerContextAssessment':GENERIC.get(source,'Production references pinned at the exact selected PR head.')})

cellrows=[];decisions=[]
for rank,source in enumerate(selected,76):
    source_id=sid(source);why,confidence=RATIONALES.get(source,(GENERIC.get(source,'The exact caller context supports the current target; no material defect was identified.'),'moderate'))
    for locale in LOCALES:
        current=catalogs[locale][source];current_hash=sha(current.encode());held=HOLDS.get((source,locale));proposal=TRANSLATIONS.get(source,{}).get(locale)
        if held:disp='hold';final=None;reason=held;conf='low'
        elif proposal is not None and proposal!=current:disp='propose-correction';final=proposal;reason=why;conf=confidence
        else:disp='accept-current';final=current;reason=GENERIC.get(source,'The existing localized target preserves the source meaning in its exact caller context; no material defect was identified.');conf='moderate'
        source_ph=ph(source);cur_ph=ph(current);final_ph=ph(final) if final is not None else None
        source_tags=tags(source);cur_tags=tags(current);final_tags=tags(final) if final is not None else None
        ph_ok=source_ph==cur_ph and (final_ph==source_ph if final is not None else True)
        tag_ok=source_tags==cur_tags and (final_tags==source_tags if final is not None else True)
        protected=[]
        for token in ['CSV','URL']:
            if re.search(r'(?<![A-Za-z0-9])'+re.escape(token)+r'(?![A-Za-z0-9])',source):protected.append({'literal':token,'policy':'exact case-sensitive technical literal','currentPreserved':token in current,'finalPreserved':token in final if final is not None else None})
        if source=='Could not load saved pod channels: {message}':protected.append({'literal':'Pod','policy':'registered product/entity term; source is lowercase pod but caller is a Pod channel reader','currentPreserved':'Pod' in current,'finalPreserved':'Pod' in final if final is not None else None})
        if source=='Quarantine Jury updated':protected.append({'literal':'Quarantine Jury','policy':'prior W14 per-locale localized keep in eight locales; unresolved protected-name conflict in ja/ko/zh-Hans/zh-Hant','currentPreserved':'Quarantine Jury' in current,'finalPreserved':'Quarantine Jury' in final if final is not None else None})
        if source=='Review accepted realm index disagreements with provenance before trusting a realm authority.':
            term=catalogs[locale].get('Realm');protected.append({'literal':'realm','policy':'localized terminology matches standalone Realm key','localizedTerm':term,'finalContainsLocalizedTerm':term.casefold() in final.casefold() if final is not None and term else None})
        if source=='Copy a safe-fix manifest for selected Library Health issues':
            term=catalogs[locale].get('Library Health');protected.append({'literal':'Library Health','policy':'localized feature-name consistency matches standalone Library Health key','localizedTerm':term,'finalContainsLocalizedTerm':term.casefold() in final.casefold() if final is not None and term else None})
        assert ph_ok and tag_ok,(source_id,locale,ph_ok,tag_ok)
        if final is not None:
            for p in protected:
                if p['literal'] in {'CSV','URL','Pod'}:assert p['finalPreserved'],(source_id,locale,p)
        row={'repository':'snapetech-org/slskdN','pullRequest':409,'exactHead':HEAD,'exactTree':TREE,'window':'W48 reconstructed pending stable-ID ranks 76-100; historical source ordinal unavailable','windowRank':rank,'remainingQueueRank':rank-75,'sourceId':source_id,'source':source,'sourceSha256':sha(source.encode()),'locale':locale,'catalogPath':f'src/web/public/locales/{locale}.json','catalogFileSha256':catrows[LOCALES.index(locale)]['sha256'],'currentTarget':current,'currentTargetSha256':current_hash,'primaryDisposition':disp,'proposedTarget':final if disp=='propose-correction' else None,'proposedTargetSha256':sha(final.encode()) if disp=='propose-correction' else None,'finalReviewedTarget':final,'finalReviewedTargetSha256':sha(final.encode()) if final is not None else None,'rationale':reason,'semanticConfidence':conf,'localeQualityConfidence':'moderate machine-assisted; native-speaker review outstanding','nativeSpeakerApproval':False,'callerReferenceCount':len(caller_by_id[source_id]),'callerPathsLines':[{'path':x['path'],'line':x['line'],'lineSha256':x['lineSha256'],'fileSha256':x['fileSha256'],'gitBlob':x['gitBlob']} for x in caller_by_id[source_id]],'sourcePlaceholders':dict(source_ph),'currentTargetPlaceholders':dict(cur_ph),'finalTargetPlaceholders':dict(final_ph) if final_ph is not None else None,'placeholderParity':ph_ok,'sourceMarkup':dict(source_tags),'currentTargetMarkup':dict(cur_tags),'finalTargetMarkup':dict(final_tags) if final_tags is not None else None,'markupParity':tag_ok,'protectedLiteralChecks':protected}
        decisions.append(row);cellrows.append({k:row[k] for k in ['windowRank','remainingQueueRank','sourceId','source','sourceSha256','locale','catalogPath','catalogFileSha256','currentTarget','currentTargetSha256']})
assert len(cellrows)==300 and len(decisions)==300
counts=collections.Counter(x['primaryDisposition'] for x in decisions)
assert all(x['callerReferenceCount']>0 for x in decisions),[x['sourceId'] for x in decisions if x['callerReferenceCount']==0]

prev=sorted(w47,key=lambda x:x['selectionRank'])[-1]
boundary=[{'continuationRank':75,'role':'previous-window-last','sourceId':prev['sourceId'],'source':prev['source'],'sourceSha256':prev['sourceSha256'],'origin':'W47 selection evidence'}]
for rank,source in enumerate(selected,76):boundary.append({'continuationRank':rank,'role':'selected-W48','sourceId':sid(source),'source':source,'sourceSha256':sha(source.encode()),'remainingQueueRank':rank-75})
nextrow={'sourceId':pending[25],'source':source_by_id[pending[25]],'sourceSha256':sha(source_by_id[pending[25]].encode())}
boundary.append({'continuationRank':101,'role':'next-unselected-boundary',**nextrow,'remainingQueueRank':26})
selection={'repository':'snapetech-org/slskdN','pullRequest':409,'pullRequestUrl':PR,'pullRequestState':pr['state'],'pullRequestIsDraft':pr['isDraft'],'exactHead':HEAD,'exactTree':TREE,'headVerifiedAgainstLiveGitHub':True,'worktreeClean':True,'catalogs':catrows,'orderedCatalogKeyCount':6176,'orderedCatalogKeySha256':keyorder_sha,'exclusionCounts':{'W1-W45 evidence IDs':len(prior),'W46 reconstructed manual IDs':len(w46),'W46 count-aware follow-up IDs':len(w46f),'W47 primary IDs':len(w47),'W47 W71 rich-text follow-up ID':1,'uniqueTotal':len(exset)},'excludedStableIdCount':len(exset),'pendingStableIdCount':len(pending),'windowLabel':'W48 reconstructed pending stable-ID ranks 76-100; historical source ordinal unavailable','selectionRankRange':[76,100],'remainingQueueRankRange':[1,25],'nextUnselectedRemainingQueueRank':26,'sourceOrdinalRange':None,'selectedSourceCount':25,'localeCount':12,'cellCount':300,'exclusionSourceIdsFile':'prior-excluded-source-ids.jsonl','w47PrimaryChecksumsVerified':len(w47sum),'w47PrimaryChecksumFailures':0,'w47RichTextReattestationCells':len(rich_checks),'w47RichTextReattestationFailures':0,'w47RuntimeCatalogReattestationCells':len(runtime_checks),'w47RuntimeCatalogReattestationFailures':0,'runtimeFollowupPolicy':'W47 W54/W57 runtime follow-up reattests seven catalog values but is not treated as semantic translation review for pending IDs. The W71 combined rich-text source was separately translated/reviewed and is excluded.','boundaryEvidence':{'previousRank75':boundary[0],'firstRank76':boundary[1],'lastRank100':boundary[-2],'nextRank101':boundary[-1]},'primaryDispositionCounts':dict(counts),'placeholderMismatches':0,'markupMismatches':0,'nativeSpeakerApproval':False,'headedBrowserReview':False,'testsBuildScansCiRun':False,'repositoryModified':False,'remoteMutation':False}

wjl(OUT/'catalog-structure.jsonl',catrows);wjl(OUT/'prior-excluded-source-ids.jsonl',excluded);wjl(OUT/'source-inventory.jsonl',inventory);wjl(OUT/'selection-boundary.jsonl',boundary);wjl(OUT/'caller-context.jsonl',callers);wjl(OUT/'source-current-cells.jsonl',cellrows);wjl(OUT/'review-decisions.jsonl',decisions)
wj(OUT/'selection-and-boundary.json',selection)
wj(OUT/'w47-runtime-followup-reattestation.json',{'runtimeCatalogCells':runtime_checks,'richTextSourceCells':rich_checks,'w47PrimaryChecksumEntries':w47sum,'failures':0})
wj(OUT/'review-summary.json',{'exactHead':HEAD,'exactTree':TREE,'window':'W48 reconstructed pending stable-ID ranks 76-100; historical source ordinal unavailable','sourceCount':25,'localeCount':12,'cellCount':300,'dispositionCounts':dict(counts),'proposalSourceIds':sorted({x['sourceId'] for x in decisions if x['primaryDisposition']=='propose-correction'}),'heldSourceIds':sorted({x['sourceId'] for x in decisions if x['primaryDisposition']=='hold'}),'placeholderMismatches':0,'markupMismatches':0,'protectedPodPreserved':True,'protectedCsvUrlPreserved':True,'nativeSpeakerApproval':False,'semanticConfidence':'moderate machine-assisted primary review','localeQualityConfidence':'moderate machine-assisted; native-speaker review outstanding','headedBrowserReview':False,'testsBuildScansCiRun':False,'remoteMutation':False,'repositoryModified':False})
runtime_pending=[]
for source in runtime['sources']:
    source_id=sid(source);qrank=pending_index.get(source_id)
    runtime_pending.append({'sourceId':source_id,'source':source,'alreadyInPriorEvidence':source_id in exset,'remainingQueueRank':qrank,'continuationRank':75+qrank if qrank else None,'inW48':source_id in selected_ids,'note':'Runtime display fix/catalog readback is not treated as an independent semantic translation disposition unless the source is covered by prior window evidence.'})
wj(OUT/'runtime-followup-boundary.json',{'evidencePath':str(EVIDENCE/'window47-runtime-followup/catalog-key-readback.json'),'sourceCount':len(runtime_pending),'sources':runtime_pending,'richTextSourceIdExcluded':RICH_ID,'richTextSourceSha256':sha(RICH_SOURCE.encode()),'rationale':'Avoid treating runtime caller review as translation review for otherwise pending source keys.'})
readme=f'''# slskdN PR #409 W48 primary populated-catalog review

## Pin and lane

- Live PR: {PR} (OPEN, draft), head `{HEAD}`, tree `{TREE}`. GitHub API, local checkout, and clean worktree agree.
- The twelve direct locale catalogs have identical ordered key sets and contain 6,176 populated keys. Their file hashes and Git blob IDs are in `catalog-structure.jsonl`.
- W48 is the next deterministic reconstructed pending stable-ID lane after excluding the exact 1,122 W1-W45 evidence IDs, 25 W46 manual IDs, five W46 count-aware follow-up IDs, 25 W47 primary IDs, and the separately reviewed W71 rich-text source. These are 1,178 unique current source IDs, leaving 4,998 pending IDs. W48 takes continuation ranks 76-100, the first 25 remaining IDs. `selection-boundary.jsonl` records rank 75, ranks 76-100, and rank 101. No historical source ordinal is claimed.
- The W47 W54/W57 runtime follow-up reattests seven catalog values but does not add semantic dispositions for otherwise pending source IDs. `runtime-followup-boundary.json` records their positions; “Close another room before opening listen-along here.” is rank 77.

## Review packet

- 25 sources × 12 locales = 300 cells in `source-current-cells.jsonl` and `review-decisions.jsonl`.
- Exact source hashes, current target hashes, caller line/file hashes and Git blobs, line contexts, placeholder inventories, markup inventories, protected-term handling, primary dispositions, and target hashes are recorded per cell or source.
- Disposition counts: {', '.join(f'{k} {v}' for k,v in sorted(counts.items()))}. This is machine-assisted review; no native-speaker approval or headed-browser review is claimed.
- “Quarantine Jury updated” is held in ja, ko, zh-Hans, and zh-Hant based on unresolved prior protected-name evidence. The other locales reuse the prior per-locale keep decision.

## Limitations and side effects

Native-speaker review remains outstanding. No repository/catalog changes, tests, builds, scans, CI jobs, browser work, PR edits, commits, or pushes were performed. The packet is task-scoped scratch output only. `build_w48_primary.py` reproduces the packet from the pinned head and prior evidence.
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')
arts=sorted(p for p in OUT.iterdir() if p.is_file() and p.name not in {'manifest.json','SHA256SUMS'})
wj(OUT/'manifest.json',{'schemaVersion':1,'repository':'snapetech-org/slskdN','pullRequest':409,'exactHead':HEAD,'exactTree':TREE,'window':'W48 reconstructed pending stable-ID ranks 76-100','artifacts':[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in arts]})
files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name!='SHA256SUMS')
with (OUT/'SHA256SUMS').open('w',encoding='utf-8',newline='\n') as f:
    for p in files:f.write(f'{sha(p.read_bytes())}  {p.name}\n')
for line in (OUT/'SHA256SUMS').read_text().splitlines():
    h,n=line.split(None,1);assert sha((OUT/n.strip()).read_bytes())==h,n
for a in rj(OUT/'manifest.json')['artifacts']:
    b=(OUT/a['path']).read_bytes();assert len(b)==a['bytes'] and sha(b)==a['sha256'],a['path']
assert not git('status','--porcelain=v1').decode().strip()
print(json.dumps({'output':str(OUT),'files':len(files)+1,'sumEntries':len(files),'manifestArtifacts':len(arts),'sources':25,'cells':len(decisions),'dispositions':dict(counts),'selectedBoundary':[selected[0],selected[-1],nextrow['source']],'repositoryClean':True},ensure_ascii=False,indent=2))
