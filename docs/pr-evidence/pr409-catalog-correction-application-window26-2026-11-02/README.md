# Window 26 catalog correction application evidence

This bundle records the 48 exact-hash corrections independently accepted by root cross-review and applied in commit `792f19f3ecf0370ff0cc65307cab376dd5512498` (tree `bb05bd2fb2d71937d12e2123237051ef02563013`). The application commit is a direct child of the review head `7c3283a340324e19577a486bfc427eb40b6eb5f2` and changed only the 12 locale JSON catalogs plus `docs/CHANGELOG.md`.

The independent root ledger and exact apply plan are preserved as separate files. The 12 no-caller Smart-radio Wishlist rows are in `uncertain-review-rows.jsonl`; their current translations were checked and remain unchanged. The application ledger is `applied-corrections-window26.jsonl`.

`verify_application.py` reconciles all 26 manual windows, prior application and hold ledgers, the frozen baseline catalog census, exact source/caller/target hashes, formal-result overlap, uncertainty rows, PR state, and workflow/source path boundaries. It requires the repository evidence paths and review snapshots recorded in the manifest.

The cumulative census after application is 1,070 changed values across 257 source keys, six held cells, 220 remaining uncertain cells, and 59,280 unreviewed cells. Native-speaker and headed-browser review remain outstanding. No tests, builds, CI, releases, or tags were run.
