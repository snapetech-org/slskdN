#!/usr/bin/env python3
"""Read-only exact-pin, overlap, caller, hash, and packet verifier for W35."""
import collections, hashlib, json, re, subprocess
from pathlib import Path

ROOT = Path('/mnt/disks/scratch/task-scratch/slskdn-manual-review-window35-91727326-20261102')
REPO = Path('/mnt/disks/scratch/task-worktrees/localization-20261102/slskdn-pr409-w35-review')
BRANCH = 'refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'
EVIDENCE = 'docs/pr-evidence/pr409-manual-semantic-review-2026-11-01'
LOCALES = ['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']

def sha(value): return hashlib.sha256(value if isinstance(value, bytes) else value.encode('utf-8')).hexdigest()
def read_jsonl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args])
def git_text(*args): return git(*args).decode('utf-8').strip()
def fail(message): raise SystemExit('FAIL: '+message)

manifest = json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
head, tree, source_tree = manifest['headCommit'], manifest['tree'], manifest['sourceSubtreeTree']
pr = json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,mergeStateStatus,headRefOid'], text=True))
if pr != {'state':'OPEN','isDraft':True,'mergeStateStatus':'CLEAN','headRefOid':head}: fail(f'live PR state/head changed: {pr}')
if git_text('rev-parse',f'{head}^{{tree}}') != tree or git_text('rev-parse',f'{head}:src/web/src') != source_tree: fail('pinned commit/tree/source subtree mismatch')
remote_rows = subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin',BRANCH], text=True).splitlines()
remote = remote_rows[0].split()[0] if remote_rows else ''
if remote != head: fail(f'remote PR branch changed: {remote}')
repo_head = git_text('rev-parse','HEAD')
if repo_head != head: fail(f'inspection worktree not at exact pin: {repo_head}')
if git_text('status','--porcelain'): fail('inspection worktree not clean')

# Recheck the complete prior manual-review and application histories from the pinned commit.
manual_ids, manual_keys, manual_cells = set(), set(), 0
window_counts = []
for n in range(1,35):
    path = f'{EVIDENCE}/window{n}/review-input.jsonl'
    if n in (32,33,34): path = f'{EVIDENCE}/window{n}/review-packet/review-input.jsonl' if n in (32,33) else f'{EVIDENCE}/window34/review-packet/review-input.jsonl'
    try: rows = [json.loads(x) for x in git('show',f'{head}:{path}').decode('utf-8').splitlines() if x.strip()]
    except subprocess.CalledProcessError: fail(f'prior review input missing: W{n}')
    ids = {r['id'] for r in rows}
    if len(ids) != len(rows) or manual_ids & ids: fail(f'prior manual-window duplicate/overlap at W{n}')
    manual_ids |= ids; manual_keys |= {r['sourceId'] for r in rows}; manual_cells += len(rows)
    window_counts.append({'window':n,'cells':len(rows),'sourceKeys':len({r['sourceId'] for r in rows})})
if (manual_cells,len(manual_ids),len(manual_keys)) != (10052,10052,847): fail(f'prior manual totals changed: {manual_cells}/{len(manual_ids)}/{len(manual_keys)}')

formal_rows = read_jsonl(ROOT/'formal-cell-ids.jsonl')
formal_ids = {r['id'] for r in formal_rows}
if len(formal_rows) != 4800 or len(formal_ids) != 4800: fail('formal-cell-id count/uniqueness mismatch')
if sha((ROOT/'formal-cell-ids.jsonl').read_bytes()) != manifest['formalAccumulator']['cellIdsSha256']: fail('formal-cell-id checksum mismatch')
if formal_ids & manual_ids: fail('historical formal/manual overlap')

applied_paths = [
 'docs/pr-evidence/pr409-catalog-correction-application-2026-11-01/applied-corrections.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows18-19-2026-11-02/applied-corrections.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows20-21-2026-11-02/applied-corrections.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02/applied-corrections-windows22-23.jsonl',
 'docs/pr-evidence/pr409-catalog-correction-application-windows22-23-2026-11-02/applied-corrections-realm-window20.jsonl',
] + [f'docs/pr-evidence/pr409-catalog-correction-application-window{n}-2026-11-02/applied-corrections-window{n}.jsonl' for n in range(24,35)]
applied_rows, applied_ids, applied_hashes = [], set(), {}
for path in applied_paths:
    raw = git('show',f'{head}:{path}')
    rows = [json.loads(x) for x in raw.decode('utf-8').splitlines() if x.strip()]
    ids = {r['id'] for r in rows}
    if len(ids) != len(rows) or applied_ids & ids: fail(f'applied correction overlap/duplicate: {path}')
    applied_ids |= ids; applied_rows.extend(rows); applied_hashes[path] = sha(raw)
