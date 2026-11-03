#!/usr/bin/env python3
"""Verify the complete portable slskdN W70 review/application evidence."""
from pathlib import Path
import hashlib,json,subprocess,sys
W=Path(__file__).resolve().parent
R=W.parents[3]
def die(s): raise SystemExit("FAIL: "+s)
def sha(b): return hashlib.sha256(b).hexdigest()
sums=W/"SHA256SUMS.txt"
listed={}
for line in sums.read_text(encoding="utf-8").splitlines():
 if line.strip():
  h,n=line.split("  ",1)
  if n in listed: die("duplicate checksum "+n)
  listed[n]=h
actual={p.relative_to(W).as_posix() for p in W.rglob("*") if p.is_file() and p!=sums}
if set(listed)!=actual: die("root checksum inventory mismatch")
for n,h in listed.items():
 if sha((W/n).read_bytes())!=h: die("root checksum mismatch "+n)
m=json.loads((W/"manifest.json").read_text(encoding="utf-8"))
rows={x["path"]:x for x in m["files"]}
if set(rows)!=actual-{"manifest.json"}: die("manifest inventory mismatch")
for n,x in rows.items():
 b=(W/n).read_bytes()
 if len(b)!=x["bytes"] or sha(b)!=x["sha256"]: die("manifest mismatch "+n)
# Require the three standalone sealed packets to be byte-identical copies from the full cross packet.
def same(a,b):
 aa={p.relative_to(a).as_posix():p for p in a.rglob("*") if p.is_file()}
 bb={p.relative_to(b).as_posix():p for p in b.rglob("*") if p.is_file()}
 if set(aa)!=set(bb): die("packet copy inventory mismatch "+str(a))
 for k in aa:
  if aa[k].read_bytes()!=bb[k].read_bytes(): die("packet copy mismatch "+k)
same(W/"candidate-free-packet",W/"cross-audit"/"candidate-free-packet")
same(W/"primary-packet",W/"cross-audit"/"primary-packet")
same(W/"blind-packet",W/"cross-audit"/"blind-packet")
# Check the nested cross packet's sealed root checksums as a portable file bundle.
c=W/"cross-audit"; csum={}
for line in (c/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
 if line.strip():
  h,n=line.split("  ",1)
  if n in csum: die("duplicate cross checksum "+n)
  csum[n]=h
cactual={p.relative_to(c).as_posix() for p in c.rglob("*") if p.is_file() and p!=c/"SHA256SUMS.txt"}
if set(csum)!=cactual: die("cross packet checksum inventory")
for n,h in csum.items():
 if sha((c/n).read_bytes())!=h: die("cross packet checksum "+n)
allow="--allow-uncommitted" in sys.argv
cmd=[sys.executable,str(W/"application"/"verify_application.py")]+(["--allow-uncommitted"] if allow else [])
run=subprocess.run(cmd,cwd=R,text=True,capture_output=True)
if run.returncode: die("application verifier failed: "+run.stdout+run.stderr)
# Verify every evidence file is present byte-for-byte in current committed Git tree.
head=subprocess.check_output(["git","-C",str(R),"rev-parse","HEAD"],text=True).strip()
if not allow:
 tracked={x.decode() for x in subprocess.check_output(["git","-C",str(R),"ls-tree","-r","--name-only",head,"--",W.relative_to(R).as_posix()]).splitlines()}
 expected={str((W.relative_to(R)/p).as_posix()) for p in actual}
 if tracked!=expected|{(W.relative_to(R)/"SHA256SUMS.txt").as_posix()}: die("committed evidence path inventory")
 for rel in expected|{(W.relative_to(R)/"SHA256SUMS.txt").as_posix()}:
  disk=(R/rel).read_bytes()
  blob=subprocess.check_output(["git","-C",str(R),"show",f"{head}:{rel}"])
  if blob!=disk: die("committed evidence blob mismatch "+rel)
print(json.dumps({"result":"PASS","head":head,"files":len(actual),"manifestFiles":len(rows),"crossFiles":len(cactual),"applicationVerifier":"PASS","committedBlobs":"PENDING" if allow else "PASS"},indent=2))
print(run.stdout,end="")
