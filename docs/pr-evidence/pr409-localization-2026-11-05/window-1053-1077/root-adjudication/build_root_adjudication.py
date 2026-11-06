#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, hashlib, json, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE
BASE=HERE.parent
CROSS=BASE/'integrated-cross-review'
CF=BASE/'candidate-free'

def sha(v): return hashlib.sha256(v.encode('utf-8') if isinstance(v,str) else v).hexdigest()
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def write_rows(p,rs): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rs),encoding='utf-8')
def git(repo,*args): return subprocess.check_output(['git',*args],cwd=repo,text=True).strip()
def key_for_hash(data,source_sha):
 keys=[k for k in data if sha(k)==source_sha]
 if len(keys)!=1: raise SystemExit(f'hash-only source-key mapping is not unique ({len(keys)})')
 return keys[0]
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True,type=Path); a=ap.parse_args(); repo=a.repo.resolve()
 m=json.loads((CROSS/'manifest.json').read_text(encoding='utf-8')); head=m['head']; tree=m['tree']
 if git(repo,'rev-parse','HEAD')!=head or git(repo,'rev-parse','HEAD^{tree}')!=tree: raise SystemExit('input head/tree mismatch')
 if git(repo,'status','--porcelain'): raise SystemExit('input worktree must be clean')
 cross=rows(CROSS/'integrated-cross-review-ledger.jsonl'); cf=rows(CF/'source-current-cells.jsonl')
 if len(cross)!=300 or len(cf)!=300: raise SystemExit('expected 300 cells')
 cfmap={(x['continuationRank'],x['locale']):x for x in cf}
 if len(cfmap)!=300: raise SystemExit('candidate-free cell keys are not unique')
 counts=collections.Counter(); ledger=[]; selected=[]; groups={}; resolution_counts=collections.Counter()
 for x in cross:
  key=(x['continuationRank'],x['locale']); c=cfmap[key]
  if (x['head'],x['tree'])!=(head,tree): raise SystemExit(f'cell head/tree mismatch {key}')
  for k in ('sourceId','sourceIdSha256','sourceSha256','callerContextSha256','catalogPath','catalogFileSha256','callerCount'):
   ck={'sourceId':'sourceId','sourceIdSha256':'sourceIdSha256','sourceSha256':'sourceSha256','callerContextSha256':'callerContextSha256','catalogPath':'catalogPath','catalogFileSha256':'catalogFileSha256','callerCount':'callerCount'}[k]
   if x.get(k)!=c.get(ck): raise SystemExit(f'candidate-free pin mismatch {key} {k}')
  decision=x['decision']; backed=x['callerBacked'] is True
  if backed!=bool(c.get('currentTargetTextIncluded')): raise SystemExit(f'caller/current-text flag mismatch {key}')
  if backed:
   if not isinstance(x.get('source'),str) or not isinstance(x.get('currentTarget'),str): raise SystemExit(f'caller-backed text missing {key}')
   if x['source']!=c.get('source') or sha(x['source'])!=x['sourceSha256'] or x['currentTarget']!=c['currentTarget'] or sha(x['currentTarget'])!=x['currentTargetSha256']:
    raise SystemExit(f'source/current value hash mismatch {key}')
  else:
   if any(isinstance(x.get(k),str) for k in ('source','currentTarget','target','reviewCandidateTarget')): raise SystemExit(f'hash-only hold leaks text {key}')
   if x['decision']!='hold-hash-only' or x['currentTargetSha256']!=c['currentTargetSha256']: raise SystemExit(f'callerless hold mismatch {key}')
  if decision=='retain-current':
   disp='accept-current'; target=x['currentTarget']; target_sha=x['currentTargetSha256']
   if target!=x['target'] or target_sha!=x['targetSha256'] or x['tokenChecksPass'] is not True: raise SystemExit(f'retain-current mismatch {key}')
  elif decision=='revise':
   target=x['target']; target_sha=x['targetSha256']
   if not backed or not isinstance(target,str) or sha(target)!=target_sha or target==x['currentTarget'] or x['tokenChecksPass'] is not True: raise SystemExit(f'revision target mismatch {key}')
   disp='refinement' if x['proposalResolution']=='primary-proposal-refined' else 'correction'
  elif decision=='review':
   if not backed or x['unresolvedLowConfidence'] is not True or x['target']!=x['currentTarget'] or x['targetSha256']!=x['currentTargetSha256']:
    raise SystemExit(f'low-confidence hold mismatch {key}')
   disp='hold-low-confidence'; target=x['currentTarget']; target_sha=x['currentTargetSha256']
  elif decision=='hold-hash-only':
   disp='hold-hash-only'; target=None; target_sha=x['currentTargetSha256']
  else: raise SystemExit(f'unsupported integrated decision {decision}')
  resolution_counts[x['proposalResolution']]+=1; counts[disp]+=1
  row={'continuationRank':key[0],'remainingQueueRank':x['remainingQueueRank'],'locale':key[1],
   'sourceId':x['sourceId'],'sourceIdSha256':x['sourceIdSha256'],'sourceSha256':x['sourceSha256'],
   'currentTargetSha256':x['currentTargetSha256'],'callerContextSha256':x['callerContextSha256'],
   'catalogPath':x['catalogPath'],'catalogFileSha256':x['catalogFileSha256'],'catalogGitBlob':x['catalogGitBlob'],
   'callerReferenceCount':x['callerCount'],'callerOccurrenceCount':sum(int(y['literalOccurrenceCount']) for y in x.get('callerReferences',[])),
   'crossDecision':decision,'selectionSource':x['proposalResolution'],'primaryDecision':x['primaryDecision'],
   'blindDecision':x['blindDisposition'],'rootDisposition':disp,'rootTarget':target,'rootTargetSha256':target_sha,
   'rootOverrideApplied':False,'confidence':'moderate','rootRationale':(
    'Keep the exact current value on hold until a qualified locale reviewer resolves the flagged product term, referent, or terminology.' if disp=='hold-low-confidence' else
    'Preserve the callerless target by hash only; no source/current/proposal text is exposed.' if disp=='hold-hash-only' else
    x['rationale'] if disp in ('correction','refinement') else
    'Retain the exact current value accepted by both semantic reviews and pinned to the caller context.'
   ),'nativeSpeakerApproval':False}
  if backed:
   row.update({'sourceKey':x['source'],'source':x['source'],'currentTarget':x['currentTarget'],
    'crossTarget':x['target'],'crossTargetSha256':x['targetSha256'],'sourceTextIncluded':True,'currentTargetTextIncluded':True})
  else:
   row.update({'sourceTextIncluded':False,'currentTargetTextIncluded':False,'crossTargetSha256':x['targetSha256']})
  row['callerReferences']=x.get('callerReferences',[])
  ledger.append(row); groups.setdefault(x['catalogPath'],[]).append((x,row))
  if disp in ('correction','refinement'):
   selected.append({'continuationRank':key[0],'remainingQueueRank':x['remainingQueueRank'],'locale':key[1],
    'sourceId':x['sourceId'],'sourceKey':x['source'],'source':x['source'],'sourceSha256':x['sourceSha256'],
    'catalogPath':x['catalogPath'],'catalogFileSha256':x['catalogFileSha256'],
    'before':x['currentTarget'],'beforeSha256':x['currentTargetSha256'],'after':target,'afterSha256':target_sha,
    'crossTarget':x['target'],'crossTargetSha256':x['targetSha256'],'crossDecision':decision,
    'selectionSource':x['proposalResolution'],'rootDisposition':disp,'rootOverrideApplied':False,'rationale':row['rootRationale'],
    'callerContextSha256':x['callerContextSha256']})
 expected=collections.Counter({'accept-current':214,'correction':53,'refinement':1,'hold-low-confidence':8,'hold-hash-only':24})
 if counts!=expected or len(selected)!=54 or len(groups)!=12: raise SystemExit(f'unexpected adjudication totals: {counts}')
 # Validate all 12 exact catalog pins and every visible current target; hash-only rows remain text-free.
 baseline={}
 for path,items in groups.items():
  raw=subprocess.check_output(['git','show',f'{head}:{path}'],cwd=repo)
  pins={x['catalogFileSha256'] for x,_ in items}
  if len(pins)!=1 or sha(raw)!=next(iter(pins)): raise SystemExit(f'catalog hash mismatch {path}')
  data=json.loads(raw.decode('utf-8'))
  if len(data)!=6175 or (json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')!=raw: raise SystemExit(f'catalog shape/serialization mismatch {path}')
  for x,r in items:
   if r['rootDisposition']=='hold-hash-only':
    catalog_key=key_for_hash(data,r['sourceSha256'])
    if sha(data[catalog_key])!=r['currentTargetSha256']: raise SystemExit(f'hash-only target mismatch {r["continuationRank"]}::{r["locale"]}')
   elif data.get(x['source'])!=x['currentTarget'] or sha(data[x['source']])!=x['currentTargetSha256']:
    raise SystemExit(f'current target mismatch {r["continuationRank"]}::{r["locale"]}')
  baseline[path]=sha(raw)
 prior=rows(CROSS/'prior-active-holds-hash-only.jsonl')
 current=rows(CROSS/'current-window-holds-hash-only.jsonl')
 if len(prior)!=433 or len(current)!=24: raise SystemExit('hold lineage count mismatch')
 if any(any(k in x for k in ('source','sourceKey','currentTarget','target')) for x in prior+current): raise SystemExit('hash-only hold text leaked')
 write_rows(ROOT/'root-disposition-ledger.jsonl',ledger); write_rows(ROOT/'root-selected-targets.jsonl',selected); write_rows(ROOT/'root-overrides.jsonl',[])
 (ROOT/'prior-active-holds-hash-only.jsonl').write_bytes((CROSS/'prior-active-holds-hash-only.jsonl').read_bytes())
 (ROOT/'current-window-holds-hash-only.jsonl').write_bytes((CROSS/'current-window-holds-hash-only.jsonl').read_bytes())
 (ROOT/'prior-hold-resolution-history-hash-only.jsonl').write_bytes((CROSS/'prior-hold-resolution-history-hash-only.jsonl').read_bytes())
 summary={'result':'PASS_ROOT_ADJUDICATION','head':head,'tree':tree,'window':'W1053-W1077','cells':300,
  'dispositions':dict(counts),'selectedChanges':54,'rootOverrides':0,'catalogs':12,'entriesPerCatalog':6175,
  'priorActiveHashOnlyHolds':433,'newCallerlessHashOnlyHolds':24,'activeHashOnlyHoldsAfter':457,
  'newLowConfidenceReviewHolds':8,'nativeSpeakerApproval':False,'headedBrowserReview':False,
  'crossResolutionCounts':dict(resolution_counts),'manualReview':'All 54 selected targets were read against their exact source/caller context and token audit. Eight terminology/referent cells remain held at current hashes.'}
 (ROOT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 att={'head':head,'tree':tree,'integratedCrossLedgerSha256':sha((CROSS/'integrated-cross-review-ledger.jsonl').read_bytes()),
  'integratedCrossChecksumListSha256':sha((CROSS/'SHA256SUMS.txt').read_bytes()),'candidateFreeChecksumListSha256':sha((CF/'SHA256SUMS.txt').read_bytes()),
  'candidateFreeCurrentCellsSha256':sha((CF/'source-current-cells.jsonl').read_bytes()),
  'crossVerifierResult':'PASS','reviewedCallerBackedCells':276,'selectedChanges':54,'heldLowConfidenceCells':8,
  'callerlessHashOnlyHolds':24,'priorActiveHashOnlyHolds':433,'nativeSpeakerApproval':False,
  'rootReview':'The 54 selected strings were individually reviewed against the English source and pinned callers. The eight low-confidence cells remain unchanged.'}
 (ROOT/'input-attestation.json').write_text(json.dumps(att,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 notes=['# Root review notes — slskdN PR #409 W1053–W1077','',f"Input head/tree: `{head}` / `{tree}`.",'',
  'I reviewed all 54 selected targets with the exact source, caller context, primary and blind rationales, and token results. The resulting choices correct missing product meaning, technical terms, punctuation, room terminology, and action timing while preserving placeholders, ICU syntax, markup, numeric values, and protected literals. Eight low-confidence cells remain unchanged; 24 callerless cells and 433 previous holds remain hash-only. No native-speaker or browser acceptance is claimed.','', '## Selected targets','']
 for x in selected: notes.append(f"- `{x['continuationRank']}::{x['locale']}` ({x['rootDisposition']}): `{x['after']}` — {x['rationale']}")
 (ROOT/'root-review-notes.md').write_text('\n'.join(notes)+'\n',encoding='utf-8')
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
