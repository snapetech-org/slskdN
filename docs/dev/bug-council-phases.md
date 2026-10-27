# slskd Focused Remediation Tracker

This tracker covers confirmed slskd findings and their regression checks. Broad source, dependency, secret, and configuration scans use the existing Semgrep and Trivy workflows.

## Retained checks

- `scripts/check-remediation-baseline.sh` registers the focused safety and remediation gates.
- `tests/slskd.Tests/WebInputAdversarialFuzzTests.cs` preserves malformed JSON, random bytes, and hostile query/path cases as regression tests.
- `scripts/run-bug-council-all-phases.sh` runs the remediation gates and the focused web-input fuzz test.

## Retired checks

- Candidate scanners, generated active-bughunt reports, candidate-count gates, and Council-specific semantic analyzer guidance have been removed.
- Semgrep and Trivy remain the general source, dependency, secret, and configuration scanners.

## slskd phases

| # | Name | Status | Owner | Exit criteria |
| --- | --- | --- | --- | --- |
| 1 | Focused remediation documentation | Done | (agent) | The ledger, negative-space gate, behavior-pinning guidance, and this tracker describe the retained regression process. |
| 2 | Negative-space gate registration | Done | (agent) | `scripts/check-remediation-baseline.sh` calls `scripts/check-council-negative-space.sh`. |
| 3 | Web-input adversarial regression | Done | (agent) | The test host covers malformed JSON, deterministic random bytes, and hostile query/path strings; the baseline keeps the test registered. |

## How to resume

1. Read this tracker and the remediation ledger.
2. Run `bash scripts/check-remediation-baseline.sh` for the focused gates.
3. Run `npm run check:council` for the slskd remediation gates and web-input regression test.
