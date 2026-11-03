#!/usr/bin/env python3
"""Third-party cross-audit for slskdN PR #409 W56, ranks 301–302."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import subprocess

ROOT = Path('/mnt/disks/scratch/task-scratch')
INPUT = ROOT / 'slskdn-pr409-w56-ranks301-302-candidate-free-20261103/input'
PRIMARY_DIR = ROOT / 'slskdn-pr409-w56-primary-review-20261103'
PRIMARY_LEDGER = PRIMARY_DIR / 'review-ledger.jsonl'
BLIND_DIR = ROOT / 'slskdn-pr409-w56-independent-blind-20261103'
BLIND_LEDGER = BLIND_DIR / 'blind-decisions.jsonl'
OUT = ROOT / 'slskdn-pr409-w56-third-party-cross-audit-20261103'
HEAD = '32afa31caca42b17ac89c9ee91e54ed94cad0411'
TREE = '0111bd0c279534b972fcbc5f36dd7a32baf86909'
BRANCH = 'codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES = ['ar', 'de', 'es', 'fr', 'hi', 'id', 'ja', 'ko', 'pt-BR', 'vi', 'zh-Hans', 'zh-Hant']
PH = re.compile(r'\{[^{}]+\}')
MARKUP = re.compile(r'</?[A-Za-z][^>]*>')
NUMBER = re.compile(r'(?<![A-Za-z])\d+(?:[.,]\d+)?%?(?![A-Za-z])')

FINAL_RANK302 = {
    'ar': {'decision': 'refinement', 'target': 'أنواع المهام', 'basis': 'Blind suggestion adopted: the pinned caller identifies system-job categories, and المهام makes task/function wording clearer than the broad current الوظائف without changing its understood scope.'},
    'de': {'decision': 'accept-current', 'target': 'Jobtypen', 'basis': 'Primary and blind reviews agree. The technical compound clearly labels system job categories in this caller.'},
    'es': {'decision': 'refinement', 'target': 'Tipos de tareas', 'basis': 'Blind suggestion adopted: tareas is clearer for system task categories than the broader trabajo; the current wording remains understandable in context.'},
    'fr': {'decision': 'correction', 'target': 'Types de tâches', 'basis': 'Primary and blind reviews agree. emplois suggests employment or job positions, while the pinned caller is a System > Jobs category statistic.'},
    'hi': {'decision': 'correction', 'target': 'कार्य के प्रकार', 'basis': 'Blind candidate selected over the primary loanword alternative जॉब के प्रकार: कार्य directly describes system work/task categories and avoids retaining the employment ambiguity of नौकरी.'},
    'id': {'decision': 'refinement', 'target': 'Jenis Tugas', 'basis': 'Blind suggestion adopted with capitalization aligned to the current title-style label. Tugas makes the system task-category sense clearer than the broad pekerjaan.'},
    'ja': {'decision': 'correction', 'target': 'ジョブの種類', 'basis': 'Primary and blind reviews agree. 職種 normally means occupational category; the pinned caller counts system job types.'},
    'ko': {'decision': 'correction', 'target': '작업 유형', 'basis': 'Primary and blind reviews agree. 직업 유형 reads as an occupation; 작업 유형 labels system task/job categories.'},
    'pt-BR': {'decision': 'refinement', 'target': 'Tipos de tarefas', 'basis': 'Blind suggestion adopted: tarefas describes system task categories more directly than trabalho, which can suggest kinds of employment/work.'},
    'vi': {'decision': 'refinement', 'target': 'Loại tác vụ', 'basis': 'Blind suggestion adopted: tác vụ makes the technical system-task sense explicit; công việc is broader.'},
    'zh-Hans': {'decision': 'correction', 'target': '任务类型', 'basis': 'Blind candidate selected over the primary 作业类型 alternative. 任务类型 is the more general system-task category label supported by this caller; no evidence limits these jobs to batch 作业.'},
    'zh-Hant': {'decision': 'correction', 'target': '任務類型', 'basis': 'Blind candidate selected over the primary 作業類型 alternative. 任務類型 is the more general system-task category label supported by this caller; no evidence limits these jobs to batch 作業.'},
}

def sha(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def write_jsonl(path, rows):
    path.write_text(''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n' for row in rows), encoding='utf-8')

def verify_sums(path):
    results = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        expected, rel = line.split(None, 1)
        rel = rel.strip().lstrip('*')
        actual = sha((path.parent / rel).read_bytes())
        results.append({'path': rel, 'expected': expected, 'actual': actual, 'matches': expected == actual})
    assert results and all(row['matches'] for row in results), results
    return results

def verify_live():
    pr = json.loads(subprocess.check_output(
        ['gh', 'pr', 'view', '409', '--repo', 'snapetech-org/slskdN', '--json', 'state,isDraft,headRefName,headRefOid,baseRefName'],
        text=True,
    ))
    assert pr['state'] == 'OPEN' and pr['isDraft'] is True and pr['headRefName'] == BRANCH and pr['headRefOid'] == HEAD
    assert pr['baseRefName'] == 'main'
    remote = subprocess.check_output(
        ['git', 'ls-remote', 'https://github.com/snapetech-org/slskdN.git', f'refs/heads/{BRANCH}'],
        text=True,
    ).strip().split()
    assert len(remote) == 2 and remote[0] == HEAD, remote
    return {'pr': pr, 'remoteBranchHead': remote[0], 'head': HEAD, 'tree': TREE}

def caller_pin_projection(ref):
    return {
        'path': ref['path'], 'line': ref['line'], 'lineSha256': ref['lineSha256'],
        'contextSha256': ref['contextSha256'], 'fileSha256': ref['fileSha256'], 'gitBlob': ref['gitBlob'],
    }

def main():
    assert not (OUT / 'cross-audit-ledger.jsonl').exists(), 'audit output already exists'
    input_checks = verify_sums(INPUT / 'PACKET-SHA256SUMS.txt')
    primary_checks = verify_sums(PRIMARY_DIR / 'SHA256SUMS.txt')
    blind_checks = verify_sums(BLIND_DIR / 'SHA256SUMS.txt')
    blind_input_checks = verify_sums(BLIND_DIR / 'input/PACKET-SHA256SUMS.txt')
    input_manifest = json.loads((INPUT / 'manifest.json').read_text(encoding='utf-8'))
    primary_manifest = json.loads((PRIMARY_DIR / 'manifest.json').read_text(encoding='utf-8'))
    blind_summary = json.loads((BLIND_DIR / 'summary.json').read_text(encoding='utf-8'))
    assert input_manifest['candidateFree'] is True and input_manifest['head'] == HEAD and input_manifest['tree'] == TREE
    assert primary_manifest['head'] == HEAD and primary_manifest['tree'] == TREE and primary_manifest['rowCount'] == 24
    assert blind_summary['head'] == HEAD and blind_summary['tree'] == TREE and blind_summary['reviewedCells'] == 24

    # The blind review's sealed input must be byte-identical to the canonical packet.
    packet_names = [line.split(None, 1)[1].strip().lstrip('*') for line in (INPUT / 'PACKET-SHA256SUMS.txt').read_text().splitlines() if line.strip()]
    blind_input = BLIND_DIR / 'input'
    assert (INPUT / 'PACKET-SHA256SUMS.txt').read_bytes() == (blind_input / 'PACKET-SHA256SUMS.txt').read_bytes()
    input_copy_deltas = []
    for name in packet_names:
        left, right = (INPUT / name).read_bytes(), (blind_input / name).read_bytes()
        if left != right:
            input_copy_deltas.append(name)
    assert not input_copy_deltas, input_copy_deltas

    live = verify_live()
    attestation = json.loads((INPUT / 'head-tree-attestation.json').read_text(encoding='utf-8'))
    assert attestation['head'] == HEAD and attestation['tree'] == TREE and attestation['remoteBranchHead'] == HEAD

    input_rows = read_jsonl(INPUT / 'source-current-cells.jsonl')
    caller_rows = {row['sourceId']: row for row in read_jsonl(INPUT / 'caller-contexts.jsonl')}
    primary_rows = read_jsonl(PRIMARY_LEDGER)
    blind_rows = read_jsonl(BLIND_LEDGER)
    assert len(input_rows) == len(primary_rows) == len(blind_rows) == 24
    keys = {(row['sourceId'], row['locale']) for row in input_rows}
    assert len(keys) == 24
    pmap = {(row['sourceId'], row['locale']): row for row in primary_rows}
    bmap = {(row['sourceId'], row['locale']): row for row in blind_rows}
    assert set(pmap) == set(bmap) == keys

    audit_rows = []
    disagreement_rows = []
    counts = Counter()
    primary_counts = Counter()
    blind_counts = Counter()
    for item in input_rows:
        key = (item['sourceId'], item['locale'])
        p, b = pmap[key], bmap[key]
        rank, locale = item['continuationRank'], item['locale']
        assert p['continuationRank'] == rank and b['continuationRank'] == rank
        assert p['head'] == HEAD and p['tree'] == TREE
        assert blind_summary['head'] == HEAD and blind_summary['tree'] == TREE
        assert p['sourceId'] == b['sourceId'] == item['sourceId'] and p['sourceSha256'] == b['sourceSha256'] == item['sourceSha256']
        assert p['currentTarget'] == b['currentTarget'] == item['currentTarget']
        assert p['currentTargetSha256'] == b['currentTargetSha256'] == item['currentTargetSha256']
        assert p['catalogPath'] == b['catalogPath'] == item['catalogPath']
        assert p['catalogFileSha256'] == b['catalogFileSha256'] == item['catalogFileSha256']
        assert p['catalogGitBlob'] == b['catalogGitBlob'] == item['catalogGitBlob']

        caller = caller_rows[item['sourceId']]
        assert caller['sourceSha256'] == item['sourceSha256']
        assert item['callerContextSha256'] == p['callerContextSha256']
        expected_refs = [caller_pin_projection(ref) for ref in caller['callers']]
        assert p['pinnedCallerRefs'] == expected_refs
        blind_refs = [caller_pin_projection(ref) for ref in b['callerContext']['references']]
        assert blind_refs == expected_refs
        assert b['callerContext']['callerReferenceCount'] == len(expected_refs)

        primary_counts[p['decision']] += 1
        blind_counts[b['decision']] += 1
        primary_target = p['recommendedTarget']
        blind_target = b['selectedTarget']
        assert b.get('candidateTarget') in (None, blind_target)
        if b['decision'] == 'accept-current':
            assert blind_target == item['currentTarget'] and b.get('candidateTarget') is None
        else:
            assert b['candidateTarget'] == blind_target

        if rank == 301:
            assert item['source'] == '- {warning}'
            assert item['placeholderEvidence']['sourceTokens'] == {'{warning}': 1}
            assert item['placeholderEvidence']['matches'] is True
            assert primary_target == blind_target == item['currentTarget']
            assert primary_target.count('{warning}') == 1
            final_decision, final_target = 'accept-current', item['currentTarget']
            rationale = ('Both reviews agree and the pinned caller confirms this is a list-marker fragment with the runtime warning passed at {warning}. '
                         'Keep the exact token unchanged in every locale. The Japanese middle-dot bullet is an equivalent localized list marker.')
            resolution = 'consensus-accept-current'
            winner = 'primary-and-blind-consensus'
            protected = {'token': '{warning}', 'expectedCount': 1, 'sourceCount': 1, 'currentCount': 1, 'primaryCount': 1, 'blindCount': 1, 'finalCount': 1, 'allChecksPass': True}
        else:
            assert rank == 302 and item['source'] == 'Job Types'
            spec = FINAL_RANK302[locale]
            final_decision, final_target = spec['decision'], spec['target']
            rationale = spec['basis']
            if primary_target == blind_target:
                resolution, winner = 'consensus', 'primary-and-blind-consensus'
            elif final_target == blind_target:
                resolution, winner = 'cross-review-winner', 'independent-blind'
            elif final_target == primary_target:
                resolution, winner = 'cross-review-winner', 'primary'
            else:
                resolution, winner = 'cross-audit-adjudication', 'third-party-cross-audit'
            protected = {'token': None, 'expectedCount': 0, 'sourceCount': 0, 'currentCount': 0, 'primaryCount': 0, 'blindCount': 0, 'finalCount': 0, 'allChecksPass': True}
            assert not PH.findall(final_target)

        assert item['placeholderEvidence']['matches'] and item['markupEvidence']['matches']
        assert Counter(PH.findall(final_target)) == Counter(PH.findall(item['source']))
        assert Counter(MARKUP.findall(final_target)) == Counter(MARKUP.findall(item['source']))
        assert NUMBER.findall(final_target) == NUMBER.findall(item['source'])
        assert final_decision == 'accept-current' or final_target != item['currentTarget']
        counts[final_decision] += 1

        audit = {
            'repository': 'snapetech-org/slskdN', 'pullRequest': 409, 'head': HEAD, 'tree': TREE,
            'window': 'W56', 'continuationRank': rank, 'sourceId': item['sourceId'], 'source': item['source'],
            'sourceSha256': item['sourceSha256'], 'locale': locale,
            'catalogPath': item['catalogPath'], 'catalogFileSha256': item['catalogFileSha256'],
            'catalogGitBlob': item['catalogGitBlob'], 'currentTarget': item['currentTarget'],
            'currentTargetSha256': item['currentTargetSha256'],
            'callerContextSha256': item['callerContextSha256'], 'pinnedCallerRefs': expected_refs,
            'primaryDecision': p['decision'], 'primaryTarget': primary_target,
            'blindDecision': b['decision'], 'blindTarget': blind_target,
            'crossAuditDecision': final_decision, 'crossAuditTarget': final_target,
            'resolution': resolution, 'winner': winner, 'rationale': rationale,
            'placeholderEvidence': item['placeholderEvidence'], 'markupEvidence': item['markupEvidence'],
            'sourceNumericTokens': item['sourceNumericTokens'], 'currentNumericTokens': item['currentNumericTokens'],
            'protectedWarningToken': protected,
            'inputMatchesPrimaryAndBlind': True,
        }
        audit_rows.append(audit)
        if p['decision'] != b['decision'] or primary_target != blind_target:
            disagreement_rows.append({
                'continuationRank': rank, 'sourceId': item['sourceId'], 'locale': locale,
                'currentTarget': item['currentTarget'], 'primaryDecision': p['decision'], 'primaryTarget': primary_target,
                'blindDecision': b['decision'], 'blindTarget': blind_target,
                'crossAuditDecision': final_decision, 'crossAuditTarget': final_target,
                'resolution': resolution, 'winner': winner, 'rationale': rationale,
            })

    assert counts == {'accept-current': 13, 'correction': 6, 'refinement': 5}, counts
    assert len(disagreement_rows) == 8
    assert len([row for row in audit_rows if row['continuationRank'] == 301]) == 12
    assert all(row['crossAuditTarget'].count('{warning}') == 1 for row in audit_rows if row['continuationRank'] == 301)

    write_jsonl(OUT / 'cross-audit-ledger.jsonl', audit_rows)
    write_jsonl(OUT / 'disagreements.jsonl', disagreement_rows)
    input_verification = {
        'head': HEAD, 'tree': TREE, 'livePRRemote': live,
        'candidateFreePacketChecks': input_checks,
        'primaryPacketChecks': primary_checks,
        'blindPacketChecks': blind_checks,
        'blindCandidateFreeInputChecks': blind_input_checks,
        'blindInputIsByteIdenticalToCanonicalPacket': True,
        'canonicalInputManifestSha256': sha((INPUT / 'manifest.json').read_bytes()),
        'primaryManifestSha256': sha((PRIMARY_DIR / 'manifest.json').read_bytes()),
        'blindSummarySha256': sha((BLIND_DIR / 'summary.json').read_bytes()),
        'candidateFreeRows': len(input_rows), 'primaryRows': len(primary_rows), 'blindRows': len(blind_rows),
        'cellPinsMatchAcrossAllThreePackets': True,
        'callerPinsMatchAcrossAllThreePackets': True,
    }
    write_json(OUT / 'input-verification.json', input_verification)
    summary = {
        'artifact': 'slskdN PR #409 third-party cross-audit W56 ranks 301-302',
        'repository': 'snapetech-org/slskdN', 'pullRequest': 409,
        'head': HEAD, 'tree': TREE, 'sourceCount': 2, 'reviewedCells': 24, 'localeCount': 12,
        'primaryDecisionCounts': dict(primary_counts), 'blindDecisionCounts': dict(blind_counts),
        'crossAuditDecisionCounts': dict(counts), 'crossAuditProposalCounts': {'correction': counts['correction'], 'refinement': counts['refinement']},
        'primaryBlindDisagreements': len(disagreement_rows), 'resolvedDisagreements': len(disagreement_rows), 'unresolvedDisagreements': 0,
        'rank301': {'decision': 'accept-current all locales', 'exactRuntimePlaceholder': '{warning}', 'placeholderFailures': 0,
                    'caller': 'src/web/src/lib/searchActionPreview.js:112 interpolates formatWarning(warning) into the list-marker fragment'},
        'rank302': {'decisionCounts': dict(Counter(row['crossAuditDecision'] for row in audit_rows if row['continuationRank'] == 302)),
                    'caller': 'src/web/src/components/System/Jobs/index.jsx:332-334 labels the count of analytics.byType keys',
                    'finalTargets': {row['locale']: row['crossAuditTarget'] for row in audit_rows if row['continuationRank'] == 302}},
        'allPacketChecksumsVerified': True,
        'placeholderMarkupNumericFailures': 0,
        'nativeSpeakerApproval': False,
        'limitations': 'Machine-assisted cross-audit. Language-specific target choices, especially Hindi and Chinese terminology, remain subject to qualified native-speaker review.',
        'repositoryOrPREdited': False,
        'testsBuildsScansCIWorkflowsBrowserMergeReleaseOrTagPerformed': False,
    }
    write_json(OUT / 'summary.json', summary)
    readme = '''# slskdN PR #409 third-party cross-audit — W56 ranks 301–302

The candidate-free packet, primary ledger, blind packet, and blind packet’s copied input all passed their checksum manifests. The blind copy is byte-identical to the canonical candidate-free packet. Live PR #409 and its remote branch still match head `32afa31caca42b17ac89c9ee91e54ed94cad0411`, tree `0111bd0c279534b972fcbc5f36dd7a32baf86909`.

The audit reconciles all 24 cells. Rank 301 is accepted in all twelve locales; the runtime `{warning}` token remains exact. Rank 302 retains German `Jobtypen`; it adopts the blind proposals for Arabic, Spanish, French, Hindi, Indonesian, Japanese, Korean, Brazilian Portuguese, Vietnamese, and both Chinese variants. French, Hindi, Japanese, Korean, and Chinese are corrections; Arabic, Spanish, Indonesian, Brazilian Portuguese, and Vietnamese are refinements. The Hindi candidate resolves the primary/blind wording split as `कार्य के प्रकार`. The Chinese candidates use `任务类型` and `任務類型` rather than the primary’s narrower `作业类型`/`作業類型`.

All eight primary/blind disagreements are resolved in the ledger; none remain unresolved. Placeholder, markup, and numeric checks pass. This is machine-assisted review, not native-speaker approval. No repository or PR changes, tests, builds, scans, CI, workflows, browser work, merge, release, or tag were performed.
'''
    (OUT / 'README.md').write_text(readme, encoding='utf-8')
    files = sorted(path for path in OUT.iterdir() if path.is_file() and path.name not in ('manifest.json', 'SHA256SUMS.txt'))
    manifest = {
        'artifact': 'slskdN PR #409 W56 third-party cross-audit', 'sealed': True,
        'repository': 'snapetech-org/slskdN', 'pullRequest': 409, 'head': HEAD, 'tree': TREE,
        'rowCount': len(audit_rows), 'disagreementCount': len(disagreement_rows),
        'decisionCounts': dict(counts),
        'files': [{'name': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())} for path in files],
    }
    write_json(OUT / 'manifest.json', manifest)
    files = sorted(path for path in OUT.iterdir() if path.is_file() and path.name not in ('manifest.json', 'SHA256SUMS.txt'))
    (OUT / 'SHA256SUMS.txt').write_text(''.join(f'{sha(path.read_bytes())}  {path.name}\n' for path in files), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
