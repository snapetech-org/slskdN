#!/usr/bin/env python3
"""Reconcile the sealed independent pass with primary and blind proposal packets."""
import collections, hashlib, json, re
from pathlib import Path

ROOT=Path('/home/keith/Documents/code/task-scratch/slskdn-pr409-w903-927-20261105')
INPUT=ROOT/'candidate-free'/'input'
PRIMARY=ROOT/'primary-review'/'output'
BLIND=ROOT/'blind-review'
OUT=ROOT/'cross-review'/'output'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

PREFER_PRIMARY={
 (903,'vi'),(907,'id'),(907,'pt-BR'),(918,'ar'),
 *((922,loc) for loc in LOCALES),
 *((923,loc) for loc in ['ar','es','fr','hi','ja','vi']),
 *((925,loc) for loc in ['de','hi','id']),
}
CUSTOM={
 (904,'id'):('Perbaikan untuk masalah yang bisa diperbaiki secara otomatis telah dimasukkan ke antrean: {count}.','The current Indonesian names a remediation queue rather than saying the remediation was queued. This states the queued action and preserves {count}.'),
 (921,'ar'):('معرّف المحتوى (ID، مثلًا: content:audio:album:mb-release-id)','Keep the required ASCII ID token and preserve the exact machine-readable sample identifier.'),
}
RATIONALE_OVERRIDES={
 **{(922,loc):'The supplied caller is in System/Security/AdversarialSettings.jsx and places Transport Status beside a signal icon. That supports a technical network/communication reading; this wording stays within that evidence and does not assume unseen panel values.' for loc in LOCALES},
 **{(925,loc):'The supplied caller passes {itemType} as a runtime value. This wording avoids attaching a fixed-gender article or particle to a value that may vary.' for loc in ['de','es','hi','ko','pt-BR']},
 (925,'id'):'The caller supplies {itemType} as a runtime value; putting ini after the item noun gives natural Indonesian word order while preserving the placeholder.',
}

class ReviewError(Exception): pass
def fail(msg): raise ReviewError(msg)
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha_bytes(p.read_bytes())
def canon(obj): return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def tree_hash(root):
    rec=[]
    for p in sorted(x for x in root.rglob('*') if x.is_file()):
        b=p.read_bytes(); rec.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':sha_bytes(b)})
    return sha_bytes(canon(rec))
def checksum_entries(path,root):
    res={}
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        digest,name=line.split('  ',1)
        if name in res: fail(f'duplicate checksum {name} in {path}')
        q=(root/name).resolve()
        if not q.is_relative_to(root.resolve()) or not q.is_file() or sha_file(q)!=digest: fail(f'checksum mismatch {q}')
        res[name]=digest
    return res
def text_hash(s): return sha_bytes(s.encode('utf-8'))
def tok(s,pat): return re.findall(pat,s)

# Confirm all input seals and exact packet identities before doing any row reconciliation.
input_manifest=readj(INPUT/'manifest.json')
primary_manifest=readj(PRIMARY/'manifest.json')
blind_manifest=readj(BLIND/'blind-review-manifest.json')
input_sums=checksum_entries(INPUT/'PACKET-SHA256SUMS.txt',INPUT)
primary_sums=checksum_entries(PRIMARY/'SHA256SUMS.txt',PRIMARY)
blind_sums=checksum_entries(BLIND/'SHA256SUMS.txt',BLIND)
if tree_hash(INPUT)!=blind_manifest['inputTreeSha256']: fail('candidate-free input tree hash mismatch')
if (sha_file(INPUT/'manifest.json'),sha_file(INPUT/'PACKET-SHA256SUMS.txt'))!=(primary_manifest['candidateFreeInputManifestSha256'],primary_manifest['candidateFreeInputChecksumListSha256']): fail('primary packet input hash binding')
if (sha_file(INPUT/'manifest.json'),sha_file(INPUT/'PACKET-SHA256SUMS.txt'))!=(blind_manifest['inputManifestSha256'],blind_manifest['inputChecksumFileSha256']): fail('blind packet input hash binding')
if (input_manifest['head'],input_manifest['tree'],input_manifest['cellCount'])!=(primary_manifest['head'],primary_manifest['tree'],primary_manifest['cellCount']): fail('primary head/tree/cell binding')
if (input_manifest['head'],input_manifest['tree'],input_manifest['cellCount'])!=(blind_manifest['head'],blind_manifest['tree'],blind_manifest['cellCount']): fail('blind head/tree/cell binding')
for key in ['sourceCurrentCellsSha256','callerContextSha256','selectionBoundarySha256','sourceInventorySelectionSha256']:
    inp_name={'sourceCurrentCellsSha256':'source-current-cells.jsonl','callerContextSha256':'caller-contexts.jsonl','selectionBoundarySha256':'selection-boundary.jsonl','sourceInventorySelectionSha256':'source-inventory-selection.jsonl'}[key]
    if sha_file(INPUT/inp_name)!=primary_manifest[key]: fail('primary '+key+' input hash binding')
