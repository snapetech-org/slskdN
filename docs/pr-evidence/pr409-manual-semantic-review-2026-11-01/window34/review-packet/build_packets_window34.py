#!/usr/bin/env python3
"""Build the W34 per-cell semantic decision and cross-review packet in task scratch."""
import collections, hashlib, json, re
from pathlib import Path

ROOT=Path('/mnt/disks/scratch/task-scratch/slskdn-manual-review-window34-dc8ed240-20261102')
LOCALES=['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']

def sha(value):
    return hashlib.sha256(value if isinstance(value,bytes) else value.encode('utf-8')).hexdigest()

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def write_jsonl(path, rows):
    path.write_text(''.join(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for row in rows),encoding='utf-8')

# Only clear source/context-bound semantic or protected-literal defects are proposed.
fixes={
 'src_02f5f7929175e1c0': {
  'de':('Meinungen abrufen','This button loads existing opinions for review, as its tooltip states. The current wording can read as soliciting or gathering opinions rather than retrieving them.','high'),
  'ja':('意見を読み込む','This button loads existing opinions for review, as its tooltip states. 聞く means asking/listening for opinions rather than loading the existing records.','high'),
 },
 'src_031a8f0f659df890': {
  'fr':('Échec','This source is reused as a standalone status in several unrelated status lists and as a failed-result fallback. The current plural adjective Échoués has no consistently matching subject; the neutral status noun avoids that number mismatch.','moderate'),
  'pt-BR':('Falha','This source is reused as a standalone status in several unrelated status lists and as a failed-result fallback. Falharam says “they failed”; the neutral status noun Falha fits the standalone failure state.','moderate'),
 },
 'src_03513e10082916f0': {
  'zh-Hans':('目标对等方：','This is a count of target Soulseek network peers. 同行 refers to colleagues or people in the same profession; 对等方 is the established P2P term in this locale.','high'),
  'hi':('लक्ष्य पीयर:','This is a count of target Soulseek network peers. सहकर्मी means colleagues/coworkers; पीयर preserves the P2P network meaning used elsewhere in this locale.','high'),
  'de':('Ziel-Peers:','This is a count of target Soulseek network peers. Zielkollegen means target coworkers, while Peers is the established network term.','high'),
  'ko':('대상 피어:','This is a count of target Soulseek network peers. 동료 means colleagues; 피어 is the technical P2P term.','high'),
  'zh-Hant':('目標對等方：','This is a count of target Soulseek network peers. 同行 refers to colleagues or people in the same profession; 對等方 is the established P2P term in this locale.','high'),
  'vi':('Peer mục tiêu:','This is a count of target Soulseek network peers. Đối tượng ngang hàng reads as an object/subject or a peer-to-peer relation, not the remote network participant; peer preserves the P2P meaning.','moderate'),
  'id':('Peer sasaran:','This is a count of target Soulseek network peers. Rekan means a colleague/associate; peer preserves the P2P network meaning used elsewhere in this locale.','high'),
 },
 'src_03867aea70acaf4c': {
  'ar':('أدلة','This appears as an evidence lane/label and a Quarantine Jury evidence column. شهادة means testimony or a certificate; أدلة names supporting evidence/data.','high'),
 },
 'src_03c73a8121cec12f': {
  'ja':('スロット、速度上限、自動置換、スケジュールの有効化。','The current Japanese value contains two zero-width space characters inside 速度上限. Removing those invisible characters leaves the intended speed-limit term intact.','high'),
 },
 'src_03d02cb9535b25b0': {
  'zh-Hans':('对等方不可用','This is a remote P2P transfer error. 对等方 is the established network-peer term; 对等点 reads as a peer “point” and is inconsistent with the terminology used elsewhere.','high'),
  'hi':('पीयर उपलब्ध नहीं है','This is a remote P2P transfer error. सहकर्मी means colleague/coworker; पीयर preserves the network-peer meaning used elsewhere in this locale.','high'),
  'zh-Hant':('對等方不可用','This is a remote P2P transfer error. 對等方 is the established network-peer term; 對等點 reads as a peer “point” and is inconsistent with the terminology used elsewhere.','high'),
  'vi':('Peer không khả dụng','This is a remote P2P transfer error. Ngang hàng describes a peer-to-peer relation, not the unavailable remote network participant; peer preserves the P2P meaning.','moderate'),
  'id':('Peer tidak tersedia','This is a remote P2P transfer error. Rekan means a colleague/associate; peer preserves the P2P network meaning used elsewhere in this locale.','high'),
 },
 'src_0404be0f930be704': {
  'hi':('मेटाडेटा निर्यात, आयात और संघर्ष समाधान के मेट्रिक्स लोड करें।','The tooltip refers to resolving metadata conflicts. विरोध means opposition, not conflicting metadata values; संघर्ष समाधान expresses conflict resolution.','high'),
 },
 'src_046a093f5e41b87e': {
  'hi':('डुप्लिकेट मिले:','This is a plural count label followed by the number of duplicate hashes. The current wording says a single duplicate was detected; this form identifies the plural duplicates counted.','moderate'),
 },
 'src_046ca04041737cfb': {
  'ko':('무작위로 가져온 네이티브 프리셋','The caller identifies an imported native preset from the browser-local preset library. 기본 means default, which changes native to default; 네이티브 preserves the source distinction.','moderate'),
 },
 'src_04875bce2d1363bd': {
  'zh-Hans':('覆盖网络对等方：{count}','This tooltip reports the count of peers in the overlay network. 节点对等端 is redundant/unclear; 对等方 is the established P2P peer term. The {count} placeholder is preserved.','high'),
  'zh-Hant':('覆蓋網路對等方：{count}','This tooltip reports the count of peers in the overlay network. 點對點裝置 means a P2P device rather than a peer; 對等方 is the established P2P peer term. The {count} placeholder is preserved.','high'),
 },
 'src_048fc12579e7f9cd': {
  'hi':('एआई ह्यूरिस्टिक्स','This is a scorecard category counting AI heuristic clips. अनुमान means an estimate/inference and does not identify the heuristic category; the technical term is retained in transliteration.','moderate'),
  'ar':('الأساليب الاستدلالية للذكاء الاصطناعي','This is a scorecard category for AI heuristic clips. The current phrase reads as reasoning about AI; this names heuristic methods used by AI.','moderate'),
  'vi':('Phương pháp heuristic AI','This is a scorecard category counting AI heuristic clips. Chẩn đoán AI means AI diagnosis, which names a different category; this retains the technical heuristic term.','moderate'),
 },
 'src_04d1e2c8561db224': {
  'hi':('PodCore की उपलब्धता की जाँच की जा रही है...','PodCore is an exact protected product name. The current target transliterates it; preserve the exact Latin spelling.','high'),
 },
 'src_04e24b989d400c03': {
  'zh-Hans':('听歌记录与评分导出','The media-server action exports confirmed local plays or ratings. 拼字游戏 means the Scrabble word game, not scrobbling/listening history; the replacement names the listening record and rating export.','high'),
  'zh-Hant':('聆聽紀錄與評分匯出','The media-server action exports confirmed local plays or ratings. 拼字遊戲 means the Scrabble word game, not scrobbling/listening history; the replacement names the listening record and rating export.','high'),
  'ar':('تصدير سجل الاستماع والتقييمات','The media-server action exports confirmed local plays or ratings. التمرير means scrolling and التصنيف can mean classification/ranking; the replacement identifies listening-history and rating export.','high'),
  'pt-BR':('Scrobble e exportação de avaliações','The media-server action exports confirmed local plays or ratings. Avaliações identifies user ratings more clearly than classificação, which can read as classification or ranking.','moderate'),
  'vi':('Scrobble và xuất đánh giá','The media-server action exports confirmed local plays or ratings. Xuất khẩu is usually commercial export and xếp hạng means ranking; this names scrobble and data-rating export.','moderate'),
  'id':('Ekspor scrobble dan rating','The media-server action exports confirmed local plays or ratings. The current word order peringkat ekspor reads as ranking export; this names the scrobble and rating data being exported.','moderate'),
 },
}

