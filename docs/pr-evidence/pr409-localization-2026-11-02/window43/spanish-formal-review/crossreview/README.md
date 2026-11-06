# slskdN PR #409 W43 Spanish formal-lane cross-review

Independent static review of the one-cell primary packet at the exact live OPEN/DRAFT head `7fa557e4b3c433708bd490bd1fc9279c0539bc8f` / tree `fd4f7b6f33398fec278173fcf68a04d9c15bc94b`. The primary packet checksums were verified before review.

**Disposition: accept the exact current Spanish value `30 d`.** Reattested source ordinal 87 (`src_0ef5849949bcf7b6`, source `30D`), source hash, catalog blob/file hash, current target hash, caller blob/file/line hashes, and adjacent labels at the pinned head. The caller assigns `30D` the numeric value 30 and places it between `7D` and `90D`; Spanish catalog values are `7 d`, `30 d`, and `90 d`. The key `30D` remains a protected code literal. The label has no placeholder or markup and has no register-bearing words or address form.

BIPM's current 9th-edition SI brochure (v4.01, June 2026) lists day as the non-SI unit symbol `d`, with `1 d = 24 h = 86 400 s` (Table 8, p. 140), and requires a space between number and unit symbol (section 5.4.3, p. 145). This directly supports the value and spacing in `30 d`; BIPM is being used for unit notation, not as evidence of Spanish editorial style.

This is a static cross-review and does not establish native-speaker or browser approval. No repository/PR files were changed; no tests, builds, CI, or browser work ran.

Official references: [BIPM SI Brochure page](https://www.bipm.org/en/publications/si-brochure), [BIPM English brochure PDF](https://www.bipm.org/documents/20126/41483022/SI-Brochure-9-EN.pdf/2d2b50bf-f2b4-9661-f402-5f9d66e4b507?download=true&t=1780410776583&version=7.0), [DOI](https://doi.org/10.59161/AUEZ1291).
