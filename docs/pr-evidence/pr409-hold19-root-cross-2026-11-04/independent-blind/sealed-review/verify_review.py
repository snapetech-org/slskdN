#!/usr/bin/env python3
from pathlib import Path
import json, re, subprocess, sys

OUT = Path(__file__).resolve().parent
IN = OUT.parent / 'input' / 'input'
expected_head = '03c73e7b6706d8a034d7a24d6984763134f61bac'
expected_tree = 'fa3f2041bbc2d4bb4eb512c03e874db3dbf631a5'

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]

subprocess.run([sys.executable, str(IN / 'verify_clean_input.py')], cwd=IN, check=True, stdout=subprocess.DEVNULL)
subprocess.run(['sha256sum', '-c', 'PACKET-SHA256SUMS.txt'], cwd=IN, check=True, stdout=subprocess.DEVNULL)
source = read_jsonl(IN / 'source-current-cells.jsonl')
ledger = read_jsonl(OUT / 'review-ledger.jsonl')
summary = json.loads((OUT / 'summary.json').read_text())
assert len(source) == 19 and len(ledger) == 19
assert summary['pinnedSource']['head'] == expected_head and summary['pinnedSource']['tree'] == expected_tree
assert summary['inputIntegrity']['candidateFree'] is True
assert summary['inputIntegrity']['historicalDispositionsIncluded'] is False
assert summary['publicStateAfter'] is not None
assert summary['noCatalogEditsOrPRStateChanges'] is True
source_by_key = {(r['sourceId'], r['locale'], r['continuationRank']): r for r in source}
seen = set()
for item in ledger:
    key = (item['sourceId'], item['locale'], item['continuationRank'])
    assert key in source_by_key and key not in seen
    seen.add(key)
    original = source_by_key[key]
    assert item['source'] == original['source']
    assert item['currentTarget'] == original['currentTarget']
    assert item['catalogPath'] == original['catalogPath'] and item['catalogKey'] == original['catalogKey']
    assert item['confidence'] in {'high', 'moderate', 'low', 'unknown'}
    assert item['rationale'].strip()
    if item['disposition'] == 'accept-current':
        assert item['proposedTarget'] is None and item['finalTarget'] == original['currentTarget']
    else:
        assert item['disposition'] == 'propose-correction'
        assert item['proposedTarget'] and item['proposedTarget'] != original['currentTarget']
        assert item['finalTarget'] == item['proposedTarget']
    final = item['finalTarget']
    # The input supplies exact token evidence. The reviewed scope has no tokens,
    # digits, markup tags, or protected literals; verify candidates stay aligned.
    assert re.findall(r'\{[^{}]+\}|%[A-Za-z0-9_]+', final) == original['placeholderEvidence']['sourceTokens']
    assert re.findall(r'\d+', final) == original['sourceNumericTokens']
    assert re.findall(r'<[^>]+>', final) == original['markupEvidence']['sourceTags']
    assert all(lit in final for lit in original['sourceProtectedLiterals'])
    assert item['tokenChecks']['placeholders']['matches'] is True
    assert item['tokenChecks']['numeric']['matches'] is True
    assert item['tokenChecks']['markup']['matches'] is True
    assert item['tokenChecks']['protectedLiterals']['matches'] is True
    if 'Servarr' in original['source']:
        assert 'Servarr' in final
        assert item['tokenChecks']['ServarrLiteral']['targetPreserved'] is True
assert len(seen) == 19
assert summary['decisions']['acceptCurrent'] == sum(x['disposition'] == 'accept-current' for x in ledger)
assert summary['decisions']['proposeCorrection'] == sum(x['disposition'] == 'propose-correction' for x in ledger)
assert summary['decisions']['acceptCurrent'] + summary['decisions']['proposeCorrection'] == 19
assert summary['tokenAndLiteralReview']['outputCandidatesChecked'] == summary['decisions']['proposeCorrection']
print('PASS: 19 cells, source alignment, dispositions, token/literal checks, input integrity, and pinned review metadata')
