import collections, hashlib, json, re
from pathlib import Path
root=Path(__file__).resolve().parent
rows=[json.loads(l) for l in (root/"cross-audit-ledger.jsonl").read_text().splitlines() if l.strip()]
assert len(rows)==300 and len({(r["continuationRank"],r["locale"]) for r in rows})==300
assert all(r["head"]=="3fbcea3185c02efca7c45d03a195acf488e70587" and r["tree"]=="95604b428133b5e52247c1f3f00900c2c7d5192f" for r in rows)
assert all(hashlib.sha256(r["selectedTarget"].encode()).hexdigest()==r["selectedTargetSha256"] for r in rows if r["selectedForApplication"])
assert sum(r["selectedForApplication"] for r in rows)==84
assert collections.Counter(r["disposition"] for r in rows)=={"accept-current":216,"correction":57,"refinement":27}
assert all(r["placeholderCheck"] and r["markupCheck"] and r["numericTokenCheck"] for r in rows)
assert all(r["selectedForApplication"]==(r["selectedTarget"] is not None) for r in rows)
summary=json.loads((root/"summary.json").read_text())
assert summary["cellCount"]==300 and summary["selectedChanges"]==84 and summary["disagreementCount"]==83
print("cross-audit evidence verified: 300 cells, 84 selected changes, 83 reconciled disagreements, 0 holds")
