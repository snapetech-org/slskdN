#!/usr/bin/env python3
"""Build exact-head W37 primary semantic dispositions in task scratch only."""
import collections, hashlib, json, re, subprocess
from pathlib import Path

ROOT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window37-primary-20261102')
REPO = Path('/mnt/disks/scratch/task-worktrees/localization-20261102/slskdn-pr409-w36-review')
HEAD = '2be3fa4dd46a0f0f49adad342f289721e4777035'
TREE = 'f838ae565086dec8639f8a54aa4c7d4572342b5f'
SOURCE_TREE = '594e56c3f439bad476b1bd57e0de1665c62fa1bb'
FORMAL = {json.loads(line)['id'] for line in (ROOT/'formal-cell-ids.jsonl').read_text().splitlines() if line.strip()}

# Proposals are limited to clear meaning, terminology, configuration-key, and data-type errors.
CANDIDATES = {
 ('src_0738bb3259fd619e','zh-Hans'): ('自动替换已禁用。自动重试是单独功能；要停止重试失败的下载，请禁用 transfers.download.auto_retry.enabled。', 'The setting path is a case-sensitive configuration key; preserve its exact lowercase spelling.', 'high'),
 ('src_0738bb3259fd619e','hi'): ('स्वतः प्रतिस्थापन बंद है। स्वचालित पुनः प्रयास एक अलग सुविधा है; विफल डाउनलोड के पुनः प्रयास रोकने के लिए transfers.download.auto_retry.enabled को बंद करें।', 'The current setting path changes the property name from transfers to Transfer; preserve the exact configuration key.', 'high'),
 ('src_0738bb3259fd619e','de'): ('Automatisches Ersetzen ist deaktiviert. Automatische Wiederholungen sind eine separate Funktion. Deaktivieren Sie transfers.download.auto_retry.enabled, um fehlgeschlagene Downloads nicht erneut zu starten.', 'Preserve the exact configuration key and use a separate sentence for the disable instruction.', 'high'),
 ('src_0738bb3259fd619e','fr'): ('Le remplacement automatique est désactivé. La nouvelle tentative automatique est une fonction distincte ; désactivez transfers.download.auto_retry.enabled pour arrêter les nouvelles tentatives des téléchargements échoués.', 'The current setting path is singularized as transfer; preserve the exact configuration key.', 'high'),
 ('src_0738bb3259fd619e','ar'): ('تم تعطيل الاستبدال التلقائي. إعادة المحاولة التلقائية ميزة منفصلة؛ عطّل transfers.download.auto_retry.enabled لإيقاف إعادة محاولة التنزيلات الفاشلة.', 'The current target translates part of the configuration key; preserve the exact lowercase key.', 'high'),
 ('src_0738bb3259fd619e','zh-Hant'): ('自動替換已停用。自動重試是另一項功能；若要停止重試失敗的下載，請停用 transfers.download.auto_retry.enabled。', 'The setting path must keep its exact lowercase spelling.', 'high'),
 ('src_0738bb3259fd619e','vi'): ('Tự động thay thế đã tắt. Tính năng thử lại tự động là riêng biệt; để ngừng thử lại các lượt tải xuống thất bại, hãy tắt transfers.download.auto_retry.enabled.', 'The current setting path is singularized as transfer; preserve the exact configuration key.', 'high'),

 ('src_076f9c8cff1db724','fr'): ('Enregistrez la décision d’acceptation locale pour cette recommandation concernant la version candidate.', '“Libération” reads as liberation; this caller concerns a software release-candidate recommendation.', 'high'),
 ('src_076f9c8cff1db724','id'): ('Catat keputusan penerimaan lokal untuk rekomendasi kandidat rilis ini.', '“Pelepasliaran” refers to releasing something into the wild; this caller concerns a software release candidate.', 'high'),
 ('src_077506f3bbc87b87','id'): ('Laju sampel Chromaprint', 'For an audio setting, “laju sampel” names sample rate; “kecepatan sampel” reads as sample speed.', 'moderate'),
 ('src_07ac461a993457c4','hi'): ('दूरस्थ पथ', 'This label names an FTP remote filesystem path; “दूरस्थ” is the usual technical rendering of remote.', 'moderate'),

 ('src_07c0b991c768e218','hi'): ('एक साथ आने वाली खोजों की संख्या', 'The current construction is an awkward calque; this numeric field controls how many incoming searches can run at once.', 'moderate'),
 ('src_07c0b991c768e218','fr'): ('Nombre de recherches entrantes simultanées', '“Concurrence” suggests competition; the setting controls concurrent incoming searches.', 'high'),
 ('src_07c0b991c768e218','pt-BR'): ('Número de pesquisas recebidas simultaneamente', 'This numeric field controls how many incoming searches can be processed at once.', 'moderate'),
 ('src_07c0b991c768e218','ar'): ('عدد عمليات البحث الواردة المتزامنة', 'Name the number of incoming search requests that may run concurrently.', 'moderate'),
 ('src_07c0b991c768e218','vi'): ('Số lượt tìm kiếm đến đồng thời', 'The current phrase is ungrammatical; this names the count of incoming searches at the same time.', 'moderate'),
 ('src_07c0b991c768e218','id'): ('Jumlah pencarian masuk bersamaan', 'This numeric field controls the number of searches that can arrive concurrently.', 'moderate'),

 ('src_07ce8b8a99bc57e9','de'): ('Themen-URL', 'Use the German compound for the URL of an ntfy topic.', 'moderate'),
 ('src_07ce8b8a99bc57e9','fr'): ('URL du sujet', 'Put URL before the topic noun in this French field label.', 'moderate'),
 ('src_07ce8b8a99bc57e9','pt-BR'): ('URL do tópico', 'Use the natural Portuguese order for a topic URL.', 'moderate'),
 ('src_07ce8b8a99bc57e9','ar'): ('عنوان URL للموضوع', 'This is the URL address for an ntfy topic; retain the protected acronym URL.', 'moderate'),
 ('src_07ce8b8a99bc57e9','vi'): ('URL của chủ đề', 'Use the natural Vietnamese possessive order for the topic URL.', 'moderate'),
 ('src_07ce8b8a99bc57e9','id'): ('URL topik', 'Use the natural Indonesian order for a topic URL.', 'moderate'),

 ('src_07ceeb4bc33842b0','zh-Hans'): ('Discogs 发行版/母版 ID', '“发布/主” reads as publish/main; distinguish the Discogs Release and Master record types.', 'moderate'),
 ('src_07ceeb4bc33842b0','fr'): ('ID de sortie/master Discogs', '“Version/ID principal” loses the Discogs Master entity; preserve the Release/Master distinction.', 'moderate'),
 ('src_07ceeb4bc33842b0','pt-BR'): ('ID de lançamento/master do Discogs', '“Liberação” reads as liberation; this field accepts Discogs release or master identifiers.', 'high'),
 ('src_07ceeb4bc33842b0','zh-Hant'): ('Discogs 發行版／母版 ID', '“發佈/主” reads as publish/main; distinguish the Discogs Release and Master record types.', 'moderate'),
 ('src_07ceeb4bc33842b0','vi'): ('ID bản phát hành/bản master của Discogs', 'The current wording turns release/master into a verb and a generic main ID; name the two Discogs record types.', 'moderate'),

 ('src_07d70633fc2bb901','vi'): ('Video:', '“Băng hình” means videotape; the source is a media-property label for video content.', 'high'),
 ('src_07daadb6ed60272f','fr'): ('Vous avez déjà rejoint le salon. Appuyez sur Entrée pour l’ouvrir.', 'The caller is a room-search hint; name the joined room and give a complete French instruction.', 'moderate'),
 ('src_07daadb6ed60272f','ja'): ('すでに参加しています。Enterキーを押して開きます。', 'Use the standard Japanese label Enterキー; the current text omits キー and inserts an unnatural space.', 'moderate'),
 ('src_07e56bf8696ead49','zh-Hans'): ('预计大小：', 'The caller reports totalSizeBytes; “尺寸” suggests physical dimensions instead of data size.', 'high'),
 ('src_07e56bf8696ead49','zh-Hant'): ('預計大小：', 'The caller reports totalSizeBytes; “尺寸” suggests physical dimensions instead of data size.', 'high'),
 ('src_07f4c78b5e0b3026','ja'): ('評価統計', 'The caller displays rating counts and score distribution; 世論統計 suggests public-opinion polling.', 'high'),
 ('src_07f68caa669e1912','id'): ('Pengaburan Waktu', '“Kebingungan Waktu” means time confusion; this privacy control obscures timing patterns.', 'high'),

 ('src_0831a9db649eaabc','zh-Hans'): ('路径：', 'The caller displays a filesystem/source path; 小路 means a footpath.', 'high'),
 ('src_0831a9db649eaabc','de'): ('Pfad:', 'The caller displays a filesystem/source path; Pfad is the technical file-path term.', 'high'),
 ('src_0831a9db649eaabc','ar'): ('المسار:', 'The caller displays a filesystem/source path; طريق means a road.', 'high'),
 ('src_0831a9db649eaabc','ko'): ('경로:', 'The caller displays a filesystem/source path; 길 means a road or way.', 'high'),
 ('src_0831a9db649eaabc','zh-Hant'): ('路徑：', 'The caller displays a filesystem/source path; 小路 means a footpath.', 'high'),
 ('src_0831a9db649eaabc','vi'): ('Đường dẫn:', 'The caller displays a filesystem/source path; con đường means a road.', 'high'),
 ('src_0845f26528463f04','de'): ('Freiwilliges öffentliches Rendezvous ist deaktiviert.', 'The source explicitly says opt-in; retain that consent-based participation in the status heading.', 'moderate'),
}

