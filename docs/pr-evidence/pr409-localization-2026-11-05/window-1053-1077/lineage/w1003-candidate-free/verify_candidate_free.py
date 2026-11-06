#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, re, subprocess, sys, unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parent
HEAD='8c752c49281418fdd96341ed46f5c321627b625f'; TREE='b930b0d82679e843849e54456f3250e422c4682c'
BASE='f25d263a2a7cdb2c8f76c40c346cb10f749a9356'; MAIN='bc6251ff4ea5a7e59f2d86e2400c90520601f46e'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PREL='docs/pr-evidence/pr409-localization-2026-11-05/window-978-1002/candidate-free/input'
TEXT_KEYS={'source','sourceText','target','currentTarget','proposedTarget','proposedTargetText','candidateTarget','reviewTarget','rationale','reason'}
def need(ok,msg):
    if not ok: raise SystemExit('FAIL: '+msg)
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def blobsha(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def readj(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def readjl(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args])
def prod(path):
    parts=path.split('/'); name=parts[-1]
    return path.startswith('src/web/src/') and Path(path).suffix.lower() in {'.js','.jsx','.ts','.tsx'} and not any(x in {'__tests__','__specs__'} for x in parts) and not any(x in name for x in ('.test.','.spec.'))
def verify_sums(root):
    seen={}
    for line in (root/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1); need(n not in seen,'duplicate checksum '+n); p=root/n
        need(p.is_file() and sha(p.read_bytes())==h,'checksum '+n); seen[n]=h
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    need(actual==set(seen),'checksum file inventory')
    return seen
def token_data(source,target):
    placeholders=lambda s:collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s))
    tags=lambda s:collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',s))
    nums=lambda s:[''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in t) for t in re.findall(r'\d+',s)]
    protected=lambda s:sorted(set(re.findall(r'\b[A-Z][A-Z0-9]{1,}\b',s))|{x for x in ('slskdN','PodCore','Wishlist','soulfind','FFmpeg','Lidarr') if x in s})
    sp,tp=placeholders(source),placeholders(target); st,tt=tags(source),tags(target); sn,tn=nums(source),nums(target); sl=protected(source)
    return {'placeholders':{'source':sorted(sp.elements()),'target':sorted(tp.elements()),'matches':sp==tp},
      'markup':{'source':sorted(st.elements()),'target':sorted(tt.elements()),'matches':st==tt},
      'numbers':{'source':sn,'target':tn,'sourcePreserved':all(tn.count(x)>=n for x,n in collections.Counter(sn).items())},
      'protectedLiterals':{'source':sl,'target':protected(target),'missing':[x for x in sl if x not in target]}}
