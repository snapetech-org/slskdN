#!/usr/bin/env python3
"""Build clean exact-head source/current/caller input for slskdN PR #409 W53."""
from pathlib import Path
import collections, hashlib, json, re, shutil, subprocess

REPO = Path('/mnt/disks/scratch/task-worktrees/localization-20261103/slskdn-pr409-w52-primary-20261103')
OUT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w53-20261103')
INPUT = OUT / 'input'
W49 = REPO / 'docs/pr-evidence/pr409-localization-2026-11-03/window49'
W50 = REPO / 'docs/pr-evidence/pr409-localization-2026-11-03/window50'
W51 = REPO / 'docs/pr-evidence/pr409-localization-2026-11-03/window51'
W52 = REPO / 'docs/pr-evidence/pr409-localization-2026-11-03/window52'
HEAD = '6d5723e244338a550e3dfa5182a45857156467a7'
TREE = '8435576260e9aa760609be6a28001b2bb38b8c11'
BODY_SHA256 = '8d1708765c003a72da67370af5816a7cd998cfb97b2246227aaf1529f858cf4a'
BRANCH = 'codex/slskdn-oidc-tooltip-localization-20261030'
PR = 409
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
CATALOGS = {loc: f'src/web/public/locales/{loc}.json' for loc in LOCALES}
WINDOW = range(226, 251)

# Exact tokens that are product, service, protocol, command, or app names.
# This is a review checklist, not a candidate translation or verdict.
PROTECTED = {
    229: [{'literal':'MilkDrop3','kind':'product/format name','policy':'Preserve exact spelling and case.'}],
    230: [{'literal':'Pushover','kind':'notification service name','policy':'Preserve exact spelling and case.'}],
    234: [{'literal':'/','kind':'slash-command introducer','policy':'Preserve the slash-command syntax.'},
          {'literal':'/help','kind':'slash command','policy':'Preserve exact spelling and case.'}],
    237: [{'literal':'Pushbullet','kind':'notification service name','policy':'Preserve exact spelling and case.'}],
    240: [{'literal':'Obfs4','kind':'proxy protocol name','policy':'Preserve exact spelling and case.'}],
    245: [{'literal':'Kestrel','kind':'server technology name','policy':'Preserve exact spelling and case.'}],
    249: [{'literal':'slskdN','kind':'application name','policy':'Preserve exact spelling and case.'}],
}
SEMANTIC_TERMS = {
    229: [{'term':'q-register','basis':'MilkDrop visualization preset terminology; preserve the register concept, localize surrounding prose.'}],
    231: [{'term':'retention minutes','basis':'Admin policy duration/retention setting; preserve that the value is minutes.'}],
    235: [{'term':'host','basis':'Listen-along room host role; distinguish host from the local user.'}],
    238: [{'term':'auto-tagging','basis':'Metadata-processing stage label; describe automatic tagging.'}],
    239: [{'term':'changed fields','basis':'Audit/change summary term; caller was not found in the bounded production scan.'}],
    244: [{'term':'native presets','basis':'Visualizer feature refers to locally imported native presets; caller context must distinguish them from packaged presets.'}],
    249: [{'term':'cutoff-unmet','basis':'Servarr readiness state; retain the meaning that the cutoff condition has not been met.'}],
}

PLACEHOLDER_RE = re.compile(r'\{[^{}]+\}')
MARKUP_RE = re.compile(r'</?[A-Za-z][^>]*>')
NUMBER_RE = re.compile(r'(?<![A-Za-z])\d+(?:[.,]\d+)?%?(?![A-Za-z])')


def run(*args, cwd=REPO, text=True):
    return subprocess.check_output(list(args), cwd=cwd, text=text)

def sha(data):
    if isinstance(data, str): data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()

def git_blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()

def sid(source):
    return 'src_' + sha(source)[:16]

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def write_jsonl(path, rows):
    with path.open('w', encoding='utf-8', newline='\n') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def verify_manifest(directory, name):
    manifest = directory / name
    checks = []
    for line in manifest.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        expected, rel = line.split(None, 1)
        rel = rel.strip().lstrip('*')
        actual = sha((directory / rel).read_bytes())
        checks.append({'path':rel,'expected':expected,'actual':actual,'matches':expected == actual})
    assert checks and all(x['matches'] for x in checks), (manifest, checks)
    return checks

