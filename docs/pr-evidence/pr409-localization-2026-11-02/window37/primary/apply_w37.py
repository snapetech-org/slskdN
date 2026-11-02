import hashlib,json,re,subprocess
from collections import Counter
from pathlib import Path

root=Path('/mnt/disks/scratch/task-worktrees/localization-20261102/slskdn-pr409-w36-review')
primary_dir=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window37-primary-20261102')
cross_dir=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window37-crossreview-20261102')
head_expected='2be3fa4dd46a0f0f49adad342f289721e4777035'
tree_expected='f838ae565086dec8639f8a54aa4c7d4572342b5f'

def sha(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def placeholders(s): return sorted(set(re.findall(r'\{[^{}]+\}',s)))
def read_jsonl(p): return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]

head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
tree=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD^{tree}'],text=True).strip()
assert (head,tree)==(head_expected,tree_expected),(head,tree)
primary=read_jsonl(primary_dir/'review-decisions.jsonl')
cross=read_jsonl(cross_dir/'independent-crossreview-ledger.jsonl')
assert len(primary)==273 and len(cross)==273
primary_map={r['id']:r for r in primary}
cross_map={r['id']:r for r in cross}
assert set(primary_map)==set(cross_map)
updates=[]
for key,p in primary_map.items():
 c=cross_map[key]
 assert c['head']==head_expected and c['tree']==tree_expected
 assert c['sourceCurrentCallerPinsVerified'] and c['placeholderAndProtectedLiteralParityVerified']
 assert p['currentTargetSha256']==c['currentTargetSha256']
 assert p['sourceSha256']==c['sourceSha256'] and sha(c['source'])==c['sourceSha256']
 assert sha(c['currentTarget'])==c['currentTargetSha256']
 assert sha(c['finalTarget'])==c['finalTargetSha256']
 assert placeholders(c['source'])==placeholders(c['finalTarget']),(key,'placeholder mismatch')
 disp=c['independentDisposition']
 if disp in ('accepted','refined','missed'):
  assert c['finalTarget']!=c['currentTarget'],(key,disp,'unchanged candidate')
  path=Path(c['catalogPath'])
  assert not path.is_absolute() and path.suffix=='.json'
  updates.append({
   'id':c['id'],'locale':c['locale'],'source_id':c['sourceId'],'catalog_key':c['catalogKey'],
   'catalog_path':c['catalogPath'],'decision':disp,'primary_verdict':c['primaryVerdict'],
   'source':c['source'],'source_sha256':c['sourceSha256'],
   'current_text':c['currentTarget'],'current_target_sha256':c['currentTargetSha256'],
   'primary_candidate':c['candidateTarget'],'primary_candidate_sha256':c['candidateTargetSha256'],
   'final_target':c['finalTarget'],'final_target_sha256':c['finalTargetSha256'],
   'candidate_rationale':c['candidateRationale'],'independent_rationale':c['independentRationale'],
   'caller_refs':c['callerRefs'],
  })
 else:
  assert disp=='accept-current',(key,disp)
  assert c['finalTarget']==c['currentTarget']

assert len(updates)==47,len(updates)
assert Counter(u['decision'] for u in updates)==Counter({'accepted':41,'refined':1,'missed':5})
assert Counter(c['independentDisposition'] for c in cross)==Counter({'accept-current':226,'accepted':41,'missed':5,'refined':1})

catalogs=sorted((root/'src/web/public/locales').glob('*.json'))
assert len(catalogs)==12,len(catalogs)
reference=None
catalog_pins={}
for path in catalogs:
 data_bytes=path.read_bytes(); data=json.loads(data_bytes)
 assert len(data)==6169,(path.name,len(data))
 if reference is None: reference=set(data)
 assert set(data)==reference,(path.name,'key parity')
 rel=path.relative_to(root).as_posix()
 blob=subprocess.check_output(['git','-C',str(root),'rev-parse',f'{head_expected}:{rel}'],text=True).strip()
 catalog_pins[rel]={'git_blob':blob,'sha256':hashlib.sha256(data_bytes).hexdigest(),'keys':len(data)}
for u in updates:
 data=json.loads((root/u['catalog_path']).read_text())
 assert u['catalog_key'] in data and data[u['catalog_key']]==u['current_text']
 assert sha(data[u['catalog_key']])==u['current_target_sha256']

plan=primary_dir/'apply-plan-w37.jsonl'
plan.write_text(''.join(json.dumps(u,ensure_ascii=False,sort_keys=True)+'\n' for u in updates),encoding='utf-8')
for rel in sorted({u['catalog_path'] for u in updates}):
 path=root/rel; data=json.loads(path.read_text())
 for u in updates:
  if u['catalog_path']==rel: data[u['catalog_key']]=u['final_target']
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

readback=[]
for c in cross:
 p=root/c['catalogPath']; value=json.loads(p.read_text())[c['catalogKey']]
 value_hash=sha(value)
 assert value==c['finalTarget'] and value_hash==c['finalTargetSha256'],(c['id'],'readback')
 readback.append({'id':c['id'],'source_id':c['sourceId'],'locale':c['locale'],'catalog_path':c['catalogPath'],'catalog_key':c['catalogKey'],'disposition':c['independentDisposition'],'expected_final_target':c['finalTarget'],'expected_final_sha256':c['finalTargetSha256'],'readback_target':value,'readback_sha256':value_hash,'readback_match':True})
assert len(readback)==273
readback_path=primary_dir/'exact-head-final-readback-w37.jsonl'
readback_path.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in readback),encoding='utf-8')
for path in catalogs:
 data=json.loads(path.read_text())
 assert len(data)==6169 and set(data)==reference
summary={
 'repository':'snapetech-org/slskdN','pull_request':409,'input_head':head_expected,'input_tree':tree_expected,
 'source_subtree_tree':'594e56c3f439bad476b1bd57e0de1665c62fa1bb','window':37,
 'reviewed_cells':273,'primary_candidate_dispositions':{'accepted':41,'refined':1},
 'missed_corrections':5,'accepted_current':226,'applied_changes':len(updates),
 'applied_by_disposition':dict(Counter(u['decision'] for u in updates)),
 'changes_by_locale':dict(Counter(u['locale'] for u in updates)),
 'held':0,'no_op':0,'catalogs':catalog_pins,'keys_per_catalog':6169,
 'final_readback_rows':len(readback),'final_readback_mismatches':0,
 'readback_sha256':hashlib.sha256(readback_path.read_bytes()).hexdigest(),
 'apply_plan_sha256':hashlib.sha256(plan.read_bytes()).hexdigest(),
 'primary_manifest_sha256':'c38e3d7736e2179d1014d2c10b4e75cfb27d6d2b12c57fc70b34678b8b120bf7',
 'cross_review_manifest_sha256':'af2dac6d417e173613458b9506d177b4e291e4c66f3cac0dee32a927150862d7',
 'native_speaker_review_performed':False,'browser_review_performed':False,
 'tests_builds_scans_ci_workflow_changes_releases_tags_merges':False,
}
(primary_dir/'apply-summary-w37.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:summary[k] for k in ['applied_changes','applied_by_disposition','changes_by_locale','keys_per_catalog','final_readback_rows','readback_sha256']},ensure_ascii=False,indent=2))
