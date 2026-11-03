#!/usr/bin/env python3
"""Create an independent blind W55 review using candidate-free input only."""
from pathlib import Path
import collections, hashlib, json, re
OUT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w55-independent-blind-20261103')
IN=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w55-primary-20261103/input')
INPUT=IN; LEDGER=OUT/'blind-review-ledger.jsonl'
HEAD='6a46b8f1dc87d899308fee141fa0db392e49e098'; TREE='a22e9a896aae12aa89a1502d9748b12816d491ed'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PH=re.compile(r'\{[^{}]+\}'); MARKUP=re.compile(r'</?[A-Za-z][^>]*>'); NUMBER=re.compile(r'(?<![A-Za-z])\d+(?:[.,]\d+)?%?(?![A-Za-z])')
def sha(v): return hashlib.sha256(v.encode('utf-8') if isinstance(v,str) else v).hexdigest()
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def write_json(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_jsonl(p,rows): p.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in rows),encoding='utf-8')
def verify_manifest(d,name):
 rows=[]
 for line in (d/name).read_text().splitlines():
  if not line.strip(): continue
  h,rel=line.split(None,1); rel=rel.strip().lstrip('*'); rows.append({'path':rel,'matches':sha((d/rel).read_bytes())==h})
 assert rows and all(r['matches'] for r in rows),(d/name,rows)
 return rows
assert not LEDGER.exists() and IN.is_dir()
input_checks=verify_manifest(IN,'PACKET-SHA256SUMS.txt')
att=json.loads((IN/'head-tree-attestation.json').read_text(encoding='utf-8'))
selection=json.loads((IN/'selection-and-boundary.json').read_text(encoding='utf-8'))
assert (att['head'],att['tree'])==(HEAD,TREE) and selection['inputContainsCandidates'] is False
cells=jl(IN/'source-current-cells.jsonl'); caller_rows=jl(IN/'caller-contexts.jsonl')
assert len(cells)==300 and len(caller_rows)==25
assert [(r['continuationRank'],r['locale']) for r in cells]==[(rank,loc) for rank in range(276,301) for loc in LOCALES]
caller_by_id={c['sourceId']:c for c in caller_rows}

