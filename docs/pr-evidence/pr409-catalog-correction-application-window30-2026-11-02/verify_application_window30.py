#!/usr/bin/env python3
import collections
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path('/mnt/disks/scratch/task-worktrees/localization-20261030/slskdn-pr409-batch4-docs-20261101')
BASE = Path('/mnt/disks/scratch/task-worktrees/localization-20261030')
MANUAL = REPO / 'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01'
APP0 = REPO / 'docs/pr-evidence/pr409-catalog-correction-application-2026-11-01'
APP18 = REPO / 'docs/pr-evidence/pr409-catalog-correction-application-windows18-19-2026-11-02'
APP20 = REPO / 'docs/pr-evidence/pr409-catalog-correction-application-windows20-21-2026-11-02'
APP22 = REPO / 'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02'
APP24 = REPO / 'docs/pr-evidence/pr409-catalog-correction-application-window24-2026-11-02'
APP25 = REPO / 'docs/pr-evidence/pr409-catalog-correction-application-window25-2026-11-02'
APP26 = REPO / 'docs/pr-evidence/pr409-catalog-correction-application-window26-2026-11-02'
APP27 = REPO / 'docs/pr-evidence/pr409-catalog-correction-application-window27-2026-11-02'
APP28 = REPO / 'docs/pr-evidence/pr409-catalog-correction-application-window28-2026-11-02'
APP29 = REPO / 'docs/pr-evidence/pr409-catalog-correction-application-window29-2026-11-02'
APP30_DIR = REPO / 'docs/pr-evidence/pr409-catalog-correction-application-window30-2026-11-02'
BUNDLE = BASE / 'slskdn-populated-review-4c2b-20261101' / 'bundle'
RESULTS = BASE / 'semantic-review-results/slskdn-4c2b2e47-v1-912fadf3fce5'
BASELINE = '4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb'
REVIEW30 = 'f11dc7199b662a49c5e84794730043af29d6830b'
APP30_COMMIT = '0188e7f2b3ca5d57fd91409159a42495cbbac763'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
APP_PATHS = {'src/web/public/locales/' + locale + '.json' for locale in LOCALES} | {'docs/CHANGELOG.md'}

def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode('utf-8')).hexdigest()

def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args], text=True).strip()

def show(commit, path):
    return subprocess.check_output(['git', '-C', str(REPO), 'show', f'{commit}:{path}'])

