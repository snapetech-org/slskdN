#!/usr/bin/env python3
"""Portable integrity verifier for the blind W903-W927 review ledger."""
import hashlib,json,re,sys
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
def parse_sums(path,root):
    out={}
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        digest,name=line.split('  ',1)
        if name in out: fail('duplicate checksum entry '+name)
        p=(root/name).resolve()
        if not p.is_relative_to(root.resolve()) or not p.is_file() or sha(p.read_bytes())!=digest: fail('checksum mismatch '+name)
        out[name]=digest
    return out
def tokens(s,pattern): return re.findall(pattern,s)
def main():
    if len(sys.argv)!=3: raise SystemExit('usage: verify_blind_review.py INPUT_DIR REVIEW_DIR')
    inp=Path(sys.argv[1]).resolve(); out=Path(sys.argv[2]).resolve()
    m=readj(out/'blind-review-manifest.json')
    sums=parse_sums(out/'SHA256SUMS.txt',out)
    expected_output={'blind-review-ledger.jsonl','blind-review-manifest.json','verify_blind_review.py','README.md'}
    if set(sums)!=expected_output: fail('sealed output inventory')
    if set(x.relative_to(out).as_posix() for x in out.iterdir() if x.is_file())!=expected_output|{'SHA256SUMS.txt'}: fail('unexpected/missing review output')
    if sha((out/'blind-review-ledger.jsonl').read_bytes())!=m['ledgerSha256']: fail('ledger hash')
    if sha((out/'verify_blind_review.py').read_bytes())!=m['verifierSha256']: fail('verifier hash')
    if sha((out/'README.md').read_bytes())!=m['readmeSha256']: fail('README hash')
    if sha((out/'blind-review-manifest.json').read_bytes())!=sums['blind-review-manifest.json']: fail('review manifest seal')
    pm=readj(inp/'manifest.json')
    listed={x['path']:x for x in pm['files']}
    packet_sums=parse_sums(inp/'PACKET-SHA256SUMS.txt',inp)
    if set(packet_sums)!=set(listed)|{'manifest.json'}: fail('packet checksum inventory')
    if sha((inp/'manifest.json').read_bytes())!=packet_sums['manifest.json']: fail('packet manifest checksum')
    actual={p.relative_to(inp).as_posix() for p in inp.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    if actual!=set(listed)|{'manifest.json','PACKET-SHA256SUMS.txt'}: fail('packet file inventory')
    for name,rec in listed.items():
        b=(inp/name).read_bytes()
        if len(b)!=rec['bytes'] or sha(b)!=rec['sha256']: fail('packet manifest mismatch '+name)
    ih=tree_hash(inp)
    if ih!=m['inputTreeSha256']: fail('candidate-free input tree hash')
    if (pm['head'],pm['tree'],pm['pullRequest'],pm['window'],pm['continuationRankRange'],pm['remainingQueueRankRange'],pm['cellCount'])!=(m['head'],m['tree'],409,'W81',[903,927],[803,827],300): fail('input identity/window binding')
    att=readj(inp/'head-tree-attestation.json')
    if (att.get('headRefOid'),att.get('treeOid'),att.get('branchRefOid'),att.get('pullRefOid'))!=(m['head'],m['tree'],m['head'],m['head']): fail('head/tree attestation binding')
    cells=readrows(inp/'source-current-cells.jsonl')
    selected={r['sourceId']:r for r in readrows(inp/'selected-sources.jsonl')}
    if len(cells)!=300: fail('input cell count')
    ledger=readrows(out/'blind-review-ledger.jsonl')
    if len(ledger)!=300: fail('ledger cell count')
    key=lambda x:(x['continuationRank'],x['locale'])
    if len({key(x) for x in ledger})!=300: fail('duplicate ledger cell')
    if {key(x) for x in ledger}!={(r['continuationRank'],r['locale']) for r in cells}: fail('ledger/input cell coverage')
    ranks={}; counts={'accept':0,'correction':0,'refinement':0,'hold':0}
    for c in cells:
        x=next(a for a in ledger if key(a)==key(c)); src=selected[c['sourceId']]
        if (x['head'],x['tree'],x['inputTreeSha256'])!=(m['head'],m['tree'],ih): fail('row packet binding')
        for f in ['sourceId','source','sourceSha256','locale','currentTarget','currentTargetSha256','callerContextSha256','callerRefs','catalogKey','catalogPath','catalogFileSha256','catalogGitBlob','continuationRank','remainingQueueRank']:
            expected=c.get(f,src.get(f))
            if x.get(f)!=expected: fail('row input signature '+f+' '+str(key(x)))
        if sha(x['source'].encode())!=x['sourceSha256'] or sha(x['currentTarget'].encode())!=x['currentTargetSha256']: fail('row text hash '+str(key(x)))
        ph=r'\{[^{}]+\}'; tags=r'</?[A-Za-z][^>]*>'; nums=r'(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])'
        if sorted(tokens(src['source'],ph))!=sorted(tokens(x['currentTarget'],ph)): fail('current placeholder mismatch '+str(key(x)))
        if sorted(tokens(src['source'],tags))!=sorted(tokens(x['currentTarget'],tags)): fail('current markup mismatch '+str(key(x)))
        if any(tokens(x['currentTarget'],nums).count(t)<n for t,n in __import__('collections').Counter(tokens(src['source'],nums)).items()): fail('current numeric token mismatch '+str(key(x)))
        signature={k:x[k] for k in ['head','tree','continuationRank','remainingQueueRank','sourceId','source','sourceSha256','locale','catalogKey','catalogPath','catalogFileSha256','catalogGitBlob','callerContextSha256','callerRefs','currentTargetSha256']}
        if sha(canon(signature))!=x['structuralSignatureSha256']: fail('structural signature '+str(key(x)))
        decision=x['decision']
        if decision not in counts: fail('unknown decision')
        counts[decision]+=1
        has='proposedTarget' in x
        if has!=(decision in {'correction','refinement'}): fail('proposal/decision mismatch '+str(key(x)))
        if has:
            proposal=x['proposedTarget']
            if sha(proposal.encode())!=x.get('proposedTargetSha256'): fail('proposal hash '+str(key(x)))
            ph=r'\{[^{}]+\}'
            if sorted(tokens(src['source'],ph))!=sorted(tokens(proposal,ph)): fail('proposal placeholder mismatch '+str(key(x)))
            tags=r'</?[A-Za-z][^>]*>'
            if sorted(tokens(src['source'],tags))!=sorted(tokens(proposal,tags)): fail('proposal markup mismatch '+str(key(x)))
            if any(tokens(proposal,nums).count(t)<n for t,n in __import__('collections').Counter(tokens(src['source'],nums)).items()): fail('proposal numeric token mismatch '+str(key(x)))
        # Technical field/brand literals established by the supplied source and caller context.
        protected={905:['DHT'],907:['SongRec'],917:['ContentID','DHT'],918:['B'],919:['VPN'],921:['ID','content:audio:album:mb-release-id'],927:['SongID']}.get(c['continuationRank'],[])
        for literal in protected:
            if literal not in x['currentTarget']:
                if not has or literal not in x['proposedTarget'] or decision not in {'correction','refinement'}: fail('unresolved protected literal '+literal+' '+str(key(x)))
        if not x.get('rationale') or x.get('confidence') not in {'high','moderate','low','unknown'}: fail('missing rationale/confidence')
    if counts!=m['decisionCounts']: fail('decision counts')
    print(json.dumps({'result':'PASS','head':m['head'],'tree':m['tree'],'inputTreeSha256':ih,'cells':len(ledger),'decisionCounts':counts},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
