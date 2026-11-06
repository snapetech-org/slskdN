from __future__ import annotations
import hashlib,json,re,subprocess,pathlib,collections
from datetime import datetime,timezone
OUT=pathlib.Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window46-reconstructed-ranks26-50-primary-20261102')
W44=pathlib.Path('/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn/docs/pr-evidence/pr409-localization-2026-11-02/window45-reconstructed-ranks1-25')
WORK=pathlib.Path('/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn')
HEAD='31544a6ef15db2f8481dd76aa9c10844ec3164ba'; TREE='fe94582c3e13f0f567fbfa6c3abac6e8558ba17d'
BRANCH='codex/slskdn-localization-apply-20261102'; PR_BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
REPOS=[('SeerrNG',418),('ChaptarrNG',190),('QuestarrNG',155),('ROMarrNG',70),('slskR',204),('slskdN',409),('TorrentNG',243)]
def sha(b):return hashlib.sha256(b if isinstance(b,bytes) else b.encode()).hexdigest()
def jbytes(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def git(*args):return subprocess.check_output(['git','-C',str(WORK),*args])
def readjl(p):return [json.loads(x) for x in pathlib.Path(p).read_text().splitlines() if x.strip()]
def writejl(p,rows):pathlib.Path(p).write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rows))
def writej(p,x):pathlib.Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
def verify_manifest(root,manifest):
    out=subprocess.run(['sha256sum','-c',str(manifest)],cwd=root,text=True,capture_output=True)
    assert out.returncode==0,out.stdout+out.stderr
    return {'path':str(manifest),'sha256':sha(manifest.read_bytes()),'entries':len(out.stdout.splitlines()),'verified':True}
def query_live():
    rows=[]
    for repo,n in REPOS:
        pr=json.loads(subprocess.check_output(['gh','pr','view',str(n),'--repo',f'snapetech-org/{repo}','--json','number,state,isDraft,headRefName,headRefOid,baseRefName,baseRefOid,url'],text=True))
        tree=json.loads(subprocess.check_output(['gh','api',f"repos/snapetech-org/{repo}/git/commits/{pr['headRefOid']}"],text=True))['tree']['sha']
        row={'repository':f'snapetech-org/{repo}',**pr,'headTree':tree}
        if n==409:row['remoteBranchOid']=subprocess.check_output(['git','ls-remote','https://github.com/snapetech-org/slskdN.git',f"refs/heads/{pr['headRefName']}"],text=True).split()[0]
        rows.append(row)
    return rows
# Exact current tree/worktree and live PR pins.
assert git('rev-parse','HEAD').decode().strip()==HEAD and git('rev-parse','HEAD^{tree}').decode().strip()==TREE
assert git('branch','--show-current').decode().strip()==BRANCH and git('status','--porcelain').decode().strip()==''
live=query_live(); p409=next(x for x in live if x['number']==409)
assert p409['state']=='OPEN' and p409['isDraft'] and p409['headRefOid']==HEAD and p409['headTree']==TREE and p409['remoteBranchOid']==HEAD
assert subprocess.check_output(['git','-C',str(WORK),'ls-remote','origin',f"refs/heads/{p409['headRefName']}"],text=True).split()[0]==HEAD
# Verify committed W45 evidence and both nested primary/cross-review manifests.
root_manifest=verify_manifest(W44,W44/'SHA256SUMS.txt')
primary_dir=W44/'primary'; cross_dir=W44/'crossreview'
primary_manifest=verify_manifest(primary_dir,primary_dir/'SHA256SUMS.txt')
cross_manifest=verify_manifest(cross_dir,cross_dir/'SHA256SUMS.txt')
w44_prior=readjl(primary_dir/'prior-source-ids.jsonl'); w44_selected=readjl(primary_dir/'pending-source-selection.jsonl')
assert len(w44_prior)==1097 and len({x['sourceId'] for x in w44_prior})==1097
assert len(w44_selected)==25 and [x['selectionRank'] for x in w44_selected]==list(range(1,26))
w44_prior_ids={x['sourceId'] for x in w44_prior}
prior={}
for x in w44_prior:
    sid=x['sourceId']; src=x['source']; sh=sha(src)
    assert sid=='src_'+sh[:16] and x['sourceSha256']==sh
    assert sid not in prior
    prior[sid]={'sourceId':sid,'source':src,'sourceSha256':sh,'originWindows':x.get('windows',[]),'origin':'W1-W44 prior evidence'}
