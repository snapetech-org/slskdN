#!/usr/bin/env python3
import collections, hashlib, json, re
from pathlib import Path
TASK=Path(__file__).resolve().parents[1]
ROOT=TASK/'root-adjudication'; CF=TASK/'candidate-free'; PRIMARY=TASK/'primary-review'
BLIND=TASK/'blind-review'; CROSS=TASK/'cross-review'; ADVISORY=TASK/'advisory-review'
HEAD='8c752c49281418fdd96341ed46f5c321627b625f'; TREE='b930b0d82679e843849e54456f3250e422c4682c'
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def token_ok(source,target,protected):
 patterns=[r'\{[^{}]+\}',r'<[^>]+>',r'(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])']
 return all(collections.Counter(re.findall(p,source))==collections.Counter(re.findall(p,target)) for p in patterns) and all(x in target for x in protected)
# Root accepted the 67 advisory-supported recommendations, and adjusted four targets that still used jargon or implied destructive removal.
overrides={
 (1004,'fr'):('Nombre maximal de clients de versions antérieures pouvant se connecter simultanément','The Bridge setting counts simultaneous clients running earlier software versions; make the older-version meaning explicit instead of leaving “legacy” in English.'),
 (1004,'hi'):('पुराने संस्करण वाले क्लाइंटों की अधिकतम समवर्ती संख्या','The setting refers to clients using older software versions; spell that out instead of relying on the transliterated developer term “legacy”.'),
 (1004,'id'):('Jumlah maksimum klien versi lama secara bersamaan','The setting refers to clients using older software versions; use the direct Indonesian phrase “versi lama” rather than English “legacy”.'),
 (1021,'vi'):('Gỡ mục truyền khỏi danh sách','The exact transfer-table tooltip says the action removes this transfer from the list without deleting the source file; state that list-only action explicitly.'),
}
cf_path=CF/'source-current-cells.jsonl'; cfraw=[x for x in cf_path.read_bytes().splitlines() if x.strip()]
cfrows=[json.loads(x) for x in cfraw]
cfmap={(r['continuationRank'],r['locale']):r for r in cfrows}
rowhash={(r['continuationRank'],r['locale']):sha(line) for r,line in zip(cfrows,cfraw)}
pm={(r['continuationRank'],r['locale']):r for r in rows(PRIMARY/'primary-review.jsonl')}
phm={(r['continuationRank'],r['locale']):r for r in rows(PRIMARY/'holds-hash-only.jsonl')}
bm={(r['continuationRank'],r['locale']):r for r in rows(BLIND/'review-cells.jsonl')}
xm={(r['continuationRank'],r['locale']):r for r in rows(CROSS/'cross-review.jsonl')}
am={(r['continuationRank'],r['locale']):r for r in rows(ADVISORY/'findings.jsonl')}
assert len(cfmap)==len(bm)==len(xm)==300 and len(pm)==288 and len(phm)==12
assert set(cfmap)==set(bm)==set(xm) and set(pm).isdisjoint(phm) and set(pm)|set(phm)==set(cfmap)
assert len(am)==71 and set(overrides)=={k for k in am if am[k]['disposition']=='question'}
root_rows=[]; selected=[]; override_rows=[]; counts=collections.Counter()
for key in sorted(cfmap):
 c,b,x=cfmap[key],bm[key],xm[key]; p=pm.get(key,phm.get(key)); rank,locale=key
 assert p is not None
 assert c['sourceSha256']==x['sourceSha256'] and c['currentTargetSha256']==x['currentTargetSha256']
 assert c['callerContextSha256']==x['callerContextSha256']
 assert b['callerContextSha256']==c['callerContextSha256']
 rec={'schemaVersion':1,'reviewStage':'root-adjudication','exactHead':HEAD,'exactTree':TREE,
   'continuationRank':rank,'remainingQueueRank':c['remainingQueueRank'],'locale':locale,
   'sourceSha256':c['sourceSha256'],'currentTargetSha256':c['currentTargetSha256'],
   'callerContextSha256':c['callerContextSha256'],'candidateFreeRowSha256':rowhash[key],
   'primaryDisposition':p.get('disposition',p.get('decision')),'blindDecision':b.get('decision'),
   'crossDisposition':x['crossDisposition'],'confidence':'moderate'}
 if c['candidateFreeHold']:
  assert key not in am and x['crossDisposition']=='hash-only-hold' and p['disposition']=='hash-only-hold'
  rec.update({'callerless':True,'rootDisposition':'hold-hash-only','rootTarget':None,'rootTargetSha256':None,
   'sourceTextIncluded':False,'currentTargetTextIncluded':False,'rationale':'No exact production caller is pinned; preserve the text-free hash-only hold.'})
 else:
  assert c['sourceTextIncluded'] and c['currentTargetTextIncluded']
  assert c['source']==x['source'] and c['currentTarget']==x['currentTarget']
  rec.update({'callerless':False,'sourceId':c['sourceId'],'source':c['source'],'currentTarget':c['currentTarget'],
    'sourceTextIncluded':True,'currentTargetTextIncluded':True})
  if x['crossDisposition']=='correction':
   target=x['crossTarget']; rationale=x['crossRationale']; basis='independent cross-review recommendation'
   if key in overrides:
    target, rationale=overrides[key]; a=am[key]
    assert a['crossRecommendation']==x['crossTarget'] and a['suggestedAlternative']==target
    basis='root override after independent advisory review'
    override_rows.append({'continuationRank':rank,'locale':locale,'sourceId':c['sourceId'],'source':c['source'],
      'sourceSha256':c['sourceSha256'],'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],
      'crossTarget':x['crossTarget'],'crossTargetSha256':x['crossTargetSha256'],'rootTarget':target,
      'rootTargetSha256':tsha(target),'advisoryAlternative':a['suggestedAlternative'],
      'advisoryIssue':a['issue'],'callerContextSha256':c['callerContextSha256'],
      'rootRationale':rationale,'confidence':'moderate'})
   assert tsha(target)==(tsha(a['suggestedAlternative']) if key in overrides else x['crossTargetSha256'])
   rec.update({'rootDisposition':'correction','rootTarget':target,'rootTargetSha256':tsha(target),
      'selectionBasis':basis,'rationale':rationale,'crossTargetSha256':x['crossTargetSha256']})
   selected.append({'continuationRank':rank,'remainingQueueRank':c['remainingQueueRank'],'locale':locale,
      'sourceId':c['sourceId'],'source':c['source'],'sourceSha256':c['sourceSha256'],'catalogPath':c['catalogPath'],
      'before':c['currentTarget'],'beforeSha256':c['currentTargetSha256'],'after':target,'afterSha256':tsha(target),
      'disposition':'correction','selectionBasis':basis,'rationale':rationale,
      'callerContextSha256':c['callerContextSha256'],'crossTargetSha256':x['crossTargetSha256'],
      'overrideApplied':key in overrides})
  else:
   assert x['crossDisposition']=='accept-current'
   rec.update({'rootDisposition':'accept-current','rootTarget':c['currentTarget'],
      'rootTargetSha256':c['currentTargetSha256'],'selectionBasis':'cross-review accepted current value',
      'rationale':'Retain the exact-head target; caller-bound primary, blind, cross, and advisory review found no remaining issue.'})
 counts[rec['rootDisposition']]+=1; root_rows.append(rec)
