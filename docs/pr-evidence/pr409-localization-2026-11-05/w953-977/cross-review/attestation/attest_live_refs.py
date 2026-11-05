#!/usr/bin/env python3
from __future__ import annotations
import argparse,datetime,hashlib,json,subprocess
from pathlib import Path
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261105/slskdn-pr409-w928-952-pinned')
SLUG='snapetech-org/slskdN'; PR=409
HEAD='fc8e42a06363ceee762ae084bbe716953d4a5d94'; TREE='e04aa06b8cfb0ee41cae90aef601a0552b5e85bd'
BASE='f25d263a2a7cdb2c8f76c40c346cb10f749a9356'; BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
def run(cmd): return subprocess.check_output(cmd,text=True).strip()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--label',required=True);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
 pr=json.loads(run(['gh','pr','view',str(PR),'--repo',SLUG,'--json','number,state,isDraft,headRefName,headRefOid,baseRefName,baseRefOid,url']))
 refs_raw=run(['git','-C',str(REPO),'ls-remote','origin','refs/heads/main','refs/heads/'+BRANCH,'refs/pull/409/head'])
 refs={line.split('\t')[1]:line.split('\t')[0] for line in refs_raw.splitlines() if line.strip()}
 tree=lambda rev:run(['git','-C',str(REPO),'rev-parse',rev+'^{tree}'])
 status=run(['git','-C',str(REPO),'status','--porcelain=v1'])
 main=refs.get('refs/heads/main')
 data={'schemaVersion':1,'label':a.label,'capturedAtUtc':datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z'),'repository':SLUG,'pullRequest':PR,'prApi':pr,'remoteRefs':refs,'headSha':HEAD,'headTree':tree(HEAD),'apiBaseSha':BASE,'apiBaseTree':tree(BASE),'liveMainSha':main,'liveMainTree':tree(main),'exactWorktree':str(REPO),'exactWorktreeHead':run(['git','-C',str(REPO),'rev-parse','HEAD']),'exactWorktreeTree':run(['git','-C',str(REPO),'rev-parse','HEAD^{tree}']),'exactWorktreeClean':not bool(status),'exactWorktreeStatusSha256':hashlib.sha256(status.encode()).hexdigest()}
 if pr['state']!='OPEN' or pr['isDraft'] is not True or pr['headRefName']!=BRANCH or pr['headRefOid']!=HEAD or pr['baseRefName']!='main' or pr['baseRefOid']!=BASE:raise SystemExit('FAIL: live PR API state/pins changed')
 if refs.get('refs/heads/'+BRANCH)!=HEAD or refs.get('refs/pull/409/head')!=HEAD:raise SystemExit('FAIL: live branch/pull refs changed')
 if data['headTree']!=TREE or data['exactWorktreeHead']!=HEAD or data['exactWorktreeTree']!=TREE or not data['exactWorktreeClean']:raise SystemExit('FAIL: exact head/tree clean checkout')
 if data['apiBaseTree']!='b2ce36e07aee6ade05e6d8795d04b9a7455a081f':raise SystemExit('FAIL: API base tree mismatch')
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(data,sort_keys=True,indent=2)+'\n');print(json.dumps(data,indent=2))
if __name__=='__main__':main()
