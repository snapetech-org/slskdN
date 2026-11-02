# Window 30 populated-catalog semantic review

This review covers the final 22 eligible all-locale keys in the ordered common-key pass: 264 cells across all twelve locales. The exact review base was PR #409 head f11dc7199b662a49c5e84794730043af29d6830b, tree 14fc14f856f6335c17d87e78e33963ad1c219735, source/catalog subtree f55419446a34ba4c6cd666aedd1b192d004e88c3.

## Review results

- 213 cells are keep decisions, 39 are correction candidates, and 12 remain uncertain because the duplicated bounded-search status key has no verified caller.
- The correction candidates cover nine source keys. They fix a translated ContentID example in ten locales, unmatched playlist-state wording, French Actions, Korean Contributing Members, the German Browse tab name, the Pod publishing heading, the Arabic/Vietnamese canonical-support wording, bounded-search wording, and Chinese None reported labels.
- Root cross-review accepted 37 candidates as proposed and refined two. All 39 exact-hash targets were applied in commit 0188e7f2b3ca5d57fd91409159a42495cbbac763.
- The 12 uncertain cells remain unchanged and are held for exact source context.

## Exact-head verification

Preflight rechecked 444 caller lines, 29 prior disjoint manual windows / 8,700 cells, 4,800 formal cells, and zero overlap. The candidate verifier rechecked all 444 caller pins, current catalog/source hashes, placeholders, the exact ContentID format literal, and the 39-row cross-review plan. The post-apply verifier checked 92 caller lines for the correction rows, exact changed-key sets, all twelve 6,169-key catalogs, placeholders, and the no-source/no-workflow boundary.

Input SHA-256: cdddce2d0a1eb4b24ac1dced73273ecedb23ef7ff7cc1feb6c426df35a8e8311.
Decision SHA-256: 5b47f3a50bfd3206ee3847eebf5890d89f3c0e793124a20840837d4508c6bdb1.
Candidate-plan SHA-256: a4754dbb630a91f612013e11feba2d2d27f38587eb17411ebeafde9a32eaee66.
Independent root ledger SHA-256: 6a1d408e2c2d513d0b9dfd3ccd7708f00331d3bb36c67093791667a747510c12.

Semantic confidence is high for the flagged errors; locale-quality confidence is moderate. Native-speaker and headed-browser review remain outstanding. No tests, builds, CI, releases, or tags were run for this window. The local Semgrep hook was not run outside private JIT; the application commit used a one-command core.hooksPath override.
