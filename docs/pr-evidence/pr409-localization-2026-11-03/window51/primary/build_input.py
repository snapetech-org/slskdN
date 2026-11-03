#!/usr/bin/env python3
"""Build exact-head source/current/caller packets for slskdN PR #409 W51."""
from pathlib import Path
import collections, hashlib, json, re, shutil, subprocess

REPO = Path('/mnt/disks/scratch/task-worktrees/localization-20261103/slskdn-pr409-w51-apply-20261103')
OUT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window51-primary-20261103')
BLIND = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window51-blind-input-20261103')
W49 = REPO / 'docs/pr-evidence/pr409-localization-2026-11-03/window49'
W50 = REPO / 'docs/pr-evidence/pr409-localization-2026-11-03/window50'
HEAD = '45664e79a6d9bd41519b674d33464e5f7cb9ce2c'
TREE = 'dc5f6ab2aab3668f674dd583451d3464a3a1c081'
BRANCH = 'codex/slskdn-oidc-tooltip-localization-20261030'
PR = 409
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
CATALOGS = {loc: f'src/web/public/locales/{loc}.json' for loc in LOCALES}
WINDOW = range(176, 201)


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
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def write_jsonl(path, rows):
    with path.open('w', encoding='utf-8', newline='\n') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def verify_sum_file(directory, name):
    checks = []
    for line in (directory / name).read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        expected, rel = line.split(None, 1)
        rel = rel.strip().lstrip('*')
        actual = sha((directory / rel).read_bytes())
        checks.append({'path': rel, 'expected': expected, 'actual': actual, 'matches': expected == actual})
    assert checks and all(x['matches'] for x in checks), (directory, name, checks)
    return checks

def live_pin():
    head = run('git','rev-parse','HEAD').strip()
    tree = run('git','rev-parse','HEAD^{tree}').strip()
    assert head == HEAD and tree == TREE, (head, tree)
    assert not run('git','status','--porcelain=v1').strip(), run('git','status','--short')
    pr = json.loads(run('gh','pr','view',str(PR),'--repo','snapetech-org/slskdN','--json','headRefOid,headRefName,isDraft,state,url'))
    assert pr['state'] == 'OPEN' and pr['isDraft'] is True
    assert pr['headRefOid'] == HEAD and pr['headRefName'] == BRANCH, pr
    branch = run('gh','api',f'repos/snapetech-org/slskdN/branches/{BRANCH.replace("/", "%2F")}','--jq','.commit.sha').strip()
    assert branch == HEAD, branch
    remote = run('git','ls-remote','origin',f'refs/heads/{BRANCH}').strip().split()
    assert len(remote) == 2 and remote[0] == HEAD, remote
    return {'repository':'snapetech-org/slskdN','pullRequest':PR,'url':pr['url'],'state':pr['state'],'isDraft':pr['isDraft'],'branch':BRANCH,'head':HEAD,'tree':TREE,'remoteBranchHead':remote[0],'localWorktreeClean':True}

assert OUT.exists() and set(p.name for p in OUT.iterdir()) == {'build_input.py'} and not BLIND.exists(), 'Task packet path already exists or has unexpected content'
assert shutil.disk_usage(OUT.parent).free > 1_000_000_000
pin = live_pin()
w49_checks = verify_sum_file(W49, 'EVIDENCE-SHA256SUMS.txt')
w50_checks = verify_sum_file(W50, 'EVIDENCE-SHA256SUMS.txt')
w49_inventory_path = W49 / 'primary/source-inventory.jsonl'
w49_inventory = read_jsonl(w49_inventory_path)
w49_summary = json.loads((W49/'primary/selection-and-boundary.json').read_text(encoding='utf-8'))
w50_selection = json.loads((W50/'primary/selection-and-boundary.json').read_text(encoding='utf-8'))
w50_rows = read_jsonl(W50/'primary/selection-boundary.jsonl')
w50_selected = [x for x in w50_rows if x.get('role') == 'selected-W50']
assert len(w50_selected) == 25, len(w50_selected)

