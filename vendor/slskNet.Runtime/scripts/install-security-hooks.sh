#!/usr/bin/env bash
set -euo pipefail
repo_root="$(git rev-parse --show-toplevel)"
current="$(git -C "$repo_root" config --local --get core.hooksPath || true)"
if [[ -n "$current" ]]; then
  printf 'Keeping existing core.hooksPath (%s).\n' "$current"
  exit 0
fi
git -C "$repo_root" config --local core.hooksPath .githooks
printf 'Installed local pre-commit security scan hook.\n'
