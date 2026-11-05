# Root adjudication and exact-hash application

`root-review-ledger.jsonl` records all 300 cells. `root-application-plan.json` selects the 114 exact-hash updates, including the single Vietnamese manual adjustment. The 12 held cells are hash-only and contain no translation text.

`apply_exact_plan.py` requires the pinned input head/tree and clean worktree; it checks all 12 catalog preimages, key counts, ordering, and target hashes before applying. `verify_readback.py` validates the committed product diff and reads all 300 pinned cells back from the repository catalogs.

The root disposition counts are 110 corrections, three refinements, one manual adjustment, 174 unchanged cells, and 12 hash-only holds. The review confidence is moderate. Native-speaker approval and browser review are not claimed.
