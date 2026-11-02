#!/usr/bin/env python3
import collections, hashlib, json, re
from pathlib import Path
ROOT=Path('/mnt/disks/scratch/task-scratch/slskdn-manual-review-window33-0abf10ae-20261102')
LOCALES=['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
def sha(value): return hashlib.sha256(value if isinstance(value,bytes) else value.encode('utf-8')).hexdigest()
def read_jsonl(path): return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
def write_jsonl(path, rows): path.write_text(''.join(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for row in rows),encoding='utf-8')

fixes={
 'src_01de77717ad6d8ac': {'fr':('Obtenez des opinions agrégées','The button asks for aggregated opinions in MediaCore. The current French word globales describes global or worldwide opinions rather than opinions combined into an aggregate.','high')},
 'src_01f15db89c14092f': {'fr':('DHT uniquement sur le réseau local','This toggle restricts DHT rendezvous to private or local discovery paths. The current French word order makes the DHT/LAN relationship unclear.','moderate')},
 'src_022b431a245e7a24': {
  'fr':('Port TCP du réseau superposé DHT','The setting is the TCP port for the DHT overlay network. The current superposition is the geometric sense of overlay and obscures the networking term.','moderate'),
  'ar':('منفذ TCP لشبكة تراكب DHT','The setting is the TCP port for the DHT overlay network. The current mixed-language word order makes the port/network relationship unclear.','moderate'),
  'id':('Port TCP jaringan overlay DHT','The setting is the TCP port for the DHT overlay network. Hamparan means an expanse or spread and is not a clear networking term here; overlay preserves the established technical term.','moderate'),
 },
 'src_0240829060eab635': {
  'zh-Hans':('获取会员记录','The button performs a read-only lookup of the selected peer’s membership record for the pod, as its tooltip states. The current wording can read as acquiring member status; this names the record being fetched.','high'),
  'hi':('सदस्यता रिकॉर्ड प्राप्त करें','The button performs a read-only lookup of the selected peer’s membership record for the pod, as its tooltip states. The current wording can read as acquiring membership; this names the record being fetched.','high'),
  'de':('Mitgliedschaftsdatensatz abrufen','The button performs a read-only lookup of the selected peer’s membership record for the pod, as its tooltip states. The current wording can read as joining or receiving a membership; this names the record being fetched.','high'),
  'ja':('会員記録を取得する','The button performs a read-only lookup of the selected peer’s membership record for the pod, as its tooltip states. The current wording can read as acquiring membership; this names the record being fetched.','high'),
  'fr':('Récupérer le dossier d’adhésion','The button performs a read-only lookup of the selected peer’s membership record for the pod, as its tooltip states. Devenez membre means become a member, the opposite of this lookup action.','high'),
  'pt-BR':('Consultar registro de membro','The button performs a read-only lookup of the selected peer’s membership record for the pod, as its tooltip states. Assinatura means subscription and does not identify the membership record.','high'),
  'ar':('استرجع سجل العضوية','The button performs a read-only lookup of the selected peer’s membership record for the pod, as its tooltip states. The current wording can read as acquiring membership; this names the record being fetched.','moderate'),
  'ko':('회원 기록 조회','The button performs a read-only lookup of the selected peer’s membership record for the pod, as its tooltip states. 회원가입 means membership registration/joining rather than looking up an existing record.','high'),
  'zh-Hant':('取得會員記錄','The button performs a read-only lookup of the selected peer’s membership record for the pod, as its tooltip states. The current wording can read as acquiring member status; this names the record being fetched.','high'),
  'vi':('Lấy hồ sơ thành viên','The button performs a read-only lookup of the selected peer’s membership record for the pod, as its tooltip states. The current wording names member status rather than the existing record being fetched.','high'),
  'id':('Ambil catatan keanggotaan','The button performs a read-only lookup of the selected peer’s membership record for the pod, as its tooltip states. The current wording can read as acquiring/joining membership; this names the record being fetched.','high'),
 },
 'src_025e9fb1391ea956': {
  'zh-Hans':('在判断结果是否完整之前，请浏览此对等方，以查找同一文件夹中的更多文件。','Peer here is the remote P2P user whose share is being browsed. The current 同级 means a person or thing at the same level, not a network peer; 对等方 matches this UI concept.','high'),
  'hi':('नतीजा पूरा है या नहीं, यह तय करने से पहले उसी फ़ोल्डर में और फ़ाइलें ढूँढ़ने के लिए इस पीयर को ब्राउज़ करें।','Peer here is the remote P2P user whose share is being browsed. सहकर्मी means coworker; पीयर matches the network term used elsewhere in this locale.','high'),
  'pt-BR':('Navegue por este par para encontrar mais arquivos na mesma pasta antes de decidir se o resultado está completo.','Peer here is the remote P2P user whose share is being browsed. The current ponto means point and changes the object of the browse action; par matches this locale’s established peer translation.','high'),
  'zh-Hant':('在判斷結果是否完整之前，請瀏覽此對等方，以尋找同一資料夾中的更多檔案。','Peer here is the remote P2P user whose share is being browsed. The current 同級 means a person or thing at the same level, not a network peer; 對等方 matches this UI concept.','high'),
  'vi':('Duyệt peer này để tìm thêm tệp trong cùng thư mục trước khi quyết định kết quả đã đầy đủ chưa.','Peer here is the remote P2P user whose share is being browsed. The current ngang hàng is an adverbial peer-to-peer phrase; borrowed peer matches the locale’s established wording for remote P2P users.','moderate'),
  'id':('Telusuri peer ini untuk mencari lebih banyak file di folder yang sama sebelum memutuskan apakah hasilnya sudah lengkap.','Peer here is the remote P2P user whose share is being browsed. Rekan suggests a colleague; peer matches the term used elsewhere for P2P users.','high'),
 },
 'src_0281c5055613ba4f': {
  'zh-Hans':('关注 Pod 广播','Pod is the application’s group/workspace concept, also used as Pod in this locale. 播客 means podcast, so the current target changes the object being followed.','high'),
  'ko':('포드 방송 팔로우','Pod is the application’s group/workspace concept, also rendered 포드 in this locale. 팟캐스트 means podcast, so the current target changes the object being followed.','high'),
  'zh-Hant':('關注 Pod 廣播','Pod is the application’s group/workspace concept, also used as Pod in this locale. 播客 means podcast, so the current target changes the object being followed.','high'),
 },
 'src_02c345586b79402d': {
  'ar':('البايتات حسب المصدر','This is a table header for byte counts grouped by source. The current singular بايت does not express the plural byte values shown in the table.','moderate'),
 },
 'src_02c7594d08c46d3d': {
  'zh-Hans':('Ntfy 访问令牌','Ntfy is an exact protected product/service name in the token field. Preserve its spelling and casing; the current target changes the casing.' ,'high'),
  'hi':('Ntfy एक्सेस टोकन','Ntfy is an exact protected product/service name in the token field. Preserve the Latin spelling; the current target transliterates the name.','high'),
  'zh-Hant':('Ntfy 存取令牌','Ntfy is an exact protected product/service name in the token field. Preserve its spelling and casing; the current target changes the casing.','high'),
  'id':('Token akses Ntfy','Ntfy is an exact protected product/service name in the token field. The current Indonesian text says the token is inaccessible and drops the product name.','high'),
 },
 'src_02d19b1532d820d5': {
  'fr':('Copier l’historique des exécutions d’automatisation','The button copies formatAutomationRunHistoryReport(runHistory). Révisions means revisions or versions; this control copies automation run history for review.','moderate'),
 },
 'src_02d2e2581dd8d687': {
  'hi':('लाइब्रेरी स्वास्थ्य स्कैन की स्थिति की जाँच नहीं हो सकी।','The source means status polling/querying, not conducting a survey. सर्वेक्षण is survey; the proposed wording says the scan status could not be checked.','high'),
  'fr':('Échec de la vérification de l’état de l’analyse de santé de la bibliothèque.','The error is about checking the scan status. The current French wording repeats état and makes the nested scan/library-health relationship hard to parse.','moderate'),
  'pt-BR':('Falha ao consultar o status da verificação do Library Health.','The source means querying/polling scan status. Pesquisar suggests searching; consultar states that the scan status could not be retrieved.','high'),
  'ko':('라이브러리 상태 스캔 진행 상황을 확인하지 못했습니다.','The error is about checking the Library Health scan status. The current 라이브러리 상태 검색 상태 repeats status and reads as a search for a library-status status.','high'),
 },
 'src_02e445ae370faf7c': {
  'fr':('Rechercher ce mix','This is an action button that queues searches for the mix cluster’s segment clues. The current Mélange de recherche is a noun phrase rather than the search action.','high'),
  'pt-BR':('Pesquisar o mix','This is an action button that queues searches for the mix cluster’s segment clues. The current Mistura de pesquisa is a noun phrase rather than the search action.','high'),
  'ja':('ミックスを検索','This is an action button that queues searches for the mix cluster’s segment clues. The current 検索ミックス reads as a compound/noun phrase rather than the action to search the mix.','moderate'),
  'ar':('ابحث عن المزيج','This is an action button that queues searches for the mix cluster’s segment clues. The current مزيج البحث is a noun phrase rather than an instruction to search the mix.','high'),
  'ko':('믹스 검색','This is an action button that queues searches for the mix cluster’s segment clues. The current 검색 믹스 makes search the modifier; this order names the action and its mix target.','moderate'),
  'id':('Cari Campuran','This is an action button that queues searches for the mix cluster’s segment clues. The current Campuran Pencarian is a noun phrase rather than the search action.','high'),
 },
}
uncertain_sources={
 'src_029c1853243a12a3':'The current source/caller evidence is incomplete: the frozen text combines “Policy report prepared for {length} shelf items” with “clipboard is unavailable,” but the current source caller only contains the first sentence, has no sourceCallsites in this row, and no sourceContexts. The full string and its locale targets cannot be judged against an exact current UI use until this source-context discrepancy is resolved.'
}
inputs=read_jsonl(ROOT/'review-input.jsonl')
manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
by_id={row['id']:row for row in inputs}
if len(by_id)!=len(inputs): raise SystemExit('duplicate review input IDs')
for sid, locales in fixes.items():
 if sid not in {row['sourceId'] for row in inputs}: raise SystemExit(f'fix source not selected: {sid}')
 for locale,(target,reason,confidence) in locales.items():
  if not any(row['sourceId']==sid and row['locale']==locale for row in inputs): raise SystemExit(f'fix locale absent: {sid}/{locale}')
if set(uncertain_sources)!={sid for sid in {row['sourceId'] for row in inputs} if sid in uncertain_sources}: raise SystemExit('uncertain source mismatch')

ledger=[]
plan=[]
for row in inputs:
 sid,locale,ident=row['sourceId'],row['locale'],row['id']
 current=row['target']
 current_hash=sha(current)
 if current_hash!=row['targetSha256']: raise SystemExit(f'input current hash mismatch: {ident}')
 if sid in uncertain_sources:
  verdict='uncertain'
  decision={'schemaVersion':1,'window':33,'id':ident,'locale':locale,'sourceId':sid,'sourceSha256':row['sourceSha256'],'currentTargetSha256':current_hash,'verdict':verdict,'reason':uncertain_sources[sid]}
 elif locale in fixes.get(sid,{}):
  target,reason,confidence=fixes[sid][locale]
  verdict='correct'
  target_hash=sha(target)
  placeholders=lambda s: sorted(re.findall(r'\{[^{}]+\}',s))
  if placeholders(row['source'])!=placeholders(current) or placeholders(row['source'])!=placeholders(target):
   raise SystemExit(f'candidate placeholder mismatch: {ident}')
  for literal in row.get('protectedLiterals',[]):
   if literal not in target:
    raise SystemExit(f'candidate protected literal mismatch: {ident}/{literal}')
  decision={'schemaVersion':1,'window':33,'id':ident,'locale':locale,'sourceId':sid,'sourceSha256':row['sourceSha256'],'currentTargetSha256':current_hash,'verdict':verdict,'candidateTargetSha256':target_hash,'reason':reason}
  plan.append({'schemaVersion':1,'window':33,'id':ident,'locale':locale,'sourceId':sid,'source':row['source'],'sourceSha256':row['sourceSha256'],'catalogKey':row['catalogKey'],'catalogPath':row['catalogPath'],'currentTarget':current,'currentTargetSha256':current_hash,'proposedTarget':target,'proposedTargetSha256':target_hash,'reason':reason,'confidence':confidence,'sourceCallsites':row.get('sourceCallsites',[]),'sourceContexts':row.get('sourceContexts',[]),'placeholders':row.get('placeholders',[]),'protectedLiterals':row.get('protectedLiterals',[]),'placeholderCheck':'source/current/proposed placeholder sequences match','protectedLiteralCheck':'all protected literals are present in the proposed target','currentCatalogFileSha256':manifest['currentCatalogFileSha256'][locale],'currentPrHead':manifest['headCommit'],'currentPrTree':manifest['tree'],'currentSourceSubtreeTree':manifest['sourceSubtreeTree'],'nativeSpeakerApproved':False})
 else:
  verdict='keep'
  decision={'schemaVersion':1,'window':33,'id':ident,'locale':locale,'sourceId':sid,'sourceSha256':row['sourceSha256'],'currentTargetSha256':current_hash,'verdict':verdict,'reason':'Meaning, locale grammar, caller context, placeholders, and protected literals are acceptable.'}
 ledger.append(decision)

if len(ledger)!=len(inputs) or len({row['id'] for row in ledger})!=len(inputs): raise SystemExit('decision ledger coverage mismatch')
for row in inputs:
 if row['sourceId'] in uncertain_sources: continue
 expected='correct' if row['locale'] in fixes.get(row['sourceId'],{}) else 'keep'
 got=next(d['verdict'] for d in ledger if d['id']==row['id'])
 if got!=expected: raise SystemExit(f'verdict mismatch {row["id"]}: {got}/{expected}')
write_jsonl(ROOT/'review-decisions.jsonl',ledger)
write_jsonl(ROOT/'crossreview-plan.jsonl',plan)
counts=collections.Counter(row['verdict'] for row in ledger)
by_locale={loc:dict(collections.Counter(d['verdict'] for d in ledger if d['locale']==loc)) for loc in LOCALES if any(d['locale']==loc for d in ledger)}
by_source={}
for d in ledger:
 entry=by_source.setdefault(d['sourceId'],{'verdicts':collections.Counter()})
 entry['verdicts'][d['verdict']]+=1
summary={'result':'MANUAL_REVIEW_COMPLETE_PENDING_ROOT_CROSS_REVIEW','window':33,'reviewBaseHead':manifest['headCommit'],'reviewBaseTree':manifest['tree'],'sourceSubtreePath':manifest['sourceSubtreePath'],'sourceSubtreeTree':manifest['sourceSubtreeTree'],'sourceKeys':len({row['sourceId'] for row in inputs}),'cells':len(inputs),'verdicts':dict(sorted(counts.items())),'correctionRows':len(plan),'correctionSourceKeys':len({row['sourceId'] for row in plan}),'uncertainSourceKeys':len(uncertain_sources),'uncertainRows':sum(1 for d in ledger if d['verdict']=='uncertain'),'perLocale':by_locale,'reviewInputSha256':sha((ROOT/'review-input.jsonl').read_bytes()),'decisionLedgerSha256':sha((ROOT/'review-decisions.jsonl').read_bytes()),'candidatePlanSha256':sha((ROOT/'crossreview-plan.jsonl').read_bytes()),'sourceCallerLinesPinned':manifest['sourceCallerLinesPreflighted'],'semanticDecisionConfidence':'high for context-bound semantic, literal, and technical errors; locale-quality confidence moderate; native-speaker review outstanding','reviewerMethod':'manual semantic review of every selected locale cell against pinned source/callsite context, placeholders, protected literals, and product terminology; no translation model/API call','independentCrossReview':'pending','rootCrossReview':'pending','targetsApplied':False,'catalogsEdited':False,'uncertainReasons':uncertain_sources}
(ROOT/'review-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest.update({'reviewDecisionLedger':{'path':'review-decisions.jsonl','rows':len(ledger),'sha256':sha((ROOT/'review-decisions.jsonl').read_bytes())},'candidatePlan':{'path':'crossreview-plan.jsonl','rows':len(plan),'sha256':sha((ROOT/'crossreview-plan.jsonl').read_bytes())},'manualReviewSummary':{'path':'review-summary.json','sha256':sha((ROOT/'review-summary.json').read_bytes())},'reviewDecisions':dict(sorted(counts.items())),'independentCrossReview':'pending','rootCrossReview':'pending','targetsApplied':False,'catalogsEdited':False})
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report={'result':'PASS','window':33,'inputRows':len(inputs),'decisionRows':len(ledger),'candidateRows':len(plan),'decisionCounts':dict(sorted(counts.items())),'perLocale':by_locale,'reviewInputSha256':sha((ROOT/'review-input.jsonl').read_bytes()),'decisionLedgerSha256':sha((ROOT/'review-decisions.jsonl').read_bytes()),'candidatePlanSha256':sha((ROOT/'crossreview-plan.jsonl').read_bytes()),'manifestSha256':sha((ROOT/'manifest.json').read_bytes()),'sourceCallsiteRowsWithoutPinnedCallers':sum(not row.get('sourceCallsites') for row in inputs),'uncertainSourceIds':sorted(uncertain_sources)}
(ROOT/'verification-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name in ['review-input.jsonl','review-decisions.jsonl','crossreview-plan.jsonl','manifest.json','preflight.json','review-summary.json','verification-report.json','freeze_window33.py','build_packets_window33.py','verify_window33.py','README.md']:
 if not (ROOT/name).is_file(): raise SystemExit(f'missing artifact {name}')
(ROOT/'SHA256SUMS.txt').write_text(''.join(f'{sha((ROOT/name).read_bytes())}  {name}\n' for name in ['review-input.jsonl','review-decisions.jsonl','crossreview-plan.jsonl','manifest.json','preflight.json','review-summary.json','verification-report.json','freeze_window33.py','build_packets_window33.py','verify_window33.py','README.md']),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
