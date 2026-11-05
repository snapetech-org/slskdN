#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
TASK=Path(__file__).resolve().parents[1]
REPO=Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/slskdn-w978')
HEAD='8c752c49281418fdd96341ed46f5c321627b625f'
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
product=git('rev-parse','HEAD'); tree=git('rev-parse','HEAD^{tree}'); parent=git('rev-parse','HEAD^')
assert parent==HEAD
names=git('diff-tree','--no-commit-id','--name-only','-r',product).splitlines()
assert len(names)==12 and all(n.startswith('src/web/public/locales/') and n.endswith('.json') for n in names)
p=TASK/'root-application'/'application-summary.json'
d=json.loads(p.read_text(encoding='utf-8'))
d.update({'productCommit':product,'productTree':tree,'commitParent':parent,
 'productCommitNames':names,'productCommitPending':False})
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'productCommit':product,'productTree':tree,'commitParent':parent,'changedFiles':len(names)},ensure_ascii=False,indent=2))
