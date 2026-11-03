import hashlib, json, pathlib, subprocess

REPO=pathlib.Path('/mnt/disks/scratch/task-worktrees/localization-20261103/slskdn-pr409-w56-apply-20261103')
AUDIT=pathlib.Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w58-third-party-cross-audit-20261103')
OUT=pathlib.Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w58-apply-20261103')
APP=OUT/'application'
HEAD='47735fbdb8df3de8dc5fd297c2717dc332764431'
TREE='b29397903a036d40af1c6551dedbe070e735cfed'
assert not OUT.exists(), f'refusing to overwrite {OUT}'

def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args])
def sha(b): return hashlib.sha256(b).hexdigest()
def shat(s): return sha(s.encode('utf-8'))
def canonical(v): return json.dumps(v,ensure_ascii=False,separators=(',',':'),sort_keys=True)
assert git('rev-parse','HEAD').decode().strip()==HEAD
assert git('rev-parse','HEAD^{tree}').decode().strip()==TREE
assert not git('status','--porcelain').decode().strip(), 'apply worktree must be clean'
summary=json.loads((AUDIT/'summary.json').read_text())
assert summary['cellCount']==300 and summary['selectedTargetChangesFromCurrent']==58
rows=[json.loads(line) for line in (AUDIT/'reconciliation-ledger.jsonl').read_text().splitlines() if line]
assert len(rows)==300
assert all(r['head']==HEAD and r['tree']==TREE for r in rows)
assert not any(r.get('finalDisposition')=='hold' for r in rows)
assert sum(r.get('selectedTargetSha256')!=r.get('currentTargetSha256') for r in rows)==58
file_rows={}
for row in rows:
    path=row['catalogPath']; file_rows.setdefault(path,[]).append(row)
for path,items in file_rows.items():
    raw=git('show',f'HEAD:{path}')
    assert all(x['catalogFileSha256']==sha(raw) for x in items), f'catalog hash mismatch at {path}'
    assert all(x['catalogGitBlob']==git('rev-parse',f'HEAD:{path}').decode().strip() for x in items)
    data=json.loads(raw)
    assert len(data)==6176 and len(items)==25
    assert all(x['source'] in data for x in items)
    assert all(data[x['source']]==x['currentTarget'] for x in items)
    assert all(shat(data[x['source']])==x['currentTargetSha256'] for x in items)

plan=[]
changes_by_file={}
for row in rows:
    target=row['selectedTarget']; target_hash=row['selectedTargetSha256']
    assert target is not None and shat(target)==target_hash
    changed=target_hash!=row['currentTargetSha256']
    item={'continuationRank':row['continuationRank'],'sourceId':row['sourceId'],'locale':row['locale'],'catalogPath':row['catalogPath'],'source':row['source'],'currentTarget':row['currentTarget'],'currentTargetSha256':row['currentTargetSha256'],'selectedTarget':target,'selectedTargetSha256':target_hash,'disposition':row['finalDisposition'],'changed':changed}
    plan.append(item)
    if changed:
        changes_by_file.setdefault(row['catalogPath'],[]).append(row)
assert sum(x['changed'] for x in plan)==58 and len(changes_by_file)==12

# Replace only JSON string values for audited English-source keys, preserving other bytes.
decoder=json.JSONDecoder()
for path,items in changes_by_file.items():
    raw=git('show',f'HEAD:{path}').decode('utf-8')
    lines=raw.splitlines(keepends=True)
    for row in items:
        matched=[]
        for index,line in enumerate(lines):
            stripped=line.lstrip()
            indent=len(line)-len(stripped)
            try:
                key,key_end=decoder.raw_decode(stripped)
            except json.JSONDecodeError:
                continue
            if key!=row['source']:
                continue
            cursor=indent+key_end
            if cursor>=len(line) or line[cursor]!=':':
                continue
            cursor+=1
            while cursor<len(line) and line[cursor].isspace():
                cursor+=1
            old,old_end=decoder.raw_decode(line,cursor)
            if old!=row['currentTarget']:
                raise SystemExit(f'{path}: current target differs at {row["sourceId"]}')
            suffix=line[old_end:]
            if suffix.strip() not in {',',''}:
                raise SystemExit(f'{path}: unexpected JSON line suffix for {row["sourceId"]}: {suffix!r}')
            lines[index]=line[:cursor]+json.dumps(row['selectedTarget'],ensure_ascii=False)+suffix
            matched.append(index)
        if len(matched)!=1:
            raise SystemExit(f'{path}: expected one key for source {row["source"]!r}, found {len(matched)}')
    edited=''.join(lines)
    parsed=json.loads(edited)
    base=json.loads(raw)
    assert list(parsed)==list(base), f'key order changed: {path}'
    intended={row['source'] for row in items}
    assert {key for key in base if base[key]!=parsed[key]}==intended, f'non-target changes in {path}'
    for row in items:
        assert parsed[row['source']]==row['selectedTarget']
    (REPO/path).write_text(edited,encoding='utf-8')

OUT.mkdir(parents=True)
APP.mkdir(parents=True)
(APP/'apply-plan.jsonl').write_text(''.join(canonical(x)+'\n' for x in plan),encoding='utf-8')
readback=[]
for row in rows:
    data=json.loads((REPO/row['catalogPath']).read_text())
    actual=data[row['source']]
    item={'continuationRank':row['continuationRank'],'sourceId':row['sourceId'],'locale':row['locale'],'catalogPath':row['catalogPath'],'expectedTarget':row['selectedTarget'],'expectedTargetSha256':row['selectedTargetSha256'],'actualTarget':actual,'actualTargetSha256':shat(actual),'matches':actual==row['selectedTarget'] and shat(actual)==row['selectedTargetSha256']}
    readback.append(item)
assert len(readback)==300 and all(x['matches'] for x in readback)
(APP/'readback.jsonl').write_text(''.join(canonical(x)+'\n' for x in readback),encoding='utf-8')
summary_out={'repository':'snapetech-org/slskdN','pullRequest':409,'baseHead':HEAD,'baseTree':TREE,'reviewedCells':300,'sourceCount':25,'localeCount':12,'finalDispositionCounts':summary['finalDispositionCounts'],'changedTargets':58,'changedCatalogFiles':len(changes_by_file),'changedSourceIds':sorted({r['sourceId'] for rr in changes_by_file.values() for r in rr}),'readbackRows':len(readback),'readbackMismatches':sum(not x['matches'] for x in readback),'nonTargetChanges':0,'orderedKeyCounts':{path:6176 for path in file_rows}}
(APP/'summary.json').write_text(json.dumps(summary_out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary_out,ensure_ascii=False,indent=2))
