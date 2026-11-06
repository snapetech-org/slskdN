# slskdN PR #409 W64 ranks 478–502 primary review

Independent primary semantic review of all 300 current locale cells at head 3cc9db334cfb1693dd6bd93bb83cfeba65930adb and tree 9d40e239e7e717a81bd176d143d1ce067fe026a1. The review uses only the sealed W64 candidate-free input; no blind or cross-audit material was consulted.

## Results

- Corrections: 74
- Refinements: 0
- Accept current: 214
- Callerless holds: 12 across rank 486 in all 12 locales
- Prior held cells outside this range reattested unchanged: 86 (72 earlier windows plus 14 W63 holds)
- Placeholder, markup, and numeric-token mismatches: 0
- Baseline protected-literal mismatches: 23, all reviewed. The 12 Wishlist misses are corrected by preserving exact Wishlist spelling. The 11 ACCEPT misses are intentionally localized status labels; the pinned caller routes ACCEPT through interfaceText. Unresolved protected/product-literal issues after review: 0.

Each ledger row includes the source and target hashes, current caller/catalog pins, selected target, disposition, rationale, and placeholder/markup/numeric/protected-token audit. The primary verifier checks every row against the candidate-free cells and exact window pins.

Run verify_primary.py and sha256sum -c SHA256SUMS.txt from this directory.
