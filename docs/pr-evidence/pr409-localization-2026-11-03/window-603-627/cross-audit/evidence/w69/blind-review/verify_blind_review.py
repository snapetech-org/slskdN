#!/usr/bin/env python3
"""Portable, offline verifier for the W69 slskdN blind-review packet."""
import argparse, hashlib, json, re, sys
from pathlib import Path

HEAD="9ef252a53d2c14201c736de41efd0531bc00965a"
TREE="becf17f8be3f3251691002dbce487c1e94693e63"
WINDOW="W69-ranks603-627"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
DECISIONS={"accept-current","correction","refinement","hold"}

def sha(b): return hashlib.sha256(b).hexdigest()
def read_jsonl(p): return [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s.strip()]
def fail(s): raise SystemExit("FAIL: "+s)
def ph(s): return sorted(set(re.findall(r"\{[^{}]+\}",s)))
def tags(s): return sorted(re.findall(r"</?[A-Za-z][^>]*>",s))
def nums(s): return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)
def prot(s):
 f=set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])",s))
 for x in ("Wishlist","Soulseek","Discogs","Pod"):
  if re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",s): f.add(x)
 return sorted(f)
def sig(s): return {"placeholders":ph(s),"markup":tags(s),"numeric":nums(s),"protected":prot(s)}
def checksums(folder, name):
 seen=set()
 p=folder/name
 if not p.is_file(): fail("missing checksum list "+str(p))
 for line in p.read_text(encoding="utf-8").splitlines():
  if not line.strip(): continue
  m=re.fullmatch(r"([0-9a-f]{64})  (.+)",line)
  if not m: fail("malformed checksum line: "+line)
  digest,rel=m.groups(); q=Path(rel)
  if q.is_absolute() or ".." in q.parts: fail("unsafe checksum path "+rel)
  if rel in seen: fail("duplicate checksum path "+rel)
  seen.add(rel); f=folder/q
  if not f.is_file() or sha(f.read_bytes())!=digest: fail("checksum mismatch "+str(f))
 return seen