# Re-attest current catalog structure and the stable source-ID sequence.
locales = {}
cat_rows = []
ordered_keys = None
for loc, path in CATALOGS.items():
    data = (REPO/path).read_bytes()
    entries = json.loads(data)
    keys = list(entries)
    if ordered_keys is None: ordered_keys = keys
    assert keys == ordered_keys, f'ordered key mismatch in {loc}'
    assert all(isinstance(v, str) and v for v in entries.values()), f'blank/non-string catalog value in {loc}'
    locales[loc] = entries
    blob = run('git','rev-parse',f'{HEAD}:{path}').strip()
    assert git_blob(data) == blob, f'blob mismatch {loc}'
    cat_rows.append({'locale':loc,'catalogPath':path,'bytes':len(data),'sha256':sha(data),'gitBlob':blob,'entryCount':len(entries),'nonemptyValueCount':sum(bool(v) for v in entries.values()),'orderedKeySha256':sha('\n'.join(keys)+'\n')})
assert len(ordered_keys) == 6176
ordered_hash = sha('\n'.join(ordered_keys)+'\n')
assert len({row['orderedKeySha256'] for row in cat_rows}) == 1

source_by_id = {sid(source): source for source in ordered_keys}
assert len(source_by_id) == len(ordered_keys)
rank_rows = {row['continuationRank']: row for row in w49_inventory if row.get('continuationRank') in WINDOW}
assert set(rank_rows) == set(WINDOW), (len(rank_rows), sorted(rank_rows))
selected = [rank_rows[r] for r in WINDOW]
assert len(selected) == 25 and len({x['sourceId'] for x in selected}) == 25
assert all(x['sourceId'] == sid(x['source']) and source_by_id.get(x['sourceId']) == x['source'] for x in selected)

# Verify W50's reviewed IDs and its rank-label basis against W49's stable inventory.
w50_ids = {x['sourceId'] for x in w50_selected}
rank151_175 = {x['sourceId'] for x in w49_inventory if x.get('continuationRank') in range(151,176)}
rank126_150 = {x['sourceId'] for x in w49_inventory if x.get('continuationRank') in range(126,151)}
assert len(rank151_175) == 25 and w50_ids == rank151_175
assert len(rank126_150) == 25 and not (set(x['sourceId'] for x in selected) & (w50_ids | rank126_150))
assert not (set(x['sourceId'] for x in selected) & {x['sourceId'] for x in read_jsonl(W50/'primary/prior-excluded-source-ids.jsonl')})

# Exact quoted production literal search also recognizes JavaScript-escaped
# quotes/backslashes (for example a source string containing \" inside JSX).
quote_re_cache = {}
def js_escape(value, delimiter):
    value = value.replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    return value.replace(delimiter, '\\' + delimiter)
def caller_refs(source):
    if source not in quote_re_cache:
        double = r'"' + re.escape(js_escape(source, '"')) + r'"'
        single = r"'" + re.escape(js_escape(source, "'")) + r"'"
        quote_re_cache[source] = re.compile(r'(?<![A-Za-z0-9_$])(?:' + double + r'|' + single + r')')
    pat = quote_re_cache[source]
    refs = []
    for path in sorted((REPO/'src/web/src').rglob('*')):
        if path.suffix not in {'.js','.jsx','.ts','.tsx'}: continue
        if '.test.' in path.name or '__tests__' in path.parts or path.name.endswith('.test'+path.suffix): continue
        try: content = path.read_bytes(); text = content.decode('utf-8')
        except (OSError, UnicodeDecodeError): continue
        lines = text.splitlines()
        for line_no, line in enumerate(lines,1):
            if not pat.search(line): continue
            rel = str(path.relative_to(REPO))
            head_content = run('git','show',f'{HEAD}:{rel}',text=False)
            assert head_content == content, f'caller does not match pinned tree: {rel}'
            context = [{'line':i+1,'text':lines[i]} for i in range(max(0,line_no-3),min(len(lines),line_no+2))]
            refs.append({'path':rel,'line':line_no,'lineText':line,'lineSha256':sha(line),'context':context,'contextSha256':sha(canonical(context)),'fileBytes':len(content),'fileSha256':sha(content),'gitBlob':run('git','rev-parse',f'{HEAD}:{rel}').strip(),'gitBlobSha1Check':git_blob(content)})
    return refs

caller_rows=[]
caller_map={}
for row in selected:
    refs = caller_refs(row['source'])
    caller_map[row['sourceId']] = refs
    caller_rows.append({'continuationRank':row['continuationRank'],'sourceId':row['sourceId'],'source':row['source'],'sourceSha256':sha(row['source']),'productionCallerCount':len(refs),'callers':refs})

