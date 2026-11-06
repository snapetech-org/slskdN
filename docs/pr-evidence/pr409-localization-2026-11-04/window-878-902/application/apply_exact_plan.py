#!/usr/bin/env python3
"""Apply the sealed W80 plan after exact catalog preimage checks."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import subprocess
from pathlib import Path

HEAD = "7a1ca27fd0519674c3b42a3e3df3638b0f671567"
TREE = "b3525218d0f9676c88c4991e78775d113f18b7d9"
PLAN_SHA256 = "b6a55ca7c871b87977879dc7dbea043d9fb7751ba37619e4f2fef09cb27bb0fa"
ROOT_REVIEW_SHA256 = "2e85d1c162401e8b2538fb53864583bf1fb5f231aafbf0afd08c7aba62333ef7"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
LOCALE_PATH = "src/web/public/locales/{}.json"
EVIDENCE = "docs/pr-evidence/pr409-localization-2026-11-04/window-878-902"


def need(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("FAIL: " + message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def read_rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--apply", action="store_true", help="write the 81 guarded targets")
    args = parser.parse_args()
    repo = args.repo.resolve()
    evidence = repo / EVIDENCE
    app = evidence / "application"
    plan_path = app / "application-plan.jsonl"
    plan_bytes = plan_path.read_bytes()
    need(sha(plan_bytes) == PLAN_SHA256, "sealed plan SHA-256")
    need(subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip() == HEAD,
         "application must start at pinned W80 source head")
    need(subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"], text=True).strip() == TREE,
         "pinned W80 source tree")
    need(not subprocess.run(["git", "-C", str(repo), "diff", "--quiet", "HEAD", "--", "src/web/public/locales"],
                            check=False).returncode, "locale catalogs have no pre-existing working-tree changes")

    root_review_dir = evidence / "review-packet/root-manual-review"
    root_review = json.loads((root_review_dir / "review.json").read_text(encoding="utf-8"))
    need(sha((root_review_dir / "review.json").read_bytes()) == ROOT_REVIEW_SHA256, "root review attestation SHA-256")
    need(root_review["crossProposalPlanSha256"] == PLAN_SHA256 and root_review["selectedChangeCount"] == 81
         and root_review["keepCount"] == 219 and root_review["holdCount"] == 0,
         "root review attestation binds this exact plan and counts")

    plan = read_rows(plan_path)
    need(len(plan) == 81, "81 selected rows")
    keys = [(r["continuationRank"], r["locale"]) for r in plan]
    need(len(set(keys)) == 81, "unique rank/locale plan rows")
    need(all(r["window"] == "W80" and 878 <= r["continuationRank"] <= 902
             and r["locale"] in LOCALES and r["planOnly"] is True and r["appliedToRepository"] is False
             for r in plan), "W80 proposal plan shape")
    need(all(r["productionCallerCount"] > 0 for r in plan), "every selected row has a pinned production caller")
    proposals = {(r["locale"], r["continuationRank"]): r for r in plan}
    catalogs: dict[str, dict[str, str]] = {}
    before_objects: dict[str, dict[str, str]] = {}
    before_raw: dict[str, bytes] = {}
    before_order: dict[str, list[str]] = {}
    before_hashes: dict[str, dict[str, str]] = {}

    for locale in LOCALES:
        relative = LOCALE_PATH.format(locale)
        raw = subprocess.check_output(["git", "-C", str(repo), "show", f"{HEAD}:{relative}"])
        need(subprocess.check_output(["git", "-C", str(repo), "hash-object", "--stdin"], input=raw).decode().strip()
             == git_blob(raw), f"Git blob preimage for {locale}")
        obj = json.loads(raw.decode("utf-8"))
        need(len(obj) == 6176, f"ordered catalog entry count for {locale}")
        need(raw.endswith(b"\n") and json.dumps(obj, ensure_ascii=False, indent=2) + "\n" == raw.decode("utf-8"),
             f"catalog serialization format for {locale}")
        need(not subprocess.run(["git", "-C", str(repo), "diff", "--quiet", "HEAD", "--", relative],
                                check=False).returncode, f"clean catalog preimage for {locale}")
        catalogs[locale] = obj
        before_objects[locale] = obj.copy()
        before_raw[locale] = raw
        before_order[locale] = list(obj)
        before_hashes[locale] = {"sha256": sha(raw), "gitBlob": git_blob(raw), "bytes": len(raw)}

    for r in plan:
        locale = r["locale"]
        path = LOCALE_PATH.format(locale)
        raw = before_raw[locale]
        value = catalogs[locale].get(r["catalogKey"])
        need(r["catalogPath"] == path, "locale path binding")
        need(sha(raw) == r["catalogFileSha256"] and git_blob(raw) == r["catalogGitBlob"],
             f"exact catalog file preimage: {locale}")
        need(value == r["currentTarget"] and sha(value.encode("utf-8")) == r["currentTargetSha256"],
             f"exact target preimage: {locale}/{r['continuationRank']}")
        need(r["target"] != value and sha(r["target"].encode("utf-8")) == r["targetSha256"]
             == r["crossTargetSha256"], f"exact selected target hash: {locale}/{r['continuationRank']}")
        tokens = r["tokenCheck"]["proposal"]
        need(tokens["placeholderParity"] and tokens["markupParity"] and tokens["numericTokensPreserved"]
             and tokens["protectedLiteralsPreserved"], f"selected target token parity: {locale}/{r['continuationRank']}")
        catalogs[locale][r["catalogKey"]] = r["target"]

    if not args.apply:
        print(json.dumps({"result": "PREFLIGHT PASS", "planSha256": PLAN_SHA256,
                          "selectedTargets": len(plan), "locales": len(LOCALES)}, indent=2))
        return

    write_result = {"result": "APPLIED", "window": "W80", "baseHead": HEAD, "baseTree": TREE,
                    "applyPlanSha256": PLAN_SHA256, "selectedTargets": len(plan), "catalogCount": len(LOCALES),
                    "files": {}}
    postimages_dir = app / "postimages"
    postimages_dir.mkdir(parents=True, exist_ok=True)
    for locale in LOCALES:
        relative = LOCALE_PATH.format(locale)
        serialized = (json.dumps(catalogs[locale], ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        repo_path = repo / relative
        repo_path.write_bytes(serialized)
        readback = repo_path.read_bytes()
        need(readback == serialized, f"catalog write readback {locale}")
        need(list(json.loads(readback.decode("utf-8"))) == before_order[locale], f"catalog key order {locale}")
        postimages_dir.joinpath(locale + ".json").write_bytes(readback)
        plan_rows = [r for r in plan if r["locale"] == locale]
        write_result["files"][relative] = {
            "changedCells": len(plan_rows),
            "beforeFileSha256": before_hashes[locale]["sha256"],
            "beforeGitBlob": before_hashes[locale]["gitBlob"],
            "afterFileSha256": sha(readback),
            "afterGitBlob": git_blob(readback),
            "afterBytes": len(readback),
        }

    decisions = read_rows(evidence / "review-packet/cross-review/cross-review-decisions.jsonl")
    need(len(decisions) == 300, "cross decision matrix size")
    decision_ids = {(r["locale"], r["continuationRank"]): r for r in decisions}
    need(len(decision_ids) == 300, "unique cross decision cells")
    need(collections.Counter(r["crossDisposition"] for r in decisions) == {"keep": 219, "propose": 81},
         "cross disposition counts")
    need(set(proposals).issubset(decision_ids), "all plan proposals map to cross decisions")
    readback_rows = []
    for key, d in sorted(decision_ids.items(), key=lambda x: (x[0][1], LOCALES.index(x[0][0]))):
        locale, rank = key
        planned = proposals.get(key)
        need(d["crossDisposition"] == ("propose" if planned else "keep"), f"plan/disposition binding {locale}/{rank}")
        final = catalogs[locale].get(d["catalogKey"])
        expected = planned["target"] if planned else d["currentTarget"]
        expected_hash = planned["targetSha256"] if planned else d["currentTargetSha256"]
        need(final == expected and sha(final.encode("utf-8")) == expected_hash,
             f"300-cell readback {locale}/{rank}")
        need(d["currentTarget"] is not None and d["source"] is not None,
             f"caller-backed readback only {locale}/{rank}")
        readback_rows.append({
            "schemaVersion": 1, "window": "W80", "continuationRank": rank,
            "remainingQueueRank": d["remainingQueueRank"], "sourceId": d["sourceId"],
            "sourceSha256": d["sourceSha256"], "source": d["source"], "locale": locale,
            "catalogPath": d["catalogPath"], "catalogKey": d["catalogKey"],
            "crossDisposition": d["crossDisposition"],
            "preimageTargetSha256": d["currentTargetSha256"], "preimageTarget": d["currentTarget"],
            "readbackTargetSha256": sha(final.encode("utf-8")), "readbackTarget": final,
            "selectedPlanTargetSha256": planned["targetSha256"] if planned else None,
            "matchesExpected": True
        })

    need(len(readback_rows) == 300 and sum(r["crossDisposition"] == "propose" for r in readback_rows) == 81
         and sum(r["crossDisposition"] == "keep" for r in readback_rows) == 219,
         "all 300 readback rows and final dispositions")
    (app / "application-readback-300-cells.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for r in readback_rows),
        encoding="utf-8")

    previous_holds = read_rows(app / "prior-w79-holds-hash-only.jsonl")
    need(len(previous_holds) == 39 and all(r["priorWindow"] == "W79" and r["priorDisposition"] == "hold"
         and r["matchesPriorCurrentValue"] and r["callerEvidenceUnchanged"] for r in previous_holds),
         "all 39 prior W79 holds are unchanged at the pinned preimage")
    need(not ({r["sourceId"] for r in plan} & {r["sourceId"] for r in previous_holds}),
         "W80 proposal IDs are disjoint from the prior W79 held IDs")
    need(sum(r["continuationRank"] == 885 and r["locale"] == "ar" and "ID" in r["target"] for r in plan) == 1,
         "Arabic rank 885 selected target retains protected literal ID")

    prepost = {"artifact": "W80 locale catalog preimage and postimage manifest", "baseHead": HEAD,
               "baseTree": TREE, "catalogs": {}}
    for locale in LOCALES:
        relative = LOCALE_PATH.format(locale)
        raw = (repo / relative).read_bytes()
        after = json.loads(raw.decode("utf-8"))
        need(len(after) == 6176 and list(after) == before_order[locale], f"final catalog structure {locale}")
        expected_keys = {r["catalogKey"] for r in plan if r["locale"] == locale}
        changed_keys = {k for k in after if after[k] != before_objects[locale][k]}
        need(changed_keys == expected_keys, f"only selected target keys changed in {locale}")
        prepost["catalogs"][relative] = {
            "entries": len(after), "keyOrderSha256": sha("\n".join(after.keys()).encode("utf-8")),
            "selectedChanges": len(changed_keys), "changedKeysSha256": sha("\n".join(sorted(changed_keys)).encode("utf-8")),
            "beforeFileSha256": before_hashes[locale]["sha256"], "beforeGitBlob": before_hashes[locale]["gitBlob"],
            "afterFileSha256": sha(raw), "afterGitBlob": git_blob(raw), "afterBytes": len(raw)
        }

    (app / "catalog-preimage-and-postimage.json").write_text(json.dumps(prepost, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (app / "application-write-result.json").write_text(json.dumps(write_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    locale_counts = collections.Counter(r["locale"] for r in plan)
    summary = {
        "artifact": "slskdN PR #409 W80 localization application readback", "schemaVersion": 1,
        "window": "W80", "continuationRanks": [878, 902], "remainingQueueRanks": [778, 802],
        "baseHead": HEAD, "baseTree": TREE, "proposalCount": 81, "keepCount": 219, "newHoldCount": 0,
        "priorW79HoldsRetained": 39, "priorHoldLineageCount": 382,
        "readbackCellCount": 300, "catalogCount": 12, "catalogKeyCountPerLocale": 6176,
        "catalogKeyOrderUnchanged": True, "onlySelectedKeysChanged": True,
        "changedCellsByLocale": dict(sorted(locale_counts.items())),
        "baselineProtectedLiteralMismatch": {"rank": 885, "locale": "ar", "literal": "ID",
                                             "resolvedBySelectedTarget": True},
        "productPathsOutsideLocaleCatalogs": False, "workflowPathsChanged": 0,
        "nativeSpeakerApproval": False, "browserReview": False,
        "testsBuildsScansCiRun": False
    }
    (app / "application-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": "PASS", "applied": True, "selectedTargets": 81,
                      "keeps": 219, "readbackCells": len(readback_rows), "priorW79Holds": 39,
                      "changedFiles": len(write_result["files"])}, indent=2))


if __name__ == "__main__":
    main()
