#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
EV=Path(__file__).resolve().parent
sha=lambda s:hashlib.sha256(s.encode("utf-8")).hexdigest()
corrections=[json.loads(x) for x in (EV/"cross-review/corrections.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
ledger=[json.loads(x) for x in (EV/"cross-review/cross-review-ledger.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
expected={r['locale']:r['catalogFileSha256'] for r in ledger if r['crossDisposition']!='hold-text-free'}
data={}
for locale,digest in expected.items():
 p=ROOT/f"src/web/public/locales/{locale}.json"; raw=p.read_bytes(); assert hashlib.sha256(raw).hexdigest()==digest
 data[locale]=json.loads(raw)
assert len(corrections)==72
for row in corrections:
 values=data[row['locale']]; key=row['sourceText']; current=values[key]
 assert current==row['currentTarget'] and sha(current)==row['currentTargetSha256']
# This routine is documented for reproducing the base-head application only. It intentionally refuses
# a second run after catalog cells changed because each exact-current hash guard will fail.
for row in corrections:data[row['locale']][row['sourceText']]=row['recommendedTarget']
for locale,values in data.items():
 (ROOT/f"src/web/public/locales/{locale}.json").write_text(json.dumps(values,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({'preflight':'PASS','updatedCells':len(corrections),'locales':len(data)}))