# Independent exact winners. These were chosen directly from current values and
# pinned caller context; no prior primary ledger was read.
PROPOSALS={
 (276,'zh-Hans'):('黄色','refinement','The caller uses this as a color swatch label. Removing 的 yields the color name rather than an adjectival phrase.'),
 (276,'zh-Hant'):('黃色','refinement','The caller uses this as a color swatch label. Removing 的 yields the color name rather than an adjectival phrase.'),
 (279,'ar'):('الفحوصات:','refinement','The caller uses this as a section heading above readiness checks. Use the heading noun and remove the space before the colon.'),
 (279,'de'):('Prüfungen:','correction','The caller uses this as a heading above readiness checks. The current target is an imperative sentence, not a section label.'),
 (279,'id'):('Pemeriksaan:','refinement','This is a heading above readiness checks; remove the nonstandard space before the colon.'),
 (279,'pt-BR'):('Verificações:','refinement','This is a heading above readiness checks; use standard Portuguese punctuation spacing.'),
 (279,'vi'):('Kiểm tra:','refinement','This is a heading above readiness checks; remove the nonstandard space before the colon.'),
 (281,'ar'):('تصحيح الأخطاء','correction','The pinned object is a log severity level. The current target means correction; this explicitly means debugging.'),
 (281,'de'):('Debug','correction','The pinned object is the Debug log level. The current infinitive names the act, not the level.'),
 (281,'es'):('Depuración','refinement','Use the noun label for the Debug log level instead of the infinitive verb.'),
 (281,'fr'):('Débogage','refinement','Use the noun label for the Debug log level instead of the infinitive verb.'),
 (281,'id'):('Debug','correction','The pinned object is the Debug log level. Replace the awkward verb form with the level name.'),
 (281,'pt-BR'):('Depuração','refinement','Use the noun label for the Debug log level instead of the infinitive verb.'),
 (283,'ar'):('فعّل مزامنة الألبومات المطلوبة من Lidarr مع Wishlist','correction','The pinned checkbox and tooltip identify Lidarr wanted albums synchronized into Wishlist. The current target describes a wanted sync setting without stating what is synchronized.'),
 (283,'de'):('Synchronisierung der von Lidarr gewünschten Alben mit Wishlist aktivieren','correction','The pinned checkbox and tooltip identify Lidarr wanted albums synchronized into Wishlist. The current word order obscures the target of wanted.'),
 (283,'es'):('Activar la sincronización de los álbumes deseados de Lidarr con Wishlist','correction','The pinned checkbox and tooltip identify Lidarr wanted albums synchronized into Wishlist. The current target does not state what is synchronized.'),
 (283,'fr'):('Activer la synchronisation des albums souhaités par Lidarr avec Wishlist','correction','The pinned checkbox and tooltip identify Lidarr wanted albums synchronized into Wishlist. The current recherchés means searched-for and misses the wanted state.'),
 (283,'hi'):('Lidarr के वांछित एल्बमों को Wishlist में सिंक करने की सेटिंग सक्षम करें','correction','The pinned checkbox and tooltip identify Lidarr wanted albums synchronized into Wishlist. This makes the object and setting action explicit.'),
 (283,'id'):('Aktifkan sinkronisasi album yang diinginkan di Lidarr ke Wishlist','correction','The pinned checkbox and tooltip identify Lidarr wanted albums synchronized into Wishlist. This makes the object and destination explicit.'),
 (283,'ja'):('Lidarrで取得を希望しているアルバムをWishlistに同期する設定を有効にする','correction','The pinned checkbox and tooltip identify Lidarr wanted albums synchronized into Wishlist. The current target does not say what the setting synchronizes.'),
 (283,'ko'):('Lidarr에서 원하는 앨범을 Wishlist에 동기화하도록 설정','correction','The pinned checkbox and tooltip identify Lidarr wanted albums synchronized into Wishlist. The current target does not clearly express the setting action.'),
 (283,'pt-BR'):('Ativar a sincronização dos álbuns desejados pelo Lidarr com Wishlist','correction','The pinned checkbox and tooltip identify Lidarr wanted albums synchronized into Wishlist. The current target does not state what is synchronized.'),
 (283,'vi'):('Bật đồng bộ các album được Lidarr mong muốn với Wishlist','correction','The pinned checkbox and tooltip identify Lidarr wanted albums synchronized into Wishlist. The current target leaves the object and destination unclear.'),
 (283,'zh-Hans'):('启用将 Lidarr 中想要的专辑同步到 Wishlist','correction','The pinned checkbox and tooltip identify Lidarr wanted albums synchronized into Wishlist. The current target is a literal fragment and does not clearly name the setting action.'),
 (283,'zh-Hant'):('啟用將 Lidarr 中想要的專輯同步至 Wishlist','correction','The pinned checkbox and tooltip identify Lidarr wanted albums synchronized into Wishlist. The current target is a literal fragment and does not clearly name the setting action.'),
 (285,'es'):('Explorar recursos compartidos','correction','The caller says this opens another user’s shared files. Acciones means actions, not shares.'),
 (285,'id'):('Jelajahi berkas yang dibagikan','correction','The caller says this opens another user’s shared files. Saham means stocks, not file shares.'),
 (287,'ja'):('DR={range}のロスレスファイルは、音源が非可逆圧縮である可能性を示唆する','correction','The caller formats an audio-quality diagnosis. The current 損失源 refers to a loss source; state that the source audio may be lossy.'),
 (287,'ko'):('DR={range}인 무손실 파일은 손실 음원일 가능성을 시사합니다','correction','The caller formats an audio-quality diagnosis. The current 제안합니다 means proposes, not suggests in this diagnostic.'),
 (288,'ar'):('0.1, -0.2, 0.3, ... (تمت تسويته من -1.0 إلى 1.0)','correction','The pinned text area is parsed by splitting on ASCII commas and parsing floats. Arabic commas would not split the samples; preserve the parser example exactly.'),
 (288,'de'):('0.1, -0.2, 0.3, ... (normalisiert von -1.0 bis 1.0)','correction','The pinned text area is parsed by splitting on commas and parsing floats. Decimal commas conflict with sample separators; retain decimal points and the exact sample syntax.'),
 (288,'es'):('0.1, -0.2, 0.3, ... (normalizado de -1.0 a 1.0)','correction','The pinned text area is parsed by splitting on commas and parsing floats. Decimal commas conflict with sample separators; retain decimal points and the exact sample syntax.'),
 (288,'fr'):('0.1, -0.2, 0.3, ... (normalisé de -1.0 à 1.0)','correction','The pinned text area is parsed by splitting on commas and parsing floats. Decimal commas conflict with sample separators; retain decimal points and the exact sample syntax.'),
 (288,'ja'):('0.1, -0.2, 0.3, ...（-1.0 から 1.0 に正規化）','correction','The pinned text area is parsed by splitting on ASCII commas and parsing floats. Japanese list commas would not split the samples; preserve the parser example exactly.'),
 (288,'pt-BR'):('0.1, -0.2, 0.3, ... (normalizado de -1.0 a 1.0)','correction','The pinned text area is parsed by splitting on commas and parsing floats. Decimal commas conflict with sample separators; retain decimal points and the exact sample syntax.'),
 (288,'vi'):('0.1, -0.2, 0.3, ... (chuẩn hóa từ -1.0 đến 1.0)','correction','The pinned text area is parsed by splitting on commas and parsing floats. Decimal commas conflict with sample separators; retain decimal points and the exact sample syntax.'),
 (288,'zh-Hans'):('0.1, -0.2, 0.3, ...（标准化 -1.0 至 1.0）','correction','The pinned text area is parsed by splitting on ASCII commas and parsing floats. Ideographic commas would not split the samples; preserve the parser example exactly.'),
 (288,'zh-Hant'):('0.1, -0.2, 0.3, ...（標準化 -1.0 至 1.0）','correction','The pinned text area is parsed by splitting on ASCII commas and parsing floats. Ideographic commas would not split the samples; preserve the parser example exactly.'),
 (290,'es'):('Detenido','refinement','The caller displays a current health state. Detenido is a state label; Interrumpido suggests an interruption.'),
 (290,'ja'):('停止中','refinement','The caller displays a current health state. Use a compact state label rather than the current completed-action sentence.'),
 (290,'pt-BR'):('Parado','refinement','The caller displays a current health state. Use a compact state label rather than the current verb form.'),
 (292,'ar'):('معدل الإيجابيات الكاذبة المقدّر:','correction','The caller renders estimatedFalsePositiveRate as a percentage. The current EST abbreviation is not an estimate in Arabic and omits that this is a rate.'),
 (292,'de'):('Geschätzte Falsch-Positiv-Rate:','correction','The caller renders estimatedFalsePositiveRate as a percentage. Name the estimated rate rather than the current awkward shorthand.'),
 (292,'es'):('Tasa estimada de falsos positivos:','correction','The caller renders estimatedFalsePositiveRate as a percentage. Expand Est. and name the rate.'),
 (292,'fr'):('Taux estimé de faux positifs :','correction','The caller renders estimatedFalsePositiveRate as a percentage. HNE is a time-zone abbreviation, not an estimate.'),
 (292,'hi'):('अनुमानित गलत-सकारात्मक दर:','correction','The caller renders estimatedFalsePositiveRate as a percentage. Name the estimated rate instead of transliterating Est.'),
 (292,'id'):('Perkiraan tingkat positif palsu:','correction','The caller renders estimatedFalsePositiveRate as a percentage. Name the rate explicitly.'),
 (292,'ja'):('推定偽陽性率:','correction','The caller renders estimatedFalsePositiveRate as a percentage. The current EST suggests a time-zone abbreviation and omits rate.'),
 (292,'ko'):('추정 위양성률:','correction','The caller renders estimatedFalsePositiveRate as a percentage. Name the estimated false-positive rate.'),
 (292,'pt-BR'):('Taxa estimada de falsos positivos:','correction','The caller renders estimatedFalsePositiveRate as a percentage. Husa is not a meaningful estimate abbreviation.'),
 (292,'vi'):('Tỷ lệ dương tính giả ước tính:','correction','The caller renders estimatedFalsePositiveRate as a percentage. Name the estimated rate explicitly.'),
 (292,'zh-Hans'):('预计误报率：','correction','The caller renders estimatedFalsePositiveRate as a percentage. Replace the literal Est. abbreviation with the estimated rate.'),
 (292,'zh-Hant'):('預估偽陽性率：','correction','The caller renders estimatedFalsePositiveRate as a percentage. Replace the literal Est. abbreviation with the estimated rate.'),
 (294,'vi'):('Chỉ hiển thị các lượt truyền tệp thất bại để bạn tập trung vào phần đó của hàng đợi.','correction','The caller is a file-transfer filter. Giao dịch means transaction; use wording for file transfers.'),
 (295,'ar'):('مسارات Demucs الصوتية','correction','The caller lists outputs of audio source separation. The current target treats stems as a verb and transliterates Demucs.'),
 (295,'de'):('Demucs-Stems','correction','The caller lists separated audio stems. Vorbauten is not an audio term; retain the exact model name.'),
 (295,'es'):('Pistas separadas de Demucs','correction','The caller lists separated audio stems. Tallos means botanical stems; retain the exact model name.'),
 (295,'fr'):('Pistes séparées de Demucs','correction','The caller lists separated audio stems. Tiges means botanical stems; retain the exact model name.'),
 (295,'hi'):('Demucs के अलग-अलग ऑडियो ट्रैक','correction','The caller lists separated audio stems. The current botanical noun is wrong for audio; retain the exact model name.'),
 (295,'id'):('Stem audio Demucs','correction','The caller lists separated audio stems. Batang means a plant stem; retain the exact model name.'),
 (295,'ja'):('Demucsのステム','correction','The caller lists separated audio stems. Use the audio loanword and preserve the exact model name.'),
 (295,'ko'):('Demucs 스템','correction','The caller lists separated audio stems. Use the audio loanword and preserve the exact model name.'),
 (295,'pt-BR'):('Stems do Demucs','correction','The caller lists separated audio stems. Hastes means botanical stems; retain the exact model name.'),
 (295,'vi'):('Các stem âm thanh của Demucs','correction','The caller lists separated audio stems. The current target refers to Demucs trees; retain the audio term and exact model name.'),
 (295,'zh-Hans'):('Demucs 分轨','correction','The caller lists separated audio stems. The current target uses a botanical term; use audio-track terminology and preserve the exact model name.'),
 (295,'zh-Hant'):('Demucs 分軌','correction','The caller lists separated audio stems. The current target uses a botanical term; use audio-track terminology and preserve the exact model name.'),
 (298,'ko'):('이미지','correction','The caller uses this as the image media type beside Audio, Video, and Text. 영상 means video.'),
 (300,'ar'):(' | الألبوم: {album}','correction','The caller concatenates Album between Artist and Title using a literal pipe. The current target omits it, so report fields can run together.'),
 (300,'de'):(' | Album: {album}','correction','The caller concatenates Album between Artist and Title using a literal pipe. The current target omits it, so report fields can run together.'),
 (300,'ja'):(' | アルバム: {album}','correction','The caller concatenates Album between Artist and Title using a literal pipe. The current target omits it, so report fields can run together.'),
 (300,'ko'):(' | 앨범: {album}','correction','The caller concatenates Album between Artist and Title using a literal pipe. The current target omits it, so report fields can run together.'),
}
HOLDS={278:'terminology',282:'terminology',289:'terminology'}
HOLD_REASON={
 278:'The pinned caller names DHT metadata workflows for the MediaCore Pod object. The input explicitly records that no approved localized product noun for Pod exists; keep current values unchanged pending terminology approval.',
 282:'The pinned caller describes a Pod with VPN gateway capability as the port-forwarding prerequisite. The product noun Pod has no approved localized term in the input glossary guidance; keep current values unchanged.',
 289:'The pinned callers request both Pod ID and Peer ID for membership and role operations. The Pod noun has no approved localized product term; keep current values unchanged until that decision is made.'
}
BASE_RATIONALE={
 276:'The caller uses this as a color option and the current value names yellow.',
 277:'The caller formats collection backfill counts with distinct successful and failed placeholders; the current value preserves both meanings and tokens.',
 279:'The callers use this as a section heading above readiness checks; the current value conveys a checks heading.',
 280:'The caller is a discovery-graph description; the current value retains artist, alternatives, and segment ambiguity context.',
 281:'The caller uses this as the Debug log severity label; the current value denotes debugging.',
 284:'The caller exposes messaging actions from the member name and supplies the display placeholder; the current value preserves both.',
 285:'The caller labels browsing another user’s shared files; the current value conveys that action.',
 286:'The caller uses this as an accessible equalizer control label; the current value preserves frequency and gain.',
 287:'The caller formats an audio-quality warning and supplies the DR placeholder; the current value preserves lossless/lossy direction.',
 288:'The caller uses this as the audio sample field placeholder; the current value preserves the numeric range, though some localized separators require correction.',
 290:'The caller displays a stopped bridge health status; the current value conveys the stopped state.',
 291:'The caller uses this as the source/from label for the Lidarr import path setting; the current value conveys a from/source choice.',
 292:'The caller displays an estimated false-positive rate as a percentage; the current value signals a false-positive metric.',
 293:'The caller labels whether a media-server automation is included in review; the current value preserves the action and label placeholder.',
 294:'The caller describes filtering the failed-transfer queue; the current value conveys that filter.',
 295:'The caller labels separated audio outputs; the current value conveys an audio category.',
 296:'The caller opens a peer’s shared files and supplies the username placeholder; the current value preserves both.',
 297:'The caller is a Reset tooltip for source-feed settings; the current value preserves discarding edits and restoring daemon-reported values.',
 298:'The caller uses this as the image media type among Audio, Video, and Text; the current value names that type.',
 299:'The caller is the cancel tooltip for a private-message dialog; the current value preserves closing without sending.',
 300:'The caller concatenates Album metadata between Artist and Title; the current value retains the album label and placeholder.'
}

