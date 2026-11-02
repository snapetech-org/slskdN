# Window 31 exact-hash catalog corrections

Applied the 36 corrections independently accepted by root, with no refinements or holds. The application is commit `b38a95fb75ec4ac691ad02c4b2c7393f8a1389b7`, a direct child of reviewed PR head `fbafaae2e05af8ce51a263c7be2a92a8728ceb94`; tree `f2e7a734d60555964f0487377066a955308fd8c9`. The commit changes 36 locale values across 11 locale catalogs plus the cumulative `docs/CHANGELOG.md`; Spanish has no W31 cells.

Candidate-plan SHA-256: `320f88df56d7f9f1f1ec2fe20fab467235ab59471fe7812b63f8ba8979de5bba`. Root decision ledger SHA-256: `4e0809fcad3782ab73027cb22f2dea97ce18a3c891e91a7ad872a1ee74d67005`. Exact apply-plan SHA-256: `70067d1a6a13349d1d72db7227d3e79fae1757cc97e50e37330456d3121a64ca`. Applied-row ledger SHA-256: `2704474b3d89611ab953246fa99e3230a82e3214bf09ff707dda6bf5939011f7`.

The post-apply verification passed exact old/new target hashes, changed-cell sets, catalog key parity, and 74,028 placeholder checks. Cumulative reconciliation: 31 windows / 9,238 cells (7,706 keep, 1,264 correction decisions, 268 originally uncertain); 1,270 applied corrections across 290 source keys; six missing-context cells held; 12 Realm rows resolved by independent caller review; 256 uncertain cells and 57,842 unreviewed cells remain. All 4,800 formal cells remain disjoint from manual coverage.

The commit changes no source-code or workflow paths. Post-commit verification passed path scope, `git diff --check`, source-code and workflow subtree equality, and exact catalog hashes. PR #409 remains OPEN/DRAFT/CLEAN. Native-speaker and headed-browser review remain outstanding. No tests, builds, CI, releases, tags, or merges were run. The Semgrep hook was disabled for the single commit command as required outside private JIT; no local Semgrep run is claimed.

See the [window31 manual semantic review](../pr409-manual-semantic-review-2026-11-01/window31/README.md) for the input, dispositions, root cross-review, and caller pins.

The durable cumulative verifier passed at PR head `2d0434655973b42c1d2c43ead9572954da49a495`; its snapshot is `cumulative-verification.json` (SHA-256 `1afb6b732e6ccceaf3619f0df598329db2152d3462c11236feda26c5d5558028`). The exact-current post-push attestation is `post-push-verification.json` (SHA-256 `d39daf93cbc870cca13344281438a58065bcc9e7495a577d93ad2a45df98aba3`). The verifier script is included and can be rerun at a later clean PR head.
