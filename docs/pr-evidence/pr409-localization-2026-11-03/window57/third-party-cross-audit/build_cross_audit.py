import collections, hashlib, json, re
from pathlib import Path

ROOT = Path('/mnt/disks/scratch/task-scratch')
OUT = ROOT / 'slskdn-pr409-w57-third-party-cross-audit-20261103'
INPUT = ROOT / 'slskdn-pr409-w57-ranks303-327-candidate-free-20261103' / 'input'
PRIMARY_DIR = ROOT / 'slskdn-pr409-w57-primary-review-20261103'
BLIND_DIR = ROOT / 'slskdn-pr409-w57-independent-blind-20261103'
HEAD = '6b09b3c7bf7de69c316ba3e2503dc450004c9b59'
TREE = 'a5f9b792875d341a49208d0785bfff28aa9092d7'
REPO = 'snapetech-org/slskdN'
PR = 409
BRANCH = 'codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

CANDIDATES = {
 (310,'es'): ('correction', 'Verificación de pertenencia al Pod', 'The caller is a Pod security card. “grupo Pod” adds a redundant group noun and obscures the named Pod entity; “pertenencia al Pod” retains membership in that entity.'),
 (310,'vi'): ('correction', 'Xác minh tư cách thành viên của Pod', 'The caller is a Pod security card. The current wording says group membership but omits the named Pod entity; the proposal makes the membership relation explicit.'),
 (315,'pt-BR'): ('correction', 'Permitir que clientes legados do Soulseek se conectem por meio de uma ponte', 'The caller is a bridge permission setting. “Herdados” means inherited and is a false friend for legacy clients; “legados” is the software sense of legacy. The infinitive matches a permission label.'),
 (315,'vi'): ('correction', 'Cho phép các máy khách Soulseek đời cũ kết nối qua cầu nối', 'The caller is a bridge permission setting. “Kế thừa” means inherited and misreads legacy; “đời cũ” describes older legacy clients while preserving Soulseek and bridge access.'),
 (317,'zh-Hant'): ('correction', '來源：{tier} {peerId}', 'The pinned formatter supplies a provenance label followed by trust tier and peer ID. Current 出生 means birth; 來源 correctly labels provenance and preserves both runtime placeholders.'),
 (318,'de'): ('correction', 'Aktivieren Sie die Lidarr-Einstellung zum Ersetzen vorhandener Dateien', 'The checkbox controls Lidarr’s replace-existing-files option. The current order “Einstellung Lidarr” is ungrammatical; the proposal clearly identifies Lidarr’s setting.'),
 (318,'es'): ('correction', 'Activar la opción de Lidarr para reemplazar archivos existentes', 'The checkbox controls Lidarr’s replace-existing-files option. The current wording says Lidarr replaces the configuration of existing files; this names the option being enabled.'),
 (318,'hi'): ('correction', 'मौजूदा फ़ाइलों को बदलने के लिए Lidarr की सेटिंग चालू करें', 'The current word order is difficult to parse as an instruction to enable the Lidarr setting. The proposal states that the setting permits replacement of existing files.'),
 (318,'id'): ('correction', 'Aktifkan pengaturan Lidarr untuk mengganti file yang sudah ada', 'The current wording conflates enabling Lidarr with replacing a setting. The proposal clearly enables Lidarr’s setting for replacing existing files.'),
 (318,'pt-BR'): ('refinement', 'Ative a opção do Lidarr para substituir arquivos existentes', 'The current target broadly conveys the setting but its noun chain is awkward and makes the relation unclear. This is a clearer wording refinement for the same checkbox.'),
 (318,'vi'): ('correction', 'Bật tùy chọn Lidarr cho phép thay thế các tệp hiện có', 'The current wording can read as enabling Lidarr and replacing a setting. The proposal clearly names the Lidarr option that permits replacing existing files.'),
 (322,'id'): ('correction', 'Folder bersama yang dikonfigurasi', 'The caller labels the System/Shares table. “Saham” means financial stocks in this context; “folder bersama” identifies configured shared folders. Confidence is moderate because the packet does not include table row data.'),
}
HOLD_RANKS = {319: 'The caller is an empty-state prompt to play local tracks, but the packet gives no definition or approved localized glossary for “recommendation seeds.” The seed metaphor may be a product term or a generic recommendation input; hold all locales rather than guess.'}


