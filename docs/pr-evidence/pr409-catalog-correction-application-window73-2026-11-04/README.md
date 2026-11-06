# slskdN PR #409 W73 catalog application

Applied the 72 independently cross-adjudicated catalog corrections from `cross-review/` on review base `871330ca37a40c15172d3be040271e3944f6f628` / tree `965be29857c8476224307e5dd70c8117d31c2536`. Catalog/changelog commit: `b0f57deaa7e166932eb3923646814b6009acf4bb` (tree `15b08c80bc9223416249c7015a133ab6103c6a81`). The catalog commit changes only `CHANGELOG.md` and the 12 locale JSON catalogs.

Readback covers all 300 selected cells: 72 recommended target hashes match the committed catalogs; 216 accepted values remain at their pinned current hashes; 12 unresolved hold values remain unchanged and are represented in evidence only by hashes and opaque IDs. Each catalog retains 6,176 entries. Placeholder, markup, number/comparator, explicit protected-literal, and exact example-ID parity passed.

`application-readback.jsonl` records only hashes and pins per cell; held rows contain no source/current/proposed text. `cross-review/` is a portable copy of the sealed cross-audit packet with its own checksum manifest and verifier. `apply_catalogs_window73.py` documents the hash-guarded update procedure; `verify_application_window73.py` rechecks committed catalogs.

No tests, builds, scans, or CI were run. No workflow was changed. Native-speaker signoff and browser review are not claimed.
