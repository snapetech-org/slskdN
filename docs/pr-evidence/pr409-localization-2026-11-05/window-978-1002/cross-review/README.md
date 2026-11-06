# slskdN PR #409 W978–W1002 independent cross-review

This packet reconciles the 300 exact-head cells at `1c2fe3be2c720693cbcb12d377bf1177804f4e77` / tree `808501cbc3b6ed873a47d7188189d486f0673f5e` against the sealed candidate-free input and both supplied review passes. It does not modify the repository or locale catalogs.

## Coverage and result

- 25 source IDs × 12 locales = 300 cells.
- Primary: 89 corrections and 211 accept-current decisions.
- Blind: 60 proposals and 240 retains.
- Primary/blind comparison: 211 both retain, 28 exact-target agreements, 32 different-target conflicts, 29 primary-only proposals, and no blind-only proposals.
- Independent recommendation: 89 corrections and 211 accept-current decisions.
- 64 cells are flagged for root adjudication: every primary/blind disagreement, any independently adjusted exact target, and all baseline protected-literal mismatches.
- The five baseline protected-literal cases are recorded individually in `cross-review-summary.json`: Spotify `ID` in Arabic and Hindi; `CPU` in Arabic and French; and `QR` in Simplified Chinese.

Each ledger row records exact source, current target, source ID, caller-context, catalog file and Git blob hashes; caller path/line hashes and context; both prior decisions/targets/rationales; target-agreement class; independent target, rationale, confidence and token checks; and root-adjudication flags. Conflicting candidates are kept verbatim so the exact recommended alternative is reviewable. Chinese checked-count labels use the locale’s full-width colon in the recommendation.

## Verify

Run the packet-local verifier with the three source packet paths and exact-head worktree:

```sh
python3 verify_cross_review.py \
  --input-dir /mnt/disks/scratch/task-scratch/slskdn-pr409-w978-1002-20261105/candidate-free/input \
  --primary-dir /mnt/disks/scratch/task-scratch/slskdn-pr409-w978-1002-20261105/primary-review \
  --blind-dir /mnt/disks/scratch/task-scratch/slskdn-pr409-w978-1002-20261105-blind-review-independent \
  --repo-dir /home/keith/Documents/code/.task-worktrees/localization-20261105/slskdn-w978
```

The verifier checks this packet’s SHA256 inventory, all bound input packet file hashes, 300-cell identity and ordering, exact source/current/caller/catalog bindings, both review decisions, target-agreement counts, recommendation hashes and token preservation. With `--repo-dir`, it also runs the supplied candidate-free and primary exact-worktree verifiers plus the blind packet verifier. It runs no tests, builds, scans, or CI jobs.

## Limits

The cross-review is a semantic/context review, not native-speaker or browser signoff. The ledger recommends an exact target for every cell, flags conflicts and protected-literal repairs, and leaves root adjudication explicitly unperformed.
