#!/usr/bin/env python3
"""Build exact-head W38 primary semantic dispositions in task scratch only."""
import collections, hashlib, json, re, subprocess
from pathlib import Path

ROOT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window38-primary-20261102')
REPO = Path('/mnt/disks/scratch/task-worktrees/localization-20261102/slskdn-pr409-w36-review')
HEAD = '2be3fa4dd46a0f0f49adad342f289721e4777035'
TREE = 'f838ae565086dec8639f8a54aa4c7d4572342b5f'
SOURCE_TREE = '594e56c3f439bad476b1bd57e0de1665c62fa1bb'
FORMAL = {json.loads(line)['id'] for line in (ROOT/'formal-cell-ids.jsonl').read_text().splitlines() if line.strip()}

# Proposals are limited to clear meaning, terminology, configuration-key, and data-type errors.
CANDIDATES = {
 ('src_084ee5f9dc342f13','zh-Hans'): ('无法保存发行雷达订阅。', 'The caller is an artist release alert; 发行 is the music-release term here.', 'moderate'),
 ('src_084ee5f9dc342f13','zh-Hant'): ('無法儲存發行雷達訂閱。', 'The caller is an artist release alert; 發行 is the music-release term here.', 'moderate'),
 ('src_084ee5f9dc342f13','fr'): ('Impossible d’enregistrer l’abonnement au radar des sorties.', 'Publication means publishing; the panel subscribes to alerts for music releases.', 'high'),
 ('src_084ee5f9dc342f13','ar'): ('تعذّر حفظ الاشتراك في رادار الإصدارات.', 'The current Arabic order is unnatural; this names a subscription to new-release alerts.', 'high'),

 ('src_0894b7f847440bec','zh-Hans'): ('播放器已隐藏', '玩家 means a person or game player; this UI status is for the music player.', 'high'),
 ('src_0894b7f847440bec','de'): ('Player ausgeblendet', 'Spieler suggests a person or game player; the icon and caller identify the media player.', 'moderate'),
 ('src_0894b7f847440bec','fr'): ('Lecteur masqué', 'Joueur means a person or game player; this caller is the media player.', 'high'),
 ('src_0894b7f847440bec','pt-BR'): ('Reprodutor oculto', 'Jogador means a person or game player; this caller is the media player.', 'high'),
 ('src_0894b7f847440bec','ar'): ('تم إخفاء مشغل الوسائط', 'اللاعب means a person or athlete; this status refers to the media player.', 'high'),
 ('src_0894b7f847440bec','zh-Hant'): ('播放器已隱藏', '玩家 means a person or game player; this UI status is for the music player.', 'high'),
 ('src_0894b7f847440bec','vi'): ('Trình phát đã bị ẩn', 'Người chơi means a person or game player; this caller is the media player.', 'high'),
 ('src_0894b7f847440bec','id'): ('Pemutar media disembunyikan', 'Pemain means a person or game player; this caller is the media player.', 'high'),

 ('src_08b30b1aba98a1d4','zh-Hans'): ('原生 MilkDrop 形状片段', 'MilkDrop is the visualizer name; 奶滴 translates its parts literally and loses the product name.', 'high'),
('src_08b30b1aba98a1d4','hi'): ('मूल MilkDrop आकार का अंश', 'MilkDrop is the visualizer name; preserve the exact product name rather than transliterating it as milk drop.', 'moderate'),
 ('src_08b30b1aba98a1d4','zh-Hant'): ('原生 MilkDrop 形狀片段', 'MilkDrop is the visualizer name; 奶滴 translates its parts literally and loses the product name.', 'high'),

 ('src_08cddda722527ffd','zh-Hans'): ('搜索片段', 'This button searches tracks derived from a segment; 部分 means a generic part.', 'high'),
 ('src_08cddda722527ffd','ar'): ('ابحث عن المقطع', 'This is an action to search the selected audio segment; قسم means a section.', 'high'),
 ('src_08cddda722527ffd','zh-Hant'): ('搜尋片段', 'This button searches tracks derived from a segment; 部分 means a generic part.', 'high'),

 ('src_08f271887ce94707','zh-Hans'): ('M', 'The same label is a keyboard key, memory-size unit, and QR/error-correction code; preserve the Latin symbol.', 'high'),
 ('src_08f271887ce94707','hi'): ('M', 'The same label is a keyboard key, memory-size unit, and QR/error-correction code; preserve the Latin symbol.', 'high'),
 ('src_08f271887ce94707','ar'): ('M', 'The same label is a keyboard key, memory-size unit, and QR/error-correction code; preserve the Latin symbol.', 'high'),
 ('src_08f271887ce94707','ko'): ('M', 'The same label is a keyboard key, memory-size unit, and QR/error-correction code; preserve the Latin symbol.', 'high'),
 ('src_08f271887ce94707','zh-Hant'): ('M', 'The same label is a keyboard key, memory-size unit, and QR/error-correction code; preserve the Latin symbol.', 'high'),

 ('src_090269ba94d47580','fr'): ('IDs des pairs cibles (séparés par des virgules)', 'The source has plural IDs; make the French noun plural to agree with séparés.', 'high'),

 ('src_090512d93fcc3c0d','ar'): ('التكاملات', 'The settings page groups several integration providers, so the plural heading is more exact.', 'moderate'),

 ('src_090940bae1e24f54','zh-Hans'): ('查询：', 'This labels a SongID search query value; 询问 means an inquiry or question.', 'high'),
 ('src_090940bae1e24f54','hi'): ('खोज क्वेरी:', 'This labels the submitted SongID search query, not a question.', 'high'),
 ('src_090940bae1e24f54','ar'): ('الاستعلام:', 'استفسار means an inquiry; this label introduces the actual search query.', 'high'),
 ('src_090940bae1e24f54','ko'): ('검색어:', '질문 means a question; this label introduces the actual search term.', 'high'),
 ('src_090940bae1e24f54','zh-Hant'): ('查詢：', '詢問 means an inquiry or question; this label introduces the actual search query.', 'high'),
 ('src_090940bae1e24f54','id'): ('Kueri:', 'Pertanyaan means a question; this label introduces the actual search query.', 'high'),

 ('src_09155891b81b403c','zh-Hans'): ('正在加载共享内容', 'The inbox is loading shared items; adding 内容 makes the status phrase natural and clear.', 'moderate'),
 ('src_09155891b81b403c','hi'): ('साझा की गई फ़ाइलें लोड हो रही हैं', 'शेयर is ambiguous with financial shares; the inbox is loading shared files.', 'high'),
 ('src_09155891b81b403c','de'): ('Freigaben werden geladen', 'Anteile suggests financial or fractional shares; Freigaben is the usual file-sharing term.', 'high'),
 ('src_09155891b81b403c','ar'): ('جارٍ تحميل الملفات المشتركة', 'الأسهم means financial shares; the inbox is loading files that were shared.', 'high'),
 ('src_09155891b81b403c','zh-Hant'): ('正在載入共享內容', 'Adding 內容 clarifies that the inbox is loading shared items.', 'moderate'),
 ('src_09155891b81b403c','vi'): ('Đang tải nội dung được chia sẻ', 'Lượt chia sẻ sounds like a count of shares; this is a loading status for shared content.', 'high'),
 ('src_09155891b81b403c','id'): ('Memuat file yang dibagikan', 'Bagian means a part or section; the inbox is loading files shared with the user.', 'high'),

 ('src_091a998e1a186d71','hi'): ('प्रसारण रोकें', 'Use the standard polite imperative for a room-control button.', 'moderate'),

 ('src_09230b3dbc35635f','hi'): ('विफलता', 'The label counts failed checks; the noun विफलता fits this statistic better than an adjective.', 'moderate'),
 ('src_09230b3dbc35635f','fr'): ('Échec', 'Échouer is an infinitive; the statistic label names a failure.', 'high'),
 ('src_09230b3dbc35635f','pt-BR'): ('Falha', 'Falhar is an infinitive; the statistic label names a failure.', 'high'),
 ('src_09230b3dbc35635f','ar'): ('فشل', 'يفشل is a verb; the statistic and status label needs a noun.', 'high'),
 ('src_09230b3dbc35635f','ko'): ('실패', '실패하다 is a verb; this statistic label names the failed outcome.', 'high'),

 ('src_0924a671165fef5a','hi'): ('कूलडाउन अवधि', 'शांत हो जाओ is an instruction to calm down; this label names an automation waiting interval.', 'high'),
 ('src_0924a671165fef5a','fr'): ('Période d’attente', 'Refroidir is a verb; the value beside this label is an automation waiting period.', 'high'),
 ('src_0924a671165fef5a','pt-BR'): ('Intervalo de espera', 'Esfriar is a verb; the value beside this label is an automation waiting interval.', 'high'),
 ('src_0924a671165fef5a','ar'): ('فترة الانتظار', 'ترطيب means moistening or cooling; this automation label names a waiting interval.', 'high'),
 ('src_0924a671165fef5a','vi'): ('Thời gian chờ', 'The caller is an automation recipe interval, not a game ability cooldown.', 'moderate'),
 ('src_0924a671165fef5a','id'): ('Masa jeda', 'Pendinginan means cooling; this automation label names a pause between runs.', 'high'),

 ('src_093fc8439d0ade12','ar'): ('في إعدادات الخادم لاستخدام غرف Pod وميزة الاكتشاف.', 'غرف الكبسولة is a literal capsule-room rendering; retain the product term Pod.', 'moderate'),
 ('src_093fc8439d0ade12','ko'): ('포드 룸 및 탐색 기능을 사용하려면 서버 구성에서', 'Discovery is broader than search here; 탐색 기능 better names the discovery feature.', 'moderate'),
 ('src_093fc8439d0ade12','vi'): ('trong cấu hình máy chủ để sử dụng phòng Pod và tính năng khám phá.', 'phòng nhóm means group rooms; retain the product term Pod and name discovery as a feature.', 'moderate'),

 ('src_094e2630f1d48460','ar'): ('لا تتوفر بيانات للفنان', 'The current Arabic construction is awkward; this is the empty artist-data state.', 'high'),
}

