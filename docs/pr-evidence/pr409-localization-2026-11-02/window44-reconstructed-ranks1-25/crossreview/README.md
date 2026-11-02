# slskdN PR #409 W44 independent cross-review

This read-only review covers the 25 reconstructed pending source IDs at selection ranks 1–25 across 12 locales: 300 cells. It reattests PR #409 as OPEN/DRAFT at head `f3fbd3f8db10f78768b9951a67b4b9de8581a408` and tree `9495c35a540ef2d2e845c833acb709365e0e26ac`. The PR branch matches the head, and the worktree is clean.

## Dispositions

- 241 current translations accepted.
- 15 primary corrections and 16 primary refinements accepted at their exact proposed hashes.
- 2 additional corrections and 2 additional refinements proposed after reviewing all 300 cells.
- 24 cells held: `pods` and `Private Message from {username}` remain without a production localization caller, across all 12 locales.

The four additional findings are:

- Rank 2 Arabic, `limited download history`: propose `سجل التنزيلات محدود`; the current `تاريخ التحميل المحدود` can read as a download date. The caller uses this as a search-ranking reason.
- Rank 17 Arabic, `Spectral bandwidth {bandwidth}kHz suggests {bitrate}kbps lossy source`: propose `يشير عرض النطاق الطيفي البالغ {bandwidth}kHz إلى مصدر صوتي مضغوط بفقدان البيانات بمعدل {bitrate}kbps.` The current `مصدر فاقد` is unclear for a lossy audio source.
- Rank 23 Indonesian, `Evidence: {evidence}`: propose `Bukti: {evidence}`. The current `Keterangan` means general information; this catalog uses `Bukti` for `Evidence` and evidence items.
- Rank 23 Brazilian Portuguese, `Evidence: {evidence}`: propose `Evidência: {evidence}`. This matches the catalog's `Evidence`, `No evidence supplied`, and evidence-item terminology better than `Prova`.

All four retain the exact source placeholders, markup, and protected literals. Exact target hashes, current-value hashes, caller references, and rationales are in `additional-findings.jsonl` and `cross-review-ledger.jsonl`.

## Reattestation and scope

The primary packet manifest SHA-256 is `4bc75c5111f8e4e6e650225e6e4b3e9cc62eb2f738adb0d8fe66e3dcfeeb2068`; all 18 entries verified. All 12 locale catalogs match the pinned tree and share the same ordered 6,170 source-key inventory. The review independently rebuilt the current pending IDs after excluding the 1,072 W1–W43 IDs, verified the first 25 sorted pending IDs, and retained rank labels because the historical W44 ordinal boundary is absent. No ordinal range was invented.

All 300 source/current/catalog hashes, 41 caller references, placeholders, markup, and protected literals passed readback. The 31 primary candidates had no no-op targets. The separate W98 hold readback confirms all 11 previously held rows and their caller composition remain unchanged and outstanding; they are not part of W44.

The cross-review has moderate confidence. Native-speaker approval and browser review remain outstanding. No repository or PR files were changed; no tests, builds, CI, browser work, releases, or tags were run.

## Files

- `cross-review-ledger.jsonl`: exact-hash disposition for every W44 cell.
- `additional-findings.jsonl`: four added target proposals with rationale and pins.
- `structural-caller-reattestation.jsonl`: per-cell source/current/caller and structural checks.
- `source-selection-reattestation.json`: catalog inventory, prior-ID exclusion, and reconstructed rank evidence.
- `w98-holds-reattestation.jsonl`: separate readback of the 11 outstanding W98 holds.
- `live-seven-pr-heads-start.json` and `live-seven-pr-heads-final.json`: fresh all-seven PR snapshots.
- `final-reattestation.json` and `cross-review-summary.json`: final state, counts, and checks.
- `build_crossreview.py` and `attest_live_heads.py`: reproducible read-only packet scripts.
- `SHA256SUMS.txt`: checksums for all packet files except this checksum manifest.
