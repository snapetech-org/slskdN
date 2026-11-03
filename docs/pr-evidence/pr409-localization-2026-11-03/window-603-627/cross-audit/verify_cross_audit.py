#!/usr/bin/env python3
"""Offline verifier for the sealed slskdN PR #409 W69 cross-audit packet."""
import hashlib,json,re,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parent
HEAD="9ef252a53d2c14201c736de41efd0531bc00965a"
TREE="becf17f8be3f3251691002dbce487c1e94693e63"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
def fail(s): raise SystemExit("FAIL: "+s)
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+bytes([0])+b).hexdigest()
def j(p): return json.loads(p.read_text(encoding="utf-8"))
def jl(p): return [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s.strip()]
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
def ph(s): return sorted(set(re.findall(r"\{[^{}]+\}",s)))
def tags(s): return sorted(re.findall(r"</?[A-Za-z][^>]*>",s))
def nums(s): return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)
def prot(s):
 f=set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])",s))
 for x in ("Wishlist","Soulseek","Discogs","Pod"):
  if re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",s): f.add(x)
 return sorted(f)
def sig(s): return {"placeholders":ph(s),"markup":tags(s),"numeric":nums(s),"protectedLiterals":prot(s)}
def tokcheck(src,tgt):
 a,b=sig(src),sig(tgt)
 return {"placeholdersPreserved":a["placeholders"]==b["placeholders"],"markupPreserved":a["markup"]==b["markup"],"numericTokensPreserved":a["numeric"]==b["numeric"],"protectedLiteralsPreserved":all(tgt.count(x)>=src.count(x) for x in a["protectedLiterals"]),"requiredProtectedLiterals":a["protectedLiterals"],"protectedLiteralsPresent":[x for x in a["protectedLiterals"] if tgt.count(x)>=src.count(x)]}
def verify_sums(folder,name):
 p=folder/name
 if not p.is_file(): fail("missing checksum list "+str(p))
 seen=set()
 for line in p.read_text(encoding="utf-8").splitlines():
  if not line.strip(): continue
  m=re.fullmatch(r"([0-9a-f]{64})  (.+)",line)
  if not m: fail("malformed checksum line "+line)
  digest,rel=m.groups(); q=Path(rel)
  if q.is_absolute() or ".." in q.parts or rel in seen: fail("unsafe/duplicate path "+rel)
  seen.add(rel); f=folder/q
  if not f.is_file() or sha(f.read_bytes())!=digest: fail("packet checksum mismatch "+str(f))
 return len(seen)
def raw_json_stream(path):
 text=path.read_text(encoding="utf-8"); dec=json.JSONDecoder(); vals=[]; i=0
 while i<len(text):
  while i<len(text) and text[i].isspace(): i+=1
  if i==len(text): break
  v,n=dec.raw_decode(text,i); vals.append(v); i=n
 return vals
manifest=j(ROOT/"manifest.json"); entries=manifest["files"]
if not isinstance(entries,list) or not entries: fail("empty outer manifest")
seen=set()
for x in entries:
 rel=x["path"]; q=Path(rel)
 if q.is_absolute() or ".." in q.parts or rel in seen: fail("unsafe/duplicate outer path "+rel)
 seen.add(rel); f=ROOT/q
 if not f.is_file() or f.stat().st_size!=x["bytes"] or sha(f.read_bytes())!=x["sha256"]: fail("outer manifest mismatch "+rel)
sum_count=verify_sums(ROOT,"SHA256SUMS.txt")
if sum_count!=len(entries)+1: fail("outer checksum coverage mismatch")
I=ROOT/"evidence/w69/candidate-free-input"; P=ROOT/"evidence/w69/primary-review"; B=ROOT/"evidence/w69/blind-review"
W68I=ROOT/"evidence/w68-lineage/candidate-free-input"; W68X=ROOT/"evidence/w68-lineage/cross-audit"
inner={"w69CandidateInput":verify_sums(I,"PACKET-SHA256SUMS.txt"),"w69Primary":verify_sums(P,"SHA256SUMS.txt"),"w69Blind":verify_sums(B,"SHA256SUMS.txt"),"w68CandidateInput":verify_sums(W68I,"PACKET-SHA256SUMS.txt"),"w68CrossAudit":verify_sums(W68X,"SHA256SUMS")}
im=j(I/"manifest.json"); pm=j(P/"manifest.json"); bm=j(B/"manifest.json")
if (im["head"],im["tree"],im["sourceCount"],im["cellCount"])!=(HEAD,TREE,25,300): fail("W69 input pin")
if pm["inputManifestSha256"]!=sha((I/"manifest.json").read_bytes()) or bm["candidateFreeInputManifestSha256"]!=sha((I/"manifest.json").read_bytes()): fail("review input lineage")
if pm["inputCellLedgerSha256"]!=sha((I/"source-current-cells.jsonl").read_bytes()) or bm["candidateFreeInputPacketChecksumsSha256"]!=sha((I/"PACKET-SHA256SUMS.txt").read_bytes()): fail("review cell/packet lineage")
for name in ("live-pr-before.json","live-pr-after.json"):
 x=j(ROOT/name)
 draft=x.get("draft",x.get("isDraft"))
 branch=x.get("branch",x.get("headRefName"))
 head=x.get("head",x.get("headRefOid"))
 tree=x.get("commitTree",x.get("tree"))
 if x.get("state")!="OPEN" or draft is not True: fail("live state snapshot "+name)
 if name=="live-pr-after.json" and x.get("matches") is not True: fail("live after-state refs "+name)
 if (branch,head,tree)!=(im["branch"],HEAD,TREE) or x.get("branchRef")!=HEAD or x.get("pullRef")!=HEAD: fail("live pin snapshot "+name)
