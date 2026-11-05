#!/usr/bin/env python3
"""Verify the committed slskdN W953–W977 product changes against all 300 pinned cells."""
import argparse
import collections
import copy
import hashlib
import json
import subprocess
from pathlib import Path

INPUT_HEAD = 'fc8e42a06363ceee762ae084bbe716953d4a5d94'
INPUT_TREE = 'e04aa06b8cfb0ee41cae90aef601a0552b5e85bd'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def text_sha(text):
    return sha(text.encode('utf-8'))

def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()

def git_bytes(repo, revision, path):
    return subprocess.check_output(['git', '-C', str(repo), 'show', f'{revision}:{path}'])

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def fail(message):
    raise SystemExit('FAIL: ' + message)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--product-head', required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--root-ledger', type=Path, required=True)
    parser.add_argument('--candidate-free', type=Path, required=True)
    parser.add_argument('--cross-review', type=Path, required=True)
    parser.add_argument('--readback', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    plan = read_json(args.plan)
    root_ledger = read_jsonl(args.root_ledger)
    candidate = read_jsonl(args.candidate_free)
    cross = read_jsonl(args.cross_review)
    if git(repo, 'rev-parse', INPUT_HEAD) != INPUT_HEAD or git(repo, 'rev-parse', f'{INPUT_HEAD}^{{tree}}') != INPUT_TREE:
        fail('pinned input commit/tree not present')
    product = args.product_head
    if git(repo, 'rev-parse', f'{product}^') != INPUT_HEAD:
        fail('product commit parent is not exact pinned input head')
    final_head = git(repo, 'rev-parse', 'HEAD')
    if git(repo, 'merge-base', '--is-ancestor', product, final_head) != '':
        fail('product commit is not an ancestor of current HEAD')
    if git(repo, 'status', '--porcelain=v1'):
        fail('worktree is not clean at readback')
    product_tree = git(repo, 'rev-parse', f'{product}^{{tree}}')
    if plan['sourcePin']['head'] != INPUT_HEAD or plan['sourcePin']['tree'] != INPUT_TREE:
        fail('plan source pin mismatch')
    if len(root_ledger) != len(candidate) != 300:
        fail('unexpected root/candidate cell count')
    if len(root_ledger) != 300 or len(candidate) != 300 or len(cross) != 300:
        fail('full 300-cell matrix incomplete')
    cm = {(r['continuationRank'], r['locale']): r for r in candidate}
    xm = {(r['continuationRank'], r['locale']): r for r in cross}
    rm = {(r['continuationRank'], r['locale']): r for r in root_ledger}
    changes = {(r['continuationRank'], r['locale']): r for r in plan['changes']}
    if len(cm) != 300 or len(xm) != 300 or len(rm) != 300 or set(cm) != set(xm) or set(cm) != set(rm):
        fail('cell matrix keys differ')
    if len(changes) != 114 or len(plan['catalogs']) != 12:
        fail('plan change/catalog count mismatch')

    catalog_meta = {r['path']: r for r in plan['catalogs']}
    expected_paths = set(catalog_meta)
    product_paths = set(git(repo, 'diff-tree', '--no-commit-id', '--name-only', '-r', product).splitlines())
    if product_paths != expected_paths:
        fail('product commit changed unexpected paths')
    if any(path.startswith('.github/workflows/') for path in product_paths):
        fail('workflow path changed')

    base_catalogs, expected_catalogs, live_catalogs = {}, {}, {}
    for path, meta in catalog_meta.items():
        base_raw = git_bytes(repo, INPUT_HEAD, path)
        if sha(base_raw) != meta['preimageSha256']:
            fail('base catalog hash mismatch ' + path)
        base = json.loads(base_raw)
        if len(base) != meta['entryCount'] or sha(('\n'.join(base.keys()) + '\n').encode()) != meta['orderedKeySha256']:
            fail('base catalog structure mismatch ' + path)
        raw = (repo / path).read_bytes()
        now = json.loads(raw)
        if raw != (json.dumps(now, ensure_ascii=False, indent=2) + '\n').encode('utf-8'):
            fail('live catalog serialization mismatch ' + path)
        if len(now) != meta['entryCount'] or list(now) != list(base):
            fail('catalog key count/order changed ' + path)
        base_catalogs[path] = base
        expected_catalogs[path] = copy.deepcopy(base)
        live_catalogs[path] = now

    counts = collections.Counter()
    readback_rows = []
    changed_count = 0
    for key in sorted(cm):
        c, x, r = cm[key], xm[key], rm[key]
        if c['sourceId'] != r.get('sourceId', c['sourceId']) or c['sourceSha256'] != x['sourceTextSha256']:
            fail('source binding mismatch ' + str(key))
        for field in ('currentTargetSha256', 'callerContextSha256', 'callerCount'):
            if c[field] != x[field] or c[field] != r[field]:
                fail(field + ' binding mismatch ' + str(key))
        if text_sha(c['currentTarget']) != c['currentTargetSha256']:
            fail('candidate current-target hash mismatch ' + str(key))
        path, source_key = c['catalogPath'], c['source']
        if path not in live_catalogs or source_key not in live_catalogs[path]:
            fail('catalog key missing ' + str(key))
        observed = live_catalogs[path][source_key]
        change = changes.get(key)
        root_disposition = r['rootDisposition']
        if change:
            for field in ('sourceId', 'catalogPath', 'source', 'sourceSha256', 'callerContextSha256', 'currentTarget', 'currentTargetSha256'):
                if change[field] != c[field]:
                    fail(field + ' plan binding mismatch ' + str(key))
            if r.get('selectedTarget') != change['selectedTarget'] or r.get('selectedTargetSha256') != change['selectedTargetSha256']:
                fail('root/plan selected target mismatch ' + str(key))
            if text_sha(change['selectedTarget']) != change['selectedTargetSha256']:
                fail('selected target hash mismatch ' + str(key))
            if x['recommendation'] == 'hold-hash-only' or x['recommendation'] == 'accept-current':
                fail('changed cell has non-change cross disposition ' + str(key))
            if change['selectedTarget'] != observed or text_sha(observed) != change['selectedTargetSha256']:
                fail('changed target readback mismatch ' + str(key))
            if root_disposition == 'root-manual-adjustment':
                if change['crossRecommendedTargetSha256'] == change['selectedTargetSha256']:
                    fail('root manual adjustment does not differ from cross target')
                counts['root-manual-adjustment'] += 1
            elif root_disposition == 'accept-correction':
                counts['accept-correction'] += 1
            elif root_disposition == 'accept-refinement':
                counts['accept-refinement'] += 1
            elif root_disposition == 'accept-cross-adjustment':
                counts['accept-cross-adjustment'] += 1
            else:
                fail('unexpected changed root disposition ' + str(key))
            expected_catalogs[path][source_key] = change['selectedTarget']
            changed_count += observed != c['currentTarget']
            readback_rows.append({
                'continuationRank': key[0], 'remainingQueueRank': c['remainingQueueRank'], 'sourceId': c['sourceId'],
                'locale': key[1], 'sourceSha256': c['sourceSha256'], 'callerContextSha256': c['callerContextSha256'],
                'beforeTargetSha256': c['currentTargetSha256'], 'expectedAfterSha256': change['selectedTargetSha256'],
                'observedAfterSha256': text_sha(observed), 'changed': observed != c['currentTarget'],
                'rootDisposition': root_disposition, 'beforeTarget': c['currentTarget'], 'afterTarget': observed,
            })
        elif x['recommendation'] == 'hold-hash-only':
            if root_disposition != 'hold-non-user-facing-hash-only':
                fail('hold disposition mismatch ' + str(key))
            for forbidden in ('source', 'currentTarget', 'selectedTarget'):
                if forbidden in r:
                    fail('root hold contains text field ' + forbidden)
            if observed != c['currentTarget']:
                fail('held cell changed ' + str(key))
            counts['hold-hash-only'] += 1
            readback_rows.append({
                'continuationRank': key[0], 'remainingQueueRank': c['remainingQueueRank'], 'sourceIdSha256': r['sourceIdSha256'],
                'locale': key[1], 'sourceSha256': r['sourceTextSha256'], 'callerContextSha256': c['callerContextSha256'],
                'beforeTargetSha256': c['currentTargetSha256'], 'expectedAfterSha256': c['currentTargetSha256'],
                'observedAfterSha256': text_sha(observed), 'changed': False, 'rootDisposition': root_disposition,
                'holdReasonClass': x['blindHoldReasonClass'],
            })
        else:
            if x['recommendation'] != 'accept-current' or root_disposition != 'accept-current':
                fail('unplanned cell has unexpected disposition ' + str(key))
            if observed != c['currentTarget'] or x['recommendedTargetSha256'] != c['currentTargetSha256']:
                fail('accept-current cell changed ' + str(key))
            counts['accept-current'] += 1
            readback_rows.append({
                'continuationRank': key[0], 'remainingQueueRank': c['remainingQueueRank'], 'sourceId': c['sourceId'],
                'locale': key[1], 'sourceSha256': c['sourceSha256'], 'callerContextSha256': c['callerContextSha256'],
                'beforeTargetSha256': c['currentTargetSha256'], 'expectedAfterSha256': c['currentTargetSha256'],
                'observedAfterSha256': text_sha(observed), 'changed': False, 'rootDisposition': root_disposition,
            })

    if changed_count != 114:
        fail('expected exactly 114 changed cells')
    for path, live in live_catalogs.items():
        if live != expected_catalogs[path]:
            fail('non-target catalog values changed ' + path)
    if counts != collections.Counter({'accept-current': 174, 'accept-correction': 110, 'accept-refinement': 3, 'root-manual-adjustment': 1, 'hold-hash-only': 12}):
        fail('root disposition counts mismatch ' + str(counts))

    args.readback.parent.mkdir(parents=True, exist_ok=True)
    args.readback.write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in readback_rows), encoding='utf-8')
    report = {
        'result': 'PASS', 'inputHead': INPUT_HEAD, 'inputTree': INPUT_TREE, 'productHead': product,
        'productTree': product_tree, 'finalHead': final_head, 'candidateCells': 300, 'observedChangedCells': changed_count,
        'dispositionCounts': dict(counts), 'changedCatalogCount': len(product_paths), 'changedCatalogPaths': sorted(product_paths),
        'allCatalogKeysPreserved': True, 'allNonTargetCatalogValuesPreserved': True, 'all12CatalogsReadBack': True,
        'hashOnlyHoldsTextFree': True, 'workflowChanges': 0, 'readbackSha256': sha(args.readback.read_bytes()),
        'postimageHashes': {path: sha((repo / path).read_bytes()) for path in sorted(live_catalogs)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'postimageHashes'}, ensure_ascii=False, sort_keys=True))

if __name__ == '__main__':
    main()