uncertain={
 'fr:src_03c73a8121cec12f': 'The card describes transfer policy, where “slots” likely means transfer/concurrency slots, not locations or scheduled time slots. The current Emplacements can suggest physical locations, while créneaux can suggest schedule periods. Hold this French term for terminology review rather than guessing a replacement.',
}

inputs=read_jsonl(ROOT/'review-input.jsonl')
manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
by_id={row['id']:row for row in inputs}
if len(by_id)!=len(inputs): raise SystemExit('duplicate review input IDs')
selected={row['sourceId'] for row in inputs}
for sid,locales in fixes.items():
    if sid not in selected: raise SystemExit(f'correction source not selected: {sid}')
    for locale,(target,reason,confidence) in locales.items():
        matches=[row for row in inputs if row['sourceId']==sid and row['locale']==locale]
        if len(matches)!=1: raise SystemExit(f'correction cell absent/duplicate: {sid}/{locale}')
for ident in uncertain:
    if ident not in by_id: raise SystemExit(f'uncertain cell absent: {ident}')

decisions=[]; plan=[]; uncertain_rows=[]
for row in inputs:
    sid,locale,ident=row['sourceId'],row['locale'],row['id']
    current=row['target']; current_hash=sha(current)
    if current_hash!=row['targetSha256']: raise SystemExit(f'input target hash mismatch: {ident}')
    if ident in uncertain:
        reason=uncertain[ident]
        decisions.append({'schemaVersion':1,'window':34,'id':ident,'locale':locale,'sourceId':sid,'sourceSha256':row['sourceSha256'],'currentTargetSha256':current_hash,'verdict':'uncertain','reason':reason})
        uncertain_rows.append({'schemaVersion':1,'window':34,'id':ident,'locale':locale,'sourceId':sid,'source':row['source'],'sourceSha256':row['sourceSha256'],'catalogKey':row['catalogKey'],'catalogPath':row['catalogPath'],'currentTarget':current,'currentTargetSha256':current_hash,'reason':reason,'sourceCallsites':row.get('sourceCallsites',[]),'sourceContexts':row.get('sourceContexts',[]),'placeholders':row.get('placeholders',[]),'protectedLiterals':row.get('protectedLiterals',[]),'currentCatalogFileSha256':manifest['currentCatalogFileSha256'][locale],'currentPrHead':manifest['headCommit'],'currentPrTree':manifest['tree'],'currentSourceSubtreeTree':manifest['sourceSubtreeTree'],'nativeSpeakerApproved':False})
    elif locale in fixes.get(sid,{}):
        target,reason,confidence=fixes[sid][locale]
        target_hash=sha(target)
        placeholders=lambda value: sorted(re.findall(r'\{[^{}]+\}',value))
        if placeholders(row['source'])!=placeholders(current) or placeholders(row['source'])!=placeholders(target):
            raise SystemExit(f'placeholder mismatch: {ident}')
        for literal in row.get('protectedLiterals',[]):
            if literal not in target: raise SystemExit(f'protected literal missing: {ident}/{literal}')
        decisions.append({'schemaVersion':1,'window':34,'id':ident,'locale':locale,'sourceId':sid,'sourceSha256':row['sourceSha256'],'currentTargetSha256':current_hash,'verdict':'correct','candidateTargetSha256':target_hash,'reason':reason})
        plan.append({'schemaVersion':1,'window':34,'id':ident,'locale':locale,'sourceId':sid,'source':row['source'],'sourceSha256':row['sourceSha256'],'catalogKey':row['catalogKey'],'catalogPath':row['catalogPath'],'currentTarget':current,'currentTargetSha256':current_hash,'proposedTarget':target,'proposedTargetSha256':target_hash,'reason':reason,'confidence':confidence,'sourceCallsites':row.get('sourceCallsites',[]),'sourceContexts':row.get('sourceContexts',[]),'placeholders':row.get('placeholders',[]),'protectedLiterals':row.get('protectedLiterals',[]),'placeholderCheck':'source/current/proposed placeholder sequences match','protectedLiteralCheck':'all protected literals are present in the proposed target','currentCatalogFileSha256':manifest['currentCatalogFileSha256'][locale],'currentPrHead':manifest['headCommit'],'currentPrTree':manifest['tree'],'currentSourceSubtreeTree':manifest['sourceSubtreeTree'],'nativeSpeakerApproved':False})
    else:
        decisions.append({'schemaVersion':1,'window':34,'id':ident,'locale':locale,'sourceId':sid,'sourceSha256':row['sourceSha256'],'currentTargetSha256':current_hash,'verdict':'keep','reason':'Meaning, locale usage, pinned caller context, placeholders, and protected literals are acceptable for this review; native-speaker review remains outstanding.'})

