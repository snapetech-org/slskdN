# Cross-audit package

`cross-audit-ledger.jsonl` reconciles all 300 W59 cells. `summary.json` gives disposition and validation totals. `disagreement-and-hold-summary.json` lists every primary/blind disagreement and each of the 24 callerless held cells. `attestation.json` records exact-head pins and the source packet manifests. `supplemental-catalog-context.json` records exact-head locale-key evidence used for the peer, Messages, and Wishlist wording decisions.

`verify_cross_audit_evidence.py --repo /path/to/slskdN` verifies the audit package and reads the current values from the exact pinned Git tree. The independent blind review, primary ledger, and candidate-free input are separate packet artifacts under task scratch; their manifest hashes are recorded in the attestation. This audit is not native-speaker approval and does not approve a release.
