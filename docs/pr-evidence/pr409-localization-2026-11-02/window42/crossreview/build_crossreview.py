from __future__ import annotations
import hashlib, json, re, subprocess, collections, os
from pathlib import Path

OUT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window42-crossreview-independent-20261102')
PRIMARY = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window42-primary-20261102')
BUNDLE = Path('/mnt/disks/scratch/task-worktrees/localization-20261030/slskdn-populated-review-4c2b-20261101/bundle')
REPO = OUT / 'source-copy'
HEAD_EXPECTED = '1b518a69d099032c497149102751271eddb0fa57'
TREE_EXPECTED = 'c7f351a3507a3758a10369632feeb7a001e83aeb'
LOCALes = ['zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
ALL_LOCALES = LOCALes + ['es']
PH = re.compile(r'\{[A-Za-z_][A-Za-z0-9_]*\}')
MARK = re.compile(r'</?([A-Za-z][A-Za-z0-9:_-]*)(?:\s[^<>]*?)?\s*/?>')
checks=[]

def sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def shat(s: str) -> str: return sha(s.encode('utf-8'))
def read_json(p: Path): return json.loads(p.read_text(encoding='utf-8'))
def read_jl(p: Path): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args], text=True).strip()
def git_bytes(path: str, rev='HEAD') -> bytes: return subprocess.check_output(['git','-C',str(REPO),'show',f'{rev}:{path}'])
def addcheck(name, ok, detail=None):
    checks.append({'check':name,'passed':bool(ok),'detail':detail})
    if not ok: raise RuntimeError(f'check failed: {name}: {detail}')
