#!/usr/bin/env python3
"""Portable verifier for the W81 primary semantic review packet."""
import collections,hashlib,json,re,subprocess,sys,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parent
INPUT=ROOT.parent.parent/'candidate-free'/'input'
HEAD='91da6fff5d5b628ade7ee556386e3db1db6878fa'
TREE='56930b73d10a4c419edf68f0d951ceedaa63c990'
BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
TEXT_KEYS={'source','sourceText','target','currentTarget','proposedTarget','proposedTargetText','reason','resolvedTarget','resolvedTargetText','formerTargetText'}
def fail(s): raise SystemExit('FAIL: '+s)
def need(ok,s):
    if not ok: fail(s)
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def j(root,n): return json.loads((root/n).read_text(encoding='utf-8'))
def rows(root,n): return [json.loads(x) for x in (root/n).read_text(encoding='utf-8').splitlines() if x.strip()]
def ph(s): return collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s))
def tags(s): return collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',s))
def nums(s): return [''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in n) for n in re.findall(r'\d+',s)]
def prot(s):
    v=set(re.findall(r'\b[A-Z][A-Z0-9]{1,}\b',s)); v.update(x for x in ('slskdN','Tor','Wishlist','Chromaprint') if x in s); return sorted(v)
def not_less(a,b):
    x,y=collections.Counter(a),collections.Counter(b); return all(y[k]>=n for k,n in x.items())
def token_check(source,current,target=None):
    r={'sourcePlaceholderTokens':sorted(ph(source).elements()),'currentPlaceholderTokens':sorted(ph(current).elements()),
       'sourceMarkupTokens':sorted(tags(source).elements()),'currentMarkupTokens':sorted(tags(current).elements()),
       'sourceNumericTokens':nums(source),'currentNumericTokens':nums(current),'sourceProtectedLiterals':prot(source),
       'currentProtectedLiterals':[x for x in prot(source) if x in current],'placeholderParityCurrent':ph(source)==ph(current),
       'markupParityCurrent':tags(source)==tags(current),'numericTokensPreservedCurrent':not_less(nums(source),nums(current)),
       'protectedLiteralsPreservedCurrent':all(x in current for x in prot(source))}
    if target is not None:
        r['proposal']={'placeholderTokens':sorted(ph(target).elements()),'markupTokens':sorted(tags(target).elements()),'numericTokens':nums(target),
          'protectedLiterals':prot(target),'placeholderParity':ph(source)==ph(target),'markupParity':tags(source)==tags(target),
          'numericTokensPreserved':not_less(nums(source),nums(target)),'protectedLiteralsPreserved':all(x in target for x in prot(source))}
    return r
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def verify_packet_inventory():
    m=j(ROOT,'manifest.json'); expected={x['path'] for x in m['files']}; need(len(expected)==len(m['files']),'duplicate packet files')
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name not in {'manifest.json','SHA256SUMS.txt'} and '__pycache__' not in p.parts}
    need(actual==expected,'packet inventory')
    for x in m['files']:
        p=(ROOT/x['path']).resolve(); need(p.is_relative_to(ROOT.resolve()) and p.is_file(),'unsafe or missing packet file')
        b=p.read_bytes(); need(len(b)==x['bytes'] and sha(b)==x['sha256'],'packet file hash '+x['path'])
    checks={}
    for line in (ROOT/'SHA256SUMS.txt').read_text().splitlines():
        if not line.strip(): continue
        d,n=line.split('  ',1); need(n not in checks,'duplicate checksum')
        p=(ROOT/n).resolve(); need(p.is_relative_to(ROOT.resolve()) and p.is_file() and sha(p.read_bytes())==d,'checksum '+n); checks[n]=d
    need(set(checks)==expected|{'manifest.json'},'checksum inventory')
    need((m.get('artifact'),m.get('window'),m.get('head'),m.get('tree'),m.get('sourceCount'),m.get('localeCount'),m.get('cellCount'),m.get('proposalCount'),m.get('holdCount'))==
      ('slskdN PR #409 W81 independent primary semantic review','W81',HEAD,TREE,25,12,300,43,12),'manifest identity')
    need(m.get('blindReviewUsed') is False and m.get('crossReviewUsed') is False and m.get('nativeSpeakerSignoff') is False and m.get('browserReview') is False and m.get('prBodyQueried') is False,'scope flags')
    return m,len(checks)
