from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import hashlib, json, re, shutil, subprocess

T=Path('/home/keith/Documents/code/task-scratch/slskdn-pr409-w64-blind-20261103')
IN=Path('/home/keith/Documents/code/task-scratch/slskdn-pr409-w64-ranks478-502-primary-20261103/input')
OUT=T/'review'
HEAD='3cc9db334cfb1693dd6bd93bb83cfeba65930adb'
TREE='9d40e239e7e717a81bd176d143d1ce067fe026a1'
BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
INPUT_MANIFEST_SHA='4f428c69b3abec8db8ad9d7796f5c9a6e9e6da9234361cc644721b932de05456'
INPUT_SUMS_SHA='2064eb36dcd2bc27344f73c57b62e8e3078d087da115fe04d52348a30855e5c8'
PH=re.compile(r'\{[^{}\r\n]+\}')
MK=re.compile(r'</?[A-Za-z][^<>]*?/?>')
NUM=re.compile(r'(?<!\w)[+-]?\d+(?:[.,]\d+)?%?(?!\w)')

def sha(b): return hashlib.sha256(b).hexdigest()
def st(s): return sha(s.encode('utf-8'))
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def wj(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def wjl(p,rows): p.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rows),encoding='utf-8')
def live_attest():
 pr=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','number,state,isDraft,headRefName,headRefOid,baseRefName,baseRefOid,url'],text=True))
 refs=subprocess.check_output(['git','ls-remote','https://github.com/snapetech-org/slskdN.git',f'refs/heads/{BRANCH}','refs/pull/409/head'],text=True)
 refmap={line.split()[1]:line.split()[0] for line in refs.splitlines() if line.strip()}
 tree=subprocess.check_output(['gh','api',f'repos/snapetech-org/slskdN/commits/{HEAD}','--jq','.commit.tree.sha'],text=True).strip()
 assert (pr['number'],pr['state'],pr['isDraft'],pr['headRefName'],pr['headRefOid'],pr['baseRefName'])==(409,'OPEN',True,BRANCH,HEAD,'main'),pr
 assert refmap=={f'refs/heads/{BRANCH}':HEAD,'refs/pull/409/head':HEAD},refmap
 assert tree==TREE,tree
 return {'repository':'snapetech-org/slskdN','pullRequest':409,'state':pr['state'],'draft':pr['isDraft'],'branch':BRANCH,'head':HEAD,'tree':TREE,'branchRef':refmap[f'refs/heads/{BRANCH}'],'pullRef':refmap['refs/pull/409/head'],'baseBranch':pr['baseRefName'],'baseHead':pr['baseRefOid'],'prUrl':pr['url'],'reattestedAtUTC':datetime.now(timezone.utc).isoformat()}

