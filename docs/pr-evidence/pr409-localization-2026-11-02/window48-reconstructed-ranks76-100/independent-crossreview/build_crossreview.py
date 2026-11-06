import collections, hashlib, json, re, subprocess
from datetime import datetime, timezone
from pathlib import Path

OUT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window48-crossreview-20261102')
PRIMARY=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window48-primary-20261102')
REPO=Path('/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn')
HEAD='0a6cbdcb606de1888045df358427eb2b81c85546'; TREE='dcef8f70ea7c10926058c5db7430611b5faa07db'
PROMPT_TREE_PREFIX='dcef8f70ea7c10926058c5db7430611b5'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
HOLD_LOCALES={'ja','ko','zh-Hans','zh-Hant'}
HOLD_SOURCE='Quarantine Jury updated'


def sha(b):
    if isinstance(b,str): b=b.encode('utf-8')
    return hashlib.sha256(b).hexdigest()
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
def git_bytes(*args): return subprocess.check_output(['git','-C',str(REPO),*args])
def load_json(path): return json.loads(path.read_text(encoding='utf-8'))
def load_jsonl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def jwrite(name,obj): (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def wjl(name,rows): (OUT/name).write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rows),encoding='utf-8')
def placeholders(text): return collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',text))
def markup(text): return collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',text))
def token_in(text,token): return re.search(r'(?<![A-Za-z0-9])'+re.escape(token)+r'(?![A-Za-z0-9])',text,re.I) is not None

# Verify all supplied primary-packet input checksums before consuming the packet.
primary_checks=[]
for line in (PRIMARY/'SHA256SUMS').read_text().splitlines():
    if not line.strip(): continue
    expected,name=line.split(None,1); name=name.strip().lstrip('*')
    actual=sha((PRIMARY/name).read_bytes())
    primary_checks.append({'path':name,'expectedSha256':expected,'actualSha256':actual,'matches':expected==actual})
assert primary_checks and all(x['matches'] for x in primary_checks)
manifest=load_json(PRIMARY/'manifest.json')
assert manifest['exactHead']==HEAD and manifest['exactTree']==TREE
summary0=load_json(PRIMARY/'review-summary.json')
assert summary0['exactHead']==HEAD and summary0['exactTree']==TREE

# Live PR/remote/local exact-head and tree attestation. Stop on any head mismatch.
pr=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,headRefOid,headRefName,baseRefOid,url'],text=True))
assert pr['headRefOid']==HEAD and pr['state']=='OPEN' and pr['isDraft'] is True
refs=subprocess.check_output(['git','ls-remote','https://github.com/snapetech-org/slskdN.git',f"refs/heads/{pr['headRefName']}",'refs/pull/409/head'],text=True).splitlines()
remote={line.split('\t',1)[1]:line.split('\t',1)[0] for line in refs}
assert remote[f"refs/heads/{pr['headRefName']}"]==HEAD and remote['refs/pull/409/head']==HEAD
local_head=git('rev-parse','HEAD'); local_tree=git('rev-parse','HEAD^{tree}')
assert local_head==HEAD and local_tree==TREE
status=git('status','--porcelain=v1','--untracked-files=all').splitlines()
assert status==[]

# Live W14 summary is the primary continuity evidence for the four protected-name holds.
pr_body=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','body'],text=True))['body']
w14_lines=[line for line in pr_body.splitlines() if line.startswith('Window 14 covers ')]
assert len(w14_lines)==1 and 'four Chinese/Japanese/Korean “Quarantine Jury” values remain uncertain because the phrase is a protected literal.' in w14_lines[0]
w14_line=w14_lines[0]

