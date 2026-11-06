from __future__ import annotations
import collections, hashlib, json, re
from pathlib import Path

OUT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window46-reconstructed-ranks26-50-primary-20261102')
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PROPOSALS={
 (31,'zh-Hant'):'選取 {directory} 中的所有檔案',
 (32,'de'):'ContentID für die Suche nach Treffern',
 (32,'es'):'ContentID para buscar coincidencias',
 (32,'fr'):'ContentID pour rechercher des correspondances',
 (32,'hi'):'मिलान खोजने के लिए ContentID',
 (32,'pt-BR'):'ContentID para buscar correspondências',
 (32,'vi'):'ContentID dùng để tìm các kết quả phù hợp',
 (30,'de'):'Websicherheitshärtung erzwingen',
 (34,'ja'):'競合解決戦略',
 (35,'ar'):'يرجى إدخال بيانات JSON لطلب المغادرة.',
 (35,'de'):'Bitte geben Sie die JSON-Daten für den Austrittsantrag ein.',
 (35,'es'):'Ingrese los datos JSON de la solicitud de salida.',
 (35,'fr'):'Veuillez saisir les données JSON de la demande de départ.',
 (35,'hi'):'कृपया सदस्यता छोड़ने के अनुरोध का JSON डेटा दर्ज करें।',
 (35,'id'):'Masukkan data JSON untuk permintaan keluar.',
 (35,'ja'):'退会リクエストの JSON データを入力してください。',
 (35,'ko'):'탈퇴 요청 JSON 데이터를 입력하세요.',
 (35,'pt-BR'):'Insira os dados JSON da solicitação de saída.',
 (35,'vi'):'Vui lòng nhập dữ liệu JSON cho yêu cầu rời nhóm.',
 (35,'zh-Hans'):'请输入退出请求的 JSON 数据。',
 (35,'zh-Hant'):'請輸入退出請求的 JSON 資料。',
 (41,'ar'):'تقييم',
 (41,'es'):'valoración',
 (41,'id'):'penilaian',
 (41,'zh-Hans'):'评分',
 (41,'zh-Hant'):'評分',
 (43,'ko'):'녹음 ID',
 (47,'ar'):'عدد الأيام حتى انتهاء صلاحية العناصر غير المصنفة',
 (47,'de'):'Tage bis zum Ablauf unbewerteter Einträge',
 (47,'es'):'Días hasta que caduquen los elementos sin valoración',
 (47,'fr'):'Nombre de jours avant l’expiration des éléments non évalués',
 (47,'hi'):'बिना रेटिंग वाले आइटम समाप्त होने तक के दिन',
 (47,'id'):'Hari hingga item tanpa penilaian kedaluwarsa',
 (47,'ja'):'未評価の項目が期限切れになるまでの日数',
 (47,'ko'):'미평가 항목이 만료되기까지의 일수',
 (47,'pt-BR'):'Dias até os itens sem avaliação expirarem',
 (47,'vi'):'Số ngày cho đến khi mục chưa được đánh giá hết hạn',
 (47,'zh-Hans'):'未评级条目过期前的天数',
 (47,'zh-Hant'):'未評級項目過期前的天數',
}
HOLD_RANKS={42:'The caller appends this one catalog word after a dynamic matched-track count. The count can take locale-specific plural categories, but the source exposes no count/ICU value to this fragment. Hold all locale cells until the caller uses a count-aware localized phrase.',
 49:'The same source word is rendered both as a standalone new-message separator and as the suffix after an unseen-result count. These contexts require different grammatical forms and, in several locales, a noun or count-sensitive form. Hold until the callers use separate/count-aware source messages.'}
