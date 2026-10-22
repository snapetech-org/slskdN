#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failed=0

while IFS= read -r workflow; do
  rel="${workflow#$repo_root/}"

  if LC_ALL=C grep -n $'\t' "$workflow" >&2; then
    printf '%s contains tab characters; GitHub workflow YAML must be spaces-only\n' "$rel" >&2
    failed=1
  fi
done < <(find "$repo_root/.github/workflows" -maxdepth 1 -type f \( -name '*.yml' -o -name '*.yaml' \) | sort)

if ! ruby -e 'require "yaml"; ARGV.each { |path| YAML.load_file(path) }' "$repo_root"/.github/workflows/*.yml; then
  printf 'GitHub workflow YAML parsing failed\n' >&2
  failed=1
fi

if [ "$failed" -ne 0 ]; then
  exit 1
fi

printf 'GitHub workflow YAML files parse and contain no tab indentation.\n'
