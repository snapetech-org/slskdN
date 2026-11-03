#!/usr/bin/env python3
"""Create a pinned scratch-only primary review packet for slskdN PR #409 W49."""
import collections, hashlib, json, re, shutil, subprocess, sys
from pathlib import Path

REPO=Path('/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn')
OUT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window49-primary-20261102')
W48=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window48-primary-20261102')
HEAD='a0f97a65f75df32a196338bea7a176b23b126cc4'
TREE='a5cb30af29a947edbf76721bbc29b59e4330f970'
BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
CATALOGS=[f'src/web/public/locales/{x}.json' for x in LOCALES]
PR_URL='https://github.com/snapetech-org/slskdN/pull/409'

ON='On'
GRAPH='Persistent graph surface for wandering the neighborhood around a seed without opening a modal. Use manual seeds, canonical ids, or saved branches to keep exploration in the page flow.'
SEARCH='lackluster container -bothersome iscbr|isvbr islossless|islossy minbr:320 minfilesize:100mb maxfilesize:2gb minfilesinfolder:8 minlength:5000'
PREVIEW='Preview Playlist'
DELETE='Delete the active native playlist from this browser.'
AUTOMATIONS='Automations:'
WAIT='Wait for online'
FAKE='Fake-lossless warnings'
MESSAGE='Please enter a message JSON'
DHT='Enable DHT rendezvous. Disable this when you want no DHT peer discovery.'
NONE='none'