source_cells=[]
for row in selected:
    source = row['source']; source_id = row['sourceId']; refs = caller_map[source_id]
    ref_sha = sha(canonical(refs))
    for loc in LOCALES:
        target = locales[loc][source]
        cat = next(x for x in cat_rows if x['locale']==loc)
        source_cells.append({'continuationRank':row['continuationRank'],'historicalSourceOrdinal':None,'sourceId':source_id,'source':source,'sourceSha256':sha(source),'locale':loc,'catalogPath':CATALOGS[loc],'catalogFileSha256':cat['sha256'],'catalogGitBlob':cat['gitBlob'],'currentTarget':target,'currentTargetSha256':sha(target),'callerContextSha256':ref_sha,'callerRefs':[{'path':r['path'],'line':r['line'],'lineSha256':r['lineSha256'],'fileSha256':r['fileSha256'],'gitBlob':r['gitBlob']} for r in refs]})
assert len(source_cells)==300

byrank={r['continuationRank']:r for r in w49_inventory}
selection_rows=[]
for rank in sorted(WINDOW):
    r=byrank[rank]
    selection_rows.append({'role':'selected-W51','continuationRank':rank,'sourceId':r['sourceId'],'source':r['source'],'sourceSha256':r['sourceSha256'],'historicalSourceOrdinal':None,'w49RemainingQueueRank':r['remainingQueueRank']})
previous=byrank[175]; following=byrank[201]
sequence_note={
 'w50PacketHead':'7a415b975bf0c783e3a91a9e3bab63bb7fd9e443',
 'w50PacketTree':'12b1a85af7c036dc3716d2730dfef0fa18a220a8',
 'w50AppliedHead':HEAD,
 'w50PacketDeclaredWindow':'continuation ranks 126-150',
 'w50SelectedIdsAsRankedInW49Inventory':'151-175',
 'w50DeclaredRank151NextBoundarySourceId':w50_selection['nextBoundary']['sourceId'],
 'w50NextBoundaryAsRankedInW49Inventory':176,
 'resolution':'Preserve W50 historical packets unchanged. Continue from the exact W49 stable-ID inventory sequence; W51 uses ranks 176-200, beginning at the W50 next-boundary ID. W50 declared rank labels used a different rank basis.'
}
selection={
 'repository':'snapetech-org/slskdN','pullRequest':PR,'pullRequestUrl':pin['url'],'pins':pin,
 'window':'W51 continuation of the exact W49 stable-ID inventory: ranks 176-200; historical source ordinals unavailable and not claimed',
 'localeOrder':LOCALES,'localeCount':12,'sourceCount':25,'cellCount':300,'catalogSourceCount':len(ordered_keys),'orderedCatalogKeySha256':ordered_hash,
 'sourceSequenceBasis':'W49 primary source-inventory.jsonl, re-attested against W51 current catalog keys; selected stable-ID rows at continuationRank 176-200',
 'previousBoundary':{'continuationRank':175,'sourceId':previous['sourceId'],'source':previous['source'],'sourceSha256':previous['sourceSha256']},
 'firstSelected':selection_rows[0],'lastSelected':selection_rows[-1],
 'nextBoundary':{'continuationRank':201,'sourceId':following['sourceId'],'source':following['source'],'sourceSha256':following['sourceSha256']},
 'w50RankBasisReconciliation':sequence_note,
 'disjointness':{'w49SelectedCount':25,'w50SelectedCount':25,'w51SelectedCount':25,'w51DisjointFromW49':True,'w51DisjointFromW50':True,'w51DisjointFromW50PriorExclusions':True,'w50SelectedIdsMatchW49InventoryRanks151To175':True},
 'priorEvidenceChecksums':{'w49EvidenceEntriesVerified':len(w49_checks),'w50EvidenceEntriesVerified':len(w50_checks),'w49EvidenceManifestSha256':sha((W49/'EVIDENCE-SHA256SUMS.txt').read_bytes()),'w50EvidenceManifestSha256':sha((W50/'EVIDENCE-SHA256SUMS.txt').read_bytes()),'w49SourceInventorySha256':sha(w49_inventory_path.read_bytes()),'w50SelectionBoundarySha256':sha((W50/'primary/selection-boundary.jsonl').read_bytes())}
}

