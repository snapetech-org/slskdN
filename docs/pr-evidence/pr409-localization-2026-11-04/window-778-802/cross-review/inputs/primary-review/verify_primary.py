#!/usr/bin/env python3
import argparse,collections,hashlib,json,re,subprocess,sys,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parent
INPUT=ROOT.parent.parent/"candidate-free"/"input"
HEAD="674156749ee86021ef91d896b1824be62cff9a93"
TREE="86483dbf9227130cade6a3f4c9dc9ef5cf232450"
BRANCH="codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
def fail(s): raise SystemExit("FAIL: "+s)
def sha(b): return hashlib.sha256(b).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def readj(p): return json.loads(p.read_text(encoding="utf-8"))
def rows(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def ph(s): return collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}",s))
def tags(s): return collections.Counter(re.findall(r"</?[A-Za-z][^>]*>",s))
def nums(s): return ["".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in m) for m in re.findall(r"\d+",s)]
def prot(s):
 t=set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b",s)); t.update(x for x in ("slskdN","Tor","Wishlist","Chromaprint") if x in s); return sorted(t)
def not_less(a,b):
 ca,cb=collections.Counter(a),collections.Counter(b); return all(cb[t]>=n for t,n in ca.items())
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--repo",required=True); a=ap.parse_args(); repo=Path(a.repo).resolve()
 inp=json.loads(subprocess.check_output(["python3",str(INPUT/"verify_input.py"),"--repo",str(repo)],text=True))
 if inp.get("result")!="PASS" or inp.get("head")!=HEAD or inp.get("tree")!=TREE: fail("candidate-free verifier")
 input_manifest=readj(INPUT/"manifest.json")
 cells=rows(INPUT/"source-current-cells.jsonl")
 ledger=rows(ROOT/"primary-review.jsonl"); corrections=rows(ROOT/"corrections.jsonl"); holds=rows(ROOT/"holds-hash-only.jsonl")
 expected={(x["continuationRank"],x["locale"]):x for x in cells}
 actual={(x["continuationRank"],x["locale"]):x for x in ledger}
 if len(expected)!=300 or len(actual)!=300 or set(expected)!=set(actual): fail("cell coverage/uniqueness")
 counts=collections.Counter(); correction_rows=[]; hold_rows=[]
 caller_by_rank={x["continuationRank"]:x for x in rows(INPUT/"caller-contexts.jsonl")}
 for key,source in expected.items():
  rank,locale=key; row=actual[key]; disposition=row.get("disposition"); counts[disposition]+=1
  if row.get("head")!=HEAD or row.get("tree")!=TREE: fail(f"pin {rank}/{locale}")
  for f in ("continuationRank","remainingQueueRank","sourceId","sourceSha256","locale","catalogPath","catalogFileSha256","catalogGitBlob","currentTargetSha256","callerContextSha256","callerRefs"):
   if row.get(f)!=source.get(f): fail(f"input reference {f} {rank}/{locale}")
  caller_count=caller_by_rank[rank]["productionCallerCount"]
  if row.get("productionCallerCount")!=caller_count: fail(f"caller count {rank}/{locale}")
  if disposition=="hold":
   if caller_count!=0: fail(f"hold has caller {rank}/{locale}")
   if any(k in row for k in ("source","catalogKey","currentTarget","target")): fail(f"hold leaks text {rank}/{locale}")
   if row.get("sourceTextIncluded") is not False or row.get("currentTargetTextIncluded") is not False: fail(f"hold text flags {rank}/{locale}")
   if not row.get("holdReason") or not row.get("holdReasonSha256") or row.get("confidence") not in ("high","moderate","low"): fail(f"hold metadata {rank}/{locale}")
   hold_rows.append(row); continue
  if caller_count==0: fail(f"callerless non-hold {rank}/{locale}")
  for f in ("source","catalogKey","currentTarget"):
   if row.get(f)!=source.get(f): fail(f"text mismatch {f} {rank}/{locale}")
  if sha(row["source"].encode())!=row["sourceSha256"] or sha(row["currentTarget"].encode())!=row["currentTargetSha256"]: fail(f"text hash {rank}/{locale}")
  if not row.get("rationale") or row.get("confidence") not in ("high","moderate","low"): fail(f"rationale/confidence {rank}/{locale}")
  tc=row.get("tokenCheck",{})
  s,c=row["source"],row["currentTarget"]
  if tc.get("placeholderParityCurrent")!=(ph(s)==ph(c)) or tc.get("markupParityCurrent")!=(tags(s)==tags(c)) or tc.get("numericTokensPreservedCurrent")!=not_less(nums(s),nums(c)) or tc.get("protectedLiteralsPreservedCurrent")!=all(x in c for x in prot(s)):
   fail(f"current token evidence {rank}/{locale}")
  if disposition=="accept-current":
   if "target" in row or "proposal" in tc: fail(f"accept includes proposal {rank}/{locale}")
  elif disposition=="correct":
   target=row.get("target")
   if not isinstance(target,str) or not target or row.get("targetSha256")!=sha(target.encode()): fail(f"target/hash {rank}/{locale}")
   p=tc.get("proposal",{})
   if p.get("placeholderParity")!=(ph(s)==ph(target)) or p.get("markupParity")!=(tags(s)==tags(target)) or p.get("numericTokensPreserved")!=not_less(nums(s),nums(target)) or p.get("protectedLiteralsPreserved")!=all(x in target for x in prot(s)):
    fail(f"proposal token mismatch {rank}/{locale}")
   if p.get("placeholderTokens")!=sorted(ph(target).elements()) or p.get("markupTokens")!=sorted(tags(target).elements()) or p.get("numericTokens")!=nums(target) or p.get("protectedLiterals")!=prot(target):
    fail(f"proposal token list {rank}/{locale}")
   correction_rows.append(row)
  else: fail(f"unknown disposition {rank}/{locale}")
 if counts!=collections.Counter({"accept-current":183,"correct":69,"hold":48}): fail(f"disposition counts {counts}")
 callerless={r["continuationRank"] for r in caller_by_rank.values() if r["productionCallerCount"]==0}
 if callerless!={793,795,796,802}: fail(f"callerless set changed {callerless}")
 if corrections!=correction_rows or holds!=hold_rows: fail("extract differs from primary ledger")
 if any(any(k in r for k in ("source","catalogKey","currentTarget","target")) for r in holds): fail("hold extract has text")
 sr=readj(ROOT/"source-rewrite-recommendations.json")
 if sr!={"schemaVersion":1,"recommendations":[]}: fail("source rewrite recommendations")
 before,after=readj(ROOT/"live-before.json"),readj(ROOT/"live-after.json")
 for live in (before,after):
  if live.get("repository")!="snapetech-org/slskdN" or live.get("pullRequest")!=409 or live.get("state")!="OPEN" or live.get("draft") is not True or live.get("merged") is not False: fail("PR state")
  for f,v in (("headRefOid",HEAD),("branchRefOid",HEAD),("pullRefOid",HEAD),("headRefName",BRANCH),("baseRefName","main"),("baseRefOid","f25d263a2a7cdb2c8f76c40c346cb10f749a9356")):
   if live.get(f)!=v: fail("PR ref "+f)
 if any(before.get(k)!=after.get(k) for k in set(before)|set(after) if k!="attestedUtc"): fail("PR refs changed during review")
 summary=readj(ROOT/"summary.json")
 if summary.get("dispositions")!={"accept-current":183,"correct":69,"hold":48} or summary.get("candidateFreeInputManifestSha256")!=sha((INPUT/"manifest.json").read_bytes()) or summary.get("candidateFreeInputChecksumListSha256")!=sha((INPUT/"PACKET-SHA256SUMS.txt").read_bytes()) or summary.get("selectionBoundarySha256")!=sha((INPUT/"selection-boundary.jsonl").read_bytes()): fail("summary linkage")
 manifest=readj(ROOT/"manifest.json")
 if manifest.get("head")!=HEAD or manifest.get("tree")!=TREE or manifest.get("window")!="W76" or manifest.get("sourceCount")!=25 or manifest.get("cellCount")!=300: fail("manifest pin/coverage")
 if manifest.get("candidateFreeInputManifestSha256")!=summary.get("candidateFreeInputManifestSha256") or manifest.get("dispositions")!=summary.get("dispositions"): fail("manifest/input lineage")
 entries={x["path"]:x for x in manifest["files"]}
 actual_files={p.name for p in ROOT.iterdir() if p.is_file() and p.name not in {"manifest.json","SHA256SUMS.txt"}}
 if set(entries)!=actual_files: fail("manifest file set")
 for name,e in entries.items():
  p=ROOT/name
  if p.stat().st_size!=e["bytes"] or sha(p.read_bytes())!=e["sha256"]: fail("manifest digest "+name)
 sums={}
 for line in (ROOT/"SHA256SUMS.txt").read_text().splitlines():
  if line.strip():
   h,n=line.split("  ",1); sums[n]=h
 if set(sums)!=actual_files|{"manifest.json"}: fail("checksum inventory")
 for name,h in sums.items():
  if sha((ROOT/name).read_bytes())!=h: fail("checksum "+name)
 print(json.dumps({"result":"PASS","head":HEAD,"tree":TREE,"sourceCount":25,"localeCount":12,"cellCount":300,
 "acceptCurrent":counts["accept-current"],"correct":counts["correct"],"textFreeHolds":counts["hold"],
 "callerlessSources":len(callerless),"callerlessCells":len(callerless)*12,"proposalTokenMismatches":0,
 "inputVerifier":"PASS","PR":"OPEN/DRAFT/CLEAN at exact head","checksums":len(sums)},ensure_ascii=False))
if __name__=="__main__": main()

