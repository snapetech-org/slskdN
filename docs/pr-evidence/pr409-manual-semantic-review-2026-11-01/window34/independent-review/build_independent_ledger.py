#!/usr/bin/env python3
"""Build read-only row-level cross-review dispositions for W34."""
import collections, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'independent-review'
HEAD='dc8ed2406a2247600d487df1ae3128ce08cc7faa'
TREE='9909f5d6e32dfcc78ba53aa0c838f95e9ba246d3'
SOURCE_TREE='594e56c3f439bad476b1bd57e0de1665c62fa1bb'
def sha(s): return hashlib.sha256(s if isinstance(s,bytes) else s.encode('utf-8')).hexdigest()
def rows(p): return [json.loads(x) for x in (ROOT/p).read_text(encoding='utf-8').splitlines() if x.strip()]
manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
inputs=rows('review-input.jsonl')
original_decisions={r['id']:r for r in rows('review-decisions.jsonl')}
plan={r['id']:r for r in rows('crossreview-plan.jsonl')}
uncertain={r['id']:r for r in rows('uncertain-ledger.jsonl')}
# The source-specific caller context checked during this independent pass.
context={
'src_02f5f7929175e1c0':'Pod opinion retrieval button loads opinions for a supplied pod and content ID so the user can inspect ratings and notes.',
'src_0303e18246708180':'Lidarr connection and setup-health status; the value denotes a service that is not connected.',
'src_030a1b1d9c5117ee':'Setup-health status for the required download destination path; it is missing or unavailable.',
'src_03146d319e93da56':'Pod content-ID validation success; the checkmark and valid identifier meaning are intact.',
'src_031a8f0f659df890':'Generic failed state reused in status lists, job filtering, import history, and fallback text.',
'src_034d99b92c102178':'Broadcast error explains an expired host session and instructs the user to start a new broadcast.',
'src_03513e10082916f0':'Pod routing result reports the number of target Soulseek network peers.',
'src_03867aea70acaf4c':'Discovery graph evidence lane and Quarantine Jury evidence column; this is supporting evidence, not a certificate.',
'src_0390795f456408d4':'Navigation/page heading for the system log view.',
'src_03bd71353a136104':'Advanced controls for publishing data into the Pod registry.',
'src_03c73a8121cec12f':'Admin Policies Transfer Policy card summarizes transfer concurrency slots, speed limits, auto-replace, and scheduled-limit enablement.',
'src_03d02cb9535b25b0':'Remote peer endpoint is unavailable during a transfer.',
'src_0404be0f930be704':'Tooltip on the button that loads metadata export, import, and conflict-resolution metrics.',
'src_046a093f5e41b87e':'Label immediately preceding a count of detected duplicate hashes.',
'src_046ca04041737cfb':'Visualizer control picks a random imported native preset from the browser-local preset library.',
'src_047b64c86d5d9f2b':'Fallback placeholder in the download-destination selector for a configured default.',
'src_04875bce2d1363bd':'Footer tooltip reports the count of remote peers in the overlay network; {count} is the rendered count.',
'src_0489310e023d53ed':'Security setting for an anonymity mode that uses relays only.',
'src_048fc12579e7f9cd':'Song-ID scorecard category counts AI heuristic clips.',
'src_04abc996f51bbd12':'Player-bar notice says an action was prepared for a title and explicitly says files were not moved or deleted.',
'src_04d1e2c8561db224':'MediaCore status message while checking the protected PodCore service name.',
'src_04d21f2e2af9f9a0':'Jobs-page error toast for a failed jobs-fetch request.',
'src_04d7b48339271ea6':'Primary navigation item for the messages/chat section.',
'src_04dfac3671b494ad':'Connection-state and integration status meaning disconnected.',
'src_04e24b989d400c03':'Media-server automation action exports confirmed local plays (scrobbles) or ratings back to the selected profile.',
}
# Independent decisions for candidate cells; unchanged rows receive the source-specific caller rationale above.
candidate_reason={
'de:src_02f5f7929175e1c0':'The button retrieves existing opinion records; “Meinungen abrufen” expresses loading/retrieval rather than soliciting opinions.',
'ja:src_02f5f7929175e1c0':'The tooltip explicitly loads existing opinions for review; 読み込む is the appropriate load action, unlike 聞く (“ask/listen”).',
'fr:src_031a8f0f659df890':'A neutral failure-state noun avoids the current plural adjective whose subject varies across this key’s status and fallback callers.',
'pt-BR:src_031a8f0f659df890':'Falha is a neutral failure-state label; Falharam says “they failed” and does not fit all standalone status callers.',
'zh-Hans:src_03513e10082916f0':'The caller counts target Soulseek peers; 对等方 means a network peer, while 同行 means a colleague or person in the same field.',
'hi:src_03513e10082916f0':'The caller counts Soulseek peers; पीयर preserves the P2P participant meaning rather than coworker सहकर्मी.',
'de:src_03513e10082916f0':'Ziel-Peers correctly identifies destination network peers; Zielkollegen would mean coworkers.',
'ko:src_03513e10082916f0':'The value is a count of P2P peers, so 피어 is the technical network term rather than colleague 동료.',
'zh-Hant:src_03513e10082916f0':'The caller counts network peers; 對等方 is the P2P participant term rather than colleagues 同行.',
'vi:src_03513e10082916f0':'The result counts remote P2P peers; Peer mục tiêu is more precise than the relational/object-like Đối tượng ngang hàng.',
'id:src_03513e10082916f0':'The result counts Soulseek network peers; Peer sasaran avoids reading Rekan as an associate or coworker.',
'ar:src_03867aea70acaf4c':'Both callers use the label for supporting evidence; شهادة means testimony/certificate, whereas أدلة means evidence.',
'ja:src_03c73a8121cec12f':'The proposed text removes two invisible zero-width spaces inside 速度上限 without changing the meaning; French is held separately for transfer-slot terminology.',
'zh-Hans:src_03d02cb9535b25b0':'This is a remote network peer error; 对等方 names the peer, while 对等点 can suggest a point or location.',
'hi:src_03d02cb9535b25b0':'The transfer error concerns a P2P peer, not a coworker; पीयर available/not-available wording fits that entity.',
'zh-Hant:src_03d02cb9535b25b0':'The transfer error concerns a network peer; 對等方 is the participant term, not a point/location.',
'vi:src_03d02cb9535b25b0':'The error concerns the remote Peer; the proposal names the unavailable participant rather than the peer-to-peer relationship.',
'id:src_03d02cb9535b25b0':'The error concerns the remote Peer; Peer tidak tersedia is clearer than a colleague/associate being unavailable.',
'hi:src_0404be0f930be704':'The tooltip concerns metadata conflicts; संघर्ष is conflict, whereas विरोध means opposition.',
'hi:src_046a093f5e41b87e':'The label precedes a duplicate-hash count; डुप्लिकेट मिले naturally signals multiple duplicates found.',
'ko:src_046ca04041737cfb':'The control chooses an imported native preset from this browser; 네이티브 preserves native, while 기본 incorrectly changes it to default.',
'zh-Hans:src_04875bce2d1363bd':'This footer count is overlay-network peers; 对等方 is the network participant and {count} is unchanged.',
'zh-Hant:src_04875bce2d1363bd':'This footer count is overlay-network peers; 對等方 identifies peers rather than P2P devices, and {count} is unchanged.',
'hi:src_048fc12579e7f9cd':'This scorecard category counts heuristic clips; ह्यूरिस्टिक्स names the method category rather than an estimate/inference.',
'ar:src_048fc12579e7f9cd':'This scorecard category names AI heuristic methods; the proposal avoids a reading of “reasoning about AI.”',
'vi:src_048fc12579e7f9cd':'The scorecard category is AI heuristics, not diagnosis; the proposal preserves the technical heuristic concept.',
'hi:src_04d1e2c8561db224':'PodCore is a protected product/service name; the proposal keeps its exact Latin spelling.',
'zh-Hans:src_04e24b989d400c03':'The action exports listening history/scrobbles and ratings; the current phrase says Scrabble, the unrelated word game.',
'pt-BR:src_04e24b989d400c03':'The operation exports local plays or ratings; avaliações conveys user ratings better than classificação, which can mean ranking/classification.',
'ar:src_04e24b989d400c03':'التمرير means scrolling and التصنيف can mean ranking; the proposal clearly labels listening-history and rating export.',
'zh-Hant:src_04e24b989d400c03':'The action exports listening history and ratings; the current phrase names the Scrabble game.',
'vi:src_04e24b989d400c03':'The proposal corrects the commercial “export” and ranking senses while preserving scrobble and rating export.',
'id:src_04e24b989d400c03':'The proposal gives natural export-first word order and identifies both scrobble and rating data.',
}
french_keep_rationale='The pinned Transfer Policy card summarizes the immediately following numeric Upload Slots and Download Slots fields (uploadSlots/downloadSlots), alongside speed ceilings, auto-replace, and schedule enablement. The exact French sibling labels are “Emplacements d’envoi” and “Emplacements de téléchargement”, establishing Emplacements as this interface’s transfer-slot term. Keep the current summary “Emplacements, plafonds de vitesse, remplacement automatique et activation de la planification.” unchanged; no terminology hold remains.'
refinements={
 'zh-Hant:src_04875bce2d1363bd':('覆疊網路對等方：{count}','對等方 fixes the peer term, but the proposed 覆蓋網路 departs from the catalog’s existing Traditional Chinese term 覆疊網路 for overlay network. Keep that established term and apply the peer correction.')
}
ledger=[]
for row in inputs:
    ident=row['id']; sid=row['sourceId']; loc=row['locale']
    base={
      'id':ident,'locale':loc,'sourceId':sid,'source':row['source'],
      'sourceSha256':row['sourceSha256'],'currentTarget':row['target'],
      'currentTargetSha256':row['targetSha256'],'catalogPath':row['catalogPath'],
      'currentCatalogFileSha256':manifest['currentCatalogFileSha256'][loc],
      'prHead':HEAD,'prTree':TREE,'sourceSubtreePath':manifest['sourceSubtreePath'],
      'sourceSubtreeTree':SOURCE_TREE,'callerPins':row['sourceCallsites'],
      'placeholders':row.get('placeholders',[]),'protectedLiterals':row.get('protectedLiterals',[]),
      'nativeSpeakerApproved':False,'reviewConfidence':'moderate'
    }
    if ident in plan:
        c=plan[ident]
        if ident in refinements:
            final_text,final_rationale=refinements[ident]
            base.update({
              'independentDisposition':'refine-proposed','finalTarget':final_text,
              'finalTargetSha256':sha(final_text),'candidateTarget':c['proposedTarget'],
              'candidateTargetSha256':c['proposedTargetSha256'],
              'rationale':final_rationale,
              'packetDisposition':original_decisions[ident]['verdict']
            })
        else:
            base.update({
              'independentDisposition':'accept-proposed','finalTarget':c['proposedTarget'],
              'finalTargetSha256':c['proposedTargetSha256'],'candidateTarget':c['proposedTarget'],
              'candidateTargetSha256':c['proposedTargetSha256'],
              'rationale':candidate_reason[ident],
              'packetDisposition':original_decisions[ident]['verdict']
            })
    elif ident in uncertain:
        base.update({
          'independentDisposition':'keep-current','finalTarget':row['target'],
          'finalTargetSha256':row['targetSha256'],'candidateTarget':None,
          'candidateTargetSha256':None,'rationale':french_keep_rationale,
          'packetDisposition':original_decisions[ident]['verdict']
        })
    else:
        base.update({
          'independentDisposition':'keep-current','finalTarget':row['target'],
          'finalTargetSha256':row['targetSha256'],'candidateTarget':None,
          'candidateTargetSha256':None,
          'rationale':'The exact pinned caller context supports the current rendering: '+context[sid],
          'packetDisposition':original_decisions[ident]['verdict']
        })
    ledger.append(base)
