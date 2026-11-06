# slskdN PR #409 W40 exact-hash review and application

W40 covers 25 source IDs across 11 non-Spanish locales, plus 25 Spanish formal-lane preservation cells and 50 prior holds. The primary packet is pinned to `67e40aaa5b89db51397953dc89730316b1ab8bbc` / `7a8d85f9b967893d386bf5679ef0b46322307983`; the independent reviewer rechecked the exact live PR head/tree and all 350 rows.

The independent review accepted all 63 primary proposals (44 corrections and 19 refinements), accepted 212 current values, preserved all 25 Spanish formal-lane cells and all 50 holds. It reattested 12 catalogs, 25 source rows, and 38 caller line pins; placeholder, markup, and protected-literal checks passed. Three held cells still have exact callers and remain held pending terminology review.

Applied 63 exact-hash changes across 11 locale catalogs. The application plan records each before/after target and both review dispositions. Readback verifies every target hash, and all twelve locale files retain 6,169 ordered keys. The original primary and cross-review packets, including checksums, are retained in `primary/` and `cross-review/`.

Native-speaker review remains outstanding. No tests, builds, scans, CI, browser review, workflows, releases, tags, or merges were run or changed for this window.
