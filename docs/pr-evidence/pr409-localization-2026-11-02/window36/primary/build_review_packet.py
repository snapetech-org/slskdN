import hashlib
import json
import pathlib
import re
import subprocess
from collections import Counter, defaultdict

SCRATCH = pathlib.Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window36-20261102')
WORKTREE = pathlib.Path('/mnt/disks/scratch/task-worktrees/localization-20261102/slskdn-pr409-w36-review')
INPUT = SCRATCH / 'review-input.jsonl'
PRECHECK = json.loads((SCRATCH / 'preflight.json').read_text())
FORMAL_IDS = {json.loads(line)['id'] for line in (SCRATCH / 'formal-cell-ids.jsonl').read_text().splitlines() if line.strip()}
HEAD = '370c172e91935d7753c398eaf1b1fbc2e82f65ba'
TREE = '61bd0c6af797b0e810fdf9fad82c7d3a95c88b9c'
SOURCE_TREE = '594e56c3f439bad476b1bd57e0de1665c62fa1bb'

CANDIDATES = {
    ('src_05da9cbb4bd46c0f', 'zh-Hans'): ('筛选 {format} 文件', '“过滤到” is a calque; this source is a filter action on a file format.', 'high'),
    ('src_05da9cbb4bd46c0f', 'ja'): ('{format} ファイルに絞り込む', 'The current “filter to” wording is unnatural in Japanese; this expresses filtering down to files of the selected format.', 'high'),
    ('src_05da9cbb4bd46c0f', 'pt-BR'): ('Filtrar arquivos {format}', '“Filtrar para arquivos” is an awkward calque; the control filters the list to files of this format.', 'high'),
    ('src_05da9cbb4bd46c0f', 'ar'): ('صفِّ الملفات بصيغة {format}', 'The current construction calques “filter to”; this is an imperative to filter files by format.', 'high'),
    ('src_05da9cbb4bd46c0f', 'zh-Hant'): ('篩選 {format} 檔案', '“過濾到” is a calque; this is the natural filter action for files of the selected format.', 'high'),
    ('src_05da9cbb4bd46c0f', 'vi'): ('Lọc các tệp {format}', '“Lọc thành” calques “filter to” and reads as changing files into something; this says to filter the listed files by format.', 'high'),
    ('src_05da9cbb4bd46c0f', 'id'): ('Saring file berformat {format}', 'The current phrase uses “Filter” in English and “ke” makes the format relation awkward; this is a natural Indonesian filter label.', 'high'),

    ('src_05e48200ad1eb8ac', 'pt-BR'): ('Os logs em tempo real estão desconectados.', '“Registros ativos” means active records and loses the live-log meaning.', 'high'),

    ('src_060b076be748ec44', 'ar'): ('مستلمة /', 'The current verb means “he received”; this fragment labels bytes received before the slash in a transfer statistic.', 'high'),

    ('src_0610a61ef22aea6a', 'hi'): ('कोई विफल कार्य दिखाई नहीं दे रहा है।', 'The current word means jobs/employment; this health check reports failed background tasks.', 'high'),
    ('src_0610a61ef22aea6a', 'ja'): ('失敗したジョブは見当たりません。', 'The current wording says failed jobs are not displayed; the diagnostic means none are visible.', 'high'),
    ('src_0610a61ef22aea6a', 'fr'): ('Aucune tâche en échec n’est visible.', 'The current wording is unidiomatic and uses “travail” for a background job; this names the failed tasks shown by the health check.', 'high'),
    ('src_0610a61ef22aea6a', 'ko'): ('실패한 작업이 보이지 않습니다.', 'The current wording can mean failed jobs are not being displayed; this says none are visible, as the diagnostic intends.', 'high'),
    ('src_0610a61ef22aea6a', 'zh-Hant'): ('看不到失敗的工作', 'This is a natural diagnostic statement that no failed jobs are visible.', 'moderate'),
    ('src_0610a61ef22aea6a', 'vi'): ('Không thấy công việc nào thất bại.', 'The current wording says failed jobs are not displayed; this says no failed task is visible.', 'high'),
    ('src_0610a61ef22aea6a', 'id'): ('Tidak terlihat ada pekerjaan yang gagal.', 'The current phrase is awkward; this expresses that the health check sees no failed jobs.', 'high'),

    ('src_061c01268f7c9950', 'ar'): ('مسار ملف Soulfind التنفيذي', 'The current word is a physical road; this is a filesystem path to the Soulfind executable binary.', 'high'),
    ('src_061c01268f7c9950', 'vi'): ('Đường dẫn đến tệp nhị phân Soulfind', 'The current wording makes “binary” sound like a mathematical number; this names the Soulfind binary file.', 'high'),
    ('src_061c01268f7c9950', 'id'): ('Jalur ke berkas biner Soulfind', 'The current phrase says “road to”; this is a filesystem path to the Soulfind binary.', 'high'),

    ('src_06650b05b4cab744', 'ja'): ('ルーム配信', 'The current term means an indoor/public-address broadcast; the fallback identifies the online listening room’s broadcast.', 'high'),
    ('src_06650b05b4cab744', 'fr'): ('Diffusion du salon', '“Salle” suggests a physical hall; this is the broadcast associated with a chat/listening salon.', 'moderate'),
    ('src_06650b05b4cab744', 'ko'): ('룸 방송', 'The current string has a duplicated “room” syllable and reads as a typo.', 'high'),

    ('src_069c12967ebd313f', 'fr'): ("Récupérez les listes publiques d'intérêts et d'éléments détestés de l'utilisateur indiqué.", '“Éléments rejetés” means rejected items, while this Soulseek profile list is the user’s hated items.', 'high'),
    ('src_069c12967ebd313f', 'pt-BR'): ('Busque as listas públicas de interesses e itens que o usuário odeia.', '“Itens rejeitados” means rejected items, while this Soulseek profile list contains items the user hates.', 'high'),

    ('src_06ab0f6d089fc024', 'zh-Hans'): ('掩护流量', 'The current phrase means road/transport traffic; this privacy setting generates network cover traffic.', 'high'),
    ('src_06ab0f6d089fc024', 'hi'): ('कवर ट्रैफ़िक', 'The current phrase is an imperative to cover traffic; this is the noun technical term used as a section heading.', 'moderate'),
    ('src_06ab0f6d089fc024', 'de'): ('Tarn-Datenverkehr', 'The current phrase is an imperative to cover traffic; this privacy setting generates obfuscating network traffic.', 'high'),
    ('src_06ab0f6d089fc024', 'fr'): ('Trafic de couverture', 'The current phrase is an imperative; this is the network privacy term for cover traffic.', 'high'),
    ('src_06ab0f6d089fc024', 'pt-BR'): ('Tráfego de cobertura', 'The current phrase is an imperative; this is the network privacy term for cover traffic.', 'high'),
    ('src_06ab0f6d089fc024', 'ar'): ('حركة مرور تمويهية', 'The current wording suggests covering road traffic; this names obfuscating network traffic.', 'high'),
    ('src_06ab0f6d089fc024', 'zh-Hant'): ('掩護流量', 'The current phrase means road/transport traffic; this privacy setting generates network cover traffic.', 'high'),
    ('src_06ab0f6d089fc024', 'vi'): ('Lưu lượng ngụy trang', 'The current phrase says to cover road traffic; this names camouflage/cover traffic in the privacy settings.', 'high'),
    ('src_06ab0f6d089fc024', 'id'): ('Lalu lintas kamuflase', 'The current phrase is an imperative about road traffic; this names camouflage network traffic.', 'high'),

    ('src_06af0870f8f66ed4', 'ar'): ('الأنواع الصادرة', 'The current adjective construction is ungrammatical; this is the plural label for outbound evidence types.', 'high'),
    ('src_06af0870f8f66ed4', 'vi'): ('Các loại bằng chứng gửi đi', 'The current phrase means only “types that go”; caller context shows this is the count of outbound evidence types.', 'high'),

    ('src_06dfd9bfbec866df', 'vi'): ('ID Pod, ID nội dung và mã băm biến thể là bắt buộc', 'The current translation changes the product field “Pod ID” to “group ID”; keep the product entity name to match the form field.', 'high'),

    ('src_06e70139fcf5e5c7', 'vi'): ('Số lần thử', 'This count is the number of transfer retry attempts; “nỗ lực” means effort and is less precise as a count label.', 'moderate'),

    ('src_072c79f620d6edd4', 'ar'): ('إرسال المسار يدويًا', 'The current wording reads as sending a physical road; this section manually dispatches a network route.', 'high'),
    ('src_072c79f620d6edd4', 'vi'): ('Điều phối tuyến thủ công', 'The current word “lộ trình” suggests a travel itinerary; this section dispatches network routes.', 'high'),
}

