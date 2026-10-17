#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failed=0

target_major="$(sed -n 's/.*<TargetFramework>net\([0-9][0-9]*\)\..*/\1/p' "$repo_root/src/slskd/slskd.csproj" | head -n1)"

if [ -z "$target_major" ]; then
  printf 'unable to read slskd target framework major version\n' >&2
  exit 1
fi

while IFS= read -r project; do
  project_path="${project#"$repo_root"/}"
  target_framework="$(sed -n 's/.*<TargetFramework>\([^<]*\)<\/TargetFramework>.*/\1/p' "$project" | head -n1)"
  if [ "$target_framework" != "net${target_major}.0" ]; then
    printf '%s targets %s; first-party projects under src/tests/tools must target net%s.0\n' \
      "$project_path" "${target_framework:-no single target framework}" "$target_major" >&2
    failed=1
  fi
done < <(find "$repo_root/src" "$repo_root/tests" "$repo_root/tools" -name '*.csproj' -print | sort)

pinned_sdk_major="$(sed -n 's/.*"version": "\([0-9][0-9]*\)\..*/\1/p' "$repo_root/global.json" | head -n1)"
if [ "$pinned_sdk_major" != "$target_major" ]; then
  printf 'global.json pins .NET %s but the application targets .NET %s\n' \
    "${pinned_sdk_major:-no SDK version}" "$target_major" >&2
  failed=1
fi

expect_literal() {
  local file="$1"
  local literal="$2"

  if ! grep -Fq -- "$literal" "$repo_root/$file"; then
    printf '%s is missing literal: %s\n' "$file" "$literal" >&2
    failed=1
  fi
}

expect_literal packaging/linux/install-from-release.sh "aspnetcore-runtime-${target_major}.0"
expect_literal packaging/proxmox-lxc/setup-inside-ct.sh "aspnetcore-runtime-${target_major}.0"
expect_literal packaging/proxmox-lxc/README.md ".NET ${target_major}"
expect_literal packaging/flatpak/io.github.slskd.slskdn.yml "Runtime/${target_major}.0."
expect_literal packaging/flatpak/io.github.slskd.slskdn.yml "dotnet-runtime-${target_major}.0."
expect_literal packaging/flatpak/FLATHUB_SUBMISSION.md ".NET ${target_major}.0 runtime"
expect_literal docs/FEATURES.md ".NET ${target_major}.0 or later"
expect_literal docs/dev/e2e-testing-guide.md ".NET ${target_major}.0 SDK"
expect_literal CONTRIBUTING.md ".NET ${target_major}.0 SDK"
workflow=".github/workflows/e2e-tests.yml"
if ! rg -q "^  DOTNET_VERSION: '${target_major}\.0\.[0-9]+'$" "$repo_root/$workflow"; then
  printf '%s must pin the application .NET %s.0 runtime version\n' "$workflow" "$target_major" >&2
  failed=1
fi
expect_literal "$workflow" 'dotnet-version: ${{ env.DOTNET_VERSION }}'

expect_hosted_workflows() {
  local workflow_directory="$repo_root/.github/workflows"
  local allowed_workflow="$workflow_directory/feature-coherence-validation.yml"
  local expected_workflow_sha256="994a0beab251e1f19488493e0bc4e70ea4bf8ba063df34f728cc3128e379a3b0"
  local actual_workflow_sha256
  local policy_pattern='^[[:space:]]*(runs-on|labels):.*self-hosted|TRUSTED_MAIN_RUNNERS_ENABLED|PREFER_SELF_HOSTED|inputs\.runner'
  local matches
  local disallowed_matches

  if [[ ! -f "$allowed_workflow" || -L "$allowed_workflow" ]]; then
    printf 'the audited public-fork validation workflow is missing or not a regular file\n' >&2
    failed=1
  else
    actual_workflow_sha256="$(sha256sum -- "$allowed_workflow" | awk '{print $1}')"
    if [[ "$actual_workflow_sha256" != "$expected_workflow_sha256" ]]; then
      printf 'the public-fork runner exception does not match its reviewed workflow contents\n' >&2
      failed=1
    fi
  fi

  matches="$(rg -n "$policy_pattern" "$workflow_directory" 2>&1 || true)"
  if [[ -n "$matches" ]]; then
    disallowed_matches="$(printf '%s\n' "$matches" | awk -F: -v allowed="$allowed_workflow" '$1 != allowed { print }')"
    if [[ -n "$disallowed_matches" ]]; then
      printf '%s\n' "$disallowed_matches" >&2
      printf 'only the exact audited public-fork validation workflow may select a private runner\n' >&2
      failed=1
    fi
  fi
}

expect_hosted_workflows

if rg -n '\.NET 8\.0|\.NET 8|aspnetcore-runtime-8\.0|dotnet-runtime-8\.0|dotnet-version: .8\.0\.x.' \
  "$repo_root/packaging/flatpak" \
  "$repo_root/packaging/proxmox-lxc" \
  "$repo_root/docs/FEATURES.md" \
  "$repo_root/docs/dev/e2e-testing-guide.md" \
  "$repo_root/CONTRIBUTING.md" >&2; then
  printf 'Active package/docs runtime references must match net%s.0, not .NET 8.\n' "$target_major" >&2
  failed=1
fi

if [ "$failed" -ne 0 ]; then
  exit 1
fi

printf '.NET runtime/package matrix matches the application target framework.\n'
