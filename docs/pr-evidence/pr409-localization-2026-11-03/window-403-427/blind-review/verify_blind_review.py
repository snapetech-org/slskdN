#!/usr/bin/env python3
import collections, hashlib, json, pathlib, re, sys
OUT=pathlib.Path(__file__).resolve().parent
INPUT=pathlib.Path('/home/keith/Documents/code/task-scratch/slskdn-pr409-w61-ranks403-427-primary-20261103/input')
EXPECTED_MANIFEST='3d05538d9b4df6944add79c4fbedcaa90c93af5da7f439ebcbd55b346b8c6903'
EXPECTED_LIST='418735698e3e789a8c14005d531980631980bdccb993fe9ae669b65735e4ace7'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def fail(msg): raise SystemExit('FAIL: '+msg)
if sha(INPUT/'manifest.json')!=EXPECTED_MANIFEST: fail('candidate-free manifest hash')
if sha(INPUT/'PACKET-SHA256SUMS.txt')!=EXPECTED_LIST: fail('candidate-free checksum-list hash')
for line in (INPUT/'PACKET-SHA256SUMS.txt').read_text().splitlines():
    if not line.strip(): continue
    digest,name=line.split(None,1); name=name.strip().lstrip('*')
    if '/' in name or name in ('','..'): fail('unsafe packet path '+name)
    if sha(INPUT/name)!=digest: fail('candidate-free packet file '+name)
manifest=json.loads((INPUT/'manifest.json').read_text())
prov=json.loads((OUT/'provenance.json').read_text())
if not manifest.get('candidateFree'): fail('input is not marked candidate-free')
if manifest['head']!='0e2fc80bea8abfb02ebf13817bcef4e3ddeb4169' or manifest['tree']!='fad129065c1ccbdaaabe99c1054649dc426ea94b': fail('input head/tree')
if prov.get('candidateFreeInput',{}).get('manifestJSONSha256')!=EXPECTED_MANIFEST: fail('provenance manifest hash')
if prov.get('candidateFreeInput',{}).get('packetSHA256SUMSListSha256')!=EXPECTED_LIST: fail('provenance packet checksum-list hash')
source_rows=[json.loads(s) for s in (INPUT/'source-current-cells.jsonl').read_text().splitlines()]
contexts={x['continuationRank']:x for x in map(json.loads,(INPUT/'caller-contexts.jsonl').read_text().splitlines())}
catalog={x['locale']:x for x in map(json.loads,(INPUT/'catalog-structure.jsonl').read_text().splitlines())}
expected={(x['continuationRank'],x['locale']):x for x in source_rows}
ledger=[json.loads(s) for s in (OUT/'blind-ledger.jsonl').read_text().splitlines()]
if len(ledger)!=300 or set((x['continuationRank'],x['locale']) for x in ledger)!=set(expected): fail('ledger coverage')
ph=re.compile(r'\{[^{}]+\}'); tags=re.compile(r'</?[A-Za-z][^>]*>'); nums=re.compile(r'(?<!\w)\d+(?:[.,]\d+)?(?!\w)')
counts=collections.Counter()
for row in ledger:
    key=(row['continuationRank'],row['locale']); cell=expected[key]; ctx=contexts[cell['continuationRank']]
    if row['sourceId']!=cell['sourceId'] or row['sourceKey']!=cell['source'] or row['sourceKeySha256']!=cell['sourceSha256']: fail('source pin '+str(key))
    if row['currentTarget']!=cell['currentTarget'] or row['currentTargetSha256']!=cell['currentTargetSha256']: fail('current-target pin '+str(key))
    cat=catalog[cell['locale']]; pin=row['catalogPin']
    if (pin['path'],pin['fileSha256'],pin['gitBlob'])!=(cat['catalogPath'],cat['sha256'],cat['gitBlob']): fail('catalog pin '+str(key))
    if row['candidateFreeInput'] is not True or cell['containsCandidate']: fail('candidate contamination '+str(key))
    if ctx['productionCallerCount']<1: fail('missing caller '+str(key))
    ce=row['callerEvidence']
    if ce['productionCallerCount']!=ctx['productionCallerCount'] or ce['callers']!=ctx['callers'] or ce['aggregateContextSha256']!=cell['callerContextSha256']: fail('caller evidence '+str(key))
    status=row['decision']; counts[status]+=1
    if status not in {'accept-current','correction','refinement','hold'}: fail('decision value '+str(key))
    if status=='accept-current' and row['recommendedTarget']!=cell['currentTarget']: fail('accept-current changed target '+str(key))
    if status=='hold' and row['recommendedTarget']!=cell['currentTarget']: fail('hold changed target '+str(key))
    rec=row['recommendedTarget']
    if collections.Counter(ph.findall(cell['source']))!=collections.Counter(ph.findall(cell['currentTarget'])) or collections.Counter(ph.findall(cell['source']))!=collections.Counter(ph.findall(rec)): fail('placeholder preservation '+str(key))
    if collections.Counter(tags.findall(cell['source']))!=collections.Counter(tags.findall(rec)): fail('markup preservation '+str(key))
    if collections.Counter(nums.findall(cell['source']))!=collections.Counter(nums.findall(rec)): fail('numeric-token preservation '+str(key))
if sum(counts.values())!=300: fail('decision totals')
if counts['hold']!=12: fail('expected rank-409 semantic holds')
if any(x['continuationRank']==409 and x['decision']!='hold' for x in ledger): fail('rank-409 hold coverage')
if any(x['continuationRank']!=409 and x['decision']=='hold' for x in ledger): fail('unexpected hold')
for line in (OUT/'SHA256SUMS').read_text().splitlines():
    if not line.strip(): continue
    digest,name=line.split(None,1); name=name.strip().lstrip('*')
    if '/' in name or name=='SHA256SUMS': fail('unsafe output checksum entry '+name)
    if sha(OUT/name)!=digest: fail('output checksum '+name)
print(json.dumps({'result':'PASS','cells':len(ledger),'decisions':dict(counts),'candidateFreeManifestJSONSha256':EXPECTED_MANIFEST,'candidateFreePacketSHA256SUMSListSha256':EXPECTED_LIST},sort_keys=True))
