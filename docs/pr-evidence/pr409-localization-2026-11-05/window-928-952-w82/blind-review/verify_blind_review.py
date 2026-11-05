#!/usr/bin/env python3
"""Portable verifier for the sealed W82 blind-review bundle (Python stdlib only)."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

EXPECTED_HEAD = "6e48a342d4b1c43918c23da3afcbaad19c87a005"
EXPECTED_TREE = "b82ea7937cf9aa141a1c952283d5549dbe116ba5"
EXPECTED_LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
EXPECTED_RANKS = list(range(928, 953))


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify_sumlist(root, filename, expected_names=None):
    sums_path = root / filename
    entries = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise ValueError(f"Malformed checksum row in {filename}")
        name = parts[1].lstrip(" *")
        if Path(name).name != name or name in entries:
            raise ValueError(f"Unsafe or duplicate checksum path in {filename}")
        entries[name] = parts[0].lower()
    if expected_names is not None and set(entries) != set(expected_names):
        raise ValueError(f"Unexpected checksum file set in {filename}")
    for name, expected in entries.items():
        path = root / name
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f"Checksum mismatch: {filename}:{name}")
    return entries


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, type=Path, help="candidate-free packet input directory")
    ap.add_argument("--output", required=True, type=Path, help="blind-review output directory")
    args = ap.parse_args()
    inp, out = args.input, args.output

    input_files = [p.name for p in inp.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt"]
    input_hashes = verify_sumlist(inp, "SHA256SUMS.txt", input_files)
    pin = load_json(inp / "manifest.json")
    att = load_json(inp / "source-tree-attestation.json")
    live = load_json(inp / "live-before.json")
    boundary = load_json(inp / "selection-and-boundary.json")
    require(pin.get("candidateFree") is True and pin.get("head") == EXPECTED_HEAD and pin.get("tree") == EXPECTED_TREE, "Candidate-free manifest pin mismatch")
    require(pin.get("proposedTargetsIncluded") is False and pin.get("reviewDecisionsIncluded") is False and pin.get("prBodyContentIncluded") is False, "Input is not a clean candidate-free packet")
    require(pin.get("continuationRankRange") == [928, 952] and pin.get("sourceCount") == 25 and pin.get("localeCount") == 12 and pin.get("cellCount") == 300, "Input scope mismatch")
    require(pin.get("locales") == EXPECTED_LOCALES, "Input locale order mismatch")
    require(att.get("head") == EXPECTED_HEAD and att.get("tree") == EXPECTED_TREE, "Source-tree attestation pin mismatch")
    require(att.get("sourceInventoryHash") == digest(inp / "source-inventory-pinned.jsonl"), "Pinned source-inventory digest mismatch")
    require(att.get("runtimeFilePinsSha256") == digest(inp / "runtime-file-pins.jsonl"), "Runtime-file-pins digest mismatch")
    require(live.get("headSha") == EXPECTED_HEAD and live.get("headTree") == EXPECTED_TREE and live.get("merged") is False, "Captured PR head/state mismatch")
    require(boundary.get("head") == EXPECTED_HEAD and boundary.get("tree") == EXPECTED_TREE and boundary.get("candidateFree") is True, "Selection boundary pin mismatch")
    require(boundary.get("continuationRankRange") == [928, 952] and boundary.get("sourceCount") == 25 and boundary.get("cellCount") == 300, "Selection boundary scope mismatch")

    selected = load_jsonl(inp / "selected-sources.jsonl")
    inventory = load_jsonl(inp / "source-inventory-selection.jsonl")
    cells = load_jsonl(inp / "source-current-cells.jsonl")
    contexts = load_jsonl(inp / "caller-contexts.jsonl")
    require(len(selected) == 25 and [r["continuationRank"] for r in selected] == EXPECTED_RANKS, "Selected-source rank sequence mismatch")
    require(len(inventory) == 25 and [r["continuationRank"] for r in inventory] == EXPECTED_RANKS, "Inventory-selection rank sequence mismatch")
    selected_by_rank = {r["continuationRank"]: r for r in selected}
    for s, inv in zip(selected, inventory):
        require(s["sourceId"] == inv["sourceId"] and s["sourceSha256"] == inv["sourceSha256"] and s["remainingQueueRank"] == inv["remainingQueueRank"], "Selection/inventory row mismatch")
    require(len(cells) == 300, "Input cell count mismatch")
    cell_map = {}
    for c in cells:
        key = (c["continuationRank"], c["locale"])
        require(key not in cell_map, "Duplicate input cell")
        cell_map[key] = c
        require(c["locale"] in EXPECTED_LOCALES and c["continuationRank"] in EXPECTED_RANKS, "Out-of-scope input cell")
        require(c.get("containsCandidate") is False and c.get("decision") is None, "Input cell is not candidate-free")
        s = selected_by_rank[c["continuationRank"]]
        require(c["sourceId"] == s["sourceId"] and c["sourceSha256"] == s["sourceSha256"] and c["source"] == s["source"], "Cell/source identity mismatch")
        require(c.get("sourceTextIncluded") is True and c.get("currentTargetTextIncluded") is True, "Input cell text flag mismatch")
    require(set(cell_map) == {(rank, loc) for rank in EXPECTED_RANKS for loc in EXPECTED_LOCALES}, "Input cell matrix incomplete")
    require(len(contexts) == 25, "Caller-context packet count mismatch")
    context_by_rank = {r["continuationRank"]: r for r in contexts}
    require(set(context_by_rank) == set(EXPECTED_RANKS), "Caller-context ranks mismatch")
    for c in cells:
        ctx = context_by_rank[c["continuationRank"]]
        require(c["sourceId"] == ctx["sourceId"] and c["sourceSha256"] == ctx["sourceSha256"], "Caller-context source identity mismatch")
        require(c.get("callerCount") == ctx.get("productionCallerCount") == len(ctx.get("callers", [])), "Caller-context count mismatch")
        projected = [{k:v for k,v in ref.items() if k in {"contextSha256","fileSha256","gitBlob","line","lineSha256","path"}} for ref in ctx.get("callers", [])]
        require(c.get("callerRefs") == projected, "Caller-reference anchor mismatch")
        if c["continuationRank"] == 944:
            require(c.get("callerCount") == 0 and c.get("callerRefs") == [] and c.get("callerContextSha256") == hashlib.sha256(b"[]").hexdigest(), "Rank-944 callerless pin mismatch")
            require(ctx.get("productionCallerCount") == 0 and ctx.get("callers") == [] and ctx.get("sourceTextIncluded") is False, "Rank-944 context packet is not text-free/callerless")
    require(sum(1 for r in selected if r["continuationRank"] == 944) == 1, "Rank-944 source missing")

    output_hashes = verify_sumlist(out, "SHA256SUMS.txt", {"README.md", "blind-ledger.jsonl", "blind-manifest.json", "verify_blind_review.py"})
    om = load_json(out / "blind-manifest.json")
    require(om.get("sealed") is True and om.get("head") == EXPECTED_HEAD and om.get("tree") == EXPECTED_TREE, "Output seal/pin mismatch")
    require(om.get("inputManifestSha256") == digest(inp / "manifest.json"), "Output input-manifest digest mismatch")
    require(om.get("inputSha256SumsSha256") == digest(inp / "SHA256SUMS.txt"), "Output input-checksum-list digest mismatch")
    require(om.get("inputChecksumEntryCount") == len(input_hashes), "Input checksum count mismatch")
    require(om.get("ledgerSha256") == digest(out / "blind-ledger.jsonl"), "Ledger digest mismatch")
    require(om.get("verifierSha256") == digest(Path(__file__).resolve()), "Verifier digest mismatch")
    non_manifest_output_hashes = {name:value for name,value in output_hashes.items() if name != "blind-manifest.json"}
    require(om.get("outputChecksumEntries") == non_manifest_output_hashes, "Output checksum manifest mismatch")
    require(om.get("sourceTextIncluded") is False and om.get("currentTargetTextIncluded") is False and om.get("proposedTargetIncluded") is False, "Output text inclusion flags mismatch")

    ledger_path = out / "blind-ledger.jsonl"
    ledger_lines = [line for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ledger = [json.loads(line) for line in ledger_lines]
    require(len(ledger) == 300, "Ledger cell count mismatch")
    require(len({(r["continuationRank"],r["locale"]) for r in ledger}) == 300, "Duplicate ledger cell")
    require([(r["continuationRank"],r["locale"]) for r in ledger] == [(rank,loc) for rank in EXPECTED_RANKS for loc in EXPECTED_LOCALES], "Ledger ordering/matrix mismatch")
    require({r["disposition"] for r in ledger} <= {"accept","revise","hold"}, "Unknown disposition")
    ledger_by_key = {(r["continuationRank"],r["locale"]):r for r in ledger}
    counts = {k:sum(1 for r in ledger if r["disposition"] == k) for k in ("accept","revise","hold")}
    require(om.get("dispositionCounts") == counts, "Disposition counts mismatch")
    forbidden = {"source","sourceText","currentTarget","currentTargetText","target","targetText","proposedTarget","candidateText","proposalText"}
    for line, r in zip(ledger_lines, ledger):
        require(not (forbidden & set(r)), "Ledger contains a text field")
        require(r.get("sourceTextIncluded") is False and r.get("currentTargetTextIncluded") is False and r.get("proposedTargetIncluded") is False, "Ledger text-free flags mismatch")
        c=cell_map[(r["continuationRank"],r["locale"])]
        require(r["sourceId"] == c["sourceId"] and r["sourceSha256"] == c["sourceSha256"] and r["currentTargetSha256"] == c["currentTargetSha256"], "Ledger hash anchor mismatch")
        require(r["callerCount"] == c["callerCount"] and r["callerContextSha256"] == c["callerContextSha256"], "Ledger caller anchor mismatch")
        t=c["tokenEvidence"]
        expected_audit={
            "markupMatches":t["markup"]["matches"],
            "placeholderMatches":t["placeholders"]["matches"],
            "numbersSourcePreserved":t["numbers"]["sourcePreserved"],
            "protectedLiteralSource":t["protectedLiterals"]["source"],
            "protectedLiteralTarget":t["protectedLiterals"]["target"],
            "protectedLiteralMissing":t["protectedLiterals"]["missing"],
        }
        require(r.get("tokenAudit") == expected_audit, "Token audit evidence mismatch")
        if r["continuationRank"] == 944:
            require(r["disposition"] == "hold" and r["reasonCode"] == "callerless_context_unresolved", "Rank-944 disposition mismatch")
            require(c["source"] not in line and c["currentTarget"] not in line, "Rank-944 text leaked into ledger")
            require(not any(k.lower().endswith("text") and v is True for k,v in r.items()), "Rank-944 text flag leaked")
        if t["protectedLiterals"]["missing"]:
            require(r["disposition"] == "revise", "Protected literal mismatch not surfaced")
        if not t["markup"]["matches"] or not t["placeholders"]["matches"] or not t["numbers"]["sourcePreserved"]:
            require(r["disposition"] in {"revise","hold"}, "Token mismatch not surfaced")
    require(sum(1 for r in ledger if r["continuationRank"] == 944 and r["disposition"] == "hold") == 12, "Rank-944 text-free hold count mismatch")

    print("PASS: input checksums, pinned anchors, candidate-free scope, 300-cell matrix, token audit, text-free rank-944 holds, and sealed output hashes verified")
    print("Counts: " + json.dumps(counts, sort_keys=True))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