SOURCE_REASONS = {
    'src_05da9cbb4bd46c0f': 'Filter action for narrowing a file list by its format; preserve the {format} placeholder.',
    'src_05e48200ad1eb8ac': 'Status message for the live-log connection.',
    'src_060b076be748ec44': 'Fragment after received byte count and before the sent byte count.',
    'src_0610a61ef22aea6a': 'Diagnostic evidence says the collected state has no visible failed background jobs.',
    'src_061c01268f7c9950': 'Label for the filesystem path to the Soulfind executable.',
    'src_062ae028d80de1f3': 'Playlist error toast; preserve both {playlistName} and {message}.',
    'src_0632d9eef1b2e559': 'Plural heading introducing graph paths.',
    'src_064b7a4855ee86a2': 'Fallback label when a user reputation score is unavailable.',
    'src_064d50041fc85428': 'Success heading after publishing a descriptor.',
    'src_06650b05b4cab744': 'Compact fallback text for the listening-party room broadcast.',
    'src_0669dc2d5d3bd436': 'Diagnostic evidence value for a connected Soulseek session.',
    'src_068740f29d75f76c': 'Tooltip that closes settings after confirming ListenBrainz token changes were saved.',
    'src_069920024b690acd': 'Heading for ContentID examples.',
    'src_069c12967ebd313f': 'Tooltip fetches a Soulseek user’s public interest and hated-item lists.',
    'src_06ab0f6d089fc024': 'Privacy setting label for generated network cover traffic; backend has a cover traffic generator and configurable interval.',
    'src_06af0870f8f66ed4': 'Statistic label for the count of enabled outbound mesh evidence types.',
    'src_06b42a9189e10d33': 'System state badge indicating that a reconnect is needed.',
    'src_06c47c063e6f846f': 'Join/open action label for a Soulseek room; preserve {roomName}.',
    'src_06d19c730abd2fe4': 'Error toast shown when loading the room list fails.',
    'src_06dfd9bfbec866df': 'Error toast naming the three required Pod fields.',
    'src_06e70139fcf5e5c7': 'Count label for retry attempts in the request detail modal.',
    'src_06fddd066f1be644': 'Tooltip for selecting a custom wave in the active native preset before export/removal.',
    'src_07141bc6c8b8c649': 'Accessible label for stepping backward in the native preset library.',
    'src_072c79f620d6edd4': 'Section heading above the fields used to manually dispatch a route.',
    'src_0731fec9926056e0': 'Tooltip warns that publishing each listed ContentID to the DHT creates a network write; preserve DHT.',
}

