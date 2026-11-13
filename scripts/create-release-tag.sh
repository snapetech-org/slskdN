#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

usage() {
    cat >&2 <<'USAGE'
Usage:
  scripts/create-release-tag.sh --private-jit-run <run-id> <v<stable-version>|build-main-*|build-dev-*>

Verifies the private JIT release gate for the exact pushed main commit, then
creates and pushes the release tag.
USAGE
}

fail() {
    echo "ERROR: $1" >&2
    exit 1
}

private_jit_run=""
tag=""
while (($#)); do
    case "$1" in
        --private-jit-run)
            [[ -z "$private_jit_run" && $# -ge 2 ]] || fail "--private-jit-run requires exactly one run ID."
            private_jit_run="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            fail "Unknown option: $1"
            ;;
        *)
            [[ -z "$tag" ]] || fail "Only one release tag may be supplied."
            tag="$1"
            shift
            ;;
    esac
done

if [[ -z "$tag" ]]; then
    usage
    exit 1
fi

[[ -n "$private_jit_run" ]] || fail "A successful private JIT CI run ID is required."

if [[ "$tag" =~ [[:space:]] ]]; then
    fail "Release tag must not contain whitespace."
fi

if [[ "$tag" =~ ^v(.+)$ ]]; then
    version="${BASH_REMATCH[1]}"
    if [[ ! "$version" =~ ^(([0-9]+\.[0-9]+\.[0-9]+)|([0-9]{8,10}))-slskdn\.[0-9]+$ ]]; then
        fail "Stable v tags must use vMAJOR.MINOR.PATCH-slskdn.N or vYYYYMMDDHH-slskdn.N."
    fi
elif [[ "$tag" =~ ^build-(main|dev)-[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
    :
else
    fail "Release tag must be v<stable-version>, build-main-<version>, or build-dev-<version>."
fi

if [[ "$tag" =~ ^build-main- ]]; then
    version="${tag#build-main-}"
    if [[ ! "$version" =~ ^([0-9]+\.[0-9]+\.[0-9]+|[0-9]{10}-slskdn\.[0-9]+)$ ]]; then
        fail "Main release tags must use MAJOR.MINOR.PATCH or YYYYMMDDHH-slskdn.N after build-main-."
    fi
fi

if [[ "$tag" =~ ^build-dev- ]]; then
    version="${tag#build-dev-}"
    if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.dev\.[0-9]{8}\.[0-9]{6}$ ]]; then
        fail "Dev release tags must use MAJOR.MINOR.PATCH.dev.YYYYMMDD.HHMMSS after build-dev-."
    fi
fi

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "Not inside a git worktree."

branch="$(git symbolic-ref --quiet --short HEAD || true)"
if [[ -z "$branch" ]]; then
    fail "Detached HEAD releases are not supported by this helper."
fi

if [[ -n "$(git status --porcelain)" ]]; then
    git status --short >&2
    fail "Working tree must be clean before creating a release tag."
fi

if git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
    fail "Local tag already exists: $tag"
fi

if git ls-remote --exit-code --tags origin "refs/tags/$tag" >/dev/null 2>&1; then
    fail "Remote tag already exists on origin: $tag"
fi

echo "==> Verify GitHub target"
./scripts/verify-github-target.sh

echo
echo "==> Verify release branch sync"
bash scripts/check-release-branch-sync.sh

echo
echo "==> Validate versioned release notes"
notes_tmp="$(mktemp)"
trap 'rm -f "$notes_tmp"' EXIT
./scripts/generate-release-notes.sh "$version" "$notes_tmp" "$branch"
./scripts/validate-release-notes.sh "$version" "$notes_tmp"

echo
echo "==> Verify private JIT release gate"
./scripts/verify-private-jit-release-gate.sh "$private_jit_run" "$branch" "$(git rev-parse HEAD)"

echo
echo "==> Create and push release tag"
git tag "$tag"
git push origin "$tag"

cat <<MSG

Release tag pushed: $tag

Watch the tag build:
  gh run list --repo snapetech/slskdN --workflow build-on-tag.yml --limit 5

After the GitHub release is published, verify artifacts:
  scripts/verify-release-artifacts.sh "$tag"
MSG
