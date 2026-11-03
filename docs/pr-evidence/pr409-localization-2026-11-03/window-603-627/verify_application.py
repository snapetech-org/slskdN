#!/usr/bin/env python3
import json,hashlib,pathlib,re,subprocess,collections,sys
OUT=pathlib.Path(__file__).resolve().parent
REPO=next(p for p in OUT.parents if (p/".git").exists())
AUDIT=OUT/"cross-audit"
HEAD="9ef252a53d2c14201c736de41efd0531bc00965a"
TREE="becf17f8be3f3251691002dbce487c1e94693e63"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
def fail(s): raise SystemExit("FAIL: "+s)
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+bytes([0])+b).hexdigest()
def j(p): return json.loads(p.read_text(encoding="utf-8"))
def jl(p): return [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s.strip()]
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
def check_token(src,tgt):
 req=prot(src)
 return {"placeholdersPreserved":ph(src)==ph(tgt),"markupPreserved":tags(src)==tags(tgt),"numericTokensPreserved":nums(src)==nums(tgt),"protectedLiteralsPreserved":all(tgt.count(z)>=src.count(z) for z in req),"requiredProtectedLiterals":req,"protectedLiteralsPresent":[z for z in req if tgt.count(z)>=src.count(z)]}
def verify_sum_file(folder,name):
 p=folder/name; seen=set()
 if not p.is_file(): fail("missing checksum file "+str(p))
 for line in p.read_text(encoding="utf-8").splitlines():
  if not line.strip(): continue
  m=re.fullmatch(r"([0-9a-f]{64})  (.+)",line)
  if not m: fail("malformed checksum line")
  h,rel=m.groups(); q=pathlib.Path(rel)
  if q.is_absolute() or ".." in q.parts or rel in seen: fail("unsafe checksum path")
  seen.add(rel); f=folder/q
  if not f.is_file() or sha(f.read_bytes())!=h: fail("checksum mismatch "+str(f))
 return len(seen)
# Seal integrity for application artifacts and the nested cross-audit.
manifest=j(OUT/"manifest.json"); entries=manifest["files"]; listed=set()
for x in entries:
 rel=x["path"]; q=pathlib.Path(rel)
 if q.is_absolute() or ".." in q.parts or rel in listed: fail("unsafe/duplicate manifest path "+rel)
 listed.add(rel); f=OUT/q
 if not f.is_file() or f.stat().st_size!=x["bytes"] or sha(f.read_bytes())!=x["sha256"]: fail("manifest mismatch "+rel)
