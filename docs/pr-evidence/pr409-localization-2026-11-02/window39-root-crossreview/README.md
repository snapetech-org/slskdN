# slskdN PR #409 W39 root cross-review and application

This exact-head window covers 25 source IDs at input head `54bbece421b44fae0cc9156c42a859848db8be5e` / tree `c9c5ea9d9cd444a677d5f3428a3e3d94c49c67f2` (source subtree `594e56c3f439bad476b1bd57e0de1665c62fa1bb`). Primary and independent packets are retained with their original checksums.

- Primary reviewed 275 non-Spanish cells; root cross-review independently accepted 238 current values and all 35 proposals (25 corrections, 10 refinements).
- Root found and fixed two missed issues: remove two zero-width spaces from the Vietnamese `Publish New Opinion` heading, and restore protected `FTP` in the Hindi settings-success message.
- Applied 37 exact-hash changes across 12 catalogs. The separate Spanish formal lane remains unchanged (25 targets re-attested); all 50 prior holds remain preserved. Every catalog retains the same ordered 6,169 keys. Source, caller, target, placeholder, protected-literal, exact readback, and catalog-order checks passed.

`apply-plan.jsonl` records exact before/after targets and decisions. `readback.jsonl` confirms every applied value and hash. The original primary review packet is under `primary/`; root decisions and Spanish lane re-attestation are under `cross-review/`. Qualified native-speaker and exact-head browser review remain outstanding. No tests, builds, scans, CI, workflow changes, releases, tags, or merges were performed.