def write_manifest(directory, name):
    manifest = directory / name
    rows = []
    for p in sorted(x for x in directory.rglob('*') if x.is_file() and x != manifest):
        rows.append(f'{sha(p.read_bytes())}  {p.relative_to(directory).as_posix()}')
    manifest.write_text('\n'.join(rows) + '\n', encoding='utf-8')

def live_pin():
    head = run('git','rev-parse','HEAD').strip()
    tree = run('git','rev-parse','HEAD^{tree}').strip()
    assert head == HEAD and tree == TREE, (head, tree)
    assert not run('git','status','--porcelain=v1').strip(), run('git','status','--short')
    pr = json.loads(run('gh','pr','view',str(PR),'--repo','snapetech-org/slskdN','--json','body,headRefOid,headRefName,isDraft,state,url'))
    body_hash = sha(pr['body'])
    assert pr['state'] == 'OPEN' and pr['isDraft'] is True, pr
    assert pr['headRefOid'] == HEAD and pr['headRefName'] == BRANCH and body_hash == BODY_SHA256, (pr['headRefOid'],pr['headRefName'],body_hash)
    remote = run('git','ls-remote','origin',f'refs/heads/{BRANCH}').strip().split()
    assert len(remote) == 2 and remote[0] == HEAD, remote
    return {'repository':'snapetech-org/slskdN','pullRequest':PR,'url':pr['url'],'state':pr['state'],'isDraft':pr['isDraft'],'branch':BRANCH,'head':HEAD,'tree':TREE,'remoteBranchHead':remote[0],'bodySha256':body_hash,'localWorktreeClean':True}

def js_escape(value, delimiter):
    value = value.replace('\\','\\\\').replace('\n','\\n').replace('\r','\\r').replace('\t','\\t')
    return value.replace(delimiter, '\\' + delimiter)

assert not INPUT.exists(), f'Clean input path already exists: {INPUT}'
assert set(p.name for p in OUT.iterdir()) == {'build_input.py'}, f'Unexpected task output content: {list(OUT.iterdir())}'
assert shutil.disk_usage(OUT.parent).free > 1_000_000_000
pin = live_pin()

# Verify frozen prior evidence used to define the stable-ID continuation queue.
prior_checks = {}
for folder in (W49, W50, W51):
    checks = verify_manifest(folder, 'EVIDENCE-SHA256SUMS.txt')
    prior_checks[folder.name] = {'entriesVerified':len(checks),'manifestSha256':sha((folder/'EVIDENCE-SHA256SUMS.txt').read_bytes())}
w52_checks = {}
for manifest in sorted(p for p in W52.rglob('*') if p.is_file() and ('SHA256SUMS' in p.name)):
    checks = verify_manifest(manifest.parent, manifest.name)
    w52_checks[manifest.relative_to(W52).as_posix()] = {'entriesVerified':len(checks),'manifestSha256':sha(manifest.read_bytes())}

inventory_path = W49 / 'primary/source-inventory.jsonl'
inventory = read_jsonl(inventory_path)
by_rank = {r['continuationRank']:r for r in inventory if r.get('continuationRank') in range(126,252)}
assert set(by_rank) == set(range(126,252)), sorted(by_rank)
rank_rows = {r:by_rank[r] for r in WINDOW}
selected = [rank_rows[r] for r in WINDOW]
assert len(selected) == 25 and len({r['sourceId'] for r in selected}) == 25
assert all(r['sourceId'] == sid(r['source']) for r in selected)

