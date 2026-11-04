#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HEAD = "d0317d8258a31d05b7f163921c2e39f93deabfca"
TREE = "01475aeffa17f6151c4bf161890662167c959bb0"
EXPECTED_TARGETS = {
    (659, "fr"): "Recherchez dans le graphe d’intérêts de Soulseek les comptes maillés qui ont choisi de participer et leurs fonctionnalités publiées.",
    (662, "vi"): "Quá trình xác minh không được làm thay đổi trạng thái pod, nhưng tin nhắn đã dán và bản ghi thành viên vẫn có thể chứa dữ liệu nhạy cảm về các nút ngang hàng hoặc chữ ký.",
    (664, "ja"): "時間ベース",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def j(path):
    return json.loads(path.read_text(encoding="utf-8"))


def jl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify_sums(directory, filename="SHA256SUMS.txt"):
    entries = {}
    for line in (directory / filename).read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        entries[name] = digest
    assert entries, "empty checksum list"
    for name, digest in entries.items():
        assert sha((directory / name).read_bytes()) == digest, "checksum mismatch: " + name
    return entries


def ph(value):
    return sorted(re.findall(r"\{[^{}]+\}", value))


def tags(value):
    return sorted(re.findall(r"</?[A-Za-z][^>]*>", value))


def nums(value):
    return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])", value)


def prot(value):
    found = set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])", value))
    for term in ("Wishlist", "Soulseek", "Discogs", "Pod"):
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", value):
            found.add(term)
    return sorted(found)


def checks(source, target):
    missing = [term for term in prot(source) if term not in target]
    return {
        "placeholders": {"source": ph(source), "target": ph(target), "matches": ph(source) == ph(target)},
        "markupTags": {"source": tags(source), "target": tags(target), "matches": tags(source) == tags(target)},
        "numericTokens": {"source": nums(source), "target": nums(target), "matches": nums(source) == nums(target)},
        "protectedLiterals": {"source": prot(source), "target": prot(target), "missing": missing, "matches": not missing},
    }


