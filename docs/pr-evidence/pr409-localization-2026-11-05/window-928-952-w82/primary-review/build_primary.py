#!/usr/bin/env python3
"""Create the primary review ledger from the sealed W82 candidate-free input only."""
import collections
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent / "candidate-free" / "input"
REPO = Path(sys.argv[1]).resolve()
HEAD = "6e48a342d4b1c43918c23da3afcbaad19c87a005"
TREE = "b82ea7937cf9aa141a1c952283d5549dbe116ba5"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
INPUT_MANIFEST_SHA = None

SOURCE_CONTEXT = {
    928: "Player error toast explains that decoding failed and offers retry and likely causes.",
    929: "Spotify integration numeric field label for the maximum number of imported items.",
    930: "Wishlist action restores an ignored peer folder to future wishlist results; both values are interpolated.",
    931: "Live log warning explains that buffered entries remain available during reconnection.",
    932: "Jobs refresh tooltip describes reloading after job status or page data changes.",
    933: "Album completion badge in the album completion panel.",
    934: "VPN gateway tooltip removes a draft service and explains the save needed to stop advertising its route.",
    935: "Search empty-state caption when there are no searches to show.",
    936: "Admin policy field label for the JWT replacement key.",
    937: "Validation toast for a missing required item.",
    938: "Player button copies the generated radio search plan as plain text.",
    939: "Bridge setting names the soulfind executable and is also its default path value.",
    940: "System Events page description for reviewing recorded events and diagnostics.",
    941: "MediaCore card heading for PodCore metadata publication on the decentralized DHT.",
    942: "Accessible rating title with a dynamic rating value out of five.",
    943: "Save button in adversarial privacy and anonymity settings.",
    944: "No exact production caller exists at the pinned head, so the current label lacks enough context.",
    945: "Player control opens the browser audio-output chooser.",
    946: "Media server integration checklist status for adapter readiness.",
    947: "Queue control tooltip moves the current track earlier in playback order.",
    948: "Heading for the slskdN Wishlist request review packet.",
    949: "SongID scorecard label for comment findings.",
    950: "Wishlist action marks the search results as viewed.",
    951: "Room-broadcast tooltip retries publishing the current playback state after an update failure.",
    952: "Setup health-check group for runtime and operational diagnostics.",
}

