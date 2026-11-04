#!/usr/bin/env python3
import hashlib, json, re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent
HEAD="311127db7f4d5097dfd1dde5eaa2150f82f48f30"
TREE="23210cd313efd929cca9ceda0fd78da19e5ed50d"
LOCALES=("ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant")
ORDER="3ca04c40ebfed00b93fcd143109fc9d85da941cec30b6cb93f52e431498df6a7"
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def j(n):return json.loads((ROOT/n).read_text(encoding="utf-8"))
def jl(n):return [json.loads(x) for x in (ROOT/n).read_text(encoding="utf-8").splitlines() if x.strip()]
def ph(s):return sorted(re.findall(r"\{[^{}]+\}",s))
def tags(s):return sorted(re.findall(r"</?[A-Za-z][^>]*>",s))
def nums(s):return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)
def prot(s):
 r=set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])",s))
 for x in ("Wishlist","Soulseek","Discogs","Pod","Prometheus","Lidarr","ReplayGain","SongID","WebSocket","VBR"):
  if re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",s):r.add(x)
 return sorted(r)
def verify():
 sums={}
 for line in (ROOT/"PACKET-SHA256SUMS.txt").read_text().splitlines():
  h,n=line.split("  ",1);sums[n]=h
 assert sums and all(sha((ROOT/n).read_bytes())==h for n,h in sums.items()),"packet checksum mismatch"
 m=j("manifest.json")
 assert m["candidateFree"] is True and m["head"]==HEAD and m["tree"]==TREE and m["proposedTargetsIncluded"] is False and m["reviewDecisionsIncluded"] is False
 listed={x["path"]:x for x in m["files"]}
 assert set(listed)==set(sums)-{"manifest.json","PACKET-SHA256SUMS.txt"}
 for n,x in listed.items():
  raw=(ROOT/n).read_bytes();assert len(raw)==x["bytes"] and sha(raw)==x["sha256"],"manifest pin mismatch "+n
 inv=jl("source-inventory-pinned.jsonl")
 assert len(inv)==6176 and sha((ROOT/"source-inventory-pinned.jsonl").read_bytes())==m["sourceInventorySha256"]=="17cb8a747939d4973733016b95f29284e191d5444910051e42fb153cf4f94225"
 byid={x["sourceId"]:x for x in inv};assert len(byid)==6176
 sel=jl("source-inventory-selection.jsonl")
 assert len(sel)==25 and {x["continuationRank"] for x in sel}==set(range(678,703))
 for x in sel:
  assert byid[x["sourceId"]]["sourceSha256"]==x["sourceSha256"] and x["sourceId"]=="src_"+x["sourceSha256"][:16] and sha(x["source"].encode())==x["sourceSha256"]
 prior=jl("prior-selected-id-exclusions-hash-only.jsonl")
 assert len(prior)==1782 and len({x["sourceId"] for x in prior})==1782
 expected={x["sourceId"] for x in inv if x["excluded"] or x["inW49"] or (x["localeCoverage"]==12 and x["continuationRank"] is not None and x["continuationRank"]<=677)}
 assert {x["sourceId"] for x in prior}==expected
 assert all(x["sourceTextIncluded"] is False and x["targetTextIncluded"] is False and "source" not in x and "target" not in x for x in prior)
 for x in prior:
  row=byid[x["sourceId"]];assert x["sourceSha256"]==row["sourceSha256"] and x["sourceIdSha256"]==sha(x["sourceId"].encode())
 bounds=jl("selection-boundary.jsonl")
 assert len(bounds)==27 and bounds[0]["continuationRank"]==677 and bounds[0]["boundaryRole"]=="previous-window-final"
 assert bounds[-1]["continuationRank"]==703 and bounds[-1]["boundaryRole"]=="next-unselected"
 assert [x["continuationRank"] for x in bounds[1:-1]]==list(range(678,703))
 cats=jl("catalog-structure.jsonl");cat={x["locale"]:x for x in cats}
 assert len(cat)==12 and set(cat)==set(LOCALES)
 assert all(x["entryCount"]==6176 and x["nonemptyValueCount"]==6176 and x["orderedKeySha256"]==ORDER for x in cats)
 callers=jl("caller-contexts.jsonl");callmap={x["sourceId"]:x for x in callers}
 assert len(callmap)==25 and set(callmap)=={x["sourceId"] for x in sel}
 for x in callers:
  assert x["sourceSha256"]==sha(x["source"].encode()) and x["sourceId"]=="src_"+x["sourceSha256"][:16]
  for c in x["callers"]:
   assert c["contextSha256"]==sha(canon(c["context"]))
   line=next((z["text"] for z in c["context"] if z["line"]==c["line"]),None)
   assert line==c["lineText"] and c["lineSha256"]==sha(line.encode())
   assert c["gitBlob"] and c["fileSha256"] and c["fileBytes"]>0
  assert x["productionCallerCount"]==len(x["callers"])
  assert x["boundedScan"] and isinstance(x["callers"],list)
 cells=jl("source-current-cells.jsonl")
 assert len(cells)==300 and len({(x["sourceId"],x["locale"]) for x in cells})==300
 mismatch=Counter()
 for c in cells:
  assert c["continuationRank"] in range(678,703) and c["locale"] in LOCALES
  assert sha(c["source"].encode())==c["sourceSha256"] and c["sourceId"]=="src_"+c["sourceSha256"][:16]
  assert sha(c["currentTarget"].encode())==c["currentTargetSha256"] and c["catalogKey"]==c["source"]
  assert c["catalogFileSha256"]==cat[c["locale"]]["sha256"] and c["catalogGitBlob"]==cat[c["locale"]]["gitBlob"]
  caller=callmap[c["sourceId"]]
  assert c["callerContextSha256"]==sha(canon([x["context"] for x in caller["callers"]]))
  ref_keys=("path","line","lineSha256","contextSha256","fileSha256","gitBlob")
  assert c["callerRefs"]==[{k:r[k] for k in ref_keys} for r in caller["callers"]]
  assert c["containsCandidate"] is False and c["verdict"] is None and "proposedTarget" not in c
  assert c["placeholderEvidence"]["sourceTokens"]==ph(c["source"])
  assert c["placeholderEvidence"]["currentTokens"]==ph(c["currentTarget"])
  assert c["placeholderEvidence"]["matches"]==(ph(c["source"])==ph(c["currentTarget"]))
  assert c["markupEvidence"]["sourceTags"]==tags(c["source"]) and c["markupEvidence"]["currentTags"]==tags(c["currentTarget"])
  assert c["markupEvidence"]["matches"]==(tags(c["source"])==tags(c["currentTarget"]))
  assert c["sourceNumericTokens"]==nums(c["source"]) and c["currentNumericTokens"]==nums(c["currentTarget"])
  assert c["numericTokensPreserved"]==(nums(c["source"])==nums(c["currentTarget"]))
  missing=[x for x in prot(c["source"]) if x not in c["currentTarget"]]
  assert c["sourceProtectedLiterals"]==prot(c["source"]) and c["currentProtectedLiterals"]==prot(c["currentTarget"])
  assert c["missingProtectedLiterals"]==missing and c["protectedLiteralEvidence"]["matches"]==(not bool(missing))
  mismatch["placeholder"]+=not c["placeholderEvidence"]["matches"];mismatch["markup"]+=not c["markupEvidence"]["matches"]
  mismatch["numeric"]+=not c["numericTokensPreserved"];mismatch["protectedLiteral"]+=not c["protectedLiteralEvidence"]["matches"]
 assert m["baselineTokenMismatchSummary"]==dict(mismatch)==j("baseline-token-mismatch-summary.json")["mismatches"]
 holds=jl("prior-held-cell-reattestation-hash-only.jsonl")
 assert len(holds)==152 and len({(x["sourceId"],x["locale"]) for x in holds})==152
 assert all(x["priorDisposition"]=="hold" and x["sourceTextIncluded"] is False and x["targetTextIncluded"] is False for x in holds)
 forbidden={"source","priorTarget","currentTarget","target"}
 for h in holds:
  assert not (forbidden & set(h)) and h["sourceId"]=="src_"+h["sourceSha256"][:16] and h["sourceIdSha256"]==sha(h["sourceId"].encode())
  assert h["matchesPriorCurrentValue"]==(h["priorTargetSha256"]==h["currentTargetSha256"])
  assert h["currentCatalogFileSha256"]==cat[h["locale"]]["sha256"] and h["currentCatalogGitBlob"]==cat[h["locale"]]["gitBlob"]
  assert h["currentCallerCount"]==len(h["currentCallerRefs"]) and h["currentCallerContextSha256"]
 hs=j("prior-held-cell-reattestation-summary.json")
 assert hs["priorHeldCellsReattested"]==152 and hs["allTargetHashesMatchPrior"]==all(x["matchesPriorCurrentValue"] for x in holds)
 assert hs["allCurrentCallerAndCatalogEvidenceRepinned"] is True
 a=j("head-tree-attestation.json")
 assert a["headRefOid"]==a["branchRefOid"]==a["pullRefOid"]==HEAD and a["treeOid"]==TREE
 assert a["deploymentsForHeadBefore"]==a["deploymentsForHeadAfter"]==0
 assert m["liveBefore"]["headRefOid"]==m["liveAfter"]["headRefOid"]==HEAD and m["liveBefore"]["treeOid"]==m["liveAfter"]["treeOid"]==TREE
 assert m["liveBefore"]["deploymentsForHead"]==m["liveAfter"]["deploymentsForHead"]==0
 print(json.dumps({"verifier":"PASS","filesHashed":len(sums),"inventoryRows":len(inv),"selectedSources":len(sel),"cells":len(cells),"priorIdsHashOnly":len(prior),"priorHoldsHashOnly":len(holds),"priorHoldHashesMatching":sum(x["matchesPriorCurrentValue"] for x in holds),"catalogs":len(cats),"callerContexts":len(callers),"baselineTokenMismatches":dict(mismatch),"head":HEAD,"tree":TREE},ensure_ascii=False,indent=2))
if __name__=="__main__":verify()
