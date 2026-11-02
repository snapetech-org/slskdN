import hashlib,json,subprocess
from pathlib import Path
repo=Path('/mnt/disks/scratch/task-worktrees/localization-20261030/slskdn-pr409-batch4-docs-20261101');out=Path(__file__).parent
app='b38a95fb75ec4ac691ad02c4b2c7393f8a1389b7';base='fbafaae2e05af8ce51a263c7be2a92a8728ceb94';tree='f2e7a734d60555964f0487377066a955308fd8c9'
def g(*a):return subprocess.check_output(['git','-C',str(repo),*a],text=True).strip()
def run(*a):return subprocess.run(['git','-C',str(repo),*a]).returncode
def show(c,p):return subprocess.check_output(['git','-C',str(repo),'show',f'{c}:{p}'])
def sha(b):return hashlib.sha256(b).hexdigest()
head=g('rev-parse','HEAD');remote=subprocess.check_output(['git','-C',str(repo),'ls-remote','origin','refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'],text=True).split()[0]
pr=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,mergeStateStatus,headRefOid'],text=True))
paths=set(g('diff-tree','--no-commit-id','--name-only','-r',app).splitlines());expected={'docs/CHANGELOG.md'}|{f'src/web/public/locales/{x}.json' for x in ['ar','de','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']}
assert head==app and g('rev-parse',app+'^')==base and g('rev-parse',app+'^{tree}')==tree and remote==app
assert pr=={'state':'OPEN','isDraft':True,'mergeStateStatus':'CLEAN','headRefOid':app}
assert paths==expected and not g('status','--porcelain')
assert g('rev-parse',base+':.github/workflows')==g('rev-parse',app+':.github/workflows')
assert g('rev-parse',base+':src/web/src')==g('rev-parse',app+':src/web/src')
assert run('diff','--check',base,app)==0
audit=json.loads((out/'apply-audit-window31.json').read_text())
for loc,h in audit['newCatalogFileSha256'].items():assert sha(show(app,f'src/web/public/locales/{loc}.json'))==h
x={'result':'PASS','applicationCommit':app,'applicationTree':tree,'parentReviewHead':base,'remoteHead':remote,'livePrState':pr['state'],'livePrDraft':pr['isDraft'],'mergeStateStatus':pr['mergeStateStatus'],'commitPaths':sorted(paths),'workflowSubtreeEqual':True,'sourceCodeSubtreeEqual':True,'catalogHashesMatchPostApply':True,'diffCheck':'PASS','worktree':'clean','nativeSpeakerReview':'outstanding','testsBuildCiReleaseOrTag':'not run'}
(out/'post-commit-verification-window31.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');print(json.dumps(x,indent=2))