for x in w44_selected:
    sid=x['sourceId']; src=x['source']; sh=sha(src)
    assert sid=='src_'+sh[:16] and x['sourceSha256']==sh and sid not in prior
    prior[sid]={'sourceId':sid,'source':src,'sourceSha256':sh,'originWindows':[45],'sourceOrdinal':None,'origin':'W45 reconstructed selection'}
assert len(prior)==1122
# Reattest the committed W45 apply readback against current catalog values.
apply_rows=readjl(W44/'application/apply-readback.jsonl')
assert len(apply_rows)==300 and len({(x['selectionRank'],x['locale']) for x in apply_rows})==300
apply_map={x['sourceId']:x for x in apply_rows}
assert set(apply_map)=={x['sourceId'] for x in w44_selected}
# Load exact current catalogs and ordered English-source keys.
catalogs={}; catalog_pins={}; ordered_keys=None
for loc in LOCALES:
    rel=f'src/web/public/locales/{loc}.json'; raw=git('show',f'{HEAD}:{rel}'); obj=json.loads(raw)
    if ordered_keys is None:ordered_keys=list(obj)
    else:assert list(obj)==ordered_keys,(loc,'ordered key mismatch')
    assert len(obj)==6170 and len(set(obj))==6170
    catalogs[loc]=obj
    catalog_pins[loc]={'path':rel,'blobOid':git('rev-parse',f'{HEAD}:{rel}').decode().strip(),'fileSha256':sha(raw),'bytes':len(raw),'entryCount':len(obj)}
source_ids={f"src_{sha(k)[:16]}":k for k in ordered_keys}
assert len(source_ids)==6170
for sid,src in prior.items():assert source_ids.get(sid)==src['source']
for row in apply_rows:
    loc=row['locale']; src=row['sourceText']; cur=catalogs[loc][src]
    assert row['sourceSha256']==sha(src) and row['finalTarget']==cur and row['finalTargetSha256']==sha(cur) and row['readbackTargetSha256']==sha(cur)
    assert row['catalogPath']==catalog_pins[loc]['path']
# Reconstruct the stable sorted pending queue after W1-W44, verify W45 ranks 1-25, then take ranks 26-50.
pending_after_w44=sorted(set(source_ids)-set(w44_prior_ids))
assert len(pending_after_w44)==5073
assert pending_after_w44[:25]==[x['sourceId'] for x in w44_selected]
selected_ids=pending_after_w44[25:50]
pending=sorted(set(source_ids)-set(prior))
assert len(pending)==5048 and pending[:25]==selected_ids
selected=[]
for rank,sid in enumerate(selected_ids,26):
    selected.append({'selectionRank':rank,'sourceId':sid,'source':source_ids[sid],'sourceSha256':sha(source_ids[sid]),'sourceOrdinal':None,
      'selectionBasis':'ranks 26-50 in lexicographically sorted pending source IDs after W1-W44 stable-ID exclusion; W45 ranks 1-25 are reattested and excluded; historical ordinal not established'})
# Scan tracked code for direct localization references and other exact literal use; pin source lines/files.
tracked=git('ls-files','src/web/src').decode().splitlines()
file_bytes={}; file_lines={}
for rel in tracked:
    raw=(WORK/rel).read_bytes()
    try: lines=raw.decode('utf-8').splitlines()
    except UnicodeDecodeError: continue
    file_bytes[rel]=raw; file_lines[rel]=lines

