#!/usr/bin/env python3
"""Build the W55 machine-assisted primary semantic review from sealed input."""
from pathlib import Path
import collections, hashlib, json, re, subprocess
OUT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w55-primary-20261103')
INPUT=OUT/'input'; PRIMARY=OUT/'primary'
HEAD='6a46b8f1dc87d899308fee141fa0db392e49e098'; TREE='a22e9a896aae12aa89a1502d9748b12816d491ed'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PH=re.compile(r'\{[^{}]+\}'); MARKUP=re.compile(r'</?[A-Za-z][^>]*>'); NUMBER=re.compile(r'(?<![A-Za-z])\d+(?:[.,]\d+)?%?(?![A-Za-z])')
def sha(v): return hashlib.sha256(v.encode('utf-8') if isinstance(v,str) else v).hexdigest()
def read_jsonl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def write_json(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_jsonl(p,rows): p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
def verify_manifest(d,name):
  p=d/name; rows=[]
  for line in p.read_text(encoding='utf-8').splitlines():
    if not line.strip(): continue
    h,rel=line.split(None,1); rel=rel.strip().lstrip('*'); actual=sha((d/rel).read_bytes()); rows.append({'path':rel,'matches':h==actual})
  assert rows and all(x['matches'] for x in rows),(p,rows)
  return rows
def write_manifest(d,name):
  p=d/name; lines=[]
  for f in sorted(x for x in d.rglob('*') if x.is_file() and x!=p): lines.append(f'{sha(f.read_bytes())}  {f.relative_to(d).as_posix()}')
  p.write_text('\n'.join(lines)+'\n',encoding='utf-8')
assert INPUT.is_dir() and not PRIMARY.exists()
input_checks=verify_manifest(INPUT,'PACKET-SHA256SUMS.txt')
att=json.loads((INPUT/'head-tree-attestation.json').read_text(encoding='utf-8'))
selection=json.loads((INPUT/'selection-and-boundary.json').read_text(encoding='utf-8'))
assert att['head']==HEAD and att['tree']==TREE and selection['inputContainsCandidates'] is False
cells=read_jsonl(INPUT/'source-current-cells.jsonl'); callers=read_jsonl(INPUT/'caller-contexts.jsonl')
assert len(cells)==300 and len(callers)==25
assert [(x['continuationRank'],x['locale']) for x in cells]==[(r,l) for r in range(276,301) for l in LOCALES]
caller_by_id={x['sourceId']:x for x in callers}

# Exact proposed winners. All unlisted non-held cells accept the current value.
PROPOSALS={
 (276,'zh-Hans'):('黄色','refinement','The pinned caller uses this as a color option. Remove 的, which turns the color noun into an adjectival form.'),
 (276,'zh-Hant'):('黃色','refinement','The pinned caller uses this as a color option. Remove 的, which turns the color noun into an adjectival form.'),
 (279,'ar'):('عمليات التحقق:','correction','This is a section heading above readiness checks. The current wording is singular and has a stray space before the colon.'),
 (279,'de'):('Prüfungen:','correction','The caller uses this as a noun heading above readiness checks; the current target is an imperative sentence.'),
 (279,'id'):('Pemeriksaan:','refinement','Keep the readiness-check heading and remove the extra space before the colon.'),
 (279,'pt-BR'):('Verificações:','refinement','Keep the readiness-check heading and use standard punctuation spacing.'),
 (279,'vi'):('Kiểm tra:','refinement','Keep the readiness-check heading and remove the extra space before the colon.'),
 (281,'ar'):('تصحيح الأخطاء','correction','The caller labels a debug log level. The current word means correction; this names debugging.'),
 (281,'de'):('Debug','correction','The caller labels a debug log level. The current infinitive means the act of debugging rather than the level name.'),
 (281,'es'):('Depuración','refinement','Use the noun for the debug log level instead of the infinitive verb.'),
 (281,'fr'):('Débogage','refinement','Use the noun for the debug log level instead of the infinitive verb.'),
 (281,'id'):('Debug','correction','The caller labels a debug log level. Replace the awkward verb form with the established level name.'),
 (281,'pt-BR'):('Depuração','refinement','Use the noun for the debug log level instead of the infinitive verb.'),
 (283,'ar'):('فعّل مزامنة الألبومات المطلوبة من Lidarr مع قائمة الرغبات','correction','The pinned checkbox and tooltip describe syncing Lidarr wanted albums into the Wishlist. The current target reads wanted as a generic desired setting and obscures the action.'),
 (283,'de'):('Synchronisierung der von Lidarr gewünschten Alben mit der Wunschliste aktivieren','correction','The pinned checkbox and tooltip describe syncing Lidarr wanted albums into the Wishlist. The current target has an awkward word order and treats wanted as a generic adjective.'),
 (283,'es'):('Activar la sincronización de los álbumes deseados de Lidarr con la lista de deseos','correction','The pinned checkbox and tooltip describe syncing Lidarr wanted albums into the Wishlist. The current target has an awkward word order and treats wanted as a generic adjective.'),
 (283,'fr'):('Activer la synchronisation des albums souhaités par Lidarr avec la liste de souhaits','correction','The pinned checkbox and tooltip describe syncing Lidarr wanted albums into the Wishlist. The current target says recherchés (searched-for) rather than souhaités (wanted).'),
 (283,'hi'):('Lidarr के वांछित एल्बमों को Wishlist में सिंक करना सक्षम करें','correction','The pinned checkbox and tooltip describe syncing Lidarr wanted albums into the Wishlist. This makes the wanted-album state and destination clear.'),
 (283,'id'):('Aktifkan sinkronisasi album yang diinginkan di Lidarr ke Wishlist','correction','The pinned checkbox and tooltip describe syncing Lidarr wanted albums into the Wishlist. This clarifies what is synchronized and the destination.'),
 (283,'ja'):('Lidarrで必要とされているアルバムをウィッシュリストに同期する設定を有効にする','correction','The pinned checkbox and tooltip describe syncing Lidarr wanted albums into the Wishlist. The current target leaves the relationship between Lidarr, wanted albums, and synchronization unclear.'),
 (283,'ko'):('Lidarr에서 원하는 앨범을 위시리스트에 동기화하도록 설정','correction','The pinned checkbox and tooltip describe syncing Lidarr wanted albums into the Wishlist. The current target lacks a clear setting/action relationship.'),
 (283,'pt-BR'):('Ativar a sincronização dos álbuns desejados pelo Lidarr com a lista de desejos','correction','The pinned checkbox and tooltip describe syncing Lidarr wanted albums into the Wishlist. The current target has an awkward word order and treats wanted as a generic adjective.'),
 (283,'vi'):('Bật đồng bộ các album Lidarr mong muốn với danh sách mong muốn','correction','The pinned checkbox and tooltip describe syncing Lidarr wanted albums into the Wishlist. The current target has an awkward word order and makes the destination unclear.'),
 (283,'zh-Hans'):('启用将 Lidarr 中想要的专辑同步到愿望清单','correction','The pinned checkbox and tooltip describe syncing Lidarr wanted albums into the Wishlist. The current target uses 想要的 as a literal adjective and does not express the setting clearly.'),
 (283,'zh-Hant'):('啟用將 Lidarr 中想要的專輯同步至願望清單','correction','The pinned checkbox and tooltip describe syncing Lidarr wanted albums into the Wishlist. The current target uses 想要的 as a literal adjective and does not express the setting clearly.'),
 (285,'es'):('Explorar recursos compartidos','correction','The caller labels browsing another user’s shared files. Acciones means actions and is not file sharing.'),
 (285,'id'):('Jelajahi berkas yang dibagikan','correction','The caller labels browsing another user’s shared files. Saham means stocks, not shared files.'),
 (287,'ja'):('DR={range}のロスレスファイルは、音源が非可逆圧縮である可能性を示唆します','correction','The caller displays an audio-quality diagnostic. The current 損失源 means a loss source; state that the audio source may be lossy.'),
 (287,'ko'):('DR={range}인 무손실 파일은 손실 음원일 가능성을 시사합니다','correction','The caller displays an audio-quality diagnostic. The current wording uses 제안합니다 (proposes), which changes the meaning of suggests.'),
 (288,'ar'):('0.1, -0.2, 0.3, ... (تمت تسويته من -1.0 إلى 1.0)','correction','The pinned caller splits the sample input on ASCII commas and parses floats. The Arabic comma in the current example breaks that syntax; preserve the exact sample sequence and decimal points.'),
 (288,'de'):('0.1, -0.2, 0.3, ... (normalisiert von -1.0 bis 1.0)','correction','The pinned caller splits the sample input on commas and parses floats. Decimal commas make the example ambiguous and break the documented comma-separated syntax; retain the decimal points and exact sample sequence.'),
 (288,'es'):('0.1, -0.2, 0.3, ... (normalizado de -1.0 a 1.0)','correction','The pinned caller splits the sample input on commas and parses floats. Decimal commas make the example ambiguous and break the documented comma-separated syntax; retain the decimal points and exact sample sequence.'),
 (288,'fr'):('0.1, -0.2, 0.3, ... (normalisé de -1.0 à 1.0)','correction','The pinned caller splits the sample input on commas and parses floats. Decimal commas make the example ambiguous and break the documented comma-separated syntax; retain the decimal points and exact sample sequence.'),
 (288,'pt-BR'):('0.1, -0.2, 0.3, ... (normalizado de -1.0 a 1.0)','correction','The pinned caller splits the sample input on commas and parses floats. Decimal commas make the example ambiguous and break the documented comma-separated syntax; retain the decimal points and exact sample sequence.'),
 (288,'vi'):('0.1, -0.2, 0.3, ... (chuẩn hóa từ -1.0 đến 1.0)','correction','The pinned caller splits the sample input on commas and parses floats. Decimal commas make the example ambiguous and break the documented comma-separated syntax; retain the decimal points and exact sample sequence.'),
 (288,'ja'):('0.1, -0.2, 0.3, ... (-1.0 から 1.0 に正規化)','correction','The pinned caller splits the sample input on ASCII commas and parses floats. Japanese list commas break that syntax; preserve the exact sample sequence and decimal points.'),
 (288,'zh-Hans'):('0.1, -0.2, 0.3, ...（标准化 -1.0 至 1.0）','correction','The pinned caller splits the sample input on ASCII commas and parses floats. Ideographic commas break that syntax; preserve the exact sample sequence and decimal points.'),
 (288,'zh-Hant'):('0.1, -0.2, 0.3, ...（標準化 -1.0 至 1.0）','correction','The pinned caller splits the sample input on ASCII commas and parses floats. Ideographic commas break that syntax; preserve the exact sample sequence and decimal points.'),
 (290,'ja'):('停止中','refinement','The caller displays a current bridge health state. Use a compact state label rather than the current past-tense sentence.'),
 (290,'pt-BR'):('Parado','refinement','The caller displays a current bridge health state. Use a compact state label rather than the current verb form.'),
 (292,'ar'):('معدل الإيجابيات الكاذبة المقدّر:','correction','The caller displays estimatedFalsePositiveRate as a percentage. The current abbreviation is left as EST and omits that this is a rate.'),
 (292,'de'):('Geschätzte Falsch-Positiv-Rate:','correction','The caller displays estimatedFalsePositiveRate as a percentage. Name the estimated rate; the current text is awkward and incomplete.'),
 (292,'es'):('Tasa estimada de falsos positivos:','correction','The caller displays estimatedFalsePositiveRate as a percentage. Expand Est. and name the rate.'),
 (292,'fr'):('Taux estimé de faux positifs :','correction','The caller displays estimatedFalsePositiveRate as a percentage. The current HNE is a time-zone abbreviation, not an estimate.'),
 (292,'hi'):('अनुमानित गलत-सकारात्मक दर:','correction','The caller displays estimatedFalsePositiveRate as a percentage. Name the estimated rate instead of transliterating Est.'),
 (292,'id'):('Perkiraan tingkat positif palsu:','correction','The caller displays estimatedFalsePositiveRate as a percentage. Name the estimated rate explicitly.'),
 (292,'ja'):('推定偽陽性率:','correction','The caller displays estimatedFalsePositiveRate as a percentage. The current EST suggests a time-zone abbreviation and omits rate.'),
 (292,'ko'):('추정 위양성률:','correction','The caller displays estimatedFalsePositiveRate as a percentage. Name the estimated false-positive rate.'),
 (292,'pt-BR'):('Taxa estimada de falsos positivos:','correction','The caller displays estimatedFalsePositiveRate as a percentage. The current Husa is not a meaningful estimate abbreviation.'),
 (292,'vi'):('Tỷ lệ dương tính giả ước tính:','correction','The caller displays estimatedFalsePositiveRate as a percentage. Name the estimated rate explicitly.'),
 (292,'zh-Hans'):('预计误报率：','correction','The caller displays estimatedFalsePositiveRate as a percentage. Replace the literal Est. abbreviation with the estimated false-positive rate.'),
 (292,'zh-Hant'):('預估偽陽性率：','correction','The caller displays estimatedFalsePositiveRate as a percentage. Replace the literal Est. abbreviation with the estimated false-positive rate.'),
 (294,'vi'):('Chỉ hiển thị các lượt truyền tệp thất bại để bạn tập trung vào phần đó của hàng đợi.','correction','The caller is a file-transfer status filter. Giao dịch means a transaction; use file-transfer wording.'),
 (295,'ar'):('مسارات Demucs الصوتية','correction','The caller lists separated audio stems. The current target translates stems as botanical stems and transliterates the product name.'),
 (295,'de'):('Demucs-Stems','correction','The caller lists separated audio stems. Vorbauten means structural projections, not audio stems; keep the model name exact.'),
 (295,'es'):('Pistas separadas de Demucs','correction','The caller lists separated audio stems. Tallos means botanical stems; keep Demucs as the exact model name.'),
 (295,'fr'):('Pistes séparées de Demucs','correction','The caller lists separated audio stems. Tiges means botanical stems; keep Demucs as the exact model name.'),
 (295,'hi'):('Demucs के अलग-अलग ऑडियो ट्रैक','correction','The caller lists separated audio stems. The current botanical noun is wrong for audio; preserve the model name.'),
 (295,'id'):('Stem audio Demucs','correction','The caller lists separated audio stems. Batang means a plant stem; preserve the model name exactly.'),
 (295,'ja'):('Demucsのステム','correction','The caller lists separated audio stems. Preserve the established audio loanword and exact model name; the current transliterations are unclear.'),
 (295,'ko'):('Demucs 스템','correction','The caller lists separated audio stems. Preserve the established audio loanword and exact model name; the current target means a plant stem.'),
 (295,'pt-BR'):('Stems do Demucs','correction','The caller lists separated audio stems. Hastes means botanical stems; keep the model name exact.'),
 (295,'vi'):('Các stem âm thanh của Demucs','correction','The caller lists separated audio stems. The current target means Demucs trees; keep the audio term and model name.'),
 (295,'zh-Hans'):('Demucs 分轨','correction','The caller lists separated audio stems. The current target uses a botanical term; preserve the model name and use audio-track terminology.'),
 (295,'zh-Hant'):('Demucs 分軌','correction','The caller lists separated audio stems. The current target uses a botanical term; preserve the model name and use audio-track terminology.'),
 (298,'ko'):('이미지','correction','The caller uses this as the image media type, paired with Audio, Video, and Text. 영상 means video.'),
 (300,'ar'):(' | الألبوم: {album}','correction','The caller concatenates Artist, Album, and Title metadata with a literal pipe separator. Preserve that separator so adjacent fields remain distinct.'),
 (300,'de'):(' | Album: {album}','correction','The caller concatenates Artist, Album, and Title metadata with a literal pipe separator. Preserve that separator so adjacent fields remain distinct.'),
 (300,'ja'):(' | アルバム: {album}','correction','The caller concatenates Artist, Album, and Title metadata with a literal pipe separator. Preserve that separator so adjacent fields remain distinct.'),
 (300,'ko'):(' | 앨범: {album}','correction','The caller concatenates Artist, Album, and Title metadata with a literal pipe separator. Preserve that separator so adjacent fields remain distinct.'),
}
HOLDS={278:'terminology',282:'terminology',289:'terminology'}
HOLD_RATIONALE={
 278:'The pinned caller identifies DHT metadata workflows for the MediaCore Pod object. Prior W54 review held the localized noun for Pod because no approved product glossary term exists; keep all locale values unchanged until that term is approved.',
 282:'The pinned caller describes the Pod requirement for a VPN gateway and port forwarding. The product term Pod has no approved localized noun in the reviewed glossary; keep all locale values unchanged pending that decision.',
 289:'The pinned caller requires separate Pod ID and Peer ID values in membership and role actions. The product term Pod has no approved localized noun in the reviewed glossary; keep all locale values unchanged pending that decision.'
}
SOURCE_RATIONALES={
 276:'The caller confirms this is a color name; the current target names yellow.',
 277:'The caller formats collection backfill counts and supplies both successful and failed values; the current target preserves both placeholders and their meanings.',
 279:'The caller uses this as a section heading for readiness checks; the current target conveys the heading.',
 280:'The caller uses this as a discovery-graph description with artist, alternatives, and segment ambiguity context; the current target preserves those concepts.',
 281:'The caller uses this as a log severity label; the current target identifies debug logging.',
 284:'The caller opens available messaging actions for a member display name; the current target preserves the action and placeholder.',
 285:'The caller labels the action for browsing another user’s shared files; the current target conveys file sharing.',
 286:'The caller uses this as an accessible equalizer slider label; the current target names the frequency and gain.',
 287:'The caller formats an audio-quality diagnostic with a dynamic-range placeholder; the current target preserves lossless/lossy direction and DR.',
 288:'The caller is an audio sample input field; the current target preserves the sample sequence and normalized range syntax.',
 290:'The caller displays the bridge health state; the current target indicates that the service is stopped.',
 291:'The caller uses this as the source option for a Lidarr import path; the current target expresses a from/source choice.',
 292:'The caller displays the estimated false-positive rate as a percentage; the current target indicates a false-positive metric.',
 293:'The caller labels whether an automation is included in review; the current target preserves the label placeholder and action.',
 294:'The caller is the failed-transfers filter description; the current target preserves the filter and queue focus.',
 295:'The caller labels separated audio artifacts; the current target conveys an audio output category.',
 296:'The caller opens a peer’s shared files in the Browse view; the current target preserves the username placeholder and action.',
 297:'The caller is the Reset tooltip for source-feed settings; the current target preserves discard and restore semantics and the daemon source.',
 298:'The caller uses this as the image media type among Audio, Video, and Text; the current target names that type.',
 299:'The caller is the cancel tooltip for a private-message dialog; the current target preserves closing without sending.',
 300:'The caller concatenates Album metadata into a report line after Artist and before Title; the current target preserves the album label and placeholder.'
}

decisions=[]
for cell in cells:
  rank=cell['continuationRank']; loc=cell['locale']; key=(rank,loc); current=cell['currentTarget']; source=cell['source']
  caller=caller_by_id[cell['sourceId']]; assert sha(json.dumps(caller['callers'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())==cell['callerContextSha256']
  if rank in HOLDS:
    candidate=current; verdict='hold-'+HOLDS[rank]; rationale=HOLD_RATIONALE[rank]; confidence='low'
  elif key in PROPOSALS:
    candidate,verdict,rationale=PROPOSALS[key]; confidence='moderate'
  else:
    candidate=current; verdict='accept-current'; rationale=SOURCE_RATIONALES[rank]; confidence='moderate'
  srcph=collections.Counter(PH.findall(source)); curph=collections.Counter(PH.findall(current)); candph=collections.Counter(PH.findall(candidate))
  srcmark=collections.Counter(MARKUP.findall(source)); curmark=collections.Counter(MARKUP.findall(current)); candmark=collections.Counter(MARKUP.findall(candidate))
  srcnum=collections.Counter(NUMBER.findall(source)); curnum=collections.Counter(NUMBER.findall(current)); candnum=collections.Counter(NUMBER.findall(candidate))
  protected=[]
  for p in cell['protectedLiteralChecks']:
    protected.append({'literal':p['literal'],'kind':p['kind'],'policy':p['policy'],'sourcePresent':p['sourcePresent'],'currentPresent':p['currentPresent'],'candidatePresent':p['literal'] in candidate})
  refs=cell['callerRefs']
  assert sha(current)==cell['currentTargetSha256'] and sha(source)==cell['sourceSha256']
  decisions.append({'continuationRank':rank,'historicalSourceOrdinal':None,'sourceId':cell['sourceId'],'source':source,'sourceSha256':cell['sourceSha256'],'locale':loc,'catalogPath':cell['catalogPath'],'catalogFileSha256':cell['catalogFileSha256'],'catalogGitBlob':cell['catalogGitBlob'],'currentTarget':current,'currentTargetSha256':cell['currentTargetSha256'],'candidateTarget':candidate,'candidateTargetSha256':sha(candidate),'callerContextSha256':cell['callerContextSha256'],'callerRefs':refs,'callerCount':caller['productionCallerCount'],'confidence':confidence,'verdict':verdict,'rationale':rationale,'placeholderCheck':{'source':dict(srcph),'current':dict(curph),'candidate':dict(candph),'sourceMatchesCurrent':srcph==curph,'sourceMatchesCandidate':srcph==candph},'markupCheck':{'source':dict(srcmark),'current':dict(curmark),'candidate':dict(candmark),'sourceMatchesCurrent':srcmark==curmark,'sourceMatchesCandidate':srcmark==candmark},'numericCheck':{'source':list(NUMBER.findall(source)),'current':list(NUMBER.findall(current)),'candidate':list(NUMBER.findall(candidate)),'sourceMatchesCurrent':(not srcnum or srcnum==curnum),'sourceMatchesCandidate':(not srcnum or srcnum==candnum)},'protectedLiteralChecks':protected})

counts=collections.Counter(x['verdict'] for x in decisions)
changes=[x for x in decisions if x['candidateTarget']!=x['currentTarget']]
holds=[x for x in decisions if x['verdict'].startswith('hold-')]
assert len(decisions)==300 and len(changes)==70 and counts==collections.Counter({'accept-current':194,'correction':60,'refinement':10,'hold-terminology':36}),counts
issues={'placeholder':[],'markup':[],'numericCandidate':[],'protectedCandidate':[],'currentProtected':[],'currentNumeric':[]}
for x in decisions:
  k=f"{x['continuationRank']}:{x['locale']}"
  if not x['placeholderCheck']['sourceMatchesCandidate']: issues['placeholder'].append(k)
  if not x['markupCheck']['sourceMatchesCandidate']: issues['markup'].append(k)
  if not x['numericCheck']['sourceMatchesCandidate']: issues['numericCandidate'].append(k)
  if any(not q['candidatePresent'] for q in x['protectedLiteralChecks']): issues['protectedCandidate'].append({'cell':k,'missing':[q['literal'] for q in x['protectedLiteralChecks'] if not q['candidatePresent']]})
  if any(not q['currentPresent'] for q in x['protectedLiteralChecks']): issues['currentProtected'].append({'cell':k,'missing':[q['literal'] for q in x['protectedLiteralChecks'] if not q['currentPresent']]})
  if not x['numericCheck']['sourceMatchesCurrent']: issues['currentNumeric'].append(k)
assert not issues['placeholder'] and not issues['markup'] and not issues['numericCandidate'] and not issues['protectedCandidate'],issues
changed_by_locale=dict(collections.Counter(x['locale'] for x in changes))
changed_by_rank=dict(collections.Counter(str(x['continuationRank']) for x in changes))
changed_by_source=dict(collections.Counter(x['sourceId'] for x in changes))
summary={'repository':'snapetech-org/slskdN','pullRequest':409,'pullRequestUrl':att['url'],'exactHead':HEAD,'exactTree':TREE,'branch':att['branch'],'remoteBranchHead':att['remoteBranchHead'],'pinnedPrBodySha256':att['bodySha256'],'window':'W55 continuation ranks 276-300 from pinned W49 stable-ID inventory; historical source ordinals unavailable and not claimed','sourceCount':25,'localeCount':12,'cellCount':300,'dispositionCounts':dict(counts),'candidateChangeCount':len(changes),'changedCellsByLocale':changed_by_locale,'changedCellsByRank':changed_by_rank,'changedCellsBySource':changed_by_source,'holdCount':len(holds),'heldSourceIds':sorted({x['sourceId'] for x in holds}),'heldRanks':{'278':'Publish or retrieve pod metadata through DHT workflows.','282':'You need at least one pod with VPN gateway capability to use port forwarding.','289':'Please enter both Pod ID and Peer ID'},'holdLocalesByRank':{str(r):LOCALES for r in sorted(HOLDS)},'callerReferenceCount':sum(x['productionCallerCount'] for x in callers),'callerlessSourceIds':[],'currentProtectedLiteralMismatchCellCount':len(issues['currentProtected']),'currentProtectedLiteralMismatchCells':issues['currentProtected'],'candidateProtectedLiteralMismatchCount':len(issues['protectedCandidate']),'currentNumericMismatchCellCount':len(issues['currentNumeric']),'currentNumericMismatchCells':issues['currentNumeric'],'candidateNumericMismatchCount':len(issues['numericCandidate']),'placeholderMismatchCount':len(issues['placeholder']),'markupMismatchCount':len(issues['markup']),'inputContainsCandidates':False,'inputManifestSha256':sha((INPUT/'PACKET-SHA256SUMS.txt').read_bytes()),'inputManifestEntriesVerified':len(input_checks),'nativeSpeakerApproval':False,'headedProductBrowserReview':False,'projectTestsBuildScansCiRun':False,'repositoryModified':False,'remoteMutation':False,'reviewType':'machine-assisted primary semantic review; moderate confidence for proposed translations; terminology holds await approved product wording and native-speaker review','notes':['Ranks 276-300 are disjoint from W49 reviewed IDs and W50-W54; W49 gap 126-150 remains excluded.','Rank 288 comma-separated audio sample syntax is pinned to the production caller, which splits on commas and parses floats. Decimal-comma current values are held for correction to dot-decimal examples.','Rank 278, 282, and 289 remain terminology holds across all 12 locales because the product noun Pod has no approved localized glossary term.','Proposals are machine-assisted and do not constitute native-speaker approval.'], 'exactChanges':[{'rank':x['continuationRank'],'sourceId':x['sourceId'],'source':x['source'],'locale':x['locale'],'from':x['currentTarget'],'to':x['candidateTarget'],'verdict':x['verdict'],'rationale':x['rationale']} for x in changes], 'exactHolds':[{'rank':x['continuationRank'],'sourceId':x['sourceId'],'source':x['source'],'locale':x['locale'],'current':x['currentTarget'],'reason':x['rationale']} for x in holds]}
PRIMARY.mkdir()
write_jsonl(PRIMARY/'review-decisions.jsonl',decisions); write_json(PRIMARY/'review-summary.json',summary)
readme=(f"# slskdN PR #409 W55 primary semantic review\n\n"
 f"Pinned to open draft PR #409 head/tree `{HEAD}` / `{TREE}`. This review covers ranks 276–300 of the W49 stable-ID inventory, 25 source IDs × 12 locales = 300 cells. Historical extraction ordinals are unavailable and are not claimed. The candidate-free input manifest SHA-256 is `{summary['inputManifestSha256']}`.\n\n"
 f"Primary dispositions: 194 accept-current, 60 corrections, 10 refinements, and 36 terminology holds. The 66 exact proposals are in `review-decisions.jsonl`; the 36 unchanged holds cover `Pod` terminology in ranks 278, 282, and 289 across all 12 locales.\n\n"
 "The rank 288 sample values are comma-separated floats. Its pinned caller splits on commas and parses floats, so decimal-comma examples were changed to preserve the working syntax. The other proposals address caller-confirmed meaning, grammar, false-positive rate naming, audio stems, and metadata separators. Placeholder, markup, numeric-token, and candidate protected-literal checks pass.\n\n"
 "This is machine-assisted primary review, not native-speaker approval or headed product-browser acceptance. No repository/catalog changes, PR edits, commits, pushes, tests, builds, scans, CI, workflow changes, merges, releases, or tags were made.\n")
(PRIMARY/'README.md').write_text(readme,encoding='utf-8')
# Compact human-readable index with all proposals and holds.
lines=['# W55 primary review worksheet','',f'Exact head/tree: `{HEAD}` / `{TREE}`. Input manifest: `{summary["inputManifestSha256"]}`.','',f"Counts: {dict(counts)}; proposals: {len(changes)}; holds: {len(holds)}."]
for rank in range(276,301):
 subset=[x for x in decisions if x['continuationRank']==rank]
 first=subset[0]; lines+=['',f"## Rank {rank} — `{first['sourceId']}`",'',f"Source: {first['source']}",f"Caller hits: {first['callerCount']}"]
 for x in subset:
  if x['verdict'].startswith('hold-'):
   lines.append(f"- **{x['locale']} hold-terminology:** unchanged `{x['currentTarget']}` — {x['rationale']}")
  elif x['candidateTarget']!=x['currentTarget']:
   lines.append(f"- **{x['locale']} {x['verdict']}:** `{x['currentTarget']}` → `{x['candidateTarget']}` — {x['rationale']}")
  else:
   lines.append(f"- {x['locale']}: {x['verdict']}")
(PRIMARY/'review-worksheet.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
write_manifest(PRIMARY,'SHA256SUMS.txt')
primary_checks=verify_manifest(PRIMARY,'SHA256SUMS.txt')
assert len(read_jsonl(PRIMARY/'review-decisions.jsonl'))==300
assert verify_manifest(INPUT,'PACKET-SHA256SUMS.txt')
print(json.dumps({'verification':'primary-sealed','primaryDir':str(PRIMARY),'counts':dict(counts),'candidateChanges':len(changes),'holds':len(holds),'holdSources':summary['heldSourceIds'],'changedByLocale':changed_by_locale,'currentNumericMismatchCells':issues['currentNumeric'],'currentProtectedLiteralMismatchCount':len(issues['currentProtected']),'candidateNumericMismatchCount':len(issues['numericCandidate']),'candidateProtectedMismatchCount':len(issues['protectedCandidate']),'placeholderMismatchCount':len(issues['placeholder']),'markupMismatchCount':len(issues['markup']),'primaryManifestEntriesVerified':len(primary_checks),'primaryManifestSha256':sha((PRIMARY/'SHA256SUMS.txt').read_bytes()),'inputManifestSha256':summary['inputManifestSha256']},ensure_ascii=False,indent=2))
