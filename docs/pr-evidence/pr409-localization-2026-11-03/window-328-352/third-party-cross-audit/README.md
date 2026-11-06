# slskdN PR #409 W58 third-party cross-audit

- Exact PR head: `47735fbdb8df3de8dc5fd297c2717dc332764431` (tree `b29397903a036d40af1c6551dedbe070e735cfed`); PR #409 was open draft when pinned.
- Scope: 25 source IDs × 12 locales = 300 cells, ranks 328–352.
- Candidate-free input: `/mnt/disks/scratch/task-scratch/slskdn-pr409-w58-ranks328-352-primary-20261103/input`; raw reviewer ledgers and SHA-256 pins are recorded in `provenance.json`.
- Caller evidence: 48 production caller occurrences across 25 source strings; zero callerless strings.
- Reviewer disagreements adjudicated: 48.
- Final: 242 accept-current, 36 corrections, 22 refinements, 0 holds; 58 selected targets differ from current.
- Placeholder, markup, number, edge-whitespace, protected-literal, and exact-head caller checks passed for all 300 cells.
- No native-speaker approval is claimed. No catalog/repo/PR/workflow changes or tests/builds/scans/CI were made.

## Per-rank disposition counts

| Rank | Accept current | Corrections | Refinements | Holds |
|---:|---:|---:|---:|---:|
| 328 | 11 | 1 | 0 | 0 |
| 329 | 3 | 6 | 3 | 0 |
| 330 | 12 | 0 | 0 | 0 |
| 331 | 10 | 2 | 0 | 0 |
| 332 | 10 | 0 | 2 | 0 |
| 333 | 12 | 0 | 0 | 0 |
| 334 | 10 | 2 | 0 | 0 |
| 335 | 9 | 2 | 1 | 0 |
| 336 | 0 | 4 | 8 | 0 |
| 337 | 12 | 0 | 0 | 0 |
| 338 | 12 | 0 | 0 | 0 |
| 339 | 12 | 0 | 0 | 0 |
| 340 | 12 | 0 | 0 | 0 |
| 341 | 12 | 0 | 0 | 0 |
| 342 | 10 | 1 | 1 | 0 |
| 343 | 2 | 6 | 4 | 0 |
| 344 | 12 | 0 | 0 | 0 |
| 345 | 12 | 0 | 0 | 0 |
| 346 | 2 | 9 | 1 | 0 |
| 347 | 12 | 0 | 0 | 0 |
| 348 | 8 | 2 | 2 | 0 |
| 349 | 12 | 0 | 0 | 0 |
| 350 | 12 | 0 | 0 | 0 |
| 351 | 11 | 1 | 0 | 0 |
| 352 | 12 | 0 | 0 | 0 |

## Files

- `reconciliation-ledger.jsonl`: one selected target per cell with source/current/reviewer hashes, third-party rationale, exact caller references, and checks.
- `provenance.json`: input SHA-256 pins and exact source tree.
- `summary.json`: machine-readable counts.
- `build_audit.py`: reproducible packet verifier/ledger builder.
- `SHA256SUMS.txt`: hashes of all deliverables above except itself.
