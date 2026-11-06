# slskdN PR #409 W45 independent cross-review

This packet independently reviews the frozen reconstructed W45 selection at PR head `6a082138c09fa8af40aee3258beb98523ee821d9`, tree `90142bfd8904d2a4428ea5f144848ba1c743bdd7`.

## Selection and scope

- 25 source IDs × 12 locales = 300 exact-hash cells.
- W45 selects lexicographic ranks 1–25 among current pending stable IDs after excluding 1,097 unique W1–W44 IDs. The historical ordinal boundary is unavailable; these are reconstructed ranks only, not source ordinals.
- The current catalogs each contain the same ordered 6,170 source keys. All 300 source/target hashes, 12 catalog file hashes and blob IDs, 72 caller hit pins, 72 caller-context refs, and 300 W44 readbacks were independently reattested.
- All seven PR heads, state, draft status, and trees were captured before and after this cross-review. PR #409 stayed OPEN/DRAFT on the exact pinned head and tree.

## Dispositions

- 265 current values accepted unchanged.
- 34 primary proposals accepted as proposed.
- One Spanish proposal revised at rank 15 (`src_0fbdb1f5674cf535`): `Intente cargar de nuevo la configuración para entornos adversarios después de habilitarla en el servidor o restablecer la conexión.` The surrounding security panel calls these options for adversarial environments; this form names that context and preserves the server-enable or connection-restore condition.
- No proposals rejected or held. The current Hindi rank-24 value transliterates protected `ContentID`; the proposed reviewed value restores the ASCII literal. Placeholder, markup, and protected-literal mismatches are zero in all 300 reviewed outcomes.

`crossreview.jsonl` gives a row-level disposition, exact source and target hashes, caller context, integrity readback, and independent reason for every cell. `pin-verification.json` records the independently rechecked source selection, catalogs, caller lines, and prior W44 outputs. `primary-input-manifest.json` pins the primary packet's checksum manifest.

Confidence is moderate and machine-assisted. Qualified native-speaker review remains outstanding. No tests, builds, scans, CI, browser review, releases, tags, repository changes, or PR edits were performed.
