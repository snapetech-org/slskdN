#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, hashlib, json, re, subprocess, sys, unicodedata
from pathlib import Path
P=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--repo',type=Path,default=P.parents[4])
parser.add_argument('--w1003-input',type=Path,default=P.parent/'lineage/w1003-candidate-free')
args=parser.parse_args()
REPO=args.repo.resolve()
PREV=P.parents[1]/'window-1028-1052/candidate-free'
W1003_INPUT=args.w1003_input.resolve()
ROOT_APP=REPO/'docs/pr-evidence/pr409-localization-2026-11-05/window-1003-1027/root-application'
PREV_WINDOW_DIR=REPO/'docs/pr-evidence/pr409-localization-2026-11-05/window-1028-1052'
PREV_ROOT_APP=PREV_WINDOW_DIR/'root-application'
HEAD='ba692c15ca54942108cc9da37757f585969e6173'; TREE='27c09a8fe24030f5bb0995d809794a9e4829dc64'
BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'; BASE='f25d263a2a7cdb2c8f76c40c346cb10f749a9356'
MAIN='bc6251ff4ea5a7e59f2d86e2400c90520601f46e'; BASETREE='b2ce36e07aee6ade05e6d8795d04b9a7455a081f'; MAINTREE='4232b318aeaab4c327443638e5467ca089bbed53'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
START,END=1053,1077
TEXT_KEYS={'source','sourceText','target','currentTarget','proposedTarget','proposedTargetText','candidateTarget','reviewTarget','rationale','reason','before','after','actualValue','expectedValue'}
sys.dont_write_bytecode=True