def sha(b): return hashlib.sha256(b).hexdigest()
def read_jsonl(path): return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]
def load_json(path): return json.loads(path.read_text(encoding='utf-8'))
def write_json(path, value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_jsonl(path, rows): path.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in rows),encoding='utf-8')
def edge(s):
    return [len(s)-len(s.lstrip()), len(s)-len(s.rstrip())]
def placeholders(s): return re.findall(r'\{[^{}]+\}', s)
def markup(s): return re.findall(r'<[^>]+>', s)
def numbers(s): return re.findall(r'(?<![\w])\d+(?:[.,:/-]\d+)*(?![\w])', s)
def literal_present(s, literal): return literal in s

def verify_sum_file(directory, filename):
    sums = {}
    for line in (directory / filename).read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        digest, name = line.split(None,1)
        name = name.lstrip('* ')
        actual = sha((directory/name).read_bytes())
        sums[name] = {'expected': digest, 'actual': actual, 'matches': digest == actual}
    return sums

# Validate the three pinned packet families before producing any records.
input_sums = verify_sum_file(INPUT, 'PACKET-SHA256SUMS.txt')
primary_sums = verify_sum_file(PRIMARY_DIR, 'SHA256SUMS.txt')
blind_sums = verify_sum_file(BLIND_DIR, 'SHA256SUMS.txt')
assert input_sums and all(x['matches'] for x in input_sums.values())
assert primary_sums and all(x['matches'] for x in primary_sums.values())
assert blind_sums and all(x['matches'] for x in blind_sums.values())

inp = read_jsonl(INPUT/'source-current-cells.jsonl')
primary = read_jsonl(PRIMARY_DIR/'primary-decisions.jsonl')
blind = read_jsonl(BLIND_DIR/'review-decisions.jsonl')
inventory = read_jsonl(INPUT/'source-inventory-selection.jsonl')
boundaries = read_jsonl(INPUT/'selection-boundary.jsonl')
contexts = read_jsonl(INPUT/'caller-contexts.jsonl')
keys = lambda rows: {(r['continuationRank'],r['locale']):r for r in rows}
I, P, B = keys(inp), keys(primary), keys(blind)
assert len(inp) == len(primary) == len(blind) == 300
assert set(I) == set(P) == set(B)
assert sorted({k[0] for k in I}) == list(range(303,328))
assert sorted({k[1] for k in I}) == LOCALES
assert len(inventory) == 25 and {r['continuationRank'] for r in inventory} == set(range(303,328))
assert all(r['head']==HEAD and r['tree']==TREE and r['pullRequest']==PR and r['repository']==REPO for r in primary)

# Confirm exact identity/current-value pins, and caller references, against both ledgers.
identity_failures=[]
for key, i in I.items():
    p, b = P[key], B[key]
    for label, row in [('primary',p),('blind',b)]:
        for field in ('source','sourceId','sourceSha256','currentTarget','currentTargetSha256','catalogPath','catalogFileSha256','catalogGitBlob'):
            if row.get(field) != i.get(field): identity_failures.append({'key':key,'ledger':label,'field':field,'input':i.get(field),'ledgerValue':row.get(field)})
        context_hash = row.get('callerContextSha256') if label=='blind' else row.get('callerEvidence',{}).get('callerContextSha256')
        if context_hash != i.get('callerContextSha256'):
            identity_failures.append({'key':key,'ledger':label,'field':'callerContextSha256','input':i.get('callerContextSha256'),'ledgerValue':context_hash})
    if sha(i['currentTarget'].encode()) != i['currentTargetSha256']:
        identity_failures.append({'key':key,'field':'currentTargetSha256','reason':'input hash mismatch'})
    if sha(i['source'].encode()) != i['sourceSha256']:
        identity_failures.append({'key':key,'field':'sourceSha256','reason':'input source hash mismatch'})
