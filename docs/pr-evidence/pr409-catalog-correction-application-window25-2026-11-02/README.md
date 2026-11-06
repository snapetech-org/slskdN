# PR #409 exact-hash catalog correction application — window 25

Window 25 applied 43 exact-hash corrections from the 25-key / 300-cell review at head `5aba995a65d5901d9b92bd760072e1763d05c47d`, tree `b950c5e51b38b49033f1d85ab03609d70a2fd90f`, and source subtree `a518acd202aebcfe7f17372017cba519e432ab9a`. Root independently accepted all 43 proposals as written (0 refinements, 0 holds). The exact root ledger and apply plan are retained separately in this bundle.

The application commit is `71a9d336b5147ad6fdfd9e769c236811f19993d8` / tree `64a21bc6410161e1264879ab70c7e035e411027e`, parent `5aba995a65d5901d9b92bd760072e1763d05c47d`. Changed values by locale: ar 6, de 2, es 4, fr 4, hi 3, id 5, ja 2, ko 3, pt-BR 5, vi 3, zh-Hans 3, zh-Hant 3. The commit changes only these twelve locale catalogs and the cumulative count in `docs/CHANGELOG.md`; source implementation and workflows are unchanged.

The post-apply verifier passed with exactly 43 changed catalog values and 6,169 keys in each catalog. It checked the exact source/current/proposed/final target hashes, the root review and apply plan, caller pins, placeholders, and catalog key sets. Across 25 disjoint manual windows the review totals are 7,500 cells: 6,264 keep, 1,016 correction decisions, and 220 initially uncertain. Combined with 12 separately resolved Realm cells, 1,022 corrections are applied; six earlier values remain held for missing exact source context and 208 uncertain values remain unchanged. 59,580 backlog cells remain unreviewed. Formal/manual/application overlap is zero.

Semantic confidence is high for the accepted targets; locale-quality confidence is moderate. Native-speaker and headed-browser review remain outstanding. Tests, builds, CI, releases, and tags were not run.
