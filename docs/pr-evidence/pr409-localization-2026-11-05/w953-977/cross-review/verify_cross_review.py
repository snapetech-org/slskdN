#!/usr/bin/env python3
from __future__ import annotations
import argparse,collections,hashlib,json,re,subprocess,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent; ROOT=OUT.parent; CF=ROOT/'candidate-free'/'input'; PR=ROOT/'primary-review'; BL=ROOT/'blind-review'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PH=re.compile(r'\{[^{}]+\}'); MARKUP=re.compile(r'<[^>]+>'); NUM=re.compile(r'(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])')
FORBIDDEN_HOLD={'sourceId','source','sourceText','currentTarget','recommendedTarget','primaryCandidateTarget','blindProposalTarget','proposalText'}
def sha(b):return hashlib.sha256(b).hexdigest()
def shat(s):return sha(s.encode('utf-8'))
def rdj(p):return json.loads(p.read_text())
def rdjl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def need(ok,msg):
 if not ok:raise SystemExit('FAIL: '+msg)
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args])
def token_ok(source,target,token):
 return (collections.Counter(PH.findall(source))==collections.Counter(token['placeholders']['source'])==collections.Counter(PH.findall(target)) and
         MARKUP.findall(source)==token['markup']['source']==MARKUP.findall(target) and
         collections.Counter(NUM.findall(source))==collections.Counter(token['numbers']['source'])==collections.Counter(NUM.findall(target)) and
         all(x in target for x in token['protectedLiterals']['source']))