raw=ROOT/"evidence/pinned-source"; pinmeta=j(ROOT/"pinned-source-files.json"); rawmap={x["path"]:x for x in pinmeta["files"]}
for rel,x in rawmap.items():
 b=(raw/rel).read_bytes()
 if len(b)!=x["bytes"] or sha(b)!=x["sha256"] or blob(b)!=x["gitBlob"]: fail("raw source pin "+rel)
invpath="docs/pr-evidence/pr409-localization-2026-11-03/window49/primary/source-inventory.jsonl"
invbytes=(raw/invpath).read_bytes()
if sha(invbytes)!=im["sourceInventorySha256"]: fail("source inventory hash")
inv=jl(raw/invpath)
if len(inv)!=6176 or pinmeta["head"]!=HEAD or pinmeta["tree"]!=TREE: fail("source inventory coverage")
catalog_struct=jl(I/"catalog-structure.jsonl")
if len(catalog_struct)!=12: fail("catalog structure coverage")
catalogs={}; keysha="3ca04c40ebfed00b93fcd143109fc9d85da941cec30b6cb93f52e431498df6a7"
for s in catalog_struct:
 data=(raw/s["catalogPath"]).read_bytes()
 if sha(data)!=s["sha256"] or blob(data)!=s["gitBlob"]: fail("catalog raw pin "+s["locale"])
 cat=json.loads(data)
 if len(cat)!=6176 or sha(("\n".join(cat.keys())+"\n").encode())!=keysha: fail("catalog ordered keys "+s["locale"])
 catalogs[s["locale"]]=cat
sel=jl(I/"source-inventory-selection.jsonl"); invby={x["sourceId"]:x for x in inv}
if len(sel)!=25: fail("selected source count")
for r in sel:
 if invby.get(r["sourceId"])!=r: fail("selected source inventory mismatch "+r["sourceId"])
if [x["continuationRank"] for x in sel]!=list(range(603,628)) or [x["remainingQueueRank"] for x in sel]!=list(range(503,528)): fail("continuation/queue rank continuity")
exclusions=jl(I/"prior-selected-id-exclusions.jsonl")
if len(exclusions)!=1707 or len({x["sourceId"] for x in exclusions})!=1707 or {x["sourceId"] for x in exclusions}&{x["sourceId"] for x in sel}: fail("prior ID exclusions")
ctxs=jl(I/"caller-contexts.jsonl"); ctxby={x["sourceId"]:x for x in ctxs}
src=jl(I/"source-current-cells.jsonl"); primary=jl(P/"primary-ledger.jsonl"); blind=jl(B/"blind-ledger.jsonl")
if (len(ctxs),len(src),len(primary),len(blind))!=(25,300,300,300): fail("source/review coverage")
srcmap={(x["continuationRank"],x["locale"]):x for x in src}; pmap={(x["continuationRank"],x["locale"]):x for x in primary}; bmap={(x["continuationRank"],x["locale"]):x for x in blind}
if len(srcmap)!=300 or len(pmap)!=300 or len(bmap)!=300: fail("duplicate source/review cell")
for x in src:
 r=x["continuationRank"]; loc=x["locale"]; c=ctxby[x["sourceId"]]
 if loc not in LOCALES or x["currentTarget"]!=catalogs[loc].get(x["source"]): fail("catalog target "+str((r,loc)))
 if sha(x["currentTarget"].encode())!=x["currentTargetSha256"]: fail("current target hash "+str((r,loc)))
 callers=c["callers"]
 if c["productionCallerCount"]!=len(callers) or c["sourceSha256"]!=x["sourceSha256"]: fail("caller count/source")
 if sha(canon([q["context"] for q in callers]))!=x["callerContextSha256"]: fail("caller context aggregate")
 refs=[]
 for q in callers:
  rel=q["path"]; data=(raw/rel).read_bytes(); lines=data.decode("utf-8").splitlines()
  if sha(data)!=q["fileSha256"] or blob(data)!=q["gitBlob"]: fail("caller file pin "+rel)
  if not (1<=q["line"]<=len(lines)) or lines[q["line"]-1]!=q["lineText"]: fail("caller line "+rel)
  if sha(lines[q["line"]-1].encode())!=q["lineSha256"] or sha(canon(q["context"]))!=q["contextSha256"]: fail("caller line/context hash "+rel)
  for near in q["context"]:
   if lines[near["line"]-1]!=near["text"]: fail("caller context "+rel)
  refs.append({k:q[k] for k in ("path","line","lineSha256","fileSha256","gitBlob")})
 if refs!=x["callerRefs"]: fail("caller refs binding "+str((r,loc)))
