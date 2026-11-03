# Independent blind semantic review — slskdN PR #409 W61

- Pinned PR head: `0e2fc80bea8abfb02ebf13817bcef4e3ddeb4169` (tree `fad129065c1ccbdaaabe99c1054649dc426ea94b`).
- Selection: ranks 403–427, 25 source keys × 12 locales = 300 cells.
- Every selected key has at least one pinned production caller. The rank 409 hold is due to insufficient semantic context for “Wanted pull,” not missing callers.
- Decisions: accept-current 237, correction 41, refinement 10, hold 12.
- Placeholder, markup, and numeric-token preservation checks passed for all 300 cells; candidate-free packet reports no embedded candidates.
- Rank 409: all 12 locale cells held. The caller only checks `supportsWantedPull` and confirms no Servarr action ran; it does not define the direction or UI meaning of “Wanted pull.”
- Candidate-free manifest SHA-256: `3d05538d9b4df6944add79c4fbedcaa90c93af5da7f439ebcbd55b346b8c6903`.
- Candidate-free checksum-list SHA-256: `418735698e3e789a8c14005d531980631980bdccb993fe9ae669b65735e4ace7`.
- This blind review was generated from the candidate-free packet only; no primary review decisions were opened or used.

All per-cell source/current hashes, catalog pins, caller paths/lines/context hashes, token checks, recommendations, and rationales are recorded in `blind-ledger.jsonl`.
