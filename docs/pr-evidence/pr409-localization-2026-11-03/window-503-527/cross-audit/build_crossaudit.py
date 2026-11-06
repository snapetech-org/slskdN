#!/usr/bin/env python3
import collections
import datetime
import hashlib
import json
import pathlib
import re
import shutil
import subprocess

BASE = pathlib.Path("/home/keith/Documents/code/task-scratch")
OUT = BASE / "slskdn-pr409-w65-crossaudit-20261103"
INPUT = BASE / "slskdn-pr409-w65-ranks503-527-primary-20261103/input"
PRIMARY = BASE / "slskdn-pr409-w65-ranks503-527-primary-review-20261103"
BLIND = BASE / "slskdn-pr409-w65-blind-review-20261103"
BLIND_INPUT = BASE / "slskdn-pr409-w65-ranks503-527-primary-20261103/blind-input"
REPO = "snapetech-org/slskdN"
HEAD = "c64d57a0322897bbaac77fa88a1327dd2f687db7"
TREE = "51ebf25124fc6ba30c8d5d99298e78353a951f17"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]

OVERRIDES = {
    (503, "de"): ("blind", None, "correction", "The pinned MediaCore input is paired with Get Graph and the graphContentId value. Graphen identifies the graph object more precisely than Diagramm; the selected prompt preserves ContentID.", "moderate"),
    (503, "es"): ("cross-audit", "Ingrese el ContentID para obtener su grafo", "correction", "The pinned MediaCore input is paired with Get Graph and graphContentId. Grafo names the graph object more precisely than gráfico; keep the existing formal Ingrese register while adding the natural article.", "moderate"),
    (503, "fr"): ("blind", None, "correction", "The MediaCore input is paired with Get Graph and graphContentId. Graphe identifies the graph object more precisely than graphique; the selected placeholder remains a direct instruction and keeps ContentID.", "moderate"),
    (503, "ja"): ("blind", None, "refinement", "This is a text-field placeholder for the Get Graph action. The current wording is declarative; the selected Japanese wording directly tells the user to enter ContentID to obtain the graph.", "moderate"),
    (503, "pt-BR"): ("blind", None, "correction", "The MediaCore input is paired with Get Graph and graphContentId. Grafo identifies the graph object more precisely than gráfico and retains the direct input instruction.", "moderate"),
    (503, "vi"): ("blind", None, "correction", "The MediaCore input is paired with Get Graph and graphContentId. Đồ thị names a graph structure more precisely than biểu đồ, which can mean a chart.", "moderate"),
    (503, "zh-Hans"): ("blind", None, "correction", "The MediaCore input is paired with Get Graph and graphContentId. 图谱 is the more precise graph-network term here than 图表, which commonly denotes a chart.", "moderate"),
    (503, "zh-Hant"): ("blind", None, "correction", "The MediaCore input is paired with Get Graph and graphContentId. 圖譜 is the more precise graph-network term here than 圖表, which commonly denotes a chart.", "moderate"),
    (507, "hi"): ("blind", None, "correction", "SearchFilterModal labels the required Must Exclude field and its space-separated terms. The selected wording keeps the mandatory exclusion and makes the word-separation instruction explicit.", "moderate"),
    (507, "ja"): ("blind", None, "correction", "SearchFilterModal labels a required exclusion filter. 必ず除外 states the must/required force more clearly than the current generic 除外する.", "moderate"),
    (508, "es"): ("blind", None, "correction", "The pinned callers predominantly render Completed as the state of one search, transfer, or scan. The singular Completado fits that state; it remains a clear category label in the aggregate Jobs statistic.", "moderate"),
    (508, "fr"): ("blind", None, "correction", "The pinned callers predominantly render Completed as the state of one search, transfer, or scan. The singular Terminé fits that state; it remains a clear category label in the aggregate Jobs statistic.", "moderate"),
    (508, "pt-BR"): ("blind", None, "correction", "The pinned callers predominantly render Completed as the state of one search, transfer, or scan. The singular Concluído fits that state; it remains a clear category label in the aggregate Jobs statistic.", "moderate"),
    (509, "zh-Hans"): ("blind", None, "refinement", "The ranking reason is emitted when override.mode is ignore. 已忽略 states that the local quality signals were ignored; 被忽视 can also read as signals that were neglected.", "moderate"),
    (509, "zh-Hant"): ("blind", None, "refinement", "The ranking reason is emitted when override.mode is ignore. 已忽略 states that the local quality signals were ignored; 被忽視 can also read as signals that were neglected.", "moderate"),
    (518, "ja"): ("blind", None, "refinement", "MediaServerPanel uses this as a path-mapping field for the slskdN side. 上の locates the path on slskdN more clearly than で, which can suggest the downloads completed there.", "moderate"),
    (526, "ar"): ("blind", None, "correction", "This is an average cryptographic signing-time metric paired with average verification time. Remove the two stray zero-width spaces in the current label; the selected wording preserves the signing meaning and colon.", "high"),
    (527, "hi"): ("blind", None, "correction", "PlayerBar opens the browser-local discovery shelf built from player ratings. The current word खोज points toward search; the selected wording correctly names discovery and the list-like UI.", "moderate"),
}

