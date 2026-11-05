#!/usr/bin/env python3
"""Reattest live refs and seal the W81 primary-review packet."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
INPUT=ROOT.parent.parent/'candidate-free'/'input'
HEAD='91da6fff5d5b628ade7ee556386e3db1db6878fa'
TREE='56930b73d10a4c419edf68f0d951ceedaa63c990'
BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
def sha(b): return hashlib.sha256(b).hexdigest()
def j(n): return json.loads((ROOT/n).read_text(encoding='utf-8'))
def rows(n): return [json.loads(x) for x in (ROOT/n).read_text(encoding='utf-8').splitlines() if x.strip()]
def git(repo,*a): return subprocess.check_output(['git','-C',str(repo),*a],text=True).strip()
def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True); repo=Path(ap.parse_args().repo).resolve()
    subprocess.check_call(['python3',str(ROOT/'capture_live.py'),'after'],cwd=ROOT)
    before,after=j('live-before.json'),j('live-after.json')
    if (before['headRefOid'],before['commitTree'],after['headRefOid'],after['commitTree'])!=(HEAD,TREE,HEAD,TREE): raise SystemExit('REFUSED: primary live head/tree')
    if git(repo,'rev-parse','HEAD')!=HEAD or git(repo,'rev-parse','HEAD^{tree}')!=TREE or git(repo,'status','--porcelain=v1'): raise SystemExit('REFUSED: worktree pin/cleanliness')
    inp_drift=j('main-drift-before.json'); candrift=json.loads((INPUT/'main-drift.json').read_text())
    if (inp_drift['baseApiSha'],inp_drift['liveMainSha'],inp_drift['changedPaths'])!=(candrift['baseApiSha'],candrift['liveMainAfterSha'],candrift['changedPaths']): raise SystemExit('REFUSED: main drift differs from candidate-free input')
    refs=subprocess.check_output(['git','ls-remote','https://github.com/snapetech-org/slskdN.git',f'refs/heads/{BRANCH}','refs/pull/409/head','refs/pull/409/merge'],text=True)
    refs={x.split()[1]:x.split()[0] for x in refs.splitlines() if x.strip()}
    if refs.get(f'refs/heads/{BRANCH}')!=HEAD or refs.get('refs/pull/409/head')!=HEAD: raise SystemExit('REFUSED: branch/pull refs')
    att={'repository':'snapetech-org/slskdN','pullRequest':409,'headRefName':BRANCH,'headRefOid':HEAD,'treeOid':TREE,'baseRefName':'main','baseRefOid':before['baseRefOid'],
      'state':'OPEN','draft':True,'branchRefOid':refs.get(f'refs/heads/{BRANCH}'),'pullRefOid':refs.get('refs/pull/409/head'),'pullMergeRefOid':refs.get('refs/pull/409/merge'),
      'liveBefore':before,'liveAfter':after,'localHead':git(repo,'rev-parse','HEAD'),'localTree':git(repo,'rev-parse','HEAD^{tree}'),'worktreeClean':True,'prBodyQueried':False}
    (ROOT/'head-tree-attestation.json').write_text(json.dumps(att,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    summary=j('summary.json'); ledger=rows('primary-review.jsonl'); corrections=rows('corrections.jsonl'); holds=rows('review-holds.jsonl')
    if (len(ledger),len(corrections),len(holds))!=(300,43,12): raise SystemExit('REFUSED: primary coverage')
    files=[]
    for p in sorted(x for x in ROOT.rglob('*') if x.is_file() and x.name not in {'manifest.json','SHA256SUMS.txt'} and '__pycache__' not in x.parts):
        files.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())})
    manifest={'artifact':'slskdN PR #409 W81 independent primary semantic review','schemaVersion':1,'repository':'snapetech-org/slskdN','pullRequest':409,
      'branch':BRANCH,'window':'W81','head':HEAD,'tree':TREE,'candidateFree':True,
      'candidateFreeInputManifestSha256':summary['candidateFreeInputManifestSha256'],'candidateFreeInputChecksumListSha256':summary['candidateFreeInputChecksumListSha256'],
      'sourceInventorySelectionSha256':summary['sourceInventorySelectionSha256'],'callerContextSha256':summary['callerContextSha256'],
      'sourceCurrentCellsSha256':summary['sourceCurrentCellsSha256'],'selectionBoundarySha256':summary['selectionBoundarySha256'],
      'sourceCount':25,'localeCount':12,'cellCount':300,'locales':LOCALES,'decisionCounts':summary['dispositions'],'proposalCount':43,'holdCount':12,
      'sourceRewriteRecommendations':1,'blindReviewUsed':False,'crossReviewUsed':False,'nativeSpeakerSignoff':False,'browserReview':False,'prBodyQueried':False,
      'liveBefore':before,'liveAfter':after,'files':files}
    (ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    names=sorted([x['path'] for x in files]+['manifest.json'])
    (ROOT/'SHA256SUMS.txt').write_text(''.join(f'{sha((ROOT/n).read_bytes())}  {n}\n' for n in names),encoding='utf-8')
    print(json.dumps({'result':'SEALED-PRIMARY','head':HEAD,'tree':TREE,'decisions':summary['dispositions'],'proposalCount':43,'holdCount':12,
      'packetFiles':len(names),'prBodyQueried':False},indent=2))
if __name__=='__main__': main()
