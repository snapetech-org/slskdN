# slskdN PR #409 W69 cross-audit

Independent exact-head cross-audit of continuation ranks 603–627 for PR #409.

## Pin and coverage

- PR state at both snapshots: OPEN and DRAFT.
- Branch: codex/slskdn-oidc-tooltip-localization-20261030
- Head/tree: 9ef252a53d2c14201c736de41efd0531bc00965a / becf17f8be3f3251691002dbce487c1e94693e63
- Coverage: 25 sources × 12 locales = 300 cells.
- W68 ends at rank 602; W69 starts at 603 and ends at 627; the next unselected rank is 628.
- The evidence directory contains complete W69 candidate-free, primary, and blind packets; W68 lineage packets; the pinned source inventory; and raw catalog/caller files used to verify current values and caller references.

## Adjudication

- Reviews agreed on the exact target hash for 224 cells: 220 current targets and 4 shared changes.
- Reviews disagreed on 76 target hashes: 49 blind-only changes, 14 primary-only changes, and 13 cells where both changed to different values.
- Dispositions differed on 64 cells. The primary ledger records reviewed target hashes without proposal text; this audit preserves those hashes and selects a visible blind/current value or two explicit Chinese tab corrections.
- Final selections: 220 accept-current, 34 corrections, 34 refinements, and 12 holds.
- Rank 615 remains held in all 12 locales because the pinned production caller scan found no caller.
- The pinned caller establishes that rank 611 describes native Soulseek interest lists. The primary's blanket removal of “native” is unsupported by the caller; this audit keeps current translations except correcting French “autochtones” and Chinese “本机” to native-interest wording.
- The two rank 612 baseline literal omissions (Arabic and Hindi) are corrected with exact ID; the rank 619 Hindi omission is corrected with exact SongID. These remain caller-backed corrections.
- Prior 128 holds were reattested unchanged across W68 and W69.

## Verification

Run python3 verify_cross_audit.py from this directory. It checks packet manifests/checksums, pinned raw source hashes and Git blob IDs, caller lines/contexts, catalog values, boundaries, both review ledgers, selected hashes and token rules, prior holds, and the before/after live-state attestations. SHA256SUMS.txt seals the full portable packet.

This audit did not modify the repository or PR. No tests, builds, scans, CI, browser review, or native-speaker review were performed. Confidence is high for pins, checksums, caller evidence, and token checks; moderate for linguistic adjudication.
