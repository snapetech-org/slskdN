#!/usr/bin/env python3
"""Portable verifier for the sealed slskdN PR #409 cross-review output."""
import collections, hashlib, json, re, sys
from pathlib import Path

def fail(message): raise SystemExit('FAIL: '+message)
def sha(data): return hashlib.sha256(data).hexdigest()
def canon(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def readj(path): return json.loads(path.read_text(encoding='utf-8'))
def readrows(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def tree_hash(root):
    rec=[]
    for p in sorted(x for x in root.rglob('*') if x.is_file()):
        b=p.read_bytes(); rec.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':sha(b)})
    return sha(canon(rec))
def verify_sums(path,root):
    out={}
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        digest,name=line.split('  ',1)
        if name in out: fail('duplicate checksum '+name)
        p=(root/name).resolve()
        if not p.is_relative_to(root.resolve()) or not p.is_file() or sha(p.read_bytes())!=digest: fail('checksum mismatch '+name)
        out[name]=digest
    return out
def exact_dir_files(root,expected,label):
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    if actual!=expected: fail(label+' file inventory mismatch; extra='+repr(sorted(actual-expected))+' missing='+repr(sorted(expected-actual)))
def text_hash(s): return sha(s.encode('utf-8'))
def tokens(s,pat): return re.findall(pat,s)

def main():
    if len(sys.argv)!=5: raise SystemExit('usage: verify_cross_review.py INPUT_DIR PRIMARY_DIR BLIND_DIR CROSS_REVIEW_DIR')
    inp,primary,blind,out=(Path(x).resolve() for x in sys.argv[1:])
    im=readj(inp/'manifest.json'); pm=readj(primary/'manifest.json'); bm=readj(blind/'blind-review-manifest.json'); cm=readj(out/'cross-review-manifest.json')
    # Verify all four packet checksum sets and exact inventories.
    isum=verify_sums(inp/'PACKET-SHA256SUMS.txt',inp)
    p_sum=verify_sums(primary/'SHA256SUMS.txt',primary)
    b_sum=verify_sums(blind/'SHA256SUMS.txt',blind)
    c_sum=verify_sums(out/'SHA256SUMS.txt',out)
    input_manifest_files={x['path']:x for x in im['files']}
    if set(isum)!=set(input_manifest_files)|{'manifest.json'}: fail('candidate-free checksum inventory')
    if sha((inp/'manifest.json').read_bytes())!=isum['manifest.json']: fail('candidate-free manifest seal')
    actual_input={p.relative_to(inp).as_posix() for p in inp.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    if actual_input!=set(input_manifest_files)|{'manifest.json','PACKET-SHA256SUMS.txt'}: fail('candidate-free exact file inventory')
    for name,rec in input_manifest_files.items():
        b=(inp/name).read_bytes()
        if len(b)!=rec['bytes'] or sha(b)!=rec['sha256']: fail('candidate-free file hash '+name)
    for root,sums,label in [(primary,p_sum,'primary'),(blind,b_sum,'blind')]:
        actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        if actual!=set(sums)|{'SHA256SUMS.txt'}: fail(label+' exact file inventory')
    cross_expected={x['path']:x for x in cm['files']}
    if set(c_sum)!=set(cross_expected)|{'cross-review-manifest.json'}: fail('cross-review checksum inventory')
    if sha((out/'cross-review-manifest.json').read_bytes())!=c_sum['cross-review-manifest.json']: fail('cross-review manifest seal')
    exact_dir_files(out,set(c_sum)|{'SHA256SUMS.txt'},'cross-review')
    for name,rec in cross_expected.items():
        b=(out/name).read_bytes()
        if len(b)!=rec['bytes'] or sha(b)!=rec['sha256']: fail('cross-review file hash '+name)
    if (im['head'],im['tree'],im['cellCount'])!=(pm['head'],pm['tree'],pm['cellCount']): fail('primary exact head/tree/cell binding')
    if (im['head'],im['tree'],im['cellCount'],im['pullRequest'],im['window'])!=(bm['head'],bm['tree'],bm['cellCount'],409,'W81'): fail('blind exact input identity')
    if (sha((inp/'manifest.json').read_bytes()),sha((inp/'PACKET-SHA256SUMS.txt').read_bytes()))!=(pm['candidateFreeInputManifestSha256'],pm['candidateFreeInputChecksumListSha256']): fail('primary candidate-free hashes')
    if (sha((inp/'manifest.json').read_bytes()),sha((inp/'PACKET-SHA256SUMS.txt').read_bytes()))!=(bm['inputManifestSha256'],bm['inputChecksumFileSha256']): fail('blind candidate-free hashes')
    ih=tree_hash(inp)
    if ih!=bm['inputTreeSha256'] or ih!=readj(out/'proposal-reconciliation-summary.json')['candidateFreeInputTreeSha256']: fail('candidate-free tree hash')
    # Check the pre-proposal seal separately from later reconciliation artifacts.
    pre=verify_sums(out/'PRE-PROPOSAL-SHA256SUMS.txt',out)
    if set(pre)!={'PRE-PROPOSAL-SEAL.txt','independent-decisions.jsonl','independent-pass-summary.json'}: fail('pre-proposal seal inventory')
    independent_summary=readj(out/'independent-pass-summary.json')
    if sha((out/'independent-decisions.jsonl').read_bytes())!=independent_summary['ledgerSha256'] or sha((out/'independent-decisions.jsonl').read_bytes())!=cm['independentLedgerSha256']: fail('pre-proposal ledger hash')
    if independent_summary['proposalContentsOpenedAtSealTime'] is not False: fail('pre-proposal phase seal')
    # Exact row-by-row binding across the three proposal/review ledgers and the sealed independent pass.
    cells=readrows(inp/'source-current-cells.jsonl'); selected={x['sourceId']:x for x in readrows(inp/'selected-sources.jsonl')}
    p_rows=readrows(primary/'primary-review.jsonl'); b_rows=readrows(blind/'blind-review-ledger.jsonl')
    d_rows=readrows(out/'independent-decisions.jsonl'); cross=readrows(out/'cross-review-ledger.jsonl')
    if any(len(x)!=300 for x in [cells,p_rows,b_rows,d_rows,cross]): fail('full cell count')
    key=lambda x:(x['continuationRank'],x['locale'])
    cell_keys={key(x) for x in cells}
    maps=[]
    for label,data in [('primary',p_rows),('blind',b_rows),('independent',d_rows),('cross',cross)]:
        if len({key(x) for x in data})!=300 or {key(x) for x in data}!=cell_keys: fail(label+' cell coverage/duplicate check')
        maps.append({key(x):x for x in data})
    P,B,D,C=maps
    PH=re.compile(r'\{[^{}]+\}'); TH=re.compile(r'</?[A-Za-z][^>]*>'); NH=re.compile(r'(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])')
    for c in cells:
        k=key(c); x=C[k]; p=P[k]; b=B[k]; d=D[k]; src=selected[c['sourceId']]
        bound={f:c[f] for f in ['sourceId','source','sourceSha256','locale','currentTarget','currentTargetSha256','callerContextSha256','callerRefs','catalogKey','catalogPath','catalogFileSha256','catalogGitBlob','continuationRank','remainingQueueRank']}
        for label,row in [('primary',p),('blind',b),('independent',d),('cross',x)]:
            for f,val in bound.items():
                if row.get(f)!=val: fail(f'{label} exact cell binding {k} {f}')
        if (p['head'],p['tree'])!=(im['head'],im['tree']) or (b['head'],b['tree'])!=(im['head'],im['tree']): fail('row head/tree '+str(k))
        if b['inputTreeSha256']!=ih: fail('blind row input tree '+str(k))
        for row,target_name,hash_name,label in [(d,'independentTarget','independentTargetSha256','independent'),(x,'finalTarget','finalTargetSha256','final')]:
            target=row.get(target_name)
            if target is not None and text_hash(target)!=row.get(hash_name): fail(label+' target hash '+str(k))
        if p['disposition']=='correct' and text_hash(p['target'])!=p['targetSha256']: fail('primary proposal hash '+str(k))
        if b['decision'] in ('correction','refinement') and text_hash(b['proposedTarget'])!=b['proposedTargetSha256']: fail('blind proposal hash '+str(k))
        target=x['finalTarget']
        if target is not None:
            if sorted(tokens(c['source'],PH))!=sorted(tokens(target,PH)): fail('final placeholder parity '+str(k))
            if sorted(tokens(c['source'],TH))!=sorted(tokens(target,TH)): fail('final markup parity '+str(k))
            if not c['numericTokensPreserved']: fail('numeric token audit '+str(k))
        elif x['finalDecision']!='hold': fail('null final target outside hold '+str(k))
        if x['finalDecision']=='hold' and (k[0]!=910 or p['disposition']!='hold'): fail('unexpected final hold '+str(k))
        # Protected literals required by this packet's source/caller semantics.
        literals={905:['DHT'],907:['SongRec'],917:['ContentID','DHT'],918:['B'],919:['VPN'],921:['ID','content:audio:album:mb-release-id'],927:['SongID']}.get(k[0],[])
        if target is not None:
            for literal in literals:
                if literal not in target: fail('protected literal '+literal+' '+str(k))
        if k[0]==910:
            call=next(z for z in readrows(inp/'caller-contexts.jsonl') if z['sourceId']==c['sourceId'])
            if 'ed25519:&lt;base64 signature&gt;' not in '\n'.join(line['text'] for cr in call['callers'] for line in cr['context']): fail('inline ed25519 context literal')
            if x['finalDecision']!='hold' or x['finalTarget'] is not None: fail('rank 910 hold')
        for audit_name in ['primaryAudit','blindAudit']:
            if not x.get(audit_name): fail('missing proposal audit status '+str(k))
    pcounts=collections.Counter(x['disposition'] for x in p_rows)
    bcounts=collections.Counter(x['decision'] for x in b_rows)
    finalcounts=collections.Counter(x['finalDecision'] for x in cross)
    if pcounts!=collections.Counter({'accept-current':245,'correct':43,'hold':12}): fail('primary row counts')
    if bcounts!=collections.Counter({'accept':239,'correction':26,'refinement':35,'hold':0}): fail('blind row counts')
    if dict(finalcounts)!=readj(out/'proposal-reconciliation-summary.json')['finalCounts']: fail('final row counts')
    if sha((out/'cross-review-ledger.jsonl').read_bytes())!=cm['crossReviewLedgerSha256']: fail('final ledger hash')
    if (cm['head'],cm['tree'],cm['cellCount'])!=(im['head'],im['tree'],300): fail('cross manifest identity')
    print(json.dumps({'result':'PASS','head':im['head'],'tree':im['tree'],'candidateFreeInputTreeSha256':ih,'cells':300,'primaryCounts':dict(pcounts),'blindCounts':dict(bcounts),'finalCounts':dict(finalcounts),'crossLedgerSha256':cm['crossReviewLedgerSha256']},ensure_ascii=False,indent=2))
if __name__=='__main__':
    main()