TRANSLATIONS={
ON:{'ar':'مفعّل','de':'Ein','es':'Activado','fr':'Activé','hi':'चालू','id':'Aktif','ja':'オン','ko':'켜짐','pt-BR':'Ativado','vi':'Bật','zh-Hans':'已启用','zh-Hant':'已啟用'},
GRAPH:{
'ar':'واجهة رسم بياني دائمة لاستكشاف الجوار حول بذرة دون فتح نافذة حوار. استخدم بذورًا يدوية أو معرّفات قياسية أو فروعًا محفوظة لمواصلة الاستكشاف ضمن الصفحة.',
'de':'Eine dauerhaft sichtbare Graphansicht zum Erkunden der Umgebung eines Seeds, ohne einen Dialog zu öffnen. Verwenden Sie manuelle Seeds, kanonische IDs oder gespeicherte Zweige, um die Erkundung im Seitenablauf fortzusetzen.',
'es':'Vista de grafo persistente para explorar el entorno de una semilla sin abrir un cuadro de diálogo. Use semillas manuales, IDs canónicos o ramas guardadas para mantener la exploración en la página.',
'fr':'Vue graphique persistante permettant d’explorer le voisinage d’une graine sans ouvrir de boîte de dialogue. Utilisez des graines manuelles, des identifiants canoniques ou des branches enregistrées pour poursuivre l’exploration sur la page.',
'hi':'मोडल विंडो खोले बिना किसी बीज के आसपास के क्षेत्र को खोजने के लिए स्थायी ग्राफ़ दृश्य। पेज के भीतर अन्वेषण जारी रखने के लिए मैन्युअल बीज, मानक ID या सहेजी गई शाखाओं का उपयोग करें।',
'id':'Tampilan graf persisten untuk menjelajahi area di sekitar seed tanpa membuka dialog. Gunakan seed manual, ID kanonis, atau cabang tersimpan agar eksplorasi tetap berlangsung di halaman.',
'ja':'モーダルを開かずにシードの周辺を探索できる常設のグラフ表示です。手動シード、正規 ID、保存済みのブランチを使って、ページ内で探索を続けられます。',
'ko':'모달 창을 열지 않고 시드 주변을 탐색할 수 있는 상시 그래프 화면입니다. 수동 시드, 정식 ID 또는 저장된 분기를 사용해 페이지 안에서 계속 탐색하세요.',
'pt-BR':'Visualização persistente do grafo para explorar a vizinhança de uma semente sem abrir uma janela modal. Use sementes manuais, IDs canônicos ou ramificações salvas para manter a exploração na página.',
'vi':'Chế độ xem biểu đồ luôn hiển thị để khám phá khu vực quanh seed mà không cần mở hộp thoại. Dùng seed thủ công, ID chuẩn hoặc nhánh đã lưu để tiếp tục khám phá trên trang.',
'zh-Hans':'常驻图谱视图，可在不打开模态窗口的情况下探索种子周围的邻域。使用手动种子、规范 ID 或已保存的分支，在当前页面中继续探索。',
'zh-Hant':'常駐圖譜檢視，可在不開啟模態視窗的情況下探索種子周圍的鄰域。使用手動種子、標準 ID 或已儲存的分支，在目前頁面中繼續探索。'},
PREVIEW:{'ko':'재생목록 미리보기'},
DELETE:{'ko':'이 브라우저에서 활성 내장 재생목록을 삭제하세요.'},
AUTOMATIONS:{'de':'Automatisierungen:','fr':'Automatisations :'},
WAIT:{'ar':'انتظر حتى يصبح المستخدم متصلاً','de':'Warten, bis der Nutzer online ist','es':'Espera hasta que el usuario esté en línea','fr':'Attendre que l’utilisateur soit en ligne','hi':'उपयोगकर्ता के ऑनलाइन होने तक प्रतीक्षा करें','id':'Tunggu sampai pengguna online','ja':'ユーザーがオンラインになるまで待つ','ko':'사용자가 온라인 상태가 될 때까지 기다리기','pt-BR':'Aguarde até que o usuário fique on-line','vi':'Chờ đến khi người dùng trực tuyến','zh-Hans':'等待用户上线','zh-Hant':'等待使用者上線'},
FAKE:{'ar':'تحذيرات بشأن الملفات المشتبه في أنها زائفة بصيغة بلا فقد','de':'Warnungen zu mutmaßlich nur vorgeblich verlustfreien Dateien','es':'Advertencias sobre archivos que parecen ser sin pérdida, pero podrían no serlo','fr':'Alertes sur les fichiers prétendument sans perte','hi':'नकली लॉसलेस फ़ाइलों के बारे में चेतावनियाँ','id':'Peringatan tentang file yang diduga lossless palsu','ja':'偽装ロスレスの疑いがあるファイルに関する警告','ko':'가짜 무손실 파일 의심 경고','pt-BR':'Avisos sobre arquivos suspeitos de não serem realmente sem perdas','vi':'Cảnh báo về các tệp bị nghi giả dạng lossless','zh-Hans':'疑似伪无损文件警告','zh-Hant':'疑似偽無損檔案警告'},
MESSAGE:{'ar':'يرجى إدخال رسالة بصيغة JSON','de':'Bitte geben Sie eine Nachricht im JSON-Format ein.','es':'Introduzca un mensaje en formato JSON.','fr':'Veuillez saisir un message au format JSON.','hi':'कृपया JSON प्रारूप में संदेश दर्ज करें।','id':'Masukkan pesan dalam format JSON.','ja':'メッセージをJSON形式で入力してください。','ko':'메시지를 JSON 형식으로 입력하세요.','pt-BR':'Insira uma mensagem no formato JSON.','vi':'Vui lòng nhập tin nhắn ở định dạng JSON.','zh-Hans':'请输入 JSON 格式的消息。','zh-Hant':'請輸入 JSON 格式的訊息。'},
DHT:{'ar':'فعّل التلاقي عبر DHT. عطّل هذا الخيار إذا كنت لا تريد اكتشاف النظراء عبر DHT.','de':'DHT-Rendezvous aktivieren. Deaktivieren Sie diese Option, wenn Sie keine Peers über DHT entdecken möchten.','es':'Activa el punto de encuentro mediante DHT. Desactívalo si no quieres descubrir pares a través de DHT.','fr':'Activez le point de rendez-vous DHT. Désactivez cette option si vous ne souhaitez pas découvrir de pairs via DHT.','hi':'DHT पीयर खोज सक्षम करें। यदि आप DHT के माध्यम से पीयर नहीं खोजना चाहते, तो इसे बंद करें।','id':'Aktifkan titik temu DHT. Nonaktifkan opsi ini jika Anda tidak ingin menemukan peer melalui DHT.','ja':'DHTランデブーを有効にします。DHTでピアを検出したくない場合は、この設定を無効にしてください。','ko':'DHT 랑데부를 활성화합니다. DHT 피어 검색을 원하지 않으면 이 설정을 끄세요.','pt-BR':'Ative o ponto de encontro via DHT. Desative esta opção se não quiser descobrir pares pela DHT.','vi':'Bật cơ chế rendezvous qua DHT. Tắt tùy chọn này nếu bạn không muốn khám phá peer bằng DHT.','zh-Hans':'启用 DHT 会合机制。如果不想通过 DHT 发现节点，请关闭此选项。','zh-Hant':'啟用 DHT 匯合機制。如果不想透過 DHT 探索節點，請關閉此選項。'},
NONE:{'ar':'لا شيء','zh-Hans':'无','zh-Hant':'無'},
}
HOLDS={SEARCH:'The placeholder is a search query example, not prose: parser-supported filters and flags must remain byte-for-byte recognizable. Current locale values translate or corrupt several tokens (for example `minfilesinfolder`, `islossless`, `islossy`), while translating the free-text sample terms could change what the example searches for. Hold the full locale set until the intended localized-example policy is clear.'}
RATIONALES={
ON:'The only rendered UI value is a Boolean inbound-enabled status; the other exact-string references are fallback values for event lists. Current targets mostly translate the preposition “on,” not the enabled state.',
GRAPH:'The caller is the introduction paragraph for a persistent in-page graph atlas. Current strings are overly literal (“graph surface,” “modal,” and “wandering”); these proposals preserve the seed/branch/ID concepts while describing a graph view and dialog in UI terms.',
PREVIEW:'The caller is a Playlist Intake button. Korean noun order is more natural as “playlist preview.”',
DELETE:'The popup describes deleting a browser-local, app-built-in MilkDrop playlist. Korean 기본 means default; 내장 conveys built-in more accurately.',
AUTOMATIONS:'This is a heading immediately followed by a loop over multiple automations. German and French should use plural headings.',
WAIT:'The caller is a transfer action for an offline remote user; its description says the system retries when they come back. The current translations can read as waiting while online or waiting in a line.',
FAKE:'The policy describes signed warnings for suspicious candidates that are falsely represented as lossless. Several current translations can read as generic false warnings or warnings without loss.',
MESSAGE:'The warning is shown when the verification message field is empty; it asks for a message in JSON format. The current word order is awkward or ambiguous in every locale.',
DHT:'The checkbox tooltip explains a DHT rendezvous feature and explicitly ties disabling it to stopping DHT peer discovery. Current translations often render rendezvous as an appointment/meeting without making the peer-discovery relationship clear.',
NONE:'This is a fallback value in metadata labels. Arabic لا أحد means “nobody,” while the two Chinese targets are incomplete without an object; the proposals express absence of a value.'}
CONFIDENCE={k:'moderate' for k in RATIONALES}


