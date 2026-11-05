#!/usr/bin/env python3
"""Verify the sealed cross-review packet and its pinned upstream evidence."""
from __future__ import annotations
import collections, hashlib, json, re, subprocess, sys, unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parent
INPUT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w1003-1027-20261105')
CAND=INPUT/'candidate-free'; PRIMARY=INPUT/'primary-review'; BLIND=INPUT/'blind-review'
WORKTREE=Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/slskdn-w978')
HEAD='8c752c49281418fdd96341ed46f5c321627b625f'
TREE='b930b0d82679e843849e54456f3250e422c4682c'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

def need(ok,msg):
    if not ok: raise SystemExit('FAIL: '+msg)
def sha(data): return hashlib.sha256(data).hexdigest()
def fsha(path): return sha(path.read_bytes())
def readj(path): return json.loads(path.read_text(encoding='utf-8'))
def readjl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def token_data(source,target):
    placeholders=lambda s:collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s))
    tags=lambda s:collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',s))
    nums=lambda s:[''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in t) for t in re.findall(r'\d+',s)]
    protected=lambda s:sorted(set(re.findall(r'\b[A-Z][A-Z0-9]{1,}\b',s))|{x for x in ('slskdN','PodCore','Wishlist','soulfind','FFmpeg','Lidarr') if x in s})
    sp,tp=placeholders(source),placeholders(target); st,tt=tags(source),tags(target); sn,tn=nums(source),nums(target); sl=protected(source)
    missing=[x for x in sl if x not in target]
    return {'placeholderParity':sp==tp,'markupParity':st==tt,
      'numericTokensPreserved':all(tn.count(x)>=n for x,n in collections.Counter(sn).items()),
      'missingProtectedLiterals':missing,'protectedLiteralsPreserved':not missing}
def token_ok(t): return all(t[k] for k in ('placeholderParity','markupParity','numericTokensPreserved','protectedLiteralsPreserved'))

