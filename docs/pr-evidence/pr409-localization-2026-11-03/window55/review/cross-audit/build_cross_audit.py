#!/usr/bin/env python3
"""Pin and reconcile W55 primary and independent blind reviews."""
from pathlib import Path
import collections, hashlib, json, re, subprocess
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261103/slskdn-pr409-w52-primary-20261103')
PRIMARY_ROOT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w55-primary-20261103')
BLIND_ROOT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w55-independent-blind-20261103')
OUT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w55-third-party-cross-audit-20261103')
INPUT=PRIMARY_ROOT/'input'; PRIMARY=PRIMARY_ROOT/'primary'; BLIND=BLIND_ROOT/'blind-review-ledger.jsonl'
HEAD='6a46b8f1dc87d899308fee141fa0db392e49e098'; TREE='a22e9a896aae12aa89a1502d9748b12816d491ed'; BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PH=re.compile(r'\{[^{}]+\}'); MARKUP=re.compile(r'</?[A-Za-z][^>]*>'); NUMBER=re.compile(r'(?<![A-Za-z])\d+(?:[.,]\d+)?%?(?![A-Za-z])')
def run(*args,text=True): return subprocess.check_output(list(args),cwd=REPO,text=text)
def sha(v): return hashlib.sha256(v.encode('utf-8') if isinstance(v,str) else v).hexdigest()
def blob(v): return hashlib.sha1(b'blob '+str(len(v)).encode()+b'\0'+v).hexdigest()
def canonical(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def read_json(p): return json.loads(p.read_text(encoding='utf-8'))
def read_jsonl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def write_json(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_jsonl(p,rows): p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
def verify_manifest(directory,name):
 path=directory/name; rows=[]
 for line in path.read_text(encoding='utf-8').splitlines():
  if not line.strip(): continue
  expected,rel=line.split(None,1); rel=rel.strip().lstrip('*'); actual=sha((directory/rel).read_bytes()); rows.append({'path':rel,'expected':expected,'actual':actual,'matches':expected==actual})
 assert rows and all(x['matches'] for x in rows),(path,rows)
 return rows
def write_manifest(directory,name):
 manifest=directory/name; rows=[]
 for f in sorted(x for x in directory.rglob('*') if x.is_file() and x!=manifest): rows.append(f'{sha(f.read_bytes())}  {f.relative_to(directory).as_posix()}')
 manifest.write_text('\n'.join(rows)+'\n',encoding='utf-8')

assert not (OUT/'cross-audit-ledger.jsonl').exists()
assert run('git','rev-parse','HEAD').strip()==HEAD and run('git','rev-parse','HEAD^{tree}').strip()==TREE
assert not run('git','status','--porcelain=v1').strip(),run('git','status','--short')
pr=json.loads(run('gh','pr','view','409','--repo','snapetech-org/slskdN','--json','body,headRefName,headRefOid,isDraft,state,url'))
body_sha=sha(pr['body']); assert pr['state']=='OPEN' and pr['isDraft'] is True and pr['headRefName']==BRANCH and pr['headRefOid']==HEAD
remote=run('git','ls-remote','origin',f'refs/heads/{BRANCH}').split(); assert len(remote)==2 and remote[0]==HEAD

# Verify each sealed parent packet at its own manifest root.
primary_root_checks=verify_manifest(PRIMARY_ROOT,'SHA256SUMS.txt')
input_checks=verify_manifest(INPUT,'PACKET-SHA256SUMS.txt')
primary_checks=verify_manifest(PRIMARY,'SHA256SUMS.txt')
blind_checks=verify_manifest(BLIND_ROOT,'PACKET-SHA256SUMS.txt')
assert sha((PRIMARY_ROOT/'SHA256SUMS.txt').read_bytes())=='c30936fe3e595ef298e9c7d2a6bd84c148bd83a660321c26e27daff2a42d5fab'
assert sha((INPUT/'PACKET-SHA256SUMS.txt').read_bytes())=='4dcbdb679ced3a9211560682a5b8775af06aab9a06b1970179156d94e3cabfb0'
assert sha((PRIMARY/'SHA256SUMS.txt').read_bytes())=='1e2d4fb9994e3062db945ea9698815770d34edf4ed064267673471f9756dc863'
assert sha((BLIND_ROOT/'PACKET-SHA256SUMS.txt').read_bytes())=='6281e1efc35e78e082d9586ab1c47fdf9e80e4de48d384154e5f4996b4eec5aa'

att=read_json(INPUT/'head-tree-attestation.json'); selection=read_json(INPUT/'selection-and-boundary.json')
assert (att['head'],att['tree'],att['branch'],att['remoteBranchHead'],att['bodySha256'])==(HEAD,TREE,BRANCH,HEAD,body_sha)
assert selection['inputContainsCandidates'] is False
cells=read_jsonl(INPUT/'source-current-cells.jsonl'); callers=read_jsonl(INPUT/'caller-contexts.jsonl'); catalogs=read_jsonl(INPUT/'catalog-structure.jsonl'); protected_rows=read_jsonl(INPUT/'protected-literals.jsonl')
primary_rows=read_jsonl(PRIMARY/'review-decisions.jsonl'); blind_rows=read_jsonl(BLIND)
primary_summary=read_json(PRIMARY/'review-summary.json'); blind_summary=read_json(BLIND_ROOT/'blind-review-summary.json')
assert len(cells)==len(primary_rows)==len(blind_rows)==300 and len(callers)==len(protected_rows)==25 and len(catalogs)==12
assert [(x['continuationRank'],x['locale']) for x in cells]==[(r,l) for r in range(276,301) for l in LOCALES]
cell_by={(x['continuationRank'],x['locale']):x for x in cells}
primary_by={(x['continuationRank'],x['locale']):x for x in primary_rows}
blind_by={(x['continuationRank'],x['locale']):x for x in blind_rows}
assert cell_by.keys()==primary_by.keys()==blind_by.keys()
caller_by_id={x['sourceId']:x for x in callers}

# Re-attest every catalog byte stream, git blob, ordered keyset, source/current value.
ordered_hashes=set(); locale_docs={}
for cat in catalogs:
 data=(REPO/cat['catalogPath']).read_bytes(); doc=json.loads(data); keys=list(doc); actual_blob=run('git','rev-parse',f'{HEAD}:{cat["catalogPath"]}').strip()
 assert sha(data)==cat['sha256'] and blob(data)==cat['gitBlob']==actual_blob
 assert len(keys)==cat['entryCount']==6176 and cat['orderedKeySha256']==sha('\n'.join(keys)+'\n')
 ordered_hashes.add(cat['orderedKeySha256']); locale_docs[cat['locale']]=doc
assert len(ordered_hashes)==1 and next(iter(ordered_hashes))==selection['orderedCatalogKeySha256']

caller_ref_count=0
for cell in cells:
 rank=cell['continuationRank']; locale=cell['locale']; key=(rank,locale); p=primary_by[key]; b=blind_by[key]
 source=cell['source']; current=cell['currentTarget']; sid=cell['sourceId']
 assert sha(source)==cell['sourceSha256'] and sid=='src_'+sha(source)[:16]
 doc=locale_docs[locale]; assert source in doc and doc[source]==current and sha(current)==cell['currentTargetSha256']
 cat=next(x for x in catalogs if x['locale']==locale)
 for row in (p,b):
  assert (row['sourceId'],row['source'],row['sourceSha256'],row['locale'],row['catalogPath'],row['catalogFileSha256'],row['catalogGitBlob'],row['currentTarget'],row['currentTargetSha256'],row['callerContextSha256'])==(sid,source,cell['sourceSha256'],locale,cat['catalogPath'],cat['sha256'],cat['gitBlob'],current,cell['currentTargetSha256'],cell['callerContextSha256'])
  assert row['candidateTargetSha256']==sha(row['candidateTarget'])
  assert row['callerRefs']==cell['callerRefs']
 caller=caller_by_id[sid]
 assert sha(canonical(caller['callers']))==cell['callerContextSha256']
 assert cell['callerRefs']==[{'path':x['path'],'line':x['line'],'lineSha256':x['lineSha256'],'fileSha256':x['fileSha256'],'gitBlob':x['gitBlob']} for x in caller['callers']]
 for ref in caller['callers']:
  data=(REPO/ref['path']).read_bytes(); lines=data.decode('utf-8').splitlines(); actual_blob=run('git','rev-parse',f'{HEAD}:{ref["path"]}').strip()
  assert sha(data)==ref['fileSha256'] and blob(data)==ref['gitBlob']==actual_blob
  assert lines[ref['line']-1]==ref['lineText'] and sha(lines[ref['line']-1])==ref['lineSha256']
  context=[{'line':i+1,'text':lines[i]} for i in range(max(0,ref['line']-3),min(len(lines),ref['line']+3))]
  assert context==ref['context'] and sha(canonical(context))==ref['contextSha256']
  if locale==LOCALES[0]: caller_ref_count+=1
assert caller_ref_count==40 and sum(x['productionCallerCount'] for x in callers)==40

# Validate each current/candidate protected literal, placeholder, markup and numeric token.
issue_counts=collections.Counter(); current_protected=[]; current_numeric=[]
for cell in cells:
 key=(cell['continuationRank'],cell['locale']); p=primary_by[key]; b=blind_by[key]
 source=cell['source']; current=cell['currentTarget']; protected=cell['protectedLiteralChecks']
 for row in (p,b):
  cand=row['candidateTarget']; sp=collections.Counter(PH.findall(source)); cp=collections.Counter(PH.findall(cand)); mp=collections.Counter(MARKUP.findall(source)); cm=collections.Counter(MARKUP.findall(cand)); sn=collections.Counter(NUMBER.findall(source)); cn=collections.Counter(NUMBER.findall(cand))
  assert sp==cp and mp==cm and (not sn or sn==cn),(key,'candidate structural mismatch')
  assert all(x['literal'] in cand for x in protected),(key,'candidate protected literal missing')
  assert row['placeholderCheck']['sourceMatchesCandidate'] is True and row['markupCheck']['sourceMatchesCandidate'] is True and row['numericCheck']['sourceMatchesCandidate'] is True
 if any(x['literal'] not in current for x in protected): current_protected.append(key)
 sn=collections.Counter(NUMBER.findall(source)); cn=collections.Counter(NUMBER.findall(current))
 if sn and sn!=cn: current_numeric.append(key)
 if any(x['literal'] not in p['candidateTarget'] for x in protected) or any(x['literal'] not in b['candidateTarget'] for x in protected): issue_counts['candidate-protected']+=1
 if not collections.Counter(PH.findall(source))==collections.Counter(PH.findall(current)): issue_counts['current-placeholder']+=1
 if not collections.Counter(MARKUP.findall(source))==collections.Counter(MARKUP.findall(current)): issue_counts['current-markup']+=1
assert len(current_protected)==19 and len(current_numeric)==5
assert not issue_counts['candidate-protected'] and not issue_counts['current-placeholder'] and not issue_counts['current-markup']

# Rank 283 glossary anchors come from other source rows in the same exact-head catalogs.
wishlist_terms={}; wishlist_sha={}
for locale,doc in locale_docs.items():
 keys=['Wishlist','Sync wanted albums to Wishlist','Sync Lidarr wanted albums into slskdN Wishlist review items.']
 assert all(k in doc for k in keys)
 wishlist_terms[locale]={k:doc[k] for k in keys}
 wishlist_sha[locale]={k:sha(doc[k]) for k in keys}

# Cross-review disagreements are kept in a separate file and all target choices are adjudicated.
resolved_283={
 'ar':'فعّل مزامنة الألبومات المطلوبة من Lidarr مع قائمة الرغبات',
 'de':'Synchronisierung der von Lidarr gewünschten Alben mit der Wunschliste aktivieren',
 'es':'Activar la sincronización de los álbumes deseados de Lidarr con la lista de deseos',
 'fr':'Activer la synchronisation des albums souhaités par Lidarr avec la liste de souhaits',
 'hi':'Lidarr के वांछित एल्बमों को इच्छा सूची में सिंक करना सक्षम करें',
 'id':'Aktifkan sinkronisasi album yang diinginkan di Lidarr ke Daftar keinginan',
 'ja':'Lidarrで取得を希望しているアルバムをウィッシュリストに同期する設定を有効にする',
 'ko':'Lidarr에서 원하는 앨범을 위시리스트에 동기화하도록 설정',
 'pt-BR':'Ativar a sincronização dos álbuns desejados pelo Lidarr com a lista de desejos',
 'vi':'Bật đồng bộ các album Lidarr mong muốn vào Danh sách yêu thích',
 'zh-Hans':'启用将 Lidarr 中想要的专辑同步到愿望单',
 'zh-Hant':'啟用將 Lidarr 中想要的專輯同步至願望清單',
}
assert set(resolved_283)==set(LOCALES)
# Explicitly pin each chosen Wishlist term to the current catalog's standalone entry.
chosen_wishlist={'ar':'قائمة الرغبات','de':'Wunschliste','es':'Lista de deseos','fr':'Liste de souhaits','hi':'इच्छा सूची','id':'Daftar keinginan','ja':'ウィッシュリスト','ko':'위시리스트','pt-BR':'Lista de desejos','vi':'Danh sách yêu thích','zh-Hans':'愿望单','zh-Hant':'願望清單'}
assert all(wishlist_terms[loc]['Wishlist']==term for loc,term in chosen_wishlist.items())
assert all(term.casefold() in resolved_283[loc].casefold() for loc,term in chosen_wishlist.items())

adjudication_overrides={
 (279,'ar'):('الفحوصات:','refinement','Both reviews found the section-heading wording needs improvement. This concise heading matches the readiness-check list; the existing term conveys checking, so the cross disposition is refinement.'),
 (287,'ja'):(primary_by[(287,'ja')]['candidateTarget'],'correction','Both candidates express the intended lossy-audio warning. Use the sentence-style ending in the primary proposal, which fits this diagnostic message; both preserve DR and {range}.'),
 (288,'ja'):(blind_by[(288,'ja')]['candidateTarget'],'correction','Both proposals preserve the exact parser sample. Use Japanese fullwidth parentheses without an English-style preceding space while retaining the ASCII comma-separated sample.'),
 (290,'es'):(blind_by[(290,'es')]['candidateTarget'],'refinement','The caller displays a current stopped health state. Detenido names that state more directly than Interrumpido, which can mean an interruption.'),
}
cross_rows=[]; disagreements=[]; glossary_rows=[]
for cell in cells:
 key=(cell['continuationRank'],cell['locale']); rank,loc=key; p=primary_by[key]; b=blind_by[key]; source=cell['source']; current=cell['currentTarget']
 types=[]
 if p['candidateTarget']!=b['candidateTarget']: types.append('candidate-text-disagreement')
 if p['verdict']!=b['verdict']: types.append('verdict-disagreement')
 if rank==283:
  cand=resolved_283[loc]; verdict='correction'; rationale=f"Use the established localized feature name for Wishlist from this exact-head catalog: {chosen_wishlist[loc]!r}. The pinned caller describes syncing Lidarr wanted albums into those review items. This resolves the reviews' English-versus-local term differences without changing the product feature."; resolution='localized-catalog-glossary'
 elif key in adjudication_overrides:
  cand,verdict,rationale=adjudication_overrides[key]; resolution='semantic-cross-adjudication'
 elif p['candidateTarget']==b['candidateTarget'] and p['verdict']==b['verdict']:
  cand=p['candidateTarget']; verdict=p['verdict']; rationale='Both independent ledgers agree on the exact candidate and disposition.'; resolution='reviewer-consensus'
 elif p['candidateTarget']==b['candidateTarget']:
  cand=p['candidateTarget']; verdict=p['verdict'] if p['verdict'].startswith('hold-') or b['verdict'].startswith('hold-') else 'refinement'; rationale='The exact target text agrees. The cross-audit retains the safer hold if present; otherwise the difference is treated as a refinement of the current value.'; resolution='same-target-disposition-adjudication'
 else:
  raise AssertionError(f'unadjudicated disagreement {key}: {p["candidateTarget"]!r} vs {b["candidateTarget"]!r}')
 assert sha(cand)
 if rank==283:
  glossary_rows.append({'rank':rank,'sourceId':cell['sourceId'],'locale':loc,'standaloneWishlistKeyTarget':wishlist_terms[loc]['Wishlist'],'standaloneWishlistTargetSha256':wishlist_sha[loc]['Wishlist'],'siblingSyncLabelTarget':wishlist_terms[loc]['Sync wanted albums to Wishlist'],'tooltipTarget':wishlist_terms[loc]['Sync Lidarr wanted albums into slskdN Wishlist review items.'],'primaryCandidate':p['candidateTarget'],'blindCandidate':b['candidateTarget'],'crossCandidate':cand,'crossDisposition':verdict,'rationale':rationale})
 row={'continuationRank':rank,'historicalSourceOrdinal':None,'sourceId':cell['sourceId'],'source':source,'sourceSha256':cell['sourceSha256'],'locale':loc,'catalogPath':cell['catalogPath'],'catalogFileSha256':cell['catalogFileSha256'],'catalogGitBlob':cell['catalogGitBlob'],'currentTarget':current,'currentTargetSha256':cell['currentTargetSha256'],'callerContextSha256':cell['callerContextSha256'],'callerRefs':cell['callerRefs'],'callerCount':caller_by_id[cell['sourceId']]['productionCallerCount'],'primary':{'verdict':p['verdict'],'candidateTarget':p['candidateTarget'],'candidateTargetSha256':p['candidateTargetSha256'],'rationale':p['rationale']},'blind':{'verdict':b['verdict'],'candidateTarget':b['candidateTarget'],'candidateTargetSha256':b['candidateTargetSha256'],'rationale':b['rationale']},'comparison':{'candidateTextAgrees':p['candidateTarget']==b['candidateTarget'],'verdictAgrees':p['verdict']==b['verdict'],'disagreementTypes':types},'crossAdjudication':{'verdict':verdict,'candidateTarget':cand,'candidateTargetSha256':sha(cand),'resolution':resolution,'rationale':rationale},'checks':{}}
 for reviewer,row_in in [('primary',p),('blind',b)]:
  review_candidate=row_in['candidateTarget']; sp=collections.Counter(PH.findall(source)); cp=collections.Counter(PH.findall(review_candidate)); mp=collections.Counter(MARKUP.findall(source)); cm=collections.Counter(MARKUP.findall(review_candidate)); sn=collections.Counter(NUMBER.findall(source)); cn=collections.Counter(NUMBER.findall(review_candidate))
  row['checks'][reviewer]={'placeholderParity':sp==cp,'markupParity':mp==cm,'numericParity':(not sn or sn==cn),'protectedLiteralsPresent':all(z['literal'] in review_candidate for z in cell['protectedLiteralChecks'])}
 # Cross candidate is rechecked independently.
  cross_candidate=row['crossAdjudication']['candidateTarget']; sn=collections.Counter(NUMBER.findall(source)); crossnum=collections.Counter(NUMBER.findall(cross_candidate))
  row['checks']['cross']={'placeholderParity':collections.Counter(PH.findall(source))==collections.Counter(PH.findall(cross_candidate)),'markupParity':collections.Counter(MARKUP.findall(source))==collections.Counter(MARKUP.findall(cross_candidate)),'numericParity':(not sn or sn==crossnum),'protectedLiteralsPresent':all(z['literal'] in cross_candidate for z in cell['protectedLiteralChecks'])}
 assert all(all(x.values()) for x in row['checks'].values()),(key,row['checks'])
 cross_rows.append(row)
 if types:
   adjudicated=row['crossAdjudication']
   disagreements.append({'continuationRank':rank,'sourceId':cell['sourceId'],'source':source,'locale':loc,'disagreementTypes':types,'primaryVerdict':p['verdict'],'primaryCandidate':p['candidateTarget'],'blindVerdict':b['verdict'],'blindCandidate':b['candidateTarget'],'crossVerdict':adjudicated['verdict'],'crossCandidate':adjudicated['candidateTarget'],'crossResolution':adjudicated['resolution'],'rationale':adjudicated['rationale']})

cross_by_key={(x['continuationRank'],x['locale']):x for x in cross_rows}
for disagreement in disagreements:
 adjudicated=cross_by_key[(disagreement['continuationRank'],disagreement['locale'])]['crossAdjudication']
 assert disagreement['crossCandidate']==adjudicated['candidateTarget'] and disagreement['crossVerdict']==adjudicated['verdict'] and disagreement['crossResolution']==adjudicated['resolution'] and disagreement['rationale']==adjudicated['rationale']
for item in glossary_rows:
 adjudicated=cross_by_key[(283,item['locale'])]['crossAdjudication']
 assert item['crossCandidate']==adjudicated['candidateTarget'] and item['crossDisposition']==adjudicated['verdict']

assert len(cross_rows)==300 and len(disagreements)==15 and len(glossary_rows)==12
cross_counts=collections.Counter(x['crossAdjudication']['verdict'] for x in cross_rows)
primary_counts=collections.Counter(x['verdict'] for x in primary_rows); blind_counts=collections.Counter(x['verdict'] for x in blind_rows)
assert cross_counts==collections.Counter({'accept-current':193,'correction':59,'refinement':12,'hold-terminology':36}),cross_counts
candidate_changes=[x for x in cross_rows if x['crossAdjudication']['candidateTarget']!=x['currentTarget']]
assert len(candidate_changes)==71
summary={'reviewType':'third-party cross-audit and reconciliation of W55 candidate-free input, primary ledger, and independent blind ledger','repository':'snapetech-org/slskdN','pullRequest':409,'pullRequestUrl':pr['url'],'state':'OPEN','isDraft':True,'branch':BRANCH,'exactHead':HEAD,'exactTree':TREE,'remoteBranchHead':remote[0],'pinnedPrBodySha256':body_sha,'sourceCount':25,'localeCount':12,'cellCount':300,'orderedCatalogKeySha256':selection['orderedCatalogKeySha256'],'callerSourceCount':25,'callerReferenceCount':caller_ref_count,'callerlessSourceIds':[],'inputManifestSha256':sha((INPUT/'PACKET-SHA256SUMS.txt').read_bytes()),'inputManifestEntriesVerified':len(input_checks),'primaryRootManifestSha256':sha((PRIMARY_ROOT/'SHA256SUMS.txt').read_bytes()),'primaryRootManifestEntriesVerified':len(primary_root_checks),'primaryManifestSha256':sha((PRIMARY/'SHA256SUMS.txt').read_bytes()),'primaryManifestEntriesVerified':len(primary_checks),'blindManifestSha256':sha((BLIND_ROOT/'PACKET-SHA256SUMS.txt').read_bytes()),'blindManifestEntriesVerified':len(blind_checks),'primaryCounts':dict(primary_counts),'blindCounts':dict(blind_counts),'crossAdjudicatedCounts':dict(cross_counts),'primaryCandidateChanges':sum(x['candidateTarget']!=x['currentTarget'] for x in primary_rows),'blindCandidateChanges':sum(x['candidateTarget']!=x['currentTarget'] for x in blind_rows),'crossCandidateChanges':len(candidate_changes),'candidateTextDisagreementCount':sum(not x['comparison']['candidateTextAgrees'] for x in cross_rows),'verdictDisagreementCount':sum(not x['comparison']['verdictAgrees'] for x in cross_rows),'disagreementCellCount':len(disagreements),'unresolvedDisagreementCount':0,'holdCount':sum(v for k,v in cross_counts.items() if k.startswith('hold-')),'heldRanks':{'278':'Publish or retrieve pod metadata through DHT workflows.','282':'You need at least one pod with VPN gateway capability to use port forwarding.','289':'Please enter both Pod ID and Peer ID'},'holdLocalesByRank':{str(r):LOCALES for r in (278,282,289)},'currentProtectedLiteralMismatchCount':len(current_protected),'primaryProtectedCandidateMismatchCount':0,'blindProtectedCandidateMismatchCount':0,'crossProtectedCandidateMismatchCount':0,'currentNumericMismatchCount':len(current_numeric),'currentNumericMismatchCells':[{'rank':r,'locale':l} for r,l in current_numeric],'primaryNumericCandidateMismatchCount':0,'blindNumericCandidateMismatchCount':0,'crossNumericCandidateMismatchCount':0,'placeholderMismatchCount':0,'markupMismatchCount':0,'localizedWishlistTerms':chosen_wishlist,'wishlistTermPins':wishlist_sha,'nativeSpeakerApproval':False,'headedProductBrowserReview':False,'projectTestsBuildsScansCiRun':False,'repositoryModified':False,'remoteMutation':False,'notes':['Primary and blind ledgers independently agree on all 36 Pod terminology holds.','The 15 candidate-text disagreements and two verdict disagreements are all resolved in cross-audit ledger.','The rank 283 differences are reconciled against exact-head localized translations for the standalone Wishlist key and its sibling setting/tooltip strings.','Rank 288 candidates retain the exact comma-separated audio sample syntax; five current decimal-comma values are incompatible with the pinned comma-splitting parser.','This cross-audit is machine-assisted and does not constitute native-speaker approval.'],'exactDisagreements':disagreements,'exactCrossChanges':[{'rank':x['continuationRank'],'sourceId':x['sourceId'],'locale':x['locale'],'from':x['currentTarget'],'to':x['crossAdjudication']['candidateTarget'],'verdict':x['crossAdjudication']['verdict'],'resolution':x['crossAdjudication']['resolution']} for x in candidate_changes],'exactHolds':[{'rank':x['continuationRank'],'sourceId':x['sourceId'],'source':x['source'],'locale':x['locale'],'current':x['currentTarget'],'reason':x['crossAdjudication']['rationale']} for x in cross_rows if x['crossAdjudication']['verdict'].startswith('hold-')]}

# Write a full pinned-cell reconciliation and explicit disagreement files.
write_json(OUT/'input-verification.json',{'verification':'passed','repository':'snapetech-org/slskdN','pullRequest':409,'url':pr['url'],'state':pr['state'],'isDraft':pr['isDraft'],'branch':BRANCH,'head':HEAD,'tree':TREE,'remoteBranchHead':remote[0],'prBodySha256':body_sha,'worktreeClean':True,'inputManifestSha256':summary['inputManifestSha256'],'catalogs':len(catalogs),'catalogKeysPerLocale':6176,'orderedCatalogKeySha256':selection['orderedCatalogKeySha256'],'cells':len(cells),'callerSources':len(callers),'callerReferencesVerified':caller_ref_count,'primaryManifestEntriesVerified':len(primary_checks),'blindManifestEntriesVerified':len(blind_checks),'currentProtectedLiteralMismatchCount':len(current_protected),'currentNumericMismatchCount':len(current_numeric),'candidateProtectedNumericPlaceholderMarkupMismatchCounts':{'primary':0,'blind':0,'cross':0},'disagreementExportMatchesLedger':True,'localizedTermAdjudicationsMatchLedger':True})
write_jsonl(OUT/'cross-audit-ledger.jsonl',cross_rows)
write_jsonl(OUT/'disagreements.jsonl',disagreements)
write_jsonl(OUT/'localized-term-adjudications.jsonl',glossary_rows)
write_json(OUT/'cross-audit-summary.json',summary)
worksheet=['# W55 third-party cross-audit worksheet','',f'Exact head/tree: `{HEAD}` / `{TREE}`.',f'Candidate-free input SHA-256: `{summary["inputManifestSha256"]}`.',f'Primary vs blind: {len(disagreements)} disagreement cells; {sum(not x["comparison"]["candidateTextAgrees"] for x in cross_rows)} candidate-text disagreements; {sum(not x["comparison"]["verdictAgrees"] for x in cross_rows)} disposition disagreements. All reconciled.','',f"Cross dispositions: {dict(cross_counts)}; exact candidate changes: {len(candidate_changes)}; holds: {summary['holdCount']}.",'','## Main disagreements','','- Rank 279 Arabic: use `الفحوصات:` as the concise readiness-check heading; classify as refinement.','- Rank 283: use each locale’s pinned translation of the standalone `Wishlist` source key in the Lidarr setting string. See `localized-term-adjudications.jsonl`.','- Rank 287 Japanese: use the sentence-style `示唆します` form; preserve DR and `{range}`.','- Rank 288 Japanese: keep the exact ASCII comma-separated sample and use natural Japanese parentheses.','- Rank 290 Spanish: use `Detenido` for the current stopped health state; classify as refinement.','','## Holds','','Both ledgers hold the same three Pod-term sources in all 12 locales: ranks 278, 282, and 289. The 36 current values remain unchanged pending an approved localized product term.','','## Checks','','All 300 primary and blind rows map exactly to input source/current/catalog/caller pins. All 40 caller references match exact-head file, line, and context hashes. Candidate placeholder, markup, numeric, and protected-literal checks pass for both ledgers and the reconciled candidate set.']
(OUT/'cross-audit-worksheet.md').write_text('\n'.join(worksheet)+'\n',encoding='utf-8')
readme=(f"# slskdN PR #409 W55 third-party cross-audit\n\n"
 f"This cross-audit reconciles the candidate-free input and the primary and independent blind W55 ledgers for ranks 276–300 at exact PR head/tree `{HEAD}` / `{TREE}`. The primary root manifest SHA-256 is `{summary['primaryRootManifestSha256']}`, candidate-free input manifest `{summary['inputManifestSha256']}`, and blind packet manifest `{summary['blindManifestSha256']}`.\n\n"
 f"The audit verified 300 source/locale cells, 12 exact-head catalogs with 6,176 keys each, and 40 pinned production caller references. Primary and blind reviews have {summary['candidateTextDisagreementCount']} candidate-text disagreements and {summary['verdictDisagreementCount']} disposition disagreements, across {summary['disagreementCellCount']} cells; all are reconciled.\n\n"
 f"Cross-adjudicated counts: 193 accept-current, 59 corrections, 12 refinements, and 36 terminology holds. The holds are ranks 278, 282, and 289 across all 12 locales. Candidate source, placeholder, markup, numeric, and protected-literal checks pass.\n\n"
 "The rank 283 differences use the exact-head localized catalog value for the standalone Wishlist key. Japanese wording and Spanish status-label disagreements are adjudicated in the ledger and worksheet.\n\n"
 "This is machine-assisted cross-review, not native-speaker approval or headed product-browser acceptance. No repository/PR edits, tests, builds, scans, CI, commits, pushes, merges, releases, or tags were made.\n")
(OUT/'README.md').write_text(readme,encoding='utf-8')
write_manifest(OUT,'PACKET-SHA256SUMS.txt')
checks=verify_manifest(OUT,'PACKET-SHA256SUMS.txt')
assert len(checks)==8
print(json.dumps({'verification':'cross-audit-sealed','outputDir':str(OUT),'files':len(checks),'packetManifestSha256':sha((OUT/'PACKET-SHA256SUMS.txt').read_bytes()),'primaryManifestEntriesVerified':len(primary_checks),'inputManifestEntriesVerified':len(input_checks),'blindManifestEntriesVerified':len(blind_checks),'cells':len(cross_rows),'disagreementCells':len(disagreements),'candidateDisagreements':sum(not x['comparison']['candidateTextAgrees'] for x in cross_rows),'verdictDisagreements':sum(not x['comparison']['verdictAgrees'] for x in cross_rows),'crossCounts':dict(cross_counts),'crossChanges':len(candidate_changes),'holds':summary['holdCount'],'callerReferencesVerified':caller_ref_count,'currentProtectedMismatchCount':len(current_protected),'currentNumericMismatchCells':[f'{r}:{l}' for r,l in current_numeric]},ensure_ascii=False,indent=2))
