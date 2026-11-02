# PR #409 catalog correction application — windows 22–23

This bundle records the exact-hash application of 53 correction targets from manual review windows 22–23 and the independent review evidence for those targets. It also preserves the separate 12-row Realm cross-review from window 20, which resolved 12 earlier uncertain cells. Both cross-reviews are stored in distinct directories and have separate ledgers, summaries, and application-row ledgers.

## Pinned application

- Application commit: `740ae56ebe31893319648edadfc7da087ba5dfe3`
- Application tree: `b3b70ef49cc4ba2556c9960868231505fb57d1df`
- Application base: `64556f04f436af2e53860cdf14f0bf7d44118cfe` / tree `c101f1032ed25dcb6cd0d693704aac44bea0db2f`
- Frozen catalog baseline: `4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb` / tree `0eb84397dc2b4be4afd730f6818203bd5910cf15`
- Catalog census: 6,169 keys per locale, 12 locales, 74,028 values; 934 exact-hash corrections differ from the frozen baseline.

## Windows 22–23 cross-review

The independent reviewer accepted all 53 targets as proposed: 53 accepted, 0 refinements, 0 holds. The review covers 16 source keys across all 12 locales. Semantic confidence is high; locale-quality confidence is moderate; native-speaker review remains outstanding. The source ledger and summary are in `independent-cross-reviews/windows22-23/`. The application-row ledger is `applied-corrections-windows22-23.jsonl` (53 rows; SHA-256 `b5529b574ca56551087fddf4873dc219eced2b344d6311d3ae995e7b5e024499`). Exact IDs, proposed targets, proposed-target hashes, and pre-application target hashes match across the independent review and application ledgers.

## Separate window-20 Realm cross-review

The 12-row Realm review remains separate in `independent-cross-reviews/realm-window20/`; it accepted 10 targets as proposed and accepted 2 refined targets, with 0 holds. Its 12 exact-hash application rows are `applied-corrections-realm-window20.jsonl` (SHA-256 `f70d23171337491df198e8ca3532009764e54839a2edf67e36082d7cd34c8781`). This review resolved the 12 Realm cells originally marked uncertain in window 20; the original manual review rows are preserved unchanged.

## Reconciliation

Manual windows 1–23 cover 575 source keys / 6,900 cells: 5,752 keep, 928 correction decisions, and 220 originally uncertain. The separate Realm cross-review resolves 12 of those uncertain cells, leaving 208 unresolved uncertain values. There are 940 correction dispositions in total (928 manual correction decisions plus 12 independently resolved Realm cells): 934 have been applied and six remain held because exact source context is missing. The other 60,180 cells in the 67,080-cell frozen populated-catalog backlog remain unreviewed.

The post-application verifier result is in `verification.json`; the reproducible verifier is `verify_application.py`. The manifest records the input pins, ledger checksums, counts, and confidence status. `SHA256SUMS.txt` covers every packaged file except itself.

No tests, builds, or CI were run for this documentation/evidence package. No workflow, source-code, release, or tag changes are included. The PR remains open and draft; native-speaker review remains outstanding.