def fail(s): raise SystemExit('FAIL: '+s)
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def blobsha(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def run(*args): return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def readjl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
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
def verify_dir(path):
    listed={}
    for line in (path/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1)
        if n in listed: fail('duplicate checksum '+n)
        if not (path/n).is_file() or sha((path/n).read_bytes())!=h: fail('checksum '+n)
        listed[n]=h
    actual={x.relative_to(path).as_posix() for x in path.rglob('*') if x.is_file() and x.name!='SHA256SUMS.txt'}
    if actual!=set(listed): fail('checksum file inventory '+str(path))
    return listed
def main():
    input_sums=verify_dir(PREV); output_sums=verify_dir(P)
    w1003_sums=verify_dir(W1003_INPUT)
    w1003_manifest=readj(W1003_INPUT/'manifest.json')
    if (w1003_manifest.get('head'),w1003_manifest.get('tree'),w1003_manifest.get('window'),w1003_manifest.get('candidateFree'),w1003_manifest.get('reviewDecisionsIncluded'))!=('8c752c49281418fdd96341ed46f5c321627b625f','b930b0d82679e843849e54456f3250e422c4682c','W85',True,False): fail('W1003 candidate-free product input pin')
    prev_window_sums={}
    for line in (PREV_WINDOW_DIR/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1)
        if n.startswith('root-application/'):
            rel=n.removeprefix('root-application/')
            path=PREV_ROOT_APP/rel
            if rel in prev_window_sums or not path.is_file() or sha(path.read_bytes())!=h: fail('W1028 root-application checksum '+rel)
            prev_window_sums[rel]=h
    actual_prev_root={x.relative_to(PREV_ROOT_APP).as_posix() for x in PREV_ROOT_APP.rglob('*') if x.is_file() and x.name!='SHA256SUMS.txt'}
    if actual_prev_root!=set(prev_window_sums): fail('W1028 root-application checksum inventory')
    m=readj(P/'manifest.json'); summary=readj(P/'summary.json')
    if (m.get('head'),m.get('tree'),m.get('window'),m.get('continuationRankRange'),m.get('remainingQueueRankRange'),m.get('candidateFree'))!=(HEAD,TREE,'W87',[1053,1077],[953,977],True): fail('manifest exact pin/window')
    if m.get('reviewDecisionsIncluded') is not False or m.get('proposedTargetsIncluded') is not False: fail('candidate-free packet contains review/candidate material')
    declared={r['path']:r['sha256'] for r in m['files']}
    actual_files={x.relative_to(P).as_posix():sha(x.read_bytes()) for x in P.rglob('*') if x.is_file() and x.name not in ('SHA256SUMS.txt','manifest.json')}
    if declared!=actual_files: fail('manifest file hashes')
    if run('rev-parse','HEAD')!=HEAD or run('rev-parse','HEAD^{tree}')!=TREE or run('branch','--show-current')!=BRANCH or run('status','--porcelain=v1'): fail('repo pin/branch/clean status')
    before=readj(P/'live-before.json'); after=readj(P/'live-after.json')
    for live in (before,after):
        if (live.get('state'),live.get('draft'),live.get('merged'),live.get('headRef'),live.get('headSha'),live.get('headTree'),live.get('baseRef'),live.get('baseSha'),live.get('baseTree'),live.get('mainApiSha'),live.get('mainTree'))!=('open',True,False,BRANCH,HEAD,TREE,'main',BASE,BASETREE,MAIN,MAINTREE): fail('live PR pin')
    if before.get('remoteRefs')!=after.get('remoteRefs') or before.get('remoteBranchSha')!=HEAD or before.get('pullRefSha')!=HEAD or before.get('remoteMainSha')!=MAIN: fail('live refs changed during build')
    # Verify prior candidate-free input and its exact source-chain pin.
    pm=readj(PREV/'manifest.json')
    if (pm.get('head'),pm.get('tree'),pm.get('window'),pm.get('candidateFree'),pm.get('reviewDecisionsIncluded'))!=('624e27d8bb108a764df6daab5cfb1c517ebac96d','d139a16988e23046ccb09f519db2d3b7ae0b86d1','W86',True,False): fail('prior input pin')
    # Read exact catalogs and pins.
    tree={}
    raw_tree=subprocess.check_output(['git','-C',str(REPO),'ls-tree','-r','-z','HEAD'])
    for item in raw_tree.split(b'\0'):
        if not item: continue
        meta,path=item.split(b'\t',1); mode,kind,oid=meta.decode().split(); tree[path.decode()]={'mode':mode,'kind':kind,'gitBlob':oid}
    cats={}; keys=None; catpins={}
    structures=readjl(P/'catalog-structure.jsonl')
    if len(structures)!=12: fail('catalog pin count')
    for loc,pin in zip(LOCALES,structures):
        path='src/web/public/locales/'+loc+'.json'; raw=(REPO/path).read_bytes(); data=json.loads(raw)
        if pin['locale']!=loc or pin['path']!=path or pin['sha256']!=sha(raw) or pin['gitBlob']!=tree[path]['gitBlob'] or pin['bytes']!=len(raw): fail('catalog exact pin '+loc)
        if len(data)!=6175 or not all(isinstance(v,str) and v for v in data.values()): fail('catalog key/value count '+loc)
        if keys is None: keys=list(data)
        elif list(data)!=keys: fail('catalog key order '+loc)
        cats[loc]=data; catpins[loc]=pin
    key_hash=sha(('\n'.join(keys)+'\n').encode())
    order=readj(P/'catalog-key-order-attestation.json')
    if order.get('orderedKeySha256')!=key_hash or order.get('entryCount')!=6175 or order.get('exactHead')!=HEAD or order.get('exactTree')!=TREE: fail('catalog key-order attestation')
    source_by_id={'src_'+tsha(k)[:16]:k for k in keys}; sid_by_hash={tsha(sid):sid for sid in source_by_id}
    if len(source_by_id)!=6175: fail('source ID collision')
    inventory=readjl(P/'source-inventory-pinned.jsonl'); inv={r['sourceId']:r for r in inventory}
    if len(inv)!=6175 or set(inv)!=set(source_by_id): fail('inventory source ID coverage')
    prior_inv={r['sourceId']:r for r in readjl(PREV/'source-inventory-pinned.jsonl')}
    rankrows={r['continuationRank']:r for r in inventory if r.get('continuationRank') is not None}
    selected_rows=readjl(P/'source-inventory-selection.jsonl'); selected=[]
    for pos,record in enumerate(selected_rows,1053):
        sid=record['sourceId']; src=source_by_id[sid]
        if record.get('continuationRank')!=pos or record.get('remainingQueueRank')!=pos-100 or record.get('sourceSha256')!=tsha(src): fail('selection rank/source '+str(pos))
        if prior_inv.get(sid,{}).get('eligibleForFreshWindow') is not True or inv[sid].get('eligibleForFreshWindow') is not False or inv[sid].get('priorSelectedOrRewriteExcluded') is not True: fail('selection eligibility/exclusion '+str(pos))
        selected.append({'continuationRank':pos,'remainingQueueRank':pos-100,'sourceId':sid,'sourceSha256':tsha(src),'source':src})
    if len(selected)!=25 or [r['sourceId'] for r in selected]!=[rankrows[p]['sourceId'] for p in range(1053,1078)]: fail('selected ranks')
    boundary=readj(P/'selection-and-boundary.json')
    expected_boundary=[{'continuationRank':r['continuationRank'],'remainingQueueRank':r['remainingQueueRank'],'sourceId':r['sourceId'],'sourceSha256':r['sourceSha256']} for r in selected]
    if boundary.get('selectedWindow')!=expected_boundary or boundary.get('nextUnselected',{}).get('continuationRank')!=1078: fail('selection boundary')
    # Runtime pins unchanged across the prior scan and current head.
    runtime=[]
    for path,e in sorted(tree.items()):
        if not production_path(path): continue
        data=(REPO/path).read_bytes(); runtime.append({'path':path,'bytes':len(data),'sha256':sha(data),'gitBlob':e['gitBlob'],'lineCount':len(data.decode('utf-8').splitlines())})
    if len(runtime)!=279 or readjl(P/'runtime-file-pins.jsonl')!=runtime or runtime!=readjl(PREV/'runtime-file-pins.jsonl'): fail('runtime pins changed')
    # Recompute exact quoted caller evidence for the selected keys.
    caller_rows=readjl(P/'caller-contexts.jsonl')
    if len(caller_rows)!=25: fail('caller row count')
    bysid={}
    for sel,row in zip(selected,caller_rows):
        if row.get('sourceId')!=sel['sourceId'] or row.get('sourceSha256')!=sel['sourceSha256']: fail('caller/source pin')
        literal=re.compile(r'(?<![A-Za-z0-9_$])([\"\'])'+re.escape(sel['source'])+r'\1')
        refs=[]
        for pin in runtime:
            lines=(REPO/pin['path']).read_text(encoding='utf-8').splitlines()
            for idx,line in enumerate(lines):
                hits=len(literal.findall(line))
                if hits:
                    context=[{'line':n+1,'text':lines[n]} for n in range(max(0,idx-4),min(len(lines),idx+3))]
                    refs.append({'path':pin['path'],'line':idx+1,'lineText':line,'literalOccurrenceCount':hits,'lineSha256':tsha(line),'context':context,'contextSha256':sha(canon(context)),
                      'fileBytes':pin['bytes'],'fileSha256':pin['sha256'],'gitBlob':pin['gitBlob']})
        if row.get('callers')!=refs or row.get('productionCallerCount')!=len(refs) or row.get('callerOccurrenceCount')!=sum(x['literalOccurrenceCount'] for x in refs) or row.get('callerContextSha256')!=sha(canon(refs)): fail('caller scan mismatch '+str(sel['continuationRank']))
        has=bool(refs)
        if row.get('sourceTextIncluded') is not has or row.get('callerReferenceTextIncluded') is not has or (has and row.get('source')!=sel['source']) or (not has and 'source' in row): fail('caller text-inclusion rule')
        bysid[sel['sourceId']]=(refs,sha(canon(refs)))
    cells=readjl(P/'source-current-cells.jsonl')
    if len(cells)!=300 or [(r['continuationRank'],r['locale']) for r in cells]!=[(pos,loc) for pos in range(1053,1078) for loc in LOCALES]: fail('cell coverage/order')
    mismatch=collections.Counter(); hold_cell_count=0
    selected_by_rank={r['continuationRank']:r for r in selected}
    for cell in cells:
        sel=selected_by_rank[cell['continuationRank']]; loc=cell['locale']; refs,csha=bysid[sel['sourceId']]; has=bool(refs); value=cats[loc][sel['source']]
        if cell.get('sourceId')!=sel['sourceId'] or cell.get('sourceSha256')!=tsha(sel['source']) or cell.get('sourceIdSha256')!=tsha(sel['sourceId']) or cell.get('callerContextSha256')!=csha or cell.get('callerCount')!=len(refs): fail('cell source/caller pin')
        if cell.get('catalogFileSha256')!=catpins[loc]['sha256'] or cell.get('catalogGitBlob')!=catpins[loc]['gitBlob'] or cell.get('currentTargetSha256')!=tsha(value): fail('cell current target/catalog pin')
        if cell.get('candidateFreeHold') is (has): fail('candidate-free hold flag')
        if has:
            if cell.get('source')!=sel['source'] or cell.get('currentTarget')!=value or cell.get('currentTargetTextIncluded') is not True or cell.get('sourceTextIncluded') is not True: fail('caller-backed text mismatch')
            evidence=token_data(sel['source'],value)
            if cell.get('tokenEvidence')!=evidence or cell.get('tokenEvidenceSha256')!=sha(canon(evidence)): fail('token evidence')
            if cell.get('tokenChecksPass')!=(evidence['placeholders']['matches'] and evidence['markup']['matches'] and evidence['numbers']['sourcePreserved'] and not evidence['protectedLiterals']['missing']): fail('token pass flag')
            for k,ok in [('placeholder',evidence['placeholders']['matches']),('markup',evidence['markup']['matches']),('numeric',evidence['numbers']['sourcePreserved']),('protectedLiteral',not evidence['protectedLiterals']['missing'])]:
                if not ok: mismatch[k]+=1
        else:
            hold_cell_count+=1
            if any(k in cell for k in ('source','currentTarget','tokenEvidence')) or cell.get('sourceTextIncluded') is not False or cell.get('currentTargetTextIncluded') is not False: fail('callerless source/target text exposed')
    if dict(mismatch)!=readj(P/'baseline-token-mismatch-summary.json').get('mismatchCounts'): fail('token mismatch summary')
    # Reattest all 421 active hold records hash-only, including the product-linked current catalog hash.
    old_active=readjl(PREV/'prior-held-cell-reattestation-hash-only.jsonl')+readjl(PREV/'window-holds-hash-only.jsonl')
    holds=readjl(P/'prior-held-cell-reattestation-hash-only.jsonl')
    if len(old_active)!=433 or len(holds)!=433: fail('active hold count')
    old_by={(r['sourceIdSha256'],r['locale']):r for r in old_active}
    new_by={(r['sourceIdSha256'],r['locale']):r for r in holds}
    if len(old_by)!=433 or new_by.keys()!=old_by.keys(): fail('active hold identities')
    for key,old in old_by.items():
        new=new_by[key]; sid=old.get('sourceId') or sid_by_hash.get(key[0]); source=source_by_id.get(sid)
        if source is None or tsha(source)!=old['sourceSha256'] or tsha(sid)!=key[0]: fail('active hold source binding')
        prev_target=old.get('currentTargetSha256') or old.get('priorTargetSha256'); prev_context=old.get('currentCallerContextSha256') or old.get('callerContextSha256')
        actual=tsha(cats[old['locale']][source])
        if new.get('currentTargetSha256')!=actual or actual!=prev_target or new.get('currentCallerContextSha256')!=prev_context or new.get('callerEvidenceUnchanged') is not True: fail('active hold reattestation '+sid)
        if any(k in new for k in TEXT_KEYS): fail('active hold text disclosure')
    new_holds=readjl(P/'window-holds-hash-only.jsonl')
    if len(new_holds)!=hold_cell_count or any(any(k in r for k in TEXT_KEYS) for r in new_holds): fail('new window hold count/redaction')
    if len(new_by)+len(new_holds)!=m.get('resultingActiveHashOnlyHoldCells'): fail('active hold manifest total')
    # Reattest W1028's intervening product readback from hash-only source cells.
    app_summary=json.loads((PREV_ROOT_APP/'application-summary.json').read_text(encoding='utf-8'))
    product_pin=readj(PREV_ROOT_APP/'product-pin.json')
    raw_readback=(PREV_ROOT_APP/'final-head-readback.jsonl').read_bytes(); expected_rows=[json.loads(x) for x in raw_readback.decode().splitlines() if x.strip()]
    prev_cells={(r['continuationRank'],r['locale']):r for r in readjl(PREV/'source-current-cells.jsonl')}
    if (app_summary.get('window'),app_summary.get('inputHead'),app_summary.get('inputTree'),app_summary.get('readbackCells'),app_summary.get('changedCells'),app_summary.get('activeHoldsAfter'))!=('W1028-W1052','624e27d8bb108a764df6daab5cfb1c517ebac96d','d139a16988e23046ccb09f519db2d3b7ae0b86d1',300,44,433): fail('W1028 application metadata')
    if len(expected_rows)!=300 or len(prev_cells)!=300: fail('W1028 product readback input rows')
    if (product_pin.get('productCommit'),product_pin.get('productTree'))!=(app_summary.get('productCommit'),app_summary.get('productTree')): fail('W1028 product commit/tree metadata')
    if run('rev-parse',app_summary['productCommit']+'^{tree}')!=app_summary['productTree'] or subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',app_summary['productCommit'],HEAD]).returncode: fail('W1028 product commit ancestry')
    for path,pinned in product_pin.get('catalogSha256',{}).items():
        if not path.startswith('src/web/public/locales/') or sha((REPO/path).read_bytes())!=pinned: fail('W1028 product catalog pin '+path)
    product=readjl(P/'window-product-readback-reattestation-hash-only.jsonl')
    if len(product)!=300: fail('W1028 product readback rows')
    product_by={(r['continuationRank'],r['locale']):r for r in product}
    if len(product_by)!=300: fail('W1028 product readback duplicate')
    changed=set()
    for r in expected_rows:
        rank,loc=r['continuationRank'],r['locale']; sid=r.get('sourceId') or rankrows[rank]['sourceId']; source=source_by_id.get(sid); prev=prev_cells.get((rank,loc))
        if source is None or rankrows[rank]['sourceId']!=sid or prev is None: fail('W1028 source/cell binding')
        if r['beforeSha256']!=prev['currentTargetSha256'] or r['callerless'] is not prev['candidateFreeHold'] or r['callerless']!=(prev['callerCount']==0): fail('W1028 pre-application/caller binding')
        if r['callerless'] and (r['beforeSha256']!=r['afterSha256'] or r['textIncluded'] is not False): fail('W1028 hash-only hold changed or exposed text')
        actual=tsha(cats[loc][source]); out=product_by[(rank,loc)]
        if actual!=r['afterSha256'] or out.get('productExpectedAfterSha256')!=r['afterSha256'] or out.get('currentTargetSha256')!=actual or out.get('readbackMatchesCurrent') is not True: fail('W1028 product target readback')
        if out.get('sourceIdSha256')!=tsha(sid) or out.get('sourceSha256')!=tsha(source) or out.get('productReadbackFileSha256')!=sha(raw_readback): fail('W1028 product readback source/hash')
        if any(k in out for k in TEXT_KEYS): fail('W1028 product readback text disclosure')
        if r['beforeSha256']!=r['afterSha256']: changed.add((rank,loc,tsha(sid),tsha(source),r['afterSha256']))
    if len(changed)!=44: fail('W1028 changed readback count')
    # Retain the earlier W1003 product readback attestation as historical
    # continuity, without opening any W1003 review ledger.
    w1003_sum_map={}
    for line in (ROOT_APP/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1); w1003_sum_map[n.removeprefix('./')]=h
    w1003_summary_raw=(ROOT_APP/'application-summary.json').read_bytes()
    w1003_readback_raw=(ROOT_APP/'final-head-readback.jsonl').read_bytes()
    if w1003_sum_map.get('application-summary.json')!=sha(w1003_summary_raw) or w1003_sum_map.get('final-head-readback.jsonl')!=sha(w1003_readback_raw): fail('W1003 product readback input checksum')
    w1003_summary=readj(ROOT_APP/'application-summary.json')
    w1003_rows=[json.loads(x) for x in w1003_readback_raw.decode().splitlines() if x.strip()]
    w1003_cells={(r['continuationRank'],r['locale']):r for r in readjl(W1003_INPUT/'source-current-cells.jsonl')}
    if (w1003_summary.get('inputHead'),w1003_summary.get('inputTree'),w1003_summary.get('reviewedCells'),w1003_summary.get('changedCellCount'),w1003_summary.get('callerlessHashOnlyHolds'),w1003_summary.get('resultingActiveHolds'))!=('8c752c49281418fdd96341ed46f5c321627b625f','b930b0d82679e843849e54456f3250e422c4682c',300,71,12,421) or len(w1003_rows)!=300: fail('W1003 product readback metadata')
    w1003_changed=0
    for r in w1003_rows:
        rank,loc=r['continuationRank'],r['locale']; sid=r.get('sourceId') or rankrows[rank]['sourceId']; source=source_by_id.get(sid); old=w1003_cells.get((rank,loc))
        if source is None or old is None or old['currentTargetSha256']!=r['beforeSha256'] or rankrows[rank]['sourceId']!=sid: fail('W1003 product readback source/before hash')
        if tsha(cats[loc][source])!=r['afterSha256']: fail('W1003 product readback target no longer current')
        w1003_changed+=r['beforeSha256']!=r['afterSha256']
    if w1003_changed!=71: fail('W1003 changed target readback count')
    all_readbacks=readjl(P/'window-application-readback-hash-only.jsonl')
    if len(all_readbacks)!=1200: fail('readback history rows')
    for r in all_readbacks:
        sid=sid_by_hash.get(r['sourceIdSha256']); source=source_by_id.get(sid)
        if source is None or tsha(source)!=r['sourceSha256']: fail('historical readback source')
        actual=tsha(cats[r['locale']][source])
        expected=r.get('rootExpectedAfterSha256') or r.get('productExpectedAfterSha256')
        observed=r.get('rootObservedAfterSha256') or r.get('productObservedAfterSha256')
        current=r.get('currentCatalogTargetSha256') or r.get('currentTargetSha256')
        if actual!=expected or actual!=observed or current!=actual or r.get('readbackMatchesCurrent') is not True: fail('historical readback current hash')
        if any(k in r for k in TEXT_KEYS): fail('historical readback text disclosure')
    applied=readjl(P/'prior-applied-targets-reattestation-hash-only.jsonl')
    if len(applied)!=748: fail('prior applied count')
    for r in applied:
        sid=r.get('sourceId') or sid_by_hash.get(r['sourceIdSha256']); source=source_by_id.get(sid); actual=tsha(cats[r['locale']][source]) if source else None
        if source is None or tsha(source)!=r['sourceSha256'] or actual!=r.get('appliedTargetSha256') or actual!=r.get('currentTargetSha256') or r.get('targetRemainsApplied') is not True: fail('prior applied current hash')
    product_applied=readjl(P/'window-applied-targets-reattestation-hash-only.jsonl')
    if len(product_applied)!=44: fail('W1028 changed target count')
    product_applied_set={(r['continuationRank'],r['locale'],r['sourceIdSha256'],r['sourceSha256'],r['appliedTargetSha256']) for r in product_applied}
    if product_applied_set!={(rank,loc,sidsha,sourcesha,targetsha) for rank,loc,sidsha,sourcesha,targetsha in changed}: fail('W1028 changed-target/readback identity')
    old_window_applied=readjl(PREV/'window-applied-targets-reattestation-hash-only.jsonl')
    prior_set={(r.get('continuationRank'),r['locale'],r['sourceIdSha256'],r['sourceSha256'],r['appliedTargetSha256']) for r in applied}
    if not {(r.get('continuationRank'),r['locale'],r['sourceIdSha256'],r['sourceSha256'],r['appliedTargetSha256']) for r in old_window_applied} <= prior_set: fail('previous W1003 applied targets not preserved')
    for r in product_applied:
        sid=r.get('sourceId') or sid_by_hash.get(r['sourceIdSha256']); source=source_by_id.get(sid); actual=tsha(cats[r['locale']][source]) if source else None
        if source is None or tsha(source)!=r['sourceSha256'] or actual!=r.get('appliedTargetSha256') or actual!=r.get('currentTargetSha256') or r.get('targetRemainsApplied') is not True: fail('W1003 applied current hash')
    # Check checksums and summary facts last.
    if (summary.get('cellCount'),summary.get('priorActiveHoldsReattested'),summary.get('priorAppliedTargetsReattested'),summary.get('windowAppliedTargetsReattested'),summary.get('priorWindowProductReadbackRows'),summary.get('priorApplicationReadbackHistoryRows'))!=(300,433,748,44,300,1200): fail('summary continuity counts')
    if summary.get('sourceCallerReferenceCount')!=sum(r['productionCallerCount'] for r in caller_rows) or summary.get('sourceCallerOccurrenceCount')!=sum(r['callerOccurrenceCount'] for r in caller_rows): fail('caller totals')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'sourcePositions':[START,END],'remainingQueueRanks':[953,977],
      'cells':len(cells),'callerReferences':summary['sourceCallerReferenceCount'],'callerOccurrences':summary['sourceCallerOccurrenceCount'],
      'sourcesWithCallers':summary['sourcesWithCallers'],'sourcesWithoutCallers':summary['sourcesWithoutCallers'],
      'callerBackedCells':len(cells)-hold_cell_count,'callerlessCells':hold_cell_count,
      'activeHoldsReattested':len(holds),'newHashOnlyHolds':len(new_holds),'appliedTargetRowsReattested':len(applied),
      'W1028ProductReadbacks':len(product),'allProductReadbacksMatchCurrent':True,'W1028ChangedTargets':len(product_applied),'readbackHistoryRows':len(all_readbacks),
      'priorCandidateFreeChecksumEntries':len(input_sums),'W1003CandidateFreeChecksumEntries':len(w1003_sums),'candidateFreeChecksumEntries':len(output_sums),'tokenMismatchCounts':dict(mismatch)},indent=2))
if __name__=='__main__': main()
