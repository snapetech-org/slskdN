#!/usr/bin/env python3
from __future__ import annotations
import collections, datetime as dt, hashlib, json, re, subprocess, sys, unicodedata
from pathlib import Path

OUT=Path(__file__).resolve().parent
REPO=Path(sys.argv[1]).resolve()
PREV=REPO/'docs/pr-evidence/pr409-localization-2026-11-05/window-978-1002/candidate-free/input'
HEAD='8c752c49281418fdd96341ed46f5c321627b625f'
TREE='b930b0d82679e843849e54456f3250e422c4682c'
BASE='f25d263a2a7cdb2c8f76c40c346cb10f749a9356'
BASETREE='b2ce36e07aee6ade05e6d8795d04b9a7455a081f'
MAIN='bc6251ff4ea5a7e59f2d86e2400c90520601f46e'
MAINTREE='4232b318aeaab4c327443638e5467ca089bbed53'
BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
SLUG='snapetech-org/slskdN'
REMOTE='https://github.com/snapetech-org/slskdN.git'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
FIRST,LAST=1003,1027
QFIRST,QLAST=903,927
TEXT_KEYS={'source','sourceText','target','currentTarget','proposedTarget','proposedTargetText','candidateTarget','reviewTarget','rationale','reason'}

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
      'remoteRefs':refs,'baseIsAncestorOfMain':None,'prBodyIncluded':False}
    result['baseIsAncestorOfMain']=subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',result['baseSha'],result['mainApiSha']]).returncode==0
    need((result['state'],result['draft'],result['merged'])==('open',True,False),'PR status')
    need((result['headRef'],result['headSha'],result['headTree'])==(BRANCH,HEAD,TREE),'PR head/tree')
    need((result['branchApiSha'],result['remoteBranchSha'],result['pullRefSha'])==(HEAD,HEAD,HEAD),'branch/pull refs')
    need((result['baseRef'],result['baseSha'],result['baseTree'])==('main',BASE,BASETREE),'PR base')
    need((result['mainApiSha'],result['mainTree'],result['remoteMainSha'])==(MAIN,MAINTREE,MAIN),'live main')
    return result

