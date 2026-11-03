#!/usr/bin/env python3
"""Verify the sealed slskdN W62 root cross-audit and its source packets."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_checksums(directory: Path, checksum_name: str) -> str:
    checksum_path = directory / checksum_name
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        expected, relpath = line.split("  ", 1)
        actual_path = directory / relpath
        if sha256(actual_path) != expected:
            raise SystemExit(f"checksum mismatch: {actual_path}")
    return sha256(checksum_path)


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    input_dir = ROOT / "candidate-free-input"
    primary_dir = ROOT / "primary-review"
    blind_dir = ROOT / "blind-review"
    input_hash = verify_checksums(input_dir, "PACKET-SHA256SUMS.txt")
    primary_hash = verify_checksums(primary_dir, "PRIMARY-SHA256SUMS.txt")
    blind_hash = verify_checksums(blind_dir, "SHA256SUMS.txt")
    verify_checksums(HERE, "SHA256SUMS.txt")

    cells = jsonl(input_dir / "source-current-cells.jsonl")
    primary = jsonl(primary_dir / "primary-ledger.jsonl")
    blind = jsonl(blind_dir / "blind-ledger.jsonl")
    audit = jsonl(HERE / "cross-audit-ledger.jsonl")
    keyed = lambda rows: {(r["continuationRank"], r["locale"]): r for r in rows}
    current_by_key = keyed(cells)
    primary_by_key = keyed(primary)
    blind_by_key = keyed(blind)
    audit_by_key = keyed(audit)

    if any(len(rows) != 300 for rows in (cells, primary, blind, audit)):
        raise SystemExit("expected 300 source, primary, blind, and cross-audit cells")
    if len(current_by_key) != 300 or len(primary_by_key) != 300 or len(blind_by_key) != 300 or len(audit_by_key) != 300:
        raise SystemExit("duplicate or missing rank/locale key")

    for key, source in current_by_key.items():
        p = primary_by_key[key]
        b = blind_by_key[key]
        a = audit_by_key[key]
        for field in ("sourceId", "source", "sourceSha256", "currentTarget", "currentTargetSha256", "catalogPath", "catalogFileSha256", "catalogGitBlob", "callerContextSha256"):
            if p[field] != source[field] or b[field] != source[field] or a[field] != source[field]:
                raise SystemExit(f"source/current lineage mismatch at {key}: {field}")
        if p["head"] != b["head"] or p["head"] != a["head"] or p["tree"] != b["tree"] or p["tree"] != a["tree"]:
            raise SystemExit(f"head/tree mismatch at {key}")
        if a["callerRefs"] != source["callerRefs"]:
            raise SystemExit(f"caller-reference mismatch at {key}")
        selected = a["selectedTarget"]
        allowed = {source["currentTarget"], p["reviewedTarget"], b.get("target")}
        if key == (441, "pt-BR"):
            allowed.add("Avançar")
        if selected not in allowed:
            raise SystemExit(f"selected value has no reviewed source at {key}")
        if sha256_bytes(selected) != a["selectedTargetSha256"]:
            raise SystemExit(f"selected target hash mismatch at {key}")

        disposition = a["disposition"]
        if disposition == "hold":
            if key[0] not in (438, 452) or selected != source["currentTarget"] or source["callerRefs"]:
                raise SystemExit(f"hold policy violation at {key}")
        elif disposition == "accept-current":
            if selected != source["currentTarget"]:
                raise SystemExit(f"accept-current changed a value at {key}")
        elif disposition in ("correction", "refinement"):
            if selected == source["currentTarget"]:
                raise SystemExit(f"change disposition has no change at {key}")
        else:
            raise SystemExit(f"unknown disposition at {key}: {disposition}")

        placeholder_pattern = re.compile(r"\{[^{}\r\n]+\}")
        if placeholder_pattern.findall(source["source"]) != placeholder_pattern.findall(selected):
            raise SystemExit(f"placeholder mismatch at {key}")
        tag_pattern = re.compile(r"</?[A-Za-z][^<>]*?/?>")
        if tag_pattern.findall(source["source"]) != tag_pattern.findall(selected):
            raise SystemExit(f"markup mismatch at {key}")
        exempt = set(a["structuralEvidence"]["localizedFeatureLabels"])
        for token in source["sourceProtectedLiterals"]:
            if token not in exempt and token not in selected:
                raise SystemExit(f"protected literal {token!r} missing at {key}")

    summary = json.loads((HERE / "summary.json").read_text(encoding="utf-8"))
    counts = Counter(a["disposition"] for a in audit)
    changes = [a for a in audit if a["selectedTarget"] != a["currentTarget"]]
    updates_by_rank = Counter(str(a["continuationRank"]) for a in changes)
    if summary["candidateFreeInputPacketSha256"] != input_hash or summary["primaryPacketSha256"] != primary_hash or summary["blindPacketSha256"] != blind_hash:
        raise SystemExit("source packet checksum-list hash mismatch")
    if summary["reviewedCells"] != len(audit) or summary["dispositions"] != dict(sorted(counts.items())):
        raise SystemExit("summary cell/disposition mismatch")
    if summary["selectedUpdates"] != len(changes) or summary["callerlessHolds"] != 24:
        raise SystemExit("summary update/hold count mismatch")
    expected_updates = dict(sorted(updates_by_rank.items(), key=lambda item: int(item[0])))
    if summary["updatesByRank"] != expected_updates:
        raise SystemExit("summary update-by-rank mismatch")

    print(f"cross-audit verified: {len(audit)} cells; {len(changes)} updates; {counts['accept-current']} accept-current; {counts['hold']} callerless holds")


def sha256_bytes(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    main()
