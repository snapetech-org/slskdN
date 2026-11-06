import json, pathlib, hashlib, shutil, unicodedata, re, collections
OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parent
CF=ROOT/'candidate-free'
PP=ROOT/'primary-review'
BR=ROOT/'blind-review'
HEAD='ba692c15ca54942108cc9da37757f585969e6173'
TREE='27c09a8fe24030f5bb0995d809794a9e4829dc64'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
def jread(p): return json.loads(p.read_text(encoding='utf-8'))
def jlread(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def writej(name,o): (OUT/name).write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def writejl(name,rows): (OUT/name).write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in rows),encoding='utf-8')
def token_audit(source,target):
    def placeholders(s): return collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s))
    def markup(s): return collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',s))
    def numbers(s): return [''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in t) for t in re.findall(r'\d+',s)]
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
    def protected(s):
        return sorted(set(re.findall(r'\b[A-Z][A-Z0-9]{1,}\b',s))|{x for x in ('slskdN','PodCore','Wishlist','soulfind','FFmpeg','Lidarr') if x in s})
    special=['FPS','FTP','IP','Mesh','Soulseek','YAML','NzbGet','KeepHistory','PodCore','slskdN']
    explicit=[x for x in special if x in source]
    if '#' in source: explicit.append('#')
    explicit += [x for x in ('flac','mp3','wav','m4a') if re.search(r'\b'+x+r'\b',source)]
    sp,tp=placeholders(source),placeholders(target); st,tt=markup(source),markup(target)
    sn,tn=numbers(source),numbers(target); si,ti=icu(source),icu(target)
    sl,tl=protected(source),protected(target)
    return {
     'placeholders':{'source':sorted(sp.elements()),'target':sorted(tp.elements()),'matches':sp==tp},
     'icu':{'source':sorted(si.elements()),'target':sorted(ti.elements()),'matches':si==ti},
     'markup':{'source':sorted(st.elements()),'target':sorted(tt.elements()),'matches':st==tt},
     'numbers':{'source':sn,'target':tn,'sourcePreserved':all(tn.count(x)>=n for x,n in collections.Counter(sn).items())},
     'protectedLiterals':{'source':sl,'target':tl,'missing':[x for x in sl if x not in target]},
     'explicitDomainLiterals':{'source':list(dict.fromkeys(explicit)),'missing':[x for x in dict.fromkeys(explicit) if x not in target]},
    }

cells=jlread(CF/'source-current-cells.jsonl')
primary=jlread(PP/'primary-review-ledger.jsonl')
blind=jlread(BR/'blind-review-ledger.jsonl')
contexts=jlread(CF/'caller-contexts.jsonl')
assert len(cells)==len(primary)==len(blind)==300 and len(contexts)==25
pm={(x['continuationRank'],x['locale']):x for x in primary}
bm={(x['continuationRank'],x['locale']):x for x in blind}
cx={x['sourceId']:x for x in contexts}
assert all((x['head'],x['tree'])==(HEAD,TREE) for x in primary+blind)
assert [(x['continuationRank'],x['locale']) for x in cells]==[(x['continuationRank'],x['locale']) for x in primary]
assert [x['locale'] for x in cells[:12]]==LOCALES

