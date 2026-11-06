from __future__ import annotations
import collections, datetime, hashlib, json, re, subprocess
from pathlib import Path

INPUT_ROOT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w59-ranks353-377-primary-20261103/input')
PRIMARY_ROOT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w59-ranks353-377-primary-20261103')
BLIND_ROOT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w59-independent-blind-20261103')
OUT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w59-cross-audit-20261103')
REPO=Path('/home/keith/Documents/code/slskdn')
HEAD='fd6bf5c72a668eecac8cc57e4587bced7e4d9aad'
TREE='01c4bb4ea231e6ba72c3087d133b6e3e669853d9'
BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PR=409

def sha(data):
    if isinstance(data,str): data=data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def read_jsonl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def run(*args): return subprocess.check_output(list(args),text=True).strip()
def git_bytes(path): return subprocess.check_output(['git','-C',str(REPO),'show',f'{HEAD}:{path}'])
def git_blob(path): return run('git','-C',str(REPO),'rev-parse',f'{HEAD}:{path}')
def verify_sums(manifest):
    results=[]
    for line in manifest.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        expected,rel=line.split(None,1); rel=rel.strip().lstrip('*')
        actual=sha((manifest.parent/rel).read_bytes())
        results.append({'file':rel,'expected':expected,'actual':actual,'matches':expected==actual})
    assert results and all(x['matches'] for x in results),(manifest,results)
    return results

# Verify the three sealed packet layers before examining decisions.
input_sums=verify_sums(INPUT_ROOT/'PACKET-SHA256SUMS.txt')
primary_review_sums=verify_sums(PRIMARY_ROOT/'review/AGENT-SHA256SUMS.txt')
primary_task_sums=verify_sums(PRIMARY_ROOT/'TASK-SHA256SUMS.txt')
blind_sums=verify_sums(BLIND_ROOT/'SHA256SUMS.txt')
input_sha=sha((INPUT_ROOT/'PACKET-SHA256SUMS.txt').read_bytes())
primary_sha=sha((PRIMARY_ROOT/'review/primary-ledger.jsonl').read_bytes())
blind_sha=sha((BLIND_ROOT/'blind-decisions.jsonl').read_bytes())

# Re-attest the live PR, PR ref, branch ref, and exact tree immediately before adjudication.
pr=json.loads(subprocess.check_output(['gh','pr','view',str(PR),'-R','snapetech-org/slskdN','--json','state,isDraft,headRefName,headRefOid'],text=True))
remote_text=run('git','-C',str(REPO),'ls-remote','origin',f'refs/heads/{BRANCH}')
remote={line.split()[1]:line.split()[0] for line in remote_text.splitlines()}
live_pull=json.loads(subprocess.check_output(['gh','api',f'repos/snapetech-org/slskdN/pulls/{PR}','--jq','{state: .state, draft: .draft, headRef: .head.ref, headSha: .head.sha}'],text=True))
assert pr=={'headRefName':BRANCH,'headRefOid':HEAD,'isDraft':True,'state':'OPEN'},pr
assert remote.get(f'refs/heads/{BRANCH}')==HEAD,remote
assert live_pull=={'state':'open','draft':True,'headRef':BRANCH,'headSha':HEAD},live_pull
assert run('git','-C',str(REPO),'rev-parse',f'{HEAD}^{{tree}}')==TREE

manifest=json.loads((INPUT_ROOT/'manifest.json').read_text(encoding='utf-8'))
assert manifest['head']==HEAD and manifest['tree']==TREE
assert manifest['sourceCount']==25 and len(manifest['locales'])==12 and manifest['cellCount']==300
input_rows=read_jsonl(INPUT_ROOT/'source-current-cells.jsonl')
primary_rows=read_jsonl(PRIMARY_ROOT/'review/primary-ledger.jsonl')
blind_rows=read_jsonl(BLIND_ROOT/'blind-decisions.jsonl')
assert len(input_rows)==len(primary_rows)==len(blind_rows)==300
key=lambda x:(x['continuationRank'],x['locale'])
I={key(x):x for x in input_rows}; P={key(x):x for x in primary_rows}; B={key(x):x for x in blind_rows}
assert len(I)==len(P)==len(B)==300
assert set(I)==set(P)==set(B)
assert sorted({x['continuationRank'] for x in input_rows})==list(range(353,378))
assert sorted({x['locale'] for x in input_rows})==sorted(LOCALES)
assert sorted(manifest['locales'])==sorted(LOCALES)

