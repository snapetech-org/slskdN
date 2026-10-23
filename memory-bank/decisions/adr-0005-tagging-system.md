# ADR-0005: Tag-Based Build and Release System

**Status:** Superseded for new releases on 2026-10-23
**Date:** 2025-12-13
**Updated:** 2026-10-23
**Context:** Multi-channel CI/CD for dev and stable releases

---

## Current policy (supersedes the legacy tag format below)

All new stable releases use `v<version>`, matching the other application
repositories. Pull requests and `main` pushes run validation; release binaries,
container images, GitHub Releases, and downstream packages are produced only
from a pushed `v<version>` tag. Existing `build-main-*` tags and unprefixed
GitHub Releases remain intact for historical downloads and targeted publisher
recovery. `build-dev-*` is no longer a release trigger.

Create new tags with `scripts/create-release-tag.sh v<version>`. Do not use the
legacy channel prefixes below for new releases.

## Historical design (retained for context)

The policy below describes the former channel-prefixed release scheme. It is
not the current release procedure.

### Legacy tag-trigger behavior

**The CI workflow does NOT run on code pushes to master. Builds ONLY happen when you create a tag.**

- ❌ **DO NOT** expect builds to happen automatically when pushing code
- ❌ **DO NOT** modify workflows to trigger on branch pushes
- ❌ **DO NOT** create plain `slskdn.N` tags for releases; they do not trigger
  the release packaging workflow
- ✅ **DO** create release tags through `scripts/create-release-tag.sh` when you
  want to build/release

---

### Legacy decision

We use **explicit build tags** to trigger CI/CD builds and control which channels packages are published to.

### Tag Format

```
build-<channel>-<version>
```

### Channels

#### Dev Channel: `build-dev-*`

**Purpose:** Experimental/unstable builds from feature branches

**Version Format:** `MAJOR.MINOR.PATCH.dev.YYYYMMDD.HHMMSS`
- Example: `0.24.1.dev.20251213.203634`
- Timestamp-based for rapid iteration

**Publishes to:**
- `slskdn-dev` (AUR - binary only)
- `slskdn/slskdn-dev` (COPR)
- `slskdn-dev` package (PPA)
- `ghcr.io/snapetech/slskdn:dev-latest` (Docker)
- `ghcr.io/snapetech/slskdn:dev-VERSION` (Docker)
- Chocolatey (pre-release)

**Usage:**
```bash
VERSION="0.24.1.dev.$(date -u +%Y%m%d.%H%M%S)"
scripts/create-release-tag.sh "build-dev-${VERSION}"
```

#### Main Channel: `build-main-*`

**Purpose:** Stable releases from main branch

**Version Format:** Semantic versioning `MAJOR.MINOR.PATCH`
- Example: `0.25.0`, `1.0.0`, `1.2.3`

The current fork stable stream may also use date-based public versions in the
form `YYYYMMDDHH-slskdn.N` while local build scripts normalize that value for
MSBuild/NuGet.

**Publishes to:**
- `slskdn` (AUR - **source** build from GitHub tarball)
- `slskdn-bin` (AUR - **binary** build)
- `slskdn/slskdn` (COPR)
- `slskdn` package (PPA)
- `ghcr.io/snapetech/slskdn:latest` (Docker)
- `ghcr.io/snapetech/slskdn:VERSION` (Docker)
- Chocolatey (stable)

**Usage:**
```bash
VERSION="2026051218-slskdn.240"
scripts/create-release-tag.sh "build-main-${VERSION}"
```

## Guarded Local Release Helper

Use `scripts/create-release-tag.sh <tag>` instead of manual `git tag` and
`git push` for local releases. The helper:

- verifies the checkout targets `snapetech/slskdN`
- rejects dirty working trees
- verifies the current branch exactly matches its tracked upstream
- rejects duplicate local or remote tags
- validates `build-main-*` and `build-dev-*` tag shapes
- runs `packaging/scripts/run-release-gate.sh`
- pushes the release tag only after the gate passes

After GitHub publishes the release, run
`scripts/verify-release-artifacts.sh <tag>` to download the actual release
assets, verify `SHA256SUMS.txt`, run the Linux binary version check, and assert
that key aggregate features such as the VPN helper payload and Web footer
session-total marker are present in the shipped archive.

## Workflow Logic

### CI Workflow (`ci.yml`)