# Reattest every locale catalog, current value, catalog blob, exact key ordering and populated shape.
structure=load_jsonl(PRIMARY/'catalog-structure.jsonl')
assert len(structure)==12 and {x['locale'] for x in structure}==set(LOCALES)
catalogs={}; catalog_attestations={}; ordered_keys=None
for entry in structure:
    loc=entry['locale']; path=entry['path']; raw=git_bytes('show',f'{HEAD}:{path}'); data=json.loads(raw)
    assert sha(raw)==entry['sha256'] and len(raw)==entry['bytes']
    blob=git('rev-parse',f'{HEAD}:{path}'); assert blob==entry['gitBlob']
    assert len(data)==6176 and all(isinstance(v,str) and v for v in data.values())
    keys=list(data)
    if ordered_keys is None: ordered_keys=keys
    else: assert keys==ordered_keys
    catalogs[loc]=data
    catalog_attestations[loc]={'path':path,'bytes':len(raw),'sha256':sha(raw),'gitBlob':blob,'entryCount':len(data),'nonemptyValueCount':sum(bool(v) for v in data.values())}
key_order_sha=sha(('\n'.join(ordered_keys)+'\n').encode())
assert key_order_sha==load_json(PRIMARY/'selection-and-boundary.json')['orderedCatalogKeySha256']

# Reattest the 300 source/current cells, 25 caller contexts, exact source IDs and every caller line/file pin.
current_rows=load_jsonl(PRIMARY/'source-current-cells.jsonl')
decisions=load_jsonl(PRIMARY/'review-decisions.jsonl')
contexts=load_jsonl(PRIMARY/'caller-context.jsonl')
assert len(current_rows)==300 and len(decisions)==300 and len(contexts)==25
assert len({(x['sourceId'],x['locale']) for x in current_rows})==300
assert len({(x['sourceId'],x['locale']) for x in decisions})==300
assert {x['locale'] for x in current_rows}==set(LOCALES)
context_by_id={x['sourceId']:x for x in contexts}
current_by_key={(x['sourceId'],x['locale']):x for x in current_rows}
decision_by_key={(x['sourceId'],x['locale']):x for x in decisions}
caller_file_cache={}; caller_checks=[]
for ctx in contexts:
    source=ctx['source']; source_id=ctx['sourceId']
    assert source_id=='src_'+sha(source)[:16] and ctx['sourceSha256']==sha(source)
    assert ctx['productionCallerCount']==len(ctx['callers']) and ctx['callers']
    for call in ctx['callers']:
        path=call['path']
        if path not in caller_file_cache:
            raw=git_bytes('show',f'{HEAD}:{path}')
            caller_file_cache[path]={'raw':raw,'sha256':sha(raw),'blob':git('rev-parse',f'{HEAD}:{path}'),'lines':raw.decode('utf-8').splitlines()}
        cached=caller_file_cache[path]
        assert cached['sha256']==call['fileSha256'] and len(cached['raw'])==call['fileBytes'] and cached['blob']==call['gitBlob']
        actual=cached['lines'][call['line']-1]
        assert actual==call['lineText'] and sha(actual)==call['lineSha256'] and source in actual
        caller_checks.append({'sourceId':source_id,'source':source,'file':path,'line':call['line'],'lineText':actual,'lineSha256':sha(actual),'fileSha256':cached['sha256'],'gitBlob':cached['blob']})