decisions=[]
for cell in cells:
 rank=cell['continuationRank']; locale=cell['locale']; key=(rank,locale); current=cell['currentTarget']; source=cell['source']; caller=caller_by_id[cell['sourceId']]
 if rank in HOLDS:
  candidate=current; disposition='hold-'+HOLDS[rank]; rationale=HOLD_REASON[rank]; confidence='low'
 elif key in PROPOSALS:
  candidate,disposition,rationale=PROPOSALS[key]; confidence='moderate'
 else:
  candidate=current; disposition='accept-current'; rationale=BASE_RATIONALE[rank]; confidence='moderate'
 source_ph=collections.Counter(PH.findall(source)); current_ph=collections.Counter(PH.findall(current)); candidate_ph=collections.Counter(PH.findall(candidate))
 source_markup=collections.Counter(MARKUP.findall(source)); current_markup=collections.Counter(MARKUP.findall(current)); candidate_markup=collections.Counter(MARKUP.findall(candidate))
 source_nums=collections.Counter(NUMBER.findall(source)); current_nums=collections.Counter(NUMBER.findall(current)); candidate_nums=collections.Counter(NUMBER.findall(candidate))
 protected=[]
 for p in cell['protectedLiteralChecks']:
  protected.append({'literal':p['literal'],'kind':p['kind'],'policy':p['policy'],'sourcePresent':p['sourcePresent'],'currentPresent':p['currentPresent'],'candidatePresent':p['literal'] in candidate})
 decisions.append({'continuationRank':rank,'historicalSourceOrdinal':None,'sourceId':cell['sourceId'],'source':source,'sourceSha256':cell['sourceSha256'],'locale':locale,'catalogPath':cell['catalogPath'],'catalogFileSha256':cell['catalogFileSha256'],'catalogGitBlob':cell['catalogGitBlob'],'currentTarget':current,'currentTargetSha256':cell['currentTargetSha256'],'candidateTarget':candidate,'candidateTargetSha256':sha(candidate),'callerContextSha256':cell['callerContextSha256'],'callerRefs':cell['callerRefs'],'callerCount':caller['productionCallerCount'],'confidence':confidence,'verdict':disposition,'rationale':rationale,'placeholderCheck':{'source':dict(source_ph),'current':dict(current_ph),'candidate':dict(candidate_ph),'sourceMatchesCurrent':source_ph==current_ph,'sourceMatchesCandidate':source_ph==candidate_ph},'markupCheck':{'source':dict(source_markup),'current':dict(current_markup),'candidate':dict(candidate_markup),'sourceMatchesCurrent':source_markup==current_markup,'sourceMatchesCandidate':source_markup==candidate_markup},'numericCheck':{'source':NUMBER.findall(source),'current':NUMBER.findall(current),'candidate':NUMBER.findall(candidate),'sourceHasNumericLiterals':bool(source_nums),'sourceMatchesCurrent':(not source_nums or source_nums==current_nums),'sourceMatchesCandidate':(not source_nums or source_nums==candidate_nums)},'protectedLiteralChecks':protected})
