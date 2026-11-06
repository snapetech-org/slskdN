#!/usr/bin/env python3
import hashlib,json,re,subprocess,sys
from collections import Counter
from pathlib import Path
O=Path(__file__).resolve().parent
I=Path('/home/keith/Documents/code/task-scratch/slskdn-pr409-w68-ranks578-602-candidate-free-20261103/input')
REPO=Path('/home/keith/Documents/code/task-scratch/slskdn-pr409-w68-apply-20261103/repo')
HEAD='973a65312a475de4d8aa39aee837249553fd884e'; TREE='2a7b200dd1fe96f894bfdb663f656d6ffd48f487'; BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']; BASE=('placeholder','markup','numeric','protectedLiteral')
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode('utf-8')).hexdigest()
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def ph(s): return sorted(set(re.findall(r'\{[^{}]+\}',s)))
def tags(s): return sorted(re.findall(r'</?[A-Za-z][^>]*>',s))
def nums(s): return re.findall(r'(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])',s)
def prot(s):
 found=set(re.findall(r'(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])',s))
 for x in ('Wishlist','Soulseek','Discogs','Pod'):
  if re.search(r'(?<![A-Za-z0-9])'+re.escape(x)+r'(?![A-Za-z0-9])',s): found.add(x)
 return sorted(found)
def tok(s): return {'placeholders':ph(s),'markup':tags(s),'numeric':nums(s),'protectedLiterals':prot(s)}
subprocess.run([sys.executable,str(I/'verify_input.py')],check=True,capture_output=True,text=True)
subprocess.run(['sha256sum','-c','PACKET-SHA256SUMS.txt'],cwd=I,check=True,capture_output=True,text=True)
subprocess.run(['sha256sum','-c','SHA256SUMS.txt'],cwd=O,check=True)
im=j(I/'manifest.json'); m=j(O/'manifest.json'); s=j(O/'summary.json')
assert (im['head'],im['tree'],im['continuationRankRange'],im['remainingQueueRankRange'])==(HEAD,TREE,[578,602],[478,502])
assert (m['repository'],m['pullRequest'],m['branch'],m['window'],m['head'],m['tree'])==('snapetech-org/slskdN',409,BRANCH,'W68',HEAD,TREE)
assert (m['sourceCount'],m['localeCount'],m['cellCount'],m['priorHeldCellsReattested'])==(25,12,300,128)
assert m['blindPacketAccessed'] is False and s['blindPacketAccessed'] is False
assert s['nativeSpeakerReview']==m['nativeSpeakerReview']=='not performed' and s['browserReview']==m['browserReview']=='not performed'
assert s['repositoryOrPRFilesEdited'] is False and s['candidateFreeInputVerified'] is True
assert m['inputManifestSha256']==sha((I/'manifest.json').read_bytes()) and m['inputChecksumListSha256']==sha((I/'PACKET-SHA256SUMS.txt').read_bytes()) and m['inputLedgerSha256']==sha((I/'source-current-cells.jsonl').read_bytes())

def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
assert (git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}'),git('branch','--show-current'),git('status','--porcelain=v1'))==(HEAD,TREE,'','')
pr=json.loads(subprocess.check_output(['gh','api','repos/snapetech-org/slskdN/pulls/409'],text=True))
assert pr['state']=='open' and pr['draft'] is True and pr['head']['sha']==HEAD and pr['head']['ref']==BRANCH and pr['head']['repo']['full_name']=='snapetech-org/slskdN'
refs=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin',f'refs/heads/{BRANCH}','refs/pull/409/head'],text=True).splitlines(); refmap={x.split()[1]:x.split()[0] for x in refs}
assert refmap.get(f'refs/heads/{BRANCH}')==HEAD and refmap.get('refs/pull/409/head')==HEAD
actual={p.name for p in O.iterdir() if p.is_file()}-{'manifest.json','SHA256SUMS.txt'}; listed={x['path']:x for x in m['files']}; assert set(listed)==actual
for name,item in listed.items():
 data=(O/name).read_bytes(); assert len(data)==item['bytes'] and sha(data)==item['sha256'],name