if len(decisions)!=len(inputs) or len({d['id'] for d in decisions})!=len(inputs): raise SystemExit('decision coverage mismatch')
write_jsonl(ROOT/'review-decisions.jsonl',decisions)
write_jsonl(ROOT/'crossreview-plan.jsonl',plan)
write_jsonl(ROOT/'uncertain-ledger.jsonl',uncertain_rows)
counts=collections.Counter(d['verdict'] for d in decisions)
per_locale={loc:dict(collections.Counter(d['verdict'] for d in decisions if d['locale']==loc)) for loc in LOCALES if any(d['locale']==loc for d in decisions)}
by_source={}
for d in decisions:
    group=by_source.setdefault(d['sourceId'],collections.Counter()); group[d['verdict']]+=1
summary={'result':'MANUAL_REVIEW_COMPLETE_PENDING_ROOT_CROSS_REVIEW','window':34,'reviewBaseHead':manifest['headCommit'],'reviewBaseTree':manifest['tree'],'sourceSubtreePath':manifest['sourceSubtreePath'],'sourceSubtreeTree':manifest['sourceSubtreeTree'],'sourceKeys':len(selected),'cells':len(inputs),'verdicts':dict(sorted(counts.items())),'correctionRows':len(plan),'correctionSourceKeys':len({p['sourceId'] for p in plan}),'uncertainRows':len(uncertain_rows),'uncertainCellIds':[r['id'] for r in uncertain_rows],'perLocale':per_locale,'perSourceKey':{sid:dict(sorted(c.items())) for sid,c in sorted(by_source.items())},'reviewInputSha256':sha((ROOT/'review-input.jsonl').read_bytes()),'decisionLedgerSha256':sha((ROOT/'review-decisions.jsonl').read_bytes()),'candidatePlanSha256':sha((ROOT/'crossreview-plan.jsonl').read_bytes()),'uncertainLedgerSha256':sha((ROOT/'uncertain-ledger.jsonl').read_bytes()),'sourceCallerLinesPinned':manifest['sourceCallerLinesPreflighted'],'semanticDecisionConfidence':'high for direct meaning, protected literal, and network terminology mismatches; moderate for locale phrasing and borrowed technical terms; native-speaker review outstanding','reviewerMethod':'manual review of every selected locale cell against the frozen English source, exact caller context, locale usage, placeholders, protected literals, and pinned product context; no translation API/model calls','independentCrossReview':'not requested for this packet','rootCrossReview':'pending','nativeSpeakerReview':'outstanding','targetsApplied':False,'catalogsEdited':False}
(ROOT/'review-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
freeze_summary={'result':'MANUAL_REVIEW_COMPLETE_PENDING_ROOT_CROSS_REVIEW','window':34,'reviewBaseHead':manifest['headCommit'],'reviewBaseTree':manifest['tree'],'sourceSubtreePath':manifest['sourceSubtreePath'],'sourceSubtreeTree':manifest['sourceSubtreeTree'],'sourceKeys':len(selected),'cells':len(inputs),'perLocaleCells':dict(sorted(collections.Counter(r['locale'] for r in inputs).items())),'verdicts':dict(sorted(counts.items())),'candidateRows':len(plan),'heldRows':len(uncertain_rows),'rootCrossReview':'pending','nativeSpeakerReview':'outstanding'}
(ROOT/'freeze-summary.json').write_text(json.dumps(freeze_summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest.update({'reviewDecisionLedger':{'path':'review-decisions.jsonl','rows':len(decisions),'sha256':sha((ROOT/'review-decisions.jsonl').read_bytes())},'candidatePlan':{'path':'crossreview-plan.jsonl','rows':len(plan),'sha256':sha((ROOT/'crossreview-plan.jsonl').read_bytes())},'uncertainLedger':{'path':'uncertain-ledger.jsonl','rows':len(uncertain_rows),'sha256':sha((ROOT/'uncertain-ledger.jsonl').read_bytes())},'manualReviewSummary':{'path':'review-summary.json','sha256':sha((ROOT/'review-summary.json').read_bytes())},'reviewDecisions':dict(sorted(counts.items())),'rootCrossReview':'pending','nativeSpeakerReview':'outstanding','targetsApplied':False,'catalogsEdited':False})
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report={'result':'PACKET_BUILT_PENDING_READ_ONLY_VALIDATION','window':34,'inputRows':len(inputs),'sourceKeys':len(selected),'candidateRows':len(plan),'uncertainRows':len(uncertain_rows),'decisionCounts':dict(sorted(counts.items())),'perLocale':per_locale,'reviewInputSha256':sha((ROOT/'review-input.jsonl').read_bytes()),'decisionLedgerSha256':sha((ROOT/'review-decisions.jsonl').read_bytes()),'candidatePlanSha256':sha((ROOT/'crossreview-plan.jsonl').read_bytes()),'uncertainLedgerSha256':sha((ROOT/'uncertain-ledger.jsonl').read_bytes()),'currentPrHead':manifest['headCommit'],'currentPrTree':manifest['tree'],'currentSourceSubtreeTree':manifest['sourceSubtreeTree'],'sourceCallerLinePins':manifest['sourceCallerLinesPreflighted'],'nativeSpeakerReview':'outstanding','catalogsEdited':False}
(ROOT/'review-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'verification-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