SOURCE_REASONS = {
 'src_084759c8b290636e':'Heading for the security overview section.',
 'src_084ee5f9dc342f13':'Error toast when saving an artist release-alert subscription.',
 'src_086d9ef0599694b9':'Toast confirming queued remediation for automatically repairable library issues.',
 'src_087410a9bffaa497':'Evidence heading introducing reasons against a SongID match.',
 'src_088998ef3f0eb88d':'Validation message shown when sending a blank active-conversation message.',
 'src_0894b7f847440bec':'Status text beside a music icon when the player is hidden.',
 'src_08a3e8e660874d8a':'Action button in the modal that saves download filters.',
 'src_08b041935798fbf6':'Current-user label in a chat transcript.',
 'src_08b30b1aba98a1d4':'Accessibility/title label for a native MilkDrop visualizer shape fragment.',
 'src_08cddda722527ffd':'Action button that searches tracks derived from the selected segment.',
 'src_08e11c585cb99736':'Pagination label for result count per page.',
 'src_08f271887ce94707':'Ambiguous shared label used for a key, unit and technical setting; preserve M as a symbol.',
 'src_090269ba94d47580':'Form label for comma-separated target peer IDs.',
 'src_090512d93fcc3c0d':'Settings navigation/category heading for service integrations.',
 'src_090940bae1e24f54':'Label introducing a SongID search query value.',
 'src_090c731ea55b379e':'Message emitted only when exactly one texture asset was skipped; preserve {count} and {fileNames}.',
 'src_09155891b81b403c':'Loading status for shared items in the SharedWithMe inbox.',
 'src_091a998e1a186d71':'Room-control button stops the broadcast but leaves local playback available.',
 'src_09230b3dbc35635f':'Statistic/status label for failed setup and network-health checks.',
 'src_0924a671165fef5a':'Automation recipe cooldown interval displayed beside its value.',
 'src_0925387b88eda8fc':'Tooltip clarifies that display metadata is saved without writing audio-file bytes.',
 'src_09298403b9c41b52':'Message says a notification route was recorded for an artist title.',
 'src_093fc8439d0ade12':'Help-text fragment completing Enable feature.Pods and describing the server configuration for Pod rooms and discovery.',
 'src_094e2630f1d48460':'Library-health table state when no artist data is available.',
 'src_09501d4b96861f65':'Success toast after a count of nearby graph searches starts.',
}
ADDITIONAL_PROTECTED = {
 'src_08f271887ce94707':['M'],
 'src_08b30b1aba98a1d4':['MilkDrop'],
}



