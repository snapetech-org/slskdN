# slskdN PR #409 populated-catalog semantic review

## Exact-head status — 2026-11-01

- PR #409 remains open and draft. The audited catalog baseline is head `4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb`, tree `0eb84397dc2b4be4afd730f6818203bd5910cf15`. Seven exact-hash application commits changed only the approved locale values and `docs/CHANGELOG.md`; application ended at `295f33de43fbe4b6139f6800672411a2e90038c6` / tree `96e0884a82a2cf63f19756d63fb6a7ee77d0a259`. Source code and workflows were not changed.
- Frozen preexisting-catalog backlog: 67,080 cells. The formal result ledger has 150 valid jobs (4,800 cells), 1,951 missing jobs, and zero invalid jobs.
- Eighteen disjoint manual slices cover 450 source keys / 5,400 cells across the 12 direct locales. Combined verdicts: 4,461 keep, 767 high-confidence correction decisions, and 172 uncertain. Of the correction decisions, 736 exact-hash targets from windows 1–17 were applied, six remain held for missing exact source context, and 25 window 18 candidates are pending application. Keep and uncertain values remain unchanged. Formal-ledger overlap and overlap among the manual slices are both zero.
- Qualified native-speaker review remains required.

## Exact-hash correction application

- Applied 736 high-confidence catalog corrections across 175 source keys and all twelve locales in seven sequential commits. The bundle records every prior/proposed value hash, exact source callsite and line hashes, per-file hashes, and commit/tree pins: [`correction application evidence`](../pr-evidence/pr409-catalog-correction-application-2026-11-01/).
- The final census contains 6,169 nonempty values per locale (74,028 total). Comparing with the frozen catalog baseline, exactly the 736 evidenced cells changed; key sets still match across all catalogs. The verifier reconciled every one of the 5,100 manual decisions against the current catalogs and confirmed zero changes outside the correction ledger.
- Six values remain held for missing exact source context, 172 uncertain values remain unchanged, and all 4,461 keep values remain unchanged. Window 18 adds 25 exact-hash correction candidates that have not yet been applied. No source-code or workflow paths changed. No tests, builds, CI, releases, or tags were run for this application.

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


## Window 10

The tenth disjoint 25-key slice covers 300 cells: 247 keep, 41 high-confidence correction candidates, and 12 uncertain. Corrections address P2P peer labels, routing-stat button wording, Quarantine Jury release decisions, Lidarr API-key terms, sharing-group nouns, wishlist search selection, and the Artist Release Radar explanation. “Native playlist” remains uncertain across all locales because the source refers to a browser-local MilkDrop preset playlist and the best locale-native term needs reviewer input.

Evidence: [`window10`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window10/). Manifest SHA-256 `6339cdba5b142a0e1cddc57c1ad06f9a20680ce7a57f3b0ad8ad6f9d95054af9`; input `dc18ddabcf1e49e8283532bd9fb597e55d5f27682f3af93edff6027ff487dfed`; decisions `dc3ecff9c141fa4c06159c90180beb8d46bcc9ea665e335859a059a373078a3c`. The review was pinned to PR head `917e41c1d7b78ca7b114679e8ec1db3178a54e89` / tree `062d80f1b41b7411213736d7c9c91ffab462b0a5`; later packaging changes are docs-only. The scratch verifier confirmed zero formal-result overlap, zero overlap with the nine prior windows, and compared all 2,700 prior input/decision rows.

## Window 11

The eleventh disjoint 25-key slice covers 300 cells: 267 keep, 31 high-confidence correction candidates, and 2 uncertain. Corrections address the lyrics and forensic-analysis labels, parser-fixture terminology, Realm and Pod naming, share-group membership, French expired-membership and download-record wording, Hindi/Indonesian application-status wording, a Japanese execution-contract label, an Arabic copied-report label, and Arabic/Indonesian comparison buttons. Spanish and Vietnamese phrasing for the awkward source sentence “visible in state” remains uncertain pending native review.

Evidence: [`window11`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window11/). Manifest SHA-256 `65e317f6dbca32d1f3350c0e107170fe28d1e9fbd195a74f1bc749775b967efa`; input `90d593959e210ffdc8ca8fdf7e8a933293106829d1aa3827131dd65309418a82`; decisions `f12d3f0e14d18c8d129bc3ddc7f405e0fe2f692e146a2b43f84e52b1a0a9a098`. The review was pinned to PR head `061d9d4d10a7595edc1de6717228bbd5f385fc78` / tree `47a7c87f07c9046ed5a3201fd58ac8ee1effdba4`; later packaging changes are docs-only. The scratch verifier confirmed zero formal-result overlap, zero overlap with the ten prior windows, and compared all 3,000 prior input/decision rows.