SOURCE_REASONS = {
 'src_0738bb3259fd619e':'Toast explaining that auto-replace is disabled, automatic retry is independent, and an exact configuration key controls retries.',
 'src_07418f367b8e4a59':'Helper text asks the user to add another bridge configuration line for the Obfs4 transport; preserve Obfs4.',
 'src_07548c2c6511d4d1':'Accessible action label for expanding a search result; the source is the action paired with Collapse.',
 'src_0758527f1d1223d6':'Security tooltip says to verify a peer’s signed membership record before trusting role or ban status.',
 'src_076af4050c3596e2':'Empty-state prompt to select a request before inspecting its jury evidence.',
 'src_076f9c8cff1db724':'Tooltip records the local acceptance decision for a release-candidate recommendation.',
 'src_077506f3bbc87b87':'Accessibility label for the Chromaprint audio sample-rate setting; preserve Chromaprint.',
 'src_0785d90c99d99c5a':'Tooltip describes accepting a signed leave request and publishing membership removal after verification.',
 'src_07a0deb704c92aca':'Skipped metadata-stage reason when AcoustID or MusicBrainz is not configured; preserve both service names.',
 'src_07ac461a993457c4':'FTP settings and share table label for the remote filesystem path.',
 'src_07b78b7dc23061e8':'Accessible name for the control that refreshes Security status.',
 'src_07bf99530379773a':'Tooltip explains comparing two hashes against a chosen threshold to assess likely match.',
 'src_07c0b119540bb930':'Room-creation validation error when the name field is empty.',
 'src_07c0b991c768e218':'Admin-policy setting for the allowed number of incoming searches at once.',
 'src_07ce8b8a99bc57e9':'Notification integration field for the ntfy topic URL; preserve URL.',
 'src_07ceeb4bc33842b0':'MusicBrainz lookup form field for Discogs Release or Master IDs; preserve Discogs and distinguish the two record types.',
 'src_07d70633fc2bb901':'Media-verification detail label for whether the validated content is video.',
 'src_07daadb6ed60272f':'Room-search hint shown when the user already belongs to the room; Enter opens it.',
 'src_07e56bf8696ead49':'Estimated storage-size label preceding the totalSizeBytes value.',
 'src_07f4c78b5e0b3026':'Heading above opinion records and their rating counts, unique variants, average score, and score range.',
 'src_07f68caa669e1912':'Privacy-setting heading for timing obfuscation, paired with an enabled toggle and jitter-range control.',
 'src_082666d98a3d19e7':'Modal heading displayed after an invite is created.',
 'src_082bad10890a82a7':'Button label for rebuilding the search index.',
 'src_0831a9db649eaabc':'Label immediately before the fullSourceFingerprint.path filesystem value.',
 'src_0845f26528463f04':'Status heading in Soulseek Mesh Rendezvous explaining that opt-in public rendezvous is disabled.',
}
ADDITIONAL_PROTECTED = {'src_0738bb3259fd619e':['transfers.download.auto_retry.enabled']}


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
assert len(rows)==273 and len({r['id'] for r in rows})==273
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
              'currentTargetSha256':r['targetSha256'],'window':37,'confidence':confidence,'reason':reason}
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
assert len([json.loads(x) for x in (ROOT/'preserved-prior-routed.jsonl').read_text().splitlines() if x.strip()])==24
assert len([json.loads(x) for x in (ROOT/'preserved-spanish-reused.jsonl').read_text().splitlines() if x.strip()])==1
assert len([json.loads(x) for x in (ROOT/'preserved-prior-holds.jsonl').read_text().splitlines() if x.strip()])==50
assert preflight['manualCellOverlap']==0 and preflight['manualSourceKeyOverlap']==0
assert preflight['appliedOverlap']==0 and preflight['formalOverlap']==0 and preflight['holdSourceKeyOverlap']==0

