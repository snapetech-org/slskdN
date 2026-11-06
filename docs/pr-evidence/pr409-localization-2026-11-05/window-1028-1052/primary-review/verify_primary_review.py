#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, re, subprocess, sys
from pathlib import Path
P=Path(__file__).resolve().parent; ROOT=P.parent; CF=ROOT/'candidate-free'
HEAD='624e27d8bb108a764df6daab5cfb1c517ebac96d'; TREE='d139a16988e23046ccb09f519db2d3b7ae0b86d1'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
sys.dont_write_bytecode=True

def fail(s): raise SystemExit('FAIL: '+s)
def sha(b): return hashlib.sha256(b).hexdigest()
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def readjl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def sumdir(path):
    listed={}
    for line in (path/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1)
        if n in listed or not (path/n).is_file() or sha((path/n).read_bytes())!=h: fail('checksum '+n)
        listed[n]=h
    actual={x.relative_to(path).as_posix() for x in path.rglob('*') if x.is_file() and x.name!='SHA256SUMS.txt'}
    if actual!=set(listed): fail('checksum inventory '+str(path))
    return listed
def token_data(source,target):
    placeholders=lambda s:collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s))
    tags=lambda s:collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',s))
    nums=lambda s:re.findall(r'(?<![A-Za-z])\d+(?:[.,]\d+)?%?(?![A-Za-z])',s)
    protected=lambda s:sorted(set(re.findall(r'\b[A-Z][A-Z0-9]{1,}\b',s))|{x for x in ('slskdN','PodCore','Wishlist','soulfind','FFmpeg','Lidarr') if x in s})
    return {'placeholders':placeholders(source)==placeholders(target),'markup':tags(source)==tags(target),
      'numbersSource':sorted(nums(source)),'numbersTarget':sorted(nums(target)),
      'numbersPreserved':collections.Counter(nums(source))<=collections.Counter(nums(target)),
      'protectedSource':protected(source),'protectedTarget':protected(target),
      'protectedLiteralsPreserved':all(x in target for x in protected(source))}