def sha(v):
    if isinstance(v,str): v=v.encode('utf-8')
    return hashlib.sha256(v).hexdigest()

def git(*args):
    return subprocess.check_output(['git','-C',str(REPO),*args]).decode('utf-8').strip()

def jsonl_write(name, rows):
    raw=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows).encode('utf-8')
    (ROOT/name).write_bytes(raw)
    return sha(raw)

def cell_placeholders(s):
    return sorted(re.findall(r'\{[^{}]+\}',s))

manifest=json.loads((ROOT/'manifest.json').read_text())
preflight=json.loads((ROOT/'preflight.json').read_text())
rows=[json.loads(line) for line in (ROOT/'review-input.jsonl').read_text().splitlines() if line.strip()]
assert manifest['headCommit']==HEAD and manifest['tree']==TREE and manifest['sourceSubtreeTree']==SOURCE_TREE
assert git('rev-parse','HEAD')==HEAD and git('rev-parse','HEAD^{tree}')==TREE
assert git('rev-parse','HEAD:src/web/src')==SOURCE_TREE and git('status','--porcelain')==''
assert len(rows)==269 and len({r['id'] for r in rows})==269
assert len({r['sourceId'] for r in rows})==25
assert set(SOURCE_REASONS)=={r['sourceId'] for r in rows}
assert set(CANDIDATES)<= {(r['sourceId'],r['locale']) for r in rows}