def sha(b): return hashlib.sha256(b).hexdigest()
def sid(s): return 'src_'+sha(s.encode())[:16]
def blob_sha(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args])
def wj(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def wjl(path,rows):
    with path.open('w',encoding='utf-8',newline='\n') as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
def readjl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def verify_sums(directory,filename):
    out=[]
    for line in (directory/filename).read_text().splitlines():
        if not line.strip():continue
        expected,name=line.split(None,1); name=name.strip().lstrip('*')
        actual=sha((directory/name).read_bytes())
        out.append({'path':name,'expectedSha256':expected,'actualSha256':actual,'matches':expected==actual})
    return out
def ph(s): return collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s))
def markup(s): return collections.Counter(re.findall(r'<\/?[A-Za-z][^>]*>',s))
def canonical(obj): return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def caller_refs(source):
    pattern=re.compile(r'(?<![A-Za-z0-9_$])([\"\'])'+re.escape(source)+r'\1')
    found=[]
    for p in sorted((REPO/'src/web/src').rglob('*')):
        if p.suffix not in {'.js','.jsx','.ts','.tsx'} or p.name.endswith('.test'+p.suffix) or '.test.' in p.name or '__tests__' in p.parts: continue
        try: text=p.read_text(encoding='utf-8')
        except (UnicodeDecodeError,OSError): continue
        lines=text.splitlines()
        for n,line in enumerate(lines,1):
            if not pattern.search(line):continue
            if source=='none' and not ('LocalizedText' in line and 'source=' in line): continue
            rel=str(p.relative_to(REPO)); data=git('show',f'{HEAD}:{rel}')
            assert data==p.read_bytes(),f'caller differs from exact head: {rel}'
            context=[{'line':i+1,'text':lines[i]} for i in range(max(0,n-3),min(len(lines),n+2))]
            found.append({'path':rel,'line':n,'lineText':line,'lineSha256':sha(line.encode()),'context':context,'contextSha256':sha(canonical(context)),'fileBytes':len(data),'fileSha256':sha(data),'gitBlob':git('rev-parse',f'{HEAD}:{rel}').decode().strip(),'gitBlobSha1Check':blob_sha(data)})
    return found