**Triggers:**
- ✅ **Tags only**: Version tags, `build-dev-*`, `build-main-*`
- ✅ **Pull requests**: For testing (does not publish)
- ✅ **Manual dispatch**: `workflow_dispatch`
- ❌ **NO pushes to master**: Intentionally disabled to prevent unwanted builds

**Jobs:**
- `build`: Always runs (builds and tests)
- `publish`: Only on tags (publishes binaries)
- `docker`: Only on tags (builds Docker images)
- `release`: Only on tags (creates GitHub release)

### Build on Tag Workflow (`build-on-tag.yml`)

The build-on-tag workflow parses the tag:

1. **Parse step** extracts `channel` and `version`
2. **Build** runs for all channels (frontend + 6 platform binaries as `.zip`)
3. **Release + Package jobs** use `if: needs.parse.outputs.channel == '<channel>'`
4. Only matching channel jobs execute; others are skipped

### Channel Isolation

- Dev jobs: `if: needs.parse.outputs.channel == 'dev'`
- Main jobs: `if: needs.parse.outputs.channel == 'main'`

**Result:** Dev builds NEVER publish to main repos, and vice versa.

## Version Conversion

Package managers have version restrictions (no hyphens allowed):

**Rule:** All hyphens → dots via `sed 's/-/./g'`

Examples:
- `0.24.1.dev.20251213.203634` → `0.24.1.dev.20251213.203634` (no change)
- `0.24.1-dev-20251213-203634` → `0.24.1.dev.20251213.203634` (converted)

## Rationale

### Why `build-*` prefix?

**Explicit intent** - Prevents accidental releases. Must explicitly tag with `build-` to trigger CI/CD.

### Why channel in tag?

**Safety** - Impossible to accidentally publish dev to production channels. Channel is encoded in the tag itself, not inferred from branch.

### Why timestamp for dev?

**Rapid iteration** - Multiple builds per day without version conflicts. Clear chronological ordering.

### Why semantic versioning for main?

**Industry standard** - Clear major/minor/patch semantics. Compatible with package manager expectations.

### Why both source and binary for main AUR?

**User choice:**
- **Source** (`slskdn`) - Verifiable builds, native compilation, audit transparency
- **Binary** (`slskdn-bin`) - Fast installation, no build dependencies

Dev uses binary-only (`slskdn-dev`) for faster iteration.

## Consequences

### Positive

- ✅ **No accidental releases** - Must explicitly create `build-*` tag
- ✅ **Channel isolation** - Dev can't leak to main repos
- ✅ **Clear audit trail** - Every build has git tag pointing to exact commit
- ✅ **Version control** - Developer controls versions explicitly (no auto-bumping)
- ✅ **Safe parallel development** - Multiple feature branches can have dev builds

### Negative

- ❌ **Manual tagging required** - Can't auto-release on merge (but this is a feature, not a bug)
- ❌ **Tag cleanup needed** - Old `build-dev-*` tags accumulate (can be pruned periodically)

## Examples

### Trigger Dev Build

```bash
# From experimental/multi-source-swarm branch
VERSION="0.24.1.dev.$(date -u +%Y%m%d.%H%M%S)"
scripts/create-release-tag.sh "build-dev-${VERSION}"
# Publishes to: slskdn-dev, ghcr.io/snapetech/slskdn:dev-latest, etc.
```

### Trigger Main Build

```bash
# From main branch
VERSION="2026051218-slskdn.240"
scripts/create-release-tag.sh "build-main-${VERSION}"
# Publishes to: slskdn, slskdn-bin, ghcr.io/snapetech/slskdn:latest, etc.
```

## Related Files

- `.github/workflows/build-on-tag.yml` - Main CI/CD workflow
- `scripts/create-release-tag.sh` - Guarded local tag creation path
- `scripts/verify-release-artifacts.sh` - Post-publish asset verification
- `CI_PACKAGE_PUBLISHING.md` - Package publishing documentation
- `BUILD_RELEASE.md` - Build instructions
- `packaging/aur/PKGBUILD` - AUR source package
- `packaging/aur/PKGBUILD-bin` - AUR binary package
- `packaging/aur/PKGBUILD-dev` - AUR dev package

## Migration Notes

Old system used:
- Auto-builds on push to `experimental/multi-source-swarm`
- Separate `dev-release.yml` workflow
- No channel isolation

New system:
- Explicit `build-*` tags only
- Single `build-on-tag.yml` for both channels
- Channel encoded in tag for safety
