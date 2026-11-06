#!/usr/bin/env python3
"""Portable verifier for the slskdN PR #409 W74 cross-audit bundle."""
from __future__ import annotations
import collections, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
E=ROOT/'evidence'
CI=E/'candidate-free/input'
PO=E/'primary-review/output'
BO=E/'blind-review/output'
DISPOSITIONS=('accept-current','select-update','hold-text-free')

def sha(b): return hashlib.sha256(b).hexdigest()
def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def lines(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def require(ok,msg):
    if not ok: raise SystemExit('FAIL: '+msg)

def verify_sums(folder, sum_name, expected_files=None):
    manifest=folder/sum_name
    entries={}
    for line in manifest.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        digest,rel=line.split('  ',1)
        require(rel not in entries,'duplicate checksum path '+str(rel))
        path=(folder/rel).resolve()
        require(path.is_relative_to(folder.resolve()),'checksum path escapes '+str(folder))
        require(path.is_file() and sha(path.read_bytes())==digest,'checksum mismatch '+str(path))
        entries[rel]=digest
    if expected_files is not None:
        require(set(entries)==set(expected_files),'checksum inventory mismatch '+str(folder))
    return entries

# Candidate-free evidence is checked locally without the original absolute-path verifier.
ci_manifest=readj(CI/'manifest.json')
require(ci_manifest['candidateFree'] is True and ci_manifest['reviewDecisionsIncluded'] is False and ci_manifest['proposedTargetsIncluded'] is False,'candidate-free manifest flags')
HEAD='70e5beffd5cd8d68b8aedffa5c85d16e2cc19b3f'
TREE='14620c63bee971428fa1cd6cf1f4e944b86056a7'
require((ci_manifest['head'],ci_manifest['tree'])==(HEAD,TREE),'candidate-free pin')
ci_sums=verify_sums(CI,'PACKET-SHA256SUMS.txt')
for item in ci_manifest['files']:
    data=(CI/item['path']).read_bytes()
    require(len(data)==item['bytes'] and sha(data)==item['sha256'],'candidate-free manifest entry '+item['path'])
require(len(ci_sums)==18,'candidate-free checksum count')

# Validate copied primary and blind review packets, including their evidence inventory.
p_manifest=readj(PO/'manifest.json')
require((p_manifest['head'],p_manifest['tree'])==(HEAD,TREE),'primary packet pin')
p_expected={x['path'] for x in p_manifest['files']}|{'manifest.json'}
p_sums=verify_sums(PO,'SHA256SUMS.txt',p_expected)
b_manifest=readj(BO/'review-summary.json')
require((b_manifest['reviewedHead'],b_manifest['reviewedTree'])==(HEAD,TREE),'blind packet pin')
b_sums=verify_sums(BO,'OUTPUT-SHA256SUMS.txt')
b_actual={p.relative_to(BO).as_posix() for p in BO.rglob('*') if p.is_file() and p.name!='OUTPUT-SHA256SUMS.txt'}
require(set(b_sums)==b_actual,'blind output checksum inventory')
# The blind review uses a copied candidate-free packet; confirm it matches this bundle's source evidence.
for rel in ('manifest.json','PACKET-SHA256SUMS.txt','source-current-cells.jsonl','caller-contexts.jsonl','source-inventory-selection.jsonl','selection-boundary.jsonl'):
    require(sha((CI/rel).read_bytes())==sha((BO/'input'/rel).read_bytes()),'blind candidate-free input diverges: '+rel)

# Validate PR attestations embedded in both review packets.
for path in (PO/'live-before.json',PO/'live-after.json'):
    x=readj(path)
    require(x['state']=='OPEN' and x['isDraft'] is True and x['headRefOid']==HEAD,'primary live PR attestation')
    require(x['mergeStateStatus']=='CLEAN','primary merge-state attestation')
for name in ('PR-attestation-before.json','PR-attestation-after.json'):
    x=readj(BO/name)
    require(x['state']=='OPEN' and x['draft'] is True and x['head']==HEAD and x['tree']==TREE,'blind live PR attestation '+name)

sources=lines(CI/'source-current-cells.jsonl')
primary=lines(PO/'primary-review.jsonl')
blind=lines(BO/'blind-review-ledger.jsonl')
ledger=lines(ROOT/'cross-review-ledger.jsonl')
updates=lines(ROOT/'selected-updates.jsonl')
holds=lines(ROOT/'holds.jsonl')
rewrites=readj(ROOT/'source-rewrites.json')
custom_rows=readj(ROOT/'cross-adjudications.json')
summary=readj(ROOT/'cross-summary.json')
pins=readj(ROOT/'source-head-pins.json')
require((len(sources),len(primary),len(blind),len(ledger))==(300,300,300,300),'300-cell packet coverage')
require(pins['head']==HEAD and pins['tree']==TREE and pins['state']=='OPEN' and pins['isDraft'] is True,'cross source/head pins')
live=readj(ROOT/'live-pr-attestation-after.json')
require(live['state']=='OPEN' and live['isDraft'] is True and live['headRefOid']==HEAD and live['tree']==TREE,'live PR reattestation after review')
source_by={(r['continuationRank'],r['locale']):r for r in sources}
primary_by={(r['continuationRank'],r['locale']):r for r in primary}
blind_by={(r['continuationRank'],r['locale']):r for r in blind}
require(len(source_by)==len(primary_by)==len(blind_by)==300,'duplicate review cell')
require([(r['continuationRank'],r['locale']) for r in ledger]==[(r['continuationRank'],r['locale']) for r in sources],'cross ledger order')

placeholder_re=re.compile(r'\{[^{}]+\}')
tag_re=re.compile(r'</?([A-Za-z][A-Za-z0-9]*)\b[^>]*>')
number_re=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
counts=collections.Counter()
rewrite_by_rank={x['continuationRank']:x for x in rewrites}
for row in ledger:
    k=(row['continuationRank'],row['locale']); src=source_by[k]; p=primary_by[k]; b=blind_by[k]
    for field in ('sourceId','remainingQueueRank','source','sourceSha256','currentTarget','currentTargetSha256','catalogKey','catalogPath','catalogFileSha256','catalogGitBlob','callerContextSha256','callerRefs'):
        require(row[field]==src[field],f'source/current/caller pin mismatch {k} {field}')
    require(row['primaryDisposition']==p['disposition'] and row['primaryCandidateTarget']==p['target'],f'primary linkage {k}')
    require(row['blindDisposition']==b['disposition'] and row['blindCandidateTarget']==b['proposedTarget'],f'blind linkage {k}')
    disp=row['disposition']; require(disp in DISPOSITIONS,'unknown cross disposition '+str(k)); counts[disp]+=1
    selected_source=row.get('selectedSource')
    require(isinstance(selected_source,str),'selected source missing '+str(k))
    require(row.get('selectedSourceSha256')==sha(selected_source.encode('utf-8')),'selected source hash '+str(k))
    if row['continuationRank'] in rewrite_by_rank:
        rw=rewrite_by_rank[row['continuationRank']]
        require(selected_source==rw['proposedSource'],'source rewrite link '+str(k))
        require(row['sourceRewriteId']==f"W74-R{row['continuationRank']}",'source rewrite id '+str(k))
    else:
        require(selected_source==src['source'],'unexpected source rewrite '+str(k))
    if disp=='hold-text-free':
        forbidden={'source','currentTarget','selectedSource','selectedTarget','primaryCandidateTarget','blindCandidateTarget'}
        require(not (forbidden & row.keys()),'held row contains text '+str(k))
        continue
    target=row.get('selectedTarget')
    require(isinstance(target,str) and target,'selected target missing '+str(k))
    require(row.get('selectedTargetSha256')==sha(target.encode('utf-8')),'selected target hash '+str(k))
    require(collections.Counter(placeholder_re.findall(selected_source))==collections.Counter(placeholder_re.findall(target)),'placeholder mismatch '+str(k))
    require(collections.Counter(tag_re.findall(selected_source))==collections.Counter(tag_re.findall(target)),'markup mismatch '+str(k))
    require(collections.Counter(number_re.findall(selected_source))==collections.Counter(number_re.findall(target)),'numeric token mismatch '+str(k))
    require(all(lit in target for lit in src['sourceProtectedLiterals']),'protected literal missing '+str(k))
    require(row['placeholderEvidence']==src['placeholderEvidence'] and row['markupEvidence']==src['markupEvidence'],'input token evidence mismatch '+str(k))
    if disp=='accept-current': require(target==src['currentTarget'],'accept-current changed target '+str(k))
    if disp=='accept-current': require(row['selectedFrom']=='current','accept-current provenance '+str(k))
    if disp=='select-update':
        require(target!=src['currentTarget'],'selected update is unchanged '+str(k))
        if row['selectedFrom']=='primary': require(target==p['target'],'selected primary target mismatch '+str(k))
        elif row['selectedFrom']=='blind': require(target==b['proposedTarget'],'selected blind target mismatch '+str(k))
        elif row['selectedFrom']!='cross': require(False,'unknown selected update provenance '+str(k))
count_values={d:counts[d] for d in DISPOSITIONS}
require(count_values=={'accept-current':206,'select-update':94,'hold-text-free':0},'cross disposition counts')
require(len(updates)==94 and [(r['continuationRank'],r['locale']) for r in updates]==[(r['continuationRank'],r['locale']) for r in ledger if r['disposition']=='select-update'],'selected update subset/order')
require(len(holds)==0,'unexpected holds')
cross_by={(r['continuationRank'],r['locale']):r for r in custom_rows}
cross_actual={(r['continuationRank'],r['locale']):r for r in ledger if r['disposition']=='select-update' and r['selectedFrom']=='cross'}
require(len(custom_rows)==8 and set(cross_by)==set(cross_actual),'cross-authored adjudication inventory')
for key,r in cross_actual.items():
    c=cross_by[key]
    for field in ('sourceId','source','sourceSha256','currentTarget','currentTargetSha256','selectedSource','selectedSourceSha256','selectedTarget','selectedTargetSha256','rationale','callerContextSha256'):
        require(c[field]==r[field],f'cross-authored selection linkage {key} {field}')
require(len(rewrites)==2 and {x['continuationRank'] for x in rewrites}=={732,750},'source rewrite coverage')
for rw in rewrites:
    expected=[r for r in ledger if r['continuationRank']==rw['continuationRank']]
    require(len(expected)==12 and rw['selectedTranslations']=={r['locale']:r['selectedTarget'] for r in expected},'source rewrite locale coverage')
    require(rw['currentSourceSha256']==sha(rw['currentSource'].encode('utf-8')) and rw['proposedSourceSha256']==sha(rw['proposedSource'].encode('utf-8')),'source rewrite hashes')
require(summary['head']==HEAD and summary['tree']==TREE,'summary pin')
require(summary['counts']==count_values,'summary counts')
require(summary['crossCustomAdjudicationCount']==len(custom_rows),'summary cross-authored count')
require(summary['crossVerifier']=='PASS','summary verifier flag')
require(summary['livePrReattestationAfterReview']=='PASS','summary live PR reattestation')
require(summary['nativeSpeakerApproval'] is False and summary['browserReviewClaimed'] is False,'unsupported review claim')

# Verify this bundle's checksum manifest. It excludes itself to avoid recursion.
manifest=ROOT/'OUTPUT-SHA256SUMS.txt'
entries={}
for line in manifest.read_text(encoding='utf-8').splitlines():
    if not line.strip(): continue
    digest,rel=line.split('  ',1)
    require(rel not in entries,'duplicate output checksum '+rel)
    path=(ROOT/rel).resolve()
    require(path.is_relative_to(ROOT.resolve()) and path.is_file(),'output checksum path '+rel)
    require(sha(path.read_bytes())==digest,'output checksum mismatch '+rel)
    entries[rel]=digest
actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p!=manifest}
require(set(entries)==actual,'cross output checksum inventory')
print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'cells':len(ledger),'counts':{d:counts[d] for d in DISPOSITIONS},'sourceRewrites':len(rewrites),'candidateFreeChecksums':'PASS','primaryChecksums':'PASS','blindChecksums':'PASS','placeholdersMarkupNumbersProtectedLiterals':'PASS','outputChecksums':len(entries)},sort_keys=True))
