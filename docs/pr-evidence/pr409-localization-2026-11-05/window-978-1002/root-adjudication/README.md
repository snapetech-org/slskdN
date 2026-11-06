# slskdN PR #409 W978–W1002 root-adjudication opinion

This packet records an independent advisory recommendation for all 64 cells flagged in the cross-review ledger. It is pinned to head `1c2fe3be2c720693cbcb12d377bf1177804f4e77`, tree `808501cbc3b6ed873a47d7188189d486f0673f5e`. It preserves each cell’s exact source, current target, candidate caller references/context hashes, and primary/blind proposals so the recommendation can be checked against the sealed candidate-free input.

## Recommendation summary

- 64 flagged cells reviewed: 64 exact corrections recommended, 0 current accepts, 0 holds.
- 50 recommendations select the primary proposal, 9 select the blind proposal, 1 selects the exact primary/blind agreement, and 4 are independent refinements.
- The advisory opinion leaves final root adjudication unperformed. Confidence is moderate overall; no native-speaker signoff is claimed.
- Key conflict calls: Arabic and French W984 select blind wording; Brazilian Portuguese W984 uses an independent sentence; Japanese W988 uses a localized, explicit timed-switching label; Arabic W991 selects the blind client-ID construct; W997 selects blind wording for Arabic, Hindi, Vietnamese, and Traditional Chinese; Simplified and Traditional Chinese W1000 use the full-width colon.

## Protected-literal repairs

All five baseline protected-literal mismatches receive a repair:

- W991 Arabic and Hindi “Spotify client ID” retain exact `ID`.
- W999 Arabic and French decode-to-MP3 tooltip retain exact `CPU` and `MP3`; Arabic also changes the verb to audio decoding rather than decryption.
- W1001 Simplified Chinese “QR invite code” retains exact `QR` without redundantly translating QR as 二维码.

The JSONL has one row per flagged cell. Each row contains exact source/caller bindings, prior proposals and rationales, the selected target and its SHA256, locale-specific reasoning, and placeholder/markup/number/protected-literal checks.

## Verification

`verify_adjudication.py` checks the 64-cell identity and order against the supplied cross-review ledger, source/caller/proposal bindings, recommendation hashes, token preservation, protected-literal repairs, and this packet’s SHA256 inventory. `cross-review-verifier-output.txt` records the upstream exact-worktree/candidate-free/primary/blind/cross-review verification, which passed for all 300 cells and 64 flags.

No repository files or locale catalogs were edited. No tests, builds, scans, or CI jobs were run.