def check_live_pin():
    assert git('rev-parse','HEAD').decode().strip()==HEAD
    assert git('rev-parse','HEAD^{tree}').decode().strip()==TREE
    assert not git('status','--porcelain=v1').decode().strip()
    pr=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','headRefOid,headRefName,isDraft,state,url']))
    assert pr['state']=='OPEN' and pr['isDraft'] and pr['headRefOid']==HEAD and pr['headRefName']==BRANCH,pr
    remote=json.loads(subprocess.check_output(['gh','api',f'repos/snapetech-org/slskdN/git/commits/{HEAD}']))
    assert remote['tree']['sha']==TREE
    branch=subprocess.check_output(['gh','api',f'repos/snapetech-org/slskdN/branches/{BRANCH.replace("/","%2F")}','--jq','.commit.sha'],text=True).strip()
    assert branch==HEAD,branch
    lsremote=subprocess.check_output(['git','-C',str(REPO),'ls-remote','https://github.com/snapetech-org/slskdN.git',f'refs/heads/{BRANCH}'],text=True).strip()
    assert lsremote.split()[0]==HEAD,lsremote
    return {'repository':'snapetech-org/slskdN','pullRequest':409,'pullRequestUrl':PR_URL,'state':pr['state'],'isDraft':pr['isDraft'],'headRefName':BRANCH,'livePrHead':pr['headRefOid'],'remoteBranchHead':branch,'liveCommitTree':remote['tree']['sha'],'localHead':git('rev-parse','HEAD').decode().strip(),'localTree':git('rev-parse','HEAD^{tree}').decode().strip(),'worktreeClean':True,'allPinsMatch':True}

assert not OUT.exists(),f'Output already exists: {OUT}'
assert shutil.disk_usage(OUT.parent).free > 1_000_000_000
pin=check_live_pin()
assert W48.exists()
w48sum=verify_sums(W48,'SHA256SUMS'); assert len(w48sum)==14 and all(x['matches'] for x in w48sum),w48sum
w48summary=json.loads((W48/'review-summary.json').read_text())
assert w48summary['exactHead']=='0a6cbdcb606de1888045df358427eb2b81c85546' and w48summary['exactTree']=='dcef8f70ea7c10926058c5db7430611b5faa07db'
prior=readjl(W48/'prior-excluded-source-ids.jsonl')
w48inventory=readjl(W48/'source-inventory.jsonl')
w48selected=[x for x in w48inventory if x.get('inW48')]
assert len(prior)==1178 and len(w48selected)==25
assert len({x['sourceId'] for x in prior})==1178
special=[
 {'sourceId':'src_a9047a85f2fe6ce8','source':'Listen-along could not connect. Retry when the connection is available.','origin':'W54/W57 runtime-only catalog readback; reserved from primary sequence without semantic disposition'},
 {'sourceId':'src_3aed87bbbe53efdb','source':'Room access was revoked. Rejoin after your membership is restored.','origin':'W54/W57 runtime-only catalog readback; reserved from primary sequence without semantic disposition'},
]
excluded=[{'sourceId':x['sourceId'],'source':x['source'],'sourceSha256':x['sourceSha256'],'origin':x.get('origin','prior W1-W47 semantic window evidence')} for x in prior]
excluded += [{'sourceId':x['sourceId'],'source':x['source'],'sourceSha256':x['sourceSha256'],'origin':'W48 primary window continuation ranks 76-100'} for x in w48selected]
for x in special:
 assert sid(x['source'])==x['sourceId']
 x['sourceSha256']=sha(x['source'].encode()); excluded.append(x)
assert len(excluded)==1205 and len({x['sourceId'] for x in excluded})==1205