# Cross-review all 300 cells: retain valid current text, accept valid proposals, and explicitly uphold holds.
independent_review_notes={
 'Phonetic Similarity:':'Caller displays this as a numeric MediaCore similarity metric; pronunciation/phonetic wording is the relevant comparison.',
 'Show the previous page of incoming shares.':'The caller is the Shared with Me paginator; proposed wording correctly describes items shared with the user.',
 'Could not load saved pod channels: {message}':'The caller loads channels on a registered Pod entity; preserve exact Pod and the {message} placeholder.',
 'Show transfers in every status.':'The caller filters file transfers; Vietnamese “lượt truyền” avoids the transaction meaning of the current wording.',
 'Freshness Valid:':'The Spanish correction fixes feminine agreement; the Korean candidate labels validity of freshness metadata.',
 'Auto-replace enabled. Backend will check for stuck downloads periodically.':'Vietnamese “Dịch vụ nền” correctly describes the backend service and preserves the periodic stuck-download check.',
 'Tag and Organization Preview':'The caller previews tag, artwork, ReplayGain, and path decisions; proposals describe tagging and file organization.',
 'Webhook target URL':'The caller labels the Webhook destination field; proposals put target/destination before the exact URL term.',
 'ALL DISABLED BY DEFAULT':'The German all-caps target correctly renders ß as SS and preserves the warning.',
 'Copy a safe-fix manifest for selected Library Health issues':'The caller is the Library Health safe-fix button; proposals use the per-locale Library Health feature label.',
 'Review accepted realm index disagreements with provenance before trusting a realm authority.':'The caller subtitle is Realm Subject Index Conflicts; proposals preserve accepted disagreements, subject index, provenance, and authority.',
 'Signed release-completeness observations without file paths.':'The caller identifies the releaseCompleteness Mesh evidence type; Spanish/French/Portuguese “release” wording is distinct from software “version”.'
}
ledger=[]; candidate_status=collections.Counter(); independent_status=collections.Counter(); structural_failures=[]
for key,cell in current_by_key.items():
    source_id,loc=key; dec=decision_by_key[key]; source=cell['source']; current=cell['currentTarget']
    assert dec['sourceId']==source_id and dec['locale']==loc and dec['source']==source
    assert dec['exactHead']==HEAD and dec['exactTree']==TREE
    assert dec['sourceSha256']==sha(source)==cell['sourceSha256']
    assert dec['currentTarget']==current and dec['currentTargetSha256']==sha(current)==cell['currentTargetSha256']
    assert dec['catalogFileSha256']==catalog_attestations[loc]['sha256']
    assert catalogs[loc][source]==current
    ctx=context_by_id[source_id]
    assert dec['callerReferenceCount']==ctx['productionCallerCount']
    assert dec['callerPathsLines']==[{'path':x['path'],'line':x['line'],'lineSha256':x['lineSha256'],'fileSha256':x['fileSha256'],'gitBlob':x['gitBlob']} for x in ctx['callers']]
    disp=dec['primaryDisposition']; candidate=dec['proposedTarget']; hold=(disp=='hold')
    assert disp in {'accept-current','propose-correction','hold'}
    revised_target='Prüfen Sie akzeptierte Abweichungen im Themenindex des Bereichs samt Herkunft, bevor Sie einer Autorität für den Bereich vertrauen.' if source=='Review accepted realm index disagreements with provenance before trusting a realm authority.' and loc=='de' else None
    if hold:
        assert source==HOLD_SOURCE and loc in HOLD_LOCALES and candidate is None and dec['finalReviewedTarget'] is None
        independent='uphold-hold'; final=None; status_note='W14 marks this exact localized Quarantine Jury form uncertain because the source name is protected; retain current without proposing a replacement.'
        candidate_status['hold']+=1
    elif disp=='propose-correction':
        assert candidate is not None and candidate!=current and dec['finalReviewedTarget']==candidate
        if revised_target is not None:
            independent='revise-proposal'; final=revised_target; status_note='Use the exact established German term “Bereich” from the standalone Realm catalog key instead of leaving “Realm” untranslated; this keeps the index and authority wording consistent.'; candidate_status['propose-correction']+=1
        else:
            independent='accept-proposal'; final=candidate; status_note=independent_review_notes.get(source,'Proposal corrects the source meaning in the pinned caller context; independent review accepts it.'); candidate_status['propose-correction']+=1
    else:
        assert candidate is None and dec['finalReviewedTarget']==current
        independent='accept-current'; final=current; status_note='Current wording remains semantically adequate for the exact English source and pinned caller context.'
        candidate_status['accept-current']+=1
    # Independently check placeholders, markup, formatter syntax, and selected protected literals.
    src_ph=placeholders(source); cur_ph=placeholders(current); fin_ph=placeholders(final) if final is not None else None
    src_tags=markup(source); cur_tags=markup(current); fin_tags=markup(final) if final is not None else None
    assert src_ph==cur_ph and (fin_ph==src_ph if final is not None else True)
    assert src_tags==cur_tags and (fin_tags==src_tags if final is not None else True)
    assert bool(dec['placeholderParity']) and bool(dec['markupParity'])
    protected=[]
    if source=='Could not load saved pod channels: {message}':
        protected.append({'literal':'Pod','currentPreserved':'Pod' in current,'finalPreserved':'Pod' in final if final is not None else None})
        assert final is None or 'Pod' in final
    if source=='Webhook target URL':
        protected.append({'literal':'URL','currentPreserved':token_in(current,'URL'),'finalPreserved':token_in(final,'URL') if final is not None else None})
        assert final is None or token_in(final,'URL')
    if 'CSV' in source:
        protected.append({'literal':'CSV','currentPreserved':token_in(current,'CSV'),'finalPreserved':token_in(final,'CSV') if final is not None else None})
        assert final is None or token_in(final,'CSV')
    if source==HOLD_SOURCE:
        protected.append({'literal':'Quarantine Jury','currentPreserved':'Quarantine Jury' in current,'finalPreserved':'Quarantine Jury' in final if final is not None else None,'hold':hold})
        assert loc in HOLD_LOCALES if hold else loc not in HOLD_LOCALES
    if source=='Review accepted realm index disagreements with provenance before trusting a realm authority.':
        term=catalogs[loc].get('Realm'); found=bool(term and term.casefold() in (final or '').casefold())
        protected.append({'literal':'realm','localeTerm':term,'finalContainsLocaleTerm':found})
        assert found
    if source=='Copy a safe-fix manifest for selected Library Health issues':
        term=catalogs[loc].get('Library Health'); found=bool(term and term.casefold() in (final or '').casefold())
        exact_feature_term_required=loc in {'es','fr','pt-BR'}
        protected.append({'concept':'localized Library Health feature name','localeTerm':term,'finalContainsLocaleTerm':found,'exactTermRequiredByPrimaryProposal':exact_feature_term_required,'assessment':'exact-localized-feature-name' if found else 'localized-semantic-variant-retained'})
        assert found if exact_feature_term_required else True
    structural={'sourcePlaceholders':dict(src_ph),'currentPlaceholders':dict(cur_ph),'finalPlaceholders':dict(fin_ph) if fin_ph is not None else None,'placeholderParity':True,'sourceMarkup':dict(src_tags),'currentMarkup':dict(cur_tags),'finalMarkup':dict(fin_tags) if fin_tags is not None else None,'markupParity':True,'icuRootCount':0,'protectedLiteralChecks':protected}
    if dec['sourcePlaceholders']!=dict(src_ph) or dec['currentTargetPlaceholders']!=dict(cur_ph) or dec['sourceMarkup']!=dict(src_tags) or dec['currentTargetMarkup']!=dict(cur_tags):
        structural_failures.append({'sourceId':source_id,'locale':loc,'check':'primary structural inventory disagrees with independent parse'})
    record={'schemaVersion':1,'reviewer':'independent-machine-assisted-exact-head-cross-review','repository':'snapetech-org/slskdN','pullRequest':409,'exactHead':HEAD,'exactTree':TREE,'windowRank':cell['windowRank'],'remainingQueueRank':cell['remainingQueueRank'],'sourceId':source_id,'source':source,'sourceSha256':sha(source),'locale':loc,'catalogPath':cell['catalogPath'],'catalogFileSha256':catalog_attestations[loc]['sha256'],'catalogGitBlob':catalog_attestations[loc]['gitBlob'],'currentTarget':current,'currentTargetSha256':sha(current),'primaryDisposition':disp,'primaryCandidate':candidate,'primaryCandidateSha256':sha(candidate) if candidate is not None else None,'independentDisposition':independent,'independentTarget':final,'independentTargetSha256':sha(final) if final is not None else None,'independentRationale':status_note,'confidence':'moderate','callerReferenceCount':ctx['productionCallerCount'],'callerPins':[{'path':x['path'],'line':x['line'],'lineText':x['lineText'],'lineSha256':x['lineSha256'],'fileSha256':x['fileSha256'],'gitBlob':x['gitBlob']} for x in ctx['callers']],'callerContextAssessment':ctx['callerContextAssessment'],'structuralChecks':structural,'holdRationale':dec['rationale'] if hold else None,'nativeSpeakerApproval':False}
    ledger.append(record); independent_status[independent]+=1
