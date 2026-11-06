import hashlib, json, subprocess
from pathlib import Path

ROOT=Path('/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn')
OUT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w43-spanish-formal-gap-primary-20261102')
REPO='snapetech-org/slskdN'
PR=409
BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
HEAD_EXPECTED='7fa557e4b3c433708bd490bd1fc9279c0539bc8f'
TREE_EXPECTED='fd4f7b6f33398fec278173fcf68a04d9c15bc94b'
SOURCE_ID='src_0ef5849949bcf7b6'
SOURCE='30D'
SOURCE_SHA='0ef5849949bcf7b63a4aafd392d689e6b689f7d94a5091a115fe1516bb753b9b'
CALLER='src/web/src/components/Player/PlayerBar.jsx'
CATALOG='src/web/public/locales/es.json'

def sha(b):
    if isinstance(b,str): b=b.encode()
    return hashlib.sha256(b).hexdigest()

def run(args):
    return subprocess.check_output(args,cwd=ROOT,text=True)

pr=json.loads(run(['gh','pr','view',str(PR),'--repo',REPO,'--json','state,isDraft,headRefOid,headRefName,baseRefOid,url']))
assert pr['state']=='OPEN' and pr['isDraft'] is True and pr['headRefOid']==HEAD_EXPECTED and pr['headRefName']==BRANCH
api_tree=run(['gh','api',f'repos/{REPO}/commits/{HEAD_EXPECTED}','--jq','.commit.tree.sha']).strip()
remote=run(['git','ls-remote','taskgithub',f'refs/heads/{BRANCH}']).split()[0]
head=run(['git','rev-parse','HEAD']).strip()
tree=run(['git','rev-parse','HEAD^{tree}']).strip()
assert (api_tree,remote,head,tree)==(TREE_EXPECTED,HEAD_EXPECTED,HEAD_EXPECTED,TREE_EXPECTED)
assert run(['git','status','--porcelain']).strip()==''

order_path=ROOT/'docs/pr-evidence/pr409-localization-2026-11-02/window43/primary/order-and-boundary.json'
order=json.loads(order_path.read_text())
row=next(x for x in order['sourceIdsByOrdinal'] if x['sourceOrdinal']==87)
assert row['sourceId']==SOURCE_ID and row['source']=='30D' and row['sourceSha256']==SOURCE_SHA

caller_raw=subprocess.check_output(['git','show',f'HEAD:{CALLER}'],cwd=ROOT)
lines=caller_raw.decode().splitlines()
line_no=1337
assert lines[line_no-1].strip()=='{ label: interfaceText("30D"), value: 30 },'
caller_context=lines[line_no-2:line_no+3]
for expected in ['7D','30D','90D','All']:
    assert any(expected in line for line in caller_context)

catalog_raw=subprocess.check_output(['git','show',f'HEAD:{CATALOG}'],cwd=ROOT)
catalog=json.loads(catalog_raw)
assert len(catalog)==6170 and catalog['30D']=='30 d'
assert catalog['7D']=='7 d' and catalog['90D']=='90 d' and catalog['All']=='Todos'
catalog_blob=run(['git','rev-parse',f'HEAD:{CATALOG}']).strip()
caller_blob=run(['git','rev-parse',f'HEAD:{CALLER}']).strip()

cell={
 'sourceOrdinal':87,'sourceId':SOURCE_ID,'source':'30D','sourceSha256':SOURCE_SHA,
 'locale':'es','catalogPath':CATALOG,'catalogBlob':catalog_blob,'catalogFileSha256':sha(catalog_raw),
 'catalogKeyCount':len(catalog),'currentTarget':catalog['30D'],'currentTargetSha256':sha(catalog['30D']),
 'recommendedTarget':'30 d','recommendedTargetSha256':sha('30 d'),'disposition':'accept-current',
 'callerPath':CALLER,'callerBlob':caller_blob,'callerFileSha256':sha(caller_raw),'callerLine':line_no,
 'callerLineText':lines[line_no-1],'callerLineSha256':sha(lines[line_no-1]),
 'callerContextBefore':lines[line_no-3:line_no-1],'callerContextAfter':lines[line_no:line_no+2],
 'rationale':'The adjacent PlayerBar filter options 7D, 30D, and 90D are numeric durations. Spanish 30 d uses d as the international symbol for day and contains no person, verb, pronoun, or address form that distinguishes formal from informal register. This exact cell is therefore register-neutral; the missing formal-lane accumulator does not change its value.',
 'registerApplicability':'none; numeric unit label has no address/register choice',
 'externalReference':'https://www.bipm.org/documents/20126/41483022/SI-Brochure-9.pdf/fcf090b2-04e6-88cc-1149-c3e029ad8232',
 'nativeSpeakerApproval':False
}
(OUT/'cell-review.json').write_text(json.dumps(cell,ensure_ascii=False,indent=2)+'\n')
(OUT/'live-head.json').write_text(json.dumps({'repository':REPO,'pullRequest':PR,'state':pr['state'],'isDraft':pr['isDraft'],'url':pr['url'],'branch':BRANCH,'head':head,'tree':tree,'apiTree':api_tree,'remoteHead':remote,'worktreeStatus':''},indent=2)+'\n')
(OUT/'README.md').write_text(f'''# slskdN PR #409 W43 Spanish formal-lane gap review

At exact OPEN/DRAFT PR head {head} / tree {tree}, reattested the one Spanish cell previously left without a formal-lane verdict: source ordinal 87, {SOURCE_ID}, source {SOURCE}, at {CALLER}:{line_no}.

The exact caller groups the filter options 7D, 30D, 90D, and All. The current Spanish value is 30 d, matching 7 d and 90 d. The International System of Units brochure published by BIPM lists d as the symbol for day: {cell['externalReference']}. The numeric label has no person, verb, pronoun, or address form, so formal versus informal Spanish register does not apply. The primary disposition is accept-current; an independent cross-review is required before the W43 cell is marked closed.

No repository or PR files were changed. This static language review does not establish native-speaker approval. No tests, builds, scans, CI, browser work, releases, tags, or merges ran.
''')
summary={'result':'PRIMARY_REVIEW_COMPLETE_PENDING_INDEPENDENT_CROSS_REVIEW','window':43,'pullRequest':PR,'head':head,'tree':tree,'sourceOrdinal':87,'sourceId':SOURCE_ID,'source':'30D','locale':'es','currentTarget':'30 d','disposition':'accept-current','formalRegisterApplicable':False,'callerReattested':True,'nativeSpeakerApproval':False,'repositoryModified':False,'testsBuildsCiRun':False}
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name not in ('SHA256SUMS','manifest.json'))
(OUT/'SHA256SUMS').write_text(''.join(f'{sha(p.read_bytes())}  {p.name}\n' for p in files))
manifest={'repository':REPO,'pullRequest':PR,'head':head,'tree':tree,'sourceOrdinal':87,'cellCount':1,'files':[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in files],'sha256SumsSha256':sha((OUT/'SHA256SUMS').read_bytes())}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'path':str(OUT),'summary':summary,'sha256SumsSha256':sha((OUT/'SHA256SUMS').read_bytes())}))
