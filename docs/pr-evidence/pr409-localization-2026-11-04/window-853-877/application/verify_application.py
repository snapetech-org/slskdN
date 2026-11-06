#!/usr/bin/env python3
"""Verify W79 product commit, exact 300-cell readback, and portable evidence."""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import subprocess
from pathlib import Path

HEAD = '4d67527be0ca3b75e866f25bef5e58ae7f777f7f'
TREE = '99ba5d8f7d631de3337e6b02f74af6d14e46c2ff'
BRANCH = 'codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
RANKS = set(range(853,878))
CALLERLESS = {865,868}
TEXT_FIELDS = {'source','sourceText','currentTarget','currentTargetText','target','crossTarget',
               'proposedTarget','readbackTarget','catalogKey'}


def fail(message: str) -> None:
    raise SystemExit('FAIL: ' + message)


def need(ok: bool, message: str) -> None:
    if not ok:
        fail(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text_sha(value: str) -> str:
    return sha(value.encode('utf-8'))


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def canon(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def loadj(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def check_inventory(root: Path, manifest_name='manifest.json', sums_name='SHA256SUMS.txt'):
    manifest = loadj(root / manifest_name)
    entries = manifest['files']
    expected = {entry['path'] for entry in entries}
    need(len(expected) == len(entries), f'duplicate inventory path in {root}')
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()
              and p.relative_to(root).as_posix() not in {manifest_name, sums_name}}
    need(actual == expected, f'file inventory mismatch in {root}')
    for entry in entries:
        path = (root / entry['path']).resolve()
        need(path.is_relative_to(root.resolve()) and path.is_file(), 'missing/unsafe file ' + entry['path'])
        data = path.read_bytes()
        need(len(data) == entry['bytes'] and sha(data) == entry['sha256'], 'inventory hash ' + entry['path'])
    sums = {}
    for line in (root / sums_name).read_text(encoding='utf-8').splitlines():
        if line.strip():
            digest, name = line.split('  ', 1)
            need(name not in sums, 'duplicate checksum entry')
            sums[name] = digest
    need(set(sums) == expected | {manifest_name}, f'checksum inventory mismatch in {root}')
    for name, digest in sums.items():
        path = root / name
        need(path.is_file() and sha(path.read_bytes()) == digest, 'checksum mismatch ' + name)
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True, type=Path)
    ap.add_argument('--mode', choices=['prepared','committed'], default='committed')
    args = ap.parse_args()
    repo = args.repo.resolve()
    app = Path(__file__).resolve().parent
    bundle = app.parent
    review = bundle / 'review-packet'
    git = lambda *cmd: subprocess.check_output(['git','-C',str(repo),*cmd], text=True).strip()

    outer = check_inventory(bundle)
    need(outer['artifact'] == 'slskdN PR #409 W79 localization application evidence', 'outer evidence identity')
    nested = check_inventory(review)
    need(nested['head'] == HEAD and nested['tree'] == TREE and nested['cellCount'] == 300,
         'sealed cross-review pin/coverage')
    need(nested['callerlessTextIncluded'] is False and nested['blindCallerlessIssueDetailsIncluded'] is False,
         'sealed packet callerless redaction flags')
    need(nested['catalogChangesMade'] is False and nested['prChanged'] is False,
         'sealed review packet was modified')

    cross = rows(review / 'cross-review-decisions.jsonl')
    current = rows(review / 'inputs/source-current-cells.jsonl')
    plan = rows(app / 'application-plan.jsonl')
    readback = rows(app / 'application-readback-300-cells.jsonl')
    holds = rows(app / 'holds-hash-only.jsonl')
    need((app / 'application-plan.jsonl').read_bytes() == (review / 'proposal-apply-plan.jsonl').read_bytes(),
         'application plan is not byte-identical to sealed plan')
    expected_keys = {(rank, locale) for rank in RANKS for locale in LOCALES}
    key = lambda row: (row['continuationRank'], row['locale'])
    cross_map = {key(row): row for row in cross}
    current_map = {key(row): row for row in current}
    plan_map = {key(row): row for row in plan}
    readback_map = {key(row): row for row in readback}
    holds_map = {key(row): row for row in holds}
    need(len(cross_map) == len(current_map) == len(readback_map) == 300 and
         set(cross_map) == set(current_map) == set(readback_map) == expected_keys,
         'exact 300-cell coverage or duplicate cells')
    counts = collections.Counter(row['crossDisposition'] for row in cross)
    need(counts == {'propose':46,'keep':215,'hold':39}, 'cross disposition counts')
    need(len(plan_map) == 46 and set(plan_map) == {k for k,r in cross_map.items() if r['crossDisposition']=='propose'},
         'proposal plan coverage')
    need(len(holds_map) == 39 and set(holds_map) == {k for k,r in cross_map.items() if r['crossDisposition']=='hold'},
         'all holds retained in hash-only evidence')

    product = loadj(app / 'product-commit.json')
    product_commit = product['commit']
    need(product['expectedParent'] == HEAD and product['parent'] == HEAD and git('rev-parse', product_commit + '^') == HEAD,
         'catalog commit parent')
    need(git('rev-parse', HEAD + '^{tree}') == TREE, 'pinned source tree')
    product_tree = git('rev-parse', product_commit + '^{tree}')
    need(product_tree == product['tree'], 'catalog commit tree hash')
    catalog_paths = sorted({r['catalogPath'] for r in plan})
    need(len(catalog_paths) == 12, 'catalog path count')
    committed_product_paths = sorted(git('diff-tree','--no-commit-id','--name-only','-r',product_commit).splitlines())
    need(committed_product_paths == catalog_paths and all(p.startswith('src/web/public/locales/') and p.endswith('.json') for p in committed_product_paths),
         'catalog commit path scope')
    need(not any(p.startswith('.github/workflows/') or p.startswith('.github/actions/') for p in committed_product_paths),
         'workflow path changed in product commit')
    need('[skip ci]' in git('show','-s','--format=%s',product_commit), 'skip-CI commit marker missing')

    base_catalogs = {}
    post_catalogs = {}
    plan_by_path = collections.defaultdict(list)
    for row in plan:
        plan_by_path[row['catalogPath']].append(row)
        need(text_sha(row['target']) == row['targetSha256'], 'proposal target hash')
        need(row['callerRefs'] and row['productionCallerCount'] > 0, 'callerless proposal')
    metadata = loadj(app / 'catalog-preimage-and-postimage.json')['catalogs']
    metadata_by_path = {row['path']: row for row in metadata}
    need(set(metadata_by_path) == set(catalog_paths) and len(metadata_by_path) == 12, 'catalog metadata coverage')
    for path in catalog_paths:
        base_bytes = subprocess.check_output(['git','-C',str(repo),'show',f'{HEAD}:{path}'])
        post_bytes = subprocess.check_output(['git','-C',str(repo),'show',f'{product_commit}:{path}'])
        copy_bytes = (app / 'postimages' / Path(path).name).read_bytes()
        need(post_bytes == copy_bytes, 'stored catalog postimage differs from commit: ' + path)
        meta = metadata_by_path[path]
        need(sha(base_bytes) == meta['preimageSha256'] and blob_sha(base_bytes) == meta['preimageGitBlob'],
             'catalog preimage hash/blob: ' + path)
        need(sha(post_bytes) == meta['postimageSha256'] and blob_sha(post_bytes) == meta['postimageGitBlob'] and
             git('rev-parse',f'{product_commit}:{path}') == meta['postimageGitBlob'], 'catalog postimage hash/blob: ' + path)
        base_obj, post_obj = json.loads(base_bytes), json.loads(post_bytes)
        need(len(base_obj) == len(post_obj) == 6176 and list(base_obj) == list(post_obj), 'catalog key order/count: ' + path)
        need(sha(canon(list(base_obj))) == meta['keyOrderSha256'] == sha(canon(list(post_obj))), 'ordered key digest: ' + path)
        selected = {r['catalogKey'] for r in plan_by_path[path]}
        changed = {k for k in base_obj if base_obj[k] != post_obj[k]}
        need(changed == selected, 'non-target or missing changed key in ' + path)
        need(meta['changedEntryCount'] == len(selected) and meta['entryCount'] == 6176, 'catalog metadata counts')
        for row in plan_by_path[path]:
            key_name = row['catalogKey']
            need(base_obj.get(key_name) == row['currentTarget'] and text_sha(base_obj[key_name]) == row['currentTargetSha256'],
                 f"preimage target guard {row['continuationRank']}/{row['locale']}")
            need(post_obj.get(key_name) == row['target'] and text_sha(post_obj[key_name]) == row['targetSha256'],
                 f"postimage target readback {row['continuationRank']}/{row['locale']}")
        base_catalogs[path], post_catalogs[path] = base_obj, post_obj

    proposal_source_ids = {r['sourceId'] for r in plan}
    for k, row in cross_map.items():
        cell, rb = current_map[k], readback_map[k]
        backed = row['productionCallerCount'] > 0
        need(rb['sourceId'] == row['sourceId'] and rb['sourceSha256'] == row['sourceSha256'] == cell['sourceSha256'],
             'readback source linkage ' + repr(k))
        need(rb['currentTargetSha256'] == row['currentTargetSha256'] == cell['currentTargetSha256'],
             'readback current hash linkage ' + repr(k))
        need(rb['callerContextSha256'] == row['callerContextSha256'] == cell['callerContextSha256'] and
             rb['productionCallerCount'] == row['productionCallerCount'], 'readback caller linkage ' + repr(k))
        disposition = row['crossDisposition']
        expected_sha = row.get('targetSha256') if disposition == 'propose' else row['currentTargetSha256']
        need(rb['crossDisposition'] == disposition and rb['expectedTargetSha256'] == expected_sha and
             rb['readbackTargetSha256'] == expected_sha and rb['readbackMatched'] is True,
             'readback expected/actual hash ' + repr(k))
        need(rb['catalogPath'] == cell['catalogPath'], 'readback catalog path ' + repr(k))
        need(rb['catalogFilePreimageSha256'] == cell['catalogFileSha256'], 'readback preimage file binding ' + repr(k))
        need(rb['catalogFilePostimageSha256'] == metadata_by_path[cell['catalogPath']]['postimageSha256'],
             'readback postimage file binding ' + repr(k))
        hold_row = holds_map.get(k)
        if disposition == 'hold':
            need(hold_row is not None and not (TEXT_FIELDS & set(rb)) and not (TEXT_FIELDS & set(hold_row)),
                 'held cell text in application evidence ' + repr(k))
            need(rb['readbackTargetTextIncluded'] is False and hold_row['targetTextIncluded'] is False and
                 hold_row['sourceTextIncluded'] is False, 'held text inclusion flags')
            need(hold_row['sourceId'] == row['sourceId'] and hold_row['currentTargetSha256'] == expected_sha and
                 hold_row['callerContextSha256'] == row['callerContextSha256'], 'hold hash row binding')
            if backed:
                actual = post_catalogs[cell['catalogPath']][cell['catalogKey']]
                need(text_sha(actual) == expected_sha, 'backed hold value changed')
            else:
                need(k[0] in CALLERLESS and row['holdReasonCode'] == 'CALLERLESS_NO_PRODUCTION_CALLER', 'callerless hold reason')
                need(rb.get('callerlessHashOnly') is True and 'catalogKey' not in rb and row.get('catalogKey') is None,
                     'callerless readback leaked key')
                need(cell.get('sourceTextIncluded') is False and cell.get('currentTargetTextIncluded') is False and
                     'source' not in cell and 'currentTarget' not in cell and 'catalogKey' not in cell,
                     'callerless source/current text or key included')
                need(row['sourceId'] not in proposal_source_ids, 'callerless source ID is among proposed keys')
            need(row['crossDisposition'] == 'hold', 'hold disposition changed')
        else:
            need(backed and hold_row is None and rb['catalogKey'] == cell['catalogKey'], 'non-hold lacks caller/key')
            actual = post_catalogs[cell['catalogPath']][cell['catalogKey']]
            need(rb.get('readbackTarget') == actual and text_sha(actual) == rb['readbackTargetSha256'],
                 'exact application value readback ' + repr(k))
            need(rb['readbackTargetTextIncluded'] is True, 'backed readback text missing')
            if disposition == 'propose':
                proposal = plan_map[k]
                need(actual == proposal['target'] and row['targetSha256'] == proposal['targetSha256'] == rb['readbackTargetSha256'],
                     'proposal exact-value readback ' + repr(k))
                need(proposal['currentTargetSha256'] == row['currentTargetSha256'], 'proposal current-hash guard linkage')
            else:
                need(disposition == 'keep' and text_sha(actual) == row['currentTargetSha256'], 'kept value changed')
        need(rb.get('sourceTextIncluded') is False, 'readback duplicated source text')

    # Every callerless row stays hash-only in each sealed and application ledger.
    callerless_keys = {(rank, locale) for rank in CALLERLESS for locale in LOCALES}
    need({k for k,r in cross_map.items() if r['productionCallerCount']==0} == callerless_keys, 'callerless coverage')
    for k in callerless_keys:
        row = cross_map[k]
        need(row['crossDisposition']=='hold' and row['sourceTextIncluded'] is False and
             row['currentTargetTextIncluded'] is False and row['primaryProposalTextIncluded'] is False and
             row['crossTargetTextIncluded'] is False, 'callerless review text flags')
        need(not (TEXT_FIELDS & set(row)), 'callerless cross row contains text/key')
        blind = next(x for x in rows(review / 'blind-review-redacted.jsonl') if key(x)==k)
        need('issues' not in blind and blind.get('blindIssueDetailsOmitted') is True and
             blind.get('sourceTextIncluded') is False and blind.get('targetTextIncluded') is False,
             'callerless blind issue/text leakage')

    app_summary = loadj(app / 'application-summary.json')
    need(app_summary['productCommit'] == product_commit and app_summary['readbackCellCount']==300 and
         app_summary['proposalCount']==46 and app_summary['keepCount']==215 and app_summary['holdCount']==39 and
         app_summary['callerlessHashOnlyHoldCount']==24 and app_summary['catalogCount']==12 and
         app_summary['catalogKeyCountPerLocale']==6176 and app_summary['catalogKeyOrderUnchanged'] is True and
         app_summary['repositoryEditsOutsideLocaleCatalogs'] is False, 'application summary mismatch')
    policy = loadj(app / 'local-hooks-policy.json')
    need(policy['hookBypassCommandScope']=='one-shot' and policy['testsScansBuildsCiRun'] is False,
         'hook policy/effect summary')
    live = loadj(app / 'live-before-apply.json')
    need(live['headRefOid']==HEAD and live['branchRefOid']==HEAD and live['pullRefOid']==HEAD and
         live['commitTree']==TREE and live['state']=='OPEN' and live['draft'] is True and live['merged'] is False,
         'pre-apply live refs')

    if args.mode == 'prepared':
        need(git('rev-parse','HEAD') == product_commit, 'prepared mode must run at catalog commit')
        status = subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True).splitlines()
        need(status == ['?? ' + bundle.relative_to(repo).as_posix() + '/'], 'unexpected prepared worktree changes')
    else:
        need(git('rev-parse','HEAD^') == product_commit, 'evidence commit parent is not product commit')
        need(not git('status','--porcelain'), 'worktree not clean after evidence commit')
        evidence_paths = sorted(git('diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines())
        expected_evidence_paths = sorted(
            str(Path(bundle.relative_to(repo)) / p.relative_to(bundle))
            for p in bundle.rglob('*') if p.is_file()
        )
        need(evidence_paths == expected_evidence_paths, 'evidence commit path scope differs from bundle')
        need(all(p.startswith(str(bundle.relative_to(repo)) + '/') for p in evidence_paths), 'evidence commit modified outside packet')
        need('[skip ci]' in git('show','-s','--format=%s','HEAD'), 'evidence commit skip-CI marker missing')
    print(json.dumps({
        'result':'PASS','mode':args.mode,'baseHead':HEAD,'productCommit':product_commit,
        'readbackCells':300,'proposals':46,'keeps':215,'holds':39,'callerlessHashOnlyHolds':24,
        'catalogs':12,'catalogEntriesPerLocale':6176,'catalogKeyOrder':'unchanged',
        'tokenSafeSelectedProposals':46,'workflowPathsChanged':0,
    },ensure_ascii=False,sort_keys=True))


if __name__=='__main__':
    main()
