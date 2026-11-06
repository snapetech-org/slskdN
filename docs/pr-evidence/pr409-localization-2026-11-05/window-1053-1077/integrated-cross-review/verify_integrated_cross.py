from __future__ import annotations
import collections, hashlib, json, re, unicodedata
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parent.parent
INPUTS={
 'candidate-free':ROOT/'candidate-free',
 'primary':ROOT/'primary-review',
 'blind':ROOT/'blind-review',
}
HEAD='ba692c15ca54942108cc9da37757f585969e6173'
TREE='27c09a8fe24030f5bb0995d809794a9e4829dc64'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
TEXT_KEYS={'source','sourceText','target','currentTarget','primaryProposal','proposedTarget','blindReviewTarget','reviewTarget','reviewCandidateTarget','actualValue','expectedValue'}

def fail(msg): raise SystemExit('FAIL: '+msg)
def sha(data): return hashlib.sha256(data).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def jread(p): return json.loads(p.read_text(encoding='utf-8'))
def jlread(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]

def checksum_inventory(directory, allow_self=False):
    checksum=directory/'SHA256SUMS.txt'
    if not checksum.is_file(): fail('missing output checksum file')
    expected={}
    for line in checksum.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        parts=line.split('  ',1)
        if len(parts)!=2: fail('malformed checksum line '+str(directory))
        digest,name=parts
        if name in expected: fail('duplicate checksum path '+name)
        path=Path(name)
        if path.is_absolute() or '..' in path.parts: fail('unsafe checksum path '+name)
        target=directory/name
        if not target.is_file() or sha(target.read_bytes())!=digest: fail('checksum mismatch '+str(target))
        expected[name]=digest
    actual={p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    if actual!=set(expected): fail('checksum coverage mismatch '+str(directory))
    return expected

def verify_external_packet(directory):
    expected={}
    for line in (directory/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        digest,name=line.split('  ',1)
        if name in expected or not (directory/name).is_file(): fail('input checksum list inventory '+name)
        if sha((directory/name).read_bytes())!=digest: fail('input checksum mismatch '+str(directory/name))
        expected[name]=digest
    actual={p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    if actual!=set(expected): fail('input checksum coverage mismatch '+str(directory))
    return expected

def token_audit(source,target):
    ph=lambda s:collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s))
    tags=lambda s:collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',s))
    nums=lambda s:[''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in t) for t in re.findall(r'\d+',s)]
    def icu(s):
        found=[]
        for m in re.finditer(r'\{\s*[A-Za-z_][A-Za-z0-9_]*\s*,\s*(?:plural|select|selectordinal)\s*,',s):
            depth=0; end=None
            for i in range(m.start(),len(s)):
                if s[i]=='{': depth+=1
                elif s[i]=='}':
                    depth-=1
                    if depth==0: end=i+1; break
            found.append(s[m.start():end] if end else s[m.start():])
        return collections.Counter(found)
    protected=lambda s:sorted(set(re.findall(r'\b[A-Z][A-Z0-9]{1,}\b',s))|{x for x in ('slskdN','PodCore','Wishlist','soulfind','FFmpeg','Lidarr') if x in s})
    special=['FPS','FTP','IP','Mesh','Soulseek','YAML','NzbGet','KeepHistory','PodCore','slskdN']
    explicit=[x for x in special if x in source]
    if '#' in source: explicit.append('#')
    explicit += [x for x in ('flac','mp3','wav','m4a') if re.search(r'\b'+x+r'\b',source)]
    sp,tp=ph(source),ph(target); st,tt=tags(source),tags(target); sn,tn=nums(source),nums(target)
    si,ti=icu(source),icu(target); sl,tl=protected(source),protected(target)
    return {
      'placeholders':{'source':sorted(sp.elements()),'target':sorted(tp.elements()),'matches':sp==tp},
      'icu':{'source':sorted(si.elements()),'target':sorted(ti.elements()),'matches':si==ti},
      'markup':{'source':sorted(st.elements()),'target':sorted(tt.elements()),'matches':st==tt},
      'numbers':{'source':sn,'target':tn,'sourcePreserved':all(tn.count(x)>=n for x,n in collections.Counter(sn).items())},
      'protectedLiterals':{'source':sl,'target':tl,'missing':[x for x in sl if x not in target]},
      'explicitDomainLiterals':{'source':list(dict.fromkeys(explicit)),'missing':[x for x in dict.fromkeys(explicit) if x not in target]},
    }