# Verify all 12 exact-head catalog file pins and all 300 input values against Git.
catalogs={}; catalog_bytes={}
for locale in LOCALES:
    path=f'src/web/public/locales/{locale}.json'
    raw=git_bytes(path); digest=sha(raw); blob=git_blob(path)
    expected=next(x for x in input_rows if x['locale']==locale)
    assert digest==expected['catalogFileSha256'],(locale,digest,expected['catalogFileSha256'])
    assert blob==expected['catalogGitBlob'],(locale,blob,expected['catalogGitBlob'])
    catalog_bytes[locale]=raw
    catalogs[locale]=json.loads(raw)

for k,i in I.items():
    p=P[k]; b=B[k]
    assert sha(i['source'])==i['sourceSha256']
    assert sha(i['currentTarget'])==i['currentTargetSha256']
    assert catalogs[i['locale']].get(i['source'])==i['currentTarget'],k
    assert p['repository']=='snapetech-org/slskdN' and p['pullRequest']==PR and p['head']==HEAD and p['tree']==TREE
    assert b['repository']=='snapetech-org/slskdN' and b['pullRequest']==PR and b['head']==HEAD and b['tree']==TREE
    for x in (p,b):
        assert (x['continuationRank'],x['locale'],x['sourceId'],x['source'],x['sourceSha256'],x['catalogPath'],x['catalogFileSha256'],x['catalogGitBlob'],x['currentTarget'],x['currentTargetSha256']) == (
            i['continuationRank'],i['locale'],i['sourceId'],i['source'],i['sourceSha256'],i['catalogPath'],i['catalogFileSha256'],i['catalogGitBlob'],i['currentTarget'],i['currentTargetSha256']),k
    assert sha(canon(i))==p['candidateFreeInputCellSha256'],k
    assert p['callerContextSha256']==i['callerContextSha256'] and p['callerCount']==len(i['callerRefs']),k
    assert b['callerContext']['callerCount']==len(i['callerRefs']),k
    if p.get('proposedTarget') is not None:
        assert sha(p['proposedTarget'])==p['proposedTargetSha256'],k
    else:
        assert p.get('proposedTargetSha256') is None,k
    assert sha(b['selectedTarget'])==b['selectedTargetSha256'],k
    assert p['verdict'] in ('accept-current','correction','refinement','hold')
    assert b['disposition'] in ('accept-current','correction','refinement','hold')

# Extra glossary evidence for source-bound product terms and an adjacent peer label.
supplemental={
 'schemaVersion':1,'repository':'snapetech-org/slskdN','pullRequest':PR,'head':HEAD,'tree':TREE,
 'catalogKeyEvidence':{},'purpose':'Exact current-head translations used to adjudicate context-specific consistency questions.'
}
for source_key in ['Wishlist','Messages','Peers are discovered through searches and downloads']:
    supplemental['catalogKeyEvidence'][source_key]={}
    for locale in LOCALES:
        value=catalogs[locale].get(source_key)
        assert isinstance(value,str) and value
        supplemental['catalogKeyEvidence'][source_key][locale]={
            'translatedValue':value,'catalogPath':f'src/web/public/locales/{locale}.json',
            'catalogFileSha256':sha(catalog_bytes[locale]),'catalogGitBlob':git_blob(f'src/web/public/locales/{locale}.json'),
            'valueSha256':sha(value)
        }

# Adjudicated additional values are anchored to exact current catalog terminology.
wishlist_terms={locale:supplemental['catalogKeyEvidence']['Wishlist'][locale]['translatedValue'] for locale in LOCALES}
wishlist_final={
 'ar':'تجاهل مجلد قائمة الرغبات',
 'de':'Wunschlistenordner ignorieren',
 'es':'Ignorar carpeta de la lista de deseos',
 'fr':'Ignorer le dossier de la liste de souhaits',
 'hi':'इच्छा सूची फ़ोल्डर को अनदेखा करें',
 'id':'Abaikan folder daftar keinginan',
 'ja':'ウィッシュリストフォルダーを無視',
 'ko':'위시리스트 폴더 무시',
 'pt-BR':'Ignorar pasta da lista de desejos',
 'vi':'Bỏ qua thư mục danh sách yêu thích',
 'zh-Hans':'忽略愿望单文件夹',
 'zh-Hant':'忽略願望清單資料夾',
}
assert set(wishlist_final)==set(LOCALES)

