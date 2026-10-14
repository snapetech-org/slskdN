#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failed=0

if rg -n 'raw\.githubusercontent\.com/snapetech-org/slskdN/master|github\.com/snapetech-org/slskdN/blob/master|github\.com/snapetech-org/slskdN/tree/master|github\.com/snapetech-org/slskdN/raw/master' \
  "$repo_root/packaging" "$repo_root/docs" "$repo_root/config" \
  -g '!docs/archive/**' \
  -g '!docs/dev/bug-burndown-ledger.md' >&2; then
  printf 'Active fork package/docs links must target main, not master.\n' >&2
  failed=1
fi

if rg -n --hidden '(github\.com|githubusercontent\.com)/snapetech/(slskdn|slskdN)(/|[?#]|[[:space:]]|$)' \
  "$repo_root" \
  -g '!**/.git/**' \
  -g '!memory-bank/**' \
  -g '!docs/archive/**' \
  -g '!docs/CHANGELOG.md' \
  -g '!CHANGELOG.md' \
  -g '!release-notes/**' \
  -g '!docs/dev/bug-burndown-ledger.md' \
  -g '!scripts/check-fork-main-branch-links.sh' \
  -g '!packaging/scripts/validate-packaging-metadata.sh' >&2; then
  printf 'Active repository links must use the canonical snapetech-org/slskdN owner.\n' >&2
  failed=1
fi

if rg -n 'branches:\s*\[master\]' "$repo_root/docs" \
  -g '!docs/archive/**' \
  -g '!docs/dev/bug-burndown-ledger.md' >&2; then
  printf 'Active GitHub Actions examples must target main, not master.\n' >&2
  failed=1
fi

if rg -n 'slskdN master branch|\*\*Branch\*\*:\s*`?master`?|git checkout master' \
  "$repo_root/docs" \
  -g '!docs/archive/**' \
  -g '!docs/dev/bug-burndown-ledger.md' \
  -g '!docs/CHANGELOG.md' >&2; then
  printf 'Active fork docs must describe main as the fork branch, not master.\n' >&2
  failed=1
fi

if rg -n 'every push to master|Keep master scanning' "$repo_root/.github/workflows" \
  -g '*.yml' \
  -g '*.yaml' >&2; then
  printf 'Active workflow comments must describe main as the fork branch, not master.\n' >&2
  failed=1
fi

if [ "$failed" -ne 0 ]; then
  exit 1
fi

printf 'Active fork branch links target main.\n'
