#!/usr/bin/env bash
# Repo-backed GitHub release notes.
# Tagged releases use either the matching version section in docs/CHANGELOG.md
# or synthesize notes from the commit delta since the previous release tag.
# They must never publish the rolling Unreleased bucket.
#
# Usage:
#   ./scripts/generate-release-notes.sh <logical-version> <out-path> [git-ref]
#
# <logical-version> should match a heading in docs/CHANGELOG.md:
#   ## [<logical-version>] — YYYY-MM-DD   or   ## [<logical-version>]
#
# <git-ref> defaults to the release source tag when available (for example
# build-main-<logical-version> / build-dev-<logical-version>), otherwise
# refs/tags/<logical-version>, GITHUB_SHA, or HEAD.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

err() {
  echo "[generate-release-notes] ERROR: $*" >&2
  exit 1
}

trim_blank_edges() {
  awk '
    { lines[NR] = $0 }
    END {
      start = 1
      while (start <= NR && lines[start] ~ /^[[:space:]]*$/) start++
      end = NR
      while (end >= start && lines[end] ~ /^[[:space:]]*$/) end--
      for (i = start; i <= end; i++) print lines[i]
    }
  '
}

CHANGELOG_PATH="${CHANGELOG_PATH:-docs/CHANGELOG.md}"

extract_changelog_section() {
  local heading="$1"
  [[ -f "$CHANGELOG_PATH" ]] || return 0
  awk -v heading="$heading" '
    $0 == heading { in_section = 1; next }
    in_section && /^## \[/ { exit }
    in_section && /^---$/ { next }
    in_section { print }
  ' "$CHANGELOG_PATH" | trim_blank_edges
}

extract_changelog_release_date() {
  local version="$1"
  [[ -f "$CHANGELOG_PATH" ]] || return 0
  awk -v ver="$version" '
    $0 ~ "^## \\[" ver "\\] — [0-9]{4}-[0-9]{2}-[0-9]{2}$" {
      print substr($0, length("## [" ver "] — ") + 1)
      exit
    }
  ' "$CHANGELOG_PATH"
}

normalize_remote_url() {
  local raw="$1"
  case "$raw" in
    https://github.com/*)
      printf '%s\n' "${raw%.git}"
      ;;
    git@github.com:*)
      raw="${raw#git@github.com:}"
      printf 'https://github.com/%s\n' "${raw%.git}"
      ;;
    *)
      printf '%s\n' "${raw%.git}"
      ;;
  esac
}

repo_slug_from_url() {
  local raw="$1"
  case "$raw" in
    https://github.com/*)
      raw="${raw#https://github.com/}"
      printf '%s\n' "${raw%.git}"
      ;;
    git@github.com:*)
      raw="${raw#git@github.com:}"
      printf '%s\n' "${raw%.git}"
      ;;
    *)
      printf '%s\n' ""
      ;;
  esac
}

subject_highlight() {
  local subject="$1"
  subject="$(printf '%s' "$subject" | sed -E 's/^[a-z]+(\([^)]+\))?:[[:space:]]*//')"
  printf '%s' "$subject" | awk '
    {
      line = $0
      if (length(line) == 0) next
      first = substr(line, 1, 1)
      rest = substr(line, 2)
      line = toupper(first) rest
      if (line !~ /[.!?]$/) line = line "."
      print line
    }
  '
}