def verify_sums(directory):
    listed={}
    for line in (directory/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1); need(n not in listed and fsha(directory/n)==h,'checksum '+n); listed[n]=h
    actual={p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    need(actual==set(listed),'checksum inventory '+str(directory))
    return listed

# Verify exact-head source and upstream review packets with their own verifiers.
subprocess.run([sys.executable,'-B',str(CAND/'verify_candidate_free.py'),str(WORKTREE)],check=True)
subprocess.run([sys.executable,'-B',str(PRIMARY/'verify_primary.py'),str(WORKTREE)],check=True)
blind_sums=verify_sums(BLIND)
need((WORKTREE/'src').exists(),'exact worktree path')
need(subprocess.check_output(['git','-C',str(WORKTREE),'rev-parse','HEAD'],text=True).strip()==HEAD,'exact worktree head')
need(subprocess.check_output(['git','-C',str(WORKTREE),'rev-parse','HEAD^{tree}'],text=True).strip()==TREE,'exact worktree tree')
need((BLIND/'input-SHA256SUMS.txt').read_bytes()==(CAND/'SHA256SUMS.txt').read_bytes(),'blind candidate-free checksum copy')
bs=readj(BLIND/'summary.json')
need(bs['inputManifestSha256']==fsha(CAND/'manifest.json') and bs['inputChecksumsFileSha256']==fsha(CAND/'SHA256SUMS.txt'),'blind input pin')

sums=verify_sums(ROOT)
manifest=readj(ROOT/'manifest.json'); summary=readj(ROOT/'summary.json')
need((manifest['head'],manifest['tree'],manifest['window'])==(HEAD,TREE,'W85'),'manifest identity')
need(manifest['blindReviewUsed'] is True and manifest['crossReviewUsed'] is True and manifest['rootAdjudicationPerformed'] is False,'manifest root flags')
need(manifest['catalogsEdited'] is False and manifest['translationsApplied'] is False,'manifest no-application flags')
files={x['path']:x for x in manifest['files']}
need(set(files)==set(sums)-{'manifest.json'},'manifest file inventory')
for name,rec in files.items():
    need(rec['bytes']==(ROOT/name).stat().st_size and rec['sha256']==fsha(ROOT/name),'manifest content pin '+name)
need(manifest['candidateFreeInputManifestSha256']==fsha(CAND/'manifest.json'),'manifest candidate input pin')
need(manifest['primaryInputManifestSha256']==fsha(PRIMARY/'manifest.json'),'manifest primary input pin')
need(manifest['blindInputChecksumsSha256']==fsha(BLIND/'SHA256SUMS.txt'),'manifest blind input pin')

cells=readjl(CAND/'source-current-cells.jsonl')
pr=readjl(PRIMARY/'primary-review.jsonl'); bl=readjl(BLIND/'review-cells.jsonl')
cross=readjl(ROOT/'cross-review.jsonl')
input_cells={(r['continuationRank'],r['locale']):r for r in cells}
primary={(r['continuationRank'],r['locale']):r for r in pr}
blind={(r['continuationRank'],r['locale']):r for r in bl}
need(len(input_cells)==len(cells)==300 and len(primary)==len(pr)==288 and len(blind)==len(bl)==300,'input row uniqueness/counts')
expected=[(rank,locale) for rank in range(1003,1028) for locale in LOCALES]
need([(r['continuationRank'],r['locale']) for r in cross]==expected,'cross cell order/coverage')
need(len(cross)==300,'cross cell count')
corrections=collections.Counter(); baseline_mismatches=collections.Counter()
primary_keys={k for k,v in primary.items() if v['disposition']=='correction'}
blind_keys={k for k,v in blind.items() if v['decision']=='proposal'}
need(len(primary_keys)==57 and len(blind_keys)==59,'proposal input counts')

for row in cross:
    key=(row['continuationRank'],row['locale']); c=input_cells[key]; b=blind[key]; p=primary.get(key)
    for field in ('sourceId','sourceIdSha256','sourceSha256','catalogPath','catalogFileSha256','catalogGitBlob','callerCount','callerContextSha256','candidateFreeHold'):
        need(row[field]==c[field],f'cell input pin {key} {field}')
    need(row['head']==HEAD and row['tree']==TREE and row['crossReviewUsed'] is True and row['blindReviewUsed'] is True and row['rootAdjudicationPerformed'] is False,'cell flags '+str(key))
    if c['callerCount']==0:
        need(key not in primary and b['decision']=='hold','hold input state '+str(key))
        need(row['crossDisposition']=='hash-only-hold' and row['holdReasonClass']=='no-pinned-production-localization-caller','hold disposition '+str(key))
        need(row['sourceTextIncluded'] is False and row['currentTargetTextIncluded'] is False and row['primaryCandidateTargetTextIncluded'] is False and row['blindProposalTargetTextIncluded'] is False and row['crossTargetTextIncluded'] is False,'hold text flags '+str(key))
        forbidden={'source','currentTarget','primaryCandidateTarget','blindProposalTarget','crossTarget','crossRationale','primaryRationale','blindRationale','baselineTokenEvidence','effectiveTargetTokenCheck'}
        need(not (set(row)&forbidden),'hold text-free schema '+str(key))
        need(row['sourceSha256']==c['sourceSha256'] and row['currentTargetSha256']==c['currentTargetSha256'],'hold hash pins '+str(key))
        corrections['hash-only-hold']+=1
        continue
    need(p is not None and b['decision'] in ('retain','proposal'),'caller-backed inputs '+str(key))
    need(row['sourceTextIncluded'] is True and row['currentTargetTextIncluded'] is True,'caller-backed text flags '+str(key))
    need(row['source']==c['source'] and row['currentTarget']==c['currentTarget'],'caller-backed text pins '+str(key))
    need(sha(row['source'].encode())==c['sourceSha256'] and sha(row['currentTarget'].encode())==c['currentTargetSha256'],'caller-backed text hashes '+str(key))
    need(row['baselineTokenEvidenceSha256']==c['tokenEvidenceSha256'] and row['baselineTokenEvidence']==c['tokenEvidence'],'baseline token pin '+str(key))
    need(row['baselineTokenChecksPass']==c['tokenChecksPass'],'baseline token status pin '+str(key))
    if not c['tokenChecksPass']:
        current_ev=token_data(c['source'],c['currentTarget'])
        if not current_ev['placeholderParity']: baseline_mismatches['placeholder']+=1
        if not current_ev['markupParity']: baseline_mismatches['markup']+=1
        if not current_ev['numericTokensPreserved']: baseline_mismatches['numeric']+=1
        if current_ev['missingProtectedLiterals']: baseline_mismatches['protectedLiteral']+=1
    need(row['primaryDisposition']==p['disposition'],'primary disposition pin '+str(key))
    expected_pc=p.get('candidateTarget') if p['disposition']=='correction' else None
    need(row['primaryCandidateTarget']==expected_pc,'primary candidate text pin '+str(key))
    need(row['primaryCandidateTargetTextIncluded']==(expected_pc is not None),'primary candidate flag '+str(key))
    if expected_pc is not None:
        need(row['primaryCandidateTargetSha256']==p['candidateTargetSha256']==sha(expected_pc.encode()),'primary candidate hash '+str(key))
        need(token_ok(token_data(c['source'],expected_pc)),'primary candidate token check '+str(key))
    need(row['blindDecision']==b['decision'],'blind decision pin '+str(key))
    expected_bt=b.get('proposedTarget') if b['decision']=='proposal' else None
    need(row['blindProposalTarget']==expected_bt,'blind proposal text pin '+str(key))
    need(row['blindProposalTargetTextIncluded']==(expected_bt is not None),'blind proposal flag '+str(key))
    if expected_bt is not None:
        need(row['blindProposalTargetSha256']==sha(expected_bt.encode()),'blind proposal hash '+str(key))
        need(b['proposedTokenChecksPass'] and token_ok(token_data(c['source'],expected_bt)),'blind proposal token check '+str(key))
    expected_disp='correction' if row['crossTarget'] is not None else 'accept-current'
    need(row['crossDisposition']==expected_disp,'cross disposition-target relation '+str(key))
    effective=row['crossTarget'] if expected_disp=='correction' else c['currentTarget']
    need(row['effectiveTargetSha256']==sha(effective.encode()),'effective target hash '+str(key))
    ev=token_data(c['source'],effective)
    need(row['effectiveTargetTokenCheck']==ev and token_ok(ev),'effective target token evidence '+str(key))
    expected_literals=[x for x in ('ContentID','YouTube') if x in c['source']]
    literal_checks=[{'literal':x,'preserved':x in effective} for x in expected_literals]
    need(row['additionalLiteralChecks']==literal_checks and all(x['preserved'] for x in literal_checks),'case-sensitive product literals '+str(key))
    if expected_disp=='correction':
        need(row['crossTargetTextIncluded'] is True and row['crossTargetSha256']==sha(row['crossTarget'].encode()),'cross target text/hash '+str(key))
        corrections['correction']+=1
    else:
        need(row['crossTargetTextIncluded'] is False and row['crossTarget'] is None and row['crossTargetSha256'] is None,'retain target omission '+str(key))
        corrections['accept-current']+=1

need(baseline_mismatches==collections.Counter({'protectedLiteral':1}),'single protected FTP baseline mismatch')
need([(r['continuationRank'],r['locale']) for r in cross if r['callerCount']==0]==[(1024,l) for l in LOCALES],'rank-1024 hold coverage')
need(sum(1 for r in cross if r['callerCount']>0 and not r['baselineTokenChecksPass'])==1,'baseline mismatch cell count')
hi=next(r for r in cross if r['continuationRank']==1008 and r['locale']=='hi')
need(hi['crossDisposition']=='correction' and 'FTP' in hi['crossTarget'] and hi['effectiveTargetTokenCheck']['protectedLiteralsPreserved'],'Hindi FTP correction')
need(corrections==collections.Counter({'correction':71,'accept-current':217,'hash-only-hold':12}),'cross decision totals')
need(len(primary_keys|blind_keys)==71 and len(primary_keys&blind_keys)==45 and len(primary_keys-blind_keys)==12 and len(blind_keys-primary_keys)==14,'proposal union arithmetic')

active_prior=readjl(ROOT/'prior-active-holds-hash-only.jsonl')
ph=readjl(CAND/'prior-held-cell-reattestation-hash-only.jsonl')
wh=[r for r in readjl(CAND/'window-holds-hash-only.jsonl') if r.get('window')=='W953-W977']
need(active_prior==ph+wh and len(active_prior)==409,'previous active hold preservation')
for r in active_prior:
    need(r.get('sourceTextIncluded') is False and r.get('targetTextIncluded') is False,'prior hold text redaction')
    need(not (set(r)&{'source','currentTarget','target','candidateTarget','proposalTarget'}),'prior hold text-free schema')
need(len(active_prior)+sum(1 for r in cross if r['crossDisposition']=='hash-only-hold')==421,'total active hash-only holds')
need(summary['cellCount']==300 and summary['callerBackedCellCount']==288 and summary['callerlessHashOnlyHoldCellCount']==12,'summary coverage')
need(summary['crossDispositionCounts']==dict(corrections),'summary disposition counts')
need(summary['primaryCorrectionCount']==57 and summary['blindProposalCount']==59 and summary['proposalUnionCellCount']==71,'summary proposal counts')
need(summary['baselineCurrentTokenResults']['mismatchCounts']=={'protectedLiteral':1},'summary baseline mismatch totals')
need(summary['crossSelectedTargetTokenResults']['passingTargets']==288 and summary['crossSelectedTargetTokenResults']['failingTargets']==0,'summary selected-token totals')
need(summary['previousActiveHashOnlyHoldsReattested']==409 and summary['resultingActiveHashOnlyHolds']==421,'summary hold counts')
need(summary['rootFlags']=={'candidateFreeInput':True,'blindReviewUsed':True,'crossReviewUsed':True,'rootAdjudicationPerformed':False,'catalogsEdited':False,'translationsApplied':False,'testsBuildsScansCiRun':False},'summary root flags')
print(json.dumps({'result':'PASS','verifier':'sealed-cross-review','head':HEAD,'tree':TREE,
  'cells':300,'callerBacked':288,'crossCorrections':71,'retainedCurrent':217,'newHashOnlyHolds':12,
  'primaryCandidateTargets':57,'blindProposalTargets':59,'proposalUnionCells':71,
  'baselineTokenMismatch':'Hindi FTP protected literal; corrected target preserves FTP',
  'priorActiveHashOnlyHolds':409,'resultingActiveHashOnlyHolds':421,
  'checksummedFiles':len(sums),'upstreamBlindChecksummedFiles':len(blind_sums)},indent=2))
