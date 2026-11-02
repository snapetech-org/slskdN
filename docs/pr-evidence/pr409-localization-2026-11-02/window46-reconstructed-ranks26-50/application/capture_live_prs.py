from __future__ import annotations

import datetime
import json
import subprocess
from pathlib import Path


EXPECTED = {
    ("SeerrNG", 418): ("open", True, "9242898e23f7f25d515d10b5b0b51df322e395fb"),
    ("ChaptarrNG", 190): ("open", True, "a9a74f6ba733e8c1f06a2d260bd802d4fde2da0e"),
    ("QuestarrNG", 155): ("open", False, "be131f2d42988bb8f4a271e4df428985da15b53b"),
    ("ROMarrNG", 70): ("open", True, "8e3820252b0c362e18e421b3a73e7ff1478d32a0"),
    ("slskR", 204): ("open", True, "5f295feea832b3078c52d92d9268cd6446f804a5"),
    ("slskdN", 409): ("open", True, "31544a6ef15db2f8481dd76aa9c10844ec3164ba"),
    ("TorrentNG", 243): ("open", True, "11ff6fa2618e842e92716b7e92867769200e32e5"),
}
rows = []
for (repo, number), expected in EXPECTED.items():
    raw = subprocess.check_output(
        ["gh", "api", f"repos/snapetech-org/{repo}/pulls/{number}", "--jq", "{state,draft,head:.head.sha,ref:.head.ref,url:.html_url}"],
        text=True,
    )
    item = json.loads(raw)
    assert (item["state"], item["draft"], item["head"]) == expected, (repo, number, item)
    rows.append({"repository": f"snapetech-org/{repo}", "number": number, **item})
snapshot = {
    "capturedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "allSevenStatesAndHeadsMatchExpected": True,
    "pullRequests": rows,
}
out = Path(__file__).with_name("live-prs-before-apply.json")
out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(out)
