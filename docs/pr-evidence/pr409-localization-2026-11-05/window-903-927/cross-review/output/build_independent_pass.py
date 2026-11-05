#!/usr/bin/env python3
"""Build the independent pre-proposal semantic pass from candidate-free input only."""
import hashlib, json, re
from pathlib import Path

ROOT = Path('/home/keith/Documents/code/task-scratch/slskdn-pr409-w903-927-20261105')
INPUT = ROOT / 'candidate-free' / 'input'
OUT = ROOT / 'cross-review' / 'output'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

INTENTS = {
903: 'Label the global upload-slot setting; caller uses it as the aria-label and localized form property for uploadSlots.',
904: 'Report that remediation for auto-fixable issues was queued and interpolate the dynamic issue count.',
905: 'Label the DHT node list or metric in the mesh view.',
906: 'Report that no audio fingerprint was produced; caller places this among audio fingerprinting and metadata statuses.',
907: 'Label the count of distinct SongRec matches in a scorecard.',
908: 'Report failure to retrieve content metadata and preserve the dynamic message.',
909: 'Offer the keep-reviewing action in a review-mode selector.',
910: 'Supply the introductory fragment before the caller’s inline ed25519 signature example and the following format clause.',
911: 'Report an incomplete album and preserve missing and total track counts in their labeled positions.',
912: 'Label a mapped path shown as code in a diagnostic.',
913: 'Describe reloading release-radar subscriptions and notifications from the local backend.',
914: 'Report failure to retrieve opinions and preserve the dynamic message.',
915: 'Label the last error field.',
916: 'Label a page-size option with the dynamic count per page.',
917: 'Describe a manual DHT lookup for this exact ContentID; use cache bypass only for a fresh read.',
918: 'Label hash field B in hexadecimal; B identifies the field.',
919: 'Report failure to update VPN policy.',
920: 'Label the metadata-corrections category.',
921: 'Label a Content ID input and give the exact content:audio:album:mb-release-id syntax example.',
922: 'Label transport status; caller places it beside a signal icon, so the reading is a network transport status.',
923: 'Explain that refreshing, listing, and aggregating opinions read Pod opinion state, while publishing and affinity recalculation are advanced operations below.',
924: 'Report failure to fetch swarm data.',
925: 'Report that this dynamically named item cannot be deleted; preserve itemType.',
926: 'Label the action that switches the visualizer into fullscreen.',
927: 'Tell the user to open this exact SongID run and follow its queue position, evidence, and download options.',
}

