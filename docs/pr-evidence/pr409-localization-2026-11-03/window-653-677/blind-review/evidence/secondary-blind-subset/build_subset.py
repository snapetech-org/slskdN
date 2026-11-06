#!/usr/bin/env python3
import collections
import hashlib
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w71-653-677-20261103/candidate-free-packet/input")
OUT = pathlib.Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w71-es-hi-vi-653-677-independent-blind-20261103")
LOCALES = ("es", "hi", "vi")
RANKS = range(653, 678)
CONFIG = json.loads("{\"653\":{\"decision\":\"accept\",\"confidence\":\"moderate\",\"rationale\":\"The option appears between Trusted and Local in a scope selector; each translation plausibly labels the realm scope.\",\"locales\":{}},\"654\":{\"decision\":\"hold_context\",\"confidence\":\"low\",\"rationale\":\"The packet records no production caller for this key. The translations are plausible, but exact UI usage is unavailable and “transfer totals” could refer to counts or amounts; leave unchanged pending caller context.\",\"locales\":{}},\"655\":{\"decision\":\"accept\",\"confidence\":\"high\",\"rationale\":\"The caller localizes the issue type before interpolation. Keeping the leading separator and {type} unchanged preserves the composed label.\",\"locales\":{}},\"656\":{\"decision\":\"accept\",\"confidence\":\"moderate\",\"rationale\":\"The visible use is a footer label immediately before the latest build number; the event listener use is not rendered text.\",\"locales\":{\"es\":{\"decision\":\"revise\",\"confidence\":\"moderate\",\"reviewedTarget\":\"actualización\",\"rationale\":\"Use the noun form for the visible footer label before the build number; the current infinitive reads as an action.\"}}},\"657\":{\"decision\":\"accept\",\"confidence\":\"high\",\"rationale\":\"This is a VPN gateway table header; each target correctly labels the destination column.\",\"locales\":{}},\"658\":{\"decision\":\"accept\",\"confidence\":\"high\",\"rationale\":\"This is the search-list button that loads more search entries; the action is preserved.\",\"locales\":{\"vi\":{\"decision\":\"revise\",\"confidence\":\"moderate\",\"reviewedTarget\":\"Tải thêm lượt tìm kiếm\",\"rationale\":\"Add the natural Vietnamese counter “lượt” for the list of search entries.\"}}},\"659\":{\"decision\":\"accept\",\"confidence\":\"moderate\",\"rationale\":\"This tooltip describes searching the Soulseek interest graph for mesh accounts and their published capabilities.\",\"locales\":{\"es\":{\"decision\":\"revise\",\"confidence\":\"moderate\",\"reviewedTarget\":\"Busque en el grafo de intereses de Soulseek las cuentas de malla que hayan optado por participar y sus capacidades publicadas.\",\"rationale\":\"Use “grafo” for a network graph and express opted-in as choosing to participate; retain Soulseek exactly.\"},\"vi\":{\"decision\":\"revise\",\"confidence\":\"moderate\",\"reviewedTarget\":\"Tìm các tài khoản lưới đã chọn tham gia và các khả năng được công bố của họ trong đồ thị sở thích Soulseek.\",\"rationale\":\"Use “đồ thị” for a network graph and make the search relationship natural; retain Soulseek exactly.\"}}},\"660\":{\"decision\":\"accept\",\"confidence\":\"high\",\"rationale\":\"The footer link title identifies the slskdN project; all targets retain the brand exactly.\",\"locales\":{}},\"661\":{\"decision\":\"accept\",\"confidence\":\"high\",\"rationale\":\"This is a recurring cadence option grouped with Manual, Daily, and Monthly; each target means weekly.\",\"locales\":{}},\"662\":{\"decision\":\"accept\",\"confidence\":\"moderate\",\"rationale\":\"The notice explains that verification is read-only while warning about sensitive data in pasted messages and membership records.\",\"locales\":{\"hi\":{\"decision\":\"revise\",\"confidence\":\"moderate\",\"reviewedTarget\":\"सत्यापन जाँच से पॉड की स्थिति में बदलाव नहीं होना चाहिए, लेकिन चिपकाए गए संदेशों और सदस्यता रिकॉर्ड में अभी भी पीयर या हस्ताक्षर से जुड़ा संवेदनशील डेटा हो सकता है।\",\"rationale\":\"Use “पीयर” for a network peer; “सहकर्मी” suggests a coworker. The revision keeps the warning and pod-state meaning.\"},\"vi\":{\"decision\":\"revise\",\"confidence\":\"moderate\",\"reviewedTarget\":\"Các bước kiểm tra xác minh không được làm thay đổi trạng thái pod, nhưng tin nhắn được dán và hồ sơ thành viên vẫn có thể chứa dữ liệu nhạy cảm về các peer hoặc chữ ký.\",\"rationale\":\"Keep the technical term pod, translate messages as “tin nhắn” rather than mail, and preserve that both peer and signature data may be sensitive.\"}}},\"663\":{\"decision\":\"accept\",\"confidence\":\"high\",\"rationale\":\"This is a fallback display when member nicknames and identifiers are absent; each target means unknown member.\",\"locales\":{}},\"664\":{\"decision\":\"accept\",\"confidence\":\"moderate\",\"rationale\":\"The caller returns this as a visualizer mode alongside Beat and Off.\",\"locales\":{\"es\":{\"decision\":\"revise\",\"confidence\":\"moderate\",\"reviewedTarget\":\"Temporizado\",\"rationale\":\"Use an adjective for the visualizer mode label; “Por tiempo” reads as a loose adverbial phrase.\"}}},\"665\":{\"decision\":\"accept\",\"confidence\":\"high\",\"rationale\":\"This is the action button in a collection-sharing dialog; each target is a suitable share command.\",\"locales\":{}},\"666\":{\"decision\":\"accept\",\"confidence\":\"high\",\"rationale\":\"This is an error toast after stopping a search fails; each target expresses that the search could not be stopped.\",\"locales\":{}},\"667\":{\"decision\":\"accept\",\"confidence\":\"moderate\",\"rationale\":\"This error label precedes the registration error returned by a pod registration workflow.\",\"locales\":{\"vi\":{\"decision\":\"revise\",\"confidence\":\"moderate\",\"reviewedTarget\":\"Không thể đăng ký pod:\",\"rationale\":\"Retain the technical product term pod instead of translating it as a generic group.\"}}},\"668\":{\"decision\":\"accept\",\"confidence\":\"high\",\"rationale\":\"This is a duration field preceding elapsed seconds or milliseconds in report summaries.\",\"locales\":{\"vi\":{\"decision\":\"revise\",\"confidence\":\"moderate\",\"reviewedTarget\":\"Thời lượng:\",\"rationale\":\"Use “thời lượng” for elapsed duration; “khoảng thời gian” usually means a time interval.\"}}},\"669\":{\"decision\":\"revise\",\"confidence\":\"moderate\",\"rationale\":\"This is tooltip text for a preference that only organizes received results and does not contact more peers.\",\"locales\":{\"es\":{\"reviewedTarget\":\"Muestra debajo de las búsquedas de canciones el panel de revisión de álbumes candidatos. Solo organiza los resultados ya recibidos; no inicia otra búsqueda ni contacta con más pares.\",\"rationale\":\"Use “álbumes candidatos” and “pares” to preserve the candidate-review and peer-network meanings; retain the no-new-search limitation.\"},\"hi\":{\"reviewedTarget\":\"गीत खोजों के नीचे संभावित एल्बमों की समीक्षा का पैनल दिखाएँ। यह केवल पहले से मिले परिणामों को व्यवस्थित करता है; यह नई खोज शुरू नहीं करता और न ही अन्य पीयर से संपर्क करता है।\",\"rationale\":\"Make the candidate-review phrase more natural and use “पीयर” for network peers rather than generic companions.\"},\"vi\":{\"reviewedTarget\":\"Bên dưới các lượt tìm kiếm bài hát, hãy hiển thị bảng xem xét các album ứng viên. Bảng chỉ sắp xếp các kết quả đã nhận; không bắt đầu tìm kiếm mới hoặc liên hệ thêm các nút ngang hàng.\",\"rationale\":\"Translate candidates as “album ứng viên” rather than recommended albums, and specify peer nodes while keeping the no-new-search meaning.\"}}},\"670\":{\"decision\":\"accept\",\"confidence\":\"moderate\",\"rationale\":\"This is a discovery-graph node type listed beside track, songid_run, and mix.\",\"locales\":{\"vi\":{\"decision\":\"revise\",\"confidence\":\"moderate\",\"reviewedTarget\":\"phân đoạn\",\"rationale\":\"Use the neutral graph/data term “phân đoạn”; “phân khúc” commonly suggests a market segment.\"}}},\"671\":{\"decision\":\"accept\",\"confidence\":\"high\",\"rationale\":\"This is an ARIA label for an enable/disable checkbox; all translations preserve the {title} placeholder exactly.\",\"locales\":{}},\"672\":{\"decision\":\"revise\",\"confidence\":\"moderate\",\"rationale\":\"The sentence is followed by the HTTPS URL link, so the translation must lead naturally into that link and retain the protected literal TLS.\",\"locales\":{\"es\":{\"reviewedTarget\":\"Si su instancia ofrece TLS, inicie sesión de forma segura en\",\"rationale\":\"“Ofrece TLS” is more idiomatic for an instance that provides TLS; keep “en” because the URL follows immediately.\"},\"hi\":{\"reviewedTarget\":\"यदि आपके इंस्टेंस में TLS उपलब्ध है, तो यहाँ सुरक्षित रूप से साइन इन करें:\",\"rationale\":\"Restore exact protected literal TLS and connect the sentence to the following link; the current target transliterates TLS and omits that connection.\"},\"vi\":{\"reviewedTarget\":\"Nếu bản cài đặt của bạn hỗ trợ TLS, hãy đăng nhập an toàn tại\",\"rationale\":\"Use “bản cài đặt” and “hỗ trợ” for an application instance providing TLS; keep TLS and the link-introducing “tại”.\"}}},\"673\":{\"decision\":\"accept\",\"confidence\":\"moderate\",\"rationale\":\"This is the heading for an unavailable trace-data state in the swarm visualization.\",\"locales\":{\"es\":{\"decision\":\"revise\",\"confidence\":\"moderate\",\"reviewedTarget\":\"Datos de trazas no disponibles\",\"rationale\":\"Use “trazas” for technical trace data; “seguimiento” means tracking and can change the meaning.\"},\"vi\":{\"decision\":\"revise\",\"confidence\":\"moderate\",\"reviewedTarget\":\"Không có dữ liệu truy vết\",\"rationale\":\"Use “truy vết” for technical trace data; the current phrase reads as tracking data.\"}}},\"674\":{\"decision\":\"accept\",\"confidence\":\"moderate\",\"rationale\":\"This labels the aggregate totalVerdicts statistic in the quarantine jury view.\",\"locales\":{\"vi\":{\"decision\":\"revise\",\"confidence\":\"moderate\",\"reviewedTarget\":\"Phán quyết\",\"rationale\":\"“Phán quyết” fits jury verdicts; “bản án” usually means a court sentence.\"}}},\"675\":{\"decision\":\"accept\",\"confidence\":\"high\",\"rationale\":\"This is a player visualizer tile mode for album artwork; each target means album cover art.\",\"locales\":{}},\"676\":{\"decision\":\"accept\",\"confidence\":\"high\",\"rationale\":\"This is a time-window label; every translation preserves the {count} placeholder and the hours unit.\",\"locales\":{}},\"677\":{\"decision\":\"accept\",\"confidence\":\"moderate\",\"rationale\":\"This is the UserCard fallback when no canonical opinion records exist.\",\"locales\":{\"hi\":{\"decision\":\"revise\",\"confidence\":\"moderate\",\"reviewedTarget\":\"कोई आधिकारिक मत दर्ज नहीं है\",\"rationale\":\"Use “आधिकारिक” for the authoritative/canonical sense; “मान्य” can mean merely valid.\"},\"vi\":{\"decision\":\"revise\",\"confidence\":\"moderate\",\"reviewedTarget\":\"Chưa ghi nhận ý kiến chính thức\",\"rationale\":\"Use natural Vietnamese for authoritative/canonical opinions; “ý kiến chuẩn” sounds like standard opinions.\"}}}}")