def verify_live(repo,m):
    before,after=j(ROOT,'live-before.json'),j(ROOT,'live-after.json'); att=j(ROOT,'head-tree-attestation.json')
    need(att.get('liveBefore')==before and att.get('liveAfter')==after,'live attestation linkage')
    stable=('repository','pullRequest','state','draft','merged','headRefName','headRefOid','branchRefOid','pullRefOid','baseRefName','baseRefOid','liveMainSha','commitTree')
    for s in (before,after):
        need(s.get('prBodyQueried') is False and not any('body' in k.lower() for k in s if k!='prBodyQueried'),'PR body not accessed')
        need((s.get('repository'),s.get('pullRequest'),s.get('state'),s.get('draft'),s.get('merged'),s.get('headRefName'),s.get('headRefOid'),s.get('branchRefOid'),s.get('pullRefOid'),s.get('baseRefName'),s.get('baseRefOid'),s.get('commitTree'))==
          ('snapetech-org/slskdN',409,'OPEN',True,False,BRANCH,HEAD,HEAD,HEAD,'main','f25d263a2a7cdb2c8f76c40c346cb10f749a9356',TREE),'live PR snapshot')
    need(all(before.get(k)==after.get(k) for k in stable),'live refs stable')
    need(git(repo,'rev-parse','HEAD')==HEAD and git(repo,'rev-parse','HEAD^{tree}')==TREE and not git(repo,'status','--porcelain=v1'),'pinned clean worktree')
    api=json.loads(subprocess.check_output(['gh','api','repos/snapetech-org/slskdN/pulls/409','--jq','{state:.state,draft:.draft,merged:(.merged_at!=null),headRefName:.head.ref,headRefOid:.head.sha,baseRefName:.base.ref,baseRefOid:.base.sha}']))
    ref=json.loads(subprocess.check_output(['gh','api',f'repos/snapetech-org/slskdN/git/ref/heads/{BRANCH}','--jq','{oid:.object.sha}']))
    tree=json.loads(subprocess.check_output(['gh','api',f'repos/snapetech-org/slskdN/commits/{HEAD}','--jq','{sha:.sha,tree:.commit.tree.sha}']))
    main=subprocess.check_output(['gh','api','repos/snapetech-org/slskdN/commits/main','--jq','.sha'],text=True).strip()
    need((api['state'],api['draft'],api['merged'],api['headRefName'],api['headRefOid'],api['baseRefName'],api['baseRefOid'])==('open',True,False,BRANCH,HEAD,'main','f25d263a2a7cdb2c8f76c40c346cb10f749a9356'),'live PR API')
    need(ref['oid']==HEAD and tree=={'sha':HEAD,'tree':TREE} and main==after['liveMainSha'],'live branch/main API')
    remote=subprocess.check_output(['git','ls-remote',f'https://github.com/snapetech-org/slskdN.git',f'refs/heads/{BRANCH}','refs/pull/409/head'],text=True)
    refs={x.split()[1]:x.split()[0] for x in remote.splitlines() if x.strip()}
    need(refs.get(f'refs/heads/{BRANCH}')==HEAD and refs.get('refs/pull/409/head')==HEAD,'remote branch/pull refs')
    drift=j(INPUT,'main-drift.json'); out=j(ROOT,'main-drift.json')
    need((out['baseApiSha'],out['liveMainBeforeSha'],out['liveMainAfterSha'],out['localizationOrCatalogChanges'])==(drift['baseApiSha'],drift['liveMainBeforeSha'],drift['liveMainAfterSha'],False),'main drift reattestation')
    need(not any(p.startswith('src/web/public/locales/') or p.startswith('src/web/src/') or p.endswith('source-inventory.jsonl') for p in out['changedPaths']),'main drift source overlap')
    need(m['liveBefore']==before and m['liveAfter']==after,'manifest live snapshots')
