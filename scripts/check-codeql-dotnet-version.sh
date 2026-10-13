#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workflow="$repo_root/.github/workflows/codeql.yml"
ci_workflow="$repo_root/.github/workflows/ci.yml"
project="$repo_root/src/slskd/slskd.csproj"
failed=0

if [ ! -f "$workflow" ]; then
  printf '.github/workflows/codeql.yml is missing\n' >&2
  exit 1
fi

target_major="$(sed -n 's/.*<TargetFramework>net\([0-9][0-9]*\)\..*/\1/p' "$project" | head -n1)"
sdk_major="$(sed -n 's/.*"version": "\([0-9][0-9]*\)\..*/\1/p' "$repo_root/global.json" | head -n1)"
ci_sdk_version="$(sed -n "s/^[[:space:]]*DOTNET_VERSION: '\([^']*\)'/\1/p" "$ci_workflow" | head -n1)"
workflow_sdk_version="$(sed -n "s/^[[:space:]]*DOTNET_VERSION: '\([^']*\)'/\1/p" "$workflow" | head -n1)"

if [ -z "$target_major" ]; then
  printf 'unable to read target framework major version\n' >&2
  exit 1
fi

if [ -n "$sdk_major" ] && [ "$target_major" != "$sdk_major" ]; then
  printf 'global.json SDK major %s does not match slskd target framework net%s.0\n' "$sdk_major" "$target_major" >&2
  failed=1
fi

if [[ ! "$ci_sdk_version" =~ ^${target_major}\.0\.[0-9]+$ ]]; then
  printf 'CI must pin a stable .NET %s.0 SDK version, found %s\n' "$target_major" "${ci_sdk_version:-none}" >&2
  failed=1
fi

if [ "$workflow_sdk_version" != "$ci_sdk_version" ]; then
  printf 'CodeQL workflow must use the CI SDK pin %s, found %s\n' "$ci_sdk_version" "${workflow_sdk_version:-none}" >&2
  failed=1
fi

if ! rg -q 'dotnet-version: \$\{\{ env\.DOTNET_VERSION \}\}' "$workflow"; then
  printf 'CodeQL workflow must use env.DOTNET_VERSION for setup-dotnet\n' >&2
  failed=1
fi

if rg -n "dotnet-version: '[0-9]+'" "$workflow" >&2; then
  printf 'CodeQL workflow must not pin a divergent hard-coded dotnet-version\n' >&2
  failed=1
fi

if [ "$failed" -ne 0 ]; then
  exit 1
fi

printf 'CodeQL and CI use the same stable .NET SDK pin for the application target framework.\n'
