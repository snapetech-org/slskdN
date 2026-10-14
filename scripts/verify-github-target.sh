#!/usr/bin/env bash
set -euo pipefail

expected_repo="snapetech-org/slskdN"
expected_origin="git@github.com:snapetech-org/slskdN.git"
expected_upstream="https://github.com/slskd/slskd.git"

origin_url="$(git remote get-url origin)"
upstream_url="$(git remote get-url upstream 2>/dev/null || true)"
default_repo="$(gh repo set-default --view 2>/dev/null || true)"

if [[ "${origin_url}" != "${expected_origin}" ]]; then
  echo "ERROR: origin remote is '${origin_url}', expected '${expected_origin}'." >&2
  exit 1
fi

if [[ -n "${upstream_url}" && "${upstream_url}" != "${expected_upstream}" ]]; then
  echo "ERROR: upstream remote is '${upstream_url}', expected '${expected_upstream}'." >&2
  exit 1
fi

if [[ "${default_repo}" != "${expected_repo}" ]]; then
  echo "ERROR: gh default repo is '${default_repo:-<unset>}', expected '${expected_repo}'." >&2
  echo "Run: gh repo set-default ${expected_repo}" >&2
  exit 1
fi

cat <<EOF
GitHub target verified.
- origin: ${origin_url}
- upstream: ${upstream_url:-<unset>}
- gh default: ${default_repo}

Write actions from this checkout must target ${expected_repo} only.
Upstream slskd/slskd is read-only reference and must not be modified from this workspace.
EOF
