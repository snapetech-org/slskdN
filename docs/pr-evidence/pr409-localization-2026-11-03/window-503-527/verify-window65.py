#!/usr/bin/env python3
from pathlib import Path
import collections
import hashlib
import json
import subprocess
import sys

E = Path(__file__).resolve().parent
REPO = E.parents[3]
BASE = "c64d57a0322897bbaac77fa88a1327dd2f687db7"
TREE = "51ebf25124fc6ba30c8d5d99298e78353a951f17"
BRANCH = "codex/slskdn-oidc-tooltip-localization-20261030"
MODES = {"--precommit", "--prepush", "--evidence", "--postpush"}
mode = sys.argv[1] if len(sys.argv) > 1 else "--postpush"
assert mode in MODES, mode

def run(args, cwd=None):
    return subprocess.check_output(args, cwd=cwd or REPO, text=True).strip()

def rows(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def verify_sums(folder, filename):
    for line in (folder / filename).read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(None, 1)
            name = name.strip().lstrip("*")
            assert sha((folder / name).read_bytes()) == digest, (folder / name, "checksum")

def porcelain_paths():
    raw = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "--untracked-files=all", "-z"], cwd=REPO
    )
    paths = []
    for entry in raw.split(b"\0"):
        if entry:
            paths.append(entry[3:].decode("utf-8"))
    return paths

def verify_repo_sums():
    sums = E / "SHA256SUMS.txt"
    if not sums.exists():
        return
    for line in sums.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(None, 1)
            name = name.strip().lstrip("*")
            assert sha((E / name).read_bytes()) == digest, (E / name, "repository evidence checksum")

I = E / "candidate-free-input"
P = E / "primary-review"
B = E / "independent-blind-review"
BI = B / "blind-input"
X = E / "cross-audit"
verify_sums(I, "PACKET-SHA256SUMS.txt")
verify_sums(P, "SHA256SUMS.txt")
verify_sums(BI, "PACKET-SHA256SUMS.txt")
verify_sums(B, "SHA256SUMS.txt")
verify_sums(X, "SHA256SUMS.txt")
im = json.loads((I / "manifest.json").read_text())
pm = json.loads((P / "manifest.json").read_text())
bm = json.loads((B / "input-manifest.json").read_text())
xm = json.loads((X / "manifest.json").read_text())
assert (im["head"], im["tree"]) == (BASE, TREE)
assert (pm["head"], pm["tree"]) == (BASE, TREE)
assert (xm["head"], xm["tree"]) == (BASE, TREE)
assert im["repository"] == pm["repository"] == xm["repository"] == "snapetech-org/slskdN"
cells = rows(I / "source-current-cells.jsonl")
primary = rows(P / "primary-ledger.jsonl")
blind = rows(B / "sealed-translation-ledger.jsonl")
cross = rows(X / "crossaudit-decisions.jsonl")
assert len(cells) == len(primary) == len(blind) == len(cross) == 300
index = lambda rs, keys: {tuple(r[k] for k in keys): r for r in rs}
ci = index(cells, ["continuationRank", "locale"])
pi = index(primary, ["continuationRank", "locale"])
bi = index(blind, ["sourceId", "locale"])
xi = index(cross, ["continuationRank", "locale"])
assert len(ci) == len(pi) == len(xi) == 300 and len(bi) == 300
updates = {}
dispositions = collections.Counter()
for key, cell in ci.items():
    x = xi[key]
    p = pi[key]
    b = bi[(cell["sourceId"], cell["locale"])]
    audit = x["crossAudit"]
    assert x["sourceId"] == cell["sourceId"] and x["source"] == cell["source"]
    assert x["currentTarget"] == cell["currentTarget"]
    assert x["currentTargetSha256"] == cell["currentTargetSha256"]
    assert x["callerContextSha256"] == cell["callerContextSha256"]
    assert p["sourceId"] == cell["sourceId"] and p["currentTarget"] == cell["currentTarget"]
    assert p["callerContextSha256"] == cell["callerContextSha256"]
    assert b["sourceId"] == cell["sourceId"] and b["source"] == cell["source"]
    assert b["locale"] == cell["locale"]
    assert audit["selectedTargetSha256"] == sha(audit["selectedTarget"].encode())
    assert audit["tokenChecks"]["allPass"] is True
    dispositions[audit["disposition"]] += 1
    if audit["disposition"] in ("correction", "refinement"):
        assert audit["selectedTarget"] != cell["currentTarget"]
        updates[key] = (cell, audit)
    else:
        assert audit["selectedTarget"] == cell["currentTarget"]
        assert audit["disposition"] in ("accept-current", "hold")
assert dispositions == collections.Counter({
    "accept-current": 211, "correction": 73, "refinement": 10, "hold": 6
})
assert len(updates) == 83
catalogs = {}
for cell in cells:
    path = cell["catalogPath"]
    if path not in catalogs:
        raw = subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=REPO)
        assert sha(raw) == cell["catalogFileSha256"]
        assert run(["git", "rev-parse", f"{BASE}:{path}"]) == cell["catalogGitBlob"]
        catalogs[path] = (json.loads(raw.decode()), json.loads((REPO / path).read_text(encoding="utf-8")))
