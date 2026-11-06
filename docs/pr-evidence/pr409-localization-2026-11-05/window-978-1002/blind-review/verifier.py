#!/usr/bin/env python3
import argparse,hashlib,json,re,sys
from pathlib import Path
def sha(b): return hashlib.sha256(b).hexdigest()
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x]
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--input-dir',required=True,type=Path); a=ap.parse_args(); p=Path(__file__).resolve().parent
 sums={}
 for line in (p/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
  h,n=line.split('  ',1); sums[n]=h; assert sha((p/n).read_bytes())==h,f'packet checksum mismatch: {n}'
 actual={x.name for x in p.iterdir() if x.is_file() and x.name!='SHA256SUMS.txt'}; assert actual==set(sums)
 att=j(p/'review-attestation.json'); m=j(a.input_dir/'manifest.json')
 assert att['exactHead']==m['head']=='1c2fe3be2c720693cbcb12d377bf1177804f4e77'; assert att['exactTree']==m['tree']=='808501cbc3b6ed873a47d7188189d486f0673f5e'
 assert sha((a.input_dir/'manifest.json').read_bytes())==att['inputManifestSha256']
 for n,h in att['inputFileSha256'].items(): assert sha((a.input_dir/n).read_bytes())==h,f'input binding mismatch: {n}'
 assert (p/'source-caller-bindings.jsonl').read_bytes()==(a.input_dir/'caller-contexts.jsonl').read_bytes()
 cells=jl(a.input_dir/'source-current-cells.jsonl'); sources=jl(a.input_dir/'selected-sources.jsonl'); callers=jl(a.input_dir/'caller-contexts.jsonl'); rows=jl(p/'review-decisions.jsonl')
 assert len(cells)==len(rows)==300 and len(sources)==len(callers)==25
 cm={(x['continuationRank'],x['locale']):x for x in cells}; sm={x['sourceId']:x for x in sources}; bm={x['sourceId']:x for x in callers}; locales=m['locales']; assert len(cm)==300 and len(sm)==len(bm)==25
 keys=set(); counts={'retain':0,'propose':0}
 for r in rows:
  k=(r['continuationRank'],r['locale']); assert k not in keys and k in cm; keys.add(k); c=cm[k]; s=sm[r['sourceId']]; b=bm[r['sourceId']]
  assert r['exactHead']==b['exactHead']==att['exactHead'] and r['exactTree']==b['exactTree']==att['exactTree']
  for f in ('sourceId','sourceIdSha256','source','sourceSha256','continuationRank','remainingQueueRank'): assert r[f]==c[f]==s[f],f'{f} mismatch at {k}'
  for f in ('catalogPath','catalogGitBlob','catalogFileSha256','currentTarget','currentTargetSha256','callerCount','callerContextSha256'): assert r[f]==c[f],f'{f} mismatch at {k}'
  assert r['callerCount']==b['productionCallerCount']>0 and r['callerContextSha256']==b['callerContextSha256'] and r['sourceCallerBindingFile']=='source-caller-bindings.jsonl'
  if r['disposition']=='retain': counts['retain']+=1; assert 'proposedTarget' not in r and 'rationale' not in r; final=c['currentTarget']
  else:
   assert r['disposition']=='propose'; counts['propose']+=1; assert r.get('proposedTarget') and r.get('rationale'); final=r['proposedTarget']
  assert sha(final.encode())==r['finalTargetSha256']; e=c['tokenEvidence']; ph=e['placeholders']['source']; mk=e['markup']['source']; nums=e['numbers']['source']; prot=e['protectedLiterals']['source']
  pht=re.findall(r'\{[^{}]+\}',final); mkt=re.findall(r'<[^>]+>',final); numt=re.findall(r'\d+(?:[.,]\d+)?',final); prt=[x for x in prot if x in final]; miss=[x for x in prot if x not in final]
  calc={'placeholders':{'source':ph,'target':pht,'matches':sorted(ph)==sorted(pht)},'markup':{'source':mk,'target':mkt,'matches':sorted(mk)==sorted(mkt)},'numbers':{'source':nums,'target':numt,'sourcePreserved':all(x in numt for x in nums)},'protectedLiterals':{'source':prot,'target':prt,'missing':miss,'matches':not miss}}
  assert calc==r['finalTokenChecks'] and all([calc['placeholders']['matches'],calc['markup']['matches'],calc['numbers']['sourcePreserved'],calc['protectedLiterals']['matches']]),f'token failure at {k}'
 assert len(keys)==300 and counts=={'retain':240,'propose':60}; assert {r['sourceId'] for r in rows}==set(sm)
 for l in locales: assert sum(r['locale']==l for r in rows)==25
 su=j(p/'review-summary.json'); assert su['dispositionCounts']==counts and su['cellCount']==300
 print(f"PASS: 300 cells; 240 retain, 60 propose; 25 sources × 12 locales; caller bindings and final token checks verified.")
if __name__=='__main__':
 try: main()
 except Exception as e: print(f'FAIL: {e}',file=sys.stderr); raise