assert not identity_failures, identity_failures[:3]
context_by_rank={r['continuationRank']:r for r in contexts}
caller_count=sum(len(c['callers']) for c in contexts)
caller_failures=[]
for key,i in I.items():
    c=context_by_rank[key[0]]
    refs=i['callerRefs']
    c_refs=[]
    for caller in c['callers']:
        c_refs.append({'path':caller['path'],'line':caller['line'],'lineSha256':caller['lineSha256'],'fileSha256':caller['fileSha256'],'gitBlob':caller['gitBlob']})
    normalized=sorted(refs,key=lambda r:(r['path'],r['line']))
    if sorted(c_refs,key=lambda r:(r['path'],r['line'])) != normalized:
        caller_failures.append({'rank':key[0],'inputRefs':normalized,'contextRefs':c_refs})
assert not caller_failures, caller_failures[:1]
assert caller_count == 42

# Validate the known defect without relying on its bad lastSelected/nextBoundary fields.
selection = load_json(INPUT/'selection-and-boundary.json')
full_boundary = {r['continuationRank']:r for r in boundaries}
assert 'ranks 303-327' in selection['window']
assert len(boundaries)==27
assert full_boundary[302]['role']=='previous-boundary-W56'
assert full_boundary[303]['role']=='selected-W57'
assert full_boundary[327]['role']=='selected-W57'
assert full_boundary[328]['role']=='next-boundary-W58'
assert selection['lastSelected']['continuationRank']==304 and selection['nextBoundary']['continuationRank']==305
assert selection['nextBoundary']['role']=='selected-W57'

# Independent semantic adjudication: evaluate every current cell; intervene only on the explicit
# context/language issues listed above, and retain a hold for the unresolved terminology set.
ledger=[]
for key in sorted(I):
    rank, locale = key
    i,p,b=I[key],P[key],B[key]
    if rank in HOLD_RANKS:
        decision='hold'; proposed=None; selected=None
        rationale=HOLD_RANKS[rank]
        confidence='low'
    elif key in CANDIDATES:
        decision, proposed, rationale=CANDIDATES[key]
        selected=proposed
        confidence='moderate' if key not in {(315,'pt-BR'),(315,'vi'),(318,'pt-BR'),(322,'id')} else 'low'
    else:
        decision='accept-current'; proposed=None; selected=i['currentTarget']
        rationale=('The source, current target, and pinned caller were checked against both review records. '
                   'Neither reviewer identified a material semantic error here, and this audit found no '
                   'caller-context mismatch or placeholder, markup, numeric, or edge-whitespace defect.')
        confidence='moderate'
    checked_target = selected if selected is not None else i['currentTarget']
    src_tokens, tgt_tokens = placeholders(i['source']), placeholders(checked_target)
    src_tags, tgt_tags = markup(i['source']), markup(checked_target)
    src_nums, tgt_nums = numbers(i['source']), numbers(checked_target)
    # A small protected-literal set is evidenced by the primary audit packet and source strings.
    protected = ['Soulseek'] if rank==315 else (['Lidarr'] if rank in (316,318) else [])
    checks={
       'placeholders': {'source':src_tokens,'checkedTarget':tgt_tokens,'matchesExactly':src_tokens==tgt_tokens},
       'markup': {'source':src_tags,'checkedTarget':tgt_tags,'matchesExactly':src_tags==tgt_tags},
       'numericTokens': {'source':src_nums,'checkedTarget':tgt_nums,'matchesExactly':src_nums==tgt_nums},
       'edgeWhitespace': {'source':edge(i['source']),'current':edge(i['currentTarget']),'checkedTarget':edge(checked_target),'matchesSource':edge(i['source'])==edge(checked_target)},
       'protectedLiterals': [{'literal':lit,'inSource':literal_present(i['source'],lit),'inCurrent':literal_present(i['currentTarget'],lit),'inCheckedTarget':literal_present(checked_target,lit),'preserved':not literal_present(i['source'],lit) or literal_present(checked_target,lit)} for lit in protected]
    }
    assert checks['placeholders']['matchesExactly'] and checks['markup']['matchesExactly'] and checks['numericTokens']['matchesExactly'] and checks['edgeWhitespace']['matchesSource']
    assert all(x['preserved'] for x in checks['protectedLiterals'])
    reviewer_integrity={}
    for reviewer,target in [('primarySelectedTarget',p['selectedTarget']),('blindCandidateTarget',b['candidateTarget'])]:
        if target is None:
            reviewer_integrity[reviewer]=None
            continue
        r_checks={
          'placeholders': placeholders(i['source'])==placeholders(target),
          'markup': markup(i['source'])==markup(target),
          'numericTokens': numbers(i['source'])==numbers(target),
          'edgeWhitespace': edge(i['source'])==edge(target),
          'protectedLiterals': all(not literal_present(i['source'],lit) or literal_present(target,lit) for lit in protected)
        }
        assert all(r_checks.values()), (key,reviewer,r_checks)
        reviewer_integrity[reviewer]={'target':target,'checks':r_checks}
    ctx=context_by_rank[rank]
    refs=[{'path':x['path'],'line':x['line'],'lineSha256':x['lineSha256'],'fileSha256':x['fileSha256'],'gitBlob':x['gitBlob']} for x in ctx['callers']]
    row={
       'schemaVersion':1,'auditId':f'W57-rank-{rank}-{locale}','repository':REPO,'pullRequest':PR,
       'head':HEAD,'tree':TREE,'window':'W57 ranks 303–327','continuationRank':rank,'historicalSourceOrdinal':i['historicalSourceOrdinal'],
       'sourceId':i['sourceId'],'source':i['source'],'sourceSha256':i['sourceSha256'],'locale':locale,
       'catalogPath':i['catalogPath'],'catalogFileSha256':i['catalogFileSha256'],'catalogGitBlob':i['catalogGitBlob'],
       'currentTarget':i['currentTarget'],'currentTargetSha256':i['currentTargetSha256'],
       'callerContextSha256':i['callerContextSha256'],'callerRefs':refs,
       'primaryDecision':p['decision'],'primaryCandidateTarget':p['candidateTarget'],'primaryRationale':p['rationale'],
       'blindDisposition':b['disposition'],'blindCandidateTarget':b['candidateTarget'],'blindRationale':b['rationale'],
       'auditDisposition':decision,'proposedTarget':proposed,'selectedTarget':selected,'selectedTargetSha256':sha(selected.encode()) if selected is not None else None,
       'rationale':rationale,'confidence':confidence,'nativeSpeakerApproved':False,'integrityChecks':checks,'reviewerCandidateIntegrity':reviewer_integrity
    }
    ledger.append(row)

