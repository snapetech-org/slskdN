#!/usr/bin/env python3
from __future__ import annotations
import collections,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
CF=ROOT/'candidate-free'/'input'; PR=ROOT/'primary-review'; BL=ROOT/'blind-review'; OUT=ROOT/'cross-review'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PH=re.compile(r'\{[^{}]+\}'); MARKUP=re.compile(r'<[^>]+>'); NUM=re.compile(r'(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])')
def sha(b):return hashlib.sha256(b).hexdigest()
def shat(s):return sha(s.encode('utf-8'))
def canon(o):return (json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def rdj(p):return json.loads(p.read_text())
def loadjl(p):return [(json.loads(line),line.encode()) for line in p.read_text().splitlines() if line.strip()]
def wj(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def wjl(name,rows):(OUT/name).write_bytes(b''.join(canon(r) for r in rows))
def need(ok,msg):
 if not ok:raise SystemExit('FAIL: '+msg)
def verify_sum(folder):
 subprocess.run(['sha256sum','-c','SHA256SUMS.txt'],cwd=folder,check=True,stdout=subprocess.DEVNULL)

def token_check(source,target,token):
 ph=token['placeholders']['source']; nums=token['numbers']['source']; markup=token['markup']['source']; protected=token['protectedLiterals']['source']
 return {'placeholderParity':collections.Counter(PH.findall(source))==collections.Counter(ph)==collections.Counter(PH.findall(target)),
         'markupParity':MARKUP.findall(source)==markup==MARKUP.findall(target),
         'numericTokensPreserved':collections.Counter(NUM.findall(source))==collections.Counter(nums)==collections.Counter(NUM.findall(target)),
         'protectedLiteralsPreserved':all(x in target for x in protected),
         'sourceProtectedLiterals':protected}

# Upstream packet checksums and exact pin consistency.
for folder in (CF,PR,BL):verify_sum(folder)
cfm=rdj(CF/'manifest.json'); prm=rdj(PR/'manifest.json'); blm=rdj(BL/'manifest.json')
need(cfm['head']==prm['head']==blm['head']=='fc8e42a06363ceee762ae084bbe716953d4a5d94','upstream head pins')
need(cfm['tree']==prm['tree']==blm['tree']=='e04aa06b8cfb0ee41cae90aef601a0552b5e85bd','upstream tree pins')
need(prm['candidateFreeInputManifestSha256']==sha((CF/'manifest.json').read_bytes()),'primary candidate-free manifest pin')
need(blm['candidateFreeChecksumListSha256']==sha((CF/'SHA256SUMS.txt').read_bytes()),'blind candidate-free checksum-list pin')
sel=rdj(CF/'selection-and-boundary.json'); live_before=rdj(OUT/'attestation'/'live-before.json')
need(sel['continuationRankRange']==[953,977] and sel['remainingQueueRankRange']==[853,877],'rank ranges')
need(live_before['headSha']==cfm['head'] and live_before['headTree']==cfm['tree'],'live-before packet head/tree')
need(live_before['apiBaseSha']=='f25d263a2a7cdb2c8f76c40c346cb10f749a9356','API base pin')
# Current sources/cells/callers.
sources=[r for r,_ in loadjl(CF/'selected-sources.jsonl')]
cell_pairs=loadjl(CF/'source-current-cells.jsonl'); cells=[r for r,_ in cell_pairs]
ctx=[r for r,_ in loadjl(CF/'caller-contexts.jsonl')]
need(len(sources)==25 and len(cells)==300 and len(ctx)==25,'candidate-free dimensions')
need([s['continuationRank'] for s in sources]==list(range(953,978)),'source order')
need([s['remainingQueueRank'] for s in sources]==list(range(853,878)),'queue order')
sm={s['sourceId']:s for s in sources}; ctxm={r['sourceId']:r for r in ctx}
cm={(r['sourceId'],r['locale']):r for r in cells}; cbytes={(r['sourceId'],r['locale']):raw.rstrip(b'\n') for r,raw in cell_pairs}
need(len(cm)==300 and len(ctxm)==25,'unique cell/source maps')
for c in cells:
 s=sm[c['sourceId']]; cr=ctxm[c['sourceId']]
 need(c['source']==s['source'] and c['sourceSha256']==s['sourceSha256'] and shat(c['source'])==c['sourceSha256'],'source row hash')
 need(c['continuationRank']==s['continuationRank'] and c['remainingQueueRank']==s['remainingQueueRank'],'cell rank')
 need(c['locale'] in LOCALES and c['callerCount']==cr['productionCallerCount']==len(c['callerRefs']),'caller count')
 # Compare context reference projection; full caller context contains surrounding source lines.
 projected=[{k:x[k] for k in ('path','line','lineSha256','fileSha256','gitBlob','contextSha256')} for x in cr['callers']]
 need(projected==c['callerRefs'],'candidate-free caller reference pins')
 need(all(x['fileSha256'] and x['gitBlob'] and x['lineSha256'] and x['contextSha256'] for x in c['callerRefs']),'complete caller pins')
 need(c['currentTargetTextIncluded'] is True and c['sourceTextIncluded'] is True,'candidate-free values available')
 need(shat(c['currentTarget'])==c['currentTargetSha256'],'current target hash')
 token=c['tokenEvidence']; current_check=token_check(c['source'],c['currentTarget'],token)
 need(all(current_check[k] for k in ('placeholderParity','markupParity','numericTokensPreserved','protectedLiteralsPreserved')),'baseline token integrity')

primary_pairs=loadjl(PR/'primary-review.jsonl'); primary={(r['sourceId'],r['locale']):r for r,_ in primary_pairs}
blind_pairs=loadjl(BL/'blind-ledger.jsonl'); blind={(r['continuationRank'],r['locale']):r for r,_ in blind_pairs}
blind_props=loadjl(BL/'proposals.jsonl'); blind_props_map={(r['continuationRank'],r['locale']):r for r,_ in blind_props}
primary_corr=loadjl(PR/'corrections.jsonl'); primary_corr_map={(r['sourceId'],r['locale']):r for r,_ in primary_corr}
primary_holds=loadjl(PR/'holds-hash-only.jsonl'); blind_holds=loadjl(BL/'holds-hash-only.jsonl')
need(len(primary)==len(blind)==300 and len(primary_corr)==111 and len(blind_props)==66 and len(primary_holds)==0 and len(blind_holds)==12,'review packet dimensions')
# Confirm both reviewers reference exact candidate-free source/current/caller/catalog pins.
for key,c in cm.items():
 p=primary[key]; b=blind[(c['continuationRank'],c['locale'])]
 for r,name in ((p,'primary'),(b,'blind')):
  need(r['head']==cfm['head'] and r['tree']==cfm['tree'],'review exact pin '+name)
  need(r['sourceSha256']==c['sourceSha256'] and r['currentTargetSha256']==c['currentTargetSha256'] and r['callerContextSha256']==c['callerContextSha256'],'review source/current/caller hash '+name)
  if name=='blind' and r['decision']=='hold':
   need(r['sourceIdSha256']==shat(c['sourceId']) and r['sourceTextIncluded'] is False and r['currentTargetTextIncluded'] is False,'blind hold identifier/hash-only binding')
  else:
   need(r['catalogFileSha256']==c['catalogFileSha256'] and r['catalogGitBlob']==c['catalogGitBlob'],'review catalog pin '+name)
   need(r['source']==c['source'] and r['currentTarget']==c['currentTarget'],'review input text mismatch '+name)
 if p['disposition']=='correction':
  q=primary_corr_map.get(key);need(q and q['candidateTargetSha256']==p['candidateTargetSha256'] and q['candidateTarget']==p['candidateTarget'],'primary correction list reconciliation')
  pcheck=token_check(c['source'],p['candidateTarget'],c['tokenEvidence'])
  need(shat(p['candidateTarget'])==p['candidateTargetSha256'] and all(pcheck[k] for k in ('placeholderParity','markupParity','numericTokensPreserved','protectedLiteralsPreserved')),'primary candidate token integrity')
 else:need(key not in primary_corr_map,'unexpected primary proposal')
 if b['decision'] in ('correction','refinement'):
  q=blind_props_map.get((c['continuationRank'],c['locale']));need(q and q['proposedTargetSha256']==b['proposedTargetSha256'] and q['proposedTarget']==b['proposedTarget'],'blind proposal list reconciliation')
  bcheck=token_check(c['source'],b['proposedTarget'],c['tokenEvidence'])
  need(shat(b['proposedTarget'])==b['proposedTargetSha256'] and all(bcheck[k] for k in ('placeholderParity','markupParity','numericTokensPreserved','protectedLiteralsPreserved')),'blind candidate token integrity')
 else:need((c['continuationRank'],c['locale']) not in blind_props_map,'unexpected blind proposal')
 if b['decision']=='hold':
  h=next((x for x,_ in blind_holds if x['continuationRank']==c['continuationRank'] and x['locale']==c['locale']),None)
  need(h is not None and h['sourceIdSha256']==shat(c['sourceId']) and h['sourceSha256']==c['sourceSha256'] and h['currentTargetSha256']==c['currentTargetSha256'] and h['callerContextSha256']==c['callerContextSha256'],'blind hash-only hold binding')
# Explicit cross choices, all other cells prefer an independently reviewed primary correction,
# then a blind proposal, then the current target. The lone context-ambiguous source remains held.
blind_choice={(954,'pt-BR'),(955,'hi'),(959,'hi'),(962,'ko'),(969,'ar'),(969,'id'),(969,'pt-BR'),(973,'es'),(973,'fr'),(973,'id'),(973,'pt-BR'),(975,'ko'),(975,'zh-Hans'),(975,'zh-Hant'),(976,'de'),(976,'es'),(976,'fr'),(976,'hi'),(976,'id'),(976,'ja'),(976,'ko'),(976,'vi')}
current_choice={(975,'vi')}
adjusted={(977,'vi'):'Chuyển giao vào hàng đợi thu mua nội dung.'}
rationales={
953:'Descriptive membership workflow link; preserve the Pod entity and present the four actions as flows.',
954:'Success toast counts nearby Atlas searches; keep {count} attached to the search operation.',
955:'Empty group state; the text reports that no members are assigned.',
956:'Bridge tooltip distinguishes stopping the local legacy-client bridge from starting it and states the active-client disconnect effect.',
957:'Validation toast requests Pod JSON input; retain the product entity and JSON format.',
958:'Section heading directs the user to review opinions; use a concise panel-heading form.',
959:'Form label denotes the search-history retention duration measured in minutes.',
960:'Accessible checkbox label disables the recipe title; preserve {title}.',
961:'Fallback label for a newly opened room tab.',
962:'Mesh evidence section heading for outbound publication.',
963:'Transfer table column for the local file.',
964:'Dropdown duration option; preserve the numeric value 3.',
965:'Confirmation question for permanent deletion; preserve the {fullName} interpolation.',
966:'The pinned occurrences are layout/alignment attributes, not demonstrated user-facing localization calls; defer all locales as hash-only holds.',
967:'Tooltip describes changing a verified peer’s Pod role and granting or removing moderator/owner duties.',
968:'Collapse control hides a section’s conversations; preserve {section}.',
969:'Tooltip describes recounting configured shares after file or exclusion changes.',
970:'Policy preview label for promoting/featuring a library item, paired with archive and expire.',
971:'Wishlist button starts enabled searches; make the search object explicit.',
972:'Playlist intake detail states the multi-artist policy; preserve {policy}.',
973:'Room creation type is a private chat room, not a residential bedroom.',
974:'Modal title for the playback queue.',
975:'Automation recipe checks the media library’s health/status.',
976:'Lidarr toast confirms import queuing and reports the safe-candidate file count; preserve Lidarr and {safeCandidates}.',
977:'Integration label hands content to the acquisition queue; retain the media-content context.'}
ledger=[]; held=[]; proposal_reconciliation=[]; dispositions=collections.Counter(); selected_source=collections.Counter(); proposal_outcomes=collections.Counter()
for s in sources:
 rank=s['continuationRank']; sid=s['sourceId']
 for loc in LOCALES:
  key=(sid,loc); c=cm[key]; p=primary[key]; b=blind[(rank,loc)]; token=c['tokenEvidence']
  if b['decision']=='hold':
   need(rank==966,'unexpected blind hold outside ambiguous source')
   source_id_sha=shat(sid)
   row={'schemaVersion':1,'continuationRank':rank,'remainingQueueRank':c['remainingQueueRank'],'sourceIdSha256':source_id_sha,'sourceTextSha256':c['sourceSha256'],'sourceCurrentCellSha256':sha(cbytes[key]),'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'callerReferencePinsSha256':b['callerReferencePinsSha256'],'callerCount':c['callerCount'],'locale':loc,'primaryDisposition':p['disposition'],'primaryCandidateTargetSha256':p['candidateTargetSha256'],'blindDecision':'hold','blindHoldReasonClass':'no-user-facing-localization-call','recommendation':'hold-hash-only','recommendedTargetTextIncluded':False,'sourceTextIncluded':False,'currentTargetTextIncluded':False,'confidence':'high','rationale':rationales[rank]}
   ledger.append(row);held.append({'schemaVersion':1,'continuationRank':rank,'remainingQueueRank':c['remainingQueueRank'],'sourceIdSha256':source_id_sha,'sourceTextSha256':c['sourceSha256'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'callerReferencePinsSha256':b['callerReferencePinsSha256'],'callerCount':c['callerCount'],'locale':loc,'reason':'Only layout/alignment references are pinned; a user-facing translation caller is not demonstrated. Keep current cell hash-only until a genuine localization call is established.','sourceTextOmitted':True,'currentTargetTextOmitted':True,'proposalTextOmitted':True,'crossDecision':'hold-hash-only'})
   dispositions['hold-hash-only']+=1;selected_source['none']+=1
   for side,decision,target,thash in [('primary',p['disposition'],p.get('candidateTarget'),p.get('candidateTargetSha256')),('blind',b['decision'],b.get('proposedTarget'),b.get('proposedTargetSha256'))]:
    if decision in ('correction','refinement'):
     proposal_reconciliation.append({'schemaVersion':1,'reviewer':side,'continuationRank':rank,'remainingQueueRank':c['remainingQueueRank'],'sourceIdSha256':source_id_sha,'locale':loc,'sourceSha256':c['sourceSha256'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'proposalSha256':thash,'proposalTextIncluded':False,'crossOutcome':'held-hash-only','crossTargetSha256':None,'rationale':'A blind-review caller-context hold supersedes text proposals for this source.'})
     proposal_outcomes['held-hash-only']+=1
   continue
  if (rank,loc) in adjusted:
   target=adjusted[(rank,loc)]; selected='cross-adjustment'
  elif (rank,loc) in current_choice:
   target=c['currentTarget']; selected='current'
  elif (rank,loc) in blind_choice:
   target=b['proposedTarget']; selected='blind'
  elif p['disposition']=='correction':
   target=p['candidateTarget']; selected='primary'
  elif b['decision'] in ('correction','refinement'):
   target=b['proposedTarget']; selected='blind'
  else:
   target=c['currentTarget']; selected='current'
  recommended_check=token_check(c['source'],target,token)
  need(all(recommended_check[k] for k in ('placeholderParity','markupParity','numericTokensPreserved','protectedLiteralsPreserved')),'selected wording token integrity '+str((rank,loc)))
  phash=shat(p['candidateTarget']) if p.get('candidateTarget') is not None else None
  bhash=shat(b['proposedTarget']) if b.get('proposedTarget') is not None else None
  target_hash=shat(target)
  if target_hash==c['currentTargetSha256']: status='accept-current'
  elif target_hash==phash and target_hash==bhash: status='accept-agreement'
  elif target_hash==phash: status='accept-primary'
  elif target_hash==bhash: status='accept-blind'
  else: status='adjust'
  row={'schemaVersion':1,'continuationRank':rank,'remainingQueueRank':c['remainingQueueRank'],'sourceId':sid,'sourceTextSha256':c['sourceSha256'],'sourceCurrentCellSha256':sha(cbytes[key]),'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'callerCount':c['callerCount'],'locale':loc,'primaryDisposition':p['disposition'],'primaryCandidateTargetSha256':phash,'blindDecision':b['decision'],'blindProposalTargetSha256':bhash,'recommendation':status,'recommendationSource':selected,'recommendedTarget':target,'recommendedTargetSha256':target_hash,'tokenIntegrity':{k:recommended_check[k] for k in ('placeholderParity','markupParity','numericTokensPreserved','protectedLiteralsPreserved')},'confidence':'moderate','rationale':rationales[rank]}
  ledger.append(row);dispositions[status]+=1;selected_source[selected]+=1
  for side,decision,candidate,chash in [('primary',p['disposition'],p.get('candidateTarget'),phash),('blind',b['decision'],b.get('proposedTarget'),bhash)]:
   if decision not in ('correction','refinement'):continue
   actual=shat(candidate); outcome='selected' if actual==target_hash else ('superseded-by-cross-adjustment' if selected=='cross-adjustment' else 'superseded-by-current' if selected=='current' else 'reviewer-option-not-selected')
   proposal_reconciliation.append({'schemaVersion':1,'reviewer':side,'continuationRank':rank,'remainingQueueRank':c['remainingQueueRank'],'sourceId':sid,'locale':loc,'sourceSha256':c['sourceSha256'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'proposalSha256':chash,'proposalTextIncluded':False,'crossOutcome':outcome,'crossTargetSha256':target_hash,'rationale':('Cross-review selected this wording.' if outcome=='selected' else rationales[rank])})
   proposal_outcomes[outcome]+=1
# Require proposal inventory reconciliation: 111 primary + 66 blind = 177 rows.
need(len(proposal_reconciliation)==177,'proposal reconciliation count')
need(len(ledger)==300 and len(held)==12,'final ledger/hold count')
need(sum(r['recommendation']=='hold-hash-only' for r in ledger)==12,'exact hold set')
# Stable ordered input pins, no candidate-free/primary/blind mutation.
input_pins={'candidateFreeManifestSha256':sha((CF/'manifest.json').read_bytes()),'candidateFreeChecksumListSha256':sha((CF/'SHA256SUMS.txt').read_bytes()),'candidateFreeCellsSha256':sha((CF/'source-current-cells.jsonl').read_bytes()),'candidateFreeSelectedSourcesSha256':sha((CF/'selected-sources.jsonl').read_bytes()),'candidateFreeCallerContextsSha256':sha((CF/'caller-contexts.jsonl').read_bytes()),'primaryManifestSha256':sha((PR/'manifest.json').read_bytes()),'primaryChecksumListSha256':sha((PR/'SHA256SUMS.txt').read_bytes()),'primaryReviewSha256':sha((PR/'primary-review.jsonl').read_bytes()),'primaryCorrectionsSha256':sha((PR/'corrections.jsonl').read_bytes()),'blindManifestSha256':sha((BL/'manifest.json').read_bytes()),'blindChecksumListSha256':sha((BL/'SHA256SUMS.txt').read_bytes()),'blindLedgerSha256':sha((BL/'blind-ledger.jsonl').read_bytes()),'blindProposalsSha256':sha((BL/'proposals.jsonl').read_bytes()),'blindHoldsSha256':sha((BL/'holds-hash-only.jsonl').read_bytes())}
wj('input-pins.json',{'schemaVersion':1,'head':cfm['head'],'tree':cfm['tree'],'apiBase':live_before['apiBaseSha'],'liveMain':live_before['liveMainSha'],'sourceIds':25,'locales':LOCALES,'cells':300,'sourceCallerCurrentAndReviewerInputs':input_pins})
wjl('cross-review-ledger.jsonl',ledger);wjl('proposal-reconciliation.jsonl',proposal_reconciliation);wjl('holds-hash-only.jsonl',held)
changed=sum(r['recommendation'] not in ('accept-current','hold-hash-only') for r in ledger)
summary={'schemaVersion':1,'artifact':'slskdN PR #409 W953-W977 independent semantic cross-review','repository':'snapetech-org/slskdN','pullRequest':409,'branch':cfm['branch'],'window':'W83','head':cfm['head'],'tree':cfm['tree'],'apiBase':live_before['apiBaseSha'],'liveMainAtBefore':live_before['liveMainSha'],'continuationRankRange':[953,977],'remainingQueueRankRange':[853,877],'sourceCount':25,'localeCount':12,'cellCount':300,'recommendationCounts':dict(sorted(dispositions.items())),'proposalRecordsReconciled':len(proposal_reconciliation),'proposalOutcomes':dict(sorted(proposal_outcomes.items())),'primaryCorrectionsReviewed':len(primary_corr),'blindProposalsReviewed':len(blind_props),'blindHashOnlyHolds':len(held),'primaryHashOnlyHolds':len(primary_holds),'crossHoldCount':len(held),'crossHoldSourceIds':['sha256:'+held[0]['sourceIdSha256']] if held else [],'recommendedChanges':changed,'recommendedCurrentRetained':dispositions['accept-current'],'exactTargetReadyNonHoldCells':300-len(held),'tokenIntegrity':'PASS for all 288 non-hold targets and all 177 candidate proposals','callerAndSourcePins':'PASS; candidate-free verifier checked exact pinned worktree','mainDrift':rdj(CF/'main-drift.json'),'proposalInputsReadOnly':True,'repositoryOrPREdited':False,'applicationPerformed':False,'testsBuildsScansCiRun':False,'nativeSpeakerSignoff':False,'confidence':'moderate','limitations':'Machine-assisted semantic review. No native-speaker signoff or browser review. All 12 cells for source rank 966 remain text-free/hash-only because pinned production references are layout alignment attributes, not user-facing localization calls.','result':'PASS'}
wj('summary.json',summary)
(OUT/'README.md').write_text(f'''# slskdN PR #409 W953–W977 semantic cross-review

This cross-review covers 25 source IDs × 12 locales = 300 cells at PR head `{cfm['head']}` / tree `{cfm['tree']}`. It reconciles the candidate-free source/current/caller packet with the primary and blind reviews after independently checking all 300 rows and every proposed target. The exact API base is `{live_before['apiBaseSha']}`; live main at review start was `{live_before['liveMainSha']}`.

`cross-review-ledger.jsonl` binds each decision to source, current-target, caller-context, and candidate-free row hashes. It records an exact recommended target for every non-held cell, validates placeholders/markup/numeric/protected literals, and records source reviewer dispositions and proposal hashes. `proposal-reconciliation.jsonl` accounts for all {len(proposal_reconciliation)} primary and blind proposals. `holds-hash-only.jsonl` retains all 12 cells for source rank 966 without source, current target, or proposal text. The held source’s caller inventory consists of layout/alignment attributes; the blind hold is upheld and the primary Arabic suggestion is rejected as ambiguous.

The primary review supplied {len(primary_corr)} correction records and the blind review supplied {len(blind_props)} proposal records. The cross-review recommends {changed} changed targets, retains {dispositions['accept-current']} current targets, and holds 12 cells. Notable choices: retain the current Hindi library label at rank 975 rather than narrow it to a music-only scan; select explicit search wording for the Wishlist action; use chat-room terms for Private Room; use content-acquisition wording for the handoff; preserve all placeholders and protected `Lidarr` literal.

`attestation/live-before.json` and `attestation/live-after.json` pin the open draft PR, base, branch/pull refs, main, exact Git trees, and clean exact-head worktree. No product files or PR content were changed or applied. No tests/builds/CI were run. Run `python3 verify_cross_review.py` for portable checks; add `/path/to/exact-head-worktree` to verify the exact source/caller/catalog objects too.
''')
print(json.dumps({'result':'PASS','ledgerRows':len(ledger),'proposalRows':len(proposal_reconciliation),'holds':len(held),'recommendationCounts':dict(dispositions),'selectedFrom':dict(selected_source),'proposalOutcomes':dict(proposal_outcomes),'changed':changed},ensure_ascii=False,indent=2))
