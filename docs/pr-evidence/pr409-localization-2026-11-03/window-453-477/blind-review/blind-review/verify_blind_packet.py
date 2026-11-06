#!/usr/bin/env python3
import hashlib, json, subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
inp=root/'candidate-free-input'
rev=root/'blind-review'
def check(condition,message):
    if not condition: raise SystemExit('FAIL: '+message)
def lines(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x]
def sha(data): return hashlib.sha256(data).hexdigest()
p=subprocess.run(['sha256sum','-c','PACKET-SHA256SUMS.txt'],cwd=inp,text=True,capture_output=True)
check(p.returncode==0,'candidate-free input checksum list')
manifest=json.loads((inp/'manifest.json').read_text(encoding='utf-8'))
summary=json.loads((rev/'summary.json').read_text(encoding='utf-8'))
rows=lines(inp/'source-current-cells.jsonl')
ledger=lines(rev/'blind-ledger.jsonl')
selected=lines(rev/'selected-blind-proposals.jsonl')
check(len(rows)==300 and len(ledger)==300,'expected 300 input and ledger rows')
check(len({(r['sourceId'],r['locale']) for r in ledger})==300,'ledger cell uniqueness')
check({r['continuationRank'] for r in ledger}==set(range(453,478)),'rank coverage')
input_map={(r['sourceId'],r['locale']):r for r in rows}
ledger_map={(r['sourceId'],r['locale']):r for r in ledger}
check(set(input_map)==set(ledger_map),'ledger/input cell coverage')
for key,src in input_map.items():
    out=ledger_map[key]
    for field in ['continuationRank','source','sourceSha256','currentTarget','currentTargetSha256','callerContextSha256','catalogPath','catalogFileSha256']:
        check(out[field]==src[field],f'input lineage mismatch {key} {field}')
    check(sha(src['currentTarget'].encode('utf-8'))==src['currentTargetSha256'],f'input current target hash mismatch {key}')
    chosen=out['proposedTarget'] if out['proposedTarget'] is not None else out['currentTarget']
    check(all(t in chosen for t in src['placeholderEvidence']['sourceTokens']),f'placeholder loss {key}')
    check(all(t in chosen for t in src['sourceNumericTokens']),f'numeric token loss {key}')
    check(all(t in chosen for t in src['sourceProtectedLiterals']),f'protected literal loss {key}')
    check(all(t in chosen for t in src['markupEvidence']['sourceTags']),f'markup loss {key}')
    if src['continuationRank']==468 and out['proposedTarget'] is not None:
        check('OCR' in chosen and chosen.endswith('('),f'OCR prefix/punctuation lost {key}')
held=[r for r in ledger if r['continuationRank']==476]
check(len(held)==12 and all(r['disposition']=='hold' and r['proposedTarget'] is None for r in held),'rank 476 holds')
check(all(input_map[(r['sourceId'],r['locale'])]['currentTarget']==r['currentTarget'] for r in held),'rank 476 current values changed')
check(len(selected)==69,'selected proposal count')
check({(r['sourceId'],r['locale']) for r in selected}=={(r['sourceId'],r['locale']) for r in ledger if r['disposition'] in ('correction','refinement')},'selected proposal index')
counts={}
for r in ledger: counts[r['disposition']]=counts.get(r['disposition'],0)+1
check(counts=={'accept_current':219,'refinement':16,'correction':53,'hold':12},f'counts mismatch {counts}')
check(summary['counts']==counts,'summary counts mismatch')
check(summary['head']==manifest['head'] and summary['tree']==manifest['tree'],'head/tree mismatch')
check(summary['candidateFreeManifestJsonSha256']==sha((inp/'manifest.json').read_bytes()),'manifest hash mismatch')
check(summary['candidateFreeChecksumListSha256']==sha((inp/'PACKET-SHA256SUMS.txt').read_bytes()),'checksum-list hash mismatch')
check(manifest['candidateFree'] is True and manifest['cellCount']==300,'candidate-free manifest')
check(manifest['callerlessSelectedRanks']==[476],'callerless hold rank')
structure=lines(inp/'catalog-structure.jsonl')
check(len(structure)==12 and all(x['entryCount']==6176 and x['orderedKeySha256']==manifest['orderedCatalogKeySha256'] for x in structure),'catalog structure evidence')
prior=json.loads((inp/'prior-rank-disposition-reattestation-summary.json').read_text(encoding='utf-8'))
check(prior['priorHeldCellCount']==72,'prior held-cell reattestation count')
check(len(lines(inp/'prior-rank-disposition-reattestation.jsonl'))==72,'prior held-cell rows')
print('PASS: 300 cells, 69 proposals (53 corrections, 16 refinements), 219 accepts, 12 rank-476 holds; tokens, lineage, ordered catalog evidence and checksums verified.')