## Window 12

The twelfth disjoint 25-key slice covers 300 cells: 255 keep, 44 high-confidence correction candidates, and 1 uncertain. Corrections address IPLD graph-structure terminology, publication statistics, configured share scanning, Smart Radio’s search-plan name, file-write impact, lossless-exact profile wording, recommendation-seed grammar, Pushbullet room mentions, local readiness, and membership-record terminology. Vietnamese wording for the compressed “No file writes” label remains uncertain pending native review.

Evidence: [`window12`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window12/). Manifest SHA-256 `28dd658c1a245f9a6a65597ec35f8a3ca1a6f6e24a2de3b05c9f80c319bde458`; input `4db161920d006dfa3ca1dcd09f8504b57689ffdc9bf55e52c3838b49a5a1ba57`; decisions `85b9121d358c023ec6402539c62eb55d6ea5950255a837f3afa88232272344e4`. The review was pinned to PR head `45645893ab0af3b7cc15556c27496bb9bb699b73` / tree `019bcabdb9d0ef709e7d3a2dd1b9da7f3ed59017`; later packaging changes are docs-only. The scratch verifier confirmed zero formal-result overlap, zero overlap with the eleven prior windows, and compared all 3,300 prior input/decision rows.

## Window 13

The thirteenth disjoint 25-key slice covers 300 cells: 240 keep, 36 high-confidence correction candidates, and 24 uncertain. Corrections address Wishlist search-hit labels, Mesh overlay-network sessions, imported-search count grammar, Smart Radio terminology in Chinese and Japanese, Arabic fast-forward wording, Chinese/Arabic Lidarr software-import terms, and Hindi/Arabic/Indonesian Local Disables labels. “Playlist collection” and “native Soulseek interests” remain uncertain across all locales pending precise product wording.

Evidence: [`window13`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window13/). Manifest SHA-256 `a4b46faeedb1a78c131df0a275da6560f779773e9a28245b9e11453961c56cbe`; input `638d45f1b44d5d37d79e0f78828b99fe9eb93a5bd00ebdeebaebae5b07bcb2a1`; decisions `556b4791e022bcf442589345ea88dec95f47456c565831cb7ba48ea1552a6912`. The review was pinned to PR head `b4b66f815240a7b8636a61d02a208efc314f8e10` / tree `853677967f0691c53c10cb52d565c5c046ae68e9`; later packaging changes are docs-only. The scratch verifier confirmed zero formal-result overlap, zero overlap with the twelve prior windows, and compared all 3,600 prior input/decision rows.

## Window 14

The fourteenth disjoint 25-key slice covers 300 cells: 238 keep, 44 high-confidence correction candidates, and 18 uncertain. Corrections address Smart Radio naming, MilkDrop composite-shader terminology, Hindi port-field grammar, Chinese content-registry terms, successful-check labels, Pod and peer terminology, access categories, selected-search labels, standalone color values, and perceptual-similarity wording. The four Chinese/Japanese/Korean “Quarantine Jury” values remain uncertain because the phrase is marked as a protected literal while the contextual correction would replace it.

Evidence: [`window14`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window14/). Manifest SHA-256 `0f710896ab5fa8f5321de43a48462b58c3eb77ae41f876d32b39c26f63d3ddbb`; input `bbe86d596f788bca47ff31e60a8b2eb1b6b841de21dd48c20ea83e6f1f7028a8`; decisions `2c75706a2e1e9e330ab7ae351e1d1f2bd5d912aaa844af716537978c95dcd905`. The review was pinned to PR head `3b5060fa630836b7bdb467f61d73d5e52f907dbb` / tree `283aa0efedacd4df8528853ea31a4e38db5095a3`; later packaging changes are docs-only. The scratch verifier confirmed zero formal-result overlap, zero overlap with the thirteen prior windows, and compared all 3,900 prior input/decision rows.

## Window 15

The fifteenth disjoint 25-key slice covers 300 cells: 253 keep, 46 high-confidence correction candidates, and 1 uncertain. Corrections address start-time table headings, Pod entity naming, the Hindi retry label, setup health-check wording, Chinese user-note and manual-lookup terms, Arabic new-install wording, Korean verification-stat punctuation, local match-confidence terminology, transfer-table labels, Chinese DHT-publishing terminology, automatic-replacement size thresholds, and Hindi Mesh transliteration. Arabic “Mesh Sync Security” remains uncertain pending the preferred product/network term.

