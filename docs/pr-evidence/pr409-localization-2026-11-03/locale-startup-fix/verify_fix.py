#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, subprocess

EVIDENCE = Path(__file__).resolve().parent
REPO = EVIDENCE.parents[3]
META = json.loads((EVIDENCE / "verification.json").read_text(encoding="utf-8"))
BASE = META["parentHead"]
FILES = META["changedSourceFiles"]

def run(*args):
    return subprocess.check_output(["git", *args], cwd=REPO).decode().strip()

assert run("rev-parse", f"{BASE}^{{tree}}") == META["parentTree"]
for path in FILES:
    assert run("rev-parse", f"{BASE}:{path}") == META["sourceBlobsBefore"][path]
    original = subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=REPO)
    assert hashlib.sha256(original).hexdigest() == META["sourceSha256Before"][path]
    current = (REPO / path).read_bytes()
    assert run("hash-object", path) == META["sourceBlobsAfter"][path]
    assert hashlib.sha256(current).hexdigest() == META["sourceSha256After"][path]

head = run("rev-parse", "HEAD")
if head == BASE:
    actual_patch = subprocess.check_output(["git", "diff", "--no-ext-diff", "--no-color", "--unified=0", BASE, "--", *FILES], cwd=REPO)
else:
    assert subprocess.run(["git", "merge-base", "--is-ancestor", BASE, head], cwd=REPO).returncode == 0
    actual_patch = subprocess.check_output(["git", "diff", "--no-ext-diff", "--no-color", "--unified=0", BASE, head, "--", *FILES], cwd=REPO)
assert actual_patch == (EVIDENCE / "patch.diff").read_bytes()
subprocess.check_call(["git", "diff", "--check", BASE, "--", *FILES], cwd=REPO)

entry = (REPO / FILES[0]).read_text(encoding="utf-8")
locale = (REPO / FILES[1]).read_text(encoding="utf-8")
assert entry.index("applyInitialInterfaceLanguage()") < entry.index("createRoot(")
assert ".catch(() => undefined)" in entry and ".then(() => {" in entry
assert "const subtags = normalized.split(/[-_]/);" in locale
assert "subtags.find((subtag) => subtag === 'hans' || subtag === 'hant')" in locale
assert locale.index("const script = subtags.find") < locale.index("/(?:^|[-_])(?:tw|hk|mo)(?:[-_]|$)/")
assert ".catch(() => null)" in locale
assert "activeLanguage = 'en';" in locale

changed = run("diff", "--name-only", BASE, head).splitlines() if head != BASE else run("diff", "--name-only", BASE).splitlines()
assert not any(path.startswith(".github/workflows/") for path in changed)
for line in (EVIDENCE / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    digest, name = line.split("  ", 1)
    assert hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest() == digest, name

print(json.dumps({"result":"PASS","base":BASE,"currentHead":head,"verifiedSourceFiles":FILES,"workflowFilesChanged":False}, indent=2))