def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()

def sha_text(value):
    return sha_bytes(value.encode("utf-8"))

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def placeholders(value):
    return re.findall(r"\{[^{}]+\}", value)

def number_tokens(value):
    return re.findall(r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])", value)

checksum = subprocess.run(["sha256sum", "-c", "PACKET-SHA256SUMS.txt"], cwd=ROOT, text=True, capture_output=True, check=True)
input_check = subprocess.run(["python3", "verify_input.py"], cwd=ROOT, text=True, capture_output=True, check=True)
input_verifier = json.loads(input_check.stdout)
manifest = read_json(ROOT / "manifest.json")
head = read_json(ROOT / "head-tree-attestation.json")
boundary = read_jsonl(ROOT / "selection-boundary.jsonl")
boundary_selected = [x for x in boundary if x.get("boundaryRole") == "selected"]
cells = [x for x in read_jsonl(ROOT / "source-current-cells.jsonl") if x.get("locale") in LOCALES and x.get("continuationRank") in RANKS]
contexts = {x["continuationRank"]: x for x in read_jsonl(ROOT / "caller-contexts.jsonl")}
prior_holds = read_jsonl(ROOT / "prior-held-cell-reattestation.jsonl")

assert input_verifier["verifier"] == "PASS"
assert input_verifier["priorHoldTargetMatches"] == input_verifier["priorHolds"]
assert len(boundary_selected) == 25
assert len({x["continuationRank"] for x in boundary_selected}) == 25
assert len(cells) == 75
assert len({(x["continuationRank"], x["locale"]) for x in cells}) == 75

