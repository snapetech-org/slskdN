#!/usr/bin/env bash
set -euo pipefail

expected_repo="snapetech-org/slskdN"
expected_upstream="https://github.com/slskd/slskd.git"

origin_url="$(git remote get-url origin)"
push_url="$(git remote get-url --push origin)"
upstream_url="$(git remote get-url upstream 2>/dev/null || true)"

github_repo_from_url() {
  local url="$1"
  local path
  case "${url}" in
    git@github.com:*) path="${url#git@github.com:}" ;;
    ssh://git@github.com/*) path="${url#ssh://git@github.com/}" ;;
    https://github.com/*) path="${url#https://github.com/}" ;;
    *) path="" ;;
  esac
  path="${path%.git}"
  printf '%s' "${path,,}"
}

expected_repo_lower="${expected_repo,,}"
origin_repo="$(github_repo_from_url "${origin_url}")"
push_repo="$(github_repo_from_url "${push_url}")"
actual_repo="$(gh repo view "${expected_repo}" --json nameWithOwner --jq .nameWithOwner)"

if [[ "${origin_repo}" != "${expected_repo_lower}" ]]; then
  echo "ERROR: origin fetch remote is '${origin_url}', expected a GitHub remote for '${expected_repo}'." >&2
  exit 1
fi

if [[ "${push_repo}" != "${expected_repo_lower}" ]]; then
  echo "ERROR: origin push remote is '${push_url}', expected a GitHub remote for '${expected_repo}'." >&2
  exit 1
fi

if [[ -n "${upstream_url}" && "${upstream_url}" != "${expected_upstream}" ]]; then
  echo "ERROR: upstream remote is '${upstream_url}', expected '${expected_upstream}'." >&2
  exit 1
fi

if [[ "${actual_repo,,}" != "${expected_repo_lower}" ]]; then
  echo "ERROR: GitHub resolved '${expected_repo}' to '${actual_repo}', which does not match the expected owner and repository." >&2
  exit 1
fi

cat <<EOF
GitHub target verified.
- origin: ${origin_url}
- origin push: ${push_url}
- upstream: ${upstream_url:-<unset>}
- GitHub repository: ${actual_repo}

Write actions from this checkout must pass --repo ${expected_repo} explicitly.
Upstream slskd/slskd is read-only reference and must not be modified from this workspace.
EOF