for path, (before, after) in catalogs.items():
    assert list(before) == list(after) and set(before) == set(after)
    selected = {
        cell["catalogKey"]: audit["selectedTarget"]
        for cell, audit in updates.values() if cell["catalogPath"] == path
    }
    for key in before:
        if key in selected:
            assert after[key] == selected[key], (path, key, "target mismatch")
        else:
            assert after[key] == before[key], (path, key, "non-target value changed")
for cell, audit in updates.values():
    assert catalogs[cell["catalogPath"]][1][cell["catalogKey"]] == audit["selectedTarget"]
prior = rows(X / "prior-held-cell-reattestation.jsonl")
prior_input = rows(I / "prior-held-cell-reattestation.jsonl")
assert len(prior) == len(prior_input) == 98 and prior == prior_input
for hold in prior:
    value = catalogs[hold["currentCatalogPath"]][1][hold["source"]]
    assert value == hold["currentTarget"]
    assert sha(value.encode()) == hold["currentTargetSha256"]
new_holds = [x for x in cross if x["crossAudit"]["disposition"] == "hold"]
assert len(new_holds) == 6 and {x["continuationRank"] for x in new_holds} == {504}
assert all(x["crossAudit"]["selectedTarget"] == x["currentTarget"] for x in new_holds)

allowed_catalogs = {cell["catalogPath"] for cell in cells}
evidence_rel = E.relative_to(REPO).as_posix()
def allowed(path):
    return path in allowed_catalogs or path.startswith(evidence_rel + "/")
diff_names = set(filter(None, run(["git", "diff", "--name-only", BASE]).splitlines()))
assert all(allowed(p) for p in diff_names), sorted(diff_names - allowed_catalogs)
assert not any(p.startswith(".github/workflows/") for p in diff_names)
check = subprocess.run(["git", "-C", str(REPO), "diff", "--check", BASE],
                       capture_output=True, text=True)
assert check.returncode == 0, check.stdout + check.stderr
status_paths = porcelain_paths()
head = run(["git", "rev-parse", "HEAD"])
tree = run(["git", "rev-parse", "HEAD^{tree}"])
state = json.loads(run(["gh", "api", "repos/snapetech-org/slskdN/pulls/409"]))
assert (state["state"], state["draft"], state["head"]["ref"], state["base"]["ref"]) == (
    "open", True, BRANCH, "main"
)
refs_text = run(["git", "ls-remote", "https://github.com/snapetech-org/slskdN.git",
                 f"refs/heads/{BRANCH}", "refs/pull/409/head"])
refs = {line.split()[1]: line.split()[0] for line in refs_text.splitlines() if line.strip()}
remote_branch = refs[f"refs/heads/{BRANCH}"]
remote_pr = refs["refs/pull/409/head"]
if mode == "--precommit":
    assert head == BASE and tree == TREE
    assert state["head"]["sha"] == BASE and remote_branch == remote_pr == BASE
    assert all(allowed(p) for p in status_paths), status_paths
    assert all(p in status_paths for p in allowed_catalogs)
elif mode == "--prepush":
    assert run(["git", "rev-parse", f"{head}^"]) == BASE
    assert not status_paths, status_paths
    assert state["head"]["sha"] == BASE and remote_branch == remote_pr == BASE
elif mode == "--evidence":
    assert head == "ed63a36e37f12b1061bed90418d52044e5bff410"
    assert state["head"]["sha"] == head and remote_branch == remote_pr == head
    assert all(p.startswith(evidence_rel + "/") for p in status_paths), status_paths
    verify_repo_sums()
else:
    assert state["head"]["sha"] == head and remote_branch == remote_pr == head
    assert not status_paths, status_paths
    verify_repo_sums()
    av_path = E / "application-verification.json"
    if av_path.exists():
        av = json.loads(av_path.read_text(encoding="utf-8"))
        applied = av["applicationCommit"]
        assert applied in run(["git", "rev-list", f"{BASE}..{head}"]).split()
        assert run(["git", "rev-parse", f"{applied}^{{tree}}"]) == av["applicationTree"]
        assert av["livePullRequestHead"] == applied
        assert av["branch"] == BRANCH
        assert av["catalogs"] == {
            path: sha((REPO / path).read_bytes()) for path in sorted(allowed_catalogs)
        }
av_path = E / "application-verification.json"
if av_path.exists():
    av = json.loads(av_path.read_text(encoding="utf-8"))
    applied = av["applicationCommit"]
    assert applied in run(["git", "rev-list", f"{BASE}..{head}"]).split()
    assert run(["git", "rev-parse", f"{applied}^{{tree}}"]) == av["applicationTree"]
    assert av["livePullRequestHead"] == applied
    assert av["branch"] == BRANCH
    assert av["catalogs"] == {
        path: sha((REPO / path).read_bytes()) for path in sorted(allowed_catalogs)
    }
print(json.dumps({
    "pass": True, "mode": mode, "reviewBaseHead": BASE, "reviewBaseTree": TREE,
    "currentHead": head, "currentTree": tree, "cells": 300,
    "dispositions": dict(dispositions), "updates": len(updates),
    "updatedCatalogs": len(catalogs), "nonTargetChanges": 0,
    "catalogKeyOrderPreserved": True, "priorHoldsPreserved": 98, "newHolds": 6,
    "workflowFilesTouched": False, "gitDiffCheck": "PASS", "pr": "OPEN/DRAFT"
}, indent=2))