w68im=j(W68I/"manifest.json"); w68sel=j(W68I/"selection-and-boundary.json"); w69sel=j(I/"selection-and-boundary.json")
if (w68im["head"],w68im["tree"],w68im["continuationRankRange"])!=("973a65312a475de4d8aa39aee837249553fd884e","2a7b200dd1fe96f894bfdb663f656d6ffd48f487",[578,602]): fail("W68 pin")
if w68sel["nextUnselectedContinuationRank"]!=603 or w68sel["nextUnselectedSourceId"]!=sel[0]["sourceId"]: fail("W68/W69 start boundary")
if (w69sel["previousWindow"],w69sel["previousWindowFinalContinuationRank"],w69sel["selection"]["continuationRankStart"],w69sel["selection"]["continuationRankEnd"],w69sel["nextUnselectedContinuationRank"])!=("W68",602,603,627,628): fail("W69 boundary")
if w69sel["nextUnselectedSourceId"]!="src_27f3ec760e95a097": fail("W69 next source")
if sha((W68I/"PACKET-SHA256SUMS.txt").read_bytes())!=im["priorLineagePins"]["W68CandidateFreeChecksumsSha256"]: fail("W68 packet lineage")
if sha((W68X/"manifest.json").read_bytes())!=im["priorLineagePins"]["W68CrossAuditManifestSha256"]: fail("W68 manifest lineage")
if sha((W68X/"SHA256SUMS").read_bytes())!=im["priorLineagePins"]["W68CrossAuditChecksumsSha256"]: fail("W68 checksum lineage")
prior68=jl(W68I/"prior-held-cell-reattestation.jsonl"); prior69=jl(I/"prior-held-cell-reattestation.jsonl"); paired=jl(ROOT/"prior-hold-reconciliation.jsonl")
if not (len(prior68)==len(prior69)==128): fail("prior hold source count")
def keyed(rows): return {(x["continuationRank"],x["locale"],x["sourceId"]):x for x in rows}
a,z,q=keyed(prior68),keyed(prior69),keyed(paired)
if not (len(a)==len(z)==len(q)==128) or set(a)!=set(z) or set(a)!=set(q): fail("prior hold coverage")
for k in a:
 if a[k]["currentTargetSha256"]!=z[k]["currentTargetSha256"] or z[k]["currentTargetSha256"]!=z[k]["priorTargetSha256"]: fail("prior hold drift "+str(k))
 if q[k]["w68CurrentTargetSha256"]!=q[k]["w69CurrentTargetSha256"] or q[k]["w69CurrentTargetSha256"]!=z[k]["currentTargetSha256"]: fail("prior hold pairing "+str(k))
