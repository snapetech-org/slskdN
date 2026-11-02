#!/usr/bin/env python3
"""Apply the exact 38 root-final W35 catalog targets after a fresh exact-head gate."""
import collections, hashlib, json, re, subprocess
from pathlib import Path

SCRATCH=Path('/mnt/disks/scratch/task-scratch/slskdn-manual-review-window35-91727326-20261102')
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261102/slskdn-pr409-w35-review')
BASE='917273260c49cca1c14576a0720fc84998d2846d'
TREE='1cdd8c831d224a5706ac6f3e465add4fd249d2be'
SOURCE_TREE='594e56c3f439bad476b1bd57e0de1665c62fa1bb'
REMOTE_REF='refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'
ROOT_SHA='9370973a90aaef1e6a597a4aa31d6bd21fedd4b7f8ded71f4d93ee0533d0f749'
INDEPENDENT_SHA='6053ad16c8c19ecccfcfb330987810b6f3fd30c19538b67e48488195e190a36f'
PLAN_SHA='fff13fd0e44f61ce78bf21d53136dd99bd8bcb2258662f4bf61ecfe454bc39fc'
LOCALES=['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
def sha(v): return hashlib.sha256(v if isinstance(v,bytes) else v.encode('utf-8')).hexdigest()
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args])
def git_text(*args): return git(*args).decode('utf-8').strip()
def require(ok,msg):
    if not ok: raise SystemExit('FAIL: '+msg)
def placeholders(v): return sorted(re.findall(r'\{[^{}]+\}',v))

