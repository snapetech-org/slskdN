#!/usr/bin/env python3
"""Build the recommendation-only W77 cross-audit packet from sealed inputs."""
import collections
import hashlib
import json
from pathlib import Path

BASE = Path('/home/keith/Documents/code/task-scratch')
PACKET = BASE / 'slskdn-pr409-w77-cross-20261104'
PRIMARY_ROOT = BASE / 'slskdn-pr409-w77-803-827-primary-20261104'
CANDIDATE = PRIMARY_ROOT / 'candidate-free/input'
PRIMARY = PRIMARY_ROOT / 'primary-review/output'
BLIND = BASE / 'slskdn-pr409-w77-803-827-blind-fresh-20261104'
PINNED_HEAD = '582ae64e5c3af275490f11f4350b33da7373a3c3'
PINNED_TREE = 'b8692bb066cede93b6668806d0b97816135ce647'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def dump_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def dump_jsonl(path, rows):
    path.write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows), encoding='utf-8')


RATIONALE = {
    805: 'The MediaCorePods caller handles a pod backfill-stats operation. The affected current wording means refilling or replenishing a pod; the selected wording preserves the technical backfill meaning and the message placeholder.',
    806: 'The caller maps this label to an olive-colored swatch. The selected wording identifies the color rather than the olive fruit.',
    807: 'The caller passes a dynamic scan ID and library path. The selected Korean wording labels both values and avoids a particle whose form would depend on the dynamic ID.',
    808: 'The surrounding TransferManager states refer to completed transfers. The selected wording makes completed modify the transfers in the history, rather than the act of loading history.',
    809: 'The caller reports an empty set of matched playlist rows before creation. The selected Japanese wording says no matching rows can be added to the named playlist and avoids the current stacked modifiers.',
    811: 'The caller uses this text as the Mesh Evidence Publish recipe title. The selected Arabic repairs the word order; the selected Hindi transliterates Mesh instead of using मेष, which means ram/Aries.',
    812: 'The caller warns that publishing membership records exposes peer IDs, roles, keys, ban state, and participation history. German Nachweis means proof/certificate; Datensatz identifies a record.',
    815: 'The caller localizes Strong as a match-confidence tier. In Chinese, 强/強 denotes strength here, while 强大/強大 more strongly suggests power or might.',
    816: 'The caller reports that a search task has entered a queue and that no download starts before result selection. The selected wording states that queued status and preserves the no-download condition.',
    817: 'The surrounding German errors use formal Sie address. The selected wording makes this retry message consistent with that UI tone.',
    821: 'The French current wording describes a page about upcoming collections. The caller labels forward pagination; Page suivante means the next page.',
    825: 'The caller displays the disabled state of the DHT rendezvous feature. The selected wording clarifies the rendezvous point/feature and uses a feature control term where the current literal gate wording is awkward or misleading.',
}

OWN_PROPOSALS = {
    ('src_3034c12681609f00', 'id'): {
        'target': 'Gagal menyinkronkan backfill pod: {message}',
        'rationale': RATIONALE[805],
        'confidence': 'moderate',
    },
    ('src_30774beffae75f66', 'de'): {
        'target': 'Mitgliedschaftsdatensatz veröffentlichen',
        'rationale': RATIONALE[812],
        'confidence': 'moderate',
    },
}


def caller_refs(row):
    return [
        {
            'path': ref['path'], 'line': ref['line'],
            'contextSha256': ref['contextSha256'],
            'lineSha256': ref['lineSha256'],
            'fileSha256': ref['fileSha256'], 'gitBlob': ref['gitBlob'],
        }
        for ref in row['callerRefs']
    ]


