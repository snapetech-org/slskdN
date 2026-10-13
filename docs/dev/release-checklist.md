# Release Checklist

## Purpose

This is the minimum release-readiness checklist for `slskdn`.

Green local validation means the tree is a viable release candidate. It does not replace the tag-triggered CI build/publish path.

## Minimum local release bar

Run this from repo root:

```bash
bash packaging/scripts/run-release-gate.sh
bash ./bin/lint
```

When local test execution is unavailable, run the `CI` workflow manually on
`main` using the GitHub-hosted runner option, then pass its run ID to the
release helper:

`scripts/create-release-tag.sh --hosted-ci-run <run-id> <tag>`

Dispatch the workflow with `runner=github-hosted` so the release check does not
depend on the checkout's local SDK or caches.

The helper accepts only a completed successful workflow dispatch for the exact
current `main` commit and the repository's `ci.yml` workflow. The hosted
workflow must include the full release gate.

`node scripts/validate-development.mjs --plan` can preview discovery, runtime versions, and
selected work. It is read-only discovery evidence; only executing the release
gate produces test and build results.

If the release claims to fix a reported bug, also run the reproduce-first workflow in [bugfix-verification-checklist.md](bugfix-verification-checklist.md). Green generic validation is not enough on its own.

The release gate now covers:

- branch sync with the tracked upstream before tagging
- vendored `slskNet.Runtime` revision and local-patch composition
- packaging metadata validation
- validation-engine contract tests and release-note tooling tests
- frontend unit tests
- frontend production build
- built-web output verification
- served-under-subpath web smoke (`/slskd/`)
- backend unit tests
- backend smoke/regression tests
- targeted backend integration smoke tests:
  - `LoadTests`
  - `DisasterModeIntegrationTests`
  - `SoulbeetAdvancedModeTests`
  - `CanonicalSelectionTests`
  - `LibraryHealthTests`

The release gate writes a source-bound receipt and per-task logs to a private
temporary directory. GitHub engine jobs set `TMPDIR` to the job's runner temp
directory and upload only evidence from that directory for seven days. This
receipt does not combine results from the separate Nix job or prove that
publishing and platform installer workflows succeeded.

## What green local validation proves

- the repo builds
- the release gate passes on the current tree
- critical packaged-web and startup/API smoke paths are covered
- a small release-surface integration slice is working

## What it does not prove

- tag-triggered packaging/publish workflows succeeded
- every platform package installed cleanly
- every slow or environment-sensitive E2E path is green
- a tester-reported bug is fixed unless the same reported path was re-run successfully

## Release flow

1. Get the tree green locally:
   - `bash packaging/scripts/run-release-gate.sh`
   - `bash ./bin/lint`
2. For any build that claims to fix a reported issue:
   - capture the repro contract
   - split multi-symptom reports into separate acceptance checks
   - re-run the same path after the patch
   - identify any symptoms that remain unverified
3. Move the shipped user-facing bullets from `## [Unreleased]` into an exact
   version section in `docs/CHANGELOG.md`, for example:
   `## [2026072717-slskdn.292] — 2026-07-27`. The section must contain at least
   one meaningful highlight; empty, placeholder, or “no recorded changes” notes
   are release-blocking.
4. Preview and validate the exact notes when needed:
   - `scripts/generate-release-notes.sh <version> /tmp/release-notes.md <git-ref>`
   - `scripts/validate-release-notes.sh <version> /tmp/release-notes.md`
5. Push the code branch normally if needed.
6. Only trigger build/release by running the guarded tag helper when explicitly desired:
   - `scripts/create-release-tag.sh build-main-YYYYMMDDHH-slskdn.N`
   - `scripts/create-release-tag.sh --hosted-ci-run <run-id> build-main-YYYYMMDDHH-slskdn.N`
   - `scripts/create-release-tag.sh build-dev-MAJOR.MINOR.PATCH.dev.YYYYMMDD.HHMMSS`
7. After GitHub publishes the release, verify the actual assets:
   - `scripts/verify-release-artifacts.sh <tag>`
8. After a stable container image is published, confirm its Docker Hub manifest
   includes Linux amd64 and arm64, then run
   `packaging/scripts/update-cloudron-stable-image.sh <tag>`. This adds an
   immutable `CloudronVersions.json` entry and updates the manifest, Dockerfile,
   and `packaging/docker/stable-image-version`. Rerun packaging metadata
   validation. Do not advance Cloudron from the binary Formula when the Docker
   image job failed.

Do not rely on a normal branch push to validate packaging or publish artifacts. This repo builds releases on tags.
Do not create or push plain `slskdn.N` tags for releases; those do not run the release packaging workflow.

The guarded tag helper validates the versioned changelog section before doing
the expensive release gate or creating a tag. The hosted workflow generates
the notes again from the tagged source and validates them immediately before
the GitHub release write. Both paths fail closed on missing titles/dates,
missing or short highlights, and placeholder wording.

## Release-note contract

User-facing, security, operational, and user-facing documentation changes add
one new validated fragment under `release-notes/`. The pull-request workflow
requires that fragment or an explicit internal-only selection. Fragments are
append-only and carry category, audience, area, action, and breaking-change
metadata.

Preview the grouped release text with:

```bash
python3 scripts/release_notes.py preview --base <base> --head <head>
```

The tag workflow assembles the same grouped `### User-facing changes` section
into `release/RELEASE_NOTES.md`, uses that file for the GitHub release, and
passes the exact body to the Discord embed. Pull-request summaries also show a
capture-metadata table for auditing the fragment fields.

## Recommended extra checks for risky changes

Run these when the change touches the relevant surface:

- Packaging/workflow changes:
  - `bash packaging/scripts/validate-packaging-metadata.sh`
  - `bash packaging/scripts/run-nix-package-smoke.sh`
- Frontend hosting/base-path changes:
  - `pnpm --filter @slskdn/web build`
  - `node src/web/scripts/verify-build-output.mjs`
  - `node src/web/scripts/smoke-subpath-build.mjs`
- Browser/user-journey changes:
  - use the existing Playwright workflow or local E2E smoke
- Packaging or distro-specific changes:
  - perform the relevant platform install smoke before tagging

## Release decision rule

Do not call a build "release-ready" unless:

- local release gate is green
- lint is green
- any claimed bugfix has passed its issue-specific repro/acceptance checks, or is clearly labeled as an unverified mitigation
- no known release-blocking packaging issue is open for the touched platform
- the tag-triggered build is the next intended step

## Orphaned-change guard

The release source of truth is the pushed branch head plus a `build-main-*` or
`build-dev-*` tag created by `scripts/create-release-tag.sh`. The helper refuses
dirty trees, local-only commits, stale upstream branches, duplicate local/remote
tags, and invalid tag names before it runs the full release gate and pushes the
tag. The post-release artifact verifier then checks the downloaded GitHub assets
for checksums, the VPN helper payload, and the bundled Web footer session-total
marker so a release cannot silently miss recently merged aggregate code.