OUT.mkdir(exist_ok=True)
BLIND.mkdir()
(OUT/'primary').mkdir(); (BLIND/'input').mkdir()
write_jsonl(OUT/'primary/catalog-structure.jsonl',cat_rows)
write_jsonl(OUT/'primary/caller-contexts.jsonl',caller_rows)
write_jsonl(OUT/'primary/source-current-cells.jsonl',source_cells)
write_jsonl(OUT/'primary/selection-boundary.jsonl',selection_rows)
write_json(OUT/'primary/selection-and-boundary.json',selection)
# Blind input deliberately excludes primary decisions, candidate translations, and adjudication.
write_jsonl(BLIND/'input/catalog-structure.jsonl',cat_rows)
write_jsonl(BLIND/'input/caller-contexts.jsonl',caller_rows)
write_jsonl(BLIND/'input/source-current-cells.jsonl',source_cells)
write_jsonl(BLIND/'input/selection-boundary.jsonl',selection_rows)
write_json(BLIND/'input/head-tree-attestation.json',pin)

worksheet=['# W51 source/current worksheet','',f"Pinned PR head/tree: `{HEAD}` / `{TREE}`.", 'Stable-ID ranks follow the re-attested W49 source inventory, ranks 176-200. Historical source ordinals are unavailable.']
for row in selected:
    refs=caller_map[row['sourceId']]
    worksheet += ['',f"## Rank {row['continuationRank']} — `{row['sourceId']}`", '',f"**English:** {row['source']}",'','**Pinned production callers:**']
    if refs:
        for ref in refs: worksheet.append(f"- `{ref['path']}:{ref['line']}`: {ref['lineText']}")
    else: worksheet.append('- None found in the bounded source scan; translation proposals require conservative handling.')
    worksheet += ['', '| Locale | Current target |', '|---|---|']
    for loc in LOCALES: worksheet.append(f"| {loc} | {locales[loc][row['source']]} |")
(OUT/'primary/review-worksheet.md').write_text('\n'.join(worksheet)+'\n',encoding='utf-8')

blind_readme=(f"""# slskdN PR #409 W51 blind-review input\n\nPinned live PR head/tree: `{HEAD}` / `{TREE}`. The packet contains 25 stable source IDs at exact continuation ranks 176–200, all 12 current locale targets, and source/caller/catalog hash pins. Review each source and locale independently for meaning, caller context, register, fluency, placeholder/markup safety, and protected product/API literals. Record one disposition for every sourceId/locale pair: accept-current, correction, refinement, or hold-context. Do not infer historical extraction ordinals or claim native-speaker approval.\n\nFiles in `input/` are source/current/caller evidence only; no primary candidate or disposition data is included. The W50 historical rank-basis note is intentionally omitted from this review input to avoid influencing independent judgment; the source ID set itself is exact and fixed.\n""")
(BLIND/'README.md').write_text(blind_readme,encoding='utf-8')

# Hash manifests cover their respective packet directories, excluding the manifest itself.
def manifest(directory, path):
    rows=[]
    for p in sorted(x for x in directory.rglob('*') if x.is_file() and x != path):
        rows.append(f"{sha(p.read_bytes())}  {p.relative_to(directory).as_posix()}")
    path.write_text('\n'.join(rows)+'\n',encoding='utf-8')
manifest(OUT/'primary',OUT/'primary/SHA256SUMS.txt')
manifest(BLIND,BLIND/'PACKET-SHA256SUMS.txt')

# Re-attest exact pin after packet generation; no repo mutations occur in this script.
assert live_pin() == pin
print(json.dumps({'primaryDir':str(OUT),'blindDir':str(BLIND),'head':HEAD,'tree':TREE,'catalogs':len(cat_rows),'catalogKeys':len(ordered_keys),'orderedKeySha256':ordered_hash,'sources':len(selected),'cells':len(source_cells),'callerCount':sum(x['productionCallerCount'] for x in caller_rows),'callerlessSourceIds':[x['sourceId'] for x in caller_rows if x['productionCallerCount']==0],'w49EvidenceFilesVerified':len(w49_checks),'w50EvidenceFilesVerified':len(w50_checks),'selectedFirst':selection_rows[0],'selectedLast':selection_rows[-1],'w50RankBasisReconciliation':sequence_note},ensure_ascii=False,indent=2))