rows = [json.loads(line) for line in INPUT.read_text().splitlines() if line.strip()]
assert len(rows) == 275
assert len({r['sourceId'] for r in rows}) == 25
assert all(r['locale'] != 'es' for r in rows)
assert set(SOURCE_REASONS) == {r['sourceId'] for r in rows}

# Verify exact worktree pins before recomputing evidence.
def git(*args):
    return subprocess.check_output(['git', *args], cwd=WORKTREE, text=True).strip()
assert git('rev-parse', 'HEAD') == HEAD
assert git('rev-parse', 'HEAD^{tree}') == TREE
assert git('rev-parse', 'HEAD:src/web/src') == SOURCE_TREE
assert git('status', '--porcelain') == ''

# Recompute hashes for all locale files and compare the frozen manifest.
for locale, expected in PRECHECK['catalogHashes'].items():
    path = WORKTREE / f'src/web/public/locales/{locale}.json'
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected, (locale, actual, expected)

# Row-level source/catalog hash re-attestation and caller line/file re-attestation.
source_attest = {}
caller_attest = {}
for r in rows:
    source_bytes = r['source'].encode('utf-8')
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    assert source_hash == r['sourceSha256']
    assert r['sourceId'] == 'src_' + source_hash[:16]
    catalog_path = WORKTREE / r['catalogPath']
    catalog = json.loads(catalog_path.read_text())
    actual_target = catalog[r['catalogKey']]
    target_hash = hashlib.sha256(actual_target.encode('utf-8')).hexdigest()
    assert actual_target == r['target']
    assert target_hash == r['targetSha256']
    source_attest[(r['sourceId'], r['sourceSha256'])] = {
        'sourceId': r['sourceId'], 'source': r['source'], 'sourceSha256': source_hash,
        'sourceFingerprint': r['sourceFingerprint'], 'sourceKind': r['sourceKind'],
    }
    for c in r['sourceCallsites']:
        key = (c['path'], c['line'])
        p = WORKTREE / c['path']
        file_hash = hashlib.sha256(p.read_bytes()).hexdigest()
        lines = p.read_text().splitlines()
        line_text = lines[c['line'] - 1].strip()
        line_hash = hashlib.sha256(line_text.encode('utf-8')).hexdigest()
        assert file_hash == c['fileSha256'], (key, file_hash, c['fileSha256'])
        assert line_text == c['lineText'], (key, line_text, c['lineText'])
        assert line_hash == c['lineTextSha256'], (key, line_hash, c['lineTextSha256'])
        caller_attest[key] = {
            'path': c['path'], 'line': c['line'], 'lineText': line_text,
            'lineTextSha256': line_hash, 'fileSha256': file_hash,
            'sourceIds': [],
        }
        if r['sourceId'] not in caller_attest[key]['sourceIds']:
            caller_attest[key]['sourceIds'].append(r['sourceId'])

