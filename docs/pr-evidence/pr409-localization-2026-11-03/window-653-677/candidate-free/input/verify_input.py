#!/usr/bin/env python3
import hashlib, json, re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED_HEAD="d0317d8258a31d05b7f163921c2e39f93deabfca"
EXPECTED_TREE="01475aeffa17f6151c4bf161890662167c959bb0"
EXPECTED_ORDER="3ca04c40ebfed00b93fcd143109fc9d85da941cec30b6cb93f52e431498df6a7"
LOCALES=("ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant")

def sha(raw): return hashlib.sha256(raw).hexdigest()
def canon(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
def jl(name): return [json.loads(x) for x in (ROOT/name).read_text(encoding="utf-8").splitlines() if x.strip()]
def j(name): return json.loads((ROOT/name).read_text(encoding="utf-8"))
def ph(s): return sorted(re.findall(r"\{[^{}]+\}",s))
def tags(s): return sorted(re.findall(r"</?[A-Za-z][^>]*>",s))
def nums(s): return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)
def prot(s):
    found=set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])",s))
    for x in ("Wishlist","Soulseek","Discogs","Pod"):
        if re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",s): found.add(x)
    return sorted(found)

def main():
    checked={}
    for line in (ROOT/"PACKET-SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest,name=line.split("  ",1)
        checked[name]=sha((ROOT/name).read_bytes())==digest
    assert checked and all(checked.values()),"packet checksum failure"
    manifest=j("manifest.json")
    assert manifest["head"]==EXPECTED_HEAD and manifest["tree"]==EXPECTED_TREE
    assert manifest["candidateFree"] is True and manifest["proposedTargetsIncluded"] is False
    assert manifest["reviewDecisionsIncluded"] is False
    files={x["path"]:x for x in manifest["files"]}
    for name,info in files.items():
        raw=(ROOT/name).read_bytes()
        assert len(raw)==info["bytes"] and sha(raw)==info["sha256"],f"manifest file pin mismatch: {name}"
    inventory=jl("source-inventory-pinned.jsonl")
    assert len(inventory)==6176 and sha((ROOT/"source-inventory-pinned.jsonl").read_bytes())==manifest["sourceInventorySha256"]
    selected=jl("source-inventory-selection.jsonl")
    assert len(selected)==25 and {r["continuationRank"] for r in selected}==set(range(653,678))
    byid={r["sourceId"]:r for r in inventory}
    assert len(byid)==len(inventory)
    for r in selected:
        assert byid[r["sourceId"]]["sourceSha256"]==r["sourceSha256"]
        assert sha(r["source"].encode("utf-8"))==r["sourceSha256"]
        assert r["sourceId"]=="src_"+r["sourceSha256"][:16]
    excluded=jl("prior-selected-id-exclusions.jsonl")
    ids={r["sourceId"] for r in excluded}
    assert len(excluded)==1757 and len(ids)==1757
    selected_ids={r["sourceId"] for r in selected}
    assert not ids & selected_ids
    expected={r["sourceId"] for r in inventory if r["excluded"] or r["inW49"] or
        (r["localeCoverage"]==12 and r["continuationRank"] is not None and r["continuationRank"]<=652)}
    assert expected==ids
    boundaries=jl("selection-boundary.jsonl")
    assert len(boundaries)==27
    assert boundaries[0]["continuationRank"]==652 and boundaries[0]["boundaryRole"]=="previous-window-final"
    assert boundaries[-1]["continuationRank"]==678 and boundaries[-1]["boundaryRole"]=="next-unselected"
    assert [r["continuationRank"] for r in boundaries[1:-1]]==list(range(653,678))
    current=jl("source-current-cells.jsonl")
    assert len(current)==300
    assert len({(r["sourceId"],r["locale"]) for r in current})==300
    assert all(sum(r["locale"]==loc for r in current)==25 for loc in LOCALES)
    callers={r["sourceId"]:r for r in jl("caller-contexts.jsonl")}
    assert set(callers)==selected_ids
    mismatches=Counter()
    for r in current:
        assert r["sourceId"] in selected_ids and r["locale"] in LOCALES
        assert sha(r["source"].encode("utf-8"))==r["sourceSha256"]
        assert sha(r["currentTarget"].encode("utf-8"))==r["currentTargetSha256"]
        assert r["catalogKey"]==r["source"]
        callrow=callers[r["sourceId"]]
        assert r["callerContextSha256"]==sha(canon([c["context"] for c in callrow["callers"]]))
        assert len(r["callerRefs"])==callrow["productionCallerCount"]
        assert r["placeholderEvidence"]["sourceTokens"]==ph(r["source"])
        assert r["placeholderEvidence"]["currentTokens"]==ph(r["currentTarget"])
        assert r["placeholderEvidence"]["matches"]==(ph(r["source"])==ph(r["currentTarget"]))
        assert r["markupEvidence"]["sourceTags"]==tags(r["source"])
        assert r["markupEvidence"]["currentTags"]==tags(r["currentTarget"])
        assert r["markupEvidence"]["matches"]==(tags(r["source"])==tags(r["currentTarget"]))
        assert r["sourceNumericTokens"]==nums(r["source"]) and r["currentNumericTokens"]==nums(r["currentTarget"])
        assert r["numericTokensPreserved"]==(nums(r["source"])==nums(r["currentTarget"]))
        missing=[x for x in prot(r["source"]) if x not in r["currentTarget"]]
        assert r["sourceProtectedLiterals"]==prot(r["source"])
        assert r["currentProtectedLiterals"]==prot(r["currentTarget"])
        assert r["missingProtectedLiterals"]==missing
        assert r["protectedLiteralEvidence"]["matches"]==(not bool(missing))
        assert r["containsCandidate"] is False and r["verdict"] is None
        mismatches["placeholder"]+=not r["placeholderEvidence"]["matches"]
        mismatches["markup"]+=not r["markupEvidence"]["matches"]
        mismatches["numeric"]+=not r["numericTokensPreserved"]
        mismatches["protectedLiteral"]+=not r["protectedLiteralEvidence"]["matches"]
    summary=j("baseline-token-mismatch-summary.json")
    assert summary["cellCount"]==300 and summary["mismatches"]==dict(mismatches)
    catalog=jl("catalog-structure.jsonl")
    assert len(catalog)==12 and {r["locale"] for r in catalog}==set(LOCALES)
    assert all(r["entryCount"]==6176 and r["nonemptyValueCount"]==6176 and r["orderedKeySha256"]==EXPECTED_ORDER for r in catalog)
    holds=jl("prior-held-cell-reattestation.jsonl")
    assert len(holds)==140 and len({(r["sourceId"],r["locale"]) for r in holds})==140
    assert all(r["priorDisposition"]=="hold" for r in holds)
    hold_summary=j("prior-held-cell-reattestation-summary.json")
    assert hold_summary["priorHeldCellsReattested"]==140
    assert hold_summary["allTargetHashesMatchPrior"]==all(r["matchesPriorCurrentValue"] for r in holds)
    assert hold_summary["allCurrentCallerAndCatalogEvidenceRepinned"] is True
    att=j("head-tree-attestation.json")
    assert att["headRefOid"]==EXPECTED_HEAD and att["branchRefOid"]==EXPECTED_HEAD and att["pullRefOid"]==EXPECTED_HEAD and att["treeOid"]==EXPECTED_TREE
    print(json.dumps({"verifier":"PASS","filesHashed":len(checked),"sourceInventoryRows":len(inventory),
        "selectedSources":len(selected),"currentCells":len(current),"priorExcludedIds":len(excluded),
        "priorHolds":len(holds),"priorHoldTargetMatches":sum(r["matchesPriorCurrentValue"] for r in holds),
        "catalogs":len(catalog),"callerContexts":len(callers),"tokenMismatches":dict(mismatches)},ensure_ascii=False,indent=2))

if __name__=="__main__": main()

