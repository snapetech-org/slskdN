# PR #409 catalog correction application

This bundle records seven exact-hash-checked correction batches from the 17 disjoint populated-catalog review windows. The reviewed baseline is catalog commit `4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb`; correction commits run from `cf88dc6033a395db6a9d10d202349ec6f3bdceb7` through `295f33de43fbe4b6139f6800672411a2e90038c6`.

The manual review covered 5,100 cells across 425 source keys: 4,187 remain unchanged, 736 high-confidence correction cells were applied across all twelve locales, six correction rows remain held because the frozen review input lacked exact source context, and 171 uncertain values remain unchanged. The 736 applied cells cover 175 distinct source keys. Formal-result overlap and overlap among the manual windows were both zero.

The final correction-head census contains 6,169 nonempty entries in each of twelve catalogs (74,028 values). Comparing against the frozen catalog baseline, exactly the 736 cells in `applied-corrections.jsonl` changed; the catalogs retain matching key sets. Per-locale totals are in `manifest.json`.

- `applied-corrections.jsonl` records each source string, exact previous target/hash, applied target/hash, contextual reason, and source callsite/file/line hashes.
- `held-no-context.jsonl` records the six unapplied correction decisions lacking exact callsite/context.
- `preflight.json` preserves the exact-head, overlap, and source/target-hash preflight snapshot.
- `manifest.json` pins the seven commit/tree records and per-batch hashes.
- `verify_application.py` rechecks the batch commit chain, changed cells, source callsites, 12-catalog census, and all 5,100 final review dispositions.
- `verification.json` is the verifier result recorded at the final correction commit head.

Run the evidence verifier from the repository root with `python3 docs/pr-evidence/pr409-catalog-correction-application-2026-11-01/verify_application.py`. This is a data-integrity and evidence reconciliation check; no tests, builds, CI jobs, releases, or tags were run for this application.
