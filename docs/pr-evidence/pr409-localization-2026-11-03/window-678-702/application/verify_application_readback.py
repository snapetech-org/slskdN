#!/usr/bin/env python3
import collections,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
HEAD="311127db7f4d5097dfd1dde5eaa2150f82f48f30";TREE="23210cd313efd929cca9ceda0fd78da19e5ed50d"
LOCALES=("ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant")
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def j(n):return json.loads((ROOT/n).read_text(encoding="utf-8"))
def jl(n):return [json.loads(x) for x in (ROOT/n).read_text(encoding="utf-8").splitlines() if x.strip()]
def checks(s,t):
 p=sorted(re.findall(r"\{[^{}]+\}",s))==sorted(re.findall(r"\{[^{}]+\}",t))
 g=sorted(re.findall(r"</?[A-Za-z][^>]*>",s))==sorted(re.findall(r"</?[A-Za-z][^>]*>",t))
 n=re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)==re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",t)
 q=set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])",s))
 for x in ("Wishlist","Soulseek","Discogs","Pod","Prometheus","Lidarr","ReplayGain","SongID","WebSocket","VBR"):
  if re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",s):q.add(x)
 return {"placeholders":p,"markup":g,"numbers":n,"protectedLiterals":all(x in t for x in q)}
def verify_sums():
 p=ROOT/"SHA256SUMS.txt";rows={}
 for line in p.read_text(encoding="utf-8").splitlines():
  h,n=line.split("  ",1);rows[n]=h
 actual=sorted(x for x in ROOT.rglob("*") if x.is_file() and x.name!="SHA256SUMS.txt")
 assert rows and set(rows)=={x.relative_to(ROOT).as_posix() for x in actual}
 assert all(sha((ROOT/n).read_bytes())==h for n,h in rows.items())
 return len(rows)
def main():
 nfiles=verify_sums();plan=j("application-plan.json")
 assert plan["window"]=="W72" and plan["headBeforeApply"]==HEAD and plan["treeBeforeApply"]==TREE
 assert len(plan["targetRows"])==31 and len(plan["filesChanged"])==10 and plan["workflowFilesChanged"]==0
 cats={x["locale"]:x for x in plan["catalogFiles"]}
 assert len(cats)==10
 before={};after={}
 for loc in cats:
  a=(ROOT/"preimage"/"locales"/(loc+".json")).read_bytes();b=(ROOT/"postimage"/"locales"/(loc+".json")).read_bytes()
  assert sha(a)==cats[loc]["preimageSha256"] and blob(a)==cats[loc]["preimageGitBlob"]
  assert sha(b)==cats[loc]["postimageSha256"] and blob(b)==cats[loc]["postimageGitBlob"]
  da=json.loads(a);db=json.loads(b);assert list(da)==list(db) and len(da)==6176
  before[loc]=da;after[loc]=db
 byloc=collections.defaultdict(list);keys=set()
 for r in plan["targetRows"]:
  k=(r["continuationRank"],r["locale"],r["sourceId"])
  assert r["sourceId"]=="src_"+r["sourceSha256"][:16] and sha(r["source"].encode())==r["sourceSha256"]
  assert r["locale"] in cats and r["catalogPath"]==cats[r["locale"]]["catalogPath"]
  assert r["preimageCatalogSha256"]==cats[r["locale"]]["preimageSha256"] and r["postimageCatalogSha256"]==cats[r["locale"]]["postimageSha256"]
  assert before[r["locale"]].get(r["catalogKey"])==r["currentTarget"]
  assert sha(r["currentTarget"].encode())==r["currentTargetSha256"]
  assert after[r["locale"]].get(r["catalogKey"])==r["proposedTarget"]
  assert sha(r["proposedTarget"].encode())==r["proposedTargetSha256"]
  assert r["currentTarget"]!=r["proposedTarget"] and all(checks(r["source"],r["proposedTarget"]).values())
  byloc[r["locale"]].append(r["catalogKey"]);keys.add(k)
 assert len(keys)==31
 for loc in cats:
  diff={k for k in before[loc] if before[loc][k]!=after[loc][k]}
  assert diff==set(byloc[loc]),"unexpected catalog key changes in "+loc
 readback=jl("application-readback.jsonl")
 assert len(readback)==31 and len({(r["continuationRank"],r["locale"],r["sourceId"]) for r in readback})==31
 expected={(r["continuationRank"],r["locale"],r["sourceId"]):r for r in plan["targetRows"]}
 for r in readback:
  p=expected[r["continuationRank"],r["locale"],r["sourceId"]]
  assert r["catalogKey"]==p["catalogKey"] and r["preimageTarget"]==p["currentTarget"] and r["preimageTargetSha256"]==p["currentTargetSha256"]
  assert r["expectedTarget"]==p["proposedTarget"] and r["expectedTargetSha256"]==p["proposedTargetSha256"]
  assert r["readbackTarget"]==p["proposedTarget"] and r["readbackTargetSha256"]==p["proposedTargetSha256"] and r["matches"] is True
  assert r["preimageCatalogSha256"]==p["preimageCatalogSha256"] and r["postimageCatalogSha256"]==p["postimageCatalogSha256"]
 holds=jl("held-cells-hash-only.jsonl");prior=jl("prior-held-cell-reattestation-hash-only.jsonl");ids=jl("prior-selected-id-exclusions-hash-only.jsonl")
 assert len(holds)==108 and len({(x["sourceId"],x["locale"]) for x in holds})==108
 assert all(x["recommendation"]=="hold" and x["callerCount"]==0 and x["sourceTextIncluded"] is False and x["currentTargetTextIncluded"] is False and x["recommendedTargetTextIncluded"] is False for x in holds)
 assert all(not ({"source","currentTarget","recommendedTarget","target"}&set(x)) for x in holds)
 assert len(prior)==152 and len(ids)==1782
 assert all(x["sourceTextIncluded"] is False and x["targetTextIncluded"] is False and "source" not in x and "currentTarget" not in x and "priorTarget" not in x for x in prior)
 assert all(x["sourceTextIncluded"] is False and x["targetTextIncluded"] is False and "source" not in x and "target" not in x for x in ids)
 summary=j("application-summary.json")
 assert summary["targetCells"]==summary["readbackMatches"]==31 and summary["readbackMismatches"]==0
 assert summary["targetLocaleFiles"]==10 and summary["currentWindowCallerlessHoldsHashOnly"]==108
 assert summary["priorHeldCellsHashOnly"]==152 and summary["priorSelectedIdsHashOnly"]==1782 and summary["workflowFilesChanged"]==0
 commit_path=ROOT/"application-commit.json"
 if commit_path.exists():
  cr=j("application-commit.json")
  assert cr["parent"]==HEAD and cr["changedFileCount"]==10 and cr["changedCellCount"]==31 and cr["workflowFilesChanged"]==0
  assert cr["changedFiles"]==plan["filesChanged"] and cr["tree"]
  assert plan["applicationCommit"]==cr["commit"]==summary["applicationCommit"]
 print(json.dumps({"verifier":"PASS","filesHashed":nfiles,"selectedTargets":31,"catalogs":10,"readbackMatches":31,"readbackMismatches":0,"callerlessHoldsHashOnly":108,"priorHoldsHashOnly":152,"priorIdsHashOnly":1782,"wholeCatalogDiffs":"exactly the 31 selected keys"},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
