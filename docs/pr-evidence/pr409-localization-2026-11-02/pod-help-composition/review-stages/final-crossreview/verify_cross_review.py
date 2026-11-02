#!/usr/bin/env python3
"""Read-only exact-head and proposal-packet verifier for slskdN PR #409."""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path('/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn')
HERE=Path(__file__).resolve().parent
INPUT=HERE/'input'
HEAD='490983c336d4958f11518c73268de2788c8858cb'
TREE='01ca1bcdd5f74fd1adf6151dda441e8a77a811da'
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def run(*args): return subprocess.check_output(args,cwd=ROOT).decode().strip()
assert run('git','rev-parse','HEAD')==HEAD
assert run('git','rev-parse','HEAD^{tree}')==TREE
assert run('git','status','--porcelain')==''
pr=json.loads(run('gh','pr','view','409','--repo','snapetech-org/slskdN','--json','number,state,isDraft,headRefOid,headRefName,baseRefName'))
assert pr['number']==409 and pr['state']=='OPEN' and pr['isDraft'] and pr['headRefOid']==HEAD and pr['baseRefName']=='main'
with (INPUT/'SHA256SUMS').open() as f: pass
subprocess.check_call(['sha256sum','-c','SHA256SUMS'],cwd=INPUT,stdout=subprocess.DEVNULL)
pins=json.loads((INPUT/'source-caller-pins.json').read_text())
caller=ROOT/pins['callerPath']; rich=ROOT/pins['richTextPath']
assert sha(caller.read_bytes())==pins['callerSha256'] and run('git','rev-parse',f'{HEAD}:{pins["callerPath"]}')==pins['callerGitBlob']
assert sha(rich.read_bytes())==pins['richTextSha256'] and run('git','rev-parse',f'{HEAD}:{pins["richTextPath"]}')==pins['richTextGitBlob']
lines=caller.read_text().splitlines()
assert lines[pins['callerLines'][0]['line']-1]==pins['callerLines'][0]['text']
source='Enable {feature} in the server configuration to use Pod rooms and discover other Pods.'
comp=pins['expectedComposition']
assert source.count('{feature}')==1 and comp.count('<code dir="ltr">feature.Pods</code>')==1
assert comp.count('</code>')==1
rich_text=rich.read_text()
assert 'export const LocalizedRichText' in rich_text
assert 'const parts = t(source).split(/(\\{[a-zA-Z][a-zA-Z0-9_]*\\})/g);' in rich_text
assert ': <Fragment key={index}>{value}</Fragment>;' in rich_text
rows=[json.loads(x) for x in (INPUT/'final-targets.jsonl').read_text().splitlines()]
assert len(rows)==12 and {r['locale'] for r in rows}=={'ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant'}
for r in rows:
 raw=(ROOT/r['catalogPath']).read_bytes(); cat=json.loads(raw)
 assert sha(raw)==r['catalogSha256'] and run('git','rev-parse',f'{HEAD}:{r["catalogPath"]}')==r['catalogGitBlob']
 assert cat['Enable']==r['oldEnable'] and cat['in the server configuration to use pod rooms and discovery.']==r['oldFragment']
 assert sha(r['newTarget'])==r['newTargetSha256']
 assert r['newSourceAbsent'] and source not in cat and r['newTarget'] not in cat
 assert r['newTarget'].count('{feature}')==r['newTargetPlaceholderCount']==1
 assert '<' not in r['newTarget'] and '>' not in r['newTarget']
print('exact head, PR state, source/caller/catalog pins, and 12 target hashes: OK')
