# slskdN PR #409 populated-catalog semantic review

## Exact-head status — 2026-11-01

- PR #409 remains open and draft. The audited source/catalog snapshot is head `4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb`, tree `0eb84397dc2b4be4afd730f6818203bd5910cf15`. Subsequent commits in this workstream contain review evidence/docs only.
- Frozen preexisting-catalog backlog: 67,080 cells. The formal result ledger has 150 valid jobs (4,800 cells), 1,951 missing jobs, and zero invalid jobs.
- Two independent manual slices cover 50 source keys / 600 cells across the 12 direct locales. Combined verdicts: 488 keep, 84 correction-needed, and 28 uncertain. These manual decisions are separate from the formal result ledger and have not been applied to catalogs.
- Qualified native-speaker review remains required.

## Window 1

The first 25-key slice covers 300 cells: 267 keep and 33 corrections. Corrections address Arabic/Vietnamese Pod entity terminology, the Light theme label, Arabic “None” meaning nobody, Share List noun labels, and Transports Up meaning available transports rather than direction. The verifier confirmed exact source rows, pending status, no prior-result overlap, placeholder integrity, exact head/tree, and checksums.

Evidence: [`window1`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window1/). Manifest SHA-256 `30bc07c74d23d823c441811a559eb9a4677bc9304e6b5183d4b9cf71a229cb4e`; input `11b7d401023abe47fda7255d0b6158231e93ecc9feb4fdebea323b7480c44bf2`; decisions `2914f53ec1e807edaeb033deefa81661a5133c1da9b269704971e87c79c1dcb6`.

## Window 2

The next 25-key slice covers another 300 cells: 221 keep, 51 corrections, and 28 uncertain. Clear corrections address network-peer terminology, vocal-cancellation meaning, a software feature gate mistranslated as a physical gate, channel loading, the keyboard Enter key name, View actions, an adversarial-resilience heading, and membership-info retrieval errors. Uncertain items are Configured import success, the Realm subject-index field, and locale-specific Tor BridgeLines wording in zh-Hans, zh-Hant, vi, and id.

Evidence: [`window2`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window2/). Manifest SHA-256 `32a567b651ced306e08287b731585f29f1c953e475a3f57da700a929855bb2fa`; input `c8507f897140d5c9bbd38cd8b238228407541c971822ff55c55415242fc25af9`; decisions `965201e7bb42959fd262f22eb1132db8cdb6558c9f1f5e1cea0bb31697677d3d`.

No catalogs, source, formal shared ledger, tests, builds, or CI were changed or run by these evidence slices. The PR branch changes introduced to retain these results are documentation/evidence only.
