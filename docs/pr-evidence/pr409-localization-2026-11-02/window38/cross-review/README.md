# Independent cross-review: slskdN PR #409 W38

## Scope and updated pin

This packet covers all 269 W38 cells across 11 locales and the 54 primary correction proposals. The review packet was frozen at `2be3fa4dd46a0f0f49adad342f289721e4777035` / tree `f838ae565086dec8639f8a54aa4c7d4572342b5f`. W37 was pushed afterward. I re-attested every W38 source/current value, all candidates, and caller pins at updated PR head `36084c57b5a0e26804bc497c32d51c321258176d` / tree `a79ceb485188d131d93315718278d52d79e5ff8a`; the `src/web/src` subtree is still `594e56c3f439bad476b1bd57e0de1665c62fa1bb`.

All 269 W38 target strings and hashes still match. All 48 caller file/line pins and 498 row-to-caller references still match. W37 changed raw catalog file hashes but did not change any W38 target. W1–W37 manual cell/source overlap remains zero; the 25 Spanish formal-lane rows remain outside W38 decisions.

The primary README includes all 54 candidate texts and reasons. I read it before freezing the independent pre-comparison ledger, so this is not a blind review. The row-level primary JSONL ledgers were not opened in full before that ledger was frozen. This exposure is recorded in the ledgers.

## Cross-review dispositions

- **255 accepted:** 207 current targets plus 48 primary candidates.
- **3 refined:** Arabic, Simplified Chinese, and Traditional Chinese for “Search Segment.” The primary candidates remain noun-like or search for the segment itself; the caller performs a track search using an audio segment.
- **8 missed:** German, French, Hindi, Indonesian, Japanese, Korean, Brazilian Portuguese, and Vietnamese for “Search Segment.” Their current labels also read as a noun for a search segment.
- **3 held:** Arabic, Korean, and Vietnamese candidates for “in the server configuration to use pod rooms and discovery.” The fragment follows a separately translated “Enable” label and literal `feature.Pods`; review the composed localized sentence before applying the fragment proposals.
- **0 no-op cells.** All candidate texts differ from current targets.

The 11 Search Segment refinements/misses and their exact text hashes are in `additional-findings.jsonl`. All 54 exact primary candidates, hashes, and dispositions are in `primary-candidates-cross-reviewed.jsonl`. The three held primary proposals are in `held-proposals.jsonl`.

The “Skipped {count} texture asset” key is used only when exactly one texture asset is skipped. The plural branch uses a separate source key. All 11 current targets are accepted in this context; the check is recorded in `singular-texture-branch-check.json`.

## Preserved prior holds and review limits

All 50 explicit prior hold rows across seven source IDs remain unchanged and were re-attested at the updated head. Four caller refs available at W38 were verified; 47 original hold rows have no caller refs. They remain preserved separately from the 269 W38 cells. No native-speaker approval or headed browser review is recorded. Native language review and the composed Pod sentence review remain outstanding.

No catalog, source, workflow, or PR files were edited. No tests, builds, scans, CI, or releases were run.

## Evidence files

- `independent-precomparison-ledger.jsonl` and `independent-precomparison-summary.json`: pre-comparison cell dispositions and exposure note.
- `cross-review-ledger.jsonl`: all 269 updated-head dispositions, exact current/source hashes, caller refs, primary verdicts/candidates, and cross-review candidate texts/hashes.
- `primary-candidates-cross-reviewed.jsonl`: all 54 exact primary candidate texts/hashes and dispositions.
- `additional-findings.jsonl`: 3 refinements and 8 missed cells with exact candidate text/hash.
- `held-proposals.jsonl`: three exact primary candidates held pending composed-sentence review.
- `source-current-caller-reattestation.json`, `updated-head-reattestation.json`, `source-pins-reattested.jsonl`, and `caller-pins-reattested.jsonl`: updated-head source/current/catalog/caller verification.
- `prior-holds-reattested.jsonl`: preserved prior hold rows and caller evidence available at W38.
- `singular-texture-branch-check.json`: caller branch evidence for the singular texture message.
- `cross-review-summary.json` and `verification.json`: counts and integrity results.
- `SHA256SUMS`: checksums for every packet file except this checksum list.