RATIONALES={
 30:'This is the accessible name for an enabled/disabled security-hardening checkbox. Use a concise action label instead of a polite imperative sentence.',
 31:'The Traditional Chinese value is an aria-label for a checkbox that selects every file. The current translation names the files but omits the select action.',
 32:'This is a search-field placeholder. The current translations repeat the terminal preposition or leave a dangling “for”; rephrase as a concise “ContentID for searching matches” label and preserve ContentID.',
 34:'This Content Core dropdown selects a software conflict-handling policy. Use the Japanese computing term 競合 rather than 紛争, which suggests interpersonal disputes.',
 35:'The caller parses a request to leave a Pod membership (`requestPodLeave`); “leave request” here means departure/withdrawal, not vacation or time off. Preserve JSON.',
 41:'The caller displays a numeric user.rating value beside a peer. Use the rating/evaluation sense, not classification, rank, or grade.',
 43:'The caller is a music-discovery recording identifier. Korean 녹화 means video recording; use 녹음 for an audio recording.',
 47:'The numeric input is explicitly identified as Discovery shelf expiry days. Express this as the number of days until unrated items expire, matching the actual field value.',
}
SELECTION_CONTEXT={
 26:'Security/AdversarialSettings.jsx displays the relay-only maximum chain length.',
 27:'Pods/PortForwarding.jsx labels a statistic for total pod members.',
 28:'MediaCore/index.jsx heads a message containing similarity-analysis results.',
 29:'No exact production localization caller was found; the source is a Wishlist folder-ignore helper description.',
 30:'AdminPolicies/index.jsx uses this text as the accessible name for a web-security-hardening checkbox.',
 31:'Shared/FileList.jsx uses this string as the aria-label for the select-all-files checkbox.',
 32:'MediaCore/index.jsx uses this text as a ContentID search-field placeholder.',
 33:'No exact production localization caller was found for this label.',
 34:'MediaCore/index.jsx labels the software conflict-resolution strategy dropdown.',
 35:'MediaCorePods.jsx validates an empty leaveRequestData field before calling requestPodLeave.',
 36:'servarrReadiness.js formats this bullet line with separately localized status and title placeholders.',
 37:'No exact production localization caller was found; source is a download confirmation question.',
 38:'LibraryHealth/index.jsx uses this as the label for copying a review-only safe-fix manifest.',
 39:'Logs/index.jsx uses this as the accessible name for the recent/system log view button group.',
 40:'Collections.jsx displays a localized share-group name with an audienceId placeholder.',
 41:'SoulseekDiscoveryPanel.jsx displays user.rating as a numeric value beside a peer.',
 42:'PlaylistIntake.jsx concatenates summary.matched before this catalog fragment and punctuation after it.',
 43:'DiscoveryGraphAtlasPanel.jsx labels an audio recording identifier input.',
 44:'No exact production localization caller was found for this label.',
 45:'MediaCorePods.jsx labels the DHT Key value in publishing statistics.',
 46:'No exact production localization caller was found for this status message.',
 47:'PlayerBar.jsx uses this before a numeric input whose accessible label is Discovery shelf expiry days.',
 48:'MediaCorePods.jsx displays the count of failed DHT publications.',
 49:'MessageStream.jsx uses this as a standalone separator; Wishlist.jsx also appends it after unseenCount.',
 50:'RoomCreateModal.jsx and MediaCorePods.jsx use this colon label before explanatory or user-provided notes.',
}
EXPECTED={
 26:'Max Chain Length:',27:'Total Members',28:'Similarity Analysis Results',29:'Folder ignores are available only for wishlist searches because each rule belongs to one wishlist item. Open a result from Wishlist history to use them.',
 30:'Enforce web security hardening',31:'Select all files in {directory}',32:'ContentID to find matches for',33:'Missing:',34:'Conflict Resolution Strategy',35:'Please enter leave request JSON data',36:'- {status}: {title}',37:'Download {count} files from {directory}?',38:'Copy Safe-Fix Manifest',39:'Choose system log view',40:'Group {audienceId}',41:'rating',42:'tracks,',43:'Recording ID',44:'Quality Presets',45:'DHT Key:',46:'Unblocked {username}.',47:'Expire unrated after',48:'Failed Publications:',49:'new',50:'Note:'}

def readjl(path): return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
def writejl(path,rows): Path(path).write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rows))
def writej(path,obj): Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()

