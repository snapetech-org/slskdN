#!/usr/bin/env python3
import hashlib,json,re,subprocess
from collections import Counter
from pathlib import Path
I=Path(__file__).resolve().parent
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode('utf-8')).hexdigest()
def j(n): return json.loads((I/n).read_text(encoding='utf-8'))
def jl(n): return [json.loads(x) for x in (I/n).read_text(encoding='utf-8').splitlines() if x.strip()]
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def ph(s): return sorted(set(re.findall(r'\{[^{}]+\}',s)))
def tags(s): return sorted(re.findall(r'</?[A-Za-z][^>]*>',s))
def nums(s): return re.findall(r'(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])',s)
def prot(s):
    found=set(re.findall(r'(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])',s))
    for literal in ('Wishlist','Soulseek','Discogs','Pod'):
        if re.search(r'(?<![A-Za-z0-9])'+re.escape(literal)+r'(?![A-Za-z0-9])',s): found.add(literal)
    return sorted(found)
manifest=j('manifest.json')
assert manifest['candidateFree'] is True
assert (manifest['repository'],manifest['pullRequest'],manifest['head'],manifest['tree'])==('snapetech-org/slskdN',409,'c64d57a0322897bbaac77fa88a1327dd2f687db7','51ebf25124fc6ba30c8d5d99298e78353a951f17')
assert (manifest['sourceCount'],manifest['localeCount'],manifest['cellCount'])==(25,12,300)
assert manifest['continuationRankRange']==[503,527] and manifest['remainingQueueRankRange']==[403,427]
listed={}
for item in manifest['files']:
    raw=(I/item['path']).read_bytes(); listed[item['path']]=item['sha256']
    assert len(raw)==item['bytes'] and sha(raw)==item['sha256'],item['path']