Evidence: [`window15`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window15/). Manifest SHA-256 `7f34a7d568a9545abd59e1003c3103be06e7db677c6c35f44cb55e370c729e05`; input `dbfd4aa6418be05df35c70c842aca5ccb2b4c9cfc578b41978be25d911dcfbe4`; decisions `01794ece71d9ddfe25dc515c48202088186848f4f25f84d4eede290f0a8799ec`. The review was pinned to PR head `6e5658684ff16dffe267d27a3323c46a9120ab45` / tree `32a78530979e5a852d712a86721533809adb6604`; later packaging changes are docs-only. The scratch verifier confirmed zero formal-result overlap, zero overlap with the fourteen prior windows, and compared all 4,200 prior input/decision rows.

## Window 16

The sixteenth disjoint 25-key slice covers 300 cells: 283 keep and 17 high-confidence correction candidates, with no uncertain cells. Corrections address Hindi user-profile terminology, Vietnamese Pod channels and routing, Arabic confirmation and Mesh Pods labels, computing thread counts, playback buffering, transfer-history retention, Korean retrieval counts, and Hindi/Korean visual-theme labels.

Evidence: [`window16`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window16/). Manifest SHA-256 `fc453431e0f182af16d8bd0472f035066521219755aae3f58b2c11e8fd6324f0`; input `849a840e92656c5782e92ee6380f3d0a442f3fc48118917e2f545a3c00eea2b3`; decisions `40c30305647b29d48386a6285d7ff13e71ac18ec39a06a78b9877b12ae23427d`. The review was pinned to PR head `7c111b332060cf23c6c283f3437cb8fc5fb17370` / tree `8857a0cd9d25298a4fa7c6425ce5b7d7ac62f4b6`; later packaging changes are docs-only. The scratch verifier confirmed zero formal-result overlap, zero overlap with the fifteen prior windows, and compared all 4,500 prior input/decision rows.

## Window 17

The seventeenth disjoint 25-key slice covers 300 cells: 241 keep, 35 high-confidence correction candidates, and 24 uncertain. Corrections address Hindi automatic-replacement wording and the service-name example, Chinese similarity headings, adversarial-environment security settings, Vietnamese Discovery Inbox naming, completed-transfer filter labels, and successful-transfer counts. “Unknown Seed” and the incomplete “Edit Filter for” phrase remain uncertain across all locales.

Evidence: [`window17`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window17/). Manifest SHA-256 `2f607cf9329a41bf7d822408d9e1d169699f07afd7f74c4a1c020ecc11d1fac6`; input `5c8aa2d11b2fc4d452497b5975d71cf85672925f5ab8a398e6a8e445cbeb9b55`; decisions `70bd71fa0b37cd7f83172fde81fbf9587d623a316256e8a3a1dec7eb89417bd8`. The review was pinned to PR head `b488c6e3a383824f30702ab469fc74972b647b80` / tree `5f41148487d822b8c6fd51339336928018839226`; later packaging changes are docs-only. The scratch verifier confirmed zero formal-result overlap, zero overlap with the sixteen prior windows, and compared all 4,800 prior input/decision rows.

## Window 18

The eighteenth disjoint 25-key slice covers 300 cells: 274 keep, 25 high-confidence correction candidates, and 1 uncertain. Corrections address Hindi active-search wording, P2P peer terminology, Chinese history and acceptance headings, Arabic dashboard controls, missed-message backfill terminology, reminder titles, Hindi pinned-state agreement, automation-workflow wording, and draft allowlist phrasing. The Japanese “DHT nodes and” fragment remains uncertain because its wording depends on the adjacent count fragment.

Evidence: [`window18`](../pr-evidence/pr409-manual-semantic-review-2026-11-01/window18/). Manifest SHA-256 `3ad326433061518700941cef3eb2c014e659eb2a761e507079a5e4ee9491a11d`; input `124a993a8f50ae4adaa57858c6426c8a36a57b2f789d96e7fefa960ed661c5cf`; decisions `d83201fdb2a63fee0ab8fdfed5bae479707a3cc75d30626788c07621bc7e1157`. Review pin: PR head `5e2c0cb7a8fa3711a5e3ac231a22699fcc86f44f` / tree `a47479dc9625f7dd13c99e6c4febb121e6c56769`; source/catalog snapshot remained unchanged from the previous exact-head census. The scratch verifier passed with zero formal overlap, zero overlap with the 17 prior windows, and zero overlap with the applied correction ledger. The verifier remains in scratch; its path and hash are recorded in the manifest.