FIXES = {
(906,'es'): ('No se generó ninguna huella de audio.', 'In the audio-fingerprinting status context, “huellas dactilares” reads as biometric fingerprints; name the audio fingerprint directly.'),
(907,'ar'): ('مطابقات SongRec المميّزة', 'The scorecard value counts distinct matches; state that SongRec matches are being counted and preserve the SongRec name.'),
(907,'fr'): ('Correspondances distinctes de SongRec', 'The scorecard value counts distinct matches; make the match category explicit while preserving SongRec.'),
(907,'id'): ('Kecocokan unik SongRec', 'The current word “Perbedaan” means differences; the scorecard category is unique matches.'),
(907,'ja'): ('SongRec の一意な一致', 'The scorecard value counts distinct matches; name unique matches instead of the current vague “individual.”'),
(907,'pt-BR'): ('Correspondências distintas do SongRec', 'The scorecard value counts distinct matches; name the match category rather than describing SongRec as an adjective.'),
(909,'ja'): ('レビューを続ける', 'Use a natural action label for continuing the review; the current 続きレビュー is an awkward noun phrase.'),
(910,'ar'): ('في وضع الفرض، يجب أن تستخدم التوقيعات', 'The source is intentionally a fragment that flows into the inline signature example. “الامتداد” means extension, which mislabels the ed25519 signature format.'),
(918,'ar'): ('التجزئة B (ست عشري)', 'Keep the field identifier as the protected Latin capital B; do not replace it with the Arabic letter ب.'),
(918,'hi'): ('हैश B (हेक्स)', 'Keep the field identifier as the protected Latin capital B; do not transliterate it as बी.'),
(921,'ar'): ('معرّف المحتوى (ID) (مثلًا: content:audio:album:mb-release-id)', 'Restore the required literal ID and preserve the exact schema example for users to copy.'),
(921,'es'): ('ID de contenido (por ejemplo: content:audio:album:mb-release-id)', 'Restore the exact schema example; the current target translates its schema components, making the example unusable.'),
(921,'hi'): ('कंटेंट ID (जैसे: content:audio:album:mb-release-id)', 'Restore the required literal ID and exact schema example; the current target transliterates both.'),
(921,'id'): ('ID Konten (misalnya: content:audio:album:mb-release-id)', 'Preserve the exact schema example; the current target translates the content and album components.'),
(921,'zh-Hans'): ('内容 ID（例如：content:audio:album:mb-release-id）', 'Preserve the exact schema example; the current target translates the syntax components.'),
(921,'zh-Hant'): ('內容 ID（例如：content:audio:album:mb-release-id）', 'Preserve the exact schema example; the current target translates the syntax components.'),
(923,'ar'): ('يؤدي تحديث الآراء وإدراجها وتجميعها إلى قراءة حالة آراء الـpod. ويُجمع نشر الآراء وإعادة حساب بيانات التقارب أدناه ضمن العمليات المتقدمة.', 'Keep Pod as the technical entity and make clear that the read operation concerns its opinion state; the current target drops Pod.'),
(923,'es'): ('Actualizar, enumerar y agregar opiniones lee el estado de opiniones del pod. La publicación de opiniones y el recálculo de los datos de afinidad se agrupan abajo como operaciones avanzadas.', '“Grupo” changes the technical Pod entity into a generic group; preserve pod as the entity named by the caller context.'),
(923,'vi'): ('Làm mới, liệt kê và tổng hợp ý kiến sẽ đọc trạng thái ý kiến của pod. Việc xuất bản ý kiến và tính toán lại dữ liệu về mối quan hệ được nhóm bên dưới thành các thao tác nâng cao.', '“Nhóm” changes the technical Pod entity into a generic group; preserve pod as the entity named by the caller context.'),
(926,'ar'): ('افتح العارض المرئي بملء الشاشة', 'The current wording literally says to enter a visualizer; the caller is a button that switches the current visualizer into fullscreen.'),
(926,'de'): ('Vollbild-Visualizer öffnen', 'The current “Geben Sie … ein” reads like entering text into a visualizer; use a clear fullscreen action label.'),
(926,'hi'): ('फ़ुलस्क्रीन विज़ुअलाइज़र खोलें', 'The current literal “दर्ज करें” reads like entering data; use a clear action to open the visualizer in fullscreen.'),
(926,'ja'): ('ビジュアライザーを全画面で表示', 'The current 入力してください means “please enter/input”; the caller is a button that switches the visualizer to fullscreen.'),
(927,'hi'): ('इस SongID रन को खोलें और इसकी कतार स्थिति, साक्ष्य और डाउनलोड विकल्पों पर नज़र रखें।', 'Keep the protected SongID spelling; transliterating it as सॉन्गआईडी loses the exact product identifier.'),
}

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def read_jsonl(name):
    return [json.loads(line) for line in (INPUT/name).read_text(encoding='utf-8').splitlines() if line]

sources=read_jsonl('selected-sources.jsonl')
cells=read_jsonl('source-current-cells.jsonl')
contexts={x['sourceId']:x for x in read_jsonl('caller-contexts.jsonl')}
assert len(sources)==25 and len(cells)==300 and len(contexts)==25
source_by_id={s['sourceId']:s for s in sources}
assert set(INTENTS)=={s['continuationRank'] for s in sources}
assert set((s['continuationRank'],l) for s in sources for l in LOCALES)=={(c['continuationRank'],c['locale']) for c in cells}
rows=[]
for c in cells:
    rank=c['continuationRank']; loc=c['locale']; key=(rank,loc)
    src=source_by_id[c['sourceId']]; caller=contexts[c['sourceId']]
    assert c['source']==src['source'] and c['sourceSha256']==src['sourceSha256']
    assert c['sourceId']==caller['sourceId'] and c['source']==caller['source']
    assert sorted(ref['contextSha256'] for ref in c['callerRefs'])==sorted(call['contextSha256'] for call in caller['callers'])
    if key in FIXES:
        target,reason=FIXES[key]; decision='revise-current'
    else:
        target=c['currentTarget']; decision='retain-current'
        reason='Current target retained after checking the source intent against its production caller context; no concrete mistranslation was identified in this pass.'
    # Exact interpolation and syntax checks on each independent target.
    placeholders=lambda s: sorted(re.findall(r'\{[^{}]+\}',s))
    tags=lambda s: sorted(re.findall(r'</?[A-Za-z][^>]*>',s))
    assert placeholders(src['source'])==placeholders(target), (rank,loc,'placeholder mismatch')
    assert tags(src['source'])==tags(target), (rank,loc,'markup mismatch')
    assert c['numericTokensPreserved']
    if key in FIXES:
        # All pre-proposal revisions concern cells with no literal numeric source tokens.
        assert not c['sourceNumericTokens'], (rank,loc,'numeric revision needs re-review')
    if rank==917: assert 'ContentID' in target, (rank,loc,'ContentID')
    if rank==918: assert re.search(r'(?<![A-Za-z])B(?![A-Za-z])',target), (rank,loc,'field B')
    if rank==921:
        assert 'ID' in target and 'content:audio:album:mb-release-id' in target, (rank,loc,'ID/schema')
    if rank==927: assert 'SongID' in target, (rank,loc,'SongID')
    if rank==910:
        context_text='\n'.join(caller['callers'][0]['context'][i]['text'] for i in range(len(caller['callers'][0]['context'])))
        assert 'ed25519:&lt;base64 signature&gt;' in context_text
    rows.append({
      'continuationRank':rank,'remainingQueueRank':c['remainingQueueRank'],'sourceId':c['sourceId'],
      'source':src['source'],'sourceSha256':src['sourceSha256'],'locale':loc,
      'catalogPath':c['catalogPath'],'catalogKey':c['catalogKey'],'catalogFileSha256':c['catalogFileSha256'],
      'catalogGitBlob':c['catalogGitBlob'],'callerContextSha256':c['callerContextSha256'],
      'callerRefs':c['callerRefs'],'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],
      'independentDecision':decision,'independentTarget':target,'independentTargetSha256':hashlib.sha256(target.encode()).hexdigest(),
      'rationale':reason,'sourceIntent':INTENTS[rank],'confidence':'moderate',
      'sourcePlaceholderTokens':c['placeholderEvidence']['sourceTokens'],
      'currentPlaceholderTokens':c['placeholderEvidence']['currentTokens'],
      'sourceMarkupTags':c['markupEvidence']['sourceTags'],'currentMarkupTags':c['markupEvidence']['currentTags'],
      'sourceNumericTokens':c['sourceNumericTokens'],'currentNumericTokens':c['currentNumericTokens'],
      'sourceProtectedLiterals':c['sourceProtectedLiterals'],'currentProtectedLiterals':c['currentProtectedLiterals'],
      'independentProtectedAudit':{
        'ContentID':('ContentID' in target) if rank==917 else None,
        'fieldB':bool(re.search(r'(?<![A-Za-z])B(?![A-Za-z])',target)) if rank==918 else None,
        'ID':('ID' in target) if rank==921 else None,
        'schemaExample':('content:audio:album:mb-release-id' in target) if rank==921 else None,
        'SongID':('SongID' in target) if rank==927 else None,
        'inlineEd25519Caller':('ed25519:&lt;base64 signature&gt;' in '\n'.join(ctx['text'] for call in caller['callers'] for ctx in call['context'])) if rank==910 else None,
      },
      'independentBeforeProposalReview':True,
    })
