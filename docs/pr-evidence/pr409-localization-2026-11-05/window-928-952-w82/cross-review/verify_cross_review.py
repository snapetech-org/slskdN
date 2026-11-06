#!/usr/bin/env python3
"""Portable integrity verifier for slskdN PR #409 W82 cross-review evidence."""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

HEAD = "6e48a342d4b1c43918c23da3afcbaad19c87a005"
TREE = "b82ea7937cf9aa141a1c952283d5549dbe116ba5"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
PLACEHOLDER = re.compile(r"\{[^{}]+\}")
MARKUP = re.compile(r"</?[A-Za-z][^>]*>")
NUMBER = re.compile(r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text_digest(value: str) -> str:
    return digest(value.encode("utf-8"))


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify_sums(folder: Path):
    sums_path = folder / "SHA256SUMS.txt"
    recorded = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, name = line.split(None, 1)
        name = name.strip().lstrip("* ")
        candidate = (folder / name).resolve()
        if candidate.parent != folder.resolve():
            raise ValueError(f"checksum path escapes packet: {name}")
        if digest(candidate.read_bytes()) != expected:
            raise ValueError(f"checksum mismatch: {folder}/{name}")
        recorded[name] = expected
    actual = {p.name for p in folder.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt"}
    if actual != set(recorded):
        raise ValueError(f"checksum file coverage mismatch in {folder}: missing={sorted(actual-set(recorded))}, extra={sorted(set(recorded)-actual)}")
    return digest(sums_path.read_bytes())


def verify_tokens(source: str, target: str, cell):
    if collections.Counter(PLACEHOLDER.findall(source)) != collections.Counter(PLACEHOLDER.findall(target)):
        raise ValueError("placeholder mismatch in selected target")
    if collections.Counter(MARKUP.findall(source)) != collections.Counter(MARKUP.findall(target)):
        raise ValueError("markup mismatch in selected target")
    if not set(NUMBER.findall(source)).issubset(set(NUMBER.findall(target))):
        raise ValueError("number missing in selected target")
    protected = cell["tokenEvidence"]["protectedLiterals"]["source"]
    if not all(value in target for value in protected):
        raise ValueError("protected literal missing in selected target")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-free", type=Path, required=True)
    ap.add_argument("--primary", type=Path, required=True)
    ap.add_argument("--blind", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    cf, primary, blind, out = [x.resolve() for x in (args.candidate_free, args.primary, args.blind, args.output)]
    cf_sums = verify_sums(cf)
    primary_sums = verify_sums(primary)
    blind_sums = verify_sums(blind)
    summary = json.loads((out / "cross-review-summary.json").read_text(encoding="utf-8"))
    cf_manifest = json.loads((cf / "manifest.json").read_text(encoding="utf-8"))
    pmanifest = json.loads((primary / "manifest.json").read_text(encoding="utf-8"))
    bmanifest = json.loads((blind / "blind-manifest.json").read_text(encoding="utf-8"))
    if (summary["head"], summary["tree"]) != (HEAD, TREE):
        raise ValueError("cross summary anchor mismatch")
    if (cf_manifest["head"], cf_manifest["tree"]) != (HEAD, TREE):
        raise ValueError("candidate-free anchor mismatch")
    if pmanifest["candidateFreeInputManifestSha256"] != digest((cf / "manifest.json").read_bytes()):
        raise ValueError("primary input manifest anchor mismatch")
    if bmanifest["inputManifestSha256"] != digest((cf / "manifest.json").read_bytes()):
        raise ValueError("blind input manifest anchor mismatch")
    if pmanifest["head"] != HEAD or pmanifest["tree"] != TREE or bmanifest["head"] != HEAD or bmanifest["tree"] != TREE:
        raise ValueError("review input anchor mismatch")
    if summary["inputChecksumsSha256"] != {"candidateFree": cf_sums, "primary": primary_sums, "blind": blind_sums}:
        raise ValueError("cross summary input checksum binding mismatch")

    cells = read_jsonl(cf / "source-current-cells.jsonl")
    prows = read_jsonl(primary / "primary-review.jsonl")
    proposals = read_jsonl(primary / "corrections.jsonl")
    brows = read_jsonl(blind / "blind-ledger.jsonl")
    ledger = read_jsonl(out / "cross-ledger.jsonl")
    key = lambda row: (row["continuationRank"], row["locale"])
    cm, pm, bm, prop, lm = ({key(row): row for row in rows} for rows in (cells, prows, brows, proposals, ledger))
    expected = {(rank, locale) for rank in range(928, 953) for locale in LOCALES}
    if any(len(rows) != 300 or set(mapping) != expected for rows, mapping in ((cells, cm), (prows, pm), (brows, bm), (ledger, lm))):
        raise ValueError("cross evidence does not cover the exact 300-cell matrix")
    if len(proposals) != 37 or set(prop) != {k for k, row in pm.items() if row["disposition"] == "correction"}:
        raise ValueError("primary correction matrix mismatch")

    counts = collections.Counter(row["crossDisposition"] for row in ledger)
    for k, row in lm.items():
        cell, primary_row, blind_row = cm[k], pm[k], bm[k]
        if row["sourceSha256"] != cell["sourceSha256"] or row["currentTargetSha256"] != cell["currentTargetSha256"]:
            raise ValueError(f"candidate-free cell hash mismatch: {k}")
        if row["callerContextSha256"] != cell["callerContextSha256"] or row["callerCount"] != cell["callerCount"]:
            raise ValueError(f"caller context mismatch: {k}")
        if row["primaryDisposition"] != primary_row["disposition"]:
            raise ValueError(f"primary disposition mismatch: {k}")
        if row["blindDisposition"] != blind_row["disposition"] or row["blindReasonCode"] != blind_row["reasonCode"]:
            raise ValueError(f"blind disposition mismatch: {k}")
        expected_proposal_sha = prop[k]["candidateTargetSha256"] if k in prop else None
        if row["primaryProposalSha256"] != expected_proposal_sha:
            raise ValueError(f"primary proposal hash mismatch: {k}")
        if row["sourceTextIncluded"] is not False or row["currentTargetTextIncluded"] is not False:
            raise ValueError(f"unexpected source/current text flag: {k}")
        disposition = row["crossDisposition"]
        if disposition in ("correction", "refinement"):
            if k not in prop or row["selectedTarget"] != prop[k]["candidateTarget"]:
                raise ValueError(f"selected target does not match primary proposal: {k}")
            if row["selectedTargetSha256"] != prop[k]["candidateTargetSha256"] or text_digest(row["selectedTarget"]) != row["selectedTargetSha256"]:
                raise ValueError(f"selected target hash mismatch: {k}")
            if row["selectedTargetTextIncluded"] is not True:
                raise ValueError(f"selected target text flag mismatch: {k}")
            verify_tokens(cell["source"], row["selectedTarget"], cell)
        elif disposition == "accept-current":
            if k in prop or row["selectedTarget"] is not None or row["selectedTargetSha256"] is not None or row["selectedTargetTextIncluded"] is not False:
                raise ValueError(f"invalid accept-current row: {k}")
        elif disposition == "hold":
            if row["selectedTarget"] is not None or row["selectedTargetTextIncluded"] is not False:
                raise ValueError(f"hold contains selected text: {k}")
            if k[0] == 944 and (cell["callerCount"] != 0 or row["currentTargetSha256"] is None):
                raise ValueError("rank 944 must remain text-free and callerless")
        else:
            raise ValueError(f"unknown disposition {disposition!r}: {k}")
    expected_counts = {"accept-current": 251, "correction": 30, "refinement": 4, "hold": 15}
    if dict(counts) != expected_counts or summary["crossDispositionCounts"] != expected_counts:
        raise ValueError(f"cross disposition counts mismatch: {dict(counts)}")
    if len([row for row in ledger if row["selectedTarget"] is not None]) != 34:
        raise ValueError("expected 34 selected changes")
    if summary["ledgerSha256"] != digest((out / "cross-ledger.jsonl").read_bytes()):
        raise ValueError("cross ledger seal mismatch")
    if summary["nativeSpeakerValidationClaimed"] or summary["browserReviewClaimed"] or summary["sourceCatalogPrEditsMade"] or summary["testsBuildsScansCiRun"] or summary["workflowChanges"] != 0:
        raise ValueError("unsupported completion claim in summary")
    verify_sums(out)
    print("PASS: input checksums/anchors, 300-cell reconciliation, 34 target hashes, token checks, 15 text-free holds, and output seal verified")
    print("Counts: " + json.dumps(expected_counts, sort_keys=True))


if __name__ == "__main__":
    main()
