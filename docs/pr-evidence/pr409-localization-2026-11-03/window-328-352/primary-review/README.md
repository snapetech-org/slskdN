# slskdN PR #409 W58 primary semantic review

This primary review covers 25 source IDs (stable-ID ranks 328–352) across 12 locales, for 300 cells. It is bound to PR head `47735fbdb8df3de8dc5fd297c2717dc332764431`, tree `b29397903a036d40af1c6551dedbe070e735cfed`. The live PR was open and draft and the remote branch matched before packet generation. The complete candidate-free input was reviewed before writing this ledger; no blind or cross-audit output was consulted.

## Dispositions

- 267 accept-current
- 21 corrections recommended
- 12 refinements recommended
- 0 holds

The 33 proposals address the Chinese search-list label at rank 331, the enabled-feature heading at rank 335, the positive network-health heading at rank 336, the public DHT rendezvous notice at rank 343, the shown-of-total track count at rank 346, and the Hindi sync-interval label at rank 351. All other current cells were accepted. Every source has at least one pinned production caller; there are no callerless holds in this window.

All 300 current target hashes and source hashes were verified. Proposed values preserve exact placeholder counts and token order, markup, numeric tokens, edge whitespace, and protected literals `SongID`, `Soulseek`, `DHT`, `BitTorrent`, and `slskdN` where applicable. This machine review is not native-speaker approval.

## Prior input boundary note

The W57 `selection-and-boundary.json` has a known wrong `lastSelected`/`nextBoundary` index. This review used its checksummed complete `selection-boundary.jsonl` (ranks 303–327, next boundary 328), its 300 cell rows, and its 25 selected source rows; it did not trust the defective summary fields. The W58 packet independently re-attests ranks 328–352 and boundary 353 against the exact-head W49 inventory.

`primary-decisions.jsonl` contains per-cell current and proposed target hashes, caller context, disposition, rationale, confidence, protected-literal checks, and structural integrity checks. No repository or PR files were edited. No tests, builds, scans, CI, workflow, browser, merge, release, or tag actions were taken.
