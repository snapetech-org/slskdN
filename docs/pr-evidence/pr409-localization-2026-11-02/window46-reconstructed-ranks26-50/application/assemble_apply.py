from __future__ import annotations

import collections
import hashlib
import json
import subprocess
from pathlib import Path


EVIDENCE = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[5]
HEAD = "31544a6ef15db2f8481dd76aa9c10844ec3164ba"
TREE = "fe94582c3e13f0f567fbfa6c3abac6e8558ba17d"
LEDGER = EVIDENCE / "adjudication" / "final-adjudication-ledger.jsonl"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]


def sha(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


assert git("rev-parse", "HEAD") == HEAD
assert git("rev-parse", "HEAD^{tree}") == TREE
status = git("status", "--short").splitlines()
assert all(line.startswith("?? docs/pr-evidence/pr409-localization-2026-11-02/window46-reconstructed-ranks26-50") for line in status), status

snapshot = json.loads((EVIDENCE / "application" / "live-prs-before-apply.json").read_text(encoding="utf-8"))
assert snapshot["allSevenStatesAndHeadsMatchExpected"] is True
assert len(snapshot["pullRequests"]) == 7
slskdn_pr = next(row for row in snapshot["pullRequests"] if row["number"] == 409)
assert slskdn_pr["state"] == "open" and slskdn_pr["draft"] is True
assert slskdn_pr["head"] == HEAD

rows = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]
assert len(rows) == 300
assert len({(row["selectionRank"], row["locale"]) for row in rows}) == 300
counts = collections.Counter(row["adjudicatedDisposition"] for row in rows)
assert counts == {"accept-current": 220, "accept-reviewed-correction": 38, "adopt-crossreview-revision": 6, "hold": 36}

