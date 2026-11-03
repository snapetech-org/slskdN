#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,subprocess
E=Path(__file__).resolve().parent
REPO=E.parents[3]
PLAN=json.loads((E/'apply-plan.json').read_text(encoding='utf-8'))
BASE=PLAN['head']; BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
sha=lambda b:hashlib.sha256(b).hexdigest()
def run(args):return subprocess.check_output(args,cwd=REPO,text=True).strip()
assert run(['git','rev-parse','HEAD'])==BASE
assert run(['git','rev-parse','HEAD^{tree}'])==PLAN['tree']
assert PLAN['updateCount']==83
pr=json.loads(run(['gh','api','repos/snapetech-org/slskdN/pulls/409']))
assert (pr['state'],pr['draft'],pr['head']['sha'],pr['head']['ref'],pr['base']['ref'])==('open',True,BASE,BRANCH,'main')
ref=run(['git','ls-remote','https://github.com/snapetech-org/slskdN.git',f'refs/heads/{BRANCH}','refs/pull/409/head']).splitlines()
assert {x.split()[1]:x.split()[0] for x in ref}=={f'refs/heads/{BRANCH}':BASE,f'refs/pull/409/head':BASE}
updates=PLAN['updates']; paths={}
for u in updates: paths.setdefault(u['catalogPath'],{})[u['catalogKey']]=u
assert len(paths)==12 and len({(u['continuationRank'],u['locale']) for u in updates})==83
cells=[json.loads(x) for x in (E/'candidate-free-input/source-current-cells.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
assert len(cells)==300
by_cell={(x['continuationRank'],x['locale']):x for x in cells}
for u in updates:
 c=by_cell[(u['continuationRank'],u['locale'])]
 assert (u['sourceId'],u['catalogPath'],u['catalogKey'],u['currentTarget'],u['currentTargetSha256'])==(c['sourceId'],c['catalogPath'],c['catalogKey'],c['currentTarget'],c['currentTargetSha256'])
 assert sha(u['selectedTarget'].encode())==u['selectedTargetSha256']
applied_already=True
for path,items in paths.items():
 p=REPO/path
 raw=subprocess.check_output(['git','show',f'{BASE}:{path}'],cwd=REPO)
 assert sha(raw)==next(c['catalogFileSha256'] for c in cells if c['catalogPath']==path)
 before=json.loads(raw.decode('utf-8'))
 current=json.loads(p.read_text(encoding='utf-8'))
 assert list(before)==list(current) and set(before)==set(current)
 if p.read_bytes()==raw:
  applied_already=False
  data=before.copy()
  for key,u in items.items():
   assert data[key]==u['currentTarget'] and sha(data[key].encode())==u['currentTargetSha256']
   data[key]=u['selectedTarget']
  p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 else:
  for key in before:
   if key in items: assert current[key]==items[key]['selectedTarget'],(path,key,'partial/wrong target')
   else: assert current[key]==before[key],(path,key,'non-target edit')
# Verify every planned update and every untouched key.
for path,items in paths.items():
 before=json.loads(subprocess.check_output(['git','show',f'{BASE}:{path}'],cwd=REPO,text=True))
 after=json.loads((REPO/path).read_text(encoding='utf-8'))
 assert list(before)==list(after) and set(before)==set(after)
 for key in before:
  if key in items: assert after[key]==items[key]['selectedTarget']
  else: assert after[key]==before[key]
diff=set(run(['git','diff','--name-only']).splitlines())
assert diff==set(paths),diff
print(json.dumps({'pass':True,'baseHead':BASE,'updatedCells':len(updates),'updatedCatalogs':len(paths),'nonTargetChanges':0,'catalogKeyOrderPreserved':True,'alreadyApplied':applied_already},indent=2))