rows.sort(key=lambda r:(r['continuationRank'],LOCALES.index(r['locale'])))
ledger=OUT/'independent-decisions.jsonl'
ledger.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
fix_count=sum(r['independentDecision']=='revise-current' for r in rows)
summary={
 'artifact':'slskdN PR #409 W903-W927 independent semantic pass',
 'phase':'sealed before opening primary or blind proposal contents',
 'repository':'snapetech-org/slskdN','pullRequest':409,'window':'W81',
 'head':'91da6fff5d5b628ade7ee556386e3db1db6878fa','tree':'56930b73d10a4c419edf68f0d951ceedaa63c990',
 'continuationRankRange':[903,927],'remainingQueueRankRange':[803,827],
 'candidateFreeInputManifestSha256':sha(INPUT/'manifest.json'),
 'candidateFreePacketChecksumListSha256':sha(INPUT/'PACKET-SHA256SUMS.txt'),
 'selectedSourcesSha256':sha(INPUT/'selected-sources.jsonl'),
 'sourceCurrentCellsSha256':sha(INPUT/'source-current-cells.jsonl'),
 'callerContextsSha256':sha(INPUT/'caller-contexts.jsonl'),
 'cellCount':len(rows),'independentRetainCurrent':len(rows)-fix_count,'independentReviseCurrent':fix_count,
 'independentHolds':0,'proposalContentsOpenedAtSealTime':False,
 'decisionCountsByRank':{str(rank):sum(r['continuationRank']==rank for r in rows) for rank in range(903,928)},
 'correctionCountsByRank':{str(rank):sum(r['continuationRank']==rank and r['independentDecision']=='revise-current' for r in rows) for rank in range(903,928)},
 'confidenceNote':'Moderate overall; this was an independent semantic review without native-speaker verification.',
 'ledgerSha256':sha(ledger),
}
(OUT/'independent-pass-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'PRE-PROPOSAL-SEAL.txt').write_text('Independent 300-cell decisions and targets were recorded and checksummed before opening either proposal packet.\nInput used: candidate-free packet only.\n',encoding='utf-8')
# Hash the three pre-proposal artifacts. Final cross-review artifacts will later replace this sum list.
for name in ['PRE-PROPOSAL-SEAL.txt','independent-decisions.jsonl','independent-pass-summary.json']:
    pass
(OUT/'PRE-PROPOSAL-SHA256SUMS.txt').write_text(''.join(f"{sha(OUT/name)}  {name}\n" for name in ['PRE-PROPOSAL-SEAL.txt','independent-decisions.jsonl','independent-pass-summary.json']),encoding='utf-8')
print(json.dumps({k:summary[k] for k in ['cellCount','independentRetainCurrent','independentReviseCurrent','independentHolds','ledgerSha256']},indent=2))
