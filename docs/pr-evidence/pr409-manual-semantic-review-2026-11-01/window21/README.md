# slskdN PR #409 manual semantic review: window 21

This exact-head evidence window reviews the next 25 eligible source keys (`src_f45aa5a5e4e25790` through `src_f59ab8d1331b7b16`): 300 cells across all twelve direct locales. It is pinned to OPEN/DRAFT PR head `a098c95c814a555454c11eaf2478ca5ae628a933`, tree `dedfcc3c93b1b3a67e7d582a9eeaa0df052ccf42`, and source tree `a50cd94b2bc8d0f09de0882600207a4b82293108`.

Verdicts: **247 keep, 29 high-confidence correction candidates, 24 uncertain**. Corrections address the Japanese descriptor-age unit, file-transfer cancellation terms in Chinese and Vietnamese, transcript-segment labels in Chinese, Wishlist-entry wording in Chinese, cryptographic-signing terminology in Chinese and Vietnamese, active-process status wording, Chinese message-registration errors and validity results, and recording-metadata terms in Chinese, Portuguese, and Vietnamese.

Two phrases remain uncertain in all locales. “Showing latest” is assembled with two counts and separate “of” and “messages…” fragments in English order, so natural target-language word order needs the full source sentence. The ListenBrainz listen-count string has no source callsite/context in the frozen snapshot, leaving the product-specific event term unconfirmed.

Per-locale counts (keep / correction / uncertain): es 22/1/2; zh-Hans 15/8/2; hi 22/1/2; de 23/0/2; ja 21/2/2; fr 23/0/2; pt-BR 21/2/2; ar 22/1/2; ko 21/2/2; zh-Hant 15/8/2; vi 20/3/2; id 22/1/2.

The exact-head preflight rebuilt eligibility from the frozen pending bundle, the formal accumulator (150 valid jobs / 4,800 cells), all 20 prior manual windows (6,000 cells), and the 818-row applied-correction ledger. It selected the next disjoint 25 keys; overlap with formal decisions, prior manual windows, and the correction ledger is zero. All 300 selected catalog values matched their frozen target hashes, and all available source callsite occurrences were reverified. Input SHA-256: `50eccb5239402dc25d2f27988f4541e90d66a3908e6273a204509542aa81d974`. Decisions SHA-256: `caab2a60a2023206004b09e0b2e16eb3d444d09d4cc57b3bb003a9829398906b`.

The adapted scratch verifier passed at the exact head/tree above. Its path and SHA-256 are recorded in `manifest.json`; the script is not copied here because it enforces the live PR head and prior-sibling state. The packaged JSON rows and verification result are byte-identical to scratch. This package is evidence-only: no catalog values were changed by this review. No model/API calls, tests, builds, or CI jobs ran. Native-speaker review remains outstanding.