sum_count=verify_sum_file(OUT,"SHA256SUMS.txt")
if sum_count!=len(entries)+1: fail("application checksum coverage")
subprocess.run(["python3",str(AUDIT/"verify_cross_audit.py")],cwd=REPO,check=True,stdout=subprocess.DEVNULL)
audit=jl(AUDIT/"cross-audit-ledger.jsonl")
if len(audit)!=300: fail("cross-audit ledger")
amap={(x["continuationRank"],x["locale"]):x for x in audit}
plan=jl(OUT/"application-plan.jsonl"); rb=jl(OUT/"catalog-readback.jsonl")
if len(plan)!=300 or len(rb)!=300: fail("application coverage")
pmap={(x["continuationRank"],x["locale"]):x for x in plan}; rmap={(x["continuationRank"],x["locale"]):x for x in rb}
if set(pmap)!=set(amap) or set(rmap)!=set(amap): fail("application row keys")
res=j(OUT/"application-result.json"); base=res["baseHead"]
if (base,res["baseTree"])!=(HEAD,TREE): fail("base pin")
if run(["git","rev-parse",base+"^{tree}"])!=TREE: fail("base tree object")
changes=collections.Counter(); paths=set(); applied=0
for k,x in amap.items():
 p=pmap[k]; r=rmap[k]
 if p["selectedTarget"]!=x["selectedTarget"] or p["selectedTargetSha256"]!=x["selectedTargetSha256"] or p["currentTargetSha256"]!=x["currentTargetSha256"]: fail("plan/audit binding "+str(k))
 if r["selectedTarget"]!=x["selectedTarget"] or r["readbackTarget"]!=x["selectedTarget"] or r["readbackTargetSha256"]!=x["selectedTargetSha256"] or r["readbackMatches"] is not True: fail("readback binding "+str(k))
 d=json.loads((REPO/x["catalogPath"]).read_text(encoding="utf-8"))
 if d.get(x["catalogKey"])!=x["selectedTarget"] or sha(d[x["catalogKey"]].encode())!=x["selectedTargetSha256"]: fail("catalog exact readback "+str(k))
 before=json.loads(subprocess.check_output(["git","show",base+":"+x["catalogPath"]],cwd=REPO))
 if before.get(x["catalogKey"])!=x["currentTarget"] or sha(before[x["catalogKey"]].encode())!=x["currentTargetSha256"]: fail("catalog source preimage "+str(k))
 changed=x["selectedTarget"]!=x["currentTarget"]
 if changed:
  applied+=1
  if x["selectedDisposition"] not in ("correction","refinement"): fail("changed non-change disposition "+str(k))
 else:
  if x["selectedDisposition"] in ("correction","refinement"): fail("unchanged change disposition "+str(k))
  if before[x["catalogKey"]]!=d[x["catalogKey"]]: fail("unexpected retained target mutation "+str(k))
 if x["selectedDisposition"] in ("accept-current","hold") and changed: fail("accept/hold changed "+str(k))
 t=check_token(x["source"],x["selectedTarget"])
 if t!=x["selectedTokenAudit"] or not all(t[z] for z in ("placeholdersPreserved","markupPreserved","numericTokensPreserved","protectedLiteralsPreserved")): fail("selected token audit "+str(k))
 paths.add(x["catalogPath"]); changes[x["selectedDisposition"]]+=1
 if list(before.keys())!=list(d.keys()) or ordered_hash(d)!="3ca04c40ebfed00b93fcd143109fc9d85da941cec30b6cb93f52e431498df6a7": fail("catalog key order "+x["catalogPath"])
 if len(before)!=6176 or len(d)!=6176: fail("catalog key count")
 if "ID" in x["source"] and x["continuationRank"]==612 and x["locale"] in ("ar","hi") and "ID" not in x["selectedTarget"]: fail("rank612 exact ID")
 if "SongID" in x["source"] and x["continuationRank"]==619 and x["locale"]=="hi" and "SongID" not in x["selectedTarget"]: fail("rank619 exact SongID")
 if x["continuationRank"]==615 and (x["selectedDisposition"]!="hold" or x["callerContext"]["productionCallerCount"]!=0): fail("rank615 hold")
 # Compare all non-target values against the base commit.
 changed_keys={a["catalogKey"] for a in audit if a["catalogPath"]==x["catalogPath"] and a["selectedTarget"]!=a["currentTarget"]}
 if any(before[z]!=d[z] for z in before if z not in changed_keys): fail("non-target catalog value changed "+x["catalogPath"])
if applied!=68 or changes!={"accept-current":220,"correction":34,"refinement":34,"hold":12} or len(paths)!=12: fail("final application counts")
if any(x["nonTargetValuesChanged"]!=0 for x in res["catalogs"]): fail("recorded non-target change")
if res["changedCellCount"]!=68 or res["priorHoldsRetainedUnchanged"]!=128 or res["selectedTokenFailures"]!=0: fail("application result summary")
# Only locale catalogs plus this W69 evidence directory may differ from the pinned base.
changed_paths=set(run(["git","diff","--name-only",base]).splitlines())
allowed=paths
for p in changed_paths:
 if p in allowed: continue
 if not p.startswith("docs/pr-evidence/pr409-localization-2026-11-03/window-603-627/"): fail("unexpected changed path "+p)
if any(p.startswith(".github/workflows/") for p in changed_paths): fail("workflow path changed")
# Verify prior holds and exact held rank.
holds=jl(AUDIT/"prior-hold-reconciliation.jsonl")
if len(holds)!=128 or any(x["targetHashMatchesAcrossW68W69"] is not True for x in holds): fail("prior hold reconciliation")
summary=j(OUT/"application-plan-summary.json")
if summary["applicationPlanCount"]!=300 or summary["noOpCount"]!=232 or summary["dispositionCounts"]!={"correction":34,"refinement":34}: fail("application plan summary")
print(json.dumps({"result":"PASS","baseHead":HEAD,"baseTree":TREE,"appliedCells":applied,"dispositions":dict(changes),"catalogFiles":len(paths),"readbackCells":len(rb),"nonTargetValuesChanged":0,"catalogKeysPerLocale":6176,"priorHoldsRetained":len(holds),"workflowFilesChanged":0},ensure_ascii=False,indent=2))