reviews={
 (1054,'ar'):'The source names a selected Pod and peer. Current Arabic localizes Pod as a generic group; this packet does not establish the product term used for Pod in Arabic.',
 (1054,'es'):'The source names a selected Pod and peer. Current Spanish uses grupo; the primary proposal uses pod/peer. Confirm the established Spanish product terminology.',
 (1054,'vi'):'The source names a selected Pod and peer. Current Vietnamese uses nhóm; the primary proposal retains Pod/peer. Confirm the established Vietnamese product terminology.',
 (1056,'ar'):'The caller distinguishes a share group from a user collection, while current Arabic uses المجموعة for both. Confirm the established Arabic term for a user-created collection.',
 (1063,'zh-Hans'):'The caller is the empty state on the Collections page. 收藏 can read as favorites; confirm the established Simplified Chinese term for user-created collections.',
 (1063,'zh-Hant'):'The caller is the empty state on the Collections page. 收藏 can read as favorites; confirm the established Traditional Chinese term for user-created collections.',
 (1071,'fr'):'The caller counts stored hash values. hachages may name the hashing operation; confirm the established French term for hash values.',
 (1076,'ar'):'The caller exposes an implicit entry record but no Arabic antecedent. The primary proposal changes feminine agreement to masculine; confirm the intended referent before changing the current form.',
}
accept_primary={
 (1053,'ar'),(1054,'zh-Hans'),(1054,'zh-Hant'),(1058,'vi'),
 (1059,'ar'),(1059,'de'),(1059,'id'),(1059,'ja'),(1059,'zh-Hans'),(1059,'zh-Hant'),
 (1062,'hi'),(1064,'pt-BR'),
 (1066,'ar'),(1066,'hi'),(1066,'id'),(1066,'ja'),(1066,'vi'),(1066,'zh-Hans'),(1066,'zh-Hant'),
 (1069,'es'),(1075,'ja'),(1075,'vi'),(1076,'vi'),
}
reject_primary={
 (1054,'fr'):'The current French already conveys banning, role changes, the selected Pod and peer, and the membership record; the proposed wording is a stylistic variant without a material gain.',
 (1054,'hi'):'The current Hindi already preserves the selected Pod/peer concepts and membership-record instruction; the primary wording is an optional product-term/style variant, not a material correction.',
 (1067,'zh-Hans'):'执行合同 already expresses an execution contract in this status label; the primary 契约 alternative is a terminology preference without a demonstrated semantic improvement.',
 (1067,'zh-Hant'):'執行合約 already expresses an execution contract in this status label; the primary 契約 alternative is a terminology preference without a demonstrated semantic improvement.',
}
refined={(1059,'ja'):'ソース:{provenance}。'}
specific_reasons={
 (1053,'ar'):'The source and Visualizer caller identify imported native presets; the current Arabic says general settings and omits the preset distinction.',
 (1054,'zh-Hans'):'The warning refers to banning members and publishing membership state for selected Pod and peer. 封禁 is more specific than the current 禁止, and 对等节点 identifies the peer as a node.',
 (1054,'zh-Hant'):'The warning refers to banning members and publishing membership state for selected Pod and peer. 封鎖 is more specific than the current 禁止, and 對等節點 identifies the peer as a node.',
 (1058,'vi'):'The caller verifies a descriptor signature and freshness. The current wording says description; bộ mô tả names the technical descriptor object.',
 (1059,'ar'):'The caller passes provenance as {provenance}. Preserve the placeholder and source sentence punctuation.',
 (1059,'de'):'The caller passes provenance as {provenance}. Preserve the placeholder and restore the source final period.',
 (1059,'id'):'The caller passes provenance as {provenance}. Preserve the placeholder and correct colon spacing and final period.',
 (1059,'ja'):'The caller passes provenance as {provenance}. Keep Japanese colon spacing compact, preserve the placeholder, and restore the Japanese sentence stop.',
 (1059,'zh-Hans'):'The caller passes provenance as {provenance}. Preserve the placeholder and use standard full-width Chinese colon punctuation.',
 (1059,'zh-Hant'):'The caller passes provenance as {provenance}. Preserve the placeholder and use standard full-width Chinese colon punctuation.',
 (1062,'hi'):'The Security caller counts tracked IP addresses. Preserve the technical abbreviation IP instead of transliterating it.',
 (1064,'pt-BR'):'The Messaging caller joins or creates a room named with #. Entrar/Criar describes the room action more precisely than Junte-se/crie and preserves #.',
 (1066,'ar'):'The MessagingV2 caller is a matching room-search result list. Explicitly identify Soulseek rooms as chat rooms.',
 (1066,'hi'):'The MessagingV2 caller is a matching room-search result list. Explicitly identify Soulseek rooms as chat rooms.',
 (1066,'id'):'The MessagingV2 caller is a matching room-search result list. Explicitly identify Soulseek rooms as chat rooms.',
 (1066,'ja'):'The MessagingV2 caller is a matching room-search result list. Explicitly identify Soulseek rooms as chat rooms.',
 (1066,'vi'):'The MessagingV2 caller is a matching room-search result list. Replace the awkward suitable-for-a-room wording with matching Soulseek chat rooms.',
 (1066,'zh-Hans'):'The MessagingV2 caller is a matching room-search result list. Explicitly identify Soulseek rooms as chat rooms.',
 (1066,'zh-Hant'):'The MessagingV2 caller is a matching room-search result list. Explicitly identify Soulseek rooms as chat rooms.',
 (1069,'es'):'The tooltip states that FTP uploads occur after downloads complete. Current Spanish can read as uploads of completed downloads; make the timing explicit.',
 (1075,'ja'):'The AdminPolicies caller uses incoming as the inbound direction, and the MediaCore caller counts incoming links. 受信 labels received/inbound data more precisely than 入ってくる.',
 (1075,'vi'):'The AdminPolicies and MediaCore callers use incoming as an inbound direction. Chiều vào states that direction more precisely than đến.',
 (1076,'vi'):'The Mesh Evidence caller lists the entry provenance and then says it is accepted for local use. The concise cục bộ wording fits local use in this policy context.',
}
rows=[]; hashes=[]; unresolved=[]; counts=collections.Counter(); resolutions=collections.Counter()
for inp in cells:
    k=(inp['continuationRank'],inp['locale']); p=pm[k]; b=bm[k]; context=cx[inp['sourceId']]
    backed=context['productionCallerCount']>0
    assert inp['callerCount']==context['productionCallerCount']
    row={
     'head':HEAD,'tree':TREE,'window':'W1053-W1077','continuationRank':inp['continuationRank'],
     'remainingQueueRank':inp['remainingQueueRank'],'sourceId':inp['sourceId'],'sourceIdSha256':inp['sourceIdSha256'],
     'sourceSha256':inp['sourceSha256'],'locale':inp['locale'],'catalogPath':inp['catalogPath'],
     'catalogGitBlob':inp['catalogGitBlob'],'catalogFileSha256':inp['catalogFileSha256'],
     'callerBacked':backed,'callerCount':context['productionCallerCount'],'callerContextSha256':context['callerContextSha256'],
     'primaryDecision':p['decision'],'primaryConfidence':p['confidence'],'primaryProposalIncluded':p['proposalIncluded'],
     'primaryProposalSha256':p['proposedTargetSha256'],'primaryRationale':p['rationale'],
     'blindDisposition':b['disposition'],'blindConfidence':b['confidence'],'blindIssueCodes':b['issueCodes'],
     'blindReviewTargetSha256':b.get('reviewTargetSha256'),'blindReviewerSuggestionSha256':b.get('reviewerSuggestionSha256'),
     'blindRationale':b['rationale'],'nativeSpeakerApproval':False,
    }
    if backed:
        assert inp['sourceTextIncluded'] and inp['currentTargetTextIncluded']
        assert p['source']==b['source']==inp['source'] and p['currentTarget']==b['currentTarget']==inp['currentTarget']
        assert p['callerContextSha256']==b['callerContextSha256']==context['callerContextSha256']
        assert b['reviewTargetTextIncluded'] and isinstance(b['reviewTarget'],str)
        row.update({'source':inp['source'],'sourceTextIncluded':True,'currentTarget':inp['currentTarget'],
          'currentTargetSha256':inp['currentTargetSha256'],'currentTargetTextIncluded':True,
          'callerReferences':b['callerReferences'],'primaryProposal':p['proposedTarget'] if p['proposalIncluded'] else None,
          'blindReviewTarget':b['reviewTarget']})
        if k in reviews:
            decision='review'; target=inp['currentTarget']; confidence='low'; reason=reviews[k]
            candidate=p['proposedTarget'] if p['decision']=='revise' else None
            row['reviewCandidateTarget']=candidate
            row['reviewCandidateTargetSha256']=p['proposedTargetSha256'] if candidate is not None else None
            row['unresolvedLowConfidence']=True; row['unresolvedReason']=reason
            resolution='pending-low-confidence-review'
        elif k in accept_primary:
            assert p['decision']=='revise' and b['disposition']=='retain'
            target=refined.get(k,p['proposedTarget']); decision='revise'; confidence='moderate'
            reason=specific_reasons[k]
            row['reviewCandidateTarget']=None; row['reviewCandidateTargetSha256']=None
            row['unresolvedLowConfidence']=False
            resolution='primary-proposal-refined' if target!=p['proposedTarget'] else 'primary-only-proposal-accepted'
        elif p['decision']=='revise' and b['disposition']=='retain':
            assert k in reject_primary
            target=inp['currentTarget']; decision='retain-current'; confidence='moderate'; reason=reject_primary[k]
            row['reviewCandidateTarget']=None; row['reviewCandidateTargetSha256']=None
            row['unresolvedLowConfidence']=False; resolution='primary-only-proposal-rejected'
        elif b['disposition']=='revise':
            target=b['reviewTarget']; decision='revise'; confidence='moderate'; reason=b['rationale']
            row['reviewCandidateTarget']=None; row['reviewCandidateTargetSha256']=None; row['unresolvedLowConfidence']=False
            if p['decision']=='revise':
                resolution='overlapping-proposals-converged' if target==p['proposedTarget'] else 'overlap-resolved-to-blind-target'
            else: resolution='blind-only-proposal-accepted'
        else:
            target=inp['currentTarget']; decision='retain-current'; confidence='moderate'
            reason='Both reviews retain the current translation; source, exact caller context, and token evidence show no material semantic or technical defect.'
            row['reviewCandidateTarget']=None; row['reviewCandidateTargetSha256']=None
            row['unresolvedLowConfidence']=False; resolution='both-retain-current'
        audit=token_audit(inp['source'],target)
        token_ok=(audit['placeholders']['matches'] and audit['icu']['matches'] and audit['markup']['matches']
          and audit['numbers']['sourcePreserved'] and not audit['protectedLiterals']['missing']
          and not audit['explicitDomainLiterals']['missing'])
        row.update({'decision':decision,'target':target,'targetSha256':tsha(target),'targetTextIncluded':True,
          'confidence':confidence,'rationale':reason,'proposalResolution':resolution,
          'tokenAudit':audit,'tokenChecksPass':token_ok})
        assert token_ok,(k,audit)
        counts[decision]+=1
        if decision=='revise': counts['acceptedTargetChanges']+=1
        if decision=='review':
            unresolved.append({'continuationRank':inp['continuationRank'],'remainingQueueRank':inp['remainingQueueRank'],
             'locale':inp['locale'],'sourceId':inp['sourceId'],'sourceSha256':inp['sourceSha256'],'source':inp['source'],
             'currentTarget':inp['currentTarget'],'currentTargetSha256':inp['currentTargetSha256'],'target':target,
             'targetSha256':tsha(target),'reviewCandidateTarget':candidate,
             'reviewCandidateTargetSha256':p['proposedTargetSha256'] if candidate is not None else None,
             'callerContextSha256':context['callerContextSha256'],'confidence':'low','reason':reason})
    else:
        assert not inp['sourceTextIncluded'] and not inp['currentTargetTextIncluded']
        assert 'source' not in inp and 'currentTarget' not in inp
        assert p['decision']=='hold-hash-only' and not p['proposalIncluded']
        assert b['disposition']=='hold' and b.get('reviewTarget') is None
        assert context['productionCallerCount']==0
        row.update({'sourceTextIncluded':False,'currentTargetSha256':inp['currentTargetSha256'],
         'currentTargetTextIncluded':False,'targetSha256':inp['currentTargetSha256'],'targetTextIncluded':False,
         'decision':'hold-hash-only','confidence':'unknown',
         'rationale':'No pinned production localization caller is available; source/current target text remains withheld.',
         'proposalResolution':'no-caller-hash-only-hold','unresolvedLowConfidence':False,'tokenAudit':None,'tokenChecksPass':None})
        counts['hold-hash-only']+=1
    rows.append(row)
    if backed:
        resolutions[row['proposalResolution']]+=1
    hashes.append({'head':HEAD,'tree':TREE,'continuationRank':inp['continuationRank'],
      'remainingQueueRank':inp['remainingQueueRank'],'locale':inp['locale'],
      'sourceId':inp['sourceId'] if backed else None,'sourceIdSha256':inp['sourceIdSha256'],
      'sourceSha256':inp['sourceSha256'],'callerContextSha256':context['callerContextSha256'],
      'currentTargetSha256':inp['currentTargetSha256'],'targetSha256':row['targetSha256'],
      'targetTextIncluded':False,'decision':row['decision']})
