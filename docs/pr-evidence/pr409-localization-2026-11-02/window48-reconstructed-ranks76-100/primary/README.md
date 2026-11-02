# slskdN PR #409 W48 primary populated-catalog review

## Pin and lane

- Live PR: https://github.com/snapetech-org/slskdN/pull/409 (OPEN, draft), head `0a6cbdcb606de1888045df358427eb2b81c85546`, tree `dcef8f70ea7c10926058c5db7430611b5faa07db`. GitHub API, local checkout, and clean worktree agree.
- The twelve direct locale catalogs have identical ordered key sets and contain 6,176 populated keys. Their file hashes and Git blob IDs are in `catalog-structure.jsonl`.
- W48 is the next deterministic reconstructed pending stable-ID lane after excluding the exact 1,122 W1-W45 evidence IDs, 25 W46 manual IDs, five W46 count-aware follow-up IDs, 25 W47 primary IDs, and the separately reviewed W71 rich-text source. These are 1,178 unique current source IDs, leaving 4,998 pending IDs. W48 takes continuation ranks 76-100, the first 25 remaining IDs. `selection-boundary.jsonl` records rank 75, ranks 76-100, and rank 101. No historical source ordinal is claimed.
- The W47 W54/W57 runtime follow-up reattests seven catalog values but does not add semantic dispositions for otherwise pending source IDs. `runtime-followup-boundary.json` records their positions; “Close another room before opening listen-along here.” is rank 77.

## Review packet

- 25 sources × 12 locales = 300 cells in `source-current-cells.jsonl` and `review-decisions.jsonl`.
- Exact source hashes, current target hashes, caller line/file hashes and Git blobs, line contexts, placeholder inventories, markup inventories, protected-term handling, primary dispositions, and target hashes are recorded per cell or source.
- Disposition counts: accept-current 228, hold 4, propose-correction 68. This is machine-assisted review; no native-speaker approval or headed-browser review is claimed.
- “Quarantine Jury updated” is held in ja, ko, zh-Hans, and zh-Hant based on unresolved prior protected-name evidence. The other locales reuse the prior per-locale keep decision.

## Limitations and side effects

Native-speaker review remains outstanding. No repository/catalog changes, tests, builds, scans, CI jobs, browser work, PR edits, commits, or pushes were performed. The packet is task-scoped scratch output only. `build_w48_primary.py` reproduces the packet from the pinned head and prior evidence.
