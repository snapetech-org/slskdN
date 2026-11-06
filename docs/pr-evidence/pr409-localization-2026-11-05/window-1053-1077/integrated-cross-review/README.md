# slskdN PR #409 W1053-W1077 integrated cross-review

Pinned product head/tree: ba692c15ca54942108cc9da37757f585969e6173 / 27c09a8fe24030f5bb0995d809794a9e4829dc64.

The packet integrates all 300 cells in the 12-locale window: 54 revised targets, 214 retained current targets, 8 low-confidence review holds, and 24 callerless hash-only holds. It records the exact primary proposal and blind target alongside the selected target for each caller-backed cell, with source/caller hashes and token audit. The 24 callerless rows expose hashes only.

The 31 blind revisions were accepted after source/caller review. Of the 28 primary-only revisions, 23 were accepted, four were rejected as non-material or unsupported terminology changes, and one Arabic gender-agreement proposal remains held for review. Four primary revisions within blind-review flags also remain held. Three further blind-review holds plus that Arabic cell yield eight unresolved low-confidence cells; their ranks/locales and exact current/candidate targets are listed in unresolved-low-confidence-cells.jsonl.

The source/current-cell file, exact caller contexts, the 24 callerless holds, all 433 prior active holds, and prior hash-only hold-resolution history are retained from the sealed candidate-free input. The 24 callerless hold file and 433 prior active-hold file were also byte-compared with both primary and independent blind packets.

## Verification

Run python3 -B verify_integrated_cross.py from this directory. The verifier checks every input file checksum, all 300 row identities and exact proposal/caller pins, source/current/target hashes, token and protected-literal integrity, all hold lineage, and output checksum coverage.

INPUT_SHA256SUMS.txt inventories every file in the three input packets. SHA256SUMS.txt covers every regular file in this output packet except itself. The output checksum-list digest is reported with the verifier result.

No repository, PR, product files, tests, builds, scans, or CI were changed or run. These proposals and decisions are machine-reviewed and are not native-speaker-approved.
