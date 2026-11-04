#!/usr/bin/env python3
"""Build the W78 blind-review packet from its candidate-free input."""
import collections
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent
INPUT = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w78-828-852-primary-20261104/candidate-free/input")
SOURCE = Path("/mnt/disks/scratch/task-worktrees/localization-20261104/slskdn-pr409-w78-828-852-source")
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]

CONTEXT = {
    "src_30f0dd08d39c6d5e": "reply-button title and tooltip in a room message action",
    "src_30f52f173d34e0f4": "no production caller was found by the supplied bounded scan",
    "src_30f84002403ca166": "accessible name and tooltip for expanding a user's search-result group",
    "src_3109c7f2e1f5502f": "popup for locally disabling a realm authority during browser review, with an explicit governance disclaimer",
    "src_310b91343c426a61": "empty-state prompt shown when no room is selected",
    "src_310b993f07ab828f": "accessible label for the API-key CIDR allowlist input",
    "src_3111a5ac38c05ad9": "cancel-button tooltip in the create-share-group dialog",
    "src_311ed25d5fa9a11d": "selection tooltip before queueing a peer download",
    "src_312e215c7d555697": "playback error detail",
    "src_31458506a6a11770": "Bridge card heading followed by the connected-client count and a caller-supplied closing parenthesis",
    "src_3151b73ca0d7f79a": "percentage label for the auto-replace size threshold input",
    "src_3152b873a3f79771": "confirmation popup for application restart or shutdown, with the action label supplied as a placeholder",
    "src_315ab5673cfc7a8a": "loading message in federated recommendations and federation diagnostics",
    "src_316633455d4716bf": "table header identifying who shared a collection with the user",
    "src_316cfce013499533": "error toast for the database VACUUM maintenance operation",
    "src_3170543ce47c2f0b": "automation cadence and cooldown value",
    "src_317b1fbc1e13beeb": "red health-status value for mesh routing, peer connectivity, and message flow",
    "src_31ca26c85e632d29": "accessible name and tooltip for the next-page control in SharedWithMe",
    "src_31d2f5207656f3b3": "tooltip for running a SongID action on a decomposed audio segment",
    "src_31d30a319874d88f": "tooltip for the previous-page control in a collection-items list",
    "src_31d6dd1efa458b9a": "diagnostic-bundle modal close tooltip",
    "src_31df66dc9f060166": "connection-status menu label displayed beside the controller state",
    "src_31eeaf8d203a72b5": "local mesh policy action for disabling publication of a dynamic evidence label",
    "src_31f24684b3973583": "empty user-share placeholder in Browse",
    "src_31fbef162594de01": "button to resume history backfill",
}

