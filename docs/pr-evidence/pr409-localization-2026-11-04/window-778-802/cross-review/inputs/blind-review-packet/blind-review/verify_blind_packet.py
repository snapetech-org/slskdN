#!/usr/bin/env python3
import argparse,hashlib,json,re
from pathlib import Path

def digest(b): return hashlib.sha256(b).hexdigest()
def textsha(s): return digest(s.encode('utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x]
def fail(s): raise SystemExit('FAIL: '+s)
def sums(folder,path):
 for line in path.read_text(encoding='utf-8').splitlines():
  if not line.strip(): continue
  h,rel=line.split('  ',1); f=folder/rel
  if not f.is_file() or digest(f.read_bytes())!=h: fail('checksum mismatch: '+str(f))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--packet-root',type=Path,default=Path(__file__).resolve().parent.parent);root=ap.parse_args().packet_root.resolve();cf=root/'candidate-free';out=root/'blind-review'
 sums(root,root/'SHA256SUMS.txt');sums(out,out/'SHA256SUMS.txt')
 manifest=json.loads((cf/'manifest.json').read_text());meta=json.loads((out/'review-packet.json').read_text());inputs=jl(cf/'source-current-cells.jsonl');dec=jl(out/'review-cells.jsonl');callers={x['sourceId']:x for x in jl(cf/'caller-contexts.jsonl')}
 if len(inputs)!=300 or len(dec)!=300:fail('expected exactly 300 cells')
 ix={(x['sourceId'],x['locale']):x for x in inputs};seen=set();counts={'keep':0,'propose':0,'hold':0}
 for d in dec:
  k=(d['sourceId'],d['locale'])
  if k in seen or k not in ix:fail('duplicate/unmatched cell '+str(k))
  seen.add(k);c=ix[k];ctx=callers[d['sourceId']]
  for f in ('continuationRank','remainingQueueRank','sourceSha256','currentTargetSha256','callerContextSha256','catalogPath','catalogFileSha256','catalogGitBlob'):
   if d.get(f)!=c.get(f):fail('binding mismatch '+str(k)+' '+f)
  if d['sourceSha256']!=textsha(c['source']) or d['currentTargetSha256']!=textsha(c['currentTarget']):fail('source/target hash mismatch '+str(k))
  cl=ctx['productionCallerCount']==0
  if d.get('productionCallerCount')!=ctx['productionCallerCount']:fail('caller count mismatch '+str(k))
  if cl:
   if d.get('disposition')!='hold' or d.get('sourceTextIncluded') is not False or d.get('currentTargetIncluded') is not False or d.get('proposalIncluded') is not False:fail('callerless cell is not text-free hold '+str(k))
   if any(f in d for f in ('sourceText','currentTarget','proposal','recommendedTarget')):fail('callerless text leaked '+str(k))
  else:
   if d.get('sourceTextIncluded') is not True or d.get('currentTargetIncluded') is not True or d.get('sourceText')!=c['source'] or d.get('currentTarget')!=c['currentTarget']:fail('cell text mismatch '+str(k))
   disp=d.get('disposition')
   if disp=='keep':
    if d.get('recommendedTarget')!=c['currentTarget'] or d.get('recommendedTargetSha256')!=c['currentTargetSha256'] or 'proposal' in d:fail('keep mismatch '+str(k))
   elif disp=='propose':
    p=d.get('proposal')
    if not isinstance(p,str) or not p or d.get('proposalSha256')!=textsha(p) or d.get('proposalIncluded') is not True:fail('bad proposal '+str(k))
    if d.get('sourceProtectedLiterals')!=c['sourceProtectedLiterals']:fail('protected-literal binding missing '+str(k))
    for lit in c['sourceProtectedLiterals']:
     if lit not in p:fail('proposal lost protected literal '+str(k))
    if sorted(re.findall(r'\{[^{}]+\}|%[^%]+%|<[^>]+>',p))!=sorted(c['placeholderEvidence']['sourceTokens']):fail('placeholder mismatch '+str(k))
    for tok in c['sourceNumericTokens']:
     if not re.search(r'(?<!\d)'+re.escape(tok)+r'(?!\d)',p):fail('numeric token mismatch '+str(k))
   elif disp!='hold':fail('bad disposition '+str(k))
  if not d.get('rationale'):fail('missing rationale '+str(k))
  counts[d['disposition']]+=1
 if seen!=set(ix):fail('incomplete cell coverage')
 if counts!=meta['counts']:fail('count mismatch')
 src=jl(out/'review-sources.jsonl')
 if len(src)!=25:fail('expected 25 source rows')
 for s in src:
  ctx=callers[s['sourceId']]
  if ctx['productionCallerCount']==0:
   if s.get('sourceTextIncluded') is not False or s.get('callerRefsIncluded') is not False or 'sourceText' in s or 'callers' in s:fail('callerless source text leaked')
  elif s.get('sourceText')!=ctx['source'] or s.get('callers')!=ctx['callers']:fail('caller evidence mismatch '+s['sourceId'])
 inp=(cf/'prior-held-cell-reattestation-hash-only.jsonl').read_bytes();outp=(out/'prior-held-cells-hash-only.jsonl').read_bytes()
 if inp!=outp or len(outp.splitlines())!=meta['priorHeldCellsPreserved']:fail('prior holds not preserved')
 for line in outp.decode().splitlines():
  r=json.loads(line)
  if r.get('sourceTextIncluded') is not False or r.get('targetTextIncluded') is not False:fail('prior hold is not text-free')
 if manifest.get('head')!=meta['inputHead'] or manifest.get('tree')!=meta['inputTree']:fail('head/tree mismatch')
 print('PASS: 300/300 cells, source/current/caller/catalog bindings, callerless text-free holds, proposal hashes and tokens, prior holds, and SHA256 manifests verified.')
 print('counts='+json.dumps(counts,sort_keys=True))
if __name__=='__main__':main()
