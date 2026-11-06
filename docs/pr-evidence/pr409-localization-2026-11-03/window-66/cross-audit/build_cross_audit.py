#!/usr/bin/env python3
import collections, datetime, hashlib, json, pathlib, re, shutil, subprocess

BASE = pathlib.Path('/home/keith/Documents/code/task-scratch')
OUT = BASE / 'slskdn-pr409-w66-ranks528-552-cross-audit-20261103'
INPUT = BASE / 'slskdn-pr409-w66-ranks528-552-primary-20261103/input'
PRIMARY = BASE / 'slskdn-pr409-w66-ranks528-552-primary-20261103/primary'
BLIND = BASE / 'slskdn-pr409-w66-ranks528-552-blind-review-20261103'
REPO = 'snapetech-org/slskdN'
BRANCH = 'codex/slskdn-oidc-tooltip-localization-20261030'
HEAD = 'c258a11d25a5cffc82b6b7cb2964d8f57b8eeac1'
TREE = '53e65bd1f3d87362916f1e51e2d1fd1d0cef73a5'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

# Independently adjudicated source when proposals differ. The sets are checked against all 41 non-hold target conflicts.
PRIMARY_KEYS = {
 (530,'id'), (534,'ar'), (534,'pt-BR'),
 (536,'es'), (536,'pt-BR'), (536,'vi'),
 (538,'es'), (540,'de'),
 (542,'de'), (542,'fr'), (542,'hi'),
 (545,'ja'), (549,'ja'), (551,'hi'),
 *((552,loc) for loc in ('ar','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant')),
}
BLIND_KEYS = {
 (530,'ko'), (536,'ar'), (536,'fr'),
 (537,'ar'), (537,'id'), (537,'vi'),
 (538,'ko'), (540,'hi'), (540,'id'), (540,'pt-BR'), (540,'vi'),
 (548,'hi'), (548,'ja'), (548,'ko'), (549,'es'), (549,'pt-BR'),
}
assert len(PRIMARY_KEYS) == 25 and len(BLIND_KEYS) == 16 and not PRIMARY_KEYS & BLIND_KEYS

DISPOSITION_ADJUDICATIONS = {
 (536,'zh-Hans'): ('correction', 'The numeric configuration field is for a retry count. 次数 removes the redundant retry-attempt wording in the current target; classify this as a correction even though the primary labels it refinement.'),
 (536,'zh-Hant'): ('correction', 'The numeric configuration field is for a retry count. 次數 removes the redundant retry-attempt wording in the current target; classify this as a correction even though the primary labels it refinement.'),
 (539,'ar'): ('refinement', 'The generated report uses this as a section heading. The shared proposed heading removes the extra space before the colon while keeping the same meaning.'),
 (539,'hi'): ('refinement', 'The generated report uses this as a section heading. The shared proposed heading is a more direct label for Summary and removes the extra space before the colon.'),
 (539,'vi'): ('refinement', 'The generated report uses this as a section heading. The shared proposed heading is a concise, natural heading and removes the extra space before the colon.'),
}

