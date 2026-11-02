# slskdN W34 semantic review packet

W34 freezes the next 25 uncovered source keys for PR #409. Review pins:

- PR head: `dc8ed2406a2247600d487df1ae3128ce08cc7faa`
- Tree: `9909f5d6e32dfcc78ba53aa0c838f95e9ba246d3`
- Caller subtree `src/web/src`: `594e56c3f439bad476b1bd57e0de1665c62fa1bb`
- Live PR state at freeze: open, draft, merge state clean

The frozen input has 274 locale cells across 25 source keys. There are pending cells in 11 locales; Spanish is included in the 12-locale disjointness check but has no pending cells in this window. All 514 exact caller lines, caller file hashes, current catalog values, and source/current hashes were checked against the pinned PR commit. W34 has no overlap with the 9,778 prior manual cells / 822 source keys, the 4,800 formal cells, or 1,340 applied correction rows.

Manual review disposition:

- 33 correction candidates
- 240 keep
- 1 held cell: French “Slots, speed ceilings, auto-replace, and schedule enablement.” The caller is a transfer-policy summary; the exact French term for transfer/concurrency slots needs terminology review.

`crossreview-plan.jsonl` contains all source/current/proposed hashes, exact English caller contexts and file pins, placeholder/protected-literal checks, and exact PR/catalog pins for each candidate. `uncertain-ledger.jsonl` is a separate, complete record of the held cell. `review-decisions.jsonl` covers all 274 cells. The separate read-only validator checks the live PR and remote head, historical window disjointness, all caller/catalog pins and hashes, candidate and uncertainty coverage, placeholders, protected literals, and packet counts.

No repository or catalog files were changed. No tests, builds, scans, CI, or translation API/model calls were run. Native-speaker review and root cross-review remain outstanding; no candidates have been applied.

Run `python3 verify_window34.py` to recheck the packet against the pinned PR object and live PR state. `SHA256SUMS.txt` covers the frozen inputs, decisions, candidate and uncertain ledgers, summaries, verification report, README, and helper scripts.
