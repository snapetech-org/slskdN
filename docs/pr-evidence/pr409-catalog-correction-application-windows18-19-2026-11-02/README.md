# PR #409 catalog correction application: windows 18–19

This incremental bundle applies 82 exact-hash corrections from the window 18 and 19 semantic reviews. The reviewed windows are pinned to PR heads `5e2c0cb7a8fa3711a5e3ac231a22699fcc86f44f` / tree `a47479dc9625f7dd13c99e6c4febb121e6c56769` and `4ebd4591994ee709051156df9c9d42160da0b165` / tree `89658bbd1e5ae93080d8fd61ef71beea811e99a2`. Application preflight rechecked live OPEN/DRAFT PR head `35e1c6289cab52a585f14b01d5e4684c068855b6` / tree `196e0432f190f0ceede5cdf8e81e7fa66fb3030a`, with source tree `b5a776a81982ebde32163f06d47c57fc79e40ad9` unchanged.

The bundle adds 82 applied cells across all twelve locales to the earlier exact-hash application of 736 cells. The combined census now has **818 applied corrections across 195 source keys**, **6 held** for missing exact source context, **172 uncertain** values unchanged, and **4,704 keep** values unchanged. All 5,700 manual review rows reconcile with the final catalog values. The per-locale applied totals are: ar 93, de 44, es 66, fr 66, hi 72, id 78, ja 43, ko 57, pt-BR 57, vi 86, zh-Hans 79, zh-Hant 77.

The preflight confirmed 82 candidate cells with exact current-target, source, and callsite hashes; zero overlap with the previous 736 applied cells, six held cells, 4,800 formal cells, or prior windows; and no duplicate target keys. The catalog commit `6045f4610` changes the twelve locale catalogs and `docs/CHANGELOG.md` only. Since frozen catalog baseline `4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb` / tree `0eb84397dc2b4be4afd730f6818203bd5910cf15`, exactly the 818 ledger cells changed. Each locale still has 6,169 nonempty entries and identical key sets. No workflow or non-catalog source changes were made.

Evidence files:

- `applied-corrections.jsonl`: 82 exact source/current/proposed values, hashes, review references, and source callsite hashes.
- `preflight.json`: exact live-head, overlap, formal ledger, prior ledger, and source/catalog preflight results.
- `application-result.json`: before/after catalog file hashes for the 12 locale files.
- `manifest.json`: catalog baseline, application commit/tree, cumulative counts, and artifact hashes.
- `verify_application.py`: rechecks the entire 19-window census and exact-current catalog reconciliation. Run from the repository root with `python3 docs/pr-evidence/pr409-catalog-correction-application-windows18-19-2026-11-02/verify_application.py`.
- `verification.json`: verifier output at application commit `6045f4610`; the subsequent docs-only evidence commit does not alter catalog values.

No tests, builds, CI jobs, local scans, releases, or tags were run for this application. The earlier packaging commit `5e2c0cb7` automatically ran the local Semgrep hook and reported zero findings; this application and its follow-up documentation commit used a one-command `core.hooksPath=/dev/null` override per the private-JIT policy. Native-speaker review remains required.