w50_rows = read_jsonl(W50/'primary/selection-boundary.jsonl')
w51_rows = read_jsonl(W51/'primary/selection-boundary.jsonl')
w52_rows = read_jsonl(W52/'primary/selection-boundary.jsonl')
w50_ids = {r['sourceId'] for r in w50_rows if r.get('role') == 'selected-W50'}
w51_ids = {r['sourceId'] for r in w51_rows if r.get('role') == 'selected-W51'}
w52_ids = {r['sourceId'] for r in w52_rows if r.get('role') == 'selected-W52'}
assert len(w50_ids) == len(w51_ids) == len(w52_ids) == 25
assert w50_ids == {by_rank[r]['sourceId'] for r in range(151,176)}
assert w51_ids == {by_rank[r]['sourceId'] for r in range(176,201)}
assert w52_ids == {by_rank[r]['sourceId'] for r in range(201,226)}
excluded_w49_gap = {by_rank[r]['sourceId'] for r in range(126,151)}
selected_ids = {r['sourceId'] for r in selected}
assert not selected_ids & (w50_ids | w51_ids | w52_ids | excluded_w49_gap)

# Read and pin every locale catalog at the exact PR head.
locales = {}
cat_rows = []
ordered_keys = None
for loc, relpath in CATALOGS.items():
    data = (REPO / relpath).read_bytes()
    entries = json.loads(data)
    keys = list(entries)
    if ordered_keys is None: ordered_keys = keys
    assert keys == ordered_keys, f'ordered key mismatch in {loc}'
    assert all(isinstance(v,str) and v for v in entries.values()), f'blank/non-string entry in {loc}'
    locales[loc] = entries
    blob = run('git','rev-parse',f'{HEAD}:{relpath}').strip()
    assert git_blob(data) == blob, f'catalog blob mismatch {loc}'
    cat_rows.append({'locale':loc,'catalogPath':relpath,'bytes':len(data),'sha256':sha(data),'gitBlob':blob,'entryCount':len(entries),'nonemptyValueCount':sum(bool(v) for v in entries.values()),'orderedKeySha256':sha('\n'.join(keys)+'\n')})
assert len(ordered_keys) == 6176
ordered_hash = sha('\n'.join(ordered_keys)+'\n')
assert len({x['orderedKeySha256'] for x in cat_rows}) == 1
source_by_id = {sid(source):source for source in ordered_keys}
assert len(source_by_id) == len(ordered_keys)
assert all(source_by_id.get(r['sourceId']) == r['source'] for r in selected)

quote_cache = {}
def caller_refs(source):
    if source not in quote_cache:
        double = r'"' + re.escape(js_escape(source, '"')) + r'"'
        single = r"'" + re.escape(js_escape(source, "'")) + r"'"
        quote_cache[source] = re.compile(r'(?<![A-Za-z0-9_$])(?:' + double + r'|' + single + r')')
    pat = quote_cache[source]
    refs = []
    for path in sorted((REPO/'src/web/src').rglob('*')):
        if path.suffix not in {'.js','.jsx','.ts','.tsx'}: continue
        if '.test.' in path.name or '__tests__' in path.parts or path.name.endswith('.test'+path.suffix): continue
        try: data = path.read_bytes(); text = data.decode('utf-8')
        except (OSError,UnicodeDecodeError): continue
        lines = text.splitlines()
        for line_no,line in enumerate(lines,1):
            if not pat.search(line): continue
            rel = str(path.relative_to(REPO))
            pinned = run('git','show',f'{HEAD}:{rel}',text=False)
            assert pinned == data, f'caller file is not from pinned tree: {rel}'
            context = [{'line':i+1,'text':lines[i]} for i in range(max(0,line_no-3),min(len(lines),line_no+3))]
            refs.append({'path':rel,'line':line_no,'lineText':line,'lineSha256':sha(line),'context':context,'contextSha256':sha(canonical(context)),'fileBytes':len(data),'fileSha256':sha(data),'gitBlob':run('git','rev-parse',f'{HEAD}:{rel}').strip(),'gitBlobSha1Check':git_blob(data)})
    return refs

caller_rows = []
caller_map = {}
for row in selected:
    refs = caller_refs(row['source'])
    caller_map[row['sourceId']] = refs
    caller_rows.append({'continuationRank':row['continuationRank'],'sourceId':row['sourceId'],'source':row['source'],'sourceSha256':sha(row['source']),'productionCallerCount':len(refs),'boundedScan':'exact quoted literal search in src/web/src JavaScript/TypeScript production files; tests excluded','callers':refs})

