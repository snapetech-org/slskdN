#!/usr/bin/env bash
set -euo pipefail

expected_repo="snapetech-org/slskdN"
expected_repo_id="1108894784"
expected_upstream="https://github.com/slskd/slskd.git"

fail() {
  echo "ERROR: $1" >&2
  exit 1
}

github_repo_from_url() {
  local url="$1"
  local repository

  case "$url" in
    git@github.com:*) repository="${url#git@github.com:}" ;;
    ssh://git@github.com/*) repository="${url#ssh://git@github.com/}" ;;
    https://github.com/*) repository="${url#https://github.com/}" ;;
    *) fail "remote must use a recognized GitHub URL" ;;
  esac

  repository="${repository%.git}"
  printf '%s\n' "${repository,,}"
}

origin_url="$(git remote get-url origin)"
push_url="$(git remote get-url --push origin)"
upstream_url="$(git remote get-url upstream 2>/dev/null || true)"
expected_repo_lower="${expected_repo,,}"
origin_repo="$(github_repo_from_url "$origin_url")"
push_repo="$(github_repo_from_url "$push_url")"

if [[ "$origin_repo" != "$expected_repo_lower" ]]; then
  fail "origin fetch remote is '$origin_url'; expected a GitHub remote for '$expected_repo'"
fi

if [[ "$push_repo" != "$expected_repo_lower" ]]; then
  fail "origin push remote is '$push_url'; expected a GitHub remote for '$expected_repo'"
fi

if [[ -n "$upstream_url" && "$upstream_url" != "$expected_upstream" ]]; then
  fail "upstream remote is not the expected read-only reference"
fi

if ! repository_id="$(gh api "repos/$expected_repo" --jq '.id | select(type == "number")')"; then
  fail "could not resolve canonical GitHub repository '$expected_repo'"
fi

if [[ "$repository_id" != "$expected_repo_id" ]]; then
  fail "canonical GitHub repository resolved to unexpected repository ID '$repository_id'"
fi

cat <<EOF
GitHub target verified.
- origin: ${origin_url}
- origin push: ${push_url}
- upstream: ${upstream_url:-<unset>}
- GitHub repository: ${expected_repo} (ID ${repository_id})

Write actions from this checkout must pass --repo ${expected_repo} explicitly.
Upstream slskd/slskd is a read-only reference and must not be modified from this workspace.
EOF
