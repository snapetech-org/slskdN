from __future__ import annotations
import json,subprocess,pathlib
from datetime import datetime,timezone
OUT=pathlib.Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window44-crossreview-20261102')
REPOS=[('SeerrNG',418),('ChaptarrNG',190),('QuestarrNG',155),('ROMarrNG',70),('slskR',204),('slskdN',409),('TorrentNG',243)]
def run(*a): return subprocess.check_output(a,text=True).strip()
rows=[]
for repo,n in REPOS:
 pr=json.loads(run('gh','pr','view',str(n),'--repo',f'snapetech-org/{repo}','--json','number,state,isDraft,headRefName,headRefOid,baseRefName,baseRefOid,url'))
 tree=json.loads(run('gh','api',f"repos/snapetech-org/{repo}/git/commits/{pr['headRefOid']}"))['tree']['sha']
 row={'repository':f'snapetech-org/{repo}',**pr,'headTree':tree}
 if n==409: row['remoteBranchOid']=run('git','ls-remote','https://github.com/snapetech-org/slskdN.git',f"refs/heads/{pr['headRefName']}").split()[0]
 rows.append(row)
t=next(x for x in rows if x['number']==409)
assert t['state']=='OPEN' and t['isDraft'] is True
assert t['headRefOid']=='f3fbd3f8db10f78768b9951a67b4b9de8581a408'
assert t['headTree']=='9495c35a540ef2d2e845c833acb709365e0e26ac'
assert t['remoteBranchOid']==t['headRefOid']
(OUT/'live-seven-pr-heads-start.json').write_text(json.dumps({'capturedAtUtc':datetime.now(timezone.utc).isoformat(),'pullRequests':rows},ensure_ascii=False,indent=2,sort_keys=True)+'\n')
print(json.dumps([{'number':x['number'],'repository':x['repository'],'state':x['state'],'isDraft':x['isDraft'],'head':x['headRefOid'],'tree':x['headTree'],'remote':x.get('remoteBranchOid')} for x in rows],ensure_ascii=False,indent=2))
