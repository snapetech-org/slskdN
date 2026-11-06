#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def j(path):
    return json.loads(path.read_text(encoding="utf-8"))


def jl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    app = Path(__file__).resolve().parent
    bundle = app.parent
    plan = j(app / "application-plan.json")
    source_plan_path = app / "application-plan-source.json"
    source_plan = j(source_plan_path)
    readback = jl(app / "application-readback.jsonl")
    readback_summary = j(app / "application-plan-readback.json")
    app_summary = j(app / "application-summary.json")
    commit = j(app / "application-commit.json")
    holds = jl(app / "held-cells-hash-only.jsonl")
    cross = {(r["sourceId"], r["locale"]): r for r in jl(bundle / "cross-review/cross-review.jsonl")}
    addendum = {(r["sourceId"], r["locale"]): r for r in jl(bundle / "second-person-audit/concern-resolution-addendum/target-resolution-addendum.jsonl")}
    readback_by_key = {(r["sourceId"], r["locale"]): r for r in readback}
    plan_by_key = {(r["sourceId"], r["locale"]): r for r in plan["updates"]}
    assert len(readback) == len(plan["updates"]) == 57 and len(readback_by_key) == len(plan_by_key) == 57
    assert plan["sourcePlanSha256"] == sha(source_plan_path.read_bytes())
    assert plan["applicationCommit"] == commit["commit"] == "f120ea15892aa1bd8e17ab43965822ac459e4a71"
    assert plan["applicationTree"] == commit["tree"] == "a6b6e84f512e21b7f0bf3a44879ccf81815d3bcc"
    assert plan["head"] == "d0317d8258a31d05b7f163921c2e39f93deabfca"
    assert commit["parent"] == plan["head"] and commit["pushPerformed"] is False
    assert commit["workflowFilesChanged"] == 0 and all(".github/workflows/" not in p for p in commit["changedFiles"])
    assert len(holds) == 12 and all(r["recommendation"] == "hold" and r["callerCount"] == 0 for r in holds)
    assert all(r["sourceTextIncluded"] is False and r["currentTargetTextIncluded"] is False and r["recommendedTargetTextIncluded"] is False for r in holds)
    for key, u in plan_by_key.items():
        r = readback_by_key[key]
        x = cross[key]
        expected = addendum[key]["revisedRecommendedTarget"] if key in addendum else x["recommendedTarget"]
        assert u["source"] == x["source"] and u["key"] == x["source"]
        assert u["old"] == x["currentTarget"] and r["expectedOldTarget"] == u["old"]
        assert u["new"] == expected == r["readbackTarget"]
        assert u["newSha256"] == r["expectedNewTargetSha256"] == r["readbackTargetSha256"]
        assert r["readbackMatchesPlan"] is True and r["readbackMatchesFinalCrossReview"] is True
        assert r["headCommit"] == commit["commit"] and r["catalogPath"] == u["path"] and r["catalogKey"] == u["key"]
    catalog_summary = {r["path"]: r for r in readback_summary["catalogs"]}
    assert len(catalog_summary) == 12 and all(catalog_summary[c["path"]]["actualSha256"] == c["sha256"] for c in plan["catalogs"])
    delta_paths = {r["path"] for r in readback_summary["sourcePlanCatalogHashDeltas"]}
    assert delta_paths == {"src/web/public/locales/fr.json", "src/web/public/locales/ja.json", "src/web/public/locales/vi.json"}
    assert all(not c["matchesSourcePlan"] for c in readback_summary["catalogs"] if c["path"] in delta_paths)
    assert all(c["matchesSourcePlan"] for c in readback_summary["catalogs"] if c["path"] not in delta_paths)
    assert app_summary["actualReadbackMatches"] == readback_summary["readbackMatches"] == 57
    assert app_summary["readbackMismatches"] == readback_summary["readbackMismatches"] == 0
    assert app_summary["hashOnlyCallerlessHolds"] == len(holds) == 12
    assert app_summary["priorHeldCellsHashOnly"] == 140 and app_summary["priorSelectedSourceIdsHashOnly"] == 1757
    print(json.dumps({"verifier":"PASS","readbackRows":len(readback),"readbackMismatches":0,"holdsHashOnly":len(holds),"planCatalogHashDeltas":sorted(delta_paths),"applicationCommit":commit["commit"],"workflowFilesChanged":0},indent=2))


if __name__=="__main__":
    main()