counts=collections.Counter(x['verdict'] for x in decisions); changes=[x for x in decisions if x['candidateTarget']!=x['currentTarget']]; holds=[x for x in decisions if x['verdict'].startswith('hold-')]
assert len(decisions)==300 and len(changes)==71 and counts==collections.Counter({'accept-current':193,'correction':59,'refinement':12,'hold-terminology':36}),counts
issues={'placeholder':[],'markup':[],'numericCandidate':[],'protectedCandidate':[],'currentProtected':[],'currentNumeric':[]}
for x in decisions:
 cell=f"{x['continuationRank']}:{x['locale']}"
 if not x['placeholderCheck']['sourceMatchesCandidate']: issues['placeholder'].append(cell)
 if not x['markupCheck']['sourceMatchesCandidate']: issues['markup'].append(cell)
 if not x['numericCheck']['sourceMatchesCandidate']: issues['numericCandidate'].append(cell)
 if not x['numericCheck']['sourceMatchesCurrent']: issues['currentNumeric'].append(cell)
 if any(not z['candidatePresent'] for z in x['protectedLiteralChecks']): issues['protectedCandidate'].append({'cell':cell,'missing':[z['literal'] for z in x['protectedLiteralChecks'] if not z['candidatePresent']]})
 if any(not z['currentPresent'] for z in x['protectedLiteralChecks']): issues['currentProtected'].append({'cell':cell,'missing':[z['literal'] for z in x['protectedLiteralChecks'] if not z['currentPresent']]})
