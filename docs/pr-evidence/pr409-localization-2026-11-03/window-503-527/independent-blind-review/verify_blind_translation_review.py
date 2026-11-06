#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,subprocess
OUT=Path(__file__).resolve().parent
I=Path('/home/keith/Documents/code/task-scratch/slskdn-pr409-w65-ranks503-527-primary-20261103/blind-input')
def sha(b): return hashlib.sha256(b).hexdigest()
def st(s): return sha(s.encode('utf-8'))
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def check_sums(d,name):
    p=subprocess.run(['sha256sum','-c',name],cwd=d,text=True,capture_output=True)
    assert p.returncode==0,(d,p.stdout,p.stderr)
    return p.stdout
input_checks=check_sums(I,'PACKET-SHA256SUMS.txt')
subprocess.run(['python3',str(I/'verify_blind_input.py')],cwd=I,check=True,capture_output=True,text=True)
manifest=j(I/'manifest.json'); summary=j(OUT/'summary.json')
assert manifest['head']==summary['head']=='c64d57a0322897bbaac77fa88a1327dd2f687db7'
assert manifest['tree']==summary['tree']=='51ebf25124fc6ba30c8d5d99298e78353a951f17'
assert sha((I/'manifest.json').read_bytes())==summary['blindInputManifestSha256']
assert sha((I/'PACKET-SHA256SUMS.txt').read_bytes())==summary['blindInputChecksumListSha256']
assert (OUT/'input-manifest.json').read_bytes()==(I/'manifest.json').read_bytes()
assert (OUT/'input-PACKET-SHA256SUMS.txt').read_bytes()==(I/'PACKET-SHA256SUMS.txt').read_bytes()
source_rows=jl(I/'translation-prompts.jsonl'); ledger=jl(OUT/'sealed-translation-ledger.jsonl')
assert len(source_rows)==len(ledger)==300
src={(r['sourceId'],r['locale']):r for r in source_rows}
rows={(r['sourceId'],r['locale']):r for r in ledger}
assert len(rows)==300 and rows.keys()==src.keys()
ph=re.compile(r'\{[^{}\r\n]+\}'); tag=re.compile(r'</?[A-Za-z][^<>]*>'); num=re.compile(r'(?<!\w)[+-]?\d+(?:[.,]\d+)?%?(?!\w)')
identifiers=('ContentID','MusicBrainz','VPN','URL','slskdN','API')
for key,r in rows.items():
    s=src[key]
    assert r['head']==manifest['head'] and r['tree']==manifest['tree']
    assert (r['source'],r['sourceSha256'],r['language'],r['callerCount'])==(s['source'],s['sourceSha256'],s['language'],s['productionCallerCount'])
    assert r['callerReferences']==[{'path':c['path'],'line':c['line'],'lineText':c['lineText'],'context':c['context']} for c in s['callers']]
    assert r['disposition']=='propose' and r['translation'].strip() and r['rationale'].strip()
    assert r['translationSha256']==st(r['translation'])
    placeholders=ph.findall(s['source']); assert placeholders==s['sourceTokens']==ph.findall(r['translation'])
    assert r['placeholderChecks']=={'sourcePlaceholders':placeholders,'translationPlaceholders':placeholders,'match':True,'missing':[],'unexpected':[]}
    tags=tag.findall(s['source']); assert tags==tag.findall(r['translation'])==r['markupChecks']['sourceTags']==r['markupChecks']['translationTags']
    assert r['markupChecks']['match'] is True
    nums=num.findall(s['source']); assert nums==num.findall(r['translation'])==r['numericTokenChecks']['sourceTokens']==r['numericTokenChecks']['translationTokens']
    assert r['numericTokenChecks']['match'] is True
    protected=[x for x in identifiers if x in s['source']]
    assert r['protectedLiteralChecks']['sourceLiterals']==protected
    missing=[x for x in protected if x not in r['translation']]
    assert r['protectedLiteralChecks']['missing']==missing==[] and r['protectedLiteralChecks']['translationContainsAll'] is True
    assert r['confidence'] in {'high','moderate','low'} and r['sourceContextOnly'] is True
listed={line.split(None,1)[1].strip().lstrip('*') for line in (OUT/'SHA256SUMS.txt').read_text().splitlines() if line.strip()}
assert listed=={p.name for p in OUT.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt'}
for line in (OUT/'SHA256SUMS.txt').read_text().splitlines():
    digest,name=line.split(None,1); name=name.strip().lstrip('*')
    assert sha((OUT/name).read_bytes())==digest,(name,'checksum')
print(json.dumps({'result':'PASS','head':manifest['head'],'tree':manifest['tree'],'cells':len(rows),'locales':manifest['locales'],'placeholderMismatches':0,'markupMismatches':0,'numericMismatches':0,'protectedLiteralMismatches':0,'inputManifestSha256':summary['blindInputManifestSha256'],'inputChecksumListSha256':summary['blindInputChecksumListSha256'],'outputChecksumListSha256':sha((OUT/'SHA256SUMS.txt').read_bytes()),'inputVerifier':'PASS','inputPacketChecksums':'PASS'},ensure_ascii=False,indent=2))