def unique_json(raw, label):
    def hook(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError(f'duplicate JSON key {key!r} in {label}')
            out[key] = value
        return out
    return json.loads(raw.decode('utf-8'), object_pairs_hook=hook)

def fail(message):
    raise SystemExit('FAIL: ' + message)

def applied_target(row):
    for key in ('appliedTarget','newTarget','rootTarget','proposedTarget','crossReviewedTarget','applied_target'):
        if key in row:
            return row[key]
    fail(f'no target field for applied ledger row {row.get("id")}')

def main():
    head, tree = git('rev-parse','HEAD'), git('rev-parse','HEAD^{tree}')
    remote = subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin','refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'],text=True).split()[0]
    state = json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,mergeStateStatus,headRefOid'],text=True))
    if head != APP30_COMMIT or remote != head or state.get('headRefOid') != head or state.get('state') != 'OPEN' or state.get('isDraft') is not True:
        fail(f'PR/local/remote exact-head mismatch: head={head} remote={remote} pr={state}')
    if git('rev-parse',APP30_COMMIT+'^') != REVIEW30:
        fail('window30 application commit is not a direct child of its review base')
    if git('rev-parse',APP30_COMMIT+'^{tree}') != '0909e7e881d99f9e181ae6ed34034e45d9eada7d':
        fail('window30 application tree pin mismatch')
    app_paths = set(git('diff-tree','--no-commit-id','--name-only','-r',APP30_COMMIT).splitlines())
    if app_paths != APP_PATHS:
        fail(f'window30 commit path scope mismatch: {sorted(app_paths ^ APP_PATHS)}')
    if git('rev-parse',REVIEW30+':.github/workflows') != git('rev-parse',APP30_COMMIT+':.github/workflows'):
        fail('workflow subtree changed in window30 app commit')
    if git('rev-parse',REVIEW30+':src/web/src') != git('rev-parse',APP30_COMMIT+':src/web/src'):
        fail('source code tree changed in window30 app commit')

    manual_ids = set()
    manual_keys = set()
    manual_by_id = {}
    manual_verdicts = collections.Counter()
    formal_rows = 4800
    for window in range(1,31):
        directory = MANUAL / f'window{window}'
        inputs = rows(directory/'review-input.jsonl')
        decisions = rows(directory/'review-decisions.jsonl')
        by_decision = {row['id']:row for row in decisions}
        expected_cells = 264 if window == 30 else 300
        if len(inputs) != expected_cells or len(decisions) != expected_cells or len(by_decision) != expected_cells:
            fail(f'window {window} input/decision cell count mismatch')
        if {row['id'] for row in inputs} != set(by_decision):
            fail(f'window {window} input/decision IDs differ')
        if window == 30:
            manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
            if (manifest['headCommit'],manifest['tree'],manifest['sourceSubtreeTree']) != (REVIEW30,'14fc14f856f6335c17d87e78e33963ad1c219735','f55419446a34ba4c6cd666aedd1b192d004e88c3'):
                fail('window30 review pin mismatch')
            if sha((directory/'review-input.jsonl').read_bytes()) != 'cdddce2d0a1eb4b24ac1dced73273ecedb23ef7ff7cc1feb6c426df35a8e8311':
                fail('window30 input hash mismatch')
            if sha((directory/'review-decisions.jsonl').read_bytes()) != '5b47f3a50bfd3206ee3847eebf5890d89f3c0e793124a20840837d4508c6bdb1':
                fail('window30 decision hash mismatch')
            if sha((directory/'crossreview-plan.jsonl').read_bytes()) != 'a4754dbb630a91f612013e11feba2d2d27f38587eb17411ebeafde9a32eaee66':
                fail('window30 proposal hash mismatch')
        for row in inputs:
            ident = row['id']
            decision = by_decision[ident]
            if ident in manual_ids:
                fail(f'manual window overlap: {ident}')
            if ident != f'{row["locale"]}:{row["sourceId"]}' or row['locale'] not in LOCALES:
                fail(f'malformed manual row ID: {ident}')
            if sha(row['source']) != row['sourceSha256'] or sha(row['target']) != row['targetSha256']:
                fail(f'manual source/target hash mismatch: {ident}')
            if decision['verdict'] not in {'keep','correct','uncertain'}:
                fail(f'unknown manual verdict: {ident}')
            if decision['verdict'] == 'correct' and (not decision.get('target') or re.findall(r'\{[^{}]+\}',decision['target']) != re.findall(r'\{[^{}]+\}',row['source'])):
                fail(f'manual correction placeholder mismatch: {ident}')
            manual_ids.add(ident)
            manual_keys.add(row['sourceId'])
            manual_by_id[ident] = (row,decision)
            manual_verdicts[decision['verdict']] += 1
    if len(manual_ids) != 8964 or len(manual_keys) != 747:
        fail('30-window cumulative coverage mismatch')
    if manual_verdicts != collections.Counter({'keep':7468,'correct':1228,'uncertain':268}):
        fail(f'manual verdict totals mismatch: {dict(manual_verdicts)}')

    applied_groups = [
        rows(APP0/'applied-corrections.jsonl'),
        rows(APP18/'applied-corrections.jsonl'),
        rows(APP20/'applied-corrections.jsonl'),
        rows(APP22/'applied-corrections-windows22-23.jsonl'),
        rows(APP22/'applied-corrections-realm-window20.jsonl'),
        rows(APP24/'applied-corrections-window24.jsonl'),
        rows(APP25/'applied-corrections-window25.jsonl'),
        rows(APP26/'applied-corrections-window26.jsonl'),
        rows(APP27/'applied-corrections-window27.jsonl'),
        rows(APP28/'applied-corrections-window28.jsonl'),
        rows(APP29/'applied-corrections-window29.jsonl'),
        rows(APP30_DIR/'applied-corrections-window30.jsonl'),
    ]
    held = rows(APP0/'held-no-context.jsonl')
    expected_group_sizes = [736,82,51,53,12,45,43,48,44,39,42,39]
    if [len(group) for group in applied_groups] != expected_group_sizes or len(held) != 6:
        fail('application/hold ledger row counts mismatch')
    applied = [row for group in applied_groups for row in group]
    applied_by = {row['id']:row for row in applied}
    held_by = {row['id']:row for row in held}
    if len(applied_by) != 1234 or len(held_by) != 6:
        fail('application/hold IDs are not unique')
    all_sets = [{row['id'] for row in group} for group in applied_groups+[held]]
    if any(all_sets[i] & all_sets[j] for i in range(len(all_sets)) for j in range(i+1,len(all_sets))):
        fail('application/hold ledgers overlap')
    if len({row['sourceId'] for row in applied}) != 284:
        fail('applied correction source-key count mismatch')
    realm_ids = {row['id'] for row in applied_groups[4]}
    manual_correct = {ident for ident,(row,decision) in manual_by_id.items() if decision['verdict']=='correct'}
    manual_uncertain = {ident for ident,(row,decision) in manual_by_id.items() if decision['verdict']=='uncertain'}
    if set(applied_by) | set(held_by) != manual_correct | realm_ids:
        fail('manual corrections plus Realm cross-review do not reconcile to application/hold ledgers')
    if len(manual_uncertain - realm_ids) != 256:
        fail('remaining uncertain-cell count mismatch')

    final_locale_counts = collections.Counter(row['locale'] for row in applied)
    if sum(final_locale_counts.values()) != 1234:
        fail('applied row total mismatch')
    for locale in LOCALES:
        rel = f'src/web/public/locales/{locale}.json'
        baseline = unique_json(show(BASELINE,rel),f'{BASELINE}:{rel}')
        final_raw = show(APP30_COMMIT,rel)
        final = unique_json(final_raw,f'{APP30_COMMIT}:{rel}')
        if len(baseline) != 6169 or len(final) != 6169 or set(baseline) != set(final):
            fail(f'catalog key shape mismatch: {locale}')
        if any(not isinstance(value,str) or not value for value in final.values()):
            fail(f'empty/non-string catalog value: {locale}')
        for key,value in final.items():
            if collections.Counter(re.findall(r'\{[^{}]+\}',key)) != collections.Counter(re.findall(r'\{[^{}]+\}',value)):
                fail(f'full catalog placeholder mismatch: {locale}:{key}')
        changed = {key for key in baseline if baseline[key] != final[key]}
        expected_changed = {row['catalogKey'] for row in applied if row['locale']==locale}
        if changed != expected_changed:
            fail(f'final catalog changed-key/apply-ledger mismatch: {locale}')
        for row in applied:
            if row['locale']==locale and final.get(row['catalogKey']) != applied_target(row):
                fail(f'final catalog value does not match applied ledger: {row["id"]}')
        if sha(final_raw) != json.loads((APP30_DIR/'apply-audit-window30.json').read_text())['newCatalogFileSha256'][locale]:
            fail(f'window30 final catalog hash mismatch: {locale}')

    sys.path.insert(0,str(BASE/'translation-tools'))
    import strict_populated_semantic_review_runner_core as core
    bundle_manifest = json.loads((BUNDLE/'manifest.json').read_text(encoding='utf-8'))
    bundle = core.load_bundle(
        BUNDLE, sha((BUNDLE/'manifest.json').read_bytes()), sha((BUNDLE/'batches.json').read_bytes()),
        bundle_manifest['headCommit'], bundle_manifest['tree'], 'snapetech-org/slskdN', 'slskdn',
        BASE/'slskdn-populated-review-4c2b-20261101'/'snapshot-repo',
    )
    scan = core.scan_results(bundle, RESULTS)
    formal = {decision['id'] for result in scan['valid'].values() for decision in result['decisions']}
    if scan['invalid'] or len(scan['valid']) != 150 or len(scan['missing']) != 1951 or len(formal) != formal_rows:
        fail('formal accumulator shape/count mismatch')
    if formal & manual_ids or formal & set(applied_by) or formal & set(held_by):
        fail('formal/manual/application overlap')
    if '1,234 exact-hash-validated populated-catalog corrections across 284 source keys' not in show(APP30_COMMIT,'docs/CHANGELOG.md').decode('utf-8'):
        fail('cumulative changelog mismatch')

    output = {
        'result':'PASS',
        'pullRequest':409,
        'livePrState':state['state'],
        'livePrDraft':state['isDraft'],
        'mergeStateStatus':state.get('mergeStateStatus'),
        'pushState':'pushed-and-current',
        'applicationCommit':APP30_COMMIT,
        'applicationTree':git('rev-parse',APP30_COMMIT+'^{tree}'),
        'currentHead':head,
        'currentTree':tree,
        'currentRemoteHead':remote,
        'manualCoverage':{'windows':30,'sourceKeys':747,'cells':8964,'verdicts':dict(manual_verdicts),'formalOverlap':0,'manualWindowOverlap':0},
        'window30RootReview':{'rows':39,'acceptedAsProposed':37,'refinedAndAccepted':2,'held':0,'candidatePlanSha256':'a4754dbb630a91f612013e11feba2d2d27f38587eb17411ebeafde9a32eaee66','ledgerSha256':'6a1d408e2c2d513d0b9dfd3ccd7708f00331d3bb36c67093791667a747510c12','applyPlanSha256':'c38e7b567bab2a38f4897c2ba7364bd475ac6f8d03c78f8612f807cfb7d3b155'},
        'application':{'previousApplied':1195,'newApplied':39,'totalApplied':1234,'uniqueSourceKeys':284,'heldNoContext':6,'uncertainOriginally':268,'uncertainResolvedByRealm':12,'uncertainRemaining':256,'unreviewedCells':58116,'byLocale':dict(sorted(final_locale_counts.items())),'window30ByLocale':dict(sorted(collections.Counter(row['locale'] for row in applied_groups[-1]).items()))},
        'catalogCensus':{'locales':12,'keysPerLocale':6169,'totalValues':74028,'changedCellsSinceFrozenBaseline':1234,'placeholderChecks':74028,'catalogFileSha256':{locale:sha(show(APP30_COMMIT,f'src/web/public/locales/{locale}.json')) for locale in LOCALES}},
        'formalAccumulator':{'validJobs':150,'missingJobs':1951,'invalidJobs':0,'cells':4800},
        'workflowChanges':0,'window30ChangedPaths':sorted(app_paths),'nativeSpeakerReview':'outstanding','headedBrowserReview':'outstanding','testsBuildCiReleaseOrTag':'not run',
    }
    output_path = BASE/'slskdn-manual-review-window30-f11dc719-20261102'/'cumulative-verification-window30.json'
    output_path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(output,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