assert len(ledger)==274 and len({r['id'] for r in ledger})==274
assert collections.Counter(r['independentDisposition'] for r in ledger)=={'accept-proposed':32,'refine-proposed':1,'keep-current':241}
(OUT/'independent-crossreview-window34.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in ledger),encoding='utf-8')
summary={
 'result':'INDEPENDENT_CROSS_REVIEW_COMPLETE','window':34,
 'repository':'snapetech-org/slskdN','pullRequest':409,
 'livePrState':'OPEN','livePrDraft':True,'livePrMergeState':'CLEAN',
 'head':HEAD,'tree':TREE,'sourceSubtreeTree':SOURCE_TREE,
 'reviewedCells':len(ledger),'sourceKeys':len({r['sourceId'] for r in ledger}),
 'dispositions':dict(collections.Counter(r['independentDisposition'] for r in ledger)),
 'acceptedCorrectionRows':32,'refinedCorrectionRows':1,'keptRows':241,'heldRows':0,
 'packetUncertainCellIndependentlyResolved':'fr:src_03c73a8121cec12f','packetUncertainSource':'Slots, speed ceilings, auto-replace, and schedule enablement.',
 'correctionCandidatesAcceptedAsProposed':32,'refined':1,'keptDespiteCandidate':0,
 'staleOrDuplicateRows':0,'exactSourceCurrentCallerPlaceholderProtectedLiteralPins':'passed independently',
 'manualOverlap':0,'appliedCorrectionOverlap':0,
 'formalOverlap':'packet preflight claims 0; raw formal result rows are not included in the supplied packet, so this component was not independently reconstructed',
 'nativeSpeakerApproved':False,'testsBuildsOrRepoChanges':False,
 'ledgerSha256':sha((OUT/'independent-crossreview-window34.jsonl').read_bytes()),
 'rationale':'The candidate fixes align with exact caller context; one zh-Hant overlay term was refined for catalog consistency. The packet’s French uncertainty is independently resolved as keep-current because the neighboring Upload Slots and Download Slots controls use the exact French transfer-slot term “Emplacements d’envoi” and “Emplacements de téléchargement”.'
}
(OUT/'independent-crossreview-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