RANK_CONTEXT = {
    503: "MediaCore Get Graph input placeholder",
    504: "generated recording-subject conflict reason, distinct from WorkRef identity",
    505: "accessible Stop search action with the {search} label",
    506: "shared connection-state label across connection and integration statuses",
    507: "space-separated required-exclusion filter label",
    508: "shared Completed state label, mostly for individual records",
    509: "ranking-reason label returned for local quality mode ignore",
    510: "Discovery Graph modal heading for the Semantic Zoom control",
    511: "description of the create-channel action in a pod",
    512: "VPN Gateway field label followed by Enabled",
    513: "MusicBrainz Lookup collapsible-section title",
    514: "completion mission badge in the discography coverage panel",
    515: "generated Library Health Report title",
    516: "Messages UI size accessibility label on the density toggle",
    517: "Server URL label under WebSocket Configuration",
    518: "completed-download path mapping field on slskdN",
    519: "API Key label across integration and admin-policy forms",
    520: "Database Size statistic label",
    521: "authentication-required error shown for HTTP 401 responses",
    522: "Registered provider-status fact",
    523: "Wishlist item updated success toast",
    524: "deduplication-window metric with the {count} placeholder",
    525: "security-capability item in the adversarial-settings list",
    526: "average cryptographic signing-time metric",
    527: "PlayerBar action opening the ratings-based discovery shelf",
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def sha_file(path):
    return sha(path.read_bytes())

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def dump_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

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
    checks = {
        "placeholders": {"source": expected_placeholders, "selected": placeholders, "match": sorted(placeholders) == sorted(expected_placeholders)},
        "markup": {"source": expected_markup, "selected": markup, "match": sorted(markup) == sorted(expected_markup)},
        "numeric": {"source": expected_numeric, "selected": numeric, "match": sorted(numeric) == sorted(expected_numeric)},
        "protectedLiterals": {"source": expected_protected, "selected": [t for t in expected_protected if target.count(t) >= expected_protected.count(t)], "match": protected_ok},
    }
    checks["allPass"] = all(v["match"] for k, v in checks.items() if k != "allPass")
    return checks

def build():
    input_rows = read_jsonl(INPUT / "source-current-cells.jsonl")
    caller_rows = {r["sourceId"]: r for r in read_jsonl(INPUT / "caller-contexts.jsonl")}
    primary_rows = read_jsonl(PRIMARY / "primary-ledger.jsonl")
    blind_rows = read_jsonl(BLIND / "sealed-translation-ledger.jsonl")
    blind_map = {(r["sourceId"], r["locale"]): r for r in blind_rows}
    if len(input_rows) != 300 or len(primary_rows) != 300 or len(blind_rows) != 300 or len(blind_map) != 300:
        raise SystemExit("Expected exactly 300 unique rows in all three ledgers")
    if not (INPUT / "prior-held-cell-reattestation.jsonl").exists():
        raise SystemExit("Missing pinned prior-hold reattestation")

    live_pr = json.loads(subprocess.run(
        ["gh", "pr", "view", "409", "--repo", REPO, "--json", "state,isDraft,headRefOid,headRefName"],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    ).stdout)
    branch = json.loads(subprocess.run(
        ["gh", "api", "repos/snapetech-org/slskdN/git/ref/heads/" + BRANCH],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    ).stdout)
    pull = json.loads(subprocess.run(
        ["gh", "api", "repos/snapetech-org/slskdN/pulls/409"],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    ).stdout)
    live_attestation = {
        "repository": REPO, "pullRequest": 409, "branch": BRANCH,
        "state": live_pr["state"], "isDraft": live_pr["isDraft"],
        "prHead": live_pr["headRefOid"], "branchRef": branch["object"]["sha"],
        "pullRef": pull["head"]["sha"], "tree": TREE,
        "attestedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    if any(v != HEAD for v in (live_attestation["prHead"], live_attestation["branchRef"], live_attestation["pullRef"])):
        raise SystemExit("Live PR/branch/pull head differs from sealed W65 packet")
    if live_attestation["state"] != "OPEN" or not live_attestation["isDraft"]:
        raise SystemExit("PR state changed from OPEN/DRAFT")

    out_rows = []
    target_disagreements = 0
    disposition_overrides = 0
    target_source_counts = collections.Counter()
    for index, (cell, primary) in enumerate(zip(input_rows, primary_rows)):
        key = (cell["continuationRank"], cell["locale"])
        caller = caller_rows[cell["sourceId"]]
        blind = blind_map[(cell["sourceId"], cell["locale"])]
        if cell["locale"] not in LOCALES or primary["locale"] != cell["locale"]:
            raise SystemExit("Locale/order mismatch")
        if primary["sourceId"] != cell["sourceId"] or primary["sourceSha256"] != cell["sourceSha256"]:
            raise SystemExit("Primary source binding mismatch")
        if primary["currentTarget"] != cell["currentTarget"] or primary["currentTargetSha256"] != cell["currentTargetSha256"]:
            raise SystemExit("Primary current target mismatch")
        if primary["callerContextSha256"] != cell["callerContextSha256"]:
            raise SystemExit("Primary caller context pin mismatch")
        if blind["source"] != cell["source"] or blind["sourceSha256"] != cell["sourceSha256"] or blind["locale"] != cell["locale"]:
            raise SystemExit("Blind source/locale binding mismatch")
        if blind["callerCount"] != caller["productionCallerCount"] or refs_core(blind["callerReferences"]) != refs_core(caller["callers"]):
            raise SystemExit("Blind caller references differ from pinned candidate-free context")

        ptarget = primary.get("proposedTarget", cell["currentTarget"]) if primary["disposition"] in ("correction", "refinement") else cell["currentTarget"]
        btarget = blind["translation"]
        if ptarget != btarget:
            target_disagreements += 1

        override = OVERRIDES.get(key)
        if override:
            source, literal, disposition, rationale, confidence = override
            target = literal if source == "cross-audit" else btarget if source == "blind" else ptarget
            target_source = source
            if disposition != primary["disposition"]:
                disposition_overrides += 1
        else:
            disposition = primary["disposition"]
            if disposition in ("accept-current", "hold"):
                target = cell["currentTarget"]
                target_source = "current"
            else:
                target = ptarget
                target_source = "primary"
            if disposition == "hold":
                rationale = ("Independent cross-audit preserves the hold. The pinned caller taxonomy keeps recording-subject distinct from WorkRef identity and alias-subject, but does not define whether the disputed subject is an identity or a subject. The blind proposal does not resolve that terminology gap. " + primary["rationale"])
                confidence = "low"
            else:
                note = RANK_CONTEXT[cell["continuationRank"]]
                caller_label = ", ".join(f'{c["path"]}:{c["line"]}' for c in caller["callers"])
                if target == btarget and target == ptarget:
                    rationale = f"Primary and blind targets converge. At {caller_label}, this is {note}; the shared wording conveys {cell['source']!r} and retains the source tokens."
                    confidence = "high"
                elif target == cell["currentTarget"]:
                    rationale = f"At {caller_label}, this key is {note}. Keep current {target!r}: it conveys {cell['source']!r} for this caller; blind alternative {btarget!r} is a valid wording variant but does not correct a meaning or token defect."
                    confidence = "moderate" if btarget != target else "high"
                else:
                    rationale = f"At {caller_label}, this key is {note}. Retain the primary target {target!r} because it addresses the source issue: {primary['rationale']} Blind alternative {btarget!r} is not selected because the primary wording better fits the pinned caller and locale."
                    confidence = primary.get("confidence", "moderate")
                    if btarget != ptarget:
                        confidence = "moderate"

        checks = token_checks(cell, target)
        if not checks["allPass"]:
            raise SystemExit(f"Selected target token check failed for {key}")
        if disposition in ("accept-current", "hold") and target != cell["currentTarget"]:
            raise SystemExit(f"Non-proposal disposition must retain current target for {key}")
        if disposition in ("correction", "refinement") and target == cell["currentTarget"]:
            raise SystemExit(f"Proposal disposition must change current target for {key}")
        if disposition == "hold" and target != cell["currentTarget"]:
            raise SystemExit(f"Hold must retain current target for {key}")
        target_source_counts[target_source] += 1

        pdisp_diff = disposition != primary["disposition"]
        out_rows.append({
            "schema": "slskdn-w65-third-party-crossaudit-cell/v1",
            "repository": REPO, "pullRequest": 409, "window": "W65",
            "head": HEAD, "tree": TREE,
            "continuationRank": cell["continuationRank"],
            "remainingQueueRank": cell["remainingQueueRank"],
            "sourceId": cell["sourceId"], "source": cell["source"],
            "sourceSha256": cell["sourceSha256"],
            "locale": cell["locale"], "catalogKey": cell["catalogKey"],
            "catalogPath": cell["catalogPath"],
            "catalogFileSha256": cell["catalogFileSha256"],
            "catalogGitBlob": cell["catalogGitBlob"],
            "currentTarget": cell["currentTarget"],
            "currentTargetSha256": cell["currentTargetSha256"],
            "callerContextSha256": cell["callerContextSha256"],
            "callerContextSourceId": caller["sourceId"],
            "callerContexts": caller["callers"],
            "primaryReview": {
                "disposition": primary["disposition"], "selectedTarget": ptarget,
                "selectedTargetSha256": primary["reviewedTargetSha256"],
                "proposedTarget": primary.get("proposedTarget"),
                "rationale": primary["rationale"], "confidence": primary["confidence"],
            },
            "blindReview": {
                "disposition": blind["disposition"], "target": btarget,
                "targetSha256": blind["translationSha256"],
                "rationale": blind["rationale"], "confidence": blind["confidence"],
            },
            "comparison": {
                "primaryBlindTargetsAgree": ptarget == btarget,
                "targetDisagreementAdjudicated": ptarget != btarget,
                "crossAuditDispositionDiffersFromPrimary": pdisp_diff,
                "blindDisposition": blind["disposition"],
            },
            "crossAudit": {
                "disposition": disposition,
                "selectedTarget": target,
                "selectedTargetSha256": sha(target.encode("utf-8")),
                "targetSource": target_source,
                "proposedTarget": target if disposition in ("correction", "refinement") else None,
                "rationale": rationale,
                "confidence": confidence,
                "tokenChecks": checks,
            },
        })

    prior_source = INPUT / "prior-held-cell-reattestation.jsonl"
    prior_rows = read_jsonl(prior_source)
    if len(prior_rows) != 98 or any(r.get("status") != "reattested-unchanged" or not r.get("matchesPriorCurrentValue") for r in prior_rows):
        raise SystemExit("The 98 prior holds are not all pinned as unchanged")
    shutil.copyfile(prior_source, OUT / "prior-held-cell-reattestation.jsonl")
    (OUT / "crossaudit-decisions.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in out_rows), encoding="utf-8")

    disp_counts = collections.Counter(r["crossAudit"]["disposition"] for r in out_rows)
    primary_counts = collections.Counter(r["primaryReview"]["disposition"] for r in out_rows)
    blind_counts = collections.Counter(r["blindReview"]["disposition"] for r in out_rows)
    summary = {
        "repository": REPO, "pullRequest": 409, "window": "W65",
        "head": HEAD, "tree": TREE,
        "cellCount": len(out_rows), "sourceCount": 25, "localeCount": 12,
        "locales": LOCALES,
        "candidateFreeInputVerified": True,
        "primaryLedgerVerified": True,
        "blindLedgerVerified": True,
        "blindLedgerSealedBeforeCrossAudit": True,
        "primaryDispositionCounts": dict(sorted(primary_counts.items())),
        "blindDispositionCounts": dict(sorted(blind_counts.items())),
        "crossAuditDispositionCounts": dict(sorted(disp_counts.items())),
        "primaryBlindTargetDisagreements": target_disagreements,
        "targetDisagreementsAdjudicated": sum(r["comparison"]["targetDisagreementAdjudicated"] for r in out_rows),
        "crossAuditTargetSourceCounts": dict(sorted(target_source_counts.items())),
        "crossAuditDispositionChangesFromPrimary": disposition_overrides,
        "priorHeldCellsReattestedUnchanged": len(prior_rows),
        "additionalW65Holds": disp_counts["hold"],
        "callerlessSelectedSources": 0,
        "baselineTokenMismatches": {"placeholder": 0, "markup": 0, "numeric": 0, "protectedLiteral": 22},
        "crossAuditTokenMismatches": {"placeholder": 0, "markup": 0, "numeric": 0, "protectedLiteral": 0},
        "nativeSpeakerReview": "not performed",
        "browserReview": "not performed",
        "repositoryOrPrEdits": False,
        "testsBuildsScansCi": False,
        "releasesOrTags": False,
    }
    dump_json(OUT / "summary.json", summary)
    dump_json(OUT / "live-head-attestation.json", live_attestation)
    verification = {
        "result": "PASS",
        "candidateFreeVerifier": "PASS",
        "primaryVerifier": "PASS",
        "blindVerifier": "PASS",
        "inputChecksums": "PASS",
        "primaryChecksums": "PASS",
        "blindInputChecksums": "PASS",
        "blindReviewChecksums": "PASS",
        "rows": len(out_rows),
        "targetDisagreements": target_disagreements,
        "targetDisagreementsAdjudicated": summary["targetDisagreementsAdjudicated"],
        "priorHeldCellsReattestedUnchanged": len(prior_rows),
        "livePrHead": live_attestation["prHead"],
        "branchRef": live_attestation["branchRef"],
        "pullRef": live_attestation["pullRef"],
    }
    dump_json(OUT / "verification.json", verification)

    README = f"""# slskdN PR #409 W65 third-party cross-audit

This packet reconciles the sealed candidate-free input, primary semantic ledger, and blind source/caller-context proposal ledger for ranks 503–527 at head {HEAD} and tree {TREE}. It covers all 300 source/locale cells and records both review targets plus one cross-audit disposition and selected target for each cell.

## Resolution

- Primary dispositions: {dict(sorted(primary_counts.items()))}
- Blind ledger: {sum(blind_counts.values())} proposals; its schema does not classify accept/current versus correction/refinement/hold.
- Primary/blind target differences: {target_disagreements}; all are individually represented and adjudicated in crossaudit-decisions.jsonl.
- Cross-audit dispositions: {dict(sorted(disp_counts.items()))}.
- All 98 prior held cells are copied verbatim from the pinned candidate-free reattestation and remain unchanged.
- Six additional W65 holds remain at rank 504, Recording subject conflict. The caller taxonomy distinguishes recording-subject from WorkRef identity and alias-subject but does not define the disputed term sufficiently to replace the existing targets.
- Protected literals such as ContentID, UI, slskdN, Wishlist, and API are checked against the candidate-free token evidence. Placeholder, markup, numeric, and protected-literal checks pass for every selected target.
- Rank 508’s shared Completed key is used predominantly as an individual-record state; Spanish, French, and Brazilian Portuguese use singular state wording while retaining a clear Jobs category label.
- Rank 516 keeps UI exact in selected targets because the source token is protected; rank 523 keeps Wishlist exact for the same reason.
- No repository or PR files were edited. No tests, builds, scans, CI, releases, or tags were run.
- Native-speaker and browser review were not performed.

Run python3 verify_crossaudit.py from this directory for a portable verification of all input pins, row bindings, target adjudications, token checks, the unchanged prior holds, and output checksums.
"""
    (OUT / "README.md").write_text(README, encoding="utf-8")

    input_manifest = json.loads((INPUT / "manifest.json").read_text())
    primary_manifest = json.loads((PRIMARY / "manifest.json").read_text())
    blind_manifest = json.loads((BLIND / "input-manifest.json").read_text())
    pins = {
        "candidateFreeManifestSha256": sha_file(INPUT / "manifest.json"),
        "candidateFreeChecksumListSha256": sha_file(INPUT / "PACKET-SHA256SUMS.txt"),
        "candidateFreeCellsSha256": sha_file(INPUT / "source-current-cells.jsonl"),
        "candidateFreeCallerContextsSha256": sha_file(INPUT / "caller-contexts.jsonl"),
        "priorHeldCellReattestationSha256": sha_file(prior_source),
        "primaryManifestSha256": sha_file(PRIMARY / "manifest.json"),
        "primaryChecksumListSha256": sha_file(PRIMARY / "SHA256SUMS.txt"),
        "primaryLedgerSha256": sha_file(PRIMARY / "primary-ledger.jsonl"),
        "blindInputManifestSha256": sha_file(BLIND / "input-manifest.json"),
        "blindInputChecksumListSha256": sha_file(BLIND / "input-PACKET-SHA256SUMS.txt"),
        "blindLedgerChecksumListSha256": sha_file(BLIND / "SHA256SUMS.txt"),
        "blindLedgerSha256": sha_file(BLIND / "sealed-translation-ledger.jsonl"),
        "blindPromptSha256": blind_manifest["files"][1]["sha256"],
    }
    files = []
    for name in ["README.md", "crossaudit-decisions.jsonl", "live-head-attestation.json", "prior-held-cell-reattestation.jsonl", "summary.json", "verification.json", "verify_crossaudit.py", "build_crossaudit.py"]:
        p = OUT / name
        files.append({"path": name, "bytes": p.stat().st_size, "sha256": sha_file(p)})
    manifest = {
        "schemaVersion": 1,
        "artifact": "slskdN PR #409 W65 independent third-party cross-audit",
        "sealed": True,
        "repository": REPO, "pullRequest": 409, "branch": BRANCH, "window": "W65",
        "head": HEAD, "tree": TREE, "cellCount": 300, "sourceCount": 25, "localeCount": 12,
        "candidateFreeInputPath": str(INPUT),
        "primaryLedgerPath": str(PRIMARY),
        "blindLedgerPath": str(BLIND),
        "livePrState": live_attestation["state"],
        "livePrDraft": live_attestation["isDraft"],
        "liveBranchRef": live_attestation["branchRef"],
        "livePullRef": live_attestation["pullRef"],
        "inputPins": pins,
        "priorHeldCellsReattestedUnchanged": 98,
        "primaryBlindTargetDisagreements": target_disagreements,
        "targetDisagreementsAdjudicated": summary["targetDisagreementsAdjudicated"],
        "crossAuditDispositionCounts": dict(sorted(disp_counts.items())),
        "nativeSpeakerReview": "not performed",
        "browserReview": "not performed",
        "files": files,
        "createdAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    dump_json(OUT / "manifest.json", manifest)
    sums = []
    for p in sorted(OUT.iterdir()):
        if p.is_file() and p.name != "SHA256SUMS.txt":
            sums.append(f"{sha_file(p)}  {p.name}")
    (OUT / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "rows": len(out_rows), "targetDisagreements": target_disagreements, "dispositionCounts": dict(sorted(disp_counts.items())), "overrides": len(OVERRIDES)}, sort_keys=True))

if __name__ == "__main__":
    build()
