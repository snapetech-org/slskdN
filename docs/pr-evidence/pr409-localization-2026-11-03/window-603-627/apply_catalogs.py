#!/usr/bin/env python3
import hashlib,json,pathlib,re,subprocess,collections,datetime
OUT=pathlib.Path(__file__).resolve().parent
REPO=next(p for p in OUT.parents if (p/".git").exists())
AUDIT=OUT/"cross-audit"
HEAD="9ef252a53d2c14201c736de41efd0531bc00965a"
TREE="becf17f8be3f3251691002dbce487c1e94693e63"
KEYSHA="3ca04c40ebfed00b93fcd143109fc9d85da941cec30b6cb93f52e431498df6a7"
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+bytes([0])+b).hexdigest()
def j(p): return json.loads(p.read_text(encoding="utf-8"))
def jl(p): return [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s.strip()]
def writej(p,x): p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
def writel(p,x): p.write_text("".join(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n" for v in x),encoding="utf-8")
def run(args): return subprocess.check_output(args,cwd=REPO,text=True).strip()
def ordered_hash(d): return sha(("\n".join(d.keys())+"\n").encode())
def ph(s): return sorted(set(re.findall(r"\{[^{}]+\}",s)))
def tags(s): return sorted(re.findall(r"</?[A-Za-z][^>]*>",s))
def nums(s): return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)
def prot(s):
 f=set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])",s))
 for z in ("Wishlist","Soulseek","Discogs","Pod"):
  if re.search(r"(?<![A-Za-z0-9])"+re.escape(z)+r"(?![A-Za-z0-9])",s): f.add(z)
 return sorted(f)
def token_audit(source,target):
 req=prot(source)
 return {"placeholdersPreserved":ph(source)==ph(target),"markupPreserved":tags(source)==tags(target),"numericTokensPreserved":nums(source)==nums(target),"protectedLiteralsPreserved":all(target.count(z)>=source.count(z) for z in req),"requiredProtectedLiterals":req,"protectedLiteralsPresent":[z for z in req if target.count(z)>=source.count(z)]}
# Pinned base and review packet are checked before any catalog write.
if run(["git","rev-parse","HEAD"])!=HEAD or run(["git","rev-parse","HEAD^{tree}"])!=TREE: raise SystemExit("base HEAD/tree drift")
subprocess.run(["python3",str(AUDIT/"verify_cross_audit.py")],cwd=REPO,check=True,stdout=subprocess.DEVNULL)
subprocess.run(["sha256sum","-c","SHA256SUMS.txt"],cwd=AUDIT,check=True,stdout=subprocess.DEVNULL)
ledger=jl(AUDIT/"cross-audit-ledger.jsonl")
if len(ledger)!=300: raise SystemExit("cross-audit ledger coverage")
counts=collections.Counter(x["selectedDisposition"] for x in ledger)
if counts!={"accept-current":220,"correction":34,"refinement":34,"hold":12}: raise SystemExit(f"unexpected dispositions {counts}")
changed=[x for x in ledger if x["selectedTargetSha256"]!=x["currentTargetSha256"]]
if len(changed)!=68 or any(x["selectedDisposition"] not in ("correction","refinement") for x in changed): raise SystemExit("change set mismatch")
if any(x["selectedTargetSha256"]!=x["currentTargetSha256"] for x in ledger if x["selectedDisposition"] in ("accept-current","hold")): raise SystemExit("accept/hold mutation")
if any(not all(x["selectedTokenAudit"][k] for k in ("placeholdersPreserved","markupPreserved","numericTokensPreserved","protectedLiteralsPreserved")) for x in ledger): raise SystemExit("selected target token failure")
# Build a 300-cell plan and preflight all raw JSON edits in memory.
plan=[]
for x in ledger:
 plan.append({
  "baseHead":HEAD,"baseTree":TREE,"continuationRank":x["continuationRank"],"remainingQueueRank":x["remainingQueueRank"],
  "sourceId":x["sourceId"],"source":x["source"],"sourceSha256":x["sourceSha256"],"locale":x["locale"],
  "catalogPath":x["catalogPath"],"catalogKey":x["catalogKey"],"catalogFileSha256Before":x["catalogFileSha256"],
  "catalogGitBlobBefore":x["catalogGitBlob"],"currentTarget":x["currentTarget"],"currentTargetSha256":x["currentTargetSha256"],
  "selectedTarget":x["selectedTarget"],"selectedTargetSha256":x["selectedTargetSha256"],
  "disposition":x["selectedDisposition"],"resolutionNote":x["selectedRationale"],
  "callerRefs":x["callerRefs"],"callerContextSha256":x["callerContextSha256"],
  "action":"apply" if x["selectedTargetSha256"]!=x["currentTargetSha256"] else ("hold" if x["selectedDisposition"]=="hold" else "retain")
 })