ledger=jl(ROOT/"cross-audit-ledger.jsonl")
if len(ledger)!=300: fail("cross ledger count")
lm={(x["continuationRank"],x["locale"]):x for x in ledger}
if len(lm)!=300 or set(lm)!=set(srcmap): fail("cross ledger keys")
cc=collections.Counter(); dc=collections.Counter(); sc=collections.Counter()
target_conflicts=disp_diffs=rat_diffs=changed=token_fails=0
for k,x in lm.items():
 s=srcmap[k]; p=pmap[k]; b=bmap[k]
 if x["sourceId"]!=s["sourceId"] or x["source"]!=s["source"] or x["currentTarget"]!=s["currentTarget"]: fail("cross cell binding "+str(k))
 eff=s["currentTarget"] if b["blindDisposition"]=="hold" else b.get("blindTarget",s["currentTarget"])
 phash=p["reviewedTargetSha256"]; bh=sha(eff.encode()); ch=s["currentTargetSha256"]
 if x["primaryReviewedTargetSha256"]!=phash or x["blindEffectiveTarget"]!=eff or x["blindEffectiveTargetSha256"]!=bh: fail("review target binding "+str(k))
 pc=phash!=ch; bc=bh!=ch
 cmp=("agree_changed" if pc else "agree_current") if phash==bh else ("both_different" if pc and bc else "primary_only" if pc else "blind_only")
 if x["comparison"]!=cmp: fail("comparison "+str(k))
 cc[cmp]+=1
 if phash!=bh: target_conflicts+=1
 if p["disposition"]!=b["blindDisposition"]: disp_diffs+=1
 if p["rationale"]!=b["rationale"]: rat_diffs+=1
 if x["primaryDisposition"]!=p["disposition"] or x["blindDisposition"]!=b["blindDisposition"]: fail("review disposition "+str(k))
 if x["selectedTargetSha256"]!=sha(x["selectedTarget"].encode()): fail("selected hash "+str(k))
 if not x["selectedRationale"] or not x["selectedConfidence"]: fail("missing rationale "+str(k))
 d=x["selectedDisposition"]
 if d=="hold":
  if k[0]!=615 or x["selectedTarget"]!=s["currentTarget"]: fail("invalid hold "+str(k))
 elif d=="accept-current":
  if x["selectedTarget"]!=s["currentTarget"]: fail("accept target "+str(k))
 elif d in ("correction","refinement"):
  if x["selectedTarget"]==s["currentTarget"]: fail("changed disposition "+str(k))
 else: fail("unknown selected disposition "+str(k))
 if x["selectedTarget"]!=s["currentTarget"]: changed+=1
 t=tokcheck(s["source"],x["selectedTarget"])
 if x["selectedTokenAudit"]!=t or not all(t[n] for n in ("placeholdersPreserved","markupPreserved","numericTokensPreserved","protectedLiteralsPreserved")): token_fails+=1
 dc[d]+=1; sc[x["selectionSource"]]+=1
 if k[0]==615 and (d!="hold" or not x["callerless"] or x["callerContext"]["productionCallerCount"]!=0): fail("rank 615 must hold")
if target_conflicts!=76 or disp_diffs!=64 or rat_diffs!=300 or token_fails: fail("disagreement/token totals")
if cc!={"blind_only":49,"agree_current":220,"both_different":13,"primary_only":14,"agree_changed":4}: fail("comparison counts")
if dc!={"correction":34,"refinement":34,"accept-current":220,"hold":12}: fail("selected disposition counts")
if changed!=68: fail("selected changes")
for loc in ("ar","hi"):
 x=lm[(612,loc)]
 if "ID" not in x["selectedTarget"] or x["selectedDisposition"]!="correction" or x.get("protectedLiteralFinding")!="ID": fail("rank 612 ID "+loc)
x=lm[(619,"hi")]
if "SongID" not in x["selectedTarget"] or x["selectedDisposition"]!="correction" or x.get("protectedLiteralFinding")!="SongID": fail("rank 619 SongID")
for loc in LOCALES:
 if lm[(615,loc)]["selectedDisposition"]!="hold": fail("rank 615 locale "+loc)
cf=j(ROOT/"candidate-free-verification.json"); blindv=j(ROOT/"blind-verification.json"); prim=raw_json_stream(ROOT/"primary-verification.json")
if not cf.get("pass") or cf.get("head")!=HEAD or cf.get("tree")!=TREE: fail("candidate-free verifier evidence")
if len(prim)<2 or not prim[-1].get("pass") or prim[-1].get("cells")!=300: fail("primary verifier evidence")
if blindv.get("result")!="PASS" or blindv.get("cells")!=300 or blindv.get("selectedTokenAuditFailures")!=0: fail("blind verifier evidence")
summary=j(ROOT/"summary.json")
if summary["comparisonCounts"]!=dict(cc) or summary["selectedDispositionCounts"]!=dict(dc): fail("summary count binding")
if summary["targetHashDisagreements"]!=target_conflicts or summary["primaryBlindDispositionDifferences"]!=disp_diffs or summary["rationaleTextDifferences"]!=rat_diffs: fail("summary disagreement binding")
if summary["priorHoldsReattested"]!=128 or summary["selectedTokenFailures"]!=0 or summary["repositoryOrPullRequestModified"] is not False: fail("summary attestation")
print(json.dumps({"result":"PASS","head":HEAD,"tree":TREE,"innerPacketFilesVerified":inner,"rawPinnedSourceFiles":pinmeta["fileCount"],"sourceInventoryRows":len(inv),"cells":len(ledger),"sources":25,"locales":12,"comparisonCounts":dict(cc),"targetHashDisagreements":target_conflicts,"dispositionDifferences":disp_diffs,"selectedDispositionCounts":dict(dc),"selectedChangedTargets":changed,"baselineProtectedLiteralOmissions":3,"selectedTokenFailures":token_fails,"rank612ExactIDRepairs":2,"rank619ExactSongIDRepairs":1,"rank615HeldCells":12,"priorHoldsReattested":128,"w68End":602,"w69Start":603,"w69End":627,"nextUnselected":628,"outerManifestFiles":len(entries),"outerChecksumEntries":sum_count},ensure_ascii=False,indent=2))