if len(applied_rows) != 1373 or len(applied_ids) != 1373 or not applied_ids <= manual_ids: fail(f'applied correction totals changed: {len(applied_rows)}/{len(applied_ids)}')

inputs = read_jsonl(ROOT/'review-input.jsonl')
decisions = read_jsonl(ROOT/'review-decisions.jsonl')
plan = read_jsonl(ROOT/'crossreview-plan.jsonl')
uncertain = read_jsonl(ROOT/'uncertain-ledger.jsonl')
if sha((ROOT/'review-input.jsonl').read_bytes()) != manifest['reviewInput']['sha256']: fail('review-input checksum mismatch')
if len(inputs) != 274 or len({r['id'] for r in inputs}) != 274 or len({r['sourceId'] for r in inputs}) != 25: fail('W35 input coverage/uniqueness mismatch')
if len({r['sourceId'] for r in inputs} & manual_keys) or {r['id'] for r in inputs} & (manual_ids | formal_ids | applied_ids): fail('W35 input overlaps prior manual/formal/applied rows')
if manifest['scope']['formalOverlap'] != 0 or manifest['scope']['priorManualOverlap'] != 0 or manifest['scope']['priorCorrectionOverlap'] != 0: fail('manifest reports overlap')
if {r['id'] for r in inputs} != {d['id'] for d in decisions} or len(decisions) != len(inputs): fail('decision ledger does not cover each input once')
by_input, by_decision, by_plan, by_uncertain = ({r['id']:r for r in rows} for rows in (inputs,decisions,plan,uncertain))
if len(by_plan) != len(plan) or len(by_uncertain) != len(uncertain): fail('duplicate candidate/uncertain rows')
if {i for i,d in by_decision.items() if d['verdict']=='correct'} != set(by_plan): fail('candidate set differs from correction decisions')
if {i for i,d in by_decision.items() if d['verdict']=='uncertain'} != set(by_uncertain): fail('uncertain ledger differs from decisions')

placeholder_re = re.compile(r'\{[^{}]+\}')
def placeholders(value): return sorted(placeholder_re.findall(value))
caller_count = 0
for locale in manifest['scope']['directLocales']:
    catalog_path = f'src/web/public/locales/{locale}.json'
    raw = git('show',f'{head}:{catalog_path}')
    if sha(raw) != manifest['currentCatalogFileSha256'][locale]: fail(f'catalog blob hash mismatch: {locale}')
    catalog = json.loads(raw.decode('utf-8'))
    if len(catalog) != manifest['catalogKeyCounts'][locale]: fail(f'catalog key count mismatch: {locale}')
    for row in inputs:
        if row['locale'] != locale: continue
        if catalog.get(row['catalogKey']) != row['target'] or sha(row['target']) != row['targetSha256']: fail(f'current target/hash mismatch: {row["id"]}')
        if sha(row['source']) != row['sourceSha256']: fail(f'source hash mismatch: {row["id"]}')
        if placeholders(row['source']) != sorted(row.get('placeholders',[])) or placeholders(row['source']) != placeholders(row['target']): fail(f'frozen source/current placeholder mismatch: {row["id"]}')
        for literal in row.get('protectedLiterals',[]):
            if literal not in row['target']: fail(f'current protected literal mismatch: {row["id"]}/{literal}')
        for caller in row.get('sourceCallsites',[]):
            caller_raw = git('show',f'{head}:{caller["path"]}')
            if sha(caller_raw) != caller['fileSha256']: fail(f'caller file hash mismatch: {row["id"]}/{caller["path"]}')
            lines = caller_raw.decode('utf-8').splitlines()
            if not 1 <= caller['line'] <= len(lines): fail(f'caller line out of range: {row["id"]}')
            line = lines[caller['line']-1].strip()
            if line != caller['lineText'] or sha(line) != caller['lineTextSha256']: fail(f'caller line text/hash mismatch: {row["id"]}/{caller["path"]}:{caller["line"]}')
            caller_count += 1

