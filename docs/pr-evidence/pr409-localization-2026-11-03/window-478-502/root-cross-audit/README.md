Independent root cross-audit for slskdN PR #409 W64 ranks 478–502.

The sealed candidate-free, primary, and blind packets are reconciled against the exact pre-application head 3cc9db334cfb1693dd6bd93bb83cfeba65930adb / tree 9d40e239e7e717a81bd176d143d1ce067fe026a1. The PR now points to 1d45cb002e206b0f611e27d3a17f4663aefc6eb7 / tree dec2f192c0dce1c8eb1c6caab35cb29fb1c5005d; that single application commit has 3cc9db334cfb1693dd6bd93bb83cfeba65930adb as its parent. Branch and pull refs match the current head.

All 300 cells are independently dispositioned. The primary and blind target texts differ in 79 cells; their dispositions differ in 53 rows. The audit records every disagreement in disagreements.jsonl. Root dispositions: 202 accept-current, 76 corrections, 10 refinements, and 12 holds. All 86 applied target changes match the selected root targets; all 12 locale values at callerless rank 486 remain held. The 86 earlier held cells are reattested unchanged.

Candidate-free manifest JSON SHA-256: 4f428c69b3abec8db8ad9d7796f5c9a6e9e6da9234361cc644721b932de05456. Candidate-free packet checksum-list SHA-256: 2064eb36dcd2bc27344f73c57b62e8e3078d087da115fe04d52348a30855e5c8. Primary checksum-list SHA-256: 0cce03a378a71f9250586c8d99005ab3bc7a78c9d112739698f6f0123bfa2139. Blind checksum-list SHA-256: 9525a2322f1ab0c820d0abbade8ad302a9d5f2dc87725b9ffad194095f68ec30. The manifest and checksum-list hashes are kept separate. Current applied catalogs were read from the exact current PR head and their 300 target values are in applied-current-readback.jsonl.

The input recorded 23 baseline protected-literal mismatches. The root targets restore the 12 Wishlist literals. The 11 localized ACCEPT values are a justified exception: the exact caller passes ACCEPT/REJECT through interfaceText in a human-readable report. Placeholder, markup, numeric, and unresolved protected-literal mismatches are zero.

This is a read-only audit; it makes no source catalog or PR-body changes. Native-speaker and browser signoff remain false.

The prior W64 PR-body section reported 79 corrections and 7 refinements. This independent audit classifies the same 86 applied target values as 76 corrections and 10 refinements. This is a disposition-label difference only: all 86 changed targets match exactly, all other 214 cells match their current value or hold. The follow-up PR-body note records the corrected classification. The portable verifier checks immutable Git objects and sibling packets; it does not read a live PR body or mutable ref.
