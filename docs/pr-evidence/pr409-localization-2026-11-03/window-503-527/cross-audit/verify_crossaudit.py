#!/usr/bin/env python3
import collections
import hashlib
import json
import pathlib
import re
import subprocess
import sys

BASE = pathlib.Path("/home/keith/Documents/code/task-scratch")
OUT = pathlib.Path(__file__).resolve().parent
INPUT = BASE / "slskdn-pr409-w65-ranks503-527-primary-20261103/input"
PRIMARY = BASE / "slskdn-pr409-w65-ranks503-527-primary-review-20261103"
BLIND = BASE / "slskdn-pr409-w65-blind-review-20261103"
BLIND_INPUT = BASE / "slskdn-pr409-w65-ranks503-527-primary-20261103/blind-input"
HEAD = "c64d57a0322897bbaac77fa88a1327dd2f687db7"
TREE = "51ebf25124fc6ba30c8d5d99298e78353a951f17"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]

OVERRIDES = {
    (503, "de"): ("blind", None, "correction"),
    (503, "es"): ("cross-audit", "Ingrese el ContentID para obtener su grafo", "correction"),
    (503, "fr"): ("blind", None, "correction"),
    (503, "ja"): ("blind", None, "refinement"),
    (503, "pt-BR"): ("blind", None, "correction"),
    (503, "vi"): ("blind", None, "correction"),
    (503, "zh-Hans"): ("blind", None, "correction"),
    (503, "zh-Hant"): ("blind", None, "correction"),
    (507, "hi"): ("blind", None, "correction"),
    (507, "ja"): ("blind", None, "correction"),
    (508, "es"): ("blind", None, "correction"),
    (508, "fr"): ("blind", None, "correction"),
    (508, "pt-BR"): ("blind", None, "correction"),
    (509, "zh-Hans"): ("blind", None, "refinement"),
    (509, "zh-Hant"): ("blind", None, "refinement"),
    (518, "ja"): ("blind", None, "refinement"),
    (526, "ar"): ("blind", None, "correction"),
    (527, "hi"): ("blind", None, "correction"),
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def sha_file(path):
    return sha(path.read_bytes())

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def run(args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.strip()

def refs_core(callers):
    return [(c.get("path"), c.get("line"), c.get("lineText"), c.get("context")) for c in callers]

def token_checks(cell, target):
    placeholders = re.findall(r"\{[^{}]*\}", target)
    markup = re.findall(r"</?[A-Za-z][^>]*>", target)
    numeric = re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)?(?![A-Za-z])", target)
    expected_placeholders = cell["placeholderEvidence"]["sourceTokens"]
    expected_markup = cell["markupEvidence"]["sourceTags"]
    expected_numeric = cell["sourceNumericTokens"]
    expected_protected = cell["sourceProtectedLiterals"]
    protected_ok = all(target.count(token) >= expected_protected.count(token) for token in set(expected_protected))
    result = {
        "placeholders": {"source": expected_placeholders, "selected": placeholders, "match": sorted(placeholders) == sorted(expected_placeholders)},
        "markup": {"source": expected_markup, "selected": markup, "match": sorted(markup) == sorted(expected_markup)},
        "numeric": {"source": expected_numeric, "selected": numeric, "match": sorted(numeric) == sorted(expected_numeric)},
        "protectedLiterals": {"source": expected_protected, "selected": [t for t in expected_protected if target.count(t) >= expected_protected.count(t)], "match": protected_ok},
    }
    result["allPass"] = all(v["match"] for v in result.values())
    return result

def verify():
    manifest = json.loads((OUT / "manifest.json").read_text())
    summary = json.loads((OUT / "summary.json").read_text())
    live = json.loads((OUT / "live-head-attestation.json").read_text())
    verification = json.loads((OUT / "verification.json").read_text())
    expected_files = {x["path"]: x for x in manifest["files"]}
    if set(expected_files) != {"README.md", "crossaudit-decisions.jsonl", "live-head-attestation.json", "prior-held-cell-reattestation.jsonl", "summary.json", "verification.json", "verify_crossaudit.py", "build_crossaudit.py"}:
        raise SystemExit("Manifest output-file set mismatch")
    for name, entry in expected_files.items():
        p = OUT / name
        if not p.is_file() or p.stat().st_size != entry["bytes"] or sha_file(p) != entry["sha256"]:
            raise SystemExit(f"Manifest hash/size mismatch: {name}")
    run(["sha256sum", "-c", "SHA256SUMS.txt"], OUT)
    run(["sha256sum", "-c", "PACKET-SHA256SUMS.txt"], INPUT)
    input_verify = json.loads(run(["python3", "verify_input.py"], INPUT))
    run(["sha256sum", "-c", "SHA256SUMS.txt"], PRIMARY)
    primary_verify = json.loads(run(["python3", "verify_primary.py"], PRIMARY))
    run(["sha256sum", "-c", "PACKET-SHA256SUMS.txt"], BLIND_INPUT)
    run(["sha256sum", "-c", str(BLIND / "input-PACKET-SHA256SUMS.txt")], BLIND_INPUT)
    run(["sha256sum", "-c", "SHA256SUMS.txt"], BLIND)
    blind_verify = json.loads(run(["python3", "verify_blind_translation_review.py"], BLIND))
    if not input_verify.get("pass") or primary_verify.get("pass") is not True or blind_verify.get("result") != "PASS":
        raise SystemExit("A source packet verifier failed")
    if any(x != HEAD for x in (input_verify["head"], primary_verify["head"], blind_verify["head"], live["prHead"], live["branchRef"], live["pullRef"], manifest["head"])):
        raise SystemExit("Head mismatch")
    if any(x != TREE for x in (input_verify["tree"], primary_verify["tree"], blind_verify["tree"], live["tree"], manifest["tree"])):
        raise SystemExit("Tree mismatch")
    if str(live["state"]).lower() != "open" or live["isDraft"] is not True or str(manifest["livePrState"]).lower() != "open" or manifest["livePrDraft"] is not True:
        raise SystemExit("PR no longer OPEN/DRAFT in sealed attestation")
    if live["repository"] != manifest["repository"] or live["pullRequest"] != 409:
        raise SystemExit("Live PR attestation metadata mismatch")

    pins = manifest["inputPins"]
    pin_paths = {
        "candidateFreeManifestSha256": INPUT / "manifest.json",
        "candidateFreeChecksumListSha256": INPUT / "PACKET-SHA256SUMS.txt",
        "candidateFreeCellsSha256": INPUT / "source-current-cells.jsonl",
        "candidateFreeCallerContextsSha256": INPUT / "caller-contexts.jsonl",
        "priorHeldCellReattestationSha256": INPUT / "prior-held-cell-reattestation.jsonl",
        "primaryManifestSha256": PRIMARY / "manifest.json",
        "primaryChecksumListSha256": PRIMARY / "SHA256SUMS.txt",
        "primaryLedgerSha256": PRIMARY / "primary-ledger.jsonl",
        "blindInputManifestSha256": BLIND / "input-manifest.json",
        "blindInputChecksumListSha256": BLIND / "input-PACKET-SHA256SUMS.txt",
        "blindLedgerChecksumListSha256": BLIND / "SHA256SUMS.txt",
        "blindLedgerSha256": BLIND / "sealed-translation-ledger.jsonl",
    }
    for name, path in pin_paths.items():
        if sha_file(path) != pins[name]:
            raise SystemExit(f"Input hash pin mismatch: {name}")
    if pins["blindPromptSha256"] != sha_file(BLIND_INPUT / "translation-prompts.jsonl"):
        raise SystemExit("Blind prompt pin mismatch")

    input_rows = read_jsonl(INPUT / "source-current-cells.jsonl")
    caller_rows = {r["sourceId"]: r for r in read_jsonl(INPUT / "caller-contexts.jsonl")}
    primary_rows = read_jsonl(PRIMARY / "primary-ledger.jsonl")
    blind_rows = read_jsonl(BLIND / "sealed-translation-ledger.jsonl")
    blind_map = {(r["sourceId"], r["locale"]): r for r in blind_rows}
    cross_rows = read_jsonl(OUT / "crossaudit-decisions.jsonl")
    if not (len(input_rows) == len(primary_rows) == len(blind_rows) == len(cross_rows) == 300):
        raise SystemExit("Expected all 300 cells in each input/review/output")
    if len(blind_map) != 300:
        raise SystemExit("Blind ledger has duplicate cells")

    pcounts = collections.Counter()
    bcounts = collections.Counter()
    xcounts = collections.Counter()
    target_disagreements = 0
    p_disp_changes = 0
    target_sources = collections.Counter()
    for cell, primary, cross in zip(input_rows, primary_rows, cross_rows):
        key = (cell["continuationRank"], cell["locale"])
        caller = caller_rows[cell["sourceId"]]
        blind = blind_map[(cell["sourceId"], cell["locale"])]
        if cross["continuationRank"] != key[0] or cross["locale"] != key[1] or cross["sourceId"] != cell["sourceId"]:
            raise SystemExit(f"Cross-audit row order/key mismatch: {key}")
        for record in (cross, cross["primaryReview"], cross["blindReview"]):
            if record.get("head", HEAD) != HEAD or record.get("tree", TREE) != TREE:
                raise SystemExit(f"Embedded head/tree mismatch: {key}")
        if cross["source"] != cell["source"] or cross["sourceSha256"] != cell["sourceSha256"] or cross["currentTarget"] != cell["currentTarget"] or cross["currentTargetSha256"] != cell["currentTargetSha256"]:
            raise SystemExit(f"Candidate-free cell binding mismatch: {key}")
        if cross["catalogPath"] != cell["catalogPath"] or cross["catalogFileSha256"] != cell["catalogFileSha256"] or cross["catalogGitBlob"] != cell["catalogGitBlob"] or cross["catalogKey"] != cell["catalogKey"]:
            raise SystemExit(f"Catalog pin mismatch: {key}")
        if cross["callerContextSha256"] != cell["callerContextSha256"] or cross["callerContextSourceId"] != cell["sourceId"] or cross["callerContexts"] != caller["callers"]:
            raise SystemExit(f"Caller context pin mismatch: {key}")
        if primary["sourceId"] != cell["sourceId"] or primary["sourceSha256"] != cell["sourceSha256"] or primary["currentTarget"] != cell["currentTarget"] or primary["callerContextSha256"] != cell["callerContextSha256"]:
            raise SystemExit(f"Primary row mismatch: {key}")
        if blind["sourceId"] != cell["sourceId"] or blind["sourceSha256"] != cell["sourceSha256"] or blind["source"] != cell["source"] or blind["locale"] != cell["locale"]:
            raise SystemExit(f"Blind row mismatch: {key}")
        if refs_core(blind["callerReferences"]) != refs_core(caller["callers"]) or blind["callerCount"] != caller["productionCallerCount"]:
            raise SystemExit(f"Blind caller context mismatch: {key}")

        ptarget = primary.get("proposedTarget", cell["currentTarget"]) if primary["disposition"] in ("correction", "refinement") else cell["currentTarget"]
        btarget = blind["translation"]
        if ptarget != btarget:
            target_disagreements += 1
        pcounts[primary["disposition"]] += 1
        bcounts[blind["disposition"]] += 1

        override = OVERRIDES.get(key)
        xa = cross["crossAudit"]
        if override:
            source, literal, expected_disp = override
            expected_target = literal if source == "cross-audit" else btarget if source == "blind" else ptarget
            expected_source = source
        else:
            expected_disp = primary["disposition"]
            expected_target = ptarget if expected_disp in ("correction", "refinement") else cell["currentTarget"]
            expected_source = "primary" if expected_disp in ("correction", "refinement") else "current"
        if xa["disposition"] != expected_disp or xa["selectedTarget"] != expected_target or xa["targetSource"] != expected_source:
            raise SystemExit(f"Cross-audit adjudication mismatch: {key}")
        if xa["selectedTargetSha256"] != sha(xa["selectedTarget"].encode("utf-8")):
            raise SystemExit(f"Selected target hash mismatch: {key}")
        expected_proposed = expected_target if expected_disp in ("correction", "refinement") else None
        if xa["proposedTarget"] != expected_proposed:
            raise SystemExit(f"Proposal field mismatch: {key}")
        if not xa["rationale"].strip() or xa["confidence"] not in ("high", "moderate", "low"):
            raise SystemExit(f"Missing rationale/confidence: {key}")
        check = token_checks(cell, xa["selectedTarget"])
        if xa["tokenChecks"] != check or not check["allPass"]:
            raise SystemExit(f"Selected target token audit mismatch: {key}")
        if xa["disposition"] in ("accept-current", "hold") and xa["selectedTarget"] != cell["currentTarget"]:
            raise SystemExit(f"Non-proposal does not retain current target: {key}")
        if xa["disposition"] == "hold" and xa["proposedTarget"] is not None:
            raise SystemExit(f"Hold includes a proposal: {key}")
        if xa["disposition"] in ("correction", "refinement") and xa["selectedTarget"] == cell["currentTarget"]:
            raise SystemExit(f"Unchanged target marked as proposal: {key}")
        p_diff = ptarget != btarget
        if cross["comparison"]["primaryBlindTargetsAgree"] != (not p_diff) or cross["comparison"]["targetDisagreementAdjudicated"] != p_diff:
            raise SystemExit(f"Target comparison record mismatch: {key}")
        if cross["comparison"]["crossAuditDispositionDiffersFromPrimary"] != (xa["disposition"] != primary["disposition"]):
            raise SystemExit(f"Disposition comparison record mismatch: {key}")
        if cross["comparison"]["blindDisposition"] != blind["disposition"]:
            raise SystemExit(f"Blind disposition comparison mismatch: {key}")
        xcounts[xa["disposition"]] += 1
        target_sources[xa["targetSource"]] += 1
        if xa["disposition"] != primary["disposition"]:
            p_disp_changes += 1

    prior_input = INPUT / "prior-held-cell-reattestation.jsonl"
    prior_copy = OUT / "prior-held-cell-reattestation.jsonl"
    prior = read_jsonl(prior_input)
    copied = read_jsonl(prior_copy)
    if len(prior) != 98 or prior != copied or sha_file(prior_input) != sha_file(prior_copy):
        raise SystemExit("The 98 prior holds were not preserved byte-for-byte")
    if any(r.get("status") != "reattested-unchanged" or not r.get("matchesPriorCurrentValue") for r in copied):
        raise SystemExit("One or more prior holds are not marked unchanged")

    if summary["cellCount"] != 300 or summary["priorHeldCellsReattestedUnchanged"] != 98:
        raise SystemExit("Summary counts mismatch")
    if summary["primaryDispositionCounts"] != dict(sorted(pcounts.items())) or summary["blindDispositionCounts"] != dict(sorted(bcounts.items())) or summary["crossAuditDispositionCounts"] != dict(sorted(xcounts.items())):
        raise SystemExit("Summary disposition counts mismatch")
    if summary["primaryBlindTargetDisagreements"] != target_disagreements or summary["targetDisagreementsAdjudicated"] != target_disagreements:
        raise SystemExit("Target disagreement count/adjudication mismatch")
    if summary["crossAuditDispositionChangesFromPrimary"] != p_disp_changes or summary["crossAuditTargetSourceCounts"] != dict(sorted(target_sources.items())):
        raise SystemExit("Summary cross-audit result counts mismatch")
    if not all(r["crossAudit"]["tokenChecks"]["allPass"] for r in cross_rows):
        raise SystemExit("One or more target token checks failed")
    if verification["result"] != "PASS" or verification["rows"] != 300 or verification["targetDisagreements"] != target_disagreements or verification["priorHeldCellsReattestedUnchanged"] != 98:
        raise SystemExit("Verification report mismatch")

    print(f"PASS: W65 cross-audit covers 300 cells at exact head/tree; all {target_disagreements} primary/blind target differences are adjudicated; {len(prior)} prior holds are unchanged; all selected token checks and packet checksums pass.")

if __name__ == "__main__":
    verify()