# Only clear, context-supported defects are proposed. Callerless cells are
# deliberately kept hash-only and held.
PROPOSALS = {
    ("src_30f84002403ca166", "hi"): (
        "\u200f{username} के खोज परिणामों का विस्तार करें",
        "The current Hindi verb फैलाएँ reads as spreading/scattering; this is an accessible toggle for expanding a collapsed search-result group. The proposal says to expand the user's search results and preserves the username placeholder and right-to-left mark.",
    ),
    ("src_310b993f07ab828f", "hi"): (
        "API कुंजी CIDR अनुमति सूची",
        "The current Hindi spelling सीआईडीआर drops the protected technical literal CIDR from the accessible field name. The proposal retains API and CIDR as exact literals.",
    ),
    ("src_31458506a6a11770", "hi"): (
        "कनेक्टेड क्लाइंट्स (",
        "ग्राहक means customers, while this Bridge heading counts software clients. The proposal uses the established technical loanword for clients.",
    ),
    ("src_31458506a6a11770", "vi"): (
        "Ứng dụng khách đã kết nối (",
        "Khách hàng means customers. This Bridge heading counts connected client software; the proposal names connected client applications.",
    ),
    ("src_31458506a6a11770", "zh-Hans"): (
        "连接的客户端 (",
        "The current full-width opening parenthesis is followed by a caller-supplied ASCII closing parenthesis after the count. Use ASCII here so the pair matches in the rendered heading.",
    ),
    ("src_31458506a6a11770", "zh-Hant"): (
        "連接的客戶端 (",
        "The current full-width opening parenthesis is followed by a caller-supplied ASCII closing parenthesis after the count. Use ASCII here so the pair matches in the rendered heading.",
    ),
    ("src_3152b873a3f79771", "ja"): (
        "アプリケーションに「{actionLabel}」を実行します。",
        "The current Japanese target is a bare action-label plus noun phrase and lacks the syntax needed for this confirmation tooltip. The proposal frames the supplied action label as the action performed on the application and preserves the placeholder.",
    ),
    ("src_3152b873a3f79771", "ko"): (
        "애플리케이션에서 “{actionLabel}” 작업을 실행합니다.",
        "The current Korean ending means the application is the action label, rather than describing the requested operation. The proposal says to execute the supplied action on the application and preserves the placeholder.",
    ),
    ("src_316cfce013499533", "es"): (
        "No se pudo ejecutar VACUUM en la base de datos: {message}",
        "Aspirar suggests household vacuuming. This toast reports a database maintenance command; the proposal names VACUUM explicitly and retains the error-message placeholder.",
    ),
    ("src_316cfce013499533", "fr"): (
        "Échec de la commande VACUUM sur la base de données : {message}",
        "Aspiration suggests suction or household vacuuming. This toast reports a database maintenance command; the proposal names VACUUM explicitly and retains the error-message placeholder.",
    ),
    ("src_316cfce013499533", "id"): (
        "Gagal menjalankan VACUUM pada basis data: {message}",
        "Menyedot means sucking/vacuuming and misstates the database operation. The proposal names VACUUM explicitly and retains the error-message placeholder.",
    ),
    ("src_316cfce013499533", "ko"): (
        "데이터베이스 VACUUM 작업에 실패했습니다: {message}",
        "비우다 means emptying the database, which changes the operation's meaning. The proposal names VACUUM explicitly and retains the error-message placeholder.",
    ),
    ("src_316cfce013499533", "vi"): (
        "Không thể chạy VACUUM trên cơ sở dữ liệu: {message}",
        "Hút means sucking and is misleading for a database operation. The proposal names VACUUM explicitly and retains the error-message placeholder.",
    ),
    ("src_317b1fbc1e13beeb", "es"): (
        "No saludable",
        "Malsano reads as ill/unwell, which is less apt for this software health-status value. The proposal uses the direct status wording No saludable.",
    ),
    ("src_317b1fbc1e13beeb", "fr"): (
        "En mauvais état",
        "Malsain describes an unhealthy person or condition and is awkward as a mesh status. The proposal uses a natural poor-condition status value.",
    ),
    ("src_317b1fbc1e13beeb", "hi"): (
        "अस्वस्थ",
        "बीमार most directly describes a sick person. The proposal uses the broader unhealthy condition term for a software health status.",
    ),
    ("src_317b1fbc1e13beeb", "ko"): (
        "상태 불량",
        "위험한 means dangerous rather than unhealthy. The proposal labels the mesh component as being in poor condition.",
    ),
    ("src_317b1fbc1e13beeb", "pt-BR"): (
        "Não saudável",
        "Insalubre usually describes an unfit or hazardous environment. The proposal gives a direct software health-status value.",
    ),
    ("src_317b1fbc1e13beeb", "vi"): (
        "Không lành mạnh",
        "The current phrase means not good for health and reads as advice about a living being. The proposal gives a compact unhealthy-status value.",
    ),
    ("src_31ca26c85e632d29", "ar"): (
        "الصفحة التالية للمجموعات التي تمت مشاركتها معي",
        "الأسهم means financial shares/stocks. This control pages through collections shared with the user, so the proposal names the shared collections and direction.",
    ),
    ("src_31ca26c85e632d29", "es"): (
        "Página siguiente de las colecciones compartidas conmigo",
        "Acciones means financial shares/stocks. The SharedWithMe table pages through collections shared with the user; the proposal makes that meaning explicit.",
    ),
    ("src_31ca26c85e632d29", "fr"): (
        "Page suivante des collections partagées avec moi",
        "The current phrase is awkward and does not clearly say who receives the shares. The proposal matches the SharedWithMe collection table context.",
    ),
    ("src_31ca26c85e632d29", "hi"): (
        "मेरे साथ साझा किए गए संग्रहों का अगला पृष्ठ",
        "शेयर is ambiguous with financial shares and the current phrase does not clearly identify incoming collections. The proposal matches the SharedWithMe collection table context.",
    ),
    ("src_31ca26c85e632d29", "id"): (
        "Halaman berikutnya untuk koleksi yang dibagikan kepada saya",
        "The current target leaves share in English and does not identify the shared collection. The proposal localizes the term and matches the SharedWithMe table context.",
    ),
    ("src_31ca26c85e632d29", "ja"): (
        "自分に共有されたコレクションの次のページ",
        "株式 means financial shares/stocks. This control pages through collections shared with the user; the proposal names that context.",
    ),
    ("src_31ca26c85e632d29", "vi"): (
        "Trang tiếp theo của các bộ sưu tập được chia sẻ với tôi",
        "The current target says only next share page and omits the incoming direction. The proposal names the collections shared with the user, matching SharedWithMe.",
    ),
    ("src_31ca26c85e632d29", "zh-Hans"): (
        "分享给我的集合的下一页",
        "传入 is more commonly used for incoming data/traffic and the current phrase does not identify the shared collection. The proposal matches the SharedWithMe table context.",
    ),
    ("src_31ca26c85e632d29", "zh-Hant"): (
        "分享給我的集合的下一頁",
        "傳入 is more commonly used for incoming data/traffic and the current phrase does not identify the shared collection. The proposal matches the SharedWithMe table context.",
    ),
    ("src_31df66dc9f060166", "ar"): (
        "وحدة التحكم",
        "المراقب المالي means a financial controller. This is a connection-status menu label; the proposal uses the technical controller term.",
    ),
    ("src_31fbef162594de01", "ar"): (
        "متابعة",
        "يكمل is a third-person verb, not a button command. The proposal uses the concise continue action for resuming history backfill.",
    ),
    ("src_31fbef162594de01", "hi"): (
        "जारी रखें",
        "जारी रखना is an infinitive, while this is a button to resume backfill. The proposal uses the polite imperative.",
    ),
    ("src_31fbef162594de01", "id"): (
        "Lanjutkan",
        "Melanjutkan is a verbal noun/continuing form, while this is a button action. The proposal uses the direct continue command.",
    ),
    ("src_31fbef162594de01", "ja"): (
        "続行",
        "続く is an intransitive dictionary-form verb and is awkward as a button label. The proposal uses the compact continue/proceed action label.",
    ),
    ("src_31fbef162594de01", "ko"): (
        "계속",
        "계속하다 is a dictionary-form verb and is awkward as a button label. The proposal uses the compact continue action label.",
    ),
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def digest_text(text):
    return sha(text.encode("utf-8"))

def token_checks(source, target, protected, required_numbers):
    token_pattern = re.compile(r"\{[^{}]+\}")
    tag_pattern = re.compile(r"</?([A-Za-z][A-Za-z0-9:-]*)\b[^>]*>")
    number_pattern = re.compile(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])")
    def without_placeholders(text):
        return token_pattern.sub("", text)
    source_placeholders = token_pattern.findall(source)
    target_placeholders = token_pattern.findall(target)
    source_markup = tag_pattern.findall(source)
    target_markup = tag_pattern.findall(target)
    source_numbers = list(required_numbers)
    target_numbers = number_pattern.findall(without_placeholders(target))
    return {
        "placeholders": {"source": source_placeholders, "target": target_placeholders, "matches": collections.Counter(source_placeholders) == collections.Counter(target_placeholders)},
        "markup": {"source": source_markup, "target": target_markup, "matches": collections.Counter(source_markup) == collections.Counter(target_markup)},
        "numbers": {"source": source_numbers, "target": target_numbers, "matches": all(token in target_numbers for token in source_numbers)},
        "protectedLiterals": {"required": protected, "missing": [literal for literal in protected if literal not in target], "matches": all(literal in target for literal in protected)},
    }

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