writel(OUT/"application-plan.jsonl",plan)
files={}
for path in sorted({x["catalogPath"] for x in ledger}):
 p=REPO/path
 before=p.read_bytes()
 expected=next(x["catalogFileSha256"] for x in ledger if x["catalogPath"]==path)
 if sha(before)!=expected: raise SystemExit("catalog preimage hash mismatch "+path)
 d=json.loads(before)
 if len(d)!=6176 or ordered_hash(d)!=KEYSHA: raise SystemExit("catalog key invariant before "+path)
 work=before.decode("utf-8")
 rows=[x for x in ledger if x["catalogPath"]==path]
 for x in rows:
  if d.get(x["catalogKey"])!=x["currentTarget"]: raise SystemExit("current target preimage mismatch "+path+" "+x["catalogKey"])
  if sha(d[x["catalogKey"]].encode())!=x["currentTargetSha256"]: raise SystemExit("current target preimage hash mismatch "+path+" "+x["catalogKey"])
  if x["selectedTargetSha256"]==x["currentTargetSha256"]: continue
  old=json.dumps(x["catalogKey"],ensure_ascii=False)+": "+json.dumps(x["currentTarget"],ensure_ascii=False)
  new=json.dumps(x["catalogKey"],ensure_ascii=False)+": "+json.dumps(x["selectedTarget"],ensure_ascii=False)
  if work.count(old)!=1: raise SystemExit("non-unique surgical preimage "+path+" "+x["catalogKey"])
  work=work.replace(old,new,1)
 after=work.encode("utf-8"); da=json.loads(after)
 keys_changed=[x["catalogKey"] for x in rows if x["selectedTargetSha256"]!=x["currentTargetSha256"]]
 if list(da.keys())!=list(d.keys()) or ordered_hash(da)!=KEYSHA: raise SystemExit("catalog key invariant after "+path)
 for x in rows:
  if da.get(x["catalogKey"])!=x["selectedTarget"]: raise SystemExit("selected value preflight mismatch "+path+" "+x["catalogKey"])
  if sha(da[x["catalogKey"]].encode())!=x["selectedTargetSha256"]: raise SystemExit("selected hash preflight mismatch "+path+" "+x["catalogKey"])
 targets={x["catalogKey"] for x in rows if x["selectedTargetSha256"]!=x["currentTargetSha256"]}
 if any(d[k]!=da[k] for k in d if k not in targets): raise SystemExit("non-target preflight mutation "+path)
 files[path]={"before":before,"after":after,"beforeDoc":d,"afterDoc":da,"rows":rows,"changedKeys":keys_changed}
if len(files)!=12: raise SystemExit("expected twelve catalog files")
# Verify special protected literals before writing.
for loc in ("ar","hi"):
 x=next(x for x in ledger if x["continuationRank"]==612 and x["locale"]==loc)
 if "ID" not in x["selectedTarget"]: raise SystemExit("rank612 ID missing "+loc)
x=next(x for x in ledger if x["continuationRank"]==619 and x["locale"]=="hi")
if "SongID" not in x["selectedTarget"]: raise SystemExit("rank619 SongID missing")
# All checks passed; write only the twelve catalogs containing selected W69 targets.
for path,item in files.items(): (REPO/path).write_bytes(item["after"])
# Write complete readback for all 300 cells after actual writes.
readback=[]
for x in ledger:
 actual=json.loads((REPO/x["catalogPath"]).read_text(encoding="utf-8")).get(x["catalogKey"])
 ah=sha(actual.encode()) if isinstance(actual,str) else None
 if actual!=x["selectedTarget"] or ah!=x["selectedTargetSha256"]: raise SystemExit("readback mismatch "+str((x["continuationRank"],x["locale"])))
 readback.append({"continuationRank":x["continuationRank"],"remainingQueueRank":x["remainingQueueRank"],"sourceId":x["sourceId"],"catalogKey":x["catalogKey"],"catalogPath":x["catalogPath"],"locale":x["locale"],"disposition":x["selectedDisposition"],"selectedTarget":x["selectedTarget"],"selectedTargetSha256":x["selectedTargetSha256"],"readbackTarget":actual,"readbackTargetSha256":ah,"readbackMatches":True})
