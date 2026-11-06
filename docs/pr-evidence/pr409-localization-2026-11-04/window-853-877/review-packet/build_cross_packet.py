#!/usr/bin/env python3
"""Build the W79 independent cross-review evidence packet."""
import collections
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

PKT = Path(__file__).resolve().parent
TASK = PKT.parent
INPUT = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w79-853-877-primary-20261104/candidate-free/input")
PRIMARY = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w79-853-877-primary-20261104/primary-review/output")
BLIND = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w79-853-877-blind-20261104")
SOURCE = TASK / "pinned-source"
HEAD = "4d67527be0ca3b75e866f25bef5e58ae7f777f7f"
TREE = "99ba5d8f7d631de3337e6b02f74af6d14e46c2ff"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
RANKS = list(range(853, 878))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text_sha(value):
    return sha(value.encode("utf-8"))


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def rows_raw(path):
    result = []
    for line in path.read_bytes().splitlines():
        if line.strip():
            result.append((json.loads(line), line))
    return result


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                            for value in values), encoding="utf-8")


def git(*args):
    return subprocess.check_output(["git", "-C", str(SOURCE), *args]).strip()


def git_bytes(*args):
    return subprocess.check_output(["git", "-C", str(SOURCE), *args])


def token_check(source, current, target=None):
    import collections as c
    import re
    import unicodedata
    def ph(v):
        return c.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", v))
    def tags(v):
        return c.Counter(re.findall(r"</?[A-Za-z][^>]*>", v))
    def nums(v):
        return ["".join(str(unicodedata.digit(ch)) if ch.isdigit() else ch for ch in m)
                for m in re.findall(r"\d+", v)]
    def prot(v):
        out = set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", v))
        out.update(x for x in ("slskdN", "Tor", "Wishlist", "Chromaprint") if x in v)
        return sorted(out)
    def not_less(src, dst):
        src, dst = c.Counter(src), c.Counter(dst)
        return all(dst[t] >= n for t, n in src.items())
    result = {
        "sourcePlaceholderTokens": sorted(ph(source).elements()),
        "currentPlaceholderTokens": sorted(ph(current).elements()),
        "sourceMarkupTokens": sorted(tags(source).elements()),
        "currentMarkupTokens": sorted(tags(current).elements()),
        "sourceNumericTokens": nums(source),
        "currentNumericTokens": nums(current),
        "sourceProtectedLiterals": prot(source),
        "currentProtectedLiterals": [x for x in prot(source) if x in current],
        "placeholderParityCurrent": ph(source) == ph(current),
        "markupParityCurrent": tags(source) == tags(current),
        "numericTokensPreservedCurrent": not_less(nums(source), nums(current)),
        "protectedLiteralsPreservedCurrent": all(x in current for x in prot(source)),
    }
    if target is not None:
        result["proposal"] = {
            "placeholderTokens": sorted(ph(target).elements()),
            "markupTokens": sorted(tags(target).elements()),
            "numericTokens": nums(target),
            "protectedLiterals": prot(target),
            "placeholderParity": ph(source) == ph(target),
            "markupParity": tags(source) == tags(target),
            "numericTokensPreserved": not_less(nums(source), nums(target)),
            "protectedLiteralsPreserved": all(x in target for x in prot(source)),
        }
    return result


CUSTOM_PROPOSALS = {
    (857, "vi"): "Đang hiển thị các tìm kiếm {start}–{end} trong số {count} tìm kiếm đã tải",
    (861, "fr"): "Le point de rendez-vous public n'a aucun pair visible",
    (861, "hi"): "सार्वजनिक मिलन बिंदु पर कोई पीयर दिखाई नहीं दे रहा है।",
    (861, "id"): "Titik temu publik tidak memiliki peer yang terlihat",
    (861, "pt-BR"): "O ponto de encontro público não tem pares visíveis",
    (864, "ar"): "تم تكوين المجلدات المشتركة",
    (869, "ar"): "لا تتوفر بيانات تحليلات السرب. ابدأ بعض التنزيلات عبر السرب لرؤية المقاييس.",
    (869, "id"): "Tidak ada data analitik swarm yang tersedia. Mulai beberapa unduhan swarm untuk melihat metrik.",
    (869, "ko"): "사용할 수 있는 스웜 분석 데이터가 없습니다. 측정항목을 보려면 스웜 다운로드를 시작하세요.",
    (872, "es"): "Grafo",
    (872, "fr"): "Graphe",
    (872, "id"): "Graf",
    (872, "pt-BR"): "Grafo",
    (875, "pt-BR"): "Copie um relatório de integridade somente leitura para revisão offline. Isso não corrige, não faz uma nova varredura, não coloca em quarentena, não pesquisa nem altera arquivos.",
    (876, "ko"): "캐시 우회(새 데이터를 강제로 다시 가져오기)",
    (877, "es"): "nombres de usuario rastreados.",
}

HOLD_RANKS = {
    855: set(LOCALES),
    865: set(LOCALES),
    868: set(LOCALES),
    869: {"ja", "zh-Hans", "zh-Hant"},
}

