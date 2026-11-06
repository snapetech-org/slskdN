# slskdN PR #409 W35 semantic review packet

This scratch-only packet freezes the next disjoint 25 source keys for a populated-catalog semantic review. It is pinned to live draft PR #409 at commit `917273260c49cca1c14576a0720fc84998d2846d`, tree `1cdd8c831d224a5706ac6f3e465add4fd249d2be`, and `src/web/src` subtree `594e56c3f439bad476b1bd57e0de1665c62fa1bb`.

## Scope and checks

- 25 source keys and 274 populated locale cells; 445 exact caller line references are pinned.
- The W35 window has zero exact-cell overlap with 4,800 formal cells, 10,052 prior manual-review cells across 847 source keys, and 1,373 already-applied correction rows.
- Current locale catalogs each have 6,169 keys. This selected window has 25 cells in zh-Hans, hi, ja, fr, pt-BR, ar, ko, zh-Hant, vi, and id; 24 in de; and none in es.
- Every source/current value, catalog file, caller file, line, placeholder, and protected literal is checked against the pinned commit.
- The row-level decision ledger covers all 274 cells: 38 correction candidates, 236 keeps, and no uncertain rows. `crossreview-plan.jsonl` contains only the correction candidates and is ready for root cross-review.
- The candidate suggestions are independent review proposals. No catalog or repository file was edited, and no target has been applied. Independent root cross-review and native-speaker review remain outstanding.

## Files

- `review-input.jsonl`: frozen source, current target, locale, caller, placeholder, and protected-literal evidence for each cell.
- `review-decisions.jsonl`: one exact-hash keep/correct disposition for each input cell.
- `crossreview-plan.jsonl`: 38 source/context/current/proposed rows for independent review.
- `uncertain-ledger.jsonl`: separate uncertainty ledger (empty for this window).
- `manifest.json`, `preflight.json`, and `freeze-summary.json`: exact PR/tree/catalog/caller pins, overlap accounting, and counts.
- `verification-report.json`: read-only exact-head, overlap, hash, caller, and packet verification.
- `freeze_window35.py`, `build_packets_window35.py`, and `verify_window35.py`: reproducible freeze, decision-packet, and verifier helpers. The freeze helper uses the already-frozen populated catalog audit; it does not modify the repository.
- `SHA256SUMS.txt`: checksums for the packet and helpers.

Run `python3 verify_window35.py` to recheck the live PR state, remote branch, exact commit/tree, historical overlap, catalog and caller pins, all row hashes, placeholders, protected literals, and packet counts. The checker only writes its report and checksums under this task-scratch directory.

No tests, builds, scans, CI, releases, tags, merges, workflow changes, or catalog edits were performed.
