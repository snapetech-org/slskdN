#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, re, subprocess, sys, unicodedata
from pathlib import Path

INPUT = Path("/mnt/disks/scratch/task-scratch/slskdn-pr409-w1028-1052-20261105/candidate-free")
REPO = Path("/home/keith/Documents/code/.task-worktrees/localization-20261105/slskdn-w978")
OUT = Path(__file__).resolve().parent
HEAD = "624e27d8bb108a764df6daab5cfb1c517ebac96d"
TREE = "d139a16988e23046ccb09f519db2d3b7ae0b86d1"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
PROTECTED = ["Ntfy", "Last.fm", "API", "WebGPU", "DHT", "Pod", "PodCore", "Wishlist", "soulfind", "FFmpeg", "Lidarr", "Soulseek", "slskdN"]

# Recommendations are generated only from the sealed candidate-free queue,
# exact-head current targets, and pinned production caller context.
PROPOSALS = {
    (1030, "id"): {
        "target": "Notifikasi Ntfy untuk pesan pribadi",
        "reasonCode": "semantic_mistranslation_brand_omitted",
        "reason": "The current Indonesian says private-message notifications cannot be received, reversing the setting label and omitting the Ntfy product name."
    },
    (1031, "ar"): {
        "target": " ث من المقطع",
        "reasonCode": "duration_unit_missing",
        "reason": "The caller concatenates this value after a duration number; the current target drops the seconds unit. The spaced Arabic seconds abbreviation keeps the inline value readable."
    },
    (1031, "es"): {
        "target": " s de clip",
        "reasonCode": "duration_unit_missing",
        "reason": "The caller appends this string directly to durationSeconds; the current target drops the seconds unit and joins the number directly to clip."
    },
    (1031, "fr"): {
        "target": " s de clip",
        "reasonCode": "duration_unit_missing",
        "reason": "The caller appends this string directly to durationSeconds; the current target begins with a determiner and omits the seconds unit."
    },
    (1031, "hi"): {
        "target": " सेकंड की क्लिप",
        "reasonCode": "duration_unit_missing",
        "reason": "The current transliteration of the letter s does not clearly express seconds in the caller's inline duration-plus-clip label."
    },
    (1031, "id"): {
        "target": " detik dari klip",
        "reasonCode": "duration_unit_missing",
        "reason": "The caller appends this string to a numeric duration; the current target names a clip but omits seconds and leaves the number joined to the noun."
    },
    (1031, "ja"): {
        "target": "秒のクリップ",
        "reasonCode": "duration_unit_missing",
        "reason": "The caller appends this string to durationSeconds; the current target omits seconds and reads as a clip count."
    },
    (1031, "ko"): {
        "target": "초 클립",
        "reasonCode": "duration_unit_missing",
        "reason": "The caller appends this string to durationSeconds; the current target omits seconds and reads as a clip count."
    },
    (1031, "pt-BR"): {
        "target": " s de clipe",
        "reasonCode": "duration_unit_missing",
        "reason": "The caller appends this string to durationSeconds; the current target omits seconds and joins the number directly to clipe."
    },
    (1031, "vi"): {
        "target": " giây của đoạn clip",
        "reasonCode": "duration_unit_missing",
        "reason": "The caller appends this string to durationSeconds; the current target omits the seconds unit and uses an incomplete phrase."
    },
    (1031, "zh-Hans"): {
        "target": "秒片段",
        "reasonCode": "duration_unit_missing",
        "reason": "The current target omits seconds, so the inline number reads as a clip count rather than a clip duration."
    },
    (1031, "zh-Hant"): {
        "target": "秒片段",
        "reasonCode": "duration_unit_missing",
        "reason": "The current target omits seconds, so the inline number reads as a clip count rather than a clip duration."
    },
    (1045, "fr"): {
        "target": "Saisissez les valeurs que vous souhaitez examiner. Elles restent sur cette page uniquement ; les actions d’aperçu et d’examen du contrat ne lancent aucun scan ni aucune autre opération côté serveur.",
        "reasonCode": "agreement_and_contract_action_clarity",
        "reason": "The current French pronoun Ils disagrees with feminine plural valeurs. The caller describes a local execution-contract review, so examen du contrat makes the action clear."
    },
    (1046, "vi"): {
        "target": "Các điều khiển nâng cao để tạo Pod liên kết với nội dung",
        "reasonCode": "product_entity_mistranslated",
        "reason": "The caller is for creating a federated Pod. The current word nhóm means a generic group and loses the product entity Pod."
    },
    (1047, "ja"): {
        "target": "ダウンロード先のパスが設定されています。",
        "reasonCode": "status_tense_mismatch",
        "reason": "The caller uses this as positive setup-health evidence. The current Japanese says the path will be configured, while the source reports that it is already configured."
    },
    (1048, "ar"): {
        "target": "حمّل أعداد الرسائل ونتائج توجيهها لمراجعة نشاط التسليم الأخير في Pod.",
        "reasonCode": "routing_counts_and_outcomes_incomplete",
        "reason": "The current Arabic says routing-result counts and omits the message count. The caller is a message-routing statistics control for Pod delivery activity."
    },
    (1050, "ar"): {
        "target": "مراجعة استكمال سجل الرسائل في Pod",
        "reasonCode": "backfill_term_mistranslated",
        "reason": "The caller explains that backfill requests missed messages and catches up Pod history; the current Arabic word suggests physical fill and translates Pod as a case."
    },
    (1050, "es"): {
        "target": "Revisión de la recuperación del historial de mensajes del Pod",
        "reasonCode": "backfill_and_pod_terms_mistranslated",
        "reason": "The caller is about recovering missed Pod message history. Reabastecimiento de cápsulas describes restocking capsules, not a Pod history backfill."
    },
    (1050, "fr"): {
        "target": "Examen du rattrapage de l’historique des messages du Pod",
        "reasonCode": "backfill_scope_incomplete",
        "reason": "The caller is about catching up missed Pod messages; remplissage des pods does not convey message-history backfill."
    },
    (1050, "id"): {
        "target": "Tinjauan pemulihan riwayat pesan Pod",
        "reasonCode": "backfill_scope_incomplete",
        "reason": "The caller is about recovering missed Pod messages; pengisian ulang suggests refilling rather than catching up message history."
    },
    (1050, "pt-BR"): {
        "target": "Revisão da recuperação do histórico de mensagens do Pod",
        "reasonCode": "backfill_scope_incomplete",
        "reason": "The caller is about recovering missed Pod messages; preenchimento de pod is too generic and loses the message-history backfill meaning."
    },
    (1050, "vi"): {
        "target": "Đánh giá việc bổ sung lịch sử tin nhắn cho Pod",
        "reasonCode": "backfill_and_pod_terms_mistranslated",
        "reason": "The caller is about adding missed message history to a federated Pod; nhóm means a generic group and chèn lấp does not clearly convey that operation."
    },
    (1051, "es"): {
        "target": "Copie un informe de revisión de una rama del grafo con familias de nodos visibles, familias de aristas, rutas sugeridas y semillas de búsqueda cercanas.",
        "reasonCode": "graph_branch_and_edge_terms",
        "reason": "The caller is a Discovery Graph report. Sucursales means business branches, and aristas is the graph term for edges."
    },
    (1051, "fr"): {
        "target": "Copiez un rapport d’examen d’une branche du graphe avec les familles de nœuds visibles, les familles d’arêtes, les itinéraires suggérés et les graines de recherche proches.",
        "reasonCode": "graph_edge_term",
        "reason": "The caller is a Discovery Graph report. Tronçons means segments; arêtes is the graph term for edges."
    }
}