assert len(ledger)==300
assert collections.Counter(r['auditDisposition'] for r in ledger)=={'accept-current':276,'correction':11,'refinement':1,'hold':12}

# Produce compact disagreements for all primary/blind recommendation conflicts and divergent targets.
disagreements=[]
for r in ledger:
    pd,bd=r['primaryDecision'],r['blindDisposition']
    ptarget=r['primaryCandidateTarget']
    btarget=r['blindCandidateTarget']
    normalized_bd='correction' if bd=='correction/refinement proposal' else bd
    if pd!=normalized_bd or (ptarget and btarget and ptarget!=btarget):
        disagreements.append({
          'auditId':r['auditId'],'continuationRank':r['continuationRank'],'locale':r['locale'],'sourceId':r['sourceId'],
          'primaryDecision':pd,'primaryCandidateTarget':ptarget,'blindDisposition':bd,'blindCandidateTarget':btarget,
          'auditDisposition':r['auditDisposition'],'auditSelectedTarget':r['selectedTarget'],'auditRationale':r['rationale'],
          'classification':('unresolved terminology: cross-audit holds all rank 319 cells' if r['continuationRank']==319 else ('candidate wording differs' if pd==normalized_bd else 'decision differs'))
        })

write_jsonl(OUT/'cross-audit-ledger.jsonl',ledger)
write_jsonl(OUT/'disagreements.jsonl',disagreements)

