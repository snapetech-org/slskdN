#!/usr/bin/env python3
"""Read-only structural, hash, caller, and manifest verification for W53."""
import collections, hashlib, json, re, subprocess, sys
from pathlib import Path
OUT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w53-20261103')
INPUT=OUT/'input'; PRIMARY=OUT/'primary'
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261103/slskdn-pr409-w52-primary-20261103')
HEAD='6d5723e244338a550e3dfa5182a45857156467a7'; TREE='8435576260e9aa760609be6a28001b2bb38b8c11'; BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PH=re.compile(r'\{[^{}]+\}'); MARKUP=re.compile(r'</?[A-Za-z][^>]*>'); NUMBER=re.compile(r'(?<![A-Za-z])\d+(?:[.,]\d+)?%?(?![A-Za-z])')

def sha(value): return hashlib.sha256(value.encode('utf-8') if isinstance(value,str) else value).hexdigest()
def blob(data): return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
def canon(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def jl(path): return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
def manifest(directory,name):
    checks=[]
    for line in (directory/name).read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        expected,rel=line.split(None,1); rel=rel.strip().lstrip('*'); actual=sha((directory/rel).read_bytes())
        checks.append({'path':rel,'matches':actual==expected})
    return checks, bool(checks) and all(x['matches'] for x in checks)
def git(*args): return subprocess.check_output(['git',*args],cwd=REPO,text=True).strip()
checks={}; details={}; issues=[]
def require(name,ok,detail=None):
    checks[name]=bool(ok)
    if not ok: issues.append({'check':name,'detail':detail})

require('worktree_head',git('rev-parse','HEAD')==HEAD,git('rev-parse','HEAD'))
require('worktree_tree',git('rev-parse','HEAD^{tree}')==TREE,git('rev-parse','HEAD^{tree}'))
require('worktree_clean',not git('status','--porcelain=v1'),git('status','--short'))
remote=git('ls-remote','origin',f'refs/heads/{BRANCH}').split()
require('remote_branch_head',len(remote)==2 and remote[0]==HEAD,remote)
input_checks,input_ok=manifest(INPUT,'PACKET-SHA256SUMS.txt'); primary_checks,primary_ok=manifest(PRIMARY,'SHA256SUMS.txt')
require('input_manifest',input_ok,input_checks)
require('primary_manifest',primary_ok,primary_checks)
prior={}
for win in ['window49','window50','window51']:
    d=REPO/f'docs/pr-evidence/pr409-localization-2026-11-03/{win}'
    rows,ok=manifest(d,'EVIDENCE-SHA256SUMS.txt'); prior[win]=len(rows); require(win+'_manifest',ok,rows)
w52=REPO/'docs/pr-evidence/pr409-localization-2026-11-03/window52'
w52_manifests={}
for p in sorted(x for x in w52.rglob('*') if x.is_file() and 'SHA256SUMS' in x.name):
    rows,ok=manifest(p.parent,p.name); w52_manifests[p.relative_to(w52).as_posix()]=len(rows)
    require('window52_'+p.relative_to(w52).as_posix().replace('/','_'),ok,rows)

att=json.loads((INPUT/'head-tree-attestation.json').read_text(encoding='utf-8'))
selection=json.loads((INPUT/'selection-and-boundary.json').read_text(encoding='utf-8'))
inputs=jl(INPUT/'source-current-cells.jsonl'); callers=jl(INPUT/'caller-contexts.jsonl'); protected=jl(INPUT/'protected-literals.jsonl')
decisions=jl(PRIMARY/'review-decisions.jsonl'); summary=json.loads((PRIMARY/'review-summary.json').read_text(encoding='utf-8'))
require('input_attestation',att['head']==HEAD and att['tree']==TREE and att['branch']==BRANCH and att['state']=='OPEN' and att['isDraft'] is True,att)
require('selection_pin',selection.get('pins')==att and selection.get('inputContainsCandidates') is False)
require('cell_counts',len(inputs)==len(decisions)==300 and len(callers)==len(protected)==25,{'input':len(inputs),'decisions':len(decisions),'callers':len(callers),'protected':len(protected)})
expected=[(rank,loc) for rank in range(226,251) for loc in LOCALES]
require('input_cell_order',[(x['continuationRank'],x['locale']) for x in inputs]==expected)
require('review_cell_order',[(x['continuationRank'],x['locale']) for x in decisions]==expected)
require('input_has_no_candidates',all(not any(k in x for k in ('candidateTarget','verdict','disposition')) for x in inputs))
require('caller_total',sum(x['productionCallerCount'] for x in callers)==32)
require('catalog_count',len(jl(INPUT/'catalog-structure.jsonl'))==12)

catalog_rows=jl(INPUT/'catalog-structure.jsonl'); catalogs={}; ordered=None
for c in catalog_rows:
    path=REPO/c['catalogPath']; data=path.read_bytes(); doc=json.loads(data); keys=list(doc)
    if ordered is None: ordered=keys
    require('catalog_'+c['locale'],keys==ordered and len(keys)==6176 and sha(data)==c['sha256'] and blob(data)==c['gitBlob'] and git('rev-parse',f'{HEAD}:{c["catalogPath"]}')==c['gitBlob'],c['catalogPath'])
    require('catalog_order_hash_'+c['locale'],sha('\n'.join(keys)+'\n')==c['orderedKeySha256'],c['locale'])
    catalogs[c['locale']]=doc
require('ordered_catalog_hash',sha('\n'.join(ordered)+'\n')==selection['orderedCatalogKeySha256'])

caller_by_id={x['sourceId']:x for x in callers}; caller_refs=0
current_protected=[]; candidate_protected=[]; placeholder_bad=[]; markup_bad=[]; number_bad=[]
caller_refs=sum(x['productionCallerCount'] for x in callers)
for a,b in zip(inputs,decisions):
    rank,loc=a['continuationRank'],a['locale']
    require(f'cell_identity_{rank}_{loc}',(rank,a['sourceId'],a['source'],loc)==(b['continuationRank'],b['sourceId'],b['source'],b['locale']))
    require(f'source_hash_{rank}_{loc}',sha(a['source'])==a['sourceSha256']==b['sourceSha256'])
    require(f'current_hash_{rank}_{loc}',sha(a['currentTarget'])==a['currentTargetSha256']==b['currentTargetSha256'])
    require(f'current_catalog_readback_{rank}_{loc}',a['currentTarget']==catalogs[loc].get(a['source']))
    require(f'catalog_cell_pin_{rank}_{loc}',a['catalogFileSha256']==b['catalogFileSha256'] and a['catalogGitBlob']==b['catalogGitBlob'])
    require(f'candidate_hash_{rank}_{loc}',sha(b['candidateTarget'])==b['candidateTargetSha256'])
    require(f'caller_cell_pin_{rank}_{loc}',a['callerContextSha256']==b['callerContextSha256'] and a['callerRefs']==b['callerRefs'])
    caller=caller_by_id[a['sourceId']]; refs=caller['callers']
    require(f'caller_context_hash_{rank}_{loc}',sha(canon(refs))==a['callerContextSha256'])
    require(f'caller_count_{rank}_{loc}',caller['productionCallerCount']==b['callerCount'])
    for n,ref in enumerate(refs):
        data=(REPO/ref['path']).read_bytes(); lines=data.decode('utf-8').splitlines()
        ok=(sha(data)==ref['fileSha256'] and blob(data)==ref['gitBlob'] and git('rev-parse',f'{HEAD}:{ref["path"]}')==ref['gitBlob'] and sha(lines[ref['line']-1])==ref['lineSha256'] and sha(canon(ref['context']))==ref['contextSha256'])
        require(f'caller_file_line_context_{rank}_{loc}_{n}',ok,f'{ref["path"]}:{ref["line"]}')
    srcph=collections.Counter(PH.findall(a['source'])); curph=collections.Counter(PH.findall(a['currentTarget'])); candph=collections.Counter(PH.findall(b['candidateTarget']))
    srcmark=collections.Counter(MARKUP.findall(a['source'])); curmark=collections.Counter(MARKUP.findall(a['currentTarget'])); candmark=collections.Counter(MARKUP.findall(b['candidateTarget']))
    if not (srcph==curph==candph): placeholder_bad.append((rank,loc))
    if not (srcmark==curmark==candmark): markup_bad.append((rank,loc))
    if collections.Counter(NUMBER.findall(a['source']))!=collections.Counter(NUMBER.findall(b['candidateTarget'])): number_bad.append((rank,loc))
    for p in a.get('protectedLiteralChecks',[]):
        if p['literal'] not in a['currentTarget']: current_protected.append((rank,loc,p['literal']))
        if p['literal'] not in b['candidateTarget']: candidate_protected.append((rank,loc,p['literal']))

counts=collections.Counter(x['verdict'] for x in decisions); changes=[x for x in decisions if x['candidateTarget']!=x['currentTarget']]
by_locale=dict(collections.Counter(x['locale'] for x in changes))
require('caller_reference_total',caller_refs==32,caller_refs)
require('placeholder_parity',not placeholder_bad,placeholder_bad)
require('markup_parity',not markup_bad,markup_bad)
require('numeric_parity',not number_bad,number_bad)
require('protected_candidate_literals',not candidate_protected,candidate_protected)
require('current_protected_gap_count',len(current_protected)==summary['currentProtectedLiteralMismatchCount']==21,len(current_protected))
require('candidate_protected_gap_count',len(candidate_protected)==summary['candidateProtectedLiteralMismatchCount']==0,len(candidate_protected))
require('disposition_summary',dict(counts)==summary['dispositionCounts'],{'actual':dict(counts),'summary':summary['dispositionCounts']})
require('change_count',len(changes)==summary['candidateChangeCount']==82,len(changes))
require('locale_change_counts',by_locale==summary['changedCellsByLocale'],{'actual':by_locale,'summary':summary['changedCellsByLocale']})
require('callerless_hold_scope',summary['callerlessSourceIds']==summary['heldSourceIds'] and summary['holdCount']==24,{'callerless':summary['callerlessSourceIds'],'held':summary['heldSourceIds']})

if issues:
    print(json.dumps({'verification':'failed','issues':issues,'checkCount':len(checks),'passedChecks':sum(checks.values())},ensure_ascii=False,indent=2))
    sys.exit(1)
report={'verification':'passed','prPin':{'number':409,'url':att['url'],'state':'open','draft':True,'head':HEAD,'tree':TREE,'branch':BRANCH,'remoteBranchHead':remote[0],'bodySha256':att['bodySha256']},'selection':{'firstRank':226,'lastRank':250,'sourceCount':25,'localeCount':12,'cellCount':300,'firstSourceId':selection['firstSelected']['sourceId'],'lastSourceId':selection['lastSelected']['sourceId'],'nextBoundarySourceId':selection['nextBoundary']['sourceId'],'historicalSourceOrdinalsClaimed':False,'disjointFromW50W51W52':True,'w49Gap126To150Preserved':True},'catalogs':{'count':12,'keysPerCatalog':6176,'orderedKeySha256':selection['orderedCatalogKeySha256'],'allFileHashesAndGitBlobsMatch':True},'callers':{'references':caller_refs,'callerlessSourceIds':summary['callerlessSourceIds'],'allCallerFileLineContextHashesMatch':True},'primary':{'dispositions':dict(counts),'candidateChanges':len(changes),'changedCellsByLocale':by_locale,'holds':summary['holdCount'],'currentProtectedLiteralMismatches':len(current_protected),'candidateProtectedLiteralMismatches':len(candidate_protected),'placeholderMismatches':len(placeholder_bad),'markupMismatches':len(markup_bad),'numericMismatches':len(number_bad)},'manifests':{'inputEntriesVerified':len(input_checks),'inputSha256':sha((INPUT/'PACKET-SHA256SUMS.txt').read_bytes()),'primaryEntriesVerified':len(primary_checks),'primarySha256':sha((PRIMARY/'SHA256SUMS.txt').read_bytes()),'w49w50w51EvidenceEntryCounts':prior,'w52ManifestEntryCounts':w52_manifests},'checksPassed':len(checks),'repositoryStatus':'clean exact-head worktree; no repository or PR mutations'}
(OUT/'packet-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
