#!/usr/bin/env python3
import collections,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PACKET=ROOT.parent
CF=PACKET/"candidate-free"/"input";PR=PACKET/"primary-review";BL=PACKET/"blind-review"
HEAD="311127db7f4d5097dfd1dde5eaa2150f82f48f30";TREE="23210cd313efd929cca9ceda0fd78da19e5ed50d"
LOCALES=("ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant")
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def j(p):return json.loads(p.read_text(encoding="utf-8"))
def jl(p):return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def sums(root,name):
 d={}
 for line in (root/name).read_text(encoding="utf-8").splitlines():
  h,n=line.split("  ",1);d[n]=h
 assert d and all(sha((root/n).read_bytes())==h for n,h in d.items()),"checksum mismatch: "+str(root)
 return d
def checks(s,t):
 p=sorted(re.findall(r"\{[^{}]+\}",s))==sorted(re.findall(r"\{[^{}]+\}",t))
 g=sorted(re.findall(r"</?[A-Za-z][^>]*>",s))==sorted(re.findall(r"</?[A-Za-z][^>]*>",t))
 n=re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)==re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",t)
 q=set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])",s))
 for x in ("Wishlist","Soulseek","Discogs","Pod","Prometheus","Lidarr","ReplayGain","SongID","WebSocket","VBR"):
  if re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",s):q.add(x)
 return {"placeholders":p,"markup":g,"numbers":n,"protectedLiterals":all(x in t for x in q)}