actual={p.name for p in I.iterdir() if p.is_file() and p.name not in ('manifest.json','PACKET-SHA256SUMS.txt')}
assert set(listed)==actual
checksum=set()
for line in (I/'PACKET-SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
    if not line.strip(): continue
    digest,name=line.split(None,1); name=name.strip().lstrip('*'); checksum.add(name)
    assert (I/name).is_file() and sha((I/name).read_bytes())==digest,name
assert checksum=={p.name for p in I.iterdir() if p.is_file() and p.name!='PACKET-SHA256SUMS.txt'}
att=j('head-tree-attestation.json'); boundary=j('selection-and-boundary.json')
assert att['headRefOid']==manifest['head'] and att['treeOid']==manifest['tree']
assert att['branchRefOid']==manifest['head'] and att['pullRefOid']==manifest['head'] and att['checkoutClean'] is True
assert boundary['head']==manifest['head'] and boundary['tree']==manifest['tree'] and boundary['previousWindow']=='W64'
assert boundary['selection']=={'window':'W65','continuationRankStart':503,'continuationRankEnd':527,'remainingQueueRankStart':403,'remainingQueueRankEnd':427,'sourceCount':25,'localeCount':12,'cellCount':300}
assert boundary['previousWindowFinalContinuationRank']==502 and boundary['nextUnselectedContinuationRank']==528
assert boundary['nextUnselectedSourceId']=='src_238c156d69336197'
sources=jl('source-inventory-selection.jsonl'); contexts=jl('caller-contexts.jsonl'); cells=jl('source-current-cells.jsonl')
catalogs=jl('catalog-structure.jsonl'); holds=jl('prior-held-cell-reattestation.jsonl'); excluded=jl('prior-selected-id-exclusions.jsonl')
selection=jl('selection-boundary.jsonl')
prior_boundary=j('prior-window-selection-and-boundary.json')
assert len(sources)==len(contexts)==25 and len(cells)==300 and len(catalogs)==12 and len(holds)==98 and len(excluded)==1607 and len(selection)==27
assert (prior_boundary['repository'],prior_boundary['pullRequest'])==('snapetech-org/slskdN',409)
assert prior_boundary['sourceInventorySha256']==manifest['sourceInventorySha256']
assert hashlib.sha256((I/'prior-window-selection-and-boundary.json').read_bytes()).hexdigest()==manifest['priorBoundaryEvidenceSha256']
assert prior_boundary['selection']['window']=='W64' and prior_boundary['nextUnselectedContinuationRank']==503
assert prior_boundary['nextUnselectedSourceId']==sources[0]['sourceId']
assert [r['continuationRank'] for r in sources]==list(range(503,528))
assert [r['remainingQueueRank'] for r in sources]==list(range(403,428))
assert len({r['sourceId'] for r in sources})==25
assert len({r['sourceId'] for r in excluded})==1607
assert not ({r['sourceId'] for r in sources}&{r['sourceId'] for r in excluded})
assert {r['sourceId'] for r in sources}.issubset({r['sourceId'] for r in selection})
assert Counter(r['boundaryRole'] for r in selection)==Counter({'selected':25,'previous-window-final':1,'next-unselected':1})
assert next(r for r in selection if r['boundaryRole']=='previous-window-final')['continuationRank']==502
next_unselected=next(r for r in selection if r['boundaryRole']=='next-unselected')
assert next_unselected['continuationRank']==528 and next_unselected['sourceId']==boundary['nextUnselectedSourceId']
ordered='3ca04c40ebfed00b93fcd143109fc9d85da941cec30b6cb93f52e431498df6a7'
assert all(r['entryCount']==6176 and r['nonemptyValueCount']==6176 and r['orderedKeySha256']==ordered for r in catalogs)
assert len({r['catalogPath'] for r in catalogs})==12
catalog_by_locale={r['locale']:r for r in catalogs}
source_by_rank={r['continuationRank']:r for r in sources}; caller_by_rank={r['continuationRank']:r for r in contexts}
assert set(source_by_rank)==set(caller_by_rank)==set(range(503,528))
cell_index={(r['continuationRank'],r['locale']):r for r in cells}
assert len(cell_index)==300
mismatch=Counter()
for rank,src in source_by_rank.items():
    assert sha(src['source'].encode())==src['sourceSha256']
    ctx=caller_by_rank[rank]
    assert (ctx['sourceId'],ctx['source'],ctx['sourceSha256'])==(src['sourceId'],src['source'],src['sourceSha256'])
    callers=ctx['callers']
    assert ctx['productionCallerCount']==len(callers)
    for caller in callers:
        assert sha(caller['lineText'].encode())==caller['lineSha256']
        assert sha(canon(caller['context']))==caller['contextSha256']
    ctxsha=sha(canon([c['context'] for c in callers]))
    for locale in manifest['locales']:
        c=cell_index[(rank,locale)]; st=src['source']; target=c['currentTarget']; cat=catalog_by_locale[locale]
        assert (c['sourceId'],c['source'],c['sourceSha256'])==(src['sourceId'],st,src['sourceSha256'])
        assert c['catalogKey']==st and c['locale']==locale
        assert c['catalogPath']==cat['catalogPath'] and c['catalogFileSha256']==cat['sha256'] and c['catalogGitBlob']==cat['gitBlob']
        assert c['callerContextSha256']==ctxsha
        assert c['callerRefs']==[{'path':x['path'],'line':x['line'],'lineSha256':x['lineSha256'],'fileSha256':x['fileSha256'],'gitBlob':x['gitBlob']} for x in callers]
        assert c['containsCandidate'] is False and c['verdict'] is None
        assert sha(st.encode())==c['sourceSha256'] and sha(target.encode())==c['currentTargetSha256']
        assert c['placeholderEvidence']['sourceTokens']==ph(st) and c['placeholderEvidence']['currentTokens']==ph(target)
        assert c['placeholderEvidence']['matches']==(ph(st)==ph(target))
        assert c['markupEvidence']['sourceTags']==tags(st) and c['markupEvidence']['currentTags']==tags(target)
        assert c['markupEvidence']['matches']==(tags(st)==tags(target))
        assert c['sourceNumericTokens']==nums(st) and c['currentNumericTokens']==nums(target)
        assert c['sourceProtectedLiterals']==prot(st) and c['currentProtectedLiterals']==prot(target)
        assert c['protectedLiteralEvidence']['matches']==all(x in target for x in c['sourceProtectedLiterals'])
        mismatch['placeholder']+=not c['placeholderEvidence']['matches']
        mismatch['markup']+=not c['markupEvidence']['matches']
        mismatch['numeric']+=c['sourceNumericTokens']!=c['currentNumericTokens']
        mismatch['protectedLiteral']+=not c['protectedLiteralEvidence']['matches']
assert j('baseline-token-mismatch-summary.json')=={'cellCount':300,'mismatches':dict(mismatch)}
assert all(r['priorDisposition']=='hold' and r['matchesPriorCurrentValue'] and r['status']=='reattested-unchanged' for r in holds)
assert all(sha(r['currentTarget'].encode())==r['currentTargetSha256']==r['priorTargetSha256'] for r in holds)
assert Counter(r['priorWindow'] for r in holds)['W64']==12
assert all(r['currentCatalogPath']==catalog_by_locale[r['locale']]['catalogPath'] for r in holds)
assert manifest['priorHeldCellsReattested']==98 and manifest['allUnavailableIdsBeforeW65']==1607
assert manifest['callerlessSelectedRanks']==[]
print(json.dumps({'pass':True,'window':'W65 ranks 503-527','head':manifest['head'],'tree':manifest['tree'],'sourceCount':25,'cellCount':300,'priorHeldCellsReattested':98,'callerlessSelectedRanks':[],'baselineTokenMismatches':dict(mismatch)},ensure_ascii=False,indent=2))
