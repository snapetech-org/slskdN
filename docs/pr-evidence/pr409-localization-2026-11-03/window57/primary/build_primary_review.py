#!/usr/bin/env python3
"""Primary semantic review of slskdN PR #409 W57 from candidate-free input only."""
from __future__ import annotations
import collections, hashlib, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parent
INPUT=ROOT/'input'
REPO='snapetech-org/slskdN'; PR=409
HEAD='6b09b3c7bf7de69c316ba3e2503dc450004c9b59'
TREE='a5f9b792875d341a49208d0785bfff28aa9092d7'
BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PH=re.compile(r'\{[^{}]+\}')
TAG=re.compile(r'</?[A-Za-z][^>]*>')
NUM=re.compile(r'\d+')

# Primary recommendations are recorded only after reviewing each candidate-free
# source/current cell and the pinned caller context.
PROPOSALS={}
HOLDS={}
def propose(rank,loc,target,kind,rationale,confidence='moderate'):
    PROPOSALS[(rank,loc)]={'decision':kind,'target':target,'rationale':rationale,'confidence':confidence}
def hold(rank,loc,reason): HOLDS[(rank,loc)]=reason

# Rank 310: this is the Pod security workflow card title; make the Pod relation explicit.
propose(310,'es','Verificación de pertenencia al Pod','correction','The pinned card is the security workflow for verifying membership in a Pod. “grupo Pod” is redundant and less direct; retain the product entity name Pod.')
propose(310,'vi','Xác minh tư cách thành viên của Pod','correction','The pinned card verifies membership in a Pod for security. The current translation says group membership but omits the named Pod entity.')
# Rank 315: preserve the Soulseek product name and express “legacy” as older clients, not inherited clients.
propose(315,'pt-BR','Permitir que clientes antigos do Soulseek se conectem por meio de uma ponte','correction','The caller is the Bridge configuration toggle. “Herdados” means inherited and misstates legacy clients; “antigos” expresses older client versions. Preserve Soulseek.')
propose(315,'vi','Cho phép các ứng dụng Soulseek phiên bản cũ kết nối qua cầu nối','correction','The caller is the Bridge configuration toggle. “Kế thừa” means inherited and is an unnatural rendering of legacy clients. Preserve Soulseek and express older client versions.')
# Rank 317: exact trust tier and peer ID are interpolated by the pinned formatter.
propose(317,'zh-Hant','來源：{tier} {peerId}','correction','The pinned formatter labels a provenance line followed by the trust tier and peer identifier. The current 出生 means birth; 來源 correctly means source/provenance. Preserve both placeholders exactly.')
# Rank 318: this aria-label names the Lidarr setting that lets completed-download imports replace existing files.
propose(318,'es','Activar la opción de Lidarr para reemplazar archivos existentes','correction','The pinned checkbox controls the Lidarr replace-existing-files option. The current wording says Lidarr replaces the setting itself; name the option and preserve Lidarr.')
propose(318,'hi','मौजूदा फ़ाइलों को बदलने की Lidarr सेटिंग चालू करें','correction','The pinned checkbox controls the setting that allows Lidarr imports to replace existing files. The current wording is ungrammatical and obscures the setting; preserve Lidarr.')
propose(318,'id','Aktifkan pengaturan Lidarr untuk mengganti file yang sudah ada','correction','The pinned checkbox enables Lidarr’s replace-existing-files setting. The current wording is ungrammatical; preserve Lidarr and the existing-file meaning.')
propose(318,'vi','Bật cài đặt cho phép Lidarr thay thế các tệp hiện có','correction','The pinned checkbox enables the setting that lets Lidarr imports replace existing files. The current word order says Lidarr replaces a setting; preserve Lidarr.')
# Rank 322: System/Shares ShareTable region. Indonesian saham means financial stocks, not file shares.
propose(322,'id','Folder bersama yang dikonfigurasi','correction','The pinned caller labels the System/Shares table region. “Saham” means financial stocks; this heading refers to configured shared folders.')
# Rank 319: the exact algorithmic sense of “recommendation seeds” is not established by the pinned empty-state caller.
for loc in LOCALES:
    hold(319,loc,'The pinned caller is an empty-state instruction to play more local tracks, but the packet does not define what data the product calls “recommendation seeds” or provide approved localized terminology. Hold pending product terminology; do not substitute a guessed algorithmic meaning.')