# Cross-audit decision overrides where reviewer proposals differ or catalog context resolves terminology.
overrides={
 (355,'pt-BR'):{'target':'este download via swarm','disposition':'correction','source':'cross-audit','rationale':'The current noun stack “download swarm” is not natural Brazilian Portuguese. “via swarm” states the method clearly and preserves the exact technical term swarm; the primary proposal used “por swarm”, while the blind review retained the current phrasing.'},
 (365,'zh-Hant'):{'target':'未讀通知篩選','disposition':'correction','source':'primary+cross-audit','rationale':'This field filters unread release-radar notifications. The selected value names those notifications and uses Traditional Chinese script; the blind proposal repaired the script but left the filtered object implicit.'},
 (368,'hi'):{'target':B[(368,'hi')]['selectedTarget'],'disposition':'correction','source':'blind','rationale':'The exact locale catalog translates the UI section name “Messages” as “संदेश”; the current tooltip retains the English section name. The blind review’s localized target matches that pinned catalog term and preserves UI as the interface abbreviation.'},
 (362,'vi'):{'target':P[(362,'vi')]['proposedTarget'],'disposition':'correction','source':'primary+cross-audit','rationale':'The adjacent exact catalog message “Peers are discovered through searches and downloads” uses the technical loanword peer (“Các peer”). The selected wording follows that established term and avoids adding “node”, which is not in the source.'},
}

# The current exact catalog translates the application-owned Wishlist label in every locale.
# Apply that established term in the confirmation title in all 12 locales, including cells
# where both reviewers accepted a mixed-English current string.
for locale in LOCALES:
    overrides[(374,locale)]={'target':wishlist_final[locale],'disposition':'correction','source':'catalog-glossary-cross-audit',
       'rationale':f'The current target leaves the application-owned feature label “Wishlist” in English. The exact current locale catalog maps the standalone key “Wishlist” to {wishlist_terms[locale]!r}; this title uses the same localized feature term.'}

