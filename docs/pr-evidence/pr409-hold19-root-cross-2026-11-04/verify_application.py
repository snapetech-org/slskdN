#!/usr/bin/env python3
"""Verify the exact-hash slskdN PR #409 hold19 catalog application."""
from pathlib import Path
import hashlib, json, subprocess, sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
def fail(message): raise SystemExit('FAIL: '+message)
def digest(data): return hashlib.sha256(data).hexdigest()
def jread(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def run(args,cwd=REPO): return subprocess.check_output(args,cwd=cwd,text=True).strip()
# Validate the sealed cross packet and added application evidence manifests.
for manifest,root in ((HERE/'SHA256SUMS.txt',HERE),(HERE/'APPLICATION-SHA256SUMS.txt',HERE)):
    for line in manifest.read_text(encoding='utf-8').splitlines():
        expected,rel=line.split('  ',1); p=root/rel
        if not p.is_file() or digest(p.read_bytes())!=expected: fail('checksum mismatch: '+rel)
# Run the supplied evidence-only review verifiers (no builds/tests/CI).
for d,cmd in ((HERE/'input/candidate-free-input',['python3','verify_input.py']),
              (HERE/'primary-review/input',['python3','verify_clean_input.py']),
              (HERE/'primary-review/output',['python3','verify_primary.py']),
              (HERE/'independent-blind/sealed-review',['python3','verify_review.py']),
              (HERE/'cross-review',['python3','verify_root_cross.py'])):
    subprocess.check_call(cmd,cwd=d,stdout=subprocess.DEVNULL)
meta=jread(HERE/'application-readback-metadata.json')
ledger=[json.loads(x) for x in (HERE/'cross-review/root-cross-ledger.jsonl').read_text(encoding='utf-8').splitlines()]
input_cells=[json.loads(x) for x in (HERE/'input/candidate-free-input/source-current-cells.jsonl').read_text(encoding='utf-8').splitlines()]
structure=[json.loads(x) for x in (HERE/'input/candidate-free-input/catalog-structure.jsonl').read_text(encoding='utf-8').splitlines()]
readback=[json.loads(x) for x in (HERE/'application-readback.jsonl').read_text(encoding='utf-8').splitlines()]
if len(ledger)!=19 or len(readback)!=19: fail('expected 19 root/readback rows')
reviewed=meta['reviewedHead']; app=meta['catalogCommit']
if run(['git','rev-parse',app+'^'])!=reviewed: fail('catalog commit parent is not reviewed head')
if run(['git','rev-parse',app+'^{tree}'])!=meta['catalogTree']: fail('catalog tree mismatch')
# ensure catalog and evidence commits remain descendants of the pinned review head
try: subprocess.check_call(['git','merge-base','--is-ancestor',app,'HEAD'],cwd=REPO,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
except subprocess.CalledProcessError: fail('catalog commit is not an ancestor of current checkout')
if run(['git','diff','--name-only',reviewed+'..HEAD','--','.github/workflows']): fail('workflow files changed')
bycell={(r['continuationRank'],r['locale']):r for r in input_cells}
root={(r['continuationRank'],r['locale']):r for r in ledger}
rb={(r['continuationRank'],r['locale']):r for r in readback}
if set(root)!=set(rb) or set(root)!=set(bycell): fail('cell coverage mismatch')
updates={(r['continuationRank'],r['locale']):r for r in ledger if r['continuationRank']==409 and r['action']=='update'}
if len(updates)!=12: fail('expected 12 rank-409 updates')
if not all('Servarr' in r['selectedTarget'] for r in updates.values()): fail('Servarr literal not preserved in all updates')
for row in structure:
    path=row['catalogPath']
    before=json.loads(subprocess.check_output(['git','show',reviewed+':'+path],cwd=REPO).decode('utf-8'))
    after=json.loads(subprocess.check_output(['git','show',app+':'+path],cwd=REPO).decode('utf-8'))
    if list(before)!=list(after): fail('catalog key ordering changed: '+path)
    changed={k:v for k,v in after.items() if before.get(k)!=v}
    selected={r['catalogKey']:r['selectedTarget'] for r in updates.values() if r['catalogPath']==path}
    if changed!=selected: fail('catalog changes are not exactly selected updates: '+path)
for key,r in root.items():
    c=bycell[key]; a=rb[key]
    if a['catalogPath']!=r['catalogPath'] or a['catalogCommit']!=app or a['catalogTree']!=meta['catalogTree']: fail('readback metadata mismatch '+str(key))
    if a['currentTargetSha256']!=r['currentTargetSha256']: fail('input target hash mismatch '+str(key))
    blob=subprocess.check_output(['git','show',app+':'+r['catalogPath']],cwd=REPO)
    data=json.loads(blob.decode('utf-8'))
    if r['continuationRank']==409:
        if r['action']!='update' or a.get('disposition')!='correction': fail('rank-409 disposition mismatch '+str(key))
        target=r['selectedTarget']; actual=data[r['catalogKey']]
        if actual!=target or digest(actual.encode())!=r['selectedTargetSha256']: fail('rank-409 target mismatch '+str(key))
        if a.get('catalogKey')!=r['catalogKey'] or a.get('selectedTarget')!=target or a.get('readbackTarget')!=actual: fail('rank-409 readback mismatch '+str(key))
        if a.get('selectedTargetSha256')!=digest(target.encode()) or a.get('readbackTargetSha256')!=digest(actual.encode()): fail('rank-409 readback hash mismatch '+str(key))
    elif r['continuationRank']==475:
        actual=data[c['catalogKey']]
        if r['selectedDisposition']!='accept-current' or actual!=c['currentTarget'] or actual!=r['selectedTarget']: fail('rank-475 accepted value changed '+str(key))
        if a.get('disposition')!='accept-current' or a.get('readbackTarget')!=actual: fail('rank-475 readback mismatch '+str(key))
    elif r['continuationRank']==504:
        actual=data[c['catalogKey']]
        if r['selectedDisposition']!='hold' or r['selectedTarget'] is not None: fail('rank-504 hold disposition changed '+str(key))
        if digest(actual.encode())!=r['currentTargetSha256'] or digest(actual.encode())!=c['currentTargetSha256']: fail('rank-504 hold value changed '+str(key))
        if any(f in a for f in ('catalogKey','source','currentTarget','selectedTarget','readbackTarget')): fail('rank-504 hold readback contains text '+str(key))
        if a.get('disposition')!='hold' or a.get('readbackTargetSha256')!=digest(actual.encode()): fail('rank-504 hold hash mismatch '+str(key))
    else: fail('unexpected root-cross rank '+str(key))
if sum(r['continuationRank']==409 for r in root.values())!=12 or sum(r['continuationRank']==475 for r in root.values())!=1 or sum(r['continuationRank']==504 for r in root.values())!=6: fail('expected rank coverage mismatch')
print(json.dumps({'result':'PASS','catalogCommit':app,'catalogTree':meta['catalogTree'],'rows':19,'updates':12,'acceptCurrent':1,'textFreeHolds':6,'ServarrPreserved':True,'workflowChanges':False},sort_keys=True))