is_release_hygiene_subject() {
  local subject="$1"
  case "$subject" in
    ci:\ *|ci\(*\):\ *|build:\ *|build\(*\):\ *|test:\ *|test\(*\):\ *)
      return 0
      ;;
    fix\(release\):\ *|chore\(release\):\ *|docs\(release\):\ *)
      return 0
      ;;
    Revert\ \"fix\(release\):\ *|Revert\ \"docs:\ Add\ gotcha\ *)
      return 0
      ;;
    docs:\ Add\ gotcha\ for\ *|docs:\ add\ gotcha\ for\ *)
      return 0
      ;;
    docs:\ add\ release\ notes\ *|docs:\ update\ release\ *)
      return 0
      ;;
    docs:\ update\ *status|docs:\ Record\ *deploy|docs:\ record\ *deploy)
      return 0
      ;;
    docs:\ Update\ *context|docs:\ update\ *context)
      return 0
      ;;
    chore:\ commit\ packaging\ release\ cleanup)
      return 0
      ;;
    chore:\ finish\ vendored\ runtime\ rollout)
      return 0
      ;;
    chore:\ finish\ *cleanup|chore:\ include\ remaining\ *cleanup)
      return 0
      ;;
    chore:\ remove\ remaining\ *references)
      return 0
      ;;
  esac
  return 1
}

logical_is_release_version() {
  local version="${1#v}"
  [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+-slskdn\.[0-9]+$ ]] ||
    [[ "$version" =~ ^[0-9]{8,10}-slskdn\.[0-9]+$ ]]
}

strip_build_prefix() {
  local tag="$1"
  tag="${tag#v}"
  tag="${tag#build-main-}"
  tag="${tag#build-dev-}"
  printf '%s\n' "$tag"
}

resolve_current_source_tag() {
  local logical="$1"
  local explicit_ref="${2:-}"
  local candidate=""

  if [[ -n "$explicit_ref" ]] && git rev-parse -q --verify "refs/tags/${explicit_ref}" >/dev/null 2>&1; then
    printf '%s\n' "$explicit_ref"
    return 0
  fi

  for candidate in \
    "v${logical}" \
    "build-main-${logical}" \
    "build-dev-${logical}" \
    "${logical}"
  do
    if git rev-parse -q --verify "refs/tags/${candidate}" >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
}

find_previous_tag() {
  local current_tag="$1"

  if [[ -z "$current_tag" ]]; then
    git describe --tags --abbrev=0 "${GIT_REF}^" 2>/dev/null || true
    return 0
  fi

  if [[ "$current_tag" =~ ^build-main- ]]; then
    git tag --sort=-v:refname |
      grep -E '^build-main-([0-9]+\.[0-9]+\.[0-9]+|[0-9]{8,10})-slskdn\.[0-9]+$' |
      awk -v cur="$current_tag" '$0 != cur { print; exit }' || true
    return 0
  fi

  if [[ "$current_tag" =~ ^build-dev- ]]; then
    git tag --sort=-v:refname |
      grep -E '^build-dev-[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z]+)*$' |
      awk -v cur="$current_tag" '$0 != cur { print; exit }' || true
    return 0
  fi

  if logical_is_release_version "$current_tag"; then
    git tag --sort=-v:refname |
      grep -E '^v?([0-9]+\.[0-9]+\.[0-9]+|[0-9]{8,10})-slskdn\.[0-9]+$' |
      awk -v cur="$current_tag" '$0 != cur { print; exit }' || true
    return 0
  fi

  git describe --tags --abbrev=0 "${current_tag}^" 2>/dev/null || true
}

find_previous_published_release_version() {
  local logical="$1"
  local repo_slug="$2"
  local prev=""
  local tag=""

  logical_is_release_version "$logical" || return 0
  command -v gh >/dev/null 2>&1 || return 0
  [[ -n "$repo_slug" ]] || return 0

  while IFS= read -r tag; do
    tag="${tag#v}"
    logical_is_release_version "$tag" || continue
    if [[ "$tag" == "$logical" ]]; then
      break
    fi
    prev="$tag"
  done < <(
    gh release list \
      --repo "$repo_slug" \
      --limit 100 \
      --json tagName \
      --jq '.[].tagName' 2>/dev/null | sed 's/^v//' | sort -V
  )

  printf '%s\n' "$prev"
}

LOGICAL_VERSION="${1:-}"
OUT_PATH="${2:-$ROOT_DIR/dist/release-notes.md}"
GIT_REF_ARG="${3:-}"

[[ -n "$LOGICAL_VERSION" ]] || err "usage: $0 <logical-version> <output-path> [git-ref]"