def main():
    manifest=jread(OUT/'manifest.json')
    summary=jread(OUT/'summary.json')
    if (manifest.get('head'),manifest.get('tree'))!=(HEAD,TREE): fail('output head/tree pin')
    if manifest.get('nativeSpeakerApproval') is not False: fail('native approval flag')
    out_sums=checksum_inventory(OUT)
    listed={}
    for line in (OUT/'INPUT_SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        digest,name=line.split('  ',1)
        if name in listed: fail('duplicate input file checksum '+name)
        listed[name]=digest
    actual={}
    for label,directory in INPUTS.items():
        files=verify_external_packet(directory)
        for rel in files:
            name=label+'/'+rel
            actual[name]=sha((directory/rel).read_bytes())
        actual[label+'/SHA256SUMS.txt']=sha((directory/'SHA256SUMS.txt').read_bytes())
        info=manifest['inputPackets'][label]
        if info['path']!=directory.relative_to(ROOT).as_posix() or info['fileCount']!=listed_for(files)+1:
            fail('input packet path/count mismatch '+label)
        if info['sha256SumsFileSha256']!=sha((directory/'SHA256SUMS.txt').read_bytes()):
            fail('input checksum-list pin '+label)
    if listed!=actual: fail('full input checksum inventory mismatch')
    for label,directory in INPUTS.items():
        if sha((directory/'manifest.json').read_bytes())!=manifest['inputPackets'][label]['manifestSha256']:
            fail('input manifest pin '+label)

    cf=INPUTS['candidate-free']; pp=INPUTS['primary']; br=INPUTS['blind']
    cfm=jread(cf/'manifest.json'); ps=jread(pp/'summary.json'); bm=jread(br/'manifest.json')
    if (cfm.get('head'),cfm.get('tree'))!=(HEAD,TREE): fail('candidate-free head/tree')
    if (ps.get('head'),ps.get('tree'))!=(HEAD,TREE): fail('primary head/tree')
    if (bm.get('head'),bm.get('tree'))!=(HEAD,TREE): fail('blind head/tree')
    if cfm.get('proposedTargetsIncluded') is not False or cfm.get('reviewDecisionsIncluded') is not False:
        fail('candidate-free source packet has proposal data')

    for name,source in [
      ('source-current-cells.jsonl',cf/'source-current-cells.jsonl'),
      ('caller-contexts.jsonl',cf/'caller-contexts.jsonl'),
      ('prior-active-holds-hash-only.jsonl',cf/'prior-held-cell-reattestation-hash-only.jsonl'),
      ('current-window-holds-hash-only.jsonl',cf/'window-holds-hash-only.jsonl'),
      ('prior-hold-resolution-history-hash-only.jsonl',cf/'prior-hold-resolution-history-hash-only.jsonl')]:
        if (OUT/name).read_bytes()!=source.read_bytes(): fail('byte-preserved file mismatch '+name)
    prior=(OUT/'prior-active-holds-hash-only.jsonl').read_bytes()
    current=(OUT/'current-window-holds-hash-only.jsonl').read_bytes()
    if prior!=(pp/'prior-active-holds-hash-only.jsonl').read_bytes() or prior!=(br/'prior-active-holds-reattestation-hash-only.jsonl').read_bytes():
        fail('433 prior holds not byte-identical across packets')
    if current!=(pp/'current-window-holds-hash-only.jsonl').read_bytes() or current!=(br/'window-callerless-holds-hash-only.jsonl').read_bytes():
        fail('24 current holds not byte-identical across packets')

    source_rows=jlread(cf/'source-current-cells.jsonl')
    primary=jlread(pp/'primary-review-ledger.jsonl')
    blind=jlread(br/'blind-review-ledger.jsonl')
    ledger=jlread(OUT/'integrated-cross-review-ledger.jsonl')
    targets=jlread(OUT/'integrated-target-hashes.jsonl')
    contexts=jlread(OUT/'caller-contexts.jsonl')
    if not (len(source_rows)==len(primary)==len(blind)==len(ledger)==len(targets)):
        fail('row coverage length')
    if len(source_rows)!=300 or len(contexts)!=25: fail('coverage cardinality')
    if contexts!=(jlread(cf/'caller-contexts.jsonl')): fail('caller context copy rows')
    cmap={x['sourceId']:x for x in contexts}
    counts=collections.Counter(); resolutions=collections.Counter(); audit_count=0; holds=[]
    required_text_free={'source','currentTarget','target','primaryProposal','blindReviewTarget','reviewCandidateTarget'}
    for i,(c,p,b,r,h) in enumerate(zip(source_rows,primary,blind,ledger,targets)):
        key=(c['continuationRank'],c['locale'])
        if (r.get('continuationRank'),r.get('locale'))!=key or (h.get('continuationRank'),h.get('locale'))!=key:
            fail('cell order/identity '+str(key))
        if (r.get('head'),r.get('tree'),p.get('head'),p.get('tree'),b.get('head'),b.get('tree'),h.get('head'),h.get('tree'))!=(HEAD,TREE,HEAD,TREE,HEAD,TREE,HEAD,TREE):
            fail('cell pin '+str(key))
        for field in ('remainingQueueRank','sourceId','sourceIdSha256','sourceSha256','locale','callerContextSha256','currentTargetSha256'):
            if r.get(field)!=c.get(field): fail('candidate-free identity mismatch '+str(key)+' '+field)
        ctx=cmap[c['sourceId']]
        if r.get('callerBacked')!=(ctx['productionCallerCount']>0) or r.get('callerCount')!=ctx['productionCallerCount']:
            fail('caller count '+str(key))
        if r.get('callerContextSha256')!=ctx['callerContextSha256']: fail('caller context hash '+str(key))
        if p.get('sourceId')!=c.get('sourceId') or b.get('sourceId')!=c.get('sourceId'): fail('review identity '+str(key))
        if (r.get('primaryDecision'),r.get('primaryProposalIncluded'),r.get('primaryProposalSha256'))!=(p.get('decision'),p.get('proposalIncluded'),p.get('proposedTargetSha256')):
            fail('primary proposal pin '+str(key))
        if (r.get('blindDisposition'),r.get('blindIssueCodes'),r.get('blindReviewTargetSha256'),r.get('blindReviewerSuggestionSha256'))!=(b.get('disposition'),b.get('issueCodes'),b.get('reviewTargetSha256'),b.get('reviewerSuggestionSha256')):
            fail('blind review pin '+str(key))
        if (h.get('head'),h.get('tree'),h.get('sourceSha256'),h.get('currentTargetSha256'),h.get('targetSha256'),h.get('decision'))!=(HEAD,TREE,c['sourceSha256'],c['currentTargetSha256'],r.get('targetSha256'),r.get('decision')):
            fail('target hash manifest row '+str(key))
        if not ctx['productionCallerCount']:
            for field in required_text_free:
                if field in r: fail('callerless text disclosure '+str(key)+' '+field)
            if r.get('sourceTextIncluded') is not False or r.get('currentTargetTextIncluded') is not False or r.get('targetTextIncluded') is not False:
                fail('callerless text flag '+str(key))
            if r.get('decision')!='hold-hash-only' or r.get('targetSha256')!=c.get('currentTargetSha256'):
                fail('callerless disposition/hash '+str(key))
            if h.get('targetTextIncluded') is not False or h.get('sourceId') is not None:
                fail('callerless target-hash disclosure '+str(key))
            if any(k in r for k in ('tokenAudit',)) and r['tokenAudit'] is not None: fail('callerless token text')
            holds.append((c['sourceIdSha256'],c['sourceSha256'],c['locale'],c['currentTargetSha256']))
            counts['hold-hash-only']+=1
            continue

        if not r.get('sourceTextIncluded') or not r.get('currentTargetTextIncluded') or not r.get('targetTextIncluded'):
            fail('caller-backed text flags '+str(key))
        if r.get('source')!=c.get('source') or r.get('currentTarget')!=c.get('currentTarget'): fail('source/current text mismatch '+str(key))
        if tsha(r['source'])!=r['sourceSha256'] or tsha(r['currentTarget'])!=r['currentTargetSha256']: fail('source/current digest '+str(key))
        if r.get('primaryProposal')!=p.get('proposedTarget'): fail('primary proposal text mismatch '+str(key))
        if r.get('blindReviewTarget')!=b.get('reviewTarget'): fail('blind target text mismatch '+str(key))
        if r.get('callerReferences')!=b.get('callerReferences'): fail('caller reference pins '+str(key))
        if not isinstance(r.get('target'),str) or tsha(r['target'])!=r.get('targetSha256'): fail('integrated target digest '+str(key))
        if h.get('targetTextIncluded') is not False or 'target' in h: fail('hash-only target file includes text '+str(key))
        if r.get('decision') not in ('revise','retain-current','review'): fail('caller-backed decision '+str(key))
        if r['decision']=='retain-current' and r['target']!=r['currentTarget']: fail('retain target mismatch '+str(key))
        if r['decision']=='revise' and r['target']==r['currentTarget']: fail('revise does not change target '+str(key))
        if r['decision']=='review' and (r['target']!=r['currentTarget'] or r.get('confidence')!='low' or not r.get('unresolvedLowConfidence')):
            fail('review hold mismatch '+str(key))
        if r.get('unresolvedLowConfidence')!=(r['decision']=='review'): fail('unresolved flag '+str(key))
        audit=token_audit(r['source'],r['target'])
        if audit!=r.get('tokenAudit'): fail('token audit mismatch '+str(key))
        good=(audit['placeholders']['matches'] and audit['icu']['matches'] and audit['markup']['matches']
          and audit['numbers']['sourcePreserved'] and not audit['protectedLiterals']['missing']
          and not audit['explicitDomainLiterals']['missing'])
        if not good or r.get('tokenChecksPass') is not True: fail('token/protected content loss '+str(key))
        audit_count+=1; counts[r['decision']]+=1
        if r['decision']=='review':
            if r.get('unresolvedReason')!=r.get('rationale'): fail('review reason')
            resolutions['pending-low-confidence-review']+=1
        else: resolutions[r.get('proposalResolution')]+=1

    # Hold files encode the exact 24 callerless cells and the 433 prior active holds.
    prior_rows=jlread(OUT/'prior-active-holds-hash-only.jsonl')
    current_rows=jlread(OUT/'current-window-holds-hash-only.jsonl')
    if len(prior_rows)!=433 or len(current_rows)!=24: fail('hold row counts')
    if any(k in row for row in prior_rows+current_rows for k in TEXT_KEYS): fail('hash-only hold text disclosure')
    input_hold_set={(x['sourceIdSha256'],x['sourceSha256'],x['locale'],x['currentTargetSha256']) for x in current_rows}
    if set(holds)!=input_hold_set: fail('callerless cells versus hold file')
    if summary.get('integratedDispositions')!={'revise':54,'retain-current':214,'review-low-confidence':8,'hold-hash-only':24}:
        fail('summary disposition counts')
    if counts!={'revise':54,'retain-current':214,'review':8,'hold-hash-only':24}:
        fail('ledger disposition counts '+str(counts))
    if audit_count!=276: fail('caller-backed token audit coverage')
    if summary.get('primaryProposalResolutionCounts')!=dict(sorted(resolutions.items())):
        fail('proposal resolution summary counts')
    unresolved=jlread(OUT/'unresolved-low-confidence-cells.jsonl')
    if len(unresolved)!=8: fail('unresolved row count')
    expected={(x['continuationRank'],x['locale']) for x in ledger if x['decision']=='review'}
    if {(x['continuationRank'],x['locale']) for x in unresolved}!=expected: fail('unresolved cell list')
    boundary=ps.get('nextBoundary')
    if summary.get('nextBoundary')!=boundary or manifest.get('nextBoundary')!=boundary or bm.get('nextBoundary')!=boundary:
        fail('next boundary')
    if summary.get('nativeSpeakerApproval') is not False: fail('native-speaker caveat')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'cells':len(ledger),
      'revisedTargets':counts['revise'],'retainedTargets':counts['retain-current'],
      'lowConfidenceReviewHolds':counts['review'],'callerlessHashOnlyHolds':counts['hold-hash-only'],
      'priorActiveHoldsByteIdentical':len(prior_rows),'callerBackedTokenAudits':audit_count,
      'inputFilesChecksumVerified':len(listed),'outputChecksumEntries':len(out_sums),
      'outputChecksumListSha256':sha((OUT/'SHA256SUMS.txt').read_bytes()),
      'nextBoundary':boundary},ensure_ascii=False,indent=2))

def listed_for(files):
    return len(files)

if __name__=='__main__': main()
