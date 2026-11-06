#!/usr/bin/env python3
"""Create candidate-free exact-head input for slskdN PR #409 ranks 303–327."""
from pathlib import Path
import collections
import hashlib
import json
import re
import subprocess

REPO = Path('/mnt/disks/scratch/task-worktrees/localization-20261103/slskdn-pr409-w56-apply-20261103')
OUT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w57-ranks303-327-candidate-free-20261103')
INPUT = OUT / 'input'
W56_INPUT = Path('/mnt/disks/scratch/task-worktrees/localization-20261103/slskdn-pr409-w56-apply-20261103/docs/pr-evidence/pr409-localization-2026-11-03/window56/review/candidate-free-input')
INVENTORY = REPO / 'docs/pr-evidence/pr409-localization-2026-11-03/window49/primary/source-inventory.jsonl'
EXPECTED_HEAD = '6b09b3c7bf7de69c316ba3e2503dc450004c9b59'
EXPECTED_TREE = 'a5f9b792875d341a49208d0785bfff28aa9092d7'
EXPECTED_BRANCH = 'codex/slskdn-oidc-tooltip-localization-20261030'
EXPECTED_INVENTORY_SHA256 = '17cb8a747939d4973733016b95f29284e191d5444910051e42fb153cf4f94225'
PR = 409
OWNER_REPO = 'snapetech-org/slskdN'
LOCALES = ['ar', 'de', 'es', 'fr', 'hi', 'id', 'ja', 'ko', 'pt-BR', 'vi', 'zh-Hans', 'zh-Hant']
CATALOGS = {loc: f'src/web/public/locales/{loc}.json' for loc in LOCALES}
RANKS = tuple(range(303, 328))
PH = re.compile(r'\{[^{}]+\}')
MARKUP = re.compile(r'</?[A-Za-z][^>]*>')
NUMBER = re.compile(r'(?<![A-Za-z])\d+(?:[.,]\d+)?%?(?![A-Za-z])')

def run(*args, cwd=REPO, binary=False):
    return subprocess.check_output(list(args), cwd=cwd, text=not binary)