review_decision_hash=jsonl_write('review-decisions.jsonl',decisions)
review_evidence_hash=jsonl_write('review-evidence.jsonl',evidence)
review_candidates_hash=jsonl_write('correction-candidates.jsonl',candidates)
per_locale_counts={locale:dict(c) for locale,c in sorted(per_locale.items())}
per_source_counts={sid:dict(c) for sid,c in sorted(per_source.items()) if c['correct']}
row_to_caller_refs=sum(len(r['sourceCallsites']) for r in rows)
summary={
 'result':'PRIMARY_REVIEW_COMPLETE_PENDING_CROSS_REVIEW_NATIVE_SPEAKER_REVIEW_OUTSTANDING',
 'window':37,'repository':'snapetech-org/slskdN','pullRequest':409,
 'branch':'codex/slskdn-oidc-tooltip-localization-20261030',
 'livePrState':'OPEN','livePrDraft':True,'livePrMergeState':'CLEAN',
 'reviewBaseHead':HEAD,'reviewBaseTree':TREE,'sourceSubtreePath':'src/web/src','sourceSubtreeTree':SOURCE_TREE,
 'reviewInputSha256':sha((ROOT/'review-input.jsonl').read_bytes()),
 'reviewDecisionSha256':review_decision_hash,'reviewEvidenceSha256':review_evidence_hash,
 'correctionCandidatesSha256':review_candidates_hash,
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
 'callerRowReferencesReattested':row_to_caller_refs,
 'uniqueCallerLinesReattested':preflight['callerLinesRechecked'],
 'catalogFileHashesReattested':catalog_hashes,
 'placeholdersAndProtectedLiterals':'PASS: 273 current rows and all 42 proposed targets; zero mismatch',
 'sourceCurrentTargetCallerPins':'PASS at exact pushed head',
 'semanticConfidence':'High for clear false-friend, wrong data-type, path, and exact configuration-key errors; moderate overall; native-speaker review remains outstanding.',
 'nativeSpeakerReview':'outstanding',
 'headedBrowserReview':'not part of this source/catalog audit; remains outstanding for parent workflow',
 'privateJitFunctionalValidation':'not run for this read-only review',
 'testsBuildsScansCiOrReleasesRun':False,'catalogFilesEdited':False,'workflowFilesEdited':False,
 'repositoryOrPullRequestMutated':False
}
(ROOT/'review-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')