def verify(input_dir, out):
 i=input_dir.resolve(); o=out.resolve()
 insums=checksums(i,"PACKET-SHA256SUMS.txt")
 im=json.loads((i/"manifest.json").read_text(encoding="utf-8"))
 if im.get("candidateFree") is not True or (im.get("head"),im.get("tree"),im.get("cellCount"),im.get("sourceCount"))!=(HEAD,TREE,300,25): fail("candidate-free input pin or coverage mismatch")
 if im.get("continuationRankRange")!=[603,627] or im.get("remainingQueueRankRange")!=[503,527]: fail("candidate-free input rank mismatch")
 if im.get("priorHeldCellsReattested")!=128: fail("candidate-free input prior-hold count mismatch")
 declared={x["path"] for x in im.get("files",[])}
 actual={p.name for p in i.iterdir() if p.is_file() and p.name not in {"manifest.json","PACKET-SHA256SUMS.txt"}}
 if declared!=actual: fail("candidate-free input file inventory mismatch")
 if insums!=actual|{"manifest.json"}: fail("candidate-free packet checksums inventory mismatch")
 for f in im["files"]:
  p=i/f["path"]
  if not p.is_file() or p.stat().st_size!=f["bytes"] or sha(p.read_bytes())!=f["sha256"]: fail("input manifest file mismatch: "+f["path"])
 osums=checksums(o,"SHA256SUMS.txt")
 entries={p.name for p in o.iterdir()}
 if any(p.is_dir() for p in o.iterdir()) or entries!=osums|{"SHA256SUMS.txt"}: fail("unexpected/unsealed output entry")
 om=json.loads((o/"manifest.json").read_text(encoding="utf-8"))
 if (om.get("head"),om.get("tree"),om.get("window"),om.get("cellCount"),om.get("repository"),om.get("pullRequest"))!=(HEAD,TREE,WINDOW,300,"snapetech-org/slskdN",409): fail("output manifest pin mismatch")
 if om.get("candidateFreeInputManifestSha256")!=sha((i/"manifest.json").read_bytes()) or om.get("candidateFreeInputPacketChecksumsSha256")!=sha((i/"PACKET-SHA256SUMS.txt").read_bytes()): fail("output/input checksum binding mismatch")
 exp={x["path"] for x in om.get("files",[])}|{"manifest.json"}
 if exp!=osums: fail("output manifest and checksum inventory differ")
 for f in om["files"]:
  p=o/f["path"]
  if not p.is_file() or p.stat().st_size!=f["bytes"] or sha(p.read_bytes())!=f["sha256"]: fail("output manifest file mismatch: "+f["path"])
 cells=read_jsonl(i/"source-current-cells.jsonl"); ledger=read_jsonl(o/"blind-ledger.jsonl")
 contexts={x["sourceId"]:x for x in read_jsonl(i/"caller-contexts.jsonl")}
 if len(cells)!=300 or len(ledger)!=300: fail("expected 300 candidate and ledger cells")
 locs=LOCALES; expected=[(r,l) for r in range(603,628) for l in locs]
 if [(x["continuationRank"],x["locale"]) for x in cells]!=expected: fail("input cell coverage/order mismatch")
 if [(x["continuationRank"],x["locale"]) for x in ledger]!=expected: fail("ledger coverage/order mismatch")
 cmap={(x["continuationRank"],x["locale"]):x for x in cells}
 counts={x:0 for x in DECISIONS}; baseline_protected=0; target_mismatch_count=0; selected_protected_failures=0; rank615_holds=0
 for r in ledger:
  k=(r["continuationRank"],r["locale"]); c=cmap[k]
  for f in ["continuationRank","remainingQueueRank","sourceId","sourceSha256","source","catalogKey","locale","currentTarget","currentTargetSha256","catalogPath","catalogFileSha256","catalogGitBlob"]:
   if r.get(f)!=c.get(f): fail(f"input identity/current content mismatch at {k}: {f}")
  if sha(c["currentTarget"].encode("utf-8"))!=c["currentTargetSha256"]: fail(f"current target hash mismatch at {k}")
  if r.get("blindDisposition") not in DECISIONS: fail(f"unknown disposition at {k}")
  d=r["blindDisposition"]; counts[d]+=1
  if d=="hold":
   rank615_holds+=k[0]==615
   if r.get("blindTarget") is not None or r.get("blindTargetSha256") is not None: fail(f"held cell has selected target at {k}")
  else:
   t=r.get("blindTarget")
   if not isinstance(t,str) or sha(t.encode("utf-8"))!=r.get("blindTargetSha256"): fail(f"blind target/hash mismatch at {k}")
   if d=="accept-current" and t!=c["currentTarget"]: fail(f"accept-current changed target at {k}")
   if d in {"correction","refinement"} and t==c["currentTarget"]: fail(f"edit disposition has unchanged target at {k}")
  cx=contexts.get(r["sourceId"])
  if not cx: fail(f"missing caller context at {k}")
  ce=r["callerEvidence"]
  if (ce["productionCallerCount"],ce["callerContextSha256"],ce["callerRefs"],ce["callers"])!=(cx["productionCallerCount"],c["callerContextSha256"],c["callerRefs"],cx["callers"]): fail(f"caller evidence mismatch at {k}")
  if k[0]==615 and (cx["productionCallerCount"]!=0 or d!="hold"): fail("rank 615 must remain held due to no production caller")
  s0=sig(c["source"]); s1=sig(c["currentTarget"])
  if c["placeholderEvidence"]!={"sourceTokens":s0["placeholders"],"currentTokens":s1["placeholders"],"matches":s0["placeholders"]==s1["placeholders"]}: fail(f"baseline placeholder audit mismatch at {k}")
  if c["markupEvidence"]!={"sourceTags":s0["markup"],"currentTags":s1["markup"],"matches":s0["markup"]==s1["markup"]}: fail(f"baseline markup audit mismatch at {k}")
  if c["sourceNumericTokens"]!=s0["numeric"] or c["currentNumericTokens"]!=s1["numeric"]: fail(f"baseline numeric audit mismatch at {k}")
  if c["sourceProtectedLiterals"]!=s0["protected"] or c["currentProtectedLiterals"]!=s1["protected"]: fail(f"baseline protected audit mismatch at {k}")
  if c["protectedLiteralEvidence"]!={"sourceTokens":s0["protected"],"currentTokens":s1["protected"],"matches":all(x in c["currentTarget"] for x in s0["protected"])}: fail(f"baseline protected evidence mismatch at {k}")
  if not c["protectedLiteralEvidence"]["matches"]: baseline_protected+=1
  curcheck={"placeholdersMatch":s0["placeholders"]==s1["placeholders"],"markupMatch":s0["markup"]==s1["markup"],"numericMeaningMatch":s0["numeric"]==s1["numeric"],"requiredProtectedLiterals":s0["protected"],"protectedLiteralsPresent":[x for x in s0["protected"] if x in c["currentTarget"]],"protectedLiteralMatch":all(x in c["currentTarget"] for x in s0["protected"])}
  ta=r["tokenAudit"]
  if ta["source"]!=s0 or ta["current"]!=s1 or ta["currentChecks"]!=curcheck: fail(f"recorded current/source token audit mismatch at {k}")
  if d=="hold":
   if ta["blindTarget"] is not None or ta["blindTargetChecks"] is not None or ta["heldWithoutTarget"] is not True: fail(f"hold audit mismatch at {k}")
  else:
   s2=sig(r["blindTarget"])
   tgtcheck={"placeholdersMatch":s0["placeholders"]==s2["placeholders"],"markupMatch":s0["markup"]==s2["markup"],"numericMeaningMatch":s0["numeric"]==s2["numeric"],"requiredProtectedLiterals":s0["protected"],"protectedLiteralsPresent":[x for x in s0["protected"] if x in r["blindTarget"]],"protectedLiteralMatch":all(x in r["blindTarget"] for x in s0["protected"])}
   if ta["blindTarget"]!=s2 or ta["blindTargetChecks"]!=tgtcheck or ta["heldWithoutTarget"] is not False: fail(f"recorded selected token audit mismatch at {k}")
   if not all([tgtcheck["placeholdersMatch"],tgtcheck["markupMatch"],tgtcheck["numericMeaningMatch"]]): target_mismatch_count+=1
   if not tgtcheck["protectedLiteralMatch"]: selected_protected_failures+=1
 summary=json.loads((o/"summary.json").read_text(encoding="utf-8"))
 if summary.get("decisionCounts")!=counts: fail("summary decision count mismatch")
 if len(summary.get("baselineProtectedLiteralFlags",[]))!=baseline_protected or summary.get("rank615HoldCount")!=rank615_holds or summary.get("priorHoldCount")!=128 or summary.get("priorHoldHashesReattested")!=128: fail("summary diagnostic/hold count mismatch")
 if summary.get("selectedTokenAuditFailures")!=target_mismatch_count or summary.get("selectedProtectedLiteralFailures")!=selected_protected_failures: fail("summary token failure count mismatch")
 if target_mismatch_count or selected_protected_failures: fail("selected token checks did not pass")
 prior=read_jsonl(i/"prior-held-cell-reattestation.jsonl"); outprior=read_jsonl(o/"prior-holds-reattestation.jsonl")
 if len(prior)!=128 or len(outprior)!=128: fail("prior hold coverage mismatch")
 ik={(x["continuationRank"],x["locale"],x["sourceId"]):x for x in prior}
 for x in outprior:
  k=(x["continuationRank"],x["locale"],x["sourceId"]); p=ik.get(k)
  if not p: fail("unexpected prior hold cell "+str(k))
  h=sha(p["currentTarget"].encode("utf-8"))
  if h!=p["priorTargetSha256"] or h!=p["currentTargetSha256"] or x["computedCurrentTargetSha256"]!=h or x["priorTargetSha256"]!=p["priorTargetSha256"] or x["targetHashMatchesPrior"] is not True: fail("prior hold target hash mismatch "+str(k))
  if x["currentCallerRefs"]!=p["currentCallerRefs"] or x["currentCatalogFileSha256"]!=p["currentCatalogFileSha256"] or x["currentCatalogGitBlob"]!=p["currentCatalogGitBlob"]: fail("prior hold caller/catalog reattestation mismatch "+str(k))
 print(json.dumps({"result":"PASS","inputFilesVerified":len(insums),"outputFilesVerified":len(osums),"cells":len(ledger),"decisionCounts":counts,"baselineProtectedLiteralFlags":baseline_protected,"selectedProtectedLiteralFailures":selected_protected_failures,"selectedTokenAuditFailures":target_mismatch_count,"rank615HeldCells":rank615_holds,"priorHolds":len(outprior),"priorHoldHashesMatched":len(outprior)},ensure_ascii=False,indent=2))

if __name__=="__main__":
 ap=argparse.ArgumentParser(); ap.add_argument("--input",required=True,type=Path); ap.add_argument("--output",type=Path,default=Path(__file__).resolve().parent)
 a=ap.parse_args(); verify(a.input,a.output)