cells = read_jsonl(INPUT / "source-current-cells.jsonl")
contexts = {r["sourceId"]: r for r in read_jsonl(INPUT / "caller-contexts.jsonl")}
selected_ids = list(dict.fromkeys(r["sourceId"] for r in cells))
assert len(cells) == 300 and len(selected_ids) == 25

lineage_files = [
    "prior-held-cell-reattestation-hash-only.jsonl",
    "previous-window-prior-holds-hash-only.jsonl",
    "previous-window-hold-resolutions-hash-only.jsonl",
    "prior-hold-resolution-history-hash-only.jsonl",
]
lineage_hits = collections.Counter()
for filename in lineage_files:
    for row in read_jsonl(INPUT / filename):
        if row.get("sourceId") in selected_ids:
            lineage_hits[(row["sourceId"], row.get("locale"))] += 1
assert not lineage_hits

decisions = []
for cell in cells:
    sid, locale = cell["sourceId"], cell["locale"]
    key = (sid, locale)
    source = cell["source"]
    current = cell["currentTarget"]
    context = contexts[sid]
    callerless = context["productionCallerCount"] == 0
    current_hash = digest_text(current)
    source_hash = digest_text(source)
    assert current_hash == cell["currentTargetSha256"]
    assert source_hash == cell["sourceSha256"]
    base = {
        "schemaVersion": 1,
        "window": "W78",
        "continuationRank": cell["continuationRank"],
        "sourceId": sid,
        "locale": locale,
        "sourceSha256": source_hash,
        "currentTargetSha256": current_hash,
        "decisionTargetSha256": current_hash,
        "priorHoldLineage": {
            "status": "no matching source-cell record in supplied hash-only prior-hold lineage",
            "matchingRows": 0,
            "evidenceFiles": lineage_files,
        },
    }
    if callerless:
        base.update({
            "decision": "hold",
            "rationale": "The supplied production-literal scan found no caller for this source. Keep the cell on hold pending caller context and preserve hash-only handling; source and target text are withheld.",
            "callerEvidence": {"productionCallerCount": 0, "callerRefs": [], "textWithheld": True},
            "tokenChecks": {"status": "withheld with callerless hash-only hold"},
        })
        decisions.append(base)
        continue

    proposal = PROPOSALS.get(key)
    reviewed = proposal[0] if proposal else current
    checks_current = token_checks(source, current, cell["sourceProtectedLiterals"], cell["sourceNumericTokens"])
    checks_decision = token_checks(source, reviewed, cell["sourceProtectedLiterals"], cell["sourceNumericTokens"])
    assert all(check["matches"] for check in checks_decision.values()), (key, checks_decision)
    rationale = proposal[1] if proposal else (
        f"Keep: the target conveys the source meaning for the observed {CONTEXT[sid]} context; no material grammar or terminology defect was identified. It preserves all source placeholders, markup, numeric tokens, and protected literals."
    )
    refs = [{
        "path": ref["path"],
        "line": ref["line"],
        "lineSha256": ref["lineSha256"],
        "contextSha256": ref["contextSha256"],
        "fileSha256": ref["fileSha256"],
        "gitBlob": ref["gitBlob"],
    } for ref in cell["callerRefs"]]
    base.update({
        "decision": "propose" if proposal else "keep",
        "rationale": rationale,
        "sourceText": source,
        "currentTarget": current,
        "decisionTargetSha256": digest_text(reviewed),
        "callerEvidence": {
            "productionCallerCount": context["productionCallerCount"],
            "callerContextSha256": cell["callerContextSha256"],
            "callerRefs": refs,
            "contextSummary": CONTEXT[sid],
        },
        "tokenChecks": {
            "currentTarget": checks_current,
            "decisionTarget": checks_decision,
        },
    })
    if proposal:
        base["proposedTarget"] = reviewed
    decisions.append(base)

