# W55 third-party cross-audit worksheet

Exact head/tree: `6a46b8f1dc87d899308fee141fa0db392e49e098` / `a22e9a896aae12aa89a1502d9748b12816d491ed`.
Candidate-free input SHA-256: `4dcbdb679ced3a9211560682a5b8775af06aab9a06b1970179156d94e3cabfb0`.
Primary vs blind: 15 disagreement cells; 15 candidate-text disagreements; 2 disposition disagreements. All reconciled.

Cross dispositions: {'accept-current': 193, 'refinement': 12, 'hold-terminology': 36, 'correction': 59}; exact candidate changes: 71; holds: 36.

## Main disagreements

- Rank 279 Arabic: use `الفحوصات:` as the concise readiness-check heading; classify as refinement.
- Rank 283: use each locale’s pinned translation of the standalone `Wishlist` source key in the Lidarr setting string. See `localized-term-adjudications.jsonl`.
- Rank 287 Japanese: use the sentence-style `示唆します` form; preserve DR and `{range}`.
- Rank 288 Japanese: keep the exact ASCII comma-separated sample and use natural Japanese parentheses.
- Rank 290 Spanish: use `Detenido` for the current stopped health state; classify as refinement.

## Holds

Both ledgers hold the same three Pod-term sources in all 12 locales: ranks 278, 282, and 289. The 36 current values remain unchanged pending an approved localized product term.

## Checks

All 300 primary and blind rows map exactly to input source/current/catalog/caller pins. All 40 caller references match exact-head file, line, and context hashes. Candidate placeholder, markup, numeric, and protected-literal checks pass for both ledgers and the reconciled candidate set.