def main():
    input_sums=sumdir(CF); output_sums=sumdir(P)
    m=readj(P/'manifest.json'); summary=readj(P/'summary.json'); cm=readj(CF/'manifest.json')
    if (m.get('head'),m.get('tree'),m.get('window'),m.get('continuationRankRange'),m.get('remainingQueueRankRange'))!=(HEAD,TREE,'W86',[1028,1052],[928,952]): fail('manifest exact pin')
    if m.get('inputCandidateFreeManifestSha256')!=sha((CF/'manifest.json').read_bytes()) or m.get('inputCandidateFreeChecksumListSha256')!=sha((CF/'SHA256SUMS.txt').read_bytes()): fail('candidate-free input pin')
    if cm.get('head')!=HEAD or cm.get('tree')!=TREE: fail('candidate-free exact head')
    cf_copy=(P/'candidate-free-input-SHA256SUMS.txt').read_bytes()
    if cf_copy!=(CF/'SHA256SUMS.txt').read_bytes() or (P/'candidate-free-input-manifest.json').read_bytes()!=(CF/'manifest.json').read_bytes(): fail('candidate-free manifest/checksum copy')
    file_hashes={x.relative_to(P).as_posix():sha(x.read_bytes()) for x in P.rglob('*') if x.is_file() and x.name not in ('SHA256SUMS.txt','manifest.json')}
    declared={x['path']:x['sha256'] for x in m.get('files',[])}
    if file_hashes!=declared: fail('manifest output hashes')
    for key,filename in [('sourceCurrentCellsSha256','source-current-cells.jsonl'),('callerContextsSha256','caller-contexts.jsonl'),('catalogStructureSha256','catalog-structure.jsonl')]:
        if summary['inputHashes'].get(key)!=sha((CF/filename).read_bytes()): fail('input hash '+key)
    if summary['inputHashes'].get('candidateFreeManifestSha256')!=sha((CF/'manifest.json').read_bytes()) or summary['inputHashes'].get('candidateFreeChecksumListSha256')!=sha((CF/'SHA256SUMS.txt').read_bytes()): fail('summary input hashes')
    inp=readjl(CF/'source-current-cells.jsonl'); out=readjl(P/'primary-review.jsonl')
    if len(inp)!=300 or len(out)!=300: fail('cell counts')
    expected=[(r,l) for r in range(1028,1053) for l in LOCALES]
    if [(r['continuationRank'],r['locale']) for r in inp]!=expected or [(r['continuationRank'],r['locale']) for r in out]!=expected: fail('cell order/coverage')
    counts=collections.Counter(); proposal_tokens=0; holds=0
    for a,b in zip(inp,out):
        for field in ('continuationRank','remainingQueueRank','sourceIdSha256','sourceSha256','locale'):
            if b.get(field)!=a[field]: fail(f'input mismatch {a["continuationRank"]} {a["locale"]} {field}')
        target_hash_field='sourceCurrentTargetSha256' if b.get('decision')=='hold' else 'currentTargetSha256'
        if b.get(target_hash_field)!=a['currentTargetSha256']: fail(f'input mismatch {a["continuationRank"]} {a["locale"]} {target_hash_field}')
        if b.get('reviewRecordSha256')!=sha(canon({k:v for k,v in b.items() if k!='reviewRecordSha256'}).encode('utf-8')): fail('review record hash')
        if b.get('decision') not in ('proposal','retain','hold'): fail('decision vocabulary')
        counts[b['decision']]+=1
        if b['decision']=='hold':
            holds+=1
            if a.get('candidateFreeHold') is not True or b.get('sourceTextIncluded') is not False or b.get('currentTargetTextIncluded') is not False: fail('hold row text flags')
            if any(k in b for k in ('source','currentTarget','proposedTarget','rationale')): fail('hold row text')
            if b.get('reasonClass')!='no-pinned-production-localization-caller' or b.get('callerCount')!=0: fail('hold class/caller count')
            continue
        if a.get('candidateFreeHold') is not False or b.get('sourceTextIncluded') is not True or b.get('currentTargetTextIncluded') is not True: fail('caller-backed row flags')
        if b.get('source')!=a.get('source') or b.get('currentTarget')!=a.get('currentTarget') or b.get('currentTargetSha256')!=a.get('currentTargetSha256'): fail('source/current target copy')
        if not b.get('rationale') or b.get('confidence') not in ('high','moderate','low','unknown'): fail('rationale/confidence')
        target=b.get('proposedTarget') if b['decision']=='proposal' else b.get('currentTarget')
        if not isinstance(target,str) or b.get('reviewTargetSha256')!=sha(target.encode('utf-8')): fail('review target hash')
        if b['decision']=='proposal':
            proposal_tokens+=1
            if target==a['currentTarget']: fail('proposal does not change target')
            expected_tokens=token_data(a['source'],target)
            if b.get('tokenChecks')!=expected_tokens: fail('proposal token evidence mismatch')
            if not (expected_tokens['placeholders'] and expected_tokens['markup'] and expected_tokens['numbersPreserved'] and expected_tokens['protectedLiteralsPreserved']): fail('proposal token mismatch')
        elif 'proposedTarget' in b: fail('retain row contains proposal')
    if counts!=collections.Counter({'proposal':44,'retain':244,'hold':12}): fail('decision counts '+str(counts))
    if summary.get('decisions')!={'proposal':44,'retain':244,'hold':12} or summary.get('proposalTokenMismatches')!=0 or proposal_tokens!=44 or holds!=12: fail('summary decisions/tokens')
    if summary.get('callerBackedCells')!=288 or summary.get('callerlessHashOnlyCells')!=12: fail('caller coverage summary')
    active=readjl(P/'active-holds-reattestation-hash-only.jsonl'); expected_active=readjl(CF/'prior-held-cell-reattestation-hash-only.jsonl')
    product=readjl(P/'prior-product-readback-reattestation-hash-only.jsonl'); expected_product=readjl(CF/'window-product-readback-reattestation-hash-only.jsonl')
    if active!=expected_active or len(active)!=421 or any(any(k in r for k in ('source','sourceText','target','currentTarget','proposedTarget')) for r in active): fail('active hold reattestation')
    if product!=expected_product or len(product)!=300 or any(any(k in r for k in ('source','sourceText','target','currentTarget','proposedTarget','before','after')) for r in product): fail('prior product readback reattestation')
    note=(P/'provenance-note.txt').read_text(encoding='utf-8')
    if 'outside this window and were not used' not in note: fail('provenance note')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'cells':len(out),'decisions':dict(counts),
      'proposalTokenMismatches':0,'callerBackedCells':288,'callerlessHashOnlyCells':12,'activeHoldsReattestedHashOnly':len(active),
      'priorW1003ProductReadbackRows':len(product),'candidateFreeChecksums':len(input_sums),'primaryChecksums':len(output_sums)},indent=2))
if __name__=='__main__': main()
