#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, re, unicodedata
from pathlib import Path

OUT=Path(__file__).resolve().parent
INPUT=OUT.parent/'candidate-free'
HEAD='ba692c15ca54942108cc9da37757f585969e6173'
TREE='27c09a8fe24030f5bb0995d809794a9e4829dc64'
EXPECTED_INPUT_SUMS='2170ea00e2bcb8c5c79f23f86ce5acef8a31f4270813e222fea7e2f171cec1be'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
FIRST,LAST=1053,1077
TEXT_KEYS={'source','sourceText','target','currentTarget','proposedTarget','proposedTargetText','candidateTarget','reviewTarget','rationale','reason','before','after','actualValue','expectedValue'}
SPECIAL=['FPS','FTP','IP','Mesh','Soulseek','YAML','NzbGet','KeepHistory','PodCore','slskdN']

def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def readjl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def writej(name,o): (OUT/name).write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def writejl(name,rows): (OUT/name).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
def need(ok,msg):
    if not ok: raise SystemExit('REFUSED: '+msg)

# Corrections are limited to a few strings where the pinned current wording is
# ambiguous, misleading, or unidiomatic in the caller's UI context. All other
# cells retain the current locale value after semantic/token review.
REVISIONS={
(1053,'ar'):('أظهر جميع الإعدادات المسبقة الأصلية المستوردة.','Clarifies that these are presets, not general settings.'),
(1054,'es'):('Prohibir miembros y cambiar roles publica el estado de membresía del pod y del peer seleccionados. Verifique el registro de membresía actual antes de aplicar cambios.','Keeps the domain terms pod and peer distinct from a generic group and pairing.'),
(1054,'hi'):('सदस्यों पर प्रतिबंध लगाना और भूमिकाएँ बदलना चयनित Pod और समकक्ष नोड की सदस्यता स्थिति प्रकाशित करता है। बदलाव लागू करने से पहले वर्तमान सदस्यता रिकॉर्ड की पुष्टि करें।','Replaces “coworker” with the correct peer-node sense and retains the Pod entity.'),
(1054,'fr'):('Le bannissement de membres et le changement de rôles publient l’état d’adhésion du pod et du pair sélectionnés. Vérifiez le registre actuel des membres avant d’appliquer les changements.','Uses natural wording for banning and a membership record while retaining pod/peer meaning.'),
(1054,'vi'):('Việc cấm thành viên và thay đổi vai trò sẽ công bố trạng thái thành viên của Pod và peer đã chọn. Hãy xác minh bản ghi thành viên hiện tại trước khi áp dụng thay đổi.','Retains the Pod and peer concepts instead of flattening the pod into a generic group.'),
(1054,'zh-Hans'):('封禁成员和更改角色会发布所选 Pod 与对等节点的成员状态。应用更改前，请先核实当前的成员记录。','Uses a precise peer-node term and preserves Pod as the domain entity.'),
(1054,'zh-Hant'):('封鎖成員和變更角色會發布所選 Pod 與對等節點的成員狀態。套用變更前，請先核實目前的成員記錄。','Uses a precise peer-node term and preserves Pod as the domain entity.'),
(1055,'ar'):('عدد الطلبات المسموح بها لبوابة Mesh','Makes “permits” the number of allowed requests, not access permissions.'),
(1055,'de'):('Zulässige Anfragen für das Mesh-Gateway','Clarifies that permits are allowed requests in a rate-limit control.'),
(1055,'es'):('Solicitudes permitidas para la pasarela Mesh','Clarifies that permits are allowed requests, not user permissions.'),
(1055,'fr'):('Requêtes autorisées pour la passerelle Mesh','Clarifies that permits are allowed requests, not access permissions.'),
(1055,'hi'):('Mesh गेटवे के लिए अनुमत अनुरोधों की संख्या','Clarifies that the value is a request allowance.'),
(1055,'id'):('Jumlah permintaan yang diizinkan untuk gateway Mesh','Clarifies that the value is an allowed-request count.'),
(1055,'ja'):('Mesh ゲートウェイで許可するリクエスト数','Clarifies that permits are the request count allowed by the rate limit.'),
(1055,'ko'):('Mesh 게이트웨이의 허용 요청 수','Clarifies that permits are allowed requests, not permissions.'),
(1055,'pt-BR'):('Solicitações permitidas para o gateway Mesh','Clarifies that permits are allowed requests, not access permissions.'),
(1055,'vi'):('Số yêu cầu được phép qua cổng Mesh','Clarifies that permits are allowed requests, not permissions.'),
(1055,'zh-Hans'):('Mesh 网关允许的请求数','Clarifies that permits are allowed requests, not access permissions.'),
(1055,'zh-Hant'):('Mesh 閘道允許的請求數','Clarifies that permits are allowed requests, not access permissions.'),
(1058,'ar'):('التحقق من الواصف','Uses “descriptor” rather than “description.”'),
(1058,'vi'):('Xác minh bộ mô tả','Uses the technical “descriptor” sense rather than a generic description.'),
(1059,'ar'):('المصدر: {provenance}.','Preserves the placeholder and closing sentence punctuation.'),
(1059,'de'):('Quelle: {provenance}.','Preserves the placeholder and closing sentence punctuation.'),
(1059,'id'):('Sumber: {provenance}.','Uses natural colon spacing and keeps the closing punctuation.'),
(1059,'ja'):('ソース: {provenance}。','Uses Japanese punctuation while preserving the placeholder.'),
(1059,'zh-Hans'):('来源：{provenance}。','Uses Chinese punctuation while preserving the placeholder.'),
(1059,'zh-Hant'):('來源：{provenance}。','Uses Chinese punctuation while preserving the placeholder.'),
(1062,'zh-Hans'):('IP，','Corrects the existing “intellectual property” sense; this count refers to tracked IP addresses.'),
(1062,'zh-Hant'):('IP，','Corrects the existing “intellectual property” sense; this count refers to tracked IP addresses.'),
(1062,'hi'):('IP,','Keeps the technical IP abbreviation intact for the tracked-address count.'),
(1063,'zh-Hans'):('还没有合集','Uses the app’s collection sense rather than “favorites.”'),
(1063,'zh-Hant'):('目前還沒有合集','Uses the app’s collection sense rather than “favorites.”'),
(1064,'pt-BR'):('Entrar/Criar #','Uses the concise button verbs “join/create” before the room-name marker.'),
(1066,'ar'):('غرف دردشة Soulseek المطابقة','Makes clear these are matching chat rooms.'),
(1066,'es'):('Salas de chat de Soulseek que coinciden','Uses “salas de chat” for Soulseek rooms and a natural matching-results label.'),
(1066,'fr'):('Salons de discussion Soulseek correspondants','Uses “salons de discussion” for chat rooms, not physical rooms.'),
(1066,'hi'):('मेल खाते Soulseek चैट रूम','Clarifies that these are Soulseek chat rooms.'),
(1066,'id'):('Ruang obrolan Soulseek yang cocok','Clarifies that these are chat rooms, not physical rooms.'),
(1066,'ja'):('一致する Soulseek チャットルーム','Clarifies that these are Soulseek chat rooms.'),
(1066,'ko'):('일치하는 Soulseek 채팅방','Replaces the hotel-room sense with the Soulseek chat-room term.'),
(1066,'vi'):('Các phòng chat Soulseek phù hợp','Uses a natural matching label and clarifies the chat-room meaning.'),
(1066,'zh-Hans'):('匹配的 Soulseek 聊天室','Uses the matching-results sense and names the chat-room concept.'),
(1066,'zh-Hant'):('相符的 Soulseek 聊天室','Uses the matching-results sense and names the chat-room concept.'),
(1067,'ja'):('実行契約の準備完了','Corrects the existing “agreement contract” wording to the software execution-contract status.'),
(1067,'vi'):('Hợp đồng thực thi đã sẵn sàng','Corrects “construction contract” to the software execution-contract status.'),
(1067,'zh-Hans'):('执行契约已就绪','Uses the software-contract sense rather than a general legal contract.'),
(1067,'zh-Hant'):('執行契約已就緒','Uses the software-contract sense rather than a general legal contract.'),
(1069,'ar'):('تمكين الرفع عبر FTP بعد اكتمال التنزيل','Makes the timing clear: FTP uploads are enabled after downloads finish.'),
(1069,'es'):('Habilitar las cargas por FTP cuando se completen las descargas','Clarifies that the downloads complete before FTP upload handling.'),
(1069,'hi'):('डाउनलोड पूरा होने के बाद FTP अपलोड सक्षम करें','Clarifies that FTP uploads happen after the download completes.'),
(1069,'id'):('Aktifkan unggahan FTP setelah unduhan selesai','Clarifies that FTP uploads happen after the download completes.'),
(1069,'ja'):('ダウンロード完了後の FTP アップロードを有効にする','Clarifies that FTP uploads are enabled after a download completes.'),
(1069,'ko'):('다운로드 완료 후 FTP 업로드 활성화','Clarifies that FTP uploads are enabled after the download completes.'),
(1069,'pt-BR'):('Habilitar uploads por FTP após a conclusão dos downloads','Clarifies that FTP uploads follow completed downloads.'),
(1069,'vi'):('Bật tải lên qua FTP sau khi tải xuống hoàn tất','Clarifies that FTP uploads follow completed downloads.'),
(1069,'zh-Hans'):('启用下载完成后的 FTP 上传','Clarifies that FTP uploads follow completed downloads.'),
(1069,'zh-Hant'):('啟用下載完成後的 FTP 上傳','Clarifies that FTP uploads follow completed downloads.'),
(1070,'de'):('Das aktuelle YAML validieren und in der Remote-Konfigurationsdatei speichern.','Uses natural German article/case and preserves the YAML term.'),
(1075,'ja'):('受信','Uses the concise inbound-direction label for the policy setting.'),
(1075,'vi'):('Chiều vào','Uses the network-direction sense of incoming.'),
(1076,'ar'):('; مقبول للاستخدام المحلي','Avoids an unsupported feminine agreement while preserving the status fragment.'),
(1076,'vi'):('; được chấp nhận để dùng cục bộ','Expresses local-instance use rather than geographic locality.'),
}

