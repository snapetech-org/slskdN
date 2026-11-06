#!/usr/bin/env python3
"""Build the candidate-free primary semantic review ledger for slskdN W56."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import subprocess

INPUT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w56-ranks301-302-candidate-free-20261103/input')
OUT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w56-primary-review-20261103')
EXPECTED_HEAD = '32afa31caca42b17ac89c9ee91e54ed94cad0411'
EXPECTED_TREE = '0111bd0c279534b972fcbc5f36dd7a32baf86909'
BRANCH = 'codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES = ['ar', 'de', 'es', 'fr', 'hi', 'id', 'ja', 'ko', 'pt-BR', 'vi', 'zh-Hans', 'zh-Hant']

# Only these targets need correction: the current target uses an employment
# occupation/position term where the pinned caller is a system background-job
# category statistic. The other localized terms remain accurate enough in this
# caller context and are left unchanged.
CORRECTIONS = {
    (302, 'fr'): ('Types de tâches', '“Emplois” points toward employment or job positions. The pinned System > Jobs caller counts keys in analytics.byType, so “tâches” identifies system task/job categories.'),
    (302, 'hi'): ('जॉब के प्रकार', '“नौकरी” can suggest an employment position. In the pinned System > Jobs statistic this is a software job category; the common technical loanword avoids that reading.'),
    (302, 'ja'): ('ジョブの種類', '“職種” normally means an occupational category. The pinned caller is a System > Jobs category count, so use the software-job sense.'),
    (302, 'ko'): ('작업 유형', '“직업” means an occupation. The pinned caller counts system jobs by type, so “작업” is the appropriate task/work sense.'),
    (302, 'zh-Hans'): ('作业类型', '“职位” means an employment position. The pinned System > Jobs caller counts software job categories; “作业” expresses the batch/system-job sense.'),
    (302, 'zh-Hant'): ('作業類型', '“職位” means an employment position. The pinned System > Jobs caller counts software job categories; “作業” expresses the batch/system-job sense.'),
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

def verify_live_pin():
    pr = json.loads(subprocess.check_output(
        ['gh', 'pr', 'view', '409', '--repo', 'snapetech-org/slskdN', '--json', 'state,isDraft,headRefName,headRefOid'],
        text=True,
    ))
    assert pr['state'] == 'OPEN' and pr['isDraft'] is True and pr['headRefName'] == BRANCH and pr['headRefOid'] == EXPECTED_HEAD, pr
    remote = subprocess.check_output(
        ['git', 'ls-remote', 'https://github.com/snapetech-org/slskdN.git', f'refs/heads/{BRANCH}'],
        text=True,
    ).strip().split()
    assert len(remote) == 2 and remote[0] == EXPECTED_HEAD, remote
    return {'livePR': pr, 'remoteBranchHead': remote[0], 'head': EXPECTED_HEAD, 'tree': EXPECTED_TREE}

def main():
    assert not (OUT / 'review-ledger.jsonl').exists(), 'review output already exists'
    packet_checks = verify_sums(INPUT / 'PACKET-SHA256SUMS.txt')
    attestation = json.loads((INPUT / 'head-tree-attestation.json').read_text(encoding='utf-8'))
    manifest = json.loads((INPUT / 'manifest.json').read_text(encoding='utf-8'))
    assert attestation['head'] == EXPECTED_HEAD and attestation['tree'] == EXPECTED_TREE
    assert attestation['remoteBranchHead'] == EXPECTED_HEAD
    assert manifest['candidateFree'] is True and manifest['cellCount'] == 24 and manifest['sourceCount'] == 2
    live = verify_live_pin()

    cells = read_jsonl(INPUT / 'source-current-cells.jsonl')
    callers = {row['sourceId']: row for row in read_jsonl(INPUT / 'caller-contexts.jsonl')}
    assert len(cells) == 24
    assert {(row['continuationRank'], row['locale']) for row in cells} == {
        (rank, locale) for rank in (301, 302) for locale in LOCALES
    }
    assert len({row['sourceId'] for row in cells}) == 2

    ledger = []
    counts = Counter()
    for row in cells:
        rank, locale = row['continuationRank'], row['locale']
        source_id, source, current = row['sourceId'], row['source'], row['currentTarget']
        assert row['placeholderEvidence']['matches'] and row['markupEvidence']['matches']
        caller = callers[source_id]
        assert caller['sourceSha256'] == row['sourceSha256']
        assert row['callerContextSha256'] == sha(canonical(caller['callers']))
        assert len(caller['callers']) > 0, f'no pinned production caller for {source_id}'
        caller_refs = [{
            'path': ref['path'], 'line': ref['line'], 'lineSha256': ref['lineSha256'],
            'contextSha256': ref['contextSha256'], 'fileSha256': ref['fileSha256'],
            'gitBlob': ref['gitBlob'],
        } for ref in caller['callers']]

        if rank == 301:
            assert source == '- {warning}'
            assert row['placeholderEvidence']['sourceTokens'] == {'{warning}': 1}
            assert row['placeholderEvidence']['currentTokens'] == {'{warning}': 1}
            decision = 'accept-current'
            candidate = None
            rationale = (
                'The pinned caller emits a Warnings list and passes formatWarning(warning) into this fragment at the {warning} interpolation boundary. '
                'The current value preserves the exact runtime token and renders a bullet prefix. Japanese uses the locale-appropriate middle-dot bullet; '
                'all locales keep {warning} unchanged. Translating or rewriting the dynamic warning value here would be unsupported.'
            )
            confidence = 'high for placeholder and caller semantics; moderate for locale-specific punctuation'
            literal_checks = [{
                'literal': '{warning}', 'kind': 'runtime interpolation token',
                'sourcePresent': True, 'currentPresent': True, 'exactMatch': True,
            }]
        elif (rank, locale) in CORRECTIONS:
            candidate, rationale = CORRECTIONS[(rank, locale)]
            decision = 'correction'
            confidence = 'moderate; caller context distinguishes system-job categories from employment, but no native-speaker review was performed'
            literal_checks = []
        else:
            assert rank == 302 and source == 'Job Types'
            decision = 'accept-current'
            candidate = None
            rationale = (
                'The pinned caller renders this as the label for the count of keys in analytics.byType inside System > Jobs. '
                'The current wording is a reasonable broad rendering of system job categories in this locale; no clearer necessary change is supported by the supplied context.'
            )
            confidence = 'moderate; native-speaker register approval remains outstanding'
            literal_checks = []

        recommended = candidate if candidate is not None else current
        assert decision not in ('correction', 'refinement') or recommended != current
        assert '{warning}' not in recommended or rank == 301
        ledger_row = {
            'repository': 'snapetech-org/slskdN',
            'pullRequest': 409,
            'head': EXPECTED_HEAD,
            'tree': EXPECTED_TREE,
            'window': 'W56',
            'continuationRank': rank,
            'sourceId': source_id,
            'source': source,
            'sourceSha256': row['sourceSha256'],
            'locale': locale,
            'catalogPath': row['catalogPath'],
            'catalogFileSha256': row['catalogFileSha256'],
            'catalogGitBlob': row['catalogGitBlob'],
            'currentTarget': current,
            'currentTargetSha256': row['currentTargetSha256'],
            'decision': decision,
            'candidate': candidate,
            'recommendedTarget': recommended,
            'rationale': rationale,
            'confidence': confidence,
            'callerContextSha256': row['callerContextSha256'],
            'pinnedCallerRefs': caller_refs,
            'placeholderEvidence': row['placeholderEvidence'],
            'markupEvidence': row['markupEvidence'],
            'sourceNumericTokens': row['sourceNumericTokens'],
            'currentNumericTokens': row['currentNumericTokens'],
            'protectedLiteralChecks': literal_checks,
            'nativeSpeakerApproval': False,
        }
        ledger.append(ledger_row)
        counts[decision] += 1

    assert counts == {'accept-current': 18, 'correction': 6}, counts
    assert all(row['decision'] == 'accept-current' for row in ledger if row['continuationRank'] == 301)
    assert all(row['placeholderEvidence']['currentTokens'] == {'{warning}': 1} for row in ledger if row['continuationRank'] == 301)

    write_jsonl(OUT / 'review-ledger.jsonl', ledger)
    summary = {
        'artifact': 'slskdN PR #409 primary semantic localization review W56 ranks 301-302',
        'repository': 'snapetech-org/slskdN',
        'pullRequest': 409,
        'head': EXPECTED_HEAD,
        'tree': EXPECTED_TREE,
        'sourceIds': 2,
        'reviewedCells': len(ledger),
        'locales': LOCALES,
        'decisionCounts': dict(counts),
        'proposalCounts': {'correction': counts['correction'], 'refinement': counts['refinement']},
        'holds': 0,
        'rank301': {
            'decision': 'accept-current-all-locales',
            'sourceId': 'src_1ab57bbe37fe439f',
            'runtimePlaceholder': '{warning}',
            'placeholderPreservedInAllLocales': True,
            'caller': 'src/web/src/lib/searchActionPreview.js:112 passes warning: formatWarning(warning) to interfaceText and appends it beneath Warnings:',
        },
        'rank302': {
            'sourceId': 'src_1ab6aea79b68f3ed',
            'caller': 'src/web/src/components/System/Jobs/index.jsx:332-334 labels the analytics.byType count',
            'corrections': [{'locale': locale, 'candidate': candidate} for (rank, locale), (candidate, _) in CORRECTIONS.items() if rank == 302],
        },
        'inputChecksumFilesVerified': len(packet_checks),
        'livePRAndRemotePinVerified': live,
        'placeholderMarkupNumericChecks': {
            'mismatches': sum(not row['placeholderEvidence']['matches'] or not row['markupEvidence']['matches'] for row in cells),
            'rank301RuntimePlaceholderFailures': 0,
        },
        'nativeSpeakerApproval': False,
        'limitations': 'Machine-assisted semantic review. Confidence is moderate for the six job-term corrections; qualified native-speaker review remains necessary.'
    }
    write_json(OUT / 'summary.json', summary)
    attestation_out = {
        'inputDirectory': str(INPUT),
        'inputChecksumListSha256': sha((INPUT / 'PACKET-SHA256SUMS.txt').read_bytes()),
        'verifiedInputFiles': packet_checks,
        'inputManifestSha256': sha((INPUT / 'manifest.json').read_bytes()),
        'headTreeAttestationSha256': sha((INPUT / 'head-tree-attestation.json').read_bytes()),
        'sourceCurrentCellsSha256': sha((INPUT / 'source-current-cells.jsonl').read_bytes()),
        'callerContextsSha256': sha((INPUT / 'caller-contexts.jsonl').read_bytes()),
        'livePRRemoteVerification': live,
        'primaryReviewUsedCandidateFreePacketOnly': True,
    }
    write_json(OUT / 'input-attestation.json', attestation_out)
    readme = '''# slskdN PR #409 primary semantic review — W56 ranks 301–302

This ledger reviews 24 current catalog cells across twelve locales at PR head `32afa31caca42b17ac89c9ee91e54ed94cad0411`, tree `0111bd0c279534b972fcbc5f36dd7a32baf86909`. The candidate-free packet checksums and live PR/remote head were verified before review.

Rank 301 (`- {warning}`) is a runtime formatting fragment. Its pinned caller adds a `Warnings:` heading and interpolates `formatWarning(warning)` into the exact `{warning}` token. All twelve current targets retain that token; Japanese uses a localized bullet marker. All are accepted unchanged.

Rank 302 (`Job Types`) labels the number of keys in `analytics.byType` in the System > Jobs panel. Six current labels use employment-position wording that is misleading for system-job categories; the ledger proposes corrections for French, Hindi, Japanese, Korean, Simplified Chinese, and Traditional Chinese. The other six remain accepted. No unsupported cells required a hold.

This is machine-assisted semantic review, not native-speaker approval. Confidence in the six job-term corrections is moderate; qualified native-speaker review remains outstanding. No repository, PR, or workflow files were changed, and no tests, builds, scans, CI, browser work, merge, release, or tag were run.
'''
    (OUT / 'README.md').write_text(readme, encoding='utf-8')
    files = sorted(path for path in OUT.iterdir() if path.is_file() and path.name not in ('manifest.json', 'SHA256SUMS.txt'))
    output_manifest = {
        'artifact': 'slskdN PR #409 W56 primary semantic review',
        'sealed': True,
        'repository': 'snapetech-org/slskdN',
        'pullRequest': 409,
        'head': EXPECTED_HEAD,
        'tree': EXPECTED_TREE,
        'rowCount': len(ledger),
        'decisionCounts': dict(counts),
        'files': [{'name': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())} for path in files],
    }
    write_json(OUT / 'manifest.json', output_manifest)
    files = sorted(path for path in OUT.iterdir() if path.is_file() and path.name not in ('manifest.json', 'SHA256SUMS.txt'))
    (OUT / 'SHA256SUMS.txt').write_text(''.join(f'{sha(path.read_bytes())}  {path.name}\n' for path in files), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
