# PR #409 populated-catalog manual semantic review — window 24

This window reviews the next 25 disjoint populated source keys across all twelve direct locales (300 catalog cells). It was frozen at PR head `805246b87e208cedcbdd0e2f33a83f912f4ad84b`, tree `4377ade660fa379731a41b54ba387c4eff2bcf32`, and source/catalog subtree `c3d06e298da7f7e04e69bee3c2596805a03d1e4b`. The selected ID range is `src_f854c1a24ec09075` through `src_f979c57727a12999`.

## Results

- Verdicts: 255 keep, 45 high-confidence correction decisions, 0 uncertain.
- The 45-cell proposal plan is `proposal-plan.jsonl` (SHA-256 `a32015312fd7bb99e8428bbc0d42e0d5e5794c9f06d29203d4c03dadf531cfce`).
- The root’s separate exact-hash cross-review accepted 43 proposals as written and refined 2 before acceptance: Arabic `إعداد الظهور` and Vietnamese `chế độ hiển thị` for the visibility-setting/mode labels. The independent ledger and exact application plan are retained in the [window24 application bundle](../../pr409-catalog-correction-application-window24-2026-11-02/).
- The per-locale keep/correction counts are es 19/6, zh-Hans 21/4, hi 23/2, de 22/3, ja 21/4, fr 22/3, pt-BR 21/4, ar 21/4, ko 21/4, zh-Hant 21/4, vi 20/5, id 23/2.

## Verification and provenance

The review verifier checked exact source/catalog joins and hashes, placeholders/protected literals, caller pins, the corrected Repeat source binding (`src_f917fbdfc928a17f`), 23 prior manual windows, 934 previously applied cells, and the 4,800-cell formal accumulator with zero overlap. Its frozen input and decision checksums are recorded in `manifest.json` and `verification.json`.

An earlier draft proposal-to-source mapping error was detected before any application. That draft was superseded and is excluded from this evidence package. The corrected proposal plan is preserved separately from the root cross-review ledger and exact-hash apply plan.

The catalog targets were applied later in commit `00ee3b76686a3b4cdafd4d9a24a02342d5f36bb2`; application evidence and exact post-application verification are in the linked bundle. Semantic confidence is high, locale-quality confidence is moderate, and qualified native-speaker review remains outstanding.
