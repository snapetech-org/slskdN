#!/usr/bin/env python3
import hashlib, json
from pathlib import Path
root=Path(__file__).resolve().parent
source=json.loads((root/"candidate-free-input.json").read_text())
rows=[json.loads(x) for x in (root/"blind-translation-review.jsonl").read_text().splitlines() if x.strip()]
expected=["es","zh-Hans","hi","de","ja","fr","pt-BR","ar","ko","zh-Hant","vi","id"]
text=source["proposedEnglishSource"]; sha=hashlib.sha256(text.encode()).hexdigest()
assert sha==source["proposedSourceSha256"] and source["proposedSourceId"]=="src_"+sha[:16]
assert [r["locale"] for r in rows]==expected and len(rows)==12
assert all(r["source"]==text and r["sourceId"]==source["proposedSourceId"] for r in rows)
assert all(r["modePlaceholderCount"]==1 and r["target"].count("{mode}")==1 for r in rows)
assert all(r["signaturePlaceholderCount"]==1 and r["target"].count("{signature}")==1 for r in rows)
assert all("Enforce" not in r["target"] and "ed25519" not in r["target"] and "<code>" not in r["target"] for r in rows)
assert source["protectedNodes"]["mode"]["catalogContainsLiteral"] is False and source["protectedNodes"]["signature"]["catalogContainsLiteral"] is False
assert "<bdi dir=\"ltr\" lang=\"en\">Enforce</bdi>" in source["protectedNodes"]["mode"]["rendering"]
assert "<bdi dir=\"ltr\" lang=\"en\"><code>" in source["protectedNodes"]["signature"]["rendering"]
print("PASS: source hash/id, 12 locale cells, one mode/signature placeholder each, exact protected nodes outside catalog values")