plan_path=SCRATCH/'root-apply-plan-window35.jsonl'
require(sha(plan_path.read_bytes())==PLAN_SHA,'apply-plan checksum changed')
pre=json.loads((SCRATCH/'application-preflight-window35.json').read_text(encoding='utf-8'))
require(pre['result']=='READY_TO_APPLY' and pre['cellsToApply']==38,'application preflight is not ready')
require(pre['rootCrossReviewLedgerSha256']==ROOT_SHA and pre['independentFullReviewLedgerSha256']==INDEPENDENT_SHA,'cross-review ledger hashes changed')
require((pre['reviewBaseHead'],pre['reviewBaseTree'],pre['reviewBaseSourceSubtreeTree'])==(BASE,TREE,SOURCE_TREE),'preflight pins changed')
require(git_text('rev-parse','HEAD')==BASE and git_text('rev-parse','HEAD^{tree}')==TREE and git_text('rev-parse','HEAD:src/web/src')==SOURCE_TREE,'worktree pin moved')
require(not git_text('status','--porcelain'),'worktree is not clean before catalog application')
pr=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,mergeStateStatus,headRefOid,headRefName'],text=True))
require(pr=={'headRefName':'codex/slskdn-oidc-tooltip-localization-20261030','headRefOid':BASE,'isDraft':True,'mergeStateStatus':'CLEAN','state':'OPEN'},f'live PR moved: {pr}')
remote_rows=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin',REMOTE_REF],text=True).splitlines()
remote=remote_rows[0].split()[0] if remote_rows else ''
require(remote==BASE,f'remote PR branch moved: {remote}')
rows=[json.loads(x) for x in plan_path.read_text(encoding='utf-8').splitlines() if x.strip()]
require(len(rows)==38 and len({r['id'] for r in rows})==38,'apply plan row count/uniqueness mismatch')
per_locale=collections.Counter(r['locale'] for r in rows)
require(len(per_locale)==11,'expected 11 locale catalogs')
manifest=json.loads((SCRATCH/'manifest.json').read_text(encoding='utf-8'))
changed_by_locale={}
rendered={}
for locale in sorted(per_locale):
    path=f'src/web/public/locales/{locale}.json'
    raw=(REPO/path).read_bytes()
    require(sha(raw)==manifest['currentCatalogFileSha256'][locale],f'base catalog hash changed: {locale}')
    catalog=json.loads(raw.decode('utf-8'))
    require(len(catalog)==6169,'catalog key count mismatch: '+locale)
    entries=[r for r in rows if r['locale']==locale]
    keys=set()
    for row in entries:
        require(row['catalogPath']==path,f'catalog path mismatch: {row["id"]}')
        require(row['currentCatalogFileSha256']==manifest['currentCatalogFileSha256'][locale],f'catalog pin mismatch: {row["id"]}')
        require(row['currentPrHead']==BASE and row['currentPrTree']==TREE and row['currentSourceSubtreeTree']==SOURCE_TREE,f'git pin mismatch: {row["id"]}')
        key=row['catalogKey']
        require(key not in keys,f'duplicate catalog key in locale plan: {locale}/{key}')
        keys.add(key)
        require(catalog.get(key)==row['currentTarget'] and sha(row['currentTarget'])==row['currentTargetSha256'],f'current catalog value/hash mismatch: {row["id"]}')
        require(sha(row['source'])==row['sourceSha256'] and sha(row['finalTarget'])==row['finalTargetSha256'],f'source/final hash mismatch: {row["id"]}')
        require(placeholders(row['source'])==placeholders(row['currentTarget'])==placeholders(row['finalTarget'])==sorted(row['placeholders']),f'placeholder mismatch: {row["id"]}')
        for literal in row['protectedLiterals']:
            require(row['source'].count(literal)==row['currentTarget'].count(literal)==row['finalTarget'].count(literal),f'protected literal mismatch: {row["id"]}/{literal}')
        require(row['finalTarget']!=row['currentTarget'],'unexpected no-op target: '+row['id'])
        catalog[key]=row['finalTarget']
    out=(json.dumps(catalog,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf-8')
    rendered[locale]=out
    changed_by_locale[locale]=sorted(keys)

# Recheck pinned callers and their exact source lines immediately before writing.
caller_blobs={}
for row in rows:
    for call in row['sourceCallsites']:
        path=call['path']
        if path not in caller_blobs: caller_blobs[path]=git('show',f'{BASE}:{path}')
        raw=caller_blobs[path]
        require(sha(raw)==call['fileSha256'],f'caller file hash mismatch: {row["id"]}/{path}')
        lines=raw.decode('utf-8').splitlines()
        require(1<=call['line']<=len(lines),f'caller line out of range: {row["id"]}/{path}')
        line=lines[call['line']-1].strip()
        require(line==call['lineText'] and sha(line)==call['lineTextSha256'],f'caller line mismatch: {row["id"]}/{path}:{call["line"]}')

# All values have passed before any catalog write.
for locale,raw in rendered.items():
    (REPO/f'src/web/public/locales/{locale}.json').write_bytes(raw)

# Verify only requested cells changed in the local catalogs and no other path was touched.
for locale in sorted(per_locale):
    path=REPO/f'src/web/public/locales/{locale}.json'
    current=json.loads(path.read_text(encoding='utf-8'))
    base=json.loads(git('show',f'{BASE}:src/web/public/locales/{locale}.json').decode('utf-8'))
    require(set(current)==set(base) and len(current)==len(base)==6169,f'catalog key parity/count changed: {locale}')
    expected={r['catalogKey']:r['finalTarget'] for r in rows if r['locale']==locale}
    actual={k:v for k,v in current.items() if base[k]!=v}
    require(actual==expected,f'unintended catalog changes in {locale}')
allowed={f'src/web/public/locales/{locale}.json' for locale in per_locale}
changed=set(git_text('diff','--name-only',BASE,'--').splitlines())
require(changed==allowed,f'out-of-scope paths after apply: {sorted(changed^allowed)}')
require(not git_text('diff','--name-only',BASE,'--','.github/workflows'),'workflow path changed')
subprocess.check_call(['git','-C',str(REPO),'diff','--check',BASE])

applied=[]
for r in sorted(rows,key=lambda x:x['id']):
    applied.append({'schemaVersion':1,'applicationWindow':35,'id':r['id'],'locale':r['locale'],'sourceId':r['sourceId'],'source':r['source'],'sourceSha256':r['sourceSha256'],'catalogPath':r['catalogPath'],'catalogKey':r['catalogKey'],'oldTarget':r['currentTarget'],'oldTargetSha256':r['currentTargetSha256'],'newTarget':r['finalTarget'],'newTargetSha256':r['finalTargetSha256'],'candidateTarget':r['finalTarget'],'candidateTargetSha256':r['finalTargetSha256'],'applicationResult':'applied exact root-final target','rootDisposition':r['rootDisposition'],'rootReason':r['rootReason'],'sourceCallsites':r['sourceCallsites'],'prBaseHead':BASE,'prBaseTree':TREE,'sourceSubtreeTree':SOURCE_TREE,'rootLedgerSha256':ROOT_SHA,'independentLedgerSha256':INDEPENDENT_SHA})
(SCRATCH/'applied-corrections-window35.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in applied),encoding='utf-8')
report={'result':'LOCAL_CATALOG_APPLICATION_VERIFIED','window':35,'baseHead':BASE,'baseTree':TREE,'sourceSubtreeTree':SOURCE_TREE,'cellsApplied':len(applied),'catalogFilesChanged':len(per_locale),'cellsByLocale':dict(sorted(per_locale.items())),'changedKeysByLocale':changed_by_locale,'callerFilesPinned':len(caller_blobs),'callerLineReferences':sum(len(r['sourceCallsites']) for r in rows),'allCurrentFinalHashesPlaceholdersProtectedLiteralsVerified':True,'catalogKeyParity':'6,169 keys retained in each locale','catalogDiffPaths':sorted(changed),'workflowPathsChanged':[],'gitDiffCheck':'PASS','rootLedgerSha256':ROOT_SHA,'independentLedgerSha256':INDEPENDENT_SHA,'applyPlanSha256':sha(plan_path.read_bytes()),'appliedLedgerSha256':sha((SCRATCH/'applied-corrections-window35.jsonl').read_bytes()),'repositoryCatalogOnlyChanges':True,'noTestsBuildsScansCi':True}
(SCRATCH/'local-application-report-window35.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
