#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runner="$repo_root/scripts/run-bug-council-all-phases.sh"
failed=0

require_literal() {
  local literal="$1"
  local file="$2"

  if ! rg -q --fixed-strings "$literal" "$file"; then
    printf '%s is missing required council all-phases marker: %s\n' "${file#$repo_root/}" "$literal" >&2
    failed=1
  fi
}

if [ ! -x "$runner" ]; then
  printf 'Council all-phases runner is missing or not executable: %s\n' "${runner#$repo_root/}" >&2
  exit 1
fi

require_literal "check:remediation" "$runner"
require_literal "WebInputAdversarialFuzzTests" "$runner"
require_literal "dotnet test" "$runner"

require_literal '"check:council": "bash scripts/run-bug-council-all-phases.sh"' "$repo_root/package.json"
require_literal '$repo_root/scripts/check-bug-council-all-phases.sh' "$repo_root/scripts/check-remediation-baseline.sh"

if [ "$failed" -ne 0 ]; then
  exit 1
fi

printf 'Bug council all-phases runner is registered.\n'