for ident, decision in by_decision.items():
    row = by_input[ident]
    if (decision['sourceSha256'],decision['currentTargetSha256']) != (row['sourceSha256'],row['targetSha256']): fail(f'decision hash pin mismatch: {ident}')
    if decision['verdict'] == 'correct':
        candidate = by_plan[ident]
        if (candidate['sourceSha256'],candidate['currentTargetSha256']) != (row['sourceSha256'],row['targetSha256']): fail(f'candidate source/current pin mismatch: {ident}')
        if sha(candidate['proposedTarget']) != candidate['proposedTargetSha256'] or decision.get('candidateTargetSha256') != candidate['proposedTargetSha256']: fail(f'candidate target hash mismatch: {ident}')
        if placeholders(row['source']) != placeholders(candidate['proposedTarget']): fail(f'candidate placeholder mismatch: {ident}')
        if any(lit not in candidate['proposedTarget'] for lit in row.get('protectedLiterals',[])): fail(f'candidate protected literal mismatch: {ident}')
        if (candidate['currentCatalogFileSha256'],candidate['currentPrHead'],candidate['currentPrTree'],candidate['currentSourceSubtreeTree']) != (manifest['currentCatalogFileSha256'][row['locale']],head,tree,source_tree): fail(f'candidate current pin mismatch: {ident}')
    elif ident in by_plan: fail(f'non-correction row has candidate: {ident}')
    if decision['verdict'] == 'uncertain':
        hold = by_uncertain[ident]
        if (hold['sourceSha256'],hold['currentTargetSha256']) != (row['sourceSha256'],row['targetSha256']): fail(f'uncertain pin mismatch: {ident}')

counts = collections.Counter(d['verdict'] for d in decisions)
if dict(counts) != {'correct':38,'keep':236}: fail(f'decision count mismatch: {dict(counts)}')
if caller_count != 445 or caller_count != manifest['sourceCallerLinesPreflighted']: fail(f'caller line count mismatch: {caller_count}')
if manifest['priorManualCoverage']['windowCounts'] != window_counts: fail('prior manual window count manifest mismatch')
for path,key in [('review-decisions.jsonl','reviewDecisionLedger'),('crossreview-plan.jsonl','candidatePlan'),('uncertain-ledger.jsonl','uncertainLedger')]:
    if sha((ROOT/path).read_bytes()) != manifest[key]['sha256']: fail(f'{path} manifest checksum mismatch')
summary = json.loads((ROOT/'review-summary.json').read_text(encoding='utf-8'))
if summary['verdicts'] != dict(sorted(counts.items())) or summary['cells'] != len(inputs) or summary['correctionRows'] != len(plan): fail('review summary count mismatch')
if summary['rootCrossReview'] != 'pending' or summary['nativeSpeakerReview'] != 'outstanding' or summary['targetsApplied'] or summary['catalogsEdited']: fail('review state misrepresented')

report = {
 'result':'PASS', 'window':35, 'livePrState':pr['state'], 'livePrDraft':pr['isDraft'], 'livePrMergeState':pr['mergeStateStatus'],
 'livePrHead':head, 'livePrTree':tree, 'sourceSubtreePath':'src/web/src', 'sourceSubtreeTree':source_tree,
 'remotePrBranchHead':remote, 'inspectionWorktreeHead':repo_head, 'inspectionWorktreeClean':True,
 'priorManualCells':manual_cells, 'priorManualSourceKeys':len(manual_keys), 'priorAppliedCorrectionRows':len(applied_rows),
 'formalCells':len(formal_ids), 'inputCells':len(inputs), 'sourceKeys':len({r['sourceId'] for r in inputs}),
 'localeCells':dict(collections.Counter(r['locale'] for r in inputs)), 'callerLinesRechecked':caller_count,
 'decisionCounts':dict(sorted(counts.items())), 'candidateRows':len(plan), 'uncertainRows':len(uncertain),
 'reviewInputSha256':sha((ROOT/'review-input.jsonl').read_bytes()), 'decisionLedgerSha256':sha((ROOT/'review-decisions.jsonl').read_bytes()),
 'candidatePlanSha256':sha((ROOT/'crossreview-plan.jsonl').read_bytes()), 'uncertainLedgerSha256':sha((ROOT/'uncertain-ledger.jsonl').read_bytes()),
 'catalogHashes':manifest['currentCatalogFileSha256'], 'appliedLedgerFileHashes':applied_hashes,
 'rootCrossReview':'pending', 'nativeSpeakerReview':'outstanding', 'catalogsEdited':False, 'repositoryEdited':False,
}
(ROOT/'verification-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
checksum_names = ['review-input.jsonl','review-decisions.jsonl','crossreview-plan.jsonl','uncertain-ledger.jsonl','formal-cell-ids.jsonl','manifest.json','preflight.json','freeze-summary.json','review-summary.json','verification-report.json','README.md','freeze_window35.py','build_packets_window35.py','verify_window35.py']
for name in checksum_names:
    if not (ROOT/name).is_file(): fail(f'checksummed artifact missing: {name}')
(ROOT/'SHA256SUMS.txt').write_text(''.join(f'{sha((ROOT/name).read_bytes())}  {name}\n' for name in checksum_names),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
