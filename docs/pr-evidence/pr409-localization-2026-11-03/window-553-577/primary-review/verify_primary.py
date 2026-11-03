#!/usr/bin/env python3
import hashlib, json, re, subprocess, sys
from collections import Counter
from pathlib import Path

O = Path(__file__).resolve().parent
I = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w67-ranks553-577-candidate-free-20261103/input")
REPO = Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w66-apply-20261103/repo")
HEAD = "2dc64b9d00f6611aeb72713af81db53ccc5a4084"
TREE = "f13462300926ac897235cd92ae68c87695c38c31"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
BASE_KEYS = ("placeholder", "markup", "numeric", "protectedLiteral")

def sha(x):
    return hashlib.sha256(x if isinstance(x, bytes) else x.encode("utf-8")).hexdigest()

def j(p):
    return json.loads(p.read_text(encoding="utf-8"))

def jl(p):
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]

def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args], text=True).strip()

def ph(s):
    return sorted(set(re.findall(r"\{[^{}]+\}", s)))

def tags(s):
    return sorted(re.findall(r"</?[A-Za-z][^>]*>", s))

def nums(s):
    return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])", s)

def prot(s):
    found = set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])", s))
    for literal in ("Wishlist", "Soulseek", "Discogs", "Pod"):
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(literal) + r"(?![A-Za-z0-9])", s):
            found.add(literal)
    return sorted(found)

def token(s):
    return {"placeholders": ph(s), "markup": tags(s), "numeric": nums(s), "protectedLiterals": prot(s)}

def check_sums(folder, name):
    count = 0
    for line in (folder / name).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(None, 1)
        path = folder / rel.strip().lstrip("*")
        assert path.is_file() and sha(path.read_bytes()) == digest, f"checksum mismatch: {path}"
        count += 1
    return count

# Re-run the sealed candidate-free verifier and reattest exact local and live PR state.
in_result = subprocess.run([sys.executable, str(I / "verify_input.py")], capture_output=True, text=True)
assert in_result.returncode == 0, in_result.stdout + in_result.stderr
im = j(I / "manifest.json")
m = j(O / "manifest.json")
s = j(O / "summary.json")
assert im["candidateFree"] is True
assert (im["repository"], im["pullRequest"], im["branch"], im["head"], im["tree"]) == (
    "snapetech-org/slskdN", 409, BRANCH, HEAD, TREE)
assert (m["repository"], m["pullRequest"], m["branch"], m["window"], m["head"], m["tree"]) == (
    "snapetech-org/slskdN", 409, BRANCH, "W67", HEAD, TREE)
assert (m["sourceCount"], m["localeCount"], m["cellCount"], m["priorHeldCellsReattested"]) == (25, 12, 300, 128)
assert m["inputPath"] == str(I)
assert m["inputManifestSha256"] == sha((I / "manifest.json").read_bytes())
assert m["inputChecksumListSha256"] == sha((I / "PACKET-SHA256SUMS.txt").read_bytes())
assert m["inputLedgerSha256"] == sha((I / "source-current-cells.jsonl").read_bytes())
assert m["blindPacketAccessed"] is False
assert s["blindPacketAccessed"] is False
assert s["candidateFreeInputVerified"] is True
assert s["repositoryOrPRFilesEdited"] is False
assert s["nativeSpeakerReview"] == "not performed" and s["browserReview"] == "not performed"
assert m["nativeSpeakerReview"] == "not performed" and m["browserReview"] == "not performed"

head, tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
branch, status = git("branch", "--show-current"), git("status", "--porcelain=v1")
assert (head, tree, branch, status) == (HEAD, TREE, BRANCH, ""), (head, tree, branch, status)
pr = json.loads(subprocess.check_output(["gh", "api", "repos/snapetech-org/slskdN/pulls/409"], text=True))
assert pr["state"] == "open" and pr["draft"] is True
assert pr["head"]["sha"] == HEAD and pr["head"]["ref"] == BRANCH
assert pr["head"]["repo"]["full_name"] == "snapetech-org/slskdN"
refs = subprocess.check_output(["git", "-C", str(REPO), "ls-remote", "origin", f"refs/heads/{BRANCH}", "refs/pull/409/head"], text=True).splitlines()
refmap = {row.split()[1]: row.split()[0] for row in refs}
assert refmap.get(f"refs/heads/{BRANCH}") == HEAD and refmap.get("refs/pull/409/head") == HEAD
att = j(I / "head-tree-attestation.json")
assert (att["headRefName"], att["headRefOid"], att["treeOid"], att["branchRefOid"], att["pullRefOid"]) == (BRANCH, HEAD, TREE, HEAD, HEAD)

# Validate packet manifest, checksums, and exact candidate-free evidence links.
check_sums(O, "SHA256SUMS.txt")
actual_files = {p.name for p in O.iterdir() if p.is_file()} - {"manifest.json", "SHA256SUMS.txt"}
manifest_files = {row["path"]: row for row in m["files"]}
assert set(manifest_files) == actual_files, (sorted(set(manifest_files) - actual_files), sorted(actual_files - set(manifest_files)))
for name, item in manifest_files.items():
    data = (O / name).read_bytes()
    assert len(data) == item["bytes"] and sha(data) == item["sha256"], name

cells = jl(I / "source-current-cells.jsonl")
contexts = jl(I / "caller-contexts.jsonl")
rows = jl(O / "primary-ledger.jsonl")
assert len(cells) == len(rows) == 300 and len(contexts) == 25
ci = {(row["continuationRank"], row["locale"]): row for row in cells}
cx = {row["continuationRank"]: row for row in contexts}
assert len(ci) == 300 and len(cx) == 25
seen = set()
counts = Counter()
base = {key: 0 for key in BASE_KEYS}
final = {key: 0 for key in BASE_KEYS}
proposal_count = 0
caller_by_rank = {}
for ctx in contexts:
    rank = ctx["continuationRank"]
    assert rank not in caller_by_rank
    caller_by_rank[rank] = ctx["productionCallerCount"]
    assert ctx["callers"] and ctx["productionCallerCount"] == len(ctx["callers"])
assert sorted(caller_by_rank) == list(range(553, 578))
assert all(count > 0 for count in caller_by_rank.values())
assert s["callerCountByRank"] == {str(rank): count for rank, count in sorted(caller_by_rank.items())}