REMOTE_URL="$(git config --get remote.origin.url || true)"
REPO_URL="$(normalize_remote_url "$REMOTE_URL")"
REPO_SLUG="$(repo_slug_from_url "$REMOTE_URL")"
CURRENT_SOURCE_TAG="$(resolve_current_source_tag "$LOGICAL_VERSION" "$GIT_REF_ARG")"

if [[ -n "$GIT_REF_ARG" ]]; then
  if git rev-parse -q --verify "refs/tags/${GIT_REF_ARG}" >/dev/null 2>&1; then
    GIT_REF="refs/tags/${GIT_REF_ARG}"
  else
    GIT_REF="$GIT_REF_ARG"
  fi
elif [[ -n "$CURRENT_SOURCE_TAG" ]]; then
  GIT_REF="refs/tags/${CURRENT_SOURCE_TAG}"
elif git rev-parse -q --verify "refs/tags/${LOGICAL_VERSION}" >/dev/null 2>&1; then
  GIT_REF="refs/tags/${LOGICAL_VERSION}"
else
  GIT_REF="${GITHUB_SHA:-HEAD}"
fi

git rev-parse -q --verify "$GIT_REF" >/dev/null || err "git ref not found: $GIT_REF"

RELEASE_DATE="$(extract_changelog_release_date "$LOGICAL_VERSION")"
if [[ -z "$RELEASE_DATE" ]]; then
  RELEASE_DATE="$(git log -1 --format=%cs "$GIT_REF")"
fi
if [[ -n "${RELEASE_NOTES_PREVIOUS_VERSION+x}" ]]; then
  PREV_RELEASE_VERSION="$RELEASE_NOTES_PREVIOUS_VERSION"
else
  PREV_RELEASE_VERSION="$(find_previous_published_release_version "$LOGICAL_VERSION" "$REPO_SLUG")"
fi
PREV_TAG=""
PREV_DISPLAY_TAG=""

if [[ -n "$PREV_RELEASE_VERSION" ]]; then
  PREV_DISPLAY_TAG="$PREV_RELEASE_VERSION"
  for candidate in \
    "v${PREV_RELEASE_VERSION}" \
    "build-main-${PREV_RELEASE_VERSION}" \
    "build-dev-${PREV_RELEASE_VERSION}" \
    "${PREV_RELEASE_VERSION}"
  do
    if git rev-parse -q --verify "refs/tags/${candidate}" >/dev/null 2>&1; then
      PREV_TAG="$candidate"
      break
    fi
  done
fi

if [[ -z "$PREV_TAG" && -z "${RELEASE_NOTES_PREVIOUS_VERSION+x}" ]]; then
  PREV_TAG="$(find_previous_tag "$CURRENT_SOURCE_TAG")"
  PREV_DISPLAY_TAG="$(strip_build_prefix "$PREV_TAG")"
fi

TAG_SECTION="$(extract_changelog_section "## [$LOGICAL_VERSION] — $RELEASE_DATE" || true)"
if [[ -z "$TAG_SECTION" && -f "$CHANGELOG_PATH" ]]; then
  TAG_SECTION="$(
    awk -v ver="$LOGICAL_VERSION" '
      $0 ~ "^## \\[" ver "\\]" { in_section = 1; next }
      in_section && /^## \[/ { exit }
      in_section { print }
    ' "$CHANGELOG_PATH" | trim_blank_edges || true
  )"
fi

if [[ -n "$PREV_TAG" ]]; then
  RANGE="${PREV_TAG}..${GIT_REF}"
  COMPARE_URL="$REPO_URL/compare/${PREV_DISPLAY_TAG}...${LOGICAL_VERSION}"
else
  RANGE="${GIT_REF}^!"
  COMPARE_URL=""
fi

COMMITS="$(git log --reverse --no-merges --format='%H%x09%s' "$RANGE" 2>/dev/null || true)"
if [[ -z "$COMMITS" ]]; then
  COMMITS="$(git log --reverse --format='%H%x09%s' "$RANGE" 2>/dev/null || true)"
