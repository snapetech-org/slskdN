import hashlib, json, re, subprocess
from collections import Counter
from pathlib import Path

OUT=Path(__file__).resolve().parent
IN=Path('/home/keith/Documents/code/task-scratch/slskdn-pr409-w71-653-677-20261103/candidate-free-packet/input')
HEAD='d0317d8258a31d05b7f163921c2e39f93deabfca'
TREE='01475aeffa17f6151c4bf161890662167c959bb0'
LOCALES=('ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant')
def sha(b): return hashlib.sha256(b).hexdigest()
def j(path): return json.loads(path.read_text(encoding='utf-8'))
def jl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def ph(s): return sorted(re.findall(r'\{[^{}]+\}',s))
def tags(s): return sorted(re.findall(r'</?[A-Za-z][^>]*>',s))
def nums(s): return re.findall(r'(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])',s)
def prot(s):
    found=set(re.findall(r'(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])',s))
    for x in ('Wishlist','Soulseek','Discogs','Pod'):
        if re.search(r'(?<![A-Za-z0-9])'+re.escape(x)+r'(?![A-Za-z0-9])',s): found.add(x)
    return sorted(found)
def checks(source,target):
    missing=[x for x in prot(source) if x not in target]
    return {'placeholders':{'source':ph(source),'target':ph(target),'matches':ph(source)==ph(target)},
            'markupTags':{'source':tags(source),'target':tags(target),'matches':tags(source)==tags(target)},
            'numericTokens':{'source':nums(source),'target':nums(target),'matches':nums(source)==nums(target)},
            'protectedLiterals':{'source':prot(source),'target':prot(target),'missing':missing,'matches':not missing}}
def verify_sums(directory, filename):
    entries={}
    for line in (directory/filename).read_text(encoding='utf-8').splitlines():
        digest,name=line.split('  ',1); entries[name]=digest
    assert entries
    for name,digest in entries.items(): assert sha((directory/name).read_bytes())==digest, f'checksum mismatch: {name}'
    return entries

def main():
    out_sums=verify_sums(OUT,'SHA256SUMS.txt')
    in_sums=verify_sums(IN,'PACKET-SHA256SUMS.txt')
    candidate_check=json.loads(subprocess.check_output(['python',str(IN/'verify_input.py')],text=True))
    assert candidate_check['verifier']=='PASS' and candidate_check['currentCells']==300
    att=j(IN/'head-tree-attestation.json')
    assert att['headRefOid']==HEAD and att['branchRefOid']==HEAD and att['pullRefOid']==HEAD and att['treeOid']==TREE
    manifest=j(OUT/'manifest.json')
    assert manifest['head']==HEAD and manifest['tree']==TREE
    assert manifest['candidateFreeChecksumListSha256']==sha((IN/'PACKET-SHA256SUMS.txt').read_bytes())
    source_rows=jl(IN/'source-current-cells.jsonl')
    current={(r['sourceId'],r['locale']):r for r in source_rows}
    contexts={r['sourceId']:r for r in jl(IN/'caller-contexts.jsonl')}
    selected=jl(IN/'source-inventory-selection.jsonl')
    excluded=jl(IN/'prior-selected-id-exclusions.jsonl')
    holds=jl(IN/'prior-held-cell-reattestation.jsonl')
    catalog=jl(IN/'catalog-structure.jsonl')
    assert len(selected)==25 and {r['continuationRank'] for r in selected}==set(range(653,678))
    assert len(excluded)==1757 and len({r['sourceId'] for r in excluded})==1757
    assert len(holds)==140 and all(r['matchesPriorCurrentValue'] for r in holds)
    assert len(catalog)==12 and all(r['entryCount']==6176 and r['orderedKeySha256']=='3ca04c40ebfed00b93fcd143109fc9d85da941cec30b6cb93f52e431498df6a7' for r in catalog)
    review=jl(OUT/'primary-review.jsonl')
    assert len(review)==300 and len({(r['sourceId'],r['locale']) for r in review})==300
    counts=Counter(r['disposition'] for r in review)
    assert dict(counts)==manifest['dispositions']
    assert counts==Counter({'accept-current':257,'correct':21,'refine':10,'hold':12})
    assert all(sum(r['locale']==loc for r in review)==25 for loc in LOCALES)
    proposals=0; current_flags=[]; proposal_failures=0
    for r in review:
        key=(r['sourceId'],r['locale']); c=current[key]; ctx=contexts[r['sourceId']]
        assert r['head']==HEAD and r['tree']==TREE and r['continuationRank']==c['continuationRank']
        assert r['source']==c['source'] and r['sourceSha256']==c['sourceSha256'] and sha(r['source'].encode())==r['sourceSha256']
        assert r['currentTarget']==c['currentTarget'] and r['currentTargetSha256']==c['currentTargetSha256'] and sha(r['currentTarget'].encode())==r['currentTargetSha256']
        assert r['catalogPath']==c['catalogPath'] and r['catalogFileSha256']==c['catalogFileSha256'] and r['catalogGitBlob']==c['catalogGitBlob']
        assert r['callerContextSha256']==c['callerContextSha256'] and r['callerCount']==ctx['productionCallerCount']
        assert r['callerRefs']==[{k:x[k] for k in ('path','line','lineSha256','contextSha256','fileSha256','gitBlob')} for x in c['callerRefs']]
        canonical=json.dumps([q['context'] for q in ctx['callers']],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        assert sha(canonical)==r['callerContextSha256']
        cur=checks(r['source'],r['currentTarget'])
        assert cur==r['currentTokenChecks']
        if not all(v['matches'] for v in cur.values()): current_flags.append((r['continuationRank'],r['locale']))
        if r['disposition'] in ('accept-current','hold'):
            assert r['proposedTarget'] is None and r['proposedTargetSha256'] is None and r['proposedTokenChecks'] is None
        else:
            proposals+=1
            assert r['proposedTarget'] and sha(r['proposedTarget'].encode())==r['proposedTargetSha256']
            proposed=checks(r['source'],r['proposedTarget'])
            assert proposed==r['proposedTokenChecks']
            if not all(v['matches'] for v in proposed.values()): proposal_failures+=1
        assert r['rationale'] and r['confidence'] in ('high','moderate','low','unknown')
    rank654=[r for r in review if r['continuationRank']==654]
    assert len(rank654)==12 and all(r['disposition']=='hold' and r['callerCount']==0 for r in rank654)
    assert len(current_flags)==3 and set(current_flags)=={(654,'ja'),(654,'ko'),(672,'hi')}
    assert proposals==31 and proposal_failures==0
    assert manifest['reviewedCells']==300 and manifest['selectedSources']==25 and manifest['proposedCells']==31
    assert manifest['priorExcludedSourceIds']==1757 and manifest['priorHeldCells']==140 and manifest['priorHoldTargetMismatches']==0
    assert len(in_sums)==16 and len(out_sums)==4
    assert manifest['primaryReviewSha256']==sha((OUT/'primary-review.jsonl').read_bytes())
    print(json.dumps({'verifier':'PASS','outputFilesHashed':len(out_sums),'inputFilesHashed':len(in_sums),'cells':len(review),'dispositions':dict(counts),'proposedTargets':proposals,'proposedTokenMismatches':proposal_failures,'baselineFlaggedCells':current_flags,'excludedIds':len(excluded),'priorHoldsReattested':len(holds)},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
