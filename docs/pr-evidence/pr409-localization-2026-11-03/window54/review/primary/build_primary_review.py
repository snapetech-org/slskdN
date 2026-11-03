#!/usr/bin/env python3
"""Build slskdN PR #409 W54 primary review from the sealed candidate-free input."""
from pathlib import Path
import collections, hashlib, json, re, subprocess

REPO = Path('/mnt/disks/scratch/task-worktrees/localization-20261103/slskdn-pr409-w52-primary-20261103')
OUT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w54-primary-20261103')
INPUT = OUT / 'input'
PRIMARY = OUT / 'primary'
HEAD = '5812e90c3018f0a8b563bff2ba95b5fd19076908'
TREE = '632924177388e15b594976774d2d879a098e8a72'
BODY = '9234d213b20ffdbb469fcf0067a34df7ccd23d155cd1349cebb2481499738ae4'
BRANCH = 'codex/slskdn-oidc-tooltip-localization-20261030'
PR = 409
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PLACEHOLDER_RE = re.compile(r'\{[^{}]+\}')
MARKUP_RE = re.compile(r'</?[A-Za-z][^>]*>')
NUMBER_RE = re.compile(r'(?<![A-Za-z])\d+(?:[.,]\d+)?%?(?![A-Za-z])')

def run(*args, cwd=REPO, text=True):
    return subprocess.check_output(list(args), cwd=cwd, text=text)
def sha(data):
    return hashlib.sha256(data.encode('utf-8') if isinstance(data,str) else data).hexdigest()