selection=readjl(OUT/'source-selection.jsonl'); cells=readjl(OUT/'input-cells.jsonl'); callers=readjl(OUT/'caller-context.jsonl')
assert len(selection)==25 and [x['selectionRank'] for x in selection]==list(range(26,51))
assert len(cells)==300 and len(callers)==25
sel={x['selectionRank']:x for x in selection}; call={x['selectionRank']:x for x in callers}; cell={(x['selectionRank'],x['locale']):x for x in cells}
assert set(cell)=={(r,l) for r in range(26,51) for l in LOCALES}
for r,expected in EXPECTED.items(): assert sel[r]['source']==expected,(r,sel[r]['source'],expected)
assert all(sel[r]['source']==EXPECTED[r] for r in {k[0] for k in PROPOSALS})
assert all(loc in LOCALES for _,loc in PROPOSALS)

placeholder_re=re.compile(r'\{([A-Za-z][A-Za-z0-9_]*)\}')
tag_re=re.compile(r'</?[A-Za-z][^>]*>')
protected={32:['ContentID'],35:['JSON'],45:['DHT']}
reviews=[]; structural=[]; proposals=[]; gaps=[]; spanish=[]
for rank in range(26,51):
 item=sel[rank]; caller=call[rank];
 for loc in LOCALES:
  inp=cell[(rank,loc)]; source=inp['source']; current=inp['currentTarget']; candidate=PROPOSALS.get((rank,loc)); is_hold=rank in HOLD_RANKS
  source_ph=sorted(placeholder_re.findall(source)); current_ph=sorted(placeholder_re.findall(current)); source_tags=tag_re.findall(source); current_tags=tag_re.findall(current)
  target=candidate if candidate is not None else (None if is_hold else current)
  target_ph=sorted(placeholder_re.findall(target)) if target is not None else None; target_tags=tag_re.findall(target) if target is not None else None
  current_lit_bad=[t for t in protected.get(rank,[]) if t not in current]
  target_lit_bad=[t for t in protected.get(rank,[]) if target is not None and t not in target]
  assert source_ph==current_ph,(rank,loc,'current placeholder mismatch')
  if target is not None: assert source_ph==target_ph,(rank,loc,'proposed placeholder mismatch')
  if target is not None: assert not target_lit_bad,(rank,loc,'protected literal mismatch',target_lit_bad)
  assert source_tags==current_tags
  if target is not None: assert source_tags==target_tags
  disposition='hold' if is_hold else ('propose-correction' if candidate is not None else 'accept-current')
  confidence='moderate' if rank in HOLD_RANKS else ('high' if rank in (31,34,35,41,43) else 'moderate')
  rationale=HOLD_RANKS[rank] if is_hold else (RATIONALES.get(rank,'Current wording preserves the meaning, placeholders, and product terminology in the exact pinned caller context.'))
  row={'exactHead':inp['exactHead'],'exactTree':inp['exactTree'],'selectionRank':rank,'selectionRankBasis':'ranks 26-50 in the deterministic reconstructed source-ID queue; no historical source ordinal is claimed','sourceOrdinal':None,'sourceId':inp['sourceId'],'sourceText':source,'sourceSha256':inp['sourceSha256'],'locale':loc,'catalogPath':inp['catalogPath'],'catalogBlobOid':inp['catalogBlobOid'],'catalogFileSha256':inp['catalogFileSha256'],'callerUseStatus':caller['callerUseStatus'],'callerRefsSourceId':inp['sourceId'],'callerContextSummary':SELECTION_CONTEXT[rank],'currentTarget':current,'currentTargetSha256':inp['currentTargetSha256'],'currentTargetPlaceholders':current_ph,'currentTargetMarkup':current_tags,'currentPlaceholderParity':'exact' if source_ph==current_ph else 'mismatch','currentMarkupParity':'exact' if source_tags==current_tags else 'mismatch','currentProtectedLiteralMismatches':current_lit_bad,'protectedLiterals':protected.get(rank,[]),'disposition':disposition,'proposedTarget':candidate,'proposedTargetSha256':sha(candidate) if candidate is not None else None,'reviewedTarget':target,'reviewedTargetSha256':sha(target) if target is not None else None,'reviewedTargetPlaceholders':target_ph,'reviewedTargetMarkup':target_tags,'reviewedPlaceholderParity':'held' if is_hold else ('exact' if source_ph==target_ph else 'mismatch'),'reviewedMarkupParity':'held' if is_hold else ('exact' if source_tags==target_tags else 'mismatch'),'reviewedProtectedLiteralMismatches':target_lit_bad,'protectedLiteralParity':'held' if is_hold else ('exact' if not target_lit_bad else 'mismatch'),'rationale':rationale,'confidence':confidence,'nativeSpeakerReview':'outstanding','spanishFormalApplicability':'formal-imperative-in-target' if loc=='es' and rank==35 else ('not-applicable-no-direct-address-in-source' if loc=='es' else None)}
  reviews.append(row)
  structural.append({'selectionRank':rank,'sourceId':inp['sourceId'],'locale':loc,'sourceSha256':inp['sourceSha256'],'currentTargetSha256':inp['currentTargetSha256'],'disposition':disposition,'reviewedTargetSha256':sha(target) if target is not None else None,'sourcePlaceholders':source_ph,'currentPlaceholders':current_ph,'reviewedPlaceholders':target_ph,'currentPlaceholderParity':'exact' if source_ph==current_ph else 'mismatch','reviewedPlaceholderParity':'held' if is_hold else ('exact' if source_ph==target_ph else 'mismatch'),'placeholderParity':'held' if is_hold else ('exact' if source_ph==target_ph else 'mismatch'),'sourceMarkup':source_tags,'currentMarkup':current_tags,'reviewedMarkup':target_tags,'currentMarkupParity':'exact' if source_tags==current_tags else 'mismatch','reviewedMarkupParity':'held' if is_hold else ('exact' if source_tags==target_tags else 'mismatch'),'markupParity':'held' if is_hold else ('exact' if source_tags==target_tags else 'mismatch'),'protectedLiterals':protected.get(rank,[]),'currentProtectedLiteralMismatches':current_lit_bad,'reviewedProtectedLiteralMismatches':target_lit_bad,'currentProtectedLiteralParity':'exact' if not current_lit_bad else 'mismatch','protectedLiteralParity':'held' if is_hold else ('exact' if not target_lit_bad else 'mismatch')})
  if candidate is not None: proposals.append({'selectionRank':rank,'sourceId':inp['sourceId'],'sourceText':source,'sourceSha256':inp['sourceSha256'],'locale':loc,'currentTarget':current,'currentTargetSha256':inp['currentTargetSha256'],'proposedTarget':candidate,'proposedTargetSha256':sha(candidate),'rationale':RATIONALES[rank],'confidence':confidence})
  if loc=='es': spanish.append({'selectionRank':rank,'sourceId':inp['sourceId'],'sourceText':source,'formalApplicability':row['spanishFormalApplicability'],'reviewedTarget':target,'disposition':disposition})