def verify_supplemental(repo):
    s=j(ROOT,'supplemental-context.json'); need((s['head'],s['tree'])==(HEAD,TREE),'supplemental identity')
    invpath=s['sourceInventoryPath']; raw=subprocess.check_output(['git','-C',str(repo),'show',f'{HEAD}:{invpath}'])
    need(sha(raw)==s['sourceInventorySha256']==j(INPUT,'manifest.json')['sourceInventorySha256'],'supplement source inventory pin')
    inv={x['source']:x for x in (json.loads(z) for z in raw.decode().splitlines() if z.strip())}
    expected={'format over the canonical join/leave payload and the supplied public key.':(185,True),
              'file':(1104,True),'directory':(884,True),'Enter true fullscreen.':(1999,True)}
    need(len(s['relatedFragments'])==4,'supplemental fragment count')
    catalogs={x['locale']:x for x in rows(INPUT,'catalog-structure.jsonl')}
    for r in s['relatedFragments']:
        rec=inv[r['source']]; rank,outside=expected[r['source']]
        need((r['sourceId'],r['sourceSha256'],r['continuationRank'],r['outsideCurrentWindow'])==(rec['sourceId'],rec['sourceSha256'],rank,outside),'supplemental source binding')
        need(set(r['localeTargets'])==set(LOCALES),'supplement locale coverage')
        for loc,t in r['localeTargets'].items():
            catalog=json.loads((repo/f'src/web/public/locales/{loc}.json').read_text())
            need(t['text']==catalog[r['source']] and t['sha256']==sha(t['text'].encode()),'supplement target '+r['source']+'/'+loc)
    need(len(s['callerFilePins'])==3,'supplement caller files')
    for pin in s['callerFilePins']:
        data=(repo/pin['path']).read_bytes(); lines=data.decode().splitlines()
        need(sha(data)==pin['fileSha256'] and blob(data)==pin['gitBlob'],'supplement caller file pin')
        need(pin['lineEnd']-pin['lineStart']+1==len(pin['lines']),'supplement line range')
        for x in pin['lines']: need(lines[x['line']-1]==x['text'] and sha(x['text'].encode())==x['sha256'],'supplement caller line')
    need(len(s['catalogFilePins'])==12,'supplement catalog pins')
    for x in s['catalogFilePins']:
        data=(repo/x['path']).read_bytes(); c=catalogs[x['locale']]
        need(x['path']==c['catalogPath'] and sha(data)==x['sha256']==c['sha256'] and blob(data)==x['gitBlob']==c['gitBlob'],'supplement catalog pin')
    return 4,3