# Reconcile each cell and calculate structural checks on the chosen final target.
PH=re.compile(r'\{[^{}]+\}')
MARKUP=re.compile(r'</?[A-Za-z][^>]*>')
NUMBER=re.compile(r'(?<![A-Za-z])\d+(?:[.,]\d+)?%?(?![A-Za-z])')
counts=collections.Counter(); source_counts=collections.defaultdict(collections.Counter)
lineage_counts=collections.Counter(); candidate_pair_counts=collections.Counter(); changed_rows=[]; out_rows=[]
for k in sorted(I):
    i=I[k]; p=P[k]; b=B[k]; rank,locale=k
    primary_disp=p['verdict']; blind_disp=b['disposition']
    primary_selected_target=p['proposedTarget'] if p.get('proposedTarget') is not None else i['currentTarget']
    candidate_pair_counts[(primary_disp,blind_disp)]+=1
    caller_count=len(i['callerRefs'])
    assert caller_count==p['callerCount']==b['callerContext']['callerCount'],k
    if rank in (356,366):
        assert caller_count==0 and primary_disp=='hold' and blind_disp=='hold',k
        disp='hold'; target=i['currentTarget']; source='current'; reason='No exact quoted production caller is pinned for this source key. Preserve the current locale value in every catalog until the intended product context is resolved.'
    elif k in overrides:
        o=overrides[k]; disp=o['disposition']; target=o['target']; source=o['source']; reason=o['rationale']
    elif p.get('proposedTarget') is not None:
        disp=primary_disp; target=p['proposedTarget']; source='primary'
        if blind_disp=='accept-current': reason=p['rationale']+' The blind reviewer accepted the current value; cross-audit accepts this context-grounded correction/refinement after checking the exact caller.'
        elif b.get('selectedTarget')!=target: reason=p['rationale']+' The independent candidate differs; cross-audit selected this exact-context wording after comparing both proposals.'
        else: reason=p['rationale']+' The independent blind review selected the same target.'
    elif blind_disp in ('correction','refinement') and b['selectedTarget']!=i['currentTarget']:
        disp=blind_disp; target=b['selectedTarget']; source='blind'; reason=b['rationale']+' The primary reviewer accepted the current value; cross-audit accepts the blind finding after checking the pinned caller.'
    else:
        assert primary_disp=='accept-current' and blind_disp=='accept-current',k
        disp='accept-current'; target=i['currentTarget']; source='current'; reason='Both independent reviewers accept the current translation, and it matches the exact pinned caller context.'
    assert disp in ('accept-current','correction','refinement','hold')
    source_ph=collections.Counter(PH.findall(i['source'])); target_ph=collections.Counter(PH.findall(target))
    source_tags=MARKUP.findall(i['source']); target_tags=MARKUP.findall(target)
    source_nums=NUMBER.findall(i['source']); target_nums=NUMBER.findall(target)
    protected=p.get('structuralChecks',{}).get('protectedLiterals',{}).get('expected',[])
    protected_checks={lit:(lit in target) for lit in protected}
    assert source_ph==target_ph,(k,source_ph,target_ph)
    assert source_tags==target_tags,(k,source_tags,target_tags)
    assert source_nums==target_nums,(k,source_nums,target_nums)
    assert all(protected_checks.values()),(k,protected_checks)
    if 'slskdN' in i['source']: assert 'slskdN' in target,k
    if rank==355: assert 'swarm' in target.casefold(),k
    source_lead=len(i['source'])-len(i['source'].lstrip(' ')); target_lead=len(target)-len(target.lstrip(' '))
    source_trail=len(i['source'])-len(i['source'].rstrip(' ')); target_trail=len(target)-len(target.rstrip(' '))
    assert (source_lead,source_trail)==(target_lead,target_trail),(k,source_lead,target_lead,source_trail,target_trail)
    counts[disp]+=1; source_counts[rank][disp]+=1
    changed=target!=i['currentTarget']
    lineage_counts[source]+=1
    if changed: changed_rows.append({'continuationRank':rank,'locale':locale,'sourceId':i['sourceId'],'disposition':disp,'fromSha256':i['currentTargetSha256'],'toSha256':sha(target)})
    extra=None
    if k in overrides and (rank==374 or (rank==368 and locale=='hi')):
        term_key='Wishlist' if rank==374 else 'Messages'
        extra={'catalogSourceKey':term_key,'catalogValue':supplemental['catalogKeyEvidence'][term_key][locale]['translatedValue'],'catalogValueSha256':supplemental['catalogKeyEvidence'][term_key][locale]['valueSha256']}
    if rank==362 and locale in ('pt-BR','vi','zh-Hans','zh-Hant'):
        peer=supplemental['catalogKeyEvidence']['Peers are discovered through searches and downloads'][locale]
        extra={'catalogSourceKey':'Peers are discovered through searches and downloads','catalogValue':peer['translatedValue'],'catalogValueSha256':peer['valueSha256']}
    row={
      'schemaVersion':1,'repository':'snapetech-org/slskdN','pullRequest':PR,'head':HEAD,'tree':TREE,'window':'W59 ranks 353-377',
      'continuationRank':rank,'historicalSourceOrdinal':i.get('historicalSourceOrdinal'),'sourceId':i['sourceId'],'source':i['source'],'sourceSha256':i['sourceSha256'],
      'locale':locale,'catalogPath':i['catalogPath'],'catalogFileSha256':i['catalogFileSha256'],'catalogGitBlob':i['catalogGitBlob'],
      'currentTarget':i['currentTarget'],'currentTargetSha256':i['currentTargetSha256'],
      'primaryReview':{'disposition':primary_disp,'selectedTarget':primary_selected_target,'selectedTargetSha256':sha(primary_selected_target),'proposedTarget':p.get('proposedTarget'),'proposedTargetSha256':p.get('proposedTargetSha256'),'rationale':p['rationale'],'callerCount':p['callerCount'],'callerContextSha256':p['callerContextSha256'],'ledgerRowSha256':sha(canon(p))},
      'blindReview':{'disposition':blind_disp,'selectedTarget':b.get('selectedTarget'),'selectedTargetSha256':b.get('selectedTargetSha256'),'rationale':b['rationale'],'confidence':b['confidence'],'callerCount':b['callerContext']['callerCount'],'ledgerRowSha256':sha(canon(b))},
      'disposition':disp,'selectedTarget':target,'selectedTargetSha256':sha(target),'selectedBy':source,'selectedForApplication':disp in ('correction','refinement'),
      'changeFromCurrent':changed,'crossAuditRationale':reason,'confidence':'high' if disp=='hold' or primary_disp==blind_disp and primary_selected_target==b.get('selectedTarget') else 'moderate',
      'callerEvidence':{'callerCount':caller_count,'callerContextSha256':i['callerContextSha256'],'references':i['callerRefs'],'holdReason':i.get('verdict') if rank in (356,366) else None},
      'structuralChecks':{'sourceCurrentHashesVerified':True,'selectedTargetSha256Verified':True,'placeholderMultisetParity':True,'markupSequenceParity':True,'numericTokenSequenceParity':True,'protectedLiterals':protected_checks,'sourceLeadingSpaces':source_lead,'targetLeadingSpaces':target_lead,'sourceTrailingSpaces':source_trail,'targetTrailingSpaces':target_trail,'preservedSlskdN':('slskdN' not in i['source'] or 'slskdN' in target),'preservedSwarm':(rank!=355 or 'swarm' in target.casefold())},
      'supplementalCatalogEvidence':extra,'qualifiedLocaleReviewRequiredBeforeRelease':True,'releaseApprovedByThisCrossAudit':False
    }
    out_rows.append(row)

