# slskdN PR #409 W67 independent cross-audit

This cross-audit reconciles the sealed primary review and independent blind review for ranks 553–577. It checks all 300 locale cells across 25 sources and all 128 carried holds against the candidate-free pinned input.

## Reconciliation

- The two reviews agree on 186 exact current-target hashes and 9 exact non-current proposal hashes.
- They disagree on 105 target hashes. Each disagreement is adjudicated in cross-audit-ledger.jsonl; the selected source and reason are recorded per cell.
- proposal-hashes.tsv records primary, blind, and selected final hashes for all 300 cells. final-proposal-hashes.txt provides the selected final hash for each cell.
- prior-held-cell-reattestation.jsonl records the 128 unchanged prior holds by exact hashes and current source/caller/catalog pins. Held target text is omitted.

## Pins and validation

The PR head, tree, branch, and pull refs were checked before the audit and are recorded in live-ref-start.json. A second live check is recorded in live-ref-seal.json immediately before sealing. Run python3 verify_cross_audit.py and sha256sum -c SHA256SUMS.txt to verify this packet.

## Scope

This packet is an independent reconciliation of primary and blind machine-assisted review. Existing current targets were present in the candidate-free input. Native-speaker and headed-browser review were not performed. No repository or PR files were edited; no project tests, builds, CI, releases, or merges were run.
