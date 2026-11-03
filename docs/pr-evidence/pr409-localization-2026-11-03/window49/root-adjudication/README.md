# slskdN PR #409 W49 root adjudication

This packet resolves the primary review and strict-blind cross-review for reconstructed continuation ranks 101–125 (25 source IDs × 12 locales = 300 cells). Historical extraction ordinals are unavailable and are not claimed.

The exact live PR head and tree were re-queried before sealing. All 12 catalog files, ordered key sets, source/current values, and 39 caller references across 23 files were reattested from the pinned commit. The independent review seal predates the primary comparison; no per-cell primary material was read before sealing.

The ledger records a final disposition and exact target for every cell. The exact-hash apply plan has 99 changes. All 12 rank-105 parser-like filter placeholders remain held and are excluded from the plan; their current values still have 21 protected-token mismatches, so they are not approved for localization. Other final targets pass placeholder, markup, ICU, and protected-literal checks.

Root dispositions: 189 accept-current, 83 corrections, 16 refinements, 12 holds. All 79 primary/cross target disagreements and all 33 normalized disposition disagreements are resolved in `adjudication-differences.jsonl`. Rank 120 explicitly deselects issues and reuses each locale’s exact Library Health term. Rank 122 explains the DHT peer-discovery behavior while preserving `DHT`.

Native-speaker approval is not claimed. No repository, PR, workflow, or release changes were made. No tests, builds, scans, CI, or browser work were performed. W50 was not prepared.

## Files

- `root-decisions.jsonl`: all 300 final per-cell decisions, evidence pins, rationale, and structural checks.
- `exact-hash-apply-plan.jsonl`: exact current/catalog/source/caller hashes and proposed updates.
- `adjudication-differences.jsonl`: all target disagreements and their root resolutions.
- `source-evidence.jsonl`: 25 source rows with exact caller/context pins.
- `catalog-term-anchors.json`: exact locale terminology referenced in root refinements.
- `exact-head-reattestation.json`: live PR, commit/tree, catalog, source, caller, and blindness verification.
- `summary.json`: disposition and validation counts.
- `SHA256SUMS.txt`: checksums for packet files other than itself.