if (input_manifest['head'],input_manifest['tree'])!=(blind_manifest['head'],blind_manifest['tree']): fail('blind head/tree identity')
if (input_manifest['continuationRankRange'],input_manifest['remainingQueueRankRange'])!=(blind_manifest['continuationRankRange'],blind_manifest['remainingQueueRankRange']): fail('blind rank range')

selected={x['sourceId']:x for x in rows(INPUT/'selected-sources.jsonl')}
input_cells=rows(INPUT/'source-current-cells.jsonl')
independent=rows(OUT/'independent-decisions.jsonl')
primary_rows=rows(PRIMARY/'primary-review.jsonl')
blind_rows=rows(BLIND/'blind-review-ledger.jsonl')
if not (len(input_cells)==len(independent)==len(primary_rows)==len(blind_rows)==300): fail('expected 300 rows in each full-cell packet')
key=lambda x:(x['continuationRank'],x['locale'])
keyset={(x['continuationRank'],x['locale']) for x in input_cells}
for label,data in [('independent',independent),('primary',primary_rows),('blind',blind_rows)]:
    if len({key(x) for x in data})!=300 or {key(x) for x in data}!=keyset: fail(label+' row coverage or duplicate mismatch')
I={key(x):x for x in input_cells}; D={key(x):x for x in independent}; P={key(x):x for x in primary_rows}; B={key(x):x for x in blind_rows}

# Validate every primary and blind record against the candidate-free cell, including hashes and refs.
for k,c in I.items():
    src=selected[c['sourceId']]
    expected={f:c[f] for f in ['sourceId','source','sourceSha256','locale','currentTarget','currentTargetSha256','callerContextSha256','callerRefs','catalogKey','catalogPath','catalogFileSha256','catalogGitBlob','continuationRank','remainingQueueRank']}
    for label,x in [('independent',D[k]),('primary',P[k]),('blind',B[k])]:
        for f,val in expected.items():
            if x.get(f)!=val: fail(f'{label} exact cell binding mismatch {k} field {f}')
        if text_hash(x['source'])!=x['sourceSha256'] or text_hash(x['currentTarget'])!=x['currentTargetSha256']: fail(f'{label} text hash mismatch {k}')
    if (P[k]['head'],P[k]['tree'])!=(input_manifest['head'],input_manifest['tree']): fail(f'primary head/tree row mismatch {k}')
    if (B[k]['head'],B[k]['tree'],B[k]['inputTreeSha256'])!=(input_manifest['head'],input_manifest['tree'],blind_manifest['inputTreeSha256']): fail(f'blind head/tree/input row mismatch {k}')
    if text_hash(D[k]['independentTarget'])!=D[k]['independentTargetSha256']: fail(f'independent target hash mismatch {k}')
    if B[k]['decision'] in ('correction','refinement'):
        if text_hash(B[k]['proposedTarget'])!=B[k].get('proposedTargetSha256'): fail(f'blind proposal hash mismatch {k}')
    elif 'proposedTarget' in B[k]: fail(f'unexpected blind target at {k}')
    if P[k]['disposition']=='correct':
        if text_hash(P[k]['target'])!=P[k].get('targetSha256'): fail(f'primary target hash mismatch {k}')
    elif 'target' in P[k]: fail(f'unexpected primary target at {k}')

