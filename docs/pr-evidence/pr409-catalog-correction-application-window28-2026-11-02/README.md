# Window 28 catalog correction application evidence

This bundle records 39 exact-hash corrections independently accepted by root cross-review at PR #409 head `17e8d8b829867065b882423ef81c69f1f31c7d07` / tree `7562b0dd09a92398a898d84e1c936119492015be` / source subtree `6d80c43cea32f0a5721f31235ec80e6eaa6d1896`. Root accepted all 39 proposals as written; none were refined or held. The application commit is `c420ebc057d675586eaf931d6f5daeb152a16c78` / tree `ff1c49d7bc72cae70e9d5c4b4c86442358a3474b`, a direct child of the review head.

The root cross-review ledger, exact apply plan, original proposal plan, applied-row ledger, and 24 unchanged uncertain rows are preserved separately. The application changed exactly 39 values across all twelve locale catalogs plus the cumulative CHANGELOG entry; it changed no other path.

The cumulative verifier reconciles all 28 disjoint manual windows, prior application and hold ledgers, the frozen baseline catalog census, source/current/proposal/final hashes, caller pins, formal-result overlap, uncertainty rows, PR state, and workflow/source path boundaries. After application, 1,153 values have changed across 270 source keys; six remain held, 244 remain uncertain, and 58,680 cells remain unreviewed. Native-speaker and headed-browser reviews remain outstanding. No tests, builds, CI, releases, or tags were run.