assert counts=={'accept-current':207,'correction':54,'refinement':15,'hold':24},counts
assert len(changed_rows)==69,len(changed_rows)
assert all(source_counts[r]['hold']==12 for r in (356,366))
assert all(source_counts[r].get('correction',0)==0 and source_counts[r].get('refinement',0)==0 for r in (356,366))
assert len({(x['continuationRank'],x['locale']) for x in out_rows})==300
primary_blind_disposition_disagreements=sum(P[k]['verdict']!=B[k]['disposition'] for k in I)
primary_selected=lambda k:P[k]['proposedTarget'] if P[k].get('proposedTarget') is not None else I[k]['currentTarget']
primary_blind_target_disagreements=sum(primary_selected(k)!=B[k]['selectedTarget'] for k in I)
same_disposition_target_disagreements=sum(P[k]['verdict']==B[k]['disposition'] and primary_selected(k)!=B[k]['selectedTarget'] for k in I)

# Write supplemental term evidence and audit artifacts.
(OUT/'cross-audit-ledger.jsonl').write_text(''.join(canon(x)+'\n' for x in out_rows),encoding='utf-8')
(OUT/'supplemental-catalog-context.json').write_text(json.dumps(supplemental,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
summary={
 'schemaVersion':1,'repository':'snapetech-org/slskdN','pullRequest':PR,'head':HEAD,'tree':TREE,'branch':BRANCH,
 'window':'W59 ranks 353-377','sourceCount':25,'localeCount':12,'cellCount':300,
 'dispositions':dict(sorted(counts.items())),'selectedCatalogChanges':len(changed_rows),
 'callerlessHolds':{'ranks':[356,366],'cells':24,'preservedCurrentTargets':True},
 'changeCounts':{'correction':sum(1 for x in changed_rows if x['disposition']=='correction'),'refinement':sum(1 for x in changed_rows if x['disposition']=='refinement')},
 'primaryBlindDispositionPairs':{f'{a}|{b}':n for (a,b),n in sorted(candidate_pair_counts.items())},
 'primaryBlindDispositionDisagreements':primary_blind_disposition_disagreements,'primaryBlindSelectedTargetDisagreements':primary_blind_target_disagreements,'sameDispositionDifferentTargetCells':same_disposition_target_disagreements,
 'crossAuditSpecificActions':{'primaryCandidatesSelected':61,'primaryCandidateAdjusted':1,'blindOnlyCandidateSelected':1,'additionalCatalogGlossaryCorrections':6},
 'placeholderMarkupNumericProtectedAndWhitespaceFailures':0,
 'exactCatalogCurrentReadbackCells':300,'catalogFilesPinned':12,'orderedCatalogKeySetPreservationRequired':True,
 'nativeSpeakerApproval':False,'qualifiedLocaleReviewRequiredBeforeRelease':True,'releaseApprovedByThisCrossAudit':False,
 'inputManifestSha256':input_sha,'primaryLedgerSha256':primary_sha,'blindLedgerSha256':blind_sha,
}
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
disagreement_summary={
 'schemaVersion':1,'cellCount':300,'primaryBlindDispositionPairs':summary['primaryBlindDispositionPairs'],
 'dispositionDisagreementCount':primary_blind_disposition_disagreements,'selectedTargetDisagreementCount':primary_blind_target_disagreements,
 'sameDispositionDifferentTargetCount':same_disposition_target_disagreements,
 'dispositionDisagreementCells':[{'continuationRank':k[0],'locale':k[1],'primary':P[k]['verdict'],'blind':B[k]['disposition']} for k in sorted(I) if P[k]['verdict']!=B[k]['disposition']],
 'selectedTargetDisagreementCells':[{'continuationRank':k[0],'locale':k[1],'primaryTargetSha256':sha(primary_selected(k)),'blindTargetSha256':B[k]['selectedTargetSha256']} for k in sorted(I) if primary_selected(k)!=B[k]['selectedTarget']],
 'sameDispositionDifferentTargetCells':[{'continuationRank':k[0],'locale':k[1],'disposition':P[k]['verdict'],'primaryTargetSha256':sha(primary_selected(k)),'blindTargetSha256':B[k]['selectedTargetSha256']} for k in sorted(I) if P[k]['verdict']==B[k]['disposition'] and primary_selected(k)!=B[k]['selectedTarget']],
 'callerlessHolds':[{'continuationRank':k[0],'locale':k[1],'source':I[k]['source'],'currentTarget':I[k]['currentTarget'],'currentTargetSha256':I[k]['currentTargetSha256'],'callerCount':0,'primaryDisposition':P[k]['verdict'],'blindDisposition':B[k]['disposition'],'finalDisposition':'hold'} for k in sorted(I) if k[0] in (356,366)]
}
assert len(disagreement_summary['dispositionDisagreementCells'])==primary_blind_disposition_disagreements
assert len(disagreement_summary['selectedTargetDisagreementCells'])==primary_blind_target_disagreements
assert len(disagreement_summary['sameDispositionDifferentTargetCells'])==same_disposition_target_disagreements
assert len(disagreement_summary['callerlessHolds'])==24
(OUT/'disagreement-and-hold-summary.json').write_text(json.dumps(disagreement_summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
attestation={
 'repository':'snapetech-org/slskdN','pullRequest':PR,'prState':pr['state'],'prDraft':pr['isDraft'],'headRefName':pr['headRefName'],'head':HEAD,'tree':TREE,
 'remoteBranchRef':f'refs/heads/{BRANCH}','remoteBranchHead':remote[f'refs/heads/{BRANCH}'],'remotePullRef':f'refs/pull/{PR}/head','remotePullRefHead':live_pull['headSha'],'remotePullHeadVerifiedVia':'GitHub pull request API',
 'verifiedAtUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'inputPacketChecksumManifestSha256':input_sha,'inputPacketFilesVerified':len(input_sums),
 'primaryReviewManifestFilesVerified':len(primary_review_sums),'primaryTaskManifestFilesVerified':len(primary_task_sums),
 'blindReviewManifestFilesVerified':len(blind_sums),'primaryLedgerSha256':primary_sha,'blindLedgerSha256':blind_sha,
 'catalogFilesVerified':12,'cellCurrentValuesReadBack':300,'rowCount':len(out_rows),'selectedChangeCount':len(changed_rows),
 'worktreeUsed':str(REPO),'worktreeMutation':'none','testsBuildsScansCIDispatches':'none','workflowChanges':'none',
 'nativeSpeakerApproval':False,'releaseApproved':False
}
(OUT/'attestation.json').write_text(json.dumps(attestation,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report='''# slskdN PR #409 W59 ranks 353–377 third-party cross-audit\n\nThe audit is pinned to open draft PR head `'''+HEAD+'''` (tree `'''+TREE+'''`). The candidate-free input, primary ledger, and independent blind ledger each passed their checksum manifests; the live PR, branch ref, and live PR record still match this head.\n\n## Result\n\nThe 300 cells reconcile to **207 accept-current, 54 corrections, 15 refinements, and 24 holds**. The 24 holds cover all locales for rank 356 (`Add Torrent`) and rank 366 (`Searches`), each with zero pinned production callers. Those targets remain unchanged. The 69 selected catalog updates are supported by exact caller context, current catalog values, and review lineage.\n\nThe structural reconciliation verified source/current hashes, every locale catalog SHA-256 and Git blob, all 300 current values at the exact head, placeholder and markup parity, numeric tokens, protected literals, and edge whitespace. The two spaces and `{summary}` at rank 360 and `{label}` at rank 367 are retained. `slskdN` remains exact at rank 362; the technical term `swarm` remains present at rank 355, with the ordinary German noun capitalization in `Swarm`.\n\n## Reconciliation decisions\n\n- The primary and blind ledgers agree on the 24 no-caller holds and on which cells need correction at ranks 353, 357, 370, 372, and 377; where wording differs, row-level lineage records both candidates and the selected target.\n- The exact `Messages` locale key supports translating the Hindi and Vietnamese “Messages UI” tooltip at rank 368; Hindi’s blind finding is accepted while the English “Messages” token is removed.\n- Rank 362 follows each locale’s adjacent `Peers are discovered through searches and downloads` catalog term. This preserves the established peer terminology and avoids introducing a new “node” concept in Vietnamese.\n- Rank 365’s checkbox filters unread release-radar notifications; the selected labels name the filtered notifications. The Traditional Chinese target also replaces the current Simplified character.\n- Rank 367 is an accessible dropdown name. The selected locale order expresses “options for {label}” and preserves the placeholder.\n- Rank 372 is a passing setup-health status produced when no enabled provider credential gaps remain. The chosen translations say no credentials are missing; this avoids suggesting every optional provider is fully configured.\n- At rank 374, the standalone `Wishlist` key is already translated in every exact-head locale catalog. The cross-audit applies that current catalog vocabulary to the modal title in all 12 locales, including six cells where both reviewers had accepted the mixed-English current string. The exact values are recorded in `supplemental-catalog-context.json`.\n\nAcross the 300 cells, the primary and blind reviewers differ in disposition on 39 cells and in selected target on 53 cells; 15 cells have the same correction disposition but different target wording. The row-level ledger retains both reviews, each review row hash, and the adjudicated target hash. The blind reviewer accepted current values in some cells where the primary reviewer found context-specific improvements. The cross-audit retained changes where the exact caller and neighboring locale terms supported the correction. For the two callerless source keys, the existing values are preserved rather than guessed.\n\nThis is machine-assisted review, not native-speaker approval. No repository changes, tests, builds, scans, CI dispatches, workflow changes, releases, or tags were made by this cross-audit.\n'''
(OUT/'report.md').write_text(report,encoding='utf-8')
(OUT/'README.md').write_text('''# Cross-audit package\n\n`cross-audit-ledger.jsonl` reconciles all 300 W59 cells. `summary.json` gives disposition and validation totals. `disagreement-and-hold-summary.json` lists every primary/blind disagreement and each of the 24 callerless held cells. `attestation.json` records exact-head pins and the source packet manifests. `supplemental-catalog-context.json` records exact-head locale-key evidence used for the peer, Messages, and Wishlist wording decisions.\n\n`verify_cross_audit_evidence.py --repo /path/to/slskdN` verifies the audit package and reads the current values from the exact pinned Git tree. The independent blind review, primary ledger, and candidate-free input are separate packet artifacts under task scratch; their manifest hashes are recorded in the attestation. This audit is not native-speaker approval and does not approve a release.\n''',encoding='utf-8')

# Hash every artifact except the root checksum manifest.
files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
(OUT/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(OUT).as_posix()}\n' for p in files),encoding='utf-8')
print(json.dumps({'output':str(OUT),'rows':len(out_rows),'summary':summary,'attestation':attestation},ensure_ascii=False,indent=2))