OUT.mkdir(parents=True)
locales={};catrows=[];ordered_keys=None
for locale,path in zip(LOCALES,CATALOGS):
    raw=git('show',f'{HEAD}:{path}'); assert raw==(REPO/path).read_bytes(),path
    obj=json.loads(raw.decode()); keys=list(obj)
    if ordered_keys is None: ordered_keys=keys
    else: assert keys==ordered_keys,path
    assert len(keys)==6176 and all(isinstance(v,str) and v for v in obj.values()),path
    locales[locale]=obj
    catrows.append({'locale':locale,'path':path,'bytes':len(raw),'sha256':sha(raw),'gitBlob':git('rev-parse',f'{HEAD}:{path}').decode().strip(),'gitBlobSha1Check':blob_sha(raw),'entryCount':len(keys),'nonemptyValueCount':sum(bool(v) for v in obj.values()),'orderedKeySha256':sha(('\n'.join(keys)+'\n').encode())})
assert sha(('\n'.join(ordered_keys)+'\n').encode())=='3ca04c40ebfed00b93fcd143109fc9d85da941cec30b6cb93f52e431498df6a7'
source_by_id={sid(x):x for x in ordered_keys}; assert len(source_by_id)==6176
assert all(x['sourceId'] in source_by_id and source_by_id[x['sourceId']]==x['source'] for x in excluded)
exset={x['sourceId'] for x in excluded}
pending=sorted(set(source_by_id)-exset)
selected_ids=pending[:25]
expected_w49=[x['sourceId'] for x in w48inventory if x.get('continuationRank') in range(101,126)]
assert len(expected_w49)==25 and selected_ids==expected_w49,(selected_ids,expected_w49)
selected=[source_by_id[x] for x in selected_ids]
assert selected[0]==ON and selected[-1]=='{label}: {count}'
assert all(source in locales[l] for source in selected for l in LOCALES)

# Pin each exact production caller, excluding test files. Hashes bind caller text and context.
caller_rows=[];caller_by_id={}
for rank,source in enumerate(selected,101):
    refs=caller_refs(source)
    assert refs,(rank,source)
    source_id=sid(source); caller_by_id[source_id]=refs
    caller_rows.append({'continuationRank':rank,'remainingQueueRank':rank-100,'sourceId':source_id,'source':source,'sourceSha256':sha(source.encode()),'productionCallerCount':len(refs),'callers':refs})

# Capture bounded parser evidence for the exact search grammar used by the held search placeholder.
parser_path='src/web/src/lib/searches.js'; parser_lines=(REPO/parser_path).read_text(encoding='utf-8').splitlines();
parser_context=[]
for a,b in [(307,332),(364,367)]:
    block=[{'line':i,'text':parser_lines[i-1]} for i in range(a,b+1)]
    parser_context.append({'path':parser_path,'range':[a,b],'lines':block})
parser_bytes=git('show',f'{HEAD}:{parser_path}');assert parser_bytes==(REPO/parser_path).read_bytes()
support=[{'purpose':'SearchDetail placeholder uses filter flags parsed by this module; localized filter tokens would cease to match these parser expressions.','path':parser_path,'fileBytes':len(parser_bytes),'fileSha256':sha(parser_bytes),'gitBlob':git('rev-parse',f'{HEAD}:{parser_path}').decode().strip(),'gitBlobSha1Check':blob_sha(parser_bytes),'context':parser_context,'contextSha256':sha(canonical(parser_context))}]

# Whole-catalog source inventory and pending sequence, using stable source IDs only.
excluded_origins=collections.defaultdict(list)
for x in excluded: excluded_origins[x['sourceId']].append(x['origin'])
pending_rank={x:i+1 for i,x in enumerate(pending)}
inventory=[]
for source_id,source in sorted(source_by_id.items()):
    qrank=pending_rank.get(source_id)
    inventory.append({'sourceId':source_id,'source':source,'sourceSha256':sha(source.encode()),'excluded':source_id in exset,'exclusionOrigins':excluded_origins.get(source_id,[]),'remainingQueueRank':qrank,'continuationRank':100+qrank if qrank else None,'inW49':source_id in selected_ids,'localeCoverage':sum(source in locales[l] for l in LOCALES)})