# Input and boundary verification evidence.
checksums = {
 'candidateFreeInput': {'directory':str(INPUT),'checksumList':'PACKET-SHA256SUMS.txt','checksumListSha256':sha((INPUT/'PACKET-SHA256SUMS.txt').read_bytes()),'files':input_sums},
 'primaryReview': {'directory':str(PRIMARY_DIR),'checksumList':'SHA256SUMS.txt','checksumListSha256':sha((PRIMARY_DIR/'SHA256SUMS.txt').read_bytes()),'files':primary_sums,'ledgerSha256':sha((PRIMARY_DIR/'primary-decisions.jsonl').read_bytes())},
 'blindReview': {'directory':str(BLIND_DIR),'checksumList':'SHA256SUMS.txt','checksumListSha256':sha((BLIND_DIR/'SHA256SUMS.txt').read_bytes()),'files':blind_sums,'ledgerSha256':sha((BLIND_DIR/'review-decisions.jsonl').read_bytes())},
 'identityAndCallerPinCheck': {'allLedgerIdentityFieldsMatchCandidateFreeInput':True,'callerReferencesMatchedPinnedContext':True,'sourceAndCurrentTargetHashesRecomputed':True,'sourceCount':25,'cellCount':300,'productionCallerOccurrences':caller_count},
 'correctedWindowBasis': {
   'defectiveFile':'selection-and-boundary.json',
   'invalidFields':['lastSelected','nextBoundary'],
   'badValues':{'lastSelected':selection['lastSelected'],'nextBoundary':selection['nextBoundary']},
   'authoritativeSources':['selection-boundary.jsonl','source-inventory-selection.jsonl','source-current-cells.jsonl'],
   'correctWindow':{'firstRank':303,'firstSourceId':full_boundary[303]['sourceId'],'lastRank':327,'lastSourceId':full_boundary[327]['sourceId'],'nextBoundaryRank':328,'nextBoundarySourceId':full_boundary[328]['sourceId']},
   'verified':True
 },
 'livePin': {'repository':REPO,'pullRequest':PR,'branch':BRANCH,'head':HEAD,'tree':TREE,'state':'OPEN','isDraft':True,'remoteBranchHead':HEAD,'pullRefHead':HEAD}
}
write_json(OUT/'input-verification.json',checksums)

summary={
 'artifact':'slskdN PR #409 W57 ranks 303–327 third-party cross-audit',
 'repository':REPO,'pullRequest':PR,'branch':BRANCH,'head':HEAD,'tree':TREE,'state':'OPEN','isDraft':True,
 'window':'W57 ranks 303–327','nextBoundaryRank':328,'reviewedCells':300,'sourceCount':25,'localeCount':12,'productionCallerOccurrences':42,
 'dispositionCounts':dict(collections.Counter(r['auditDisposition'] for r in ledger)),
 'primaryDecisionCounts':dict(collections.Counter(r['primaryDecision'] for r in ledger)),
 'blindDispositionCounts':dict(collections.Counter(r['blindDisposition'] for r in ledger)),
 'disagreementRows':len(disagreements),
 'selectedCorrectionRanks':sorted({r['continuationRank'] for r in ledger if r['auditDisposition']=='correction'}),
 'selectedRefinementCells':[r['auditId'] for r in ledger if r['auditDisposition']=='refinement'],
 'heldCells':[r['auditId'] for r in ledger if r['auditDisposition']=='hold'],
 'unresolvedSemanticQuestion':'Rank 319 “recommendation seeds”: caller says to play more local tracks, but the packets provide no product definition or approved locale terminology. Hold all 12 locales pending product guidance.',
 'packetDefect':'The lastSelected and nextBoundary fields in selection-and-boundary.json are invalid (ranks 304 and 305). The 27-row full boundary list plus 25 selected inventory rows and 300 cell rows establish ranks 303–327 and next boundary 328.',
 'structuralChecks':{'crossAuditTargetsChecked':300,'crossAuditPlaceholderMismatches':0,'crossAuditMarkupMismatches':0,'crossAuditNumericMismatches':0,'crossAuditEdgeWhitespaceMismatches':0,'reviewerSelectedAndCandidateTargetsChecked':600,'reviewerTargetStructuralMismatches':0,'protectedLiteralChecks':sum(len(r['integrityChecks']['protectedLiterals']) for r in ledger)*3,'protectedLiteralMismatches':0},
 'nativeSpeakerApproval':False,
 'reviewLimit':'This cross-audit provides machine-assisted semantic adjudication using the pinned English, current translations, caller excerpts, and two sealed reviews. It does not constitute native-speaker approval.',
 'repositoryOrPREdited':False,'testsBuildsScansCIWorkflowBrowserMergeReleaseOrTagActions':False
}
write_json(OUT/'summary.json',summary)