def direct_patterns(src):
    q=re.escape(src); quote=r'(["\'])'
    return [
      re.compile(r'interface(?:Attribute|Toast)?Text(?:Props|Output)?\s*\(\s*'+quote+q+r'\1'),
      re.compile(r'(?:LocalizedText|LocalizedOutputText|LocalizedRichText)\s+source\s*=\s*\{\s*'+quote+q+r'\1'),
      re.compile(r'(?:LocalizedText|LocalizedOutputText|LocalizedRichText)\s+source\s*=\s*'+quote+q+r'\1'),
      re.compile(r'getApiErrorMessageOutput\s*\(\s*'+quote+q+r'\1'),
      re.compile(r'\bt\s*\(\s*'+quote+q+r'\1'),
    ]
blob_cache={}
def make_ref(src,sid,rel,n,role,exact=True):
    lines=file_lines[rel]; raw=file_bytes[rel]
    if rel not in blob_cache: blob_cache[rel]=git('rev-parse',f'{HEAD}:{rel}').decode().strip()
    return {'sourceId':sid,'source':src,'sourceSha256':sha(src),'path':rel,'line':n,'lineText':lines[n-1],
      'lineSha256':sha(lines[n-1]),'fileSha256':sha(raw),'blobOid':blob_cache[rel],
      'contextBefore':lines[max(0,n-4):n-1],'contextAfter':lines[n:min(len(lines),n+3)],'referenceRole':role,
      'exactSourceLiteralMatch':exact,'verifiedAtCurrentHead':True}
callers=[]; hits=[]
for item in selected:
    src=item['source']; sid=item['sourceId']; refs=[]; pats=direct_patterns(src)
    for rel,lines in file_lines.items():
        is_test=any(token in pathlib.PurePosixPath(rel).name for token in ('.test.','.spec.','.stories.'))
        for n,line in enumerate(lines,1):
            direct=any(p.search(line) for p in pats)
            # Exact quoted source key references catch maps/data passed to dynamic localizers.
            quoted=bool(re.search(r'(["\'])'+re.escape(src)+r'\1',line))
            if not direct and not quoted: continue
            role='direct-localized-caller' if direct and not is_test else ('test-or-story-reference' if is_test else 'exact-literal-reference')
            refs.append(make_ref(src,sid,rel,n,role,True))
    uniq={(x['path'],x['line'],x['referenceRole']):x for x in refs}
    refs=sorted(uniq.values(),key=lambda x:(x['path'],x['line'],x['referenceRole']))
    prod=[x for x in refs if x['referenceRole']=='direct-localized-caller']
    status='production-localization-reference-found' if prod else 'no-production-localization-caller-found'
    callers.append({'sourceId':sid,'source':src,'sourceSha256':item['sourceSha256'],'selectionRank':item['selectionRank'],
      'callerSearchScope':'all tracked src/web/src files at exact head; exact localizer calls and exact quoted keys; tests/stories separately labelled',
      'callerUseStatus':status,'callerRefs':refs,'callerReferenceCount':len(refs),'productionLocalizationReferenceCount':len(prod),
      'contextSummary':None})
    hits.extend(refs)
# W1-W45 stable IDs remain in current source inventory; reconstructed ranks 26-50 are unique/disjoint.
assert len({x['sourceId'] for x in selected})==25 and not(set(selected_ids)&set(prior))
assert all(x['sourceOrdinal'] is None for x in selected)
# Write exact current-value input rows, source inventory, and caller refs for semantic review.
input_rows=[]
for item in selected:
    for loc in LOCALES:
        src=item['source']; value=catalogs[loc][src]; pin=catalog_pins[loc]
        input_rows.append({'exactHead':HEAD,'exactTree':TREE,'selectionRank':item['selectionRank'],'sourceOrdinal':None,'sourceId':item['sourceId'],
          'source':src,'sourceSha256':sha(src),'locale':loc,'catalogPath':pin['path'],'catalogBlobOid':pin['blobOid'],'catalogFileSha256':pin['fileSha256'],
          'currentTarget':value,'currentTargetSha256':sha(value)})
