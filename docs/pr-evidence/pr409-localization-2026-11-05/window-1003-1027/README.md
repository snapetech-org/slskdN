# slskdN PR #409 W1003–W1027 localization review

This window covers 25 source messages across 12 direct locales (300 cells) at input head `8c752c49281418fdd96341ed46f5c321627b625f` / tree `b930b0d82679e843849e54456f3250e422c4682c`.

## Review and application

Candidate-free, primary, blind, cross-review, root adjudication, and an independent advisory audit cover all 300 cells. Root retains 217 current values, selects 71 corrections, and preserves 12 callerless cells as text-free hash-only holds. The advisory audit supported 67 cross-selected targets and questioned four; root rewrote those four for clearer French, Hindi, and Indonesian wording for older client versions and to make the Vietnamese transfer action explicitly list-only.

Product commit [`1f93b356f08b7c4bf7b2876d9d541b97dc03b82f`](https://github.com/snapetech-org/slskdN/commit/1f93b356f08b7c4bf7b2876d9d541b97dc03b82f) changes exactly 71 cells across the 12 locale JSON files. All 6,175 keys and key order are preserved in every locale, and every non-target translation remains unchanged. The Hindi FTP retry label preserves the protected literal `FTP`.

All 409 prior active holds were reattested; the 12 new callerless cells remain hash-only, for 421 active holds. The exact input hash and caller-context hold `1719::id` remains unchanged. The root selected 12 more holds at rank 1024 without source or target text.

## Evidence and limits

The candidate-free, primary, blind, cross-review, independent advisory, root-adjudication, and product-readback packets are retained here with checksums. Run `python3 verify_window.py --repo /path/to/slskdN` for the combined offline review and readback verification. This verifier checks the sealed packets and exact catalog commit; it is not a product test suite.

Machine-review confidence is moderate. No qualified native-speaker or exact-head headed-browser approval is claimed. No tests, builds, scans, CI dispatches, workflow edits, deployment, merge, release, or tag were performed for this window.
