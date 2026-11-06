import collections,hashlib,json,pathlib,re
root=pathlib.Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def verify(folder,manifest):
 p=root/folder
 for line in (p/manifest).read_text().splitlines():
  h,n=line.split('  ',1);assert sha((p/n).read_bytes())==h,(folder,n)
verify('candidate-free-input','PACKET-SHA256SUMS.txt');verify('primary-review','PRIMARY-SHA256SUMS.txt');verify('blind-review','SHA256SUMS')
rows=[json.loads(x) for x in (root/'cross-audit-ledger.jsonl').read_text().splitlines()]
selected=[json.loads(x) for x in (root/'selected-changes.jsonl').read_text().splitlines()]
assert len(rows)==300 and len({(x['continuationRank'],x['locale']) for x in rows})==300
assert len(selected)==sum(x['crossAuditTarget']!=x['currentTarget'] for x in rows)
assert all(x['crossAuditDisposition']=='hold' and x['continuationRank']==409 and x['crossAuditTarget']==x['currentTarget'] for x in rows if x['crossAuditDisposition']=='hold')
assert sum(x['crossAuditDisposition']=='hold' for x in rows)==12
for x in rows:
 toks=lambda s:re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s)
 assert toks(x['source'])==toks(x['currentTarget'])==toks(x['crossAuditTarget'])
 assert x['head']=='0e2fc80bea8abfb02ebf13817bcef4e3ddeb4169' and x['tree']=='fad129065c1ccbdaaabe99c1054649dc426ea94b'
 assert x['callerCount']>0
print(json.dumps({'result':'PASS','cells':len(rows),'selected':len(selected),'holds':12,'placeholderMismatches':0}))
