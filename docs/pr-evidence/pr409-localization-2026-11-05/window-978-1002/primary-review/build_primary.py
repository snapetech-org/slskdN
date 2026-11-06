#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, re, subprocess, sys, unicodedata
from pathlib import Path
OUT=Path(__file__).resolve().parent
CAND=OUT.parent/'candidate-free/input'
REPO=Path(sys.argv[1]).resolve()
HEAD='1c2fe3be2c720693cbcb12d377bf1177804f4e77'; TREE='808501cbc3b6ed873a47d7188189d486f0673f5e'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
TARGETS={
  (978,'hi'):'केवल पूर्वावलोकन',
  (981,'ar'):'راسم الإشارة',(981,'de'):'Signal-Oszilloskop',(981,'id'):'Osiloskop sinyal',(981,'pt-BR'):'Osciloscópio de sinal',
  (983,'vi'):'Chính sách định tuyến chỉ đọc cho mỗi hồ sơ tiếp nhận.',
  (984,'ar'):'لم يتم ربط {title} بعد بإجراء فعلي في الخلفية.',
  (984,'de'):'Für {title} ist noch keine ausführbare Backend-Aktion angebunden.',
  (984,'es'):'{title} aún no tiene una acción de backend funcional conectada.',
  (984,'fr'):'Aucune action réelle côté serveur n’est encore associée à {title}.',
  (984,'hi'):'{title} के लिए अभी तक बैकएंड की कोई वास्तविक कार्रवाई लागू नहीं है।',
  (984,'id'):'{title} belum memiliki tindakan backend yang dapat dijalankan.',
  (984,'ja'):'{title} にはまだ実際に動作するバックエンド処理が接続されていません。',
  (984,'ko'):'{title}에는 아직 실행 가능한 백엔드 작업이 연결되지 않았습니다.',
  (984,'pt-BR'):'{title} ainda não tem uma ação funcional do back-end configurada.',
  (984,'vi'):'{title} chưa được kết nối với thao tác backend nào có thể thực thi.',
  (984,'zh-Hans'):'尚未为 {title} 接入可实际执行的后端操作。',
  (984,'zh-Hant'):'尚未為 {title} 接入可實際執行的後端操作。',
  (987,'id'):'Unduhan dalam antrean',(987,'vi'):'Lượt tải xuống đang chờ',(987,'zh-Hans'):'排队中的下载',(987,'zh-Hant'):'排隊中的下載',
  (988,'ar'):'فاصل تبديل الإعدادات المسبقة الموقّت في MilkDrop الأصلي',
  (988,'de'):'Intervall für zeitgesteuerte Preset-Wechsel in nativem MilkDrop',
  (988,'es'):'Intervalo de cambio de preajustes temporizados de Native MilkDrop',
  (988,'fr'):'Intervalle des changements de préréglage temporisés de MilkDrop natif',
  (988,'hi'):'नेटिव MilkDrop में समयबद्ध प्रीसेट बदलाव का अंतराल',
  (988,'id'):'Interval pergantian preset terjadwal di MilkDrop native',
  (988,'ja'):'Native MilkDrop のプリセット切り替え間隔',
  (988,'ko'):'네이티브 MilkDrop 프리셋 변경 간격',
  (988,'pt-BR'):'Intervalo entre as trocas programadas de predefinição no MilkDrop nativo',
  (988,'vi'):'Khoảng thời gian giữa các lần đổi preset theo lịch trong MilkDrop gốc',
  (988,'zh-Hans'):'Native MilkDrop 定时预设切换间隔',(988,'zh-Hant'):'Native MilkDrop 定時預設切換間隔',
  (989,'ar'):'متطابق',(989,'hi'):'मेल खाता है',(989,'id'):'Cocok',(989,'ja'):'一致',(989,'vi'):'Khớp',
  (990,'ar'):'المجلدات',(990,'hi'):'निर्देशिकाएँ',
  (991,'ar'):'معرّف العميل Spotify (ID)',(991,'hi'):'Spotify क्लाइंट ID',(991,'vi'):'ID ứng dụng khách Spotify',
  (992,'ar'):'النتائج:',(992,'fr'):'Constats :',(992,'hi'):'निष्कर्ष:',(992,'ja'):'所見:',(992,'vi'):'Phát hiện:',
  (993,'ar'):'سرعة الرفع (KiB/s)',(993,'de'):'Uploadgeschwindigkeit (KiB/s)',(993,'es'):'Velocidad de subida (KiB/s)',
  (993,'hi'):'अपलोड गति (KiB/s)',(993,'id'):'Kecepatan unggah (KiB/s)',(993,'ja'):'アップロード速度 (KiB/s)',
  (993,'ko'):'업로드 속도 (KiB/s)',(993,'pt-BR'):'Velocidade de upload (KiB/s)',(993,'vi'):'Tốc độ tải lên (KiB/s)',
  (993,'zh-Hans'):'上传速度 (KiB/s)',(993,'zh-Hant'):'上傳速度 (KiB/s)',
  (996,'ar'):'إرسال رسالة إلى الغرفة',(996,'fr'):'Envoyer un message dans la salle',(996,'hi'):'चैट रूम में संदेश भेजें',
  (996,'id'):'Kirim pesan ke ruang obrolan',(996,'pt-BR'):'Enviar mensagem na sala',(996,'vi'):'Gửi tin nhắn vào phòng chat',
  (997,'ar'):'تقييم المقطع الجاري تشغيله',(997,'de'):'Bewertung des gerade abgespielten Titels',
  (997,'es'):'Valoración de la pista que se está reproduciendo',(997,'fr'):'Évaluation du titre en cours de lecture',
  (997,'hi'):'चल रहे गाने की रेटिंग',(997,'id'):'Rating lagu yang sedang diputar',(997,'ja'):'再生中の曲の評価',
  (997,'ko'):'현재 재생 중인 곡 평점',(997,'pt-BR'):'Avaliação da faixa em reprodução',(997,'vi'):'Đánh giá bài hát đang phát',
  (997,'zh-Hans'):'当前播放曲目的评分',(997,'zh-Hant'):'目前播放曲目的評分',
  (999,'ar'):'فك ترميز ملف مكتبة الخادم هذا إلى MP3 لهذا التشغيل فقط. سيستخدم ذلك CPU الخادم حتى يتوقف التشغيل.',
  (999,'fr'):'Décodez ce fichier de la bibliothèque du serveur en MP3 pour cette lecture uniquement. Cela utilise le CPU du serveur jusqu’à l’arrêt de la lecture.',
  (1000,'es'):'Comprobados:',(1000,'fr'):'Éléments vérifiés :',(1000,'hi'):'जाँचे गए:',(1000,'pt-BR'):'Verificados:',
  (1000,'zh-Hans'):'已检查:',(1000,'zh-Hant'):'已檢查:',
  (1001,'zh-Hans'):'QR 邀请码',(1001,'zh-Hant'):'QR 邀請碼',
  (1002,'ko'):'탐색 새로 고침에 실패했습니다: {message}',
}
WHY={
  978:'The current Hindi phrase is an imperative (“preview only”). This is a status label, so the noun phrase is clearer.',
  981:'The caller labels an oscilloscope-style signal visualizer mode. The current wording can mean signal range or scope; this names the visualization mode.',
  983:'In this acquisition-profile subheading, “mua lại” can imply repurchase. “Tiếp nhận” keeps the routing profile meaning neutral.',
  984:'The current wording calques “wired/live” and sounds like a physical cable or live broadcast. This says the recipe does not yet have an executable backend action connected.',
  987:'The current wording uses an ungrammatical queue phrase. This names downloads that are waiting in the queue.',
  988:'The current phrasing treats the timed preset and interval as a noun stack. This identifies the interval between native MilkDrop preset changes.',
  989:'This caller reports that local and server paths match exactly. The existing word means alignment, sorting, or a coalition instead of a clear match status.',
  990:'The file-browser row counts directory entries. This uses the ordinary UI term for folders/directories.',
  991:'This labels Spotify OAuth client configuration. The proposal keeps the standard ID acronym and identifies the app client field.',
  992:'The caller presents a findings section in a network-health report. This uses the locale’s report term and appropriate colon punctuation.',
  993:'The current wording reads as an imperative to upload data. The caller is a speed-limit field, so this labels the upload rate and preserves KiB/s.',
  996:'The caller is the accessible label for a button that sends a message to a chat room. The current phrasing can mean a message belonging to a room or bedroom.',
  997:'The caller groups star-rating controls for the track currently playing. The current wording treats “now playing” as a game or makes the rating itself play.',
  999:'In Arabic the current verb means decrypt, while this tooltip describes audio decoding. The French wording is also an awkward literal compound; these state that the server file is decoded for this playback only.',
  1000:'The republish summary pairs this label with the number of records checked. The proposal uses a checked-items label rather than a singular or unrelated sense.',
  1001:'This is alt text for a QR invitation image. The current Hans target translates QR without retaining the protected acronym; the Hant target is redundant.',
  1002:'The caller refreshes the Pod Discovery service. The current Korean word means search; this uses the broader discovery/exploration term and preserves the error placeholder.',
}
ACCEPT={
  978:'The green Automation Center badge marks a recipe that is preview-only; the current target conveys that status.',
  979:'The caller maps discovery-graph node type “seed” to its root/start node label; the current wording preserves that role.',
  980:'The two Wishlist popup callers use this as the action that hides expanded search results; the current targets express that action.',
  981:'The visualizer tile mode label distinguishes the signal display from album art and spectrum bars; the current target names that mode.',
  982:'The user-note tooltip promises to close without saving edits; the current target preserves the action and ownership.',
  983:'The Source Providers subheading describes a read-only routing policy for each acquisition profile; the current targets retain those concepts.',
  984:'The Automation Center message tells the user no backend action is available for the recipe yet; the current target communicates that limitation.',
  985:'The room-join empty state asks the user to change the search term; the current target is clear and direct.',
  986:'The port-forwarding tooltip explains loopback-only setup through a VPN-capable pod and use from a local app; the current target preserves those constraints.',
  987:'The Metrics table label counts downloads that are waiting in the queue; the current target is concise and fits a metric label.',
  988:'The accessible label names the interval control for timed Native MilkDrop preset changes; the current target communicates the setting.',
  989:'The integration diagnostic says the local and server paths match; the current target reads as an aligned status.',
  990:'The browse result shows counts of directories and files; the current target names directory entries.',
  991:'The integration form labels the Spotify client ID field; the current target names the client identifier.',
  992:'The network-health score report introduces its findings list; the current target supplies an appropriate section heading.',
  993:'The Admin Policies form labels an upload rate in KiB/s; the current target is a recognizable field label.',
  994:'The discovery graph exports a depth value with the {depth} placeholder; the current target preserves the label and variable.',
  995:'The MediaCore moderation form suggests this ban reason; the current target preserves the community-rules meaning.',
  996:'The room composer button sends a message to the room; the current target is understandable as a send action.',
  997:'The player groups controls for the rating of the current track; the current target signals a playback-related rating.',
  998:'The library-health table uses this as its count-column heading; the current target is a concise count label.',
  999:'The player tooltip explains server-side MP3 decoding for this playback and its CPU cost; the current target preserves the scoped behavior.',
  1000:'The republish results report the number checked; the current target indicates completed checks.',
  1001:'The Contacts image alternative text identifies the QR invitation code; the current target is understandable in the pinned context.',
  1002:'The MediaCore toast reports a failed Pod Discovery refresh and includes the backend error; the current target preserves the failure and placeholder.',
}
HIGH={(978,'hi'),(989,'hi'),(989,'ja'),(990,'ar'),(990,'hi'),(991,'ar'),(991,'hi'),(993,'ar'),(993,'es'),(993,'hi'),(993,'id'),(993,'ja'),(993,'ko'),(993,'pt-BR'),(993,'vi'),(993,'zh-Hans'),(993,'zh-Hant'),(996,'fr'),(996,'pt-BR'),(996,'vi'),(997,'ar'),(997,'de'),(997,'es'),(997,'fr'),(997,'hi'),(997,'id'),(997,'ja'),(997,'ko'),(997,'pt-BR'),(997,'vi'),(997,'zh-Hans'),(997,'zh-Hant'),(999,'ar'),(1000,'fr'),(1001,'zh-Hans'),(1001,'zh-Hant')}

