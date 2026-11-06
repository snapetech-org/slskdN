# slskdN PR #409 W45 reconstructed primary review

This static primary review covers 25 reconstructed pending source IDs × 12 locales = 300 cells at PR #409 head `6a082138c09fa8af40aee3258beb98523ee821d9`, tree `90142bfd8904d2a4428ea5f144848ba1c743bdd7`.

The PR was OPEN/DRAFT at both live checks. All seven localization PR heads were freshly queried before and after review; see `live-seven-pr-heads-start.json` and `live-seven-pr-heads-final.json`. ChaptarrNG #190 advanced during this review; the other five unrelated PRs stayed at their start heads, and #409 remained pinned. The exact worktree was clean at the pinned head before and after, and the remote PR branch matched that head; see `worktree-pre-review.json`, `exact-head.json`, and `final-reattestation.json`.

## Selection

The current 12 locale catalogs contain the same 6,170 ordered English source keys. This packet reattests the prior W1–W43 evidence (1,072 stable IDs), adds W44's 25 selected IDs, excludes the resulting 1,097 unique W1–W44 IDs, sorts the remaining source IDs lexicographically, and selects ranks 1–25. The historical W45 ordinal boundary was unavailable, so the packet records reconstructed selection ranks only and does not claim source ordinals. See `prior-source-ids.jsonl`, `source-inventory.jsonl`, `source-selection.jsonl`, and `order-and-boundary.json`.

The W44 apply readback was checked again against all 12 current catalogs at this head: all 300 W44 target hashes still match. The prior W44 root, primary, and cross-review checksum manifests also verify; see `prior-window-input-reattestation.jsonl` and `order-and-boundary.json`.

## Review

`review-decisions.jsonl` records exact source, current-target, reviewed-target, and catalog hashes for every cell. It includes caller context, source and target placeholders, markup, protected-literal checks, and Spanish formality-lane applicability. `caller-context.jsonl` and `caller-source-hits.jsonl` pin production callsites and localization dataflow lines. Six source strings use helper-based localization rather than a literal direct `interfaceText` call; their helper paths are pinned. There are no remaining caller gaps or unresolved static translation holds in this slice; native-speaker approval remains an open follow-up for every locale.

Dispositions: 265 accept-current, 29 propose-correction, and 6 propose-refinement. Thirty-five exact candidate replacements appear in `candidate-proposals.jsonl`. Current placeholders and markup match the source in all 300 cells. The sole protected-literal mismatch is the current Hindi `ContentID` transliteration in rank 24; its proposed replacement preserves the exact ASCII identifier. All reviewed targets preserve required placeholders, markup, and protected literals. See `structural-validation.jsonl`.

The Spanish formality accumulator is pinned to its exact SHA-256 in `spanish-formal-applicability.jsonl`; Spanish direct-address cells at ranks 11, 12, 17, and 22 are corrected to formal usted imperatives; ranks 8, 15, 16, 23, and 24 already use the formal register. Native-speaker approval remains outstanding for every locale. No browser review is claimed.

This is static source/caller review only. No repository files, PR contents, commits, or remote branches were changed. No tests, builds, scans, CI, browser review, native-speaker review, releases, or tags were run.

## Evidence files

- `review-decisions.jsonl`: all 300 exact-hash cell dispositions.
- `candidate-proposals.jsonl`: 34 proposed replacements with rationale and hashes.
- `structural-validation.jsonl`: placeholder, markup, and protected-literal readback.
- `caller-context.jsonl`, `caller-source-hits.jsonl`, `caller-gap-audit.jsonl`: production caller and localization helper pins.
- `prior-source-ids.jsonl`, `source-inventory.jsonl`, `source-selection.jsonl`: exact exclusion set and ranked selection.
- `live-seven-pr-heads-start.json`, `live-seven-pr-heads-final.json`, `exact-head.json`, `final-reattestation.json`: PR and worktree pins.
- `SHA256SUMS.txt`: checksums for the packet files (excluding the manifest itself).