selected_by_rank = {x["continuationRank"]: x for x in boundary_selected}
source_rows_by_rank = {}
for cell in cells:
    prior = source_rows_by_rank.setdefault(cell["continuationRank"], (cell["sourceId"], cell["source"], cell["sourceSha256"]))
    assert prior == (cell["sourceId"], cell["source"], cell["sourceSha256"])
    boundary_row = selected_by_rank[cell["continuationRank"]]
    assert boundary_row["sourceId"] == cell["sourceId"]
    assert boundary_row["sourceSha256"] == cell["sourceSha256"] == sha_text(cell["source"])
assert sorted(source_rows_by_rank) == list(RANKS)

hold_matches = 0
for row in prior_holds:
    current_hash = sha_text(row["currentTarget"])
    prior_hash = sha_text(row["priorTarget"])
    assert current_hash == row["currentTargetSha256"]
    assert prior_hash == row["priorTargetSha256"]
    assert current_hash == prior_hash
    assert row["matchesPriorCurrentValue"] is True
    hold_matches += 1
assert hold_matches == 140

ledger = []
input_literal_mismatches = collections.Counter()
output_literal_mismatches = collections.Counter()
for source in sorted(cells, key=lambda x: (x["continuationRank"], LOCALES.index(x["locale"]))):
    rank = source["continuationRank"]
    locale = source["locale"]
    row_config = CONFIG[str(rank)]
    base = {k: v for k, v in row_config.items() if k != "locales"}
    decision = {**base, **row_config.get("locales", {}).get(locale, {})}
    current = source["currentTarget"]
    reviewed = decision.get("reviewedTarget", current)
    assert decision["decision"] in ("accept", "revise", "hold_context")
    if decision["decision"] == "revise":
        assert reviewed != current
    else:
        assert reviewed == current

    p_ev = source["placeholderEvidence"]
    m_ev = source["markupEvidence"]
    protected = source["sourceProtectedLiterals"]
    numeric = source["sourceNumericTokens"]
    markup = m_ev["sourceTags"]
    ph_ok = collections.Counter(placeholders(reviewed)) == collections.Counter(p_ev["sourceTokens"])
    mark_ok = all(token in reviewed for token in markup)
    num_ok = all(token in reviewed for token in numeric)
    protected_ok = all(reviewed.count(token) >= protected.count(token) for token in protected)
    cell_mismatches = {
        "placeholder": bool(p_ev["matches"]),
        "markup": bool(m_ev["matches"]),
        "numeric": bool(source["numericTokensPreserved"]),
        "protectedLiteral": bool(source["protectedLiteralEvidence"]["matches"])
    }
    for kind, ok in cell_mismatches.items():
        if not ok:
            input_literal_mismatches[kind] += 1
    reviewed_mismatches = {
        "placeholder": ph_ok,
        "markup": mark_ok,
        "numeric": num_ok,
        "protectedLiteral": protected_ok
    }
    for kind, ok in reviewed_mismatches.items():
        if not ok:
            output_literal_mismatches[kind] += 1
    assert all(reviewed_mismatches.values()), (rank, locale, "reviewed target literal mismatch")

    context = contexts[rank]
    refs = [{
        "path": ref["path"],
        "line": ref["line"],
        "lineSha256": ref["lineSha256"],
        "contextSha256": ref["contextSha256"]
    } for ref in source["callerRefs"]]
    assert len(refs) == context["productionCallerCount"]
    assert [x["contextSha256"] for x in refs] == [x["contextSha256"] for x in context["callers"]]
    ledger.append({
        "window": "W71",
        "continuationRank": rank,
        "remainingQueueRank": source["remainingQueueRank"],
        "sourceId": source["sourceId"],
        "source": source["source"],
        "sourceSha256": source["sourceSha256"],
        "locale": locale,
        "currentTarget": current,
        "currentTargetSha256": source["currentTargetSha256"],
        "reviewedTarget": reviewed,
        "reviewedTargetSha256": sha_text(reviewed),
        "decision": decision["decision"],
        "confidence": decision["confidence"],
        "rationale": decision["rationale"],
        "callerContextSha256": source["callerContextSha256"],
        "callerCount": context["productionCallerCount"],
        "callerRefs": refs,
        "literalAudit": {
            "placeholdersPreserved": ph_ok,
            "markupPreserved": mark_ok,
            "numericTokensPreserved": num_ok,
            "protectedLiteralsPreserved": protected_ok,
            "sourcePlaceholderTokens": p_ev["sourceTokens"],
            "sourceMarkupTokens": markup,
            "sourceNumericTokens": numeric,
            "sourceProtectedLiterals": protected
        }
    })

