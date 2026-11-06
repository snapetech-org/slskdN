#!/usr/bin/env python3
"""Verify W77's 300-cell apply readback and all 12 ordered locale catalogs."""
import argparse
import collections
import hashlib
import json
import subprocess
from pathlib import Path

HEAD = '582ae64e5c3af275490f11f4350b33da7373a3c3'
TREE = 'b8692bb066cede93b6668806d0b97816135ce647'


def sha(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def readj(path):
    return json.loads(path.read_text(encoding='utf-8'))


def readjl(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, required=True, help='apply worktree or checkout containing the W77 product commit')
    ap.add_argument('--candidate-free', type=Path, required=True)
    ap.add_argument('--cross-packet', type=Path, required=True)
    ap.add_argument('--application-dir', type=Path, required=True)
    args = ap.parse_args()
    repo, candidate, cross, app = (p.resolve() for p in (args.repo, args.candidate_free, args.cross_packet, args.application_dir))

    source_rows = readjl(candidate / 'source-current-cells.jsonl')
    structure = readjl(candidate / 'catalog-structure.jsonl')
    cross_ledger = readjl(cross / 'cross-ledger.jsonl')
    holds = readjl(cross / 'holds-hash-only.jsonl')
    plan = readj(cross / 'apply-plan.json')
    readback = readjl(app / 'application-readback.jsonl')
    prepost = readj(app / 'catalog-preimage-and-postimage.json')
    summary = readj(app / 'application-summary.json')
    cell_map = {(x['sourceId'], x['locale']): x for x in source_rows}
    ledger_map = {(x['sourceId'], x['locale']): x for x in cross_ledger}
    read_map = {(x['sourceId'], x['locale']): x for x in readback}
    op_map = {(x['sourceId'], x['locale']): x for x in plan['operations']}
    hold_keys = {(x['sourceId'], x['locale']) for x in holds}
    assert len(cell_map) == len(ledger_map) == len(read_map) == 300
    assert len(op_map) == 52 and len(hold_keys) == 12
    assert set(cell_map) == set(ledger_map) == set(read_map)
    assert set(op_map) == {(x['sourceId'], x['locale']) for x in cross_ledger if x['crossDisposition'] == 'select-update'}
    assert not (hold_keys & set(op_map))
    assert plan['sourceHead'] == HEAD and plan['sourceTree'] == TREE
    prepost_map = {x['catalogPath']: x for x in prepost['catalogs']}
    structure_map = {x['catalogPath']: x for x in structure}
    assert len(structure_map) == 12 and len(prepost_map) == 12
    assert set(prepost_map) == set(structure_map)
    repo_head = git(repo, 'rev-parse', 'HEAD').decode().strip()
    if repo_head == HEAD:
        assert git(repo, 'rev-parse', 'HEAD^{tree}').decode().strip() == TREE
    else:
        product_commit = summary.get('productCommit')
        assert product_commit and git(repo, 'rev-parse', f'{product_commit}^').decode().strip() == HEAD
        assert git(repo, 'rev-parse', f'{product_commit}^{{tree}}').decode().strip() == summary['productTree']

    paths = {r['catalogPath'] for r in source_rows}
    assert paths == set(structure_map)
    for path, spec in structure_map.items():
        old_bytes = git(repo, 'show', f'{HEAD}:{path}')
        current_bytes = (repo / path).read_bytes()
        old_doc = json.loads(old_bytes)
        new_doc = json.loads(current_bytes)
        assert sha(old_bytes) == spec['sha256']
        assert len(old_doc) == len(new_doc) == spec['entryCount'] == 6176
        assert list(old_doc) == list(new_doc)
        order_hash = sha(('\n'.join(new_doc.keys()) + '\n'))
        assert order_hash == spec['orderedKeySha256']
        assert json.dumps(old_doc, ensure_ascii=False, indent=2) + '\n' == old_bytes.decode('utf-8')
        assert json.dumps(new_doc, ensure_ascii=False, indent=2) + '\n' == current_bytes.decode('utf-8')
        pp = prepost_map[path]
        assert pp['preimageSha256'] == sha(old_bytes)
        assert pp['postimageSha256'] == sha(current_bytes)
        assert pp['preimageKeyOrderSha256'] == pp['postimageKeyOrderSha256'] == order_hash
        ops_for_path = [x for x in plan['operations'] if x['catalogPath'] == path]
        assert set(pp['changedKeys']) == {x['catalogKey'] for x in ops_for_path}
        changed = {key for key in old_doc if old_doc[key] != new_doc[key]}
        assert changed == {x['catalogKey'] for x in ops_for_path}
        for key in old_doc:
            if key not in changed:
                assert new_doc[key] == old_doc[key]

    counts = collections.Counter()
    for key, cell in cell_map.items():
        read = read_map[key]
        cross_row = ledger_map[key]
        actual = json.loads((repo / cell['catalogPath']).read_text(encoding='utf-8'))[cell['catalogKey']]
        assert read['sourceId'] == cell['sourceId'] and read['locale'] == cell['locale']
        assert read['sourceSha256'] == cell['sourceSha256']
        assert read['currentTargetSha256'] == cell['currentTargetSha256']
        assert read['postReadbackSha256'] == sha(actual)
        assert cross_row['sourceSha256'] == cell['sourceSha256']
        if key in hold_keys:
            counts['hold-hash-only'] += 1
            assert cross_row['crossDisposition'] == 'hold-hash-only'
            assert read['decision'] == 'hold-hash-only' and actual == cell['currentTarget']
            assert read['postReadbackSha256'] == cell['currentTargetSha256']
            for field in ('source', 'currentTarget', 'selectedTarget', 'catalogKey'):
                assert field not in read and field not in holds[[ (h['sourceId'],h['locale']) for h in holds].index(key)]
            assert read['sourceTextIncluded'] is False and read['currentTargetIncluded'] is False and read['selectedTargetIncluded'] is False
        elif key in op_map:
            counts['select-update'] += 1
            op = op_map[key]
            assert actual == op['selectedTarget'] == read['selectedTarget']
            assert sha(actual) == op['selectedTargetSha256'] == read['selectedTargetSha256']
            assert sha(cell['currentTarget']) == op['expectedCurrentTargetSha256']
        else:
            counts['accept-current'] += 1
            assert cross_row['crossDisposition'] == 'accept-current'
            assert read['decision'] == 'accept-current'
            assert actual == cell['currentTarget'] == read['selectedTarget']
            assert sha(actual) == cell['currentTargetSha256']
    assert counts == {'select-update': 52, 'accept-current': 236, 'hold-hash-only': 12}
    if repo_head == HEAD:
        changed_paths = set(git(repo, 'diff', 'HEAD', '--name-only').decode().splitlines())
    else:
        product_commit = summary.get('productCommit')
        assert product_commit and git(repo, 'rev-parse', f'{product_commit}^').decode().strip() == HEAD
        changed_paths = set(git(repo, 'diff-tree', '--no-commit-id', '--name-only', '-r', product_commit).decode().splitlines())
    assert changed_paths == {x['catalogPath'] for x in plan['operations']}

    assert summary['result'] == 'PASS' and summary['cellsReadBack'] == 300
    assert summary['selectedUpdates'] == 52 and summary['unchangedCells'] == 236 and summary['hashOnlyHolds'] == 12
    print(json.dumps({'result':'PASS','sourceHead':HEAD,'sourceTree':TREE,'cellsReadBack':300,
                      'selectedUpdates':52,'unchanged':236,'hashOnlyHolds':12,
                      'localeCatalogs':12,'orderedKeysPerCatalog':6176,'productFilesChanged':len(changed_paths)},indent=2))


if __name__ == '__main__':
    main()
