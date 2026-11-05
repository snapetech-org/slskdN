#!/usr/bin/env python3
"""Build exact-hash root decisions for slskdN W1028-W1052."""
from __future__ import annotations
import argparse, collections, hashlib, json, subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent if HERE.name=='root-adjudication' else HERE
INPUTS=BASE/'inputs'; CROSS=INPUTS/'integrated-cross-review'
CF=INPUTS/'candidate-free'; ROOT=BASE/'root-adjudication'; APP=BASE/'root-application'
ROOT_ROWS=ROOT/'root-disposition-ledger.jsonl'; SELECTED=ROOT/'root-selected-targets.jsonl'; OVERRIDES=ROOT/'root-overrides.jsonl'
REPO: Path
OVERRIDE=(1045,'fr')
OVERRIDE_TARGET='Saisissez les valeurs que vous souhaitez examiner. Elles restent uniquement sur cette page ; l’aperçu et l’examen du contrat ne lancent aucun scan ni aucune autre opération côté serveur.'
OVERRIDE_RATIONALE='The pinned UI action is Review Contract and its local helper builds readiness checks/blocker results. Use examen du contrat to match that review without implying formal validation; the complete sentence also fixes feminine plural agreement for valeurs.'

def sha(v): return hashlib.sha256(v.encode('utf-8') if isinstance(v,str) else v).hexdigest()
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def write_rows(p,rs): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rs),encoding='utf-8')
def git(*args): return subprocess.check_output(['git',*args],cwd=REPO,text=True).strip()
def main():
 global REPO
 ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=Path,required=True); a=ap.parse_args(); REPO=a.repo.resolve()
 cross=rows(CROSS/'integrated-cross-review.jsonl'); cf=rows(CF/'source-current-cells.jsonl')
 verify=json.loads((CROSS/'input-verification.json').read_text(encoding='utf-8'))
 head=verify['head']; tree=verify['tree']
 if head!='624e27d8bb108a764df6daab5cfb1c517ebac96d' or tree!='d139a16988e23046ccb09f519db2d3b7ae0b86d1': raise SystemExit('unexpected pinned input head/tree')
 if git('rev-parse','HEAD')!=head or git('rev-parse','HEAD^{tree}')!=tree or git('status','--porcelain'): raise SystemExit('repository must be clean at exact input head/tree')
 if len(cross)!=300 or len(cf)!=300: raise SystemExit('expected 300 exact window cells')
 cfmap={(r['continuationRank'],r['locale']):r for r in cf}; assert len(cfmap)==300
 counts=collections.Counter(); final=[]; selected=[]; overrides=[]; byfile={}
 for x in cross:
  key=(x['continuation_rank'],x['locale']); c=cfmap[key]
  if x['input_head']!=head or x['input_tree']!=tree: raise SystemExit(f'cross pin mismatch {key}')
  if x['current_target_sha256']!=c['currentTargetSha256'] or x['source_sha256']!=c['sourceSha256'] or x['caller_context_sha256']!=c['callerContextSha256']:
   raise SystemExit(f'candidate-free binding mismatch {key}')
  is_hold=x['integrated_decision']=='hold_hash_only'
  if is_hold:
   if x['source_text_included'] or x['current_target_text_included'] or c['sourceTextIncluded'] or c['currentTargetTextIncluded']:
    raise SystemExit(f'hold text leaked at {key}')
   root_disp='hold-hash-only'; target=None; target_sha=None
  elif x['integrated_decision']=='retain_current':
   root_disp='accept-current'; target=x['current_target']; target_sha=x['current_target_sha256']
  else:
   if x['selected_target'] is None or sha(x['selected_target'])!=x['selected_target_sha256']:
    raise SystemExit(f'selected cross target hash mismatch {key}')
   target=x['selected_target']; target_sha=x['selected_target_sha256']
   if key==OVERRIDE:
    assert x['source_id']=='src_39a5412ab1ce15ca' and x['locale']=='fr'
    assert x['integrated_decision']=='cross_refinement'
    overrides.append({'continuationRank':key[0],'locale':key[1],'sourceId':x['source_id'],
      'sourceSha256':x['source_sha256'],'currentTarget':x['current_target'],'currentTargetSha256':x['current_target_sha256'],
      'crossTarget':x['selected_target'],'crossTargetSha256':x['selected_target_sha256'],
      'rootTarget':OVERRIDE_TARGET,'rootTargetSha256':sha(OVERRIDE_TARGET),
      'callerContextSha256':x['caller_context_sha256'],'rationale':OVERRIDE_RATIONALE,'confidence':'moderate'})
    target=OVERRIDE_TARGET; target_sha=sha(target)
   root_disp='refinement' if x['integrated_decision']=='cross_refinement' else 'correction'
  row={'continuationRank':key[0],'remainingQueueRank':x['remaining_queue_rank'],'locale':key[1],
   'sourceId':x['source_id'],'sourceIdSha256':x['source_id_sha256'],'sourceSha256':x['source_sha256'],
   'currentTargetSha256':x['current_target_sha256'],'callerContextSha256':x['caller_context_sha256'],
   'catalogPath':x['catalog_path'],'catalogFileSha256':x['catalog_file_sha256'],
   'callerReferenceCount':x['caller_reference_count'],'callerOccurrenceCount':x['caller_occurrence_count'],
   'crossDecision':x['integrated_decision'],'selectionSource':x['selection_source'],
   'primaryDecision':x['primary_decision'],'blindDecision':x['blind_decision'],
   'rootDisposition':root_disp,'rootTarget':target,'rootTargetSha256':target_sha,
   'rootOverrideApplied':key==OVERRIDE,'rootRationale':OVERRIDE_RATIONALE if key==OVERRIDE else x['rationale'],
   'confidence':'moderate'}
  if not is_hold:
   row.update({'sourceKey':x['source_text'],'source':x['source_text'],'currentTarget':x['current_target'],'sourceTextIncluded':True,'currentTargetTextIncluded':True})
  else:
   row.update({'sourceTextIncluded':False,'currentTargetTextIncluded':False})
  final.append(row); counts[root_disp]+=1
  byfile.setdefault(x['catalog_path'],[]).append((x,row))
  if root_disp in {'correction','refinement'}:
   selected.append({'continuationRank':key[0],'remainingQueueRank':x['remaining_queue_rank'],'locale':key[1],
    'sourceId':x['source_id'],'sourceKey':x['source_text'],'source':x['source_text'],'sourceSha256':x['source_sha256'],
    'catalogPath':x['catalog_path'],'catalogFileSha256':x['catalog_file_sha256'],
    'before':x['current_target'],'beforeSha256':x['current_target_sha256'],'after':target,'afterSha256':target_sha,
    'crossTarget':x['selected_target'],'crossTargetSha256':x['selected_target_sha256'],
    'crossDecision':x['integrated_decision'],'selectionSource':x['selection_source'],
    'rootOverrideApplied':key==OVERRIDE,'rationale':row['rootRationale'],'callerContextSha256':x['caller_context_sha256']})
 if counts!=collections.Counter({'accept-current':244,'correction':42,'refinement':2,'hold-hash-only':12}): raise SystemExit(f'root counts mismatch {counts}')
 if len(selected)!=44 or len(overrides)!=1 or len(byfile)!=12: raise SystemExit('unexpected selected/catalog/override counts')
 baseline={}
 for path,items in byfile.items():
  raw=subprocess.check_output(['git','show',f'{head}:{path}'],cwd=REPO)
  if len({x['catalog_file_sha256'] for x,_ in items})!=1 or sha(raw)!=items[0][0]['catalog_file_sha256']: raise SystemExit(f'catalog file hash mismatch {path}')
  data=json.loads(raw.decode('utf-8'))
  if len(data)!=6175 or (json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')!=raw: raise SystemExit(f'catalog shape/serialization mismatch {path}')
  for x,r in items:
   if r['rootDisposition']=='hold-hash-only': continue
   if data.get(x['source_text'])!=x['current_target']: raise SystemExit(f'current catalog value mismatch {path}::{x["source_id"]}')
  baseline[path]=sha(raw)
 write_rows(ROOT_ROWS,final); write_rows(SELECTED,selected); write_rows(OVERRIDES,overrides)
 summary={'result':'PASS_ROOT_ADJUDICATION','head':head,'tree':tree,'window':'W1028-W1052','cells':300,
  'dispositions':dict(counts),'selectedChanges':44,'rootOverrides':1,'catalogs':12,'entriesPerCatalog':6175,
  'priorActiveHolds':421,'newHashOnlyHolds':12,'activeHoldsAfter':433,'nativeSpeakerApproval':False,'headedBrowserReview':False}
 (ROOT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 att={'head':head,'tree':tree,'crossLedgerSha256':sha((CROSS/'integrated-cross-review.jsonl').read_bytes()),
  'crossChecksumListSha256':sha((CROSS/'SHA256SUMS.txt').read_bytes()),'candidateFreeCellsSha256':sha((CF/'source-current-cells.jsonl').read_bytes()),
  'independentAudit':'all 44 selected hashes/provenance verified; W1050 and W1031 concerns withdrawn after exact-context clarification; W1045 French wording refined',
  'sourceSupplementSha256':sha((BASE/'source-context-supplement.jsonl').read_bytes()),'baselineCatalogSha256':baseline}
 (ROOT/'input-attestation.json').write_text(json.dumps(att,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