def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def readj(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def readjl(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def writej(name,o): (OUT/name).write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def writejl(name,rows): (OUT/name).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
def verify_sums(root):
    seen={}
    for line in (root/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1); need(n not in seen and sha((root/n).read_bytes())==h,'checksum '+n); seen[n]=h
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    need(actual==set(seen),'checksum inventory')
    return seen
def token_data(source,target):
    placeholders=lambda s:collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s))
    tags=lambda s:collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',s))
    nums=lambda s:[''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in t) for t in re.findall(r'\d+',s)]
    protected=lambda s:sorted(set(re.findall(r'\b[A-Z][A-Z0-9]{1,}\b',s))|{x for x in ('slskdN','PodCore','Wishlist','soulfind','FFmpeg','Lidarr') if x in s})
    sp,tp=placeholders(source),placeholders(target); st,tt=tags(source),tags(target); sn,tn=nums(source),nums(target); sl=protected(source)
    return {'placeholderParity':sp==tp,'markupParity':st==tt,'numericTokensPreserved':all(tn.count(x)>=n for x,n in collections.Counter(sn).items()),
      'missingProtectedLiterals':[x for x in sl if x not in target],'protectedLiteralsPreserved':all(x in target for x in sl)}
def need(ok,msg):
    if not ok: raise SystemExit('REFUSED: '+msg)
