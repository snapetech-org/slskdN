# slskdN PR #409 W65 third-party cross-audit

This packet reconciles the sealed candidate-free input, primary semantic ledger, and blind source/caller-context proposal ledger for ranks 503–527 at head c64d57a0322897bbaac77fa88a1327dd2f687db7 and tree 51ebf25124fc6ba30c8d5d99298e78353a951f17. It covers all 300 source/locale cells and records both review targets plus one cross-audit disposition and selected target for each cell.

## Resolution

- Primary dispositions: {'accept-current': 227, 'correction': 60, 'hold': 6, 'refinement': 7}
- Blind ledger: 300 proposals; its schema does not classify accept/current versus correction/refinement/hold.
- Primary/blind target differences: 152; all are individually represented and adjudicated in crossaudit-decisions.jsonl.
- Cross-audit dispositions: {'accept-current': 211, 'correction': 73, 'hold': 6, 'refinement': 10}.
- All 98 prior held cells are copied verbatim from the pinned candidate-free reattestation and remain unchanged.
- Six additional W65 holds remain at rank 504, Recording subject conflict. The caller taxonomy distinguishes recording-subject from WorkRef identity and alias-subject but does not define the disputed term sufficiently to replace the existing targets.
- Protected literals such as ContentID, UI, slskdN, Wishlist, and API are checked against the candidate-free token evidence. Placeholder, markup, numeric, and protected-literal checks pass for every selected target.
- Rank 508’s shared Completed key is used predominantly as an individual-record state; Spanish, French, and Brazilian Portuguese use singular state wording while retaining a clear Jobs category label.
- Rank 516 keeps UI exact in selected targets because the source token is protected; rank 523 keeps Wishlist exact for the same reason.
- No repository or PR files were edited. No tests, builds, scans, CI, releases, or tags were run.
- Native-speaker and browser review were not performed.

Run python3 verify_crossaudit.py from this directory for a portable verification of all input pins, row bindings, target adjudications, token checks, the unchanged prior holds, and output checksums.
