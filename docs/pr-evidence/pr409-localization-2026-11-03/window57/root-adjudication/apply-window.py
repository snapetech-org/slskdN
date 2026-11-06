#!/usr/bin/env python3
"""Apply the sealed slskdN PR #409 W57 root ledger idempotently."""
import json, pathlib, subprocess, sys
EXPECTED_HEAD = "6b09b3c7bf7de69c316ba3e2503dc450004c9b59"
ledger_path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "root-adjudication.jsonl")
repo = pathlib.Path.cwd()
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
if head != EXPECTED_HEAD: raise SystemExit(f"expected exact PR head {EXPECTED_HEAD}; found {head}")
rows = [json.loads(line) for line in ledger_path.read_text().splitlines() if line.strip()]
updates = {}
for row in rows:
    if not row["changed"]: continue
    p = repo / row["catalogPath"]; data = json.loads(p.read_text()); current = data[row["sourceKey"]]
    if current == row["currentTarget"]: data[row["sourceKey"]] = row["rootTarget"]; updates[p] = data
    elif current != row["rootTarget"]: raise SystemExit(f"stale catalog value at {row['catalogPath']}:{row['sourceKey']}")
for p, data in updates.items(): p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
for row in rows:
    data=json.loads((repo/row["catalogPath"]).read_text())
    if data[row["sourceKey"]] != row["rootTarget"]: raise SystemExit(f"readback mismatch: {row['sourceKey']}")
print(f"Applied/read back {len(rows)} cells; wrote {len(updates)} catalog files.")