protected_rows = []
source_cells = []
for row in selected:
    rank = row['continuationRank']; source = row['source']; source_id = row['sourceId']; refs = caller_map[source_id]
    ref_sha = sha(canonical(refs))
    literals = PROTECTED.get(rank, [])
    protected_rows.append({'continuationRank':rank,'sourceId':source_id,'source':source,'sourceSha256':sha(source),'exactProtectedLiterals':literals,'semanticTerms':SEMANTIC_TERMS.get(rank,[]),'callerContextSha256':ref_sha})
    source_ph = collections.Counter(PLACEHOLDER_RE.findall(source))
    source_markup = collections.Counter(MARKUP_RE.findall(source))
    source_numbers = NUMBER_RE.findall(source)
    for loc in LOCALES:
        target = locales[loc][source]
        cat = next(x for x in cat_rows if x['locale'] == loc)
        current_ph = collections.Counter(PLACEHOLDER_RE.findall(target))
        current_markup = collections.Counter(MARKUP_RE.findall(target))
        protected_checks = [{'literal':item['literal'],'kind':item['kind'],'sourcePresent':item['literal'] in source,'currentPresent':item['literal'] in target,'policy':item['policy']} for item in literals]
        source_cells.append({'continuationRank':rank,'historicalSourceOrdinal':None,'sourceId':source_id,'source':source,'sourceSha256':sha(source),'locale':loc,'catalogPath':CATALOGS[loc],'catalogFileSha256':cat['sha256'],'catalogGitBlob':cat['gitBlob'],'currentTarget':target,'currentTargetSha256':sha(target),'callerContextSha256':ref_sha,'callerRefs':[{'path':r['path'],'line':r['line'],'lineSha256':r['lineSha256'],'fileSha256':r['fileSha256'],'gitBlob':r['gitBlob']} for r in refs],'placeholderEvidence':{'sourceTokens':dict(source_ph),'currentTokens':dict(current_ph),'matches':source_ph == current_ph},'markupEvidence':{'sourceTags':dict(source_markup),'currentTags':dict(current_markup),'matches':source_markup == current_markup},'sourceNumericTokens':source_numbers,'currentNumericTokens':NUMBER_RE.findall(target),'protectedLiteralChecks':protected_checks})
assert len(source_cells) == 300 and len(caller_rows) == 25 and len(protected_rows) == 25
assert all('candidateTarget' not in r and 'verdict' not in r and 'disposition' not in r for r in source_cells)

boundary_rows = []
for rank, role in ((225,'previous-boundary-W52'), *[(r,'selected-W53') for r in WINDOW], (251,'next-boundary-W54')):
    item = by_rank[rank]
    boundary_rows.append({'role':role,'continuationRank':rank,'sourceId':item['sourceId'],'source':item['source'],'sourceSha256':sha(item['source']),'historicalSourceOrdinal':None})

selection = {'repository':'snapetech-org/slskdN','pullRequest':PR,'pullRequestUrl':pin['url'],'pins':pin,'window':'W53 continuation of the W49 stable-ID inventory: ranks 226-250; historical source ordinals unavailable and not claimed','rankBasis':'W49 primary source-inventory.jsonl, re-attested against W53 current catalog keys. W50 selected IDs map to W49 ranks 151-175; W51 to 176-200; W52 to 201-225; W53 selects the next 25 IDs at 226-250. W49 ranks 126-150 remain excluded/unreviewed.','localeOrder':LOCALES,'localeCount':12,'sourceCount':25,'cellCount':300,'catalogSourceCount':len(ordered_keys),'orderedCatalogKeySha256':ordered_hash,'previousBoundary':boundary_rows[0],'firstSelected':boundary_rows[1],'lastSelected':boundary_rows[-2],'nextBoundary':boundary_rows[-1],'disjointness':{'w49HistoricalGap126To150':len(excluded_w49_gap),'w50Selected':len(w50_ids),'w51Selected':len(w51_ids),'w52Selected':len(w52_ids),'w53Selected':len(selected_ids),'w53DisjointFromW49Gap':not bool(selected_ids & excluded_w49_gap),'w53DisjointFromW50W51W52':not bool(selected_ids & (w50_ids|w51_ids|w52_ids))},'priorEvidenceChecks':{'w49':prior_checks[W49.name],'w50':prior_checks[W50.name],'w51':prior_checks[W51.name],'w52':w52_checks,'w49SourceInventorySha256':sha(inventory_path.read_bytes())},'inputContainsCandidates':False}

