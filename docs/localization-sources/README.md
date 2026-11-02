# Localization source inventory

`20261031-interface-copy-inventory.json`, `20261101-v5-followup-inventory.json`,
and the v6/v7 follow-ups are immutable source evidence. The exact-head input at
`a13c513e5cd73703653b164f36c60fd3e50d0873` (tree
`e6e4a4d563c202368e530b596ab37879479f4e85`) contained 452 source rows: 451
missing keys (5,412 target cells) plus the existing `Playback stopped.` key
with 12 English-identical values. All 5,424 target cells were filled in the
catalog update and semantically reviewed: 1,741 accepted, 3,683 corrected, and
none held. The review ledger is retained at
`/mnt/disks/scratch/task-worktrees/localization-20261030/slskdn-semantic-review-a13c513e-20261101/semantic-review-audit.jsonl`
(SHA-256 `3133d80f9aac6acb5ac025d8a6caefbe5dc7877ae844bf68ff6bca165e0520dd`).
PR #409 remains draft. All 5,424 cells still require native-speaker review; no
native approval is claimed. The source-reference inventory records 10,263 references across 5,644
unique source strings. Two fixed transfer-cleanup success messages are already
translated in all locales and do not add pending cells. Caller lines and file
hashes make the frozen source inventory reproducible.

`20261031-ui-outbound-copy.json` is preserved as the historical 56-source
checkpoint from the first source pass. It is superseded by the current ledger
and should not be edited to represent later work. Its two notification-title
records are represented by the complete current browser-source inventory and
are included in the completed 5,424-cell review.

The current ledger covers fixed browser UI copy, generated report templates,
known mapped diagnostic messages, fixed Quarantine Jury statuses and errors,
the Library Health scan failure, and the two notification titles. The browser
surface audit maps stable API error codes, exact Content ID and mesh-sync
messages, the Quarantine Jury allowlist, and the fixed Library Health failure.
API values, user content, paths, provider labels, protocol values, and unknown
diagnostics remain data. Only allowlisted application-owned strings are
translated.

Catalog parity and placeholder checks passed after the update: each locale has
the same 6,169 keys, and all 6,169 values per locale preserve the source
placeholders. This structural validation does not replace native-speaker
approval or semantic review of the previously populated catalog values.


The v5 source-fix inventory is `20261101-v5-followup-inventory.json`. It records the two previously missing app outputs (equalizer and file-deletion errors) and three MessagingV2 action templates with opaque room/pod names; their 60 target translations are included in the completed review. It separately records the 12 formerly English-identical targets for `Playback stopped.`, also included in the review. The two fixed Network sync errors and four PortForwarding validation strings already existed in every locale catalog.

The v6 boundary follow-up is `20261101-v6-boundary-followup.json`, pinned to
source head `cf99bafc6d8926ed1bd11af47105bd53f069956b`. It records one new
reference to the existing, fully translated `External Visualizer` source; it
adds no source IDs or translation cells. The source follow-up also isolates
125 dynamic aria-label, title, and alt expressions, 19 parameterized attribute
prop spreads, and three native confirmation messages in every UI language.
The source-reference extractor recognizes the new attribute/dialog helpers.
Unknown launch errors stay opaque, and configured visualizer names and paths
retain explicit language/direction metadata.

The v7 inline-text boundary follow-up is
`20261101-v7-inline-bidi-followup.json`. It records source commit
`cfde13f414b13f71c26585cf061fcd38abd9bd7b`, which wraps every own string or
number placeholder rendered by `LocalizedText` in `<bdi dir="auto" lang="und">`
for LTR translations, RTL translations, and English fallback text. Regression
coverage was added for Spanish- and Arabic-selected English fallback; it was
not run for this source-only follow-up. No source IDs, catalog values, or
translation cells were added.
