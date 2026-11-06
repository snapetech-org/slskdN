import collections,hashlib,json
from pathlib import Path
TASK=Path('/home/keith/Documents/code/task-scratch/slskdn-pr409-w74-728-752-20261104')
I=TASK/'candidate-free/input'
sha=lambda b:hashlib.sha256(b).hexdigest()
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
lines=lambda p:[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
m=load(I/'manifest.json')
assert m['candidateFree'] is True and m['head']=='70e5beffd5cd8d68b8aedffa5c85d16e2cc19b3f' and m['tree']=='14620c63bee971428fa1cd6cf1f4e944b86056a7'
for row in (I/'PACKET-SHA256SUMS.txt').read_text().splitlines():
 h,name=row.split('  ',1); assert sha((I/name).read_bytes())==h,name
for f in m['files']:
 raw=(I/f['path']).read_bytes(); assert len(raw)==f['bytes'] and sha(raw)==f['sha256'],f['path']
sel=lines(I/'source-inventory-selection.jsonl'); cells=lines(I/'source-current-cells.jsonl'); inv=lines(I/'source-inventory-pinned.jsonl')
ctx=lines(I/'caller-contexts.jsonl'); holds=lines(I/'prior-held-cell-reattestation-hash-only.jsonl'); ex=lines(I/'prior-selected-id-exclusions-hash-only.jsonl')
res=lines(I/'prior-hold-resolution-history-hash-only.jsonl'); cats=lines(I/'catalog-structure.jsonl')
assert len(inv)==6176 and sha((I/'source-inventory-pinned.jsonl').read_bytes())==m['sourceInventorySha256']
assert len(sel)==25 and [r['continuationRank'] for r in sel]==list(range(728,753)) and [r['remainingQueueRank'] for r in sel]==list(range(628,653))
assert len(cells)==300 and len({(r['sourceId'],r['locale']) for r in cells})==300
assert len(cats)==12 and all(r['entryCount']==6176 and r['nonemptyValueCount']==6176 for r in cats)
assert len(holds)==259 and all(r['matchesPriorCurrentValue'] for r in holds)
assert all(not any(k in r for k in ('source','sourceText','currentTarget','target','proposedTarget')) for r in holds)
assert len(ex)==1832 and len({r['sourceId'] for r in ex})==1832
assert len(res)==13 and all(not any(k in r for k in ('source','sourceText','currentTarget','target','resolvedTarget')) for r in res)
assert len(ctx)==25 and {r['sourceId'] for r in ctx}=={r['sourceId'] for r in sel}
assert all(r['containsCandidate'] is False and r['verdict'] is None for r in cells)
assert all(r['placeholderEvidence']['matches'] and r['markupEvidence']['matches'] and r['numericTokensPreserved'] for r in cells)
assert m['proposedTargetsIncluded'] is False and m['reviewDecisionsIncluded'] is False
print(json.dumps({'result':'PASS','head':m['head'],'tree':m['tree'],'sourceCount':len(sel),'cellCount':len(cells),'catalogs':len(cats),'catalogKeysPerLocale':6176,'priorHoldsHashOnly':len(holds),'priorIdsHashOnly':len(ex),'historicalResolutionsTextFree':len(res),'checksums':len((I/'PACKET-SHA256SUMS.txt').read_text().splitlines())},sort_keys=True))