SOURCE_NOTES={
1053:'show every imported native visualizer preset',
1054:'warn that member bans and role changes publish pod/peer membership state and advise verification first',
1055:'name the allowed-request count for the Mesh gateway rate limit',
1056:'choose a sharing group and permissions to grant collection access',
1057:'label a 30-frames-per-second option',
1058:'name verification of a technical descriptor',
1059:'label the provenance value with a format placeholder',
1060:'report a wishlist-loading error with a message placeholder',
1061:'filter by file extension and retain the four examples',
1062:'label a count of tracked IP addresses',
1063:'show the empty state for collections',
1064:'join or create a room identified by the following # name',
1065:'describe applying a palette placeholder to the dark theme',
1066:'label matching Soulseek chat-room results',
1067:'show that the adapter execution contract is ready',
1068:'label the action that analyzes text similarity',
1069:'enable FTP upload handling after completed downloads',
1070:'describe validating the current YAML and saving the remote configuration',
1071:'label a count of file hashes',
1072:'list the allowed port range for forwarding',
1074:'label the first input as a text string',
1075:'label the incoming direction of a policy setting',
1076:'append the status that a source is accepted for local use',
}

def token_audit(source,target):
    ph=lambda s:collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s))
    tags=lambda s:collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',s))
    nums=lambda s:[''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in t) for t in re.findall(r'\d+',s)]
    protected=lambda s:sorted(set(re.findall(r'\b[A-Z][A-Z0-9]{1,}\b',s))|{x for x in ('slskdN','PodCore','Wishlist','soulfind','FFmpeg','Lidarr') if x in s})
    src_ph,tgt_ph=ph(source),ph(target); src_tag,tgt_tag=tags(source),tags(target); src_nums,tgt_nums=nums(source),nums(target)
    src_protected=protected(source); missing=[x for x in src_protected if x not in target]
    explicit=[x for x in SPECIAL if x in source]
    if '#' in source: explicit.append('#')
    extensions=[x for x in ('flac','mp3','wav','m4a') if re.search(r'\b'+x+r'\b',source)]
    explicit += extensions
    explicit=list(dict.fromkeys(explicit))
    missing_explicit=[x for x in explicit if x not in target]
    return {'placeholders':{'source':sorted(src_ph.elements()),'target':sorted(tgt_ph.elements()),'matches':src_ph==tgt_ph},
      'markup':{'source':sorted(src_tag.elements()),'target':sorted(tgt_tag.elements()),'matches':src_tag==tgt_tag},
      'numbers':{'source':src_nums,'target':tgt_nums,'sourcePreserved':all(tgt_nums.count(x)>=n for x,n in collections.Counter(src_nums).items())},
      'protectedLiterals':{'source':src_protected,'target':protected(target),'missing':missing},
      'explicitDomainLiterals':{'source':explicit,'missing':missing_explicit}}