def git_blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
def canonical(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def readjl(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def readjson(path):
    return json.loads(path.read_text(encoding='utf-8'))
def verify_manifest(directory,name):
    checks=[]
    for line in (directory/name).read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        expected,rel=line.split(None,1); rel=rel.strip().lstrip('*')
        actual=sha((directory/rel).read_bytes())
        checks.append({'path':rel,'expected':expected,'actual':actual,'matches':expected==actual})
    assert checks and all(x['matches'] for x in checks),(directory,name,checks)
    return checks
def writejson(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def writejl(path,rows):
    path.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
def write_manifest(directory,name):
    manifest=directory/name
    rows=[]
    for p in sorted(x for x in directory.rglob('*') if x.is_file() and x!=manifest):
        rows.append(f'{sha(p.read_bytes())}  {p.relative_to(directory).as_posix()}')
    manifest.write_text('\n'.join(rows)+'\n',encoding='utf-8')

def live_pin():
    head=run('git','rev-parse','HEAD').strip()
    tree=run('git','rev-parse','HEAD^{tree}').strip()
    assert head==HEAD and tree==TREE and not run('git','status','--porcelain=v1').strip(),(head,tree,run('git','status','--short'))
    pr=json.loads(run('gh','pr','view',str(PR),'--repo','snapetech-org/slskdN','--json','body,headRefOid,headRefName,isDraft,state,url'))
    body_hash=sha(pr['body'])
    assert pr['state']=='OPEN' and pr['isDraft'] is True and pr['headRefOid']==HEAD and pr['headRefName']==BRANCH and body_hash==BODY,(pr['state'],pr['isDraft'],pr['headRefOid'],pr['headRefName'],body_hash)
    remote=run('git','ls-remote','origin',f'refs/heads/{BRANCH}').strip().split()
    assert len(remote)==2 and remote[0]==HEAD,remote
    return {'head':head,'tree':tree,'branch':BRANCH,'remoteBranchHead':remote[0],'state':'open','draft':True,'bodySha256':body_hash}

assert PRIMARY.is_dir()
assert {p.name for p in PRIMARY.iterdir()} <= {'build_primary_review.py','candidate-decisions.json','review-decisions.jsonl','review-summary.json','review-worksheet.md','README.md','SHA256SUMS.txt'},[p.name for p in PRIMARY.iterdir()]
input_checks=verify_manifest(INPUT,'PACKET-SHA256SUMS.txt')
input_manifest_sha=sha((INPUT/'PACKET-SHA256SUMS.txt').read_bytes())
pin=live_pin()
attest=readjson(INPUT/'head-tree-attestation.json')
selection=readjson(INPUT/'selection-and-boundary.json')
assert attest['head']==HEAD and attest['tree']==TREE and attest['bodySha256']==BODY
assert selection['pins']['head']==HEAD and selection['pins']['tree']==TREE and selection['pins']['bodySha256']==BODY
source_rows=readjl(INPUT/'source-current-cells.jsonl')
caller_rows=readjl(INPUT/'caller-contexts.jsonl')
protected_rows=readjl(INPUT/'protected-literals.jsonl')
catalog_rows=readjl(INPUT/'catalog-structure.jsonl')
assert len(source_rows)==300 and len(caller_rows)==25 and len(protected_rows)==25 and len(catalog_rows)==12
assert [(r['continuationRank'],r['locale']) for r in source_rows]==[(rank,loc) for rank in range(251,276) for loc in LOCALES]
assert len({(r['sourceId'],r['locale']) for r in source_rows})==300
assert len({r['sourceId'] for r in caller_rows})==25
assert all('candidateTarget' not in r and 'verdict' not in r and 'disposition' not in r for r in source_rows)

# Reattest catalog bytes and ordered keys against the exact tree.
ordered_keys=None
for row in catalog_rows:
    path=REPO/row['catalogPath']; data=path.read_bytes(); keys=list(json.loads(data))
    if ordered_keys is None: ordered_keys=keys
    assert keys==ordered_keys,(row['locale'],'ordered catalog keys changed')
    assert sha(data)==row['sha256'] and git_blob(data)==row['gitBlob'],(row['locale'],'catalog hash/blob mismatch')
    assert run('git','rev-parse',f'{HEAD}:{row["catalogPath"]}').strip()==row['gitBlob']
assert len(ordered_keys)==6176 and sha('\n'.join(ordered_keys)+'\n')==selection['orderedCatalogKeySha256']

# Reattest all bounded caller source lines and file hashes from the pinned tree.
caller_by_id={r['sourceId']:r for r in caller_rows}
caller_file_cache={}
for c in caller_rows:
    for ref in c['callers']:
        rel=ref['path']
        if rel not in caller_file_cache:
            data=(REPO/rel).read_bytes()
            assert sha(data)==ref['fileSha256'] and git_blob(data)==ref['gitBlob']
            assert run('git','rev-parse',f'{HEAD}:{rel}').strip()==ref['gitBlob']
            assert run('git','show',f'{HEAD}:{rel}',text=False)==data
            caller_file_cache[rel]=data.decode('utf-8').splitlines()
        line=caller_file_cache[rel][ref['line']-1]
        assert line==ref['lineText'] and sha(line)==ref['lineSha256']

raw=readjson(PRIMARY/'candidate-decisions.json')
CANDIDATES={}
for key,value in raw.items():
    rank_text,loc=key.split('|',1)
    cell=(int(rank_text),loc)
    assert cell not in CANDIDATES and cell[0] in range(251,276) and loc in LOCALES
    assert set(value)=={'target','disposition','rationale','confidence'}
    assert value['disposition'] in {'correction','refinement'} and value['target'] and value['rationale']
    CANDIDATES[cell]=value
assert len(CANDIDATES)==51
HOLD_RANKS={270}
TERMINOLOGY_HOLD_RANKS={262}
ACCEPT_RATIONALE={
251:'The caller identifies Brown as a color option; the current target is the localized color name.',
252:'The caller uses New as a message-seen registration status opposite Already known; the current target expresses new status in context.',
253:'The caller formats imported and skipped row counts from a history import; both placeholders and both skip reasons are present.',
254:'The caller is the advanced retrieval-cache controls disclosure heading; the current target preserves the heading meaning.',
255:'The caller labels a Soulseek peer ID beside affinity and trust scores; the current target identifies the peer.',
256:'The caller is a button for loading descriptor retrieval and cache performance metrics; the current target expresses the action and metric.',
257:'The caller uses this as a service-kind option alongside Database, SSH, and Custom; the current target names the web interface.',
258:'The caller toggles between all imported native MilkDrop presets and favorites; the current target identifies presets in the native library.',
259:'The caller labels a visualization with a subheader describing chunk-completion status; the current target preserves that subject.',
260:'The caller displays the count of node.outgoingLinks; the current target identifies links directed outward.',
261:'The caller is a tooltip for pinning the graph center to compare nodes or reopen the branch later; the current target preserves the action and purpose.',
263:'The caller displays a known-family score as a hint and explicitly says it is not a download-control signal; the current target preserves the distinction and score placeholder.',
264:'The caller emits this toast before refusing to save a filter with an error; the current target explains the required fix.',
265:'The source is the shared Cancel action used across modal, form, and confirmation controls; the current target communicates cancellation.',
266:'The caller labels the ReplayGain policy selector for a playlist; the current target preserves the standard name and {name} placeholder.',
267:'The caller is the live view under System/Logs, paired with retained daily application logs; the current target describes incoming software-application records.',
268:'The caller labels the count of known source providers; the current target conveys known status.',
269:'The caller groups these counters under Mesh Sync Security; the current target names signatures, reputation, rate limits, and quarantine.',
271:'The caller describes a Wishlist action that immediately searches Soulseek and contacts peers rather than waiting for the scheduled run; the current target preserves the timing and result meaning.',
272:'The caller is the HTTPS certificate password field in admin policies; the current target names the credential.',
273:'The caller is an aria-label on a file-list close button; the current target preserves the dynamic {directory} placeholder and close action.',
274:'The callers use this as a setup-health status when optional providers have missing credentials; the current target conveys the optional provider gaps.',
275:'The caller presents a dry-run action summary and says no file write has started; the current target expresses the conditional sidecar write after explicit approval.',
}
assert set(ACCEPT_RATIONALE)==(set(range(251,276))-{270,262})
rows=[]; counts=collections.Counter(); changed_by_locale=collections.Counter(); changed_by_rank=collections.Counter(); changed_by_source=collections.Counter()
placeholder_mismatches=[]; markup_mismatches=[]; numeric_mismatches=[]; candidate_protected_mismatches=[]; current_protected_mismatches=[]
protected_by_id={r['sourceId']:r for r in protected_rows}
for item in source_rows:
    rank=item['continuationRank']; source=item['source']; sid='src_'+sha(source)[:16]; source_id=item['sourceId']; loc=item['locale']; current=item['currentTarget']
    assert sid==source_id and sha(source)==item['sourceSha256']
    assert sha(current)==item['currentTargetSha256']
    cat=json.loads((REPO/item['catalogPath']).read_bytes())
    assert cat[source]==current
    assert git_blob((REPO/item['catalogPath']).read_bytes())==item['catalogGitBlob']
    if rank in TERMINOLOGY_HOLD_RANKS:
        candidate=current; verdict='hold-terminology'; confidence='low'
        rationale='The pinned caller confirms this is a Pod object published to the DHT, but the available project memory does not define the domain noun or an approved target-language term. Existing translations vary among container-like, group, and module readings; retain all locale values pending a product glossary decision.'
    elif rank in HOLD_RANKS:
        candidate=current; verdict='hold-context'; confidence='low'
        rationale='No exact production caller was found in the bounded quoted-literal scan. The fragment “waves ·” lacks enough context to identify whether it is a chart series, unit, or concatenated label; retain all locale values pending source-context resolution.'
    elif (rank,loc) in CANDIDATES:
        decision=CANDIDATES[(rank,loc)]
        candidate=decision['target']; verdict=decision['disposition']; confidence=decision['confidence']; rationale=decision['rationale']
    else:
        candidate=current; verdict='accept-current'; confidence='moderate'; rationale=ACCEPT_RATIONALE[rank]
    source_ph=collections.Counter(PLACEHOLDER_RE.findall(source)); current_ph=collections.Counter(PLACEHOLDER_RE.findall(current)); candidate_ph=collections.Counter(PLACEHOLDER_RE.findall(candidate))
    source_markup=collections.Counter(MARKUP_RE.findall(source)); current_markup=collections.Counter(MARKUP_RE.findall(current)); candidate_markup=collections.Counter(MARKUP_RE.findall(candidate))
    source_nums=collections.Counter(NUMBER_RE.findall(source)); candidate_nums=collections.Counter(NUMBER_RE.findall(candidate))
    ph_ok=source_ph==current_ph==candidate_ph
    markup_ok=source_markup==current_markup==candidate_markup
    numeric_ok=source_nums==candidate_nums
    if not ph_ok: placeholder_mismatches.append((rank,loc))
    if not markup_ok: markup_mismatches.append((rank,loc))
    if not numeric_ok: numeric_mismatches.append((rank,loc))
    checks=[]
    for lit in item.get('protectedLiteralChecks',[]):
        check={'literal':lit['literal'],'kind':lit['kind'],'policy':lit['policy'],'sourcePreserved':lit['literal'] in source,'currentPreserved':lit['literal'] in current,'candidatePreserved':lit['literal'] in candidate}
        checks.append(check)
        if not check['currentPreserved']: current_protected_mismatches.append({'rank':rank,'sourceId':source_id,'locale':loc,'literal':lit['literal']})
        if not check['candidatePreserved']: candidate_protected_mismatches.append({'rank':rank,'sourceId':source_id,'locale':loc,'literal':lit['literal']})
    assert item['callerRefs']==[{'path':r['path'],'line':r['line'],'lineSha256':r['lineSha256'],'fileSha256':r['fileSha256'],'gitBlob':r['gitBlob']} for r in caller_by_id[source_id]['callers']]
    out={'continuationRank':rank,'historicalSourceOrdinal':None,'sourceId':source_id,'source':source,'sourceSha256':item['sourceSha256'],'locale':loc,'catalogPath':item['catalogPath'],'catalogFileSha256':item['catalogFileSha256'],'catalogGitBlob':item['catalogGitBlob'],'currentTarget':current,'currentTargetSha256':item['currentTargetSha256'],'candidateTarget':candidate,'candidateTargetSha256':sha(candidate),'verdict':verdict,'rationale':rationale,'confidence':confidence,'callerCount':caller_by_id[source_id]['productionCallerCount'],'callerContextSha256':item['callerContextSha256'],'callerRefs':item['callerRefs'],'placeholderCheck':{'source':dict(source_ph),'current':dict(current_ph),'candidate':dict(candidate_ph),'sourceMatchesCurrent':source_ph==current_ph,'sourceMatchesCandidate':source_ph==candidate_ph},'markupCheck':{'source':dict(source_markup),'current':dict(current_markup),'candidate':dict(candidate_markup),'sourceMatchesCurrent':source_markup==current_markup,'sourceMatchesCandidate':source_markup==candidate_markup},'numericCheck':{'source':dict(source_nums),'candidate':dict(candidate_nums),'sourceMatchesCandidate':numeric_ok},'protectedLiteralChecks':checks}
    rows.append(out); counts[verdict]+=1
    if candidate!=current:
        changed_by_locale[loc]+=1; changed_by_rank[rank]+=1; changed_by_source[source_id]+=1
assert len(rows)==300 and not placeholder_mismatches and not markup_mismatches and not numeric_mismatches
assert not candidate_protected_mismatches
assert counts['hold-context']==12 and counts['hold-terminology']==12 and counts['correction']+counts['refinement']==len(CANDIDATES)
assert sum(changed_by_locale.values())==len(CANDIDATES)
assert all(r['candidateTargetSha256']==sha(r['candidateTarget']) for r in rows)
assert all((r['continuationRank']==270 and r['verdict']=='hold-context') or (r['continuationRank']==262 and r['verdict']=='hold-terminology') or r['verdict'] not in {'hold-context','hold-terminology'} for r in rows)

writejl(PRIMARY/'review-decisions.jsonl',rows)
summary={'repository':'snapetech-org/slskdN','pullRequest':PR,'pullRequestUrl':attest['url'],'exactHead':HEAD,'exactTree':TREE,'pinnedPrBodySha256':BODY,'window':'W54 continuation ranks 251-275 from the W49 stable-ID inventory; historical source ordinals unavailable and not claimed','sourceCount':25,'localeCount':12,'cellCount':300,'dispositionCounts':dict(counts),'candidateChangeCount':sum(changed_by_locale.values()),'changedCellsByLocale':dict(changed_by_locale),'changedCellsByRank':dict(sorted(changed_by_rank.items())),'changedCellsBySource':dict(changed_by_source),'holdCount':counts['hold-context']+counts['hold-terminology'],'contextHoldCount':counts['hold-context'],'terminologyHoldCount':counts['hold-terminology'],'heldSourceIds':sorted({r['sourceId'] for r in rows if r['verdict'] in {'hold-context','hold-terminology'}}),'contextHeldSourceIds':sorted({r['sourceId'] for r in rows if r['verdict']=='hold-context'}),'terminologyHeldSourceIds':sorted({r['sourceId'] for r in rows if r['verdict']=='hold-terminology'}),'callerReferenceCount':sum(x['productionCallerCount'] for x in caller_rows),'callerlessSourceIds':[x['sourceId'] for x in caller_rows if x['productionCallerCount']==0],'currentProtectedLiteralMismatchCount':len(current_protected_mismatches),'candidateProtectedLiteralMismatchCount':len(candidate_protected_mismatches),'placeholderMismatchCount':len(placeholder_mismatches),'markupMismatchCount':len(markup_mismatches),'numericMismatchCount':len(numeric_mismatches),'candidateChangedSourceIds':len(changed_by_source),'nativeSpeakerApproval':False,'headedBrowserReview':False,'projectTestsBuildScansCiRun':False,'repositoryModified':False,'remoteMutation':False,'reviewType':'machine-assisted primary review; moderate confidence except the caller-context and terminology holds','inputManifestSha256':input_manifest_sha,'inputManifestEntriesVerified':len(input_checks),'sourceSequence':{'first':selection['firstSelected'],'last':selection['lastSelected'],'nextBoundary':selection['nextBoundary'],'disjointFromW50W51W52W53':selection['disjointness']['w54DisjointFromW50W51W52W53'],'w49UnreviewedGapPreserved':selection['disjointness']['w54DisjointFromW49Gap']},'changes':[{'rank':r['continuationRank'],'sourceId':r['sourceId'],'source':r['source'],'locale':r['locale'],'from':r['currentTarget'],'to':r['candidateTarget'],'disposition':r['verdict'],'rationale':r['rationale']} for r in rows if r['candidateTarget']!=r['currentTarget']]}
writejson(PRIMARY/'review-summary.json',summary)
worksheet=['# W54 primary review worksheet','',f'Exact PR head/tree: `{HEAD}` / `{TREE}`.','Input packet SHA-256: `'+input_manifest_sha+'`.','25 stable-ID source rows × 12 locales = 300 cells. Historical extraction ordinals are unavailable and are not claimed.']
for rank in range(251,276):
    group=[r for r in rows if r['continuationRank']==rank]; first=group[0]
    worksheet += ['',f"## Rank {rank} — `{first['sourceId']}`",'',f"**Source:** {first['source']}",'',f"**Caller references:** {first['callerCount']}"]
    for ref in first['callerRefs']:
        worksheet.append(f"- `{ref['path']}:{ref['line']}` (line SHA `{ref['lineSha256'][:12]}`)")
    if not first['callerRefs']: worksheet.append('- None found in bounded production literal scan; all locale cells are held for context.')
    worksheet += ['', '| Locale | Current | Primary proposal | Disposition |', '|---|---|---|---|']
    for row in group:
        worksheet.append(f"| {row['locale']} | {row['currentTarget']} | {row['candidateTarget']} | {row['verdict']} |")
        if row['verdict']!='accept-current': worksheet.append(f"|  | **Rationale** | {row['rationale']} | confidence: {row['confidence']} |")
(PRIMARY/'review-worksheet.md').write_text('\n'.join(worksheet)+'\n',encoding='utf-8')
readme=f'''# slskdN PR #409 W54 primary review

This machine-assisted primary review is pinned to PR head/tree `{HEAD}` / `{TREE}` and covers 25 stable source IDs at W49 continuation ranks 251–275 across all 12 locales (300 cells). Historical extraction ordinals are unavailable and are not claimed.

Primary dispositions: {counts['accept-current']} accept-current, {counts['correction']} corrections, {counts['refinement']} refinements, 12 context holds, and 12 terminology holds. The context holds are the 12 locale values for `waves ·`; the bounded source scan found no production caller. The terminology holds are the 12 `Publish Pod` values: the caller confirms a DHT Pod object, but no approved localized noun is recorded. The primary review proposes {sum(changed_by_locale.values())} exact target changes.

Every proposal is rechecked against its exact source/current hashes and pinned caller context. Placeholder, markup, numeric, and protected-literal mismatches are zero. The separate Hindsight record says `feature.Pods` and the content identifier `pods` remain exact code tokens in another help sentence; that rule does not define this `Publish Pod` UI noun, so this window keeps that noun held. Machine review is not qualified native-speaker approval or headed-browser acceptance.

The input packet is separate and checksummed. No repository or PR changes, project tests/builds, scans, CI, browser actions, workflow edits, releases, merges, or tags were performed.
'''
(PRIMARY/'README.md').write_text(readme,encoding='utf-8')
write_manifest(PRIMARY,'SHA256SUMS.txt')
primary_checks=verify_manifest(PRIMARY,'SHA256SUMS.txt')
assert verify_manifest(INPUT,'PACKET-SHA256SUMS.txt')==input_checks
assert live_pin()==pin
print(json.dumps({'verification':'primary-sealed','head':HEAD,'tree':TREE,'inputManifestSha256':input_manifest_sha,'inputManifestEntriesVerified':len(input_checks),'primaryManifestSha256':sha((PRIMARY/'SHA256SUMS.txt').read_bytes()),'primaryManifestEntriesVerified':len(primary_checks),'sources':25,'cells':300,'dispositions':dict(counts),'candidateChanges':sum(changed_by_locale.values()),'changedCellsByLocale':dict(changed_by_locale),'holds':counts['hold-context']+counts['hold-terminology'],'contextHolds':counts['hold-context'],'terminologyHolds':counts['hold-terminology'],'heldSourceIds':summary['heldSourceIds'],'callerReferences':sum(x['productionCallerCount'] for x in caller_rows),'callerlessSourceIds':summary['callerlessSourceIds'],'placeholderMismatches':len(placeholder_mismatches),'markupMismatches':len(markup_mismatches),'numericMismatches':len(numeric_mismatches),'candidateProtectedLiteralMismatches':len(candidate_protected_mismatches)},ensure_ascii=False,indent=2))
