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

#### NuGet vulnerability scan

Run `python3 scripts/check-nuget-vulnerabilities.py` to audit every first-party
project under `src/`, `tests/`, and `tools/`. The check evaluates direct and
transitive packages and fails on any reported severity. CI runs the same check;
scanning only the application project can miss vulnerable packages resolved by
test or tooling projects.

#### Native test commands

Run the release gate from the repository root:

```bash
bash packaging/scripts/run-release-gate.sh
```

The script calls the repository's normal Python, pnpm, and `dotnet test`
commands directly. Each command stops the gate on failure. GitHub Actions keeps
the command output in the workflow run; browser workflows also upload their
Playwright reports and failure artifacts.

### 2. Focused Regression Tests

Every confirmed bug should leave behind one focused automated check when practical:

- frontend bugs: add/update `vitest` coverage near the affected component or lib
- backend persistence/API bugs: add unit or `tests/slskd.Tests` coverage
- legacy data compatibility bugs: add persistence/materialization tests with representative rows
- packaging/build regressions: add script validation or workflow-safe assertions
- tester-reported route or runtime regressions: add a regression that matches the exact production path that failed, not a nearby approximation

### 3. Deeper Integration / E2E

Use the existing integration and Playwright layers for broader end-to-end coverage:

- `tests/slskd.Tests.Integration`
- `src/web/e2e`
- `.github/workflows/e2e-tests.yml`

Run the main Playwright suite with
`SLSKDN_TEST_NO_CONNECT=true pnpm --filter @slskdn/e2e test:e2e:ci`. For the
Web workspace browser suite, build the Web workspace, run
`pnpm --filter @slskdn/web check:e2e-types`, then run
`SLSKDN_TEST_NO_CONNECT=true pnpm --filter @slskdn/web exec playwright test --reporter=line`.
Both suites need Chromium installed; see `tests/e2e/README.md` for setup.

These are important, but they should complement the release gate rather than replace it.

### 4. Packaging-Specific Smokes

Run targeted package/channel smokes when the change touches packaging:

- `bash packaging/scripts/run-nix-package-smoke.sh`

This validates the current flake package by:

- building `.#default`
- launching the packaged `bin/slskd`
- evaluating a minimal NixOS `services.slskd` configuration with the required `domain`, `environmentFile`, and `settings.shares.directories = [ ]` inputs

### 5. Vendored Runtime Checks

Changes under `vendor/slskNet.Runtime`, `src/slskd/DhtRendezvous`, or runtime capability/rendezvous integration should run the focused app-side tests plus the vendored runtime suite when practical:

- `dotnet test tests/slskd.Tests.Unit/slskd.Tests.Unit.csproj -c Release --filter "FullyQualifiedName~SoulseekCapability|FullyQualifiedName~DhtRendezvous|FullyQualifiedName~SharedMeshUdp|FullyQualifiedName~PeerDescriptor"`
- `dotnet test vendor/slskNet.Runtime/src/Soulseek.Tests/Soulseek.Tests.csproj -c Release`

If the vendored runtime suite exposes analyzer/baseline failures unrelated to the touched runtime behavior, record the exact failing test and treat the result as a known baseline caveat rather than silently dropping runtime validation.

## CI Expectations

- `ci.yml` should run the release gate on pull requests.
- `ci.yml` should also run the Nix package smoke on pull requests.
- Release gate should include `scripts/check-remediation-baseline.sh` so route inventory and shared Web API client path drift are caught before packaging.
- `build-on-tag.yml` should run the same gate before packaging/publishing artifacts.
- `build-on-tag.yml` should also run the Nix package smoke before publish, and again after stable flake metadata updates when the main-channel package pins change.
- E2E remains separate because it is slower and more environment-sensitive.

## Coverage Priorities

When adding tests, prioritize these surfaces first:

1. startup/auth/session/bootstrap paths
2. packaged web output and `web.url_base` compatibility
3. externally reported repro paths that already escaped once
4. config validation and security boundaries
5. persistence compatibility with legacy SQLite rows
6. release workflow/script logic

## Rule of Thumb

Unstable builds can expose bugs. They should not expose the same bug class twice without the repo gaining an automated check for it.
