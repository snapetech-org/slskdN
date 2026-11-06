# slskdN PR #409 W44 reconstructed ranking slice

The primary selection is reconstructed from current pending IDs because the historical W44 ordinal boundary and W40 frozen queue are unavailable. This packet covers ranks 1–25 and makes no claim that those ranks are the original W44 source ordinals.

Primary review, independent cross-review, and separate adjudication cover 300 cells (25 source IDs × 12 locales). The cross-review accepted 15 primary corrections and 16 primary refinements, proposed two additional Arabic corrections and two evidence-label refinements, and retained 24 caller-gap cells. Third-party adjudication accepted all four additional proposals. Application changed 35 catalog values and read back all 300 targets.

The 24 held values remain unchanged because `pods` and `Private Message from {username}` have no production localization caller. The separate 11 W98 holds were reattested and remain outstanding. All twelve catalogs retain the same key set; placeholder, markup, and protected-literal checks passed. The cross-review reattested 41 caller references.

The full primary, cross-review, and adjudication packets are preserved with their original checksum manifests. `application/` records pre-apply catalog pins, the 300-cell plan, exact readback, and post-apply catalog attestations.

This is machine-assisted review, not qualified native-speaker approval. Browser review was not performed here; verify exact-SHA deployment state before headed review. No tests, builds, scans, CI dispatches, workflow edits, merges, releases, or tags were made.

The repository's local pre-commit and pre-push hooks invoke security scans outside the private-JIT route, so they were not run for this commit/push.
