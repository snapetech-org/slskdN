#!/usr/bin/env python3
"""Create a separate primary review from the sealed W53 input packet."""
from pathlib import Path
import collections, hashlib, json, re, subprocess

OUT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w53-20261103')
INPUT = OUT / 'input'
PRIMARY = OUT / 'primary'
REPO = Path('/mnt/disks/scratch/task-worktrees/localization-20261103/slskdn-pr409-w52-primary-20261103')
HEAD = '6d5723e244338a550e3dfa5182a45857156467a7'
TREE = '8435576260e9aa760609be6a28001b2bb38b8c11'
BODY = '8d1708765c003a72da67370af5816a7cd998cfb97b2246227aaf1529f858cf4a'
BRANCH = 'codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PLACEHOLDER_RE = re.compile(r'\{[^{}]+\}')
MARKUP_RE = re.compile(r'</?[A-Za-z][^>]*>')
NUMBER_RE = re.compile(r'(?<![A-Za-z])\d+(?:[.,]\d+)?%?(?![A-Za-z])')

# (rank, locale): (candidate, disposition, caller/source-grounded rationale)
CANDIDATES = {
    (227,'hi'): ('सर्वर का पता','refinement','This is the FTP integration form label. Adding का makes the Hindi genitive relation natural.'),
    (227,'id'): ('Alamat server','refinement','This is the FTP integration form label. Lowercase server follows ordinary Indonesian noun capitalization.'),
    (229,'ar'): ('تغطية سجلات q على غرار MilkDrop3 عبر المعادلات والعناصر الأولية والمظللات.','correction','The caller is a MilkDrop preset fixture. تسجيل q reads as recording q; this uses the q-register concept and preserves the exact MilkDrop3 product name.'),
    (229,'es'): ('Cobertura de registros q al estilo de MilkDrop3 en ecuaciones, primitivas y shaders.','refinement','The caller is a MilkDrop preset fixture. Add the missing de in al estilo de while retaining the technical q-register and MilkDrop3 terms.'),
    (229,'hi'): ('समीकरणों, प्रिमिटिव और शेडर्स में MilkDrop3-शैली के q-रजिस्टर का कवरेज।','correction','The caller is a MilkDrop preset fixture. Preserve the exact MilkDrop3 product spelling; the current transliteration loses the protected product name.'),
    (229,'pt-BR'): ('Cobertura de registros q no estilo do MilkDrop3 em equações, primitivas e shaders.','refinement','The caller is a MilkDrop preset fixture. This makes the Portuguese phrase grammatical and keeps the q-register/MilkDrop3 concepts.'),
    (229,'vi'): ('Phạm vi bao phủ các thanh ghi q theo phong cách MilkDrop3 trong phương trình, hình cơ bản và shader.','correction','The caller is a MilkDrop preset fixture. Đăng ký means sign up/register, not a technical register; this uses thanh ghi and keeps MilkDrop3 exact.'),
    (229,'zh-Hans'): ('MilkDrop3 风格的 q 寄存器在方程、图元和着色器中的覆盖范围。','refinement','The caller is a MilkDrop preset fixture. The current grammar makes the register itself cover the subjects; this expresses the coverage range.'),
    (229,'zh-Hant'): ('MilkDrop3 風格的 q 暫存器在方程式、圖元和著色器中的涵蓋範圍。','refinement','The caller is a MilkDrop preset fixture. The current grammar makes the register itself cover the subjects; this expresses the coverage range.'),
    (230,'ar'): ('Pushover','correction','The caller uses Pushover as the notification-service product name. The current Arabic text translates the ordinary “easy task” sense.'),
    (230,'de'): ('Pushover','correction','The caller uses Pushover as the notification-service product name. The current German text describes a pushover person.'),
    (230,'es'): ('Pushover','correction','The caller uses Pushover as the notification-service product name. The current Spanish text describes a person who is easy to persuade.'),
    (230,'fr'): ('Pushover','correction','The caller uses Pushover as the notification-service product name. The current French text means “child’s play.”'),
    (230,'hi'): ('Pushover','correction','The caller uses Pushover as the notification-service product name. The current Hindi text means a small matter.'),
    (230,'id'): ('Pushover','correction','The caller uses Pushover as the notification-service product name. The current Indonesian text means a compliant person.'),
    (230,'ja'): ('Pushover','correction','The caller uses Pushover as the notification-service product name. Preserve the exact service name instead of phonetic transliteration.'),
    (230,'ko'): ('Pushover','correction','The caller uses Pushover as the notification-service product name. The current Korean text means an easy task.'),
    (230,'pt-BR'): ('Pushover','correction','The caller uses Pushover as the notification-service product name. The current Portuguese text means a push-up.'),
    (230,'vi'): ('Pushover','correction','The caller uses Pushover as the notification-service product name. The current Vietnamese text means “push.”'),
    (230,'zh-Hans'): ('Pushover','correction','The caller uses Pushover as the notification-service product name. The current Chinese text translates the ordinary “push over” sense.'),
    (230,'zh-Hant'): ('Pushover','correction','The caller uses Pushover as the notification-service product name. The current Chinese text translates the ordinary “push over” sense.'),
    (231,'ar'): ('دقائق الاحتفاظ بالتحميلات الفاشلة','correction','The caller is the Errored column of the Uploads retention table. This names the duration to retain failed uploads, rather than uploading retention minutes.'),
    (231,'de'): ('Aufbewahrungsdauer für fehlgeschlagene Uploads (Minuten)','correction','The caller is the Errored column of the Uploads retention table. The current imperative says to upload retention minutes.'),
    (231,'es'): ('Minutos de retención de las subidas fallidas','correction','The caller is the Errored column of the Uploads retention table. This is a duration label for failed uploads, not an upload action.'),
    (231,'fr'): ('Durée de conservation des envois échoués (minutes)','correction','The caller is the Errored column of the Uploads retention table. This names how long failed uploads are retained.'),
    (231,'hi'): ('विफल अपलोड को कितने मिनट तक रखना है','correction','The caller is the Errored column of the Uploads retention table. The current text reverses the action and duration.'),
    (231,'id'): ('Lama penyimpanan unggahan yang gagal (menit)','correction','The caller is the Errored column of the Uploads retention table. This names the retention duration, not an upload command.'),
    (231,'ja'): ('失敗したアップロードの保持期間（分）','correction','The caller is the Errored column of the Uploads retention table. Add the missing unit and identify the retained failed uploads.'),
    (231,'ko'): ('실패한 업로드 보존 기간(분)','correction','The caller is the Errored column of the Uploads retention table. The current word order describes an upload action.'),
    (231,'pt-BR'): ('Tempo de retenção de uploads com falha (minutos)','correction','The caller is the Errored column of the Uploads retention table. This names the time to retain failed uploads.'),
    (231,'vi'): ('Thời gian lưu giữ các lượt tải lên thất bại (phút)','correction','The caller is the Errored column of the Uploads retention table. This names the duration for failed uploads.'),
    (231,'zh-Hans'): ('失败的上传保留时间（分钟）','correction','The caller is the Errored column of the Uploads retention table. This names the retention period for failed uploads.'),
    (231,'zh-Hant'): ('失敗的上傳保留時間（分鐘）','correction','The caller is the Errored column of the Uploads retention table. This names the retention period for failed uploads.'),
    (232,'ar'): ('تمت مغادرة {podName}','correction','The caller emits a success toast after pods.leave completes. اليسار means “left” as a direction, not leaving a Pod.'),
    (232,'de'): ('Du hast {podName} verlassen.','correction','The caller emits a success toast after pods.leave completes. Links means “left” as a direction.'),
    (232,'es'): ('Has salido de {podName}.','correction','The caller emits a success toast after pods.leave completes. Izquierda means “left” as a direction.'),
    (232,'fr'): ('Vous avez quitté {podName}.','correction','The caller emits a success toast after pods.leave completes. Gauche means “left” as a direction.'),
    (232,'hi'): ('आपने {podName} छोड़ दिया।','correction','The caller emits a success toast after pods.leave completes. बायां means “left” as a direction.'),
    (232,'id'): ('Anda telah keluar dari {podName}.','correction','The caller emits a success toast after pods.leave completes. Kiri means “left” as a direction.'),
    (232,'ja'): ('{podName} から退出しました。','correction','The caller emits a success toast after pods.leave completes. 左 means “left” as a direction.'),
    (232,'ko'): ('{podName}에서 나왔습니다.','correction','The caller emits a success toast after pods.leave completes. 왼쪽 means “left” as a direction.'),
    (232,'pt-BR'): ('Você saiu de {podName}.','correction','The caller emits a success toast after pods.leave completes. Esquerda means “left” as a direction.'),
    (232,'vi'): ('Đã rời khỏi {podName}.','correction','The caller emits a success toast after pods.leave completes. Còn lại means “remaining,” not leaving.'),
    (232,'zh-Hans'): ('已离开 {podName}。','correction','The caller emits a success toast after pods.leave completes. 左 means “left” as a direction.'),
    (232,'zh-Hant'): ('已離開 {podName}。','correction','The caller emits a success toast after pods.leave completes. 左 means “left” as a direction.'),
    (235,'es'): ('Vuelva a conectarse a esta sala y actualice el estado actual del anfitrión después de un fallo de conexión o de actualización.','correction','The caller is the listen-along room retry action. Host is the person hosting playback, so anfitrión is clearer than the English loanword.'),
    (235,'vi'): ('Kết nối lại với phòng này và làm mới trạng thái hiện tại của chủ phòng sau khi kết nối hoặc làm mới thất bại.','correction','The caller is the listen-along room retry action. Máy chủ means a computer server; the host is the room’s person, chủ phòng.'),
    (235,'zh-Hans'): ('连接或刷新失败后，重新连接到该房间并刷新房主的当前状态。','correction','The caller is the listen-along room retry action. 主机 reads as a computer host; 房主 identifies the room’s playback host.'),
    (235,'zh-Hant'): ('連線或重新整理失敗後，重新連線到該房間並更新房主目前的狀態。','correction','The caller is the listen-along room retry action. 主機 reads as a computer host; 房主 identifies the room’s playback host.'),
    (241,'ja'): ('人','refinement','The only caller appends this label after a number of worker usernames. 人 gives a natural count of the additional people.'),
    (241,'ko'): ('명','refinement','The only caller appends this label after a number of worker usernames. 명 supplies the natural Korean counter for additional people.'),
    (241,'vi'): ('nữa','correction','The only caller appends this label after a number of worker usernames. hơn requires a comparison; nữa expresses additional workers.'),
    (241,'zh-Hans'): ('人','correction','The only caller appends this label after the count of extra worker usernames. 人 gives a natural count of additional people; 的 makes the current suffix ungrammatical.'),
    (241,'zh-Hant'): ('人','correction','The only caller appends this label after the count of extra worker usernames. 人 gives a natural count of additional people; 的 makes the current suffix ungrammatical.'),
    (244,'ar'): ('مسح الإعدادات المسبقة المستوردة إلى العارض الأصلي','refinement','The Visualizer caller clarifies these are imported presets for the native MilkDrop renderer. الأصلية reads as “original”; this states the renderer relationship.'),
    (244,'hi'): ('आयातित नेटिव प्रीसेट हटाएँ','correction','The Visualizer caller clarifies these are presets for the native MilkDrop renderer. देशी suggests indigenous/local origin rather than the software renderer.'),
    (244,'id'): ('Hapus preset native yang diimpor','refinement','The Visualizer caller clarifies native means the app’s renderer. Asli reads as original; native is the relevant software term.'),
    (244,'ko'): ('가져온 네이티브 프리셋 지우기','correction','The Visualizer caller clarifies these are presets for the native MilkDrop renderer. 기본 means default, which is not the source meaning.'),
    (244,'vi'): ('Xóa các preset native đã nhập','correction','The Visualizer caller clarifies native means the app’s renderer. Gốc means original/root, not a native renderer.'),
    (244,'zh-Hans'): ('清除已导入的原生预设','refinement','The Visualizer caller clarifies these are presets for the native MilkDrop renderer. 本机 means local-machine presets; 原生 preserves the renderer meaning.'),
    (244,'zh-Hant'): ('清除已匯入的原生預設','refinement','The Visualizer caller clarifies these are presets for the native MilkDrop renderer. 本機 means local-machine presets; 原生 preserves the renderer meaning.'),
    (245,'ar'): ('اتصالات Kestrel','correction','The caller is the ASP.NET Core Kestrel current-connections metric. Preserve Kestrel as the exact technology name rather than transliterating it.'),
    (245,'es'): ('Conexiones de Kestrel','correction','The caller is the ASP.NET Core Kestrel current-connections metric. Cernícalo means the bird kestrel; preserve the exact technology name.'),
    (245,'fr'): ('Connexions Kestrel','correction','The caller is the ASP.NET Core Kestrel current-connections metric. Crécerelle means the bird kestrel; preserve the exact technology name.'),
    (245,'hi'): ('Kestrel कनेक्शन','correction','The caller is the ASP.NET Core Kestrel current-connections metric. Preserve the exact technology spelling instead of transliteration.'),
    (245,'ja'): ('Kestrel 接続数','correction','The caller is the ASP.NET Core Kestrel current-connections metric. Preserve the exact technology spelling and label the connection count.'),
    (245,'ko'): ('Kestrel 연결 수','correction','The caller is the ASP.NET Core Kestrel current-connections metric. Preserve the exact technology spelling and label the connection count.'),
    (245,'zh-Hans'): ('Kestrel 连接数','correction','The caller is the ASP.NET Core Kestrel current-connections metric. 红隼 means the bird; preserve the exact technology name.'),
    (245,'zh-Hant'): ('Kestrel 連線數','correction','The caller is the ASP.NET Core Kestrel current-connections metric. 紅隼 means the bird; preserve the exact technology name.'),
    (247,'ar'): ('أفضل 10','refinement','The caller is a ranking-limit option alongside 20 and 50. أفضل is the natural label for the top-ranked entries.'),
    (249,'ar'): ('يمكن إضافة العناصر المطلوبة والعناصر التي لم تبلغ الحد المطلوب إلى مراجعة قائمة أمنيات slskdN.','correction','The caller is a Servarr readiness description for pulling wanted and cutoff-unmet items into Wishlist review. This explains the unmet cutoff as a required threshold and uses إضافة for adding items.'),
    (249,'de'): ('Gesuchte Einträge und solche, die den Grenzwert nicht erreichen, können zur Prüfung in die slskdN-Wunschliste übernommen werden.','correction','The caller is a Servarr readiness description. The current “nicht erfüllte” omits the cutoff condition; this makes the unmet threshold explicit.'),
    (249,'es'): ('Los elementos deseados y los que no alcanzan el umbral pueden añadirse a la revisión de la lista de deseos de slskdN.','correction','The caller is a Servarr readiness description. The current “no satisfechos” omits the cutoff condition; this names the unmet threshold.'),
    (249,'fr'): ('Les éléments souhaités et ceux qui n’atteignent pas le seuil peuvent être ajoutés à la liste de souhaits de slskdN pour examen.','correction','The caller is a Servarr readiness description. Recherchés can mean searched and extraits de reverses the direction; this says wanted items below the cutoff are added for review.'),
    (249,'hi'): ('चाहे गए आइटम और सीमा तक न पहुँचे आइटम समीक्षा के लिए slskdN की इच्छा-सूची में जोड़े जा सकते हैं।','correction','The caller is a Servarr readiness description. Replace the unexplained cutoff-unmet hybrid with items that have not reached the threshold.'),
    (249,'id'): ('Item yang diinginkan dan item yang belum mencapai ambang batas dapat ditambahkan ke Daftar Keinginan slskdN untuk ditinjau.','correction','The caller is a Servarr readiness description. The current wording omits the cutoff; this names the unmet threshold and review action.'),
    (249,'ja'): ('希望するアイテムや基準に達していないアイテムを、slskdN のウィッシュリストに追加して確認できます。','refinement','The caller is a Servarr readiness description. Make the cutoff threshold explicit and express the Wishlist review action naturally.'),
    (249,'ko'): ('원하는 항목과 기준에 미달한 항목을 slskdN 위시리스트 검토에 추가할 수 있습니다.','correction','The caller is a Servarr readiness description. The current phrasing is awkward and does not clearly identify items below the cutoff.'),
    (249,'pt-BR'): ('Itens desejados e os que não atingiram o limite podem ser adicionados à revisão da lista de desejos do slskdN.','correction','The caller is a Servarr readiness description. The current “não atendidos” omits the cutoff condition; this names the unmet threshold.'),
    (249,'vi'): ('Các mục được yêu cầu và các mục chưa đạt ngưỡng có thể được thêm vào phần rà soát Danh sách yêu thích của slskdN.','correction','The caller is a Servarr readiness description. The current text omits the cutoff; this names the unmet threshold and review section.'),
    (249,'zh-Hans'): ('想要的项目和未达到门槛的项目可以加入 slskdN 愿望清单审核。','correction','The caller is a Servarr readiness description. The current cutoff phrase is unnatural and 评论 means comments; this names the threshold and review.'),
    (249,'zh-Hant'): ('想要的項目和未達到門檻的項目可以加入 slskdN 願望清單審查。','correction','The caller is a Servarr readiness description. The current cutoff phrase is unnatural and 評論 means comments; this names the threshold and review.'),
}

