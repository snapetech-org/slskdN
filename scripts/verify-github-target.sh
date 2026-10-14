#!/usr/bin/env bash
set -euo pipefail

expected_repo_id="1108894784"
expected_upstream="https://github.com/slskd/slskd.git"

fail() {
  echo "ERROR: $1" >&2
  exit 1
}

repo_from_origin() {
  local remote_url="$1"
  local repository=""

  case "$remote_url" in
    git@github.com:*) repository="${remote_url#git@github.com:}" ;;
    ssh://git@github.com/*) repository="${remote_url#ssh://git@github.com/}" ;;
    https://github.com/*) repository="${remote_url#https://github.com/}" ;;
    *) fail "origin must use a recognized GitHub URL" ;;
  esac

  repository="${repository%.git}"
  if [[ ! "$repository" =~ ^[[:alnum:]_.-]+/slskdN$ ]]; then
    fail "origin does not identify the expected repository"
  fi

  printf '%s\n' "$repository"
}

repo_id_for() {
  local repository="$1"
  local repository_id

  if ! repository_id="$(gh api "repos/${repository}" --jq '.id | select(type == "number")')"; then
    fail "could not resolve configured GitHub repository"
  fi

  if [[ "$repository_id" != "$expected_repo_id" ]]; then
    fail "configured GitHub repository resolved to unexpected repository ID ${repository_id}"
  fi

  printf '%s\n' "$repository_id"
}

origin_url="$(git remote get-url origin)"
upstream_url="$(git remote get-url upstream 2>/dev/null || true)"
default_repo="$(gh repo set-default --view 2>/dev/null || true)"

if [[ -n "$upstream_url" && "$upstream_url" != "$expected_upstream" ]]; then
  fail "upstream remote is not the expected read-only reference"
fi

origin_repo="$(repo_from_origin "$origin_url")"
if [[ ! "$default_repo" =~ ^[[:alnum:]_.-]+/slskdN$ ]]; then
  fail "GitHub default repository is unset or invalid"
fi

origin_repo_id="$(repo_id_for "$origin_repo")"
default_repo_id="$(repo_id_for "$default_repo")"

cat <<EOF
GitHub target verified by repository ID.
- origin repository ID: ${origin_repo_id}
- upstream: ${upstream_url:-<unset>}
- gh default repository ID: ${default_repo_id}

Write actions from this checkout must target repository ID ${expected_repo_id} only.
Upstream slskd/slskd is read-only reference and must not be modified from this workspace.
EOF