PROPOSALS = {
    (929, "es"): ("Máximo de elementos por importación", "The current wording is an unnatural noun phrase. This is a numeric limit on imported entries.", "moderate"),
    (929, "id"): ("Jumlah maksimum item per impor", "The current abbreviation is too telegraphic for a settings label; this names the maximum item count per import.", "moderate"),
    (929, "ko"): ("가져오기당 최대 항목 수", "수입당 품목 suggests commercial imports. This field limits items brought in by a software import.", "moderate"),
    (929, "vi"): ("Số mục tối đa mỗi lần nhập", "Adding the count noun makes this setting label clearly describe the maximum item count per import.", "moderate"),
    (936, "hi"): ("JWT कुंजी", "JWT is a protocol acronym and should remain in its exact Latin form in this security field label.", "high"),
    (936, "zh-Hans"): ("JWT 密钥", "The current target transliterates JWT as a Chinese name. Preserve the exact security acronym.", "high"),
    (936, "zh-Hant"): ("JWT 金鑰", "The current target transliterates JWT as a Chinese name. Preserve the exact security acronym.", "high"),
    (938, "fr"): ("Copier le plan", "The current wording means a copy plan; this button performs the action of copying the plan.", "moderate"),
    (938, "ja"): ("プランをコピー", "This is a button action, so use the natural verb phrase instead of a noun-like compound.", "moderate"),
    (939, "ar"): ("soulfind", "This is the executable name and default command value, not prose to translate; remove the added package-like prefix.", "high"),
    (939, "de"): ("soulfind", "This is the executable name and default command value, not prose to translate.", "high"),
    (939, "es"): ("soulfind", "This is the executable name and default command value, not prose to translate.", "high"),
    (939, "fr"): ("soulfind", "This is the executable name and default command value, not prose to translate.", "high"),
    (939, "hi"): ("soulfind", "This is the executable name and default command value, not prose to translate.", "high"),
    (939, "id"): ("soulfind", "This is the executable name and default command value, not prose to translate.", "high"),
    (939, "ja"): ("soulfind", "This is the executable name and default command value, not prose to translate.", "high"),
    (939, "ko"): ("soulfind", "This is the executable name and default command value, not prose to translate.", "high"),
    (939, "pt-BR"): ("soulfind", "This is the executable name and default command value, not prose to translate.", "high"),
    (939, "vi"): ("soulfind", "This is the executable name and default command value, not prose to translate.", "high"),
    (939, "zh-Hans"): ("soulfind", "This is the executable name and default command value, not prose to translate.", "high"),
    (939, "zh-Hant"): ("soulfind", "This is the executable name and default command value, not prose to translate.", "high"),
    (941, "ar"): ("النشر عبر PodCore DHT", "Keep the PodCore product name intact and express that this section publishes through its DHT.", "moderate"),
    (941, "es"): ("Publicación en PodCore DHT", "The current noun order is awkward. This keeps the product name and describes publishing on its DHT.", "moderate"),
    (941, "fr"): ("Publication sur PodCore DHT", "This heading names publication on the PodCore DHT; keep the product name intact.", "moderate"),
    (941, "hi"): ("PodCore DHT पर प्रकाशन", "Keep the PodCore product name intact and express publication on its DHT.", "moderate"),
    (941, "ko"): ("PodCore DHT 게시", "Keep the PodCore product name intact rather than transliterating it.", "moderate"),
    (945, "de"): ("Audioausgabe auswählen", "This control opens an output chooser. The current wording is missing a natural compound and reads awkwardly.", "moderate"),
    (947, "ar"): ("انقل هذا المقطع إلى موضع أسبق في قائمة الانتظار.", "In the pinned player caller, this is a music track rather than a path; name the track and its earlier queue position.", "moderate"),
    (950, "ar"): ("وضع علامة كمُشاهَد", "The current wording reads as 'display the mark'. This action marks results as viewed.", "moderate"),
    (950, "de"): ("Als angesehen markieren", "The current label omits the action's 'as viewed' relationship. This is the standard concise UI action.", "moderate"),
    (950, "es"): ("Marcar como visto", "The current label omits 'as viewed'. This is the concise action used to mark the results as seen.", "moderate"),
    (950, "fr"): ("Marquer comme consulté", "The current wording omits 'as viewed'. This names the viewed status the action applies.", "moderate"),
    (950, "hi"): ("देखे गए के रूप में चिह्नित करें", "This action applies the viewed status to the search results; the current wording does not express that relationship clearly.", "moderate"),
    (951, "id"): ("Coba kirim ulang status pemutaran saat ini untuk ruang ini setelah pembaruan gagal.", "The current word order is ungrammatical. This expresses retrying the room's current playback-state update.", "moderate"),
    (951, "vi"): ("Thử gửi lại trạng thái phát hiện tại của phòng này sau khi cập nhật thất bại.", "The current word for publishing suggests publishing an edition. In this caller the state is sent as a room broadcast update.", "moderate"),
    (952, "ja"): ("運用", "This health-check group covers runtime state and operations; 運営 suggests managing an organization.", "moderate"),
    (952, "vi"): ("Vận hành", "This setup category covers operational and runtime checks; hoạt động is too broad for the section label.", "moderate"),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tsha(text):
    return sha(text.encode("utf-8"))


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def protected(text):
    values = set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", text))
    values.update(x for x in ("slskdN", "PodCore", "Wishlist", "soulfind", "FFmpeg") if x in text)
    return sorted(values)


def token_check(source, current, candidate=None):
    ph = lambda s: collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", s))
    tags = lambda s: collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", s))
    nums = lambda s: ["".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in n) for n in re.findall(r"\d+", s)]
    sp = ph(source)
    st = tags(source)
    sn = nums(source)
    sl = protected(source)
    def check(value):
        return {"placeholderParity": ph(source) == ph(value), "markupParity": tags(source) == st,
                "numericTokensPreserved": all(nums(value).count(x) >= n for x, n in collections.Counter(sn).items()),
                "protectedLiteralsPreserved": all(token in value for token in sl),
                "missingProtectedLiterals": [token for token in sl if token not in value]}
    return {"current": check(current), "candidate": check(candidate) if candidate is not None else None}


