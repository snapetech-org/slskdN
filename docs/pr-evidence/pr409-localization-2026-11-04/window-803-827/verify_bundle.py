#!/usr/bin/env python3
"""End-to-end verifier for the committed W77 review and application bundle."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = '582ae64e5c3af275490f11f4350b33da7373a3c3'
BASE_TREE = 'b8692bb066cede93b6668806d0b97816135ce647'
PR_BASE = 'f25d263a2a7cdb2c8f76c40c346cb10f749a9356'
BRANCH = 'codex/slskdn-oidc-tooltip-localization-20261030'


def run(args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def readj(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify_sums(folder, filename, allow_nested=False):
    sums = folder / filename
    assert sums.is_file(), f'missing checksum list {sums}'
    subprocess.run(['sha256sum', '-c', filename], cwd=folder, check=True, stdout=subprocess.DEVNULL)
    listed = {}
    for line in sums.read_text(encoding='utf-8').splitlines():
        if line.strip():
            digest, name = line.split('  ', 1)
            assert name not in listed and len(digest) == 64
            listed[name] = digest
    if not allow_nested:
        actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p != sums}
        assert set(listed) == actual, f'checksum inventory {folder}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, required=True, help='checkout containing product and evidence commits')
    ap.add_argument('--source-checkout', type=Path, required=True, help='clean checkout at the pinned review source head')
    ap.add_argument('--stage', choices=('pre-push','final'), required=True)
    args = ap.parse_args()
    repo, source = args.repo.resolve(), args.source_checkout.resolve()

    verify_sums(ROOT, 'SHA256SUMS.txt')
    verify_sums(ROOT / 'application', 'SHA256SUMS.txt')
    verify_sums(ROOT / 'delivery', 'SHA256SUMS.txt')
    verify_sums(ROOT / 'candidate-free/input', 'PACKET-SHA256SUMS.txt')
    verify_sums(ROOT / 'primary-review/output', 'SHA256SUMS.txt')
    verify_sums(ROOT / 'fresh-blind', 'BLIND-REVIEW-OUTPUT-SHA256SUMS.txt', allow_nested=True)
    verify_sums(ROOT / 'fresh-blind/candidate-free/input', 'PACKET-SHA256SUMS.txt')
    verify_sums(ROOT / 'cross-review', 'SHA256SUMS.txt')

    cross_result = json.loads(subprocess.check_output([
        'python3', str(ROOT / 'verify_cross_packet_portable.py'), '--source-checkout', str(source)
    ], text=True))
    assert cross_result['result'] == 'PASS'
    app_result = json.loads(subprocess.check_output([
        'python3', str(ROOT / 'application/verify_application.py'),
        '--repo', str(repo), '--candidate-free', str(ROOT / 'candidate-free/input'),
        '--cross-packet', str(ROOT / 'cross-review'), '--application-dir', str(ROOT / 'application'),
    ], text=True))
    assert app_result['result'] == 'PASS'
    assert app_result['cellsReadBack'] == 300 and app_result['selectedUpdates'] == 52
    assert app_result['unchanged'] == 236 and app_result['hashOnlyHolds'] == 12
    assert app_result['localeCatalogs'] == 12 and app_result['orderedKeysPerCatalog'] == 6176

    product = readj(ROOT / 'application/product-commit.json')
    summary = readj(ROOT / 'application/application-summary.json')
    product_sha = product['sha']
    assert product['parent'] == BASE and summary['productCommit'] == product_sha
    assert run(['git','-C',str(repo),'rev-parse',f'{product_sha}^']) == BASE
    assert run(['git','-C',str(repo),'rev-parse',f'{BASE}^{{tree}}']) == BASE_TREE
    assert run(['git','-C',str(repo),'rev-parse',f'{product_sha}^{{tree}}']) == product['tree'] == summary['productTree']
    product_paths = set(run(['git','-C',str(repo),'diff-tree','--no-commit-id','--name-only','-r',product_sha]).splitlines())
    assert product_paths == set(product['files']) and len(product_paths) == 12
    assert all(p.startswith('src/web/public/locales/') and p.endswith('.json') for p in product_paths)

    current_head = run(['git','-C',str(repo),'rev-parse','HEAD'])
    evidence_parent = run(['git','-C',str(repo),'rev-parse','HEAD^']) if current_head != product_sha else None
    if current_head != product_sha:
        assert evidence_parent == product_sha
        evidence_paths = set(run(['git','-C',str(repo),'diff-tree','--no-commit-id','--name-only','-r',current_head]).splitlines())
        assert evidence_paths and all(p.startswith('docs/pr-evidence/pr409-localization-2026-11-04/window-803-827/') for p in evidence_paths)
    assert not run(['git','-C',str(repo),'status','--porcelain=v1']) if args.stage == 'final' else True

    hooks = readj(ROOT / 'application/local-hooks-policy.json')
    assert hooks['hooksExecuted'] is False and hooks['testsBuildsScansCiPackagesExecuted'] is False
    assert 'one-shot' in hooks['method'] and 'No persistent' in hooks['method']

    # Refs and PR body are checked live; pre-push must still be at the original head/body.
    pr = json.loads(run(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json',
                         'number,state,isDraft,headRefName,headRefOid,baseRefName,baseRefOid,url,mergeable']))
    branch_ref = json.loads(run(['gh','api',f'repos/snapetech-org/slskdN/git/ref/heads/{BRANCH}']))
    pull = json.loads(run(['gh','api','repos/snapetech-org/slskdN/pulls/409']))
    assert pr['state']=='OPEN' and pr['isDraft'] is True and pr['headRefName']==BRANCH
    assert pr['baseRefName']=='main' and pr['baseRefOid']==PR_BASE
    assert pull['state']=='open' and pull['draft'] is True and pull['head']['ref']==BRANCH
    live_head = branch_ref['object']['sha']
    assert pull['head']['sha'] == live_head == pr['headRefOid']
    before = (ROOT / 'delivery/PR-body-before.md').read_bytes()
    target = (ROOT / 'delivery/PR-body-update-target.md').read_bytes()
    plan_body = readj(ROOT / 'delivery/PR-body-update-plan.json')
    assert target.startswith(before)
    assert hashlib.sha256(before).hexdigest() == plan_body['originalBodySha256']
    assert hashlib.sha256(target).hexdigest() == plan_body['targetBodySha256']
    live_body = (pull['body'] or '').encode('utf-8')
    if args.stage == 'pre-push':
        assert live_head == BASE and live_body == before
    else:
        assert live_head == current_head
        assert live_body.rstrip(b'\r\n') == target.rstrip(b'\r\n')
        assert live_body.rstrip(b'\r\n').startswith(before.rstrip(b'\r\n'))
        assert live_body.count('## W77 localization (ranks 803–827)'.encode('utf-8')) == 1
    print(json.dumps({'result':'PASS','stage':args.stage,'productCommit':product_sha,
                      'branchHead':live_head,'cellsReadBack':300,'updates':52,
                      'retained':236,'textFreeHolds':12,'localeKeyOrder':'PASS',
                      'PRBody':'PASS' if args.stage=='final' else 'original bytes intact'},indent=2))


if __name__ == '__main__':
    main()
