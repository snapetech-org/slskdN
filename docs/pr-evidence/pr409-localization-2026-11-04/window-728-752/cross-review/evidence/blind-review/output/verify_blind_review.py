#!/usr/bin/env python3
"""Portable verifier for the slskdN W74 clean-blind review bundle."""
import collections, hashlib, json, re, sys
from pathlib import Path

OUT=Path(__file__).resolve().parent
IN=OUT/'input'
def sha(data): return hashlib.sha256(data).hexdigest()
def readj(path): return json.loads(path.read_text(encoding='utf-8'))
def lines(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def fail(message): raise AssertionError(message)

# Verify the copied candidate-free input and its own checksums.
m=readj(IN/'manifest.json')
if m.get('candidateFree') is not True: fail('input is not marked candidate-free')
if (m.get('head'),m.get('tree')) != ('70e5beffd5cd8d68b8aedffa5c85d16e2cc19b3f','14620c63bee971428fa1cd6cf1f4e944b86056a7'): fail('input pin mismatch')
if m.get('proposedTargetsIncluded') is not False or m.get('reviewDecisionsIncluded') is not False: fail('candidate content included in input manifest')
packet_sums={}
for raw in (IN/'PACKET-SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
    digest,name=raw.split('  ',1)
    packet_sums[name]=digest
    if sha((IN/name).read_bytes()) != digest: fail('input packet checksum mismatch: '+name)
for row in m['files']:
    b=(IN/row['path']).read_bytes()
    if len(b)!=row['bytes'] or sha(b)!=row['sha256']: fail('input manifest mismatch: '+row['path'])
actual_input={p.name for p in IN.iterdir() if p.is_file()}
if actual_input != set(packet_sums)|{'PACKET-SHA256SUMS.txt'}: fail('unexpected or missing file in copied input directory')

cells=lines(IN/'source-current-cells.jsonl')
selection=lines(IN/'source-inventory-selection.jsonl')
ctx=lines(IN/'caller-contexts.jsonl')
if len(cells)!=300 or len(selection)!=25 or len(ctx)!=25: fail('candidate-free input shape mismatch')
bykey={(x['sourceId'],x['locale']):x for x in cells}
if len(bykey)!=300: fail('duplicate input cell')
if sorted(x['continuationRank'] for x in selection)!=list(range(728,753)): fail('source rank range mismatch')
if sorted(x['remainingQueueRank'] for x in selection)!=list(range(628,653)): fail('remaining rank range mismatch')

ledger=lines(OUT/'blind-review-ledger.jsonl')
proposals=lines(OUT/'blind-review-proposals.jsonl')
holds=lines(OUT/'blind-review-holds.jsonl')
if len(ledger)!=300: fail('ledger must have 300 cells')
if len({(x['sourceId'],x['locale']) for x in ledger})!=300: fail('duplicate ledger cell')
if {(x['sourceId'],x['locale']) for x in ledger} != set(bykey): fail('ledger cell coverage mismatch')

placeholder_re=re.compile(r'\{[^{}]+\}')
tag_re=re.compile(r'<[^>]+>')
number_re=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
for r in ledger:
    k=(r['sourceId'],r['locale']); c=bykey[k]
    for f in ('continuationRank','remainingQueueRank','source','sourceSha256','catalogKey','catalogPath','catalogFileSha256','catalogGitBlob','currentTarget','currentTargetSha256','callerContextSha256','callerRefs'):
        if r[f] != c[f]: fail(f'input linkage mismatch for {k}: {f}')
    if sha(r['source'].encode()) != r['sourceSha256']: fail('source hash mismatch: '+str(k))
    if sha(r['currentTarget'].encode()) != r['currentTargetSha256']: fail('target hash mismatch: '+str(k))
    if r['containsCandidate'] is not False: fail('candidate flag set in ledger')
    if r['nativeSpeakerApproval'] is not False: fail('native-speaker approval claimed')
    if r['disposition'] not in ('accept-current','revise-current','hold-text-free'): fail('invalid disposition')
    if r['disposition']=='accept-current' and r['proposedTarget'] is not None: fail('accepted cell has proposal')
    if r['disposition']=='revise-current' and not r['proposedTarget']: fail('revision lacks proposal')
    if r['disposition']=='hold-text-free' and (r['proposedTarget'] is not None or 'currentTarget' in r): fail('hold must be text-free')
    if r['placeholderEvidence'] != c['placeholderEvidence'] or r['markupEvidence'] != c['markupEvidence']: fail('token evidence linkage mismatch')
    if r['sourceNumericTokens'] != c['sourceNumericTokens'] or r['sourceProtectedLiterals'] != c['sourceProtectedLiterals']: fail('protected token linkage mismatch')
    if r['disposition']=='revise-current':
        target=r['proposedTarget']
        if collections.Counter(placeholder_re.findall(r['source'])) != collections.Counter(placeholder_re.findall(target)): fail('placeholder mismatch: '+str(k))
        if collections.Counter(tag_re.findall(r['source'])) != collections.Counter(tag_re.findall(target)): fail('markup mismatch: '+str(k))
        if collections.Counter(number_re.findall(r['source'])) != collections.Counter(number_re.findall(target)): fail('numeric token mismatch: '+str(k))
        if any(lit not in target for lit in r['sourceProtectedLiterals']): fail('protected literal missing: '+str(k))

revised=[r for r in ledger if r['disposition']=='revise-current']
accepted=[r for r in ledger if r['disposition']=='accept-current']
held=[r for r in ledger if r['disposition']=='hold-text-free']
if len(holds)!=len(held): fail('hold file count mismatch')
if any(('currentTarget' in h or 'proposedTarget' in h or 'source' in h) for h in holds): fail('hold file includes text')
pmap={(x['sourceId'],x['locale']):x for x in proposals}
if len(pmap)!=len(proposals) or set(pmap)!={(r['sourceId'],r['locale']) for r in revised}: fail('proposal linkage/count mismatch')
for r in revised:
    p=pmap[(r['sourceId'],r['locale'])]
    for f in ('reviewId','catalogPath','catalogKey','sourceSha256','currentTargetSha256','currentTarget','proposedTarget','issueClass','rationale','callerContextSha256'):
        if p[f]!=r[f]: fail('proposal differs from ledger: '+f)
summary=readj(OUT/'review-summary.json')
counts={'accept-current':len(accepted),'revise-current':len(revised),'hold-text-free':len(held)}
if summary.get('result')!='SEALED' or summary.get('cellsReviewed')!=300 or summary.get('sourcesReviewed')!=25: fail('summary coverage mismatch')
if summary.get('counts')!=counts or summary.get('proposalCount')!=len(proposals) or summary.get('holdCount')!=len(holds): fail('summary disposition mismatch')
if summary.get('nativeSpeakerApproval') is not False or summary.get('browserReviewClaimed') is not False: fail('summary makes unsupported review claim')
for name in ('PR-attestation-before.json','PR-attestation-after.json'):
    a=readj(OUT/name)
    if (a.get('result'),a.get('state'),a.get('draft'),a.get('head'),a.get('tree'),a.get('branchRefOid')) != ('PASS','OPEN',True,'70e5beffd5cd8d68b8aedffa5c85d16e2cc19b3f','14620c63bee971428fa1cd6cf1f4e944b86056a7','70e5beffd5cd8d68b8aedffa5c85d16e2cc19b3f'): fail('PR attestation mismatch: '+name)

# The bundle checksum manifest covers every file except itself.
manifest=OUT/'OUTPUT-SHA256SUMS.txt'
expected={}
for raw in manifest.read_text(encoding='utf-8').splitlines():
    digest,rel=raw.split('  ',1)
    expected[rel]=digest
actual={p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p!=manifest}
if set(expected)!=actual: fail('output checksum manifest file list mismatch')
for rel,digest in expected.items():
    if sha((OUT/rel).read_bytes())!=digest: fail('output checksum mismatch: '+rel)

print(json.dumps({'result':'PASS','pin':summary['reviewedHead'],'tree':summary['reviewedTree'],'cells':len(ledger),'sources':25,'locales':len(summary['locales']),'counts':counts,'proposals':len(proposals),'holds':len(holds),'inputChecksums':len(packet_sums),'outputChecksums':len(expected)},sort_keys=True))