def main():
    need({p.name for p in OUT.iterdir()}<={'build_primary.py','verify_primary.py'},'primary output is not empty')
    verifier=CAND/'verify_candidate_free.py'; need(verifier.is_file(),'candidate-free verifier')
    subprocess.run([sys.executable,str(verifier),str(REPO)],check=True)
    cm=readj(CAND/'manifest.json'); csumsha=sha((CAND/'SHA256SUMS.txt').read_bytes()); cmsha=sha((CAND/'manifest.json').read_bytes())
    need((cm['head'],cm['tree'])==(HEAD,TREE) and cm['cellCount']==300,'candidate-free input pin')
    cells=readjl(CAND/'source-current-cells.jsonl'); callers={r['sourceId']:r for r in readjl(CAND/'caller-contexts.jsonl')}
    selected={r['sourceId']:r for r in readjl(CAND/'selected-sources.jsonl')}
    need(len(cells)==300 and len(callers)==len(selected)==25,'primary input coverage')
    rows=[]; corrections=[]; dispositions=collections.Counter(); locale_counts=collections.Counter()
    for c in cells:
        rank=c['continuationRank']; locale=c['locale']; key=(rank,locale); source=c['source']; current=c['currentTarget']; target=TARGETS.get(key)
        source_row=selected[c['sourceId']]; caller=callers[c['sourceId']]
        need(source==source_row['source'] and c['currentTargetSha256']==tsha(current),'primary source/current pin')
        if target is None:
            disposition='accept-current'; candidate=None; rationale=ACCEPT[rank]+' No change is proposed for this cell.'; confidence='moderate'
        else:
            disposition='correction'; candidate=target; rationale=WHY[rank]; confidence='high' if key in HIGH else 'moderate'
        current_token=token_data(source,current); candidate_token=token_data(source,candidate) if candidate is not None else None
        if candidate is not None:
            need(candidate!='' and candidate!=current,'empty or no-op correction '+str(key))
            need(candidate_token['placeholderParity'] and candidate_token['markupParity'] and candidate_token['numericTokensPreserved'] and candidate_token['protectedLiteralsPreserved'],'candidate token mismatch '+str(key))
            candidate_sha=tsha(candidate)
        else: candidate_sha=None
        row={'schemaVersion':1,'reviewPass':'primary','continuationRank':rank,'remainingQueueRank':c['remainingQueueRank'],
          'sourceId':c['sourceId'],'sourceSha256':c['sourceSha256'],'locale':locale,'source':source,'sourceTextIncluded':True,
          'currentTarget':current,'currentTargetSha256':c['currentTargetSha256'],'currentTargetTextIncluded':True,
          'candidateTarget':candidate,'candidateTargetSha256':candidate_sha,'candidateTargetTextIncluded':candidate is not None,
          'disposition':disposition,'rationale':rationale,'confidence':confidence,'head':HEAD,'tree':TREE,
          'catalogPath':c['catalogPath'],'catalogFileSha256':c['catalogFileSha256'],'catalogGitBlob':c['catalogGitBlob'],
          'callerContextSha256':c['callerContextSha256'],'callerCount':c['callerCount'],'callerRefs':caller['callers'],
          'tokenCheck':{'current':current_token,'candidate':candidate_token},'blindReviewUsed':False,'crossReviewUsed':False,
          'rootAdjudicationPerformed':False}
        rows.append(row); dispositions[disposition]+=1; locale_counts[locale]+=disposition=='correction'
        if candidate is not None:
            corrections.append({k:row[k] for k in ('continuationRank','remainingQueueRank','sourceId','sourceSha256','locale','currentTargetSha256','candidateTarget','candidateTargetSha256','rationale','confidence','callerContextSha256')})
    need(len(TARGETS)==len(corrections),'proposal map/output coverage mismatch')
    need(len(rows)==300 and dispositions=={'accept-current':300-len(TARGETS),'correction':len(TARGETS)},'primary disposition counts')
    writejl('primary-review.jsonl',rows); writejl('corrections.jsonl',corrections)
    summary={'result':'PASS','artifact':'slskdN PR #409 W978-W1002 primary semantic review','head':HEAD,'tree':TREE,
      'continuationRankRange':[978,1002],'remainingQueueRankRange':[878,902],'sourceIds':25,'locales':12,'cells':300,
      'dispositions':dict(dispositions),'correctionCount':len(corrections),'acceptCurrentCount':dispositions['accept-current'],
      'correctionsByLocale':dict(locale_counts),'baselineProtectedLiteralMismatches':readj(CAND/'baseline-token-mismatch-summary.json')['mismatchCounts'],
      'candidateTokenMismatches':{},'candidateFreeInputManifestSha256':cmsha,'candidateFreeInputChecksumsSha256':csumsha,
      'blindReviewUsed':False,'crossReviewUsed':False,'rootAdjudicationPerformed':False,'catalogsEdited':False,'testsBuildsScansCiRun':False}
    writej('summary.json',summary)
    (OUT/'README.md').write_text('# slskdN PR #409 W978–W1002 primary review\n\n'
      'Primary semantic review of 300 cells for 25 source IDs across all 12 locale catalogs. Input is the sealed candidate-free packet at head '+HEAD+' / tree '+TREE+'. The review recorded '+str(len(corrections))+' proposed corrections and '+str(dispositions['accept-current'])+' accept-current decisions.\n\n'
      'This packet contains the primary pass only. Blind review, independent cross-review, root adjudication, catalog application, and readback have not been performed. Primary confidence is moderate overall; per-cell confidence is recorded. No native-speaker or browser signoff is claimed.\n',encoding='utf-8')
    names=sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p.name not in {'manifest.json','SHA256SUMS.txt'})
    manifest={'schemaVersion':1,'repository':'snapetech-org/slskdN','pullRequest':409,'window':'W84','reviewPass':'primary',
      'head':HEAD,'tree':TREE,'candidateFreeInputManifestSha256':cmsha,'candidateFreeInputChecksumsSha256':csumsha,
      'continuationRankRange':[978,1002],'remainingQueueRankRange':[878,902],'sourceCount':25,'localeCount':12,'cellCount':300,
      'dispositions':dict(dispositions),'correctionCount':len(corrections),'acceptCurrentCount':dispositions['accept-current'],
      'blindReviewUsed':False,'crossReviewUsed':False,'rootAdjudicationPerformed':False,
      'files':[{'path':n,'sha256':sha((OUT/n).read_bytes()),'bytes':(OUT/n).stat().st_size} for n in names]}
    writej('manifest.json',manifest)
    sums=sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
    (OUT/'SHA256SUMS.txt').write_text(''.join(sha((OUT/n).read_bytes())+'  '+n+'\n' for n in sums),encoding='utf-8')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'cells':300,'corrections':len(corrections),
      'acceptCurrent':dispositions['accept-current'],'correctionsByLocale':dict(locale_counts),'checksummedFiles':len(sums)},indent=2))
if __name__=='__main__': main()
