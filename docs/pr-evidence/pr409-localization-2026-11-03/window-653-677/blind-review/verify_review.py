#!/usr/bin/env python3
"""Portable verifier for the slskdN PR #409 W71 blind-review packet."""
from pathlib import Path
import collections, hashlib, json, re, subprocess, sys
HERE=Path(__file__).resolve().parent
INPUT=HERE/'input'
HEAD='d0317d8258a31d05b7f163921c2e39f93deabfca'
TREE='01475aeffa17f6151c4bf161890662167c959bb0'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

def fail(s): raise SystemExit('FAIL: '+s)
def ok(x,s):
    if not x: fail(s)
def sha(b):
    if isinstance(b,str): b=b.encode('utf-8')
    return hashlib.sha256(b).hexdigest()
def jf(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def token_sig(text):
    return {'placeholders':re.findall(r'\{[A-Za-z][A-Za-z0-9_]*\}',text),'markup':re.findall(r'</?[A-Za-z][^>]*>',text),'numeric':re.findall(r'(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])',text)}
def literal_present(term,text): return re.search(r'(?<![A-Za-z0-9])'+re.escape(term)+r'(?![A-Za-z0-9])',text) is not None

def sums(root,name='SHA256SUMS.txt'):
    seen={}; p=root/name
    for line in p.read_text(encoding='utf-8').splitlines():
        m=re.fullmatch(r'([0-9a-f]{64})  (.+)',line); ok(m is not None,'malformed checksum row '+str(p))
        h,rel=m.groups(); q=Path(rel)
        ok(not q.is_absolute() and '..' not in q.parts and rel not in seen,'unsafe/duplicate checksum path '+rel)
        seen[rel]=h
    actual={x.relative_to(root).as_posix() for x in root.rglob('*') if x.is_file() and x!=p}
    ok(actual==set(seen),'checksum inventory mismatch '+str(root))
    for rel,h in seen.items(): ok(sha((root/rel).read_bytes())==h,'checksum '+str(root/rel))
    return seen

def verify():
    root_sums=sums(HERE)
    manifest=jf(HERE/'manifest.json')
    payload={x.relative_to(HERE).as_posix() for x in HERE.rglob('*') if x.is_file() and x.relative_to(HERE).as_posix() not in ('manifest.json','SHA256SUMS.txt')}
    ok({x['path'] for x in manifest['files']}==payload,'review manifest inventory')
    for item in manifest['files']:
        q=HERE/item['path']; ok(q.stat().st_size==item['byteCount'] and sha(q.read_bytes())==item['sha256'],'manifest file hash/size '+item['path'])
    ok((manifest['repository'],manifest['pullRequest'],manifest['head'],manifest['tree'],manifest['window'],manifest['cellCount'])==('snapetech-org/slskdN',409,HEAD,TREE,'W71 ranks 653-677',300),'review manifest scope')
    summary0=jf(HERE/'summary.json')
    ok(manifest['dispositionCounts']==summary0['dispositionCounts'] and manifest['proposalCount']==summary0['proposals']==61 and manifest['currentHoldCount']==summary0['newHolds']==12,'review manifest totals')
    # Re-verify the sealed candidate-free packet before reading its cells.
    input_sums=sums(INPUT,'PACKET-SHA256SUMS.txt')
    subprocess.run([sys.executable,str(INPUT/'verify_input.py')],cwd=INPUT,check=True,stdout=subprocess.PIPE,text=True)
    im=jf(INPUT/'manifest.json'); att=jf(INPUT/'head-tree-attestation.json')
    ok((im['repository'],im['pullRequest'],im['head'],im['tree'],im['sourceCount'],im['localeCount'],im['cellCount'])==('snapetech-org/slskdN',409,HEAD,TREE,25,12,300),'candidate-free input pin')
    ok(att['headRefOid']==att['branchRefOid']==att['pullRefOid']==HEAD and att['treeOid']==TREE,'input live attestation')
    # Reattest live PR state, exact refs/tree and deployments before/after review.
    before=jf(HERE/'live-before.json'); after=jf(HERE/'live-after.json')
    for label,s in [('before',before),('after',after)]:
        pr=s['pullRequest']
        ok(s['repository']=='snapetech-org/slskdN','live repository '+label)
        ok(pr['number']==409 and pr['state']=='OPEN' and pr['isDraft'] is True and pr['baseRefName']=='main','live PR state '+label)
        ok(pr['headRefName']=='codex/slskdn-oidc-tooltip-localization-20261030' and pr['headRefOid']==HEAD,'live PR head '+label)
        ok(s['branchRef']==HEAD and s['pullRef']==HEAD and s['tree']==TREE,'live branch/pull/tree '+label)
        ok(s['deploymentCountForHead']==0 and s['deploymentIdsForHead']==[],'live deployments '+label)
    fields=lambda s:(s['pullRequest'],s['branchRef'],s['pullRef'],s['tree'],s['deploymentCountForHead'],s['deploymentIdsForHead'])
    ok(fields(before)==fields(after),'live PR/ref state changed during review')
    # Validate source/caller/catalog preimages and the complete 300-cell review.
    cells=jl(INPUT/'source-current-cells.jsonl'); cmap={(r['continuationRank'],r['locale']):r for r in cells}
    sources={r['continuationRank']:r for r in jl(INPUT/'source-inventory-selection.jsonl')}
    contexts={r['sourceId']:r for r in jl(INPUT/'caller-contexts.jsonl')}
    ledger=jl(HERE/'blind-ledger.jsonl'); lmap={(r['continuationRank'],r['locale']):r for r in ledger}
    expected=[(rank,loc) for rank in range(653,678) for loc in LOCALES]
    ok(len(cells)==len(ledger)==300 and len(sources)==len(contexts)==25,'row counts')
    ok(list(cmap)==expected and list(lmap)==expected,'coverage/order')
    counts=collections.Counter(); baseline=collections.Counter(); proposal_failures=0
    for key in expected:
        c=cmap[key]; row=lmap[key]; src=sources[key[0]]; ctx=contexts[src['sourceId']]
        for field,actual in [('sourceId',src['sourceId']),('sourceSha256',src['sourceSha256']),('currentTargetSha256',c['currentTargetSha256']),('locale',c['locale']),('catalogPath',c['catalogPath']),('catalogFileSha256',c['catalogFileSha256']),('catalogGitBlob',c['catalogGitBlob']),('callerContextSha256',c['callerContextSha256'])]:
            ok(row[field]==actual,'cell pin '+str(key)+':'+field)
        ok(c['sourceId']==src['sourceId'] and c['sourceSha256']==src['sourceSha256'] and sha(c['source'])==c['sourceSha256'],'source preimage '+str(key))
        ok(sha(c['currentTarget'])==c['currentTargetSha256']==row['currentTargetSha256'],'target preimage hash '+str(key))
        ok(row['callerCount']==ctx['productionCallerCount']==len(ctx['callers']),'caller count '+str(key))
        ok(row['callerRefs']==[{'path':x['path'],'line':x['line'],'lineSha256':x['lineSha256'],'contextSha256':x['contextSha256'],'fileSha256':x['fileSha256'],'gitBlob':x['gitBlob']} for x in c['callerRefs']],'caller reference pins '+str(key))
        ok(row['callerContextSha256']==c['callerContextSha256'],'caller context hash '+str(key))
        catalog=next((x for x in jl(INPUT/'catalog-structure.jsonl') if x['locale']==c['locale']),None)
        ok(catalog is not None and catalog['entryCount']==6176 and catalog['orderedKeySha256']==im['orderedCatalogKeySha256'],'catalog structure '+str(key))
        diag={'placeholderMismatch':not c['placeholderEvidence']['matches'],'markupMismatch':not c['markupEvidence']['matches'],'numericMismatch':not c['numericTokensPreserved'],'protectedLiteralMismatch':not c['protectedLiteralEvidence']['matches']}
        ok(row['baselineDiagnostics']==diag,'baseline diagnostics '+str(key))
        for k,v in diag.items(): baseline[k]+=v
        disp=row['disposition']; counts[disp]+=1
        target=row.get('proposedTarget')
        if disp=='hold':
            ok(key[0]==654 and ctx['productionCallerCount']==0 and not target and 'proposedTarget' not in row,'hold boundary '+str(key))
            ok(row['confidence']=='low' and row['targetTextIncluded'] is False,'hold hash-only '+str(key))
            continue
        if disp=='accept-current':
            ok(not target and 'proposedTarget' not in row and row['targetTextIncluded'] is False,'accept-current proposal omission '+str(key))
            ok(not any(diag.values()),'accepted baseline mismatch '+str(key))
            target=c['currentTarget']
        else:
            ok(disp in ('correction','refinement') and isinstance(target,str) and target,'proposal disposition/text '+str(key))
            ok(row['targetTextIncluded'] is True and row['proposedTargetSha256']==sha(target),'proposal hash/text inclusion '+str(key))
            ok(target!=c['currentTarget'],'proposal has no change '+str(key))
            ss=token_sig(c['source']); ts=token_sig(target); req=c['sourceProtectedLiterals']
            checks={'proposalPresent':True,'proposalPlaceholderMatch':ts['placeholders']==ss['placeholders'],'proposalMarkupMatch':ts['markup']==ss['markup'],'proposalNumericMatch':ts['numeric']==ss['numeric'],'proposalProtectedLiteralsRequired':req,'proposalProtectedLiteralsPresent':[x for x in req if literal_present(x,target)],'proposalProtectedLiteralsPreserved':all(literal_present(x,target) for x in req)}
            ok(row['checks']==checks and all(checks[x] for x in ('proposalPlaceholderMatch','proposalMarkupMatch','proposalNumericMatch','proposalProtectedLiteralsPreserved')),'proposal tokens/literals '+str(key))
            proposal_failures+=0
        if key[0]==672 and key[1]=='hi': ok('TLS' in target,'Hindi protected TLS literal missing')
        if key[0]==659: ok('Soulseek' in target,'Soulseek protected literal missing '+str(key))
    ok(counts=={'accept-current':227,'hold':12,'correction':44,'refinement':17},'decision counts '+str(counts))
    ok(baseline=={'placeholderMismatch':0,'markupMismatch':0,'numericMismatch':2,'protectedLiteralMismatch':1},'baseline mismatch totals '+str(baseline))
    # Verify the separately sealed candidate-free secondary blind subset and our adjudication hashes.
    subset=HERE/'evidence/secondary-blind-subset'
    subset_sums={}
    for line in (subset/'CHECKSUMS.sha256').read_text(encoding='utf-8').splitlines():
        m=re.fullmatch(r'([0-9a-f]{64})  (.+)',line); ok(m is not None,'secondary checksum row')
        h,rel=m.groups(); ok(rel not in subset_sums and '..' not in Path(rel).parts,'secondary unsafe/duplicate path')
        subset_sums[rel]=h
    subset_actual={x.relative_to(subset).as_posix() for x in subset.rglob('*') if x.is_file() and x.name!='CHECKSUMS.sha256'}
    ok(subset_actual==set(subset_sums),'secondary checksum inventory')
    for rel,h in subset_sums.items(): ok(sha((subset/rel).read_bytes())==h,'secondary checksum '+rel)
    smeta=jf(subset/'subset-metadata.json')
    ok((smeta['repository'],smeta['pullRequest'],smeta['head'],smeta['tree'],smeta['cellCount'],smeta['nativeSpeakerSignoff'])==('snapetech-org/slskdN',409,HEAD,TREE,75,False),'secondary metadata scope')
    for name,h in smeta['inputSha256'].items(): ok(sha((INPUT/name).read_bytes())==h,'secondary input pin '+name)
    secondary=jl(subset/'subset-ledger.jsonl'); adjudication=jl(HERE/'secondary-review-adjudication.jsonl')
    ok(len(secondary)==len(adjudication)==75,'secondary review count')
    smap={(x['continuationRank'],x['locale']):x for x in secondary}; amap={(x['continuationRank'],x['locale']):x for x in adjudication}
    expected_subset={(r,l) for r in range(653,678) for l in ('es','hi','vi')}
    ok(set(smap)==set(amap)==expected_subset,'secondary coverage')
    sec_counts=collections.Counter(x['decision'] for x in secondary)
    ok(sec_counts=={'accept':51,'revise':21,'hold_context':3},'secondary disposition counts')
    for k,x in smap.items():
        r=lmap[k]; a=amap[k]; sec_target=x['reviewedTarget']; ours=r.get('proposedTarget') or cmap[k]['currentTarget']
        expected_alignment=(x['decision']=='accept' and r['disposition']=='accept-current') or (x['decision']=='revise' and r['disposition'] in ('correction','refinement')) or (x['decision']=='hold_context' and r['disposition']=='hold')
        ok(a['secondaryDecision']==x['decision'] and a['blindDisposition']==r['disposition'],'secondary adjudication labels '+str(k))
        ok(a['dispositionAligned'] is expected_alignment and expected_alignment,'secondary disposition alignment '+str(k))
        equal=sec_target==ours
        ok(a['targetTextEqual'] is equal and a['secondaryReviewedTargetSha256']==sha(sec_target) and a['blindReviewedTargetSha256']==sha(ours),'secondary target hash comparison '+str(k))
    ok(sum(x['targetTextEqual'] for x in adjudication)==74,'secondary exact target agreement count')
    # Hold list is hash-only and covers exactly the callerless source's 12 locales.
    holds=jl(HERE/'review-holds-hash-only.jsonl')
    ok(len(holds)==12 and {(x['continuationRank'],x['locale']) for x in holds}=={(654,l) for l in LOCALES},'hold file coverage')
    for x in holds:
        k=(x['continuationRank'],x['locale']); c=cmap[k]
        ok(x['sourceId']==c['sourceId'] and x['sourceSha256']==c['sourceSha256'] and x['currentTargetSha256']==c['currentTargetSha256'] and x['callerCount']==0 and x['targetTextIncluded'] is False,'hash-only hold row '+str(k))
        ok(not any(k in x for k in ('source','currentTarget','target','targetText','proposedTarget')),'hold row contains text '+str(k))
    # Prior held-cell and selected-ID reattestations disclose only hashes/IDs.
    prior_in=jl(INPUT/'prior-held-cell-reattestation.jsonl'); prior_out=jl(HERE/'prior-held-cell-reattestation-hash-only.jsonl')
    ok(len(prior_in)==len(prior_out)==140,'prior hold count')
    prior_keys={(x['continuationRank'],x['locale'],x['sourceId']):x for x in prior_in}
    for x in prior_out:
        k=(x['continuationRank'],x['locale'],x['sourceId']); y=prior_keys.get(k)
        ok(y is not None and x['targetTextIncluded'] is False,'prior hold hash-only row '+str(k))
        ok(not any(f in x for f in ('source','priorTarget','currentTarget','target','targetText')),'prior target/source text present '+str(k))
        for field in ('sourceSha256','priorTargetSha256','currentTargetSha256','matchesPriorCurrentValue','currentCallerCount','currentCallerContextSha256','currentCatalogPath','currentCatalogFileSha256','currentCatalogGitBlob','holdReason','status'):
            ok(x[field]==y[field],'prior hold reattestation mismatch '+str(k)+':'+field)
        ok(x['matchesPriorCurrentValue'] is True and x['priorTargetSha256']==x['currentTargetSha256'],'prior hold target hashes '+str(k))
    ex_in=jl(INPUT/'prior-selected-id-exclusions.jsonl'); ex_out=jl(HERE/'prior-selected-id-exclusions-hash-only.jsonl')
    ok(len(ex_in)==len(ex_out)==1757,'prior selected ID exclusion count')
    expected_ex={(x['sourceId'],x['sourceSha256'],x['selectionOrigin'],x.get('continuationRank'),x.get('remainingQueueRank'),tuple(x.get('exclusionOrigins',[]))) for x in ex_in}
    actual_ex={(x['sourceId'],x['sourceSha256'],x['selectionOrigin'],x.get('continuationRank'),x.get('remainingQueueRank'),tuple(x.get('exclusionOrigins',[]))) for x in ex_out}
    ok(actual_ex==expected_ex and len({x['sourceId'] for x in ex_out})==1757,'prior selected exclusion hash map')
    for x in ex_out:
        ok(x['sourceTextIncluded'] is False and x['targetTextIncluded'] is False and x['exclusionConfirmed'] is True,'exclusion text/hash-only marker')
        ok(not any(k in x for k in ('source','target','targetText','currentTarget','priorTarget')),'prior exclusion contains text')
    summary=jf(HERE/'summary.json')
    ok(summary['cellsReviewed']==300 and summary['dispositionCounts']==dict(counts) and summary['proposals']==61 and summary['newHolds']==12,'summary decisions')
    ok(summary['carriedHoldsReattestedHashOnly']==140 and summary['priorSelectedIdExclusionsReattestedHashOnly']==1757,'summary lineage')
    ok(summary['baselineTokenMismatches']=={'placeholder':0,'markup':0,'numeric':2,'protectedLiteral':1} and summary['proposalTokenOrLiteralFailures']==proposal_failures==0,'summary token controls')
    ok(summary['nativeSpeakerReviewPerformed'] is False and summary['catalogValuesApplied'] is False and summary['repositoryOrPRFilesChanged'] is False,'review limits')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'cells':len(ledger),'dispositionCounts':dict(counts),'proposals':summary['proposals'],'newCallerlessHolds':len(holds),'carriedHoldsHashOnly':len(prior_out),'priorSelectedIdExclusionsHashOnly':len(ex_out),'baselineTokenMismatches':dict(baseline),'proposalTokenOrLiteralFailures':proposal_failures,'inputFilesVerified':len(input_sums),'outputFilesVerified':len(root_sums),'secondaryFilesVerified':len(subset_sums),'livePRState':'OPEN/DRAFT at same exact head/tree before and after','deploymentsForHead':0},indent=2,ensure_ascii=False))

if __name__=='__main__': verify()
