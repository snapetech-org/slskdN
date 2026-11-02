# Window 28 populated-catalog semantic review

This review covers the next 25 pending source keys (300 locale cells) at PR #409 head `17e8d8b829867065b882423ef81c69f1f31c7d07`, tree `7562b0dd09a92398a898d84e1c936119492015be`, source subtree `6d80c43cea32f0a5721f31235ec80e6eaa6d1896`. The ordered IDs run from `src_fd27140eac71557c` through `src_fe60c7ad5a5617f7`.

## Review results

- 237 cells are keep decisions, 39 are correction candidates, and 24 remain uncertain.
- The corrections distinguish music recommendation candidates from human applicants, clarify that “taste” refers to musical preference, replace literal “registry mutation” wording with user-facing controls for changing registry records, and preserve the Pod product name in five inconsistent translations.
- Root independently accepted all 39 exact-hash targets as proposed, with no refinements or holds. The separate application bundle retains the root ledger and apply plan.
- Two contextless source keys remain unchanged across all locales: the fragment `created,` and `Remediation queued for auto-fixable issues: {count}. Still selected for another batch: {remaining}.` Both lack caller/source composition context.

## Exact-head verification

Preflight selected the next sorted eligible IDs and verified 300 current catalog values, 468 caller lines, zero overlap with the 4,800 formal-result cells, 27 prior manual windows (8,100 cells), and 1,114 prior applied corrections. The verifier passed source/current-target joins, placeholder and protected-literal checks, all 39 root approvals, and the exact caller pins. No translation model or API was used.

Semantic confidence is moderate for the accepted targets; locale-quality confidence is moderate. Native-speaker and headed-browser review remain outstanding. No tests, builds, CI, releases, or tags were run for this window.
