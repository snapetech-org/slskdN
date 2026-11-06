#!/usr/bin/env python3
"""Build sealed candidate-free exact-head input for slskdN PR #409 W55."""
from pathlib import Path
import collections, hashlib, json, re, shutil, subprocess

REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261103/slskdn-pr409-w52-primary-20261103')
OUT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w55-primary-20261103')
INPUT=OUT/'input'
BASE=REPO/'docs/pr-evidence/pr409-localization-2026-11-03'
W49=BASE/'window49'; W50=BASE/'window50'; W51=BASE/'window51'; W52=BASE/'window52'; W53=BASE/'window53'; W54=BASE/'window54'
HEAD='6a46b8f1dc87d899308fee141fa0db392e49e098'
TREE='a22e9a896aae12aa89a1502d9748b12816d491ed'
BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
PR=409
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
CATALOGS={loc:f'src/web/public/locales/{loc}.json' for loc in LOCALES}
WINDOW=range(276,301)
PH=re.compile(r'\{[^{}]+\}')
MARKUP=re.compile(r'</?[A-Za-z][^>]*>')
NUMBER=re.compile(r'(?<![A-Za-z])\d+(?:[.,]\d+)?%?(?![A-Za-z])')
PROTECTED={
 278:[{'literal':'DHT','kind':'protocol name','policy':'Preserve exact uppercase spelling.'}],
 283:[{'literal':'Lidarr','kind':'application name','policy':'Preserve exact spelling and case.'}],
 287:[{'literal':'DR','kind':'audio dynamic-range abbreviation','policy':'Preserve exact uppercase spelling; do not expand or confuse with data rate.'}],
 288:[{'literal':'0.1, -0.2, 0.3, ...','kind':'comma-separated audio-sample parser example','policy':'Preserve this exact sequence and decimal points; the caller splits sample input on commas.'}],
 295:[{'literal':'Demucs','kind':'source-separation model/product name','policy':'Preserve exact spelling and case.'}],
 300:[{'literal':'|','kind':'metadata separator','policy':'Preserve the separator in concatenated report text.'}],
}
SEMANTIC_TERMS={
 278:[{'term':'Pod object; DHT workflow','basis':'MediaCore DHT pod metadata feature; product glossary has no approved localized noun for Pod, so evaluate whether the target requires terminology hold.'}],
 280:[{'term':'track neighborhood; alternatives; segment ambiguity','basis':'Preserve the artist neighborhood, alternative candidates, and segment-level ambiguity context; use the exact caller to identify the UI function.'}],
 282:[{'term':'Pod; VPN gateway capability; port forwarding','basis':'Preserve the capability requirement and conditional port-forwarding consequence; Pod glossary decision remains unresolved.'}],
 283:[{'term':'Lidarr wanted synchronization setting','basis':'Treat Lidarr as the application name and wanted as its desired/requested media state, not an ordinary adjective.'}],
 287:[{'term':'lossless versus lossy source; DR threshold','basis':'In audio-quality analysis DR denotes dynamic range; retain direction and the formatted threshold placeholder.'}],
 288:[{'term':'normalized signal values','basis':'Preserve signed values, decimal precision, ellipsis, and normalized range exactly.'}],
 289:[{'term':'Pod ID and Peer ID','basis':'Two distinct identifiers in a MediaCore pod/peer workflow; Pod object noun remains unresolved.'}],
 291:[{'term':'import path source','basis':'Fragment used in a selector; preserve that this is a source/from choice rather than a destination.'}],
 292:[{'term':'estimated false-positive metric','basis':'Short label; confirm caller shows this is an estimated false-positive measure.'}],
 295:[{'term':'Demucs stems','basis':'Audio source-separation output category; keep stems as separated audio tracks, not botanical stems.'}],
 297:[{'term':'daemon-reported values','basis':'Preserve discard/restore semantics and the daemon as authoritative reported state.'}],
 300:[{'term':'album metadata suffix','basis':'Preserve the literal leading separator/space and the Album label before the album placeholder.'}],
}