# Ensure each primary map/correction row is identical to the row-level proposal source.
primary_proposal_map=readj(PRIMARY/'proposal-map.json')
expected_primary_map={f"{x['continuationRank']}|{x['locale']}":x['target'] for x in primary_rows if x['disposition']=='correct'}
if primary_proposal_map!=expected_primary_map: fail('primary proposal-map vs row ledger mismatch')
corrections=rows(PRIMARY/'corrections.jsonl')
if len(corrections)!=len(expected_primary_map): fail('primary corrections count mismatch')
correction_map={f"{x['continuationRank']}|{x['locale']}":x.get('target') for x in corrections}
if correction_map!=expected_primary_map: fail('primary corrections file target mismatch')
primary_hold_rows=rows(PRIMARY/'review-holds.jsonl')
if len(primary_hold_rows)!=12 or {key(x) for x in primary_hold_rows}!={k for k,x in P.items() if x['disposition']=='hold'}: fail('primary hold records mismatch')
if (PRIMARY/'holds-hash-only.jsonl').stat().st_size!=0: fail('unexpected primary hash-only holds')
if len(expected_primary_map)!=43: fail('primary proposal count expected 43')
if collections.Counter(x['disposition'] for x in primary_rows)!=collections.Counter({'accept-current':245,'correct':43,'hold':12}): fail('primary disposition counts')
if collections.Counter(x['decision'] for x in blind_rows)!=collections.Counter({'accept':239,'correction':26,'refinement':35,'hold':0}): fail('blind decision counts')
if blind_manifest['cellCount']!=300: fail('blind manifest cell count')

# Select final target text. The default is blind if proposed, else primary, else the sealed independent pass.
final={}; final_rationale={}; basis={}; final_kind={}; holds={}
for k,c in I.items():
    rank,loc=k
    if rank==910:
        final[k]=None; basis[k]='source-hold'; final_kind[k]='hold'
        final_rationale[k]='The phrase is split around inline ed25519 and a separately localized suffix. A fragment-only translation cannot reliably control word order or avoid duplicated/misplaced “format” wording; hold all locales pending a single rich-text sentence or markup-safe interpolation.'
        holds[k]=True
        continue
    if k in CUSTOM:
        target,why=CUSTOM[k]; source='cross-review'
    elif k in PREFER_PRIMARY and P[k]['disposition']=='correct':
        target=P[k]['target']; source='primary'
    elif B[k]['decision'] in ('correction','refinement'):
        target=B[k]['proposedTarget']; source='blind'
    elif P[k]['disposition']=='correct':
        target=P[k]['target']; source='primary'
    elif D[k]['independentDecision']=='revise-current':
        target=D[k]['independentTarget']; source='independent'
    else:
        target=c['currentTarget']; source='current'
    if source=='cross-review':
        why=why
    elif source=='independent':
        why=D[k]['rationale']
    elif source=='primary':
        why=P[k]['rationale']
    elif source=='blind':
        why=B[k]['rationale']
    else:
        why='Current target retained after independent review and proposal reconciliation; no proposal supplied a necessary change for this cell.'
    if k in RATIONALE_OVERRIDES: why=RATIONALE_OVERRIDES[k]
    final[k]=target; final_rationale[k]=why; basis[k]=source
    if target==c['currentTarget']:
        final_kind[k]='retain-current'
    else:
        d=P[k]['disposition']; bd=B[k]['decision']
        final_kind[k]='correct' if d=='correct' or bd=='correction' or D[k]['independentDecision']=='revise-current' else 'refinement'

