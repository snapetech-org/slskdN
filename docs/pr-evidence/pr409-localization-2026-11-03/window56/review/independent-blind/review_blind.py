#!/usr/bin/env python3
"""Blind semantic review of the candidate-free W56 input for slskdN PR #409."""
import hashlib, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parent
INPUT=ROOT/'input'
HEAD='32afa31caca42b17ac89c9ee91e54ed94cad0411'
TREE='0111bd0c279534b972fcbc5f36dd7a32baf86909'
REPO='snapetech-org/slskdN'
PR=409
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PH=re.compile(r'\{[^{}]+\}')
TAG=re.compile(r'</?[A-Za-z][^>]*>')
RANK302={
 'ar':('correction','أنواع المهام','The pinned caller renders this as a statistic label in System > Jobs, where the value is the number of keys in analytics.byType. The source means categories of system background jobs, not employment roles; المهام makes that task/job-type sense clear.'),
 'de':('accept-current',None,'Jobtypen is a clear technical rendering for categories in the System > Jobs statistic; the caller and count disambiguate it from employment.'),
 'es':('refinement','Tipos de tareas','The pinned caller counts entries in analytics.byType on the System > Jobs page. This is about system task categories; tareas avoids a possible reading as kinds of employment.'),
 'fr':('correction','Types de tâches','The pinned caller counts entries in analytics.byType on the System > Jobs page. The current emplois suggests employment categories; tâches names system task categories.'),
 'hi':('correction','कार्य के प्रकार','The pinned caller counts entries in analytics.byType on the System > Jobs page. The current नौकरी suggests employment; कार्य identifies types of system work/tasks.'),
 'id':('refinement','Jenis tugas','The pinned caller counts entries in analytics.byType on the System > Jobs page. This label refers to system task categories; tugas avoids a possible employment reading of pekerjaan.'),
 'ja':('correction','ジョブの種類','The pinned caller counts entries in analytics.byType on the System > Jobs page. 職種 usually refers to occupations; ジョブの種類 names technical system job categories.'),
 'ko':('correction','작업 유형','The pinned caller counts entries in analytics.byType on the System > Jobs page. 직업 유형 reads as occupational types; 작업 유형 names system job/task categories.'),
 'pt-BR':('refinement','Tipos de tarefas','The pinned caller counts entries in analytics.byType on the System > Jobs page. This is about system task categories; tarefas avoids a possible reading as types of employment/work.'),
 'vi':('refinement','Loại tác vụ','The pinned caller counts entries in analytics.byType on the System > Jobs page. This is about system task categories; tác vụ makes that technical meaning explicit.'),
 'zh-Hans':('correction','任务类型','The pinned caller counts entries in analytics.byType on the System > Jobs page. 职位类型 suggests employment positions; 任务类型 names system task categories.'),
 'zh-Hant':('correction','任務類型','The pinned caller counts entries in analytics.byType on the System > Jobs page. 職位類型 suggests employment positions; 任務類型 names system task categories.'),
}

def sha(b): return hashlib.sha256(b if isinstance(b,bytes) else b.encode('utf-8')).hexdigest()
def jread(p): return json.loads(p.read_text(encoding='utf-8'))
def lines(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x]
def write_json(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def write_jsonl(p,rs): p.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rs),encoding='utf-8')
def tokens(s,rx):
 d={}
 for x in rx.findall(s): d[x]=d.get(x,0)+1
 return d