def sha(value): return hashlib.sha256(value if isinstance(value,bytes) else value.encode('utf-8')).hexdigest()
def jread(path): return json.loads(path.read_text(encoding='utf-8'))
def jlread(path): return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]
def write_json(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def write_jsonl(path,rows): path.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows),encoding='utf-8')
def counter_tokens(text,rx): return dict(sorted(collections.Counter(rx.findall(text)).items()))

# Verify the exact candidate-free packet before reviewing.
input_checks=[]
for line in (INPUT/'PACKET-SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
    digest,rel=line.split(maxsplit=1); rel=rel.strip(); p=INPUT/rel
    actual=sha(p.read_bytes()) if p.is_file() else None
    if actual!=digest: raise SystemExit(f'candidate-free input checksum mismatch: {rel}')
    input_checks.append({'path':rel,'sha256':actual,'verified':True})
manifest=jread(INPUT/'manifest.json'); att=jread(INPUT/'head-tree-attestation.json')
live={'repository':REPO,'pullRequest':PR,'state':'OPEN','isDraft':True,'baseRefName':'main','branch':BRANCH,
      'head':HEAD,'tree':TREE,'remoteBranchHead':HEAD,'verification':'gh PR + remote branch + refs/pull/409/head + GitHub commit tree API'}
if not manifest.get('candidateFree'): raise SystemExit('input is not candidate-free')
for obj in (manifest,att):
    if str(obj.get('repository','')).lower()!=REPO.lower() or obj.get('pullRequest')!=PR or obj.get('head')!=HEAD or obj.get('tree')!=TREE: raise SystemExit('packet exact head/tree mismatch')
if manifest.get('sourceCount')!=25 or manifest.get('cellCount')!=300 or manifest.get('locales')!=LOCALES: raise SystemExit('packet scope mismatch')
if att.get('state')!='OPEN' or att.get('isDraft') is not True or att.get('branch')!=BRANCH or att.get('remoteBranchHead')!=HEAD: raise SystemExit('attested PR/branch mismatch')
write_json(ROOT/'live-pr-verification.json',live)

cells=jlread(INPUT/'source-current-cells.jsonl')
contexts=jlread(INPUT/'caller-contexts.jsonl')
structure=jlread(INPUT/'catalog-structure.jsonl')
inventory=jlread(INPUT/'source-inventory-selection.jsonl')
boundaries=jlread(INPUT/'selection-boundary.jsonl')
summary_input=jread(INPUT/'selection-and-boundary.json')
if len(cells)!=300 or len(contexts)!=25 or len(structure)!=12 or len(inventory)!=25: raise SystemExit('packet row-count mismatch')
if sorted({r['continuationRank'] for r in cells})!=list(range(303,328)): raise SystemExit('cell rank coverage mismatch')
if any(sum(1 for r in cells if r['continuationRank']==rank)!=12 for rank in range(303,328)): raise SystemExit('locale coverage mismatch')
if sorted({r['locale'] for r in cells},key=LOCALES.index)!=LOCALES: raise SystemExit('locale order mismatch')
if len(boundaries)!=27 or [r['continuationRank'] for r in boundaries]!=list(range(302,329)): raise SystemExit('boundary-list coverage mismatch')
if boundaries[0]['role']!='previous-boundary-W56' or boundaries[0]['continuationRank']!=302 or boundaries[-1]['role']!='next-boundary-W58' or boundaries[-1]['continuationRank']!=328: raise SystemExit('boundary-list pin mismatch')

# The JSON boundary summary contradicts the complete boundary JSONL. Keep the discrepancy visible.
boundary_summary_discrepancy={
 'file':'input/selection-and-boundary.json',
 'finding':'lastSelected is rank 304 and nextBoundary is rank 305 (also labeled selected-W57); the complete selection-boundary.jsonl instead lists selected ranks 303–327 and next boundary 328.',
 'resolutionForThisReview':'The rank set is independently confirmed by all 300 source-current cells and all 25 source-inventory-selection rows, plus the 27-row selection-boundary.jsonl. The discrepancy is retained as a packet defect and does not change the reviewed 303–327 cells.',
 'requiresPacketCorrectionBeforeApplication':True
}

structure_by_locale={r['locale']:r for r in structure}
ctx_by_rank={r['continuationRank']:r for r in contexts}
inv_by_rank={r['continuationRank']:r for r in inventory}
for rank in range(303,328):
    c=ctx_by_rank.get(rank); inv=inv_by_rank.get(rank)
    if not c or not inv: raise SystemExit(f'missing caller or inventory row {rank}')
    if c['sourceId']!=inv['sourceId'] or c['sourceSha256']!=inv['sourceSha256'] or c['source']!=inv['source']: raise SystemExit(f'caller/inventory source mismatch at rank {rank}')
    if inv.get('excluded') is not False or inv.get('localeCoverage')!=12: raise SystemExit(f'inventory exclusion/coverage issue at rank {rank}')
    if c['sourceSha256']!=sha(c['source']): raise SystemExit(f'source context hash mismatch at rank {rank}')

# Verify that each per-cell caller pin corresponds to a retained bounded caller context.
caller_occurrences=0
for rank in range(303,328):
    ctx=ctx_by_rank[rank]
    if ctx['productionCallerCount']!=len(ctx['callers']): raise SystemExit(f'caller count mismatch at rank {rank}')
    caller_occurrences+=len(ctx['callers'])
    cellrefs=[r for r in cells if r['continuationRank']==rank][0]['callerRefs']
    expected={(r['path'],r['line'],r['lineSha256'],r['fileSha256'],r['gitBlob']) for r in ctx['callers']}
    observed={(r['path'],r['line'],r['lineSha256'],r['fileSha256'],r['gitBlob']) for r in cellrefs}
    if expected!=observed: raise SystemExit(f'caller pin mismatch at rank {rank}')
if caller_occurrences!=42: raise SystemExit(f'caller occurrence count mismatch: {caller_occurrences}')

ledger=[]; held_rows=[]; change_by_locale=collections.Counter(); change_by_rank=collections.Counter(); decisions=collections.Counter()
placeholder_checks=markup_checks=numeric_checks=edge_space_checks=0
protected_current_issues=[]; protected_candidate_issues=[]
protected_by_rank={315:['Soulseek'],316:['Lidarr'],318:['Lidarr']}
for c in sorted(cells,key=lambda r:(r['continuationRank'],LOCALES.index(r['locale']))):
    rank=c['continuationRank']; loc=c['locale']; key=(rank,loc); source=c['source']; current=c['currentTarget']; ctx=ctx_by_rank[rank]
    cat=structure_by_locale[loc]
    if c['sourceId']!=ctx['sourceId'] or c['source']!=ctx['source'] or c['sourceSha256']!=ctx['sourceSha256'] or sha(source)!=c['sourceSha256']: raise SystemExit(f'per-cell source pin mismatch {key}')
    if c['catalogPath']!=cat['catalogPath'] or c['catalogFileSha256']!=cat['sha256'] or c['catalogGitBlob']!=cat['gitBlob']: raise SystemExit(f'catalog pin mismatch {key}')
    if c['currentTargetSha256']!=sha(current): raise SystemExit(f'current target hash mismatch {key}')
    if c.get('containsCandidate') is not False or c.get('verdict') is not None: raise SystemExit(f'candidate/review data found in input {key}')
    source_ph=PH.findall(source); current_ph=PH.findall(current)
    source_tags=TAG.findall(source); current_tags=TAG.findall(current)
    source_nums=NUM.findall(source); current_nums=NUM.findall(current)
    if c['placeholderEvidence'].get('matches') is not (source_ph==current_ph): raise SystemExit(f'input placeholder assertion mismatch {key}')
    if c['markupEvidence'].get('matches') is not (source_tags==current_tags): raise SystemExit(f'input markup assertion mismatch {key}')
    if source_ph!=current_ph or source_tags!=current_tags or source_nums!=current_nums: raise SystemExit(f'current structural mismatch {key}')
    source_edge=(len(source)-len(source.lstrip()),len(source)-len(source.rstrip()))
    current_edge=(len(current)-len(current.lstrip()),len(current)-len(current.rstrip()))
    if source_edge!=current_edge: raise SystemExit(f'current edge-whitespace mismatch {key}')
    placeholder_checks+=1; markup_checks+=1; numeric_checks+=1; edge_space_checks+=1

    proposal=PROPOSALS.get(key); hold_reason=HOLDS.get(key)
    if proposal and hold_reason: raise SystemExit(f'conflicting decision {key}')
    if hold_reason:
        decision='hold'; target=None; rationale=hold_reason; confidence='low'
    elif proposal:
        decision=proposal['decision']; target=proposal['target']; rationale=proposal['rationale']; confidence=proposal['confidence']
    else:
        decision='accept-current'; target=None; confidence='moderate'
        rationale={
          303:'The pinned button calls handleGetOpinionStatistics; the current imperative means fetching statistics.',
          304:'The pinned tooltip describes a package dry-run that previews local registry changes without applying them; the current target preserves both actions.',
          305:'The pinned button loads descriptor retrieval and cache performance metrics; the current imperative and technical terms match that action.',
          306:'The pinned MusicBrainz result displays track.duration in minutes when present; the current value correctly labels an unknown track length/duration.',
          307:'The pinned role-check button checks a peer’s role in the selected Pod before authorizing an operation; the current target preserves the security action.',
          308:'The pinned caller uses this for the plural branch after starting a batch of smart-radio searches; the exact {count} placeholder is preserved.',
          309:'Both pinned callers add an allowed VPN destination to the draft policy; the current target names that destination action.',
          310:'The pinned card title names Pod membership verification, followed by the security description; the current targets convey that workflow.',
          311:'The pinned error branch reports failure to confirm room broadcast settings and invites retry; the current target preserves both.',
          312:'The pinned accessible name labels the warning-log filter; the current target names warning logs.',
          313:'The pinned fields accept image width and height in an x-separated value; the current target preserves both dimensions.',
          314:'The pinned uses are file, log, wishlist, and transfer table columns; the generic size label fits each column.',
          315:'The pinned Bridge setting allows legacy Soulseek clients to connect; the current target preserves that permission and the Soulseek name.',
          316:'The pinned pager loads the previous Lidarr album page; the current target preserves direction and product name.',
          317:'The pinned formatter emits provenance followed by trust tier and peer ID; the current target preserves the label and both placeholders.',
          318:'The pinned checkbox controls the Lidarr option that allows replacement of existing files during import; current target is adequate in this locale.',
          319:'Held across locales because the caller does not define the product-specific meaning of recommendation seeds.',
          320:'The pinned field accepts a username for friend-based sharing; the current target is a clear entry prompt.',
          321:'The pinned dashboard uses Quality for both a score label and quality class; the current target is an appropriate shared label.',
          322:'The pinned caller is the System/Shares table region; the current target means configured shares.',
          323:'The pinned formatter inserts a localized yes/no value after Enabled; the current target preserves the label and exact placeholder.',
          324:'The pinned control toggles the wishlist card view; the current target preserves that display action.',
          325:'The pinned smart-radio reason identifies a similar-track starting seed; the current target expresses that starting-point meaning.',
          326:'The pinned checkbox syncs wanted albums into the Wishlist feature; the current target preserves direction and intent.',
          327:'The pinned FTP password input labels the value as optional; the current target states that accurately.'
        }[rank]
        hold_reason=None

    selected=target if target is not None else current
    selected_ph=PH.findall(selected); selected_tags=TAG.findall(selected); selected_nums=NUM.findall(selected)
    selected_edge=(len(selected)-len(selected.lstrip()),len(selected)-len(selected.rstrip()))
    if selected_ph!=source_ph or selected_tags!=source_tags or selected_nums!=source_nums or selected_edge!=source_edge: raise SystemExit(f'selected structural mismatch {key}')
    required=protected_by_rank.get(rank,[])
    literal_checks=[]
    for literal in required:
        sc=source.count(literal); cc=current.count(literal); tc=selected.count(literal)
        if cc!=sc: protected_current_issues.append({'rank':rank,'locale':loc,'literal':literal,'sourceCount':sc,'currentCount':cc})
        if target is not None and tc!=sc: protected_candidate_issues.append({'rank':rank,'locale':loc,'literal':literal,'sourceCount':sc,'targetCount':tc})
        literal_checks.append({'literal':literal,'sourceCount':sc,'currentCount':cc,'selectedCount':tc,'currentPreserved':cc==sc,'selectedPreserved':tc==sc})
    if target is not None:
        if target==current: raise SystemExit(f'no-op proposal {key}')
        change_by_locale[loc]+=1; change_by_rank[str(rank)]+=1
    if decision=='hold':
        held_rows.append({'continuationRank':rank,'sourceId':c['sourceId'],'source':source,'locale':loc,'catalogPath':c['catalogPath'],
                          'currentTarget':current,'currentTargetSha256':c['currentTargetSha256'],'holdReason':hold_reason,
                          'callerContextEvidence':ctx})
    decisions[decision]+=1
    ledger.append({
      'schemaVersion':1,'window':'W57 ranks 303–327','repository':REPO,'pullRequest':PR,'head':HEAD,'tree':TREE,
      'continuationRank':rank,'historicalSourceOrdinal':None,'sourceId':c['sourceId'],'source':source,'sourceSha256':c['sourceSha256'],
      'locale':loc,'catalogPath':c['catalogPath'],'catalogFileSha256':c['catalogFileSha256'],'catalogGitBlob':c['catalogGitBlob'],
      'currentTarget':current,'currentTargetSha256':c['currentTargetSha256'],
      'callerEvidence':{'productionCallerCount':ctx['productionCallerCount'],'callers':ctx['callers'],
                        'callerContextSha256':c['callerContextSha256'],'perCellCallerRefs':c['callerRefs']},
      'decision':decision,'candidateTarget':target,'candidateTargetSha256':sha(target) if target is not None else None,
      'selectedTarget':selected,'selectedTargetSha256':sha(selected),'rationale':rationale,'confidence':confidence,
      'holdReason':hold_reason,'protectedLiteralsRequired':required,'protectedLiteralChecks':literal_checks,
      'integrityChecks':{'sourceTargetHashVerified':True,'currentTargetHashVerified':True,
        'sourcePlaceholderTokenSequence':source_ph,'currentPlaceholderTokenSequence':current_ph,'selectedPlaceholderTokenSequence':selected_ph,
        'placeholderParity':source_ph==selected_ph,'sourceMarkupTags':source_tags,'currentMarkupTags':current_tags,'selectedMarkupTags':selected_tags,
        'markupParity':source_tags==selected_tags,'sourceNumericTokens':source_nums,'currentNumericTokens':current_nums,'selectedNumericTokens':selected_nums,
        'numericParity':source_nums==selected_nums,'sourceEdgeWhitespace':source_edge,'currentEdgeWhitespace':current_edge,
        'selectedEdgeWhitespace':selected_edge,'edgeWhitespaceParity':source_edge==selected_edge,'runtimeExpressionsEvaluated':False},
      'nativeSpeakerApproved':False
    })
if len(ledger)!=300 or len(held_rows)!=12 or decisions['correction']!=10 or decisions['accept-current']!=278: raise SystemExit(f'ledger counts unexpected {dict(decisions)}')
if protected_candidate_issues: raise SystemExit('proposed target fails protected literal check')
write_jsonl(ROOT/'primary-decisions.jsonl',ledger)
write_jsonl(ROOT/'holds.jsonl',held_rows)
write_json(ROOT/'protected-literal-audit.json',{
 'protectedLiteralsBySource':{'315':['Soulseek'],'316':['Lidarr'],'318':['Lidarr']},
 'placeholdersCheckedExactly':['{count}','{tier}','{peerId}','{enabled}'],
 'currentValueIssues':protected_current_issues,'candidateIssues':protected_candidate_issues,
 'localizableNamedFeatureTerms':['Wishlist','Pod'],
 'note':'Brand names Soulseek and Lidarr, runtime placeholders, source markup/numerics, and edge whitespace are protected. Wishlist and Pod are treated as localizable feature/domain terms because the packet provides no exact-literal glossary.'})
write_json(ROOT/'input-integrity-notes.json',{
 'verifiedCandidateFreePacketFiles':input_checks,
 'expectedHead':HEAD,'expectedTree':TREE,'livePrPinsVerified':live,
 'boundarySummaryDiscrepancy':boundary_summary_discrepancy,
 'cellsReviewedFromPinnedCandidateFreePacketOnly':True,'laterReviewerOutputInspected':False})
summary={
 'artifact':'slskdN PR #409 W57 primary semantic review',
 'repository':REPO,'pullRequest':PR,'pullRequestUrl':'https://github.com/snapetech-org/slskdN/pull/409',
 'state':'OPEN','isDraft':True,'branch':BRANCH,'head':HEAD,'tree':TREE,'window':'W57 ranks 303–327',
 'reviewMode':'primary semantic review from candidate-free exact-head input only; no later reviewer output inspected',
 'candidateFreeInputManifestSha256':sha((INPUT/'manifest.json').read_bytes()),
 'candidateFreeChecksumListSha256':sha((INPUT/'PACKET-SHA256SUMS.txt').read_bytes()),'verifiedInputFiles':len(input_checks),
 'sourceCount':25,'localeCount':12,'reviewedCells':len(ledger),'sourceInventoryRanks':'303–327',
 'sourceRows':25,'productionCallerOccurrencesVerified':caller_occurrences,'sourceRowsWithPinnedCallerContext':len(contexts),
 'decisionCounts':dict(sorted(decisions.items())),'recommendedChanges':sum(change_by_locale.values()),
 'changesByLocale':dict(sorted(change_by_locale.items())),'changesByRank':dict(sorted(change_by_rank.items(),key=lambda x:int(x[0]))),
 'holdCount':len(held_rows),'holdsByRank':dict(collections.Counter(str(r['continuationRank']) for r in held_rows)),
 'placeholderChecks':placeholder_checks,'placeholderMismatchCount':0,'markupChecks':markup_checks,'markupMismatchCount':0,
 'numericTokenChecks':numeric_checks,'numericTokenMismatchCount':0,'edgeWhitespaceChecks':edge_space_checks,'edgeWhitespaceMismatchCount':0,
 'protectedLiteralCandidateIssues':len(protected_candidate_issues),'protectedLiteralCurrentIssues':len(protected_current_issues),
 'protectedLiteralCurrentIssueDetails':protected_current_issues,
 'unresolvedTerminology':'Rank 319 “recommendation seeds” held in all 12 locales pending product meaning/glossary.',
 'packetBoundaryIssue':boundary_summary_discrepancy,
 'runtimeExpressionsEvaluated':False,'nativeSpeakerApproval':False,'repositoryOrPREdited':False,
 'testsBuildsScansCIWorkflowBrowserMergeReleaseOrTagActions':False
}
write_json(ROOT/'summary.json',summary)
print(json.dumps(summary,ensure_ascii=False,indent=2))
