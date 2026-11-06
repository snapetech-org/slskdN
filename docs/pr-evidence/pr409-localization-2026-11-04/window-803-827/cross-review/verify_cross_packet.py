#!/usr/bin/env python3
"""Offline verifier for the sealed slskdN W77 cross-audit packet."""
import collections
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

PACKET = Path(__file__).resolve().parent
BASE = Path('/home/keith/Documents/code/task-scratch')
PRIMARY_ROOT = BASE / 'slskdn-pr409-w77-803-827-primary-20261104'
CANDIDATE = PRIMARY_ROOT / 'candidate-free/input'
PRIMARY = PRIMARY_ROOT / 'primary-review/output'
BLIND = BASE / 'slskdn-pr409-w77-803-827-blind-fresh-20261104'
SOURCE = Path('/mnt/disks/scratch/task-worktrees/localization-20261104/slskdn-pr409-w76-778-802-source')
HEAD = '582ae64e5c3af275490f11f4350b33da7373a3c3'
TREE = 'b8692bb066cede93b6668806d0b97816135ce647'


def json_read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def jsonl_read(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def placeholders(text):
    return collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", text))


def markup(text):
    return collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", text))


def numerics(text):
    return ["".join(str(unicodedata.digit(ch)) if ch.isdigit() else ch for ch in match)
            for match in re.findall(r"\d+", text)]


def protected(text):
    tokens = set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", text))
    tokens.update(token for token in ("slskdN", "Tor", "Wishlist", "Chromaprint") if token in text)
    return tokens


def check_sums(directory, manifest):
    subprocess.run(['sha256sum', '-c', manifest], cwd=directory, check=True, stdout=subprocess.DEVNULL)


def run_json(args, cwd=None):
    return json.loads(subprocess.check_output(args, cwd=cwd, text=True))


def main():
    manifest = json_read(PACKET / 'manifest.json')
    summary = json_read(PACKET / 'summary.json')
    assert manifest['reviewMode'] == 'non-blind independent cross-audit/reconciliation'
    assert manifest['sourcePin'] == {'head': HEAD, 'tree': TREE}
    assert 'not blind' in manifest['provenanceDisclosure']
    assert summary['sourcePin'] == {'head': HEAD, 'tree': TREE}
    assert summary['repositoryOrPrEdits'] == 0

    check_sums(CANDIDATE, 'PACKET-SHA256SUMS.txt')
    check_sums(PRIMARY, 'SHA256SUMS.txt')
    check_sums(BLIND, 'BLIND-REVIEW-OUTPUT-SHA256SUMS.txt')
    check_sums(BLIND / 'candidate-free/input', 'PACKET-SHA256SUMS.txt')
    assert (CANDIDATE / 'PACKET-SHA256SUMS.txt').read_bytes() == (BLIND / 'candidate-free/input/PACKET-SHA256SUMS.txt').read_bytes()

    candidate_result = run_json(['python3', str(CANDIDATE / 'verify_input.py'), '--repo', str(SOURCE)])
    primary_result = run_json(['python3', str(PRIMARY / 'verify_primary.py'), '--repo', str(SOURCE)])
    assert candidate_result['result'] == primary_result['result'] == 'PASS'
    assert candidate_result['head'] == primary_result['head'] == HEAD
    assert candidate_result['tree'] == primary_result['tree'] == TREE
    assert candidate_result['cellCount'] == primary_result['cellCount'] == 300
    assert candidate_result['callerlessSelectedSources'] == 1
    assert primary_result['callerlessHashOnlyHolds'] == 12
    assert json_read(PACKET / 'candidate-free-verifier.json') == candidate_result
    assert json_read(PACKET / 'primary-verifier.json') == primary_result

    linkage = json_read(PACKET / 'input-linkage.json')
    assert linkage['sourcePin'] == {'head': HEAD, 'tree': TREE}
    assert linkage['candidateFreeLinkage']['primaryManifestDeclaresSame'] is True
    assert linkage['candidateFreeLinkage']['blindManifestDeclaresSame'] is True
    for item in linkage['inputs'].values():
        digest = hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()
        assert digest == item['sha256']
    blind_manifest = json_read(BLIND / 'BLIND-REVIEW-MANIFEST.json')
    assert blind_manifest['primaryReviewMaterialAccessed'] is False
    assert blind_manifest['perCellPrimaryRecommendationsAccessed'] is False
    assert blind_manifest['semanticReviewStartedBeforeSeal'] is False
    blind_summary = json_read(BLIND / 'BLIND-REVIEW-SUMMARY.json')
    assert blind_summary['verdictCounts'] == {'HOLD': 20, 'PASS': 280}
    assert blind_summary['cellCount'] == 300

    source_head = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
    source_tree = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
    source_status = subprocess.check_output(['git', '-C', str(SOURCE), 'status', '--porcelain=v1'], text=True).strip()
    assert source_head == HEAD and source_tree == TREE and not source_status

    cells = jsonl_read(CANDIDATE / 'source-current-cells.jsonl')
    primary_rows = jsonl_read(PRIMARY / 'primary-review.jsonl')
    corrections = jsonl_read(PRIMARY / 'corrections.jsonl')
    holds = jsonl_read(PRIMARY / 'holds-hash-only.jsonl')
    blind = jsonl_read(BLIND / 'BLIND-REVIEW-DECISIONS.jsonl')
    callers = jsonl_read(CANDIDATE / 'caller-contexts.jsonl')
    ledger = jsonl_read(PACKET / 'cross-ledger.jsonl')
    selected = jsonl_read(PACKET / 'selected-proposals.jsonl')
    reconciliation = jsonl_read(PACKET / 'proposal-reconciliation.jsonl')
    blind_hold_reconciliation = jsonl_read(PACKET / 'blind-hold-reconciliation.jsonl')
    disagreements = jsonl_read(PACKET / 'proposal-disagreements.jsonl')
    hash_holds = jsonl_read(PACKET / 'holds-hash-only.jsonl')
    context_review = jsonl_read(PACKET / 'source-context-review.jsonl')
    plan = json_read(PACKET / 'apply-plan.json')

    def mapping(rows):
        result = {(r['sourceId'], r['locale']): r for r in rows}
        assert len(result) == len(rows)
        return result

    cell_map = mapping(cells)
    primary_map = mapping(primary_rows)
    blind_map = mapping(blind)
    ledger_map = mapping(ledger)
    selected_map = mapping(selected)
    assert len(cells) == len(ledger) == 300
    assert len(callers) == len(context_review) == 25
    assert len(corrections) == len(reconciliation) == 50
    assert len(holds) == len(hash_holds) == 12
    assert len(selected) == plan['operationCount'] == 52
    assert len(blind_hold_reconciliation) == 20
    assert len(disagreements) == 34
    assert set(cell_map) == set(primary_map) == set(blind_map) == set(ledger_map)
    assert set(selected_map) == {(r['sourceId'], r['locale']) for r in selected}

    caller_map = {r['sourceId']: r for r in callers}
    context_map = {r['sourceId']: r for r in context_review}
    assert len(context_map) == 25
    hold_keys = {(r['sourceId'], r['locale']) for r in holds}
    correction_map = mapping(corrections)
    own_keys = {('src_3034c12681609f00', 'id'), ('src_30774beffae75f66', 'de')}
    assert set(selected_map) == set(correction_map) | own_keys
    assert len(set(correction_map) & own_keys) == 0

    decision_counts = collections.Counter()
    for key, cell in cell_map.items():
        row = ledger_map[key]
        primary = primary_map[key]
        blind_row = blind_map[key]
        caller = caller_map[cell['sourceId']]
        context = context_map[cell['sourceId']]
        assert row['sourceSha256'] == cell['sourceSha256']
        assert row['currentTargetSha256'] == cell['currentTargetSha256']
        assert row['callerContextSha256'] == cell['callerContextSha256']
        assert row['productionCallerCount'] == caller['productionCallerCount']
        assert context['productionCallerCount'] == caller['productionCallerCount']
        assert context['callerContextSha256'] == cell['callerContextSha256']
        assert context['callerRefs'] == row['callerRefs']
        assert row['primaryDisposition'] == primary['disposition']
        assert row['blindVerdict'] == blind_row['verdict']
        assert row['pinHead'] == HEAD and row['pinTree'] == TREE
        decision_counts[row['crossDisposition']] += 1
        if key in hold_keys:
            assert row['crossDisposition'] == 'hold-hash-only'
            for forbidden in ('source', 'currentTarget', 'selectedTarget', 'catalogKey'):
                assert forbidden not in row
        elif key in selected_map:
            proposal = selected_map[key]
            assert row['crossDisposition'] == 'select-update'
            assert row['source'] == cell['source'] and row['currentTarget'] == cell['currentTarget']
            assert row['selectedTarget'] == proposal['selectedTarget']
            assert row['selectedTargetSha256'] == sha(proposal['selectedTarget']) == proposal['selectedTargetSha256']
            assert proposal['expectedCurrentTargetSha256'] == cell['currentTargetSha256']
            assert proposal['sourceSha256'] == cell['sourceSha256']
            assert proposal['catalogPath'] == cell['catalogPath']
            assert proposal['catalogKey'] == cell['catalogKey']
            assert proposal['catalogPath'].startswith('src/web/public/locales/')
            target = proposal['selectedTarget']
            assert placeholders(cell['source']) == placeholders(target)
            assert markup(cell['source']) == markup(target)
            source_nums, target_nums = collections.Counter(numerics(cell['source'])), collections.Counter(numerics(target))
            assert all(target_nums[token] >= count for token, count in source_nums.items())
            assert protected(cell['source']).issubset(protected(target))
        else:
            assert row['crossDisposition'] == 'accept-current'
            assert row['source'] == cell['source'] and row['currentTarget'] == cell['currentTarget']
            assert row['currentTargetSha256'] == sha(row['currentTarget'])
        assert cell['containsCandidate'] is False

    assert decision_counts == {'select-update': 52, 'accept-current': 236, 'hold-hash-only': 12}
    for key, proposal in correction_map.items():
        cell = cell_map[key]
        assert proposal['currentTargetSha256'] == cell['currentTargetSha256']
        assert proposal['sourceSha256'] == cell['sourceSha256']
        assert proposal['targetSha256'] == sha(proposal['target'])
        assert selected_map[key]['selectedTarget'] == proposal['target']
    assert selected_map[('src_3034c12681609f00', 'id')]['selectedTarget'] == 'Gagal menyinkronkan backfill pod: {message}'
    assert selected_map[('src_30774beffae75f66', 'de')]['selectedTarget'] == 'Mitgliedschaftsdatensatz veröffentlichen'

    for hold in hash_holds:
        for forbidden in ('source', 'currentTarget', 'target', 'selectedTarget', 'catalogKey'):
            assert forbidden not in hold
        assert hold['productionCallerCount'] == 0
        assert (hold['sourceId'], hold['locale']) in hold_keys

    blind_hold_keys = {(r['sourceId'], r['locale']) for r in blind if r['verdict'] == 'HOLD'}
    resolution_keys = {(r['sourceId'], r['locale']) for r in blind_hold_reconciliation}
    assert len(blind_hold_keys) == 20 and blind_hold_keys == resolution_keys
    assert all(k in selected_map for k in blind_hold_keys)
    assert sum(r['selectedFrom'] == 'primary-proposal' for r in selected) == 50
    assert sum(r['selectedFrom'] == 'cross-authored-proposal' for r in selected) == 2
    assert sum(r['crossDecision'] == 'independently-select-primary-proposal-despite-blind-pass' for r in disagreements) == 32
    assert sum(r['crossDecision'] == 'add-cross-authored-proposal' for r in disagreements) == 2

    assert plan['mode'] == 'recommendation-only; not applied'
    assert plan['sourceHead'] == HEAD and plan['sourceTree'] == TREE
    assert plan['operations'] == selected
    assert 'not applied' in plan['mode']

    # Before/after snapshots must agree with the exact pinned PR and branch refs.
    for suffix in ('before', 'after'):
        pr = json_read(PACKET / f'live-pr-{suffix}.json')
        branch = json_read(PACKET / f'live-branch-{suffix}.json')
        pull = json_read(PACKET / f'live-pull-{suffix}.json')
        main = json_read(PACKET / f'live-main-{suffix}.json')
        drift = json_read(PACKET / f'main-drift-{suffix}.json')
        local = json_read(PACKET / f'source-{suffix}.json')
        assert pr['state'] == 'OPEN' and pr['isDraft'] is True
        assert pr['headRefOid'] == HEAD and pr['baseRefOid'] == 'f25d263a2a7cdb2c8f76c40c346cb10f749a9356'
        assert branch['object']['sha'] == HEAD
        assert pull['head']['sha'] == HEAD and pull['state'] == 'open'
        assert main['commit']['sha'] == drift['commits'][-1]['sha']
        assert drift['status'] == 'ahead' and drift['ahead_by'] == 4 and drift['behind_by'] == 0
        filenames = {f['filename'] for f in drift['files']}
        assert not any('locales/' in name or name.startswith('src/web/src/') for name in filenames)
        assert local['head'] == HEAD and local['tree'] == TREE and not local['statusPorcelain']

    checksums = PACKET / 'SHA256SUMS.txt'
    if checksums.exists():
        check_sums(PACKET, 'SHA256SUMS.txt')
        listed = set()
        for line in checksums.read_text(encoding='utf-8').splitlines():
            if line.strip():
                digest, name = line.split('  ', 1)
                assert name not in listed and len(digest) == 64
                listed.add(name)
        actual = {p.relative_to(PACKET).as_posix() for p in PACKET.rglob('*')
                  if p.is_file() and p != checksums}
        assert listed == actual

    print(json.dumps({
        'result': 'PASS', 'sourceHead': HEAD, 'sourceTree': TREE,
        'cells': len(ledger), 'selectedUpdates': len(selected),
        'callerlessTextFreeHolds': len(hash_holds),
        'blindHoldsResolved': len(blind_hold_reconciliation),
        'primaryProposalRows': len(corrections),
        'liveRefs': 'PASS before and after',
        'repositoryEdits': 0,
    }, indent=2))


if __name__ == '__main__':
    main()