writel(OUT/"catalog-readback.jsonl",readback)
res_catalogs=[]; invariants=[]
for path,item in sorted(files.items()):
 after=(REPO/path).read_bytes(); da=json.loads(after); before=item["before"]; d=item["beforeDoc"]
 res_catalogs.append({"catalogPath":path,"catalogSha256Before":sha(before),"catalogGitBlobBefore":blob(before),"catalogSha256After":sha(after),"catalogGitBlobAfter":blob(after),"changedCatalogKeys":item["changedKeys"],"changedEntryCount":len(item["changedKeys"]),"keyCountBefore":len(d),"keyCountAfter":len(da),"orderedKeySha256Before":ordered_hash(d),"orderedKeySha256After":ordered_hash(da),"nonTargetValuesChanged":sum(d[k]!=da[k] for k in d if k not in set(item["changedKeys"]))})
 invariants.append({"catalogPath":path,"changedCellCount":len(item["changedKeys"]),"keyCount":len(da),"orderedKeySha256":ordered_hash(da),"nonTargetValuesChanged":sum(d[k]!=da[k] for k in d if k not in set(item["changedKeys"]))})
if any(x["nonTargetValuesChanged"]!=0 for x in res_catalogs): raise SystemExit("non-target values changed")
writej(OUT/"application-result.json",{
 "applicationMethod":"Surgical JSON string-token replacement; preserves non-target bytes, entry order, and key set.",
 "baseHead":HEAD,"baseTree":TREE,"appliedAtUtc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "changedCellCount":len(changed),"dispositionCounts":dict(counts),"noOpCount":232,"catalogs":res_catalogs,
 "priorHoldsRetainedUnchanged":128,"baselineProtectedLiteralFlagsResolved":3,
 "selectedTokenFailures":0,"repositoryFilesChangedOutside12LocaleCatalogs":False
})
writej(OUT/"catalog-invariants.json",{"baseHead":HEAD,"baseTree":TREE,"catalogKeyCountPerLocale":6176,"expectedOrderedKeySha256":KEYSHA,"changedCellCount":68,"nonTargetValuesChanged":0,"catalogs":invariants})
writej(OUT/"application-plan-summary.json",{
 "applicationPerformed":True,"baseHead":HEAD,"baseTree":TREE,"catalogFilesExpectedToChange":sorted(files),
 "catalogKeyCountPerFile":{x:6176 for x in sorted(files)},
 "dispositionCounts":{"correction":34,"refinement":34},"newHolds":0,"noOpCount":232,
 "orderedKeySha256":KEYSHA,"priorHoldsRetainedUnchanged":128,
 "applicationPlanCount":len(plan),"applicationResultSha256":sha((OUT/"application-result.json").read_bytes()),
 "reviewPacketPins":{
  "candidateFreeManifestSha256":sha((AUDIT/"evidence/w69/candidate-free-input/manifest.json").read_bytes()),
  "candidateFreeChecksumSha256":sha((AUDIT/"evidence/w69/candidate-free-input/PACKET-SHA256SUMS.txt").read_bytes()),
  "primaryManifestSha256":sha((AUDIT/"evidence/w69/primary-review/manifest.json").read_bytes()),
  "blindManifestSha256":sha((AUDIT/"evidence/w69/blind-review/manifest.json").read_bytes()),
  "crossAuditManifestSha256":sha((AUDIT/"manifest.json").read_bytes()),
  "crossAuditChecksumSha256":sha((AUDIT/"SHA256SUMS.txt").read_bytes()),
  "crossAuditLedgerSha256":sha((AUDIT/"cross-audit-ledger.jsonl").read_bytes())
 }
})
readme="""# W69 ranks 603–627 application

Applied the exact selected targets from the sealed independent cross-audit at cross-audit/. Base head/tree: 9ef252a53d2c14201c736de41efd0531bc00965a / becf17f8be3f3251691002dbce487c1e94693e63.

The application changes only 68 selected targets across the 12 locale catalogs: 34 corrections and 34 refinements. It retains 220 accepted values and all 12 rank 615 holds. The 128 carried holds remain unchanged. Arabic and Hindi at rank 612 now preserve exact ID; Hindi at rank 619 preserves exact SongID.

The application plan, preimage hashes, complete 300-cell readback, catalog key/order invariants, and non-target checks are included here. The offline verifier checks the application evidence and catalog values against the committed state.

No tests, builds, scans, CI dispatches, workflow edits, browser review, native-speaker review, merge, release, or tag were performed.
"""
(OUT/"README.md").write_text(readme,encoding="utf-8")
# Verify the only tracked modifications are the intended locale catalogs.
changed_names=set(run(["git","diff","--name-only"]).splitlines())
if changed_names!=set(files): raise SystemExit("unexpected tracked diff set "+repr(sorted(changed_names)))
print(json.dumps({"application":"PASS","changedTargets":len(changed),"dispositionCounts":dict(counts),"localeFiles":len(files),"readbackCells":len(readback),"nonTargetValuesChanged":0,"priorHoldsRetained":128},indent=2))