def main():
    parser = argparse.ArgumentParser(description="Verify the three-cell W71 wording addendum.")
    parser.add_argument("--addendum", type=Path)
    parser.add_argument("--cross-review", type=Path)
    parser.add_argument("--candidate-free", type=Path)
    parser.add_argument("--primary", type=Path)
    parser.add_argument("--blind", type=Path)
    args = parser.parse_args()
    add = args.addendum or Path(__file__).resolve().parent
    manifest = j(add / "manifest.json")
    cross = args.cross_review or Path(manifest["crossReviewPath"])
    cross_manifest = j(cross / "manifest.json")
    candidate = args.candidate_free or Path(manifest["candidateFreePath"])
    primary = args.primary or Path(manifest["primaryPath"])
    blind = args.blind or Path(manifest["blindPath"])
    second_audit = Path(manifest["secondPersonAuditPath"])
    verify_sums(add)
    verify_sums(cross)
    verify_sums(second_audit)
    verify_sums(candidate, "PACKET-SHA256SUMS.txt")
    assert sha((cross / "SHA256SUMS.txt").read_bytes()) == manifest["crossReviewChecksumListSha256"]
    assert sha((candidate / "PACKET-SHA256SUMS.txt").read_bytes()) == manifest["candidateFreeChecksumListSha256"]
    assert sha((second_audit / "SHA256SUMS.txt").read_bytes()) == manifest["secondPersonAuditChecksumListSha256"]
    cross_status=subprocess.run([sys.executable,str(cross/"verify_cross_review.py"),"--candidate-free",str(candidate),"--primary",str(primary),"--blind",str(blind)],check=True,capture_output=True,text=True)
    cross_result=json.loads(cross_status.stdout)
    assert cross_result["verifier"]=="PASS" and cross_result["cells"]==300
    assert manifest["head"]==cross_manifest["head"]==HEAD and manifest["tree"]==cross_manifest["tree"]==TREE
    assert manifest["preservesOriginalPacket"] is True
    original={(row["continuationRank"],row["locale"]):row for row in jl(cross/"cross-review.jsonl")}
    source_rows={(row["continuationRank"],row["locale"]):row for row in jl(candidate/"source-current-cells.jsonl")}
    contexts={row["sourceId"]:row for row in jl(candidate/"caller-contexts.jsonl")}
    supplemental=j(cross/"supplemental-caller-context.json")
    addendum=jl(add/"target-resolution-addendum.jsonl")
    assert len(addendum)==3 and {(row["continuationRank"],row["locale"]) for row in addendum}==set(EXPECTED_TARGETS)
    for row in addendum:
        key=(row["continuationRank"],row["locale"])
        source=source_rows[key]
        old=original[key]
        context=contexts[source["sourceId"]]
        expected_target=EXPECTED_TARGETS[key]
        assert row["head"]==HEAD and row["tree"]==TREE
        assert row["source"]==source["source"] and row["sourceSha256"]==source["sourceSha256"]
        assert row["currentTarget"]==source["currentTarget"] and row["currentTargetSha256"]==source["currentTargetSha256"]
        assert row["originalRecommendedTarget"]==old["recommendedTarget"]
        assert row["originalRecommendedTargetSha256"]==old["recommendedTargetSha256"]
        assert row["revisedRecommendedTarget"]==expected_target
        assert row["revisedTargetSha256"]==manifest["expectedTargetHashes"]["{}|{}".format(*key)]==sha(expected_target.encode("utf-8"))
        assert row["revisedRecommendedTarget"]!=row["currentTarget"] and row["revisedRecommendedTarget"]!=row["originalRecommendedTarget"]
        assert row["primaryDisposition"]==old["primaryDisposition"] and row["blindDisposition"]==old["blindDisposition"]
        assert row["callerCount"]==context["productionCallerCount"]
        assert row["callerContextSha256"]==source["callerContextSha256"]
        expected_refs=[{k:v for k,v in ref.items() if k!="lineText"} for ref in source["callerRefs"]]
        assert row["callerRefs"]==expected_refs
        regular=[]
        for caller in context["callers"]:
            regular.append({"path":caller["path"],"line":caller["line"],"lineText":caller["lineText"],"contextSha256":caller["contextSha256"],"context":[{"line":x["line"],"text":x["text"]} for x in caller["context"]]})
        assert row["pinnedCallerEvidence"][:len(regular)]==regular
        if key==(664,"ja"):
            evidence=row["pinnedCallerEvidence"][-1]
            assert evidence["path"]==supplemental["path"] and evidence["gitBlob"]==supplemental["gitBlob"] and evidence["fileSha256"]==supplemental["fileSha256"]
            assert evidence["excerpts"]==supplemental["excerpts"]
            assert any("timed mode advances on an interval" in x["text"] for x in evidence["excerpts"])
        token_checks=checks(source["source"],expected_target)
        assert row["targetTokenChecks"]==token_checks and all(x["matches"] for x in token_checks.values())
        assert row["resolved"] is True and row["nativeSpeakerSignoffBeforeApplication"] is True
        assert row["applicationRecommendation"]=="update with revised target after native-speaker signoff"
    before=j(add/"live-before.json");after=j(add/"live-after.json")
    for attestation in (before,after):
        assert attestation["repository"]=="snapetech-org/slskdN" and attestation["pullRequest"]==409
        assert attestation["headRefOid"]==attestation["branchRefOid"]==attestation["pullRefOid"]==HEAD
        assert attestation["treeOid"]==TREE
    assert before["headRefOid"]==after["headRefOid"] and before["treeOid"]==after["treeOid"]
    assert manifest["liveBeforeUtc"]==before["attestedUtc"] and manifest["liveAfterUtc"]==after["attestedUtc"] and manifest["refsUnchanged"] is True
    print(json.dumps({"verifier":"PASS","resolvedCells":len(addendum),"allTargetsDifferFromCurrent":True,"allTargetsDifferFromOriginalRecommendation":True,"tokenChecks":{"placeholders":"3/3 pass","markup":"3/3 pass","numeric":"3/3 pass","protectedLiterals":"3/3 pass"},"pinnedHeadTree":"unchanged","originalPacket":"preserved","applicationRecommendation":manifest["applicationRecommendation"]},ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
