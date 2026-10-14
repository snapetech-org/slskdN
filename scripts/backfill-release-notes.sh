#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

repo="${RELEASE_NOTES_REPO:-snapetech-org/slskdN}"
mode="${1:---dry-run}"
output_dir="${RELEASE_NOTES_AUDIT_DIR:-$ROOT/.local/release-notes-audit}"

if [[ "$mode" != "--dry-run" && "$mode" != "--apply" ]]; then
  echo "Usage: $0 [--dry-run|--apply]" >&2
  exit 1
fi

./scripts/verify-github-target.sh >/dev/null
command -v gh >/dev/null || { echo "gh is required" >&2; exit 1; }
command -v jq >/dev/null || { echo "jq is required" >&2; exit 1; }

mkdir -p "$output_dir"
inventory="$(mktemp)"
trap 'rm -f "$inventory"' EXIT

gh api --paginate "repos/$repo/releases?per_page=100" --slurp |
  jq -r '[.[][]] | sort_by(.published_at) | .[] | [.tag_name, .published_at] | @tsv' >"$inventory"

previous=""
count=0
while IFS=$'\t' read -r version published_at; do
  [[ -n "$version" ]] || continue
  tag_ref="$version"
  if ! git rev-parse -q --verify "refs/tags/$tag_ref" >/dev/null 2>&1; then
    tag_ref="build-main-$version"
  fi
  git rev-parse -q --verify "refs/tags/$tag_ref" >/dev/null || {
    echo "Missing local tag for published release $version" >&2
    exit 1
  }

  notes="$output_dir/$version.md"
  RELEASE_NOTES_PREVIOUS_VERSION="$previous" \
    RELEASE_NOTES_SYNTHETIC_COMMIT_LIMIT=100000 \
    RELEASE_NOTES_ALLOW_EMPTY=1 \
    ./scripts/generate-release-notes.sh "$version" "$notes" "$tag_ref" >/dev/null

  if grep -Eqi 'No recorded changes|Add release notes here' "$notes"; then
    echo "Generated weak notes for $version" >&2
    exit 1
  fi

  if [[ "$mode" == "--apply" ]]; then
    gh release edit "$version" --repo "$repo" --notes-file "$notes" >/dev/null
    echo "Updated $version ($published_at)"
  else
    echo "Generated $version ($published_at)"
  fi

  previous="$version"
  count=$((count + 1))
done <"$inventory"

echo "$count release note bodies ${mode#--}."