readme=['# slskdN PR #409 W37 primary semantic review','',
 f'This packet reviews the next 25 disjoint source IDs at pinned PR head `{HEAD}` (tree `{TREE}`, `src/web/src` subtree `{SOURCE_TREE}`). The review is read-only and covers the exact current locale catalogs and caller contexts.', '',
 '## Scope and overlap', '',
 f'- {len(rows)} pending cells across 11 locales: '+', '.join(f'{k} {v}' for k,v in sorted(collections.Counter(r['locale'] for r in rows).items()))+'.',
 f'- Previous exact manual windows 1–36: {preflight["priorManualCells"]} cells / {preflight["priorManualSourceKeys"]} source IDs; W37 cell and source-key overlap: 0.',
 f'- Frozen formal lane: 4,800 cells. W37 preserves {preflight["preservedSpanishRows"]} selected Spanish cells in that lane and one additional Spanish cell marked exact prior reuse; no Spanish verdicts are emitted.',
 f'- Previous applied corrections: {preflight["priorAppliedCorrections"]}; W37 applied-correction overlap: 0.',
 f'- Preserved {preflight["priorHoldRows"]} explicit prior hold rows across seven unique held source IDs; all current targets and all caller refs available in the original records were re-attested at W37 head. Hold/source-key overlap: 0.',
 f'- Decisions: {counts["keep"]} keep, {counts["correct"]} correction candidates, 0 uncertain.',
 f'- Current source, target, catalog, caller-file and caller-line pins match the exact pushed head. {preflight["callerLinesRechecked"]} unique caller lines and {row_to_caller_refs} row-to-caller references were checked.',
 '- The 42 candidate targets preserve source placeholders and protected literals, including exact configuration key `transfers.download.auto_retry.enabled`, `URL`, `Discogs`, `Obfs4`, `AcoustID`, and `MusicBrainz` where applicable.',
 '- No catalogs, workflows, or PR state were changed. No tests, builds, scans, CI, or releases were run.', '',
 '## Correction candidates', '']
