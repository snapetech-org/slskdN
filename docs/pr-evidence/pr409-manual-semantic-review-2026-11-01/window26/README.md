# PR #409 populated-catalog manual semantic review — window 26

This window reviews the next 25 ordered eligible preexisting catalog keys (300 cells, 12 locales each) at PR #409 head `7c3283a340324e19577a486bfc427eb40b6eb5f2`, tree `cf5e11244515bcd78b3bdea08226a52192b5aae3`, and source/catalog subtree `4d8da43318bdd313ce7c05dcb751c0b5beb9015f`. The selected source ID range is `src_fa7fe67124e94375` through `src_fbedb4720f8d5d62`.

## Review result

- 240 cells are keep decisions; 48 are high-confidence correction candidates; 12 are uncertain.
- The candidates address system-job counts translated as employment, load-verification button labels read as nouns, an appended username that cannot follow the current localized error fragment in seven locales, “Listen Along” wording, technical client/customer terminology, and action labels for starting a bridge.
- The 12 uncertain cells are the no-caller `Smart-radio Wishlist seeds added: {count}.` string. Its product meaning cannot be established from the frozen source and surrounding callsites.
- Correction candidates by locale: ar 6, de 5, es 4, fr 4, hi 5, id 2, ja 3, ko 5, pt-BR 2, vi 4, zh-Hans 4, zh-Hant 4.
- Exact-hash proposals are in `proposal-plan.jsonl` (48 rows). Independent cross-review accepted all 48 as proposed, with no refinements or holds. The exact reviewed values were applied in application commit `792f19f3ecf0370ff0cc65307cab376dd5512498`; the separate root ledger and apply plan are in the window26 application bundle.

## Exact-head verification

`preflight_window26.py` and `verify_window26.py` passed at the live OPEN/DRAFT head. They reconstructed the next sorted pending-key selection, checked all current locale file hashes and 360 source-callsite pins, and rechecked 25 prior disjoint windows (7,500 cells), 1,022 applied correction rows, and the 4,800-cell formal accumulator. Formal, manual, and applied overlap were zero. The independent root review accepted all 48 exact-hash proposals and the apply preflight rechecked every source/current/proposal/final hash, caller pin, placeholder, and protected literal. The post-apply verifier found exactly 48 approved values changed and no changes outside the 12 locale catalogs and changelog. The 12 no-caller Smart-radio rows remain uncertain and unchanged.

Semantic confidence is high for flagged candidates; locale-quality confidence is moderate. Native-speaker review remains outstanding. Review generation used no translation-model/API calls. The catalog edits and application ledgers are tracked separately in the linked application bundle; no source or workflow paths changed, and no tests, builds, CI, releases, or tags were run.