cells=jl(I/'source-current-cells.jsonl'); contexts=jl(I/'caller-contexts.jsonl'); rows=jl(O/'primary-ledger.jsonl')
assert len(cells)==len(rows)==300 and len(contexts)==25
ci={(x['continuationRank'],x['locale']):x for x in cells}; cx={x['continuationRank']:x for x in contexts}; seen=set(); counts=Counter(); base={x:0 for x in BASE}; final={x:0 for x in BASE}; proposals=0
assert sorted(cx)==list(range(578,603)) and all(x['callers'] and x['productionCallerCount']==len(x['callers']) for x in contexts)
assert s['callerCountByRank']=={str(x['continuationRank']):x['productionCallerCount'] for x in contexts}
for row in rows:
 key=(row['continuationRank'],row['locale']); assert key not in seen; seen.add(key); assert row['locale'] in LOCALES and row['continuationRank'] in range(578,603)
 x=ci[key]; c=cx[key[0]]; counts[row['disposition']]+=1
 assert (row['repository'],row['pullRequest'],row['window'],row['head'],row['tree'])==(im['repository'],409,'W68',HEAD,TREE)
 for field in ('sourceId','source','sourceSha256','catalogKey','catalogPath','catalogFileSha256','catalogGitBlob','currentTarget','currentTargetSha256','callerContextSha256','callerRefs','continuationRank','remainingQueueRank','locale'):
  assert row[field]==x[field],(key,field)
 assert row['callerContexts']==c['callers'] and row['callerContextSourceId']==c['sourceId'] and row['callerContextSourceSha256']==c['sourceSha256']
 assert row['containsCandidate'] is False and row['verdict'] is None and row['rationale'] and row['confidence'] in ('high','moderate','low')
 assert row['disposition'] in ('accept-current','correction','refinement')
 target=row['proposedTarget'] if row['disposition'] in ('correction','refinement') else row['currentTarget']
 if row['disposition'] in ('correction','refinement'):
  assert isinstance(target,str) and target and target!=row['currentTarget']; proposals+=1
 else: assert 'proposedTarget' not in row
 assert row['reviewedTargetSha256']==sha(target)
 st,ct,rt=tok(row['source']),tok(row['currentTarget']),tok(target)
 checks={'placeholdersPreserved':st['placeholders']==rt['placeholders'],'markupPreserved':st['markup']==rt['markup'],'numericTokensPreserved':st['numeric']==rt['numeric'],'protectedLiteralsPreserved':all(target.count(lit)>=row['source'].count(lit) for lit in st['protectedLiterals'])}
 assert row['tokenAudit']=={'source':st,'current':ct,'reviewed':rt,'checks':checks} and all(checks.values()),key
 base['placeholder']+=st['placeholders']!=ct['placeholders']; base['markup']+=st['markup']!=ct['markup']; base['numeric']+=st['numeric']!=ct['numeric']; base['protectedLiteral']+=not all(row['currentTarget'].count(lit)>=row['source'].count(lit) for lit in st['protectedLiterals'])
 final['placeholder']+=not checks['placeholdersPreserved']; final['markup']+=not checks['markupPreserved']; final['numeric']+=not checks['numericTokensPreserved']; final['protectedLiteral']+=not checks['protectedLiteralsPreserved']
assert seen==set(ci) and dict(base)==im['baselineTokenMismatchSummary'] and dict(final)=={x:0 for x in BASE}
assert dict(counts)=={'accept-current':271,'correction':29} and proposals==29
assert s['dispositionCounts']==dict(counts) and m['dispositionCounts']==dict(counts) and s['proposalCount']==m['proposalCount']==proposals and s['reviewedTokenMismatches']==dict(final)
prior=j(I/'prior-held-cell-reattestation-summary.json'); assert prior['expectedHeldCells']==prior['priorHeldCellsReattested']==128 and prior['allTargetHashesMatchPrior'] and prior['allCurrentCallerAndCatalogEvidenceRepinned']
assert s['priorHeldCellsReattested']==128 and s['priorHeldCellsUnchanged'] is True and s['callerlessSelectedRanks']==[]
print(json.dumps({'pass':True,'head':HEAD,'tree':TREE,'window':'W68','cells':300,'sources':25,'locales':12,'dispositions':dict(counts),'proposals':proposals,'baselineTokenMismatches':dict(base),'reviewedTokenMismatches':dict(final),'priorHoldsReattested':128,'callerlessSelectedSources':0,'PR':'OPEN/DRAFT','blindPacketAccessed':False,'nativeSpeakerReview':'not performed','browserReview':'not performed'},ensure_ascii=False,indent=2))