def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True); repo=Path(ap.parse_args().repo).resolve()
    m,checks=verify_packet_inventory()
    cf=json.loads(subprocess.check_output(['python3',str(INPUT/'verify_candidate_free.py'),'--repo',str(repo)],text=True))
    need(cf['result']=='PASS' and cf['head']==HEAD and cf['tree']==TREE and cf['cells']==300,'candidate-free verifier')
    need(m['candidateFreeInputManifestSha256']==sha((INPUT/'manifest.json').read_bytes()) and m['candidateFreeInputChecksumListSha256']==sha((INPUT/'PACKET-SHA256SUMS.txt').read_bytes()),'candidate-free packet link')
    for field,name in [('sourceInventorySelectionSha256','source-inventory-selection.jsonl'),('callerContextSha256','caller-contexts.jsonl'),('sourceCurrentCellsSha256','source-current-cells.jsonl'),('selectionBoundarySha256','selection-boundary.jsonl')]:
        need(m[field]==sha((INPUT/name).read_bytes()),'candidate-free link '+name)
    verify_live(repo,m); supplement_count,caller_count=verify_supplemental(repo)
    inp=rows(INPUT,'source-current-cells.jsonl'); callers={x['sourceId']:x for x in rows(INPUT,'caller-contexts.jsonl')}
    ledger=rows(ROOT,'primary-review.jsonl'); corrections=rows(ROOT,'corrections.jsonl'); holds=rows(ROOT,'review-holds.jsonl'); hash_holds=rows(ROOT,'holds-hash-only.jsonl')
    need((len(inp),len(callers),len(ledger),len(corrections),len(holds),len(hash_holds))==(300,25,300,43,12,0),'review coverage')
    need([(x['continuationRank'],x['locale']) for x in ledger]==[(x['continuationRank'],x['locale']) for x in inp],'review order/coverage')
    corr={(x['continuationRank'],x['locale']):x for x in corrections}; held={(x['continuationRank'],x['locale']):x for x in holds}
    need(len(corr)==43 and len(held)==12 and set(held)=={(910,l) for l in LOCALES},'proposal/hold coverage')
    counts=collections.Counter(x['disposition'] for x in ledger)
    for source,row in zip(inp,ledger):
        k=(source['continuationRank'],source['locale']); caller=callers[source['sourceId']]
        for f in ('continuationRank','remainingQueueRank','sourceId','sourceSha256','locale','catalogPath','catalogFileSha256','catalogGitBlob','currentTargetSha256','callerContextSha256','callerRefs'):
            need(row.get(f)==source.get(f),f'input binding {k}/{f}')
        need(row['productionCallerCount']==caller['productionCallerCount'] and caller['productionCallerCount']>0,'caller binding')
        need(row['source']==source['source'] and row['catalogKey']==source['catalogKey'] and row['currentTarget']==source['currentTarget'],'visible text binding')
        need(row['sourceTextIncluded'] is True and row['currentTargetTextIncluded'] is True,'text flags')
        disposition=row['disposition']; target=row.get('target') if disposition=='correct' else None
        need(row['tokenCheck']==token_check(source['source'],source['currentTarget'],target),'token evidence '+str(k))
        need(disposition in {'accept-current','correct','hold'} and row.get('rationale'),'decision/rationale '+str(k))
        if disposition=='correct':
            need(k in corr and corr[k]==row,'correction ledger match')
            need(row['targetSha256']==sha(row['target'].encode()),'target hash')
            check=token_check(source['source'],source['currentTarget'],row['target'])['proposal']
            need(row['proposalTokenCheck']==check,'proposal token record')
            need(check['placeholderParity'] and check['markupParity'] and check['numericTokensPreserved'] and check['protectedLiteralsPreserved'],'proposal token safety')
        elif disposition=='hold':
            need(k in held and held[k]==row and row['holdReasonCode']=='SOURCE_FRAGMENT_ORDER_DEPENDENCY','held row')
            need(row['sourceRewriteRecommendation']=='SR-910-01','hold recommendation link')
            need(not any(f in row for f in ('target','targetSha256','proposedTarget')),'held row target leakage')
        else: need(k not in corr and k not in held and not any(f in row for f in ('target','targetSha256','proposedTarget')),'accept-current leakage')
    need(dict(counts)=={'accept-current':245,'correct':43,'hold':12},'decision totals')
    need(j(ROOT,'proposal-map.json')=={f"{r['continuationRank']}|{r['locale']}":r['target'] for r in corrections},'proposal map')
    recs=j(ROOT,'source-rewrite-recommendations.json')['recommendations']; need(len(recs)==1 and recs[0]['recommendationId']=='SR-910-01' and recs[0]['implemented'] is False,'source rewrite recommendation')
    summary=j(ROOT,'summary.json')
    need(summary['dispositions']==dict(counts) and summary['proposedTargetCount']==43 and summary['reviewHoldCount']==12 and summary['hashOnlyHoldCount']==0,'summary counts')
    need((summary['priorSelectedIdsExcluded'],summary['priorHeldCellsCarried'],summary['priorHoldResolutionHistoryRows'],summary['priorAppliedTargetsReattested'],summary['w80AppliedTargets'])==(1982,382,13,190,81),'lineage summary')
    need(summary['priorHeldTargetsAllMatch'] is True and summary['priorHeldCallerEvidenceUnchanged']==382,'prior hold reattestation')
    print(json.dumps({'result':'PASS','window':'W81','head':HEAD,'tree':TREE,'cells':300,'decisions':dict(counts),'proposals':43,
      'reviewHolds':12,'hashOnlyHolds':0,'priorSelectedIds':1982,'priorHeldCells':382,'holdResolutionHistory':13,'appliedTargets':190,
      'supplementalFragments':supplement_count,'pinnedCallerFiles':caller_count,'candidateFreeVerifier':'PASS','liveRefs':'PASS','packetChecksums':checks,
      'blindReviewUsed':False,'crossReviewUsed':False,'nativeSpeakerSignoff':False,'browserReview':False,'prBodyQueried':False},indent=2))
if __name__=='__main__': main()
