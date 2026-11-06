#!/usr/bin/env python3
"""Build the root adjudication and exact-hash plan for slskdN W953–W977."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w953-977-20261105')
OUT = ROOT / 'root-application'
HEAD = 'fc8e42a06363ceee762ae084bbe716953d4a5d94'
TREE = 'e04aa06b8cfb0ee41cae90aef601a0552b5e85bd'
BASE = 'f25d263a2a7cdb2c8f76c40c346cb10f749a9356'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def sha_text(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def require(condition, message):
    if not condition:
        raise SystemExit('FAIL: ' + message)


def main():
    candidate_root = ROOT / 'candidate-free' / 'input'
    candidate = read_jsonl(candidate_root / 'source-current-cells.jsonl')
    cross = read_jsonl(ROOT / 'cross-review' / 'cross-review-ledger.jsonl')
    primary = read_jsonl(ROOT / 'primary-review' / 'corrections.jsonl')
    candidate_manifest = read_json(candidate_root / 'manifest.json')
    cross_summary = read_json(ROOT / 'cross-review' / 'summary.json')
    primary_by_key = {(r['sourceId'], r['locale']): r for r in primary}
    candidate_by_key = {(r['continuationRank'], r['locale']): r for r in candidate}
    cross_by_key = {(r['continuationRank'], r['locale']): r for r in cross}
    require(len(candidate) == len(cross) == 300, 'expected complete 300-cell candidate/cross matrices')
    require(len(candidate_by_key) == len(cross_by_key) == 300, 'duplicate or missing rank/locale cell')
    require(candidate_manifest['head'] == HEAD and candidate_manifest['tree'] == TREE, 'candidate-free head/tree mismatch')
    require(cross_summary['head'] == HEAD and cross_summary['tree'] == TREE, 'cross-review head/tree mismatch')
    require(cross_summary['apiBase'] == BASE and cross_summary['result'] == 'PASS', 'cross-review base/result mismatch')

    ledger = []
    changes = []
    counts = collections.Counter()
    recommendation_counts = collections.Counter()
    root_override = None

    for key in sorted(candidate_by_key):
        c = candidate_by_key[key]
        x = cross_by_key[key]
        require(c['sourceId'] == x.get('sourceId', c['sourceId']), f'source ID mismatch at {key}')
        for field in ('currentTargetSha256', 'callerContextSha256', 'callerCount'):
            require(c[field] == x[field], f'{field} mismatch at {key}')
        require(c['sourceSha256'] == x['sourceTextSha256'], f'source hash mismatch at {key}')
        require(sha_text(c['currentTarget']) == c['currentTargetSha256'], f'candidate current-target hash mismatch at {key}')
        rec = x['recommendation']
        recommendation_counts[rec] += 1
        common = {
            'schemaVersion': 1,
            'continuationRank': key[0],
            'remainingQueueRank': c['remainingQueueRank'],
            'locale': key[1],
            'callerContextSha256': c['callerContextSha256'],
            'callerCount': c['callerCount'],
            'currentTargetSha256': c['currentTargetSha256'],
            'sourceSha256': c['sourceSha256'],
            'crossRecommendation': rec,
            'crossRationale': x['rationale'],
        }

        if rec == 'hold-hash-only':
            require(x.get('sourceTextIncluded') is False and x.get('currentTargetTextIncluded') is False and x.get('recommendedTargetTextIncluded') is False,
                    'hash-only hold unexpectedly contains text')
            counts['hold-hash-only'] += 1
            ledger.append({
                **common,
                'sourceIdSha256': x['sourceIdSha256'],
                'sourceTextSha256': x['sourceTextSha256'],
                'rootDisposition': 'hold-non-user-facing-hash-only',
                'selectedTargetSha256': None,
                'rootRationale': 'All pinned uses are layout/alignment attributes, not user-facing localization calls; retain the hash-only hold across locales.',
            })
            continue

        require(rec in ('accept-current', 'accept-primary', 'accept-blind', 'accept-agreement', 'adjust'), f'unexpected cross recommendation {rec}')
        if rec == 'accept-current':
            require(x['recommendedTargetSha256'] == c['currentTargetSha256'], f'accept-current target is not the current hash at {key}')
            counts['accept-current'] += 1
            ledger.append({
                **common,
                'sourceId': c['sourceId'],
                'source': c['source'],
                'currentTarget': c['currentTarget'],
                'rootDisposition': 'accept-current',
                'selectedTarget': c['currentTarget'],
                'selectedTargetSha256': c['currentTargetSha256'],
                'rootRationale': 'Retain the exact current translation; independent cross-review accepted its hash.',
            })
            continue

        selected = x['recommendedTarget']
        selected_sha = x['recommendedTargetSha256']
        require(sha_text(selected) == selected_sha, f'recommended target hash mismatch at {key}')
        require(all(x['tokenIntegrity'].values()), f'token-integrity mismatch at {key}')
        recommendation_source = x['recommendationSource']
        if key == (977, 'vi') and c['sourceId'] == 'src_366ee9dd4d52817e':
            p = primary_by_key[(c['sourceId'], key[1])]
            require(p['candidateTarget'] == 'Chuyển giao vào hàng đợi tiếp nhận nội dung', 'Vietnamese root adjustment candidate changed')
            selected = p['candidateTarget']
            selected_sha = p['candidateTargetSha256']
            require(sha_text(selected) == selected_sha, 'Vietnamese root-adjustment hash mismatch')
            disposition = 'root-manual-adjustment'
            recommendation_source = 'primary-proposal-selected-by-root'
            root_rationale = 'Use neutral “content intake” wording; the source does not establish a commercial purchase, so avoid the cross-proposed term that can imply buying content.'
            root_override = {'rank': key[0], 'locale': key[1], 'crossTargetSha256': x['recommendedTargetSha256'], 'selectedTargetSha256': selected_sha}
            counts['root-manual-adjustment'] += 1
        elif rec == 'adjust':
            disposition = 'accept-cross-adjustment'
            root_rationale = 'Accept the cross-review adjustment after checking source wording, caller context, and exact hashes.'
            counts['accept-cross-adjustment'] += 1
        else:
            source_decision = x['primaryDisposition'] if rec in ('accept-primary', 'accept-agreement') else x['blindDecision']
            if source_decision == 'refinement':
                disposition = 'accept-refinement'
                counts['accept-refinement'] += 1
            else:
                disposition = 'accept-correction'
                counts['accept-correction'] += 1
            root_rationale = 'Accept the independent cross-review selection after checking source meaning, caller context, current value, reviewer reconciliation, and token integrity.'

        require(selected != c['currentTarget'], f'change disposition selects current text at {key}')
        row = {
            **common,
            'sourceId': c['sourceId'],
            'source': c['source'],
            'currentTarget': c['currentTarget'],
            'rootDisposition': disposition,
            'selectedTarget': selected,
            'selectedTargetSha256': selected_sha,
            'recommendationSource': recommendation_source,
            'rootRationale': root_rationale,
        }
        ledger.append(row)
        changes.append({
            'continuationRank': key[0],
            'remainingQueueRank': c['remainingQueueRank'],
            'sourceId': c['sourceId'],
            'locale': key[1],
            'catalogPath': c['catalogPath'],
            'source': c['source'],
            'sourceSha256': c['sourceSha256'],
            'callerContextSha256': c['callerContextSha256'],
            'currentTarget': c['currentTarget'],
            'currentTargetSha256': c['currentTargetSha256'],
            'crossRecommendedTarget': x['recommendedTarget'],
            'crossRecommendedTargetSha256': x['recommendedTargetSha256'],
            'selectedTarget': selected,
            'selectedTargetSha256': selected_sha,
            'rootDisposition': disposition,
            'rootRationale': root_rationale,
        })

    require(counts['accept-current'] == 174 and counts['accept-correction'] == 110 and counts['accept-refinement'] == 3 and counts['root-manual-adjustment'] == 1 and counts['hold-hash-only'] == 12 and counts['accept-cross-adjustment'] == 0 and sum(counts.values()) == 300, 'root disposition totals mismatch')
    require(len(changes) == 114 and len(ledger) == 300 and root_override is not None, 'unexpected root decision totals')

    catalog_rows = read_jsonl(candidate_root / 'catalog-structure.jsonl')
    catalogs = [{
        'locale': r['locale'],
        'path': r['path'],
        'preimageSha256': r['sha256'],
        'entryCount': r['entryCount'],
        'orderedKeySha256': r['orderedKeySha256'],
        'gitBlob': r['gitBlob'],
    } for r in catalog_rows]
    require(len(catalogs) == 12, 'expected 12 locale catalog pins')

    plan = {
        'schemaVersion': 1,
        'artifact': 'slskdN PR #409 W953–W977 exact-hash root application plan',
        'sourcePin': {'head': HEAD, 'tree': TREE, 'base': BASE},
        'candidateCells': 300,
        'crossReviewResult': 'PASS',
        'crossRecommendedChanges': 114,
        'rootManualOverrides': 1,
        'heldHashOnlyCells': 12,
        'catalogs': catalogs,
        'changes': changes,
    }
    summary = {
        'status': 'ROOT-ADJUDICATED',
        'repository': 'snapetech-org/slskdN',
        'pullRequest': 409,
        'window': 'W953–W977; remaining queue ranks 853–877',
        'head': HEAD,
        'tree': TREE,
        'base': BASE,
        'candidateCells': 300,
        'crossRecommendationCounts': dict(recommendation_counts),
        'rootDispositionCounts': dict(counts),
        'crossRecommendedChanges': 114,
        'appliedPlanChanges': len(changes),
        'rootManualOverrides': [root_override],
        'heldRank966Cells': 12,
        'heldReason': 'Pinned production uses are layout/alignment attributes, not user-facing localization calls; hold rows remain text-free.',
        'confidence': 'moderate',
        'nativeSpeakerApprovalClaimed': False,
        'browserReviewClaimed': False,
        'testsBuildsScansCiRun': False,
        'workflowChanges': 0,
    }
    (OUT / 'root-review-ledger.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in ledger), encoding='utf-8')
    (OUT / 'root-application-plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (OUT / 'root-review-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'result': 'PASS', 'cells': len(ledger), 'changes': len(changes), 'counts': dict(counts), 'rootOverride': root_override}, ensure_ascii=False, sort_keys=True))

if __name__ == '__main__':
    main()
