from __future__ import annotations
import collections
import datetime as dt
import hashlib
import json
import socket
import subprocess
from pathlib import Path

PRIMARY = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window46-reconstructed-ranks26-50-primary-20261102')
OUT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window46-reconstructed-ranks26-50-crossreview-20261102')
WORKTREE = Path('/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn')
EXPECTED_PRIMARY_MANIFEST = '52c0d2f6e314eb047c9fd23aadbf4f32e496999988d33c8ff41ae3603f321215'
EXPECTED_PRIMARY_SUMS = '2040e66635e5c5d239533ba40b41a858ee73dccc2e2377be0d2fed40ba8f0362'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PRS = [
 ('snapetech-org/SeerrNG',418),('snapetech-org/ChaptarrNG',190),('snapetech-org/QuestarrNG',155),
 ('snapetech-org/ROMarrNG',70),('snapetech-org/slskR',204),('snapetech-org/slskdN',409),('snapetech-org/TorrentNG',243)
]
OVERRIDES = {
 (29,'es'): ('Ignorar carpetas solo está disponible en búsquedas de Wishlist, porque cada regla pertenece a un elemento. Abra un resultado del historial de Wishlist para usar esta función.', 'The source directly instructs the reader to open a result. The current “Abre” is informal, while the established Spanish lane uses formal usted imperatives (for example, W45 corrected “Expandir” to “Expanda”). “Abra” restores the formal register; “esta función” makes the reference clear.'),
 (30,'ar'): ('فرض تعزيز أمن الويب', 'In this security-policy checkbox, “تصلب” is a literal and awkward rendering of security hardening. “تعزيز أمن الويب” expresses strengthening web security idiomatically while “فرض” preserves enforce.'),
 (32,'ar'): ('ContentID للبحث عن التطابقات', 'The current Arabic placeholder ends with the dangling preposition “لـ”. This rephrases it as “ContentID to search for matches” and preserves the exact protected ContentID literal.'),
 (34,'ar'): ('استراتيجية حل التعارضات', 'The pinned caller selects a software conflict-resolution policy. “الصراعات” reads as general disputes; “التعارضات” is the more precise computing sense.'),
 (45,'de'): ('DHT-Schlüssel:', 'German compounds an acronym with the following noun using a hyphen. “DHT Schlüssel” should be “DHT-Schlüssel”; the protected DHT token remains exact.'),
 (47,'ar'): ('عدد الأيام حتى انتهاء صلاحية العناصر غير المُقيّمة', 'The primary proposal says “unclassified” (غير المصنفة), while the source and caller mean items without a user rating. “غير المُقيّمة” matches the rating sense.'),
}
HOLD_REASON = {
 37: 'This full question contains a dynamic {count}, but no exact production localization caller was found. A fixed noun form can be ungrammatical for singular and locale-specific count categories (notably Arabic); no caller or plural-aware source/ICU message establishes the reachable count range or grammatical branches. Hold all locales until the caller and count-aware phrasing are pinned.',
 42: 'The exact caller concatenates a dynamic matched-track count before this fragment. The source provides no plural-aware phrase/ICU count value, so locale-specific grammar cannot be represented here. Hold all locale cells pending a count-aware caller message.',
 49: 'The same source word is used as a standalone “new messages” separator and as a suffix after a dynamic unseen-result count. The contexts require distinct grammatical forms and count-sensitive forms in some locales. Hold all locale cells pending separate/count-aware caller messages.'
}

def sha(data: bytes | str) -> str:
    if isinstance(data, str): data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()
