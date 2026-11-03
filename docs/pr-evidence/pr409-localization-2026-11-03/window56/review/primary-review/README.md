# slskdN PR #409 primary semantic review — W56 ranks 301–302

This ledger reviews 24 current catalog cells across twelve locales at PR head `32afa31caca42b17ac89c9ee91e54ed94cad0411`, tree `0111bd0c279534b972fcbc5f36dd7a32baf86909`. The candidate-free packet checksums and live PR/remote head were verified before review.

Rank 301 (`- {warning}`) is a runtime formatting fragment. Its pinned caller adds a `Warnings:` heading and interpolates `formatWarning(warning)` into the exact `{warning}` token. All twelve current targets retain that token; Japanese uses a localized bullet marker. All are accepted unchanged.

Rank 302 (`Job Types`) labels the number of keys in `analytics.byType` in the System > Jobs panel. Six current labels use employment-position wording that is misleading for system-job categories; the ledger proposes corrections for French, Hindi, Japanese, Korean, Simplified Chinese, and Traditional Chinese. The other six remain accepted. No unsupported cells required a hold.

This is machine-assisted semantic review, not native-speaker approval. Confidence in the six job-term corrections is moderate; qualified native-speaker review remains outstanding. No repository, PR, or workflow files were changed, and no tests, builds, scans, CI, browser work, merge, release, or tag were run.