def main():
 root_sums=sums(PACKET,"SHA256SUMS.txt")
 actual=sorted(p for p in PACKET.rglob("*") if p.is_file() and p.name!="SHA256SUMS.txt")
 assert set(root_sums)=={p.relative_to(PACKET).as_posix() for p in actual},"root inventory mismatch"
 sums(CF,"PACKET-SHA256SUMS.txt");sums(PR,"SHA256SUMS.txt");sums(BL,"SHA256SUMS.txt")
 subprocess.check_call([sys.executable,str(CF/"verify_input.py")],stdout=subprocess.DEVNULL)
 subprocess.check_call([sys.executable,str(PR/"output"/"verify_primary.py")],stdout=subprocess.DEVNULL)
 subprocess.check_call([sys.executable,str(BL/"output"/"verify_review.py")],stdout=subprocess.DEVNULL)
 m=j(ROOT/"manifest.json")
 assert m["head"]==HEAD and m["tree"]==TREE and m["scope"]=={"continuationRankStart":678,"continuationRankEnd":702,"sourceIds":25,"locales":12,"cells":300}
 assert m["candidateFreeInput"]["checksumListSha256"]==sha((CF/"PACKET-SHA256SUMS.txt").read_bytes())
 assert m["primaryInput"]["checksumListSha256"]==sha((PR/"SHA256SUMS.txt").read_bytes())
 assert m["blindInput"]["checksumListSha256"]==sha((BL/"SHA256SUMS.txt").read_bytes()) and m["blindInput"]["canonicalFullPacketOnly"] is True
 src=jl(CF/"source-current-cells.jsonl");by={(x["continuationRank"],x["locale"]):x for x in src}
 p_rows=jl(PR/"output"/"primary-review.jsonl");pmap={(x["continuationRank"],x["locale"]):x for x in p_rows}
 b_rows=jl(BL/"output"/"blind-ledger.jsonl");bmap={(x["continuationRank"],x["locale"]):x for x in b_rows}
 final=jl(ROOT/"cross-review.jsonl");assert len(src)==len(p_rows)==len(b_rows)==len(final)==300 and len(by)==len(final)
 target_map={(x["continuationRank"],x["locale"]):x for x in jl(ROOT/"blind-target-map.jsonl")}
 assert len(target_map)==31
 rows={(x["continuationRank"],x["locale"]):x for x in final};assert len(rows)==300
 exact=norm=acceptdiff=both=ponly=bonly=0;counts=collections.Counter();pc=collections.Counter(x["disposition"] for x in p_rows);bc=collections.Counter(x["recommendation"] for x in b_rows)
 for key,c in by.items():
  r=rows[key];p=pmap[key];b=bmap[key];hp=p["proposedTarget"] is not None;hb=b["recommendedTargetSha256"] is not None
  assert r["head"]==HEAD and r["tree"]==TREE and r["window"]=="W72"
  for k in ("sourceId","sourceSha256","locale","catalogPath","catalogFileSha256","catalogGitBlob","currentTargetSha256","callerContextSha256"):
   assert r[k]==c[k],"source pin mismatch "+k
  assert r["callerCount"]==len(c["callerRefs"])
  expected=[{k:x[k] for k in ("path","line","lineSha256","contextSha256","fileSha256","gitBlob")} for x in c["callerRefs"]]
  assert r["callerRefs"]==expected
  assert r["primaryDisposition"]==p["disposition"] and r["primaryProposalPresent"]==hp and r["primaryProposalSha256"]==p["proposedTargetSha256"]
  assert r["blindDisposition"]==b["recommendation"] and r["blindProposalPresent"]==hb and r["blindProposalSha256"]==b["recommendedTargetSha256"]
  exact+=p["disposition"]!=b["recommendation"]
  norm+=p["disposition"]!=b["recommendation"]
  acceptdiff+=(("change" if hp else p["disposition"])!=("change" if hb else b["recommendation"]))
  both+=hp and hb;ponly+=hp and not hb;bonly+=hb and not hp
  rec=r["recommendation"];counts[rec]+=1
  if c["callerRefs"]:
   if hp or hb:
    assert rec in ("correct","refine") and r["recommendedTargetIncluded"] is True and r["targetTextIncluded"] is True
    assert r["sourceIncluded"] is r["currentTargetIncluded"] is True
    assert r["source"]==c["source"] and r["currentTarget"]==c["currentTarget"]
    target=r["recommendedTarget"]
    assert sha(target.encode())==r["recommendedTargetSha256"]
    assert r["recommendedTokenChecks"]==checks(c["source"],target) and all(r["recommendedTokenChecks"].values())
    assert r["currentTokenChecks"]==checks(c["source"],c["currentTarget"])
    tm=target_map[(key[0],key[1])]
    assert sha(tm["recommendedTarget"].encode())==tm["recommendedTargetSha256"]==b["recommendedTargetSha256"]
    assert target==tm["recommendedTarget"]
    if hp and key!=(697,"hi"):assert target==p["proposedTarget"]
    assert r["recommendedTargetSha256"]==b["recommendedTargetSha256"]
   else:
    assert rec=="accept-current" and r["targetTextIncluded"] is False
    assert not any(k in r for k in ("source","currentTarget","recommendedTarget"))
    assert r["recommendedTargetSha256"] is None and r["recommendedTokenChecks"] is None and r["currentTokenChecks"] is None
  else:
   assert rec=="hold" and r["targetTextIncluded"] is False and r["sourceIncluded"] is False and r["currentTargetIncluded"] is False
   assert not any(k in r for k in ("source","currentTarget","recommendedTarget"))
   assert r["recommendedTargetSha256"] is None and r["recommendedTokenChecks"] is None and r["currentTokenChecks"] is None
   assert not hp and not hb
  assert r["recommendationBasis"] and r["rationale"]
 assert dict(counts)==m["finalDispositionCounts"]=={"accept-current":161,"hold":108,"correct":24,"refine":7}
 comp=m["primaryBlindComparison"]
 assert comp=={"cellsWithExactDispositionDifference":exact,"cellsWithNormalizedDispositionDifference":norm,"cellsWithAcceptVersusChangeDifference":acceptdiff,"proposalsBoth":both,"primaryOnlyProposals":ponly,"blindOnlyProposals":bonly,"selectedPrimaryFlaggedChanges":22,"selectedBlindFlaggedChanges":31,"selectedBlindOnlyChanges":9,"rootReviewCorrections":1}
 assert dict(pc)==m["primaryDispositionCounts"] and dict(bc)==m["blindDispositionCounts"]
 assert (exact,norm,acceptdiff,both,ponly,bonly)==(9,9,9,22,0,9)
 assert sum(counts[x] for x in ("correct","refine"))==31==m["targetTextIncludedForSelectedChanges"]
 corrections=jl(ROOT/"root-review-corrections.jsonl")
 assert len(corrections)==1
 corr=corrections[0];k=(697,"hi");c=by[k];p=pmap[k];b=bmap[k];r=rows[k]
 assert corr["head"]==HEAD and corr["tree"]==TREE and corr["sourceId"]==c["sourceId"] and corr["currentTargetSha256"]==c["currentTargetSha256"]
 assert corr["primaryTargetSha256"]==p["proposedTargetSha256"] and corr["blindTargetSha256"]==b["recommendedTargetSha256"]
 assert corr["selectedTargetSha256"]==r["recommendedTargetSha256"]==corr["blindTargetSha256"]
 assert p["proposedTarget"].endswith("\u3002") and b["recommendedTargetSha256"]==corr["selectedTargetSha256"]
 assert r["recommendedTarget"].endswith("\u0964") and corr["selectedTarget"]==r["recommendedTarget"]
 assert all(corr["tokenChecks"].values()) and corr["reviewOrigin"]=="parent root quality audit"
 priorh=jl(ROOT/"prior-held-cell-reattestation-hash-only.jsonl");priorids=jl(ROOT/"prior-selected-id-exclusions-hash-only.jsonl")
 assert len(priorh)==152 and len(priorids)==1782
 assert all(x["sourceTextIncluded"] is False and x["targetTextIncluded"] is False and "source" not in x and "currentTarget" not in x and "priorTarget" not in x for x in priorh)
 assert all(x["sourceTextIncluded"] is False and x["targetTextIncluded"] is False and "source" not in x and "target" not in x for x in priorids)
 assert sum(r["recommendation"]=="hold" for r in final)==m["callerlessHoldCountHashOnly"]==108
 for fn in ("candidate-free","primary-review","blind-review"):
  for x in (PACKET/fn).rglob("*"):
   if x.is_file():
    rel=x.relative_to(PACKET).as_posix()
    assert ".github/workflows/" not in rel and not rel.startswith(".github/workflows/")
 before=j(ROOT/"live-before.json");after=j(ROOT/"live-after.json")
 for a in (before,after):
  assert a["headRefOid"]==a["branchRefOid"]==a["pullRefOid"]==HEAD and a["treeOid"]==TREE and a["deploymentsForHead"]==0
 assert m["workflowPathsIncluded"]==0 and m["rootReviewCorrectionCount"]==1
 print(json.dumps({"verifier":"PASS","rootFilesVerified":len(root_sums),"candidateFreePrimaryBlindVerifiers":"PASS","cells":300,"finalDispositions":dict(counts),"selectedTargets":31,"blindOnlySelected":9,"rootReviewCorrections":1,"callerlessHoldsHashOnly":108,"priorHoldsHashOnly":152,"priorIdsHashOnly":1782,"liveHead":HEAD,"tree":TREE},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
