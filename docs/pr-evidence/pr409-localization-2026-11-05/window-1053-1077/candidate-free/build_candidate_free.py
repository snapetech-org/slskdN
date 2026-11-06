#!/usr/bin/env python3
from __future__ import annotations
import collections, datetime as dt, hashlib, json, re, subprocess, sys, unicodedata
from pathlib import Path

OUT=Path(__file__).resolve().parent
REPO=Path(sys.argv[1]).resolve()
PREV=OUT.parent.parent/'window-1028-1052/candidate-free'
W1003_INPUT=OUT.parent/'lineage/w1003-candidate-free'
ROOT_APP=REPO/'docs/pr-evidence/pr409-localization-2026-11-05/window-1003-1027/root-application'
PREV_WINDOW_DIR=REPO/'docs/pr-evidence/pr409-localization-2026-11-05/window-1028-1052'
PREV_ROOT_APP=PREV_WINDOW_DIR/'root-application'
HEAD='ba692c15ca54942108cc9da37757f585969e6173'
TREE='27c09a8fe24030f5bb0995d809794a9e4829dc64'
BASE='f25d263a2a7cdb2c8f76c40c346cb10f749a9356'
BASETREE='b2ce36e07aee6ade05e6d8795d04b9a7455a081f'
MAIN='bc6251ff4ea5a7e59f2d86e2400c90520601f46e'
MAINTREE='4232b318aeaab4c327443638e5467ca089bbed53'
BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
SLUG='snapetech-org/slskdN'
REMOTE='https://github.com/snapetech-org/slskdN.git'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
FIRST,LAST=1053,1077
QFIRST,QLAST=953,977
TEXT_KEYS={'source','sourceText','target','currentTarget','proposedTarget','proposedTargetText','candidateTarget','reviewTarget','rationale','reason','before','after','actualValue','expectedValue'}

def need(ok,msg):
    if not ok: raise SystemExit('REFUSED: '+msg)
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def blobsha(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args])
def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def readjl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def writej(name,o): (OUT/name).write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def writejl(name,rows): (OUT/name).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
def parseobj(raw,label):
    dup=[]
    def pairs(ps):
        out={}
        for k,v in ps:
            if k in out: dup.append(k)
            out[k]=v
        return out
    out=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs)
    need(isinstance(out,dict) and not dup,label+' malformed/duplicate JSON')
    return out
def verify_sums(root):
    sums={}
    for line in (root/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1)
        need(n not in sums and (root/n).is_file() and sha((root/n).read_bytes())==h,'prior checksum '+n)
        sums[n]=h
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    need(actual==set(sums),'prior checksum inventory')
    return sums
def production_path(path):
    parts=path.split('/'); name=parts[-1]
    return path.startswith('src/web/src/') and Path(path).suffix.lower() in {'.js','.jsx','.ts','.tsx'} and not any(p in {'__tests__','__specs__'} for p in parts) and not any(x in name for x in ('.test.','.spec.'))
def token_data(source,target):
    placeholders=lambda s:collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s))
    tags=lambda s:collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',s))
    nums=lambda s:[''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in t) for t in re.findall(r'\d+',s)]
    protected=lambda s:sorted(set(re.findall(r'\b[A-Z][A-Z0-9]{1,}\b',s))|{x for x in ('slskdN','PodCore','Wishlist','soulfind','FFmpeg','Lidarr') if x in s})
    sp,tp=placeholders(source),placeholders(target); st,tt=tags(source),tags(target); sn,tn=nums(source),nums(target); sl,tl=protected(source),protected(target)
    return {'placeholders':{'source':sorted(sp.elements()),'target':sorted(tp.elements()),'matches':sp==tp},
      'markup':{'source':sorted(st.elements()),'target':sorted(tt.elements()),'matches':st==tt},
      'numbers':{'source':sn,'target':tn,'sourcePreserved':all(tn.count(x)>=n for x,n in collections.Counter(sn).items())},
      'protectedLiterals':{'source':sl,'target':tl,'missing':[x for x in sl if x not in target]}}
def capture_live():
    pr=json.loads(subprocess.check_output(['gh','api','repos/snapetech-org/slskdN/pulls/409'],text=True))
    branch=json.loads(subprocess.check_output(['gh','api','repos/snapetech-org/slskdN/git/ref/heads/'+BRANCH],text=True))
    mainref=json.loads(subprocess.check_output(['gh','api','repos/snapetech-org/slskdN/git/ref/heads/main'],text=True))
    remote=subprocess.check_output(['git','ls-remote',REMOTE,'refs/heads/main','refs/heads/'+BRANCH,'refs/pull/409/head'],text=True)
    refs={line.split()[1]:line.split()[0] for line in remote.splitlines() if line.strip()}
    result={'capturedAtUtc':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),'repository':SLUG,'pullRequest':409,
      'state':pr['state'],'draft':pr['draft'],'merged':pr['merged'],'baseRef':pr['base']['ref'],'baseSha':pr['base']['sha'],
      'baseTree':git('rev-parse',pr['base']['sha']+'^{tree}').decode().strip(),'headRef':pr['head']['ref'],'headSha':pr['head']['sha'],
      'headTree':git('rev-parse',pr['head']['sha']+'^{tree}').decode().strip(),'branchApiSha':branch['object']['sha'],
      'mainApiSha':mainref['object']['sha'],'mainTree':git('rev-parse',mainref['object']['sha']+'^{tree}').decode().strip(),
      'remoteBranchSha':refs.get('refs/heads/'+BRANCH),'pullRefSha':refs.get('refs/pull/409/head'),'remoteMainSha':refs.get('refs/heads/main'),
      'remoteRefs':refs,'prBodyIncluded':False}
    need((result['state'],result['draft'],result['merged'])==('open',True,False),'PR status')
    need((result['headRef'],result['headSha'],result['headTree'])==(BRANCH,HEAD,TREE),'PR head/tree')
    need((result['branchApiSha'],result['remoteBranchSha'],result['pullRefSha'])==(HEAD,HEAD,HEAD),'branch/pull refs')
    need((result['baseRef'],result['baseSha'],result['baseTree'])==('main',BASE,BASETREE),'PR base')
    need((result['mainApiSha'],result['mainTree'],result['remoteMainSha'])==(MAIN,MAINTREE,MAIN),'live main')
    return result

