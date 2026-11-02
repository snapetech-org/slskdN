# slskdN PR #409 — W42 primary semantic review

- **Pinned input:** PR #409 was open/draft at head `1b518a69d099032c497149102751271eddb0fa57`, tree `c7f351a3507a3758a10369632feeb7a001e83aeb`.
- **Scope:** source ordinals 51–75 (25 keys); 275 non-Spanish cells across 11 catalogs.
- **Output:** read-only evidence. No repository or PR changes were made.
- **W41 reattestation:** all 275 W41 reviewed cells, 70 applied readbacks, 50 historic holds, and 25 W41 Spanish formal cells match the current catalogs with zero hash mismatches.
- **Preservation:** 25 Spanish formal-lane cells recorded without Spanish verdicts; all 50 prior held rows remain unchanged.
- **W42 verdicts:** 228 accept-current; 14 correction candidates; 33 refinement candidates; 0 W42 holds.
- **Prior exact reuse:** one French `Source` cell was reused after exact source and target hashes matched; see `prior-exact-reuse-reattestation.jsonl`.
- **Callers:** 41 exact caller references. `inbound links` has no direct caller in the frozen inventory, so its review is limited to standalone wording.
- **Validation:** all 12 catalogs have the same ordered 6,169-key set. Input/candidate hashes, placeholder, markup, protected-literal, and caller file/line checks are included. Candidate structural checks passed with zero mismatches.
- **Native-speaker review:** outstanding; machine-assisted review does not claim native-speaker approval.
- **Head movement:** PR head at completion was `1b518a69d099032c497149102751271eddb0fa57`. Reattestation required after head advance: `false.

Key files: `order-evidence.json`, `exact-head.json`, `catalog-attestation.json`, `source-slice.jsonl`, `review-input.jsonl`, `caller-attestation.jsonl`, `review-decisions.jsonl`, `correction-candidates.jsonl`, `w41-cell-reattestation.jsonl`, `preserved-prior-holds.jsonl`, and `preserved-spanish-formal.jsonl`. `SHA256SUMS.txt` covers the packet files except itself.
