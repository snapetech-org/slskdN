# slskdN PR #409 populated-catalog semantic review

## Exact-head status — 2026-11-01

- PR #409 remains open and draft. The audited source/catalog snapshot is head `4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb`, tree `0eb84397dc2b4be4afd730f6818203bd5910cf15`. Subsequent commits in this workstream contain review evidence/docs only.
- Frozen preexisting-catalog backlog: 67,080 cells. The formal result ledger has 150 valid jobs (4,800 cells), 1,951 missing jobs, and zero invalid jobs.
- Four independent manual slices cover 100 source keys / 1,200 cells across the 12 direct locales. Combined verdicts: 983 keep, 176 high-confidence correction candidates, and 41 uncertain. These evidence-only decisions are separate from the formal result ledger; no corrections have been applied to catalogs.
- Qualified native-speaker review remains required.

## Window 1

The first 25-key slice covers 300 cells: 267 keep and 33 corrections. Corrections address Arabic/Vietnamese Pod entity terminology, the Light theme label, Arabic “None” meaning nobody, Share List noun labels, and Transports Up meaning available transports rather than direction. The verifier confirmed exact source rows, pending status, no prior-result overlap, placeholder integrity, exact head/tree, and checksums.

Evidence: [`window1`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window1/). Manifest SHA-256 `30bc07c74d23d823c441811a559eb9a4677bc9304e6b5183d4b9cf71a229cb4e`; input `11b7d401023abe47fda7255d0b6158231e93ecc9feb4fdebea323b7480c44bf2`; decisions `2914f53ec1e807edaeb033deefa81661a5133c1da9b269704971e87c79c1dcb6`.

## Window 2

The next 25-key slice covers another 300 cells: 221 keep, 51 corrections, and 28 uncertain. Clear corrections address network-peer terminology, vocal-cancellation meaning, a software feature gate mistranslated as a physical gate, channel loading, the keyboard Enter key name, View actions, an adversarial-resilience heading, and membership-info retrieval errors. Uncertain items are Configured import success, the Realm subject-index field, and locale-specific Tor BridgeLines wording in zh-Hans, zh-Hant, vi, and id.

Evidence: [`window2`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window2/). Manifest SHA-256 `32a567b651ced306e08287b731585f29f1c953e475a3f57da700a929855bb2fa`; input `c8507f897140d5c9bbd38cd8b238228407541c971822ff55c55415242fc25af9`; decisions `965201e7bb42959fd262f22eb1132db8cdb6558c9f1f5e1cea0bb31697677d3d`.

## Window 3

The third 25-key slice covers another 300 cells: 233 keep, 66 high-confidence corrections, and 1 uncertain. The corrections address music-scene terminology, usernames, forensics, history backfill, audio analysis, channel controls, Soulseek interests, queued tracks, type labels, Arabic Pod terminology, paths, pipeline stages, and a Korean contact label. One Hindi Backfill label remains uncertain. The evidence verifier passed against the formal ledger and both earlier windows; the PR copy records why its verifier script remains only in scratch.

Evidence: [`window3`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window3/). Manifest SHA-256 `ae814abc687882d941082139eb039ef7bae053b05f839dc8550cc8c8a06d70b9`; input `82c267214443adddd832221240762f4fc3d178ec39639e7d4dce250eca0aeb87`; decisions `4720deeaf0598e20d974701b65e9c9b1712c7740bdd11d8c6d2a452b1fe54d2c`.

No catalogs, source, formal shared ledger, tests, builds, or CI were changed or run by these evidence slices. The PR branch changes introduced to retain these results are documentation/evidence only.

## Window 4

The fourth disjoint 25-key slice covers 300 cells: 262 keep, 26 high-confidence corrections, and 12 uncertain. Corrections address the native MilkDrop frame-rate limit, caution wording in Chinese, Spanish readiness, rank order in Chinese and Arabic, Arabic directory counts and Webhook policy terminology, an Arabic close-radio instruction, and five modal-dialog tooltips. “Playing” remains uncertain in all 12 locales because the frozen source lacks callsite and surrounding context. The scratch verifier confirmed zero formal overlap and zero overlap with the three earlier manual windows; the PR package omits the sibling-sensitive verifier and records that packaging provenance in its README.

Evidence: [`window4`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window4/). Manifest SHA-256 `ea5d19ea1afe85ab17be9d559592e38868f3f5f690c9dc0ebc82fd9083c901e2`; input `b1005dd04403787fbc7929dd1bb792fe601e5de462c31e830195c00ffdb70c72`; decisions `cbb9b148015764073c9c3c56fa4fdb0505dbb93238e275a2561431978d3ed143`. The review was pinned to PR head `33a63077e88f0cc02210cfce7bc690640ef132d0` / tree `bfeb081505e87f9ef0b1b8f067cc90d2d1fa9c4d`; later packaging changes are docs-only.