# Re-read pinned locale catalogs and verify every source/current target row and protected literal.
catalog_hashes={}
for locale in manifest['currentCatalogFileSha256']:
    raw=subprocess.check_output(['git','-C',str(REPO),'show',f'{HEAD}:src/web/public/locales/{locale}.json'])
    assert sha(raw)==manifest['currentCatalogFileSha256'][locale]
    catalog_hashes[locale]=sha(raw)
    assert len(json.loads(raw))==6169

source_reasons=SOURCE_REASONS
counts=collections.Counter()
per_locale=collections.defaultdict(collections.Counter)
per_source=collections.defaultdict(collections.Counter)
decisions=[]; evidence=[]; candidates=[]
placeholder_mismatches=[]; protected_mismatches=[]
for r in rows:
    key=(r['sourceId'],r['locale'])
    candidate=CANDIDATES.get(key)
    target,reason,confidence=candidate if candidate else (None,source_reasons[r['sourceId']],'moderate')
    cell_id=r['id']
    assert sha(r['source'])==r['sourceSha256']
    assert r['id']==f"{r['locale']}:{r['sourceId']}"
    assert sha(r['target'])==r['targetSha256']
    if cell_placeholders(r['source'])!=sorted(r['placeholders']):
        placeholder_mismatches.append(cell_id)
    if cell_placeholders(r['target'])!=sorted(r['placeholders']):
        placeholder_mismatches.append(cell_id)
    for lit in r['protectedLiterals']:
        if lit not in r['target']: protected_mismatches.append((cell_id,lit,'current'))
    reviewer_literals=ADDITIONAL_PROTECTED.get(r['sourceId'],[])
    if candidate:
        if target == r['target']:
            raise SystemExit(f'candidate is a no-op: {cell_id}')
        if cell_placeholders(target)!=sorted(r['placeholders']):
            placeholder_mismatches.append((cell_id,'candidate'))
        for lit in [*r['protectedLiterals'],*reviewer_literals]:
            if lit not in target: protected_mismatches.append((cell_id,lit,'candidate'))
        verdict='correct'; candidate_hash=sha(target)
        counts['correct']+=1; per_locale[r['locale']]['correct']+=1; per_source[r['sourceId']]['correct']+=1
        candidates.append({'id':cell_id,'sourceId':r['sourceId'],'locale':r['locale'],'source':r['source'],
           'sourceSha256':r['sourceSha256'],'currentTarget':r['target'],'currentTargetSha256':r['targetSha256'],
           'candidateTarget':target,'candidateTargetSha256':candidate_hash,'confidence':confidence,'reason':reason,
           'placeholders':r['placeholders'],'protectedLiterals':r['protectedLiterals'],
           'additionalReviewerProtectedLiterals':reviewer_literals})
    else:
        verdict='keep'; candidate_hash=None
        counts['keep']+=1; per_locale[r['locale']]['keep']+=1; per_source[r['sourceId']]['keep']+=1
    decision={'id':cell_id,'verdict':verdict,'sourceSha256':r['sourceSha256'],
              'currentTargetSha256':r['targetSha256'],'window':38,'confidence':confidence,'reason':reason}
    if candidate:
        decision['target']=target
    decisions.append(decision)
    evidence.append({'id':cell_id,'sourceId':r['sourceId'],'locale':r['locale'],
        'source':r['source'],'sourceSha256':r['sourceSha256'],
        'currentTarget':r['target'],'currentTargetSha256':r['targetSha256'],
        'candidateTarget':target,'candidateTargetSha256':candidate_hash,
        'verdict':verdict,'confidence':confidence,'reason':reason,
        'callerRefs':[{'path':c['path'],'line':c['line'],'fileSha256':c['fileSha256'],'lineTextSha256':c['lineTextSha256']} for c in r['sourceCallsites']],
        'placeholders':r['placeholders'],'protectedLiterals':r['protectedLiterals'],
        'additionalReviewerProtectedLiterals':reviewer_literals,
        'currentAdditionalProtectedLiteralMismatches':[lit for lit in reviewer_literals if lit not in r['target']],
        'contextNote':('Caller concatenates this fragment after a separately localized Enable label and the code literal feature.Pods; review the composed sentence as a whole before applying.' if r['sourceId']=='src_093fc8439d0ade12' else None),
        'catalogPath':r['catalogPath'],'catalogKey':r['catalogKey'],
        'reviewInputRowSha256':r['rowSha256']})
