#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
OUT=Path(__file__).resolve().parent
INPUT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-crossreview-w1003-1027-20261105')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def ck(ok,msg):
 if not ok:raise SystemExit('FAIL: '+msg)
for line in (OUT/'SHA256SUMS.txt').read_text().splitlines():
 if line.strip():
  digest,name=line.split('  ',1);p=OUT/name;ck(p.is_file() and sha(p)==digest,'checksum '+name)
a=json.loads((OUT/'input-attestation.json').read_text());ck(a['head']=='8c752c49281418fdd96341ed46f5c321627b625f' and a['tree']=='b930b0d82679e843849e54456f3250e422c4682c','pin')
fs=jl(OUT/'findings.jsonl');xs=jl(INPUT/'cross-review.jsonl');corr={(r['continuationRank'],r['locale']):r for r in xs if r.get('crossDisposition')=='correction'};ck(len(fs)==71 and len(corr)==71,'71 correction rows')
seen=set()
for f in fs:
 k=(f['continuationRank'],f['locale']);ck(k not in seen,'duplicate '+str(k));seen.add(k);r=corr.get(k);ck(r is not None,'unexpected '+str(k))
 for a,b in [('sourceId','sourceId'),('source','source'),('sourceSha256','sourceSha256'),('currentTarget','currentTarget'),('crossRecommendation','crossTarget')]:ck(f[a]==r[b],'mismatch '+str(k)+' '+a)
 ck(f['primaryRecommendation']['target']==r.get('primaryCandidateTarget'),'primary '+str(k));ck(f['blindRecommendation']['target']==r.get('blindProposalTarget'),'blind '+str(k))
 pins=[{'path':c['path'],'line':c['line'],'fileSha256':c['fileSha256'],'gitBlob':c['gitBlob'],'lineSha256':c['lineSha256'],'contextSha256':c['contextSha256']} for c in r['callerRefPins']];ck(f['callerContextPins']==pins,'caller pins '+str(k));ck(r.get('callerCount',0)>0 and r['effectiveTargetTokenCheck'].get('protectedLiteralsPreserved'),'caller/token '+str(k));ck(k[0]!=1024,'hold in findings')
ck(len(seen)==71,'coverage')
h=[r for r in xs if r.get('continuationRank')==1024];ck(len(h)==12 and len({r['locale'] for r in h})==12,'hold count');ck(all(r.get('candidateFreeHold') and not r.get('sourceTextIncluded') and not r.get('currentTargetTextIncluded') and not r.get('crossTargetTextIncluded') and r.get('callerCount')==0 for r in h),'hold hash-only')
ctx={r['sourceId']:r for r in jl(OUT/'caller-context-evidence.jsonl')};ck(len(ctx)==15 and all(f['sourceId'] in ctx for f in fs),'caller evidence')
flags=json.loads((OUT/'root-flags.json').read_text())['flags'];fk={(f['continuationRank'],f['locale']) for f in flags};qk={(f['continuationRank'],f['locale']) for f in fs if f['disposition']=='question'};ck(fk==qk and len(flags)==4,'flags')
vr=json.loads((OUT/'verifier-results.json').read_text());ck(vr['sealedInputVerifierExitCode']==0 and all(r.get('result')=='PASS' for r in vr['sealedInputVerifier']),'sealed verifier')
print(json.dumps({'result':'PASS','verifier':'advisory-packet','reviewedCells':len(fs),'rootFlags':len(flags),'callerBackedSources':len(ctx),'hashOnlyHoldsPreserved':len(h),'checksumFiles':len((OUT/'SHA256SUMS.txt').read_text().splitlines())},indent=2))
