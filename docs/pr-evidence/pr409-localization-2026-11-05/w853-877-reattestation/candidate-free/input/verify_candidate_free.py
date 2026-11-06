#!/usr/bin/env python3
"""Portable integrity and scope verifier for the sealed candidate-free packet."""
import hashlib, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
TEXT_KEYS={"source","sourceText","target","currentTarget","proposedTarget","proposedTargetText","candidateTarget","reviewTarget","rationale","reason"}
def need(ok,msg):
    if not ok: raise SystemExit("FAIL: "+msg)
def sha(b): return hashlib.sha256(b).hexdigest()
def readj(name): return json.loads((ROOT/name).read_text(encoding="utf-8"))
def readjl(name): return [json.loads(x) for x in (ROOT/name).read_text(encoding="utf-8").splitlines() if x.strip()]
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
def no_text(o):
    if isinstance(o,dict): return not (set(o)&TEXT_KEYS) and all(no_text(v) for v in o.values())
    if isinstance(o,list): return all(no_text(v) for v in o)
    return True

def main():
    checks={}
    sums={}
    for line in (ROOT/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        h,name=line.split("  ",1); need(name not in sums,"duplicate checksum path"); sums[name]=h
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and p.name!="SHA256SUMS.txt"}
    need(actual==set(sums),"checksum inventory differs from packet files")
    for name,h in sums.items(): need(sha((ROOT/name).read_bytes())==h,"checksum mismatch: "+name)
    checks["sha256_inventory"]="PASS"
    m=readj("manifest.json"); s=readj("summary.json")
    need(m["head"]=="cc600880606f374cebe3082789fa50f246ff614f" and m["tree"]=="440b9842d914a391f77cbb03737261b8798cc6e3","exact head/tree pin")
    need((m["baseSha"],m["mainSha"])==("f25d263a2a7cdb2c8f76c40c346cb10f749a9356","bc6251ff4ea5a7e59f2d86e2400c90520601f46e"),"base/main pins")
    mf={x["path"]:(x["sha256"],x["bytes"]) for x in m["files"]}
    need(set(mf)==actual-{"manifest.json"},"manifest file inventory")
    for name,(h,n) in mf.items(): need(sha((ROOT/name).read_bytes())==h and (ROOT/name).stat().st_size==n,"manifest file pin: "+name)
    need(s["result"]=="PASS" and (s["exactHead"],s["exactTree"])==(m["head"],m["tree"]),"summary identity")
    checks["manifest_and_summary"]="PASS"
    before,after=readj("live-before.json"),readj("live-after.json")
    for live in (before,after):
        need((live["state"],live["draft"],live["merged"])==("open",True,False),"live PR state")
        need((live["headSha"],live["headTree"],live["headRef"])==(m["head"],m["tree"],m["branch"]),"live PR head")
        need((live["baseRef"],live["baseSha"],live["baseTree"])==("main",m["baseSha"],m["baseTree"]),"live PR base")
        need((live["mainApiSha"],live["mainTree"])==(m["mainSha"],m["mainTree"]),"live main")
        need(live["branchApiSha"]==live["remoteBranchSha"]==live["pullRefSha"]==m["head"],"live branch/pull refs")
        need(live["remoteMainSha"]==m["mainSha"],"live remote main")
    need(before["remoteRefs"]==after["remoteRefs"],"live refs moved during packet build")
    checks["live_entry_exit_snapshots"]="PASS"
    selected=readjl("source-inventory-selection.jsonl")
    rows=readjl("selected-sources.jsonl")
    need(len(selected)==len(rows)==25,"selected source count")
    need([r["continuationRank"] for r in selected]==list(range(953,978)),"continuation ranks")
    need([r["remainingQueueRank"] for r in selected]==list(range(853,878)),"queue ranks")
    byid={r["sourceId"]:r for r in rows}; need(len(byid)==25,"selected source IDs unique")
    for r in selected:
        v=byid[r["sourceId"]]; need(v["sourceIdSha256"]==sha(v["sourceId"].encode()),"selected source ID hash")
        need(v["sourceSha256"]==r["sourceSha256"],"selected source hash binding")
        if r["continuationRank"]==966:
            need(v.get("sourceTextIncluded") is False and "source" not in v and v.get("sourceTextOmittedForHashOnlyHold") is True,"held source text leaked")
        else:
            need(v.get("sourceTextIncluded") is True and sha(v["source"].encode())==v["sourceSha256"],"selected source content/hash")
    checks["rank_selection_and_held_source_redaction"]="PASS"
    cells=readjl("source-current-cells.jsonl"); need(len(cells)==300,"25x12 current cells")
    keys={(r["sourceId"],r["locale"]):r for r in cells}; need(len(keys)==300,"duplicate current cell")
    locales=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
    need(set(r["locale"] for r in cells)==set(locales),"locale coverage")
    for (sid,locale),r in keys.items():
        src=byid[sid]; hold=src["continuationRank"]==966
        need(r["sourceSha256"]==src["sourceSha256"] and r["sourceIdSha256"]==sha(sid.encode()),"cell source binding")
        need(r["currentTargetTextIncluded"]==r["sourceTextIncluded"]==(not hold),"cell source/target include flags")
        need(r["tokenChecksPass"] is True and r["decision"] is None and r["containsCandidate"] is False,"candidate-free token/decision status")
        if hold:
            need(not(set(r)&TEXT_KEYS) and r.get("tokenEvidenceTextOmitted") is True,"held source/target text leaked")
        else:
            need(sha(r["source"].encode())==r["sourceSha256"] and sha(r["currentTarget"].encode())==r["currentTargetSha256"],"source/current target hashes")
            need(sha(canon(r["tokenEvidence"]))==r["tokenEvidenceSha256"],"token evidence hash")
    checks["cell_scope_and_redaction"]="PASS"
    callers=readjl("caller-contexts.jsonl"); need(len(callers)==25,"caller source count")
    for r in callers:
        hold=r["continuationRank"]==966
        need(len(r["callerContextSha256"])==64 and all(c in "0123456789abcdef" for c in r["callerContextSha256"]),"caller hash format")
        need(r["productionCallerCount"]>0,"caller reference count")
        if hold:
            need(r["productionCallerCount"]==52 and r["sourceTextIncluded"] is False and r["callerReferenceTextIncluded"] is False and "callers" not in r and no_text(r),"held caller text leaked")
        else:
            need(r["sourceTextIncluded"] is True and r["callerReferenceTextIncluded"] is True and sha(canon(r["callers"]))==r["callerContextSha256"],"caller context hash/content")
    checks["caller_context_redaction"]="PASS"
    inventory=readjl("source-inventory-pinned.jsonl"); runtime=readjl("runtime-file-pins.jsonl")
    need(len(inventory)==6175 and len(runtime)==279,"source inventory/runtime file counts")
    need(all(r["sourceTextIncluded"] is False for r in inventory),"inventory source text leaked")
    checks["catalog_and_runtime_pin_inventory"]="PASS"
    app=readjl("window-application-readback-hash-only.jsonl")
    holds=readjl("window-holds-hash-only.jsonl"); applied=readjl("window-applied-targets-reattestation-hash-only.jsonl")
    need(len(app)==300 and len(holds)==12 and len(applied)==288,"window application counts")
    need({r["continuationRank"] for r in holds}=={966},"hold rank")
    need(all(no_text(r) for r in app+holds+applied),"window readback has text")
    need(all(r["readbackMatchesCurrent"] for r in app),"current readback hash mismatch")
    need(len(readjl("prior-held-cell-reattestation-hash-only.jsonl"))==397 and len(readjl("prior-applied-targets-reattestation-hash-only.jsonl"))==300,"historical W82 state counts")
    need(len(readjl("prior-selected-id-exclusions-hash-only.jsonl"))==2060,"selection exclusions")
    resolutions=readjl("prior-hold-resolution-history-hash-only.jsonl")
    need(len(resolutions)==25 and sum(r["currentSourcePresent"] is True for r in resolutions)==13 and sum(r["currentSourcePresent"] is False for r in resolutions)==12,"historical resolution reconciliation counts")
    need(all(no_text(r) for r in resolutions),"historical resolution text")
    checks["applied_hold_and_historical_state"]="PASS"
    need(not any("proposal" in x.lower() or "review" in x.lower() or "blind" in x.lower() or "primary" in x.lower() or "cross" in x.lower() for x in actual),"proposal/review artifact present")
    need(m["proposedTargetsIncluded"] is False and m["reviewDecisionsIncluded"] is False and m["primaryBlindOrCrossProposalsRead"] is False,"candidate-free provenance")
    checks["candidate_free_boundary"]="PASS"
    print(json.dumps({"result":"PASS","verifier":"portable","checks":checks,"sourceIds":25,"cells":300,"applied":288,"hashOnlyHolds":12,"historicalResolutionTargetsReattested":13,"historicalResolutionSourcesAbsent":12},indent=2))
if __name__=="__main__": main()
