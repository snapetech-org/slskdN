#!/usr/bin/env python3
import argparse, hashlib, json, re, subprocess, sys, unicodedata
from pathlib import Path

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fail(msg): raise SystemExit("FAIL: "+msg)
def ph(text): return sorted(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',text))
def markup(text): return sorted(re.findall(r'</?[A-Za-z][^>]*>',text))
def nums(text):
 out=[]
 for match in re.findall(r'\d+',text): out.append(''.join(str(unicodedata.digit(ch)) if ch.isdigit() else ch for ch in match))
 return out
def literals(text):
 out=set(re.findall(r'\b[A-Z][A-Z0-9]{1,}\b',text))
 out.update(t for t in ('slskdN','Tor','Wishlist','Chromaprint') if t in text)
 return sorted(out)
ap=argparse.ArgumentParser(); ap.add_argument('--input',required=True); args=ap.parse_args(); inp=Path(args.input).resolve(); out=Path(__file__).resolve().parent
check=subprocess.run(['sha256sum','-c','PACKET-SHA256SUMS.txt'],cwd=inp,text=True,capture_output=True)
if check.returncode: fail('candidate-free packet checksum failure: '+check.stderr)
base={}
for line in (inp/'source-current-cells.jsonl').read_text(encoding='utf-8').splitlines():
 r=json.loads(line); base[(r['continuationRank'],r['locale'])]=r
ledger=[json.loads(s) for s in (out/'blind-decisions.jsonl').read_text(encoding='utf-8').splitlines()]
if len(base)!=300 or len(ledger)!=300: fail('cell count is not 300')
if len({(x['continuationRank'],x['locale']) for x in ledger})!=300: fail('duplicate ledger cell')
for x in ledger:
 k=(x['continuationRank'],x['locale'])
 if k not in base: fail('unknown cell '+str(k))
 r=base[k]
 for f in ('sourceId','catalogKey','source','sourceSha256','currentTarget','currentTargetSha256','callerContextSha256','sourceProtectedLiterals','currentProtectedLiterals','missingProtectedLiterals'):
  if x[f]!=r[f]: fail(f'input pin mismatch {k} {f}')
 if x['disposition'] not in ('accept','revise'): fail('invalid disposition '+str(k))
 if (x['disposition']=='revise') != (x['proposedTarget'] is not None): fail('proposal/disposition mismatch '+str(k))
 if x['proposedTarget'] is not None:
  if x['sourceTokens']!=x['currentTargetTokens']: fail('current token mismatch '+str(k))
  if x['sourceMarkupTags']!=x['currentMarkupTags']: fail('current markup mismatch '+str(k))
  if x['sourceNumericTokens']!=x['currentNumericTokens']: fail('current numeric mismatch '+str(k))
  if x['sourceProtectedLiterals']!=x['currentProtectedLiterals'] and not (x['continuationRank'] in (757,759) and x['sourceProtectedLiterals']==['Wishlist'] and not x['currentProtectedLiterals']): fail('unadjudicated protected literal mismatch '+str(k))
  proposed=x['proposedTarget']
  if ph(x['source'])!=ph(proposed): fail('proposed placeholder parity mismatch '+str(k))
  if markup(x['source'])!=markup(proposed): fail('proposed markup parity mismatch '+str(k))
  if nums(x['source'])!=nums(proposed): fail('proposed numeric parity mismatch '+str(k))
  prop_lits=literals(proposed); src_lits=literals(x['source'])
  if prop_lits!=src_lits and not (x['continuationRank'] in (757,759) and src_lits==['Wishlist'] and not prop_lits): fail('proposed protected literal parity mismatch '+str(k))
# Baseline missing-token assessments must exactly cover candidate-free mismatches.
ass=json.loads((out/'protected-literal-assessments.json').read_text(encoding='utf-8'))['assessments']
expected={(r['continuationRank'],r['locale']) for r in base.values() if r['missingProtectedLiterals']}
actual={(r['continuationRank'],r['locale']) for r in ass if r['decision']=='accept-localized-feature-name'}
if len(expected)!=23 or actual!=expected: fail('protected literal assessment coverage mismatch')
if sum(x['disposition']=='revise' for x in ledger)!=44: fail('revision count mismatch')
print(json.dumps({'result':'PASS','window':'W75','sourceCount':25,'localeCount':12,'cellCount':len(ledger),'accept':sum(x['disposition']=='accept' for x in ledger),'revise':sum(x['disposition']=='revise' for x in ledger),'holds':0,'baselineProtectedLiteralMismatches':23,'independentlyAcceptedLocalizedNameExceptions':23,'candidateFreeChecksumFiles':len((inp/'PACKET-SHA256SUMS.txt').read_text().splitlines()),'ledgerSha256':sha(out/'blind-decisions.jsonl'),'inputManifestSha256':sha(inp/'manifest.json')},ensure_ascii=False,indent=2))
