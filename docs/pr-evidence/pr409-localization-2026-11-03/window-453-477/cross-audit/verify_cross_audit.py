#!/usr/bin/env python3
import hashlib,json,re
from pathlib import Path

def h(b): return hashlib.sha256(b).hexdigest()
def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x]
def req(x,m):
    if not x: raise SystemExit('FAIL: '+m)
base=Path('/home/keith/Documents/code/task-scratch')
inp=base/'slskdn-pr409-w63-ranks453-477-primary-20261103/input'
primary_dir=base/'slskdn-pr409-w63-ranks453-477-primary-20261103/primary'
blind_root=base/'slskdn-pr409-w63-independent-blind-20261103'
blind_dir=blind_root/'blind-review'; blind_input=blind_root/'candidate-free-input'
out=Path(__file__).resolve().parent

def check_sums(root,name):
    for line in (root/name).read_text(encoding='utf-8').splitlines():
        digest,filename=line.split('  ',1)
        req(h((root/filename).read_bytes())==digest,'checksum '+str(root/filename))
check_sums(inp,'PACKET-SHA256SUMS.txt'); check_sums(primary_dir,'SHA256SUMS.txt'); check_sums(blind_root,'SHA256SUMS.txt')
manifest=readj(inp/'manifest.json'); primary_manifest=readj(primary_dir/'manifest.json'); blind_summary=readj(blind_dir/'summary.json')
manifest_sha=h((inp/'manifest.json').read_bytes()); input_sum_sha=h((inp/'PACKET-SHA256SUMS.txt').read_bytes())
req(primary_manifest['candidateFreeInput']['manifestJsonSha256']==manifest_sha and primary_manifest['candidateFreeInput']['checksumListSha256']==input_sum_sha,'primary candidate-free commitment')
req(blind_summary['candidateFreeManifestJsonSha256']==manifest_sha and blind_summary['candidateFreeChecksumListSha256']==input_sum_sha,'blind candidate-free commitment')
req(h((blind_input/'manifest.json').read_bytes())==manifest_sha and h((blind_input/'PACKET-SHA256SUMS.txt').read_bytes())==input_sum_sha,'blind input-copy commitments')
for line in (inp/'PACKET-SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
    digest,name=line.split('  ',1); req(h((blind_input/name).read_bytes())==digest,'blind copied file '+name)
req(manifest['head']=='1979c8dc4e59d5ca397251bcde73216a888aa9c9','pinned head')
req(manifest['tree']=='8b5c0ef640f487741f0a08086cc6d60d5eef43a4','pinned tree')
req(manifest['sourceCount']==25 and manifest['cellCount']==300 and len(manifest['locales'])==12,'input dimensions')
source=jl(inp/'source-inventory-selection.jsonl'); current=jl(inp/'source-current-cells.jsonl'); contexts=jl(inp/'caller-contexts.jsonl')
primary=jl(primary_dir/'review-decisions.jsonl'); blind=jl(blind_dir/'blind-ledger.jsonl'); ledger=jl(out/'cross-audit-ledger.jsonl')
plan=jl(out/'application-plan-changes.jsonl'); disagreements=jl(out/'cross-audit-disagreements.jsonl')
req(len(source)==25 and len(current)==300 and len(contexts)==25,'candidate-free row counts')
req(len(primary)==300 and len(blind)==300 and len(ledger)==300,'review/cross-audit row counts')
locales=manifest['locales']; expected={(rank,loc) for rank in range(453,478) for loc in locales}
key=lambda x:(x['continuationRank'],x['locale'])
smap={x['continuationRank']:x for x in source}; cmap={key(x):x for x in current}; pmap={key(x):x for x in primary}; bmap={key(x):x for x in blind}; lmap={key(x):x for x in ledger}; ctxmap={x['continuationRank']:x for x in contexts}
req(set(cmap)==expected and len(cmap)==300,'candidate-free cell set')
req(set(pmap)==expected and set(bmap)==expected and set(lmap)==expected,'review/cross cell set')
ph_re=re.compile(r'\{[^{}]+\}')
markup_re=re.compile(r'</?[A-Za-z][^>]*>')
num_re=re.compile(r'(?<![A-Za-z])\d+(?:[.,]\d+)?')
current_mismatch={'numeric':0,'protectedLiteral':0,'placeholder':0,'markup':0}
expected_disagreements=set(); expected_changes=set(); counts={'propose-update':0,'retain-current':0,'hold':0}
for k in sorted(expected):
    rank,loc=k; c=cmap[k]; p=pmap[k]; b=bmap[k]; r=lmap[k]; s=smap[rank]; ctx=ctxmap[rank]
    req(c['sourceId']==s['sourceId']==p['sourceId']==b['sourceId']==r['sourceId'],'source ID '+str(k))
    req(c['source']==s['source']==p['source']==b['source']==r['source'],'source text '+str(k))
    req(c['sourceSha256']==s['sourceSha256']==p['sourceSha256']==b['sourceSha256']==r['sourceSha256']==h(c['source'].encode()),'source hash '+str(k))
    req(c['currentTarget']==p['currentTarget']==b['currentTarget']==r['currentTarget'],'current readback '+str(k))
    req(c['currentTargetSha256']==p['currentTargetSha256']==b['currentTargetSha256']==r['currentTargetSha256']==h(c['currentTarget'].encode()),'current hash '+str(k))
    req(c['catalogPath']==r['catalogPath'] and c['catalogFileSha256']==r['catalogFileSha256'] and c['catalogGitBlob']==r['catalogGitBlob'],'catalog pin '+str(k))
    req(c['callerContextSha256']==r['callerContextSha256']==p['callerContextSha256']==b['callerContextSha256'],'caller context hash '+str(k))
    req(c['callerRefs']==r['callerRefs']==p['callerRefs']==b['callerRefs'],'caller refs '+str(k))
    req(c['sourceProtectedLiterals']==c['protectedLiteralEvidence']['sourceTokens'],'source protected evidence '+str(k))
    src_ph=c['placeholderEvidence']['sourceTokens']; cur_ph=c['placeholderEvidence']['currentTokens']
    src_markup=c['markupEvidence']['sourceTags']; cur_markup=c['markupEvidence']['currentTags']
    src_num=c['sourceNumericTokens']; cur_num=c['currentNumericTokens']; src_prot=c['sourceProtectedLiterals']; cur_prot=c['currentProtectedLiterals']
    if src_ph!=cur_ph: current_mismatch['placeholder']+=1
    if src_markup!=cur_markup: current_mismatch['markup']+=1
    if src_num!=cur_num: current_mismatch['numeric']+=1
    if not c['protectedLiteralEvidence']['matches']: current_mismatch['protectedLiteral']+=1
    target=r['crossAuditTarget']; action=r['crossAuditDisposition']; counts[action]+=1
    req(r['crossAuditTargetSha256']==h(target.encode()),'cross target hash '+str(k))
    req(ph_re.findall(c['source'])==ph_re.findall(target),'final placeholders '+str(k))
    req(markup_re.findall(c['source'])==markup_re.findall(target),'final markup '+str(k))
    req(num_re.findall(c['source'])==num_re.findall(target),'final numeric tokens '+str(k))
    for token in src_prot: req(token in target,'final protected literal '+token+' '+str(k))
    req(r['tokenEvidence']['sourceNumericTokens']==src_num and r['tokenEvidence']['currentNumericTokens']==cur_num,'token audit numeric '+str(k))
    req(r['tokenEvidence']['sourceProtectedLiterals']==src_prot and r['tokenEvidence']['currentProtectedLiterals']==cur_prot,'token audit protected '+str(k))
    ptarget=p['selectedTarget']; btarget=b.get('proposedTarget') or b['currentTarget']
    p_action='hold' if p['disposition']=='hold' else ('change' if ptarget!=c['currentTarget'] else 'retain')
    b_action='hold' if b['disposition']=='hold' else ('change' if btarget!=c['currentTarget'] else 'retain')
    if ptarget!=btarget or p_action!=b_action: expected_disagreements.add(k)
    if action=='propose-update':
        req(target!=c['currentTarget'],'update changes target '+str(k)); expected_changes.add(k)
        req(r['selectedFrom'] in ('primary','blind'),'update source '+str(k))
    elif action in ('hold','retain-current'):
        req(target==c['currentTarget'],'held/retained value '+str(k))
    else: req(False,'unexpected cross disposition '+str(k))
    if rank==476:
        req(action=='hold' and ctx['productionCallerCount']==0,'callerless rank 476 hold '+str(k))
        req(p['disposition']=='hold' and b['disposition']=='hold','rank 476 reviewer holds '+str(k))
    if k in {(459,'ar'),(475,'ar')}: req(action=='hold','terminology hold '+str(k))
req(current_mismatch=={'numeric':1,'protectedLiteral':19,'placeholder':0,'markup':0},'current mismatch counts '+str(current_mismatch))
req(counts=={'propose-update':55,'retain-current':231,'hold':14},'cross decision counts '+str(counts))
req(len(plan)==55 and {key(x) for x in plan}==expected_changes,'application plan cells')
req({key(x) for x in disagreements}==expected_disagreements and len(disagreements)==59,'disagreement set/count')
# Reattested live ref evidence and proposal-only boundary.
att=readj(out/'live-attestation-final.json')
req(att['head']==manifest['head'] and att['tree']==manifest['tree'],'live attestation pin')
req(att['branchRefHead']==manifest['head'] and att['pullRefHead']==manifest['head'],'live branch/pull refs')
req(att['state']=='OPEN' and att['isDraft'] is True,'live PR status')
app=readj(out/'application-plan-proposal.json')
req(app['authorization'].startswith('NOT AUTHORIZED') and app['noRepositoryOrPrWrites'],'application is proposal only')
req(app['selectedChangeCount']==55 and app['holdCount']==14 and app['callerlessRank476MustRemainUnchanged'],'application plan summary')
summary=readj(out/'summary.json')
req(summary['crossAuditCounts']==counts and summary['selectedChanges']==55 and summary['disagreementRows']==59,'summary counts')
# Output commitments; checksum list has a separate detached digest.
for line in (out/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
    digest,name=line.split('  ',1); req(h((out/name).read_bytes())==digest,'output checksum '+name)
req((out/'SHA256SUMS.sha256').read_text().strip()==h((out/'SHA256SUMS.txt').read_bytes()),'checksum list digest')
print(json.dumps({'status':'PASS','cells':len(ledger),'counts':counts,'disagreements':len(disagreements),'currentTokenMismatches':current_mismatch,'plannedTargetTokenMismatches':0,'inputChecksumListSha256':h((inp/'PACKET-SHA256SUMS.txt').read_bytes()),'primaryChecksumListSha256':h((primary_dir/'SHA256SUMS.txt').read_bytes()),'blindRootChecksumListSha256':h((blind_root/'SHA256SUMS.txt').read_bytes()),'outputChecksumListSha256':h((out/'SHA256SUMS.txt').read_bytes()),'ledgerSha256':h((out/'cross-audit-ledger.jsonl').read_bytes())},indent=2))