# Ensure the frozen caller corpus has the expected row-to-caller multiplicity.
assert sum(len(r['sourceCallsites']) for r in rows) == 429
assert len(caller_attest) == 39

# Assemble decisions and enriched cell evidence.
decisions = []
evidence = []
counts = Counter()
per_locale = defaultdict(Counter)
per_source = defaultdict(Counter)
for r in rows:
    key = (r['sourceId'], r['locale'])
    proposal = CANDIDATES.get(key)
    cell_id = r['id']
    row = {'id': cell_id, 'verdict': 'correct' if proposal else 'keep'}
    if proposal:
        candidate, reason, confidence = proposal
        assert len(re.findall(r'\{[^{}]+\}', candidate)) == len(r['placeholders'])
        assert sorted(re.findall(r'\{[^{}]+\}', candidate)) == sorted(r['placeholders'])
        for literal in r['protectedLiterals']:
            assert literal in candidate, (cell_id, literal, candidate)
        row.update({'target': candidate, 'confidence': confidence, 'reason': reason})
        candidate_hash = hashlib.sha256(candidate.encode('utf-8')).hexdigest()
        counts['correct'] += 1
        per_locale[r['locale']]['correct'] += 1
        per_source[r['sourceId']]['correct'] += 1
    else:
        candidate = None
        reason = SOURCE_REASONS[r['sourceId']]
        confidence = 'moderate'
        candidate_hash = None
        counts['keep'] += 1
        per_locale[r['locale']]['keep'] += 1
        per_source[r['sourceId']]['keep'] += 1
    row['sourceSha256'] = r['sourceSha256']
    row['currentTargetSha256'] = r['targetSha256']
    row['window'] = 36
    decisions.append(row)
    evidence.append({
        'id': cell_id, 'sourceId': r['sourceId'], 'locale': r['locale'],
        'source': r['source'], 'sourceSha256': r['sourceSha256'],
        'currentTarget': r['target'], 'currentTargetSha256': r['targetSha256'],
        'candidateTarget': candidate, 'candidateTargetSha256': candidate_hash,
        'verdict': row['verdict'], 'confidence': confidence, 'reason': reason,
        'callerRefs': [{'path': c['path'], 'line': c['line'], 'fileSha256': c['fileSha256'], 'lineTextSha256': c['lineTextSha256']} for c in r['sourceCallsites']],
        'placeholders': r['placeholders'], 'protectedLiterals': r['protectedLiterals'],
        'catalogPath': r['catalogPath'], 'catalogKey': r['catalogKey'],
        'reviewInputRowSha256': r['rowSha256'],
    })

assert counts['correct'] + counts['keep'] == 275
assert len(CANDIDATES) == counts['correct']

