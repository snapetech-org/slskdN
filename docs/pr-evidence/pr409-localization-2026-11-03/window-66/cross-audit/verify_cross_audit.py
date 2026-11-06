#!/usr/bin/env python3
import collections, hashlib, json, pathlib, re, subprocess
OUT=pathlib.Path(__file__).resolve().parent
BASE=pathlib.Path('/home/keith/Documents/code/task-scratch')
M=json.loads((OUT/'manifest.json').read_text())
INPUT=pathlib.Path(M['inputPaths']['candidateFree']); PRIMARY=pathlib.Path(M['inputPaths']['primary']); BLIND=pathlib.Path(M['inputPaths']['blind'])
HEAD=M['head']; TREE=M['tree']
def sha(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha(p.read_bytes())
def j(p): return json.loads(p.read_text())
def jl(p): return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def run(args,cwd=None): return subprocess.run(args,cwd=cwd,check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT).stdout.strip()
def checks(cell,target):
    nums=re.findall(r'(?<![A-Za-z])\d+(?:[.,]\d+)?(?![A-Za-z])',target); ph=re.findall(r'\{[^{}]*\}',target); tags=re.findall(r'</?[A-Za-z][^>]*>',target); lits=cell['sourceProtectedLiterals']
    result={'placeholders':{'source':cell['placeholderEvidence']['sourceTokens'],'selected':ph,'match':sorted(ph)==sorted(cell['placeholderEvidence']['sourceTokens'])},'markup':{'source':cell['markupEvidence']['sourceTags'],'selected':tags,'match':sorted(tags)==sorted(cell['markupEvidence']['sourceTags'])},'numeric':{'source':cell['sourceNumericTokens'],'selected':nums,'match':sorted(nums)==sorted(cell['sourceNumericTokens'])},'protectedLiterals':{'source':lits,'selected':[t for t in lits if target.count(t)>=lits.count(t)],'match':all(target.count(t)>=lits.count(t) for t in set(lits))}}
    result['allPass']=all(x['match'] for x in result.values())
    return result

def verify():
    if M.get('sealed') is not True or M.get('cellCount')!=300: raise SystemExit('Manifest seal/count mismatch')
    own_sums=OUT/'SHA256SUMS.txt'
    if own_sums.exists(): run(['sha256sum','-c','SHA256SUMS.txt'],OUT)
    expected=set(M['outputFileSet'])
    files={x['path']:x for x in M['files']}
    if set(files)!=expected: raise SystemExit('Manifest output set mismatch')
    for name,rec in files.items():
        p=OUT/name
        if not p.is_file() or p.stat().st_size!=rec['bytes'] or sha_file(p)!=rec['sha256']: raise SystemExit('Manifest hash mismatch: '+name)
    # Upstream packets are verified independently and remain immutable inputs.
    run(['sha256sum','-c','PACKET-SHA256SUMS.txt'],INPUT)
    iv=json.loads(run(['python3','verify_input.py'],INPUT))
    run(['sha256sum','-c','SHA256SUMS.txt'],PRIMARY); pv=json.loads(run(['python3','verify_primary.py'],PRIMARY))
    run(['sha256sum','-c','SHA256SUMS.txt'],BLIND); bv=json.loads(run(['python3','verify_blind_review.py'],BLIND))
    if iv.get('pass') is not True or pv.get('pass') is not True or bv.get('result')!='PASS': raise SystemExit('Upstream packet verifier failed')
    if any(x!=HEAD for x in (iv['head'],pv['head'],bv['head'])) or any(x!=TREE for x in (iv['tree'],pv['tree'],bv['tree'])): raise SystemExit('Upstream head/tree mismatch')
    pins=M['inputPins']; pinmap={'candidateFreeManifestSha256':INPUT/'manifest.json','candidateFreeChecksumListSha256':INPUT/'PACKET-SHA256SUMS.txt','candidateFreeCellsSha256':INPUT/'source-current-cells.jsonl','candidateFreeCallerContextsSha256':INPUT/'caller-contexts.jsonl','candidateFreePriorHeldSha256':INPUT/'prior-held-cell-reattestation.jsonl','primaryManifestSha256':PRIMARY/'manifest.json','primaryChecksumListSha256':PRIMARY/'SHA256SUMS.txt','primaryLedgerSha256':PRIMARY/'primary-ledger.jsonl','blindManifestSha256':BLIND/'manifest.json','blindChecksumListSha256':BLIND/'SHA256SUMS.txt','blindLedgerSha256':BLIND/'sealed-blind-review-ledger.jsonl'}
    for k,p in pinmap.items():
        if sha_file(p)!=pins[k]: raise SystemExit('Input pin mismatch: '+k)
    if j(PRIMARY/'manifest.json').get('blindPacketAccessed') is not False or j(BLIND/'manifest.json').get('primaryPacketOpened') is not False: raise SystemExit('Blind separation metadata mismatch')
    live=j(OUT/'live-head-attestation.json')
    if live['prHead']!=HEAD or live['branchHead']!=HEAD or live['pullHead']!=HEAD or live['tree']!=TREE or live['state']!='OPEN' or live['isDraft'] is not True: raise SystemExit('Live attestation mismatch')
    rows=jl(OUT/'resolution-ledger.jsonl'); cells=jl(INPUT/'source-current-cells.jsonl'); ps=jl(PRIMARY/'primary-ledger.jsonl'); bs=jl(BLIND/'sealed-blind-review-ledger.jsonl'); bm={(x['sourceId'],x['locale']):x for x in bs}; callers={x['sourceId']:x for x in jl(INPUT/'caller-contexts.jsonl')}
    if not (len(rows)==len(cells)==len(ps)==len(bs)==300) or len(bm)!=300: raise SystemExit('Exact 300-cell coverage mismatch')
    counts=collections.Counter(); sources=collections.Counter(); agreements=0; conflicts=0; primary_selected=0; blind_selected=0; dispo_overrides=0; protected=[]; numeric=[]
    for row,cell,p in zip(rows,cells,ps):
        key=(cell['continuationRank'],cell['locale']); b=bm[(cell['sourceId'],cell['locale'])]; c=row['resolution']; caller=callers[cell['sourceId']]
        if (row['continuationRank'],row['locale'],row['sourceId'])!=(key[0],key[1],cell['sourceId']): raise SystemExit('Row key/order mismatch: '+str(key))
        if row['head']!=HEAD or row['tree']!=TREE or row['source']!=cell['source'] or row['sourceSha256']!=cell['sourceSha256'] or row['currentTarget']!=cell['currentTarget'] or row['currentTargetSha256']!=cell['currentTargetSha256'] or row['catalogPath']!=cell['catalogPath'] or row['catalogKey']!=cell['catalogKey'] or row['catalogGitBlob']!=cell['catalogGitBlob']: raise SystemExit('Candidate-free binding mismatch: '+str(key))
        if row['callerContextSha256']!=cell['callerContextSha256'] or row['callerContexts']!=caller['callers'] or row['callerCount']!=caller['productionCallerCount']: raise SystemExit('Caller context mismatch: '+str(key))
        if row['primaryReview']['disposition']!=p['disposition'] or row['blindReview']['disposition']!=b['disposition']: raise SystemExit('Review disposition linkage mismatch: '+str(key))
        pt=p.get('proposedTarget',cell['currentTarget']) if p['disposition'] in ('correction','refinement') else cell['currentTarget']
        bt=b.get('translation') if b['disposition'] in ('correction','refinement','accept-current') else cell['currentTarget']
        if b['disposition']=='hold': bt=cell['currentTarget']
        if row['primaryReview']['selectedTarget']!=pt or row['blindReview']['effectiveTarget']!=bt: raise SystemExit('Review target linkage mismatch: '+str(key))
        if pt==bt:
            agreements+=1
            if c['targetSource'] not in ('current','agreement','hold-consensus'): raise SystemExit('Bad agreement source: '+str(key))
        else:
            conflicts+=1
            if c['targetSource']=='primary': primary_selected+=1
            elif c['targetSource']=='blind': blind_selected+=1
            else: raise SystemExit('Unresolved target conflict: '+str(key))
        if c['selectedTargetSha256']!=sha(c['selectedTarget'].encode()) or c['tokenChecks']!=checks(cell,c['selectedTarget']) or not c['tokenChecks']['allPass']: raise SystemExit('Target hash/token mismatch: '+str(key))
        if c['disposition'] in ('accept-current','hold') and c['selectedTarget']!=cell['currentTarget']: raise SystemExit('Non-change target mismatch: '+str(key))
        if c['disposition'] in ('correction','refinement') and c['selectedTarget']==cell['currentTarget']: raise SystemExit('Change disposition retains current target: '+str(key))
        if c['disposition']!=p['disposition']: dispo_overrides+=1
        if c['targetSource'] in ('primary','blind') and c['selectedTarget'] != (pt if c['targetSource']=='primary' else bt): raise SystemExit('Selected side target mismatch: '+str(key))
        expected_missing=[t for t in cell['sourceProtectedLiterals'] if cell['currentTarget'].count(t)<cell['sourceProtectedLiterals'].count(t)]
        if expected_missing:
            protected.append(key)
            a=c.get('tokenAdjudication')
            if not a or a['sourceLiterals']!=expected_missing or not a['selectedTargetRetainsAll']: raise SystemExit('Protected-literal adjudication absent: '+str(key))
        elif c.get('tokenAdjudication') is not None: raise SystemExit('Spurious protected-literal adjudication: '+str(key))
        source_nums=re.findall(r'(?<![A-Za-z])\d+(?:[.,]\d+)?(?![A-Za-z])',cell['currentTarget'])
        if sorted(source_nums)!=sorted(cell['sourceNumericTokens']): numeric.append(key)
        if key==(549,'ja'):
            a=c.get('numericSurfaceAdjudication')
            if not a or not a['currentSurfaceHasASCII2'] or not a['selectedSurfaceUsesKanjiOrdinal'] or a['numericSelectedTokens']: raise SystemExit('Japanese numeric surface not adjudicated')
        elif c.get('numericSurfaceAdjudication') is not None: raise SystemExit('Spurious numeric adjudication')
        counts[c['disposition']]+=1; sources[c['targetSource']]+=1
    if conflicts!=41 or primary_selected!=25 or blind_selected!=16 or sorted(protected)!=[(535,'ar'),(535,'es'),(535,'hi'),(542,'hi'),(548,'hi')] or numeric!=[(549,'ja')]: raise SystemExit(f'Conflict/token reconciliation count mismatch: {conflicts}/{primary_selected}/{blind_selected}; {protected}; {numeric}')
    holds=[r for r in rows if r['resolution']['disposition']=='hold']
    if len(holds)!=24 or {r['continuationRank'] for r in holds}!={533,541} or any(r['callerCount']!=0 or r['resolution']['selectedTarget']!=r['currentTarget'] for r in holds): raise SystemExit('24 callerless holds not preserved')
    prior=INPUT/'prior-held-cell-reattestation.jsonl'; copy=OUT/'prior-held-cell-reattestation.jsonl'
    if len(jl(prior))!=104 or sha_file(prior)!=sha_file(copy) or jl(prior)!=jl(copy): raise SystemExit('104 prior held cells not preserved byte-for-byte')
    plan=j(OUT/'apply-plan.json'); planmap={(r['sourceId'],r['locale']):r for r in plan['cells']}
    if plan.get('applicationStatus')!='not applied' or plan.get('applicationAllowedByThisTask') is not False or len(planmap)!=300: raise SystemExit('Apply-plan state/coverage mismatch')
    for r in rows:
        key=(r['sourceId'],r['locale']); x=r['resolution']; q=planmap[key]
        if q['selectedTarget']!=x['selectedTarget'] or q['selectedTargetSha256']!=x['selectedTargetSha256'] or q['disposition']!=x['disposition'] or q['applied'] is not False: raise SystemExit('Apply-plan linkage mismatch: '+str(key))
    summary=j(OUT/'summary.json')
    if summary['proposalConflicts']!=41 or summary['primarySelectedConflictCount']!=25 or summary['blindSelectedConflictCount']!=16 or summary['protectedLiteralGapsCorrected']!=5 or summary['numericSurfaceMismatchCount']!=1 or summary['callerlessHoldCells']!=24 or summary['priorHeldCellsReattestedUnchanged']!=104 or summary['crossAuditDispositionCounts']!=dict(sorted(counts.items())) or summary['crossAuditTargetSourceCounts']!=dict(sorted(sources.items())): raise SystemExit('Summary mismatch')
    verification={'result':'PASS','head':HEAD,'tree':TREE,'cells':300,'targetConflictsResolved':41,'selectedFromPrimary':25,'selectedFromBlind':16,'protectedLiteralGapsAdjudicated':5,'japaneseNumericSurfaceAdjudicated':1,'callerlessHoldsPreserved':24,'priorHeldCellsReattestedUnchanged':104,'allSelectedTokenChecksPass':True,'upstreamInputPrimaryBlindVerifiers':'PASS','livePrHeadTree':'PASS','application':'NOT APPLIED'}
    print(json.dumps(verification,ensure_ascii=False,indent=2))
if __name__=='__main__': verify()