PROPOSALS={
# rank 478: caller is MediaCorePods and the adjacent field is “Leave Acceptance JSON (signed by owner/mod)”.
(478,'ar'):('قبول طلب المغادرة (للمالك/المشرف فقط)','correction','moderate'),
(478,'de'):('Antrag auf Austritt annehmen (nur Eigentümer/Moderatoren)','correction','moderate'),
(478,'es'):('Aceptar solicitud de salida (solo propietario/moderador)','correction','moderate'),
(478,'fr'):('Accepter la demande de départ (propriétaire/modérateur uniquement)','correction','moderate'),
(478,'hi'):('छोड़ने का अनुरोध स्वीकार करें (केवल मालिक/मॉडरेटर)','correction','moderate'),
(478,'id'):('Terima permintaan untuk keluar (hanya pemilik/moderator)','correction','moderate'),
(478,'ja'):('退出リクエストを受け入れる（オーナー/モデレーターのみ）','correction','moderate'),
(478,'ko'):('나가기 요청 수락 (소유자/모더레이터 전용)','correction','moderate'),
(478,'pt-BR'):('Aceitar solicitação para sair (somente proprietário/moderador)','correction','moderate'),
(478,'vi'):('Chấp nhận yêu cầu rời đi (chỉ chủ sở hữu/người kiểm duyệt)','correction','moderate'),
(478,'zh-Hans'):('接受退出请求（仅限所有者/版主）','correction','moderate'),
(478,'zh-Hant'):('接受退出請求（僅限擁有者/版主）','correction','moderate'),
# rank 480: caller uses collectionShares; the text is about sharing collection content, not equity.
(480,'ar'):('لا توجد عناصر مشتركة حتى الآن.','correction','high'),
(480,'de'):('Noch keine geteilten Inhalte.','correction','high'),
(480,'es'):('Aún no hay elementos compartidos.','correction','high'),
(480,'hi'):('अभी तक साझा की गई कोई सामग्री नहीं है।','correction','moderate'),
(480,'id'):('Belum ada item yang dibagikan.','correction','high'),
(480,'zh-Hans'):('目前还没有共享内容。','correction','high'),
(480,'zh-Hant'):('目前還沒有分享內容。','correction','high'),
# rank 482: media-server scrobble export description; plays are playback events and ratings are evaluations.
(482,'ar'):('صدّر عمليات التشغيل أو التقييمات المحلية المؤكدة إلى ملف تعريف خادم الوسائط المحدد.','correction','moderate'),
(482,'es'):('Exporte las reproducciones o valoraciones locales confirmadas al perfil del servidor de medios seleccionado.','correction','moderate'),
(482,'fr'):('Exportez les lectures ou les notes locales confirmées vers le profil de serveur multimédia sélectionné.','correction','moderate'),
(482,'hi'):('पुष्ट स्थानीय प्लेबैक या रेटिंग को चयनित मीडिया सर्वर प्रोफ़ाइल पर वापस निर्यात करें।','correction','high'),
(482,'id'):('Ekspor pemutaran atau penilaian lokal yang terkonfirmasi kembali ke profil server media yang dipilih.','correction','moderate'),
(482,'pt-BR'):('Exporte reproduções ou avaliações locais confirmadas de volta para o perfil do servidor de mídia selecionado.','refinement','moderate'),
(482,'vi'):('Xuất các lượt phát hoặc đánh giá cục bộ đã xác nhận trở lại cấu hình máy chủ phương tiện đã chọn.','correction','moderate'),
(482,'zh-Hans'):('将已确认的本地播放记录或评分导出回选定的媒体服务器配置文件。','correction','high'),
(482,'zh-Hant'):('將已確認的本機播放記錄或評分匯出回選定的媒體伺服器設定檔。','correction','high'),
# rank 487: keep the feature name Wishlist exact in every locale.
(487,'ar'):('إضافة نتيجة Wishlist المرفوضة إلى القائمة السوداء','correction','high'),
(487,'de'):('Abgelehnte Wishlist-Ergebnisse auf die Sperrliste setzen','correction','high'),
(487,'es'):('Añadir los resultados de Wishlist rechazados a la lista negra','correction','high'),
(487,'fr'):('Ajouter les résultats Wishlist refusés à la liste noire','correction','high'),
(487,'hi'):('अस्वीकृत Wishlist परिणामों को ब्लैकलिस्ट करें','correction','high'),
(487,'id'):('Masukkan hasil Wishlist yang ditolak ke daftar hitam','correction','high'),
(487,'ja'):('拒否された Wishlist の結果をブラックリストに登録','correction','high'),
(487,'ko'):('거부된 Wishlist 결과를 차단 목록에 추가','correction','high'),
(487,'pt-BR'):('Adicionar os resultados rejeitados da Wishlist à lista de bloqueio','correction','high'),
(487,'vi'):('Đưa các kết quả Wishlist bị từ chối vào danh sách đen','correction','high'),
(487,'zh-Hans'):('将被拒绝的 Wishlist 结果加入黑名单','correction','high'),
(487,'zh-Hant'):('將遭拒絕的 Wishlist 結果加入黑名單','correction','high'),
# rank 489 is a popup tooltip; “inline” means within the page, not online or in a line.
(489,'es'):('Muestra las búsquedas vinculadas y los resultados anteriores de este elemento directamente en la página.','refinement','moderate'),
(489,'pt-BR'):('Mostre as pesquisas vinculadas e os resultados anteriores deste item diretamente na página.','refinement','moderate'),
# rank 491 button queues remediation for an auto-fixable issue.
(491,'ar'):('إصلاح','refinement','moderate'),
(491,'id'):('Perbaiki','refinement','moderate'),
(491,'ja'):('修正','refinement','moderate'),
(491,'ko'):('수정','refinement','moderate'),
(491,'zh-Hans'):('修复','correction','high'),
(491,'zh-Hant'):('修復','correction','high'),
# rank 493 is technical metadata fingerprinting; avoid biometric-only wording.
(493,'ar'):('فشل استخراج البصمة الرقمية: {exceptionType}: {message}','refinement','moderate'),
(493,'fr'):('Échec de l’extraction de l’empreinte numérique : {exceptionType} : {message}','refinement','moderate'),
# rank 498 is a loader displaying LibraryHealth issues, rather than a message about failed loading.
(498,'de'):('Probleme werden geladen...','correction','high'),
(498,'es'):('Cargando incidencias...','correction','high'),
(498,'fr'):('Chargement des problèmes...','correction','moderate'),
(498,'id'):('Memuat masalah...','correction','high'),
(498,'ko'):('문제를 불러오는 중...','correction','high'),
(498,'vi'):('Đang tải các sự cố...','correction','moderate'),
# rank 499 is a completed import status, not an in-progress loading status.
(499,'id'):('Berhasil memuat {fileName} untuk ditinjau.','correction','high'),
(499,'fr'):('Fichier {fileName} chargé pour examen.','refinement','moderate'),
(499,'ja'):('レビュー用に{fileName}を読み込みました。','refinement','moderate'),
(499,'pt-BR'):('Arquivo {fileName} carregado para revisão.','refinement','moderate'),
# rank 500 is the accessible button label for stopping an ongoing room playback-state broadcast.
(500,'vi'):('Dừng phát sóng đang hoạt động của phòng','refinement','moderate'),
(500,'zh-Hans'):('停止正在进行的房间广播','refinement','moderate'),
(500,'zh-Hant'):('停止進行中的房間廣播','refinement','moderate'),
# rank 501 is an opaque status value interpolated into a generated review report; preserve exact ACCEPT.
**{(501,loc):('ACCEPT','correction','high') for loc in ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']},
# rank 502 is a section heading for pending requests to join pods.
(502,'es'):('Solicitudes para unirse:','refinement','moderate'),
(502,'zh-Hans'):('加入请求：','correction','high'),
(502,'zh-Hant'):('加入請求：','correction','high'),
}
RATIONAL_OVERRIDES={
 (499,'id'):'The caller sets this status after file.text() completes. The current Indonesian target says the file is being loaded, while the source reports completion; this target states that the file loaded successfully for review.',
 (499,'fr'):'The caller sets this status after file.text() completes. Naming the file first makes the French completed-load status grammatical and preserves its review purpose.',
 (499,'ja'):'The caller sets this status after file.text() completes. 読み込みました is the natural Japanese completed-load wording here and preserves the review purpose.',
 (499,'pt-BR'):'The caller sets this status after file.text() completes. Naming the file first makes the Portuguese completed-load status grammatical and preserves its review purpose.',
}
REASONS={
 478:'The exact caller is in MediaCorePods beside “Leave Acceptance JSON (signed by owner/mod)”. That context points to accepting a departure request, not a vacation absence. The current translations in this locale render leave as time off and/or leave Mod ambiguous; this target states departure and the owner/moderator restriction.',
 480:'The caller reads collectionShares.length under the Collections page’s Shares heading. In this context shares are shared collection content, not stock shares or a division; the target now names shared items/content.',
 482:'The exact callers describe a media-server scrobble export. Here plays means playback activity and ratings means user evaluations; the current wording in this locale refers to stage plays, rankings, or audience ratings. This target states playback and user ratings.',
 487:'The caller is the Lidarr blacklist setting label. The setting acts on rejected Wishlist results, so the product feature name must remain exactly Wishlist and the phrase must state that rejected results are blacklisted.',
 489:'The pinned caller renders this source as a popup tooltip for a button. Inline means displaying linked searches and earlier results within the current page/view, not online or as a line of text.',
 491:'The caller is a Fix button for an auto-fixable LibraryHealth issue; its tooltip says it queues a remediation job. This target is a concise repair action and avoids the current Chinese sense of fastening something in place.',
 493:'The pinned caller is metadata-processing error detail. Fingerprint here is a technical digital fingerprint, not a biometric fingerprint; this wording removes the biometric-only reading while preserving both exact exception placeholders.',
 498:'The pinned caller shows a LoaderSegment while LibraryHealth issues are fetched. The current wording in this locale reads as problems with loading; this target says that the issues themselves are being loaded.',
 499:'This status is set after file.text() completes. The current Indonesian target says the file is being loaded, while the source reports completion; this target preserves the completed state and review purpose.',
 500:'The caller is the accessible button label for stopping the room broadcast; the adjacent popup specifies that this stops room broadcasting while keeping local playback available. This target describes an ongoing room broadcast rather than an active room.',
 501:'The caller inserts this value as a status inside a generated review report. ACCEPT is pinned as an opaque protected value, so it must stay exact and uppercase across locales.',
 502:'The caller renders a section heading for pending pod join requests. 加盟 implies commercial affiliation/franchising in Chinese, so 加入 is the clear verb for joining here; the Spanish target also reads more naturally as requests to join.',
}

assert not OUT.exists(), OUT
assert sha((IN/'manifest.json').read_bytes())==INPUT_MANIFEST_SHA
assert sha((IN/'PACKET-SHA256SUMS.txt').read_bytes())==INPUT_SUMS_SHA
subprocess.run(['python3',str(IN/'verify_input.py')],check=True,capture_output=True,text=True)
input_verify=subprocess.check_output(['python3',str(IN/'verify_input.py')],text=True)
# Reattest immediately before preparing the blind packet.
live=live_attest()
manifest=j(IN/'manifest.json'); boundary=j(IN/'selection-and-boundary.json')
assert manifest['head']==HEAD and manifest['tree']==TREE and manifest['cellCount']==300
assert boundary['selection']['continuationRankStart']==478 and boundary['selection']['continuationRankEnd']==502
rows=jl(IN/'source-current-cells.jsonl'); callers={x['continuationRank']:x for x in jl(IN/'caller-contexts.jsonl')}
assert len(rows)==300 and len(callers)==25
bykey={(x['continuationRank'],x['locale']):x for x in rows}; assert len(bykey)==300
assert set(PROPOSALS)<=set(bykey)
locales=sorted({x['locale'] for x in rows}); assert len(locales)==12
ledger=[]; selected=[]; callerless=[]
for x in rows:
 rank=x['continuationRank']; locale=x['locale']; key=(rank,locale); caller=callers[rank]
 assert caller['sourceId']==x['sourceId'] and caller['sourceSha256']==x['sourceSha256']
 assert isinstance(x['callerContextSha256'],str) and re.fullmatch(r'[0-9a-f]{64}',x['callerContextSha256']), (key,'caller context hash')
 count=caller['productionCallerCount']
 if count==0: callerless.append(key)
 prop=PROPOSALS.get(key)
 if count==0:
  assert prop is None and rank==486
  target=x['currentTarget']; disposition='hold'; confidence='high'
  rationale='No exact production caller was found for this source in the pinned bounded scan. The packet supplies no caller context that can resolve how this text is used, so preserve the current locale value and hold it without proposing a replacement.'
 elif prop:
  target,disposition,confidence=prop; rationale=RATIONAL_OVERRIDES.get(key,REASONS[rank])
  assert target != x['currentTarget']
 else:
  target=x['currentTarget']; disposition='accept-current'; confidence='moderate'
  rationale='The current target conveys the source meaning in the pinned production-caller context. Its placeholders, markup, numeric content, and protected literals match the source, and the context gives no reason to change this translation.'
 src_ph=x['placeholderEvidence']['sourceTokens']; cur_ph=x['placeholderEvidence']['currentTokens']; final_ph=PH.findall(target)
 src_mk=x['markupEvidence']['sourceTags']; cur_mk=x['markupEvidence']['currentTags']; final_mk=MK.findall(target)
 src_num=x['sourceNumericTokens']; cur_num=x['currentNumericTokens']; final_num=NUM.findall(target)
 src_prot=x['sourceProtectedLiterals']; cur_prot=x['currentProtectedLiterals']; final_prot=[v for v in src_prot if v in target]
 assert final_ph==src_ph and final_mk==src_mk and final_num==src_num, (key,'structural tokens',src_ph,final_ph,src_mk,final_mk,src_num,final_num)
 assert all(v in target for v in src_prot), (key,'protected literals',src_prot,target)
 crefs=[]
 for c in caller['callers']:
  crefs.append({'path':c['path'],'line':c['line'],'lineText':c['lineText'],'lineSha256':c['lineSha256'],'contextSha256':c['contextSha256'],'fileSha256':c['fileSha256'],'gitBlob':c['gitBlob']})
 row={'schemaVersion':1,'repository':'snapetech-org/slskdN','pullRequest':409,'window':'W64-ranks-478-502','head':HEAD,'tree':TREE,'continuationRank':rank,'remainingQueueRank':x['remainingQueueRank'],'sourceId':x['sourceId'],'source':x['source'],'sourceSha256':x['sourceSha256'],'locale':locale,'currentTarget':x['currentTarget'],'currentTargetSha256':x['currentTargetSha256'],'blindTarget':target,'blindTargetSha256':st(target),'disposition':disposition,'confidence':confidence,'rationale':rationale,'catalogPath':x['catalogPath'],'catalogFileSha256':x['catalogFileSha256'],'catalogGitBlob':x['catalogGitBlob'],'callerContextSha256':x['callerContextSha256'],'productionCallerCount':count,'callerReferences':crefs,'callerlessHold':count==0,'placeholderChecks':{'sourceTokens':src_ph,'currentTokens':cur_ph,'blindTokens':final_ph,'currentMatchesSource':x['placeholderEvidence']['matches'],'blindMatchesSource':final_ph==src_ph},'markupChecks':{'sourceTags':src_mk,'currentTags':cur_mk,'blindTags':final_mk,'currentMatchesSource':x['markupEvidence']['matches'],'blindMatchesSource':final_mk==src_mk},'numericChecks':{'sourceTokens':src_num,'currentTokens':cur_num,'blindTokens':final_num,'currentMatchesSource':cur_num==src_num,'blindMatchesSource':final_num==src_num},'protectedLiteralChecks':{'sourceLiterals':src_prot,'currentLiterals':cur_prot,'currentMatchesSource':x['protectedLiteralEvidence']['matches'],'blindLiterals':final_prot,'blindMatchesSource':all(v in target for v in src_prot)}}
 ledger.append(row)
 if disposition in {'correction','refinement'}:
  selected.append({k:row[k] for k in ['schemaVersion','repository','pullRequest','window','head','tree','continuationRank','remainingQueueRank','sourceId','source','sourceSha256','locale','currentTarget','currentTargetSha256','blindTarget','blindTargetSha256','disposition','confidence','rationale','catalogPath','catalogFileSha256','catalogGitBlob','callerContextSha256','productionCallerCount','callerReferences','placeholderChecks','markupChecks','numericChecks','protectedLiteralChecks']})
assert len(ledger)==300 and len(selected)==len(PROPOSALS)
assert set(callerless)=={(486,loc) for loc in locales} and len(callerless)==12
counts=Counter(r['disposition'] for r in ledger)
assert counts['hold']==12 and counts['correction']+counts['refinement']==len(selected)
prior=j(IN/'prior-held-cell-reattestation-summary.json')
assert prior['priorHeldCellsReattested']==prior['expectedHeldCells']==86 and prior['allTargetHashesMatchPrior'] is True
assert prior['allCurrentCallerAndCatalogEvidenceRepinned'] is True
OUT.mkdir()
wjl(OUT/'blind-ledger.jsonl',ledger); wjl(OUT/'selected-direct-locale-cells.jsonl',selected)
now=datetime.now(timezone.utc).isoformat()
wj(OUT/'live-attestation.json',live)
(OUT/'input-verification.txt').write_text(input_verify,encoding='utf-8')
summary={'schemaVersion':1,'repository':'snapetech-org/slskdN','pullRequest':409,'window':'W64-ranks-478-502','head':HEAD,'tree':TREE,'candidateFreeManifestJsonSha256':INPUT_MANIFEST_SHA,'candidateFreeChecksumListSha256':INPUT_SUMS_SHA,'sourceCount':25,'localeCount':12,'cellCount':300,'dispositions':dict(counts),'proposedChanges':len(selected),'proposedChangesByDisposition':dict(Counter(r['disposition'] for r in selected)),'proposedChangesByLocale':dict(Counter(r['locale'] for r in selected)),'proposedChangesByRank':dict(Counter(str(r['continuationRank']) for r in selected)),'currentCallerlessHoldRanks':[486],'currentCallerlessHoldCells':12,'priorHeldCellsReattestedAndPreserved':86,'baselinePlaceholderMismatches':0,'baselineMarkupMismatches':0,'baselineNumericMismatches':0,'baselineProtectedLiteralMismatches':23,'blindPlaceholderMismatches':0,'blindMarkupMismatches':0,'blindNumericMismatches':0,'blindProtectedLiteralMismatches':0,'nativeSpeakerApproval':False,'browserReview':False,'independentBlindReview':True,'reviewedAtUTC':now}
prov={'schemaVersion':1,'repository':'snapetech-org/slskdN','pullRequest':409,'window':'W64-ranks-478-502','head':HEAD,'tree':TREE,'candidateFreeManifestJsonSha256':INPUT_MANIFEST_SHA,'candidateFreeChecksumListSha256':INPUT_SUMS_SHA,'candidateFreeHashesAreSeparateFiles':True,'reviewType':'independent blind semantic review using candidate-free input only','primaryReviewRead':False,'otherAuditRead':False,'all300CellsReviewed':True,'callerContextsUsed':True,'currentCallerlessHoldsPreserved':callerless,'priorHeldCellsReattestedAndPreserved':86,'nativeSpeakerApproval':False,'browserReview':False,'reviewedAtUTC':now}
wj(OUT/'summary.json',summary); wj(OUT/'provenance.json',prov)
readme=f"""Independent blind semantic review for slskdN PR #409 W64 ranks 478–502, pinned to {HEAD} / tree {TREE}.

This review uses only the sealed candidate-free packet at `{IN}`. It covers all 300 cells across 25 source rows and 12 locales. Decisions: {counts['accept-current']} accept-current, {counts['correction']} corrections, {counts['refinement']} refinements, and {counts['hold']} holds. The {len(selected)} proposed changes are in selected-direct-locale-cells.jsonl with exact current and proposed values/hashes, caller evidence, rationale, confidence, and structural-token checks.

All 12 current values at callerless rank 486 remain held. The 86 prior held cells are reattested unchanged in the candidate-free packet. The packet records 23 baseline protected-literal mismatches; blind proposals restore the protected literals, including `Wishlist` and the exact `ACCEPT` status. Placeholder, markup, and numeric checks pass for all final targets.

Candidate-free lineage is explicit: manifest JSON SHA-256 {INPUT_MANIFEST_SHA}; packet checksum-list SHA-256 {INPUT_SUMS_SHA}. They identify separate files. This blind review is proposal-only; native-speaker and browser signoff remain false. No repository or PR edits were made.
"""
(OUT/'README.md').write_text(readme,encoding='utf-8')
shutil.copy2(T/'verify_blind_review.py',OUT/'verify_blind_review.py')
shutil.copy2(T/'build_blind_review.py',OUT/'build_blind_review.py')
checks=[f"{sha(p.read_bytes())}  {p.name}" for p in sorted(q for q in OUT.iterdir() if q.is_file() and q.name!='SHA256SUMS.txt')]
(OUT/'SHA256SUMS.txt').write_text('\n'.join(checks)+'\n',encoding='utf-8')
print(json.dumps({'result':'blind review generated','head':HEAD,'tree':TREE,'cells':len(ledger),'dispositions':dict(counts),'proposedChanges':len(selected),'currentCallerlessHolds':len(callerless),'priorHeldCellsPreserved':86,'candidateFreeManifestJsonSha256':INPUT_MANIFEST_SHA,'candidateFreeChecksumListSha256':INPUT_SUMS_SHA,'blindChecksumListSha256':sha((OUT/'SHA256SUMS.txt').read_bytes())},ensure_ascii=False,indent=2))