# Preserve, but do not re-route, Spanish W36 cells already assigned to the formal lane.
spanish = []
source_rows = {r['sourceId']: r for r in rows}
for source_id, source_row in source_rows.items():
    cell_id = f"es:{source_id}"
    assert cell_id in FORMAL_IDS, cell_id
    catalog_path = WORKTREE / 'src/web/public/locales/es.json'
    es_catalog = json.loads(catalog_path.read_text())
    value = es_catalog[source_row['catalogKey']]
    sha = hashlib.sha256(value.encode('utf-8')).hexdigest()
    spanish.append({
        'id': cell_id, 'sourceId': source_id, 'locale': 'es',
        'source': source_row['source'], 'sourceSha256': source_row['sourceSha256'],
        'currentTarget': value, 'currentTargetSha256': sha,
        'preservationDisposition': 'already routed through the formal review lane; no W36 decision emitted',
        'formalCellIdPresent': True,
        'catalogPath': 'src/web/public/locales/es.json',
        'catalogKey': source_row['catalogKey'],
        'callerRefs': [{'path': c['path'], 'line': c['line'], 'fileSha256': c['fileSha256'], 'lineTextSha256': c['lineTextSha256']} for c in source_row['sourceCallsites']],
    })

# Deterministic order: the frozen pending-cell order is retained.
def write_jsonl(path, values):
    path.write_text(''.join(json.dumps(v, ensure_ascii=False, sort_keys=True) + '\n' for v in values))
write_jsonl(SCRATCH / 'review-decisions.jsonl', decisions)
write_jsonl(SCRATCH / 'review-evidence.jsonl', evidence)
write_jsonl(SCRATCH / 'source-attestation.jsonl', sorted(source_attest.values(), key=lambda x:x['sourceId']))
write_jsonl(SCRATCH / 'caller-attestation.jsonl', [caller_attest[k] for k in sorted(caller_attest)])
write_jsonl(SCRATCH / 'preserved-prior-routed.jsonl', sorted(spanish, key=lambda x:x['sourceId']))