decision_counts = collections.Counter(x["decision"] for x in ledger)
assert decision_counts == {"accept": 51, "revise": 21, "hold_context": 3}, decision_counts
assert sum(input_literal_mismatches.values()) == 1
assert output_literal_mismatches == collections.Counter()

rationale_lines = [
    "# Independent blind review — SlskdN PR #409 W71 ranks 653–677",
    "",
    "Scope: 75 cells in es, hi, and vi only. Review used the candidate-free exact-head packet and its pinned caller contexts. This is an AI-assisted editorial review; it is not native-speaker signoff.",
    "",
    "Decisions: 51 accept, 21 revise, 3 hold for missing caller context.",
    "",
    "Prior held-cell and selection reattestation is hash-only. No prior target text is included here.",
    "",
    "## Cell rationales",
    ""
]
for item in ledger:
    refs = item["callerRefs"]
    caller_text = "; ".join(f'{x["path"]}:{x["line"]} (context SHA-256 {x["contextSha256"]})' for x in refs) or "no production caller context captured"
    rationale_lines.append(
        f'- Rank {item["continuationRank"]} / {item["locale"]} — **{item["decision"]}** (confidence: {item["confidence"]}). '
        f'{item["rationale"]} Caller context: {caller_text}.'
    )
(OUT / "subset-ledger.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n" for x in ledger), encoding="utf-8")
(OUT / "subset-rationale.md").write_text("\n".join(rationale_lines) + "\n", encoding="utf-8")