HOLD_RANKS = {226,239}
ACCEPT_RATIONALE = {
    228:'The caller is a contacts pagination tooltip; the current text clearly says to show the previous contacts page.',
    233:'The caller is a Wishlist auto-search failure toast; the current error prefix is clear and preserves the {message} placeholder.',
    234:'The caller is a message input placeholder. The current values preserve {label}, / and /help and explain the slash-command affordances.',
    236:'The caller uses this as a fallback heading for a shared collection; the current labels accurately name its contents.',
    237:'The caller is an accessible toggle label for the Pushbullet integration. The service name and enable action are retained.',
    238:'The caller is the metadata-processing stage label; the current values express automatic tagging.',
    240:'The caller is the Obfs4 settings path label. All current targets preserve the exact Obfs4 protocol name and identify the proxy path.',
    242:'The caller labels a percentage computed from baselineDelta; the current targets express a difference/delta.',
    243:'The callers are cleanup error toasts; the current wording preserves the {message} placeholder and failure meaning.',
    246:'The caller is a security settings status heading shown when the server module is unavailable; the current labels preserve that status.',
    247:'The caller is a ranking-limit option paired with 20 and 50; the current values express the top ten except the separately refined Arabic wording.',
    248:'The caller is a label immediately before a computed impact percentage; the current targets express an estimate and retain colon punctuation.',
    250:'The caller is a Wishlist tooltip for opening this item’s linked search history and prior results; current text preserves that action.',
}