def main():
    need(OUT.is_dir() and {p.name for p in OUT.iterdir()}=={'build_primary_review.py','verify_primary_review.py'},'output directory is not pristine')
    input_sums={}
    for line in (INPUT/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1)
        need(n not in input_sums and (INPUT/n).is_file() and sha((INPUT/n).read_bytes())==h,'candidate-free input checksum '+n)
        input_sums[n]=h
    actual={p.relative_to(INPUT).as_posix() for p in INPUT.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    need(actual==set(input_sums),'candidate-free input checksum inventory')
    sums_raw=(INPUT/'SHA256SUMS.txt').read_bytes(); need(sha(sums_raw)==EXPECTED_INPUT_SUMS,'candidate-free checksum-list digest')
    im=readj(INPUT/'manifest.json')
    need((im.get('head'),im.get('tree'),im.get('window'),im.get('continuationRankRange'),im.get('remainingQueueRankRange'),im.get('cellCount'),im.get('candidateFree'),im.get('reviewDecisionsIncluded'),im.get('proposedTargetsIncluded'))==(HEAD,TREE,'W87',[1053,1077],[953,977],300,True,False,False),'candidate-free manifest pin')
    cells=readjl(INPUT/'source-current-cells.jsonl'); callers=readjl(INPUT/'caller-contexts.jsonl')
    need(len(cells)==300 and len(callers)==25,'candidate-free cell/caller coverage')
    caller_by={r['sourceId']:r for r in callers}; need(len(caller_by)==25,'caller identity coverage')
    ledger=[]; counts=collections.Counter(); by_rank=collections.defaultdict(list)
    for c in cells:
        rank,loc,sid=c['continuationRank'],c['locale'],c['sourceId']; call=caller_by[sid]
        backed=call['productionCallerCount']>0
        need(c['callerCount']==call['productionCallerCount'] and c['callerContextSha256']==call['callerContextSha256'],'caller pin '+sid)
        row={'window':'W87','head':HEAD,'tree':TREE,'continuationRank':rank,'remainingQueueRank':c['remainingQueueRank'],
          'sourceId':sid,'sourceIdSha256':c['sourceIdSha256'],'sourceSha256':c['sourceSha256'],'locale':loc,
          'callerBacked':backed,'callerCount':call['productionCallerCount'],'callerContextSha256':call['callerContextSha256'],
          'sourceTextIncluded':backed,'currentTargetTextIncluded':backed,'currentTargetSha256':c['currentTargetSha256']}
        if not backed:
            need(c['candidateFreeHold'] is True and 'source' not in c and 'currentTarget' not in c,'callerless input is not text-free')
            row.update({'decision':'hold-hash-only','proposalIncluded':False,'proposedTargetSha256':None,
              'rationale':'No pinned production localization caller; preserve this cell as a hash-only hold and emit no translation text.',
              'confidence':'high','tokenAuditIncluded':False,'sourceTextIncluded':False,'currentTargetTextIncluded':False})
            counts['hold']+=1
        else:
            need(c.get('candidateFreeHold') is False and 'source' in c and 'currentTarget' in c,'caller-backed cell missing text')
            source=c['source']; old=c['currentTarget']; override=REVISIONS.get((rank,loc))
            target,rationale=(override[0],override[1]) if override else (old,'The current localized wording accurately conveys '+SOURCE_NOTES[rank]+'; retain it after checking the exact caller and technical tokens.')
            audit=token_audit(source,target)
            need(audit['placeholders']['matches'] and audit['markup']['matches'] and audit['numbers']['sourcePreserved'] and not audit['protectedLiterals']['missing'] and not audit['explicitDomainLiterals']['missing'],'token preservation failure '+str((rank,loc))+': '+json.dumps(audit,ensure_ascii=False))
            decision='revise' if override else 'retain-current'
            row.update({'source':source,'currentTarget':old,'proposedTarget':target,'proposedTargetSha256':tsha(target),
              'decision':decision,'proposalIncluded':True,'rationale':rationale,'confidence':'low' if rank in (1054,1055,1067,1076) else 'moderate',
              'tokenAudit':audit,'tokenAuditSha256':sha(canon(audit)),'tokenChecksPass':True})
            counts[decision]+=1; counts['proposal']+=1
        ledger.append(row); by_rank[rank].append(row)
    need(counts['proposal']==276 and counts['hold']==24,'disposition total')
    for rank,rows in by_rank.items():
        need(len(rows)==12,'locale coverage '+str(rank))
        need((len(rows)==12 and all(x['callerBacked'] for x in rows)) or (len(rows)==12 and all(not x['callerBacked'] for x in rows)),'source caller class is not uniform '+str(rank))
    prior_holds=readjl(INPUT/'prior-held-cell-reattestation-hash-only.jsonl')
    new_holds=readjl(INPUT/'window-holds-hash-only.jsonl')
    need(len(prior_holds)==433 and len(new_holds)==24,'active hold lineage counts')
    need(all(not any(k in TEXT_KEYS for k in r) for r in prior_holds+new_holds),'hold output text disclosure')
    writejl('primary-review-ledger.jsonl',ledger)
    writejl('prior-active-holds-hash-only.jsonl',prior_holds)
    writejl('current-window-holds-hash-only.jsonl',new_holds)
    writej('input-attestation.json',{'candidateFreePacket':INPUT.relative_to(OUT.parent).as_posix(),'head':HEAD,'tree':TREE,'window':'W87',
      'candidateFreeChecksumListSha256':sha(sums_raw),'candidateFreeChecksummedFiles':len(input_sums),
      'manifestSha256':sha((INPUT/'manifest.json').read_bytes()),'cellFileSha256':sha((INPUT/'source-current-cells.jsonl').read_bytes()),
      'callerFileSha256':sha((INPUT/'caller-contexts.jsonl').read_bytes()),'reviewedNoOtherProposalPackets':True})
    summary={'result':'PASS','artifact':'slskdN PR #409 W1053-W1077 primary semantic review','window':'W87',
      'head':HEAD,'tree':TREE,'continuationRankRange':[FIRST,LAST],'remainingQueueRankRange':[953,977],
      'sourceCount':25,'localeCount':12,'cellCount':300,'callerBackedSources':23,'callerlessSources':2,
      'callerBackedCells':276,'proposalCells':276,'revisedCells':counts['revise'],'retainedCurrentCells':counts['retain-current'],
      'hashOnlyHolds':counts['hold'],'priorActiveHashOnlyHoldsReattested':len(prior_holds),
      'resultingActiveHashOnlyHolds':len(prior_holds)+len(new_holds),'confidenceCounts':dict(collections.Counter(r['confidence'] for r in ledger)),
      'allCallerBackedTokenChecksPass':True,'nativeSpeakerApproval':False,'productEdited':False,'testsBuildsScansCiRun':False,
      'nextBoundary':readj(INPUT/'selection-and-boundary.json')['nextUnselected']}
    writej('summary.json',summary)
    (OUT/'README.md').write_text('# slskdN PR #409 W1053–W1077 primary semantic review\n\n'
      'Pinned to candidate-free input at head '+HEAD+' / tree '+TREE+' (W87; source ranks 1053–1077, remaining ranks 953–977). The review covers all 300 cells: 276 caller-backed proposals (retaining or revising current values) and 24 callerless hash-only holds. It reattests 433 prior holds, for 457 active hash-only holds after this window.\n\n'
      'The ledger records current and proposed target hashes, exact caller-context hashes, rationale, confidence, and placeholder/markup/numeric/protected-literal audits. This machine review is not native-speaker approval. No repository or product files were changed.\n',encoding='utf-8')
    files=sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p.name not in {'manifest.json','SHA256SUMS.txt'})
    manifest={'schemaVersion':1,'repository':'snapetech-org/slskdN','pullRequest':409,'window':'W87','role':'primary-semantic-review',
      'head':HEAD,'tree':TREE,'candidateFreeInputChecksumListSha256':sha(sums_raw),'continuationRankRange':[FIRST,LAST],
      'remainingQueueRankRange':[953,977],'sourceCount':25,'localeCount':12,'cellCount':300,'callerBackedCells':276,
      'proposalCells':276,'revisedCells':counts['revise'],'retainedCurrentCells':counts['retain-current'],'hashOnlyHolds':24,
      'priorActiveHashOnlyHoldsReattested':433,'resultingActiveHashOnlyHolds':457,'nativeSpeakerApproval':False,
      'files':[{'path':n,'sha256':sha((OUT/n).read_bytes()),'bytes':(OUT/n).stat().st_size} for n in files]}
    writej('manifest.json',manifest)
    names=sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
    (OUT/'SHA256SUMS.txt').write_text(''.join(sha((OUT/n).read_bytes())+'  '+n+'\n' for n in names),encoding='utf-8')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'cells':len(ledger),'proposalCells':counts['proposal'],
      'revisedCells':counts['revise'],'retainedCurrentCells':counts['retain-current'],'hashOnlyHolds':counts['hold'],
      'priorHolds':len(prior_holds),'activeHoldsAfter':len(prior_holds)+len(new_holds),'nextBoundary':summary['nextBoundary'],
      'checksummedFiles':len(names)},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
