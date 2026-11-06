# slskdN PR #409 localization review — W67

W67 covers continuation ranks 553–577 (remaining queue ranks 453–477), 25 source strings, and 300 cells across the 12 direct locales. The exact review base is commit 2dc64b9d00f6611aeb72713af81db53ccc5a4084, tree f13462300926ac897235cd92ae68c87695c38c31.

## Reconciliation and application

The sealed primary, independent blind, and cross-audit packets are retained below this directory. The cross-audit reconciled 105 differing target hashes and selected 111 updates: 72 corrections and 39 refinements. It retained 189 current targets as no-ops and added no new holds. All 128 prior held values were reattested and retained unchanged.

All 111 selected targets were applied exactly to the 12 locale catalogs. The file catalog-readback.jsonl records all 300 post-application values. The file catalog-invariants.json records each catalog hash, Git blob, 6,176-key set and order, and changed-key list. No non-target values changed.

## Evidence

- candidate-free-input/: pinned source, caller, catalog, baseline, selection, and prior-hold evidence.
- primary-review/: sealed primary review and verifier.
- blind-review/: sealed candidate-free blind review and verifier.
- cross-audit/: all 300 primary/blind/final target hashes and adjudication reasons.
- application-plan.jsonl, no-op-ledger.jsonl, and hold-ledger.jsonl: exact updates, accepted current values, and retained prior holds.
- apply_catalogs.py: one-time surgical JSON value application.
- verify_application.py: portable readback, token, source/caller/catalog pin, prior-hold, non-target, and catalog key-order verifier. It uses this directory and the repository Git base commit; it does not need the original scratch paths or a live GitHub query.
- SHA256SUMS.txt: checksum list for this entire evidence directory.

Run from this directory:

    python3 verify_application.py
    sha256sum -c SHA256SUMS.txt

Exact-head browser and qualified native-speaker review were not performed. No project tests, builds, scans, CI, workflow changes, releases, tags, or merges were run or performed.