# Verify packet inputs, candidate-free declaration, live attestation, and all 24 cells.
for line in (INPUT/'PACKET-SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
 digest,rel=line.split(maxsplit=1); f=INPUT/rel.strip()
 if not f.is_file() or sha(f.read_bytes())!=digest: raise SystemExit(f'input checksum mismatch: {rel}')
manifest=jread(INPUT/'manifest.json')
att=jread(INPUT/'head-tree-attestation.json')
live=jread(ROOT/'live-pr-verification.json')
if manifest.get('candidateFree') is not True: raise SystemExit('input is not candidate-free')
for obj in [manifest,att]:
 if obj.get('repository')!=REPO or obj.get('pullRequest')!=PR or obj.get('head')!=HEAD or obj.get('tree')!=TREE: raise SystemExit('head/tree input pin mismatch')
if live.get('state')!='OPEN' or live.get('isDraft') is not True or live.get('head')!=HEAD or live.get('tree')!=TREE or live.get('remoteBranchHead')!=HEAD: raise SystemExit('live PR/remote pin mismatch')
if manifest.get('cellCount')!=24 or manifest.get('sourceCount')!=2 or manifest.get('locales')!=LOCALES: raise SystemExit('window manifest mismatch')

cells=lines(INPUT/'source-current-cells.jsonl')
contexts=lines(INPUT/'caller-contexts.jsonl')
structure=lines(INPUT/'catalog-structure.jsonl')
selection=jread(INPUT/'selection-and-boundary.json')
if selection.get('candidateFree') is not True or selection.get('containsTranslationsBeyondCurrentValues') is not False: raise SystemExit('selection attestation is not candidate-free')
if len(cells)!=24 or len(contexts)!=2 or len(structure)!=12: raise SystemExit('input row count mismatch')
context_by_rank={r['continuationRank']:r for r in contexts}
structure_by_locale={r['locale']:r for r in structure}
if set(context_by_rank)!={301,302}: raise SystemExit('caller rank mismatch')
if selection['firstSelected']['continuationRank']!=301 or selection['lastSelected']['continuationRank']!=302: raise SystemExit('continuation boundaries mismatch')
if selection['previousBoundary']['continuationRank']!=300 or selection['nextBoundary']['continuationRank']!=303: raise SystemExit('adjacent boundary mismatch')
if selection['firstSelected']['sourceId']!=context_by_rank[301]['sourceId'] or selection['lastSelected']['sourceId']!=context_by_rank[302]['sourceId']: raise SystemExit('selected stable IDs mismatch')

ledger=[]
for c in sorted(cells,key=lambda x:(x['continuationRank'],LOCALES.index(x['locale']))):
 rank=c['continuationRank']; locale=c['locale']; cx=context_by_rank[rank]; cat=structure_by_locale[locale]
 if rank not in (301,302) or c['locale'] not in LOCALES: raise SystemExit('unexpected cell scope')
 if c['sourceId']!=cx['sourceId'] or c['source']!=cx['source'] or c['sourceSha256']!=cx['sourceSha256']: raise SystemExit('cell/context source mismatch')
 if sha(c['source'])!=c['sourceSha256'] or sha(c['currentTarget'])!=c['currentTargetSha256']: raise SystemExit('source/current hash mismatch')
 if c['catalogPath']!=cat['catalogPath'] or c['catalogFileSha256']!=cat['sha256'] or c['catalogGitBlob']!=cat['gitBlob'] or cat['entryCount']!=6176: raise SystemExit('catalog pin mismatch')
 if c['containsCandidate'] is not False or c['verdict'] is not None: raise SystemExit('candidate leakage or prior verdict')
 if c['callerContextSha256'] is None or c['callerRefs']!=[{'path':x['path'],'line':x['line'],'lineSha256':x['lineSha256'],'fileSha256':x['fileSha256'],'gitBlob':x['gitBlob']} for x in cx['callers']]: raise SystemExit('caller pin mismatch')
 src=c['source']; current=c['currentTarget']; src_ph=tokens(src,PH); cur_ph=tokens(current,PH); src_tags=tokens(src,TAG); cur_tags=tokens(current,TAG)
 if src_ph!=cur_ph or src_tags!=cur_tags: raise SystemExit('source/current placeholder or markup mismatch')
 if rank==301:
  if src!='- {warning}' or src_ph!={'{warning}':1}: raise SystemExit('rank 301 source/token mismatch')
  if cur_ph!={'{warning}':1}: raise SystemExit('rank 301 current missing exact token')
  decision='accept-current'; target=None
  rationale='The pinned caller appends one formatted preview.warnings value after a list marker, under the localized Warnings heading. There is no prose to translate in this template. Keep the exact {warning} placeholder; the Japanese middle-dot list marker is appropriate in Japanese.'
  confidence='moderate'
  review_target=current
  exact_placeholders={'{warning}':1}
 else:
  decision,target,rationale=RANK302[locale]
  if src!='Job Types': raise SystemExit('rank 302 source mismatch')
  review_target=target if target is not None else current
  exact_placeholders={}
 out=review_target
 out_ph=tokens(out,PH); out_tags=tokens(out,TAG)
 if out_ph!=src_ph or out_tags!=src_tags: raise SystemExit(f'review target structural mismatch at {rank}/{locale}')
 if rank==301 and out_ph!={'{warning}':1}: raise SystemExit(f'{locale}: {warning} token not preserved')
 numeric_src=c.get('sourceNumericTokens',[]); numeric_cur=c.get('currentNumericTokens',[])
 if numeric_src!=numeric_cur: raise SystemExit('source/current numeric token mismatch')
 # No numeric tokens are introduced or dropped by these blind proposals.
 if re.findall(r'\d+',out)!=numeric_src: raise SystemExit(f'review target numeric mismatch at {rank}/{locale}')
 caller_refs=cx['callers']
 if rank==301:
  if len(caller_refs)!=1 or 'preview.warnings.forEach' not in caller_refs[0]['lineText'] or 'formatWarning(warning)' not in '\n'.join(x['text'] for x in caller_refs[0]['context']): raise SystemExit('rank 301 caller semantics mismatch')
 else:
  if len(caller_refs)!=1 or 'System/Jobs/index.jsx' not in caller_refs[0]['path'] or 'analytics.byType' not in '\n'.join(x['text'] for x in caller_refs[0]['context']): raise SystemExit('rank 302 caller semantics mismatch')
 row={
  'schemaVersion':1,'window':'W56','continuationRank':rank,'historicalSourceOrdinal':None,
  'sourceId':c['sourceId'],'source':src,'sourceSha256':c['sourceSha256'],'locale':locale,
  'catalogPath':c['catalogPath'],'catalogFileSha256':c['catalogFileSha256'],'catalogGitBlob':c['catalogGitBlob'],
  'currentTarget':current,'currentTargetSha256':c['currentTargetSha256'],
  'callerContext':{'callerReferenceCount':cx['productionCallerCount'],'boundedScan':cx['boundedScan'],'references':caller_refs,'contextSha256s':[x['contextSha256'] for x in caller_refs]},
  'decision':decision,'candidateTarget':target,'candidateTargetSha256':sha(target) if target is not None else None,
  'selectedTarget':out,'selectedTargetSha256':sha(out),'rationale':rationale,'confidence':confidence,
  'integrityChecks':{
   'sourceHashVerified':True,'currentTargetHashVerified':True,
   'sourcePlaceholders':src_ph,'currentPlaceholders':cur_ph,'selectedPlaceholders':out_ph,
   'placeholderParity':src_ph==out_ph,
   'sourceMarkupTags':src_tags,'currentMarkupTags':cur_tags,'selectedMarkupTags':out_tags,
   'markupParity':src_tags==out_tags,
   'sourceNumericTokens':numeric_src,'currentNumericTokens':numeric_cur,'selectedNumericTokens':re.findall(r'\d+',out),
   'numericParity':numeric_src==re.findall(r'\d+',out),
   'protectedExactTokenChecks':[{'token':'{warning}','sourceCount':1,'currentCount':cur_ph.get('{warning}',0),'selectedCount':out_ph.get('{warning}',0),'preservedExactly':cur_ph.get('{warning}',0)==1 and out_ph.get('{warning}',0)==1}] if rank==301 else []
  },
  'nativeSpeakerApproved':False
 }
 ledger.append(row)

if len(ledger)!=24 or sum(1 for x in ledger if x['continuationRank']==301)!=12 or sum(1 for x in ledger if x['continuationRank']==302)!=12: raise SystemExit('ledger cell counts incorrect')
if any(x['integrityChecks']['protectedExactTokenChecks'] and not x['integrityChecks']['protectedExactTokenChecks'][0]['preservedExactly'] for x in ledger): raise SystemExit('protected warning token failure')
write_jsonl(ROOT/'blind-decisions.jsonl',ledger)
proposal_rows=[x for x in ledger if x['candidateTarget'] is not None]
summary={
 'artifact':'slskdN PR #409 independent blind semantic review W56 ranks 301-302',
 'repository':REPO,'pullRequest':PR,'head':HEAD,'tree':TREE,'branch':'codex/slskdn-oidc-tooltip-localization-20261030',
 'window':'W56','reviewMode':'blind; used only the candidate-free packet and live PR pin verification',
 'candidateFreeInputManifestSha256':sha((INPUT/'manifest.json').read_bytes()),
 'candidateFreePacketChecksumListSha256':sha((INPUT/'PACKET-SHA256SUMS.txt').read_bytes()),
 'verifiedInputFiles':8,'sourceCount':2,'localeCount':12,'reviewedCells':24,'callerReferences':2,
 'decisionCounts':{k:sum(1 for x in ledger if x['decision']==k) for k in sorted(set(x['decision'] for x in ledger))},
 'proposedChanges':len(proposal_rows),'proposalsByPosition':{'301':0,'302':len([x for x in proposal_rows if x['continuationRank']==302])},
 'rank301':{'decision':'accept-current in all locales','exactWarningPlaceholderRequired':'{warning}','placeholderPreservationFailures':0,'listMarkerRationale':'caller emits one warning per line; current locale list marker is preserved'},
 'rank302':{'caller':'System > Jobs statistic over Object.keys(analytics.byType).length','meaning':'system/background job categories, not employment categories','changeLocales':[x['locale'] for x in proposal_rows if x['continuationRank']==302]},
 'placeholderCheckCount':24,'placeholderMismatchCount':0,'markupCheckCount':24,'markupMismatchCount':0,
 'numericTokenCheckCount':24,'numericTokenMismatchCount':0,'protectedWarningTokenCheckCount':12,'protectedWarningTokenFailures':0,
 'nativeSpeakerApproval':False,'repositoryOrPREdited':False,'testsBuildsScansCIWorkflowBrowserMergeReleaseOrTagActions':False
}
write_json(ROOT/'summary.json',summary)
print(json.dumps(summary,ensure_ascii=False,indent=2))
