# slskdN PR #409 W55 primary packet

## Exact head and boundary

- PR: https://github.com/snapetech-org/slskdN/pull/409 (open, draft)
- Branch: `codex/slskdn-oidc-tooltip-localization-20261030`
- Head: `6a46b8f1dc87d899308fee141fa0db392e49e098`
- Tree: `a22e9a896aae12aa89a1502d9748b12816d491ed`
- PR body SHA-256: `9ce6507c68b3ccfbb2b7ec78282951a449d04abecf8b35c8f15b4d2412985faa`
- W49 inventory SHA-256: `17cb8a747939d4973733016b95f29284e191d5444910051e42fb153cf4f94225`

W55 reviews W49 stable-ID ranks 276–300: 25 source IDs × 12 locales = 300 cells. W54 ended at rank 275 (`src_19d9e58cec9cd8fd`); W55 begins at rank 276 (`src_19dd83f117525b93`, “Yellow”) and ends at rank 300 (`src_1ab4cba1fe971008`). The next boundary is rank 301 (`src_1ab57bbe37fe439f`, “- {warning}”). Historical extraction ordinals are unavailable and are not claimed.

W49 reviewed IDs map to ranks 101–125. W50–W54 reviewed IDs map to ranks 151–275. W55 is disjoint from those reviewed IDs. The W49 gap 126–150 remains excluded and unreviewed. The packet confirms every selected row is unexcluded and not in W49, and maps all earlier selected IDs back to the pinned inventory.

## Primary review

- 194 accept-current
- 60 corrections
- 10 refinements
- 36 terminology holds
- 70 exact proposed changes across the 12 locales

Exact proposal winners and rationales are in `primary/review-decisions.jsonl` and `primary/review-summary.json`. The exact 36 holds are also listed there. They cover `Pod` in ranks 278 (“Publish or retrieve pod metadata through DHT workflows.”), 282 (“You need at least one pod with VPN gateway capability to use port forwarding.”), and 289 (“Please enter both Pod ID and Peer ID”), across all 12 locales. The callers identify the MediaCore Pod object, but the product glossary has no approved localized noun for Pod.

The rank 288 sample is comma-separated float input. Its production caller splits on ASCII commas and parses floats. Current decimal-comma and non-ASCII-comma examples were corrected to preserve that syntax. All candidate placeholder, markup, numeric-token, and protected-literal checks pass. The current values had 19 protected-literal mismatches and five numeric-token mismatches; the proposed winners resolve these.

## Scope and limits

This is a machine-assisted primary semantic review. It is not native-speaker approval or headed product-browser acceptance. No repository/catalog edits, PR edits, commits, pushes, project tests/builds/scans, CI, workflow edits, merges, releases, or tags were made. The exact-head worktree remains detached and clean.

## Artifacts

- `input/`: candidate-free exact-head input; packet manifest SHA-256 `4dcbdb679ced3a9211560682a5b8775af06aab9a06b1970179156d94e3cabfb0`.
- `primary/`: semantic ledger and summary; manifest SHA-256 `1e2d4fb9994e3062db945ea9698815770d34edf4ed064267673471f9756dc863`.
- `build_input.py` and `build_primary_review.py`: task-scoped packet builders.
- `SHA256SUMS.txt`: checksum manifest for the complete task packet.
