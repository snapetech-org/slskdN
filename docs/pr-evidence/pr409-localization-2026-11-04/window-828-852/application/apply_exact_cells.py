#!/usr/bin/env python3
"""Apply a sealed catalog plan with preimage, cell-hash, and key-order guards."""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path


HEAD = "4120c9637e71466dc98d51a5a342dee199a1e004"
TREE = "063b62f268eb81253d2b9b4c77ad045c2f25a394"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text_sha(value: str) -> str:
    return sha(value.encode("utf-8"))


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def canon(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--input-current-cells", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo, plan_path, ledger_path, input_current_path, output = (args.repo.resolve(), args.plan.resolve(), args.ledger.resolve(),
                                                                  args.input_current_cells.resolve(), args.output.resolve())
    output.mkdir(parents=True, exist_ok=True)

    import subprocess
    git = lambda *cmd: subprocess.check_output(["git", "-C", str(repo), *cmd], text=True).strip()
    if git("rev-parse", "HEAD") != HEAD or git("rev-parse", "HEAD^{tree}") != TREE:
        raise SystemExit("FAIL: source worktree is not at exact pinned head/tree")
    if git("status", "--porcelain=v1"):
        raise SystemExit("FAIL: source worktree must be clean before apply")

    plan = read_rows(plan_path)
    ledger = read_rows(ledger_path)
    input_current = read_rows(input_current_path)
    ledger_by_key = {(row["sourceId"], row["locale"]): row for row in ledger}
    input_by_key = {(row["sourceId"], row["locale"]): row for row in input_current}
    if len(plan) != 63 or len(ledger) != 300 or len(ledger_by_key) != 300:
        raise SystemExit("FAIL: unexpected plan or cross-ledger cell count")
    if len({(row["sourceId"], row["locale"]) for row in plan}) != 63:
        raise SystemExit("FAIL: duplicate plan cell")
    plan_keys = {(row["sourceId"], row["locale"]) for row in plan}
    proposed_keys = {key for key, row in ledger_by_key.items() if row["crossDisposition"] == "propose"}
    if plan_keys != proposed_keys:
        raise SystemExit("FAIL: selected plan does not match cross-review proposal set")
    for row in plan:
        cross = ledger_by_key[(row["sourceId"], row["locale"])]
        if (cross["crossDisposition"], cross["currentTargetSha256"], cross["crossTargetSha256"]) != (
            "propose", row["currentTargetSha256"], row["targetSha256"]
        ):
            raise SystemExit("FAIL: selected plan/cross ledger mismatch")

    by_file: dict[str, list[dict]] = collections.defaultdict(list)
    for row in plan:
        if row["head"] != HEAD or row["tree"] != TREE or row["operation"] != "replace-current-catalog-value":
            raise SystemExit("FAIL: plan pin/operation mismatch")
        if text_sha(row["target"]) != row["targetSha256"]:
            raise SystemExit("FAIL: target hash mismatch")
        by_file[row["catalogPath"]].append(row)

    replacements: dict[Path, tuple[bytes, bytes, dict]] = {}
    for relative, items in by_file.items():
        path = repo / relative
        original = path.read_bytes()
        pre_sha = sha(original)
        pre_blob = blob_sha(original)
        expected_file_shas = {row["catalogFileSha256"] for row in items}
        expected_blobs = {row["catalogGitBlob"] for row in items}
        if len(expected_file_shas) != 1 or len(expected_blobs) != 1:
            raise SystemExit("FAIL: plan file guards disagree for " + relative)
        if pre_sha != next(iter(expected_file_shas)) or pre_blob != next(iter(expected_blobs)):
            raise SystemExit("FAIL: catalog preimage guard mismatch for " + relative)
        text = original.decode("utf-8")
        data = json.loads(text)
        if len(data) != 6176:
            raise SystemExit("FAIL: catalog entry count mismatch for " + relative)
        keys_before = list(data.keys())
        keys_before_sha = sha(canon(keys_before))
        updated_text = text
        for row in items:
            key = row["catalogKey"]
            if key not in data or text_sha(data[key]) != row["currentTargetSha256"]:
                raise SystemExit(f"FAIL: current value guard mismatch for {relative}:{key}")
            old_pair = json.dumps(key, ensure_ascii=False) + ": " + json.dumps(data[key], ensure_ascii=False)
            new_pair = json.dumps(key, ensure_ascii=False) + ": " + json.dumps(row["target"], ensure_ascii=False)
            if updated_text.count(old_pair) != 1:
                raise SystemExit(f"FAIL: expected one exact JSON value for {relative}:{key}")
            updated_text = updated_text.replace(old_pair, new_pair, 1)
            data[key] = row["target"]
        post_bytes = updated_text.encode("utf-8")
        parsed_after = json.loads(post_bytes.decode("utf-8"))
        if list(parsed_after.keys()) != keys_before or sha(canon(list(parsed_after.keys()))) != keys_before_sha:
            raise SystemExit("FAIL: catalog key order changed for " + relative)
        for row in items:
            if text_sha(parsed_after[row["catalogKey"]]) != row["targetSha256"]:
                raise SystemExit(f"FAIL: proposed catalog readback mismatch for {relative}:{row['catalogKey']}")
        replacements[path] = (original, post_bytes, {
            "path": relative, "entryCount": len(parsed_after),
            "preimageSha256": pre_sha, "postimageSha256": sha(post_bytes),
            "preimageGitBlob": pre_blob, "postimageGitBlob": blob_sha(post_bytes),
            "keyOrderSha256": keys_before_sha, "keyOrderUnchanged": True,
            "changedEntries": len(items),
        })

    for path, (_, post_bytes, _) in replacements.items():
        path.write_bytes(post_bytes)

    catalog_by_path = {relative: json.loads((repo / relative).read_text(encoding="utf-8")) for relative in by_file}
    post_by_path = {item["path"]: item for item in (value[2] for value in replacements.values())}
    readback, summary_by_locale = [], collections.defaultdict(collections.Counter)
    for row in sorted(ledger, key=lambda r: (r["continuationRank"], LOCALES.index(r["locale"]))):
        key = (row["sourceId"], row["locale"])
        disposition = row["crossDisposition"]
        if disposition == "hold":
            source_cell = input_by_key[key]
            hold_data = json.loads((repo / source_cell["catalogPath"]).read_text(encoding="utf-8"))
            actual_sha = text_sha(hold_data[source_cell["catalogKey"]])
            if actual_sha != row["currentTargetSha256"]:
                raise SystemExit(f"FAIL: callerless held value changed for {row['sourceId']}/{row['locale']}")
            if row["productionCallerCount"] != 0:
                raise SystemExit("FAIL: held cell has caller")
            result = {
                "schemaVersion": 1, "continuationRank": row["continuationRank"], "sourceId": row["sourceId"],
                "sourceSha256": row["sourceSha256"], "locale": row["locale"],
                "crossDisposition": "hold", "currentTargetSha256": row["currentTargetSha256"],
                "expectedTargetSha256": row["currentTargetSha256"], "readbackTargetSha256": actual_sha,
                "callerContextSha256": row["callerContextSha256"], "productionCallerCount": 0,
                "catalogTextIncluded": False, "readbackTextIncluded": False,
            }
        else:
            catalog_path, catalog_key = row["catalogPath"], row["catalogKey"]
            data = catalog_by_path[catalog_path]
            actual_target = data[catalog_key]
            actual_sha = text_sha(actual_target)
            expected_sha = row["crossTargetSha256"] if disposition == "propose" else row["currentTargetSha256"]
            if actual_sha != expected_sha:
                raise SystemExit(f"FAIL: readback mismatch for {row['sourceId']}/{row['locale']}")
            result = {
                "schemaVersion": 1, "continuationRank": row["continuationRank"], "sourceId": row["sourceId"],
                "sourceText": row["sourceText"], "sourceSha256": row["sourceSha256"], "locale": row["locale"],
                "crossDisposition": disposition, "currentTargetSha256": row["currentTargetSha256"],
                "expectedTargetSha256": expected_sha, "readbackTarget": actual_target,
                "readbackTargetSha256": actual_sha, "callerContextSha256": row["callerContextSha256"],
                "productionCallerCount": row["productionCallerCount"], "catalogPath": catalog_path,
                "catalogKey": catalog_key, "catalogFilePreimageSha256": row["catalogFileSha256"],
                "catalogFilePostimageSha256": post_by_path[catalog_path]["postimageSha256"],
            }
        summary_by_locale[row["locale"]][disposition] += 1
        readback.append(result)
    if len(readback) != 300:
        raise SystemExit("FAIL: application readback must cover 300 cells")

    postimage = list(post_by_path.values())
    app_summary = {
        "artifact": "slskdN PR #409 W78 localization application readback",
        "schemaVersion": 1, "window": "W78", "headBeforeApply": HEAD, "treeBeforeApply": TREE,
        "productChangeCount": len(plan), "retainedCurrentCount": 225, "callerlessHashOnlyHoldCount": 12,
        "readbackCellCount": len(readback), "catalogCount": len(postimage),
        "catalogKeyCountPerLocale": 6176, "catalogKeyOrderUnchanged": all(item["keyOrderUnchanged"] for item in postimage),
        "cellsByLocale": {locale: dict(summary_by_locale[locale]) for locale in LOCALES},
        "repositoryEditsOutsideLocaleCatalogs": False,
    }
    write_rows(output / "application-readback-300-cells.jsonl", readback)
    (output / "catalog-preimage-and-postimage.json").write_text(json.dumps({"catalogs": sorted(postimage,key=lambda x:x["path"])},indent=2)+"\n",encoding="utf-8")
    (output / "application-summary.json").write_text(json.dumps(app_summary,indent=2)+"\n",encoding="utf-8")
    result = {
        "artifact": "W78 exact catalog write result", "appliedUtc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
        "headBeforeApply": HEAD, "treeBeforeApply": TREE, "selectedProposalCount": len(plan),
        "catalogPathsChanged": sorted(by_file), "catalogs": sorted(postimage,key=lambda x:x["path"]),
        "readbackCellCount": len(readback), "readbackResult": "PASS", "testsBuildsScansOrCiRun": False,
    }
    (output / "application-write-result.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"result":"PASS","selected":len(plan),"readback":len(readback),"catalogs":len(postimage),"paths":sorted(by_file)},indent=2))


if __name__ == "__main__":
    main()