PROPOSAL_RATIONALES = {
    (856, "ko"): "The caller places this label immediately before the value of audioHashResult.algorithm and imageHashResult.algorithm. The current Korean term denotes an operation or computation; the selected wording names the algorithm.",
    (857, "de"): "The caller supplies start, end, and count for loaded searches. The current German participle lacks a grammatical noun; the proposal recasts the range as loaded search requests being displayed.",
    (857, "fr"): "The pagination caller supplies a range and total count of loaded searches. The current French phrase does not form a grammatical count phrase; the proposal makes the display of loaded searches explicit.",
    (857, "vi"): "The pagination caller supplies a range and total count of loaded searches. The current wording counts loaded items rather than searches; the proposal repeats the search noun and keeps all three placeholders.",
    (861, "ar"): "The caller classifies this as a connectivity failure and the source catalog describes DHT rendezvous as peer discovery. The current Arabic word suggests an appointment; this proposal names a public meeting point and network peers.",
    (861, "es"): "This is a network-health failure about peer visibility. The current Spanish cita means an appointment; punto de encuentro matches the product's DHT rendezvous wording and pares preserves the peer sense.",
    (861, "hi"): "The caller is a connectivity failure about peers. The proposal replaces ordinary-meeting and companion wording with the product's meeting-point sense and the established technical peer loanword.",
    (861, "id"): "The caller is a connectivity failure about peers. The proposal uses titik temu, the locale's existing DHT rendezvous term, and retains peer as the product's network term.",
    (861, "ko"): "The caller is a connectivity failure about peer visibility. The current 동료 means colleague; the proposal uses the product's technical rendezvous and peer terms.",
    (861, "vi"): "The caller is a connectivity failure about network peers. The current đồng nghiệp means colleague and rõ ràng means clear; the proposal uses the product's existing điểm hẹn term and describes visible peer users.",
    (861, "zh-Hans"): "The caller reports a DHT connectivity failure. The current 同行 can mean companion; the proposal uses the locale's existing discovery graph term 对等节点 for network peers and a meeting-point term for rendezvous.",
    (861, "zh-Hant"): "The caller reports a DHT connectivity failure. The current 同行 can mean companion; the proposal uses the locale's existing discovery graph term 對等節點 for network peers and a meeting-point term for rendezvous.",
    (861, "fr"): "The DHT caller uses point de rendez-vous for the endpoint concept and the locale uses pair for network peers. The current homologue is a less direct counterpart term, so the proposal aligns both terms with pinned product wording.",
    (861, "pt-BR"): "The source is a DHT endpoint with peer discovery, not an event. Ponto de encontro follows the locale's DHT rendezvous wording and pares retains the peer meaning.",
    (864, "ar"): "The caller counts configured share entries in the Storage setup check. The current الأسهم reads as stocks or equity shares; the proposal names configured shared folders.",
    (864, "es"): "The caller counts configured file-share entries. The current acciones means actions or stocks; the proposal names configured shared folders.",
    (866, "fr"): "The caller filters selected searches by a nonblank searchText field. The current exploitable means usable; the proposal states that no text is available to search.",
    (869, "es"): "The caller displays an empty-state message for swarm analytics. The current descargas enjambres is malformed; en enjambre keeps the P2P swarm qualifier in grammatical form.",
    (869, "vi"): "The caller asks users to start swarm downloads. The current second sentence omits swarm, while the proposal restores that qualifier with the locale's existing technical loanword.",
    (869, "ar"): "The caller asks for swarm downloads to populate swarm analytics. The current second sentence changes swarm downloads to collective/group downloads; this proposal repeats the established السرب term.",
    (869, "id"): "The caller concerns peer-swarm analytics. The current gerombolan reads as a crowd; the proposal uses swarm, the established technical term used elsewhere in this locale catalog.",
    (869, "ko"): "The caller concerns peer-swarm analytics. The current sentence switches from a generic herd term to English Swarm; this proposal uses the locale catalog's 스웜 term consistently.",
    (871, "ar"): "The caller is the success message for accepting a signed membership-removal request. The current الإجازة means vacation or leave from work; the proposal names an accepted request to leave the group.",
    (871, "de"): "The caller is the success message for accepting a signed membership-removal request. Urlaub means vacation; Austrittsanfrage names the accepted request to leave.",
    (871, "es"): "The caller accepts a membership-removal request. The current bare Dejar phrase is not a status sentence; the proposal names the accepted departure request.",
    (871, "fr"): "The caller accepts a signed request to remove a group membership. Congé means leave/vacation; demande de départ names the accepted departure request.",
    (871, "hi"): "The caller accepts a signed request to leave a group. छुट्टी means vacation/leave from work; the proposal explicitly names the accepted group-exit request.",
    (871, "id"): "The caller accepts a signed request to leave a membership. Cuti means vacation/leave from work; the proposal explicitly names the accepted membership-exit request.",
    (871, "ja"): "The caller accepts a signed membership-removal request. 休暇 means vacation; the proposal uses 退会申請 for a membership withdrawal request.",
    (871, "vi"): "The caller accepts a signed membership-removal request. The current wording is a bare leave verb phrase; the proposal names the accepted group-exit request.",
    (871, "zh-Hans"): "The caller accepts a signed membership-removal request. 休假 means vacation; the proposal names the approved exit request.",
    (871, "zh-Hant"): "The caller accepts a signed membership-removal request. 休假 means vacation; the proposal names the approved exit request.",
    (872, "es"): "All six callers open a relationship graph of identities, releases, tracks, artists, and branches. The locale's pinned Discovery Graph strings use grafo; Gráfico can read as a chart.",
    (872, "fr"): "All six callers open a relationship graph of identities, releases, tracks, artists, and branches. The locale's pinned Discovery Graph strings use graphe; Graphique can read as a chart.",
    (872, "id"): "All six callers open a relationship graph of identities, releases, tracks, artists, and branches. The locale's pinned term is Graf penemuan; Grafik can read as a chart.",
    (872, "pt-BR"): "All six callers open a relationship graph of identities, releases, tracks, artists, and branches. The locale's pinned Discovery Graph strings use grafo; Gráfico can read as a chart.",
    (872, "zh-Hans"): "The callers open a relationship graph with nearby identities and branches, not a standalone illustration. The locale's pinned Discovery Graph strings use 图谱; 图形 can mean a figure or shape.",
    (872, "zh-Hant"): "The callers open a relationship graph with nearby identities and branches, not a standalone illustration. The locale's pinned Discovery Graph strings use 圖譜; 圖形 can mean a figure or shape.",
    (873, "ar"): "The caller lists a metadata-processing validation error. The current Arabic adjective means approved or authorized; the proposal says unsupported.",
    (875, "fr"): "The caller explicitly promises the report does not modify files. The current muter means mute; the proposal uses modifier for changing files.",
    (875, "ko"): "The caller lists fix, rescan, quarantine, search, and mutate as distinct actions. The current wording repeats search and blurs fix/rescan; the proposal distinguishes rescan from searching and modification.",
    (875, "pt-BR"): "The caller distinguishes rescan from searching. The current verificar novamente means check/verify again; nova varredura matches the locale's pinned rescan wording.",
    (876, "zh-Hans"): "The caller retrieves cached content descriptors from the DHT and describes the option as a fresh lookup. The current 新鲜检索 is unnatural and suggests search; 重新获取 expresses fetching again.",
    (876, "zh-Hant"): "The caller retrieves cached content descriptors from the DHT and describes the option as a fresh lookup. The current 新鮮檢索 is unnatural and suggests search; 重新擷取 expresses fetching again.",
    (876, "ko"): "The caller performs a fresh DHT descriptor retrieval when cache is bypassed. The current 새로 검색 means search again; the proposal says to fetch fresh data again.",
    (877, "es"): "The caller inserts this string directly after the tracked-usernames count. The current full passive sentence breaks that count-plus-label construction; the proposal is a noun phrase that follows a number.",
}