# Summary includes the exact pins, counts, methodology, and remaining quality lane.
summary = {
    'result': 'PRIMARY_REVIEW_COMPLETE_NATIVE_SPEAKER_REVIEW_OUTSTANDING',
    'window': 36,
    'repository': 'snapetech-org/slskdN',
    'pullRequest': 409,
    'branch': 'codex/slskdn-oidc-tooltip-localization-20261030',
    'prStateAtReview': 'OPEN', 'prDraftAtReview': True, 'prMergeStateAtReview': 'CLEAN',
    'reviewBaseHead': HEAD, 'reviewBaseTree': TREE,
    'sourceSubtreePath': 'src/web/src', 'sourceSubtreeTree': SOURCE_TREE,
    'reviewInputSha256': hashlib.sha256(INPUT.read_bytes()).hexdigest(),
    'reviewDecisionSha256': hashlib.sha256((SCRATCH / 'review-decisions.jsonl').read_bytes()).hexdigest(),
    'reviewEvidenceSha256': hashlib.sha256((SCRATCH / 'review-evidence.jsonl').read_bytes()).hexdigest(),
    'sourceKeys': 25, 'pendingCells': len(rows), 'pendingCellCounts': dict(sorted(Counter(r['locale'] for r in rows).items())),
    'verdictCounts': dict(counts),
    'correctionCellsByLocale': {locale: c['correct'] for locale, c in sorted(per_locale.items())},
    'keepCellsByLocale': {locale: c['keep'] for locale, c in sorted(per_locale.items())},
    'correctedSourceIds': sorted({sid for sid, _ in CANDIDATES}),
    'correctionsBySource': {sid: v['correct'] for sid,v in sorted(per_source.items()) if v['correct']},
    'priorRoutedCellsPreserved': 25,
    'priorRoutedLocale': 'es',
    'formalCellIdSetSha256': PRECHECK['formalCellIdsSha256'],
    'callerRowReferencesReattested': 429,
    'uniqueCallerLinesReattested': len(caller_attest),
    'catalogFileHashesReattested': PRECHECK['catalogHashes'],
    'placeholdersAndProtectedLiterals': 'PASS',
    'sourceCurrentTargetHashes': 'PASS',
    'worktreeClean': git('status', '--porcelain') == '',
    'semanticConfidence': 'High for explicit corrections; moderate overall; native-speaker review remains outstanding.',
    'nativeSpeakerReview': 'outstanding',
    'headedBrowserReview': 'not part of this source/catalog audit; remains outstanding for the parent workflow',
    'testsBuildScansCiOrReleasesRun': False,
    'catalogFilesEdited': False,
    'workflowFilesEdited': False,
    'rowContractNote': 'The existing window workflow used 300 all-locale cells when all 12 locales were pending. W36 correctly contains 275 pending cells because the 25 Spanish rows for these same source IDs are already assigned to the formal lane; they are preserved separately and no new W36 Spanish verdicts are emitted.',
}
(SCRATCH / 'review-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + '\n')

# Human-readable account of the scope and material corrections.
readme = f'''# slskdN PR #409 W36 primary semantic review

This packet is a read-only primary semantic review of the next 25 ordered pending source IDs at PR #409 head `{HEAD}` (tree `{TREE}`, `src/web/src` subtree `{SOURCE_TREE}`). The selected source IDs and their caller contexts were frozen from the exact PR head in `review-input.jsonl`; the live PR remained OPEN/DRAFT/CLEAN at the same head when rechecked.

## Scope and routing

- 25 source IDs, 275 pending catalog cells across 11 locales (25 each): {', '.join(sorted(Counter(r['locale'] for r in rows)))}.
- The same source IDs have 25 Spanish cells already routed through the formal review lane. They are recorded in `preserved-prior-routed.jsonl`, with current Spanish target hashes and formal cell IDs. No new Spanish verdicts are emitted.
- The standard all-locale window size is 300 cells; the 275-cell W36 pending set is the expected result of preserving those 25 formal-lane cells.
- Decisions: {counts['keep']} keep, {counts['correct']} correction candidates, 0 uncertain.
- Placeholders and protected literals were checked for every proposed correction. Source IDs and source hashes, current catalog values and hashes, catalog file hashes, and caller source file/line hashes were recomputed against the detached exact-head worktree.
- Caller attestation covers 429 row-to-caller references over 39 unique caller lines.
- No catalogs, workflows, or PR state were changed. No tests, builds, scans, CI, or releases were run.

## Correction candidates

'''
for sid, counts_for_source in sorted(per_source.items()):
    if not counts_for_source['correct']:
        continue
    source = source_rows[sid]['source']
    readme += f"- `{sid}` — **{source}**: {counts_for_source['correct']} locale correction candidate(s).\n"
    for r in rows:
        if r['sourceId'] == sid and (sid, r['locale']) in CANDIDATES:
            candidate, why, confidence = CANDIDATES[(sid, r['locale'])]
            readme += f"  - `{r['locale']}`: `{r['target']}` → `{candidate}` ({confidence}; {why})\n"
readme += '''
## Files

- `review-input.jsonl`: frozen source/current catalog rows with source contexts, caller refs, and exact input hashes.
- `review-decisions.jsonl`: compact verdicts matching the existing semantic-review decision shape, with source/current target hashes and window number.
- `review-evidence.jsonl`: per-cell decision join containing source/current target hashes, correction text/hash where proposed, caller refs, placeholders/protected literals, and frozen row hash.
- `source-attestation.jsonl`: source-ID/source-text hash re-attestation.
- `caller-attestation.jsonl`: unique source caller line and file hash re-attestation.
- `preserved-prior-routed.jsonl`: Spanish cells preserved because they are in the formal-lane ID set.
- `preflight.json`, `freeze-summary.json`, `manifest.json`, `formal-cell-ids.jsonl`, `freeze_window36.py`: exact-head freeze and lane-exclusion evidence.
- `review-summary.json`: pins and counts.
- `build_review_packet.py`: packet generation and exact-head re-attestation code.

Semantic and locale-quality confidence is moderate overall. This packet is not native-speaker review and does not settle final locale style. The parent workflow can cross-review the proposed targets before deciding whether to apply them.
'''
(SCRATCH / 'README.md').write_text(readme)

# Integrity file, excluding itself.
files = sorted(p for p in SCRATCH.iterdir() if p.is_file() and p.name != 'SHA256SUMS.txt')
(SCRATCH / 'SHA256SUMS.txt').write_text(''.join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files))
print(json.dumps({
    'summary': summary,
    'scratchBytes': sum(p.stat().st_size for p in SCRATCH.iterdir() if p.is_file()),
    'files': [p.name for p in files] + ['SHA256SUMS.txt'],
}, ensure_ascii=False, indent=2))