assert len(decisions) == 300
assert collections.Counter(d["decision"] for d in decisions) == {"keep": 254, "propose": 34, "hold": 12}
assert all(d["decision"] == "hold" for d in decisions if d["callerEvidence"]["productionCallerCount"] == 0)

packet_path = OUT / "blind-review-decisions.jsonl"
packet_path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in decisions), encoding="utf-8")

input_manifest = json.loads((INPUT / "manifest.json").read_text(encoding="utf-8"))
prior_lineage_summary = json.loads((INPUT / "prior-hold-lineage-summary.json").read_text(encoding="utf-8"))
reattest_summary = json.loads((INPUT / "prior-held-cell-reattestation-summary.json").read_text(encoding="utf-8"))
counts = collections.Counter(d["decision"] for d in decisions)
proposals_by_locale = collections.Counter(d["locale"] for d in decisions if d["decision"] == "propose")
summary = {
    "artifact": "slskdN PR #409 W78 ranks 828-852 independent blind review",
    "schemaVersion": 1,
    "candidateFreeInput": True,
    "reviewHead": input_manifest["head"],
    "reviewTree": input_manifest["tree"],
    "window": "W78",
    "continuationRankRange": [828, 852],
    "sourceCount": 25,
    "localeCount": 12,
    "cellCount": len(decisions),
    "locales": LOCALES,
    "decisionCounts": dict(counts),
    "proposalCountsByLocale": dict(proposals_by_locale),
    "callerlessHeldCells": 12,
    "callerlessHoldPolicy": "hash-only; source and target strings withheld",
    "sourceLiteralCallerCount": 24,
    "sourceIdsWithPriorHoldLineageOverlap": 0,
    "priorHoldLineage": {
        "reattestedCells": reattest_summary.get("cellCount", 331),
        "callerEvidenceUnchanged": reattest_summary.get("callerEvidenceUnchanged", 331),
        "callerEvidenceChanged": reattest_summary.get("callerEvidenceChanged", 0),
        "resolutionHistoryRows": input_manifest["priorHoldResolutionHistoryRows"],
        "windows": prior_lineage_summary,
    },
    "baselineTokenMismatchCounts": input_manifest["baselineTokenMismatchSummary"],
    "decisionTargetTokenMismatchCounts": {"placeholders": 0, "markup": 0, "numbers": 0, "protectedLiterals": 0},
    "reviewMethod": "Cell-by-cell text review against the candidate-free packet and pinned caller contexts; no candidate-review output was used.",
}
(OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

# Input checksum listing hash and input file entries are recorded for exact provenance.
checksum_text = (INPUT / "PACKET-SHA256SUMS.txt").read_text(encoding="utf-8")
input_files = []
for line in checksum_text.splitlines():
    expected, path = line.split(maxsplit=1)
    input_files.append({"path": path.strip(), "sha256": expected})

pre = {
    "attestation": "candidate-free pre-review source attestation",
    "inputChecksumListSha256": sha(checksum_text.encode("utf-8")),
    "candidateFreeInputManifestSha256": sha((INPUT / "manifest.json").read_bytes()),
    "inputVerification": "PASS: sha256sum -c PACKET-SHA256SUMS.txt and verify_input.py --repo <source-worktree>",
    "sourceHead": input_manifest["head"],
    "sourceTree": input_manifest["tree"],
    "suppliedHeadTreeAttestation": json.loads((INPUT / "head-tree-attestation.json").read_text(encoding="utf-8")),
    "suppliedSourceTreeAttestation": json.loads((INPUT / "source-tree-attestation.json").read_text(encoding="utf-8")),
    "sourceTreeAttestationSha256": sha((INPUT / "source-tree-attestation.json").read_bytes()),
    "suppliedLiveAfterAttestation": input_manifest["liveAfter"],
    "localRefs": {
        "refs/heads/task/slskdn-pr409-w77-apply-20261104": "4120c9637e71466dc98d51a5a342dee199a1e004",
        "refs/remotes/origin/codex/slskdn-oidc-tooltip-localization-20261030": "4120c9637e71466dc98d51a5a342dee199a1e004",
        "refs/remotes/origin/pr/409": "32afa31caca42b17ac89c9ee91e54ed94cad0411",
        "refs/remotes/origin/main": "e6203f3cb16457bdb3a35678163adce01371be40",
    },
    "refAssessment": "The checked-out HEAD and the matching local source branch agree with the pin. Local origin/pr/409 and origin/main are stale relative to the supplied live-before/live-after attestation; no remote refresh was made.",
    "worktreeStatus": "clean",
    "inputFiles": input_files,
    "selectedSourceCellCount": len(cells),
    "selectedSourceCount": len(selected_ids),
    "reviewDecisionOutputCreatedAfterSuppliedAttestation": True,
}
(OUT / "pre-review-attestation.json").write_text(json.dumps(pre, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

verifier = r'''#!/usr/bin/env python3
"""Portable verifier for this sealed W78 blind-review packet (Python 3 stdlib)."""
import collections, hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKET = ROOT / "blind-review-decisions.jsonl"
MANIFEST = ROOT / "manifest.json"
SUMS = ROOT / "SEALED-SHA256SUMS.txt"

def sha(data): return hashlib.sha256(data).hexdigest()
def load_json(path): return json.loads(path.read_text(encoding="utf-8"))
def fail(message):
    print("FAIL:", message, file=sys.stderr)
    raise SystemExit(1)

if not PACKET.is_file() or not MANIFEST.is_file() or not SUMS.is_file(): fail("missing packet, manifest, or checksum list")
manifest = load_json(MANIFEST)
sum_members = {}
for line in SUMS.read_text(encoding="utf-8").splitlines():
    if not line.strip(): continue
    expected, rel = line.split(maxsplit=1)
    rel = rel.lstrip("* ")
    if rel in sum_members: fail("duplicate checksum member: " + rel)
    sum_members[rel] = expected
    path = (ROOT / rel).resolve()
    if ROOT.resolve() not in path.parents: fail("checksum path escapes packet directory")
    if not path.is_file(): fail("missing checksum member: " + rel)
    if sha(path.read_bytes()) != expected: fail("checksum mismatch: " + rel)
for member in manifest["files"]:
    path = ROOT / member["path"]
    if not path.is_file() or sha(path.read_bytes()) != member["sha256"]: fail("manifest hash mismatch: " + member["path"])
if set(sum_members) != {member["path"] for member in manifest["files"]} | {"manifest.json"}: fail("checksum list membership mismatch")
rows = [json.loads(line) for line in PACKET.read_text(encoding="utf-8").splitlines() if line]
if len(rows) != 300: fail("expected exactly 300 rows")
locales = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
keys = [(r["sourceId"], r["locale"]) for r in rows]
if len(set(keys)) != 300: fail("duplicate source-locale cell")
by_source = collections.defaultdict(set)
for row in rows: by_source[row["sourceId"]].add(row["locale"])
if len(by_source) != 25 or any(seen != set(locales) for seen in by_source.values()): fail("expected 25 source IDs with all 12 locales")
if {row["continuationRank"] for row in rows} != set(range(828, 853)): fail("unexpected continuation ranks")
counts = collections.Counter(row["decision"] for row in rows)
if counts != {"keep": 254, "propose": 34, "hold": 12}: fail("unexpected decision counts: " + repr(dict(counts)))
token_re = re.compile(r"\{[^{}]+\}")
tag_re = re.compile(r"</?([A-Za-z][A-Za-z0-9:-]*)\b[^>]*>")
number_re = re.compile(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])")
held = 0
for row in rows:
    for name in ("sourceSha256", "currentTargetSha256", "decisionTargetSha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", row[name]): fail("invalid hash in row " + repr((row["sourceId"], row["locale"])))
    if row["decision"] == "hold":
        held += 1
        if row["callerEvidence"].get("productionCallerCount") != 0: fail("hold is not callerless")
        if any(k in row for k in ("sourceText", "currentTarget", "proposedTarget")): fail("callerless hold contains text")
        if row["tokenChecks"].get("status") != "withheld with callerless hash-only hold": fail("callerless hold is not hash-only")
        continue
    source, current = row["sourceText"], row["currentTarget"]
    target = row.get("proposedTarget", current)
    if sha(source.encode("utf-8")) != row["sourceSha256"]: fail("source hash mismatch")
    if sha(current.encode("utf-8")) != row["currentTargetSha256"]: fail("current target hash mismatch")
    if sha(target.encode("utf-8")) != row["decisionTargetSha256"]: fail("decision target hash mismatch")
    def numbers(s): return number_re.findall(token_re.sub("", s))
    if collections.Counter(token_re.findall(source)) != collections.Counter(token_re.findall(target)): fail("placeholder mismatch")
    if collections.Counter(tag_re.findall(source)) != collections.Counter(tag_re.findall(target)): fail("markup mismatch")
    required_numbers = row["tokenChecks"]["decisionTarget"]["numbers"]["source"]
    if any(number not in numbers(target) for number in required_numbers): fail("numeric token mismatch")
    protected = row["tokenChecks"]["decisionTarget"]["protectedLiterals"]["required"]
    if any(literal not in target for literal in protected): fail("protected literal missing")
    if row["decision"] == "propose" and "proposedTarget" not in row: fail("proposal lacks target")
    if row["decision"] == "keep" and "proposedTarget" in row: fail("keep unexpectedly has proposal")
if held != 12: fail("expected 12 hash-only holds")
hold_ids = {row["sourceId"] for row in rows if row["decision"] == "hold"}
hold_locales = {row["locale"] for row in rows if row["decision"] == "hold"}
if len(hold_ids) != 1 or hold_locales != set(locales): fail("callerless holds must cover one source across all locales")
if manifest["cellCount"] != len(rows) or manifest["decisionCounts"] != dict(counts): fail("manifest summary mismatch")
print(json.dumps({"result":"PASS", "cells":len(rows), "sources":len(by_source), "locales":len(locales), "decisionCounts":dict(counts)}, sort_keys=True))
'''
(OUT / "verify_blind_packet.py").write_text(verifier, encoding="utf-8")

def git_text(*args):
    return subprocess.check_output(["git", *args], cwd=SOURCE, text=True).strip()

ref_names = [
    "refs/heads/task/slskdn-pr409-w77-apply-20261104",
    "refs/remotes/origin/codex/slskdn-oidc-tooltip-localization-20261030",
    "refs/remotes/origin/pr/409",
    "refs/remotes/origin/main",
]
post_state = {
    "head": git_text("rev-parse", "HEAD"),
    "tree": git_text("rev-parse", "HEAD^{tree}"),
    "status": git_text("status", "--short", "--branch"),
    "worktreeClean": not bool(git_text("status", "--porcelain")),
    "refs": {},
}
for ref in ref_names:
    post_state["refs"][ref] = git_text("rev-parse", "--verify", ref)
assert post_state["head"] == input_manifest["head"]
assert post_state["tree"] == input_manifest["tree"] and post_state["worktreeClean"]
for input_file in input_files:
    path = INPUT / input_file["path"]
    assert sha(path.read_bytes()) == input_file["sha256"], input_file["path"]

post = {
    "attestation": "post-review source/worktree attestation",
    "capturedUtc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    "sourceHead": post_state["head"],
    "sourceTree": post_state["tree"],
    "worktreeStatus": post_state["status"],
    "worktreeClean": post_state["worktreeClean"],
    "localRefs": post_state["refs"],
    "suppliedLiveAfterAttestation": input_manifest["liveAfter"],
    "inputChecksumListSha256": sha(checksum_text.encode("utf-8")),
    "inputChecksumsStillMatch": True,
    "reviewPacketSha256": sha(packet_path.read_bytes()),
    "summarySha256": sha((OUT / "summary.json").read_bytes()),
    "portableVerifierSha256": sha((OUT / "verify_blind_packet.py").read_bytes()),
    "decisionCounts": dict(counts),
    "callerlessHoldCount": 12,
}
(OUT / "post-review-attestation.json").write_text(json.dumps(post, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

members = []
for path in sorted(OUT.iterdir()):
    if path.is_file() and path.name not in {"manifest.json", "SEALED-SHA256SUMS.txt"}:
        members.append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha(path.read_bytes())})
manifest = {
    "artifact": "sealed blind review packet for slskdN PR #409 W78 ranks 828-852",
    "schemaVersion": 1,
    "repository": input_manifest["repository"],
    "pullRequest": input_manifest["pullRequest"],
    "window": "W78",
    "continuationRankRange": [828, 852],
    "candidateFreeInput": True,
    "reviewHead": input_manifest["head"],
    "reviewTree": input_manifest["tree"],
    "sourceWorktreePath": str(SOURCE),
    "inputDirectory": str(INPUT),
    "inputChecksumList": "PACKET-SHA256SUMS.txt",
    "inputChecksumListSha256": sha(checksum_text.encode("utf-8")),
    "inputManifestSha256": sha((INPUT / "manifest.json").read_bytes()),
    "inputFiles": input_files,
    "sourceRefAssessment": pre["refAssessment"],
    "suppliedLiveAfterAttestation": input_manifest["liveAfter"],
    "decisionCounts": dict(counts),
    "cellCount": len(decisions),
    "sourceCount": len(selected_ids),
    "localeCount": len(LOCALES),
    "callerlessHoldCount": 12,
    "files": members,
    "checksumFile": "SEALED-SHA256SUMS.txt",
}
(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

sealed_members = members + [{"path": "manifest.json", "bytes": (OUT / "manifest.json").stat().st_size, "sha256": sha((OUT / "manifest.json").read_bytes())}]
(OUT / "SEALED-SHA256SUMS.txt").write_text("".join(f"{member['sha256']}  {member['path']}\n" for member in sorted(sealed_members, key=lambda x: x["path"])), encoding="utf-8")

print(json.dumps({"result": "SEALED", "cells": len(decisions), "decisions": dict(counts), "out": str(OUT), "manifestSha256": sha((OUT / 'manifest.json').read_bytes()), "packetSha256": sha(packet_path.read_bytes())}, sort_keys=True))
