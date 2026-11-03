# slskdN PR #409 W59 ranks 353–377 third-party cross-audit

The audit is pinned to open draft PR head `fd6bf5c72a668eecac8cc57e4587bced7e4d9aad` (tree `01c4bb4ea231e6ba72c3087d133b6e3e669853d9`). The candidate-free input, primary ledger, and independent blind ledger each passed their checksum manifests; the live PR, branch ref, and live PR record still match this head.

## Result

The 300 cells reconcile to **207 accept-current, 54 corrections, 15 refinements, and 24 holds**. The 24 holds cover all locales for rank 356 (`Add Torrent`) and rank 366 (`Searches`), each with zero pinned production callers. Those targets remain unchanged. The 69 selected catalog updates are supported by exact caller context, current catalog values, and review lineage.

The structural reconciliation verified source/current hashes, every locale catalog SHA-256 and Git blob, all 300 current values at the exact head, placeholder and markup parity, numeric tokens, protected literals, and edge whitespace. The two spaces and `{summary}` at rank 360 and `{label}` at rank 367 are retained. `slskdN` remains exact at rank 362; the technical term `swarm` remains present at rank 355, with the ordinary German noun capitalization in `Swarm`.

## Reconciliation decisions

- The primary and blind ledgers agree on the 24 no-caller holds and on which cells need correction at ranks 353, 357, 370, 372, and 377; where wording differs, row-level lineage records both candidates and the selected target.
- The exact `Messages` locale key supports translating the Hindi and Vietnamese “Messages UI” tooltip at rank 368; Hindi’s blind finding is accepted while the English “Messages” token is removed.
- Rank 362 follows each locale’s adjacent `Peers are discovered through searches and downloads` catalog term. This preserves the established peer terminology and avoids introducing a new “node” concept in Vietnamese.
- Rank 365’s checkbox filters unread release-radar notifications; the selected labels name the filtered notifications. The Traditional Chinese target also replaces the current Simplified character.
- Rank 367 is an accessible dropdown name. The selected locale order expresses “options for {label}” and preserves the placeholder.
- Rank 372 is a passing setup-health status produced when no enabled provider credential gaps remain. The chosen translations say no credentials are missing; this avoids suggesting every optional provider is fully configured.
- At rank 374, the standalone `Wishlist` key is already translated in every exact-head locale catalog. The cross-audit applies that current catalog vocabulary to the modal title in all 12 locales, including six cells where both reviewers had accepted the mixed-English current string. The exact values are recorded in `supplemental-catalog-context.json`.

Across the 300 cells, the primary and blind reviewers differ in disposition on 39 cells and in selected target on 53 cells; 15 cells have the same correction disposition but different target wording. The row-level ledger retains both reviews, each review row hash, and the adjudicated target hash. The blind reviewer accepted current values in some cells where the primary reviewer found context-specific improvements. The cross-audit retained changes where the exact caller and neighboring locale terms supported the correction. For the two callerless source keys, the existing values are preserved rather than guessed.

This is machine-assisted review, not native-speaker approval. No repository changes, tests, builds, scans, CI dispatches, workflow changes, releases, or tags were made by this cross-audit.