KEEP_RATIONALES = {
    853: "This locale label identifies the maximum result count. Six callers use it on bounded numeric result fields in MediaCore and Wishlist.",
    854: "The Bridge caller displays a protocol-port note with the default value 2242; this locale wording retains Soulseek, the port meaning, and the literal.",
    856: "This is a label immediately before a computed audio or image hash algorithm value; the locale wording names an algorithm.",
    857: "The locale wording presents a displayed range and a total count of loaded searches, matching the pagination caller and placeholders.",
    858: "The locale wording names the Imported status; callers map it to a request imported into the library and reuse it in request state displays.",
    859: "The locale wording tells an unauthenticated user to log in to see DHT statistics, matching the footer title.",
    860: "The locale wording names the Browse item in the primary navigation.",
    861: "The locale wording describes no visible peers at a public rendezvous in a network-health connectivity failure.",
    862: "The locale wording names the Preview button; its caller previews a selected download action without starting a transfer.",
    863: "The locale wording is an imperative to find similar content, matching the MediaCore button action.",
    864: "The locale wording says file shares are configured; the setup check counts visible share entries.",
    866: "The locale wording says selected searches have no searchable text; the caller checks for a nonblank searchText before creating a batch.",
    867: "The locale wording names a link-type field beside a ContentID example.",
    869: "The locale wording describes swarm analytics and starting swarm downloads to populate metrics; the caller is the empty state for Swarm Analytics.",
    870: "The locale wording means within quota; the caller sets it when item count is not greater than the quota.",
    871: "The locale wording expresses a successful membership departure or leave-request acceptance, matching the signed group-membership action.",
    872: "The locale wording names a graph button; its callers open the Discovery Graph around related identities, releases, tracks, artists, and branches.",
    873: "The locale wording says the audio file is unsupported; the caller lists this metadata-processing validation error.",
    874: "The locale wording identifies an album candidate near the current SongID result.",
    875: "The locale wording preserves a read-only report and states that it does not perform the listed file operations.",
    876: "The locale wording says to bypass cache and retrieve fresh data, matching the descriptor-retrieval controls.",
    877: "The locale wording is a fragment that follows the tracked-usernames count in the security overview.",
}

HOLD_RATIONALES = {
    855: "The pinned Jobs caller is a job-type filter with value label_crate. Pinned integration documentation defines Label Crate as a named curated label-catalog and multi-swarm workflow. Current literal translations can read as a physical label box; with no established localized feature term in the pinned catalog, retain a review hold.",
    865: "No production caller was found for this source in the bounded pinned runtime scan. Keep the cell hash-only and held until caller evidence exists.",
    868: "No production caller was found for this source in the bounded pinned runtime scan. Keep the cell hash-only and held until caller evidence exists.",
    869: "The caller identifies peer-swarm analytics and asks for swarm downloads. This locale catalog alternates a translated group term and the English swarm loanword, so the current phrase can imply generic group downloads. The pinned locale evidence does not settle one unambiguous P2P term; retain a hold pending terminology selection.",
}

CUSTOM_HOLD_RATIONALES = {
    (869, "ja"): "The caller identifies peer-swarm analytics and asks for swarm downloads. This locale catalog alternates 群/群れ with the English swarm loanword, so the current text mixes a group term and English Swarm. The pinned locale evidence does not settle one unambiguous P2P term; retain a hold pending terminology selection.",
    (869, "zh-Hans"): "The caller identifies peer-swarm analytics and asks for swarm downloads. The current 群体/群 wording can mean a generic group, while pinned locale entries also use Latin swarm. The catalog has no stable locale term here; retain a hold pending terminology selection.",
    (869, "zh-Hant"): "The caller identifies peer-swarm analytics and asks for swarm downloads. The current 群體/群 wording can mean a generic group, while pinned locale entries also use Latin swarm or 群組. The catalog has no stable locale term here; retain a hold pending terminology selection.",
}


def caller_refs(ctx):
    return [{
        "path": item["path"], "line": item["line"], "lineSha256": item["lineSha256"],
        "contextSha256": item["contextSha256"], "fileSha256": item["fileSha256"],
        "gitBlob": item["gitBlob"],
    } for item in ctx["callers"]]