live={
 'repository':REPO,'pullRequest':PR,'url':'https://github.com/snapetech-org/slskdN/pull/409',
 'state':'OPEN','isDraft':True,'baseRefName':'main','headRefName':BRANCH,'headRefOid':HEAD,
 'headTree':TREE,'remoteBranchHead':HEAD,'pullRefHead':HEAD,
 'verifiedAt':'2026-11-03','verification':'gh pr view, gh api commit tree, and git ls-remote branch plus refs/pull/409/head',
 'matchesExpected':True
}
write_json(OUT/'live-pr-verification.json',live)

readme='''# slskdN PR #409 W57 third-party cross-audit\n\nThis sealed audit covers 300 locale cells for continuation ranks 303–327 at PR head `'''+HEAD+'''`, tree `'''+TREE+'''`. The live PR and both remote refs were checked before adjudication.\n\n## Disposition\n\n- 276 accept-current\n- 11 corrections\n- 1 wording refinement\n- 12 holds\n\nThe 12 holds are all locales for rank 319, “Play more tracks locally to build recommendation seeds.” The pinned caller is an empty-state prompt, but no packet defines “recommendation seeds” or supplies approved localized terminology.\n\nThe correction at rank 322 Indonesian changes “Saham” (financial stocks) to “Folder bersama” (shared folder), based on the caller being the System/Shares table. This is moderate confidence because the excerpt does not include row values.\n\n## Boundary defect\n\n`selection-and-boundary.json` has invalid `lastSelected` and `nextBoundary` fields (ranks 304 and 305). Those fields were excluded. The complete `selection-boundary.jsonl`, 25 inventory rows, and 300 input cells establish ranks 303–327; the next boundary is rank 328.\n\n## Integrity and limits\n\nThe candidate-free input, primary packet, and blind packet checksum lists pass. The audit independently rechecked all 300 source/current hashes and 42 caller references. Placeholder, markup, numeric token, edge whitespace, and protected-literal checks all pass on selected targets. `Soulseek`, `Lidarr`, `{tier}`, and `{peerId}` are preserved where required. No native speaker approved these outputs.\n\nSee `cross-audit-ledger.jsonl` for every cell, `disagreements.jsonl` for reviewer conflicts, `input-verification.json` for packet evidence, and `summary.json` for counts. Run `sha256sum -c SHA256SUMS.txt` from this directory to verify the sealed artifacts.\n'''
(OUT/'README.md').write_text(readme,encoding='utf-8')

# Hash all deliverables except the checksum list itself.
manifest_files=[]
for path in sorted(OUT.iterdir()):
    if path.name in {'SHA256SUMS.txt','manifest.json'} or not path.is_file(): continue
    data=path.read_bytes()
    manifest_files.append({'path':path.name,'bytes':len(data),'sha256':sha(data)})
write_json(OUT/'manifest.json',{'artifact':'slskdN PR #409 W57 third-party cross-audit','files':manifest_files,'ledgerRows':len(ledger),'disagreementRows':len(disagreements),'head':HEAD,'tree':TREE})
with (OUT/'SHA256SUMS.txt').open('w',encoding='utf-8') as f:
    for path in sorted(OUT.iterdir()):
        if path.name=='SHA256SUMS.txt' or not path.is_file(): continue
        f.write(f'{sha(path.read_bytes())}  {path.name}\n')
print(json.dumps({'output':str(OUT),'dispositionCounts':summary['dispositionCounts'],'disagreementRows':len(disagreements),'ledgerSha256':sha((OUT/'cross-audit-ledger.jsonl').read_bytes()),'manifestFiles':len(manifest_files)+1},ensure_ascii=False,indent=2))
