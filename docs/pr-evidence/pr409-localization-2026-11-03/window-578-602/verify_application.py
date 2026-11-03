#!/usr/bin/env python3
import argparse, collections, hashlib, json, subprocess
from pathlib import Path
BASE="973a65312a475de4d8aa39aee837249553fd884e"
TREE="2a7b200dd1fe96f894bfdb663f656d6ffd48f487"
REPO="snapetech-org/slskdN"
PR=409
BRANCH="codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
E=Path("docs/pr-evidence/pr409-localization-2026-11-03/window-578-602")

def fail(s): raise SystemExit("FAIL: "+s)
def sha(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()
def git(*a): return subprocess.check_output(["git",*a],text=True).strip()
def lines(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def unique_load(s,label):
 def hook(pairs):
  d={}
  for k,v in pairs:
   if k in d: fail("duplicate key in "+label+": "+k)
   d[k]=v
  return d
 return json.loads(s,object_pairs_hook=hook)
def safe(v):
 if isinstance(v,dict):
  return all((k!="matches" or x is True) and safe(x) for k,x in v.items())
 if isinstance(v,list): return all(safe(x) for x in v)
 return True
def write_or_check(p,obj):
 data=json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n"
 if p.exists():
  if p.read_text(encoding="utf-8")!=data: fail("generated evidence differs: "+str(p))
 else: p.write_text(data,encoding="utf-8")

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--pre-push",action="store_true"); ap.add_argument("--post-push",action="store_true")
 a=ap.parse_args()
 if a.pre_push and a.post_push: fail("choose one mode")
 head=git("rev-parse","HEAD")
 if git("rev-parse","--show-toplevel")!=str(Path.cwd()): fail("run at repo root")
 if a.pre_push and git("rev-parse","HEAD^")!=BASE: fail("commit parent does not equal pinned PR base")
 if a.post_push and head==BASE: fail("post-push head still equals base")
 if not E.is_dir(): fail("missing evidence directory")
 for folder,manifest in [("candidate-free-input","PACKET-SHA256SUMS.txt"),("primary-review","SHA256SUMS.txt"),("blind-review","SHA256SUMS"),("cross-audit","SHA256SUMS")]:
  r=subprocess.run(["sha256sum","-c",manifest],cwd=E/folder,text=True,capture_output=True)
  if r.returncode: fail("packet checksum failed "+folder+" "+r.stdout+r.stderr)
 sums=E/"SHA256SUMS.txt"
 if sums.exists():
  expected={}
  for l in sums.read_text().splitlines():
   if not l.strip(): continue
   h,p=l.split("  ",1); expected[p]=h
  actual=sorted(str(p.relative_to(E)) for p in E.rglob("*") if p.is_file() and p!=sums)
  if sorted(expected)!=actual: fail("top-level manifest file inventory mismatch")
  for p,h in expected.items():
   if hashlib.sha256((E/p).read_bytes()).hexdigest()!=h: fail("top-level checksum mismatch "+p)
 plan=lines(E/"application-plan.jsonl"); noops=lines(E/"no-op-ledger.jsonl"); holds=lines(E/"hold-ledger.jsonl")
 cross=lines(E/"cross-audit/cross-audit-ledger.jsonl"); primary=lines(E/"primary-review/primary-ledger.jsonl")
 blind=lines(E/"blind-review/review-ledger.jsonl"); cells=lines(E/"candidate-free-input/source-current-cells.jsonl")
 if [len(plan),len(noops),len(holds),len(cross),len(primary),len(blind),len(cells)] != [29,271,128,300,300,300,300]: fail("W68 packet cardinality mismatch")
 ps=json.loads((E/"primary-review/summary.json").read_text())
 bs=json.loads((E/"blind-review/review-summary.json").read_text())
 cs=json.loads((E/"cross-audit/cross-audit-summary.json").read_text())["reconciliation"]
 if ps["dispositionCounts"]!={"accept-current":271,"correction":29}: fail("primary counts changed")
 if bs["verdictCounts"]!={"accept":273,"revise":27,"hold":0}: fail("blind counts changed")
 if cs["finalDecisionCounts"]!={"accept-current":271,"correction":29,"hold":0} or cs["dispositionDisagreements"]!=2 or cs["proposalTextDifferencesAmongSharedCorrections"]!=16 or cs["totalCellLevelDifferencesResolved"]!=18 or not cs["allDifferencesResolved"]: fail("cross-audit reconciliation changed")
 by_id={(r["sourceId"],r["locale"]):r for r in cross}
 if len(by_id)!=300: fail("duplicate cross cell")
 plan_by={}
 for r in plan+noops:
  if r["baseHead"]!=BASE or r["baseTree"]!=TREE or r["window"]!="W68": fail("plan base pin mismatch")
  k=(r["catalogPath"],r["catalogKey"],r["locale"])
  if k in plan_by: fail("duplicate plan cell")
  plan_by[k]=r
  c=by_id.get((r["sourceId"],r["locale"]))
  if not c or (c["selectedTarget"],c["selectedTargetSha256"],c["selectedDisposition"])!=(r["selectedTarget"],r["selectedTargetSha256"],r["disposition"]): fail("plan differs from cross selection")
 if len(plan_by)!=300: fail("plan uniqueness mismatch")
 if any(not safe(r.get("selectedTokenAudit",{})) for r in cross): fail("token audit failure")
 changed_total=0; per_locale=collections.Counter(); readback=[]; invariants=[]
 order_hashes={}
 for locale in LOCALES:
  path=f"src/web/public/locales/{locale}.json"
  base=unique_load(subprocess.check_output(["git","show",f"{BASE}:{path}"]).decode(), "base "+path)
  cur=unique_load(Path(path).read_text(encoding="utf-8"),"current "+path)
  if len(base)!=6176 or len(cur)!=6176 or list(base)!=list(cur): fail("catalog key count/order mismatch "+path)
  oh=hashlib.sha256("\n".join(base.keys()).encode()).hexdigest(); order_hashes[path]=oh
  expected={}
  for r in plan+noops:
   if r["catalogPath"]!=path: continue
   key=r["catalogKey"]
   if key not in base or base[key]!=r["currentTarget"]: fail("plan target does not match exact base "+path)
   expected[key]=r["selectedTarget"]
   if cur.get(key)!=r["selectedTarget"] or sha(r["selectedTarget"])!=r["selectedTargetSha256"]: fail("catalog readback mismatch "+path+" "+key)
   if r["disposition"]!="accept-current": per_locale[locale]+=1
   readback.append({"catalogPath":path,"locale":locale,"catalogKey":key,"sourceId":r["sourceId"],"disposition":r["disposition"],"selectedTarget":r["selectedTarget"],"selectedTargetSha256":r["selectedTargetSha256"]})
  actual={k for k in base if base[k]!=cur[k]}
  wanted={k for k,v in expected.items() if base[k]!=v}
  if actual!=wanted: fail("non-target or missing catalog change "+path)
  changed_total+=len(actual)
  invariants.append({"catalogPath":path,"keyCount":len(cur),"orderedKeySha256":oh,"changedCellCount":len(actual)})
 if changed_total!=29 or sum(per_locale.values())!=29: fail("expected 29 exact catalog corrections")
 if len(set(order_hashes.values()))!=1: fail("catalog order hash mismatch across locales")
 old=lines(E/"candidate-free-input/prior-held-cell-reattestation.jsonl")
 if len(old)!=128: fail("prior hold count mismatch")
 for h in old:
  c=unique_load(Path(h["currentCatalogPath"]).read_text(encoding="utf-8"),"held catalog")
  v=c.get(h["source"])
  if v is None or sha(v)!=h["priorTargetSha256"] or sha(v)!=h["currentTargetSha256"]: fail("prior hold changed rank "+str(h["continuationRank"]))
 if any(h["hashesMatch"] is not True or h["candidateFreeCurrentTargetSha256"]!=h["priorTargetSha256"] or h["blindRecomputedCurrentTargetSha256"]!=h["priorTargetSha256"] for h in holds): fail("hold ledger hash mismatch")
 readback.sort(key=lambda r:(LOCALES.index(r["locale"]),r["catalogKey"]))
 write_or_check(E/"catalog-readback.jsonl",readback)
 write_or_check(E/"catalog-invariants.json",{"schema":"slskdn-w68-catalog-invariants/v1","baseHead":BASE,"baseTree":TREE,"window":"W68","localeCount":12,"catalogKeyCountPerLocale":6176,"cellCount":300,"correctionCount":29,"noOpCount":271,"priorHoldCount":128,"newHoldCount":0,"orderedKeySha256":next(iter(order_hashes.values())),"catalogs":invariants})
 changed=set(git("diff","--name-only",BASE).splitlines())
 status=subprocess.check_output(["git","status","--porcelain","--untracked-files=all"],text=True).splitlines()
 paths={l[3:] for l in status if len(l)>3}|changed
 allowed={f"src/web/public/locales/{l}.json" for l in LOCALES}
 unexpected=sorted(p for p in paths if p not in allowed and not p.startswith(str(E)+"/"))
 if unexpected: fail("unexpected changed paths "+", ".join(unexpected))
 if any(p.startswith(".github/workflows/") for p in paths): fail("workflow changed")
 dc=subprocess.run(["git","diff","--check",BASE],text=True,capture_output=True)
 if dc.returncode: fail("git diff --check "+dc.stdout+dc.stderr)
 if a.pre_push or a.post_push:
  pr=json.loads(subprocess.check_output(["gh","api",f"repos/{REPO}/pulls/{PR}"],text=True))
  if pr["state"]!="open" or pr.get("merged_at") is not None or not pr.get("draft",False): fail("PR not open/draft/unmerged")
  if pr["base"]["ref"]!="main": fail("unexpected PR base")
  if a.pre_push and (pr["head"]["sha"]!=BASE or pr["head"]["ref"]!=BRANCH): fail("remote PR head changed pre-push")
  if a.post_push:
   if pr["head"]["sha"]!=head or pr["head"]["ref"]!=BRANCH: fail("remote PR head mismatch")
   if pr.get("body","").count("<!-- localization-window-w68-578-602 -->")!=1: fail("PR body marker missing or duplicated")
 print(json.dumps({"status":"PASS","mode":"pre-push" if a.pre_push else "post-push" if a.post_push else "local","head":head,"reviewedCells":300,"corrections":29,"retainedCells":271,"priorHolds":128,"newHolds":0,"catalogs":12,"changedPaths":len(paths),"workflowPaths":0},indent=2))
if __name__=="__main__": main()
