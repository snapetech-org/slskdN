#!/usr/bin/env python3
"""Rebuild the W80 evidence inventory and top-level SHA-256 file."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def readj(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    app = ROOT / "application"
    summary = readj(app / "application-summary.json")
    product = readj(app / "product-commit.json")
    root_review = readj(ROOT / "review-packet/root-manual-review/review.json")
    files = []
    for path in sorted((p for p in ROOT.rglob("*") if p.is_file()
                        and p.relative_to(ROOT).as_posix() not in {"manifest.json", "SHA256SUMS.txt"}),
                       key=lambda p: p.relative_to(ROOT).as_posix()):
        data = path.read_bytes()
        files.append({"path": path.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": sha(data)})
    manifest = {
        "artifact": "slskdN PR #409 W80 localization application evidence",
        "schemaVersion": 1,
        "repository": "snapetech-org/slskdN",
        "pullRequest": 409,
        "branch": product["pushedToBranch"],
        "window": "W80",
        "continuationRanks": [878, 902],
        "remainingQueueRanks": [778, 802],
        "baseHead": product["parent"],
        "baseTree": "b3525218d0f9676c88c4991e78775d113f18b7d9",
        "productCommit": product["commit"],
        "productCommitTree": product["tree"],
        "proposalCount": summary["proposalCount"],
        "keepCount": summary["keepCount"],
        "newHoldCount": summary["newHoldCount"],
        "priorW79HoldsRetained": summary["priorW79HoldsRetained"],
        "readbackCellCount": summary["readbackCellCount"],
        "catalogCount": summary["catalogCount"],
        "catalogKeyCountPerLocale": summary["catalogKeyCountPerLocale"],
        "rootReviewPlanSha256": root_review["crossProposalPlanSha256"],
        "mainDriftOverlapCount": readj(app / "main-drift-check.json")["overlapCount"],
        "callerlessTextIncluded": False,
        "nativeSpeakerApproval": False,
        "browserReview": False,
        "testsBuildsScansCiRun": False,
        "files": files
    }
    manifest_path = ROOT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sums_paths = [ROOT / item["path"] for item in files] + [manifest_path]
    lines = [f"{sha(path.read_bytes())}  {path.relative_to(ROOT).as_posix()}" for path in sums_paths]
    (ROOT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"result": "PASS", "manifestEntries": len(files),
                      "manifestSha256": sha(manifest_path.read_bytes()),
                      "checksumEntries": len(lines)}, indent=2))


if __name__ == "__main__":
    main()
