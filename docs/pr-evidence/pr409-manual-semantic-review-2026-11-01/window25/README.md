# PR #409 populated-catalog manual semantic review — window 25

This bundle reviews the next 25 eligible preexisting catalog keys (300 cells, 12 locales each) at PR #409 head `5aba995a65d5901d9b92bd760072e1763d05c47d`, tree `b950c5e51b38b49033f1d85ab03609d70a2fd90f`, and current source/catalog subtree `a518acd202aebcfe7f17372017cba519e432ab9a`. The selected source ID range is `src_f97cd2cfcbd4a79e` through `src_fa7a4706f7006680`.

## Review result

- 257 cells are keep decisions; 43 are high-confidence correction candidates; 0 are uncertain.
- Correction coverage by locale: ar 6, de 2, es 4, fr 4, hi 3, id 5, ja 2, ko 3, pt-BR 5, vi 3, zh-Hans 3, zh-Hant 3.
- The main corrections address backfill labels that used refill/earthwork meanings, the Artist Release Radar MBID field translated as a release action, a numeric play count rendered as a verb, color names rendered as ducks, the Hindi identity-loaded status, an Arabic import-conflict label, an Arabic release-radar subscription toggle, and Spanish/French request-opening accessible labels.
- Exact-hash correction proposals are in `crossreview-plan.jsonl` (43 rows); the plan hash is recorded in `manifest.json` and `review-summary.json`. Independent cross-review accepted all 43 as proposed, with no refinements or holds. The exact reviewed values were applied in application commit `71a9d336b` and are recorded with the separate root ledger and apply plan in the window25 application bundle.

## Exact-head verification

`verify_window25.py` and the apply preflight passed at the live OPEN/DRAFT PR head before edits. They reconstructed the ordered pending-key selection, checked all current catalog file hashes and source-callsite pins, and rechecked 24 prior disjoint windows (7,200 cells), 979 applied correction rows, and the 4,800-cell formal accumulator. Formal, manual, and applied overlap were zero. The root review and apply plan joined every correction to its exact source ID, catalog key/path, source/current-target/final-target hashes, caller rows, placeholders, protected literals, and pinned head/tree/source subtree. The post-apply verifier found exactly the 43 approved values changed and no changes outside the 12 locale catalogs and changelog.

The semantic review used source callsites and UI context without translation-model/API calls. Semantic confidence is high for flagged candidates; locale-quality confidence is moderate. Native-speaker review remains outstanding. No source, workflow, PR body, tests, builds, CI, releases, or tags were changed or run by this review.