if placeholder_mismatches or protected_mismatches:
    raise SystemExit(f'placeholder/protected-literal mismatch: {placeholder_mismatches} {protected_mismatches}')
if counts['correct']+counts['keep']!=len(rows): raise SystemExit('decision row count mismatch')
if len(candidates)!=len(CANDIDATES): raise SystemExit('candidate count mismatch')

# Ensure the manual review did not re-route any formal Spanish, exact-reuse, or held cell.
formal_ids={json.loads(x)['id'] for x in (ROOT/'formal-cell-ids.jsonl').read_text().splitlines() if x.strip()}
review_ids={r['id'] for r in rows}
assert not review_ids & formal_ids
assert len([json.loads(x) for x in (ROOT/'preserved-prior-routed.jsonl').read_text().splitlines() if x.strip()])==25
assert len([json.loads(x) for x in (ROOT/'preserved-spanish-reused.jsonl').read_text().splitlines() if x.strip()])==0
assert len([json.loads(x) for x in (ROOT/'preserved-prior-holds.jsonl').read_text().splitlines() if x.strip()])==50
assert preflight['manualCellOverlap']==0 and preflight['manualSourceKeyOverlap']==0
assert preflight['appliedOverlap']==0 and preflight['formalOverlap']==0 and preflight['holdSourceKeyOverlap']==0