assert len(inventory)==6176 and all(x['localeCoverage']==12 for x in inventory)

prior_selected=[]
for rank,source in enumerate(selected,101):
    source_id=sid(source)
    prior_selected.append({'continuationRank':rank,'remainingQueueRank':rank-100,'sourceId':source_id,'source':source,'sourceSha256':sha(source.encode()),'priorW48InventoryContinuationRank':next(x['continuationRank'] for x in w48inventory if x['sourceId']==source_id),'historicalSourceOrdinal':None})
next_id=pending[25]
previous_source=next(x for x in w48inventory if x.get('inW48') and x.get('continuationRank')==100)
following_source=source_by_id[next_id]
selection={'repository':'snapetech-org/slskdN','pullRequest':409,'pullRequestUrl':PR_URL,'pins':pin,'window':'W49 reconstructed pending stable-ID continuation ranks 101-125; historical source ordinals are unavailable and not claimed','localeCount':12,'sourceCount':25,'cellCount':300,'catalogSourceCount':6176,'orderedCatalogKeySha256':sha(('\n'.join(ordered_keys)+'\n').encode()),'priorSemanticExclusionCount':len(prior),'w48SourceCount':len(w48selected),'specialRuntimeFollowupReservedCount':len(special),'excludedUniqueCount':len(excluded),'pendingCount':len(pending),'rankRule':'Sort unexcluded exact catalog source IDs lexicographically; current remainingQueueRank 1-25 maps to continuationRank 101-125. Do not infer or report historical extraction ordinals.','w48BoundaryChecksums':{'SHA256SUMS':sha((W48/'SHA256SUMS').read_bytes()),'sourceInventory':sha((W48/'source-inventory.jsonl').read_bytes()),'priorExcludedSourceIds':sha((W48/'prior-excluded-source-ids.jsonl').read_bytes()),'selectionBoundary':sha((W48/'selection-boundary.jsonl').read_bytes()),'reviewSummary':sha((W48/'review-summary.json').read_bytes()),'all15ListedEntriesVerified':True},'previousBoundary':{'continuationRank':100,'sourceId':previous_source['sourceId'],'source':previous_source['source']},'firstSelected':prior_selected[0],'lastSelected':prior_selected[-1],'nextBoundary':{'continuationRank':126,'remainingQueueRank':26,'sourceId':next_id,'source':following_source},'specialRuntimeFollowups':special,'runtimeFollowupPolicy':'The two W54/W57 readback strings are excluded from the general queue because they were special runtime-only reads; this packet does not assign them new semantic translation dispositions. W71 rich-text follow-up is already in prior semantic exclusion evidence.'}

