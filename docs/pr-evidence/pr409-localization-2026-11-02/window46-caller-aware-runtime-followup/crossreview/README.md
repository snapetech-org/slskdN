# slskdN caller-aware localization independent cross-review

- Review captured: `2026-11-02T21:29:18Z`.
- Worktree: `/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn`.
- Exact PR #409 head/base: `fa097f9aa044a63981d0c16f6daa53837f815333`; tree `4b1cb71342879581b5422de43450e4b0fc820a18`. Live PR remains OPEN/DRAFT.
- Uncommitted implementation diff SHA-256: `7c0eba386c9d1eed198d49ed88506a0e238e8e1a47c174b53455524d1db70272`.
- Primary packet: `/mnt/disks/scratch/task-scratch/slskdn-localization-callers-20261102/primary`; all five primary SHA256SUMS entries verified.
- Scope: five source IDs, twelve target locales each, 60 values.
- Outcome: 56 proposal values accepted in this machine semantic review; four exact target revisions recommended; no cell held for missing context. Qualified native-speaker review remains outstanding for all 60.

## Main findings

1. Rank37 is a production caller. At the exact base, `BrowseSession.jsx:558` is passed to `window.confirm(interfaceText(...))`; adjacent values are `filesToDownload.length` and `directory.name`. W46 caller evidence captured that line/context but incorrectly classified it as an exact-literal-only reference with zero production localization references. This made 12 crossreview holds and 12 adjudication holds false. The sealed W46 packet remains unchanged. The old primary `accept-current` rows remain valid for the old text and old catalog key; the new ICU-keyed message is independently reviewed row-by-row here. See `w46-rank37-reconciliation.json`.
2. Rank42 can display zero matched tracks and zero changed fields. `Intl.PluralRules` selects `one` for zero in French, Hindi, and Brazilian Portuguese; current singular branches therefore produce singular forms at zero. Add exact `=0` branches to those three cells. Exact suggested targets are in `cell-decisions.jsonl`.
3. Indonesian rank37 uses English `file`, whereas the existing Indonesian catalog translates `File` as `Berkas`. Change it to `berkas`.
4. Rank37 passes `directory.name` through `interfaceText` into a native confirm without direction isolation. `interfaceDialogText` cannot replace it unchanged: it isolates every parameter, including numeric `count`, making `Number(FSI + digits + PDI)` return `NaN` and leaving raw ICU syntax. Add a plural-aware native-dialog formatter that isolates ordinary opaque placeholders while preserving numeric selectors.
5. The frozen source inventory has no records for the five new source IDs. The current coverage test discovers code references and checks that catalogs contain those sources, but it does not check ICU selector names, required branch categories, or count markers. Add an append-only v8 source/caller follow-up record and update the README index; retain existing frozen files.

## Packet files

- `cell-decisions.jsonl`: all 60 row-level decisions, target hashes, exact caller pins, parity/markup checks, and exact proposed revisions.
- `source-and-caller-pins.json`: base, worktree status, diff hash, code hashes, source IDs, caller lines and hashes.
- `catalog-reattestation.json`: independent per-locale key/order/value/hash preservation.
- `live-pr-snapshot.json`: live re-query of all seven localization pull requests.
- `w46-rank37-reconciliation.json`: exact hold supersession scope and production caller proof.
- `findings.json`: full findings, plural formatter review, metadata conclusion, and process limits.

No repository or PR files were modified. No tests, builds, scans, CI, or browser actions were run.
