#!/usr/bin/env python3
import hashlib,json,re,subprocess
from pathlib import Path
from collections import Counter
T=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w64-ranks478-502-primary-20261103")
I=T/"input"; P=T/"primary"
def sha(b): return hashlib.sha256(b).hexdigest()
def jl(p): return [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s.strip()]
def toks(s): return sorted(set(re.findall(r"\{[^{}]+\}",s)))
def tags(s): return sorted(re.findall(r"</?[A-Za-z][^>]*>",s))
def nums(s): return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)
subprocess.check_call(["sha256sum","-c","PACKET-SHA256SUMS.txt"],cwd=I,stdout=subprocess.DEVNULL)
subprocess.check_call(["python3",str(I/"verify_input.py")],stdout=subprocess.DEVNULL)
im=json.loads((I/"manifest.json").read_text(encoding="utf-8"))
pm=json.loads((P/"summary.json").read_text(encoding="utf-8"))
cells=jl(I/"source-current-cells.jsonl"); decisions=jl(P/"review-decisions.jsonl")
assert len(cells)==300 and len(decisions)==300
assert im["head"]==pm["head"]=="3cc9db334cfb1693dd6bd93bb83cfeba65930adb"
assert im["tree"]==pm["tree"]=="9d40e239e7e717a81bd176d143d1ce067fe026a1"
assert pm["candidateFreeInputManifestJsonSha256"]==sha((I/"manifest.json").read_bytes())
assert pm["candidateFreeInputChecksumListSha256"]==sha((I/"PACKET-SHA256SUMS.txt").read_bytes())
idx={(r["continuationRank"],r["locale"]):r for r in cells}; assert len(idx)==300
pidx={(r["continuationRank"],r["locale"]):r for r in decisions}; assert len(pidx)==300
seen=set(); counts=Counter(); unresolved_protected=[]
for key,d in pidx.items():
    assert key in idx and key not in seen; seen.add(key); c=idx[key]
    counts[d["disposition"]]+=1
    for field in ("remainingQueueRank","sourceId","source","sourceSha256","locale","catalogKey","catalogPath","catalogFileSha256","catalogGitBlob","currentTarget","currentTargetSha256","callerContextSha256","callerRefs"):
        assert d[field]==c[field],(key,field)
    assert d["selectedTargetSha256"]==sha(d["selectedTarget"].encode())
    assert d["rationale"].strip()
    assert d["candidateFreeInputCellHash"]==sha(json.dumps(c,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode())
    assert d["tokenAudit"]["sourcePlaceholders"]==toks(c["source"])
    assert d["tokenAudit"]["selectedPlaceholders"]==toks(d["selectedTarget"])
    assert d["tokenAudit"]["placeholdersMatch"] is True
    assert d["tokenAudit"]["sourceMarkup"]==tags(c["source"])
    assert d["tokenAudit"]["selectedMarkup"]==tags(d["selectedTarget"])
    assert d["tokenAudit"]["markupMatches"] is True
    assert d["tokenAudit"]["sourceNumericTokens"]==nums(c["source"])
    assert d["tokenAudit"]["selectedNumericTokens"]==nums(d["selectedTarget"])
    assert d["tokenAudit"]["numericTokensMatch"] is True
    assert d["tokenAudit"]["sourceProtectedLiterals"]==c["sourceProtectedLiterals"]
    assert d["tokenAudit"]["selectedProtectedLiterals"]==sorted(set(d["tokenAudit"]["selectedProtectedLiterals"]))
    if d["disposition"]=="accept-current":
        assert d["selectedTarget"]==c["currentTarget"] and d["proposedTarget"]==c["currentTarget"]
    elif d["disposition"]=="correction":
        assert d["selectedTarget"]!=c["currentTarget"] and d["proposedTarget"]==d["selectedTarget"]
    elif d["disposition"]=="hold":
        assert d["continuationRank"]==486 and d["productionCallerCount"]==0
        assert d["selectedTarget"]==c["currentTarget"] and d["proposedTarget"] is None
    else: raise AssertionError(d["disposition"])
    assert d["productionCallerCount"]==(0 if d["continuationRank"]==486 else len(c["callerRefs"]))
    exception=d["tokenAudit"]["localizedStatusLiteralException"]
    if exception:
        assert d["continuationRank"]==501 and d["tokenAudit"]["sourceProtectedLiterals"]==["ACCEPT"]
        assert "interfaceText" in d["tokenAudit"]["localizedStatusExceptionRationale"]
    for literal in c["sourceProtectedLiterals"]:
        if literal=="ACCEPT" and d["continuationRank"]==501:
            continue
        if literal not in d["selectedTarget"]:
            unresolved_protected.append((key,literal))
    if d["continuationRank"]==487:
        assert "Wishlist" in d["selectedTarget"]
assert seen==set(idx)
assert counts==Counter({"correction":74,"accept-current":214,"hold":12}),counts
assert sum(1 for d in decisions if d["continuationRank"]==486 and d["disposition"]=="hold")==12
assert sum(1 for d in decisions if d["continuationRank"]==487 and d["disposition"]=="correction")==12
assert sum(1 for d in decisions if d["continuationRank"]==501 and d["tokenAudit"]["localizedStatusLiteralException"])==12
assert not unresolved_protected,unresolved_protected
assert len(jl(I/"prior-held-cell-reattestation.jsonl"))==86
assert pm["selectedTargetChanges"]==74 and pm["holds"]==12 and pm["postReviewUnresolvedProtectedLiteralMismatches"]==0
assert pm["candidateFreeInputManifestJsonSha256"]==sha((I/"manifest.json").read_bytes())
print(json.dumps({"pass":True,"head":im["head"],"tree":im["tree"],"cells":300,
 "corrections":74,"refinements":0,"acceptCurrent":214,"callerlessHolds":12,
 "priorHeldCellsReattested":86,"unresolvedProtectedLiterals":0},indent=2))