def main():
    cells = read_jsonl(CANDIDATE / 'source-current-cells.jsonl')
    callers = read_jsonl(CANDIDATE / 'caller-contexts.jsonl')
    primary_reviews = read_jsonl(PRIMARY / 'primary-review.jsonl')
    primary_corrections = read_jsonl(PRIMARY / 'corrections.jsonl')
    primary_holds = read_jsonl(PRIMARY / 'holds-hash-only.jsonl')
    blind_reviews = read_jsonl(BLIND / 'BLIND-REVIEW-DECISIONS.jsonl')

    cell_map = {(r['sourceId'], r['locale']): r for r in cells}
    review_map = {(r['sourceId'], r['locale']): r for r in primary_reviews}
    correction_map = {(r['sourceId'], r['locale']): r for r in primary_corrections}
    blind_map = {(r['sourceId'], r['locale']): r for r in blind_reviews}
    hold_map = {(r['sourceId'], r['locale']): r for r in primary_holds}
    caller_map = {r['sourceId']: r for r in callers}
    keys = set(cell_map)
    assert len(cells) == 300 and len(keys) == 300
    assert keys == set(review_map) == set(blind_map)
    assert len(callers) == 25
    assert {r['continuationRank'] for r in cells} == set(range(803, 828))
    assert all(r['containsCandidate'] is False for r in cells)
    attestation = read_json(CANDIDATE / 'head-tree-attestation.json')
    assert attestation['headRefOid'] == PINNED_HEAD
    assert attestation['treeOid'] == PINNED_TREE
    assert len(primary_corrections) == 50 and len(primary_holds) == 12

    selected = {}
    for key, proposal in correction_map.items():
        source = cell_map[key]
        assert proposal['currentTargetSha256'] == source['currentTargetSha256']
        assert proposal['sourceSha256'] == source['sourceSha256']
        assert proposal['targetSha256'] == sha(proposal['target'])
        selected[key] = {
            'target': proposal['target'], 'targetSha256': proposal['targetSha256'],
            'selectedFrom': 'primary-proposal', 'crossRationale': RATIONALE[source['continuationRank']],
            'confidence': proposal['confidence'],
        }
    for key, proposal in OWN_PROPOSALS.items():
        source = cell_map[key]
        assert key not in selected
        selected[key] = {
            'target': proposal['target'], 'targetSha256': sha(proposal['target']),
            'selectedFrom': 'cross-authored-proposal', 'crossRationale': proposal['rationale'],
            'confidence': proposal['confidence'],
        }

    ledger = []
    selected_rows = []
    hold_rows = []
    reconciliation = []
    blind_hold_reconciliation = []
    disagreements = []
    source_decisions = {}
    decision_counts = collections.Counter()
    for key, cell in sorted(cell_map.items(), key=lambda kv: (kv[1]['continuationRank'], kv[1]['locale'])):
        source_id, locale = key
        primary = review_map[key]
        blind = blind_map[key]
        caller = caller_map[source_id]
        caller_count = caller['productionCallerCount']
        is_hash_hold = key in hold_map or caller_count == 0
        base = {
            'window': 'W77', 'continuationRank': cell['continuationRank'],
            'remainingQueueRank': cell['remainingQueueRank'],
            'sourceId': source_id, 'locale': locale,
            'sourceSha256': cell['sourceSha256'],
            'currentTargetSha256': cell['currentTargetSha256'],
            'callerContextSha256': cell['callerContextSha256'],
            'productionCallerCount': caller_count,
            'callerRefs': caller_refs(cell),
            'primaryDisposition': primary['disposition'],
            'blindVerdict': blind['verdict'], 'blindIssueCode': blind['issueCode'],
            'pinHead': PINNED_HEAD, 'pinTree': PINNED_TREE,
        }
        if is_hash_hold:
            assert caller_count == 0 and key in hold_map
            row = dict(base)
            row.update({
                'crossDisposition': 'hold-hash-only',
                'crossConfidence': 'high',
                'crossRationale': 'Callerless source: preserve as a text-free hash-only hold.',
            })
            hold_rows.append({
                'window': 'W77', 'continuationRank': cell['continuationRank'],
                'remainingQueueRank': cell['remainingQueueRank'],
                'sourceId': source_id, 'locale': locale,
                'sourceSha256': cell['sourceSha256'],
                'currentTargetSha256': cell['currentTargetSha256'],
                'catalogPath': cell['catalogPath'],
                'catalogFileSha256': cell['catalogFileSha256'],
                'catalogGitBlob': cell['catalogGitBlob'],
                'callerContextSha256': cell['callerContextSha256'],
                'productionCallerCount': 0,
                'holdReasonCode': 'CALLERLESS_TEXT_FREE_HOLD',
            })
        elif key in selected:
            proposal = selected[key]
            row = dict(base)
            row.update({
                'source': cell['source'],
                'currentTarget': cell['currentTarget'],
                'selectedTarget': proposal['target'],
                'selectedTargetSha256': proposal['targetSha256'],
                'selectedFrom': proposal['selectedFrom'],
                'crossDisposition': 'select-update',
                'crossConfidence': proposal['confidence'],
                'crossRationale': proposal['crossRationale'],
            })
            operation = {
                'window': 'W77', 'continuationRank': cell['continuationRank'],
                'sourceId': source_id, 'locale': locale,
                'catalogPath': cell['catalogPath'], 'catalogKey': cell['catalogKey'],
                'sourceSha256': cell['sourceSha256'],
                'expectedCurrentTargetSha256': cell['currentTargetSha256'],
                'selectedTarget': proposal['target'],
                'selectedTargetSha256': proposal['targetSha256'],
                'selectedFrom': proposal['selectedFrom'],
                'callerContextSha256': cell['callerContextSha256'],
            }
            selected_rows.append(operation)
            if proposal['selectedFrom'] == 'primary-proposal':
                rec = correction_map[key]
                reconciliation.append({
                    'sourceId': source_id, 'continuationRank': cell['continuationRank'],
                    'locale': locale, 'primaryDisposition': primary['disposition'],
                    'primaryTargetSha256': rec['targetSha256'],
                    'selectedTargetSha256': proposal['targetSha256'],
                    'currentTargetSha256': cell['currentTargetSha256'],
                    'blindVerdict': blind['verdict'], 'blindIssueCode': blind['issueCode'],
                    'crossDecision': 'select-primary-proposal',
                    'crossRationale': proposal['crossRationale'],
                })
            else:
                disagreements.append({
                    'sourceId': source_id, 'continuationRank': cell['continuationRank'],
                    'locale': locale, 'primaryDisposition': primary['disposition'],
                    'primaryTargetWasProposed': False,
                    'blindVerdict': blind['verdict'], 'blindIssueCode': blind['issueCode'],
                    'currentTargetSha256': cell['currentTargetSha256'],
                    'selectedTargetSha256': proposal['targetSha256'],
                    'selectedFrom': proposal['selectedFrom'],
                    'crossDecision': 'add-cross-authored-proposal',
                    'crossRationale': proposal['crossRationale'],
                })
        else:
            row = dict(base)
            row.update({
                'source': cell['source'], 'currentTarget': cell['currentTarget'],
                'crossDisposition': 'accept-current',
                'crossConfidence': 'moderate',
                'crossRationale': 'Reviewed against the exact source and caller context; no material semantic defect found, so retain the current translation.',
            })
        if not is_hash_hold:
            assert caller_count > 0
            assert row.get('source') == cell['source']
        ledger.append(row)
        decision_counts[row['crossDisposition']] += 1

        if blind['verdict'] == 'HOLD':
            proposal = selected.get(key)
            assert proposal is not None
            blind_hold_reconciliation.append({
                'sourceId': source_id, 'continuationRank': cell['continuationRank'],
                'locale': locale, 'issueCode': blind['issueCode'],
                'blindCurrentTargetSha256': blind['currentTargetSha256'],
                'primaryDisposition': primary['disposition'],
                'selectedTargetSha256': proposal['targetSha256'],
                'resolution': proposal['selectedFrom'],
                'resolutionRationale': proposal['crossRationale'],
            })
        if primary['disposition'] == 'correct' and blind['verdict'] == 'PASS':
            disagreements.append({
                'sourceId': source_id, 'continuationRank': cell['continuationRank'],
                'locale': locale, 'primaryDisposition': 'correct',
                'primaryTargetWasProposed': True,
                'blindVerdict': 'PASS', 'blindIssueCode': None,
                'currentTargetSha256': cell['currentTargetSha256'],
                'selectedTargetSha256': selected[key]['targetSha256'],
                'selectedFrom': selected[key]['selectedFrom'],
                'crossDecision': 'independently-select-primary-proposal-despite-blind-pass',
                'crossRationale': selected[key]['crossRationale'],
            })
        source_decisions.setdefault(source_id, {
            'continuationRank': cell['continuationRank'],
            'sourceSha256': cell['sourceSha256'],
            'callerContextSha256': cell['callerContextSha256'],
            'productionCallerCount': caller_count,
            'callerRefs': caller_refs(cell),
        })

    assert decision_counts == {'select-update': 52, 'accept-current': 236, 'hold-hash-only': 12}
    assert len(blind_hold_reconciliation) == 20
    assert sum(r['crossDecision'] == 'select-primary-proposal' for r in reconciliation) == 50
    assert sum(r['blindVerdict'] == 'HOLD' for r in reconciliation) == 18
    assert sum(r['crossDecision'] == 'independently-select-primary-proposal-despite-blind-pass' for r in disagreements) == 32
    assert sum(r['crossDecision'] == 'add-cross-authored-proposal' for r in disagreements) == 2
    assert all('source' not in r and 'currentTarget' not in r and 'selectedTarget' not in r for r in hold_rows)

    dump_jsonl(PACKET / 'cross-ledger.jsonl', ledger)
    dump_jsonl(PACKET / 'selected-proposals.jsonl', selected_rows)
    dump_jsonl(PACKET / 'proposal-reconciliation.jsonl', reconciliation)
    dump_jsonl(PACKET / 'blind-hold-reconciliation.jsonl', blind_hold_reconciliation)
    dump_jsonl(PACKET / 'proposal-disagreements.jsonl', disagreements)
    dump_jsonl(PACKET / 'holds-hash-only.jsonl', hold_rows)
    dump_jsonl(PACKET / 'source-context-review.jsonl', [source_decisions[sid] | {'sourceId': sid} for sid in sorted(source_decisions, key=lambda s: source_decisions[s]['continuationRank'])])

    plan = {
        'schemaVersion': 1, 'mode': 'recommendation-only; not applied',
        'repository': 'snapetech-org/slskdN', 'pr': 409,
        'sourceHead': PINNED_HEAD, 'sourceTree': PINNED_TREE,
        'operationCount': len(selected_rows),
        'currentHashGuard': 'Each operation applies only when the catalog cell UTF-8 SHA-256 equals expectedCurrentTargetSha256.',
        'scope': 'Only the exact selected catalog cells listed below; no source, test, workflow, or other files.',
        'operations': selected_rows,
    }
    dump_json(PACKET / 'apply-plan.json', plan)

    blind_counts = collections.Counter(r['verdict'] for r in blind_reviews)
    primary_counts = collections.Counter(r['disposition'] for r in primary_reviews)
    rank_counts = collections.Counter(r['continuationRank'] for r in selected_rows)
    locale_counts = collections.Counter(r['locale'] for r in selected_rows)
    blind_hold_rank_counts = collections.Counter(r['continuationRank'] for r in blind_hold_reconciliation)
    blind_hold_locale_counts = collections.Counter(r['locale'] for r in blind_hold_reconciliation)
    source_pins = read_json(CANDIDATE / 'source-tree-attestation.json')
    summary = {
        'result': 'PASS', 'window': 'W77', 'pr': 409,
        'sourcePin': {'head': PINNED_HEAD, 'tree': PINNED_TREE},
        'cellCount': len(ledger), 'sourceCount': len(source_decisions),
        'localeCount': len({r['locale'] for r in cells}),
        'primaryDispositionCounts': dict(sorted(primary_counts.items())),
        'blindVerdictCounts': dict(sorted(blind_counts.items())),
        'crossDispositionCounts': dict(sorted(decision_counts.items())),
        'primaryProposals': len(primary_corrections),
        'selectedPrimaryProposals': len(reconciliation),
        'selectedCrossAuthoredProposals': len(OWN_PROPOSALS),
        'selectedUpdates': len(selected_rows),
        'blindHolds': len(blind_hold_reconciliation),
        'blindHoldsResolvedByPrimaryProposal': sum(r['resolution'] == 'primary-proposal' for r in blind_hold_reconciliation),
        'blindHoldsResolvedByCrossProposal': sum(r['resolution'] == 'cross-authored-proposal' for r in blind_hold_reconciliation),
        'blindHoldsByRank': {str(k): blind_hold_rank_counts[k] for k in sorted(blind_hold_rank_counts)},
        'blindHoldsByLocale': dict(sorted(blind_hold_locale_counts.items())),
        'primaryCorrectionsWhereBlindPassed': 32,
        'proposalDisagreements': {'primary-correction-and-blind-pass': 32, 'cross-authored-additions': 2},
        'callerlessHashOnlyHolds': len(hold_rows),
        'unresolvedContextualHolds': 0,
        'updatesByRank': {str(k): rank_counts[k] for k in sorted(rank_counts)},
        'updatesByLocale': dict(sorted(locale_counts.items())),
        'checksums': {
            'candidateFree': 'PASS; all listed hashes verified',
            'primary': 'PASS; all listed hashes verified',
            'blind': 'PASS; all listed hashes verified',
            'blindCandidateFreeCopy': 'PASS; byte-identical checksum manifest and all listed hashes verified',
        },
        'sourcePinRecheck': {'head': source_pins['head'], 'tree': source_pins['tree']},
        'baseDrift': 'Live main is 4 commits ahead and 0 behind PR base; compare contains no localization/catalog/source changes. Workflows remain outside this task.',
        'reviewProvenance': 'Non-blind cross-audit. Prior task context exposed primary aggregate counts and one callerless source ID; no claim of blind review is made.',
        'repositoryOrPrEdits': 0,
    }
    dump_json(PACKET / 'summary.json', summary)

    readme = f'''# slskdN PR #409 W77 cross-audit\n\nRecommendation-only cross-review for ranks 803–827. It reconciles the sealed primary review with the separately sealed candidate-free blind review and independently checks all 300 locale cells against the pinned source and caller contexts.\n\n- Source: `{PINNED_HEAD}` / tree `{PINNED_TREE}`\n- Cross-review mode: non-blind. Earlier task context exposed the primary aggregate counts and one callerless source ID; this packet does not claim blindness.\n- Results: 52 selected updates (50 primary proposals and 2 cross-authored proposals), 236 current translations retained, and 12 callerless hash-only holds. All 20 blind contextual holds receive a specific selected correction; no contextual hold remains unresolved.\n- `cross-ledger.jsonl` records every cell; `selected-proposals.jsonl` and `apply-plan.json` carry exact current/target hashes for the 52 recommendations. The apply plan is hash-guarded and has not been applied.\n- `holds-hash-only.jsonl` contains hashes and metadata only for the 12 callerless cells: no source text, existing translation, or proposed translation.\n- `input-linkage.json` links the candidate-free, primary, and fresh blind bundles by SHA-256. `main-drift-reconciliation.json` records the four-commit base drift, which contains no localization/catalog or product-source changes.\n- Live PR, branch, pull, main, drift, and source-worktree refs are preserved before and after the audit.\n- No product/PR/workflow edits, tests, builds, CI, merge, release, or tag were performed.\n\nRun `python3 verify_cross_packet.py` from this directory to validate input packet checksums, source pins, row linkage, text-free holds, selected proposal hashes, plan scope, and packet checksums.\n'''
    (PACKET / 'README.md').write_text(readme, encoding='utf-8')


if __name__ == '__main__':
    main()
