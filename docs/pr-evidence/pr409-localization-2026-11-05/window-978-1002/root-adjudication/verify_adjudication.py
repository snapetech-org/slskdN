#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, hashlib, json, re, sys, unicodedata
from pathlib import Path
EXPECTED_HEAD='1c2fe3be2c720693cbcb12d377bf1177804f4e77'
EXPECTED_TREE='808501cbc3b6ed873a47d7188189d486f0673f5e'
DEFAULT_INPUT='/mnt/disks/scratch/task-scratch/slskdn-pr409-w978-1002-20261105-cross-review-independent/cross-review-ledger.jsonl'
def sha(b): return hashlib.sha256(b).hexdigest()
def readjl(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def need(ok,msg):
    if not ok: raise SystemExit('FAIL: '+msg)
def token_checks(source,target):
    placeholders=lambda s:sorted(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s))
    tags=lambda s:sorted(re.findall(r'</?[A-Za-z][^>]*>',s))
    nums=lambda s:[''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in t) for t in re.findall(r'\d+',s)]
    protected=lambda s:sorted(set(re.findall(r'\b[A-Z][A-Z0-9]{1,}\b',s))|{x for x in ('slskdN','PodCore','Wishlist','soulfind','FFmpeg','Lidarr') if x in s})
    sp,tp=placeholders(source),placeholders(target); st,tt=tags(source),tags(target); sn,tn=nums(source),nums(target); sl=protected(source)
    return {'placeholders':{'source':sp,'target':tp,'matches':sp==tp},'markup':{'source':st,'target':tt,'matches':st==tt},'numbers':{'source':sn,'target':tn,'sourcePreserved':all(tn.count(x)>=n for x,n in collections.Counter(sn).items())},'protectedLiterals':{'source':sl,'target':protected(target),'missing':[x for x in sl if x not in target],'matches':all(x in target for x in sl)}}
def verify_packet(packet):
    sums=packet/'SHA256SUMS.txt'
    if not sums.exists(): return
    seen={}
    for line in sums.read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1); need(n not in seen and sha((packet/n).read_bytes())==h,'packet checksum '+n); seen[n]=h
    actual={p.relative_to(packet).as_posix() for p in packet.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    need(actual==set(seen),'packet checksum inventory')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input-ledger',type=Path,default=Path(DEFAULT_INPUT)); ap.add_argument('--packet-dir',type=Path,default=Path(__file__).resolve().parent); a=ap.parse_args()
    packet=a.packet_dir.resolve(); verify_packet(packet)
    source_path=a.input_ledger.resolve(); source=readjl(source_path); by={(r['continuationRank'],r['locale']):r for r in source if r['flagForRootAdjudication']}
    recs=readjl(packet/'root-adjudication-opinion.jsonl')
    need(len(by)==len(recs)==64,'64 flagged rows')
    keys=[(r['continuationRank'],r['locale']) for r in recs]
    need(keys==sorted(by),'flagged row order/identity')
    counts=collections.Counter(); bases=collections.Counter(); literal=[]
    for r in recs:
        k=(r['continuationRank'],r['locale']); s=by[k]
        need((r['exactHead'],r['exactTree'])==(EXPECTED_HEAD,EXPECTED_TREE),'head/tree '+str(k))
        for f in ('sourceId','sourceIdSha256','source','sourceSha256','currentTarget','currentTargetSha256','catalogPath','catalogGitBlob','catalogFileSha256','callerCount','callerContextSha256','callerBindings','primaryDisposition','primaryTarget','primaryRationale','blindDisposition','blindTarget','blindRationale','targetAgreement','baselineProtectedLiteralMismatch'):
            need(r[f]==s[f],f+' source binding '+str(k))
        need(r['recommendedDisposition'] in {'correction','accept-current','hold'},'disposition '+str(k))
        need(sha(r['recommendedTarget'].encode('utf-8'))==r['recommendedTargetSha256'],'target SHA '+str(k))
        checks=token_checks(r['source'],r['recommendedTarget'])
        need(checks==r['recommendedTokenChecks'],'token checks '+str(k))
        need(checks['placeholders']['matches'] and checks['markup']['matches'] and checks['numbers']['sourcePreserved'] and checks['protectedLiterals']['matches'],'token preservation '+str(k))
        need(r['localeSpecificRationale'] and r['confidence'] in {'high','moderate','low'},'rationale/confidence '+str(k))
        if r['selectionBasis']=='primary proposal': need(r['recommendedTarget']==s['primaryTarget'],'primary selection '+str(k))
        if r['selectionBasis']=='blind proposal': need(r['recommendedTarget']==s['blindTarget'],'blind selection '+str(k))
        if r['selectionBasis']=='primary/blind agreement': need(r['recommendedTarget']==s['primaryTarget']==s['blindTarget'],'agreement selection '+str(k))
        need(r['rootAdjudicationPerformed'] is False and r['status']=='advisory-opinion-for-root-final-selection','advisory boundary '+str(k))
        counts[r['recommendedDisposition']]+=1; bases[r['selectionBasis']]+=1
        if s['baselineProtectedLiteralMismatch']: literal.append(r)
    need(dict(counts)=={'correction':64},'recommendation totals')
    need(len(literal)==5,'protected-literal case count')
    expected={(991,'ar'):{'ID'},(991,'hi'):{'ID'},(999,'ar'):{'CPU','MP3'},(999,'fr'):{'CPU','MP3'},(1001,'zh-Hans'):{'QR'}}
    actual={(r['continuationRank'],r['locale']):set(r['recommendedTokenChecks']['protectedLiterals']['source']) for r in literal}
    need(actual==expected,'protected-literal inventory')
    print(json.dumps({'result':'PASS','verifier':'root-adjudication-opinion','head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'flaggedRows':len(recs),'recommendations':dict(counts),'selectionBasis':dict(bases),'protectedLiteralCases':len(literal),'upstreamCrossReviewLedgerSha256':sha(source_path.read_bytes())},ensure_ascii=False,indent=2))
if __name__=='__main__':
    try: main()
    except Exception as e: print('FAIL: '+str(e),file=sys.stderr); raise