catalogs: dict[str, dict] = {}
catalog_bytes: dict[str, bytes] = {}
catalog_path: dict[str, str] = {}
style: dict[str, str] = {}
preapply = []
for locale in LOCALES:
    path = f"src/web/public/locales/{locale}.json"
    raw = (REPO / path).read_bytes()
    catalog = json.loads(raw)
    compact = json.dumps(catalog, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if raw == compact:
        style[locale] = "compact-no-final-newline"
    elif raw == compact + b"\n":
        style[locale] = "compact-with-final-newline"
    else:
        raise AssertionError(f"unexpected JSON serialization style: {path}")
    catalogs[locale] = catalog
    catalog_bytes[locale] = raw
    catalog_path[locale] = path
    keys = list(catalog)
    preapply.append({
        "locale": locale,
        "path": path,
        "keyCount": len(keys),
        "fileSha256": sha(raw),
        "gitBlobOid": git("rev-parse", f"{HEAD}:{path}"),
        "orderedKeysSha256": sha("\n".join(keys)),
        "keySetSha256": sha("\n".join(sorted(keys))),
        "serializationStyle": style[locale],
    })

plan = []
for row in rows:
    locale = row["locale"]
    sid = row["sourceId"]
    source_text = row["sourceText"]
    current = catalogs[locale][source_text]
    assert row["locale"] in LOCALES
    assert row["exactHead"] == HEAD and row["exactTree"] == TREE
    assert current == row["currentTarget"] and sha(current) == row["currentTargetSha256"]
    assert sha(row["sourceText"]) == row["sourceSha256"]
    assert row["catalogPath"] == catalog_path[locale]
    assert row["catalogFileSha256"] == sha(catalog_bytes[locale])
    assert row["catalogBlobOid"] == git("rev-parse", f"{HEAD}:{catalog_path[locale]}")
    disposition = row["adjudicatedDisposition"]
    if disposition == "accept-current":
        final = current
        assert row["finalTarget"] == current
    elif disposition in {"accept-reviewed-correction", "adopt-crossreview-revision"}:
        final = row["finalTarget"]
        assert final == row["crossReviewTarget"]
        assert final is not None and sha(final) == row["finalTargetSha256"]
        assert row["placeholderMarkupParity"] == "exact"
        assert row["finalProtectedLiteralMismatches"] == []
    elif disposition == "hold":
        assert row["finalTarget"] is None
        final = current
    else:
        raise AssertionError(f"unknown disposition: {disposition}")
    plan.append({
        "exactHead": HEAD,
        "exactTree": TREE,
        "selectionRank": row["selectionRank"],
        "selectionRankBasis": row["selectionRankBasis"],
        "sourceOrdinal": row["sourceOrdinal"],
        "sourceId": sid,
        "sourceText": row["sourceText"],
        "sourceSha256": row["sourceSha256"],
        "locale": locale,
        "catalogPath": catalog_path[locale],
        "callerRefsSourceId": row["callerRefsSourceId"],
        "callerUseStatus": row["callerUseStatus"],
        "callerContextSummary": row["callerContextSummary"],
        "adjudicatedDisposition": disposition,
        "primaryDisposition": row["primaryDisposition"],
        "crossReviewDisposition": row["crossReviewDisposition"],
        "currentTarget": current,
        "currentTargetSha256": row["currentTargetSha256"],
        "finalTarget": final,
        "finalTargetSha256": sha(final),
        "heldTarget": disposition == "hold",
        "changed": final != current,
        "rationale": row["adjudicationRationale"],
    })

assert sum(item["changed"] for item in plan) == 44
write_jsonl(EVIDENCE / "application" / "catalog-preapply-pins.jsonl", preapply)
write_jsonl(EVIDENCE / "application" / "apply-plan.jsonl", plan)

for item in plan:
    if item["changed"]:
        catalogs[item["locale"]][item["sourceText"]] = item["finalTarget"]

for locale in LOCALES:
    path = REPO / catalog_path[locale]
    keys = list(json.loads(catalog_bytes[locale]))
    assert keys == list(catalogs[locale])
    compact = json.dumps(catalogs[locale], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path.write_bytes(compact + (b"\n" if style[locale] == "compact-with-final-newline" else b""))

readback = []
for item in plan:
    cat = json.loads((REPO / item["catalogPath"]).read_text(encoding="utf-8"))
    actual = cat[item["sourceText"]]
    assert actual == item["finalTarget"]
    assert sha(actual) == item["finalTargetSha256"]
    readback.append({**item, "readbackTarget": actual, "readbackTargetSha256": sha(actual), "readbackMatches": True})
write_jsonl(EVIDENCE / "application" / "apply-readback.jsonl", readback)

postapply = []
for locale in LOCALES:
    path = catalog_path[locale]
    raw = (REPO / path).read_bytes()
    cat = json.loads(raw)
    keys = list(cat)
    assert len(keys) == 6170
    assert keys == list(json.loads(catalog_bytes[locale]))
    postapply.append({
        "locale": locale,
        "path": path,
        "keyCount": len(keys),
        "fileSha256": sha(raw),
        "gitBlobOid": git("hash-object", path),
        "orderedKeysSha256": sha("\n".join(keys)),
        "keySetSha256": sha("\n".join(sorted(keys))),
        "serializationStyle": style[locale],
    })

summary = {
    "repository": "snapetech-org/slskdN",
    "pullRequest": 409,
    "sourceHead": HEAD,
    "sourceTree": TREE,
    "window": "W46 reconstructed ranks 26–50; historical source ordinal unavailable",
    "sourceIds": 25,
    "cells": 300,
    "locales": 12,
    "dispositions": dict(sorted(counts.items())),
    "changedCells": sum(item["changed"] for item in plan),
    "retainedCurrentCells": counts["accept-current"],
    "heldCells": counts["hold"],
    "holdRanks": [37, 42, 49],
    "readbackCells": len(readback),
    "allReadbackMatches": True,
    "catalogs": postapply,
    "catalogKeySetParity": len({x["keySetSha256"] for x in postapply}) == 1,
    "perLocaleKeyOrderPreserved": True,
    "nativeSpeakerApproval": False,
    "headedBrowserReview": False,
    "testsBuildScansCiRun": False,
    "workflowFilesTouched": False,
    "mergeReleaseOrTag": False,
}
write_json(EVIDENCE / "application" / "post-apply-catalog-attestation.json", summary)
write_json(EVIDENCE / "application" / "apply-summary.json", {
    key: value for key, value in summary.items() if key != "catalogs"
})
print(json.dumps({key: value for key, value in summary.items() if key != "catalogs"}, ensure_ascii=False, indent=2))