fi

DISPLAY_COMMITS=""
MAINTENANCE_COMMITS=""
if [[ -n "$COMMITS" ]]; then
  while IFS=$'\t' read -r sha subject; do
    [[ -n "$sha" ]] || continue
    case "$subject" in
      chore\(release\):*|ci:*|ci\(*\):*|build:*|build\(*\):*|test:*|test\(*\):*) ;;
      *) MAINTENANCE_COMMITS+="${sha}"$'\t'"${subject}"$'\n' ;;
    esac
    if is_release_hygiene_subject "$subject"; then
      continue
    fi

    DISPLAY_COMMITS+="${sha}"$'\t'"${subject}"$'\n'
  done <<<"$COMMITS"

  DISPLAY_COMMITS="$(printf '%s' "$DISPLAY_COMMITS" | trim_blank_edges || true)"
  MAINTENANCE_COMMITS="$(printf '%s' "$MAINTENANCE_COMMITS" | trim_blank_edges || true)"
fi

categorize_subject() {
  local subject="$1"
  case "$subject" in
    feat:*|feat\(*\):*) printf '%s\n' "Added" ;;
    fix:*|fix\(*\):*|perf:*|perf\(*\):*) printf '%s\n' "Fixed and improved" ;;
    docs:*|docs\(*\):*) printf '%s\n' "Documentation" ;;
    *) printf '%s\n' "Changed" ;;
  esac
}

write_synthesized_highlights() {
  local max_per_category="${RELEASE_NOTES_MAX_PER_CATEGORY:-10}"
  local category subject highlight
  local added="" fixed="" changed="" documentation=""
  local added_count=0 fixed_count=0 changed_count=0 documentation_count=0

  while IFS=$'\t' read -r _sha subject; do
    [[ -n "$subject" ]] || continue
    highlight="$(subject_highlight "$subject")"
    [[ -n "$highlight" ]] || continue
    category="$(categorize_subject "$subject")"
    case "$category" in
      "Added")
        added_count=$((added_count + 1))
        if (( added_count <= max_per_category )); then added+="- ${highlight}"$'\n'; fi
        ;;
      "Fixed and improved")
        fixed_count=$((fixed_count + 1))
        if (( fixed_count <= max_per_category )); then fixed+="- ${highlight}"$'\n'; fi
        ;;
      "Documentation")
        documentation_count=$((documentation_count + 1))
        if (( documentation_count <= max_per_category )); then documentation+="- ${highlight}"$'\n'; fi
        ;;
      *)
        changed_count=$((changed_count + 1))
        if (( changed_count <= max_per_category )); then changed+="- ${highlight}"$'\n'; fi
        ;;
    esac
  done <<<"$DISPLAY_COMMITS"

  for category in "Added" "Fixed and improved" "Changed" "Documentation"; do
    case "$category" in
      "Added") local body="$added" count=$added_count ;;
      "Fixed and improved") local body="$fixed" count=$fixed_count ;;
      "Changed") local body="$changed" count=$changed_count ;;
      *) local body="$documentation" count=$documentation_count ;;
    esac
    [[ -n "$body" ]] || continue
    printf '### %s\n\n%s' "$category" "$body"
    if (( count > max_per_category )); then
      printf '%s\n' "- Plus $((count - max_per_category)) additional ${category,,} changes; see the compare link for the complete diff."
    fi
    printf '\n'
  done
}

INCLUDE_COMMIT_DETAILS="${RELEASE_NOTES_INCLUDE_COMMITS:-0}"

if [[ -n "$DISPLAY_COMMITS" ]]; then
  commit_count="$(printf '%s\n' "$DISPLAY_COMMITS" | sed '/^[[:space:]]*$/d' | wc -l | tr -d ' ')"
  synthesized_commit_limit="${RELEASE_NOTES_SYNTHETIC_COMMIT_LIMIT:-80}"

  if [[ -z "$TAG_SECTION" && "$commit_count" -gt "$synthesized_commit_limit" ]]; then
    err "refusing to synthesize release notes from ${commit_count} commits for ${LOGICAL_VERSION}; add a docs/CHANGELOG.md section for this version"
  fi

  if [[ -n "$TAG_SECTION" && "$commit_count" -gt "$synthesized_commit_limit" ]]; then
    INCLUDE_COMMIT_DETAILS=0
  fi
