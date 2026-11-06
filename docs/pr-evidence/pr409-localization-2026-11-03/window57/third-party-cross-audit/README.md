# slskdN PR #409 W57 third-party cross-audit

This sealed audit covers 300 locale cells for continuation ranks 303–327 at PR head `6b09b3c7bf7de69c316ba3e2503dc450004c9b59`, tree `a5f9b792875d341a49208d0785bfff28aa9092d7`. The live PR and both remote refs were checked before adjudication.

## Disposition

- 276 accept-current
- 11 corrections
- 1 wording refinement
- 12 holds

The 12 holds are all locales for rank 319, “Play more tracks locally to build recommendation seeds.” The pinned caller is an empty-state prompt, but no packet defines “recommendation seeds” or supplies approved localized terminology.

The correction at rank 322 Indonesian changes “Saham” (financial stocks) to “Folder bersama” (shared folder), based on the caller being the System/Shares table. This is moderate confidence because the excerpt does not include row values.

## Boundary defect

`selection-and-boundary.json` has invalid `lastSelected` and `nextBoundary` fields (ranks 304 and 305). Those fields were excluded. The complete `selection-boundary.jsonl`, 25 inventory rows, and 300 input cells establish ranks 303–327; the next boundary is rank 328.

## Integrity and limits

The candidate-free input, primary packet, and blind packet checksum lists pass. The audit independently rechecked all 300 source/current hashes and 42 caller references. Placeholder, markup, numeric token, edge whitespace, and protected-literal checks all pass on selected targets. `Soulseek`, `Lidarr`, `{tier}`, and `{peerId}` are preserved where required. No native speaker approved these outputs.

See `cross-audit-ledger.jsonl` for every cell, `disagreements.jsonl` for reviewer conflicts, `input-verification.json` for packet evidence, and `summary.json` for counts. Run `sha256sum -c SHA256SUMS.txt` from this directory to verify the sealed artifacts.
