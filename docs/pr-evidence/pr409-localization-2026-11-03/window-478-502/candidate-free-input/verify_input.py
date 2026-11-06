#!/usr/bin/env python3
import hashlib,json,subprocess
from pathlib import Path
from collections import Counter
I=Path(__file__).resolve().parent
def sha(b): return hashlib.sha256(b).hexdigest()
def jl(p): return [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s.strip()]
subprocess.check_call(["sha256sum","-c","PACKET-SHA256SUMS.txt"],cwd=I)
m=json.loads((I/"manifest.json").read_text(encoding="utf-8"))
assert m["candidateFree"] is True
assert m["head"]=="3cc9db334cfb1693dd6bd93bb83cfeba65930adb"
assert m["tree"]=="9d40e239e7e717a81bd176d143d1ce067fe026a1"
assert m["sourceCount"]==25 and m["localeCount"]==12 and m["cellCount"]==300
for f in m["files"]:
    raw=(I/f["path"]).read_bytes()
    assert len(raw)==f["bytes"] and sha(raw)==f["sha256"],f["path"]
cells=jl(I/"source-current-cells.jsonl")
sources=jl(I/"source-inventory-selection.jsonl")
contexts=jl(I/"caller-contexts.jsonl")
catalogs=jl(I/"catalog-structure.jsonl")
prior=jl(I/"prior-held-cell-reattestation.jsonl")
ids=jl(I/"prior-selected-id-exclusions.jsonl")
boundary=jl(I/"selection-boundary.jsonl")
assert len(cells)==300 and len(sources)==25 and len(contexts)==25
assert len(catalogs)==12 and len(prior)==86 and len(ids)==1582 and len(boundary)==27
assert [r["continuationRank"] for r in sources]==list(range(478,503))
assert [r["remainingQueueRank"] for r in sources]==list(range(378,403))
assert len({r["sourceId"] for r in sources})==25
assert not ({r["sourceId"] for r in sources}&{r["sourceId"] for r in ids})
origins=Counter(r["selectionOrigin"] for r in ids)
assert origins==Counter({"preexisting W1-W45 evidence-set exclusion":1205,"W49":25,"prior continuation window":352}),origins
assert m["priorSelectedIdsExcluded"]==377 and m["preexistingW1W45ExcludedRows"]==1205 and m["allUnavailableIdsBeforeW64"]==1582
assert [r["boundaryRole"] for r in boundary].count("previous-window-final")==1
assert [r["boundaryRole"] for r in boundary].count("next-unselected")==1
assert [r["boundaryRole"] for r in boundary].count("selected")==25
ordered="3ca04c40ebfed00b93fcd143109fc9d85da941cec30b6cb93f52e431498df6a7"
assert all(r["entryCount"]==6176 and r["nonemptyValueCount"]==6176 and r["orderedKeySha256"]==ordered for r in catalogs)
assert len({r["catalogPath"] for r in catalogs})==12
cell_index={(r["continuationRank"],r["locale"]):r for r in cells}
assert len(cell_index)==300
for c in cells:
    assert c["containsCandidate"] is False and c["verdict"] is None
    assert sha(c["source"].encode())==c["sourceSha256"]
    assert sha(c["currentTarget"].encode())==c["currentTargetSha256"]
    assert c["placeholderEvidence"]["matches"]
    assert c["markupEvidence"]["matches"]
    assert c["sourceNumericTokens"]==c["currentNumericTokens"]
    assert c["protectedLiteralEvidence"]["matches"] == all(x in c["currentTarget"] for x in c["sourceProtectedLiterals"])
assert sum(not r["protectedLiteralEvidence"]["matches"] for r in cells)==23
counts=Counter((r["priorWindow"],r["continuationRank"]) for r in prior)
expected={("W57",319):12,("W59",356):12,("W59",366):12,("W61",409):12,
          ("W62",438):12,("W62",452):12,("W63",459):1,("W63",475):1,("W63",476):12}
assert dict(counts)==expected,counts
assert all(r["priorDisposition"]=="hold" and r["matchesPriorCurrentValue"] and r["status"]=="reattested-unchanged" for r in prior)
assert all(sha(r["currentTarget"].encode())==r["currentTargetSha256"]==r["priorTargetSha256"] for r in prior)
assert m["callerlessSelectedRanks"]==[486]
assert next(r for r in contexts if r["continuationRank"]==486)["productionCallerCount"]==0
att=json.loads((I/"head-tree-attestation.json").read_text())
assert att["headRefOid"]==m["head"] and att["treeOid"]==m["tree"]
assert att["branchRefOid"]==m["head"] and att["pullRefOid"]==m["head"] and att["checkoutClean"] is True
w63=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w63-ranks453-477-primary-20261103/input")
assert sha((w63/"manifest.json").read_bytes())==m["W63CandidateFreeManifestJsonSha256"]
assert sha((w63/"PACKET-SHA256SUMS.txt").read_bytes())==m["W63CandidateFreeChecksumListSha256"]
print(json.dumps({"pass":True,"head":m["head"],"tree":m["tree"],"sourceCount":len(sources),"cellCount":len(cells),
 "priorSelectedIdsExcluded":m["priorSelectedIdsExcluded"],"priorHeldCellsReattested":len(prior),"baselineProtectedLiteralMismatches":23,
 "placeholderMarkupNumericMismatches":0},indent=2))

