# slskdN PR #409 localization review window 37

This exact-head window covers 25 disjoint source IDs across 11 locale catalogs and 273 target cells. Input head `2be3fa4dd46a0f0f49adad342f289721e4777035`; tree `f838ae565086dec8639f8a54aa4c7d4572342b5f`; `src/web/src` subtree `594e56c3f439bad476b1bd57e0de1665c62fa1bb`.

## Reconciled result

- Primary: 231 keep decisions and 42 correction candidates. Independent cross-review: 226 accepted current values, 41 accepted proposals, one refinement, and five missed corrections.
- Applied 47 exact-hash corrections (41 accepted, one refined, five missed) across 11 non-Spanish catalogs. The 25 formal Spanish cells and one exact-reuse cell remain outside this window's Spanish verdicts.
- All 273 source/current/final values, 383 caller references across 35 lines, and candidate hashes were re-attested. Placeholder/protected-literal mismatches: zero. All 12 locale catalogs retain 6,169 keys.

The `primary/` and `cross-review/` directories retain the frozen review packets and their original checksum manifests. `apply-plan.jsonl` records the 47 exact old/new values, hashes, rationale, and callers. `exact-head-final-readback.jsonl` verifies every reviewed cell after the edits; `apply-summary.json` records the disposition counts and pins. `SHA256SUMS.txt` covers this evidence directory.

No qualified native-speaker approval or browser review is recorded. No tests, builds, scans, CI, workflow edits, releases, tags, or merges were performed.