source_cells=[];decisions=[];counts=collections.Counter(); placeholder_mismatches=[]; markup_mismatches=[]; protected_mismatches=[]
protected_by_source={SEARCH:['iscbr','isvbr','islossless','islossy','minbr','minfilesize','maxfilesize','minfilesinfolder','minlength','320','100mb','2gb','8','5000'],DHT:['DHT'],MESSAGE:['JSON'], 'Send Ntfy notifications when a private message arrives.':['Ntfy']}
for rank,source in enumerate(selected,101):
    source_id=sid(source); refs=caller_by_id[source_id]
    caller_ref_hash=sha(canonical(refs))
    for locale in LOCALES:
        current=locales[locale][source]; current_hash=sha(current.encode())
        candidate=TRANSLATIONS.get(source,{}).get(locale)
        if source in HOLDS:
            verdict='hold'; candidate=None; rationale=HOLDS[source]; confidence='low'
        elif candidate is not None and candidate!=current:
            verdict='refinement' if source in {GRAPH,PREVIEW,AUTOMATIONS,DELETE} else 'correction'
            rationale=RATIONALES[source];confidence=CONFIDENCE[source]
        else:
            candidate=current
            verdict='accept-current'; rationale='The current target is semantically compatible with the exact caller and has no clear material defect; placeholders, markup and protected source terms were checked.';confidence='moderate'
        source_ph=ph(source); current_ph=ph(current); candidate_ph=ph(candidate) if candidate is not None else None
        source_markup=markup(source); current_markup=markup(current); candidate_markup=markup(candidate) if candidate is not None else None
        ph_ok=source_ph==current_ph and (candidate is None or source_ph==candidate_ph)
        markup_ok=source_markup==current_markup and (candidate is None or source_markup==candidate_markup)
        if not ph_ok: placeholder_mismatches.append({'sourceId':source_id,'locale':locale})
        if not markup_ok: markup_mismatches.append({'sourceId':source_id,'locale':locale})
        checks=[]
        for token in protected_by_source.get(source,[]):
            current_has=token in current
            candidate_has=(token in candidate) if candidate is not None else None
            checks.append({'literal':token,'policy':'exact case-sensitive literal','currentPreserved':current_has,'candidatePreserved':candidate_has})
            if not current_has: protected_mismatches.append({'sourceId':source_id,'locale':locale,'literal':token})
        if source==SEARCH:
            checks.append({'literal':'|','policy':'filter flag alternation separator must remain in search syntax','currentPreserved':'|' in current,'candidatePreserved':'|' in candidate if candidate is not None else None})
            if '|' not in current: protected_mismatches.append({'sourceId':source_id,'locale':locale,'literal':'|'})
        row={'continuationRank':rank,'remainingQueueRank':rank-100,'historicalSourceOrdinal':None,'sourceId':source_id,'source':source,'sourceSha256':sha(source.encode()),'locale':locale,'catalogPath':f'src/web/public/locales/{locale}.json','catalogFileSha256':next(x['sha256'] for x in catrows if x['locale']==locale),'catalogGitBlob':next(x['gitBlob'] for x in catrows if x['locale']==locale),'currentTarget':current,'currentTargetSha256':current_hash,'candidateTarget':candidate,'candidateTargetSha256':sha(candidate.encode()) if candidate is not None else None,'verdict':verdict,'rationale':rationale,'confidence':confidence,'callerContextSha256':caller_ref_hash,'callerRefs':[{'path':r['path'],'line':r['line'],'lineSha256':r['lineSha256'],'fileSha256':r['fileSha256'],'gitBlob':r['gitBlob']} for r in refs],'placeholderCheck':{'source':dict(source_ph),'current':dict(current_ph),'candidate':dict(candidate_ph) if candidate is not None else None,'sourceMatchesCurrent':source_ph==current_ph,'sourceMatchesCandidate':source_ph==candidate_ph if candidate is not None else None},'markupCheck':{'source':dict(source_markup),'current':dict(current_markup),'candidate':dict(candidate_markup) if candidate is not None else None,'sourceMatchesCurrent':source_markup==current_markup,'sourceMatchesCandidate':source_markup==candidate_markup if candidate is not None else None},'icuCheck':{'icuSelectorCountSource':0,'icuSelectorCountCurrent':0,'icuSelectorCountCandidate':0 if candidate is not None else None,'ordinaryPlaceholdersAreNotICUSelectors':True},'protectedLiteralChecks':checks}
        assert ph_ok and markup_ok,(row['sourceId'],locale,ph_ok,markup_ok)
        source_cells.append({k:row[k] for k in ['continuationRank','remainingQueueRank','historicalSourceOrdinal','sourceId','source','sourceSha256','locale','catalogPath','catalogFileSha256','catalogGitBlob','currentTarget','currentTargetSha256','callerContextSha256','callerRefs']})
        decisions.append(row);counts[verdict]+=1
assert len(source_cells)==300 and len(decisions)==300 and sum(counts.values())==300

