# slskdN caller-composition implementation primary packet

- Host: `kspld0`
- Worktree: `/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn`
- Branch: `codex/slskdn-localization-apply-20261102`
- Exact base: `fa097f9aa044a63981d0c16f6daa53837f815333` / tree `4b1cb71342879581b5422de43450e4b0fc820a18`
- Evidence window: W46 committed primary, crossreview, and adjudication packets remain unchanged.
- State: uncommitted implementation diff, prepared for an independent cross-review. No push, PR update, merge, tag, or release.

## Caller findings and corrected dispositions

W45 ranks 1–25 have **0 holds** in the committed primary review summary. The source rows `pods` and `Private Message from {username}` are in W44, not W45. Their W44 evidence identifies them as a feature-gate-only source with no production display caller and a test-only source with no production caller, respectively. No caller was invented for either source.

W46 rank37 `Download {count} files from {directory}?` does have an exact production caller: `BrowseSession.jsx` passes it to `interfaceText` inside `window.confirm`, with `filesToDownload.length` and `directory.name`. The sealed W46 caller row pins that exact source literal and source context but labels its reference `exact-literal-reference`, records a production localization reference count of zero, and classifies the source as callerless. Primary review accepted all 12 existing translations; crossreview and final adjudication then held all 12. This correction **supersedes exactly the 12 rank37 crossreview hold rows and 12 rank37 final-adjudication hold rows**. It retains the 12 primary `accept-current` rows as the primary translations.

Ranks 42 and 49 had caller-composition holds. Rank42 appended `tracks,` after a dynamic matched count. Rank49 reused `new` as both a separator label and a count suffix. The caller changes now provide full count-aware messages and separate the separator source.

## Count formatter scope

The UI runtime has no MessageFormat/ICU dependency or active plural helper. A narrow formatter now handles only top-level cardinal plural selectors with a named numeric value, CLDR category branches (`zero`, `one`, `two`, `few`, `many`, `other`, and integer exact matches), and `#` replacement. It selects with `Intl.PluralRules(activeLanguage)` and formats `#` with `Intl.NumberFormat(activeLanguage)`. Ordinary `{name}` interpolation remains the existing second pass. It does not implement nested selectors, ordinal plurals, offsets, or other MessageFormat constructs.

## Primary evidence and checks

- `caller-reconciliation.json` pins the caller-count defect, original and corrected call sites, and the exact adjudication rows superseded.
- `source-catalog-matrix.json` includes all five new source IDs, source hashes, context, plural variables, every locale value, per-value hashes, and coverage metadata.
- `catalog-attestation.json` records every catalog’s base/current hash, byte size, and original-key/order preservation.
- `implementation-status.json` lists exact changed files and code hashes.
- Static catalog attestation confirmed all 12 JSON catalogs parse, share the same 5 appended source keys, preserve every preexisting value and original key order, and preserve the existing newline convention. `git diff --check` passed.
- No tests, builds, scans, CI, or browser work were run. Independent review remains pending.

## Retained deliverables

This packet is retained at `/mnt/disks/scratch/task-scratch/slskdn-localization-callers-20261102/primary` for the independent reviewer. It is task-owned evidence and should not be removed with temporary scratch output.
