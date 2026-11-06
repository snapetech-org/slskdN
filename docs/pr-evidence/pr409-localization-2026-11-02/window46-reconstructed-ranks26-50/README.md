# slskdN PR #409 W46 reconstructed ranks 26–50

This evidence packet records the deterministic W46 selection, primary review, independent cross-review, adjudication, and final catalog readback for 25 source IDs × 12 direct locales (300 cells). The live PR was OPEN/DRAFT at source head `31544a6ef15db2f8481dd76aa9c10844ec3164ba`, tree `fe94582c3e13f0f567fbfa6c3abac6e8558ba17d`. The rank range is reconstructed from the stable-ID queue after excluding W1–W45; historical source ordinals are unavailable and are not claimed.

Final dispositions are 220 accept-current, 38 accept-reviewed-correction, six adopted cross-review revisions, and 36 held cells. Forty-four reviewed values changed; all 300 rows read back against the catalog. Each of the 12 catalogs retains 6,170 keys, the shared key set, its original key order, and its compact JSON serialization.

The six adopted revisions clarify formal Spanish address, Arabic web-security and software-policy terminology, the exact `ContentID` search placeholder, German `DHT-Schlüssel`, and Arabic “unrated” meaning. All accepted changes preserve required placeholders, markup, and protected literals.

Three source contexts remain held across all locales: rank 37 `Download {count} files from {directory}?` has no production caller and no pinned count grammar; rank 42 `tracks,` follows a dynamic count without plural-aware formatting; rank 49 `new` serves both a standalone message separator and a count-bearing Wishlist suffix. The latter two require caller-level source changes before a single translated phrase can fit both contexts. The exact caller gaps and remediation notes are in the adjudication packet.

`primary/`, `crossreview/`, and `adjudication/` preserve the sealed review records and their original checksums. `application/apply-plan.jsonl`, `application/apply-readback.jsonl`, and `application/post-apply-catalog-attestation.json` record the changes and final catalog pins.

This is machine-assisted review, not qualified native-speaker approval. Exact-head headed-browser review remains outstanding because the Agent Desktop Pool coordinator is unavailable. No tests, builds, scans, CI, workflow edits, merges, releases, or tags were performed.