assert not issues['placeholder'] and not issues['markup'] and not issues['numericCandidate'] and not issues['protectedCandidate'],issues
changes_by_locale=dict(collections.Counter(x['locale'] for x in changes)); changes_by_rank=dict(collections.Counter(str(x['continuationRank']) for x in changes))
summary={'reviewType':'independent blind machine-assisted semantic review using only the sealed candidate-free input; no primary ledger was consulted before this ledger was sealed','repository':'snapetech-org/slskdN','pullRequest':409,'pullRequestUrl':att['url'],'state':att['state'],'isDraft':att['isDraft'],'branch':att['branch'],'exactHead':HEAD,'exactTree':TREE,'remoteBranchHead':att['remoteBranchHead'],'pinnedPrBodySha256':att['bodySha256'],'window':'W55 W49 stable-ID continuation ranks 276-300; historical source ordinals unavailable and not claimed','sourceCount':25,'localeCount':12,'cellCount':300,'dispositionCounts':dict(counts),'candidateChangeCount':len(changes),'changedCellsByLocale':changes_by_locale,'changedCellsByRank':changes_by_rank,'callerSourceCount':25,'callerReferenceCount':40,'callerlessSourceIds':[],'holdCount':len(holds),'heldSourceIds':sorted({x['sourceId'] for x in holds}),'heldRanks':{'278':'Publish or retrieve pod metadata through DHT workflows.','282':'You need at least one pod with VPN gateway capability to use port forwarding.','289':'Please enter both Pod ID and Peer ID'},'holdLocalesByRank':{str(r):LOCALES for r in sorted(HOLDS)},'currentProtectedLiteralMismatchCellCount':len(issues['currentProtected']),'currentProtectedLiteralMismatchCells':issues['currentProtected'],'candidateProtectedLiteralMismatchCount':len(issues['protectedCandidate']),'currentNumericMismatchCellCount':len(issues['currentNumeric']),'currentNumericMismatchCells':issues['currentNumeric'],'candidateNumericMismatchCount':len(issues['numericCandidate']),'placeholderMismatchCount':len(issues['placeholder']),'markupMismatchCount':len(issues['markup']),'inputContainsCandidates':False,'inputManifestSha256':sha((IN/'PACKET-SHA256SUMS.txt').read_bytes()),'inputManifestEntriesVerified':len(input_checks),'nativeSpeakerApproval':False,'headedProductBrowserReview':False,'repositoryModified':False,'remoteMutation':False,'projectTestsBuildsScansCiRun':False,'notes':['W55 is disjoint from the prior reviewed stable-ID ranges; W49 gap 126-150 remains excluded.','Rank 288 uses a production parser that splits audio sample input on ASCII commas; decimal commas and non-ASCII separators are not safe in this example.','The Pod term holds cover all 12 locales for ranks 278, 282, and 289 due to the unresolved product glossary noun.','Proposed strings are machine-assisted and remain subject to native-speaker review.'],'exactWinners':[{'rank':x['continuationRank'],'sourceId':x['sourceId'],'source':x['source'],'locale':x['locale'],'from':x['currentTarget'],'to':x['candidateTarget'],'disposition':x['verdict'],'rationale':x['rationale']} for x in changes],'exactHolds':[{'rank':x['continuationRank'],'sourceId':x['sourceId'],'source':x['source'],'locale':x['locale'],'current':x['currentTarget'],'reason':x['rationale']} for x in holds]}
write_jsonl(LEDGER,decisions); write_json(OUT/'blind-review-summary.json',summary)
# Build a worksheet directly from the independent ledger, after every cell was adjudicated.
lines=['# W55 independent blind review worksheet','',f"Exact head/tree: `{HEAD}` / `{TREE}`.",f"Candidate-free input manifest SHA-256: `{summary['inputManifestSha256']}`.",f"Counts: {dict(counts)}; exact proposed winners: {len(changes)}; terminology holds: {len(holds)}."]
for rank in range(276,301):
 group=[x for x in decisions if x['continuationRank']==rank]; first=group[0]
 lines+=['',f"## Rank {rank} — `{first['sourceId']}`",'',f"Source: {first['source']}",f"Pinned caller references: {first['callerCount']}"]
 for x in group:
  if x['verdict'].startswith('hold-'):
   lines.append(f"- **{x['locale']} hold-terminology:** unchanged `{x['currentTarget']}` — {x['rationale']}")
  elif x['candidateTarget']!=x['currentTarget']:
   lines.append(f"- **{x['locale']} {x['verdict']}:** `{x['currentTarget']}` → `{x['candidateTarget']}` — {x['rationale']}")
  else: lines.append(f"- {x['locale']}: accept-current")