def main():
    if subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip() != HEAD:
        raise SystemExit("REFUSED: current worktree head drift")
    if subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD^{tree}"], text=True).strip() != TREE:
        raise SystemExit("REFUSED: current worktree tree drift")
    if subprocess.check_output(["git", "-C", str(REPO), "status", "--porcelain=v1"], text=True).strip():
        raise SystemExit("REFUSED: current worktree not clean")
    checksums = {}
    for line in (INPUT / "SHA256SUMS.txt").read_text().splitlines():
        digest, name = line.split("  ", 1)
        path = INPUT / name
        if not path.is_file() or sha(path.read_bytes()) != digest:
            raise SystemExit("REFUSED: candidate-free input checksum " + name)
        checksums[name] = digest
    manifest = json.loads((INPUT / "manifest.json").read_text())
    if manifest.get("head") != HEAD or manifest.get("tree") != TREE or manifest.get("candidateFree") is not True:
        raise SystemExit("REFUSED: candidate-free packet identity")
    rows = read_jsonl(INPUT / "source-current-cells.jsonl")
    if len(rows) != 300 or len({(row["continuationRank"], row["locale"]) for row in rows}) != 300:
        raise SystemExit("REFUSED: candidate-free cell coverage")
    input_manifest_sha = sha((INPUT / "manifest.json").read_bytes())

    output, corrections, holds = [], [], []
    for source_row in rows:
        rank, locale = source_row["continuationRank"], source_row["locale"]
        source, current = source_row["source"], source_row["currentTarget"]
        proposal = PROPOSALS.get((rank, locale))
        if rank == 944:
            disposition = "hold"
            target = None
            rationale = SOURCE_CONTEXT[rank]
            confidence = "high"
        elif proposal:
            target, rationale, confidence = proposal
            disposition = "correction"
        else:
            target = None
            disposition = "accept-current"
            rationale = SOURCE_CONTEXT[rank]
            confidence = "moderate"
        token_evidence = token_check(source, current, target)
        if target is not None and not all(token_evidence["candidate"][key] for key in ("placeholderParity", "markupParity", "numericTokensPreserved", "protectedLiteralsPreserved")):
            raise SystemExit(f"REFUSED: candidate token mismatch at {rank}/{locale}")
        row = {"schemaVersion": 1, "reviewPass": "primary", "head": HEAD, "tree": TREE,
               "continuationRank": rank, "remainingQueueRank": source_row["remainingQueueRank"],
               "sourceId": source_row["sourceId"], "sourceSha256": source_row["sourceSha256"],
               "locale": locale, "catalogPath": source_row["catalogPath"],
               "catalogFileSha256": source_row["catalogFileSha256"], "catalogGitBlob": source_row["catalogGitBlob"],
               "source": source, "sourceTextIncluded": True, "currentTarget": current,
               "currentTargetSha256": source_row["currentTargetSha256"], "currentTargetTextIncluded": True,
               "callerCount": source_row["callerCount"], "callerContextSha256": source_row["callerContextSha256"],
               "callerRefs": source_row["callerRefs"], "disposition": disposition, "rationale": rationale,
               "confidence": confidence, "tokenCheck": token_evidence,
               "candidateTarget": target, "candidateTargetSha256": tsha(target) if target is not None else None,
               "candidateTargetTextIncluded": target is not None}
        if rank == 944 and source_row["callerCount"] != 0:
            raise SystemExit("REFUSED: rank 944 caller status changed")
        if rank != 944 and source_row["callerCount"] == 0:
            raise SystemExit("REFUSED: unexpected callerless selected source")
        output.append(row)
        if disposition == "correction":
            corrections.append({k: row[k] for k in ("continuationRank", "remainingQueueRank", "sourceId", "sourceSha256", "locale",
                "currentTargetSha256", "candidateTarget", "candidateTargetSha256", "rationale", "confidence")})
        if disposition == "hold":
            holds.append({"continuationRank": rank, "remainingQueueRank": source_row["remainingQueueRank"],
                          "sourceId": source_row["sourceId"], "sourceSha256": source_row["sourceSha256"],
                          "locale": locale, "currentTargetSha256": source_row["currentTargetSha256"],
                          "callerCount": 0, "callerContextSha256": source_row["callerContextSha256"],
                          "holdReasonCode": "NO_PINNED_PRODUCTION_CALLER", "holdReasonSha256": tsha(rationale),
                          "sourceTextIncluded": False, "targetTextIncluded": False})

    def write_json(name, obj):
        (ROOT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    def write_jsonl(name, items):
        with (ROOT / name).open("w", encoding="utf-8", newline="\n") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")

    write_jsonl("primary-review.jsonl", output)
    write_jsonl("corrections.jsonl", corrections)
    write_jsonl("holds-hash-only.jsonl", holds)
    counts = collections.Counter(row["disposition"] for row in output)
    write_json("summary.json", {"artifact": "slskdN PR #409 W82 primary review", "window": "W82", "head": HEAD, "tree": TREE,
        "inputManifestSha256": input_manifest_sha, "sourceCount": 25, "cellCount": 300, "localeCount": 12,
        "dispositionCounts": dict(counts), "correctionCount": len(corrections), "holdCellCount": len(holds),
        "heldSourceRanks": [944], "sourceRewriteRecommendations": 0, "candidateFreeInputOnly": True,
        "blindReviewUsed": False, "crossReviewUsed": False, "rootAdjudicationDone": False,
        "nativeSpeakerSignoff": False, "browserReview": False})
    readme = ("# slskdN PR #409 W82 primary review\n\n"
        "This primary review covers stable continuation ranks 928–952 and remaining-queue ranks 828–852: 300 cells across 12 locales. "
        "It is tied to candidate-free input manifest SHA-256 `" + input_manifest_sha + "`, head `" + HEAD + "`, and tree `" + TREE + "`.\n\n"
        "The review records " + str(counts["accept-current"]) + " accept-current cells, " + str(counts["correction"]) +
        " correction candidates, and " + str(counts["hold"]) + " holds. Rank 944 is held in all locales because no production caller is pinned. "
        "Correction candidates preserve source placeholders and protected technical literals.\n\n"
        "This is primary review only. It did not use blind or cross-review proposals, and no root adjudication or native-speaker signoff is claimed. "
        "No catalog/source/workflow edits were proposed for application; no tests, builds, repository scans, CI, merge, release, or tag were performed.\n")
    (ROOT / "README.md").write_text(readme, encoding="utf-8")

    payloads = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and p.name not in {"manifest.json", "SHA256SUMS.txt"})
    file_rows = [{"path": name, "sha256": sha((ROOT / name).read_bytes()), "bytes": (ROOT / name).stat().st_size} for name in payloads]
    write_json("manifest.json", {"artifact": "slskdN PR #409 W82 primary review", "schemaVersion": 1,
        "repository": "snapetech-org/slskdN", "pullRequest": 409, "window": "W82", "head": HEAD, "tree": TREE,
        "candidateFreeInputManifestSha256": input_manifest_sha, "candidateFreeInputChecksumListSha256": sha((INPUT / "SHA256SUMS.txt").read_bytes()),
        "sourceCount": 25, "localeCount": 12, "cellCount": len(output), "dispositionCounts": dict(counts),
        "correctionCount": len(corrections), "holdCellCount": len(holds), "sourceRewriteRecommendations": 0,
        "blindReviewUsed": False, "crossReviewUsed": False, "rootAdjudicationDone": False, "files": file_rows})
    sealed = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    (ROOT / "SHA256SUMS.txt").write_text("\n".join(f"{sha((ROOT / name).read_bytes())}  {name}" for name in sealed) + "\n", encoding="utf-8")
    print(json.dumps({"result": "SEALED-PRIMARY", "head": HEAD, "tree": TREE, "cellCount": len(output),
                      "dispositions": dict(counts), "corrections": len(corrections), "holds": len(holds),
                      "inputManifestSha256": input_manifest_sha}, indent=2))


if __name__ == "__main__":
    main()
