#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, re, subprocess, sys, unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CAND=ROOT.parent/'candidate-free/input'
HEAD='1c2fe3be2c720693cbcb12d377bf1177804f4e77'; TREE='808501cbc3b6ed873a47d7188189d486f0673f5e'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
def need(ok,msg):
    if not ok: raise SystemExit('FAIL: '+msg)
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def readj(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def readjl(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def verify_sums(root):
    seen={}
    for line in (root/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1); need(n not in seen and sha((root/n).read_bytes())==h,'checksum '+n); seen[n]=h
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    need(actual==set(seen),'checksum inventory')
    return seen
def token_data(source,target):
    placeholders=lambda s:collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s))
    tags=lambda s:collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',s))
    nums=lambda s:[''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in t) for t in re.findall(r'\d+',s)]
    protected=lambda s:sorted(set(re.findall(r'\b[A-Z][A-Z0-9]{1,}\b',s))|{x for x in ('slskdN','PodCore','Wishlist','soulfind','FFmpeg','Lidarr') if x in s})
    sp,tp=placeholders(source),placeholders(target); st,tt=tags(source),tags(target); sn,tn=nums(source),nums(target); sl=protected(source)
    return {'placeholderParity':sp==tp,'markupParity':st==tt,'numericTokensPreserved':all(tn.count(x)>=n for x,n in collections.Counter(sn).items()),
      'missingProtectedLiterals':[x for x in sl if x not in target],'protectedLiteralsPreserved':all(x in target for x in sl)}
def main():
    if len(sys.argv)!=2: raise SystemExit('usage: verify_primary.py /path/to/exact-worktree')
    repo=Path(sys.argv[1]).resolve()
    subprocess.run([sys.executable,'-B',str(CAND/'verify_candidate_free.py'),str(repo)],check=True)
    sums=verify_sums(ROOT); m=readj(ROOT/'manifest.json'); s=readj(ROOT/'summary.json')
    need((m['head'],m['tree'],m['reviewPass'])==(HEAD,TREE,'primary'),'primary manifest identity')
    need(m['blindReviewUsed'] is False and m['crossReviewUsed'] is False and m['rootAdjudicationPerformed'] is False,'primary stage boundary')
    cm=readj(CAND/'manifest.json')
    need(m['candidateFreeInputManifestSha256']==sha((CAND/'manifest.json').read_bytes()) and m['candidateFreeInputChecksumsSha256']==sha((CAND/'SHA256SUMS.txt').read_bytes()),'candidate-free input pin')
    actual=set(sums)-{'manifest.json'}; listed={r['path']:r for r in m['files']}
    need(set(listed)==actual,'manifest file inventory')
    for n,r in listed.items(): need(r['bytes']==(ROOT/n).stat().st_size and r['sha256']==sha((ROOT/n).read_bytes()),'manifest content pin '+n)
    cells=readjl(CAND/'source-current-cells.jsonl'); need(len(cells)==300,'candidate input cell count')
    inputby={(r['continuationRank'],r['locale']):r for r in cells}
    selection={r['sourceId']:r for r in readjl(CAND/'selected-sources.jsonl')}
    callers={r['sourceId']:r for r in readjl(CAND/'caller-contexts.jsonl')}
    rows=readjl(ROOT/'primary-review.jsonl'); need(len(rows)==300,'primary row count')
    need([(r['continuationRank'],r['locale']) for r in rows]==[(rank,l) for rank in range(978,1003) for l in LOCALES],'primary row ordering')
    by={(r['continuationRank'],r['locale']):r for r in rows}; need(len(by)==300,'primary duplicate cell')
    counts=collections.Counter(); correction_rows=[]
    for row in rows:
        key=(row['continuationRank'],row['locale']); c=inputby[key]; sid=c['sourceId']; source=selection[sid]['source']; caller=callers[sid]
        need(row['reviewPass']=='primary' and row['head']==HEAD and row['tree']==TREE,'primary exact-head binding')
        need(row['sourceId']==sid and row['source']==source and row['sourceSha256']==tsha(source),'primary source binding')
        need(row['currentTarget']==c['currentTarget'] and row['currentTargetSha256']==c['currentTargetSha256'] and row['catalogFileSha256']==c['catalogFileSha256'] and row['catalogGitBlob']==c['catalogGitBlob'],'primary current target/catalog pin')
        need(row['callerContextSha256']==c['callerContextSha256']==caller['callerContextSha256'] and row['callerRefs']==caller['callers'] and row['callerCount']==len(caller['callers']),'primary caller context pin')
        need(row['blindReviewUsed'] is False and row['crossReviewUsed'] is False and row['rootAdjudicationPerformed'] is False,'later review flag')
        current=token_data(source,row['currentTarget']); need(row['tokenCheck']['current']==current,'current token evidence')
        need(row['disposition'] in {'accept-current','correction'} and bool(row['rationale']) and row['confidence'] in {'high','moderate','low'},'primary decision fields')
        if row['disposition']=='accept-current':
            need(row['candidateTarget'] is None and row['candidateTargetSha256'] is None and row['candidateTargetTextIncluded'] is False,'accept-current candidate')
        else:
            candidate=row['candidateTarget']; need(isinstance(candidate,str) and candidate and candidate!=row['currentTarget'],'correction text')
            need(row['candidateTargetSha256']==tsha(candidate) and row['candidateTargetTextIncluded'] is True,'candidate hash')
            ct=token_data(source,candidate); need(row['tokenCheck']['candidate']==ct,'candidate token evidence')
            need(ct['placeholderParity'] and ct['markupParity'] and ct['numericTokensPreserved'] and ct['protectedLiteralsPreserved'],'candidate token constraints')
            correction_rows.append({k:row[k] for k in ('continuationRank','remainingQueueRank','sourceId','sourceSha256','locale','currentTargetSha256','candidateTarget','candidateTargetSha256','rationale','confidence','callerContextSha256')})
        counts[row['disposition']]+=1
    listed_corrections=readjl(ROOT/'corrections.jsonl')
    need(listed_corrections==correction_rows,'correction subset')
    need(counts==collections.Counter(m['dispositions'])==collections.Counter(s['dispositions']),'disposition totals')
    need(counts['correction']==m['correctionCount']==s['correctionCount'] and counts['accept-current']==m['acceptCurrentCount']==s['acceptCurrentCount'],'review summary counts')
    need(m['cellCount']==s['cells']==300 and m['sourceCount']==s['sourceIds']==25 and m['localeCount']==s['locales']==12,'review coverage')
    need(s['candidateTokenMismatches']=={},'candidate token mismatch summary')
    print(json.dumps({'result':'PASS','verifier':'exact-worktree-primary','head':HEAD,'tree':TREE,'sources':25,'cells':300,
      'corrections':counts['correction'],'acceptCurrent':counts['accept-current'],'candidateTokenMismatches':{},
      'checksummedFiles':len(sums),'candidateFreeInputManifestSha256':cm['files'][0]['sha256'] if cm.get('files') else None},indent=2))
if __name__=='__main__': main()
