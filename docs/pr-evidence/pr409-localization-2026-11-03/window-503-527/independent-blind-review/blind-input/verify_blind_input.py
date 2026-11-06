#!/usr/bin/env python3
import hashlib,json,re
from pathlib import Path
I=Path(__file__).resolve().parent
def sha(b): return hashlib.sha256(b).hexdigest()
m=json.loads((I/'manifest.json').read_text())
assert m['repository']=='snapetech-org/slskdN' and m['pullRequest']==409
assert m['window']=='W65' and m['head']=='c64d57a0322897bbaac77fa88a1327dd2f687db7'
assert m['tree']=='51ebf25124fc6ba30c8d5d99298e78353a951f17'
rows=[json.loads(x) for x in (I/'translation-prompts.jsonl').read_text().splitlines() if x]
assert len(rows)==300 and len({(r['sourceId'],r['locale']) for r in rows})==300
assert all(1 <= r['productionCallerCount'] == len(r['callers']) for r in rows)
def scan(x):
    if isinstance(x,dict):
        assert not (set(x)&set(m['forbiddenFieldNames'])), set(x)&set(m['forbiddenFieldNames'])
        for v in x.values(): scan(v)
    elif isinstance(x,list):
        for v in x: scan(v)
for r in rows: scan(r)
assert all(sha(r['source'].encode())==r['sourceSha256'] for r in rows)
assert all(r['sourceTokens']==sorted(set(re.findall(r'\{[^{}]+\}',r['source']))) for r in rows)
listed={f['path']:f for f in m['files']}
actual={p.name for p in I.iterdir() if p.is_file() and p.name not in ('manifest.json','PACKET-SHA256SUMS.txt')}
assert set(listed)==actual
for n,f in listed.items():
    b=(I/n).read_bytes(); assert len(b)==f['bytes'] and sha(b)==f['sha256'],n
sums={}
for line in (I/'PACKET-SHA256SUMS.txt').read_text().splitlines():
    digest,name=line.split(None,1); sums[name.strip()]=digest
assert set(sums)=={p.name for p in I.iterdir() if p.is_file() and p.name!='PACKET-SHA256SUMS.txt'}
for n,d in sums.items(): assert sha((I/n).read_bytes())==d,n
print(json.dumps({'pass':True,'cells':len(rows),'locales':m['locales'],'forbiddenFieldsAbsent':True,'head':m['head']}))