def dump_json(name, obj): (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def dump_jl(name, rows): (OUT/name).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')

# Verify the primary packet itself before using its records.
primary_sums = PRIMARY/'SHA256SUMS.txt'
sum_lines = [x for x in primary_sums.read_text().splitlines() if x.strip()]
primary_sum_results=[]
for line in sum_lines:
    expected, name = line.split(None,1); name=name.lstrip('* ')
    actual=sha((PRIMARY/name).read_bytes())
    primary_sum_results.append({'path':name,'expectedSha256':expected,'actualSha256':actual,'matches':actual==expected})
addcheck('primary_packet_checksums', all(x['matches'] for x in primary_sum_results), f'{len(primary_sum_results)} files')
addcheck('primary_sum_file_sha', sha(primary_sums.read_bytes())=='f72d022763fd048482b2c4108e5136ebfed1afffb21afcde94060b99ab92aef5', sha(primary_sums.read_bytes()))

# Exact Git object and live PR attestation.
head=git('rev-parse','HEAD'); tree=git('rev-parse','HEAD^{tree}'); status=git('status','--porcelain')
source_tree=git('rev-parse','HEAD:src/web/src'); locale_tree=git('rev-parse','HEAD:src/web/public/locales')
addcheck('source_clone_head',head==HEAD_EXPECTED,head)
addcheck('source_clone_tree',tree==TREE_EXPECTED,tree)
addcheck('source_subtree_tree',source_tree=='594e56c3f439bad476b1bd57e0de1665c62fa1bb',source_tree)
addcheck('locale_subtree_tree',locale_tree=='dd773ad577db8f4bb9274140d297ebad2da7dd92',locale_tree)
object_snapshot=(git('rev-parse','--show-toplevel')==str(REPO) and {p.name for p in REPO.iterdir()}=={'.git'})
addcheck('source_clone_is_object_only_snapshot',object_snapshot,{'root':git('rev-parse','--show-toplevel'),'rootEntries':[p.name for p in REPO.iterdir()]})
pr=json.loads(subprocess.check_output(['gh','api','repos/snapetech-org/slskdN/pulls/409'],text=True))
pr_state={'repository':'snapetech-org/slskdN','pullRequest':409,'url':pr['html_url'],'state':pr['state'],'draft':pr['draft'],'headCommit':pr['head']['sha'],'headTree':git('rev-parse',f"{pr['head']['sha']}^{{tree}}"),'base':pr['base']['ref']}
addcheck('live_pr_open_draft_exact_head',pr_state['state']=='open' and pr_state['draft'] is True and pr_state['headCommit']==HEAD_EXPECTED and pr_state['headTree']==TREE_EXPECTED,pr_state)

# Catalog bytes, ordered keys, source strings, and all W42 target cells.
catalogs={}; catmeta=[]; ordered=None
catalog_ref=read_json(PRIMARY/'catalog-attestation.json')
for loc in ALL_LOCALES:
    path=f'src/web/public/locales/{loc}.json'; raw=git_bytes(path); data=json.loads(raw); keys=list(data)
    kh=sha(json.dumps(keys,ensure_ascii=False,separators=(',',':')).encode('utf-8'))
    if ordered is None: ordered=keys
    addcheck(f'{loc}_catalog_key_count',len(keys)==6169,len(keys))
    addcheck(f'{loc}_ordered_key_sha',kh==catalog_ref['orderedKeySetSha256'],kh)
    ref=next(x for x in catalog_ref['catalogs'] if x['locale']==loc)
    blob=git('rev-parse',f'HEAD:{path}')
    addcheck(f'{loc}_catalog_blob',blob==ref['gitBlobOid'],blob)
    addcheck(f'{loc}_catalog_file_sha',sha(raw)==ref['fileSha256'],sha(raw))
    catalogs[loc]=data
    catmeta.append({'locale':loc,'path':path,'gitBlobOid':blob,'fileSha256':sha(raw),'entryCount':len(keys),'orderedKeySetSha256':kh})
addcheck('all_catalogs_same_ordered_keys',all(list(x)==ordered for x in catalogs.values()),len(ordered))
addcheck('ordered_keys_digest',sha(json.dumps(ordered,ensure_ascii=False,separators=(',',':')).encode())=='0c92b6b652164b8fa80a7b4bf4ad58c529b0bf07ecdb97bf7341e408915dc747',len(ordered))

source_rows=read_jl(PRIMARY/'source-slice.jsonl')
inputs=read_jl(PRIMARY/'review-input.jsonl')
decisions=read_jl(PRIMARY/'review-decisions.jsonl')
candidates=read_jl(PRIMARY/'correction-candidates.jsonl')
caller_att=read_jl(PRIMARY/'caller-attestation.jsonl')
source_by={r['sourceId']:r for r in source_rows}
input_by={r['id']:r for r in inputs}
dec_by={r['id']:r for r in decisions}
cand_by={r['id']:r for r in candidates}
addcheck('source_slice_25_ordinals',len(source_rows)==25 and [r['sourceOrdinal'] for r in source_rows]==list(range(51,76)),len(source_rows))
addcheck('current_cells_275',len(inputs)==275 and len({r['id'] for r in inputs})==275, len(inputs))
addcheck('decision_cells_match_inputs',set(input_by)=={r['id'] for r in decisions},len(decisions))
addcheck('locale_distribution_25_each',collections.Counter(r['locale'] for r in inputs)==collections.Counter({l:25 for l in LOCALes}),dict(collections.Counter(r['locale'] for r in inputs)))
addcheck('candidates_47',len(candidates)==47 and set(cand_by)=={r['id'] for r in decisions if r['candidateTarget'] is not None},len(candidates))
addcheck('all_exact_head_tree_tags',all(r['exactHead']==HEAD_EXPECTED and r['exactTree']==TREE_EXPECTED for r in inputs+decisions+candidates), 'review rows and candidates')

# Reattest full callsites and full file bytes at the pinned tree.
caller_rows=[]; seen_refs=set()
for s in source_rows:
    source=s['source']; sid=s['sourceId']
    source_hash=shat(source)
    addcheck(f'{sid}_source_hash',source_hash==s['sourceSha256'] and sid=='src_'+source_hash[:16],source_hash)
    addcheck(f'{sid}_source_keys_present',all(source in catalogs[l] for l in ALL_LOCALES),source)
    for call in s['sourceCallsites']:
        path=call['path']; raw=git_bytes(path); lines=raw.decode('utf-8').splitlines(); line=call['line']
        exact_line=lines[line-1] if 1<=line<=len(lines) else None
        file_sha=sha(raw); line_sha=shat(call['lineText'])
        ok=exact_line is not None and exact_line.strip()==call['lineText'] and file_sha==call['fileSha256'] and line_sha==call['lineTextSha256']
        addcheck(f'{sid}_caller_{path}_{line}',ok,{'line':line,'fileSha256':file_sha,'lineTextSha256':line_sha})
        seen_refs.add((sid,path,line))
        caller_rows.append({'sourceId':sid,'sourceOrdinal':s['sourceOrdinal'],'source':source,'sourceSha256':source_hash,'path':path,'line':line,'lineText':exact_line,'lineTextSha256':line_sha,'fileSha256':file_sha,'verified':ok})
    for ctx in s['sourceContexts']:
        joined='\n'.join(git_bytes(c['path']).decode('utf-8') for c in s['sourceCallsites']) if s['sourceCallsites'] else ''
        addcheck(f'{sid}_context_fragment_{len(ctx)}',all(part in joined for part in ctx.split(' | ')),ctx[:300])
# One independent attestation row for every unique source/caller edge.
att_refs={(r['sourceId'],r['path'],r['line']):r for r in caller_att}
addcheck('caller_attestation_41',len(caller_att)==41 and len(seen_refs)==41 and set(att_refs)==seen_refs,{'attestation':len(caller_att),'uniqueRefs':len(seen_refs)})
for ref,r in att_refs.items():
    matched=next(x for x in caller_rows if (x['sourceId'],x['path'],x['line'])==ref)
    ok=r['verified'] is True and r['fileSha256']==matched['fileSha256'] and r['lineTextSha256']==matched['lineTextSha256'] and r['sourceSha256']==matched['sourceSha256']
    addcheck(f'caller_attest_{r["sourceId"]}_{r["line"]}',ok,ref)

# Recompute structural invariants (placeholders, source markup tokens, protected literals).
structural=[]; cell_rows=[]; candidate_judgments=[]; candidate_structural=[]; failures=[]
for r in inputs:
    s=source_by[r['sourceId']]; did=r['id']; d=dec_by[did]; loc=r['locale']; target=catalogs[loc][r['catalogKey']]
    target_sha=shat(target); source_sha=shat(s['source'])
    ph_src=sorted(PH.findall(s['source'])); ph_target=sorted(PH.findall(target))
    mark_src=sorted(MARK.findall(s['source'])); mark_target=sorted(MARK.findall(target))
    protected_missing=[x for x in s['protectedLiterals'] if x not in target]
    valid=(target==r['currentTarget']==d['currentTarget'] and target_sha==r['currentTargetSha256']==d['currentTargetSha256'] and source_sha==r['sourceSha256']==d['sourceSha256'] and ph_src==ph_target and mark_src==mark_target and not protected_missing)
    addcheck(f'cell_{did}_exact_source_current_hash',valid,{'sourceSha256':source_sha,'currentTargetSha256':target_sha})
    structural.append({'id':did,'locale':loc,'sourceOrdinal':s['sourceOrdinal'],'sourceSha256':source_sha,'currentTarget':target,'currentTargetSha256':target_sha,'placeholders':ph_target,'placeholderMismatch':ph_src!=ph_target,'sourceMarkupTokens':mark_src,'targetMarkupTokens':mark_target,'markupMismatch':mark_src!=mark_target,'protectedLiterals':s['protectedLiterals'],'protectedLiteralMismatches':protected_missing})
    c=cand_by.get(did)
    if c:
        ct=c['candidateTarget']; csha=shat(ct); cph=sorted(PH.findall(ct)); cmark=sorted(MARK.findall(ct)); cmiss=[x for x in s['protectedLiterals'] if x not in ct]
        cvalid=csha==c['candidateTargetSha256'] and cph==ph_src and cmark==mark_src and not cmiss and csha==d['candidateTargetSha256']
        addcheck(f'candidate_{did}_exact_hash_structure',cvalid,{'targetSha256':csha,'placeholderMismatch':cph!=ph_src,'markupMismatch':cmark!=mark_src,'protectedLiteralMismatches':cmiss})
        candidate_structural.append({'id':did,'sourceOrdinal':s['sourceOrdinal'],'locale':loc,'sourceSha256':source_sha,'candidateTarget':ct,'candidateTargetSha256':csha,'placeholders':cph,'placeholderMismatch':cph!=ph_src,'sourceMarkupTokens':mark_src,'candidateMarkupTokens':cmark,'markupMismatch':cmark!=mark_src,'protectedLiterals':s['protectedLiterals'],'protectedLiteralMismatches':cmiss})
        independent='accept-primary-candidate'
        rationale='Independent cross-review accepts the candidate against the pinned source and caller; exact hash, placeholder, markup, and protected-literal checks pass.'
        if s['sourceOrdinal']==67 and loc=='vi':
            rationale='Accept the narrow standalone direction repair with moderate confidence. The frozen inventory has no direct caller, so application should retain the packet’s no-caller limitation.'
        candidate_judgments.append({'id':did,'sourceOrdinal':s['sourceOrdinal'],'locale':loc,'source':s['source'],'sourceSha256':source_sha,'currentTarget':target,'currentTargetSha256':target_sha,'primaryDisposition':c['reviewDisposition'],'primaryCandidateTarget':ct,'primaryCandidateTargetSha256':csha,'independentOutcome':independent,'independentTarget':ct,'independentTargetSha256':csha,'confidence':('moderate' if s['sourceOrdinal']==67 and loc=='vi' else c['confidence']),'rationale':rationale,'callerRefs':s['sourceCallsites'],'contextScope':('standalone-text-only' if not s['sourceCallsites'] else 'pinned-caller-context')})
    # Semantic verdict recorded after independent full-source/caller review.
    if c:
        cross_disp='accept-primary-candidate'; final=ct; cross_reason=candidate_judgments[-1]['rationale']
    elif s['sourceOrdinal']==57 and loc=='hi':
        cross_disp='propose-additional-correction'; final='सर्वर सूची से सभी मेल खाने वाली पूर्ण हो चुकी पंक्तियाँ हटाएँ; पूरी हो चुकी फ़ाइलें डिस्क पर बनी रहेंगी।'
        cross_reason='The current phrase “मिलती-जुलती पूरी पंक्तियाँ” reads as similar/whole rows and blurs both “matching” (the selected/filter match) and the completed transfer state. The caller is the completed-transfer removal option; preserve the distinct completed-files-on-disk clause.'
    else:
        cross_disp='accept-current'; final=target; cross_reason='Independent review retains the current translation for the pinned caller or standalone context; exact source/current hashes and structural invariants pass.'
    cell_rows.append({'id':did,'window':42,'sourceOrdinal':s['sourceOrdinal'],'locale':loc,'catalogKey':r['catalogKey'],'source':s['source'],'sourceSha256':source_sha,'currentTarget':target,'currentTargetSha256':target_sha,'primaryDisposition':d['reviewDisposition'],'independentDisposition':cross_disp,'selectedTarget':final,'selectedTargetSha256':shat(final),'rationale':cross_reason,'sourceCallsites':s['sourceCallsites'],'sourceContexts':s['sourceContexts'],'placeholders':ph_src,'protectedLiterals':s['protectedLiterals'],'exactHead':HEAD_EXPECTED,'exactTree':TREE_EXPECTED})

# The added Hindi W57 target receives its own exact structural check.
missed=[r for r in cell_rows if r['independentDisposition']=='propose-additional-correction']
addcheck('one_additional_hindi_w57_fix',len(missed)==1 and missed[0]['id']=='hi:src_0db326ab6ce1e7c7',[(x['id'],x['selectedTarget']) for x in missed])
for r in missed:
    src=source_by[r['id'].split(':',1)[1]]['source']; target=r['selectedTarget']
    addcheck(f'{r["id"]}_supplemental_structure',sorted(PH.findall(src))==sorted(PH.findall(target)) and sorted(MARK.findall(src))==sorted(MARK.findall(target)) and all(x in target for x in source_by[r['id'].split(':',1)[1]]['protectedLiterals']),target)

# W42 current table spans every cell; candidate outcomes independently recorded.
addcheck('candidate_outcome_count_47',len(candidate_judgments)==47,len(candidate_judgments))
addcheck('current_cell_ledger_count_275',len(cell_rows)==275,len(cell_rows))
addcheck('no_current_or_candidate_structural_failures',all(not r['placeholderMismatch'] and not r['markupMismatch'] and not r['protectedLiteralMismatches'] for r in structural+candidate_structural),{'current':len(structural),'candidates':len(candidate_structural)})

# Reattest Spanish formal lane: preserve 25 exact current cells and emit no Spanish verdict.
spanish=read_jl(PRIMARY/'preserved-spanish-formal.jsonl')
spanish_rows=[]
for r in spanish:
    loc='es'; cur=catalogs[loc][r['catalogKey']]; cursha=shat(cur)
    ok=r['locale']==loc and r['exactHead']==HEAD_EXPECTED and r['exactTree']==TREE_EXPECTED and r['currentTarget']==cur and r['currentTargetSha256']==cursha and r['formalCellIdPresent'] is True
    addcheck(f'spanish_formal_{r["sourceId"]}',ok,{'id':r['id'],'targetSha256':cursha})
    spanish_rows.append({'id':r['id'],'locale':'es','sourceOrdinal':r['sourceOrdinal'],'sourceId':r['sourceId'],'source':r['source'],'sourceSha256':shat(r['source']),'catalogKey':r['catalogKey'],'currentTarget':cur,'currentTargetSha256':cursha,'preservationDisposition':'preserved; no W42 Spanish language verdict','exactHead':HEAD_EXPECTED,'exactTree':TREE_EXPECTED})
addcheck('spanish_formal_count_25',len(spanish_rows)==25,len(spanish_rows))

# W41 current-cell boundary, applied readbacks, previous holds, and Spanish rows.
w41att=read_json(PRIMARY/'w41-evidence-attestation.json')
w41dir=Path(w41att['evidence']['primary/review-input.jsonl']['path']).parent.parent
w41files=[]
for label,info in w41att['evidence'].items():
    path=Path(info['path']); raw=path.read_bytes(); rows=read_jl(path)
    ok=sha(raw)==info['sha256'] and len(rows)==info['rows']
    addcheck(f'w41_evidence_{label}',ok,{'path':str(path),'rows':len(rows),'sha256':sha(raw)})
    w41files.append({'label':label,'path':str(path),'rows':len(rows),'sha256':sha(raw),'verified':ok})
w41_cells=read_jl(PRIMARY/'w41-cell-reattestation.jsonl')
w41_review_input=read_jl(w41dir/'primary/review-input.jsonl')
w41_by={(r['locale'],r['sourceId']):r for r in w41_review_input}
w41_rows=[]
for r in w41_cells:
    loc=r['locale']; sid=r['sourceId']; key=r['source']; cat=catalogs[loc]; cur=cat[key]; cursha=shat(cur)
    ok=26<=r['sourceOrdinal']<=50 and r['currentTargetSha256']==cursha and r['sourceSha256']==shat(key) and r['matchesW41SelectedOutcome'] is True
    old=w41_by.get((loc,sid))
    ok=ok and old is not None and old['source']==key and old['sourceSha256']==shat(key) and r['w41SelectedTargetSha256']==cursha
    addcheck(f'w41_cell_{r["id"]}',ok,{'ordinal':r['sourceOrdinal'],'currentTargetSha256':cursha})
    w41_rows.append({'id':r['id'],'sourceOrdinal':r['sourceOrdinal'],'locale':loc,'sourceId':sid,'source':key,'sourceSha256':shat(key),'currentTarget':cur,'currentTargetSha256':cursha,'matchesW41SelectedOutcome':ok,'appliedInW41':r['appliedInW41'],'w41PrimaryDisposition':r['w41PrimaryDisposition'],'w41CrossReviewDisposition':r['w41CrossReviewDisposition'],'exactHeadAtW42':HEAD_EXPECTED})
addcheck('w41_cells_275_and_ordinals',len(w41_rows)==275 and {r['sourceOrdinal'] for r in w41_rows}==set(range(26,51)),len(w41_rows))
# W41 70 applied values must equal current exact catalog values and readback ledgers.
apply_plan=read_jl(w41dir/'apply-plan.jsonl'); readback=read_jl(w41dir/'readback.jsonl')
plan_by={(r['locale'],r['sourceId']):r for r in apply_plan}; rb_by={(r['locale'],r['sourceId']):r for r in readback}
readback_rows=[]
for key,p in plan_by.items():
    loc,sid=key; cur=catalogs[loc][p['catalogKey']]; cursha=shat(cur); rb=rb_by.get(key)
    ok=rb is not None and p['finalTargetSha256']==cursha==rb['targetSha256'] and rb['matchesReviewedTarget'] is True
    addcheck(f'w41_applied_readback_{loc}_{sid}',ok,{'targetSha256':cursha})
    readback_rows.append({'locale':loc,'sourceId':sid,'sourceOrdinal':p['sourceOrdinal'],'catalogKey':p['catalogKey'],'currentTarget':cur,'currentTargetSha256':cursha,'readbackMatches':ok,'w41FinalTargetSha256':p['finalTargetSha256']})
addcheck('w41_applied_readbacks_70',len(readback_rows)==70 and len(readback)==70,len(readback_rows))
# Historic holds: reattest current target plus original evidence ledger bytes/row.
holds=read_jl(PRIMARY/'preserved-prior-holds.jsonl'); hold_rows=[]
for h in holds:
    loc=h['locale']; catpath=h['catalogPath']; cur=catalogs[loc][h['catalogKey']]; cursha=shat(cur)
    ledger_rel=h['sourceHoldLedgerPath']; ledger_path=REPO/ledger_rel
    try: ledger_raw=git_bytes(ledger_rel); ledger_rows=[json.loads(x) for x in ledger_raw.decode().splitlines() if x.strip()]
    except Exception:
        ledger_raw=ledger_path.read_bytes(); ledger_rows=[json.loads(x) for x in ledger_raw.decode().splitlines() if x.strip()]
    source_record=next((x for x in ledger_rows if x.get('sourceId')==h['sourceId'] and x.get('locale')==loc),None)
    ok=h['currentTarget']==cur and h['currentTargetSha256']==cursha and h['unchanged'] is True and sha(ledger_raw)==h['sourceHoldLedgerSha256'] and source_record is not None
    addcheck(f'prior_hold_{h["id"]}',ok,{'currentTargetSha256':cursha,'ledgerSha256':sha(ledger_raw),'ledgerRowFound':source_record is not None})
    hold_rows.append({'id':h['id'],'locale':loc,'sourceId':h['sourceId'],'sourceOrdinal':None,'catalogKey':h['catalogKey'],'currentTarget':cur,'currentTargetSha256':cursha,'holdDisposition':h['holdDisposition'],'sourceHoldLedgerPath':ledger_rel,'sourceHoldLedgerSha256':sha(ledger_raw),'ledgerRowFound':source_record is not None,'preservedUnchanged':ok})
addcheck('prior_holds_50',len(hold_rows)==50,len(hold_rows))
# Cross-review preserved-holds evidence also pins the W41 rows and historic ledgers.
w41_hold_rows=read_jl(w41dir/'cross-review/preserved-holds-reattestation.jsonl')
addcheck('w41_hold_reattestation_50',len(w41_hold_rows)==50,len(w41_hold_rows))
# Reattest W41 Spanish lane evidence.
w41_es=read_jl(w41dir/'cross-review/preserved-spanish-reattestation.jsonl'); w41_es_rows=[]
for r in w41_es:
    loc='es'; cur=catalogs[loc][r['catalogKey']]; cursha=shat(cur)
    ok=r['currentTarget']==cur and r['currentTargetSha256Reattested']==cursha and r['formalCellIdPresent'] is True
    addcheck(f'w41_spanish_{r["sourceId"]}',ok,cursha)
    w41_es_rows.append({'id':r['id'],'sourceOrdinal':r['sourceOrdinal'],'sourceId':r['sourceId'],'catalogKey':r['catalogKey'],'currentTarget':cur,'currentTargetSha256':cursha,'formalCellIdPresent':True,'preserved':ok})
addcheck('w41_spanish_formal_25',len(w41_es_rows)==25,len(w41_es_rows))

# Previous/future selection boundary reconstruction from W1-W41 input digests and frozen pending bundle.
order=read_json(PRIMARY/'order-evidence.json')
manifest_raw=(BUNDLE/'manifest.json').read_bytes(); batches_raw=(BUNDLE/'batches.json').read_bytes()
addcheck('frozen_bundle_manifest_sha',sha(manifest_raw)==order['frozenBundleManifestSha256'],sha(manifest_raw))
addcheck('frozen_bundle_batches_sha',sha(batches_raw)==order['frozenBundleBatchesSha256'],sha(batches_raw))
manifest=json.loads(manifest_raw)
addcheck('bundle_manifest_head_tree',manifest['headCommit']=='4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb' and manifest['tree']=='0eb84397dc2b4be4afd730f6818203bd5910cf15',{'head':manifest['headCommit'],'tree':manifest['tree']})
prev_ids=set(); prev_att=[]
for att in order['priorWindowInputAttestations']:
    rawpath=att['path']
    if rawpath.startswith('scratch:'):
        path=Path('/mnt/disks/scratch')/rawpath[len('scratch:'):]
    else: path=Path(rawpath)
    raw=path.read_bytes(); rows=[json.loads(x) for x in raw.decode('utf-8').splitlines() if x.strip()]
    ids={r['sourceId'] for r in rows}
    ok=sha(raw)==att['sha256'] and len(rows)==att['rows'] and len(ids)==att['uniqueSourceIds']
    addcheck(f'prior_window_input_{att["window"]}',ok,{'rows':len(rows),'sha256':sha(raw),'uniqueSourceIds':len(ids)})
    prev_ids.update(ids)
    prev_att.append({'window':att['window'],'path':str(path),'rows':len(rows),'sha256':sha(raw),'uniqueSourceIds':len(ids),'verified':ok})
addcheck('prior_windows_1_to_41_unique_source_ids',len(prev_ids)==order['w1Through41UniqueSourceIds']==1022,len(prev_ids))
# Ensure the distinct pending source ID inventory agrees in each non-Spanish locale.
pending_by_locale={}
for loc in LOCALes:
    rows=read_jl(BUNDLE/'pending'/f'{loc}.jsonl'); pending_by_locale[loc]={r['sourceId']:r for r in rows}
    addcheck(f'{loc}_pending_inventory_nonempty',bool(pending_by_locale[loc]),len(pending_by_locale[loc]))
pending_union=set().union(*(set(x) for x in pending_by_locale.values()))
addcheck('nonspanish_pending_source_id_union_count',len(pending_union)==order['frozenNonSpanishPendingSourceIdCount']==5650,len(pending_union))
remaining=sorted(pending_union-prev_ids)
addcheck('remaining_pending_count',len(remaining)==order['remainingSourceIdsBeforeW42']==4628,len(remaining))
w42_ids=[r['sourceId'] for r in source_rows]
addcheck('w42_selection_is_next_25',remaining[:25]==w42_ids and order['selectionReproduced'] is True,remaining[:25])
w43_ids=remaining[25:50]
addcheck('w43_future_boundary_25',len(w43_ids)==25 and len(set(w43_ids))==25,w43_ids)
# Confirm frozen bundle source rows and exact-current W43 source/targets at pinned W42 tree.
all_by_loc={}
for loc in LOCALes:
    all_rows=read_jl(BUNDLE/'all'/f'{loc}.jsonl')
    all_by_loc[loc]={r['sourceId']:r for r in all_rows}
w43_rows=[]
for n,sid in enumerate(w43_ids,76):
    baseline=all_by_loc[LOCALes[0]][sid]; source=baseline['source']; source_sha=shat(source)
    ok=all(all_by_loc[l][sid]['source']==source and all_by_loc[l][sid]['sourceSha256']==source_sha for l in LOCALes)
    addcheck(f'w43_source_{sid}',ok,{'ordinal':n,'source':source,'sourceSha256':source_sha})
    for loc in LOCALes:
        key=source; target=catalogs[loc][key]; t_sha=shat(target)
        w43_rows.append({'window':43,'sourceOrdinal':n,'sourceId':sid,'locale':loc,'source':source,'sourceSha256':source_sha,'catalogKey':key,'currentTarget':target,'currentTargetSha256':t_sha,'catalogBlobOid':git('rev-parse',f'HEAD:src/web/public/locales/{loc}.json'),'exactHead':HEAD_EXPECTED,'exactTree':TREE_EXPECTED,'futureBoundaryOnly':True})
addcheck('w43_cells_275',len(w43_rows)==275,len(w43_rows))
# W42 frozen-bundle source identity and previous window exact ordinal edge.
w42_bundle_rows=[]
for s in source_rows:
    for loc in LOCALes:
        b=all_by_loc[loc].get(s['sourceId']); ok=b is not None and b['source']==s['source'] and b['sourceSha256']==s['sourceSha256']
        addcheck(f'w42_bundle_source_{loc}_{s["sourceId"]}',ok,s['source'])
        w42_bundle_rows.append({'sourceOrdinal':s['sourceOrdinal'],'sourceId':s['sourceId'],'locale':loc,'source':s['source'],'sourceSha256':s['sourceSha256'],'frozenTarget':b['target'],'frozenTargetSha256':b['targetSha256'],'frozenDisposition':b['reviewDisposition'],'exactHead':HEAD_EXPECTED,'exactTree':TREE_EXPECTED})
addcheck('w42_bundle_cells_275',len(w42_bundle_rows)==275,len(w42_bundle_rows))

# W41/W42/W43 explicit sequence edge.
w41_ids=sorted({r['sourceId'] for r in w41_cells},key=lambda sid: next(r['sourceOrdinal'] for r in w41_cells if r['sourceId']==sid))
addcheck('w41_w42_w43_ordinals_contiguous',len(w41_ids)==25 and len(w42_ids)==25 and len(w43_ids)==25 and not (set(w41_ids)&set(w42_ids) or set(w42_ids)&set(w43_ids)),{'W41':len(w41_ids),'W42':len(w42_ids),'W43':len(w43_ids)})

# Prior exact French reuse provenance.
reuse=read_jl(PRIMARY/'prior-exact-reuse-reattestation.jsonl')
reuse_rows=[]
for r in reuse:
    path=Path(r['evidencePath']); raw=path.read_bytes()
    source=r['source']; target=catalogs[r['locale']][source]; target_sha=shat(target)
    ok=sha(raw)==r['evidenceSha256'] and r['exactSourceAndTargetHashesMatch'] is True and shat(source)==r['sourceSha256']==r['targetSha256'] and target==r['target'] and target_sha==r['currentTargetSha256']
    addcheck(f'prior_exact_reuse_{r["id"]}',ok,{'evidenceSha256':sha(raw),'targetSha256':target_sha})
    reuse_rows.append({'id':r['id'],'locale':r['locale'],'source':source,'sourceSha256':shat(source),'currentTarget':target,'currentTargetSha256':target_sha,'reuseVerdict':r['reuseVerdict'],'evidencePath':r['evidencePath'],'evidenceSha256':sha(raw),'evidenceVerified':ok})

# Last live PR read before finalizing the packet.
pr_end=json.loads(subprocess.check_output(['gh','api','repos/snapetech-org/slskdN/pulls/409'],text=True))
end_state={'state':pr_end['state'],'draft':pr_end['draft'],'headCommit':pr_end['head']['sha'],'headTree':git('rev-parse',f"{pr_end['head']['sha']}^{{tree}}")}
addcheck('live_pr_unchanged_at_finish',end_state=={'state':'open','draft':True,'headCommit':HEAD_EXPECTED,'headTree':TREE_EXPECTED},end_state)

# Export all reattestation ledgers and findings.
dump_jl('caller-reattestation.jsonl',caller_rows)
dump_jl('current-cell-reattestation.jsonl',cell_rows)
dump_jl('candidate-crossreview.jsonl',candidate_judgments)
dump_jl('structural-reattestation.jsonl',structural+candidate_structural)
dump_jl('supplemental-missed-fixes.jsonl',missed)
dump_jl('spanish-formal-preservation.jsonl',spanish_rows)
dump_jl('w41-cell-boundary-reattestation.jsonl',w41_rows)
dump_jl('w41-applied-readback-reattestation.jsonl',readback_rows)
dump_jl('w41-prior-hold-reattestation.jsonl',hold_rows)
dump_jl('w41-spanish-formal-reattestation.jsonl',w41_es_rows)
dump_jl('w42-frozen-bundle-source-reattestation.jsonl',w42_bundle_rows)
dump_jl('w43-future-boundary-reattestation.jsonl',w43_rows)
dump_jl('prior-window-input-attestation.jsonl',prev_att)
dump_jl('w41-evidence-file-attestation.jsonl',w41files)
dump_jl('prior-exact-reuse-reattestation.jsonl',reuse_rows)
dump_json('catalog-reattestation.json',{'repository':'snapetech-org/slskdN','pullRequest':409,'headCommit':HEAD_EXPECTED,'tree':TREE_EXPECTED,'sourceSubtreeTree':source_tree,'localeCatalogSubtreeTree':locale_tree,'orderedKeyCountPerLocale':6169,'orderedKeySetSha256':sha(json.dumps(ordered,ensure_ascii=False,separators=(',',':')).encode()),'catalogs':catmeta,'allCatalogsHaveSameOrderedKeys':True})
dump_json('live-pr-reattestation.json',{'start':pr_state,'finish':end_state,'unchangedAtPinnedHead':True})

counts=collections.Counter(r['independentDisposition'] for r in cell_rows)
primary_counts=collections.Counter(r['reviewDisposition'] for r in decisions)
summary={'result':'INDEPENDENT_CROSS_REVIEW_COMPLETE_PENDING_NATIVE_SPEAKER_REVIEW','window':42,'pullRequest':409,'headCommit':HEAD_EXPECTED,'tree':TREE_EXPECTED,'sourceSubtreeTree':source_tree,'localeCatalogSubtreeTree':locale_tree,'prOpenDraftExactHead':True,'sourceOrdinals':{'previous':[26,50],'reviewed':[51,75],'future':[76,100]},'reviewedKeys':25,'reviewedNonSpanishCells':275,'priorDispositionCounts':dict(primary_counts),'independentCellDispositionCounts':dict(counts),'primaryCandidates':47,'primaryCandidateOutcomes':{'accepted':len(candidate_judgments),'rejected':0,'held':0},'additionalMissedFixes':len(missed),'independentChangedTargets':len(candidate_judgments)+len(missed),'changedTargetLocales':dict(collections.Counter(r['locale'] for r in candidate_judgments+missed)),'currentCellsReattested':len(structural),'candidateTargetsReattested':len(candidate_structural),'callerPinsReattested':len(caller_rows),'uniqueCallerReferences':len(seen_refs),'priorWindowsRehashed':len(prev_att),'priorUniqueSourceIds':len(prev_ids),'previousW41CellsReattested':len(w41_rows),'w41AppliedReadbacksReattested':len(readback_rows),'priorHoldsPreserved':len(hold_rows),'w41SpanishFormalRowsPreserved':len(w41_es_rows),'w42SpanishFormalRowsPreserved':len(spanish_rows),'futureW43CellsReattested':len(w43_rows),'frozenBundleManifestSha256':sha(manifest_raw),'frozenBundleBatchesSha256':sha(batches_raw),'w42SelectionReproduced':True,'w43BoundaryDerived':True,'priorExactReuseRowsReattested':len(reuse_rows),'structuralFailures':0,'nativeSpeakerReview':'outstanding','readOnly':True,'extraFinding':'Hindi W57 current wording should be revised to distinguish matching completed rows from the files left on disk.','retainedRepoChanges':0,'checks':len(checks),'allChecksPassed':all(x['passed'] for x in checks)}
dump_json('crossreview-summary.json',summary)
dump_jl('verification-checks.jsonl',checks)

readme=f'''# slskdN PR #409 W42 independent cross-review\n\n- Live PR state: open/draft at `{HEAD_EXPECTED}` / tree `{TREE_EXPECTED}` at start and finish.\n- Scope: 25 source keys (ordinals 51–75), all 275 non-Spanish current cells, 47 primary candidates, 41 direct caller references, and W41/W43 boundaries.\n- Independent candidate outcomes: accepted all 47 primary proposals; found one additional Hindi correction for W57 (`Remove all matching completed rows...`).\n- The W67 Vietnamese proposal is accepted with moderate confidence as a standalone direction repair; there is no direct caller in the pinned inventory.\n- Previous/future boundary: W41 ordinals 26–50 and W43 ordinals 76–100 were reattested. Selection was reconstructed from the frozen pending bundle after hashing W1–W41 inputs.\n- W41 applied readbacks, 50 prior holds, W41 Spanish formal lane, and W42 Spanish formal cells were preserved and reattested.\n- Placeholders, markup, protected literals, source hashes, target hashes, caller file hashes/line text, and exact catalog objects passed.\n- Native-speaker review remains outstanding. This packet is read-only; it does not apply the accepted candidates or the additional fix.\n\nSee `crossreview-summary.json`, `verification-checks.jsonl`, and the per-cell/per-boundary JSONL ledgers for details. `SHA256SUMS.txt` covers packet files except itself.\n'''
(OUT/'README.md').write_text(readme,encoding='utf-8')
# Hash everything except the checksum manifest.
files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt')
(OUT/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.name}\n' for p in files),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
print('packet files',len(files)+1,'size_bytes',sum(p.stat().st_size for p in OUT.iterdir() if p.is_file()))
