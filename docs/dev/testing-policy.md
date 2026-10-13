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
source files remain in the snapshot. Stage new candidate files first.
The launcher opens each workspace, run-data, dependency, cache, and marker
source before masking host paths, then binds those pinned sources through
inherited file descriptors.

```bash
node /path/to/trusted-test-launcher.mjs "$PWD" -- node scripts/validate-development.mjs --tests-only
```

Run planning for an unreviewed candidate through that launcher too, because
planning imports its validation configuration. GitHub Actions remains
responsible for hosted validation.

`--plan` discovers test files, records the Git candidate and supported runtime
versions, and reports command availability. It does not execute tests.
`--tests-only` runs registered unit, regression, integration-smoke, release-note,
and engine-contract tests. The default run adds repository checks and the web
build/output checks. Browser suites remain separately selectable because they
need more time and platform setup.

During execution, the engine writes cumulative task progress to stderr when a
task starts and finishes, with a heartbeat every minute for long tasks. The
summary reports completed, failed, blocked, and pending tasks plus the active
task and elapsed time. Native test-case totals update when each task finishes;
GitHub Actions shows these live updates in the step log because rendered job
summaries are published after the step completes.

Each execution creates a fresh receipt and per-task logs in a private directory
under the operating system's temporary directory. Each log is capped at 16 MiB
and carries a marker when output was truncated. Receipts bind the Git commit,
tree, dirty diff, untracked files, lock/workflow inputs, discovered test-file
digests, runtime versions, and (on GitHub Actions) the workflow run and attempt.
Test tasks pass only when their native command succeeds and reports at least
one active case. No previous result is reused. A task that changes the planned
source blocks remaining work and fails the run. Sensitive environment values
are excluded by constructing runtime-probe and child environments from a
narrow platform and toolchain allowlist. Each task receives private home,
temporary, XDG, and .NET package directories, plus declared settings. `passEnv`
allows only variables approved for that task by the engine. The engine forces
`CI=true`; test tasks use `NODE_ENV=test`. Loader options, proxy settings,
workflow context, arbitrary variables, and operator configuration paths do not
reach child commands.

Playwright tasks keep those private home and XDG directories and use the
job-scoped `slskdn-playwright-browsers` cache under the runner temporary root.
The E2E workflow installs Chromium into that same cache before the engine runs.
The registered browser tasks set `SLSKDN_TEST_NO_CONNECT=true` explicitly, so
the isolated suite does not attempt public Soulseek connections. Use the
separate loopback journey command when exercising peer protocol behavior.
For local browser validation, install Chromium into a task-scoped cache and
pass that directory to the trusted launcher with `--playwright-cache`. The
launcher mounts it read-only and the engine accepts only the launcher's guest
mount path, so arbitrary operator cache paths remain isolated. For example:

```bash
node scripts/validation-engine/trusted-test-launcher.mjs "$PWD" \
  --playwright-cache "$PLAYWRIGHT_BROWSERS_PATH" -- \
  node scripts/validate-development.mjs --task web-browser-e2e
```

See `tests/e2e/README.md` for browser installation details.

GitHub CI uploads the receipt and logs as a seven-day artifact. A passing local
or hosted engine run does not include the separate Nix packaging job, release
publishing, or all platform installer smokes.

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

The validation engine tracks the `tests/e2e/specs` Playwright inventory as the
`browser-e2e` task. `src/web/e2e` is separately inventoried by
`web-browser-e2e`; select it explicitly when the corresponding browser setup
is available. Neither browser suite is silently included in `--tests-only`.

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
