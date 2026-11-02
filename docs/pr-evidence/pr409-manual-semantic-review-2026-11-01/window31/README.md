# Window 31 exact-hash semantic review

Window 31 reviewed the next 25 pending source keys after cell-level exclusion of formal and prior manual coverage. It contains 274 pending cells across 11 locales; Spanish cells for these keys already had formal or reusable exact decisions and were excluded. All 274 cells received a manual semantic disposition: 238 keep, 36 correction candidates, and 0 uncertain.

The exact review pin is PR #409 head `fbafaae2e05af8ce51a263c7be2a92a8728ceb94`, tree `ee4d11c5cf5b3c1053fcbdafff69dee9d2cb09d9`, source subtree `150c9fc80ce9a8f491926aa25f4397a12c8efc73`. Input SHA-256: `d5017efef0c3e063458c6271bb4b27d40b35bdf91cd8379e598648e9bfd0c1be`; decision ledger: `5395a5a3e2d205db02560c351a98bbee6420a5b845f6d35a1e5088b0e55840be`; proposal plan: `320f88df56d7f9f1f1ec2fe20fab467235ab59471fe7812b63f8ba8979de5bba`.

Independent root cross-review accepted all 36 targets as proposed, with 0 refinements and 0 holds. Root ledger SHA-256: `4e0809fcad3782ab73027cb22f2dea97ce18a3c891e91a7ad872a1ee74d67005`. The independent cross-review and candidate packet joined exact source, current-target, caller, and catalog hashes at the pinned head. The candidate verifier passed: 4,800 formal cells, 8,964 prior manual cells, zero overlap, 478 caller lines rechecked, and placeholder/protected-literal checks passed.

The 36 proposals fix the browser-local authority status, the native visualizer's uncapped Full preset label, the contextual `For:` evidence heading, Pod subsystem naming, event-retention wording, and Indonesian room/API clause order. Semantic confidence is high for the flagged errors; locale-quality confidence is moderate. No translation-model/API calls were made. Native-speaker approval remains outstanding.

The 36 accepted corrections were applied in commit `b38a95fb75ec4ac691ad02c4b2c7393f8a1389b7`. See the [window31 application evidence](../../pr409-catalog-correction-application-window31-2026-11-02/README.md). No source or workflow files changed.
