#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,collections,re,sys
ROOT=Path(__file__).resolve().parent; CF=Path("/mnt/disks/scratch/task-scratch/slskdn-pr409-w1028-1052-20261105/candidate-free"); PR=Path("/mnt/disks/scratch/task-scratch/slskdn-pr409-w1028-1052-20261105/primary-review"); BL=Path("/mnt/disks/scratch/task-scratch/slskdn-pr409-w1028-1052-independent-blind-20261105")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fail(x):print("FAIL:",x);sys.exit(1)
def check(d):
 for line in (d/"SHA256SUMS.txt").read_text().splitlines():
  h,n=line.split(None,1);n=n.strip()
  if not (d/n).exists() or sha(d/n)!=h:fail("input checksum "+d.name+"/"+n)
for d in (CF,PR,BL):check(d)
HEAD="624e27d8bb108a764df6daab5cfb1c517ebac96d";TREE="d139a16988e23046ccb09f519db2d3b7ae0b86d1"
def j(p):return json.loads(p.read_text())
cm,pm,bm=j(CF/"manifest.json"),j(PR/"manifest.json"),j(BL/"manifest.json")
for m in (cm,pm,bm):
 if m.get("head",m.get("review_head"))!=HEAD or m.get("tree",m.get("review_tree"))!=TREE:fail("input pin")
if sha(CF/"manifest.json")!=pm["inputCandidateFreeManifestSha256"] or sha(CF/"manifest.json")!=bm["candidateFreeManifestSha256"]:fail("candidate-free manifest linkage")
if sha(CF/"SHA256SUMS.txt")!=pm["inputCandidateFreeChecksumListSha256"] or sha(CF/"SHA256SUMS.txt")!=bm["candidateFreeChecksumListSha256"]:fail("candidate-free sums linkage")
def jl(p):return [json.loads(x) for x in p.read_text().splitlines()]
C=jl(CF/"source-current-cells.jsonl");P=jl(PR/"primary-review.jsonl");B=jl(BL/"blind-review.jsonl");L=jl(ROOT/"integrated-cross-review.jsonl")
if not(len(C)==len(P)==len(B)==len(L)==300):fail("row counts")
C={(x["continuationRank"],x["locale"]):x for x in C};P={(x["continuationRank"],x["locale"]):x for x in P};B={(x["continuationRank"],x["locale"]):x for x in B}
if len(C)!=300 or len(P)!=300 or len(B)!=300 or {(x["continuation_rank"],x["locale"]) for x in L}!=set(C):fail("coverage")
phre=re.compile(r"\{[^{}]+\}");tagre=re.compile(r"</?[A-Za-z][^>]*>");numre=re.compile(r"\d+")
for r in L:
 k=(r["continuation_rank"],r["locale"]);c=C[k];p=P[k];b=B[k]
 for a,z in ((r["source_id"],c["sourceId"]),(r["source_id_sha256"],c["sourceIdSha256"]),(r["source_sha256"],c["sourceSha256"]),(r["caller_context_sha256"],c["callerContextSha256"]),(r["current_target_sha256"],c["currentTargetSha256"])):
  if a!=z:fail("source provenance "+str(k))
 if r["primary_decision"]!=p["decision"] or r["blind_decision"]!=b["decision"]:fail("decision link "+str(k))
 if r["primary_target"]!=(p.get("proposedTarget") if p["decision"]=="proposal" else None):fail("primary target "+str(k))
 if r["blind_recommended_target"]!=(b.get("recommendedTarget") if b["decision"]=="revise" else None):fail("blind target "+str(k))
 hold=not c["sourceTextIncluded"] and not c["currentTargetTextIncluded"] and c["callerCount"]==0
 if hold:
  if r["integrated_decision"]!="hold_hash_only" or r["source_text"] is not None or r["current_target"] is not None or r["selected_target"] is not None:fail("hold text leak "+str(k))
  continue
 if r["source_text"]!=c["source"] or r["current_target"]!=c["currentTarget"]:fail("text provenance "+str(k))
 s=r["selected_target"];t=c["tokenEvidence"]
 if collections.Counter(phre.findall(s))!=collections.Counter(t["placeholders"]["source"]):fail("placeholder mismatch "+str(k))
 if collections.Counter(tagre.findall(s))!=collections.Counter(t["markup"]["source"]):fail("markup mismatch "+str(k))
 if any(s.count(x)<t["protectedLiterals"]["source"].count(x) for x in t["protectedLiterals"]["source"]):fail("protected literal mismatch "+str(k))
 ns=t["numbers"]["source"];nt=numre.findall(s)
 if collections.Counter(ns)!=collections.Counter(nt) and not(k==(1038,"ar") and ns==["1"] and not nt and "واحد" in s):fail("numeric mismatch "+str(k))
 if r["token_audit"]["result"]!="pass":fail("token status "+str(k))
if len(jl(ROOT/"prior-active-holds-hash-only.jsonl"))!=421 or sha(ROOT/"prior-active-holds-hash-only.jsonl")!=sha(CF/"prior-held-cell-reattestation-hash-only.jsonl"):fail("prior holds")
if len(jl(ROOT/"current-window-holds-hash-only.jsonl"))!=12 or sha(ROOT/"current-window-holds-hash-only.jsonl")!=sha(CF/"window-holds-hash-only.jsonl"):fail("current holds")
if j(ROOT/"summary.json")["integrated_proposal_cells"]!=44:fail("proposal count")
for line in (ROOT/"SHA256SUMS.txt").read_text().splitlines():
 h,n=line.split(None,1);n=n.strip()
 if sha(ROOT/n)!=h:fail("output checksum "+n)
print("PASS: input checksum lists/pins; 300 cells; provenance; 421+12 hash-only holds; selected-target tokens; output checksums")