def main():
    need({p.name for p in OUT.iterdir()}<={'build_candidate_free.py','verify_candidate_free.py'},'candidate-free output is not empty')
    need(git('rev-parse','HEAD').decode().strip()==HEAD and git('rev-parse','HEAD^{tree}').decode().strip()==TREE,'repo pin')
    need(not git('status','--porcelain=v1').decode().strip(),'repo worktree is dirty')
    need(not (REPO/'docs/pr-evidence/pr409-localization-2026-11-05/window-1003-1027').exists(),'W1003 packet already exists in branch')
    before=capture_live()
    prior_sums=verify_sums(PREV)
    prior_manifest=readj(PREV/'manifest.json')
    need((prior_manifest.get('head'),prior_manifest.get('tree'),prior_manifest.get('window'))==('1c2fe3be2c720693cbcb12d377bf1177804f4e77','808501cbc3b6ed873a47d7188189d486f0673f5e','W84'),'prior W978 lineage packet')
    need(prior_manifest.get('candidateFree') is True and prior_manifest.get('reviewDecisionsIncluded') is False,'prior packet candidate-free')
    inventory=readjl(PREV/'source-inventory-pinned.jsonl')
    exclusions=readjl(PREV/'prior-selected-id-exclusions-hash-only.jsonl')
    prior_holds=readjl(PREV/'prior-held-cell-reattestation-hash-only.jsonl')
    current_holds=readjl(PREV/'window-holds-hash-only.jsonl')
    prior_applied=readjl(PREV/'prior-applied-targets-reattestation-hash-only.jsonl')
    window_applied=readjl(PREV/'window-applied-targets-reattestation-hash-only.jsonl')
    window_readback=readjl(PREV/'window-application-readback-hash-only.jsonl')
    resolutions=readjl(PREV/'prior-hold-resolution-history-hash-only.jsonl')
    # Root-reverify W978 before carrying its applied-target and readback hashes into this window.
    W978=REPO/'docs/pr-evidence/pr409-localization-2026-11-05/window-978-1002/root-application'
    w978_plan=readjl(W978/'exact-hash-apply-plan.jsonl')
    w978_readback=readjl(W978/'final-head-readback.jsonl')
    w978_summary=readj(W978/'application-summary.json')
    need(w978_summary.get('postCommitHead')=='e18feff151531142bd4d76b394711aaca57861c6' and w978_summary.get('exactHashEditCount')==89,'W978 application summary')
    need(len(w978_plan)==89 and len(w978_readback)==300,'W978 apply/readback counts')
    w978_rank={r['continuationRank']:r for r in readjl(PREV/'source-inventory-selection.jsonl')}
    plan_by_key={(r['continuationRank'],r['locale']):r for r in w978_plan}
    need(len(plan_by_key)==89,'W978 plan identities')
    for r in w978_plan:
        src=w978_rank[r['continuationRank']]
        need(r['sourceId']==src['sourceId'] and r['sourceSha256']==src['sourceSha256'] and r['remainingQueueRank']==src['remainingQueueRank'],'W978 applied source binding')
        prior_applied.append({'applicationPlanSha256':sha((W978/'exact-hash-apply-plan.jsonl').read_bytes()),'appliedHead':w978_summary['postCommitHead'],
          'appliedTargetSha256':r['afterSha256'],'attestedAtHead':HEAD,'catalogPath':r['catalogPath'],'continuationRank':r['continuationRank'],
          'currentTargetSha256':r['afterSha256'],'locale':r['locale'],'priorCurrentTargetSha256':r['beforeSha256'],'priorWindow':'W84',
          'productCommit':w978_summary['postCommitHead'],'remainingQueueRank':r['remainingQueueRank'],'sourceId':r['sourceId'],
          'sourceIdSha256':tsha(r['sourceId']),'sourceSha256':r['sourceSha256'],'sourceTextIncluded':False,'targetRemainsApplied':True,
          'targetTextIncluded':False})
    for r in w978_readback:
        rankrow=w978_rank[r['continuationRank']]
        need(r['matches'] is True and r['actualValue']==r['expectedValue'],'W978 cell readback')
        target_hash=tsha(r['actualValue'])
        need((r['continuationRank'],r['locale']) not in {(x['continuationRank'],x['locale']) for x in window_readback},'duplicate W978 readback key')
        window_readback.append({'attestedAtHead':w978_summary['postCommitHead'],'continuationRank':r['continuationRank'],
          'remainingQueueRank':rankrow['remainingQueueRank'],'currentCatalogTargetSha256':target_hash,'locale':r['locale'],
          'readbackMatchesCurrent':True,'rootDispositionClass':'applied' if (r['continuationRank'],r['locale']) in plan_by_key else 'accept-current',
          'rootExpectedAfterSha256':target_hash,'rootObservedAfterSha256':target_hash,'sourceIdSha256':tsha(rankrow['sourceId']),
          'sourceSha256':rankrow['sourceSha256'],'sourceTextIncluded':False,'targetTextIncluded':False,'window':'W84'})
    need((len(inventory),len(exclusions),len(prior_holds),len(current_holds),len(prior_applied),len(window_applied),len(window_readback),len(resolutions))==(6175,2085,397,12,389,288,600,25),'prior continuity counts')
    need(all(not any(k in TEXT_KEYS for k in r) for rows in (exclusions,prior_holds,current_holds,prior_applied,window_applied,window_readback,resolutions) for r in rows),'prior hash-only text redaction')

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
    source_by_id={'src_'+tsha(k)[:16]:k for k in ordered}
    need(len(source_by_id)==6175,'source ID collision')
    inv_by={r['sourceId']:r for r in inventory}
    need(set(inv_by)==set(source_by_id),'inventory ID set')
    for sid,s in source_by_id.items(): need(inv_by[sid]['sourceSha256']==tsha(s),'inventory source hash '+sid)
    rankrows={r['continuationRank']:r for r in inventory if r.get('continuationRank') is not None}
    need(len(rankrows)==4967,'ranked inventory count')
    selected=[]
    for rank in range(FIRST,LAST+1):
        r=rankrows.get(rank); need(r is not None,'missing continuation rank '+str(rank))
        sid=r['sourceId']; source=source_by_id[sid]
        need((r['remainingQueueRank'],r['eligibleForFreshWindow'],r['priorSelectedOrRewriteExcluded'],r['baselineExcluded'])==(rank-100,True,False,False),'rank eligibility '+str(rank))
        selected.append({'continuationRank':rank,'remainingQueueRank':rank-100,'sourceId':sid,'sourceIdSha256':tsha(sid),'sourceSha256':tsha(source),'source':source})
    exclusion_by={r['sourceId']:r for r in exclusions}
    need(len(exclusion_by)==2085,'prior exclusion scope')
    for s in selected:
        need(s['sourceId'] not in exclusion_by,'selected ID already excluded '+s['sourceId'])
        exclusion_by[s['sourceId']]={'sourceId':s['sourceId'],'sourceIdSha256':tsha(s['sourceId']),'sourceSha256':s['sourceSha256'],
          'continuationRank':s['continuationRank'],'remainingQueueRank':s['remainingQueueRank'],'selectionOrigin':'W1003-W1027 current-head review window',
          'exclusionOrigins':['W1003-W1027 current-head candidate-free input'],'exclusionConfirmed':True,'sourceTextIncluded':False,'targetTextIncluded':False}
    need(len(exclusion_by)==2110,'updated exclusion count')
    updated_inventory=[]
    for sid,old in inv_by.items():
        excluded=sid in exclusion_by
        updated_inventory.append({'sourceId':sid,'sourceSha256':old['sourceSha256'],'continuationRank':old.get('continuationRank'),
          'remainingQueueRank':old.get('remainingQueueRank'),'baselineExcluded':old.get('baselineExcluded',False),
          'priorSelectedOrRewriteExcluded':excluded,'eligibleForFreshWindow':old.get('continuationRank') is not None and not old.get('baselineExcluded',False) and not excluded,
          'localeCoverage':12,'sourceTextIncluded':False,'attestedAtHead':HEAD})
    updated_inventory.sort(key=lambda r:r['sourceId'])

    runtime=[]
    for path,entry in sorted(tree.items()):
        if not production_path(path): continue
        data=(REPO/path).read_bytes(); need(blobsha(data)==entry['gitBlob'],'runtime blob '+path)
        runtime.append({'path':path,'bytes':len(data),'sha256':sha(data),'gitBlob':entry['gitBlob'],'lineCount':len(data.decode('utf-8').splitlines())})
    need(len(runtime)==279,'runtime file count')
    refs_by={}; runtime_by={r['path']:r for r in runtime}
    for s in selected:
        literal=re.compile(r'(?<![A-Za-z0-9_$])([\"\'])'+re.escape(s['source'])+r'\1')
        refs=[]
        for pin in runtime:
            lines=(REPO/pin['path']).read_text(encoding='utf-8').splitlines()
            for idx,line in enumerate(lines):
                if literal.search(line):
                    context=[{'line':n+1,'text':lines[n]} for n in range(max(0,idx-4),min(len(lines),idx+3))]
                    refs.append({'path':pin['path'],'line':idx+1,'lineText':line,'lineSha256':tsha(line),'context':context,
                      'contextSha256':sha(canon(context)),'fileBytes':pin['bytes'],'fileSha256':pin['sha256'],'gitBlob':pin['gitBlob']})
        refs_by[s['sourceId']]=refs
    caller_rows=[]; cell_rows=[]; token_counts=collections.Counter(); caller_ref_total=0
    for s in selected:
        sid=s['sourceId']; refs=refs_by[sid]; caller_ref_total+=len(refs); csha=sha(canon(refs)); has_callers=bool(refs)
        crow={'continuationRank':s['continuationRank'],'remainingQueueRank':s['remainingQueueRank'],'sourceId':sid,'sourceIdSha256':tsha(sid),
          'sourceSha256':s['sourceSha256'],'productionCallerCount':len(refs),'callerContextSha256':csha,'callerReferenceTextIncluded':has_callers,
          'sourceTextIncluded':has_callers,'exactHead':HEAD,'exactTree':TREE,'callers':refs}
        if has_callers: crow['source']=s['source']
        caller_rows.append(crow)
        for locale in LOCALES:
            target=catalog_objs[locale][s['source']]; th=tsha(target); evidence=token_data(s['source'],target) if has_callers else None
            if evidence:
                for key,ok in [('placeholder',evidence['placeholders']['matches']),('markup',evidence['markup']['matches']),
                  ('numeric',evidence['numbers']['sourcePreserved']),('protectedLiteral',not evidence['protectedLiterals']['missing'])]:
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
    output_window_holds=list(current_holds)
    new_window_holds=[]
    selected_by_rank={r['continuationRank']:r for r in selected}
    caller_by_id={r['sourceId']:r for r in caller_rows}
    for cell in cell_rows:
        if not cell['candidateFreeHold']: continue
        selected_source=selected_by_rank[cell['continuationRank']]
        caller=caller_by_id[cell['sourceId']]
        hold={'attestedAtHead':HEAD,'callerContextSha256':caller['callerContextSha256'],'callerCount':0,
          'continuationRank':cell['continuationRank'],'currentTargetSha256':cell['currentTargetSha256'],
          'holdReasonClass':'no-pinned-production-localization-caller','locale':cell['locale'],
          'remainingQueueRank':cell['remainingQueueRank'],'sourceIdSha256':tsha(cell['sourceId']),
          'sourceSha256':cell['sourceSha256'],'sourceTextIncluded':False,'targetTextIncluded':False,
          'proposalTextIncluded':False,'window':'W85'}
        new_window_holds.append(hold)
    output_window_holds.extend(new_window_holds)

    prior_boundary={'continuationRank':1002,'remainingQueueRank':902,'sourceId':rankrows[1002]['sourceId'],'sourceSha256':rankrows[1002]['sourceSha256']}
    nextrow=rankrows[1028]
    need(rankrows[1003]['sourceId']==selected[0]['sourceId'],'next boundary continuity')
    boundary={'window':'W85','head':HEAD,'tree':TREE,'previousWindow':'W84 / W978-W1002','previousWindowFinalRank':prior_boundary,
      'selectedWindow':[{'continuationRank':r['continuationRank'],'remainingQueueRank':r['remainingQueueRank'],'sourceId':r['sourceId'],'sourceSha256':r['sourceSha256']} for r in selected],
      'nextUnselected':{'continuationRank':1028,'remainingQueueRank':928,'sourceId':nextrow['sourceId'],'sourceSha256':nextrow['sourceSha256']},
      'selectionRule':'next 25 eligible stable source IDs from pinned W84 inventory; continuationRank = remainingQueueRank + 100'}
    ordered_manifest={'entryCount':len(ordered),'orderedKeySha256':sha(('\n'.join(ordered)+'\n').encode()),
      'sourceIdOrderSha256':sha(b''.join(bytes.fromhex(tsha(k)) for k in ordered)),
      'sourceRecordOrderSha256':sha(b''.join(bytes.fromhex(tsha('src_'+tsha(k)[:16]))+bytes.fromhex(tsha(k)) for k in ordered)),
      'catalogKeysAreEnglishSourceStrings':True,'exactHead':HEAD,'exactTree':TREE}
    writej('live-before.json',before)
    writej('catalog-key-order-attestation.json',ordered_manifest)
    writejl('catalog-structure.jsonl',catalog_rows)
    writejl('runtime-file-pins.jsonl',runtime)
    writejl('source-inventory-pinned.jsonl',updated_inventory)
    writejl('source-inventory-selection.jsonl',[{k:v for k,v in r.items() if k!='source'} for r in selected])
    writejl('selected-sources.jsonl',[({k:v for k,v in r.items() if k!='source'}|{'sourceTextIncluded':bool(refs_by[r['sourceId']])}|({'source':r['source']} if refs_by[r['sourceId']] else {'sourceTextOmittedForNoCallerHold':True})) for r in selected])
    writejl('source-current-cells.jsonl',cell_rows)
    writejl('caller-contexts.jsonl',caller_rows)
    writejl('prior-selected-id-exclusions-hash-only.jsonl',sorted(exclusion_by.values(),key=lambda r:r['sourceId']))
    for name in ['prior-held-cell-reattestation-hash-only.jsonl',
      'prior-hold-resolution-history-hash-only.jsonl','window-applied-targets-reattestation-hash-only.jsonl']:
        (OUT/name).write_bytes((PREV/name).read_bytes())
    writejl('prior-applied-targets-reattestation-hash-only.jsonl',prior_applied)
    writejl('window-application-readback-hash-only.jsonl',window_readback)
    writejl('window-holds-hash-only.jsonl',output_window_holds)
    writej('continuity-provenance.json',{'priorPacketPath':'docs/pr-evidence/pr409-localization-2026-11-05/window-978-1002/candidate-free/input',
      'priorPacketManifestSha256':sha((PREV/'manifest.json').read_bytes()),'priorPacketChecksumsSha256':sha((PREV/'SHA256SUMS.txt').read_bytes()),
      'priorLiveHead':'1c2fe3be2c720693cbcb12d377bf1177804f4e77','priorLiveTree':'808501cbc3b6ed873a47d7188189d486f0673f5e','currentAttestedHead':HEAD,'priorSourceExclusions':2085,'newlySelectedIdsExcluded':25,
      'priorActiveHolds':len(prior_holds)+len(current_holds),'priorAppliedTargets':len(prior_applied)+len(window_applied),
      'priorWindowApplicationReadbackRows':len(window_readback),'sourceTextIncluded':False,'targetTextIncluded':False})
    writej('baseline-token-mismatch-summary.json',{'cellCount':300,'callerBackedCells':sum(bool(refs_by[s['sourceId']]) for s in selected)*12,
      'noCallerHashOnlyCells':sum(not refs_by[s['sourceId']] for s in selected)*12,'mismatchCounts':dict(token_counts),
      'proposedTargetsIncluded':False,'note':'Token checks are candidate-free evidence on exact-head current values; no-caller holds expose no source or target text.'})
    writej('selection-and-boundary.json',boundary)
    after=capture_live()
    need(before['remoteRefs']==after['remoteRefs'] and (before['headSha'],before['baseSha'],before['mainApiSha'])==(after['headSha'],after['baseSha'],after['mainApiSha']),'live refs moved during build')
    writej('live-after.json',after)
    summary={'result':'PASS','artifact':'slskdN PR #409 W1003-W1027 candidate-free exact-head input','window':'W85',
      'head':HEAD,'tree':TREE,'branch':BRANCH,'baseRef':'main','baseSha':BASE,'baseTree':BASETREE,'mainSha':MAIN,'mainTree':MAINTREE,
      'continuationRankRange':[FIRST,LAST],'remainingQueueRankRange':[QFIRST,QLAST],'sourceCount':25,'localeCount':12,'cellCount':300,
      'catalogCount':12,'catalogEntryCountPerLocale':6175,'sourceInventoryRows':6175,'productionRuntimeFileCount':279,
      'sourceCallerReferenceCount':caller_ref_total,'sourcesWithCallers':sum(bool(refs_by[s['sourceId']]) for s in selected),
      'sourcesWithoutCallers':sum(not refs_by[s['sourceId']] for s in selected),'priorSelectedIdsAndNewWindowExclusions':len(exclusion_by),
      'priorActiveHoldsReattested':len(prior_holds)+len(current_holds),'newWindowHashOnlyHoldCells':len(new_window_holds),
      'resultingActiveHashOnlyHoldCells':len(prior_holds)+len(current_holds)+len(new_window_holds),'priorAppliedTargetsReattested':len(prior_applied)+len(window_applied),
      'priorWindowReadbackRows':len(window_readback),'baselineTokenMismatchCounts':dict(token_counts),'proposedTargetsIncluded':False,
      'reviewDecisionsIncluded':False,'blindReviewUsed':False,'crossReviewUsed':False,'rootAdjudicationPerformed':False,
      'catalogsEdited':False,'repoEdited':False,'testsBuildsScansCiRun':False,'workflowChanges':0}
    writej('summary.json',summary)
    (OUT/'README.md').write_text('# slskdN PR #409 W1003–W1027 candidate-free input\n\n'
      'Pinned to PR #409 head '+HEAD+' / tree '+TREE+', base '+BASE+', live main '+MAIN+'. The packet selects continuation ranks 1003–1027 (remaining-queue ranks 903–927), 25 stable source IDs across all 12 locale catalogs (300 cells).\n\n'
      'Inputs include exact-head current catalog values, caller references from 279 production runtime files, ordered catalog pins, token evidence, and hash-only hold/application continuity through W978–W1002. No proposed translations, decisions, blind review, cross-review, or root adjudication are included. Rows with no pinned production caller are hash-only holds with source and target text omitted.\n',encoding='utf-8')
    files=sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p.name not in {'manifest.json','SHA256SUMS.txt'})
    manifest={'schemaVersion':1,'repository':SLUG,'pullRequest':409,'branch':BRANCH,'window':'W85','candidateFree':True,
      'head':HEAD,'tree':TREE,'baseSha':BASE,'mainSha':MAIN,'continuationRankRange':[FIRST,LAST],
      'remainingQueueRankRange':[QFIRST,QLAST],'sourceCount':25,'localeCount':12,'cellCount':300,'locales':LOCALES,
      'catalogEntryCountPerLocale':6175,'catalogCount':12,'productionRuntimeFileCount':279,
      'sourceCallerReferenceCount':caller_ref_total,'sourcesWithCallers':summary['sourcesWithCallers'],
      'sourcesWithoutCallers':summary['sourcesWithoutCallers'],'priorSelectedIdsAndNewWindowExclusions':len(exclusion_by),
      'priorActiveHoldsReattested':len(prior_holds)+len(current_holds),'newWindowHashOnlyHoldCells':len(new_window_holds),
      'resultingActiveHashOnlyHoldCells':len(prior_holds)+len(current_holds)+len(new_window_holds),'priorAppliedTargetsReattested':len(prior_applied)+len(window_applied),
      'baselineTokenMismatchCounts':dict(token_counts),'proposedTargetsIncluded':False,'reviewDecisionsIncluded':False,
      'blindReviewUsed':False,'crossReviewUsed':False,'rootAdjudicationPerformed':False,'files':[{'path':n,'sha256':sha((OUT/n).read_bytes()),'bytes':(OUT/n).stat().st_size} for n in files]}
    writej('manifest.json',manifest)
    sums=sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
    (OUT/'SHA256SUMS.txt').write_text(''.join(sha((OUT/n).read_bytes())+'  '+n+'\n' for n in sums),encoding='utf-8')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'sources':25,'cells':300,'callers':caller_ref_total,
      'sourcesWithoutCallers':summary['sourcesWithoutCallers'],'priorHolds':summary['priorActiveHoldsReattested'],
      'priorAppliedTargets':summary['priorAppliedTargetsReattested'],'exclusions':len(exclusion_by),'checksummedFiles':len(sums)},indent=2))
if __name__=='__main__': main()