def main():
    allowed={'build_candidate_free.py','verify_candidate_free.py'}
    need({p.name for p in OUT.iterdir()}<=allowed,'candidate-free output is not empty')
    need(git('rev-parse','HEAD').decode().strip()==HEAD and git('rev-parse','HEAD^{tree}').decode().strip()==TREE,'repo pin')
    need(git('branch','--show-current').decode().strip()==BRANCH,'repo branch')
    need(not git('status','--porcelain=v1').decode().strip(),'repo worktree is dirty')
    need(not (REPO/'docs/pr-evidence/pr409-localization-2026-11-05/window-1053-1077').exists(),'W1053 packet already exists in branch')
    before=capture_live()
    prior_sums=verify_sums(PREV)
    w1003_input_sums=verify_sums(W1003_INPUT)
    w1003_input_manifest=readj(W1003_INPUT/'manifest.json')
    need((w1003_input_manifest.get('head'),w1003_input_manifest.get('tree'),w1003_input_manifest.get('window'))==('8c752c49281418fdd96341ed46f5c321627b625f','b930b0d82679e843849e54456f3250e422c4682c','W85'),'W1003 product readback input pin')
    prior_manifest=readj(PREV/'manifest.json')
    need((prior_manifest.get('head'),prior_manifest.get('tree'),prior_manifest.get('window'))==('624e27d8bb108a764df6daab5cfb1c517ebac96d','d139a16988e23046ccb09f519db2d3b7ae0b86d1','W86'),'prior W1028-W1052 lineage packet')
    need(prior_manifest.get('candidateFree') is True and prior_manifest.get('reviewDecisionsIncluded') is False and prior_manifest.get('proposedTargetsIncluded') is False,'prior packet is not candidate-free')
    # Verify only W1028 product-readback evidence; do not inspect the sibling review packet.
    window_sums={}
    for line in (PREV_WINDOW_DIR/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1)
        if n.startswith('root-application/'):
            rel=n.removeprefix('root-application/')
            path=PREV_ROOT_APP/rel
            need(rel not in window_sums and path.is_file() and sha(path.read_bytes())==h,'W1028 root-application checksum '+rel)
            window_sums[rel]=h
    actual_root_files={p.relative_to(PREV_ROOT_APP).as_posix() for p in PREV_ROOT_APP.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    need(actual_root_files==set(window_sums),'W1028 root-application checksum inventory')
    inventory=readjl(PREV/'source-inventory-pinned.jsonl')
    exclusions=readjl(PREV/'prior-selected-id-exclusions-hash-only.jsonl')
    prior_hold_rows=readjl(PREV/'prior-held-cell-reattestation-hash-only.jsonl')
    prior_window_holds=readjl(PREV/'window-holds-hash-only.jsonl')
    prior_applied=readjl(PREV/'prior-applied-targets-reattestation-hash-only.jsonl')
    prior_window_applied=readjl(PREV/'window-applied-targets-reattestation-hash-only.jsonl')
    prior_readbacks=readjl(PREV/'window-application-readback-hash-only.jsonl')
    resolutions=readjl(PREV/'prior-hold-resolution-history-hash-only.jsonl')
    prior_active=prior_hold_rows+prior_window_holds
    hold_ids=[(r['sourceIdSha256'],r['locale']) for r in prior_active]
    need(len(prior_active)==433 and len(set(hold_ids))==433,'prior active hold set count/uniqueness')
    need(all(not any(k in TEXT_KEYS for k in r) for r in prior_active+prior_applied+prior_window_applied+prior_readbacks+resolutions+exclusions),'prior hash-only text redaction')
    need(len(inventory)==6175 and len(exclusions)==2135 and len(prior_applied)==677 and len(prior_window_applied)==71 and len(prior_readbacks)==900 and len(resolutions)==25,'prior continuity counts')

    root_sums={}
    for line in (ROOT_APP/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1); root_sums[n.removeprefix('./')]=h
    app_summary_raw=(ROOT_APP/'application-summary.json').read_bytes()
    readback_raw=(ROOT_APP/'final-head-readback.jsonl').read_bytes()
    need(root_sums.get('application-summary.json')==sha(app_summary_raw),'W1003 application summary product checksum')
    need(root_sums.get('final-head-readback.jsonl')==sha(readback_raw),'W1003 final readback product checksum')
    app_summary=json.loads(app_summary_raw)
    product_commit=app_summary.get('productCommit'); product_tree=app_summary.get('productTree')
    need((app_summary.get('artifact'),app_summary.get('inputHead'),app_summary.get('inputTree'),app_summary.get('reviewedCells'),app_summary.get('changedCellCount'),app_summary.get('callerlessHashOnlyHolds'),app_summary.get('resultingActiveHolds'))==('slskdN PR #409 W1003-W1027 exact-hash application','8c752c49281418fdd96341ed46f5c321627b625f','b930b0d82679e843849e54456f3250e422c4682c',300,71,12,421),'W1003 product application metadata')
    need(git('rev-parse',product_commit+'^{tree}').decode().strip()==product_tree,'W1003 product commit/tree')
    need(subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',product_commit,HEAD]).returncode==0,'W1003 product commit is not an ancestor')
    w1003_readback=[json.loads(x) for x in readback_raw.decode('utf-8').splitlines() if x.strip()]
    need(len(w1003_readback)==300,'W1003 product readback count')

    # Read and pin the intervening W1028 product application by hashes only.
    prev_summary_raw=(PREV_ROOT_APP/'application-summary.json').read_bytes()
    prev_pin_raw=(PREV_ROOT_APP/'product-pin.json').read_bytes()
    prev_readback_raw=(PREV_ROOT_APP/'final-head-readback.jsonl').read_bytes()
    prev_summary=json.loads(prev_summary_raw); prev_pin=json.loads(prev_pin_raw)
    prev_product_commit=prev_summary.get('productCommit'); prev_product_tree=prev_summary.get('productTree')
    need((prev_summary.get('window'),prev_summary.get('inputHead'),prev_summary.get('inputTree'),prev_summary.get('reviewedCells'),prev_summary.get('selectedChanges'),prev_summary.get('hashOnlyHolds'),prev_summary.get('readbackCells'),prev_summary.get('changedCells'),prev_summary.get('activeHoldsAfter'))==('W1028-W1052','624e27d8bb108a764df6daab5cfb1c517ebac96d','d139a16988e23046ccb09f519db2d3b7ae0b86d1',300,44,12,300,44,433),'W1028 product application metadata')
    need((prev_pin.get('productCommit'),prev_pin.get('productTree'))==(prev_product_commit,prev_product_tree),'W1028 product pin metadata')
    need(git('rev-parse',prev_product_commit+'^{tree}').decode().strip()==prev_product_tree,'W1028 product commit/tree')
    need(subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',prev_product_commit,HEAD]).returncode==0,'W1028 product commit is not an ancestor')
    for path,pinned_sha in prev_pin.get('catalogSha256',{}).items():
        need(path.startswith('src/web/public/locales/') and sha((REPO/path).read_bytes())==pinned_sha,'W1028 product catalog pin '+path)
    need(len(prev_pin.get('catalogSha256',{}))==12,'W1028 product catalog pin count')
    w1028_readback=[json.loads(x) for x in prev_readback_raw.decode('utf-8').splitlines() if x.strip()]
    need(len(w1028_readback)==300,'W1028 product readback count')
    prev_cells={(r['continuationRank'],r['locale']):r for r in readjl(PREV/'source-current-cells.jsonl')}
    need(len(prev_cells)==300,'W1028 predecessor cell count')

    tree={}
    for item in git('ls-tree','-r','-z',HEAD).split(b'\0'):
        if not item: continue
        meta,path=item.split(b'\t',1); mode,kind,oid=meta.decode().split(); tree[path.decode()]={'mode':mode,'kind':kind,'gitBlob':oid}
    catalog_objs={}; catalog_rows=[]; ordered=None
    for locale in LOCALES:
        path='src/web/public/locales/'+locale+'.json'; raw=(REPO/path).read_bytes()
        need(blobsha(raw)==tree[path]['gitBlob'],'catalog blob '+locale)
        obj=parseobj(raw,locale); keys=list(obj)
        need(len(keys)==6175 and all(isinstance(v,str) and v for v in obj.values()),'catalog values/count '+locale)
        if ordered is None: ordered=keys
        else: need(keys==ordered,'catalog key order '+locale)
        catalog_objs[locale]=obj
        catalog_rows.append({'locale':locale,'path':path,'bytes':len(raw),'sha256':sha(raw),'gitBlob':tree[path]['gitBlob'],'entryCount':len(obj),'orderedKeySha256':sha(('\n'.join(keys)+'\n').encode())})
    prev_order=readj(PREV/'catalog-key-order-attestation.json')
    ordered_hash=sha(('\n'.join(ordered)+'\n').encode())
    need(prev_order.get('orderedKeySha256')==ordered_hash and prev_order.get('entryCount')==len(ordered),'source catalog key order changed')
    source_by_id={'src_'+tsha(k)[:16]:k for k in ordered}
    need(len(source_by_id)==6175,'source ID collision')
    source_id_by_hash={tsha(sid):sid for sid in source_by_id}
    inv_by={r['sourceId']:r for r in inventory}
    need(set(inv_by)==set(source_by_id),'inventory source ID set')
    for sid,source in source_by_id.items(): need(inv_by[sid]['sourceSha256']==tsha(source),'inventory source sha '+sid)
    rankrows={r['continuationRank']:r for r in inventory if r.get('continuationRank') is not None}
    need(len(rankrows)==4967,'ranked inventory count')

    runtime=[]
    for path,entry in sorted(tree.items()):
        if not production_path(path): continue
        data=(REPO/path).read_bytes(); need(blobsha(data)==entry['gitBlob'],'runtime blob '+path)
        runtime.append({'path':path,'bytes':len(data),'sha256':sha(data),'gitBlob':entry['gitBlob'],'lineCount':len(data.decode('utf-8').splitlines())})
    old_runtime=readjl(PREV/'runtime-file-pins.jsonl')
    need(len(runtime)==279 and len(old_runtime)==279,'runtime file count')
    need([(r['path'],r['bytes'],r['sha256'],r['gitBlob'],r['lineCount']) for r in runtime]==[(r['path'],r['bytes'],r['sha256'],r['gitBlob'],r['lineCount']) for r in old_runtime],'production runtime tree changed since prior exact caller scan')

    selected=[]
    for rank in range(FIRST,LAST+1):
        r=rankrows.get(rank); need(r is not None,'missing continuation rank '+str(rank))
        sid=r['sourceId']; source=source_by_id[sid]
        need((r['remainingQueueRank'],r['eligibleForFreshWindow'],r['priorSelectedOrRewriteExcluded'],r['baselineExcluded'])==(rank-100,True,False,False),'rank eligibility '+str(rank))
        selected.append({'continuationRank':rank,'remainingQueueRank':rank-100,'sourceId':sid,'sourceIdSha256':tsha(sid),'sourceSha256':tsha(source),'source':source})
    need((selected[0]['sourceId'],selected[0]['sourceSha256'])==('src_39e6bb62127db08a','39e6bb62127db08ad93ab2bde08c8f7a26f831cfed2bded4bef232c79ec60034'),'provided first source ID/SHA')
    prior_boundary_input=readj(PREV/'selection-and-boundary.json').get('nextUnselected',{})
    need((prior_boundary_input.get('continuationRank'),prior_boundary_input.get('remainingQueueRank'),prior_boundary_input.get('sourceId'),prior_boundary_input.get('sourceSha256'))==(1053,953,selected[0]['sourceId'],selected[0]['sourceSha256']),'prior queue sequence continuation')
    exclusion_by={r['sourceId']:r for r in exclusions}
    need(len(exclusion_by)==2135,'prior exclusion scope')
    for s in selected:
        need(s['sourceId'] not in exclusion_by,'selected ID already excluded '+s['sourceId'])
        exclusion_by[s['sourceId']]={'sourceId':s['sourceId'],'sourceIdSha256':tsha(s['sourceId']),'sourceSha256':s['sourceSha256'],
          'continuationRank':s['continuationRank'],'remainingQueueRank':s['remainingQueueRank'],'selectionOrigin':'W1053-W1077 current-head review window',
          'exclusionOrigins':['W1053-W1077 current-head candidate-free input'],'exclusionConfirmed':True,'sourceTextIncluded':False,'targetTextIncluded':False}
    need(len(exclusion_by)==2160,'updated exclusion count')
    updated_inventory=[]
    for sid,old in inv_by.items():
        excluded=sid in exclusion_by
        updated_inventory.append({'sourceId':sid,'sourceSha256':old['sourceSha256'],'continuationRank':old.get('continuationRank'),
          'remainingQueueRank':old.get('remainingQueueRank'),'baselineExcluded':old.get('baselineExcluded',False),
          'priorSelectedOrRewriteExcluded':excluded,'eligibleForFreshWindow':old.get('continuationRank') is not None and not old.get('baselineExcluded',False) and not excluded,
          'localeCoverage':12,'sourceTextIncluded':False,'attestedAtHead':HEAD})
    updated_inventory.sort(key=lambda r:r['sourceId'])

    refs_by={}
    for s in selected:
        literal=re.compile(r'(?<![A-Za-z0-9_$])([\"\'])'+re.escape(s['source'])+r'\1')
        refs=[]
        for pin in runtime:
            lines=(REPO/pin['path']).read_text(encoding='utf-8').splitlines()
            for idx,line in enumerate(lines):
                hits=len(literal.findall(line))
                if hits:
                    context=[{'line':n+1,'text':lines[n]} for n in range(max(0,idx-4),min(len(lines),idx+3))]
                    refs.append({'path':pin['path'],'line':idx+1,'lineText':line,'literalOccurrenceCount':hits,'lineSha256':tsha(line),'context':context,
                      'contextSha256':sha(canon(context)),'fileBytes':pin['bytes'],'fileSha256':pin['sha256'],'gitBlob':pin['gitBlob']})
        refs_by[s['sourceId']]=refs
    caller_rows=[]; cell_rows=[]; token_counts=collections.Counter(); caller_ref_total=0; caller_occurrence_total=0
    for s in selected:
        sid=s['sourceId']; refs=refs_by[sid]; caller_ref_total+=len(refs); caller_occurrence_total+=sum(r['literalOccurrenceCount'] for r in refs); csha=sha(canon(refs)); has_callers=bool(refs)
        crow={'continuationRank':s['continuationRank'],'remainingQueueRank':s['remainingQueueRank'],'sourceId':sid,'sourceIdSha256':tsha(sid),
          'sourceSha256':s['sourceSha256'],'productionCallerCount':len(refs),'callerOccurrenceCount':sum(r['literalOccurrenceCount'] for r in refs),
          'callerContextSha256':csha,'callerReferenceTextIncluded':has_callers,'sourceTextIncluded':has_callers,'exactHead':HEAD,'exactTree':TREE,'callers':refs}
        if has_callers: crow['source']=s['source']
        caller_rows.append(crow)
        for locale in LOCALES:
            target=catalog_objs[locale][s['source']]; th=tsha(target); evidence=token_data(s['source'],target) if has_callers else None
            if evidence:
                for key,ok in [('placeholder',evidence['placeholders']['matches']),('markup',evidence['markup']['matches']),('numeric',evidence['numbers']['sourcePreserved']),('protectedLiteral',not evidence['protectedLiterals']['missing'])]:
                    if not ok: token_counts[key]+=1
            row={'continuationRank':s['continuationRank'],'remainingQueueRank':s['remainingQueueRank'],'sourceId':sid,'sourceIdSha256':tsha(sid),
              'sourceSha256':s['sourceSha256'],'locale':locale,'currentTargetSha256':th,'currentTargetTextIncluded':has_callers,
              'sourceTextIncluded':has_callers,'catalogPath':'src/web/public/locales/'+locale+'.json',
              'catalogFileSha256':next(c['sha256'] for c in catalog_rows if c['locale']==locale),
              'catalogGitBlob':next(c['gitBlob'] for c in catalog_rows if c['locale']==locale),'callerContextSha256':csha,'callerCount':len(refs),
              'containsCandidate':False,'decision':None,'candidateFreeHold':not has_callers}
            if has_callers: row.update({'source':s['source'],'currentTarget':target,'tokenEvidence':evidence,
              'tokenEvidenceSha256':sha(canon(evidence)),'tokenChecksPass':evidence['placeholders']['matches'] and evidence['markup']['matches'] and evidence['numbers']['sourcePreserved'] and not evidence['protectedLiterals']['missing']})
            else: row.update({'sourceTextOmittedForNoCallerHold':True,'currentTargetOmittedForNoCallerHold':True,'tokenEvidenceIncluded':False})
            cell_rows.append(row)
    need(len(cell_rows)==300,'cell count')
    selected_by_rank={r['continuationRank']:r for r in selected}
    caller_by_id={r['sourceId']:r for r in caller_rows}
    new_holds=[]
    for cell in cell_rows:
        if not cell['candidateFreeHold']: continue
        new_holds.append({'attestedAtHead':HEAD,'callerContextSha256':cell['callerContextSha256'],'callerCount':0,
          'continuationRank':cell['continuationRank'],'currentTargetSha256':cell['currentTargetSha256'],
          'holdReasonClass':'no-pinned-production-localization-caller','locale':cell['locale'],
          'remainingQueueRank':cell['remainingQueueRank'],'sourceIdSha256':cell['sourceIdSha256'],
          'sourceSha256':cell['sourceSha256'],'sourceTextIncluded':False,'targetTextIncluded':False,'proposalTextIncluded':False,'window':'W1053-W1077'})

    # Reattest all 433 active holds without exposing text; identical runtime file blobs preserve their caller evidence.
    hold_reattests=[]
    for hold in prior_active:
        sid=hold.get('sourceId') or source_id_by_hash.get(hold['sourceIdSha256']); loc=hold['locale']; source=source_by_id.get(sid)
        need(source is not None and tsha(source)==hold['sourceSha256'] and tsha(sid)==hold['sourceIdSha256'],'active hold source identity')
        prior_target=hold.get('currentTargetSha256') or hold.get('priorTargetSha256')
        prior_context=hold.get('currentCallerContextSha256') or hold.get('callerContextSha256')
        need(prior_target and prior_context,'active hold prior target/context hash missing')
        actual=tsha(catalog_objs[loc][source])
        need(actual==prior_target,'active hold target changed '+sid+' '+loc)
        caller_count=hold.get('callerCount')
        hold_reattests.append({'holdId':sid+'::'+loc,'sourceId':sid,'sourceIdSha256':hold['sourceIdSha256'],'sourceSha256':hold['sourceSha256'],
          'locale':loc,'continuationRank':hold.get('continuationRank',inv_by[sid].get('continuationRank')),
          'remainingQueueRank':hold.get('remainingQueueRank',inv_by[sid].get('remainingQueueRank')),
          'priorWindow':hold.get('priorWindow',hold.get('window')),'holdReasonClass':hold.get('holdReasonClass'),
          'holdReasonSha256':hold.get('holdReasonSha256'),'callerCount':caller_count,
          'priorCallerContextSha256':hold.get('currentCallerContextSha256',hold.get('callerContextSha256')),
          'currentCallerContextSha256':prior_context,'callerEvidenceUnchanged':True,
          'priorTargetSha256':prior_target,'currentTargetSha256':actual,
          'currentCatalogPath':'src/web/public/locales/'+loc+'.json','currentCatalogFileSha256':next(c['sha256'] for c in catalog_rows if c['locale']==loc),
          'currentCatalogGitBlob':next(c['gitBlob'] for c in catalog_rows if c['locale']==loc),
          'attestedAtHead':HEAD,'sourceTextIncluded':False,'targetTextIncluded':False})
    need(len(hold_reattests)==433 and len({(r['sourceIdSha256'],r['locale']) for r in hold_reattests})==433,'active hold reattestation count')
    need(all(not any(k in TEXT_KEYS for k in r) for r in hold_reattests+new_holds),'active hold text redaction')

    # Reattest the older applied-target history and the most recent applied window separately.
    def reattest_applied(rows,label):
        result=[]
        for row in rows:
            sid=row.get('sourceId') or source_id_by_hash.get(row['sourceIdSha256']); loc=row['locale']; source=source_by_id.get(sid)
            need(source is not None and tsha(source)==row['sourceSha256'] and tsha(sid)==row['sourceIdSha256'],label+' source identity')
            actual=tsha(catalog_objs[loc][source]); expected=row.get('appliedTargetSha256') or row.get('currentTargetSha256')
            need(actual==expected,label+' target changed '+sid+' '+loc)
            result.append({**row,'attestedAtHead':HEAD,'currentTargetSha256':actual,
              'currentCatalogFileSha256':next(c['sha256'] for c in catalog_rows if c['locale']==loc),
              'currentCatalogGitBlob':next(c['gitBlob'] for c in catalog_rows if c['locale']==loc),
              'targetRemainsApplied':True,'sourceTextIncluded':False,'targetTextIncluded':False})
        keys={(r['sourceIdSha256'],r['locale']) for r in result}
        need(len(keys)==len(result),label+' duplicate identities')
        return result
    applied_reattests=reattest_applied(prior_applied,'prior applied')
    previous_window_applied_reattests=reattest_applied(prior_window_applied,'previous window applied')
    need(len(applied_reattests)==677 and len(previous_window_applied_reattests)==71,'prior/latest applied target counts')

    # Read only the W1003 product readback hashes and compare them with the live catalog values.
    readback_by={}; w1003_readbacks=[]; w1003_applied=[]
    old_cells={(r['continuationRank'],r['locale']):r for r in readjl(W1003_INPUT/'source-current-cells.jsonl')}
    rank_by_id={r['sourceId']:r for r in inventory}
    for r in w1003_readback:
        rank=r['continuationRank']; loc=r['locale']
        sid=r.get('sourceId') or rankrows[rank]['sourceId']; source=source_by_id.get(sid)
        need(source is not None and tsha(source)==r['sourceSha256'] and sid=='src_'+tsha(source)[:16],'W1003 readback source binding')
        need(rank_by_id[sid]['continuationRank']==rank and rank-100==r['remainingQueueRank'],'W1003 readback rank binding')
        prior_cell=old_cells.get((rank,loc)); need(prior_cell is not None and prior_cell['currentTargetSha256']==r['beforeSha256'],'W1003 readback pre-application hash binding')
        actual=tsha(catalog_objs[loc][source])
        if 'after' in r: need(tsha(r['after'])==r['afterSha256'],'W1003 readback after-text hash')
        if 'before' in r: need(tsha(r['before'])==r['beforeSha256'],'W1003 readback before-text hash')
        need(actual==r['afterSha256'],'W1003 product readback no longer present at current head '+sid+' '+loc)
        key=(rank,loc); need(key not in readback_by,'duplicate W1003 product readback identity'); readback_by[key]=r
        base={'continuationRank':rank,'remainingQueueRank':r['remainingQueueRank'],'sourceIdSha256':tsha(sid),'sourceSha256':r['sourceSha256'],
          'locale':loc,'callerContextSha256':r['callerContextSha256'],'productCommit':product_commit,'productTree':product_tree,
          'productReadbackFileSha256':sha(readback_raw),'productExpectedAfterSha256':r['afterSha256'],
          'productObservedAfterSha256':actual,'currentTargetSha256':actual,'readbackMatchesCurrent':True,
          'currentCatalogPath':'src/web/public/locales/'+loc+'.json','currentCatalogFileSha256':next(c['sha256'] for c in catalog_rows if c['locale']==loc),
          'currentCatalogGitBlob':next(c['gitBlob'] for c in catalog_rows if c['locale']==loc),
          'attestedAtHead':HEAD,'sourceTextIncluded':False,'targetTextIncluded':False}
        w1003_readbacks.append(base)
        if r['beforeSha256']!=r['afterSha256']:
            w1003_applied.append({**base,'priorCurrentTargetSha256':r['beforeSha256'],'appliedTargetSha256':r['afterSha256'],
              'rootDispositionClass':'applied','targetRemainsApplied':True})
    need(len(readback_by)==300 and len(w1003_applied)==71,'W1003 product readback changed-cell counts')
    need({(r['sourceIdSha256'],r['locale'],r['appliedTargetSha256']) for r in previous_window_applied_reattests}=={(r['sourceIdSha256'],r['locale'],r['appliedTargetSha256']) for r in w1003_applied},'W1003 applied target/readback identity continuity')

    # W1028 direct post-application readback: bind before-hashes to the
    # candidate-free cells and after-hashes to this exact current catalog.
    w1028_readbacks=[]; w1028_applied=[]; w1028_seen=set()
    for r in w1028_readback:
        rank=r['continuationRank']; loc=r['locale']; sid=r.get('sourceId') or rankrows[r['continuationRank']]['sourceId']; source=source_by_id.get(sid)
        need(source is not None and rankrows[rank]['sourceId']==sid and tsha(source)==rankrows[rank]['sourceSha256'],'W1028 readback source/rank binding')
        prev_cell=prev_cells.get((rank,loc)); need(prev_cell is not None,'W1028 readback candidate-free cell binding')
        need(r['beforeSha256']==prev_cell['currentTargetSha256'],'W1028 readback pre-application hash binding')
        need(r['callerless'] is prev_cell['candidateFreeHold'],'W1028 callerless/hash-only hold binding')
        need(r['callerless']==(prev_cell['callerCount']==0),'W1028 caller evidence binding')
        need(r['callerless'] or r['textIncluded'] is True,'W1028 caller-backed readback metadata')
        if r['callerless']: need(r['beforeSha256']==r['afterSha256'] and r['textIncluded'] is False,'W1028 hash-only hold unchanged')
        actual=tsha(catalog_objs[loc][source])
        need(actual==r['afterSha256'],'W1028 product readback no longer present at current head '+sid+' '+loc)
        key=(rank,loc); need(key not in w1028_seen,'duplicate W1028 product readback identity'); w1028_seen.add(key)
        context=prev_cell['callerContextSha256']
        base={'continuationRank':rank,'remainingQueueRank':rank-100,'sourceIdSha256':tsha(sid),'sourceSha256':tsha(source),
          'locale':loc,'callerContextSha256':context,'productCommit':prev_product_commit,'productTree':prev_product_tree,
          'productReadbackFileSha256':sha(prev_readback_raw),'productExpectedAfterSha256':r['afterSha256'],
          'productObservedAfterSha256':actual,'currentTargetSha256':actual,'readbackMatchesCurrent':True,
          'currentCatalogPath':'src/web/public/locales/'+loc+'.json','currentCatalogFileSha256':next(c['sha256'] for c in catalog_rows if c['locale']==loc),
          'currentCatalogGitBlob':next(c['gitBlob'] for c in catalog_rows if c['locale']==loc),
          'attestedAtHead':HEAD,'sourceTextIncluded':False,'targetTextIncluded':False}
        w1028_readbacks.append(base)
        if r['beforeSha256']!=r['afterSha256']:
            w1028_applied.append({**base,'priorCurrentTargetSha256':r['beforeSha256'],'appliedTargetSha256':r['afterSha256'],
              'rootDispositionClass':'applied','targetRemainsApplied':True})
    need(len(w1028_seen)==300 and len(w1028_applied)==44,'W1028 product readback changed-cell counts')
    prior_applied_all=applied_reattests+previous_window_applied_reattests
    need(len(prior_applied_all)==748 and len({(r['sourceIdSha256'],r['locale']) for r in prior_applied_all})==748,'folded historical applied target continuity')
    window_applied_reattests=w1028_applied
    # Refresh the previous 600 W978 product-readback rows at the same new head.
    refreshed_history=[]
    for row in prior_readbacks:
        sid=row['sourceIdSha256'] if 'sourceIdSha256' in row else None
        # Resolve the source ID by its stable ID hash; historical rows intentionally carry no source ID text.
        matches=[item for item in inventory if tsha(item['sourceId'])==row['sourceIdSha256']]
        need(len(matches)==1,'prior readback source ID resolution')
        invrow=matches[0]; source=source_by_id[invrow['sourceId']]; loc=row['locale']
        need(tsha(source)==row['sourceSha256'],'prior readback source hash')
        actual=tsha(catalog_objs[loc][source])
        expected=row.get('rootExpectedAfterSha256') or row.get('productExpectedAfterSha256')
        observed=row.get('rootObservedAfterSha256') or row.get('productObservedAfterSha256')
        need(actual==expected==observed,'prior readback target changed '+invrow['sourceId']+' '+loc)
        refreshed_history.append({**row,'attestedAtHead':HEAD,'currentCatalogTargetSha256':actual,'readbackMatchesCurrent':True})
    w1028_history=[]
    for r in w1028_readbacks:
        match=next(x for x in w1028_readback if x['continuationRank']==r['continuationRank'] and x['locale']==r['locale'])
        original=prev_cells[(r['continuationRank'],r['locale'])]
        disposition='hold-hash-only' if match['callerless'] else ('applied' if match['beforeSha256']!=match['afterSha256'] else 'accept-current')
        w1028_history.append({'window':'W1028-W1052','continuationRank':r['continuationRank'],'remainingQueueRank':r['remainingQueueRank'],
          'sourceIdSha256':r['sourceIdSha256'],'sourceSha256':r['sourceSha256'],'locale':r['locale'],
          'rootDispositionClass':disposition,'rootExpectedAfterSha256':r['productExpectedAfterSha256'],
          'rootObservedAfterSha256':r['productObservedAfterSha256'],'currentCatalogTargetSha256':r['currentTargetSha256'],
          'readbackMatchesCurrent':True,'callerContextSha256':original['callerContextSha256'],'attestedAtHead':HEAD,
          'sourceTextIncluded':False,'targetTextIncluded':False})
    all_readbacks=refreshed_history+w1028_history
    need(len(all_readbacks)==1200,'application readback history count')

    # Resolution history is historical metadata; preserve it hash-only without reinterpreting it.
    refreshed_resolutions=resolutions

    prior_boundary={'continuationRank':1052,'remainingQueueRank':952,'sourceId':rankrows[1052]['sourceId'],'sourceSha256':rankrows[1052]['sourceSha256']}
    nextrow=rankrows[1078]
    boundary={'window':'W87','head':HEAD,'tree':TREE,'previousWindow':'W86 / W1028-W1052','previousWindowFinalRank':prior_boundary,
      'selectedWindow':[{'continuationRank':r['continuationRank'],'remainingQueueRank':r['remainingQueueRank'],'sourceId':r['sourceId'],'sourceSha256':r['sourceSha256']} for r in selected],
      'nextUnselected':{'continuationRank':1078,'remainingQueueRank':978,'sourceId':nextrow['sourceId'],'sourceSha256':nextrow['sourceSha256']},
      'selectionRule':'next 25 eligible stable source IDs from pinned W86 inventory; continuationRank = remainingQueueRank + 100'}
    ordered_manifest={'entryCount':len(ordered),'orderedKeySha256':ordered_hash,
      'sourceIdOrderSha256':sha(b''.join(bytes.fromhex(tsha(k)) for k in ordered)),
      'sourceRecordOrderSha256':sha(b''.join(bytes.fromhex(tsha('src_'+tsha(k)[:16]))+bytes.fromhex(tsha(k)) for k in ordered)),
      'catalogKeysAreEnglishSourceStrings':True,'exactHead':HEAD,'exactTree':TREE}

    writej('live-before.json',before)
    writej('catalog-key-order-attestation.json',ordered_manifest)
    writejl('catalog-structure.jsonl',catalog_rows)
    writejl('runtime-file-pins.jsonl',runtime)
    writejl('source-inventory-pinned.jsonl',updated_inventory)
    writejl('source-inventory-selection.jsonl',[{k:v for k,v in r.items() if k!='source'} for r in selected])
    selected_rows=[]
    for r in selected:
        item={k:v for k,v in r.items() if k!='source'}
        item['sourceTextIncluded']=bool(refs_by[r['sourceId']])
        if refs_by[r['sourceId']]: item['source']=r['source']
        else: item['sourceTextOmittedForNoCallerHold']=True
        selected_rows.append(item)
    writejl('selected-sources.jsonl',selected_rows)
    writejl('source-current-cells.jsonl',cell_rows)
    writejl('caller-contexts.jsonl',caller_rows)
    writejl('prior-selected-id-exclusions-hash-only.jsonl',sorted(exclusion_by.values(),key=lambda r:r['sourceId']))
    writejl('prior-held-cell-reattestation-hash-only.jsonl',hold_reattests)
    writejl('prior-hold-resolution-history-hash-only.jsonl',refreshed_resolutions)
    writejl('prior-applied-targets-reattestation-hash-only.jsonl',prior_applied_all)
    writejl('window-applied-targets-reattestation-hash-only.jsonl',window_applied_reattests)
    writejl('window-application-readback-hash-only.jsonl',all_readbacks)
    writejl('window-product-readback-reattestation-hash-only.jsonl',w1028_readbacks)
    writejl('window-holds-hash-only.jsonl',new_holds)
    writej('product-readback-provenance.json',{'sourceWindow':'W1028-W1052','productCommit':prev_product_commit,'productTree':prev_product_tree,
      'applicationSummarySha256':sha(prev_summary_raw),'productPinSha256':sha(prev_pin_raw),'finalHeadReadbackSha256':sha(prev_readback_raw),'readbackRows':len(w1028_readbacks),
      'changedProductRows':len(w1028_applied),'allProductRowsMatchCurrentHead':True,'currentHead':HEAD,
      'sourceTextIncluded':False,'targetTextIncluded':False,'reviewLedgerRead':False})
    writej('continuity-provenance.json',{'priorPacketPath':'../window-1028-1052/candidate-free',
      'priorPacketManifestSha256':sha((PREV/'manifest.json').read_bytes()),'priorPacketChecksumsSha256':sha((PREV/'SHA256SUMS.txt').read_bytes()),
      'W1003ProductInputManifestSha256':sha((W1003_INPUT/'manifest.json').read_bytes()),'W1003ProductInputChecksumsSha256':sha((W1003_INPUT/'SHA256SUMS.txt').read_bytes()),
      'priorLiveHead':HEAD,'priorLiveTree':TREE,
      'currentAttestedHead':HEAD,'priorSourceExclusions':2135,'newlySelectedIdsExcluded':25,
      'priorActiveHolds':len(hold_reattests),'priorAppliedTargets':len(prior_applied_all),'priorWindowProductReadbackRows':len(w1028_readbacks),
      'previousW1003ProductReadbackRows':len(w1003_readbacks),'W1028ProductReadbackSha256':sha(prev_readback_raw),
      'W1003ProductCommit':product_commit,'W1003ProductTree':product_tree,'W1003ApplicationSummarySha256':sha(app_summary_raw),
      'W1003ProductReadbackSha256':sha(readback_raw),'W1003ProductReadbackRows':len(w1003_readbacks),
      'W1003ChangedProductRows':len(w1003_applied),'W1003AllProductRowsMatchCurrentHead':True,
      'productionRuntimeFilesUnchangedSincePriorScan':True,'sourceTextIncluded':False,'targetTextIncluded':False})
    writej('baseline-token-mismatch-summary.json',{'cellCount':300,'callerBackedCells':sum(bool(refs_by[s['sourceId']]) for s in selected)*12,
      'noCallerHashOnlyCells':sum(not refs_by[s['sourceId']] for s in selected)*12,'mismatchCounts':dict(token_counts),
      'proposedTargetsIncluded':False,'note':'Token checks are candidate-free evidence on exact-head current values; no-caller holds expose no source or target text.'})
    writej('selection-and-boundary.json',boundary)
    after=capture_live()
    need(before['remoteRefs']==after['remoteRefs'] and (before['headSha'],before['baseSha'],before['mainApiSha'])==(after['headSha'],after['baseSha'],after['mainApiSha']),'live refs moved during build')
    writej('live-after.json',after)
    summary={'result':'PASS','artifact':'slskdN PR #409 W1053-W1077 candidate-free exact-head input','window':'W87',
      'head':HEAD,'tree':TREE,'branch':BRANCH,'baseRef':'main','baseSha':BASE,'baseTree':BASETREE,'mainSha':MAIN,'mainTree':MAINTREE,
      'continuationRankRange':[FIRST,LAST],'remainingQueueRankRange':[QFIRST,QLAST],'sourceCount':25,'localeCount':12,'cellCount':300,
      'catalogCount':12,'catalogEntryCountPerLocale':6175,'sourceInventoryRows':6175,'productionRuntimeFileCount':279,
      'sourceCallerReferenceCount':caller_ref_total,'sourceCallerOccurrenceCount':caller_occurrence_total,
      'sourcesWithCallers':sum(bool(refs_by[s['sourceId']]) for s in selected),'sourcesWithoutCallers':sum(not refs_by[s['sourceId']] for s in selected),
      'priorSelectedIdsAndNewWindowExclusions':len(exclusion_by),'priorActiveHoldsReattested':len(hold_reattests),
      'newWindowHashOnlyHoldCells':len(new_holds),'resultingActiveHashOnlyHoldCells':len(hold_reattests)+len(new_holds),
      'priorAppliedTargetsReattested':len(prior_applied_all),'windowAppliedTargetsReattested':len(window_applied_reattests),
      'priorWindowProductReadbackRows':len(w1028_readbacks),'previousProductReadbackRows':len(w1003_readbacks),'priorApplicationReadbackHistoryRows':len(all_readbacks),
      'priorProductReadbackAllMatchCurrentHead':True,'baselineTokenMismatchCounts':dict(token_counts),'proposedTargetsIncluded':False,
      'reviewDecisionsIncluded':False,'blindReviewUsed':False,'crossReviewUsed':False,'rootAdjudicationPerformed':False,
      'catalogsEdited':False,'repoEdited':False,'testsBuildsSecurityScansCiRun':False,'workflowChanges':0}
    writej('summary.json',summary)
    (OUT/'README.md').write_text('# slskdN PR #409 W1053–W1077 candidate-free input\n\n'
      'Pinned to PR #409 head '+HEAD+' / tree '+TREE+', base '+BASE+', live main '+MAIN+'. This packet selects continuation ranks 1053–1077 (remaining-queue ranks 953–977), 25 stable source IDs across all 12 locale catalogs (300 cells).\n\n'
      'Inputs include exact-head current catalog values, exact quoted production caller contexts, ordered catalog and runtime pins, token evidence, and hash-only continuity for all active holds, applied targets, and product readbacks. The W1028 product readback is reattested against the current head; all 300 rows match, including 44 changed targets. No proposed translations or review decisions are included. Cells without pinned production callers expose no source or target text.\n',encoding='utf-8')
    files=sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p.name not in {'manifest.json','SHA256SUMS.txt'})
    manifest={'schemaVersion':2,'repository':SLUG,'pullRequest':409,'branch':BRANCH,'window':'W87','candidateFree':True,
      'head':HEAD,'tree':TREE,'baseSha':BASE,'mainSha':MAIN,'continuationRankRange':[FIRST,LAST],
      'remainingQueueRankRange':[QFIRST,QLAST],'sourceCount':25,'localeCount':12,'cellCount':300,'locales':LOCALES,
      'catalogEntryCountPerLocale':6175,'catalogCount':12,'productionRuntimeFileCount':279,
      'sourceCallerReferenceCount':caller_ref_total,'sourceCallerOccurrenceCount':caller_occurrence_total,
      'sourcesWithCallers':summary['sourcesWithCallers'],'sourcesWithoutCallers':summary['sourcesWithoutCallers'],
      'priorSelectedIdsAndNewWindowExclusions':len(exclusion_by),'priorActiveHoldsReattested':len(hold_reattests),
      'newWindowHashOnlyHoldCells':len(new_holds),'resultingActiveHashOnlyHoldCells':len(hold_reattests)+len(new_holds),
      'priorAppliedTargetsReattested':len(prior_applied_all),'windowAppliedTargetsReattested':len(window_applied_reattests),
      'priorWindowProductReadbackRows':len(w1028_readbacks),'previousProductReadbackRows':len(w1003_readbacks),'priorApplicationReadbackHistoryRows':len(all_readbacks),
      'priorProductReadbackAllMatchCurrentHead':True,'baselineTokenMismatchCounts':dict(token_counts),
      'proposedTargetsIncluded':False,'reviewDecisionsIncluded':False,'blindReviewUsed':False,'crossReviewUsed':False,
      'rootAdjudicationPerformed':False,'activeHoldTextIncluded':False,'productReadbackTextIncluded':False,
      'files':[{'path':n,'sha256':sha((OUT/n).read_bytes()),'bytes':(OUT/n).stat().st_size} for n in files]}
    writej('manifest.json',manifest)
    sums=sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
    (OUT/'SHA256SUMS.txt').write_text(''.join(sha((OUT/n).read_bytes())+'  '+n+'\n' for n in sums),encoding='utf-8')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'sources':25,'cells':300,'callerReferences':caller_ref_total,
      'callerOccurrences':caller_occurrence_total,'sourcesWithoutCallers':summary['sourcesWithoutCallers'],
      'priorActiveHoldsReattested':len(hold_reattests),'newHolds':len(new_holds),'priorAppliedTargets':len(prior_applied_all),
      'W1028ProductReadbacks':len(w1028_readbacks),'W1028ChangedTargets':len(w1028_applied),'readbackHistoryRows':len(all_readbacks),'exclusions':len(exclusion_by),'checksummedFiles':len(sums)},indent=2))
if __name__=='__main__': main()
