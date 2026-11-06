#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, hashlib, json, re, subprocess, sys, unicodedata
from pathlib import Path
EXPECTED_HEAD='1c2fe3be2c720693cbcb12d377bf1177804f4e77'
EXPECTED_TREE='808501cbc3b6ed873a47d7188189d486f0673f5e'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
def sha(b): return hashlib.sha256(b).hexdigest()
def textsha(s): return sha(s.encode('utf-8'))
def need(ok,msg):
    if not ok: raise SystemExit('FAIL: '+msg)
def readj(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def readjl(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def verify_sums(root):
    seen={}
    for line in (root/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1); need(n not in seen and sha((root/n).read_bytes())==h,'checksum '+n); seen[n]=h
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    need(actual==set(seen),'checksum inventory'); return seen
def token_checks(source,target):
    placeholders=lambda s:sorted(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s))
    tags=lambda s:sorted(re.findall(r'</?[A-Za-z][^>]*>',s))
    nums=lambda s:[''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in t) for t in re.findall(r'\d+',s)]
    protected=lambda s:sorted(set(re.findall(r'\b[A-Z][A-Z0-9]{1,}\b',s))|{x for x in ('slskdN','PodCore','Wishlist','soulfind','FFmpeg','Lidarr') if x in s})
    sp,tp=placeholders(source),placeholders(target); st,tt=tags(source),tags(target); sn,tn=nums(source),nums(target); sl=protected(source); tl=protected(target)
    return {'placeholders':{'source':sp,'target':tp,'matches':sp==tp},'markup':{'source':st,'target':tt,'matches':st==tt},
      'numbers':{'source':sn,'target':tn,'sourcePreserved':all(tn.count(x)>=n for x,n in collections.Counter(sn).items())},
      'protectedLiterals':{'source':sl,'target':tl,'missing':[x for x in sl if x not in target],'matches':all(x in target for x in sl)}}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input-dir',required=True,type=Path); ap.add_argument('--primary-dir',required=True,type=Path); ap.add_argument('--blind-dir',required=True,type=Path); ap.add_argument('--repo-dir',type=Path); args=ap.parse_args()
    packet=Path(__file__).resolve().parent; verify_sums(packet)
    att=readj(packet/'input-attestation.json'); need((att['head'],att['tree'])==(EXPECTED_HEAD,EXPECTED_TREE),'attestation identity')
    for name,root in [('candidate-free',args.input_dir.resolve()),('primary-review',args.primary_dir.resolve()),('blind-review',args.blind_dir.resolve())]:
        recorded=att['inputs'][name]; need(Path(recorded['path']).resolve()==root,'input path '+name)
        actual={p.relative_to(root).as_posix():sha(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}
        need(actual==recorded['files'],'input packet file hashes '+name)
    cf=args.input_dir.resolve(); pr=args.primary_dir.resolve(); br=args.blind_dir.resolve()
    cm=readj(cf/'manifest.json'); pm=readj(pr/'manifest.json'); ba=readj(br/'review-attestation.json')
    need((cm['head'],cm['tree'])==(EXPECTED_HEAD,EXPECTED_TREE),'candidate-free pin')
    need((pm['head'],pm['tree'])==(EXPECTED_HEAD,EXPECTED_TREE),'primary pin')
    need((ba['exactHead'],ba['exactTree'])==(EXPECTED_HEAD,EXPECTED_TREE),'blind pin')
    cells=readjl(cf/'source-current-cells.jsonl'); sources=readjl(cf/'selected-sources.jsonl'); callers=readjl(cf/'caller-contexts.jsonl')
    primary=readjl(pr/'primary-review.jsonl'); blind=readjl(br/'review-decisions.jsonl'); rows=readjl(packet/'cross-review-ledger.jsonl')
    need(len(cells)==len(primary)==len(blind)==len(rows)==300 and len(sources)==len(callers)==25,'matrix counts')
    cby={(r['continuationRank'],r['locale']):r for r in cells}; pby={(r['continuationRank'],r['locale']):r for r in primary}; bby={(r['continuationRank'],r['locale']):r for r in blind}
    sby={r['sourceId']:r for r in sources}; aby={r['sourceId']:r for r in callers}
    need(len(cby)==len(pby)==len(bby)==300,'duplicate input cells')
    locales=cm['locales']; need(locales==LOCALES,'locale order')
    need([(r['continuationRank'],r['locale']) for r in rows]==[(n,l) for n in range(978,1003) for l in LOCALES],'ledger ordering')
    counts=collections.Counter(); agreements=collections.Counter(); flags=0; mismatches=0
    for r in rows:
        k=(r['continuationRank'],r['locale']); c=cby[k]; p=pby[k]; b=bby[k]; sid=c['sourceId']; src=sby[sid]['source']; caller=aby[sid]
        need((r['exactHead'],r['exactTree'])==(EXPECTED_HEAD,EXPECTED_TREE),'ledger head/tree')
        for f in ('continuationRank','remainingQueueRank','locale','sourceId','sourceIdSha256','sourceSha256','currentTarget','currentTargetSha256','catalogPath','catalogGitBlob','catalogFileSha256','callerCount','callerContextSha256'):
            need(r[f]==c[f],f+' candidate-free binding')
        need(r['source']==src and textsha(r['source'])==r['sourceSha256'],'source text/hash')
        need(textsha(r['sourceId'])==r['sourceIdSha256'],'source ID hash')
        need(textsha(r['currentTarget'])==r['currentTargetSha256'],'current target hash')
        refs=[]
        for ref in caller['callers']:
            refs.append({x:ref[x] for x in ('path','line','lineText','lineSha256','fileBytes','fileSha256','gitBlob','contextSha256','context')})
        need(r['callerBindings']==refs and r['callerCount']==len(refs),'exact caller refs')
        need(r['primaryDisposition']==p['disposition'] and r['primaryTarget']==p['candidateTarget'] and r['primaryTargetSha256']==p['candidateTargetSha256'],'primary row binding')
        need(r['primaryRationale']==p['rationale'] and r['primaryConfidence']==p['confidence'],'primary rationale binding')
        need(r['blindDisposition']==b['disposition'] and r['blindTarget']==b.get('proposedTarget') and r['blindTargetSha256']==(b.get('finalTargetSha256') if b['disposition']=='propose' else None) and r['blindRationale']==b.get('rationale'),'blind row binding')
        if r['blindTarget'] is not None: need(textsha(r['blindTarget'])==r['blindTargetSha256'],'blind target hash')
        pt=p['candidateTarget'] if p['disposition']=='correction' else None; bt=b.get('proposedTarget') if b['disposition']=='propose' else None
        expected='exact-agreement' if pt and bt and pt==bt else ('conflicting-targets' if pt and bt else 'primary-only' if pt else 'blind-only' if bt else 'both-keep')
        need(r['targetAgreement']==expected,'target agreement '+str(k))
        source_text=r['recommendedTarget']; need(textsha(source_text)==r['recommendedTargetSha256'],'recommended target hash')
        if r['independentDisposition']=='accept-current': need(source_text==c['currentTarget'] and r['targetSelection']=='current','accept-current target')
        else:
            need(r['independentDisposition']=='correction' and source_text!=c['currentTarget'],'correction target')
            need(source_text in {pt,bt} or r['targetSelection']=='independent','recommended candidate selection')
        need(r['independentRationale'] and r['independentConfidence'] in {'high','moderate','low'},'independent rationale/confidence')
        checks=token_checks(src,source_text); need(r['independentTokenChecks']==checks,'recommended token evidence')
        need(checks['placeholders']['matches'] and checks['markup']['matches'] and checks['numbers']['sourcePreserved'] and checks['protectedLiterals']['matches'],'recommended token preservation')
        mismatch=bool(c['tokenEvidence']['protectedLiterals']['missing']); need(r['baselineProtectedLiteralMismatch']==mismatch,'baseline protected mismatch')
        need(r['baselineTokenEvidence']==c['tokenEvidence'],'baseline token evidence')
        disagree=expected in {'primary-only','blind-only','conflicting-targets'}; need(r['reviewDisagreement']==disagree,'disagreement flag')
        rootflag=disagree or mismatch or r['targetSelection']=='independent'; need(r['flagForRootAdjudication']==rootflag,'root flag')
        need(r['rootAdjudicationPerformed'] is False,'root stage boundary')
        counts[r['independentDisposition']]+=1; agreements[expected]+=1; flags+=rootflag; mismatches+=mismatch
    need(dict(agreements)=={'both-keep':211,'exact-agreement':28,'conflicting-targets':32,'primary-only':29},'proposal comparison totals')
    need(dict(counts)=={'accept-current':211,'correction':89},'independent totals')
    need(flags==readj(packet/'cross-review-summary.json')['rootAdjudicationFlagCount'],'root flag summary')
    su=readj(packet/'cross-review-summary.json'); need(su['baselineProtectedLiteralMismatchCount']==mismatches==5,'baseline mismatch totals')
    if args.repo_dir:
        repo=args.repo_dir.resolve()
        subprocess.run([sys.executable,'-B',str(cf/'verify_candidate_free.py'),str(repo)],check=True)
        subprocess.run([sys.executable,'-B',str(pr/'verify_primary.py'),str(repo)],check=True)
        subprocess.run([sys.executable,'-B',str(br/'verifier.py'),'--input-dir',str(cf)],check=True)
    print(json.dumps({'result':'PASS','verifier':'independent-cross-review','head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'cells':300,
      'proposalComparison':dict(agreements),'independentCounts':dict(counts),'rootAdjudicationFlags':flags,'baselineProtectedLiteralMismatches':mismatches},ensure_ascii=False,indent=2))
if __name__=='__main__':
    try: main()
    except Exception as e: print('FAIL: '+str(e),file=sys.stderr); raise
