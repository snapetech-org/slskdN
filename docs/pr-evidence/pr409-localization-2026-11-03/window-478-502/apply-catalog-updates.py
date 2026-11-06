#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import hashlib,json,subprocess
E=Path(__file__).resolve().parent
REPO=E.parents[3]
PLAN=json.loads((E/'cross-audit-apply-plan.json').read_text(encoding='utf-8'))
BASE=PLAN['head']
BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
assert PLAN['pullRequest']==409 and PLAN['window']=='W64-ranks-478-502'
assert subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()==BASE
assert subprocess.check_output(['git','-C',str(REPO),'branch','--show-current'],text=True).strip()=='task/slskdn-w64-20261103'
assert not subprocess.check_output(['git','-C',str(REPO),'diff','--name-only'],text=True).strip()
pr=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','number,state,isDraft,headRefName,headRefOid,baseRefName'],text=True))
assert (pr['number'],pr['state'],pr['isDraft'],pr['headRefName'],pr['headRefOid'],pr['baseRefName'])==(409,'OPEN',True,BRANCH,BASE,'main')
refs=subprocess.check_output(['git','ls-remote','https://github.com/snapetech-org/slskdN.git',f'refs/heads/{BRANCH}','refs/pull/409/head'],text=True)
refmap={line.split()[1]:line.split()[0] for line in refs.splitlines() if line.strip()}
assert refmap=={f'refs/heads/{BRANCH}':BASE,'refs/pull/409/head':BASE}
sha=lambda b:hashlib.sha256(b).hexdigest()
inputs=[json.loads(s) for s in (E/'candidate-free-input/source-current-cells.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
decisions=[json.loads(s) for s in (E/'cross-audit-decisions.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
assert len(inputs)==len(decisions)==300
expected_file_sha={}
for row in inputs:
    path=row['catalogPath']
    assert path not in expected_file_sha or expected_file_sha[path]==row['catalogFileSha256']
    expected_file_sha[path]=row['catalogFileSha256']
for path,expected in expected_file_sha.items():
    current=(REPO/path).read_bytes()
    baseline=subprocess.check_output(['git','-C',str(REPO),'show',f'{BASE}:{path}'])
    assert current==baseline and sha(current)==expected,(path,'catalog baseline differs from pinned input')
updates=PLAN['updates']
assert len(updates)==PLAN['updateCount']==86
by_path={}
for row in updates:
    by_path.setdefault(row['catalogPath'],{})[row['catalogKey']]=row
assert len(by_path)==12
for path,items in by_path.items():
    file=REPO/path
    data=json.loads(file.read_text(encoding='utf-8'))
    assert len(items)==len(set(items))
    for key,row in items.items():
        assert key in data and data[key]==row['currentTarget'],(path,key,'current target mismatch')
        assert sha(data[key].encode('utf-8'))==row['currentTargetSha256']
        assert sha(row['selectedTarget'].encode('utf-8'))==row['selectedTargetSha256']
        data[key]=row['selectedTarget']
    file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Verify each catalog has the exact planned changes and retains its key order.
changed_cells=0
for path,expected in expected_file_sha.items():
    baseline=json.loads(subprocess.check_output(['git','-C',str(REPO),'show',f'{BASE}:{path}'],text=True))
    final=json.loads((REPO/path).read_text(encoding='utf-8'))
    assert list(baseline)==list(final) and set(baseline)==set(final),(path,'catalog key order/shape changed')
    plan=by_path.get(path,{})
    for key in baseline:
        target=plan.get(key)
        if target:
            assert final[key]==target['selectedTarget'],(path,key,'target readback mismatch')
            assert baseline[key]==target['currentTarget'],(path,key,'baseline target mismatch')
            changed_cells+=1
        else:
            assert final[key]==baseline[key],(path,key,'non-target catalog value changed')
assert changed_cells==86
diff=subprocess.check_output(['git','-C',str(REPO),'diff','--name-only'],text=True).splitlines()
assert set(diff)==set(expected_file_sha),(diff,set(expected_file_sha))
assert not any(path.startswith('.github/workflows/') for path in diff)
print(json.dumps({'pass':True,'baseHead':BASE,'updatedCatalogs':len(by_path),'updatedCells':changed_cells,'nonTargetCatalogChanges':0,'catalogKeyOrderPreserved':True,'workflowFilesTouched':False,'filesChanged':diff},ensure_ascii=False,indent=2))