ACCEPT_NOTES = {
    (1038, "ar"): "Accept the written Arabic word واحد as the fixed singular one: the caller selects this string only when exactly one deletion failed. The candidate-free numeric-token checker records a baseline mismatch because the numeral 1 is spelled out; semantic count is preserved.",
    (1039, "ja"): "The shorter wording for the search service remains clear in the caller's Pod-tag discovery context.",
    (1037, "es"): "Actor is the federated source-entity term used by the caller; retain it as domain terminology."
}

def need(ok, msg):
    if not ok:
        raise SystemExit("REFUSED: " + msg)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def sha_text(value):
    return sha(value.encode("utf-8"))

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def readj(path):
    return json.loads(path.read_text(encoding="utf-8"))

def readjl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def verify_sums(root):
    sums = {}
    for line in (root / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        need(name not in sums, "duplicate input checksum entry " + name)
        file = root / name
        need(file.is_file() and sha(file.read_bytes()) == digest, "input checksum mismatch " + name)
        sums[name] = digest
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"}
    need(actual == set(sums), "input checksum inventory mismatch")
    return sums

def token_evidence(source, target):
    placeholders = lambda s: collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", s))
    tags = lambda s: collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", s))
    numbers = lambda s: ["".join(str(unicodedata.digit(ch)) if ch.isdigit() else ch for ch in token) for token in re.findall(r"\d+", s)]
    source_placeholders, target_placeholders = placeholders(source), placeholders(target)
    source_tags, target_tags = tags(source), tags(target)
    source_numbers, target_numbers = numbers(source), numbers(target)
    protected = sorted(set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", source)) | {literal for literal in PROTECTED if literal in source})
    missing = [literal for literal in protected if literal not in target]
    return {
        "placeholdersMatch": source_placeholders == target_placeholders,
        "sourcePlaceholders": sorted(source_placeholders.elements()),
        "targetPlaceholders": sorted(target_placeholders.elements()),
        "markupMatches": source_tags == target_tags,
        "sourceMarkup": sorted(source_tags.elements()),
        "targetMarkup": sorted(target_tags.elements()),
        "numericSequencePreserved": all(target_numbers.count(value) >= count for value, count in collections.Counter(source_numbers).items()),
        "sourceNumbers": source_numbers,
        "targetNumbers": target_numbers,
        "protectedLiteralsPreserved": not missing,
        "sourceProtectedLiterals": protected,
        "missingProtectedLiterals": missing,
        "matches": source_placeholders == target_placeholders and source_tags == target_tags and
                   all(target_numbers.count(value) >= count for value, count in collections.Counter(source_numbers).items()) and not missing
    }

def main():
    need(OUT.is_dir(), "output directory")
    need(subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip() == HEAD, "worktree HEAD")
    need(subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD^{tree}"], text=True).strip() == TREE, "worktree tree")
    need(not subprocess.check_output(["git", "-C", str(REPO), "status", "--porcelain=v1"], text=True).strip(), "worktree dirty")

    verifier = subprocess.run([sys.executable, "-B", str(INPUT / "verify_candidate_free.py"), str(REPO)], capture_output=True, text=True)
    need(verifier.returncode == 0, "candidate-free verifier failed: " + verifier.stdout + verifier.stderr)
    input_sums = verify_sums(INPUT)
    input_manifest = readj(INPUT / "manifest.json")
    input_summary = readj(INPUT / "summary.json")
    need((input_manifest["head"], input_manifest["tree"], input_manifest["continuationRankRange"], input_manifest["cellCount"]) ==
         (HEAD, TREE, [1028, 1052], 300), "candidate-free input pin/scope")
    need(input_manifest["candidateFree"] is True and input_manifest["proposedTargetsIncluded"] is False and input_manifest["reviewDecisionsIncluded"] is False,
         "input is not candidate-free")
    need(input_summary["result"] == "PASS" and input_summary["sourceCount"] == 25 and input_summary["localeCount"] == 12, "candidate-free summary")

    source_rows = readjl(INPUT / "source-current-cells.jsonl")
    contexts = {row["continuationRank"]: row for row in readjl(INPUT / "caller-contexts.jsonl")}
    need(len(source_rows) == 300, "candidate-free cell count")
    need(len(PROPOSALS) == 24, "proposal count configuration")

    ledger = []
    decisions = collections.Counter()
    proposal_token_failures = []
    baseline_numeric_exceptions = []
    for cell in source_rows:
        rank = cell["continuationRank"]
        locale = cell["locale"]
        key = (rank, locale)
        context = contexts[rank]
        common = {
            "cellId": cell["sourceId"] + "::" + locale,
            "continuationRank": rank,
            "remainingQueueRank": cell["remainingQueueRank"],
            "sourceId": cell["sourceId"],
            "sourceIdSha256": cell["sourceIdSha256"],
            "sourceSha256": cell["sourceSha256"],
            "locale": locale,
            "currentTargetSha256": cell["currentTargetSha256"],
            "callerContextSha256": cell["callerContextSha256"],
            "callerCount": cell["callerCount"],
            "decision": None,
            "candidateFreeInputOnly": True
        }
        if cell.get("candidateFreeHold") is True:
            need(not cell.get("sourceTextIncluded") and not cell.get("currentTargetTextIncluded"), "candidate-free hold text exposure")
            need("source" not in cell and "currentTarget" not in cell, "candidate-free hold carries text")
            need(cell["callerCount"] == 0, "hash-only hold has caller")
            common.update({
                "decision": "hold_hash_only",
                "sourceTextIncluded": False,
                "targetTextIncluded": False,
                "recommendedTargetIncluded": False,
                "reasonCode": "no_pinned_production_caller",
                "reviewNote": "Preserve this cell as a hash-only hold; the candidate-free packet intentionally omits its source and target text."
            })
        else:
            need(cell.get("sourceTextIncluded") and cell.get("currentTargetTextIncluded"), "caller-backed cell lacks review text")
            need(cell["source"] == context["source"], "source/caller mismatch")
            need(cell["callerCount"] == context["productionCallerCount"] and cell["callerCount"] > 0, "caller count mismatch")
            need(sha(canonical(context["callers"])) == cell["callerContextSha256"], "caller context hash mismatch")
            common.update({
                "source": cell["source"],
                "currentTarget": cell["currentTarget"],
                "sourceTextIncluded": True,
                "targetTextIncluded": True,
                "recommendedTargetIncluded": False
            })
            proposal = PROPOSALS.get(key)
            if proposal:
                evidence = token_evidence(cell["source"], proposal["target"])
                if not evidence["matches"]:
                    proposal_token_failures.append({"cellId": common["cellId"], "evidence": evidence})
                common.update({
                    "decision": "revise",
                    "recommendedTarget": proposal["target"],
                    "recommendedTargetIncluded": True,
                    "reasonCode": proposal["reasonCode"],
                    "reviewNote": proposal["reason"],
                    "recommendationTokenEvidence": evidence,
                    "recommendationTokenEvidenceSha256": sha(canonical(evidence))
                })
            else:
                note = ACCEPT_NOTES.get(key, "The current translation preserves the source meaning in its pinned caller context.")
                if not cell.get("tokenChecksPass", True):
                    if (rank, locale) == (1038, "ar") and cell["tokenEvidence"]["numbers"]["source"] == ["1"] and cell["tokenEvidence"]["numbers"]["target"] == []:
                        baseline_numeric_exceptions.append(common["cellId"])
                        common["baselineTokenException"] = {
                            "kind": "numeric_spelling",
                            "sourceNumericToken": "1",
                            "currentTargetWordsForOne": "واحد",
                            "rationale": "The caller selects this fixed singular source only when one item failed; Arabic spells out the same quantity."
                        }
                    else:
                        need(False, "unresolved candidate-free token mismatch at " + common["cellId"])
                common.update({
                    "decision": "accept",
                    "reasonCode": "current_translation_acceptable",
                    "reviewNote": note
                })
        decisions[common["decision"]] += 1
        ledger.append(common)

    need(len(ledger) == 300, "ledger cell count")
    need(decisions == collections.Counter({"accept": 264, "revise": 24, "hold_hash_only": 12}), "decision distribution " + str(decisions))
    need(sorted(row["cellId"] for row in ledger) == sorted(row["sourceId"] + "::" + row["locale"] for row in source_rows), "ledger cell coverage")
    need(not proposal_token_failures, "recommendation token-safety failure")
    need(baseline_numeric_exceptions == ["src_39639ee9d9b7cce1::ar"], "baseline numeric mismatch disposition")
    need(set(PROPOSALS).issubset({(row["continuationRank"], row["locale"]) for row in source_rows}), "proposal outside scope")

    ledger.sort(key=lambda row: (row["continuationRank"], LOCALES.index(row["locale"])))
    (OUT / "blind-review.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in ledger),
        encoding="utf-8"
    )
    (OUT / "prior-active-holds-hash-only.jsonl").write_bytes((INPUT / "prior-held-cell-reattestation-hash-only.jsonl").read_bytes())
    (OUT / "current-window-holds-hash-only.jsonl").write_bytes((INPUT / "window-holds-hash-only.jsonl").read_bytes())
    (OUT / "prior-hold-resolution-history-hash-only.jsonl").write_bytes((INPUT / "prior-hold-resolution-history-hash-only.jsonl").read_bytes())

    summary = {
        "result": "PASS",
        "artifact": "slskdN PR #409 W1028-W1052 independent blind review",
        "head": HEAD,
        "tree": TREE,
        "continuationRankRange": [1028, 1052],
        "remainingQueueRankRange": [928, 952],
        "sourceCount": 25,
        "localeCount": 12,
        "cells": 300,
        "callerBackedCells": 288,
        "hashOnlyCells": 12,
        "decisions": dict(sorted(decisions.items())),
        "recommendations": 24,
        "recommendationTokenFailures": 0,
        "baselineNumericExceptionCount": 1,
        "baselineNumericExceptionCell": baseline_numeric_exceptions[0],
        "priorActiveHoldsCarriedHashOnly": 421,
        "currentWindowHashOnlyHolds": 12,
        "resultingActiveHashOnlyHolds": 433,
        "priorHoldResolutionRowsCarriedHashOnly": 25,
        "candidateFreeVerifier": "PASS",
        "candidateFreeChecksumEntries": len(input_sums),
        "candidateFreeChecksumListSha256": sha((INPUT / "SHA256SUMS.txt").read_bytes()),
        "primaryPacketRead": False,
        "W1003W1027RecommendationsOrProposalsRead": False,
        "catalogsEdited": False,
        "testsBuildsScansCiRun": False
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    readme = (
        "# slskdN PR #409 W1028–W1052 independent blind review\n\n"
        "Pinned to head " + HEAD + " / tree " + TREE + ". The sealed candidate-free input is "
        + str(INPUT) + " and passed its verifier and SHA256 checks before review.\n\n"
        "The ledger covers 300 cells: 264 accepted current translations, 24 advisory revision recommendations, and 12 hash-only holds for the no-caller source at rank 1033. It carries forward 421 prior active holds and the current-window 12 hash-only rows without exposing text. One baseline token mismatch is accepted as Arabic spelling out the fixed quantity one; the caller selects the singular message only when exactly one item failed.\n\n"
        "Review used only the candidate-free queue, current source/target values, and pinned production caller context. The primary review was not opened, and W1003–W1027 recommendations/proposals were not read. Recommendations are advisory; nothing was applied. No repository files were edited and no tests, builds, scans, or CI were run.\n"
    )
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    output_files = sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob("*") if p.is_file() and p.name not in {"manifest.json", "SHA256SUMS.txt"})
    manifest = {
        "schemaVersion": 1,
        "repository": "snapetech-org/slskdN",
        "pullRequest": 409,
        "window": "W86 / W1028-W1052",
        "artifactKind": "independent-blind-review",
        "head": HEAD,
        "tree": TREE,
        "continuationRankRange": [1028, 1052],
        "remainingQueueRankRange": [928, 952],
        "sourceCount": 25,
        "localeCount": 12,
        "cellCount": 300,
        "locales": LOCALES,
        "candidateFreeInputPath": str(INPUT),
        "candidateFreeManifestSha256": sha((INPUT / "manifest.json").read_bytes()),
        "candidateFreeChecksumListSha256": sha((INPUT / "SHA256SUMS.txt").read_bytes()),
        "candidateFreeVerifier": "PASS",
        "candidateFreeInputVerifiedFiles": len(input_sums),
        "decisions": dict(sorted(decisions.items())),
        "recommendations": 24,
        "priorActiveHoldsCarriedHashOnly": 421,
        "currentWindowHashOnlyHolds": 12,
        "resultingActiveHashOnlyHolds": 433,
        "baselineNumericExceptionCell": baseline_numeric_exceptions[0],
        "primaryReviewRead": False,
        "W1003W1027RecommendationsOrProposalsRead": False,
        "catalogsEdited": False,
        "testsBuildsScansCiRun": False,
        "files": [{"path": name, "sha256": sha((OUT / name).read_bytes()), "bytes": (OUT / name).stat().st_size} for name in output_files]
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    names = sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    (OUT / "SHA256SUMS.txt").write_text("".join(sha((OUT / name).read_bytes()) + "  " + name + "\n" for name in names), encoding="utf-8")

if __name__ == "__main__":
    main()

