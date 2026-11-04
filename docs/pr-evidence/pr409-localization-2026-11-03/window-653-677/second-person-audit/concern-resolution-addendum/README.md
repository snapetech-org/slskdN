# W71 three-cell wording concern resolution addendum

This addendum resolves three non-blocking wording concerns from the second-person audit. The sealed cross-review files remain unchanged. It uses only the pinned W71 candidate-free packet and caller evidence at head `d0317d8258a31d05b7f163921c2e39f93deabfca`, tree `01475aeffa17f6151c4bf161890662167c959bb0`.

## Revised targets

- **Rank 659, French:** use `comptes maillés` for mesh accounts. This retains the graph and opted-in meaning while replacing an English adjective with idiomatic French. Confidence: high.
- **Rank 662, Vietnamese:** use `dữ liệu nhạy cảm về các nút ngang hàng hoặc chữ ký` to make the scope of sensitive explicit and identify network peers as nodes. Confidence: moderate.
- **Rank 664, Japanese:** use `時間ベース` for the interval-driven automation mode. The pinned tooltip says timed mode advances on an interval; this avoids implying a scheduled-time mode. Confidence: moderate.

All three revised targets differ from the current translation and the original recommendation. Placeholder, markup, numeric, and protected-literal checks pass. The French target preserves exact `Soulseek`; the Vietnamese target preserves technical `pod`.

## Application recommendation

Recommend updating the application to these three revised strings after native-speaker signoff, especially for Vietnamese and Japanese. No catalog or PR edits are made by this addendum.

Run `python3 verify_addendum.py` to validate the original packet pins, caller references, revised text hashes, token checks, live attestations, and addendum checksums.
