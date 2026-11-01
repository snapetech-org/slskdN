# slskdN PR #409 populated-catalog semantic review

## Exact-head status — 2026-11-01

- PR #409 remains open and draft. The audited source/catalog snapshot is head `4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb`, tree `0eb84397dc2b4be4afd730f6818203bd5910cf15`. Subsequent commits in this workstream contain review evidence/docs only.
- Frozen preexisting-catalog backlog: 67,080 cells. The formal result ledger has 150 valid jobs (4,800 cells), 1,951 missing jobs, and zero invalid jobs.
- Nine independent manual slices cover 225 source keys / 2,700 cells across the 12 direct locales. Combined verdicts: 2,163 keep, 448 high-confidence correction candidates, and 89 uncertain. These evidence-only decisions are separate from the formal result ledger; no corrections have been applied to catalogs.
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

## Window 5

The fifth disjoint 25-key slice covers 300 cells: 226 keep, 62 high-confidence corrections, and 12 uncertain. Corrections address Soulfind as a named service, Pod terminology, read-only status wording, Lidarr music-release directories, the atlas recenter action, connected-client heading tense, rationale labels, Pushbullet casing, Wishlist search-run counts, Arabic interest terminology, approximate content matching, and diagnostic redaction wording. The single-word “Release” tally remains uncertain across all locales because the compact verdict label may be read as an action or a category; locale-idiomatic wording needs native review.

Evidence: [`window5`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window5/). Manifest SHA-256 `a687c46b9b6ae22be2baaa79ab3ccb0002201d03b77dc2ffc5db22fa77a39979`; input `cb4d4cd094fc666104fdcd88c6f2f3c4e6d63be7df7d5ca47b429cf566eab795`; decisions `35bbda5c1ea44a70744abe134cc62b3ed7e84c914223737b73af80655d09b4cc`. The review was pinned to PR head `ab640fe4b65517a37778f947561513fe33684705` / tree `d201d8a813ec3554d333a28986f2bc529f510f47`; later packaging changes are docs-only.

## Window 6

The sixth disjoint 25-key slice covers 300 cells: 254 keep and 46 high-confidence corrections, with no uncertain cells. Corrections address network latency and peer-count terms, the Mesh transport filter, Vietnamese Pod terminology, Arabic throughput and randomization, cleanup-toast grammar, artist-following status, segment decomposition, traversal-time labels, bulk-filter counts, Spanish removed-state wording, and Arabic skipped-import status.

Evidence: [`window6`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window6/). Manifest SHA-256 `13f14a2e8ee34e14becb89ebeb9c68d538b62d4085e03903f8103ebeab3c7ab0`; input `3fd36a787003b2a8ce1c66365135bf1b90c3e6aa30d1c3856c51dfd7f43c2664`; decisions `c8369e8daf83fb99363774e92c4f05c580fc0c26df3f5ada19ccccecdd3f89cc`. The review was pinned to PR head `1f0edf585591f7034e30865c78fc8de57ceb64ad` / tree `bd77b2cb241080a6bddf8ddf5ad7ded720d06260`; later packaging changes are docs-only.

## Window 7

The seventh disjoint 25-key slice covers 300 cells: 228 keep, 60 high-confidence correction candidates, and 12 uncertain. Corrections address security-feature modal wording, juror targets, MusicBrainz release-group terminology, visualizer collapse actions, wanted-item synchronization, quarantine release decisions, remote settings structure, and content-acquisition terminology. “Realm” remains uncertain across all locales because the preferred localized term for the Mesh trust tier needs locale review.

Evidence: [`window7`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window7/). Manifest SHA-256 `30b193dd2173898e7e5b7af8fa4738d0347af422a11520991f112f3a43e284d0`; input `77197eb0cdb8943910ad35fbedab2ba1c41db7ae36017747b3cdeb87d90ed961`; decisions `18a43c82e2e0fb3df7111970876bce83741094bdf293099e56f8b06211f67a20`. The review was pinned to PR head `ba5d2b6f0d480cd178f9df0dc330b564e1084af2` / tree `e46b6cb479825155390c2e159efed96c3032da9e`; later packaging changes are docs-only. The scratch verifier confirmed zero formal-result overlap and zero overlap with the prior six windows, and compared all 1,800 prior input/decision rows.


## Window 8

The eighth disjoint 25-key slice covers 300 cells: 233 keep, 55 high-confidence correction candidates, and 12 uncertain. Corrections address sing/plural offline-status agreement, rescue-state wording, the Smart Radio feature, peer terminology, MilkDrop visualizer and decay labels, username wording, Wishlist filter syntax, I2P SAM and Tor SOCKS names, the Load Stats action, resolved options, and sample-rate terminology. The player’s “local discovery review shelf” phrase remains uncertain across all locales pending native UX terminology review.

Evidence: [`window8`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window8/). Manifest SHA-256 `809339be633ebc36a88453d54a53cdccc51cf700040b23af14e715b7db993e96`; input `73b80fc7fec7e9f9d8044ba78605ee3e675cd256590826ba00267f0332e3e176`; decisions `740126ca575defdc6d070ee92824dba260e62b8ac6cb4bc1136d83cd2ebf6cbd`. The review was pinned to PR head `44d4c95dabf16f203a7a51122a62d5fa2847bfc9` / tree `9ba5a02fb3160badd321cc5497bb75168cb0256d`; later packaging changes are docs-only. The scratch verifier confirmed zero formal-result overlap and zero overlap with the seven earlier windows, and compared all 2,100 prior input/decision rows.


## Window 9

The ninth disjoint 25-key slice covers 300 cells: 239 keep, 49 high-confidence correction candidates, and 12 uncertain. Corrections address audio-fingerprint terminology, joined chat rooms, web authentication, timed message batching, descriptor JSON, Release Radar, checksums and DHT retrieval, preserved filesystem examples, the official YouTube Data API name, catch-up synchronization and Pod terminology, explicit publication consent, and acquisition profiles. “Management” remains uncertain in all locales because its source row has no callsite or context.

Evidence: [`window9`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window9/). Manifest SHA-256 `fdfe97bb58fecebf3c755cb82f82332b0958cea0a89aa1ec6d7183f0284f974b`; input `7d4f73d3bca269185ef7a1ac460b1b6d8bfdd8202951ffa7b2afb44acec571cb`; decisions `814d541e36b2b6c4884695c0f4bca70f52077d9d96a1f0e9f68fd4b04a931bb8`. The review was pinned to PR head `b7462d8490f53b144945ceb2152851a8996f90b2` / tree `a19bcdc9a81b32ab5bf7aa2101da025220d296cc`; later packaging changes are docs-only. The scratch verifier confirmed zero formal-result overlap, zero overlap with the eight prior windows, and compared all 2,400 prior input/decision rows.