review_decision_hash=jsonl_write('review-decisions.jsonl',decisions)
review_evidence_hash=jsonl_write('review-evidence.jsonl',evidence)
review_candidates_hash=jsonl_write('correction-candidates.jsonl',candidates)
review_holds_hash=jsonl_write('window38-review-holds.jsonl',[])
per_locale_counts={locale:dict(c) for locale,c in sorted(per_locale.items())}
per_source_counts={sid:dict(c) for sid,c in sorted(per_source.items()) if c['correct']}
row_to_caller_refs=sum(len(r['sourceCallsites']) for r in rows)
summary={
 'result':'PRIMARY_REVIEW_COMPLETE_PENDING_CROSS_REVIEW_NATIVE_SPEAKER_REVIEW_OUTSTANDING',
 'window':38,'repository':'snapetech-org/slskdN','pullRequest':409,
 'branch':'codex/slskdn-oidc-tooltip-localization-20261030',
 'livePrState':'OPEN','livePrDraft':True,'livePrMergeState':'CLEAN',
 'reviewBaseHead':HEAD,'reviewBaseTree':TREE,'sourceSubtreePath':'src/web/src','sourceSubtreeTree':SOURCE_TREE,
 'reviewInputSha256':sha((ROOT/'review-input.jsonl').read_bytes()),
 'reviewDecisionSha256':review_decision_hash,'reviewEvidenceSha256':review_evidence_hash,
 'correctionCandidatesSha256':review_candidates_hash,
 'reviewHoldsSha256':review_holds_hash,'newPrimaryHoldRows':0,'newPrimaryHoldSourceIds':0,
 'sourceKeys':25,'pendingCells':len(rows),'pendingCellCounts':dict(sorted(collections.Counter(r['locale'] for r in rows).items())),
 'verdictCounts':dict(counts),'perLocaleVerdicts':per_locale_counts,
 'correctionCellsByLocale':{loc:c['correct'] for loc,c in sorted(per_locale.items()) if c['correct']},
 'keepCellsByLocale':{loc:c['keep'] for loc,c in sorted(per_locale.items()) if c['keep']},
 'correctedSourceIds':sorted({sid for sid,_ in CANDIDATES}),
 'correctionsBySource':{sid:info['correct'] for sid,info in per_source_counts.items()},
 'formalLaneRowsPreserved':preflight['preservedSpanishRows'],
 'spanishExactReuseRowsPreserved':preflight['preservedSpanishExactReuseRows'],
 'formalCellIdsSha256':sha((ROOT/'formal-cell-ids.jsonl').read_bytes()),
 'priorManualCells':preflight['priorManualCells'],'priorManualSourceKeys':preflight['priorManualSourceKeys'],
 'priorAppliedCorrectionRows':preflight['priorAppliedCorrections'],
 'priorHoldRowsPreservedAndReattested':preflight['priorHoldRows'],
 'priorHoldSourceIds':preflight['priorHoldSourceIds'],
 'priorManualWindows':37,
 'priorW37CandidateRowsReattested':manifest['scope']['w37CandidateRowsReattested'],
 'priorW37CandidateNoOpRows':manifest['scope']['w37CandidateNoOpRows'],
 'callerRowReferencesReattested':row_to_caller_refs,
 'uniqueCallerLinesReattested':preflight['callerLinesRechecked'],
 'catalogFileHashesReattested':catalog_hashes,
 'placeholdersAndProtectedLiterals':f'PASS: {len(rows)} current rows and all {len(candidates)} proposed targets; zero proposal mismatch',
 'candidateNoOpRows':sum(1 for c in candidates if c['candidateTarget']==c['currentTarget']),
 'sourceCurrentTargetCallerPins':'PASS at exact pushed head',
 'semanticConfidence':'High for clear false-friend, wrong data-type, path, and exact configuration-key errors; moderate overall; native-speaker review remains outstanding.',
 'composedSentenceReviewNote':'The Pod help fragment is concatenated after a separately localized Enable label and feature.Pods code literal; review the composed sentence before applying any row-level proposal.',
 'nativeSpeakerReview':'outstanding',
 'headedBrowserReview':'not part of this source/catalog audit; remains outstanding for parent workflow',
 'privateJitFunctionalValidation':'not run for this read-only review',
 'testsBuildsScansCiOrReleasesRun':False,'catalogFilesEdited':False,'workflowFilesEdited':False,
 'repositoryOrPullRequestMutated':False
}
(ROOT/'review-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')

