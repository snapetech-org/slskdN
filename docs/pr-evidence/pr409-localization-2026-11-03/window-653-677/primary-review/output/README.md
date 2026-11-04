# slskdN PR #409 W71 primary translation review

This review covers continuation ranks 653–677 (25 English source IDs) across all 12 direct locale catalogs: 300 current translation cells. It is pinned to PR #409 head `d0317d8258a31d05b7f163921c2e39f93deabfca` and tree `01475aeffa17f6151c4bf161890662167c959bb0`.

## Evidence basis

The review uses only the candidate-free packet at `/home/keith/Documents/code/task-scratch/slskdn-pr409-w71-653-677-20261103/candidate-free-packet/input/`: pinned English sources, current target strings and hashes, exact quoted-literal production caller contexts, catalog/source pins, and prior exclusion/hold attestations. Its checksum-list SHA-256 is `be3d9a9f300d15caabaffafb03fdbbb32217e01be6b808cdd71a0e691e99e3ea`; source inventory SHA-256 is `17cb8a747939d4973733016b95f29284e191d5444910051e42fb153cf4f94225`.

The candidate-free verifier passed before review. It attests 6,176 inventory IDs, 25 selected IDs at ranks 653–677, the next boundary at rank 678, 1,757 excluded IDs, 12 catalogs with 6,176 ordered keys each, and 140/140 carried held-cell target hashes unchanged. All 25 caller-context records are pinned. No blind or cross-review material was read or used.

## Dispositions

- 257 accept-current
- 21 correct
- 10 refine
- 12 hold
- 31 proposed target values

The 12 holds are all locale cells for rank 654, `Refresh the seven-day transfer totals.` The exact production scan found no caller for this source, so the requested UI action cannot be established from usage. The Japanese and Korean current targets use the digit `7` for “seven”; this is semantically equivalent but produces the two numeric-token checker flags.

The baseline has zero placeholder mismatches and zero markup mismatches. Its two numeric flags are the Japanese and Korean rank-654 targets. Its one protected-literal flag is Hindi rank 672, where `TLS` is transliterated; the proposed correction restores exact `TLS` and cues the following HTTPS link. Every proposed target passes placeholder, markup, numeric-token, and protected-literal checks. The held numeric differences remain explicitly recorded; no proposal is made for rank 654.

`primary-review.jsonl` contains one record per cell with source/current hashes, caller-context hash and exact caller references, disposition, rationale, confidence, proposed target (null for accept-current and hold), and recomputed current/proposed token checks. `manifest.json` gives counts, baseline token flags, pin identities, and review scope.

## Limits and next window

This is a machine-assisted semantic review and does not claim qualified native-speaker signoff. No repository or PR files were changed. No tests, builds, scans, CI, workflow actions, or browser actions were run. The next unselected continuation rank is 678; a following 25-source window would span 678–702 if selected.

Run `python verify_primary.py` from this directory to verify the candidate-free input checksum list, source/catalog/context pins, all 300 ledger rows, token checks, prior exclusions and holds, and the output checksum list.
