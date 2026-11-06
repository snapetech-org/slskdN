#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, re, unicodedata
from pathlib import Path

P=Path(__file__).resolve().parent
INPUT=P.parent/'candidate-free'
HEAD='ba692c15ca54942108cc9da37757f585969e6173'; TREE='27c09a8fe24030f5bb0995d809794a9e4829dc64'
INPUT_SUMS_SHA='2170ea00e2bcb8c5c79f23f86ce5acef8a31f4270813e222fea7e2f171cec1be'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
TEXT_KEYS={'source','sourceText','target','currentTarget','proposedTarget','proposedTargetText','candidateTarget','reviewTarget','before','after','actualValue','expectedValue'}
SPECIAL=['FPS','FTP','IP','Mesh','Soulseek','YAML','NzbGet','KeepHistory','PodCore','slskdN']

def fail(s): raise SystemExit('FAIL: '+s)
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def readjl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def verify_dir(p):
    listed={}
    for line in (p/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1)
        if n in listed or not (p/n).is_file() or sha((p/n).read_bytes())!=h: fail('checksum '+n)
        listed[n]=h
    actual={x.relative_to(p).as_posix() for x in p.rglob('*') if x.is_file() and x.name!='SHA256SUMS.txt'}
    if actual!=set(listed): fail('checksum inventory '+str(p))
    return listed
def token_audit(source,target):
    ph=lambda s:collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s))
    tags=lambda s:collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',s))
    nums=lambda s:[''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in t) for t in re.findall(r'\d+',s)]
    protected=lambda s:sorted(set(re.findall(r'\b[A-Z][A-Z0-9]{1,}\b',s))|{x for x in ('slskdN','PodCore','Wishlist','soulfind','FFmpeg','Lidarr') if x in s})
    sp,tp=ph(source),ph(target); st,tt=tags(source),tags(target); sn,tn=nums(source),nums(target)
    sl,tl=protected(source),protected(target); explicit=[x for x in SPECIAL if x in source]
    if '#' in source: explicit.append('#')
    extensions=[x for x in ('flac','mp3','wav','m4a') if re.search(r'\b'+x+r'\b',source)]
    explicit=list(dict.fromkeys(explicit+extensions))
    return {'placeholders':{'source':sorted(sp.elements()),'target':sorted(tp.elements()),'matches':sp==tp},
      'markup':{'source':sorted(st.elements()),'target':sorted(tt.elements()),'matches':st==tt},
      'numbers':{'source':sn,'target':tn,'sourcePreserved':all(tn.count(x)>=n for x,n in collections.Counter(sn).items())},
      'protectedLiterals':{'source':sl,'target':tl,'missing':[x for x in sl if x not in target]},
      'explicitDomainLiterals':{'source':explicit,'missing':[x for x in explicit if x not in target]}}