def run(*args, cwd=REPO, text=True): return subprocess.check_output(list(args), cwd=cwd, text=text)
def sha(data): return hashlib.sha256(data.encode('utf-8') if isinstance(data,str) else data).hexdigest()
def canonical(obj): return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def readjl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def readjson(path): return json.loads(path.read_text(encoding='utf-8'))
def verify_manifest(directory,name):
    checks=[]
    for line in (directory/name).read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        expected,rel=line.split(None,1); rel=rel.strip().lstrip('*')
        actual=sha((directory/rel).read_bytes())
        checks.append({'path':rel,'expected':expected,'actual':actual,'matches':expected==actual})
    assert checks and all(x['matches'] for x in checks),(directory,name,checks)
    return checks
def writejson(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def writejl(path,rows): path.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
def write_manifest(directory,name):
    manifest=directory/name
    rows=[]
    for p in sorted(x for x in directory.rglob('*') if x.is_file() and x!=manifest):
        rows.append(f'{sha(p.read_bytes())}  {p.relative_to(directory).as_posix()}')
    manifest.write_text('\n'.join(rows)+'\n',encoding='utf-8')

def live_pin():
    head=run('git','rev-parse','HEAD').strip(); tree=run('git','rev-parse','HEAD^{tree}').strip()
    assert head==HEAD and tree==TREE and not run('git','status','--porcelain=v1').strip(),(head,tree,run('git','status','--short'))
    remote=run('git','ls-remote','origin',f'refs/heads/{BRANCH}').strip().split()
    assert len(remote)==2 and remote[0]==HEAD,remote
    return {'head':head,'tree':tree,'branch':BRANCH,'remoteBranchHead':remote[0],'state':'open','draft':True,'bodySha256':BODY}

assert not (PRIMARY/'SHA256SUMS.txt').exists(), f'Primary review manifest already exists: {PRIMARY}'
input_manifest_checks=verify_manifest(INPUT,'PACKET-SHA256SUMS.txt')
input_manifest_sha=sha((INPUT/'PACKET-SHA256SUMS.txt').read_bytes())
pin=live_pin()
attest=readjson(INPUT/'head-tree-attestation.json')
selection=readjson(INPUT/'selection-and-boundary.json')
source_rows=readjl(INPUT/'source-current-cells.jsonl')
caller_rows=readjl(INPUT/'caller-contexts.jsonl')
protected_rows=readjl(INPUT/'protected-literals.jsonl')
assert attest['head']==HEAD and attest['tree']==TREE and attest['bodySha256']==BODY
assert selection['pins']==attest and selection['inputContainsCandidates'] is False
assert len(source_rows)==300 and len(caller_rows)==25 and len(protected_rows)==25
assert all('candidateTarget' not in r and 'verdict' not in r and 'disposition' not in r for r in source_rows)
assert [(r['continuationRank'],r['locale']) for r in source_rows]==[(rank,loc) for rank in range(226,251) for loc in LOCALES]
assert len({(r['sourceId'],r['locale']) for r in source_rows})==300
assert len({x['sourceId'] for x in caller_rows})==25
assert len(CANDIDATES)==82 and set(HOLD_RANKS)=={226,239}
assert all(rank in range(226,251) and loc in LOCALES for rank,loc in CANDIDATES)

protected_by_id={r['sourceId']:r for r in protected_rows}
rows=[]; counts=collections.Counter(); changed_by_locale=collections.Counter(); changed_by_rank=collections.Counter(); changed_by_source=collections.Counter()
current_protected_mismatches=[]; candidate_protected_mismatches=[]; placeholder_mismatches=[]; markup_mismatches=[]; numeric_mismatches=[]
for item in source_rows:
    rank=item['continuationRank']; source=item['source']; source_id=item['sourceId']; loc=item['locale']; current=item['currentTarget']
    if (rank,loc) in CANDIDATES:
        candidate,verdict,rationale=CANDIDATES[(rank,loc)]
        confidence='moderate'
    elif rank in HOLD_RANKS:
        candidate=current; verdict='hold-context'; confidence='low'
        if rank==226:
            rationale='No exact production caller was found in the bounded source scan. The current generic deletion-failure translation is plausible, but hold the cell until its source context is pinned.'
        else:
            rationale='No exact production caller was found in the bounded source scan. Hold the generic changed-fields label until its entity, register, and display context are pinned.'
    else:
        candidate=current; verdict='accept-current'; confidence='moderate'
        rationale=ACCEPT_RATIONALE.get(rank,'The current target matches the pinned source and caller context; no material meaning, grammar, placeholder, markup, number, or protected-name defect was identified.')
    source_ph=collections.Counter(PLACEHOLDER_RE.findall(source)); current_ph=collections.Counter(PLACEHOLDER_RE.findall(current)); candidate_ph=collections.Counter(PLACEHOLDER_RE.findall(candidate))
    source_markup=collections.Counter(MARKUP_RE.findall(source)); current_markup=collections.Counter(MARKUP_RE.findall(current)); candidate_markup=collections.Counter(MARKUP_RE.findall(candidate))
    source_numbers=collections.Counter(NUMBER_RE.findall(source)); candidate_numbers=collections.Counter(NUMBER_RE.findall(candidate))
    ph_ok=source_ph==current_ph and source_ph==candidate_ph
    markup_ok=source_markup==current_markup and source_markup==candidate_markup
    numeric_ok=source_numbers==candidate_numbers
    if not ph_ok: placeholder_mismatches.append((rank,loc))
    if not markup_ok: markup_mismatches.append((rank,loc))
    if not numeric_ok: numeric_mismatches.append((rank,loc))
    checks=[]
    for lit in item.get('protectedLiteralChecks',[]):
        row={'literal':lit['literal'],'kind':lit['kind'],'policy':lit['policy'],'sourcePreserved':lit['literal'] in source,'currentPreserved':lit['literal'] in current,'candidatePreserved':lit['literal'] in candidate}
        checks.append(row)
        if not row['currentPreserved']: current_protected_mismatches.append({'rank':rank,'sourceId':source_id,'locale':loc,'literal':lit['literal']})
        if not row['candidatePreserved']: candidate_protected_mismatches.append({'rank':rank,'sourceId':source_id,'locale':loc,'literal':lit['literal']})
    caller={r['sourceId']:r for r in caller_rows}[source_id]
    row={'continuationRank':rank,'historicalSourceOrdinal':None,'sourceId':source_id,'source':source,'sourceSha256':item['sourceSha256'],'locale':loc,'catalogPath':item['catalogPath'],'catalogFileSha256':item['catalogFileSha256'],'catalogGitBlob':item['catalogGitBlob'],'currentTarget':current,'currentTargetSha256':item['currentTargetSha256'],'candidateTarget':candidate,'candidateTargetSha256':sha(candidate),'verdict':verdict,'rationale':rationale,'confidence':confidence,'callerCount':caller['productionCallerCount'],'callerContextSha256':item['callerContextSha256'],'callerRefs':item['callerRefs'],'placeholderCheck':{'source':dict(source_ph),'current':dict(current_ph),'candidate':dict(candidate_ph),'sourceMatchesCurrent':source_ph==current_ph,'sourceMatchesCandidate':source_ph==candidate_ph},'markupCheck':{'source':dict(source_markup),'current':dict(current_markup),'candidate':dict(candidate_markup),'sourceMatchesCurrent':source_markup==current_markup,'sourceMatchesCandidate':source_markup==candidate_markup},'numericCheck':{'source':dict(source_numbers),'candidate':dict(candidate_numbers),'sourceMatchesCandidate':numeric_ok},'protectedLiteralChecks':checks}
    rows.append(row); counts[verdict]+=1
    if candidate!=current:
        changed_by_locale[loc]+=1; changed_by_rank[rank]+=1; changed_by_source[source_id]+=1

assert len(rows)==300 and not placeholder_mismatches and not markup_mismatches and not numeric_mismatches
assert not candidate_protected_mismatches
assert counts['hold-context']==24 and counts['correction']+counts['refinement']==82
assert all(r['candidateTargetSha256']==sha(r['candidateTarget']) for r in rows)

assert PRIMARY.is_dir() and set(p.name for p in PRIMARY.iterdir()) == {'build_primary_review.py'}, f'Unexpected primary output path content: {list(PRIMARY.iterdir())}'
writejl(PRIMARY/'review-decisions.jsonl',rows)
summary={'repository':'snapetech-org/slskdN','pullRequest':409,'pullRequestUrl':attest['url'],'exactHead':HEAD,'exactTree':TREE,'pinnedPrBodySha256':BODY,'window':'W53 continuation ranks 226-250 from the W49 stable-ID inventory; historical source ordinals unavailable and not claimed','sourceCount':25,'localeCount':12,'cellCount':300,'dispositionCounts':dict(counts),'candidateChangeCount':sum(changed_by_locale.values()),'changedCellsByLocale':dict(changed_by_locale),'changedCellsByRank':dict(sorted(changed_by_rank.items())),'changedCellsBySource':dict(changed_by_source),'holdCount':counts['hold-context'],'heldSourceIds':sorted({r['sourceId'] for r in rows if r['verdict']=='hold-context'}),'callerReferenceCount':sum(x['productionCallerCount'] for x in caller_rows),'callerlessSourceIds':[x['sourceId'] for x in caller_rows if x['productionCallerCount']==0],'currentProtectedLiteralMismatchCount':len(current_protected_mismatches),'candidateProtectedLiteralMismatchCount':len(candidate_protected_mismatches),'placeholderMismatchCount':len(placeholder_mismatches),'markupMismatchCount':len(markup_mismatches),'numericMismatchCount':len(numeric_mismatches),'candidateChangedSourceIds':len(changed_by_source),'nativeSpeakerApproval':False,'headedBrowserReview':False,'projectTestsBuildScansCiRun':False,'reviewHelperSyntaxPreflight':True,'taskOwnedPycacheRemoved':True,'repositoryModified':False,'remoteMutation':False,'reviewType':'machine-assisted primary review; moderate confidence except context holds','inputManifestSha256':input_manifest_sha,'inputManifestEntriesVerified':len(input_manifest_checks),'sourceSequence':{'first':selection['firstSelected'],'last':selection['lastSelected'],'nextBoundary':selection['nextBoundary'],'disjointFromW50W51W52':selection['disjointness']['w53DisjointFromW50W51W52'],'w49UnreviewedGapPreserved':selection['disjointness']['w53DisjointFromW49Gap']},'changes':[{'rank':r['continuationRank'],'sourceId':r['sourceId'],'source':r['source'],'locale':r['locale'],'from':r['currentTarget'],'to':r['candidateTarget'],'disposition':r['verdict'],'rationale':r['rationale']} for r in rows if r['candidateTarget']!=r['currentTarget']]}
writejson(PRIMARY/'review-summary.json',summary)

worksheet=['# W53 primary review worksheet','',f'Exact PR head/tree: `{HEAD}` / `{TREE}`.','Input packet SHA-256: `'+input_manifest_sha+'`.','25 stable-ID source rows × 12 locales = 300 cells. Historical extraction ordinals are unavailable and are not claimed.']
for rank in range(226,251):
    group=[r for r in rows if r['continuationRank']==rank]
    src=group[0]
    worksheet += ['',f"## Rank {rank} — `{src['sourceId']}`",'',f"**Source:** {src['source']}",'',f"**Caller references:** {src['callerCount']}"]
    if src['callerRefs']:
        for ref in src['callerRefs']: worksheet.append(f"- `{ref['path']}:{ref['line']}` (line SHA `{ref['lineSha256'][:12]}`)")
    else: worksheet.append('- None found in bounded production literal scan; all locale cells are held for context.')
    worksheet += ['', '| Locale | Current | Primary proposal | Disposition |', '|---|---|---|---|']
    for r in group:
        worksheet.append(f"| {r['locale']} | {r['currentTarget']} | {r['candidateTarget']} | {r['verdict']} |")
        if r['verdict']!='accept-current': worksheet.append(f"|  | **Rationale** | {r['rationale']} | confidence: {r['confidence']} |")
(PRIMARY/'review-worksheet.md').write_text('\n'.join(worksheet)+'\n',encoding='utf-8')

readme=f'''# slskdN PR #409 W53 primary review\n\nThis primary-only review covers the sealed clean input packet `{INPUT}` at PR head/tree `{HEAD}` / `{TREE}`. The review covers 25 stable source IDs at W49 continuation ranks 226–250 across all 12 locales (300 cells). Historical source ordinals are unavailable and are not claimed.\n\nPrimary dispositions: {counts['accept-current']} accept-current, {counts['correction']} corrections, {counts['refinement']} refinements, and {counts['hold-context']} context holds. There are {sum(changed_by_locale.values())} candidate value changes. The two held source IDs have no exact production caller in the bounded literal scan; all 24 locale cells remain at their current values.\n\nThe review rechecked source/current/candidate hashes, caller pins, placeholder and markup parity, numeric content, and protected names. All candidate placeholders, markup, numeric values, and protected exact literals match the review requirements. Current protected-literal mismatches are recorded separately and have candidate repairs where caller evidence is sufficient.\n\nThis is machine-assisted primary review, not qualified native-speaker approval or headed-browser review. The primary review is separate from and does not modify the sealed input. No repository or PR changes, project tests/builds, scans, CI, browser actions, workflow edits, releases, merges, or tags were performed. The review helper had a Python syntax-only preflight; its task-owned bytecode cache was removed.\n'''
(PRIMARY/'README.md').write_text(readme,encoding='utf-8')

# Seal primary files and confirm both packets still match their pinned state.
write_manifest(PRIMARY,'SHA256SUMS.txt')
primary_checks=verify_manifest(PRIMARY,'SHA256SUMS.txt')
assert verify_manifest(INPUT,'PACKET-SHA256SUMS.txt')==input_manifest_checks
assert sha((INPUT/'PACKET-SHA256SUMS.txt').read_bytes())==input_manifest_sha
assert live_pin()==pin

print(json.dumps({'verification':'primary-sealed','head':HEAD,'tree':TREE,'inputManifestSha256':input_manifest_sha,'inputManifestEntriesVerified':len(input_manifest_checks),'primaryManifestSha256':sha((PRIMARY/'SHA256SUMS.txt').read_bytes()),'primaryManifestEntriesVerified':len(primary_checks),'sources':25,'cells':300,'dispositions':dict(counts),'candidateChanges':sum(changed_by_locale.values()),'changedCellsByLocale':dict(changed_by_locale),'holds':counts['hold-context'],'heldSourceIds':summary['heldSourceIds'],'callerReferences':sum(x['productionCallerCount'] for x in caller_rows),'callerlessSourceIds':summary['callerlessSourceIds'],'placeholderMismatches':len(placeholder_mismatches),'markupMismatches':len(markup_mismatches),'numericMismatches':len(numeric_mismatches),'candidateProtectedLiteralMismatches':len(candidate_protected_mismatches)},ensure_ascii=False,indent=2))
