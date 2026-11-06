#!/usr/bin/env python3
import collections, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LOCALES=['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
def sha(v): return hashlib.sha256(v if isinstance(v,bytes) else v.encode('utf-8')).hexdigest()
def read_jsonl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def write_jsonl(p,rows): p.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
fixes={
 'src_0134493aa130b5ee': {'vi':'Truy vấn các bộ mô tả nội dung theo miền và loại tùy chọn'},
 'src_0143a3db005e1e7f': {
  'zh-Hans':'例如，mb:recording:12345-6789-...',
  'hi':'उदाहरण के लिए, mb:recording:12345-6789-...',
  'fr':'par exemple, mb:recording:12345-6789-...',
  'pt-BR':'por exemplo, mb:recording:12345-6789-...',
  'ar':'على سبيل المثال، mb:recording:12345-6789-...',
  'ko':'예: mb:recording:12345-6789-...',
  'zh-Hant':'例如，mb:recording:12345-6789-...',
 },
 'src_014659ab9d98c8fe': {
  'ja':'競合',
  'ar':'تعارض',
  'ko':'충돌',
 },
 'src_015aa2cc0b508343': {
  'ar':'الحد الأقصى لعدد مرات إعادة المحاولة',
  'id':'Jumlah Percobaan Ulang Maksimum',
 },
 'src_01736849b86961f6': {
  'ja':'シーケンス ID',
  'ko':'시퀀스 ID',
 },
 'src_018a1dce4e1fb967': {
  'ar':'إدارة الواصفات المنشورة ومراقبة حالة النشر',
  'vi':'Quản lý các bộ mô tả đã xuất bản và theo dõi trạng thái xuất bản',
 },
 'src_018fa086df9f8bf1': {
  'zh-Hans':'回填同步完成：已收到 {totalMessagesReceived} 条消息',
  'de':'Backfill-Synchronisierung abgeschlossen: {totalMessagesReceived} Nachrichten empfangen',
  'fr':'Synchronisation de remplissage terminée : {totalMessagesReceived} messages reçus',
  'pt-BR':'Sincronização de preenchimento concluída: {totalMessagesReceived} mensagens recebidas',
  'ar':'اكتملت مزامنة إعادة التعبئة: تم استلام {totalMessagesReceived} رسالة',
  'ko':'백필 동기화 완료: {totalMessagesReceived}개의 메시지 수신',
  'zh-Hant':'回填同步完成：已收到 {totalMessagesReceived} 則訊息',
  'vi':'Đồng bộ hóa chèn lấp đã hoàn tất: Đã nhận được {totalMessagesReceived} tin nhắn',
  'id':'Sinkronisasi pengisian ulang selesai: {totalMessagesReceived} pesan diterima',
 },
 'src_01c4d3c21642b217': {'ar':'SSH'},
 'src_01cd1662ba5c61e7': {'de':'Vorschau der Synchronisierung'},
 'src_01d460734d22d23c': {'ko':'자동화가 표시됨'},
}
reasons={
 'src_0134493aa130b5ee':'The UI describes querying descriptors by domain and optional type. The current Vietnamese wording parses as describing query content; the correction makes descriptors the object of the query and preserves the domain/type filters.',
 'src_0143a3db005e1e7f':'This is an External ID input example. The `mb:recording` prefix is a MusicBrainz identifier namespace used by this form and fixtures; translating it or changing its ASCII separators obscures the literal value users must enter. The correction translates only the introductory phrase.',
 'src_014659ab9d98c8fe':'The caller is a table of subject-index data conflicts. The current terms suggest interpersonal struggle/opposition rather than a data conflict/collision; the replacements use the technical conflict sense.',
 'src_015aa2cc0b508343':'This is a numeric maximum-retries policy label. The Arabic target transliterates “Max” and the Indonesian target abbreviates “Maks”; the replacements state the maximum retry count directly.',
 'src_01736849b86961f6':'The caller renders `peer.lastSeqId` in a mesh synchronization table. The current Japanese term can mean array ID and the Korean term means rank/ordinal number; these replacements identify a sequence ID.',
 'src_018a1dce4e1fb967':'MediaCore uses “descriptor” as the technical record type that is published and retrieved from the DHT. The current Arabic and Vietnamese wording says “description”; the replacements preserve the descriptor concept.',
 'src_018fa086df9f8bf1':'This is a success toast reporting a count of messages received. The current targets place the variable as though it were an item number, omit required count constructions, or attach an incorrect German hyphen. The revisions express the quantity with locale-appropriate word order while preserving the named placeholder.',
 'src_01c4d3c21642b217':'SSH is the exact protocol option shown in the selector. The current Arabic transliteration drops the repeated S and H sounds; retaining the standard protocol acronym is unambiguous.',
 'src_01cd1662ba5c61e7':'The source is a noun heading for a rendered preview of synchronization output. The current German wording is an imperative verb (“synchronize preview”); the replacement is a preview of the synchronization.',
 'src_01d460734d22d23c':'This is a setup-health-check result state meaning automation recipes are present and visible. The current Korean phrase reads like “automation display”; the correction expresses that automation is displayed/visible.',
}
inputs=read_jsonl(ROOT/'review-input.jsonl')
manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
by_id={r['id']:r for r in inputs}
if len(by_id)!=len(inputs): raise SystemExit('duplicate input IDs')
allowed={r['sourceId']:set() for r in inputs}
for r in inputs: allowed[r['sourceId']].add(r['locale'])
for sid, locs in fixes.items():
 if sid not in allowed: raise SystemExit(f'fix source not selected: {sid}')
 for loc, target in locs.items():
  if not any(r['sourceId']==sid and r['locale']==loc for r in inputs): raise SystemExit(f'fix locale absent: {sid}/{loc}')
  row=next(r for r in inputs if r['sourceId']==sid and r['locale']==loc)
  if target==row['target'] or not target.strip(): raise SystemExit(f'unchanged/empty fix: {row["id"]}')
  import re
  ph=lambda s: collections.Counter(re.findall(r'\{[^{}]+\}',s))
  if ph(target)!=ph(row['source']): raise SystemExit(f'placeholder mismatch: {row["id"]}')
  for lit in row.get('protectedLiterals',[]):
   if target.count(lit)!=row['source'].count(lit): raise SystemExit(f'protected literal mismatch: {row["id"]} {lit}')
  if sid=='src_0143a3db005e1e7f' and 'mb:recording:12345-6789-...' not in target: raise SystemExit(f'identifier prefix not preserved: {row["id"]}')
corrections={}; decisions=[]; per_locale=collections.defaultdict(collections.Counter)
for row in inputs:
 sid,loc,ident=row['sourceId'],row['locale'],row['id']; target=fixes.get(sid,{}).get(loc)
 if target is None:
  decisions.append({'id':ident,'verdict':'keep'}); per_locale[loc]['keep']+=1; continue
 decisions.append({'id':ident,'verdict':'correct','target':target,'confidence':'high','reason':reasons[sid]}); per_locale[loc]['correct']+=1
 corrections[ident]={'schemaVersion':1,'id':ident,'sourceId':sid,'locale':loc,'catalogPath':row['catalogPath'],'catalogKey':row['catalogKey'],'source':row['source'],'sourceSha256':row['sourceSha256'],'currentTarget':row['target'],'currentTargetSha256':row['targetSha256'],'proposedTarget':target,'proposedTargetSha256':sha(target),'confidence':'high','reason':reasons[sid],'currentPrHead':manifest['headCommit'],'currentPrTree':manifest['tree'],'currentSourceSubtreeTree':manifest['sourceSubtreeTree'],'currentCatalogFileSha256':manifest['currentCatalogFileSha256'][loc],'sourceCallsites':row.get('sourceCallsites',[])}
if len(decisions)!=266: raise SystemExit(f'decision count mismatch: {len(decisions)}')
ordered=sorted(corrections.values(),key=lambda r:(LOCALES.index(r['locale']),r['sourceId']))
write_jsonl(ROOT/'review-decisions.jsonl',decisions)
write_jsonl(ROOT/'crossreview-plan.jsonl',ordered)
count=collections.Counter(d['verdict'] for d in decisions)
summary={'window':32,'sourceKeys':len({r['sourceId'] for r in inputs}),'cells':len(inputs),'verdicts':dict(sorted(count.items())),'correctionRows':len(ordered),'correctionSourceKeys':len({r['sourceId'] for r in ordered}),'perLocale':{loc:{v:per_locale[loc][v] for v in ('keep','correct','uncertain')} for loc in LOCALES if per_locale[loc]},'inputSha256':sha((ROOT/'review-input.jsonl').read_bytes()),'decisionsSha256':sha((ROOT/'review-decisions.jsonl').read_bytes()),'candidatePlanSha256':sha((ROOT/'crossreview-plan.jsonl').read_bytes()),'reviewedCorrectionSourceIds':sorted({r['sourceId'] for r in ordered}),'semanticDecisionConfidence':'high for the identified meaning, identifier, and grammar errors; locale-quality confidence moderate; native-speaker review outstanding','reviewerMethod':'manual semantic review of all 266 pending cells against exact source callers and UI context; exact-hash and placeholder checks; no translation-model/API call','independentCrossReview':'pending','targetsApplied':False,'catalogsEdited':False,'uncertainCells':0,'nativeSpeakerReview':'not performed; remains required'}
(ROOT/'review-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest.update({'decisionCounts':dict(count),'perLocaleDecisionCounts':summary['perLocale'],'reviewDecisions':{'path':'review-decisions.jsonl','rows':len(decisions),'sha256':summary['decisionsSha256']},'crossReviewPlan':{'path':'crossreview-plan.jsonl','rows':len(ordered),'sha256':summary['candidatePlanSha256'],'status':'pending independent exact-hash cross-review'},'reviewerMethod':summary['reviewerMethod'],'semanticDecisionConfidence':summary['semanticDecisionConfidence'],'targetsApplied':False,'catalogsEdited':False,'sourceEdited':False,'formalLedgerEdited':False,'prBodyEdited':False,'modelCalls':0,'apiCalls':0})
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
README='''# slskdN populated catalog semantic review: W32\n\nThis 25-source window was frozen against open draft PR #409 at head `dfb9707f946bf2686210bcf1072b9d70c8442a62`, tree `9458e836ae12c02573535b5c9dc052f055b7820d`, source subtree `469e060d9e0a3fd6f54bc75a69993ee2651d3e4b`. It contains 266 pending locale cells because exact reusable/formal dispositions already cover some locales.\n\nThe review manually checked each current target against the English source, source callsites/UI context, placeholders, and technical literals. It found the per-cell dispositions in `review-decisions.jsonl`; the 29 exact-hash correction candidates are in `crossreview-plan.jsonl`. All other cells are kept unchanged. The plan has not been independently cross-reviewed or applied.\n\nThe W32 input, prior-window/correction reconciliation, all locale catalog hashes, caller blob/line pins, source/target hashes, placeholder checks, and the current PR head/tree are recorded in `manifest.json` and `preflight.json`. Native-speaker review was not performed and remains required. No repository files/catalog values were changed, and no tests, builds, scans, or CI jobs were run.\n'''
(ROOT/'README.md').write_text(README,encoding='utf-8')
(ROOT/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.name}\n' for p in sorted(ROOT.glob('*')) if p.is_file() and p.name!='SHA256SUMS.txt'),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