assert len(rows)==len(hashes)==300
assert counts['revise']==54 and counts['retain-current']==214 and counts['review']==8 and counts['hold-hash-only']==24
assert len(unresolved)==8
writejl('integrated-cross-review-ledger.jsonl',rows)
writejl('integrated-target-hashes.jsonl',hashes)
writejl('unresolved-low-confidence-cells.jsonl',unresolved)

# Byte-preserve source/caller evidence and hash-only hold lineage.
copies={
 'source-current-cells.jsonl':CF/'source-current-cells.jsonl',
 'caller-contexts.jsonl':CF/'caller-contexts.jsonl',
 'prior-active-holds-hash-only.jsonl':CF/'prior-held-cell-reattestation-hash-only.jsonl',
 'current-window-holds-hash-only.jsonl':CF/'window-holds-hash-only.jsonl',
 'prior-hold-resolution-history-hash-only.jsonl':CF/'prior-hold-resolution-history-hash-only.jsonl',
}
for outname,src in copies.items(): shutil.copyfile(src,OUT/outname)
prior=(CF/'prior-held-cell-reattestation-hash-only.jsonl').read_bytes()
assert prior==(PP/'prior-active-holds-hash-only.jsonl').read_bytes()==(BR/'prior-active-holds-reattestation-hash-only.jsonl').read_bytes()
window=(CF/'window-holds-hash-only.jsonl').read_bytes()
assert window==(PP/'current-window-holds-hash-only.jsonl').read_bytes()==(BR/'window-callerless-holds-hash-only.jsonl').read_bytes()
assert len(jlread(CF/'prior-held-cell-reattestation-hash-only.jsonl'))==433
assert len(jlread(CF/'window-holds-hash-only.jsonl'))==24