def main():
    ins=verify_dir(INPUT); outs=verify_dir(P)
    if sha((INPUT/'SHA256SUMS.txt').read_bytes())!=INPUT_SUMS_SHA: fail('candidate-free checksum-list pin')
    im=readj(INPUT/'manifest.json')
    if (im.get('head'),im.get('tree'),im.get('window'),im.get('continuationRankRange'),im.get('remainingQueueRankRange'),im.get('cellCount'),im.get('candidateFree'),im.get('reviewDecisionsIncluded'),im.get('proposedTargetsIncluded'))!=(HEAD,TREE,'W87',[1053,1077],[953,977],300,True,False,False): fail('candidate-free input pin')
    m=readj(P/'manifest.json'); s=readj(P/'summary.json')
    if (m.get('head'),m.get('tree'),m.get('window'),m.get('continuationRankRange'),m.get('remainingQueueRankRange'),m.get('role'))!=(HEAD,TREE,'W87',[1053,1077],[953,977],'primary-semantic-review'): fail('review manifest pin')
    declared={r['path']:r['sha256'] for r in m['files']}
    actual={x.relative_to(P).as_posix():sha(x.read_bytes()) for x in P.rglob('*') if x.is_file() and x.name not in ('SHA256SUMS.txt','manifest.json')}
    if declared!=actual: fail('manifest file hashes')
    cells=readjl(INPUT/'source-current-cells.jsonl'); callers=readjl(INPUT/'caller-contexts.jsonl'); callmap={r['sourceId']:r for r in callers}
    ledger=readjl(P/'primary-review-ledger.jsonl')
    if len(cells)!=300 or len(ledger)!=300 or len(callmap)!=25: fail('cell/caller coverage')
    counts=collections.Counter(); hold_ids=[]
    for inp,out in zip(cells,ledger):
        key=['continuationRank','remainingQueueRank','sourceId','sourceIdSha256','sourceSha256','locale']
        if any(inp[k]!=out.get(k) for k in key) or (out.get('head'),out.get('tree'))!=(HEAD,TREE): fail('cell identity/pin')
        call=callmap[inp['sourceId']]; backed=call['productionCallerCount']>0
        if out.get('callerBacked') is not backed or out.get('callerCount')!=call['productionCallerCount'] or out.get('callerContextSha256')!=call['callerContextSha256']: fail('caller evidence pin')
        if inp.get('currentTargetSha256')!=out.get('currentTargetSha256'): fail('current target hash pin')
        if not backed:
            if out.get('decision')!='hold-hash-only' or out.get('proposalIncluded') is not False or out.get('proposedTargetSha256') is not None: fail('callerless disposition')
            if any(k in out for k in ('source','currentTarget','proposedTarget','tokenAudit')): fail('callerless text disclosed')
            if out.get('sourceTextIncluded') is not False or out.get('currentTargetTextIncluded') is not False: fail('callerless text flags')
            if 'currentTarget' in inp or 'source' in inp: fail('input callerless cell not text-free')
            hold_ids.append((inp['sourceIdSha256'],inp['locale'])); counts['hold']+=1
            continue
        if out.get('source')!=inp.get('source') or out.get('currentTarget')!=inp.get('currentTarget'): fail('caller-backed input text mismatch')
        if inp.get('callerContextSha256')!=out.get('callerContextSha256'): fail('caller context mismatch')
        target=out.get('proposedTarget')
        if not isinstance(target,str) or not target or out.get('proposalIncluded') is not True or tsha(target)!=out.get('proposedTargetSha256'): fail('proposal text/hash')
        audit=token_audit(inp['source'],target)
        if audit!=out.get('tokenAudit') or sha(canon(audit))!=out.get('tokenAuditSha256'): fail('token audit mismatch')
        if not audit['placeholders']['matches'] or not audit['markup']['matches'] or not audit['numbers']['sourcePreserved'] or audit['protectedLiterals']['missing'] or audit['explicitDomainLiterals']['missing'] or out.get('tokenChecksPass') is not True: fail('token preservation')
        if out.get('decision')=='retain-current':
            if target!=inp['currentTarget'] or out.get('proposedTargetSha256')!=inp['currentTargetSha256']: fail('retain-current mismatch')
            counts['retain-current']+=1
        elif out.get('decision')=='revise':
            if target==inp['currentTarget']: fail('revise does not change target')
            counts['revise']+=1
        else: fail('unknown caller-backed disposition')
        if out.get('confidence') not in ('moderate','low'): fail('confidence label')
        counts['proposal']+=1
    prior=readjl(INPUT/'prior-held-cell-reattestation-hash-only.jsonl'); current=readjl(INPUT/'window-holds-hash-only.jsonl')
    prior_out=readjl(P/'prior-active-holds-hash-only.jsonl'); current_out=readjl(P/'current-window-holds-hash-only.jsonl')
    if len(prior)!=433 or prior_out!=prior or len(current)!=24 or current_out!=current: fail('hold continuity mismatch')
    if any(any(k in r for k in TEXT_KEYS) for r in prior_out+current_out): fail('hold continuity text disclosure')
    if len(set(hold_ids))!=24 or {tuple(x) for x in hold_ids}!={(r['sourceIdSha256'],r['locale']) for r in current}: fail('callerless cell hold identity')
    boundary=readj(INPUT/'selection-and-boundary.json')['nextUnselected']
    if s.get('nextBoundary')!=boundary: fail('next boundary')
    if (s.get('cellCount'),s.get('proposalCells'),s.get('revisedCells'),s.get('retainedCurrentCells'),s.get('hashOnlyHolds'),s.get('priorActiveHashOnlyHoldsReattested'),s.get('resultingActiveHashOnlyHolds'))!=(300,276,counts['revise'],counts['retain-current'],24,433,457): fail('summary counts')
    att=readj(P/'input-attestation.json')
    if att.get('candidateFreeChecksumListSha256')!=INPUT_SUMS_SHA or (att.get('head'),att.get('tree'))!=(HEAD,TREE): fail('input attestation')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'cells':len(ledger),'proposalCells':counts['proposal'],
      'revisedCells':counts['revise'],'retainedCurrentCells':counts['retain-current'],'hashOnlyHolds':counts['hold'],
      'priorActiveHoldsReattested':len(prior_out),'resultingActiveHashOnlyHolds':len(prior_out)+len(current_out),
      'nextBoundary':boundary,'inputChecksumEntries':len(ins),'outputChecksumEntries':len(outs),
      'outputChecksumListSha256':sha((P/'SHA256SUMS.txt').read_bytes())},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
