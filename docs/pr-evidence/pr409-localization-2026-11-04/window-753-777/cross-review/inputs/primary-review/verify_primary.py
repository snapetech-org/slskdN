#!/usr/bin/env python3
import argparse, collections, hashlib, json, pathlib, re, subprocess, sys, unicodedata
ROOT=pathlib.Path(__file__).resolve().parent
INPUT=ROOT.parent.parent/'candidate-free'/'input'
HEAD='99d6afbfb8cca4dccc018e72c01950bc304240db'
TREE='f21cb5cde009ac35f5531ddc40612821aee6f471'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
def fail(s): raise SystemExit('FAIL: '+s)
def sha(b): return hashlib.sha256(b).hexdigest()
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def ph(s): return re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s)
def tags(s): return re.findall(r'</?[A-Za-z][^>]*>',s)
def nums(s):
 out=[]
 for m in re.findall(r'\d+',s): out.append(''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in m))
 return out

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True); a=ap.parse_args()
 iv=subprocess.check_output([sys.executable,str(INPUT/'verify_input.py'),'--repo',a.repo],text=True)
 ivo=json.loads(iv)
 if ivo.get('result')!='PASS' or ivo.get('head')!=HEAD or ivo.get('tree')!=TREE: fail('candidate-free verifier or pinned head/tree did not pass')
 cells=jl(INPUT/'source-current-cells.jsonl'); ledger=jl(ROOT/'primary-review.jsonl'); corrections=jl(ROOT/'corrections.jsonl'); holds=jl(ROOT/'holds-hash-only.jsonl')
 if len(cells)!=300 or len(ledger)!=300: fail('expected 300 input and review rows')
 inp={(r['continuationRank'],r['locale']):r for r in cells}; out={(r['continuationRank'],r['locale']):r for r in ledger}
 if len(inp)!=300 or len(out)!=300 or set(inp)!=set(out): fail('cell uniqueness/coverage mismatch')
 counts=collections.Counter(); correct_rows=[]; hold_rows=[]; proposal_mismatches=0; wishlist_flags=0; wishlist_false_positives=0
 for k,src in inp.items():
  rank,locale=k; row=out[k]; counts[row.get('disposition')]+=1
  if row.get('head')!=HEAD or row.get('tree')!=TREE: fail(f'pin mismatch at {rank}/{locale}')
  for f in ('continuationRank','remainingQueueRank','sourceId','sourceSha256','locale','catalogPath','catalogFileSha256','catalogGitBlob','currentTargetSha256','callerContextSha256','callerRefs'):
   if row.get(f)!=src.get(f): fail(f'input reference mismatch {f} at {rank}/{locale}')
  if not src.get('callerRefs') or row.get('productionCallerCount',0)<1: fail(f'callerless cell at {rank}/{locale}')
  if rank==754:
   if row.get('disposition')!='hold': fail(f'rank 754 must stay held at {locale}')
   for f in ('source','catalogKey','currentTarget','target'):
    if f in row: fail(f'text present in hold row ({f}) at {rank}/{locale}')
   if not row.get('holdReason') or row.get('confidence') not in ('high','moderate','low'): fail(f'hold reason missing at {rank}/{locale}')
   hold_rows.append(row); continue
  for f in ('source','catalogKey','currentTarget'):
   if row.get(f)!=src.get(f): fail(f'text/current input mismatch {f} at {rank}/{locale}')
  if sha(row['source'].encode())!=row['sourceSha256'] or sha(row['currentTarget'].encode())!=row['currentTargetSha256']: fail(f'text hash mismatch at {rank}/{locale}')
  if not row.get('rationale') or row.get('confidence') not in ('high','moderate','low'): fail(f'rationale/confidence missing at {rank}/{locale}')
  tc=row.get('tokenCheck',{})
  wishlist_exception=rank in (757,759) and 'Wishlist' in src.get('sourceProtectedLiterals',[])
  if wishlist_exception:
   wishlist_flags+=1
   if not src.get('protectedLiteralEvidence',{}).get('matches'): wishlist_false_positives+=1
   if tc.get('protectedLiteralDisposition')!='localized-feature-label' or not tc.get('protectedLiteralRationale'): fail(f'Wishlist false-positive exception missing at {rank}/{locale}')
   if tc.get('currentCellTokenEvidence',{}).get('protectedLiterals') is not True: fail(f'Wishlist exception not accounted for at {rank}/{locale}')
  elif not all(tc.get('currentCellTokenEvidence',{}).values()): fail(f'unresolved baseline token mismatch at {rank}/{locale}')
  if row['disposition']=='accept-current':
   if row.get('target') is not None: fail(f'accept-current proposes target at {rank}/{locale}')
   if tc.get('proposedTargetCheck') is not None: fail(f'accept-current proposal token check at {rank}/{locale}')
  elif row['disposition']=='correct':
   target=row.get('target')
   if not isinstance(target,str) or not target: fail(f'missing correction at {rank}/{locale}')
   check=tc.get('proposedTargetCheck') or {}
   ph_ok=collections.Counter(check.get('placeholderTokens',[]))==collections.Counter(ph(row['source'])) and check.get('placeholderParity') is True
   tag_ok=collections.Counter(check.get('markupTags',[]))==collections.Counter(tags(row['source'])) and check.get('markupParity') is True
   num_ok=all(nums(target).count(t)>=nums(row['source']).count(t) for t in set(nums(row['source'])))
   prot_ok=all(x in target for x in src.get('sourceProtectedLiterals',[]))
   if not (ph_ok and tag_ok and num_ok and prot_ok and check.get('numericTokensPreserved') is True and check.get('protectedLiteralsPreserved') is True):
    proposal_mismatches+=1; fail(f'proposal token mismatch at {rank}/{locale}')
   for x in ('source','currentTarget','target'):
    if not row.get(x): fail(f'correction text missing {x} at {rank}/{locale}')
   if rank==767 and locale=='hi' and '83d91898-...' not in target: fail('Hindi MBID example not preserved exactly')
   correct_rows.append(row)
  else: fail(f'unknown disposition at {rank}/{locale}')
 if counts!=collections.Counter({'accept-current':268,'correct':20,'hold':12}): fail(f'disposition counts mismatch: {counts}')
 if wishlist_flags!=24 or wishlist_false_positives!=23: fail(f'localized Wishlist exception counts mismatch: exceptionCells={wishlist_flags}, falsePositiveCells={wishlist_false_positives}')
 if proposal_mismatches: fail(f'{proposal_mismatches} proposal token mismatches')
 if corrections!=correct_rows: fail('corrections extract differs from ledger')
 if holds!=hold_rows: fail('hash-only hold extract differs from ledger')
 sr=json.loads((ROOT/'source-rewrite-recommendations.json').read_text())
 if sr!={'schemaVersion':1,'recommendations':[]}: fail('unexpected source rewrite recommendation')
 before=json.loads((ROOT/'live-before.json').read_text()); after=json.loads((ROOT/'live-after.json').read_text())
 for x in (before,after):
  if x.get('repository')!='snapetech-org/slskdN' or x.get('pullRequest')!=409 or x.get('state')!='OPEN' or x.get('draft') is not True or x.get('merged') is not False: fail('PR state is not OPEN/DRAFT')
  for f,v in [('headRefOid',HEAD),('branchRefOid',HEAD),('pullRefOid',HEAD),('headRefName','codex/slskdn-oidc-tooltip-localization-20261030'),('baseRefName','main'),('baseRefOid','f25d263a2a7cdb2c8f76c40c346cb10f749a9356')]:
   if x.get(f)!=v: fail(f'live PR ref mismatch {f}')
 if any(before.get(k)!=after.get(k) for k in set(before)|set(after) if k!='attestedUtc'): fail('PR state/ref changed during primary window')
 summary=json.loads((ROOT/'summary.json').read_text())
 if summary.get('dispositions')!={'accept-current':268,'correct':20,'hold':12} or summary.get('inputManifestSha256')!=sha((INPUT/'manifest.json').read_bytes()) or summary.get('inputChecksumListSha256')!=sha((INPUT/'PACKET-SHA256SUMS.txt').read_bytes()) or summary.get('selectionBoundarySha256')!=sha((INPUT/'selection-boundary.jsonl').read_bytes()): fail('summary/provenance mismatch')
 manifest=json.loads((ROOT/'manifest.json').read_text())
 if manifest.get('head')!=HEAD or manifest.get('tree')!=TREE or manifest.get('sourceCount')!=25 or manifest.get('cellCount')!=300: fail('manifest pin/coverage mismatch')
 entries={x['path']:x for x in manifest['files']}
 if 'manifest.json' in entries or 'SHA256SUMS.txt' in entries: fail('recursive manifest inventory')
 for n,e in entries.items():
  p=ROOT/n
  if not p.is_file() or p.stat().st_size!=e['bytes'] or sha(p.read_bytes())!=e['sha256']: fail('manifest file digest mismatch '+n)
 sums={}
 for l in (ROOT/'SHA256SUMS.txt').read_text().splitlines():
  if l.strip():
   h,n=l.split('  ',1); sums[n]=h
 if set(sums)!=set(entries)|{'manifest.json'}: fail('checksum inventory mismatch')
 for n,h in sums.items():
  if not (ROOT/n).is_file() or sha((ROOT/n).read_bytes())!=h: fail('checksum mismatch '+n)
 print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'sourceCount':25,'localeCount':12,'cellCount':300,'acceptCurrent':counts['accept-current'],'correct':counts['correct'],'textFreeHolds':counts['hold'],'callerlessCells':0,'localizedWishlistCells':wishlist_flags,'localizedWishlistBaselineFalsePositivesExplained':wishlist_false_positives,'proposalTokenMismatches':proposal_mismatches,'inputVerifier':'PASS','livePR':'OPEN/DRAFT/CLEAN at pinned head','checksums':len(sums)},ensure_ascii=False))
if __name__=='__main__': main()
