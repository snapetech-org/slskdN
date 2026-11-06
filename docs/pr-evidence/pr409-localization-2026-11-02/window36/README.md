# slskdN PR #409 localization review window 36

This evidence records W36 at exact PR head `370c172e91935d7753c398eaf1b1fbc2e82f65ba` (tree `61bd0c6af797b0e810fdf9fad82c7d3a95c88b9c`). The source subtree was `594e56c439bad476b1bd57e0de1665c62fa1bb`. The PR remained open and draft when the packet was frozen.

## Scope and review

- 25 source keys and 275 pending cells across 11 locale catalogs; 25 Spanish cells stayed in the formal review lane.
- Primary review: 236 keep decisions and 39 correction proposals.
- Independent cross-review: accepted 36 proposals, refined 3, agreed with 228 keeps, found 5 missed corrections, and held 3 terminology questions for native-language review.
- The 44 applied corrections are the 36 accepted proposals, 3 refinements, and 5 missed corrections. The three held cells were preserved byte-for-byte.
- Source, current target, caller, placeholder, protected-literal, history-overlap, and exact-hash checks passed. The review covers 429 caller references over 39 unique lines. No duplicate routing, prior-review overlap, or no-op candidates were found.
- All 12 catalogs retain exactly 6,169 keys. The 11 edited catalogs have 44 changed cells; Spanish was not edited.

The primary packet's summary says it has 34 prior review windows, but the pinned ledgers contain 35 disjoint windows totaling 10,326 cells across 872 source keys. This metadata discrepancy is retained here rather than rewriting the frozen source packet.

## Changes and limits

The exact-hash apply plan and `apply-readback-report.json` record all 44 catalog updates and verify that every changed cell reads back as expected. No source or workflow file changed. No tests, builds, scans, CI jobs, releases, or tags were run or created.

The three terminology holds are Vietnamese `Previous native preset`, German `Manual Route Dispatch`, and Korean `Publish one descriptor for each listed ContentID to the DHT...`. They remain unchanged pending native-language review. Overall semantic confidence is moderate; machine review is not native-speaker approval.

## Evidence files

- `primary/`: frozen source/current/caller evidence and primary decisions.
- `crossreview/`: independent cell-by-cell review, missed-correction candidates, and holds.
- `exact-hash-apply-plan.jsonl`: the 44 exact old-target hashes and approved replacements.
- `apply-plan-summary.json`: pinned head and disposition counts.
- `apply-readback-report.json`: catalog key counts, changed-cell counts, and readback hashes.

The packet checksums are listed in `SHA256SUMS.txt`.