# Check protected literals and source syntax on all final cells; rank 910 is held with no final target.
placeholder_pat=r'\{[^{}]+\}'; markup_pat=r'</?[A-Za-z][^>]*>'; numeric_pat=r'(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])'
output=[]
for k,c in I.items():
    rank,loc=k; p=P[k]; b=B[k]; d=D[k]; target=final[k]
    if target is not None:
        if sorted(tok(c['source'],placeholder_pat))!=sorted(tok(target,placeholder_pat)): fail(f'final placeholder mismatch {k}')
        if sorted(tok(c['source'],markup_pat))!=sorted(tok(target,markup_pat)): fail(f'final markup mismatch {k}')
        if not c['numericTokensPreserved']: fail(f'input numeric token baseline not preserved {k}')
        if target!=c['currentTarget'] and c['sourceNumericTokens']: fail(f'changed source-numeric cell requires review {k}')
    elif not c['numericTokensPreserved']: fail(f'held current numeric token baseline {k}')
    protected={
      905:['DHT'],907:['SongRec'],917:['ContentID','DHT'],918:['B'],919:['VPN'],
      921:['ID','content:audio:album:mb-release-id'],927:['SongID']
    }.get(rank,[])
    if target is not None:
        for literal in protected:
            if literal not in target: fail(f'final protected literal missing {literal} {k}')
    if rank==910:
        ctx=readj(INPUT/'manifest.json')
        # Exact inline token lives in the caller, not in the localizable fragment.
        call=next(x for x in rows(INPUT/'caller-contexts.jsonl') if x['sourceId']==c['sourceId'])
        if 'ed25519:&lt;base64 signature&gt;' not in '\n'.join(line['text'] for cr in call['callers'] for line in cr['context']): fail('rank 910 inline ed25519 context token missing')
    # Per-proposal audit result.
    if target is None:
        p_audit='accepted-hold' if p['disposition']=='hold' else ('held-pending-source-rewrite' if p['disposition']=='correct' else 'no-target-proposal')
        b_audit='held-pending-source-rewrite' if b['decision'] in ('correction','refinement') else 'no-target-proposal'
    else:
        p_audit=('no-target-proposal' if p['disposition']!='correct' else ('accepted-exact' if p['target']==target else 'accepted-alternative'))
        b_audit=('no-target-proposal' if b['decision'] not in ('correction','refinement') else ('accepted-exact' if b['proposedTarget']==target else 'accepted-alternative'))
    row={
      'continuationRank':rank,'remainingQueueRank':c['remainingQueueRank'],'sourceId':c['sourceId'],'source':c['source'],'sourceSha256':c['sourceSha256'],
      'locale':loc,'head':input_manifest['head'],'tree':input_manifest['tree'],
      'catalogKey':c['catalogKey'],'catalogPath':c['catalogPath'],'catalogFileSha256':c['catalogFileSha256'],'catalogGitBlob':c['catalogGitBlob'],
      'callerContextSha256':c['callerContextSha256'],'callerRefs':c['callerRefs'],
      'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],
      'independentDecision':d['independentDecision'],'independentTarget':d['independentTarget'],'independentTargetSha256':d['independentTargetSha256'],
      'independentRationale':d['rationale'],'independentConfidence':d['confidence'],
      'primaryDisposition':p['disposition'],'primaryProposalTarget':p.get('target'),'primaryProposalTargetSha256':p.get('targetSha256'),
      'primaryRationale':p['rationale'],'primaryAudit':p_audit,
      'blindDecision':b['decision'],'blindProposalTarget':b.get('proposedTarget'),'blindProposalTargetSha256':b.get('proposedTargetSha256'),
      'blindRationale':b['rationale'],'blindAudit':b_audit,
      'finalDecision':final_kind[k],'finalTarget':target,'finalTargetSha256':text_hash(target) if target is not None else None,
      'finalBasis':basis[k],'finalRationale':final_rationale[k],
      'sourceRewriteRecommendationId':'SR-910-01' if rank==910 else None,
      'protectedLiteralAudit':{
        'ContentID':('ContentID' in target) if rank==917 and target is not None else None,
        'DHT':('DHT' in target) if rank in (905,917) and target is not None else None,
        'fieldB':bool(re.search(r'(?<![A-Za-z])B(?![A-Za-z])',target)) if rank==918 and target is not None else None,
        'ID':('ID' in target) if rank==921 and target is not None else None,
        'schemaExample':('content:audio:album:mb-release-id' in target) if rank==921 and target is not None else None,
        'SongRec':('SongRec' in target) if rank==907 and target is not None else None,
        'SongID':('SongID' in target) if rank==927 and target is not None else None,
        'VPN':('VPN' in target) if rank==919 and target is not None else None,
        'inlineEd25519Caller':'ed25519:&lt;base64 signature&gt;' if rank==910 else None,
        'placeholderParity':sorted(tok(c['source'],placeholder_pat))==sorted(tok(target,placeholder_pat)) if target is not None else c['placeholderEvidence']['matches'],
        'markupParity':sorted(tok(c['source'],markup_pat))==sorted(tok(target,markup_pat)) if target is not None else c['markupEvidence']['matches'],
        'numericTokensPreserved':c['numericTokensPreserved'],
      },
    }
    output.append(row)
