# slskdN PR #409 W37 independent cross-review

## Exact-head verification

- Live PR: OPEN, draft, branch `codex/slskdn-oidc-tooltip-localization-20261030`.
- Head: `2be3fa4dd46a0f0f49adad342f289721e4777035`; tree: `f838ae565086dec8639f8a54aa4c7d4572342b5f`; `src/web/src` subtree: `594e56c3f439bad476b1bd57e0de1665c62fa1bb`.
- Independently checked all 273 source/current cells, all 11 locale catalog file hashes, all 383 caller references across 35 unique caller lines, and all 42 candidate target hashes. No mismatches.

## Dispositions

- **accepted: 41**
- **refined: 1**

Five missed corrections were found among primary keep rows:

- German and Korean `Incoming search concurrency`: the current wording describes concurrency abstractly instead of naming the count entered in this numeric field.
- Hindi `Timing Obfuscation`: the current text says time-related ambiguity, not concealment of timing patterns.
- Brazilian Portuguese and Vietnamese `release-candidate recommendation`: the current wording does not use a clear software candidate-version term.

One German candidate was refined: `Freiwilliges öffentliches Rendezvous ist deaktiviert.` → `Das Opt-in für öffentliche Rendezvous ist deaktiviert.` The source denotes the opt-in feature, not a voluntary rendezvous.

No proposals were held or classed as no-op. The ledger includes exact source/current/candidate/final SHA-256 values and pinned caller context for every row.

No repository catalogs, PR docs, workflows, builds, tests, scans, CI, releases, or tags were changed or run. Browser and qualified native-speaker review remain outstanding.

## Files

- `independent-crossreview-ledger.jsonl`: all 273 source/current rows, candidate hashes, cross-review dispositions, final target values, and caller pins.
- `summary.json`: exact-head verification and disposition counts.
