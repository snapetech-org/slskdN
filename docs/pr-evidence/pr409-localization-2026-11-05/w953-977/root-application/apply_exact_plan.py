#!/usr/bin/env python3
"""Apply only the 114 root-adjudicated, exact-hash slskdN W953–W977 targets."""
import argparse
import collections
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

HEAD = 'fc8e42a06363ceee762ae084bbe716953d4a5d94'
TREE = 'e04aa06b8cfb0ee41cae90aef601a0552b5e85bd'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def text_sha(value):
    return sha(value.encode('utf-8'))

def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()

def fail(message):
    raise SystemExit('FAIL: ' + message)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    plan = json.loads(args.plan.read_text(encoding='utf-8'))
    if git(repo, 'rev-parse', 'HEAD') != HEAD or git(repo, 'rev-parse', 'HEAD^{tree}') != TREE:
        fail('exact source HEAD/tree mismatch')
    if git(repo, 'status', '--porcelain=v1'):
        fail('worktree is not clean before apply')
    if plan['sourcePin']['head'] != HEAD or plan['sourcePin']['tree'] != TREE:
        fail('plan source pin mismatch')
    if plan['candidateCells'] != 300 or len(plan['changes']) != 114 or plan['heldHashOnlyCells'] != 12:
        fail('plan cell dimensions mismatch')

    catalogs, original, key_orders = {}, {}, {}
    for meta in plan['catalogs']:
        path = meta['path']
        raw = (repo / path).read_bytes()
        if sha(raw) != meta['preimageSha256']:
            fail('catalog preimage hash mismatch ' + path)
        data = json.loads(raw)
        if len(data) != meta['entryCount']:
            fail('catalog entry count mismatch ' + path)
        if raw != (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8'):
            fail('catalog serialization mismatch ' + path)
        ordered_hash = sha(('\n'.join(data.keys()) + '\n').encode('utf-8'))
        if ordered_hash != meta['orderedKeySha256']:
            fail('catalog ordered-key hash mismatch ' + path)
        catalogs[path] = data
        original[path] = raw
        key_orders[path] = list(data)

    seen = set()
    by_path = collections.defaultdict(list)
    for change in plan['changes']:
        cell = (change['continuationRank'], change['locale'])
        if cell in seen:
            fail('duplicate selected cell ' + str(cell))
        seen.add(cell)
        path = change['catalogPath']
        if path not in catalogs:
            fail('un-pinned catalog ' + path)
        if text_sha(change['selectedTarget']) != change['selectedTargetSha256']:
            fail('selected-target hash mismatch ' + str(cell))
        if text_sha(change['currentTarget']) != change['currentTargetSha256']:
            fail('current-target hash mismatch ' + str(cell))
        data = catalogs[path]
        source_key = change['source']
        if source_key not in data:
            fail('source key missing from catalog ' + str(cell))
        current = data[source_key]
        if current != change['currentTarget'] or text_sha(current) != change['currentTargetSha256']:
            fail('live current target mismatch ' + str(cell))
        by_path[path].append(change)
    if len(seen) != 114 or len(by_path) != 12:
        fail('application row/catalog count mismatch')

    for path, rows in by_path.items():
        data = catalogs[path]
        for row in rows:
            data[row['source']] = row['selectedTarget']
        if list(data) != key_orders[path]:
            fail('catalog key order changed in memory ' + path)
        postimage = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        temp = None
        try:
            with tempfile.NamedTemporaryFile(prefix='.w953-', suffix='.tmp', dir=(repo / path).parent, delete=False) as handle:
                handle.write(postimage)
                handle.flush()
                os.fsync(handle.fileno())
                temp = handle.name
            os.replace(temp, repo / path)
        finally:
            if temp and os.path.exists(temp):
                os.unlink(temp)
        if (repo / path).read_bytes() != postimage:
            fail('postimage write mismatch ' + path)

    changed = set(git(repo, 'diff', '--name-only').splitlines())
    status_lines = subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain=v1'], text=True).splitlines()
    status_paths = {line[3:] for line in status_lines if len(line) >= 4}
    expected = set(by_path)
    if changed != expected or status_paths != expected:
        fail('working paths are not exactly selected locale catalogs')
    if any(path.startswith('.github/workflows/') for path in changed):
        fail('workflow path changed')

    result = {
        'result': 'PASS',
        'sourcePin': plan['sourcePin'],
        'candidateCells': 300,
        'selectedChanges': 114,
        'heldHashOnlyCells': 12,
        'rootManualOverrides': plan['rootManualOverrides'],
        'changedCatalogCount': len(expected),
        'changedCatalogPaths': sorted(expected),
        'workflowChanges': 0,
        'hooks': {'preCommit': 'not run; hooks disabled for commit', 'prePush': 'not run; hooks disabled for push'},
        'catalogs': [],
    }
    for meta in plan['catalogs']:
        path = meta['path']
        raw = (repo / path).read_bytes()
        data = json.loads(raw)
        result['catalogs'].append({
            'locale': meta['locale'],
            'path': path,
            'preimageSha256': sha(original[path]),
            'postimageSha256': sha(raw),
            'entryCount': len(data),
            'orderedKeySha256': sha(('\n'.join(data.keys()) + '\n').encode('utf-8')),
            'changedCellCount': len(by_path.get(path, [])),
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'result': 'PASS', 'selectedChanges': 114, 'changedCatalogCount': len(expected), 'paths': sorted(expected)}, ensure_ascii=False, sort_keys=True))

if __name__ == '__main__':
    main()
