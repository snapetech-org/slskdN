# Testing Policy

## Purpose

slskdn needs one repeatable gate for release-critical behavior, not scattered one-off tests. The goal is to catch the failure classes that have actually hurt releases:

- frontend bootstrap regressions
- subpath hosting / packaged asset regressions
- backend startup and API smoke failures
- release metadata drift

## Test Layers

### 0. Reproduce-Then-Disprove Bugfix Work

For tester-reported or externally reported regressions, the release bar is not just "some tests passed." The team must capture the reported repro contract, reproduce the same failure locally or in an equivalent environment when practical, then verify the same path after the patch.

Use [bugfix-verification-checklist.md](bugfix-verification-checklist.md) before calling a reported issue "fixed."

Rules:

- split multi-symptom reports into separate acceptance checks
- do not call a bug "fixed" based on a partial internal signal if the user-visible flow was not re-run
- if exact repro is still unavailable, describe the result as a mitigation or unverified fix, not a confirmed fix

### 1. Release Gate

Run `bash packaging/scripts/run-release-gate.sh`.

This is the minimum bar for code that is about to ship or gate CI:

- packaging metadata validation
- frontend unit tests (`vitest`)
- frontend production build
- built-web output verification for subpath-safe relative assets
- served-under-subpath web smoke for `web.url_base` deployments
- backend unit tests
- backend smoke/regression tests in `tests/slskd.Tests`
- targeted backend integration smoke in `tests/slskd.Tests.Integration`:
  - `LoadTests`
  - `DisasterModeIntegrationTests`
  - `SoulbeetAdvancedModeTests`
  - `CanonicalSelectionTests`
  - `LibraryHealthTests`

See [release-checklist.md](release-checklist.md) for the operator-facing release steps and what this gate does or does not prove.

#### Validation engine entry points

The release gate is driven by the repository-specific validation engine. From
the repository root:

```bash
node scripts/validate-development.mjs --plan
node scripts/validate-development.mjs --tests-only
node scripts/validate-development.mjs
node scripts/validate-development.mjs --task browser-e2e
node scripts/validate-development.mjs --task web-browser-e2e
```

Local execution of test tasks requires the trusted Linux bubblewrap launcher.
When evaluating an unreviewed branch, copy `trusted-test-launcher.mjs` and
`trusted-test-sandbox-policy.mjs` from the same reviewed revision to a location
outside the checkout, keeping them together. The launcher snapshots only paths
in the Git index, hides the original checkout and common host configuration and
data roots, and runs candidate code offline. Credential files are excluded
even when extensionless or stored in credential-named folders, while token-like
source files remain in the snapshot. Stage new candidate files first. The
launcher opens each workspace, run-data, dependency, cache, and marker source
before masking host paths, then binds those pinned sources through inherited
file descriptors.