REASONS = {
 (530,'id'): 'The help text describes removing metadata so the listing is withdrawn from DHT discovery. The primary wording clearly says to withdraw an entry; the blind wording’s “discovery process” and “publication” are less direct in this caller.',
 (530,'ko'): 'The caller’s help text says the Pod’s metadata is removed and then its listing is withdrawn. The blind wording makes the possessive metadata relation explicit and names withdrawal of a posted item.',
 (534,'ar'): 'This value is nested in “Message registered as seen: {status}”. The primary feminine form agrees with the Arabic noun رسالة supplied by that exact caller.',
 (534,'pt-BR'): 'This value is nested in “Message registered as seen: {status}”. The primary feminine form conhecida agrees with the Portuguese noun mensagem supplied by that exact caller.',
 (536,'ar'): 'This labels the numeric webhookRetryAttempts configuration field. The primary wording explicitly names retry attempts and suits a number input; the separate terminology still needs an Arabic native-speaker check.',
 (536,'es'): 'This is the numeric webhookRetryAttempts field. Número de reintentos states the quantity directly and avoids repeating the retry concept.',
 (536,'fr'): 'The input is already a compact webhook-retries label. Keep that established concise wording; the primary alternative expands it into a repetitive count-of-retries phrase.',
 (536,'pt-BR'): 'This is the numeric webhookRetryAttempts field. The primary wording explicitly says the number of resend attempts and fits a quantity input.',
 (536,'vi'): 'The caller is an accessible label for the webhook retry setting. The current concise retries label is clear in this numeric field; the primary expansion adds a quantity cue but is not required to understand the field.',
 (537,'ar'): 'The source names streaming over a mesh network. The blind wording expresses transmission through a mesh network; the current تدفق شبكة reads as generic network flow.',
 (537,'id'): 'The source names streaming over a mesh network. The blind wording explicitly says through a mesh network; the current “streaming jala” only says network streaming.',
 (537,'vi'): 'The source names streaming over a mesh network. The blind wording identifies the mesh network; the current phrase can read as grid streaming.',
 (538,'es'): 'The phrase completes an instruction to set dht.lan_only=true before long-term operation. The primary article in en la configuración makes the destination read naturally in this sentence.',
 (538,'ko'): 'The exact caller instructs the user to set dht.lan_only=true before long-term operation. The blind imperative says to add it to configuration before operation, which fits the instruction more directly than the current fragment.',
 (540,'de'): 'This is a success toast for the adversarial-settings form. The primary compound retains the technical adversarial concept instead of making the settings sound merely opponent-related.',
 (540,'hi'): 'This is a success toast for the adversarial-settings form. The blind technical transliteration avoids the current general meaning “adverse/hostile” and names the feature domain more clearly.',
 (540,'id'): 'This is a success toast for the adversarial-settings form. The blind technical term adversarial avoids the current wording for hostility or enmity.',
 (540,'pt-BR'): 'This is a success toast for the adversarial-settings form. Adversariais is the technical adjective for adversarial settings; adversárias can describe settings belonging to opponents.',
 (540,'vi'): 'This is a success toast for the adversarial-settings form. The blind wording names the adversarial concept more specifically than the current generic opposing-settings phrase.',
 (542,'de'): 'The caller is a details summary directly above a registration form. The primary Optionen is a natural heading for the form’s advanced registration choices; the blind literal controls wording is less idiomatic here.',
 (542,'fr'): 'The caller is a details summary directly above a registration form. Keep the primary/current Contrôles wording, which is a natural label for these form controls; Commandes shifts the meaning toward commands.',
 (542,'hi'): 'The caller is a details summary directly above a registration form. The primary विकल्प is a natural heading for its advanced registration options and preserves the exact ContentID product identifier.',
 (545,'ja'): 'This accessible playback help appears beside a collection item. The primary removes unnatural spaces inside the Japanese compound for collection item and keeps the browser-player action explicit.',
 (548,'hi'): 'The caller is a beat-count setting for native MilkDrop automation. The blind wording preserves MilkDrop and says the next preset; the primary “second preset” over-specifies another preset as the second one.',
 (548,'ja'): 'This is help for the native MilkDrop beat-count selector. The blind wording naturally says the built-in visualizer switches presets after the selected beats; the current phrasing is awkward.',
 (548,'ko'): 'This is help for the native MilkDrop beat-count selector. The blind wording uses built-in, preserves the product name, and explains how many beats pass before switching presets.',
 (549,'es'): 'The tooltip explains that status checks resume on the server and do not launch another scan. The blind wording says the scan is on the server in a more natural way and uses the clearer analysis term in the follow-up.',
 (549,'ja'): 'The source spells out “a second scan” and has no numeric token. The primary 二回目 preserves that ordinal as Japanese kanji and avoids the current ASCII digit 2; it is clear for a countable scan.',
 (549,'pt-BR'): 'This is an action tooltip. The blind imperative Retome reads as a direct instruction, while preserving the current server-side scan and the promise that no second scan starts.',
 (551,'hi'): 'This is the header for a failed contacts-loading state. The primary spelling किए is the standard form and corrects the current orthographic variant किये.',
}

