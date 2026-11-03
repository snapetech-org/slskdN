#!/usr/bin/env python3
from pathlib import Path
import collections,hashlib,json,re,subprocess,sys
OUT=Path(__file__).resolve().parent
M=json.loads((OUT/"manifest.json").read_text(encoding="utf-8"))
I=Path(M["candidateFreeInputPath"])
def sha(b): return hashlib.sha256(b).hexdigest()
def st(s): return sha(s.encode("utf-8"))
def jl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def ph(s): return sorted(set(re.findall(r"\{[^{}\r\n]+\}",s)))
def tags(s): return sorted(re.findall(r"</?[A-Za-z][^<>]*>",s))
def nums(s): return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)
def prot(s):
    found=set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])",s))
    for value in ("Wishlist","Soulseek","Discogs","Pod"):
        if re.search(r"(?<![A-Za-z0-9])"+re.escape(value)+r"(?![A-Za-z0-9])",s): found.add(value)
    return sorted(found)
def verify_sums():
    p=OUT/"SHA256SUMS.txt"
    listed={}
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        digest,name=line.split(None,1); name=name.strip().lstrip("*")
        assert name not in listed
        listed[name]=digest
    expected={p.name for p in OUT.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt"}
    assert set(listed)==expected,(set(listed)-expected,expected-set(listed))
    for name,digest in listed.items(): assert sha((OUT/name).read_bytes())==digest,(name,"checksum")
    return sha(p.read_bytes())
assert M["candidateFreeInputOnly"] is True and M["primaryPacketOpened"] is False
assert (M["sourceCount"],M["localeCount"],M["cellCount"])==(25,12,300)
assert M["continuationRankRange"]==[528,552]
assert sha((I/"manifest.json").read_bytes())==M["candidateFreeInputManifestSha256"]
assert sha((I/"PACKET-SHA256SUMS.txt").read_bytes())==M["candidateFreeInputChecksumListSha256"]
subprocess.run(["python3",str(I/"verify_input.py")],cwd=I,check=True,capture_output=True,text=True)
cells=jl(I/"source-current-cells.jsonl")
contexts={r["continuationRank"]:r for r in jl(I/"caller-contexts.jsonl")}
assert len(cells)==300 and len(contexts)==25
source_cells={(r["continuationRank"],r["locale"]):r for r in cells}
assert len(source_cells)==300
ledger=jl(OUT/"sealed-blind-review-ledger.jsonl")
keys=[(r["continuationRank"],r["locale"]) for r in ledger]
assert len(ledger)==300 and len(set(keys))==300 and set(keys)==set(source_cells)
counts=collections.Counter()
for r in ledger:
    k=(r["continuationRank"],r["locale"]); s=source_cells[k]; c=contexts[r["continuationRank"]]
    assert (r["head"],r["tree"])==(M["head"],M["tree"])
    assert (r["sourceId"],r["source"],r["sourceSha256"],r["locale"])==(s["sourceId"],s["source"],s["sourceSha256"],s["locale"])
    assert (r["currentTarget"],r["currentTargetSha256"])==(s["currentTarget"],s["currentTargetSha256"])
    assert r["callerCount"]==c["productionCallerCount"]
    assert r["callerReferences"]==[{"path":x["path"],"line":x["line"],"lineText":x["lineText"],"context":x["context"]} for x in c["callers"]]
    assert r["reviewRole"]=="independent-blind" and "candidate-free" in r["reviewBasis"]
    assert r["disposition"] in {"accept-current","correction","refinement","hold"}
    counts[r["disposition"]]+=1
    if r["disposition"]=="hold":
        assert r["translation"] is None and r["translationSha256"] is None and r["callerCount"]==0
        target=s["currentTarget"]
    else:
        assert r["translation"] and r["translation"].strip()
        assert r["translationSha256"]==st(r["translation"])
        if r["disposition"]=="accept-current": assert r["translation"]==s["currentTarget"]
        if r["disposition"] in {"correction","refinement"}: assert r["translation"]!=s["currentTarget"]
        target=r["translation"]
    source=s["source"]
    source_ph=ph(source); target_ph=ph(target)
    source_tags=tags(source); target_tags=tags(target)
    source_nums=nums(source); target_nums=nums(target)
    source_prot=s["sourceProtectedLiterals"]; target_prot=prot(target)
    missing=[x for x in source_prot if x not in target_prot]
    assert source_ph==target_ph and r["placeholderChecks"]=={"sourcePlaceholders":source_ph,"translationPlaceholders":target_ph,"match":True,"missing":[],"unexpected":[]}
    assert source_tags==target_tags and r["markupChecks"]=={"sourceTags":source_tags,"translationTags":target_tags,"match":True}
    assert source_nums==target_nums and r["numericTokenChecks"]=={"sourceTokens":source_nums,"translationTokens":target_nums,"match":True}
    assert prot(source)==source_prot and not missing
    assert r["protectedLiteralChecks"]=={"sourceLiterals":source_prot,"translationLiterals":target_prot,"missing":[],"translationContainsAll":True}
    current=s["currentTarget"]
    assert r["currentTargetTokenStatus"]=={
      "placeholdersMatch":ph(source)==ph(current),
      "markupMatch":tags(source)==tags(current),
      "numericMatch":nums(source)==nums(current),
      "missingProtectedLiterals":[x for x in source_prot if x not in prot(current)]
    }
assert counts["hold"]==24 and sum(counts.values())==300
assert all(r["disposition"]=="hold" for r in ledger if r["continuationRank"] in {533,541})
assert all(r["disposition"]!="hold" for r in ledger if r["continuationRank"] not in {533,541})
assert counts==collections.Counter(json.loads((OUT/"summary.json").read_text())["dispositionCounts"])
verification=json.loads((OUT/"verification.json").read_text())
assert verification["result"]=="PASS" and verification["cells"]==300 and verification["head"]==M["head"]
sumsha=verify_sums()
print(json.dumps({"result":"PASS","mode":"independent-blind-review","head":M["head"],"tree":M["tree"],"cells":300,"dispositionCounts":dict(counts),"callerlessHolds":24,"missingProtectedLiterals":0,"placeholderMismatches":0,"markupMismatches":0,"numericMismatches":0,"inputVerifier":"PASS","outputChecksums":"PASS","outputChecksumListSha256":sumsha},ensure_ascii=False,indent=2))
