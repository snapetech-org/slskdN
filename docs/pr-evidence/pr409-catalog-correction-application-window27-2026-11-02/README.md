# Window 27 catalog correction application evidence

This bundle records 44 exact-hash corrections independently reviewed at PR #409 head `11e7971bc33513c7aad65f2831e1d474e541a5e0` / tree `97b609cdbf423f55d595a77220b7362b9fd3d8ef` / source subtree `ee5969020b2184b7a6179e8e7b9805041c782fb7`. Root accepted 30 targets as proposed and refined 14; none were held. The application commit is `3c25504c8c475ae40dab1acef2a85bdb37f1a620` / tree `349af6afff06f50d9583cecbe05847486affd15b`, a direct child of the review head.

The independent root ledger, exact apply plan, original 44-row proposal plan, and applied-row ledger are retained as separate artifacts. The application changed exactly 44 values across all twelve locale catalogs plus the cumulative CHANGELOG entry; it changed no other path. There were no uncertain cells in this window.

`verify_application.py` reconciles all 27 manual windows, earlier application/hold ledgers, the frozen baseline census, exact hashes and caller pins, formal-result overlap, workflow/source path boundaries, PR state, and this bundle’s checksums. After application, 1,114 values have changed across 265 source keys; six are held, 220 remain uncertain, and 58,980 cells remain unreviewed. Native-speaker and headed-browser reviews remain outstanding. No tests, builds, CI, releases, or tags were run.