output.sort(key=lambda r:(r['continuationRank'],LOCALES.index(r['locale'])))
ledger=OUT/'cross-review-ledger.jsonl'
ledger.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in output),encoding='utf-8')

# Audit rank-922 rationale scope: do not repeat unshown panel details as independently verified facts.
r922path=next(ref['path'] for c in input_cells if c['continuationRank']==922 for ref in c['callerRefs'])
manifest_summary={
 'artifact':'slskdN PR #409 W903-W927 sealed cross-review',
 'repository':'snapetech-org/slskdN','pullRequest':409,'window':'W81',
 'head':input_manifest['head'],'tree':input_manifest['tree'],
 'continuationRankRange':[903,927],'remainingQueueRankRange':[803,827],
 'candidateFreeManifestSha256':sha_file(INPUT/'manifest.json'),
 'candidateFreeChecksumListSha256':sha_file(INPUT/'PACKET-SHA256SUMS.txt'),
 'candidateFreeInputTreeSha256':tree_hash(INPUT),
 'sourceCurrentCellsSha256':sha_file(INPUT/'source-current-cells.jsonl'),
 'callerContextsSha256':sha_file(INPUT/'caller-contexts.jsonl'),
 'selectedSourcesSha256':sha_file(INPUT/'selected-sources.jsonl'),
 'primaryManifestSha256':sha_file(PRIMARY/'manifest.json'),
 'primaryChecksumListSha256':sha_file(PRIMARY/'SHA256SUMS.txt'),
 'primaryReviewLedgerSha256':sha_file(PRIMARY/'primary-review.jsonl'),
 'primaryProposalMapSha256':sha_file(PRIMARY/'proposal-map.json'),
 'primarySummarySha256':sha_file(PRIMARY/'summary.json'),
 'blindManifestSha256':sha_file(BLIND/'blind-review-manifest.json'),
 'blindChecksumListSha256':sha_file(BLIND/'SHA256SUMS.txt'),
 'blindReviewLedgerSha256':sha_file(BLIND/'blind-review-ledger.jsonl'),
 'blindInputTreeSha256':blind_manifest['inputTreeSha256'],
 'independentLedgerSha256':sha_file(OUT/'independent-decisions.jsonl'),
 'independentPassSummarySha256':sha_file(OUT/'independent-pass-summary.json'),
 'independentPreProposalSealSha256':sha_file(OUT/'PRE-PROPOSAL-SEAL.txt'),
 'independentPreProposalChecksumListSha256':sha_file(OUT/'PRE-PROPOSAL-SHA256SUMS.txt'),
 'cellCount':len(output),
 'primaryCounts':{'accept-current':245,'correct':43,'hold':12},
 'blindCounts':{'accept':239,'correction':26,'refinement':35,'hold':0},
 'independentCounts':{'retain-current':276,'revise-current':24,'hold':0},
 'finalCounts':dict(collections.Counter(r['finalDecision'] for r in output)),
 'proposalAuditCounts':{
   'primary':dict(collections.Counter(r['primaryAudit'] for r in output)),
   'blind':dict(collections.Counter(r['blindAudit'] for r in output)),
 },
 'baselineTokenMismatchSummary':readj(INPUT/'baseline-token-mismatch-summary.json'),
 'additionalProtectedLiteralFindings':[
   'rank 918: Latin B field identifier translated in ar and hi',
   'rank 921: literal sample content:audio:album:mb-release-id localized or reformatted in es, hi, id, zh-Hans, zh-Hant',
   'rank 927: SongID transliterated in hi',
 ],
 'rank921ProtectedIdCells':['ar','hi'],
 'rank910Disposition':'hold all 12 pending source rewrite; preserve inline ed25519 code in caller',
 'sourceRewriteRecommendation':{
   'id':'SR-910-01','implemented':False,'acceptedAsDesignRecommendation':True,
   'summary':'Combine the sentence into one translatable rich-text message with the signature format as a markup-safe code interpolation so locales can reorder it.'
 },
 'rank922EvidenceScope':{
   'pinnedCallerPath':r922path,
   'acceptedInterpretation':'network transport, based on the pinned System/Security/AdversarialSettings.jsx path and signal-icon header',
   'note':'The primary rationale also names Tor/I2P/direct/failover panel values; those details are not present in the candidate-free six-line caller excerpt or primary supplemental context pins, so this cross-review does not claim to have independently verified them.'
 },
 'nativeSpeakerSignoff':False,'browserReview':False,'repositoryOrWorktreeInspected':False,'prBodyInspected':False,'externalSourcesUsed':False,
 'rationaleNote':'Every cell carries independent, primary, blind, and final rationales; proposals are logged with exact target hashes and audit outcomes.',
 'crossReviewLedgerSha256':sha_file(ledger),
}
(OUT/'proposal-reconciliation-summary.json').write_text(json.dumps(manifest_summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
process_note=(
 'Process exposure note\n'
 'Before the independent pass was sealed, a filesystem inventory listed filenames and byte sizes in all three supplied packet directories. This exposed the proposal packet filenames and artifact types, but no primary or blind file contents were opened. The independent 300-cell ledger and its pre-proposal SHA-256 seal were written before either proposal packet was opened.\n'
 'The first checksum command was run from the workspace root against a relative-name checksum list and returned missing-file errors; it read no proposal content. Re-running from the candidate-free input directory verified all listed packet files. Primary and blind checksums were verified after the pre-proposal seal. The blind portable verifier passed all 300 rows.\n'
 'No repository/worktree, PR body, browser/native-speaker review, other review windows, or external sources/search were accessed. No catalogs, PR state, or source files were edited. The rank-922 proposal rationale includes panel-value details not present in the supplied caller excerpt; this cross-review uses only the pinned path and signal-icon header to support the network reading and flags the extra detail as unverified.\n'
)
(OUT/'process-exposure.txt').write_text(process_note,encoding='utf-8')

# Cross-review manifest and SHA256SUMS seal every deliverable except the checksum list itself.
files=[]
for p in sorted(x for x in OUT.iterdir() if x.is_file() and x.name not in {'cross-review-manifest.json','SHA256SUMS.txt'}):
    b=p.read_bytes(); files.append({'path':p.name,'bytes':len(b),'sha256':sha_bytes(b)})
manifest={
 'artifact':'slskdN PR #409 W903-W927 cross-review output seal','schemaVersion':1,
 'head':input_manifest['head'],'tree':input_manifest['tree'],
 'candidateFreeManifestSha256':sha_file(INPUT/'manifest.json'),
 'primaryManifestSha256':sha_file(PRIMARY/'manifest.json'),
 'blindManifestSha256':sha_file(BLIND/'blind-review-manifest.json'),
 'independentLedgerSha256':sha_file(OUT/'independent-decisions.jsonl'),
 'crossReviewLedgerSha256':sha_file(ledger),
 'cellCount':len(output),'finalCounts':manifest_summary['finalCounts'],
 'files':files,
}
(OUT/'cross-review-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
checks=[]
for p in sorted(x for x in OUT.iterdir() if x.is_file() and x.name!='SHA256SUMS.txt'):
    checks.append(f'{sha_file(p)}  {p.name}\n')
(OUT/'SHA256SUMS.txt').write_text(''.join(checks),encoding='utf-8')
print(json.dumps({'result':'BUILT','cells':len(output),'finalCounts':manifest_summary['finalCounts'],'primaryAuditCounts':manifest_summary['proposalAuditCounts']['primary'],'blindAuditCounts':manifest_summary['proposalAuditCounts']['blind'],'ledgerSha256':manifest['crossReviewLedgerSha256'],'output':str(OUT)},ensure_ascii=False,indent=2))
