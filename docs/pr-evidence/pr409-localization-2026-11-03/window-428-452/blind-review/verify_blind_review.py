#!/usr/bin/env python3
import pathlib,json,hashlib,re,collections
root=pathlib.Path(__file__).resolve().parent
inp=root/'candidate-free-input'
def sha(b): return hashlib.sha256(b).hexdigest()
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
for line in (root/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
 if not line.strip(): continue
 digest,rel=line.split(None,1); path=root/rel.lstrip('* ')
 assert path.is_file() and sha(path.read_bytes())==digest,path
prov=json.loads((root/'provenance.json').read_text(encoding='utf-8'))
seal=json.loads((root/'seal.json').read_text(encoding='utf-8'))
summary=json.loads((root/'summary.json').read_text(encoding='utf-8'))
manifest=json.loads((inp/'manifest.json').read_text(encoding='utf-8'))
att=json.loads((inp/'head-tree-attestation.json').read_text(encoding='utf-8'))
assert prov['candidateFreeOnly'] and prov['primaryReviewNotRead'] and prov['priorCandidateProposalsNotRead'] and prov['bodyNotUsed']
assert prov['candidateFreeInputChecksumListSha256']=='005097b25bd89a302b4caebd4478013fbc5b239c210f841613b5edb6d706660b'
assert prov['candidateFreeInputManifestSha256']=='bb5c8dd36775fa59fe17335ed8260498484d40adf89b6e565386d92dd5d75bd4'
assert manifest['head']==prov['head'] and manifest['tree']==prov['tree']
assert att['head']==prov['head'] and att['tree']==prov['tree']
for name,digest in prov['candidateFreeInputUsedFiles'].items(): assert sha((inp/name).read_bytes())==digest,name
currows=rows(inp/'source-current-cells.jsonl')
contexts={x['continuationRank']:x for x in rows(inp/'caller-contexts.jsonl')}
ledger=rows(root/'blind-ledger.jsonl')
assert len(currows)==300 and len(ledger)==300 and len(contexts)==25
cur={(x['continuationRank'],x['locale']):x for x in currows}
rev={(x['continuationRank'],x['locale']):x for x in ledger}
assert len(cur)==300 and len(rev)==300 and set(cur)==set(rev)
ph=re.compile(r'\{[^{}]+\}'); tag=re.compile(r'</?[A-Za-z][^>]*>'); num=re.compile(r'(?<![A-Za-z0-9_])\d+(?:[.,]\d+)?(?![A-Za-z0-9_])')
counts=collections.Counter(); kinds=collections.Counter()
for ident,c in cur.items():
 r=rev[ident]; ctx=contexts[ident[0]]
 assert r['head']==prov['head'] and r['tree']==prov['tree']
 assert r['sourceId']==c['sourceId'] and r['source']==c['source'] and r['sourceSha256']==c['sourceSha256']
 assert r['currentTarget']==c['currentTarget'] and r['currentTargetSha256']==c['currentTargetSha256']
 assert r['callerRefs']==c['callerRefs'] and r['callerCount']==ctx['productionCallerCount'] and r['callerContextSha256']==c['callerContextSha256']
 assert sha(r['target'].encode('utf-8'))==r['targetSha256']
 assert ph.findall(r['target'])==ph.findall(r['source'])
 assert tag.findall(r['target'])==tag.findall(r['source'])
 assert num.findall(ph.sub('',r['target']))==num.findall(ph.sub('',r['source']))
 assert all(r['target'].count(token)==r['source'].count(token) for token in c['sourceProtectedLiterals'])
 assert r['placeholderCheck']['matchesSource'] and r['markupCheck']['matchesSource'] and r['numericCheck']['matchesSource'] and r['protectedLiteralCheck']['targetMatchesSource']
 if r['decision']=='retain': assert r['target']==r['currentTarget'] and r['proposalKind']=='accept-current'
 if r['decision']=='hold': assert r['target']==r['currentTarget'] and ctx['productionCallerCount']==0 and not c['callerRefs'] and r['proposalKind']=='callerless-hold'
 if r['decision']=='propose': assert r['target']!=r['currentTarget'] and r['proposalKind'] in ('correction','refinement')
 assert r['decision'] in ('propose','retain','hold')
 counts[r['decision']]+=1
 if r['decision']=='propose': kinds[r['proposalKind']]+=1
holds=[r for r in ledger if r['decision']=='hold']
expected_holds={(rank,loc) for rank in (438,452) for loc in manifest['locales']}
assert len(holds)==24 and {(r['continuationRank'],r['locale']) for r in holds}==expected_holds
assert counts==collections.Counter({'propose':68,'retain':208,'hold':24})
assert summary['decisionCounts']==dict(counts) and summary['proposalKinds']==dict(kinds)
assert summary['reviewedCells']==300 and summary['holdsByRank']=={'438':12,'452':12}
for name,digest in seal['sealedArtifacts'].items(): assert sha((root/name).read_bytes())==digest,name
print('blind review verified: 300 cells; 68 proposals; 208 retains; 24 callerless holds (ranks 438 and 452); hashes and token invariants pass')
