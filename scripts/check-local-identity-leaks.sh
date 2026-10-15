#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if ! command -v rg >/dev/null 2>&1; then
  echo "check-local-identity-leaks: ripgrep (rg) is required." >&2
  exit 127
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "check-local-identity-leaks: jq is required." >&2
  exit 127
fi

tmp_tokens="$(mktemp)"
tmp_commits="$(mktemp)"
tmp_files="$(mktemp)"
trap 'rm -f "$tmp_tokens" "$tmp_commits" "$tmp_files"' EXIT

add_token() {
  local token="$1"
  token="${token//$'\n'/}"
  token="${token//$'\r'/}"
  [[ ${#token} -ge 3 ]] || return 0
  case "$token" in
    root|runner|build|agent|agents|github|actions|action|node|npm|yarn|pnpm|dotnet|cargo|target|debug|release)
      return 0
      ;;
  esac
  printf '%s\n' "$token" >>"$tmp_tokens"
}

add_token "${LOCAL_IDENTITY_DENYLIST:-}"
add_token "${SLSKDN_LOCAL_IDENTITY_DENYLIST:-}"
add_token "${SLSKDN_FORBIDDEN_LOCAL_HOSTNAME:-}"

case "${LOCAL_IDENTITY_SCAN_RUNTIME_IDENTITIES:-1}" in
  0)
    ;;
  1)
    add_token "$(hostname -s 2>/dev/null || true)"
    add_token "${USER:-}"
    add_token "$(id -un 2>/dev/null || true)"
    add_token "$(basename "${HOME:-}" 2>/dev/null || true)"
    ;;
  *)
    echo "LOCAL_IDENTITY_SCAN_RUNTIME_IDENTITIES must be 0 or 1." >&2
    exit 2
    ;;
esac

read_csv_tokens() {
  local value="$1"
  [[ -n "$value" ]] || return 0
  IFS=',' read -ra tokens <<<"$value"
  for token in "${tokens[@]}"; do
    add_token "$token"
  done
}

read_csv_tokens "${LOCAL_IDENTITY_DENYLIST:-}"
read_csv_tokens "${SLSKDN_LOCAL_IDENTITY_DENYLIST:-}"

read_denylist_file() {
  local file="$1"
  [[ -n "$file" && -f "$file" ]] || return 0
  while IFS= read -r token; do
    [[ "$token" =~ ^[[:space:]]*# ]] && continue
    add_token "$token"
  done <"$file"
}

read_denylist_file "${LOCAL_IDENTITY_DENYLIST_FILE:-}"
read_denylist_file "${SLSKDN_LOCAL_IDENTITY_DENYLIST_FILE:-}"

sort -u "$tmp_tokens" -o "$tmp_tokens"
if [[ ! -s "$tmp_tokens" ]]; then
  echo "No local identity tokens configured for scanning."
  exit 0
fi

failed=0

check_file() {
  local label="$1"
  local path="$2"
  local display_path="${3:-$path}"
  local whole_words="${4:-0}"
  local matches=""
  local -a rg_args=(--json --fixed-strings --ignore-case --file "$tmp_tokens")

  if [[ "$whole_words" == "1" ]]; then
    rg_args+=(--word-regexp)
  fi

  [[ -f "$path" ]] || return 0
  matches="$(
    rg "${rg_args[@]}" "$path" |
      jq -r --arg label "$label" --arg display_path "$display_path" 'select(.type == "match") | "\($label): \($display_path):\(.data.line_number)"' |
      sort -u || true
  )"

  if [[ -n "$matches" ]]; then
    printf '%s\n' "$matches" >&2
    failed=1
  fi
}

if [[ -f docs/CHANGELOG.md ]]; then
  tmp_unreleased="$(mktemp)"
  trap 'rm -f "$tmp_tokens" "$tmp_commits" "$tmp_files" "$tmp_unreleased"' EXIT
  awk '
    $0 == "## [Unreleased]" { in_section = 1; next }
    in_section && /^## \[/ { exit }
    in_section { print }
  ' docs/CHANGELOG.md >"$tmp_unreleased"
  check_file "docs/CHANGELOG.md Unreleased" "$tmp_unreleased" "docs/CHANGELOG.md#Unreleased"
fi

if [[ "${LOCAL_IDENTITY_SCAN_COMMITS:-0}" == "1" ]]; then
  latest_tag="$(git tag --sort=-creatordate --list 'build-main-*' | head -n 1 || true)"
  if [[ -z "$latest_tag" ]]; then
    latest_tag="$(git describe --tags --abbrev=0 2>/dev/null || true)"
  fi
  if [[ -n "$latest_tag" ]]; then
    # Co-authored-by and Signed-off-by trailers are attribution metadata rather
    # than release-facing content, so exclude only those trailers while
    # retaining the subject and body scan.
    git log --format='%s%n%b' "${latest_tag}..HEAD" |
      sed -E '/^[[:space:]]*(Co-authored-by|Signed-off-by):/Id' >"$tmp_commits"
    # Match names as complete words so a synthetic sandbox token such as
    # "home" does not match the ordinary plural "homes".
    check_file "recent commit messages" "$tmp_commits" "git log" "1"
  fi
fi

find . \
  -path './.git' -prune -o \
  -path './node_modules' -prune -o \
  -path './vendor' -prune -o \
  -path './target' -prune -o \
  -path './dist' -prune -o \
  -path './build' -prune -o \
  -path './zeek/pkg' -prune -o \
  -type f \( \
    -path './.github/release-notes/*' -o \
    -path './docs/dev/release-copy.md' -o \
    -path './docs/release*.md' -o \
    -path './docs/RELEASE*.md' -o \
    -path './packaging/winget/*' \
  \) -print | sed 's#^./##' >"$tmp_files"

while IFS= read -r path; do
  [[ -n "$path" ]] || continue
  check_file "$path" "$path"
done <"$tmp_files"

if [[ "$failed" -ne 0 ]]; then
  echo "Local hostname/username leaked into release-facing text. Use generic wording like 'live validation host' or 'operator account'." >&2
  exit 1
fi

echo "No local hostname or username leaks found in release-facing text."
