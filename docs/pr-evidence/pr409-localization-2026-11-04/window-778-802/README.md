# slskdN PR #409 W76 localization application

This packet covers continuation ranks 778–802 (remaining queue ranks 678–702): 25 source strings × 12 locales = 300 cells. The independent cross-review selected 69 exact catalog targets, retained 183 current values, and kept 48 callerless cells unchanged with text-free hash-only holds.

The application changes exactly 69 values across the 12 direct locale catalogs. Their 6,176-key sequences and all other catalog values remain unchanged. All 300 cells were read back by exact value and SHA-256; the 48 hold rows in application evidence omit source and target text.

`cross-review/` is the portable candidate-free, primary, blind, and independent cross-review packet, including per-cell rationale, proposal reconciliation, exact PR refs, hash-only hold lineage, verifiers, and checksums. `application/` contains the selected update plan, 300-cell readback, catalog preimages/postimages, and hash-only lineage.

## Semantic decisions

The `Jobs` navigation and `No jobs found` empty state refer to background tasks. `Minimum trusted taste sources` is a numeric threshold for preference-based recommendations; the exact caller is a number input bound to `minimumTrustedSources`, with the neighboring label `Minimum trusted sources`. `Route to Jurors` is a send action in the quarantine-jury interface. `Port Forwarding` is the network tunnel feature. `16 beats` is the musical MilkDrop setting. The Hindi local-tunnel tooltip preserves `localhost:{localPort}`.

## Verification and limits

The candidate-free, primary, blind, and cross packet verifiers passed at the exact W76 base head before application. After the PR head advanced, the offline cross-packet replay rechecked the sealed historical review and checksum chain. The application readback confirms 69 updates, 183 unchanged cells, and 48 text-free holds; `git diff --check` passed. `verify_bundle.py` rechecks the committed catalog preimages/postimages and all evidence checksums. Its optional `--base-checkout` argument reruns the offline cross-packet verifier against a clean checkout at the pinned W76 base head.

No tests, builds, scans, or CI jobs were run. `.github/workflows` was untouched. The PR remains open and draft; browser acceptance and qualified native-speaker signoff are not claimed. No merge, release, or tag was made.