for row in rows:
    key = (row["continuationRank"], row["locale"])
    assert key not in seen
    seen.add(key)
    assert row["locale"] in LOCALES
    assert row["continuationRank"] in range(553, 578)
    assert row["remainingQueueRank"] == row["continuationRank"] - 100
    x, c = ci[key], cx[key[0]]
    counts[row["disposition"]] += 1
    assert (row["repository"], row["pullRequest"], row["window"], row["head"], row["tree"]) == (
        im["repository"], im["pullRequest"], "W67", HEAD, TREE)
    for field in ("sourceId", "source", "sourceSha256", "catalogKey", "catalogPath", "catalogFileSha256",
                  "catalogGitBlob", "currentTarget", "currentTargetSha256", "callerContextSha256",
                  "callerRefs", "continuationRank", "remainingQueueRank", "locale"):
        assert row[field] == x[field], (key, field)
    assert row["callerContexts"] == c["callers"]
    assert row["callerContextSourceId"] == c["sourceId"]
    assert row["callerContextSourceSha256"] == c["sourceSha256"]
    assert row["containsCandidate"] is False and row["verdict"] is None and row["rationale"]
    assert row["confidence"] in ("high", "moderate", "low")
    assert row["disposition"] in ("accept-current", "correction", "refinement", "hold")
    if row["disposition"] in ("correction", "refinement"):
        assert isinstance(row.get("proposedTarget"), str) and row["proposedTarget"]
        target = row["proposedTarget"]
        proposal_count += 1
    else:
        assert "proposedTarget" not in row
        target = row["currentTarget"]
    assert row["disposition"] != "hold", (key, "selected source has a caller and no hold was claimed")
    assert row["reviewedTargetSha256"] == sha(target)
    source_tokens, current_tokens, reviewed_tokens = token(row["source"]), token(row["currentTarget"]), token(target)
    checks = {
        "placeholdersPreserved": source_tokens["placeholders"] == reviewed_tokens["placeholders"],
        "markupPreserved": source_tokens["markup"] == reviewed_tokens["markup"],
        "numericTokensPreserved": source_tokens["numeric"] == reviewed_tokens["numeric"],
        "protectedLiteralsPreserved": all(literal in target for literal in source_tokens["protectedLiterals"]),
    }
    assert row["tokenAudit"] == {"source": source_tokens, "current": current_tokens, "reviewed": reviewed_tokens, "checks": checks}, key
    assert all(checks.values()), (key, checks)
    base["placeholder"] += source_tokens["placeholders"] != current_tokens["placeholders"]
    base["markup"] += source_tokens["markup"] != current_tokens["markup"]
    base["numeric"] += source_tokens["numeric"] != current_tokens["numeric"]
    base["protectedLiteral"] += not all(literal in row["currentTarget"] for literal in source_tokens["protectedLiterals"])
    final["placeholder"] += not checks["placeholdersPreserved"]
    final["markup"] += not checks["markupPreserved"]
    final["numeric"] += not checks["numericTokensPreserved"]
    final["protectedLiteral"] += not checks["protectedLiteralsPreserved"]

assert seen == set(ci)
assert dict(base) == im["baselineTokenMismatchSummary"] == {"placeholder": 0, "markup": 0, "numeric": 0, "protectedLiteral": 10}
assert dict(final) == {key: 0 for key in BASE_KEYS}
assert counts == Counter({"accept-current": 226, "correction": 33, "refinement": 41}), counts
assert proposal_count == 74
assert s["dispositionCounts"] == dict(counts) and s["proposalCount"] == proposal_count
assert m["dispositionCounts"] == dict(counts) and m["proposalCount"] == proposal_count
assert s["baselineTokenMismatches"] == dict(base) and s["reviewedTokenMismatches"] == dict(final)
assert s["priorHeldCellsReattested"] == 128 and s["priorHeldCellsUnchanged"] is True
assert s["callerlessSelectedRanks"] == []
prior = j(I / "prior-held-cell-reattestation-summary.json")
assert prior == {"expectedHeldCells": 128, "priorHeldCellsReattested": 128, "preW66Holds": 104, "w66Holds": 24,
                 "allTargetHashesMatchPrior": True, "allCurrentCallerAndCatalogEvidenceRepinned": True}
held = jl(I / "prior-held-cell-reattestation.jsonl")
assert len(held) == 128
assert sum(row["priorWindow"] == "W66" for row in held) == 24
assert sum(row["priorWindow"] != "W66" for row in held) == 104
assert sum(row["continuationRank"] in (533, 541) for row in held) == 24

print(json.dumps({
    "pass": True,
    "candidateFreeInputVerifier": "PASS",
    "checksums": "PASS",
    "livePR": {"state": "OPEN", "draft": True, "head": HEAD, "tree": TREE, "branch": BRANCH},
    "rows": 300,
    "sources": 25,
    "locales": 12,
    "dispositions": dict(counts),
    "proposals": proposal_count,
    "baselineTokenMismatches": dict(base),
    "reviewedTokenMismatches": dict(final),
    "priorHoldsReattested": {"total": 128, "preW66": 104, "W66": 24, "ranks533And541": 24},
    "callerlessSelectedSources": 0,
    "blindPacketAccessed": False,
    "nativeSpeakerReview": "not performed",
    "browserReview": "not performed",
    "repositoryOrPRFilesEdited": False
}, ensure_ascii=False, indent=2))