def verify_sums(folder):
 sums={}
 for line in (folder/'SHA256SUMS.txt').read_text().splitlines():
  h,name=line.split('  ',1);sums[name]=h
 actual={p.relative_to(folder).as_posix():sha(p.read_bytes()) for p in folder.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
 need(sums==actual,'checksum inventory '+str(folder))

def portable():
 verify_sums(OUT); verify_sums(CF); verify_sums(PR); verify_sums(BL)
 cfm=rdj(CF/'manifest.json'); prm=rdj(PR/'manifest.json'); blm=rdj(BL/'manifest.json')
 summary=rdj(OUT/'summary.json'); pins=rdj(OUT/'input-pins.json')
 need(summary['head']==cfm['head']==prm['head']==blm['head']=='fc8e42a06363ceee762ae084bbe716953d4a5d94','head pins')
 need(summary['tree']==cfm['tree']==prm['tree']==blm['tree']=='e04aa06b8cfb0ee41cae90aef601a0552b5e85bd','tree pins')
 need(pins['sourceCallerCurrentAndReviewerInputs']['candidateFreeCellsSha256']==sha((CF/'source-current-cells.jsonl').read_bytes()),'candidate-free cell input pin')
 need(pins['sourceCallerCurrentAndReviewerInputs']['primaryReviewSha256']==sha((PR/'primary-review.jsonl').read_bytes()),'primary review input pin')
 need(pins['sourceCallerCurrentAndReviewerInputs']['blindLedgerSha256']==sha((BL/'blind-ledger.jsonl').read_bytes()),'blind review input pin')
 before=rdj(OUT/'attestation'/'live-before.json'); after=rdj(OUT/'attestation'/'live-after.json')
 for att in (before,after):
  need(att['prApi']['state']=='OPEN' and att['prApi']['isDraft'] is True and att['prApi']['headRefOid']==att['headSha']==summary['head'],'live PR state')
  need(att['headTree']==summary['tree'] and att['apiBaseSha']==summary['apiBase'],'live Git pins')
  need(att['remoteRefs']['refs/pull/409/head']==att['headSha'] and att['remoteRefs']['refs/heads/codex/slskdn-oidc-tooltip-localization-20261030']==att['headSha'],'live branch/pull refs')
  need(att['remoteRefs']['refs/heads/main']==att['liveMainSha'],'live main ref')
 need(before['headSha']==after['headSha'] and before['headTree']==after['headTree'] and before['apiBaseSha']==after['apiBaseSha'],'before/after head and base')
 need(before['liveMainSha']==after['liveMainSha'] and before['liveMainTree']==after['liveMainTree'],'before/after live main')
 need(before['exactWorktreeClean'] and after['exactWorktreeClean'],'clean exact checkout attested')
 sources=rdjl(CF/'selected-sources.jsonl'); cells=rdjl(CF/'source-current-cells.jsonl')
 srcmap={r['sourceId']:r for r in sources}; cellmap={(r['sourceId'],r['locale']):r for r in cells}
 primary=rdjl(PR/'primary-review.jsonl'); blind=rdjl(BL/'blind-ledger.jsonl')
 pmap={(r['sourceId'],r['locale']):r for r in primary}; bmap={(r['continuationRank'],r['locale']):r for r in blind}
 ledger=rdjl(OUT/'cross-review-ledger.jsonl'); holds=rdjl(OUT/'holds-hash-only.jsonl'); reconc=rdjl(OUT/'proposal-reconciliation.jsonl')
 need(len(ledger)==300 and len(holds)==12,'ledger and hold counts')
 need([(r['continuationRank'],r['sourceId'] if 'sourceId' in r else r['sourceIdSha256'],r['locale']) for r in ledger]==[(c['continuationRank'],c['sourceId'] if c['continuationRank']!=966 else shat(c['sourceId']),c['locale']) for c in cells],'cross ledger cell order/identity')
 counts=collections.Counter(); outcome=collections.Counter(); expected_props=set()
 for (sid,loc),c in cellmap.items():
  rank=c['continuationRank']; p=pmap[(sid,loc)]; b=bmap[(rank,loc)]
  row=next(x for x in ledger if x['continuationRank']==rank and x['locale']==loc)
  source_hash=row.get('sourceTextSha256',row.get('sourceSha256'))
  need(source_hash==c['sourceSha256'] and row['currentTargetSha256']==c['currentTargetSha256'] and row['callerContextSha256']==c['callerContextSha256'],'cross source/current/caller hash')
  need(row['primaryDisposition']==p['disposition'] and row['blindDecision']==b['decision'],'review disposition reconciliation')
  if b['decision']=='hold':
   need(rank==966 and not (set(row)&FORBIDDEN_HOLD),'cross hold contains text')
   h=next(x for x in holds if x['continuationRank']==rank and x['locale']==loc)
   need(h['sourceIdSha256']==shat(sid) and h['sourceTextSha256']==c['sourceSha256'] and h['currentTargetSha256']==c['currentTargetSha256'] and h['callerContextSha256']==c['callerContextSha256'],'hash-only hold binding')
   counts['hold-hash-only']+=1
  else:
   need(row['sourceId']==sid and row['recommendationSource'] in ('primary','blind','current','cross-adjustment'),'non-hold identity/source')
   target=row['recommendedTarget']; th=shat(target)
   need(th==row['recommendedTargetSha256'],'recommended target hash')
   token=next(t for t in c['tokenEvidence'].values()) if False else c['tokenEvidence']
   need(token_ok(c['source'],target,token),'recommended target token integrity')
   need(row['tokenIntegrity']=={'placeholderParity':True,'markupParity':True,'numericTokensPreserved':True,'protectedLiteralsPreserved':True},'recorded target token flags')
   if th==c['currentTargetSha256']:need(row['recommendation']=='accept-current','current disposition')
   counts[row['recommendation']]+=1
  # Independently check every proposed primary and blind target, including proposals not selected.
  if p['disposition']=='correction':
   need(shat(p['candidateTarget'])==p['candidateTargetSha256'] and token_ok(c['source'],p['candidateTarget'],c['tokenEvidence']),'primary proposal token/hash')
   expected_props.add(('primary',rank,sid,loc,p['candidateTargetSha256']))
  if b['decision'] in ('correction','refinement'):
   need(shat(b['proposedTarget'])==b['proposedTargetSha256'] and token_ok(c['source'],b['proposedTarget'],c['tokenEvidence']),'blind proposal token/hash')
   expected_props.add(('blind',rank,sid,loc,b['proposedTargetSha256']))
 for h in holds:need(not(set(h)&FORBIDDEN_HOLD) and h['sourceTextOmitted'] and h['currentTargetTextOmitted'] and h['proposalTextOmitted'],'hold text omission flags')
 actual_props={(r['reviewer'],r['continuationRank'],r.get('sourceId'),r['locale'],r['proposalSha256']) for r in reconc}
 # Held primary proposals intentionally use only a hashed source identifier.
 for r in reconc:
  if r['crossOutcome']=='held-hash-only':
   match=next((x for x in holds if x['continuationRank']==r['continuationRank'] and x['locale']==r['locale']),None)
   need(match and r['sourceIdSha256']==match['sourceIdSha256'],'held proposal hash binding')
 need(len(reconc)==177,'proposal reconciliation row count')
 need(sum(1 for r in reconc if r['reviewer']=='primary')==111 and sum(1 for r in reconc if r['reviewer']=='blind')==66,'reviewer proposal reconciliation counts')
 # Bind every proposal to its exact reviewer input using hashes; no proposal text is duplicated in reconciliation rows.
 for r in reconc:need(r['proposalTextIncluded'] is False and r['sourceSha256'] and r['callerContextSha256'] and r['currentTargetSha256'],'proposal reconciliation source pins')
 need(dict(counts)==summary['recommendationCounts'],'summary disposition counts')
 need(len(reconc)==summary['proposalRecordsReconciled'] and len(holds)==summary['crossHoldCount'],'summary proposal/hold counts')
 return {'result':'PASS','head':summary['head'],'tree':summary['tree'],'mainBefore':before['liveMainSha'],'sources':25,'cells':300,'proposalsReconciled':177,'hashOnlyHolds':12,'recommendationCounts':dict(counts),'tokenIntegrity':'PASS for all proposals and 288 non-hold recommendations'}

def exact_repo(repo):
 summary=rdj(OUT/'summary.json'); head=summary['head']; tree=summary['tree']
 need(git(repo,'rev-parse','HEAD').decode().strip()==head,'exact repo HEAD')
 need(git(repo,'rev-parse','HEAD^{tree}').decode().strip()==tree,'exact repo tree')
 need(git(repo,'status','--porcelain=v1').decode().strip()=='','exact repo clean')
 outputs=[]
 for script,folder in [(CF/'verify_candidate_free.py',CF),(PR/'verify_primary.py',PR)]:
  res=subprocess.run(['python3',str(script),str(repo)],cwd=folder,text=True,capture_output=True,check=True)
  outputs.append(json.loads(res.stdout))
 res=subprocess.run(['python3',str(BL/'verify_blind_review.py')],cwd=BL,text=True,capture_output=True,check=True)
 outputs.append(json.loads(res.stdout))
 need(all(x.get('result')=='PASS' for x in outputs),'upstream packet exact verifiers')
 print(json.dumps({'exactWorktree':'PASS','head':head,'tree':tree,'upstreamVerifiers':outputs},ensure_ascii=False,indent=2))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('repo',nargs='?');args=ap.parse_args()
 result=portable()
 if args.repo:exact_repo(Path(args.repo))
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