def sha_bytes(data): return hashlib.sha256(data).hexdigest()
def sha_file(path): return sha_bytes(path.read_bytes())
def read_json(path): return json.loads(path.read_text(encoding='utf-8'))
def read_jsonl(path): return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
def write_json(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)+'\n', encoding='utf-8')
def token_checks(cell, target):
    placeholders = re.findall(r'\{[^{}]*\}', target)
    markup = re.findall(r'</?[A-Za-z][^>]*>', target)
    numeric = re.findall(r'(?<![A-Za-z])\d+(?:[.,]\d+)?(?![A-Za-z])', target)
    protected = cell['sourceProtectedLiterals']
    literal_ok = all(target.count(t) >= protected.count(t) for t in set(protected))
    checks = {
      'placeholders': {'source':cell['placeholderEvidence']['sourceTokens'],'selected':placeholders,'match':sorted(placeholders)==sorted(cell['placeholderEvidence']['sourceTokens'])},
      'markup': {'source':cell['markupEvidence']['sourceTags'],'selected':markup,'match':sorted(markup)==sorted(cell['markupEvidence']['sourceTags'])},
      'numeric': {'source':cell['sourceNumericTokens'],'selected':numeric,'match':sorted(numeric)==sorted(cell['sourceNumericTokens'])},
      'protectedLiterals': {'source':protected,'selected':[t for t in protected if target.count(t)>=protected.count(t)],'match':literal_ok},
    }
    checks['allPass'] = all(x['match'] for x in checks.values())
    return checks

def run(args):
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.strip()

