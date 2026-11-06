#!/usr/bin/env python3
"""Validate checksums and candidate coverage in this immutable review packet."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
checks={}
for line in (root/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
 d,n=line.split("  ",1); checks[n]=d
for n,d in checks.items():
 p=root/n
 if not p.is_file() or sha(p.read_bytes())!=d: raise SystemExit(f"FAIL {n}")
rows=[json.loads(x) for x in (root/"independent-decisions.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
report=json.loads((root/"verification-report.json").read_text(encoding="utf-8"))
if len(rows)!=41 or len({r["id"] for r in rows})!=41: raise SystemExit("FAIL row coverage")
if report["dispositions"]!={"accept":40,"refine":1} or report["reviewedCandidates"]!=41: raise SystemExit("FAIL disposition totals")
print("PASS: checksums and 41-row decision coverage")