def main():
    if len(sys.argv)!=2: raise SystemExit('usage: verify_candidate_free.py /path/to/exact-worktree')
    repo=Path(sys.argv[1]).resolve(); need(repo.is_dir(),'repo path')
    need(git(repo,'rev-parse','HEAD').decode().strip()==HEAD,'worktree HEAD')
    need(git(repo,'rev-parse','HEAD^{tree}').decode().strip()==TREE,'worktree tree')
    need(not git(repo,'status','--porcelain=v1').decode().strip(),'worktree must be clean')
    sums=verify_sums(ROOT); m=readj(ROOT/'manifest.json')
    need((m.get('head'),m.get('tree'),m.get('window'))==(HEAD,TREE,'W85'),'manifest identity')
    need(m.get('candidateFree') is True and m.get('proposedTargetsIncluded') is False and m.get('reviewDecisionsIncluded') is False,'candidate-free boundary')
    need(m.get('blindReviewUsed') is False and m.get('crossReviewUsed') is False and m.get('rootAdjudicationPerformed') is False,'review stages not performed')
    actual=set(sums)-{'manifest.json'}; listed={r['path']:r for r in m.get('files',[])}
    need(set(listed)==actual,'manifest file inventory')
    for n,r in listed.items(): need(r['bytes']==(ROOT/n).stat().st_size and r['sha256']==sha((ROOT/n).read_bytes()),'manifest pin '+n)
    summary=readj(ROOT/'summary.json')
    need(summary['head']==HEAD and summary['tree']==TREE and summary['sourceCount']==25 and summary['cellCount']==300,'summary pin')
    before=readj(ROOT/'live-before.json'); after=readj(ROOT/'live-after.json')
    need(before['remoteRefs']==after['remoteRefs'] and before['headSha']==after['headSha']==HEAD and before['baseSha']==after['baseSha']==BASE,'live entry/exit pins')
    need(before['mainApiSha']==after['mainApiSha']==MAIN and before['remoteMainSha']==after['remoteMainSha']==MAIN,'live main pin')
    tree={}
    for item in git(repo,'ls-tree','-r','-z',HEAD).split(b'\0'):
        if not item: continue
        meta,path=item.split(b'\t',1); mode,kind,oid=meta.decode().split(); tree[path.decode()]={'mode':mode,'kind':kind,'gitBlob':oid}
    structs=readjl(ROOT/'catalog-structure.jsonl'); need(len(structs)==12 and [x['locale'] for x in structs]==LOCALES,'catalog locales')
    catalogs={}; keys=None
    for pin in structs:
        raw=(repo/pin['path']).read_bytes(); need(sha(raw)==pin['sha256'] and len(raw)==pin['bytes'] and blobsha(raw)==pin['gitBlob']==tree[pin['path']]['gitBlob'],'catalog current pin '+pin['locale'])
        obj=json.loads(raw.decode('utf-8')); need(len(obj)==6175,'catalog key count '+pin['locale'])
        if keys is None: keys=list(obj)
        else: need(list(obj)==keys,'catalog order '+pin['locale'])
        need(sha(('\n'.join(keys)+'\n').encode())==pin['orderedKeySha256'],'catalog key hash '+pin['locale'])
        catalogs[pin['locale']]=obj
    source_by={'src_'+tsha(s)[:16]:s for s in keys}; need(len(source_by)==6175,'source ID uniqueness')
    selection=readjl(ROOT/'source-inventory-selection.jsonl'); selected=readjl(ROOT/'selected-sources.jsonl')
    need(len(selection)==len(selected)==25,'selected source count')
    need([r['continuationRank'] for r in selection]==list(range(1003,1028)) and [r['remainingQueueRank'] for r in selection]==list(range(903,928)),'rank sequence')
    byid={r['sourceId']:r for r in selection}; full={r['sourceId']:r for r in selected}; need(set(byid)==set(full),'selected source IDs')
    inv=readjl(ROOT/'source-inventory-pinned.jsonl'); need(len(inv)==6175,'inventory rows'); invby={r['sourceId']:r for r in inv}
    need(set(invby)==set(source_by),'inventory IDs')
    rankmap={r['continuationRank']:r for r in inv if r.get('continuationRank') is not None}
    for sid,s in source_by.items(): need(invby[sid]['sourceSha256']==tsha(s),'inventory source pin')
    for ix,s in enumerate(selection):
        source=source_by[s['sourceId']]; row=full[s['sourceId']]
        need(s['sourceId']==('src_'+tsha(source)[:16]) and s['sourceSha256']==tsha(source) and s['sourceIdSha256']==tsha(s['sourceId']),'selected source hash')
        need(row['sourceSha256']==tsha(source),'selected source hash')
        if row['sourceTextIncluded'] is True: need(row.get('source')==source,'selected source text')
        else: need(row.get('sourceTextOmittedForNoCallerHold') is True and 'source' not in row,'selected no-caller source redaction')
        need(rankmap[s['continuationRank']]['eligibleForFreshWindow'] is False and rankmap[s['continuationRank']]['priorSelectedOrRewriteExcluded'] is True,'selected exclusion state')
        need(s['remainingQueueRank']==s['continuationRank']-100,'queue rank mapping')
    boundary=readj(ROOT/'selection-and-boundary.json')
    need(boundary['previousWindowFinalRank']['continuationRank']==1002 and boundary['selectedWindow'][0]['sourceId']==selection[0]['sourceId'],'previous boundary')
    need(boundary['nextUnselected']['continuationRank']==1028 and boundary['nextUnselected']['sourceId']==rankmap[1028]['sourceId'],'next boundary')
    runtime=readjl(ROOT/'runtime-file-pins.jsonl'); expected={p for p in tree if prod(p)}
    need(len(runtime)==279 and {r['path'] for r in runtime}==expected,'runtime file set')
    runtime_lines={}
    for pin in runtime:
        raw=(repo/pin['path']).read_bytes(); need(sha(raw)==pin['sha256'] and len(raw)==pin['bytes'] and blobsha(raw)==pin['gitBlob']==tree[pin['path']]['gitBlob'],'runtime pin '+pin['path'])
        runtime_lines[pin['path']]=raw.decode('utf-8').splitlines()
    callers=readjl(ROOT/'caller-contexts.jsonl'); need(len(callers)==25,'caller rows'); callerby={r['sourceId']:r for r in callers}
    cells=readjl(ROOT/'source-current-cells.jsonl'); need(len(cells)==300,'cell count')
    need([(r['continuationRank'],r['locale']) for r in cells]==[(rank,l) for rank in range(1003,1028) for l in LOCALES],'cell ordering')
    hold_ids=set(); token_mismatches=collections.Counter(); caller_total=0
    for s in selection:
        sid=s['sourceId']; source=source_by[sid]; cr=callerby[sid]; refs=[]
        literal=re.compile(r'(?<![A-Za-z0-9_$])([\"\'])'+re.escape(source)+r'\1')
        for pin in runtime:
            lines=runtime_lines[pin['path']]
            for i,line in enumerate(lines):
                if literal.search(line):
                    context=[{'line':j+1,'text':lines[j]} for j in range(max(0,i-4),min(len(lines),i+3))]
                    refs.append({'path':pin['path'],'line':i+1,'lineText':line,'lineSha256':tsha(line),'context':context,'contextSha256':sha(canon(context)),
                      'fileBytes':pin['bytes'],'fileSha256':pin['sha256'],'gitBlob':pin['gitBlob']})
        caller_total+=len(refs); need(cr['productionCallerCount']==len(refs) and cr['callerContextSha256']==sha(canon(refs)),'caller pin '+sid)
        need(cr['callers']==refs and cr['sourceTextIncluded']==bool(refs),'caller evidence '+sid)
        if refs: need(cr.get('source')==source,'caller source text '+sid)
        else: need('source' not in cr,'caller source redaction '+sid)
        if not refs: hold_ids.add(sid)
        for row in [x for x in cells if x['sourceId']==sid]:
            target=catalogs[row['locale']][source]; ev=token_data(source,target)
            need(row['currentTargetSha256']==tsha(target) and row['sourceSha256']==tsha(source),'current target hash')
            need(row['catalogFileSha256']==next(x['sha256'] for x in structs if x['locale']==row['locale']) and row['catalogGitBlob']==tree[row['catalogPath']]['gitBlob'],'cell catalog pin')
            need(row['callerContextSha256']==cr['callerContextSha256'] and row['callerCount']==len(refs),'cell caller pin')
            need(row['containsCandidate'] is False and row['decision'] is None and row['candidateFreeHold']==(not refs),'candidate-free cell')
            if refs:
                need(row['source']==source and row['currentTarget']==target and row['tokenEvidence']==ev and row['tokenEvidenceSha256']==sha(canon(ev)),'cell text/token evidence')
                for kind,ok in [('placeholder',ev['placeholders']['matches']),('markup',ev['markup']['matches']),('numeric',ev['numbers']['sourcePreserved']),('protectedLiteral',not ev['protectedLiterals']['missing'])]:
                    if not ok: token_mismatches[kind]+=1
            else:
                need(not(set(row)&TEXT_KEYS) and row['sourceTextIncluded'] is False and row['currentTargetTextIncluded'] is False,'no-caller cell redaction')
    baseline_tokens=readj(ROOT/'baseline-token-mismatch-summary.json')
    need(dict(token_mismatches)==baseline_tokens['mismatchCounts'],'candidate-free token mismatch summary')
    prior=repo/PREL; prior_m=readj(prior/'manifest.json'); need((prior_m['head'],prior_m['tree'])==('1c2fe3be2c720693cbcb12d377bf1177804f4e77','808501cbc3b6ed873a47d7188189d486f0673f5e'),'prior lineage head')
    psums={}
    for line in (prior/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1); need(sha((prior/n).read_bytes())==h,'prior packet checksum '+n); psums[n]=h
    provenance=readj(ROOT/'continuity-provenance.json')
    need(provenance['priorPacketManifestSha256']==sha((prior/'manifest.json').read_bytes()) and provenance['priorPacketChecksumsSha256']==sha((prior/'SHA256SUMS.txt').read_bytes()),'prior packet pin')
    w978=repo/'docs/pr-evidence/pr409-localization-2026-11-05/window-978-1002/root-application'
    w978_summary=readj(w978/'application-summary.json')
    w978_plan=readjl(w978/'exact-hash-apply-plan.jsonl')
    w978_readback=readjl(w978/'final-head-readback.jsonl')
    need(w978_summary['inputHead']==prior_m['head'] and w978_summary['postCommitHead']=='e18feff151531142bd4d76b394711aaca57861c6','W978 application head pin')
    need(w978_summary['exactHashEditCount']==89 and len(w978_plan)==89 and len(w978_readback)==300,'W978 application/readback counts')
    need(subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',w978_summary['postCommitHead'],HEAD]).returncode==0,'W978 product commit ancestry')
    grouped_plan={}
    for edit in w978_plan:
        grouped_plan.setdefault(edit['catalogPath'],[]).append(edit)
        need(tsha(edit['source'])==edit['sourceSha256'] and tsha(edit['before'])==edit['beforeSha256'] and tsha(edit['after'])==edit['afterSha256'],'W978 edit hash binding')
    readback_by={(r['continuationRank'],r['locale']):r for r in w978_readback}
    need(len(readback_by)==300 and all(r['matches'] and r['actualValue']==r['expectedValue'] for r in w978_readback),'W978 all-cell readback')
    w978_selected={r['continuationRank']:r for r in readjl(prior/'source-inventory-selection.jsonl')}
    for edit in w978_plan:
        src=w978_selected[edit['continuationRank']]
        rb=readback_by[(edit['continuationRank'],edit['locale'])]
        need(edit['sourceId']==src['sourceId'] and edit['sourceSha256']==src['sourceSha256'] and rb['actualValue']==edit['after'],'W978 selected/apply binding')
    for pin in readjl(prior/'catalog-structure.jsonl'):
        path=pin['path']; raw=git(repo,'show',prior_m['head']+':'+path)
        need(sha(raw)==pin['sha256'],'W978 parent catalog hash '+path)
        expected=json.loads(raw.decode('utf-8'))
        for edit in grouped_plan.get(path,[]):
            need(expected.get(edit['source'])==edit['before'],'W978 parent exact-hash guard '+path)
            expected[edit['source']]=edit['after']
        expected_bytes=(json.dumps(expected,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
        need((repo/path).read_bytes()==expected_bytes,'current catalog equals W978 parent plus its exact plan '+path)
    prior_runtime={r['path']:r for r in readjl(prior/'runtime-file-pins.jsonl')}
    need({r['path']:r['sha256'] for r in runtime}=={p:r['sha256'] for p,r in prior_runtime.items()},'prior production runtime unchanged at current head')
    exclusions=readjl(ROOT/'prior-selected-id-exclusions-hash-only.jsonl'); need(len(exclusions)==2110,'prior ID exclusions')
    for r in exclusions:
        need(r['sourceIdSha256']==tsha(r['sourceId']) and r['sourceId']=='src_'+r['sourceSha256'][:16],'exclusion ID/source hash binding')
        if r['sourceId'] in source_by: need(r['sourceSha256']==tsha(source_by[r['sourceId']]),'current exclusion source hash')
        else: need(r['sourceTextIncluded'] is False and r['targetTextIncluded'] is False,'retired exclusion redaction')
    ph=readjl(ROOT/'prior-held-cell-reattestation-hash-only.jsonl'); wh=readjl(ROOT/'window-holds-hash-only.jsonl')
    prior_window_holds=[r for r in wh if r.get('window')=='W953-W977']
    new_window_holds=[r for r in wh if r.get('window')=='W85']
    need(len(ph)+len(prior_window_holds)==409 and len(new_window_holds)==12,'prior and new active hold counts')
    source_inventory=readjl(prior/'source-inventory-pinned.jsonl')
    prior_rankrows={r['continuationRank']:r for r in source_inventory if r.get('continuationRank') is not None}
    prior_applied=readjl(ROOT/'prior-applied-targets-reattestation-hash-only.jsonl'); window_applied=readjl(ROOT/'window-applied-targets-reattestation-hash-only.jsonl')
    need(len(prior_applied)+len(window_applied)==677,'prior applied target count')
    pa=prior_applied; wa=window_applied
    for r in ph:
        s=source_by.get(r['sourceId']); need(s is not None and tsha(s)==r['sourceSha256'] and tsha(catalogs[r['locale']][s])==r['currentTargetSha256'],'active prior hold readback')
        need(r['currentCallerContextSha256']==r['priorCallerContextSha256'] and r['callerEvidenceUnchanged'] is True,'active prior hold caller pin')
    for r in prior_window_holds:
        old=prior_rankrows[r['continuationRank']]; s=source_by[old['sourceId']]
        need(r['sourceIdSha256']==tsha(old['sourceId']) and r['sourceSha256']==tsha(s) and tsha(catalogs[r['locale']][s])==r['currentTargetSha256'],'W953 hold readback')
    current_cells={(r['continuationRank'],r['locale']):r for r in cells}
    current_selected={r['continuationRank']:r for r in selection}
    for r in new_window_holds:
        cell=current_cells[(r['continuationRank'],r['locale'])]
        selected_source=current_selected[r['continuationRank']]
        need(cell['candidateFreeHold'] is True and cell['callerCount']==0 and cell['currentTargetTextIncluded'] is False,'new hash-only hold cell')
        need(r['sourceIdSha256']==tsha(selected_source['sourceId']) and r['sourceSha256']==selected_source['sourceSha256'] and r['currentTargetSha256']==cell['currentTargetSha256'],'new hash-only hold binding')
        need(r['callerContextSha256']==callerby[selected_source['sourceId']]['callerContextSha256'] and r['callerCount']==0,'new hash-only caller binding')
        need(r['sourceTextIncluded'] is False and r['targetTextIncluded'] is False and r['proposalTextIncluded'] is False,'new hash-only hold redaction')
    for r in pa:
        s=source_by.get(r['sourceId']); need(s is not None and tsha(s)==r['sourceSha256'],'prior applied source')
        target=tsha(catalogs[r['locale']][s]); expected_hash=r.get('currentTargetSha256',r.get('appliedTargetSha256'))
        need(target==expected_hash,'prior applied target readback')
    for r in wa:
        s=source_by[r['sourceId']]; need(tsha(s)==r['sourceSha256'] and tsha(catalogs[r['locale']][s])==r['currentTargetSha256']==r['appliedTargetSha256'],'W953 applied target readback')
    rb=readjl(ROOT/'window-application-readback-hash-only.jsonl'); need(len(rb)==600,'prior W953/W978 600-cell readback')
    for r in rb:
        sid=prior_rankrows[r['continuationRank']]['sourceId']; s=source_by[sid]
        need(r['sourceSha256']==tsha(s) and tsha(catalogs[r['locale']][s])==r['currentCatalogTargetSha256']==r['rootObservedAfterSha256'] and r['readbackMatchesCurrent'],'W953 current readback')
    resolutions=readjl(ROOT/'prior-hold-resolution-history-hash-only.jsonl'); need(len(resolutions)==25,'hold resolution history')
    for r in resolutions:
        s=source_by.get(r['sourceId'])
        if s is None: need(r['currentSourcePresent'] is False and r['currentTargetSha256'] is None,'historical absent source')
        else: need(tsha(s)==r['sourceSha256'] and tsha(catalogs[r['locale']][s])==r['currentTargetSha256']==r['resolvedTargetSha256'],'historical resolution target')
    print(json.dumps({'result':'PASS','verifier':'exact-worktree','head':HEAD,'tree':TREE,'sources':25,'cells':300,'locales':12,
      'catalogKeysPerLocale':6175,'runtimeFiles':279,'callerReferences':caller_total,'priorActiveHolds':409,'newHashOnlyHolds':12,'priorAppliedTargets':677,
      'priorWindowReadbackCells':len(rb),'newWindowHashOnlyCells':len(new_window_holds),'resultingActiveHashOnlyHoldCells':len(ph)+len(wh),'sourceExclusions':len(exclusions),'checksummedFiles':len(sums)},indent=2))
if __name__=='__main__': main()