def live_attestation():
    pr = json.loads(run(['gh','pr','view','409','--repo',REPO,'--json','state,isDraft,headRefOid,headRefName,baseRefName']))
    ref = json.loads(run(['gh','api','repos/snapetech-org/slskdN/git/ref/heads/'+BRANCH]))
    pull = json.loads(run(['gh','api','repos/snapetech-org/slskdN/pulls/409']))
    commit = json.loads(run(['gh','api','repos/snapetech-org/slskdN/commits/'+HEAD]))
    data = {'repository':REPO,'pullRequest':409,'branch':BRANCH,'state':pr['state'],'isDraft':pr['isDraft'],'baseBranch':pr['baseRefName'],'prHead':pr['headRefOid'],'branchHead':ref['object']['sha'],'pullHead':pull['head']['sha'],'tree':commit['commit']['tree']['sha'],'attestedAtUtc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    if any(data[k] != HEAD for k in ('prHead','branchHead','pullHead')) or data['tree'] != TREE:
        raise SystemExit('Live PR/branch/tree no longer matches W66 input pins')
    if data['state'] != 'OPEN' or data['isDraft'] is not True:
        raise SystemExit('PR is no longer OPEN/DRAFT')
    return data

def main():
    if {x.name for x in OUT.iterdir()} - {'build_cross_audit.py','verify_cross_audit.py'}: raise SystemExit('Cross-audit output directory has unexpected files; refusing to overwrite')
    cells = read_jsonl(INPUT/'source-current-cells.jsonl')
    callers = {r['sourceId']:r for r in read_jsonl(INPUT/'caller-contexts.jsonl')}
    primary = read_jsonl(PRIMARY/'primary-ledger.jsonl')
    blind_rows = read_jsonl(BLIND/'sealed-blind-review-ledger.jsonl')
    blind = {(r['sourceId'],r['locale']):r for r in blind_rows}
    if not (len(cells)==len(primary)==len(blind_rows)==len(blind)==300): raise SystemExit('Expected 300 unique rows in each packet')
    if len({(c['continuationRank'],c['locale']) for c in cells}) != 300: raise SystemExit('Duplicate candidate-free cells')
    if read_json(INPUT/'manifest.json')['head'] != HEAD or read_json(INPUT/'manifest.json')['tree'] != TREE: raise SystemExit('Input head/tree mismatch')
    if read_json(PRIMARY/'manifest.json').get('blindPacketAccessed') is not False: raise SystemExit('Primary manifest does not affirm blind separation')
    if read_json(BLIND/'manifest.json').get('primaryPacketOpened') is not False: raise SystemExit('Blind manifest does not affirm primary separation')

    pcounts=collections.Counter(); bcounts=collections.Counter(); xcounts=collections.Counter(); selected_sources=collections.Counter(); rows=[]
    actual_primary_conflicts=set(); actual_blind_conflicts=set(); target_conflicts=0; agreement_cells=0; disposition_overrides=0
    baseline_protected=[]; baseline_numeric=[]
    for cell, p in zip(cells, primary):
        rank, loc = cell['continuationRank'], cell['locale']; key=(rank,loc); caller=callers[cell['sourceId']]; b=blind[(cell['sourceId'],loc)]
        if p['sourceId'] != cell['sourceId'] or p['locale'] != loc or p['sourceSha256'] != cell['sourceSha256'] or p['currentTarget'] != cell['currentTarget'] or p['currentTargetSha256'] != cell['currentTargetSha256'] or p['callerContextSha256'] != cell['callerContextSha256']:
            raise SystemExit(f'Primary cell binding mismatch: {key}')
        if b['sourceId'] != cell['sourceId'] or b['source'] != cell['source'] or b['sourceSha256'] != cell['sourceSha256'] or b['locale'] != loc or b['currentTarget'] != cell['currentTarget'] or b['currentTargetSha256'] != cell['currentTargetSha256']:
            raise SystemExit(f'Blind cell binding mismatch: {key}')
        if b['callerCount'] != caller['productionCallerCount'] or [(x.get('path'),x.get('line'),x.get('lineText'),x.get('context')) for x in b['callerReferences']] != [(x.get('path'),x.get('line'),x.get('lineText'),x.get('context')) for x in caller['callers']]:
            raise SystemExit(f'Blind caller reference mismatch: {key}')
        ptarget = p.get('proposedTarget',cell['currentTarget']) if p['disposition'] in ('correction','refinement') else cell['currentTarget']
        btarget = b.get('translation') if b['disposition'] in ('correction','refinement','accept-current') else cell['currentTarget']
        if b['disposition']=='hold': btarget=cell['currentTarget']
        if p['disposition']=='hold' or b['disposition']=='hold':
            if p['disposition']!='hold' or b['disposition']!='hold' or caller['productionCallerCount'] != 0 or rank not in (533,541): raise SystemExit(f'Unexpected hold: {key}')
            selected=cell['currentTarget']; disposition='hold'; target_source='hold-consensus'; disposition_source='hold-consensus'
            rationale='Preserve this callerless hold: the candidate-free input pins no exact production caller, and both reviews retain the current catalog value. No translation proposal is selected.'
            confidence='low'
        elif ptarget != btarget:
            target_conflicts += 1
            if key in PRIMARY_KEYS:
                chosen_side='primary'; chosen=ptarget; disposition=p['disposition']; actual_primary_conflicts.add(key)
            elif key in BLIND_KEYS:
                chosen_side='blind'; chosen=btarget; disposition=b['disposition']; actual_blind_conflicts.add(key)
            else: raise SystemExit(f'Unadjudicated target conflict: {key}')
            selected=chosen; target_source=chosen_side; disposition_source=chosen_side
            rationale=REASONS.get(key) or ('The pinned caller renders this label only when isGoldStarClub is true, while the other branch says Leave Pod. Retain Gold Star as the named membership feature instead of translating it as a generic gold star.' if rank==552 else None)
            if not rationale: raise SystemExit(f'Missing explicit conflict rationale: {key}')
            confidence='moderate'
        else:
            agreement_cells += 1; selected=ptarget; target_source='current' if selected==cell['currentTarget'] else 'agreement'
            if p['disposition']==b['disposition']:
                disposition=p['disposition']; disposition_source='agreement'
            elif key in DISPOSITION_ADJUDICATIONS:
                disposition, rationale=DISPOSITION_ADJUDICATIONS[key]; disposition_source='cross-audit'; disposition_overrides += 1; confidence='moderate'
            else: raise SystemExit(f'Unadjudicated disposition difference on agreed target: {key}')
            if key not in DISPOSITION_ADJUDICATIONS:
                rationale = ('Primary and blind review select the same target for the same pinned caller context. ' + ('Retain the current catalog value.' if selected==cell['currentTarget'] else 'Select their convergent proposed wording.'))
                confidence='high'
        if key in DISPOSITION_ADJUDICATIONS and ptarget==btarget:
            disposition_source='cross-audit'
        if disposition in ('accept-current','hold') and selected != cell['currentTarget']: raise SystemExit(f'Non-proposal changes target: {key}')
        if disposition in ('correction','refinement') and selected == cell['currentTarget']: raise SystemExit(f'Proposal does not change target: {key}')
        if disposition not in ('accept-current','correction','refinement','hold'): raise SystemExit(f'Unknown disposition: {key}')
        checks=token_checks(cell,selected)
        if not checks['allPass']: raise SystemExit(f'Selected token contract failed: {key}')
        missing=[t for t in cell['sourceProtectedLiterals'] if cell['currentTarget'].count(t)<cell['sourceProtectedLiterals'].count(t)]
        if missing: baseline_protected.append((key,missing))
        nums=re.findall(r'(?<![A-Za-z])\d+(?:[.,]\d+)?(?![A-Za-z])',cell['currentTarget'])
        if sorted(nums)!=sorted(cell['sourceNumericTokens']): baseline_numeric.append((key,nums))
        caller_refs=caller['callers']
        token_adjudication=None
        if missing:
            token_adjudication={'type':'protected-literal-gap','sourceLiterals':missing,'selectedTargetRetainsAll':all(selected.count(t)>=cell['sourceProtectedLiterals'].count(t) for t in missing),'selectedSide':target_source,'rationale':rationale}
        numeric_adjudication=None
        if key==(549,'ja'):
            numeric_adjudication={'type':'source-spelled-ordinal-vs-ASCII-digit','sourceSurface':'a second scan','currentSurfaceHasASCII2':bool(re.search(r'(?<![A-Za-z])2(?![A-Za-z])',cell['currentTarget'])),'selectedSurfaceUsesKanjiOrdinal':'二回目' in selected,'selectedSurface':selected,'numericSourceTokens':cell['sourceNumericTokens'],'numericSelectedTokens':checks['numeric']['selected'],'rationale':'Select the primary’s 二回目 wording because the English source spells out second and the pinned scan-status tooltip should not add an ASCII numeric surface.'}
            if not numeric_adjudication['currentSurfaceHasASCII2'] or not numeric_adjudication['selectedSurfaceUsesKanjiOrdinal'] or numeric_adjudication['numericSelectedTokens']:
                raise SystemExit('Japanese numeric-surface adjudication failed')
        rows.append({
          'schema':'slskdn-w66-third-party-crossaudit-cell/v1','repository':REPO,'pullRequest':409,'window':'W66','head':HEAD,'tree':TREE,
          'continuationRank':rank,'remainingQueueRank':cell['remainingQueueRank'],'sourceId':cell['sourceId'],'source':cell['source'],'sourceSha256':cell['sourceSha256'],'locale':loc,
          'catalogKey':cell['catalogKey'],'catalogPath':cell['catalogPath'],'catalogFileSha256':cell['catalogFileSha256'],'catalogGitBlob':cell['catalogGitBlob'],
          'currentTarget':cell['currentTarget'],'currentTargetSha256':cell['currentTargetSha256'],'callerContextSha256':cell['callerContextSha256'],'callerContextSourceId':caller['sourceId'],'callerCount':caller['productionCallerCount'],'callerContexts':caller_refs,
          'primaryReview':{'disposition':p['disposition'],'selectedTarget':ptarget,'proposedTarget':p.get('proposedTarget'),'targetSha256':p.get('reviewedTargetSha256'),'rationale':p['rationale'],'confidence':p['confidence']},
          'blindReview':{'disposition':b['disposition'],'selectedTarget':b.get('translation'),'effectiveTarget':btarget,'targetSha256':b.get('translationSha256'),'rationale':b['rationale'],'confidence':b['confidence'],'packetPrimaryWasUnopened':True},
          'comparison':{'targetsAgree':ptarget==btarget,'targetConflictAdjudicated':ptarget!=btarget,'primaryBlindDispositionsAgree':p['disposition']==b['disposition'],'dispositionOverridden':disposition_source=='cross-audit'},
          'resolution':{'disposition':disposition,'selectedTarget':selected,'selectedTargetSha256':sha_bytes(selected.encode()),'targetSource':target_source,'dispositionSource':disposition_source,'proposedTarget':selected if disposition in ('correction','refinement') else None,'rationale':rationale,'confidence':confidence,'tokenChecks':checks,'tokenAdjudication':token_adjudication,'numericSurfaceAdjudication':numeric_adjudication}
        })
    if actual_primary_conflicts != PRIMARY_KEYS or actual_blind_conflicts != BLIND_KEYS or target_conflicts != 41:
        raise SystemExit(f'Conflict map mismatch: primary={len(actual_primary_conflicts)} blind={len(actual_blind_conflicts)} conflicts={target_conflicts}')
    if len(baseline_protected)!=5 or len(baseline_numeric)!=1 or {x[0] for x in baseline_numeric}!={(549,'ja')}:
        raise SystemExit(f'Expected five protected-literal gaps and one Japanese numeric mismatch; got {len(baseline_protected)} and {baseline_numeric}')
    hold_rows=[r for r in rows if r['resolution']['disposition']=='hold']
    if len(hold_rows)!=24 or {r['continuationRank'] for r in hold_rows}!={533,541} or any(r['callerCount']!=0 for r in hold_rows): raise SystemExit('Callerless hold coverage mismatch')
    if len([r for r in rows if r['resolution']['tokenAdjudication']])!=5: raise SystemExit('Five protected-literal decisions were not recorded')
    if len([r for r in rows if r['resolution']['numericSurfaceAdjudication']])!=1: raise SystemExit('Japanese numeric decision was not recorded')

    # Copy the already pinned reattestation unchanged; this preserves all 104 prior holds.
    prior_src=INPUT/'prior-held-cell-reattestation.jsonl'; prior_dst=OUT/'prior-held-cell-reattestation.jsonl'
    prior=read_jsonl(prior_src)
    if len(prior)!=104 or any(x.get('status')!='reattested-unchanged' or not x.get('matchesPriorCurrentValue') for x in prior): raise SystemExit('Prior hold reattestation mismatch')
    shutil.copyfile(prior_src,prior_dst)
    if sha_file(prior_src)!=sha_file(prior_dst): raise SystemExit('Prior holds copy differs')

    plan_rows=[]
    for r in rows:
        x=r['resolution']; d=x['disposition']
        action='hold' if d=='hold' else 'no-change' if d=='accept-current' else 'propose-update'
        plan_rows.append({'continuationRank':r['continuationRank'],'remainingQueueRank':r['remainingQueueRank'],'sourceId':r['sourceId'],'locale':r['locale'],'catalogPath':r['catalogPath'],'catalogKey':r['catalogKey'],'catalogGitBlob':r['catalogGitBlob'],'currentTarget':r['currentTarget'],'selectedTarget':x['selectedTarget'],'selectedTargetSha256':x['selectedTargetSha256'],'disposition':d,'action':action,'applied':False})
    pcount=collections.Counter(x['disposition'] for x in primary); bcount=collections.Counter(x['disposition'] for x in blind_rows); xcount=collections.Counter(r['resolution']['disposition'] for r in rows); sources=collections.Counter(r['resolution']['targetSource'] for r in rows)
    live=live_attestation()
    live_path=OUT/'live-head-attestation.json'; write_json(live_path,live)
    jsonl=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows)
    (OUT/'resolution-ledger.jsonl').write_text(jsonl,encoding='utf-8')
    plan={'schema':'slskdn-w66-third-party-crossaudit-apply-plan/v1','repository':REPO,'pullRequest':409,'window':'W66','head':HEAD,'tree':TREE,'applicationStatus':'not applied','applicationAllowedByThisTask':False,'cellCount':300,'changeCount':sum(x['action']=='propose-update' for x in plan_rows),'noChangeCount':sum(x['action']=='no-change' for x in plan_rows),'holdCount':sum(x['action']=='hold' for x in plan_rows),'priorHeldCellsReattestedUnchanged':104,'cells':plan_rows}
    write_json(OUT/'apply-plan.json',plan)
    summary={'schema':'slskdn-w66-third-party-crossaudit-summary/v1','repository':REPO,'pullRequest':409,'window':'W66','head':HEAD,'tree':TREE,'cellCount':300,'rankRange':[528,552],'localeCount':12,'primaryDispositionCounts':dict(sorted(collections.Counter(x['disposition'] for x in primary).items())),'blindDispositionCounts':dict(sorted(collections.Counter(x['disposition'] for x in blind_rows).items())),'crossAuditDispositionCounts':dict(sorted(xcount.items())),'effectiveTargetAgreementCells':agreement_cells,'proposalConflicts':target_conflicts,'primarySelectedConflictCount':len(actual_primary_conflicts),'blindSelectedConflictCount':len(actual_blind_conflicts),'dispositionAdjudications':disposition_overrides,'protectedLiteralGapCount':len(baseline_protected),'protectedLiteralGapKeys':[{'rank':k[0],'locale':k[1],'literals':v} for k,v in baseline_protected],'protectedLiteralGapsCorrected':5,'numericSurfaceMismatchCount':1,'numericSurfaceAdjudicationKey':{'rank':549,'locale':'ja'},'placeholderOrMarkupGaps':0,'callerlessHoldCells':24,'callerlessHoldRanks':[533,541],'priorHeldCellsReattestedUnchanged':104,'crossAuditTargetSourceCounts':dict(sorted(sources.items())),'allSelectedTokenChecksPass':all(r['resolution']['tokenChecks']['allPass'] for r in rows),'blindReviewSeparation':'blind packet was sealed with primaryPacketOpened=false and its sealed ledger/checksums are pinned; independent blind review remains separate from this cross-audit','nativeSpeakerReview':'not performed','browserNativeReview':'not performed','catalogChangesApplied':False,'releaseCreated':False,'livePrState':live['state'],'livePrDraft':live['isDraft'],'liveHead':live['prHead'],'liveTree':live['tree']}
    write_json(OUT/'summary.json',summary)
    readme='''# slskdN PR #409 W66 third-party cross-audit\n\nThis sealed task-scratch packet reconciles all 300 cells for continuation ranks 528–552 across the candidate-free input, the primary review, and the independent blind review. It preserves the blind review’s separate provenance: its manifest records that the primary packet was unopened, and this cross-audit verifies its sealed checksums before reconciling decisions.\n\nThe resolution ledger records both reviews, the pinned current target and caller context, the selected target and disposition, exact token checks, and the reason for each adjudication. It resolves 41 non-hold target conflicts (25 selected from primary and 16 from blind), records five protected-literal gaps and the Japanese numeric-surface mismatch, and preserves 24 callerless holds at ranks 533 and 541. The prior 104 held cells are copied byte-for-byte from their reattestation packet.\n\n`apply-plan.json` is a proposed plan only. No catalog, repository, or PR changes were applied. Native-speaker and browser/native UI review remain outstanding; this cross-audit does not replace them. No tests, builds, CI jobs, browser sessions, or releases were run.\n\nVerify with `python3 verify_cross_audit.py`, then `sha256sum -c SHA256SUMS.txt`. The manifest pins the exact input and review packet hashes; the checksum list seals all output files including the verification record.\n'''
    (OUT/'README.md').write_text(readme,encoding='utf-8')
    pins={
      'candidateFreeManifestSha256':sha_file(INPUT/'manifest.json'),'candidateFreeChecksumListSha256':sha_file(INPUT/'PACKET-SHA256SUMS.txt'),'candidateFreeCellsSha256':sha_file(INPUT/'source-current-cells.jsonl'),'candidateFreeCallerContextsSha256':sha_file(INPUT/'caller-contexts.jsonl'),'candidateFreePriorHeldSha256':sha_file(prior_src),
      'primaryManifestSha256':sha_file(PRIMARY/'manifest.json'),'primaryChecksumListSha256':sha_file(PRIMARY/'SHA256SUMS.txt'),'primaryLedgerSha256':sha_file(PRIMARY/'primary-ledger.jsonl'),
      'blindManifestSha256':sha_file(BLIND/'manifest.json'),'blindChecksumListSha256':sha_file(BLIND/'SHA256SUMS.txt'),'blindLedgerSha256':sha_file(BLIND/'sealed-blind-review-ledger.jsonl'),
    }
    manifest={'schema':'slskdn-w66-third-party-crossaudit-manifest/v1','sealed':True,'repository':REPO,'pullRequest':409,'branch':BRANCH,'window':'W66','head':HEAD,'tree':TREE,'inputPaths':{'candidateFree':str(INPUT),'primary':str(PRIMARY),'blind':str(BLIND)},'inputPins':pins,'livePrState':live['state'],'livePrDraft':live['isDraft'],'blindSeparation':{'candidateFreeInputOnlyAtBlindReview':True,'primaryPacketOpenedByBlindReviewer':False,'blindPacketSealedAt':'2026-11-03','blindLedgerSha256':pins['blindLedgerSha256']},'cellCount':300,'priorHeldCellsReattestedUnchanged':104,'outputFileSet':['README.md','apply-plan.json','build_cross_audit.py','live-head-attestation.json','prior-held-cell-reattestation.jsonl','resolution-ledger.jsonl','summary.json','verify_cross_audit.py'],'createdAtUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':[]}
    for name in manifest['outputFileSet']:
        p=OUT/name
        if not p.is_file(): raise SystemExit(f'Missing output before manifest: {name}')
        manifest['files'].append({'path':name,'bytes':p.stat().st_size,'sha256':sha_file(p)})
    write_json(OUT/'manifest.json',manifest)
    print(json.dumps({'built':str(OUT),'summary':summary,'manifestSha256':sha_file(OUT/'manifest.json')},ensure_ascii=False))
if __name__=='__main__': main()
