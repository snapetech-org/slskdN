# slskdN PR #409 manual semantic review: window 19

This exact-head evidence window reviews the next 25 eligible source keys (`src_f25ebda399d5624d` through `src_f34f5b18ffbe66dd`): 300 cells across all twelve direct locales. It is pinned to OPEN/DRAFT PR head `4ebd4591994ee709051156df9c9d42160da0b165`, tree `89658bbd1e5ae93080d8fd61ef71beea811e99a2`, and source tree `b5a776a81982ebde32163f06d47c57fc79e40ad9`.

Verdicts: **243 keep, 57 high-confidence correction candidates, 0 uncertain**. The findings cover peer-identity wording, incoming file-share pagination, diagnostic-bundle terminology, rate-limit window units, MilkDrop frame-rate caps, album release dates, Lidarr URL/API-key wording, the French Pod entity name, and a Hindi spelling error. All proposed targets preserve placeholders and protected literals.

Per-locale counts (keep / correction / uncertain): es 21/4/0; zh-Hans 19/6/0; hi 19/6/0; de 21/4/0; ja 22/3/0; fr 21/4/0; pt-BR 21/4/0; ar 20/5/0; ko 21/4/0; zh-Hant 19/6/0; vi 20/5/0; id 19/6/0.

The exact-head preflight rebuilt eligibility from the frozen pending bundle, the formal accumulator (150 valid jobs / 4,800 cells), and all 18 prior manual windows (5,400 cells). It found 297 eligible all-locale keys before selection, selected the next disjoint 25, and found zero overlap with formal decisions, previous manual windows, or the 736-row applied-correction ledger. All 300 selected catalog values and 444 source callsite occurrences matched their pinned hashes. Input SHA-256: `675a23d87cb111538504af36d39cb5b6efe395248503c4f5165c53b29aa3cf8a`. Decisions SHA-256: `5074f55c96eef5782e9d002676fc6214902baf207fbedf837b932d58c53c2fee`.

The adapted scratch verifier passed against this exact live head/tree. Its path and checksum are in `manifest.json`; it is not copied here because it enforces exact live-head equality. This package is evidence-only: catalog values were not changed by this review. No model/API calls, tests, builds, or CI jobs ran. Native-speaker review remains outstanding.