def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)+'\n')
def write_jsonl(path: Path, rows):
    path.write_text(''.join(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n' for row in rows))
def run(args, cwd=None):
    return subprocess.run(args, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

OUT.mkdir(parents=True, exist_ok=True)
# Verify the primary's manifest and every listed file before trusting its input.
primary_manifest_bytes=(PRIMARY/'manifest.json').read_bytes()
primary_sums_bytes=(PRIMARY/'SHA256SUMS.txt').read_bytes()
assert sha(primary_manifest_bytes)==EXPECTED_PRIMARY_MANIFEST
assert sha(primary_sums_bytes)==EXPECTED_PRIMARY_SUMS
primary_manifest=json.loads(primary_manifest_bytes)
assert primary_manifest['head']=='31544a6ef15db2f8481dd76aa9c10844ec3164ba'
assert primary_manifest['tree']=='fe94582c3e13f0f567fbfa6c3abac6e8558ba17d'
checks=[]
for line in primary_sums_bytes.decode().splitlines():
    digest,name=line.split('  ',1)
    actual=sha((PRIMARY/name).read_bytes())
    assert digest==actual,(name,digest,actual)
    checks.append({'path':name,'sha256':actual,'verified':True})
for entry in primary_manifest['files']:
    assert sha((PRIMARY/entry['path']).read_bytes())==entry['sha256']
assert len(checks)==len(primary_manifest['files'])

# Re-query live PR state/head and GitHub commit trees for all seven repositories.
live=[]
for repo,number in PRS:
    pr=json.loads(run(['gh','pr','view',str(number),'-R',repo,'--json','number,state,isDraft,headRefOid,headRefName,baseRefName,url']).decode())
    oid=pr['headRefOid']
    commit=json.loads(run(['gh','api',f'repos/{repo}/git/commits/{oid}']).decode())
    row={'repository':repo,'number':number,**pr,'headTree':commit['tree']['sha']}
    live.append(row)
    expected=next(x for x in json.loads((PRIMARY/'input-integrity.json').read_text())['liveSevenPrSnapshot'] if x['number']==number)
    assert row['headRefOid']==expected['headRefOid'],(repo,number,row['headRefOid'],expected['headRefOid'])
    assert row['headTree']==expected['headTree'],(repo,number,row['headTree'],expected['headTree'])
    assert row['state']==expected['state'] and row['isDraft']==expected['isDraft']
slsk=next(x for x in live if x['number']==409)
assert slsk['headRefOid']==primary_manifest['head'] and slsk['headTree']==primary_manifest['tree']
write_json(OUT/'live-pr-snapshot.json',{'queriedAtUtc':dt.datetime.now(dt.timezone.utc).isoformat(),'pullRequests':live})
write_json(OUT/'primary-packet-verification.json',{
 'primaryPacket':str(PRIMARY),'manifestSha256':EXPECTED_PRIMARY_MANIFEST,'sha256SumsSha256':EXPECTED_PRIMARY_SUMS,
 'manifestAndChecksumsVerified':True,'verifiedFiles':checks,'fileCount':len(checks),
 'pr409ExactHead':slsk['headRefOid'],'pr409ExactTree':slsk['headTree'],'allSevenLivePrHeadsMatchPrimarySnapshot':True})

# Independently reattest the local source and its exact pinned catalogs/callers.
head=run(['git','rev-parse','HEAD'],cwd=WORKTREE).decode().strip()
tree=run(['git','rev-parse','HEAD^{tree}'],cwd=WORKTREE).decode().strip()
status=run(['git','status','--porcelain'],cwd=WORKTREE).decode()
assert head==slsk['headRefOid'] and tree==slsk['headTree'] and not status
catalog_structure=json.loads((PRIMARY/'catalog-structure.json').read_text())
assert catalog_structure['exactHead']==head and catalog_structure['exactTree']==tree
catalog_checks=[]
catalog_maps={}
for c in catalog_structure['catalogs']:
    blob=run(['git','rev-parse',f'{head}:{c["path"]}'],cwd=WORKTREE).decode().strip()
    raw=run(['git','show',f'{head}:{c["path"]}'],cwd=WORKTREE)
    assert blob==c['blobOid'] and sha(raw)==c['fileSha256']
    data=json.loads(raw)
    assert len(data)==c['entryCount']==6170
    catalog_checks.append({'path':c['path'],'blobOid':blob,'fileSha256':sha(raw),'entryCount':len(data),'verified':True})
    catalog_maps[c['path']]=data
caller_rows=[json.loads(x) for x in (PRIMARY/'caller-context.jsonl').read_text().splitlines()]
caller_checks=[]
for row in caller_rows:
  for ref in row['callerRefs']:
    path=ref['path']
    blob=run(['git','rev-parse',f'{head}:{path}'],cwd=WORKTREE).decode().strip()
    raw=run(['git','show',f'{head}:{path}'],cwd=WORKTREE)
    lines=raw.decode('utf-8').splitlines()
    line=lines[ref['line']-1]
    assert blob==ref['blobOid'],(path,blob,ref['blobOid'])
    assert sha(raw)==ref['fileSha256'],path
    assert line==ref['lineText'],(path,ref['line'],line,ref['lineText'])
    assert sha(line)==ref['lineSha256'],(path,ref['line'])
    caller_checks.append({'sourceId':ref['sourceId'],'path':path,'line':ref['line'],'blobOid':blob,'fileSha256':sha(raw),'lineSha256':sha(line),'referenceRole':ref['referenceRole'],'verified':True})
write_json(OUT/'independent-pin-verification.json',{
 'repository':'snapetech-org/slskdN','head':head,'tree':tree,'worktree':str(WORKTREE),'worktreeClean':True,
 'catalogsVerified':catalog_checks,'catalogCount':len(catalog_checks),'callerReferencesVerified':caller_checks,
 'callerReferenceCount':len(caller_checks),'callerRowsWithProductionDisplay':sum(x['callerUseStatus']=='production-localization-reference-found' for x in caller_rows),
 'verifiedAtUtc':dt.datetime.now(dt.timezone.utc).isoformat()})

primary_rows=[json.loads(x) for x in (PRIMARY/'review-decisions.jsonl').read_text().splitlines()]
assert len(primary_rows)==300
assert all(x['exactHead']==head and x['exactTree']==tree for x in primary_rows)
assert all(x['locale'] in LOCALES for x in primary_rows)
primary_cells={(x['selectionRank'],x['locale']):x for x in primary_rows}
assert len(primary_cells)==300
# Recheck source identities, target hashes and exact catalog values against the pinned blobs.
for key,x in primary_cells.items():
    assert x['sourceId']=='src_'+x['sourceSha256'][:16],key
    assert sha(x['sourceText'])==x['sourceSha256'],key
    assert sha(x['currentTarget'])==x['currentTargetSha256'],key
    assert catalog_maps[x['catalogPath']][x['sourceText']]==x['currentTarget'],key
    assert x['catalogBlobOid']==next(c['blobOid'] for c in catalog_structure['catalogs'] if c['path']==x['catalogPath'])
    assert x['catalogFileSha256']==next(c['fileSha256'] for c in catalog_structure['catalogs'] if c['path']==x['catalogPath'])

cross=[]
for rank in range(26,51):
  for locale in LOCALES:
    p=primary_cells[(rank,locale)]
    if rank in HOLD_REASON:
      disp='hold'; target=None
      rationale=HOLD_REASON[rank]
      origin='independent-crossreview'
    elif (rank,locale) in OVERRIDES:
      target,rationale=OVERRIDES[(rank,locale)]
      disp='revise-proposal'
      origin='independent-crossreview'
    elif p['disposition']=='propose-correction':
      target=p['proposedTarget']; disp='accept-proposal'
      rationale='Independently accept the primary correction: it resolves the recorded meaning/context issue and preserves source tokens.'
      origin='primary-proposal-independently-accepted'
    else:
      target=p['currentTarget']; disp='accept-current'
      rationale='Independently read this locale cell against the English source and pinned caller context (when one exists). It preserves the source meaning and product term; no material wording correction was found. Structural tokens and protected literals remain intact.'
      origin='independent-current-retention'
    target_sha=sha(target) if target is not None else None
    if target is not None:
      # Every non-held target retains exact source placeholders, markup tags and protected literals.
      import re
      token_re=re.compile(r'\{([A-Za-z][A-Za-z0-9_]*)\}')
      tag_re=re.compile(r'</?[A-Za-z][^>]*>')
      protected=p['protectedLiterals']
      assert sorted(token_re.findall(target))==sorted(token_re.findall(p['sourceText'])),(rank,locale,'placeholder')
      assert tag_re.findall(target)==tag_re.findall(p['sourceText']),(rank,locale,'markup')
      assert not [v for v in protected if v not in target],(rank,locale,'protected literal')
    cross.append({
      'exactHead':head,'exactTree':tree,'selectionRank':rank,'selectionRankBasis':p['selectionRankBasis'],'sourceOrdinal':None,
      'sourceId':p['sourceId'],'sourceText':p['sourceText'],'sourceSha256':p['sourceSha256'],'locale':locale,
      'catalogPath':p['catalogPath'],'catalogBlobOid':p['catalogBlobOid'],'catalogFileSha256':p['catalogFileSha256'],
      'callerUseStatus':p['callerUseStatus'],'callerContextSummary':p['callerContextSummary'],
      'currentTarget':p['currentTarget'],'currentTargetSha256':p['currentTargetSha256'],
      'primaryDisposition':p['disposition'],'primaryReviewedTarget':p['reviewedTarget'],'primaryReviewedTargetSha256':p['reviewedTargetSha256'],
      'crossReviewDisposition':disp,'crossReviewTarget':target,'crossReviewTargetSha256':target_sha,
      'crossReviewTargetPlaceholders':sorted(re.findall(r'\{([A-Za-z][A-Za-z0-9_]*)\}',target)) if target is not None else None,
      'crossReviewTargetMarkup':re.findall(r'</?[A-Za-z][^>]*>',target) if target is not None else None,
      'protectedLiterals':p['protectedLiterals'],'currentProtectedLiteralMismatches':p['currentProtectedLiteralMismatches'],
      'crossReviewProtectedLiteralMismatches':[] if target is not None else None,
      'rationale':rationale,'rationaleOrigin':origin,'confidence':'moderate' if disp!='hold' else 'high',
      'nativeSpeakerReview':'outstanding'
    })

counts=collections.Counter(x['crossReviewDisposition'] for x in cross)
assert len(cross)==300 and dict(counts)=={'accept-current':220,'accept-proposal':38,'hold':36,'revise-proposal':6},dict(counts)
write_jsonl(OUT/'crossreview-decisions.jsonl',cross)

findings=[]
for (rank,locale),(target,rationale) in OVERRIDES.items():
  p=primary_cells[(rank,locale)]
  findings.append({'selectionRank':rank,'sourceId':p['sourceId'],'sourceText':p['sourceText'],'locale':locale,
    'primaryDisposition':p['disposition'],'currentTarget':p['currentTarget'],'primaryTarget':p['proposedTarget'] or p['reviewedTarget'],
    'crossReviewDisposition':'revise-proposal','recommendedTarget':target,'recommendedTargetSha256':sha(target),
    'rationale':rationale,'requiresNativeSpeakerReview':True})
write_jsonl(OUT/'independent-findings.jsonl',findings)

caller_by_rank={x['selectionRank']:x for x in caller_rows}
gaps=[]
for rank in (37,42,49):
  row=caller_by_rank[rank]
  gaps.append({'selectionRank':rank,'sourceId':row['sourceId'],'source':row['source'],'sourceSha256':row['sourceSha256'],
    'callerUseStatus':row['callerUseStatus'],'callerReferenceCount':row['callerReferenceCount'],
    'callerRefs':row['callerRefs'],'affectedLocaleCount':12,'affectedCells':12,
    'reason':HOLD_REASON[rank],
    'recommendedRemediation': 'Replace the fragment or full sentence with a caller-pinned count-aware localized message/ICU plural form. Re-review the current 12 translations after the actual numeric range and caller context are established.'})
write_jsonl(OUT/'source-runtime-gaps.jsonl',gaps)

# Re-evaluate the Spanish direct-address lane for the full selection.
es_rows=[]
for n in range(26,51):
  p=primary_cells[(n,'es')]
  target=next(x for x in cross if x['selectionRank']==n and x['locale']=='es')['crossReviewTarget']
  applicable=n in (29,35,39)
  reason={29:'Direct source instruction “Open a result”; current “Abre” uses informal tú and was changed to formal “Abra”.',
          35:'Direct request prompt; “Ingrese” is formal usted imperative.',
          39:'Source action “Choose”; “Elija” is formal usted imperative.'}.get(n,'No direct usted/tú imperative is used in this source and target; infinitive control labels or declarative text do not set address form.')
  es_rows.append({'selectionRank':n,'sourceId':p['sourceId'],'sourceText':p['sourceText'],'sourceSha256':p['sourceSha256'],
    'primaryTarget':p['currentTarget'],'crossReviewTarget':target,'formalAddressApplicable':applicable,
    'formalAddressStatus':'formal-imperative' if applicable else 'not-applicable','rationale':reason,
    'crossReviewDisposition':next(x for x in cross if x['selectionRank']==n and x['locale']=='es')['crossReviewDisposition']})
write_jsonl(OUT/'spanish-formal-applicability.jsonl',es_rows)

summary={
 'repository':'snapetech-org/slskdN','pullRequest':409,'window':'W46 reconstructed ranks 26–50; historical source ordinal unavailable',
 'exactHead':head,'exactTree':tree,'sourceCount':25,'localeCount':12,'cellCount':len(cross),
 'crossReviewDispositionCounts':dict(sorted(counts.items())),
 'primaryProposalCount':39,'primaryProposalsAccepted':38,'primaryProposalsRevised':1,
 'additionalCorrectionsProposed':5,'heldSourceIds':[primary_cells[(rank,'ar')]['sourceId'] for rank in (37,42,49)],'heldCells':counts['hold'],
 'directCallerRows':sum(x['callerUseStatus']=='production-localization-reference-found' for x in caller_rows),
 'callerReferences':sum(x['callerReferenceCount'] for x in caller_rows),'callerPinsReattested':len(caller_checks),
 'catalogCount':len(catalog_checks),'orderedKeysPerCatalog':6170,'catalogKeySetsExact':True,
 'placeholderMismatchesFinal':0,'markupMismatchesFinal':0,'protectedLiteralMismatchesFinal':0,
 'currentProtectedLiteralMismatchCells':sum(bool(x['currentProtectedLiteralMismatches']) for x in cross),
 'nativeSpeakerApproval':False,'headedBrowserReview':False,'testsBuildScansCiRun':False,
 'repositoryModified':False,'allSevenPrHeadsRequeriedAndMatched':True,'sourceCallerAndCatalogPinsReattested':True,
 'reviewerHost':socket.gethostname(),'reviewedAtUtc':dt.datetime.now(dt.timezone.utc).isoformat()
}
write_json(OUT/'crossreview-summary.json',summary)
readme=f'''# slskdN PR #409 W46 independent cross-review\n\nThis packet independently cross-reviews the 25 reconstructed pending source IDs at ranks 26–50 across 12 locales (300 cells). It does not claim a historical ordinal. Exact PR #409 head/tree: `{head}` / `{tree}`. All seven localization PR heads, states and draft statuses were requeried and matched the primary snapshot; #409 remains OPEN/DRAFT.\n\nCross-review dispositions: `{dict(sorted(counts.items()))}`. The 39 primary proposals were independently checked: 38 accepted and Arabic #47 revised because the primary target meant “unclassified” rather than “unrated.” Five additional corrections are recorded: formal Spanish address at #29; clearer Arabic security terminology at #30; remove a dangling Arabic preposition at #32; use software-conflict terminology in Arabic #34; and hyphenate German `DHT-Schlüssel` at #45.\n\nAll 300 source IDs and current catalog values were re-attested against the exact current commit. All 12 catalog blobs and all caller line/file hashes were verified from the pinned worktree. Final non-held targets preserve placeholders, markup, and protected literals (`ContentID`, `JSON`, `DHT`). One pre-existing current Hindi #32 target changes protected `ContentID` casing; the cross-review proposal restores it.\n\nThree source/runtime issues remain held across 12 locales each (36 cells): #37 has a dynamic count with no verified production caller and no count-aware grammar; #42 concatenates a track count with a fixed fragment; #49 shares one word between a message separator and a count-bearing Wishlist badge. Exact refs and caller-level remediation are in `source-runtime-gaps.jsonl`.\n\nThis is independent machine-assisted language review, not qualified native-speaker approval. Headed-browser and RTL visual review remain outstanding; the browser coordinator is unavailable. No repo files or PR metadata were changed, and no tests, builds, scans or CI ran.\n'''
(OUT/'README.md').write_text(readme)

# Seal every packet artifact except the checksum list and manifest themselves.
files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name not in ('SHA256SUMS.txt','manifest.json'))
sums=''.join(f'{sha(p.read_bytes())}  {p.name}\n' for p in files).encode()
(OUT/'SHA256SUMS.txt').write_bytes(sums)
manifest={'repository':'snapetech-org/slskdN','pullRequest':409,'window':'W46 reconstructed ranks 26-50 cross-review',
 'head':head,'tree':tree,'primaryManifestSha256':EXPECTED_PRIMARY_MANIFEST,'primarySha256SumsSha256':EXPECTED_PRIMARY_SUMS,
 'cellCount':len(cross),'dispositionCounts':dict(sorted(counts.items())),
 'files':[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in files],
 'sha256SumsSha256':sha(sums)}
write_json(OUT/'manifest.json',manifest)
print(json.dumps({'summary':summary,'manifestSha256':sha((OUT/'manifest.json').read_bytes()),'sha256SumsSha256':sha(sums),'output':str(OUT)},ensure_ascii=False,indent=2))