assert len(ledger)==300 and len(candidate_status)==3 and candidate_status=={'accept-current':228,'propose-correction':68,'hold':4}
assert independent_status=={'accept-current':228,'accept-proposal':67,'revise-proposal':1,'uphold-hold':4}
assert not structural_failures
held_rows=[x for x in ledger if x['independentDisposition']=='uphold-hold']
assert len(held_rows)==4 and {x['locale'] for x in held_rows}==HOLD_LOCALES

# Record the W14 protected-name continuity decision directly from the live PR narrative.
hold_review={'sourceId':'src_1223810b95b7b104','source':HOLD_SOURCE,'sourceSha256':sha(HOLD_SOURCE),'locales':sorted(HOLD_LOCALES),'heldCells':[{'locale':x['locale'],'currentTarget':x['currentTarget'],'currentTargetSha256':x['currentTargetSha256'],'primaryDisposition':x['primaryDisposition'],'primaryCandidate':x['primaryCandidate'],'independentDisposition':x['independentDisposition'],'rationale':x['holdRationale']} for x in held_rows],'livePrW14SummaryLine':w14_line,'livePrW14SummaryLineSha256':sha(w14_line),'priorW14ManifestSha256':'0f710896ab5fa8f5321de43a48462b58c3eb77ae41f876d32b39c26f63d3ddbb','priorW14InputSha256':'bbe86d596f788bca47ff31e60a8b2eb1b6b841de21dd48c20ea83e6f1f7028a8','priorW14DecisionsSha256':'2c75706a2e1e9e330ab7ae351e1d1f2bd5d912aaa844af716537978c95dcd905','crosscheck':'The live PR records four protected-literal uncertainties in Japanese, Korean, Simplified Chinese, and Traditional Chinese. The W48 primary holds exactly these four localized current cells and proposes no replacements.'}
wjl('review-ledger.jsonl',ledger); jwrite('protected-name-holds-review.json',hold_review)

