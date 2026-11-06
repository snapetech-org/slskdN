#!/usr/bin/env python3
import collections, hashlib, json, pathlib, re, subprocess, sys
out=pathlib.Path(__file__).resolve().parent
inp=out.parent/'input'
expected_head='03c73e7b6706d8a034d7a24d6984763134f61bac'
expected_tree='fa3f2041bbc2d4bb4eb512c03e874db3dbf631a5'
# Verify sanitized input through its published portable verifier.
subprocess.run([sys.executable,str(inp/'verify_clean_input.py')],check=True,stdout=subprocess.DEVNULL)
manifest=json.loads((inp/'manifest.json').read_text(encoding='utf-8'))
assert manifest['head']==expected_head and manifest['tree']==expected_tree
source_rows=[json.loads(s) for s in (inp/'source-current-cells.jsonl').read_text(encoding='utf-8').splitlines() if s]
key=lambda x:(x['continuationRank'],x['locale'])
source_map={key(x):x for x in source_rows}
review_rows=[json.loads(s) for s in (out/'primary-review.jsonl').read_text(encoding='utf-8').splitlines() if s]
assert len(source_rows)==19 and len(review_rows)==19
review_map={key(x):x for x in review_rows}
assert set(review_map)==set(source_map)
counts=collections.Counter()
for k,src in source_map.items():
 r=review_map[k]
 assert r['head']==expected_head and r['tree']==expected_tree
 for field in ('sourceId','catalogPath','catalogKey','source','sourceSha256','currentTarget','currentTargetSha256','callerContextSha256'):
  assert r[field]==src[field],(k,field)
 assert r['disposition'] in {'accept-current','correct','refine','hold'}
 counts[r['disposition']]+=1
 if r['disposition'] in {'accept-current','hold'}:
  assert r['target'] is None
 else:
  target=r['target']; assert isinstance(target,str) and target and target!=src['currentTarget']
  # This scope's sources contain no placeholders, tags, or numbers; enforce the same on proposed targets.
  assert not re.findall(r'\{\{?[^{}]+\}?\}|%[0-9]*[sd]',target)
  assert not re.findall(r'<[^>]+>',target)
  assert not re.findall(r'\d+(?:[.,]\d+)?',target)
  if 'Servarr' in src['source']:
   assert 'Servarr' in target
   assert r['tokenCheck']['proposedTargetCheck']['requiredCallerLiteralsPreserved'] is True
  assert r['tokenCheck']['proposedTargetCheck']['placeholdersPreserved'] is True
  assert r['tokenCheck']['proposedTargetCheck']['markupPreserved'] is True
  assert r['tokenCheck']['proposedTargetCheck']['numericTokensPreserved'] is True
 assert len(r['callerRefs'])==len(src['callerRefs'])
 for actual, original in zip(r['callerRefs'],src['callerRefs']):
  for field in ('path','line','lineSha256','contextSha256','fileSha256','gitBlob'):
   assert actual[field]==original[field],(k,field)
assert counts=={'accept-current':2,'correct':7,'refine':4,'hold':6},counts
summary=json.loads((out/'summary.json').read_text(encoding='utf-8'))
assert summary['head']==expected_head and summary['tree']==expected_tree
assert summary['cellCount']==19 and summary['dispositions']==dict(counts)
assert summary['proposedTargets']==11 and summary['heldForSemanticAmbiguity']==6
for name in ('live-before.json','live-after.json'):
 live=json.loads((out/name).read_text(encoding='utf-8'))
 assert live['head']==expected_head and live['tree']==expected_tree
 assert live['remoteBranchHead']==expected_head
 assert live['prState']=='OPEN' and live['draft'] is True
 assert live['deploymentsAtPinnedHead']==0 and live['worktreeClean'] is True
before=json.loads((out/'live-before.json').read_text(encoding='utf-8'))
after=json.loads((out/'live-after.json').read_text(encoding='utf-8'))
for field in ('repository','pullRequest','prState','draft','branch','head','tree','remoteBranchHead','deploymentsAtPinnedHead','worktreeClean'):
 assert before[field]==after[field],field
# Verify the packet checksum inventory itself; SHA256SUMS.txt is intentionally not self-hashed.
listed={}
for line in (out/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
 digest, name=line.split('  ',1)
 assert name not in listed
 listed[name]=digest
actual_files={p.name for p in out.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt'}
assert set(listed)==actual_files,(set(listed),actual_files)
for name,digest in listed.items():
 assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest,name
print(json.dumps({'verifier':'PASS','cells':19,'dispositions':dict(counts),'selectedTargets':11,'semanticHolds':6,'tokenMismatches':0,'livePins':'PASS','checksummedFiles':len(listed)},indent=2))