OUT.mkdir(parents=True,exist_ok=True)
INPUT.mkdir()
write_json(INPUT/'head-tree-attestation.json',pin)
write_json(INPUT/'selection-and-boundary.json',selection)
write_jsonl(INPUT/'selection-boundary.jsonl',boundary_rows)
write_jsonl(INPUT/'catalog-structure.jsonl',cat_rows)
write_jsonl(INPUT/'caller-contexts.jsonl',caller_rows)
write_jsonl(INPUT/'source-current-cells.jsonl',source_cells)
write_jsonl(INPUT/'protected-literals.jsonl',protected_rows)
readme = f'''# slskdN PR #409 W53 clean input packet\n\nThis is a no-candidate input packet pinned to live PR head/tree `{HEAD}` / `{TREE}` and branch `{BRANCH}`. PR #409 was open and draft at capture; PR body SHA-256: `{BODY_SHA256}`.\n\nW53 selects 25 stable source IDs at W49 inventory continuation ranks 226–250 across all 12 direct locale catalogs (300 cells). Historical extraction ordinals are unavailable and are not claimed. The previous boundary is rank 225; the next boundary is rank 251. The source set is disjoint from W49's unreviewed ranks 126–150 and W50–W52 (W50 selected IDs map to W49 ranks 151–175).\n\n`source-current-cells.jsonl` includes exact source/current SHA-256 values, catalog blob and file pins, caller references, placeholder and markup evidence, numeric source/current tokens, and checks of listed protected literals. `caller-contexts.jsonl` records bounded exact-literal production caller hits with source lines, surrounding context, and file/line/blob hashes. `protected-literals.jsonl` contains a source- and caller-based protected-name checklist and semantic terms. Two sources have no exact production caller in the bounded source scan; the packet marks those counts explicitly and leaves their values for reviewer judgment.\n\nThis input contains no candidate translations, verdicts, dispositions, or adjudication. The primary review is stored separately in `../primary/` and was prepared only after this input manifest was sealed.\n'''
(INPUT/'README.md').write_text(readme,encoding='utf-8')
write_manifest(INPUT,'PACKET-SHA256SUMS.txt')

# Read back structural counts and seal after reattesting live repository/PR pins.
input_checks = verify_manifest(INPUT,'PACKET-SHA256SUMS.txt')
assert live_pin() == pin
assert len(read_jsonl(INPUT/'source-current-cells.jsonl')) == 300
assert all('candidateTarget' not in r and 'verdict' not in r and 'disposition' not in r for r in read_jsonl(INPUT/'source-current-cells.jsonl'))
print(json.dumps({'verification':'input-sealed','inputDir':str(INPUT),'head':HEAD,'tree':TREE,'bodySha256':BODY_SHA256,'catalogs':len(cat_rows),'keysPerCatalog':len(ordered_keys),'orderedKeySha256':ordered_hash,'sources':len(selected),'cells':len(source_cells),'callers':sum(r['productionCallerCount'] for r in caller_rows),'callerlessSourceIds':[r['sourceId'] for r in caller_rows if not r['productionCallerCount']],'placeholderSourceCurrentMismatches':sum(not r['placeholderEvidence']['matches'] for r in source_cells),'markupSourceCurrentMismatches':sum(not r['markupEvidence']['matches'] for r in source_cells),'protectedLiterals':sum(len(r['exactProtectedLiterals']) for r in protected_rows),'inputManifestEntriesVerified':len(input_checks),'inputManifestSha256':sha((INPUT/'PACKET-SHA256SUMS.txt').read_bytes()),'containsCandidates':False,'priorEvidenceVerified':prior_checks|{'window52':w52_checks}},ensure_ascii=False,indent=2))
