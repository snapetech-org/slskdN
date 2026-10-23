#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

usage() {
    cat >&2 <<'USAGE'
Usage:
  scripts/create-release-tag.sh [--hosted-ci-run <run-id>] <v<version>>

Runs the release gate against the exact pushed branch head, then creates and
pushes the release tag. A successful manual CI run may be supplied when local
test execution is unavailable.
USAGE
}

fail() {
    echo "ERROR: $1" >&2
    exit 1
}

hosted_ci_run=""
tag=""
while (($#)); do
    case "$1" in
        --hosted-ci-run)
            [[ -z "$hosted_ci_run" && $# -ge 2 ]] || fail "--hosted-ci-run requires exactly one run ID."
            hosted_ci_run="$2"
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

if [[ "$tag" =~ [[:space:]] ]]; then
    fail "Release tag must not contain whitespace."
fi

if [[ ! "$tag" =~ ^v([0-9]+\.[0-9]+\.[0-9]+|[0-9]{10}-slskdn\.[0-9]+)$ ]]; then
    fail "Release tags must use vMAJOR.MINOR.PATCH or vYYYYMMDDHH-slskdn.N."
fi
version="${tag#v}"

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
echo "==> Run release gate"
if [[ -n "$hosted_ci_run" ]]; then
    ./scripts/verify-hosted-release-gate.sh "$hosted_ci_run" "$branch" "$(git rev-parse HEAD)"
else
    bash packaging/scripts/run-release-gate.sh
fi

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