def run(*args,cwd=REPO,text=True): return subprocess.check_output(list(args),cwd=cwd,text=text)
def sha(v): return hashlib.sha256(v.encode('utf-8') if isinstance(v,str) else v).hexdigest()
def blob(data): return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
def canonical(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def read_jsonl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def write_json(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_jsonl(p,rows): p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
def verify_manifest(d,name):
  p=d/name; checks=[]
  for line in p.read_text(encoding='utf-8').splitlines():
    if not line.strip(): continue
    h,rel=line.split(None,1); rel=rel.strip().lstrip('*'); actual=sha((d/rel).read_bytes()); checks.append({'path':rel,'expected':h,'actual':actual,'matches':h==actual})
  assert checks and all(x['matches'] for x in checks),(p,checks)
  return checks
def write_manifest(d,name):
  p=d/name; rows=[]
  for f in sorted(x for x in d.rglob('*') if x.is_file() and x!=p): rows.append(f'{sha(f.read_bytes())}  {f.relative_to(d).as_posix()}')
  p.write_text('\n'.join(rows)+'\n',encoding='utf-8')
def live_pin():
  head=run('git','rev-parse','HEAD').strip(); tree=run('git','rev-parse','HEAD^{tree}').strip()
  assert (head,tree)==(HEAD,TREE),(head,tree)
  assert not run('git','status','--porcelain=v1').strip(),run('git','status','--short')
  pr=json.loads(run('gh','pr','view',str(PR),'--repo','snapetech-org/slskdN','--json','body,headRefOid,headRefName,isDraft,state,url'))
  body=sha(pr['body'])
  assert pr['state']=='OPEN' and pr['isDraft'] is True and pr['headRefOid']==HEAD and pr['headRefName']==BRANCH,(pr['state'],pr['isDraft'],pr['headRefOid'],pr['headRefName'])
  remote=run('git','ls-remote','origin',f'refs/heads/{BRANCH}').strip().split()
  assert len(remote)==2 and remote[0]==HEAD,remote
  return {'repository':'snapetech-org/slskdN','pullRequest':PR,'url':pr['url'],'state':pr['state'],'isDraft':pr['isDraft'],'branch':BRANCH,'head':HEAD,'tree':TREE,'remoteBranchHead':remote[0],'bodySha256':body,'localWorktreeClean':True}

def js_escape(s,q): return s.replace('\\','\\\\').replace('\n','\\n').replace('\r','\\r').replace('\t','\\t').replace(q,'\\'+q)
assert not INPUT.exists()
assert set(x.name for x in OUT.iterdir())=={'build_input.py'}
assert shutil.disk_usage(OUT.parent).free>1_000_000_000
pin=live_pin()

# Verify prior frozen evidence, then map all selected windows back to W49 ranks.
prior_checks={}
for folder in (W49,W50,W51):
  c=verify_manifest(folder,'EVIDENCE-SHA256SUMS.txt'); prior_checks[folder.name]={'entriesVerified':len(c),'manifestSha256':sha((folder/'EVIDENCE-SHA256SUMS.txt').read_bytes())}
for folder,manifest in [(W52,'SHA256SUMS.txt'),(W53,'SHA256SUMS.txt'),(W54,'SHA256SUMS.txt')]:
  c=verify_manifest(folder,manifest); prior_checks[folder.name]={'entriesVerified':len(c),'manifestSha256':sha((folder/manifest).read_bytes())}
  for mf in sorted(x for x in folder.rglob('*') if x.is_file() and 'SHA256SUMS' in x.name and x.name!=manifest):
    c=verify_manifest(mf.parent,mf.name); prior_checks[folder.name][mf.relative_to(folder).as_posix()]={'entriesVerified':len(c),'manifestSha256':sha(mf.read_bytes())}
inventory_path=W49/'primary/source-inventory.jsonl'; inventory=read_jsonl(inventory_path)
by_rank={r['continuationRank']:r for r in inventory if isinstance(r.get('continuationRank'),int)}
assert all(r in by_rank for r in range(101,302))
assert sha(inventory_path.read_bytes())=='17cb8a747939d4973733016b95f29284e191d5444910051e42fb153cf4f94225'
assert all(by_rank[r].get('excluded') is False for r in WINDOW)
assert all(by_rank[r].get('inW49') is False for r in WINDOW)
selected=[by_rank[r] for r in WINDOW]
assert len(selected)==25 and len({r['sourceId'] for r in selected})==25
assert all('src_'+sha(r['source'])[:16]==r['sourceId'] and sha(r['source'])==r['sourceSha256'] for r in selected)

def selected_ids(folder, candidates, all_rows=False):
  for rel in candidates:
    p=folder/rel
    if p.exists():
      rows=read_jsonl(p) if p.suffix=='.jsonl' else []
      if rows:
        return {r['sourceId'] for r in rows if all_rows or str(r.get('role','')).startswith('selected-') or r.get('selected') is True}
  raise AssertionError(f'no selected ID list in {folder}')
prior_windows={
 'W49':(W49,['primary/selection-boundary.jsonl'],range(101,126),True),
 'W50':(W50,['primary/selection-boundary.jsonl'],range(151,176),False),
 'W51':(W51,['primary/selection-boundary.jsonl'],range(176,201),False),
 'W52':(W52,['input/input/selection-boundary.jsonl','primary/selection-boundary.jsonl'],range(201,226),False),
 'W53':(W53,['review/input/selection-boundary.jsonl'],range(226,251),False),
 'W54':(W54,['review/input/selection-boundary.jsonl'],range(251,276),False),
}
prior_union=set(); window_checks={}
for name,(folder,paths,ranks,all_rows) in prior_windows.items():
  ids=selected_ids(folder,paths,all_rows); expected={by_rank[r]['sourceId'] for r in ranks}
  assert ids==expected,(name,len(ids),sorted((next((x.get('continuationRank') for x in inventory if x['sourceId']==i),None),i) for i in ids))
  window_checks[name]={'selectedCount':len(ids),'mappedRankStart':min(ranks),'mappedRankEnd':max(ranks),'matchesPinnedInventory':True}
  prior_union |= ids
w49_gap={by_rank[r]['sourceId'] for r in range(126,151)}
selected_ids_w55={r['sourceId'] for r in selected}
assert not selected_ids_w55 & prior_union and not selected_ids_w55 & w49_gap
assert len(prior_union)==150

# Reattest all current catalogs against the exact PR tree.
locales={}; catalog_rows=[]; ordered=None
for loc,path in CATALOGS.items():
  data=(REPO/path).read_bytes(); doc=json.loads(data); keys=list(doc)
  if ordered is None: ordered=keys
  assert keys==ordered and all(isinstance(v,str) and v for v in doc.values())
  git_blob=run('git','rev-parse',f'{HEAD}:{path}').strip(); assert blob(data)==git_blob
  locales[loc]=doc
  catalog_rows.append({'locale':loc,'catalogPath':path,'bytes':len(data),'sha256':sha(data),'gitBlob':git_blob,'entryCount':len(doc),'nonemptyValueCount':sum(bool(v) for v in doc.values()),'orderedKeySha256':sha('\n'.join(keys)+'\n')})
assert len(ordered)==6176
ordered_hash=sha('\n'.join(ordered)+'\n')
assert all(c['orderedKeySha256']==ordered_hash for c in catalog_rows)
source_by_id={'src_'+sha(s)[:16]:s for s in ordered}; assert len(source_by_id)==len(ordered)
assert all(source_by_id.get(r['sourceId'])==r['source'] for r in selected)

# Exact quoted-literal caller scan bounded to production JS/TS source.
quote_cache={}
def caller_refs(source):
  if source not in quote_cache:
    dq='"'+re.escape(js_escape(source,'"'))+'"'; sq="'"+re.escape(js_escape(source,"'"))+"'"
    quote_cache[source]=re.compile(r'(?<![A-Za-z0-9_$])(?:'+dq+'|'+sq+r')')
  pat=quote_cache[source]; refs=[]
  for path in sorted((REPO/'src/web/src').rglob('*')):
    if path.suffix not in {'.js','.jsx','.ts','.tsx'}: continue
    if '.test.' in path.name or '__tests__' in path.parts: continue
    try: data=path.read_bytes(); text=data.decode('utf-8')
    except (OSError,UnicodeDecodeError): continue
    lines=text.splitlines()
    for n,line in enumerate(lines,1):
      if not pat.search(line): continue
      rel=path.relative_to(REPO).as_posix(); assert run('git','show',f'{HEAD}:{rel}',text=False)==data,(rel,'not at pinned tree')
      context=[{'line':i+1,'text':lines[i]} for i in range(max(0,n-3),min(len(lines),n+3))]
      refs.append({'path':rel,'line':n,'lineText':line,'lineSha256':sha(line),'context':context,'contextSha256':sha(canonical(context)),'fileBytes':len(data),'fileSha256':sha(data),'gitBlob':run('git','rev-parse',f'{HEAD}:{rel}').strip(),'gitBlobSha1Check':blob(data)})
  return refs
caller_rows=[]; caller_map={}
for r in selected:
  refs=caller_refs(r['source']); caller_map[r['sourceId']]=refs
  caller_rows.append({'continuationRank':r['continuationRank'],'sourceId':r['sourceId'],'source':r['source'],'sourceSha256':sha(r['source']),'productionCallerCount':len(refs),'boundedScan':'exact quoted literal search in src/web/src JavaScript/TypeScript production files; tests excluded','callers':refs})

protected_rows=[]; source_cells=[]
for r in selected:
  rank=r['continuationRank']; source=r['source']; sid=r['sourceId']; refs=caller_map[sid]; refsha=sha(canonical(refs)); literals=PROTECTED.get(rank,[])
  protected_rows.append({'continuationRank':rank,'sourceId':sid,'source':source,'sourceSha256':sha(source),'exactProtectedLiterals':literals,'semanticTerms':SEMANTIC_TERMS.get(rank,[]),'callerContextSha256':refsha})
  sph=collections.Counter(PH.findall(source)); smark=collections.Counter(MARKUP.findall(source)); snum=NUMBER.findall(source)
  for loc in LOCALES:
    target=locales[loc][source]; cat=next(c for c in catalog_rows if c['locale']==loc)
    protected_checks=[{'literal':x['literal'],'kind':x['kind'],'policy':x['policy'],'sourcePresent':x['literal'] in source,'currentPresent':x['literal'] in target} for x in literals]
    source_cells.append({'continuationRank':rank,'historicalSourceOrdinal':None,'sourceId':sid,'source':source,'sourceSha256':sha(source),'locale':loc,'catalogPath':CATALOGS[loc],'catalogFileSha256':cat['sha256'],'catalogGitBlob':cat['gitBlob'],'currentTarget':target,'currentTargetSha256':sha(target),'callerContextSha256':refsha,'callerRefs':[{'path':x['path'],'line':x['line'],'lineSha256':x['lineSha256'],'fileSha256':x['fileSha256'],'gitBlob':x['gitBlob']} for x in refs],'placeholderEvidence':{'sourceTokens':dict(sph),'currentTokens':dict(collections.Counter(PH.findall(target))),'matches':sph==collections.Counter(PH.findall(target))},'markupEvidence':{'sourceTags':dict(smark),'currentTags':dict(collections.Counter(MARKUP.findall(target))),'matches':smark==collections.Counter(MARKUP.findall(target))},'sourceNumericTokens':snum,'currentNumericTokens':NUMBER.findall(target),'protectedLiteralChecks':protected_checks})
assert len(source_cells)==300 and len(caller_rows)==25 and len(protected_rows)==25
assert all(not any(k in r for k in ('candidateTarget','verdict','disposition')) for r in source_cells)

boundary=[]
for rank,role in [(275,'previous-boundary-W54'),*[(r,'selected-W55') for r in WINDOW],(301,'next-boundary-W56')]:
  assert rank in by_rank
  x=by_rank[rank]; boundary.append({'role':role,'continuationRank':rank,'sourceId':x['sourceId'],'source':x['source'],'sourceSha256':x['sourceSha256'],'historicalSourceOrdinal':None})
selection={'repository':'snapetech-org/slskdN','pullRequest':PR,'pullRequestUrl':pin['url'],'pins':pin,'window':'W55 continuation of the W49 stable-ID inventory: ranks 276-300; historical source ordinals unavailable and not claimed','rankBasis':'Pinned W49 primary source-inventory.jsonl, re-attested against exact-head current catalog keys. W49 reviewed IDs map to ranks 101-125; the reserved W49 gap 126-150 remains excluded/unreviewed; W50-W54 reviewed IDs map to ranks 151-275. W55 selects the next 25 unexcluded IDs at ranks 276-300.','localeOrder':LOCALES,'localeCount':len(LOCALES),'sourceCount':len(selected),'cellCount':len(source_cells),'catalogSourceCount':len(ordered),'orderedCatalogKeySha256':ordered_hash,'previousBoundary':boundary[0],'firstSelected':boundary[1],'lastSelected':boundary[-2],'nextBoundary':boundary[-1],'disjointness':{'w49Reviewed':window_checks['W49']['selectedCount'],'w49Gap126To150':len(w49_gap),'w50Selected':window_checks['W50']['selectedCount'],'w51Selected':window_checks['W51']['selectedCount'],'w52Selected':window_checks['W52']['selectedCount'],'w53Selected':window_checks['W53']['selectedCount'],'w54Selected':window_checks['W54']['selectedCount'],'w55Selected':len(selected_ids_w55),'w55DisjointFromAllPriorReviewed':not bool(selected_ids_w55&prior_union),'w55DisjointFromW49Gap':not bool(selected_ids_w55&w49_gap),'priorRankMaps':window_checks},'priorEvidenceChecks':prior_checks|{'w49SourceInventorySha256':sha(inventory_path.read_bytes())},'inputContainsCandidates':False}
OUT.mkdir(exist_ok=True); INPUT.mkdir()
write_json(INPUT/'head-tree-attestation.json',pin); write_json(INPUT/'selection-and-boundary.json',selection)
write_jsonl(INPUT/'selection-boundary.jsonl',boundary); write_jsonl(INPUT/'catalog-structure.jsonl',catalog_rows); write_jsonl(INPUT/'caller-contexts.jsonl',caller_rows); write_jsonl(INPUT/'source-current-cells.jsonl',source_cells); write_jsonl(INPUT/'protected-literals.jsonl',protected_rows)
readme=(f"# slskdN PR #409 W55 candidate-free input packet\n\nExact live PR pin: head `{HEAD}`, tree `{TREE}`, branch `{BRANCH}`; PR #409 was open and draft at capture. PR body SHA-256: `{pin['bodySha256']}`.\n\n"
 f"W55 selects the next 25 stable IDs in the pinned W49 inventory, ranks 276–300, across all 12 direct locale catalogs (300 source/locale cells). Historical extraction ordinals are unavailable and are not claimed. W54 ends at rank 275; W56 begins at rank 301. W49 reviewed ranks 101–125 and W50–W54 reviewed ranks 151–275 are excluded by stable ID. The reserved W49 gap 126–150 remains unreviewed and excluded.\n\n"
 "The input contains current values only, exact catalog file/Git blob pins, source/current hashes, bounded production caller contexts with file/line/blob hashes, placeholders, markup, numeric tokens, and protected-literal checks. It contains no candidate translations, verdicts, dispositions, or adjudication. Primary review is stored separately after this packet was sealed.\n")
(INPUT/'README.md').write_text(readme,encoding='utf-8'); write_manifest(INPUT,'PACKET-SHA256SUMS.txt')
checks=verify_manifest(INPUT,'PACKET-SHA256SUMS.txt'); assert live_pin()==pin
assert len(read_jsonl(INPUT/'source-current-cells.jsonl'))==300
print(json.dumps({'verification':'input-sealed','inputDir':str(INPUT),'head':HEAD,'tree':TREE,'prBodySha256':pin['bodySha256'],'sources':len(selected),'cells':len(source_cells),'callers':sum(x['productionCallerCount'] for x in caller_rows),'callerlessSourceIds':[x['sourceId'] for x in caller_rows if not x['productionCallerCount']],'catalogs':len(catalog_rows),'catalogKeys':len(ordered),'orderedCatalogKeySha256':ordered_hash,'previousBoundary':boundary[0],'firstSelected':boundary[1],'lastSelected':boundary[-2],'nextBoundary':boundary[-1],'inputManifestEntriesVerified':len(checks),'inputManifestSha256':sha((INPUT/'PACKET-SHA256SUMS.txt').read_bytes()),'containsCandidates':False,'priorRankMaps':window_checks,'priorEvidenceChecks':prior_checks},ensure_ascii=False,indent=2))