(OUT/'blind-review-worksheet.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
readme=(f"# slskdN PR #409 W55 independent blind review\n\n"
 f"This independent blind review covers W49 stable-ID ranks 276–300, 25 sources × 12 locales = 300 cells, on live PR head/tree `{HEAD}` / `{TREE}`. It was prepared from the candidate-free input at `{IN}`; the primary review ledger was not consulted before this ledger was completed. Input manifest SHA-256: `{summary['inputManifestSha256']}`.\n\n"
 f"Dispositions: 193 accept-current, 59 corrections, 12 refinements, and 36 terminology holds. Exact proposed winners and reasons are in `blind-review-ledger.jsonl` and `blind-review-summary.json`. The holds cover `Pod` at ranks 278, 282, and 289 across all 12 locales because no approved localized product noun is provided.\n\n"
 "Pinned catalog values and all 40 production caller references were checked against the exact head. Candidate placeholder, markup, numeric-token, and protected-literal checks pass. Rank 288 keeps the parser’s ASCII comma-separated decimal-point sample syntax.\n\n"
 "This is machine-assisted review, not native-speaker approval or headed product-browser acceptance. No repository or PR edits, commits, pushes, tests, builds, scans, CI, or workflow changes were made. The PR remains open and draft.\n")
(OUT/'README.md').write_text(readme,encoding='utf-8')
# Seal the blind packet after the complete ledger, exact winners/holds, and worksheet exist.
rows=[]
for f in sorted(x for x in OUT.rglob('*') if x.is_file() and x.name not in {'PACKET-SHA256SUMS.txt'}):
 rows.append(f"{sha(f.read_bytes())}  {f.relative_to(OUT).as_posix()}")
(OUT/'PACKET-SHA256SUMS.txt').write_text('\n'.join(rows)+'\n',encoding='utf-8')
checks=verify_manifest(OUT,'PACKET-SHA256SUMS.txt')
assert len(jl(LEDGER))==300 and len(checks)==7
print(json.dumps({'verification':'blind-review-sealed','outputDir':str(OUT),'counts':dict(counts),'exactProposals':len(changes),'holds':len(holds),'holdRanks':summary['heldRanks'],'changedCellsByLocale':changes_by_locale,'currentProtectedMismatchCount':len(issues['currentProtected']),'candidateProtectedMismatchCount':len(issues['protectedCandidate']),'currentNumericMismatchCells':issues['currentNumeric'],'candidateNumericMismatchCount':len(issues['numericCandidate']),'placeholderMismatchCount':len(issues['placeholder']),'markupMismatchCount':len(issues['markup']),'inputManifestSha256':summary['inputManifestSha256'],'blindManifestEntriesVerified':len(checks),'blindManifestSha256':sha((OUT/'PACKET-SHA256SUMS.txt').read_bytes())},ensure_ascii=False,indent=2))