# Recheck pin after all reads; no repository writes are performed by this builder.
pin_after=check_live_pin(); assert pin_after==pin
wjl(OUT/'catalog-structure.jsonl',catrows)
wjl(OUT/'prior-excluded-source-ids.jsonl',excluded)
wjl(OUT/'source-inventory.jsonl',inventory)
wjl(OUT/'selection-boundary.jsonl',prior_selected)
wjl(OUT/'caller-context.jsonl',caller_rows)
wjl(OUT/'source-current-cells.jsonl',source_cells)
wjl(OUT/'review-decisions.jsonl',decisions)
wjl(OUT/'supporting-context.jsonl',support)
wj(OUT/'selection-and-boundary.json',selection)
summary={'exactHead':HEAD,'exactTree':TREE,'window':'W49 pending stable-ID continuation ranks 101-125; historical source ordinals unavailable','sourceCount':25,'localeCount':12,'cellCount':300,'dispositionCounts':dict(counts),'correctionOrRefinementCount':counts['correction']+counts['refinement'],'holdSourceIds':[x['sourceId'] for x in prior_selected if x['source']==SEARCH],'heldCellCount':counts['hold'],'placeholderMismatches':len(placeholder_mismatches),'markupMismatches':len(markup_mismatches),'currentProtectedLiteralMismatchCount':len(protected_mismatches),'currentProtectedLiteralMismatchExamples':protected_mismatches[:50],'candidateProtectedLiteralMismatchCount':sum(1 for x in decisions if x['candidateTarget'] is not None for p in x['protectedLiteralChecks'] if not p['candidatePreserved']),'searchPlaceholderHeldAllLocales':True,'catalogCoverageCells':300,'nativeSpeakerApproval':False,'semanticConfidence':'moderate machine-assisted primary review','localeQualityConfidence':'moderate machine-assisted; native-speaker review outstanding','headedBrowserReview':False,'testsBuildScansCiRun':False,'remoteMutation':False,'repositoryModified':False,'finalPrHeadStillPinned':True,'scratchPath':str(OUT)}
wj(OUT/'review-summary.json',summary)
readme=f'''# slskdN PR #409 W49 primary localization review

- Exact PR head/tree: `{HEAD}` / `{TREE}`. Live PR, remote branch, local worktree, and commit tree were reattested before and after packet generation.
- The packet covers 25 pending stable source IDs × 12 locales = 300 cells. It reconstructs continuation ranks 101–125 from the exact ordered catalog key set after excluding W1–W48 semantic windows and reserving the two W54/W57 runtime-only follow-ups. Historical source ordinals are unavailable and are not claimed.
- W48 evidence checksums were verified (14 entries); source inventory, prior exclusions, W48 selection, and the special runtime follow-up boundary are recorded.
- Caller source lines, context hashes, exact caller-file hashes/Git blobs, current catalog file hashes/Git blobs, current target hashes, placeholders, markup, ICU selector counts, and protected literals are recorded.
- The filter placeholder is held in all locales because it demonstrates parser syntax and current translations alter parser tokens; the exact parser implementation is pinned in `supporting-context.jsonl`. The current protected-literal failures are confined to this held placeholder.
- Dispositions: {', '.join(f'{k} {v}' for k,v in sorted(counts.items()))}. All candidate translations remain proposals pending locale review.
- This is machine-assisted primary review. Native-speaker approval is outstanding. No repository edits, tests, builds, scans, CI, browser work, PR changes, commits, or pushes were performed. Only this task-scoped scratch packet was created.
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')
arts=sorted(p for p in OUT.iterdir() if p.is_file() and p.name not in {'manifest.json','SHA256SUMS'})
wj(OUT/'manifest.json',{'schemaVersion':1,'repository':'snapetech-org/slskdN','pullRequest':409,'exactHead':HEAD,'exactTree':TREE,'window':'W49 continuation ranks 101-125; historical ordinals unavailable','artifacts':[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in arts]})
files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name!='SHA256SUMS')
with (OUT/'SHA256SUMS').open('w',encoding='utf-8',newline='\n') as f:
    for p in files:f.write(f'{sha(p.read_bytes())}  {p.name}\n')
for line in (OUT/'SHA256SUMS').read_text().splitlines():
    expected,name=line.split(None,1); assert sha((OUT/name.strip()).read_bytes())==expected,name
for artifact in json.loads((OUT/'manifest.json').read_text())['artifacts']:
    data=(OUT/artifact['path']).read_bytes(); assert len(data)==artifact['bytes'] and sha(data)==artifact['sha256'],artifact['path']
assert not git('status','--porcelain=v1').decode().strip()
print(json.dumps({'output':str(OUT),'sumEntries':len(files),'manifestArtifacts':len(arts),'sourceCount':25,'cellCount':300,'dispositionCounts':dict(counts),'placeholderMismatches':len(placeholder_mismatches),'markupMismatches':len(markup_mismatches),'protectedLiteralMismatches':len(protected_mismatches),'worktreeClean':True,'scratchBytes':sum(p.stat().st_size for p in OUT.iterdir() if p.is_file())},ensure_ascii=False,indent=2))