# Complete file-level inventory of the three external input packets.
lines=[]; packets={}
for label,d in [('candidate-free',CF),('primary',PP),('blind',BR)]:
    files=sorted(x for x in d.rglob('*') if x.is_file())
    for f in files: lines.append(f'{sha(f.read_bytes())}  {label}/{f.relative_to(d).as_posix()}')
    packets[label]={'path':d.relative_to(ROOT).as_posix(),'fileCount':len(files),
      'sha256SumsFileSha256':sha((d/'SHA256SUMS.txt').read_bytes()),
      'manifestSha256':sha((d/'manifest.json').read_bytes())}
(OUT/'INPUT_SHA256SUMS.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
cfm=jread(CF/'manifest.json'); ps=jread(PP/'summary.json'); bmft=jread(BR/'manifest.json')
boundary=ps['nextBoundary']; assert boundary==bmft['nextBoundary']
summary={
 'result':'PASS','head':HEAD,'tree':TREE,'window':'W1053-W1077','pullRequest':409,'repository':'snapetech-org/slskdN',
 'cellCount':300,'localeCount':12,'sourceCount':25,'callerBackedCells':276,'callerlessHashOnlyHolds':24,
 'integratedDispositions':{'revise':counts['revise'],'retain-current':counts['retain-current'],'review-low-confidence':counts['review'],'hold-hash-only':counts['hold-hash-only']},
 'acceptedTargetChanges':counts['acceptedTargetChanges'],'primaryProposalResolutionCounts':dict(sorted(resolutions.items())),
 'primaryProposalCells':ps['proposalCells'],'primaryRevisions':ps['revisedCells'],'blindDispositions':bmft['dispositions'],
 'overlapResolution':{'blindRevisionsAccepted':31,'primaryOnlyAcceptedOrRefined':23,'primaryOnlyRejected':4,
  'primaryReviewCandidatesHeld':4,'additionalLowConfidenceHold':1},
 'priorActiveHashOnlyHoldsCopiedByteForByte':433,'windowCallerlessHashOnlyHoldsCopiedByteForByte':24,
 'resultingActiveHashOnlyHolds':457,
 'tokenIntegrity':{'callerBackedTargetsChecked':276,'passing':276,'failures':0,
  'checks':['named placeholders','ICU plural/select syntax','markup tags','numeric tokens','protected literals','explicit product/domain literals']},
 'unresolvedLowConfidenceCells':[{'continuationRank':x['continuationRank'],'locale':x['locale'],'sourceId':x['sourceId'],'reason':x['reason']} for x in unresolved],
 'nextBoundary':boundary,'nativeSpeakerApproval':False,'confidence':'moderate',
 'noRepositoryOrPRChanges':True,'testsBuildsScansCiRun':False}
writej('summary.json',summary)
manifest={
 'artifact':'slskdN PR #409 W1053-W1077 integrated cross-review','repository':'snapetech-org/slskdN','pullRequest':409,
 'head':HEAD,'tree':TREE,'baseSha':cfm['baseSha'],'liveMainSha':cfm['mainSha'],'window':'W1053-W1077',
 'continuationRankRange':[1053,1077],'remainingQueueRankRange':[953,977],'localeOrder':LOCALES,
 'cellCount':300,'callerBackedCellCount':276,'callerlessHashOnlyHoldCount':24,
 'candidateFreeInput':True,'primaryCrossReviewUsed':True,'independentBlindCrossReviewUsed':True,
 'nativeSpeakerApproval':False,'confidence':'moderate','inputPackets':packets,'inputFileChecksumInventory':'INPUT_SHA256SUMS.txt',
 'holdLineage':{'priorActiveHoldCount':433,'priorActiveHoldsByteForByteFromCandidateFreePrimaryBlind':True,
  'currentWindowCallerlessHoldCount':24,'currentHoldsByteForByteFromCandidateFreePrimaryBlind':True,
  'priorHoldResolutionHistoryCopiedByteForByte':True},
 'nextBoundary':boundary,'generator':'create_packet.py',
 'outputFiles':['source-current-cells.jsonl','caller-contexts.jsonl','prior-active-holds-hash-only.jsonl',
  'current-window-holds-hash-only.jsonl','prior-hold-resolution-history-hash-only.jsonl',
  'integrated-cross-review-ledger.jsonl','integrated-target-hashes.jsonl',
  'unresolved-low-confidence-cells.jsonl','summary.json','README.md','INPUT_SHA256SUMS.txt','manifest.json',
  'SHA256SUMS.txt','create_packet.py','verify_integrated_cross.py'],
 'checksumCoverage':'SHA256SUMS.txt covers every regular output file except itself; INPUT_SHA256SUMS.txt covers every regular input file in all three sealed packets.'}
writej('manifest.json',manifest)
readme='''# slskdN PR #409 W1053-W1077 integrated cross-review

Pinned product head/tree: ba692c15ca54942108cc9da37757f585969e6173 / 27c09a8fe24030f5bb0995d809794a9e4829dc64.

The packet integrates all 300 cells in the 12-locale window: 54 revised targets, 214 retained current targets, 8 low-confidence review holds, and 24 callerless hash-only holds. It records the exact primary proposal and blind target alongside the selected target for each caller-backed cell, with source/caller hashes and token audit. The 24 callerless rows expose hashes only.

The 31 blind revisions were accepted after source/caller review. Of the 28 primary-only revisions, 23 were accepted, four were rejected as non-material or unsupported terminology changes, and one Arabic gender-agreement proposal remains held for review. Four primary revisions within blind-review flags also remain held. Three further blind-review holds plus that Arabic cell yield eight unresolved low-confidence cells; their ranks/locales and exact current/candidate targets are listed in unresolved-low-confidence-cells.jsonl.

The source/current-cell file, exact caller contexts, the 24 callerless holds, all 433 prior active holds, and prior hash-only hold-resolution history are retained from the sealed candidate-free input. The 24 callerless hold file and 433 prior active-hold file were also byte-compared with both primary and independent blind packets.

## Verification

Run python3 -B verify_integrated_cross.py from this directory. The verifier checks every input file checksum, all 300 row identities and exact proposal/caller pins, source/current/target hashes, token and protected-literal integrity, all hold lineage, and output checksum coverage.

INPUT_SHA256SUMS.txt inventories every file in the three input packets. SHA256SUMS.txt covers every regular file in this output packet except itself. The output checksum-list digest is reported with the verifier result.

No repository, PR, product files, tests, builds, scans, or CI were changed or run. These proposals and decisions are machine-reviewed and are not native-speaker-approved.
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')
print(json.dumps({'out':str(OUT),'rows':len(rows),'counts':dict(counts),'resolutions':dict(resolutions),
 'unresolved':len(unresolved),'inputFiles':len(lines)},ensure_ascii=False,indent=2))