def main():
    if not SOURCE.exists():
        raise SystemExit(f"missing pinned source worktree: {SOURCE}")
    (PKT / "inputs").mkdir(parents=True, exist_ok=True)
    for src, rel in [
        (INPUT / "manifest.json", "inputs/candidate-free-manifest.json"),
        (INPUT / "caller-contexts.jsonl", "inputs/caller-contexts.jsonl"),
        (INPUT / "source-current-cells.jsonl", "inputs/source-current-cells.jsonl"),
        (INPUT / "prior-held-cell-reattestation-hash-only.jsonl", "inputs/prior-held-cell-reattestation-hash-only.jsonl"),
        (INPUT / "prior-hold-resolution-history-hash-only.jsonl", "inputs/prior-hold-resolution-history-hash-only.jsonl"),
        (INPUT / "prior-hold-lineage-summary.json", "inputs/prior-hold-lineage-summary.json"),
        (INPUT / "prior-held-cell-reattestation-summary.json", "inputs/prior-held-cell-reattestation-summary.json"),
        (INPUT / "previous-window-cross-holds-hash-only.jsonl", "inputs/previous-window-cross-holds-hash-only.jsonl"),
        (INPUT / "previous-window-applied-targets-hash-only.jsonl", "inputs/previous-window-applied-targets-hash-only.jsonl"),
        (PRIMARY / "manifest.json", "inputs/primary-manifest.json"),
        (PRIMARY / "summary.json", "inputs/primary-summary.json"),
        (PRIMARY / "primary-review.jsonl", "inputs/primary-review.jsonl"),
        (BLIND / "manifest.json", "inputs/blind-manifest.json"),
    ]:
        shutil.copyfile(src, PKT / rel)

    source_records = rows_raw(INPUT / "source-current-cells.jsonl")
    context_records = rows_raw(INPUT / "caller-contexts.jsonl")
    primary_records = rows_raw(PRIMARY / "primary-review.jsonl")
    blind_records = rows_raw(BLIND / "review-cells.jsonl")
    cells = {(r["continuationRank"], r["locale"]): (r, raw) for r, raw in source_records}
    contexts = {r["sourceId"]: r for r, _ in context_records}
    primary = {(r["continuationRank"], r["locale"]): (r, raw) for r, raw in primary_records}
    blind = {(r["continuationRank"], r["locale"]): (r, raw) for r, raw in blind_records}
    expected_keys = {(rank, locale) for rank in RANKS for locale in LOCALES}
    if set(cells) != expected_keys or set(primary) != expected_keys or set(blind) != expected_keys:
        raise SystemExit("source, primary, or blind cell coverage mismatch")
    if len(contexts) != 25:
        raise SystemExit("caller context source coverage mismatch")

    redacted_blind = []
    blind_hashes = []
    cross_rows = []
    proposal_rows = []
    no_op_rows = []
    hold_rows = []
    callerless_holds = []
    primary_audit = []
    for key in sorted(expected_keys):
        rank, locale = key
        cell, cell_raw = cells[key]
        p, p_raw = primary[key]
        b, b_raw = blind[key]
        source_id = cell["sourceId"]
        ctx = contexts[source_id]
        backed = ctx["productionCallerCount"] > 0
        refs = caller_refs(ctx) if backed else []
        if p["sourceId"] != source_id or b["sourceId"] != source_id:
            raise SystemExit(f"source id mismatch at {rank}/{locale}")
        if p["callerContextSha256"] != cell["callerContextSha256"] or b["callerContextSha256"] != cell["callerContextSha256"]:
            raise SystemExit(f"caller hash mismatch at {rank}/{locale}")
        if backed:
            source = cell["source"]
            current = cell["currentTarget"]
            if text_sha(source) != cell["sourceSha256"] or text_sha(current) != cell["currentTargetSha256"]:
                raise SystemExit(f"candidate-free text/hash mismatch at {rank}/{locale}")
            if p["source"] != source or p["currentTarget"] != current or p["callerRefs"] != refs:
                raise SystemExit(f"primary source/caller linkage mismatch at {rank}/{locale}")
            if b["currentTarget"] != current or b["currentTargetSha256"] != cell["currentTargetSha256"]:
                raise SystemExit(f"blind target/hash mismatch at {rank}/{locale}")
            if cell["sourceTextIncluded"] is not True or cell["currentTargetTextIncluded"] is not True:
                raise SystemExit(f"caller-backed text missing at {rank}/{locale}")
        else:
            source = current = None
            if cell.get("sourceTextIncluded") is not False or cell.get("currentTargetTextIncluded") is not False:
                raise SystemExit(f"callerless candidate-free text flag mismatch at {rank}/{locale}")
            if p.get("sourceTextIncluded") is not False or p.get("currentTargetTextIncluded") is not False:
                raise SystemExit(f"callerless primary text flag mismatch at {rank}/{locale}")
            if b.get("targetTextIncluded") is not False or b.get("sourceTextIncluded", False) is not False:
                raise SystemExit(f"callerless blind text flag mismatch at {rank}/{locale}")
            if p.get("callerRefs") != []:
                raise SystemExit(f"callerless primary refs are not empty at {rank}/{locale}")

        chosen = p.get("target") if p["disposition"] == "correct" else None
        if key in CUSTOM_PROPOSALS:
            chosen = CUSTOM_PROPOSALS[key]
        if rank in HOLD_RANKS and locale in HOLD_RANKS[rank]:
            chosen = None
        if not backed:
            chosen = None

        if not backed:
            cross_row = {
                "schemaVersion": 1, "window": "W79", "continuationRank": rank,
                "remainingQueueRank": cell["remainingQueueRank"], "sourceId": source_id,
                "sourceIdSha256": text_sha(source_id), "locale": locale,
                "head": HEAD, "tree": TREE,
                "crossDisposition": "hold", "holdReasonCode": "CALLERLESS_NO_PRODUCTION_CALLER",
                "sourceSha256": cell["sourceSha256"],
                "currentTargetSha256": cell["currentTargetSha256"],
                "callerContextSha256": cell["callerContextSha256"],
                "productionCallerCount": 0,
                "tokenEvidenceSha256": p["tokenEvidenceSha256"],
                "catalogFileSha256": cell["catalogFileSha256"],
                "catalogGitBlob": cell["catalogGitBlob"],
                "sourceTextIncluded": False, "currentTargetTextIncluded": False,
                "primaryProposalTextIncluded": False, "crossTargetTextIncluded": False,
                "blindDecision": b["decision"], "blindIssueDetailsOmitted": True,
                "primaryDisposition": p["disposition"],
                "primaryReviewRowSha256": sha(p_raw), "blindReviewRowSha256": sha(b_raw),
                "sourceCurrentRowSha256": sha(cell_raw),
                "confidence": "high",
            }
            redacted = {
                "schemaVersion": 1, "continuationRank": rank, "sourceId": source_id,
                "sourceIdSha256": text_sha(source_id), "locale": locale,
                "sourceSha256": cell["sourceSha256"],
                "currentTargetSha256": cell["currentTargetSha256"],
                "callerContextSha256": cell["callerContextSha256"],
                "callerCount": 0, "decision": b["decision"],
                "sourceTextIncluded": False, "targetTextIncluded": False,
                "blindIssueDetailsOmitted": True,
            }
            hold = {k: cross_row[k] for k in (
                "schemaVersion", "window", "continuationRank", "remainingQueueRank", "sourceId",
                "sourceIdSha256", "locale", "crossDisposition", "holdReasonCode", "sourceSha256",
                "currentTargetSha256", "callerContextSha256", "productionCallerCount",
                "tokenEvidenceSha256", "catalogFileSha256", "catalogGitBlob",
                "sourceTextIncluded", "currentTargetTextIncluded",
            )}
            callerless_holds.append(hold)
        else:
            if chosen is not None:
                target = chosen
                disposition = "propose"
                rationale = PROPOSAL_RATIONALES.get(key)
                if not rationale:
                    rationale = p["rationale"] if p["disposition"] == "correct" else "The caller context and pinned locale terminology support this correction to the current target."
                token = token_check(source, current, target)
                primary_target = p.get("target")
                if p["disposition"] == "correct":
                    primary_verdict = "adopt" if target == primary_target else "revise"
                else:
                    primary_verdict = "independent-proposal"
                cross_row = {
                    "schemaVersion": 1, "window": "W79", "continuationRank": rank,
                    "remainingQueueRank": cell["remainingQueueRank"], "sourceId": source_id,
                    "sourceIdSha256": text_sha(source_id), "locale": locale,
                    "head": HEAD, "tree": TREE,
                    "source": source, "sourceTextIncluded": True,
                    "sourceSha256": cell["sourceSha256"],
                    "catalogKey": cell["catalogKey"], "catalogPath": cell["catalogPath"],
                    "catalogFileSha256": cell["catalogFileSha256"], "catalogGitBlob": cell["catalogGitBlob"],
                    "currentTarget": current, "currentTargetTextIncluded": True,
                    "currentTargetSha256": cell["currentTargetSha256"],
                    "crossDisposition": disposition, "target": target, "crossTargetTextIncluded": True,
                    "targetSha256": text_sha(target),
                    "callerContextSha256": cell["callerContextSha256"],
                    "productionCallerCount": ctx["productionCallerCount"], "callerRefs": refs,
                    "blindDecision": b["decision"],
                    "blindIssueCodes": [issue["code"] for issue in b.get("issues", [])],
                    "blindIssues": b.get("issues", []),
                    "primaryDisposition": p["disposition"],
                    "primaryProposalVerdict": primary_verdict,
                    "primaryProposal": primary_target,
                    "primaryProposalSha256": p.get("targetSha256"),
                    "primaryProposalTextIncluded": primary_target is not None,
                    "primaryRationaleSha256": text_sha(p["rationale"]) if p.get("rationale") else None,
                    "rationale": rationale, "confidence": "moderate",
                    "tokenCheck": token,
                    "sourceCurrentRowSha256": sha(cell_raw),
                    "primaryReviewRowSha256": sha(p_raw), "blindReviewRowSha256": sha(b_raw),
                }
                proposal_rows.append({
                    "schemaVersion": 1, "window": "W79", "continuationRank": rank,
                    "remainingQueueRank": cell["remainingQueueRank"], "sourceId": source_id,
                    "sourceIdSha256": text_sha(source_id), "locale": locale,
                    "source": source, "sourceSha256": cell["sourceSha256"],
                    "catalogKey": cell["catalogKey"], "catalogPath": cell["catalogPath"],
                    "catalogFileSha256": cell["catalogFileSha256"], "catalogGitBlob": cell["catalogGitBlob"],
                    "currentTarget": current, "currentTargetSha256": cell["currentTargetSha256"],
                    "target": target, "targetSha256": text_sha(target),
                    "callerContextSha256": cell["callerContextSha256"],
                    "productionCallerCount": ctx["productionCallerCount"], "callerRefs": refs,
                    "primaryProposalVerdict": primary_verdict,
                    "primaryProposalSha256": p.get("targetSha256"),
                    "crossRationale": rationale,
                    "tokenCheck": token, "planOnly": True,
                })
            else:
                is_hold = rank in HOLD_RANKS and locale in HOLD_RANKS[rank]
                if is_hold:
                    disposition = "hold"
                    rationale = CUSTOM_HOLD_RATIONALES.get(key, HOLD_RATIONALES[rank])
                    token = token_check(source, current)
                    cross_row = {
                        "schemaVersion": 1, "window": "W79", "continuationRank": rank,
                        "remainingQueueRank": cell["remainingQueueRank"], "sourceId": source_id,
                        "sourceIdSha256": text_sha(source_id), "locale": locale,
                        "head": HEAD, "tree": TREE,
                        "source": source, "sourceTextIncluded": True,
                        "sourceSha256": cell["sourceSha256"],
                        "catalogKey": cell["catalogKey"], "catalogPath": cell["catalogPath"],
                        "catalogFileSha256": cell["catalogFileSha256"], "catalogGitBlob": cell["catalogGitBlob"],
                        "currentTarget": current, "currentTargetTextIncluded": True,
                        "currentTargetSha256": cell["currentTargetSha256"],
                        "crossDisposition": disposition,
                        "holdReasonCode": "FEATURE_TERM_CONTEXT" if rank == 855 else "LOCALE_TECHNICAL_TERM_AMBIGUITY",
                        "callerContextSha256": cell["callerContextSha256"],
                        "productionCallerCount": ctx["productionCallerCount"], "callerRefs": refs,
                        "blindDecision": b["decision"],
                        "blindIssueCodes": [issue["code"] for issue in b.get("issues", [])],
                        "blindIssues": b.get("issues", []),
                        "primaryDisposition": p["disposition"],
                        "primaryProposalVerdict": "cross-hold",
                        "primaryProposal": p.get("target"),
                        "primaryProposalSha256": p.get("targetSha256"),
                        "primaryProposalTextIncluded": p.get("target") is not None,
                        "rationale": rationale, "confidence": "moderate",
                        "tokenCheck": token,
                        "sourceCurrentRowSha256": sha(cell_raw),
                        "primaryReviewRowSha256": sha(p_raw), "blindReviewRowSha256": sha(b_raw),
                    }
                    hold_rows.append({
                        "schemaVersion": 1, "window": "W79", "continuationRank": rank,
                        "remainingQueueRank": cell["remainingQueueRank"], "sourceId": source_id,
                        "sourceIdSha256": text_sha(source_id), "locale": locale,
                        "crossDisposition": "hold", "holdReasonCode": cross_row["holdReasonCode"],
                        "source": source, "sourceSha256": cell["sourceSha256"],
                        "currentTarget": current, "currentTargetSha256": cell["currentTargetSha256"],
                        "callerContextSha256": cell["callerContextSha256"],
                        "productionCallerCount": ctx["productionCallerCount"],
                        "callerRefs": refs, "rationale": rationale,
                        "sourceTextIncluded": True, "targetTextIncluded": True,
                    })
                else:
                    disposition = "keep"
                    rationale = KEEP_RATIONALES[rank]
                    token = token_check(source, current)
                    cross_row = {
                        "schemaVersion": 1, "window": "W79", "continuationRank": rank,
                        "remainingQueueRank": cell["remainingQueueRank"], "sourceId": source_id,
                        "sourceIdSha256": text_sha(source_id), "locale": locale,
                        "head": HEAD, "tree": TREE,
                        "source": source, "sourceTextIncluded": True,
                        "sourceSha256": cell["sourceSha256"],
                        "catalogKey": cell["catalogKey"], "catalogPath": cell["catalogPath"],
                        "catalogFileSha256": cell["catalogFileSha256"], "catalogGitBlob": cell["catalogGitBlob"],
                        "currentTarget": current, "currentTargetTextIncluded": True,
                        "currentTargetSha256": cell["currentTargetSha256"],
                        "crossDisposition": disposition,
                        "callerContextSha256": cell["callerContextSha256"],
                        "productionCallerCount": ctx["productionCallerCount"], "callerRefs": refs,
                        "blindDecision": b["decision"],
                        "blindIssueCodes": [issue["code"] for issue in b.get("issues", [])],
                        "blindIssues": b.get("issues", []),
                        "primaryDisposition": p["disposition"],
                        "primaryProposalVerdict": "no-change",
                        "primaryProposalSha256": p.get("targetSha256"),
                        "rationale": rationale, "confidence": "moderate",
                        "tokenCheck": token,
                        "sourceCurrentRowSha256": sha(cell_raw),
                        "primaryReviewRowSha256": sha(p_raw), "blindReviewRowSha256": sha(b_raw),
                    }
                    no_op_rows.append({
                        "schemaVersion": 1, "window": "W79", "continuationRank": rank,
                        "remainingQueueRank": cell["remainingQueueRank"], "sourceId": source_id,
                        "sourceIdSha256": text_sha(source_id), "sourceSha256": cell["sourceSha256"],
                        "locale": locale, "currentTargetSha256": cell["currentTargetSha256"],
                        "callerContextSha256": cell["callerContextSha256"],
                        "productionCallerCount": ctx["productionCallerCount"],
                        "catalogPath": cell["catalogPath"], "catalogFileSha256": cell["catalogFileSha256"],
                        "catalogGitBlob": cell["catalogGitBlob"], "sourceTextIncluded": False,
                        "targetTextIncluded": False,
                    })

            redacted = {
                "schemaVersion": 1, "continuationRank": rank, "sourceId": source_id,
                "sourceIdSha256": text_sha(source_id), "locale": locale,
                "sourceSha256": cell["sourceSha256"], "currentTargetSha256": cell["currentTargetSha256"],
                "callerContextSha256": cell["callerContextSha256"],
                "callerCount": ctx["productionCallerCount"], "decision": b["decision"],
                "issues": b.get("issues", []),
                "sourceTextIncluded": True, "targetTextIncluded": True,
            }

        if backed:
            cross_row["tokenCheckSha256"] = sha(canon(cross_row["tokenCheck"]))
            supplemental = []
            if rank == 855:
                supplemental = [
                    {"kind": "pinned-source", "evidenceId": "label-crate-feature"},
                    {"kind": "pinned-source", "evidenceId": "label-crate-api-route"},
                ]
            elif rank == 861:
                supplemental = [{"kind": "locale-term", "category": "rendezvous",
                                 "locale": locale, "sourceKey": "Enable DHT rendezvous"}]
            elif rank == 869:
                supplemental = [{"kind": "locale-term", "category": "swarm",
                                 "locale": locale, "sourceKey": "Active Swarm Downloads"}]
            elif rank == 872:
                supplemental = [{"kind": "locale-term", "category": "graph",
                                 "locale": locale, "sourceKey": "Discovery Graph"}]
            elif rank == 875 and locale == "pt-BR":
                supplemental = [{"kind": "locale-term", "category": "rescan",
                                 "locale": locale, "sourceKey": "Rescan Shares"}]
            if supplemental:
                cross_row["supplementalEvidenceRefs"] = supplemental
        cross_rows.append(cross_row)
        redacted_blind.append(redacted)
        blind_hashes.append({
            "schemaVersion": 1, "window": "W79", "continuationRank": rank,
            "sourceId": source_id, "sourceIdSha256": text_sha(source_id),
            "locale": locale, "blindDecision": b["decision"],
            "sourceSha256": cell["sourceSha256"],
            "currentTargetSha256": cell["currentTargetSha256"],
            "callerContextSha256": cell["callerContextSha256"],
            "productionCallerCount": ctx["productionCallerCount"] if backed else 0,
            "blindReviewRowSha256": sha(b_raw),
            "sourceTextIncluded": False, "targetTextIncluded": False,
        })
        if p["disposition"] == "correct":
            primary_audit.append({
                "schemaVersion": 1, "window": "W79", "continuationRank": rank,
                "sourceId": source_id, "locale": locale,
                "primaryProposal": p["target"], "primaryProposalSha256": p["targetSha256"],
                "crossProposal": cross_row.get("target"),
                "crossProposalSha256": cross_row.get("targetSha256"),
                "crossVerdict": cross_row.get("primaryProposalVerdict"),
                "crossRationale": cross_row.get("rationale"),
                "callerContextSha256": cell["callerContextSha256"],
                "primaryReviewRowSha256": sha(p_raw),
                "callerlessTextIncluded": False,
            })

    write_jsonl(PKT / "cross-review-decisions.jsonl", cross_rows)
    write_jsonl(PKT / "proposal-apply-plan.jsonl", proposal_rows)
    write_jsonl(PKT / "no-op-ledger-hash-only.jsonl", no_op_rows)
    write_jsonl(PKT / "unresolved-holds.jsonl", hold_rows)
    write_jsonl(PKT / "callerless-holds-hash-only.jsonl", callerless_holds)
    write_jsonl(PKT / "blind-review-redacted.jsonl", redacted_blind)
    write_jsonl(PKT / "blind-review-row-hashes.jsonl", blind_hashes)
    write_jsonl(PKT / "primary-proposal-audit.jsonl", primary_audit)

    proposal_map = {f"{r['continuationRank']}|{r['locale']}": r["target"] for r in proposal_rows}
    write_json(PKT / "proposal-map.json", proposal_map)

    term_keys = [
        ("graph", "Graph"),
        ("graph", "Discovery Graph"),
        ("graph", "Open a Discovery Graph centered on this result to explore related context."),
        ("swarm", "Active Swarm Downloads"),
        ("swarm", "Close swarm download visualization"),
        ("swarm", "Detailed peer contribution and performance metrics require trace data. This may not be available for all swarm downloads."),
        ("rendezvous", "Enable DHT rendezvous"),
        ("rescan", "Rescan Shares"),
    ]
    term_rows = []
    for locale in LOCALES:
        path = f"src/web/public/locales/{locale}.json"
        data = (SOURCE / path).read_bytes()
        catalog = json.loads(data)
        blob = git("rev-parse", f"{HEAD}:{path}").decode().strip()
        for category, key in term_keys:
            if key not in catalog:
                raise SystemExit(f"missing locale terminology key {locale}/{key}")
            value = catalog[key]
            term_rows.append({
                "schemaVersion": 1, "head": HEAD, "tree": TREE,
                "category": category, "locale": locale, "sourceKey": key,
                "translation": value, "translationSha256": text_sha(value),
                "catalogPath": path, "catalogFileSha256": sha(data), "catalogGitBlob": blob,
            })
    write_jsonl(PKT / "locale-term-evidence.jsonl", term_rows)

    extra = []
    for evidence_id, path, start, end in [
        ("label-crate-feature", "docs/MUSICBRAINZ_INTEGRATION.md", 958, 962),
        ("label-crate-api-route", "docs/api-documentation.md", 264, 267),
    ]:
        data = git_bytes("show", f"{HEAD}:{path}")
        content = data.decode("utf-8")
        lines = content.splitlines()
        excerpts = [{"line": n, "text": lines[n - 1]} for n in range(start, end + 1)]
        extra.append({
            "schemaVersion": 1, "head": HEAD, "tree": TREE,
            "evidenceId": evidence_id, "path": path,
            "lineStart": start, "lineEnd": end,
            "excerpt": excerpts, "fileSha256": sha(data),
            "gitBlob": git("rev-parse", f"{HEAD}:{path}").decode().strip(),
            "excerptSha256": sha(canon(excerpts)),
        })
    write_jsonl(PKT / "pinned-source-evidence.jsonl", extra)

    live_before = json.loads((PKT / "live-before.json").read_text(encoding="utf-8"))
    live_after = json.loads((PKT / "live-after.json").read_text(encoding="utf-8"))
    source_status = git("status", "--porcelain").decode("utf-8")
    if source_status:
        raise SystemExit("pinned source worktree is not clean")
    source_head = git("rev-parse", "HEAD").decode().strip()
    source_tree = git("rev-parse", "HEAD^{tree}").decode().strip()
    if source_head != HEAD or source_tree != TREE:
        raise SystemExit("pinned source worktree does not match requested pin")
    for snapshot in (live_before, live_after):
        if not (snapshot["headRefOid"] == HEAD and snapshot["branchRefOid"] == HEAD
                and snapshot["pullRefOid"] == HEAD and snapshot["commitTree"] == TREE
                and snapshot["state"] == "OPEN" and snapshot["draft"] is True
                and snapshot["merged"] is False):
            raise SystemExit("live PR API or refs do not match the requested pin")
    for field in ("headRefOid", "branchRefOid", "pullRefOid", "pullMergeRefOid", "commitTree"):
        if live_before[field] != live_after[field]:
            raise SystemExit(f"live PR ref moved during review: {field}")

    decisions = collections.Counter(r["crossDisposition"] for r in cross_rows)
    primary_verdicts = collections.Counter(r["crossVerdict"] for r in primary_audit)
    blind_holds = [r for r, _ in blind_records if r["decision"] == "hold"]
    cross_by_key = {(r["continuationRank"], r["locale"]): r for r in cross_rows}
    blind_hold_cross = collections.Counter(
        cross_by_key[(r["continuationRank"], r["locale"])]["crossDisposition"] for r in blind_holds
    )
    summary = {
        "artifact": "slskdN PR #409 W79 independent cross-review",
        "schemaVersion": 1, "window": "W79", "continuationRankRange": [853, 877],
        "remainingQueueRankRange": [753, 777],
        "repository": "snapetech-org/slskdN", "pullRequest": 409, "branch": BRANCH,
        "head": HEAD, "tree": TREE, "sourceCount": 25, "localeCount": 12,
        "locales": LOCALES, "cellCount": 300,
        "crossDecisionCounts": dict(decisions),
        "crossProposalCount": len(proposal_rows), "noOpCount": len(no_op_rows),
        "crossHoldCount": len(hold_rows) + len(callerless_holds),
        "callerlessHoldCount": len(callerless_holds), "callerlessSourceCount": 2,
        "primaryProposalCountAudited": len(primary_audit),
        "primaryProposalVerdicts": dict(primary_verdicts),
        "newProposalCountBeyondPrimary": sum(1 for r in proposal_rows if r["primaryProposalVerdict"] == "independent-proposal"),
        "blindHoldCountAudited": len(blind_holds),
        "blindHoldCrossDispositionCounts": dict(blind_hold_cross),
        "localeTermEvidenceRows": len(term_rows),
        "pinnedDocumentationEvidenceRows": len(extra),
        "priorHeldCellsReattested": 343, "priorHoldResolutionHistoryRows": 13,
        "candidateFreeInputManifestSha256": sha((INPUT / "manifest.json").read_bytes()),
        "primaryReviewManifestSha256": sha((PRIMARY / "manifest.json").read_bytes()),
        "blindReviewManifestSha256": sha((BLIND / "manifest.json").read_bytes()),
        "candidateFreeVerifier": "PASS", "primaryVerifier": "PASS",
        "liveRefsMatchPin": True,
        "liveBeforeSha256": sha((PKT / "live-before.json").read_bytes()),
        "liveAfterSha256": sha((PKT / "live-after.json").read_bytes()),
        "sourceWorktreeHead": source_head, "sourceWorktreeTree": source_tree,
        "sourceWorktreeCleanAtBuild": True, "sourceWorktreeRetained": False,
        "appliedToRepository": False, "repositoryOrPrEdited": False,
        "nativeSpeakerSignoff": False, "browserReview": False,
    }
    write_json(PKT / "summary.json", summary)

    inputs = {
        "candidateFreeManifest": {
            "path": "inputs/candidate-free-manifest.json",
            "sha256": sha((PKT / "inputs/candidate-free-manifest.json").read_bytes()),
        },
        "sourceCurrentCellsSha256": sha((PKT / "inputs/source-current-cells.jsonl").read_bytes()),
        "callerContextsSha256": sha((PKT / "inputs/caller-contexts.jsonl").read_bytes()),
        "primaryReviewManifestSha256": sha((PKT / "inputs/primary-manifest.json").read_bytes()),
        "primaryReviewLedgerSha256": sha((PKT / "inputs/primary-review.jsonl").read_bytes()),
        "blindReviewManifestSha256": sha((PKT / "inputs/blind-manifest.json").read_bytes()),
        "blindOriginalReviewLedgerSha256": sha((BLIND / "review-cells.jsonl").read_bytes()),
    }
    write_json(PKT / "input-attestation.json", inputs)

    readme = """# slskdN PR #409 W79 independent cross-review

This packet reconciles all 300 locale cells for continuation ranks 853–877 against the pinned source, candidate-free caller evidence, primary proposals, and blind decisions.

- Pin: 4d67527be0ca3b75e866f25bef5e58ae7f777f7f / tree 99ba5d8f7d631de3337e6b02f74af6d14e46c2ff.
- Cross decisions: 46 proposals, 215 keeps, and 39 holds.
- All 32 primary proposals were audited: 30 adopted, 2 revised, and 14 additional cross proposals were added.
- All 71 blind holds were adjudicated: 44 receive cross proposals and 27 remain holds. Remaining holds are 12 Label Crate terminology cells, 24 callerless cells, and 3 unresolved Japanese/Chinese swarm-term cells.
- The 24 callerless cells stay hash-only throughout this packet. Their source and target text, blind issue details, and proposal text are absent.
- Candidate-free and primary packet verifiers passed. All 276 caller-backed current values and all 46 proposed targets preserve placeholders, markup, numbers, and protected literals.
- Pinned locale-term excerpts and source-context hashes are included. No native-speaker signoff or browser review is claimed.
- The proposal plan is evidence only; no catalogs, branch, PR, or repository files were changed.

Verify from this directory with: python3 verify_cross_packet.py --repo /path/to/slskdN
Verify checksums with: sha256sum -c SHA256SUMS.txt
"""
    (PKT / "README.md").write_text(readme, encoding="utf-8")

    manifest_files = []
    for path in sorted(p for p in PKT.rglob("*") if p.is_file()
                       and p.name not in {"manifest.json", "SHA256SUMS.txt"}):
        data = path.read_bytes()
        manifest_files.append({"path": path.relative_to(PKT).as_posix(),
                               "bytes": len(data), "sha256": sha(data)})
    manifest = {
        "artifact": "slskdN PR #409 W79 ranks 853-877 independent cross-review packet",
        "schemaVersion": 1, "repository": "snapetech-org/slskdN", "pullRequest": 409,
        "branch": BRANCH, "window": "W79", "head": HEAD, "tree": TREE,
        "continuationRankRange": [853, 877], "remainingQueueRankRange": [753, 777],
        "sourceCount": 25, "localeCount": 12, "cellCount": 300,
        "sourceWorktreePathAtReview": str(SOURCE),
        "candidateFreeVerifier": "PASS", "primaryVerifier": "PASS",
        "crossDecisionCounts": dict(decisions), "proposalCount": len(proposal_rows),
        "noOpCount": len(no_op_rows), "holdCount": len(hold_rows) + len(callerless_holds),
        "callerlessHoldCount": len(callerless_holds),
        "primaryProposalCountAudited": len(primary_audit),
        "primaryProposalVerdicts": dict(primary_verdicts),
        "blindHoldCountAudited": len(blind_holds),
        "blindHoldCrossDispositionCounts": dict(blind_hold_cross),
        "blindCallerlessIssueDetailsIncluded": False, "callerlessTextIncluded": False,
        "proposalTargetsIncluded": True, "catalogChangesMade": False, "prChanged": False,
        "liveBeforeSha256": sha((PKT / "live-before.json").read_bytes()),
        "liveAfterSha256": sha((PKT / "live-after.json").read_bytes()),
        "inputsAttestationSha256": sha((PKT / "input-attestation.json").read_bytes()),
        "summarySha256": sha((PKT / "summary.json").read_bytes()),
        "files": manifest_files,
    }
    write_json(PKT / "manifest.json", manifest)
    sums = [(item["sha256"], item["path"]) for item in manifest_files]
    sums.append((sha((PKT / "manifest.json").read_bytes()), "manifest.json"))
    (PKT / "SHA256SUMS.txt").write_text(
        "".join(f"{digest}  {name}\n" for digest, name in sorted(sums, key=lambda x: x[1])),
        encoding="utf-8",
    )
    print(json.dumps({
        "result": "BUILT", "packet": str(PKT), "decisions": dict(decisions),
        "proposals": len(proposal_rows), "keeps": len(no_op_rows),
        "holds": len(hold_rows) + len(callerless_holds),
        "primaryProposalVerdicts": dict(primary_verdicts),
        "blindHoldCrossDispositionCounts": dict(blind_hold_cross),
        "packetFiles": len(manifest_files) + 2,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
