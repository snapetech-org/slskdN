#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

assert_phase_done() {
  local phase_name="$1"

  if ! awk -F'|' -v phase="$phase_name" '
    $2 ~ /^[[:space:]]*[0-9]+[[:space:]]*$/ && $3 ~ phase {
      status = $4
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", status)
      found = 1
      if (status != "Done") {
        exit 2
      }
    }
    END {
      if (!found) {
        exit 3
      }
    }
  ' "$repo_root/docs/dev/bug-council-phases.md"; then
    printf 'Council phase is not Done or is missing: %s\n' "$phase_name" >&2
    exit 1
  fi
}

assert_phase_done "Focused remediation documentation"
assert_phase_done "Negative-space gate registration"
assert_phase_done "Web-input adversarial regression"

npm run check:remediation
dotnet test "$repo_root/tests/slskd.Tests/slskd.Tests.csproj" --no-restore --filter FullyQualifiedName~WebInputAdversarialFuzzTests

printf 'All slskd remediation regression phases passed.\n'