for rank,reason in HOLD_RANKS.items():
 item=sel[rank]; caller=call[rank]
 gaps.append({'selectionRank':rank,'sourceId':item['sourceId'],'sourceText':item['source'],'sourceSha256':item['sourceSha256'],'callerUseStatus':caller['callerUseStatus'],'callerRefs':caller['callerRefs'],'reason':reason,'affectedLocaleCount':12,'affectedCells':12,'recommendedSourceOrCallerRemediation':'Use a context-specific source message with count-aware plural formatting for tracks, and separate the standalone new separator from the count-bearing wishlist badge.' if rank==49 else 'Pass the numeric count into a plural-aware localized message, including locale-specific singular/other or Arabic plural branches; do not concatenate a generic catalog fragment after the count.'})

counts=collections.Counter(x['disposition'] for x in reviews)
assert len(reviews)==300 and counts['hold']==24 and len(proposals)==39
writejl(OUT/'review-decisions.jsonl',reviews)
writejl(OUT/'candidate-proposals.jsonl',proposals)
writejl(OUT/'structural-validation.jsonl',structural)
writejl(OUT/'source-runtime-gaps.jsonl',gaps)
writejl(OUT/'spanish-formal-applicability.jsonl',spanish)
summary={'repository':'snapetech-org/slskdN','pullRequest':409,'windowLabel':'W46 deterministic reconstruction, pending source-ID ranks 26-50; historical ordinal unavailable','exactHead':cells[0]['exactHead'],'exactTree':cells[0]['exactTree'],'sourceCount':25,'cellCount':300,'localeCount':12,'selectionRanks':[26,50],'dispositionCounts':dict(sorted(counts.items())),'proposalCount':len(proposals),'holdSourceIds':[sel[r]['sourceId'] for r in HOLD_RANKS],'heldCells':sum(counts[k] for k in ('hold',)),'directCallerRows':sum(x['callerUseStatus']=='production-localization-reference-found' for x in callers),'callerReferences':sum(x['callerReferenceCount'] for x in callers),'productionCallerGaps':[{'selectionRank':x['selectionRank'],'sourceId':x['sourceId'],'source':x['source']} for x in callers if x['callerUseStatus']!='production-localization-reference-found'],'placeholderMismatchesCurrent':sum(x['currentPlaceholderParity']!='exact' for x in structural),'placeholderMismatchesReviewed':sum(x['placeholderParity']=='mismatch' for x in structural),'markupMismatchesCurrent':sum(x['currentMarkupParity']!='exact' for x in structural),'markupMismatchesReviewed':sum(x['markupParity']=='mismatch' for x in structural),'protectedLiteralMismatchesReviewed':sum(bool(x['reviewedProtectedLiteralMismatches']) for x in structural),'nativeSpeakerApproval':False,'headedBrowserReview':False,'testsBuildScansCiRun':False,'repositoryModified':False,'sourceIds':[sel[r]['source'] for r in range(26,51)]}
writej(OUT/'review-summary.json',summary)
readme=f'''# slskdN PR #409 primary semantic review — W46 reconstructed ranks 26–50\n\nReviewed 25 source IDs × 12 direct locales (300 cells) at exact OPEN/DRAFT PR head {summary['exactHead']} / tree {summary['exactTree']}. Selection is a deterministic reconstruction from the stable-ID queue after excluding the W1–W45 evidence set. Ranks 26–50 correspond to the second 25 entries in the original reconstructed W1–W44 pending order; no historical source ordinal is claimed.\n\nPrimary dispositions: {dict(sorted(counts.items()))}. The 39 proposed corrections cover the web-security checkbox name, select-all Traditional Chinese action, ContentID search placeholders, software conflict terminology, departure-request JSON wording, peer rating labels, Korean audio-recording terminology, and the discovery-shelf expiry-day label.\n\nTwo context issues remain held across all 12 locales (24 cells total): `tracks,` is concatenated after a dynamic count without locale plural handling; `new` is shared by a standalone message separator and a count-bearing Wishlist badge. Both require caller-level localization before target cells can be accepted. Their exact references and recommended remediation are recorded in `source-runtime-gaps.jsonl`. Five source IDs have no exact production localization caller; those are explicitly listed in the caller context packet.\n\nPlaceholder, markup, and protected-literal checks pass for every proposed target. Protected literals `ContentID`, `JSON`, and `DHT` remain intact. This is static machine-assisted primary review; native-speaker approval and headed-browser review remain outstanding. No repository files were modified; no tests, builds, scans, or CI ran.\n'''
(OUT/'README.md').write_text(readme)
# Capture all files created by preparation and review, excluding the checksum/manifest being generated.
def manifest():
 files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name not in ('SHA256SUMS.txt','manifest.json'))
 (OUT/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.name}\n' for p in files))
 obj={'repository':'snapetech-org/slskdN','pullRequest':409,'window':'W46 reconstructed ranks 26-50','head':summary['exactHead'],'tree':summary['exactTree'],'sourceCount':25,'cellCount':300,'dispositionCounts':dict(sorted(counts.items())),'proposalCount':len(proposals),'holdCellCount':counts['hold'],'files':[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in files],'sha256SumsSha256':sha((OUT/'SHA256SUMS.txt').read_bytes())}
 writej(OUT/'manifest.json',obj)
manifest()
print(json.dumps({'summary':summary,'manifestSha256':sha((OUT/'manifest.json').read_bytes()),'sha256SumsSha256':sha((OUT/'SHA256SUMS.txt').read_bytes())},ensure_ascii=False,indent=2))