readme=['# slskdN PR #409 W38 primary semantic review','',
 f'This packet reviews the next 25 disjoint source IDs at pinned PR head `{HEAD}` (tree `{TREE}`, `src/web/src` subtree `{SOURCE_TREE}`). The review is read-only and covers the exact current locale catalogs and caller contexts.', '',
 '## Scope and overlap', '',
 f'- {len(rows)} pending cells across 11 locales: '+', '.join(f'{k} {v}' for k,v in sorted(collections.Counter(r['locale'] for r in rows).items()))+'.',
 f'- Previous exact manual windows 1–37: {preflight["priorManualCells"]} cells / {preflight["priorManualSourceKeys"]} source IDs; W38 cell and source-key overlap: 0.',
 f'- Selected sorted source-key positions 1–25 from the {manifest["scope"]["remainingSourceIdsBeforeSelection"]} IDs remaining after W1–W37; ordered IDs are in `manifest.json` and `preflight.json`.',
 f'- Frozen formal lane: 4,800 cells. W38 preserves {preflight["preservedSpanishRows"]} selected Spanish cells in that lane and {preflight["preservedSpanishExactReuseRows"]} additional Spanish exact-reuse cells; no Spanish verdicts are emitted.',
 f'- Previous applied corrections: {preflight["priorAppliedCorrections"]}; W38 applied-correction overlap: 0.',
 f'- Preserved {preflight["priorHoldRows"]} explicit prior hold rows across seven unique held source IDs; all current targets and all caller refs available in the original records were re-attested at W38 head. Hold/source-key overlap: 0.',
 f'- Decisions: {counts["keep"]} keep, {counts["correct"]} correction candidates, 0 uncertain.',
 f'- Current source, target, catalog, caller-file and caller-line pins match the exact pushed head. {preflight["callerLinesRechecked"]} unique caller lines and {row_to_caller_refs} row-to-caller references were checked.',
 f'- All {len(candidates)} candidate targets differ from current targets and preserve source placeholders and reviewer-protected literals; candidate no-op count: 0.',
 f'- Prior W37 candidate re-attestation: {manifest["scope"]["w37CandidateRowsReattested"]} proposals, {manifest["scope"]["w37CandidateNoOpRows"]} current-target no-ops.',
 '- The Pod help fragment is concatenated after a separately localized Enable label and the feature.Pods code literal; sentence-level review remains necessary before applying its row-level proposals.',
 '- No catalogs, workflows, or PR state were changed. No tests, builds, scans, CI, or releases were run.', '',
 '## Correction candidates', '']
source_rows={r['sourceId']:r for r in rows}
for sid,pc in sorted(per_source_counts.items()):
    readme.append(f'- `{sid}` — **{source_rows[sid]["source"]}**: {pc["correct"]} locale correction candidate(s).')
    for item in candidates:
        if item['sourceId']==sid:
            readme.append(f'  - `{item["locale"]}`: `{item["currentTarget"]}` → `{item["candidateTarget"]}` ({item["confidence"]}; {item["reason"]})')
readme += ['', '## Prior holds and review limitations', '',
 'Byte-exact copies of all explicit active prior hold ledgers are in `prior-holds/`; `preserved-prior-holds.jsonl` joins each original row to its source-ledger path/hash, and `hold-revalidation.jsonl` records current-head target and available caller re-attestation. All 50 held targets remain unchanged. W38 adds no new hold; the W34 French uncertain cell was independently resolved as keep-current.',
 'No native-speaker signoff or browser/visual review was performed in this primary packet. Translation confidence is high for direct semantic errors and exact-key fixes, moderate overall; native locale review and headed browser work remain outstanding in the parent workflow.', '',
 '## Files', '',
 '- `review-input.jsonl`: exact frozen pending source/current target rows with caller context.',
 '- `review-decisions.jsonl`: one primary verdict per cell.',
 '- `review-evidence.jsonl` and `correction-candidates.jsonl`: row-level source/current/candidate hashes, reasons, caller refs, and literal checks.',
 '- `source-attestation.jsonl` and `caller-attestation.jsonl`: source and caller pins re-attested at the exact head.',
 '- `preserved-prior-routed.jsonl` / `preserved-spanish-reused.jsonl`: Spanish formal-lane and exact-reuse cells left outside W38 decisions.',
 '- `preserved-prior-holds.jsonl`, `hold-revalidation.jsonl`, and `prior-holds/`: all explicit prior hold rows and their exact source ledgers.',
 '- `window38-review-holds.jsonl`: empty new-hold ledger; all prior holds remain separately preserved.',
 '- `manifest.json`, `preflight.json`, `freeze-summary.json`, and `formal-cell-ids.jsonl`: window derivation and overlap evidence.',
 '- `review-summary.json`: decision counts and remaining native/browser/JIT gaps.',
 '- `freeze_window38.py` and `build_review_packet.py`: scratch-only packet generation scripts.', '',
 'Cross-review is required before any candidate is applied.']
(ROOT/'README.md').write_text('\n'.join(readme)+'\n',encoding='utf-8')

# SHA manifest is regenerated after the README and summary; this is packet integrity accounting, not a repo test.
files=sorted(p for p in ROOT.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
(ROOT/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(ROOT)}\n' for p in files),encoding='utf-8')
print(json.dumps({'summary':summary,'files':[str(p.relative_to(ROOT)) for p in files]+['SHA256SUMS.txt']},ensure_ascii=False,indent=2))
