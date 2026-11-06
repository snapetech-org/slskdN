#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, re, subprocess, sys, unicodedata
from pathlib import Path
OUT=Path(__file__).resolve().parent
CAND=OUT.parent/'candidate-free'
REPO=Path(sys.argv[1]).resolve()
HEAD='8c752c49281418fdd96341ed46f5c321627b625f'; TREE='b930b0d82679e843849e54456f3250e422c4682c'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
TARGETS={
 (1004,'hi'):'अधिकतम समवर्ती लेगेसी क्लाइंट',
 (1007,'ar'):'لا يوجد تشويه',(1007,'hi'):'वार्प प्रभाव नहीं',
 (1008,'ar'):'عدد مرات إعادة المحاولة عبر FTP',(1008,'es'):'Reintentos de FTP',
 (1008,'hi'):'FTP पुनः प्रयासों की संख्या',(1008,'id'):'Jumlah percobaan ulang FTP',
 (1008,'ja'):'FTP 再試行回数',(1008,'ko'):'FTP 재시도 횟수',
 (1008,'zh-Hans'):'FTP 重试次数',(1008,'zh-Hant'):'FTP 重試次數',
 (1012,'ar'):'نظّف السجلات المنتهية الصلاحية',(1012,'de'):'Abgelaufene Einträge bereinigen',
 (1012,'es'):'Limpiar registros caducados',(1012,'fr'):'Nettoyer les entrées expirées',
 (1012,'hi'):'समाप्त हो चुके रिकॉर्ड साफ़ करें',(1012,'id'):'Bersihkan catatan yang kedaluwarsa',
 (1012,'ja'):'期限切れのレコードを整理',(1012,'ko'):'만료된 레코드 정리',
 (1012,'pt-BR'):'Limpar registros expirados',(1012,'vi'):'Dọn dẹp các bản ghi đã hết hạn',
 (1012,'zh-Hans'):'清理已过期的记录',(1012,'zh-Hant'):'清理已過期的記錄',
 (1013,'de'):'Auswirkung: {impact}',(1013,'id'):'Dampak: {impact}',
 (1014,'de'):'Titel',(1014,'hi'):'ट्रैक',(1014,'id'):'lagu',
 (1015,'de'):'Mitgliedschaftseintrag abrufen',
 (1016,'es'):'Clave de la API de YouTube',(1016,'zh-Hans'):'YouTube API 密钥',(1016,'zh-Hant'):'YouTube API 金鑰',
 (1018,'ar'):'جسر',(1018,'id'):'Jembatan',
 (1021,'vi'):'Xóa tác vụ truyền',
 (1022,'ar'):'مدة الاحتفاظ بالملفات المكتملة (بالدقائق)',
 (1022,'de'):'Aufbewahrungsdauer abgeschlossener Dateien (Minuten)',
 (1022,'es'):'Tiempo de retención de archivos completados (min)',
 (1022,'fr'):'Durée de conservation des fichiers terminés (min)',
 (1022,'hi'):'पूरी हो चुकी फ़ाइलों को रखने की अवधि (मिनट)',
 (1022,'id'):'Masa simpan file yang selesai (menit)',
 (1022,'ja'):'完了したファイルの保持時間（分）',(1022,'ko'):'완료된 파일 보존 시간(분)',
 (1022,'pt-BR'):'Tempo de retenção de arquivos concluídos (min)',
 (1022,'vi'):'Thời gian lưu giữ tệp đã hoàn tất (phút)',
 (1022,'zh-Hans'):'已完成文件的保留时间（分钟）',(1022,'zh-Hant'):'已完成檔案的保留時間（分鐘）',
 (1023,'ar'):'اسم مفتاح API',
 (1026,'ar'):'منفذ TCP لشبكة DHT overlay',
 (1026,'es'):'Puerto TCP de la red superpuesta de DHT',
 (1026,'fr'):'Port TCP du réseau superposé DHT',
 (1026,'hi'):'DHT ओवरले नेटवर्क का TCP पोर्ट',
 (1026,'id'):'Port TCP jaringan overlay DHT',
 (1026,'pt-BR'):'Porta TCP da rede de sobreposição DHT',
 (1026,'vi'):'Cổng TCP của mạng overlay DHT',
 (1026,'zh-Hans'):'DHT 覆盖网络 TCP 端口',(1026,'zh-Hant'):'DHT 覆蓋網路 TCP 連接埠',
}
WHY={
 1004:'In the Bridge settings helper, “legacy clients” means older software clients; the Hindi current target calls them customers rather than clients.',
 1007:'This is a visualizer shader-section status, so the label means that the warp effect is absent. The current Arabic reads as a command and the Hindi term means weaving.',
 1008:'This is the accessible label for a numeric FTP retry-count field. These current targets repeat the notion of retrying and attempting; the proposals use a concise retry count.',
 1012:'The button removes expired membership records from local state. The current targets read as a cleanup that expired or ended, rather than an action on expired records.',
 1013:'The playlist-intake summary reports the network impact. These targets mean influence, which is less precise here than the resulting effect or impact.',
 1014:'All three callers count music tracks in directories or releases. These current targets mean railway tracks/traces or use an ambiguous borrowed term rather than music tracks.',
 1015:'The MediaCore section retrieves a membership record. The current German target means a membership card, not a record or entry.',
 1016:'This label identifies a YouTube API credential. The Spanish word order is unnatural for an API key, and the Chinese targets use the word for a physical key rather than a credential.',
 1018:'This is a noun label for the Bridge settings pane. The current Arabic is colloquial for a road bridge and the Indonesian target is a verb (“to bridge”).',
 1021:'The button removes a file transfer from a list without changing its source file. The current Vietnamese phrase commonly means a bank transfer.',
 1022:'The field controls the retention duration, in minutes, for completed files. The current targets largely read as “complete files/minimum” and omit the retention meaning.',
 1023:'This is the label for a policy name field. The current Arabic word order does not form “API key name.”',
 1026:'The Admin Policies field is the TCP port for the DHT overlay network. These targets treat overlay as a visual layer; Indonesian also translates port as a harbor.',
}
ACCEPT={
 1003:'This button starts cleanup of messages older than 30 days; the current targets express that action and time period.',
 1004:'The helper identifies the maximum number of concurrent legacy software clients; the current targets preserve that meaning.',
 1007:'This visualizer debug label indicates that the warp shader section is absent; the current targets communicate that absence.',
 1008:'This numeric field counts FTP retries; the current targets preserve the protocol and retry-count meaning.',
 1012:'The button removes expired membership entries from local state; no unchanged target is retained for this row.',
 1013:'This playlist-intake summary label introduces a localized network-impact value; the current targets preserve the label and placeholder.',
 1014:'These callers count music tracks in directories and releases; the current targets name tracks or songs in context.',
 1015:'This MediaCore section retrieves a membership record; the current targets preserve the retrieval action and record concept.',
 1016:'This label identifies the YouTube API key credential; the current targets preserve the service and credential meaning.',
 1018:'This is the System navigation label for the Bridge settings pane; the current targets use a noun for that feature.',
 1021:'This button removes a transfer from the list; the current targets convey removal of a transfer item.',
 1022:'The field controls retention minutes for completed files; no unchanged target is retained for this row.',
 1023:'This is the label for the API key policy name field; the current targets express the identifier name.',
 1026:'This Admin Policies field labels the TCP port used by the DHT overlay network; the current targets retain overlay networking terminology.',
 1005:'This header introduces warnings about the federation posture; the current targets preserve the warning and federation concepts.',
 1006:'This action stops a search that is still in progress; the current targets communicate that action and state.',
 1009:'This is an empty-state message for the selected log filter; the current targets state that no logs match it.',
 1010:'This is a job identifier in sort and table headers; retaining the standard ID abbreviation is appropriate.',
 1011:'This helper text requires a base URL, token, and path-map to be ready before live execution; the current targets preserve the prerequisites and timing.',
 1017:'This diagnostic reports skipped texture assets and includes both count and filename placeholders; the current targets preserve the meaning and variables.',
 1019:'This tooltip asks the user to publish a descriptor for the ContentID to the DHT and review metadata first; the current targets preserve that sequence and terminology.',
 1020:'This tooltip closes a log preview and returns to retained files; the current targets preserve both actions and the destination.',
 1025:'The label accompanies numeric quality, heuristic, and health scores; the current targets use a score/points term.',
 1027:'This error message reports that federation diagnostics failed to load; the current targets preserve the failure and subject.',
}
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def readj(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def readjl(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def writej(name,o): (OUT/name).write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def writejl(name,rows): (OUT/name).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
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
    subprocess.run([sys.executable,'-B',str(verifier),str(REPO)],check=True)
    cm=readj(CAND/'manifest.json'); csumsha=sha((CAND/'SHA256SUMS.txt').read_bytes()); cmsha=sha((CAND/'manifest.json').read_bytes())
    need((cm['head'],cm['tree'])==(HEAD,TREE) and cm['cellCount']==300,'candidate-free input pin')
    cells=readjl(CAND/'source-current-cells.jsonl'); callers={r['sourceId']:r for r in readjl(CAND/'caller-contexts.jsonl')}
    selected={r['sourceId']:r for r in readjl(CAND/'selected-sources.jsonl')}
    need(len(cells)==300 and len(callers)==len(selected)==25,'primary input coverage')
    backed=[c for c in cells if c.get('callerCount')==1 or c.get('callerCount',0)>1]
    held=[c for c in cells if c.get('callerCount')==0]
    need(len(backed)==288 and len(held)==12,'caller-backed and hash-only input counts')
    need(all(1024!=c['continuationRank'] for c in backed) and all(1024==c['continuationRank'] for c in held),'hash-only source rank boundary')
    rows=[]; corrections=[]; dispositions=collections.Counter(); locale_counts=collections.Counter()
    for c in backed:
        rank=c['continuationRank']; locale=c['locale']; key=(rank,locale); source=c['source']; current=c['currentTarget']; target=TARGETS.get(key)
        source_row=selected[c['sourceId']]; caller=callers[c['sourceId']]
        need(source==source_row['source'] and c['currentTargetSha256']==tsha(current),'primary source/current pin')
        if target is None:
            disposition='accept-current'; candidate=None; rationale=ACCEPT[rank]+' No change is proposed for this cell.'
        else:
            disposition='correction'; candidate=target; rationale=WHY[rank]
        confidence='moderate'
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
    hold_rows=[]
    for c in held:
        # The input is already a hash-only hold. Keep all source and target text omitted.
        need(c.get('sourceTextIncluded') is False and c.get('currentTargetTextIncluded') is False and c.get('callerCount')==0,'hold input text exclusion')
        row={'schemaVersion':1,'reviewPass':'primary','head':HEAD,'tree':TREE,'continuationRank':c['continuationRank'],
          'remainingQueueRank':c['remainingQueueRank'],'sourceIdSha256':c['sourceIdSha256'],'sourceSha256':c['sourceSha256'],
          'locale':c['locale'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],
          'callerCount':0,'disposition':'hash-only-hold','holdReasonClass':'no-pinned-production-localization-caller',
          'sourceTextIncluded':False,'currentTargetTextIncluded':False,'candidateTargetTextIncluded':False,
          'rationale':'No pinned production localization caller exists for this source. Preserve the existing text-free hold; no source or target string was inspected or inferred.',
          'blindReviewUsed':False,'crossReviewUsed':False,'rootAdjudicationPerformed':False}
        hold_rows.append(row)
    rows.sort(key=lambda r:(r['continuationRank'],LOCALES.index(r['locale'])))
    hold_rows.sort(key=lambda r:(r['continuationRank'],LOCALES.index(r['locale'])))
    need(len(rows)==288 and dispositions=={'accept-current':288-len(TARGETS),'correction':len(TARGETS)},'primary disposition counts')
    writejl('primary-review.jsonl',rows); writejl('corrections.jsonl',corrections); writejl('holds-hash-only.jsonl',hold_rows)
    summary={'result':'PASS','artifact':'slskdN PR #409 W1003-W1027 primary semantic review','head':HEAD,'tree':TREE,
      'continuationRankRange':[1003,1027],'remainingQueueRankRange':[903,927],'sourceIds':25,'callerBackedSources':24,'locales':12,
      'reviewedCells':288,'hashOnlyHoldCells':len(hold_rows),'dispositions':dict(dispositions),'correctionCount':len(corrections),
      'acceptCurrentCount':dispositions['accept-current'],'correctionsByLocale':dict(locale_counts),
      'baselineProtectedLiteralMismatches':readj(CAND/'baseline-token-mismatch-summary.json')['mismatchCounts'],
      'candidateTokenMismatches':{},'candidateFreeInputManifestSha256':cmsha,'candidateFreeInputChecksumsSha256':csumsha,
      'blindReviewUsed':False,'crossReviewUsed':False,'rootAdjudicationPerformed':False,'catalogsEdited':False,'testsBuildsScansCiRun':False}
    writej('summary.json',summary)
    (OUT/'README.md').write_text('# slskdN PR #409 W1003–W1027 primary review\n\n'
      'Primary semantic review of 288 caller-backed cells across 24 sources and all 12 locale catalogs at head '+HEAD+' / tree '+TREE+'. The packet records '+str(len(corrections))+' proposed corrections and '+str(dispositions['accept-current'])+' accept-current decisions. The remaining 12 cells for rank 1024 are preserved as text-free hash-only holds because no pinned production localization caller exists.\n\n'
      'This packet contains the primary pass only. Blind review, independent cross-review, root adjudication, catalog application, and readback have not been performed. Per-cell confidence is moderate; no native-speaker or browser signoff is claimed.\n',encoding='utf-8')
    names=sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p.name not in {'manifest.json','SHA256SUMS.txt'})
    manifest={'schemaVersion':1,'repository':'snapetech-org/slskdN','pullRequest':409,'window':'W85','reviewPass':'primary',
      'head':HEAD,'tree':TREE,'candidateFreeInputManifestSha256':cmsha,'candidateFreeInputChecksumsSha256':csumsha,
      'continuationRankRange':[1003,1027],'remainingQueueRankRange':[903,927],'sourceCount':25,'callerBackedSourceCount':24,
      'localeCount':12,'reviewedCellCount':288,'hashOnlyHoldCellCount':len(hold_rows),
      'dispositions':dict(dispositions),'correctionCount':len(corrections),'acceptCurrentCount':dispositions['accept-current'],
      'blindReviewUsed':False,'crossReviewUsed':False,'rootAdjudicationPerformed':False,
      'files':[{'path':n,'sha256':sha((OUT/n).read_bytes()),'bytes':(OUT/n).stat().st_size} for n in names]}
    writej('manifest.json',manifest)
    sums=sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
    (OUT/'SHA256SUMS.txt').write_text(''.join(sha((OUT/n).read_bytes())+'  '+n+'\n' for n in sums),encoding='utf-8')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'reviewedCells':288,'hashOnlyHoldCells':len(hold_rows),
      'corrections':len(corrections),'acceptCurrent':dispositions['accept-current'],'correctionsByLocale':dict(locale_counts),
      'checksummedFiles':len(sums)},indent=2))
if __name__=='__main__': main()
