#!/usr/bin/env python3
"""Verify independent W34 cross-review rows against the frozen packet."""
import collections, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'independent-review'
def sha(s):return hashlib.sha256(s if isinstance(s,bytes) else s.encode('utf-8')).hexdigest()
def rows(p):return [json.loads(x) for x in (ROOT/p).read_text(encoding='utf-8').splitlines() if x.strip()]
inputs=rows('review-input.jsonl'); plan=rows('crossreview-plan.jsonl'); uncertain=rows('uncertain-ledger.jsonl')
ledger=rows('independent-review/independent-crossreview-window34.jsonl')
summary=json.loads((OUT/'independent-crossreview-summary.json').read_text(encoding='utf-8'))
by_input={r['id']:r for r in inputs}; by_plan={r['id']:r for r in plan}; by_uncertain={r['id']:r for r in uncertain}; by_ledger={r['id']:r for r in ledger}
assert len(inputs)==274 and len(ledger)==274 and len(by_ledger)==274 and set(by_input)==set(by_ledger)
assert len(by_plan)==33 and len(by_uncertain)==1
assert summary['ledgerSha256']==sha((OUT/'independent-crossreview-window34.jsonl').read_bytes())
assert (summary['head'],summary['tree'],summary['sourceSubtreeTree'])==('dc8ed2406a2247600d487df1ae3128ce08cc7faa','9909f5d6e32dfcc78ba53aa0c838f95e9ba246d3','594e56c3f439bad476b1bd57e0de1665c62fa1bb')
for ident,r in by_input.items():
 d=by_ledger[ident]
 assert (d['sourceId'],d['locale'],d['source'],d['sourceSha256'])==(r['sourceId'],r['locale'],r['source'],r['sourceSha256']),ident
 assert (d['currentTarget'],d['currentTargetSha256'])==(r['target'],r['targetSha256']),ident
 assert d['callerPins']==r['sourceCallsites'],ident
 assert sha(d['finalTarget'])==d['finalTargetSha256'],ident
 placeholders=sorted(re.findall(r'\{[^{}]+\}',r['source']))
 assert placeholders==sorted(d['placeholders'])==sorted(re.findall(r'\{[^{}]+\}',d['finalTarget'])),ident
 assert all(lit in d['finalTarget'] for lit in r.get('protectedLiterals',[])),ident
 if ident in by_plan:
  c=by_plan[ident]
  assert (d['candidateTarget'],d['candidateTargetSha256'])==(c['proposedTarget'],c['proposedTargetSha256']),ident
  assert d['independentDisposition'] in ('accept-proposed','refine-proposed'),ident
 elif ident in by_uncertain:
  assert d['independentDisposition']=='keep-current' and d['finalTarget']==r['target'],ident
  assert 'Emplacements d’envoi' in d['rationale'] and 'Emplacements de téléchargement' in d['rationale'],ident
 else:
  assert d['independentDisposition']=='keep-current' and d['finalTarget']==r['target'],ident
 if d['independentDisposition']=='refine-proposed':
  assert ident=='zh-Hant:src_04875bce2d1363bd',ident
  assert d['finalTarget']=='覆疊網路對等方：{count}',ident
counts=collections.Counter(d['independentDisposition'] for d in ledger)
assert counts=={'keep-current':241,'accept-proposed':32,'refine-proposed':1},counts
assert summary['dispositions']==dict(counts)
assert summary['refinedCorrectionRows']==1 and summary['acceptedCorrectionRows']==32
assert summary['keptRows']==241 and summary['heldRows']==0
print(json.dumps({'result':'PASS','rows':len(ledger),'counts':dict(counts),'ledgerSha256':sha((OUT/'independent-crossreview-window34.jsonl').read_bytes())},ensure_ascii=False,indent=2))
