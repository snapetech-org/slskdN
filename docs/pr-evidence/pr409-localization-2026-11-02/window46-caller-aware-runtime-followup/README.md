# slskdN W46 caller-aware runtime and translation follow-up

This follow-up repairs the caller-context classification for W46 rank37 and
replaces three incomplete count labels with complete, count-aware messages.
It is pinned to PR #409 input head `fa097f9aa044a63981d0c16f6daa53837f815333`
and tree `4b1cb71342879581b5422de43450e4b0fc820a18`. The source, catalog, and
line hashes in `current-caller-pins.json` and
`docs/localization-sources/20261102-v8-count-aware-plural-followup.json` pin the
resulting state.

## Review and adjudication

Primary and independent review covered five source IDs across all twelve
direct locales: 60 values total. Root adjudication accepts 56 independent
cross-review targets and adopts four exact revisions: zero-count plural
branches for French, Hindi, and Brazilian Portuguese playlist summaries, and
Indonesian `berkas` in the download confirmation. The row-level decisions,
source/target hashes, caller pins, and exact readback are in
`root-adjudication.jsonl`, `exact-hash-apply-plan.jsonl`, and
`exact-hash-readback.json`.

An additional root static pass confirmed that the final 60 values preserve the
source selector names, have balanced plural branches, contain one `#` marker
per branch, and retain an `other` fallback.

The accepted messages cover matched-track and changed-field counts, wishlist
new-result badges and tooltips, the `New messages` stream separator, and
download confirmation. The wishlist count caller only renders positive
counts. The playlist summary can render zero counts; therefore the three
locales whose cardinal rules select `one` for zero have explicit `=0` target
branches.

## Rank37 caller correction

The production caller in `BrowseSession` passes the directory-download
confirmation to `window.confirm` with `filesToDownload.length` and
`directory.name`. The earlier W46 cross-review and final adjudication treated
the source as callerless because the caller reference was mislabeled. The
sealed W46 packet is preserved. This follow-up supersedes exactly the 12
rank37 cross-review holds and 12 rank37 adjudication holds; the 12 primary
`accept-current` decisions remain valid for the old source text and catalog
key. `w46-rank37-reconciliation.json` contains the independent correction.

## Runtime and catalog boundary

The interface formatter implements the narrow cardinal-plural subset used by
these messages: named numeric selectors, CLDR category branches, integer exact
matches, and `#` substitution with the active locale's plural rules and number
format. It does not implement nested selectors, ordinal plurals, offsets, or
general ICU MessageFormat. `interfaceDialogText` leaves numeric selector
parameters numeric and isolates ordinary opaque values, such as a directory
name, before the native confirmation is displayed.

All twelve catalogs retain their original 6,170 ordered keys and values, then
append the same five reviewed keys in the same order for 6,175 keys each. The
four revised target values are recorded by exact hash; no preexisting catalog
value changed.

The append-only source/caller inventory is
`docs/localization-sources/20261102-v8-count-aware-plural-followup.json`.
Earlier frozen inventories and W46 review packets are not edited.

## Limits

The machine primary and independent reviews do not establish native-speaker
approval. Native-speaker review remains pending for all 60 values. No tests,
builds, scans, CI, or browser work were run for this follow-up; exact-head
headed app review remains outstanding because PR #409 has no exact-head
deployment. No workflow, release, or tag was changed or created.

## Retained packets

- `primary/` — sealed primary packet copied from the task-scoped review output.
- `crossreview/` — sealed independent review and W46 rank37 reconciliation.
- `root-adjudication.jsonl` — final 60-cell machine-review dispositions.
- `exact-hash-apply-plan.jsonl` — reviewed target application plan.
- `exact-hash-readback.json` — all-locale exact-hash readback and catalog-shape
  reconciliation.
- `current-caller-pins.json` — caller lines and file hashes at the applied state.
- `runtime-review.json` — formatter and bidi-boundary code-review findings.
- `SHA256SUMS` — evidence-file manifest.