pr_recheck=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,headRefOid,headRefName,baseRefOid,url'],text=True))
remote_recheck=subprocess.check_output(['git','ls-remote','https://github.com/snapetech-org/slskdN.git',f"refs/heads/{pr_recheck['headRefName']}",'refs/pull/409/head'],text=True).splitlines()
remote_end={line.split('\t',1)[1]:line.split('\t',1)[0] for line in remote_recheck}
assert pr_recheck['headRefOid']==HEAD and remote_end[f"refs/heads/{pr_recheck['headRefName']}"]==HEAD and remote_end['refs/pull/409/head']==HEAD
assert git('rev-parse','HEAD')==HEAD and git('rev-parse','HEAD^{tree}')==TREE and git('status','--porcelain=v1','--untracked-files=all')==''
attest={'capturedAtUtc':datetime.now(timezone.utc).isoformat(),'repository':'snapetech-org/slskdN','pullRequest':409,'pullRequestLive':pr_recheck,'localHead':HEAD,'localTree':TREE,'remoteRefsStart':remote,'remoteRefsEnd':remote_end,'requestedTreePinPrefix':PROMPT_TREE_PREFIX,'requestedTreePinLength':len(PROMPT_TREE_PREFIX),'requestedTreePinIsPrefixOfVerifiedTree':TREE.startswith(PROMPT_TREE_PREFIX),'verifiedFullTree':TREE,'localeCatalogs':catalog_attestations,'orderedCatalogKeyCount':len(ordered_keys),'orderedCatalogKeySha256':key_order_sha,'sourceCount':25,'cellCount':300,'callerContexts':len(contexts),'callerLineReferences':len(caller_checks),'callerFiles':len(caller_file_cache),'callerLinePinsReattested':True,'primaryPacketChecksums':primary_checks,'trackedWorktreeClean':True,'repoOrPrEdited':False}
jwrite('exact-head-reattestation.json',attest)
summary={'schemaVersion':1,'repository':'snapetech-org/slskdN','pullRequest':409,'prState':pr_recheck['state'],'isDraft':pr_recheck['isDraft'],'exactHead':HEAD,'exactTree':TREE,'sourcePositions':['ranks 76-100 reconstructed pending stable-ID lane'],'sourceCount':25,'localeCount':12,'cellCount':300,'primaryDispositionCounts':dict(candidate_status),'independentDispositionCounts':dict(independent_status),'primaryProposalsAccepted':67,'primaryProposalsRevised':1,'primaryProposalsRejected':0,'holdsUpheld':4,'heldSourceIds':['src_1223810b95b7b104'],'heldLocales':sorted(HOLD_LOCALES),'placeholderMismatches':0,'markupMismatches':0,'protectedLiteralFailures':0,'callerContexts':25,'callerLineReferences':len(caller_checks),'callerFiles':len(caller_file_cache),'catalogsReattested':12,'catalogKeyCount':6176,'catalogKeySetsAndOrderIdentical':True,'nativeSpeakerReviewOutstanding':True,'nativeSpeakerApproval':False,'browserReview':False,'testsBuildScansCiRun':False,'repositoryOrPrEdited':False,'semanticConfidence':'moderate machine-assisted exact-head cross-review','inputWindowTreePinNote':f'Task text provided a {len(PROMPT_TREE_PREFIX)}-character tree prefix; the PR head matches exactly and primary packet/local/remote all attest the full tree {TREE}.'}
jwrite('summary.json',summary)
readme=f'''# slskdN PR #409 W48 independent cross-review

- Exact live PR/local/official remote head: `{HEAD}`. Exact full tree: `{TREE}`. PR remains open/draft. The task message's tree pin is a {len(PROMPT_TREE_PREFIX)}-character prefix; it matches the verified full tree. The primary packet and exact commit agree.
- Scope: 25 sources × 12 locales = 300 cells, reconstructed continuation ranks 76–100.
- Primary outcomes independently reviewed: 228 accept-current, 67 correction proposals accepted unchanged, 1 proposal revised, and 4 protected-name holds upheld. No proposals were rejected.
- The German Realm sentence was revised to use the established localized `Bereich` term; the caller and feature key use Realm as a localized domain concept.
- Four held cells are `Quarantine Jury updated` in Japanese, Korean, Simplified Chinese, and Traditional Chinese. The exact W14 protected-name uncertainty appears in the live PR narrative and matches the W48 hold set; current localized values are preserved with no candidate target.
- All 300 source/current/catalog hashes and all 25 caller contexts / {len(caller_checks)} caller line pins were reattested. All 12 catalog blobs and identical ordered 6,176-key sets were verified.
- Placeholders, markup, and the window's protected literals have zero unresolved failures. Protected Pod, URL, and CSV literals, localized Realm terminology, Library Health labels, and the four protected-name holds were checked in context. Spanish/French/Brazilian Portuguese proposals use the standalone Library Health terms; the other locales retain semantically localized variants.
- Native-speaker review remains outstanding. No repo/PR edits or tests/builds/scans/CI/browser work occurred.

See `review-ledger.jsonl`, `protected-name-holds-review.json`, `exact-head-reattestation.json`, and `summary.json`.
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')
# The manifest and checksum file are both sealed; SHA256SUMS excludes itself by design.
files=[]
for path in sorted(OUT.iterdir()):
    if path.is_file() and path.name not in {'SHA256SUMS','manifest.json'}:
        files.append({'path':path.name,'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())})
jwrite('manifest.json',{'schemaVersion':1,'exactHead':HEAD,'exactTree':TREE,'files':files})
sums=[]
for path in sorted(OUT.iterdir()):
    if path.is_file() and path.name!='SHA256SUMS': sums.append(f'{sha(path.read_bytes())}  {path.name}')
(OUT/'SHA256SUMS').write_text('\n'.join(sums)+'\n',encoding='utf-8')
print(json.dumps({'summary':summary,'outputDirectory':str(OUT),'fileCount':len(sums)},ensure_ascii=False,indent=2))
