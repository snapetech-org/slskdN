#!/usr/bin/env python3
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
