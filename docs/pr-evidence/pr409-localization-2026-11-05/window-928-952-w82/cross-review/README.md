# slskdN PR #409 W82 cross-review

This cross-review reconciles the candidate-free, primary, and blind packets for continuation ranks 928–952 at head `6e48a342d4b1c43918c23da3afcbaad19c87a005`, tree `b82ea7937cf9aa141a1c952283d5549dbe116ba5`. The window covers 25 source IDs × 12 direct locales (300 cells). All three input checksum lists, exact anchors, and 300-cell matrices were verified before review.

## Dispositions

- 251 cells: accept current value.
- 30 cells: correction.
- 4 cells: refinement.
- 15 cells: hold.

Thirty-four primary proposals were selected. They restore exact technical literals (`JWT`, `soulfind`, and `PodCore`), correct the Arabic queue-position and viewed-action meanings, and address the reviewed setting, button, status, and section-label wording. Rank 950 remains held in German, French, and Hindi for qualified language review. Rank 944 remains held in all 12 locales because the pinned source has no production caller; its source and target texts are omitted from this packet.

The blind audit identified 17 protected-literal mismatches plus one additional semantic issue where Arabic contained an unsupported `com.` prefix before `soulfind`. These affect 18 cells: JWT in three locales, soulfind in 12 locales, and PodCore in three locales. Placeholder, markup, and numeric-token checks report no mismatch across the 300-cell matrix.

## Evidence

- `cross-ledger.jsonl` binds every row to source, current-target, caller-context, primary, and blind hashes. It contains selected target text only for the 34 approved proposals. Held rows are text-free.
- `cross-review-summary.json` records exact counts, anchors, token findings, and limitations.
- `build_cross_review.py` rebuilds the ledger and summary from the candidate-free, primary, and blind packets.
- `verify_cross_review.py` verifies packet checksums, matrix coverage, anchors, dispositions, hashes, text-free holds, and output seals.
- `SHA256SUMS.txt` seals this packet.

Run the verifier with Python 3:

```sh
python3 verify_cross_review.py \
  --candidate-free /path/to/candidate-free/input \
  --primary /path/to/primary-review \
  --blind /path/to/blind-review \
  --output /path/to/cross-review
```

This is machine semantic review at moderate confidence; it is not native-speaker, browser, or app-runtime approval. No catalog/source/PR edit, test, build, scan, CI run, workflow change, merge, release, or tag occurred as part of this review. Root adjudication remains the next step before applying any selected values.