fi

PRODUCT_NAME="${RELEASE_NOTES_PRODUCT_NAME:-}"
if [[ -z "$PRODUCT_NAME" ]]; then
  PRODUCT_NAME="$(basename "$(git config --get remote.origin.url || echo slskdn)" .git)"
  if [[ "$PRODUCT_NAME" == "slskdn" ]]; then
    PRODUCT_NAME="slskdN"
  fi
fi

mkdir -p "$(dirname "$OUT_PATH")"

{
  printf '# %s %s\n\n' "$PRODUCT_NAME" "$LOGICAL_VERSION"
  printf 'Released: %s\n\n' "$RELEASE_DATE"

  if [[ -n "$PREV_TAG" && -n "$REPO_URL" ]]; then
    printf 'Compare: [%s...%s](%s)\n\n' "$PREV_DISPLAY_TAG" "$LOGICAL_VERSION" "$COMPARE_URL"
  elif [[ -n "$PREV_TAG" ]]; then
    printf 'Compare: `%s...%s`\n\n' "$PREV_DISPLAY_TAG" "$LOGICAL_VERSION"
  fi

  printf '## Highlights\n\n'

  if [[ -n "$TAG_SECTION" ]]; then
    printf '%s\n\n' "$TAG_SECTION"
    printf '_Source: `%s` section for `%s`._\n\n' "$CHANGELOG_PATH" "$LOGICAL_VERSION"
  else
    if [[ -z "$DISPLAY_COMMITS" ]]; then
      if [[ -z "$MAINTENANCE_COMMITS" ]]; then
        if [[ "${RELEASE_NOTES_ALLOW_EMPTY:-0}" != "1" ]]; then
          err "no changes found for ${LOGICAL_VERSION}; add a versioned changelog section"
        fi
        printf '%s\n\n' "This release republishes the same source commit as the previous published release. There are no additional application or configuration changes; use this release for refreshed distribution artifacts and package-channel publication."
        printf '%s\n\n' "- Rebuilt and republished the existing slskdN source for all supported release targets."
      else
        printf '%s\n\n' "This is a maintenance/documentation release with no additional application binary changes beyond the previous published release."
        DISPLAY_COMMITS="$MAINTENANCE_COMMITS"
        write_synthesized_highlights
      fi
    else
      write_synthesized_highlights
    fi
  fi

  if [[ "$INCLUDE_COMMIT_DETAILS" -eq 1 ]]; then
    printf '## Included Product Commits\n\n'
    if [[ -z "$DISPLAY_COMMITS" ]]; then
      printf '%s\n' "- No product-facing commits listed for \`${LOGICAL_VERSION}\` after filtering release, CI, documentation-gotcha, test, and repo-maintenance commits."
    else
      while IFS=$'\t' read -r sha subject; do
        short_sha="${sha:0:7}"
        if [[ -n "$REPO_URL" ]]; then
          printf '%s\n' "- \`${short_sha}\` ${subject} ([commit](${REPO_URL}/commit/${sha}))"
        else
          printf '%s\n' "- \`${short_sha}\` ${subject}"
        fi
      done <<<"$DISPLAY_COMMITS"
    fi
  fi
} >"$OUT_PATH"

release_notes_base="${PREV_TAG:-}"
if [[ -z "$release_notes_base" ]]; then
  release_notes_base="$(git hash-object -t tree /dev/null)"
fi
python3 scripts/release_notes.py assemble \
  --base "$release_notes_base" \
  --head "$GIT_REF" \
  --input "$OUT_PATH" \
  --output "$OUT_PATH"

printf 'Wrote %s\n' "$OUT_PATH"