source_rows={r['sourceId']:r for r in rows}
for sid,pc in sorted(per_source_counts.items()):
    readme.append(f'- `{sid}` — **{source_rows[sid]["source"]}**: {pc["correct"]} locale correction candidate(s).')
    for item in candidates:
        if item['sourceId']==sid:
            readme.append(f'  - `{item["locale"]}`: `{item["currentTarget"]}` → `{item["candidateTarget"]}` ({item["confidence"]}; {item["reason"]})')
readme += ['', '## Prior holds and review limitations', '',
 'Byte-exact copies of all explicit active prior hold ledgers are in `prior-holds/`; `preserved-prior-holds.jsonl` joins each original row to its source-ledger path/hash, and `hold-revalidation.jsonl` records current-head target and available caller re-attestation. The held targets remain unchanged. The older W34 French uncertain cell was independently resolved as keep-current, and W35 recorded no hold candidates.',
 'No native-speaker signoff or browser/visual review was performed in this primary packet. Translation confidence is high for direct semantic errors and exact-key fixes, moderate overall; native locale review and headed browser work remain outstanding in the parent workflow.', '',
 '## Files', '',
 '- `review-input.jsonl`: exact frozen pending source/current target rows with caller context.',
 '- `review-decisions.jsonl`: one primary verdict per cell.',
 '- `review-evidence.jsonl` and `correction-candidates.jsonl`: row-level source/current/candidate hashes, reasons, caller refs, and literal checks.',
 '- `source-attestation.jsonl` and `caller-attestation.jsonl`: source and caller pins re-attested at the exact head.',
 '- `preserved-prior-routed.jsonl` / `preserved-spanish-reused.jsonl`: Spanish formal-lane and exact-reuse cells left outside W37 decisions.',
 '- `preserved-prior-holds.jsonl`, `hold-revalidation.jsonl`, and `prior-holds/`: all explicit prior hold rows and their exact source ledgers.',
 '- `manifest.json`, `preflight.json`, `freeze-summary.json`, and `formal-cell-ids.jsonl`: window derivation and overlap evidence.',
 '- `review-summary.json`: decision counts and remaining native/browser/JIT gaps.',
 '- `freeze_window37.py` and `build_review_packet.py`: scratch-only packet generation scripts.', '',
 'Cross-review is required before any candidate is applied.']
(ROOT/'README.md').write_text('\n'.join(readme)+'\n',encoding='utf-8')

# SHA manifest is regenerated after the README and summary; this is packet integrity accounting, not a repo test.
files=sorted(p for p in ROOT.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
(ROOT/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(ROOT)}\n' for p in files),encoding='utf-8')
print(json.dumps({'summary':summary,'files':[str(p.relative_to(ROOT)) for p in files]+['SHA256SUMS.txt']},ensure_ascii=False,indent=2))