boundary_bytes = (ROOT / "selection-boundary.jsonl").read_bytes()
selected_ids = [selected_by_rank[r]["sourceId"] for r in sorted(selected_by_rank)]
selected_id_digest = sha_text("\n".join(selected_ids))
hold_file_hash = sha_bytes((ROOT / "prior-held-cell-reattestation.jsonl").read_bytes())
source_file_hash = sha_bytes((ROOT / "source-current-cells.jsonl").read_bytes())
context_file_hash = sha_bytes((ROOT / "caller-contexts.jsonl").read_bytes())
metadata = {
    "artifact": "SlskdN PR #409 W71 independent blind subset review",
    "candidateFreeInput": str(ROOT),
    "repository": "snapetech-org/slskdN",
    "pullRequest": 409,
    "head": manifest["head"],
    "tree": manifest["tree"],
    "window": "W71",
    "continuationRankRange": [653, 677],
    "remainingQueueRankRange": [553, 577],
    "locales": list(LOCALES),
    "cellCount": len(ledger),
    "dispositionCounts": dict(decision_counts),
    "nativeSpeakerSignoff": False,
    "inputChecksumStatus": "PASS",
    "inputChecksumFilesVerified": 16,
    "inputVerifier": input_verifier,
    "inputSha256": {
        "manifest.json": sha_bytes((ROOT / "manifest.json").read_bytes()),
        "selection-boundary.jsonl": sha_bytes(boundary_bytes),
        "source-current-cells.jsonl": source_file_hash,
        "caller-contexts.jsonl": context_file_hash,
        "prior-held-cell-reattestation.jsonl": hold_file_hash
    },
    "priorHeldCellReattestation": {
        "count": hold_matches,
        "targetHashMatches": hold_matches,
        "targetHashMismatches": 0,
        "targetTextEmitted": False
    },
    "selectionReattestation": {
        "selectedSourceCount": len(selected_by_rank),
        "continuationRankRange": [min(selected_by_rank), max(selected_by_rank)],
        "selectedSourceIdsSha256": selected_id_digest,
        "selectionBoundarySha256": sha_bytes(boundary_bytes),
        "sourceTextHashMismatches": 0,
        "selectedSourceTextEmitted": False
    },
    "assignedSubsetCurrentLiteralMismatches": dict(input_literal_mismatches),
    "reviewedTargetLiteralMismatches": dict(output_literal_mismatches),
    "reviewedTargetLiteralAuditStatus": "PASS"
}
(OUT / "subset-metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "builder": "PASS",
    "cells": len(ledger),
    "dispositionCounts": dict(decision_counts),
    "priorHeldTargetHashMatches": hold_matches,
    "priorHeldTargetHashMismatches": 0,
    "selectedSourceHashMismatches": 0,
    "reviewedTargetLiteralMismatches": dict(output_literal_mismatches)
}, indent=2))

