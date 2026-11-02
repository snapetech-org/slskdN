#!/usr/bin/env python3
import collections,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261030/slskdn-pr409-batch4-docs-20261101')
INDEP=Path('/mnt/disks/scratch/task-scratch/slskdn-window32-independent-crossreview-20261102')
ROOTPKT=Path('/mnt/disks/scratch/task-scratch/slskdn-root-crossreview-W32-dfb9707f-20261102')
HEAD='dfb9707f946bf2686210bcf1072b9d70c8442a62'; TREE='9458e836ae12c02573535b5c9dc052f055b7820d'; SRC='469e060d9e0a3fd6f54bc75a69993ee2651d3e4b'
INPUT_SHA='09d534acad981c383c42c2da15b0c26a667af529cf108430ae7c388294c1f988'; CANDIDATE_SHA='ac67de5559bea50e815a729f95ff8a3c6e54bdd4751fc3d1278fd4add7808109'; INDEP_SHA='18dcbf5ae633336bf3cb423dc7c470adc38636aba9b2f17eb66c1d1d65f8204a'; ROOT_SHA='5ff63d8e936e7640febc50847ece6f1a3eee4928530dbaa03cacddfc070af7db'
LOCALES=['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
def sha(v):return hashlib.sha256(v if isinstance(v,bytes) else v.encode('utf-8')).hexdigest()
def read(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(*a):return subprocess.check_output(['git','-C',str(REPO),*a],text=True).strip()
def show(commit,path):return subprocess.check_output(['git','-C',str(REPO),'show',f'{commit}:{path}'])
def fail(s):raise SystemExit('FAIL: '+s)
def unique(rows,label):
 d={r['id']:r for r in rows}
 if len(d)!=len(rows):fail(f'duplicate IDs in {label}')
 return d
# Verify both reviewer bundles and fixed artifact checksums before preparing changes.
for directory in (INDEP,ROOTPKT):
 if subprocess.run(['sha256sum','-c','SHA256SUMS.txt'],cwd=directory,capture_output=True,text=True).returncode:fail(f'checksum mismatch in {directory}')
input_path=ROOT/'review-input.jsonl'; candidate_path=ROOT/'crossreview-plan.jsonl'; root_path=ROOTPKT/'root-disposition-ledger.jsonl'; independent_path=INDEP/'decision-ledger.jsonl'
if sha(input_path.read_bytes())!=INPUT_SHA or sha(candidate_path.read_bytes())!=CANDIDATE_SHA or sha(independent_path.read_bytes())!=INDEP_SHA or sha(root_path.read_bytes())!=ROOT_SHA:fail('review artifact hash mismatch')
manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
if (manifest['headCommit'],manifest['tree'],manifest['sourceSubtreeTree'])!=(HEAD,TREE,SRC):fail('manifest pin mismatch')
inputs=unique(read(input_path),'input'); candidates=unique(read(candidate_path),'candidate'); root_rows=unique(read(root_path),'root'); independent=unique(read(independent_path),'independent')
if len(inputs)!=266 or len(candidates)!=29 or len(root_rows)!=29 or len(independent)!=29 or set(candidates)!=set(root_rows):fail('review row-set mismatch')
counts=collections.Counter(r['disposition'] for r in root_rows.values())
if counts!=collections.Counter({'accept':22,'refine':7}):fail(f'root disposition counts mismatch: {dict(counts)}')
# Re-attest the immutable review base before application planning.
pr=json.loads(subprocess.check_output(['gh','api','repos/snapetech-org/slskdN/pulls/409','--jq','{head:.head.sha,state:.state,draft:.draft}'],text=True))
head,tree,src=git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}'),git('rev-parse','HEAD:src')
remote=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin','refs/heads/codex/slskdn-oidc-tooltip-localization-20261030'],text=True).split()[0]
if pr!={'head':HEAD,'state':'open','draft':True} or (head,tree,src,remote)!=(HEAD,TREE,SRC,HEAD):fail(f'live head diverged: {pr}/{head}/{tree}/{src}/{remote}')
if git('status','--porcelain'):fail('worktree must be clean before application')
# Verify the complete final ledger against the exact proposal, independent ledger, catalog value and callers.
plan=[]; changed_keys=collections.defaultdict(set); caller_count=0
for ident, root in root_rows.items():
 row=inputs.get(ident); candidate=candidates.get(ident); ind=independent.get(ident)
 if not row or not candidate or not ind:fail(f'missing joined review row: {ident}')
 loc=root['locale']; key=root['catalogKey']; target=root['finalTarget']
 if root['window']!=32 or root['prHead']!=HEAD or root['prTree']!=TREE or root['sourceSubtreeTree']!=SRC:fail(f'root pin mismatch: {ident}')
 if root['reviewInputSha256']!=INPUT_SHA or root['candidatePlanSha256']!=CANDIDATE_SHA or root['independentLedgerSha256']!=INDEP_SHA:fail(f'root ledger pin mismatch: {ident}')
 if root['sourceId']!=row['sourceId'] or root['locale']!=row['locale'] or root['catalogKey']!=row['catalogKey'] or root['catalogPath']!=row['catalogPath']:fail(f'cell coordinates mismatch: {ident}')
 if root['source']!=row['source'] or root['sourceSha256']!=row['sourceSha256'] or root['currentTarget']!=row['target'] or root['currentTargetSha256']!=row['targetSha256']:fail(f'source/current value mismatch: {ident}')
 if candidate['proposedTarget']!=root['proposedTarget'] or candidate['proposedTargetSha256']!=root['proposedTargetSha256']:fail(f'candidate/root proposal mismatch: {ident}')
 if ind['currentTarget']!=root['currentTarget'] or ind['sourceSha256']!=root['sourceSha256'] or ind['currentTargetSha256']!=root['currentTargetSha256']:fail(f'independent/root input mismatch: {ident}')
 if root['disposition'] not in {'accept','refine'} or root['nativeSpeakerApproved'] is not False:fail(f'unsupported root disposition: {ident}')
 if sha(target)!=root['finalTargetSha256'] or not target:fail(f'final hash/empty target: {ident}')
 if collections.Counter(re.findall(r'\{[^{}]+\}',target))!=collections.Counter(re.findall(r'\{[^{}]+\}',row['source'])):fail(f'placeholder mismatch: {ident}')
 for literal in row.get('protectedLiterals',[]):
  if target.count(literal)!=row['source'].count(literal):fail(f'protected literal mismatch: {ident}:{literal}')
 if root['sourceCallsites']!=row.get('sourceCallsites',[]):fail(f'caller evidence mismatch: {ident}')
 for c in row.get('sourceCallsites',[]):
  raw=show(HEAD,c['path']); lines=raw.decode('utf-8').splitlines(); line=lines[c['line']-1].strip()
  if sha(raw)!=c['fileSha256'] or line!=c['lineText'] or sha(line)!=c['lineTextSha256']:fail(f'caller pin mismatch: {ident}:{c["path"]}:{c["line"]}')
  caller_count+=1
 if ind['disposition'] not in {'accept','refine'}:fail(f'independent disposition missing: {ident}')
 raw=show(HEAD,root['catalogPath']); cat=json.loads(raw.decode('utf-8'))
 if sha(raw)!=manifest['currentCatalogFileSha256'][loc] or cat.get(key)!=root['currentTarget'] or sha(cat[key])!=root['currentTargetSha256']:fail(f'catalog pin/value mismatch: {ident}')
 changed_keys[loc].add(key)
 plan.append({'schemaVersion':1,'window':32,'id':ident,'sourceId':row['sourceId'],'locale':loc,'catalogPath':row['catalogPath'],'catalogKey':key,'source':row['source'],'sourceSha256':row['sourceSha256'],'oldTarget':row['target'],'oldTargetSha256':row['targetSha256'],'newTarget':target,'newTargetSha256':root['finalTargetSha256'],'rootDisposition':root['disposition'],'rootRationale':root['reviewRationale'],'candidateTarget':candidate['proposedTarget'],'candidatePlanSha256':CANDIDATE_SHA,'rootLedgerSha256':ROOT_SHA,'independentLedgerSha256':INDEP_SHA,'baseHead':HEAD,'baseTree':TREE,'baseSourceSubtreeTree':SRC,'baseCatalogFileSha256':manifest['currentCatalogFileSha256'][loc],'sourceCallsites':row.get('sourceCallsites',[]),'nativeSpeakerApproved':False})
plan.sort(key=lambda r:(LOCALES.index(r['locale']),r['sourceId']))
raw=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in plan).encode('utf-8')
(ROOT/'root-apply-plan-window32.jsonl').write_bytes(raw)
pre={'result':'READY_TO_APPLY','window':32,'pr':409,'livePrState':'OPEN','livePrDraft':True,'head':head,'tree':tree,'sourceSubtreeTree':src,'remoteHead':remote,'rootDispositionLedgerSha256':ROOT_SHA,'independentReviewLedgerSha256':INDEP_SHA,'candidatePlanSha256':CANDIDATE_SHA,'reviewInputSha256':INPUT_SHA,'applyPlanSha256':sha(raw),'cellsToApply':len(plan),'acceptedAsProposed':counts['accept'],'refinedAndAccepted':counts['refine'],'held':0,'callerPinsRechecked':caller_count,'localeCatalogPinsRechecked':len(manifest['currentCatalogFileSha256']),'allOldValuesMatchLiveCatalog':True,'allFinalHashesAndPlaceholdersPass':True,'worktreeCleanBeforeApplication':True,'nativeSpeakerApproved':False}
(ROOT/'application-preflight-window32.json').write_text(json.dumps(pre,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(pre,ensure_ascii=False,indent=2))
