from __future__ import annotations
import json,hashlib,pathlib,subprocess,re,collections
from datetime import datetime,timezone
OUT=pathlib.Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window44-crossreview-20261102')
PRIMARY=pathlib.Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window44-primary-reconstructed-20261102')
WORK=pathlib.Path('/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn')
HEAD='f3fbd3f8db10f78768b9951a67b4b9de8581a408'; TREE='9495c35a540ef2d2e845c833acb709365e0e26ac'
REPOS=[('SeerrNG',418),('ChaptarrNG',190),('QuestarrNG',155),('ROMarrNG',70),('slskR',204),('slskdN',409),('TorrentNG',243)]
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def jbytes(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def git(*a): return subprocess.check_output(['git','-C',str(WORK),*a])
def readjl(path): return [json.loads(x) for x in pathlib.Path(path).read_text().splitlines()]
def placeholders(s): return sorted(set(re.findall(r'\{[^{}]+\}|%\d*\$?[sdif]|\$\{[^}]+\}',s)))
def markup(s):
    if re.fullmatch(r'<[^<>/]+>',s): return []
    return re.findall(r'</?[A-Za-z][^>]*>',s)
def query_live():
    rows=[]
    for repo,n in REPOS:
        pr=json.loads(subprocess.check_output(['gh','pr','view',str(n),'--repo',f'snapetech-org/{repo}','--json','number,state,isDraft,headRefName,headRefOid,baseRefName,baseRefOid,url'],text=True))
        tree=json.loads(subprocess.check_output(['gh','api',f"repos/snapetech-org/{repo}/git/commits/{pr['headRefOid']}"],text=True))['tree']['sha']
        row={'repository':f'snapetech-org/{repo}',**pr,'headTree':tree}
        if n==409: row['remoteBranchOid']=subprocess.check_output(['git','ls-remote','https://github.com/snapetech-org/slskdN.git',f"refs/heads/{pr['headRefName']}"],text=True).split()[0]
        rows.append(row)
    return rows
def verify_sumfile(path,cwd):
    r=subprocess.run(['sha256sum','-c',str(path)],cwd=cwd,text=True,capture_output=True)
    assert r.returncode==0,r.stdout+r.stderr
    return len(r.stdout.splitlines())
def verify_ref(ref, expected_source=None):
    path=ref['path']; raw=git('show',f'{HEAD}:{path}'); lines=raw.decode().splitlines(); n=ref['line']
    actual=lines[n-1] if 1<=n<=len(lines) else None
    return {
      'path':path,'line':n,'lineTextMatches':actual is not None and actual==ref['lineText'],
      'lineSha256Matches':actual is not None and sha(actual)==ref['lineSha256'],
      'fileBlobOidMatches':git('rev-parse',f'{HEAD}:{path}').decode().strip()==ref['blobOid'],
      'fileSha256Matches':sha(raw)==ref['fileSha256'],
      'contextBeforeMatches':actual is not None and [v.strip() for v in lines[max(0,n-1-len(ref['contextBefore'])):n-1]]==[v.strip() for v in ref['contextBefore']],
      'contextAfterMatches':actual is not None and [v.strip() for v in lines[n:min(len(lines),n+len(ref['contextAfter']))]]==[v.strip() for v in ref['contextAfter']],
      'verifiedAtCurrentHead':ref.get('verifiedAtCurrentHead') is True,
      'referenceRole':ref.get('referenceRole'),
      'exactSourceLiteralMatch':ref.get('exactSourceLiteralMatch'),
      'expectedSourceMatches':expected_source is None or ref.get('source')==expected_source,
    }
# Fresh live query and exact worktree state before readback.
start_live=query_live(); live409=next(x for x in start_live if x['number']==409)
assert live409['state']=='OPEN' and live409['isDraft'] is True and live409['headRefOid']==HEAD and live409['headTree']==TREE and live409['remoteBranchOid']==HEAD
assert git('rev-parse','HEAD').decode().strip()==HEAD and git('rev-parse','HEAD^{tree}').decode().strip()==TREE
assert git('status','--porcelain').decode().strip()==''
assert git('branch','--show-current').decode().strip()=='codex/slskdn-localization-apply-20261102'
# Verify primary evidence checksums and its selected input/head pins.
primary_sum_rows=verify_sumfile(PRIMARY/'SHA256SUMS.txt',PRIMARY)
manifest_sha=sha((PRIMARY/'SHA256SUMS.txt').read_bytes())
summary=json.loads((PRIMARY/'summary.json').read_text()); structure=json.loads((PRIMARY/'catalog-structure.json').read_text())
assert summary['head']==HEAD and summary['tree']==TREE and summary['cells']==300
assert structure['head']==HEAD and structure['tree']==TREE and structure['sourceKeyCountPerLocale']==6170
# Load catalogs from the exact live tree, preserving ordered source keys and exact target values.
catalogs={}; catalog_pins={}; ordered_keys=None
for c in structure['catalogs']:
    loc=c['locale']; path=c['path']; raw=git('show',f'{HEAD}:{path}'); obj=json.loads(raw)
    keys=list(obj)
    if ordered_keys is None: ordered_keys=keys
    assert keys==ordered_keys,(loc,'ordered source-key inventory mismatch')
    assert len(obj)==6170 and c['entryCount']==6170 and sha(raw)==c['fileSha256']
    assert git('rev-parse',f'{HEAD}:{path}').decode().strip()==c['blobOid']
    catalogs[loc]=obj; catalog_pins[loc]={'path':path,'blobOid':c['blobOid'],'fileSha256':c['fileSha256'],'bytes':len(raw)}
assert set(catalogs)==set(LOCALES)
assert sha(json.dumps(ordered_keys,ensure_ascii=False,separators=(',',':')))==structure['orderedKeyInventorySha256']
assert git('rev-parse',f'{HEAD}:src/web/public/locales').decode().strip()==structure['localeCatalogSubtreeTree']
assert git('rev-parse',f'{HEAD}:src/web/src').decode().strip()==structure['sourceSubtreeTree']
# Rebuild every source key id and the pending selection from all 12 catalogs and W1-W43 exclusions.
source_by={f"src_{sha(k)[:16]}":k for k in ordered_keys}
assert len(source_by)==6170 and sha(json.dumps(sorted(source_by),separators=(',',':')))==structure['sourceIdInventorySha256']
source_inventory=readjl(PRIMARY/'source-inventory.jsonl'); prior=readjl(PRIMARY/'prior-source-ids.jsonl'); selected=readjl(PRIMARY/'pending-source-selection.jsonl')
assert len(source_inventory)==6170 and len(prior)==1072 and len({x['sourceId'] for x in prior})==1072
assert len(selected)==25
for row in source_inventory:
    assert source_by.get(row['sourceId'])==row['source'] and row['sourceId']==f"src_{sha(row['source'])[:16]}" and row['sourceSha256']==sha(row['source'])
prior_ids={x['sourceId'] for x in prior}
for row in prior:
    assert source_by.get(row['sourceId'])==row['source'] and row['sourceSha256']==sha(row['source']) and row['presentInCurrentInventory'] is True and row['sourceIdRecheckedAgainstCurrentKey'] is True
pending=sorted(set(source_by)-prior_ids)
assert len(pending)==5098
for rank,row in enumerate(selected,1):
    sid=pending[rank-1]
    assert row['selectionRank']==rank and row['sourceId']==sid and row['source']==source_by[sid] and row['sourceSha256']==sha(row['source']) and row['sourceOrdinal'] is None
# Read primary decisions/candidates/callers and verify the caller pins at exact source lines.
primary_rows=readjl(PRIMARY/'review-decisions.jsonl'); candidates=readjl(PRIMARY/'candidate-proposals.jsonl'); caller_rows=readjl(PRIMARY/'caller-context.jsonl')
gaps=readjl(PRIMARY/'source-runtime-gaps.jsonl'); spanish=readjl(PRIMARY/'spanish-formal-applicability.jsonl')
assert len(primary_rows)==300 and len(candidates)==31 and len(caller_rows)==25 and len(spanish)==25
pmap={(x['selectionRank'],x['locale']):x for x in primary_rows}; assert len(pmap)==300
cmap={x['sourceId']:x for x in caller_rows}; assert len(cmap)==25
candmap={(x['selectionRank'],x['locale']):x for x in candidates}; assert len(candmap)==31
caller_checks={}; caller_failures=[]
for sid,c in cmap.items():
    assert source_by[sid]==c['source'] and c['sourceSha256']==sha(c['source']) and c['callerReferenceCount']==len(c['callerRefs'])
    for ref in c['callerRefs']:
        check=verify_ref(ref,expected_source=c['source'] if ref.get('exactSourceLiteralMatch') else None)
        caller_checks.setdefault(sid,[]).append(check)
        if not all(check[k] for k in ('lineTextMatches','lineSha256Matches','fileBlobOidMatches','fileSha256Matches','contextBeforeMatches','contextAfterMatches','verifiedAtCurrentHead','expectedSourceMatches')):
            caller_failures.append({'sourceId':sid,'ref':ref,'check':check})
assert not caller_failures,caller_failures[:3]
# Two W44 caller gaps are independently confirmed; the old W98 hold is kept separate.
gap_by={x['sourceId']:x for x in gaps}
assert {x['selectionRank'] for x in selected if x['sourceId'] in gap_by}=={12,21}
for r in primary_rows:
    if r['disposition']=='hold':
        gap=gap_by[r['sourceId']]
        assert gap['affectedCells']==12 and gap['callerUseStatus'] in ('feature-gate-only-no-production-display-caller','test-only-reference-no-production-caller')
        assert r['reviewedTarget'] is None
# Main independent proposals found during complete 300-cell language scan.
ADDITIONAL={
 (2,'ar'):('سجل التنزيلات محدود','propose-additional-correction','Arabic for limited download history should name the download log/history (سجل التنزيلات). تاريخ التحميل can read as a download date, and this reason is explicitly about historical downloads. The caller uses it as a search-ranking reason label.'),
 (17,'ar'):('يشير عرض النطاق الطيفي البالغ {bandwidth}kHz إلى مصدر صوتي مضغوط بفقدان البيانات بمعدل {bitrate}kbps.','propose-additional-correction','مصدر فاقد is unclear as a rendering of a lossy audio source and can read as a source that is missing. The caller reports an audio spectral signature; this names a lossy-compressed audio source and preserves the bitrate and bandwidth values.'),
 (23,'id'):('Bukti: {evidence}','propose-additional-refinement','The setup health check prints evidence from each check. The current Keterangan means general information/details, while the same catalog maps Evidence to Bukti, No evidence supplied to Tidak ada bukti, and evidence item to item bukti.'),
 (23,'pt-BR'):('Evidência: {evidence}','propose-additional-refinement','The setup health check prints evidence from each check. The current Prova is less consistent with this catalog, which maps Evidence to Evidência, No evidence supplied to Nenhuma evidência, and evidence item to item de evidência.'),
}
rows=[]; structural=[]; counts=collections.Counter(); noops=[]; failures=[]
for (rank,loc),p in sorted(pmap.items()):
    sid=p['sourceId']; src=source_by[sid]; current=catalogs[loc][src]; target_file=catalog_pins[loc]
    assert p['sourceOrdinal'] is None and p['selectionRank']==rank and selected[rank-1]['sourceId']==sid
    assert p['sourceText']==src and p['catalogKey']==src and p['sourceSha256']==sha(src)
    assert p['catalogPath']==target_file['path'] and p['catalogBlobOid']==target_file['blobOid'] and p['catalogFileSha256']==target_file['fileSha256']
    assert p['currentTarget']==current and p['currentTargetSha256']==sha(current)
    assert p['callerRefsSourceId']==sid and p['callerUseStatus']==cmap[sid]['callerUseStatus']
    source_ph=placeholders(src); current_ph=placeholders(current); source_m=markup(src); current_m=markup(current)
    final=None; disp=None; rationale=None; new_type=None
    if p['disposition']=='hold':
        disp='retain-hold'; rationale=p['rationale']
    elif (rank,loc) in ADDITIONAL:
        final,disp,rationale=ADDITIONAL[(rank,loc)]
        assert final!=current
        new_type='correction' if disp.endswith('correction') else 'refinement'
    elif p['disposition']=='accept-current':
        final=current; disp='accept-current'; rationale='Current target retained after independent source, caller, catalog, placeholder, markup, literal, and semantic review.'
    elif p['disposition'] in ('propose-correction','propose-refinement'):
        q=candmap[(rank,loc)]
        assert q['proposedTarget']==p['reviewedTarget'] and q['proposedTargetSha256']==p['reviewedTargetSha256']==sha(p['reviewedTarget'])
        assert q['currentTarget']==current and q['currentTargetSha256']==sha(current)
        assert p['reviewedTarget']!=current
        final=p['reviewedTarget']
        disp='accept-primary-correction' if p['disposition']=='propose-correction' else 'accept-primary-refinement'
        rationale='Accepted the exact primary candidate after independent context and language review.'
    else: raise AssertionError((rank,loc,p['disposition']))
    protected=list(p['protectedLiterals'])
    current_protected_bad=[v for v in protected if v not in current]
    assert p['currentPlaceholderParity']=='exact' and p['currentMarkupParity']=='exact'
    assert placeholders(current)==source_ph and markup(current)==source_m
    assert p['currentProtectedLiteralMismatches']==current_protected_bad
    assert not current_protected_bad,(rank,loc,current_protected_bad,current)
    checked_target=final if final is not None else current
    if final is not None:
        assert placeholders(final)==source_ph and markup(final)==source_m
        final_hash=sha(final)
    else: final_hash=None
    protected_bad=[v for v in protected if v not in checked_target]
    assert not protected_bad,(rank,loc,protected_bad,checked_target)
    if p['disposition'] in ('propose-correction','propose-refinement') and p['reviewedTarget']==current: noops.append((rank,loc))
    refs=cmap[sid]['callerRefs']; caller_ctx_hash=sha(jbytes(refs))
    assert all(x['sourceId']==sid for x in refs)
    cross={
      'exactHead':HEAD,'exactTree':TREE,'sourceOrdinal':None,'selectionRank':rank,'sourceId':sid,'locale':loc,'source':src,'sourceSha256':sha(src),
      'selectionBasis':'first 25 lexicographically sorted source IDs pending after W1-W43 exclusion; historical ordinal not established',
      'catalogPath':target_file['path'],'catalogBlobOid':target_file['blobOid'],'catalogFileSha256':target_file['fileSha256'],
      'currentTarget':current,'currentTargetSha256':sha(current),'primaryDisposition':p['disposition'],'primaryTarget':p['reviewedTarget'],'primaryTargetSha256':p['reviewedTargetSha256'],
      'crossReviewDisposition':disp,'crossReviewFinalTarget':final,'crossReviewFinalTargetSha256':final_hash,'crossReviewRationale':rationale,'confidence':'moderate',
      'sourcePlaceholders':source_ph,'currentTargetPlaceholders':current_ph,'finalPlaceholders':placeholders(final) if final is not None else None,
      'sourceMarkup':source_m,'currentTargetMarkup':current_m,'finalMarkup':markup(final) if final is not None else None,
      'protectedLiterals':protected,'currentProtectedLiteralsPreserved':not current_protected_bad,'protectedLiteralsPreserved':not protected_bad,
      'callerUseStatus':p['callerUseStatus'],'callerContextSummary':p['callerContextSummary'],'callerRefsSourceId':p['callerRefsSourceId'],
      'callerRefs':refs,'callerRefsSha256':caller_ctx_hash,'callerRefChecks':caller_checks[sid],
      'spanishFormalApplicability':p['spanishFormalApplicability'],'nativeSpeakerApproval':False,'browserReview':False,
    }
    rows.append(cross); counts[disp]+=1
    struct={
      'exactHead':HEAD,'exactTree':TREE,'selectionRank':rank,'sourceId':sid,'locale':loc,'sourceSha256':sha(src),'currentTargetSha256':sha(current),
      'catalogPath':target_file['path'],'catalogBlobOid':target_file['blobOid'],'catalogFileSha256':target_file['fileSha256'],
      'sourceKeyIdentity':sid==f"src_{sha(src)[:16]}",'sourceSelectionMatches':selected[rank-1]['source']==src and selected[rank-1]['sourceId']==sid,
      'currentValueHashMatches':p['currentTarget']==current and p['currentTargetSha256']==sha(current),
      'currentPlaceholderParity':placeholders(current)==source_ph and p['currentPlaceholderParity']=='exact',
      'currentMarkupParity':markup(current)==source_m and p['currentMarkupParity']=='exact',
      'currentProtectedLiteralParity':not current_protected_bad,
      'callerSourcePinMatches':p['callerRefsSourceId']==sid and p['callerUseStatus']==cmap[sid]['callerUseStatus'],
      'callerRefsHash':caller_ctx_hash,'callerReferencesVerified':all(all(ch[k] for k in ('lineTextMatches','lineSha256Matches','fileBlobOidMatches','fileSha256Matches','contextBeforeMatches','contextAfterMatches','verifiedAtCurrentHead','expectedSourceMatches')) for ch in caller_checks[sid]),
      'sourcePlaceholders':source_ph,'currentPlaceholders':current_ph,'finalPlaceholders':placeholders(final) if final is not None else None,
      'sourceMarkup':source_m,'currentMarkup':current_m,'finalMarkup':markup(final) if final is not None else None,
      'placeholderParity':placeholders(checked_target)==source_ph,'markupParity':markup(checked_target)==source_m,
      'protectedLiterals':protected,'currentProtectedLiteralsPreserved':not current_protected_bad,'protectedLiteralsPreserved':not protected_bad,
      'primaryDisposition':p['disposition'],'crossReviewDisposition':disp,'finalTargetSha256':final_hash,
    }
    bad=[k for k,v in struct.items() if k in ('sourceKeyIdentity','sourceSelectionMatches','currentValueHashMatches','currentPlaceholderParity','currentMarkupParity','currentProtectedLiteralParity','callerSourcePinMatches','callerReferencesVerified','placeholderParity','markupParity','protectedLiteralsPreserved') and v is not True]
    if bad: failures.append({'rank':rank,'locale':loc,'failedChecks':bad})
    structural.append(struct)
assert not failures,failures[:5]
assert not noops,noops
assert len(rows)==len(structural)==300
assert counts=={'accept-current':241,'accept-primary-correction':15,'accept-primary-refinement':16,'propose-additional-correction':2,'propose-additional-refinement':2,'retain-hold':24},counts
assert all(r['sourceOrdinal'] is None and r['selectionRank']==selected[r['selectionRank']-1]['selectionRank'] for r in rows)
assert all(r['selectionRank'] in (12,21) for r in rows if r['crossReviewDisposition']=='retain-hold')
# Validate Spanish direct-address assessment independently for the selected 25 IDs.
spanish_map={x['selectionRank']:x for x in spanish}; assert len(spanish_map)==25
for r in rows:
    s=spanish_map[r['selectionRank']]
    assert s['sourceId']==r['sourceId'] and s['englishDirectAddressForms']==[] and not s['formalLaneAccumulatorCellPresent']
    assert s['currentSpanishTarget']==catalogs['es'][r['source']] and s['currentSpanishTargetSha256']==sha(s['currentSpanishTarget'])
# Reattest prior W98 held values/caller composition at current head, keeping these separate from W44.
w98=readjl(PRIMARY/'w98-holds-reattestation.jsonl'); assert len(w98)==11
w98_readback=[]; w98_fails=[]
for r in w98:
    loc=r['locale']; src=r['source']; value=catalogs[loc][src]; checks=[]
    for ref in r['currentCallerRefs']: checks.append(verify_ref(ref))
    check={'currentValueMatches':value==r['currentTarget'] and sha(value)==r['currentTargetSha256']==r['w43TargetSha256'],
      'catalogPinMatches':r['catalogPath']==catalog_pins[loc]['path'] and r['catalogBlobOid']==catalog_pins[loc]['blobOid'] and r['catalogFileSha256']==catalog_pins[loc]['fileSha256'],
      'sourceIdentityMatches':r['sourceId']==f"src_{sha(src)[:16]}" and r['sourceSha256']==sha(src),
      'callerRefsVerified':all(all(c[k] for k in ('lineTextMatches','lineSha256Matches','fileBlobOidMatches','fileSha256Matches','contextBeforeMatches','contextAfterMatches','verifiedAtCurrentHead')) for c in checks),
      'holdStillOutstanding':r['disposition']=='preserve-existing-hold' and r['outstandingHold'] is True and r['newW44SliceMember'] is False}
    if not all(check.values()): w98_fails.append({'rank':r.get('sourceOrdinal'),'locale':loc,'checks':check})
    w98_readback.append({'exactHead':HEAD,'exactTree':TREE,'sourceOrdinal':98,'sourceId':r['sourceId'],'locale':loc,'source':src,'sourceSha256':sha(src),'currentTarget':value,'currentTargetSha256':sha(value),'priorDisposition':r['disposition'],'reason':r['reason'],'currentCallerRefs':r['currentCallerRefs'],'callerChecks':checks,'checks':check})
assert not w98_fails,w98_fails[:3]
# Confirm the W44 source/caller gaps still have no production translation caller.
gap_summary=[]
for sid in (selected[11]['sourceId'],selected[20]['sourceId']):
    g=gap_by[sid]
    gap_summary.append({'sourceId':sid,'source':g['source'],'callerUseStatus':g['callerUseStatus'],'reason':g['gap'],'affectedCells':g['affectedCells'],'heldCells':sum(x['sourceId']==sid and x['crossReviewDisposition']=='retain-hold' for x in rows)})
assert len(w98_readback)==11 and all(x['checks']['holdStillOutstanding'] for x in w98_readback)
# Write exact row ledgers and findings.
(OUT/'cross-review-ledger.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rows))
(OUT/'structural-caller-reattestation.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in structural))
(OUT/'w98-holds-reattestation.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in w98_readback))
extra=[]
for (rank,loc),(target,disp,why) in ADDITIONAL.items():
    p=pmap[(rank,loc)]; src=p['sourceText']; sid=p['sourceId']; cur=p['currentTarget']; loccat=catalog_pins[loc]; refs=cmap[sid]['callerRefs']
    extra.append({'exactHead':HEAD,'exactTree':TREE,'sourceOrdinal':None,'selectionRank':rank,'sourceId':sid,'locale':loc,'source':src,'sourceSha256':sha(src),'currentTarget':cur,'currentTargetSha256':sha(cur),'recommendedTarget':target,'recommendedTargetSha256':sha(target),'disposition':disp,'rationale':why,'confidence':'moderate','catalogPath':loccat['path'],'catalogBlobOid':loccat['blobOid'],'catalogFileSha256':loccat['fileSha256'],'callerUseStatus':p['callerUseStatus'],'callerContextSummary':p['callerContextSummary'],'callerRefs':refs,'callerRefsSha256':sha(jbytes(refs)),'placeholdersPreserved':placeholders(src)==placeholders(target),'sourcePlaceholders':placeholders(src),'recommendedPlaceholders':placeholders(target),'sourceMarkup':markup(src),'recommendedMarkup':markup(target),'markupPreserved':markup(src)==markup(target),'protectedLiterals':p['protectedLiterals'],'protectedLiteralsPreserved':all(v in target for v in p['protectedLiterals']),'nativeSpeakerApproval':False})
(OUT/'additional-findings.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in extra))
# Fresh live query at end and worktree check before sealing.
end_live=query_live(); end409=next(x for x in end_live if x['number']==409)
assert end409['state']=='OPEN' and end409['isDraft'] is True and end409['headRefOid']==HEAD and end409['headTree']==TREE and end409['remoteBranchOid']==HEAD
assert git('rev-parse','HEAD').decode().strip()==HEAD and git('rev-parse','HEAD^{tree}').decode().strip()==TREE and git('status','--porcelain').decode().strip()==''
assert [(x['number'],x['headRefOid'],x['headTree']) for x in start_live]==[(x['number'],x['headRefOid'],x['headTree']) for x in end_live]
now=datetime.now(timezone.utc).isoformat()
for name,prs in [('live-seven-pr-heads-start.json',start_live),('live-seven-pr-heads-final.json',end_live)]:
 (OUT/name).write_text(json.dumps({'capturedAtUtc':now,'pullRequests':prs},ensure_ascii=False,indent=2,sort_keys=True)+'\n')
selection={'capturedAtUtc':now,'exactHead':HEAD,'exactTree':TREE,'catalogSubtreeTree':structure['localeCatalogSubtreeTree'],'sourceSubtreeTree':structure['sourceSubtreeTree'],'sourceKeyCount':len(ordered_keys),'orderedKeyInventorySha256':structure['orderedKeyInventorySha256'],'sourceIdInventorySha256':structure['sourceIdInventorySha256'],'priorW1W43UniqueIds':len(prior_ids),'pendingIdsAfterPriorExclusion':len(pending),'selectedIds':[{'rank':i,'sourceId':selected[i-1]['sourceId'],'source':selected[i-1]['source'],'sourceSha256':selected[i-1]['sourceSha256'],'historicalOrdinal':None} for i in range(1,26)],'historicalOrdinalWindowEstablished':False,'sourceSelectionClaim':'Ranks 1–25 from the exact current lexicographically sorted pending source-ID queue after W1-W43 exclusion; no historical source ordinal is claimed.','all12CatalogsOrderAndKeysetsMatch':True}
(OUT/'source-selection-reattestation.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
summary_out={'schemaVersion':1,'title':'slskdN PR #409 W44 reconstructed primary packet independent cross-review','repository':'snapetech-org/slskdN','pullRequest':409,'exactHead':HEAD,'exactTree':TREE,'state':'OPEN','draft':True,'scope':{'selectionRanks':[1,25],'sourceIds':25,'locales':LOCALES,'cells':300,'historicalSourceOrdinalRange':None},'crossReviewDispositionCounts':dict(counts),'primaryCandidates':31,'primaryCorrectionsAccepted':15,'primaryRefinementsAccepted':16,'primaryRevisions':0,'additionalCorrections':2,'additionalRefinements':2,'additionalIssues':[{'rank':r,'locale':l,'targetSha256':sha(t),'type':d} for (r,l),(t,d,w) in ADDITIONAL.items()],'callerRefsVerified':sum(len(v) for v in caller_checks.values()),'callerRefFailures':len(caller_failures),'catalogKeysetParity':12,'sourceTargetStructuralFailures':0,'sourceCallerGapsHeld':24,'w98PriorHoldCellsReattested':len(w98_readback),'w98PriorHoldCellsOutstanding':len(w98_readback),'spanishDirectAddressRows':0,'spanishFormalApplicability':'not applicable for this slice','primaryPacket':str(PRIMARY),'primaryPacketManifestSha256':manifest_sha,'primaryPacketChecksumRowsVerified':primary_sum_rows,'browserReview':False,'nativeSpeakerApproval':False,'testsBuildCiRun':False,'repositoryModified':False,'confidence':'moderate','scopeLimitation':'Primary packet selection is reconstructed from current pending IDs because historical W44 boundary and W40 frozen queue are absent; ranks are used, no source ordinals are fabricated.'}
(OUT/'cross-review-summary.json').write_text(json.dumps(summary_out,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
final={'capturedAtUtc':now,'repository':'snapetech-org/slskdN','pullRequest':409,'state':end409['state'],'isDraft':end409['isDraft'],'prHeadBranch':end409['headRefName'],'exactHead':HEAD,'exactTree':TREE,'remoteBranchOid':end409['remoteBranchOid'],'worktree':str(WORK),'worktreeBranch':git('branch','--show-current').decode().strip(),'worktreeHead':git('rev-parse','HEAD').decode().strip(),'worktreeTree':git('rev-parse','HEAD^{tree}').decode().strip(),'worktreeStatus':'clean','allSevenPRsQueriedAtStartAndEnd':True,'allSevenPRHeadsStable':True,'w44SourceSelectionRanks':[1,25],'historicalW44OrdinalRange':None,'cellsReadBack':300,'dispositions':dict(counts),'primaryCandidateCount':31,'additionalFindingCount':len(extra),'callerRefsVerified':sum(len(v) for v in caller_checks.values()),'catalogsReattested':12,'priorW1W43SourceIdsReattested':len(prior_ids),'w98HoldsReattested':len(w98_readback),'primaryPacketManifestSha256':manifest_sha,'primaryPacketChecksumRowsVerified':primary_sum_rows,'readbackFailures':0,'nativeSpeakerApproval':False,'browserReview':False,'testsBuildCiRun':False,'repoModified':False,'confidence':'moderate'}
(OUT/'final-reattestation.json').write_text(json.dumps(final,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
print(json.dumps({'head':HEAD,'tree':TREE,'counts':dict(counts),'candidateCount':len(candidates),'additionalFindings':len(extra),'callerRefsVerified':sum(len(v) for v in caller_checks.values()),'callerFailures':len(caller_failures),'priorW98Holds':len(w98_readback),'primaryPacketChecksumRows':primary_sum_rows,'readbackFailures':0},ensure_ascii=False,indent=2))