def sha(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()

def git_blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def write_jsonl(path, rows):
    path.write_text(''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n' for row in rows), encoding='utf-8')

def verify_sums(path):
    root = path.parent
    results = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        expected, rel = line.split(None, 1)
        rel = rel.strip().lstrip('*')
        actual = sha((root / rel).read_bytes())
        results.append({'path': rel, 'expected': expected, 'actual': actual, 'matches': expected == actual})
    assert results and all(row['matches'] for row in results), results
    return results

def write_sums(root, destination, excluded=()):
    rows = []
    for file in sorted(path for path in root.rglob('*') if path.is_file() and path != destination and path.name not in excluded):
        rows.append(f'{sha(file.read_bytes())}  {file.relative_to(root).as_posix()}')
    destination.write_text('\n'.join(rows) + '\n', encoding='utf-8')

def live_pin():
    head = run('git', 'rev-parse', 'HEAD').strip()
    tree = run('git', 'rev-parse', 'HEAD^{tree}').strip()
    status = run('git', 'status', '--porcelain=v1').strip()
    assert (head, tree) == (EXPECTED_HEAD, EXPECTED_TREE), (head, tree)
    assert not status, status
    pr = json.loads(run('gh', 'pr', 'view', str(PR), '--repo', OWNER_REPO, '--json', 'body,headRefOid,headRefName,isDraft,state,url'))
    assert pr['state'] == 'OPEN' and pr['isDraft'] is True
    assert pr['headRefOid'] == EXPECTED_HEAD and pr['headRefName'] == EXPECTED_BRANCH
    assert 'slskdN localization W56' in pr['body'], 'live PR body lacks the W56 checkpoint'
    remote = run('git', 'ls-remote', 'origin', f'refs/heads/{EXPECTED_BRANCH}').strip().split()
    assert len(remote) == 2 and remote[0] == EXPECTED_HEAD, remote
    return {
        'repository': OWNER_REPO,
        'pullRequest': PR,
        'url': pr['url'],
        'state': pr['state'],
        'isDraft': pr['isDraft'],
        'branch': EXPECTED_BRANCH,
        'head': EXPECTED_HEAD,
        'tree': EXPECTED_TREE,
        'remoteBranchHead': remote[0],
        'bodySha256': sha(pr['body']),
        'localWorktreeClean': True,
    }

def js_escape(value, quote):
    return value.replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t').replace(quote, '\\' + quote)

def caller_refs(source):
    dq = '"' + re.escape(js_escape(source, '"')) + '"'
    sq = "'" + re.escape(js_escape(source, "'")) + "'"
    pattern = re.compile(r'(?<![A-Za-z0-9_$])(?:' + dq + '|' + sq + r')')
    refs = []
    for path in sorted((REPO / 'src/web/src').rglob('*')):
        if path.suffix not in {'.js', '.jsx', '.ts', '.tsx'}:
            continue
        if '.test.' in path.name or '__tests__' in path.parts:
            continue
        try:
            data = path.read_bytes()
            text = data.decode('utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        lines = text.splitlines()
        for n, line in enumerate(lines, 1):
            if not pattern.search(line):
                continue
            rel = path.relative_to(REPO).as_posix()
            pinned = run('git', 'show', f'{EXPECTED_HEAD}:{rel}', binary=True)
            assert pinned == data, (rel, 'working file differs from pinned head')
            context = [{'line': i + 1, 'text': lines[i]} for i in range(max(0, n - 3), min(len(lines), n + 3))]
            blob = run('git', 'rev-parse', f'{EXPECTED_HEAD}:{rel}').strip()
            refs.append({
                'path': rel,
                'line': n,
                'lineText': line,
                'lineSha256': sha(line),
                'context': context,
                'contextSha256': sha(canonical(context)),
                'fileBytes': len(data),
                'fileSha256': sha(data),
                'gitBlob': blob,
                'gitBlobSha1Check': git_blob(data),
            })
    return refs

def main():
    assert not INPUT.exists(), f'candidate-free output already exists: {INPUT}'
    assert not (OUT / 'TASK-SHA256SUMS.txt').exists()
    pin = live_pin()

    w56_checks = verify_sums(W56_INPUT / 'PACKET-SHA256SUMS.txt')
    w56 = json.loads((W56_INPUT / 'selection-and-boundary.json').read_text(encoding='utf-8'))
    assert w56['livePin']['head'] == '32afa31caca42b17ac89c9ee91e54ed94cad0411'
    assert w56['lastSelected']['continuationRank'] == 302
    assert w56['nextBoundary']['continuationRank'] == 303
    assert w56['candidateFree'] is True

    inventory_bytes = INVENTORY.read_bytes()
    assert sha(inventory_bytes) == EXPECTED_INVENTORY_SHA256
    assert run('git', 'show', f'{EXPECTED_HEAD}:docs/pr-evidence/pr409-localization-2026-11-03/window49/primary/source-inventory.jsonl', binary=True) == inventory_bytes
    inventory = read_jsonl(INVENTORY)
    by_rank = {row['continuationRank']: row for row in inventory if isinstance(row.get('continuationRank'), int)}
    assert all(rank in by_rank for rank in (302, 303, 327, 328))
    selected = [by_rank[rank] for rank in RANKS]
    assert len(selected) == 25
    assert all(row.get('excluded') is False and row.get('inW49') is False for row in selected)
    assert w56['nextBoundary']['sourceId'] == by_rank[303]['sourceId']
    assert w56['nextBoundary']['sourceSha256'] == by_rank[303]['sourceSha256']
    assert w56['lastSelected']['sourceId'] == by_rank[302]['sourceId']

    locales = {}
    catalog_rows = []
    ordered_keys = None
    for locale, rel in CATALOGS.items():
        data = (REPO / rel).read_bytes()
        document = json.loads(data)
        keys = list(document)
        if ordered_keys is None:
            ordered_keys = keys
        assert keys == ordered_keys
        assert all(isinstance(value, str) and value for value in document.values())
        assert run('git', 'rev-parse', f'{EXPECTED_HEAD}:{rel}').strip() == git_blob(data)
        locales[locale] = document
        catalog_rows.append({
            'locale': locale,
            'catalogPath': rel,
            'bytes': len(data),
            'sha256': sha(data),
            'gitBlob': git_blob(data),
            'entryCount': len(document),
            'nonemptyValueCount': sum(bool(value) for value in document.values()),
            'orderedKeySha256': sha('\n'.join(keys) + '\n'),
        })
    assert len(ordered_keys) == 6176
    ordered_hash = sha('\n'.join(ordered_keys) + '\n')
    assert ordered_hash == w56['orderedCatalogKeySha256']
    source_by_id = {'src_' + sha(source)[:16]: source for source in ordered_keys}
    assert len(source_by_id) == len(ordered_keys)
    for row in selected:
        assert source_by_id.get(row['sourceId']) == row['source']
        assert sha(row['source']) == row['sourceSha256']

    caller_rows = []
    caller_map = {}
    for row in selected:
        refs = caller_refs(row['source'])
        caller_map[row['sourceId']] = refs
        caller_rows.append({
            'continuationRank': row['continuationRank'],
            'historicalSourceOrdinal': None,
            'sourceId': row['sourceId'],
            'source': row['source'],
            'sourceSha256': sha(row['source']),
            'productionCallerCount': len(refs),
            'boundedScan': 'exact quoted-literal search in pinned src/web/src JavaScript/TypeScript production files; tests excluded',
            'callers': refs,
        })

    source_cells = []
    for row in selected:
        source = row['source']
        source_id = row['sourceId']
        refs = caller_map[source_id]
        caller_context_sha = sha(canonical(refs))
        source_placeholders = collections.Counter(PH.findall(source))
        source_markup = collections.Counter(MARKUP.findall(source))
        for locale in LOCALES:
            target = locales[locale][source]
            catalog = next(entry for entry in catalog_rows if entry['locale'] == locale)
            target_placeholders = collections.Counter(PH.findall(target))
            target_markup = collections.Counter(MARKUP.findall(target))
            source_cells.append({
                'continuationRank': row['continuationRank'],
                'historicalSourceOrdinal': None,
                'sourceId': source_id,
                'source': source,
                'sourceSha256': sha(source),
                'locale': locale,
                'catalogPath': CATALOGS[locale],
                'catalogFileSha256': catalog['sha256'],
                'catalogGitBlob': catalog['gitBlob'],
                'currentTarget': target,
                'currentTargetSha256': sha(target),
                'callerContextSha256': caller_context_sha,
                'callerRefs': [
                    {'path': ref['path'], 'line': ref['line'], 'lineSha256': ref['lineSha256'], 'fileSha256': ref['fileSha256'], 'gitBlob': ref['gitBlob']}
                    for ref in refs
                ],
                'placeholderEvidence': {
                    'sourceTokens': dict(source_placeholders),
                    'currentTokens': dict(target_placeholders),
                    'matches': source_placeholders == target_placeholders,
                },
                'markupEvidence': {
                    'sourceTags': dict(source_markup),
                    'currentTags': dict(target_markup),
                    'matches': source_markup == target_markup,
                },
                'sourceNumericTokens': NUMBER.findall(source),
                'currentNumericTokens': NUMBER.findall(target),
                'containsCandidate': False,
                'verdict': None,
            })
    assert len(source_cells) == 300 and len(caller_rows) == 25
    assert not any(row['containsCandidate'] or row['verdict'] is not None for row in source_cells)

    boundary = []
    for rank, role in [(302, 'previous-boundary-W56')] + [(n, 'selected-W57') for n in range(303, 328)] + [(328, 'next-boundary-W58')]:
        row = by_rank[rank]
        boundary.append({
            'role': role,
            'continuationRank': rank,
            'sourceId': row['sourceId'],
            'source': row['source'],
            'sourceSha256': row['sourceSha256'],
            'historicalSourceOrdinal': None,
        })

    selection = {
        'artifact': 'slskdN PR #409 candidate-free exact-head review input W57 ranks 303-327',
        'repository': OWNER_REPO,
        'pullRequest': PR,
        'pullRequestUrl': pin['url'],
        'livePin': pin,
        'window': 'W57 continuation of the pinned W49 stable-ID inventory: ranks 303-327; historical source ordinals unavailable and not claimed',
        'rankBasis': 'W56 candidate-free packet pins ranks 301-302 and identifies rank 303 as next. Selected IDs and source hashes are re-attested against the W49 pinned source inventory at the current exact head. W49 ranks 101-125 and W50-W56 ranks 151-302 are prior coverage; the reserved W49 gap 126-150 remains excluded and unreviewed.',
        'localeOrder': LOCALES,
        'localeCount': len(LOCALES),
        'sourceCount': len(selected),
        'cellCount': len(source_cells),
        'catalogSourceCount': len(ordered_keys),
        'orderedCatalogKeySha256': ordered_hash,
        'previousBoundary': boundary[0],
        'firstSelected': boundary[1],
        'lastSelected': boundary[2],
        'nextBoundary': boundary[3],
        'w56Input': {
            'inputDirectory': str(W56_INPUT),
            'checksumListSha256': sha((W56_INPUT / 'PACKET-SHA256SUMS.txt').read_bytes()),
            'verifiedFiles': w56_checks,
            'previousWindowLastSelected': w56['lastSelected'],
            'nextBoundary': w56['nextBoundary'],
        },
        'sourceInventory': {
            'pathAtHead': 'docs/pr-evidence/pr409-localization-2026-11-03/window49/primary/source-inventory.jsonl',
            'sha256': EXPECTED_INVENTORY_SHA256,
            'selectedRanksExcluded': [row.get('excluded') for row in selected],
            'selectedRanksInW49': [row.get('inW49') for row in selected],
        },
        'candidateFree': True,
        'containsTranslationsBeyondCurrentValues': False,
        'callerScan': 'Exact quoted source-literal search across pinned src/web/src JavaScript/TypeScript production files; tests excluded; bounded six-line context spans retained for hits.',
    }

    INPUT.mkdir()
    write_json(INPUT / 'head-tree-attestation.json', pin)
    write_json(INPUT / 'selection-and-boundary.json', selection)
    write_jsonl(INPUT / 'selection-boundary.jsonl', boundary)
    write_jsonl(INPUT / 'source-inventory-selection.jsonl', selected)
    write_jsonl(INPUT / 'catalog-structure.jsonl', catalog_rows)
    write_jsonl(INPUT / 'caller-contexts.jsonl', caller_rows)
    write_jsonl(INPUT / 'source-current-cells.jsonl', source_cells)
    readme = (
        f"# slskdN PR #409 candidate-free input — W57 ranks 303–327\n\n"
        f"The live PR was open and draft at head `{EXPECTED_HEAD}`, tree `{EXPECTED_TREE}`, branch `{EXPECTED_BRANCH}`. The remote branch and clean exact-head worktree matched.\n\n"
        "W56 ends at stable-ID rank 302. Its sealed candidate-free boundary packet identifies rank 303 as the next ID. The pinned W49 inventory and current 6,176-key catalogs confirm 25 selected source IDs at ranks 303–327, covering 300 cells across the 12 direct locales. Historical source ordinals are unavailable and are not claimed.\n\n"
        "The packet contains current catalog targets, exact source/catalog/caller pins, bounded production caller context where found, and placeholder/markup/numeric-token evidence. It contains no proposed translations, review decisions, verdicts, or adjudication.\n"
    )
    (INPUT / 'README.md').write_text(readme, encoding='utf-8')

    input_manifest = {
        'artifact': 'slskdN PR #409 W57 ranks 303-327 candidate-free exact-head input',
        'candidateFree': True,
        'repository': OWNER_REPO,
        'pullRequest': PR,
        'head': EXPECTED_HEAD,
        'tree': EXPECTED_TREE,
        'sourceCount': 25,
        'cellCount': 300,
        'locales': LOCALES,
        'files': [
            {'path': file.relative_to(INPUT).as_posix(), 'bytes': len(file.read_bytes()), 'sha256': sha(file.read_bytes())}
            for file in sorted(path for path in INPUT.rglob('*') if path.is_file() and path.name not in ('manifest.json', 'PACKET-SHA256SUMS.txt'))
        ],
    }
    write_json(INPUT / 'manifest.json', input_manifest)
    write_sums(INPUT, INPUT / 'PACKET-SHA256SUMS.txt', excluded=('PACKET-SHA256SUMS.txt',))
    checks = verify_sums(INPUT / 'PACKET-SHA256SUMS.txt')
    assert live_pin() == pin

    # Task-level checksums preserve the packet and its generator together.
    write_sums(OUT, OUT / 'TASK-SHA256SUMS.txt', excluded=('TASK-SHA256SUMS.txt',))
    task_checks = verify_sums(OUT / 'TASK-SHA256SUMS.txt')
    summary = {
        'artifact': 'slskdN PR #409 candidate-free exact-head packet W57 ranks 303-327',
        'head': EXPECTED_HEAD,
        'tree': EXPECTED_TREE,
        'sourceIds': [{'rank': row['continuationRank'], 'id': row['sourceId'], 'source': row['source']} for row in selected],
        'cells': len(source_cells),
        'locales': len(LOCALES),
        'productionCallerCounts': {row['sourceId']: row['productionCallerCount'] for row in caller_rows},
        'catalogCount': len(catalog_rows),
        'catalogKeysPerLocale': len(ordered_keys),
        'w56InputChecksumFilesVerified': len(w56_checks),
        'packetChecksumFilesVerified': len(checks),
        'taskChecksumFilesVerified': len(task_checks),
        'placeholderOrMarkupMismatches': sum(not row['placeholderEvidence']['matches'] or not row['markupEvidence']['matches'] for row in source_cells),
        'candidateFree': True,
        'repositoryOrPRChanged': False,
        'testsBuildsScansCIWorkflowsBrowserMergeReleaseOrTagPerformed': False,
    }
    write_json(OUT / 'summary.json', summary)
    # Refresh task-level checksums to include final summary.
    write_sums(OUT, OUT / 'TASK-SHA256SUMS.txt', excluded=('TASK-SHA256SUMS.txt',))
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
