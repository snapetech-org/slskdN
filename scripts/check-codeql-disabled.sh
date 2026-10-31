#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workflow_directory="$repo_root/.github/workflows"

active_workflows="$(find "$workflow_directory" -maxdepth 1 -type f \
  \( -iname '*codeql*.yml' -o -iname '*codeql*.yaml' \) -print | sort)"
if [[ -n "$active_workflows" ]]; then
  printf 'CodeQL workflow files must be disabled or removed:\n%s\n' "$active_workflows" >&2
  exit 1
fi

if rg -n -i \
  'github/codeql-action/(init|analyze)@|codeql[[:space:]]+(database|analyze|pack)|^[[:space:]]*name:[[:space:]]*CodeQL([[:space:](]|$)' \
  "$workflow_directory" --glob '*.yml' --glob '*.yaml'; then
  printf 'CodeQL analysis must not be invoked by repository workflows\n' >&2
  exit 1
fi

printf 'No active CodeQL workflow or analysis invocation remains.\n'