assert len(selected)==71 and len(override_rows)==4 and counts=={'accept-current':217,'correction':71,'hold-hash-only':12}
for r in selected:
 c=cfmap[(r['continuationRank'],r['locale'])]
 assert r['after'] and isinstance(r['after'],str)
 protected=c['tokenEvidence']['protectedLiterals']['source']
 assert token_ok(c['source'],r['after'],protected)

# Advisory-suggested and cross-selected targets are independently token-checked by the cross verifier; explicitly pin the four root overrides.
for k,(target,_) in overrides.items():
 a=am[k]; c=cfmap[k]
 assert a['suggestedAlternative']==target and tsha(target)==tsha(a['suggestedAlternative'])
 assert c['tokenEvidence']['protectedLiterals']['source']==[]
(ROOT/'root-disposition-ledger.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in root_rows),encoding='utf-8')
(ROOT/'selected-targets.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in selected),encoding='utf-8')
(ROOT/'root-overrides.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in override_rows),encoding='utf-8')
inputs={
 'candidateFreeCellsSha256':sha(cf_path.read_bytes()),
 'candidateFreeManifestSha256':sha((CF/'manifest.json').read_bytes()),
 'primaryRowsSha256':sha((PRIMARY/'primary-review.jsonl').read_bytes()),
 'blindRowsSha256':sha((BLIND/'review-cells.jsonl').read_bytes()),
 'crossRowsSha256':sha((CROSS/'cross-review.jsonl').read_bytes()),
 'advisoryFindingsSha256':sha((ADVISORY/'findings.jsonl').read_bytes()),
 'advisoryRootFlagsSha256':sha((ADVISORY/'root-flags.json').read_bytes()),
}
att={'artifact':'slskdN PR #409 W1003-W1027 root adjudication input attestation','head':HEAD,'tree':TREE,
 'cellCount':300,'callerBackedCells':288,'selectedCorrections':71,'rootOverrides':4,'hashOnlyHolds':12,
 'inputHashes':inputs,'independentAdvisoryCounts':{'supported':67,'questioned':4},
 'priorActiveHoldsReattested':409,'newCallerlessHolds':12,'resultingActiveHolds':421,
 'baselineProtectedLiteralMismatch':'Hindi FTP; selected target preserves FTP',
 'rootAdjudicationPerformed':True,'catalogsEdited':False,'applicationPerformed':False,
 'nativeSpeakerApproval':False,'headedBrowserReviewPerformed':False}
(ROOT/'input-attestation.json').write_text(json.dumps(att,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
summary={'artifact':'slskdN PR #409 W1003-W1027 root adjudication','head':HEAD,'tree':TREE,
 'window':'W1003-W1027','cellCount':300,'rootDispositionCounts':dict(counts),
 'selectedCorrectionCount':71,'rootOverrideCount':4,'callerlessHashOnlyHolds':12,
 'advisorySupported':67,'advisoryQuestioned':4,'previousActiveHolds':409,'resultingActiveHolds':421,
 'confidence':'moderate','applicationPerformed':False,'nativeSpeakerApproval':False,'headedBrowserReviewPerformed':False}
(ROOT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
