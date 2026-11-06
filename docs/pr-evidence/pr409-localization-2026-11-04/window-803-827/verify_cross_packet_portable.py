#!/usr/bin/env python3
"""Portable verifier for bundled W77 candidate-free, primary, blind, and cross packets."""
import argparse
import collections
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEAD = '582ae64e5c3af275490f11f4350b33da7373a3c3'
TREE = 'b8692bb066cede93b6668806d0b97816135ce647'
BASE = 'f25d263a2a7cdb2c8f76c40c346cb10f749a9356'


def readj(path):
    return json.loads(path.read_text(encoding='utf-8'))


def readjl(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]


def sha(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def run(args):
    return subprocess.check_output(args, text=True).strip()


def check_sums(folder, filename):
    subprocess.run(['sha256sum', '-c', filename], cwd=folder, check=True, stdout=subprocess.DEVNULL)
    listed = {}
    for line in (folder / filename).read_text(encoding='utf-8').splitlines():
        if line.strip():
            digest, name = line.split('  ', 1)
            assert name not in listed
            listed[name] = digest
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p != folder / filename}
    assert set(listed) == actual


def check_sums_allow_nested(folder, filename):
    subprocess.run(['sha256sum', '-c', filename], cwd=folder, check=True, stdout=subprocess.DEVNULL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-checkout', type=Path, required=True, help='clean exact-head checkout for candidate-free/primary verifiers')
    ap.add_argument('--historical-offline', action='store_true', help='replay sealed evidence after the live PR head has advanced')
    args = ap.parse_args()
    source = args.source_checkout.resolve()
    cf = ROOT / 'candidate-free/input'
    primary = ROOT / 'primary-review/output'
    blind = ROOT / 'fresh-blind'
    cross = ROOT / 'cross-review'

    check_sums(cf, 'PACKET-SHA256SUMS.txt')
    check_sums(primary, 'SHA256SUMS.txt')
    check_sums_allow_nested(blind, 'BLIND-REVIEW-OUTPUT-SHA256SUMS.txt')
    check_sums(blind / 'candidate-free/input', 'PACKET-SHA256SUMS.txt')
    check_sums(cross, 'SHA256SUMS.txt')
    assert (cf / 'PACKET-SHA256SUMS.txt').read_bytes() == (blind / 'candidate-free/input/PACKET-SHA256SUMS.txt').read_bytes()

    if args.historical_offline:
        candidate_result = readj(cross / 'candidate-free-verifier.json')
        primary_result = readj(cross / 'primary-verifier.json')
        assert run(['git','-C',str(source),'rev-parse','HEAD']) == HEAD
        assert run(['git','-C',str(source),'rev-parse','HEAD^{tree}']) == TREE
        assert not run(['git','-C',str(source),'status','--porcelain=v1'])
    else:
        candidate_result = json.loads(subprocess.check_output(['python3', str(cf / 'verify_input.py'), '--repo', str(source)], text=True))
        primary_result = json.loads(subprocess.check_output(['python3', str(primary / 'verify_primary.py'), '--repo', str(source)], text=True))
    assert candidate_result['result'] == primary_result['result'] == 'PASS'
    assert candidate_result['head'] == primary_result['head'] == HEAD
    assert candidate_result['tree'] == primary_result['tree'] == TREE

    linkage = readj(cross / 'input-linkage.json')
    local_inputs = {
        'candidateFreeManifest': cf / 'manifest.json',
        'candidateFreeChecksumList': cf / 'PACKET-SHA256SUMS.txt',
        'primaryManifest': primary / 'manifest.json',
        'primaryChecksumList': primary / 'SHA256SUMS.txt',
        'blindManifest': blind / 'BLIND-REVIEW-MANIFEST.json',
        'blindSummary': blind / 'BLIND-REVIEW-SUMMARY.json',
        'blindDecisions': blind / 'BLIND-REVIEW-DECISIONS.jsonl',
        'blindChecksumList': blind / 'BLIND-REVIEW-OUTPUT-SHA256SUMS.txt',
    }
    assert set(local_inputs) == set(linkage['inputs'])
    for name, path in local_inputs.items():
        assert sha(path.read_bytes()) == linkage['inputs'][name]['sha256']
    assert linkage['candidateFreeLinkage']['primaryManifestDeclaresSame'] is True
    assert linkage['candidateFreeLinkage']['blindManifestDeclaresSame'] is True
    blind_manifest = readj(blind / 'BLIND-REVIEW-MANIFEST.json')
    assert blind_manifest['primaryReviewMaterialAccessed'] is False
    assert blind_manifest['perCellPrimaryRecommendationsAccessed'] is False
    assert blind_manifest['semanticReviewStartedBeforeSeal'] is False

    cells = readjl(cf / 'source-current-cells.jsonl')
    callers = readjl(cf / 'caller-contexts.jsonl')
    primary_rows = readjl(primary / 'primary-review.jsonl')
    corrections = readjl(primary / 'corrections.jsonl')
    holds = readjl(primary / 'holds-hash-only.jsonl')
    blind_rows = readjl(blind / 'BLIND-REVIEW-DECISIONS.jsonl')
    ledger = readjl(cross / 'cross-ledger.jsonl')
    proposals = readjl(cross / 'selected-proposals.jsonl')
    plan = readj(cross / 'apply-plan.json')
    hold_reconciliation = readjl(cross / 'blind-hold-reconciliation.jsonl')
    cross_holds = readjl(cross / 'holds-hash-only.jsonl')
    summary = readj(cross / 'summary.json')
    def m(rows):
        out = {(r['sourceId'], r['locale']): r for r in rows}
        assert len(out) == len(rows)
        return out
    cell_map, primary_map, blind_map, ledger_map, proposal_map = map(m, (cells, primary_rows, blind_rows, ledger, proposals))
    assert len(callers) == 25 and len(cells) == len(ledger) == 300
    assert len(corrections) == 50 and len(holds) == 12
    assert len(proposals) == plan['operationCount'] == 52
    assert plan['sourceHead'] == HEAD and plan['sourceTree'] == TREE
    assert len(hold_reconciliation) == 20
    assert summary['sourcePin'] == {'head': HEAD, 'tree': TREE}
    assert summary['crossDispositionCounts'] == {'accept-current': 236, 'hold-hash-only': 12, 'select-update': 52}
    assert all(x['containsCandidate'] is False for x in cells)

    primary_correction_map = m(corrections)
    primary_hold_keys = {(x['sourceId'], x['locale']) for x in holds}
    cross_hold_keys = {(x['sourceId'], x['locale']) for x in cross_holds}
    assert primary_hold_keys == cross_hold_keys and len(cross_hold_keys) == 12
    assert set(proposal_map) == set(primary_correction_map) | {('src_3034c12681609f00','id'),('src_30774beffae75f66','de')}
    assert {(x['sourceId'],x['locale']) for x in plan['operations']} == set(proposal_map)

    counts = collections.Counter()
    for key, cell in cell_map.items():
        row = ledger_map[key]
        assert row['sourceSha256'] == cell['sourceSha256']
        assert row['currentTargetSha256'] == cell['currentTargetSha256']
        assert row['callerContextSha256'] == cell['callerContextSha256']
        if key in cross_hold_keys:
            counts['hold-hash-only'] += 1
            assert row['crossDisposition'] == 'hold-hash-only'
            for field in ('source','currentTarget','selectedTarget','catalogKey'):
                assert field not in row
        elif key in proposal_map:
            counts['select-update'] += 1
            prop = proposal_map[key]
            assert row['crossDisposition'] == 'select-update'
            assert prop['expectedCurrentTargetSha256'] == cell['currentTargetSha256']
            assert prop['sourceSha256'] == cell['sourceSha256']
            assert prop['selectedTargetSha256'] == sha(prop['selectedTarget'])
            assert row['selectedTarget'] == prop['selectedTarget']
        else:
            counts['accept-current'] += 1
            assert row['crossDisposition'] == 'accept-current'
            assert row['currentTarget'] == cell['currentTarget']
    assert counts == {'select-update':52,'accept-current':236,'hold-hash-only':12}
    blind_holds = {(x['sourceId'],x['locale']) for x in blind_rows if x['verdict']=='HOLD'}
    assert blind_holds == {(x['sourceId'],x['locale']) for x in hold_reconciliation}
    assert len(blind_holds) == 20 and blind_holds.issubset(set(proposal_map))

    # Confirm the sealed snapshots bind the review to the exact historical PR refs.
    for suffix in ('before','after'):
        pr = readj(cross / f'live-pr-{suffix}.json')
        branch = readj(cross / f'live-branch-{suffix}.json')
        pull = readj(cross / f'live-pull-{suffix}.json')
        assert pr['state']=='OPEN' and pr['isDraft'] is True and pr['headRefOid']==HEAD and pr['baseRefOid']==BASE
        assert branch['object']['sha']==HEAD and pull['head']['sha']==HEAD and pull['state']=='open'
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'cells':300,'updates':52,
                      'retained':236,'textFreeHolds':12,'blindHoldsResolved':20,
                      'candidateFreePrimaryBlindCrossChecksums':'PASS',
                      'reviewVerifierMode':'historical-offline' if args.historical_offline else 'live-ref-attested'},indent=2))


if __name__ == '__main__':
    main()