assert len(input_rows)==300
inventory=[{'sourceId':sid,'source':src,'sourceSha256':sha(src),'previouslyProcessed':sid in prior,'selectionRank':next((x['selectionRank'] for x in selected if x['sourceId']==sid),None)} for sid,src in source_ids.items()]
writejl(OUT/'source-inventory.jsonl',inventory)
writejl(OUT/'prior-source-ids.jsonl',[prior[k] for k in sorted(prior)])
writejl(OUT/'source-selection.jsonl',selected)
writejl(OUT/'input-cells.jsonl',input_rows)
writejl(OUT/'caller-context.jsonl',callers)
writejl(OUT/'caller-source-hits.jsonl',hits)
writej(OUT/'catalog-structure.json',{'exactHead':HEAD,'exactTree':TREE,'sourceCatalogCount':12,'orderedKeyCount':len(ordered_keys),'orderedKeySha256':sha(json.dumps(ordered_keys,ensure_ascii=False,separators=(',',':'))),'priorStableSourceIdsW1W45':len(prior),'pendingAfterExclusion':len(pending),'pendingAfterW1W44':len(pending_after_w44),'selectedRanks':[26,50],'historicalOrdinalRange':None,'catalogs':[catalog_pins[x] for x in LOCALES]})
writej(OUT/'input-integrity.json',{'exactHead':HEAD,'exactTree':TREE,'worktree':str(WORK),'worktreeBranch':BRANCH,'worktreeStatus':'clean','pr409State':'OPEN','pr409IsDraft':True,'pr409RemoteHead':HEAD,'liveSevenPrSnapshot':live,'w45EvidenceRootManifest':root_manifest,'w45PrimaryManifest':primary_manifest,'w45CrossreviewManifest':cross_manifest,'w1ThroughW44StableIDs':1097,'w45SelectedIDs':len(w44_selected),'w45ApplyRowsReattested':len(apply_rows),'w1ThroughW45StableUniqueIDs':len(prior),'pendingIDs':len(pending),'selectedIDs':len(selected),'callerReferences':len(hits),'callerRowsWithProductionDisplay':sum(x['callerUseStatus']=='production-localization-reference-found' for x in callers),'readOnly':True,'testsBuildsCiBrowserRun':False})
writej(OUT/'selection-method.json',{'windowLabel':'W46 deterministic reconstruction ranks 26-50; historical ordinal boundary unavailable','selectionMethod':'Use the committed W45 primary prior-source-ids list for W1-W44 (1,097 unique IDs), reattest the 25 W45 selected IDs and readbacks at current catalogs, exclude all 1,122 W1-W45 IDs from the exact current inventory, sort the W1-W44 pending IDs lexicographically, verify W45 ranks 1-25, and select ranks 26-50. No historical ordinal is claimed.','sourceOrdinalRange':None,'selectionRankRange':[26,50],'priorW1W44IDs':1097,'w45IDs':len(w44_selected),'priorW1W45UniqueIDs':len(prior),'currentSourceKeyInventory':len(source_ids),'pendingAfterExclusion':len(pending),'pendingBeforeW45Exclusion':len(pending_after_w44),'selectedIds':[{'rank':x['selectionRank'],'sourceId':x['sourceId'],'source':x['source'],'sourceSha256':x['sourceSha256'],'sourceOrdinal':None} for x in selected],'historicalOrdinalStillUnavailable':'This reconstructed selection is not represented as the historical W46 ordinal range.'})
print(json.dumps({'head':HEAD,'tree':TREE,'w1W45IDs':len(prior),'pending':len(pending),'selected':[{k:x[k] for k in ('selectionRank','sourceId','source')} for x in selected],'callerRefs':len(hits),'callerUseStatus':{x['sourceId']:x['callerUseStatus'] for x in callers}},ensure_ascii=False,indent=2))
