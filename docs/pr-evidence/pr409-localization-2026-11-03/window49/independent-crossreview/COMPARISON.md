# W49 independent cross-review comparison

Independent decisions were sealed before the primary review summary or per-cell decisions were opened. The sealed review covers reconstructed continuation ranks 101–125 (25 source IDs × 12 locales), with no historical source-ordinal claim.

## Reattestation

- PR #409 remained open and draft at exact head `a0f97a65f75df32a196338bea7a176b23b126cc4`, tree `a5cb30af29a947edbf76721bbc29b59e4330f970`.
- The independent pass verified all 300 source/current hashes, all 12 catalog file/blob/keyset pins (6,176 ordered keys each), and 39 caller references across 25 source contexts against exact-head repository text.
- The separate dated reattestation's hashes for the primary packet files and its SHA256 manifest matched.

## Comparison

- Primary dispositions: `accept-current` 209, `correction` 63, `refinement` 16, `hold` 12.
- Independent dispositions: `keep` 202, `revise` 86, `hold` 12.
- Normalized disposition agreement: 267/300; differences: 33.
- Candidate text: exact matches 209; different where primary supplied a candidate 79; primary candidate absent on all 12 held cells.
- Placeholder and markup results agree on all comparable cells. Candidate target hashes verify on both packets.
- The primary recorded 216 protected-literal checks, with 21 current-text failures and 0 candidate failures. The independent rank-105 cells remain held rather than approved.
- No native-speaker approval is claimed.

## Largest decision differences

- Rank 120, “Clear selected Library Health issues”: primary accepts all 12 current translations; the independent pass revises all 12 because the exact-head callback clears the selection set, while the tooltip says issue status is unchanged.
- Rank 122, DHT rendezvous: primary revises all 12 to spell out peer discovery; the independent pass retains all 12 current strings, with low confidence because exact technical terminology lacks an in-repository glossary.
- Rank 102: the independent pass revises Arabic, Indonesian, and Vietnamese to name similar music tracks; primary accepts the current strings in all locales.
- Rank 121: the independent pass revises Arabic, Indonesian, Vietnamese, and both Chinese variants for mesh-node wording; primary accepts all current strings.
- Rank 104: both passes revise all 12, but choose different graph/seed terminology in every locale.
- Rank 105: both passes hold all 12. The primary enumerates parser-literal preservation checks; the independent packet flags the unresolved parser-syntax boundary and keeps current strings only as unapproved references.

See `primary-comparison.json` for all 300 cell pairs, exact targets, hashes, dispositions, confidence/rationale text, and structural/literal checks.
