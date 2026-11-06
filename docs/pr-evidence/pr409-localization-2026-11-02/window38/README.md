# slskdN PR #409 localization review window 38

## Scope and exact-head evidence

This window covers 269 target cells across 11 locales and 54 primary correction candidates for 25 source keys. The primary packet was frozen at `2be3fa4dd46a0f0f49adad342f289721e4777035`. After W37 advanced the PR, the independent cross-review re-attested all 269 source/current target hashes, 54 candidate hashes/literals, 48 unique caller lines, and 498 row-to-caller references at `36084c57b5a0e26804bc497c32d51c321258176d` (tree `a79ceb485188d131d93315718278d52d79e5ff8a`); no stale pins or W1–W37 overlaps were found.

The primary README exposed its proposed translations before the independent pre-comparison ledger was frozen; the packet records that review limitation.

## Result

- 48 primary candidates accepted as written.
- 3 primary candidates refined by cross-review.
- 8 errors missed by the primary review corrected from the cross-review recommendations.
- 3 Pod help fragments held pending review of the complete localized sentence around the literal `feature.Pods`.
- 207 remaining rows accepted unchanged; 50 older explicit holds were preserved separately.
- 59 exact-hash corrections were applied across 11 locale catalogs. Each catalog retains 6,169 keys, and all 59 target values were read back with matching hashes.

The 59 applied rows are 48 accepted proposals, 3 refinements, and 8 missed corrections. The three held rows were not applied. All 25 Spanish formal-lane rows remain outside this window.

## Review limits

This is a machine-assisted semantic review, not qualified native-speaker approval. The three Pod fragments remain held because the target is concatenated after a separately localized `Enable` label and the code literal `feature.Pods`; full composed sentence review is needed before those fragments can be accepted. Headed browser review is not complete for this window. The isolated Agent Desktop Pool review could not reach the private preview and its release returned `operator recovery required`; no retry was made.

No tests, builds, scans, CI runs, workflow edits, releases, tags, or merges were performed.

## Evidence

- `primary/`: frozen W38 primary packet and its original checksums.
- `cross-review/`: updated-head independent cross-review, re-attestation, and checksums.
- `root-apply/apply-plan.jsonl`: exact source/target hashes, dispositions, caller context, and approved corrections.
- `root-apply/readback.jsonl`: readback of each applied target at the resulting worktree state.
- `root-apply/apply-summary.json`: input/output pins, counts, catalog hashes, and validation limits.
